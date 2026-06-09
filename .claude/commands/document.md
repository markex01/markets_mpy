Arguments: $FILE

Add documentation to $FILE without modifying any existing code.

1. Read the file and list every function and class that is missing a docstring
2. Show me that list and wait for my confirmation before writing anything

Rules:
- Google-style docstrings only (Args, Returns, Raises sections)
- Inline comments only for non-obvious logic — do not comment obvious code
- Skip functions that already have a docstring — do not modify existing ones
- Do NOT change any existing code in any way: no reformatting, no renaming, no reordering
- Write all new documentation in English

After applying: run `git diff $FILE` and show it so I can verify only documentation was added.