#!/usr/bin/env python3
"""
Validation for COLE_PRESENTATION_OUTLINE.md.

Purpose:
- keep the presentation-outline surface aligned with the frozen evaluation standard
- make sure the speaking version keeps the historical-vs-current benchmark distinction clear
- pin the explicit selective / Harville / XGBoost method-family guardrail for cold readers
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
OUTLINE = BASE / "COLE_PRESENTATION_OUTLINE.md"
PORTFOLIO_CSV = BASE / "portfolio_decision_card.csv"
METHOD_CSV = BASE / "method_family_decision_card.csv"
SCORECARD_CSV = BASE / "forward_evidence_scorecard.csv"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
OUT_DIR = BASE / "out" / "status_validation" / "cole_presentation_outline"
OUT_MD = OUT_DIR / "cole_presentation_outline_validation.md"
OUT_JSON = OUT_DIR / "cole_presentation_outline_validation.json"
REBUILD_COMMAND = "python3 validate_cole_presentation_outline.py"
EXPECTED_REBUILD_ORDER_COMMANDS = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"


def load_csv_map(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {str(row[key]): row for row in rows}


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "pass", "detail": detail}


def require_positive_non_bool_int(value: Any, *, source_name: str, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, source_name: str, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise AssertionError(f"{source_name} {field_name} must be a list of non-empty strings")
    return value


def scorecard_gate_context(scorecard_json_path: Path = SCORECARD_JSON) -> dict[str, Any]:
    source_path = Path(scorecard_json_path)
    source_name = source_path.name
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    gates = payload.get("decision_gate_minimums")
    if not isinstance(gates, dict):
        raise AssertionError(f"{source_name} is missing decision_gate_minimums")

    anchor_gate = gates.get("anchor_displacement")
    phase8_gate = gates.get("phase8_promotion_review")
    real_money_gate = gates.get("real_money_discussion")
    if not isinstance(anchor_gate, dict) or not isinstance(phase8_gate, dict) or not isinstance(real_money_gate, dict):
        raise AssertionError(f"{source_name} decision_gate_minimums is missing a required gate")

    anchor_min = require_positive_non_bool_int(
        anchor_gate.get("min_roi_complete_settled_observations"),
        source_name=source_name,
        field_name="decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
    )
    phase8_min = require_positive_non_bool_int(
        phase8_gate.get("min_roi_complete_settled_observations"),
        source_name=source_name,
        field_name="decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
    )
    real_money_min = require_positive_non_bool_int(
        real_money_gate.get("min_total_settled_observations_with_usable_roi"),
        source_name=source_name,
        field_name="decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
    )
    real_money_requirements = require_string_list(
        real_money_gate.get("also_requires"),
        source_name=source_name,
        field_name="decision_gate_minimums.real_money_discussion.also_requires",
    )
    if NO_BAQ_AS_BEL_PREREQUISITE not in real_money_requirements:
        raise AssertionError(
            f"{source_name} decision_gate_minimums.real_money_discussion.also_requires "
            f"must include {NO_BAQ_AS_BEL_PREREQUISITE}"
        )

    return {
        "payload": payload,
        "read": {
            "source": source_name,
            "source_path": "decision_gate_minimums",
            "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
            "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
            "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
            "real_money_no_baq_as_bel_required": True,
        },
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
        raise AssertionError(
            "current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true"
        )
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
    parser = argparse.ArgumentParser(description="Validate the Cole presentation outline")
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--current-evidence-json", type=Path, default=CURRENT_EVIDENCE_JSON)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def scorecard_gate_cli_contract_checks(
    scorecard_json_path: Path = SCORECARD_JSON,
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="presentation_scorecard_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(scorecard_json_path).read_text(encoding="utf-8"))
        scorecard_path = tmp_root / "forward_evidence_scorecard.json"

        nonpositive_phase8_out_dir = tmp_root / "nonpositive_phase8" / "cole_presentation_outline_validation"
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
                "--current-evidence-json",
                str(current_evidence_json_path),
                "--out-dir",
                str(nonpositive_phase8_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not nonpositive_phase8_out_dir.exists()
                and "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer"
                in proc.stderr,
                "scorecard_nonpositive_phase8_floor_fails_before_artifacts",
                "validate_cole_presentation_outline.py rejects a non-positive Phase 8 promotion-review scorecard gate before creating nested output directories or partial presentation validation artifacts",
            )
        )

        nonpositive_real_money_out_dir = tmp_root / "nonpositive_real_money" / "cole_presentation_outline_validation"
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
                "--current-evidence-json",
                str(current_evidence_json_path),
                "--out-dir",
                str(nonpositive_real_money_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not nonpositive_real_money_out_dir.exists()
                and "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer"
                in proc.stderr,
                "scorecard_nonpositive_real_money_floor_fails_before_artifacts",
                "validate_cole_presentation_outline.py rejects a non-positive real-money discussion scorecard gate before creating nested output directories or partial presentation validation artifacts",
            )
        )

    return checks


def current_bridge_cli_contract_checks(
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="presentation_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json_path).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "cole_presentation_outline_validation"
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
                "validate_cole_presentation_outline.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial presentation validation artifacts",
            )
        )

        weakened_contract_out_dir = tmp_root / "weakened" / "cole_presentation_outline_validation"
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
                and "current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true"
                in proc.stderr,
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "validate_cole_presentation_outline.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial presentation validation artifacts",
            )
        )

    return checks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    text = OUTLINE.read_text(encoding="utf-8")
    portfolio = load_csv_map(PORTFOLIO_CSV, "method_id")
    method_family = load_csv_map(METHOD_CSV, "family_id")
    scorecard = load_csv_map(SCORECARD_CSV, "rule_id")
    scorecard_gate_context_read = scorecard_gate_context(args.scorecard_json)
    scorecard_json = scorecard_gate_context_read["payload"]
    current_evidence = json.loads(Path(args.current_evidence_json).read_text(encoding="utf-8"))
    rebuild_validation_contract_json_read = require_current_evidence_rebuild_contract(current_evidence)

    anchor = scorecard["OP_DURABLE_K7"]
    phase7 = portfolio["phase7_live_portfolio"]
    phase8 = portfolio["phase8_frozen_portfolio"]
    selector = portfolio["train_only_selector"]
    selective = method_family["selective_rule_path"]
    harville = method_family["harville_ranked"]
    xgboost = method_family["xgboost_residual"]
    current_primary = current_evidence["current_paper_status"]["primary"]
    current_first_read = current_primary["first_read"]
    current_portfolio_review = current_primary["portfolio_review"]
    rule_progress = {row["rule_id"]: row for row in current_primary["rule_progress"]}
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
    source_consistency_label = (
        "matched" if current_evidence["source_consistency"]["overall_match"] is True else "not matched"
    )
    current_source_consistency = (
        current_evidence.get("source_consistency")
        if isinstance(current_evidence.get("source_consistency"), dict)
        else {}
    )
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
        "read": operator_read_gate_read,
    }
    scorecard_audit_route = (
        current_evidence.get("scorecard_audit_route")
        if isinstance(current_evidence.get("scorecard_audit_route"), dict)
        else {}
    )
    scorecard_audit_route_json_read = {
        "source": CURRENT_EVIDENCE_JSON.name,
        "source_path": "scorecard_audit_route",
        "markdown_path": scorecard_audit_route.get("markdown_path"),
        "json_path": scorecard_audit_route.get("json_path"),
        "validator_command": scorecard_audit_route.get("validator_command"),
        "gate_floor_source": scorecard_audit_route.get("gate_floor_source"),
        "gate_floor_snapshot": scorecard_audit_route.get("gate_floor_snapshot"),
        "route_read": scorecard_audit_route.get("route_read"),
        "valid_use": scorecard_audit_route.get("valid_use"),
        "artifacts_present": scorecard_audit_route.get("artifacts_present"),
        "not_forward_performance_evidence": scorecard_audit_route.get("not_forward_performance_evidence"),
        "not_settled_roi_evidence": scorecard_audit_route.get("not_settled_roi_evidence"),
        "not_promotion_readiness_evidence": scorecard_audit_route.get("not_promotion_readiness_evidence"),
        "not_live_profitability_evidence": scorecard_audit_route.get("not_live_profitability_evidence"),
        "not_bankroll_guidance": scorecard_audit_route.get("not_bankroll_guidance"),
        "not_real_money_evidence": scorecard_audit_route.get("not_real_money_evidence"),
    }
    upstream_refresh_commands = rebuild_validation_contract_json_read["upstream_refresh_order"]
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
    scorecard_gate_read = scorecard_gate_context_read["read"]
    scorecard_anchor_min = scorecard_gate_read["anchor_displacement_min_roi_complete_settled_observations"]
    scorecard_phase8_min = scorecard_gate_read["phase8_promotion_review_min_roi_complete_settled_observations"]
    scorecard_real_money_min = scorecard_gate_read[
        "real_money_discussion_min_total_settled_observations_with_usable_roi"
    ]
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
    expected_source_freshness_line = (
        "- The bridge uses the combined current-paper route: `operator_status_context`, `source_freshness.requires_refresh_before_right_now_use=true`, and `operator_read_gate.requires_refresh_before_evidence_read=true`; rerun `./run_daily_portfolio_observation.sh` before treating wrapper-refresh, missing-output, stale/API-failure `PAPER_TRADE_NOW`, or its best-action card as today's operator instruction or evidence."
        if requires_refresh
        else (
            "- The bridge uses the combined current-paper route: `operator_status_context`, "
            "`source_freshness.requires_refresh_before_right_now_use=false`, and "
            f"`operator_read_gate.requires_refresh_before_evidence_read={operator_read_gate_requires_refresh_label}`; "
            "the saved `PAPER_TRADE_NOW` best-action card is fresh against the bridge reference date, but operator "
            "read-gate routing still governs instruction/evidence use and is not performance evidence."
        )
    )
    expected_bridge_repair_line = (
        "- If `source_consistency.overall_match=false`, repair the top-card / audit / CSV mismatch before quoting current paper numbers; then use the combined `operator_status_context` + `source_freshness` + `operator_read_gate` route before using the saved right-now card as current-day guidance or evidence."
    )
    expected_operator_read_gate_line = (
        f"- The bridge also publishes `operator_read_gate.requires_refresh_before_evidence_read="
        f"{operator_read_gate_requires_refresh_label}`: "
        f"{operator_read_gate_read}"
    )
    expected_scorecard_audit_route_line = (
        f"- Scorecard audit route: `{CURRENT_EVIDENCE_JSON.name}.scorecard_audit_route` -> "
        f"`{scorecard_audit_route['markdown_path']}` / `{scorecard_audit_route['json_path']}` plus "
        f"`{scorecard_audit_route['validator_command']}` for copied gate/ranking/CI-only/timezone/no-BAQ "
        "synchronization checks; this is report-synchronization metadata only, not forward performance, "
        "settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence."
    )
    expected_rebuild_validation_contract_line = (
        f"- Rebuild-order route: `{CURRENT_EVIDENCE_JSON.name}.rebuild_validation_contract` -> "
        f"`{upstream_refresh_commands[0]}` -> `{upstream_refresh_commands[1]}` -> `{upstream_refresh_commands[2]}` "
        "after scorecard/rules/signals/settlement-ledger byte changes and before quoting "
        "`CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not settled ROI, "
        "promotion readiness, live profitability, bankroll guidance, or real-money evidence."
    )

    expected_thesis = (
        "We found a real-looking but smaller-than-advertised betting edge in a narrow set of superfecta situations, and the honest next step is paper trading the simpler Phase 7 rules, not claiming Phase 8 or ML solved the problem."
    )
    expected_walk_forward_line = (
        "> I tested a superfecta strategy across a large historical dataset and found that a small set of simple favorite-gap rules held up better than the more complicated versions. The best honest forward-style number is about **+22.46% ROI in walk-forward testing**, not the flashy **+46.72%** full-sample Phase 8 result. On the actual 2024-2025 holdout, the simpler **Phase 7 portfolio beat Phase 8, +38.68% vs +21.45%**, but that Phase 7 edge was uneven: **2024 was basically flat (+0.37% on 109 races)** and **2025 was much stronger (+105.38% on 66 races)**. So my conclusion is not \"mission accomplished.\" It is \"there may be an edge, but it is narrow, track-specific, and needs paper trading before any real-money claim.\""
    )
    expected_phase7_line = f"- **Phase 7 OP/CD rule-component basket:** **{float(phase7['holdout_roi']):+.2f}% ROI**, {int(phase7['holdout_races'])} races, **$10,210.61** profit; split: **2024 {float(phase7['holdout_2024_roi']):+.2f}% on {int(phase7['holdout_2024_races'])}**, **2025 {float(phase7['holdout_2025_roi']):+.2f}% on {int(phase7['holdout_2025_races'])}**; target cards still come from daily preflight"
    expected_phase8_line = f"- **Phase 8 frozen portfolio:** **{float(phase8['holdout_roi']):+.2f}% ROI**, {int(phase8['holdout_races'])} races, **$5,585.05** profit; split: **2024 {float(phase8['holdout_2024_roi']):+.2f}% on {int(phase8['holdout_2024_races'])}**, **2025 {float(phase8['holdout_2025_roi']):+.2f}% on {int(phase8['holdout_2025_races'])}**"
    expected_anchor_line = f"  - Holdout: **{float(anchor['holdout_roi']):+.1f}% ROI on {int(anchor['holdout_races'])} races**"
    expected_anchor_split_line = (
        f"  - Holdout split: **2024 {float(anchor['holdout_2024_roi']):+.2f}% on {int(anchor['holdout_2024_races'])} races; "
        f"2025 {float(anchor['holdout_2025_roi']):+.2f}% on {int(anchor['holdout_2025_races'])} races**"
    )
    cd_core = scorecard["CD_CORE_K8"]
    expected_cd_split_line = (
        f"  - Holdout split: **2024 {float(cd_core['holdout_2024_roi']):+.2f}% on {int(cd_core['holdout_2024_races'])} races; "
        f"2025 {float(cd_core['holdout_2025_roi']):+.2f}% on {int(cd_core['holdout_2025_races'])} races**"
    )
    op_refined = scorecard["OP_REFINED_K7"]
    expected_op_refined_split_line = (
        f"  - Holdout split: **2024 {float(op_refined['holdout_2024_roi']):+.2f}% on {int(op_refined['holdout_2024_races'])} races; "
        f"2025 {float(op_refined['holdout_2025_roi']):+.2f}% on {int(op_refined['holdout_2025_races'])} races**"
    )
    wf_selected_text = str(anchor.get('wf_selected', '7/10'))
    if '/' in wf_selected_text:
        wf_num, wf_den = wf_selected_text.split('/', 1)
    else:
        wf_num = wf_selected_text
        wf_den = str(anchor.get('wf_total', '10'))
    expected_anchor_fold_line = f"  - Walk-forward selected in **{int(wf_num)} of {int(wf_den)} folds**"
    expected_observation_only_line = "- **Observation-only pockets:** `KEE_K9`, `SA_K9`, `DMR_FALL_K7`"
    expected_observation_only_detail = "  - Interesting enough to log, but still too small for near-promotion talk"
    expected_slide5_short_line = "CD is the steadier two-positive-year paper candidate, OP_DURABLE is still the safest anchor because it has the bigger OP sample plus the strongest walk-forward support, OP_REFINED still looks more like a smaller hot-2025 challenger than a replacement, and the other Phase 8 names stay observation-only."
    expected_guardrail_header = "## Slide 5A, Method-family guardrail"
    expected_guardrail_lines = [
        f"- **{selective['label']} = {selective['role']}**",
        f"  - Current frozen holdout: **{float(selective['primary_metric']):+.2f}% ROI on {int(selective['primary_sample'])} races**; split: **2024 {float(phase7['holdout_2024_roi']):+.2f}% on {int(phase7['holdout_2024_races'])}**, **2025 {float(phase7['holdout_2025_roi']):+.2f}% on {int(phase7['holdout_2025_races'])}**",
        "  - This is the only family here with positive current frozen holdout evidence and an actual paper-trade workflow, but the recent path was uneven rather than smooth",
        "  - Current paper-companion read: `OP_DURABLE_K7` stays the safest anchor, `CD_CORE_K8` is the primary OP/CD paper-basket companion, and `OP_REFINED_K7` remains the narrower same-family OP shadow challenger rather than a promoted default",
        f"- **{harville['label']} = {harville['role']}**",
        f"  - Broad benchmark: **{float(harville['primary_metric']):+.2f}% ROI on {int(harville['primary_sample'])} races**",
        f"- **{xgboost['label']} = {xgboost['role']}**",
        f"  - Best ML betting line: **{float(xgboost['primary_metric']):+.2f}% ROI on {int(xgboost['primary_sample'])} races**",
    ]
    expected_guardrail_outro = "- First rule out dead-end method families, then compare the serious selective contenders against each other."
    expected_guardrail_replay_line = "- The broader selective-family secondary lines elsewhere in the repo are replay context on walk-forward test years, not extra train-only validation."
    expected_guardrail_honesty_line = "- Inside the selective family, do not let the highest small-sample ROI outrun the current anchor / paper companion / same-family shadow challenger order."
    expected_ml_line = "- **ML / XGBoost** did not improve betting decisions in a usable way."
    expected_full_data_retrain_guardrail_line = (
        "  - Full-data retrain artifacts and exact retrain/prediction commands route to `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py`; large RMSE / MAE gains are model-fit reproducibility context only, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence"
    )
    expected_full_data_retrain_qa_line = (
        "For the full-data retrain artifact specifically, read `FULL_DATA_RETRAIN_ARTIFACTS.md` and run `python3 validate_full_data_retrain_artifacts.py`; large RMSE / MAE gains remain model-fit diagnostics, not paper-trade evidence."
    )
    expected_full_data_retrain_artifact_lines = [
        "- `FULL_DATA_RETRAIN_ARTIFACTS.md`",
        "- `validate_full_data_retrain_artifacts.py`",
        "- Full-data retrain caveat route: `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py`; exact retrain/prediction commands and large RMSE / MAE gains are model-fit reproducibility context only, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
    ]
    expected_workflow_not_proof_line = "- A clean first paper-trade run would prove the workflow works and observations are being captured, not that the edge is already confirmed live."
    expected_settled_evidence_line = "- The improved paper-trade stack is workflow hardening and observation capture, not new forward evidence by itself; genuinely new forward evidence starts when settled paper trades accumulate."
    expected_evidence_scope_line = "- Evidence-scope rule: only settled paper-trade rows with usable ROI coverage should change deployment posture; clean scans, open signals, historical replay rows, calibration-only summaries, or another odds-only rerun should not."
    expected_decision_gate_source_line = (
        f"- Decision-gate source: `{SCORECARD_JSON.name}` `decision_gate_minimums` sets "
        f"`anchor_displacement={scorecard_anchor_min}`, `phase8_promotion_review={scorecard_phase8_min}`, "
        f"and `real_money_discussion={scorecard_real_money_min}`; these are future ROI-complete observation floors, not cleared gates."
    )
    expected_queue_context_line = (
        f"- Settlement queue state: `{open_settlement_queue_state}`; {open_settlement_context}; detail: "
        f"{open_settlement_queue_read}"
    )
    expected_queue_artifact_line = (
        f"- Current settlement queue state: `{open_settlement_queue_state}`; {open_settlement_context}; detail: "
        f"{open_settlement_queue_read} Latest primary recommendation context is recommendation-state routing, "
        "not a bet-ready ticket or forward-performance proof."
    )
    queue_recommendation_context_label = "source-published settlement queue state plus recommendation-state context"
    suite_queue_context = (
        f"settlement queue state={open_settlement_queue_state} / context={open_settlement_context} remains workflow context "
        f"with source detail_read={open_settlement_queue_read} while latest primary recommendation context says "
        f"{recommendation_context['read']}"
    )
    expected_current_evidence_lines = [
        "## Slide 7A, Current paper-read bridge",
        "### Title",
        "What the current paper totals mean right now",
        "- For current paper totals, read `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` before quoting `PAPER_TRADE_NOW`, ops-bucket/operator-status context, settlement-audit, or primary-ledger numbers.",
        f"- The bridge currently says source consistency is {source_consistency_label} across the top card, settlement audit, and primary settlement CSV.",
        expected_source_freshness_line,
        expected_operator_read_gate_line,
        expected_scorecard_audit_route_line,
        f"- Primary paper is still **{current_first_read['current']}/{current_first_read['threshold']}** ROI-complete toward a first statistical read and **{current_portfolio_review['current']}/{current_portfolio_review['threshold']}** toward broader review.",
        f"- The current settled sample is **CD-only**: `CD_CORE_K8` has **{rule_progress['CD_CORE_K8']['roi_complete_settled_rows']}** ROI-complete settled rows, while `OP_DURABLE_K7` has **{rule_progress['OP_DURABLE_K7']['roi_complete_settled_rows']}**.",
        f"- Latest primary recommendation context: {recommendation_context['read']}",
        expected_queue_context_line,
        "- So these current paper totals are operational context, not OP-anchor evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        expected_bridge_repair_line,
        expected_rebuild_validation_contract_line,
        "- Do not change rules from this tiny settled sample.",
        "- Do not promote `OP_REFINED_K7` or Phase 8 from this sample.",
        "- Do not substitute `BAQ` for `BEL`.",
        "- Do not discuss real-money scaling until the scorecard-sourced 30 / 20 / 100 usable-settlement gates are actually supported.",
    ]
    expected_current_evidence_artifact_lines = [
        "- `CURRENT_EVIDENCE_SUMMARY.md`",
        "- `current_evidence_summary.json`",
        "- `validate_current_evidence_summary.py`",
        f"- Current paper bridge: source consistency {source_consistency_label}; combined operator-status / source-freshness / operator-read-gate route {combined_operator_route_label}; primary paper **{current_first_read['current']}/{current_first_read['threshold']}** first-read and **{current_portfolio_review['current']}/{current_portfolio_review['threshold']}** broader-review gates; `CD_CORE_K8` has **{rule_progress['CD_CORE_K8']['roi_complete_settled_rows']}** ROI-complete settled rows and `OP_DURABLE_K7` has **{rule_progress['OP_DURABLE_K7']['roi_complete_settled_rows']}**, so current settled paper context is CD-only and not OP-anchor evidence.",
        f"- Current operator read gate: `operator_read_gate.requires_refresh_before_evidence_read={operator_read_gate_requires_refresh_label}`; {operator_read_gate_read}",
        f"- Scorecard audit route: `{CURRENT_EVIDENCE_JSON.name}.scorecard_audit_route` points to `{scorecard_audit_route['markdown_path']}` / `{scorecard_audit_route['json_path']}` plus `{scorecard_audit_route['validator_command']}` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks as report-synchronization metadata only.",
        f"- Rebuild-order route: `{CURRENT_EVIDENCE_JSON.name}.rebuild_validation_contract` points to `{upstream_refresh_commands[0]}` -> `{upstream_refresh_commands[1]}` -> `{upstream_refresh_commands[2]}` after scorecard/rules/signals/settlement-ledger byte changes and before quoting `CURRENT_EVIDENCE_SUMMARY.*` as provenance/rebuild metadata only.",
        expected_queue_artifact_line,
        "- Direct cross-family current-paper caveat route: `CROSS_FAMILY_DECISION.md` plus `validate_cross_family_decision.py`; stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green presentation validation are not OP-anchor proof or cross-family promotion evidence.",
    ]
    expected_cross_family_caveat_slide_line = "- For the anchor / paper / watch shortlist specifically, use `CROSS_FAMILY_DECISION.md` and `validate_cross_family_decision.py` as the direct current-paper caveat route; stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green presentation validation are not OP-anchor proof or cross-family promotion evidence."
    expected_q5_evidence_scope = "A decent settled paper-trade sample with usable ROI coverage. If live-style logging comes in far below expectation, I would lower confidence quickly. If it tracks the current range over enough races, confidence improves. Clean scans, open signals, historical replay rows, calibration-only summaries, or another odds-only rerun would not change deployment posture."
    expected_short_reco = "> Paper trade the Phase 7 core, especially OP and CD, and judge the project by holdout plus walk-forward evidence, not the Phase 8 headline backtest; only change the posture after settled, ROI-complete forward observations clear the explicit gates."

    checks: list[dict[str, Any]] = []
    checks.extend(scorecard_gate_cli_contract_checks(args.scorecard_json, args.current_evidence_json))
    checks.extend(current_bridge_cli_contract_checks(args.current_evidence_json))
    checks.append(
        require(
            anchor["tier"] == "ANCHOR" and anchor["rank"] == "1",
            "anchor_source_still_op_durable",
            "forward evidence scorecard still ranks OP_DURABLE_K7 first in the ANCHOR tier",
        )
    )
    checks.append(
        require(
            expected_thesis in text,
            "presentation_thesis",
            "presentation outline still opens with the honest smaller-than-advertised edge thesis",
        )
    )
    checks.append(
        require(
            expected_walk_forward_line in text,
            "walk_forward_vs_headline",
            "presentation outline still leads with +22.46% walk-forward instead of the Phase 8 headline backtest number",
        )
    )
    checks.append(
        require(
            expected_phase7_line in text and expected_phase8_line in text,
            "phase7_beats_phase8_holdout",
            "presentation outline still states the current holdout comparison with Phase 7 ahead of Phase 8 and the explicit 2024/2025 split",
        )
    )
    checks.append(
        require(
            expected_anchor_line in text
            and expected_anchor_split_line in text
            and expected_cd_split_line in text
            and expected_op_refined_split_line in text
            and expected_anchor_fold_line in text
            and expected_slide5_short_line in text,
            "op_anchor_lines",
            "presentation outline now pins the 2024-vs-2025 split for the current anchor / paper / watch trio, so the speaking surface explains sample-vs-stability tradeoffs directly",
        )
    )
    checks.append(
        require(
            expected_observation_only_line in text and expected_observation_only_detail in text,
            "observation_only_pockets",
            "presentation outline now says plainly that KEE_K9, SA_K9, and DMR_FALL_K7 stay observation-only pockets rather than near-promotion cases",
        )
    )
    checks.append(
        require(
            expected_guardrail_header in text
            and all(line in text for line in expected_guardrail_lines)
            and expected_guardrail_outro in text
            and expected_guardrail_replay_line in text
            and expected_guardrail_honesty_line in text,
            "method_family_guardrail_section",
            "presentation outline now carries an explicit selective / Harville / XGBoost guardrail block plus the current paper anchor/shadow ordering inside the selective family and the replay-only caution on broader selective-family secondary lines",
        )
    )
    checks.append(
        require(
            expected_ml_line in text,
            "ml_failure_line",
            "presentation outline still states plainly that ML/XGBoost did not improve betting decisions in a usable way",
        )
    )
    checks.append(
        require(
            expected_full_data_retrain_guardrail_line in text
            and expected_full_data_retrain_qa_line in text
            and all(line in text for line in expected_full_data_retrain_artifact_lines),
            "full_data_retrain_caveat_route_present",
            "presentation outline now routes full-data XGBoost retrain artifact and exact retrain/prediction command questions to FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py while keeping large RMSE / MAE gains in model-fit reproducibility context only",
        )
    )
    checks.append(
        require(
            expected_workflow_not_proof_line in text and expected_settled_evidence_line in text,
            "paper_trade_workflow_not_live_proof",
            "presentation outline now says plainly that a clean first paper-trade run proves workflow/observation capture, not that the edge is already confirmed live, and that genuinely new forward evidence still requires settled paper trades",
        )
    )
    checks.append(
        require(
            expected_evidence_scope_line in text and expected_q5_evidence_scope in text,
            "presentation_evidence_scope_gate",
            "presentation outline now says decision-posture changes require settled paper-trade rows with usable ROI coverage, not clean scans, open signals, replay rows, calibration summaries, or another odds-only rerun",
        )
    )
    checks.append(
        require(
            current_evidence["source_consistency"]["overall_match"] is True
            and recommendation_context.get("latest_context_has_bet_ready_language") is False
            and recommendation_context.get("not_forward_performance_evidence") is True
            and recommendation_context.get("not_bet_readiness_evidence_by_itself") is True
            and (api_access_action_route_present if api_access_action_route_required else True)
            and expected_decision_gate_source_line in text
            and all(line in text for line in expected_current_evidence_lines)
            and all(line in text for line in expected_current_evidence_artifact_lines)
            and "- Do not change rules from 4 settled misses." not in text,
            "current_evidence_bridge_slide",
            f"presentation outline now has a dedicated current paper-read bridge that routes paper totals through CURRENT_EVIDENCE_SUMMARY.md / current_evidence_summary.json, pins source consistency, routes wrapper-refresh/missing-output/stale or API-failure right-now cards through the combined operator-status/source-freshness/operator-read-gate path, keeps the scorecard-sourced current gates visible and avoids pinning rule-change caution to the current miss count, preserves the source-derived {queue_recommendation_context_label} as workflow context rather than bet-ready or forward-performance proof, separates the CD-only settled sample from OP-anchor evidence, and blocks rule changes, OP_REFINED_K7 / Phase 8 promotion, BAQ/BEL substitution, bankroll guidance, and real-money claims from the tiny current sample",
        )
    )
    checks.append(
        require(
            expected_queue_context_line in text
            and expected_queue_artifact_line in text
            and "Current open-row context: `none`" not in text
            and "current open-row context: `none`" not in text
            and "The current bridge has no open primary settlement rows; the closed settlement queue" not in text,
            "source_published_settlement_queue_state",
            "presentation outline consumes the bridge-published settlement queue state/context/detail and does not render a closed queue as open-row `none` or raw closed-queue prose",
        )
    )
    checks.append(
        require(
            expected_source_freshness_line in text
            and expected_bridge_repair_line in text
            and "source_freshness.requires_refresh_before_right_now_use" in text
            and "operator_read_gate.requires_refresh_before_evidence_read" in text
            and (not requires_refresh or "./run_daily_portfolio_observation.sh" in text),
            "current_evidence_combined_operator_read_route",
            "presentation outline now carries the combined operator_status_context / source_freshness / operator_read_gate route, so refresh-required right-now cards trigger the daily wrapper and fresh cards stay in current operator-routing context before instruction or evidence use",
        )
    )
    checks.append(
        require(
            expected_operator_read_gate_line in text
            and expected_current_evidence_artifact_lines[4] in text
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
            "presentation outline now carries current_evidence_summary.json operator_read_gate as refresh-before-evidence-read routing before stale, stale-cache fallback, or missing-state top-card instruction/evidence use, without treating that state as no-target, clean-empty, bet-readiness, settled-ROI, forward-performance, promotion, live-profitability, bankroll, or real-money evidence",
        )
    )
    checks.append(
        require(
            expected_scorecard_audit_route_line in text
            and expected_current_evidence_artifact_lines[5] in text
            and scorecard_audit_route_json_read.get("source") == "current_evidence_summary.json"
            and scorecard_audit_route_json_read.get("source_path") == "scorecard_audit_route"
            and scorecard_audit_route_json_read.get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route_json_read.get("json_path") == "scorecard_ranking_contract_audit.json"
            and scorecard_audit_route_json_read.get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route_json_read.get("gate_floor_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and scorecard_audit_route_json_read.get("gate_floor_snapshot", {}).get(
                "anchor_displacement_min_roi_complete_settled_observations"
            )
            == 30
            and scorecard_audit_route_json_read.get("gate_floor_snapshot", {}).get(
                "phase8_promotion_review_min_roi_complete_settled_observations"
            )
            == 20
            and scorecard_audit_route_json_read.get("gate_floor_snapshot", {}).get(
                "real_money_discussion_min_total_settled_observations_with_usable_roi"
            )
            == 100
            and scorecard_audit_route_json_read.get("gate_floor_snapshot", {}).get("real_money_no_baq_as_bel_required")
            is True
            and scorecard_audit_route_json_read.get("artifacts_present") is True
            and scorecard_audit_route_json_read.get("not_forward_performance_evidence") is True
            and scorecard_audit_route_json_read.get("not_settled_roi_evidence") is True
            and scorecard_audit_route_json_read.get("not_promotion_readiness_evidence") is True
            and scorecard_audit_route_json_read.get("not_live_profitability_evidence") is True
            and scorecard_audit_route_json_read.get("not_bankroll_guidance") is True
            and scorecard_audit_route_json_read.get("not_real_money_evidence") is True,
            "current_evidence_scorecard_audit_route_present",
            "presentation outline now carries current_evidence_summary.json scorecard_audit_route to the scorecard ranking-contract audit for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks while keeping that route out of forward performance, settled ROI, promotion readiness, live profitability, bankroll, and real-money evidence",
        )
    )
    checks.append(
        require(
            expected_rebuild_validation_contract_line in text
            and expected_current_evidence_artifact_lines[6] in text
            and rebuild_validation_contract_json_read.get("source") == "current_evidence_summary.json"
            and rebuild_validation_contract_json_read.get("source_path") == "rebuild_validation_contract"
            and rebuild_validation_contract_json_read.get("upstream_refresh_order")
            == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and rebuild_validation_contract_json_read.get("prerequisite_rebuild_command")
            == "python3 paper_trade_settlement_audit.py"
            and rebuild_validation_contract_json_read.get("rebuild_command") == "python3 current_evidence_summary.py"
            and rebuild_validation_contract_json_read.get("direct_validation_command")
            == "python3 validate_current_evidence_summary.py"
            and rebuild_validation_contract_json_read.get(
                "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
            )
            is True
            and rebuild_validation_contract_json_read.get("requires_source_consistency_before_quoting_current_totals")
            is True
            and rebuild_validation_contract_json_read.get("upstream_refresh_order_is_provenance_metadata_only")
            is True
            and rebuild_validation_contract_json_read.get("not_settled_roi_or_real_money_evidence") is True,
            "current_evidence_rebuild_validation_contract_route",
            "presentation outline now carries current_evidence_summary.json rebuild_validation_contract so slide readers know to refresh settlement audit before rebuilding/validating the current bridge after source-byte changes, while keeping the route as provenance/rebuild metadata rather than settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
        )
    )
    checks.append(
        require(
            expected_cross_family_caveat_slide_line in text
            and expected_current_evidence_artifact_lines[-1] in text,
            "cross_family_current_paper_route_present",
            "presentation outline now routes anchor / paper / watch current-paper caveat questions to CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py and keeps stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green presentation validation out of OP-anchor proof or cross-family promotion evidence",
        )
    )
    checks.append(
        require(
            current_source_consistency.get("overall_match") is True
            and current_roi_rows.get("paper_trade_now")
            == current_roi_rows.get("settlement_audit")
            == current_roi_rows.get("settlement_csv_recomputed")
            and current_open_rows.get("paper_trade_now") == current_open_rows.get("settlement_audit")
            and current_incomplete_rows.get("paper_trade_now") == current_incomplete_rows.get("settlement_audit")
            and current_roi_gap_rows.get("paper_trade_now") == current_roi_gap_rows.get("settlement_audit")
            and source_freshness.get("right_now_freshness_state_valid") is True
            and isinstance(source_freshness.get("requires_refresh_before_right_now_use"), bool)
            and current_gate_minimums.get("source_path") == "forward_evidence_scorecard.json"
            and current_gate_minimums.get("source_loaded") is True
            and current_gate_minimums.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and current_gate_minimums.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and current_gate_minimums.get("real_money_discussion_min_total_settled_observations_with_usable_roi")
            == 100
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
            "current_evidence_bridge_json_is_source_gate_routed",
            "presentation-outline child JSON now exposes the current-evidence bridge's source-consistent top-card/audit/CSV read, valid source-freshness route, and directly scorecard-sourced 30/20/100 gates instead of relying only on prose in the slide read",
        )
    )
    checks.append(
        require(
            current_gate_minimums.get("source_values_match_scorecard") is True
            and current_gate_minimums.get("effective_values_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and current_gate_minimums.get("missing_top_card_fields") == []
            and current_gate_minimums.get("mismatched_fields") == []
            and current_gate_top_card_values == current_gate_scorecard_values == current_gate_effective_values
            and current_gate_effective_values.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and current_gate_effective_values.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and current_gate_effective_values.get("real_money_discussion_min_total_settled_observations_with_usable_roi")
            == 100
            and current_gate_threshold_sources.get("anchor_displacement")
            == "forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations"
            and current_gate_threshold_sources.get("phase8_promotion_review")
            == "forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations"
            and current_gate_threshold_sources.get("real_money_discussion")
            == "forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
            "current_evidence_bridge_effective_gates_are_scorecard_backed",
            "presentation-outline child JSON now preserves the current-evidence bridge's canonical scorecard-backed effective gate values, top-card/scorecard alignment state, missing/mismatched gate lists, and exact threshold-source paths so report rollups cannot flatten copied top-card fields into the canonical 30/20/100 floors",
        )
    )
    checks.append(
        require(
            expected_short_reco in text,
            "short_recommendation",
            "presentation outline still ends with the Phase 7 core paper-trade recommendation and the settled ROI-complete gate",
        )
    )

    suite_read = (
        f"presentation outline matches frozen posture: anchor={anchor['rule_id']} ({float(anchor['holdout_roi']):+.1f}% on {int(anchor['holdout_races'])}; "
        f"2024={float(anchor['holdout_2024_roi']):+.2f}% on {int(anchor['holdout_2024_races'])}, "
        f"2025={float(anchor['holdout_2025_roi']):+.2f}% on {int(anchor['holdout_2025_races'])}); "
        f"paper={phase7['label']} ({float(phase7['holdout_roi']):+.2f}% on {int(phase7['holdout_races'])}; 2024={float(phase7['holdout_2024_roi']):+.2f}% on {int(phase7['holdout_2024_races'])}, 2025={float(phase7['holdout_2025_roi']):+.2f}% on {int(phase7['holdout_2025_races'])}); "
        f"selector benchmark={selector['label']} ({float(selector['wf_roi']):+.2f}% WF, {float(selector['holdout_roi']):+.2f}% holdout); "
        f"Phase 8={phase8['role']} ({float(phase8['holdout_roi']):+.2f}% on {int(phase8['holdout_races'])}; 2024={float(phase8['holdout_2024_roi']):+.2f}% on {int(phase8['holdout_2024_races'])}, 2025={float(phase8['holdout_2025_roi']):+.2f}% on {int(phase8['holdout_2025_races'])}); method roles={selective['role']} / {harville['role']} / {xgboost['role']}; full-data retrain caveat route=FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py, with large RMSE / MAE gains and exact retrain/prediction commands kept as model-fit reproducibility context rather than paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence; first paper-trade run=workflow/observation proof, not live-edge confirmation; genuinely new forward evidence still requires settled paper trades; evidence scope=settled paper-trade rows with usable ROI coverage can change posture, while clean scans/open signals/historical replay/calibration-only summaries/odds-only reruns cannot; presentation gates source-matched to forward_evidence_scorecard.json decision_gate_minimums with anchor_displacement={scorecard_anchor_min}, phase8_promotion_review={scorecard_phase8_min}, and real_money_discussion={scorecard_real_money_min}; current evidence bridge=CURRENT_EVIDENCE_SUMMARY.md/current_evidence_summary.json source consistency {source_consistency_label}, combined operator-status/source-freshness/operator-read-gate route {combined_operator_route_label}, primary paper {current_first_read['current']}/{current_first_read['threshold']} first-read and {current_portfolio_review['current']}/{current_portfolio_review['threshold']} broader-review gates, CD_CORE_K8={rule_progress['CD_CORE_K8']['roi_complete_settled_rows']} ROI-complete rows, OP_DURABLE_K7={rule_progress['OP_DURABLE_K7']['roi_complete_settled_rows']} ROI-complete rows, current settled sample is CD-only context and not OP-anchor evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence; operator_read_gate read={operator_read_gate_read}; scorecard audit route=current_evidence_summary.json.scorecard_audit_route to {scorecard_audit_route['markdown_path']} / {scorecard_audit_route['json_path']} plus {scorecard_audit_route['validator_command']} for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks as report-synchronization metadata only; rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only; {suite_queue_context}; direct cross-family current-paper caveat route=CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py, with stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green presentation validation not OP-anchor proof or cross-family promotion evidence; broader selective-family secondary lines elsewhere stay replay-context rather than extra train-only proof; selective paper-companion read anchor={selective['current_anchor']}, paper companion={selective['primary_shadow']}, closest shadow={selective['secondary_shadow']}; remaining Phase 8 pockets=KEE_K9 / SA_K9 / DMR_FALL_K7 stay observation-only rather than near-promotion cases"
    )

    payload = {
        "suite_status": "pass",
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "current_evidence_bridge_json_read": current_bridge_json_read,
        "current_evidence_operator_read_gate_read": operator_read_gate_json_read,
        "current_evidence_scorecard_audit_route_read": scorecard_audit_route_json_read,
        "current_evidence_rebuild_validation_contract_read": rebuild_validation_contract_json_read,
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
        "# Cole Presentation Outline Validation",
        "",
        "This report checks that `COLE_PRESENTATION_OUTLINE.md` stays aligned with the frozen evaluation standard and now carries the explicit method-family and evidence-scope guardrails.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Target file: `{OUTLINE.name}`",
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
            f"- Guardrail header: {expected_guardrail_header}",
            f"- Method-family roles: {selective['role']} / {harville['role']} / {xgboost['role']}",
            f"- Full-data retrain caveat line: {expected_full_data_retrain_guardrail_line}",
            f"- Full-data retrain Q&A line: {expected_full_data_retrain_qa_line}",
            f"- Full-data retrain artifact line: {expected_full_data_retrain_artifact_lines[-1]}",
            f"- Selective-family paper-companion read: anchor={selective['current_anchor']}, paper companion={selective['primary_shadow']}, closest shadow={selective['secondary_shadow']}",
            f"- Phase 7 line: {expected_phase7_line}",
            f"- Phase 8 line: {expected_phase8_line}",
            f"- Anchor split line: {expected_anchor_split_line}",
            f"- CD split line: {expected_cd_split_line}",
            f"- OP refined split line: {expected_op_refined_split_line}",
            f"- Observation-only line: {expected_observation_only_line}",
            f"- Evidence-scope line: {expected_evidence_scope_line}",
            f"- Decision-gate source line: {expected_decision_gate_source_line}",
            f"- Current-evidence bridge line: {expected_current_evidence_lines[3]}",
            f"- Current-evidence freshness line: {expected_source_freshness_line}",
            f"- Current-evidence operator read gate line: {expected_operator_read_gate_line}",
            f"- Current-evidence scorecard audit route line: {expected_scorecard_audit_route_line}",
            f"- Current-evidence rebuild-order route line: {expected_rebuild_validation_contract_line}",
            f"- Current-evidence gate line: {expected_bridge_repair_line}",
            f"- Direct cross-family caveat slide line: {expected_cross_family_caveat_slide_line}",
            f"- Direct cross-family artifact line: {expected_current_evidence_artifact_lines[-1]}",
            f"- Current-evidence rule-mix line: {expected_current_evidence_lines[9]}",
            f"- Current recommendation context line: {expected_current_evidence_lines[10]}",
            f"- Current settlement-queue context line: {expected_current_evidence_lines[11]}",
            "",
            "## Source Artifacts",
            "",
            f"- `{SCORECARD_CSV.name}`",
            f"- `{SCORECARD_JSON.name}`",
            f"- `{scorecard_audit_route['markdown_path']}`",
            f"- `{scorecard_audit_route['json_path']}`",
            f"- `{str(scorecard_audit_route['validator_command']).split()[-1]}`",
            f"- `{PORTFOLIO_CSV.name}`",
            f"- `{METHOD_CSV.name}`",
            f"- `{CURRENT_EVIDENCE_JSON.name}`",
            "- `validate_current_evidence_summary.py`",
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
