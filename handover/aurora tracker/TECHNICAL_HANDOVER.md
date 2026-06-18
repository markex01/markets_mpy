# 🛠️ Technical Handover — Python Unified (Aurora focus)

**Audience:** the developer taking over this codebase.
**Assumes:** Python, pandas, Jupyter, git, basic API/SharePoint familiarity.
**Companion docs:** [00_START_HERE.md](00_START_HERE.md) (orientation + credential checklist), [AURORA_QUARTERLY_RUNBOOK.md](AURORA_QUARTERLY_RUNBOOK.md) (the non-technical operating procedure).

This document covers how the Aurora pipeline actually works, the non-obvious wiring, the known issues, and the backlog.

---

## 1. Repository at a glance

```
Python Unified/
├── packages/                      # 4 installable packages (editable installs)
│   ├── common_libs/               #   finance (FX/inflation), sp (SharePoint/Graph), utils
│   ├── api_retrieval/             #   Exus-DB ETL (used) · ESIOS/ENTSO-E/AEMET (not currently in use)
│   ├── aurora_forecasts/          #   ★ THE AURORA PACKAGE — all Aurora code lives here
│   └── bloomberg/                 #   Bloomberg Terminal + BNEF
├── notebooks/                     # the actual workflows, numbered by step
│   ├── aurora_forecasts/forecasts # ★ the quarterly Aurora pipeline (1a → 2x → 3a)
│   ├── aurora_forecasts/actuals   # 1a_retrieve_actuals
│   ├── api_retrieval/{entsoe,esios,exus,meteo}
│   └── bloomberg/
├── config/
│   ├── aurora/api_params.yaml     # ★ Aurora token + country list (TOKEN STORED HERE)
│   ├── aurora/ms_config.yaml      # (legacy) automated SharePoint-upload config — NOT used; publishing is manual
│   └── api_retrieval/*.yaml       # api_retrieval configs (ENTSO-E/AEMET pipelines not used)
├── data/                          # ★ on-disk data root (NOT notebooks/data — see §2)
│   └── aurora/{,raw,processed}/   # parquet (raw scenarios) + pkl/xlsx (processed)
├── outputs/trackers/              # generated Excel trackers (prices, curtailment…) + heatmap_data.xlsx
└── README.md                      # top-level project overview (maintained separately)
```

Install (Python 3.10, conda recommended):
```bash
conda create -n python-unified python=3.10 -y && conda activate python-unified
pip install -e packages/common_libs -e packages/api_retrieval -e packages/aurora_forecasts -e packages/bloomberg
pip install ipykernel jupyterlab
```

---

## 2. ⚠️ Non-obvious wiring (gotchas the code won't tell you)

A few things about how the pipeline is wired that will trip you up if you assume the obvious:

1. **There is only ONE Aurora package: `aurora_forecasts`.** If you find any reference (in old notebooks, emails, or git history) to a package called **`aurora_api`** with imports like `from aurora_api import AuroraAPI` — **it does not exist on disk and never shipped.** The low-level stateless client (`AuroraHttpClient` + `ForecastRequest`) lives at `aurora_forecasts.retrieval_helper.client`. Everything you actually run is the `aurora_forecasts` path.

2. **The data root is the top-level `data/` directory** (not `notebooks/data/`). Notebooks reach it via the relative prefix `../../../data/...` because they run from `notebooks/aurora_forecasts/forecasts/`.

3. **The token is read straight from YAML, not from `AURORA_TOKEN`.** The package's `load_api_params()` *does* prefer the `AURORA_TOKEN` env var (`config_loader.py:161`), **but the actual retrieval notebook `1a` does not use `load_api_params()`** — it does `yaml.safe_load(open('.../config/aurora/api_params.yaml'))['aurora_token']` directly. So in practice the live credential is the plain-text value in `config/aurora/api_params.yaml`.

4. **`config_loader` default paths don't match the notebook paths.** `config_loader.py` builds default parquet paths under `<package_root>/data/...`, but the notebooks pass **explicit** paths under the repo-level `../../../data/aurora/...`. The notebooks' explicit paths are the ones in use; the config defaults are effectively dead for the current workflow.

