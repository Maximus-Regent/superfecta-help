#!/usr/bin/env python3
"""
Run the main report-facing narrative validators together.

Purpose:
- give Cole one command for the fast-read repo and report surfaces
- keep README, the long-form report, the working-status report, the presentation outline, and the shareable HTML report aligned with the frozen evidence standard
- keep the shareable dated PDF refresh/check helper pinned to the dated HTML trust anchor rather than a separate evidence source
- summarize whether the main human-facing story still matches the current conservative deployment posture
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import validate_cole_full_report as full_report
import validate_cole_presentation_outline as presentation_outline
import validate_readme_current_status as readme_status
import validate_refresh_shareable_report_pdf as pdf_refresh_helper
import validate_superfecta_html_report as html_report
import validate_working_status_report as working_status_report

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "out" / "status_validation" / "report_surfaces"
OUT_MD = OUT_DIR / "report_surfaces_validation.md"
OUT_JSON = OUT_DIR / "report_surfaces_validation.json"
REBUILD_COMMAND = "python3 validate_report_surfaces.py"
REUSE_EXISTING_FLAG = "--reuse-existing-child-json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "human-facing report-surface validator rollup",
    "source_scope": [
        "README current-status validator output",
        "long-form markdown report validator output",
        "dated working-status report validator output",
        "presentation-outline validator output",
        "shareable HTML report validator output",
        "shareable PDF refresh helper validator output",
    ],
    "valid_use": "shareable-wording, presentation-drift, dated-report trust-path, PDF derivative refresh-helper, and narrative alignment audit for Cole-facing report surfaces",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "report_validator_passes_are_alignment_metadata_only": True,
    "stronger_forward_confidence_requires": [
        "qualifying live paper signals",
        "ROI-complete settled paper rows",
        "settlement-quality checks",
        "other real forward observations",
    ],
    "non_goals": [
        "do not use a green report-surface sweep as settled ROI",
        "do not use report wording alignment as live profitability evidence",
        "do not promote OP_REFINED_K7 or Phase 8 from narrative validation cleanliness",
        "do not reopen current odds-only XGBoost from narrative validation cleanliness",
        "do not substitute BAQ for BEL",
        "do not treat refreshed HTML/PDF surfaces or PDF refresh-helper outputs as real-money evidence",
    ],
}

SUITE: list[dict[str, Any]] = [
    {
        "name": "readme_current_status",
        "label": "README current status",
        "runner": readme_status.main,
        "json_path": BASE / "out" / "status_validation" / "readme_current_status" / "readme_current_status_validation.json",
        "metric": lambda payload: int(payload.get("check_count", 0)),
        "metric_label": "checks",
        "passed": lambda payload: payload.get("suite_status") == "pass",
        "current_read": lambda payload: payload.get("summary", {}).get("suite_read", ""),
    },
    {
        "name": "cole_full_report",
        "label": "Cole full report",
        "runner": full_report.main,
        "json_path": BASE / "out" / "status_validation" / "cole_full_report" / "cole_full_report_validation.json",
        "metric": lambda payload: int(payload.get("check_count", 0)),
        "metric_label": "checks",
        "passed": lambda payload: payload.get("suite_status") == "pass",
        "current_read": lambda payload: payload.get("summary", {}).get("suite_read", ""),
    },
    {
        "name": "working_status_report",
        "label": "Working status report",
        "runner": working_status_report.main,
        "json_path": BASE / "out" / "status_validation" / "working_status_report" / "working_status_report_validation.json",
        "metric": lambda payload: int(payload.get("check_count", 0)),
        "metric_label": "checks",
        "passed": lambda payload: payload.get("suite_status") == "pass",
        "current_read": lambda payload: payload.get("summary", {}).get("suite_read", ""),
    },
    {
        "name": "cole_presentation_outline",
        "label": "Cole presentation outline",
        "runner": presentation_outline.main,
        "json_path": BASE / "out" / "status_validation" / "cole_presentation_outline" / "cole_presentation_outline_validation.json",
        "metric": lambda payload: int(payload.get("check_count", 0)),
        "metric_label": "checks",
        "passed": lambda payload: payload.get("suite_status") == "pass",
        "current_read": lambda payload: payload.get("summary", {}).get("suite_read", ""),
    },
    {
        "name": "superfecta_html_report",
        "label": "Superfecta HTML report",
        "runner": html_report.main,
        "json_path": BASE / "out" / "status_validation" / "superfecta_html_report" / "superfecta_html_report_validation.json",
        "metric": lambda payload: int(payload.get("check_count", 0)),
        "metric_label": "checks",
        "passed": lambda payload: payload.get("suite_status") == "pass",
        "current_read": lambda payload: payload.get("summary", {}).get("suite_read", ""),
    },
    {
        "name": "shareable_report_pdf_refresh",
        "label": "Shareable PDF refresh helper",
        "runner": pdf_refresh_helper.main,
        "json_path": BASE / "out" / "status_validation" / "refresh_shareable_report_pdf" / "refresh_shareable_report_pdf_validation.json",
        "metric": lambda payload: int(payload.get("check_count", 0)),
        "metric_label": "checks",
        "passed": lambda payload: payload.get("suite_status") == "pass",
        "current_read": lambda payload: payload.get("summary", {}).get("suite_read", ""),
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        REUSE_EXISTING_FLAG,
        dest="reuse_existing_child_json",
        action="store_true",
        help="reuse existing child validator JSON artifacts instead of rerunning every child suite",
    )
    return parser.parse_args()


def run_validator(fn: Callable[[], int | None], label: str) -> None:
    result = fn()
    if result not in (None, 0):
        raise AssertionError(f"{label} returned non-zero status: {result}")


def load_child_payload(item: dict[str, Any], reuse_existing_child_json: bool) -> dict[str, Any]:
    if reuse_existing_child_json:
        if not item["json_path"].exists():
            raise AssertionError(
                f"{item['label']} reuse requested but child JSON is missing: {item['json_path']}"
            )
    else:
        run_validator(item["runner"], item["label"])
        if not item["json_path"].exists():
            raise AssertionError(f"{item['label']} did not write expected child JSON: {item['json_path']}")
    return json.loads(item["json_path"].read_text(encoding="utf-8"))


def require(condition: bool, label: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    return {"check": label, "status": "pass", "detail": detail}


def has_timezone_aware_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parse_text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(parse_text)
    except ValueError:
        return False
    return parsed.utcoffset() is not None


def require_child_status(payload: dict[str, Any], label: str) -> str:
    artifact = payload.get("artifact")
    for candidate in (
        payload.get("suite_status"),
        artifact.get("status") if isinstance(artifact, dict) else None,
        payload.get("artifact_status"),
        payload.get("result"),
        payload.get("status"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip().upper()
    raise AssertionError(f"{label} child JSON is missing an explicit status field")


def require_child_check_count(payload: dict[str, Any], label: str) -> int:
    value = payload.get("check_count")
    if isinstance(value, bool) or not isinstance(value, int):
        raise AssertionError(f"{label} child JSON is missing explicit integer check_count")
    return value


def require_child_checks(payload: dict[str, Any], label: str) -> list[dict[str, Any]]:
    checks = payload.get("checks")
    if not isinstance(checks, list):
        raise AssertionError(f"{label} child JSON is missing checks list")
    return checks


def require_child_read(payload: dict[str, Any], label: str) -> str:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise AssertionError(f"{label} child JSON is missing summary metadata")
    for key in ("suite_read", "current_read"):
        value = summary.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise AssertionError(f"{label} child JSON is missing summary.suite_read/current_read")


def build_suite_read(rows: list[dict[str, Any]]) -> str:
    row_map = {row["name"]: row for row in rows}
    return (
        f"README: {row_map['readme_current_status']['current_read']}; "
        f"full report: {row_map['cole_full_report']['current_read']}; "
        f"working status report: {row_map['working_status_report']['current_read']}; "
        f"presentation outline: {row_map['cole_presentation_outline']['current_read']}; "
        f"HTML report: {row_map['superfecta_html_report']['current_read']}; "
        f"PDF refresh helper: {row_map['shareable_report_pdf_refresh']['current_read']}; "
        "report-surfaces suite layer: saved narrative report surfaces, direct validator report paths, and the shareable PDF refresh/check helper path stay pinned across the human-facing rollup; shareable wording, presentation drift, the dated-report trust path, PDF derivative refresh-helper, and the README-inherited wrapper-leaf source-of-truth note stay explicit instead of getting flattened away; current-evidence generated_at provenance is checked as timezone-aware metadata before report-facing summaries quote the bridge; human-facing alignment and export reproducibility check, not new forward evidence by itself; stronger forward confidence still requires settled paper trades and other real forward results; machine-readable evidence_boundary metadata in the report-surface JSON keeps human-facing wording alignment, dated-report trust-path checks, PDF refresh-helper checks, and narrative validator passes separate from settled ROI, live profitability, promotion readiness, bankroll guidance, and real-money evidence"
    )


def current_rebuild_validation_contract_context(current_evidence: dict[str, Any]) -> dict[str, Any]:
    contract = current_evidence.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise AssertionError("current_evidence_summary.json must publish rebuild_validation_contract as an object")
    upstream_refresh_order = contract.get("upstream_refresh_order")
    if not isinstance(upstream_refresh_order, list):
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract must publish upstream_refresh_order")

    upstream_refresh_commands: list[str] = []
    upstream_refresh_order_numbers: list[int] = []
    for row in upstream_refresh_order:
        if not isinstance(row, dict):
            raise AssertionError("current_evidence_summary.json rebuild_validation_contract upstream rows must be objects")
        command = row.get("command")
        order = row.get("order")
        if not isinstance(command, str) or not command.strip():
            raise AssertionError("current_evidence_summary.json rebuild_validation_contract upstream commands must be strings")
        if isinstance(order, bool) or not isinstance(order, int):
            raise AssertionError("current_evidence_summary.json rebuild_validation_contract upstream order values must be integers")
        upstream_refresh_commands.append(command)
        upstream_refresh_order_numbers.append(order)

    expected_commands = [
        "python3 paper_trade_settlement_audit.py",
        "python3 current_evidence_summary.py",
        "python3 validate_current_evidence_summary.py",
    ]
    if upstream_refresh_commands != expected_commands:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract upstream order drifted")
    if upstream_refresh_order_numbers != [1, 2, 3]:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract upstream order numbers drifted")

    return {
        "source": CURRENT_EVIDENCE_JSON.name,
        "source_path": "rebuild_validation_contract",
        "upstream_refresh_order": upstream_refresh_commands,
        "upstream_refresh_order_numbers": upstream_refresh_order_numbers,
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


def main() -> int:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rebuild_command = REBUILD_COMMAND + (f" {REUSE_EXISTING_FLAG}" if args.reuse_existing_child_json else "")
    child_validator_mode = "reuse-existing-child-json" if args.reuse_existing_child_json else "rebuild-children"

    rows: list[dict[str, Any]] = []
    child_payloads: dict[str, Any] = {}
    total_checks = 0

    for item in SUITE:
        payload = load_child_payload(item, args.reuse_existing_child_json)
        child_payloads[item["name"]] = payload
        artifact_status = require_child_status(payload, item["label"])
        metric_value = require_child_check_count(payload, item["label"])
        child_checks = require_child_checks(payload, item["label"])
        current_read = require_child_read(payload, item["label"])
        total_checks += metric_value
        rows.append(
            {
                "name": item["name"],
                "label": item["label"],
                "metric_value": metric_value,
                "metric_label": item["metric_label"],
                "result": artifact_status,
                "current_read": current_read,
                "json_path": str(item["json_path"].relative_to(BASE)),
                "child_check_count": metric_value,
                "child_checks": child_checks,
            }
        )

    if not all(row["result"] == "PASS" for row in rows):
        raise AssertionError("Report surfaces suite has at least one failing validator")

    row_map = {row["name"]: row for row in rows}
    current_evidence = json.loads(CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8"))
    current_primary = current_evidence["current_paper_status"]["primary"]
    current_first_gate = f"{current_primary['first_read']['current']}/{current_primary['first_read']['threshold']}"
    current_portfolio_gate = f"{current_primary['portfolio_review']['current']}/{current_primary['portfolio_review']['threshold']}"
    current_gate_phrase = f"{current_first_gate} and {current_portfolio_gate} gates"
    current_report_gate_phrase = (
        f"primary paper {current_first_gate} first-read and {current_portfolio_gate} broader-review gates"
    )
    current_gate_progress = (
        current_evidence.get("decision_gate_progress")
        if isinstance(current_evidence.get("decision_gate_progress"), dict)
        else {}
    )
    current_gate_progress_read = str(current_gate_progress.get("read") or "").strip()
    current_open_settlements = int(current_primary.get("open_settlements", 0) or 0)
    current_open_queue = current_primary.get("open_settlement_queue_by_rule")
    if not isinstance(current_open_queue, dict):
        raise AssertionError("current_evidence_summary.json must publish current_paper_status.primary.open_settlement_queue_by_rule")
    current_open_queue_state = str(current_open_queue.get("open_settlement_queue_state") or "").strip()
    current_open_queue_context = str(current_open_queue.get("open_settlement_context") or "").strip()
    current_open_queue_detail_read = str(current_open_queue.get("detail_read") or "").strip()
    expected_current_open_queue_state = "closed" if current_open_settlements == 0 else "open"
    if current_open_queue_state != expected_current_open_queue_state:
        raise AssertionError("current-evidence open_settlement_queue_state must match open_settlements")
    if "Open settlement queue by rule:" not in current_open_queue_detail_read:
        raise AssertionError("current-evidence detail_read must carry by-rule open settlement detail")
    if "Settlement queue state:" in current_open_queue_detail_read:
        raise AssertionError("current-evidence detail_read must not nest the settlement queue state wrapper")
    bridge_queue_navigation = (
        "closed settlement-queue plus recommendation-state context"
        if current_open_settlements == 0
        else "current open-row identity plus recommendation-state context"
    )
    report_child_queue_context = (
        f"settlement queue state={current_open_queue_state} / context={current_open_queue_context}"
    )
    presentation_child_queue_context = report_child_queue_context
    report_child_queue_boundary = "source-published settlement queue state/detail boundary"
    report_child_queue_workflow_phrase = (
        "remains workflow context rather than a bet-ready ticket or forward-performance proof"
        if current_open_settlements == 0
        else "remains settlement workflow rather than a bet-ready ticket or forward-performance proof"
    )
    presentation_queue_boundary = "source-published settlement queue state/detail boundary"
    presentation_queue_workflow_phrase = (
        "remains workflow context"
        if current_open_settlements == 0
        else "remains settlement workflow"
    )
    working_status_queue_check_name = (
        "current_settlement_queue_recommendation_state_context"
        if current_open_settlements == 0
        else "current_open_row_recommendation_state_context"
    )
    working_child_queue_context = (
        f"settlement queue state={current_open_queue_state} / context={current_open_queue_context}"
    )
    working_child_queue_workflow_phrase = (
        "remains workflow context rather than a bet-ready ticket or forward-performance proof"
    )
    current_source_consistency = (
        current_evidence.get("source_consistency")
        if isinstance(current_evidence.get("source_consistency"), dict)
        else {}
    )
    current_source_freshness = (
        current_evidence.get("source_freshness")
        if isinstance(current_evidence.get("source_freshness"), dict)
        else {}
    )
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
    current_rebuild_contract_read = current_rebuild_validation_contract_context(current_evidence)
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
        "source_path": CURRENT_EVIDENCE_JSON.name,
        "generated_at": current_evidence.get("generated_at"),
        "generated_at_timezone_aware": has_timezone_aware_timestamp(current_evidence.get("generated_at")),
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
        "source_freshness_state": current_source_freshness.get("right_now_freshness_state"),
        "source_freshness_state_valid": current_source_freshness.get("right_now_freshness_state_valid"),
        "requires_refresh_before_right_now_use": current_source_freshness.get("requires_refresh_before_right_now_use"),
        "requires_refresh_reason": current_source_freshness.get("requires_refresh_reason"),
        "decision_gate_source": current_gate_minimums.get("source_path"),
        "decision_gate_source_loaded": current_gate_minimums.get("source_loaded"),
        "anchor_displacement_min": current_gate_minimums.get("anchor_displacement_min_roi_complete_settled_observations"),
        "phase8_promotion_review_min": current_gate_minimums.get("phase8_promotion_review_min_roi_complete_settled_observations"),
        "real_money_discussion_min": current_gate_minimums.get("real_money_discussion_min_total_settled_observations_with_usable_roi"),
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
        "rebuild_validation_contract": current_rebuild_contract_read,
    }
    presentation_bridge_json_read = child_payloads["cole_presentation_outline"].get(
        "current_evidence_bridge_json_read"
    )
    if not isinstance(presentation_bridge_json_read, dict):
        presentation_bridge_json_read = {}
    full_report_bridge_json_read = child_payloads["cole_full_report"].get("current_evidence_bridge_json_read")
    if not isinstance(full_report_bridge_json_read, dict):
        full_report_bridge_json_read = {}
    source_freshness_label = (
        "requires refresh before right-now use"
        if current_evidence["source_freshness"].get("requires_refresh_before_right_now_use")
        else "fresh for right-now use"
    )
    combined_operator_read_route_phrase = (
        "combined operator-status/source-freshness/operator-read-gate route "
        "requires refresh before right-now instruction or evidence use"
        if current_evidence["source_freshness"].get("requires_refresh_before_right_now_use")
        else "combined operator-status/source-freshness/operator-read-gate route "
        "is fresh against the bridge reference date but still goes through operator read-gate routing before right-now instruction or evidence use"
    )
    report_operator_read_route_phrase = combined_operator_read_route_phrase
    full_report_operator_read_route_phrase = combined_operator_read_route_phrase
    presentation_operator_read_route_phrase = combined_operator_read_route_phrase
    working_operator_read_route_phrase = (
        combined_operator_read_route_phrase
    )
    expected_operator_read_gate = (
        current_evidence.get("operator_read_gate")
        if isinstance(current_evidence.get("operator_read_gate"), dict)
        else {}
    )
    expected_operator_read_gate_read = str(expected_operator_read_gate.get("read") or "").strip()
    expected_operator_read_gate_line = f"operator_read_gate read={expected_operator_read_gate_read}"
    expected_operator_requires_refresh = bool(
        expected_operator_read_gate.get("requires_refresh_before_evidence_read")
    )
    expected_operator_recommended_command = expected_operator_read_gate.get("recommended_command")
    expected_operator_has_api_access_failure = bool(expected_operator_read_gate.get("has_api_access_failure_context"))
    expected_operator_has_scanner_failure = bool(expected_operator_read_gate.get("has_scanner_failure_boundary"))
    expected_operator_has_stale_cache_fallback = bool(expected_operator_read_gate.get("has_stale_cache_fallback_context"))
    expected_api_access_action_route_required = bool(
        expected_operator_has_api_access_failure
        or expected_operator_has_scanner_failure
        or expected_operator_has_stale_cache_fallback
    )

    def child_operator_gate_matches(child_name: str) -> bool:
        read = child_payloads[child_name].get("current_evidence_operator_read_gate_read")
        return (
            isinstance(read, dict)
            and read.get("source") == "current_evidence_summary.json"
            and read.get("source_path") == "operator_read_gate"
            and read.get("gate_status")
            in {"refresh_required_before_evidence_read", "current_operator_routing_context_only"}
            and read.get("valid_use") == "operator instruction/evidence-read gating only"
            and read.get("requires_refresh_before_evidence_read") is expected_operator_requires_refresh
            and read.get("has_api_access_failure_context") is expected_operator_has_api_access_failure
            and read.get("has_scanner_failure_boundary") is expected_operator_has_scanner_failure
            and read.get("has_stale_cache_fallback_context") is expected_operator_has_stale_cache_fallback
            and read.get("recommended_command") == expected_operator_recommended_command
            and read.get("current_top_card_counts_as_no_target_evidence") is False
            and read.get("current_top_card_counts_as_clean_empty_evidence") is False
            and read.get("current_top_card_counts_as_bet_readiness_evidence") is False
            and read.get("current_top_card_counts_as_settled_roi_evidence") is False
            and read.get("not_live_profitability_evidence") is True
            and read.get("not_real_money_evidence") is True
        )

    def readme_api_route_matches() -> bool:
        read = child_payloads["readme_current_status"].get("current_evidence_api_access_route_read")
        return (
            isinstance(read, dict)
            and read.get("source") == "current_evidence_summary.json"
            and read.get("source_path") == "current_paper_status.primary.recommendation_context.read"
            and read.get("route_required") is expected_api_access_action_route_required
            and read.get("readme_has_sidecar_action") is expected_api_access_action_route_required
            and read.get("readme_has_recheck_command") is expected_api_access_action_route_required
            and read.get("source_has_sidecar_action") is expected_api_access_action_route_required
            and read.get("source_has_recheck_command") is expected_api_access_action_route_required
        )
    checks = [
        require(
            has_timezone_aware_timestamp(current_evidence.get("generated_at"))
            and current_bridge_json_read["generated_at_timezone_aware"] is True
            and current_bridge_json_read["generated_at"] == current_evidence.get("generated_at")
            and current_bridge_json_read["source_path"] == CURRENT_EVIDENCE_JSON.name,
            "report_surfaces_current_evidence_generated_at_is_timezone_aware",
            f"report-surface parent JSON now records current_evidence_summary.json generated_at={current_evidence.get('generated_at')!r} as parseable timezone-aware provenance metadata before report-facing summaries quote the current bridge",
        ),
        require(
            "anchor=OP_DURABLE_K7" in row_map["readme_current_status"]["current_read"]
            and "2024=" in row_map["readme_current_status"]["current_read"]
            and "2025=" in row_map["readme_current_status"]["current_read"]
            and "frozen-evidence ordering check rather than new proof" in row_map["readme_current_status"]["current_read"]
            and "cross-layer alignment check rather than new forward evidence" in row_map["readme_current_status"]["current_read"]
            and "recent-run context plus lifted lane why-now lines" in row_map["readme_current_status"]["current_read"]
            and "direct primary/shadow pipeline/scanner status-sidecar pointers" in row_map["readme_current_status"]["current_read"]
            and "stale downstream lane details as inherited snapshot context rather than current-day state" in row_map["readme_current_status"]["current_read"]
            and "frozen-to-current bridge `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` now visible for short Cole updates" in row_map["readme_current_status"]["current_read"]
            and "current_evidence_summary.json scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus validate_scorecard_ranking_contract_audit.py for copied gate-floor/ranking/CI-only/timezone/no-BAQ prerequisite drift as synchronization metadata only" in row_map["readme_current_status"]["current_read"]
            and f"source consistency, the combined operator-status/source-freshness/operator-read-gate route, CD-only current rule mix, {bridge_queue_navigation}, scorecard_audit_route synchronization routing" in row_map["readme_current_status"]["current_read"]
            and "rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only" in row_map["readme_current_status"]["current_read"]
            and "bridge-published current gates source-matched to `forward_evidence_scorecard.json` `decision_gate_minimums`" in row_map["readme_current_status"]["current_read"]
            and "scorecard_audit_route synchronization routing to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization metadata only" in row_map["readme_current_status"]["current_read"]
            and "bridge-owned rebuild-order routing in the report inventory" in row_map["readme_current_status"]["current_read"]
            and f"direct `decision_gate_progress` read={current_gate_progress_read}" in row_map["readme_current_status"]["current_read"]
            and expected_operator_read_gate_line in row_map["readme_current_status"]["current_read"]
            and "source-published settlement queue state/detail read=" in row_map["readme_current_status"]["current_read"]
            and "anchor_displacement=30, phase8_promotion_review=20, and real_money_discussion=100" in row_map["readme_current_status"]["current_read"]
            and "no-new-forward-evidence / no-promotion / no-live-profitability / no-real-money boundaries" in row_map["readme_current_status"]["current_read"]
            and "daily guide now also explicitly pointing issue-day triage at those top-card sidecar pointers" in row_map["readme_current_status"]["current_read"]
            and "direct cross-family current-paper validation path now pins stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and no OP-anchor / no cross-family-promotion evidence" in row_map["readme_current_status"]["current_read"]
            and "direct one-screen main comparison route `compare_main_approaches.md` plus matched CSV/JSON sidecars" in row_map["readme_current_status"]["current_read"]
            and "Harville benchmark-only lane, current odds-only XGBoost research-only lane" in row_map["readme_current_status"]["current_read"]
            and "machine-readable evidence boundary as reproducibility/navigation metadata rather than new evidence" in row_map["readme_current_status"]["current_read"]
            and "direct full-data XGBoost retrain caveat route `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py`" in row_map["readme_current_status"]["current_read"]
            and "RMSE / MAE diagnostics in model-fit context only rather than paper-trade, live-profitability, promotion, bankroll, or real-money evidence" in row_map["readme_current_status"]["current_read"]
            and "generated main-comparison markdown/CSV/JSON bundle plus direct validator in the report inventory" in row_map["readme_current_status"]["current_read"]
            and "full-data retrain artifact plus direct validator in the report inventory" in row_map["readme_current_status"]["current_read"]
            and "scorecard audit markdown/JSON plus direct validator in the report inventory as synchronization/reproducibility metadata only" in row_map["readme_current_status"]["current_read"]
            and "source-checked current-evidence bridge with the combined operator-read route plus direct validator, bridge-owned scorecard-audit routing, and bridge-owned rebuild-order routing in the report inventory" in row_map["readme_current_status"]["current_read"]
            and "main status / repo-map route `COLE_STATUS_AND_PLAN.md` plus `validate_cole_status_and_plan.py` now visible for `status_doc_base_api_access_route_documented` base API-access / HTTP 403 status-summary route wording before lane enrichment as status/map alignment metadata only" in row_map["readme_current_status"]["current_read"]
            and "main status document plus direct validator in the report inventory" in row_map["readme_current_status"]["current_read"]
            and "rebuilt top-card recent-run context plus lifted lane why-now lines preserved when current lane artifacts provide them" in row_map["readme_current_status"]["current_read"]
            and "stale rebuilt cards keeping the inherited-snapshot honesty note" in row_map["readme_current_status"]["current_read"]
            and "routed top-card snapshot inheritance" in row_map["readme_current_status"]["current_read"]
            and "operator_read_gate no-evidence routing" in row_map["readme_current_status"]["current_read"]
            and "`--latest-only` confined to the newest copied run's preflight, lane, and daily-summary surfaces" in row_map["readme_current_status"]["current_read"]
            and "`--skip-top-level` confined to leaving `OPS_HISTORY` / `PAPER_TRADE_NOW` untouched while still rerendering those per-run surfaces against the existing top-level outputs" in row_map["readme_current_status"]["current_read"]
            and "explicit `--as-of-date` freshness pinning that now says whether it was applied or skipped because top-level outputs were refreshed or skipped" in row_map["readme_current_status"]["current_read"]
            and "the real daily-wrapper validator as the other source-of-truth wrapper leaf" in row_map["readme_current_status"]["current_read"]
            and "wrapper-generated CURRENT_EVIDENCE_SUMMARY refresh/placeholder plus source-backed recommendation-context/open-row separation before Cole-facing current-paper wording" in row_map["readme_current_status"]["current_read"]
            and "the operator-suite sweep should preserve those inherited wrapper-guardrail inventories rather than flattening them" in row_map["readme_current_status"]["current_read"],
            "readme_keeps_anchor_and_split_read",
            f"README rollup still carries OP_DURABLE_K7 plus the split-aware 2024/2025 Phase 7 posture, keeps the landing-page top operator read aligned to recent-run context plus lifted lane why-now lines, direct sidecar pointers, matched operator_read_gate routing, and the stale-card inherited-snapshot honesty note, keeps the source-checked frozen-to-current bridge visible with source consistency, the combined operator-status/source-freshness/operator-read-gate route, CD-only current rule mix, {bridge_queue_navigation}, bridge-published current gate wording, and no-new-forward-evidence / no-promotion / no-live-profitability / no-real-money boundaries, keeps the landing-page daily guide explicit about using those sidecar pointers for issue-day triage, makes the saved-live refresh path keep the rebuilt-stale-card inherited-snapshot note, routed top-card snapshot inheritance, operator_read_gate no-evidence routing, the distinct newest-run preflight/lane/daily latest-only boundary versus skip-top-level top-card-preservation boundary, explicit as-of-date-usage honesty, and the wrapper-leaf source-of-truth / inherited-guardrail-preservation note plus wrapper-generated CURRENT_EVIDENCE_SUMMARY refresh/placeholder and recommendation-context/open-row separation guardrail visible instead of only implied by the rebuilt top-card contract, pins the landing-page one-screen main comparison route plus report-inventory bundle/validator entries to the matched CSV/JSON sidecars and machine-readable evidence-boundary metadata without promoting Harville or current odds-only XGBoost, now exposes the full-data retrain caveat route as model-fit context only, and now frames the landing-page validation sweeps as alignment/order checks rather than new evidence",
        ),
        require(
            "anchor=OP_DURABLE_K7" in row_map["cole_full_report"]["current_read"]
            and "paper companion=CD_CORE_K8" in row_map["cole_full_report"]["current_read"]
            and "closest shadow=OP_REFINED_K7" in row_map["cole_full_report"]["current_read"]
            and "operational/reproducibility improvement rather than new forward evidence" in row_map["cole_full_report"]["current_read"]
            and "genuinely new forward evidence still requiring settled paper trades" in row_map["cole_full_report"]["current_read"]
            and "evidence scope=settled paper-trade rows with usable ROI coverage can change posture" in row_map["cole_full_report"]["current_read"]
            and "clean scans/open signals/historical replay/calibration-only summaries/odds-only reruns cannot" in row_map["cole_full_report"]["current_read"]
            and "current evidence bridge=CURRENT_EVIDENCE_SUMMARY.md/current_evidence_summary.json" in row_map["cole_full_report"]["current_read"]
            and "source consistency matched" in row_map["cole_full_report"]["current_read"]
            and full_report_operator_read_route_phrase in row_map["cole_full_report"]["current_read"]
            and expected_operator_read_gate_line in row_map["cole_full_report"]["current_read"]
            and "scorecard audit route=current_evidence_summary.json.scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks as report-synchronization metadata only" in row_map["cole_full_report"]["current_read"]
            and "rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only" in row_map["cole_full_report"]["current_read"]
            and current_report_gate_phrase in row_map["cole_full_report"]["current_read"]
            and "current settled sample is CD-only context and not OP-anchor evidence" in row_map["cole_full_report"]["current_read"]
            and report_child_queue_context in row_map["cole_full_report"]["current_read"]
            and report_child_queue_workflow_phrase in row_map["cole_full_report"]["current_read"]
            and current_open_queue_detail_read in row_map["cole_full_report"]["current_read"]
            and (
                not expected_api_access_action_route_required
                or "Sidecar action: refresh_daily_wrapper_before_evidence_read" in row_map["cole_full_report"]["current_read"]
            )
            and (
                not expected_api_access_action_route_required
                or "Recheck command: ./run_daily_portfolio_observation.sh" in row_map["cole_full_report"]["current_read"]
            )
            and "direct cross-family current-paper caveat route=CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py" in row_map["cole_full_report"]["current_read"]
            and "green report validation not OP-anchor proof or cross-family promotion evidence" in row_map["cole_full_report"]["current_read"]
            and "full-data retrain caveat route=FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py" in row_map["cole_full_report"]["current_read"]
            and "large RMSE / MAE gains and exact retrain/prediction commands kept as model-fit reproducibility context" in row_map["cole_full_report"]["current_read"]
            and "selective-family secondary lines elsewhere stay explicitly replay-context rather than extra train-only proof" in row_map["cole_full_report"]["current_read"],
            "full_report_keeps_paper_companion_hierarchy",
            f"full report rollup still carries the OP anchor plus the explicit selective paper-companion / shadow-challenger hierarchy, the paper-trade workflow not-new-evidence frame, the settled-paper-trades evidence boundary, the stricter evidence-scope exclusion for clean scans/open signals/replay/calibration/odds-only reruns, the source-consistent current-evidence bridge with combined operator-status/source-freshness/operator-read-gate routing plus current gate counts, the scorecard-audit route, and the rebuild-order route, the CD-only/not-OP-anchor and {report_child_queue_boundary}, the direct cross-family current-paper caveat route, the full-data retrain caveat route, and the replay-context caution on broader selective-family secondary lines",
        ),
        require(
            "operability check rather than a profitability/deployment claim" in row_map["working_status_report"]["current_read"]
            and "settled paper trades in the actual paper-trade lane" in row_map["working_status_report"]["current_read"]
            and "current paper totals route through CURRENT_EVIDENCE_SUMMARY.md/current_evidence_summary.json" in row_map["working_status_report"]["current_read"]
            and "source consistency matched" in row_map["working_status_report"]["current_read"]
            and "rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only" in row_map["working_status_report"]["current_read"]
            and working_operator_read_route_phrase in row_map["working_status_report"]["current_read"]
            and expected_operator_read_gate_line in row_map["working_status_report"]["current_read"]
            and "report gates source-matched to forward_evidence_scorecard.json decision_gate_minimums" in row_map["working_status_report"]["current_read"]
            and current_report_gate_phrase in row_map["working_status_report"]["current_read"]
            and "current settled sample is CD-only context and not OP-anchor evidence" in row_map["working_status_report"]["current_read"]
            and "direct cross-family current-paper caveat route=CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py" in row_map["working_status_report"]["current_read"]
            and "green working-status validation not OP-anchor proof or cross-family promotion evidence" in row_map["working_status_report"]["current_read"]
            and "full-data retrain caveat route=FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py" in row_map["working_status_report"]["current_read"]
            and "large RMSE / MAE gains and exact retrain/prediction commands kept as model-fit reproducibility context" in row_map["working_status_report"]["current_read"]
            and working_child_queue_context in row_map["working_status_report"]["current_read"]
            and working_child_queue_workflow_phrase in row_map["working_status_report"]["current_read"]
            and current_open_queue_detail_read in row_map["working_status_report"]["current_read"]
            and (
                not expected_api_access_action_route_required
                or "Sidecar action: refresh_daily_wrapper_before_evidence_read" in row_map["working_status_report"]["current_read"]
            )
            and (
                not expected_api_access_action_route_required
                or "Recheck command: ./run_daily_portfolio_observation.sh" in row_map["working_status_report"]["current_read"]
            )
            and "mutable convenience alias" in row_map["working_status_report"]["current_read"],
            "working_status_stays_non_promotional",
            f"working-status rollup still frames the demo lane as operability evidence, keeps the settled-paper-trades evidence boundary, routes current paper-total wording through the source-consistent/operator-context/freshness/operator-read-gate-routed current-evidence bridge with scorecard-sourced current gate counts plus the CD-only/not-OP-anchor and source-published settlement queue state/detail boundary, carries the direct cross-family current-paper caveat route, carries the full-data retrain caveat route in model-fit context only, and treats latest_demo_run.json as a mutable convenience alias",
        ),
        require(
            "anchor=OP_DURABLE_K7" in row_map["cole_presentation_outline"]["current_read"]
            and "method roles=PAPER NOW / BENCHMARK ONLY / RESEARCH ONLY" in row_map["cole_presentation_outline"]["current_read"]
            and "paper companion=CD_CORE_K8" in row_map["cole_presentation_outline"]["current_read"]
            and "closest shadow=OP_REFINED_K7" in row_map["cole_presentation_outline"]["current_read"]
            and "full-data retrain caveat route=FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py" in row_map["cole_presentation_outline"]["current_read"]
            and "large RMSE / MAE gains and exact retrain/prediction commands kept as model-fit reproducibility context" in row_map["cole_presentation_outline"]["current_read"]
            and "workflow/observation proof, not live-edge confirmation" in row_map["cole_presentation_outline"]["current_read"]
            and "genuinely new forward evidence still requires settled paper trades" in row_map["cole_presentation_outline"]["current_read"]
            and "evidence scope=settled paper-trade rows with usable ROI coverage can change posture" in row_map["cole_presentation_outline"]["current_read"]
            and "clean scans/open signals/historical replay/calibration-only summaries/odds-only reruns cannot" in row_map["cole_presentation_outline"]["current_read"]
            and "current evidence bridge=CURRENT_EVIDENCE_SUMMARY.md/current_evidence_summary.json" in row_map["cole_presentation_outline"]["current_read"]
            and "source consistency matched" in row_map["cole_presentation_outline"]["current_read"]
            and presentation_operator_read_route_phrase in row_map["cole_presentation_outline"]["current_read"]
            and expected_operator_read_gate_line in row_map["cole_presentation_outline"]["current_read"]
            and "scorecard audit route=current_evidence_summary.json.scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks as report-synchronization metadata only" in row_map["cole_presentation_outline"]["current_read"]
            and "rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only" in row_map["cole_presentation_outline"]["current_read"]
            and current_report_gate_phrase in row_map["cole_presentation_outline"]["current_read"]
            and "current settled sample is CD-only context and not OP-anchor evidence" in row_map["cole_presentation_outline"]["current_read"]
            and presentation_child_queue_context in row_map["cole_presentation_outline"]["current_read"]
            and current_open_queue_detail_read in row_map["cole_presentation_outline"]["current_read"]
            and "latest primary recommendation context" in row_map["cole_presentation_outline"]["current_read"]
            and presentation_queue_workflow_phrase in row_map["cole_presentation_outline"]["current_read"]
            and (
                not expected_api_access_action_route_required
                or "Sidecar action: refresh_daily_wrapper_before_evidence_read" in row_map["cole_presentation_outline"]["current_read"]
            )
            and (
                not expected_api_access_action_route_required
                or "Recheck command: ./run_daily_portfolio_observation.sh" in row_map["cole_presentation_outline"]["current_read"]
            )
            and "direct cross-family current-paper caveat route=CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py" in row_map["cole_presentation_outline"]["current_read"]
            and "green presentation validation not OP-anchor proof or cross-family promotion evidence" in row_map["cole_presentation_outline"]["current_read"]
            and "broader selective-family secondary lines elsewhere stay replay-context rather than extra train-only proof" in row_map["cole_presentation_outline"]["current_read"]
            and "remaining Phase 8 pockets=KEE_K9 / SA_K9 / DMR_FALL_K7 stay observation-only rather than near-promotion cases" in row_map["cole_presentation_outline"]["current_read"],
            "presentation_outline_keeps_method_roles",
            f"presentation-outline rollup still carries the OP anchor plus the paper/benchmark/research method roles, selective paper-companion / shadow-challenger ordering, the full-data retrain caveat route, the first-paper-trade-run not-live-proof frame, the settled-paper-trades evidence boundary, the stricter evidence-scope exclusion for clean scans/open signals/replay/calibration/odds-only reruns, the current-evidence bridge with source consistency plus combined operator-status/source-freshness/operator-read-gate right-now instruction/evidence routing plus current gate counts, the scorecard-audit route, and the rebuild-order route, the CD-only/not-OP-anchor boundary, the current latest recommendation context, the {presentation_queue_boundary}, and the direct cross-family current-paper caveat route, plus the replay-context caution on broader selective-family secondary lines",
        ),
        require(
            "legacy alias=redirect-only warning page" in row_map["superfecta_html_report"]["current_read"]
            and "claim-free boundary" in row_map["superfecta_html_report"]["current_read"]
            and "dated validated HTML trust anchor" in row_map["superfecta_html_report"]["current_read"]
            and "workflow/reproducibility improvement rather than new forward evidence by itself" in row_map["superfecta_html_report"]["current_read"]
            and "evidence scope=settled paper-trade rows with usable ROI coverage can change posture" in row_map["superfecta_html_report"]["current_read"]
            and "clean scans/open signals/historical replay/calibration-only summaries/odds-only reruns cannot" in row_map["superfecta_html_report"]["current_read"]
            and "current evidence bridge=CURRENT_EVIDENCE_SUMMARY.md/current_evidence_summary.json" in row_map["superfecta_html_report"]["current_read"]
            and "source consistency matched" in row_map["superfecta_html_report"]["current_read"]
            and report_operator_read_route_phrase in row_map["superfecta_html_report"]["current_read"]
            and expected_operator_read_gate_line in row_map["superfecta_html_report"]["current_read"]
            and "report gates source-matched to forward_evidence_scorecard.json decision_gate_minimums" in row_map["superfecta_html_report"]["current_read"]
            and current_report_gate_phrase in row_map["superfecta_html_report"]["current_read"]
            and "scorecard audit route=current_evidence_summary.json.scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks as report-synchronization metadata only" in row_map["superfecta_html_report"]["current_read"]
            and "rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only" in row_map["superfecta_html_report"]["current_read"]
            and "current settled sample is CD-only context and not OP-anchor evidence" in row_map["superfecta_html_report"]["current_read"]
            and "direct cross-family current-paper caveat route=CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py" in row_map["superfecta_html_report"]["current_read"]
            and "green HTML/PDF validation not OP-anchor proof or cross-family promotion evidence" in row_map["superfecta_html_report"]["current_read"]
            and "full-data retrain caveat route=FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py" in row_map["superfecta_html_report"]["current_read"]
            and "RMSE / MAE diagnostics kept as model-fit reproducibility context only" in row_map["superfecta_html_report"]["current_read"]
            and "OP_REFINED CI-only route=forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7 with ci_only_promotion_allowed=false" in row_map["superfecta_html_report"]["current_read"]
            and "dated PDF derivative export verified for the combined operator-status/source-freshness/operator-read-gate route, current-evidence bridge, rebuild-order route, scorecard-audit route, OP_REFINED CI-only boundary, cross-family current-paper caveat route, and full-data retrain caveat route" in row_map["superfecta_html_report"]["current_read"]
            and "legacy PDF alias=claim-free warning export, not the old XGBoost rerun report or a separate evidence source" in row_map["superfecta_html_report"]["current_read"]
            and "legacy DOCX alias=claim-free warning document, not the old XGBoost rerun report or a separate evidence source" in row_map["superfecta_html_report"]["current_read"]
            and "legacy quick-start PDF alias=claim-free warning export, not the old ML/live-prediction quick-start or a separate evidence source" in row_map["superfecta_html_report"]["current_read"]
            and "legacy OpenClaw prompt DOCX alias=claim-free historical-prompt warning document, not the old ML/profitability-training prompt or a separate evidence source" in row_map["superfecta_html_report"]["current_read"]
            and "shareable report Phase 7 wording=OP/CD rule-component basket with target cards confirmed by daily preflight" in row_map["superfecta_html_report"]["current_read"]
            and "broader selective-family secondary lines elsewhere stay replay-context rather than extra train-only proof" in row_map["superfecta_html_report"]["current_read"],
            "html_report_keeps_alias_guardrail",
            "HTML rollup still demotes the undated HTML/PDF/DOCX aliases, the old quick-start PDF, and the old OpenClaw prompt DOCX to warning surfaces with claim-free boundaries, keeps the undated PDF/DOCX aliases as warning exports rather than the old XGBoost rerun report, keeps the quick-start PDF as a warning export rather than the old ML/live-prediction guide, keeps the prompt DOCX as a historical-prompt warning rather than the old ML/profitability-training task, keeps the paper-trade workflow upgrade framed as not-new-evidence, carries the stricter evidence-scope exclusion for clean scans/open signals/replay/calibration/odds-only reruns, routes current paper-total wording through the current-evidence bridge with source consistency plus combined operator-status/source-freshness/operator-read-gate routing plus current gate counts, carries the rebuild-order route, the scorecard-audit route, and the OP_REFINED CI-only boundary, carries the direct cross-family current-paper caveat route plus the full-data retrain caveat route, verifies the dated PDF derivative export carries the same combined operator-status/source-freshness/operator-read-gate bridge, rebuild-order route, scorecard-audit route, OP_REFINED CI-only boundary, cross-family caveat route, and full-data retrain caveat route, separates the CD-only current sample from OP-anchor proof, carries the Phase 7 OP/CD rule-component basket / daily-preflight wording, and carries the replay-context caution on broader selective-family secondary lines",
        ),
        require(
            "PDF refresh helper check-existing path passes through the dated HTML report validator" in row_map["shareable_report_pdf_refresh"]["current_read"]
            and "dated HTML remains the trust anchor" in row_map["shareable_report_pdf_refresh"]["current_read"]
            and "dated PDF remains a derivative export" in row_map["shareable_report_pdf_refresh"]["current_read"]
            and "legacy undated PDF/DOCX aliases, legacy quick-start PDF alias, and legacy OpenClaw prompt DOCX alias stay claim-free" in row_map["shareable_report_pdf_refresh"]["current_read"]
            and "HTML/PDF combined operator-read route, rebuild-order route, scorecard-audit route, OP_REFINED CI-only boundary, cross-family current-paper caveat route, and full-data retrain caveat route stay pinned" in row_map["shareable_report_pdf_refresh"]["current_read"]
            and "reproducibility metadata only rather than settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence" in row_map["shareable_report_pdf_refresh"]["current_read"],
            "shareable_pdf_refresh_helper_keeps_derivative_boundary",
            "PDF refresh helper rollup keeps the safe check-existing path tied to the dated HTML validator, preserves the dated HTML as trust anchor, the dated PDF as derivative export, and the undated PDF/DOCX plus old quick-start PDF and historical OpenClaw prompt DOCX aliases as claim-free, keeps the HTML/PDF combined operator-read route plus rebuild-order route plus scorecard-audit route plus OP_REFINED CI-only boundary plus cross-family current-paper caveat route plus full-data retrain caveat route pinned, and frames the helper output as reproducibility metadata only rather than settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence",
        ),
        require(
            current_source_consistency.get("overall_match") is True
            and current_roi_rows.get("paper_trade_now")
            == current_roi_rows.get("settlement_audit")
            == current_roi_rows.get("settlement_csv_recomputed")
            and current_open_rows.get("paper_trade_now") == current_open_rows.get("settlement_audit")
            and current_incomplete_rows.get("paper_trade_now") == current_incomplete_rows.get("settlement_audit")
            and current_roi_gap_rows.get("paper_trade_now") == current_roi_gap_rows.get("settlement_audit")
            and current_source_freshness.get("right_now_freshness_state_valid") is True
            and isinstance(current_source_freshness.get("requires_refresh_before_right_now_use"), bool)
            and current_gate_minimums.get("source_path") == "forward_evidence_scorecard.json"
            and current_gate_minimums.get("source_loaded") is True
            and current_gate_minimums.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and current_gate_minimums.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and current_gate_minimums.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100,
            "report_surfaces_current_evidence_bridge_json_is_source_gate_routed",
            "report-surface parent JSON now has to expose the current-evidence bridge's source-consistent top-card/audit/CSV read, valid source-freshness route, and scorecard-sourced 30/20/100 gates before report-facing summaries quote current paper totals",
        ),
        require(
            current_rebuild_contract_read.get("source") == CURRENT_EVIDENCE_JSON.name
            and current_rebuild_contract_read.get("source_path") == "rebuild_validation_contract"
            and current_rebuild_contract_read.get("upstream_refresh_order")
            == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and current_rebuild_contract_read.get("upstream_refresh_order_numbers") == [1, 2, 3]
            and current_rebuild_contract_read.get("prerequisite_rebuild_command") == "python3 paper_trade_settlement_audit.py"
            and current_rebuild_contract_read.get("rebuild_command") == "python3 current_evidence_summary.py"
            and current_rebuild_contract_read.get("direct_validation_command") == "python3 validate_current_evidence_summary.py"
            and current_rebuild_contract_read.get(
                "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
            )
            is True
            and current_rebuild_contract_read.get("requires_source_consistency_before_quoting_current_totals") is True
            and current_rebuild_contract_read.get("upstream_refresh_order_is_provenance_metadata_only") is True
            and current_rebuild_contract_read.get("not_settled_roi_or_real_money_evidence") is True,
            "report_surfaces_current_evidence_rebuild_contract_is_source_routed",
            "report-surface parent JSON now source-checks current_evidence_summary.json.rebuild_validation_contract directly, so a green human-facing report sweep cannot quote current bridge totals after source-byte changes without the settlement-audit -> current-bridge -> bridge-validator route remaining intact",
        ),
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
            "report_surfaces_current_evidence_effective_gates_are_scorecard_backed",
            "report-surface parent JSON now has to preserve the current-evidence bridge's canonical scorecard-backed effective gate values, top-card/scorecard alignment state, missing/mismatched gate lists, and exact threshold-source paths before human-facing reports quote the 30/20/100 floors",
        ),
        require(
            presentation_bridge_json_read.get("source_consistency_overall_match") is True
            and presentation_bridge_json_read.get("primary_roi_complete_rows_match") is True
            and presentation_bridge_json_read.get("primary_open_rows_match") is True
            and presentation_bridge_json_read.get("primary_incomplete_rows_match") is True
            and presentation_bridge_json_read.get("primary_roi_gap_rows_match") is True
            and presentation_bridge_json_read.get("source_freshness_state_valid") is True
            and isinstance(presentation_bridge_json_read.get("requires_refresh_before_right_now_use"), bool)
            and presentation_bridge_json_read.get("decision_gate_source") == "forward_evidence_scorecard.json"
            and presentation_bridge_json_read.get("decision_gate_source_loaded") is True
            and presentation_bridge_json_read.get("anchor_displacement_min") == 30
            and presentation_bridge_json_read.get("phase8_promotion_review_min") == 20
            and presentation_bridge_json_read.get("real_money_discussion_min") == 100,
            "presentation_outline_current_evidence_bridge_json_is_source_gate_routed",
            "report-surface parent now has to preserve the presentation-outline child's structured current-evidence source/gate read, so the slide surface cannot keep safe prose while dropping machine-readable source consistency, freshness, or 30/20/100 gate routing",
        ),
        require(
            presentation_bridge_json_read.get("decision_gate_source_values_match_scorecard") is True
            and presentation_bridge_json_read.get("decision_gate_effective_values_source")
            == "forward_evidence_scorecard.json:decision_gate_minimums"
            and presentation_bridge_json_read.get("decision_gate_missing_top_card_fields") == []
            and presentation_bridge_json_read.get("decision_gate_mismatched_fields") == []
            and presentation_bridge_json_read.get("effective_anchor_displacement_min") == 30
            and presentation_bridge_json_read.get("effective_phase8_promotion_review_min") == 20
            and presentation_bridge_json_read.get("effective_real_money_discussion_min") == 100
            and presentation_bridge_json_read.get("top_card_anchor_displacement_min") == 30
            and presentation_bridge_json_read.get("top_card_phase8_promotion_review_min") == 20
            and presentation_bridge_json_read.get("top_card_real_money_discussion_min") == 100
            and presentation_bridge_json_read.get("scorecard_anchor_displacement_min_from_bridge") == 30
            and presentation_bridge_json_read.get("scorecard_phase8_promotion_review_min_from_bridge") == 20
            and presentation_bridge_json_read.get("scorecard_real_money_discussion_min_from_bridge") == 100
            and presentation_bridge_json_read.get("decision_gate_threshold_sources", {}).get("anchor_displacement")
            == "forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations"
            and presentation_bridge_json_read.get("decision_gate_threshold_sources", {}).get("phase8_promotion_review")
            == "forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations"
            and presentation_bridge_json_read.get("decision_gate_threshold_sources", {}).get("real_money_discussion")
            == "forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
            "presentation_outline_current_evidence_effective_gates_are_scorecard_backed",
            "report-surface parent now has to preserve the presentation-outline child's canonical effective gate source, top-card/scorecard alignment fields, missing/mismatch lists, and threshold-source paths instead of accepting only the older flattened 30/20/100 fields",
        ),
        require(
            full_report_bridge_json_read.get("source_consistency_overall_match") is True
            and full_report_bridge_json_read.get("primary_roi_complete_rows_match") is True
            and full_report_bridge_json_read.get("primary_open_rows_match") is True
            and full_report_bridge_json_read.get("primary_incomplete_rows_match") is True
            and full_report_bridge_json_read.get("primary_roi_gap_rows_match") is True
            and full_report_bridge_json_read.get("source_freshness_state_valid") is True
            and isinstance(full_report_bridge_json_read.get("requires_refresh_before_right_now_use"), bool)
            and full_report_bridge_json_read.get("decision_gate_source") == "forward_evidence_scorecard.json"
            and full_report_bridge_json_read.get("decision_gate_source_loaded") is True
            and full_report_bridge_json_read.get("decision_gate_source_values_match_scorecard") is True
            and full_report_bridge_json_read.get("decision_gate_effective_values_source")
            == "forward_evidence_scorecard.json:decision_gate_minimums"
            and full_report_bridge_json_read.get("decision_gate_missing_top_card_fields") == []
            and full_report_bridge_json_read.get("decision_gate_mismatched_fields") == []
            and full_report_bridge_json_read.get("anchor_displacement_min") == 30
            and full_report_bridge_json_read.get("phase8_promotion_review_min") == 20
            and full_report_bridge_json_read.get("real_money_discussion_min") == 100
            and full_report_bridge_json_read.get("effective_anchor_displacement_min") == 30
            and full_report_bridge_json_read.get("effective_phase8_promotion_review_min") == 20
            and full_report_bridge_json_read.get("effective_real_money_discussion_min") == 100
            and full_report_bridge_json_read.get("top_card_anchor_displacement_min") == 30
            and full_report_bridge_json_read.get("top_card_phase8_promotion_review_min") == 20
            and full_report_bridge_json_read.get("top_card_real_money_discussion_min") == 100
            and full_report_bridge_json_read.get("scorecard_anchor_displacement_min_from_bridge") == 30
            and full_report_bridge_json_read.get("scorecard_phase8_promotion_review_min_from_bridge") == 20
            and full_report_bridge_json_read.get("scorecard_real_money_discussion_min_from_bridge") == 100
            and full_report_bridge_json_read.get("decision_gate_threshold_sources", {}).get("anchor_displacement")
            == "forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations"
            and full_report_bridge_json_read.get("decision_gate_threshold_sources", {}).get("phase8_promotion_review")
            == "forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations"
            and full_report_bridge_json_read.get("decision_gate_threshold_sources", {}).get("real_money_discussion")
            == "forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
            "full_report_current_evidence_effective_gates_are_scorecard_backed",
            "report-surface parent now has to preserve the long-form full-report child's canonical current-evidence gate source, scorecard-backed effective values, top-card/scorecard alignment fields, missing/mismatch lists, and threshold-source paths instead of only trusting the summary prose",
        ),
        require(
            all(row_map[name]["result"] == "PASS" for name in row_map)
            and all(isinstance(row_map[name]["child_check_count"], int) and row_map[name]["child_check_count"] > 0 for name in row_map)
            and all(isinstance(row_map[name]["current_read"], str) and row_map[name]["current_read"].strip() for name in row_map),
            "child_report_validators_publish_explicit_status_counts_and_reads",
            "all six report-surface child validators now have to publish explicit PASS status, nonzero check_count, and non-empty summary read metadata instead of letting the parent sweep infer them from partial payloads",
        ),
        require(
            child_payloads["readme_current_status"].get("suite_status") == "pass"
            and child_payloads["readme_current_status"].get("total_checks") == 64
            and child_payloads["readme_current_status"].get("check_count") == 64
            and isinstance(child_payloads["readme_current_status"].get("scorecard_decision_gate_minimums_read"), dict)
            and child_payloads["readme_current_status"]["scorecard_decision_gate_minimums_read"].get("source") == "forward_evidence_scorecard.json"
            and child_payloads["readme_current_status"]["scorecard_decision_gate_minimums_read"].get("source_path") == "decision_gate_minimums"
            and child_payloads["readme_current_status"]["scorecard_decision_gate_minimums_read"].get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and child_payloads["readme_current_status"]["scorecard_decision_gate_minimums_read"].get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and child_payloads["readme_current_status"]["scorecard_decision_gate_minimums_read"].get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and child_payloads["readme_current_status"]["scorecard_decision_gate_minimums_read"].get("real_money_no_baq_as_bel_required") is True
            and isinstance(child_payloads["readme_current_status"].get("current_evidence_gate_progress_read"), dict)
            and child_payloads["readme_current_status"]["current_evidence_gate_progress_read"].get("source") == "current_evidence_summary.json"
            and child_payloads["readme_current_status"]["current_evidence_gate_progress_read"].get("source_path") == "decision_gate_progress"
            and child_payloads["readme_current_status"]["current_evidence_gate_progress_read"].get("scorecard_source") == "forward_evidence_scorecard.json"
            and child_payloads["readme_current_status"]["current_evidence_gate_progress_read"].get("scorecard_source_json_path") == "decision_gate_minimums"
            and child_payloads["readme_current_status"]["current_evidence_gate_progress_read"].get("gate_status") == "all_uncleared"
            and child_payloads["readme_current_status"]["current_evidence_gate_progress_read"].get("all_gates_ready") is False
            and child_payloads["readme_current_status"]["current_evidence_gate_progress_read"].get("read") == current_gate_progress_read
            and child_payloads["readme_current_status"]["current_evidence_gate_progress_read"].get("not_forward_performance_evidence") is True
            and child_payloads["readme_current_status"]["current_evidence_gate_progress_read"].get("not_promotion_readiness_evidence") is True
            and child_payloads["readme_current_status"]["current_evidence_gate_progress_read"].get("not_live_profitability_evidence") is True
            and child_payloads["readme_current_status"]["current_evidence_gate_progress_read"].get("not_real_money_evidence") is True
            and child_operator_gate_matches("readme_current_status")
            and readme_api_route_matches()
            and isinstance(child_payloads["readme_current_status"].get("current_evidence_scorecard_audit_route_read"), dict)
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("source") == "current_evidence_summary.json"
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("source_path") == "scorecard_audit_route"
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("json_path") == "scorecard_ranking_contract_audit.json"
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("real_money_no_baq_as_bel_required") is True
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("artifacts_present") is True
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("not_forward_performance_evidence") is True
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("not_settled_roi_evidence") is True
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("not_promotion_readiness_evidence") is True
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("not_live_profitability_evidence") is True
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("not_bankroll_guidance") is True
            and child_payloads["readme_current_status"]["current_evidence_scorecard_audit_route_read"].get("not_real_money_evidence") is True
            and isinstance(child_payloads["readme_current_status"].get("current_evidence_rebuild_validation_contract_read"), dict)
            and child_payloads["readme_current_status"]["current_evidence_rebuild_validation_contract_read"].get("source") == "current_evidence_summary.json"
            and child_payloads["readme_current_status"]["current_evidence_rebuild_validation_contract_read"].get("source_path") == "rebuild_validation_contract"
            and child_payloads["readme_current_status"]["current_evidence_rebuild_validation_contract_read"].get("prerequisite_rebuild_command") == "python3 paper_trade_settlement_audit.py"
            and child_payloads["readme_current_status"]["current_evidence_rebuild_validation_contract_read"].get("rebuild_command") == "python3 current_evidence_summary.py"
            and child_payloads["readme_current_status"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and child_payloads["readme_current_status"]["current_evidence_rebuild_validation_contract_read"].get("direct_validation_command") == "python3 validate_current_evidence_summary.py"
            and child_payloads["readme_current_status"]["current_evidence_rebuild_validation_contract_read"].get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and child_payloads["readme_current_status"]["current_evidence_rebuild_validation_contract_read"].get("requires_source_consistency_before_quoting_current_totals") is True
            and child_payloads["readme_current_status"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order_is_provenance_metadata_only") is True
            and child_payloads["readme_current_status"]["current_evidence_rebuild_validation_contract_read"].get("not_settled_roi_or_real_money_evidence") is True
            and isinstance(child_payloads["readme_current_status"].get("current_evidence_settlement_queue_read"), dict)
            and child_payloads["readme_current_status"]["current_evidence_settlement_queue_read"].get("source") == "current_evidence_summary.json"
            and child_payloads["readme_current_status"]["current_evidence_settlement_queue_read"].get("source_path") == "current_paper_status.primary.open_settlement_queue_by_rule"
            and child_payloads["readme_current_status"]["current_evidence_settlement_queue_read"].get("open_settlements") == current_open_settlements
            and child_payloads["readme_current_status"]["current_evidence_settlement_queue_read"].get("open_settlement_queue_state") == current_open_queue_state
            and child_payloads["readme_current_status"]["current_evidence_settlement_queue_read"].get("open_settlement_context") == current_open_queue_context
            and child_payloads["readme_current_status"]["current_evidence_settlement_queue_read"].get("detail_read") == current_open_queue_detail_read
            and child_payloads["readme_current_status"]["current_evidence_settlement_queue_read"].get("not_forward_performance_evidence") is True
            and child_payloads["cole_full_report"].get("suite_status") == "pass"
            and child_payloads["cole_full_report"].get("total_checks") == 29
            and child_payloads["cole_full_report"].get("check_count") == 29
            and child_operator_gate_matches("cole_full_report")
            and isinstance(child_payloads["cole_full_report"].get("current_evidence_scorecard_audit_route_read"), dict)
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("source") == "current_evidence_summary.json"
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("source_path") == "scorecard_audit_route"
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("json_path") == "scorecard_ranking_contract_audit.json"
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("real_money_no_baq_as_bel_required") is True
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("artifacts_present") is True
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("not_forward_performance_evidence") is True
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("not_settled_roi_evidence") is True
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("not_promotion_readiness_evidence") is True
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("not_live_profitability_evidence") is True
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("not_bankroll_guidance") is True
            and child_payloads["cole_full_report"]["current_evidence_scorecard_audit_route_read"].get("not_real_money_evidence") is True
            and isinstance(child_payloads["cole_full_report"].get("current_evidence_rebuild_validation_contract_read"), dict)
            and child_payloads["cole_full_report"]["current_evidence_rebuild_validation_contract_read"].get("source") == "current_evidence_summary.json"
            and child_payloads["cole_full_report"]["current_evidence_rebuild_validation_contract_read"].get("source_path") == "rebuild_validation_contract"
            and child_payloads["cole_full_report"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and child_payloads["cole_full_report"]["current_evidence_rebuild_validation_contract_read"].get("prerequisite_rebuild_command") == "python3 paper_trade_settlement_audit.py"
            and child_payloads["cole_full_report"]["current_evidence_rebuild_validation_contract_read"].get("rebuild_command") == "python3 current_evidence_summary.py"
            and child_payloads["cole_full_report"]["current_evidence_rebuild_validation_contract_read"].get("direct_validation_command") == "python3 validate_current_evidence_summary.py"
            and child_payloads["cole_full_report"]["current_evidence_rebuild_validation_contract_read"].get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and child_payloads["cole_full_report"]["current_evidence_rebuild_validation_contract_read"].get("requires_source_consistency_before_quoting_current_totals") is True
            and child_payloads["cole_full_report"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order_is_provenance_metadata_only") is True
            and child_payloads["cole_full_report"]["current_evidence_rebuild_validation_contract_read"].get("not_settled_roi_or_real_money_evidence") is True
            and child_payloads["working_status_report"].get("suite_status") == "pass"
            and child_payloads["working_status_report"].get("total_checks") == 26
            and child_payloads["working_status_report"].get("check_count") == 26
            and child_operator_gate_matches("working_status_report")
            and isinstance(child_payloads["working_status_report"].get("current_evidence_rebuild_validation_contract_read"), dict)
            and child_payloads["working_status_report"]["current_evidence_rebuild_validation_contract_read"].get("source") == "current_evidence_summary.json"
            and child_payloads["working_status_report"]["current_evidence_rebuild_validation_contract_read"].get("source_path") == "rebuild_validation_contract"
            and child_payloads["working_status_report"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and child_payloads["working_status_report"]["current_evidence_rebuild_validation_contract_read"].get("prerequisite_rebuild_command") == "python3 paper_trade_settlement_audit.py"
            and child_payloads["working_status_report"]["current_evidence_rebuild_validation_contract_read"].get("rebuild_command") == "python3 current_evidence_summary.py"
            and child_payloads["working_status_report"]["current_evidence_rebuild_validation_contract_read"].get("direct_validation_command") == "python3 validate_current_evidence_summary.py"
            and child_payloads["working_status_report"]["current_evidence_rebuild_validation_contract_read"].get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and child_payloads["working_status_report"]["current_evidence_rebuild_validation_contract_read"].get("requires_source_consistency_before_quoting_current_totals") is True
            and child_payloads["working_status_report"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order_is_provenance_metadata_only") is True
            and child_payloads["working_status_report"]["current_evidence_rebuild_validation_contract_read"].get("not_settled_roi_or_real_money_evidence") is True
            and child_payloads["cole_presentation_outline"].get("suite_status") == "pass"
            and child_payloads["cole_presentation_outline"].get("total_checks") == 25
            and child_payloads["cole_presentation_outline"].get("check_count") == 25
            and child_operator_gate_matches("cole_presentation_outline")
            and isinstance(child_payloads["cole_presentation_outline"].get("current_evidence_rebuild_validation_contract_read"), dict)
            and child_payloads["cole_presentation_outline"]["current_evidence_rebuild_validation_contract_read"].get("source") == "current_evidence_summary.json"
            and child_payloads["cole_presentation_outline"]["current_evidence_rebuild_validation_contract_read"].get("source_path") == "rebuild_validation_contract"
            and child_payloads["cole_presentation_outline"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and child_payloads["cole_presentation_outline"]["current_evidence_rebuild_validation_contract_read"].get("prerequisite_rebuild_command") == "python3 paper_trade_settlement_audit.py"
            and child_payloads["cole_presentation_outline"]["current_evidence_rebuild_validation_contract_read"].get("rebuild_command") == "python3 current_evidence_summary.py"
            and child_payloads["cole_presentation_outline"]["current_evidence_rebuild_validation_contract_read"].get("direct_validation_command") == "python3 validate_current_evidence_summary.py"
            and child_payloads["cole_presentation_outline"]["current_evidence_rebuild_validation_contract_read"].get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and child_payloads["cole_presentation_outline"]["current_evidence_rebuild_validation_contract_read"].get("requires_source_consistency_before_quoting_current_totals") is True
            and child_payloads["cole_presentation_outline"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order_is_provenance_metadata_only") is True
            and child_payloads["cole_presentation_outline"]["current_evidence_rebuild_validation_contract_read"].get("not_settled_roi_or_real_money_evidence") is True
            and child_payloads["superfecta_html_report"].get("suite_status") == "pass"
            and child_payloads["superfecta_html_report"].get("total_checks") == 33
            and child_payloads["superfecta_html_report"].get("check_count") == 33
            and child_operator_gate_matches("superfecta_html_report")
            and isinstance(child_payloads["superfecta_html_report"].get("current_evidence_rebuild_validation_contract_read"), dict)
            and child_payloads["superfecta_html_report"]["current_evidence_rebuild_validation_contract_read"].get("source") == "current_evidence_summary.json"
            and child_payloads["superfecta_html_report"]["current_evidence_rebuild_validation_contract_read"].get("source_path") == "rebuild_validation_contract"
            and child_payloads["superfecta_html_report"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and child_payloads["superfecta_html_report"]["current_evidence_rebuild_validation_contract_read"].get("prerequisite_rebuild_command") == "python3 paper_trade_settlement_audit.py"
            and child_payloads["superfecta_html_report"]["current_evidence_rebuild_validation_contract_read"].get("rebuild_command") == "python3 current_evidence_summary.py"
            and child_payloads["superfecta_html_report"]["current_evidence_rebuild_validation_contract_read"].get("direct_validation_command") == "python3 validate_current_evidence_summary.py"
            and child_payloads["superfecta_html_report"]["current_evidence_rebuild_validation_contract_read"].get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and child_payloads["superfecta_html_report"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order_is_provenance_metadata_only") is True
            and child_payloads["superfecta_html_report"]["current_evidence_rebuild_validation_contract_read"].get("not_settled_roi_or_real_money_evidence") is True
            and child_payloads["shareable_report_pdf_refresh"].get("suite_status") == "pass"
            and child_payloads["shareable_report_pdf_refresh"].get("total_checks") == 5
            and child_payloads["shareable_report_pdf_refresh"].get("check_count") == 5,
            "child_report_validators_publish_explicit_total_checks",
            "all six report-surface child validators now publish explicit top-level total_checks alongside check_count, so the parent sweep does not have to treat check_count alone as the full direct report-surface scope contract",
        ),
        require(
            row_map["readme_current_status"].get("child_check_count") == 64
            and isinstance(row_map["readme_current_status"].get("child_checks"), list)
            and {check.get("check") for check in row_map["readme_current_status"]["child_checks"]} == {
                "scorecard_nonpositive_phase8_floor_fails_before_artifacts",
                "scorecard_nonpositive_real_money_floor_fails_before_artifacts",
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "source_freshness_false_branch_is_fresh_not_refresh",
                "source_freshness_true_branch_is_refresh_first",
                "anchor_source_still_op_durable",
                "status_intro",
                "anchor_line",
                "paper_line",
                "selector_line",
                "phase8_line",
                "shadow_split_line",
                "current_evidence_bridge_line",
                "source_published_settlement_queue_state",
                "current_evidence_api_access_route_line",
                "readme_current_gates_source_match_scorecard_json",
                "current_evidence_combined_operator_read_route",
                "current_evidence_operator_read_gate_route",
                "current_evidence_navigation_uses_bridge_published_gates",
                "method_family_lines",
                "stale_selector_headline_removed",
                "cold_start_scorecard_read",
                "cold_start_scorecard_audit_read",
                "current_evidence_scorecard_audit_route_read",
                "current_evidence_rebuild_validation_contract_read",
                "cold_start_top_card_read",
                "cold_start_current_evidence_read",
                "cold_start_status_doc_api_access_route",
                "cold_start_decision_path_read",
                "cold_start_main_comparison_read",
                "cold_start_full_data_retrain_caveat_read",
                "cold_start_frozen_read",
                "cold_start_current_evidence_validation_read",
                "cold_start_top_card_validation_read",
                "cold_start_decision_cards_validation_read",
                "cross_family_current_paper_route_present",
                "cold_start_project_read",
                "cold_start_scorecard_validator",
                "cold_start_current_evidence_validator",
                "cold_start_top_card_validator",
                "validated_read_note",
                "core_strategy_inventory_lines",
                "live_demo_inventory_lines",
                "paper_trade_ops_inventory_lines",
                "operator_docs_inventory_lines",
                "readme_wrapper_leaf_source_of_truth_note_present",
                "decision_card_inventory_lines",
                "op_anchor_inventory_line",
                "main_comparison_inventory_lines",
                "full_data_retrain_inventory_lines",
                "current_evidence_inventory_lines",
                "scorecard_audit_inventory_lines",
                "status_doc_api_access_inventory_lines",
                "working_status_validator_inventory_line",
                "report_alias_note",
                "legacy_report_aliases_not_listed_as_primary_artifacts",
                "cold_start_paths_exist",
                "report_anchor_and_runbook_paths_exist",
                "core_strategy_inventory_paths_exist",
                "live_demo_inventory_paths_exist",
                "paper_trade_ops_inventory_paths_exist",
                "operator_inventory_paths_exist",
                "highlighted_report_inventory_paths_exist",
            }
            and row_map["cole_full_report"].get("child_check_count") == 29
            and isinstance(row_map["cole_full_report"].get("child_checks"), list)
            and {check.get("check") for check in row_map["cole_full_report"]["child_checks"]} == {
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "malformed_scorecard_gate_floors_fail_before_artifacts",
                "anchor_source_still_op_durable",
                "historical_selector_line",
                "current_selector_line",
                "phase7_holdout_line",
                "phase8_shadow_line",
                "portfolio_decision_year_split",
                "method_family_line",
                "full_data_retrain_caveat_route_present",
                "full_report_evidence_scope_boundary",
                "rule_hierarchy_year_split",
                "method_family_guardrail_section",
                "paper_trade_ops_not_new_evidence_frame",
                "current_evidence_bridge_read",
                "current_evidence_scorecard_audit_route_present",
                "current_evidence_rebuild_validation_contract_read",
                "source_published_settlement_queue_state",
                "cross_family_current_paper_route_present",
                "full_report_gate_source_matches_scorecard_json",
                "current_evidence_bridge_effective_gates_are_scorecard_backed",
                "current_evidence_combined_operator_read_route",
                "current_evidence_operator_read_gate_route",
                "improvement_rank_section",
                "report_safe_conclusion",
                "short_answer_fragment",
                "stale_ambiguous_phrase_removed",
                "stale_live_default_and_live_paper_lane_removed",
            }
            and row_map["working_status_report"].get("child_check_count") == 26
            and isinstance(row_map["working_status_report"].get("child_checks"), list)
            and {check.get("check") for check in row_map["working_status_report"]["child_checks"]} == {
                "scorecard_nonpositive_phase8_floor_fails_before_artifacts",
                "scorecard_nonpositive_real_money_floor_fails_before_artifacts",
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "bottom_line_framing",
                "demo_wrapper_section",
                "files_added_section",
                "production_vs_demo_distinction",
                "preflight_target_tracks_not_active_basket",
                "demo_lane_section",
                "current_evidence_bridge_section",
                "current_evidence_rebuild_validation_contract_read",
                "source_published_settlement_queue_state",
                "cross_family_current_paper_route_present",
                "full_data_retrain_caveat_route_present",
                "working_status_gate_source_matches_scorecard_json",
                "current_evidence_combined_operator_read_route",
                "current_evidence_operator_read_gate_route",
                working_status_queue_check_name,
                "demo_command_block",
                "report_time_snapshot",
                "operational_bottom_line",
                "stale_latest_phrase_removed",
                "ops_active_tracks_still_op_cd",
                "demo_cli_flags_exist",
                "referenced_artifacts_exist",
            }
            and row_map["cole_presentation_outline"].get("child_check_count") == 25
            and isinstance(row_map["cole_presentation_outline"].get("child_checks"), list)
            and {check.get("check") for check in row_map["cole_presentation_outline"]["child_checks"]} == {
                "scorecard_nonpositive_phase8_floor_fails_before_artifacts",
                "scorecard_nonpositive_real_money_floor_fails_before_artifacts",
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "anchor_source_still_op_durable",
                "presentation_thesis",
                "walk_forward_vs_headline",
                "phase7_beats_phase8_holdout",
                "op_anchor_lines",
                "observation_only_pockets",
                "method_family_guardrail_section",
                "ml_failure_line",
                "full_data_retrain_caveat_route_present",
                "paper_trade_workflow_not_live_proof",
                "presentation_evidence_scope_gate",
                "current_evidence_bridge_slide",
                "source_published_settlement_queue_state",
                "current_evidence_combined_operator_read_route",
                "current_evidence_operator_read_gate_route",
                "current_evidence_scorecard_audit_route_present",
                "current_evidence_rebuild_validation_contract_route",
                "cross_family_current_paper_route_present",
                "current_evidence_bridge_json_is_source_gate_routed",
                "current_evidence_bridge_effective_gates_are_scorecard_backed",
                "short_recommendation",
            }
            and row_map["superfecta_html_report"].get("child_check_count") == 33
            and isinstance(row_map["superfecta_html_report"].get("child_checks"), list)
            and {check.get("check") for check in row_map["superfecta_html_report"]["child_checks"]} == {
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "malformed_scorecard_gate_floors_fail_before_artifacts",
                "anchor_source_still_op_durable",
                "hero_fragment",
                "metric_fragment",
                "selector_table_row",
                "selective_family_current_paper_credibility_wording",
                "paper_trade_workflow_not_new_evidence_frame",
                "html_report_evidence_scope_boundary",
                "current_evidence_bridge_card",
                "html_report_gate_source_matches_scorecard_json",
                "cross_family_current_paper_route_present",
                "html_pdf_scorecard_ci_only_boundary",
                "html_pdf_scorecard_audit_route",
                "html_pdf_current_evidence_rebuild_validation_contract_route",
                "full_data_retrain_caveat_route_present",
                "current_evidence_combined_operator_read_route",
                "current_evidence_operator_read_gate_route",
                "dated_pdf_derivative_current_evidence_bridge",
                "validation_upgrade_card",
                "rule_hierarchy_year_split",
                "improvement_story",
                "bar_title",
                "selector_row_preserved",
                "method_family_guardrail_section",
                "final_stance_fragment",
                "legacy_alias_redirect_notice",
                "legacy_pdf_alias_claim_boundary",
                "legacy_docx_alias_claim_boundary",
                "legacy_quick_start_pdf_alias_claim_boundary",
                "legacy_prompt_docx_alias_claim_boundary",
                "stale_phrase_removed",
            }
            and row_map["shareable_report_pdf_refresh"].get("child_check_count") == 5
            and isinstance(row_map["shareable_report_pdf_refresh"].get("child_checks"), list)
            and {check.get("check") for check in row_map["shareable_report_pdf_refresh"]["child_checks"]} == {
                "helper_script_exposes_safe_check_and_export_paths",
                "helper_check_existing_writes_pass_artifacts",
                "helper_routes_through_html_report_validator",
                "helper_publishes_html_pdf_fingerprints",
                "helper_publishes_report_safe_evidence_boundary",
            },
            "child_report_validators_publish_structured_checks",
            "all six report-surface child validators now have to publish their pinned structured child-check sets instead of only result + summary strings",
        ),
    ]

    suite_read = build_suite_read(rows)
    checks.append(
        require(
            "saved narrative report surfaces, direct validator report paths, and the shareable PDF refresh/check helper path stay pinned across the human-facing rollup" in suite_read,
            "report_surfaces_suite_keeps_reproducibility_visible",
            "report-surfaces suite summary now says plainly that the saved narrative surfaces, direct validator report paths, and shareable PDF refresh/check helper path stay pinned across the human-facing rollup",
        )
    )
    checks.append(
        require(
            "shareable wording, presentation drift, the dated-report trust path, PDF derivative refresh-helper, and the README-inherited wrapper-leaf source-of-truth note stay explicit instead of getting flattened away" in suite_read,
            "report_surfaces_suite_names_shareable_wording_trust_path_scope",
            "report-surfaces suite summary now says plainly that this rollup is the direct shareable-wording / presentation-drift / dated-report-trust-path / PDF-refresh-helper / inherited-wrapper-note sweep rather than a generic narrative read",
        )
    )
    checks.append(
        require(
            "human-facing alignment and export reproducibility check, not new forward evidence by itself" in suite_read
            and "stronger forward confidence still requires settled paper trades and other real forward results" in suite_read,
            "report_surfaces_suite_explicitly_stays_alignment_not_new_evidence",
            "report-surfaces suite summary now says plainly that a green human-facing sweep is alignment checking rather than new forward evidence",
        )
    )
    checks.append(
        require(
            EVIDENCE_BOUNDARY.get("artifact_role") == "human-facing report-surface validator rollup"
            and EVIDENCE_BOUNDARY.get("not_new_forward_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_settled_roi_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_live_profitability_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_real_money_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_promotion_readiness_evidence") is True
            and EVIDENCE_BOUNDARY.get("report_validator_passes_are_alignment_metadata_only") is True
            and "ROI-complete settled paper rows" in EVIDENCE_BOUNDARY.get("stronger_forward_confidence_requires", [])
            and "do not promote OP_REFINED_K7 or Phase 8 from narrative validation cleanliness" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "do not substitute BAQ for BEL" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "machine-readable evidence_boundary metadata" in suite_read
            and "PDF refresh-helper checks" in suite_read,
            "report_surfaces_json_publishes_machine_readable_evidence_boundary",
            "report-surface parent JSON now publishes a machine-readable evidence_boundary block that keeps human-facing wording alignment, dated-report trust-path checks, narrative validator passes, OP_REFINED_K7 / Phase 8 promotion, BAQ/BEL substitution, live profitability, promotion readiness, settled ROI, and real-money evidence in separate lanes",
        )
    )
    payload = {
        "suite_status": "pass",
        "validators_run": len(rows),
        "total_checks": total_checks,
        "rows": rows,
        "current_evidence_bridge_json_read": current_bridge_json_read,
        "current_evidence_rebuild_validation_contract_read": current_rebuild_contract_read,
        "full_report_current_evidence_bridge_json_read": full_report_bridge_json_read,
        "presentation_outline_current_evidence_bridge_json_read": presentation_bridge_json_read,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "check_count": len(checks),
        "checks": checks,
        "summary": {
            "suite_read": suite_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": rebuild_command,
            "child_validator_mode": child_validator_mode,
        },
    }

    lines = [
        "# Report Surfaces Validation",
        "",
        "This report runs the main narrative surfaces and the shareable PDF refresh helper together so the README, long-form markdown report, working-status report, presentation outline, shareable HTML report, and dated PDF maintenance path stay aligned with the frozen evidence standard.",
        "It is the direct sweep for shareable wording, presentation drift, the dated-report trust path, PDF derivative refresh-helper, and the README-inherited wrapper-leaf/source-of-truth note.",
        "",
        f"- Validators run: {len(rows)}",
        f"- Total checks: {total_checks}",
        "- Overall result: PASS",
        "",
        "## Surface Summary",
        "",
        "| Surface | Scope Metric | Result | Source |",
        "|---|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['label']} | {row['metric_value']} {row['metric_label']} | {row['result']} | `{row['json_path']}` |"
        )

    lines.extend(
        [
            "",
            "## Rollup Checks",
            "",
        ]
    )
    for check in checks:
        lines.append(f"- PASS `{check['check']}` — {check['detail']}")

    lines.extend(
        [
            "",
            "## Current Read",
            "",
            f"- Suite read: {suite_read}",
            "",
            "## Child Surface Reads",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- **{row['label']}**: {row['current_read']}")

    lines.extend(
        [
            "",
            "## Rebuild",
            "",
            f"- Working directory: `{BASE}`",
            f"- Command: `{rebuild_command}`",
            f"- Child validator mode: `{child_validator_mode}`",
            "",
            "## Evidence Boundary",
            "",
            f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
            f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
            "- Not new forward evidence; not a live paper-trade ledger; not current-day scanner evidence; not settled ROI; not live-profitability evidence; not real-money evidence; not promotion-readiness evidence.",
            "- Report validator passes are alignment metadata only.",
            f"- Stronger forward confidence still requires: {', '.join(EVIDENCE_BOUNDARY['stronger_forward_confidence_requires'])}.",
            f"- Non-goals: {', '.join(EVIDENCE_BOUNDARY['non_goals'])}.",
            "",
            "## Bottom Line",
            "",
            "If this suite stays green, the main human-facing report surfaces are all telling the same conservative story — and this remains the direct human-facing sweep for shareable wording, presentation drift, the dated-report trust path, PDF derivative refresh-helper, and the README-inherited wrapper-leaf/source-of-truth note:",
            "That green read is a human-facing alignment and export reproducibility check, not new forward evidence by itself; stronger forward confidence still has to come from settled paper trades and other real forward results.",
            "",
            f"- README: {next(row['current_read'] for row in rows if row['name'] == 'readme_current_status')}",
            f"- Full report: {next(row['current_read'] for row in rows if row['name'] == 'cole_full_report')}",
            f"- Working status report: {next(row['current_read'] for row in rows if row['name'] == 'working_status_report')}",
            f"- Presentation outline: {next(row['current_read'] for row in rows if row['name'] == 'cole_presentation_outline')}",
            f"- HTML report: {next(row['current_read'] for row in rows if row['name'] == 'superfecta_html_report')}",
            f"- PDF refresh helper: {next(row['current_read'] for row in rows if row['name'] == 'shareable_report_pdf_refresh')}",
            "",
            "## Sources",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- `{row['json_path']}`")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
