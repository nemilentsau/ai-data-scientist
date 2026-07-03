# Project Rules

## Tooling & Commands
- **Python**: `uv` only (never bare `pip`). Single venv at `.venv`, Python 3.14.
- **Install deps**: `uv sync`
- **Run fake MVP smoke**: `uv run python -m eda_artifacts.cli run --adapter fake --run-id smoke --question "Assess whether monthly_rent_usd has a simple distribution."`
- **Run Codex MVP**: `uv run python -m eda_artifacts.cli run --adapter codex-exec --run-id codex-smoke --question "Assess whether monthly_rent_usd has a simple distribution."`
- **Frontend install**: `cd frontend && npm install`
- **Frontend dev**: `cd frontend && npm run dev`
- **Frontend checks**: `cd frontend && npm run check`
- **Frontend build**: `cd frontend && npm run build`
- **Frontend URL**: `http://localhost:5180/`
- **Tests**: `uv run pytest tests/ -v`
- **Single test file**: `uv run pytest tests/test_foo.py -v`
- **Lint**: `uv run ruff check`
- **Python type check**: `uv run pyright`
- **Validation scope rules**:
  - **Python files changed**: run `uv run ruff check`, `uv run pyright`, and
    `uv run pytest tests/ -v`. Iterate until all pass — 0 errors, no exceptions.

## Testing
- Read `.codex/testing/SKILL.md` before writing any test.
- Read `.codex/backend-frontend-contract/SKILL.md` before changing backend run
  output contracts, role schemas, artifact filenames/layout, lineage fields, or
  frontend run rendering.
- Tests live in `tests/`.
- Name tests after behaviour, not function names.
- One test per branch + two tests per boundary. No redundant parametrize cases.
- Do NOT test LLM outputs or prompt content — test outcomes given certain inputs.
- Backend contract/layout changes must run
  `uv run pytest tests/test_frontend_contract.py -v`. This is the mechanical
  backend-to-frontend guard; do not rely on opening the browser to discover
  rendering breakage. The guard must cover both path/schema compatibility and
  explicit agent-invocation visibility.

## Frontend UX
- Do not use cards unless the content explicitly justifies a card-like unit. Before choosing a UI element, analyze what best presents the data; when multiple presentations are viable, choose the one that does not use cards.
- The run inspector must not use fallback rendering for unknown backend
  artifacts. Unknown paths, missing required fields, or backend schema drift must
  fail in `frontend/src/selectedView.ts` and tests.
- The run inspector must expose the run's control flow as a graph, not only as
  stage folders. The harness stages and their revise / next-artifact loops are
  rendered as a node-link graph, and every agent invocation — `eda_framer`, each
  `artifact_builder` attempt, and each `visual_reviewer` attempt — must be
  derivable from `frontend/src/agentInvocations.ts` and reachable in the UI (via
  the pipeline graph's per-stage drill-in).

## Frontend Stack
- The frontend lives only in `frontend/`.
- Use Vite, React, Tailwind CSS, and strict TypeScript. The pipeline
  control-flow graph uses React Flow (`@xyflow/react`).
- The dev server must run at `http://localhost:5180/`; do not bind this project to `127.0.0.1` or Vite's default `5173` port.
- The inspector's primary flow must load repo-local runs from `runs/eda-artifacts` through the Vite dev server; do not require the user to start from an OS folder picker.
- Repo-owned frontend source and config must be TypeScript or declarative assets: `.ts`, `.tsx`, `.d.ts`, `.css`, `.html`, `.json`, or Markdown. Do not add `.js`, `.jsx`, `.mjs`, or `.cjs` files.
- `frontend/tsconfig.json` must keep `strict: true` and `allowJs: false`.
- Run `cd frontend && npm run check` before claiming frontend work is ready.