5. **Stray `… copy.ipynb` scratch notebooks** may exist in some domains (e.g. `1c_entsoe_retrieval copy.ipynb` under `api_retrieval/entsoe/`). Treat the non-`copy` versions as canonical.

---

## 3. The Aurora package (`aurora_forecasts`)

```
packages/aurora_forecasts/src/aurora_forecasts/
├── retrieval_helper/
│   ├── client.py            # AuroraHttpClient + ForecastRequest (low-level HTTP/CSV)
│   ├── retrieval_helper.py  # ★ AuroraAPI — the class you instantiate in 1a
│   ├── processors.py        # process_system_forecast / process_technology_forecast (→ long format)
│   └── plotting.py
├── processing/
│   ├── unit_conversion.py   # convert_units (GW→MW, TWh→GWh)
│   └── dicts.py             # region/country maps, variable-name mappings used by 2c/2d/2e
├── utils/
│   ├── config_loader.py     # load_api_params() → AuroraApiConfig (see §2 caveats)
│   └── forecast_release.py  # ReleaseInfo dataclass + parse_release_info() — derive quarter/month/year from a scenario name
└── plot/plotting.py         # duplicate of retrieval_helper/plotting.py (dead — see §5)
```

> ℹ️ `get_quarterly_strings()` (used by `2c`/`2e`) is **not** in this package — it lives in `common_libs.utils.utils_dates`.

### `AuroraAPI` (the class that does the work — `retrieval_helper.py`)

Construction queries the API immediately (`_retrieve_available_forecasts`) and loads the local JSON registry. Key methods:

| Method | What it does |
|---|---|
| `__init__(token, scenario_comp_registry_path, technology_db_path, system_db_path, country_code_list=None, http_client=None)` | Loads registry, fetches the list of available scenarios/regions/currencies. |
| `from_config(config, resolution="1y", …)` | Factory from an `AuroraApiConfig`. **Note `1a` does NOT use this** — it constructs `AuroraAPI(...)` directly with explicit paths. |
| `retrieve_single_forecast(hash, region_code, sensitivity, type, currency_code, resolution)` | Downloads + processes one scenario. Returns a long-format DataFrame. `type="technology"` only valid for `1y`/`1m`. |
| `update_scenario_database(currency_code=None, resolution="1y", country_code_list=None)` | **The quarterly entry point.** Iterates published scenarios for the configured regions, skips any `(hash, region_code)` already in the registry, fetches **both** system & technology, appends to the parquet files, updates the registry JSON. |
| `concat_existing_data(df_new, path_existing)` | Read-existing → concat → `drop_duplicates(keep="last")` → write back to the **same** parquet path. |

### 🔑 The incremental model (important — and why the runbook says "never rename files")

`update_scenario_database` **appends to fixed parquet files**; it does not create per-release files. Dedup is by the `(hash, region_code)` pair held in the registry JSON (`retrieval_helper.py:216–229`), and a second dedup on full-row equality at write time (`concat_existing_data`, line 321). Practical consequences:

- Re-running is **idempotent** for already-downloaded scenarios (they print "skipping").
- The parquet filenames are **stable across quarters** — a new release just adds rows. (A previous handover draft wrongly told users to rename files each quarter. Do not.)
- The registry JSON is the source of truth for "what have we already pulled." If it gets out of sync with the parquet (e.g. parquet deleted but registry kept), you'll get gaps — delete both and re-pull to rebuild cleanly.

### Fixed paths used by `1a` (the retrieval notebook)

```
data/aurora/aurora_scenario_components_registry_{1m,1y,1h}.json   # registries
data/aurora/aurora2_technology_scenarios_ES_default_currency_1y.parquet
data/aurora/aurora2_system_scenarios_ES_default_currency_1y.parquet
data/aurora/aurora_technology_scenarios_ES_default_currency_1m.parquet
data/aurora/aurora_system_scenarios_ES_default_currency_1m.parquet
config/aurora/api_params.yaml                                     # token + country list
```
(Note the `aurora2_` prefix on the **yearly** files but `aurora_` on the monthly — historical, not a typo to "fix" without updating every consumer.)

---

## 4. The notebook pipeline

Run from `notebooks/aurora_forecasts/forecasts/`. Order matters: Step 1 must precede Step 2+.

