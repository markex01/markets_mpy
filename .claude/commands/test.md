# Validate / Test

This project has no formal test suite. Validation is done interactively via Python REPL or notebook cells.

## Steps

1. **Identify what to validate** from the task description or the current file.

2. **Run import verification** first:
   ```bash
   python -c "import common_libs; import api_retrieval; import aurora_forecasts; import bloomberg; print('All packages OK')"
   ```
   If this fails, stop and report the error before going further.

3. **Run the appropriate validation** for the type of change:

   **For a new or modified package function:**
   - Call the function with a minimal, safe input (small date range, single indicator, single country).
   - Print the result shape, dtypes, and first few rows.
   - Never use a multi-year range for validation — use 7-30 days maximum.

   **For a Parquet read/write change:**
   - Write a small DataFrame to a temp path under `notebooks/data/temp/`.
   - Read it back immediately.
   - Assert shape and dtypes match.
   - Delete the temp file after.

   **For a configuration change:**
   - Instantiate the config object and print each resolved path.
   - Confirm no `FileNotFoundError` is raised.

   **For a notebook cell change:**
   - Describe which cell to re-run and what the expected output should be.
   - Do not run notebooks programmatically unless the user asks for it.

4. **Report results:**
   - Show stdout/stderr output.
   - If validation passes: summarise what was confirmed.
   - If validation fails: explain the root cause clearly, propose a fix, and **wait for approval before modifying any source file**.

Never modify source code silently to make a validation pass.
