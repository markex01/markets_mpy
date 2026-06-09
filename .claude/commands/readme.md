# Update README

Review the current state of the project and update README.md accordingly.

Check that the following sections exist and are accurate:

- **Project description** — what this monorepo does and what problem it solves.
- **Requirements** — Python version (3.10 exactly) and key dependencies.
- **Installation** — conda environment creation, editable package installs, Jupyter kernel registration.
- **Environment variables** — mention that a `.env` file is needed and refer to `.env.example` for required variables. List known variables: `AURORA_TOKEN`, `AURORA_API_PARAMS_PATH`, SharePoint/Graph API credentials.
- **How to run** — `jupyter lab` launch command and kernel selection.
- **Repository layout** — high-level folder tree with intent of each folder (`packages/`, `notebooks/`, `outputs/`, `scripts/`, `config/`).
- **Notebook structure** — domain subfolders, numbered execution order (`1a_`, `2a_`, ...), and data flow (raw → processed → analysis).
- **Package summaries** — one-paragraph description per package (`common_libs`, `api_retrieval`, `aurora_forecasts`, `bloomberg`) with submodule table.

If any section is missing or outdated, propose the new content and **wait for confirmation before making changes**.

Do not add sections about HTTP endpoints, API routes, or server commands — this project has no server.
