#!/usr/bin/env python3
"""
Fixture-driven validation for paper_trade_status_summary.py.

Purpose:
- pin the one-line base status summary the wrapper depends on before lane enrichment
- keep scanner-only alerts, cache-miss, scanner-failure, API-access stale-cache fallback, partial-cache, clean-empty, empty/unreadable/invalid-shape scanner-sidecar, empty/unreadable/invalid-shape/missing required-pipeline sidecar, and bet-ready wording reproducible across text and JSON paths where those branches matter operationally
- validate the helper's explicit failure contract when no readable sidecars exist
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import paper_trade_status_summary as status_summary_source

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "paper_trade_status_summary.py"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "status_summary_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_status_summary"
REPORT_MD = OUT_DIR / "paper_trade_status_summary_validation.md"
REPORT_JSON = OUT_DIR / "paper_trade_status_summary_validation.json"
REBUILD_COMMAND = "python3 validate_paper_trade_status_summary.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
API_ACCESS_ACTION_TEXT = "operator action refresh_daily_wrapper_before_evidence_read"
API_ACCESS_RECHECK_TEXT = "recheck command ./run_daily_portfolio_observation.sh"
STATUS_SUMMARY_VALID_SCOPE_LINE = f"valid_evidence_scope={status_summary_source.STATUS_VALID_SCOPE}"

VALIDATOR_EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade status-summary validator",
    "source_scope": [
        "paper_trade_status_summary.py fixture outputs",
        "forward_evidence_scorecard.json decision_gate_minimums",
    ],
    "valid_use": "base operator-state routing validation before lane enrichment",
    "valid_evidence_scope": status_summary_source.STATUS_VALID_SCOPE,
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "status_summary_validator_passes_are_operator_state_metadata_only": True,
}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, indent=2) + "\n")


def assert_contains(text: str, needle: str, case_name: str) -> None:
    if needle not in text:
        raise AssertionError(f"{case_name}: expected to find {needle!r}")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def pass_check(check: str, detail: str) -> dict[str, str]:
    return {"check": check, "status": "pass", "detail": detail}


def require_positive_non_bool_int(value: Any, *, source_name: str, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, source_name: str, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise AssertionError(f"{source_name} {field_name} must be a string list")
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
        "source": "forward_evidence_scorecard.json",
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_also_requires": real_money_requires,
        "real_money_no_baq_as_bel_required": True,
        "evidence_boundary": (
            "base status-summary fixtures do not count toward anchor-displacement, "
            "Phase 8 promotion-review, or real-money discussion gates"
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
    REPORT_MD = OUT_DIR / "paper_trade_status_summary_validation.md"
    REPORT_JSON = OUT_DIR / "paper_trade_status_summary_validation.json"


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
            timeout=120,
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
            check_name="scorecard_boolean_gate_floor_fails_before_status_summary_artifacts",
            detail=(
                "a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before "
                "the status-summary validator creates fixture roots or report artifacts"
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
            check_name="scorecard_nonpositive_phase8_gate_floor_fails_before_status_summary_artifacts",
            detail=(
                "a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails before "
                "the status-summary validator creates fixture roots or report artifacts"
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
            check_name="scorecard_nonpositive_real_money_gate_floor_fails_before_status_summary_artifacts",
            detail=(
                "a non-positive real-money discussion floor in forward_evidence_scorecard.json fails before "
                "the status-summary validator creates fixture roots or report artifacts"
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
            check_name="scorecard_missing_no_baq_fails_before_status_summary_artifacts",
            detail=(
                "a scorecard real-money gate that drops the no BAQ-as-BEL prerequisite fails before "
                "the status-summary validator creates fixture roots or report artifacts"
            ),
        ),
    ]


def build_fixture_scratch_metadata() -> dict[str, Any]:
    return {
        "fixture_root": str(FIXTURE_ROOT),
        "fixture_root_relative": str(FIXTURE_ROOT.relative_to(BASE)),
        "fixture_root_is_project_local": FIXTURE_ROOT.is_relative_to(BASE),
        "fixture_root_cleared_before_fixture_run": True,
        "evidence_boundary": (
            "status-summary fixture scratch metadata is operator-state reproducibility context only, "
            "not a live scanner result, settled ROI, promotion readiness, live profitability, bankroll guidance, "
            "or real-money evidence"
        ),
    }


CASES: list[dict[str, Any]] = [
    {
        "name": "case_bets_ready_text",
        "scenario": "bet-ready live lane summary with dedup detail",
        "format": "text",
        "scanner": {
            "run_ts": "2026-05-18T16:05:00",
            "result": "alerts_found",
            "emitted_hit_count": 1,
            "raw_hit_count": 2,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-18T16:05:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "alerts_found",
            "observation_result": "bets_ready",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 1,
            "error_count": 0,
        },
        "needles": [
            "Phase 7 current paper run 2026-05-18T16:05:00: bets ready",
            "1 scanner hit(s)",
            "2 raw before dedup",
            "1 recommendation(s)",
            "1 BET",
        ],
    },
    {
        "name": "case_bets_ready_json",
        "scenario": "JSON payload for bet-ready live lane summary with dedup detail",
        "format": "json",
        "scanner": {
            "run_ts": "2026-05-18T16:05:00",
            "result": "alerts_found",
            "emitted_hit_count": 1,
            "raw_hit_count": 2,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-18T16:05:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "alerts_found",
            "observation_result": "bets_ready",
            "observation_scope": "bet_ready",
            "observation_reason": "bets_ready",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 1,
            "error_count": 0,
        },
        "expected_json": {
            "headline": "bets ready",
            "scan_hit_count": 1,
            "raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 1,
            "error_count": 0,
            "observation_scope": "bet_ready",
            "observation_reason": "bets_ready",
            "cache_only_miss": False,
        },
        "summary_needles": [
            "bets ready",
            "1 scanner hit(s)",
            "2 raw before dedup",
            "1 recommendation(s)",
            "1 BET",
        ],
    },
    {
        "name": "case_clean_empty_text",
        "scenario": "clean-empty lane summary",
        "format": "text",
        "scanner": {
            "run_ts": "2026-05-19T11:00:00",
            "result": "no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase8_shadow_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-19T11:00:00",
            "rules_path": "phase8_shadow_rules.json",
            "scanner_result": "no_qualifiers",
            "observation_result": "clean_empty_run",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
        },
        "needles": [
            "Phase 8 shadow run 2026-05-19T11:00:00: clean empty run",
            "0 scanner hit(s)",
            "0 recommendation(s)",
        ],
    },
    {
        "name": "case_clean_empty_json",
        "scenario": "JSON payload for clean-empty lane summary",
        "format": "json",
        "scanner": {
            "run_ts": "2026-05-19T11:00:00",
            "result": "no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase8_shadow_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-19T11:00:00",
            "rules_path": "phase8_shadow_rules.json",
            "scanner_result": "no_qualifiers",
            "observation_result": "clean_empty_run",
            "observation_scope": "clean_observation",
            "observation_reason": "no_qualifiers",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
        },
        "expected_json": {
            "headline": "clean empty run",
            "scan_hit_count": 0,
            "raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "observation_scope": "clean_observation",
            "observation_reason": "no_qualifiers",
            "cache_only_miss": False,
        },
        "expected_issue_flags": {
            "has_api_access_failure_context": False,
            "has_scanner_failure_boundary": False,
            "has_stale_cache_fallback_context": False,
        },
        "summary_needles": [
            "clean empty run",
            "0 scanner hit(s)",
            "0 recommendation(s)",
        ],
    },
    {
        "name": "case_partial_cache_text",
        "scenario": "partial-cache lane summary with missing-detail / max-races detail",
        "format": "text",
        "scanner": {
            "run_ts": "2026-05-20T12:15:00",
            "result": "partial_cache_no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "partial_cache": True,
            "missing_race_detail_cache_skips": 2,
            "max_race_limit_hit": True,
            "race_details_attempted": 7,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-20T12:15:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "partial_cache_no_qualifiers",
            "observation_result": "partial_cache_empty_run",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
            "scanner_partial_cache": True,
            "scanner_missing_race_detail_cache_skips": 2,
        },
        "needles": [
            "Phase 7 current paper run 2026-05-20T12:15:00: partial cache",
            "0 scanner hit(s)",
            "2 missing race detail cache file(s)",
            "max-races cap hit after 7 attempt(s)",
        ],
    },
    {
        "name": "case_partial_cache_json",
        "scenario": "JSON payload for partial-cache lane summary with missing-detail / max-races detail",
        "format": "json",
        "scanner": {
            "run_ts": "2026-05-20T12:15:00",
            "result": "partial_cache_no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "partial_cache": True,
            "missing_race_detail_cache_skips": 2,
            "max_race_limit_hit": True,
            "race_details_attempted": 7,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-20T12:15:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "partial_cache_no_qualifiers",
            "observation_result": "partial_cache_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_empty",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
            "scanner_partial_cache": True,
            "scanner_missing_race_detail_cache_skips": 2,
        },
        "expected_json": {
            "headline": "partial cache",
            "scan_hit_count": 0,
            "raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "scanner_partial_cache": True,
            "missing_race_detail_cache_skips": 2,
            "race_details_attempted": 7,
            "max_race_limit_hit": True,
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_empty",
            "cache_only_miss": False,
            "detail_parts": [
                "0 scanner hit(s)",
                "0 recommendation(s)",
                "2 missing race detail cache file(s)",
                "max-races cap hit after 7 attempt(s)",
            ],
        },
        "summary_needles": [
            "partial cache",
            "0 scanner hit(s)",
            "2 missing race detail cache file(s)",
            "max-races cap hit after 7 attempt(s)",
        ],
    },
    {
        "name": "case_partial_cache_with_activity_text",
        "scenario": "partial-cache lane summary with surviving activity kept distinct from empty limited-coverage days",
        "format": "text",
        "scanner": {
            "run_ts": "2026-05-20T12:45:00",
            "result": "partial_cache_missing_detail",
            "emitted_hit_count": 1,
            "raw_hit_count": 2,
            "partial_cache": True,
            "missing_race_detail_cache_skips": 1,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-20T12:45:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "partial_cache_missing_detail",
            "observation_result": "partial_cache_with_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_with_activity",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 0,
            "error_count": 0,
            "scanner_partial_cache": True,
            "scanner_missing_race_detail_cache_skips": 1,
        },
        "needles": [
            "Phase 7 current paper run 2026-05-20T12:45:00: partial cache with activity",
            "1 scanner hit(s)",
            "2 raw before dedup",
            "1 recommendation(s)",
            "1 missing race detail cache file(s)",
        ],
    },
    {
        "name": "case_partial_cache_with_activity_json",
        "scenario": "JSON payload for partial-cache lane summary with surviving activity kept distinct from empty limited-coverage days",
        "format": "json",
        "scanner": {
            "run_ts": "2026-05-20T12:45:00",
            "result": "partial_cache_missing_detail",
            "emitted_hit_count": 1,
            "raw_hit_count": 2,
            "partial_cache": True,
            "missing_race_detail_cache_skips": 1,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-20T12:45:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "partial_cache_missing_detail",
            "observation_result": "partial_cache_with_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_with_activity",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 0,
            "error_count": 0,
            "scanner_partial_cache": True,
            "scanner_missing_race_detail_cache_skips": 1,
        },
        "expected_json": {
            "headline": "partial cache with activity",
            "scan_hit_count": 1,
            "raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 0,
            "scanner_partial_cache": True,
            "missing_race_detail_cache_skips": 1,
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_with_activity",
            "cache_only_miss": False,
            "detail_parts": [
                "1 scanner hit(s)",
                "2 raw before dedup",
                "1 recommendation(s)",
                "1 missing race detail cache file(s)",
            ],
        },
        "summary_needles": [
            "partial cache with activity",
            "1 scanner hit(s)",
            "2 raw before dedup",
            "1 recommendation(s)",
            "1 missing race detail cache file(s)",
        ],
    },
    {
        "name": "case_relocated_scanner_sidecar_text",
        "scenario": "helper recovers a lane-local relative pipeline-declared relocated scanner sidecar when the requested default path is missing",
        "format": "text",
        "scanner_write_relpath": "renamed_live_scan.status.json",
        "scanner_arg_relpath": "live_scan.status.json",
        "scanner": {
            "run_ts": "2026-05-20T13:05:00",
            "result": "partial_cache_missing_detail",
            "emitted_hit_count": 1,
            "raw_hit_count": 2,
            "partial_cache": True,
            "missing_race_detail_cache_skips": 1,
            "max_race_limit_hit": True,
            "race_details_attempted": 4,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-20T13:05:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_status_path": "renamed_live_scan.status.json",
            "scanner_result": "partial_cache_missing_detail",
            "observation_result": "partial_cache_with_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_with_activity",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 0,
            "error_count": 0,
            "scanner_partial_cache": True,
            "scanner_missing_race_detail_cache_skips": 1,
        },
        "needles": [
            "Phase 7 current paper run 2026-05-20T13:05:00: partial cache with activity",
            "1 scanner hit(s)",
            "2 raw before dedup",
            "1 recommendation(s)",
            "1 missing race detail cache file(s)",
            "max-races cap hit after 4 attempt(s)",
        ],
    },
    {
        "name": "case_relocated_scanner_sidecar_json",
        "scenario": "JSON payload keeps relocated scanner-sidecar detail when the requested default path is missing",
        "format": "json",
        "scanner_write_relpath": "renamed_live_scan.status.json",
        "scanner_arg_relpath": "live_scan.status.json",
        "scanner": {
            "run_ts": "2026-05-20T13:05:00",
            "result": "partial_cache_missing_detail",
            "emitted_hit_count": 1,
            "raw_hit_count": 2,
            "partial_cache": True,
            "missing_race_detail_cache_skips": 1,
            "max_race_limit_hit": True,
            "race_details_attempted": 4,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-20T13:05:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_status_path": "renamed_live_scan.status.json",
            "scanner_result": "partial_cache_missing_detail",
            "observation_result": "partial_cache_with_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_with_activity",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 0,
            "error_count": 0,
            "scanner_partial_cache": True,
            "scanner_missing_race_detail_cache_skips": 1,
        },
        "expected_json": {
            "headline": "partial cache with activity",
            "scan_hit_count": 1,
            "raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 0,
            "scanner_partial_cache": True,
            "missing_race_detail_cache_skips": 1,
            "race_details_attempted": 4,
            "max_race_limit_hit": True,
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_with_activity",
            "cache_only_miss": False,
            "scanner_status_state": "ok",
            "detail_parts": [
                "1 scanner hit(s)",
                "2 raw before dedup",
                "1 recommendation(s)",
                "1 missing race detail cache file(s)",
                "max-races cap hit after 4 attempt(s)",
            ],
        },
        "summary_needles": [
            "partial cache with activity",
            "1 scanner hit(s)",
            "2 raw before dedup",
            "1 recommendation(s)",
            "1 missing race detail cache file(s)",
            "max-races cap hit after 4 attempt(s)",
        ],
    },
    {
        "name": "case_relocated_scanner_sidecar_run_root_relative_text",
        "scenario": "helper recovers a run-root relative pipeline-declared relocated scanner sidecar when the requested default path is missing",
        "format": "text",
        "scanner_write_relpath": "phase7_current_paper/renamed_live_scan.status.json",
        "scanner_arg_relpath": "phase7_current_paper/live_scan.status.json",
        "pipeline_write_relpath": "phase7_current_paper/pipeline_status.json",
        "pipeline_arg_relpath": "phase7_current_paper/pipeline_status.json",
        "scanner": {
            "run_ts": "2026-05-20T13:06:00",
            "result": "partial_cache_missing_detail",
            "emitted_hit_count": 1,
            "raw_hit_count": 2,
            "partial_cache": True,
            "missing_race_detail_cache_skips": 1,
            "max_race_limit_hit": True,
            "race_details_attempted": 4,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-20T13:06:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_status_path": "phase7_current_paper/renamed_live_scan.status.json",
            "scanner_result": "partial_cache_missing_detail",
            "observation_result": "partial_cache_with_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_with_activity",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 0,
            "error_count": 0,
            "scanner_partial_cache": True,
            "scanner_missing_race_detail_cache_skips": 1,
        },
        "needles": [
            "Phase 7 current paper run 2026-05-20T13:06:00: partial cache with activity",
            "1 scanner hit(s)",
            "2 raw before dedup",
            "1 recommendation(s)",
            "1 missing race detail cache file(s)",
            "max-races cap hit after 4 attempt(s)",
        ],
    },
    {
        "name": "case_relocated_scanner_sidecar_project_relative_json",
        "scenario": "JSON payload recovers a project-relative pipeline-declared relocated scanner sidecar when the requested default path is missing",
        "format": "json",
        "scanner_write_relpath": "project_sidecars/renamed_live_scan.status.json",
        "scanner_arg_relpath": "phase7_current_paper/live_scan.status.json",
        "pipeline_write_relpath": "phase7_current_paper/pipeline_status.json",
        "pipeline_arg_relpath": "phase7_current_paper/pipeline_status.json",
        "scanner": {
            "run_ts": "2026-05-20T13:07:00",
            "result": "partial_cache_missing_detail",
            "emitted_hit_count": 1,
            "raw_hit_count": 2,
            "partial_cache": True,
            "missing_race_detail_cache_skips": 1,
            "max_race_limit_hit": True,
            "race_details_attempted": 4,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-20T13:07:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_status_path": "out/status_validation/status_summary_fixture/case_relocated_scanner_sidecar_project_relative_json/project_sidecars/renamed_live_scan.status.json",
            "scanner_result": "partial_cache_missing_detail",
            "observation_result": "partial_cache_with_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_with_activity",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 0,
            "error_count": 0,
            "scanner_partial_cache": True,
            "scanner_missing_race_detail_cache_skips": 1,
        },
        "expected_json": {
            "headline": "partial cache with activity",
            "scan_hit_count": 1,
            "raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 0,
            "scanner_partial_cache": True,
            "missing_race_detail_cache_skips": 1,
            "race_details_attempted": 4,
            "max_race_limit_hit": True,
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_with_activity",
            "cache_only_miss": False,
            "scanner_status_state": "ok",
            "detail_parts": [
                "1 scanner hit(s)",
                "2 raw before dedup",
                "1 recommendation(s)",
                "1 missing race detail cache file(s)",
                "max-races cap hit after 4 attempt(s)",
            ],
        },
        "summary_needles": [
            "partial cache with activity",
            "1 scanner hit(s)",
            "2 raw before dedup",
            "1 recommendation(s)",
            "1 missing race detail cache file(s)",
            "max-races cap hit after 4 attempt(s)",
        ],
    },
    {
        "name": "case_declared_scanner_sidecar_beats_stale_default_json",
        "scenario": "JSON payload prefers the pipeline-declared scanner sidecar when a stale default scanner filename also exists",
        "format": "json",
        "scanner_write_relpath": "phase7_current_paper/renamed_live_scan.status.json",
        "scanner_arg_relpath": "phase7_current_paper/live_scan.status.json",
        "pipeline_write_relpath": "phase7_current_paper/pipeline_status.json",
        "pipeline_arg_relpath": "phase7_current_paper/pipeline_status.json",
        "extra_json_files": {
            "phase7_current_paper/live_scan.status.json": {
                "run_ts": "2026-05-20T13:08:00",
                "result": "no_qualifiers",
                "emitted_hit_count": 0,
                "raw_hit_count": 0,
                "rules_path": "phase7_current_paper_rules.json",
            },
        },
        "scanner": {
            "run_ts": "2026-05-20T13:08:00",
            "result": "partial_cache_missing_detail",
            "emitted_hit_count": 1,
            "raw_hit_count": 2,
            "partial_cache": True,
            "missing_race_detail_cache_skips": 1,
            "max_race_limit_hit": True,
            "race_details_attempted": 4,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-20T13:08:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_status_path": "phase7_current_paper/renamed_live_scan.status.json",
            "scanner_result": "partial_cache_missing_detail",
            "observation_result": "partial_cache_with_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_with_activity",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 0,
            "error_count": 0,
            "scanner_partial_cache": True,
        },
        "expected_json": {
            "headline": "partial cache with activity",
            "scan_hit_count": 1,
            "raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 0,
            "scanner_partial_cache": True,
            "missing_race_detail_cache_skips": 1,
            "race_details_attempted": 4,
            "max_race_limit_hit": True,
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_with_activity",
            "cache_only_miss": False,
            "scanner_status_state": "ok",
            "detail_parts": [
                "1 scanner hit(s)",
                "2 raw before dedup",
                "1 recommendation(s)",
                "1 missing race detail cache file(s)",
                "max-races cap hit after 4 attempt(s)",
            ],
        },
        "summary_needles": [
            "partial cache with activity",
            "1 scanner hit(s)",
            "2 raw before dedup",
            "1 recommendation(s)",
            "1 missing race detail cache file(s)",
            "max-races cap hit after 4 attempt(s)",
        ],
    },
    {
        "name": "case_scanner_only_alerts_text",
        "scenario": "scanner-only alerts fallback before pipeline sidecar exists",
        "format": "text",
        "scanner": {
            "run_ts": "2026-05-21T08:45:00",
            "result": "alerts_found",
            "emitted_hit_count": 2,
            "raw_hit_count": 3,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": None,
        "needles": [
            "Phase 7 current paper run 2026-05-21T08:45:00: scanner alerts found",
            "2 scanner hit(s)",
            "3 raw before dedup",
        ],
    },
    {
        "name": "case_scanner_only_alerts_json",
        "scenario": "JSON payload for scanner-only alerts fallback before pipeline sidecar exists",
        "format": "json",
        "scanner": {
            "run_ts": "2026-05-21T08:45:00",
            "result": "alerts_found",
            "emitted_hit_count": 2,
            "raw_hit_count": 3,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": None,
        "expected_json": {
            "headline": "scanner alerts found",
            "scan_hit_count": 2,
            "raw_hit_count": 3,
            "recommendation_count": 0,
            "bet_count": 0,
            "cache_only_miss": False,
        },
        "summary_needles": [
            "scanner alerts found",
            "2 scanner hit(s)",
            "3 raw before dedup",
        ],
    },
    {
        "name": "case_cache_only_miss_text",
        "scenario": "cache-only miss lane summary",
        "format": "text",
        "scanner": {
            "run_ts": "2026-05-21T09:00:00",
            "result": "scanner_error",
            "error": "No cached data found for today's races",
            "cache_only": True,
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-21T09:00:00",
            "rules_path": "phase7_current_paper_rules.json",
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
        "needles": [
            "Phase 7 current paper run 2026-05-21T09:00:00: cache miss (cache-only)",
            "0 scanner hit(s)",
            "0 recommendation(s)",
        ],
    },
    {
        "name": "case_cache_only_miss_json",
        "scenario": "JSON payload for cache-only miss lane summary",
        "format": "json",
        "scanner": {
            "run_ts": "2026-05-21T09:00:00",
            "result": "scanner_error",
            "error": "No cached data found for today's races",
            "cache_only": True,
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-21T09:00:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "scanner_error",
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "cache_only_miss",
            "cache_only": True,
            "scanner_error": "No cached data found for today's races",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
        },
        "expected_json": {
            "headline": "cache miss (cache-only)",
            "scan_hit_count": 0,
            "raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "observation_scope": "operational_limit",
            "observation_reason": "cache_only_miss",
            "cache_only_miss": True,
        },
        "summary_needles": [
            "cache miss (cache-only)",
            "0 scanner hit(s)",
            "0 recommendation(s)",
        ],
    },
    {
        "name": "case_scanner_failure_text",
        "scenario": "generic scanner-failure lane summary stays distinct from cache-only miss",
        "format": "text",
        "scanner": {
            "run_ts": "2026-05-21T09:05:00",
            "result": "scanner_error",
            "error": "Upstream feed timeout while fetching cards",
            "cache_only": False,
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-21T09:05:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "scanner_error",
            "observation_result": "scanner_failed_empty_run",
            "cache_only": False,
            "scanner_error": "Upstream feed timeout while fetching cards",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 1,
        },
        "needles": [
            "Phase 7 current paper run 2026-05-21T09:05:00: scanner failure",
            "0 scanner hit(s)",
            "0 recommendation(s)",
            "1 ERROR",
        ],
    },
    {
        "name": "case_scanner_failure_json",
        "scenario": "JSON payload for generic scanner-failure lane summary",
        "format": "json",
        "scanner": {
            "run_ts": "2026-05-21T09:05:00",
            "result": "scanner_error",
            "error": "Upstream feed timeout while fetching cards",
            "cache_only": False,
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-21T09:05:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "scanner_error",
            "observation_result": "scanner_failed_empty_run",
            "cache_only": False,
            "scanner_error": "Upstream feed timeout while fetching cards",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 1,
        },
        "expected_json": {
            "headline": "scanner failure",
            "scan_hit_count": 0,
            "raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 1,
            "cache_only_miss": False,
        },
        "expected_issue_flags": {
            "has_api_access_failure_context": False,
            "has_scanner_failure_boundary": True,
            "has_stale_cache_fallback_context": False,
        },
        "summary_needles": [
            "scanner failure",
            "0 scanner hit(s)",
            "0 recommendation(s)",
            "1 ERROR",
        ],
    },
    {
        "name": "case_api_access_scanner_failure_text",
        "scenario": "API-access scanner failure text summary keeps the operator action/recheck route visible",
        "format": "text",
        "scanner": {
            "run_ts": "2026-06-26T09:05:00",
            "result": "scanner_error",
            "error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "http_status": 403,
            "api_access_failure": True,
            "api_failure_class": "http_403_forbidden",
            "api_failure_valid_scope": "operator_context_only",
            "api_failure_boundary": "not no-target, clean-empty, settled ROI, promotion, live-profitability, or real-money evidence",
            "api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
            "api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-06-26T09:05:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "scanner_error",
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_api_access_failure",
            "scanner_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "scanner_http_status": 403,
            "scanner_api_access_failure": True,
            "scanner_api_failure_class": "http_403_forbidden",
            "scanner_api_failure_valid_scope": "operator_context_only",
            "scanner_api_failure_boundary": "not no-target, clean-empty, settled ROI, promotion, live-profitability, or real-money evidence",
            "scanner_api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
            "scanner_api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 1,
        },
        "needles": [
            "Phase 7 current paper run 2026-06-26T09:05:00: scanner API access failure",
            "0 scanner hit(s)",
            "0 recommendation(s)",
            "1 ERROR",
            "HTTP 403",
            "API-access-failure operator context only",
            API_ACCESS_ACTION_TEXT,
            API_ACCESS_RECHECK_TEXT,
            "scanner failure class http_403_forbidden",
        ],
    },
    {
        "name": "case_api_access_scanner_failure_json",
        "scenario": "JSON payload for API-access scanner failure keeps structured operator action/recheck fields",
        "format": "json",
        "scanner": {
            "run_ts": "2026-06-26T09:05:00",
            "result": "scanner_error",
            "error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "http_status": 403,
            "api_access_failure": True,
            "api_failure_class": "http_403_forbidden",
            "api_failure_valid_scope": "operator_context_only",
            "api_failure_boundary": "not no-target, clean-empty, settled ROI, promotion, live-profitability, or real-money evidence",
            "api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
            "api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-06-26T09:05:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "scanner_error",
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_api_access_failure",
            "scanner_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "scanner_http_status": 403,
            "scanner_api_access_failure": True,
            "scanner_api_failure_class": "http_403_forbidden",
            "scanner_api_failure_valid_scope": "operator_context_only",
            "scanner_api_failure_boundary": "not no-target, clean-empty, settled ROI, promotion, live-profitability, or real-money evidence",
            "scanner_api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
            "scanner_api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 1,
        },
        "expected_json": {
            "headline": "scanner API access failure",
            "scanner_result": "scanner_error",
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_api_access_failure",
            "scan_hit_count": 0,
            "raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 1,
            "scanner_http_status": 403,
            "scanner_api_access_failure": True,
            "scanner_api_failure_class": "http_403_forbidden",
            "scanner_api_failure_valid_scope": "operator_context_only",
            "scanner_api_failure_boundary": "not no-target, clean-empty, settled ROI, promotion, live-profitability, or real-money evidence",
            "scanner_api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
            "scanner_api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
            "cache_only_miss": False,
            "detail_parts": [
                "0 scanner hit(s)",
                "0 recommendation(s)",
                "1 ERROR",
                "HTTP 403",
                "API-access-failure operator context only",
                API_ACCESS_ACTION_TEXT,
                API_ACCESS_RECHECK_TEXT,
                "scanner failure class http_403_forbidden",
            ],
        },
        "expected_issue_flags": {
            "has_api_access_failure_context": True,
            "has_scanner_failure_boundary": True,
            "has_stale_cache_fallback_context": False,
        },
        "summary_needles": [
            "scanner API access failure",
            "HTTP 403",
            "API-access-failure operator context only",
            API_ACCESS_ACTION_TEXT,
            API_ACCESS_RECHECK_TEXT,
        ],
    },
    {
        "name": "case_api_access_stale_cache_fallback_text",
        "scenario": "API-access scanner failure with stale-cache fallback keeps fallback context visible in text",
        "format": "text",
        "scanner": {
            "run_ts": "2026-06-26T09:05:00",
            "result": "scanner_error",
            "error_type": "HTTPError",
            "error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "http_status": 403,
            "api_access_failure": True,
            "api_failure_class": "api_access_failure",
            "api_failure_valid_scope": "operator_refresh_context_only",
            "api_failure_boundary": "API-access-failure operator context only; not a no-target, clean-empty, or forward-performance read.",
            "api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
            "api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
            "stale_cache_fallback_applied": True,
            "stale_cache_fallback_count": 2,
            "stale_cache_fallback_kind": "cards",
            "stale_cache_fallback_error_type": "HTTPError",
            "stale_cache_fallback_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-06-26T09:05:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "scanner_error",
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "api_access_failure",
            "scanner_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "scanner_error_type": "HTTPError",
            "scanner_http_status": 403,
            "scanner_api_access_failure": True,
            "scanner_api_failure_class": "api_access_failure",
            "scanner_api_failure_valid_scope": "operator_refresh_context_only",
            "scanner_api_failure_boundary": "API-access-failure operator context only; not a no-target, clean-empty, or forward-performance read.",
            "scanner_api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
            "scanner_api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
            "scanner_stale_cache_fallback_applied": True,
            "scanner_stale_cache_fallback_count": 2,
            "scanner_stale_cache_fallback_kind": "cards",
            "scanner_stale_cache_fallback_error_type": "HTTPError",
            "scanner_stale_cache_fallback_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
        },
        "needles": [
            "Phase 7 current paper run 2026-06-26T09:05:00: scanner API access failure",
            "0 scanner hit(s)",
            "0 recommendation(s)",
            "HTTP 403",
            "API-access-failure operator context only",
            API_ACCESS_ACTION_TEXT,
            API_ACCESS_RECHECK_TEXT,
            "stale cache fallback used for cards",
            "2 stale cache fallback(s)",
            "stale cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "scanner failure class api_access_failure",
        ],
    },
    {
        "name": "case_api_access_stale_cache_fallback_json",
        "scenario": "JSON payload for API-access stale-cache fallback keeps structured fallback metadata",
        "format": "json",
        "scanner": {
            "run_ts": "2026-06-26T09:05:00",
            "result": "scanner_error",
            "error_type": "HTTPError",
            "error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "http_status": 403,
            "api_access_failure": True,
            "api_failure_class": "api_access_failure",
            "api_failure_valid_scope": "operator_refresh_context_only",
            "api_failure_boundary": "API-access-failure operator context only; not a no-target, clean-empty, or forward-performance read.",
            "api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
            "api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
            "stale_cache_fallback_applied": True,
            "stale_cache_fallback_count": 2,
            "stale_cache_fallback_kind": "cards",
            "stale_cache_fallback_error_type": "HTTPError",
            "stale_cache_fallback_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-06-26T09:05:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "scanner_error",
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "api_access_failure",
            "scanner_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "scanner_error_type": "HTTPError",
            "scanner_http_status": 403,
            "scanner_api_access_failure": True,
            "scanner_api_failure_class": "api_access_failure",
            "scanner_api_failure_valid_scope": "operator_refresh_context_only",
            "scanner_api_failure_boundary": "API-access-failure operator context only; not a no-target, clean-empty, or forward-performance read.",
            "scanner_api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
            "scanner_api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
            "scanner_stale_cache_fallback_applied": True,
            "scanner_stale_cache_fallback_count": 2,
            "scanner_stale_cache_fallback_kind": "cards",
            "scanner_stale_cache_fallback_error_type": "HTTPError",
            "scanner_stale_cache_fallback_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
        },
        "expected_json": {
            "headline": "scanner API access failure",
            "scanner_result": "scanner_error",
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "api_access_failure",
            "scan_hit_count": 0,
            "raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
            "scanner_http_status": 403,
            "scanner_api_access_failure": True,
            "scanner_api_failure_class": "api_access_failure",
            "scanner_api_failure_valid_scope": "operator_refresh_context_only",
            "scanner_api_failure_boundary": "API-access-failure operator context only; not a no-target, clean-empty, or forward-performance read.",
            "scanner_api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
            "scanner_api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
            "scanner_stale_cache_fallback_applied": True,
            "scanner_stale_cache_fallback_count": 2,
            "scanner_stale_cache_fallback_kind": "cards",
            "scanner_stale_cache_fallback_error_type": "HTTPError",
            "scanner_stale_cache_fallback_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "cache_only_miss": False,
            "detail_parts": [
                "0 scanner hit(s)",
                "0 recommendation(s)",
                "HTTP 403",
                "API-access-failure operator context only",
                API_ACCESS_ACTION_TEXT,
                API_ACCESS_RECHECK_TEXT,
                "stale cache fallback used for cards",
                "2 stale cache fallback(s)",
                "stale cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
                "scanner failure class api_access_failure",
            ],
        },
        "expected_issue_flags": {
            "has_api_access_failure_context": True,
            "has_scanner_failure_boundary": True,
            "has_stale_cache_fallback_context": True,
        },
        "summary_needles": [
            "scanner API access failure",
            "HTTP 403",
            "API-access-failure operator context only",
            API_ACCESS_ACTION_TEXT,
            API_ACCESS_RECHECK_TEXT,
            "stale cache fallback used for cards",
            "2 stale cache fallback(s)",
            "stale cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
        ],
    },
    {
        "name": "case_missing_scan_output_text",
        "scenario": "successful scanner sidecar with missing scan-output artifact stays distinct from clean empty",
        "format": "text",
        "scanner": {
            "run_ts": "2026-05-26T10:37:59",
            "result": "no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_live_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-26T10:37:59",
            "rules_path": "phase7_live_rules.json",
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
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
        },
        "needles": [
            "Phase 7 basket run 2026-05-26T10:37:59: missing scanner output",
            "0 scanner hit(s)",
            "0 recommendation(s)",
            "scanner-status reported no_qualifiers",
            "safe empty scan fallback missing_or_empty_scan_output",
            "scan input was missing before fallback",
        ],
    },
    {
        "name": "case_missing_scan_output_json",
        "scenario": "JSON payload for successful scanner sidecar with missing scan-output artifact",
        "format": "json",
        "scanner": {
            "run_ts": "2026-05-26T10:37:59",
            "result": "no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_live_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-26T10:37:59",
            "rules_path": "phase7_live_rules.json",
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
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
        },
        "expected_json": {
            "headline": "missing scanner output",
            "scanner_result": "missing_scan_output",
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "missing_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "missing_or_empty_scan_output",
            "scan_input_state_before_empty_fallback": "missing",
            "scan_input_empty_fallback_value": "[]",
            "scanner_status_reported_result": "no_qualifiers",
            "scan_hit_count": 0,
            "raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
            "cache_only_miss": False,
        },
        "summary_needles": [
            "missing scanner output",
            "0 scanner hit(s)",
            "0 recommendation(s)",
            "scanner-status reported no_qualifiers",
            "safe empty scan fallback missing_or_empty_scan_output",
            "scan input was missing before fallback",
        ],
    },
    {
        "name": "case_signals_no_bet_text",
        "scenario": "text lane summary for signals-without-bet state",
        "format": "text",
        "scanner": {
            "run_ts": "2026-05-22T15:40:00",
            "result": "alerts_found",
            "emitted_hit_count": 2,
            "raw_hit_count": 2,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-22T15:40:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "alerts_found",
            "observation_result": "signals_logged_no_bet",
            "scan_hit_count": 2,
            "scanner_raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 0,
            "error_count": 0,
        },
        "needles": [
            "Phase 7 current paper run 2026-05-22T15:40:00: signals logged, no bet",
            "2 scanner hit(s)",
            "1 recommendation(s)",
        ],
    },
    {
        "name": "case_json_payload",
        "scenario": "JSON payload shape for signals-without-bet state",
        "format": "json",
        "scanner": {
            "run_ts": "2026-05-22T15:40:00",
            "result": "alerts_found",
            "emitted_hit_count": 2,
            "raw_hit_count": 2,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-22T15:40:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "alerts_found",
            "observation_result": "signals_logged_no_bet",
            "scan_hit_count": 2,
            "scanner_raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 0,
            "error_count": 0,
        },
        "expected_json": {
            "headline": "signals logged, no bet",
            "scan_hit_count": 2,
            "raw_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 0,
            "cache_only_miss": False,
        },
        "summary_needles": [
            "signals logged, no bet",
            "2 scanner hit(s)",
            "1 recommendation(s)",
        ],
    },
    {
        "name": "case_recommender_failure_text",
        "scenario": "recommender crash stays an operational failure instead of flattening into a normal scan outcome",
        "format": "text",
        "scanner": {
            "run_ts": "2026-05-22T16:10:00",
            "result": "alerts_found",
            "emitted_hit_count": 1,
            "raw_hit_count": 1,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-22T16:10:00",
            "rules_path": "phase7_current_paper_rules.json",
            "result": "pipeline_error",
            "stage": "recommender",
            "last_completed_stage": "scanner",
            "error_type": "RuntimeError",
            "error": "fixture recommender crash",
            "scanner_result": "alerts_found",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 1,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
        },
        "needles": [
            "Phase 7 current paper run 2026-05-22T16:10:00: recommender failure",
            "1 scanner hit(s)",
            "0 recommendation(s)",
            "last completed stage scanner",
            "stage recommender",
            "scanner hits before failure 1",
            "RuntimeError",
            "detail: fixture recommender crash",
        ],
    },
    {
        "name": "case_recommender_failure_json",
        "scenario": "JSON payload for recommender crash state",
        "format": "json",
        "scanner": {
            "run_ts": "2026-05-22T16:10:00",
            "result": "alerts_found",
            "emitted_hit_count": 1,
            "raw_hit_count": 1,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-22T16:10:00",
            "rules_path": "phase7_current_paper_rules.json",
            "result": "pipeline_error",
            "stage": "recommender",
            "last_completed_stage": "scanner",
            "error_type": "RuntimeError",
            "error": "fixture recommender crash",
            "scanner_result": "alerts_found",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 1,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
        },
        "expected_json": {
            "headline": "recommender failure",
            "scan_hit_count": 1,
            "raw_hit_count": 1,
            "recommendation_count": 0,
            "bet_count": 0,
            "cache_only_miss": False,
            "pipeline_result": "pipeline_error",
            "pipeline_stage": "recommender",
            "pipeline_last_completed_stage": "scanner",
            "pipeline_error_type": "RuntimeError",
            "pipeline_error": "fixture recommender crash",
        },
        "summary_needles": [
            "recommender failure",
            "1 scanner hit(s)",
            "0 recommendation(s)",
            "last completed stage scanner",
            "stage recommender",
            "scanner hits before failure 1",
            "RuntimeError",
            "detail: fixture recommender crash",
        ],
    },
    {
        "name": "case_logger_failure_text",
        "scenario": "logger crash stays distinct from a normal bets-ready or no-bet summary",
        "format": "text",
        "scanner": {
            "run_ts": "2026-05-22T16:20:00",
            "result": "alerts_found",
            "emitted_hit_count": 1,
            "raw_hit_count": 1,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-22T16:20:00",
            "rules_path": "phase7_current_paper_rules.json",
            "result": "pipeline_error",
            "stage": "logger",
            "last_completed_stage": "recommender",
            "observation_result": "bets_ready",
            "error_type": "OSError",
            "error": "fixture logger write failure",
            "scanner_result": "alerts_found",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 1,
            "error_count": 0,
        },
        "needles": [
            "Phase 7 current paper run 2026-05-22T16:20:00: logger failure",
            "1 scanner hit(s)",
            "1 recommendation(s)",
            "1 BET",
            "last completed stage recommender",
            "stage logger",
            "recommendations built before failure 1",
            "BET recommendations before failure 1",
            "pre-error context bets_ready",
            "OSError",
            "detail: fixture logger write failure",
        ],
    },
    {
        "name": "case_logger_failure_json",
        "scenario": "JSON payload for logger crash state",
        "format": "json",
        "scanner": {
            "run_ts": "2026-05-22T16:20:00",
            "result": "alerts_found",
            "emitted_hit_count": 1,
            "raw_hit_count": 1,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": {
            "run_ts": "2026-05-22T16:20:00",
            "rules_path": "phase7_current_paper_rules.json",
            "result": "pipeline_error",
            "stage": "logger",
            "last_completed_stage": "recommender",
            "observation_result": "bets_ready",
            "error_type": "OSError",
            "error": "fixture logger write failure",
            "scanner_result": "alerts_found",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 1,
            "error_count": 0,
        },
        "expected_json": {
            "headline": "logger failure",
            "scan_hit_count": 1,
            "raw_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 1,
            "cache_only_miss": False,
            "pipeline_result": "pipeline_error",
            "pipeline_stage": "logger",
            "pipeline_last_completed_stage": "recommender",
            "pipeline_error_type": "OSError",
            "pipeline_error": "fixture logger write failure",
        },
        "summary_needles": [
            "logger failure",
            "1 scanner hit(s)",
            "1 recommendation(s)",
            "1 BET",
            "last completed stage recommender",
            "stage logger",
            "recommendations built before failure 1",
            "BET recommendations before failure 1",
            "pre-error context bets_ready",
            "OSError",
            "detail: fixture logger write failure",
        ],
    },
    {
        "name": "case_scanner_sidecar_unreadable_text",
        "scenario": "pipeline parses but malformed scanner sidecar now stays explicit in the one-line text summary",
        "format": "text",
        "scanner_text": "{bad json\n",
        "pipeline": {
            "run_ts": "2026-05-23T09:30:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "no_qualifiers",
            "observation_result": "clean_empty_run",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
        },
        "needles": [
            "Phase 7 current paper run 2026-05-23T09:30:00: scanner sidecar unreadable",
            "0 scanner hit(s)",
            "0 recommendation(s)",
        ],
    },
    {
        "name": "case_scanner_sidecar_unreadable_json",
        "scenario": "JSON payload keeps malformed scanner sidecar explicit instead of flattening into clean-empty",
        "format": "json",
        "scanner_text": "{bad json\n",
        "pipeline": {
            "run_ts": "2026-05-23T09:30:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "no_qualifiers",
            "observation_result": "clean_empty_run",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
        },
        "expected_json": {
            "headline": "scanner sidecar unreadable",
            "scan_hit_count": 0,
            "raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "cache_only_miss": False,
            "scanner_status_state": "unreadable",
            "pipeline_status_state": "ok"
        },
        "summary_needles": [
            "scanner sidecar unreadable",
            "0 scanner hit(s)",
            "0 recommendation(s)",
        ],
    },
    {
        "name": "case_scanner_sidecar_invalid_shape_json",
        "scenario": "JSON payload keeps readable but non-object scanner sidecars explicit instead of flattening into unreadable or clean-empty",
        "format": "json",
        "scanner_text": "[]\n",
        "pipeline": {
            "run_ts": "2026-05-23T09:45:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_status_state": "readable",
            "scanner_status_error": "expected scanner-status JSON object, got list",
            "scanner_result": "scanner_status_invalid_shape",
            "observation_result": "scanner_status_unavailable_with_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_status_invalid_shape",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 0,
            "error_count": 0,
        },
        "expected_json": {
            "headline": "scanner sidecar invalid shape",
            "scan_hit_count": 1,
            "raw_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 0,
            "cache_only_miss": False,
            "scanner_status_state": "invalid_shape",
            "effective_scanner_status_state": "invalid_shape",
            "pipeline_scanner_status_state": "readable",
            "pipeline_scanner_status_error": "expected scanner-status JSON object, got list",
            "pipeline_status_state": "ok",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_status_invalid_shape",
            "detail_parts": [
                "1 scanner hit(s)",
                "1 recommendation(s)",
                "scanner-status error: expected scanner-status JSON object, got list",
                "pipeline recorded scanner-status state readable",
            ],
        },
        "summary_needles": [
            "scanner sidecar invalid shape",
            "1 scanner hit(s)",
            "1 recommendation(s)",
            "scanner-status error: expected scanner-status JSON object, got list",
            "pipeline recorded scanner-status state readable",
        ],
    },
    {
        "name": "case_scanner_sidecar_empty_text",
        "scenario": "pipeline parses but blank scanner sidecar now stays explicit in the one-line text summary",
        "format": "text",
        "scanner_text": "",
        "pipeline": {
            "run_ts": "2026-05-23T10:00:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "no_qualifiers",
            "observation_result": "clean_empty_run",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
        },
        "needles": [
            "Phase 7 current paper run 2026-05-23T10:00:00: scanner sidecar empty",
            "0 scanner hit(s)",
            "0 recommendation(s)",
        ],
    },
    {
        "name": "case_scanner_sidecar_empty_json",
        "scenario": "JSON payload keeps blank scanner sidecar explicit instead of flattening into clean-empty",
        "format": "json",
        "scanner_text": "",
        "pipeline": {
            "run_ts": "2026-05-23T10:00:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "no_qualifiers",
            "observation_result": "clean_empty_run",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
        },
        "expected_json": {
            "headline": "scanner sidecar empty",
            "scan_hit_count": 0,
            "raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "cache_only_miss": False,
            "scanner_status_state": "empty",
            "pipeline_status_state": "ok"
        },
        "summary_needles": [
            "scanner sidecar empty",
            "0 scanner hit(s)",
            "0 recommendation(s)",
        ],
    },
    {
        "name": "case_pipeline_recorded_empty_scanner_sidecar_text",
        "scenario": "pipeline-recorded zero-byte scanner-status state stays explicit even if the physical scanner sidecar is absent from the copied surface",
        "format": "text",
        "pipeline": {
            "run_ts": "2026-05-23T10:30:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_status_state": "empty",
            "scanner_result": "scanner_status_empty",
            "observation_result": "scanner_status_unavailable_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_status_empty",
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
        },
        "needles": [
            "Phase 7 current paper run 2026-05-23T10:30:00: scanner sidecar recorded empty",
            "0 scanner hit(s)",
            "0 recommendation(s)",
            "current scanner sidecar file missing",
            "pipeline recorded scanner-status state empty",
        ],
    },
    {
        "name": "case_pipeline_recorded_unreadable_scanner_sidecar_json",
        "scenario": "pipeline-recorded malformed scanner-status state preserves activity and stays explicit even if the physical scanner sidecar is absent from the copied surface",
        "format": "json",
        "pipeline": {
            "run_ts": "2026-05-23T10:45:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_status_state": "unreadable",
            "scanner_status_error": "JSONDecodeError: fixture malformed scanner status",
            "scanner_result": "scanner_status_unreadable",
            "observation_result": "scanner_status_unavailable_with_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_status_unreadable",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 0,
            "error_count": 0,
        },
        "expected_json": {
            "headline": "scanner sidecar recorded unreadable",
            "scan_hit_count": 1,
            "raw_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 0,
            "cache_only_miss": False,
            "scanner_status_state": "missing",
            "effective_scanner_status_state": "unreadable",
            "pipeline_scanner_status_state": "unreadable",
            "pipeline_status_state": "ok",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_status_unreadable",
            "detail_parts": [
                "1 scanner hit(s)",
                "1 recommendation(s)",
                "current scanner sidecar file missing",
                "pipeline recorded scanner-status state unreadable",
            ],
        },
        "summary_needles": [
            "scanner sidecar recorded unreadable",
            "1 scanner hit(s)",
            "1 recommendation(s)",
            "current scanner sidecar file missing",
            "pipeline recorded scanner-status state unreadable",
        ],
    },
    {
        "name": "case_pipeline_recorded_invalid_shape_scanner_sidecar_json",
        "scenario": "pipeline-recorded non-object scanner-status shape preserves activity and stays explicit even if the physical scanner sidecar is absent from the copied surface",
        "format": "json",
        "pipeline": {
            "run_ts": "2026-05-23T10:55:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_status_state": "readable",
            "scanner_status_error": "expected scanner-status JSON object, got list",
            "scanner_result": "scanner_status_invalid_shape",
            "observation_result": "scanner_status_unavailable_with_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_status_invalid_shape",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 0,
            "error_count": 0,
        },
        "expected_json": {
            "headline": "scanner sidecar recorded invalid shape",
            "scan_hit_count": 1,
            "raw_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 0,
            "cache_only_miss": False,
            "scanner_status_state": "missing",
            "effective_scanner_status_state": "invalid_shape",
            "pipeline_scanner_status_state": "readable",
            "pipeline_scanner_status_error": "expected scanner-status JSON object, got list",
            "pipeline_status_state": "ok",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_status_invalid_shape",
            "detail_parts": [
                "1 scanner hit(s)",
                "1 recommendation(s)",
                "scanner-status error: expected scanner-status JSON object, got list",
                "current scanner sidecar file missing",
                "pipeline recorded scanner-status state readable",
            ],
        },
        "summary_needles": [
            "scanner sidecar recorded invalid shape",
            "1 scanner hit(s)",
            "1 recommendation(s)",
            "scanner-status error: expected scanner-status JSON object, got list",
            "current scanner sidecar file missing",
            "pipeline recorded scanner-status state readable",
        ],
    },
    {
        "name": "case_pipeline_sidecar_missing_required_text",
        "scenario": "required pipeline mode keeps a readable scanner plus missing pipeline sidecar explicit in the one-line text summary",
        "format": "text",
        "extra_args": ["--require-pipeline-status"],
        "scanner": {
            "run_ts": "2026-05-24T09:30:00",
            "result": "no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": None,
        "needles": [
            "Phase 7 current paper run 2026-05-24T09:30:00: pipeline sidecar missing",
            "0 scanner hit(s)",
        ],
    },
    {
        "name": "case_pipeline_sidecar_missing_required_json",
        "scenario": "required pipeline mode keeps a readable scanner plus missing pipeline sidecar explicit in the JSON payload too",
        "format": "json",
        "extra_args": ["--require-pipeline-status"],
        "scanner": {
            "run_ts": "2026-05-24T09:30:00",
            "result": "no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline": None,
        "expected_json": {
            "headline": "pipeline sidecar missing",
            "scan_hit_count": 0,
            "raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "cache_only_miss": False,
            "scanner_status_state": "ok",
            "pipeline_status_state": "missing"
        },
        "summary_needles": [
            "pipeline sidecar missing",
            "0 scanner hit(s)"
        ],
    },
    {
        "name": "case_pipeline_sidecar_empty_required_text",
        "scenario": "required pipeline mode keeps a readable scanner plus blank pipeline sidecar explicit in the one-line text summary",
        "format": "text",
        "extra_args": ["--require-pipeline-status"],
        "scanner": {
            "run_ts": "2026-05-25T08:45:00",
            "result": "no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline_text": "",
        "needles": [
            "Phase 7 current paper run 2026-05-25T08:45:00: pipeline sidecar empty",
            "0 scanner hit(s)",
        ],
    },
    {
        "name": "case_pipeline_sidecar_empty_required_json",
        "scenario": "required pipeline mode keeps a readable scanner plus blank pipeline sidecar explicit in the JSON payload too",
        "format": "json",
        "extra_args": ["--require-pipeline-status"],
        "scanner": {
            "run_ts": "2026-05-25T08:45:00",
            "result": "no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline_text": "",
        "expected_json": {
            "headline": "pipeline sidecar empty",
            "scan_hit_count": 0,
            "raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "cache_only_miss": False,
            "scanner_status_state": "ok",
            "pipeline_status_state": "empty"
        },
        "summary_needles": [
            "pipeline sidecar empty",
            "0 scanner hit(s)"
        ],
    },
    {
        "name": "case_pipeline_sidecar_unreadable_required_text",
        "scenario": "required pipeline mode keeps a readable scanner plus malformed pipeline sidecar explicit in the one-line text summary",
        "format": "text",
        "extra_args": ["--require-pipeline-status"],
        "scanner": {
            "run_ts": "2026-05-25T09:30:00",
            "result": "no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline_text": "{bad json\n",
        "needles": [
            "Phase 7 current paper run 2026-05-25T09:30:00: pipeline sidecar unreadable",
            "0 scanner hit(s)",
        ],
    },
    {
        "name": "case_pipeline_sidecar_unreadable_required_json",
        "scenario": "required pipeline mode keeps a readable scanner plus malformed pipeline sidecar explicit in the JSON payload too",
        "format": "json",
        "extra_args": ["--require-pipeline-status"],
        "scanner": {
            "run_ts": "2026-05-25T09:30:00",
            "result": "no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline_text": "{bad json\n",
        "expected_json": {
            "headline": "pipeline sidecar unreadable",
            "scan_hit_count": 0,
            "raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "cache_only_miss": False,
            "scanner_status_state": "ok",
            "pipeline_status_state": "unreadable"
        },
        "summary_needles": [
            "pipeline sidecar unreadable",
            "0 scanner hit(s)"
        ],
    },
    {
        "name": "case_pipeline_sidecar_invalid_shape_required_json",
        "scenario": "required pipeline mode keeps a readable scanner plus non-object pipeline sidecar explicit in the JSON payload too",
        "format": "json",
        "extra_args": ["--require-pipeline-status"],
        "scanner": {
            "run_ts": "2026-05-25T09:45:00",
            "result": "no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
        "pipeline_text": "[]\n",
        "expected_json": {
            "headline": "pipeline sidecar invalid shape",
            "scan_hit_count": 0,
            "raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "cache_only_miss": False,
            "scanner_status_state": "ok",
            "pipeline_status_state": "invalid_shape"
        },
        "summary_needles": [
            "pipeline sidecar invalid shape",
            "0 scanner hit(s)"
        ],
    },
    {
        "name": "case_missing_sidecars_error",
        "scenario": "explicit non-zero failure when neither sidecar is readable",
        "format": "text",
        "scanner": None,
        "pipeline": None,
        "expect_failure": "No readable status JSON found.",
    },
]


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_root = FIXTURE_ROOT / case["name"]
    if case_root.exists():
        shutil.rmtree(case_root)
    case_root.mkdir(parents=True, exist_ok=True)

    scanner_write_path = case_root / case.get("scanner_write_relpath", "scanner_status.json")
    scanner_arg_path = case_root / case.get("scanner_arg_relpath", case.get("scanner_write_relpath", "scanner_status.json"))
    pipeline_write_path = case_root / case.get("pipeline_write_relpath", "pipeline_status.json")
    pipeline_arg_path = case_root / case.get("pipeline_arg_relpath", case.get("pipeline_write_relpath", "pipeline_status.json"))
    output_path = case_root / ("summary.json" if case["format"] == "json" else "summary.txt")

    if "scanner_text" in case:
        write_text(scanner_write_path, str(case["scanner_text"]))
    elif case.get("scanner") is not None:
        write_json(scanner_write_path, case["scanner"])
    if "pipeline_text" in case:
        write_text(pipeline_write_path, str(case["pipeline_text"]))
    elif case.get("pipeline") is not None:
        write_json(pipeline_write_path, case["pipeline"])
    for relpath, payload in (case.get("extra_json_files") or {}).items():
        write_json(case_root / relpath, payload)
    for relpath, text in (case.get("extra_text_files") or {}).items():
        write_text(case_root / relpath, str(text))

    cmd = [
        sys.executable,
        str(SCRIPT),
        "--scanner-status", str(scanner_arg_path),
        "--pipeline-status", str(pipeline_arg_path),
        "--format", case["format"],
        "--output", str(output_path),
        *(case.get("extra_args") or []),
    ]
    result = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)

    if case.get("expect_failure"):
        if result.returncode == 0:
            raise AssertionError(f"{case['name']}: expected helper failure")
        assert_contains(result.stderr, case["expect_failure"], case["name"])
        return {
            "case": case["name"],
            "scenario": case.get("scenario"),
            "result": "PASS",
            "mode": "expected failure",
            "preview": "expected failure",
            "error": result.stderr.strip(),
        }

    if result.returncode != 0:
        raise AssertionError(f"{case['name']}: helper failed unexpectedly: {result.stderr.strip()}")

    content = output_path.read_text(encoding="utf-8")
    resolved_scanner_path = status_summary_source.resolve_scanner_status_path(
        scanner_arg_path,
        pipeline_arg_path,
        case.get("pipeline"),
    )
    scanner_state = status_summary_source.json_state(resolved_scanner_path)
    pipeline_state = status_summary_source.json_state(pipeline_arg_path)
    expected_payload = status_summary_source.summarize(
        case.get("scanner") if resolved_scanner_path.exists() else None,
        case.get("pipeline"),
        scanner_state=scanner_state,
        pipeline_state=pipeline_state,
        require_pipeline_status="--require-pipeline-status" in (case.get("extra_args") or []),
    )
    if case["format"] == "json":
        expected_content = json.dumps(expected_payload, indent=2) + "\n"
        if content != expected_content:
            raise AssertionError(f"{case['name']}: summary.json no longer matches a fresh render from paper_trade_status_summary.py")
        payload = json.loads(content)
        if payload.get("valid_evidence_scope") != status_summary_source.STATUS_VALID_SCOPE:
            raise AssertionError(f"{case['name']}: summary.json is missing the workflow-only evidence scope")
        if payload.get("evidence_boundary") != status_summary_source.STATUS_EVIDENCE_BOUNDARY:
            raise AssertionError(f"{case['name']}: summary.json is missing the operational-status evidence boundary")
        boundary_metadata = payload.get("evidence_boundary_metadata")
        if not isinstance(boundary_metadata, dict):
            raise AssertionError(f"{case['name']}: summary.json is missing evidence_boundary_metadata")
        if boundary_metadata.get("artifact_role") != "paper-trade base status summary":
            raise AssertionError(f"{case['name']}: summary.json evidence_boundary_metadata has the wrong artifact role")
        if boundary_metadata.get("valid_evidence_scope") != status_summary_source.STATUS_VALID_SCOPE:
            raise AssertionError(f"{case['name']}: summary.json evidence_boundary_metadata lost the workflow-only scope")
        for flag in (
            "not_new_forward_evidence_by_itself",
            "not_settled_roi_evidence",
            "not_live_profitability_evidence",
            "not_promotion_readiness_evidence",
            "not_anchor_change_evidence",
            "not_phase8_promotion_evidence",
            "not_scope_change_evidence",
            "not_real_money_evidence",
            "not_baq_as_bel_evidence",
            "quiet_run_classification_is_not_performance_evidence",
            "clean_empty_run_is_not_forward_performance_evidence",
            "limited_coverage_is_operational_context_only",
            "api_access_failure_is_operator_context_only",
            "broken_sidecars_are_not_clean_empty_evidence",
            "requires_lane_enrichment_and_settlement_audit_before_performance_read",
        ):
            if boundary_metadata.get(flag) is not True:
                raise AssertionError(f"{case['name']}: summary.json evidence_boundary_metadata missing true {flag}")
        for key, expected in (case.get("expected_json") or {}).items():
            actual = payload.get(key)
            if actual != expected:
                raise AssertionError(f"{case['name']}: expected payload[{key!r}]={expected!r}, got {actual!r}")
        issue_flags = payload.get("operator_read_gate_issue_flags")
        if not isinstance(issue_flags, dict):
            raise AssertionError(f"{case['name']}: summary.json is missing operator_read_gate_issue_flags")
        for flag in status_summary_source.STATUS_OPERATOR_READ_GATE_ISSUE_FLAGS:
            if not isinstance(payload.get(flag), bool):
                raise AssertionError(f"{case['name']}: summary.json {flag} is not a boolean")
            if issue_flags.get(flag) is not payload.get(flag):
                raise AssertionError(f"{case['name']}: summary.json issue flag mirror drifted for {flag}")
        for flag, expected in (case.get("expected_issue_flags") or {}).items():
            if payload.get(flag) is not expected:
                raise AssertionError(f"{case['name']}: expected {flag}={expected}, got {payload.get(flag)}")
        for needle in case.get("summary_needles") or []:
            assert_contains(str(payload.get("summary_line") or ""), needle, case["name"])
        preview = payload.get("summary_line") or ""
    else:
        expected_content = expected_payload["summary_line"] + "\n"
        if content != expected_content:
            raise AssertionError(f"{case['name']}: summary.txt no longer matches a fresh render from paper_trade_status_summary.py")
        for needle in case.get("needles") or []:
            assert_contains(content, needle, case["name"])
        preview = content.strip()

    return {
        "case": case["name"],
        "scenario": case.get("scenario"),
        "result": "PASS",
        "mode": case["format"],
        "output": str(output_path.relative_to(BASE)),
        "preview": preview,
    }


def render_case_result(row: dict[str, Any]) -> str:
    value = str(row.get("preview") or row.get("mode") or "")
    return value.replace("|", "\\|")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    scorecard_json = args.scorecard_json.expanduser().resolve()
    configure_output_paths(args.fixture_root.expanduser().resolve(), args.out_dir.expanduser().resolve())
    scorecard_gates = read_scorecard_gate_minimums(scorecard_json)
    scorecard_artifact_guardrails = scorecard_no_artifact_guardrails(scorecard_json)

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for legacy in [
        FIXTURE_ROOT / "status_summary_fixture_validation.md",
        FIXTURE_ROOT / "status_summary_fixture_validation.json",
    ]:
        if legacy.exists():
            legacy.unlink()
    scratch = build_fixture_scratch_metadata()
    results = [run_case(case) for case in CASES]
    suite_read = (
        "status-summary helper still distinguishes scanner-only alerts, bets ready, clean empty run, partial cache empty, partial cache with activity, "
        "cache miss (cache-only), missing scanner output, scanner failure, empty/unreadable/invalid-shape scanner sidecars, pipeline-recorded empty/unreadable/invalid-shape scanner-status states, required-pipeline sidecar failures, recommender failure, logger failure, signals logged / no bet, "
        "API-access scanner failures with explicit operator action/recheck routing and stale-cache fallback metadata, "
        "and the no-readable-sidecars failure, with pipeline stage / type / detail preserved in the human-facing failure line and now also carrying last-completed-stage plus pre-error scanner/recommendation context for post-scan failures, plus first-class JSON `detail_parts`, `scanner_partial_cache`, `pipeline_scanner_status_error`, structured `observation_scope` / `observation_reason`, and `operator_read_gate_issue_flags` fields so limited-coverage, clean-empty, scanner/API-access, and stale-cache fallback context do not have to be reparsed from prose alone, while now also recovering lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars when the requested default scanner path is missing, preferring the pipeline-declared sidecar when a stale default scanner filename also exists, and preserving the source pipeline's recorded scanner-status state when the physical scanner sidecar is absent from a copied surface, "
        "and the saved text and JSON surfaces pinned to fresh source-layer renders, with every JSON summary carrying `valid_evidence_scope`, an `evidence_boundary`, and `evidence_boundary_metadata` so automation cannot treat quiet runs, clean scans, limited coverage, API-access failures, stale-cache fallback, or broken-sidecar classifications as live profitability, promotion, anchor movement, scope movement, BAQ/BEL substitution, or real-money proof, while the validator report now exposes exact `valid_evidence_scope=workflow_state_triage_only` as source-output scope metadata only, rejects malformed scorecard gates before fixture/report artifacts, publishes project-local fixture scratch metadata, and preserves the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that base status-summary fixtures do not advance; status-summary helper: base operational state contract, not new forward evidence by itself"
    )
    if (
        scorecard_gates.get("source") != "forward_evidence_scorecard.json"
        or scorecard_gates.get("source_path") != "decision_gate_minimums"
        or scorecard_gates.get("anchor_displacement_min_roi_complete_settled_observations") != 30
        or scorecard_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") != 20
        or scorecard_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") != 100
        or scorecard_gates.get("real_money_no_baq_as_bel_required") is not True
        or "no BAQ-as-BEL substitution" not in scorecard_gates.get("real_money_also_requires", [])
    ):
        raise AssertionError("status-summary scorecard gate boundary no longer matches forward_evidence_scorecard.json")

    lines = [
        "# Paper-Trade Status Summary Validation",
        "",
        "This report validates `paper_trade_status_summary.py` directly against representative fixture cases under `out/status_validation/status_summary_fixture/`, while publishing the direct validator readout under `out/status_validation/paper_trade_status_summary/`.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Fixture scratch metadata: `{scratch['fixture_root_relative']}` is project-local and cleared before fixture setup.",
        "",
        "## Cases",
        "",
        "| Case | Scenario | Result |",
        "|---|---|---|",
        *[
            f"| `{row['case']}` | {row['scenario']} | {render_case_result(row)} |"
            for row in results
        ],
        "",
        "## Validation result",
        "",
        "- Fixture root: `out/status_validation/status_summary_fixture/`",
        "- Direct validator report path: `out/status_validation/paper_trade_status_summary/`",
        "- The base status-summary helper now has direct fixture coverage for the wrapper states it is supposed to describe honestly before lane enrichment starts.",
        "- Each fixture now requires the saved `summary.txt` or `summary.json` output to match a fresh source-layer render from `paper_trade_status_summary.py`, not just selected phrases from that branch.",
        "- Bets-ready now has both a plain text one-line summary fixture and a JSON payload fixture, so the actual action-ready state stays aligned across the helper's two delivery paths too.",
        "- Clean-empty now has both a plain text one-line summary fixture and a JSON payload fixture, so the quiet no-qualifier state stays aligned across the helper's two delivery paths too.",
        "- Partial-cache now has both a plain text one-line summary fixture and a JSON payload fixture, so missing-detail counts and max-race-cap detail stay aligned across the helper's two delivery paths too.",
        "- The JSON payload now also exposes `detail_parts`, the explicit `scanner_partial_cache` flag, structured `observation_scope` / `observation_reason`, `valid_evidence_scope`, `evidence_boundary`, `evidence_boundary_metadata`, and `operator_read_gate_issue_flags` fields, so downstream wrappers and validators can consume limited-coverage, partial-cache-with-activity, clean-empty, scanner/API-access, stale-cache fallback, and no-promotion context structurally instead of reparsing the saved prose line.",
        "- Relocated scanner-sidecar recovery now has lane-local text/JSON coverage plus dedicated run-root-relative, project-relative, and stale-default-masking fixtures, so copied runs or scratch rerenders can still keep the richer base scanner detail when `pipeline_status.json` points at a renamed scanner sidecar, including when an older `live_scan.status.json` is still sitting beside it.",
        "- Scanner-only alerts now has both a plain text one-line summary fixture and a JSON payload fixture, so the pre-enrichment fallback stays aligned across the helper's two delivery paths too.",
        "- Cache-only miss now has both a plain text one-line summary fixture and a JSON payload fixture, so the most important cache-recovery branch stays aligned across the helper's two delivery paths too.",
        "- Missing scanner output now has both a plain text one-line summary fixture and a JSON payload fixture, so a successful scanner sidecar with a missing scan-output artifact stays distinct from clean no-qualifier scans while preserving the sidecar's reported result and safe empty-fallback metadata.",
        "- Generic scanner failure now has both a plain text one-line summary fixture and a JSON payload fixture, so broader scan breakage stays distinct from cache-only miss across the helper's two delivery paths too.",
        "- API-access scanner failure now has plain text and JSON payload fixture coverage for both direct API failures and API failures completed from stale cache, so HTTP 403 / API-access context keeps the operator action `refresh_daily_wrapper_before_evidence_read`, recheck command `./run_daily_portfolio_observation.sh`, stale-cache fallback count/kind, fallback error metadata, and the three issue booleans visible at the base helper layer instead of flattening into a generic scanner failure or clean-empty read.",
        "- Empty and unreadable scanner sidecars now both have plain text one-line summary fixtures and JSON payload fixtures, readable-but-invalid-shape scanner sidecars have direct JSON payload coverage, and source-pipeline-recorded empty/unreadable/invalid-shape scanner-status states have direct coverage when the physical scanner sidecar is absent from a copied surface, so blank, malformed, or non-object scan-status artifacts can no longer masquerade as normal clean-empty days at the base helper layer.",
        "- Required-pipeline mode now has plain text and JSON fixture coverage for missing, empty, and unreadable pipeline sidecars plus JSON coverage for invalid-shape pipeline sidecars, so the daily wrapper can demand an honest base-summary warning without breaking legitimate scanner-only helper use elsewhere.",
        "- Signals-without-bet now has both a plain text one-line summary fixture and a JSON payload fixture, so the helper's two delivery paths stay aligned on that branch.",
        "- Recommender failure now has both a plain text one-line summary fixture and a JSON payload fixture, so a mid-pipeline crash can no longer masquerade as a normal scan outcome at the base helper layer and the saved human-facing line keeps the last completed stage, stage, pre-failure scanner-hit context, error type, and detail together.",
        "- Logger failure now has both a plain text one-line summary fixture and a JSON payload fixture, so downstream surfaces can keep broken ledger writes distinct from real quiet or action-ready states while preserving the last completed stage, stage, pre-failure recommendation/BET context, pre-error observation context, error type, and detail in the saved human-facing line too.",
        "- This pins the exact one-line base summary contract across scanner-only alerts, bet-ready, clean-empty, partial-cache, cache-only-miss, missing-scan-output, generic scanner-failure, API-access stale-cache fallback, empty/unreadable/invalid-shape-scanner-sidecar, pipeline-recorded scanner-status unavailable, required-pipeline-sidecar-missing/empty/unreadable/invalid-shape, recommender-failure, logger-failure, and signals-without-bet states, plus the explicit failure path when no readable sidecars exist.",
        "- Malformed scorecard gate metadata now fails before fixture roots or report artifacts are created, including boolean anchor-displacement floors, non-positive Phase 8 and real-money floors, and missing no-BAQ-as-BEL real-money prerequisites.",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {VALIDATOR_EVIDENCE_BOUNDARY['artifact_role']}",
        f"- Valid use: {VALIDATOR_EVIDENCE_BOUNDARY['valid_use']}",
        f"- {STATUS_SUMMARY_VALID_SCOPE_LINE}",
        "- Boundary: status-summary validator cleanliness is operator state-routing metadata only, not new forward evidence, not a live paper-trade ledger, not a current-day scanner result, not settled ROI, not live profitability, not promotion readiness, and not real-money evidence.",
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
        "## Bottom Line",
        "",
        "Green here means the base status-summary helper still keeps empty, missing-output, limited-coverage, cache-miss, broken-sidecar, invalid-shape-sidecar, pipeline-recorded sidecar-unavailable, and mid-pipeline failure states operationally distinct across both text and JSON outputs, so downstream wrapper surfaces do not have to guess whether a quiet-looking day was actually clean, partial, or broken. This is an operator-state contract check, not new forward-profit evidence.",
        "",
    ]
    child_checks = [
        *scorecard_artifact_guardrails,
        {
            "check": "fixture_state_matrix_stays_covered_across_text_json_and_failure_modes",
            "status": "pass",
            "detail": "the validator still covers scanner-only alerts, bets ready, clean empty, partial-cache empty, partial-cache with activity, cache-only miss, missing scanner output, generic scanner failure, signals-without-bet, recommender failure, logger failure, empty/unreadable/invalid-shape sidecars, pipeline-recorded empty/unreadable/invalid-shape scanner-status states, required-pipeline failures, and the explicit no-readable-sidecars failure instead of collapsing those operator states together",
        },
        {
            "check": "api_access_scanner_failure_route_stays_explicit",
            "status": "pass",
            "detail": "the status-summary validator now has text and JSON fixtures proving API-access scanner failures keep HTTP status, API-access-only context, operator action refresh_daily_wrapper_before_evidence_read, and recheck command ./run_daily_portfolio_observation.sh visible before lane enrichment",
        },
        {
            "check": "api_access_stale_cache_fallback_route_stays_explicit",
            "status": "pass",
            "detail": "the status-summary validator now has text and JSON fixtures proving API-access failures completed from stale cache keep HTTP status, API-access-only context, stale-cache fallback kind/count/error metadata, operator action refresh_daily_wrapper_before_evidence_read, and recheck command ./run_daily_portfolio_observation.sh visible before lane enrichment",
        },
        {
            "check": "structured_partial_cache_and_observation_fields_stay_explicit",
            "status": "pass",
            "detail": "json fixtures still pin `detail_parts`, `scanner_partial_cache`, `observation_scope`, `observation_reason`, `effective_scanner_status_state`, `pipeline_scanner_status_state`, `pipeline_scanner_status_error`, `valid_evidence_scope`, `evidence_boundary`, and `evidence_boundary_metadata` so limited-coverage, clean-empty, missing-output fallback, cache-edge, broken-shape, and no-promotion context can stay machine-readable instead of being reparsed from the saved prose line",
        },
        {
            "check": "pipeline_failure_context_and_pre_error_counts_stay_honest",
            "status": "pass",
            "detail": "recommender and logger failure fixtures still keep stage, last-completed-stage, error type, error detail, and the pre-error scanner/recommendation context explicit in both text and json paths so broken runs do not masquerade as normal quiet or action-ready states",
        },
        {
            "check": "relocated_scanner_and_required_pipeline_sidecar_recovery_stay_explicit",
            "status": "pass",
            "detail": "the helper still recovers lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars when the requested default path is missing and now prefers the pipeline-declared sidecar over a stale default scanner filename, while required-pipeline mode keeps missing, empty, or unreadable pipeline sidecars explicit instead of flattening them into clean-empty or scanner-only fallback summaries",
        },
        {
            "check": "saved_outputs_match_current_source_layer_and_status_summary_stays_base_state_only",
            "status": "pass",
            "detail": "every fixture still requires saved text or json output to match a fresh source-layer render from paper_trade_status_summary.py, and the validator summary still says plainly this helper is the base operational state contract rather than new forward evidence",
        },
        {
            "check": "fixture_scratch_metadata_published",
            "status": "pass",
            "detail": "the status-summary validator now publishes project-local fixture scratch metadata so parent rollups can verify base-state fixture hygiene without parsing markdown prose",
        },
        {
            "check": "status_summary_preserves_scorecard_gate_boundary",
            "status": "pass",
            "detail": "the status-summary validator now publishes the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite while saying base status-summary fixtures do not count toward those gates",
        },
        {
            "check": "source_json_summaries_publish_machine_readable_evidence_boundary_metadata",
            "status": "pass",
            "detail": "every status-summary JSON fixture now has to publish source-level evidence_boundary_metadata so quiet runs, clean empty states, limited coverage, API-access failures, stale-cache fallback, and broken sidecars stay machine-readable as operational routing only, not settled ROI, live profitability, promotion readiness, anchor movement, scope movement, BAQ/BEL substitution, or real-money evidence",
        },
        {
            "check": "direct_validation_report_exposes_status_summary_valid_scope",
            "status": "pass",
            "detail": f"the status-summary validation markdown and JSON now expose exact {STATUS_SUMMARY_VALID_SCOPE_LINE} as source-output scope metadata only, without changing the one-line text helper output or treating validator cleanliness as settled ROI, live profitability, promotion readiness, BAQ/BEL substitution, or real-money evidence",
        },
        {
            "check": "source_json_summaries_publish_operator_read_gate_issue_flags",
            "status": "pass",
            "detail": "every status-summary JSON fixture now publishes the same three operator read-gate issue booleans used downstream, with clean-empty false, generic scanner failure scanner-boundary-only, API-access API/scanner true, and API-access stale-cache fallback all true",
        },
    ]

    payload = {
        "suite_status": "pass",
        "total_fixture_scenarios": len(results),
        "total_checks": len(results),
        "check_count": len(results),
        "child_check_count": len(child_checks),
        "child_checks": child_checks,
        "results": results,
        "summary": {
            "suite_read": suite_read,
        },
        "valid_evidence_scope": status_summary_source.STATUS_VALID_SCOPE,
        "evidence_boundary": VALIDATOR_EVIDENCE_BOUNDARY,
        "scratch": scratch,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "fixture_root": display_path(FIXTURE_ROOT),
        "report_path": display_path(OUT_DIR),
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }

    write_text(REPORT_MD, "\n".join(lines))
    write_text(REPORT_JSON, json.dumps(payload, indent=2) + "\n")

    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    for row in results:
        tail = row.get("output") or row.get("mode")
        print(f"PASS {row['case']}: {tail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
