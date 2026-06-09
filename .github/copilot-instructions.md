# Project Guidelines

## Project Overview
This is a monolithic Python backend API project. The entire codebase lives in a single repository.

## Language
- All code comments, docstrings, and documentation must be written in **English**.

## Core Responsibilities

### 1. Code Generation & Refactoring
- Generate new code that follows Python best practices and is consistent with the existing codebase style.
- When you identify opportunities for refactoring or improvement, **always notify the user first and wait for explicit confirmation before making any changes**.
- Never refactor proactively without asking. Describe what you would change and why, then wait.

### 2. Bug Review & Fixing
- Identify and explain bugs clearly before proposing a fix.
- Present the fix and wait for approval before applying it.

### 3. Documentation
- Write **docstrings** for all functions and classes using the Google style format.
- Add **inline comments** for complex or non-obvious logic.
- Keep the **README.md** up to date when functionality changes significantly. Propose README updates and wait for confirmation.

## Environment Variables
- The project uses a `.env` file for configuration.
- **Never expose, print, log, or commit the contents of `.env`**.
- If new environment variables are needed, add them as examples in a `.env.example` file with placeholder values.
- Never hardcode secrets or credentials in the code.

## General Behaviour
- Before making any non-trivial change, briefly explain what you plan to do and ask for confirmation.
- When in doubt about the project structure or intent, ask rather than assume.
- Keep changes focused and minimal — do not modify files unrelated to the current task.

## Project Conventions

### Bloomberg Security Tickers
- All Bloomberg tickers must include their full suffix: `" Index"`, `" Curncy"`, `" Comdty"`, etc.
- Tickers are stored **with** the suffix in `security_dicts.py`. Never strip or re-add the suffix in retrieval code.
- Example: `'ES': 'OMLPDAHD Index'` — correct. `'ES': 'OMLPDAHD'` — wrong.

### Quarterly String Format
- Quarters are represented as `"YYQX"` strings, e.g. `"25Q4"` = Q4 2025.
- Use `get_start_date_from_quarterly(quarterly)` from `common_libs.utils.utils_dates` to convert to date ranges.

### Excel Export Format
- `build_monthly_absolute_df()` and `build_monthly_normalized_df()` both return a **transposed** DataFrame (`.T`).
- This transposed format is intentional — it matches ThinkCell's expected layout.
- When concatenating results from these methods, call `.T.set_index("date")` on each before `pd.concat(..., axis=1)`.

### Outputs Directory
- All Excel exports go to `outputs/`. This folder is **not tracked by git** (in `.gitignore`).
- Never hardcode absolute paths — always use `os.path.abspath()` relative to the notebook.

### Legacy Code
- `packages/bloomberg/src/bloomberg/api_helper/extractor_ref.py` is the old Bloomberg extractor (written in Spanish). Do not modify it.
- All new Bloomberg code should use `extractor.py` and the `BloombergExtractor` class.

### Package Structure
- `common_libs` — shared date utils, finance helpers, SharePoint client. No Bloomberg dependency.
- `bloomberg` — Bloomberg Terminal integration only.
- `api_retrieval` — ESIOS, ENTSOE, AEMET, REE data pipelines.
- `aurora_forecasts` — Aurora Energy Research API.
- Notebooks import from all packages freely. Packages should not import from notebooks.
