#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE="${SCRIPT_DIR}/paper_trade_pipeline.py"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "${LOG_DIR}"

LOGFILE="${LOG_DIR}/paper_trade_$(date +%Y-%m-%d).log"

echo "--- $(date '+%Y-%m-%d %H:%M:%S') ---" >> "${LOGFILE}"
echo "[$(date '+%H:%M:%S')] Running paper_trade_pipeline.py $*" >> "${LOGFILE}"

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "[$(date '+%H:%M:%S')] python3 not found; set PYTHON_BIN or install python3" | tee -a "${LOGFILE}" >&2
  exit 127
fi

if [[ ! -f "${PIPELINE}" ]]; then
  echo "[$(date '+%H:%M:%S')] Pipeline entrypoint not found: ${PIPELINE}" | tee -a "${LOGFILE}" >&2
  exit 1
fi

"${PYTHON_BIN}" -u "${PIPELINE}" "$@" 2>> "${LOGFILE}" | tee -a "${LOGFILE}"
pipeline_exit=${PIPESTATUS[0]}
if [[ ${pipeline_exit} -ne 0 ]]; then
  echo "[$(date '+%H:%M:%S')] paper_trade_pipeline.py failed with code ${pipeline_exit}" >> "${LOGFILE}"
  exit ${pipeline_exit}
fi
