#!/usr/bin/env python3
"""
ab_downstream_comparison.py — Honest A/B comparison of baseline vs enriched
residual payout models through the downstream EV ticket engine.

Tests whether the enriched horse-history model's improved payout prediction
accuracy translates to better downstream betting decisions.

Approach:
  1. Load 14years_major_tracks.csv, reproduce chronological 75/25 split.
  2. Build race-level features matching the training pipeline.
  3. For the enriched path, merge horse-history features from cache.
  4. Score each winning combo with both pre-trained models.
  5. Apply the EV ticket engine thresholds to both predictions.
  6. Compare: prediction accuracy, EV filter pass rates, implied ROI.

Limitation (stated clearly):
  This compares predictions on the *actual winning combos* only. It does NOT
  test whether the enriched model changes the *ranking* of non-winning combos.
  A full combo-level comparison would require building horse features for every
  horse in every race, which is a larger integration.

Output: ab_downstream_comparison_results.json, AB_DOWNSTREAM_COMPARISON.md,
and a printed summary.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import warnings
from contextlib import redirect_stdout
from datetime import datetime
from math import log
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
JSON_OUT = BASE / "ab_downstream_comparison_results.json"
MD_OUT = BASE / "AB_DOWNSTREAM_COMPARISON.md"
CROSS_FAMILY_CSV = BASE / "cross_family_decision_card.csv"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
BASELINE_MODEL = BASE / "ab_baseline_model.json"
ENRICHED_MODEL = BASE / "ab_enriched_model.json"
VALID_EVIDENCE_SCOPE = "downstream_xgboost_ab_research_comparison_only"
EVIDENCE_BOUNDARY = {
    "artifact_role": "downstream baseline-vs-enriched XGBoost A/B comparison artifact",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "valid_use": "research-only downstream EV pass-through comparison plus copied current paper-status caveat",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "current_operator_routing_source": "CURRENT_EVIDENCE_SUMMARY.md / current_evidence_summary.json",
    "current_operator_routing_fields": [
        "operator_status_context",
        "source_freshness",
        "operator_read_gate",
        "decision_gate_progress",
        "scorecard_audit_route",
        "rebuild_validation_contract",
    ],
    "current_operator_routing_requires_combined_route": True,
    "current_operator_routing_is_source_readiness_not_performance": True,
    "non_goals": [
        "do not promote enriched horse-history XGBoost from this artifact",
        "do not reopen current odds-only XGBoost from this artifact",
        "do not use winner-only EV pass-through as a full combo-ranking test",
        "do not substitute BAQ for BEL",
        "do not quote current PAPER_TRADE_NOW instructions from this artifact; use the combined operator_status_context/source_freshness/operator_read_gate route from CURRENT_EVIDENCE_SUMMARY instead",
        "do not treat the copied current-evidence operator snapshot as settled ROI or bet readiness",
        "do not treat the copied scorecard audit route as downstream A/B evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
        "do not treat the copied rebuild-validation contract as downstream A/B evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
    ],
}
EXPECTED_REBUILD_REFRESH_ORDER = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]
EXPECTED_SCORECARD_AUDIT_ROUTE_FIELDS = {
    "markdown_path": "SCORECARD_RANKING_CONTRACT_AUDIT.md",
    "json_path": "scorecard_ranking_contract_audit.json",
    "validator_command": "python3 validate_scorecard_ranking_contract_audit.py",
    "gate_floor_source": "forward_evidence_scorecard.json:decision_gate_minimums",
    "gate_floor_snapshot": {
        "anchor_displacement_min_roi_complete_settled_observations": 30,
        "phase8_promotion_review_min_roi_complete_settled_observations": 20,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": 100,
        "real_money_no_baq_as_bel_required": True,
    },
}
REQUIRED_CURRENT_GATE_PROGRESS_FIELDS = {
    "read",
    "source_path",
    "source_json_path",
    "gate_status",
    "all_gates_ready",
    "primary_first_read",
    "op_anchor_same_candidate_review",
    "phase8_promotion_review",
    "real_money_discussion",
    "not_forward_performance_evidence",
    "not_promotion_readiness_evidence",
    "not_live_profitability_evidence",
    "not_real_money_evidence",
}
REQUIRED_OPERATOR_READ_GATE_TEXT_FIELDS = [
    "gate_status",
    "reason_text",
    "recommended_command",
    "valid_use",
    "read",
]
REQUIRED_OPERATOR_READ_GATE_BOOL_FIELDS = [
    "requires_refresh_before_evidence_read",
    "requires_source_freshness_refresh",
    "has_api_access_failure_context",
    "has_scanner_failure_boundary",
    "has_stale_cache_fallback_context",
    "has_missing_scan_output_artifact_issue",
    "has_wrapper_refresh_action",
    "has_issue_bucket",
    "current_top_card_counts_as_no_target_evidence",
    "current_top_card_counts_as_clean_empty_evidence",
    "current_top_card_counts_as_bet_readiness_evidence",
    "current_top_card_counts_as_settled_roi_evidence",
    "not_forward_performance_evidence",
    "not_promotion_readiness_evidence",
    "not_live_profitability_evidence",
    "not_real_money_evidence",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare baseline vs enriched downstream A/B evidence")
    parser.add_argument("--cross-family-csv", default=str(CROSS_FAMILY_CSV), help="cross-family decision CSV path for selective paper-lane hierarchy labels")
    parser.add_argument("--current-evidence-json", default=str(CURRENT_EVIDENCE_JSON), help="current-evidence bridge JSON path for operator-boundary context")
    parser.add_argument("--md-output", default=str(MD_OUT), help="markdown output path")
    parser.add_argument("--json-output", default=str(JSON_OUT), help="JSON output path")
    parser.add_argument(
        "--refresh-current-evidence-only",
        action="store_true",
        help=(
            "refresh only the copied current-evidence bridge, hierarchy, and model fingerprints "
            "inside an existing saved A/B result without rerunning the raw race-level model comparison"
        ),
    )
    return parser.parse_args()


def file_fingerprint(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": path.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|")


def model_source_fingerprints() -> dict[str, object]:
    return {
        "baseline_model": file_fingerprint(BASELINE_MODEL),
        "enriched_model": file_fingerprint(ENRICHED_MODEL),
    }


def has_timezone_aware_timestamp(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    parse_text = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(parse_text)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def validate_decision_gate_progress(payload: dict[str, Any], source_name: str) -> dict[str, Any]:
    progress = payload.get("decision_gate_progress")
    if not isinstance(progress, dict):
        raise ValueError(f"{source_name} is missing decision_gate_progress")
    missing = sorted(REQUIRED_CURRENT_GATE_PROGRESS_FIELDS - set(progress))
    if missing:
        raise ValueError(f"{source_name} decision_gate_progress is missing fields: {', '.join(missing)}")
    if progress.get("gate_status") != "all_uncleared":
        raise ValueError(f"{source_name} decision_gate_progress must remain gate_status=all_uncleared")
    if progress.get("all_gates_ready") is not False:
        raise ValueError(f"{source_name} decision_gate_progress must keep all_gates_ready=false")
    for flag in (
        "not_forward_performance_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_real_money_evidence",
    ):
        if progress.get(flag) is not True:
            raise ValueError(f"{source_name} decision_gate_progress must mark {flag}=true")

    primary = progress.get("primary_first_read")
    anchor = progress.get("op_anchor_same_candidate_review")
    phase8 = progress.get("phase8_promotion_review")
    real_money = progress.get("real_money_discussion")
    if not all(isinstance(item, dict) for item in (primary, anchor, phase8, real_money)):
        raise ValueError(f"{source_name} decision_gate_progress must publish structured gate-detail blocks")
    if int(primary.get("current_rows", -1)) != 6 or int(primary.get("threshold", -1)) != 30 or primary.get("ready") is not False:
        raise ValueError(f"{source_name} decision_gate_progress primary_first_read must publish uncleared 6/30 progress")
    if (
        anchor.get("candidate_rule_id") != "OP_DURABLE_K7"
        or int(anchor.get("current_rows", -1)) != 0
        or int(anchor.get("threshold", -1)) != 30
        or anchor.get("companion_rows_count_as_anchor_evidence") is not False
    ):
        raise ValueError(f"{source_name} decision_gate_progress must publish OP_DURABLE_K7 same-candidate 0/30 progress")
    if int(phase8.get("weakest_current_rows", -1)) != 0 or int(phase8.get("threshold_per_candidate", -1)) != 20 or phase8.get("ready") is not False:
        raise ValueError(f"{source_name} decision_gate_progress must publish Phase 8 weakest 0/20 progress")
    if int(real_money.get("current_primary_roi_complete_rows", -1)) != 6 or int(real_money.get("threshold", -1)) != 100 or real_money.get("ready") is not False:
        raise ValueError(f"{source_name} decision_gate_progress must publish real-money discussion 6/100 progress")

    read = str(progress.get("read") or "")
    for phrase in (
        "Gate progress: primary first-read 6/30",
        "OP anchor same-candidate 0/30",
        "Phase 8 weakest shadow 0/20",
        "real-money discussion floor 6/100",
        "All remain uncleared",
    ):
        if phrase not in read:
            raise ValueError(f"{source_name} decision_gate_progress.read is missing {phrase!r}")
    return dict(progress)


def validate_scorecard_audit_route(payload: dict[str, Any], source_name: str) -> dict[str, Any]:
    route = payload.get("scorecard_audit_route")
    if not isinstance(route, dict):
        raise ValueError(f"{source_name} is missing scorecard_audit_route")
    for key, expected in EXPECTED_SCORECARD_AUDIT_ROUTE_FIELDS.items():
        if route.get(key) != expected:
            raise ValueError(f"{source_name} scorecard_audit_route.{key} drifted")
    if route.get("artifacts_present") is not True:
        raise ValueError(f"{source_name} scorecard_audit_route must verify referenced artifacts are present")
    for flag in (
        "not_forward_performance_evidence",
        "not_settled_roi_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_bankroll_guidance",
        "not_real_money_evidence",
    ):
        if route.get(flag) is not True:
            raise ValueError(f"{source_name} scorecard_audit_route.{flag} must be true")
    route_read = str(route.get("route_read") or "")
    for phrase in (
        "SCORECARD_RANKING_CONTRACT_AUDIT.md",
        "scorecard_ranking_contract_audit.json",
        "python3 validate_scorecard_ranking_contract_audit.py",
        "copied 30/20/100 gate floors",
        "tier-first ranking",
        "OP_REFINED CI-only support context",
        "generated-at timezone provenance",
        "no-BAQ-as-BEL prerequisite",
    ):
        if phrase not in route_read:
            raise ValueError(f"{source_name} scorecard_audit_route.route_read is missing {phrase!r}")
    return json.loads(json.dumps(route))


def validate_rebuild_validation_contract(payload: dict[str, Any], source_name: str) -> dict[str, Any]:
    contract = payload.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise ValueError(f"{source_name} is missing rebuild_validation_contract")
    order = contract.get("upstream_refresh_order")
    if not isinstance(order, list):
        raise ValueError(f"{source_name} rebuild_validation_contract.upstream_refresh_order must be a list")
    commands = [str(row.get("command") or "") for row in order if isinstance(row, dict)]
    order_values = [row.get("order") for row in order if isinstance(row, dict)]
    if commands != EXPECTED_REBUILD_REFRESH_ORDER:
        raise ValueError(f"{source_name} rebuild_validation_contract upstream order drifted")
    if order_values != [1, 2, 3]:
        raise ValueError(f"{source_name} rebuild_validation_contract order numbers drifted")
    if contract.get("prerequisite_rebuild_command") != EXPECTED_REBUILD_REFRESH_ORDER[0]:
        raise ValueError(f"{source_name} rebuild_validation_contract prerequisite command drifted")
    if contract.get("rebuild_command") != EXPECTED_REBUILD_REFRESH_ORDER[1]:
        raise ValueError(f"{source_name} rebuild_validation_contract rebuild command drifted")
    if contract.get("direct_validation_command") != EXPECTED_REBUILD_REFRESH_ORDER[2]:
        raise ValueError(f"{source_name} rebuild_validation_contract direct validator command drifted")
    for flag in (
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
        "requires_source_consistency_before_quoting_current_totals",
        "requires_source_freshness_before_right_now_instruction_use",
        "green_checks_are_reproducibility_metadata_only",
        "upstream_refresh_order_is_provenance_metadata_only",
        "not_settled_roi_or_real_money_evidence",
    ):
        if contract.get(flag) is not True:
            raise ValueError(f"{source_name} rebuild_validation_contract.{flag} must be true")
    copied = json.loads(json.dumps(contract))
    copied["source_path"] = "rebuild_validation_contract"
    copied["upstream_refresh_commands"] = commands
    return copied


def validate_operator_read_gate(payload: dict[str, Any], source_name: str) -> dict[str, Any]:
    gate = payload.get("operator_read_gate")
    if not isinstance(gate, dict):
        raise ValueError(f"{source_name} is missing operator_read_gate")

    missing_text_fields = [
        field
        for field in REQUIRED_OPERATOR_READ_GATE_TEXT_FIELDS
        if not isinstance(gate.get(field), str) or not str(gate.get(field)).strip()
    ]
    missing_bool_fields = [
        field
        for field in REQUIRED_OPERATOR_READ_GATE_BOOL_FIELDS
        if not isinstance(gate.get(field), bool)
    ]
    if missing_text_fields or missing_bool_fields:
        missing = missing_text_fields + missing_bool_fields
        raise ValueError(f"{source_name} operator_read_gate missing fields: {', '.join(missing)}")

    gate_status = gate.get("gate_status")
    if gate_status not in {"refresh_required_before_evidence_read", "current_operator_routing_context_only"}:
        raise ValueError(
            f"{source_name} operator_read_gate.gate_status must be a known instruction/evidence-read state"
        )
    if gate.get("valid_use") != "operator instruction/evidence-read gating only":
        raise ValueError(f"{source_name} operator_read_gate.valid_use drifted")

    required_true_flags = [
        "not_forward_performance_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_real_money_evidence",
    ]
    false_true_flags = [field for field in required_true_flags if gate.get(field) is not True]
    if false_true_flags:
        raise ValueError(f"{source_name} operator_read_gate must mark {', '.join(false_true_flags)}=true")

    required_false_flags = [
        "current_top_card_counts_as_no_target_evidence",
        "current_top_card_counts_as_clean_empty_evidence",
        "current_top_card_counts_as_bet_readiness_evidence",
        "current_top_card_counts_as_settled_roi_evidence",
    ]
    weakened_false_flags = [field for field in required_false_flags if gate.get(field) is not False]
    if weakened_false_flags:
        raise ValueError(f"{source_name} operator_read_gate must mark {', '.join(weakened_false_flags)}=false")

    read = str(gate.get("read") or "")
    if gate_status == "refresh_required_before_evidence_read":
        if gate.get("recommended_command") != "./run_daily_portfolio_observation.sh":
            raise ValueError(f"{source_name} operator_read_gate must recommend ./run_daily_portfolio_observation.sh")
        required_refresh_flags = [
            "requires_refresh_before_evidence_read",
            "has_wrapper_refresh_action",
        ]
        false_refresh_flags = [field for field in required_refresh_flags if gate.get(field) is not True]
        if false_refresh_flags:
            raise ValueError(f"{source_name} operator_read_gate must mark {', '.join(false_refresh_flags)}=true")
        if not any(
            gate.get(field) is True
            for field in (
                "requires_source_freshness_refresh",
                "has_api_access_failure_context",
                "has_scanner_failure_boundary",
                "has_stale_cache_fallback_context",
                "has_missing_scan_output_artifact_issue",
                "has_issue_bucket",
            )
        ):
            raise ValueError(f"{source_name} operator_read_gate refresh branch must publish a refresh cause")
        for phrase in (
            "Refresh/recheck with `./run_daily_portfolio_observation.sh`",
            "not a no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money read",
        ):
            if phrase not in read:
                raise ValueError(f"{source_name} operator_read_gate.read is missing {phrase!r}")
    else:
        unexpected_refresh_flags = [
            "requires_refresh_before_evidence_read",
            "requires_source_freshness_refresh",
            "has_api_access_failure_context",
            "has_scanner_failure_boundary",
            "has_stale_cache_fallback_context",
            "has_missing_scan_output_artifact_issue",
            "has_wrapper_refresh_action",
            "has_issue_bucket",
        ]
        true_refresh_flags = [field for field in unexpected_refresh_flags if gate.get(field) is not False]
        if true_refresh_flags:
            raise ValueError(
                f"{source_name} current operator-read branch must mark {', '.join(true_refresh_flags)}=false"
            )
        for phrase in (
            "current operator routing context",
            "not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence",
        ):
            if phrase not in read:
                raise ValueError(f"{source_name} operator_read_gate.read is missing {phrase!r}")

    return json.loads(json.dumps(gate))


def load_current_operator_boundary(current_evidence_json: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    current_evidence_json = Path(current_evidence_json)
    source_name = current_evidence_json.name
    payload = json.loads(current_evidence_json.read_text(encoding="utf-8"))
    if not has_timezone_aware_timestamp(payload.get("generated_at")):
        raise ValueError(f"{source_name} generated_at must be timezone-aware ISO provenance metadata")
    decision_gate_progress = validate_decision_gate_progress(payload, source_name)
    scorecard_audit_route = validate_scorecard_audit_route(payload, source_name)
    rebuild_validation_contract = validate_rebuild_validation_contract(payload, source_name)
    operator_read_gate = validate_operator_read_gate(payload, source_name)

    source_freshness = payload.get("source_freshness")
    if not isinstance(source_freshness, dict):
        raise ValueError(f"{source_name} missing source_freshness")
    required_source_freshness_fields = [
        "generated_reference_date",
        "generated_reference_timezone",
        "staleness_comparison_source",
        "staleness_comparison_date",
        "read",
    ]
    missing_source_freshness_fields = [
        field for field in required_source_freshness_fields if not source_freshness.get(field)
    ]
    if missing_source_freshness_fields:
        raise ValueError(
            f"{source_name} source_freshness missing fields: {', '.join(missing_source_freshness_fields)}"
        )
    refresh_action_boundary = source_freshness.get("refresh_action_boundary")
    if not isinstance(refresh_action_boundary, dict):
        raise ValueError(f"{source_name} missing source_freshness.refresh_action_boundary")
    required_refresh_text_fields = ["command", "valid_use", "read"]
    required_refresh_bool_fields = [
        "required_before_right_now_instruction_use",
        "source_action_counts_as_current_instruction_before_refresh",
        "wrapper_refresh_can_update_operator_surfaces",
        "wrapper_refresh_can_settle_open_rows_by_itself",
        "wrapper_refresh_counts_as_roi_complete_evidence_by_itself",
        "clean_empty_refresh_counts_as_forward_performance",
        "missing_or_invalid_artifact_counts_as_clean_quiet_day",
        "not_forward_performance_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_real_money_evidence",
    ]
    missing_refresh_fields = [
        field for field in required_refresh_text_fields if not refresh_action_boundary.get(field)
    ]
    missing_refresh_fields.extend(
        field
        for field in required_refresh_bool_fields
        if not isinstance(refresh_action_boundary.get(field), bool)
    )
    if missing_refresh_fields:
        raise ValueError(
            f"{source_name} source_freshness.refresh_action_boundary missing fields: "
            f"{', '.join(missing_refresh_fields)}"
        )
    required_refresh_true_fields = [
        "not_forward_performance_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_real_money_evidence",
    ]
    false_refresh_fields = [
        field for field in required_refresh_true_fields if refresh_action_boundary.get(field) is not True
    ]
    if false_refresh_fields:
        raise ValueError(
            f"{source_name} source_freshness.refresh_action_boundary must mark "
            f"{', '.join(false_refresh_fields)}=true"
        )
    if refresh_action_boundary.get("wrapper_refresh_can_update_operator_surfaces") is not True:
        raise ValueError(
            f"{source_name} source_freshness.refresh_action_boundary must mark "
            "wrapper_refresh_can_update_operator_surfaces=true"
        )
    required_refresh_false_fields = [
        "wrapper_refresh_can_settle_open_rows_by_itself",
        "wrapper_refresh_counts_as_roi_complete_evidence_by_itself",
        "clean_empty_refresh_counts_as_forward_performance",
        "missing_or_invalid_artifact_counts_as_clean_quiet_day",
    ]
    weakened_refresh_false_fields = [
        field
        for field in required_refresh_false_fields
        if refresh_action_boundary.get(field) is not False
    ]
    if weakened_refresh_false_fields:
        raise ValueError(
            f"{source_name} source_freshness.refresh_action_boundary must mark "
            f"{', '.join(weakened_refresh_false_fields)}=false"
        )
    current_paper = payload.get("current_paper_status")
    if not isinstance(current_paper, dict):
        raise ValueError(f"{source_name} missing current_paper_status")
    operator_status_context = current_paper.get("operator_status_context")
    if not isinstance(operator_status_context, dict):
        raise ValueError(f"{source_name} missing current_paper_status.operator_status_context")
    required_operator_status_text_fields = ["read", "valid_use"]
    missing_operator_status_text_fields = [
        field
        for field in required_operator_status_text_fields
        if not isinstance(operator_status_context.get(field), str)
        or not str(operator_status_context.get(field)).strip()
    ]
    if missing_operator_status_text_fields:
        raise ValueError(
            f"{source_name} current_paper_status.operator_status_context missing fields: "
            f"{', '.join(missing_operator_status_text_fields)}"
        )
    if operator_status_context.get("not_forward_performance_evidence") is not True:
        raise ValueError(
            f"{source_name} current_paper_status.operator_status_context must mark "
            "not_forward_performance_evidence=true"
        )
    best_action = current_paper.get("best_action")
    if not isinstance(best_action, dict):
        raise ValueError(f"{source_name} missing current_paper_status.best_action")
    primary = current_paper.get("primary")
    if not isinstance(primary, dict):
        raise ValueError(f"{source_name} missing current_paper_status.primary")
    first_read = primary.get("first_read")
    if not isinstance(first_read, dict):
        raise ValueError(f"{source_name} missing current_paper_status.primary.first_read")
    anchor_gap = primary.get("anchor_settlement_gap")
    if not isinstance(anchor_gap, dict):
        raise ValueError(f"{source_name} missing current_paper_status.primary.anchor_settlement_gap")
    open_queue = primary.get("open_settlement_queue_by_rule")
    if not isinstance(open_queue, dict):
        raise ValueError(f"{source_name} missing current_paper_status.primary.open_settlement_queue_by_rule")
    rule_progress = {
        str(row.get("rule_id")): row
        for row in primary.get("rule_progress", [])
        if isinstance(row, dict) and row.get("rule_id")
    }

    op_anchor_rows = int(
        anchor_gap.get(
            "anchor_roi_complete_settled_rows",
            rule_progress.get("OP_DURABLE_K7", {}).get("roi_complete_settled_rows", 0),
        )
        or 0
    )
    cd_companion_rows = int(
        anchor_gap.get(
            "companion_roi_complete_settled_rows",
            rule_progress.get("CD_CORE_K8", {}).get("roi_complete_settled_rows", 0),
        )
        or 0
    )
    open_settlement_rows = int(primary.get("open_settlements") or 0)
    open_settlement_queue_state = str(open_queue.get("open_settlement_queue_state") or "").strip()
    open_settlement_context = str(open_queue.get("open_settlement_context") or "").strip()
    open_settlement_queue_read = str(open_queue.get("detail_read") or "").strip()
    expected_open_settlement_queue_state = "closed" if open_settlement_rows == 0 else "open"
    if open_settlement_queue_state not in {"closed", "open"}:
        raise ValueError(
            f"{source_name} current_paper_status.primary.open_settlement_queue_by_rule.open_settlement_queue_state "
            "must be closed or open"
        )
    if open_settlement_queue_state != expected_open_settlement_queue_state:
        raise ValueError(
            f"{source_name} current_paper_status.primary.open_settlement_queue_by_rule.open_settlement_queue_state "
            "must match current_paper_status.primary.open_settlements"
        )
    if not open_settlement_context:
        raise ValueError(
            f"{source_name} current_paper_status.primary.open_settlement_queue_by_rule.open_settlement_context "
            "must be populated"
        )
    if open_settlement_rows == 0 and open_settlement_context != "no open primary settlement rows":
        raise ValueError(
            f"{source_name} current_paper_status.primary.open_settlement_queue_by_rule.open_settlement_context "
            "must read no open primary settlement rows when open_settlements is 0"
        )
    if open_settlement_rows > 0 and open_settlement_context.lower() in {"none", "no open primary settlement rows"}:
        raise ValueError(
            f"{source_name} current_paper_status.primary.open_settlement_queue_by_rule.open_settlement_context "
            "must identify open rows when open_settlements is greater than 0"
        )
    if "Open settlement queue by rule:" not in open_settlement_queue_read:
        raise ValueError(
            f"{source_name} current_paper_status.primary.open_settlement_queue_by_rule.detail_read "
            "must carry the by-rule open settlement detail"
        )
    if "Settlement queue state:" in open_settlement_queue_read:
        raise ValueError(
            f"{source_name} current_paper_status.primary.open_settlement_queue_by_rule.detail_read "
            "must not duplicate the queue-state wrapper"
        )
    combined_route_read = (
        f"{current_evidence_json.name} combined route: use operator_status_context plus "
        f"source_freshness.requires_refresh_before_right_now_use="
        f"{bool(source_freshness.get('requires_refresh_before_right_now_use'))} plus "
        f"operator_read_gate.requires_refresh_before_evidence_read="
        f"{operator_read_gate.get('requires_refresh_before_evidence_read')} before quoting current PAPER_TRADE_NOW "
        f"instructions from this downstream A/B artifact; recommended command="
        f"{operator_read_gate.get('recommended_command')}."
    )

    return {
        "source_path": source_name,
        "source_fingerprint": file_fingerprint(current_evidence_json),
        "generated_at": payload.get("generated_at"),
        "combined_operator_route_read": combined_route_read,
        "operator_status_context_read": operator_status_context.get("read"),
        "operator_status_context_valid_use": operator_status_context.get("valid_use"),
        "operator_status_context_best_action_command": operator_status_context.get("best_action_command"),
        "operator_status_context_ops_day_bucket": operator_status_context.get("ops_day_bucket"),
        "operator_status_context_not_forward_performance_evidence": bool(
            operator_status_context.get("not_forward_performance_evidence")
        ),
        "operator_read_gate": operator_read_gate,
        "right_now_freshness_state": source_freshness.get("right_now_freshness_state"),
        "requires_refresh_before_right_now_use": bool(source_freshness.get("requires_refresh_before_right_now_use")),
        "source_freshness_read": source_freshness.get("read"),
        "source_freshness_generated_reference_date": source_freshness.get("generated_reference_date"),
        "source_freshness_generated_reference_timezone": source_freshness.get("generated_reference_timezone"),
        "source_freshness_staleness_comparison_source": source_freshness.get("staleness_comparison_source"),
        "source_freshness_staleness_comparison_date": source_freshness.get("staleness_comparison_date"),
        "refresh_action_command": refresh_action_boundary.get("command"),
        "refresh_required_before_right_now_instruction_use": bool(
            refresh_action_boundary.get("required_before_right_now_instruction_use")
        ),
        "refresh_can_update_operator_surfaces": bool(
            refresh_action_boundary.get("wrapper_refresh_can_update_operator_surfaces")
        ),
        "refresh_can_settle_open_rows_by_itself": bool(
            refresh_action_boundary.get("wrapper_refresh_can_settle_open_rows_by_itself")
        ),
        "refresh_counts_as_roi_complete_evidence_by_itself": bool(
            refresh_action_boundary.get("wrapper_refresh_counts_as_roi_complete_evidence_by_itself")
        ),
        "clean_empty_refresh_counts_as_forward_performance": bool(
            refresh_action_boundary.get("clean_empty_refresh_counts_as_forward_performance")
        ),
        "refresh_action_boundary_read": refresh_action_boundary.get("read"),
        "refresh_boundary_not_forward_performance_evidence": bool(
            refresh_action_boundary.get("not_forward_performance_evidence")
        ),
        "refresh_boundary_not_promotion_readiness_evidence": bool(
            refresh_action_boundary.get("not_promotion_readiness_evidence")
        ),
        "refresh_boundary_not_live_profitability_evidence": bool(
            refresh_action_boundary.get("not_live_profitability_evidence")
        ),
        "refresh_boundary_not_real_money_evidence": bool(refresh_action_boundary.get("not_real_money_evidence")),
        "best_action_headline": best_action.get("headline"),
        "best_action_command": best_action.get("command"),
        "decision_gate_progress": decision_gate_progress,
        "scorecard_audit_route": scorecard_audit_route,
        "rebuild_validation_contract": rebuild_validation_contract,
        "roi_complete_primary_rows": int(primary.get("roi_complete_settled") or 0),
        "first_read_threshold": int(first_read.get("threshold") or 0),
        "first_read_remaining": int(first_read.get("remaining") or 0),
        "anchor_rule_id": anchor_gap.get("anchor_rule_id", "OP_DURABLE_K7"),
        "companion_rule_id": anchor_gap.get("companion_rule_id", "CD_CORE_K8"),
        "op_anchor_roi_complete_rows": op_anchor_rows,
        "cd_companion_roi_complete_rows": cd_companion_rows,
        "current_settled_context_is_cd_only": bool(
            anchor_gap.get("current_sample_is_cd_only", op_anchor_rows == 0 and cd_companion_rows > 0)
        ),
        "companion_rows_count_as_anchor_evidence": bool(
            anchor_gap.get("companion_rows_count_as_anchor_evidence")
        ),
        "anchor_rows_needed_for_same_candidate_review": int(
            anchor_gap.get("anchor_rows_needed_for_same_candidate_review") or 0
        ),
        "primary_rule_mix_read": primary.get("rule_mix_read"),
        "anchor_settlement_gap_read": anchor_gap.get("read"),
        "open_settlement_rows": open_settlement_rows,
        "open_settlement_queue_state": open_settlement_queue_state,
        "open_settlement_context": open_settlement_context,
        "anchor_open_rows": int(open_queue.get("anchor_open_rows") or 0),
        "companion_open_rows": int(open_queue.get("companion_open_rows") or 0),
        "current_open_queue_is_cd_only": bool(open_queue.get("current_open_queue_is_cd_only")),
        "open_rows_count_as_roi_complete": bool(open_queue.get("open_rows_count_as_roi_complete")),
        "open_rows_count_as_anchor_evidence": bool(open_queue.get("open_rows_count_as_anchor_evidence")),
        "open_settlement_queue_read": open_settlement_queue_read,
        "not_forward_performance_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_live_profitability_evidence": True,
        "not_real_money_evidence": True,
    }

# ── EV engine constants (match ev_ticket_engine.py defaults) ────────
PAYOUT_HAIRCUT = 0.75
MIN_EV_ROI = 0.15
MIN_PROB = 0.0005
PAYOUT_UNIT = 1.0


# ═══════════════════════════════════════════════════════════════════
# DATA LOADING (mirrors train_test_residual.py logic)
# ═══════════════════════════════════════════════════════════════════

def load_selective_shadow_read(cross_family_csv: Path = CROSS_FAMILY_CSV) -> dict[str, object]:
    cross_family_csv = Path(cross_family_csv)
    with cross_family_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    by_shadow = {row["shadow_rank"]: row for row in rows if row.get("shadow_rank")}
    return {
        "current_anchor": by_shadow["LIVE_DEFAULT"]["rule_id"],
        "primary_shadow": by_shadow["PRIMARY_SHADOW"]["rule_id"],
        "primary_companion": by_shadow["PRIMARY_SHADOW"]["rule_id"],
        "secondary_shadow": by_shadow["SECONDARY_SHADOW"]["rule_id"],
        "cross_family_source": file_fingerprint(cross_family_csv),
    }


def safe_float(value, default=np.nan):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if np.isfinite(result) else default


def moneyline_to_prob(odds: float) -> float:
    odds = safe_float(odds)
    if not np.isfinite(odds):
        return np.nan
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return (-odds) / (-odds + 100.0)


def load_and_build(csv_path: Path) -> pd.DataFrame:
    """Load horse-level CSV → race-level DataFrame with features + targets."""
    print(f"Loading {csv_path.name} ...")
    df = pd.read_csv(
        csv_path,
        parse_dates=["race_date"],
        dtype={"post_time": str, "program_number": str, "registration_number": str},
    )
    df["post_time"] = df["post_time"].fillna("").str.extract(r"(\d+)$")[0].str[-4:]
    df["post_time"] = pd.to_datetime(df["post_time"], format="%H%M", errors="coerce")
    df = df[df["scratch_indicator"].fillna("N") != "Y"]

    races_with_winners = (
        df[df["winning_numbers"].notna()]
        [["track_id", "race_date", "race_number"]]
        .drop_duplicates()
    )
    keep = set(zip(races_with_winners.track_id,
                   races_with_winners.race_date,
                   races_with_winners.race_number))

    rows = []
    for (track, date, rnum), grp in df.groupby(["track_id", "race_date", "race_number"]):
        if (track, date, rnum) not in keep:
            continue
        wrows = grp[grp["winning_numbers"].notna()]
        if wrows.empty:
            continue
        wi = wrows.iloc[0]
        wp = [str(x).strip() for x in str(wi["winning_numbers"]).split("-") if str(x).strip()]
        if len(wp) != 4:
            continue

        payoff = safe_float(wi.get("payoff_amount"))
        tickets = safe_float(wi.get("number_of_tickets_bet"))
        if not np.isfinite(payoff) or payoff <= 0 or not np.isfinite(tickets) or tickets <= 0:
            continue

        horses = []
        for _, h in grp.iterrows():
            odds = safe_float(h.get("odds"))
            if np.isfinite(odds):
                rp = moneyline_to_prob(odds)
                if np.isfinite(rp) and rp > 0:
                    horses.append({
                        "prog": str(h["program_number"]).strip(),
                        "reg": str(h.get("registration_number", "")).strip(),
                        "odds": odds,
                        "rp": rp,
                    })
        if len(horses) < 4:
            continue

        tot = sum(h["rp"] for h in horses)
        if tot <= 0:
            continue
        prog_prob = {h["prog"]: h["rp"] / tot for h in horses}
        prog_odds = {h["prog"]: h["odds"] for h in horses}
        prog_reg = {h["prog"]: h["reg"] for h in horses}

        wprobs = [prog_prob.get(p) for p in wp]
        wodds = [prog_odds.get(p) for p in wp]
        wregs = [prog_reg.get(p, "") for p in wp]
        if any(v is None for v in wprobs) or any(v is None for v in wodds):
            continue

        p1, p2, p3, p4 = wprobs
        d1 = 1 - p1
        d2 = d1 - p2
        d3 = d2 - p3
        if d1 <= 0 or d2 <= 0 or d3 <= 0:
            continue
        joint = p1 * (p2 / d1) * (p3 / d2) * (p4 / d3)
        if joint <= 0:
            continue
        h_pay = 1.0 / joint
        actual_payout = float(payoff) * (100.0 / float(tickets))
        lr = log(actual_payout / h_pay)

        all_odds = [h["odds"] for h in horses]
        first = grp.iloc[0]
        post_hour = first["post_time"].hour if pd.notna(first.get("post_time")) else 14
        fs = len(grp)

        rows.append({
            "track_id": track, "race_date": date, "race_number": rnum,
            "prob1": p1, "prob2": p2, "prob3": p3, "prob4": p4,
            "odds1": wodds[0], "odds2": wodds[1], "odds3": wodds[2], "odds4": wodds[3],
            "reg1": wregs[0], "reg2": wregs[1], "reg3": wregs[2], "reg4": wregs[3],
            "number_of_runners": safe_float(first.get("number_of_runners"), default=fs),
            "field_size": fs,
            "purse_usa": safe_float(first.get("purse_usa"), default=0.0),
            "distance_id": safe_float(first.get("distance_id"), default=0.0),
            "post_hour": float(post_hour),
            "total_pool": safe_float(first.get("total_pool"), default=0.0),
            "avg_field_odds": float(np.mean(all_odds)),
            "odds_std": float(np.std(all_odds)) if len(all_odds) > 1 else 0.0,
            "surface": str(first.get("surface", "")).strip(),
            "course_type": str(first.get("course_type", "")).strip(),
            "track_condition": str(first.get("track_condition", "")).strip(),
            "harville_payout": h_pay,
            "actual_payout": actual_payout,
            "joint_prob": joint,
            "log_ratio": lr,
        })

    out = pd.DataFrame(rows).sort_values("race_date").reset_index(drop=True)

    # Remove 3-sigma outliers on log_ratio (same as training)
    mu, sig = out["log_ratio"].mean(), out["log_ratio"].std()
    mask = (out["log_ratio"] >= mu - 3 * sig) & (out["log_ratio"] <= mu + 3 * sig)
    out = out[mask].reset_index(drop=True)

    print(f"  {len(out)} valid races after outlier removal")
    return out


def build_baseline_features(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """Build the ~55-feature matrix matching the baseline model's expectations."""
    eps = 1e-10
    df = df.copy()

    for i in range(1, 5):
        p = df[f"prob{i}"]
        df[f"logit{i}"] = np.where(
            (p > 0) & (p < 1), np.log(p / (1 - p)), 0.0
        )

    df["favorite_odds"] = df[["odds1", "odds2", "odds3", "odds4"]].min(axis=1)
    df["longshot_odds"] = df[["odds1", "odds2", "odds3", "odds4"]].max(axis=1)
    df["odds_range"] = df["longshot_odds"] - df["favorite_odds"]
    df["prob_product"] = df["prob1"] * df["prob2"] * df["prob3"] * df["prob4"]
    df["prob_sum"] = df["prob1"] + df["prob2"] + df["prob3"] + df["prob4"]
    df["min_prob"] = df[["prob1", "prob2", "prob3", "prob4"]].min(axis=1)
    df["max_prob"] = df[["prob1", "prob2", "prob3", "prob4"]].max(axis=1)
    df["prob_variance"] = np.var(
        [df[f"prob{i}"].values for i in range(1, 5)], axis=0
    )
    df["prob_entropy"] = -sum(
        df[f"prob{i}"] * np.log(df[f"prob{i}"] + eps) for i in range(1, 5)
    )
    df["pool_per_runner"] = df["total_pool"] / df["number_of_runners"].replace(0, 1)
    df["purse_per_runner"] = df["purse_usa"] / df["number_of_runners"].replace(0, 1)
    df["harville_log"] = np.log(df["harville_payout"])

    # Categoricals as dummies
    dummies = pd.get_dummies(
        df[["surface", "course_type", "track_condition"]],
        prefix=["surface", "course_type", "track_condition"],
        dummy_na=True,
    )
    df = pd.concat([df, dummies], axis=1)

    feature_cols = (
        [f"logit{i}" for i in range(1, 5)]
        + [f"prob{i}" for i in range(1, 5)]
        + ["number_of_runners", "field_size", "purse_usa", "distance_id",
           "post_hour", "total_pool", "avg_field_odds", "odds_std"]
        + ["favorite_odds", "longshot_odds", "odds_range", "prob_product",
           "prob_sum", "prob_entropy", "min_prob", "max_prob", "pool_per_runner",
           "purse_per_runner", "harville_log", "prob_variance"]
        + list(dummies.columns)
    )

    return df[feature_cols].fillna(0).values, feature_cols, df


