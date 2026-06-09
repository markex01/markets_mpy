# Aurora API — Implementation Tutorial

This project exposes Aurora Energy Research data through **two separate packages** with different purposes:

| Package | Purpose | Persistence |
|---|---|---|
| `aurora_api` | Stateless retrieval client — one call, one DataFrame | None (in-memory only) |
| `aurora_forecasts` | Full data pipeline — incremental Parquet database, registry, processing | Parquet + JSON registry |

Choose `aurora_api` for ad-hoc exploration and `aurora_forecasts` for production pipelines.

---

## Part 1 — `aurora_api` (stateless client)

### Installation

Both packages are installed in editable mode from the repo root:

```bash
pip install -e packages/aurora_api -e packages/aurora_forecasts -e packages/common_libs
```

### 1.1 High-level facade: `AuroraAPI`

```python
from aurora_api import AuroraAPI

api = AuroraAPI(
    token="YOUR_AURORA_TOKEN",
    country_codes=["esp", "gbr", "prt"],  # filter to these regions
)
```

**Explore available scenarios:**

```python
scenarios = api.list_scenarios()
print(scenarios[["name", "hash", "regionCode", "sensitivity", "defaultCurrency"]])
```

The `hash` column is the unique identifier you pass to `fetch_forecast`.

**List regions and currencies:**

```python
regions    = api.list_regions()
currencies = api.list_currencies()
```

**Fetch a forecast:**

```python
df = api.fetch_forecast(
    hash="<scenario-hash>",
    region_code="esp",        # must match a region in the scenario
    sensitivity="central",    # "central" | "low" | "high"
    forecast_type="system",   # "system" | "technology"
    currency_code="eur2024",  # "eur2024" | "gbp2024" | "pln2024"
    resolution="1y",          # "1y" | "1m" | "1h"
)
```

> **Note:** `forecast_type="technology"` is only valid for `resolution="1y"` and `"1m"`. Use `"system"` for `"1h"`.

The returned DataFrame is already in **long format** — no further melting required.

---

### 1.2 Parameter reference

| Parameter | Type | Valid values | Notes |
|---|---|---|---|
| `hash` | `str` | UUID from `list_scenarios()` | Identifies the scenario release |
| `region_code` | `str` | `"esp"`, `"gbr"`, `"prt"`, `"ita"`, `"fra"`, `"deu"`, `"pol"`, … | Must be published for that scenario |
| `sensitivity` | `str` | `"central"`, `"low"`, `"high"` | Not all scenarios have all three |
| `forecast_type` | `str` | `"system"`, `"technology"` | `"technology"` only for `1y`/`1m` |
| `currency_code` | `str` | `"eur2024"`, `"gbp2024"`, `"pln2024"` | Real (inflation-adjusted) currencies |
| `resolution` | `str` | `"1y"`, `"1m"`, `"1h"` | Hourly data is large — fetch short ranges |

---

### 1.3 Output format

**System forecast** (`forecast_type="system"`) → long DataFrame:

| Column | Description |
|---|---|
| `year` / `month` / `datetime` | Time column (depends on `resolution`) |
| `variable` | Metric name, e.g. `"Power Price"`, `"Demand"` |
| `value` | Numeric value |
| `units` | Unit string, e.g. `"EUR/MWh"`, `"GW"` |

**Technology forecast** (`forecast_type="technology"`) → long DataFrame:

| Column | Description |
|---|---|
| `year` / `month` | Time column |
| `Group` | Technology group, e.g. `"Solar"`, `"Wind Onshore"` |
| `Subgroup` | Detailed sub-category |
| `type` | `"Installed Capacity"`, `"Generation"`, etc. |
| `value` | Numeric value |
| `unit` | Unit string |

---

### 1.4 Low-level client: `AuroraHttpClient`

Use this to access the raw CSV response or when you need more control:

