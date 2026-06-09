Analyze recent project changes and update CLAUDE.md if needed.

1. Run `git log --oneline -20` to see recent commits
2. Run `git diff HEAD~10 --stat` to see what files changed most
3. Run `git diff HEAD~10 -- pyproject.toml requirements.txt` to catch dependency changes
4. Read the current .claude/CLAUDE.md
5. Explore any files that changed significantly (new modules, new routers, new models, etc.)

Then decide: did anything major change? Major means:
- New dependencies or libraries added
- New folders or architectural layers created
- New naming conventions visible in recent code
- Old modules removed or renamed
- New environment variables (check .env.example)
- New common commands in Makefile or scripts/

If yes: update only the relevant sections of CLAUDE.md. Don't rewrite everything.
If no: say "CLAUDE.md is up to date, no significant changes detected."

After updating, show a diff of what you changed and why.