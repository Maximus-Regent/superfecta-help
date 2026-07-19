#!/usr/bin/env python3
"""
Evaluate frozen superfecta portfolios on chronological holdouts.

Why this exists:
- The old residual-model script used a shuffled train/test split.
- Later rule-search phases used temporal splits, but portfolio selection was still
  mostly judged on full-history summaries.
- This script evaluates already-defined rule sets as frozen portfolios on later years,
  which is closer to how they would behave in deployment.

Outputs:
- frozen_portfolio_eval_summary.csv
- frozen_portfolio_eval_yearly.csv
- FROZEN_PORTFOLIO_EVAL.md
"""

from __future__ import annotations

from argparse import ArgumentParser
import hashlib
import json
from datetime import datetime
from math import perm
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path("/Users/maximusregent_ai/Shared/Superfecta Help")
CACHE_PATH = BASE / "phase5_race_cache.pkl"
PHASE7_RULES_PATH = BASE / "phase7_live_rules.json"
OUT_SUMMARY = BASE / "frozen_portfolio_eval_summary.csv"
OUT_YEARLY = BASE / "frozen_portfolio_eval_yearly.csv"
OUT_REPORT = BASE / "FROZEN_PORTFOLIO_EVAL.md"
OUT_METADATA = BASE / "frozen_portfolio_eval_metadata.json"
CURRENT_EVIDENCE_SUMMARY = BASE / "current_evidence_summary.json"

HOLDOUT_YEARS = [2024, 2025]
TRAIN_END_YEAR = 2023
SOURCE_SCOPE = "cached major-track race-level dataset + phase7_live_rules.json + embedded Phase 8 frozen rule definitions"
VALID_EVIDENCE_SCOPE = "frozen_portfolio_replay_chronological_holdout_only"
EVIDENCE_BOUNDARY = (
    "historical frozen replay only; not a live paper-trade ledger, live-profitability proof, "
    "promotion-ready evidence, or real-money evidence"
)
EVIDENCE_BOUNDARY_METADATA_ROLE = "frozen chronological holdout replay metadata"
REQUIRED_SOURCE_FRESHNESS_FIELDS = [
    "generated_reference_date",
    "generated_reference_timezone",
    "staleness_comparison_source",
    "staleness_comparison_date",
    "read",
]
REQUIRED_REFRESH_ACTION_BOUNDARY_TEXT_FIELDS = [
    "command",
    "valid_use",
    "read",
]
REQUIRED_REFRESH_ACTION_BOUNDARY_BOOL_FIELDS = [
    "required_before_right_now_instruction_use",
    "source_action_counts_as_current_instruction_before_refresh",
    "not_forward_performance_evidence",
    "not_live_profitability_evidence",
    "not_promotion_readiness_evidence",
    "not_real_money_evidence",
    "wrapper_refresh_can_update_operator_surfaces",
    "wrapper_refresh_can_settle_open_rows_by_itself",
    "wrapper_refresh_counts_as_roi_complete_evidence_by_itself",
    "clean_empty_refresh_counts_as_forward_performance",
    "missing_or_invalid_artifact_counts_as_clean_quiet_day",
]
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
REQUIRED_REBUILD_REFRESH_ORDER = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]

PHASE8_FROZEN_RULES = [
    {
        "rule_id": "BEL_BROAD1_K7",
        "track": "BEL",
        "k": 7,
        "field_min": 11,
        "field_max": 13,
        "gap_min": 0.22,
        "fav_prob_min": 0.35,
        "condition": "fast",
        "card_min": 5,
    },
    {
        "rule_id": "OP_REFINED_K7",
        "track": "OP",
        "k": 7,
        "field_min": 11,
        "field_max": 12,
        "gap_min": 0.05,
        "fav_prob_min": 0.25,
        "condition": "all",
        "card_min": 9,
    },
    {
        "rule_id": "AQU_K9",
        "track": "AQU",
        "k": 9,
        "field_min": 10,
        "field_max": 11,
        "gap_min": 0.22,
        "fav_prob_min": 0.0,
        "condition": "all",
        "card_min": 9,
    },
    {
        "rule_id": "SA_K9",
        "track": "SA",
        "k": 9,
        "field_min": 11,
        "field_max": 12,
        "gap_min": 0.20,
        "fav_prob_min": 0.0,
        "condition": "fast",
        "card_min": 9,
    },
    {
        "rule_id": "KEE_K9",
        "track": "KEE",
        "k": 9,
        "field_min": 12,
        "field_max": 14,
        "gap_min": 0.05,
        "fav_prob_min": 0.35,
        "condition": "fast",
        "card_min": 1,
    },
    {
        "rule_id": "CD_REFINED_K9",
        "track": "CD",
        "k": 9,
        "field_min": 11,
        "field_max": 12,
        "gap_min": 0.0,
        "fav_prob_min": 0.30,
        "condition": "all",
        "card_min": 7,
        "top2_mass_min": 0.55,
    },
    {
        "rule_id": "DMR_FALL_K7",
        "track": "DMR",
        "k": 7,
        "field_min": 10,
        "field_max": 11,
        "gap_min": 0.10,
        "fav_prob_min": 0.0,
        "condition": "all",
        "card_min": 5,
        "months": [9, 10, 11],
    },
]


