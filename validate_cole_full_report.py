#!/usr/bin/env python3
"""
Validation for COLE_FULL_REPORT_2026-04-15.md.

Purpose:
- keep the main narrative report aligned with the frozen evaluation standard
- ensure historical selector-scoring improvements stay distinct from the current frozen benchmark
- pin the report's current deployment posture to the same anchor / paper / shadow / method-family reads used elsewhere
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

BASE = Path(__file__).resolve().parent
REPORT = BASE / "COLE_FULL_REPORT_2026-04-15.md"
PORTFOLIO_CSV = BASE / "portfolio_decision_card.csv"
METHOD_CSV = BASE / "method_family_decision_card.csv"
SCORECARD_CSV = BASE / "forward_evidence_scorecard.csv"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
OUT_DIR = BASE / "out" / "status_validation" / "cole_full_report"
OUT_MD = OUT_DIR / "cole_full_report_validation.md"
OUT_JSON = OUT_DIR / "cole_full_report_validation.json"
REBUILD_COMMAND = "python3 validate_cole_full_report.py"
EXPECTED_REBUILD_ORDER_COMMANDS = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]


def load_csv_map(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {str(row[key]): row for row in rows}


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "pass", "detail": detail}


def require_positive_non_bool_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{field_name} must be a positive non-boolean integer")
    return value


def require_scorecard_decision_gate_minimums(
    scorecard_json: dict[str, Any],
    source_name: str,
) -> dict[str, Any]:
    gates = scorecard_json.get("decision_gate_minimums")
    if not isinstance(gates, dict):
        raise AssertionError(f"{source_name} is missing decision_gate_minimums")

    anchor = gates.get("anchor_displacement")
    phase8 = gates.get("phase8_promotion_review")
    real_money = gates.get("real_money_discussion")
    if not all(isinstance(item, dict) for item in (anchor, phase8, real_money)):
        raise AssertionError(f"{source_name} decision_gate_minimums is incomplete")

    anchor_min = require_positive_non_bool_int(
        anchor.get("min_roi_complete_settled_observations"),
        "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
    )
    phase8_min = require_positive_non_bool_int(
        phase8.get("min_roi_complete_settled_observations"),
        "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
    )
    real_money_min = require_positive_non_bool_int(
        real_money.get("min_total_settled_observations_with_usable_roi"),
        "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
    )
    also_requires = real_money.get("also_requires")
    if not isinstance(also_requires, list) or any(not isinstance(item, str) for item in also_requires):
        raise AssertionError("decision_gate_minimums.real_money_discussion.also_requires must be a string list")
    if "no BAQ-as-BEL substitution" not in also_requires:
        raise AssertionError(
            "decision_gate_minimums.real_money_discussion.also_requires must include no BAQ-as-BEL substitution"
        )

    return {
        "source": source_name,
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_no_baq_as_bel_required": True,
    }


def require_current_evidence_rebuild_contract(current_evidence: dict[str, Any]) -> dict[str, Any]:
    contract = current_evidence.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise AssertionError("current_evidence_summary.json must publish rebuild_validation_contract as an object")
    upstream_refresh_order = contract.get("upstream_refresh_order")
    if not isinstance(upstream_refresh_order, list) or len(upstream_refresh_order) != len(EXPECTED_REBUILD_ORDER_COMMANDS):
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract must publish the three-step upstream_refresh_order")

    commands: list[str] = []
    for expected_order, step in enumerate(upstream_refresh_order, start=1):
        if not isinstance(step, dict):
            raise AssertionError("current_evidence_summary.json upstream_refresh_order steps must be objects")
        if step.get("order") != expected_order:
            raise AssertionError("current_evidence_summary.json upstream_refresh_order order values drifted")
        command = step.get("command")
        if not isinstance(command, str):
            raise AssertionError("current_evidence_summary.json upstream_refresh_order commands must be strings")
        commands.append(command)

    if commands != EXPECTED_REBUILD_ORDER_COMMANDS:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract upstream order drifted")
    if contract.get("prerequisite_rebuild_command") != EXPECTED_REBUILD_ORDER_COMMANDS[0]:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract prerequisite command drifted")
    if contract.get("rebuild_command") != EXPECTED_REBUILD_ORDER_COMMANDS[1]:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract rebuild command drifted")
    if contract.get("direct_validation_command") != EXPECTED_REBUILD_ORDER_COMMANDS[2]:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract direct validator command drifted")
    if contract.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is not True:
        raise AssertionError("rebuild_validation_contract must require settlement-audit refresh before bridge rebuilds")
    if contract.get("requires_source_consistency_before_quoting_current_totals") is not True:
        raise AssertionError("rebuild_validation_contract must require source consistency before current totals are quoted")
    if contract.get("upstream_refresh_order_is_provenance_metadata_only") is not True:
        raise AssertionError("rebuild_validation_contract upstream order must be provenance metadata only")
    if contract.get("not_settled_roi_or_real_money_evidence") is not True:
        raise AssertionError("rebuild_validation_contract must not be settled ROI or real-money evidence")

    return {
        "source": CURRENT_EVIDENCE_JSON.name,
        "source_path": "rebuild_validation_contract",
        "upstream_refresh_order": commands,
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
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Cole's full report")
    parser.add_argument("--current-evidence-json", type=Path, default=CURRENT_EVIDENCE_JSON)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def current_bridge_cli_contract_checks(
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="full_report_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json_path).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "cole_full_report_validation"
        missing_contract_payload = json.loads(json.dumps(base_payload))
        missing_contract_payload.pop("rebuild_validation_contract", None)
        current_evidence_path.write_text(json.dumps(missing_contract_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--current-evidence-json",
                str(current_evidence_path),
                "--out-dir",
                str(missing_contract_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not missing_contract_out_dir.exists()
                and "current_evidence_summary.json must publish rebuild_validation_contract as an object"
                in proc.stderr,
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "validate_cole_full_report.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial full-report validation artifacts",
            )
        )

        weakened_contract_out_dir = tmp_root / "weakened" / "cole_full_report_validation"
        weakened_contract_payload = json.loads(json.dumps(base_payload))
        weakened_contract_payload["rebuild_validation_contract"][
            "upstream_refresh_order_is_provenance_metadata_only"
        ] = False
        current_evidence_path.write_text(json.dumps(weakened_contract_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--current-evidence-json",
                str(current_evidence_path),
                "--out-dir",
                str(weakened_contract_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not weakened_contract_out_dir.exists()
                and "rebuild_validation_contract upstream order must be provenance metadata only"
                in proc.stderr,
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "validate_cole_full_report.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial full-report validation artifacts",
            )
        )

    return checks


def scorecard_cli_gate_contract_checks(
    scorecard_json_path: Path = SCORECARD_JSON,
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> list[dict[str, Any]]:
    with TemporaryDirectory(prefix="full_report_scorecard_gates_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(scorecard_json_path).read_text(encoding="utf-8"))
        errors: list[str] = []
        cases = [
            (
                "boolean_anchor",
                lambda payload: payload["decision_gate_minimums"]["anchor_displacement"].__setitem__(
                    "min_roi_complete_settled_observations",
                    True,
                ),
                "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations must be a positive non-boolean integer",
            ),
            (
                "nonpositive_phase8",
                lambda payload: payload["decision_gate_minimums"]["phase8_promotion_review"].__setitem__(
                    "min_roi_complete_settled_observations",
                    0,
                ),
                "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer",
            ),
            (
                "nonpositive_real_money",
                lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                    "min_total_settled_observations_with_usable_roi",
                    0,
                ),
                "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer",
            ),
            (
                "missing_no_baq",
                lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                    "also_requires",
                    [
                        item
                        for item in payload["decision_gate_minimums"]["real_money_discussion"].get(
                            "also_requires",
                            [],
                        )
                        if item != "no BAQ-as-BEL substitution"
                    ],
                ),
                "decision_gate_minimums.real_money_discussion.also_requires must include no BAQ-as-BEL substitution",
            ),
        ]

        for case_name, mutate, expected_error in cases:
            payload = json.loads(json.dumps(base_payload))
            mutate(payload)
            scorecard_path = tmp_root / f"{case_name}_scorecard.json"
            out_dir = tmp_root / case_name / "cole_full_report_validation"
            scorecard_path.write_text(json.dumps(payload), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--scorecard-json",
                    str(scorecard_path),
                    "--current-evidence-json",
                    str(current_evidence_json_path),
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=BASE,
                capture_output=True,
                text=True,
            )
            combined = f"{proc.stdout}\n{proc.stderr}"
            if proc.returncode == 0:
                errors.append(f"{case_name}: malformed scorecard was accepted")
            if out_dir.exists():
                errors.append(f"{case_name}: output directory was created before scorecard gate validation failed")
            if expected_error not in combined:
                errors.append(f"{case_name}: expected error text was missing")

    return [
        require(
            not errors,
            "malformed_scorecard_gate_floors_fail_before_artifacts",
            "validate_cole_full_report.py rejects boolean anchor floors, non-positive Phase 8 / real-money floors, and a missing no-BAQ-as-BEL prerequisite before creating nested full-report validation artifacts",
        )
    ]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    text = REPORT.read_text(encoding="utf-8")
    portfolio = load_csv_map(PORTFOLIO_CSV, "method_id")
    method_family = load_csv_map(METHOD_CSV, "family_id")
    scorecard = load_csv_map(SCORECARD_CSV, "rule_id")
    scorecard_json_path = Path(args.scorecard_json)
    scorecard_json = json.loads(scorecard_json_path.read_text(encoding="utf-8"))
    scorecard_gate_read = require_scorecard_decision_gate_minimums(
        scorecard_json,
        scorecard_json_path.name,
    )
    current_evidence = json.loads(Path(args.current_evidence_json).read_text(encoding="utf-8"))
    rebuild_contract_read = require_current_evidence_rebuild_contract(current_evidence)

    anchor = scorecard["OP_DURABLE_K7"]
    phase7 = portfolio["phase7_live_portfolio"]
    selector = portfolio["train_only_selector"]
    phase8 = portfolio["phase8_frozen_portfolio"]
    selective = method_family["selective_rule_path"]
    harville = method_family["harville_ranked"]
    xgboost = method_family["xgboost_residual"]
    current_primary = current_evidence["current_paper_status"]["primary"]
    rule_progress = {
        row["rule_id"]: row for row in current_primary["rule_progress"]
    }
    open_settlements = int(current_primary.get("open_settlements", 0) or 0)
    open_settlement_summary = current_primary["open_settlement_summary"]
    open_queue = current_primary.get("open_settlement_queue_by_rule")
    if not isinstance(open_queue, dict):
        raise AssertionError("current_paper_status.primary.open_settlement_queue_by_rule must be present")
    open_settlement_queue_state = str(open_queue.get("open_settlement_queue_state") or "").strip()
    open_settlement_context = str(open_queue.get("open_settlement_context") or "").strip()
    open_settlement_queue_read = str(open_queue.get("detail_read") or "").strip()
    expected_open_settlement_queue_state = "closed" if open_settlements == 0 else "open"
    if open_settlement_queue_state not in {"closed", "open"}:
        raise AssertionError("open_settlement_queue_state must be closed or open")
    if open_settlement_queue_state != expected_open_settlement_queue_state:
        raise AssertionError("open_settlement_queue_state must match primary open_settlements")
    if open_settlements == 0 and open_settlement_context != "no open primary settlement rows":
        raise AssertionError("closed settlement queue must use the source no-open-primary-rows context")
    if open_settlements > 0 and "open" not in open_settlement_context.lower():
        raise AssertionError("open settlement queue context must identify open rows")
    if "Open settlement queue by rule:" not in open_settlement_queue_read:
        raise AssertionError("detail_read must preserve the by-rule open settlement detail")
    if "Settlement queue state:" in open_settlement_queue_read:
        raise AssertionError("detail_read must not nest the settlement queue state wrapper")
    recommendation_context = current_primary["recommendation_context"]
    recommendation_read = str(recommendation_context.get("read") or "").strip()
    api_access_action_route_present = (
        "Sidecar action: refresh_daily_wrapper_before_evidence_read" in recommendation_read
        and "Recheck command: ./run_daily_portfolio_observation.sh" in recommendation_read
    )
    current_first_read = current_primary["first_read"]
    current_portfolio_review = current_primary["portfolio_review"]
    current_source_consistency = current_evidence["source_consistency"]
    source_consistency_label = "matched" if current_source_consistency["overall_match"] is True else "not matched"
    source_freshness = current_evidence["source_freshness"]
    requires_refresh = bool(source_freshness.get("requires_refresh_before_right_now_use"))
    source_freshness_label = "requires refresh before right-now use" if requires_refresh else "fresh for right-now use"
    combined_operator_route_label = (
        "requires refresh before right-now instruction or evidence use"
        if requires_refresh
        else "is fresh against the bridge reference date but still goes through operator read-gate routing before right-now instruction or evidence use"
    )
    operator_read_gate = (
        current_evidence.get("operator_read_gate")
        if isinstance(current_evidence.get("operator_read_gate"), dict)
        else {}
    )
    operator_read_gate_read = str(operator_read_gate.get("read") or "").strip()
    api_access_action_route_required = bool(
        operator_read_gate.get("has_api_access_failure_context")
        or operator_read_gate.get("has_scanner_failure_boundary")
        or operator_read_gate.get("has_stale_cache_fallback_context")
    )
    operator_read_gate_requires_refresh = bool(
        operator_read_gate.get("requires_refresh_before_evidence_read")
    )
    operator_read_gate_requires_refresh_label = (
        "true" if operator_read_gate_requires_refresh else "false"
    )
    operator_read_gate_json_read = {
        "source": CURRENT_EVIDENCE_JSON.name,
        "source_path": "operator_read_gate",
        "gate_status": operator_read_gate.get("gate_status"),
        "valid_use": operator_read_gate.get("valid_use"),
        "requires_refresh_before_evidence_read": operator_read_gate.get("requires_refresh_before_evidence_read"),
        "has_api_access_failure_context": operator_read_gate.get("has_api_access_failure_context"),
        "has_scanner_failure_boundary": operator_read_gate.get("has_scanner_failure_boundary"),
        "has_stale_cache_fallback_context": operator_read_gate.get("has_stale_cache_fallback_context"),
        "recommended_command": operator_read_gate.get("recommended_command"),
        "current_top_card_counts_as_no_target_evidence": operator_read_gate.get(
            "current_top_card_counts_as_no_target_evidence"
        ),
        "current_top_card_counts_as_clean_empty_evidence": operator_read_gate.get(
            "current_top_card_counts_as_clean_empty_evidence"
        ),
        "current_top_card_counts_as_bet_readiness_evidence": operator_read_gate.get(
            "current_top_card_counts_as_bet_readiness_evidence"
        ),
        "current_top_card_counts_as_settled_roi_evidence": operator_read_gate.get(
            "current_top_card_counts_as_settled_roi_evidence"
        ),
        "not_forward_performance_evidence": operator_read_gate.get("not_forward_performance_evidence"),
        "not_promotion_readiness_evidence": operator_read_gate.get("not_promotion_readiness_evidence"),
        "not_live_profitability_evidence": operator_read_gate.get("not_live_profitability_evidence"),
        "not_real_money_evidence": operator_read_gate.get("not_real_money_evidence"),
    }
    current_gate_minimums = (
        current_evidence.get("decision_gate_minimums")
        if isinstance(current_evidence.get("decision_gate_minimums"), dict)
        else {}
    )
    current_gate_top_card_values = (
        current_gate_minimums.get("top_card_values")
        if isinstance(current_gate_minimums.get("top_card_values"), dict)
        else {}
    )
    current_gate_scorecard_values = (
        current_gate_minimums.get("scorecard_values")
        if isinstance(current_gate_minimums.get("scorecard_values"), dict)
        else {}
    )
    current_gate_effective_values = (
        current_gate_minimums.get("effective_values")
        if isinstance(current_gate_minimums.get("effective_values"), dict)
        else {}
    )
    current_gate_threshold_sources = (
        current_gate_minimums.get("threshold_sources")
        if isinstance(current_gate_minimums.get("threshold_sources"), dict)
        else {}
    )
    current_roi_rows = (
        current_source_consistency.get("primary_roi_complete_settled_rows")
        if isinstance(current_source_consistency.get("primary_roi_complete_settled_rows"), dict)
        else {}
    )
    current_open_rows = (
        current_source_consistency.get("primary_open_settlement_rows")
        if isinstance(current_source_consistency.get("primary_open_settlement_rows"), dict)
        else {}
    )
    current_incomplete_rows = (
        current_source_consistency.get("primary_incomplete_settlement_rows")
        if isinstance(current_source_consistency.get("primary_incomplete_settlement_rows"), dict)
        else {}
    )
    current_roi_gap_rows = (
        current_source_consistency.get("primary_roi_gap_settlement_rows")
        if isinstance(current_source_consistency.get("primary_roi_gap_settlement_rows"), dict)
        else {}
    )
    scorecard_anchor_min = scorecard_gate_read["anchor_displacement_min_roi_complete_settled_observations"]
    scorecard_phase8_min = scorecard_gate_read["phase8_promotion_review_min_roi_complete_settled_observations"]
    scorecard_real_money_min = scorecard_gate_read[
        "real_money_discussion_min_total_settled_observations_with_usable_roi"
    ]
    scorecard_audit_route = (
        current_evidence.get("scorecard_audit_route")
        if isinstance(current_evidence.get("scorecard_audit_route"), dict)
        else {}
    )
    scorecard_audit_route_read = {
        "source": CURRENT_EVIDENCE_JSON.name,
        "source_path": "scorecard_audit_route",
        "markdown_path": scorecard_audit_route.get("markdown_path"),
        "json_path": scorecard_audit_route.get("json_path"),
        "validator_command": scorecard_audit_route.get("validator_command"),
        "gate_floor_source": scorecard_audit_route.get("gate_floor_source"),
        "gate_floor_snapshot": scorecard_audit_route.get("gate_floor_snapshot"),
        "valid_use": scorecard_audit_route.get("valid_use"),
        "artifacts_present": scorecard_audit_route.get("artifacts_present"),
        "not_forward_performance_evidence": scorecard_audit_route.get("not_forward_performance_evidence"),
        "not_settled_roi_evidence": scorecard_audit_route.get("not_settled_roi_evidence"),
        "not_promotion_readiness_evidence": scorecard_audit_route.get("not_promotion_readiness_evidence"),
        "not_live_profitability_evidence": scorecard_audit_route.get("not_live_profitability_evidence"),
        "not_bankroll_guidance": scorecard_audit_route.get("not_bankroll_guidance"),
        "not_real_money_evidence": scorecard_audit_route.get("not_real_money_evidence"),
        "route_read": scorecard_audit_route.get("route_read"),
    }
    current_bridge_json_read = {
        "source_consistency_overall_match": current_source_consistency.get("overall_match"),
        "primary_roi_complete_rows_match": (
            current_roi_rows.get("paper_trade_now")
            == current_roi_rows.get("settlement_audit")
            == current_roi_rows.get("settlement_csv_recomputed")
        ),
        "primary_open_rows_match": current_open_rows.get("paper_trade_now") == current_open_rows.get("settlement_audit"),
        "primary_incomplete_rows_match": (
            current_incomplete_rows.get("paper_trade_now") == current_incomplete_rows.get("settlement_audit")
        ),
        "primary_roi_gap_rows_match": current_roi_gap_rows.get("paper_trade_now") == current_roi_gap_rows.get("settlement_audit"),
        "source_freshness_state": source_freshness.get("right_now_freshness_state"),
        "source_freshness_state_valid": source_freshness.get("right_now_freshness_state_valid"),
        "requires_refresh_before_right_now_use": source_freshness.get("requires_refresh_before_right_now_use"),
        "requires_refresh_reason": source_freshness.get("requires_refresh_reason"),
        "decision_gate_source": current_gate_minimums.get("source_path"),
        "decision_gate_source_loaded": current_gate_minimums.get("source_loaded"),
        "anchor_displacement_min": current_gate_minimums.get(
            "anchor_displacement_min_roi_complete_settled_observations"
        ),
        "phase8_promotion_review_min": current_gate_minimums.get(
            "phase8_promotion_review_min_roi_complete_settled_observations"
        ),
        "real_money_discussion_min": current_gate_minimums.get(
            "real_money_discussion_min_total_settled_observations_with_usable_roi"
        ),
        "decision_gate_source_values_match_scorecard": current_gate_minimums.get("source_values_match_scorecard"),
        "decision_gate_effective_values_source": current_gate_minimums.get("effective_values_source"),
        "decision_gate_missing_top_card_fields": current_gate_minimums.get("missing_top_card_fields"),
        "decision_gate_mismatched_fields": current_gate_minimums.get("mismatched_fields"),
        "effective_anchor_displacement_min": current_gate_effective_values.get(
            "anchor_displacement_min_roi_complete_settled_observations"
        ),
        "effective_phase8_promotion_review_min": current_gate_effective_values.get(
            "phase8_promotion_review_min_roi_complete_settled_observations"
        ),
        "effective_real_money_discussion_min": current_gate_effective_values.get(
            "real_money_discussion_min_total_settled_observations_with_usable_roi"
        ),
        "top_card_anchor_displacement_min": current_gate_top_card_values.get(
            "anchor_displacement_min_roi_complete_settled_observations"
        ),
        "top_card_phase8_promotion_review_min": current_gate_top_card_values.get(
            "phase8_promotion_review_min_roi_complete_settled_observations"
        ),
        "top_card_real_money_discussion_min": current_gate_top_card_values.get(
            "real_money_discussion_min_total_settled_observations_with_usable_roi"
        ),
        "scorecard_anchor_displacement_min_from_bridge": current_gate_scorecard_values.get(
            "anchor_displacement_min_roi_complete_settled_observations"
        ),
        "scorecard_phase8_promotion_review_min_from_bridge": current_gate_scorecard_values.get(
            "phase8_promotion_review_min_roi_complete_settled_observations"
        ),
        "scorecard_real_money_discussion_min_from_bridge": current_gate_scorecard_values.get(
            "real_money_discussion_min_total_settled_observations_with_usable_roi"
        ),
        "decision_gate_threshold_sources": current_gate_threshold_sources,
        "scorecard_anchor_displacement_min": scorecard_anchor_min,
        "scorecard_phase8_promotion_review_min": scorecard_phase8_min,
        "scorecard_real_money_discussion_min": scorecard_real_money_min,
    }
    expected_source_freshness_summary_sentence = (
        "Its combined current-paper route across `operator_status_context`, `source_freshness.requires_refresh_before_right_now_use=true`, and `operator_read_gate.requires_refresh_before_evidence_read=true` means rerun `./run_daily_portfolio_observation.sh` before treating a wrapper-refresh, missing-output, or stale/API-failure saved best-action card as today's operator instruction or evidence; this is not OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence."
        if requires_refresh
        else (
            "Its combined current-paper route across `operator_status_context`, "
            f"`source_freshness.requires_refresh_before_right_now_use=false`, and "
            f"`operator_read_gate.requires_refresh_before_evidence_read={operator_read_gate_requires_refresh_label}` "
            "says the saved best-action card is fresh against the bridge reference date but still goes through "
            "operator-read-gate routing before instruction or evidence use; this is not OP-anchor proof, "
            "promotion readiness, live profitability, bankroll guidance, or real-money evidence."
        )
    )
    expected_source_freshness_bridge_sentence = (
        "The bridge uses the combined current-paper route: `operator_status_context`, `source_freshness.requires_refresh_before_right_now_use=true`, and `operator_read_gate.requires_refresh_before_evidence_read=true`; rerun `./run_daily_portfolio_observation.sh` before treating wrapper-refresh, missing-output, stale/API-failure `PAPER_TRADE_NOW`, or its best-action card as today's operator instruction or evidence."
        if requires_refresh
        else (
            "The bridge uses the combined current-paper route: `operator_status_context`, "
            f"`source_freshness.requires_refresh_before_right_now_use=false`, and "
            f"`operator_read_gate.requires_refresh_before_evidence_read={operator_read_gate_requires_refresh_label}`; "
            "the saved right-now source is fresh against the bridge reference date but still goes through "
            "operator read-gate routing before right-now instruction or evidence use."
        )
    )
    expected_source_freshness_repair_sentence = (
        "If `source_consistency.overall_match=false`, repair the top-card / audit / CSV mismatch before quoting current paper numbers from this report; then use the combined `operator_status_context` + `source_freshness` + `operator_read_gate` route before using the saved right-now card as current-day guidance or evidence."
        if requires_refresh
        else "If `source_consistency.overall_match=false`, repair the top-card / audit / CSV mismatch before quoting current paper numbers from this report; then use the combined `operator_status_context` + `source_freshness` + `operator_read_gate` route before using the saved right-now card as current-day guidance or evidence."
    )
    expected_operator_read_gate_bridge_sentence = (
        f"The bridge also publishes `operator_read_gate.requires_refresh_before_evidence_read="
        f"{operator_read_gate_requires_refresh_label}`: {operator_read_gate_read}"
    )

    expected_historical_line = (
        "- **Largest validated historical selector-scoring improvement:** walk-forward ROI improved from "
        "**+22.46%** to **+30.42%** with sqrt-dampened scoring, but that is a research-side improvement, "
        "**not** the current frozen deployment benchmark."
    )
    expected_selector_line = (
        f"- **Current honest selector benchmark:** still the **{selector['label']}** at "
        f"**{float(selector['wf_roi']):+.2f}% walk-forward** and **{float(selector['holdout_roi']):+.2f}% 2024-2025 holdout**, "
        f"which stays **{selector['role']}**."
    )
    expected_phase7_baseline_line = (
        "- **Best current paper-observation baseline:** still the **Phase 7 OP/CD rule-component basket**, "
        "with target cards confirmed only by daily preflight, not the Phase 8 expansion."
    )
    expected_phase7_line = (
        f"- **Best current holdout result:** **{float(phase7['holdout_roi']):+.2f}% ROI on {int(phase7['holdout_races'])} races** "
        "for the Phase 7 OP/CD rule-component basket, but that path was not smooth: "
        f"**2024 {float(phase7['holdout_2024_roi']):+.2f}% on {int(phase7['holdout_2024_races'])} races; "
        f"2025 {float(phase7['holdout_2025_roi']):+.2f}% on {int(phase7['holdout_2025_races'])} races**. "
        "Target-card availability still comes from daily preflight."
    )
    expected_phase8_line = (
        f"- **Phase 8 status:** still useful, but it stays **shadow-only**, because its 2024-2025 holdout is weaker at "
        f"**{float(phase8['holdout_roi']):+.2f}% on {int(phase8['holdout_races'])} races** and also uneven: "
        f"**2024 {float(phase8['holdout_2024_roi']):+.2f}% on {int(phase8['holdout_2024_races'])} races; "
        f"2025 {float(phase8['holdout_2025_roi']):+.2f}% on {int(phase8['holdout_2025_races'])} races**."
    )
    expected_method_line = (
        "- **Method-family verdict:** the **selective rule path** is still the only family that deserves paper-trade treatment. "
        "**Harville = benchmark only. XGBoost = research only.**"
    )
    expected_full_data_retrain_summary_line = (
        "- **Full-data XGBoost retrain caveat:** read `FULL_DATA_RETRAIN_ARTIFACTS.md` and run `python3 validate_full_data_retrain_artifacts.py` when checking the full-data retrain artifact or exact retrain/prediction commands; large RMSE / MAE gains are model-fit reproducibility context only, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence."
    )
    expected_full_data_retrain_section_line = (
        "For the separate full-data retrain artifact, use `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py` only as a model-fit reproducibility route. Large full-data RMSE / MAE gains and exact retrain/prediction commands are diagnostics, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence."
    )
    expected_paper_trade_evidence_status_line = (
        "- **Paper-trade evidence status:** the improved paper-trade stack is a workflow/reproducibility gain, not new forward evidence by itself; genuinely new forward evidence still requires settled paper trades and the downstream forward-check artifacts."
    )
    expected_evidence_scope_summary_line = (
        "- **Evidence-scope boundary:** only settled paper-trade rows with usable ROI coverage should change deployment posture; clean scans, open signals, historical replay rows, calibration-only summaries, or another odds-only rerun should not."
    )
    expected_decision_gate_source_line = (
        f"- **Decision-gate source:** `{SCORECARD_JSON.name}` `decision_gate_minimums` sets "
        f"`anchor_displacement={scorecard_anchor_min}`, `phase8_promotion_review={scorecard_phase8_min}`, "
        f"and `real_money_discussion={scorecard_real_money_min}`; these are future ROI-complete observation floors, not cleared gates."
    )
    expected_decision_gate_bridge_line = (
        f"Gate source: `{SCORECARD_JSON.name}` `decision_gate_minimums` sets "
        f"`anchor_displacement={scorecard_anchor_min}`, `phase8_promotion_review={scorecard_phase8_min}`, "
        f"and `real_money_discussion={scorecard_real_money_min}`; these are future ROI-complete observation floors, not cleared gates."
    )
    expected_rebuild_order_route_sentence = (
        "Rebuild order route: `current_evidence_summary.json.rebuild_validation_contract`; after scorecard/rules/signals/settlement-ledger byte changes, "
        "run `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*`; "
        "this is provenance/rebuild metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence."
    )
    expected_scorecard_audit_route_summary_line = (
        "- **Scorecard audit route:** `current_evidence_summary.json.scorecard_audit_route` points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to "
        "`SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py`; "
        "this is report-synchronization metadata only, not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence."
    )
    expected_scorecard_audit_route_bridge_sentence = (
        "Scorecard audit route: `current_evidence_summary.json.scorecard_audit_route` points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to "
        "`SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py`; "
        "this is report-synchronization metadata only, not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence."
    )
    expected_evidence_scope_ops_line = (
        "Only settled paper-trade rows with usable ROI coverage should change deployment posture; clean scans, open signals, historical replay rows, calibration-only summaries, or another odds-only rerun should not."
    )
    expected_open_row_summary_sentence = (
        f"Settlement queue state: `{open_settlement_queue_state}`; {open_settlement_context}; detail: "
        f"{open_settlement_queue_read} Latest recommendation-state context: {recommendation_read}"
    )
    expected_open_row_bridge_sentence = expected_open_row_summary_sentence
    queue_recommendation_context_label = "source-published settlement queue state plus recommendation-state context"
    suite_queue_context = (
        f"settlement queue state={open_settlement_queue_state} / context={open_settlement_context} remains workflow context "
        f"rather than a bet-ready ticket or forward-performance proof, with source detail_read={open_settlement_queue_read} "
        f"and latest recommendation-state context saying {recommendation_read}"
    )

    expected_current_evidence_summary_line = (
        "- **Current evidence bridge:** before quoting current paper totals, read `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json`; "
        f"the current bridge is source-consistent, primary paper is still **{current_first_read['current']}/{current_first_read['threshold']}** ROI-complete toward a first read and **{current_portfolio_review['current']}/{current_portfolio_review['threshold']}** toward broader review, "
        f"and the settled sample is **CD_CORE_K8-only** with **{rule_progress['OP_DURABLE_K7']['roi_complete_settled_rows']} OP_DURABLE_K7** ROI-complete rows. "
        f"{expected_source_freshness_summary_sentence} "
        f"{expected_operator_read_gate_bridge_sentence} "
        f"{expected_rebuild_order_route_sentence} "
        f"{expected_open_row_summary_sentence}"
    )
    expected_cross_family_caveat_summary_line = (
        "- **Direct cross-family caveat route:** when the question is whether the anchor / paper / watch shortlist still carries the current-paper caveat, read `CROSS_FAMILY_DECISION.md` and run `python3 validate_cross_family_decision.py`; stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green report validation are not OP-anchor proof or cross-family promotion evidence."
    )
    expected_cross_family_caveat_bridge_line = (
        "For the anchor / paper / watch shortlist specifically, use `CROSS_FAMILY_DECISION.md` and `validate_cross_family_decision.py` as the narrow current-paper caveat route: stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green report-surface validation do not count as OP-anchor proof or cross-family promotion evidence."
    )
    expected_current_evidence_bridge_lines = [
        "### Current evidence bridge for report updates",
        "For short Cole updates, use `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` as the bridge from frozen research posture to current paper-trade status before quoting `PAPER_TRADE_NOW`, ops-bucket/operator-status context, settlement-audit, or primary-ledger totals.",
        expected_decision_gate_bridge_line,
        f"The bridge currently says source consistency is {source_consistency_label} across the top card, audit, and primary settlement CSV; primary paper is still **{current_first_read['current']}/{current_first_read['threshold']}** ROI-complete toward a first statistical read and **{current_portfolio_review['current']}/{current_portfolio_review['threshold']}** toward broader review; `CD_CORE_K8` has **{rule_progress['CD_CORE_K8']['roi_complete_settled_rows']}** ROI-complete settled rows while `OP_DURABLE_K7` has **{rule_progress['OP_DURABLE_K7']['roi_complete_settled_rows']}**; and the current settled paper context is CD-only, so it should not be counted as OP-anchor forward evidence.",
        expected_rebuild_order_route_sentence,
        expected_source_freshness_bridge_sentence,
        expected_operator_read_gate_bridge_sentence,
        expected_scorecard_audit_route_bridge_sentence,
        expected_open_row_bridge_sentence,
        expected_source_freshness_repair_sentence,
    ]
    expected_guardrail_header = "## 2A) Method-family guardrail"
    expected_guardrail_intro = "This is intentionally separate from the selective-method ranking."
    expected_guardrail_rows = [
        f"| {selective['label']} | {selective['role']} | {float(selective['primary_metric']):+.2f}% holdout ROI on {int(selective['primary_sample'])} races; 2024 {float(phase7['holdout_2024_roi']):+.2f}% on {int(phase7['holdout_2024_races'])}, 2025 {float(phase7['holdout_2025_roi']):+.2f}% on {int(phase7['holdout_2025_races'])} | Only family here with positive current frozen holdout evidence plus a paper-trade observation path; `{selective['current_anchor']}` still anchors it, `{selective['primary_shadow']}` is the primary OP/CD paper-basket companion, and `{selective['secondary_shadow']}` remains the smaller same-family shadow challenger, but the recent path was uneven rather than smooth. |",
        f"| {harville['label']} | {harville['role']} | {float(harville['primary_metric']):+.2f}% broad ROI on {int(harville['primary_sample'])} races | Useful structural benchmark, but the large-sample ROI is still deeply negative, so it does not beat takeout. |",
        f"| {xgboost['label']} | {xgboost['role']} | {float(xgboost['primary_metric']):+.2f}% best ML betting ROI on {int(xgboost['primary_sample'])} races | Prediction quality improved a bit, but the betting case did not materially improve downstream. |",
    ]
    expected_guardrail_outro = (
        f"The right read is still layered: compare the serious selective contenders against each other, keep `{selective['current_anchor']}` / `{selective['primary_shadow']}` / `{selective['secondary_shadow']}` in their current anchor / paper-companion / shadow-challenger order, keep Harville benchmark-only, and keep the current odds-only XGBoost path parked outside the paper-decision lane unless its evidence class changes materially."
    )
    expected_guardrail_replay_caution = (
        "The broader selective-family secondary lines elsewhere in the repo are replay context on walk-forward test years, not extra train-only validation."
    )
    expected_rule_split_lines = [
        f"- **OP_DURABLE_K7**: mixed holdout, but on the largest OP holdout sample (**2024 {float(anchor['holdout_2024_roi']):+.2f}% on {int(anchor['holdout_2024_races'])} races; 2025 {float(anchor['holdout_2025_roi']):+.2f}% on {int(anchor['holdout_2025_races'])}**) plus the strongest walk-forward support (**7/10 folds**)",
        "- **CD_CORE_K8**: steadier current paper candidate, because it stayed positive in both holdout years (**2024 +45.65% on 41; 2025 +78.21% on 19**)",
        "- **OP_REFINED_K7**: prettier aggregate ROI, but still a smaller mixed-year challenger (**2024 -25.47% on 33; 2025 +210.02% on 16**)",
    ]
    expected_rule_split_summary = (
        "So the real read is not \"highest ROI wins.\" It is that CD currently looks steadier, OP_DURABLE still has the stronger anchor-grade evidence base, and OP_REFINED still needs more forward sample before it can challenge the anchor seriously."
    )
    expected_portfolio_decision_lines = [
        f"- **Phase 7 holdout:** **{float(phase7['holdout_roi']):+.2f}% ROI on {int(phase7['holdout_races'])} races** — split: **2024 {float(phase7['holdout_2024_roi']):+.2f}% on {int(phase7['holdout_2024_races'])}; 2025 {float(phase7['holdout_2025_roi']):+.2f}% on {int(phase7['holdout_2025_races'])}**",
        f"- **Phase 8 holdout:** **{float(phase8['holdout_roi']):+.2f}% ROI on {int(phase8['holdout_races'])} races** — split: **2024 {float(phase8['holdout_2024_roi']):+.2f}% on {int(phase8['holdout_2024_races'])}; 2025 {float(phase8['holdout_2025_roi']):+.2f}% on {int(phase8['holdout_2025_races'])}**",
        "So the project improved not by inventing a prettier story, but by making the deployment story harder to bullshit. Phase 7 still leads, but not because it delivered a smooth two-year glide path.",
    ]
    expected_rank_section = (
        "1. **Historical selector scoring got better in a validated way**\n"
        "   - +22.46% to +30.42% walk-forward in the selector-scoring experiment, while the current frozen benchmark still remains the train-only selector card at +22.46% walk-forward and +14.36% holdout"
    )
    expected_operational_evidence_frame = (
        "These are operational and reproducibility improvements, not new forward-evidence wins by themselves.\n"
        "They make the current paper lane easier to run and interpret from saved artifacts, but they do **not** create new paper-trade outcomes.\n"
        "New forward evidence still requires settled paper trades and the downstream forward-check artifacts."
    )
    expected_rank_operational_line = (
        "2. **The project is much more operational**\n"
        "   - daily paper-trade workflow is now clearer and more runnable, but that is workflow/reproducibility improvement rather than new forward proof"
    )
    expected_conclusion_fragment = (
        "The biggest validated historical numeric gain was the selector-scoring improvement from +22.46% to +30.42%, "
        "but the current frozen benchmark still remains the train-only selector at +22.46% walk-forward and +14.36% holdout, "
        "with BENCHMARK ONLY status."
    )
    expected_short_answer_fragment = (
        "- the biggest clean historical numeric gain was **+7.96 percentage points** in selector-scoring walk-forward ROI, "
        "while the current frozen selector benchmark remains the train-only selector at **+22.46%** walk-forward and **+14.36%** holdout"
    )
    stale_ambiguous_phrase = "- **Best validated selector improvement:**"
    stale_active_phase7_phrase = "Phase 7 / active OP+CD basket"
    stale_active_op_sample_phrase = "biggest active OP sample"

    checks: list[dict[str, Any]] = []
    checks.extend(current_bridge_cli_contract_checks(args.current_evidence_json))
    checks.extend(scorecard_cli_gate_contract_checks(scorecard_json_path, args.current_evidence_json))
    checks.append(
        require(
            anchor["tier"] == "ANCHOR" and anchor["rank"] == "1",
            "anchor_source_still_op_durable",
            "forward evidence scorecard still ranks OP_DURABLE_K7 first in the ANCHOR tier",
        )
    )
    checks.append(
        require(
            expected_historical_line in text,
            "historical_selector_line",
            "full report still labels +30.42% as a historical selector-scoring improvement, not the current benchmark",
        )
    )
    checks.append(
        require(
            expected_selector_line in text,
            "current_selector_line",
            "full report still names the train-only yearly selector as the current honest BENCHMARK ONLY selector read",
        )
    )
    checks.append(
        require(
            expected_phase7_line in text and expected_phase7_baseline_line in text,
            "phase7_holdout_line",
            "full report still states the current Phase 7 holdout baseline from the frozen portfolio card and frames the OP/CD paper baseline as preflight-gated rule components",
        )
    )
    checks.append(
        require(
            expected_phase8_line in text,
            "phase8_shadow_line",
            "full report still keeps Phase 8 in shadow-only status with the weaker frozen holdout read and explicit year split",
        )
    )
    checks.append(
        require(
            all(line in text for line in expected_portfolio_decision_lines),
            "portfolio_decision_year_split",
            "full report now makes the Phase 7 versus Phase 8 portfolio decision split-aware in the main decision section instead of only quoting aggregate holdout ROI",
        )
    )
    checks.append(
        require(
            expected_method_line in text and expected_paper_trade_evidence_status_line in text,
            "method_family_line",
            "full report still preserves the selective-rule / Harville / XGBoost posture split and now names the settled-paper-trades boundary in the executive summary",
        )
    )
    checks.append(
        require(
            expected_full_data_retrain_summary_line in text
            and expected_full_data_retrain_section_line in text,
            "full_data_retrain_caveat_route_present",
            "full report now routes full-data XGBoost retrain artifact and exact retrain/prediction command questions to FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py while keeping large RMSE / MAE gains in model-fit reproducibility context only",
        )
    )
    checks.append(
        require(
            expected_evidence_scope_summary_line in text and expected_evidence_scope_ops_line in text,
            "full_report_evidence_scope_boundary",
            "full report now says posture changes require settled paper-trade rows with usable ROI coverage, not clean scans, open signals, replay rows, calibration summaries, or another odds-only rerun",
        )
    )
    checks.append(
        require(
            all(line in text for line in expected_rule_split_lines)
            and expected_rule_split_summary in text,
            "rule_hierarchy_year_split",
            "full report now explains the anchor / paper / watch hierarchy with the explicit 2024-vs-2025 split instead of only aggregate ROI labels",
        )
    )
    checks.append(
        require(
            expected_guardrail_header in text
            and expected_guardrail_intro in text
            and all(row in text for row in expected_guardrail_rows)
            and expected_guardrail_outro in text
            and expected_guardrail_replay_caution in text,
            "method_family_guardrail_section",
            "full report now carries an explicit method-family guardrail block so cold readers see the selective / Harville / XGBoost posture split in table form plus the replay-only selective-family secondary caution",
        )
    )
    checks.append(
        require(
            expected_operational_evidence_frame in text,
            "paper_trade_ops_not_new_evidence_frame",
            "full report now says plainly that paper-trade workflow hardening is operational/reproducibility improvement, not new forward evidence by itself",
        )
    )
    checks.append(
        require(
            current_evidence["source_consistency"]["overall_match"] is True
            and recommendation_read
            and recommendation_context.get("not_forward_performance_evidence") is True
            and recommendation_context.get("not_bet_readiness_evidence_by_itself") is True
            and (api_access_action_route_present if api_access_action_route_required else True)
            and expected_decision_gate_source_line in text
            and expected_current_evidence_summary_line in text
            and expected_scorecard_audit_route_summary_line in text
            and all(line in text for line in expected_current_evidence_bridge_lines),
            "current_evidence_bridge_read",
            f"full report now routes current paper-total wording through CURRENT_EVIDENCE_SUMMARY.md / current_evidence_summary.json, pins the matched source-consistency read, keeps the scorecard-sourced current gates visible, routes wrapper-refresh/missing-output/stale or API-failure right-now cards through the combined operator-status/source-freshness/operator-read-gate path, preserves the source-derived {queue_recommendation_context_label} as workflow context rather than bet-ready or forward-performance proof, and separates the CD-only settled sample from OP-anchor proof, promotion readiness, live profitability, bankroll guidance, and real-money evidence",
        )
    )
    checks.append(
        require(
            scorecard_audit_route_read["source"] == CURRENT_EVIDENCE_JSON.name
            and scorecard_audit_route_read["source_path"] == "scorecard_audit_route"
            and scorecard_audit_route_read["markdown_path"] == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route_read["json_path"] == "scorecard_ranking_contract_audit.json"
            and scorecard_audit_route_read["validator_command"] == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route_read["gate_floor_source"] == "forward_evidence_scorecard.json:decision_gate_minimums"
            and scorecard_audit_route_read["gate_floor_snapshot"]["anchor_displacement_min_roi_complete_settled_observations"] == 30
            and scorecard_audit_route_read["gate_floor_snapshot"]["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and scorecard_audit_route_read["gate_floor_snapshot"]["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and scorecard_audit_route_read["gate_floor_snapshot"]["real_money_no_baq_as_bel_required"] is True
            and scorecard_audit_route_read["artifacts_present"] is True
            and scorecard_audit_route_read["not_forward_performance_evidence"] is True
            and scorecard_audit_route_read["not_settled_roi_evidence"] is True
            and scorecard_audit_route_read["not_promotion_readiness_evidence"] is True
            and scorecard_audit_route_read["not_live_profitability_evidence"] is True
            and scorecard_audit_route_read["not_bankroll_guidance"] is True
            and scorecard_audit_route_read["not_real_money_evidence"] is True
            and "copied 30/20/100 gate floors" in scorecard_audit_route_read["route_read"]
            and "no-BAQ-as-BEL prerequisite" in scorecard_audit_route_read["route_read"]
            and expected_scorecard_audit_route_summary_line in text
            and expected_scorecard_audit_route_bridge_sentence in text,
            "current_evidence_scorecard_audit_route_present",
            "full report now republishes current_evidence_summary.json scorecard_audit_route for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks, with the 30/20/100/no-BAQ snapshot and non-evidence flags intact",
        )
    )
    checks.append(
        require(
            expected_rebuild_order_route_sentence in text
            and rebuild_contract_read.get("source") == "current_evidence_summary.json"
            and rebuild_contract_read.get("source_path") == "rebuild_validation_contract"
            and rebuild_contract_read.get("upstream_refresh_order") == EXPECTED_REBUILD_ORDER_COMMANDS
            and rebuild_contract_read.get("prerequisite_rebuild_command") == EXPECTED_REBUILD_ORDER_COMMANDS[0]
            and rebuild_contract_read.get("rebuild_command") == EXPECTED_REBUILD_ORDER_COMMANDS[1]
            and rebuild_contract_read.get("direct_validation_command") == EXPECTED_REBUILD_ORDER_COMMANDS[2]
            and rebuild_contract_read.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and rebuild_contract_read.get("requires_source_consistency_before_quoting_current_totals") is True
            and rebuild_contract_read.get("upstream_refresh_order_is_provenance_metadata_only") is True
            and rebuild_contract_read.get("not_settled_roi_or_real_money_evidence") is True,
            "current_evidence_rebuild_validation_contract_read",
            "full report now source-checks current_evidence_summary.json rebuild_validation_contract so long-form report readers see the settlement-audit -> current-bridge -> current-bridge-validator order before quoting current bridge totals after source-byte changes, while keeping that route as provenance/rebuild metadata only",
        )
    )
    checks.append(
        require(
            expected_open_row_bridge_sentence in text
            and "Current open-row context: `none`" not in text
            and "current open-row context: `none`" not in text
            and "The current bridge has no open primary settlement rows; the closed settlement queue" not in text,
            "source_published_settlement_queue_state",
            "full report consumes the bridge-published settlement queue state/context/detail and does not render a closed queue as open-row `none` or raw closed-queue prose",
        )
    )
    checks.append(
        require(
            expected_cross_family_caveat_summary_line in text
            and expected_cross_family_caveat_bridge_line in text,
            "cross_family_current_paper_route_present",
            "full report now routes anchor / paper / watch current-paper caveat questions to CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py and keeps stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green report validation out of OP-anchor proof or cross-family promotion evidence",
        )
    )
    checks.append(
        require(
            current_gate_minimums.get("source_path") == "forward_evidence_scorecard.json"
            and current_gate_minimums.get("source_loaded") is True
            and current_gate_minimums.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and current_gate_minimums.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and current_gate_minimums.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and scorecard_gate_read["source"] == "forward_evidence_scorecard.json"
            and scorecard_gate_read["source_path"] == "decision_gate_minimums"
            and scorecard_gate_read["anchor_displacement_min_roi_complete_settled_observations"] == 30
            and scorecard_gate_read["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and scorecard_gate_read["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and scorecard_gate_read["real_money_no_baq_as_bel_required"] is True
            and current_gate_minimums.get("anchor_displacement_min_roi_complete_settled_observations")
            == scorecard_gate_read["anchor_displacement_min_roi_complete_settled_observations"]
            and current_gate_minimums.get("phase8_promotion_review_min_roi_complete_settled_observations")
            == scorecard_gate_read["phase8_promotion_review_min_roi_complete_settled_observations"]
            and current_gate_minimums.get("real_money_discussion_min_total_settled_observations_with_usable_roi")
            == scorecard_gate_read["real_money_discussion_min_total_settled_observations_with_usable_roi"],
            "full_report_gate_source_matches_scorecard_json",
            "full report validator now reads forward_evidence_scorecard.json decision_gate_minimums directly and checks the report/current-evidence gates against the scorecard-sourced 30/20/100 floors plus the no-BAQ-as-BEL prerequisite",
        )
    )
    checks.append(
        require(
            current_bridge_json_read.get("source_consistency_overall_match") is True
            and current_bridge_json_read.get("primary_roi_complete_rows_match") is True
            and current_bridge_json_read.get("primary_open_rows_match") is True
            and current_bridge_json_read.get("primary_incomplete_rows_match") is True
            and current_bridge_json_read.get("primary_roi_gap_rows_match") is True
            and current_bridge_json_read.get("source_freshness_state_valid") is True
            and isinstance(current_bridge_json_read.get("requires_refresh_before_right_now_use"), bool)
            and current_gate_minimums.get("source_values_match_scorecard") is True
            and current_gate_minimums.get("effective_values_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and current_gate_minimums.get("missing_top_card_fields") == []
            and current_gate_minimums.get("mismatched_fields") == []
            and current_gate_top_card_values == current_gate_scorecard_values == current_gate_effective_values
            and current_bridge_json_read.get("effective_anchor_displacement_min") == 30
            and current_bridge_json_read.get("effective_phase8_promotion_review_min") == 20
            and current_bridge_json_read.get("effective_real_money_discussion_min") == 100
            and current_bridge_json_read.get("top_card_anchor_displacement_min") == 30
            and current_bridge_json_read.get("top_card_phase8_promotion_review_min") == 20
            and current_bridge_json_read.get("top_card_real_money_discussion_min") == 100
            and current_bridge_json_read.get("scorecard_anchor_displacement_min_from_bridge") == 30
            and current_bridge_json_read.get("scorecard_phase8_promotion_review_min_from_bridge") == 20
            and current_bridge_json_read.get("scorecard_real_money_discussion_min_from_bridge") == 100
            and current_bridge_json_read.get("decision_gate_threshold_sources", {}).get("anchor_displacement")
            == "forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations"
            and current_bridge_json_read.get("decision_gate_threshold_sources", {}).get("phase8_promotion_review")
            == "forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations"
            and current_bridge_json_read.get("decision_gate_threshold_sources", {}).get("real_money_discussion")
            == "forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
            "current_evidence_bridge_effective_gates_are_scorecard_backed",
            "full report validator now publishes the current-evidence bridge's canonical scorecard-backed effective gate values, top-card/scorecard alignment fields, missing/mismatch lists, and exact threshold-source paths instead of accepting only the older flattened 30/20/100 fields",
        )
    )
    checks.append(
        require(
            "source_freshness.requires_refresh_before_right_now_use" in text
            and expected_source_freshness_summary_sentence in text
            and expected_source_freshness_bridge_sentence in text
            and expected_source_freshness_repair_sentence in text,
            "current_evidence_combined_operator_read_route",
            "full report now carries the combined operator_status_context / source_freshness / operator_read_gate route, so a source-matched but stale/API-failure right-now card triggers the daily wrapper before being used as current-day instruction or evidence",
        )
    )
    checks.append(
        require(
            "operator_read_gate.requires_refresh_before_evidence_read" in text
            and expected_operator_read_gate_bridge_sentence in text
            and operator_read_gate_json_read.get("source") == "current_evidence_summary.json"
            and operator_read_gate_json_read.get("source_path") == "operator_read_gate"
            and operator_read_gate_json_read.get("gate_status") in {
                "refresh_required_before_evidence_read",
                "current_operator_routing_context_only",
            }
            and operator_read_gate_json_read.get("valid_use") == "operator instruction/evidence-read gating only"
            and isinstance(operator_read_gate_json_read.get("requires_refresh_before_evidence_read"), bool)
            and isinstance(operator_read_gate_json_read.get("has_api_access_failure_context"), bool)
            and isinstance(operator_read_gate_json_read.get("has_scanner_failure_boundary"), bool)
            and isinstance(operator_read_gate_json_read.get("has_stale_cache_fallback_context"), bool)
            and isinstance(operator_read_gate_json_read.get("recommended_command"), str)
            and bool(operator_read_gate_json_read.get("recommended_command"))
            and operator_read_gate_json_read.get("current_top_card_counts_as_no_target_evidence") is False
            and operator_read_gate_json_read.get("current_top_card_counts_as_clean_empty_evidence") is False
            and operator_read_gate_json_read.get("current_top_card_counts_as_bet_readiness_evidence") is False
            and operator_read_gate_json_read.get("current_top_card_counts_as_settled_roi_evidence") is False
            and operator_read_gate_json_read.get("not_forward_performance_evidence") is True
            and operator_read_gate_json_read.get("not_promotion_readiness_evidence") is True
            and operator_read_gate_json_read.get("not_live_profitability_evidence") is True
            and operator_read_gate_json_read.get("not_real_money_evidence") is True,
            "current_evidence_operator_read_gate_route",
            "full report now carries current_evidence_summary.json operator_read_gate as refresh-before-evidence-read routing before stale, stale-cache fallback, or missing-state top-card instruction/evidence use, without treating that state as no-target, clean-empty, bet-readiness, settled-ROI, forward-performance, promotion, live-profitability, bankroll, or real-money evidence",
        )
    )
    checks.append(
        require(
            expected_rank_section in text and expected_rank_operational_line in text,
            "improvement_rank_section",
            "full report still distinguishes the historical selector improvement from the current frozen benchmark in the improvement ranking, and now keeps the operational-improvement item explicit that it is not new forward proof",
        )
    )
    checks.append(
        require(
            expected_conclusion_fragment in text,
            "report_safe_conclusion",
            "recommended report-safe conclusion still states the historical-vs-current selector distinction explicitly",
        )
    )
    checks.append(
        require(
            expected_short_answer_fragment in text,
            "short_answer_fragment",
            "short-answer summary still keeps the historical gain separate from the current frozen selector benchmark",
        )
    )
    checks.append(
        require(
            stale_ambiguous_phrase not in text
            and stale_active_phase7_phrase not in text
            and stale_active_op_sample_phrase not in text,
            "stale_ambiguous_phrase_removed",
            "full report no longer uses the older ambiguous 'Best validated selector improvement' wording, the stale active-OP+CD baseline shorthand, or active-OP historical sample wording",
        )
    )
    checks.append(
        require(
            "new live default" not in text
            and "live-paper lane" not in text,
            "stale_live_default_and_live_paper_lane_removed",
            "full report now avoids live-default and live-paper-lane shorthand for paper-observation posture",
        )
    )

    suite_read = (
        f"COLE full report matches frozen posture: anchor={anchor['rule_id']} ({float(anchor['holdout_roi']):+.1f}% on {int(anchor['holdout_races'])}; "
        f"2024={float(anchor['holdout_2024_roi']):+.2f}% on {int(anchor['holdout_2024_races'])}, "
        f"2025={float(anchor['holdout_2025_roi']):+.2f}% on {int(anchor['holdout_2025_races'])}); "
        f"paper={phase7['label']} ({float(phase7['holdout_roi']):+.2f}% on {int(phase7['holdout_races'])}; 2024={float(phase7['holdout_2024_roi']):+.2f}% on {int(phase7['holdout_2024_races'])}, 2025={float(phase7['holdout_2025_roi']):+.2f}% on {int(phase7['holdout_2025_races'])}); "
        f"selector current benchmark={selector['label']} ({float(selector['wf_roi']):+.2f}% WF, {float(selector['holdout_roi']):+.2f}% holdout, {selector['role']}); "
        f"historical selector improvement=+22.46% to +30.42%; Phase 7 paper baseline wording=OP/CD rule-component paper-observation basket with target cards requiring daily preflight; Phase 8={phase8['role']} ({float(phase8['holdout_roi']):+.2f}% on {int(phase8['holdout_races'])}; 2024={float(phase8['holdout_2024_roi']):+.2f}% on {int(phase8['holdout_2024_races'])}, 2025={float(phase8['holdout_2025_roi']):+.2f}% on {int(phase8['holdout_2025_races'])}); method roles={selective['role']} / {harville['role']} / {xgboost['role']}; paper-trade workflow hardening now stays framed as operational/reproducibility improvement rather than new forward evidence, with genuinely new forward evidence still requiring settled paper trades; evidence scope=settled paper-trade rows with usable ROI coverage can change posture, while clean scans/open signals/historical replay/calibration-only summaries/odds-only reruns cannot; report gates source-matched to forward_evidence_scorecard.json decision_gate_minimums with anchor_displacement={scorecard_anchor_min}, phase8_promotion_review={scorecard_phase8_min}, and real_money_discussion={scorecard_real_money_min}; current evidence bridge=CURRENT_EVIDENCE_SUMMARY.md/current_evidence_summary.json source consistency {source_consistency_label}, combined operator-status/source-freshness/operator-read-gate route {combined_operator_route_label}, primary paper {current_first_read['current']}/{current_first_read['threshold']} first-read and {current_portfolio_review['current']}/{current_portfolio_review['threshold']} broader-review gates, CD_CORE_K8={rule_progress['CD_CORE_K8']['roi_complete_settled_rows']} ROI-complete rows, OP_DURABLE_K7={rule_progress['OP_DURABLE_K7']['roi_complete_settled_rows']} ROI-complete rows, current settled sample is CD-only context and not OP-anchor evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence; operator_read_gate read={operator_read_gate_read}; selective-family secondary lines elsewhere stay explicitly replay-context rather than extra train-only proof; selective paper-companion read anchor={selective['current_anchor']}, paper companion={selective['primary_shadow']}, closest shadow={selective['secondary_shadow']}"
        f"; scorecard audit route=current_evidence_summary.json.scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks as report-synchronization metadata only; {suite_queue_context}; direct cross-family current-paper caveat route=CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py, with stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green report validation not OP-anchor proof or cross-family promotion evidence; full-data retrain caveat route=FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py, with large RMSE / MAE gains and exact retrain/prediction commands kept as model-fit reproducibility context rather than paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence"
        f"; rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only"
    )

    payload = {
        "suite_status": "pass",
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "current_evidence_bridge_json_read": current_bridge_json_read,
        "current_evidence_operator_read_gate_read": operator_read_gate_json_read,
        "current_evidence_scorecard_audit_route_read": scorecard_audit_route_read,
        "current_evidence_rebuild_validation_contract_read": rebuild_contract_read,
        "scorecard_decision_gate_minimums_read": scorecard_gate_read,
        "summary": {
            "suite_read": suite_read,
            "selective_shadow_read": {
                "anchor": selective["current_anchor"],
                "primary_shadow": selective["primary_shadow"],
                "secondary_shadow": selective["secondary_shadow"],
            },
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }

    lines = [
        "# Cole Full Report Validation",
        "",
        "This report checks that `COLE_FULL_REPORT_2026-04-15.md` keeps historical selector-scoring gains separate from the current frozen deployment benchmark, posture, and evidence-scope boundary.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Target file: `{REPORT.name}`",
        f"- Checks: {len(checks)}",
        "- Result: PASS",
        "",
        "## Checks",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for item in checks:
        lines.append(f"| {item['check']} | {item['status'].upper()} | {item['detail']} |")

    lines.extend(
        [
            "",
            "## Current Read",
            "",
            f"- Suite read: {suite_read}",
            f"- Historical selector line: {expected_historical_line}",
            f"- Current selector line: {expected_selector_line}",
            f"- Phase 7 baseline line: {expected_phase7_baseline_line}",
            f"- Phase 7 line: {expected_phase7_line}",
            f"- Phase 8 line: {expected_phase8_line}",
            f"- Rule split line (anchor): {expected_rule_split_lines[0]}",
            f"- Rule split line (paper): {expected_rule_split_lines[1]}",
            f"- Rule split line (watch): {expected_rule_split_lines[2]}",
            f"- Evidence-scope summary line: {expected_evidence_scope_summary_line}",
            f"- Full-data retrain caveat summary line: {expected_full_data_retrain_summary_line}",
            f"- Full-data retrain caveat section line: {expected_full_data_retrain_section_line}",
            f"- Decision-gate source line: {expected_decision_gate_source_line}",
            f"- Rebuild order route: {expected_rebuild_order_route_sentence}",
            f"- Scorecard audit route summary line: {expected_scorecard_audit_route_summary_line}",
            f"- Scorecard audit route bridge line: {expected_scorecard_audit_route_bridge_sentence}",
            f"- Current-evidence bridge line: {expected_current_evidence_summary_line}",
            f"- Current-evidence operator read gate line: {expected_operator_read_gate_bridge_sentence}",
            f"- Direct cross-family caveat route: {expected_cross_family_caveat_summary_line}",
            f"- Direct cross-family bridge line: {expected_cross_family_caveat_bridge_line}",
            f"- Current settlement-queue context line: {expected_open_row_bridge_sentence}",
            f"- Method-family guardrail header: {expected_guardrail_header}",
            f"- Method-family guardrail roles: {selective['role']} / {harville['role']} / {xgboost['role']}",
            f"- Selective-family paper-companion read: anchor={selective['current_anchor']}, paper companion={selective['primary_shadow']}, closest shadow={selective['secondary_shadow']}",
            "",
            "## Source Artifacts",
            "",
            f"- `{SCORECARD_CSV.name}`",
            f"- `{SCORECARD_JSON.name}`",
            f"- `{PORTFOLIO_CSV.name}`",
            f"- `{METHOD_CSV.name}`",
        ]
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