def merge_horse_features(df: pd.DataFrame, hf_path: Path) -> tuple[pd.DataFrame, list[str]]:
    """Merge horse-history features for the 4 winners (mirrors training pipeline)."""
    HORSE_COLS = [
        "n_prior_starts", "prior_win_rate", "prior_top3_rate",
        "avg_finish_all", "avg_finish_last5", "days_since_last",
        "avg_prior_purse", "class_change",
        "surface_prior_starts", "surface_win_rate", "surface_avg_finish",
        "distance_prior_starts", "distance_win_rate", "distance_avg_finish",
        "track_prior_starts", "track_win_rate", "track_avg_finish",
    ]

    print(f"Loading horse features from {hf_path.name} ...")
    hf = pd.read_csv(
        hf_path, parse_dates=["race_date"],
        dtype={"program_number": str, "registration_number": str},
    )
    hf["_jk"] = (
        hf["registration_number"].astype(str) + "|"
        + hf["track_id"].astype(str) + "|"
        + hf["race_date"].astype(str) + "|"
        + hf["race_number"].astype(str)
    )
    hf = hf.drop_duplicates(subset="_jk", keep="first")
    hf_lookup = hf.set_index("_jk")[HORSE_COLS]

    new_cols: list[str] = []
    df = df.copy()

    for pos in range(1, 5):
        prefix = f"w{pos}_"
        jk = (
            df[f"reg{pos}"].astype(str) + "|"
            + df["track_id"].astype(str) + "|"
            + df["race_date"].astype(str) + "|"
            + df["race_number"].astype(str)
        )
        matched = hf_lookup.reindex(jk.values)
        for col in HORSE_COLS:
            new_name = f"{prefix}{col}"
            df[new_name] = matched[col].values
            new_cols.append(new_name)

    for col in HORSE_COLS:
        w_cols = [f"w{i}_{col}" for i in range(1, 5)]
        sub = df[w_cols]
        df[f"avg_{col}"] = sub.mean(axis=1)
        df[f"min_{col}"] = sub.min(axis=1)
        df[f"max_{col}"] = sub.max(axis=1)
        new_cols.extend([f"avg_{col}", f"min_{col}", f"max_{col}"])

    df["n_debut_winners"] = sum(
        (df[f"w{i}_n_prior_starts"] == 0).astype(float) for i in range(1, 5)
    )
    new_cols.append("n_debut_winners")

    match_rate = df["w1_n_prior_starts"].notna().mean()
    print(f"  Horse feature match rate: {match_rate:.1%}")
    print(f"  Added {len(new_cols)} horse-history features")

    return df, new_cols


