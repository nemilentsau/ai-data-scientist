#!/usr/bin/env bash
set -euo pipefail

DATASET_NAME="${1:?Usage: run_codex.sh <dataset_name> <csv_path> <results_dir> [prompt_file] [max_turns] [model] [tools]}"
DATASET_CSV="${2:?Missing dataset CSV path}"
RESULTS_DIR="${3:?Missing results directory}"
PROMPT_FILE="${4:-}"
MAX_TURNS="${5:-30}"
MODEL="${6:-}"
TOOLS="${7:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load prompt from file or fall back to default.
if [ -n "${PROMPT_FILE}" ] && [ -f "${PROMPT_FILE}" ]; then
  PROMPT="$(cat "${PROMPT_FILE}")"
else
  PROMPT="$(cat "${SCRIPT_DIR}/prompt_template.txt")"
fi

# Create isolated working directory
WORK_DIR=$(mktemp -d)

cp "${DATASET_CSV}" "${WORK_DIR}/dataset.csv"
mkdir -p "${WORK_DIR}/plots" "${WORK_DIR}/.matplotlib"

# Reuse a shared benchmark venv instead of reinstalling dependencies for every
# dataset run. The agent still sees it at ./ .venv inside the temp workspace.
BENCHMARK_VENV="${PROJECT_ROOT}/.codex-benchmark-venv"
if [ ! -x "${BENCHMARK_VENV}/bin/python" ]; then
  uv venv "${BENCHMARK_VENV}" --python 3.14 --quiet
fi
if ! "${BENCHMARK_VENV}/bin/python" - <<'PY' >/dev/null 2>&1
mods = ["numpy", "pandas", "scipy", "sklearn", "matplotlib", "seaborn", "statsmodels", "lifelines"]
for mod in mods:
    __import__(mod)
PY
then
  uv pip install --python "${BENCHMARK_VENV}/bin/python" --quiet \
    numpy pandas scipy scikit-learn matplotlib seaborn statsmodels lifelines
fi
ln -s "${BENCHMARK_VENV}" "${WORK_DIR}/.venv"

# Create results directory
mkdir -p "${RESULTS_DIR}"

# Use a benchmark-local Codex home so personal ~/.codex config does not leak
# into runs. We copy only the auth/version files needed to keep the CLI logged in.
CODEX_HOME_DIR="${WORK_DIR}/.codex-home"
mkdir -p "${CODEX_HOME_DIR}" "${CODEX_HOME_DIR}/shell_snapshots"
if [ -f "${HOME}/.codex/auth.json" ]; then
  cp "${HOME}/.codex/auth.json" "${CODEX_HOME_DIR}/auth.json"
fi
if [ -f "${HOME}/.codex/version.json" ]; then
  cp "${HOME}/.codex/version.json" "${CODEX_HOME_DIR}/version.json"
fi

# Ensure the agent uses its own venv, not the project's
export VIRTUAL_ENV="${WORK_DIR}/.venv"
export PATH="${WORK_DIR}/.venv/bin:${PATH}"
export CODEX_HOME="${CODEX_HOME_DIR}"
export MPLCONFIGDIR="${WORK_DIR}/.matplotlib"

# Keep a lightweight session log with the exact benchmark settings plus Codex stderr.
{
  echo "dataset=${DATASET_NAME}"
  echo "project_root=${PROJECT_ROOT}"
  echo "work_dir=${WORK_DIR}"
  echo "codex_home=${CODEX_HOME}"
  echo "max_turns=${MAX_TURNS}"
  echo "tools=${TOOLS}"
  codex --version 2>/dev/null || true
  echo
} > "${RESULTS_DIR}/session.log"

# On current Codex CLI builds, approval flags must be passed before `exec`,
# while exec-specific flags remain after it. `--json` gives us
# machine-readable trace events and `-o` preserves the agent's final summary
# separately from the trace.
CODEX_ARGS=(-a never)
if [ -n "${MODEL}" ]; then
  CODEX_ARGS+=(-m "${MODEL}")
fi
CODEX_ARGS+=(
  --disable plugins
  --disable shell_snapshot
  exec
  -s workspace-write
  --json
  --skip-git-repo-check
  -C "${WORK_DIR}"
  -o "${RESULTS_DIR}/final_message.md"
  "${PROMPT}"
)

# Run Codex CLI headless with JSONL trace on stdout and progress/warnings on stderr.
codex "${CODEX_ARGS[@]}" \
  > "${RESULTS_DIR}/trace.jsonl" \
  2>> "${RESULTS_DIR}/session.log" || true

# Copy outputs to results — do this BEFORE cleaning up
cp "${WORK_DIR}/analysis_report.md" "${RESULTS_DIR}/" 2>/dev/null || true
[ -d "${WORK_DIR}/plots" ] && [ "$(ls -A "${WORK_DIR}/plots" 2>/dev/null)" ] && \
  cp -r "${WORK_DIR}/plots" "${RESULTS_DIR}/"
for f in "${WORK_DIR}"/*.py; do
  [ -f "$f" ] && cp "$f" "${RESULTS_DIR}/"
done

echo "Codex analysis complete for ${DATASET_NAME}"
[ -f "${RESULTS_DIR}/trace.jsonl" ] && echo "Trace: $(wc -l < "${RESULTS_DIR}/trace.jsonl") events logged"

# Clean up
rm -rf "${WORK_DIR}"