def file_fingerprint(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": path.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def source_file_fingerprints(current_evidence_path: Path = CURRENT_EVIDENCE_SUMMARY) -> dict[str, dict[str, object]]:
    return {
        "race_cache": file_fingerprint(CACHE_PATH),
        "phase7_rules": file_fingerprint(PHASE7_RULES_PATH),
        "generator": file_fingerprint(Path(__file__).resolve()),
        "current_evidence_summary": file_fingerprint(current_evidence_path),
    }


def has_timezone_aware_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parse_text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(parse_text)
    except ValueError:
        return False
    return parsed.utcoffset() is not None


def require_current_evidence_generated_at(current_evidence: dict[str, object], current_evidence_path: Path) -> None:
    if not has_timezone_aware_timestamp(current_evidence.get("generated_at")):
        raise ValueError(f"{current_evidence_path.name} generated_at must be timezone-aware ISO provenance metadata")


def format_source_fingerprint(label: str, info: dict[str, object]) -> str:
    return f"- {label}: {info['path']} ({info['bytes']} bytes, sha256={info['sha256']})"


def frozen_replay_evidence_boundary_metadata(
    *,
    phase7_holdout: dict[str, object],
    phase8_holdout: dict[str, object],
) -> dict[str, object]:
    return {
        "artifact_role": EVIDENCE_BOUNDARY_METADATA_ROLE,
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "valid_use": "historical frozen replay reproducibility and posture metadata",
        "source_scope": SOURCE_SCOPE,
        "holdout_years": HOLDOUT_YEARS,
        "train_end_year": TRAIN_END_YEAR,
        "phase7_over_phase8_holdout_read": (
            "Phase 7 current-paper rules remain ahead of Phase 8 frozen rules on the "
            f"{HOLDOUT_YEARS[0]}-{HOLDOUT_YEARS[-1]} frozen holdout"
        ),
        "phase7_holdout_roi": phase7_holdout["roi"],
        "phase7_holdout_races": phase7_holdout["races"],
        "phase8_holdout_roi": phase8_holdout["roi"],
        "phase8_holdout_races": phase8_holdout["races"],
        "current_operator_routing_requires_combined_route": True,
        "current_operator_route_source": "current_evidence_summary.json",
        "current_operator_route": [
            "operator_status_context",
            "source_freshness",
            "operator_read_gate",
        ],
        "current_bridge_rebuild_route_source": "current_evidence_summary.json.rebuild_validation_contract",
        "current_bridge_rebuild_order": REQUIRED_REBUILD_REFRESH_ORDER,
        "current_bridge_rebuild_route_valid_use": (
            "provenance/rebuild metadata only before quoting CURRENT_EVIDENCE_SUMMARY after source-byte changes"
        ),
        "not_live_paper_trade_ledger": True,
        "not_current_day_scanner_result": True,
        "not_live_profitability_evidence": True,
        "not_real_money_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_anchor_change_evidence": True,
        "not_companion_change_evidence": True,
        "not_phase8_promotion_evidence": True,
        "not_baq_as_bel_evidence": True,
        "baq_as_bel_substitution_allowed": False,
        "non_goals": [
            "do not treat historical frozen replay P&L as live paper-trade ledger evidence",
            "do not treat source fingerprints as performance evidence",
            "do not promote Phase 8 or OP_REFINED_K7 from this artifact",
            "do not change the OP_DURABLE_K7 anchor from this artifact",
            "do not substitute BAQ for BEL",
            "do not discuss real-money profitability from this artifact",
        ],
    }


def load_current_evidence_summary(current_evidence_path: Path = CURRENT_EVIDENCE_SUMMARY) -> dict[str, object]:
    """Read the current bridge so the frozen report does not hardcode live-paper counts."""
    payload = json.loads(current_evidence_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{current_evidence_path.name} must contain a JSON object")
    require_current_evidence_generated_at(payload, current_evidence_path)
    current_source_freshness_context(payload, current_evidence_path)
    current_refresh_action_boundary_context(payload, current_evidence_path)
    current_operator_read_gate_context(payload, current_evidence_path)
    current_rebuild_validation_contract_context(payload, current_evidence_path)
    return payload


def current_rebuild_validation_contract_context(
    current_evidence: dict[str, object],
    current_evidence_path: Path = CURRENT_EVIDENCE_SUMMARY,
) -> dict[str, object]:
    contract = current_evidence.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise ValueError(f"{current_evidence_path.name} is missing rebuild_validation_contract")
    order = contract.get("upstream_refresh_order")
    if not isinstance(order, list):
        raise ValueError(f"{current_evidence_path.name} rebuild_validation_contract.upstream_refresh_order must be a list")
    commands: list[str] = []
    for expected_order, row in enumerate(order, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"{current_evidence_path.name} rebuild_validation_contract.upstream_refresh_order row drifted")
        if row.get("order") != expected_order:
            raise ValueError(f"{current_evidence_path.name} rebuild_validation_contract.upstream_refresh_order order drifted")
        command = str(row.get("command") or "")
        reason = str(row.get("reason") or "")
        if not command or not reason:
            raise ValueError(f"{current_evidence_path.name} rebuild_validation_contract.upstream_refresh_order row is incomplete")
        commands.append(command)
    if commands != REQUIRED_REBUILD_REFRESH_ORDER:
        raise ValueError(f"{current_evidence_path.name} rebuild_validation_contract upstream order drifted")
    expected_values = {
        "prerequisite_rebuild_command": "python3 paper_trade_settlement_audit.py",
        "rebuild_command": "python3 current_evidence_summary.py",
        "direct_validation_command": "python3 validate_current_evidence_summary.py",
        "upstream_refresh_order_valid_use": (
            "reproducible rebuild order for current bridge provenance after scorecard/rules/ledger byte changes"
        ),
    }
    for key, expected in expected_values.items():
        if contract.get(key) != expected:
            raise ValueError(f"{current_evidence_path.name} rebuild_validation_contract.{key} drifted")
    required_true_flags = [
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
        "green_checks_are_reproducibility_metadata_only",
        "requires_source_consistency_before_quoting_current_totals",
        "requires_source_freshness_before_right_now_instruction_use",
        "upstream_refresh_order_is_provenance_metadata_only",
        "not_settled_roi_or_real_money_evidence",
    ]
    weakened_flags = [flag for flag in required_true_flags if contract.get(flag) is not True]
    if weakened_flags:
        raise ValueError(
            f"{current_evidence_path.name} rebuild_validation_contract must mark "
            f"{', '.join(weakened_flags)}=true"
        )
    return {
        "source_path": "rebuild_validation_contract",
        "upstream_refresh_commands": commands,
        "prerequisite_rebuild_command": contract["prerequisite_rebuild_command"],
        "rebuild_command": contract["rebuild_command"],
        "direct_validation_command": contract["direct_validation_command"],
        "upstream_refresh_order_valid_use": contract["upstream_refresh_order_valid_use"],
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": contract[
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
        ],
        "requires_source_consistency_before_quoting_current_totals": contract[
            "requires_source_consistency_before_quoting_current_totals"
        ],
        "requires_source_freshness_before_right_now_instruction_use": contract[
            "requires_source_freshness_before_right_now_instruction_use"
        ],
        "green_checks_are_reproducibility_metadata_only": contract[
            "green_checks_are_reproducibility_metadata_only"
        ],
        "upstream_refresh_order_is_provenance_metadata_only": contract[
            "upstream_refresh_order_is_provenance_metadata_only"
        ],
        "not_settled_roi_or_real_money_evidence": contract["not_settled_roi_or_real_money_evidence"],
    }


def current_source_freshness_context(
    current_evidence: dict[str, object],
    current_evidence_path: Path = CURRENT_EVIDENCE_SUMMARY,
) -> dict[str, object]:
    source_freshness = current_evidence.get("source_freshness")
    if not isinstance(source_freshness, dict):
        raise ValueError(f"{current_evidence_path.name} is missing source_freshness")
    missing = [
        field
        for field in REQUIRED_SOURCE_FRESHNESS_FIELDS
        if source_freshness.get(field) in (None, "")
    ]
    if missing:
        raise ValueError(f"{current_evidence_path.name} source_freshness is missing fields: {', '.join(missing)}")
    return {
        "generated_reference_date": str(source_freshness["generated_reference_date"]),
        "generated_reference_timezone": str(source_freshness["generated_reference_timezone"]),
        "staleness_comparison_source": str(source_freshness["staleness_comparison_source"]),
        "staleness_comparison_date": str(source_freshness["staleness_comparison_date"]),
        "read": str(source_freshness["read"]),
        "right_now_freshness_state": str(source_freshness.get("right_now_freshness_state") or "unknown"),
        "requires_refresh_before_right_now_use": bool(
            source_freshness.get("requires_refresh_before_right_now_use")
        ),
    }


def current_refresh_action_boundary_context(
    current_evidence: dict[str, object],
    current_evidence_path: Path = CURRENT_EVIDENCE_SUMMARY,
) -> dict[str, object]:
    source_freshness = current_evidence.get("source_freshness")
    if not isinstance(source_freshness, dict):
        raise ValueError(f"{current_evidence_path.name} is missing source_freshness")
    refresh_action = source_freshness.get("refresh_action_boundary")
    if not isinstance(refresh_action, dict):
        raise ValueError(f"{current_evidence_path.name} source_freshness is missing refresh_action_boundary")
    missing = [
        field
        for field in REQUIRED_REFRESH_ACTION_BOUNDARY_TEXT_FIELDS
        if refresh_action.get(field) in (None, "")
    ]
    missing.extend(
        field
        for field in REQUIRED_REFRESH_ACTION_BOUNDARY_BOOL_FIELDS
        if not isinstance(refresh_action.get(field), bool)
    )
    if missing:
        raise ValueError(
            f"{current_evidence_path.name} source_freshness.refresh_action_boundary is missing fields: "
            f"{', '.join(missing)}"
        )
    required_true_fields = [
        "not_forward_performance_evidence",
        "not_live_profitability_evidence",
        "not_promotion_readiness_evidence",
        "not_real_money_evidence",
    ]
    weakened_true_fields = [
        field for field in required_true_fields if refresh_action.get(field) is not True
    ]
    if weakened_true_fields:
        raise ValueError(
            f"{current_evidence_path.name} source_freshness.refresh_action_boundary must mark "
            f"{', '.join(weakened_true_fields)}=true"
        )
    if refresh_action.get("wrapper_refresh_can_update_operator_surfaces") is not True:
        raise ValueError(
            f"{current_evidence_path.name} source_freshness.refresh_action_boundary must mark "
            "wrapper_refresh_can_update_operator_surfaces=true"
        )
    required_false_fields = [
        "wrapper_refresh_can_settle_open_rows_by_itself",
        "wrapper_refresh_counts_as_roi_complete_evidence_by_itself",
        "clean_empty_refresh_counts_as_forward_performance",
        "missing_or_invalid_artifact_counts_as_clean_quiet_day",
    ]
    weakened_false_fields = [
        field for field in required_false_fields if refresh_action.get(field) is not False
    ]
    if weakened_false_fields:
        raise ValueError(
            f"{current_evidence_path.name} source_freshness.refresh_action_boundary must mark "
            f"{', '.join(weakened_false_fields)}=false"
        )
    return {
        "command": str(refresh_action["command"]),
        "valid_use": str(refresh_action["valid_use"]),
        "read": str(refresh_action["read"]),
        "required_before_right_now_instruction_use": refresh_action["required_before_right_now_instruction_use"],
        "source_action_counts_as_current_instruction_before_refresh": refresh_action[
            "source_action_counts_as_current_instruction_before_refresh"
        ],
        "not_forward_performance_evidence": refresh_action["not_forward_performance_evidence"],
        "not_live_profitability_evidence": refresh_action["not_live_profitability_evidence"],
        "not_promotion_readiness_evidence": refresh_action["not_promotion_readiness_evidence"],
        "not_real_money_evidence": refresh_action["not_real_money_evidence"],
        "wrapper_refresh_can_update_operator_surfaces": refresh_action[
            "wrapper_refresh_can_update_operator_surfaces"
        ],
        "wrapper_refresh_can_settle_open_rows_by_itself": refresh_action[
            "wrapper_refresh_can_settle_open_rows_by_itself"
        ],
        "wrapper_refresh_counts_as_roi_complete_evidence_by_itself": refresh_action[
            "wrapper_refresh_counts_as_roi_complete_evidence_by_itself"
        ],
        "clean_empty_refresh_counts_as_forward_performance": refresh_action[
            "clean_empty_refresh_counts_as_forward_performance"
        ],
        "missing_or_invalid_artifact_counts_as_clean_quiet_day": refresh_action[
            "missing_or_invalid_artifact_counts_as_clean_quiet_day"
        ],
    }


def current_operator_read_gate_context(
    current_evidence: dict[str, object],
    current_evidence_path: Path = CURRENT_EVIDENCE_SUMMARY,
) -> dict[str, object]:
    gate = current_evidence.get("operator_read_gate")
    if not isinstance(gate, dict):
        raise ValueError(f"{current_evidence_path.name} is missing operator_read_gate")
    status = current_evidence.get("current_paper_status")
    if isinstance(status, dict) and gate != status.get("operator_read_gate"):
        raise ValueError(
            f"{current_evidence_path.name} operator_read_gate must match current_paper_status.operator_read_gate"
        )
    missing = [
        field
        for field in REQUIRED_OPERATOR_READ_GATE_TEXT_FIELDS
        if gate.get(field) in (None, "")
    ]
    missing.extend(
        field
        for field in REQUIRED_OPERATOR_READ_GATE_BOOL_FIELDS
        if not isinstance(gate.get(field), bool)
    )
    if missing:
        raise ValueError(f"{current_evidence_path.name} operator_read_gate is missing fields: {', '.join(missing)}")
    gate_status = gate.get("gate_status")
    if gate_status not in {"refresh_required_before_evidence_read", "current_operator_routing_context_only"}:
        raise ValueError(
            f"{current_evidence_path.name} operator_read_gate.gate_status must be a known "
            "instruction/evidence-read state"
        )
    if gate.get("valid_use") != "operator instruction/evidence-read gating only":
        raise ValueError(f"{current_evidence_path.name} operator_read_gate.valid_use drifted")
    required_true_fields = [
        "not_forward_performance_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_real_money_evidence",
    ]
    weakened_true_fields = [
        field for field in required_true_fields if gate.get(field) is not True
    ]
    if weakened_true_fields:
        raise ValueError(
            f"{current_evidence_path.name} operator_read_gate must mark "
            f"{', '.join(weakened_true_fields)}=true"
        )
    required_false_fields = [
        "current_top_card_counts_as_no_target_evidence",
        "current_top_card_counts_as_clean_empty_evidence",
        "current_top_card_counts_as_bet_readiness_evidence",
        "current_top_card_counts_as_settled_roi_evidence",
    ]
    weakened_false_fields = [
        field for field in required_false_fields if gate.get(field) is not False
    ]
    if weakened_false_fields:
        raise ValueError(
            f"{current_evidence_path.name} operator_read_gate must mark "
            f"{', '.join(weakened_false_fields)}=false"
        )
    read = str(gate["read"]).strip()
    if gate_status == "refresh_required_before_evidence_read":
        if gate.get("recommended_command") != "./run_daily_portfolio_observation.sh":
            raise ValueError(
                f"{current_evidence_path.name} operator_read_gate must recommend ./run_daily_portfolio_observation.sh"
            )
        required_refresh_fields = [
            "requires_refresh_before_evidence_read",
            "has_wrapper_refresh_action",
        ]
        false_refresh_fields = [
            field for field in required_refresh_fields if gate.get(field) is not True
        ]
        if false_refresh_fields:
            raise ValueError(
                f"{current_evidence_path.name} operator_read_gate must mark "
                f"{', '.join(false_refresh_fields)}=true"
            )
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
            raise ValueError(f"{current_evidence_path.name} operator_read_gate refresh branch must publish a refresh cause")
        for phrase in (
            "Refresh/recheck with `./run_daily_portfolio_observation.sh`",
            "not a no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money read",
        ):
            if phrase not in read:
                raise ValueError(f"{current_evidence_path.name} operator_read_gate.read is missing {phrase!r}")
    else:
        unexpected_refresh_fields = [
            "requires_refresh_before_evidence_read",
            "requires_source_freshness_refresh",
            "has_api_access_failure_context",
            "has_scanner_failure_boundary",
            "has_stale_cache_fallback_context",
            "has_missing_scan_output_artifact_issue",
            "has_wrapper_refresh_action",
            "has_issue_bucket",
        ]
        true_refresh_fields = [
            field for field in unexpected_refresh_fields if gate.get(field) is not False
        ]
        if true_refresh_fields:
            raise ValueError(
                f"{current_evidence_path.name} current operator-read branch must mark "
                f"{', '.join(true_refresh_fields)}=false"
            )
        for phrase in (
            "current operator routing context",
            "not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence",
        ):
            if phrase not in read:
                raise ValueError(f"{current_evidence_path.name} operator_read_gate.read is missing {phrase!r}")
    return {
        "gate_status": str(gate["gate_status"]),
        "valid_use": str(gate["valid_use"]),
        "reason_text": str(gate["reason_text"]),
        "recommended_command": str(gate["recommended_command"]),
        "requires_refresh_before_evidence_read": gate["requires_refresh_before_evidence_read"],
        "requires_source_freshness_refresh": gate["requires_source_freshness_refresh"],
        "has_api_access_failure_context": gate["has_api_access_failure_context"],
        "has_scanner_failure_boundary": gate["has_scanner_failure_boundary"],
        "has_stale_cache_fallback_context": gate["has_stale_cache_fallback_context"],
        "has_missing_scan_output_artifact_issue": gate["has_missing_scan_output_artifact_issue"],
        "has_wrapper_refresh_action": gate["has_wrapper_refresh_action"],
        "has_issue_bucket": gate["has_issue_bucket"],
        "current_top_card_counts_as_no_target_evidence": gate[
            "current_top_card_counts_as_no_target_evidence"
        ],
        "current_top_card_counts_as_clean_empty_evidence": gate[
            "current_top_card_counts_as_clean_empty_evidence"
        ],
        "current_top_card_counts_as_bet_readiness_evidence": gate[
            "current_top_card_counts_as_bet_readiness_evidence"
        ],
        "current_top_card_counts_as_settled_roi_evidence": gate[
            "current_top_card_counts_as_settled_roi_evidence"
        ],
        "not_forward_performance_evidence": gate["not_forward_performance_evidence"],
        "not_promotion_readiness_evidence": gate["not_promotion_readiness_evidence"],
        "not_live_profitability_evidence": gate["not_live_profitability_evidence"],
        "not_real_money_evidence": gate["not_real_money_evidence"],
        "read": read,
    }


def current_boundary_date(current_evidence: dict[str, object]) -> str:
    return str(current_boundary_info(current_evidence)["date"])


def current_boundary_info(current_evidence: dict[str, object]) -> dict[str, object]:
    source_freshness = current_evidence.get("source_freshness")
    if isinstance(source_freshness, dict):
        if source_freshness.get("generated_reference_date"):
            return {
                "date": str(source_freshness["generated_reference_date"]),
                "source": "source_freshness.generated_reference_date",
                "timezone": source_freshness.get("generated_reference_timezone"),
            }
        if source_freshness.get("generated_date"):
            return {
                "date": str(source_freshness["generated_date"]),
                "source": "source_freshness.generated_date",
                "timezone": None,
            }
    generated_at = str(current_evidence.get("generated_at") or "")
    if "T" in generated_at:
        return {"date": generated_at.split("T", 1)[0], "source": "generated_at_date", "timezone": None}
    return {"date": generated_at or "unknown", "source": "unknown", "timezone": None}


def current_boundary_source_line(current_evidence: dict[str, object]) -> str:
    freshness = current_source_freshness_context(current_evidence)
    return (
        f"- Source freshness provenance: bridge reference `{freshness['generated_reference_date']}` "
        f"(`{freshness['generated_reference_timezone']}`); comparison "
        f"`{freshness['staleness_comparison_source']}` = `{freshness['staleness_comparison_date']}`; "
        f"right-now state `{freshness['right_now_freshness_state']}`; refresh before right-now use = "
        f"`{freshness['requires_refresh_before_right_now_use']}`; read: {freshness['read']} "
        "This is source-routing metadata only, not frozen-replay or live-performance evidence."
    )


def current_refresh_action_boundary_line(current_evidence: dict[str, object]) -> str:
    refresh_action = current_refresh_action_boundary_context(current_evidence)
    return (
        f"- Refresh action boundary: `{refresh_action['command']}` valid use = "
        f"{refresh_action['valid_use']}; required before right-now use = "
        f"`{refresh_action['required_before_right_now_instruction_use']}`; source action counts as current before "
        f"refresh = `{refresh_action['source_action_counts_as_current_instruction_before_refresh']}`; can update operator surfaces = "
        f"`{refresh_action['wrapper_refresh_can_update_operator_surfaces']}`, but can settle open rows by itself = "
        f"`{refresh_action['wrapper_refresh_can_settle_open_rows_by_itself']}`, counts as ROI-complete evidence by itself = "
        f"`{refresh_action['wrapper_refresh_counts_as_roi_complete_evidence_by_itself']}`, clean-empty refresh counts as "
        f"forward performance = `{refresh_action['clean_empty_refresh_counts_as_forward_performance']}`, missing/invalid artifacts count as "
        f"a clean quiet day = `{refresh_action['missing_or_invalid_artifact_counts_as_clean_quiet_day']}`; "
        f"not forward/live-profitability/promotion/real-money evidence = "
        f"`{refresh_action['not_forward_performance_evidence']}` / "
        f"`{refresh_action['not_live_profitability_evidence']}` / "
        f"`{refresh_action['not_promotion_readiness_evidence']}` / "
        f"`{refresh_action['not_real_money_evidence']}`; read: {refresh_action['read']}"
    )


def current_operator_read_gate_line(current_evidence: dict[str, object]) -> str:
    gate = current_operator_read_gate_context(current_evidence)
    requires_refresh = str(gate["requires_refresh_before_evidence_read"]).lower()
    return (
        f"- Operator read gate: `operator_read_gate.requires_refresh_before_evidence_read="
        f"{requires_refresh}`; gate status = `{gate['gate_status']}`; "
        f"recommended command = `{gate['recommended_command']}`; read: {gate['read']} "
        "This is instruction/evidence-read routing only, not frozen-replay performance evidence."
    )


def current_rebuild_validation_contract_line(current_evidence: dict[str, object]) -> str:
    contract = current_rebuild_validation_contract_context(current_evidence)
    return (
        "- Current bridge rebuild order: `current_evidence_summary.json` `rebuild_validation_contract` "
        f"routes source-byte changes through {' -> '.join(contract['upstream_refresh_commands'])} "
        "before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, "
        "not frozen-replay performance, settled ROI, live profitability, promotion readiness, "
        "bankroll guidance, or real-money evidence."
    )


def current_paper_context(current_evidence: dict[str, object]) -> dict[str, object]:
    status = current_evidence.get("current_paper_status")
    if not isinstance(status, dict):
        raise ValueError("current_evidence_summary.json is missing current_paper_status")
    primary = status.get("primary")
    if not isinstance(primary, dict):
        raise ValueError("current_evidence_summary.json is missing current_paper_status.primary")
    first_read = primary.get("first_read") if isinstance(primary.get("first_read"), dict) else {}
    recommendation_context = (
        primary.get("recommendation_context") if isinstance(primary.get("recommendation_context"), dict) else {}
    )
    open_settlements = int(primary.get("open_settlements", 0) or 0)
    open_summary = str(primary.get("open_settlement_summary") or "").strip()
    if open_settlements > 0 and open_summary.lower() in {"", "none"}:
        raise ValueError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_summary "
            "must identify open rows when open_settlements > 0"
        )
    open_queue = primary.get("open_settlement_queue_by_rule")
    if not isinstance(open_queue, dict):
        raise ValueError(
            "current_evidence_summary.json is missing "
            "current_paper_status.primary.open_settlement_queue_by_rule"
        )
    open_settlement_queue_state = str(open_queue.get("open_settlement_queue_state") or "").strip()
    open_settlement_context = str(open_queue.get("open_settlement_context") or "").strip()
    open_settlement_queue_read = str(open_queue.get("detail_read") or "").strip()
    expected_open_settlement_queue_state = "closed" if open_settlements == 0 else "open"
    if open_settlement_queue_state not in {"closed", "open"}:
        raise ValueError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_queue_state must be closed or open"
        )
    if open_settlement_queue_state != expected_open_settlement_queue_state:
        raise ValueError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_queue_state must match current_paper_status.primary.open_settlements"
        )
    if not open_settlement_context:
        raise ValueError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_context is required"
        )
    if open_settlements == 0 and open_settlement_context != "no open primary settlement rows":
        raise ValueError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_context must read no open primary settlement rows when open_settlements is 0"
        )
    if open_settlements > 0 and "open" not in open_settlement_context.lower():
        raise ValueError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_context must identify open rows when open_settlements is greater than 0"
        )
    if "Open settlement queue by rule:" not in open_settlement_queue_read:
        raise ValueError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "detail_read must carry the by-rule open settlement detail"
        )
    if "Settlement queue state:" in open_settlement_queue_read:
        raise ValueError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "detail_read must not nest the settlement queue state wrapper"
        )
    return {
        "roi_complete_settled": int(primary.get("roi_complete_settled", 0) or 0),
        "hit_count": int(primary.get("hit_count", 0) or 0),
        "miss_count": int(primary.get("miss_count", 0) or 0),
        "open_settlements": open_settlements,
        "open_settlement_summary": open_summary,
        "open_settlement_queue_state": open_settlement_queue_state,
        "open_settlement_context": open_settlement_context,
        "open_settlement_queue_read": open_settlement_queue_read,
        "rule_mix_read": str(primary.get("rule_mix_read") or "").strip(),
        "first_read_current": int(first_read.get("current", 0) or 0),
        "first_read_threshold": int(first_read.get("threshold", 30) or 30),
        "latest_context_has_no_bet_recommendations": bool(
            recommendation_context.get("latest_context_has_no_bet_recommendations")
        ),
        "recommendation_context_read": str(recommendation_context.get("read") or "").strip(),
    }


