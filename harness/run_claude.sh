#!/usr/bin/env bash
set -euo pipefail

DATASET_NAME="${1:?Usage: run_claude.sh <dataset_name> <csv_path> <results_dir> [prompt_file] [max_turns] [model] [tools]}"
DATASET_CSV="${2:?Missing dataset CSV path}"
RESULTS_DIR="${3:?Missing results directory}"
PROMPT_FILE="${4:-}"
MAX_TURNS="${5:-30}"
MODEL="${6:-}"
TOOLS="${7:-Bash,Read,Write,Edit,Glob,Grep}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load prompt from file or fall back to default
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

# Set TRACE_FILE so the PostToolUse hook logs every step
export TRACE_FILE="${RESULTS_DIR}/trace.jsonl"
echo "Trace file: ${TRACE_FILE}"

# Copy hook config into the work dir so claude picks it up
mkdir -p "${WORK_DIR}/.claude/hooks"
cp "${PROJECT_ROOT}/.claude/settings.json" "${WORK_DIR}/.claude/settings.json"
cp "${PROJECT_ROOT}/.claude/hooks/trace.sh" "${WORK_DIR}/.claude/hooks/trace.sh"

# Ensure the agent uses its own venv, not the project's
export VIRTUAL_ENV="${WORK_DIR}/.venv"
export PATH="${WORK_DIR}/.venv/bin:${PATH}"

# Build claude command
CLAUDE_ARGS=(-p "${PROMPT}" --output-format json --max-turns "${MAX_TURNS}" --allowedTools "${TOOLS}")
if [ -n "${MODEL}" ]; then
  CLAUDE_ARGS+=(--model "${MODEL}")
fi

# Run Claude Code headless
cd "${WORK_DIR}"
claude "${CLAUDE_ARGS[@]}" > "${RESULTS_DIR}/session.json" 2>&1 || true

# Copy outputs to results — do this BEFORE cleaning up
cp "${WORK_DIR}/analysis_report.md" "${RESULTS_DIR}/" 2>/dev/null || true
[ -d "${WORK_DIR}/plots" ] && [ "$(ls -A "${WORK_DIR}/plots" 2>/dev/null)" ] && \
  cp -r "${WORK_DIR}/plots" "${RESULTS_DIR}/"
for f in "${WORK_DIR}"/*.py; do
  [ -f "$f" ] && cp "$f" "${RESULTS_DIR}/"
done

echo "Claude analysis complete for ${DATASET_NAME}"
[ -f "${TRACE_FILE}" ] && echo "Trace: $(wc -l < "${TRACE_FILE}") events logged"

# Clean up
rm -rf "${WORK_DIR}"
