# Document Notebook

Analyze and document the Jupyter notebook provided as `$ARGUMENTS`.

## Your Task

You will transform the notebook into a **fully documented, professional-grade artifact** by doing two things:

1. **Add inline code comments** to every code cell — explaining the *why*, not just the *what*.
2. **Insert Markdown cells** before and after logical sections of the notebook with rich, professional formatting.

---

## Step-by-Step Instructions

### 1. Read & Understand the Notebook

- Parse the notebook file (`$ARGUMENTS`) and understand its end-to-end purpose.
- Identify the logical sections (e.g., imports, data loading, preprocessing, modelling, evaluation, visualisation, export).
- Understand the domain: is this data science, ML, finance, biology, etc.?

### 2. Add Code Comments

For every code cell:
- Add a **block comment** at the top of the cell summarising what the cell accomplishes.
- Add **inline comments** on non-obvious lines explaining intent, chosen parameters, or any gotchas.
- Do **not** comment trivially obvious lines (e.g., `import os  # imports os`).
- Use present-tense, active voice: *"Filter rows where..."* not *"This filters rows where..."*

### 3. Insert Professional Markdown Cells

Insert Markdown cells at the following points — **use the formatting rules below**:

| Position | Content |
|---|---|
| **Top of notebook** | Title banner, author/date placeholder, abstract |
| **Before each logical section** | Section header + explanation of what & why |
| **After complex operations** | Key takeaways or interpretation callouts |
| **End of notebook** | Summary & next-steps section |

---

## Markdown Formatting Rules

Use **fancy, professional Markdown** throughout. Follow these conventions:

### Notebook Title (top cell)

```markdown
# 📊 <Descriptive Title Inferred from the Notebook>

> **Author:** `<!-- your name -->`  · **Date:** `<!-- date -->`  · **Version:** 1.0

---

## Abstract

_A 3–5 sentence plain-English summary of what this notebook does, why it exists,
and what a reader will learn or produce by running it._

---
```

### Section Headers

Use H2 (`##`) for major sections and H3 (`###`) for sub-sections. Prepend a relevant emoji to every H2:

```markdown
## 📦 1 · Imports & Environment Setup
## 🗂️ 2 · Data Loading
## 🔍 3 · Exploratory Data Analysis
## ⚙️ 4 · Preprocessing & Feature Engineering
## 🤖 5 · Modelling
## 📈 6 · Evaluation & Results
## 💾 7 · Export & Next Steps
```

Adapt section names and emojis to the actual content of the notebook.

### Section Body

Each section Markdown cell should contain:

1. **What** — one sentence describing what this section does.
2. **Why** — one sentence explaining the motivation or design choice.
3. **Inputs / Outputs** — a brief bullet list of what enters and exits the section (when relevant).

Example:

```markdown
## 🔍 3 · Exploratory Data Analysis

This section profiles the raw dataset to surface data quality issues and
understand the underlying distributions before any transformation is applied.

**Why here?** Early EDA prevents assumptions from silently propagating through
the pipeline and helps justify downstream preprocessing decisions.

| | |
|---|---|
| **Input** | Raw `DataFrame` loaded in §2 |
| **Output** | Distribution plots, missing-value report, correlation matrix |
```

### Callout Boxes

Use blockquotes to highlight important findings, warnings, or decisions:

```markdown
> 💡 **Insight:** The target variable is heavily right-skewed (skewness = 3.4).
> A log-transform will be applied in §4 to stabilise variance.

> ⚠️ **Warning:** Column `revenue` contains 12 % missing values.
> Rows are dropped here because missingness appears to be MCAR.

> ✅ **Result:** Final model achieves **RMSE = 0.042** on the held-out test set.
```

### Summary Cell (bottom of notebook)

```markdown
---

## 🏁 Summary & Next Steps

### What We Did
- _Bullet recap of each major section in one line each._

### Key Results
| Metric | Value |
|---|---|
| _metric name_ | _value_ |

### Suggested Next Steps
1. _Actionable follow-up item._
2. _Another follow-up item._

---
*Generated documentation · feel free to edit and expand.*
```

---

## Output Format

- Modify the notebook **in place** (overwrite `$ARGUMENTS`).
- Preserve all existing cell outputs and metadata — do **not** re-execute cells.
- New Markdown cells must have `"cell_type": "markdown"` in the JSON.
- New comments must be embedded inside the existing `"source"` of code cells.
- Keep the notebook valid JSON / `.ipynb` format.

## Quality Bar

Before finishing, verify:
- [ ] Every code cell has at least one comment.
- [ ] Every logical section has a preceding Markdown header cell.
- [ ] The top banner cell and bottom summary cell are present.
- [ ] All Markdown uses the formatting conventions above (emojis, tables, callouts).
- [ ] The notebook still runs without errors (structure is intact).