| Step | Notebook | Reads | Writes | Status |
|---|---|---|---|---|
| 1 | `1a_aurora_forecasts.ipynb` | Aurora API | the 5 parquet files above | ✅ works; **hourly section is WIP** and will error — stop after the monthly fetch (Section 7) |
| 2a | `2a_..._prices_processing_yearly` | `aurora2_{tech,system}_…1y.parquet`, `data/finance/inflation.xlsx` | `outputs/trackers/prices_tracker.xlsx`, `data/processed/aurora_prices_melted_default_currency_1y.parquet`, (SP upload, partly disabled) | ✅ works |
| 2b | `2b_..._processing_monthly` | monthly parquet + yearly (to fill gaps) + inflation | `.pkl`/`.csv` to **hardcoded `c:/Users/mpy/Market data retrieval/...`** | ❌ **BROKEN** — see §5 |
| 2c | `2c_..._curtailment_processing_yearly` | `aurora2_tech…1y.parquet`, inflation | `outputs/trackers/curtailment_tracker.xlsx` (+SP) | ✅; **edit `release = 'YYQX'`** |
| 2d | `2d_..._technology_processing_yearly` | `aurora2_tech…1y.parquet` | `data/aurora/processed/generation_tracker.xlsx` (+SP) | ✅; no quarterly edit |
| 2e | `2e_..._demand_processing_yearly` | `aurora2_system…1y.parquet` | `outputs/trackers/demand_tracker.xlsx` (+SP) | ✅; **edit `release = 'YYQX'`** |
| 3a | `3a_process_merged_prices` | **SharePoint** master price tracker (`SP_BASE_PATH` + `…/Prices/Tracker/Exus power price forecasts tracker.xlsx`, sheet `Real prices`) | `outputs/trackers/heatmap_data.xlsx` | ✅ required; depends on 2a being published to the master tracker. Output feeds the **PowerPoint heatmap slides** via the `refresh-aurora-slide` Claude skill. |

### Quarterly parameters (the things that change per release)

Most consumers read the **fixed** parquet, so there is little to edit. The genuine per-quarter edits:

- **`2c` and `2e`:** a `release = 'YYQX'` string near the top (currently `'26Q2'`). It drives the quarter/month filter via `get_quarterly_strings()` (imported from `common_libs.utils.utils_dates`, **not** from `aurora_forecasts`), which matches on the scenario `name`. If Aurora's scenario naming changes, this filter is the fragile point. (`2a`/`2d` instead auto-derive the release from the name via `parse_release_info()` and need no edit.)
- **Occasional, `2a`:** `currency_year` (real-price base year, currently `2025`), `commodity_list`, and a `df_concat[~name.isin([...])]` exclusion list for deprecated releases. Only touch when Aurora adds/removes variables or you re-base.
- **Inflation vintage:** `2a`/`2b` filter `inflation.xlsx` to a hardcoded month (e.g. `'2025-Apr'`). Update `data/finance/inflation.xlsx` and the date filter when a newer vintage lands.
- **`3a`:** reads the SharePoint master price tracker (sheet `Real prices`, `skiprows=5`, `usecols='C:BH'`), computes average price + quarter-on-quarter variation pivots by country/release, and writes `outputs/trackers/heatmap_data.xlsx`. That file is the input to the `refresh-aurora-slide` Claude skill, which updates the PowerPoint heatmap slide. Requires `SP_BASE_PATH` set and OneDrive synced.

### Other notebooks in the Aurora folders (not part of the quarterly run)

- **`actuals/1a_retrieve_actuals.ipynb`** — retrieves historical *actual* prices (for comparison against the forecasts).
- **`forecasts/DAM_Prices 1.ipynb`** — ad-hoc day-ahead-market price exploration; not wired into the quarterly pipeline and undocumented. Treat as scratch unless you find it's used.

---

## 4a. ⭐ Aurora data drift & the mapping dicts (the single most important recurring gotcha)

**Aurora is not rigorous about what they publish each quarter.** A new release frequently exposes **new variables / price types / regions over the API** that didn't exist before. When that happens, the processing notebooks (chiefly **`2a`**, but also `2c`/`2e`) will **fail with a `ValueError`** because the new value has no entry in the mapping dictionaries. This is *by design* — the guards below turn a silent `NaN` into a loud, early failure so corrupted data never reaches the trackers. **Expect this to happen, and know how to fix it.**

