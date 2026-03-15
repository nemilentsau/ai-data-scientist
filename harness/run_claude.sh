#!/usr/bin/env bash
set -euo pipefail

DATASET_NAME="${1:?Usage: run_claude.sh <dataset_name> <dataset_csv_path> <results_dir>}"
DATASET_CSV="${2:?Missing dataset CSV path}"
RESULTS_DIR="${3:?Missing results directory}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROMPT="$(cat "${SCRIPT_DIR}/prompt_template.txt")"

# Create isolated working directory
WORK_DIR=$(mktemp -d)
trap "rm -rf ${WORK_DIR}" EXIT

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

# Run Claude Code headless
cd "${WORK_DIR}"
claude -p "${PROMPT}" \
  --output-format json \
  --max-turns 30 \
  --allowedTools "Bash,Read,Write,Edit,Glob,Grep" \
  2>&1 | tee "${RESULTS_DIR}/session.json"

# Copy outputs to results
cp -r "${WORK_DIR}/analysis_report.md" "${RESULTS_DIR}/" 2>/dev/null || true
cp -r "${WORK_DIR}/plots" "${RESULTS_DIR}/" 2>/dev/null || true
cp -r "${WORK_DIR}"/*.py "${RESULTS_DIR}/" 2>/dev/null || true

echo "Claude analysis complete for ${DATASET_NAME}"
echo "Trace: $(wc -l < "${TRACE_FILE}") events logged"
