#!/usr/bin/env bash
set -euo pipefail

DATASET_NAME="${1:?Usage: run_claude.sh <dataset_name> <dataset_csv_path> <results_dir>}"
DATASET_CSV="${2:?Missing dataset CSV path}"
RESULTS_DIR="${3:?Missing results directory}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT="$(cat "${SCRIPT_DIR}/prompt_template.txt")"

# Create isolated working directory
WORK_DIR=$(mktemp -d)
trap "rm -rf ${WORK_DIR}" EXIT

cp "${DATASET_CSV}" "${WORK_DIR}/dataset.csv"
mkdir -p "${WORK_DIR}/plots"

# Create results directory
mkdir -p "${RESULTS_DIR}"

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
