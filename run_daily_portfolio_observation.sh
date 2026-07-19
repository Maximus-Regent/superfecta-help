#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
PIPELINE="${SCRIPT_DIR}/paper_trade_pipeline.py"
STATUS_SUMMARY="${SCRIPT_DIR}/paper_trade_status_summary.py"
SETTLEMENT_SYNC="${SCRIPT_DIR}/paper_trade_settlement_sync.py"
SETTLEMENT_AUDIT="${SCRIPT_DIR}/paper_trade_settlement_audit.py"
FORWARD_CHECK="${SCRIPT_DIR}/paper_trade_forward_check.py"
LANE_MONITOR="${SCRIPT_DIR}/paper_trade_lane_monitor.py"
NEXT_STEPS="${SCRIPT_DIR}/paper_trade_next_steps.py"
PREFLIGHT_NOTE="${SCRIPT_DIR}/paper_trade_preflight_note.py"
OPS_HISTORY="${SCRIPT_DIR}/paper_trade_ops_history.py"
RIGHT_NOW="${SCRIPT_DIR}/paper_trade_now.py"
DAILY_SUMMARY_HELPER="${SCRIPT_DIR}/paper_trade_daily_summary.py"
LANE_SUMMARY_HELPER="${SCRIPT_DIR}/paper_trade_lane_summary.py"
CURRENT_EVIDENCE_SUMMARY="${SCRIPT_DIR}/current_evidence_summary.py"
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

if [[ ! -f "${SETTLEMENT_AUDIT}" ]]; then
  echo "Settlement audit helper not found: ${SETTLEMENT_AUDIT}" >&2
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

if [[ ! -f "${RIGHT_NOW}" ]]; then
  echo "Right-now helper not found: ${RIGHT_NOW}" >&2
  exit 1
fi

if [[ ! -f "${DAILY_SUMMARY_HELPER}" ]]; then
  echo "Daily-summary helper not found: ${DAILY_SUMMARY_HELPER}" >&2
  exit 1
fi

if [[ ! -f "${LANE_SUMMARY_HELPER}" ]]; then
  echo "Lane-summary helper not found: ${LANE_SUMMARY_HELPER}" >&2
  exit 1
fi

if [[ ! -f "${CURRENT_EVIDENCE_SUMMARY}" ]]; then
  echo "Current-evidence summary helper not found: ${CURRENT_EVIDENCE_SUMMARY}" >&2
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

rules_label() {
  case "$(basename "$1")" in
    op_anchor_rules.json)
      echo "OP anchor"
      ;;
    phase7_live_rules.json)
      echo "Phase 7 basket"
      ;;
    phase7_current_paper_rules.json)
      echo "Phase 7 current paper"
      ;;
    phase8_shadow_rules.json)
      echo "Phase 8 shadow"
      ;;
    *)
      basename "$1" .json | tr '_' ' '
      ;;
  esac
}

write_status_summary_placeholder() {
  local output_path="$1"
  local rules_path="$2"
  local scanner_status_path="$3"
  local pipeline_status_path="$4"
  local label
  label="$(rules_label "$rules_path")"

  mkdir -p "$(dirname "$output_path")"
  printf "%s run: status summary unavailable because lane status artifacts were missing or unreadable. Scanner sidecar: %s. Pipeline sidecar: %s.\n" \
    "$label" \
    "$(basename "$scanner_status_path")" \
    "$(basename "$pipeline_status_path")" > "$output_path"

  echo "WARN: status summary helper failed for ${label}; wrote placeholder summary to ${output_path}." | tee -a "${LOGFILE}"
}

write_markdown_placeholder() {
  local output_path="$1"
  local text_path="$2"
  local label="$3"

  mkdir -p "$(dirname "$output_path")"
  {
    printf '# %s\n\n' "$label"
    printf 'Markdown render failed during the daily wrapper run, so this placeholder mirror points to the text artifact instead.\n\n'
    if [[ "$label" == "paper-trade right now" && -n "${OPS_HISTORY_MD:-}" ]]; then
      printf 'Quick reads:\n'
      printf -- '- Text artifact: `%s`\n' "${text_path#${SCRIPT_DIR}/}"
      printf -- '- Rolling ops history: `%s`\n\n' "${OPS_HISTORY_MD#${SCRIPT_DIR}/}"
    else
      printf 'Text artifact: `%s`\n\n' "${text_path#${SCRIPT_DIR}/}"
    fi
    printf '```text\n'
    cat "$text_path"
    printf '\n```\n'
  } > "$output_path"
}