def current_operator_ledger_line(current_evidence: dict[str, object]) -> str:
    context = current_paper_context(current_evidence)
    roi_complete = context["roi_complete_settled"]
    first_current = context["first_read_current"]
    first_threshold = context["first_read_threshold"]
    hits = context["hit_count"]
    misses = context["miss_count"]
    open_rows = context["open_settlements"]
    rule_mix = str(context["rule_mix_read"])
    open_settlement_queue_state = str(context["open_settlement_queue_state"])
    open_settlement_context = str(context["open_settlement_context"])
    open_settlement_queue_read = str(context["open_settlement_queue_read"])
    recommendation_context_read = str(context["recommendation_context_read"])

    result_read = f"{hits} hit(s), {misses} miss(es)"
    if roi_complete == misses and hits == 0:
        result_read = "all misses"

    open_read = (
        f"with {open_rows} open primary settlement row(s) awaiting result/payout evidence"
        if open_rows
        else "with no open primary settlement rows awaiting result/payout evidence"
    )
    queue_state_read = (
        f" Settlement queue state: `{open_settlement_queue_state}`; "
        f"{open_settlement_context}; detail: {open_settlement_queue_read}"
    )
    settlement_queue_boundary = (
        " Open/closed queue state is workflow context, not a bet-ready ticket or forward-performance proof."
    )
    recommendation_read = (
        f" Latest primary recommendation context: {recommendation_context_read}"
        if recommendation_context_read
        else " Latest primary recommendation context is unavailable from the current-evidence bridge."
    )
    return (
        f"- The separate current operator ledger now has {roi_complete} ROI-complete primary-lane settlements "
        f"({rule_mix}), {result_read}, {open_read}; open/closed settlement-queue state is operability metadata only "
        f"and does not change the {first_current}/{first_threshold} ROI-complete first-read count."
        f"{queue_state_read}{recommendation_read}{settlement_queue_boundary} "
        "This frozen replay still cannot prove live profitability or justify a strategy change."
    )


