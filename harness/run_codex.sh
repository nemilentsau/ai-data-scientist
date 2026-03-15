#!/usr/bin/env bash
set -euo pipefail

DATASET_NAME="${1:?Usage: run_codex.sh <dataset_name> <dataset_csv_path> <results_dir>}"
DATASET_CSV="${2:?Missing dataset CSV path}"
RESULTS_DIR="${3:?Missing results directory}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT="$(cat "${SCRIPT_DIR}/prompt_template.txt")"

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

# Run Codex CLI headless with --json for structured JSONL trace
cd "${WORK_DIR}"
codex exec \
  --approval-mode full-auto \
  --json \
  -q "${PROMPT}" \
  > "${RESULTS_DIR}/trace.jsonl" \
  2> "${RESULTS_DIR}/session.log" || true

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
