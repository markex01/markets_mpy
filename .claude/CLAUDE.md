# Project Guidelines for Claude

## Project Overview
Python Unified is a monorepo consolidating four independent market-research Python packages into a single repository. The primary interface is **JupyterLab notebooks** — there is no HTTP API server or CLI entrypoint. All packages are installed in editable mode and consumed by notebooks.

## Language
- All code comments, docstrings, and documentation must be written in **English**.

---

## Stack

| Layer | Technology |
|---|---|
| Runtime | Python **3.10** (strictly required — do not use 3.11+ syntax) |
| Environment manager | **Conda** (`python-unified` environment) |
| Package install | `pip install -e` (editable installs from `packages/`) |
| Primary data structure | `pandas.DataFrame` |
| Data persistence | **Parquet** (pyarrow / fastparquet) — not CSV or pickle |
| Configuration | YAML files + `.env` / environment variable fallback |
| Notebooks | JupyterLab (`jupyter lab`) |
| Excel export | openpyxl / xlwings — always to `outputs/` |
| Bloomberg Terminal | `blpapi` from **conda-forge** (not on PyPI) |
| Solar/meteo data | `pvlib` (PVGIS API client) |
| HTTP clients | `requests.Session` |
| Auth (SharePoint) | `msal` (service principal) |
| AI / LLM | `openai` + `langchain-openai` |

### Python 3.10 type hint style
Use built-in generics — **not** `typing` module equivalents:
```python
# Correct (Python 3.10+)
def foo(x: list[str]) -> tuple[str, str]: ...
def bar(d: dict[str, int]) -> None: ...

# Wrong — do not use
from typing import List, Tuple, Dict
def foo(x: List[str]) -> Tuple[str, str]: ...
```

---

## Project Structure

```
Python Unified/
├── packages/                   # Four installable editable packages
│   ├── common_libs/            # Shared utils — NO Bloomberg dependency
│   ├── api_retrieval/          # ESIOS, ENTSOE, AEMET, REE pipelines
│   ├── aurora_forecasts/       # Aurora Energy Research API
│   └── bloomberg/              # Bloomberg Terminal integration only
├── notebooks/                  # Jupyter notebooks (primary interface)
│   ├── api_retrieval/          # ENTSOE, ESIOS, EXUS DB, AEMET notebooks
│   │   └── meteo/              # AEMET & PVGIS meteo notebooks + pvgis.py script
│   ├── aurora_forecasts/       # Aurora retrieval & processing notebooks
│   ├── bloomberg/              # Bloomberg data pull & processing
│   ├── agentic_news/           # AI-powered news analysis
│   ├── transcription/          # Audio/video transcription utilities
│   └── data/                   # Shared data root (raw/ and processed/)
│       ├── aurora/
│       ├── entsoe/
│       ├── esios/
│       ├── bnef/
│       └── finance/
├── outputs/                    # Excel exports — gitignored, never hardcode paths
├── scripts/                    # Utility scripts (e.g. update_notebook_imports.py)
├── config/                     # Project-level configuration files
└── .env                        # Secrets — never commit, never log
```

### Package internals follow `src/` layout:
```
packages/<name>/
└── src/<name>/
    ├── __init__.py   # re-exports the public API
    └── <submodule>/
```

### Package dependency rules (strict — never violate)
- `common_libs` — no dependency on any other project package
- `bloomberg` — may use `common_libs` only
- `api_retrieval` — may use `common_libs` only
- `aurora_forecasts` — may use `common_libs` only
- **Notebooks** — may import from all packages freely
- **Packages must never import from notebooks**

---

## Common Commands

```bash
# Install all packages in editable mode (run from repo root)
pip install -e packages/common_libs -e packages/api_retrieval -e packages/aurora_forecasts -e packages/bloomberg

# Register Jupyter kernel
python -m ipykernel install --user --name python-unified --display-name "Python (python-unified)"

# Launch JupyterLab
jupyter lab

# Verify all packages importable
python -c "import common_libs; import api_retrieval; import aurora_forecasts; import bloomberg; print('OK')"

# Install Bloomberg Terminal API (conda-forge only — not on PyPI)
conda install -c conda-forge blpapi
```

