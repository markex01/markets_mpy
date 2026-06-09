from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml

from common_libs.sp.env import require_env
from common_libs.sp.graph_client import SharePointConfig


@dataclass(frozen=True)
class AzureConfig:
    tenant_id: str
    client_id: str
    client_secret: str


def _default_yaml_path() -> Path:
    """Returns the default YAML config path for the common_libs package.

    Resolves relative to this file's location so the path is correct
    regardless of the current working directory.

    Returns:
        Path: ``<common_libs_repo_root>/config/ms_config.yaml``.
    """
    # settings.py is at: common_libs/src/common_libs/sp/settings.py
    # repo root is: parents[3] => .../common_libs
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "config" / "ms_config.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    """Loads and parses a YAML file, raising a descriptive error if missing.

    Args:
        path: Absolute or relative path to the YAML file to load.

    Returns:
        Dict[str, Any]: Parsed YAML content, or an empty dict if the file
        is empty or contains only null.

    Raises:
        RuntimeError: If the file does not exist at ``path``, with a hint
            to set the ``MS_CONFIG_PATH`` environment variable.
    """
    if not path.exists():
        raise RuntimeError(
            f"Config file not found at: {path}\n"
            "Set MS_CONFIG_PATH to override the location."
        )
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_ms_config() -> tuple[AzureConfig, SharePointConfig]:
    """Loads Microsoft/Azure config from YAML and injects secrets from the environment.

    YAML path resolution order:

    1. ``MS_CONFIG_PATH`` environment variable (recommended for multi-project use).
    2. ``<common_libs_repo>/config/ms_config.yaml`` (default).

    The ``AZURE_CLIENT_SECRET`` is always read from the environment; it is
    never stored in the YAML file.

    Returns:
        tuple[AzureConfig, SharePointConfig]: A 2-tuple of frozen dataclasses
        containing Azure tenant/client IDs and the SharePoint site configuration.

    Raises:
        RuntimeError: If the YAML config file cannot be found, or if the
            ``AZURE_CLIENT_SECRET`` environment variable is not set.
        KeyError: If required keys (``azure``, ``sharepoint``) are absent
            from the YAML file.
    """
    yaml_path = Path(os.environ.get("MS_CONFIG_PATH", _default_yaml_path()))
    raw = _load_yaml(yaml_path)

    # ----- Azure (IDs in YAML, secret in env) -----
    azure = AzureConfig(
        tenant_id=raw["azure"]["tenant_id"],
        client_id=raw["azure"]["client_id"],
        client_secret=require_env("AZURE_CLIENT_SECRET"),
    )

    # ----- SharePoint -----
    sp_raw = raw["sharepoint"]
    sp_cfg = SharePointConfig(
        tenant_id=azure.tenant_id,
        client_id=azure.client_id,
        client_secret=azure.client_secret,
        sp_hostname=sp_raw["hostname"],
        sp_site_path=sp_raw["site_path"],
        drive_name=sp_raw.get("drive_name", "Documents"),
    )

    return azure, sp_cfg

