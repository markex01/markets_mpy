from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

_CONFIG_ENV_PATH = "AURORA_API_PARAMS_PATH"
_TOKEN_ENV = "AURORA_TOKEN"


def _project_root() -> Path:
    """Returns the aurora_forecasts package root directory.

    Resolves relative to this file's location, so it works regardless of
    the current working directory.

    Returns:
        Path: Absolute path to the aurora_forecasts package root.
    """
    return Path(__file__).resolve().parents[2]


def _default_api_params_path(root: Path) -> Path:
    """Returns the default path for the Aurora API parameters YAML file.

    Args:
        root (Path): Package root directory.

    Returns:
        Path: Path to ``<root>/config/api_params.yaml``.
    """
    return root / "config" / "api_params.yaml"


def _default_technology_paths(root: Path) -> Mapping[str, Path]:
    """Returns the default Parquet paths for technology scenario data by resolution.

    Args:
        root (Path): Package root directory.

    Returns:
        Mapping[str, Path]: Dict mapping resolution codes ("1y", "1m") to
            their corresponding Parquet file paths.
    """
    return {
        "1y": root / "data" / "aurora2_technology_scenarios_ES_default_currency_1y.parquet",
        "1m": root / "data" / "raw" / "aurora_technology_scenarios_ES_default_currency_1m.parquet",
    }


def _default_system_paths(root: Path) -> Mapping[str, Path]:
    """Returns the default Parquet paths for system scenario data by resolution.

    Args:
        root (Path): Package root directory.

    Returns:
        Mapping[str, Path]: Dict mapping resolution codes ("1y", "1m") to
            their corresponding Parquet file paths.
    """
    return {
        "1y": root / "data" / "aurora2_system_scenarios_ES_default_currency_1y.parquet",
        "1m": root / "data" / "raw" / "aurora_system_scenarios_ES_default_currency_1m.parquet",
    }


def _default_registry_path(root: Path, resolution: str) -> Path:
    """Returns the default path for the scenario component registry JSON file.

    Args:
        root (Path): Package root directory.
        resolution (str): Data resolution. "1h" uses a separate registry
            file; all other resolutions share the "1y" registry.

    Returns:
        Path: Path to the registry JSON file.
    """
    suffix = "1h" if resolution == "1h" else "1y"
    return root / "data" / f"aurora_scenario_components_registry_{suffix}.json"


@dataclass(frozen=True)
class AuroraApiConfig:
    token: str
    country_codes: tuple[str, ...]
    root: Path
    technology_paths: Mapping[str, Path]
    system_paths: Mapping[str, Path]

    def scenario_registry_path(self, resolution: str = "1y") -> Path:
        """Returns the scenario component registry path for the given resolution.

        Args:
            resolution (str): Data resolution ("1y", "1m", or "1h").
                Defaults to "1y".

        Returns:
            Path: Path to the registry JSON file.
        """
        return _default_registry_path(self.root, resolution)

    def technology_db_path(self, resolution: str = "1y") -> Path:
        """Returns the technology Parquet database path for the given resolution.

        Falls back to the "1y" path if the resolution is not found.

        Args:
            resolution (str): Data resolution ("1y" or "1m"). Defaults to "1y".

        Returns:
            Path: Path to the technology Parquet file.
        """
        return self.technology_paths.get(resolution, self.technology_paths["1y"])

    def system_db_path(self, resolution: str = "1y") -> Path:
        """Returns the system Parquet database path for the given resolution.

        Falls back to the "1y" path if the resolution is not found.

        Args:
            resolution (str): Data resolution ("1y" or "1m"). Defaults to "1y".

        Returns:
            Path: Path to the system Parquet file.
        """
        return self.system_paths.get(resolution, self.system_paths["1y"])


def load_api_params(path: Path | str | None = None) -> AuroraApiConfig:
    """Loads Aurora API configuration from a YAML file and environment variables.

    Config path resolution order:
      1. The ``path`` argument (if provided).
      2. The ``AURORA_API_PARAMS_PATH`` environment variable.
      3. ``<package_root>/config/api_params.yaml`` (default).

    The Aurora API token is read from the ``AURORA_TOKEN`` environment variable,
    falling back to the ``aurora_token`` key in the YAML file if the variable
    is not set.

    Args:
        path: Optional explicit path to the YAML config file.

    Returns:
        AuroraApiConfig: Frozen dataclass with token, country codes, and
            resolved data paths.
    """
    root = _project_root()
    config_path = Path(
        path
        or os.environ.get(_CONFIG_ENV_PATH)
        or _default_api_params_path(root)
    )

    with config_path.open("r", encoding="utf-8") as handler:
        raw = yaml.safe_load(handler)

    token = os.environ.get(_TOKEN_ENV, raw.get("aurora_token", ""))
    country_codes = tuple(raw.get("country_code_list", ["esp"]))

    technology_paths = _default_technology_paths(root)
    system_paths = _default_system_paths(root)

    return AuroraApiConfig(
        token=token,
        country_codes=country_codes,
        root=root,
        technology_paths=technology_paths,
        system_paths=system_paths,
    )
