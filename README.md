# Python Unified Monorepo

A single, notebook-forward monorepo that centralises the independent Exus market research and forecasting workflows. Four installable Python packages share a common data tree, eliminating duplicated code and fragile `sys.path` hacks.

## Overview

### What Problem Does This Solve?

Exus research historically lived in four separate projects, each with its own virtual environment, duplicated utility code, and disconnected data directories. As the number of markets and data sources grew this caused:

- **Dependency drift** – each project pinned its own versions of pandas, pyarrow, etc.
- **Copy-paste logic** – authentication helpers, Parquet I/O wrappers, and plotting utilities were duplicated.
- **Broken cross-references** – notebooks relied on ad-hoc `sys.path` insertions to reach shared code.
- **No single source of truth** for processed data across ENTSOE, ESIOS, Aurora, and Bloomberg pipelines.

`Python Unified` solves this by:
- Grouping everything into one repository with a shared `notebooks/data` tree.
- Extracting cross-cutting code into `common_libs` and installing all packages in editable mode.
- Preserving the original notebook directory structure so existing `../../data/...` paths continue to work without modification.

### Key Features

- **Monorepo layout** – one `git clone`, one environment, all workflows.
- **Four focused packages** – `common_libs`, `api_retrieval`, `aurora_forecasts`, `bloomberg`, each with its own `pyproject.toml`.
- **Shared data tree** – all processed and raw data lives under `notebooks/data/`, referenced consistently by every domain notebook.
- **Editable installs** – `pip install -e` lets notebooks `import <package>` directly; no path manipulation.
- **Parquet-first storage** – raw API responses are normalised and persisted in Parquet for fast, schema-aware access.
- **Notebook ordering** – numbered prefixes (`1a_`, `2a_`, …) document the intended execution sequence within each domain.
- **AI/LLM ready** – OpenAI and LangChain dependencies are included for agentic and summarisation notebooks.

---

## Repository Layout

```
Python Unified/
├── packages/
│   ├── common_libs/          # Shared utilities (finance, SharePoint, generic helpers)
│   ├── api_retrieval/        # ETL pipelines – ESIOS, ENTSOE, Aurora market priors
│   ├── aurora_forecasts/     # Aurora Energy Research forecast retrieval & processing
│   └── bloomberg/            # Bloomberg market data integration
├── notebooks/
│   ├── api_retrieval/        # AEMET, ENTSOE, ESIOS, Exus DB notebooks
│   │   ├── entsoe/
│   │   ├── esios/
│   │   ├── exus/
│   │   └── meteo/            # AEMET temperature and PVGIS irradiance notebooks
│   ├── aurora_forecasts/     # Aurora retrieval and multi-resolution processing
│   │   ├── actuals/
│   │   └── forecasts/
│   ├── bloomberg/            # Bloomberg retrieval and quarterly data notebooks
│   ├── agentic_news/         # AI-powered news and report analysis
│   ├── transcription/        # Audio/video transcription utilities
│   └── data/                 # Single shared data root
│       ├── aurora/           #   └── raw/ and processed/ Aurora data
│       ├── entsoe/           #   └── ENTSOE capacity and generation data
│       ├── esios/            #   └── ESIOS spot prices
│       ├── bnef/             #   └── BloombergNEF data
│       ├── finance/          #   └── FX and inflation tables
│       ├── raw/
│       ├── processed/
│       └── temp/
├── scripts/
│   └── update_notebook_imports.py   # Import-normalisation helper used during migration
└── pyproject.toml            # Root manifest (no top-level source; packages installed individually)
```

---

## Packages

### `common_libs`

Shared helper routines used by every other package.

| Submodule | Purpose |
|-----------|---------|
| `finance` | FX conversion, inflation adjustment utilities |
| `sp` | Microsoft SharePoint / Graph API helpers (`msal` integration) |
| `utils` | Generic I/O, logging, and data-wrangling helpers |

```python
from common_libs import finance, sp, utils
```

---

### `api_retrieval`

ETL workflows for pulling, validating, and compiling market-prior datasets from multiple data providers.

| Submodule | Purpose |
|-----------|---------|
| `aurora_retrieval` | Aurora scenario component helpers and dictionaries |
| `config` | YAML-based configuration loader |
| `etl` | ESIOS provider pipeline |
| `load_compilation` | Load-data compilation orchestration and notebook executor |
| `markets` | Market-specific processing routines |
| `shared` | Cross-provider shared utilities |
| `utils` | Logging, file I/O, date helpers |
| `verification_project` | Data-quality checks and reconciliation |