---

## Core Responsibilities

### 1. Code Generation & Refactoring
- Generate new code that follows Python best practices and is consistent with the existing codebase style.
- When you identify opportunities for refactoring or improvement, **always notify the user first and wait for explicit confirmation before making any changes**.
- Never refactor proactively without asking. Describe what you would change and why, then wait.

### 2. Bug Review & Fixing
- Identify and explain bugs clearly before proposing a fix.
- Present the fix and wait for approval before applying it.

### 3. Documentation
- Write **docstrings** for all functions and classes using the **Google style** format.
- Add **inline comments** for complex or non-obvious logic.
- Keep the **README.md** up to date when functionality changes significantly. Propose README updates and wait for confirmation.

---

## Coding Conventions

### Docstrings — Google style, English only
```python
def get_start_date_from_quarterly(quarterly: str) -> tuple[str, str]:
    """Convert a YYQX quarterly string to a 3-year lookback date range.

    Args:
        quarterly: Quarter string in YYQX format, e.g. "25Q4".

    Returns:
        Tuple of (start_date, end_date) as "YYYYMMDD" strings.

    Raises:
        ValueError: If the quarterly string is not in YYQX format.
    """
```

### Type hints — required on all public function signatures
- Use Python 3.10 built-in generics (`list`, `dict`, `tuple`) — not `typing` module.
- `Optional[X]` → `X | None`

### Configuration loading pattern
- YAML file as primary source; environment variable as fallback.
- Use frozen `dataclass` for config objects (immutability).
- Resolve all paths relative to a `base_path` from the YAML, never hardcoded.
- Example: `aurora_forecasts/utils/config_loader.py` → `AuroraApiConfig` dataclass.

### API / HTTP client pattern
- Wrap API calls in a class (e.g. `EsiosAPI`, `AuroraHttpClient`).
- Use `requests.Session` for connection reuse.
- For large historical datasets, **chunk requests** (e.g. 30-day windows for ESIOS) — do not fetch years in a single call.
- Return `pd.DataFrame`; return empty DataFrame on error — never `None`.

### Data persistence pattern
- **Always store as Parquet** (not CSV or pickle) for processed datasets.
- Use `pyarrow` engine by default.
- Cache paths are resolved through config objects, not hardcoded strings.

### Class structure
- One class per file where practical (mirrors existing package structure).
- Configuration classes: frozen `@dataclass`.
- API clients: regular class with `__init__` taking a config object.
- Use `@classmethod` named `from_config()` as an alternative constructor when a config object is the primary input.

---

## Naming Conventions

| Entity | Convention | Example |
|---|---|---|
| Files / modules | `snake_case` | `config_loader.py`, `esios_api.py` |
| Classes | `PascalCase` | `EsiosAPI`, `AuroraApiConfig`, `GraphSharePointClient` |
| Functions / methods | `snake_case` | `get_start_date_from_quarterly()` |
| Variables | `snake_case` | `start_date`, `country_codes` |
| Constants / dicts | `snake_case` with `_dict` suffix for mappings | `region_tracker_map`, `country_tracker_map` |
| Bloomberg ticker dicts | `snake_case` with descriptive name | `fx_dict`, `europe_daily_pool_dict` |
| Parquet cache files | `<domain>_<resolution>.parquet` | `aurora_1m.parquet` |
| Notebook files | `<step_number><sub>_<description>.ipynb` | `2a_capture_prices.ipynb` |

---

## Project Conventions

### Bloomberg Security Tickers
- All Bloomberg tickers **must include their full suffix**: `" Index"`, `" Curncy"`, `" Comdty"`, etc.
- Tickers are stored **with** the suffix in `security_dicts.py`. Never strip or re-add the suffix in retrieval code.
- Example: `'ES': 'OMLPDAHD Index'` — correct. `'ES': 'OMLPDAHD'` — wrong.
- Source of truth: `packages/bloomberg/src/bloomberg/securities/security_dicts.py`

