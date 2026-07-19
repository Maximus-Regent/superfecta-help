#!/usr/bin/env python3
"""
Fixture-driven validation for paper_trade_daily_summary.py.

Purpose:
- keep the daily quick-jump summary reproducible
- validate representative empty, settlement-pending, active-target, explicit pipeline-failure, and missing-lane-summary cases
- confirm the generator preserves the operator-facing surface without depending on live runs
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import paper_trade_daily_summary as ptds

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "paper_trade_daily_summary.py"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "daily_summary_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_daily_summary"
OUT_MD = OUT_DIR / "paper_trade_daily_summary_validation.md"
OUT_JSON = OUT_DIR / "paper_trade_daily_summary_validation.json"
LIVE_RUNS_ROOT = BASE / "out" / "daily_portfolio_runs"
REBUILD_COMMAND = "python3 validate_paper_trade_daily_summary.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
API_ACCESS_ACTION_TEXT = "Sidecar action: refresh_daily_wrapper_before_evidence_read"
API_ACCESS_RECHECK_TEXT = "Recheck command: ./run_daily_portfolio_observation.sh"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade daily-summary validator",
    "valid_evidence_scope": ptds.DAILY_SUMMARY_VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "isolated daily-summary fixture daily-run folders",
        "saved live daily_summary.txt source-layer rebuilds",
        "paper_trade_daily_summary.py",
        "forward_evidence_scorecard.json decision_gate_minimums",
    ],
    "valid_use": "combined operator workflow/navigation validation for daily paper-trade run summaries",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "daily_summary_validator_passes_are_workflow_navigation_metadata_only": True,
    "non_goals": [
        "do not treat combined daily-summary cleanliness as ROI-complete observations",
        "do not treat inherited right-now, lane-summary, or next-step lines as fresh performance evidence",
        "do not promote OP_REFINED_K7 or Phase 8 from daily-summary route visibility",
        "do not substitute BAQ for BEL",
        "do not treat daily-summary validation as real-money evidence",
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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def setup_case(case_name: str, run_date: str, preflight_note: str, primary_summary: str, shadow_summary: str,
               preflight_json: dict[str, Any] | None = None,
               primary_next_steps_text: str = "Phase 7 current paper lane next steps\n- State: WAITING FOR FIRST SETTLED RACES\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- First statistical-read progress: 0/30 settled (30 more needed)\n- Broader portfolio-review progress: 0/100 settled (100 more needed)\n- Why: No primary races are settled yet. The first statistical read is still 0/30 and the broader portfolio-review gate is 0/100, so keep the OP/CD observation loop running instead of over-reading empty forward metrics.",
               shadow_next_steps_text: str = "Phase 8 shadow lane next steps\n- State: WAITING FOR FIRST SETTLED RACES\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- First statistical-read progress: 0/20 settled (20 more needed)\n- Broader portfolio-review progress: 0/100 settled (100 more needed)\n- Why: No shadow races are settled yet. The first statistical read is still 0/20 and the broader portfolio-review gate is 0/100, so keep Phase 8 in watch mode instead of promotion/readiness language.",
               settlement_lanes: list[dict[str, Any]] | None = None,
               right_now_issue_flags: dict[str, bool] | None = None,
               right_now_focus: str | None = None,
               right_now_timing: str = "now",
               right_now_run_freshness: str | None = None,
               right_now_stale_snapshot_note: str | None = None,
               right_now_ops_bucket: str = "FIXTURE OPS SNAPSHOT") -> tuple[Path, Path]:
    case_root = FIXTURE_ROOT / case_name
    if case_root.exists():
        shutil.rmtree(case_root)
    run_root = case_root / "out" / "daily_portfolio_runs" / run_date

    if right_now_focus is None:
        right_now_focus = f"Fixture focus for {case_name}"
    write_text(
        case_root / "PAPER_TRADE_NOW.md",
        "\n".join([
            f"# Fixture right now for {case_name}",
            "",
            "## Best operator action now",
            "",
            f"- Focus: **{right_now_focus}**",
            f"- Timing: **{right_now_timing}**",
            *([f"- Run freshness: {right_now_run_freshness}"] if right_now_run_freshness else []),
            *([f"- Stale snapshot note: {right_now_stale_snapshot_note}"] if right_now_stale_snapshot_note else []),
            "",
            "## Current context",
            "",
            f"- Latest ops bucket: **{right_now_ops_bucket}**",
            "",
        ]),
    )
    if right_now_issue_flags is None:
        right_now_issue_flags = {
            "has_api_access_failure_context": False,
            "has_scanner_failure_boundary": False,
            "has_stale_cache_fallback_context": False,
        }
    write_json(
        case_root / "PAPER_TRADE_NOW.json",
        {
            "operator_read_gate": {
                "valid_use": "operator instruction/evidence-read gating only",
                "gate_status": "fixture_operator_read_gate",
                "requires_refresh_before_evidence_read": False,
                "recommended_command": "./run_daily_portfolio_observation.sh",
                "read": (
                    "Fixture operator read gate: use the fixture top card as workflow routing only; "
                    "do not treat it as no-target, clean-empty, settled-ROI, promotion, "
                    "live-profitability, bankroll, or real-money evidence."
                ),
                "not_forward_performance_evidence": True,
                "not_promotion_readiness_evidence": True,
                "not_live_profitability_evidence": True,
                "not_bankroll_guidance": True,
                "not_real_money_evidence": True,
                **right_now_issue_flags,
            }
        },
    )
    write_text(case_root / "OPS_HISTORY.md", f"# Fixture ops history for {case_name}\n")
    write_text(
        case_root / "out" / "paper_trade_settlement_audit.md",
        "# Fixture settlement audit\n\n- This fixture audit is a ledger-completeness / ROI-coverage audit only, not new forward evidence by itself.\n",
    )
    if settlement_lanes is None:
        settlement_lanes = [
            {
                "name": "primary",
                "next_action": "collect_signals",
                "next_action_reason": "Fixture primary lane has no ROI-complete settled rows yet; keep collecting qualifying paper observations.",
            },
            {
                "name": "shadow",
                "next_action": "collect_signals",
                "next_action_reason": "Fixture shadow lane has no ROI-complete settled rows yet; keep collecting observation-only paper rows.",
                "promotion_gate": {
                    "scope": "per_rule_shadow_watch",
                    "min_roi_complete_settled_per_rule": 20,
                    "gate_read": "Shadow/watch phase8_promotion_review gate is per-rule: every expected shadow rule needs 20 ROI-complete settled row(s) before review; the 20-row count is a review floor, not a promotion entitlement; lane totals alone do not promote OP_REFINED_K7 or any other Phase 8 pocket; scorecard tiers remain binding (forward_evidence_scorecard.json); negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion; weakest current rule coverage is 0/20.",
                    "rule_progress": [
                        {"rule_id": "OP_REFINED_K7", "roi_complete_settled_rows": 0, "promotion_progress": "0/20 (0.0%)", "scorecard_tier": "WATCH"},
                        {"rule_id": "AQU_K9", "roi_complete_settled_rows": 0, "promotion_progress": "0/20 (0.0%)", "scorecard_tier": "SKIP"},
                    ],
                },
            },
        ]
    write_json(
        case_root / "out" / "paper_trade_settlement_audit.json",
        {
            "artifact_status": "pass",
            "summary": {
                "evidence_boundary": "This fixture audit is a ledger-completeness / ROI-coverage audit only, not new forward evidence by itself.",
            },
            "lanes": settlement_lanes,
        },
    )
    write_text(run_root / "preflight_note.txt", preflight_note + "\n")
    if preflight_json is not None:
        write_json(run_root / "preflight_note.json", preflight_json)
    write_text(run_root / "phase7_current_paper" / "summary.txt", primary_summary.strip() + "\n")
    write_text(run_root / "phase8_shadow" / "summary.txt", shadow_summary.strip() + "\n")

    write_text(run_root / "phase7_current_paper" / "next_steps.txt", primary_next_steps_text.strip() + "\n")
    write_text(run_root / "phase8_shadow" / "next_steps.txt", shadow_next_steps_text.strip() + "\n")

    for rel_path in [
        "phase7_current_paper/next_steps.md",
        "phase7_current_paper/lane_monitor.md",
        "phase7_current_paper/forward_check.md",
        "phase8_shadow/next_steps.md",
        "phase8_shadow/lane_monitor.md",
        "phase8_shadow/forward_check.md",
    ]:
        write_text(run_root / rel_path, f"placeholder for {case_name}: {rel_path}\n")

    return case_root, run_root


def assert_contains(text: str, needle: str, case_name: str) -> None:
    if needle not in text:
        raise AssertionError(f"{case_name}: expected to find {needle!r}")


def assert_api_access_action_route_if_present(text: str, case_name: str) -> bool:
    has_api_access_context = (
        "API-access-failure operator context" in text
        or "API-access scanner failure" in text
        or "403 Client Error" in text
    )
    if not has_api_access_context:
        return False
    assert_contains(text, API_ACCESS_ACTION_TEXT, f"{case_name} API-access sidecar action route")
    assert_contains(text, API_ACCESS_RECHECK_TEXT, f"{case_name} API-access recheck command route")
    return True


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
            "combined daily-summary route visibility, inherited right-now snapshots, lane context, "
            "quick jumps, readiness lines, and green validator passes do not count toward "
            "anchor-displacement, Phase 8 promotion-review, or real-money discussion gates"
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--fixture-root", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def configure_output_paths(fixture_root: Path, out_dir: Path) -> None:
    global FIXTURE_ROOT, OUT_DIR, OUT_MD, OUT_JSON
    FIXTURE_ROOT = fixture_root
    OUT_DIR = out_dir
    OUT_MD = OUT_DIR / "paper_trade_daily_summary_validation.md"
    OUT_JSON = OUT_DIR / "paper_trade_daily_summary_validation.json"


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
            check_name="scorecard_boolean_gate_floor_fails_before_daily_summary_artifacts",
            detail=(
                "a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before "
                "the daily-summary validator creates fixture roots or report artifacts"
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
            check_name="scorecard_phase8_gate_floor_fails_before_daily_summary_artifacts",
            detail=(
                "a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails before "
                "the daily-summary validator creates fixture roots or report artifacts"
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
            check_name="scorecard_real_money_gate_floor_fails_before_daily_summary_artifacts",
            detail=(
                "a non-positive real-money discussion floor in forward_evidence_scorecard.json fails before "
                "the daily-summary validator creates fixture roots or report artifacts"
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
            check_name="scorecard_missing_no_baq_fails_before_daily_summary_artifacts",
            detail=(
                "a scorecard real-money gate that drops the no BAQ-as-BEL prerequisite fails before "
                "the daily-summary validator creates fixture roots or report artifacts"
            ),
        ),
    ]


def run_case(case_name: str, case_root: Path, run_root: Path, expected_needles: list[str], scenario: str | None = None) -> dict[str, Any]:
    output = case_root / "daily_summary.txt"
    right_now_path = case_root / "PAPER_TRADE_NOW.md"
    ops_history_path = case_root / "OPS_HISTORY.md"
    settlement_audit_path = case_root / "out" / "paper_trade_settlement_audit.md"
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--run-root", str(run_root),
        "--right-now", str(right_now_path),
        "--ops-history", str(ops_history_path),
        "--settlement-audit", str(settlement_audit_path),
        "--output", str(output),
    ]
    result = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, check=True)
    content = output.read_text(encoding="utf-8")

    rebuilt_args = argparse.Namespace(
        run_root=str(run_root),
        primary_lane=ptds.DEFAULT_PRIMARY_LANE,
        shadow_lane=ptds.DEFAULT_SHADOW_LANE,
        primary_label=ptds.DEFAULT_PRIMARY_LABEL,
        shadow_label=ptds.DEFAULT_SHADOW_LABEL,
        right_now=str(right_now_path),
        ops_history=str(ops_history_path),
        settlement_audit=str(settlement_audit_path),
        output=str(output),
    )
    rebuilt_payload = ptds.build_payload(rebuilt_args)
    rebuilt = ptds.render_text(rebuilt_payload)
    if content != rebuilt:
        raise AssertionError(f"{case_name}: daily_summary.txt no longer matches a fresh rebuild from paper_trade_daily_summary.py")

    assert_contains(content, f"- Right now: {right_now_path.relative_to(BASE)}", f"{case_name} routed right-now quick jump")
    assert_contains(content, f"- Right-now JSON: {right_now_path.with_suffix('.json').relative_to(BASE)}", f"{case_name} routed right-now JSON quick jump")
    assert_contains(content, f"- Rolling ops history: {ops_history_path.relative_to(BASE)}", f"{case_name} routed ops-history quick jump")
    assert_contains(content, f"- Settlement audit: {settlement_audit_path.relative_to(BASE)}", f"{case_name} routed settlement-audit quick jump")
    assert_contains(content, "- Settlement-audit actions are ledger-readiness guidance only; they are not new forward evidence by themselves.", f"{case_name} settlement-audit action boundary")
    primary_audit_line = f"- Primary settlement-audit action: {rebuilt_payload['primary_settlement_audit_next_action']}"
    if rebuilt_payload.get("primary_settlement_audit_next_action_reason"):
        primary_audit_line += f" — {rebuilt_payload['primary_settlement_audit_next_action_reason']}"
    shadow_audit_line = f"- Shadow settlement-audit action: {rebuilt_payload['shadow_settlement_audit_next_action']}"
    if rebuilt_payload.get("shadow_settlement_audit_next_action_reason"):
        shadow_audit_line += f" — {rebuilt_payload['shadow_settlement_audit_next_action_reason']}"
    assert_contains(content, primary_audit_line, f"{case_name} primary settlement-audit next-action line")
    assert_contains(content, shadow_audit_line, f"{case_name} shadow settlement-audit next-action line")
    if rebuilt_payload.get("shadow_settlement_audit_promotion_gate"):
        assert_contains(content, f"- Shadow settlement-audit promotion gate: {rebuilt_payload['shadow_settlement_audit_promotion_gate']}", f"{case_name} shadow settlement-audit promotion-gate line")
    if rebuilt_payload.get("shadow_settlement_audit_rule_progress"):
        assert_contains(content, f"- Shadow per-rule promotion coverage: {rebuilt_payload['shadow_settlement_audit_rule_progress']}", f"{case_name} shadow per-rule promotion-coverage line")
    assert_contains(content, "Right-now snapshot:", f"{case_name} right-now snapshot header")
    if rebuilt_payload.get("right_now_focus"):
        assert_contains(content, f"- Current operator focus: {rebuilt_payload['right_now_focus']}", f"{case_name} right-now focus snapshot")
    if rebuilt_payload.get("right_now_timing"):
        assert_contains(content, f"- Current timing: {rebuilt_payload['right_now_timing']}", f"{case_name} right-now timing snapshot")
    if rebuilt_payload.get("right_now_run_freshness"):
        assert_contains(content, f"- Current run freshness: {rebuilt_payload['right_now_run_freshness']}", f"{case_name} right-now freshness snapshot")
    if rebuilt_payload.get("right_now_stale_snapshot_note"):
        assert_contains(content, f"- Current stale snapshot note: {rebuilt_payload['right_now_stale_snapshot_note']}", f"{case_name} right-now stale snapshot note")
    if rebuilt_payload.get("right_now_ops_bucket"):
        assert_contains(content, f"- Current ops bucket: {rebuilt_payload['right_now_ops_bucket']}", f"{case_name} right-now ops-bucket snapshot")
    assert_contains(content, f"- Current operator read gate: {rebuilt_payload['right_now_operator_read_gate']}", f"{case_name} right-now operator read-gate line")
    if rebuilt_payload.get("right_now_operator_read_gate_status"):
        assert_contains(content, f"- Current operator read-gate status: {rebuilt_payload['right_now_operator_read_gate_status']}", f"{case_name} right-now operator read-gate status")
    if rebuilt_payload.get("right_now_operator_read_gate_requires_refresh") is not None:
        assert_contains(content, f"- Current read gate requires refresh: {rebuilt_payload['right_now_operator_read_gate_requires_refresh']}", f"{case_name} right-now read-gate refresh flag")
    if rebuilt_payload.get("right_now_operator_read_gate_recommended_command"):
        assert_contains(content, f"- Current read-gate command: {rebuilt_payload['right_now_operator_read_gate_recommended_command']}", f"{case_name} right-now read-gate command")
    assert_contains(content, f"- Current operator read-gate issue flags: {rebuilt_payload['right_now_operator_read_gate_issue_flags']}", f"{case_name} right-now read-gate issue flags")
    assert_contains(content, f"- Preflight note: {rebuilt_payload['preflight_note_path']}", f"{case_name} routed preflight quick jump")
    if rebuilt_payload.get("preflight_excluded_track_summary"):
        assert_contains(content, f"Excluded track aliases: {rebuilt_payload['preflight_excluded_track_summary']}", f"{case_name} structured preflight excluded-track alias visibility")
    assert_contains(content, f"- Primary summary: {run_root.relative_to(BASE) / 'phase7_current_paper/summary.txt'}", f"{case_name} routed primary summary quick jump")
    assert_contains(content, f"- Primary next steps: {run_root.relative_to(BASE) / 'phase7_current_paper/next_steps.md'}", f"{case_name} routed primary next-steps quick jump")
    assert_contains(content, f"- Primary next-step source artifact: {rebuilt_payload['primary_next_steps_source']}", f"{case_name} primary next-step source artifact")
    assert_contains(content, f"- Primary lane monitor: {run_root.relative_to(BASE) / 'phase7_current_paper/lane_monitor.md'}", f"{case_name} routed primary lane-monitor quick jump")
    assert_contains(content, f"- Primary forward check: {run_root.relative_to(BASE) / 'phase7_current_paper/forward_check.md'}", f"{case_name} routed primary forward-check quick jump")
    assert_contains(content, f"- Shadow summary: {run_root.relative_to(BASE) / 'phase8_shadow/summary.txt'}", f"{case_name} routed shadow summary quick jump")
    assert_contains(content, f"- Shadow next steps: {run_root.relative_to(BASE) / 'phase8_shadow/next_steps.md'}", f"{case_name} routed shadow next-steps quick jump")
    assert_contains(content, f"- Shadow next-step source artifact: {rebuilt_payload['shadow_next_steps_source']}", f"{case_name} shadow next-step source artifact")
    assert_contains(content, f"- Shadow lane monitor: {run_root.relative_to(BASE) / 'phase8_shadow/lane_monitor.md'}", f"{case_name} routed shadow lane-monitor quick jump")
    assert_contains(content, f"- Shadow forward check: {run_root.relative_to(BASE) / 'phase8_shadow/forward_check.md'}", f"{case_name} routed shadow forward-check quick jump")
    assert_contains(content, f"Artifacts root: {run_root.relative_to(BASE)}", f"{case_name} routed artifacts-root pointer")
    assert_contains(content, "Evidence frame:", f"{case_name} evidence-frame header")
    assert_contains(content, f"- valid_evidence_scope={ptds.DAILY_SUMMARY_VALID_EVIDENCE_SCOPE}", f"{case_name} source evidence scope line")
    assert_contains(content, f"- Boundary: {ptds.DAILY_SUMMARY_EVIDENCE_BOUNDARY_TEXT}", f"{case_name} source evidence boundary line")
    assert_contains(content, "- Workflow and navigation surface: This daily summary is an operator workflow surface, not a profit-proof or CI-backed forward-validation report.", f"{case_name} evidence-frame summary line")
    assert_contains(content, "- Limitation: Use it to decide what to read or do next; treat forward performance claims as pending until settled paper trades with usable return/cost coverage accumulate in the underlying lane artifacts.", f"{case_name} evidence-frame limitation line")
    assert_contains(content, "- Primary readiness: first read", f"{case_name} primary readiness line")
    assert_contains(content, "| broader review ", f"{case_name} readiness format")
    if rebuilt_payload.get("primary_decision_gate"):
        assert_contains(content, f"- Primary decision gate: {rebuilt_payload['primary_decision_gate']}", f"{case_name} primary decision-gate snapshot line")
    if rebuilt_payload.get("shadow_decision_gate"):
        assert_contains(content, f"- Shadow decision gate: {rebuilt_payload['shadow_decision_gate']}", f"{case_name} shadow decision-gate snapshot line")
    if rebuilt_payload.get("primary_recent_run_context"):
        assert_contains(content, f"- Primary lane context: {rebuilt_payload['primary_recent_run_context']}", f"{case_name} primary recent-context line")
    if rebuilt_payload.get("primary_why_now"):
        assert_contains(content, f"- Primary lane why now: {rebuilt_payload['primary_why_now']}", f"{case_name} primary why-now line")
    if rebuilt_payload.get("primary_sidecar_action"):
        assert_contains(content, f"- Primary sidecar action: {rebuilt_payload['primary_sidecar_action']}", f"{case_name} primary sidecar action line")
    if rebuilt_payload.get("primary_recheck_command"):
        assert_contains(content, f"- Primary recheck command: {rebuilt_payload['primary_recheck_command']}", f"{case_name} primary recheck command line")
    assert_contains(content, "- Primary settlement integrity:", f"{case_name} primary settlement-integrity line")
    assert_contains(content, "- Primary ROI coverage:", f"{case_name} primary ROI-coverage line")
    if rebuilt_payload.get("primary_roi_gap_summary"):
        assert_contains(content, f"- Primary ROI coverage gaps: {rebuilt_payload['primary_roi_gap_summary']}", f"{case_name} primary ROI-gap summary line")
    assert_contains(content, "- Shadow readiness: first read", f"{case_name} shadow readiness line")
    if rebuilt_payload.get("shadow_recent_run_context"):
        assert_contains(content, f"- Shadow lane context: {rebuilt_payload['shadow_recent_run_context']}", f"{case_name} shadow recent-context line")
    if rebuilt_payload.get("shadow_why_now"):
        assert_contains(content, f"- Shadow lane why now: {rebuilt_payload['shadow_why_now']}", f"{case_name} shadow why-now line")
    if rebuilt_payload.get("shadow_sidecar_action"):
        assert_contains(content, f"- Shadow sidecar action: {rebuilt_payload['shadow_sidecar_action']}", f"{case_name} shadow sidecar action line")
    if rebuilt_payload.get("shadow_recheck_command"):
        assert_contains(content, f"- Shadow recheck command: {rebuilt_payload['shadow_recheck_command']}", f"{case_name} shadow recheck command line")
    assert_contains(content, "- Shadow settlement integrity:", f"{case_name} shadow settlement-integrity line")
    assert_contains(content, "- Shadow ROI coverage:", f"{case_name} shadow ROI-coverage line")
    if rebuilt_payload.get("shadow_roi_gap_summary"):
        assert_contains(content, f"- Shadow ROI coverage gaps: {rebuilt_payload['shadow_roi_gap_summary']}", f"{case_name} shadow ROI-gap summary line")

    for needle in expected_needles:
        assert_contains(content, needle, case_name)

    return {
        "case": case_name,
        "scenario": scenario,
        "output": str(output.relative_to(BASE)),
        "artifacts_root": f"Artifacts root: {run_root.relative_to(BASE)}",
        "first_line": content.splitlines()[0],
        "preview": result.stdout.splitlines()[:6],
    }


def live_run_roots() -> list[Path]:
    candidates = sorted(p for p in LIVE_RUNS_ROOT.iterdir() if p.is_dir()) if LIVE_RUNS_ROOT.exists() else []
    if not candidates:
        raise AssertionError(f"no live run folders found under {LIVE_RUNS_ROOT}")
    return candidates


def extract_live_field(text: str, label: str) -> str | None:
    match = re.search(rf"(?:^|\n)\s*-\s*{re.escape(label)}:\s*(.+)", text)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def validate_live_surfaces() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for run_root in live_run_roots():
        output = run_root / "daily_summary.txt"
        args = argparse.Namespace(
            run_root=str(run_root),
            primary_lane=ptds.DEFAULT_PRIMARY_LANE,
            shadow_lane=ptds.DEFAULT_SHADOW_LANE,
            primary_label=ptds.DEFAULT_PRIMARY_LABEL,
            shadow_label=ptds.DEFAULT_SHADOW_LABEL,
            right_now=str(ptds.DEFAULT_RIGHT_NOW),
            ops_history=str(ptds.DEFAULT_OPS_HISTORY),
            settlement_audit=str(ptds.DEFAULT_SETTLEMENT_AUDIT),
            output=str(output),
        )
        expected_payload = ptds.build_payload(args)
        if not output.exists():
            raise AssertionError(f"missing live daily summary surface: {output}")
        live_text = output.read_text(encoding="utf-8")
        for payload_key, label in (
            ("right_now_focus", "Current operator focus"),
            ("right_now_timing", "Current timing"),
            ("right_now_run_freshness", "Current run freshness"),
            ("right_now_stale_snapshot_note", "Current stale snapshot note"),
            ("right_now_ops_bucket", "Current ops bucket"),
        ):
            live_value = extract_live_field(live_text, label)
            if live_value:
                expected_payload[payload_key] = live_value
            elif payload_key == "right_now_stale_snapshot_note":
                expected_payload[payload_key] = ""
        expected = ptds.render_text(expected_payload)
        if live_text != expected:
            raise AssertionError(f"live daily_summary.txt drifted from the current source-layer rebuild: {output}")
        assert_contains(live_text, f"- Right now: {Path(ptds.DEFAULT_RIGHT_NOW).relative_to(BASE)}", f"live_surface_{run_root.name} routed right-now quick jump")
        assert_contains(live_text, f"- Right-now JSON: {Path(ptds.DEFAULT_RIGHT_NOW).with_suffix('.json').relative_to(BASE)}", f"live_surface_{run_root.name} routed right-now JSON quick jump")
        assert_contains(live_text, f"- Rolling ops history: {Path(ptds.DEFAULT_OPS_HISTORY).relative_to(BASE)}", f"live_surface_{run_root.name} routed ops-history quick jump")
        assert_contains(live_text, f"- Settlement audit: {Path(ptds.DEFAULT_SETTLEMENT_AUDIT).relative_to(BASE)}", f"live_surface_{run_root.name} routed settlement-audit quick jump")
        assert_contains(live_text, "Right-now snapshot:", f"live_surface_{run_root.name} right-now snapshot header")
        if expected_payload.get("right_now_focus"):
            assert_contains(live_text, f"- Current operator focus: {expected_payload['right_now_focus']}", f"live_surface_{run_root.name} right-now focus snapshot")
        if expected_payload.get("right_now_timing"):
            assert_contains(live_text, f"- Current timing: {expected_payload['right_now_timing']}", f"live_surface_{run_root.name} right-now timing snapshot")
        if expected_payload.get("right_now_run_freshness"):
            assert_contains(live_text, f"- Current run freshness: {expected_payload['right_now_run_freshness']}", f"live_surface_{run_root.name} right-now freshness snapshot")
        if expected_payload.get("right_now_stale_snapshot_note"):
            assert_contains(live_text, f"- Current stale snapshot note: {expected_payload['right_now_stale_snapshot_note']}", f"live_surface_{run_root.name} right-now stale snapshot note")
        if expected_payload.get("right_now_ops_bucket"):
            assert_contains(live_text, f"- Current ops bucket: {expected_payload['right_now_ops_bucket']}", f"live_surface_{run_root.name} right-now ops-bucket snapshot")
        assert_contains(live_text, f"- Current operator read gate: {expected_payload['right_now_operator_read_gate']}", f"live_surface_{run_root.name} right-now operator read-gate line")
        if expected_payload.get("right_now_operator_read_gate_status"):
            assert_contains(live_text, f"- Current operator read-gate status: {expected_payload['right_now_operator_read_gate_status']}", f"live_surface_{run_root.name} right-now operator read-gate status")
        if expected_payload.get("right_now_operator_read_gate_requires_refresh") is not None:
            assert_contains(live_text, f"- Current read gate requires refresh: {expected_payload['right_now_operator_read_gate_requires_refresh']}", f"live_surface_{run_root.name} right-now read-gate refresh flag")
        if expected_payload.get("right_now_operator_read_gate_recommended_command"):
            assert_contains(live_text, f"- Current read-gate command: {expected_payload['right_now_operator_read_gate_recommended_command']}", f"live_surface_{run_root.name} right-now read-gate command")
        assert_contains(live_text, f"- Current operator read-gate issue flags: {expected_payload['right_now_operator_read_gate_issue_flags']}", f"live_surface_{run_root.name} right-now read-gate issue flags")
        assert_contains(live_text, f"- Preflight note: {expected_payload['preflight_note_path']}", f"live_surface_{run_root.name} routed preflight quick jump")
        if expected_payload.get("preflight_excluded_track_summary"):
            assert_contains(live_text, f"Excluded track aliases: {expected_payload['preflight_excluded_track_summary']}", f"live_surface_{run_root.name} structured preflight excluded-track alias visibility")
        assert_contains(live_text, f"- Primary summary: {run_root.relative_to(BASE) / 'phase7_current_paper/summary.txt'}", f"live_surface_{run_root.name} routed primary summary quick jump")
        assert_contains(live_text, f"- Primary next steps: {run_root.relative_to(BASE) / 'phase7_current_paper/next_steps.md'}", f"live_surface_{run_root.name} routed primary next-steps quick jump")
        assert_contains(live_text, f"- Primary lane monitor: {run_root.relative_to(BASE) / 'phase7_current_paper/lane_monitor.md'}", f"live_surface_{run_root.name} routed primary lane-monitor quick jump")
        assert_contains(live_text, f"- Primary forward check: {run_root.relative_to(BASE) / 'phase7_current_paper/forward_check.md'}", f"live_surface_{run_root.name} routed primary forward-check quick jump")
        assert_contains(live_text, f"- Shadow summary: {run_root.relative_to(BASE) / 'phase8_shadow/summary.txt'}", f"live_surface_{run_root.name} routed shadow summary quick jump")
        assert_contains(live_text, f"- Shadow next steps: {run_root.relative_to(BASE) / 'phase8_shadow/next_steps.md'}", f"live_surface_{run_root.name} routed shadow next-steps quick jump")
        assert_contains(live_text, f"- Shadow lane monitor: {run_root.relative_to(BASE) / 'phase8_shadow/lane_monitor.md'}", f"live_surface_{run_root.name} routed shadow lane-monitor quick jump")
        assert_contains(live_text, f"- Shadow forward check: {run_root.relative_to(BASE) / 'phase8_shadow/forward_check.md'}", f"live_surface_{run_root.name} routed shadow forward-check quick jump")
        assert_contains(live_text, f"Artifacts root: {run_root.relative_to(BASE)}", f"live_surface_{run_root.name} routed artifacts-root pointer")
        assert_contains(live_text, "Evidence frame:", f"live_surface_{run_root.name} evidence-frame header")
        assert_contains(live_text, f"- valid_evidence_scope={ptds.DAILY_SUMMARY_VALID_EVIDENCE_SCOPE}", f"live_surface_{run_root.name} source evidence scope line")
        assert_contains(live_text, f"- Boundary: {ptds.DAILY_SUMMARY_EVIDENCE_BOUNDARY_TEXT}", f"live_surface_{run_root.name} source evidence boundary line")
        assert_contains(live_text, "- Workflow and navigation surface: This daily summary is an operator workflow surface, not a profit-proof or CI-backed forward-validation report.", f"live_surface_{run_root.name} evidence-frame summary line")
        assert_contains(live_text, "- Limitation: Use it to decide what to read or do next; treat forward performance claims as pending until settled paper trades with usable return/cost coverage accumulate in the underlying lane artifacts.", f"live_surface_{run_root.name} evidence-frame limitation line")
        assert_contains(live_text, "- Primary readiness: first read", f"live_surface_{run_root.name} primary readiness line")
        assert_contains(live_text, "| broader review ", f"live_surface_{run_root.name} readiness format")
        if expected_payload.get("primary_decision_gate"):
            assert_contains(live_text, f"- Primary decision gate: {expected_payload['primary_decision_gate']}", f"live_surface_{run_root.name} primary decision-gate snapshot line")
        if expected_payload.get("shadow_decision_gate"):
            assert_contains(live_text, f"- Shadow decision gate: {expected_payload['shadow_decision_gate']}", f"live_surface_{run_root.name} shadow decision-gate snapshot line")
        if expected_payload.get("primary_recent_run_context"):
            assert_contains(live_text, f"- Primary lane context: {expected_payload['primary_recent_run_context']}", f"live_surface_{run_root.name} primary recent-context line")
        if expected_payload.get("primary_why_now"):
            assert_contains(live_text, f"- Primary lane why now: {expected_payload['primary_why_now']}", f"live_surface_{run_root.name} primary why-now line")
        assert_contains(live_text, "- Primary settlement integrity:", f"live_surface_{run_root.name} primary settlement-integrity line")
        assert_contains(live_text, "- Primary ROI coverage:", f"live_surface_{run_root.name} primary ROI-coverage line")
        if expected_payload.get("primary_roi_gap_summary"):
            assert_contains(live_text, f"- Primary ROI coverage gaps: {expected_payload['primary_roi_gap_summary']}", f"live_surface_{run_root.name} primary ROI-gap summary line")
        assert_contains(live_text, "- Shadow readiness: first read", f"live_surface_{run_root.name} shadow readiness line")
        if expected_payload.get("shadow_recent_run_context"):
            assert_contains(live_text, f"- Shadow lane context: {expected_payload['shadow_recent_run_context']}", f"live_surface_{run_root.name} shadow recent-context line")
        if expected_payload.get("shadow_why_now"):
            assert_contains(live_text, f"- Shadow lane why now: {expected_payload['shadow_why_now']}", f"live_surface_{run_root.name} shadow why-now line")
        assert_contains(live_text, "- Shadow settlement integrity:", f"live_surface_{run_root.name} shadow settlement-integrity line")
        assert_contains(live_text, "- Shadow ROI coverage:", f"live_surface_{run_root.name} shadow ROI-coverage line")
        if expected_payload.get("shadow_roi_gap_summary"):
            assert_contains(live_text, f"- Shadow ROI coverage gaps: {expected_payload['shadow_roi_gap_summary']}", f"live_surface_{run_root.name} shadow ROI-gap summary line")
        api_access_action_route_confirmed = assert_api_access_action_route_if_present(
            live_text,
            f"live_surface_{run_root.name}",
        )
        results.append({
            "case": f"live_surface_{run_root.name}",
            "scenario": "saved live daily_summary.txt matches the current source-layer rebuild",
            "run_root": str(run_root.relative_to(BASE)),
            "output": str(output.relative_to(BASE)),
            "first_line": expected.splitlines()[0] if expected else "",
            "api_access_action_route_confirmed": api_access_action_route_confirmed,
        })
    return results


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_output_paths(args.fixture_root, args.out_dir)
    scorecard_gates = read_scorecard_gate_minimums(args.scorecard_json)
    scorecard_guardrails = scorecard_no_artifact_guardrails(args.scorecard_json)

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for legacy in [
        FIXTURE_ROOT / "daily_summary_fixture_validation.md",
        FIXTURE_ROOT / "daily_summary_fixture_validation.json",
    ]:
        if legacy.exists():
            legacy.unlink()
    suite_read = (
        "daily summary still preserves the full routed quick-jump bundle including the settlement-audit quick read, routed right-now JSON pointer plus current operator_read_gate read/status/refresh-command lines and issue flags, including true operator_read_gate issue flags in the 403 stale-cache fallback fixture, direct primary/shadow settlement-audit next-action lines, the shadow settlement-audit per-rule promotion gate plus per-rule coverage line, an explicit routed right-now focus/timing/freshness/stale-snapshot/ops snapshot, preflight context, an explicit current live hierarchy block, an explicit workflow-and-navigation evidence-frame disclaimer, explicit primary/shadow next-step source artifact paths and state lines plus lifted no-overpromotion decision-gate snapshot lines, first-read and broader-review readiness lines, explicit primary/shadow settlement-integrity, ROI-coverage, and settled-row ROI-gap-reason lines, explicit primary/shadow recent-run context plus why-now lines when next-steps surfaces save them, including saved-live and direct-fixture API-access action/recheck routing when lane context is a 403 scanner failure with stale-cache fallback and markdown-only next-steps fallback when the text mirror is missing or blank, primary and shadow lane sections, artifacts-root, "
        "explicit recommender/logger pipeline-failure summary context, preserved missing scan-output fallback context plus pipeline-recorded empty/unreadable/invalid-shape scanner-status issue lines from copied lane summaries, malformed/invalid-shape/missing-lanes settlement-audit JSON sidecars separated from missing audit JSON, explicit fallback to the saved preflight JSON note when the sibling text surface is missing on both active-target and no-target days, continued preference for that saved JSON note when the sibling text artifact exists but is blank on both active-target and no-target days, structured preflight excluded-track alias visibility so BAQ remains explicitly not BEL when saved JSON carries that calendar context, and explicit placeholders when preflight, lane-summary, or required next-steps fields are missing, "
        "with shadow review-readiness visible without implying live promotion, the ROI-complete settled-evidence boundary visible in the evidence frame, source rendered daily summaries and the direct validator report now publish exact `valid_evidence_scope=daily_operator_workflow_navigation_only` lines plus source-level boundary text so combined quick jumps, inherited right-now snapshots, lane context, readiness lines, settlement-audit action routing, clean-empty/no-target routing, issue routing, and saved-live rebuild cleanliness remain workflow/navigation metadata only, malformed scorecard gates rejected before fixture/report artifacts, including non-positive Phase 8 and real-money floors, the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite preserved as a boundary that combined quick jumps, inherited right-now snapshots, lane context, and readiness lines do not advance, and the rendered text surface pinned at the source layer; daily summary: operator workflow/navigation surface, not new forward evidence by itself"
    )

    empty_root, empty_run = setup_case(
        case_name="case_empty_no_targets",
        run_date="2026-05-10",
        preflight_note="Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 20 NYRA card(s). Shadow-only tracks present: KEE.",
        primary_summary="Phase 7 current paper run 2026-05-10T10:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        shadow_summary="Phase 8 shadow run 2026-05-10T10:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
    )
    pending_root, pending_run = setup_case(
        case_name="case_settlement_pending",
        run_date="2026-05-11",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        primary_summary="Phase 7 current paper run 2026-05-11T17:00:00: signals logged, 2 pending settlement row(s), forward check still early",
        shadow_summary="Phase 8 shadow run 2026-05-11T17:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        primary_next_steps_text="Phase 7 current paper lane next steps\n- State: NEEDS SETTLEMENT\n- Settled races: 0 | open races: 2 | open settlement rows: 2 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- First statistical-read progress: 0/30 settled (30 more needed)\n- Broader portfolio-review progress: 0/100 settled (100 more needed)",
    )
    incomplete_root, incomplete_run = setup_case(
        case_name="case_incomplete_settlement_gap",
        run_date="2026-05-17",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP.",
        primary_summary="Phase 7 current paper run 2026-05-17T17:20:00: settlement cleanup pending, 1 row marked settled without an outcome",
        shadow_summary="Phase 8 shadow run 2026-05-17T17:20:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        primary_next_steps_text="Phase 7 current paper lane next steps\n- State: NEEDS SETTLEMENT\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 1\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- First statistical-read progress: 0/30 settled (30 more needed)\n- Broader portfolio-review progress: 0/100 settled (100 more needed)",
    )
    partial_roi_root, partial_roi_run = setup_case(
        case_name="case_partial_roi_coverage_gap",
        run_date="2026-05-18",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP.",
        primary_summary="""Phase 7 current paper run 2026-05-18T17:40:00: collecting sample, 5 settled races but only partial return coverage so ROI remains incomplete