Key domain notebooks:
- `notebooks/api_retrieval/entsoe/1c_entsoe_retrieval.ipynb` – ENTSOE capacity & generation
- `notebooks/api_retrieval/entsoe/2a_capture_prices.ipynb` – European capture-price calculation
- `notebooks/api_retrieval/esios/1a_esios_retrieval.ipynb` – Spanish spot prices (ESIOS)
- `notebooks/api_retrieval/exus/1b_bbdd_exus.ipynb` – Exus internal database extraction
- `notebooks/api_retrieval/meteo/1d_aemet_retrieval.ipynb` – Spanish temperature & precipitation (AEMET)
- `notebooks/api_retrieval/meteo/pvgis.py` – PVGIS solar irradiance & wind speed per autonomous community

```python
from api_retrieval import etl, load_compilation, utils
```

---

### `aurora_forecasts`

Forecast retrieval and multi-resolution processing for Aurora Energy Research data covering eight European markets.

| Submodule | Purpose |
|-----------|---------|
| `retrieval_helper` | `AuroraAPI` client – scenario listing, download, normalization |
| `processing` | Mapping dictionaries – region codes, country tracker maps |
| `plot` | Chart generation for price, demand, technology-mix comparisons |
| `utils` | `load_api_params()` config loader |

Supported countries: Spain · France · Germany · Great Britain · Italy · Poland · Portugal · Ireland

Supported resolutions: `1h` (hourly) · `1m` (monthly) · `1y` (yearly)

Key domain notebooks (`notebooks/aurora_forecasts/forecasts/`):
- `1a_aurora_forecasts.ipynb` – retrieve raw scenarios from the Aurora API
- `2a_aurora_forecast_prices_processing_yearly.ipynb` – process yearly price forecasts
- `2b_aurora_forecast_processing_monthly.ipynb` – process monthly forecasts
- `2c_aurora_forecast_curtailment_processing_yearly.ipynb` – curtailment analysis
- `2d_aurora_forecast_technology_processing_yearly.ipynb` – technology-mix processing
- `2e_aurora_forecast_demand_processing_yearly.ipynb` – demand forecast processing
- `3a_sharepoint_data_prices_processing_yearly.ipynb` – SharePoint-sourced price processing
- `4a_process_merged_prices.ipynb` – merge actuals with forecasts

```python
from aurora_forecasts import AuroraAPI, load_api_params

config = load_api_params()
api = AuroraAPI.from_config(config, resolution="1y")
api.update_scenario_database()
```

---

### `bloomberg`

Market data integration for Bloomberg Terminal and BloombergNEF research.

| Submodule | Purpose |
|-----------|---------|
| `api_helper` | `blpapi` wrapper for Bloomberg Terminal data requests |
| `quarterly` | Quarterly earnings and market-indicator processing |
| `securities` | Security metadata and time-series retrieval helpers |
| `utils` | Bloomberg-specific formatting and I/O utilities |

Key domain notebooks (`notebooks/bloomberg/`):
- `1a_retrieve_info.ipynb` – pull security data from Bloomberg
- `1b_quarterly_data.ipynb` – process and store quarterly metrics

```python
from bloomberg import api_helper, quarterly, securities
```

---

## Installation

### Requirements

- **Anaconda** (recommended) or Miniconda
- **Python 3.10** (required by all packages)

### Step-by-step (Anaconda)

**Step 1 — Open Anaconda Prompt** (or a PowerShell terminal with `conda` on the PATH)

**Step 2 — Create the conda environment with Python 3.10**

```powershell
conda create -n python-unified python=3.10 -y
```

**Step 3 — Activate the environment**

```powershell
conda activate python-unified
```

**Step 4 — Install all packages in editable mode** (run from the repository root)

```powershell
pip install -e packages/common_libs -e packages/api_retrieval -e packages/aurora_forecasts -e packages/bloomberg
```

This installs all dependencies declared in each `pyproject.toml` automatically and makes every package importable without any `sys.path` manipulation.

**Step 5 — Register the environment as a Jupyter kernel**

```powershell
pip install ipykernel
python -m ipykernel install --user --name python-unified --display-name "Python (python-unified)"
```

**Step 6 — Launch JupyterLab**

```powershell
jupyter lab
```

Select the **"Python (python-unified)"** kernel in any notebook.

### Verification

```sh
python -c "import common_libs; import api_retrieval; import aurora_forecasts; import bloomberg; print('All packages OK')"
```

### Aurora API configuration

Set your Aurora token via environment variable (recommended):

```sh
$Env:AURORA_TOKEN = "your_api_token_here"
```

Or store it in a `config/api_params.yaml` file inside the `aurora_forecasts` package:

```yaml
aurora_token: "your_token_here"
country_code_list:
  - esp
  - fra
  - deu
  - gbr
  - ita
  - pol
  - prt
  - irx
```

> **Security**: Never commit API tokens to version control.

---

## Notebook Workflow

