# AI Data Scientist Benchmark

Benchmark harness that compares Claude Code and OpenAI Codex CLI as autonomous data scientists. Each agent runs headless against 20 curated datasets, each hiding a specific statistical pattern. An LLM reviewer scores each agent's analysis against a ground-truth rubric.

## What it measures

Each dataset is designed to test whether an agent can:
- Explore data without hints from filenames or column names (files are named `dataset_001.csv` through `dataset_020.csv`)
- Identify the core statistical pattern (Simpson's paradox, heteroscedasticity, concept drift, etc.)
- Choose appropriate methods and check assumptions
- Avoid common traps (reporting only accuracy on imbalanced data, ignoring censoring, fitting linear models to quadratic data)

Datasets span regression, classification, clustering, time series, survival analysis, causal inference, and data quality challenges across realistic domains (hospital records, ad campaigns, gene expression, manufacturing QC, etc.).

## Setup

```bash
uv venv --python 3.14
uv sync
```

Authenticate the CLIs you plan to benchmark:

```bash
claude login
codex login
```

For unattended Codex runs, OpenAI also documents `CODEX_API_KEY` support for `codex exec`.

## Quick start

### Generate datasets

```bash
uv run python -m datasets.generator
```

Produces 20 CSVs in `datasets/generated/` with opaque filenames.

### Run the full benchmark

```bash
uv run python run_benchmark.py --config solo-baseline
uv run python run_benchmark.py --config solo-codex
```

This will:
1. Generate all 20 datasets
2. Run the selected agent config in an isolated temp directory per dataset
3. Score each agent's output using the LLM reviewer
4. Produce a per-config report at `results/runs/<config>/benchmark_report.md`

### Run a single agent on a single dataset

```bash
# Run Claude on simpsons_paradox only (skip dataset generation if CSVs exist)
uv run python run_benchmark.py --config solo-baseline --datasets simpsons_paradox --skip-generate

# Run Codex on two specific datasets
uv run python run_benchmark.py --config solo-codex --datasets pure_noise quadratic --skip-generate

# Run agent only, skip scoring
uv run python run_benchmark.py --config solo-baseline --datasets mnar --skip-generate --skip-score
```

### Other subset options

```bash
# All datasets, single agent
uv run python run_benchmark.py --config solo-baseline

# Re-score existing results without re-running agents
uv run python run_benchmark.py --config solo-codex --skip-generate --skip-run
```

## Tracing

Every agent run produces a detailed `trace.jsonl` in its results directory, logging each tool call with timestamps, inputs, and outputs.

**Claude Code** — Uses [hooks](https://docs.anthropic.com/en/docs/claude-code/hooks) (`.claude/hooks/trace.sh`) registered in `.claude/settings.json`. The `PostToolUse` and `PostToolUseFailure` hooks fire after every tool call and append a JSON line to `results/<agent>/<dataset>/trace.jsonl`. Each line contains:

```json
{"timestamp":"2026-03-15T12:00:00Z","event":"PostToolUse","tool":"Bash","tool_input":{"command":"python analysis.py"},"tool_response":"...","cwd":"/tmp/work"}
```

**Codex CLI** — Uses `codex -a never exec -s workspace-write --json --skip-git-repo-check`, which natively streams JSONL events (thread starts, tool executions, completions) to `trace.jsonl`. The harness also saves Codex stderr to `session.log` and the final agent message to `final_message.md`.

The reviewer reads `trace.jsonl` (when available) instead of the raw session log, giving it full visibility into the agent's step-by-step reasoning.

## Project structure

```
ai-data-scientist/
├── .claude/
│   ├── settings.json         # Hook config (PostToolUse → trace.sh)
│   └── hooks/
│       └── trace.sh          # Logs every tool call to trace.jsonl
├── .codex/
│   └── testing/
│       └── SKILL.md          # Test-writing guidance for Codex agents
├── datasets/
│   ├── generator.py          # 20 dataset generators + filename mapping
│   ├── registry.py           # Ground-truth metadata per dataset
│   └── generated/            # Output CSVs (git-ignored)
├── harness/
│   ├── prompt_template.txt   # Analysis prompt sent to both agents
│   ├── run_claude.sh         # Headless Claude Code runner (sets TRACE_FILE)
│   └── run_codex.sh          # Headless Codex CLI runner (uses --json)
├── reviewer/
│   ├── rubric.py             # 7-dimension scoring rubric (0-5 each)
│   ├── scorer.py             # LLM-based reviewer (reads trace.jsonl)
│   └── report.py             # Markdown comparison report generator
├── tests/                    # pytest suite
├── frontend/
│   ├── src/                  # Svelte 5 trace viewer
│   │   ├── App.svelte
│   │   ├── main.js
│   │   ├── global.css
│   │   └── lib/              # Components + parsing logic
│   ├── serve.py              # Production server (serves dist/)
│   ├── package.json
│   └── vite.config.js
├── results/                  # Agent outputs + scores (git-ignored)
└── run_benchmark.py          # Orchestrator
```

## Scoring

Each analysis is scored on 7 dimensions (0-5 each, max 35):

| Dimension | What it measures |
|-----------|-----------------|
| Data Loading & Inspection | Did the agent check dtypes, nulls, distributions? |
| EDA Quality | Visualizations + stats + narrative, not just `.describe()` |
| Pattern Identification | Did it find the core pattern the dataset was designed to test? |
| Method Selection | Appropriate model/technique with justification |
| Assumption Checking | Tested assumptions, adapted when violated |
| Code Quality | Clean, reproducible, runs without errors |
| Conclusions | Correct, nuanced, acknowledges limitations |

Bonus/penalty modifiers (up to +/-3) for proactive exploration, catching secondary patterns, hallucinating nonexistent patterns, or crashing.

## Trace viewer

Built with Svelte 5 + Vite.

```bash
# Production (serves built assets)
cd frontend && npm install && npm run build
uv run python frontend/serve.py

# Development (hot reload)
cd frontend && npm run dev
```

Opens `http://localhost:8080` (production) or `http://localhost:5173` (dev). Drop `trace.jsonl` and `analysis_report.md` files to load.

Features:
- Timeline of every tool call with timestamps and deltas between steps
- Color-coded icons per tool type (Bash, Read, Write, Edit, Grep, Glob)
- Expandable code blocks with line numbers, diff highlighting, language detection
- Rendered analysis report with tables, code blocks, markdown
- Plot gallery with file paths extracted from trace
- Error highlighting with inline error messages
- Click any event for the full raw JSON
- Filter by tool type, toggle responses, or show errors only
- Summary bar with events, errors, duration, cost, and turns

## Tests

```bash
uv run pytest tests/ -v
```

## Requirements

- Python 3.14+
- `uv` for package management
- `claude` CLI (for Claude Code agent runs + LLM reviewer scoring)
- `codex` CLI (for Codex agent runs)