def load_data() -> pd.DataFrame:
    df = pd.read_pickle(CACHE_PATH).copy()
    df["second_prob"] = df["fav_prob"] - df["prob_gap"]
    df["top2_mass"] = df["fav_prob"] + df["second_prob"]
    return df


def normalize_phase7_rule(rule: dict) -> dict:
    return {
        "rule_id": rule["rule_id"],
        "track": rule["track"],
        "k": int(rule["k"]),
        "field_min": int(rule["field_min"]),
        "field_max": int(rule["field_max"]),
        "gap_min": float(rule["gap_min"]),
        "fav_prob_min": float(rule["fav_prob_min"]),
        "condition": rule["condition"],
        "card_min": int(rule["card_min"]),
    }


def build_mask(df: pd.DataFrame, rule: dict) -> np.ndarray:
    mask = (df["track"].to_numpy() == rule["track"])
    mask &= df[f"eligible_{rule['k']}"] .to_numpy(dtype=bool)
    fs = df["fs"].to_numpy(dtype=np.int16)
    mask &= (fs >= rule["field_min"]) & (fs <= rule["field_max"])
    mask &= df["prob_gap"].to_numpy(dtype=np.float64) >= rule["gap_min"]
    mask &= df["fav_prob"].to_numpy(dtype=np.float64) >= rule["fav_prob_min"]

    if rule["condition"] == "fast":
        mask &= df["is_fast"].to_numpy(dtype=bool)

    mask &= df["rnum"].to_numpy(dtype=np.int16) >= rule["card_min"]

    if rule.get("months"):
        mask &= np.isin(df["month"].to_numpy(dtype=np.int16), rule["months"])

    if rule.get("top2_mass_min") is not None:
        mask &= df["top2_mass"].to_numpy(dtype=np.float64) >= float(rule["top2_mass_min"])

    return mask


