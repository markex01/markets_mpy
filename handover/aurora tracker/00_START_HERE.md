# 📌 Project Handover — START HERE

**Project:** Python Unified (Exus market research & forecasting monorepo)
**Outgoing owner:** Mikel Perez
**Date prepared:** June 2026
**Primary focus of this handover:** the **Aurora** power-price forecasting pipeline.

---

## Who should read what

This handover has **three documents**. Read the one that matches you.

| You are… | Read this | What it gives you |
|---|---|---|
| **The manager / interim owner** (non-technical) | 👉 **[AURORA_QUARTERLY_RUNBOOK.md](AURORA_QUARTERLY_RUNBOOK.md)** | A click-by-click guide to run the Aurora update yourself each quarter — no coding knowledge assumed. |
| **The future developer** (takes over the code) | 👉 **[TECHNICAL_HANDOVER.md](TECHNICAL_HANDOVER.md)** | Architecture, how everything fits together, known issues, and the backlog. |
| **Anyone** | This file | Orientation + the critical "what happens when Mikel leaves" checklist below. |

> The repo's root [`README.md`](../../README.md) is still useful background, but parts are out of date — see the "Known documentation gaps" section in the technical handover before trusting it.

---

## What this project does (in one paragraph)

Exus needs forward power-price forecasts and related market data (generation mix, demand, curtailment) for eight European markets. This repository pulls that data from external providers — chiefly **Aurora Energy Research** (via their API) but also ENTSO-E, ESIOS, AEMET and Bloomberg — cleans it, adjusts it for inflation, and writes **Excel "trackers"** that feed the team's market-research reporting and the price-forecast dashboards. Aurora releases new forecasts roughly **once a quarter**, and the main recurring job is to refresh our data when a new Aurora release comes out.

---

## ⚠️ CRITICAL — things that may BREAK when Mikel's account is deactivated

These are the items most likely to silently stop the pipeline working once Mikel leaves. **Action each one before the leaving date.**

| # | Item | Where it lives | Why it matters | Owner after handover |
|---|---|---|---|---|
| 1 | **Aurora API token** | `config/aurora/api_params.yaml` → `aurora_token` | This is the live key that downloads Aurora data. **It is a personal token, so it stops working once Mikel leaves → the whole pipeline stops.** A fresh token must be retrieved from the **Aurora EOS Platform** and pasted into the YAML. | New hire — get a fresh token from the Aurora EOS Platform |
| 2 | **SharePoint sync (OneDrive)** | Root `.env` file → `SP_BASE_PATH` (git-ignored, loaded via python-dotenv). Value: `C:\Users\mpy\OneDrive - Exus Management Partners\EU - Strategy & Markets - Documentos` | Several notebooks read/write the master trackers from this OneDrive-synced SharePoint folder. On a new machine: re-sync OneDrive and re-create `.env` with this variable. | New hire / IT |
| 3 | **Bloomberg** | Bloomberg Terminal login (**shared/team seat**) | The Bloomberg notebook only works on a machine with the Terminal running + logged in. The seat is shared/team, so it **persists after Mikel leaves** — no personal credential to transfer. See [bloomberg/BLOOMBERG_HANDOVER.md](../bloomberg/BLOOMBERG_HANDOVER.md). | New hire — just needs the Terminal running |
| 4 | **The working machine** | Mikel's laptop | The Python environment, the OneDrive sync, and the Aurora token are all set up on this machine. If it's wiped, everything has to be re-installed from scratch (see runbook Part A). | IT / new hire |

> 🔐 **Security note:** API tokens are currently stored in plain-text YAML files inside the repo. This is convenient but not best practice. The technical handover lists this as a known issue. **Do not email these files or commit them to a public repo.**

---

## The 60-second mental model

```
   ┌─────────────────────────────────────────────────────────┐
   │  EXTERNAL PROVIDERS                                     │
   │  Aurora API · ENTSO-E · ESIOS · AEMET · Bloomberg       │
   └───────────────────────────┬─────────────────────────────┘
                               │  "retrieval" notebooks (1a, 1c…)
                               ▼
   ┌─────────────────────────────────────────────────────────┐
   │  RAW DATA on disk  ·  data/aurora/*.parquet             │
   │  (downloaded once, then appended to each quarter)       │
   └───────────────────────────┬─────────────────────────────┘
                               │  "processing" notebooks (2a, 2c, 2d, 2e…)
                               ▼
   ┌─────────────────────────────────────────────────────────┐
   │  EXCEL TRACKERS  ·  outputs/trackers/*.xlsx             │
   │  prices · curtailment · generation · demand             │
   └───────────────────────────┬─────────────────────────────┘
                               │  uploaded / pasted into SharePoint
                               ▼
   ┌─────────────────────────────────────────────────────────┐
   │  Master trackers + dashboards used by the team          │
   └─────────────────────────────────────────────────────────┘
```

**The recurring job** = "a new Aurora release came out → refresh the raw data → re-run the processing → publish the updated trackers." That whole job is what the [runbook](AURORA_QUARTERLY_RUNBOOK.md) walks you through.

---

## ✍️ For Mikel — please fill these in before you go

The code tells me *what* runs, but only you know these human details. Please complete them so the handover is usable:

- [ ] **How often is the dashboard (`3a_process_merged_prices` + `input.html`) actually refreshed, and who consumes it?**
I use 3a for getting the heatmap data, stored in `outputs/trackers/heatmap_data.xlsx`. That file is then used inside the PowerPoint heatmap slides. Claude has a skill that is "refresh-aurora-slide", so by attaching the heatmap data file and invoking the skill, slide will be automatically updated.
- [ ] **Is the Aurora token a shared/service credential or your personal one?** My token is personal, but a new one can be retrieved from Aurora EOS Platform
