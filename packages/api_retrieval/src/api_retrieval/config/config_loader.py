import yaml
from pathlib import Path

class Config:
    def __init__(self, config_file="../../configs/config.yaml"):
        """Initializes the Config object and loads the YAML configuration file.

        Args:
            config_file (str): Path to the YAML configuration file. Can be
                relative (resolved against the current working directory) or
                absolute. Defaults to "../../configs/config.yaml".

        Raises:
            FileNotFoundError: If the config file does not exist at the
                resolved path.
            KeyError: If the "base_path" key is missing from the YAML file.
        """
        # Store the config file path (absolute, but we will NOT use its parent to resolve other paths)
        self._config_file = str(Path(config_file).resolve())
        self._config = None
        self._load_config()

    def _load_config(self):
        """Loads the configuration file into memory and validates required keys.

        Raises:
            FileNotFoundError: If the config file does not exist.
            KeyError: If the "base_path" key is missing from the YAML file.
        """
        cfg_path = Path(self._config_file)
        if not cfg_path.exists():
            raise FileNotFoundError(f"Config file not found: {self._config_file}")

        with cfg_path.open("r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f) or {}

        # Ensure base_path exists in YAML (explicit requirement)
        if "base_path" not in self._config:
            raise KeyError("Missing required key 'base_path' in configuration YAML.")

        # Normalize base_path but DO NOT tie it to the config file's folder
        raw_base = str(self._config["base_path"]).strip()
        self._base_path = Path(raw_base)
        # Make sure base_path is absolute (if not, resolve relative to current working dir)
        if not self._base_path.is_absolute():
            self._base_path = self._base_path.resolve()

    @property
    def base_dir(self) -> str:
        """Returns the absolute base directory specified in the YAML file.

        Returns:
            str: Absolute path to the base directory.
        """
        return str(self._base_path)

    def get(self, key, default=None):
        """Retrieves a value from the configuration using a dot-separated key.

        Args:
            key (str): Dot-separated key path (e.g. "data_path.elec.processed.folder").
            default: Value to return if the key is not found. Defaults to None.

        Returns:
            The value at the specified key path, or default if not found.
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if not isinstance(value, dict):
                return default
            value = value.get(k, default)
        return value

    def get_path(self, key, **kwargs) -> str:
        """Retrieves and resolves a path from the configuration using base_path as root.

        - If the configured value (after formatting) is absolute, return it as-is.
        - If it is relative, join it to base_path and resolve.

        Args:
            key (str): Dot-separated key for the path (e.g. 'data_path.elec.processed.folder').
            kwargs: Dynamic variables to format the path (e.g. {year}, {month}, {cliente}).

        Returns:
            str: The resolved absolute path.

        Raises:
            KeyError: If the key is not found in the configuration, or if a
                placeholder in the path value cannot be filled from kwargs.
            TypeError: If the value at the key is not a string.
        """
        value = self.get(key)
        if value is None:
            raise KeyError(f"Key '{key}' not found in configuration.")
        if not isinstance(value, str):
            raise TypeError(f"Key '{key}' does not contain a valid path string.")

        # 1) Format placeholders
        try:
            formatted = value.format(**kwargs).strip()
        except KeyError as e:
            raise KeyError(f"Missing dynamic variable for placeholder in '{key}': {str(e)}")

        p = Path(formatted)

        # 2) Respect explicit absolute paths (allow per-entry overrides)
        if p.is_absolute():
            return str(p.resolve())

        # 3) Otherwise, resolve relative to base_path ONLY (never to config file parent)
        return str((self._base_path / p).resolve())

    def get_resolved_path(self, key, **kwargs) -> str:
        """Retrieves and validates a path, ensuring it exists on disk.

        Args:
            key (str): Dot-separated key for the path.
            kwargs: Dynamic variables to format the path.

        Returns:
            str: The resolved absolute path.

        Raises:
            FileNotFoundError: If the resolved path does not exist.
        """
        resolved_path = self.get_path(key, **kwargs)
        if not Path(resolved_path).exists():
            raise FileNotFoundError(f"Resolved path does not exist: {resolved_path}")
        return resolved_path
