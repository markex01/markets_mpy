from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from ..utils.config_loader import AuroraApiConfig
from .client import AuroraHttpClient, ForecastRequest
from .processors import process_system_forecast, process_technology_forecast


class AuroraAPI:
    _registry_columns = ["name", "hash", "currency", "sensitivity", "region_code"]

    def __init__(
        self,
        token: str,
        scenario_comp_registry_path: Path | str,
        technology_db_path: Path | str,
        system_db_path: Path | str,
        country_code_list: Iterable[str] | None = None,
        http_client: AuroraHttpClient | None = None,
    ):
        """Initializes the AuroraAPI client and fetches available forecasts.

        On construction, loads the scenario component registry from disk and
        queries the Aurora API for available published scenarios.

        Args:
            token: Aurora API private token.
            scenario_comp_registry_path: Path to the JSON file tracking which
                scenarios have already been retrieved.
            technology_db_path: Path to the Parquet file storing technology
                scenario data.
            system_db_path: Path to the Parquet file storing system scenario data.
            country_code_list: Iterable of Aurora country/region codes to filter
                (e.g. ["esp", "gbr"]). Defaults to an empty list (no filter).
            http_client: Optional pre-configured AuroraHttpClient. A new one is
                created from the token if not provided.
        """
        self.token = token
        self.scenario_comp_registry_path = Path(scenario_comp_registry_path)
        self.technology_db_path = Path(technology_db_path)
        self.system_db_path = Path(system_db_path)
        self.country_code_list = list(country_code_list) if country_code_list is not None else []
        self.http_client = http_client or AuroraHttpClient(self.token)

        self.df_system_scenarios = pd.DataFrame()
        self.df_technology_scenarios = pd.DataFrame()
        self.df_currencies = pd.DataFrame()
        self.df_regions = pd.DataFrame()
        self.available_scenarios_df = pd.DataFrame()
        self.scenario_comp_registry = self._load_registry()

        self._retrieve_available_forecasts()

    @classmethod
    def from_config(
        cls,
        config: AuroraApiConfig,
        resolution: str = "1y",
        scenario_registry_path: Path | str | None = None,
        technology_db_path: Path | str | None = None,
        system_db_path: Path | str | None = None,
        country_code_list: Iterable[str] | None = None,
        http_client: AuroraHttpClient | None = None,
    ) -> "AuroraAPI":
        """Constructs an AuroraAPI instance from a configuration object.

        Path arguments override the defaults derived from the config.

        Args:
            config: AuroraApiConfig dataclass with token, country codes, and
                default paths.
            resolution: Data resolution to use for default paths ("1y", "1m",
                or "1h"). Defaults to "1y".
            scenario_registry_path: Override for the scenario registry path.
            technology_db_path: Override for the technology Parquet path.
            system_db_path: Override for the system Parquet path.
            country_code_list: Override for the list of country/region codes.
            http_client: Optional pre-configured AuroraHttpClient.

        Returns:
            AuroraAPI: Configured and initialised API instance.
        """
        scenario_path = scenario_registry_path or config.scenario_registry_path(resolution)
        technology_path = technology_db_path or config.technology_db_path(resolution)
        system_path = system_db_path or config.system_db_path(resolution)

        configured_countries = country_code_list or config.country_codes
        return cls(
            token=config.token,
            scenario_comp_registry_path=scenario_path,
            technology_db_path=technology_path,
            system_db_path=system_path,
            country_code_list=configured_countries,
            http_client=http_client,
        )

    def _load_registry(self) -> pd.DataFrame:
        """Loads the scenario component registry from the JSON file on disk.

        Returns:
            pd.DataFrame: Registry DataFrame. If the file does not exist,
                an empty registry file is created and returned.
        """
        if not self.scenario_comp_registry_path.exists():
            self.scenario_comp_registry_path.parent.mkdir(parents=True, exist_ok=True)
            df_empty = pd.DataFrame(columns=self._registry_columns)
            df_empty.to_json(self.scenario_comp_registry_path)
            return df_empty

        try:
            df_registry = pd.read_json(self.scenario_comp_registry_path)
        except Exception as error:
            print("Error reading scenario component registry:", error)
            return pd.DataFrame(columns=self._registry_columns)

        if df_registry.empty:
            return pd.DataFrame(columns=self._registry_columns)

        for column in self._registry_columns:
            if column not in df_registry.columns:
                df_registry[column] = pd.Series(dtype="object")

        return df_registry

    def _save_registry(self) -> None:
        """Persists the scenario component registry to disk."""
        self.scenario_comp_registry_path.parent.mkdir(parents=True, exist_ok=True)
        if self.scenario_comp_registry.empty and not self.scenario_comp_registry.columns.size:
            self.scenario_comp_registry = pd.DataFrame(columns=self._registry_columns)
        self.scenario_comp_registry.to_json(self.scenario_comp_registry_path)

    def _retrieve_available_forecasts(self) -> None:
        """Fetches available scenarios, currencies, and regions from the Aurora API.

        Populates self.available_scenarios_df, self.df_currencies, and
        self.df_regions in place.
        """
        payload = self.http_client.describe_available_forecasts()
        self.available_scenarios_df = pd.DataFrame(payload.get("scenarios", []))
        self.df_currencies = pd.DataFrame(payload.get("currencies", []))
        self.df_regions = pd.DataFrame(payload.get("regions", []))

    def retrieve_single_forecast(
        self,
        hash: str,
        region_code: str,
        sensitivity: str,
        type: str,
        currency_code: str,
        resolution: str,
    ) -> pd.DataFrame:
        """Downloads and processes a single Aurora forecast scenario.

        Args:
            hash: Aurora scenario hash identifier.
            region_code: Aurora region/country code (e.g. "esp").
            sensitivity: Scenario sensitivity label (e.g. "Central").
            type: Forecast type — "system" or "technology".
            currency_code: Currency code for price data (e.g. "EUR").
            resolution: Time resolution — "1y", "1m", or "1h".

        Returns:
            pd.DataFrame: Processed long-format DataFrame, or an empty DataFrame
                if the download fails or the type/resolution combination is
                not supported.
        """
        payload = ForecastRequest(
            hash=hash,
            region_code=region_code,
            sensitivity=sensitivity,
            forecast_type=type,
            currency_code=currency_code,
            resolution=resolution,
        )

        df = self.http_client.fetch_forecast(payload)
        if df.empty:
            return pd.DataFrame()

        if type == "technology" and resolution in {"1m", "1y"}:
            return process_technology_forecast(df, resolution)

        if type == "system":
            return process_system_forecast(df, resolution)

        return pd.DataFrame()

    def update_scenario_database(
        self,
        currency_code: str | None = None,
        resolution: str = "1y",
        country_code_list: Iterable[str] | None = None,
    ) -> "AuroraAPI":
        """Downloads all new published scenarios and appends them to the local Parquet files.

        Iterates over published scenarios for the given country codes. Scenarios
        already present in the registry are skipped. New scenarios are retrieved,
        metadata columns are attached, and the data is saved to disk.

        Args:
            currency_code: Currency to use for all downloads. If None, each
                scenario's default currency is used.
            resolution: Time resolution — "1y" (default), "1m", or "1h".
            country_code_list: Country/region codes to filter. Defaults to
                self.country_code_list or ["esp"] if empty.

        Returns:
            AuroraAPI: Returns self to allow method chaining.
        """
        if country_code_list is None:
            country_code_list = list(self.country_code_list) if self.country_code_list else ["esp"]
        else:
            country_code_list = list(country_code_list)

        df_concat_1 = pd.DataFrame()
        df_concat_2 = pd.DataFrame()
        df_scenarios = self.available_scenarios_df

        currency_bool = bool(currency_code)

        filtered = df_scenarios[
            (df_scenarios["publishType"] == "Published")
            & (df_scenarios["regionCode"].isin(country_code_list))
        ]

        for _, row in filtered.iterrows():
            hash_value = row["hash"]
            default_currency = row["defaultCurrency"]
            sensitivity = row["sensitivity"]
            region_code = row["regionCode"]
            name = row["name"]

            if not currency_bool:
                currency_code = default_currency

            existing_scenarios = set()
            if not self.scenario_comp_registry.empty:
                existing_scenarios = set(
                    zip(
                        self.scenario_comp_registry["hash"].astype(str),
                        self.scenario_comp_registry["region_code"].astype(str),
                    )
                )

            key = (str(hash_value), str(region_code))

            if key in existing_scenarios:
                print(f"Scenario {name} for region {region_code} already in registry, skipping retrieval.")
                continue

            new_row = {
                "name": name,
                "hash": hash_value,
                "currency": currency_code,
                "sensitivity": sensitivity,
                "region_code": region_code,
            }

            print(f"Retrieving data for scenario: {name} (region: {region_code})")
            df_temp_1 = self.retrieve_single_forecast(
                hash_value,
                region_code,
                sensitivity,
                "system",
                currency_code=currency_code,
                resolution=resolution,
            )

            if df_temp_1.empty:
                print(f"No data retrieved for scenario: {name} (region: {region_code})")
                continue

            df_temp_1["name"] = name
            df_temp_1["currency"] = currency_code
            df_temp_1["sensitivity"] = sensitivity
            df_temp_1["region_code"] = region_code

            df_concat_1 = pd.concat([df_concat_1, df_temp_1], ignore_index=True)

            df_temp_2 = self.retrieve_single_forecast(
                hash_value,
                region_code,
                sensitivity,
                "technology",
                currency_code=currency_code,
                resolution=resolution,
            )

            if df_temp_2.empty:
                print(f"No data retrieved for scenario: {name}")
                continue

            df_temp_2["name"] = name
            df_temp_2["currency"] = currency_code
            df_temp_2["sensitivity"] = sensitivity
            df_temp_2["region_code"] = region_code

            df_concat_2 = pd.concat([df_concat_2, df_temp_2], ignore_index=True)

            self.scenario_comp_registry = pd.concat(
                [self.scenario_comp_registry, pd.DataFrame([new_row])],
                ignore_index=True,
            )

        if (df_concat_1.empty or df_concat_2.empty) and resolution != "1h":
            print("No new data retrieved.")
            self._save_registry()
            return self

        if not df_concat_1.empty:
            self.df_system_scenarios = df_concat_1
        if not df_concat_2.empty:
            self.df_technology_scenarios = df_concat_2

        self._save_registry()

        self.concat_existing_data(self.df_system_scenarios, self.system_db_path)
        self.concat_existing_data(self.df_technology_scenarios, self.technology_db_path)

        return self

    def concat_existing_data(self, df_new: pd.DataFrame, path_existing: Path | str) -> None:
        """Appends new data to an existing Parquet file, deduplicating in place.

        If the target file does not exist or cannot be read, the new data is
        written as-is. Duplicates are dropped keeping the last occurrence.

        Args:
            df_new: DataFrame containing new rows to append.
            path_existing: Path to the existing Parquet file.
        """
        target_path = Path(path_existing)
        try:
            df_existing = pd.read_parquet(target_path)
        except Exception as error:
            print("Error reading existing data:", error)
            df_existing = pd.DataFrame()

        if not df_existing.empty:
            df_new = pd.concat([df_existing, df_new], ignore_index=True)

        df_new.drop_duplicates(keep="last", inplace=True)
        df_new.to_parquet(target_path, index=False)
