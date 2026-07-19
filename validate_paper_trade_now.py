#!/usr/bin/env python3
"""
Fixture-driven validation for paper_trade_now.py.

Purpose:
- keep the single-action priority order reproducible as real paper-trade data arrives
- validate the real CLI against synthetic cases without touching live ledgers
- cover the most important operator branches: settle-first, decision-grade review, stale-run refresh, cache recovery, missing-vs-empty-vs-unreadable pipeline/scanner artifact recovery, honest no-target stand-down, and unknown-calendar ambiguity
"""

from __future__ import annotations

import csv
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import paper_trade_now as source_now

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "paper_trade_now.py"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "paper_trade_now_fixture"
REPORT_DIR = BASE / "out" / "status_validation" / "paper_trade_now"
REPORT_MD = REPORT_DIR / "paper_trade_now_validation.md"
REPORT_JSON = REPORT_DIR / "paper_trade_now_validation.json"
LIVE_TXT = BASE / "PAPER_TRADE_NOW.txt"
LIVE_MD = BASE / "PAPER_TRADE_NOW.md"
LIVE_JSON = BASE / "PAPER_TRADE_NOW.json"
FROZEN_EVAL = BASE / "frozen_portfolio_eval_summary.csv"
REBUILD_COMMAND = "python3 validate_paper_trade_now.py"
PRIMARY_RULES = BASE / "phase7_current_paper_rules.json"
SHADOW_RULES = BASE / "phase8_shadow_rules.json"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade right-now validator",
    "valid_evidence_scope": source_now.RIGHT_NOW_VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "isolated paper_trade_now fixture run folders",
        "saved live PAPER_TRADE_NOW text/markdown/JSON surfaces",
        "paper_trade_now.py",
        "forward_evidence_scorecard.json decision_gate_minimums",
    ],
    "valid_use": "operator action-priority validation for the right-now top card",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "right_now_validator_passes_are_operator_routing_metadata_only": True,
    "non_goals": [
        "do not treat right-now action routing as ROI-complete observations",
        "do not treat stale snapshot context or quick-read visibility as current-day performance evidence",
        "do not promote OP_REFINED_K7 or Phase 8 from top-card validation cleanliness",
        "do not substitute BAQ for BEL",
        "do not treat right-now validation as real-money evidence",
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


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


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
            "right-now action routing, stale-snapshot context, quick-read visibility, active gate lines, "
            "and green validator passes do not count toward anchor-displacement, Phase 8 "
            "promotion-review, or real-money discussion gates"
        ),
    }


def guardrail(condition: bool, check: str, detail: str) -> dict[str, str]:
    if not condition:
        raise AssertionError(f"{check}: {detail}")
    return {"check": check, "status": "pass", "detail": detail}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--fixture-root", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=REPORT_DIR)
    return parser.parse_args(argv)


