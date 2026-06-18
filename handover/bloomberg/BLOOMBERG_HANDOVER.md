# 📈 Bloomberg Quarterly Data — Handover

**Project:** Python Unified (Exus market research & forecasting monorepo)
**Outgoing owner:** Mikel Perez
**Covers:** the Bloomberg market-data retrieval workflow (a single notebook + the `bloomberg` package).

> This is a **simple, single-notebook** workflow: one notebook pulls a set of market series from the Bloomberg Terminal and writes them to Excel. The series it pulls are defined in **one file** — the *security dictionaries* (see §4, the important part).
>
> How these Excel outputs are then used in the team's reports/decks is **out of scope here** — that is covered separately in the workflow-integration write-up.

---

## 1. What it does (in one paragraph)

The notebook **`notebooks/bloomberg/1a_quarterly_data.ipynb`** connects to the **Bloomberg Terminal**, retrieves monthly-average market data for a fixed list of securities (FX rates, European power prices, gas/CO₂/coal, metals, inflation, swap rates, government 10y yields, stock indices) plus FX forecasts, and writes each group to a **transposed Excel file** (securities as rows, dates as columns) under `outputs/quarterly/`. It runs **once per quarter**. The Excel files are then linked manually into a PowerPoint (documented separately).

---

## 2. Prerequisites & access

| Need | Detail |
|---|---|
| **Bloomberg Terminal running + logged in** | The code connects to the Terminal locally at **`localhost:8194`**. The Terminal **must be open and signed in on the same machine** before you run the notebook. There is **no API token or key** — authentication is the Terminal session itself. |
| **Bloomberg seat** | A **shared/team seat** — it persists after Mikel leaves. The new person just needs the Terminal running and logged in on the machine; no personal credential to transfer. _(This is unlike Aurora, which uses a personal token.)_ |
| **Python environment** | The `python-unified` conda env, with the `bloomberg` package installed (`pip install -e packages/bloomberg`). |
| **`blpapi`** | The Bloomberg Python library. If missing: `conda install -c conda-forge blpapi`. |
| **VS Code** | Same as the Aurora workflow — open the repo in VS Code and run the notebook there (Python + Jupyter extensions). |

---

## 3. How to run it (quarterly)

