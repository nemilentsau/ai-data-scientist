# AI Data Scientist Benchmark

Benchmark harness that compares Claude Code and OpenAI Codex CLI as autonomous data scientists. Each agent runs headless against 20 curated datasets, each hiding a specific statistical pattern. An LLM reviewer scores each agent's analysis against a ground-truth rubric. Legacy run outputs can then be imported into an experiment catalog for frontend browsing and cross-run comparison.

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
uv run python run_benchmark.py --config codex-v3
```

This will:
1. Generate all 20 datasets
2. Run the selected agent config in an isolated temp directory per dataset
3. Score each agent's output using the LLM reviewer
4. Produce a per-config report at `results/runs/<config>/benchmark_report.md`
5. Refresh an experiment manifest in `results/experiments/...`

The runner refreshes experiment metadata automatically unless you pass `--skip-import`.
By default it creates a new experiment per invocation. To compare multiple configs inside the same experiment, reuse `--experiment-id` across runs and set `--experiment-title` on the first one.

```bash
uv run python run_benchmark.py --config solo-baseline --experiment-id exp_solo_compare --experiment-title "Solo compare"
uv run python run_benchmark.py --config solo-codex --experiment-id exp_solo_compare
```

### Workflow configs

The runner now supports both legacy single-agent configs and ordered multi-step workflows.

Legacy configs still work unchanged:

```yaml
name: solo-codex
team:
  - role: codex
    prompt: prompts/analyst-generic.md
    max_turns: 30
harness: harness/run_codex.sh
```

New workflow configs use a backend plus ordered steps:

```yaml
name: codex-v3
backend: codex_cli
workflow:
  steps:
    - id: analyst
      role: analyst
      prompt: prompts/analyst-v2.md
      max_turns: 30
    - id: visual_review
      role: visual_reviewer
      prompt: prompts/visual-review.md
      image_inputs:
        - plots/*.png
      required: true
```

The current built-in backends are:

- `codex_cli`
- `claude_cli`

### Import legacy runs into the experiment catalog

Use the import CLI for existing run folders that were created before automatic experiment refresh existed, or when you want to rebuild metadata from `results/runs/...`.

```bash
uv run python experiment_import.py --title "Legacy Solo Benchmark Import"
```

This creates:

- `results/experiments/catalog.sqlite` — SQLite metadata catalog
- `results/experiments/index.json` — experiment list export for the frontend
- `results/experiments/<experiment_id>/manifest.json` — per-experiment export used by the frontend

The import is metadata-only. Reports, traces, plots, session logs, and generated Python files remain in `results/runs/...` and are referenced from the catalog.

Experiment-scoped markdown notes can also be surfaced in the dashboard by
placing them under `docs/artifacts/` with YAML front matter that includes
matching `experiment_ids`.

Optional `datasets` and `config_names` front-matter fields let one note attach
to the matching case details inside that experiment.

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

Every agent run produces a top-level `trace.jsonl` in its results directory. For multi-step workflows, it is an append-only concatenation of the per-step traces in execution order.

**Claude Code** — Uses [hooks](https://docs.anthropic.com/en/docs/claude-code/hooks) (`.claude/hooks/trace.sh`) registered in `.claude/settings.json`. The `PostToolUse` and `PostToolUseFailure` hooks fire after every tool call and append JSON lines to a per-step trace, which the orchestrator then appends into the top-level `trace.jsonl`. Each line contains:

```json
{"timestamp":"2026-03-15T12:00:00Z","event":"PostToolUse","tool":"Bash","tool_input":{"command":"python analysis.py"},"tool_response":"...","cwd":"/tmp/work"}
```

**Codex CLI** — Uses `codex exec` and `codex exec resume` in a shared workspace. Each step streams JSONL events to a step trace, and the orchestrator appends those events into the top-level `trace.jsonl`. Codex stderr is saved per step and aggregated into the top-level `session.log`.

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
│   ├── prompt_template.txt   # Legacy fallback prompt
│   ├── run_claude.sh         # Legacy shim / reference runner
│   └── run_codex.sh          # Legacy shim / reference runner
├── prompts/
│   ├── analyst-generic.md
│   ├── analyst-v2.md
│   └── visual-review.md
├── ai_data_scientist/
│   ├── cli/                  # Benchmark + import CLIs
│   ├── orchestration/        # Workflow runner, workspace prep, backend adapters
│   └── experiments/          # SQLite catalog, import pipeline, dashboard export
├── reviewer/
│   ├── rubric.py             # 7-dimension scoring rubric (0-5 each)
│   ├── scorer.py             # LLM-based reviewer (reads trace.jsonl)
│   └── report.py             # Markdown comparison report generator
├── experiment_import.py      # Thin wrapper for the import CLI
├── tests/                    # pytest suite
├── frontend/
│   ├── src/                  # Svelte 5 experiment dashboard
│   │   ├── App.svelte
│   │   ├── main.js
│   │   ├── global.css
│   │   └── lib/              # Components + experiment/trace view-model logic
│   ├── serve.py              # Production server (serves built dashboard)
│   ├── package.json
│   └── vite.config.js
├── results/
│   ├── runs/                 # Raw harness outputs
│   └── experiments/          # SQLite catalog + JSON exports for the frontend
└── run_benchmark.py          # Thin wrapper for the benchmark CLI
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

## Experiment dashboard

Built with Svelte 5 + Vite.

```bash
# Production (serves built assets and exported experiment API files)
cd frontend && npm install && npm run build
uv run python frontend/serve.py

# Development (hot reload)
cd frontend && npm run dev
```

Opens `http://localhost:8080` (production) or `http://localhost:5173` (dev).

The dashboard expects imported experiments in `results/experiments/...`. In dev and build mode, Vite serves:

- `/api/experiments.json`
- `/api/experiments/<experiment_id>.json`
- `/api/artifacts/<experiment_id>/<artifact_id>/content.<ext>`

Features:
- Experiment selector and case comparison matrix
- Artifact browser with search and filters by category, dataset, config, and scope
- Lazy-loaded case detail from imported artifact metadata
- Generic artifact detail for markdown, images, JSON, traces, logs, and generated code
- Timeline of tool calls with timestamps and deltas between steps
- Rendered analysis report and plot gallery
- Summary bar with verdict, coverage, cost, duration, and turns
- Artifact-backed trace and session hydration from imported experiments

## Tests

```bash
uv run pytest tests/ -v
npm --prefix frontend test
```

## Requirements

- Python 3.14+
- `uv` for package management
- `claude` CLI (for Claude Code agent runs + LLM reviewer scoring)
- `codex` CLI (for Codex agent runs)
