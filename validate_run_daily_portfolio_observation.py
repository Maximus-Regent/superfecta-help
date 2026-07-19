#!/usr/bin/env python3
"""
Fixture-driven validation for run_daily_portfolio_observation.sh.

Purpose:
- validate the real daily wrapper end to end instead of only its downstream helper surfaces
- keep the primary + shadow orchestration reproducible without touching live paper-trade ledgers
- cover representative no-target and active-target cache-miss, signals-without-bet, settle-first, limited-coverage, missing-status, unreadable-scanner-sidecar, unreadable-pipeline-sidecar, forward-check-helper-failure, next-steps-helper-failure, lane-monitor-helper-failure, right-now-helper-failure, and markdown-mirror fallback days in isolated fixture trees
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
WRAPPER = BASE / "run_daily_portfolio_observation.sh"
DEFAULT_FIXTURE_ROOT = BASE / "out" / "status_validation" / "daily_wrapper_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "run_daily_portfolio_observation"
OUT_MD = OUT_DIR / "run_daily_portfolio_observation_validation.md"
OUT_JSON = OUT_DIR / "run_daily_portfolio_observation_validation.json"
REBUILD_COMMAND = "python3 validate_run_daily_portfolio_observation.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
VALID_EVIDENCE_SCOPE = "daily_wrapper_orchestration_and_fallback_validation_only"
OPERATOR_READ_GATE_ISSUE_FLAGS = (
    "has_api_access_failure_context",
    "has_scanner_failure_boundary",
    "has_stale_cache_fallback_context",
)
EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "daily-wrapper validator",
    "source_scope": [
        "isolated daily-wrapper fixture project roots",
        "run_daily_portfolio_observation.sh",
        "wrapper-generated operator artifacts",
        "forward_evidence_scorecard.json decision_gate_minimums",
        "current_evidence_summary.json rebuild_validation_contract",
    ],
    "valid_use": "end-to-end wrapper orchestration and fallback/rebuild reproducibility validation",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_real_money_evidence": True,
    "daily_wrapper_validator_passes_are_orchestration_metadata_only": True,
    "non_goals": [
        "do not treat fixture wrapper passes as ROI-complete paper observations",
        "do not treat clean-empty, no-target, cache-miss, or helper-fallback days as rules-performance evidence",
        "do not treat right-now card freshness or current-evidence bridge regeneration as promotion readiness",
        "do not promote OP_REFINED_K7 or Phase 8 from wrapper fixture cleanliness",
        "do not substitute BAQ for BEL",
        "do not treat wrapper validation as real-money evidence",
    ],
}


def fixture_root() -> Path:
    override = os.environ.get("DAILY_WRAPPER_FIXTURE_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_FIXTURE_ROOT


def logical_fixture_root(root: Path) -> Path:
    return DEFAULT_FIXTURE_ROOT


def display_path(path: Path) -> str:
    return str(path.relative_to(BASE) if path.is_relative_to(BASE) else path)


def logical_fixture_path(path: Path, root: Path) -> str:
    if path.is_relative_to(root):
        return display_path(logical_fixture_root(root) / path.relative_to(root))
    return display_path(path)


def execution_mode(root: Path) -> str:
    return "default_fixture_root" if root == DEFAULT_FIXTURE_ROOT else "isolated_scratch_root"


def build_fixture_scratch_metadata(root: Path) -> dict[str, Any]:
    logical_root = logical_fixture_root(root)
    return {
        "fixture_root_relative": display_path(logical_root),
        "fixture_root_is_project_local": logical_root.is_relative_to(BASE),
        "case_roots_cleared_by_copy_fixture_project": True,
        "evidence_boundary": (
            "daily-wrapper fixture scratch metadata is orchestration/reproducibility context only, "
            "not a current-day scanner result, settled ROI, promotion readiness, live profitability, "
            "bankroll guidance, or real-money evidence"
        ),
    }


def expected_preflight_jump_path(run_root: Path, run_root_rel: Path) -> Path:
    text_path = run_root / "preflight_note.txt"
    json_path = run_root / "preflight_note.json"
    if text_path.exists():
        try:
            if text_path.read_text(encoding="utf-8").strip():
                return run_root_rel / "preflight_note.txt"
        except Exception:
            return run_root_rel / "preflight_note.txt"
    payload = read_json_optional(json_path)
    if payload and isinstance(payload.get("note"), str) and payload["note"].strip():
        return run_root_rel / "preflight_note.json"
    if text_path.exists():
        return run_root_rel / "preflight_note.txt"
    if json_path.exists():
        return run_root_rel / "preflight_note.json"
    return run_root_rel / "preflight_note.txt"


def strip_inline_markdown(value: str) -> str:
    return value.replace("**", "").replace("`", "").strip()


def extract_optional_bullet_value(text: str, label: str) -> str | None:
    match = re.search(rf"(?:^|\n)\s*-\s*{re.escape(label)}:\s*(.+)", text)
    if not match:
        return None
    value = strip_inline_markdown(match.group(1))
    return value or None


def normalize_stdout_line(line: str, root: Path) -> str:
    line = line.replace(str(root), display_path(logical_fixture_root(root)))
    line = line.replace(str(BASE) + "/", "")
    line = re.sub(r"^--- \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} (.+) ---$", r"--- <generated_ts> \1 ---", line)
    return line


def report_md_path(root: Path) -> Path:
    return OUT_MD


def report_json_path(root: Path) -> Path:
    return OUT_JSON


def require(condition: bool, label: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    return {"check": label, "status": "pass", "detail": detail}


def read_json_optional(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def validate_current_evidence_rebuild_contract(payload: dict[str, Any], case_name: str) -> dict[str, Any]:
    contract = payload.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise AssertionError(f"{case_name}: current evidence bridge did not publish rebuild_validation_contract")
    upstream_order = contract.get("upstream_refresh_order")
    if not isinstance(upstream_order, list) or len(upstream_order) != len(EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER):
        raise AssertionError(f"{case_name}: current evidence rebuild_validation_contract upstream_refresh_order shape drifted")
    commands: list[str] = []
    orders: list[int] = []
    for step in upstream_order:
        if not isinstance(step, dict):
            raise AssertionError(f"{case_name}: current evidence rebuild_validation_contract step was not an object")
        orders.append(step.get("order"))
        commands.append(step.get("command"))
    if orders != [1, 2, 3] or commands != EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER:
        raise AssertionError(f"{case_name}: current evidence rebuild_validation_contract upstream order drifted")
    if contract.get("prerequisite_rebuild_command") != EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER[0]:
        raise AssertionError(f"{case_name}: current evidence rebuild_validation_contract prerequisite command drifted")
    if contract.get("rebuild_command") != EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER[1]:
        raise AssertionError(f"{case_name}: current evidence rebuild_validation_contract rebuild command drifted")
    if contract.get("direct_validation_command") != EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER[2]:
        raise AssertionError(f"{case_name}: current evidence rebuild_validation_contract validator command drifted")
    for flag in (
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
        "requires_source_consistency_before_quoting_current_totals",
        "upstream_refresh_order_is_provenance_metadata_only",
        "not_settled_roi_or_real_money_evidence",
    ):
        if contract.get(flag) is not True:
            raise AssertionError(f"{case_name}: current evidence rebuild_validation_contract.{flag} must be true")
    return {
        "source_path": "rebuild_validation_contract",
        "upstream_refresh_order_commands": commands,
        "prerequisite_rebuild_command": contract.get("prerequisite_rebuild_command"),
        "rebuild_command": contract.get("rebuild_command"),
        "direct_validation_command": contract.get("direct_validation_command"),
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": contract.get(
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
        ),
        "requires_source_consistency_before_quoting_current_totals": contract.get(
            "requires_source_consistency_before_quoting_current_totals"
        ),
        "upstream_refresh_order_is_provenance_metadata_only": contract.get(
            "upstream_refresh_order_is_provenance_metadata_only"
        ),
        "not_settled_roi_or_real_money_evidence": contract.get("not_settled_roi_or_real_money_evidence"),
        "evidence_boundary": "current-evidence rebuild order is provenance metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
    }


def read_current_evidence_rebuild_contract(current_evidence_json: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    source_name = display_path(current_evidence_json)
    payload = json.loads(current_evidence_json.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{source_name} must be a JSON object")
    contract = validate_current_evidence_rebuild_contract(payload, source_name)
    return {
        "source": source_name,
        **contract,
    }


COPIED_FILES = [
    "run_daily_portfolio_observation.sh",
    "paper_trade_status_summary.py",
    "paper_trade_settlement_sync.py",
    "paper_trade_settlement_audit.py",
    "paper_trade_forward_check.py",
    "paper_trade_lane_monitor.py",
    "paper_trade_next_steps.py",
    "paper_trade_ops_history.py",
    "paper_trade_now.py",
    "paper_trade_daily_summary.py",
    "paper_trade_lane_summary.py",
    "current_evidence_summary.py",
    "paper_trade_settlement_helper.py",
    "phase7_current_paper_rules.json",
    "phase8_shadow_rules.json",
    "frozen_portfolio_eval_summary.csv",
    "forward_evidence_scorecard.json",
]

SIGNAL_FIELDS = [
    "signal_key",
    "scan_ts",
    "rule_id",
    "track",
    "card_name",
    "race_number",
    "race_id",
    "estimated_cost",
]

RECOMMENDATION_FIELDS = [
    "signal_key",
    "rule_id",
    "track",
    "race_number",
    "bet_decision",
    "estimated_cost",
]

PREFLIGHT_STUB = r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

CASES = {
    "case_no_target_cache_miss": {
        "note": "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 12 NYRA card(s). Shadow-only tracks present: KEE.",
        "api_ok": True,
        "has_targets": False,
        "relevant_tracks": [],
        "shadow_tracks": ["KEE"],
        "total_cards": 12,
    },
    "case_active_target_cache_miss": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_missing_scan_output_refresh": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_primary_settlement": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_active_signals_no_bet": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_shadow_settlement": {
        "note": "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today. Shadow-only tracks present: KEE.",
        "api_ok": True,
        "has_targets": False,
        "relevant_tracks": [],
        "shadow_tracks": ["KEE"],
        "total_cards": 12,
    },
    "case_partial_cache_refresh": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_missing_primary_status": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_unreadable_primary_scanner_status": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_unreadable_primary_pipeline_status": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_right_now_md_placeholder": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_lane_summary_fallback": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_daily_summary_fallback": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_unreadable_preflight_json": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_blank_text_prefers_json_preflight_note": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD. Saved JSON note should still drive the wrapper when preflight_note.txt is blank.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_blank_text_no_targets_prefers_json_preflight_note": {
        "note": "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today. Saved JSON stand-down note should still drive the wrapper when preflight_note.txt is blank.",
        "api_ok": True,
        "has_targets": False,
        "relevant_tracks": [],
        "shadow_tracks": ["KEE"],
        "total_cards": 12,
    },
    "case_preflight_helper_failure": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_ops_history_fallback": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_right_now_helper_failure": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_forward_check_helper_failure": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_lane_monitor_helper_failure": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_next_steps_helper_failure": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_pipeline_error_refresh": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
    "case_pipeline_logger_error_refresh": {
        "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "api_ok": True,
        "has_targets": True,
        "relevant_tracks": ["OP", "CD"],
        "shadow_tracks": [],
        "total_cards": 12,
    },
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fixture preflight note stub")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--output")
    return p.parse_args()


def write_output(path: str | None, content: str) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    case_name = os.environ.get("FIXTURE_CASE", "case_no_target_cache_miss")
    payload = CASES[case_name]
    if case_name == "case_preflight_helper_failure":
        print("fixture preflight helper failure", file=sys.stderr)
        return 1
    if args.format == "json":
        if case_name == "case_unreadable_preflight_json":
            output = "{bad json\n"
        else:
            output = json.dumps(payload, indent=2) + "\n"
    else:
        if case_name in {"case_blank_text_prefers_json_preflight_note", "case_blank_text_no_targets_prefers_json_preflight_note"}:
            output = "\n"
        else:
            output = payload["note"] + "\n"
    write_output(args.output, output)
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

PIPELINE_STUB = r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

SIGNAL_FIELDS = [
    "signal_key",
    "scan_ts",
    "rule_id",
    "track",
    "card_name",
    "race_number",
    "race_id",
    "estimated_cost",
]

RECOMMENDATION_FIELDS = [
    "signal_key",
    "rule_id",
    "track",
    "race_number",
    "bet_decision",
    "estimated_cost",
]

CASES = {
    "case_no_target_cache_miss": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-05-30T09:00:00",
                "result": "scanner_error",
                "error": "No cached data found for today's races",
                "cache_only": True,
                "card_count": 0,
                "race_count": 0,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "scanner_error",
                "observation_result": "scanner_failed_empty_run",
                "cache_only": True,
                "scanner_error": "No cached data found for today's races",
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-05-30T09:02:00",
                "result": "scanner_error",
                "error": "No cached data found for today's races",
                "cache_only": True,
                "card_count": 0,
                "race_count": 0,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "scanner_error",
                "observation_result": "scanner_failed_empty_run",
                "cache_only": True,
                "scanner_error": "No cached data found for today's races",
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_active_target_cache_miss": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-05-29T09:00:00",
                "result": "scanner_error",
                "error": "No cached data found for today's races",
                "cache_only": True,
                "card_count": 0,
                "race_count": 0,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "scanner_error",
                "observation_result": "scanner_failed_empty_run",
                "cache_only": True,
                "scanner_error": "No cached data found for today's races",
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-05-29T09:02:00",
                "result": "scanner_error",
                "error": "No cached data found for today's races",
                "cache_only": True,
                "card_count": 0,
                "race_count": 0,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "scanner_error",
                "observation_result": "scanner_failed_empty_run",
                "cache_only": True,
                "scanner_error": "No cached data found for today's races",
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_missing_scan_output_refresh": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-20T11:05:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "missing_scan_output",
                "scanner_status_reported_result": "no_qualifiers",
                "scanner_stage_status": "missing_scan_output",
                "observation_result": "scanner_failed_empty_run",
                "observation_scope": "operational_limit",
                "observation_reason": "missing_scan_output",
                "scan_input_empty_fallback_applied": True,
                "scan_input_empty_fallback_reason": "missing_or_empty_scan_output",
                "scan_input_state_before_empty_fallback": "missing",
                "scan_input_empty_fallback_value": "[]",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-20T11:07:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_primary_settlement": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-05-31T16:05:00",
                "result": "alerts_found",
                "cache_only": False,
                "card_count": 1,
                "race_count": 9,
                "emitted_hit_count": 1,
                "raw_hit_count": 1,
            },
            "pipeline": {
                "scanner_result": "alerts_found",
                "observation_result": "bets_ready",
                "cache_only": False,
                "scan_hit_count": 1,
                "scanner_raw_hit_count": 1,
                "recommendation_count": 1,
                "bet_count": 1,
                "error_count": 0,
            },
            "signals": [
                {
                    "signal_key": "2026-05-31_OP_7_OP_DURABLE_K7",
                    "scan_ts": "2026-05-31T16:05:00",
                    "rule_id": "OP_DURABLE_K7",
                    "track": "OP",
                    "card_name": "Oaklawn",
                    "race_number": "7",
                    "race_id": "OP-2026-05-31-7",
                    "estimated_cost": "24.0",
                }
            ],
            "recommendations": [
                {
                    "signal_key": "2026-05-31_OP_7_OP_DURABLE_K7",
                    "rule_id": "OP_DURABLE_K7",
                    "track": "OP",
                    "race_number": "7",
                    "bet_decision": "BET",
                    "estimated_cost": "24.0",
                }
            ],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-05-31T16:07:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 9,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_active_signals_no_bet": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-07T15:40:00",
                "result": "alerts_found",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 1,
                "raw_hit_count": 1,
            },
            "pipeline": {
                "scanner_result": "alerts_found",
                "observation_result": "signals_logged_no_bet",
                "cache_only": False,
                "scan_hit_count": 1,
                "scanner_raw_hit_count": 1,
                "recommendation_count": 1,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [
                {
                    "signal_key": "2026-06-07_OP_8_OP_DURABLE_K7",
                    "scan_ts": "2026-06-07T15:40:00",
                    "rule_id": "OP_DURABLE_K7",
                    "track": "OP",
                    "card_name": "Oaklawn",
                    "race_number": "8",
                    "race_id": "OP-2026-06-07-8",
                    "estimated_cost": "24.0",
                }
            ],
            "recommendations": [
                {
                    "signal_key": "2026-06-07_OP_8_OP_DURABLE_K7",
                    "rule_id": "OP_DURABLE_K7",
                    "track": "OP",
                    "race_number": "8",
                    "bet_decision": "NO BET",
                    "estimated_cost": "24.0",
                }
            ],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-07T15:42:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_shadow_settlement": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-05-31T16:05:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 0,
                "race_count": 0,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-05-31T16:07:00",
                "result": "alerts_found",
                "cache_only": False,
                "card_count": 1,
                "race_count": 9,
                "emitted_hit_count": 1,
                "raw_hit_count": 1,
            },
            "pipeline": {
                "scanner_result": "alerts_found",
                "observation_result": "bets_ready",
                "cache_only": False,
                "scan_hit_count": 1,
                "scanner_raw_hit_count": 1,
                "recommendation_count": 1,
                "bet_count": 1,
                "error_count": 0,
            },
            "signals": [
                {
                    "signal_key": "2026-05-31_KEE_9_KEE_K9",
                    "scan_ts": "2026-05-31T16:07:00",
                    "rule_id": "KEE_K9",
                    "track": "KEE",
                    "card_name": "Keeneland",
                    "race_number": "9",
                    "race_id": "KEE-2026-05-31-9",
                    "estimated_cost": "36.0",
                }
            ],
            "recommendations": [
                {
                    "signal_key": "2026-05-31_KEE_9_KEE_K9",
                    "rule_id": "KEE_K9",
                    "track": "KEE",
                    "race_number": "9",
                    "bet_decision": "BET",
                    "estimated_cost": "36.0",
                }
            ],
        },
    },
    "case_partial_cache_refresh": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-01T10:10:00",
                "result": "partial_cache_empty",
                "cache_only": True,
                "partial_cache": True,
                "card_count": 1,
                "race_count": 6,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
                "missing_race_detail_cache_skips": 2,
                "race_details_attempted": 4,
            },
            "pipeline": {
                "scanner_result": "partial_cache_empty",
                "observation_result": "partial_cache_empty_run",
                "cache_only": True,
                "scanner_partial_cache": True,
                "scanner_missing_race_detail_cache_skips": 2,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-01T10:12:00",
                "result": "no_qualifiers",
                "cache_only": True,
                "card_count": 1,
                "race_count": 6,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": True,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_missing_primary_status": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-02T09:45:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "write_scanner_status": False,
            "write_pipeline_status": False,
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-02T09:47:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_unreadable_primary_scanner_status": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-16T09:45:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "scanner_status_text": "{bad json\n",
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-16T09:47:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_unreadable_primary_pipeline_status": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-17T09:45:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "pipeline_status_text": "{bad json\n",
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-17T09:47:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_right_now_md_placeholder": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-03T16:05:00",
                "result": "alerts_found",
                "cache_only": False,
                "card_count": 1,
                "race_count": 9,
                "emitted_hit_count": 1,
                "raw_hit_count": 1,
            },
            "pipeline": {
                "scanner_result": "alerts_found",
                "observation_result": "bets_ready",
                "cache_only": False,
                "scan_hit_count": 1,
                "scanner_raw_hit_count": 1,
                "recommendation_count": 1,
                "bet_count": 1,
                "error_count": 0,
            },
            "signals": [
                {
                    "signal_key": "2026-06-03_OP_7_OP_DURABLE_K7",
                    "scan_ts": "2026-06-03T16:05:00",
                    "rule_id": "OP_DURABLE_K7",
                    "track": "OP",
                    "card_name": "Oaklawn",
                    "race_number": "7",
                    "race_id": "OP-2026-06-03-7",
                    "estimated_cost": "24.0",
                }
            ],
            "recommendations": [
                {
                    "signal_key": "2026-06-03_OP_7_OP_DURABLE_K7",
                    "rule_id": "OP_DURABLE_K7",
                    "track": "OP",
                    "race_number": "7",
                    "bet_decision": "BET",
                    "estimated_cost": "24.0",
                }
            ],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-03T16:07:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 9,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_lane_summary_fallback": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-04T16:05:00",
                "result": "alerts_found",
                "cache_only": False,
                "card_count": 1,
                "race_count": 9,
                "emitted_hit_count": 1,
                "raw_hit_count": 1,
            },
            "pipeline": {
                "scanner_result": "alerts_found",
                "observation_result": "bets_ready",
                "cache_only": False,
                "scan_hit_count": 1,
                "scanner_raw_hit_count": 1,
                "recommendation_count": 1,
                "bet_count": 1,
                "error_count": 0,
            },
            "signals": [
                {
                    "signal_key": "2026-06-04_OP_7_OP_DURABLE_K7",
                    "scan_ts": "2026-06-04T16:05:00",
                    "rule_id": "OP_DURABLE_K7",
                    "track": "OP",
                    "card_name": "Oaklawn",
                    "race_number": "7",
                    "race_id": "OP-2026-06-04-7",
                    "estimated_cost": "24.0",
                }
            ],
            "recommendations": [
                {
                    "signal_key": "2026-06-04_OP_7_OP_DURABLE_K7",
                    "rule_id": "OP_DURABLE_K7",
                    "track": "OP",
                    "race_number": "7",
                    "bet_decision": "BET",
                    "estimated_cost": "24.0",
                }
            ],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-04T16:07:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 9,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_daily_summary_fallback": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-05T16:05:00",
                "result": "alerts_found",
                "cache_only": False,
                "card_count": 1,
                "race_count": 9,
                "emitted_hit_count": 1,
                "raw_hit_count": 1,
            },
            "pipeline": {
                "scanner_result": "alerts_found",
                "observation_result": "bets_ready",
                "cache_only": False,
                "scan_hit_count": 1,
                "scanner_raw_hit_count": 1,
                "recommendation_count": 1,
                "bet_count": 1,
                "error_count": 0,
            },
            "signals": [
                {
                    "signal_key": "2026-06-05_OP_7_OP_DURABLE_K7",
                    "scan_ts": "2026-06-05T16:05:00",
                    "rule_id": "OP_DURABLE_K7",
                    "track": "OP",
                    "card_name": "Oaklawn",
                    "race_number": "7",
                    "race_id": "OP-2026-06-05-7",
                    "estimated_cost": "24.0",
                }
            ],
            "recommendations": [
                {
                    "signal_key": "2026-06-05_OP_7_OP_DURABLE_K7",
                    "rule_id": "OP_DURABLE_K7",
                    "track": "OP",
                    "race_number": "7",
                    "bet_decision": "BET",
                    "estimated_cost": "24.0",
                }
            ],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-05T16:07:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 9,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_unreadable_preflight_json": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-06T11:05:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-06T11:07:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_blank_text_prefers_json_preflight_note": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-18T11:05:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-18T11:07:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_blank_text_no_targets_prefers_json_preflight_note": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-19T09:00:00",
                "result": "scanner_error",
                "error": "No cached data found for today's races",
                "cache_only": True,
            },
            "pipeline": {
                "scanner_result": "scanner_error",
                "observation_result": "cache_miss",
                "cache_only": True,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 1,
                "scanner_error": "No cached data found for today's races",
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-19T09:00:00",
                "result": "scanner_error",
                "error": "No cached data found for today's races",
                "cache_only": True,
            },
            "pipeline": {
                "scanner_result": "scanner_error",
                "observation_result": "cache_miss",
                "cache_only": True,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 1,
                "scanner_error": "No cached data found for today's races",
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_preflight_helper_failure": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-08T11:05:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-08T11:07:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_ops_history_fallback": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-09T11:05:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-09T11:07:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_right_now_helper_failure": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-10T11:05:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-10T11:07:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_forward_check_helper_failure": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-11T11:05:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-11T11:07:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_lane_monitor_helper_failure": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-12T11:05:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-12T11:07:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_next_steps_helper_failure": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-12T11:05:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-12T11:07:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_pipeline_error_refresh": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-14T11:05:00",
                "result": "alerts_found",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 1,
                "raw_hit_count": 1,
            },
            "pipeline": {
                "result": "pipeline_error",
                "stage": "recommender",
                "error_type": "RuntimeError",
                "error": "fixture recommender crash",
                "scanner_result": "alerts_found",
                "observation_result": "signals_logged_no_bet",
                "cache_only": False,
                "scan_hit_count": 1,
                "scanner_raw_hit_count": 1,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-14T11:07:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 8,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
    "case_pipeline_logger_error_refresh": {
        "phase7_current_paper_rules.json": {
            "scanner": {
                "run_ts": "2026-06-15T11:05:00",
                "result": "alerts_found",
                "cache_only": False,
                "card_count": 1,
                "race_count": 9,
                "emitted_hit_count": 1,
                "raw_hit_count": 1,
            },
            "pipeline": {
                "result": "pipeline_error",
                "stage": "logger",
                "error_type": "ValueError",
                "error": "fixture logger crash",
                "scanner_result": "alerts_found",
                "observation_result": "signals_logged_no_bet",
                "cache_only": False,
                "scan_hit_count": 1,
                "scanner_raw_hit_count": 1,
                "recommendation_count": 1,
                "bet_count": 1,
                "error_count": 1,
            },
            "signals": [],
            "recommendations": [],
        },
        "phase8_shadow_rules.json": {
            "scanner": {
                "run_ts": "2026-06-15T11:07:00",
                "result": "no_qualifiers",
                "cache_only": False,
                "card_count": 1,
                "race_count": 9,
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
            },
            "pipeline": {
                "scanner_result": "no_qualifiers",
                "observation_result": "clean_empty_run",
                "cache_only": False,
                "scan_hit_count": 0,
                "scanner_raw_hit_count": 0,
                "recommendation_count": 0,
                "bet_count": 0,
                "error_count": 0,
            },
            "signals": [],
            "recommendations": [],
        },
    },
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fixture pipeline stub")
    p.add_argument("--rules", required=True)
    p.add_argument("--scan-input", required=True)
    p.add_argument("--recommendation-output-dir", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--state")
    p.add_argument("--recommendation-ledger", required=True)
    p.add_argument("--recommendation-state")
    p.add_argument("--status-output", required=True)
    p.add_argument("--scanner-status-output")
    return p.parse_known_args()[0]


def write_json(path: str, payload: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_csv(path: str, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def main() -> int:
    args = parse_args()
    case_name = os.environ["FIXTURE_CASE"]
    rules_name = Path(args.rules).name
    spec = CASES[case_name][rules_name]

    scan_input = Path(args.scan_input)
    scan_input.parent.mkdir(parents=True, exist_ok=True)
    scan_input.write_text(json.dumps({"fixture_case": case_name, "rules": rules_name}, indent=2) + "\n", encoding="utf-8")
    Path(args.recommendation_output_dir).mkdir(parents=True, exist_ok=True)

    scanner_status = dict(spec["scanner"])
    scanner_status["rules_path"] = args.rules
    scanner_status_path = Path(args.scanner_status_output) if args.scanner_status_output else scan_input.with_name("live_scan.status.json")
    if spec.get("write_scanner_status", True):
        if "scanner_status_text" in spec:
            scanner_status_path.write_text(str(spec["scanner_status_text"]), encoding="utf-8")
        else:
            write_json(str(scanner_status_path), scanner_status)

    pipeline_status = dict(spec["pipeline"])
    pipeline_status["run_ts"] = scanner_status.get("run_ts")
    pipeline_status["rules_path"] = args.rules
    pipeline_status["scanner_status_path"] = str(scanner_status_path)
    if spec.get("write_pipeline_status", True):
        if "pipeline_status_text" in spec:
            Path(args.status_output).write_text(str(spec["pipeline_status_text"]), encoding="utf-8")
        else:
            write_json(args.status_output, pipeline_status)

    write_csv(args.ledger, SIGNAL_FIELDS, spec["signals"])
    write_csv(args.recommendation_ledger, RECOMMENDATION_FIELDS, spec["recommendations"])

    print(f"fixture pipeline: {case_name} {rules_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

RIGHT_NOW_MD_FAIL_STUB = r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent

TEXT = """# PAPER TRADE NOW