All the mappings live in **one file:**
`packages/aurora_forecasts/src/aurora_forecasts/processing/dicts.py`

| Dict in `dicts.py` | Used by (cell) | Maps | The `ValueError` you'll see | Trips when Aurora adds… |
|---|---|---|---|---|
| `curtailment_type_dict` | `2a` (cell 9), `2c` | price `type` → Curtailed/Uncurtailed class | "There are some price types that have not been mapped to curtailed/uncurtailed." | a new capture-price `type` variant |
| `commodity_scope_dict` | `2a` (cell 18) | commodity `variable` → Scope | "There are some commodity types that have not been mapped to 'scope'." | a new commodity/system price variable |
| `region_tracker_map` + `country_tracker_map` | `2a` (cells 14–15), all | `region_code` → region / country name | "…not been mapped to country/region." | a new region / price zone / country |
| `demand_drivers_tracker_mappings` | `2e` | demand `variable` → label | "Null values found in 'variable' column after mapping…" | a new demand driver |

> ⚠️ Two related fragile points beyond the dicts:
> - **`commodity_list`** (a literal list near the top of `2a`) is the *filter* that selects which system variables become "commodities." A genuinely new commodity must be added in **two places**: this filter list **and** `commodity_scope_dict`.
> - `2c`/`2e` filter scenarios by `sensitivity` (`['central','low','high']`). Aurora sometimes ships extra sensitivities (e.g. `lowextendedgenerationtax`); those are silently dropped unless added to the filter.
> - **`2d` does NOT fail loudly on a new region.** It maps with `na_action='ignore'`, so an unmapped `region_code` silently becomes blank rather than raising like `2a`/`2c`/`2e` do. If the generation tracker shows blank regions, suspect a missing `region_tracker_map` entry — there's no guard to catch it for you.

### How to fix it when `2a` (or `2c`/`2e`) raises this error

1. **Find the offending value.** The guard only says "something didn't map." Identify *what* by inspecting the null rows. Add a temporary line just before the guard, e.g. for the curtailment guard in cell 9:
   ```python
   print(df_prices.loc[df_prices['curtailed_uncurtailed'].isnull(), 'type'].unique())
   ```
   (or `'variable'` for the commodity guard in cell 18, `'region_code'` for cells 14–15.)
2. **Decide what it maps to.** This needs judgment about what the new variable *means* — check Aurora's release notes / data definitions, or ask the Aurora contact. ✍️ _Mikel: see your note in §"How to decide a new mapping" below._
3. **Add the entry** to the correct dict in `dicts.py` (e.g. `"New capture price (M0)": "Curtailed"`).
4. **Restart the notebook kernel** (in VS Code: the **Restart** button in the toolbar) and re-run from the top. Because the package is an *editable install*, the edited dict is only picked up **after a kernel restart** — re-running the cell alone uses the stale cached module.
5. Remove the temporary `print` once resolved.

> 🐞 **Minor code bug to fix while you're here:** the region/country guard in `2a` cell 14 raises with the *wrong* message ("…not been mapped to curtailed/uncurtailed.") — copy-paste error from cell 9. Harmless but misleading; correct it to reference country/region.

---

## 5. Known issues / tech debt (prioritised)

