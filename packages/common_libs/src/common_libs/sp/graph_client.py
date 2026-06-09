# graph_client.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import msal
import requests


@dataclass(frozen=True)
class SharePointConfig:
    tenant_id: str
    client_id: str
    client_secret: str
    sp_hostname: str     # e.g. "contoso.sharepoint.com"
    sp_site_path: str    # e.g. "sites/YourSiteName"
    drive_name: str = "Documents"  # commonly "Documents" (shown as "Shared Documents" in UI)


class GraphSharePointClient:
    """
    Minimal Microsoft Graph client for uploading files to a SharePoint document library.
    Uses client credentials flow (app-only).

    Notes:
      - Simple PUT uploads are best for <= ~250MB.
      - Destination folders must already exist (simple PUT does not create folders).
    """

    def __init__(self, config: SharePointConfig, timeout: int = 60):
        """Initializes the client with a SharePoint configuration.

        Args:
            config: SharePointConfig dataclass with tenant, client, and
                SharePoint site details.
            timeout: HTTP request timeout in seconds. Defaults to 60.
        """
        self.config = config
        self.timeout = timeout
        self._token: Optional[str] = None
        self._site_id: Optional[str] = None
        self._drive_id: Optional[str] = None

    @classmethod
    def from_env(cls) -> "GraphSharePointClient":
        """Constructs a client by reading credentials from environment variables.

        Expected env vars:
          AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET,
          SP_HOSTNAME, SP_SITE_PATH, (optional) SP_DRIVE_NAME

        Returns:
            GraphSharePointClient: Configured client instance.
        """
        cfg = SharePointConfig(
            tenant_id=os.environ["AZURE_TENANT_ID"],
            client_id=os.environ["AZURE_CLIENT_ID"],
            client_secret=os.environ["AZURE_CLIENT_SECRET"],
            sp_hostname=os.environ["SP_HOSTNAME"],
            sp_site_path=os.environ["SP_SITE_PATH"],
            drive_name=os.environ.get("SP_DRIVE_NAME", "Documents"),
        )
        return cls(cfg)

    # ---------- Helpers ----------
    @staticmethod
    def _encode_sp_path(path: str) -> str:
        """URL-encodes a SharePoint path while preserving "/" separators.

        This prevents Graph errors when folders or files contain spaces, "&", etc.

        Args:
            path (str): SharePoint-relative path (e.g. "Folder/My File.xlsx").

        Returns:
            str: URL-encoded path with "/" preserved.
        """
        return quote(path, safe="/")

    def _raise_for_status(self, r: requests.Response) -> None:
        """Raises a RuntimeError with Graph error details if the response is an HTTP error.

        Args:
            r: The HTTP response object to check.

        Raises:
            RuntimeError: If the response status code indicates an HTTP error,
                including the status code and the parsed JSON body (or raw text).
        """
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise RuntimeError(f"Graph request failed: {r.status_code} {detail}") from e

    # ---------- Auth ----------
    def get_access_token(self, force_refresh: bool = False) -> str:
        """Acquires a Microsoft Graph access token using client credentials flow.

        Tokens are cached on the instance; set force_refresh=True to obtain a
        new token regardless of the cached value.

        Args:
            force_refresh: If True, always acquires a new token even if one is
                cached. Defaults to False.

        Returns:
            str: A valid Bearer access token for Microsoft Graph.

        Raises:
            RuntimeError: If MSAL token acquisition fails.
        """
        if self._token and not force_refresh:
            return self._token

        app = msal.ConfidentialClientApplication(
            self.config.client_id,
            authority=f"https://login.microsoftonline.com/{self.config.tenant_id}",
            client_credential=self.config.client_secret,
        )
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" not in result:
            raise RuntimeError(f"Auth failed: {result}")

        self._token = result["access_token"]
        return self._token

    def _headers(self) -> dict:
        """Returns the HTTP headers required for authenticated Graph API requests.

        Returns:
            dict: Headers dict with Authorization Bearer token and Accept JSON.
        """
        return {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Accept": "application/json",
        }

    # ---------- Low-level HTTP ----------
    def _get_json(self, url: str) -> dict:
        """Sends a GET request to a Graph API URL and returns the parsed JSON body.

        Args:
            url: Full Graph API URL to request.

        Returns:
            dict: Parsed JSON response body.

        Raises:
            RuntimeError: If the HTTP response indicates an error.
        """
        r = requests.get(url, headers=self._headers(), timeout=self.timeout)
        self._raise_for_status(r)
        return r.json()

    def _put_bytes(self, url: str, content: bytes) -> dict:
        """Sends a PUT request with binary content to a Graph API URL.

        Args:
            url: Full Graph API URL to upload to.
            content: Raw bytes to upload as the request body.

        Returns:
            dict: Parsed JSON response body from the Graph API.

        Raises:
            RuntimeError: If the HTTP response indicates an error.
        """
        r = requests.put(
            url,
            headers={**self._headers(), "Content-Type": "application/octet-stream"},
            data=content,
            timeout=self.timeout,
        )
        self._raise_for_status(r)
        return r.json()

    # ---------- SharePoint resolution ----------
    def get_site_id(self, force_refresh: bool = False) -> str:
        """Resolves and returns the Graph site ID for the configured SharePoint site.

        The result is cached on the instance after the first successful call.

        Args:
            force_refresh: If True, bypasses the cache and re-queries the API.
                Defaults to False.

        Returns:
            str: Graph site ID string.

        Raises:
            RuntimeError: If the API request fails.
        """
        if self._site_id and not force_refresh:
            return self._site_id

        # Prefer the explicit form ending in ":/" for robustness across tenants
        url = f"https://graph.microsoft.com/v1.0/sites/{self.config.sp_hostname}:/{self.config.sp_site_path}:/"
        site = self._get_json(url)
        self._site_id = site["id"]
        return self._site_id

    def get_drive_id(self, force_refresh: bool = False) -> str:
        """Resolves and returns the Graph drive ID for the configured document library.

        The result is cached on the instance after the first successful call.

        Args:
            force_refresh: If True, bypasses the cache and re-queries the API.
                Defaults to False.

        Returns:
            str: Graph drive ID string.

        Raises:
            RuntimeError: If the named drive is not found or the API request fails.
        """
        if self._drive_id and not force_refresh:
            return self._drive_id

        site_id = self.get_site_id()
        drives = self._get_json(f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives")

        for d in drives.get("value", []):
            if d.get("name") == self.config.drive_name:
                self._drive_id = d["id"]
                return self._drive_id

        available = [d.get("name") for d in drives.get("value", [])]
        raise RuntimeError(
            f"Drive '{self.config.drive_name}' not found. Available drives: {available}"
        )

    # ---------- Public API ----------
    def upload_file(self, local_path: str, sp_path_in_library: str) -> dict:
        """Uploads (creates or replaces) a file in the SharePoint document library.

        Uses a simple PUT request, suitable for files up to ~250MB.
        The destination folder must already exist in SharePoint.

        Args:
            local_path: Absolute or relative path to the local file to upload.
            sp_path_in_library: Target path within the document library root
                (e.g. "General/Reports/my_file.xlsx").

        Returns:
            dict: Graph API response body for the uploaded item (includes id,
                name, webUrl, etc.).

        Raises:
            RuntimeError: If the upload request fails.
            FileNotFoundError: If local_path does not exist.
        """
        site_id = self.get_site_id()
        drive_id = self.get_drive_id()

        with open(local_path, "rb") as f:
            content = f.read()

        encoded_path = self._encode_sp_path(sp_path_in_library)
        url = (
            f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}"
            f"/root:/{encoded_path}:/content"
        )
        return self._put_bytes(url, content)