def score_with_model(
    model: xgb.Booster,
    model_feats: list[str],
    df_feats: pd.DataFrame,
    all_feature_cols: list[str],
) -> np.ndarray:
    """Score rows using a pre-trained model, aligning features by name."""
    # Build feature matrix in the order the model expects
    X = np.zeros((len(df_feats), len(model_feats)))
    col_map = {c: i for i, c in enumerate(all_feature_cols)}

    for j, mf in enumerate(model_feats):
        if mf in col_map:
            X[:, j] = df_feats.iloc[:, col_map[mf]].values
        # else: stays 0 (missing feature → 0, same as training fillna(0))

    dm = xgb.DMatrix(X, feature_names=model_feats)
    return model.predict(dm)


def ev_pass(joint_prob: float, predicted_payout: float) -> tuple[bool, float]:
    """Apply the EV engine's core bet/no-bet decision for a single ticket."""
    if joint_prob < MIN_PROB:
        return False, 0.0
    adj = predicted_payout * PAYOUT_HAIRCUT
    gross = adj / PAYOUT_UNIT
    ev_profit = joint_prob * gross - 1.0

    if ev_profit < MIN_EV_ROI:
        return False, 0.0

    # Kelly check (simplified — same as ev_ticket_engine)
    net = gross - 1.0
    if gross < 1.05:
        return False, 0.0
    kelly = (joint_prob * net - (1.0 - joint_prob)) / net
    if kelly <= 0:
        return False, 0.0

    return True, ev_profit