1. ✅ **Make sure the Bloomberg Terminal is open and logged in** on this machine. (If it isn't, the notebook will fail to connect.)
2. 🖱️ Open the repo in **VS Code**: **File → Open Folder…** → `C:\Users\mpy\Python Unified`.
3. In the **Explorer** panel, open `notebooks` → `bloomberg` → **`1a_quarterly_data.ipynb`**.
4. At the **top-right**, click **Select Kernel** and choose **`python-unified`**.
5. **Update the run parameters for the new quarter:**
   - `quarterly = "26Q1"` — at the **top** of the notebook.
   - `start_date = "2024-01-01"` — set inside the **two loop cells** (absolute and normalized); update **both**.
   - The **FX-forecast cell at the bottom** has its own hardcoded dates and quarter-coded tickers (`…Q426…`) — bump those too (this part is WIP; see §4 → "Special cases").
6. Click **Run All**. Check there are no red errors.
7. The Excel files appear under **`outputs\quarterly\`** — one per security group, in both **absolute** form and **normalized** form (the normalized files end in `_pu.xlsx`), plus `fx_forecasts.xlsx`.

> 💾 **Note:** `outputs/` contents are git-ignored (only the empty folder structure is committed), so these `.xlsx` files stay local — they are not pushed to the repo.

---

## 4. ⭐ The security dictionaries (the part to understand)

**File:** `packages/bloomberg/src/bloomberg/securities/security_dicts.py`

This file holds the **security lists** — flat Python dictionaries mapping a **friendly label** → a **Bloomberg ticker string**, grouped by asset class. The script defines *what* the tickers are; the **notebook** then binds each group to an output file (see "How the notebook and the script depend on each other" below — that coupling is the part people miss).

```python
fx_rate_securities = {
    'EURUSD': 'EURUSD BGN Curncy',
    'EURGBP': 'EURGBP BGN Curncy',
    ...
}

europe_daily_pool_securities = {     # European power pools
    'ES': 'OMLPDAHD Index',
    'DE': 'LPXBHRBS Index',
    ...
}

gas_securities = {
    "TTF Spot":  "TTFG1MON BCFV Index",
    "CO2 Spot":  "EECXM1 SONA Index",
    "API2 Spot": "XA1 Comdty",
}
```

The groups currently defined include: `fx_rate_securities`, `fx_forecast_securities`, `europe_daily_pool_securities`, `europe_hourly_pool_security_roots`, `europe_inflation_securities`, `europe_swap_rate_securities`, `europe_gov_10y_yield_securities`, `europe_stock_market_securities`, `gas_securities`, `wtg_securities`, `solar_n_bess_securities`, `bop_bos_securities`.

**Ticker format:** `"<TICKER> <YELLOW KEY>"` — the yellow key is the Bloomberg asset class, e.g. `Curncy` (FX), `Index` (indices/power pools/inflation), `Comdty` (commodities/metals).

### 🔗 How the notebook and the script depend on each other (the part to get right)

The security dicts on their own do nothing. The notebook `1a_quarterly_data.ipynb` is what pulls them, and it **wires each security group to a specific output file**. That wiring lives in two cells of the notebook:

**1. Output paths** — one path variable per output Excel, all under `outputs/quarterly/`:
```python
BASE_OUTPUT_DIR = os.path.abspath("../../outputs/quarterly")
fx_rates_path          = os.path.join(BASE_OUTPUT_DIR, "fx_rates.xlsx")
europe_gas_prices_path = os.path.join(BASE_OUTPUT_DIR, "europe_gas_prices.xlsx")
...
```

**2. Export configs** — `exports_abs` (absolute values) and `exports_pu` (normalized/indexed, files ending `_pu.xlsx`). Each entry **binds three things**: a security dict (from the script), an output path (from above), and a periodicity (`"M"` monthly or `"D"` daily):
```python
from bloomberg.securities.security_dicts import *

exports_abs = {
    "fx_rate_securities": {
        "securities":  fx_rate_securities,      # ← the dict from security_dicts.py
        "excel_path":  fx_rates_path,           # ← where it gets written
        "periodicity": "M",
    },
    "europe_gas_prices_securities": {
        "securities":  gas_securities,
        "excel_path":  europe_gas_prices_path,
        "periodicity": "M",
    },
    ...
}
```
The notebook then loops over these and calls the extractor:
```python
for value in exports_abs.values():
    qe.build_monthly_absolute_df(securities_dict=value["securities"],
                                 start_date=start_date,
                                 export_path=value["excel_path"],
                                 periodicity=value["periodicity"])
```

**So a security group exists in two places at once:** its tickers in `security_dicts.py`, and its binding (output path + periodicity, absolute and/or normalized) in the notebook's `exports_abs` / `exports_pu`. Change one side without the other and you either pull data with nowhere to write it, or reference a group that doesn't exist.

> The export *key* string (e.g. `"europe_gas_prices_securities"`) is only a label — the real link is the `securities` dict object paired with its `excel_path`. That's why `gas_securities` can appear under the key `"europe_gas_prices_securities"`.

### How to add / change a security

- **Add one security to an existing group** → edit *only* the dict in `security_dicts.py` (append a `"label": "TICKER yellow-key"` line). It's already bound in the notebook, so nothing else changes. **Restart the kernel** (editable install) and re-run.
- **Add a whole new group** → three edits, all required:
  1. **Script:** add the new dict in `security_dicts.py`.
  2. **Notebook (paths cell):** add `my_group_path = os.path.join(BASE_OUTPUT_DIR, "my_file.xlsx")`.
  3. **Notebook (exports cell):** add an entry to `exports_abs` (and to `exports_pu` if you want a normalized version) binding the new dict → its path → periodicity.
  Then restart the kernel and re-run.
- **Remove a group** → delete its entry from `exports_abs`/`exports_pu` (and optionally its dict + path). Deleting only the dict while leaving the export entry raises a `NameError`.
- **Fix a broken ticker** → update the string in the dict. If a futures ticker stopped returning data it has likely **rolled / been discontinued** — find the current one in the Terminal.

### Special cases (NOT driven by `exports_abs` / `exports_pu`)

- **Power prices** (`europe_daily_pool_securities`, `europe_hourly_pool_security_roots`) are also passed straight into the `QuarterlyDataExtractor(...)` constructor — the **hourly** pool is produced there (`power_prices_hourly.xlsx`), not through the export configs.
- **FX forecasts** (`fx_forecast_securities`) are handled in a **separate inline cell at the bottom**, and that block is **WIP**. Its tickers are **quarter-coded** (e.g. `FCUSEU Q426 Index` … `Q429`) and its dates are hardcoded — so it needs its **tickers and dates bumped each quarter/year**, unlike the auto-looping groups above.

---

## 5. How it connects (brief technical map)

`packages/bloomberg/src/bloomberg/`

| File | Purpose |
|---|---|
| `api_helper/extractor.py` | **`BloombergExtractor`** — wraps `blpapi`. Opens a session to `localhost:8194`, exposes `bdp()` (reference/point-in-time fields), `bdh()` (historical time series), `intraday_bars()` (e.g. hourly), and `get_chain_tickers()`. Works as a context manager (`with BloombergExtractor() as be:`), which auto-closes the session. |
| `quarterly/retrieval.py` | **`QuarterlyDataExtractor`** — high-level wrapper used by the notebook. Builds monthly **absolute** and **normalized** DataFrames from a securities dict and exports them **transposed** to Excel. |
| `securities/security_dicts.py` | The security dictionaries (§4). |
| `api_helper/extractor_ref.py` | Legacy/reference extractor with extra/older methods. **Archived — not used by the live notebook.** |
| `api_helper/trial.py`, `utils/blutils.py` | Stubs — unused. |

Connection settings (`host="localhost"`, `port=8194`) are hardcoded defaults in a `BloombergConfig` dataclass in `extractor.py`; there is no separate Bloomberg config or credentials file.

---

## 6. Troubleshooting

| What you see | Likely cause | Fix |
|---|---|---|
| Connection error / `SessionStartFailure` / can't reach `localhost:8194` | Bloomberg Terminal not running or not logged in | Open the Terminal, sign in, then re-run the notebook. |
| `ModuleNotFoundError: blpapi` | `blpapi` not installed in the env | `conda install -c conda-forge blpapi` (in the `python-unified` env). |
| `ImportError` / `ModuleNotFoundError` for `bloomberg` | Wrong kernel, or package not installed | Select the **`python-unified`** kernel; if it persists, `pip install -e packages/bloomberg`. |
| A security returns empty / errors out | The ticker is wrong, discontinued, or rolled | Verify the current ticker in the Terminal and update it in `security_dicts.py` (then **restart the kernel**). |
| Edited `security_dicts.py` but the change isn't reflected | Editable-install import is cached | **Restart the notebook kernel** and run again. |

---

## 7. Continuity

Bloomberg is **lower-risk** than Aurora for the handover:

- ✅ The Bloomberg seat is **shared/team**, so it does **not** get revoked when Mikel leaves.
- The only requirements are a machine with the **Terminal running + logged in** and the **`python-unified`** environment installed.
- There is **no personal token or secret** to transfer (contrast with Aurora's personal API token). Use Delia's or Ana's Bloomberg licenses.

The one piece of knowledge worth capturing is **maintaining the security dictionaries**
