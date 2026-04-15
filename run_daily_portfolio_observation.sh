#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
PIPELINE="${SCRIPT_DIR}/paper_trade_pipeline.py"
STATUS_SUMMARY="${SCRIPT_DIR}/paper_trade_status_summary.py"
SETTLEMENT_SYNC="${SCRIPT_DIR}/paper_trade_settlement_sync.py"
FORWARD_CHECK="${SCRIPT_DIR}/paper_trade_forward_check.py"
LANE_MONITOR="${SCRIPT_DIR}/paper_trade_lane_monitor.py"
NEXT_STEPS="${SCRIPT_DIR}/paper_trade_next_steps.py"
PREFLIGHT_NOTE="${SCRIPT_DIR}/paper_trade_preflight_note.py"
OPS_HISTORY="${SCRIPT_DIR}/paper_trade_ops_history.py"
LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "${LOG_DIR}"

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "python3 not found; set PYTHON_BIN or install python3" >&2
  exit 127
fi

if [[ ! -f "${PIPELINE}" ]]; then
  echo "Pipeline entrypoint not found: ${PIPELINE}" >&2
  exit 1
fi

if [[ ! -f "${STATUS_SUMMARY}" ]]; then
  echo "Status summary helper not found: ${STATUS_SUMMARY}" >&2
  exit 1
fi

if [[ ! -f "${SETTLEMENT_SYNC}" ]]; then
  echo "Settlement sync helper not found: ${SETTLEMENT_SYNC}" >&2
  exit 1
fi

if [[ ! -f "${FORWARD_CHECK}" ]]; then
  echo "Forward check helper not found: ${FORWARD_CHECK}" >&2
  exit 1
fi

if [[ ! -f "${LANE_MONITOR}" ]]; then
  echo "Lane monitor helper not found: ${LANE_MONITOR}" >&2
  exit 1
fi

if [[ ! -f "${NEXT_STEPS}" ]]; then
  echo "Next-steps helper not found: ${NEXT_STEPS}" >&2
  exit 1
fi

if [[ ! -f "${PREFLIGHT_NOTE}" ]]; then
  echo "Preflight-note helper not found: ${PREFLIGHT_NOTE}" >&2
  exit 1
fi

if [[ ! -f "${OPS_HISTORY}" ]]; then
  echo "Ops-history helper not found: ${OPS_HISTORY}" >&2
  exit 1
fi

RUN_DATE="${RUN_DATE:-$(date +%Y-%m-%d)}"
RUN_ROOT="${SCRIPT_DIR}/out/daily_portfolio_runs/${RUN_DATE}"
mkdir -p "${RUN_ROOT}"
LOGFILE="${LOG_DIR}/daily_portfolio_observation_${RUN_DATE}.log"
PREFLIGHT_NOTE_TXT="${RUN_ROOT}/preflight_note.txt"
PREFLIGHT_NOTE_JSON="${RUN_ROOT}/preflight_note.json"

PRIMARY_RULES="${SCRIPT_DIR}/phase7_current_paper_rules.json"
SHADOW_RULES="${SCRIPT_DIR}/phase8_shadow_rules.json"

