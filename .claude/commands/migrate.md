# Migrate Parquet Schema

This project has no SQL migrations. "Migration" here means evolving the schema of a cached Parquet file — adding, renaming, or dropping columns, or changing dtypes.

## Steps

1. **Identify the change** — describe what column(s) or dtype(s) are being added, renamed, or removed.

2. **Find affected Parquet files:**
   ```bash
   find notebooks/data/ -name "*.parquet" | sort
   ```
   List all files whose schema will be affected.

3. **Show the current schema** for each affected file:
   ```python
   import pyarrow.parquet as pq
   schema = pq.read_schema("notebooks/data/<provider>/processed/<file>.parquet")
   print(schema)
   ```

4. **Classify the change:**

   | Change type | Risk | Required action |
   |---|---|---|
   | Add column with default | Low | Re-run processing notebook; old data still valid |
   | Rename column | Medium | Old files unreadable by new code until regenerated |
   | Drop column | **HIGH** | Data permanently lost from cache; regeneration required |
   | Change dtype | Medium | May silently corrupt aggregations |

5. **Warn loudly on destructive changes.**
   - For DROP or dtype change: print a clear warning block before doing anything.
   - Suggest keeping the old file as a backup: `<file>_backup_YYYYMMDD.parquet`.

6. **Ask for confirmation** before:
   - Deleting or overwriting any `.parquet` file.
   - Re-running a processing notebook to regenerate cached data.

7. **After confirmation:**
   - Optionally rename the old file to `<file>_backup_YYYYMMDD.parquet` rather than deleting it.
   - Update the relevant processing notebook or package function.
   - Re-run validation: write the new file and read it back, compare shape and dtypes.

## Notes
- Raw files under `notebooks/data/<provider>/raw/` are **never modified** — only processed files change.
- If a schema change also requires updating the downstream code that reads the file, flag that as a separate step.
- Never delete a backup file in the same session it was created.
