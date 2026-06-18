# 🔁 Process Overview — the two quarterly processes

**Project:** Python Unified (Exus market research & forecasting)
**Outgoing owner:** Mikel Perez

This repo's code is used in **two separate, end-to-end quarterly processes.** They share some building blocks (the same notebooks/packages) but produce **different deliverables** and are run independently:

| # | Process | What it produces | Detailed docs |
|---|---|---|---|
| 1 | **Aurora update** | Power-price report figures (heatmap) + updated master **Power Prices** and **Generation Mix** trackers on SharePoint | [aurora tracker/AURORA_QUARTERLY_RUNBOOK.md](aurora%20tracker/AURORA_QUARTERLY_RUNBOOK.md) · [aurora tracker/TECHNICAL_HANDOVER.md](aurora%20tracker/TECHNICAL_HANDOVER.md) |
| 2 | **Quarterly update** | The country slides (monthly power prices, inflation, interest rates, FX) | [bloomberg/BLOOMBERG_HANDOVER.md](bloomberg/BLOOMBERG_HANDOVER.md) |

> This document is the **map** of how the pieces compose into each process. For the click-by-click mechanics of running a given notebook, follow the linked docs. How the final figures/data are assembled into the published decks is covered separately in the workflow-integration write-up.

> ⚠️ **A recurring theme in BOTH processes:** not all data is available through the APIs. Each process has manual data that must be sourced by hand and checked every release — see the "data not available via API" notes in each process below. This is the easiest thing to forget.

---

## Process 1 — Aurora update

**Trigger:** a new Aurora release (≈ once per quarter).

### Step 0 — Prepare the notebooks
Before running anything, update the Aurora notebooks for the new release:
- corrected **quarter date** (`release = 'YYQX'` in `2c`/`2e`),
- **currency year** (`currency_year` in `2a`),
- check the **country codes** are present in `config/aurora/api_params.yaml`,
- (other per-quarter checks — see the [Aurora runbook](aurora%20tracker/AURORA_QUARTERLY_RUNBOOK.md) and [technical handover](aurora%20tracker/TECHNICAL_HANDOVER.md)).

### Step 1 — Retrieve
Run **`1a_aurora_forecasts.ipynb`** (pulls the new release into the Parquet files). Stop after the monthly fetch — the hourly section is WIP.

### Then two parallel workflows

```
                 1a (retrieve)
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
  A. PRICES                   B. GENERATION MIX
  run 2a + 2c                 run 2d + 2e
        │                           │
        ▼                           ▼
  update master              manually load into master
  Power Prices Tracker       Generation Mix Tracker
  (SharePoint)               (SharePoint)
        │                           │
        ▼                           ▼
  run 3a → heatmap_data       (done — mind the units)
        │
        ▼
  Claude skill → report
```

> ⏭️ **Note:** `2b` (monthly) is **skipped** — it is broken. See the technical handover.

#### Workflow A — Prices
1. Run **`2a`** (prices) and **`2c`** (curtailment).
2. Take the outputs into the **master Power Prices Tracker** file on SharePoint and make all the updates there.
3. **★ Document the data that is NOT available via the API**, for every release, in:
   `Market Research\Trackers - EUROPE\Prices\Backup\Aurora\Python\aurora_api_drivers_registry_prices.xlsx`
   (This registry is how the team keeps track of what had to be filled in by hand each release — keep it up to date.)
4. Go back and run **`3a_process_merged_prices.ipynb`** — it reads the now-updated master tracker and writes `outputs/trackers/heatmap_data.xlsx` (the heatmap figures).
5. Plug those figures into the report with the help of the **`refresh-aurora-slide`** Claude skill (attach `heatmap_data.xlsx`, invoke the skill).

#### Workflow B — Generation mix
1. Run **`2d`** (generation/capacity) and **`2e`** (demand).
2. **Manually load the contents into the master Generation Mix Tracker** on SharePoint.
3. **Check for data not available via the API.** As of today the only such variable is **base demand** — it must be added manually.
4. **⚠️ Mind the units:** watch MW vs GW and MWh vs GWh when loading figures into the tracker.

---

## Process 2 — Quarterly update (country slides)

**Trigger:** the quarterly cycle. **Goal:** update the **country slides** with the latest:
- **Monthly power prices**
- **Quarterly inflation**
- **Quarterly interest rates**
- **Monthly FX rates** (for **POL** and **UK** only)

### ★ Data source by country (exact)

