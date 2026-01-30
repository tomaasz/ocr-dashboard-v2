# AGENTS.md - OCR Dashboard V2

## Commands
- **Run server**: `./scripts/start_web.sh` or `uvicorn app.main:app --port 9090`
- **Lint/Format**: `ruff check . && ruff format .` (auto-fix: `ruff check --fix .`)
- **Test all**: `pytest tests/`
- **Single test**: `pytest tests/path/test_file.py::test_function -v`
- **Type check**: Uses Pydantic v2 for runtime validation

## Architecture
- **Framework**: FastAPI with Jinja2 templates, served on port 9090
- **Database**: PostgreSQL via `psycopg2` (DSN in `OCR_PG_DSN` env var)
- **Structure**: `app/routes/` (thin API layer) → `app/services/` (business logic) → `app/models/` (Pydantic)
- **Static files**: `static/`, templates: `templates/`
- **Config**: `app/config.py` reads all settings from environment variables

## Repo Layout (Single Repo)
- **Primary repo**: develop and sync here
  - Linux/WSL: `~/ocr-dashboard-v2`
  - Windows: `C:\Dev\ocr-dashboard-v2`

## Code Style
- **Python 3.11+**, PEP 8, max line length 100 (ruff enforced)
- **Type hints required** on all functions; use Pydantic models for validation
- **Imports**: stdlib → third-party → first-party (`app.*`), sorted by ruff/isort
- **Naming**: `snake_case` files/functions, `PascalCase` classes, `UPPER_SNAKE_CASE` constants
- **Async**: Use `async/await` for all I/O; parameterized queries only (no string interpolation)
- **Errors**: Catch specific exceptions, log with context, return `HTTPException` with proper status codes
- **No bare `except:`**, no secrets in code/logs, Google-style docstrings for public APIs
