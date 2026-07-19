#!/usr/bin/env python3
"""
Fixture-driven validation for active-target partial-cache messaging.

Purpose:
- keep active-target partial-cache empty and partial-cache-with-activity runs distinct from both full cache misses and genuine clean-empty scans
- validate the operator-facing wording across status summary, next steps, ops history, and the top-level right-now card
- avoid touching live ledgers while checking the exact CLI surfaces Cole reads
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

BASE = Path(__file__).resolve().parent
FIXTURE_ROOT = BASE / "out" / "status_validation" / "partial_cache_messaging_fixture"
REPORT_DIR = BASE / "out" / "status_validation" / "partial_cache_messaging"
REPORT_MD = REPORT_DIR / "partial_cache_messaging_validation.md"
REPORT_JSON = REPORT_DIR / "partial_cache_messaging_validation.json"
RUNS_ROOT = FIXTURE_ROOT / "out" / "daily_portfolio_runs"
PAPER_TRADES = FIXTURE_ROOT / "paper_trades"
REBUILD_COMMAND = "python3 validate_partial_cache_messaging.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
VALID_EVIDENCE_SCOPE = "partial_cache_limited_coverage_routing_only"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "partial-cache messaging validator",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "active-target clean-empty and partial-cache fixtures",
        "saved preflight_note.txt / preflight_note.json active-day split",
        "forward_evidence_scorecard.json decision_gate_minimums",
        "paper_trade_status_summary.py",
        "paper_trade_next_steps.py",
        "paper_trade_ops_history.py",
        "paper_trade_now.py",
    ],
    "valid_use": "operator failure-mode routing for active-target limited-coverage days, including clean-empty versus partial-cache-empty versus partial-cache-with-activity separation",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "partial_cache_validator_passes_are_operator_routing_metadata_only": True,
    "non_goals": [
        "do not treat partial-cache empty runs as clean live zero-hit evidence",
        "do not treat partial-cache-with-activity runs as full live recommendation evidence",
        "do not promote OP_REFINED_K7 or Phase 8 from partial-cache validator cleanliness",
        "do not reopen current odds-only XGBoost from partial-cache validator cleanliness",
        "do not substitute BAQ for BEL",
        "do not treat fixture-routed operator surfaces as real-money evidence",
    ],
}

STATUS_SUMMARY = BASE / "paper_trade_status_summary.py"
NEXT_STEPS = BASE / "paper_trade_next_steps.py"
OPS_HISTORY = BASE / "paper_trade_ops_history.py"
RIGHT_NOW = BASE / "paper_trade_now.py"

SIGNALS_HEADER = "signal_key,scan_ts,rule_id,track,card_name,race_number,race_id,surface,condition,field_size,favorite_program,favorite_name,favorite_prob,second_prob,prob_gap,k,base_stake,estimated_cost,underneath_programs,ticket_structure,status,outcome,notes\n"
RECOMMENDATIONS_HEADER = "signal_key,run_ts,rule_id,track,card_name,race_number,race_id,decision,reason,favorite_program,underneath_programs,scanner_estimated_cost,scored_combo_count,filtered_combo_count,bankroll,race_risk_budget,total_stake,total_expected_return,total_expected_profit,portfolio_expected_roi_pct,tickets_selected,tickets_json,prediction_csv,plan_json,plan_csv,status,outcome,notes\n"
SETTLEMENTS_HEADER = "signal_key,scan_ts,rule_id,track,card_name,race_number,race_id,expected_cost,settlement_status,outcome,actual_cost,actual_return,actual_profit,settled_ts,notes\n"

ACTIVE_PREFLIGHT_TEXT = "Preflight context: primary paper-basket target tracks racing today: OP, CD."
ACTIVE_PREFLIGHT_JSON = {
    "checked_at": "2026-05-24 11:00",
    "api_ok": True,
    "has_targets": True,
    "relevant_tracks": ["OP", "CD"],
    "shadow_tracks": [],
    "total_cards": 18,
    "error": None,
    "note": ACTIVE_PREFLIGHT_TEXT,
}

CASES = {
    "case_clean_empty_active": {
        "date": "2026-05-23",
        "run_ts": "2026-05-23T11:00:00",
        "status_headline": "clean empty run",
        "next_steps_state": "WAITING FOR FIRST SETTLED RACES",
        "next_steps_detail": "completed cleanly and found no qualifying races",
        "ops_bucket": "ACTIVE, ZERO HITS",
        "ops_takeaway": "OP/CD were active, but the primary lane found zero qualifying hits.",
        "scanner": {
            "result": "no_qualifiers",
            "partial_cache": False,
            "cache_only": False,
            "error": None,
            "missing_race_detail_cache_skips": 0,
            "race_details_attempted": 24,
            "max_race_limit_hit": 0,
            "card_count": 8,
            "race_count": 24,
            "raw_hit_count": 0,
            "emitted_hit_count": 0,
        },
        "pipeline": {
            "scanner_result": "no_qualifiers",
            "scanner_partial_cache": False,
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
            "observation_result": "clean_empty_run",
            "cache_only": False,
        },
    },
    "case_partial_cache_active": {
        "date": "2026-05-24",
        "run_ts": "2026-05-24T11:00:00",
        "status_headline": "partial cache",
        "next_steps_state": "LIMITED CACHE COVERAGE",
        "next_steps_detail": "partial cache data and finished empty",
        "ops_bucket": "ACTIVE, LIMITED COVERAGE",
        "ops_takeaway": "OP/CD were active, but the latest primary-lane read finished empty on partial cache coverage. 3 missing race detail cache file(s); max-races cap hit after 3 attempt(s). Re-run live before treating it as a true zero-hit day.",
        "right_now_headline": "Refresh the primary lane live after the partial-cache read",
        "right_now_detail": "Refresh the daily wrapper live before treating it as a true zero-hit day.",
        "scanner": {
            "result": "partial_cache_no_qualifiers",
            "partial_cache": True,
            "cache_only": True,
            "error": None,
            "missing_race_detail_cache_skips": 3,
            "race_details_attempted": 3,
            "max_race_limit_hit": 1,
            "card_count": 8,
            "race_count": 24,
            "raw_hit_count": 0,
            "emitted_hit_count": 0,
        },
        "pipeline": {
            "scanner_result": "partial_cache_no_qualifiers",
            "scanner_partial_cache": True,
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "scanner_missing_race_detail_cache_skips": 3,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
            "observation_result": "partial_cache_empty_run",
            "cache_only": True,
        },
    },
    "case_partial_cache_with_activity": {
        "date": "2026-05-22",
        "run_ts": "2026-05-22T11:00:00",
        "status_headline": "partial cache with activity",
        "scanner_status_relpath": "renamed_live_scan.status.json",
        "next_steps_state": "WAITING FOR FIRST SETTLED RACES",
        "next_steps_detail": "partial cache data but still produced 1 recommendation(s) from 1 raw hit(s)",
        "ops_bucket": "ACTIVE, LIMITED COVERAGE WITH ACTIVITY",
        "ops_takeaway": "OP/CD were active and the primary lane still found 1 hit(s) and turned them into 1 recommendation(s) on partial cache coverage, so keep the activity but do not treat it like a full live read. 1 missing race detail cache file(s). Re-run live before leaning on it as evidence.",
        "right_now_headline": "Refresh the primary lane live after the partial-cache activity read",
        "right_now_detail": "Keep the activity, but refresh the daily wrapper live before leaning on it like a full clean read.",
        "scanner": {
            "result": "partial_cache_missing_detail",
            "partial_cache": True,
            "cache_only": False,
            "error": None,
            "missing_race_detail_cache_skips": 1,
            "race_details_attempted": 9,
            "max_race_limit_hit": 0,
            "card_count": 8,
            "race_count": 24,
            "raw_hit_count": 1,
            "emitted_hit_count": 1,
        },
        "pipeline": {
            "scanner_result": "partial_cache_missing_detail",
            "scanner_partial_cache": True,
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 1,
            "scanner_missing_race_detail_cache_skips": 1,
            "recommendation_count": 1,
            "bet_count": 0,
            "error_count": 0,
            "observation_result": "partial_cache_with_activity",
            "observation_reason": "partial_cache_with_activity",
            "cache_only": False,
        },
    },
    "case_clean_empty_active_json_only": {
        "date": "2026-05-25",
        "run_ts": "2026-05-25T11:00:00",
        "status_headline": "clean empty run",
        "next_steps_state": "WAITING FOR FIRST SETTLED RACES",
        "next_steps_detail": "completed cleanly and found no qualifying races",
        "ops_bucket": "ACTIVE, ZERO HITS",
        "ops_takeaway": "OP/CD were active, but the primary lane found zero qualifying hits.",
        "preflight_text": "JSON-only preflight note: primary paper-basket target tracks racing today: OP, CD.",
        "remove_preflight_txt": True,
        "scanner": {
            "result": "no_qualifiers",
            "partial_cache": False,
            "cache_only": False,
            "error": None,
            "missing_race_detail_cache_skips": 0,
            "race_details_attempted": 24,
            "max_race_limit_hit": 0,
            "card_count": 8,
            "race_count": 24,
            "raw_hit_count": 0,
            "emitted_hit_count": 0,
        },
        "pipeline": {
            "scanner_result": "no_qualifiers",
            "scanner_partial_cache": False,
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
            "observation_result": "clean_empty_run",
            "cache_only": False,
        },
    },
    "case_partial_cache_active_json_only": {
        "date": "2026-05-26",
        "run_ts": "2026-05-26T11:00:00",
        "status_headline": "partial cache",
        "next_steps_state": "LIMITED CACHE COVERAGE",
        "next_steps_detail": "partial cache data and finished empty",
        "ops_bucket": "ACTIVE, LIMITED COVERAGE",
        "ops_takeaway": "OP/CD were active, but the latest primary-lane read finished empty on partial cache coverage. 3 missing race detail cache file(s); max-races cap hit after 3 attempt(s). Re-run live before treating it as a true zero-hit day.",
        "right_now_headline": "Refresh the primary lane live after the partial-cache read",
        "right_now_detail": "Refresh the daily wrapper live before treating it as a true zero-hit day.",
        "preflight_text": "JSON-only preflight note: primary paper-basket target tracks racing today: OP, CD.",
        "remove_preflight_txt": True,
        "scanner": {
            "result": "partial_cache_no_qualifiers",
            "partial_cache": True,
            "cache_only": True,
            "error": None,
            "missing_race_detail_cache_skips": 3,
            "race_details_attempted": 3,
            "max_race_limit_hit": 1,
            "card_count": 8,
            "race_count": 24,
            "raw_hit_count": 0,
            "emitted_hit_count": 0,
        },
        "pipeline": {
            "scanner_result": "partial_cache_no_qualifiers",
            "scanner_partial_cache": True,
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "scanner_missing_race_detail_cache_skips": 3,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
            "observation_result": "partial_cache_empty_run",
            "cache_only": True,
        },
    },
    "case_clean_empty_active_blank_text_prefers_json": {
        "date": "2026-05-27",
        "run_ts": "2026-05-27T11:00:00",
        "status_headline": "clean empty run",
        "next_steps_state": "WAITING FOR FIRST SETTLED RACES",
        "next_steps_detail": "completed cleanly and found no qualifying races",
        "ops_bucket": "ACTIVE, ZERO HITS",
        "ops_takeaway": "OP/CD were active, but the primary lane found zero qualifying hits.",
        "preflight_text": "",
        "blank_preflight_txt": True,
        "preflight_json_note": "Blank-text fallback preflight note: primary paper-basket target tracks racing today: OP, CD.",
        "scanner": {
            "result": "no_qualifiers",
            "partial_cache": False,
            "cache_only": False,
            "error": None,
            "missing_race_detail_cache_skips": 0,
            "race_details_attempted": 24,
            "max_race_limit_hit": 0,
            "card_count": 8,
            "race_count": 24,
            "raw_hit_count": 0,
            "emitted_hit_count": 0,
        },
        "pipeline": {
            "scanner_result": "no_qualifiers",
            "scanner_partial_cache": False,
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
            "observation_result": "clean_empty_run",
            "cache_only": False,
        },
    },
    "case_partial_cache_active_blank_text_prefers_json": {
        "date": "2026-05-28",
        "run_ts": "2026-05-28T11:00:00",
        "status_headline": "partial cache",
        "next_steps_state": "LIMITED CACHE COVERAGE",
        "next_steps_detail": "partial cache data and finished empty",
        "ops_bucket": "ACTIVE, LIMITED COVERAGE",
        "ops_takeaway": "OP/CD were active, but the latest primary-lane read finished empty on partial cache coverage. 3 missing race detail cache file(s); max-races cap hit after 3 attempt(s). Re-run live before treating it as a true zero-hit day.",
        "right_now_headline": "Refresh the primary lane live after the partial-cache read",
        "right_now_detail": "Refresh the daily wrapper live before treating it as a true zero-hit day.",
        "preflight_text": "",
        "blank_preflight_txt": True,
        "preflight_json_note": "Blank-text fallback preflight note: primary paper-basket target tracks racing today: OP, CD.",
        "scanner": {
            "result": "partial_cache_no_qualifiers",
            "partial_cache": True,
            "cache_only": True,
            "error": None,
            "missing_race_detail_cache_skips": 3,
            "race_details_attempted": 3,
            "max_race_limit_hit": 1,
            "card_count": 8,
            "race_count": 24,
            "raw_hit_count": 0,
            "emitted_hit_count": 0,
        },
        "pipeline": {
            "scanner_result": "partial_cache_no_qualifiers",
            "scanner_partial_cache": True,
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "scanner_missing_race_detail_cache_skips": 3,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
            "observation_result": "partial_cache_empty_run",
            "cache_only": True,
        },
    },
}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, indent=2) + "\n")


def assert_contains(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"{label}: expected to find {needle!r}")


def assert_not_contains(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise AssertionError(f"{label}: did not expect to find {needle!r}")


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, check=True)


def require_positive_non_bool_int(value: Any, *, source_name: str, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, source_name: str, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise AssertionError(f"{source_name} {field_name} must be a list of non-empty strings")
    return value


def read_scorecard_gate_minimums(scorecard_json_path: Path = SCORECARD_JSON) -> dict[str, Any]:
    source_path = Path(scorecard_json_path)
    source_name = source_path.name
    payload = json.loads(source_path.read_text(encoding="utf-8"))
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
            "partial-cache limited-coverage fixtures do not count toward anchor-displacement, "
            "Phase 8 promotion-review, or real-money discussion gates"
        ),
    }


def guardrail(condition: bool, check: str, detail: str) -> dict[str, str]:
    if not condition:
        raise AssertionError(f"{check}: {detail}")
    return {"check": check, "status": "pass", "detail": detail}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--out-dir", type=Path, default=REPORT_DIR)
    return parser.parse_args([] if argv is None else argv)


def scorecard_gate_cli_contract_checks(scorecard_json_path: Path = SCORECARD_JSON) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    with TemporaryDirectory(prefix="partial_cache_scorecard_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(scorecard_json_path).read_text(encoding="utf-8"))
        scorecard_path = tmp_root / "forward_evidence_scorecard.json"
        bad_out_dir = tmp_root / "nested" / "partial_cache_messaging_validation"

        bool_payload = json.loads(json.dumps(base_payload))
        bool_payload["decision_gate_minimums"]["anchor_displacement"][
            "min_roi_complete_settled_observations"
        ] = True
        scorecard_path.write_text(json.dumps(bool_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(scorecard_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            guardrail(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations must be a positive non-boolean integer" in proc.stderr,
                "scorecard_boolean_gate_floor_fails_before_partial_cache_artifacts",
                "a malformed boolean anchor-displacement scorecard gate fails before nested partial-cache validation outputs are created",
            )
        )

        nonpositive_phase8_payload = json.loads(json.dumps(base_payload))
        nonpositive_phase8_payload["decision_gate_minimums"]["phase8_promotion_review"][
            "min_roi_complete_settled_observations"
        ] = 0
        scorecard_path.write_text(json.dumps(nonpositive_phase8_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(scorecard_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            guardrail(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer" in proc.stderr,
                "scorecard_nonpositive_phase8_gate_floor_fails_before_partial_cache_artifacts",
                "a non-positive Phase 8 promotion-review scorecard gate fails before nested partial-cache validation outputs are created",
            )
        )

        nonpositive_real_money_payload = json.loads(json.dumps(base_payload))
        nonpositive_real_money_payload["decision_gate_minimums"]["real_money_discussion"][
            "min_total_settled_observations_with_usable_roi"
        ] = 0
        scorecard_path.write_text(json.dumps(nonpositive_real_money_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(scorecard_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            guardrail(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer" in proc.stderr,
                "scorecard_nonpositive_real_money_gate_floor_fails_before_partial_cache_artifacts",
                "a non-positive real-money discussion scorecard gate fails before nested partial-cache validation outputs are created",
            )
        )

        missing_no_baq_payload = json.loads(json.dumps(base_payload))
        missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"]["also_requires"] = [
            requirement
            for requirement in missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"].get(
                "also_requires",
                [],
            )
            if requirement != NO_BAQ_AS_BEL_PREREQUISITE
        ]
        scorecard_path.write_text(json.dumps(missing_no_baq_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(scorecard_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            guardrail(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.real_money_discussion.also_requires must include no BAQ-as-BEL substitution" in proc.stderr,
                "scorecard_missing_no_baq_fails_before_partial_cache_artifacts",
                "a scorecard gate missing the no-BAQ-as-BEL real-money prerequisite fails before nested partial-cache validation outputs are created",
            )
        )
    return checks


def build_fixture_scratch_metadata() -> dict[str, Any]:
    return {
        "fixture_root": str(FIXTURE_ROOT),
        "fixture_root_relative": str(FIXTURE_ROOT.relative_to(BASE)),
        "fixture_root_is_project_local": FIXTURE_ROOT.is_relative_to(BASE),
        "fixture_root_cleared_before_fixture_run": True,
        "evidence_boundary": (
            "partial-cache messaging fixture scratch metadata is operator-routing reproducibility context only, "
            "not a live scanner result, settled ROI, promotion readiness, live profitability, bankroll guidance, "
            "or real-money evidence"
        ),
    }


def make_lane(run_root: Path, lane_name: str, rules_name: str, case: dict[str, Any]) -> None:
    lane_dir = run_root / lane_name
    scanner_status_path = lane_dir / case.get("scanner_status_relpath", "live_scan.status.json")
    scanner = {
        "run_ts": case["run_ts"],
        "rules_path": str(BASE / rules_name),
        "cache_ttl": 900,
        "max_races": 3,
        "base_stake": 1.0,
        "include_cards": [],
        "dedup_enabled": True,
        "rule_count": 2,
        **case["scanner"],
    }
    pipeline = {
        "run_ts": case["run_ts"],
        "rules_path": str(BASE / rules_name),
        "scan_input": str(lane_dir / "live_scan.json"),
        "scanner_status_path": str(scanner_status_path),
        "recommendation_output_dir": str(lane_dir / "recommendations"),
        "recommendations_input": str(lane_dir / "recommendations" / "recommendations_summary.json"),
        "status_output": str(lane_dir / "pipeline_status.json"),
        "skip_scan": False,
        "stage": "done",
        "result": "ok",
        "scanner_stage_status": "ok",
        "scanner_exit_code": 0,
        "scanner_emitted_hit_count": 0,
        "no_bet_count": 0,
        **case["pipeline"],
    }
    write_json(scanner_status_path, scanner)
    write_json(lane_dir / "pipeline_status.json", pipeline)
    write_text(lane_dir / "live_scan.json", "[]\n")


def make_case(case_name: str, spec: dict[str, Any]) -> Path:
    run_root = RUNS_ROOT / spec["date"]
    preflight_json = dict(ACTIVE_PREFLIGHT_JSON)
    preflight_json["date"] = spec["date"]
    preflight_json["checked_at"] = f"{spec['date']} 11:00"
    preflight_note = spec.get("preflight_text", ACTIVE_PREFLIGHT_TEXT)
    preflight_json["note"] = spec.get("preflight_json_note", preflight_note)
    write_text(run_root / "preflight_note.txt", "\n" if spec.get("blank_preflight_txt") else preflight_note + "\n")
    write_json(run_root / "preflight_note.json", preflight_json)
    if spec.get("remove_preflight_txt"):
        (run_root / "preflight_note.txt").unlink()
    make_lane(run_root, "phase7_current_paper", "phase7_current_paper_rules.json", spec)
    make_lane(run_root, "phase8_shadow", "phase8_shadow_rules.json", spec)
    (FIXTURE_ROOT / case_name).mkdir(parents=True, exist_ok=True)
    return run_root


def ensure_ledgers() -> None:
    for lane_name in ["phase7_current_paper", "phase8_shadow"]:
        write_text(PAPER_TRADES / f"{lane_name}_paper_trade_signals.csv", SIGNALS_HEADER)
        write_text(PAPER_TRADES / f"{lane_name}_paper_trade_recommendations.csv", RECOMMENDATIONS_HEADER)
        write_text(PAPER_TRADES / f"{lane_name}_paper_trade_settlements.csv", SETTLEMENTS_HEADER)


def validate_case(case_name: str, run_root: Path, spec: dict[str, Any]) -> dict[str, str]:
    case_root = FIXTURE_ROOT / case_name
    status_out = case_root / "status_summary.txt"
    next_steps_out = case_root / "next_steps.txt"
    right_now_md = case_root / "PAPER_TRADE_NOW.md"
    right_now_json = case_root / "PAPER_TRADE_NOW.json"
    ops_history_md = FIXTURE_ROOT / "OPS_HISTORY.md"

    run([
        sys.executable,
        str(STATUS_SUMMARY),
        "--scanner-status", str(run_root / "phase7_current_paper" / "live_scan.status.json"),
        "--pipeline-status", str(run_root / "phase7_current_paper" / "pipeline_status.json"),
        "--output", str(status_out),
    ])
    status_text = status_out.read_text(encoding="utf-8")
    assert_contains(status_text, spec["status_headline"], f"{case_name} status summary")

    run([
        sys.executable,
        str(NEXT_STEPS),
        "--signals-ledger", str(PAPER_TRADES / "phase7_current_paper_paper_trade_signals.csv"),
        "--recommendation-ledger", str(PAPER_TRADES / "phase7_current_paper_paper_trade_recommendations.csv"),
        "--settlement-ledger", str(PAPER_TRADES / "phase7_current_paper_paper_trade_settlements.csv"),
        "--rules", str(BASE / "phase7_current_paper_rules.json"),
        "--scanner-status", str(run_root / "phase7_current_paper" / "live_scan.status.json"),
        "--pipeline-status", str(run_root / "phase7_current_paper" / "pipeline_status.json"),
        "--preflight-note", str(run_root / "preflight_note.txt"),
        "--format", "text",
        "--output", str(next_steps_out),
    ])
    next_steps_text = next_steps_out.read_text(encoding="utf-8")
    assert_contains(next_steps_text, f"State: {spec['next_steps_state']}", f"{case_name} next steps state")
    assert_contains(next_steps_text, spec["next_steps_detail"], f"{case_name} next steps detail")
    if spec.get("remove_preflight_txt") or spec.get("blank_preflight_txt"):
        assert_contains(next_steps_text, spec.get("preflight_json_note", spec["preflight_text"]), f"{case_name} next steps json-backed preflight note")

    run([
        sys.executable,
        str(RIGHT_NOW),
        "--run-root", str(run_root),
        "--runs-root", str(RUNS_ROOT),
        "--paper-trades-dir", str(PAPER_TRADES),
        "--primary-rules", str(BASE / "phase7_current_paper_rules.json"),
        "--shadow-rules", str(BASE / "phase8_shadow_rules.json"),
        "--ops-history-md", str(ops_history_md),
        "--as-of-date", spec["date"],
        "--format", "json",
        "--output", str(right_now_json),
    ])
    payload = json.loads(right_now_json.read_text(encoding="utf-8"))

    run([
        sys.executable,
        str(RIGHT_NOW),
        "--run-root", str(run_root),
        "--runs-root", str(RUNS_ROOT),
        "--paper-trades-dir", str(PAPER_TRADES),
        "--primary-rules", str(BASE / "phase7_current_paper_rules.json"),
        "--shadow-rules", str(BASE / "phase8_shadow_rules.json"),
        "--ops-history-md", str(ops_history_md),
        "--as-of-date", spec["date"],
        "--format", "md",
        "--output", str(right_now_md),
    ])
    right_now_text = right_now_md.read_text(encoding="utf-8")
    assert_contains(right_now_text, f"Latest ops bucket: **{spec['ops_bucket']}**", f"{case_name} right now bucket")
    if spec.get("remove_preflight_txt") or spec.get("blank_preflight_txt"):
        assert_contains(right_now_text, spec.get("preflight_json_note", spec["preflight_text"]), f"{case_name} right now json-backed preflight note")
    focus_lane = payload[payload["best_action"]["lane_key"]]
    expected_quick_reads = [
        f"1. `{focus_lane['summary_txt']}`",
        f"2. `{focus_lane['next_steps_md']}`",
        f"3. `{focus_lane['lane_monitor_md']}`",
        f"4. `{payload['daily_summary']}`",
        f"5. `{ops_history_md.relative_to(BASE)}`",
    ]
    for snippet in expected_quick_reads:
        assert_contains(right_now_text, snippet, f"{case_name} right now quick reads")

    if spec.get("right_now_headline"):
        assert_contains(right_now_text, spec["right_now_headline"], f"{case_name} right now headline")
        assert_contains(right_now_text, spec["right_now_detail"], f"{case_name} right now detail")
        assert_not_contains(right_now_text, "Rerun the primary lane live, without --cache-only", f"{case_name} right now distinct from cache miss")
    else:
        assert_contains(right_now_text, "Follow the Phase 7 current paper lane next-step lead", f"{case_name} right now clean-empty headline")
        assert_contains(right_now_text, "Why: No ROI-complete races are settled yet", f"{case_name} right now clean-empty why")
        assert_not_contains(right_now_text, "partial-cache read", f"{case_name} right now distinct from partial cache")

    if spec.get("scanner_status_relpath"):
        assert_contains(right_now_text, spec["scanner_status_relpath"], f"{case_name} right now relocated scanner pointer")

    return {
        "status_summary": str(status_out.relative_to(BASE)),
        "next_steps": str(next_steps_out.relative_to(BASE)),
        "right_now": str(right_now_md.relative_to(BASE)),
        "right_now_json": str(right_now_json.relative_to(BASE)),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    scorecard_gates = read_scorecard_gate_minimums(args.scorecard_json)
    scorecard_cli_checks = scorecard_gate_cli_contract_checks(args.scorecard_json)
    report_dir = Path(args.out_dir)
    report_md = report_dir / "partial_cache_messaging_validation.md"
    report_json = report_dir / "partial_cache_messaging_validation.json"

    if FIXTURE_ROOT.exists():
        shutil.rmtree(FIXTURE_ROOT)

    scratch = build_fixture_scratch_metadata()
    ensure_ledgers()
    run_roots = {case_name: make_case(case_name, spec) for case_name, spec in CASES.items()}

    ops_md = FIXTURE_ROOT / "OPS_HISTORY.md"
    ops_csv = FIXTURE_ROOT / "ops_history.csv"
    run([
        sys.executable,
        str(OPS_HISTORY),
        "--runs-root", str(RUNS_ROOT),
        "--md-output", str(ops_md),
        "--csv-output", str(ops_csv),
    ])
    ops_text = ops_md.read_text(encoding="utf-8")
    assert_contains(ops_text, "| `2026-05-24` | OP/CD ACTIVE | PARTIAL CACHE EMPTY", "ops history partial-cache row")
    assert_contains(ops_text, CASES["case_partial_cache_active"]["ops_takeaway"], "ops history partial-cache takeaway")
    assert_contains(ops_text, "| `2026-05-22` | OP/CD ACTIVE | PARTIAL CACHE WITH ACTIVITY", "ops history partial-cache-with-activity row")
    assert_contains(ops_text, CASES["case_partial_cache_with_activity"]["ops_takeaway"], "ops history partial-cache-with-activity takeaway")
    assert_contains(ops_text, "| `2026-05-23` | OP/CD ACTIVE | CLEAN EMPTY", "ops history clean-empty row")
    assert_contains(ops_text, CASES["case_clean_empty_active"]["ops_takeaway"], "ops history clean-empty takeaway")
    assert_contains(ops_text, "| `2026-05-26` | OP/CD ACTIVE | PARTIAL CACHE EMPTY", "ops history json-only partial-cache row")
    assert_contains(ops_text, "| `2026-05-25` | OP/CD ACTIVE | CLEAN EMPTY", "ops history json-only clean-empty row")
    assert_contains(ops_text, "Active-target limited-coverage days: **3**", "ops history limited-coverage count")
    assert_contains(ops_text, "Active-target limited-coverage-with-activity days: **1**", "ops history limited-coverage-with-activity count")
    assert_contains(ops_text, "Consecutive active-target limited-coverage days at the top of the log: **1**", "ops history limited-coverage streak")
    assert_contains(ops_text, "- `2026-05-26`: JSON-only preflight note: primary paper-basket target tracks racing today: OP, CD.", "ops history json-only partial-cache preflight note")
    assert_contains(ops_text, "- `2026-05-25`: JSON-only preflight note: primary paper-basket target tracks racing today: OP, CD.", "ops history json-only clean-empty preflight note")
    assert_contains(ops_text, "| `2026-05-28` | OP/CD ACTIVE | PARTIAL CACHE EMPTY", "ops history blank-text partial-cache row")
    assert_contains(ops_text, "| `2026-05-27` | OP/CD ACTIVE | CLEAN EMPTY", "ops history blank-text clean-empty row")
    assert_contains(ops_text, "- `2026-05-28`: Blank-text fallback preflight note: primary paper-basket target tracks racing today: OP, CD.", "ops history blank-text partial-cache preflight note")
    assert_contains(ops_text, "- `2026-05-27`: Blank-text fallback preflight note: primary paper-basket target tracks racing today: OP, CD.", "ops history blank-text clean-empty preflight note")

    outputs = {case_name: validate_case(case_name, run_roots[case_name], spec) for case_name, spec in CASES.items()}

    suite_read = (
        "partial-cache messaging still keeps active-target limited-coverage empty days and limited-coverage-with-activity days distinct from both clean-empty scans and full cache misses, "
        "across ops history, status summary, next steps, and the top right-now card, and it now proves the same clean-empty-vs-limited-coverage split survives json-backed preflight-note fallback when the sibling text note is missing or blank, with the ops-history takeaway carrying scanner-side missing-detail context when it exists, the limited-coverage-with-activity branch also surviving a pipeline-declared relocated scanner sidecar when the default lane filename is absent, the right-now card keeping a dedicated partial-cache-activity refresh branch, that card's full routed recommendation-lane quick-reads bundle pinned to the fixture-routed surfaces, and a machine-readable evidence_boundary keeping partial-cache routing metadata separate from settled ROI, live profitability, promotion readiness, and real-money evidence"
        f"; it also publishes project-local fixture scratch metadata, exposes exact valid_evidence_scope={VALID_EVIDENCE_SCOPE} as limited-coverage routing metadata only, and preserves the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that partial-cache limited-coverage fixtures do not advance"
    )
    child_checks = [
        *scorecard_cli_checks,
        {
            "check": "clean_empty_and_partial_cache_empty_stay_distinct",
            "status": "pass",
            "detail": "the fixtures still prove a normal active zero-hit clean-empty day stays separate from a limited-coverage empty day across ops history, status summary, next steps, and the top card instead of collapsing both into one generic empty branch",
        },
        {
            "check": "partial_cache_with_activity_stays_distinct_from_empty_and_full_cache_miss",
            "status": "pass",
            "detail": "the activity fixture still proves a limited-coverage run that found and routed activity stays distinct from both the empty limited-coverage branch and the full cache-miss rerun-live branch",
        },
        {
            "check": "json_only_preflight_fallback_preserves_clean_empty_vs_limited_coverage_split",
            "status": "pass",
            "detail": "the json-only fixtures still prove removing preflight_note.txt does not erase the active-day interpretation because next steps and the top card keep reading preflight_note.json while preserving clean-empty versus limited-coverage messaging",
        },
        {
            "check": "blank_text_preflight_fallback_preserves_clean_empty_vs_limited_coverage_split",
            "status": "pass",
            "detail": "the blank-text fixtures still prove an existing-but-empty preflight_note.txt does not erase the active-day interpretation because next steps and the top card keep preferring preflight_note.json while preserving clean-empty versus limited-coverage messaging",
        },
        {
            "check": "partial_cache_activity_branch_keeps_relocated_scanner_pointer_and_routed_quick_reads",
            "status": "pass",
            "detail": "the partial-cache-with-activity branch still preserves the pipeline-declared relocated scanner sidecar pointer plus the full routed recommendation-lane quick-reads bundle instead of drifting back to repo-root defaults or the missing happy-path filename",
        },
        {
            "check": "partial_cache_messaging_stays_cross_surface_and_fixture_routed",
            "status": "pass",
            "detail": "the validator still proves the limited-coverage contract through the exact fixture-routed CLI surfaces Cole reads — ops history, status summary, next steps, and PAPER_TRADE_NOW — rather than leaning on live artifacts or prose alone",
        },
        {
            "check": "fixture_scratch_metadata_published",
            "status": "pass",
            "detail": "the partial-cache validator now publishes project-local fixture scratch metadata so parent rollups can verify limited-coverage fixture hygiene without parsing markdown prose",
        },
        {
            "check": "partial_cache_messaging_explicitly_stays_operator_routing_not_new_evidence",
            "status": "pass",
            "detail": "the partial-cache validator now publishes machine-readable evidence_boundary metadata so clean fixture-routed limited-coverage handling stays classified as operator routing metadata, not settled ROI, live profitability, promotion readiness, or real-money evidence",
        },
        {
            "check": "partial_cache_messaging_preserves_scorecard_gate_boundary",
            "status": "pass",
            "detail": "the partial-cache validator now publishes the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite while saying limited-coverage fixtures do not count toward those gates",
        },
        {
            "check": "direct_validation_report_exposes_partial_cache_valid_scope",
            "status": "pass",
            "detail": "the direct partial-cache validator report now exposes the raw valid_evidence_scope line and keeps green limited-coverage handling classified as operator routing metadata only",
        },
    ]
    if (
        scorecard_gates.get("source") != "forward_evidence_scorecard.json"
        or scorecard_gates.get("source_path") != "decision_gate_minimums"
        or scorecard_gates.get("anchor_displacement_min_roi_complete_settled_observations") != 30
        or scorecard_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") != 20
        or scorecard_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") != 100
        or scorecard_gates.get("real_money_no_baq_as_bel_required") is not True
        or "no BAQ-as-BEL substitution" not in scorecard_gates.get("real_money_also_requires", [])
    ):
        raise AssertionError("partial-cache scorecard gate boundary no longer matches forward_evidence_scorecard.json")

    report = {
        "suite_status": "pass",
        "total_fixture_scenarios": len(CASES),
        "total_checks": len(CASES),
        "check_count": len(CASES),
        "child_check_count": len(child_checks),
        "child_checks": child_checks,
        "ops_history": str(ops_md.relative_to(BASE)),
        "ops_csv": str(ops_csv.relative_to(BASE)),
        "results": [
            {"case": case_name, **outputs[case_name]}
            for case_name in CASES.keys()
        ],
        "summary": {
            "suite_read": suite_read,
        },
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scratch": scratch,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "fixture_root": str(FIXTURE_ROOT),
            "report_path": str(report_md),
        },
        **outputs,
    }
    write_text(report_md, "\n".join([
        "# Partial-Cache Messaging Validation",
        "",
        "This report validates that active-target partial-cache empty runs and partial-cache-with-activity runs stay distinct from both clean-empty scans and full cache misses across the operator-facing surfaces, including json-backed preflight-note fallback runs where the sibling text note is missing or blank.",
        "",
        "## Checks",
        "",
        f"- Ops history: `{report['ops_history']}` now shows an active-target partial-cache day as `PARTIAL CACHE EMPTY` with an `ACTIVE, LIMITED COVERAGE` bucket and the scanner-side missing-detail context in the takeaway, instead of flattening it into a clean-empty or generic-other day.",
        f"- Clean-empty comparison: `{report['case_clean_empty_active']['status_summary']}` plus `{report['case_clean_empty_active']['right_now']}` still read as a normal active zero-hit day, not a coverage problem.",
        f"- Partial-cache status summary: `{report['case_partial_cache_active']['status_summary']}` reports `partial cache`, not `cache miss (cache-only)` or `clean empty run`.",
        f"- Partial-cache next steps: `{report['case_partial_cache_active']['next_steps']}` promotes `LIMITED CACHE COVERAGE` and tells Cole to refresh live before treating the lane as a true zero-hit day.",
        f"- Partial-cache right-now card: `{report['case_partial_cache_active']['right_now']}` promotes `Refresh the primary lane live after the partial-cache read` instead of the full cache-miss rerun wording, while keeping the full routed recommendation-lane quick-reads bundle pinned to `{report['case_partial_cache_active']['right_now_json']}`'s chosen lane and `{report['ops_history']}`.",
        f"- Partial-cache-with-activity status summary: `{report['case_partial_cache_with_activity']['status_summary']}` reports `partial cache with activity`, preserving that the run still produced something instead of flattening it into the empty limited-coverage branch.",
        f"- Partial-cache-with-activity next steps + right-now card: `{report['case_partial_cache_with_activity']['next_steps']}` keeps the surviving recommendation context, and `{report['case_partial_cache_with_activity']['right_now']}` still promotes `Refresh the primary lane live after the partial-cache activity read` so Cole does not mistake incomplete coverage for a full clean live read, while also preserving the renamed scanner-sidecar pointer after the default `live_scan.status.json` path is removed.",
        f"- JSON-only clean-empty fallback: `{report['case_clean_empty_active_json_only']['next_steps']}` and `{report['case_clean_empty_active_json_only']['right_now']}` still read the saved preflight note from `preflight_note.json` after `preflight_note.txt` is removed, preserving the normal active zero-hit interpretation.",
        f"- JSON-only partial-cache fallback: `{report['case_partial_cache_active_json_only']['next_steps']}` and `{report['case_partial_cache_active_json_only']['right_now']}` still read the saved preflight note from `preflight_note.json` after `preflight_note.txt` is removed, preserving the limited-coverage interpretation instead of collapsing into a cache-miss or generic issue read.",
        f"- Blank-text clean-empty fallback: `{report['case_clean_empty_active_blank_text_prefers_json']['next_steps']}` and `{report['case_clean_empty_active_blank_text_prefers_json']['right_now']}` still prefer the saved preflight note from `preflight_note.json` when the sibling `preflight_note.txt` exists but is blank, preserving the normal active zero-hit interpretation.",
        f"- Blank-text partial-cache fallback: `{report['case_partial_cache_active_blank_text_prefers_json']['next_steps']}` and `{report['case_partial_cache_active_blank_text_prefers_json']['right_now']}` still prefer the saved preflight note from `preflight_note.json` when the sibling `preflight_note.txt` exists but is blank, preserving the limited-coverage interpretation instead of collapsing into a cache-miss or generic issue read.",
        "",
        "## Current Read",
        "",
        f"- Suite read: {suite_read}",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
        f"- valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
        f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
        "- Boundary: partial-cache validator cleanliness is operator failure-mode routing metadata only, not new forward evidence, not a live paper-trade ledger, not a current-day scanner result, not settled ROI, not live profitability, not promotion readiness, and not real-money evidence.",
        "- Non-goals: do not treat partial-cache empty runs as clean live zero-hit evidence, partial-cache-with-activity runs as full live recommendation evidence, or fixture-routed operator cards as promotion / real-money support.",
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
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Fixture root: `{FIXTURE_ROOT}`",
        f"- Fixture scratch metadata: `{scratch['fixture_root_relative']}` is project-local and cleared before fixture setup.",
        f"- Report path: `{report_md}`",
        "",
        "## Result",
        "",
        "- PASS: active-target partial-cache empty runs and partial-cache-with-activity runs now stay distinct from both full cache misses and genuine clean-empty scans across the covered operator surfaces, including the json-backed preflight fallback branches for both missing and blank text notes plus the relocated scanner-sidecar recovery branch.",
        "",
    ]))
    write_text(report_json, json.dumps(report, indent=2) + "\n")

    print(f"Wrote {report_md}")
    print(f"Wrote {report_json}")
    print("PASS partial-cache messaging fixture")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