### Quarterly String Format
- Quarters are represented as `"YYQX"` strings, e.g. `"25Q4"` = Q4 2025.
- Use `get_start_date_from_quarterly(quarterly)` from `common_libs.utils.utils_dates` to convert to date ranges (returns 3-year lookback).
- Never implement your own quarter-to-date conversion.

### Excel Export Format
- `build_monthly_absolute_df()` and `build_monthly_normalized_df()` both return a **transposed** DataFrame (`.T`).
- This transposed format is intentional — it matches ThinkCell's expected layout.
- When concatenating results from these methods, call `.T.set_index("date")` on each before `pd.concat(..., axis=1)`.

### Outputs Directory
- All Excel exports go to `outputs/`. This folder is **not tracked by git**.
- Never hardcode absolute paths — always use `os.path.abspath()` relative to the notebook file.

### Data Directory
- `notebooks/data/raw/` — original downloads, never modified after write.
- `notebooks/data/processed/` — cleaned/transformed datasets.
- `notebooks/data/temp/` — gitignored; safe to delete.

### Legacy Code
- `packages/bloomberg/src/bloomberg/api_helper/extractor_ref.py` is the old Bloomberg extractor (written in Spanish). **Do not modify it.**
- All new Bloomberg code should use `extractor.py` and the `BloombergExtractor` class.

---

## Environment Variables
- The project uses a `.env` file for configuration loaded via `python-dotenv`.
- **Never expose, print, log, or commit the contents of `.env`**.
- If new environment variables are needed, add them as examples in a `.env.example` file with placeholder values.
- Never hardcode secrets or credentials in the code.

Known environment variables (add new ones to `.env.example`):
- `AURORA_TOKEN` — Aurora Energy Research API token
- `AURORA_API_PARAMS_PATH` — optional override path to `api_params.yaml`
- SharePoint / Graph API credentials (MSAL service principal)

---

## Testing Guidelines
- There is **no formal test suite** in this project. Validation is done interactively in notebooks.
- When adding a new function to a package, demonstrate its usage in a notebook cell or docstring example.
- For data pipeline functions, validate with a small date range before running full history.
- Parquet round-trips are a useful sanity check: write, read back, compare shapes.
- Do not introduce `pytest` or other test frameworks unless explicitly requested by the user.

---

## General Behaviour
- Before making any non-trivial change, briefly explain what you plan to do and ask for confirmation.
- When in doubt about the project structure or intent, ask rather than assume.
- Keep changes focused and minimal — do not modify files unrelated to the current task.

---

## What NOT To Do

- **Do not modify** `extractor_ref.py` — it is legacy, written in Spanish, and intentionally untouched.
- **Do not add Bloomberg imports** to `common_libs`, `api_retrieval`, or `aurora_forecasts`.
- **Do not install `blpapi` via pip/PyPI** — it is only available via conda-forge or Bloomberg SDK.
- **Do not strip Bloomberg ticker suffixes** — tickers must always carry their suffix (` Index`, ` Curncy`, etc.).
- **Do not use `from typing import List, Tuple, Dict`** — use built-in generics (`list`, `tuple`, `dict`) as required by Python 3.10+ style.
- **Do not hardcode absolute paths** — use `os.path.abspath()` or config-resolved paths.
- **Do not write processed data as CSV** — use Parquet for all persistent datasets.
- **Do not commit files to `outputs/`** — it is gitignored and contains Excel exports for end users.
- **Do not import from notebooks inside packages** — the dependency flow is one-way (packages → notebooks).
- **Do not implement your own quarter-to-date conversion** — use `get_start_date_from_quarterly()` from `common_libs`.
- **Do not use `Optional[X]`** — use `X | None` (Python 3.10+ union syntax).
- **Do not make a single API call for multi-year date ranges** — use chunking (30-day windows for ESIOS, etc.).
- **Do not add `__init__.py` exports for internal helpers** — only export the public API surface from package `__init__.py` files.