def configure_output_paths(fixture_root: Path, out_dir: Path) -> None:
    global FIXTURE_ROOT, REPORT_DIR, REPORT_MD, REPORT_JSON
    FIXTURE_ROOT = fixture_root
    REPORT_DIR = out_dir
    REPORT_MD = REPORT_DIR / "paper_trade_now_validation.md"
    REPORT_JSON = REPORT_DIR / "paper_trade_now_validation.json"


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
    return guardrail(True, check_name, detail)


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
            check_name="scorecard_boolean_gate_floor_fails_before_right_now_artifacts",
            detail=(
                "a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before "
                "the right-now validator creates fixture roots or report artifacts"
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
            check_name="scorecard_nonpositive_phase8_gate_floor_fails_before_right_now_artifacts",
            detail=(
                "a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails before "
                "the right-now validator creates fixture roots or report artifacts"
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
            check_name="scorecard_nonpositive_real_money_gate_floor_fails_before_right_now_artifacts",
            detail=(
                "a non-positive real-money discussion floor in forward_evidence_scorecard.json fails before "
                "the right-now validator creates fixture roots or report artifacts"
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
            check_name="scorecard_missing_no_baq_fails_before_right_now_artifacts",
            detail=(
                "a scorecard real-money gate that drops the no BAQ-as-BEL prerequisite fails before "
                "the right-now validator creates fixture roots or report artifacts"
            ),
        ),
    ]


def empty_ledgers(case_root: Path) -> None:
    paper_trades = case_root / "paper_trades"
    for lane in ("phase7_current_paper", "phase8_shadow"):
        write_csv(paper_trades / f"{lane}_paper_trade_signals.csv", SIGNAL_FIELDS, [])
        write_csv(paper_trades / f"{lane}_paper_trade_recommendations.csv", RECOMMENDATION_FIELDS, [])
        write_csv(paper_trades / f"{lane}_paper_trade_settlements.csv", SETTLEMENT_FIELDS, [])


def signal_row(idx: int, rule_id: str, track: str, race_number: int, estimated_cost: float) -> dict[str, Any]:
    card_name = {
        "OP": "Oaklawn Park",
        "CD": "Churchill Downs",
        "KEE": "Keeneland",
    }.get(track, track)
    return {
        "signal_key": f"{rule_id.lower()}_{idx:03d}",
        "scan_ts": f"2026-05-01T1{idx % 10}:00:00",
        "rule_id": rule_id,
        "track": track,
        "card_name": card_name,
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


def settlement_row(signal: dict[str, Any], settlement_status: str, outcome: str, actual_return: float | None = None,
                   *, actual_cost_override: str | None = None,
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
            if settled_ts_override is not None
            else "2026-05-01T19:30:00" if settlement_status == "settled" else ""
        ),
        "notes": "fixture",
    }


def pipeline_status(observation_result: str, hits: int = 0, recs: int = 0, bets: int = 0,
                    cache_only: bool = False, scanner_result: str | None = None,
                    scanner_error: str | None = None, result: str = "ok",
                    stage: str = "done", error_type: str | None = None,
                    error: str | None = None, observation_reason: str | None = None,
                    api_failure_operator_action: str | None = None,
                    api_failure_recheck_command: str | None = None,
                    scanner_api_access_failure: bool | None = None,
                    scanner_http_status: int | None = None,
                    scanner_api_failure_class: str | None = None,
                    scanner_api_failure_valid_scope: str | None = None,
                    scanner_api_failure_boundary: str | None = None,
                    stale_cache_fallback_applied: bool | None = None,
                    stale_cache_fallback_count: int | None = None,
                    stale_cache_fallback_kind: str | None = None,
                    stale_cache_fallback_error_type: str | None = None,
                    stale_cache_fallback_error: str | None = None) -> dict[str, Any]:
    payload = {
        "result": result,
        "observation_result": observation_result,
        "scan_hit_count": hits,
        "recommendation_count": recs,
        "bet_count": bets,
        "cache_only": cache_only,
        "stage": stage,
    }
    if scanner_result is not None:
        payload["scanner_result"] = scanner_result
    if scanner_error is not None:
        payload["scanner_error"] = scanner_error
    if api_failure_operator_action is not None:
        payload["scanner_api_failure_operator_action"] = api_failure_operator_action
    if api_failure_recheck_command is not None:
        payload["scanner_api_failure_recheck_command"] = api_failure_recheck_command
    if scanner_api_access_failure is not None:
        payload["scanner_api_access_failure"] = scanner_api_access_failure
    if scanner_http_status is not None:
        payload["scanner_http_status"] = scanner_http_status
    if scanner_api_failure_class is not None:
        payload["scanner_api_failure_class"] = scanner_api_failure_class
    if scanner_api_failure_valid_scope is not None:
        payload["scanner_api_failure_valid_scope"] = scanner_api_failure_valid_scope
    if scanner_api_failure_boundary is not None:
        payload["scanner_api_failure_boundary"] = scanner_api_failure_boundary
    if stale_cache_fallback_applied is not None:
        payload["scanner_stale_cache_fallback_applied"] = stale_cache_fallback_applied
    if stale_cache_fallback_count is not None:
        payload["scanner_stale_cache_fallback_count"] = stale_cache_fallback_count
    if stale_cache_fallback_kind is not None:
        payload["scanner_stale_cache_fallback_kind"] = stale_cache_fallback_kind
    if stale_cache_fallback_error_type is not None:
        payload["scanner_stale_cache_fallback_error_type"] = stale_cache_fallback_error_type
    if stale_cache_fallback_error is not None:
        payload["scanner_stale_cache_fallback_error"] = stale_cache_fallback_error
    if error_type is not None:
        payload["error_type"] = error_type
    if error is not None:
        payload["error"] = error
    if observation_reason is not None:
        payload["observation_reason"] = observation_reason
    return payload


def scanner_status(result: str, *, cache_only: bool = False, error: str | None = None,
                   partial_cache: bool = False, missing_race_detail_cache_skips: int = 0,
                   api_failure_operator_action: str | None = None,
                   api_failure_recheck_command: str | None = None,
                   api_access_failure: bool | None = None,
                   http_status: int | None = None,
                   api_failure_class: str | None = None,
                   api_failure_valid_scope: str | None = None,
                   api_failure_boundary: str | None = None,
                   stale_cache_fallback_applied: bool | None = None,
                   stale_cache_fallback_count: int | None = None,
                   stale_cache_fallback_kind: str | None = None,
                   stale_cache_fallback_error_type: str | None = None,
                   stale_cache_fallback_error: str | None = None) -> dict[str, Any]:
    payload = {
        "result": result,
        "cache_only": cache_only,
        "partial_cache": partial_cache,
        "missing_race_detail_cache_skips": missing_race_detail_cache_skips,
        "card_count": 2,
        "race_count": 18,
    }
    if error is not None:
        payload["error"] = error
    if api_failure_operator_action is not None:
        payload["api_failure_operator_action"] = api_failure_operator_action
    if api_failure_recheck_command is not None:
        payload["api_failure_recheck_command"] = api_failure_recheck_command
    if api_access_failure is not None:
        payload["api_access_failure"] = api_access_failure
    if http_status is not None:
        payload["http_status"] = http_status
    if api_failure_class is not None:
        payload["api_failure_class"] = api_failure_class
    if api_failure_valid_scope is not None:
        payload["api_failure_valid_scope"] = api_failure_valid_scope
    if api_failure_boundary is not None:
        payload["api_failure_boundary"] = api_failure_boundary
    if stale_cache_fallback_applied is not None:
        payload["stale_cache_fallback_applied"] = stale_cache_fallback_applied
    if stale_cache_fallback_count is not None:
        payload["stale_cache_fallback_count"] = stale_cache_fallback_count
    if stale_cache_fallback_kind is not None:
        payload["stale_cache_fallback_kind"] = stale_cache_fallback_kind
    if stale_cache_fallback_error_type is not None:
        payload["stale_cache_fallback_error_type"] = stale_cache_fallback_error_type
    if stale_cache_fallback_error is not None:
        payload["stale_cache_fallback_error"] = stale_cache_fallback_error
    return payload


def preflight(has_targets: bool, note: str, relevant_tracks: list[str] | None = None,
              shadow_tracks: list[str] | None = None, excluded_tracks: list[str] | None = None) -> dict[str, Any]:
    excluded_tracks = excluded_tracks or []
    return {
        "date": "2026-05-01",
        "checked_at": "2026-05-01 12:00",
        "api_ok": True,
        "has_targets": has_targets,
        "relevant_tracks": relevant_tracks or [],
        "shadow_tracks": shadow_tracks or [],
        "excluded_tracks": excluded_tracks,
        "excluded_track_count": len(excluded_tracks),
        "total_cards": 18,
        "error": None,
        "note": note,
    }


def setup_case(case_name: str, run_date: str, preflight_payload: dict[str, Any],
               primary_status: dict[str, Any], shadow_status: dict[str, Any],
               primary_signals: list[dict[str, Any]], primary_settlements: list[dict[str, Any]],
               shadow_signals: list[dict[str, Any]] | None = None,
               shadow_settlements: list[dict[str, Any]] | None = None,
               primary_scanner_status: dict[str, Any] | None = None,
               shadow_scanner_status: dict[str, Any] | None = None,
               primary_scanner_relpath: str | None = None,
               shadow_scanner_relpath: str | None = None) -> tuple[Path, Path]:
    case_root = FIXTURE_ROOT / case_name
    if case_root.exists():
        shutil.rmtree(case_root)
    empty_ledgers(case_root)

    paper_trades = case_root / "paper_trades"
    write_csv(paper_trades / "phase7_current_paper_paper_trade_signals.csv", SIGNAL_FIELDS, primary_signals)
    write_csv(paper_trades / "phase7_current_paper_paper_trade_recommendations.csv", RECOMMENDATION_FIELDS, [])
    write_csv(paper_trades / "phase7_current_paper_paper_trade_settlements.csv", SETTLEMENT_FIELDS, primary_settlements)
    write_csv(paper_trades / "phase8_shadow_paper_trade_signals.csv", SIGNAL_FIELDS, shadow_signals or [])
    write_csv(paper_trades / "phase8_shadow_paper_trade_recommendations.csv", RECOMMENDATION_FIELDS, [])
    write_csv(paper_trades / "phase8_shadow_paper_trade_settlements.csv", SETTLEMENT_FIELDS, shadow_settlements or [])

    run_root = case_root / "out" / "daily_portfolio_runs" / run_date
    primary_scanner_path = run_root / (primary_scanner_relpath or "phase7_current_paper/live_scan.status.json")
    shadow_scanner_path = run_root / (shadow_scanner_relpath or "phase8_shadow/live_scan.status.json")
    write_text(run_root / "preflight_note.txt", preflight_payload["note"] + "\n")
    write_json(run_root / "preflight_note.json", preflight_payload)
    primary_status_payload = dict(primary_status)
    shadow_status_payload = dict(shadow_status)
    if primary_scanner_relpath and primary_scanner_status is not None and not str(primary_status_payload.get("scanner_status_path") or "").strip():
        primary_status_payload["scanner_status_path"] = str(primary_scanner_path)
    if shadow_scanner_relpath and shadow_scanner_status is not None and not str(shadow_status_payload.get("scanner_status_path") or "").strip():
        shadow_status_payload["scanner_status_path"] = str(shadow_scanner_path)
    write_json(run_root / "phase7_current_paper" / "pipeline_status.json", primary_status_payload)
    write_json(run_root / "phase8_shadow" / "pipeline_status.json", shadow_status_payload)
    if primary_scanner_status is not None:
        write_json(primary_scanner_path, primary_scanner_status)
    if shadow_scanner_status is not None:
        write_json(shadow_scanner_path, shadow_scanner_status)
    write_text(run_root / "daily_summary.txt", f"Fixture daily summary for {case_name}.\n")
    write_text(
        case_root / "out" / "paper_trade_settlement_audit.md",
        "# Fixture settlement audit\n\n- This fixture audit is a ledger-completeness / ROI-coverage audit only, not new forward evidence by itself.\n",
    )
    write_json(
        case_root / "out" / "paper_trade_settlement_audit.json",
        {
            "artifact_status": "pass",
            "summary": {
                "evidence_boundary": "This fixture audit is a ledger-completeness / ROI-coverage audit only, not new forward evidence by itself.",
            },
            "lanes": [
                {
                    "name": "primary",
                    "promotion_gate": {
                        "scope": "lane_total_first_read",
                        "gate_read": "Primary first-read gate is lane-total: 30 ROI-complete settled row(s) before a first read and 100 before broader portfolio review; audit cleanliness still is not profit proof.",
                        "rule_progress": [
                            {"rule_id": "OP_DURABLE_K7", "roi_complete_settled_rows": 0},
                            {"rule_id": "CD_CORE_K8", "roi_complete_settled_rows": 0},
                        ],
                    },
                },
                {
                    "name": "shadow",
                    "promotion_gate": {
                        "scope": "per_rule_shadow_watch",
                        "min_roi_complete_settled_per_rule": 20,
                        "gate_read": "Shadow/watch phase8_promotion_review gate is per-rule: every expected shadow rule needs 20 ROI-complete settled row(s) before review; the 20-row count is a review floor, not a promotion entitlement; lane totals alone do not promote OP_REFINED_K7 or any other Phase 8 pocket; scorecard tiers remain binding (forward_evidence_scorecard.json); negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion; weakest current rule coverage is 0/20.",
                        "rule_progress": [
                            {"rule_id": "OP_REFINED_K7", "roi_complete_settled_rows": 0, "promotion_progress": "0/20 (0.0%)", "promotion_ready": False, "scorecard_tier": "WATCH"},
                            {"rule_id": "AQU_K9", "roi_complete_settled_rows": 0, "promotion_progress": "0/20 (0.0%)", "promotion_ready": False, "scorecard_tier": "SKIP"},
                            {"rule_id": "SA_K9", "roi_complete_settled_rows": 0, "promotion_progress": "0/20 (0.0%)", "promotion_ready": False, "scorecard_tier": "WATCH"},
                            {"rule_id": "KEE_K9", "roi_complete_settled_rows": 0, "promotion_progress": "0/20 (0.0%)", "promotion_ready": False, "scorecard_tier": "WATCH"},
                            {"rule_id": "CD_REFINED_K9", "roi_complete_settled_rows": 0, "promotion_progress": "0/20 (0.0%)", "promotion_ready": False, "scorecard_tier": "SKIP"},
                            {"rule_id": "DMR_FALL_K7", "roi_complete_settled_rows": 0, "promotion_progress": "0/20 (0.0%)", "promotion_ready": False, "scorecard_tier": "WATCH"},
                        ],
                        "promotion_ready": False,
                    },
                },
            ],
        },
    )
    return case_root, run_root


def assert_action_priority_contract(payload: dict[str, Any], text_output: str, md_output: str, label: str) -> None:
    if payload.get("valid_evidence_scope") != source_now.RIGHT_NOW_VALID_EVIDENCE_SCOPE:
        raise AssertionError(f"{label}: JSON payload lost the right-now valid_evidence_scope")
    if payload.get("evidence_boundary") != source_now.RIGHT_NOW_EVIDENCE_BOUNDARY:
        raise AssertionError(f"{label}: JSON payload lost the machine-readable right-now evidence boundary")
    if payload.get("action_priority_contract") != source_now.RIGHT_NOW_ACTION_PRIORITY_CONTRACT:
        raise AssertionError(f"{label}: JSON payload lost the machine-readable action-priority contract")
    scope_line = f"valid_evidence_scope={source_now.RIGHT_NOW_VALID_EVIDENCE_SCOPE}"
    if f"- {scope_line}" not in text_output:
        raise AssertionError(f"{label}: text output lost the visible right-now valid_evidence_scope line")
    if f"- `{scope_line}`" not in md_output:
        raise AssertionError(f"{label}: markdown output lost the visible right-now valid_evidence_scope line")

    boundary = payload["evidence_boundary"]
    for flag in (
        "not_new_forward_evidence",
        "not_settled_roi_evidence",
        "not_live_profitability_evidence",
        "not_promotion_readiness_evidence",
        "not_anchor_displacement_evidence",
        "not_real_money_evidence",
        "decision_gate_advancement_requires_roi_complete_settlements",
    ):
        if boundary.get(flag) is not True:
            raise AssertionError(f"{label}: evidence_boundary.{flag} is no longer true")
    boundary_text = str(boundary.get("boundary_text") or "")
    for snippet in (
        "single-action operator top card",
        "not new forward evidence",
        "settled ROI evidence",
        "live profitability evidence",
        "promotion readiness evidence",
        "anchor-displacement evidence",
        "real-money evidence",
    ):
        if snippet not in boundary_text:
            raise AssertionError(f"{label}: evidence boundary text dropped {snippet!r}")

    contract = payload["action_priority_contract"]
    if contract.get("primary_action_field") != "best_action" or contract.get("freshness_field") != "run_freshness":
        raise AssertionError(f"{label}: action-priority contract no longer points consumers to best_action plus run_freshness")
    if "active_decision_gates" not in contract.get("source_fields", []) or "live_hierarchy" not in contract.get("source_fields", []):
        raise AssertionError(f"{label}: action-priority contract lost gate/hierarchy source-field visibility")

    freshness = payload.get("run_freshness") if isinstance(payload.get("run_freshness"), dict) else {}
    state = freshness.get("freshness_state")
    valid_states = {"current_run_date", "stale_past_run", "future_run_date", "unknown_run_date"}
    if state not in valid_states:
        raise AssertionError(f"{label}: run_freshness.freshness_state is missing or invalid: {state!r}")
    if (state == "current_run_date") == bool(freshness.get("is_stale")):
        raise AssertionError(f"{label}: run_freshness.freshness_state and is_stale disagree")
    if not str(freshness.get("summary") or "").strip():
        raise AssertionError(f"{label}: run_freshness.summary must stay non-empty for operator readability")
    expected_text_state = f"- Freshness state: {state}"
    expected_md_state = f"- Freshness state: `{state}`"
    if expected_text_state not in text_output:
        raise AssertionError(f"{label}: text output dropped the structured freshness state line")
    if expected_md_state not in md_output:
        raise AssertionError(f"{label}: markdown output dropped the structured freshness state line")

    expected_contract_line = f"- Action contract: {source_now.RIGHT_NOW_ACTION_CONTRACT_TEXT}"
    if expected_contract_line not in text_output:
        raise AssertionError(f"{label}: text output dropped the action-priority contract line")
    if expected_contract_line not in md_output:
        raise AssertionError(f"{label}: markdown output dropped the action-priority contract line")

    read_gate = payload.get("operator_read_gate")
    if not isinstance(read_gate, dict):
        raise AssertionError(f"{label}: JSON payload lost the machine-readable operator_read_gate")
    if read_gate.get("valid_use") != "operator instruction/evidence-read gating only":
        raise AssertionError(f"{label}: operator_read_gate.valid_use drifted")
    for flag in source_now.OPERATOR_READ_GATE_ISSUE_FLAGS:
        if not isinstance(read_gate.get(flag), bool):
            raise AssertionError(f"{label}: operator_read_gate.{flag} is no longer a boolean")
    for flag in (
        "not_forward_performance_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_bankroll_guidance",
        "not_real_money_evidence",
    ):
        if read_gate.get(flag) is not True:
            raise AssertionError(f"{label}: operator_read_gate.{flag} is no longer true")
    for flag in (
        "current_top_card_counts_as_no_target_evidence",
        "current_top_card_counts_as_clean_empty_evidence",
        "current_top_card_counts_as_bet_readiness_evidence",
        "current_top_card_counts_as_settled_roi_evidence",
    ):
        if read_gate.get(flag) is not False:
            raise AssertionError(f"{label}: operator_read_gate.{flag} is no longer false")
    gate_read = str(read_gate.get("read") or "")
    if not gate_read:
        raise AssertionError(f"{label}: operator_read_gate.read is empty")
    expected_gate_line = f"- Operator read gate: {gate_read}"
    if expected_gate_line not in text_output:
        raise AssertionError(f"{label}: text output dropped the operator read gate line")
    if expected_gate_line not in md_output:
        raise AssertionError(f"{label}: markdown output dropped the operator read gate line")
    expected_issue_line = f"- Operator read-gate issue flags: {source_now.operator_issue_flags_line(read_gate)}"
    expected_md_issue_line = f"- Operator read-gate issue flags: {source_now.operator_issue_flags_line(read_gate, markdown=True)}"
    if expected_issue_line not in text_output:
        raise AssertionError(f"{label}: text output dropped the operator read-gate issue flags line")
    if expected_md_issue_line not in md_output:
        raise AssertionError(f"{label}: markdown output dropped the operator read-gate issue flags line")


def run_case(case_name: str, case_root: Path, run_root: Path, expected_headline: str,
             expected_timing: str, expected_command_contains: str,
             expected_day_bucket: str | None = None,
             expected_why_contains: str | None = None,
             md_must_contain: list[str] | None = None,
             txt_must_contain: list[str] | None = None,
             scenario: str | None = None,
             as_of_date: str | None = None,
             expected_issue_flags: dict[str, bool] | None = None) -> dict[str, Any]:
    output_json = case_root / "PAPER_TRADE_NOW.json"
    output_txt = case_root / "PAPER_TRADE_NOW.txt"
    output_md = case_root / "PAPER_TRADE_NOW.md"
    ops_history_md = case_root / "OPS_HISTORY.md"
    settlement_audit_md = case_root / "out" / "paper_trade_settlement_audit.md"
    common = [
        sys.executable,
        str(SCRIPT),
        "--run-root", str(run_root),
        "--runs-root", str(case_root / "out" / "daily_portfolio_runs"),
        "--paper-trades-dir", str(case_root / "paper_trades"),
        "--primary-rules", str(PRIMARY_RULES),
        "--shadow-rules", str(SHADOW_RULES),
        "--frozen-eval", str(FROZEN_EVAL),
        "--ops-history-md", str(ops_history_md),
        "--settlement-audit", str(settlement_audit_md),
        "--as-of-date", as_of_date or run_root.name,
    ]

    source_args = SimpleNamespace(
        run_root=str(run_root),
        runs_root=str(case_root / "out" / "daily_portfolio_runs"),
        ops_limit=14,
        min_settled=None,
        portfolio_review_settled=None,
        max_open=5,
        runner=str(source_now.DEFAULT_RUNNER),
        paper_trades_dir=str(case_root / "paper_trades"),
        primary_rules=str(PRIMARY_RULES),
        shadow_rules=str(SHADOW_RULES),
        frozen_eval=str(FROZEN_EVAL),
        ops_history_md=str(ops_history_md),
        settlement_audit=str(settlement_audit_md),
        as_of_date=as_of_date or run_root.name,
        format="json",
        output=None,
    )
    expected_payload = source_now.build_payload(source_args)
    expected_json = json.dumps(expected_payload, indent=2) + "\n"
    expected_text = source_now.render_text(expected_payload)
    expected_md = source_now.render_md(expected_payload) + "\n"

    json_result = subprocess.run(
        common + ["--format", "json", "--output", str(output_json)],
        cwd=BASE,
        capture_output=True,
        text=True,
        check=True,
    )
    text_result = subprocess.run(
        common + ["--format", "text", "--output", str(output_txt)],
        cwd=BASE,
        capture_output=True,
        text=True,
        check=True,
    )
    md_result = subprocess.run(
        common + ["--format", "md", "--output", str(output_md)],
        cwd=BASE,
        capture_output=True,
        text=True,
        check=True,
    )

    json_text = output_json.read_text(encoding="utf-8")
    txt_text = output_txt.read_text(encoding="utf-8")
    md_text = output_md.read_text(encoding="utf-8")
    payload = json.loads(json_text)
    assert_action_priority_contract(payload, txt_text, md_text, case_name)

    if payload != expected_payload:
        raise AssertionError(f"{case_name}: JSON payload drifted from fresh build_payload() output")
    if json_text != expected_json:
        raise AssertionError(f"{case_name}: saved JSON output drifted from fresh source-layer JSON render")
    if json_result.stdout != expected_json:
        raise AssertionError(f"{case_name}: JSON stdout drifted from saved/source-layer JSON render")
    if txt_text != expected_text:
        raise AssertionError(f"{case_name}: saved text output drifted from fresh source-layer text render")
    if text_result.stdout != expected_text:
        raise AssertionError(f"{case_name}: text stdout drifted from saved/source-layer text render")
    if md_text != expected_md:
        raise AssertionError(f"{case_name}: saved markdown output drifted from fresh source-layer markdown render")
    if md_result.stdout != expected_md:
        raise AssertionError(f"{case_name}: markdown stdout drifted from saved/source-layer markdown render")
    expected_ops_history_rel = str(ops_history_md.relative_to(BASE))
    if payload["ops"]["ops_history_md"] != expected_ops_history_rel:
        raise AssertionError(f"{case_name}: JSON payload did not carry the fixture-routed ops-history path")

    headline = payload["best_action"]["headline"]
    timing = payload["best_action"]["timing"]
    command = payload["best_action"]["command"]
    why = payload["best_action"]["why"]

    if headline != expected_headline:
        raise AssertionError(f"{case_name}: expected headline {expected_headline!r}, got {headline!r}")
    if timing != expected_timing:
        raise AssertionError(f"{case_name}: expected timing {expected_timing!r}, got {timing!r}")
    if expected_command_contains not in command:
        raise AssertionError(f"{case_name}: expected command containing {expected_command_contains!r}, got {command!r}")

    day_bucket = payload["ops"]["day_bucket"]
    if expected_day_bucket is not None and day_bucket != expected_day_bucket:
        raise AssertionError(f"{case_name}: expected ops day bucket {expected_day_bucket!r}, got {day_bucket!r}")
    if expected_why_contains is not None and expected_why_contains not in why:
        raise AssertionError(f"{case_name}: expected why containing {expected_why_contains!r}, got {why!r}")
    if expected_issue_flags:
        read_gate = payload.get("operator_read_gate") or {}
        for flag, expected in expected_issue_flags.items():
            if read_gate.get(flag) is not expected:
                raise AssertionError(
                    f"{case_name}: expected operator_read_gate.{flag}={expected}, "
                    f"got {read_gate.get(flag)!r}"
                )
    if expected_day_bucket is not None:
        expected_bucket_line = f"- Latest ops bucket: **{expected_day_bucket}**"
        if expected_bucket_line not in md_text:
            raise AssertionError(f"{case_name}: expected markdown output to contain {expected_bucket_line!r}")
    stale_snapshot_note = expected_payload.get("stale_snapshot_note")
    if stale_snapshot_note:
        expected_md_stale_note = f"- Stale snapshot note: {stale_snapshot_note}"
        expected_txt_stale_note = f"- Stale snapshot note: {stale_snapshot_note}"
        if expected_md_stale_note not in md_text:
            raise AssertionError(f"{case_name}: expected markdown output to contain stale snapshot note {expected_md_stale_note!r}")
        if expected_txt_stale_note not in txt_text:
            raise AssertionError(f"{case_name}: expected text output to contain stale snapshot note {expected_txt_stale_note!r}")
    if expected_why_contains is not None and expected_why_contains not in md_text:
        raise AssertionError(f"{case_name}: expected markdown output to contain why snippet {expected_why_contains!r}")
    focus_lane = payload[payload["best_action"]["lane_key"]]
    expected_text_quick_reads = [
        f"1. {focus_lane['summary_txt']}",
        f"2. {focus_lane['next_steps_md']}",
        f"3. {focus_lane['lane_monitor_md']}",
        f"4. {payload['daily_summary']}",
        f"5. {expected_ops_history_rel}",
    ]
    expected_md_quick_reads = [
        f"1. `{focus_lane['summary_txt']}`",
        f"2. `{focus_lane['next_steps_md']}`",
        f"3. `{focus_lane['lane_monitor_md']}`",
        f"4. `{payload['daily_summary']}`",
        f"5. `{expected_ops_history_rel}`",
    ]
    expected_text_preflight_surface = f"- Preflight note artifact: {payload['preflight_note_path']}"
    expected_md_preflight_surface = f"- Preflight note artifact: `{payload['preflight_note_path']}`"
    expected_text_sidecar_lines = [
        f"- Primary lane status sidecars: pipeline={payload['primary']['pipeline_status_json']} | scanner={payload['primary']['scanner_status_json']}",
        f"- Shadow lane status sidecars: pipeline={payload['shadow']['pipeline_status_json']} | scanner={payload['shadow']['scanner_status_json']}",
    ]
    expected_md_sidecar_lines = [
        f"- Primary lane status sidecars: pipeline=`{payload['primary']['pipeline_status_json']}`, scanner=`{payload['primary']['scanner_status_json']}`",
        f"- Shadow lane status sidecars: pipeline=`{payload['shadow']['pipeline_status_json']}`, scanner=`{payload['shadow']['scanner_status_json']}`",
    ]
    expected_text_context_lines = []
    expected_md_context_lines = []
    if payload["primary"].get("recent_run_context"):
        expected_text_context_lines.append(f"- Primary lane context: {payload['primary']['recent_run_context']}")
        expected_md_context_lines.append(f"- Primary lane context: {payload['primary']['recent_run_context']}")
    if payload["primary"].get("why"):
        expected_text_context_lines.append(f"- Primary lane why now: {payload['primary']['why']}")
        expected_md_context_lines.append(f"- Primary lane why now: {payload['primary']['why']}")
    if payload["shadow"].get("recent_run_context"):
        expected_text_context_lines.append(f"- Shadow lane context: {payload['shadow']['recent_run_context']}")
        expected_md_context_lines.append(f"- Shadow lane context: {payload['shadow']['recent_run_context']}")
    if payload["shadow"].get("why"):
        expected_text_context_lines.append(f"- Shadow lane why now: {payload['shadow']['why']}")
        expected_md_context_lines.append(f"- Shadow lane why now: {payload['shadow']['why']}")
    for snippet in expected_text_quick_reads:
        if snippet not in txt_text:
            raise AssertionError(f"{case_name}: text output dropped quick-read item {snippet!r}")
    for snippet in expected_md_quick_reads:
        if snippet not in md_text:
            raise AssertionError(f"{case_name}: markdown output dropped quick-read item {snippet!r}")
    if expected_text_preflight_surface not in txt_text:
        raise AssertionError(f"{case_name}: text output dropped routed preflight note artifact {expected_text_preflight_surface!r}")
    if expected_md_preflight_surface not in md_text:
        raise AssertionError(f"{case_name}: markdown output dropped routed preflight note artifact {expected_md_preflight_surface!r}")
    if payload.get("preflight_excluded_track_summary"):
        expected_text_excluded = f"- Excluded track aliases: {payload['preflight_excluded_track_summary']}"
        expected_md_excluded = f"- Excluded track aliases: {payload['preflight_excluded_track_summary']}"
        if expected_text_excluded not in txt_text:
            raise AssertionError(f"{case_name}: text output dropped structured preflight excluded-track aliases {expected_text_excluded!r}")
        if expected_md_excluded not in md_text:
            raise AssertionError(f"{case_name}: markdown output dropped structured preflight excluded-track aliases {expected_md_excluded!r}")
    expected_text_audit = f"- Settlement audit: {payload['settlement_audit']}"
    expected_md_audit = f"- Settlement audit: `{payload['settlement_audit']}`"
    if expected_text_audit not in txt_text:
        raise AssertionError(f"{case_name}: text output dropped routed settlement-audit pointer {expected_text_audit!r}")
    if expected_md_audit not in md_text:
        raise AssertionError(f"{case_name}: markdown output dropped routed settlement-audit pointer {expected_md_audit!r}")
    gate_minimums = payload["decision_gate_minimums"]
    active_gates = payload["active_decision_gates"]
    expected_text_gate_source = f"- Decision-gate source: {source_now.gate_source_text(gate_minimums)}"
    expected_text_active_gates = f"- Active right-now gates: {source_now.active_gate_line(active_gates)}"
    expected_md_gate_source = f"- Source: `{gate_minimums['source_path']}`; loaded={gate_minimums['source_loaded']}; fallback_used={gate_minimums['fallback_used']}."
    expected_md_active_gates = f"- Active right-now gates: {source_now.active_gate_line(active_gates, markdown=True)}"
    if not gate_minimums.get("source_loaded") or gate_minimums.get("cli_overrides"):
        raise AssertionError(f"{case_name}: expected default right-now gate payload to be scorecard-sourced without CLI overrides")
    if (
        active_gates.get("primary_min_settled") != 30
        or active_gates.get("shadow_min_settled") != 20
        or active_gates.get("portfolio_review_settled") != 100
        or active_gates.get("first_read_gate_parity") is not False
        or active_gates.get("portfolio_review_gate_parity") is not True
        or active_gates.get("primary_shadow_gate_parity") is not False
    ):
        raise AssertionError(f"{case_name}: expected source-matched lane-specific right-now gates (primary 30, shadow 20, portfolio 100)")
    for snippet in (expected_text_gate_source, expected_text_active_gates):
        if snippet not in txt_text:
            raise AssertionError(f"{case_name}: text output dropped scorecard-sourced right-now gate line {snippet!r}")
    for snippet in ("## Decision-Gate Source", expected_md_gate_source, expected_md_active_gates):
        if snippet not in md_text:
            raise AssertionError(f"{case_name}: markdown output dropped scorecard-sourced right-now gate line {snippet!r}")
    if payload.get("shadow_settlement_audit_promotion_gate"):
        expected_text_gate = f"- Shadow settlement-audit promotion gate: {payload['shadow_settlement_audit_promotion_gate']}"
        if expected_text_gate not in txt_text:
            raise AssertionError(f"{case_name}: text output dropped shadow settlement-audit promotion gate {expected_text_gate!r}")
        if expected_text_gate not in md_text:
            raise AssertionError(f"{case_name}: markdown output dropped shadow settlement-audit promotion gate {expected_text_gate!r}")
    if payload.get("shadow_settlement_audit_rule_progress"):
        expected_text_progress = f"- Shadow per-rule promotion coverage: {payload['shadow_settlement_audit_rule_progress']}"
        if expected_text_progress not in txt_text:
            raise AssertionError(f"{case_name}: text output dropped shadow settlement-audit rule-progress line {expected_text_progress!r}")
        if expected_text_progress not in md_text:
            raise AssertionError(f"{case_name}: markdown output dropped shadow settlement-audit rule-progress line {expected_text_progress!r}")
    for snippet in expected_text_sidecar_lines:
        if snippet not in txt_text:
            raise AssertionError(f"{case_name}: text output dropped routed status-sidecar line {snippet!r}")
    for snippet in expected_md_sidecar_lines:
        if snippet not in md_text:
            raise AssertionError(f"{case_name}: markdown output dropped routed status-sidecar line {snippet!r}")
    for snippet in expected_text_context_lines:
        if snippet not in txt_text:
            raise AssertionError(f"{case_name}: text output dropped lane-context line {snippet!r}")
    for snippet in expected_md_context_lines:
        if snippet not in md_text:
            raise AssertionError(f"{case_name}: markdown output dropped lane-context line {snippet!r}")
    for snippet in txt_must_contain or []:
        if snippet not in txt_text:
            raise AssertionError(f"{case_name}: expected text output to contain {snippet!r}")
    for snippet in md_must_contain or []:
        if snippet not in md_text:
            raise AssertionError(f"{case_name}: expected markdown output to contain {snippet!r}")

    return {
        "case": case_name,
        "scenario": scenario,
        "headline": headline,
        "timing": timing,
        "command": command,
        "why": why,
        "day_bucket": day_bucket,
        "primary_state": payload["primary"]["state"],
        "shadow_state": payload["shadow"]["state"],
        "output_json": str(output_json.relative_to(BASE)),
        "output_txt": str(output_txt.relative_to(BASE)),
        "output_md": str(output_md.relative_to(BASE)),
    }


def validate_live_surfaces() -> dict[str, Any]:
    run_root = source_now.latest_run_root(source_now.DEFAULT_RUNS_ROOT)
    if run_root is None:
        raise AssertionError(f"no live daily run folders found under {source_now.DEFAULT_RUNS_ROOT}")

    live_args = SimpleNamespace(
        run_root=None,
        runs_root=str(source_now.DEFAULT_RUNS_ROOT),
        ops_limit=14,
        min_settled=None,
        portfolio_review_settled=None,
        max_open=5,
        runner=str(source_now.DEFAULT_RUNNER),
        paper_trades_dir=str(source_now.DEFAULT_PAPER_TRADES_DIR),
        primary_rules=str(source_now.DEFAULT_PRIMARY_RULES),
        shadow_rules=str(source_now.DEFAULT_SHADOW_RULES),
        frozen_eval=str(source_now.DEFAULT_FROZEN_EVAL),
        ops_history_md=str(source_now.DEFAULT_OPS_HISTORY_MD),
        settlement_audit=str(source_now.DEFAULT_SETTLEMENT_AUDIT),
        format="json",
        output=None,
    )
    expected_payload = source_now.build_payload(live_args)
    expected_text = source_now.render_text(expected_payload)
    expected_md = source_now.render_md(expected_payload) + "\n"
    expected_json = json.dumps(expected_payload, indent=2) + "\n"

    if not LIVE_TXT.exists():
        raise AssertionError(f"missing live text surface: {LIVE_TXT}")
    if not LIVE_MD.exists():
        raise AssertionError(f"missing live markdown surface: {LIVE_MD}")
    if not LIVE_JSON.exists():
        raise AssertionError(f"missing live JSON surface: {LIVE_JSON}")

    live_text = LIVE_TXT.read_text(encoding="utf-8")
    live_md = LIVE_MD.read_text(encoding="utf-8")
    live_json = LIVE_JSON.read_text(encoding="utf-8")
    if live_text != expected_text:
        raise AssertionError("live PAPER_TRADE_NOW.txt drifted from the current render_text(...) output")
    if live_md != expected_md:
        if live_md.lstrip().startswith("{"):
            raise AssertionError("live PAPER_TRADE_NOW.md contains JSON-style content instead of the current markdown render")
        raise AssertionError("live PAPER_TRADE_NOW.md drifted from the current render_md(...) output")
    if live_json != expected_json:
        raise AssertionError("live PAPER_TRADE_NOW.json drifted from the current build_payload(...) output")
    live_json_payload = json.loads(live_json)
    assert_action_priority_contract(live_json_payload, live_text, live_md, "live_current_surface")
    if live_json_payload.get("run_freshness", {}).get("is_stale") and "run_daily_portfolio_observation.sh" not in str(live_json_payload.get("best_action", {}).get("command") or ""):
        raise AssertionError("stale live PAPER_TRADE_NOW best_action must point to the daily wrapper, not a lane-only read")
    live_read_gate = live_json_payload.get("operator_read_gate") or {}
    if live_json_payload.get("run_freshness", {}).get("is_stale"):
        if live_read_gate.get("requires_refresh_before_evidence_read") is not True:
            raise AssertionError("stale live PAPER_TRADE_NOW operator_read_gate must require refresh before evidence read")
        if live_read_gate.get("recommended_command") != "./run_daily_portfolio_observation.sh":
            raise AssertionError("stale live PAPER_TRADE_NOW operator_read_gate must recommend the daily wrapper")
        if live_read_gate.get("current_top_card_counts_as_no_target_evidence") is not False or live_read_gate.get("current_top_card_counts_as_clean_empty_evidence") is not False:
            raise AssertionError("stale live PAPER_TRADE_NOW operator_read_gate must not count as no-target or clean-empty evidence")
        live_lane_context = " ".join(
            str(value or "")
            for value in (
                live_json_payload.get("primary", {}).get("recent_run_context"),
                live_json_payload.get("primary", {}).get("why"),
                live_json_payload.get("shadow", {}).get("recent_run_context"),
                live_json_payload.get("shadow", {}).get("why"),
            )
        )
        if ("API-access" in live_lane_context or "403 Client Error" in live_lane_context) and "scanner/API-access failure context is present" not in live_read_gate.get("reasons", []):
            raise AssertionError("live PAPER_TRADE_NOW operator_read_gate no longer preserves the scanner/API-access failure reason")
        if "- Operator read gate: " not in live_md or "- Operator read gate: " not in live_text:
            raise AssertionError("live PAPER_TRADE_NOW surfaces dropped the operator read gate line")
    if not live_json_payload.get("settlement_audit") or not live_json_payload.get("shadow_settlement_audit_promotion_gate") or not live_json_payload.get("shadow_settlement_audit_rule_progress"):
        raise AssertionError("live PAPER_TRADE_NOW.json no longer carries the settlement-audit pointer and shadow per-rule promotion-gate fields")
    hierarchy = live_json_payload.get("live_hierarchy") or {}
    if hierarchy.get("primary_companion") != "CD_CORE_K8" or "not the Phase 8 shadow/watch lane" not in str(hierarchy.get("primary_companion_note") or ""):
        raise AssertionError("live PAPER_TRADE_NOW.json no longer distinguishes CD_CORE_K8 as the active primary-basket paper companion rather than a Phase 8 shadow-lane promotion")
    if "## Live lane hierarchy" not in live_md or "**OP_DURABLE_K7**" not in live_md or "**CD_CORE_K8**" not in live_md or "**OP_REFINED_K7**" not in live_md:
        raise AssertionError("live PAPER_TRADE_NOW.md no longer carries the explicit live lane hierarchy block")
    if "primary OP/CD paper-basket companion" not in live_md or "not a Phase 8 shadow-lane promotion" not in live_md or "primary OP/CD paper-basket companion" not in live_text or "not a Phase 8 shadow-lane promotion" not in live_text:
        raise AssertionError("live PAPER_TRADE_NOW surfaces no longer clarify that CD_CORE_K8 is a primary-basket paper companion, not a Phase 8 shadow-lane promotion")
    if expected_payload.get("stale_snapshot_note"):
        expected_stale_note = f"- Stale snapshot note: {expected_payload['stale_snapshot_note']}"
        if expected_stale_note not in live_md:
            raise AssertionError("live PAPER_TRADE_NOW.md no longer makes stale lane context read explicitly like inherited snapshot context")
        if expected_stale_note not in live_text:
            raise AssertionError("live PAPER_TRADE_NOW.txt no longer makes stale lane context read explicitly like inherited snapshot context")
    if "- Evidence frame: **Operational priority surface**" not in live_md or "not a profit-proof or CI-backed forward-validation surface" not in live_md or "forward performance still needs settled paper trades before the lane says anything new about live edge" not in live_md or "broader selective-family secondary lines stay replay context on walk-forward test years, not extra train-only validation" not in live_md:
        raise AssertionError("live PAPER_TRADE_NOW.md no longer states the operational evidence frame, replay-context caution, and forward-performance limitation explicitly")
    if "- Evidence frame: Operational priority surface — This card is an operational priority read, not a profit-proof or CI-backed forward-validation surface." not in live_text or "- Limitation: Treat this as an operator runbook for what to do next; forward performance still needs settled paper trades before the lane says anything new about live edge." not in live_text or "broader selective-family secondary lines stay replay context on walk-forward test years, not extra train-only validation" not in live_text:
        raise AssertionError("live PAPER_TRADE_NOW.txt no longer states the operational evidence frame, replay-context caution, and limitation explicitly")
    expected_live_text_audit = f"- Settlement audit: {expected_payload['settlement_audit']}"
    expected_live_md_audit = f"- Settlement audit: `{expected_payload['settlement_audit']}`"
    if expected_live_text_audit not in live_text or expected_live_md_audit not in live_md:
        raise AssertionError("live PAPER_TRADE_NOW surfaces no longer carry the routed settlement-audit pointer")
    gate_minimums = live_json_payload.get("decision_gate_minimums") or {}
    active_gates = live_json_payload.get("active_decision_gates") or {}
    expected_live_text_gate_source = f"- Decision-gate source: {source_now.gate_source_text(gate_minimums)}"
    expected_live_text_active_gates = f"- Active right-now gates: {source_now.active_gate_line(active_gates)}"
    expected_live_md_gate_source = f"- Source: `{gate_minimums['source_path']}`; loaded={gate_minimums['source_loaded']}; fallback_used={gate_minimums['fallback_used']}."
    expected_live_md_active_gates = f"- Active right-now gates: {source_now.active_gate_line(active_gates, markdown=True)}"
    if not gate_minimums.get("source_loaded") or gate_minimums.get("cli_overrides"):
        raise AssertionError("live PAPER_TRADE_NOW.json no longer uses scorecard-sourced right-now gates without CLI overrides")
    if (
        active_gates.get("primary_min_settled") != 30
        or active_gates.get("shadow_min_settled") != 20
        or active_gates.get("portfolio_review_settled") != 100
        or active_gates.get("first_read_gate_parity") is not False
        or active_gates.get("portfolio_review_gate_parity") is not True
        or active_gates.get("primary_shadow_gate_parity") is not False
    ):
        raise AssertionError("live PAPER_TRADE_NOW.json no longer keeps source-matched lane-specific right-now gates (primary 30, shadow 20, portfolio 100)")
    for snippet in (expected_live_text_gate_source, expected_live_text_active_gates):
        if snippet not in live_text:
            raise AssertionError(f"live PAPER_TRADE_NOW.txt dropped scorecard-sourced right-now gate line {snippet!r}")
    for snippet in ("## Decision-Gate Source", expected_live_md_gate_source, expected_live_md_active_gates):
        if snippet not in live_md:
            raise AssertionError(f"live PAPER_TRADE_NOW.md dropped scorecard-sourced right-now gate line {snippet!r}")
    if expected_payload.get("shadow_settlement_audit_promotion_gate"):
        expected_gate = f"- Shadow settlement-audit promotion gate: {expected_payload['shadow_settlement_audit_promotion_gate']}"
        if expected_gate not in live_text or expected_gate not in live_md:
            raise AssertionError("live PAPER_TRADE_NOW surfaces no longer carry the shadow per-rule settlement-audit promotion gate")
    if expected_payload.get("shadow_settlement_audit_rule_progress"):
        expected_progress = f"- Shadow per-rule promotion coverage: {expected_payload['shadow_settlement_audit_rule_progress']}"
        if expected_progress not in live_text or expected_progress not in live_md:
            raise AssertionError("live PAPER_TRADE_NOW surfaces no longer carry the shadow per-rule promotion coverage line")
    live_focus_lane = expected_payload[expected_payload["best_action"]["lane_key"]]
    expected_text_quick_reads = [
        f"1. {live_focus_lane['summary_txt']}",
        f"2. {live_focus_lane['next_steps_md']}",
        f"3. {live_focus_lane['lane_monitor_md']}",
        f"4. {expected_payload['daily_summary']}",
        f"5. {expected_payload['ops']['ops_history_md']}",
    ]
    expected_md_quick_reads = [
        f"1. `{live_focus_lane['summary_txt']}`",
        f"2. `{live_focus_lane['next_steps_md']}`",
        f"3. `{live_focus_lane['lane_monitor_md']}`",
        f"4. `{expected_payload['daily_summary']}`",
        f"5. `{expected_payload['ops']['ops_history_md']}`",
    ]
    expected_text_preflight_surface = f"- Preflight note artifact: {expected_payload['preflight_note_path']}"
    expected_md_preflight_surface = f"- Preflight note artifact: `{expected_payload['preflight_note_path']}`"
    expected_text_sidecar_lines = [
        f"- Primary lane status sidecars: pipeline={expected_payload['primary']['pipeline_status_json']} | scanner={expected_payload['primary']['scanner_status_json']}",
        f"- Shadow lane status sidecars: pipeline={expected_payload['shadow']['pipeline_status_json']} | scanner={expected_payload['shadow']['scanner_status_json']}",
    ]
    expected_md_sidecar_lines = [
        f"- Primary lane status sidecars: pipeline=`{expected_payload['primary']['pipeline_status_json']}`, scanner=`{expected_payload['primary']['scanner_status_json']}`",
        f"- Shadow lane status sidecars: pipeline=`{expected_payload['shadow']['pipeline_status_json']}`, scanner=`{expected_payload['shadow']['scanner_status_json']}`",
    ]
    for snippet in expected_text_quick_reads:
        if snippet not in live_text:
            raise AssertionError(f"live PAPER_TRADE_NOW.txt dropped quick-read item {snippet!r}")
    for snippet in expected_md_quick_reads:
        if snippet not in live_md:
            raise AssertionError(f"live PAPER_TRADE_NOW.md dropped quick-read item {snippet!r}")
    if expected_text_preflight_surface not in live_text:
        raise AssertionError(f"live PAPER_TRADE_NOW.txt dropped routed preflight note artifact {expected_text_preflight_surface!r}")
    if expected_md_preflight_surface not in live_md:
        raise AssertionError(f"live PAPER_TRADE_NOW.md dropped routed preflight note artifact {expected_md_preflight_surface!r}")
    if expected_payload.get("preflight_excluded_track_summary"):
        expected_text_excluded = f"- Excluded track aliases: {expected_payload['preflight_excluded_track_summary']}"
        expected_md_excluded = f"- Excluded track aliases: {expected_payload['preflight_excluded_track_summary']}"
        if expected_text_excluded not in live_text:
            raise AssertionError(f"live PAPER_TRADE_NOW.txt dropped structured preflight excluded-track aliases {expected_text_excluded!r}")
        if expected_md_excluded not in live_md:
            raise AssertionError(f"live PAPER_TRADE_NOW.md dropped structured preflight excluded-track aliases {expected_md_excluded!r}")
    for snippet in expected_text_sidecar_lines:
        if snippet not in live_text:
            raise AssertionError(f"live PAPER_TRADE_NOW.txt dropped routed status-sidecar line {snippet!r}")
    for snippet in expected_md_sidecar_lines:
        if snippet not in live_md:
            raise AssertionError(f"live PAPER_TRADE_NOW.md dropped routed status-sidecar line {snippet!r}")
    expected_text_context_lines = []
    expected_md_context_lines = []
    if expected_payload["primary"].get("recent_run_context"):
        expected_text_context_lines.append(f"- Primary lane context: {expected_payload['primary']['recent_run_context']}")
        expected_md_context_lines.append(f"- Primary lane context: {expected_payload['primary']['recent_run_context']}")
    if expected_payload["primary"].get("why"):
        expected_text_context_lines.append(f"- Primary lane why now: {expected_payload['primary']['why']}")
        expected_md_context_lines.append(f"- Primary lane why now: {expected_payload['primary']['why']}")
    if expected_payload["shadow"].get("recent_run_context"):
        expected_text_context_lines.append(f"- Shadow lane context: {expected_payload['shadow']['recent_run_context']}")
        expected_md_context_lines.append(f"- Shadow lane context: {expected_payload['shadow']['recent_run_context']}")
    if expected_payload["shadow"].get("why"):
        expected_text_context_lines.append(f"- Shadow lane why now: {expected_payload['shadow']['why']}")
        expected_md_context_lines.append(f"- Shadow lane why now: {expected_payload['shadow']['why']}")
    for snippet in expected_text_context_lines:
        if snippet not in live_text:
            raise AssertionError(f"live PAPER_TRADE_NOW.txt dropped lane-context/why line {snippet!r}")
    for snippet in expected_md_context_lines:
        if snippet not in live_md:
            raise AssertionError(f"live PAPER_TRADE_NOW.md dropped lane-context/why line {snippet!r}")

    return {
        "case": "live_current_surface",
        "scenario": "default PAPER_TRADE_NOW text, markdown, and JSON surfaces match the latest live run render",
        "headline": expected_payload["best_action"]["headline"],
        "timing": expected_payload["best_action"]["timing"],
        "command": expected_payload["best_action"]["command"],
        "why": expected_payload["best_action"]["why"],
        "day_bucket": expected_payload["ops"]["day_bucket"],
        "primary_state": expected_payload["primary"]["state"],
        "shadow_state": expected_payload["shadow"]["state"],
        "output_txt": str(LIVE_TXT.relative_to(BASE)),
        "output_md": str(LIVE_MD.relative_to(BASE)),
        "output_json": str(LIVE_JSON.relative_to(BASE)),
        "run_root": expected_payload["run_root"],
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    scorecard_json = args.scorecard_json.expanduser().resolve()
    configure_output_paths(args.fixture_root.expanduser().resolve(), args.out_dir.expanduser().resolve())
    scorecard_gates = read_scorecard_gate_minimums(scorecard_json)
    scorecard_artifact_guardrails = scorecard_no_artifact_guardrails(scorecard_json)

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)

    open_signal = signal_row(1, "OP_DURABLE_K7", "OP", 8, 120.0)
    primary_open_root, primary_open_run = setup_case(
        case_name="case_primary_open",
        run_date="2026-05-01",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        primary_status=pipeline_status("signals_logged_no_bet", hits=1, recs=1, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[open_signal],
        primary_settlements=[settlement_row(open_signal, "open", "")],
    )

    primary_incomplete_signal = signal_row(2, "OP_DURABLE_K7", "OP", 9, 120.0)
    primary_incomplete_root, primary_incomplete_run = setup_case(
        case_name="case_primary_incomplete",
        run_date="2026-05-13",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        primary_status=pipeline_status("signals_logged_no_bet", hits=1, recs=1, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[primary_incomplete_signal],
        primary_settlements=[settlement_row(primary_incomplete_signal, "settled", "")],
    )

    primary_roi_gap_signals = [signal_row(idx, "OP_DURABLE_K7", "OP", 7 + idx, 120.0) for idx in range(1, 6)]
    primary_roi_gap_root, primary_roi_gap_run = setup_case(
        case_name="case_primary_partial_roi_coverage",
        run_date="2026-05-14",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=primary_roi_gap_signals,
        primary_settlements=[
            settlement_row(primary_roi_gap_signals[0], "settled", "HIT", 96.0),
            settlement_row(primary_roi_gap_signals[1], "settled", "MISS", 0.0),
            settlement_row(primary_roi_gap_signals[2], "settled", "MISS", None),
            settlement_row(primary_roi_gap_signals[3], "settled", "MISS", None),
            settlement_row(primary_roi_gap_signals[4], "settled", "MISS", None),
        ],
    )

    primary_malformed_cost_signals = [signal_row(idx, "OP_DURABLE_K7", "OP", 7 + idx, 120.0) for idx in range(11, 14)]
    primary_malformed_cost_root, primary_malformed_cost_run = setup_case(
        case_name="case_primary_malformed_actual_cost_roi_coverage",
        run_date="2026-05-15",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=primary_malformed_cost_signals,
        primary_settlements=[
            settlement_row(primary_malformed_cost_signals[0], "settled", "HIT", 96.0),
            settlement_row(primary_malformed_cost_signals[1], "settled", "MISS", 0.0, actual_cost_override="bad-cost"),
            settlement_row(primary_malformed_cost_signals[2], "settled", "MISS", 0.0),
        ],
    )

    primary_missing_ts_signals = [signal_row(idx, "OP_DURABLE_K7", "OP", 7 + idx, 120.0) for idx in range(21, 24)]
    primary_missing_ts_root, primary_missing_ts_run = setup_case(
        case_name="case_primary_missing_settled_ts_roi_coverage",
        run_date="2026-05-16",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=primary_missing_ts_signals,
        primary_settlements=[
            settlement_row(primary_missing_ts_signals[0], "settled", "HIT", 96.0),
            settlement_row(primary_missing_ts_signals[1], "settled", "MISS", 0.0, settled_ts_override=""),
            settlement_row(primary_missing_ts_signals[2], "settled", "MISS", 0.0),
        ],
    )

    decision_signals: list[dict[str, Any]] = []
    decision_settlements: list[dict[str, Any]] = []
    for idx in range(1, 21):
        sig = signal_row(idx, "OP_DURABLE_K7", "OP", 7 + (idx % 5), 120.0)
        decision_signals.append(sig)
        decision_settlements.append(settlement_row(sig, "settled", "HIT" if idx <= 7 else "MISS", 480.0 if idx <= 7 else 0.0))
    for idx in range(21, 31):
        sig = signal_row(idx, "CD_CORE_K8", "CD", 1 + (idx % 6), 210.0)
        decision_signals.append(sig)
        decision_settlements.append(settlement_row(sig, "settled", "HIT" if idx <= 24 else "MISS", 840.0 if idx <= 24 else 0.0))

    decision_root, decision_run = setup_case(
        case_name="case_decision_grade",
        run_date="2026-05-02",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=decision_signals,
        primary_settlements=decision_settlements,
    )

    cache_miss_root, cache_miss_run = setup_case(
        case_name="case_rerun_live_cache_miss",
        run_date="2026-05-03",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        primary_status=pipeline_status(
            "scanner_failed_empty_run",
            hits=0,
            recs=0,
            bets=0,
            cache_only=True,
            scanner_result="scanner_error",
            scanner_error="No cached data found for today's cards.",
        ),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status(
            "scanner_error",
            cache_only=True,
            error="No cached data found for today's cards.",
        ),
    )

    generic_scanner_error_root, generic_scanner_error_run = setup_case(
        case_name="case_generic_scanner_error_detail",
        run_date="2026-05-21",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        primary_status=pipeline_status(
            "scanner_failed_empty_run",
            hits=0,
            recs=0,
            bets=0,
            scanner_result="scanner_error",
            scanner_error="403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            api_failure_operator_action="refresh_daily_wrapper_before_evidence_read",
            api_failure_recheck_command="./run_daily_portfolio_observation.sh",
        ),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status(
            "scanner_error",
            error="403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            api_failure_operator_action="refresh_daily_wrapper_before_evidence_read",
            api_failure_recheck_command="./run_daily_portfolio_observation.sh",
        ),
    )

    api_access_stale_cache_root, api_access_stale_cache_run = setup_case(
        case_name="case_api_access_stale_cache_fallback_top_card",
        run_date="2026-05-22",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        primary_status=pipeline_status(
            "scanner_failed_empty_run",
            hits=0,
            recs=0,
            bets=0,
            scanner_result="scanner_error",
            scanner_error="403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            observation_reason="api_access_failure",
            api_failure_operator_action="refresh_daily_wrapper_before_evidence_read",
            api_failure_recheck_command="./run_daily_portfolio_observation.sh",
            scanner_api_access_failure=True,
            scanner_http_status=403,
            scanner_api_failure_class="api_access_failure",
            scanner_api_failure_valid_scope="operational_context_only",
            scanner_api_failure_boundary="not clean-empty/no-target evidence",
            stale_cache_fallback_applied=True,
            stale_cache_fallback_count=2,
            stale_cache_fallback_kind="cards",
            stale_cache_fallback_error_type="HTTPError",
            stale_cache_fallback_error="403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
        ),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status(
            "scanner_error",
            error="403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            api_failure_operator_action="refresh_daily_wrapper_before_evidence_read",
            api_failure_recheck_command="./run_daily_portfolio_observation.sh",
            api_access_failure=True,
            http_status=403,
            api_failure_class="api_access_failure",
            api_failure_valid_scope="operational_context_only",
            api_failure_boundary="not clean-empty/no-target evidence",
            stale_cache_fallback_applied=True,
            stale_cache_fallback_count=2,
            stale_cache_fallback_kind="cards",
            stale_cache_fallback_error_type="HTTPError",
            stale_cache_fallback_error="403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
        ),
    )

    partial_cache_root, partial_cache_run = setup_case(
        case_name="case_partial_cache_refresh",
        run_date="2026-05-04",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        primary_status=pipeline_status("partial_cache_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status(
            "partial_cache_no_qualifiers",
            partial_cache=True,
            missing_race_detail_cache_skips=3,
        ),
    )

    partial_cache_activity_root, partial_cache_activity_run = setup_case(
        case_name="case_partial_cache_activity_refresh",
        run_date="2026-05-06",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        primary_status=pipeline_status(
            "partial_cache_with_activity",
            hits=1,
            recs=1,
            bets=0,
            scanner_result="partial_cache_missing_detail",
            observation_reason="partial_cache_with_activity",
        ),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status(
            "partial_cache_missing_detail",
            partial_cache=True,
            missing_race_detail_cache_skips=1,
        ),
    )

    missing_scan_output_root, missing_scan_output_run = setup_case(
        case_name="case_missing_scan_output_refresh",
        run_date="2026-05-20-missing-scan-output",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        primary_status={
            **pipeline_status(
                "scanner_failed_empty_run",
                hits=0,
                recs=0,
                bets=0,
                scanner_result="missing_scan_output",
                observation_reason="missing_scan_output",
            ),
            "observation_scope": "operational_limit",
            "scanner_stage_status": "missing_scan_output",
            "scanner_status_reported_result": "no_qualifiers",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "missing_or_empty_scan_output",
            "scan_input_state_before_empty_fallback": "missing",
            "scan_input_empty_fallback_value": "[]",
        },
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status("no_qualifiers"),
        shadow_scanner_status=scanner_status("no_qualifiers"),
    )

    pipeline_failure_root, pipeline_failure_run = setup_case(
        case_name="case_pipeline_failure_refresh",
        run_date="2026-05-10",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        primary_status=pipeline_status(
            "signals_logged_no_bet",
            hits=1,
            recs=0,
            bets=0,
            scanner_result="alerts_found",
            result="pipeline_error",
            stage="recommender",
            error_type="RuntimeError",
            error="fixture recommender crash",
        ),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status("alerts_found"),
    )

    pipeline_logger_failure_root, pipeline_logger_failure_run = setup_case(
        case_name="case_pipeline_logger_failure_refresh",
        run_date="2026-05-11",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        primary_status=pipeline_status(
            "signals_logged_no_bet",
            hits=1,
            recs=1,
            bets=0,
            scanner_result="alerts_found",
            result="pipeline_error",
            stage="logger",
            error_type="ValueError",
            error="fixture logger crash",
        ),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status("alerts_found"),
    )

    shadow_open_signal = signal_row(41, "KEE_K9", "KEE", 9, 96.0)
    shadow_open_root, shadow_open_run = setup_case(
        case_name="case_shadow_open",
        run_date="2026-05-08",
        preflight_payload=preflight(False, "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today. Shadow-only tracks present: KEE.", shadow_tracks=["KEE"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("signals_logged_no_bet", hits=1, recs=1, bets=0),
        primary_signals=[],
        primary_settlements=[],
        shadow_signals=[shadow_open_signal],
        shadow_settlements=[settlement_row(shadow_open_signal, "open", "")],
    )

    shadow_decision_signals: list[dict[str, Any]] = []
    shadow_decision_settlements: list[dict[str, Any]] = []
    for idx in range(61, 91):
        sig = signal_row(idx, "OP_REFINED_K7", "OP", 5 + (idx % 5), 72.0)
        shadow_decision_signals.append(sig)
        shadow_decision_settlements.append(settlement_row(sig, "settled", "HIT" if idx <= 68 else "MISS", 288.0 if idx <= 68 else 0.0))

    shadow_decision_root, shadow_decision_run = setup_case(
        case_name="case_shadow_decision_grade",
        run_date="2026-05-12",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        shadow_signals=shadow_decision_signals,
        shadow_settlements=shadow_decision_settlements,
    )

    no_target_root, no_target_run = setup_case(
        case_name="case_no_targets",
        run_date="2026-05-05",
        preflight_payload=preflight(False, "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 18 NYRA card(s). Shadow-only tracks present: KEE.", shadow_tracks=["KEE"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
    )

    stale_no_target_root, stale_no_target_run = setup_case(
        case_name="case_stale_no_target_run",
        run_date="2026-05-06",
        preflight_payload=preflight(False, "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 18 NYRA card(s). Shadow-only tracks present: KEE.", shadow_tracks=["KEE"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
    )

    undated_run_root, undated_run = setup_case(
        case_name="case_undated_run_folder_refresh",
        run_date="latest-run-copy",
        preflight_payload=preflight(False, "Preflight context: copied run folder with no dated name; do not treat it as current.", shadow_tracks=["KEE"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
    )

    json_only_preflight_root, json_only_preflight_run = setup_case(
        case_name="case_json_only_preflight_note",
        run_date="2026-05-15",
        preflight_payload=preflight(False, "JSON-only preflight note: no active OP/CD cards today; KEE is shadow-only.", shadow_tracks=["KEE"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
    )
    (json_only_preflight_run / "preflight_note.txt").unlink()

    empty_text_json_note_root, empty_text_json_note_run = setup_case(
        case_name="case_empty_text_prefers_json_preflight_note",
        run_date="2026-05-17",
        preflight_payload=preflight(False, "JSON survives even if sibling text file is blank.", shadow_tracks=["KEE"], excluded_tracks=["BAQ"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
    )
    write_text(empty_text_json_note_run / "preflight_note.txt", "\n")

    missing_json_note_root, missing_json_note_run = setup_case(
        case_name="case_missing_json_preflight_note_field",
        run_date="2026-05-18",
        preflight_payload=preflight(False, "", shadow_tracks=["KEE"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
    )
    (missing_json_note_run / "preflight_note.txt").unlink()
    missing_json_note_payload = json.loads((missing_json_note_run / "preflight_note.json").read_text(encoding="utf-8"))
    missing_json_note_payload.pop("note", None)
    write_json(missing_json_note_run / "preflight_note.json", missing_json_note_payload)

    json_only_active_target_root, json_only_active_target_run = setup_case(
        case_name="case_json_only_active_target_preflight",
        run_date="2026-05-16",
        preflight_payload=preflight(True, "JSON-only preflight note: OP is still active today.", relevant_tracks=["OP"]),
        primary_status=pipeline_status(
            "scanner_failed_empty_run",
            cache_only=True,
            scanner_result="scanner_error",
            scanner_error="No cached data found for today's races",
        ),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status(
            "scanner_error",
            cache_only=True,
            error="No cached data found for today's races",
        ),
        shadow_scanner_status=scanner_status("no_qualifiers"),
    )
    (json_only_active_target_run / "preflight_note.txt").unlink()

    empty_text_active_target_root, empty_text_active_target_run = setup_case(
        case_name="case_empty_text_active_target_prefers_json_preflight_note",
        run_date="2026-05-19",
        preflight_payload=preflight(True, "JSON still wins on an active-target day when sibling text file is blank.", relevant_tracks=["OP"]),
        primary_status=pipeline_status(
            "scanner_failed_empty_run",
            cache_only=True,
            scanner_result="scanner_error",
            scanner_error="No cached data found for today's races",
        ),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status(
            "scanner_error",
            cache_only=True,
            error="No cached data found for today's races",
        ),
        shadow_scanner_status=scanner_status("no_qualifiers"),
    )
    write_text(empty_text_active_target_run / "preflight_note.txt", "\n")

    unknown_calendar_root, unknown_calendar_run = setup_case(
        case_name="case_unknown_calendar",
        run_date="2026-05-09",
        preflight_payload={
            "date": "2026-05-09",
            "checked_at": "2026-05-09 12:00",
            "api_ok": False,
            "has_targets": False,
            "relevant_tracks": [],
            "shadow_tracks": [],
            "total_cards": 18,
            "error": "upstream card check failed",
            "note": "Preflight context: calendar state unknown because the upstream card check failed.",
        },
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
    )

    missing_status_root, missing_status_run = setup_case(
        case_name="case_missing_primary_status",
        run_date="2026-05-06",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
    )
    (missing_status_run / "phase7_current_paper" / "pipeline_status.json").unlink()

    empty_status_root, empty_status_run = setup_case(
        case_name="case_empty_primary_status",
        run_date="2026-05-06-empty-pipeline",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
    )
    write_text(empty_status_run / "phase7_current_paper" / "pipeline_status.json", "")

    malformed_status_root, malformed_status_run = setup_case(
        case_name="case_malformed_primary_status",
        run_date="2026-05-07",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP, CD.", relevant_tracks=["OP", "CD"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
    )
    write_text(malformed_status_run / "phase7_current_paper" / "pipeline_status.json", "{bad json\n")

    malformed_scanner_root, malformed_scanner_run = setup_case(
        case_name="case_malformed_primary_scanner_status",
        run_date="2026-05-10",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status("no_qualifiers"),
        shadow_scanner_status=scanner_status("no_qualifiers"),
    )
    write_text(malformed_scanner_run / "phase7_current_paper" / "live_scan.status.json", "{bad json\n")

    empty_scanner_root, empty_scanner_run = setup_case(
        case_name="case_empty_primary_scanner_status",
        run_date="2026-05-10-empty-scanner",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        primary_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status("no_qualifiers"),
        shadow_scanner_status=scanner_status("no_qualifiers"),
    )
    write_text(empty_scanner_run / "phase7_current_paper" / "live_scan.status.json", "")

    recorded_empty_scanner_root, recorded_empty_scanner_run = setup_case(
        case_name="case_pipeline_recorded_empty_primary_scanner_missing",
        run_date="2026-05-10-recorded-empty-scanner",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        primary_status={
            **pipeline_status(
                "scanner_status_unavailable_empty_run",
                scanner_result="scanner_status_empty",
            ),
            "scanner_status_state": "empty",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_status_empty",
        },
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        shadow_scanner_status=scanner_status("no_qualifiers"),
    )

    recorded_unreadable_scanner_root, recorded_unreadable_scanner_run = setup_case(
        case_name="case_pipeline_recorded_unreadable_primary_scanner_missing",
        run_date="2026-05-10-recorded-unreadable-scanner",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        primary_status={
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
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        shadow_scanner_status=scanner_status("no_qualifiers"),
    )

    recorded_invalid_shape_scanner_root, recorded_invalid_shape_scanner_run = setup_case(
        case_name="case_pipeline_recorded_invalid_shape_primary_scanner_missing",
        run_date="2026-05-10-recorded-invalid-shape-scanner",
        preflight_payload=preflight(True, "Preflight context: primary paper-basket target tracks racing today: OP.", relevant_tracks=["OP"]),
        primary_status={
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
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        shadow_scanner_status=scanner_status("no_qualifiers"),
    )

    relocated_scanner_root, relocated_scanner_run = setup_case(
        case_name="case_primary_relocated_scanner_status",
        run_date="2026-05-11",
        preflight_payload=preflight(False, "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 18 NYRA card(s).", shadow_tracks=["KEE"]),
        primary_status={**pipeline_status("clean_empty_run", hits=0, recs=0, bets=0), "scanner_status_path": "renamed_live_scan.status.json"},
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status("no_matching_cards"),
        shadow_scanner_status=scanner_status("no_qualifiers"),
        primary_scanner_relpath="phase7_current_paper/renamed_live_scan.status.json",
    )

    relocated_run_root_scanner_root, relocated_run_root_scanner_run = setup_case(
        case_name="case_primary_relocated_scanner_status_run_root_relative",
        run_date="2026-05-11",
        preflight_payload=preflight(False, "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 18 NYRA card(s).", shadow_tracks=["KEE"]),
        primary_status={**pipeline_status("clean_empty_run", hits=0, recs=0, bets=0), "scanner_status_path": "phase7_current_paper/renamed_live_scan.status.json"},
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status("no_matching_cards"),
        shadow_scanner_status=scanner_status("no_qualifiers"),
        primary_scanner_relpath="phase7_current_paper/renamed_live_scan.status.json",
    )

    relocated_project_scanner_root, relocated_project_scanner_run = setup_case(
        case_name="case_primary_relocated_scanner_status_project_relative",
        run_date="2026-05-11",
        preflight_payload=preflight(False, "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 18 NYRA card(s).", shadow_tracks=["KEE"]),
        primary_status={
            **pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
            "scanner_status_path": "out/status_validation/paper_trade_now_fixture/case_primary_relocated_scanner_status_project_relative/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/renamed_live_scan.status.json",
        },
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status("no_matching_cards"),
        shadow_scanner_status=scanner_status("no_qualifiers"),
        primary_scanner_relpath="phase7_current_paper/renamed_live_scan.status.json",
    )

    declared_beats_stale_scanner_root, declared_beats_stale_scanner_run = setup_case(
        case_name="case_primary_declared_scanner_beats_stale_default",
        run_date="2026-05-11",
        preflight_payload=preflight(False, "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 18 NYRA card(s).", shadow_tracks=["KEE"]),
        primary_status={**pipeline_status("clean_empty_run", hits=0, recs=0, bets=0), "scanner_status_path": "renamed_live_scan.status.json"},
        shadow_status=pipeline_status("clean_empty_run", hits=0, recs=0, bets=0),
        primary_signals=[],
        primary_settlements=[],
        primary_scanner_status=scanner_status("no_matching_cards"),
        shadow_scanner_status=scanner_status("no_qualifiers"),
        primary_scanner_relpath="phase7_current_paper/renamed_live_scan.status.json",
    )
    write_json(
        declared_beats_stale_scanner_run / "phase7_current_paper" / "live_scan.status.json",
        scanner_status("no_qualifiers"),
    )

    fixture_results = [
        run_case(
            "case_primary_open",
            primary_open_root,
            primary_open_run,
            "Settle the primary lane first",
            "now",
            "paper_trade_settlement_helper.py list-open",
            "ACTIVE, HITS FOUND",
            "primary settlement row(s) are still open",
            md_must_contain=[
                "## Live lane hierarchy",
                "- Primary lane anchor: **OP_DURABLE_K7**; primary OP/CD paper-basket companion: **CD_CORE_K8** (not a Phase 8 shadow-lane promotion).",
                "- Shadow lane lead: **OP_REFINED_K7**; closest challenger only, while **KEE_K9 / SA_K9 / DMR_FALL_K7** stay observation-only pockets rather than promotion candidates.",
                "Primary lane context: Latest run context: the latest run logged signals but produced no BET recommendations (1 recommendation(s), 0 raw hit(s)).",
                "open-settlements=`1`",
                "Ops takeaway: OP/CD were active and the primary lane found 1 hit(s), but nothing reached a bet-ready state.",
                "out/status_validation/paper_trade_now_fixture/case_primary_open/out/daily_portfolio_runs/2026-05-01/phase7_current_paper/summary.txt",
                "out/status_validation/paper_trade_now_fixture/case_primary_open/out/daily_portfolio_runs/2026-05-01/phase7_current_paper/next_steps.md",
            ],
            txt_must_contain=[
                "Primary lane context: Latest run context: the latest run logged signals but produced no BET recommendations (1 recommendation(s), 0 raw hit(s)).",
                "open settlements=1",
                "Ops takeaway: OP/CD were active and the primary lane found 1 hit(s), but nothing reached a bet-ready state.",
            ],
            scenario="primary settlement queue wins while preserving no-bet signal context",
        ),
        run_case(
            "case_primary_incomplete",
            primary_incomplete_root,
            primary_incomplete_run,
            "Complete the primary lane settlement entries",
            "now",
            "paper_trade_settlement_helper.py settle",
            expected_why_contains="missing outcome data",
            md_must_contain=[
                "incomplete-settlements=`1`",
                "Focus: **Complete the primary lane settlement entries**",
            ],
            scenario="primary incomplete settled rows outrank normal forward reading",
        ),
        run_case(
            "case_primary_partial_roi_coverage",
            primary_roi_gap_root,
            primary_roi_gap_run,
            "Repair the primary lane ROI coverage",
            "now",
            "paper_trade_lane_monitor.py",
            "ACTIVE, ZERO HITS",
            "missing actual_return: 3",
            md_must_contain=[
                "roi-coverage=`2/5` (`3` missing); ROI gaps=`3`: missing actual_return: 3",
                "Focus: **Repair the primary lane ROI coverage**",
                "Repair those missing or malformed return/cost/timestamp values before treating the forward read as fully measured.",
            ],
            txt_must_contain=[
                "ROI coverage=2/5 (3 missing); ROI gaps=3: missing actual_return: 3",
            ],
            scenario="primary ROI-coverage gaps outrank normal forward reading when settlement outcomes exist but realized ROI is still partial",
        ),
        run_case(
            "case_primary_malformed_actual_cost_roi_coverage",
            primary_malformed_cost_root,
            primary_malformed_cost_run,
            "Repair the primary lane ROI coverage",
            "now",
            "paper_trade_lane_monitor.py",
            "ACTIVE, ZERO HITS",
            "malformed actual_cost: 1",
            md_must_contain=[
                "roi-coverage=`2/3` (`1` missing); ROI gaps=`1`: malformed actual_cost: 1",
                "Focus: **Repair the primary lane ROI coverage**",
                "Repair those missing or malformed return/cost/timestamp values before treating the forward read as fully measured.",
            ],
            txt_must_contain=[
                "ROI coverage=2/3 (1 missing); ROI gaps=1: malformed actual_cost: 1",
            ],
            scenario="malformed actual_cost stays visible in the right-now ROI repair action instead of being flattened into generic partial coverage",
        ),
        run_case(
            "case_primary_missing_settled_ts_roi_coverage",
            primary_missing_ts_root,
            primary_missing_ts_run,
            "Repair the primary lane ROI coverage",
            "now",
            "paper_trade_lane_monitor.py",
            "ACTIVE, ZERO HITS",
            "missing settled_ts: 1",
            md_must_contain=[
                "roi-coverage=`2/3` (`1` missing); ROI gaps=`1`: missing settled_ts: 1",
                "Focus: **Repair the primary lane ROI coverage**",
                "Repair those missing or malformed return/cost/timestamp values before treating the forward read as fully measured.",
            ],
            txt_must_contain=[
                "ROI coverage=2/3 (1 missing); ROI gaps=1: missing settled_ts: 1",
            ],
            scenario="missing settled_ts stays visible in the right-now ROI repair action even when return/cost fields are usable",
        ),
        run_case(
            "case_decision_grade",
            decision_root,
            decision_run,
            "Read the primary forward check",
            "now",
            "paper_trade_forward_check.py",
            "ACTIVE, ZERO HITS",
            "finally enough to treat the forward read as a real comparison",
            scenario="decision-grade forward review wins",
        ),
        run_case(
            "case_rerun_live_cache_miss",
            cache_miss_root,
            cache_miss_run,
            "Rerun the primary lane live, without --cache-only",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "latest cache-only check missed the day's cache files",
            scenario="active-target cache-only miss promotes rerun-live action",
        ),
        run_case(
            "case_generic_scanner_error_detail",
            generic_scanner_error_root,
            generic_scanner_error_run,
            "Refresh the daily wrapper, primary lane hit an API access failure",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "API-access scanner failure operator context",
            txt_must_contain=[
                "Primary lane context: Latest run context: scanner failed before producing signals. Detail: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx Treat this as API-access-failure operator context only, not a no-target, clean-empty, or forward-performance read. Sidecar action: refresh_daily_wrapper_before_evidence_read. Recheck command: ./run_daily_portfolio_observation.sh.",
                "Primary lane why now: The latest lane scanner failed before producing signals. Detail: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence. Refresh the daily wrapper and re-check scanner/preflight sidecars before reading the lane as evidence. Sidecar action: refresh_daily_wrapper_before_evidence_read. Recheck command: ./run_daily_portfolio_observation.sh.",
            ],
            md_must_contain=[
                "Primary lane context: Latest run context: scanner failed before producing signals. Detail: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx Treat this as API-access-failure operator context only, not a no-target, clean-empty, or forward-performance read. Sidecar action: refresh_daily_wrapper_before_evidence_read. Recheck command: ./run_daily_portfolio_observation.sh.",
                "Primary lane why now: The latest lane scanner failed before producing signals. Detail: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence. Refresh the daily wrapper and re-check scanner/preflight sidecars before reading the lane as evidence. Sidecar action: refresh_daily_wrapper_before_evidence_read. Recheck command: ./run_daily_portfolio_observation.sh.",
            ],
            scenario="generic non-cache scanner failure keeps upstream error detail visible and promotes wrapper refresh instead of looking like a quiet/no-hit or sample-collection day",
        ),
        run_case(
            "case_api_access_stale_cache_fallback_top_card",
            api_access_stale_cache_root,
            api_access_stale_cache_run,
            "Refresh the daily wrapper, primary lane hit an API access failure",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "stale-cache fallback used for cards",
            txt_must_contain=[
                "Primary lane context: Latest run context: scanner failed before producing signals. Detail: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx Treat this as API-access-failure operator context only, not a no-target, clean-empty, or forward-performance read. stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx. Sidecar action: refresh_daily_wrapper_before_evidence_read. Recheck command: ./run_daily_portfolio_observation.sh.",
                "Primary lane why now: The latest lane scanner failed before producing signals. Detail: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence. Refresh the daily wrapper and re-check scanner/preflight sidecars before reading the lane as evidence. stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx. Sidecar action: refresh_daily_wrapper_before_evidence_read. Recheck command: ./run_daily_portfolio_observation.sh.",
                "Operator read gate: Refresh/recheck with `./run_daily_portfolio_observation.sh` before using the saved top card as today's instruction or evidence; reasons: scanner/API-access failure context is present; ops bucket is ISSUE; best action points to wrapper refresh.",
            ],
            md_must_contain=[
                "Primary lane context: Latest run context: scanner failed before producing signals. Detail: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx Treat this as API-access-failure operator context only, not a no-target, clean-empty, or forward-performance read. stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx. Sidecar action: refresh_daily_wrapper_before_evidence_read. Recheck command: ./run_daily_portfolio_observation.sh.",
                "Primary lane why now: The latest lane scanner failed before producing signals. Detail: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence. Refresh the daily wrapper and re-check scanner/preflight sidecars before reading the lane as evidence. stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx. Sidecar action: refresh_daily_wrapper_before_evidence_read. Recheck command: ./run_daily_portfolio_observation.sh.",
                "Operator read gate: Refresh/recheck with `./run_daily_portfolio_observation.sh` before using the saved top card as today's instruction or evidence; reasons: scanner/API-access failure context is present; ops bucket is ISSUE; best action points to wrapper refresh.",
            ],
            scenario="top-card API-access stale-cache fallback preserves fallback count/kind/error plus action/recheck routing instead of flattening to generic scanner failure or clean-empty context",
            expected_issue_flags={
                "has_api_access_failure_context": True,
                "has_scanner_failure_boundary": True,
                "has_stale_cache_fallback_context": True,
            },
        ),
        run_case(
            "case_partial_cache_refresh",
            partial_cache_root,
            partial_cache_run,
            "Refresh the primary lane live after the partial-cache read",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ACTIVE, LIMITED COVERAGE",
            "finished empty on partial cache coverage",
            scenario="active-target partial-cache empty promotes refresh-live action",
        ),
        run_case(
            "case_partial_cache_activity_refresh",
            partial_cache_activity_root,
            partial_cache_activity_run,
            "Refresh the primary lane live after the partial-cache activity read",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ACTIVE, LIMITED COVERAGE WITH ACTIVITY",
            "still found activity on partial cache coverage",
            txt_must_contain=[
                "active-limited-coverage-with-activity=1",
                "Latest run context: the latest run depended on partial cache data but still produced 1 recommendation(s) from 1 hit(s)",
            ],
            md_must_contain=[
                "active-limited-coverage-with-activity=`1`",
                "Latest run context: the latest run depended on partial cache data but still produced 1 recommendation(s) from 1 hit(s)",
            ],
            scenario="active-target partial-cache activity keeps the surviving recommendation visible while still promoting a clean live refresh",
        ),
        run_case(
            "case_missing_scan_output_refresh",
            missing_scan_output_root,
            missing_scan_output_run,
            "Refresh the daily wrapper, primary lane scan-output artifact is missing",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "scan-output artifact was missing",
            txt_must_contain=[
                "Primary lane context: Latest run context: scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers; the pipeline used a safe empty [] fallback. Treat this as an artifact issue, not a clean no-qualifier observation.",
                "Primary lane why now: The latest lane scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers; the pipeline used a safe empty [] fallback. Treat this as an artifact issue, not a clean no-qualifier observation. Refresh the daily wrapper before treating this lane as empty.",
            ],
            md_must_contain=[
                "Focus: **Refresh the daily wrapper, primary lane scan-output artifact is missing**",
                "Primary lane context: Latest run context: scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers; the pipeline used a safe empty [] fallback. Treat this as an artifact issue, not a clean no-qualifier observation.",
                "Primary lane why now: The latest lane scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers; the pipeline used a safe empty [] fallback. Treat this as an artifact issue, not a clean no-qualifier observation. Refresh the daily wrapper before treating this lane as empty.",
            ],
            scenario="missing scan-output artifact promotes a distinct daily-wrapper refresh action instead of clean-empty or generic scanner-failure guidance",
        ),
        run_case(
            "case_pipeline_failure_refresh",
            pipeline_failure_root,
            pipeline_failure_run,
            "Refresh the daily wrapper, primary lane hit a recommender failure",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "operational issue instead of normal observation noise",
            md_must_contain=[
                "Latest run context: the latest lane run ended in recommender failure.",
                "Error type: RuntimeError.",
            ],
            scenario="explicit recommender failure promotes refresh instead of normal observe/stand-down guidance",
        ),
        run_case(
            "case_pipeline_logger_failure_refresh",
            pipeline_logger_failure_root,
            pipeline_logger_failure_run,
            "Refresh the daily wrapper, primary lane hit a logger failure",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "operational issue instead of normal observation noise",
            md_must_contain=[
                "Latest run context: the latest lane run ended in logger failure.",
                "Error type: ValueError.",
            ],
            scenario="explicit logger failure promotes refresh instead of normal observe/stand-down guidance",
        ),
        run_case(
            "case_shadow_open",
            shadow_open_root,
            shadow_open_run,
            "Settle the shadow lane queue",
            "now",
            "paper_trade_settlement_helper.py list-open",
            "NO TARGETS",
            "shadow settlement row(s) still need results",
            md_must_contain=[
                "out/status_validation/paper_trade_now_fixture/case_shadow_open/out/daily_portfolio_runs/2026-05-08/phase8_shadow/summary.txt",
                "out/status_validation/paper_trade_now_fixture/case_shadow_open/out/daily_portfolio_runs/2026-05-08/phase8_shadow/next_steps.md",
            ],
            scenario="shadow settlement queue wins when primary is clear",
        ),
        run_case(
            "case_shadow_decision_grade",
            shadow_decision_root,
            shadow_decision_run,
            "Read the shadow forward check",
            "now",
            "paper_trade_forward_check.py",
            expected_why_contains="shadow lane now has 30 settled races",
            md_must_contain=[
                "out/status_validation/paper_trade_now_fixture/case_shadow_decision_grade/out/daily_portfolio_runs/2026-05-12/phase8_shadow/summary.txt",
                "out/status_validation/paper_trade_now_fixture/case_shadow_decision_grade/out/daily_portfolio_runs/2026-05-12/phase8_shadow/next_steps.md",
                "out/status_validation/paper_trade_now_fixture/case_shadow_decision_grade/out/daily_portfolio_runs/2026-05-12/phase8_shadow/lane_monitor.md",
            ],
            scenario="shadow decision-grade review wins when the primary lane is clear",
        ),
        run_case(
            "case_no_targets",
            no_target_root,
            no_target_run,
            "Stand down, no OP / CD target action tonight",
            "next OP / CD race day",
            "./run_daily_portfolio_observation.sh",
            "NO TARGETS",
            "explained by the race calendar, not by a rules miss",
            scenario="no-target stand-down wins",
        ),
        run_case(
            "case_primary_relocated_scanner_status",
            relocated_scanner_root,
            relocated_scanner_run,
            "Stand down, no OP / CD target action tonight",
            "next OP / CD race day",
            "./run_daily_portfolio_observation.sh",
            "NO TARGETS",
            "explained by the race calendar, not by a rules miss",
            txt_must_contain=[
                "Primary lane context: Latest run context: no matching cards were available for this ruleset in the latest scan window.",
                "Primary lane status sidecars: pipeline=out/status_validation/paper_trade_now_fixture/case_primary_relocated_scanner_status/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/pipeline_status.json | scanner=out/status_validation/paper_trade_now_fixture/case_primary_relocated_scanner_status/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/renamed_live_scan.status.json",
            ],
            md_must_contain=[
                "Primary lane context: Latest run context: no matching cards were available for this ruleset in the latest scan window.",
                "Primary lane status sidecars: pipeline=`out/status_validation/paper_trade_now_fixture/case_primary_relocated_scanner_status/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/pipeline_status.json`, scanner=`out/status_validation/paper_trade_now_fixture/case_primary_relocated_scanner_status/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/renamed_live_scan.status.json`",
            ],
            scenario="top card recovers a lane-local relative pipeline-declared renamed scanner sidecar instead of linking to the default missing filename",
        ),
        run_case(
            "case_primary_relocated_scanner_status_run_root_relative",
            relocated_run_root_scanner_root,
            relocated_run_root_scanner_run,
            "Stand down, no OP / CD target action tonight",
            "next OP / CD race day",
            "./run_daily_portfolio_observation.sh",
            "NO TARGETS",
            "explained by the race calendar, not by a rules miss",
            txt_must_contain=[
                "Primary lane context: Latest run context: no matching cards were available for this ruleset in the latest scan window.",
                "Primary lane status sidecars: pipeline=out/status_validation/paper_trade_now_fixture/case_primary_relocated_scanner_status_run_root_relative/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/pipeline_status.json | scanner=out/status_validation/paper_trade_now_fixture/case_primary_relocated_scanner_status_run_root_relative/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/renamed_live_scan.status.json",
            ],
            md_must_contain=[
                "Primary lane context: Latest run context: no matching cards were available for this ruleset in the latest scan window.",
                "Primary lane status sidecars: pipeline=`out/status_validation/paper_trade_now_fixture/case_primary_relocated_scanner_status_run_root_relative/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/pipeline_status.json`, scanner=`out/status_validation/paper_trade_now_fixture/case_primary_relocated_scanner_status_run_root_relative/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/renamed_live_scan.status.json`",
            ],
            scenario="top card recovers a run-root relative pipeline-declared renamed scanner sidecar instead of linking to the default missing filename",
        ),
        run_case(
            "case_primary_relocated_scanner_status_project_relative",
            relocated_project_scanner_root,
            relocated_project_scanner_run,
            "Stand down, no OP / CD target action tonight",
            "next OP / CD race day",
            "./run_daily_portfolio_observation.sh",
            "NO TARGETS",
            "explained by the race calendar, not by a rules miss",
            txt_must_contain=[
                "Primary lane context: Latest run context: no matching cards were available for this ruleset in the latest scan window.",
                "Primary lane status sidecars: pipeline=out/status_validation/paper_trade_now_fixture/case_primary_relocated_scanner_status_project_relative/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/pipeline_status.json | scanner=out/status_validation/paper_trade_now_fixture/case_primary_relocated_scanner_status_project_relative/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/renamed_live_scan.status.json",
            ],
            md_must_contain=[
                "Primary lane context: Latest run context: no matching cards were available for this ruleset in the latest scan window.",
                "Primary lane status sidecars: pipeline=`out/status_validation/paper_trade_now_fixture/case_primary_relocated_scanner_status_project_relative/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/pipeline_status.json`, scanner=`out/status_validation/paper_trade_now_fixture/case_primary_relocated_scanner_status_project_relative/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/renamed_live_scan.status.json`",
            ],
            scenario="top card recovers a project-relative pipeline-declared renamed scanner sidecar instead of linking to the default missing filename",
        ),
        run_case(
            "case_primary_declared_scanner_beats_stale_default",
            declared_beats_stale_scanner_root,
            declared_beats_stale_scanner_run,
            "Stand down, no OP / CD target action tonight",
            "next OP / CD race day",
            "./run_daily_portfolio_observation.sh",
            "NO TARGETS",
            "explained by the race calendar, not by a rules miss",
            txt_must_contain=[
                "Primary lane context: Latest run context: no matching cards were available for this ruleset in the latest scan window.",
                "Primary lane status sidecars: pipeline=out/status_validation/paper_trade_now_fixture/case_primary_declared_scanner_beats_stale_default/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/pipeline_status.json | scanner=out/status_validation/paper_trade_now_fixture/case_primary_declared_scanner_beats_stale_default/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/renamed_live_scan.status.json",
            ],
            md_must_contain=[
                "Primary lane context: Latest run context: no matching cards were available for this ruleset in the latest scan window.",
                "Primary lane status sidecars: pipeline=`out/status_validation/paper_trade_now_fixture/case_primary_declared_scanner_beats_stale_default/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/pipeline_status.json`, scanner=`out/status_validation/paper_trade_now_fixture/case_primary_declared_scanner_beats_stale_default/out/daily_portfolio_runs/2026-05-11/phase7_current_paper/renamed_live_scan.status.json`",
            ],
            scenario="top card prefers a pipeline-declared renamed scanner sidecar over a stale default scanner filename",
        ),
        run_case(
            "case_stale_no_target_run",
            stale_no_target_root,
            stale_no_target_run,
            "Refresh the daily wrapper, latest operator card is stale",
            "now",
            "./run_daily_portfolio_observation.sh",
            "NO TARGETS",
            "saved operator card is 2 day(s) old",
            md_must_contain=[
                "Run freshness: Latest run date `2026-05-06` is 2 day(s) behind the as-of date `2026-05-08`",
                "Freshness state: `stale_past_run`",
                "Stale snapshot note: The preflight note/artifact, excluded-track aliases, lane context, current-state counts, ops streaks, and quick reads below are inherited from the latest saved run (`2026-05-06`) and should be treated as stale snapshot context until the daily wrapper is rerun.",
            ],
            txt_must_contain=[
                "- Run freshness: Latest run date `2026-05-06` is 2 day(s) behind the as-of date `2026-05-08`",
                "- Freshness state: stale_past_run",
                "- Stale snapshot note: The preflight note/artifact, excluded-track aliases, lane context, current-state counts, ops streaks, and quick reads below are inherited from the latest saved run (`2026-05-06`) and should be treated as stale snapshot context until the daily wrapper is rerun.",
            ],
            scenario="stale saved no-target card promotes refresh instead of stale stand-down guidance while marking downstream lane context as inherited snapshot state",
            as_of_date="2026-05-08",
        ),
        run_case(
            "case_undated_run_folder_refresh",
            undated_run_root,
            undated_run,
            "Refresh the daily wrapper, latest operator card is stale",
            "now",
            "./run_daily_portfolio_observation.sh",
            "NO TARGETS",
            "saved operator card is out of sync with the as-of date",
            md_must_contain=[
                "Run freshness: Latest run folder `latest-run-copy` is not an ISO date, so the saved top card is stale until the daily wrapper is rerun or a dated run folder is selected.",
                "Freshness state: `unknown_run_date`",
                "Stale snapshot note: The preflight note/artifact, excluded-track aliases, lane context, current-state counts, ops streaks, and quick reads below are inherited from the latest saved run (`latest-run-copy`) and should be treated as stale snapshot context until the daily wrapper is rerun.",
            ],
            txt_must_contain=[
                "- Run freshness: Latest run folder `latest-run-copy` is not an ISO date, so the saved top card is stale until the daily wrapper is rerun or a dated run folder is selected.",
                "- Freshness state: unknown_run_date",
                "- Stale snapshot note: The preflight note/artifact, excluded-track aliases, lane context, current-state counts, ops streaks, and quick reads below are inherited from the latest saved run (`latest-run-copy`) and should be treated as stale snapshot context until the daily wrapper is rerun.",
            ],
            scenario="undated copied run folder fails closed to daily-wrapper refresh instead of becoming a clean no-target stand-down card",
            as_of_date="2026-05-08",
        ),
        run_case(
            "case_json_only_preflight_note",
            json_only_preflight_root,
            json_only_preflight_run,
            "Stand down, no OP / CD target action tonight",
            "next OP / CD race day",
            "./run_daily_portfolio_observation.sh",
            "NO TARGETS",
            "explained by the race calendar, not by a rules miss",
            md_must_contain=[
                "Preflight note: JSON-only preflight note: no active OP/CD cards today; KEE is shadow-only.",
            ],
            txt_must_contain=[
                "- Preflight note: JSON-only preflight note: no active OP/CD cards today; KEE is shadow-only.",
            ],
            scenario="top-card preflight note falls back to saved JSON when the sibling text surface is missing",
        ),
        run_case(
            "case_empty_text_prefers_json_preflight_note",
            empty_text_json_note_root,
            empty_text_json_note_run,
            "Stand down, no OP / CD target action tonight",
            "next OP / CD race day",
            "./run_daily_portfolio_observation.sh",
            "NO TARGETS",
            "explained by the race calendar, not by a rules miss",
            md_must_contain=[
                "Preflight note: JSON survives even if sibling text file is blank.",
                "Preflight note artifact: `out/status_validation/paper_trade_now_fixture/case_empty_text_prefers_json_preflight_note/out/daily_portfolio_runs/2026-05-17/preflight_note.json`",
                "- Excluded track aliases: BAQ (not treated as BEL)",
            ],
            txt_must_contain=[
                "- Preflight note: JSON survives even if sibling text file is blank.",
                "- Preflight note artifact: out/status_validation/paper_trade_now_fixture/case_empty_text_prefers_json_preflight_note/out/daily_portfolio_runs/2026-05-17/preflight_note.json",
                "- Excluded track aliases: BAQ (not treated as BEL)",
            ],
            scenario="top-card still prefers the saved JSON note when the sibling text artifact exists but is blank",
        ),
        run_case(
            "case_missing_json_preflight_note_field",
            missing_json_note_root,
            missing_json_note_run,
            "Stand down, no OP / CD target action tonight",
            "next OP / CD race day",
            "./run_daily_portfolio_observation.sh",
            "NO TARGETS",
            "explained by the race calendar, not by a rules miss",
            md_must_contain=[
                "Preflight note: [missing preflight note field: out/status_validation/paper_trade_now_fixture/case_missing_json_preflight_note_field/out/daily_portfolio_runs/2026-05-18/preflight_note.json]",
                "Preflight note artifact: `out/status_validation/paper_trade_now_fixture/case_missing_json_preflight_note_field/out/daily_portfolio_runs/2026-05-18/preflight_note.json`",
            ],
            txt_must_contain=[
                "- Preflight note: [missing preflight note field: out/status_validation/paper_trade_now_fixture/case_missing_json_preflight_note_field/out/daily_portfolio_runs/2026-05-18/preflight_note.json]",
                "- Preflight note artifact: out/status_validation/paper_trade_now_fixture/case_missing_json_preflight_note_field/out/daily_portfolio_runs/2026-05-18/preflight_note.json",
            ],
            scenario="top-card keeps an explicit placeholder when only preflight JSON survives but its note field is missing",
        ),
        run_case(
            "case_json_only_active_target_preflight",
            json_only_active_target_root,
            json_only_active_target_run,
            "Rerun the primary lane live, without --cache-only",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "latest cache-only check missed the day's cache files",
            md_must_contain=[
                "Preflight note: JSON-only preflight note: OP is still active today.",
            ],
            txt_must_contain=[
                "- Preflight note: JSON-only preflight note: OP is still active today.",
            ],
            scenario="top-card preflight note falls back to saved JSON on an active-target rerun-live day when the sibling text surface is missing",
        ),
        run_case(
            "case_empty_text_active_target_prefers_json_preflight_note",
            empty_text_active_target_root,
            empty_text_active_target_run,
            "Rerun the primary lane live, without --cache-only",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "latest cache-only check missed the day's cache files",
            md_must_contain=[
                "Preflight note: JSON still wins on an active-target day when sibling text file is blank.",
                "Preflight note artifact: `out/status_validation/paper_trade_now_fixture/case_empty_text_active_target_prefers_json_preflight_note/out/daily_portfolio_runs/2026-05-19/preflight_note.json`",
            ],
            txt_must_contain=[
                "- Preflight note: JSON still wins on an active-target day when sibling text file is blank.",
                "- Preflight note artifact: out/status_validation/paper_trade_now_fixture/case_empty_text_active_target_prefers_json_preflight_note/out/daily_portfolio_runs/2026-05-19/preflight_note.json",
            ],
            scenario="top-card still prefers the saved JSON note on an active-target rerun-live day when the sibling text artifact exists but is blank",
        ),
        run_case(
            "case_unknown_calendar",
            unknown_calendar_root,
            unknown_calendar_run,
            "Refresh the daily wrapper, calendar state is unknown",
            "now",
            "./run_daily_portfolio_observation.sh",
            "UNKNOWN CALENDAR",
            "operationally ambiguous",
            md_must_contain=[
                "Preflight context: calendar state unknown because the upstream card check failed.",
            ],
            scenario="unknown-calendar day promotes refresh instead of stand-down",
        ),
        run_case(
            "case_missing_primary_status",
            missing_status_root,
            missing_status_run,
            "Refresh the daily wrapper, primary lane pipeline status is missing",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "pipeline status artifact is missing",
            scenario="missing primary sidecar promotes refresh-artifacts action",
        ),
        run_case(
            "case_empty_primary_status",
            empty_status_root,
            empty_status_run,
            "Refresh the daily wrapper, primary lane pipeline status is empty",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "pipeline status artifact is empty",
            scenario="empty primary pipeline sidecar promotes a distinct refresh-artifacts action",
        ),
        run_case(
            "case_malformed_primary_status",
            malformed_status_root,
            malformed_status_run,
            "Refresh the daily wrapper, primary lane pipeline status is unreadable",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "pipeline status artifact is unreadable",
            scenario="malformed primary sidecar promotes refresh-artifacts action",
        ),
        run_case(
            "case_malformed_primary_scanner_status",
            malformed_scanner_root,
            malformed_scanner_run,
            "Refresh the daily wrapper, primary lane scanner sidecar is unreadable",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "scanner status sidecar is unreadable",
            scenario="malformed primary scanner sidecar keeps the top-card refresh guidance specific",
        ),
        run_case(
            "case_empty_primary_scanner_status",
            empty_scanner_root,
            empty_scanner_run,
            "Refresh the daily wrapper, primary lane scanner sidecar is empty",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "scanner status sidecar is empty",
            scenario="empty primary scanner sidecar keeps the top-card refresh guidance specific",
        ),
        run_case(
            "case_pipeline_recorded_empty_primary_scanner_missing",
            recorded_empty_scanner_root,
            recorded_empty_scanner_run,
            "Refresh the daily wrapper, primary lane scanner sidecar was recorded empty",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "scanner status sidecar was recorded empty by the pipeline",
            scenario="pipeline-recorded empty primary scanner-status state keeps the top-card refresh guidance specific when the copied surface lacks the physical scanner sidecar",
        ),
        run_case(
            "case_pipeline_recorded_unreadable_primary_scanner_missing",
            recorded_unreadable_scanner_root,
            recorded_unreadable_scanner_run,
            "Refresh the daily wrapper, primary lane scanner sidecar was recorded unreadable",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "scanner status sidecar was recorded unreadable by the pipeline",
            scenario="pipeline-recorded unreadable primary scanner-status state keeps the top-card refresh guidance specific when the copied surface lacks the physical scanner sidecar",
        ),
        run_case(
            "case_pipeline_recorded_invalid_shape_primary_scanner_missing",
            recorded_invalid_shape_scanner_root,
            recorded_invalid_shape_scanner_run,
            "Refresh the daily wrapper, primary lane scanner sidecar was recorded invalid-shape",
            "now",
            "./run_daily_portfolio_observation.sh",
            "ISSUE",
            "scanner status sidecar was recorded invalid-shape by the pipeline",
            scenario="pipeline-recorded invalid-shape primary scanner-status state keeps the top-card refresh guidance specific when the copied surface lacks the physical scanner sidecar",
        ),
    ]
    live_surface_result = validate_live_surfaces()
    results = fixture_results + [live_surface_result]
    scratch = build_fixture_scratch_metadata()
    if (
        scorecard_gates.get("source") != "forward_evidence_scorecard.json"
        or scorecard_gates.get("source_path") != "decision_gate_minimums"
        or scorecard_gates.get("anchor_displacement_min_roi_complete_settled_observations") != 30
        or scorecard_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") != 20
        or scorecard_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") != 100
        or scorecard_gates.get("real_money_no_baq_as_bel_required") is not True
        or "no BAQ-as-BEL substitution" not in scorecard_gates.get("real_money_also_requires", [])
    ):
        raise AssertionError("right-now scorecard gate boundary no longer matches forward_evidence_scorecard.json")
    if (
        scratch.get("fixture_root_relative") != "out/status_validation/paper_trade_now_fixture"
        or scratch.get("fixture_root_is_project_local") is not True
        or scratch.get("case_roots_cleared_by_setup_case") is not True
    ):
        raise AssertionError("right-now fixture scratch metadata no longer proves a project-local cleared fixture root")

    suite_read = (
        "paper-trade-now still prioritizes primary or shadow settlement first, with open primary settlement/recommendation-state context preserved as workflow routing rather than bet-ready or forward-performance posture, explicit incomplete-settlement cleanup when rows are marked settled but still missing outcomes, explicit missing/malformed/timestamp ROI-coverage repair when settled outcomes exist but realized ROI still only covers part of the lane, including compact ROI gap reason summaries such as missing settled_ts in the text and markdown lane context, primary or shadow decision-grade review when that lane finally has enough settled races, stale-run refresh when the saved top card predates the as-of day or the latest run folder is undated, plus a structured freshness_state and an explicit stale-snapshot note so inherited preflight note/artifact, excluded-track aliases, lane context, counts, ops streaks, and quick reads do not masquerade as current state, rerun-live after cache-only miss, "
        "refresh after partial-cache empty or partial-cache-with-activity reads, missing scan-output artifact refresh, explicit scanner/API-access-failure refresh with stale-cache fallback count/kind/error preservation, explicit recommender/logger pipeline-failure refresh, unknown-calendar ambiguity, or missing scan-output plus missing-vs-empty-vs-unreadable-vs-invalid-shape primary pipeline/scanner artifact recovery plus pipeline-recorded empty/unreadable/invalid-shape scanner-status states when copied surfaces lack the physical scanner sidecar, and honest no-target stand-down, while now also preserving upstream scanner-error detail in lane context and lane-why refresh routing for generic non-cache scanner failures, falling back to saved preflight JSON note text when the sibling preflight text surface is missing on both the no-target stand-down branch and the active-target rerun-live branch, still preferring that saved JSON note when the sibling text artifact exists but is blank on both the no-target stand-down branch and the active-target rerun-live branch, keeping an explicit placeholder when only the preflight JSON artifact survives but its `note` field is missing, recovering lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars and preferring the declared sidecar over a stale default scanner filename (`live_scan.status.json`), so the top card's direct machine-readable pointer stays honest, carrying the explicit OP_DURABLE_K7 / CD_CORE_K8 / OP_REFINED_K7 live lane hierarchy block plus the narrower shadow-lane triage that keeps OP_REFINED_K7 as the closest challenger while KEE_K9 / SA_K9 / DMR_FALL_K7 stay observation-only pockets, an explicit operational-evidence-frame disclaimer, and the replay-context caution that broader selective-family secondary lines stay replay context on walk-forward test years rather than extra train-only validation, dual primary/shadow lane-context lines and dual primary/shadow lane-why lines when those underlying next-steps surfaces save them, the full routed recommendation-lane quick-reads bundle, the routed preflight-note source path, direct primary/shadow pipeline/scanner status-sidecar pointers, the routed settlement-audit pointer, shadow per-rule promotion gate and coverage line from the audit JSON, explicit active-limited-coverage-with-activity streak context in the top card, and scorecard-sourced right-now decision-gate metadata from forward_evidence_scorecard.json decision_gate_minimums, with the saved and shell-facing JSON, text, and markdown surfaces pinned to fresh source-layer payload and render output, including JSON parity for the settlement-audit pointer, active right-now gate fields, and shadow per-rule promotion-gate fields and the direct validator report now published at the standard paper-trade-now validation path; "
        "including structured preflight excluded-track alias visibility so BAQ remains explicitly not BEL when the saved JSON carries that calendar context; "
        "the right-now validator report now publishes the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as action-routing boundary metadata only and rejects malformed scorecard gates, including boolean and non-positive copied-gate floors, before creating fixture/report artifacts; paper-trade-now layer: machine-readable `valid_evidence_scope`, visible `valid_evidence_scope=operator_action_routing_only` text/markdown output, direct validation report `valid_evidence_scope=operator_action_routing_only`, `evidence_boundary`, `action_priority_contract`, and `operator_read_gate` fields preserve the operator action-priority/read-gating contract, not no-target, clean-empty, settled-ROI, promotion, live-profitability, bankroll, real-money, or new forward evidence by itself; stronger forward confidence still requires settled paper trades and other real forward results"
        "; project-local fixture scratch metadata is now published as a structured guardrail so parent rollups can verify the isolated top-card fixture root directly"
    )

    child_checks = [
        *scorecard_artifact_guardrails,
        {
            "check": "fixture_branches_and_navigation_bundle_stay_covered",
            "status": "pass",
            "detail": "synthetic fixtures still cover the main top-card branches, including settle-first with open primary settlement/recommendation-state context preserved as workflow routing rather than bet-readiness or forward-performance proof, missing/malformed/timestamp ROI repair, decision-grade, stale-run refresh, undated-run-folder freshness refresh, cache-miss rerun-live, generic non-cache scanner/API-access-failure detail preservation plus refresh routing, partial-cache refresh, missing scan-output refresh, pipeline-failure refresh, missing/empty/unreadable/invalid-shape artifact-issue refresh, pipeline-recorded scanner-status refresh, and no-target stand-down, while pinning the full routed navigation bundle",
        },
        {
            "check": "api_access_stale_cache_fallback_top_card_context_stays_pinned",
            "status": "pass",
            "detail": "the top-card validator now has a direct API-access stale-cache fallback fixture proving lane context, lane why-now, best action, and operator_read_gate keep HTTP 403, stale-cache fallback count/kind/error, true issue booleans, refresh_daily_wrapper_before_evidence_read, and ./run_daily_portfolio_observation.sh visible instead of flattening to clean-empty/no-target or generic scanner-failure context",
        },
        {
            "check": "live_surface_drift_check_stays_pinned_to_current_render",
            "status": "pass",
            "detail": "the saved live PAPER_TRADE_NOW text and markdown surfaces still have to match the current latest-run render instead of drifting behind source-layer changes",
        },
        {
            "check": "stale_snapshot_hierarchy_and_evidence_boundary_stay_explicit",
            "status": "pass",
            "detail": "the top card still says plainly when preflight, excluded-alias, lane, count, ops, and quick-read context is inherited from a stale snapshot, publishes structured freshness_state values including undated-run-folder failure, keeps the explicit OP_DURABLE_K7 / CD_CORE_K8 / OP_REFINED_K7 lane hierarchy, carries the shadow settlement-audit per-rule promotion gate plus coverage line, and preserves the operational-priority/not-new-evidence boundary",
        },
        {
            "check": "relocated_sidecar_and_routed_context_pointers_stay_explicit",
            "status": "pass",
            "detail": "the top card still keeps routed preflight and primary/shadow sidecar pointers explicit, including JSON-note fallback when text is missing or blank on both the no-target and active-target branches, explicit missing-note placeholders when only malformed preflight JSON survives, recovery of lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars, declared-sidecar precedence over stale default scanner filenames, plus per-lane context and why lines",
        },
        {
            "check": "right_now_scorecard_gate_source_stays_explicit",
            "status": "pass",
            "detail": "text, markdown, and JSON top-card surfaces now have to carry scorecard-sourced primary_min_settled, shadow_min_settled, and portfolio_review_settled metadata from forward_evidence_scorecard.json decision_gate_minimums, with primary 30 / shadow 20 lane-specific first-read gates and no CLI override drift on the default path",
        },
        {
            "check": "paper_trade_now_explicitly_stays_action_priority_not_new_evidence",
            "status": "pass",
            "detail": "JSON fixtures and live surfaces now publish `valid_evidence_scope`, text/markdown surfaces publish `valid_evidence_scope=operator_action_routing_only`, and `evidence_boundary`, `action_priority_contract`, and `operator_read_gate` fields stay pinned, while the direct validator summary still says plainly that paper_trade_now is an operator action-priority/read-gating surface, not no-target, clean-empty, settled-ROI, promotion, live-profitability, bankroll, real-money, or new forward evidence by itself",
        },
        {
            "check": "direct_validation_report_exposes_right_now_valid_scope",
            "status": "pass",
            "detail": "the direct paper-trade-now validation markdown, JSON, and evidence_boundary block now expose valid_evidence_scope=operator_action_routing_only so the report artifact itself cannot be copied as no-target, clean-empty, settled-ROI, promotion, live-profitability, bankroll, real-money, or new forward evidence",
        },
        {
            "check": "fixture_scratch_metadata_published",
            "status": "pass",
            "detail": "paper_trade_now validation publishes top-level project-local fixture scratch metadata so parent rollups can verify the isolated fixture root without parsing markdown prose",
        },
    ]

    report_lines = [
        "# Paper-Trade Right-Now Validation",
        "",
        "This report validates the `paper_trade_now.py` CLI against synthetic cases under `out/status_validation/paper_trade_now_fixture/`, while publishing the direct validator readout under `out/status_validation/paper_trade_now/`.",
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
        "| Case | Expected branch | Actual headline | Timing | Primary state | Ops bucket | Output surfaces |",
        "|---|---|---|---|---|---|---|",
        *[
            f"| `{row['case']}` | {row['scenario']} | {row['headline']} | {row['timing']} | {row['primary_state']} | {row['day_bucket']} | `{row['output_json']}`, `{row['output_txt']}`, `{row['output_md']}` |"
            for row in fixture_results
        ],
        "",
        "## Live current surface",
        "",
        f"- Latest live run: `{live_surface_result['run_root']}`",
        f"- Current headline: **{live_surface_result['headline']}**",
        f"- Current timing: **{live_surface_result['timing']}**",
        f"- Current ops bucket: **{live_surface_result['day_bucket']}**",
        f"- Live surfaces pinned: `{live_surface_result['output_txt']}`, `{live_surface_result['output_md']}`",
        "",
        "## Validation result",
        "",
        f"- All {len(fixture_results)} synthetic fixture cases now pass their expected headline, timing, command-shape, ops-bucket, `why` explanation, the routed preflight-note source-path assertion, direct routed primary/shadow status-sidecar path assertions, and full routed recommendation-lane quick-reads bundle assertions (`summary.txt`, `next_steps.md`, `lane_monitor.md`, `daily_summary.txt`, and `OPS_HISTORY.md`).",
        "- The validator now also fails if the real `PAPER_TRADE_NOW.txt` or `PAPER_TRADE_NOW.md` drifts from the current latest-run render, including stale recommendation-lane quick-read paths, a dropped routed preflight-note source path, dropped ROI-coverage gap reason context, lost saved-preflight-JSON fallback when the sibling text note is missing or blank on either side of the calendar split, or JSON accidentally written into the markdown top-card path.",
        "- The saved and shell-facing JSON, text, and markdown fixture outputs remain pinned directly against fresh `build_payload(...)`, `render_text(...)`, and `render_md(...)` output from `paper_trade_now.py`.",
        "- This keeps the top-level operator card honest across the main current branches: settle either lane first, repair missing or malformed return/cost/timestamp realized-ROI coverage before review/sample guidance, review either lane when it reaches decision-grade, rerun live after cache-only misses, refresh after partial-cache empty reads, refresh after partial-cache activity reads that still need a clean rerun, refresh after missing scan-output artifacts, refresh after explicit recommender/logger pipeline failures, refresh when the preflight calendar state is unknown, refresh when the latest run folder is undated instead of treating a copied folder as current, distinguish missing vs empty vs unreadable vs invalid-shape primary pipeline/scanner artifacts plus pipeline-recorded empty/unreadable/invalid-shape scanner-status states when refresh is needed, and stand down on true no-target days.",
        "- On stale-card days, the text and markdown surfaces now also say plainly that the lane context, current-state counts, and quick reads underneath are inherited snapshot context from the latest saved run rather than current-day live state, and they expose a structured freshness state so stale-past-run, future-date, current-date, and unknown-run-date cases cannot be collapsed together."
        "- The markdown top card now also carries a dedicated live lane hierarchy block so `primary` and `shadow` stay tied to `OP_DURABLE_K7`, `CD_CORE_K8`, and `OP_REFINED_K7`, while the narrower shadow-lane triage keeps OP_REFINED_K7 as the closest challenger and KEE_K9 / SA_K9 / DMR_FALL_K7 as observation-only pockets instead of letting Phase 8 read like a soft promotion queue.",
        "- The top card now also carries the routed settlement-audit pointer, shadow/watch per-rule promotion gate and per-rule coverage line from audit JSON, so OP_REFINED_K7 and the other Phase 8 pockets cannot look promotion-ready from lane totals alone.",
        "- The text and markdown top cards now also say plainly that `paper_trade_now` is an operational priority surface driven by current run artifacts plus the frozen lane hierarchy, not a profit-proof or CI-backed forward-validation card.",
        "- The JSON/text/markdown top cards now also carry a machine-readable action-priority contract, an `operator_read_gate` with explicit API-access / scanner-failure / stale-cache-fallback issue booleans, and evidence-boundary flags, so downstream consumers can tell that `best_action` routing is current-run workflow/read-gating metadata rather than no-target proof, clean-empty proof, settled ROI, promotion readiness, anchor-displacement proof, live-profitability, bankroll guidance, or real-money evidence.",
        "- The top card now also carries the routed preflight-note source path directly, so Cole can jump from the rendered note text back to the actual saved `preflight_note.txt` or `preflight_note.json` surface that produced it.",
        "- The top card now also carries structured preflight excluded-track alias visibility from `preflight_note.json`, so a copied or JSON-backed run can keep `BAQ (not treated as BEL)` visible even when the sibling text note is blank or missing.",
        "- The top card now also carries direct primary/shadow machine-readable sidecar pointers, and it now recovers lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars while preferring the pipeline-declared sidecar over a stale default `live_scan.status.json`, so cache-miss, partial-cache, or pipeline-failure days can still jump straight from the human-facing card to the real sidecars that explain the operational branch.",
        "- The top card now also carries explicit primary/shadow lane-context lines and per-lane `Why` lines when the underlying next-steps surfaces save them, so cross-lane cache-miss, failure, or sample-readiness explanation cannot disappear just because only one lane owns the current recommendation headline.",
        "- The quick-read block now proves the full routed recommendation-lane navigation bundle directly instead of only one routed link, so the top card cannot quietly lose `summary.txt`, `next_steps.md`, `lane_monitor.md`, or `daily_summary.txt` while rebuild parity stays green.",
        "- The top card now also publishes active decision-gate metadata sourced from `forward_evidence_scorecard.json` `decision_gate_minimums`, so default right-now sample/readiness gates follow the same lane-specific 30/20/100 scorecard thresholds used by the forward-check, lane-monitor, and next-steps layers rather than a local hardcoded threshold.",
        "- The validator now fails before creating fixture/report artifacts when the scorecard has malformed gate floors or drops the no-BAQ-as-BEL prerequisite.",
        "- The validator JSON now also publishes thirteen explicit structured guardrails, so parent rollups can verify fail-before-artifacts scorecard checks, branch coverage, live-surface drift parity, stale-snapshot disclosure, relocated-sidecar pointer recovery, scorecard-sourced right-now gate visibility, the direct valid-scope report line, the operator-read-gate/not-new-evidence boundary, and project-local fixture scratch metadata directly instead of inferring them only from totals plus prose.",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
        f"- `valid_evidence_scope={source_now.RIGHT_NOW_VALID_EVIDENCE_SCOPE}`",
        f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
        "- Boundary: right-now validator cleanliness is operator action-priority metadata only, not new forward evidence, not a live paper-trade ledger, not a current-day scanner result, not settled ROI, not live profitability, not promotion readiness, and not real-money evidence.",
        "- Non-goals: do not treat right-now action routing, stale snapshot context, quick-read visibility, active gate lines, or green validators as ROI-complete observations, profitability evidence, promotion support, or real-money support.",
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
    ]
    payload = {
        "suite_status": "pass",
        "total_fixture_scenarios": len(fixture_results),
        "total_checks": len(results),
        "check_count": len(results),
        "fixture_case_count": len(fixture_results),
        "live_surface_checks": 1,
        "results": results,
        "child_check_count": len(child_checks),
        "child_checks": child_checks,
        "summary": {
            "suite_read": suite_read,
        },
        "valid_evidence_scope": source_now.RIGHT_NOW_VALID_EVIDENCE_SCOPE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "scratch": scratch,
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "fixture_root": str(FIXTURE_ROOT.relative_to(BASE)),
            "report_path": str(REPORT_MD.relative_to(BASE)),
        },
    }

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    for legacy in (
        FIXTURE_ROOT / "paper_trade_now_fixture_validation.md",
        FIXTURE_ROOT / "paper_trade_now_fixture_validation.json",
    ):
        legacy.unlink(missing_ok=True)
    report_body = "\n".join(report_lines)
    report_json_body = json.dumps(payload, indent=2) + "\n"
    scope_line = f"valid_evidence_scope={source_now.RIGHT_NOW_VALID_EVIDENCE_SCOPE}"
    if f"- `{scope_line}`" not in report_body:
        raise AssertionError("paper_trade_now direct validation report lost its visible valid_evidence_scope line")
    if payload.get("valid_evidence_scope") != source_now.RIGHT_NOW_VALID_EVIDENCE_SCOPE:
        raise AssertionError("paper_trade_now direct validation JSON lost its top-level valid_evidence_scope")
    if payload.get("evidence_boundary", {}).get("valid_evidence_scope") != source_now.RIGHT_NOW_VALID_EVIDENCE_SCOPE:
        raise AssertionError("paper_trade_now evidence_boundary lost its valid_evidence_scope")

    write_text(REPORT_MD, report_body)
    write_text(REPORT_JSON, report_json_body)

    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    for row in results:
        print(f"PASS {row['case']}: {row['headline']} -> {row['command']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