def combined_operator_route_boundary_text(current_operator_boundary: dict[str, Any]) -> str:
    if (
        current_operator_boundary.get("requires_refresh_before_right_now_use")
        or (current_operator_boundary.get("operator_read_gate") or {}).get("requires_refresh_before_evidence_read")
    ):
        return (
            "The combined route is refresh-before-instruction/evidence-read routing only; do not quote current "
            "PAPER_TRADE_NOW instructions from this artifact as no-target, clean-empty, bet-readiness, settled ROI, "
            "model-family proof, OP-anchor proof, promotion, live-profitability, bankroll, or real-money evidence"
        )
    return (
        "The combined route is instruction/evidence-read gating only; the saved top card is fresh operator-routing "
        "context, not no-target, clean-empty, bet-readiness, settled ROI, model-family proof, OP-anchor proof, "
        "promotion, live-profitability, bankroll, or real-money evidence"
    )


def operator_read_gate_boundary_text(gate: dict[str, Any]) -> str:
    if gate.get("requires_refresh_before_evidence_read"):
        return (
            "The saved top card must be refreshed before evidence/instruction use; this read gate is not no-target "
            "evidence, clean-empty evidence, model-family proof, OP-anchor proof, bet readiness, settled ROI, "
            "promotion readiness, live profitability, bankroll guidance, or real-money evidence"
        )
    return (
        "The saved top card can be read only as current operator instruction/evidence gating context; this read gate "
        "is not no-target evidence, clean-empty evidence, model-family proof, OP-anchor proof, bet readiness, "
        "settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence"
    )