1. Activate the virtual environment and launch JupyterLab from the repository root.
2. Navigate to the relevant domain folder under `notebooks/`.
3. Run notebooks in their numbered order (`1a_` → `2a_` → …).
4. All notebooks write processed outputs to `notebooks/data/<provider>/processed/` and raw downloads to `notebooks/data/<provider>/raw/`.
5. No `sys.path` manipulation is needed — editable installs handle all imports.

### Data Flow

```
Aurora API / ESIOS / ENTSOE / Bloomberg
          │
          ▼
  1x_  retrieval notebooks   →  notebooks/data/<provider>/raw/
          │
          ▼
  2x_  processing notebooks  →  notebooks/data/<provider>/processed/  (Parquet)
          │
          ▼
  3x+  analysis / reporting notebooks
```

---

## Dependencies Overview

| Category | Key Libraries |
|----------|--------------|
| Data processing | `pandas`, `numpy`, `pyarrow`, `fastparquet`, `statsmodels`, `pmdarima` |
| Visualisation | `matplotlib`, `plotly`, `seaborn` |
| API & web | `requests`, `beautifulsoup4`, `selenium`, `lxml` |
| Database | `sqlalchemy`, `pyodbc` |
| Document I/O | `openpyxl`, `pdfplumber`, `xlrd`, `pypandoc` |
| Notebooks | `jupyter`, `jupyterlab`, `ipython`, `papermill` |
| AI / LLM | `openai`, `langchain-core`, `langchain-openai`, `langsmith` |
| Authentication | `msal`, `python-dotenv` |
| Market-specific | `entsoe-py`, `eurostat`, `blpapi` (conda-forge), `pvlib`, `xlwings` |
| Utilities | `pyyaml`, `tqdm`, `click`, `colorlog` |

---

## Advanced Usage

### Running a single notebook programmatically (papermill)

```python
import papermill as pm

pm.execute_notebook(
    "notebooks/aurora_forecasts/forecasts/2a_aurora_forecast_prices_processing_yearly.ipynb",
    "notebooks/aurora_forecasts/forecasts/outputs/2a_output.ipynb",
    parameters={"resolution": "1y", "currency_code": "eur2019"},
)
```

### Adding a new country to Aurora

1. Add the region code to `packages/aurora_forecasts/src/aurora_forecasts/processing/dicts.py` — both `region_tracker_map` and `country_tracker_map`.
2. Add the code to `aurora_token.country_code_list` in `config/api_params.yaml`.
3. Re-run notebook `1a_aurora_forecasts.ipynb` to pull the new scenarios.

### Adding a new data provider

1. Create a new submodule under the most relevant package (or create a new package under `packages/`).
2. Add a `pyproject.toml` following the existing pattern.
3. Install with `pip install -e packages/<new_package>`.
4. Add notebooks under `notebooks/<new_domain>/`.

---

## Troubleshooting

**Import errors after installation**
```
Verify editable installs: pip list | findstr -i "common_libs api_retrieval aurora_forecasts bloomberg"
Reinstall if needed:      pip install -e packages/common_libs --force-reinstall
```

**`AURORA_TOKEN` not found**
```
Set $Env:AURORA_TOKEN = "..." in the same shell session that runs JupyterLab,
or add it to a .env file and load it via python-dotenv.
```

**Parquet read errors after schema change**
```
Delete the affected .parquet file under notebooks/data/<provider>/processed/
and rerun the processing notebook to regenerate it.
```

**`blpapi` import error**
```
blpapi is available via conda-forge. Install it with:
  conda install -c conda-forge blpapi

Note: the Bloomberg Terminal must be running and you must be logged in
before importing blpapi or making any data requests.
```

**Wrong Python version**
```
All packages require Python 3.10.x. Check: python --version
Use a dedicated conda environment: conda create -n python-unified python=3.10 -y
```

---

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes following PEP 8 and add type hints to all public functions.
3. If adding a new notebook, follow the naming convention `<step>_<description>.ipynb` (e.g. `2b_new_processing.ipynb`).
4. Commit with a descriptive message: `git commit -m "feat: add ENTSOE generation processing"`
5. Push and open a pull request.

### Coding Guidelines

- Use type hints for all function signatures.
- Add module-level and class-level docstrings.
- Keep notebooks focused on a single logical step; heavy logic belongs in the package source.
- Store credentials in environment variables or `.env` files — never in notebooks or source code.

---

## Cleanup Notes

- No build artifacts (`__pycache__`, `*.egg-info`) are tracked; add them to `.gitignore`.
- The helper script at `scripts/update_notebook_imports.py` documents how imports were normalised during the initial migration from the legacy projects; rerun it if new notebooks are added.

---

## License

Proprietary software — all rights reserved. For licensing inquiries contact the repository owner.

## Contact

- **Author**: Mikel Perez
- **Version**: 0.1.0
- **Python**: 3.10
- **Last Updated**: February 2026

