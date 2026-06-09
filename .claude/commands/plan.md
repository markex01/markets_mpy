# Plan Before Coding

Before writing any code, produce a structured implementation plan and wait for explicit approval.

## Steps

1. **Explore** the relevant files and folders to understand the current state.
   - Read the files that will be affected.
   - Search for existing utilities or patterns that can be reused — avoid reinventing.
   - Check package dependency rules: `common_libs` ← `api_retrieval` / `aurora_forecasts` / `bloomberg`. Never reverse these.

2. **Produce the plan** with the following sections:

   ### Files
   For each file to be created, modified, or deleted:
   - Path (relative to repo root)
   - Action: CREATE / MODIFY / DELETE
   - Summary of the change (1-3 sentences)

   ### Risks
   Flag anything that could break things:
   - Cross-package import violations (Bloomberg code in common_libs, etc.)
   - Hardcoded paths or secrets
   - CSV output instead of Parquet
   - Single API call covering a multi-year range (should be chunked)
   - Removing or renaming a public function that notebooks depend on
   - Changing a Parquet schema (existing cached files will become stale)

   ### Open Questions
   List anything ambiguous that needs a decision before starting.

3. **Wait for explicit approval** — do not write a single line of code or modify any file until the user confirms.

If the user says "go ahead" or equivalent, begin implementation immediately following the approved plan.
