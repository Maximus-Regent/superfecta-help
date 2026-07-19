#!/usr/bin/env python3
"""
Fixture-driven validation for paper_trade_lane_summary.py.

Purpose:
- keep the per-lane summary expansion reproducible
- validate representative empty, settlement-pending, and missing-detail cases
- confirm the helper preserves the operator-facing section layout
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

import paper_trade_lane_summary as ptls
import paper_trade_status_summary as ptds

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "paper_trade_lane_summary.py"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "lane_summary_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_lane_summary"
OUT_MD = OUT_DIR / "paper_trade_lane_summary_validation.md"
OUT_JSON = OUT_DIR / "paper_trade_lane_summary_validation.json"
TMP_PARENT = OUT_DIR / "_tmp"
LIVE_RUNS_ROOT = BASE / "out" / "daily_portfolio_runs"
REBUILD_COMMAND = "python3 validate_paper_trade_lane_summary.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
API_ACCESS_ACTION_TEXT = "Sidecar action: refresh_daily_wrapper_before_evidence_read"
API_ACCESS_RECHECK_TEXT = "Recheck command: ./run_daily_portfolio_observation.sh"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade lane-summary validator",
    "valid_evidence_scope": ptls.LANE_SUMMARY_VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "isolated lane-summary fixture lane folders",
        "saved live lane summary source-layer rebuilds",
        "paper_trade_lane_summary.py",
        "forward_evidence_scorecard.json decision_gate_minimums",
    ],
    "valid_use": "per-lane operator navigation/context validation for paper-trade run summaries",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "lane_summary_validator_passes_are_navigation_context_metadata_only": True,
    "non_goals": [
        "do not treat lane-summary cleanliness as ROI-complete observations",
        "do not treat lifted decision-gate or review-floor text as settled sample progress",
        "do not promote OP_REFINED_K7 or Phase 8 from lane-summary route visibility",
        "do not substitute BAQ for BEL",
        "do not treat lane-summary validation as real-money evidence",
    ],
}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, indent=2) + "\n")


def prepare_tmp_parent() -> Path:
    if TMP_PARENT.exists():
        shutil.rmtree(TMP_PARENT)
    TMP_PARENT.mkdir(parents=True, exist_ok=True)
    return TMP_PARENT


def setup_case(case_name: str, base_summary: str, forward_check: str | None, lane_monitor: str | None, next_steps: str | None) -> tuple[Path, dict[str, Path]]:
    case_root = FIXTURE_ROOT / case_name
    if case_root.exists():
        shutil.rmtree(case_root)
    lane_dir = case_root / "out" / "daily_portfolio_runs" / "2026-05-20" / "phase7_current_paper"
    paths = {
        "output": lane_dir / "summary.txt",
        "base": lane_dir / "summary_base.txt",
        "forward_text": lane_dir / "forward_check.txt",
        "forward_md": lane_dir / "forward_check.md",
        "monitor_text": lane_dir / "lane_monitor.txt",
        "monitor_md": lane_dir / "lane_monitor.md",
        "next_text": lane_dir / "next_steps.txt",
        "next_md": lane_dir / "next_steps.md",
        "settlement": case_root / "paper_trades" / "phase7_current_paper_paper_trade_settlements.csv",
    }

    write_text(paths["base"], base_summary + "\n")
    write_text(paths["forward_md"], f"md detail for {case_name}: forward\n")
    write_text(paths["monitor_md"], f"md detail for {case_name}: monitor\n")
    write_text(paths["next_md"], f"md detail for {case_name}: next\n")
    write_text(paths["settlement"], "signal_key,settlement_status\n")

    if forward_check is not None:
        write_text(paths["forward_text"], forward_check + "\n")
    if lane_monitor is not None:
        write_text(paths["monitor_text"], lane_monitor + "\n")
    if next_steps is not None:
        write_text(paths["next_text"], next_steps + "\n")

    return case_root, paths


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
            "lane-summary quick files, compact lane snapshots, lifted decision gates, "
            "Phase 8 review-floor cautions, pipeline-failure context, and green validator passes "
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
    global FIXTURE_ROOT, OUT_DIR, OUT_MD, OUT_JSON, TMP_PARENT
    FIXTURE_ROOT = fixture_root
    OUT_DIR = out_dir
    OUT_MD = OUT_DIR / "paper_trade_lane_summary_validation.md"
    OUT_JSON = OUT_DIR / "paper_trade_lane_summary_validation.json"
    TMP_PARENT = OUT_DIR / "_tmp"


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
            check_name="scorecard_boolean_gate_floor_fails_before_lane_summary_artifacts",
            detail=(
                "a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before "
                "the lane-summary validator creates fixture roots or report artifacts"
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
            check_name="scorecard_nonpositive_phase8_gate_floor_fails_before_lane_summary_artifacts",
            detail=(
                "a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails before "
                "the lane-summary validator creates fixture roots or report artifacts"
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
            check_name="scorecard_nonpositive_real_money_gate_floor_fails_before_lane_summary_artifacts",
            detail=(
                "a non-positive real-money discussion floor in forward_evidence_scorecard.json fails before "
                "the lane-summary validator creates fixture roots or report artifacts"
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
            check_name="scorecard_missing_no_baq_fails_before_lane_summary_artifacts",
            detail=(
                "a scorecard real-money gate that drops the no BAQ-as-BEL prerequisite fails before "
                "the lane-summary validator creates fixture roots or report artifacts"
            ),
        ),
    ]


def run_case(case_name: str, paths: dict[str, Path], expected_needles: list[str], *, display_summary: Path | None = None, scenario: str | None = None) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--base-summary", str(paths["base"]),
        "--next-steps-text", str(paths["next_text"]),
        "--next-steps-md", str(paths["next_md"]),
        "--lane-monitor-text", str(paths["monitor_text"]),
        "--lane-monitor-md", str(paths["monitor_md"]),
        "--forward-check-text", str(paths["forward_text"]),
        "--forward-check-md", str(paths["forward_md"]),
        "--settlement-ledger", str(paths["settlement"]),
    ]
    if display_summary is not None:
        cmd.extend(["--display-summary", str(display_summary)])
    cmd.extend(["--output", str(paths["output"])])
    subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, check=True)
    content = paths["output"].read_text(encoding="utf-8")

    rebuilt_args = argparse.Namespace(
        base_summary=str(paths["base"]),
        next_steps_text=str(paths["next_text"]),
        next_steps_md=str(paths["next_md"]),
        lane_monitor_text=str(paths["monitor_text"]),
        lane_monitor_md=str(paths["monitor_md"]),
        forward_check_text=str(paths["forward_text"]),
        forward_check_md=str(paths["forward_md"]),
        settlement_ledger=str(paths["settlement"]),
        display_summary=str(display_summary) if display_summary is not None else None,
        output=str(paths["output"]),
    )
    rebuilt = ptls.render_text(rebuilt_args)
    if content != rebuilt:
        raise AssertionError(f"{case_name}: summary.txt no longer matches a fresh rebuild from paper_trade_lane_summary.py")

    quick_summary = display_summary if display_summary is not None else paths["output"]
    assert_contains(content, f"- Summary: {quick_summary.relative_to(BASE)}", f"{case_name} routed summary quick file")
    assert_contains(content, f"- Next steps: {paths['next_md'].relative_to(BASE)}", f"{case_name} routed next-steps quick file")
    assert_contains(content, f"- Lane monitor: {paths['monitor_md'].relative_to(BASE)}", f"{case_name} routed lane-monitor quick file")
    assert_contains(content, f"- Forward check: {paths['forward_md'].relative_to(BASE)}", f"{case_name} routed forward-check quick file")
    assert_contains(content, f"- Settlement ledger: {paths['settlement'].relative_to(BASE)}", f"{case_name} routed settlement-ledger quick file")
    assert_contains(content, "Evidence frame:", f"{case_name} source evidence-frame header")
    assert_contains(content, f"- valid_evidence_scope={ptls.LANE_SUMMARY_VALID_EVIDENCE_SCOPE}", f"{case_name} source evidence scope line")
    assert_contains(content, f"- Boundary: {ptls.LANE_SUMMARY_EVIDENCE_BOUNDARY_TEXT}", f"{case_name} source evidence boundary line")

    for needle in expected_needles:
        assert_contains(content, needle, case_name)

    display_path = display_summary if display_summary is not None else paths["output"]
    result = {
        "case": case_name,
        "scenario": scenario,
        "output": str(display_path.relative_to(BASE)),
    }
    if display_summary is not None:
        result["write_target"] = str(paths["output"].relative_to(BASE))
    return result


def resolve_lane_scanner_status_path(lane_dir: Path) -> Path:
    pipeline_path = lane_dir / "pipeline_status.json"
    pipeline = ptds.read_json(pipeline_path)
    return ptds.resolve_scanner_status_path(lane_dir / "live_scan.status.json", pipeline_path, pipeline)


def build_base_summary_from_lane_status(lane_dir: Path) -> str:
    pipeline_path = lane_dir / "pipeline_status.json"
    pipeline = ptds.read_json(pipeline_path)
    scanner_path = resolve_lane_scanner_status_path(lane_dir)
    scanner = ptds.read_json(scanner_path)
    if scanner is None and pipeline is None:
        raise AssertionError(f"missing readable live status sidecars for {lane_dir}")
    return ptds.summarize(
        scanner,
        pipeline,
        scanner_state=ptds.json_state(scanner_path),
        pipeline_state=ptds.json_state(pipeline_path),
    )["summary_line"]




def setup_relocated_scanner_base_summary_case(case_name: str, declared_scanner_status_path: str) -> tuple[Path, dict[str, Path]]:
    case_root, paths = setup_case(
        case_name,
        "placeholder base summary rebuilt from relocated scanner sidecar",
        "Phase 7 current paper lane: TOO EARLY, 1 settled / 0 open, baseline hit rate 27.43%, Only 1 settled race(s).",
        "Phase 7 current paper lane monitor\n- Forward assessment: TOO EARLY\n- Pending settlement rows: 0\n- Read: treat this as limited coverage with surviving activity, not a dead missing-sidecar day.",
        "Phase 7 current paper lane next steps\n- State: COLLECTING SAMPLE\n- Why: The latest lane run kept surviving activity even though one race-detail cache file was missing, so keep it in the operational-limit bucket instead of flattening it into a generic unreadable artifact issue.\n- Latest run context: the latest lane run stayed in partial-cache-with-activity. One scanner hit survived, one recommendation was built, and the renamed scanner sidecar still carries the max-races detail.",
    )
    lane_dir = paths["output"].parent
    renamed_scanner_path = lane_dir / "renamed_live_scan.status.json"
    write_json(
        renamed_scanner_path,
        {
            "run_ts": "2026-05-20T20:20:00",
            "result": "partial_cache_missing_detail",
            "emitted_hit_count": 1,
            "raw_hit_count": 2,
            "partial_cache": True,
            "missing_race_detail_cache_skips": 1,
            "max_race_limit_hit": True,
            "race_details_attempted": 4,
            "rules_path": "phase7_current_paper_rules.json",
        },
    )
    if declared_scanner_status_path == "__RUN_ROOT_RELATIVE__":
        scanner_status_path = f"{lane_dir.name}/renamed_live_scan.status.json"
    elif declared_scanner_status_path == "__PROJECT_RELATIVE__":
        scanner_status_path = str(renamed_scanner_path.relative_to(BASE))
    else:
        scanner_status_path = declared_scanner_status_path
    write_json(
        lane_dir / "pipeline_status.json",
        {
            "run_ts": "2026-05-20T20:20:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_status_path": scanner_status_path,
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
    )
    write_text(paths["base"], build_base_summary_from_lane_status(lane_dir) + "\n")
    return case_root, paths


def setup_pipeline_recorded_scanner_status_base_summary_case(case_name: str, state: str, scanner_result: str) -> tuple[Path, dict[str, Path]]:
    case_root, paths = setup_case(
        case_name,
        "placeholder base summary rebuilt from pipeline-recorded scanner-status state",
        "Phase 7 current paper lane: NO DATA, 0 settled / 0 open, baseline hit rate 27.43%, No settled races yet, so this lane has no forward evidence one way or the other.",
        "Phase 7 current paper lane monitor\n- Forward assessment: NO DATA\n- Pending settlement rows: 0\n- Read: treat this as an operational scanner-status issue, not a clean quiet market day.",
        f"Phase 7 current paper lane next steps\n- State: REFRESH RUN ARTIFACTS\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- Why: The pipeline recorded the scanner status sidecar as {state}, but this copied lane surface no longer has the physical scanner sidecar file. Refresh the daily wrapper before reading the lane as clean market quiet.\n- Latest run context: the latest lane run preserved a pipeline-recorded scanner-status state: {state}. The current copied scanner sidecar file is missing, so keep this as an operational status issue.",
    )
    lane_dir = paths["output"].parent
    default_scanner_path = lane_dir / "live_scan.status.json"
    if default_scanner_path.exists():
        default_scanner_path.unlink()
    write_json(
        lane_dir / "pipeline_status.json",
        {
            "run_ts": "2026-05-20T20:40:00" if state == "empty" else "2026-05-20T20:45:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": scanner_result,
            "scanner_status_state": state,
            "observation_result": scanner_result,
            "observation_scope": "operational_issue",
            "observation_reason": scanner_result,
            "scan_hit_count": 0,
            "scanner_raw_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "error_count": 0,
        },
    )
    write_text(paths["base"], build_base_summary_from_lane_status(lane_dir) + "\n")
    return case_root, paths


def setup_missing_scan_output_base_summary_case() -> tuple[Path, dict[str, Path]]:
    case_root, paths = setup_case(
        "case_missing_scan_output_summary_context",
        "placeholder base summary rebuilt from missing scan-output pipeline state",
        "Phase 7 current paper lane: NO DATA, 0 settled / 0 open, baseline hit rate 27.43%, No settled races yet, so this lane has no forward evidence one way or the other.\n- Decision gate: No strategy change: this is still pre-evidence with 0 settled races.",
        "Phase 7 current paper lane monitor\n- Forward assessment: NO DATA\n- Decision gate: No strategy change: this is still pre-evidence with 0 settled races.\n- Pending settlement rows: 0\n- Read: treat this as an operational scan-output artifact issue, not a clean quiet market day.",
        "Phase 7 current paper lane next steps\n- State: REFRESH RUN ARTIFACTS\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- Why: The latest lane scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers; the pipeline used a safe empty [] fallback. Treat this as an artifact issue, not a clean no-qualifier observation. Refresh the daily wrapper before treating this lane as empty.\n- Latest run context: scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers; the pipeline used a safe empty [] fallback. Treat this as an artifact issue, not a clean no-qualifier observation.",
    )
    lane_dir = paths["output"].parent
    write_json(
        lane_dir / "live_scan.status.json",
        {
            "run_ts": "2026-05-20T20:35:00",
            "result": "no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
    )
    write_json(
        lane_dir / "pipeline_status.json",
        {
            "run_ts": "2026-05-20T20:35:00",
            "rules_path": "phase7_current_paper_rules.json",
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
    )
    write_text(paths["base"], build_base_summary_from_lane_status(lane_dir) + "\n")
    return case_root, paths


def setup_api_access_stale_cache_base_summary_case() -> tuple[Path, dict[str, Path]]:
    case_root, paths = setup_case(
        "case_api_access_stale_cache_fallback_context",
        "placeholder base summary rebuilt from API-access stale-cache fallback pipeline state",
        "Phase 7 current paper lane: NO DATA, 0 settled / 0 open, baseline hit rate 27.43%, No settled races yet, so this lane has no forward evidence one way or the other.\n- Decision gate: No strategy change: this is still pre-evidence with 0 settled races.",
        "Phase 7 current paper lane monitor\n- Forward assessment: NO DATA\n- Decision gate: No strategy change: this is still pre-evidence with 0 settled races.\n- Pending settlement rows: 0\n- Read: treat this as API-access scanner failure operator context, not a clean empty or no-target market read.",
        "Phase 7 current paper lane next steps\n- State: CHECK SCANNER FAILURE\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- Operator read-gate issue flags: has_api_access_failure_context=true; has_scanner_failure_boundary=true; has_stale_cache_fallback_context=true\n- Why: Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence. stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx.\n- Latest run context: scanner failed before producing signals. Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence. stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx.\n- Sidecar action: refresh_daily_wrapper_before_evidence_read.\n- Recheck command: ./run_daily_portfolio_observation.sh.",
    )
    lane_dir = paths["output"].parent
    write_json(
        lane_dir / "live_scan.status.json",
        {
            "run_ts": "2026-05-20T20:55:00",
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
    )
    write_json(
        lane_dir / "pipeline_status.json",
        {
            "run_ts": "2026-05-20T20:55:00",
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
    )
    write_text(paths["base"], build_base_summary_from_lane_status(lane_dir) + "\n")
    return case_root, paths


def setup_pipeline_recorded_invalid_shape_base_summary_case() -> tuple[Path, dict[str, Path]]:
    case_root, paths = setup_case(
        "case_pipeline_recorded_invalid_shape_scanner_missing",
        "placeholder base summary rebuilt from pipeline-recorded invalid-shape scanner-status state",
        "Phase 7 current paper lane: NO DATA, 0 settled / 0 open, baseline hit rate 27.43%, No settled races yet, so this lane has no forward evidence one way or the other.",
        "Phase 7 current paper lane monitor\n- Forward assessment: NO DATA\n- Pending settlement rows: 0\n- Read: treat this as an operational scanner-status issue, not a clean quiet market day.",
        "Phase 7 current paper lane next steps\n- State: REFRESH RUN ARTIFACTS\n- Settled races: 0 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races have return values (no settled outcomes yet)\n- Why: The latest scanner status sidecar was recorded invalid-shape by the pipeline, and the current scanner sidecar file is missing from this surface. Refresh the daily wrapper before treating this lane as empty.\n- Latest run context: the latest lane run preserved a pipeline-recorded scanner-status state: invalid-shape. The current copied scanner sidecar file is missing, so keep this as an operational status issue.",
    )
    lane_dir = paths["output"].parent
    default_scanner_path = lane_dir / "live_scan.status.json"
    if default_scanner_path.exists():
        default_scanner_path.unlink()
    write_json(
        lane_dir / "pipeline_status.json",
        {
            "run_ts": "2026-05-20T20:50:00",
            "rules_path": "phase7_current_paper_rules.json",
            "scanner_result": "scanner_status_invalid_shape",
            "scanner_status_state": "invalid_shape",
            "scanner_status_error": "expected scanner-status JSON object, got list",
            "observation_result": "scanner_status_unavailable_with_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_status_invalid_shape",
            "scan_hit_count": 1,
            "scanner_raw_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 0,
            "error_count": 0,
        },
    )
    write_text(paths["base"], build_base_summary_from_lane_status(lane_dir) + "\n")
    return case_root, paths


def live_lane_dirs() -> list[Path]:
    lanes: list[Path] = []
    if not LIVE_RUNS_ROOT.exists():
        raise AssertionError(f"no live run folders found under {LIVE_RUNS_ROOT}")
    for run_root in sorted(p for p in LIVE_RUNS_ROOT.iterdir() if p.is_dir()):
        for lane_dir in sorted(p for p in run_root.iterdir() if p.is_dir()):
            if (lane_dir / "summary.txt").exists():
                lanes.append(lane_dir)
    if not lanes:
        raise AssertionError(f"no live lane summaries found under {LIVE_RUNS_ROOT}")
    return lanes


def validate_live_surfaces() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for lane_dir in live_lane_dirs():
        with tempfile.TemporaryDirectory(prefix="lane-summary-live-", dir=TMP_PARENT) as tmp_dir:
            base_summary_path = Path(tmp_dir) / "summary_base.txt"
            write_text(base_summary_path, build_base_summary_from_lane_status(lane_dir) + "\n")
            rebuilt_args = argparse.Namespace(
                base_summary=str(base_summary_path),
                next_steps_text=str(lane_dir / "next_steps.txt"),
                next_steps_md=str(lane_dir / "next_steps.md"),
                lane_monitor_text=str(lane_dir / "lane_monitor.txt"),
                lane_monitor_md=str(lane_dir / "lane_monitor.md"),
                forward_check_text=str(lane_dir / "forward_check.txt"),
                forward_check_md=str(lane_dir / "forward_check.md"),
                settlement_ledger=str(BASE / "paper_trades" / f"{lane_dir.name}_paper_trade_settlements.csv"),
                display_summary=None,
                output=str(lane_dir / "summary.txt"),
            )
            expected = ptls.render_text(rebuilt_args)
        summary_path = lane_dir / "summary.txt"
        live_text = summary_path.read_text(encoding="utf-8")
        if live_text != expected:
            raise AssertionError(f"live lane summary drifted from the current source-layer rebuild: {summary_path}")
        assert_contains(live_text, f"- Summary: {summary_path.relative_to(BASE)}", f"live_surface_{lane_dir.parent.name}_{lane_dir.name} routed summary quick file")
        assert_contains(live_text, f"- Next steps: {(lane_dir / 'next_steps.md').relative_to(BASE)}", f"live_surface_{lane_dir.parent.name}_{lane_dir.name} routed next-steps quick file")
        assert_contains(live_text, f"- Lane monitor: {(lane_dir / 'lane_monitor.md').relative_to(BASE)}", f"live_surface_{lane_dir.parent.name}_{lane_dir.name} routed lane-monitor quick file")
        assert_contains(live_text, f"- Forward check: {(lane_dir / 'forward_check.md').relative_to(BASE)}", f"live_surface_{lane_dir.parent.name}_{lane_dir.name} routed forward-check quick file")
        assert_contains(live_text, f"- Settlement ledger: {(BASE / 'paper_trades' / f'{lane_dir.name}_paper_trade_settlements.csv').relative_to(BASE)}", f"live_surface_{lane_dir.parent.name}_{lane_dir.name} routed settlement-ledger quick file")
        assert_contains(live_text, "Evidence frame:", f"live_surface_{lane_dir.parent.name}_{lane_dir.name} source evidence-frame header")
        assert_contains(live_text, f"- valid_evidence_scope={ptls.LANE_SUMMARY_VALID_EVIDENCE_SCOPE}", f"live_surface_{lane_dir.parent.name}_{lane_dir.name} source evidence scope line")
        assert_contains(live_text, f"- Boundary: {ptls.LANE_SUMMARY_EVIDENCE_BOUNDARY_TEXT}", f"live_surface_{lane_dir.parent.name}_{lane_dir.name} source evidence boundary line")
        api_access_action_route_confirmed = assert_api_access_action_route_if_present(
            live_text,
            f"live_surface_{lane_dir.parent.name}_{lane_dir.name}",
        )
        results.append({
            "case": f"live_surface_{lane_dir.parent.name}_{lane_dir.name}",
            "scenario": "saved live lane summary matches the current source-layer rebuild",
            "lane_dir": str(lane_dir.relative_to(BASE)),
            "output": str(summary_path.relative_to(BASE)),
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
    tmp_parent = prepare_tmp_parent()
    for legacy in [
        FIXTURE_ROOT / "lane_summary_fixture_validation.md",
        FIXTURE_ROOT / "lane_summary_fixture_validation.json",
    ]:
        if legacy.exists():
            legacy.unlink()
    suite_read = (
        "lane summary still preserves the full routed quick-files bundle, a compact lane snapshot with settlement-integrity, ROI-coverage, current ROI-complete/timestamp coverage wording, explicit malformed-field placeholders, and lifted latest-run-context visibility, including saved-live and direct-fixture API-access action/recheck routing when the latest-run context is a 403 scanner failure with stale-cache fallback, forward-check, lane-monitor, next-steps, explicit zero-settled pre-evidence wording, lifted operator read-gate issue flags, missing scan-output fallback context, and stage-aware pipeline-failure context, "
        "while source rendered lane summaries and the direct validator report now publish exact `valid_evidence_scope=paper_trade_lane_summary_navigation_context_only` lines plus source-level boundary text so quick files, compact lane snapshots, lifted decision-gate wording, Phase 8 review-floor cautions, pipeline context, clean-empty/no-target routing, issue routing, and saved-live rebuild cleanliness stay navigation/context metadata only, while degrading missing base or detail files into explicit placeholders, hiding temp write paths from the human-facing summary, keeping live rebuild scratch files under a project-local validation root, recovering lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars before regenerating the live base headline for saved lane-surface rebuilds, keeping missing scan-output fallback metadata plus pipeline-recorded empty/unreadable/invalid-shape scanner-status base headlines explicit when copied lane surfaces lack the physical scanner sidecar, and lifting the no-overpromotion decision gate plus Phase 8 review-floor caution into the lane snapshot when source artifacts provide them, "
        "while rejecting malformed scorecard gates before fixture/report artifacts and preserving the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that quick files, compact lane snapshots, lifted gate wording, pipeline context, and saved-live rebuild cleanliness do not advance; lane summary: enriched operator navigation/context surface, not new forward evidence by itself"
    )

    _, empty_paths = setup_case(
        "case_empty_lane",
        "Phase 7 current paper run 2026-05-20T11:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        "Phase 7 current paper lane: NO DATA, 0 settled / 0 open, baseline hit rate 27.43%, No settled races yet, so this lane has no forward evidence one way or the other.\n- Decision gate: No strategy change: this is still pre-evidence with 0 settled races.",
        "Phase 7 current paper lane monitor\n- Forward assessment: NO DATA\n- Decision gate: No strategy change: this is still pre-evidence with 0 settled races.\n- Pending settlement rows: 0",
        "Phase 7 current paper lane next steps\n- State: WAITING FOR FIRST SETTLED RACES\n- Operator read-gate issue flags: has_api_access_failure_context=false; has_scanner_failure_boundary=false; has_stale_cache_fallback_context=false",
    )
    _, pending_paths = setup_case(
        "case_settlement_pending",
        "Phase 7 current paper run 2026-05-20T16:00:00: signals logged, 2 pending settlement row(s)",
        "Phase 7 current paper lane: TOO EARLY, 3 settled / 2 open, baseline hit rate 27.43%, Only 3 settled race(s).\n- Decision gate: No strategy change: 3 settled race(s) is below the first statistical-read gate of 30.",
        "Phase 7 current paper lane monitor\n- Forward assessment: TOO EARLY\n- Decision gate: No strategy change: 3 settled race(s) is below the first statistical-read gate of 30.\n- Pending settlement rows: 2",
        "Phase 7 current paper lane next steps\n- State: NEEDS SETTLEMENT",
    )
    _, phase8_caution_paths = setup_case(
        "case_phase8_review_floor_caution",
        "Phase 8 shadow run 2026-05-20T16:20:00: signals logged, no bet, 1 scanner hit(s), 1 recommendation(s)",
        "Phase 8 shadow lane: NO DATA, 0 settled / 1 open, baseline hit rate 34.75%, No settled races yet, so this lane has no forward evidence one way or the other.",
        "Phase 8 shadow lane monitor\n- Forward assessment: NO DATA\n- Decision gate: No strategy change: this is still pre-evidence with 0 settled races.\n- Pending settlement rows: 1",
        "Phase 8 shadow lane next steps\n- State: NEEDS SETTLEMENT\n- Settled races: 0 | open races: 1 | open settlement rows: 1 | settled rows missing outcome: 0\n- ROI coverage: 0/0 settled races are ROI-complete (no settled outcomes yet)\n- Why: 1 settlement row(s) are still open, so settle before reading this as evidence.",
    )
    write_text(
        phase8_caution_paths["forward_md"],
        "# Paper-Trade Forward Check\n\n"
        "- Decision-gate caution: Phase 8 shadow first-read status is a review floor, not a promotion entitlement; lane totals alone do not promote any Phase 8 pocket, scorecard tiers remain binding, and negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion.\n",
    )
    _, missing_paths = setup_case(
        "case_missing_detail",
        "Phase 7 current paper run 2026-05-20T18:00:00: bets ready, 1 BET recommendation(s)",
        None,
        "Phase 7 current paper lane monitor\n- Forward assessment: NO DATA",
        None,
    )
    _, partial_roi_paths = setup_case(
        "case_partial_roi_coverage",
        "Phase 7 current paper run 2026-05-20T17:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        "Phase 7 current paper lane: TOO EARLY, 5 settled / 0 open, baseline hit rate 27.43%, ROI coverage 2/5, observed ROI +100.00% on 2/5 covered settled races, Only 5 settled race(s).\n- Decision gate: No strategy change: 5 settled race(s) is below the first statistical-read gate of 30.",
        "Phase 7 current paper lane monitor\n- Forward assessment: TOO EARLY\n- ROI coverage: 2/5 settled races have return values (3 still missing return/cost coverage)\n- Decision gate: No strategy change: 5 settled race(s) is below the first statistical-read gate of 30.\n- Settled rows missing ROI coverage: 3",
        "Phase 7 current paper lane next steps\n- State: COLLECTING SAMPLE\n- Settled races: 5 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 2/5 settled races have return values (3 still missing return/cost coverage)",
    )
    _, current_roi_wording_paths = setup_case(
        "case_current_roi_complete_coverage_wording",
        "Phase 7 current paper run 2026-05-20T17:10:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        "Phase 7 current paper lane: TOO EARLY, 3 settled / 0 open, baseline hit rate 27.43%, ROI coverage 1/3, observed ROI +300.00% on 1/3 covered settled races, Only 3 settled race(s).\n- Decision gate: No strategy change: 3 settled race(s) is below the first statistical-read gate of 30.",
        "Phase 7 current paper lane monitor\n- Forward assessment: TOO EARLY\n- ROI coverage: 1/3 settled races are ROI-complete with return/cost/timestamp coverage (2 still missing coverage)\n- Decision gate: No strategy change: 3 settled race(s) is below the first statistical-read gate of 30.\n- Settled rows missing ROI-complete coverage: 2 (non-positive actual_cost: 1; non-positive expected_cost: 1)",
        "Phase 7 current paper lane next steps\n- State: COLLECTING SAMPLE\n- Settled races: 3 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0\n- ROI coverage: 1/3 settled races are ROI-complete with return/cost/timestamp coverage (2 still missing coverage)\n- Settled rows missing ROI-complete coverage: 2 (non-positive actual_cost: 1; non-positive expected_cost: 1)",
    )
    _, malformed_next_steps_paths = setup_case(
        "case_missing_next_step_snapshot_fields",
        "Phase 7 current paper run 2026-05-20T18:30:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        "Phase 7 current paper lane: NO DATA, 0 settled / 0 open, baseline hit rate 27.43%, No settled races yet, so this lane has no forward evidence one way or the other.",
        "Phase 7 current paper lane monitor\n- Forward assessment: NO DATA\n- Pending settlement rows: 0",
        "Phase 7 current paper lane next steps",
    )
    _, temp_paths = setup_case(
        "case_display_summary_override",
        "Phase 7 current paper run 2026-05-20T19:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        "Phase 7 current paper lane: NO DATA, 0 settled / 0 open, baseline hit rate 27.43%, No settled races yet, so this lane has no forward evidence one way or the other.",
        "Phase 7 current paper lane monitor\n- Forward assessment: NO DATA\n- Pending settlement rows: 0",
        "Phase 7 current paper lane next steps\n- State: WAITING FOR FIRST SETTLED RACES",
    )
    temp_paths["output"] = temp_paths["output"].with_name("summary.enriched.tmp")
    _, pipeline_failure_paths = setup_case(
        "case_pipeline_failure_context",
        "Phase 7 current paper run 2026-05-20T19:30:00: logger failure, 1 scanner hit(s), 1 recommendation(s), stage logger, ValueError, detail: fixture logger crash",
        "Phase 7 current paper lane: NO DATA, 0 settled / 0 open, baseline hit rate 27.43%, No settled races yet, so this lane has no forward evidence one way or the other.",
        "Phase 7 current paper lane monitor\n- Forward assessment: NO DATA\n- Pending settlement rows: 0\n- Read: No settled races yet, so this lane has no forward evidence one way or the other.",
        "Phase 7 current paper lane next steps\n- State: CHECK PIPELINE FAILURE\n- Why: The latest lane run ended in logger failure, so treat this as an operational issue instead of normal observation noise. Refresh the daily wrapper and re-check the lane before reading it as evidence.\n- Latest run context: the latest lane run ended in logger failure. Stage: logger. Error type: ValueError. Detail: fixture logger crash",
    )
    _, pipeline_recommender_paths = setup_case(
        "case_pipeline_recommender_failure_context",
        "Phase 7 current paper run 2026-05-20T19:20:00: recommender failure, 1 scanner hit(s), 0 recommendation(s), stage recommender, RuntimeError, detail: fixture recommender crash",
        "Phase 7 current paper lane: NO DATA, 0 settled / 0 open, baseline hit rate 27.43%, No settled races yet, so this lane has no forward evidence one way or the other.",
        "Phase 7 current paper lane monitor\n- Forward assessment: NO DATA\n- Pending settlement rows: 0\n- Read: No settled races yet, so this lane has no forward evidence one way or the other.",
        "Phase 7 current paper lane next steps\n- State: CHECK PIPELINE FAILURE\n- Why: The latest lane run ended in recommender failure, so treat this as an operational issue instead of normal observation noise. Refresh the daily wrapper and re-check the lane before reading it as evidence.\n- Latest run context: the latest lane run ended in recommender failure. Stage: recommender. Error type: RuntimeError. Detail: fixture recommender crash",
    )
    _, missing_base_paths = setup_case(
        "case_missing_base_summary",
        "Phase 7 current paper run 2026-05-20T20:00:00: clean empty run, 0 scanner hit(s), 0 recommendation(s)",
        "Phase 7 current paper lane: NO DATA, 0 settled / 0 open, baseline hit rate 27.43%, No settled races yet, so this lane has no forward evidence one way or the other.",
        "Phase 7 current paper lane monitor\n- Forward assessment: NO DATA\n- Pending settlement rows: 0",
        "Phase 7 current paper lane next steps\n- State: WAITING FOR FIRST SETTLED RACES",
    )
    missing_base_paths["base"].unlink()
    _, relocated_scanner_paths = setup_relocated_scanner_base_summary_case(
        "case_relocated_scanner_base_summary",
        "renamed_live_scan.status.json",
    )
    _, relocated_scanner_run_root_paths = setup_relocated_scanner_base_summary_case(
        "case_relocated_scanner_base_summary_run_root_relative",
        "__RUN_ROOT_RELATIVE__",
    )
    _, relocated_scanner_project_paths = setup_relocated_scanner_base_summary_case(
        "case_relocated_scanner_base_summary_project_relative",
        "__PROJECT_RELATIVE__",
    )
    _, pipeline_recorded_empty_paths = setup_pipeline_recorded_scanner_status_base_summary_case(
        "case_pipeline_recorded_empty_scanner_missing",
        "empty",
        "scanner_status_empty",
    )
    _, pipeline_recorded_unreadable_paths = setup_pipeline_recorded_scanner_status_base_summary_case(
        "case_pipeline_recorded_unreadable_scanner_missing",
        "unreadable",
        "scanner_status_unreadable",
    )
    _, missing_scan_output_paths = setup_missing_scan_output_base_summary_case()
    _, api_access_stale_cache_paths = setup_api_access_stale_cache_base_summary_case()
    _, pipeline_recorded_invalid_shape_paths = setup_pipeline_recorded_invalid_shape_base_summary_case()

    fixture_results = [
        run_case(
            "case_empty_lane",
            empty_paths,
            [
                "Quick files:",
                "Forward check:",
                "Lane monitor:",
                "Next steps:",
                "clean empty run, 0 scanner hit(s), 0 recommendation(s)",
                "- Operator read-gate issue flags: has_api_access_failure_context=false; has_scanner_failure_boundary=false; has_stale_cache_fallback_context=false",
                "- Decision gate: No strategy change: this is still pre-evidence with 0 settled races.",
            ],
            scenario="normal empty lane summary",
        ),
        run_case(
            "case_settlement_pending",
            pending_paths,
            [
                "2 pending settlement row(s)",
                "Pending settlement rows: 2",
                "State: NEEDS SETTLEMENT",
                "- Decision gate: No strategy change: 3 settled race(s) is below the first statistical-read gate of 30.",
                "Settlement ledger:",
            ],
            scenario="settlement-pending lane summary",
        ),
        run_case(
            "case_phase8_review_floor_caution",
            phase8_caution_paths,
            [
                "Phase 8 shadow run 2026-05-20T16:20:00: signals logged, no bet, 1 scanner hit(s), 1 recommendation(s)",
                "- Decision gate: No strategy change: this is still pre-evidence with 0 settled races.",
                "- Decision-gate caution: Phase 8 shadow first-read status is a review floor, not a promotion entitlement; lane totals alone do not promote any Phase 8 pocket, scorecard tiers remain binding, and negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion.",
                "State: NEEDS SETTLEMENT",
            ],
            scenario="Phase 8 shadow review-floor caution is lifted into the compact lane snapshot",
        ),
        run_case(
            "case_missing_detail",
            missing_paths,
            [
                "bets ready, 1 BET recommendation(s)",
                "[missing forward-check text:",
                "[missing next-steps text:",
                "Lane monitor detail:",
            ],
            scenario="missing detail artifacts degrade with placeholders",
        ),
        run_case(
            "case_partial_roi_coverage",
            partial_roi_paths,
            [
                "Lane snapshot:",
                "- Settlement integrity: 5 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0",
                "- ROI coverage: 2/5 settled races have return values (3 still missing return/cost coverage)",
                "ROI coverage 2/5 (3 missing)",
                "Settled rows missing ROI coverage: 3",
                "- Decision gate: No strategy change: 5 settled race(s) is below the first statistical-read gate of 30.",
            ],
            scenario="compact lane summary now keeps partial ROI coverage visible before the reader drills into detail artifacts",
        ),
        run_case(
            "case_current_roi_complete_coverage_wording",
            current_roi_wording_paths,
            [
                "Lane snapshot:",
                "- Settlement integrity: 3 | open races: 0 | open settlement rows: 0 | settled rows missing outcome: 0",
                "- ROI coverage: 1/3 settled races are ROI-complete with return/cost/timestamp coverage (2 still missing coverage)",
                "ROI coverage 1/3 (2 missing)",
                "Settled rows missing ROI-complete coverage: 2 (non-positive actual_cost: 1; non-positive expected_cost: 1)",
                "- Decision gate: No strategy change: 3 settled race(s) is below the first statistical-read gate of 30.",
            ],
            scenario="current ROI-complete coverage wording enriches the base headline with missing-count context",
        ),
        run_case(
            "case_missing_next_step_snapshot_fields",
            malformed_next_steps_paths,
            [
                "- Settlement integrity: [missing settlement integrity: out/status_validation/lane_summary_fixture/case_missing_next_step_snapshot_fields/out/daily_portfolio_runs/2026-05-20/phase7_current_paper/next_steps.txt]",
                "- ROI coverage: [missing ROI coverage: out/status_validation/lane_summary_fixture/case_missing_next_step_snapshot_fields/out/daily_portfolio_runs/2026-05-20/phase7_current_paper/next_steps.txt]",
                "Phase 7 current paper lane next steps",
            ],
            scenario="malformed-but-present next-steps artifacts keep missing settlement/ROI snapshot fields explicit instead of quietly disappearing from the lane summary",
        ),
        run_case(
            "case_relocated_scanner_base_summary",
            relocated_scanner_paths,
            [
                "partial cache with activity, 1 scanner hit(s), 2 raw before dedup, 1 recommendation(s), 1 missing race detail cache file(s), max-races cap hit after 4 attempt(s)",
                "Latest run context: the latest lane run stayed in partial-cache-with-activity. One scanner hit survived, one recommendation was built, and the renamed scanner sidecar still carries the max-races detail.",
                "Forward check:",
                "Lane monitor:",
                "Next steps:",
            ],
            scenario="live-style rebuild keeps the stronger base headline when pipeline_status.json points at a renamed scanner sidecar",
        ),
        run_case(
            "case_relocated_scanner_base_summary_run_root_relative",
            relocated_scanner_run_root_paths,
            [
                "partial cache with activity, 1 scanner hit(s), 2 raw before dedup, 1 recommendation(s), 1 missing race detail cache file(s), max-races cap hit after 4 attempt(s)",
                "Latest run context: the latest lane run stayed in partial-cache-with-activity. One scanner hit survived, one recommendation was built, and the renamed scanner sidecar still carries the max-races detail.",
                "Forward check:",
                "Lane monitor:",
                "Next steps:",
            ],
            scenario="live-style rebuild keeps the stronger base headline when pipeline_status.json declares the renamed scanner sidecar relative to the run root",
        ),
        run_case(
            "case_relocated_scanner_base_summary_project_relative",
            relocated_scanner_project_paths,
            [
                "partial cache with activity, 1 scanner hit(s), 2 raw before dedup, 1 recommendation(s), 1 missing race detail cache file(s), max-races cap hit after 4 attempt(s)",
                "Latest run context: the latest lane run stayed in partial-cache-with-activity. One scanner hit survived, one recommendation was built, and the renamed scanner sidecar still carries the max-races detail.",
                "Forward check:",
                "Lane monitor:",
                "Next steps:",
            ],
            scenario="live-style rebuild keeps the stronger base headline when pipeline_status.json declares the renamed scanner sidecar relative to the project root",
        ),
        run_case(
            "case_pipeline_recorded_empty_scanner_missing",
            pipeline_recorded_empty_paths,
            [
                "scanner sidecar recorded empty, 0 scanner hit(s), 0 recommendation(s), current scanner sidecar file missing, pipeline recorded scanner-status state empty",
                "State: REFRESH RUN ARTIFACTS",
                "pipeline-recorded scanner-status state: empty",
                "operational scanner-status issue, not a clean quiet market day",
            ],
            scenario="live-style rebuild keeps a pipeline-recorded empty scanner-status state explicit when the copied scanner sidecar file is missing",
        ),
        run_case(
            "case_pipeline_recorded_unreadable_scanner_missing",
            pipeline_recorded_unreadable_paths,
            [
                "scanner sidecar recorded unreadable, 0 scanner hit(s), 0 recommendation(s), current scanner sidecar file missing, pipeline recorded scanner-status state unreadable",
                "State: REFRESH RUN ARTIFACTS",
                "pipeline-recorded scanner-status state: unreadable",
                "operational scanner-status issue, not a clean quiet market day",
            ],
            scenario="live-style rebuild keeps a pipeline-recorded unreadable scanner-status state explicit when the copied scanner sidecar file is missing",
        ),
        run_case(
            "case_missing_scan_output_summary_context",
            missing_scan_output_paths,
            [
                "missing scanner output, 0 scanner hit(s), 0 recommendation(s)",
                "scanner-status reported no_qualifiers",
                "safe empty scan fallback missing_or_empty_scan_output",
                "scan input was missing before fallback",
                "State: REFRESH RUN ARTIFACTS",
                "- Why now: The latest lane scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers; the pipeline used a safe empty [] fallback. Treat this as an artifact issue, not a clean no-qualifier observation. Refresh the daily wrapper before treating this lane as empty.",
                "- Latest run context: scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers; the pipeline used a safe empty [] fallback. Treat this as an artifact issue, not a clean no-qualifier observation.",
                "operational scan-output artifact issue, not a clean quiet market day",
            ],
            scenario="live-style rebuild keeps missing scan-output fallback metadata visible in the enriched lane summary instead of flattening the lane into clean-empty context",
        ),
        run_case(
            "case_api_access_stale_cache_fallback_context",
            api_access_stale_cache_paths,
            [
                "scanner API access failure",
                "HTTP 403",
                "API-access-failure operator context only",
                "operator action refresh_daily_wrapper_before_evidence_read",
                "recheck command ./run_daily_portfolio_observation.sh",
                "stale cache fallback used for cards",
                "2 stale cache fallback(s)",
                "stale cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
                "scanner failure class api_access_failure",
                "State: CHECK SCANNER FAILURE",
                "- Operator read-gate issue flags: has_api_access_failure_context=true; has_scanner_failure_boundary=true; has_stale_cache_fallback_context=true",
                "- Why now: Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence. stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx.",
                "- Latest run context: scanner failed before producing signals. Treat this as API-access scanner failure operator context, not a no-target day, clean-empty scan, settled ROI, promotion, live-profitability, or real-money evidence. stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx.",
                API_ACCESS_ACTION_TEXT,
                API_ACCESS_RECHECK_TEXT,
            ],
            scenario="live-style rebuild keeps API-access stale-cache fallback context visible in the enriched lane summary instead of flattening the lane into clean-empty context",
        ),
        run_case(
            "case_pipeline_recorded_invalid_shape_scanner_missing",
            pipeline_recorded_invalid_shape_paths,
            [
                "scanner sidecar recorded invalid shape, 1 scanner hit(s), 1 recommendation(s), scanner-status error: expected scanner-status JSON object, got list, current scanner sidecar file missing, pipeline recorded scanner-status state invalid_shape",
                "State: REFRESH RUN ARTIFACTS",
                "recorded invalid-shape by the pipeline",
                "pipeline-recorded scanner-status state: invalid-shape",
                "operational scanner-status issue, not a clean quiet market day",
            ],
            scenario="live-style rebuild keeps a pipeline-recorded invalid-shape scanner-status state explicit when the copied scanner sidecar file is missing",
        ),
        run_case(
            "case_display_summary_override",
            temp_paths,
            [
                "Quick files:",
                "- Summary: out/status_validation/lane_summary_fixture/case_display_summary_override/out/daily_portfolio_runs/2026-05-20/phase7_current_paper/summary.txt",
            ],
            display_summary=temp_paths["output"].with_name("summary.txt"),
            scenario="temp-file writes still display the final summary path",
        ),
        run_case(
            "case_pipeline_failure_context",
            pipeline_failure_paths,
            [
                "logger failure, 1 scanner hit(s), 1 recommendation(s), stage logger, ValueError, detail: fixture logger crash",
                "State: CHECK PIPELINE FAILURE",
                "- Why now: The latest lane run ended in logger failure, so treat this as an operational issue instead of normal observation noise. Refresh the daily wrapper and re-check the lane before reading it as evidence.",
                "- Latest run context: the latest lane run ended in logger failure. Stage: logger. Error type: ValueError. Detail: fixture logger crash",
                "Stage: logger. Error type: ValueError. Detail: fixture logger crash",
            ],
            scenario="logger-stage pipeline-failure context stays visible in the enriched lane summary",
        ),
        run_case(
            "case_pipeline_recommender_failure_context",
            pipeline_recommender_paths,
            [
                "recommender failure, 1 scanner hit(s), 0 recommendation(s), stage recommender, RuntimeError, detail: fixture recommender crash",
                "State: CHECK PIPELINE FAILURE",
                "- Why now: The latest lane run ended in recommender failure, so treat this as an operational issue instead of normal observation noise. Refresh the daily wrapper and re-check the lane before reading it as evidence.",
                "- Latest run context: the latest lane run ended in recommender failure. Stage: recommender. Error type: RuntimeError. Detail: fixture recommender crash",
                "Stage: recommender. Error type: RuntimeError. Detail: fixture recommender crash",
            ],
            scenario="recommender-stage pipeline-failure context stays visible in the enriched lane summary",
        ),
        run_case(
            "case_missing_base_summary",
            missing_base_paths,
            [
                "[missing base summary:",
                "Forward check:",
                "Lane monitor:",
                "Next steps:",
            ],
            scenario="missing base summary degrades to explicit placeholder",
        ),
    ]
    live_surfaces = validate_live_surfaces()
    live_api_access_action_route_checks = sum(
        1 for row in live_surfaces if row.get("api_access_action_route_confirmed")
    )
    if live_api_access_action_route_checks <= 0:
        raise AssertionError(
            "saved live lane summaries no longer include an API-access action/recheck route check"
        )
    results = fixture_results + live_surfaces

    report_md = OUT_MD
    report_json = OUT_JSON
    child_checks = scorecard_guardrails + [
        {
            "check": "fixture_quick_files_and_lane_snapshot_stay_covered",
            "status": "pass",
            "detail": "fixture cases still preserve the full routed quick-files bundle, compact lane snapshot, malformed-field placeholders, missing scan-output context, and forward-check/lane-monitor/next-steps sections",
        },
        {
            "check": "saved_live_lane_summaries_match_current_rebuilds",
            "status": "pass",
            "detail": "saved live lane summary surfaces under out/daily_portfolio_runs still have to match the current source-layer rebuild instead of drifting behind helper changes, and saved-live API-access contexts have to keep the sidecar action plus wrapper recheck command visible in generated text",
        },
        {
            "check": "relocated_sidecar_and_placeholder_fallbacks_stay_explicit",
            "status": "pass",
            "detail": "live rebuilds still recover lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars and keep missing scan-output fallback metadata plus pipeline-recorded empty/unreadable/invalid-shape scanner-status base headlines explicit when copied lane surfaces lack the physical scanner sidecar, while missing base or detail artifacts degrade into explicit placeholders instead of depending on shell cat success",
        },
        {
            "check": "pipeline_failure_roi_gap_and_context_lines_stay_pinned",
            "status": "pass",
            "detail": "stage-aware pipeline-failure context, lifted Why/latest-run-context lines, malformed settlement/ROI snapshot placeholders, zero-settled framing, and both legacy return-value and current ROI-complete/timestamp coverage snapshot lines stay explicit in the enriched lane summary",
        },
        {
            "check": "api_access_stale_cache_fallback_context_stays_pinned",
            "status": "pass",
            "detail": "API-access scanner failures that complete from stale cache keep HTTP status, stale-cache fallback count/kind/error detail, action/recheck routing, operator read-gate issue flags, and the no-evidence boundary visible in the enriched lane summary",
        },
        {
            "check": "lane_summary_lifts_decision_gate_when_available",
            "status": "pass",
            "detail": "the enriched lane snapshot now lifts the no-overpromotion decision gate and Phase 8 review-floor caution from source artifacts when available, so quick lane summaries do not show only the assessment and ROI detail",
        },
        {
            "check": "lane_summary_explicitly_stays_navigation_not_new_evidence",
            "status": "pass",
            "detail": "the direct validator summary still treats lane summary as a routed navigation/reproducibility surface rather than standalone new forward evidence",
        },
        {
            "check": "source_lane_summary_output_publishes_evidence_boundary_fields",
            "status": "pass",
            "detail": "fixture and saved-live summary.txt outputs now publish exact source-level valid_evidence_scope=paper_trade_lane_summary_navigation_context_only lines plus evidence_boundary_text so quick files, compact lane snapshots, decision-gate wording, Phase 8 review-floor cautions, pipeline context, clean-empty/no-target routing, issue routing, and saved-live rebuild cleanliness are not overread as scanner evidence, live ledger evidence, settled ROI, promotion readiness, live profitability, real-money support, or BAQ-as-BEL evidence",
        },
        {
            "check": "direct_validation_report_exposes_lane_summary_valid_scope",
            "status": "pass",
            "detail": "the direct lane-summary validator report now exposes the raw valid_evidence_scope line and keeps green summary checks classified as navigation/context metadata only",
        },
        {
            "check": "lane_summary_preserves_scorecard_gate_boundary",
            "status": "pass",
            "detail": "the lane-summary validator now publishes the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite while saying quick files, compact lane snapshots, lifted decision-gate wording, pipeline context, and saved-live rebuild cleanliness do not count toward those gates",
        },
        {
            "check": "fixture_scratch_root_project_local",
            "status": "pass",
            "detail": f"live lane-summary rebuild scratch files write under the project-local temporary root {TMP_PARENT}, cleared before validation",
        },
        {
            "check": "fixture_scratch_metadata_published",
            "status": "pass",
            "detail": "the lane-summary validator JSON publishes tmp_parent, tmp_parent_is_project_local, and tmp_parent_cleared_before_fixture_run so parent rollups can audit scratch hygiene without parsing markdown prose",
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
        raise AssertionError("lane-summary scorecard gate boundary no longer matches forward_evidence_scorecard.json")
    report_lines = [
        "# Paper-Trade Lane Summary Validation",
        "",
        "This report validates `paper_trade_lane_summary.py` against representative fixture cases under `out/status_validation/lane_summary_fixture/`, while publishing the direct validator readout under `out/status_validation/paper_trade_lane_summary/`.",
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
        *[f"- `{row['lane_dir']}` -> `{row['output']}`" for row in live_surfaces],
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
        f"- Source scope line: `valid_evidence_scope={ptls.LANE_SUMMARY_VALID_EVIDENCE_SCOPE}`.",
        f"- Source boundary: {ptls.LANE_SUMMARY_EVIDENCE_BOUNDARY_TEXT}",
        "- Boundary: lane-summary validator cleanliness is navigation/context metadata only, not new forward evidence, not a live paper-trade ledger, not a current-day scanner result, not settled ROI, not live profitability, not promotion readiness, and not real-money evidence.",
        "- Non-goals: do not treat quick files, compact lane snapshots, lifted decision-gate wording, Phase 8 review-floor cautions, clean-empty/no-target routing, or green validators as ROI-complete observations, profitability evidence, promotion support, or real-money support.",
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
        "## Fixture Scratch Root",
        "",
        f"- Temporary fixture root: `{tmp_parent}` (cleared before validation)",
        f"- Temporary fixture root project-local: `{tmp_parent.is_relative_to(BASE)}`",
        "",
        "## Validation result",
        "",
        "- Fixture root: `out/status_validation/lane_summary_fixture/`",
        "- Direct validator report path: `out/status_validation/paper_trade_lane_summary/`",
        f"- All {len(fixture_results)} fixture cases now preserve the full routed quick-files bundle: routed summary, next-steps, lane-monitor, forward-check, and settlement-ledger links, plus the compact lane snapshot and the forward-check, lane-monitor, and next-steps sections.",
        "- The validator now also fails if any saved live lane `summary.txt` under `out/daily_portfolio_runs/` drifts from the current source-layer rebuild or drops any part of that same full routed quick-files bundle, and those live rebuilds now recover lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars before regenerating the base headline.",
        "- Source-rendered lane summaries now also publish an `Evidence frame` with exact `valid_evidence_scope=paper_trade_lane_summary_navigation_context_only` plus boundary text so the copyable lane artifact itself says it is navigation/context metadata only, not scanner evidence, live ledger evidence, settled ROI, promotion readiness, live profitability, real-money support, or BAQ-as-BEL evidence.",
        f"- Saved live lane summaries with API-access / HTTP 403 context must also preserve `{API_ACCESS_ACTION_TEXT}` and `{API_ACCESS_RECHECK_TEXT}` in generated text; current saved-live route checks: {live_api_access_action_route_checks}.",
        "- Copied-lane fixtures now also prove that missing scan-output fallback metadata stays visible in the enriched lane summary when the scanner-status sidecar reports `no_qualifiers`, that API-access stale-cache fallback context keeps HTTP status, stale-cache count/kind/error metadata, operator read-gate issue flags, and action/recheck routing visible, and that pipeline-recorded empty/unreadable/invalid-shape scanner-status states stay visible as operational status issues when the physical scanner sidecar file is absent.",
        "- Missing base and detail artifacts now degrade into explicit placeholders instead of making lane-summary assembly depend on shell `cat` success.",
        "- Stage-aware pipeline-failure context, lifted `Why` / `Latest run context` snapshot lines, zero-settled pre-evidence wording, partial ROI-coverage snapshot lines, current ROI-complete/timestamp coverage wording, and the no-overpromotion decision gate plus Phase 8 review-floor caution are now pinned directly at the lane-summary layer, including the base headline carrying missing-count context when realized ROI is only partially covered, so logger/recommender failure detail, first-sample framing, decision-gate wording, review-floor wording, and incomplete ROI coverage cannot quietly disappear from the enriched lane summary even if wrapper-level coverage stays green.",
        "- Temp-file writes can still display the final summary path inside the full routed quick-files bundle, which keeps wrapper-generated summaries from leaking implementation-only `.tmp` paths into human-facing artifacts.",
        "- Each fixture output is still checked against a fresh in-memory rebuild from `paper_trade_lane_summary.py`, not only against selected strings.",
        "- The validation report now lists the human-facing summary path for each fixture case while separately pinning every saved live lane surface.",
        "- Live-surface rebuild scratch files now stay under the project-local validation scratch root instead of system temp, and that scratch root is cleared before validation.",
        "- The validator JSON now also publishes sixteen explicit structured guardrails, so parent rollups can verify malformed-scorecard no-artifact failures including non-positive Phase 8 and real-money copied gate floors, saved-live rebuild parity, source-output evidence-boundary fields, direct validator valid_evidence_scope exposure, relocated-sidecar recovery plus missing scan-output fallback, API-access stale-cache fallback context with operator read-gate issue flags, and pipeline-recorded scanner-status preservation, placeholder fallback behavior, pinned failure/ROI-gap context, lifted decision-gate plus review-floor caution visibility, the navigation/not-new-evidence boundary, the scorecard-sourced gate boundary, and project-local scratch hygiene directly instead of inferring them only from totals plus prose.",
        "",
    ]
    payload = {
        "suite_status": "pass",
        "valid_evidence_scope": ptls.LANE_SUMMARY_VALID_EVIDENCE_SCOPE,
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
        "fixture_root": str(FIXTURE_ROOT.relative_to(BASE)),
        "report_path": str(OUT_DIR.relative_to(BASE)),
        "scratch": {
            "tmp_parent": str(tmp_parent),
            "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
            "tmp_parent_cleared_before_fixture_run": True,
        },
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