- Decision gate: No strategy change: 5 settled race(s) is below the first statistical-read gate of 30.""",
        shadow_summary="""Phase 8 shadow run 2026-05-18T17:40:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)
- Decision gate: No strategy change: this is still pre-evidence with 0 settled races.""",
        primary_next_steps_text="Phase 7 current paper lane next steps\n- State: COLLECTING SAMPLE\n- Settled races: 5 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 2/5 settled races have return values (3 still missing return/cost coverage)\n- Settled rows missing ROI coverage: 3 (missing actual_return: 3)\n- First statistical-read progress: 5/30 settled (25 more needed)\n- Broader portfolio-review progress: 5/100 settled (95 more needed)",
        settlement_lanes=[
            {
                "name": "primary",
                "next_action": "repair_roi_coverage",
                "next_action_reason": "Primary fixture has 3 settled rows missing usable ROI coverage; repair actual_return before reading ROI.",
            },
            {
                "name": "shadow",
                "next_action": "collect_signals",
                "next_action_reason": "Fixture shadow lane has no ROI-complete settled rows yet; keep collecting observation-only paper rows.",
            },
        ],
    )
    active_root, active_run = setup_case(
        case_name="case_active_target",
        run_date="2026-05-12",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP.",
        primary_summary="Phase 7 current paper run 2026-05-12T18:10:00: bets ready, 1 BET recommendation(s), read lane monitor before post time",
        shadow_summary="Phase 8 shadow run 2026-05-12T18:10:00: signals logged, no BET recommendation(s)",
        primary_next_steps_text="Phase 7 current paper lane next steps\n- State: WAITING FOR FIRST SETTLED RACES\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- First statistical-read progress: 0/30 settled (30 more needed)\n- Broader portfolio-review progress: 0/100 settled (100 more needed)",
        shadow_next_steps_text="Phase 8 shadow lane next steps\n- State: COLLECTING SAMPLE\n- Settled races: 5 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 3/5 settled races have return values (2 still missing return/cost coverage)\n- Settled rows missing ROI coverage: 2 (malformed actual_cost: 1; missing actual_return: 1)\n- First statistical-read progress: 5/20 settled (15 more needed)\n- Broader portfolio-review progress: 5/100 settled (95 more needed)",
    )
    pipeline_recorded_empty_root, pipeline_recorded_empty_run = setup_case(
        case_name="case_pipeline_recorded_empty_scanner_missing",
        run_date="2026-05-24",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP.",
        primary_summary="Phase 7 current paper run 2026-05-24T18:20:00: scanner sidecar recorded empty, 0 scanner hit(s), 0 recommendation(s), current scanner sidecar file missing, pipeline recorded scanner-status state empty",
        shadow_summary="Phase 8 shadow run 2026-05-24T18:20:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        primary_next_steps_text="Phase 7 current paper lane next steps\n- State: REFRESH RUN ARTIFACTS\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- First statistical-read progress: 0/30 settled (30 more needed)\n- Broader portfolio-review progress: 0/100 settled (100 more needed)\n- Why: The pipeline recorded the scanner status sidecar as empty, but this copied lane surface no longer has the physical scanner sidecar file. Refresh the daily wrapper before reading the lane as clean market quiet.\n- Latest run context: the latest lane run preserved a pipeline-recorded scanner-status state: empty. The current copied scanner sidecar file is missing, so keep this as an operational status issue.",
    )
    pipeline_recorded_unreadable_root, pipeline_recorded_unreadable_run = setup_case(
        case_name="case_pipeline_recorded_unreadable_scanner_missing",
        run_date="2026-05-25",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: CD.",
        primary_summary="Phase 7 current paper run 2026-05-25T18:25:00: scanner sidecar recorded unreadable, 0 scanner hit(s), 0 recommendation(s), current scanner sidecar file missing, pipeline recorded scanner-status state unreadable",
        shadow_summary="Phase 8 shadow run 2026-05-25T18:25:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        primary_next_steps_text="Phase 7 current paper lane next steps\n- State: REFRESH RUN ARTIFACTS\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- First statistical-read progress: 0/30 settled (30 more needed)\n- Broader portfolio-review progress: 0/100 settled (100 more needed)\n- Why: The pipeline recorded the scanner status sidecar as unreadable, but this copied lane surface no longer has the physical scanner sidecar file. Refresh the daily wrapper before reading the lane as clean market quiet.\n- Latest run context: the latest lane run preserved a pipeline-recorded scanner-status state: unreadable. The current copied scanner sidecar file is missing, so keep this as an operational status issue.",
    )
    pipeline_recorded_invalid_shape_root, pipeline_recorded_invalid_shape_run = setup_case(
        case_name="case_pipeline_recorded_invalid_shape_scanner_missing",
        run_date="2026-05-26",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP.",
        primary_summary="Phase 7 current paper run 2026-05-26T18:30:00: scanner sidecar recorded invalid shape, 1 scanner hit(s), 1 recommendation(s), scanner-status error: expected scanner-status JSON object, got list, current scanner sidecar file missing, pipeline recorded scanner-status state invalid_shape",
        shadow_summary="Phase 8 shadow run 2026-05-26T18:30:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        primary_next_steps_text="Phase 7 current paper lane next steps\n- State: REFRESH RUN ARTIFACTS\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- First statistical-read progress: 0/30 settled (30 more needed)\n- Broader portfolio-review progress: 0/100 settled (100 more needed)\n- Why: The latest scanner status sidecar was recorded invalid-shape by the pipeline, and the current scanner sidecar file is missing from this surface. Refresh the daily wrapper before treating this lane as empty.\n- Latest run context: the latest lane run preserved a pipeline-recorded scanner-status state: invalid-shape. The current copied scanner sidecar file is missing, so keep this as an operational status issue.",
    )
    missing_scan_output_root, missing_scan_output_run = setup_case(
        case_name="case_missing_scan_output_context",
        run_date="2026-05-27",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP.",
        primary_summary="Phase 7 current paper run 2026-05-27T18:35:00: missing scanner output, 0 scanner hit(s), 0 recommendation(s); scanner-status reported no_qualifiers; safe empty scan fallback missing_or_empty_scan_output; scan input was missing before fallback",
        shadow_summary="Phase 8 shadow run 2026-05-27T18:35:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        primary_next_steps_text="Phase 7 current paper lane next steps\n- State: REFRESH RUN ARTIFACTS\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- First statistical-read progress: 0/30 settled (30 more needed)\n- Broader portfolio-review progress: 0/100 settled (100 more needed)\n- Why: The latest lane scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers; the pipeline used a safe empty [] fallback. Treat this as an artifact issue, not a clean no-qualifier observation. Refresh the daily wrapper before treating this lane as empty.\n- Latest run context: scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers; the pipeline used a safe empty [] fallback. Treat this as an artifact issue, not a clean no-qualifier observation.",
        right_now_focus="Refresh the daily wrapper, primary lane scan-output artifact is missing",
        right_now_ops_bucket="ISSUE, MISSING SCAN OUTPUT",
    )
    api_access_stale_cache_root, api_access_stale_cache_run = setup_case(
        case_name="case_api_access_stale_cache_fallback_context",
        run_date="2026-05-31",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        primary_summary="Phase 7 current paper run 2026-05-31T18:35:00: scanner API access failure, 0 scanner hit(s), 0 recommendation(s), HTTP 403, API-access-failure operator context only, operator action refresh_daily_wrapper_before_evidence_read, recheck command ./run_daily_portfolio_observation.sh, stale cache fallback used for cards, 2 stale cache fallback(s), stale cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx, scanner failure class api_access_failure",
        shadow_summary="Phase 8 shadow run 2026-05-31T18:35:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        primary_next_steps_text="Phase 7 current paper lane next steps\n- State: CHECK SCANNER FAILURE\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- First statistical-read progress: 0/30 settled (30 more needed)\n- Broader portfolio-review progress: 0/100 settled (100 more needed)\n- Why: Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence. stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx.\n- Latest run context: scanner failed before producing signals. Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence. stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx.\n- Sidecar action: refresh_daily_wrapper_before_evidence_read.\n- Recheck command: ./run_daily_portfolio_observation.sh.",
        right_now_issue_flags={
            "has_api_access_failure_context": True,
            "has_scanner_failure_boundary": True,
            "has_stale_cache_fallback_context": True,
        },
        right_now_focus="Refresh the daily wrapper, primary lane scanner hit an API-access stale-cache fallback",
        right_now_ops_bucket="ISSUE, API ACCESS STALE CACHE FALLBACK",
    )
    malformed_settlement_audit_root, malformed_settlement_audit_run = setup_case(
        case_name="case_malformed_settlement_audit_json",
        run_date="2026-05-28",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: CD.",
        primary_summary="Phase 7 current paper run 2026-05-28T18:50:00: settlement audit sidecar is malformed; refresh audit before reading next actions",
        shadow_summary="Phase 8 shadow run 2026-05-28T18:50:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
    )
    write_text(malformed_settlement_audit_root / "out" / "paper_trade_settlement_audit.json", "{not valid json\n")

    invalid_shape_settlement_audit_root, invalid_shape_settlement_audit_run = setup_case(
        case_name="case_invalid_shape_settlement_audit_json",
        run_date="2026-05-29",
        preflight_note="Preflight context: no primary paper-basket target tracks (OP / CD) are racing today.",
        primary_summary="Phase 7 current paper run 2026-05-29T18:55:00: settlement audit sidecar has invalid shape; refresh audit before reading next actions",
        shadow_summary="Phase 8 shadow run 2026-05-29T18:55:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
    )
    write_text(invalid_shape_settlement_audit_root / "out" / "paper_trade_settlement_audit.json", "[]\n")

    missing_lanes_settlement_audit_root, missing_lanes_settlement_audit_run = setup_case(
        case_name="case_missing_settlement_audit_lanes_list",
        run_date="2026-05-30",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP.",
        primary_summary="Phase 7 current paper run 2026-05-30T19:00:00: settlement audit sidecar is missing the lanes list; refresh audit before reading next actions",
        shadow_summary="Phase 8 shadow run 2026-05-30T19:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
    )
    write_json(
        missing_lanes_settlement_audit_root / "out" / "paper_trade_settlement_audit.json",
        {
            "artifact_status": "pass",
            "summary": {
                "evidence_boundary": "Fixture audit is intentionally missing the lanes list.",
            },
        },
    )

    stale_right_now_root, stale_right_now_run = setup_case(
        case_name="case_stale_right_now_snapshot",
        run_date="2026-05-21",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: CD.",
        primary_summary="Phase 7 current paper run 2026-05-21T17:55:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        shadow_summary="Phase 8 shadow run 2026-05-21T17:55:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        right_now_focus="Refresh the daily wrapper, latest operator card is stale",
        right_now_run_freshness="Latest run date 2026-05-21 is 2 day(s) behind the as-of date 2026-05-23, so the saved top card is stale until the daily wrapper is rerun.",
        right_now_stale_snapshot_note="The preflight note/artifact, excluded-track aliases, lane context, current-state counts, ops streaks, and quick reads below are inherited from the latest saved run (2026-05-21) and should be treated as stale snapshot context until the daily wrapper is rerun.",
        right_now_ops_bucket="ACTIVE, ZERO HITS",
    )
    recommender_failure_root, recommender_failure_run = setup_case(
        case_name="case_recommender_failure_context",
        run_date="2026-05-13",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        primary_summary="Phase 7 current paper run 2026-05-13T18:05:00: recommender failure, 1 scanner hit(s), 0 recommendation(s), last completed stage scanner, stage recommender, scanner hits before failure 1, RuntimeError, detail: fixture recommender crash",
        shadow_summary="Phase 8 shadow run 2026-05-13T18:05:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        primary_next_steps_text="Phase 7 current paper lane next steps\n- State: CHECK PIPELINE FAILURE\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- First statistical-read progress: 0/30 settled (30 more needed)\n- Broader portfolio-review progress: 0/100 settled (100 more needed)\n- Why: The latest lane run ended in recommender failure, so treat this as an operational issue instead of normal observation noise. The scanner had already found 1 hit(s) before the recommender failed. Refresh the daily wrapper and re-check the lane before reading it as evidence.\n- Latest run context: the latest lane run ended in recommender failure. Last completed stage: scanner. Stage: recommender. Scanner hits before failure: 1. Error type: RuntimeError. Detail: fixture recommender crash",
    )
    logger_failure_root, logger_failure_run = setup_case(
        case_name="case_logger_failure_context",
        run_date="2026-05-14",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        primary_summary="Phase 7 current paper run 2026-05-14T18:10:00: logger failure, 1 scanner hit(s), 1 recommendation(s), 1 BET, last completed stage recommender, stage logger, recommendations built before failure 1, BET recommendations before failure 1, pre-error context bets_ready, ValueError, detail: fixture logger crash",
        shadow_summary="Phase 8 shadow run 2026-05-14T18:10:00: signals logged, no BET recommendation(s)",
        primary_next_steps_text="Phase 7 current paper lane next steps\n- State: CHECK PIPELINE FAILURE\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- First statistical-read progress: 0/30 settled (30 more needed)\n- Broader portfolio-review progress: 0/100 settled (100 more needed)\n- Why: The latest lane run ended in logger failure, so treat this as an operational issue instead of normal observation noise. The recommender had already produced 1 recommendation(s), including 1 BET recommendation(s), before the logger failed. Refresh the daily wrapper and re-check the lane before reading it as evidence.\n- Latest run context: the latest lane run ended in logger failure. Last completed stage: recommender. Stage: logger. Recommendations built before failure: 1. BET recommendations before failure: 1. Pre-error lane context: bets_ready. Error type: ValueError. Detail: fixture logger crash",
    )
    missing_shadow_root, missing_shadow_run = setup_case(
        case_name="case_missing_shadow_summary",
        run_date="2026-05-15",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        primary_summary="Phase 7 current paper run 2026-05-15T17:45:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        shadow_summary="Phase 8 shadow run 2026-05-15T17:45:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        shadow_next_steps_text="Phase 8 shadow lane next steps\n- State: DECISION-GRADE REVIEW\n- Settled races: 20 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 20/20 settled races have return values (0 still missing return/cost coverage)\n- First statistical-read progress: 20/20 settled (threshold reached)\n- Broader portfolio-review progress: 20/100 settled (80 more needed)",
    )
    (missing_shadow_run / "phase8_shadow" / "summary.txt").unlink()

    missing_preflight_root, missing_preflight_run = setup_case(
        case_name="case_missing_preflight_note",
        run_date="2026-05-16",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        primary_summary="Phase 7 current paper run 2026-05-16T18:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        shadow_summary="Phase 8 shadow run 2026-05-16T18:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        primary_next_steps_text="Phase 7 current paper lane next steps\n- State: WAITING FOR FIRST SETTLED RACES\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- First statistical-read progress: 0/30 settled (30 more needed)\n- Broader portfolio-review progress: 0/100 settled (100 more needed)",
        shadow_next_steps_text="Phase 8 shadow lane next steps\n- State: COLLECTING SAMPLE\n- Settled races: 5 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 5/5 settled races have return values (0 still missing return/cost coverage)\n- First statistical-read progress: 5/20 settled (15 more needed)\n- Broader portfolio-review progress: 5/100 settled (95 more needed)",
    )
    (missing_preflight_run / "preflight_note.txt").unlink()

    json_only_preflight_root, json_only_preflight_run = setup_case(
        case_name="case_json_only_preflight_note",
        run_date="2026-05-19",
        preflight_note="JSON-only preflight note: OP is active today even though the text surface is missing.",
        preflight_json={
            "date": "2026-05-19",
            "checked_at": "2026-05-19 12:00",
            "api_ok": True,
            "calendar_state": "ACTIVE TARGETS",
            "calendar_reason": "active_targets",
            "has_targets": True,
            "relevant_tracks": ["OP"],
            "shadow_tracks": [],
            "total_cards": 18,
            "error": None,
            "note": "JSON-only preflight note: OP is active today even though the text surface is missing.",
        },
        primary_summary="Phase 7 current paper run 2026-05-19T18:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        shadow_summary="Phase 8 shadow run 2026-05-19T18:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
    )
    (json_only_preflight_run / "preflight_note.txt").unlink()

    blank_text_json_preflight_root, blank_text_json_preflight_run = setup_case(
        case_name="case_blank_text_prefers_json_preflight_note",
        run_date="2026-05-21",
        preflight_note="JSON preflight should still win when the sibling text file is blank.",
        preflight_json={
            "date": "2026-05-21",
            "checked_at": "2026-05-21 12:00",
            "api_ok": True,
            "calendar_state": "ACTIVE TARGETS",
            "calendar_reason": "active_targets",
            "has_targets": True,
            "relevant_tracks": ["OP"],
            "shadow_tracks": [],
            "total_cards": 18,
            "error": None,
            "note": "JSON preflight should still win when the sibling text file is blank.",
        },
        primary_summary="Phase 7 current paper run 2026-05-21T18:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        shadow_summary="Phase 8 shadow run 2026-05-21T18:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
    )
    write_text(blank_text_json_preflight_run / "preflight_note.txt", "\n")

    blank_text_no_targets_root, blank_text_no_targets_run = setup_case(
        case_name="case_blank_text_no_targets_preflight",
        run_date="2026-05-23",
        preflight_note="Blank-text JSON fallback note: no active OP/CD cards today; KEE is shadow-only.",
        preflight_json={
            "date": "2026-05-23",
            "checked_at": "2026-05-23 12:00",
            "api_ok": True,
            "calendar_state": "NO TARGETS",
            "calendar_reason": "no_targets",
            "has_targets": False,
            "relevant_tracks": [],
            "shadow_tracks": ["KEE"],
            "excluded_tracks": ["BAQ"],
            "excluded_track_count": 1,
            "total_cards": 18,
            "error": None,
            "note": "Blank-text JSON fallback note: no active OP/CD cards today; KEE is shadow-only.",
        },
        primary_summary="Phase 7 current paper run 2026-05-23T18:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        shadow_summary="Phase 8 shadow run 2026-05-23T18:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
    )
    write_text(blank_text_no_targets_run / "preflight_note.txt", "\n")

    json_only_no_targets_root, json_only_no_targets_run = setup_case(
        case_name="case_json_only_no_targets_preflight",
        run_date="2026-05-20",
        preflight_note="JSON-only preflight note: no active OP/CD cards today; KEE is shadow-only.",
        preflight_json={
            "date": "2026-05-20",
            "checked_at": "2026-05-20 12:00",
            "api_ok": True,
            "calendar_state": "NO TARGETS",
            "calendar_reason": "no_targets",
            "has_targets": False,
            "relevant_tracks": [],
            "shadow_tracks": ["KEE"],
            "total_cards": 18,
            "error": None,
            "note": "JSON-only preflight note: no active OP/CD cards today; KEE is shadow-only.",
        },
        primary_summary="Phase 7 current paper run 2026-05-20T18:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        shadow_summary="Phase 8 shadow run 2026-05-20T18:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
    )
    (json_only_no_targets_run / "preflight_note.txt").unlink()

    markdown_only_next_steps_root, markdown_only_next_steps_run = setup_case(
        case_name="case_markdown_only_next_steps",
        run_date="2026-05-24",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP.",
        primary_summary="Phase 7 current paper run 2026-05-24T18:40:00: text next-steps artifact missing but markdown next-steps artifact is available",
        shadow_summary="Phase 8 shadow run 2026-05-24T18:40:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        primary_next_steps_text="Phase 7 current paper lane next steps\n- State: NEEDS SETTLEMENT\n- Settled races: 1 | open races: 1 | open settlement rows: 1 | settled rows missing outcome: 0\n- ROI coverage: 1/1 settled races have return values (0 still missing return/cost coverage)\n- First statistical-read progress: 1/30 settled (29 more needed)\n- Broader portfolio-review progress: 1/100 settled (99 more needed)\n- Why: Markdown-only fixture proves the daily summary can rebuild from next_steps.md when next_steps.txt is absent instead of dropping lane readiness context.",
    )
    write_text(
        markdown_only_next_steps_run / "phase7_current_paper" / "next_steps.md",
        "Phase 7 current paper lane next steps\n- State: NEEDS SETTLEMENT\n- Settled races: 1 | open races: 1 | open settlement rows: 1 | settled rows missing outcome: 0\n- ROI coverage: 1/1 settled races have return values (0 still missing return/cost coverage)\n- First statistical-read progress: 1/30 settled (29 more needed)\n- Broader portfolio-review progress: 1/100 settled (99 more needed)\n- Why: Markdown-only fixture proves the daily summary can rebuild from next_steps.md when next_steps.txt is absent instead of dropping lane readiness context.\n",
    )
    (markdown_only_next_steps_run / "phase7_current_paper" / "next_steps.txt").unlink()

    blank_text_next_steps_root, blank_text_next_steps_run = setup_case(
        case_name="case_blank_text_next_steps",
        run_date="2026-05-26",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP.",
        primary_summary="Phase 7 current paper run 2026-05-26T18:45:00: text next-steps artifact blank but markdown next-steps artifact is available",
        shadow_summary="Phase 8 shadow run 2026-05-26T18:45:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        primary_next_steps_text="Placeholder that will be replaced by a blank text mirror after setup.",
    )
    write_text(
        blank_text_next_steps_run / "phase7_current_paper" / "next_steps.md",
        'Phase 7 current paper lane next steps\n- State: NEEDS SETTLEMENT\n- Settled races: 2 | open races: 1 | open settlement rows: 1 | settled rows missing outcome: 0\n- ROI coverage: 2/2 settled races have return values (0 still missing return/cost coverage)\n- First statistical-read progress: 2/30 settled (28 more needed)\n- Broader portfolio-review progress: 2/100 settled (98 more needed)\n- Why: Blank-text fixture proves the daily summary can rebuild from next_steps.md when next_steps.txt exists but has no readable content instead of dropping lane readiness context.\n',
    )
    write_text(blank_text_next_steps_run / "phase7_current_paper" / "next_steps.txt", "\n")

    malformed_next_steps_root, malformed_next_steps_run = setup_case(
        case_name="case_missing_next_step_fields",
        run_date="2026-05-22",
        preflight_note="Preflight context: primary paper-basket target tracks racing today: OP, CD.",
        primary_summary="Phase 7 current paper run 2026-05-22T18:15:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        shadow_summary="Phase 8 shadow run 2026-05-22T18:15:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        primary_next_steps_text="Phase 7 current paper lane next steps",
    )

    fixture_results = [
        run_case(
            "case_empty_no_targets",
            empty_root,
            empty_run,
            [
                "Quick jump index:",
                f"- Right now: {empty_root.relative_to(BASE) / 'PAPER_TRADE_NOW.md'}",
                f"- Rolling ops history: {empty_root.relative_to(BASE) / 'OPS_HISTORY.md'}",
                f"- Primary summary: {empty_run.relative_to(BASE) / 'phase7_current_paper/summary.txt'}",
                f"- Shadow summary: {empty_run.relative_to(BASE) / 'phase8_shadow/summary.txt'}",
                "Current live hierarchy:",
                "`OP_DURABLE_K7` remains the anchor; `CD_CORE_K8` remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion.",
                "`OP_REFINED_K7` remains the lead same-family challenger; the rest of Phase 8 stays research/watch only until it earns more forward evidence.",
                "BAQ (not treated as BEL): never substitute BAQ for the dormant BEL rule or count BAQ as BEL forward evidence.",
                "- Shadow settlement-audit promotion gate: Shadow/watch phase8_promotion_review gate is per-rule",
                "- Shadow per-rule promotion coverage: OP_REFINED_K7 (WATCH) 0/20 (0.0%); AQU_K9 (SKIP) 0/20 (0.0%)",
                "- Primary next-step state: WAITING FOR FIRST SETTLED RACES",
                "- Primary lane why now: No primary races are settled yet. The first statistical read is still 0/30 and the broader portfolio-review gate is 0/100, so keep the OP/CD observation loop running instead of over-reading empty forward metrics.",
                "- Primary readiness: first read 0/30 settled (30 more needed) | broader review 0/100 settled (100 more needed)",
                "- Shadow next-step state: WAITING FOR FIRST SETTLED RACES",
                "- Shadow lane why now: No shadow races are settled yet. The first statistical read is still 0/20 and the broader portfolio-review gate is 0/100, so keep Phase 8 in watch mode instead of promotion/readiness language.",
                "- Shadow readiness: first read 0/20 settled (20 more needed) | broader review 0/100 settled (100 more needed)",
                "PRIMARY: Phase 7 current paper basket (OP + CD rule components; target cards require preflight)",
                "SHADOW: Phase 8 watch-list basket",
                "clean empty run, 0 scanner hit(s), 0 recommendation(s)",
                f"Artifacts root: {empty_run.relative_to(BASE)}",
            ],
            scenario="empty no-target day",
        ),
        run_case(
            "case_settlement_pending",
            pending_root,
            pending_run,
            [
                "primary paper-basket target tracks racing today: OP, CD.",
                "2 pending settlement row(s)",
                "- Primary next-step state: NEEDS SETTLEMENT",
                "- Primary readiness: first read 0/30 settled (30 more needed) | broader review 0/100 settled (100 more needed)",
                f"- Primary summary: {pending_run.relative_to(BASE) / 'phase7_current_paper/summary.txt'}",
                f"- Primary next steps: {pending_run.relative_to(BASE) / 'phase7_current_paper/next_steps.md'}",
                f"Artifacts root: {pending_run.relative_to(BASE)}",
            ],
            scenario="settlement-pending active day",
        ),
        run_case(
            "case_incomplete_settlement_gap",
            incomplete_root,
            incomplete_run,
            [
                "primary paper-basket target tracks racing today: OP.",
                "settlement cleanup pending, 1 row marked settled without an outcome",
                "- Primary next-step state: NEEDS SETTLEMENT",
                "- Primary settlement integrity: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 1",
                f"Artifacts root: {incomplete_run.relative_to(BASE)}",
            ],
            scenario="incomplete settled rows stay visible in the combined daily summary",
        ),
        run_case(
            "case_partial_roi_coverage_gap",
            partial_roi_root,
            partial_roi_run,
            [
                "collecting sample, 5 settled races but only partial return coverage so ROI remains incomplete",
                "- Primary next-step state: COLLECTING SAMPLE",
                "- Primary decision gate: No strategy change: 5 settled race(s) is below the first statistical-read gate of 30.",
                "- Shadow decision gate: No strategy change: this is still pre-evidence with 0 settled races.",
                "- Primary settlement integrity: 5 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0",
                "- Primary ROI coverage: 2/5 settled races have return values (3 still missing return/cost coverage)",
                "- Primary ROI coverage gaps: 3 (missing actual_return: 3)",
                "- Primary settlement-audit action: repair_roi_coverage — Primary fixture has 3 settled rows missing usable ROI coverage; repair actual_return before reading ROI.",
                f"Artifacts root: {partial_roi_run.relative_to(BASE)}",
            ],
            scenario="partial ROI coverage stays visible in the combined daily summary",
        ),
        run_case(
            "case_active_target",
            active_root,
            active_run,
            [
                "primary paper-basket target tracks racing today: OP.",
                "bets ready, 1 BET recommendation(s)",
                "signals logged, no BET recommendation(s)",
                "- Primary readiness: first read 0/30 settled (30 more needed) | broader review 0/100 settled (100 more needed)",
                "- Shadow next-step state: COLLECTING SAMPLE",
                "- Shadow readiness: first read 5/20 settled (15 more needed) | broader review 5/100 settled (95 more needed)",
                "- Shadow ROI coverage: 3/5 settled races have return values (2 still missing return/cost coverage)",
                "- Shadow ROI coverage gaps: 2 (malformed actual_cost: 1; missing actual_return: 1)",
                f"- Primary summary: {active_run.relative_to(BASE) / 'phase7_current_paper/summary.txt'}",
                f"- Shadow summary: {active_run.relative_to(BASE) / 'phase8_shadow/summary.txt'}",
                f"- Shadow lane monitor: {active_run.relative_to(BASE) / 'phase8_shadow/lane_monitor.md'}",
            ],
            scenario="active-target / bets-ready day",
        ),
        run_case(
            "case_pipeline_recorded_empty_scanner_missing",
            pipeline_recorded_empty_root,
            pipeline_recorded_empty_run,
            [
                "scanner sidecar recorded empty, 0 scanner hit(s), 0 recommendation(s), current scanner sidecar file missing, pipeline recorded scanner-status state empty",
                "- Primary next-step state: REFRESH RUN ARTIFACTS",
                "- Primary lane context: Latest run context: the latest lane run preserved a pipeline-recorded scanner-status state: empty. The current copied scanner sidecar file is missing, so keep this as an operational status issue.",
                f"- Primary summary: {pipeline_recorded_empty_run.relative_to(BASE) / 'phase7_current_paper/summary.txt'}",
                f"Artifacts root: {pipeline_recorded_empty_run.relative_to(BASE)}",
            ],
            scenario="combined daily summary keeps a pipeline-recorded empty scanner-status issue visible when the copied primary scanner sidecar is missing",
        ),
        run_case(
            "case_pipeline_recorded_unreadable_scanner_missing",
            pipeline_recorded_unreadable_root,
            pipeline_recorded_unreadable_run,
            [
                "scanner sidecar recorded unreadable, 0 scanner hit(s), 0 recommendation(s), current scanner sidecar file missing, pipeline recorded scanner-status state unreadable",
                "- Primary next-step state: REFRESH RUN ARTIFACTS",
                "- Primary lane context: Latest run context: the latest lane run preserved a pipeline-recorded scanner-status state: unreadable. The current copied scanner sidecar file is missing, so keep this as an operational status issue.",
                f"- Primary summary: {pipeline_recorded_unreadable_run.relative_to(BASE) / 'phase7_current_paper/summary.txt'}",
                f"Artifacts root: {pipeline_recorded_unreadable_run.relative_to(BASE)}",
            ],
            scenario="combined daily summary keeps a pipeline-recorded unreadable scanner-status issue visible when the copied primary scanner sidecar is missing",
        ),
        run_case(
            "case_pipeline_recorded_invalid_shape_scanner_missing",
            pipeline_recorded_invalid_shape_root,
            pipeline_recorded_invalid_shape_run,
            [
                "scanner sidecar recorded invalid shape, 1 scanner hit(s), 1 recommendation(s), scanner-status error: expected scanner-status JSON object, got list, current scanner sidecar file missing, pipeline recorded scanner-status state invalid_shape",
                "- Primary next-step state: REFRESH RUN ARTIFACTS",
                "- Primary lane context: Latest run context: the latest lane run preserved a pipeline-recorded scanner-status state: invalid-shape. The current copied scanner sidecar file is missing, so keep this as an operational status issue.",
                "recorded invalid-shape by the pipeline",
                f"- Primary summary: {pipeline_recorded_invalid_shape_run.relative_to(BASE) / 'phase7_current_paper/summary.txt'}",
                f"Artifacts root: {pipeline_recorded_invalid_shape_run.relative_to(BASE)}",
            ],
            scenario="combined daily summary keeps a pipeline-recorded invalid-shape scanner-status issue visible when the copied primary scanner sidecar is missing",
        ),
        run_case(
            "case_missing_scan_output_context",
            missing_scan_output_root,
            missing_scan_output_run,
            [
                "missing scanner output, 0 scanner hit(s), 0 recommendation(s); scanner-status reported no_qualifiers; safe empty scan fallback missing_or_empty_scan_output; scan input was missing before fallback",
                "- Current operator focus: Refresh the daily wrapper, primary lane scan-output artifact is missing",
                "- Current ops bucket: ISSUE, MISSING SCAN OUTPUT",
                "- Primary next-step state: REFRESH RUN ARTIFACTS",
                "- Primary lane why now: The latest lane scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers; the pipeline used a safe empty [] fallback. Treat this as an artifact issue, not a clean no-qualifier observation. Refresh the daily wrapper before treating this lane as empty.",
                "- Primary lane context: Latest run context: scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers; the pipeline used a safe empty [] fallback. Treat this as an artifact issue, not a clean no-qualifier observation.",
                f"- Primary summary: {missing_scan_output_run.relative_to(BASE) / 'phase7_current_paper/summary.txt'}",
                f"Artifacts root: {missing_scan_output_run.relative_to(BASE)}",
            ],
            scenario="combined daily summary keeps missing scan-output fallback context visible across top-card, lane-summary, and next-step sections",
        ),
        run_case(
            "case_api_access_stale_cache_fallback_context",
            api_access_stale_cache_root,
            api_access_stale_cache_run,
            [
                "scanner API access failure, 0 scanner hit(s), 0 recommendation(s), HTTP 403, API-access-failure operator context only",
                "- Current operator focus: Refresh the daily wrapper, primary lane scanner hit an API-access stale-cache fallback",
                "- Current ops bucket: ISSUE, API ACCESS STALE CACHE FALLBACK",
                "- Current operator read-gate issue flags: has_api_access_failure_context=true; has_scanner_failure_boundary=true; has_stale_cache_fallback_context=true",
                "- Primary next-step state: CHECK SCANNER FAILURE",
                "- Primary lane why now: Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence. stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx.",
                "- Primary lane context: Latest run context: scanner failed before producing signals. Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence. stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx.",
                "- Primary sidecar action: refresh_daily_wrapper_before_evidence_read.",
                "- Primary recheck command: ./run_daily_portfolio_observation.sh.",
                f"- Primary summary: {api_access_stale_cache_run.relative_to(BASE) / 'phase7_current_paper/summary.txt'}",
                f"Artifacts root: {api_access_stale_cache_run.relative_to(BASE)}",
            ],
            scenario="combined daily summary keeps API-access stale-cache fallback context visible across top-card, lane-summary, and next-step sections",
        ),
        run_case(
            "case_malformed_settlement_audit_json",
            malformed_settlement_audit_root,
            malformed_settlement_audit_run,
            [
                "settlement audit sidecar is malformed; refresh audit before reading next actions",
                f"- Primary settlement-audit action: [malformed settlement-audit JSON: {malformed_settlement_audit_root.relative_to(BASE) / 'out/paper_trade_settlement_audit.json'}",
                f"- Shadow settlement-audit action: [malformed settlement-audit JSON: {malformed_settlement_audit_root.relative_to(BASE) / 'out/paper_trade_settlement_audit.json'}",
                f"Artifacts root: {malformed_settlement_audit_run.relative_to(BASE)}",
            ],
            scenario="malformed settlement-audit JSON sidecar stays explicit instead of looking like a missing audit",
        ),
        run_case(
            "case_invalid_shape_settlement_audit_json",
            invalid_shape_settlement_audit_root,
            invalid_shape_settlement_audit_run,
            [
                "settlement audit sidecar has invalid shape; refresh audit before reading next actions",
                f"- Primary settlement-audit action: [invalid-shape settlement-audit JSON: {invalid_shape_settlement_audit_root.relative_to(BASE) / 'out/paper_trade_settlement_audit.json'} expected object, got list]",
                f"- Shadow settlement-audit action: [invalid-shape settlement-audit JSON: {invalid_shape_settlement_audit_root.relative_to(BASE) / 'out/paper_trade_settlement_audit.json'} expected object, got list]",
                f"Artifacts root: {invalid_shape_settlement_audit_run.relative_to(BASE)}",
            ],
            scenario="invalid-shape settlement-audit JSON sidecar stays explicit instead of looking like a missing audit",
        ),
        run_case(
            "case_missing_settlement_audit_lanes_list",
            missing_lanes_settlement_audit_root,
            missing_lanes_settlement_audit_run,
            [
                "settlement audit sidecar is missing the lanes list; refresh audit before reading next actions",
                f"- Primary settlement-audit action: [missing settlement-audit lanes list: {missing_lanes_settlement_audit_root.relative_to(BASE) / 'out/paper_trade_settlement_audit.json'}]",
                f"- Shadow settlement-audit action: [missing settlement-audit lanes list: {missing_lanes_settlement_audit_root.relative_to(BASE) / 'out/paper_trade_settlement_audit.json'}]",
                f"Artifacts root: {missing_lanes_settlement_audit_run.relative_to(BASE)}",
            ],
            scenario="missing settlement-audit lanes list stays explicit instead of looking like a missing audit",
        ),
        run_case(
            "case_stale_right_now_snapshot",
            stale_right_now_root,
            stale_right_now_run,
            [
                "primary paper-basket target tracks racing today: CD.",
                "- Current operator focus: Refresh the daily wrapper, latest operator card is stale",
                "- Current run freshness: Latest run date 2026-05-21 is 2 day(s) behind the as-of date 2026-05-23, so the saved top card is stale until the daily wrapper is rerun.",
                "- Current stale snapshot note: The preflight note/artifact, excluded-track aliases, lane context, current-state counts, ops streaks, and quick reads below are inherited from the latest saved run (2026-05-21) and should be treated as stale snapshot context until the daily wrapper is rerun.",
                "- Current ops bucket: ACTIVE, ZERO HITS",
                f"Artifacts root: {stale_right_now_run.relative_to(BASE)}",
            ],
            scenario="daily summary preserves the routed stale-run warning from the top card instead of only the generic focus line",
        ),
        run_case(
            "case_recommender_failure_context",
            recommender_failure_root,
            recommender_failure_run,
            [
                "primary paper-basket target tracks racing today: OP, CD.",
                "recommender failure, 1 scanner hit(s), 0 recommendation(s), last completed stage scanner, stage recommender, scanner hits before failure 1, RuntimeError, detail: fixture recommender crash",
                "- Primary next-step state: CHECK PIPELINE FAILURE",
                "- Primary lane context: Latest run context: the latest lane run ended in recommender failure. Last completed stage: scanner. Stage: recommender. Scanner hits before failure: 1. Error type: RuntimeError. Detail: fixture recommender crash",
                "- Primary readiness: first read 0/30 settled (30 more needed) | broader review 0/100 settled (100 more needed)",
                f"- Primary summary: {recommender_failure_run.relative_to(BASE) / 'phase7_current_paper/summary.txt'}",
                f"- Primary next steps: {recommender_failure_run.relative_to(BASE) / 'phase7_current_paper/next_steps.md'}",
                f"Artifacts root: {recommender_failure_run.relative_to(BASE)}",
            ],
            scenario="active-target recommender-stage pipeline failure stays explicit in the combined daily summary",
        ),
        run_case(
            "case_logger_failure_context",
            logger_failure_root,
            logger_failure_run,
            [
                "primary paper-basket target tracks racing today: OP, CD.",
                "logger failure, 1 scanner hit(s), 1 recommendation(s), 1 BET, last completed stage recommender, stage logger, recommendations built before failure 1, BET recommendations before failure 1, pre-error context bets_ready, ValueError, detail: fixture logger crash",
                "signals logged, no BET recommendation(s)",
                "- Primary next-step state: CHECK PIPELINE FAILURE",
                "- Primary lane context: Latest run context: the latest lane run ended in logger failure. Last completed stage: recommender. Stage: logger. Recommendations built before failure: 1. BET recommendations before failure: 1. Pre-error lane context: bets_ready. Error type: ValueError. Detail: fixture logger crash",
                "- Shadow readiness: first read 0/20 settled (20 more needed) | broader review 0/100 settled (100 more needed)",
                f"- Primary summary: {logger_failure_run.relative_to(BASE) / 'phase7_current_paper/summary.txt'}",
                f"Artifacts root: {logger_failure_run.relative_to(BASE)}",
            ],
            scenario="active-target logger-stage pipeline failure stays explicit in the combined daily summary",
        ),
        run_case(
            "case_missing_shadow_summary",
            missing_shadow_root,
            missing_shadow_run,
            [
                "primary paper-basket target tracks racing today: OP, CD.",
                "- Shadow next-step state: DECISION-GRADE REVIEW",
                "- Shadow readiness: first read 20/20 settled (threshold reached) | broader review 20/100 settled (80 more needed)",
                "clean empty run, 0 scanner hit(s), 0 recommendation(s)",
                f"- Shadow summary: {missing_shadow_run.relative_to(BASE) / 'phase8_shadow/summary.txt'}",
                f"[missing shadow summary: {missing_shadow_run.relative_to(BASE) / 'phase8_shadow/summary.txt'}]",
                f"Artifacts root: {missing_shadow_run.relative_to(BASE)}",
            ],
            scenario="missing shadow summary degrades to explicit placeholder",
        ),
        run_case(
            "case_missing_preflight_note",
            missing_preflight_root,
            missing_preflight_run,
            [
                f"- Preflight note: {missing_preflight_run.relative_to(BASE) / 'preflight_note.txt'}",
                f"[missing preflight note: {missing_preflight_run.relative_to(BASE) / 'preflight_note.txt'}]",
                "- Primary readiness: first read 0/30 settled (30 more needed) | broader review 0/100 settled (100 more needed)",
                "- Shadow readiness: first read 5/20 settled (15 more needed) | broader review 5/100 settled (95 more needed)",
                "clean empty run, 0 scanner hit(s), 0 recommendation(s)",
                f"Artifacts root: {missing_preflight_run.relative_to(BASE)}",
            ],
            scenario="missing preflight note degrades to explicit placeholder",
        ),
        run_case(
            "case_json_only_preflight_note",
            json_only_preflight_root,
            json_only_preflight_run,
            [
                f"- Preflight note: {json_only_preflight_run.relative_to(BASE) / 'preflight_note.json'}",
                "JSON-only preflight note: OP is active today even though the text surface is missing.",
                "- Primary readiness: first read 0/30 settled (30 more needed) | broader review 0/100 settled (100 more needed)",
                f"Artifacts root: {json_only_preflight_run.relative_to(BASE)}",
            ],
            scenario="daily summary falls back to the saved preflight JSON on an active-target day when the sibling text surface is missing",
        ),
        run_case(
            "case_blank_text_prefers_json_preflight_note",
            blank_text_json_preflight_root,
            blank_text_json_preflight_run,
            [
                f"- Preflight note: {blank_text_json_preflight_run.relative_to(BASE) / 'preflight_note.json'}",
                "JSON preflight should still win when the sibling text file is blank.",
                "- Primary readiness: first read 0/30 settled (30 more needed) | broader review 0/100 settled (100 more needed)",
                f"Artifacts root: {blank_text_json_preflight_run.relative_to(BASE)}",
            ],
            scenario="daily summary still prefers the saved preflight JSON when the sibling text surface exists but is blank on an active-target day",
        ),
        run_case(
            "case_blank_text_no_targets_preflight",
            blank_text_no_targets_root,
            blank_text_no_targets_run,
            [
                f"- Preflight note: {blank_text_no_targets_run.relative_to(BASE) / 'preflight_note.json'}",
                "Blank-text JSON fallback note: no active OP/CD cards today; KEE is shadow-only.",
                "Excluded track aliases: BAQ (not treated as BEL)",
                "- Primary readiness: first read 0/30 settled (30 more needed) | broader review 0/100 settled (100 more needed)",
                f"Artifacts root: {blank_text_no_targets_run.relative_to(BASE)}",
            ],
            scenario="daily summary still prefers the saved preflight JSON when the sibling text surface exists but is blank on a no-target day",
        ),
        run_case(
            "case_json_only_no_targets_preflight",
            json_only_no_targets_root,
            json_only_no_targets_run,
            [
                f"- Preflight note: {json_only_no_targets_run.relative_to(BASE) / 'preflight_note.json'}",
                "JSON-only preflight note: no active OP/CD cards today; KEE is shadow-only.",
                "- Primary readiness: first read 0/30 settled (30 more needed) | broader review 0/100 settled (100 more needed)",
                f"Artifacts root: {json_only_no_targets_run.relative_to(BASE)}",
            ],
            scenario="daily summary falls back to the saved preflight JSON on a no-target day when the sibling text surface is missing",
        ),
        run_case(
            "case_markdown_only_next_steps",
            markdown_only_next_steps_root,
            markdown_only_next_steps_run,
            [
                "text next-steps artifact missing but markdown next-steps artifact is available",
                "- Primary next steps: out/status_validation/daily_summary_fixture/case_markdown_only_next_steps/out/daily_portfolio_runs/2026-05-24/phase7_current_paper/next_steps.md",
                "- Primary next-step source artifact: out/status_validation/daily_summary_fixture/case_markdown_only_next_steps/out/daily_portfolio_runs/2026-05-24/phase7_current_paper/next_steps.md",
                "- Primary next-step state: NEEDS SETTLEMENT",
                "- Primary lane why now: Markdown-only fixture proves the daily summary can rebuild from next_steps.md when next_steps.txt is absent instead of dropping lane readiness context.",
                "- Primary readiness: first read 1/30 settled (29 more needed) | broader review 1/100 settled (99 more needed)",
                "- Primary settlement integrity: 1 | open races: 1 | open settlement rows: 1 | settled rows missing outcome: 0",
                "- Primary ROI coverage: 1/1 settled races have return values (0 still missing return/cost coverage)",
                f"Artifacts root: {markdown_only_next_steps_run.relative_to(BASE)}",
            ],
            scenario="markdown-only next-steps source keeps state/readiness/ROI context visible when the text mirror is missing",
        ),
        run_case(
            "case_blank_text_next_steps",
            blank_text_next_steps_root,
            blank_text_next_steps_run,
            [
                "text next-steps artifact blank but markdown next-steps artifact is available",
                "- Primary next steps: out/status_validation/daily_summary_fixture/case_blank_text_next_steps/out/daily_portfolio_runs/2026-05-26/phase7_current_paper/next_steps.md",
                "- Primary next-step source artifact: out/status_validation/daily_summary_fixture/case_blank_text_next_steps/out/daily_portfolio_runs/2026-05-26/phase7_current_paper/next_steps.md",
                "- Primary next-step state: NEEDS SETTLEMENT",
                "- Primary lane why now: Blank-text fixture proves the daily summary can rebuild from next_steps.md when next_steps.txt exists but has no readable content instead of dropping lane readiness context.",
                "- Primary readiness: first read 2/30 settled (28 more needed) | broader review 2/100 settled (98 more needed)",
                "- Primary settlement integrity: 2 | open races: 1 | open settlement rows: 1 | settled rows missing outcome: 0",
                "- Primary ROI coverage: 2/2 settled races have return values (0 still missing return/cost coverage)",
                f"Artifacts root: {blank_text_next_steps_run.relative_to(BASE)}",
            ],
            scenario="markdown-only next-steps source also keeps state/readiness/ROI context visible when the text mirror exists but is blank",
        ),
        run_case(
            "case_missing_next_step_fields",
            malformed_next_steps_root,
            malformed_next_steps_run,
            [
                "- Primary next-step state: [missing primary next-steps state: out/status_validation/daily_summary_fixture/case_missing_next_step_fields/out/daily_portfolio_runs/2026-05-22/phase7_current_paper/next_steps.txt]",
                "- Primary readiness: first read [missing primary first-read progress: out/status_validation/daily_summary_fixture/case_missing_next_step_fields/out/daily_portfolio_runs/2026-05-22/phase7_current_paper/next_steps.txt] | broader review [missing primary portfolio-review progress: out/status_validation/daily_summary_fixture/case_missing_next_step_fields/out/daily_portfolio_runs/2026-05-22/phase7_current_paper/next_steps.txt]",
                "- Primary settlement integrity: [missing primary settlement integrity: out/status_validation/daily_summary_fixture/case_missing_next_step_fields/out/daily_portfolio_runs/2026-05-22/phase7_current_paper/next_steps.txt]",
                "- Primary ROI coverage: [missing primary ROI coverage: out/status_validation/daily_summary_fixture/case_missing_next_step_fields/out/daily_portfolio_runs/2026-05-22/phase7_current_paper/next_steps.txt]",
                "- Shadow next-step state: WAITING FOR FIRST SETTLED RACES",
                f"Artifacts root: {malformed_next_steps_run.relative_to(BASE)}",
            ],
            scenario="missing required next-steps labels degrade to explicit field placeholders instead of quietly dropping settlement or ROI integrity context from the combined summary",
        ),
    ]
    live_surfaces = validate_live_surfaces()
    live_api_access_action_route_checks = sum(
        1 for row in live_surfaces if row.get("api_access_action_route_confirmed")
    )
    if live_api_access_action_route_checks <= 0:
        raise AssertionError(
            "saved live daily summaries no longer include an API-access action/recheck route check"
        )
    results = fixture_results + live_surfaces
    scratch = build_fixture_scratch_metadata()

    report_md = OUT_MD
    report_json = OUT_JSON
    child_checks = scorecard_guardrails + [
        {
            "check": "fixture_bundle_and_snapshot_lines_stay_covered",
            "status": "pass",
            "detail": "fixture cases still pin the full routed quick-jump bundle including the settlement-audit quick read, routed right-now JSON pointer plus operator_read_gate read/status/refresh-command/issue-flag lines, settlement-audit next-action snapshot lines, the shadow settlement-audit per-rule promotion gate plus per-rule coverage line, routed right-now snapshot lines, preflight section, live hierarchy block, explicit next-step source artifact paths, lifted primary/shadow decision-gate snapshot lines, readiness lines, ROI-gap-reason lines plus why-now lines when next-steps surfaces provide them, lane sections, and artifacts-root pointer",
        },
        {
            "check": "saved_live_daily_summaries_match_current_rebuilds",
            "status": "pass",
            "detail": "saved live daily_summary.txt surfaces under out/daily_portfolio_runs still have to match the current source-layer rebuild instead of drifting behind helper changes, while preserving the absence of optional stale-snapshot-note lines on historical saved summaries that were created before the top card became stale and keeping API-access sidecar action plus wrapper recheck routing visible when generated lane context carries a 403 scanner failure",
        },
        {
            "check": "json_only_preflight_and_missing_artifacts_stay_explicit",
            "status": "pass",
            "detail": "missing preflight notes, json-only preflight fallback on both sides of the calendar split, blank-text preflight fallback to saved JSON on both sides of the calendar split, missing lane summaries, markdown-only next-steps fallback for missing or blank text mirrors, missing required next-steps labels, and missing settlement-audit JSON still stay explicit in the direct daily-summary helper layer",
        },
        {
            "check": "settlement_audit_json_malformed_invalid_shape_and_missing_lanes_stay_distinct",
            "status": "pass",
            "detail": "malformed, invalid-shape, and missing-lanes settlement-audit JSON sidecars now stay distinct from missing settlement-audit JSON in the combined daily summary, so operators know whether to rebuild a missing audit or repair a broken sidecar before reading next_action routing",
        },
        {
            "check": "pipeline_failure_and_readiness_context_stay_pinned",
            "status": "pass",
            "detail": "active-target recommender/logger pipeline-failure summaries, missing scan-output fallback context plus pipeline-recorded empty/unreadable/invalid-shape scanner-status issue lines from copied lane summaries, saved next-steps failure/status-context lines, primary 30-row versus shadow 20-row first-read gate visibility, broader-review readiness context, and settled-row ROI-gap reasons, markdown-only next-steps fallback for missing or blank text mirrors, and why-now lines stay explicit in the combined daily summary",
        },
        {
            "check": "api_access_stale_cache_fallback_context_stays_pinned",
            "status": "pass",
            "detail": "API-access scanner failures that complete from stale cache keep HTTP status, stale-cache fallback count/kind/error detail, true operator_read_gate issue flags, action/recheck routing, and the no-evidence boundary visible in the combined daily summary",
        },
        {
            "check": "daily_summary_explicitly_stays_workflow_not_new_evidence",
            "status": "pass",
            "detail": "the direct validator summary still says plainly that the combined daily summary is a workflow/navigation surface, not a profit-proof or CI-backed forward-validation report, and that forward-performance claims stay pending until settled paper trades have usable return/cost coverage",
        },
        {
            "check": "source_daily_summary_output_publishes_evidence_boundary_fields",
            "status": "pass",
            "detail": "fixture and saved-live daily_summary.txt outputs now publish exact source-level valid_evidence_scope=daily_operator_workflow_navigation_only lines plus evidence_boundary_text so combined quick jumps, inherited top-card snapshots, lane context, readiness lines, settlement-audit action routing, clean-empty/no-target routing, issue routing, and saved-live rebuild cleanliness are not overread as scanner evidence, live ledger evidence, settled ROI, promotion readiness, live profitability, real-money support, or BAQ-as-BEL evidence",
        },
        {
            "check": "direct_validation_report_exposes_daily_summary_valid_scope",
            "status": "pass",
            "detail": "the direct daily-summary validator report now exposes the raw valid_evidence_scope line and keeps green summary checks classified as workflow/navigation metadata only",
        },
        {
            "check": "daily_summary_preserves_scorecard_gate_boundary",
            "status": "pass",
            "detail": "the daily-summary validator now publishes the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite while saying combined quick jumps, inherited right-now snapshots, lane context, readiness lines, and validator cleanliness do not count toward those gates",
        },
        {
            "check": "fixture_scratch_metadata_published",
            "status": "pass",
            "detail": "the daily-summary validator JSON publishes project-local fixture scratch metadata so parent rollups can verify the isolated fixture root without parsing markdown prose",
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
        raise AssertionError("daily-summary scorecard gate boundary no longer matches forward_evidence_scorecard.json")
    if (
        scratch.get("fixture_root_relative") != "out/status_validation/daily_summary_fixture"
        or scratch.get("fixture_root_is_project_local") is not True
        or scratch.get("case_roots_cleared_by_setup_case") is not True
    ):
        raise AssertionError("daily-summary fixture scratch metadata no longer proves a project-local cleared fixture root")
    report_lines = [
        "# Paper-Trade Daily Summary Validation",
        "",
        "This report validates `paper_trade_daily_summary.py` against representative fixture cases under `out/status_validation/daily_summary_fixture/`, while publishing the direct validator readout under `out/status_validation/paper_trade_daily_summary/`.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        "",
        "## Fixture cases",
        "",
        "| Case | Scenario | Output |",
        "|---|---|---|",
        *[f"| `{row['case']}` | {row['scenario']} | `{row['output']}` |" for row in fixture_results],
        "",
        "## Live current surfaces",
        "",
        *[f"- `{row['run_root']}` -> `{row['output']}`" for row in live_surfaces],
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
        "- Boundary: daily-summary validator cleanliness is workflow/navigation metadata only, not new forward evidence, not a live paper-trade ledger, not a current-day scanner result, not settled ROI, not live profitability, not promotion readiness, and not real-money evidence.",
        "- Non-goals: do not treat combined quick jumps, inherited top-card snapshots, lane context, readiness lines, clean-empty/no-target routing, or green validators as ROI-complete observations, profitability evidence, promotion support, or real-money support.",
        "",
        "## Source Output Boundary",
        "",
        f"- Source scope line: `valid_evidence_scope={ptds.DAILY_SUMMARY_VALID_EVIDENCE_SCOPE}`.",
        f"- Boundary: {ptds.DAILY_SUMMARY_EVIDENCE_BOUNDARY_TEXT}",
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
        "- Fixture root: `out/status_validation/daily_summary_fixture/`",
        "- Direct validator report path: `out/status_validation/paper_trade_daily_summary/`",
        "- All fixture cases preserved the full routed quick-jump bundle including the settlement-audit quick read, routed right-now JSON pointer plus operator_read_gate read/status/refresh-command/issue-flag lines, direct primary/shadow settlement-audit next-action lines, the shadow settlement-audit per-rule promotion gate plus per-rule coverage line, explicit routed right-now focus/timing/freshness/stale-snapshot/ops snapshot lines, preflight note section, current live hierarchy block, explicit next-step source artifact paths, lifted primary/shadow decision-gate snapshot lines, explicit primary/shadow readiness lines, settled-row ROI-gap-reason lines plus why-now lines when next-steps surfaces provide them, markdown-only next-steps fallback when the text mirror is missing or blank, lane sections, artifacts-root line, and explicit missing-field placeholders when required next-steps labels drift.",
        "- The validator now also fails if any saved real `daily_summary.txt` under `out/daily_portfolio_runs/` drifts from the current source-layer rebuild.",
        f"- Saved live daily summaries with API-access / HTTP 403 lane context must also preserve `{API_ACCESS_ACTION_TEXT}` and `{API_ACCESS_RECHECK_TEXT}` in generated text; current saved-live route checks: {live_api_access_action_route_checks}.",
        "- Every fixture case now fails if that routed quick-jump bundle stops pointing at the case's routed `PAPER_TRADE_NOW.md`, sibling `PAPER_TRADE_NOW.json`, `OPS_HISTORY.md`, or settlement-audit artifact, and the combined summary now also fails if it drops the routed top-card focus/timing/freshness/stale-snapshot/ops snapshot extracted from that case-local `PAPER_TRADE_NOW.md`, the operator_read_gate extracted from sibling JSON, or the concrete next-step source artifact paths used for state/readiness extraction.",
        "- The routed quick-jump bundle still includes the direct settlement-audit artifact plus direct links to the primary and shadow `summary.txt` artifacts, not just their downstream detail files; the live hierarchy block now also lifts settlement-audit `next_action` / `next_action_reason` guidance plus the shadow per-rule promotion gate from the adjacent audit JSON while preserving the no-new-forward-evidence boundary.",
        "- Missing preflight notes, plus json-only preflight fallback on both active-target and no-target days, blank-text preflight fallback to saved JSON on both active-target and no-target days, markdown-only next-steps fallback for missing or blank text mirrors, missing lane summaries, and missing settlement-audit JSON now stay explicit at the direct helper layer too, instead of being left implicit behind only the wrapper-level fallback coverage.",
        "- Malformed, invalid-shape, and missing-lanes settlement-audit JSON sidecars now stay distinct from missing settlement-audit JSON in the combined daily summary, so operators know whether to rebuild a missing audit or repair a broken sidecar before reading next_action routing.",
        "- Structured preflight excluded-track aliases from `preflight_note.json` now stay visible in the combined summary too, so `BAQ (not treated as BEL)` cannot disappear downstream when the text note is missing or blank.",
        "- Active-target recommender/logger pipeline-failure summaries, missing scan-output fallback context, API-access stale-cache fallback context with true operator-read-gate issue flags, pipeline-recorded empty/unreadable/invalid-shape scanner-status issue lines, saved primary next-steps failure/status-context lines, primary 30-row versus shadow 20-row first-read gate visibility, broader-review readiness context, and settled-row ROI-gap reasons are now pinned directly here too, so the combined daily surface cannot quietly flatten those branches while lower-level validators stay green.",
        "- The rendered summary now also says plainly that it is a workflow/navigation surface driven by current run artifacts plus frozen hierarchy, not a profit-proof or CI-backed forward-validation report, and that forward-performance claims remain pending until settled paper trades have usable return/cost coverage.",
        "- Each fixture output is still checked against a fresh in-memory rebuild from `paper_trade_daily_summary.py`, not only against selected strings.",
        "- This keeps the combined daily summary surface reproducible across empty, settlement-pending, partial ROI coverage with explicit gap reasons, active-target, missing scan-output fallback, API-access stale-cache fallback, pipeline-recorded empty/unreadable/invalid-shape scanner-status issue, explicit pipeline-failure, malformed/invalid-shape/missing-lanes settlement-audit JSON, markdown-only next-steps, missing-lane-summary, missing-preflight, blank-text-with-json-preflight on both sides of the calendar split, and json-only-preflight days on both sides of the calendar split, while also pinning top-level recent-run failure/status context, lifted lane-summary decision-gate context, plus first-read vs broader-review readiness in the current live cold-start summary.",
        "- The validator JSON now also publishes fifteen explicit structured guardrails, so parent rollups can verify malformed-scorecard no-artifact failures, non-positive copied Phase 8 and real-money gate floor failures, saved-live rebuild parity, explicit missing/json-only fallback handling, malformed/invalid-shape/missing-lanes settlement-audit JSON separation, pinned missing scan-output/API-access stale-cache/scanner-status/failure/readiness context, the sibling top-card JSON operator_read_gate route including issue flags, the shadow per-rule promotion-gate line, the source-output evidence-boundary fields, direct valid_evidence_scope exposure, the workflow/not-new-evidence boundary, the scorecard-sourced gate boundary, and project-local fixture scratch metadata directly instead of inferring them only from totals plus prose.",
        "",
    ]
    payload = {
        "suite_status": "pass",
        "valid_evidence_scope": ptds.DAILY_SUMMARY_VALID_EVIDENCE_SCOPE,
        "total_fixture_scenarios": len(fixture_results),
        "total_checks": len(results),
        "check_count": len(results),
        "fixture_case_count": len(fixture_results),
        "live_surface_checks": len(live_surfaces),
        "live_api_access_action_route_checks": live_api_access_action_route_checks,
        "results": results,
        "child_check_count": len(child_checks),
        "child_checks": child_checks,
        "summary": {
            "suite_read": suite_read,
        },
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "scratch": scratch,
        "fixture_root": str(FIXTURE_ROOT.relative_to(BASE)),
        "report_path": str(OUT_DIR.relative_to(BASE)),
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }
    write_text(report_md, "\n".join(report_lines))
    write_text(report_json, json.dumps(payload, indent=2) + "\n")

    print(f"Wrote {report_md}")
    print(f"Wrote {report_json}")
    for row in results:
        print(f"PASS {row['case']}: {row['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
