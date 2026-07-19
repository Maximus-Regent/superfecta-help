#!/usr/bin/env python3
"""
Fixture-driven validation for cache-only missing-cache messaging.

Purpose:
- distinguish cache-only cache misses from generic scanner failures
- keep the operator-facing messaging honest across status summary, next steps, ops history, and the top-level right-now card
- validate both the no-target and active-target interpretations without touching live ledgers
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
FIXTURE_ROOT = BASE / "out" / "status_validation" / "cache_only_messaging_fixture"
REPORT_DIR = BASE / "out" / "status_validation" / "cache_only_messaging"
REPORT_MD = REPORT_DIR / "cache_only_messaging_validation.md"
REPORT_JSON = REPORT_DIR / "cache_only_messaging_validation.json"
RUNS_ROOT = FIXTURE_ROOT / "out" / "daily_portfolio_runs"
PAPER_TRADES = FIXTURE_ROOT / "paper_trades"
REBUILD_COMMAND = "python3 validate_cache_only_messaging.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
VALID_EVIDENCE_SCOPE = "cache_only_missing_cache_routing_only"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "cache-only messaging validator",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "cache-only missing-cache fixtures",
        "saved preflight_note.txt / preflight_note.json calendar split",
        "forward_evidence_scorecard.json decision_gate_minimums",
        "paper_trade_status_summary.py",
        "paper_trade_next_steps.py",
        "paper_trade_ops_history.py",
        "paper_trade_now.py",
    ],
    "valid_use": "operator failure-mode routing for cache-only missing-cache days, including no-target stand-down versus active-target rerun-live separation",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "cache_only_validator_passes_are_operator_routing_metadata_only": True,
    "non_goals": [
        "do not treat cache-only no-target stand-down days as profitability evidence",
        "do not treat active-target cache misses as clean empty scans",
        "do not promote OP_REFINED_K7 or Phase 8 from cache-only validator cleanliness",
        "do not reopen current odds-only XGBoost from cache-only validator cleanliness",
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

CASES = {
    "case_no_targets": {
        "date": "2026-05-21",
        "preflight_text": "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 22 NYRA card(s). Shadow-only tracks present: KEE.",
        "preflight_json": {
            "date": "2026-05-21",
            "checked_at": "2026-05-21 11:00",
            "api_ok": True,
            "has_targets": False,
            "relevant_tracks": [],
            "shadow_tracks": ["KEE"],
            "total_cards": 22,
            "error": None,
            "note": "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 22 NYRA card(s). Shadow-only tracks present: KEE.",
        },
        "right_now_headline": "Stand down, no OP / CD target action tonight",
        "right_now_bucket": "Latest ops bucket: **NO TARGETS**",
        "right_now_detail": "cache miss",
        "next_steps_detail": "cache-only check could not start because today's cache files were missing",
        "ops_detail": "The cache-only run missed today's cache files, but the quiet day is still explained by the race calendar",
    },
    "case_active_targets": {
        "date": "2026-05-22",
        "scanner_status_relpath": "renamed_live_scan.status.json",
        "preflight_text": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        "preflight_json": {
            "date": "2026-05-22",
            "checked_at": "2026-05-22 11:00",
            "api_ok": True,
            "has_targets": True,
            "relevant_tracks": ["OP", "CD"],
            "shadow_tracks": [],
            "total_cards": 18,
            "error": None,
            "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        },
        "right_now_headline": "Rerun the primary lane live, without --cache-only",
        "right_now_bucket": "Latest ops bucket: **ISSUE**",
        "right_now_detail": "Re-run the daily wrapper live before treating the lane as empty.",
        "next_steps_detail": "Re-run without --cache-only before treating this lane as empty.",
        "ops_detail": "Re-run without --cache-only before drawing conclusions.",
    },
    "case_no_targets_json_only": {
        "date": "2026-05-25",
        "preflight_text": "JSON-only preflight note: no active OP/CD cards today; KEE is shadow-only.",
        "preflight_json": {
            "date": "2026-05-25",
            "checked_at": "2026-05-25 11:00",
            "api_ok": True,
            "has_targets": False,
            "relevant_tracks": [],
            "shadow_tracks": ["KEE"],
            "total_cards": 19,
            "error": None,
            "note": "JSON-only preflight note: no active OP/CD cards today; KEE is shadow-only.",
        },
        "right_now_headline": "Stand down, no OP / CD target action tonight",
        "right_now_bucket": "Latest ops bucket: **NO TARGETS**",
        "right_now_detail": "cache miss",
        "next_steps_detail": "cache-only check could not start because today's cache files were missing",
        "ops_detail": "The cache-only run missed today's cache files, but the quiet day is still explained by the race calendar",
        "remove_preflight_txt": True,
    },
    "case_active_targets_json_only": {
        "date": "2026-05-26",
        "preflight_text": "JSON-only preflight note: primary paper-basket target tracks racing today: OP, CD.",
        "preflight_json": {
            "date": "2026-05-26",
            "checked_at": "2026-05-26 11:00",
            "api_ok": True,
            "has_targets": True,
            "relevant_tracks": ["OP", "CD"],
            "shadow_tracks": [],
            "total_cards": 17,
            "error": None,
            "note": "JSON-only preflight note: primary paper-basket target tracks racing today: OP, CD.",
        },
        "right_now_headline": "Rerun the primary lane live, without --cache-only",
        "right_now_bucket": "Latest ops bucket: **ISSUE**",
        "right_now_detail": "Re-run the daily wrapper live before treating the lane as empty.",
        "next_steps_detail": "Re-run without --cache-only before treating this lane as empty.",
        "ops_detail": "Re-run without --cache-only before drawing conclusions.",
        "remove_preflight_txt": True,
    },
    "case_no_targets_blank_text_prefers_json": {
        "date": "2026-05-27",
        "preflight_text": "",
        "preflight_json": {
            "date": "2026-05-27",
            "checked_at": "2026-05-27 11:00",
            "api_ok": True,
            "has_targets": False,
            "relevant_tracks": [],
            "shadow_tracks": ["KEE"],
            "total_cards": 21,
            "error": None,
            "note": "Blank-text fallback preflight note: no active OP/CD cards today; KEE is shadow-only.",
        },
        "right_now_headline": "Stand down, no OP / CD target action tonight",
        "right_now_bucket": "Latest ops bucket: **NO TARGETS**",
        "right_now_detail": "cache miss",
        "next_steps_detail": "cache-only check could not start because today's cache files were missing",
        "ops_detail": "The cache-only run missed today's cache files, but the quiet day is still explained by the race calendar",
        "blank_preflight_txt": True,
    },
    "case_active_targets_blank_text_prefers_json": {
        "date": "2026-05-28",
        "preflight_text": "",
        "preflight_json": {
            "date": "2026-05-28",
            "checked_at": "2026-05-28 11:00",
            "api_ok": True,
            "has_targets": True,
            "relevant_tracks": ["OP", "CD"],
            "shadow_tracks": [],
            "total_cards": 16,
            "error": None,
            "note": "Blank-text fallback preflight note: primary paper-basket target tracks racing today: OP, CD.",
        },
        "right_now_headline": "Rerun the primary lane live, without --cache-only",
        "right_now_bucket": "Latest ops bucket: **ISSUE**",
        "right_now_detail": "Re-run the daily wrapper live before treating the lane as empty.",
        "next_steps_detail": "Re-run without --cache-only before treating this lane as empty.",
        "ops_detail": "Re-run without --cache-only before drawing conclusions.",
        "blank_preflight_txt": True,
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
            "cache-only missing-cache fixtures do not count toward anchor-displacement, "
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
    with TemporaryDirectory(prefix="cache_only_scorecard_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(scorecard_json_path).read_text(encoding="utf-8"))
        scorecard_path = tmp_root / "forward_evidence_scorecard.json"
        bad_out_dir = tmp_root / "nested" / "cache_only_messaging_validation"

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
                "scorecard_boolean_gate_floor_fails_before_cache_only_artifacts",
                "a malformed boolean anchor-displacement scorecard gate fails before nested cache-only validation outputs are created",
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
                "scorecard_nonpositive_phase8_gate_floor_fails_before_cache_only_artifacts",
                "a non-positive Phase 8 promotion-review scorecard gate fails before nested cache-only validation outputs are created",
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
                "scorecard_nonpositive_real_money_gate_floor_fails_before_cache_only_artifacts",
                "a non-positive real-money discussion scorecard gate fails before nested cache-only validation outputs are created",
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
                "scorecard_missing_no_baq_fails_before_cache_only_artifacts",
                "a scorecard gate missing the no-BAQ-as-BEL real-money prerequisite fails before nested cache-only validation outputs are created",
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
            "cache-only messaging fixture scratch metadata is operator-routing reproducibility context only, "
            "not a live scanner result, settled ROI, promotion readiness, live profitability, bankroll guidance, "
            "or real-money evidence"
        ),
    }


def make_lane(run_root: Path, lane_name: str, rules_name: str, run_ts: str, scanner_status_relpath: str = "live_scan.status.json") -> None:
    lane_dir = run_root / lane_name
    scanner_status_path = lane_dir / scanner_status_relpath
    scanner = {
        "run_ts": run_ts,
        "rules_path": str(BASE / rules_name),
        "cache_only": True,
        "cache_ttl": 900,
        "max_races": 1,
        "base_stake": 1.0,
        "include_cards": [],
        "dedup_enabled": True,
        "result": "scanner_error",
        "rule_count": 2,
        "error_type": "SystemExit",
        "error": "[cache-only] No cached data for cards/today — run without --cache-only first.",
        "cards_fallback_uses": 0,
        "races_fallback_uses": 0,
        "missing_race_detail_cache_skips": 0,
        "race_details_attempted": 0,
        "race_details_loaded": 0,
        "max_race_limit_hit": 0,
    }
    pipeline = {
        "run_ts": run_ts,
        "rules_path": str(BASE / rules_name),
        "scan_input": str(lane_dir / "live_scan.json"),
        "scanner_status_path": str(scanner_status_path),
        "recommendation_output_dir": str(lane_dir / "recommendations"),
        "recommendations_input": str(lane_dir / "recommendations" / "recommendations_summary.json"),
        "status_output": str(lane_dir / "pipeline_status.json"),
        "cache_only": True,
        "skip_scan": False,
        "stage": "done",
        "result": "ok",
        "scanner_stage_status": "scanner_failed",
        "scanner_exit_code": 1,
        "scan_hit_count": 0,
        "scanner_result": "scanner_error",
        "scanner_partial_cache": False,
        "scanner_raw_hit_count": 0,
        "scanner_emitted_hit_count": 0,
        "scanner_missing_race_detail_cache_skips": 0,
        "recommendation_count": 0,
        "bet_count": 0,
        "no_bet_count": 0,
        "error_count": 0,
        "observation_result": "scanner_failed_empty_run",
    }
    write_json(scanner_status_path, scanner)
    write_json(lane_dir / "pipeline_status.json", pipeline)
    write_text(lane_dir / "live_scan.json", "[]\n")


def make_case(case_name: str, spec: dict[str, Any]) -> Path:
    run_root = RUNS_ROOT / spec["date"]
    preflight_text = spec["preflight_text"]
    write_text(run_root / "preflight_note.txt", "\n" if spec.get("blank_preflight_txt") else preflight_text + "\n")
    write_json(run_root / "preflight_note.json", spec["preflight_json"])
    if spec.get("remove_preflight_txt"):
        (run_root / "preflight_note.txt").unlink()
    make_lane(run_root, "phase7_current_paper", "phase7_current_paper_rules.json", f"{spec['date']}T11:00:00", spec.get("scanner_status_relpath", "live_scan.status.json"))
    make_lane(run_root, "phase8_shadow", "phase8_shadow_rules.json", f"{spec['date']}T11:00:00")
    case_dir = FIXTURE_ROOT / case_name
    case_dir.mkdir(parents=True, exist_ok=True)
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
    assert_contains(status_text, "cache miss (cache-only)", f"{case_name} status summary")

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
    assert_contains(next_steps_text, spec["next_steps_detail"], f"{case_name} next steps")
    if spec.get("remove_preflight_txt") or spec.get("blank_preflight_txt"):
        assert_contains(next_steps_text, spec["preflight_json"]["note"], f"{case_name} next steps json-backed preflight note")
    if case_name in {"case_active_targets", "case_active_targets_json_only"}:
        assert_contains(next_steps_text, "State: RERUN LIVE CHECK", f"{case_name} next steps state")

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
    assert_contains(right_now_text, spec["right_now_headline"], f"{case_name} right now headline")
    assert_contains(right_now_text, spec["right_now_bucket"], f"{case_name} right now bucket")
    assert_contains(right_now_text, spec["right_now_detail"], f"{case_name} right now detail")
    if spec.get("remove_preflight_txt") or spec.get("blank_preflight_txt"):
        assert_contains(right_now_text, spec["preflight_json"]["note"], f"{case_name} right now json-backed preflight note")

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
    report_md = report_dir / "cache_only_messaging_validation.md"
    report_json = report_dir / "cache_only_messaging_validation.json"

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
    assert_contains(ops_text, "| `2026-05-21` | NO TARGETS | CACHE MISS (CACHE-ONLY)", "ops history no-target row")
    assert_contains(ops_text, CASES["case_no_targets"]["ops_detail"], "ops history no-target detail")
    assert_contains(ops_text, "| `2026-05-22` | OP/CD ACTIVE | CACHE MISS (CACHE-ONLY)", "ops history active-target row")
    assert_contains(ops_text, CASES["case_active_targets"]["ops_detail"], "ops history active-target detail")
    assert_contains(ops_text, "| `2026-05-27` | NO TARGETS | CACHE MISS (CACHE-ONLY)", "ops history blank-text no-target row")
    assert_contains(ops_text, "| `2026-05-28` | OP/CD ACTIVE | CACHE MISS (CACHE-ONLY)", "ops history blank-text active-target row")
    assert_contains(ops_text, "- `2026-05-27`: Blank-text fallback preflight note: no active OP/CD cards today; KEE is shadow-only.", "ops history blank-text no-target preflight note")
    assert_contains(ops_text, "- `2026-05-28`: Blank-text fallback preflight note: primary paper-basket target tracks racing today: OP, CD.", "ops history blank-text active-target preflight note")

    outputs = {case_name: validate_case(case_name, run_roots[case_name], spec) for case_name, spec in CASES.items()}

    suite_read = (
        "cache-only missing-cache messaging still stays distinct between no-target stand-down days and active-target rerun-live days, "
        "across ops history, status summary, next steps, and the top right-now card, and it now proves the same split survives json-backed preflight-note fallback when the sibling text note is missing or blank, with the active-target rerun-live branch also surviving a pipeline-declared relocated scanner sidecar when the default lane filename is absent, that card's full routed recommendation-lane quick-reads bundle pinned to the fixture-routed surfaces, and a machine-readable evidence_boundary keeping cache-only routing metadata separate from settled ROI, live profitability, promotion readiness, and real-money evidence"
        "; it also publishes project-local fixture scratch metadata and preserves the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that cache-only missing-cache fixtures do not advance, with boolean and non-positive copied-gate failures covered before cache-only validation artifacts are written"
        f"; the direct validator report now exposes exact valid_evidence_scope={VALID_EVIDENCE_SCOPE} as missing-cache routing metadata only"
    )
    child_checks = [
        *scorecard_cli_checks,
        {
            "check": "no_target_cache_only_days_stay_stand_down_not_generic_issue",
            "status": "pass",
            "detail": "the no-target fixtures still prove cache-only misses stay in the honest stand-down lane across ops history, status summary, next steps, and the top right-now card instead of collapsing into a generic issue or false live-action prompt",
        },
        {
            "check": "active_target_cache_only_days_stay_rerun_live_not_empty_or_quiet",
            "status": "pass",
            "detail": "the active-target fixtures still prove cache-only misses promote rerun-live guidance across next steps, ops history, and the top card instead of being mislabeled as a genuine clean-empty or quiet no-target day",
        },
        {
            "check": "json_only_preflight_fallback_preserves_the_calendar_split",
            "status": "pass",
            "detail": "the json-only fixtures still prove removing preflight_note.txt does not erase the no-target versus active-target interpretation because next steps and the top card keep reading the saved preflight_note.json snapshot",
        },
        {
            "check": "blank_text_preflight_fallback_preserves_the_calendar_split",
            "status": "pass",
            "detail": "the blank-text fixtures still prove an existing-but-empty preflight_note.txt does not erase the no-target versus active-target interpretation because next steps and the top card keep preferring the saved preflight_note.json note",
        },
        {
            "check": "active_target_branch_keeps_relocated_scanner_pointer_and_routed_quick_reads",
            "status": "pass",
            "detail": "the active-target rerun-live branch still preserves the pipeline-declared relocated scanner sidecar pointer and the full routed recommendation-lane quick-reads bundle instead of drifting back to repo-root defaults or the missing happy-path filename",
        },
        {
            "check": "cache_only_messaging_stays_cross_surface_and_fixture_routed",
            "status": "pass",
            "detail": "the validator still proves the cache-only contract through the exact CLI surfaces Cole reads — ops history, status summary, next steps, and PAPER_TRADE_NOW — while keeping those saved outputs pinned inside the fixture-routed scratch tree rather than leaning on live artifacts",
        },
        {
            "check": "fixture_scratch_metadata_published",
            "status": "pass",
            "detail": "the cache-only validator now publishes project-local fixture scratch metadata so parent rollups can verify missing-cache fixture hygiene without parsing markdown prose",
        },
        {
            "check": "cache_only_messaging_explicitly_stays_operator_routing_not_new_evidence",
            "status": "pass",
            "detail": "the cache-only validator now publishes machine-readable evidence_boundary metadata so clean fixture-routed cache-miss handling stays classified as operator routing metadata, not settled ROI, live profitability, promotion readiness, or real-money evidence",
        },
        {
            "check": "cache_only_messaging_preserves_scorecard_gate_boundary",
            "status": "pass",
            "detail": "the cache-only validator now publishes the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite while saying missing-cache fixtures do not count toward those gates",
        },
        {
            "check": "direct_validation_report_exposes_cache_only_valid_scope",
            "status": "pass",
            "detail": "the direct cache-only validator report now exposes the raw valid_evidence_scope line and keeps green missing-cache handling classified as operator routing metadata only",
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
        raise AssertionError("cache-only scorecard gate boundary no longer matches forward_evidence_scorecard.json")

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
        "# Cache-Only Messaging Validation",
        "",
        "This report validates that cache-only missing-cache runs are described distinctly from generic scanner failures in both no-target and active-target cases, including json-backed preflight-note fallback runs where the sibling text note is missing or blank.",
        "",
        "## Checks",
        "",
        f"- Ops history: `{report['ops_history']}` keeps the no-target case in `NO TARGETS` with an explicit cache-miss explanation, and keeps the active-target case as an issue that tells Cole to rerun without `--cache-only`.",
        f"- No-target status summary: `{report['case_no_targets']['status_summary']}` reports `cache miss (cache-only)`.",
        f"- No-target next steps: `{report['case_no_targets']['next_steps']}` explains that the cache-only check could not start because today's cache files were missing.",
        f"- No-target right-now card: `{report['case_no_targets']['right_now']}` still returns an honest stand-down read instead of a generic issue-only message, and its full routed recommendation-lane quick-reads bundle stays routed to `{report['case_no_targets']['right_now_json']}`'s chosen lane plus `{report['ops_history']}` instead of slipping back to repo-root defaults.",
        f"- Active-target next steps: `{report['case_active_targets']['next_steps']}` promotes `RERUN LIVE CHECK` and tells Cole to rerun without `--cache-only`.",
        f"- Active-target right-now card: `{report['case_active_targets']['right_now']}` promotes `Rerun the primary lane live, without --cache-only` as the best action now, while keeping the full routed recommendation-lane quick-reads bundle pinned to that chosen lane and `{report['ops_history']}`, and it now preserves the renamed scanner-sidecar pointer after the default `live_scan.status.json` path is removed.",
        f"- JSON-only no-target fallback: `{report['case_no_targets_json_only']['next_steps']}` and `{report['case_no_targets_json_only']['right_now']}` still read the saved preflight note from `preflight_note.json` after `preflight_note.txt` is removed, preserving the honest stand-down interpretation.",
        f"- JSON-only active-target fallback: `{report['case_active_targets_json_only']['next_steps']}` and `{report['case_active_targets_json_only']['right_now']}` still read the saved preflight note from `preflight_note.json` after `preflight_note.txt` is removed, preserving the rerun-live interpretation instead of collapsing into a generic issue read.",
        f"- Blank-text no-target fallback: `{report['case_no_targets_blank_text_prefers_json']['next_steps']}` and `{report['case_no_targets_blank_text_prefers_json']['right_now']}` still prefer the saved preflight note from `preflight_note.json` when the sibling `preflight_note.txt` exists but is blank, preserving the honest stand-down interpretation.",
        f"- Blank-text active-target fallback: `{report['case_active_targets_blank_text_prefers_json']['next_steps']}` and `{report['case_active_targets_blank_text_prefers_json']['right_now']}` still prefer the saved preflight note from `preflight_note.json` when the sibling `preflight_note.txt` exists but is blank, preserving the rerun-live interpretation instead of collapsing into a generic issue read.",
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
        "- Boundary: cache-only validator cleanliness is operator failure-mode routing metadata only, not new forward evidence, not a live paper-trade ledger, not a current-day scanner result, not settled ROI, not live profitability, not promotion readiness, and not real-money evidence.",
        "- Non-goals: do not treat no-target cache misses as profitability evidence, active-target cache misses as clean empty scans, or fixture-routed operator cards as promotion / real-money support.",
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
        "- PASS: cache-only cache misses now read differently from generic scanner failures across both no-target and active-target operator surfaces covered here, including the json-backed preflight fallback branches for both missing and blank text notes plus the relocated scanner-sidecar recovery branch.",
        "",
    ]))
    write_text(report_json, json.dumps(report, indent=2) + "\n")

    print(f"Wrote {report_md}")
    print(f"Wrote {report_json}")
    print("PASS cache-only messaging fixture")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