run_lane() {
  local lane="$1"
  local rules="$2"
  shift 2
  local lane_dir="${RUN_ROOT}/${lane}"
  local scan_input="${lane_dir}/live_scan.json"
  local scanner_status="${lane_dir}/live_scan.status.json"
  local reco_dir="${lane_dir}/recommendations"
  local pipeline_status="${lane_dir}/pipeline_status.json"
  local summary_txt="${lane_dir}/summary.txt"

  local signal_ledger="${SCRIPT_DIR}/paper_trades/${lane}_paper_trade_signals.csv"
  local signal_state="${SCRIPT_DIR}/paper_trades/.${lane}_logged_signals.json"
  local recommendation_ledger="${SCRIPT_DIR}/paper_trades/${lane}_paper_trade_recommendations.csv"
  local recommendation_state="${SCRIPT_DIR}/paper_trades/.${lane}_logged_recommendations.json"
  local settlement_ledger="${SCRIPT_DIR}/paper_trades/${lane}_paper_trade_settlements.csv"
  local forward_check_txt="${lane_dir}/forward_check.txt"
  local forward_check_md="${lane_dir}/forward_check.md"
  local lane_monitor_txt="${lane_dir}/lane_monitor.txt"
  local lane_monitor_md="${lane_dir}/lane_monitor.md"
  local next_steps_txt="${lane_dir}/next_steps.txt"
  local next_steps_md="${lane_dir}/next_steps.md"
  local rel_summary_txt="${summary_txt#${SCRIPT_DIR}/}"
  local rel_settlement_ledger="${settlement_ledger#${SCRIPT_DIR}/}"
  local rel_forward_check_md="${forward_check_md#${SCRIPT_DIR}/}"
  local rel_lane_monitor_md="${lane_monitor_md#${SCRIPT_DIR}/}"
  local rel_next_steps_md="${next_steps_md#${SCRIPT_DIR}/}"

  mkdir -p "${lane_dir}"

  echo "--- $(date '+%Y-%m-%d %H:%M:%S') ${lane} ---" | tee -a "${LOGFILE}"
  echo "Rules: ${rules}" | tee -a "${LOGFILE}"

  "${PYTHON_BIN}" -u "${PIPELINE}" \
    --rules "${rules}" \
    --scan-input "${scan_input}" \
    --recommendation-output-dir "${reco_dir}" \
    --ledger "${signal_ledger}" \
    --state "${signal_state}" \
    --recommendation-ledger "${recommendation_ledger}" \
    --recommendation-state "${recommendation_state}" \
    --status-output "${pipeline_status}" \
    "$@" 2>> "${LOGFILE}" | tee -a "${LOGFILE}"

  "${PYTHON_BIN}" "${STATUS_SUMMARY}" \
    --scanner-status "${scanner_status}" \
    --pipeline-status "${pipeline_status}" \
    --output "${summary_txt}" | tee -a "${LOGFILE}"

  "${PYTHON_BIN}" "${SETTLEMENT_SYNC}" \
    --signals-ledger "${signal_ledger}" \
    --settlement-ledger "${settlement_ledger}" | tee -a "${LOGFILE}"

  "${PYTHON_BIN}" "${FORWARD_CHECK}" \
    --signals-ledger "${signal_ledger}" \
    --recommendation-ledger "${recommendation_ledger}" \
    --settlement-ledger "${settlement_ledger}" \
    --rules "${rules}" \
    --format text \
    --output "${forward_check_txt}" | tee -a "${LOGFILE}"

  "${PYTHON_BIN}" "${FORWARD_CHECK}" \
    --signals-ledger "${signal_ledger}" \
    --recommendation-ledger "${recommendation_ledger}" \
    --settlement-ledger "${settlement_ledger}" \
    --rules "${rules}" \
    --format md \
    --output "${forward_check_md}" > /dev/null

  "${PYTHON_BIN}" "${LANE_MONITOR}" \
    --signals-ledger "${signal_ledger}" \
    --recommendation-ledger "${recommendation_ledger}" \
    --settlement-ledger "${settlement_ledger}" \
    --rules "${rules}" \
    --format text \
    --output "${lane_monitor_txt}" | tee -a "${LOGFILE}"

  "${PYTHON_BIN}" "${LANE_MONITOR}" \
    --signals-ledger "${signal_ledger}" \
    --recommendation-ledger "${recommendation_ledger}" \
    --settlement-ledger "${settlement_ledger}" \
    --rules "${rules}" \
    --format md \
    --output "${lane_monitor_md}" > /dev/null

  "${PYTHON_BIN}" "${NEXT_STEPS}" \
    --signals-ledger "${signal_ledger}" \
    --recommendation-ledger "${recommendation_ledger}" \
    --settlement-ledger "${settlement_ledger}" \
    --rules "${rules}" \
    --runner "${SCRIPT_DIR}/run_daily_portfolio_observation.sh" \
    --scanner-status "${scanner_status}" \
    --pipeline-status "${pipeline_status}" \
    --preflight-note "${PREFLIGHT_NOTE_TXT}" \
    --format text \
    --output "${next_steps_txt}" | tee -a "${LOGFILE}"

  "${PYTHON_BIN}" "${NEXT_STEPS}" \
    --signals-ledger "${signal_ledger}" \
    --recommendation-ledger "${recommendation_ledger}" \
    --settlement-ledger "${settlement_ledger}" \
    --rules "${rules}" \
    --runner "${SCRIPT_DIR}/run_daily_portfolio_observation.sh" \
    --scanner-status "${scanner_status}" \
    --pipeline-status "${pipeline_status}" \
    --preflight-note "${PREFLIGHT_NOTE_TXT}" \
    --format md \
    --output "${next_steps_md}" > /dev/null

  {
    echo
    echo "Quick files:"
    echo "- Summary: ${rel_summary_txt}"
    echo "- Next steps: ${rel_next_steps_md}"
    echo "- Lane monitor: ${rel_lane_monitor_md}"
    echo "- Forward check: ${rel_forward_check_md}"
    echo "- Settlement ledger: ${rel_settlement_ledger}"
    echo
    echo "Forward check:"
    cat "${forward_check_txt}"
    echo "Forward check detail: ${rel_forward_check_md}"
    echo
    echo "Lane monitor:"
    cat "${lane_monitor_txt}"
    echo "Lane monitor detail: ${rel_lane_monitor_md}"
    echo
    echo "Next steps:"
    cat "${next_steps_txt}"
    echo "Next steps detail: ${rel_next_steps_md}"
  } >> "${summary_txt}"
}

