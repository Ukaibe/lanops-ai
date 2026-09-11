# Repository Guidelines

## Project Structure & Module Organization

This repository is a Dockerized FastAPI and LangGraph service. `main.py` exposes the app; `lanops_ai/` contains API, agent, tool, RAG, security, and syslog modules. Automated tests live in `tests/`, while `test_main.http` provides manual requests. Nginx configuration is in `nginx/`, the static client is in `web/`, and Compose orchestration is in `compose.yaml`.

## Build, Test, and Development Commands

- `uv sync` creates or updates the local environment from `pyproject.toml` and `uv.lock`.
- `uv run uvicorn main:app --reload` starts the API at `http://127.0.0.1:8000` with development reloads.
- `uv run uvicorn main:app` runs the service without reload behavior.
- `uv run pytest` runs the automated test suite.
- `uv run ruff check .` checks formatting and lint rules.
- `docker compose up --build` starts Nginx, the API, Ollama, and model initialization.
- Open `test_main.http` in PyCharm and execute each request to smoke-test the current routes.

Python 3.14 or newer is required. Commit changes to `uv.lock` whenever dependency updates alter the resolved environment.

## Coding Style & Naming Conventions

Follow PEP 8 with four-space indentation and type annotations for function parameters and return values where practical. Use `snake_case` for modules, functions, and variables; use `PascalCase` for classes; use uppercase names for constants. Keep route handlers small and move business logic into focused modules as it develops. Prefer explicit imports and concise docstrings for non-obvious behavior. No formatter or linter is currently configured; avoid introducing tool-specific formatting churn in unrelated changes.

## Testing Guidelines

Tests use `pytest` and FastAPI's test client; no coverage threshold is currently enforced. Add files named `test_<module>.py` and functions named `test_<behavior>()`. Mock Ollama and network devices in unit tests; reserve live-device checks for explicitly configured integration tests.

## Commit & Pull Request Guidelines

Git history is not available in this checkout. Use short, imperative commit subjects such as `Add device status endpoint`, keeping each commit focused. Pull requests should summarize the change, explain how it was tested, link relevant issues, and call out API or dependency changes. Include example requests and responses when endpoint behavior changes; screenshots are useful only for documentation or UI changes.

## Security & Configuration

Do not commit credentials, tokens, local `.env` files, or machine-specific `.idea/workspace.xml` settings. Read secrets from environment variables and document any new required configuration in the pull request.
