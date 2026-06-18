# 🟢 Aurora Quarterly Update — Step-by-Step Runbook

**Audience:** anyone who needs to refresh the Aurora data each quarter. **No programming knowledge is assumed.** If you can follow a recipe, you can run this.

> **What you are doing:** Aurora publishes a new power-price forecast about once a quarter (e.g. "Iberia Q2 26"). This procedure downloads that new release and regenerates the Excel "trackers" the team uses. You run it **once per quarter**, after Aurora announces a new release.

> **How long it takes:** about **30–45 minutes**, most of which is the computer downloading and you waiting.

---

## 📖 How to read this guide

- **Part A — First-time setup** is for getting the project working on a computer. **You probably do NOT need this** — it's almost certainly already set up on Mikel's machine. Skip to Part B. Only use Part A if you're starting on a fresh computer (give it to IT or the new developer).
- **Part B — The quarterly run** is the part you do every quarter. This is the important one.
- **Part C — Checking it worked** and **Part D — When something goes wrong**.

Throughout, anything you literally type is shown `like this`. 🖱️ means "click". ⌨️ means "type".

---

## Part A — First-time setup (one time only — likely already done)

> ⏭️ **If the project already runs on the computer you're using, SKIP to Part B.** This section is best handed to the incoming developer or IT.

You need installed: **Anaconda** (Python), **Visual Studio Code** (with its Python + Jupyter extensions), the **project files**, and the **Aurora token**.

1. **Install Anaconda** — download from <https://www.anaconda.com/download> and install with default options. Then install **Visual Studio Code** from <https://code.visualstudio.com/>, open it, click the **Extensions** icon on the left bar, and install the **Python** and **Jupyter** extensions (search each name → **Install**).
2. **Get the project files** — the folder `Python Unified` (this repository). It should be copied to the computer, e.g. into `C:\Users\<you>\Python Unified`.
3. **Open "Anaconda Prompt"** (search for it in the Windows Start menu). A black text window opens.
4. **Set up the environment** — copy-paste these lines one at a time, pressing Enter after each. Wait for each to finish.
   ```powershell
   conda create -n python-unified python=3.10 -y
   conda activate python-unified
   cd "C:\Users\<you>\Python Unified"
   pip install -e packages/common_libs -e packages/api_retrieval -e packages/aurora_forecasts -e packages/bloomberg
   pip install ipykernel jupyterlab
   ```
   (Replace `<you>` with the actual Windows username / folder location.)