```python
from aurora_api.client import AuroraHttpClient, ForecastRequest

request = ForecastRequest(
    hash="<scenario-hash>",
    region_code="esp",
    sensitivity="central",
    forecast_type="system",
    currency_code="eur2024",
    resolution="1y",
)

client = AuroraHttpClient(token="YOUR_AURORA_TOKEN")

# Returns raw DataFrame (CSV decoded, no post-processing)
raw_df = client.fetch_forecast(request)

# Returns the full available-forecasts JSON as a dict
metadata = client.describe_available_forecasts()
```

`ForecastRequest` is a frozen dataclass — all fields are required.

---

### 1.5 Processors

If you use the raw client, apply processors manually:

```python
from aurora_api.processors import process_system_forecast, process_technology_forecast

# For system forecasts
long_df = process_system_forecast(raw_df, resolution="1y")

# For technology forecasts
long_df = process_technology_forecast(raw_df, resolution="1m")
```

---

## Part 2 — `aurora_forecasts` (persistent pipeline)

This package wraps the same HTTP client but adds:
- A **JSON scenario registry** to avoid re-fetching already downloaded scenarios.
- **Parquet storage** for accumulated historical data.
- Helper utilities for processing, unit conversion, and plotting.

### 2.1 Configuration

Config is loaded from `config/aurora/api_params.yaml`:

```yaml
# config/aurora/api_params.yaml
aurora_token: "<placeholder>"          # override with AURORA_TOKEN env var
country_code_list:
  - pol
  - ita
  - deu
  - gbr
  - esp
  - fra
  - prt
```

The token should be stored in your `.env` file as `AURORA_TOKEN` and **never committed** to the repository. The YAML value serves only as a local fallback.

Load the config in a notebook:

```python
from aurora_forecasts import load_api_params

config = load_api_params("../../../config/aurora/api_params.yaml")
```

`load_api_params` returns an `AuroraApiConfig` frozen dataclass with these fields:

| Field | Type | Description |
|---|---|---|
| `token` | `str` | API token (from env var or YAML) |
| `country_codes` | `tuple[str, ...]` | Country codes to retrieve |
| `root` | `Path` | Base path for data storage |
| `technology_paths` | `dict` | Parquet paths per resolution |
| `system_paths` | `dict` | Parquet paths per resolution |

---

### 2.2 `AuroraAPI` — persistent retrieval

```python
from aurora_forecasts import AuroraAPI, load_api_params

config = load_api_params("../../../config/aurora/api_params.yaml")

# Instantiate for a specific resolution
api = AuroraAPI.from_config(config, resolution="1y")
```

On instantiation the API client:
1. Loads the JSON scenario registry from disk (tracks what has already been fetched).
2. Calls the Aurora API to fetch the list of available scenarios/regions/currencies.

**Inspect available scenarios:**

```python
print(api.available_scenarios_df[["name", "hash", "regionCode", "sensitivity"]])
```

**Fetch a single forecast** (returns a processed DataFrame, does not update Parquet):

```python
df = api.retrieve_single_forecast(
    hash="<scenario-hash>",
    region_code="esp",
    sensitivity="central",
    type="system",           # note: parameter is named `type` here, not `forecast_type`
    currency_code="eur2024",
    resolution="1y",
)
```

---

### 2.3 Updating the database (main pipeline entry point)

`update_scenario_database` is the method you call in the scheduled/incremental pipeline. It:
1. Iterates over all published scenarios for the configured country codes.
2. Skips any `(hash, region, sensitivity)` combination already in the JSON registry.
3. Fetches both `system` and `technology` forecasts for new entries.
4. Appends results to the Parquet files (deduplication-aware).
5. Updates the JSON registry.

```python
api.update_scenario_database(
    currency_code="eur2024",
    resolution="1y",
    country_code_list=config.country_codes,   # optional override
)
```

> **Typical usage:** run this once per quarter after a new Aurora release.

---

### 2.4 Reading stored data

After the database has been updated, read data directly from Parquet:

