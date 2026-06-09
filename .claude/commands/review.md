Arguments: $FILE

Add documentation to $FILE without modifying any logic.

1. Read the file and list every function/class that is missing a docstring
2. Show me the plan — what you will add and where
3. Wait for my confirmation before writing anything

Rules:
- Google-style docstrings only (Args, Returns, Raises)
- Inline comments only for non-obvious logic
- Do NOT modify existing docstrings or comments
- Do NOT change any logic, signatures, or structure
- Write all new documentation in English

After applying: show a git diff so I can verify only documentation was added.