The eight countries are **Spain, Portugal, Germany, France, Italy, Poland, UK, Ireland.** Each cell shows where that variable comes from for that country:

| Country | Monthly power prices | Quarterly inflation | Quarterly interest rates | Monthly FX |
|---|---|---|---|---|
| **Spain** (ES) | Internal Exus DB | Bloomberg | Bloomberg | — (EUR) |
| **Portugal** (PT) | Internal Exus DB | Bloomberg | Bloomberg | — (EUR) |
| **Germany** (DE) | Internal Exus DB | Bloomberg | Bloomberg | — (EUR) |
| **France** (FR) | Internal Exus DB | **INSEE (manual web)** | Bloomberg | — (EUR) |
| **Italy** (IT) | **Bloomberg** | Bloomberg | Bloomberg | — (EUR) |
| **Poland** (PL) | Internal Exus DB | Bloomberg | Bloomberg | **Bloomberg (PLN)** |
| **UK** (GB) | Internal Exus DB | Bloomberg | Bloomberg | **Bloomberg (GBP)** |
| **Ireland** (IE) | **Bloomberg** | Bloomberg | Bloomberg | — (EUR) |

How to read it:
- **Power prices** → internal **Exus DB** for ES, PT, DE, FR, PL, UK; **Bloomberg** for **Italy and Ireland**.
- **Inflation** → **Bloomberg** for everyone **except France**, which is taken by hand from the **INSEE** website.
- **Interest rates** → **Bloomberg** for all eight.
- **FX** → only the non-euro countries need it: **Poland (PLN)** and **UK (GBP)**. The euro countries have no FX.

### Steps

1. **Internal-DB power prices** — run **`notebooks/api_retrieval/exus/1a_quarterly.ipynb`**:
   - **✏️ Type the new quarter by hand** in the notebook: `quarter = '26Q2'` → set it to the quarter you're producing. (It derives the date range via `get_start_date_from_quarterly()`.)
   - It queries the internal `EuropeDAMActuals` table for `countries = ['DE','IT','ES','FR','PT','PL','GB']` and writes **`outputs/quarterly/exus_monthly_prices_<quarter>.xlsx`**.
   - **Ireland is not in the internal DB** (a code comment says to follow up with Energy Management if it's ever added) → Irish prices come from Bloomberg.
   - The notebook *does* pull **Italy** from the DB too, but for the slides Italy's price is taken from **Bloomberg** — so the DB's Italian figure is effectively superseded.
2. **Bloomberg data** — inflation, interest rates, FX, and the Bloomberg-sourced power prices (Italy + Ireland). Run the Bloomberg workflow → [bloomberg/BLOOMBERG_HANDOVER.md](bloomberg/BLOOMBERG_HANDOVER.md). Also writes to `outputs/quarterly/`.
3. **France inflation (manual)** — not in the automated pulls; extract by hand from INSEE:
   <https://www.insee.fr/fr/statistiques/8997720#tableau-ipc-flash-g1-fr>
4. All quarterly data lands in **`outputs/quarterly/`**, ready to be linked into the country slides.

> 🔐 **Note:** `1a_quarterly.ipynb` currently has **hardcoded database credentials** (a read-only user) in its first cell. Lower-risk since it's read-only, but it should be moved to `.env` and kept out of any public repo.

---

## Quick reference

```
AURORA UPDATE  (per new Aurora release)
  0. Update notebooks: quarter date, currency_year, country codes in config
  1. Run 1a  (retrieve; stop after monthly)   [skip 2b — broken]
  2. PARALLEL:
       A) 2a + 2c → update master Power Prices Tracker (SharePoint)
                  → log non-API data in aurora_api_drivers_registry_prices.xlsx
                  → run 3a → heatmap_data.xlsx → refresh-aurora-slide skill → report
       B) 2d + 2e → load into master Generation Mix Tracker (SharePoint)
                  → add base demand by hand · WATCH UNITS (MW/GW, MWh/GWh)

QUARTERLY UPDATE  (country slides)
  - Run notebooks/api_retrieval/exus/1a_quarterly.ipynb   (✏️ type quarter='26QX' inside) → outputs/quarterly/exus_monthly_prices_<quarter>.xlsx
       internal DB covers: ES PT DE FR PL UK   ·   Italy & Ireland prices → Bloomberg
  - Run Bloomberg workflow (see bloomberg handover)        → outputs/quarterly/
  - Manual exceptions:
       France inflation → INSEE website
       Italy & Ireland monthly power prices → Bloomberg
       FX + interest rates → Bloomberg (all countries)
```