## Primary action
- Settle the primary lane first
- Fixture note: markdown mirror intentionally failed after the text card was written.
- Fallback note: read the Phase 7 current paper next-step artifact directly if the markdown mirror is unavailable.

## Decision-gate source
- Decision-gate source: forward_evidence_scorecard.json decision_gate_minimums loaded=True anchor_displacement=30 phase8_promotion_review=20 real_money_discussion=100
- Active right-now gates: primary_min_settled=30; shadow_min_settled=20; portfolio_review_settled=100. right-now action gates are source-matched to forward_evidence_scorecard.json decision_gate_minimums.
"""


def rel(path: str | None) -> str:
    if not path:
        return ""
    try:
        return str(Path(path).resolve().relative_to(BASE.resolve()))
    except Exception:
        return str(path)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fixture right-now stub")
    p.add_argument("--run-root")
    p.add_argument("--as-of-date")
    p.add_argument("--settlement-audit")
    p.add_argument("--format", choices=["text", "md", "json"], default="text")
    p.add_argument("--output")
    return p.parse_args()


def build_json_payload(args: argparse.Namespace) -> dict[str, object]:
    return {
        "run_root": rel(args.run_root),
        "run_date": Path(args.run_root or "").name,
        "run_freshness": {"as_of_date": args.as_of_date, "is_stale": False, "summary": f"Fixture as-of date `{args.as_of_date}`."},
        "settlement_audit": rel(args.settlement_audit),
        "decision_gate_minimums": {
            "source_path": "forward_evidence_scorecard.json",
            "source_loaded": True,
            "fallback_used": False,
            "fallback_reason": "",
            "anchor_displacement_min_roi_complete_settled_observations": 30,
            "phase8_promotion_review_min_roi_complete_settled_observations": 20,
            "real_money_discussion_min_total_settled_observations_with_usable_roi": 100,
            "active_min_settled": 30,
            "active_portfolio_review_settled": 100,
            "cli_overrides": {},
            "alignment_read": "forward-check sample milestones are source-matched to forward_evidence_scorecard.json decision_gate_minimums",
        },
        "active_decision_gates": {
            "source_path": "forward_evidence_scorecard.json",
            "source_loaded": True,
            "fallback_used": False,
            "min_settled": 30,
            "portfolio_review_settled": 100,
            "primary_min_settled": 30,
            "shadow_min_settled": 20,
            "primary_portfolio_review_settled": 100,
            "shadow_portfolio_review_settled": 100,
            "first_read_gate_parity": False,
            "portfolio_review_gate_parity": True,
            "primary_shadow_gate_parity": False,
            "alignment_read": "right-now action gates are source-matched to forward_evidence_scorecard.json decision_gate_minimums",
        },
        "shadow_settlement_audit_promotion_gate": "fixture shadow per-rule gate survived the markdown fallback",
        "shadow_settlement_audit_rule_progress": "OP_REFINED_K7 0/20 (0.0%)",
        "best_action": {
            "headline": "Settle the primary lane first",
            "lane_key": "primary",
            "lane": "Phase 7 current paper lane",
            "command": "python3 paper_trade_settlement_helper.py",
            "why": "Fixture JSON was still written even though the markdown mirror failed.",
            "timing": "now",
        },
        "operator_read_gate": {
            "valid_use": "operator instruction/evidence-read gating only",
            "gate_status": "operator_action_routing_only",
            "requires_refresh_before_evidence_read": False,
            "requires_settlement_or_roi_repair_before_forward_read": False,
            "has_api_access_failure_context": False,
            "has_scanner_failure_boundary": False,
            "has_stale_cache_fallback_context": False,
            "recommended_command": "python3 paper_trade_settlement_helper.py",
            "reasons": ["fixture markdown fallback still wrote JSON"],
            "read": "Use this as a single-action operator routing card only.",
            "current_top_card_counts_as_no_target_evidence": False,
            "current_top_card_counts_as_clean_empty_evidence": False,
            "current_top_card_counts_as_bet_readiness_evidence": False,
            "current_top_card_counts_as_settled_roi_evidence": False,
            "not_forward_performance_evidence": True,
            "not_promotion_readiness_evidence": True,
            "not_live_profitability_evidence": True,
            "not_bankroll_guidance": True,
            "not_real_money_evidence": True,
        },
        "evidence_boundary": "fixture right-now JSON is operator routing only, not new forward evidence",
    }


def main() -> int:
    args = parse_args()
    if args.format == "md":
        print("fixture right-now md failure", file=sys.stderr)
        return 1
    output = json.dumps(build_json_payload(args), indent=2) + "\n" if args.format == "json" else TEXT
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

RIGHT_NOW_HELPER_FAIL_STUB = r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fixture right-now helper failure stub")
    p.add_argument("--run-root")
    p.add_argument("--format", choices=["text", "md", "json"], default="text")
    p.add_argument("--output")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    print(f"fixture right-now helper failure ({args.format})", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

LANE_SUMMARY_FAIL_STUB = r'''#!/usr/bin/env python3
from __future__ import annotations

import sys

print("fixture lane summary failure", file=sys.stderr)
raise SystemExit(1)
'''

DAILY_SUMMARY_FAIL_STUB = r'''#!/usr/bin/env python3
from __future__ import annotations

import sys

print("fixture daily summary failure", file=sys.stderr)
raise SystemExit(1)
'''

OPS_HISTORY_FAIL_STUB = r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from typing import Any, Callable


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fixture ops history failure stub")
    p.add_argument("--runs-root")
    p.add_argument("--limit", type=int, default=14)
    p.add_argument("--md-output")
    p.add_argument("--csv-output")
    return p.parse_args()


def collect_rows(runs_root, limit: int) -> list[dict[str, Any]]:
    return []


def current_streak(rows: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]) -> int:
    return 0


def main() -> int:
    parse_args()
    print("fixture ops history failure", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

CASES: list[dict[str, Any]] = [
    {
        "name": "case_no_target_cache_miss",
        "run_date": "2026-05-30",
        "wrapper_args": ["--cache-only", "--max-races", "1"],
        "scenario": "no-target cache-only miss stays a stand-down day while the wrapper still refreshes the full artifact stack",
        "assertions": [
            ("primary_summary", "cache miss (cache-only)"),
            ("primary_next_steps", "Latest run context: the latest cache-only check could not start because today's cache files were missing."),
            ("right_now_md", "Stand down, no OP / CD target action tonight"),
            ("ops_history_md", "| `2026-05-30` | NO TARGETS |"),
            ("daily_summary", "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today"),
        ],
    },
    {
        "name": "case_active_target_cache_miss",
        "run_date": "2026-05-29",
        "wrapper_args": ["--cache-only", "--max-races", "1"],
        "scenario": "active-target cache-only miss stays distinct from clean-empty days and promotes a rerun-live action through the full wrapper path",
        "assertions": [
            ("primary_summary", "cache miss (cache-only)"),
            ("primary_next_steps", "State: RERUN LIVE CHECK"),
            ("right_now_md", "Rerun the primary lane live, without --cache-only"),
            ("ops_history_md", "| `2026-05-29` | OP/CD ACTIVE | CACHE MISS (CACHE-ONLY)"),
            ("daily_summary", "Preflight context: primary paper-basket target tracks racing today: OP, CD."),
        ],
    },
    {
        "name": "case_missing_scan_output_refresh",
        "run_date": "2026-06-20",
        "wrapper_args": [],
        "scenario": "active-target readable scanner-status sidecar plus missing scan-output artifact stays an explicit refresh-artifacts condition through the full wrapper path",
        "assertions": [
            ("primary_summary", "missing scanner output, 0 scanner hit(s), 0 recommendation(s)"),
            ("primary_summary", "scanner-status reported no_qualifiers"),
            ("primary_summary", "safe empty scan fallback missing_or_empty_scan_output"),
            ("primary_summary", "scan input was missing before fallback"),
            ("primary_next_steps", "State: REFRESH RUN ARTIFACTS"),
            ("primary_next_steps", "scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers"),
            ("primary_next_steps", "not a clean no-qualifier observation"),
            ("right_now_md", "Refresh the daily wrapper, primary lane scan-output artifact is missing"),
            ("right_now_md", "Primary lane context: Latest run context: scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers"),
            ("ops_history_md", "| `2026-06-20` | OP/CD ACTIVE | MISSING SCAN OUTPUT"),
            ("ops_history_md", "pipeline used a safe empty [] fallback"),
            ("daily_summary", "missing scanner output, 0 scanner hit(s), 0 recommendation(s), scanner-status reported no_qualifiers, safe empty scan fallback missing_or_empty_scan_output"),
            ("daily_summary", "- Current operator focus: Refresh the daily wrapper, primary lane scan-output artifact is missing"),
            ("daily_summary", "- Current ops bucket: ISSUE"),
            ("daily_summary", "not a clean no-qualifier observation"),
        ],
    },
    {
        "name": "case_primary_settlement",
        "run_date": "2026-05-31",
        "wrapper_args": [],
        "scenario": "active primary BET day lands in settle-first mode once the wrapper syncs the open settlement row",
        "assertions": [
            ("primary_summary", "Quick files:"),
            ("primary_next_steps", "State: NEEDS SETTLEMENT"),
            ("settlement_ledger", "2026-05-31_OP_7_OP_DURABLE_K7"),
            ("right_now_md", "Settle the primary lane first"),
            ("ops_history_md", "| `2026-05-31` | OP/CD ACTIVE | BETS READY (1 bet)"),
            ("daily_summary", "primary paper-basket target tracks racing today: OP, CD."),
        ],
    },
    {
        "name": "case_active_signals_no_bet",
        "run_date": "2026-06-07",
        "wrapper_args": [],
        "scenario": "active-target hit-found day with a NO BET recommendation still syncs an observation settlement row while staying distinct from both clean-empty and bet-ready behavior end to end",
        "assertions": [
            ("primary_summary", "signals logged, no bet"),
            ("primary_next_steps", "State: NEEDS SETTLEMENT"),
            ("primary_next_steps", "logged signals but produced no BET recommendations"),
            ("settlement_ledger", "2026-06-07_OP_8_OP_DURABLE_K7"),
            ("right_now_md", "Settle the primary lane first"),
            ("right_now_md", "Latest ops bucket: **ACTIVE, HITS FOUND**"),
            ("ops_history_md", "| `2026-06-07` | OP/CD ACTIVE | SIGNALS, NO BET"),
            ("daily_summary", "signals logged, no bet"),
        ],
    },
    {
        "name": "case_shadow_settlement",
        "run_date": "2026-05-31",
        "wrapper_args": [],
        "scenario": "shadow-only BET day still lands in shadow settle-first mode end to end once the wrapper syncs the open shadow settlement row",
        "assertions": [
            ("shadow_summary", "Quick files:"),
            ("shadow_next_steps", "State: NEEDS SETTLEMENT"),
            ("shadow_settlement_ledger", "2026-05-31_KEE_9_KEE_K9"),
            ("right_now_md", "Settle the shadow lane queue"),
            ("right_now_md", "phase8_shadow/summary.txt"),
            ("ops_history_md", "| `2026-05-31` | NO TARGETS |"),
            ("daily_summary", "Shadow summary:"),
        ],
    },
    {
        "name": "case_partial_cache_refresh",
        "run_date": "2026-06-01",
        "wrapper_args": ["--cache-only", "--max-races", "1"],
        "scenario": "active-target partial-cache empty day stays limited-coverage and promotes a live refresh through the full wrapper path",
        "assertions": [
            ("primary_summary", "partial cache"),
            ("primary_next_steps", "State: LIMITED CACHE COVERAGE"),
            ("right_now_md", "Refresh the primary lane live after the partial-cache read"),
            ("ops_history_md", "| `2026-06-01` | OP/CD ACTIVE | PARTIAL CACHE EMPTY"),
            ("daily_summary", "Preflight context: primary paper-basket target tracks racing today: OP."),
        ],
    },
    {
        "name": "case_missing_primary_status",
        "run_date": "2026-06-02",
        "wrapper_args": [],
        "scenario": "missing primary status sidecars no longer kill the wrapper, they write a placeholder summary and promote refresh-artifacts messaging",
        "assertions": [
            ("primary_summary", "status summary unavailable because lane status artifacts were missing or unreadable"),
            ("primary_next_steps", "State: REFRESH RUN ARTIFACTS"),
            ("right_now_md", "Refresh the daily wrapper, primary lane pipeline status is missing"),
            ("ops_history_md", "| `2026-06-02` | OP/CD ACTIVE | MISSING"),
            ("daily_summary", "Preflight context: primary paper-basket target tracks racing today: OP, CD."),
            ("logfile", "WARN: status summary helper failed for Phase 7 current paper; wrote placeholder summary"),
        ],
    },
    {
        "name": "case_unreadable_primary_scanner_status",
        "run_date": "2026-06-16",
        "wrapper_args": [],
        "scenario": "an unreadable primary scanner sidecar now stays explicit through the saved wrapper artifacts instead of drifting into a benign zero-hit day",
        "assertions": [
            ("primary_summary", "scanner sidecar unreadable, 0 scanner hit(s), 0 recommendation(s)"),
            ("primary_next_steps", "The latest scanner status sidecar is unreadable."),
            ("primary_next_steps", "State: REFRESH RUN ARTIFACTS"),
            ("right_now_md", "Refresh the daily wrapper, primary lane scanner sidecar is unreadable"),
            ("right_now_md", "Latest ops bucket: **ISSUE**"),
            ("ops_history_md", "| `2026-06-16` | OP/CD ACTIVE | UNREADABLE"),
            ("ops_history_md", "Primary lane status artifacts were missing or unreadable. Refresh the daily wrapper before drawing conclusions."),
            ("daily_summary", "Preflight context: primary paper-basket target tracks racing today: OP."),
        ],
    },
    {
        "name": "case_unreadable_primary_pipeline_status",
        "run_date": "2026-06-17",
        "wrapper_args": [],
        "scenario": "a readable primary scanner plus malformed pipeline sidecar now stays explicit through the saved wrapper artifacts instead of drifting into a scanner-only summary",
        "assertions": [
            ("primary_summary", "pipeline sidecar unreadable, 0 scanner hit(s)"),
            ("primary_next_steps", "The latest lane pipeline status artifact is unreadable."),
            ("primary_next_steps", "State: REFRESH RUN ARTIFACTS"),
            ("right_now_md", "Refresh the daily wrapper, primary lane pipeline status is unreadable"),
            ("right_now_md", "Latest ops bucket: **ISSUE**"),
            ("ops_history_md", "| `2026-06-17` | OP/CD ACTIVE | UNREADABLE"),
            ("ops_history_md", "Primary lane status artifacts were missing or unreadable. Refresh the daily wrapper before drawing conclusions."),
            ("daily_summary", "Preflight context: primary paper-basket target tracks racing today: OP."),
        ],
    },
    {
        "name": "case_right_now_md_placeholder",
        "run_date": "2026-06-03",
        "wrapper_args": [],
        "scenario": "markdown-only right-now render failures no longer kill the wrapper once the text card already exists, they write a placeholder mirror instead",
        "assertions": [
            ("right_now_md", "Markdown render failed during the daily wrapper run"),
            ("right_now_md", "Quick reads:"),
            ("right_now_md", "Text artifact: `PAPER_TRADE_NOW.txt`"),
            ("right_now_md", "Rolling ops history: `OPS_HISTORY.md`"),
            ("right_now_md", "read the Phase 7 current paper next-step artifact directly"),
            ("ops_history_md", "| `2026-06-03` | OP/CD ACTIVE | BETS READY (1 bet)"),
            ("daily_summary", "Preflight context: primary paper-basket target tracks racing today: OP, CD."),
            ("logfile", "WARN: paper-trade right now markdown render failed; wrote placeholder mirror"),
        ],
    },
    {
        "name": "case_lane_summary_fallback",
        "run_date": "2026-06-04",
        "wrapper_args": [],
        "scenario": "lane-summary enrichment failures no longer destroy an already-written base summary, they log a warning and keep the honest status line",
        "assertions": [
            ("primary_summary", "Phase 7 current paper run 2026-06-04T16:05:00: bets ready, 1 scanner hit(s), 1 recommendation(s), 1 BET"),
            ("shadow_summary", "Phase 8 shadow run 2026-06-04T16:07:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)"),
            ("right_now_md", "Settle the primary lane first"),
            ("ops_history_md", "| `2026-06-04` | OP/CD ACTIVE | BETS READY (1 bet)"),
            ("daily_summary", "Preflight context: primary paper-basket target tracks racing today: OP, CD."),
            ("logfile", "WARN: lane summary helper failed for Phase 7 current paper; kept base summary"),
            ("logfile", "WARN: lane summary helper failed for Phase 8 shadow; kept base summary"),
        ],
    },
    {
        "name": "case_daily_summary_fallback",
        "run_date": "2026-06-05",
        "wrapper_args": [],
        "scenario": "combined daily-summary helper failures no longer kill the wrapper once the core artifacts exist, they write a placeholder top-level summary instead",
        "assertions": [
            ("daily_summary", "WARNING: combined daily summary helper failed, so this placeholder summary points to the core text artifacts instead."),
            ("daily_summary", "Preflight context: primary paper-basket target tracks racing today: OP, CD."),
            ("daily_summary", "Current live hierarchy:"),
            ("daily_summary", "`OP_DURABLE_K7` remains the anchor; `CD_CORE_K8` remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion."),
            ("daily_summary", "Primary lane context:"),
            ("daily_summary", "Primary lane why now: 1 settlement row(s) are still open, so the clean next step is result entry before asking the forward checker for a fresher read."),
            ("daily_summary", "Shadow lane context:"),
            ("daily_summary", "Shadow lane why now: No ROI-complete races are settled yet. The first statistical read is still 0/20 ROI-complete settled rows, and the broader portfolio review gate is 0/100, so the right move is to keep the daily observation loop running instead of over-reading empty forward metrics."),
            ("daily_summary", "- Shadow summary: out/daily_portfolio_runs/2026-06-05/phase8_shadow/summary.txt"),
            ("daily_summary", "PRIMARY: Phase 7 current paper basket (OP + CD rule components; target cards require preflight)"),
            ("daily_summary", "SHADOW: Phase 8 watch-list basket"),
            ("daily_summary", "Phase 8 shadow run 2026-06-05T16:07:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)"),
            ("right_now_md", "Settle the primary lane first"),
            ("ops_history_md", "| `2026-06-05` | OP/CD ACTIVE | BETS READY (1 bet)"),
            ("logfile", "WARN: combined daily summary helper failed; wrote placeholder summary"),
        ],
    },
    {
        "name": "case_unreadable_preflight_json",
        "run_date": "2026-06-06",
        "wrapper_args": [],
        "scenario": "malformed preflight JSON no longer softens into a missing-note day, the wrapper keeps running while ops history marks the calendar as unreadable",
        "assertions": [
            ("primary_summary", "clean empty run, 0 scanner hit(s), 0 recommendation(s)"),
            ("primary_summary", "- Summary: out/daily_portfolio_runs/2026-06-06/phase7_current_paper/summary.txt"),
            ("right_now_md", "Refresh the daily wrapper, calendar state is unknown"),
            ("right_now_md", "operationally ambiguous"),
            ("ops_history_md", "| `2026-06-06` | UNREADABLE | CLEAN EMPTY"),
            ("ops_history_md", "UNKNOWN CALENDAR"),
            ("daily_summary", "Preflight context: primary paper-basket target tracks racing today: OP, CD."),
        ],
    },
    {
        "name": "case_blank_text_prefers_json_preflight_note",
        "run_date": "2026-06-18",
        "wrapper_args": [],
        "scenario": "a blank preflight_note.txt no longer outranks a valid saved preflight_note.json note on an active-target day anywhere in the real daily wrapper path",
        "assertions": [
            ("primary_summary", "clean empty run, 0 scanner hit(s), 0 recommendation(s)"),
            ("right_now_md", "Saved JSON note should still drive the wrapper when preflight_note.txt is blank."),
            ("right_now_md", "Preflight note artifact: `out/daily_portfolio_runs/2026-06-18/preflight_note.json`"),
            ("daily_summary", "Saved JSON note should still drive the wrapper when preflight_note.txt is blank."),
            ("daily_summary", "- Preflight note: out/daily_portfolio_runs/2026-06-18/preflight_note.json"),
            ("ops_history_md", "| `2026-06-18` | OP/CD ACTIVE | CLEAN EMPTY"),
        ],
    },
    {
        "name": "case_blank_text_no_targets_prefers_json_preflight_note",
        "run_date": "2026-06-19",
        "wrapper_args": ["--cache-only", "--max-races", "1"],
        "scenario": "a blank preflight_note.txt no longer outranks a valid saved preflight_note.json note on a true no-target day anywhere in the real daily wrapper path",
        "assertions": [
            ("primary_summary", "cache miss (cache-only)"),
            ("right_now_md", "Stand down, no OP / CD target action tonight"),
            ("right_now_md", "Saved JSON stand-down note should still drive the wrapper when preflight_note.txt is blank."),
            ("right_now_md", "Preflight note artifact: `out/daily_portfolio_runs/2026-06-19/preflight_note.json`"),
            ("daily_summary", "Saved JSON stand-down note should still drive the wrapper when preflight_note.txt is blank."),
            ("daily_summary", "- Preflight note: out/daily_portfolio_runs/2026-06-19/preflight_note.json"),
            ("ops_history_md", "| `2026-06-19` | NO TARGETS |"),
        ],
    },
    {
        "name": "case_preflight_helper_failure",
        "run_date": "2026-06-08",
        "wrapper_args": [],
        "scenario": "preflight helper failures no longer abort the daily wrapper, they degrade to explicit placeholder note artifacts while the rest of the run stays usable",
        "assertions": [
            ("primary_summary", "clean empty run, 0 scanner hit(s), 0 recommendation(s)"),
            ("right_now_md", "Refresh the daily wrapper, calendar state is unknown"),
            ("right_now_md", "operationally ambiguous"),
            ("ops_history_md", "| `2026-06-08` | UNKNOWN | CLEAN EMPTY"),
            ("ops_history_md", "UNKNOWN CALENDAR"),
            ("daily_summary", "Preflight context unavailable because preflight-note helper failed during the daily wrapper run."),
            ("logfile", "WARN: preflight-note text helper failed; wrote placeholder note"),
            ("logfile", "WARN: preflight-note json helper failed; wrote placeholder JSON"),
        ],
    },
    {
        "name": "case_ops_history_fallback",
        "run_date": "2026-06-09",
        "wrapper_args": [],
        "scenario": "ops-history helper failures no longer abort the daily wrapper after both lanes finish, they write placeholder history artifacts and keep the right-now and daily-summary surfaces usable",
        "assertions": [
            ("primary_summary", "Quick files:"),
            ("ops_history_md", "Latest refresh failed during the daily wrapper run"),
            ("ops_history_md", "out/daily_portfolio_runs/2026-06-09"),
            ("ops_history_md", "Next step: rerun ./run_daily_portfolio_observation.sh or python3 paper_trade_ops_history.py."),
            ("right_now_md", "Follow the Phase 7 current paper lane next-step lead"),
            ("daily_summary", "Preflight context: primary paper-basket target tracks racing today: OP, CD."),
            ("logfile", "WARN: ops-history helper failed; wrote placeholder artifacts"),
        ],
    },
    {
        "name": "case_right_now_helper_failure",
        "run_date": "2026-06-10",
        "wrapper_args": [],
        "scenario": "right-now helper failures no longer abort the daily wrapper after ops history succeeds, they write a placeholder text card and markdown mirror so the run still closes cleanly",
        "assertions": [
            ("primary_summary", "Quick files:"),
            ("right_now_md", "Markdown render failed during the daily wrapper run"),
            ("right_now_md", "Quick reads:"),
            ("right_now_md", "Rolling ops history: `OPS_HISTORY.md`"),
            ("right_now_md", "read the Phase 7 current paper next-step artifact directly"),
            ("right_now_md", "Primary lane context: Latest run context: the latest live scan completed cleanly and found no qualifying races across 1 card(s) and 8 race(s)."),
            ("right_now_md", "Primary lane why now: No ROI-complete races are settled yet. The first statistical read is still 0/30 ROI-complete settled rows, and the broader portfolio review gate is 0/100, so the right move is to keep the daily observation loop running instead of over-reading empty forward metrics."),
            ("right_now_md", "Shadow lane context: Latest run context: the latest live scan completed cleanly and found no qualifying races across 1 card(s) and 8 race(s)."),
            ("right_now_md", "Shadow lane why now: No ROI-complete races are settled yet. The first statistical read is still 0/20 ROI-complete settled rows, and the broader portfolio review gate is 0/100, so the right move is to keep the daily observation loop running instead of over-reading empty forward metrics."),
            ("right_now_md", "out/daily_portfolio_runs/2026-06-10/phase7_current_paper/next_steps.txt"),
            ("right_now_md", "out/daily_portfolio_runs/2026-06-10/phase8_shadow/next_steps.txt"),
            ("ops_history_md", "| `2026-06-10` | OP/CD ACTIVE | CLEAN EMPTY"),
            ("daily_summary", "Right now: PAPER_TRADE_NOW.md"),
            ("logfile", "WARN: right-now text helper failed; wrote placeholder card"),
            ("logfile", "WARN: paper-trade right now markdown render failed; wrote placeholder mirror"),
        ],
    },
    {
        "name": "case_forward_check_helper_failure",
        "run_date": "2026-06-11",
        "wrapper_args": [],
        "scenario": "forward-check helper failures no longer abort the lane once the base summary and settlement sync already exist, they write placeholder forward-check artifacts and keep the wrapper usable",
        "assertions": [
            ("primary_summary", "Quick files:"),
            ("primary_forward_check_md", "Markdown render failed during the daily wrapper run"),
            ("primary_forward_check_md", "Text artifact: `out/daily_portfolio_runs/2026-06-11/phase7_current_paper/forward_check.txt`"),
            ("primary_forward_check_md", "Forward assessment: unavailable because the forward-check helper failed during the daily wrapper run."),
            ("shadow_forward_check_md", "Markdown render failed during the daily wrapper run"),
            ("shadow_forward_check_md", "Text artifact: `out/daily_portfolio_runs/2026-06-11/phase8_shadow/forward_check.txt`"),
            ("ops_history_md", "| `2026-06-11` | OP/CD ACTIVE | CLEAN EMPTY"),
            ("daily_summary", "Preflight context: primary paper-basket target tracks racing today: OP, CD."),
            ("logfile", "WARN: forward-check helper failed for Phase 7 current paper; wrote placeholder forward check"),
            ("logfile", "WARN: Phase 7 current paper forward check markdown render failed; wrote placeholder mirror"),
            ("logfile", "WARN: forward-check helper failed for Phase 8 shadow; wrote placeholder forward check"),
            ("logfile", "WARN: Phase 8 shadow forward check markdown render failed; wrote placeholder mirror"),
        ],
    },
    {
        "name": "case_lane_monitor_helper_failure",
        "run_date": "2026-06-12",
        "wrapper_args": [],
        "scenario": "lane-monitor helper failures no longer abort the lane once forward-check text already exists, they write placeholder monitor artifacts and keep the wrapper usable",
        "assertions": [
            ("primary_summary", "Quick files:"),
            ("primary_lane_monitor_md", "Markdown render failed during the daily wrapper run"),
            ("primary_lane_monitor_md", "Text artifact: `out/daily_portfolio_runs/2026-06-12/phase7_current_paper/lane_monitor.txt`"),
            ("primary_lane_monitor_md", "Forward assessment: unavailable because the lane-monitor helper failed during the daily wrapper run."),
            ("shadow_lane_monitor_md", "Markdown render failed during the daily wrapper run"),
            ("shadow_lane_monitor_md", "Text artifact: `out/daily_portfolio_runs/2026-06-12/phase8_shadow/lane_monitor.txt`"),
            ("ops_history_md", "| `2026-06-12` | OP/CD ACTIVE | CLEAN EMPTY"),
            ("daily_summary", "Preflight context: primary paper-basket target tracks racing today: OP, CD."),
            ("logfile", "WARN: lane monitor helper failed for Phase 7 current paper; wrote placeholder monitor"),
            ("logfile", "WARN: Phase 7 current paper lane monitor markdown render failed; wrote placeholder mirror"),
            ("logfile", "WARN: lane monitor helper failed for Phase 8 shadow; wrote placeholder monitor"),
            ("logfile", "WARN: Phase 8 shadow lane monitor markdown render failed; wrote placeholder mirror"),
        ],
    },
    {
        "name": "case_next_steps_helper_failure",
        "run_date": "2026-06-13",
        "wrapper_args": [],
        "scenario": "next-steps helper failures no longer abort the lane after the base artifacts exist, they write placeholder next-step artifacts and let the wrapper finish cleanly",
        "assertions": [
            ("primary_summary", "Quick files:"),
            ("primary_next_steps", "State: REFRESH NEXT-STEPS ARTIFACTS"),
            ("primary_next_steps", "next-steps helper failed during the daily wrapper run"),
            ("primary_next_steps_md", "Markdown render failed during the daily wrapper run"),
            ("primary_next_steps_md", "Text artifact: `out/daily_portfolio_runs/2026-06-13/phase7_current_paper/next_steps.txt`"),
            ("shadow_next_steps", "State: REFRESH NEXT-STEPS ARTIFACTS"),
            ("shadow_next_steps_md", "Markdown render failed during the daily wrapper run"),
            ("shadow_next_steps_md", "Text artifact: `out/daily_portfolio_runs/2026-06-13/phase8_shadow/next_steps.txt`"),
            ("right_now_md", "Follow the Phase 7 current paper lane next-step lead"),
            ("ops_history_md", "| `2026-06-13` | OP/CD ACTIVE | CLEAN EMPTY"),
            ("daily_summary", "Preflight context: primary paper-basket target tracks racing today: OP, CD."),
            ("logfile", "WARN: next-steps helper failed for Phase 7 current paper; wrote placeholder next steps"),
            ("logfile", "WARN: Phase 7 current paper next steps markdown render failed; wrote placeholder mirror"),
            ("logfile", "WARN: next-steps helper failed for Phase 8 shadow; wrote placeholder next steps"),
            ("logfile", "WARN: Phase 8 shadow next steps markdown render failed; wrote placeholder mirror"),
        ],
    },
    {
        "name": "case_pipeline_error_refresh",
        "run_date": "2026-06-14",
        "wrapper_args": [],
        "scenario": "active-target recommender-stage pipeline errors stay explicit through the full wrapper path instead of flattening into normal observation guidance",
        "assertions": [
            ("primary_summary", "recommender failure"),
            ("primary_summary", "stage recommender"),
            ("primary_next_steps", "State: CHECK PIPELINE FAILURE"),
            ("primary_next_steps", "latest lane run ended in recommender failure"),
            ("right_now_md", "Refresh the daily wrapper, primary lane hit a recommender failure"),
            ("right_now_md", "Primary lane context: Latest run context: the latest lane run ended in recommender failure."),
            ("ops_history_md", "| `2026-06-14` | OP/CD ACTIVE | RECOMMENDER FAILURE (hits=1, recs=0, bets=0)"),
            ("ops_history_md", "Primary lane hit a recommender failure. After scanner completed, 1 hit(s) were already found before the failure. Error type: RuntimeError. Detail: fixture recommender crash. Refresh the daily wrapper and re-check sidecars before treating the day as evidence."),
            ("daily_summary", "Preflight context: primary paper-basket target tracks racing today: OP, CD."),
            ("daily_summary", "recommender failure"),
        ],
    },
    {
        "name": "case_pipeline_logger_error_refresh",
        "run_date": "2026-06-15",
        "wrapper_args": [],
        "scenario": "active-target logger-stage pipeline errors stay explicit through the full wrapper path instead of flattening into normal observation guidance",
        "assertions": [
            ("primary_summary", "logger failure"),
            ("primary_summary", "stage logger"),
            ("primary_next_steps", "State: CHECK PIPELINE FAILURE"),
            ("primary_next_steps", "latest lane run ended in logger failure"),
            ("right_now_md", "Refresh the daily wrapper, primary lane hit a logger failure"),
            ("right_now_md", "Primary lane context: Latest run context: the latest lane run ended in logger failure."),
            ("ops_history_md", "| `2026-06-15` | OP/CD ACTIVE | LOGGER FAILURE (hits=1, recs=1, bets=1)"),
            ("ops_history_md", "Primary lane hit a logger failure. After recommender completed, 1 recommendation(s) were already built and 1 BET recommendation(s) were ready (context: signals_logged_no_bet) before the failure. Error type: ValueError. Detail: fixture logger crash. Refresh the daily wrapper and re-check sidecars before treating the day as evidence."),
            ("daily_summary", "Preflight context: primary paper-basket target tracks racing today: OP, CD."),
            ("daily_summary", "logger failure"),
        ],
    },
]

EXPECTED_CASE_NAMES = {
    "case_no_target_cache_miss",
    "case_active_target_cache_miss",
    "case_missing_scan_output_refresh",
    "case_primary_settlement",
    "case_active_signals_no_bet",
    "case_shadow_settlement",
    "case_partial_cache_refresh",
    "case_missing_primary_status",
    "case_unreadable_primary_scanner_status",
    "case_unreadable_primary_pipeline_status",
    "case_right_now_md_placeholder",
    "case_lane_summary_fallback",
    "case_daily_summary_fallback",
    "case_unreadable_preflight_json",
    "case_blank_text_prefers_json_preflight_note",
    "case_blank_text_no_targets_prefers_json_preflight_note",
    "case_preflight_helper_failure",
    "case_ops_history_fallback",
    "case_right_now_helper_failure",
    "case_forward_check_helper_failure",
    "case_lane_monitor_helper_failure",
    "case_next_steps_helper_failure",
    "case_pipeline_error_refresh",
    "case_pipeline_logger_error_refresh",
}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, indent=2) + "\n")


def require_positive_non_bool_int(value: Any, *, source_name: str, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, source_name: str, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AssertionError(f"{source_name} {field_name} must be a list of strings")
    return value


def read_scorecard_gate_minimums(scorecard_json: Path = SCORECARD_JSON) -> dict[str, Any]:
    source_name = display_path(scorecard_json)
    payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
    gates = payload.get("decision_gate_minimums")
    if not isinstance(gates, dict):
        raise AssertionError(f"{source_name} is missing decision_gate_minimums")
    anchor = gates.get("anchor_displacement")
    phase8 = gates.get("phase8_promotion_review")
    real_money = gates.get("real_money_discussion")
    if not isinstance(anchor, dict) or not isinstance(phase8, dict) or not isinstance(real_money, dict):
        raise AssertionError(f"{source_name} decision_gate_minimums is incomplete")
    anchor_min = require_positive_non_bool_int(
        anchor.get("min_roi_complete_settled_observations"),
        source_name=source_name,
        field_name="decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
    )
    phase8_min = require_positive_non_bool_int(
        phase8.get("min_roi_complete_settled_observations"),
        source_name=source_name,
        field_name="decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
    )
    real_money_min = require_positive_non_bool_int(
        real_money.get("min_total_settled_observations_with_usable_roi"),
        source_name=source_name,
        field_name="decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
    )
    real_money_requires = require_string_list(
        real_money.get("also_requires"),
        source_name=source_name,
        field_name="decision_gate_minimums.real_money_discussion.also_requires",
    )
    if NO_BAQ_AS_BEL_PREREQUISITE not in real_money_requires:
        raise AssertionError(
            f"{source_name} decision_gate_minimums.real_money_discussion.also_requires "
            f"must include {NO_BAQ_AS_BEL_PREREQUISITE}"
        )
    return {
        "source": source_name,
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_also_requires": real_money_requires,
        "real_money_no_baq_as_bel_required": True,
        "evidence_boundary": (
            "daily-wrapper fixture runs, right-now card rerenders, current-evidence bridge refreshes, "
            "clean-empty/no-target/cache-miss branches, and helper-fallback paths do not count toward "
            "anchor-displacement, Phase 8 promotion-review, or real-money discussion gates"
        ),
    }


def parse_main_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--current-evidence-json", type=Path, default=CURRENT_EVIDENCE_JSON)
    parser.add_argument("--fixture-root", type=Path)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args(argv)


def configure_output_paths(out_dir: Path) -> None:
    global OUT_DIR, OUT_MD, OUT_JSON
    OUT_DIR = out_dir
    OUT_MD = OUT_DIR / "run_daily_portfolio_observation_validation.md"
    OUT_JSON = OUT_DIR / "run_daily_portfolio_observation_validation.json"


def assert_scorecard_failure_before_artifacts(
    *,
    scorecard_json: Path,
    current_evidence_json: Path,
    mutation: Any,
    expected_stderr: str,
    check_name: str,
    detail: str,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"{check_name}_") as tmp:
        tmpdir = Path(tmp)
        bad_scorecard = tmpdir / "forward_evidence_scorecard.json"
        bad_payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
        mutation(bad_payload)
        bad_scorecard.write_text(json.dumps(bad_payload, indent=2) + "\n", encoding="utf-8")

        fixture_root_path = tmpdir / "fixture_root"
        out_dir = tmpdir / "nested" / "report_artifacts"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(bad_scorecard),
                "--current-evidence-json",
                str(current_evidence_json),
                "--fixture-root",
                str(fixture_root_path),
                "--out-dir",
                str(out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
        if result.returncode == 0:
            raise AssertionError(f"{check_name}: malformed scorecard unexpectedly passed")
        if expected_stderr not in result.stderr:
            raise AssertionError(
                f"{check_name}: failure stderr no longer explains the malformed scorecard gate\n"
                f"stderr={result.stderr}"
            )
        if fixture_root_path.exists() or out_dir.exists():
            raise AssertionError(f"{check_name}: malformed scorecard created fixture/report artifacts")
    return require(True, check_name, detail)


def scorecard_no_artifact_guardrails(scorecard_json: Path, current_evidence_json: Path) -> list[dict[str, Any]]:
    return [
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            current_evidence_json=current_evidence_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["anchor_displacement"].__setitem__(
                "min_roi_complete_settled_observations",
                True,
            ),
            expected_stderr=(
                "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check_name="scorecard_boolean_gate_floor_fails_before_daily_wrapper_artifacts",
            detail=(
                "a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before "
                "the daily-wrapper validator creates fixture roots or report artifacts"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            current_evidence_json=current_evidence_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["phase8_promotion_review"].__setitem__(
                "min_roi_complete_settled_observations",
                0,
            ),
            expected_stderr=(
                "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check_name="scorecard_nonpositive_phase8_gate_floor_fails_before_daily_wrapper_artifacts",
            detail=(
                "a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails before "
                "the daily-wrapper validator creates fixture roots or report artifacts"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            current_evidence_json=current_evidence_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                "min_total_settled_observations_with_usable_roi",
                0,
            ),
            expected_stderr=(
                "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi "
                "must be a positive non-boolean integer"
            ),
            check_name="scorecard_nonpositive_real_money_gate_floor_fails_before_daily_wrapper_artifacts",
            detail=(
                "a non-positive real-money discussion floor in forward_evidence_scorecard.json fails before "
                "the daily-wrapper validator creates fixture roots or report artifacts"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            current_evidence_json=current_evidence_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                "also_requires",
                [
                    item
                    for item in payload["decision_gate_minimums"]["real_money_discussion"].get(
                        "also_requires",
                        [],
                    )
                    if item != NO_BAQ_AS_BEL_PREREQUISITE
                ],
            ),
            expected_stderr=(
                "decision_gate_minimums.real_money_discussion.also_requires must include "
                f"{NO_BAQ_AS_BEL_PREREQUISITE}"
            ),
            check_name="scorecard_missing_no_baq_fails_before_daily_wrapper_artifacts",
            detail=(
                "a scorecard real-money gate that drops the no BAQ-as-BEL prerequisite fails before "
                "the daily-wrapper validator creates fixture roots or report artifacts"
            ),
        ),
    ]


def assert_current_evidence_failure_before_artifacts(
    *,
    scorecard_json: Path,
    current_evidence_json: Path,
    mutation: Any,
    expected_stderr: str,
    check_name: str,
    detail: str,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"{check_name}_") as tmp:
        tmpdir = Path(tmp)
        bad_current_evidence = tmpdir / "current_evidence_summary.json"
        bad_payload = json.loads(current_evidence_json.read_text(encoding="utf-8"))
        mutation(bad_payload)
        bad_current_evidence.write_text(json.dumps(bad_payload, indent=2) + "\n", encoding="utf-8")

        fixture_root_path = tmpdir / "fixture_root"
        out_dir = tmpdir / "nested" / "report_artifacts"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(scorecard_json),
                "--current-evidence-json",
                str(bad_current_evidence),
                "--fixture-root",
                str(fixture_root_path),
                "--out-dir",
                str(out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
        if result.returncode == 0:
            raise AssertionError(f"{check_name}: malformed current-evidence sidecar unexpectedly passed")
        if expected_stderr not in result.stderr:
            raise AssertionError(
                f"{check_name}: failure stderr no longer explains the malformed current-evidence rebuild contract\n"
                f"stderr={result.stderr}"
            )
        if fixture_root_path.exists() or out_dir.exists():
            raise AssertionError(f"{check_name}: malformed current-evidence sidecar created fixture/report artifacts")
    return require(True, check_name, detail)


def current_evidence_no_artifact_guardrails(
    scorecard_json: Path,
    current_evidence_json: Path,
) -> list[dict[str, Any]]:
    return [
        assert_current_evidence_failure_before_artifacts(
            scorecard_json=scorecard_json,
            current_evidence_json=current_evidence_json,
            mutation=lambda payload: payload.pop("rebuild_validation_contract", None),
            expected_stderr="current evidence bridge did not publish rebuild_validation_contract",
            check_name="current_evidence_missing_rebuild_contract_fails_before_daily_wrapper_artifacts",
            detail=(
                "a current_evidence_summary.json sidecar missing rebuild_validation_contract fails before "
                "the daily-wrapper validator creates fixture roots or report artifacts"
            ),
        ),
        assert_current_evidence_failure_before_artifacts(
            scorecard_json=scorecard_json,
            current_evidence_json=current_evidence_json,
            mutation=lambda payload: payload["rebuild_validation_contract"].__setitem__(
                "upstream_refresh_order_is_provenance_metadata_only",
                False,
            ),
            expected_stderr="current evidence rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true",
            check_name="current_evidence_weakened_rebuild_contract_fails_before_daily_wrapper_artifacts",
            detail=(
                "a current_evidence_summary.json sidecar whose rebuild order is no longer provenance metadata only "
                "fails before the daily-wrapper validator creates fixture roots or report artifacts"
            ),
        ),
    ]


def assert_contains(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"{label}: expected to find {needle!r}")


def operator_issue_flags_line(gate: dict[str, Any]) -> str:
    parts: list[str] = []
    for flag in OPERATOR_READ_GATE_ISSUE_FLAGS:
        value = gate.get(flag)
        if not isinstance(value, bool):
            raise AssertionError(f"operator_read_gate.{flag} must stay a boolean")
        parts.append(f"{flag}={str(value).lower()}")
    return "- Current operator read-gate issue flags: " + "; ".join(parts)


def rerender_right_now_json(case_root: Path, run_root: Path, run_date: str, settlement_audit_md: Path) -> str:
    expected_path = case_root / ".expected_PAPER_TRADE_NOW.json"
    cmd = [
        sys.executable,
        str(case_root / "paper_trade_now.py"),
        "--run-root",
        str(run_root),
        "--as-of-date",
        run_date,
        "--settlement-audit",
        str(settlement_audit_md),
        "--format",
        "json",
        "--output",
        str(expected_path),
    ]
    result = subprocess.run(cmd, cwd=case_root, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise AssertionError(f"right-now JSON source-layer rerender failed: {detail}")
    return expected_path.read_text(encoding="utf-8")


def rewrite_main_exit(path: Path, stderr_line: str) -> None:
    text = path.read_text(encoding="utf-8")
    sentinel = 'if __name__ == "__main__":\n    raise SystemExit(main())\n'
    replacement = (
        'if __name__ == "__main__":\n'
        '    import sys\n\n'
        f'    print({stderr_line!r}, file=sys.stderr)\n'
        '    raise SystemExit(1)\n'
    )
    if sentinel not in text:
        raise AssertionError(f"could not find __main__ sentinel in {path}")
    path.write_text(text.replace(sentinel, replacement), encoding="utf-8")


def copy_fixture_project(case_root: Path) -> None:
    if case_root.exists():
        shutil.rmtree(case_root)
    case_root.mkdir(parents=True, exist_ok=True)

    for rel_name in COPIED_FILES:
        source = BASE / rel_name
        target = case_root / rel_name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    write_text(case_root / "paper_trade_preflight_note.py", PREFLIGHT_STUB)
    write_text(case_root / "paper_trade_pipeline.py", PIPELINE_STUB)
    if case_root.name == "case_right_now_md_placeholder":
        write_text(case_root / "paper_trade_now.py", RIGHT_NOW_MD_FAIL_STUB)
    if case_root.name == "case_right_now_helper_failure":
        write_text(case_root / "paper_trade_now.py", RIGHT_NOW_HELPER_FAIL_STUB)
    if case_root.name == "case_forward_check_helper_failure":
        rewrite_main_exit(case_root / "paper_trade_forward_check.py", "fixture forward check failure")
    if case_root.name == "case_lane_monitor_helper_failure":
        rewrite_main_exit(case_root / "paper_trade_lane_monitor.py", "fixture lane monitor failure")
    if case_root.name == "case_next_steps_helper_failure":
        rewrite_main_exit(case_root / "paper_trade_next_steps.py", "fixture next steps failure")
    if case_root.name == "case_lane_summary_fallback":
        write_text(case_root / "paper_trade_lane_summary.py", LANE_SUMMARY_FAIL_STUB)
    if case_root.name == "case_daily_summary_fallback":
        write_text(case_root / "paper_trade_daily_summary.py", DAILY_SUMMARY_FAIL_STUB)
    if case_root.name == "case_ops_history_fallback":
        write_text(case_root / "paper_trade_ops_history.py", OPS_HISTORY_FAIL_STUB)
    (case_root / "run_daily_portfolio_observation.sh").chmod(0o755)
    (case_root / "paper_trade_preflight_note.py").chmod(0o755)
    (case_root / "paper_trade_pipeline.py").chmod(0o755)
    if case_root.name == "case_right_now_md_placeholder":
        (case_root / "paper_trade_now.py").chmod(0o755)
    if case_root.name == "case_right_now_helper_failure":
        (case_root / "paper_trade_now.py").chmod(0o755)
    if case_root.name == "case_lane_summary_fallback":
        (case_root / "paper_trade_lane_summary.py").chmod(0o755)
    if case_root.name == "case_daily_summary_fallback":
        (case_root / "paper_trade_daily_summary.py").chmod(0o755)
    if case_root.name == "case_ops_history_fallback":
        (case_root / "paper_trade_ops_history.py").chmod(0o755)
    (case_root / "paper_trades").mkdir(parents=True, exist_ok=True)


def gather_artifacts(case_root: Path, run_date: str) -> dict[str, Path]:
    run_root = case_root / "out" / "daily_portfolio_runs" / run_date
    primary_dir = run_root / "phase7_current_paper"
    shadow_dir = run_root / "phase8_shadow"
    return {
        "run_root": run_root,
        "primary_summary": primary_dir / "summary.txt",
        "primary_next_steps": primary_dir / "next_steps.txt",
        "primary_next_steps_md": primary_dir / "next_steps.md",
        "primary_forward_check_md": primary_dir / "forward_check.md",
        "primary_lane_monitor_md": primary_dir / "lane_monitor.md",
        "settlement_ledger": case_root / "paper_trades" / "phase7_current_paper_paper_trade_settlements.csv",
        "shadow_summary": shadow_dir / "summary.txt",
        "shadow_next_steps": shadow_dir / "next_steps.txt",
        "shadow_next_steps_md": shadow_dir / "next_steps.md",
        "shadow_forward_check_md": shadow_dir / "forward_check.md",
        "shadow_lane_monitor_md": shadow_dir / "lane_monitor.md",
        "shadow_settlement_ledger": case_root / "paper_trades" / "phase8_shadow_paper_trade_settlements.csv",
        "primary_pipeline_status": primary_dir / "pipeline_status.json",
        "shadow_pipeline_status": shadow_dir / "pipeline_status.json",
        "right_now_txt": case_root / "PAPER_TRADE_NOW.txt",
        "right_now_md": case_root / "PAPER_TRADE_NOW.md",
        "right_now_json": case_root / "PAPER_TRADE_NOW.json",
        "current_evidence_md": case_root / "CURRENT_EVIDENCE_SUMMARY.md",
        "current_evidence_json": case_root / "current_evidence_summary.json",
        "ops_history_md": case_root / "OPS_HISTORY.md",
        "settlement_audit_md": case_root / "out" / "paper_trade_settlement_audit.md",
        "settlement_audit_json": case_root / "out" / "paper_trade_settlement_audit.json",
        "daily_summary": run_root / "daily_summary.txt",
        "logfile": case_root / "logs" / f"daily_portfolio_observation_{run_date}.log",
    }


def run_case(case: dict[str, Any], root: Path) -> dict[str, Any]:
    case_root = root / case["name"]
    copy_fixture_project(case_root)

    env = os.environ.copy()
    env.update({
        "PYTHON_BIN": sys.executable,
        "RUN_DATE": case["run_date"],
        "FIXTURE_CASE": case["name"],
    })

    cmd = ["bash", str(case_root / "run_daily_portfolio_observation.sh"), *case["wrapper_args"]]
    result = subprocess.run(cmd, cwd=case_root, env=env, capture_output=True, text=True, check=True)
    artifacts = gather_artifacts(case_root, case["run_date"])

    optional_missing = {"primary_pipeline_status", "shadow_pipeline_status"}
    for label, path in artifacts.items():
        if label in optional_missing:
            continue
        if not path.exists():
            raise AssertionError(f"{case['name']}: missing expected artifact {label}: {path}")

    texts = {
        label: path.read_text(encoding="utf-8")
        for label, path in artifacts.items()
        if label not in {"run_root", "primary_pipeline_status", "shadow_pipeline_status"}
    }
    run_root_rel = artifacts["run_root"].relative_to(case_root)
    daily_summary_text = texts["daily_summary"]
    assert_contains(daily_summary_text, "Right now: PAPER_TRADE_NOW.md", f"{case['name']} daily_summary routed right-now quick jump")
    assert_contains(daily_summary_text, "Rolling ops history: OPS_HISTORY.md", f"{case['name']} daily_summary routed ops-history quick jump")
    assert_contains(daily_summary_text, "Settlement audit: out/paper_trade_settlement_audit.md", f"{case['name']} daily_summary routed settlement-audit quick jump")
    assert_contains(
        daily_summary_text,
        f"- Preflight note: {expected_preflight_jump_path(artifacts['run_root'], run_root_rel)}",
        f"{case['name']} daily_summary routed preflight quick jump",
    )
    assert_contains(daily_summary_text, f"- Primary summary: {run_root_rel / 'phase7_current_paper/summary.txt'}", f"{case['name']} daily_summary routed primary summary quick jump")
    assert_contains(daily_summary_text, f"- Shadow summary: {run_root_rel / 'phase8_shadow/summary.txt'}", f"{case['name']} daily_summary routed shadow summary quick jump")
    assert_contains(daily_summary_text, f"Artifacts root: {run_root_rel}", f"{case['name']} daily_summary routed artifacts-root pointer")
    if case["name"] != "case_daily_summary_fallback":
        assert_contains(daily_summary_text, "Right-now snapshot:", f"{case['name']} daily_summary right-now snapshot header")
        right_now_focus = extract_optional_bullet_value(texts["right_now_md"], "Focus")
        right_now_timing = extract_optional_bullet_value(texts["right_now_md"], "Timing")
        right_now_run_freshness = extract_optional_bullet_value(texts["right_now_md"], "Run freshness")
        right_now_ops_bucket = extract_optional_bullet_value(texts["right_now_md"], "Latest ops bucket")
        if right_now_focus:
            assert_contains(daily_summary_text, f"- Current operator focus: {right_now_focus}", f"{case['name']} daily_summary right-now focus snapshot")
        if right_now_timing:
            assert_contains(daily_summary_text, f"- Current timing: {right_now_timing}", f"{case['name']} daily_summary right-now timing snapshot")
        if right_now_run_freshness:
            assert_contains(daily_summary_text, f"- Current run freshness: {right_now_run_freshness}", f"{case['name']} daily_summary right-now freshness snapshot")
        if right_now_ops_bucket:
            assert_contains(daily_summary_text, f"- Current ops bucket: {right_now_ops_bucket}", f"{case['name']} daily_summary right-now ops-bucket snapshot")
        assert_contains(daily_summary_text, f"- Primary next steps: {run_root_rel / 'phase7_current_paper/next_steps.md'}", f"{case['name']} daily_summary routed primary next-steps quick jump")
        assert_contains(daily_summary_text, f"- Primary lane monitor: {run_root_rel / 'phase7_current_paper/lane_monitor.md'}", f"{case['name']} daily_summary routed primary lane-monitor quick jump")
        assert_contains(daily_summary_text, f"- Primary forward check: {run_root_rel / 'phase7_current_paper/forward_check.md'}", f"{case['name']} daily_summary routed primary forward-check quick jump")
        assert_contains(daily_summary_text, f"- Shadow next steps: {run_root_rel / 'phase8_shadow/next_steps.md'}", f"{case['name']} daily_summary routed shadow next-steps quick jump")
        assert_contains(daily_summary_text, f"- Shadow lane monitor: {run_root_rel / 'phase8_shadow/lane_monitor.md'}", f"{case['name']} daily_summary routed shadow lane-monitor quick jump")
        assert_contains(daily_summary_text, f"- Shadow forward check: {run_root_rel / 'phase8_shadow/forward_check.md'}", f"{case['name']} daily_summary routed shadow forward-check quick jump")
    assert_contains(texts["right_now_md"], "OPS_HISTORY.md", f"{case['name']} right_now_md routed ops-history reference")
    assert_contains(texts["settlement_audit_md"], "Paper Trade Settlement Audit", f"{case['name']} settlement audit title")
    assert_contains(texts["settlement_audit_md"], "not new forward-performance evidence by itself", f"{case['name']} settlement audit evidence boundary")
    assert_contains(texts["current_evidence_md"], "Current Evidence Summary", f"{case['name']} current evidence bridge title")
    assert_contains(texts["current_evidence_md"], "not forward-performance evidence", f"{case['name']} current evidence bridge no-forward-performance boundary")
    current_evidence_payload = read_json_optional(artifacts["current_evidence_json"])
    if not current_evidence_payload:
        raise AssertionError(f"{case['name']}: current_evidence_summary.json was missing, unreadable, or not a JSON object")
    if current_evidence_payload.get("artifact_status") == "placeholder":
        summary = current_evidence_payload.get("summary", {})
        boundary = str(summary.get("evidence_boundary") if isinstance(summary, dict) else "")
        rebuild_order = str(summary.get("rebuild_order") if isinstance(summary, dict) else "")
        if "not forward-performance evidence" not in boundary or "real-money evidence" not in boundary:
            raise AssertionError(f"{case['name']}: current-evidence placeholder dropped the no-forward/real-money boundary")
        if (
            "paper_trade_settlement_audit.py before current_evidence_summary.py" not in boundary
            or "paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py" not in rebuild_order
        ):
            raise AssertionError(f"{case['name']}: current-evidence placeholder did not preserve the settlement-audit-first rebuild order")
        current_evidence_status = "placeholder"
        current_evidence_boundary = True
        current_evidence_recommendation_context_boundary = True
        current_evidence_rebuild_contract_boundary = True
        current_evidence_rebuild_contract = {
            "source_path": "placeholder.summary.rebuild_order",
            "upstream_refresh_order_commands": EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER,
            "evidence_boundary": "placeholder rebuild order is operator recovery metadata only",
        }
    else:
        evidence_boundary = current_evidence_payload.get("evidence_boundary")
        source_freshness = current_evidence_payload.get("source_freshness")
        current_status = current_evidence_payload.get("current_paper_status")
        summary = current_evidence_payload.get("summary")
        current_read = summary.get("current_read") if isinstance(summary, dict) else ""
        if not isinstance(evidence_boundary, dict) or evidence_boundary.get("not_new_forward_evidence") is not True:
            raise AssertionError(f"{case['name']}: current evidence bridge did not preserve not_new_forward_evidence=true")
        if evidence_boundary.get("not_real_money_evidence") is not True:
            raise AssertionError(f"{case['name']}: current evidence bridge did not preserve not_real_money_evidence=true")
        if not isinstance(source_freshness, dict) or (
            source_freshness.get("right_now_freshness_state_valid") is not True
            and source_freshness.get("requires_refresh_before_right_now_use") is not True
        ):
            raise AssertionError(f"{case['name']}: current evidence bridge did not publish a valid freshness state or explicit refresh-before-use routing")
        if not isinstance(current_status, dict) or not isinstance(current_status.get("best_action"), dict):
            raise AssertionError(f"{case['name']}: current evidence bridge did not carry the right-now best-action context")
        if (
            "Recommendation context:" not in current_read
            or "latest open-row context" in current_read
            or "open-row no-BET" in current_read
            or not (
                "operator context only" in current_read
                or "not a bet-ready ticket" in current_read
                or "do not treat the recommendation context itself as forward performance" in current_read
                or "No latest primary recommendation context" in current_read
                or "use recommendation and settlement ledgers before interpreting bet readiness or forward performance" in current_read
            )
        ):
            raise AssertionError(
                f"{case['name']}: current evidence bridge did not keep recommendation-state context separate from open-row or forward-performance wording"
            )
        current_evidence_rebuild_contract = validate_current_evidence_rebuild_contract(
            current_evidence_payload,
            case["name"],
        )
        current_evidence_status = "pass"
        current_evidence_boundary = True
        current_evidence_recommendation_context_boundary = True
        current_evidence_rebuild_contract_boundary = True
    audit_payload = read_json_optional(artifacts["settlement_audit_json"])
    audit_status = audit_payload.get("artifact_status") if audit_payload else None
    if audit_status not in {"pass", "placeholder"}:
        raise AssertionError(f"{case['name']}: settlement audit JSON did not publish an explicit artifact_status")
    audit_lanes: list[str] = []
    audit_next_actions: dict[str, str] = {}
    audit_next_action_reasons: dict[str, str] = {}
    audit_json_boundary = False
    if audit_status == "pass":
        audit_summary = audit_payload.get("summary", {}) if audit_payload else {}
        audit_current_read = audit_summary.get("current_read") if isinstance(audit_summary, dict) else ""
        if not isinstance(audit_current_read, str):
            audit_current_read = ""
        assert_contains(audit_current_read, "ledger-completeness / ROI-coverage audit only", f"{case['name']} settlement audit JSON audit-only boundary")
        assert_contains(audit_current_read, "not new forward evidence by itself", f"{case['name']} settlement audit JSON no-new-evidence boundary")
        lanes = audit_payload.get("lanes") if audit_payload else None
        if not isinstance(lanes, list):
            raise AssertionError(f"{case['name']}: settlement audit JSON did not publish a lanes list")
        audit_lanes = sorted(str(lane.get("name", "")) for lane in lanes if isinstance(lane, dict) and lane.get("name"))
        if set(audit_lanes) != {"primary", "shadow"}:
            raise AssertionError(f"{case['name']}: settlement audit JSON lanes should stay primary/shadow, got {audit_lanes!r}")
        for lane in lanes:
            if not isinstance(lane, dict):
                continue
            lane_name = str(lane.get("name") or "").strip()
            if lane_name not in {"primary", "shadow"}:
                continue
            action = str(lane.get("next_action") or "").strip()
            reason = str(lane.get("next_action_reason") or "").strip()
            if not action:
                raise AssertionError(f"{case['name']}: settlement audit JSON lane {lane_name!r} did not publish next_action")
            if not reason:
                raise AssertionError(f"{case['name']}: settlement audit JSON lane {lane_name!r} did not publish next_action_reason")
            audit_next_actions[lane_name] = action
            audit_next_action_reasons[lane_name] = reason
        if set(audit_next_actions) != {"primary", "shadow"}:
            raise AssertionError(f"{case['name']}: settlement audit JSON next-action inventory should stay primary/shadow, got {audit_next_actions!r}")
        if case["name"] != "case_daily_summary_fallback":
            assert_contains(
                daily_summary_text,
                "- Settlement-audit actions are ledger-readiness guidance only; they are not new forward evidence by themselves.",
                f"{case['name']} daily_summary settlement-audit action boundary",
            )
            for lane_name, label_name in (("primary", "Primary"), ("shadow", "Shadow")):
                expected_action_line = (
                    f"- {label_name} settlement-audit action: {audit_next_actions[lane_name]}"
                    f" — {audit_next_action_reasons[lane_name]}"
                )
                assert_contains(daily_summary_text, expected_action_line, f"{case['name']} daily_summary {lane_name} settlement-audit action line")
        audit_json_boundary = True

    right_now_payload = read_json_optional(artifacts["right_now_json"])
    if not right_now_payload:
        raise AssertionError(f"{case['name']}: PAPER_TRADE_NOW.json was missing, unreadable, or not a JSON object")
    right_now_json_status = str(right_now_payload.get("artifact_status") or "pass")
    right_now_json_matches_source = False
    right_now_json_has_shadow_gate = False
    right_now_json_has_scorecard_gate_source = False
    right_now_json_placeholder_boundary = False
    daily_summary_operator_read_gate_issue_flags = False
    if case["name"] == "case_right_now_helper_failure":
        if right_now_json_status != "placeholder":
            raise AssertionError(f"{case['name']}: right-now helper failure should leave an explicit JSON placeholder, got {right_now_json_status!r}")
        if right_now_payload.get("run_root") != str(run_root_rel):
            raise AssertionError(f"{case['name']}: right-now JSON placeholder did not preserve the wrapper-local run_root")
        if not isinstance(right_now_payload.get("best_action"), dict) or not right_now_payload["best_action"].get("headline"):
            raise AssertionError(f"{case['name']}: right-now JSON placeholder did not preserve a best_action headline")
        quick_reads = right_now_payload.get("quick_reads")
        if not isinstance(quick_reads, list) or "OPS_HISTORY.md" not in quick_reads or str(run_root_rel / "daily_summary.txt") not in quick_reads:
            raise AssertionError(f"{case['name']}: right-now JSON placeholder did not preserve fallback quick reads")
        if "not new forward evidence" not in str(right_now_payload.get("evidence_boundary") or ""):
            raise AssertionError(f"{case['name']}: right-now JSON placeholder dropped the no-new-forward-evidence boundary")
        gate_minimums = right_now_payload.get("decision_gate_minimums")
        active_gates = right_now_payload.get("active_decision_gates")
        if not isinstance(gate_minimums, dict) or not isinstance(active_gates, dict):
            raise AssertionError(f"{case['name']}: right-now JSON placeholder did not publish scorecard-sourced decision gate metadata")
        expected_gate_minimums = {
            "source_path": "forward_evidence_scorecard.json",
            "source_loaded": True,
            "fallback_used": False,
            "anchor_displacement_min_roi_complete_settled_observations": 30,
            "phase8_promotion_review_min_roi_complete_settled_observations": 20,
            "real_money_discussion_min_total_settled_observations_with_usable_roi": 100,
            "active_min_settled": 30,
            "active_portfolio_review_settled": 100,
        }
        for field, expected in expected_gate_minimums.items():
            if gate_minimums.get(field) != expected:
                raise AssertionError(f"{case['name']}: right-now JSON placeholder decision_gate_minimums[{field!r}] drifted to {gate_minimums.get(field)!r}")
        if gate_minimums.get("cli_overrides") != {}:
            raise AssertionError(f"{case['name']}: right-now JSON placeholder should not use CLI gate overrides")
        if (
            active_gates.get("source_path") != "forward_evidence_scorecard.json"
            or active_gates.get("source_loaded") is not True
            or active_gates.get("fallback_used") is not False
            or active_gates.get("min_settled") != 30
            or active_gates.get("portfolio_review_settled") != 100
            or active_gates.get("primary_min_settled") != 30
            or active_gates.get("shadow_min_settled") != 20
            or active_gates.get("primary_portfolio_review_settled") != 100
            or active_gates.get("shadow_portfolio_review_settled") != 100
            or active_gates.get("first_read_gate_parity") is not False
            or active_gates.get("portfolio_review_gate_parity") is not True
            or active_gates.get("primary_shadow_gate_parity") is not False
            or "right-now placeholder gates are source-matched" not in str(active_gates.get("alignment_read") or "")
        ):
            raise AssertionError(f"{case['name']}: right-now JSON placeholder active_decision_gates drifted from scorecard-sourced lane-specific 30/20/100 gates")
        assert_contains(texts["right_now_txt"], "Decision-gate source: forward_evidence_scorecard.json decision_gate_minimums loaded=True", f"{case['name']} right_now_txt placeholder scorecard gate source line")
        assert_contains(texts["right_now_txt"], "Active right-now gates: primary_min_settled=30; shadow_min_settled=20; portfolio_review_settled=100", f"{case['name']} right_now_txt placeholder active right-now gate line")
        assert_contains(texts["right_now_md"], "forward_evidence_scorecard.json", f"{case['name']} right_now_md placeholder scorecard gate source reference")
        assert_contains(texts["right_now_md"], "Active right-now gates", f"{case['name']} right_now_md placeholder active right-now gate line")
        right_now_json_has_scorecard_gate_source = True
        right_now_json_placeholder_boundary = True
    else:
        if right_now_json_status == "placeholder":
            raise AssertionError(f"{case['name']}: PAPER_TRADE_NOW.json unexpectedly fell back to a placeholder")
        expected_json = rerender_right_now_json(case_root, artifacts["run_root"], case["run_date"], artifacts["settlement_audit_md"])
        actual_json = artifacts["right_now_json"].read_text(encoding="utf-8")
        if actual_json != expected_json:
            raise AssertionError(f"{case['name']}: PAPER_TRADE_NOW.json drifted from an immediate fixture-local paper_trade_now.py --format json rerender")
        right_now_json_matches_source = True
        if right_now_payload.get("run_root") != str(run_root_rel):
            raise AssertionError(f"{case['name']}: PAPER_TRADE_NOW.json did not preserve the wrapper-local run_root")
        freshness = right_now_payload.get("run_freshness")
        if isinstance(freshness, dict) and freshness.get("as_of_date") != case["run_date"]:
            raise AssertionError(f"{case['name']}: PAPER_TRADE_NOW.json did not pin run_freshness to RUN_DATE")
        if not isinstance(right_now_payload.get("best_action"), dict) or not right_now_payload["best_action"].get("headline"):
            raise AssertionError(f"{case['name']}: PAPER_TRADE_NOW.json did not preserve a best_action headline")
        if right_now_payload["best_action"].get("headline") not in texts["right_now_txt"]:
            raise AssertionError(f"{case['name']}: PAPER_TRADE_NOW.json best_action headline drifted from PAPER_TRADE_NOW.txt")
        if right_now_payload.get("settlement_audit") != "out/paper_trade_settlement_audit.md":
            raise AssertionError(f"{case['name']}: PAPER_TRADE_NOW.json did not carry the wrapper-local settlement-audit pointer")
        gate_minimums = right_now_payload.get("decision_gate_minimums")
        active_gates = right_now_payload.get("active_decision_gates")
        if not isinstance(gate_minimums, dict) or not isinstance(active_gates, dict):
            raise AssertionError(f"{case['name']}: PAPER_TRADE_NOW.json did not publish scorecard-sourced decision gate metadata")
        expected_gate_minimums = {
            "source_path": "forward_evidence_scorecard.json",
            "source_loaded": True,
            "fallback_used": False,
            "anchor_displacement_min_roi_complete_settled_observations": 30,
            "phase8_promotion_review_min_roi_complete_settled_observations": 20,
            "real_money_discussion_min_total_settled_observations_with_usable_roi": 100,
            "active_min_settled": 30,
            "active_portfolio_review_settled": 100,
        }
        for field, expected in expected_gate_minimums.items():
            if gate_minimums.get(field) != expected:
                raise AssertionError(f"{case['name']}: PAPER_TRADE_NOW.json decision_gate_minimums[{field!r}] drifted to {gate_minimums.get(field)!r}")
        if gate_minimums.get("cli_overrides") != {}:
            raise AssertionError(f"{case['name']}: PAPER_TRADE_NOW.json should not use CLI gate overrides in wrapper fixtures")
        if (
            active_gates.get("source_path") != "forward_evidence_scorecard.json"
            or active_gates.get("source_loaded") is not True
            or active_gates.get("fallback_used") is not False
            or active_gates.get("min_settled") != 30
            or active_gates.get("portfolio_review_settled") != 100
            or active_gates.get("primary_min_settled") != 30
            or active_gates.get("shadow_min_settled") != 20
            or active_gates.get("primary_portfolio_review_settled") != 100
            or active_gates.get("shadow_portfolio_review_settled") != 100
            or active_gates.get("first_read_gate_parity") is not False
            or active_gates.get("portfolio_review_gate_parity") is not True
            or active_gates.get("primary_shadow_gate_parity") is not False
            or active_gates.get("alignment_read") != "right-now action gates are source-matched to forward_evidence_scorecard.json decision_gate_minimums"
        ):
            raise AssertionError(f"{case['name']}: PAPER_TRADE_NOW.json active_decision_gates drifted from scorecard-sourced lane-specific 30/20/100 gates")
        assert_contains(texts["right_now_txt"], "Decision-gate source: forward_evidence_scorecard.json decision_gate_minimums loaded=True", f"{case['name']} right_now_txt scorecard gate source line")
        assert_contains(texts["right_now_txt"], "Active right-now gates: primary_min_settled=30; shadow_min_settled=20; portfolio_review_settled=100", f"{case['name']} right_now_txt active right-now gate line")
        assert_contains(texts["right_now_md"], "forward_evidence_scorecard.json", f"{case['name']} right_now_md scorecard gate source reference")
        assert_contains(texts["right_now_md"], "Active right-now gates", f"{case['name']} right_now_md active right-now gate line")
        right_now_json_has_scorecard_gate_source = True
        operator_read_gate = right_now_payload.get("operator_read_gate")
        if not isinstance(operator_read_gate, dict):
            raise AssertionError(f"{case['name']}: PAPER_TRADE_NOW.json did not publish operator_read_gate")
        expected_issue_flags_line = operator_issue_flags_line(operator_read_gate)
        if case["name"] != "case_daily_summary_fallback":
            assert_contains(
                daily_summary_text,
                expected_issue_flags_line,
                f"{case['name']} daily_summary operator-read-gate issue flags",
            )
            daily_summary_operator_read_gate_issue_flags = True
        if audit_status == "pass":
            right_now_json_has_shadow_gate = bool(
                right_now_payload.get("shadow_settlement_audit_promotion_gate")
                and right_now_payload.get("shadow_settlement_audit_rule_progress")
            )
            if not right_now_json_has_shadow_gate:
                raise AssertionError(f"{case['name']}: PAPER_TRADE_NOW.json dropped the shadow per-rule promotion gate or coverage payload")

    for label, needle in case["assertions"]:
        assert_contains(texts[label], needle, f"{case['name']} {label}")

    primary_pipeline = read_json_optional(artifacts["primary_pipeline_status"])
    shadow_pipeline = read_json_optional(artifacts["shadow_pipeline_status"])
    expected_primary_scanner = str(artifacts["run_root"] / "phase7_current_paper" / "live_scan.status.json")
    expected_shadow_scanner = str(artifacts["run_root"] / "phase8_shadow" / "live_scan.status.json")

    daily_first = texts["daily_summary"].splitlines()[0]
    return {
        "case": case["name"],
        "scenario": case["scenario"],
        "run_root": logical_fixture_path(artifacts["run_root"], root),
        "wrapper_args": case["wrapper_args"],
        "daily_summary": logical_fixture_path(artifacts["daily_summary"], root),
        "right_now_md": logical_fixture_path(artifacts["right_now_md"], root),
        "right_now_json": logical_fixture_path(artifacts["right_now_json"], root),
        "current_evidence_md": logical_fixture_path(artifacts["current_evidence_md"], root),
        "current_evidence_json": logical_fixture_path(artifacts["current_evidence_json"], root),
        "current_evidence_status": current_evidence_status,
        "current_evidence_boundary": current_evidence_boundary,
        "current_evidence_recommendation_context_boundary": current_evidence_recommendation_context_boundary,
        "current_evidence_rebuild_contract_boundary": current_evidence_rebuild_contract_boundary,
        "current_evidence_rebuild_contract": current_evidence_rebuild_contract,
        "right_now_json_status": right_now_json_status,
        "right_now_json_matches_source": right_now_json_matches_source,
        "right_now_json_has_shadow_gate": right_now_json_has_shadow_gate,
        "right_now_json_has_scorecard_gate_source": right_now_json_has_scorecard_gate_source,
        "right_now_json_placeholder_boundary": right_now_json_placeholder_boundary,
        "daily_summary_operator_read_gate_issue_flags": daily_summary_operator_read_gate_issue_flags,
        "ops_history_md": logical_fixture_path(artifacts["ops_history_md"], root),
        "settlement_audit_md": logical_fixture_path(artifacts["settlement_audit_md"], root),
        "settlement_audit_json": logical_fixture_path(artifacts["settlement_audit_json"], root),
        "settlement_audit_status": audit_status,
        "settlement_audit_lanes": audit_lanes,
        "settlement_audit_next_actions": audit_next_actions,
        "settlement_audit_json_boundary": audit_json_boundary,
        "primary_summary": logical_fixture_path(artifacts["primary_summary"], root),
        "logfile": logical_fixture_path(artifacts["logfile"], root),
        "daily_summary_first_line": daily_first,
        "stdout_preview": [normalize_stdout_line(line, root) for line in result.stdout.splitlines()[:6]],
        "primary_pipeline_scanner_status_path": primary_pipeline.get("scanner_status_path") if primary_pipeline else None,
        "shadow_pipeline_scanner_status_path": shadow_pipeline.get("scanner_status_path") if shadow_pipeline else None,
        "primary_pipeline_explicit_scanner_status": bool(primary_pipeline and primary_pipeline.get("scanner_status_path") == expected_primary_scanner),
        "shadow_pipeline_explicit_scanner_status": bool(shadow_pipeline and shadow_pipeline.get("scanner_status_path") == expected_shadow_scanner),
        "right_now_helper_keeps_lane_why": (
            "Primary lane why now:" in texts["right_now_md"]
            and "Shadow lane why now:" in texts["right_now_md"]
        ),
        "daily_summary_fallback_keeps_lane_why": (
            "Primary lane why now:" in texts["daily_summary"]
            and "Shadow lane why now:" in texts["daily_summary"]
        ),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_main_args(argv)
    configure_output_paths(args.out_dir.expanduser().resolve())
    scorecard_json = args.scorecard_json.expanduser().resolve()
    current_evidence_json = args.current_evidence_json.expanduser().resolve()
    scorecard_gates = read_scorecard_gate_minimums(scorecard_json)
    current_evidence_rebuild_contract = read_current_evidence_rebuild_contract(current_evidence_json)
    scorecard_artifact_guardrails = scorecard_no_artifact_guardrails(scorecard_json, current_evidence_json)
    current_evidence_artifact_guardrails = current_evidence_no_artifact_guardrails(
        scorecard_json,
        current_evidence_json,
    )

    root = args.fixture_root.expanduser().resolve() if args.fixture_root else fixture_root()
    report_md = report_md_path(root)
    report_json = report_json_path(root)
    root.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = [run_case(case, root) for case in CASES]
    row_map = {row["case"]: row for row in results}
    declared_case_names = [case["name"] for case in CASES]
    scratch = build_fixture_scratch_metadata(root)
    wrapper_source = WRAPPER.read_text(encoding="utf-8")

    checks = scorecard_artifact_guardrails + current_evidence_artifact_guardrails + [
        require(
            set(declared_case_names) == EXPECTED_CASE_NAMES
            and len(declared_case_names) == len(EXPECTED_CASE_NAMES)
            and len(results) == len(EXPECTED_CASE_NAMES)
            and set(row_map) == EXPECTED_CASE_NAMES,
            "all_wrapper_fixture_cases_rendered",
            "the wrapper validator still renders the full fixed set of twenty-four declared fixture cases, including cache-miss, missing scan-output, fallback, helper-failure, and pipeline-error branches",
        ),
        require(
            "no primary paper-basket target tracks (OP / CD) are racing today" in " ".join(row_map["case_no_target_cache_miss"]["stdout_preview"])
            and "primary paper-basket target tracks racing today: OP, CD." in " ".join(row_map["case_active_target_cache_miss"]["stdout_preview"])
            and "partial cache" in " ".join(row_map["case_partial_cache_refresh"]["stdout_preview"]),
            "cache_and_calendar_modes_stay_distinct",
            "the wrapper fixture suite still keeps no-target cache misses, active-target cache misses, and active-target partial-cache days operationally distinct",
        ),
        require(
            "bets ready" in " ".join(row_map["case_primary_settlement"]["stdout_preview"])
            and "Settlement sync complete: 1 row(s), 1 added" in " ".join(row_map["case_primary_settlement"]["stdout_preview"])
            and "signals logged, no bet" in " ".join(row_map["case_active_signals_no_bet"]["stdout_preview"])
            and "Settlement sync complete: 1 row(s), 1 added" in " ".join(row_map["case_active_signals_no_bet"]["stdout_preview"])
            and row_map["case_shadow_settlement"]["scenario"].startswith("shadow-only BET day still lands in shadow settle-first mode"),
            "settlement_and_no_bet_paths_stay_distinct",
            "the wrapper fixture suite still separates primary settle-first, shadow settle-first, and hit-found-but-NO-BET days while proving settlement sync stays in the loop",
        ),
        require(
            "WARN: status summary helper failed" in " ".join(row_map["case_missing_primary_status"]["stdout_preview"])
            and "scanner sidecar unreadable" in " ".join(row_map["case_unreadable_primary_scanner_status"]["stdout_preview"])
            and "pipeline sidecar unreadable" in " ".join(row_map["case_unreadable_primary_pipeline_status"]["stdout_preview"]),
            "artifact_degradation_stays_explicit",
            "the wrapper fixture suite still keeps missing-status, unreadable-scanner, and unreadable-pipeline degradations explicit instead of flattening them into benign empty days",
        ),
        require(
            "missing scanner output" in " ".join(row_map["case_missing_scan_output_refresh"]["stdout_preview"])
            and row_map["case_missing_scan_output_refresh"].get("primary_pipeline_explicit_scanner_status"),
            "missing_scan_output_wrapper_path_stays_explicit",
            "the real wrapper fixture suite now preserves a readable scanner-status sidecar with a missing scan-output artifact as explicit refresh-artifacts context through status summary, next steps, right-now, ops-history, and combined daily summary surfaces instead of flattening it into clean-empty wrapper output",
        ),
        require(
            row_map["case_primary_settlement"].get("primary_pipeline_explicit_scanner_status")
            and row_map["case_primary_settlement"].get("shadow_pipeline_explicit_scanner_status")
            and row_map["case_unreadable_primary_scanner_status"].get("primary_pipeline_explicit_scanner_status"),
            "wrapper_pins_explicit_scanner_sidecar_paths",
            "the wrapper now pins each lane's intended scanner-sidecar output path directly into the pipeline call and readable pipeline status sidecars, so downstream helpers do not depend on the pipeline's implicit basename default",
        ),
        require(
            all(name in row_map for name in [
                "case_right_now_md_placeholder",
                "case_lane_summary_fallback",
                "case_daily_summary_fallback",
                "case_preflight_helper_failure",
                "case_ops_history_fallback",
                "case_right_now_helper_failure",
                "case_forward_check_helper_failure",
                "case_lane_monitor_helper_failure",
                "case_next_steps_helper_failure",
            ]),
            "fallback_and_helper_failure_coverage_stays_present",
            "the wrapper fixture suite still covers markdown-mirror fallback plus preflight, ops-history, right-now, forward-check, lane-monitor, next-steps, lane-summary, and daily-summary helper-failure recovery paths",
        ),
        require(
            all(name in row_map for name in ["case_pipeline_error_refresh", "case_pipeline_logger_error_refresh"]),
            "pipeline_error_refresh_paths_stay_covered",
            "the wrapper fixture suite still covers both recommender-stage and logger-stage pipeline-error refresh branches",
        ),
        require(
            row_map["case_right_now_helper_failure"].get("right_now_helper_keeps_lane_why")
            and row_map["case_daily_summary_fallback"].get("daily_summary_fallback_keeps_lane_why"),
            "fallbacks_preserve_lane_why_lines_when_next_steps_exist",
            "the right-now helper fallback and daily-summary fallback still preserve both lanes' why-now lines whenever the saved next-steps artifacts already provide them",
        ),
        require(
            all(row.get("right_now_json_matches_source") for name, row in row_map.items() if name != "case_right_now_helper_failure")
            and all(row.get("right_now_json_has_shadow_gate") for name, row in row_map.items() if name != "case_right_now_helper_failure")
            and all(row.get("right_now_json_has_scorecard_gate_source") for row in row_map.values())
            and row_map["case_right_now_helper_failure"].get("right_now_json_status") == "placeholder"
            and row_map["case_right_now_helper_failure"].get("right_now_json_placeholder_boundary"),
            "right_now_json_payloads_match_source_or_explicit_placeholder",
            "the wrapper now requires PAPER_TRADE_NOW.json for every fixture case: normal and markdown-fallback runs must match an immediate fixture-local paper_trade_now.py --format json rerender with the settlement-audit pointer, scorecard-sourced right-now decision-gate metadata, and shadow per-rule promotion-gate fields, while right-now-helper failure must leave an explicit no-new-forward-evidence JSON placeholder that still carries the same scorecard-sourced gate metadata",
        ),
        require(
            all(
                row.get("daily_summary_operator_read_gate_issue_flags")
                for name, row in row_map.items()
                if name not in {"case_daily_summary_fallback", "case_right_now_helper_failure"}
            ),
            "daily_summary_lifts_operator_read_gate_issue_flags",
            "every full daily-wrapper fixture summary now has to lift the routed PAPER_TRADE_NOW.json operator_read_gate issue booleans into daily_summary.txt, while helper-fallback summaries remain explicit reduced fallback artifacts rather than evidence reads",
        ),
        require(
            all(row.get("current_evidence_status") in {"pass", "placeholder"} for row in row_map.values())
            and all(row.get("current_evidence_boundary") for row in row_map.values())
            and all(row.get("current_evidence_recommendation_context_boundary") for row in row_map.values()),
            "current_evidence_bridge_refreshes_or_explicitly_placeholders",
            "the wrapper now rebuilds CURRENT_EVIDENCE_SUMMARY.md/json after the right-now JSON and settlement audit refresh, with source-backed bridges preserving recommendation-context/open-row separation plus no-forward-performance / no-real-money boundaries, or leaves an explicit no-forward-performance / no-real-money placeholder instead of silently preserving a stale report bridge",
        ),
        require(
            all(row.get("current_evidence_rebuild_contract_boundary") for row in row_map.values())
            and all(
                row.get("current_evidence_rebuild_contract", {}).get("upstream_refresh_order_commands")
                == EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER
                for row in row_map.values()
            )
            and "python3 paper_trade_settlement_audit.py before python3 current_evidence_summary.py" in wrapper_source
            and "python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py" in wrapper_source,
            "current_evidence_rebuild_contract_preserved",
            "the wrapper validator now proves source-backed current-evidence bridge outputs publish the settlement-audit -> current bridge -> current bridge validator order, and wrapper bridge-failure placeholders point operators to rerun the settlement audit before rebuilding current evidence",
        ),
        require(
            scorecard_gates.get("source") == "forward_evidence_scorecard.json"
            and scorecard_gates.get("source_path") == "decision_gate_minimums"
            and scorecard_gates.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and scorecard_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and scorecard_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and scorecard_gates.get("real_money_no_baq_as_bel_required") is True
            and "no BAQ-as-BEL substitution" in scorecard_gates.get("real_money_also_requires", []),
            "daily_wrapper_preserves_scorecard_gate_boundary",
            "the wrapper validator now publishes the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite while saying fixture wrapper runs, card rerenders, bridge refreshes, clean-empty/no-target/cache-miss branches, and helper-fallback paths do not count toward those gates",
        ),
        require(
            scratch.get("fixture_root_relative") == "out/status_validation/daily_wrapper_fixture"
            and scratch.get("fixture_root_is_project_local") is True
            and scratch.get("case_roots_cleared_by_copy_fixture_project") is True,
            "fixture_scratch_metadata_published",
            "the daily-wrapper validator now publishes project-local fixture scratch metadata so parent rollups can verify case-root hygiene without parsing markdown prose",
        ),
        require(
            EVIDENCE_BOUNDARY.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE,
            "direct_validation_report_exposes_daily_wrapper_valid_scope",
            f"the direct daily-wrapper validator report now exposes exact valid_evidence_scope={VALID_EVIDENCE_SCOPE} as wrapper orchestration/fallback metadata only",
        ),
    ]

    suite_read = (
        "daily wrapper still refreshes preflight, per-lane summaries, settlement audit, ops history, right-now, CURRENT_EVIDENCE_SUMMARY, and combined daily summary together, now also pinning each lane's scanner-sidecar output path explicitly instead of relying on the pipeline's implicit `live_scan.status.json` default, "
        "while keeping cache-miss, signals-without-bet, settle-first, limited-coverage, explicit recommender/logger pipeline-error refresh, missing scan-output refresh, missing-vs-unreadable artifact recovery, placeholder, malformed-preflight, blank-text-preflight-json-fallback on both active-target and true no-target days, preflight-helper-failure, ops-history-fallback, right-now-helper-failure, forward-check-helper-failure, lane-monitor-helper-failure, and next-steps-helper-failure days operationally distinct, "
        f"with every non-fallback fixture run keeping the full routed daily-summary quick-jump bundle including settlement audit plus settlement-audit next-action/no-new-evidence lines, routed PAPER_TRADE_NOW operator_read_gate issue flags, and the routed right-now focus/timing/freshness/ops snapshot pinned to wrapper-local artifacts, every passing settlement-audit JSON preserving the machine-readable primary/shadow lane inventory plus lane next_action / next_action_reason guidance and the ledger-completeness / ROI-coverage no-new-evidence boundary, every current-evidence bridge output preserving the no-forward-performance / no-real-money evidence boundary whether it passes or placeholders while every source-backed current-evidence bridge also keeps recommendation-context/open-row separation explicit and publishes the settlement-audit -> current bridge -> current bridge validator rebuild order, every wrapper bridge-failure placeholder now pointing operators to rerun the settlement audit before rebuilding current evidence, every non-right-now-helper-failure PAPER_TRADE_NOW.json matching an immediate fixture-local paper_trade_now.py --format json rerender while carrying the wrapper-local settlement-audit pointer, scorecard-sourced right-now decision-gate metadata (forward_evidence_scorecard.json loaded, 30/20/100 active gates, no CLI overrides), and shadow per-rule promotion-gate fields, the right-now markdown fallback preserving JSON parity instead of degrading the machine-readable payload, the right-now-helper-failure branch leaving an explicit no-new-forward-evidence JSON placeholder that still carries the same scorecard-sourced gate metadata, the direct wrapper validator itself now validating malformed scorecard gates before any fixture/report artifacts, including boolean and non-positive copied-gate floors, while publishing the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as orchestration-boundary metadata, validates malformed current-evidence rebuild contracts before fixture/report artifacts and publishes the bridge-owned current_evidence_summary.json rebuild_validation_contract read as daily-wrapper boundary metadata only, project-local fixture scratch metadata for daily-wrapper case-root hygiene, and now exposes exact valid_evidence_scope={VALID_EVIDENCE_SCOPE} as wrapper orchestration/fallback metadata only; the daily-summary fallback still keeps its reduced preflight-plus-summary quick-jump contract honest while now also preserving both lane recent-run context plus why-now lines when the saved next-steps artifacts provide them, the right-now helper fallback now also preserving both lanes' routed next-step pointers plus their recent-run context and why-now lines when the saved next-steps artifacts provide them, the top-level right-now cross-links pinned to wrapper-local OPS_HISTORY and PAPER_TRADE_NOW surfaces, the per-lane markdown fallback mirrors pinned back to their text artifacts, and the validator now says plainly that this is the other leaf source-of-truth wrapper report whose inherited wrapper-guardrail inventory broader operator/project sweeps should preserve rather than flatten"
    )

    logical_root = display_path(logical_fixture_root(root))
    mode = execution_mode(root)

    lines = [
        "# Run Daily Portfolio Observation Validation",
        "",
        f"This report validates `run_daily_portfolio_observation.sh` end to end inside isolated fixture project roots while publishing normalized logical fixture-path references under `{logical_root}` and the direct validator readout under the standard `out/status_validation/run_daily_portfolio_observation/` path.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Fixture root (logical): `{logical_root}`",
        f"- Report path: `{display_path(report_md)}`",
        "",
        "## Cases",
        "",
        "| Case | Scenario | Daily Summary |",
        "|---|---|---|",
    ]
    for row in results:
        lines.append(f"| `{row['case']}` | {row['scenario']} | `{row['daily_summary']}` |")

    lines.extend([
        "",
        "## Rollup Checks",
        "",
    ])
    for check in checks:
        lines.append(f"- PASS `{check['check']}` — {check['detail']}")

    lines.extend([
        "",
        "## Current Read",
        "",
        f"- Suite read: {suite_read}",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
        f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
        f"- valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
        "- Not new forward evidence: true",
        "- Not settled ROI evidence: true",
        "- Not live profitability evidence: true",
        "- Not promotion readiness evidence: true",
        "- Not real-money evidence: true",
        "",
        "## Decision-Gate Source",
        "",
        f"- Source: `{scorecard_gates['source']}` `{scorecard_gates['source_path']}`.",
        f"- Anchor displacement: `{scorecard_gates['anchor_displacement_min_roi_complete_settled_observations']}` ROI-complete same-candidate paper observations.",
        f"- Phase 8 promotion review: `{scorecard_gates['phase8_promotion_review_min_roi_complete_settled_observations']}` ROI-complete shadow observations.",
        f"- Real-money discussion: `{scorecard_gates['real_money_discussion_min_total_settled_observations_with_usable_roi']}` total settled observations with usable ROI.",
        f"- Real-money prerequisites: {'; '.join(scorecard_gates['real_money_also_requires'])}.",
        f"- Boundary: {scorecard_gates['evidence_boundary']}.",
        "",
        "## Current Evidence Rebuild Contract",
        "",
        f"- Source: `{current_evidence_rebuild_contract['source']}` `{current_evidence_rebuild_contract['source_path']}`.",
        f"- Order: `{'` -> `'.join(current_evidence_rebuild_contract['upstream_refresh_order_commands'])}`.",
        f"- Boundary: {current_evidence_rebuild_contract['evidence_boundary']}.",
        "",
        "## Fixture Scratch",
        "",
        f"- Fixture scratch metadata: `{scratch['fixture_root_relative']}` is project-local and each case root is cleared by `copy_fixture_project` before setup.",
        f"- Boundary: {scratch['evidence_boundary']}.",
        "",
        "## Validation result",
        "",
        f"- Fixture root (logical): `{logical_root}`",
        f"- Execution mode: `{mode}`",
        "- Direct validator report path: `out/status_validation/run_daily_portfolio_observation/`",
        "- The real daily wrapper still refreshes the preflight note, per-lane summaries, settlement audit, rolling ops history, top-level right-now card, and combined daily summary together.",
        "- Every non-fallback fixture run now fails if `daily_summary.txt` drops any part of its routed quick-jump bundle (`PAPER_TRADE_NOW.md`, `OPS_HISTORY.md`, the settlement-audit artifact, the source-resolved preflight note surface, both lane `summary.txt` reads, both lane detail quick jumps, or `Artifacts root`) or if it loses the routed right-now snapshot header plus any current focus / timing / ops-bucket line that is still present in that run's wrapper-local `PAPER_TRADE_NOW.md`, the combined daily-summary fallback now fails if its reduced placeholder contract drops that routed preflight note surface, either lane `summary.txt`, either lane recent-run context line when the saved next-steps artifacts provide one, either lane why-now line when the saved next-steps artifacts provide one, or `Artifacts root`, the settlement-audit markdown artifact has to render the no-new-evidence audit boundary, the settlement-audit JSON artifact has to preserve the machine-readable primary/shadow lane inventory, lane next_action / next_action_reason guidance, and the ledger-completeness / ROI-coverage audit-only boundary whenever it passes, every non-fallback daily summary has to lift those settlement-audit next-action/no-new-evidence lines, `PAPER_TRADE_NOW.md` still has to reference wrapper-local `OPS_HISTORY.md` in either its normal quick-read list or its markdown-fallback mirror, a right-now helper fallback still has to keep both lanes' routed next-step pointers plus either lane's recent-run context and why-now line when the saved next-steps artifacts provide one, either lane's forward-check / lane-monitor / next-steps markdown fallbacks still have to point back to their corresponding text artifacts, and a lane-summary fallback still has to preserve the already-written base summary for either lane.",
        "- Every non-fallback combined daily summary must now carry the settlement-audit next-action/no-new-evidence lines from the wrapper-local audit JSON plus the operator-read-gate issue flags from the wrapper-local `PAPER_TRADE_NOW.json`, so collect/repair/settle guidance and API/scanner/stale-cache issue context cannot disappear between the audit, top card, and daily handoff.",
        "- `PAPER_TRADE_NOW.json` is now required in every wrapper fixture: normal and markdown-fallback runs must match an immediate fixture-local `paper_trade_now.py --format json` rerender and carry the wrapper-local settlement-audit pointer, scorecard-sourced decision-gate minimums, active right-now 30/20/100 gates, no CLI gate overrides, and shadow per-rule promotion-gate fields, while right-now-helper failure must leave an explicit no-new-forward-evidence JSON placeholder that still carries those same scorecard-sourced gates.",
        "- `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` are now rebuilt by the wrapper after `PAPER_TRADE_NOW.json` and `out/paper_trade_settlement_audit.json`; every fixture must either publish a source-backed bridge with recommendation-state context kept separate from open-row wording plus no-new-forward-evidence and no-real-money flags plus the settlement-audit -> current bridge -> current bridge validator rebuild order, or an explicit placeholder with the same no-forward/no-real-money boundary and settlement-audit-first recovery route.",
        "- The isolated fixture runs now prove twenty-four important wrapper reads: no-target cache misses, active-target cache misses that must rerun live, active-target hit-found but NO BET days, primary settle-first days, shadow settle-first days on shadow-only race cards, active-target partial-cache refresh days, active-target readable scanner-status sidecar plus missing scan-output artifact days that must refresh instead of being treated as clean-empty, active-target recommender-stage pipeline-error days that must refresh instead of falling through to normal observation guidance, active-target logger-stage pipeline-error days that must also refresh instead of falling through to normal observation guidance, missing-primary-status days that degrade to explicit placeholders, unreadable-primary-scanner days that stay explicit instead of drifting into ordinary zero-hit messaging, unreadable-primary-pipeline days that stay explicit instead of collapsing into a scanner-only read, markdown-only mirror failures that fall back to placeholder `.md` artifacts once the text card already exists, lane-summary enrichment failures that keep the base status line instead of destroying it late, combined daily-summary failures that fall back to a placeholder top-level summary once the core artifacts already exist while still keeping both lane sections readable plus their preserved lane why-now context, malformed preflight JSON that keeps the wrapper alive while the rolling ops surface marks the calendar context unreadable, blank `preflight_note.txt` on an active-target day that still preserves the saved JSON note plus routed `preflight_note.json` quick jumps through the top card and combined summary, blank `preflight_note.txt` on a true no-target day that still preserves the saved JSON stand-down note plus routed `preflight_note.json` quick jumps through the top card and combined summary, full preflight-helper failures that degrade to explicit placeholder note artifacts instead of aborting the run, late ops-history helper failures that write placeholder history artifacts instead of killing the wrapper after both lanes already finished, the settlement audit artifact refreshes before late top-level summaries, right-now helper failures that fall back to a placeholder text card plus markdown mirror while still pointing at both lanes' next-step artifacts and preserving both lanes' recent-run context plus why-now lines instead of aborting late, forward-check helper failures that fall back to placeholder forward-check artifacts instead of killing an otherwise usable lane once settlement sync already succeeded, lane-monitor helper failures that fall back to placeholder monitor artifacts instead of killing an otherwise usable lane, and next-steps helper failures that now fall back to placeholder next-step text plus markdown mirror artifacts instead of aborting the lane after the base artifacts already exist.",
        "- This keeps the shell entrypoint aligned with the helper-level validators even when the shadow lane, not the primary lane, owns the top operator action, when active targets were on the calendar but the cache-only run missed the day cache and must be rerun live, when active targets were on the calendar and the lane found hits but nothing reached BET, when a readable scanner-status sidecar reports no_qualifiers but the scan-output artifact is missing, when an active primary lane hit a recommender-stage pipeline_error and must be refreshed instead of treated like normal observation noise, when an active primary lane hit a logger-stage pipeline_error and must be refreshed instead of treated like a normal logged-bet outcome, when ops history now surfaces those as explicit recommender/logger failure rows instead of generic operational issues, when one lane loses its status sidecars, when the primary pipeline sidecar still parses but its scanner sidecar is unreadable, when a markdown mirror helper fails after the honest text artifact was already written while the JSON payload stays source-layer current, when the full right-now helper fails after ops history already succeeded, when the forward-check helper fails after lane status and settlement sync already succeeded, when the lane-monitor helper fails after forward-check text already exists, when the next-steps helper fails after the base lane artifacts already exist, when the lane-summary enrichment step breaks after the base summary already exists, when the preflight helper itself fails before writing either note artifact, when the preflight JSON is malformed while the plain-text note still exists, when the plain-text preflight note exists but is blank on either a true no-target or active-target day while the saved JSON note still carries the real calendar context, when the ops-history helper breaks after the run folders already exist, or when the combined-summary helper fails after the core daily artifacts are already on disk.",
        "",
    ])

    payload = {
        "suite_status": "pass",
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "total_fixture_scenarios": len(results),
        "results": results,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "child_check_count": len(checks),
        "child_checks": checks,
        "summary": {
            "scenario_count": len(results),
            "suite_read": suite_read,
        },
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "current_evidence_rebuild_validation_contract_read": current_evidence_rebuild_contract,
        "scratch": scratch,
        "fixture_root": logical_root,
        "execution_mode": mode,
        "path_normalization": "logical_fixture_root",
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "fixture_root": logical_root,
            "report_path": display_path(report_md),
        },
    }

    for legacy in (
        logical_fixture_root(root) / "daily_wrapper_fixture_validation.md",
        logical_fixture_root(root) / "daily_wrapper_fixture_validation.json",
        root / "daily_wrapper_fixture_validation.md",
        root / "daily_wrapper_fixture_validation.json",
    ):
        legacy.unlink(missing_ok=True)

    write_text(report_md, "\n".join(lines) + "\n")
    write_json(report_json, payload)

    print(f"Wrote {report_md}")
    print(f"Wrote {report_json}")
    for row in results:
        print(f"PASS {row['case']}: {row['daily_summary']}")
    print("PASS run_daily_portfolio_observation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
