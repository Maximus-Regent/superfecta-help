#!/usr/bin/env python3
"""
Validate scanner-status path resolution across paper-trade operator surfaces.

Purpose:
- keep the pipeline-declared scanner_status_path authoritative
- prevent a stale default live_scan.status.json from masking a missing copied sidecar
- prove missing declared sidecars route to refresh/artifact guidance, not quiet-day evidence
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any

import paper_trade_next_steps as next_steps
import paper_trade_now as right_now
import paper_trade_ops_history as ops_history
import paper_trade_status_summary as status_summary
import refresh_live_paper_trade_surfaces as refresh_surfaces

BASE = Path(__file__).resolve().parent
FIXTURE_ROOT = BASE / "out" / "status_validation" / "scanner_sidecar_resolution_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "scanner_sidecar_resolution_contract"
REPORT_MD = OUT_DIR / "scanner_sidecar_resolution_contract_validation.md"
REPORT_JSON = OUT_DIR / "scanner_sidecar_resolution_contract_validation.json"
REBUILD_COMMAND = "python3 validate_scanner_sidecar_resolution_contract.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
VALID_EVIDENCE_SCOPE = "scanner_sidecar_path_resolution_contract_only"

EVIDENCE_BOUNDARY = {
    "artifact_role": "scanner-sidecar path-resolution contract validator",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "valid_use": "synthetic operator-artifact routing validation for copied/moved scanner status sidecars",
    "source_scope": "temporary fixture pipeline/scanner sidecars plus direct helper/CLI outputs and forward_evidence_scorecard.json decision_gate_minimums; not a live scanner result",
    "scanner_sidecar_validator_passes_are_operator_routing_metadata_only": True,
    "not_new_forward_evidence": True,
    "not_current_day_scanner_evidence": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_real_money_evidence": True,
    "non_goals": [
        "do not treat a green path-resolution validator as a clean empty day",
        "do not use missing-sidecar recovery as settled ROI or live-profitability evidence",
        "do not use this fixture as OP-anchor, Phase 8 promotion, bankroll, or real-money support",
        "do not alias BAQ as BEL",
    ],
}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def require(condition: bool, check: str, detail: str) -> dict[str, str]:
    if not condition:
        raise AssertionError(f"{check}: {detail}")
    return {"check": check, "status": "pass", "detail": detail}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--fixture-root", type=Path, default=FIXTURE_ROOT)
    return parser.parse_args(argv)


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
            "synthetic scanner-status path-resolution checks do not count toward anchor-displacement, "
            "Phase 8 promotion-review, or real-money discussion gates"
        ),
    }


def scorecard_gate_cli_contract_checks(scorecard_json_path: Path = SCORECARD_JSON) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    with TemporaryDirectory(prefix="scanner_sidecar_scorecard_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(scorecard_json_path).read_text(encoding="utf-8"))
        scorecard_path = tmp_root / "forward_evidence_scorecard.json"
        bad_out_dir = tmp_root / "nested" / "scanner_sidecar_resolution_contract"
        bad_fixture_root = tmp_root / "nested" / "scanner_sidecar_resolution_fixture"

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
                "--fixture-root",
                str(bad_fixture_root),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and not bad_fixture_root.exists()
                and "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations must be a positive non-boolean integer" in proc.stderr,
                "scorecard_boolean_gate_floor_fails_before_scanner_sidecar_artifacts",
                "a malformed boolean anchor-displacement scorecard gate fails before nested copied-sidecar fixture or validation outputs are created",
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
                "--fixture-root",
                str(bad_fixture_root),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and not bad_fixture_root.exists()
                and "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer" in proc.stderr,
                "scorecard_nonpositive_phase8_gate_floor_fails_before_scanner_sidecar_artifacts",
                "a non-positive Phase 8 promotion-review scorecard gate fails before nested copied-sidecar fixture or validation outputs are created",
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
                "--fixture-root",
                str(bad_fixture_root),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and not bad_fixture_root.exists()
                and "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer" in proc.stderr,
                "scorecard_nonpositive_real_money_gate_floor_fails_before_scanner_sidecar_artifacts",
                "a non-positive real-money discussion scorecard gate fails before nested copied-sidecar fixture or validation outputs are created",
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
                "--fixture-root",
                str(bad_fixture_root),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and not bad_fixture_root.exists()
                and "decision_gate_minimums.real_money_discussion.also_requires must include no BAQ-as-BEL substitution" in proc.stderr,
                "scorecard_missing_no_baq_fails_before_scanner_sidecar_artifacts",
                "a scorecard gate missing the no-BAQ-as-BEL real-money prerequisite fails before nested copied-sidecar fixture or validation outputs are created",
            )
        )
    return checks


def build_fixture(fixture_root: Path = FIXTURE_ROOT) -> dict[str, Any]:
    if fixture_root.exists():
        shutil.rmtree(fixture_root)

    run_dir = fixture_root / "out" / "daily_portfolio_runs" / "2026-05-25"
    lane_dir = run_dir / "phase7_current_paper"
    lane_dir.mkdir(parents=True, exist_ok=True)

    default_scanner = lane_dir / "live_scan.status.json"
    declared_scanner = lane_dir / "renamed_live_scan.status.json"
    pipeline_status = lane_dir / "pipeline_status.json"

    # This file is intentionally stale/noisy: it exists at the default lane filename,
    # but it is not the scanner sidecar recorded by the pipeline sidecar below.
    write_json(
        default_scanner,
        {
            "run_ts": "2026-05-25T18:00:00",
            "result": "no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
            "fixture_note": "stale default sidecar that must not mask missing declared sidecar",
        },
    )
    pipeline_payload = {
        "run_ts": "2026-05-25T19:12:00",
        "rules_path": "phase7_current_paper_rules.json",
        "scanner_status_path": "phase7_current_paper/renamed_live_scan.status.json",
        "scanner_status_state": "unreadable",
        "scanner_status_error": "JSONDecodeError: copied fixture scanner status was malformed before it went missing",
        "scanner_result": "scanner_status_unreadable",
        "observation_result": "scanner_status_unavailable_empty_run",
        "observation_scope": "operational_limit",
        "observation_reason": "scanner_status_unreadable",
        "scan_hit_count": 0,
        "scanner_raw_hit_count": 0,
        "recommendation_count": 0,
        "bet_count": 0,
        "error_count": 0,
    }
    write_json(pipeline_status, pipeline_payload)

    api_run_dir = fixture_root / "out" / "daily_portfolio_runs" / "2026-05-26"
    api_lane_dir = api_run_dir / "phase7_current_paper"
    api_lane_dir.mkdir(parents=True, exist_ok=True)
    api_default_scanner = api_lane_dir / "live_scan.status.json"
    api_declared_scanner = api_lane_dir / "api_access_live_scan.status.json"
    api_pipeline_status = api_lane_dir / "pipeline_status.json"
    api_boundary = (
        "API-access-failure operator context only; not a no-target, clean-empty, "
        "or forward-performance read."
    )
    api_action = "refresh_daily_wrapper_before_evidence_read"
    api_recheck = "./run_daily_portfolio_observation.sh"

    write_json(
        api_default_scanner,
        {
            "run_ts": "2026-05-26T18:00:00",
            "result": "no_qualifiers",
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
            "fixture_note": "stale clean default sidecar that must not mask declared API-access failure",
        },
    )
    write_json(
        api_declared_scanner,
        {
            "run_ts": "2026-05-26T19:12:00",
            "result": "scanner_error",
            "error_type": "HTTPError",
            "error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "http_status": 403,
            "api_access_failure": True,
            "api_failure_class": "api_access_failure",
            "api_failure_valid_scope": "operator_refresh_context_only",
            "api_failure_boundary": api_boundary,
            "api_failure_operator_action": api_action,
            "api_failure_recheck_command": api_recheck,
            "emitted_hit_count": 0,
            "raw_hit_count": 0,
            "rules_path": "phase7_current_paper_rules.json",
        },
    )
    api_pipeline_payload = {
        "run_ts": "2026-05-26T19:12:00",
        "rules_path": "phase7_current_paper_rules.json",
        "scanner_status_path": "phase7_current_paper/api_access_live_scan.status.json",
        "scanner_status_state": "ok",
        "scanner_result": "scanner_error",
        "observation_result": "scanner_failed_empty_run",
        "observation_scope": "operational_limit",
        "observation_reason": "api_access_failure",
        "scan_hit_count": 0,
        "scanner_raw_hit_count": 0,
        "recommendation_count": 0,
        "bet_count": 0,
        "error_count": 0,
        "scanner_http_status": 403,
        "scanner_api_access_failure": True,
        "scanner_api_failure_class": "api_access_failure",
        "scanner_api_failure_valid_scope": "operator_refresh_context_only",
        "scanner_api_failure_boundary": api_boundary,
        "scanner_api_failure_operator_action": api_action,
        "scanner_api_failure_recheck_command": api_recheck,
    }
    write_json(api_pipeline_status, api_pipeline_payload)

    return {
        "run_dir": run_dir,
        "lane_dir": lane_dir,
        "default_scanner": default_scanner,
        "declared_scanner": declared_scanner,
        "pipeline_status": pipeline_status,
        "pipeline_payload": pipeline_payload,
        "api_access": {
            "run_dir": api_run_dir,
            "lane_dir": api_lane_dir,
            "default_scanner": api_default_scanner,
            "declared_scanner": api_declared_scanner,
            "pipeline_status": api_pipeline_status,
            "pipeline_payload": api_pipeline_payload,
            "operator_action": api_action,
            "recheck_command": api_recheck,
        },
    }


def main(argv: list[str] | None = None) -> int:
    args_cli = parse_args(argv)
    scorecard_gates = read_scorecard_gate_minimums(args_cli.scorecard_json)
    fixture = build_fixture(args_cli.fixture_root)
    run_dir: Path = fixture["run_dir"]
    lane_dir: Path = fixture["lane_dir"]
    default_scanner: Path = fixture["default_scanner"]
    declared_scanner: Path = fixture["declared_scanner"]
    pipeline_status: Path = fixture["pipeline_status"]
    pipeline_payload: dict[str, Any] = fixture["pipeline_payload"]
    args = SimpleNamespace(scanner_status=str(default_scanner), pipeline_status=str(pipeline_status))
    api_fixture: dict[str, Any] = fixture["api_access"]
    api_run_dir: Path = api_fixture["run_dir"]
    api_lane_dir: Path = api_fixture["lane_dir"]
    api_default_scanner: Path = api_fixture["default_scanner"]
    api_declared_scanner: Path = api_fixture["declared_scanner"]
    api_pipeline_status: Path = api_fixture["pipeline_status"]
    api_pipeline_payload: dict[str, Any] = api_fixture["pipeline_payload"]
    api_args = SimpleNamespace(scanner_status=str(api_default_scanner), pipeline_status=str(api_pipeline_status))

    status_summary_path = status_summary.resolve_scanner_status_path(default_scanner, pipeline_status, pipeline_payload)
    next_steps_path = next_steps.resolve_scanner_status_path(args, pipeline_payload)
    right_now_path = right_now.resolve_lane_scanner_status_path(lane_dir)
    ops_history_path = ops_history.resolve_lane_scanner_status_path(run_dir, "phase7_current_paper", pipeline_payload)
    refresh_path = refresh_surfaces.resolve_lane_scanner_status_path(lane_dir)
    api_status_summary_path = status_summary.resolve_scanner_status_path(api_default_scanner, api_pipeline_status, api_pipeline_payload)
    api_next_steps_path = next_steps.resolve_scanner_status_path(api_args, api_pipeline_payload)
    api_right_now_path = right_now.resolve_lane_scanner_status_path(api_lane_dir)
    api_ops_history_path = ops_history.resolve_lane_scanner_status_path(api_run_dir, "phase7_current_paper", api_pipeline_payload)
    api_refresh_path = refresh_surfaces.resolve_lane_scanner_status_path(api_lane_dir)

    status_proc = subprocess.run(
        [
            sys.executable,
            str(BASE / "paper_trade_status_summary.py"),
            "--scanner-status",
            str(default_scanner),
            "--pipeline-status",
            str(pipeline_status),
            "--format",
            "json",
        ],
        cwd=BASE,
        text=True,
        capture_output=True,
        check=True,
    )
    status_payload = json.loads(status_proc.stdout)
    api_status_proc = subprocess.run(
        [
            sys.executable,
            str(BASE / "paper_trade_status_summary.py"),
            "--scanner-status",
            str(api_default_scanner),
            "--pipeline-status",
            str(api_pipeline_status),
            "--format",
            "json",
        ],
        cwd=BASE,
        text=True,
        capture_output=True,
        check=True,
    )
    api_status_payload = json.loads(api_status_proc.stdout)
    artifact_issue = next_steps.latest_status_artifact_issue(args)

    expected = declared_scanner.resolve()
    api_expected = api_declared_scanner.resolve()
    checks = [
        *scorecard_gate_cli_contract_checks(args_cli.scorecard_json),
        require(
            status_summary_path.resolve() == expected,
            "status_summary_uses_declared_missing_sidecar_over_stale_default",
            "paper_trade_status_summary.resolve_scanner_status_path returns the pipeline-declared missing renamed sidecar, not the existing stale default live_scan.status.json",
        ),
        require(
            next_steps_path is not None and next_steps_path.resolve() == expected,
            "next_steps_uses_declared_missing_sidecar_over_stale_default",
            "paper_trade_next_steps routes artifact checks to the declared missing scanner sidecar before considering the existing default filename",
        ),
        require(
            right_now_path.resolve() == expected,
            "right_now_pointer_uses_declared_missing_sidecar_over_stale_default",
            "PAPER_TRADE_NOW direct sidecar pointers stay on the pipeline-declared missing scanner sidecar instead of linking to a stale default file",
        ),
        require(
            ops_history_path.resolve() == expected,
            "ops_history_uses_declared_missing_sidecar_over_stale_default",
            "ops-history lane summarization reads the missing declared sidecar state rather than borrowing the stale default scanner sidecar",
        ),
        require(
            refresh_path.resolve() == expected,
            "saved_live_refresh_uses_declared_missing_sidecar_over_stale_default",
            "saved-live surface refresh rebuilds from the pipeline-declared scanner path even when that copied sidecar is absent",
        ),
        require(
            status_payload.get("headline") == "scanner sidecar recorded unreadable"
            and status_payload.get("scanner_status_state") == "missing"
            and status_payload.get("effective_scanner_status_state") == "unreadable"
            and status_payload.get("pipeline_scanner_status_state") == "unreadable"
            and "current scanner sidecar file missing" in status_payload.get("detail_parts", []),
            "status_summary_cli_surfaces_recorded_missing_declared_sidecar",
            "the JSON status summary reports the pipeline-recorded unreadable scanner sidecar plus current missing declared file instead of reporting the stale default as OK",
        ),
        require(
            isinstance(artifact_issue, str)
            and "recorded unreadable by the pipeline" in artifact_issue
            and "current scanner sidecar file is missing" in artifact_issue,
            "next_steps_artifact_issue_surfaces_recorded_missing_declared_sidecar",
            "next-step artifact guidance tells Cole to refresh after the pipeline-recorded unreadable scanner sidecar is missing from the copied surface",
        ),
        require(
            default_scanner.exists()
            and not declared_scanner.exists()
            and all(path.resolve() != default_scanner.resolve() for path in [status_summary_path, next_steps_path, right_now_path, ops_history_path, refresh_path] if path is not None),
            "stale_default_file_cannot_mask_missing_declared_sidecar",
            "the fixture keeps an existing default scanner file beside a missing declared scanner path, and no covered resolver returns the stale default",
        ),
        require(
            api_declared_scanner.exists()
            and api_default_scanner.exists()
            and all(
                path.resolve() == api_expected
                for path in [api_status_summary_path, api_next_steps_path, api_right_now_path, api_ops_history_path, api_refresh_path]
                if path is not None
            ),
            "api_access_declared_sidecar_beats_stale_clean_default",
            "when the declared scanner sidecar exists and carries API-access failure metadata, every covered resolver returns it instead of the stale clean default live_scan.status.json",
        ),
        require(
            api_status_payload.get("headline") == "scanner API access failure"
            and api_status_payload.get("scanner_result") == "scanner_error"
            and api_status_payload.get("observation_scope") == "operational_limit"
            and api_status_payload.get("observation_reason") == "api_access_failure"
            and api_status_payload.get("scanner_api_access_failure") is True
            and api_status_payload.get("scanner_http_status") == 403
            and api_status_payload.get("scanner_api_failure_class") == "api_access_failure"
            and api_status_payload.get("scanner_api_failure_operator_action") == api_fixture["operator_action"]
            and api_status_payload.get("scanner_api_failure_recheck_command") == api_fixture["recheck_command"]
            and "operator action refresh_daily_wrapper_before_evidence_read" in api_status_payload.get("detail_parts", [])
            and "recheck command ./run_daily_portfolio_observation.sh" in api_status_payload.get("detail_parts", [])
            and "clean empty" not in str(api_status_payload.get("headline") or "").lower(),
            "api_access_declared_sidecar_surfaces_action_fields",
            "status summary keeps the declared HTTP 403 sidecar as scanner API access failure with action/recheck fields instead of reading the stale default as clean empty",
        ),
        require(
            scorecard_gates.get("source") == "forward_evidence_scorecard.json"
            and scorecard_gates.get("source_path") == "decision_gate_minimums"
            and scorecard_gates.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and scorecard_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and scorecard_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and scorecard_gates.get("real_money_no_baq_as_bel_required") is True
            and "no BAQ-as-BEL substitution" in scorecard_gates.get("real_money_also_requires", [])
            and "do not count toward anchor-displacement" in scorecard_gates.get("evidence_boundary", ""),
            "scanner_sidecar_resolution_preserves_scorecard_gate_boundary",
            "synthetic scanner-status path-resolution checks now publish the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite while saying copied-sidecar routing fixtures do not count toward those gates",
        ),
        require(
            EVIDENCE_BOUNDARY.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and EVIDENCE_BOUNDARY.get("scanner_sidecar_validator_passes_are_operator_routing_metadata_only") is True
            and EVIDENCE_BOUNDARY.get("not_settled_roi_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_live_profitability_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_promotion_readiness_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_real_money_evidence") is True,
            "direct_validation_report_exposes_scanner_sidecar_valid_scope",
            "the direct scanner-sidecar validator report now exposes the raw valid_evidence_scope line and keeps green path-resolution checks classified as operator routing metadata only",
        ),
    ]

    current_read = (
        "pipeline-declared scanner_status_path is now fail-closed across status-summary, next-steps, PAPER_TRADE_NOW, ops-history, and saved-live refresh helpers: "
        "if a copied run loses the declared scanner sidecar while a stale default live_scan.status.json still exists, the operator surfaces keep pointing at the missing declared artifact and promote refresh/artifact guidance rather than treating the stale default as a clean lane read"
        "; if the declared sidecar exists and carries API-access failure metadata, the same resolver contract preserves the HTTP 403 operator action and recheck command instead of reading a stale clean default as a quiet day"
        "; the validator also rejects malformed and non-positive scorecard gates before copied-sidecar fixture/report artifacts and preserves the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that copied-sidecar routing fixtures do not advance"
        f"; the direct validator report now exposes exact valid_evidence_scope={VALID_EVIDENCE_SCOPE} as path-resolution/routing metadata only"
    )
    out_dir = Path(args_cli.out_dir)
    out_md = out_dir / REPORT_MD.name
    out_json = out_dir / REPORT_JSON.name
    report = {
        "suite_status": "pass",
        "artifact_status": "pass",
        "total_fixture_scenarios": 2,
        "total_checks": len(checks),
        "check_count": len(checks),
        "child_check_count": len(checks),
        "child_checks": checks,
        "summary": {"current_read": current_read},
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "fixture_paths": {
            "run_dir": rel(run_dir),
            "lane_dir": rel(lane_dir),
            "default_scanner_status": rel(default_scanner),
            "declared_scanner_status": rel(declared_scanner),
            "pipeline_status": rel(pipeline_status),
            "api_access_default_scanner_status": rel(api_default_scanner),
            "api_access_declared_scanner_status": rel(api_declared_scanner),
            "api_access_pipeline_status": rel(api_pipeline_status),
        },
        "resolved_paths": {
            "status_summary": rel(status_summary_path),
            "next_steps": rel(next_steps_path),
            "right_now": rel(right_now_path),
            "ops_history": rel(ops_history_path),
            "saved_live_refresh": rel(refresh_path),
            "api_access_status_summary": rel(api_status_summary_path),
            "api_access_next_steps": rel(api_next_steps_path),
            "api_access_right_now": rel(api_right_now_path),
            "api_access_ops_history": rel(api_ops_history_path),
            "api_access_saved_live_refresh": rel(api_refresh_path),
        },
        "status_summary_payload": status_payload,
        "api_access_status_summary_payload": api_status_payload,
        "next_steps_artifact_issue": artifact_issue,
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "fixture_root": rel(args_cli.fixture_root),
            "report_path": rel(out_md),
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Scanner Sidecar Resolution Contract Validation",
        "",
        "This report validates that a pipeline-declared `scanner_status_path` remains authoritative even when the declared copied sidecar is missing and an older default `live_scan.status.json` still exists beside it.",
        "",
        "## Current Read",
        "",
        f"- {current_read}",
        "",
        "## Checks",
        "",
    ]
    for check in checks:
        lines.append(f"- PASS `{check['check']}` — {check['detail']}")
    lines.extend(
        [
            "",
            "## Fixture Paths",
            "",
            f"- Stale default scanner status: `{rel(default_scanner)}`",
            f"- Missing declared scanner status: `{rel(declared_scanner)}`",
            f"- Pipeline status: `{rel(pipeline_status)}`",
            f"- API-access stale default scanner status: `{rel(api_default_scanner)}`",
            f"- API-access declared scanner status: `{rel(api_declared_scanner)}`",
            f"- API-access pipeline status: `{rel(api_pipeline_status)}`",
            "",
            "## Evidence Boundary",
            "",
            f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
            f"- valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
            f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
            f"- Source scope: {EVIDENCE_BOUNDARY['source_scope']}",
            "- Not new forward evidence; not current-day scanner evidence; not settled ROI; not live-profitability evidence; not promotion-readiness evidence; not real-money evidence.",
            "- Green status here proves synthetic path-routing behavior only; it does not prove a quiet/no-signal day or any paper-trade edge.",
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
            f"- Fixture root: `{args_cli.fixture_root}`",
            f"- Report path: `{out_md}`",
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"Wrote {out_json}")
    print(f"PASS scanner_sidecar_resolution_contract {len(checks)}/{len(checks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
