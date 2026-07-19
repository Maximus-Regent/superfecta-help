#!/usr/bin/env python3
"""
Fixture-driven validation for paper_trade_next_steps.py.

Purpose:
- pin the lane-state to next-command transitions directly at the source layer
- keep settlement, cache, stale-artifact, and sample-size guidance reproducible
- validate the real CLI against isolated fixtures without touching live ledgers
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import paper_trade_next_steps as ptns

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "paper_trade_next_steps.py"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "next_steps_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_next_steps"
REPORT_MD = OUT_DIR / "paper_trade_next_steps_validation.md"
REPORT_JSON = OUT_DIR / "paper_trade_next_steps_validation.json"
LIVE_RUNS_ROOT = BASE / "out" / "daily_portfolio_runs"
REBUILD_COMMAND = "python3 validate_paper_trade_next_steps.py"
FROZEN_EVAL = BASE / "frozen_portfolio_eval_summary.csv"
RULES = BASE / "phase7_current_paper_rules.json"
PHASE8_RULES = BASE / "phase8_shadow_rules.json"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade next-steps validator",
    "valid_evidence_scope": ptns.VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "isolated next-steps fixture ledgers and sidecars",
        "saved live next-steps source-layer rebuilds",
        "paper_trade_next_steps.py",
        "forward_evidence_scorecard.json decision_gate_minimums",
    ],
    "valid_use": "operator action-routing validation for settlement, cache, artifact-refresh, and sample-readiness guidance",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "next_steps_validator_passes_are_action_routing_metadata_only": True,
    "non_goals": [
        "do not treat next-step routing cleanliness as ROI-complete observations",
        "do not treat refresh/rerun/repair guidance as sample progress",
        "do not treat scorecard-gate visibility as promotion readiness",
        "do not promote OP_REFINED_K7 or Phase 8 from review-floor wording",
        "do not substitute BAQ for BEL",
        "do not treat next-steps validation as real-money evidence",
    ],
}


def build_fixture_scratch_metadata() -> dict[str, Any]:
    validation_root = (BASE / "out" / "status_validation").resolve()
    fixture_root = FIXTURE_ROOT.resolve()
    return {
        "fixture_root": str(fixture_root),
        "fixture_root_relative": str(FIXTURE_ROOT.relative_to(BASE)),
        "fixture_root_is_project_local": fixture_root == validation_root or validation_root in fixture_root.parents,
        "case_roots_cleared_by_setup_case": True,
    }


SIGNAL_FIELDS = [
    "signal_key", "scan_ts", "rule_id", "track", "card_name", "race_number", "race_id",
    "surface", "condition", "field_size", "favorite_program", "favorite_name", "favorite_prob",
    "second_prob", "prob_gap", "k", "base_stake", "estimated_cost", "underneath_programs",
    "ticket_structure", "status", "outcome", "notes",
]
RECOMMENDATION_FIELDS = [
    "signal_key", "run_ts", "rule_id", "track", "card_name", "race_number", "race_id", "decision",
    "reason", "favorite_program", "underneath_programs", "scanner_estimated_cost", "scored_combo_count",
    "filtered_combo_count", "bankroll", "race_risk_budget", "total_stake", "total_expected_return",
    "total_expected_profit", "portfolio_expected_roi_pct", "tickets_selected", "tickets_json",
    "prediction_csv", "plan_json", "plan_csv", "status", "outcome", "notes",
]
SETTLEMENT_FIELDS = [
    "signal_key", "scan_ts", "rule_id", "track", "card_name", "race_number", "race_id", "expected_cost",
    "settlement_status", "outcome", "actual_cost", "actual_return", "actual_profit", "settled_ts", "notes",
]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def display_scorecard_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BASE.resolve()))
    except Exception:
        return str(path)


def require_positive_non_bool_int(value: Any, *, source_name: str, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, source_name: str, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise AssertionError(f"{source_name} {field_name} must be a string list")
    return value


def empty_ledgers(case_root: Path) -> None:
    paper_trades = case_root / "paper_trades"
    write_csv(paper_trades / "phase7_current_paper_paper_trade_signals.csv", SIGNAL_FIELDS, [])
    write_csv(paper_trades / "phase7_current_paper_paper_trade_recommendations.csv", RECOMMENDATION_FIELDS, [])
    write_csv(paper_trades / "phase7_current_paper_paper_trade_settlements.csv", SETTLEMENT_FIELDS, [])


def signal_row(idx: int, rule_id: str = "OP_DURABLE_K7", track: str = "OP", race_number: int = 7,
               estimated_cost: float = 24.0) -> dict[str, Any]:
    return {
        "signal_key": f"{rule_id.lower()}_{idx:03d}",
        "scan_ts": f"2026-05-01T1{idx % 10}:00:00",
        "rule_id": rule_id,
        "track": track,
        "card_name": "Oaklawn Park" if track == "OP" else "Churchill Downs",
        "race_number": race_number,
        "race_id": f"{track}-2026-05-01-R{race_number}",
        "surface": "dirt",
        "condition": "fast",
        "field_size": 11 if rule_id == "OP_DURABLE_K7" else 10,
        "favorite_program": "1",
        "favorite_name": f"Favorite {idx}",
        "favorite_prob": "0.32",
        "second_prob": "0.18",
        "prob_gap": "0.14",
        "k": "7" if rule_id == "OP_DURABLE_K7" else "8",
        "base_stake": "1",
        "estimated_cost": f"{estimated_cost:.2f}",
        "underneath_programs": "2,3,4",
        "ticket_structure": "1 / 2,3,4",
        "status": "",
        "outcome": "",
        "notes": "fixture",
    }


def settlement_row(signal: dict[str, Any], settlement_status: str, outcome: str,
                   actual_return: float | None = None, *, actual_cost_override: str | None = None,
                   settled_ts_override: str | None = None) -> dict[str, Any]:
    cost = float(signal["estimated_cost"])
    returned = actual_return if actual_return is not None else ""
    if actual_cost_override is not None:
        actual_cost = actual_cost_override
    else:
        actual_cost = f"{cost:.2f}" if settlement_status == "settled" else ""
    profit = ""
    if actual_return is not None and actual_cost:
        try:
            profit = f"{actual_return - float(actual_cost):.2f}"
        except ValueError:
            profit = ""
    return {
        "signal_key": signal["signal_key"],
        "scan_ts": signal["scan_ts"],
        "rule_id": signal["rule_id"],
        "track": signal["track"],
        "card_name": signal["card_name"],
        "race_number": signal["race_number"],
        "race_id": signal["race_id"],
        "expected_cost": signal["estimated_cost"],
        "settlement_status": settlement_status,
        "outcome": outcome,
        "actual_cost": actual_cost,
        "actual_return": f"{returned:.2f}" if isinstance(returned, float) else returned,
        "actual_profit": profit,
        "settled_ts": (
            settled_ts_override
            if settled_ts_override is not None else
            ("2026-05-01T19:30:00" if settlement_status == "settled" else "")
        ),
        "notes": "fixture",
    }


def pipeline_status(observation_result: str, *, hits: int = 0, recs: int = 0, bets: int = 0,
                    cache_only: bool = False, scanner_result: str | None = None,
                    scanner_error: str | None = None, result: str = "ok",
                    stage: str = "done", error_type: str | None = None,
                    error: str | None = None, last_completed_stage: str | None = None,
                    max_race_limit_hit: bool = False, race_details_attempted: int = 0,
                    target_race_count: int = 0, full_target_coverage_min_races: int = 0,
                    unattempted_target_race_count: int = 0,
                    api_failure_operator_action: str | None = None,
                    api_failure_recheck_command: str | None = None) -> dict[str, Any]:
    payload = {
        "result": result,
        "observation_result": observation_result,
        "scan_hit_count": hits,
        "recommendation_count": recs,
        "bet_count": bets,
        "cache_only": cache_only,
        "stage": stage,
        "rules_path": str(RULES.name),
    }
    if scanner_result is not None:
        payload["scanner_result"] = scanner_result
    if scanner_error is not None:
        payload["scanner_error"] = scanner_error
    if api_failure_operator_action is not None:
        payload["scanner_api_failure_operator_action"] = api_failure_operator_action
    if api_failure_recheck_command is not None:
        payload["scanner_api_failure_recheck_command"] = api_failure_recheck_command
    if error_type is not None:
        payload["error_type"] = error_type
    if error is not None:
        payload["error"] = error
    if last_completed_stage is not None:
        payload["last_completed_stage"] = last_completed_stage
    if max_race_limit_hit:
        payload["scanner_max_race_limit_hit"] = True
    if race_details_attempted:
        payload["scanner_race_details_attempted"] = race_details_attempted
    if target_race_count:
        payload["scanner_target_race_count"] = target_race_count
    if full_target_coverage_min_races:
        payload["scanner_full_target_coverage_min_races"] = full_target_coverage_min_races
    if unattempted_target_race_count:
        payload["scanner_unattempted_target_race_count"] = unattempted_target_race_count
    if result == "pipeline_error":
        payload["observation_scope"] = "operational_failure"
        payload["observation_reason"] = "logger_failure" if stage == "logger" else "recommender_failure" if stage == "recommender" else "pipeline_error"
    elif cache_only and scanner_result == "scanner_error" and scanner_error and "No cached data" in scanner_error:
        payload["observation_scope"] = "operational_limit"
        payload["observation_reason"] = "cache_only_miss"
    elif observation_result == "partial_cache_empty_run":
        payload["observation_scope"] = "operational_limit"
        payload["observation_reason"] = "partial_cache_empty"
    elif observation_result == "partial_cache_with_activity":
        payload["observation_scope"] = "operational_limit"
        payload["observation_reason"] = "partial_cache_with_activity"
    elif observation_result == "scanner_failed_empty_run":
        payload["observation_scope"] = "operational_limit"
        payload["observation_reason"] = "scanner_failure"
    elif observation_result == "clean_empty_run":
        payload["observation_scope"] = "clean_observation"
        payload["observation_reason"] = "reused_input_empty" if scanner_result == "reused_input_empty" else "no_matching_cards" if scanner_result == "no_matching_cards" else "no_qualifiers"
    elif observation_result == "signals_logged_no_bet":
        payload["observation_scope"] = "clean_observation"
        payload["observation_reason"] = "signals_logged_no_bet"
    elif observation_result == "bets_ready":
        payload["observation_scope"] = "bet_ready"
        payload["observation_reason"] = "bets_ready"
    return payload


def scanner_status(result: str, *, cache_only: bool = False, error: str | None = None,
                   partial_cache: bool = False, missing_race_detail_cache_skips: int = 0,
                   max_race_limit_hit: bool = False, race_details_attempted: int = 0,
                   target_race_count: int = 0, full_target_coverage_min_races: int = 0,
                   unattempted_target_race_count: int = 0,
                   api_failure_operator_action: str | None = None,
                   api_failure_recheck_command: str | None = None) -> dict[str, Any]:
    payload = {
        "result": result,
        "cache_only": cache_only,
        "partial_cache": partial_cache,
        "missing_race_detail_cache_skips": missing_race_detail_cache_skips,
        "card_count": 2,
        "race_count": 18,
        "rules_path": str(RULES.name),
    }
    if max_race_limit_hit:
        payload["max_race_limit_hit"] = 1
    if race_details_attempted:
        payload["race_details_attempted"] = race_details_attempted
    if target_race_count:
        payload["target_race_count"] = target_race_count
    if full_target_coverage_min_races:
        payload["full_target_coverage_min_races"] = full_target_coverage_min_races
    if unattempted_target_race_count:
        payload["unattempted_target_race_count"] = unattempted_target_race_count
    if error is not None:
        payload["error"] = error
    if api_failure_operator_action is not None:
        payload["api_failure_operator_action"] = api_failure_operator_action
    if api_failure_recheck_command is not None:
        payload["api_failure_recheck_command"] = api_failure_recheck_command
    return payload


def preflight(has_targets: bool, note: str, relevant_tracks: list[str] | None = None,
              shadow_tracks: list[str] | None = None, calendar_reason: str | None = None,
              calendar_state: str | None = None, api_ok: bool = True, error: str | None = None) -> dict[str, Any]:
    if calendar_reason is None:
        if error:
            calendar_reason = "upstream_error"
        elif not api_ok:
            calendar_reason = "api_unreachable"
        else:
            calendar_reason = "active_targets" if has_targets else "no_targets"
    if calendar_state is None:
        if calendar_reason in {"upstream_error", "api_unreachable"}:
            calendar_state = "UNKNOWN"
        elif calendar_reason == "active_targets":
            calendar_state = "ACTIVE TARGETS"
        else:
            calendar_state = "NO TARGETS"
    return {
        "date": "2026-05-01",
        "checked_at": "2026-05-01 12:00",
        "api_ok": api_ok,
        "calendar_state": calendar_state,
        "calendar_reason": calendar_reason,
        "has_targets": has_targets,
        "relevant_tracks": relevant_tracks or [],
        "shadow_tracks": shadow_tracks or [],
        "total_cards": 18,
        "error": error,
        "note": note,
    }


def setup_case(case_name: str, preflight_payload: dict[str, Any], primary_signals: list[dict[str, Any]],
               primary_settlements: list[dict[str, Any]], primary_status: dict[str, Any] | None,
               primary_scanner_status: dict[str, Any] | None,
               scanner_relpath: str | None = None) -> tuple[Path, Path, Path, Path, Path, Path, Path]:
    case_root = FIXTURE_ROOT / case_name
    if case_root.exists():
        shutil.rmtree(case_root)
    empty_ledgers(case_root)

    paper_trades = case_root / "paper_trades"
    signals_path = paper_trades / "phase7_current_paper_paper_trade_signals.csv"
    recs_path = paper_trades / "phase7_current_paper_paper_trade_recommendations.csv"
    settlements_path = paper_trades / "phase7_current_paper_paper_trade_settlements.csv"
    write_csv(signals_path, SIGNAL_FIELDS, primary_signals)
    write_csv(recs_path, RECOMMENDATION_FIELDS, [])
    write_csv(settlements_path, SETTLEMENT_FIELDS, primary_settlements)

    run_root = case_root / "out" / "daily_portfolio_runs" / "2026-05-01"
    preflight_path = run_root / "preflight_note.txt"
    pipeline_path = run_root / "phase7_current_paper" / "pipeline_status.json"
    scanner_path = run_root / "phase7_current_paper" / "live_scan.status.json"
    actual_scanner_path = run_root / scanner_relpath if scanner_relpath else scanner_path
    write_text(preflight_path, preflight_payload["note"] + "\n")
    write_json(run_root / "preflight_note.json", preflight_payload)
    if primary_status is not None:
        status_payload = dict(primary_status)
        if scanner_relpath and not str(status_payload.get("scanner_status_path") or "").strip():
            status_payload["scanner_status_path"] = str(actual_scanner_path)
        write_json(pipeline_path, status_payload)
    if primary_scanner_status is not None:
        write_json(actual_scanner_path, primary_scanner_status)

    return case_root, signals_path, recs_path, settlements_path, scanner_path, pipeline_path, preflight_path


def assert_contains(text: str, needle: str, case_name: str) -> None:
    if needle not in text:
        raise AssertionError(f"{case_name}: expected to find {needle!r}")


def read_scorecard_gate_minimums(scorecard_json: Path = SCORECARD_JSON) -> dict[str, Any]:
    source_name = display_scorecard_path(scorecard_json)
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
        "source": "forward_evidence_scorecard.json",
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_also_requires": real_money_requires,
        "real_money_no_baq_as_bel_required": True,
        "evidence_boundary": (
            "next-step routing, cache/artifact refresh guidance, settlement-repair prompts, "
            "sample-readiness wording, scorecard-gate visibility, and Phase 8 review-floor cautions "
            "do not count toward anchor-displacement, Phase 8 promotion-review, or real-money discussion gates"
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--fixture-root", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def configure_output_paths(fixture_root: Path, out_dir: Path) -> None:
    global FIXTURE_ROOT, OUT_DIR, REPORT_MD, REPORT_JSON
    FIXTURE_ROOT = fixture_root
    OUT_DIR = out_dir
    REPORT_MD = OUT_DIR / "paper_trade_next_steps_validation.md"
    REPORT_JSON = OUT_DIR / "paper_trade_next_steps_validation.json"


def pass_check(check_name: str, detail: str) -> dict[str, str]:
    return {"check": check_name, "status": "pass", "detail": detail}


def expected_issue_flags(
    *,
    api_access: bool = False,
    scanner_boundary: bool = False,
    stale_cache: bool = False,
) -> dict[str, bool]:
    return {
        "has_api_access_failure_context": api_access,
        "has_scanner_failure_boundary": scanner_boundary,
        "has_stale_cache_fallback_context": stale_cache,
    }


def assert_operator_read_gate_issue_flags(payload: dict[str, Any], case: dict[str, Any]) -> None:
    nested = payload.get("operator_read_gate_issue_flags")
    if not isinstance(nested, dict):
        raise AssertionError(f"{case['name']}: next_steps.json is missing operator_read_gate_issue_flags")
    for flag in ptns.STATUS_OPERATOR_READ_GATE_ISSUE_FLAGS:
        top_value = payload.get(flag)
        nested_value = nested.get(flag)
        if not isinstance(top_value, bool) or not isinstance(nested_value, bool):
            raise AssertionError(f"{case['name']}: {flag} must be a boolean in both top-level and nested issue flags")
        if top_value != nested_value:
            raise AssertionError(f"{case['name']}: top-level {flag} no longer mirrors operator_read_gate_issue_flags")
    expected = case.get("operator_read_gate_issue_flags")
    if expected is not None and nested != expected:
        raise AssertionError(
            f"{case['name']}: expected operator_read_gate_issue_flags {expected!r}, got {nested!r}"
        )


def assert_scorecard_failure_before_artifacts(
    *,
    scorecard_json: Path,
    mutation: Any,
    expected_stderr: str,
    check_name: str,
    detail: str,
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix=f"{check_name}_") as tmp:
        tmpdir = Path(tmp)
        bad_scorecard = tmpdir / "forward_evidence_scorecard.json"
        bad_payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
        mutation(bad_payload)
        bad_scorecard.write_text(json.dumps(bad_payload, indent=2) + "\n", encoding="utf-8")

        fixture_root = tmpdir / "fixture_root"
        out_dir = tmpdir / "nested" / "report_artifacts"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(bad_scorecard),
                "--fixture-root",
                str(fixture_root),
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
        if fixture_root.exists() or out_dir.exists():
            raise AssertionError(f"{check_name}: malformed scorecard created fixture/report artifacts")
    return pass_check(check_name, detail)


def scorecard_no_artifact_guardrails(scorecard_json: Path) -> list[dict[str, str]]:
    return [
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["anchor_displacement"].__setitem__(
                "min_roi_complete_settled_observations",
                True,
            ),
            expected_stderr=(
                "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check_name="scorecard_boolean_gate_floor_fails_before_next_steps_artifacts",
            detail=(
                "a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before "
                "the next-steps validator creates fixture roots or report artifacts"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["phase8_promotion_review"].__setitem__(
                "min_roi_complete_settled_observations",
                0,
            ),
            expected_stderr=(
                "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check_name="scorecard_nonpositive_phase8_gate_floor_fails_before_next_steps_artifacts",
            detail=(
                "a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails before "
                "the next-steps validator creates fixture roots or report artifacts"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                "min_total_settled_observations_with_usable_roi",
                0,
            ),
            expected_stderr=(
                "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi "
                "must be a positive non-boolean integer"
            ),
            check_name="scorecard_nonpositive_real_money_gate_floor_fails_before_next_steps_artifacts",
            detail=(
                "a non-positive real-money discussion floor in forward_evidence_scorecard.json fails before "
                "the next-steps validator creates fixture roots or report artifacts"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
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
            check_name="scorecard_missing_no_baq_fails_before_next_steps_artifacts",
            detail=(
                "a scorecard real-money gate that drops the no BAQ-as-BEL prerequisite fails before "
                "the next-steps validator creates fixture roots or report artifacts"
            ),
        ),
    ]


def assert_scorecard_gate_source(
    payload: dict[str, Any],
    text_content: str,
    md_content: str,
    case_name: str,
    *,
    expected_active_gate: str = "anchor_displacement",
    expected_active_min_settled: int = 30,
    expected_active_gate_key: str = "anchor_displacement_min_roi_complete_settled_observations",
) -> None:
    gates = payload.get("decision_gate_minimums") or {}
    expected = {
        "source_path": "forward_evidence_scorecard.json",
        "source_loaded": True,
        "fallback_used": False,
        "anchor_displacement_min_roi_complete_settled_observations": 30,
        "phase8_promotion_review_min_roi_complete_settled_observations": 20,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": 100,
        "real_money_discussion_also_requires": [
            "positive paper ROI",
            "concentration checks",
            "payout-distribution sanity checks",
            "no BAQ-as-BEL substitution",
        ],
        "real_money_no_baq_as_bel_required": True,
        "active_first_read_gate": expected_active_gate,
        "active_first_read_gate_key": expected_active_gate_key,
        "active_min_settled": expected_active_min_settled,
        "active_portfolio_review_settled": 100,
        "cli_overrides": {},
    }
    for key, value in expected.items():
        if gates.get(key) != value:
            raise AssertionError(f"{case_name}: expected decision_gate_minimums[{key!r}] == {value!r}, got {gates.get(key)!r}")
    if payload.get("min_settled") != expected_active_min_settled or payload.get("portfolio_review_settled") != 100:
        raise AssertionError(f"{case_name}: next-steps active gate payload drifted from scorecard-sourced lane-specific 30/20/100 defaults")
    active_gate = str(gates["active_first_read_gate"])
    alignment = f"next-steps sample milestones are source-matched to forward_evidence_scorecard.json decision_gate_minimums using {active_gate} for this lane"
    expected_forward_alignment = f"forward-check sample milestones are source-matched to forward_evidence_scorecard.json decision_gate_minimums using {active_gate} for this lane"
    if gates.get("alignment_read") != expected_forward_alignment:
        raise AssertionError(f"{case_name}: underlying forward-check alignment metadata drifted")
    assert_contains(
        text_content,
        "- Gate source: forward_evidence_scorecard.json decision_gate_minimums loaded=True anchor_displacement=30 phase8_promotion_review=20 real_money_discussion=100 real_money_no_baq_as_bel_required=True",
        case_name,
    )
    assert_contains(
        text_content,
        f"- Active gates: first_read={expected_active_min_settled}; portfolio_review=100. {alignment}.",
        case_name,
    )
    assert_contains(md_content, "## Decision-Gate Source", case_name)
    assert_contains(md_content, "- Source: `forward_evidence_scorecard.json`; loaded=True; fallback_used=False.", case_name)
    assert_contains(
        md_content,
        "- Scorecard `decision_gate_minimums`: anchor_displacement=30 ROI-complete same-candidate settled observations; phase8_promotion_review=20 ROI-complete shadow observations; real_money_discussion=100 total settled observations with usable ROI; real_money_requires=positive paper ROI; concentration checks; payout-distribution sanity checks; no BAQ-as-BEL substitution.",
        case_name,
    )
    assert_contains(
        md_content,
        f"- Active next-step gates: min_settled={expected_active_min_settled}; portfolio_review_settled=100. {alignment}.",
        case_name,
    )
    assert_contains(md_content, "- These thresholds are posture-gate metadata for action routing only; they are not live-profitability, promotion, anchor-change, or real-money evidence.", case_name)


CASES: list[dict[str, Any]] = [
    {
        "name": "case_needs_settlement",
        "scenario": "open settlement queue takes priority",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        "signals": [signal_row(1)],
        "settlements": [settlement_row(signal_row(1), "open", "")],
        "status": pipeline_status("signals_logged_no_bet", hits=1, recs=1, scanner_result="alerts_found"),
        "scanner": scanner_status("alerts_found"),
        "state": "NEEDS SETTLEMENT",
        "why": "settlement row(s) are still open",
        "command_1": "paper_trade_settlement_helper.py list-open",
        "recent_context": "logged signals but produced no BET recommendations",
        "text_needles": ["--outcome '<HIT_OR_MISS>'"],
        "md_needles": ["--outcome '<HIT_OR_MISS>'"],
        "must_not_contain": ["--outcome HIT --actual-return"],
    },
    {
        "name": "case_incomplete_settlement_data",
        "scenario": "rows marked settled without an outcome still force settlement cleanup before forward interpretation",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        "signals": [signal_row(1)],
        "settlements": [settlement_row(signal_row(1), "settled", "")],
        "status": pipeline_status("clean_empty_run", scanner_result="no_qualifiers"),
        "scanner": scanner_status("no_qualifiers"),
        "state": "NEEDS SETTLEMENT",
        "why": "marked settled but still missing outcome data",
        "command_1": "paper_trade_lane_monitor.py",
        "text_needles": [
            "settled rows missing outcome: 1",
            "fix those ledger rows before treating the forward metrics as complete",
        ],
        "md_needles": [
            "- Settled rows missing outcome: `1`",
            "fix those ledger rows before treating the forward metrics as complete",
        ],
    },
    {
        "name": "case_refresh_run_artifacts",
        "scenario": "missing latest pipeline sidecar forces refresh-artifacts state",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        "signals": [],
        "settlements": [],
        "status": None,
        "scanner": scanner_status("no_qualifiers"),
        "state": "REFRESH RUN ARTIFACTS",
        "why": "pipeline status artifact is missing",
        "command_1": "./run_daily_portfolio_observation.sh",
    },
    {
        "name": "case_empty_pipeline_artifact",
        "scenario": "empty latest pipeline sidecar forces refresh-artifacts state with a distinct operator clue",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        "signals": [],
        "settlements": [],
        "status": pipeline_status("clean_empty_run", scanner_result="no_qualifiers"),
        "scanner": scanner_status("no_qualifiers"),
        "empty_pipeline_status": True,
        "state": "REFRESH RUN ARTIFACTS",
        "why": "pipeline status artifact is empty",
        "command_1": "./run_daily_portfolio_observation.sh",
        "text_needles": [
            "The latest lane pipeline status artifact is empty.",
        ],
        "md_needles": [
            "The latest lane pipeline status artifact is empty.",
        ],
    },
    {
        "name": "case_invalid_shape_pipeline_artifact",
        "scenario": "readable but non-object latest pipeline sidecar forces refresh-artifacts state with a distinct operator clue",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        "signals": [],
        "settlements": [],
        "status": pipeline_status("clean_empty_run", scanner_result="no_qualifiers"),
        "scanner": scanner_status("no_qualifiers"),
        "invalid_shape_pipeline_status": True,
        "state": "REFRESH RUN ARTIFACTS",
        "why": "pipeline status artifact has invalid JSON shape",
        "command_1": "./run_daily_portfolio_observation.sh",
        "text_needles": [
            "The latest lane pipeline status artifact has invalid JSON shape.",
        ],
        "md_needles": [
            "The latest lane pipeline status artifact has invalid JSON shape.",
        ],
    },
    {
        "name": "case_empty_scanner_sidecar",
        "scenario": "empty latest scanner sidecar forces refresh-artifacts state with a distinct operator clue",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        "signals": [],
        "settlements": [],
        "status": pipeline_status("clean_empty_run", scanner_result="no_qualifiers"),
        "scanner": scanner_status("no_qualifiers"),
        "empty_scanner_status": True,
        "state": "REFRESH RUN ARTIFACTS",
        "why": "scanner status sidecar is empty",
        "command_1": "./run_daily_portfolio_observation.sh",
        "text_needles": [
            "The latest scanner status sidecar is empty.",
        ],
        "md_needles": [
            "The latest scanner status sidecar is empty.",
        ],
    },
    {
        "name": "case_invalid_shape_scanner_sidecar",
        "scenario": "readable but non-object latest scanner sidecar forces refresh-artifacts state with a distinct operator clue",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        "signals": [],
        "settlements": [],
        "status": pipeline_status("clean_empty_run", scanner_result="no_qualifiers"),
        "scanner": scanner_status("no_qualifiers"),
        "invalid_shape_scanner_status": True,
        "state": "REFRESH RUN ARTIFACTS",
        "why": "scanner status sidecar has invalid JSON shape",
        "command_1": "./run_daily_portfolio_observation.sh",
        "text_needles": [
            "The latest scanner status sidecar has invalid JSON shape.",
        ],
        "md_needles": [
            "The latest scanner status sidecar has invalid JSON shape.",
        ],
    },
    {
        "name": "case_pipeline_recorded_empty_scanner_sidecar_missing",
        "scenario": "pipeline-recorded empty scanner-status state still forces refresh guidance when copied surface lacks the physical scanner sidecar",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        "signals": [],
        "settlements": [],
        "status": {
            **pipeline_status(
                "scanner_status_unavailable_empty_run",
                scanner_result="scanner_status_empty",
            ),
            "scanner_status_state": "empty",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_status_empty",
        },
        "scanner": None,
        "state": "REFRESH RUN ARTIFACTS",
        "why": "scanner status sidecar was recorded empty by the pipeline",
        "command_1": "./run_daily_portfolio_observation.sh",
        "text_needles": [
            "The latest scanner status sidecar was recorded empty by the pipeline, and the current scanner sidecar file is missing from this surface.",
        ],
        "md_needles": [
            "The latest scanner status sidecar was recorded empty by the pipeline, and the current scanner sidecar file is missing from this surface.",
        ],
    },
    {
        "name": "case_pipeline_recorded_unreadable_scanner_sidecar_missing",
        "scenario": "pipeline-recorded unreadable scanner-status state still forces refresh guidance when copied surface lacks the physical scanner sidecar",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        "signals": [],
        "settlements": [],
        "status": {
            **pipeline_status(
                "scanner_status_unavailable_with_activity",
                hits=1,
                recs=1,
                scanner_result="scanner_status_unreadable",
            ),
            "scanner_status_state": "unreadable",
            "scanner_status_error": "JSONDecodeError: fixture malformed scanner status",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_status_unreadable",
        },
        "scanner": None,
        "state": "REFRESH RUN ARTIFACTS",
        "why": "scanner status sidecar was recorded unreadable by the pipeline",
        "command_1": "./run_daily_portfolio_observation.sh",
        "text_needles": [
            "The latest scanner status sidecar was recorded unreadable by the pipeline, and the current scanner sidecar file is missing from this surface.",
        ],
        "md_needles": [
            "The latest scanner status sidecar was recorded unreadable by the pipeline, and the current scanner sidecar file is missing from this surface.",
        ],
    },
    {
        "name": "case_pipeline_recorded_invalid_shape_scanner_sidecar_missing",
        "scenario": "pipeline-recorded invalid-shape scanner-status state still forces refresh guidance when copied surface lacks the physical scanner sidecar",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        "signals": [],
        "settlements": [],
        "status": {
            **pipeline_status(
                "scanner_status_unavailable_with_activity",
                hits=1,
                recs=1,
                scanner_result="scanner_status_invalid_shape",
            ),
            "scanner_status_state": "invalid_shape",
            "scanner_status_error": "expected scanner-status JSON object, got list",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_status_invalid_shape",
        },
        "scanner": None,
        "state": "REFRESH RUN ARTIFACTS",
        "why": "scanner status sidecar was recorded invalid-shape by the pipeline",
        "command_1": "./run_daily_portfolio_observation.sh",
        "text_needles": [
            "The latest scanner status sidecar was recorded invalid-shape by the pipeline, and the current scanner sidecar file is missing from this surface.",
        ],
        "md_needles": [
            "The latest scanner status sidecar was recorded invalid-shape by the pipeline, and the current scanner sidecar file is missing from this surface.",
        ],
    },
    {
        "name": "case_rerun_live_check",
        "scenario": "active-target cache-only miss promotes rerun-live guidance",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        "signals": [],
        "settlements": [],
        "status": pipeline_status(
            "scanner_failed_empty_run",
            cache_only=True,
            scanner_result="scanner_error",
            scanner_error="No cached data found for today's races",
        ),
        "scanner": scanner_status(
            "scanner_error",
            cache_only=True,
            error="No cached data found for today's races",
        ),
        "state": "RERUN LIVE CHECK",
        "why": "cache-only check could not start",
        "command_1": "./run_daily_portfolio_observation.sh",
        "recent_context": "cache-only check could not start because today's cache files were missing",
        "operator_read_gate_issue_flags": expected_issue_flags(),
    },
    {
        "name": "case_generic_scanner_error_detail",
        "scenario": "non-cache scanner failures preserve upstream error detail and force scanner-failure refresh guidance instead of falling into sample collection",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        "signals": [],
        "settlements": [],
        "status": pipeline_status(
            "scanner_failed_empty_run",
            scanner_result="scanner_error",
            scanner_error="403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            api_failure_operator_action="refresh_daily_wrapper_before_evidence_read",
            api_failure_recheck_command="./run_daily_portfolio_observation.sh",
        ),
        "scanner": scanner_status(
            "scanner_error",
            error="403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            api_failure_operator_action="refresh_daily_wrapper_before_evidence_read",
            api_failure_recheck_command="./run_daily_portfolio_observation.sh",
        ),
        "state": "CHECK SCANNER FAILURE",
        "why": "API-access scanner failure operator context",
        "command_1": "./run_daily_portfolio_observation.sh",
        "scanner_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
        "scanner_failure_recheck_command": "./run_daily_portfolio_observation.sh",
        "operator_read_gate_issue_flags": expected_issue_flags(api_access=True, scanner_boundary=True),
        "recent_context": "scanner failed before producing signals",
        "must_contain": [
            "Detail: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "API-access-failure operator context only",
            "Sidecar action: refresh_daily_wrapper_before_evidence_read.",
            "Recheck command: ./run_daily_portfolio_observation.sh.",
        ],
        "text_needles": [
            "Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence.",
            "Sidecar action: refresh_daily_wrapper_before_evidence_read.",
            "Recheck command: ./run_daily_portfolio_observation.sh.",
        ],
        "md_needles": [
            "Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence.",
            "Sidecar action: refresh_daily_wrapper_before_evidence_read.",
            "Recheck command: ./run_daily_portfolio_observation.sh.",
        ],
        "must_not_contain": [
            "completed cleanly and found no qualifying races",
            "cache-only check could not start",
        ],
    },
    {
        "name": "case_api_access_stale_cache_fallback_route",
        "scenario": "API-access scanner failures that complete from stale cache preserve fallback context in exact next-command guidance",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        "signals": [],
        "settlements": [],
        "status": {
            **pipeline_status(
                "scanner_failed_empty_run",
                scanner_result="scanner_error",
                scanner_error="403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
                api_failure_operator_action="refresh_daily_wrapper_before_evidence_read",
                api_failure_recheck_command="./run_daily_portfolio_observation.sh",
            ),
            "observation_scope": "operational_limit",
            "observation_reason": "api_access_failure",
            "scanner_http_status": 403,
            "scanner_api_access_failure": True,
            "scanner_api_failure_class": "api_access_failure",
            "scanner_stale_cache_fallback_applied": True,
            "scanner_stale_cache_fallback_count": 2,
            "scanner_stale_cache_fallback_kind": "cards",
            "scanner_stale_cache_fallback_error_type": "HTTPError",
            "scanner_stale_cache_fallback_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
        },
        "scanner": {
            **scanner_status(
                "scanner_error",
                error="403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
                api_failure_operator_action="refresh_daily_wrapper_before_evidence_read",
                api_failure_recheck_command="./run_daily_portfolio_observation.sh",
            ),
            "http_status": 403,
            "api_access_failure": True,
            "api_failure_class": "api_access_failure",
            "stale_cache_fallback_applied": True,
            "stale_cache_fallback_count": 2,
            "stale_cache_fallback_kind": "cards",
            "stale_cache_fallback_error_type": "HTTPError",
            "stale_cache_fallback_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
        },
        "state": "CHECK SCANNER FAILURE",
        "why": "API-access scanner failure operator context",
        "command_1": "./run_daily_portfolio_observation.sh",
        "scanner_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
        "scanner_failure_recheck_command": "./run_daily_portfolio_observation.sh",
        "operator_read_gate_issue_flags": expected_issue_flags(
            api_access=True,
            scanner_boundary=True,
            stale_cache=True,
        ),
        "recent_context": "scanner failed before producing signals",
        "must_contain": [
            "stale-cache fallback used for cards",
            "2 stale-cache fallback(s)",
            "stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "API-access-failure operator context only",
        ],
        "text_needles": [
            "Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence.",
            "stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx.",
            "Sidecar action: refresh_daily_wrapper_before_evidence_read.",
            "Recheck command: ./run_daily_portfolio_observation.sh.",
        ],
        "md_needles": [
            "Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence.",
            "stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx.",
            "Sidecar action: refresh_daily_wrapper_before_evidence_read.",
            "Recheck command: ./run_daily_portfolio_observation.sh.",
        ],
        "must_not_contain": [
            "completed cleanly and found no qualifying races",
            "No ROI-complete races are settled yet",
        ],
    },
    {
        "name": "case_missing_scan_output_refresh_artifacts",
        "scenario": "successful scanner sidecar with missing scan-output artifact forces refresh-artifacts guidance instead of clean-empty or generic scanner-failure guidance",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        "signals": [],
        "settlements": [],
        "status": {
            **pipeline_status(
                "scanner_failed_empty_run",
                scanner_result="missing_scan_output",
            ),
            "observation_scope": "operational_limit",
            "observation_reason": "missing_scan_output",
            "scanner_status_reported_result": "no_qualifiers",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "missing_or_empty_scan_output",
            "scan_input_state_before_empty_fallback": "missing",
            "scan_input_empty_fallback_value": "[]",
        },
        "scanner": scanner_status("no_qualifiers"),
        "state": "REFRESH RUN ARTIFACTS",
        "why": "scan-output artifact was missing",
        "command_1": "./run_daily_portfolio_observation.sh",
        "recent_context": "scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers",
        "must_contain": [
            "safe empty [] fallback",
            "not a clean no-qualifier observation",
        ],
        "must_not_contain": [
            "scanner failed before producing signals",
            "completed cleanly and found no qualifying races",
        ],
    },
    {
        "name": "case_limited_cache_coverage",
        "scenario": "active-target partial-cache empty read stays operationally limited",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        "signals": [],
        "settlements": [],
        "status": pipeline_status(
            "partial_cache_empty_run",
            scanner_result="partial_cache_no_qualifiers",
        ),
        "scanner": scanner_status(
            "partial_cache_no_qualifiers",
            partial_cache=True,
            missing_race_detail_cache_skips=2,
        ),
        "state": "LIMITED CACHE COVERAGE",
        "why": "partial cache coverage",
        "command_1": "./run_daily_portfolio_observation.sh",
        "recent_context": "latest run depended on partial cache data and finished empty",
    },
    {
        "name": "case_partial_cache_with_activity_waits_for_settlements",
        "scenario": "partial-cache runs with surviving activity do not get mislabeled as limited-cache empty days",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        "signals": [],
        "settlements": [],
        "status": pipeline_status(
            "partial_cache_with_activity",
            hits=1,
            recs=1,
            bets=0,
            scanner_result="partial_cache_missing_detail",
        ),
        "scanner": scanner_status(
            "partial_cache_missing_detail",
            partial_cache=True,
            missing_race_detail_cache_skips=1,
        ),
        "state": "WAITING FOR FIRST SETTLED RACES",
        "why": "No ROI-complete races are settled yet",
        "command_1": "./run_daily_portfolio_observation.sh",
        "recent_context": "depended on partial cache data but still produced 1 recommendation(s) from 1 hit(s)",
        "text_needles": [
            "First statistical-read progress: 0/30 ROI-complete settled",
            "Broader portfolio-review progress: 0/100 ROI-complete settled",
        ],
        "md_needles": [
            "First statistical-read progress: `0/30` ROI-complete settled",
            "Broader portfolio-review progress: `0/100` ROI-complete settled",
        ],
    },
    {
        "name": "case_max_races_limited_empty_coverage",
        "scenario": "active-target max-races-limited empty read routes to limited target coverage instead of clean zero-hit guidance",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        "signals": [],
        "settlements": [],
        "status": pipeline_status(
            "limited_coverage_empty_run",
            scanner_result="no_qualifiers",
            max_race_limit_hit=True,
            race_details_attempted=12,
            target_race_count=18,
            full_target_coverage_min_races=18,
            unattempted_target_race_count=6,
        ),
        "scanner": scanner_status(
            "no_qualifiers",
            max_race_limit_hit=True,
            race_details_attempted=12,
            target_race_count=18,
            full_target_coverage_min_races=18,
            unattempted_target_race_count=6,
        ),
        "state": "LIMITED TARGET COVERAGE",
        "why": "limited target coverage rather than a clean empty observation",
        "command_1": "./run_daily_portfolio_observation.sh",
        "recent_context": "latest live scan hit the --max-races cap after 12 candidate race-detail attempt(s)",
        "must_contain": [
            "6 target candidate race(s) unattempted",
            "raise --max-races to at least 18 for full target coverage",
            "not a clean zero-hit observation",
        ],
        "must_not_contain": [
            "completed cleanly and found no qualifying races",
        ],
    },
    {
        "name": "case_pipeline_failure",
        "scenario": "recommender-stage pipeline crash becomes an explicit operator issue instead of falling through to normal observation guidance",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        "signals": [],
        "settlements": [],
        "status": pipeline_status(
            "signals_logged_no_bet",
            hits=1,
            recs=0,
            bets=0,
            scanner_result="alerts_found",
            result="pipeline_error",
            stage="recommender",
            error_type="RuntimeError",
            error="fixture recommender crash",
            last_completed_stage="scanner",
        ),
        "scanner": scanner_status("alerts_found"),
        "state": "CHECK PIPELINE FAILURE",
        "why": "operational issue instead of normal observation noise",
        "command_1": "./run_daily_portfolio_observation.sh",
        "recent_context": "latest lane run ended in recommender failure",
        "must_contain": [
            "Last completed stage: scanner.",
            "Stage: recommender.",
            "Scanner hits before failure: 1.",
            "Error type: RuntimeError.",
            "Detail: fixture recommender crash",
        ],
        "text_needles": [
            "The scanner had already found 1 hit(s) before the recommender failed.",
        ],
        "md_needles": [
            "The scanner had already found 1 hit(s) before the recommender failed.",
        ],
    },
    {
        "name": "case_pipeline_logger_failure",
        "scenario": "logger-stage pipeline crash becomes an explicit operator issue instead of falling through to normal observation guidance",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        "signals": [],
        "settlements": [],
        "status": pipeline_status(
            "bets_ready",
            hits=1,
            recs=1,
            bets=1,
            scanner_result="alerts_found",
            result="pipeline_error",
            stage="logger",
            error_type="ValueError",
            error="fixture logger crash",
            last_completed_stage="recommender",
        ),
        "scanner": scanner_status("alerts_found"),
        "state": "CHECK PIPELINE FAILURE",
        "why": "operational issue instead of normal observation noise",
        "command_1": "./run_daily_portfolio_observation.sh",
        "recent_context": "latest lane run ended in logger failure",
        "must_contain": [
            "Last completed stage: recommender.",
            "Stage: logger.",
            "Recommendations built before failure: 1.",
            "BET recommendations before failure: 1.",
            "Pre-error lane context: bets_ready.",
            "Error type: ValueError.",
            "Detail: fixture logger crash",
        ],
        "text_needles": [
            "The recommender had already produced 1 recommendation(s), including 1 BET recommendation(s), before logging failed.",
        ],
        "md_needles": [
            "The recommender had already produced 1 recommendation(s), including 1 BET recommendation(s), before logging failed.",
        ],
    },
    {
        "name": "case_waiting_for_first_settled_races",
        "scenario": "zero-settled lane stays in observation mode",
        "preflight": preflight(False, "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 18 NYRA card(s).", shadow_tracks=["KEE"]),
        "signals": [],
        "settlements": [],
        "status": pipeline_status("clean_empty_run", scanner_result="no_qualifiers"),
        "scanner": scanner_status("no_qualifiers"),
        "state": "WAITING FOR FIRST SETTLED RACES",
        "why": "No ROI-complete races are settled yet",
        "command_1": "./run_daily_portfolio_observation.sh",
        "recent_context": "latest live scan completed cleanly and found no qualifying races",
        "operator_read_gate_issue_flags": expected_issue_flags(),
        "text_needles": [
            "- First statistical-read progress: 0/30 ROI-complete settled (30 more needed)",
            "- Broader portfolio-review progress: 0/100 ROI-complete settled (100 more needed)",
        ],
        "md_needles": [
            "- First statistical-read progress: `0/30` ROI-complete settled (30 more needed)",
            "- Broader portfolio-review progress: `0/100` ROI-complete settled (100 more needed)",
        ],
    },
    {
        "name": "case_pipeline_declared_scanner_sidecar",
        "scenario": "next-steps recovers a lane-local renamed scanner sidecar from pipeline_status.json instead of assuming live_scan.status.json exists",
        "preflight": preflight(False, "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 18 NYRA card(s).", shadow_tracks=["KEE"]),
        "signals": [],
        "settlements": [],
        "status": {**pipeline_status("clean_empty_run"), "scanner_status_path": "renamed_live_scan.status.json"},
        "scanner": scanner_status("no_qualifiers"),
        "scanner_relpath": "phase7_current_paper/renamed_live_scan.status.json",
        "state": "WAITING FOR FIRST SETTLED RACES",
        "why": "No ROI-complete races are settled yet",
        "command_1": "./run_daily_portfolio_observation.sh",
        "recent_context": "latest live scan completed cleanly and found no qualifying races across 2 card(s) and 18 race(s)",
    },
    {
        "name": "case_pipeline_declared_scanner_sidecar_run_root_relative",
        "scenario": "next-steps recovers a run-root-relative renamed scanner sidecar from pipeline_status.json instead of assuming live_scan.status.json exists",
        "preflight": preflight(False, "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 18 NYRA card(s).", shadow_tracks=["KEE"]),
        "signals": [],
        "settlements": [],
        "status": {**pipeline_status("clean_empty_run"), "scanner_status_path": "phase7_current_paper/renamed_live_scan.status.json"},
        "scanner": scanner_status("no_qualifiers"),
        "scanner_relpath": "phase7_current_paper/renamed_live_scan.status.json",
        "state": "WAITING FOR FIRST SETTLED RACES",
        "why": "No ROI-complete races are settled yet",
        "command_1": "./run_daily_portfolio_observation.sh",
        "recent_context": "latest live scan completed cleanly and found no qualifying races across 2 card(s) and 18 race(s)",
    },
    {
        "name": "case_pipeline_declared_scanner_sidecar_project_relative",
        "scenario": "next-steps recovers a project-relative renamed scanner sidecar from pipeline_status.json instead of assuming live_scan.status.json exists",
        "preflight": preflight(False, "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 18 NYRA card(s).", shadow_tracks=["KEE"]),
        "signals": [],
        "settlements": [],
        "status": {
            **pipeline_status("clean_empty_run"),
            "scanner_status_path": "out/status_validation/next_steps_fixture/case_pipeline_declared_scanner_sidecar_project_relative/out/daily_portfolio_runs/2026-05-01/phase7_current_paper/renamed_live_scan.status.json",
        },
        "scanner": scanner_status("no_qualifiers"),
        "scanner_relpath": "phase7_current_paper/renamed_live_scan.status.json",
        "state": "WAITING FOR FIRST SETTLED RACES",
        "why": "No ROI-complete races are settled yet",
        "command_1": "./run_daily_portfolio_observation.sh",
        "recent_context": "latest live scan completed cleanly and found no qualifying races across 2 card(s) and 18 race(s)",
    },
    {
        "name": "case_structured_active_target_preflight",
        "scenario": "active-target rerun-live guidance trusts structured preflight JSON even if the note text wording drifts",
        "preflight": preflight(True, "Calendar note wording changed, but OP is still active today.", relevant_tracks=["OP"], calendar_reason="active_targets", calendar_state="ACTIVE TARGETS"),
        "signals": [],
        "settlements": [],
        "status": pipeline_status(
            "scanner_failed_empty_run",
            cache_only=True,
            scanner_result="scanner_error",
            scanner_error="No cached data found for today's races",
        ),
        "scanner": scanner_status(
            "scanner_error",
            cache_only=True,
            error="No cached data found for today's races",
        ),
        "state": "RERUN LIVE CHECK",
        "why": "cache-only check could not start",
        "command_1": "./run_daily_portfolio_observation.sh",
        "recent_context": "cache-only check could not start because today's cache files were missing",
    },
    {
        "name": "case_json_only_active_target_preflight",
        "scenario": "missing preflight text surface still falls back to the saved JSON snapshot instead of treating the file path as note text",
        "preflight": preflight(True, "JSON-only preflight note: OP is still active today.", relevant_tracks=["OP"], calendar_reason="active_targets", calendar_state="ACTIVE TARGETS"),
        "signals": [],
        "settlements": [],
        "status": pipeline_status(
            "scanner_failed_empty_run",
            cache_only=True,
            scanner_result="scanner_error",
            scanner_error="No cached data found for today's races",
        ),
        "scanner": scanner_status(
            "scanner_error",
            cache_only=True,
            error="No cached data found for today's races",
        ),
        "state": "RERUN LIVE CHECK",
        "why": "cache-only check could not start",
        "command_1": "./run_daily_portfolio_observation.sh",
        "recent_context": "cache-only check could not start because today's cache files were missing",
        "remove_preflight_txt": True,
        "text_needles": [
            "- JSON-only preflight note: OP is still active today.",
        ],
        "md_needles": [
            "- JSON-only preflight note: OP is still active today.",
        ],
    },
    {
        "name": "case_blank_text_active_target_preflight",
        "scenario": "blank preflight text surface still falls back to the saved JSON snapshot instead of hiding active-target rerun-live context",
        "preflight": preflight(True, "Blank-text fallback note: OP is still active today.", relevant_tracks=["OP"], calendar_reason="active_targets", calendar_state="ACTIVE TARGETS"),
        "signals": [],
        "settlements": [],
        "status": pipeline_status(
            "scanner_failed_empty_run",
            cache_only=True,
            scanner_result="scanner_error",
            scanner_error="No cached data found for today's races",
        ),
        "scanner": scanner_status(
            "scanner_error",
            cache_only=True,
            error="No cached data found for today's races",
        ),
        "state": "RERUN LIVE CHECK",
        "why": "cache-only check could not start",
        "command_1": "./run_daily_portfolio_observation.sh",
        "recent_context": "cache-only check could not start because today's cache files were missing",
        "blank_preflight_txt": True,
        "text_needles": [
            "- Blank-text fallback note: OP is still active today.",
        ],
        "md_needles": [
            "- Blank-text fallback note: OP is still active today.",
        ],
    },
    {
        "name": "case_partial_roi_coverage_gap",
        "scenario": "settled outcomes with missing return values stay visible as incomplete ROI-complete coverage instead of looking fully measured",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        "signals": [signal_row(i) for i in range(1, 6)],
        "settlements": [
            settlement_row(signal_row(1), "settled", "HIT", 96.0),
            settlement_row(signal_row(2), "settled", "MISS", 0.0),
            settlement_row(signal_row(3), "settled", "MISS", None),
            settlement_row(signal_row(4), "settled", "MISS", None),
            settlement_row(signal_row(5), "settled", "MISS", None),
        ],
        "status": pipeline_status("clean_empty_run", scanner_result="no_qualifiers"),
        "scanner": scanner_status("no_qualifiers"),
        "state": "REPAIR ROI COVERAGE",
        "why": "still cannot contribute to realized ROI",
        "command_1": "paper_trade_lane_monitor.py",
        "text_needles": [
            "- ROI coverage: 2/5 settled races are ROI-complete with return/cost/timestamp coverage (3 still missing coverage)",
            "- Settled rows missing ROI-complete coverage: 3 (missing actual_return: 3)",
            "fill the missing or malformed return/cost/timestamp values before treating the forward metrics as complete",
        ],
        "md_needles": [
            "- ROI coverage: `2/5` settled races are ROI-complete with return/cost/timestamp coverage (`3` still missing coverage)",
            "- Settled rows missing ROI-complete coverage: `3` (missing actual_return: 3)",
        ],
    },
    {
        "name": "case_malformed_actual_cost_roi_repair",
        "scenario": "settled outcomes with malformed actual_cost route next-step guidance to ROI-complete repair instead of collection/review",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        "signals": [signal_row(i) for i in range(1, 4)],
        "settlements": [
            settlement_row(signal_row(1), "settled", "HIT", 96.0),
            settlement_row(signal_row(2), "settled", "MISS", 0.0, actual_cost_override="bad-cost"),
            settlement_row(signal_row(3), "settled", "MISS", 0.0),
        ],
        "status": pipeline_status("clean_empty_run", scanner_result="no_qualifiers"),
        "scanner": scanner_status("no_qualifiers"),
        "state": "REPAIR ROI COVERAGE",
        "why": "malformed actual_cost",
        "command_1": "paper_trade_lane_monitor.py",
        "text_needles": [
            "- ROI coverage: 2/3 settled races are ROI-complete with return/cost/timestamp coverage (1 still missing coverage)",
            "- Settled rows missing ROI-complete coverage: 1 (malformed actual_cost: 1)",
            "fill the missing or malformed return/cost/timestamp values before treating the forward metrics as complete",
        ],
        "md_needles": [
            "- ROI coverage: `2/3` settled races are ROI-complete with return/cost/timestamp coverage (`1` still missing coverage)",
            "- Settled rows missing ROI-complete coverage: `1` (malformed actual_cost: 1)",
        ],
    },
    {
        "name": "case_settled_timestamp_gap_roi_repair",
        "scenario": "settled outcomes with usable return/cost but missing settled_ts stay out of ROI-complete sample gates",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        "signals": [signal_row(i) for i in range(1, 31)],
        "settlements": [
            settlement_row(
                signal_row(i),
                "settled",
                "HIT" if i <= 6 else "MISS",
                96.0 if i <= 6 else 0.0,
                settled_ts_override="" if i == 30 else None,
            )
            for i in range(1, 31)
        ],
        "status": pipeline_status("clean_empty_run", scanner_result="no_qualifiers"),
        "scanner": scanner_status("no_qualifiers"),
        "state": "REPAIR ROI COVERAGE",
        "why": "missing settled_ts",
        "command_1": "paper_trade_lane_monitor.py",
        "text_needles": [
            "- ROI coverage: 29/30 settled races are ROI-complete with return/cost/timestamp coverage (1 still missing coverage)",
            "- Settled rows missing ROI-complete coverage: 1 (missing settled_ts: 1)",
            "- First statistical-read progress: 29/30 ROI-complete settled (1 more needed)",
            "fill the missing or malformed return/cost/timestamp values before treating the forward metrics as complete",
        ],
        "md_needles": [
            "- ROI coverage: `29/30` settled races are ROI-complete with return/cost/timestamp coverage (`1` still missing coverage)",
            "- Settled rows missing ROI-complete coverage: `1` (missing settled_ts: 1)",
            "- First statistical-read progress: `29/30` ROI-complete settled (1 more needed)",
        ],
    },
    {
        "name": "case_collecting_sample",
        "scenario": "sub-threshold settled sample stays below decision-grade",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        "signals": [signal_row(i) for i in range(1, 6)],
        "settlements": [settlement_row(signal_row(i), "settled", "HIT" if i == 1 else "MISS", 96.0 if i == 1 else 0.0) for i in range(1, 6)],
        "status": pipeline_status("clean_empty_run", scanner_result="no_qualifiers"),
        "scanner": scanner_status("no_qualifiers"),
        "state": "COLLECTING SAMPLE",
        "why": "below the first statistical-read threshold",
        "command_1": "paper_trade_lane_monitor.py",
        "text_needles": [
            "- First statistical-read progress: 5/30 ROI-complete settled (25 more needed)",
            "- Broader portfolio-review progress: 5/100 ROI-complete settled (95 more needed)",
        ],
        "md_needles": [
            "- First statistical-read progress: `5/30` ROI-complete settled (25 more needed)",
            "- Broader portfolio-review progress: `5/100` ROI-complete settled (95 more needed)",
        ],
    },
    {
        "name": "case_decision_grade_review",
        "scenario": "threshold-crossing lane promotes forward-check review",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        "signals": [signal_row(i) for i in range(1, 31)],
        "settlements": [settlement_row(signal_row(i), "settled", "HIT" if i <= 6 else "MISS", 96.0 if i <= 6 else 0.0) for i in range(1, 31)],
        "status": pipeline_status("clean_empty_run", scanner_result="no_qualifiers"),
        "scanner": scanner_status("no_qualifiers"),
        "state": "DECISION-GRADE REVIEW",
        "why": "has reached the first statistical-read threshold",
        "command_1": "paper_trade_forward_check.py",
        "recent_context": "latest live scan completed cleanly and found no qualifying races",
        "text_needles": [
            "- First statistical-read progress: 30/30 ROI-complete settled (threshold reached)",
            "- Broader portfolio-review progress: 30/100 ROI-complete settled (70 more needed)",
        ],
        "md_needles": [
            "- First statistical-read progress: `30/30` ROI-complete settled; threshold reached",
            "- Broader portfolio-review progress: `30/100` ROI-complete settled (70 more needed)",
        ],
    },
    {
        "name": "case_phase8_review_floor_not_promotion",
        "scenario": "Phase 8 shadow first-read threshold stays a review floor rather than promotion entitlement",
        "rules": PHASE8_RULES,
        "expected_active_gate": "phase8_promotion_review",
        "expected_active_gate_key": "phase8_promotion_review_min_roi_complete_settled_observations",
        "expected_active_min_settled": 20,
        "preflight": preflight(True, "Preflight context: shadow-watch target tracks racing today: CD.", shadow_tracks=["CD"]),
        "signals": [signal_row(i, rule_id="CD_REFINED_K9", track="CD", race_number=9, estimated_cost=30.0) for i in range(1, 21)],
        "settlements": [
            settlement_row(
                signal_row(i, rule_id="CD_REFINED_K9", track="CD", race_number=9, estimated_cost=30.0),
                "settled",
                "MISS",
                0.0,
            )
            for i in range(1, 21)
        ],
        "status": pipeline_status("clean_empty_run", scanner_result="no_qualifiers"),
        "scanner": scanner_status("no_qualifiers"),
        "state": "DECISION-GRADE REVIEW",
        "why": "review floor, not a promotion entitlement",
        "command_1": "paper_trade_forward_check.py",
        "text_needles": [
            "- First statistical-read progress: 20/20 ROI-complete settled (threshold reached)",
            "- Active gates: first_read=20; portfolio_review=100. next-steps sample milestones are source-matched to forward_evidence_scorecard.json decision_gate_minimums using phase8_promotion_review for this lane.",
            "- Decision-gate caution: Phase 8 shadow first-read status is a review floor, not a promotion entitlement; lane totals alone do not promote any Phase 8 pocket, scorecard tiers remain binding, and negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion.",
        ],
        "md_needles": [
            "- First statistical-read progress: `20/20` ROI-complete settled; threshold reached",
            "- Active next-step gates: min_settled=20; portfolio_review_settled=100. next-steps sample milestones are source-matched to forward_evidence_scorecard.json decision_gate_minimums using phase8_promotion_review for this lane.",
            "- Decision-gate caution: Phase 8 shadow first-read status is a review floor, not a promotion entitlement; lane totals alone do not promote any Phase 8 pocket, scorecard tiers remain binding, and negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion.",
        ],
    },
    {
        "name": "case_portfolio_review_ready",
        "scenario": "broad portfolio-review milestone is explicit once the larger settled sample is reached",
        "preflight": preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        "signals": [signal_row(i) for i in range(1, 101)],
        "settlements": [settlement_row(signal_row(i), "settled", "HIT" if i <= 20 else "MISS", 96.0 if i <= 20 else 0.0) for i in range(1, 101)],
        "status": pipeline_status("clean_empty_run", scanner_result="no_qualifiers"),
        "scanner": scanner_status("no_qualifiers"),
        "state": "DECISION-GRADE REVIEW",
        "why": "has also reached the broader portfolio review gate",
        "command_1": "paper_trade_forward_check.py",
        "text_needles": [
            "- First statistical-read progress: 100/30 ROI-complete settled (threshold reached)",
            "- Broader portfolio-review progress: 100/100 ROI-complete settled (threshold reached)",
        ],
        "md_needles": [
            "- First statistical-read progress: `100/30` ROI-complete settled; threshold reached",
            "- Broader portfolio-review progress: `100/100` ROI-complete settled; threshold reached",
        ],
    },
]


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    rules_path = case.get("rules", RULES)
    case_root, signals_path, recs_path, settlements_path, scanner_path, pipeline_path, preflight_path = setup_case(
        case_name=case["name"],
        preflight_payload=case["preflight"],
        primary_signals=case["signals"],
        primary_settlements=case["settlements"],
        primary_status=case["status"],
        primary_scanner_status=case["scanner"],
        scanner_relpath=case.get("scanner_relpath"),
    )

    if case.get("remove_preflight_txt"):
        preflight_path.unlink(missing_ok=True)
    elif case.get("blank_preflight_txt"):
        preflight_path.write_text("", encoding="utf-8")
    if case.get("empty_pipeline_status"):
        pipeline_path.write_text("", encoding="utf-8")
    if case.get("invalid_shape_pipeline_status"):
        pipeline_path.write_text("[]\n", encoding="utf-8")
    if case.get("empty_scanner_status"):
        scanner_path.write_text("", encoding="utf-8")
    if case.get("invalid_shape_scanner_status"):
        scanner_path.write_text("[]\n", encoding="utf-8")

    json_output = case_root / "next_steps.json"
    text_output = case_root / "next_steps.txt"
    md_output = case_root / "next_steps.md"

    common = [
        sys.executable,
        str(SCRIPT),
        "--signals-ledger", str(signals_path),
        "--recommendation-ledger", str(recs_path),
        "--settlement-ledger", str(settlements_path),
        "--rules", str(rules_path),
        "--frozen-eval", str(FROZEN_EVAL),
        "--runner", str(BASE / "run_daily_portfolio_observation.sh"),
        "--scanner-status", str(scanner_path),
        "--pipeline-status", str(pipeline_path),
        "--preflight-note", str(preflight_path),
    ]

    json_result = subprocess.run(common + ["--format", "json", "--output", str(json_output)], cwd=BASE, capture_output=True, text=True, check=True)
    payload = json.loads(json_result.stdout)
    text_result = subprocess.run(common + ["--format", "text", "--output", str(text_output)], cwd=BASE, capture_output=True, text=True, check=True)
    md_result = subprocess.run(common + ["--format", "md", "--output", str(md_output)], cwd=BASE, capture_output=True, text=True, check=True)

    rebuilt_args = argparse.Namespace(
        signals_ledger=str(signals_path),
        recommendation_ledger=str(recs_path),
        settlement_ledger=str(settlements_path),
        rules=str(rules_path),
        frozen_eval=str(FROZEN_EVAL),
        min_settled=None,
        portfolio_review_settled=None,
        max_open=5,
        runner=str(BASE / "run_daily_portfolio_observation.sh"),
        scanner_status=str(scanner_path),
        pipeline_status=str(pipeline_path),
        preflight_note=str(preflight_path),
        format="json",
        output=None,
    )
    expected_payload = ptns.build_payload(rebuilt_args)
    if payload != expected_payload:
        raise AssertionError(f"{case['name']}: next_steps.json no longer matches a fresh rebuild from paper_trade_next_steps.py")
    expected_text = ptns.render_text(expected_payload)
    if text_output.read_text(encoding="utf-8") != expected_text or text_result.stdout != expected_text:
        raise AssertionError(f"{case['name']}: next_steps.txt no longer matches a fresh rebuild from paper_trade_next_steps.py")
    expected_md = ptns.render_md(expected_payload) + "\n"
    if md_output.read_text(encoding="utf-8") != expected_md or md_result.stdout != expected_md:
        raise AssertionError(f"{case['name']}: next_steps.md no longer matches a fresh rebuild from paper_trade_next_steps.py")

    if payload.get("valid_evidence_scope") != ptns.VALID_EVIDENCE_SCOPE:
        raise AssertionError(f"{case['name']}: next_steps.json is missing the source output valid_evidence_scope")
    boundary = payload.get("evidence_boundary")
    if (
        not isinstance(boundary, dict)
        or boundary.get("artifact_role") != "paper-trade next-steps source output"
        or boundary.get("not_current_day_scanner_result") is not True
        or boundary.get("not_live_paper_trade_ledger") is not True
        or boundary.get("not_settled_roi_evidence") is not True
        or boundary.get("not_promotion_readiness_evidence") is not True
        or boundary.get("not_live_profitability_evidence") is not True
        or boundary.get("not_real_money_evidence") is not True
        or boundary.get("baq_as_bel_substitution_allowed") is not False
    ):
        raise AssertionError(f"{case['name']}: next_steps.json evidence_boundary no longer pins source-output limits")
    if payload.get("evidence_boundary_text") != ptns.EVIDENCE_BOUNDARY_TEXT:
        raise AssertionError(f"{case['name']}: next_steps.json evidence_boundary_text drifted from source constant")

    if payload["state"] != case["state"]:
        raise AssertionError(f"{case['name']}: expected state {case['state']!r}, got {payload['state']!r}")
    assert_operator_read_gate_issue_flags(payload, case)
    assert_contains(payload["why"], case["why"], case["name"])
    assert_contains(payload["commands"][0], case["command_1"], case["name"])
    if "scanner_failure_operator_action" in case and payload.get("scanner_failure_operator_action") != case["scanner_failure_operator_action"]:
        raise AssertionError(
            f"{case['name']}: expected scanner_failure_operator_action "
            f"{case['scanner_failure_operator_action']!r}, got {payload.get('scanner_failure_operator_action')!r}"
        )
    if "scanner_failure_recheck_command" in case and payload.get("scanner_failure_recheck_command") != case["scanner_failure_recheck_command"]:
        raise AssertionError(
            f"{case['name']}: expected scanner_failure_recheck_command "
            f"{case['scanner_failure_recheck_command']!r}, got {payload.get('scanner_failure_recheck_command')!r}"
        )
    text_content = text_output.read_text(encoding="utf-8")
    md_content = md_output.read_text(encoding="utf-8")
    issue_flags_text = ptns.format_operator_read_gate_issue_flags(payload.get("operator_read_gate_issue_flags") or {})
    assert_contains(text_content, f"- State: {case['state']}", case["name"])
    assert_contains(text_content, case["why"], case["name"])
    assert_contains(md_content, f"- State: **{case['state']}**", case["name"])
    assert_contains(text_content, f"- Operator read-gate issue flags: {issue_flags_text}", case["name"])
    assert_contains(md_content, f"- Operator read-gate issue flags: `{issue_flags_text}`", case["name"])
    assert_contains(text_content, "- First statistical-read progress:", case["name"])
    assert_contains(text_content, "- Broader portfolio-review progress:", case["name"])
    assert_contains(md_content, "- First statistical-read progress:", case["name"])
    assert_contains(md_content, "- Broader portfolio-review progress:", case["name"])
    assert_contains(text_content, "- ROI coverage:", case["name"])
    assert_contains(md_content, "- ROI coverage:", case["name"])
    assert_contains(text_content, f"- valid_evidence_scope={ptns.VALID_EVIDENCE_SCOPE}", case["name"])
    assert_contains(text_content, f"- Evidence boundary: {ptns.EVIDENCE_BOUNDARY_TEXT}", case["name"])
    assert_contains(md_content, f"- `valid_evidence_scope={ptns.VALID_EVIDENCE_SCOPE}`", case["name"])
    assert_contains(md_content, f"- {ptns.EVIDENCE_BOUNDARY_TEXT}", case["name"])
    assert_scorecard_gate_source(
        payload,
        text_content,
        md_content,
        case["name"],
        expected_active_gate=case.get("expected_active_gate", "anchor_displacement"),
        expected_active_min_settled=case.get("expected_active_min_settled", 30),
        expected_active_gate_key=case.get(
            "expected_active_gate_key",
            "anchor_displacement_min_roi_complete_settled_observations",
        ),
    )
    for needle in case.get("text_needles", []):
        assert_contains(text_content, needle, case["name"])
    for needle in case.get("md_needles", []):
        assert_contains(md_content, needle, case["name"])
    recent_context = case.get("recent_context")
    if recent_context:
        assert_contains(str(payload.get("recent_run_context") or ""), recent_context, case["name"])
        assert_contains(text_content, recent_context, case["name"])
        assert_contains(md_content, recent_context, case["name"])
    for needle in case.get("must_contain", []):
        assert_contains(str(payload.get("recent_run_context") or ""), needle, case["name"])
        assert_contains(text_content, needle, case["name"])
        assert_contains(md_content, needle, case["name"])
    for needle in case.get("must_not_contain", []):
        recent_text = str(payload.get("recent_run_context") or "")
        if needle in recent_text or needle in text_content or needle in md_content:
            raise AssertionError(f"{case['name']}: expected not to find {needle!r} in next-steps outputs")

    return {
        "case": case["name"],
        "scenario": case.get("scenario"),
        "state": payload["state"],
        "why": payload["why"],
        "command_1": payload["commands"][0],
        "recent_run_context": payload.get("recent_run_context"),
        "operator_read_gate_issue_flags": payload.get("operator_read_gate_issue_flags"),
        "text_output": str(text_output.relative_to(BASE)),
        "md_output": str(md_output.relative_to(BASE)),
    }


def resolve_live_scanner_status_path(lane_dir: Path) -> Path | None:
    args = argparse.Namespace(
        scanner_status=str(lane_dir / "live_scan.status.json"),
        pipeline_status=str(lane_dir / "pipeline_status.json"),
    )
    pipeline = ptns.read_pipeline_payload(args)
    return ptns.resolve_scanner_status_path(args, pipeline)


def live_lane_dirs() -> list[Path]:
    lanes: list[Path] = []
    if not LIVE_RUNS_ROOT.exists():
        raise AssertionError(f"no live run folders found under {LIVE_RUNS_ROOT}")
    for run_root in sorted(p for p in LIVE_RUNS_ROOT.iterdir() if p.is_dir()):
        for lane_dir in sorted(p for p in run_root.iterdir() if p.is_dir()):
            if (lane_dir / "next_steps.txt").exists() and (lane_dir / "next_steps.md").exists():
                lanes.append(lane_dir)
    if not lanes:
        raise AssertionError(f"no live next-steps surfaces found under {LIVE_RUNS_ROOT}")
    return lanes


def validate_live_surfaces() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for lane_dir in live_lane_dirs():
        lane_name = lane_dir.name
        scanner_status_path = resolve_live_scanner_status_path(lane_dir)
        if scanner_status_path is None:
            raise AssertionError(f"could not resolve live scanner status sidecar for {lane_dir}")
        args = argparse.Namespace(
            signals_ledger=str(BASE / "paper_trades" / f"{lane_name}_paper_trade_signals.csv"),
            recommendation_ledger=str(BASE / "paper_trades" / f"{lane_name}_paper_trade_recommendations.csv"),
            settlement_ledger=str(BASE / "paper_trades" / f"{lane_name}_paper_trade_settlements.csv"),
            rules=str(BASE / f"{lane_name}_rules.json"),
            frozen_eval=str(FROZEN_EVAL),
            min_settled=None,
            portfolio_review_settled=None,
            max_open=5,
            runner=str(BASE / "run_daily_portfolio_observation.sh"),
            scanner_status=str(scanner_status_path),
            pipeline_status=str(lane_dir / "pipeline_status.json"),
            preflight_note=str(lane_dir.parent / "preflight_note.txt"),
            format="json",
            output=None,
        )
        payload = ptns.build_payload(args)
        expected_text = ptns.render_text(payload)
        expected_md = ptns.render_md(payload) + "\n"
        text_path = lane_dir / "next_steps.txt"
        md_path = lane_dir / "next_steps.md"
        if text_path.read_text(encoding="utf-8") != expected_text:
            raise AssertionError(f"live next_steps.txt drifted from the current source-layer rebuild: {text_path}")
        if md_path.read_text(encoding="utf-8") != expected_md:
            raise AssertionError(f"live next_steps.md drifted from the current source-layer rebuild: {md_path}")
        results.append({
            "case": f"live_surface_{lane_dir.parent.name}_{lane_name}",
            "scenario": "saved live next-steps surfaces match the current source-layer rebuild",
            "lane_dir": str(lane_dir.relative_to(BASE)),
            "text_output": str(text_path.relative_to(BASE)),
            "md_output": str(md_path.relative_to(BASE)),
            "state": payload["state"],
            "command_1": payload["commands"][0],
        })
    return results


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_output_paths(args.fixture_root, args.out_dir)
    scorecard_gates = read_scorecard_gate_minimums(args.scorecard_json)
    scorecard_guardrails = scorecard_no_artifact_guardrails(args.scorecard_json)

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for legacy in (
        FIXTURE_ROOT / "next_steps_fixture_validation.md",
        FIXTURE_ROOT / "next_steps_fixture_validation.json",
    ):
        legacy.unlink(missing_ok=True)

    fixture_results = [run_case(case) for case in CASES]
    live_surfaces = validate_live_surfaces()
    results = fixture_results + live_surfaces
    scratch = build_fixture_scratch_metadata()
    fixture_map = {row["case"]: row for row in fixture_results}
    if fixture_map["case_waiting_for_first_settled_races"].get("operator_read_gate_issue_flags") != expected_issue_flags():
        raise AssertionError("clean-empty next-steps fixture no longer preserves false operator read-gate issue flags")
    if fixture_map["case_rerun_live_check"].get("operator_read_gate_issue_flags") != expected_issue_flags():
        raise AssertionError("cache-only miss next-steps fixture no longer preserves false operator read-gate issue flags")
    if fixture_map["case_generic_scanner_error_detail"].get("operator_read_gate_issue_flags") != expected_issue_flags(
        api_access=True,
        scanner_boundary=True,
    ):
        raise AssertionError("API-access scanner-failure next-steps fixture no longer preserves true/true/false issue flags")
    if fixture_map["case_api_access_stale_cache_fallback_route"].get("operator_read_gate_issue_flags") != expected_issue_flags(
        api_access=True,
        scanner_boundary=True,
        stale_cache=True,
    ):
        raise AssertionError("API-access stale-cache next-steps fixture no longer preserves true/true/true issue flags")
    suite_read = (
        "next-steps helper still keeps settlement-first, repair-ROI-coverage, refresh-artifacts, missing scan-output refresh, rerun-live, limited-cache, max-races-limited target-coverage, explicit scanner/API-access-failure refresh, explicit recommender/logger pipeline-failure, waiting-for-first-settled, "
        "collecting-sample, and decision-grade-review states distinct, now preserving distinct missing scan-output plus missing/empty/unreadable/invalid-shape refresh-artifact wording for scan-output, pipeline, and scanner status sidecars plus pipeline-recorded empty/unreadable/invalid-shape scanner-status states when copied surfaces lack the physical scanner sidecar, trusting the structured preflight JSON snapshot first when deciding whether active-target cache misses should promote rerun-live guidance and when a saved preflight JSON survives with its sibling text note missing or blank, while also using the pipeline sidecar's structured observation-scope/reason fields so partial-cache runs with surviving activity do not get mislabeled as limited-cache empty days, using max-races limited-coverage metadata to recommend a higher cap before reading no-hit scans as quiet, and recovering lane-local, run-root, or project-relative pipeline-declared relocated scanner-status sidecars when the default live_scan.status.json path is absent, including when saved live next-steps surfaces are rebuilt for drift checks, surfacing first statistical-read and broader portfolio-review milestone progress plus explicit scorecard-sourced decision-gate metadata from forward_evidence_scorecard.json decision_gate_minimums and explicit missing/malformed/timestamp ROI-complete repair visibility directly in the next-steps surface, with latest-run context now preserving last-completed-stage plus pre-error scanner/recommendation detail for pipeline failures and the direct validator report now published at the standard next-steps validation path with exact valid_evidence_scope=paper_trade_next_step_action_routing_only; "
        "generic non-cache scanner failures now keep the upstream scanner_error/error detail in latest-run context and route to CHECK SCANNER FAILURE refresh guidance, with API-access stale-cache fallback count/kind/error context preserved in both the why line and latest-run context, and JSON `operator_read_gate_issue_flags` plus top-level issue booleans now pinned for clean-empty, cache-only miss, API-access scanner failure, and API-access stale-cache fallback states, with matching text/markdown issue-flag lines so an operational failure such as a 403 remains visible without becoming quiet-day, sample-collection, or performance evidence; "
        "source JSON/text/markdown outputs now publish `valid_evidence_scope`, `evidence_boundary`, and `evidence_boundary_text` so next-step command guidance cannot be overread as scanner evidence, ledger evidence, settled ROI, promotion readiness, live profitability, real-money support, or BAQ-as-BEL evidence; "
        "Phase 8 shadow first-read status now carries an explicit review floor rather than a promotion entitlement caution in JSON/text/markdown, with malformed scorecard gates rejected before fixture/report artifacts, and with project-local fixture scratch metadata now published as a structured guardrail, while preserving the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that routing cleanliness, refresh/rerun guidance, repair prompts, sample-readiness wording, and review-floor cautions do not advance; next steps: operator action-routing surface, not new forward edge evidence by itself"
    )

    child_checks = [
        *scorecard_guardrails,
        {
            "check": "fixture_state_ladder_stays_covered",
            "status": "pass",
            "detail": "direct fixtures still cover the main next-steps state ladder from settlement-first and repair-ROI-coverage through refresh-artifact recovery for missing scan-output artifacts, missing/empty/unreadable/invalid-shape sidecars, plus pipeline-recorded empty/unreadable/invalid-shape scanner-status states, rerun-live, limited-cache, max-races-limited target-coverage, scanner/API-access failure including stale-cache fallback metadata, pipeline-failure, collecting-sample, and decision-grade branches, including missing-text and blank-text saved-preflight fallback in the active-target rerun-live branch",
        },
        {
            "check": "latest_run_context_and_pipeline_failure_detail_stay_pinned",
            "status": "pass",
            "detail": "mixed-state branches still pin latest-run context explicitly, including upstream scanner-error detail, API-access stale-cache fallback context, and refresh routing for generic scanner/API-access failures plus last-completed-stage and pre-error scanner/recommendation detail for post-scan pipeline failures",
        },
        {
            "check": "source_json_next_steps_publish_operator_read_gate_issue_flags",
            "status": "pass",
            "detail": "every fixture next_steps.json now publishes boolean has_api_access_failure_context, has_scanner_failure_boundary, has_stale_cache_fallback_context, and nested operator_read_gate_issue_flags fields, and every fixture text/markdown surface renders the same issue-flag line; direct fixtures pin clean-empty and cache-only miss as false/false/false, API-access scanner failure as true/true/false, and API-access stale-cache fallback as true/true/true",
        },
        {
            "check": "source_outputs_publish_next_steps_evidence_boundary_fields",
            "status": "pass",
            "detail": "every fixture next_steps.json now publishes valid_evidence_scope, evidence_boundary, and evidence_boundary_text, and every fixture text/markdown output renders the same source-level evidence boundary line before action routing details",
        },
        {
            "check": "direct_validation_report_exposes_next_steps_valid_scope",
            "status": "pass",
            "detail": "the direct next-steps validator report now exposes the raw valid_evidence_scope line and keeps green routing checks classified as operator action-routing metadata only",
        },
        {
            "check": "saved_outputs_match_source_layer_rebuilds",
            "status": "pass",
            "detail": "fixture JSON, text, and markdown outputs stay pinned to fresh build_payload/render_text/render_md output from paper_trade_next_steps.py, including scorecard-sourced decision-gate metadata from forward_evidence_scorecard.json decision_gate_minimums",
        },
        {
            "check": "saved_live_drift_checks_recover_relocated_scanner_sidecars",
            "status": "pass",
            "detail": "saved live next_steps drift checks now rebuild through lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars instead of assuming live_scan.status.json still exists",
        },
        {
            "check": "next_steps_explicitly_stays_action_routing_not_new_edge_evidence",
            "status": "pass",
            "detail": "the direct validator summary still says plainly that next_steps is an operator action-routing surface, not new forward edge evidence by itself, and that Phase 8 shadow first-read status is a review floor rather than a promotion entitlement",
        },
        {
            "check": "next_steps_preserves_scorecard_gate_boundary",
            "status": "pass",
            "detail": "the next-steps validator now publishes the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite while saying routing cleanliness, refresh/rerun guidance, repair prompts, sample-readiness wording, and review-floor cautions do not count toward those gates",
        },
        {
            "check": "fixture_scratch_metadata_published",
            "status": "pass",
            "detail": "the next-steps validator JSON publishes project-local fixture scratch metadata so parent rollups can verify the isolated fixture root without parsing markdown prose",
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
        raise AssertionError("next-steps scorecard gate boundary no longer matches forward_evidence_scorecard.json")
    if (
        scratch.get("fixture_root_relative") != "out/status_validation/next_steps_fixture"
        or scratch.get("fixture_root_is_project_local") is not True
        or scratch.get("case_roots_cleared_by_setup_case") is not True
    ):
        raise AssertionError("next-steps fixture scratch metadata no longer proves a project-local cleared fixture root")

    lines = [
        "# Paper-Trade Next Steps Validation",
        "",
        "This report validates `paper_trade_next_steps.py` directly against representative fixture cases under `out/status_validation/next_steps_fixture/`, while publishing the direct validator readout under `out/status_validation/paper_trade_next_steps/`.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Fixture root: `{FIXTURE_ROOT.relative_to(BASE)}`",
        f"- Direct report path: `{REPORT_MD.relative_to(BASE)}`",
        "",
        "## Fixture cases",
        "",
        "| Case | Scenario | Result |",
        "|---|---|---|",
        *[
            f"| `{row['case']}` | {row['scenario']} | {row['state']} -> `{row['command_1']}` |"
            for row in fixture_results
        ],
        "",
        "## Live current surfaces",
        "",
        *[
            f"- `{row['lane_dir']}` -> `{row['text_output']}` and `{row['md_output']}` ({row['state']} -> `{row['command_1']}`)"
            for row in live_surfaces
        ],
        "",
        "## Current Read",
        "",
        f"- Suite read: {suite_read}",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
        f"- valid_evidence_scope={EVIDENCE_BOUNDARY['valid_evidence_scope']}",
        f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
        "- Boundary: next-steps validator cleanliness is action-routing metadata only, not new forward evidence, not a live paper-trade ledger, not a current-day scanner result, not settled ROI, not live profitability, not promotion readiness, and not real-money evidence.",
        "- Non-goals: do not treat refresh/rerun guidance, settlement-repair prompts, sample-readiness wording, scorecard-gate visibility, Phase 8 review-floor cautions, saved-live rebuild cleanliness, or green validators as ROI-complete observations, profitability evidence, promotion support, or real-money support.",
        f"- Source output fields: `valid_evidence_scope={ptns.VALID_EVIDENCE_SCOPE}`, JSON `evidence_boundary`, and `evidence_boundary_text` are now pinned directly on `next_steps.json` and rendered in text/markdown output.",
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
        "## Validation result",
        "",
        "- The next-steps helper still has direct source-layer fixture coverage for its main state transitions instead of relying only on downstream wrapper or top-card tests.",
        "- The validator still pins the `Latest run context` line directly for mixed-state branches like signals-without-bet, cache-only miss, missing scan-output artifact, partial-cache empty, partial-cache with surviving activity, max-races-limited target coverage, explicit API-access stale-cache fallback, explicit recommender/logger pipeline failure, and clean-empty observation days, and now also requires last-completed-stage plus pre-error scanner/recommendation detail for post-scan pipeline failures.",
        "- Each fixture case now requires the saved JSON, text, and markdown outputs to match fresh source-layer rebuilds from `paper_trade_next_steps.py`, not just selected state and wording checks, and also requires the 30 / 20 / 100 scorecard-sourced decision-gate metadata plus the no-BAQ-as-BEL real-money prerequisite to remain visible in text and markdown.",
        "- The validator now also fails if any saved live `next_steps.txt` or `next_steps.md` surface under `out/daily_portfolio_runs/` drifts from the current source-layer rebuild, and those live rebuilds now recover lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars before regenerating guidance.",
        "- This pins the operator guidance across settlement-first, repair-ROI-coverage, stale-artifact recovery with distinct missing scan-output artifact wording, missing/empty/unreadable/invalid-shape sidecar wording, plus pipeline-recorded empty/unreadable/invalid-shape scanner-status state preservation when copied surfaces lack the physical scanner sidecar, cache-miss recovery, partial-cache recovery, max-races-limited target-coverage recovery, explicit scanner/API-access failure recovery with stale-cache fallback count/kind/error context, explicit recommender/logger pipeline-failure recovery, early observation, collecting-sample, and decision-grade states, while also pinning the structured-preflight active-target branch, the saved-preflight JSON fallback branch when the sibling text note is missing or blank, the structured observation-scope/reason partial-cache-with-activity branch, recovery of lane-local, run-root, or project-relative pipeline-declared relocated scanner-status sidecars, post-scan pipeline-failure context recovery, explicit missing/malformed/timestamp ROI-complete repair visibility, plus first statistical-read / broader portfolio-review milestone progress and scorecard-sourced gate-source visibility in both fixtures and saved live lane surfaces.",
        "- The Phase 8 shadow fixture now proves that a 20/20 first-read state carries the review floor rather than a promotion entitlement caution in JSON, text, and markdown, so `DECISION-GRADE REVIEW` cannot be read as an automatic Phase 8 promotion cue.",
        "- The validator JSON now also publishes fourteen explicit structured guardrails, including malformed-scorecard no-artifact checks for non-positive Phase 8 and real-money copied gate floors, source JSON/text/markdown operator-read-gate issue flags, source output evidence-boundary fields, direct validator valid_evidence_scope exposure, the scorecard-sourced gate boundary, and project-local fixture scratch metadata, so parent rollups can verify the saved-live drift rebuild contract, action-routing evidence-boundary language, scorecard-gate boundary, and isolated fixture root directly instead of inferring them only from totals plus a summary string.",
        "",
    ]
    payload = {
        "suite_status": "pass",
        "valid_evidence_scope": ptns.VALID_EVIDENCE_SCOPE,
        "total_fixture_scenarios": len(fixture_results),
        "total_checks": len(results),
        "check_count": len(results),
        "fixture_case_count": len(fixture_results),
        "live_surface_checks": len(live_surfaces),
        "results": results,
        "child_check_count": len(child_checks),
        "child_checks": child_checks,
        "summary": {
            "suite_read": suite_read,
        },
        "scratch": scratch,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "fixture_root": str(FIXTURE_ROOT.relative_to(BASE)),
            "report_path": str(REPORT_MD.relative_to(BASE)),
        },
    }

    write_text(REPORT_MD, "\n".join(lines))
    write_text(REPORT_JSON, json.dumps(payload, indent=2) + "\n")

    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    for row in results:
        print(f"PASS {row['case']}: {row['state']} -> {row['command_1']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
