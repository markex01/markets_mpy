from __future__ import annotations

import pandas as pd
import requests

from .client import AuroraHttpClient, ForecastRequest
from .processors import process_system_forecast, process_technology_forecast


class AuroraAPI:
    """Simplified Aurora Energy Research API client.

    Provides two operations:
      1. List available published forecast scenarios.
      2. Fetch a single forecast scenario as a long-format DataFrame.

    No data is written to disk. Each call to :meth:`fetch_forecast` returns
    an independent DataFrame, which is intentional for large resolutions
    such as hourly data.

    Example usage::

        from aurora_api import AuroraAPI

        api = AuroraAPI(token="YOUR_TOKEN", country_codes=["esp", "gbr"])

        scenarios = api.list_scenarios()
        print(scenarios[["name", "hash", "regionCode", "sensitivity", "defaultCurrency"]])

        df = api.fetch_forecast(
            hash="<hash_from_scenarios>",
            region_code="esp",
            sensitivity="Central",
            forecast_type="system",
            currency_code="EUR",
            resolution="1h",
        )
        print(df.head())
    """

    def __init__(
        self,
        token: str,
        country_codes: list[str] | None = None,
        session: requests.Session | None = None,
    ):
        """Initializes the AuroraAPI client.

        Args:
            token: Aurora API private token.
            country_codes: Optional list of Aurora region codes to filter
                when calling :meth:`list_scenarios` (e.g. ``["esp", "gbr"]``).
                If empty or None, all regions are returned.
            session: Optional pre-configured requests.Session.
        """
        self.country_codes = list(country_codes) if country_codes else []
        self._client = AuroraHttpClient(token=token, session=session)

    def list_scenarios(self) -> pd.DataFrame:
        """Returns all published forecast scenarios available on the API.

        Filters by :attr:`country_codes` if provided.

        Returns:
            pd.DataFrame: Published scenarios with columns including ``name``,
                ``hash``, ``regionCode``, ``sensitivity``, and
                ``defaultCurrency``. Returns an empty DataFrame if the API
                call fails.
        """
        payload = self._client.describe_available_forecasts()
        df = pd.DataFrame(payload.get("scenarios", []))
        if df.empty:
            return df

        df = df[df["publishType"] == "Published"]
        if self.country_codes:
            df = df[df["regionCode"].isin(self.country_codes)]
        return df.reset_index(drop=True)

    def list_regions(self) -> pd.DataFrame:
        """Returns all regions available on the API.

        Returns:
            pd.DataFrame: Regions available on the Aurora API.
        """
        payload = self._client.describe_available_forecasts()
        return pd.DataFrame(payload.get("regions", []))

    def list_currencies(self) -> pd.DataFrame:
        """Returns all currencies available on the API.

        Returns:
            pd.DataFrame: Currencies available on the Aurora API.
        """
        payload = self._client.describe_available_forecasts()
        return pd.DataFrame(payload.get("currencies", []))

    def fetch_forecast(
        self,
        hash: str,
        region_code: str,
        sensitivity: str,
        forecast_type: str,
        currency_code: str,
        resolution: str,
    ) -> pd.DataFrame:
        """Downloads and parses a single Aurora forecast scenario.

        Each call is independent — no data is cached or written to disk.
        For hourly resolution (``"1h"``), only ``forecast_type="system"``
        is supported by the Aurora API.

        Args:
            hash: Scenario hash identifier (from :meth:`list_scenarios`).
            region_code: Aurora region code: ``"esp"``, ``"gbr"``, ``"fra"``, ``"prt"``, ``"ita"``, ``"ita"``, ``"pol"``, ``"irx"``, ``"ita_cal"``, ``"ita_cnor"``, ``"ita_csud"``, ``"ita_sar"``, ``"ita_sic"``, ``"ita_sud"`` .
            sensitivity: Scenario sensitivity label, e.g. ``"central"``, ``"low"``, ``"high"``.
            forecast_type: Either ``"system"`` or ``"technology"``.
                Note: ``"technology"`` is only available for ``"1y"`` and
                ``"1m"`` resolutions.
            currency_code: Currency for price data, e.g. ``"eur2024"``, ``"gbp2024"``, ``"pln2024"``.
            resolution: Time resolution — ``"1y"``, ``"1m"``, or ``"1h"``.

        Returns:
            pd.DataFrame: Parsed long-format DataFrame, or an empty DataFrame
                if the download fails or the combination is not supported.
        """
        request = ForecastRequest(
            hash=hash,
            region_code=region_code,
            sensitivity=sensitivity,
            forecast_type=forecast_type,
            currency_code=currency_code,
            resolution=resolution,
        )

        df_raw = self._client.fetch_forecast(request)
        if df_raw.empty:
            return pd.DataFrame()

        if forecast_type == "technology":
            if resolution not in {"1y", "1m"}:
                print(f"Technology forecasts are not available at '{resolution}' resolution.")
                return pd.DataFrame()
            return process_technology_forecast(df_raw, resolution)

        if forecast_type == "system":
            return process_system_forecast(df_raw, resolution)

        print(f"Unknown forecast_type '{forecast_type}'. Use 'system' or 'technology'.")
        return pd.DataFrame()