```python
import pandas as pd

system_path = config.system_db_path("1y")      # e.g. data/aurora/aurora2_system_1y.parquet
tech_path   = config.technology_db_path("1y")  # e.g. data/aurora/aurora2_technology_1y.parquet

df_system = pd.read_parquet(system_path)
df_tech   = pd.read_parquet(tech_path)
```

---

### 2.5 Unit conversion

Technology DataFrames may contain GW/TWh values. Convert them to MW/GWh with:

```python
from aurora_forecasts.processing.unit_conversion import convert_units

unit_map = {"GW": "MW", "TWh": "GWh"}   # example
df_converted = convert_units(df_tech, unit_conversion_map=unit_map)
```

---

### 2.6 Plotting

```python
from aurora_forecasts.retrieval_helper.plotting import plot_aurora_with_actuals_month

fig = plot_aurora_with_actuals_month(df_forecast, df_actuals, region_code="esp")
fig.show()
```

---

## Part 3 — Notebook pipeline overview

The `notebooks/aurora_forecasts/forecasts/` folder implements a numbered pipeline:

| Step | Notebook | Action |
|---|---|---|
| 0 | `0_aurora_1.ipynb` | Ad-hoc exploration with `aurora_api` (no persistence) |
| 1 | `1a_aurora_forecasts.ipynb` | **Retrieve** — calls `update_scenario_database()` for `1y` and `1m` resolutions |
| 2a | `2a_aurora_forecast_prices_processing_yearly.ipynb` | **Process** — inflation adjust, pivot, export Excel |
| 2b | `2b_aurora_forecast_processing_monthly.ipynb` | Monthly price processing |
| 2c–2e | `2c/2d/2e_*.ipynb` | Curtailment / technology / demand processing |
| 3a | `3a_sharepoint_data_prices_processing_yearly.ipynb` | Pull SharePoint-sourced data |
| 4a | `4a_process_merged_prices.ipynb` | Merge actuals with forecasts |

Run notebooks **in order** within each session. Step 1 must complete before any Step 2+ notebook.

---

## Part 4 — Complete minimal example

```python
# ── Ad-hoc exploration (no disk I/O) ──────────────────────────────────────
from aurora_api import AuroraAPI

api = AuroraAPI(token="YOUR_AURORA_TOKEN", country_codes=["esp", "prt"])

scenarios = api.list_scenarios()
print(scenarios[["name", "hash", "regionCode", "sensitivity"]].head(10))

target_hash = scenarios.loc[scenarios["regionCode"] == "esp", "hash"].iloc[0]

df = api.fetch_forecast(
    hash=target_hash,
    region_code="esp",
    sensitivity="central",
    forecast_type="system",
    currency_code="eur2024",
    resolution="1y",
)
print(df.head())
```

```python
# ── Persistent pipeline (Parquet database) ────────────────────────────────
from aurora_forecasts import AuroraAPI, load_api_params
import pandas as pd

config = load_api_params("../../../config/aurora/api_params.yaml")
api    = AuroraAPI.from_config(config, resolution="1y")

# Incremental update — only fetches what is new since last run
api.update_scenario_database(currency_code="eur2024", resolution="1y")

# Load resulting data
df = pd.read_parquet(config.system_db_path("1y"))
print(df.shape, df.columns.tolist())
```

---

## Part 5 — Common pitfalls

| Pitfall | Correct approach |
|---|---|
| Hardcoding the API token | Store in `.env` as `AURORA_TOKEN`; never commit the token |
| Using `resolution="1h"` with `forecast_type="technology"` | `"technology"` is only valid for `"1y"` and `"1m"` |
| Expecting wide-format output | Both processors return **long format** — pivot yourself if needed |
| Running Step 2+ notebooks before Step 1 | Always run `1a_aurora_forecasts.ipynb` first to populate the Parquet files |
| Hardcoding absolute paths | Use `os.path.abspath()` relative to the notebook or resolve via `config` |
| Importing `aurora_forecasts.AuroraAPI` when you only need `aurora_api.AuroraAPI` | The two classes have the same name but different contracts — `aurora_forecasts.AuroraAPI` requires a registry path and manages state on disk |