def evaluate_mask(mask: np.ndarray, hit: np.ndarray, payout: np.ndarray, cost: int) -> dict:
    n = int(mask.sum())
    if n == 0:
        return {
            "races": 0,
            "hits": 0,
            "wagered": 0,
            "returned": 0.0,
            "profit": 0.0,
            "roi": 0.0,
            "hit_rate": 0.0,
        }

    h = mask & hit
    hits = int(h.sum())
    wagered = n * cost
    returned = float(payout[h].sum())
    profit = returned - wagered
    roi = profit / wagered * 100.0 if wagered else 0.0
    hit_rate = hits / n * 100.0
    return {
        "races": n,
        "hits": hits,
        "wagered": wagered,
        "returned": round(returned, 2),
        "profit": round(profit, 2),
        "roi": round(roi, 2),
        "hit_rate": round(hit_rate, 2),
    }


def evaluate_portfolio(df: pd.DataFrame, portfolio_name: str, rules: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    payout = df["payout"].to_numpy(dtype=np.float64)
    year_arr = df["year"].to_numpy(dtype=np.int16)

    summary_rows: list[dict] = []
    yearly_rows: list[dict] = []

    compiled = []
    for rule in rules:
        mask = build_mask(df, rule)
        hit = df[f"hit_{rule['k']}"] .to_numpy(dtype=bool)
        cost = perm(rule["k"] - 1, 3)
        compiled.append({"rule": rule, "mask": mask, "hit": hit, "cost": cost})

    slices = {
        "full": None,
        f"train_2010_{TRAIN_END_YEAR}": year_arr <= TRAIN_END_YEAR,
        f"holdout_{HOLDOUT_YEARS[0]}_{HOLDOUT_YEARS[-1]}": np.isin(year_arr, HOLDOUT_YEARS),
    }
    for y in HOLDOUT_YEARS:
        slices[f"year_{y}"] = year_arr == y

    for item in compiled:
        rule = item["rule"]
        for slice_name, year_mask in slices.items():
            mask = item["mask"] if year_mask is None else (item["mask"] & year_mask)
            stats = evaluate_mask(mask, item["hit"], payout, item["cost"])
            summary_rows.append({
                "portfolio": portfolio_name,
                "level": "rule",
                "name": rule["rule_id"],
                "slice": slice_name,
                "cost_per_race": item["cost"],
                **stats,
            })

    for slice_name, year_mask in slices.items():
        total_wagered = 0
        total_returned = 0.0
        total_hits = 0
        total_races = 0
        for item in compiled:
            mask = item["mask"] if year_mask is None else (item["mask"] & year_mask)
            stats = evaluate_mask(mask, item["hit"], payout, item["cost"])
            total_wagered += stats["wagered"]
            total_returned += stats["returned"]
            total_hits += stats["hits"]
            total_races += stats["races"]
        profit = total_returned - total_wagered
        roi = profit / total_wagered * 100.0 if total_wagered else 0.0
        hit_rate = total_hits / total_races * 100.0 if total_races else 0.0
        summary_rows.append({
            "portfolio": portfolio_name,
            "level": "portfolio",
            "name": portfolio_name,
            "slice": slice_name,
            "cost_per_race": np.nan,
            "races": total_races,
            "hits": total_hits,
            "wagered": total_wagered,
            "returned": round(total_returned, 2),
            "profit": round(profit, 2),
            "roi": round(roi, 2),
            "hit_rate": round(hit_rate, 2),
        })

    for y in sorted(df["year"].unique()):
        total_wagered = 0
        total_returned = 0.0
        total_hits = 0
        total_races = 0
        for item in compiled:
            mask = item["mask"] & (year_arr == y)
            stats = evaluate_mask(mask, item["hit"], payout, item["cost"])
            total_wagered += stats["wagered"]
            total_returned += stats["returned"]
            total_hits += stats["hits"]
            total_races += stats["races"]
        profit = total_returned - total_wagered
        roi = profit / total_wagered * 100.0 if total_wagered else 0.0
        hit_rate = total_hits / total_races * 100.0 if total_races else 0.0
        yearly_rows.append({
            "portfolio": portfolio_name,
            "year": int(y),
            "races": total_races,
            "hits": total_hits,
            "wagered": total_wagered,
            "returned": round(total_returned, 2),
            "profit": round(profit, 2),
            "roi": round(roi, 2),
            "hit_rate": round(hit_rate, 2),
        })

    return pd.DataFrame(summary_rows), pd.DataFrame(yearly_rows)


def build_report(
    summary_df: pd.DataFrame,
    yearly_df: pd.DataFrame,
    *,
    current_evidence: dict[str, object],
    current_evidence_path: Path = CURRENT_EVIDENCE_SUMMARY,
) -> str:
    def row(portfolio: str, slice_name: str) -> pd.Series:
        return summary_df[
            (summary_df["portfolio"] == portfolio)
            & (summary_df["level"] == "portfolio")
            & (summary_df["slice"] == slice_name)
        ].iloc[0]

    p7_hold = row("phase7_live", f"holdout_{HOLDOUT_YEARS[0]}_{HOLDOUT_YEARS[-1]}")
    p8_hold = row("phase8_frozen", f"holdout_{HOLDOUT_YEARS[0]}_{HOLDOUT_YEARS[-1]}")
    p7_train = row("phase7_live", f"train_2010_{TRAIN_END_YEAR}")
    p8_train = row("phase8_frozen", f"train_2010_{TRAIN_END_YEAR}")
    p7_full = row("phase7_live", "full")
    p8_full = row("phase8_frozen", "full")

    lines = [
        "# Frozen Portfolio Evaluation",
        "",
        "This report evaluates already-defined rule portfolios on a later chronological holdout, using the cached major-track race-level dataset.",
        "",
        f"## Current evidence boundary ({current_boundary_date(current_evidence)})",
        "",
        "- Treat this as a **historical frozen replay**, not a live paper-trade ledger and not real-money evidence.",
        f"- Valid evidence scope: `valid_evidence_scope={VALID_EVIDENCE_SCOPE}`.",
        f"- The stricter read is still: **Phase 7 beat Phase 8 on frozen {HOLDOUT_YEARS[0]}-{HOLDOUT_YEARS[-1]} holdout** (`{p7_hold['roi']:+.2f}%` on {int(p7_hold['races'])} races vs. `{p8_hold['roi']:+.2f}%` on {int(p8_hold['races'])} races), so Phase 8 remains shadow/watch rather than a deployment upgrade.",
        "- `OP_DURABLE_K7` remains the safest current paper anchor; `CD_CORE_K8` is the paper companion; `OP_REFINED_K7` and the rest of Phase 8 need forward observation before promotion.",
        current_operator_ledger_line(current_evidence),
        current_operator_read_gate_line(current_evidence),
        "- If quoting the current paper top card from this frozen report context, read `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` first and use the combined `operator_status_context` + `source_freshness` + `operator_read_gate` route; wrapper-refresh, missing-output, freshness routing, or read-gate routing is source-readiness context, not frozen-replay performance evidence.",
        current_rebuild_validation_contract_line(current_evidence),
        "- `BAQ` is not `BEL`; the frozen coverage break should not be patched with unsupported aliasing.",
        "- Re-check this report boundary with `python3 validate_frozen_portfolio_eval_caution.py` after edits.",
        "",
        "## Source reproducibility",
        "",
        "- Generated from exact local source bytes; fingerprints are audit/reproducibility metadata only, not performance evidence.",
        f"- Machine-readable evidence boundary: `frozen_portfolio_eval_metadata.json.evidence_boundary_metadata` marks this as {EVIDENCE_BOUNDARY_METADATA_ROLE}, requires the combined current-operator route before top-card quotation, and is not live-profitability, promotion, anchor-change, Phase 8 promotion, BAQ/BEL substitution, or real-money evidence.",
        current_boundary_source_line(current_evidence),
        current_refresh_action_boundary_line(current_evidence),
        current_operator_read_gate_line(current_evidence),
        current_rebuild_validation_contract_line(current_evidence),
        "- Phase 8 frozen rule definitions are embedded in `evaluate_frozen_portfolios.py`, so the generator fingerprint is part of the source contract.",
        "- Source fingerprints (exact bytes used for this frozen replay; same values are copied into `frozen_portfolio_eval_metadata.json`):",
        *[format_source_fingerprint(label, info) for label, info in source_file_fingerprints(current_evidence_path).items()],
        "",
        "## Why this matters",
        "",
        "- The old residual-model script (`XGBoost/train_test_residual.py`) uses `train_test_split(..., test_size=0.25, shuffle=True)`, which is a random 75/25 split and not deployment-realistic.",
        f"- This report instead checks frozen portfolios on **train = 2010-{TRAIN_END_YEAR}** and **holdout = {HOLDOUT_YEARS[0]}-{HOLDOUT_YEARS[-1]}**.",
        "- This is still not a perfect no-lookahead rule-discovery test, because the rule sets themselves were originally discovered from historical research. It is materially closer to a deployment-style replay than shuffled splits, but it still needs train-only walk-forward context and live paper settlement before any rule promotion or bankroll discussion.",
        "",
        "## Portfolio Summary",
        "",
        "| Portfolio | Full ROI | Train ROI | Holdout ROI | Holdout Profit | Holdout Races | Holdout Hit Rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Phase 7 current-paper rules | {p7_full['roi']:+.2f}% | {p7_train['roi']:+.2f}% | {p7_hold['roi']:+.2f}% | ${p7_hold['profit']:,.2f} | {int(p7_hold['races'])} | {p7_hold['hit_rate']:.2f}% |",
        f"| Phase 8 frozen rules | {p8_full['roi']:+.2f}% | {p8_train['roi']:+.2f}% | {p8_hold['roi']:+.2f}% | ${p8_hold['profit']:,.2f} | {int(p8_hold['races'])} | {p8_hold['hit_rate']:.2f}% |",
        "",
        "## Holdout by Year",
        "",
    ]

    for portfolio in ["phase7_live", "phase8_frozen"]:
        lines.append(f"### {portfolio}")
        lines.append("")
        lines.append("| Year | Races | Wagered | Profit | ROI | Hit Rate |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        sub = yearly_df[(yearly_df["portfolio"] == portfolio) & (yearly_df["year"].isin(HOLDOUT_YEARS))]
        for _, r in sub.iterrows():
            lines.append(
                f"| {int(r['year'])} | {int(r['races'])} | ${r['wagered']:,.0f} | ${r['profit']:,.2f} | {r['roi']:+.2f}% | {r['hit_rate']:.2f}% |"
            )
        lines.append("")

    lines.extend([
        "## Interpretation",
        "",
        f"- The **Phase 7 current-paper rule portfolio** held up best on the later holdout: **{p7_hold['roi']:+.2f}% ROI** on {int(p7_hold['races'])} races, for **${p7_hold['profit']:,.2f}** profit.",
        f"- The **Phase 8 frozen portfolio** also stayed positive on the holdout: **{p8_hold['roi']:+.2f}% ROI** on {int(p8_hold['races'])} races, for **${p8_hold['profit']:,.2f}** profit.",
        "- The BEL rule has **0 holdout races** in 2024-2025 because the later data uses `BAQ` instead of `BEL`, and the current rule mapping explicitly avoids unsupported aliasing.",
        "- This is a more deployment-realistic historical replay than the old shuffled ML split because it preserves chronology and reports historical replay P&L, but it does **not** by itself prove live profitability.",
        "- The main things still missing are a truly clean no-lookahead discovery loop where rules are searched only on prior years, frozen, then tested on the next period, plus ROI-complete live paper-trade settlements.",
        "",
        "## Recommended next evaluation loop",
        "",
        "1. Freeze a candidate search space before looking at the test window.",
        f"2. Use an expanding yearly walk-forward: train on 2010..Y-1, select rules on train only, test on year Y.",
        "3. Track portfolio-level ROI, profit, races, hit rate, and per-year profitability, not just model R² or full-sample ROI.",
        "4. Keep the most recent 12-24 months as a final untouched holdout until the selection logic is frozen.",
        "5. Promote only rules that survive both train-only selection and frozen-holdout evaluation into **live paper trading**, then wait for ROI-complete settled observations before any real-money discussion.",
        "",
    ])

    return "\n".join(lines)


def portfolio_slice(summary_df: pd.DataFrame, portfolio: str, slice_name: str) -> dict[str, object]:
    row = summary_df[
        (summary_df["portfolio"] == portfolio)
        & (summary_df["level"] == "portfolio")
        & (summary_df["slice"] == slice_name)
    ].iloc[0]
    return {
        "races": int(row["races"]),
        "hits": int(row["hits"]),
        "wagered": float(row["wagered"]),
        "returned": float(row["returned"]),
        "profit": float(row["profit"]),
        "roi": float(row["roi"]),
        "hit_rate": float(row["hit_rate"]),
    }


def build_metadata(
    summary_df: pd.DataFrame,
    yearly_df: pd.DataFrame,
    *,
    current_evidence: dict[str, object],
    current_evidence_path: Path = CURRENT_EVIDENCE_SUMMARY,
    summary_output: Path = OUT_SUMMARY,
    yearly_output: Path = OUT_YEARLY,
    report_output: Path = OUT_REPORT,
    metadata_output: Path = OUT_METADATA,
) -> dict[str, object]:
    paper_context = current_paper_context(current_evidence)
    boundary_info = current_boundary_info(current_evidence)
    source_freshness = current_source_freshness_context(current_evidence, current_evidence_path)
    refresh_action = current_refresh_action_boundary_context(current_evidence, current_evidence_path)
    operator_read_gate = current_operator_read_gate_context(current_evidence, current_evidence_path)
    rebuild_validation_contract = current_rebuild_validation_contract_context(
        current_evidence,
        current_evidence_path,
    )
    holdout_slice = f"holdout_{HOLDOUT_YEARS[0]}_{HOLDOUT_YEARS[-1]}"
    phase7_holdout = portfolio_slice(summary_df, "phase7_live", holdout_slice)
    phase8_holdout = portfolio_slice(summary_df, "phase8_frozen", holdout_slice)
    return {
        "artifact": "frozen_portfolio_eval",
        "schema_version": 1,
        "source_scope": SOURCE_SCOPE,
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "evidence_boundary_metadata": frozen_replay_evidence_boundary_metadata(
            phase7_holdout=phase7_holdout,
            phase8_holdout=phase8_holdout,
        ),
        "current_boundary_date": boundary_info["date"],
        "current_boundary_date_source": boundary_info["source"],
        "current_boundary_reference_timezone": boundary_info["timezone"],
        "current_source_freshness": source_freshness,
        "current_refresh_action_boundary": refresh_action,
        "current_operator_read_gate": operator_read_gate,
        "current_evidence_rebuild_validation_contract": rebuild_validation_contract,
        "current_evidence_source": {
            "path": current_evidence_path.name,
            "generated_at": current_evidence.get("generated_at"),
        },
        "current_paper_context": paper_context,
        "holdout_years": HOLDOUT_YEARS,
        "train_end_year": TRAIN_END_YEAR,
        "source_files": source_file_fingerprints(current_evidence_path),
        "outputs": {
            "summary_csv": summary_output.name,
            "yearly_csv": yearly_output.name,
            "report_md": report_output.name,
            "metadata_json": metadata_output.name,
        },
        "holdout_summary": {
            "phase7_live": phase7_holdout,
            "phase8_frozen": phase8_holdout,
        },
        "row_counts": {
            "summary_csv": int(len(summary_df)),
            "yearly_csv": int(len(yearly_df)),
        },
        "non_goals": [
            "not a live paper-trade ledger",
            "not live-profitability proof",
            "not promotion-ready evidence",
            "not real-money evidence",
        ],
    }


def parse_args() -> object:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--current-evidence-json", type=Path, default=CURRENT_EVIDENCE_SUMMARY)
    parser.add_argument("--summary-output", type=Path, default=OUT_SUMMARY)
    parser.add_argument("--yearly-output", type=Path, default=OUT_YEARLY)
    parser.add_argument("--report-output", type=Path, default=OUT_REPORT)
    parser.add_argument("--metadata-output", type=Path, default=OUT_METADATA)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    current_evidence = load_current_evidence_summary(args.current_evidence_json)

    df = load_data()

    with PHASE7_RULES_PATH.open() as f:
        phase7_rules = [normalize_phase7_rule(r) for r in json.load(f)["rules"]]

    phase7_summary, phase7_yearly = evaluate_portfolio(df, "phase7_live", phase7_rules)
    phase8_summary, phase8_yearly = evaluate_portfolio(df, "phase8_frozen", PHASE8_FROZEN_RULES)

    summary_df = pd.concat([phase7_summary, phase8_summary], ignore_index=True)
    yearly_df = pd.concat([phase7_yearly, phase8_yearly], ignore_index=True)

    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.yearly_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.metadata_output.parent.mkdir(parents=True, exist_ok=True)

    args.summary_output.write_text(summary_df.to_csv(index=False), encoding="utf-8")
    args.yearly_output.write_text(yearly_df.to_csv(index=False), encoding="utf-8")
    args.report_output.write_text(
        build_report(
            summary_df,
            yearly_df,
            current_evidence=current_evidence,
            current_evidence_path=args.current_evidence_json,
        ),
        encoding="utf-8",
    )
    args.metadata_output.write_text(
        json.dumps(
            build_metadata(
                summary_df,
                yearly_df,
                current_evidence=current_evidence,
                current_evidence_path=args.current_evidence_json,
                summary_output=args.summary_output,
                yearly_output=args.yearly_output,
                report_output=args.report_output,
                metadata_output=args.metadata_output,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print("Saved:")
    print(f"  {args.summary_output.name}")
    print(f"  {args.yearly_output.name}")
    print(f"  {args.report_output.name}")
    print(f"  {args.metadata_output.name}")

    hold_slice = f"holdout_{HOLDOUT_YEARS[0]}_{HOLDOUT_YEARS[-1]}"
    for portfolio in ["phase7_live", "phase8_frozen"]:
        row = summary_df[
            (summary_df["portfolio"] == portfolio)
            & (summary_df["level"] == "portfolio")
            & (summary_df["slice"] == hold_slice)
        ].iloc[0]
        print(
            f"{portfolio}: holdout ROI {row['roi']:+.2f}% | "
            f"profit ${row['profit']:,.2f} | races {int(row['races'])}"
        )


if __name__ == "__main__":
    main()
