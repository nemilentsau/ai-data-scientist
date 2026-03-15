#!/usr/bin/env bash
set -euo pipefail

DATASET_NAME="${1:?Usage: run_codex.sh <dataset_name> <dataset_csv_path> <results_dir>}"
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

# Run Codex CLI headless with --json for structured JSONL trace
cd "${WORK_DIR}"
codex exec \
  --approval-mode full-auto \
  --json \
  -q "${PROMPT}" \
  > "${RESULTS_DIR}/trace.jsonl" \
  2> "${RESULTS_DIR}/session.log"

# Also save just the final assistant message
codex exec \
  --approval-mode full-auto \
  -o "${RESULTS_DIR}/codex_output.txt" \
  -q "${PROMPT}" \
  2>/dev/null || true

# Copy outputs to results
cp -r "${WORK_DIR}/analysis_report.md" "${RESULTS_DIR}/" 2>/dev/null || true
cp -r "${WORK_DIR}/plots" "${RESULTS_DIR}/" 2>/dev/null || true
cp -r "${WORK_DIR}"/*.py "${RESULTS_DIR}/" 2>/dev/null || true

echo "Codex analysis complete for ${DATASET_NAME}"
echo "Trace: $(wc -l < "${RESULTS_DIR}/trace.jsonl") events logged"
