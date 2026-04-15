#!/bin/bash
set -euo pipefail

# Cron-safe wrapper for the Phase 7 live portfolio scanner.
# Logs output, handles failures gracefully, optionally posts to Discord.
#
# Usage:
#   ./scan_live.sh                      # default scan
#   ./scan_live.sh --discord             # Discord-formatted output
#   ./scan_live.sh --cache-only          # offline / no API calls
#
# Cron example (every 30 min during race hours, ET):
#   */30 12-19 * * 1-6 /path/to/scan_live.sh --discord >> /path/to/scan.log 2>&1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCANNER="${SCRIPT_DIR}/live_portfolio_scanner.py"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
LOG_DIR="${SCRIPT_DIR}/logs"
OUT_DIR="${SCRIPT_DIR}/out"

mkdir -p "${LOG_DIR}" "${OUT_DIR}"

LOGFILE="${LOG_DIR}/scan_$(date +%Y-%m-%d).log"
LATEST_TXT="${OUT_DIR}/live_scan_latest.txt"
LATEST_JSON="${OUT_DIR}/live_scan_latest.json"

CACHE_TTL="${SCAN_CACHE_TTL:-900}"
MAX_RACES="${SCAN_MAX_RACES:-12}"
BASE_STAKE="${SCAN_BASE_STAKE:-1.0}"

DEFAULT_ARGS=(
  --cache-ttl "${CACHE_TTL}"
  --max-races "${MAX_RACES}"
  --base-stake "${BASE_STAKE}"
  --save "${LATEST_JSON}"
)

echo "--- $(date '+%Y-%m-%d %H:%M:%S') ---" >> "${LOGFILE}"
echo "[$(date '+%H:%M:%S')] Running scanner with defaults: cache_ttl=${CACHE_TTL}s max_races=${MAX_RACES} base_stake=${BASE_STAKE}" >> "${LOGFILE}"

if [[ -z "${PYTHON_BIN}" ]]; then
    echo "[$(date '+%H:%M:%S')] python3 not found; set PYTHON_BIN or install python3" | tee -a "${LOGFILE}" >&2
    exit 127
fi

if [[ ! -f "${SCANNER}" ]]; then
    echo "[$(date '+%H:%M:%S')] Scanner entrypoint not found: ${SCANNER}" | tee -a "${LOGFILE}" >&2
    exit 1
fi

"${PYTHON_BIN}" -u "${SCANNER}" "${DEFAULT_ARGS[@]}" "$@" 2>> "${LOGFILE}" | tee -a "${LOGFILE}" "${LATEST_TXT}"

exit_code=${PIPESTATUS[0]}
if [[ ${exit_code} -ne 0 ]]; then
    echo "[$(date '+%H:%M:%S')] Scanner exited with code ${exit_code}" >> "${LOGFILE}"
fi

exit ${exit_code}