echo "--- $(date '+%Y-%m-%d %H:%M:%S') ---" >> "${LOGFILE}"
echo "[$(date '+%H:%M:%S')] Running daily portfolio observation cycle $*" >> "${LOGFILE}"

"${PYTHON_BIN}" "${PREFLIGHT_NOTE}" --format text --output "${PREFLIGHT_NOTE_TXT}" | tee -a "${LOGFILE}"
"${PYTHON_BIN}" "${PREFLIGHT_NOTE}" --format json --output "${PREFLIGHT_NOTE_JSON}" > /dev/null

run_lane phase7_current_paper "${PRIMARY_RULES}" "$@"
run_lane phase8_shadow "${SHADOW_RULES}" "$@"

PRIMARY_SUMMARY="${RUN_ROOT}/phase7_current_paper/summary.txt"
SHADOW_SUMMARY="${RUN_ROOT}/phase8_shadow/summary.txt"
COMBINED_SUMMARY="${RUN_ROOT}/daily_summary.txt"

{
  echo "Daily portfolio observation summary (${RUN_DATE})"
  echo
  echo "Quick jump index:"
  echo "- Rolling ops history: OPS_HISTORY.md"
  echo "- Preflight note: out/daily_portfolio_runs/${RUN_DATE}/preflight_note.txt"
  echo "- Primary next steps: out/daily_portfolio_runs/${RUN_DATE}/phase7_current_paper/next_steps.md"
  echo "- Primary lane monitor: out/daily_portfolio_runs/${RUN_DATE}/phase7_current_paper/lane_monitor.md"
  echo "- Primary forward check: out/daily_portfolio_runs/${RUN_DATE}/phase7_current_paper/forward_check.md"
  echo "- Shadow next steps: out/daily_portfolio_runs/${RUN_DATE}/phase8_shadow/next_steps.md"
  echo "- Shadow lane monitor: out/daily_portfolio_runs/${RUN_DATE}/phase8_shadow/lane_monitor.md"
  echo "- Shadow forward check: out/daily_portfolio_runs/${RUN_DATE}/phase8_shadow/forward_check.md"
  echo
  echo "Preflight note:"
  cat "${PREFLIGHT_NOTE_TXT}"
  echo
  echo "PRIMARY: Phase 7 current paper basket (active OP + CD)"
  cat "${PRIMARY_SUMMARY}"
  echo
  echo "SHADOW: Phase 8 watch-list basket"
  cat "${SHADOW_SUMMARY}"
  echo
  echo "Artifacts root: out/daily_portfolio_runs/${RUN_DATE}"
} > "${COMBINED_SUMMARY}"

"${PYTHON_BIN}" "${OPS_HISTORY}" >> "${LOGFILE}"

cat "${COMBINED_SUMMARY}"