5. **Check the Aurora token is in place** — open the file `config\aurora\api_params.yaml` in Notepad. The first line should read `aurora_token: "..."` with a long code inside the quotes. If it says `<placeholder>` or is empty, you need a valid Aurora token (see [START_HERE](00_START_HERE.md), critical item #1).

Setup is now done. You never repeat Part A unless you move to a new computer.

---

## Part B — The quarterly run

### ☑️ Before you start

- [ ] Aurora has announced a **new release** (e.g. "Iberia Q3 26"). You need to know its **quarter code**, written as `YYQX` — for example Q3 of 2026 is **`26Q3`**, Q1 of 2027 is **`27Q1`**. Write it down; you'll type it in Step 4.
- [ ] You're on the computer where the project is set up (see Part A).

---

### Step 1 — Open the project in VS Code

1. 🖱️ Open **Visual Studio Code**.
2. 🖱️ Open the project folder: **File → Open Folder…**, select `C:\Users\mpy\Python Unified`, and click **Select Folder**. If a bar asks *"Do you trust the authors of the files in this folder?"*, click **Yes, I trust the authors**.
3. The project's files appear in the **Explorer** panel down the left-hand side. That's all you need open — there's no separate black window or web browser.

> 💡 Next time, reopen it instantly via **File → Open Recent → Python Unified**.

---

### Step 2 — Download the new Aurora release

1. In the **Explorer** panel on the left, open the folders in order:
   `notebooks` → `aurora_forecasts` → `forecasts`
2. 🖱️ Click **`1a_aurora_forecasts.ipynb`** to open it. It opens as a notebook — a series of grey "cells" you run top to bottom.
3. **Choose the environment (first run of the session):** at the **top-right** of the notebook click **Select Kernel**, then pick **`python-unified`** (under "Python Environments"). If VS Code offers to install **ipykernel**, click **Install**. VS Code usually remembers this next time.
4. Run the cells **one at a time, from the top**: click the first cell, then press **Shift + Enter**. Repeat down the notebook. A cell is finished when the spinning icon on its left turns into a number like `[5]`.
5. **Keep going until you have run the cell titled "⬇️ Fetch Monthly Forecast Scenarios" (Section 7).** Two cells — the yearly fetch (Section 5) and the monthly fetch (Section 7) — are the ones that actually download. They can each take **several minutes**; that's normal. You'll see lines like `Retrieving data for scenario: Iberia Q3 26 (Central)` scroll past, and `already in registry, skipping` for older ones.
6. 🛑 **STOP after the monthly fetch.** Everything below Section 7 (the "Hourly" section) is **experimental and unfinished** — you do not need it, and it may show a red error. That is expected and harmless. Just don't run those cells.

> 💡 **You never rename or move any files.** The download automatically adds the new release to the existing data files and skips anything already downloaded. If you re-run it, it just says "skipping" — it won't duplicate anything.

✅ When you've run through the monthly fetch with no red errors, the new raw data is saved. Move on.

---

### Step 3 — (Important) Note which notebooks to run, and which to skip

In the same `forecasts` folder you'll run these processing notebooks **in this order**:

| Run? | Notebook | Produces |
|:---:|---|---|
| ✅ | `2a_aurora_forecast_prices_processing_yearly.ipynb` | **Prices** tracker |
| ❌ **SKIP** | `2b_aurora_forecast_processing_monthly.ipynb` | _(currently broken — do not run, see note below)_ |
| ✅ | `2c_aurora_forecast_curtailment_processing_yearly.ipynb` | **Curtailment** tracker |
| ✅ | `2d_aurora_forecast_technology_processing_yearly.ipynb` | **Generation** tracker |
| ✅ | `2e_aurora_forecast_demand_processing_yearly.ipynb` | **Demand** tracker |
| ✅ | `3a_process_merged_prices.ipynb` | **Heatmap data** for the PowerPoint slides — see Step 6 _(run it after Step 5 publishing)_ |

> ⚠️ **Do not run `2b` (monthly).** It has a known bug and will fail partway through. It is not needed for the quarterly trackers. (Detail for the developer is in the technical handover.)

---

### Step 4 — Run the four processing notebooks

For **`2a`**, **`2c`**, **`2d`**, **`2e`** (in that order), do the following each time:

1. 🖱️ Double-click the notebook to open it.
2. **⚠️ Only for `2c` and `2e`:** these two have **one line you must update with the new quarter.** Near the top there is a cell containing a line like:
   ```python
   release = '26Q2'
   ```
   🖱️ Click into it and change `'26Q2'` to **the new quarter you wrote down** (e.g. `'26Q3'`). Keep the quotes. `2a` and `2d` need **no edits**.
3. Run the whole notebook: click the **Run All** button in the toolbar at the top of the notebook (▷▷ "Run All"). If asked to select a kernel, pick **`python-unified`**.
4. Wait until every cell shows a number (no more `[*]` spinners). Scroll through and check there are **no red error boxes**. (A yellow/pink *warning* is fine — only red **errors** matter.)
5. Close the notebook tab and move to the next one.

> 💡 **What the edit in 2c/2e does:** it tells the notebook which release to highlight as "the latest" in the tracker. If you forget to change it, the tracker will still build but may show the previous quarter as the newest — so don't skip it.

> ⭐ **Expect this from time to time — it is the most common hiccup.** Aurora is **not consistent** about the data they publish: a new release sometimes contains brand-new variables (a new price type, a new commodity, a new region) that the tool has never seen. When that happens, **`2a` (and sometimes `2c`/`2e`) will stop with a red `ValueError` containing words like _"have not been mapped"_.**
>
> This is **not your mistake** and **not something you can fix by re-running.** It means a developer needs to add the new Aurora item to the tool's "dictionary" so it knows what to do with it. **What to do:** copy the exact red error text (and ideally a screenshot), note which notebook it happened in, and send it to the developer / Mikel. It's usually a 10-minute fix for them. See Part D below.

> ℹ️ **Occasionally (not every quarter):** Aurora may also rename things or add a new scenario sensitivity. Same rule — if a tracker looks wrong or a notebook errors, that's a flag to ask the developer, not something to force through.

---

### Step 5 — Find your results

After 2a/2c/2d/2e finish, the freshly built Excel trackers are saved here inside the project folder:

| Tracker | File location |
|---|---|
| Prices | `outputs\trackers\prices_tracker.xlsx` |
| Curtailment | `outputs\trackers\curtailment_tracker.xlsx` |
| Generation / capacity | `data\aurora\processed\generation_tracker.xlsx` |
| Demand | `outputs\trackers\demand_tracker.xlsx` |

🖱️ Open each in Excel and have a quick look (see Part C for what "looks right" means).

> 📤 **Publishing is manual.** The generated trackers are **copied by hand into the master tracker files on SharePoint** — the automatic upload in the code is only partly working, so don't rely on it.
> - **Prices (`2a`) and Curtailment (`2c`)** → update the master **Power Prices Tracker** on SharePoint. While doing this, **log any data that wasn't available through the Aurora API**, for this release, in:
>   `Market Research\Trackers - EUROPE\Prices\Backup\Aurora\Python\aurora_api_drivers_registry_prices.xlsx`
> - **Generation (`2d`) and Demand (`2e`)** → load into the master **Generation Mix Tracker** on SharePoint. Add any non-API data by hand (currently only **base demand**) and **mind the units** (MW/GW, MWh/GWh).
>
> The master Power Prices Tracker must be updated **before** Step 6, because `3a` reads it. See [PROCESS_OVERVIEW.md](../PROCESS_OVERVIEW.md) for the full end-to-end picture.

---

### Step 6 — Generate the heatmap data for the PowerPoint slides

This step produces the data behind the quarterly **PowerPoint heatmap slides**, so it is part of the normal quarterly run (not optional).

- 🖱️ Open **`3a_process_merged_prices.ipynb`**. It reads the **master price tracker from SharePoint**, so **Step 5's publishing must already be done** and your OneDrive/SharePoint must be synced.
- If prompted, set the kernel to **`python-unified`** (top-right), then click the **Run All** button. Check there are no red errors.
- It writes **`outputs\trackers\heatmap_data.xlsx`**.
- 📊 **Then update the slides:** in Claude, attach that `heatmap_data.xlsx` file and invoke the **`refresh-aurora-slide`** skill — the heatmap slide is updated automatically.

---

## Part C — How to check it actually worked

A quick sanity check after each run:

- ✅ **No red error boxes** in any notebook you ran (warnings in yellow/pink are OK).
- ✅ Each tracker Excel file's **"last modified" time** is today.
- ✅ Open `prices_tracker.xlsx` — there should be a **new column/section for the new release** (the quarter you just downloaded). Numbers should look like sensible power prices (roughly tens of €/MWh, not blanks or huge/negative nonsense).
- ✅ In Step 2 you saw `Retrieving data for scenario: …Q… 26…` lines for the **new** release (not only "skipping" lines). If you saw *only* "skipping" messages, the new release may not be published yet, or was already downloaded.

If all four boxes tick, you're done. 🎉

---

## Part D — When something goes wrong

| What you see | What it means | What to do |
|---|---|---|
| Step 2 shows **only** "already in registry, skipping" and no "Retrieving…" lines | The new release isn't downloading | Check the new Aurora release is actually published yet. If it is, the token may be expired — see [START_HERE](00_START_HERE.md) item #1, or call the developer. |
| Red error mentioning **`token`**, **`401`**, **`403`**, or **`Unauthorized`** | The Aurora token is invalid/expired | Retrieve a fresh token from the **Aurora EOS Platform** and paste it into `config\aurora\api_params.yaml` (the `aurora_token` line). Usually a developer task. |
| Red error mentioning **`ImportError`** or **`ModuleNotFoundError`** | The Python environment isn't active or isn't installed | Make sure you ran `conda activate python-unified` (Step 1.2). If it persists, the environment may need reinstalling (Part A) — get the developer. |
| Red **`ValueError`** with text like **"have not been mapped"** (in `2a`, `2c` or `2e`) | ⭐ **Common.** Aurora published a new variable/region this release that the tool doesn't recognise yet | **Not fixable by re-running.** It needs a developer to add the new item to the mapping dictionary (`dicts.py`). Copy the exact red text + which notebook, and send it on. Usually a quick fix. |
| Red error mentioning a **file path** or **`No such file`** | A data file or the SharePoint sync is missing | Check OneDrive is synced and signed in. Note the exact red text and send it to the developer. |
| Error in **`2b`** | Expected — `2b` is broken | You should not be running `2b`. Skip it (Step 3). |
| VS Code is unresponsive / a cell is stuck on the spinner forever | A cell hung | Click **Restart** in the notebook toolbar at the top, then run that notebook again from the first cell. |
| Everything looks weird and you're not sure | — | **Stop. Don't delete anything.** Take a screenshot of the red error and send it to the developer / Mikel. Nothing you do by *re-running* will break the source data — the worst case is you re-download. |

> 🆘 **Golden rule:** if in doubt, **do not delete files** and **do not "fix" the code**. Re-running the notebooks is always safe. Reach out with a screenshot of the red error text.

---

## Quick reference card (print this)

```
QUARTERLY AURORA UPDATE  —  ~30–45 min
─────────────────────────────────────────
0. Know the new quarter code, e.g. 26Q3
1. VS Code → File > Open Folder > C:\Users\mpy\Python Unified
2. Open  notebooks/aurora_forecasts/forecasts/1a_aurora_forecasts.ipynb
   → top-right: Select Kernel = python-unified
   → Shift+Enter through to "Fetch Monthly" (Section 7), then STOP
   (ignore/skip the experimental Hourly section)
3. Run, in order, via the "Run All" button:
     2a   (no edit)
     2c   (edit:  release = '26Q3')
     2d   (no edit)
     2e   (edit:  release = '26Q3')
     -- SKIP 2b (broken) --
4. Check outputs\trackers\*.xlsx  +  data\aurora\processed\*.xlsx
   → modified today, new release column present, no red errors
5. Publish trackers to SharePoint  (see Step 5 — confirm with Mikel)
6. Run 3a_process_merged_prices  → outputs\trackers\heatmap_data.xlsx
   → in Claude: attach that file + run skill "refresh-aurora-slide"  (updates the PPT heatmap)
─────────────────────────────────────────
Trouble? Screenshot the RED text. Don't delete anything.
```
