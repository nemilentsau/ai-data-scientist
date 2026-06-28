# Project Rules

## Tooling & Commands
- **Python**: `uv` only (never bare `pip`). Single venv at `.venv`, Python 3.14.
- **Install deps**: `uv sync`
- **Run fake MVP smoke**: `uv run python -m eda_artifacts.cli run --adapter fake --run-id smoke`
- **Run Codex MVP**: `uv run python -m eda_artifacts.cli run --adapter codex-exec --run-id codex-smoke`
- **Frontend install**: `cd frontend && npm install`
- **Frontend dev**: `cd frontend && npm run dev`
- **Frontend checks**: `cd frontend && npm run check`
- **Frontend build**: `cd frontend && npm run build`
- **Frontend URL**: `http://localhost:5180/`
- **Tests**: `uv run pytest tests/ -v`
- **Single test file**: `uv run pytest tests/test_foo.py -v`
- **Lint**: `uv run ruff check` (if ruff is added)
- **Validation scope rules**:
  - **Python files changed**: run tests. Iterate until all pass — 0 errors, no exceptions.

## Testing
- Read `.codex/testing/SKILL.md` before writing any test.
- Tests live in `tests/`.
- Name tests after behaviour, not function names.
- One test per branch + two tests per boundary. No redundant parametrize cases.
- Do NOT test LLM outputs or prompt content — test outcomes given certain inputs.

## Frontend UX
- Do not use cards unless the content explicitly justifies a card-like unit. Before choosing a UI element, analyze what best presents the data; when multiple presentations are viable, choose the one that does not use cards.

## Frontend Stack
- The frontend lives only in `frontend/`.
- Use Vite, React, Tailwind CSS, and strict TypeScript.
- The dev server must run at `http://localhost:5180/`; do not bind this project to `127.0.0.1` or Vite's default `5173` port.
- Repo-owned frontend source and config must be TypeScript or declarative assets: `.ts`, `.tsx`, `.d.ts`, `.css`, `.html`, `.json`, or Markdown. Do not add `.js`, `.jsx`, `.mjs`, or `.cjs` files.
- `frontend/tsconfig.json` must keep `strict: true` and `allowJs: false`.
- Run `cd frontend && npm run check` before claiming frontend work is ready.