def build_markdown(results: dict[str, object]) -> str:
    test_set = results["test_set"]
    shadow_read = results["selective_shadow_read"]
    source = shadow_read.get("cross_family_source", {}) if isinstance(shadow_read, dict) else {}
    if isinstance(source, dict) and source.get("path") and source.get("sha256"):
        hierarchy_source_line = (
            f"- Selective paper-lane hierarchy source: `{source['path']}` "
            f"(`sha256={source['sha256']}`, `{source.get('bytes', 0)}` bytes)."
        )
    else:
        hierarchy_source_line = "- Selective paper-lane hierarchy source: not recorded in this payload."
    pred = results["prediction_accuracy"]
    base = pred["baseline"]
    enriched = pred["enriched"]
    delta = pred["delta"]
    ev = results["ev_engine_comparison"]
    ev_base = ev["baseline"]
    ev_enriched = ev["enriched"]
    disagreement = results["disagreement_analysis"]
    limitation = results["limitation"]
    pass_delta = ev["delta"]
    model_fingerprints = results.get("model_source_fingerprints", {})
    current_operator_boundary = results.get("current_operator_boundary") or {}
    decision_gate_progress = current_operator_boundary.get("decision_gate_progress")
    if not isinstance(decision_gate_progress, dict):
        decision_gate_progress = {}

    payout_rmse_improvement_pct = (
        (base["payout_rmse"] - enriched["payout_rmse"]) / base["payout_rmse"] * 100.0
    )
    log_ratio_rmse_improvement_pct = (
        (base["log_ratio_rmse"] - enriched["log_ratio_rmse"]) / base["log_ratio_rmse"] * 100.0
    )
    current_anchor_label = current_operator_boundary.get("anchor_rule_id", "OP_DURABLE_K7")
    current_companion_label = current_operator_boundary.get("companion_rule_id", "CD_CORE_K8")
    rebuild_contract = current_operator_boundary.get("rebuild_validation_contract") or {}
    rebuild_order_commands = rebuild_contract.get("upstream_refresh_commands")
    if not isinstance(rebuild_order_commands, list):
        rebuild_order_commands = [
            str(row.get("command") or "")
            for row in rebuild_contract.get("upstream_refresh_order", [])
            if isinstance(row, dict)
        ]
    rebuild_order_read = " -> ".join(f"`{command}`" for command in rebuild_order_commands)
    operator_read_gate = current_operator_boundary.get("operator_read_gate") or {}
    combined_route_boundary = combined_operator_route_boundary_text(current_operator_boundary)
    operator_gate_boundary = operator_read_gate_boundary_text(operator_read_gate)

    lines = [
        "# A/B Downstream Comparison",
        "",
        "This artifact compares the current baseline payout model against the enriched horse-history XGBoost path on the same chronological test set.",
        "",
        "## Guardrail",
        "",
        "- This is a research comparison, not a paper-promotion case.",
        f"- Valid evidence scope: `valid_evidence_scope={results.get('valid_evidence_scope') or VALID_EVIDENCE_SCOPE}`.",
        "- The selective rule path remains the only method family in `PAPER NOW` status.",
        f"- Inside that paper lane, `{shadow_read['current_anchor']}` remains the safest anchor, `{shadow_read['primary_companion']}` is the primary OP/CD paper-basket companion, and `{shadow_read['secondary_shadow']}` stays a smaller same-family OP shadow challenger rather than a promoted default.",
        hierarchy_source_line,
        "- A modest payout-prediction improvement is not enough by itself to promote the enriched horse-history XGBoost path into paper-betting logic.",
        "- Non-goal: do not quote current `PAPER_TRADE_NOW` instructions from this A/B artifact without the combined `CURRENT_EVIDENCE_SUMMARY` `operator_status_context` / `source_freshness` / `operator_read_gate` route.",
        "",
        "## Current Read",
        "",
        f"- On {test_set['n_races']} test-set winning combos from {test_set['date_range']}, the enriched horse-history XGBoost path improves payout prediction error by {payout_rmse_improvement_pct:.2f}% and log-ratio RMSE by {log_ratio_rmse_improvement_pct:.2f}%, but it still does not create a cleaner deployment case because conservative EV winner pass counts drift down by {abs(pass_delta['ev_pass_count_delta'])} ({pass_delta['ev_pass_count_relative_change_pct']:+.2f}% relative; {pass_delta['ev_pass_pct_point_delta']:+.4f} percentage points of test winners) from {ev_base['ev_pass_count']} baseline to {ev_enriched['ev_pass_count']} enriched.",
        "",
        "## Current Paper Snapshot",
        "",
        f"This snapshot is copied from `{current_operator_boundary.get('source_path', 'current_evidence_summary.json')}` so the A/B model comparison can show the current paper-lane caveat without becoming a live-performance surface.",
        "",
        "| Item | Current Read | Boundary |",
        "|---|---|---|",
        f"| Combined operator route | {md_cell(current_operator_boundary.get('combined_operator_route_read'))} Operator context read = {md_cell(current_operator_boundary.get('operator_status_context_read'))}; ops bucket = `{current_operator_boundary.get('operator_status_context_ops_day_bucket')}` | {combined_route_boundary} |",
        f"| Source freshness | `{current_operator_boundary.get('right_now_freshness_state')}`; refresh before right-now use = `{current_operator_boundary.get('requires_refresh_before_right_now_use')}`; bridge reference = `{current_operator_boundary.get('source_freshness_generated_reference_date')}` (`{current_operator_boundary.get('source_freshness_generated_reference_timezone')}`); comparison = `{current_operator_boundary.get('source_freshness_staleness_comparison_source')}` / `{current_operator_boundary.get('source_freshness_staleness_comparison_date')}`; read = {md_cell(current_operator_boundary.get('source_freshness_read'))} | Source freshness is operator-readiness metadata, not performance proof |",
        f"| Refresh action boundary | `{current_operator_boundary.get('refresh_action_command')}` required before right-now use = `{current_operator_boundary.get('refresh_required_before_right_now_instruction_use')}`; settles rows / creates ROI evidence / clean-empty performance = `{current_operator_boundary.get('refresh_can_settle_open_rows_by_itself')}` / `{current_operator_boundary.get('refresh_counts_as_roi_complete_evidence_by_itself')}` / `{current_operator_boundary.get('clean_empty_refresh_counts_as_forward_performance')}` | Wrapper refresh is operator routing only; it is not settled ROI, promotion readiness, live profitability, or real-money evidence |",
        f"| Operator read gate | `{current_operator_boundary.get('source_path', 'current_evidence_summary.json')}` `operator_read_gate`: {md_cell(operator_read_gate.get('read'))} Gate status = `{operator_read_gate.get('gate_status')}`; recommended command = `{operator_read_gate.get('recommended_command')}` | {operator_gate_boundary} |",
        f"| Bridge-published gate progress | `{current_operator_boundary.get('source_path', 'current_evidence_summary.json')}` `decision_gate_progress`: {md_cell(decision_gate_progress.get('read'))} Source: `{decision_gate_progress.get('source_path')}` `{decision_gate_progress.get('source_json_path')}`; gate status = `{decision_gate_progress.get('gate_status')}` | Current gates are all uncleared routing context only; they do not change the downstream A/B model comparison or create settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll, or real-money evidence |",
        f"| Scorecard audit route | `{current_operator_boundary.get('source_path', 'current_evidence_summary.json')}` `scorecard_audit_route`: {md_cell((current_operator_boundary.get('scorecard_audit_route') or {}).get('route_read'))} Validator: `{(current_operator_boundary.get('scorecard_audit_route') or {}).get('validator_command')}`; artifacts: `{(current_operator_boundary.get('scorecard_audit_route') or {}).get('markdown_path')}` / `{(current_operator_boundary.get('scorecard_audit_route') or {}).get('json_path')}`; gate snapshot = 30/20/100 with no-BAQ-as-BEL required `{((current_operator_boundary.get('scorecard_audit_route') or {}).get('gate_floor_snapshot') or {}).get('real_money_no_baq_as_bel_required')}` | Report-synchronization route only; it is not downstream A/B evidence, forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
        f"| Current bridge rebuild order | `{current_operator_boundary.get('source_path', 'current_evidence_summary.json')}` `rebuild_validation_contract`: {rebuild_order_read} before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes | Provenance/rebuild route only; green checks and rebuild order are not downstream A/B evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
        f"| Current settled rule mix | {current_anchor_label}={current_operator_boundary.get('op_anchor_roi_complete_rows')}; {current_companion_label}={current_operator_boundary.get('cd_companion_roi_complete_rows')}; {md_cell(current_operator_boundary.get('primary_rule_mix_read'))} | Rule-specific settled rows stay separate; CD-only paper rows are not OP-anchor forward evidence |",
        f"| Settlement queue state | `{current_operator_boundary.get('open_settlement_queue_state')}`; {md_cell(current_operator_boundary.get('open_settlement_context'))}; detail: {md_cell(current_operator_boundary.get('open_settlement_queue_read'))} | Open rows are settlement workflow only; fill outcomes from result/payout evidence before interpreting ROI |",
        f"| Operator route | `{current_operator_boundary.get('best_action_command')}` | Use the bridge route for operator context; do not infer profit, promotion, or real-money readiness from the route itself |",
        "",
        "## Test Set",
        "",
        f"- Chronological split date: `{test_set['split_date']}`",
        f"- Test races: `{test_set['n_races']}` winning combos",
        f"- Date range: `{test_set['date_range']}`",
        "",
        "## Prediction Accuracy (winning combos only)",
        "",
        "| Metric | Baseline | Enriched | Delta |",
        "|---|---:|---:|---:|",
        f"| log-ratio RMSE | {base['log_ratio_rmse']:.6f} | {enriched['log_ratio_rmse']:.6f} | {delta['log_ratio_rmse']:+.6f} |",
        f"| log-ratio R² | {base['log_ratio_r2']:.6f} | {enriched['log_ratio_r2']:.6f} | {delta['log_ratio_r2']:+.6f} |",
        f"| payout RMSE | {base['payout_rmse']:.2f} | {enriched['payout_rmse']:.2f} | {delta['payout_rmse']:+.2f} |",
        f"| payout RMSE improvement vs Harville | {base['payout_rmse_improvement_vs_harville_pct']:.2f}% | {enriched['payout_rmse_improvement_vs_harville_pct']:.2f}% | {enriched['payout_rmse_improvement_vs_harville_pct'] - base['payout_rmse_improvement_vs_harville_pct']:+.2f}pp |",
        "",
        "## Conservative EV Pass-Through",
        "",
        f"- EV filter: `{int(PAYOUT_HAIRCUT * 100)}%` payout haircut, `{int(MIN_EV_ROI * 100)}%` minimum EV ROI, `Kelly > 0`, `joint_prob >= {MIN_PROB}`",
        "- These pass counts are computed on the true winning combos only, so the flat ROI figures below are diagnostic outputs, not deployable ROI claims.",
        "",
        "| Path | Winner pass count | Winner pass % | Avg EV profit at filter | Diagnostic flat ROI on passing winners |",
        "|---|---:|---:|---:|---:|",
        f"| Baseline | {ev_base['ev_pass_count']} | {ev_base['ev_pass_pct']:.4f}% | {ev_base['avg_ev_profit_at_filter']:.4f} | {ev_base['implied_flat_roi_pct']:+.2f}% |",
        f"| Enriched | {ev_enriched['ev_pass_count']} | {ev_enriched['ev_pass_pct']:.4f}% | {ev_enriched['avg_ev_profit_at_filter']:.4f} | {ev_enriched['implied_flat_roi_pct']:+.2f}% |",
        "",
        f"- Pass-through delta vs baseline: `{pass_delta['ev_pass_count_delta']:+d}` winner passes, `{pass_delta['ev_pass_count_relative_change_pct']:+.2f}%` relative, `{pass_delta['ev_pass_pct_point_delta']:+.4f}` percentage points of the winning-combo test set.",
        "- Even where the enriched path shows slightly higher average EV profit on the winning-combo subset, that read remains diagnostic only because it comes from a tiny, winner-only slice rather than a full paper-candidate ranking test.",
        "",
        "## Disagreement Analysis",
        "",
        "| Bucket | Count | Diagnostic ROI on winning-combo subset |",
        "|---|---:|---:|",
        f"| Both pass | {disagreement['both_pass']['count']} | {disagreement['both_pass']['roi_pct']:+.2f}% |",
        f"| Only baseline passes | {disagreement['only_baseline_pass']['count']} | {disagreement['only_baseline_pass']['roi_pct']:+.2f}% |",
        f"| Only enriched passes | {disagreement['only_enriched_pass']['count']} | {disagreement['only_enriched_pass']['roi_pct']:+.2f}% |",
        f"| Neither passes | {disagreement['neither_pass']} | n/a |",
        "",
        "## Model Source Fingerprints",
        "",
        "Exact model artifact fingerprints for this saved A/B read. Use them as reproducibility metadata only; they do not prove paper ROI, promotion readiness, live profitability, or real-money performance.",
        "",
        "| Source | Path | Bytes | SHA-256 |",
        "|---|---|---:|---|",
        *[
            f"| `{label}` | `{fingerprint['path']}` | {fingerprint['bytes']} | `{fingerprint['sha256']}` |"
            for label, fingerprint in model_fingerprints.items()
        ],
        "",
        "## Limitation",
        "",
        f"- {limitation}",
        "",
        "## Bottom Line",
        "",
        "- The enriched horse-history XGBoost path is still useful as model research because it modestly improves payout prediction quality on the matched test set.",
        "- That prediction gain still does not outrank the frozen selective-rule evidence chain, because the downstream conservative EV picture stays small, winner-only, and not clearly better on pass counts.",
        f"- Keep the enriched horse-history XGBoost path in `RESEARCH ONLY`, keep Harville in `BENCHMARK ONLY`, and keep the selective rule path as the only `PAPER NOW` family, with `{shadow_read['current_anchor']}` still the safest anchor, `{shadow_read['primary_companion']}` as the primary OP/CD paper-basket companion, and `{shadow_read['secondary_shadow']}` as the same-family OP shadow challenger.",
    ]
    return "\n".join(lines) + "\n"