0. **Mapping-dict drift (see §4a) is the most frequent breakage.** Worth a small robustness investment: change the guards to **print the offending values automatically** (instead of a generic message), and consider logging newly-seen Aurora variables on every run so drift is noticed *before* it errors. This is the single best quality-of-life fix for whoever runs the quarterly job.
1. **`2b_aurora_forecast_processing_monthly.ipynb` is broken.** Fails at `from utils.utils_dates import map_month` (`ModuleNotFoundError`). The helper exists as `common_libs.utils.utils_dates.map_month` — the import path is wrong. Also writes to **hardcoded absolute paths** `c:/Users/mpy/Market data retrieval/...` that don't exist on other machines. **Fix:** correct the import to `from common_libs.utils.utils_dates import map_month` and replace the absolute output paths with `../../../data/aurora/processed/...`. Until fixed, the runbook tells users to skip it.
2. **Secret in plain-text YAML.** `config/aurora/api_params.yaml` holds the live Aurora token. Migrate it to `.env` + `python-dotenv` (the package already supports `AURORA_TOKEN`) or a secrets manager, and ensure the file is `.gitignore`d. **Confirm it was never pushed to a remote.**
3. **Publishing to the master trackers is manual; the automated-upload code is dead.** The generated trackers are copied into the master SharePoint trackers **by hand** (runbook Step 5 / [PROCESS_OVERVIEW.md](../PROCESS_OVERVIEW.md)). The `GraphSharePointClient` / `load_ms_config()` (Azure) upload path is **not used** — and is also broken (`load_ms_config()` looks for `packages/common_libs/config/ms_config.yaml`, which doesn't exist). Delete that dead path, or fix it only if automated upload is ever wanted. The one live SharePoint dependency is `SP_BASE_PATH` (the OneDrive mirror), read from the git-ignored root `.env`.
4. **Hardcoded machine-specific paths** beyond 2b (`SP_BASE_PATH` defaults pointing at `C:/Users/mpy/OneDrive - Exus Management Partners/...`). Parameterise.
5. **`1a` hourly section is unfinished** — `update_scenario_database(resolution='1h')` is not implemented for batch; only ad-hoc `retrieve_single_forecast` calls. The CSV parse also emits a `DtypeWarning` (mixed types in column 1) — set `low_memory=False`/explicit dtypes in `client.py:75` if you finish this.
6. **`config_loader` defaults are dead code** relative to the notebooks (see §2.4). Either route the notebooks through `from_config`/`load_api_params` (cleaner, env-var token, single source of paths) or remove the unused defaults to avoid confusion.
7. **Stray `… copy.ipynb` notebooks** in other domains (e.g. `api_retrieval/entsoe/1c_entsoe_retrieval copy.ipynb`) should be removed once confirmed redundant.
8. **Duplicate plotting module** — `plot/plotting.py` duplicates `retrieval_helper/plotting.py`. Keep one.

---

## 6. Suggested first week for the new dev

1. Get the env installed (§1) and **confirm the Aurora token works** — run `1a` through the yearly fetch. If it 401s, the token transfer (START_HERE #1) didn't happen.
2. Do **one full dry-run** of the quarterly procedure following [the runbook](AURORA_QUARTERLY_RUNBOOK.md), then diff the regenerated trackers against the last published ones to confirm parity.
3. Fix **`2b`** (quick win, §5.1) and resolve the **secrets** issue (§5.2).
4. **SharePoint publishing is manual** — documented in the runbook Step 5 and [PROCESS_OVERVIEW.md](../PROCESS_OVERVIEW.md). The remaining debt is the **dead automated-upload code** (§5.3): decide whether to delete or fix it.
5. Decide whether to route notebooks through `load_api_params()` for a single source of config truth (§5.6).

### Adding a new country (reference)
1. Add the region code to `processing/dicts.py` (`region_tracker_map` **and** `country_tracker_map`).
2. Add the code to `country_code_list` in `config/aurora/api_params.yaml`.
3. Re-run `1a` to pull the new region's scenarios.

---

## 7. Other pipelines (brief)

Not the focus of this handover, but for completeness — the other non-Aurora pieces in the repo:

- **Exus internal DB** (`notebooks/api_retrieval/exus/`) — `pyodbc`/SQLAlchemy extraction; used by the **Quarterly update** process (`1a_quarterly.ipynb` → `outputs/quarterly/`). See [PROCESS_OVERVIEW.md](../PROCESS_OVERVIEW.md).
- **Bloomberg** (`notebooks/bloomberg/`) — requires a logged-in Bloomberg Terminal; `blpapi` from conda-forge. See [bloomberg/BLOOMBERG_HANDOVER.md](../bloomberg/BLOOMBERG_HANDOVER.md).
> **Not currently in use** (present in the repo but not part of either documented process, and intentionally left out of this handover): the **ESIOS** (`api_retrieval/esios`), **ENTSO-E** (`api_retrieval/entsoe`), and **AEMET/PVGIS** (`api_retrieval/meteo`) pipelines, plus the **Azure / SharePoint automated-upload** path.
