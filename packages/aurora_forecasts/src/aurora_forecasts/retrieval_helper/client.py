from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import Optional

import pandas as pd
import requests


@dataclass(frozen=True)
class ForecastRequest:
    hash: str
    region_code: str
    sensitivity: str
    forecast_type: str
    currency_code: str
    resolution: str


class AuroraHttpClient:
    _BASE_URL = "https://api.auroraer.com/scenarioExplr/v1/scenarios"

    def __init__(self, token: str, session: Optional[requests.Session] = None):
        """Initializes the Aurora HTTP client with authentication headers.

        Args:
            token: Aurora API private token used for authentication.
            session: Optional pre-configured requests.Session. A new session
                is created if not provided.
        """
        self.session = session or requests.Session()
        self.session.headers.update({
            "accept": "text/csv",
            "Private-Token": token,
        })

    def describe_available_forecasts(self) -> dict[str, list[dict[str, str]]]:
        """Fetches the list of available forecast scenarios from the Aurora API.

        Returns:
            dict[str, list[dict[str, str]]]: Parsed JSON payload containing
                lists of scenarios, currencies, and regions. Returns an empty
                dict if the request fails.
        """
        response = self.session.get(self._BASE_URL)
        if response.status_code != 200:
            print("Unable to load available forecasts:", response.status_code)
            return {}
        return response.json()

    def fetch_forecast(self, request: ForecastRequest) -> pd.DataFrame:
        """Downloads a single forecast CSV and returns it as a DataFrame.

        Args:
            request: ForecastRequest dataclass specifying the scenario hash,
                region, sensitivity, forecast type, currency, and resolution.

        Returns:
            pd.DataFrame: Parsed CSV content as a DataFrame, or an empty
                DataFrame if the download fails or the payload is empty.
        """
        url = (
            f"{self._BASE_URL}/pmf/{request.hash}/{request.region_code}/"
            f"{request.sensitivity}/{request.currency_code}-"
            f"{request.forecast_type}-{request.resolution}.csv"
        )
        response = self.session.get(url)

        if response.status_code != 200:
            print("Forecast download failed:", response.status_code)
            return pd.DataFrame()

        try:
            return pd.read_csv(StringIO(response.text))
        except pd.errors.EmptyDataError:
            print("Received empty payload from Aurora API.")
        except Exception as error:
            print("Unable to parse forecast payload:", error)
        return pd.DataFrame()