def refresh_saved_current_evidence(
    *,
    json_output: Path,
    md_output: Path,
    current_evidence_json: Path,
    cross_family_csv: Path,
) -> dict[str, object]:
    if not json_output.exists():
        raise FileNotFoundError(
            f"{json_output} is required for --refresh-current-evidence-only; "
            "run a full rebuild when raw A/B inputs are available"
        )

    results = json.loads(json_output.read_text(encoding="utf-8"))
    required_sections = [
        "test_set",
        "prediction_accuracy",
        "ev_engine_comparison",
        "disagreement_analysis",
        "limitation",
    ]
    missing_sections = [section for section in required_sections if section not in results]
    if missing_sections:
        raise ValueError(
            f"{json_output.name} is missing saved A/B result sections needed for refresh: "
            f"{', '.join(missing_sections)}"
        )

    results["selective_shadow_read"] = load_selective_shadow_read(cross_family_csv)
    results["current_operator_boundary"] = load_current_operator_boundary(current_evidence_json)
    results["model_source_fingerprints"] = model_source_fingerprints()
    results["valid_evidence_scope"] = VALID_EVIDENCE_SCOPE
    results["evidence_boundary"] = json.loads(json.dumps(EVIDENCE_BOUNDARY))

    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    md_output.write_text(build_markdown(results), encoding="utf-8")
    return results


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main() -> int:
    args = parse_args()
    cross_family_csv = Path(args.cross_family_csv)
    current_evidence_json = Path(args.current_evidence_json)
    md_output = Path(args.md_output)
    json_output = Path(args.json_output)
    current_operator_boundary = load_current_operator_boundary(current_evidence_json)
    t0 = time.time()

    if args.refresh_current_evidence_only:
        results = refresh_saved_current_evidence(
            json_output=json_output,
            md_output=md_output,
            current_evidence_json=current_evidence_json,
            cross_family_csv=cross_family_csv,
        )
        markdown = build_markdown(results)
        print(markdown, end="")
        print(f"Saved: {md_output.name}")
        print(f"Saved: {json_output.name}")
        return 0

    with redirect_stdout(sys.stderr):
        # ── 1. Load data ────────────────────────────────────────────────
        csv_path = BASE / "14years_major_tracks.csv"
        if not csv_path.exists():
            print(f"ERROR: {csv_path} not found")
            return 1

        races = load_and_build(csv_path)
        print(f"  Date range: {races['race_date'].min().date()} → {races['race_date'].max().date()}")

        # ── 2. Chronological 75/25 split (same as validation) ──────────
        n = len(races)
        split_idx = int(n * 0.75)
        test = races.iloc[split_idx:].copy().reset_index(drop=True)
        split_date = test["race_date"].iloc[0].date()
        print(f"\nChronological split: train {split_idx} races, test {len(test)} races")
        print(f"  Test set starts: {split_date}")

        # ── 3. Load both models ─────────────────────────────────────────
        baseline_path = BASELINE_MODEL
        enriched_path = ENRICHED_MODEL

        for p in [baseline_path, enriched_path]:
            if not p.exists():
                print(f"ERROR: {p} not found")
                return 1

        bl_model = xgb.Booster()
        bl_model.load_model(str(baseline_path))
        bl_feats = bl_model.feature_names
        print(f"\nBaseline model: {len(bl_feats)} features")

        en_model = xgb.Booster()
        en_model.load_model(str(enriched_path))
        en_feats = en_model.feature_names
        print(f"Enriched model: {len(en_feats)} features")

        # ── 4. Build features ───────────────────────────────────────────
        print("\nBuilding baseline features ...")
        _, bl_cols, test_feat = build_baseline_features(test)

        print("Building enriched features ...")
        hf_path = BASE / "horse_features_major_tracks.csv"
        if not hf_path.exists():
            print(f"ERROR: {hf_path} not found")
            return 1
        test_horse, horse_cols = merge_horse_features(test_feat, hf_path)

        all_enriched_cols = bl_cols + horse_cols
        enriched_feat_df = test_horse[all_enriched_cols].fillna(0)

        # ── 5. Score with both models ───────────────────────────────────
        print("\nScoring test set ...")
        bl_preds = score_with_model(bl_model, bl_feats, test_feat[bl_cols].fillna(0), bl_cols)
        en_preds = score_with_model(en_model, en_feats, enriched_feat_df, all_enriched_cols)

        test["bl_log_ratio"] = bl_preds
        test["en_log_ratio"] = en_preds
        test["bl_predicted_payout"] = test["harville_payout"] * np.exp(bl_preds)
        test["en_predicted_payout"] = test["harville_payout"] * np.exp(en_preds)

        # ── 6. Prediction accuracy ──────────────────────────────────────
        actual_lr = test["log_ratio"].values
        actual_pay = test["actual_payout"].values

        def metrics(preds_lr, preds_pay, label):
            from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
            from scipy.stats import pearsonr

            lr_rmse = float(np.sqrt(mean_squared_error(actual_lr, preds_lr)))
            lr_r2 = float(r2_score(actual_lr, preds_lr))
            lr_corr = float(pearsonr(actual_lr, preds_lr)[0])
            pay_rmse = float(np.sqrt(mean_squared_error(actual_pay, preds_pay)))
            pay_mae = float(mean_absolute_error(actual_pay, preds_pay))
            harv_rmse = float(np.sqrt(mean_squared_error(actual_pay, test["harville_payout"].values)))
            payout_imp = (harv_rmse - pay_rmse) / harv_rmse * 100
            return {
                "label": label,
                "log_ratio_rmse": round(lr_rmse, 6),
                "log_ratio_r2": round(lr_r2, 6),
                "log_ratio_corr": round(lr_corr, 6),
                "payout_rmse": round(pay_rmse, 2),
                "payout_mae": round(pay_mae, 2),
                "payout_rmse_improvement_vs_harville_pct": round(payout_imp, 2),
            }

        bl_metrics = metrics(bl_preds, test["bl_predicted_payout"].values, "baseline")
        en_metrics = metrics(en_preds, test["en_predicted_payout"].values, "enriched")

        # ── 7. EV engine pass-through ───────────────────────────────────
        print("\nApplying EV engine thresholds ...")
        bl_bets = []
        en_bets = []

        for i in range(len(test)):
            jp = test.iloc[i]["joint_prob"]
            ap = test.iloc[i]["actual_payout"]

            bl_pass, bl_ev = ev_pass(jp, test.iloc[i]["bl_predicted_payout"])
            en_pass, en_ev = ev_pass(jp, test.iloc[i]["en_predicted_payout"])

            bl_bets.append({"pass": bl_pass, "ev": bl_ev, "actual": ap, "cost": 1.0})
            en_bets.append({"pass": en_pass, "ev": en_ev, "actual": ap, "cost": 1.0})

        test["bl_ev_pass"] = [b["pass"] for b in bl_bets]
        test["en_ev_pass"] = [b["pass"] for b in en_bets]

        n_test = len(test)

        def ev_summary(bets, label):
            passed = [b for b in bets if b["pass"]]
            n_pass = len(passed)
            if n_pass == 0:
                return {
                    "label": label,
                    "ev_pass_count": 0,
                    "ev_pass_pct": 0.0,
                    "note": "No winning combos passed the EV filter — this is expected "
                    "because the EV engine is very conservative (25% haircut + "
                    "15% min ROI + Kelly). Most winning combos do NOT pass.",
                }
            total_cost = sum(b["cost"] for b in passed)
            total_return = sum(b["actual"] for b in passed)
            roi = (total_return - total_cost) / total_cost * 100
            avg_ev = np.mean([b["ev"] for b in passed])
            return {
                "label": label,
                "ev_pass_count": n_pass,
                "ev_pass_pct": round(n_pass / n_test * 100, 4),
                "total_wagered": round(total_cost, 2),
                "total_returned": round(total_return, 2),
                "implied_flat_roi_pct": round(roi, 2),
                "avg_ev_profit_at_filter": round(avg_ev, 4),
            }

        bl_ev = ev_summary(bl_bets, "baseline")
        en_ev = ev_summary(en_bets, "enriched")

        # ── 8. Disagreement analysis ────────────────────────────────────
        neither = sum(1 for i in range(n_test) if not bl_bets[i]["pass"] and not en_bets[i]["pass"])

        def bucket_roi(indices):
            if not indices:
                return {"count": 0}
            total_ret = sum(test.iloc[i]["actual_payout"] for i in indices)
            total_cost = len(indices)
            return {
                "count": len(indices),
                "total_returned": round(total_ret, 2),
                "roi_pct": round((total_ret - total_cost) / total_cost * 100, 2),
            }

        only_en_idx = [i for i in range(n_test) if not bl_bets[i]["pass"] and en_bets[i]["pass"]]
        only_bl_idx = [i for i in range(n_test) if bl_bets[i]["pass"] and not en_bets[i]["pass"]]
        both_idx = [i for i in range(n_test) if bl_bets[i]["pass"] and en_bets[i]["pass"]]

        disagreement = {
            "both_pass": bucket_roi(both_idx),
            "only_baseline_pass": bucket_roi(only_bl_idx),
            "only_enriched_pass": bucket_roi(only_en_idx),
            "neither_pass": neither,
        }

        # ── 9. Payout prediction comparison at percentiles ──────────────
        bl_err = np.abs(test["bl_predicted_payout"].values - actual_pay)
        en_err = np.abs(test["en_predicted_payout"].values - actual_pay)
        pct_labels = [10, 25, 50, 75, 90]
        payout_percentile_comparison = {}
        for pct in pct_labels:
            payout_percentile_comparison[f"p{pct}"] = {
                "baseline_mae": round(float(np.percentile(bl_err, pct)), 2),
                "enriched_mae": round(float(np.percentile(en_err, pct)), 2),
            }

        # ── 10. Assemble results ────────────────────────────────────────
        elapsed = time.time() - t0
        selective_shadow_read = load_selective_shadow_read(cross_family_csv)
        results = {
            "test_set": {
                "n_races": n_test,
                "split_date": str(split_date),
                "date_range": f"{test['race_date'].min().date()} → {test['race_date'].max().date()}",
            },
            "selective_shadow_read": selective_shadow_read,
            "current_operator_boundary": current_operator_boundary,
            "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
            "evidence_boundary": json.loads(json.dumps(EVIDENCE_BOUNDARY)),
            "model_source_fingerprints": model_source_fingerprints(),
            "prediction_accuracy": {
                "baseline": bl_metrics,
                "enriched": en_metrics,
                "delta": {
                    "log_ratio_rmse": round(en_metrics["log_ratio_rmse"] - bl_metrics["log_ratio_rmse"], 6),
                    "log_ratio_r2": round(en_metrics["log_ratio_r2"] - bl_metrics["log_ratio_r2"], 6),
                    "payout_rmse": round(en_metrics["payout_rmse"] - bl_metrics["payout_rmse"], 2),
                },
            },
            "ev_engine_comparison": {
                "baseline": bl_ev,
                "enriched": en_ev,
                "delta": {
                    "ev_pass_count_delta": en_ev["ev_pass_count"] - bl_ev["ev_pass_count"],
                    "ev_pass_count_relative_change_pct": round(
                        ((en_ev["ev_pass_count"] - bl_ev["ev_pass_count"]) / bl_ev["ev_pass_count"] * 100.0),
                        2,
                    ) if bl_ev["ev_pass_count"] else None,
                    "ev_pass_pct_point_delta": round(en_ev["ev_pass_pct"] - bl_ev["ev_pass_pct"], 4),
                    "avg_ev_profit_at_filter_delta": round(
                        en_ev.get("avg_ev_profit_at_filter", 0.0) - bl_ev.get("avg_ev_profit_at_filter", 0.0),
                        4,
                    ),
                },
            },
            "disagreement_analysis": disagreement,
            "payout_error_percentiles": payout_percentile_comparison,
            "limitation": (
                "This comparison tests predictions on actual winning combos only. "
                "It does NOT test whether the enriched model changes the ranking of "
                "non-winning combos. The EV pass rates here indicate how often each "
                "model's payout prediction for the *true winner* would have cleared "
                "the conservative EV filter."
            ),
        }

        print("\n" + "=" * 72)
        print("A/B DOWNSTREAM COMPARISON: BASELINE vs ENRICHED HORSE-HISTORY MODEL")
        print("=" * 72)
        print(f"\nTest set: {n_test} races, {split_date} onward")
        print("\n── Prediction accuracy (winning combos) ──")
        print(f"  {'Metric':<35} {'Baseline':>12} {'Enriched':>12} {'Delta':>10}")
        print(f"  {'log_ratio RMSE':<35} {bl_metrics['log_ratio_rmse']:>12.4f} {en_metrics['log_ratio_rmse']:>12.4f} {en_metrics['log_ratio_rmse'] - bl_metrics['log_ratio_rmse']:>+10.4f}")
        print(f"  {'log_ratio R²':<35} {bl_metrics['log_ratio_r2']:>12.4f} {en_metrics['log_ratio_r2']:>12.4f} {en_metrics['log_ratio_r2'] - bl_metrics['log_ratio_r2']:>+10.4f}")
        print(f"  {'payout RMSE ($)':<35} {bl_metrics['payout_rmse']:>12.2f} {en_metrics['payout_rmse']:>12.2f} {en_metrics['payout_rmse'] - bl_metrics['payout_rmse']:>+10.2f}")
        print(f"  {'payout RMSE improvement vs Harv.':<35} {bl_metrics['payout_rmse_improvement_vs_harville_pct']:>11.1f}% {en_metrics['payout_rmse_improvement_vs_harville_pct']:>11.1f}%")
        print("\n── EV engine pass-through (conservative thresholds) ──")
        print(f"  EV filter: {PAYOUT_HAIRCUT:.0%} haircut, {MIN_EV_ROI:.0%} min ROI, Kelly > 0")
        print(f"  Baseline: {bl_ev['ev_pass_count']} winners passed ({bl_ev.get('ev_pass_pct', 0):.2f}%)")
        print(f"  Enriched: {en_ev['ev_pass_count']} winners passed ({en_ev.get('ev_pass_pct', 0):.2f}%)")
        if bl_ev["ev_pass_count"] > 0:
            print(f"  Baseline implied flat-bet ROI: {bl_ev.get('implied_flat_roi_pct', 0):+.1f}%")
        if en_ev["ev_pass_count"] > 0:
            print(f"  Enriched implied flat-bet ROI: {en_ev.get('implied_flat_roi_pct', 0):+.1f}%")
        print("\n── Disagreement analysis ──")
        print(f"  Both pass:           {disagreement['both_pass']['count']}")
        print(f"  Only baseline pass:  {disagreement['only_baseline_pass']['count']}")
        print(f"  Only enriched pass:  {disagreement['only_enriched_pass']['count']}")
        print(f"  Neither pass:        {disagreement['neither_pass']}")
        if disagreement["only_enriched_pass"]["count"] > 0:
            print(f"  Enriched-only ROI:   {disagreement['only_enriched_pass']['roi_pct']:+.1f}%")
        if disagreement["only_baseline_pass"]["count"] > 0:
            print(f"  Baseline-only ROI:   {disagreement['only_baseline_pass']['roi_pct']:+.1f}%")
        print(f"\nCompleted in {elapsed:.1f}s")
        print("=" * 72)

    json_text = json.dumps(results, indent=2) + "\n"
    markdown = build_markdown(results)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json_text, encoding="utf-8")
    md_output.write_text(markdown, encoding="utf-8")
    print(markdown, end="")
    print(f"Saved: {md_output.name}")
    print(f"Saved: {json_output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