write_preflight_text_placeholder() {
  local output_path="$1"
  mkdir -p "$(dirname "$output_path")"
  printf 'Preflight context unavailable because preflight-note helper failed during the daily wrapper run.\n' > "$output_path"
  echo "WARN: preflight-note text helper failed; wrote placeholder note to ${output_path}." | tee -a "${LOGFILE}"
}

write_preflight_json_placeholder() {
  local output_path="$1"
  mkdir -p "$(dirname "$output_path")"
  cat > "$output_path" <<'EOF'
{
  "api_ok": false,
  "error": "preflight note helper failed during daily wrapper run",
  "note": "Preflight context unavailable because preflight-note helper failed during the daily wrapper run."
}
EOF
  echo "WARN: preflight-note json helper failed; wrote placeholder JSON to ${output_path}." | tee -a "${LOGFILE}"
}

write_ops_history_placeholder() {
  local md_output="$1"
  local csv_output="$2"
  local run_root="$3"

  mkdir -p "$(dirname "$md_output")"
  cat > "$md_output" <<EOF
# Paper-Trade Ops History

Latest refresh failed during the daily wrapper run, so this placeholder keeps the ops-history artifact path alive until the helper is rerun.

- Latest run root: ${run_root#${SCRIPT_DIR}/}
- Current refresh status: unavailable because the ops-history helper failed during the daily wrapper run.
- Next step: rerun ./run_daily_portfolio_observation.sh or python3 paper_trade_ops_history.py.
EOF

  mkdir -p "$(dirname "$csv_output")"
  cat > "$csv_output" <<EOF
date,day_bucket,calendar_state,primary_state,takeaway,run_root
$(basename "$run_root"),ISSUE,UNKNOWN,UNAVAILABLE,"Ops-history helper failed during daily wrapper run; rerun wrapper or paper_trade_ops_history.py.",${run_root#${SCRIPT_DIR}/}
EOF

  echo "WARN: ops-history helper failed; wrote placeholder artifacts to ${md_output} and ${csv_output}." | tee -a "${LOGFILE}"
}

write_settlement_audit_placeholder() {
  local md_output="$1"
  local json_output="$2"
  local run_root="$3"

  mkdir -p "$(dirname "$md_output")"
  cat > "$md_output" <<EOF
# Paper Trade Settlement Audit

Settlement-audit refresh failed during the daily wrapper run, so this placeholder keeps the audit artifact path alive until the helper is rerun.

- Latest run root: ${run_root#${SCRIPT_DIR}/}
- Current audit status: unavailable because paper_trade_settlement_audit.py failed during the daily wrapper run.
- Evidence boundary: this placeholder is not forward-performance evidence. Rerun ./run_daily_portfolio_observation.sh or python3 paper_trade_settlement_audit.py before interpreting settled ROI coverage.
EOF

  mkdir -p "$(dirname "$json_output")"
  cat > "$json_output" <<EOF
{
  "artifact_status": "placeholder",
  "summary": {
    "current_read": "settlement audit unavailable because paper_trade_settlement_audit.py failed during the daily wrapper run",
    "evidence_boundary": "This placeholder is not forward-performance evidence; rerun the settlement audit before interpreting settled ROI coverage."
  },
  "lanes": []
}
EOF

  echo "WARN: settlement audit helper failed; wrote placeholder artifacts to ${md_output} and ${json_output}." | tee -a "${LOGFILE}"
}

write_current_evidence_placeholder() {
  local md_output="$1"
  local json_output="$2"
  local run_root="$3"

  mkdir -p "$(dirname "$md_output")"
  cat > "$md_output" <<EOF
# Current Evidence Summary

Current-evidence bridge refresh failed during the daily wrapper run, so this placeholder keeps the report bridge path alive until the helper is rerun.

- Latest run root: ${run_root#${SCRIPT_DIR}/}
- Current bridge status: unavailable because current_evidence_summary.py failed during the daily wrapper run.
- Evidence boundary: this placeholder is not forward-performance evidence, live-profitability evidence, promotion-readiness evidence, bankroll guidance, or real-money evidence. Rerun ./run_daily_portfolio_observation.sh, or rerun python3 paper_trade_settlement_audit.py before python3 current_evidence_summary.py, before quoting current paper totals from this bridge.
EOF

  mkdir -p "$(dirname "$json_output")"
  cat > "$json_output" <<EOF
{
  "artifact_status": "placeholder",
  "summary": {
    "current_read": "current evidence summary unavailable because current_evidence_summary.py failed during the daily wrapper run",
    "evidence_boundary": "This placeholder is not forward-performance evidence, live-profitability evidence, promotion-readiness evidence, bankroll guidance, or real-money evidence; rerun the daily wrapper, or rerun paper_trade_settlement_audit.py before current_evidence_summary.py, before quoting current paper totals from this bridge.",
    "rebuild_order": "python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py"
  },
  "run_root": "${run_root#${SCRIPT_DIR}/}"
}
EOF

  echo "WARN: current-evidence summary helper failed; wrote placeholder artifacts to ${md_output} and ${json_output}." | tee -a "${LOGFILE}"
}

right_now_placeholder_gate_lines() {
  "${PYTHON_BIN}" - "${SCRIPT_DIR}/forward_evidence_scorecard.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

scorecard_path = Path(sys.argv[1])
loaded = False
fallback_used = True
anchor = 30
phase8 = 20
real_money = 100
try:
    payload = json.loads(scorecard_path.read_text(encoding="utf-8"))
    gates = payload.get("decision_gate_minimums", {}) if isinstance(payload, dict) else {}
    anchor = int(gates["anchor_displacement"]["min_roi_complete_settled_observations"])
    phase8 = int(gates["phase8_promotion_review"]["min_roi_complete_settled_observations"])
    real_money = int(gates["real_money_discussion"]["min_total_settled_observations_with_usable_roi"])
    loaded = True
    fallback_used = False
except Exception:
    pass

print(
    f"- Decision-gate source: forward_evidence_scorecard.json decision_gate_minimums "
    f"loaded={loaded} fallback_used={fallback_used} anchor_displacement={anchor} "
    f"phase8_promotion_review={phase8} real_money_discussion={real_money}"
)
print(
    f"- Active right-now gates: primary_min_settled={anchor}; shadow_min_settled={phase8}; portfolio_review_settled={real_money}. "
    "right-now placeholder gates are source-matched to forward_evidence_scorecard.json decision_gate_minimums when available; "
    "otherwise they use conservative fallback values and must not be treated as posture-changing evidence."
)
PY
}

write_right_now_text_placeholder() {
  local output_path="$1"
  local run_root="$2"
  local primary_next_steps="$3"
  local shadow_next_steps="$4"
  local daily_summary_path="$5"
  local primary_context=""
  local shadow_context=""
  local primary_why=""
  local shadow_why=""
  local gate_lines=""

  primary_context="$(extract_latest_run_context "$primary_next_steps")"
  shadow_context="$(extract_latest_run_context "$shadow_next_steps")"
  primary_why="$(extract_latest_run_why "$primary_next_steps")"
  shadow_why="$(extract_latest_run_why "$shadow_next_steps")"
  gate_lines="$(right_now_placeholder_gate_lines || true)"

  mkdir -p "$(dirname "$output_path")"
  {
    printf 'Paper-trade right now\n'
    printf -- '- Latest run: %s\n' "${run_root#${SCRIPT_DIR}/}"
    printf -- '- Best action: read the Phase 7 current paper next-step artifact directly\n'
    printf -- '- Timing: now\n'
    printf -- '- Command: open the primary next-step artifact listed below\n'
    printf -- '- Why: paper_trade_now.py failed during the daily wrapper run, so this placeholder points back to the core operator artifacts instead of pretending to rank them.\n'
    if [[ -n "$gate_lines" ]]; then
      printf '%s\n' "$gate_lines"
    fi
    if [[ -n "$primary_context" ]]; then
      printf '%s\n' "- Primary lane context: ${primary_context}"
    fi
    if [[ -n "$primary_why" ]]; then
      printf '%s\n' "- Primary lane why now: ${primary_why}"
    fi
    if [[ -n "$shadow_context" ]]; then
      printf '%s\n' "- Shadow lane context: ${shadow_context}"
    fi
    if [[ -n "$shadow_why" ]]; then
      printf '%s\n' "- Shadow lane why now: ${shadow_why}"
    fi
    printf -- '- Quick reads:\n'
    printf -- '  1. %s\n' "${primary_next_steps#${SCRIPT_DIR}/}"
    printf -- '  2. %s\n' "${shadow_next_steps#${SCRIPT_DIR}/}"
    printf -- '  3. %s\n' "${daily_summary_path#${SCRIPT_DIR}/}"
    printf -- '  4. OPS_HISTORY.md\n'
  } > "$output_path"

  echo "WARN: right-now text helper failed; wrote placeholder card to ${output_path}." | tee -a "${LOGFILE}"
}

write_right_now_json_placeholder() {
  local output_path="$1"
  local run_root="$2"
  local primary_next_steps="$3"
  local shadow_next_steps="$4"
  local daily_summary_path="$5"

  mkdir -p "$(dirname "$output_path")"
  "${PYTHON_BIN}" - \
    "$output_path" \
    "${SCRIPT_DIR}/forward_evidence_scorecard.json" \
    "${run_root#${SCRIPT_DIR}/}" \
    "${primary_next_steps#${SCRIPT_DIR}/}" \
    "${shadow_next_steps#${SCRIPT_DIR}/}" \
    "${daily_summary_path#${SCRIPT_DIR}/}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

output_path = Path(sys.argv[1])
scorecard_path = Path(sys.argv[2])
run_root, primary_next_steps, shadow_next_steps, daily_summary_path = sys.argv[3:7]

anchor = 30
phase8 = 20
real_money = 100
loaded = False
fallback_reason = "forward_evidence_scorecard.json missing or unreadable; using conservative right-now placeholder gate defaults"
try:
    scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
    gates = scorecard.get("decision_gate_minimums", {}) if isinstance(scorecard, dict) else {}
    anchor = int(gates["anchor_displacement"]["min_roi_complete_settled_observations"])
    phase8 = int(gates["phase8_promotion_review"]["min_roi_complete_settled_observations"])
    real_money = int(gates["real_money_discussion"]["min_total_settled_observations_with_usable_roi"])
    loaded = True
    fallback_reason = ""
except Exception:
    pass

fallback_used = not loaded
gate_minimums = {
    "source_path": "forward_evidence_scorecard.json",
    "source_loaded": loaded,
    "fallback_used": fallback_used,
    "fallback_reason": fallback_reason,
    "anchor_displacement_min_roi_complete_settled_observations": anchor,
    "phase8_promotion_review_min_roi_complete_settled_observations": phase8,
    "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money,
    "active_min_settled": anchor,
    "active_portfolio_review_settled": real_money,
    "cli_overrides": {},
    "alignment_read": "right-now placeholder gates are source-matched to forward_evidence_scorecard.json decision_gate_minimums when available",
}
active_gates = {
    "source_path": "forward_evidence_scorecard.json",
    "source_loaded": loaded,
    "fallback_used": fallback_used,
    "min_settled": anchor,
    "portfolio_review_settled": real_money,
    "primary_min_settled": anchor,
    "shadow_min_settled": phase8,
    "primary_portfolio_review_settled": real_money,
    "shadow_portfolio_review_settled": real_money,
    "first_read_gate_parity": anchor == phase8,
    "portfolio_review_gate_parity": True,
    "primary_shadow_gate_parity": anchor == phase8,
    "alignment_read": "right-now placeholder gates are source-matched to forward_evidence_scorecard.json decision_gate_minimums when available; fallback values are not posture-changing evidence",
}
payload = {
    "artifact_status": "placeholder",
    "run_root": run_root,
    "decision_gate_minimums": gate_minimums,
    "active_decision_gates": active_gates,
    "best_action": {
        "headline": "read the Phase 7 current paper next-step artifact directly",
        "timing": "now",
        "command": "open the primary next-step artifact listed below",
        "why": "paper_trade_now.py failed during the daily wrapper run, so this placeholder points back to the core operator artifacts instead of pretending to rank them.",
    },
    "quick_reads": [primary_next_steps, shadow_next_steps, daily_summary_path, "OPS_HISTORY.md"],
    "evidence_boundary": "right-now placeholder is operator routing only, not new forward evidence",
}
output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

  echo "WARN: right-now json helper failed; wrote placeholder payload to ${output_path}." | tee -a "${LOGFILE}"
}

write_forward_check_placeholder() {
  local output_path="$1"
  local label="$2"
  local summary_path="$3"
  local settlement_ledger="$4"

  mkdir -p "$(dirname "$output_path")"
  {
    printf '%s forward check\n' "$label"
    printf -- '- Forward assessment: unavailable because the forward-check helper failed during the daily wrapper run.\n'
    printf -- '- Why this placeholder exists: the forward-check helper crashed after the lane summary and settlement sync already existed, so this fallback preserves the operator surface without pretending the forward read succeeded.\n'
    printf -- '- Quick reads:\n'
    printf -- '  1. %s\n' "${summary_path#${SCRIPT_DIR}/}"
    printf -- '  2. %s\n' "${settlement_ledger#${SCRIPT_DIR}/}"
  } > "$output_path"

  echo "WARN: forward-check helper failed for ${label}; wrote placeholder forward check to ${output_path}." | tee -a "${LOGFILE}"
}

write_lane_monitor_placeholder() {
  local output_path="$1"
  local label="$2"
  local forward_check_path="$3"
  local settlement_ledger="$4"

  mkdir -p "$(dirname "$output_path")"
  {
    printf '%s lane monitor\n' "$label"
    printf -- '- Forward assessment: unavailable because the lane-monitor helper failed during the daily wrapper run.\n'
    printf -- '- Why this placeholder exists: the lane monitor crashed after the base lane artifacts were already available, so this fallback preserves the operator surface without pretending the monitor read succeeded.\n'
    printf -- '- Quick reads:\n'
    printf -- '  1. %s\n' "${forward_check_path#${SCRIPT_DIR}/}"
    printf -- '  2. %s\n' "${settlement_ledger#${SCRIPT_DIR}/}"
  } > "$output_path"

  echo "WARN: lane monitor helper failed for ${label}; wrote placeholder monitor to ${output_path}." | tee -a "${LOGFILE}"
}

write_next_steps_placeholder() {
  local output_path="$1"
  local label="$2"
  local runner_path="$3"
  local forward_check_path="$4"
  local lane_monitor_path="$5"
  local summary_path="$6"

  mkdir -p "$(dirname "$output_path")"
  {
    printf '%s next steps\n' "$label"
    printf -- '- State: REFRESH NEXT-STEPS ARTIFACTS\n'
    printf -- '- Forward assessment: unavailable because the next-steps helper failed during the daily wrapper run.\n'
    printf -- '- Settled races: unknown | open races: unknown | open settlement rows: unknown\n'
    printf -- '- Why: the next-steps helper crashed after the base lane artifacts already existed, so this placeholder points back to the wrapper rerun plus the current summary, forward check, and lane monitor instead of pretending the lane state was recomputed successfully.\n'
    printf -- '- Latest run context: unavailable because the next-steps helper failed during the daily wrapper run.\n'
    printf -- '- Recommended commands:\n'
    printf -- '  1. ./%s\n' "$(basename "$runner_path")"
    printf -- '  2. cat %s\n' "${summary_path#${SCRIPT_DIR}/}"
    printf -- '  3. cat %s\n' "${forward_check_path#${SCRIPT_DIR}/}"
    printf -- '  4. cat %s\n' "${lane_monitor_path#${SCRIPT_DIR}/}"
  } > "$output_path"

  echo "WARN: next-steps helper failed for ${label}; wrote placeholder next steps to ${output_path}." | tee -a "${LOGFILE}"
}

render_markdown_or_placeholder() {
  local label="$1"
  local text_path="$2"
  local output_path="$3"
  shift 3

  if "$@" > /dev/null; then
    return 0
  fi

  if [[ -s "$text_path" ]]; then
    write_markdown_placeholder "$output_path" "$text_path" "$label"
    echo "WARN: ${label} markdown render failed; wrote placeholder mirror to ${output_path} from ${text_path}." | tee -a "${LOGFILE}"
    return 0
  fi

  echo "ERROR: ${label} markdown render failed and no text artifact existed at ${text_path}." | tee -a "${LOGFILE}"
  return 1
}

read_text_or_placeholder() {
  local path="$1"
  local missing_label="$2"

  if [[ -f "$path" && -s "$path" ]]; then
    cat "$path"
  else
    printf '[%s: %s]\n' "$missing_label" "${path#${SCRIPT_DIR}/}"
  fi
}

extract_latest_run_context() {
  local path="$1"

  if [[ -f "$path" && -s "$path" ]]; then
    grep -m1 '^- Latest run context:' "$path" | sed 's/^- //' || true
  fi
}

extract_latest_run_why() {
  local path="$1"

  if [[ -f "$path" && -s "$path" ]]; then
    grep -m1 '^- Why:' "$path" | sed 's/^- Why: //' || true
  fi
}

write_daily_summary_placeholder() {
  local output_path="$1"
  local run_root="$2"
  local preflight_path="$3"
  local primary_summary="$4"
  local shadow_summary="$5"
  local primary_next_steps="$6"
  local shadow_next_steps="$7"
  local right_now_path="$8"
  local ops_history_path="$9"
  local settlement_audit_path="${10}"
  local primary_context=""
  local shadow_context=""
  local primary_why=""
  local shadow_why=""

  primary_context="$(extract_latest_run_context "$primary_next_steps")"
  shadow_context="$(extract_latest_run_context "$shadow_next_steps")"
  primary_why="$(extract_latest_run_why "$primary_next_steps")"
  shadow_why="$(extract_latest_run_why "$shadow_next_steps")"

  mkdir -p "$(dirname "$output_path")"
  {
    printf 'Daily portfolio observation summary (%s)\n\n' "$(basename "$run_root")"
    printf 'WARNING: combined daily summary helper failed, so this placeholder summary points to the core text artifacts instead.\n\n'
    printf 'Quick jump index:\n'
    printf -- '- Right now: %s\n' "${right_now_path#${SCRIPT_DIR}/}"
    printf -- '- Rolling ops history: %s\n' "${ops_history_path#${SCRIPT_DIR}/}"
    printf -- '- Settlement audit: %s\n' "${settlement_audit_path#${SCRIPT_DIR}/}"
    printf -- '- Preflight note: %s\n' "${preflight_path#${SCRIPT_DIR}/}"
    printf -- '- Primary summary: %s\n' "${primary_summary#${SCRIPT_DIR}/}"
    printf -- '- Shadow summary: %s\n\n' "${shadow_summary#${SCRIPT_DIR}/}"
    printf 'Preflight note:\n'
    read_text_or_placeholder "$preflight_path" "missing preflight note"
    printf '\nCurrent live hierarchy:\n'
    printf '%s\n' '- Primary lane: `OP_DURABLE_K7` remains the anchor; `CD_CORE_K8` remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion.'
    printf '%s\n' '- Shadow lane: `OP_REFINED_K7` remains the lead same-family challenger; the rest of Phase 8 stays research/watch only until it earns more forward evidence.'
    if [[ -n "$primary_context" ]]; then
      printf '%s\n' "- Primary lane context: ${primary_context}"
    fi
    if [[ -n "$primary_why" ]]; then
      printf '%s\n' "- Primary lane why now: ${primary_why}"
    fi
    if [[ -n "$shadow_context" ]]; then
      printf '%s\n' "- Shadow lane context: ${shadow_context}"
    fi
    if [[ -n "$shadow_why" ]]; then
      printf '%s\n' "- Shadow lane why now: ${shadow_why}"
    fi
    printf '\nPRIMARY: Phase 7 current paper basket (OP + CD rule components; target cards require preflight)\n'
    read_text_or_placeholder "$primary_summary" "missing primary summary"
    printf '\nSHADOW: Phase 8 watch-list basket\n'
    read_text_or_placeholder "$shadow_summary" "missing shadow summary"
    printf '\nArtifacts root: %s\n' "${run_root#${SCRIPT_DIR}/}"
  } > "$output_path"

  echo "WARN: combined daily summary helper failed; wrote placeholder summary to ${output_path}." | tee -a "${LOGFILE}"
}

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
    --scanner-status-output "${scanner_status}" \
    --recommendation-output-dir "${reco_dir}" \
    --ledger "${signal_ledger}" \
    --state "${signal_state}" \
    --recommendation-ledger "${recommendation_ledger}" \
    --recommendation-state "${recommendation_state}" \
    --status-output "${pipeline_status}" \
    "$@" 2>> "${LOGFILE}" | tee -a "${LOGFILE}"

  if ! "${PYTHON_BIN}" "${STATUS_SUMMARY}" \
    --scanner-status "${scanner_status}" \
    --pipeline-status "${pipeline_status}" \
    --require-pipeline-status \
    --output "${summary_txt}" | tee -a "${LOGFILE}"; then
    write_status_summary_placeholder "${summary_txt}" "${rules}" "${scanner_status}" "${pipeline_status}"
  fi

  "${PYTHON_BIN}" "${SETTLEMENT_SYNC}" \
    --signals-ledger "${signal_ledger}" \
    --settlement-ledger "${settlement_ledger}" | tee -a "${LOGFILE}"

  if ! "${PYTHON_BIN}" "${FORWARD_CHECK}" \
    --signals-ledger "${signal_ledger}" \
    --recommendation-ledger "${recommendation_ledger}" \
    --settlement-ledger "${settlement_ledger}" \
    --rules "${rules}" \
    --format text \
    --output "${forward_check_txt}" | tee -a "${LOGFILE}"; then
    write_forward_check_placeholder "${forward_check_txt}" "$(rules_label "${rules}")" "${summary_txt}" "${settlement_ledger}"
  fi

  render_markdown_or_placeholder "$(rules_label "${rules}") forward check" "${forward_check_txt}" "${forward_check_md}" \
    "${PYTHON_BIN}" "${FORWARD_CHECK}" \
    --signals-ledger "${signal_ledger}" \
    --recommendation-ledger "${recommendation_ledger}" \
    --settlement-ledger "${settlement_ledger}" \
    --rules "${rules}" \
    --format md \
    --output "${forward_check_md}"

  if ! "${PYTHON_BIN}" "${LANE_MONITOR}" \
    --signals-ledger "${signal_ledger}" \
    --recommendation-ledger "${recommendation_ledger}" \
    --settlement-ledger "${settlement_ledger}" \
    --rules "${rules}" \
    --format text \
    --output "${lane_monitor_txt}" | tee -a "${LOGFILE}"; then
    write_lane_monitor_placeholder "${lane_monitor_txt}" "$(rules_label "${rules}")" "${forward_check_txt}" "${settlement_ledger}"
  fi

  render_markdown_or_placeholder "$(rules_label "${rules}") lane monitor" "${lane_monitor_txt}" "${lane_monitor_md}" \
    "${PYTHON_BIN}" "${LANE_MONITOR}" \
    --signals-ledger "${signal_ledger}" \
    --recommendation-ledger "${recommendation_ledger}" \
    --settlement-ledger "${settlement_ledger}" \
    --rules "${rules}" \
    --format md \
    --output "${lane_monitor_md}"

  if ! "${PYTHON_BIN}" "${NEXT_STEPS}" \
    --signals-ledger "${signal_ledger}" \
    --recommendation-ledger "${recommendation_ledger}" \
    --settlement-ledger "${settlement_ledger}" \
    --rules "${rules}" \
    --runner "${SCRIPT_DIR}/run_daily_portfolio_observation.sh" \
    --scanner-status "${scanner_status}" \
    --pipeline-status "${pipeline_status}" \
    --preflight-note "${PREFLIGHT_NOTE_TXT}" \
    --format text \
    --output "${next_steps_txt}" | tee -a "${LOGFILE}"; then
    write_next_steps_placeholder "${next_steps_txt}" "$(rules_label "${rules}")" "${SCRIPT_DIR}/run_daily_portfolio_observation.sh" "${forward_check_txt}" "${lane_monitor_txt}" "${summary_txt}"
  fi

  render_markdown_or_placeholder "$(rules_label "${rules}") next steps" "${next_steps_txt}" "${next_steps_md}" \
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
    --output "${next_steps_md}"

  local lane_summary_tmp="${lane_dir}/summary.enriched.tmp"
  if "${PYTHON_BIN}" "${LANE_SUMMARY_HELPER}" \
    --base-summary "${summary_txt}" \
    --next-steps-text "${next_steps_txt}" \
    --next-steps-md "${next_steps_md}" \
    --lane-monitor-text "${lane_monitor_txt}" \
    --lane-monitor-md "${lane_monitor_md}" \
    --forward-check-text "${forward_check_txt}" \
    --forward-check-md "${forward_check_md}" \
    --settlement-ledger "${settlement_ledger}" \
    --display-summary "${summary_txt}" \
    --output "${lane_summary_tmp}" > /dev/null; then
    mv "${lane_summary_tmp}" "${summary_txt}"
  else
    rm -f "${lane_summary_tmp}"
    if [[ -s "${summary_txt}" ]]; then
      echo "WARN: lane summary helper failed for $(rules_label "${rules}"); kept base summary at ${summary_txt}." | tee -a "${LOGFILE}"
    else
      echo "ERROR: lane summary helper failed for $(rules_label "${rules}") and no base summary existed at ${summary_txt}." | tee -a "${LOGFILE}"
      return 1
    fi
  fi
}

echo "--- $(date '+%Y-%m-%d %H:%M:%S') ---" >> "${LOGFILE}"
echo "[$(date '+%H:%M:%S')] Running daily portfolio observation cycle $*" >> "${LOGFILE}"

if ! "${PYTHON_BIN}" "${PREFLIGHT_NOTE}" --format text --output "${PREFLIGHT_NOTE_TXT}" 2>> "${LOGFILE}" | tee -a "${LOGFILE}"; then
  write_preflight_text_placeholder "${PREFLIGHT_NOTE_TXT}"
fi

if ! "${PYTHON_BIN}" "${PREFLIGHT_NOTE}" --format json --output "${PREFLIGHT_NOTE_JSON}" > /dev/null 2>> "${LOGFILE}"; then
  write_preflight_json_placeholder "${PREFLIGHT_NOTE_JSON}"
fi

run_lane phase7_current_paper "${PRIMARY_RULES}" "$@"
run_lane phase8_shadow "${SHADOW_RULES}" "$@"

COMBINED_SUMMARY="${RUN_ROOT}/daily_summary.txt"
COMBINED_SUMMARY_TMP="${RUN_ROOT}/daily_summary.tmp"
SETTLEMENT_AUDIT_MD="${SCRIPT_DIR}/out/paper_trade_settlement_audit.md"
SETTLEMENT_AUDIT_JSON="${SCRIPT_DIR}/out/paper_trade_settlement_audit.json"
RIGHT_NOW_TXT="${SCRIPT_DIR}/PAPER_TRADE_NOW.txt"
RIGHT_NOW_MD="${SCRIPT_DIR}/PAPER_TRADE_NOW.md"
RIGHT_NOW_JSON="${SCRIPT_DIR}/PAPER_TRADE_NOW.json"
CURRENT_EVIDENCE_MD="${SCRIPT_DIR}/CURRENT_EVIDENCE_SUMMARY.md"
CURRENT_EVIDENCE_JSON="${SCRIPT_DIR}/current_evidence_summary.json"
OPS_HISTORY_MD="${SCRIPT_DIR}/OPS_HISTORY.md"
OPS_HISTORY_CSV="${SCRIPT_DIR}/ops_history.csv"
PRIMARY_SUMMARY_TXT="${RUN_ROOT}/phase7_current_paper/summary.txt"
SHADOW_SUMMARY_TXT="${RUN_ROOT}/phase8_shadow/summary.txt"
PRIMARY_NEXT_STEPS_TXT="${RUN_ROOT}/phase7_current_paper/next_steps.txt"
SHADOW_NEXT_STEPS_TXT="${RUN_ROOT}/phase8_shadow/next_steps.txt"

if ! "${PYTHON_BIN}" "${SETTLEMENT_AUDIT}" \
  --format text \
  --output-md "${SETTLEMENT_AUDIT_MD}" \
  --output-json "${SETTLEMENT_AUDIT_JSON}" | tee -a "${LOGFILE}"; then
  write_settlement_audit_placeholder "${SETTLEMENT_AUDIT_MD}" "${SETTLEMENT_AUDIT_JSON}" "${RUN_ROOT}"
fi

if ! "${PYTHON_BIN}" "${OPS_HISTORY}" >> "${LOGFILE}" 2>&1; then
  write_ops_history_placeholder "${OPS_HISTORY_MD}" "${OPS_HISTORY_CSV}" "${RUN_ROOT}"
fi

if ! "${PYTHON_BIN}" "${RIGHT_NOW}" \
  --run-root "${RUN_ROOT}" \
  --as-of-date "${RUN_DATE}" \
  --settlement-audit "${SETTLEMENT_AUDIT_MD}" \
  --format text \
  --output "${RIGHT_NOW_TXT}" | tee -a "${LOGFILE}"; then
  write_right_now_text_placeholder "${RIGHT_NOW_TXT}" "${RUN_ROOT}" "${PRIMARY_NEXT_STEPS_TXT}" "${SHADOW_NEXT_STEPS_TXT}" "${COMBINED_SUMMARY}"
fi

if ! "${PYTHON_BIN}" "${RIGHT_NOW}" \
  --run-root "${RUN_ROOT}" \
  --as-of-date "${RUN_DATE}" \
  --settlement-audit "${SETTLEMENT_AUDIT_MD}" \
  --format json \
  --output "${RIGHT_NOW_JSON}" >> "${LOGFILE}" 2>&1; then
  write_right_now_json_placeholder "${RIGHT_NOW_JSON}" "${RUN_ROOT}" "${PRIMARY_NEXT_STEPS_TXT}" "${SHADOW_NEXT_STEPS_TXT}" "${COMBINED_SUMMARY}"
fi

render_markdown_or_placeholder "paper-trade right now" "${RIGHT_NOW_TXT}" "${RIGHT_NOW_MD}" \
  "${PYTHON_BIN}" "${RIGHT_NOW}" \
  --run-root "${RUN_ROOT}" \
  --as-of-date "${RUN_DATE}" \
  --settlement-audit "${SETTLEMENT_AUDIT_MD}" \
  --format md \
  --output "${RIGHT_NOW_MD}"

if ! "${PYTHON_BIN}" "${CURRENT_EVIDENCE_SUMMARY}" \
  --right-now-json "${RIGHT_NOW_JSON}" \
  --settlement-audit-json "${SETTLEMENT_AUDIT_JSON}" \
  --md-output "${CURRENT_EVIDENCE_MD}" \
  --json-output "${CURRENT_EVIDENCE_JSON}" >> "${LOGFILE}" 2>&1; then
  write_current_evidence_placeholder "${CURRENT_EVIDENCE_MD}" "${CURRENT_EVIDENCE_JSON}" "${RUN_ROOT}"
fi

if "${PYTHON_BIN}" "${DAILY_SUMMARY_HELPER}" \
  --run-root "${RUN_ROOT}" \
  --output "${COMBINED_SUMMARY_TMP}" > /dev/null; then
  mv "${COMBINED_SUMMARY_TMP}" "${COMBINED_SUMMARY}"
else
  rm -f "${COMBINED_SUMMARY_TMP}"
  write_daily_summary_placeholder "${COMBINED_SUMMARY}" "${RUN_ROOT}" "${PREFLIGHT_NOTE_TXT}" "${PRIMARY_SUMMARY_TXT}" "${SHADOW_SUMMARY_TXT}" "${PRIMARY_NEXT_STEPS_TXT}" "${SHADOW_NEXT_STEPS_TXT}" "${RIGHT_NOW_MD}" "${OPS_HISTORY_MD}" "${SETTLEMENT_AUDIT_MD}"
fi

cat "${COMBINED_SUMMARY}"
