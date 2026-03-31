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
mkdir -p "${WORK_DIR}/plots"

# Create a fresh venv for the agent with common DS packages
uv venv "${WORK_DIR}/.venv" --python 3.14 --quiet
uv pip install --python "${WORK_DIR}/.venv/bin/python" --quiet \
  numpy pandas scipy scikit-learn matplotlib seaborn statsmodels lifelines

# Create results directory
mkdir -p "${RESULTS_DIR}"

# Ensure the agent uses its own venv, not the project's
export VIRTUAL_ENV="${WORK_DIR}/.venv"
export PATH="${WORK_DIR}/.venv/bin:${PATH}"

# Keep a lightweight session log with the exact benchmark settings plus Codex stderr.
{
  echo "dataset=${DATASET_NAME}"
  echo "project_root=${PROJECT_ROOT}"
  echo "work_dir=${WORK_DIR}"
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
  exec
  -s workspace-write
  --json
  --ephemeral
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
