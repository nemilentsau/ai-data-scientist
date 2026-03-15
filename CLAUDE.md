# Project Rules

## Tooling & Commands
- **Python**: `uv` only (never bare `pip`). Single venv at `.venv`, Python 3.14.
- **Install deps**: `uv sync`
- **Run benchmark**: `uv run python run_benchmark.py`
- **Generate datasets**: `uv run python -m datasets.generator`
- **Tests**: `uv run pytest tests/ -v`
- **Single test file**: `uv run pytest tests/test_foo.py -v`
- **Lint**: `uv run ruff check` (if ruff is added)
- **Validation scope rules**:
  - **Python files changed**: run tests. Iterate until all pass — 0 errors, no exceptions.

## Testing
- Read `.claude/testing/SKILL.md` before writing any test.
- Tests live in `tests/`.
- Name tests after behaviour, not function names.
- One test per branch + two tests per boundary. No redundant parametrize cases.
- Do NOT test LLM outputs or prompt content — test outcomes given certain inputs.
