#!/usr/bin/env python3
"""
Fast honest comparison harness for the main superfecta approaches.

Purpose:
- Compare the current approaches without rerunning a wide search.
- Keep the comparison anchored to the frozen honest standard.
- Put 2024-2025 holdout, walk-forward context, and OP-focused options in one place.

Usage:
    python3 compare_main_approaches.py

Outputs:
    - compare_main_approaches.csv
    - compare_main_approaches.md
    - compare_main_approaches.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime
from math import perm
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
CACHE_PATH = BASE / "phase5_race_cache.pkl"
PHASE7_RULES_PATH = BASE / "phase7_live_rules.json"
WF_FOLDS_PATH = BASE / "walk_forward_validation_folds.csv"
WF_RULES_PATH = BASE / "walk_forward_validation_rules.csv"
SCORECARD_CSV = BASE / "forward_evidence_scorecard.csv"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
EXPECTED_SCORECARD_AUDIT_ROUTE = {
    "markdown_path": "SCORECARD_RANKING_CONTRACT_AUDIT.md",
    "json_path": "scorecard_ranking_contract_audit.json",
    "validator_command": "python3 validate_scorecard_ranking_contract_audit.py",
    "gate_floor_source": "forward_evidence_scorecard.json:decision_gate_minimums",
    "valid_use": "navigation route for scorecard gate/ranking/CI-only/timezone/no-BAQ synchronization checks",
}
EXPECTED_SCORECARD_AUDIT_GATE_FLOOR_SNAPSHOT = {
    "anchor_displacement_min_roi_complete_settled_observations": 30,
    "phase8_promotion_review_min_roi_complete_settled_observations": 20,
    "real_money_discussion_min_total_settled_observations_with_usable_roi": 100,
    "real_money_no_baq_as_bel_required": True,
}
EXPECTED_REBUILD_VALIDATION_CONTRACT = {
    "rebuild_command": "python3 current_evidence_summary.py",
    "prerequisite_rebuild_command": "python3 paper_trade_settlement_audit.py",
    "direct_validation_command": "python3 validate_current_evidence_summary.py",
}
EXPECTED_REBUILD_VALIDATION_ORDER_COMMANDS = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]
REQUIRED_SCORECARD_AUDIT_ROUTE_FLAGS = [
    "artifacts_present",
    "not_forward_performance_evidence",
    "not_settled_roi_evidence",
    "not_promotion_readiness_evidence",
    "not_live_profitability_evidence",
    "not_bankroll_guidance",
    "not_real_money_evidence",
]
REQUIRED_SCORECARD_AUDIT_ROUTE_READ_PHRASES = [
    "SCORECARD_RANKING_CONTRACT_AUDIT.md",
    "scorecard_ranking_contract_audit.json",
    "python3 validate_scorecard_ranking_contract_audit.py",
    "30/20/100 gate floors",
    "tier-first ranking",
    "OP_REFINED CI-only support context",
    "generated-at timezone provenance",
    "no-BAQ-as-BEL prerequisite",
]
REQUIRED_REBUILD_VALIDATION_CONTRACT_FLAGS = [
    "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
    "green_checks_are_reproducibility_metadata_only",
    "requires_source_consistency_before_quoting_current_totals",
    "requires_source_freshness_before_right_now_instruction_use",
    "upstream_refresh_order_is_provenance_metadata_only",
    "not_settled_roi_or_real_money_evidence",
]
REQUIRED_SOURCE_FRESHNESS_TEXT_FIELDS = [
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

OUT_CSV = BASE / "compare_main_approaches.csv"
OUT_MD = BASE / "compare_main_approaches.md"
OUT_JSON = BASE / "compare_main_approaches.json"

REQUIRED_SCORECARD_RULE_IDS = (
    "OP_DURABLE_K7",
    "CD_CORE_K8",
    "OP_REFINED_K7",
    "BEL_BROAD1_K7",
    "DMR_FALL_K7",
    "KEE_K9",
    "SA_K9",
)
REQUIRED_SCORECARD_COLUMNS = {
    "rule_id",
    "tier",
    "holdout_2024_roi",
    "holdout_2024_races",
    "holdout_2025_roi",
    "holdout_2025_races",
    "wf_selected_count",
    "wf_total_folds",
    "action_now",
    "current_role",
    "deployment_reason",
}
REQUIRED_WF_FOLD_COLUMNS = {
    "test_year",
    "test_races",
    "test_hits",
    "test_wagered",
    "test_profit",
    "test_roi",
}
REQUIRED_WF_RULE_COLUMNS = {
    "test_year",
    "rule_id",
    "qualifies",
    "selection_score",
    "train_races",
    "train_roi",
    "test_races",
    "test_hits",
    "test_wagered",
    "test_profit",
    "test_roi",
}
REQUIRED_OP_SWITCH_RULES = ("OP_DURABLE_K7", "OP_REFINED_K7")

DEPLOYMENT_POSTURE = {
    "phase7_live_portfolio": "PAPER NOW",
    "phase8_frozen_portfolio": "SHADOW ONLY",
    "op_durable_only": "ANCHOR",
    "op_refined_only": "WATCH",
    "op_train_switch": "BENCHMARK ONLY",
    "train_only_selector": "BENCHMARK ONLY",
}

DEFAULT_HOLDOUT_YEARS = [2024, 2025]

SOURCE_PATHS = {
    "phase5_race_cache": CACHE_PATH,
    "phase7_live_rules": PHASE7_RULES_PATH,
    "walk_forward_folds": WF_FOLDS_PATH,
    "walk_forward_rules": WF_RULES_PATH,
    "forward_evidence_scorecard": SCORECARD_CSV,
    "forward_evidence_scorecard_json": SCORECARD_JSON,
    "current_evidence_summary_json": CURRENT_EVIDENCE_JSON,
    "cross_family_decision_card": BASE / "cross_family_decision_card.csv",
    "backtest_summary": BASE / "backtest_summary.csv",
    "ab_downstream_comparison_results": BASE / "ab_downstream_comparison_results.json",
}

EVIDENCE_BOUNDARY = (
    "main-comparison render/sidecar only; source fingerprints, clean rebuilds, and validator passes are "
    "reproducibility metadata, not live paper-trade evidence, settled ROI, live profitability, "
    "promotion readiness, or real-money evidence; current top-card/operator routing belongs in "
    "CURRENT_EVIDENCE_SUMMARY.md / current_evidence_summary.json via the combined "
    "operator_status_context/source_freshness/operator_read_gate route"
)
MACHINE_READABLE_EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "main approach comparison bundle",
    "valid_evidence_scope": "frozen_main_approach_comparison_only",
    "source_scope": [
        "phase5_race_cache.pkl",
        "phase7_live_rules.json",
        "walk_forward_validation_folds.csv",
        "walk_forward_validation_rules.csv",
        "forward_evidence_scorecard.csv",
        "forward_evidence_scorecard.json",
        "current_evidence_summary.json",
        "cross_family_decision_card.csv",
        "backtest_summary.csv",
        "ab_downstream_comparison_results.json",
    ],
    "valid_use": "frozen 2024-2025 holdout, train-only walk-forward, method-family, and paper-lane posture comparison",
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
        "source_consistency",
        "operator_read_gate",
    ],
    "current_operator_routing_requires_combined_route": True,
    "current_operator_routing_is_source_readiness_not_performance": True,
    "current_operator_boundary_snapshot_is_context_only": True,
    "source_fingerprints_are_reproducibility_metadata_only": True,
    "row_identical_source_byte_drift_is_provenance_only": True,
    "decision_gates_are_forward_observation_requirements_not_current_evidence": True,
    "stronger_forward_confidence_requires": [
        "qualifying live paper signals",
        "ROI-complete settled paper rows",
        "settlement-quality checks",
        "other real forward observations",
    ],
    "non_goals": [
        "do not use the main comparison rebuild as settled ROI",
        "do not promote OP_REFINED_K7 or Phase 8 from this artifact",
        "do not reopen current odds-only XGBoost from this artifact",
        "do not treat Harville benchmark-only output as a live approach",
        "do not substitute BAQ for BEL",
        "do not discuss real-money scaling from this artifact",
        "do not quote current PAPER_TRADE_NOW instructions from this artifact; use the combined operator_status_context/source_freshness/operator_read_gate route from CURRENT_EVIDENCE_SUMMARY instead",
        "do not treat the copied current-evidence operator snapshot as settled ROI or bet readiness",
    ],
}

def require_scorecard_gate_dict(payload: dict[str, Any], gate_name: str, scorecard_json: Path) -> dict[str, Any]:
    gate_minimums = payload.get("decision_gate_minimums")
    if not isinstance(gate_minimums, dict):
        raise ValueError(f"{scorecard_json.name} is missing decision_gate_minimums")
    gate = gate_minimums.get(gate_name)
    if not isinstance(gate, dict):
        raise ValueError(f"{scorecard_json.name} is missing decision_gate_minimums.{gate_name}")
    return gate


def require_scorecard_positive_int(gate: dict[str, Any], key: str, dotted_path: str, scorecard_json: Path) -> int:
    value = gate.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{scorecard_json.name} JSON path must be a positive integer: {dotted_path}")
    return value


def require_scorecard_str_list(gate: dict[str, Any], key: str, dotted_path: str, scorecard_json: Path) -> list[str]:
    value = gate.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{scorecard_json.name} JSON path must be a string list: {dotted_path}")
    return [item.strip() for item in value]


def load_scorecard_ci_only_promotion_diagnostic(
    scorecard_json: Path,
    candidate_rule: str,
    anchor_rule: str,
) -> dict[str, Any]:
    scorecard_json = Path(scorecard_json)
    payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
    diagnostics = payload.get("ci_only_promotion_diagnostics")
    if not isinstance(diagnostics, dict):
        raise ValueError(f"{scorecard_json.name} is missing ci_only_promotion_diagnostics")
    diagnostic = diagnostics.get(candidate_rule)
    if not isinstance(diagnostic, dict):
        raise ValueError(f"{scorecard_json.name} is missing ci_only_promotion_diagnostics.{candidate_rule}")
    if diagnostic.get("candidate_rule_id") != candidate_rule:
        raise ValueError(
            f"{scorecard_json.name} ci_only_promotion_diagnostics.{candidate_rule}.candidate_rule_id "
            f"must equal {candidate_rule}"
        )
    if diagnostic.get("current_anchor_rule_id") != anchor_rule:
        raise ValueError(
            f"{scorecard_json.name} ci_only_promotion_diagnostics.{candidate_rule}.current_anchor_rule_id "
            f"must equal {anchor_rule}"
        )
    if diagnostic.get("positive_ci_lower_bound_is_support_context") is not True:
        raise ValueError(
            f"{scorecard_json.name} ci_only_promotion_diagnostics.{candidate_rule} must mark "
            "positive_ci_lower_bound_is_support_context=true"
        )
    if diagnostic.get("ci_only_promotion_allowed") is not False:
        raise ValueError(
            f"{scorecard_json.name} ci_only_promotion_diagnostics.{candidate_rule} must mark "
            "ci_only_promotion_allowed=false"
        )
    require_scorecard_str_list(
        diagnostic,
        "why_not",
        f"ci_only_promotion_diagnostics.{candidate_rule}.why_not",
        scorecard_json,
    )
    required_before_review = diagnostic.get("required_before_review")
    if not isinstance(required_before_review, dict) or not all(
        isinstance(required_before_review.get(key), str) and required_before_review.get(key, "").strip()
        for key in ("phase8_promotion_review", "anchor_displacement")
    ):
        raise ValueError(
            f"{scorecard_json.name} JSON path must include string review requirements: "
            f"ci_only_promotion_diagnostics.{candidate_rule}.required_before_review"
        )
    require_scorecard_str_list(
        diagnostic,
        "does_not_count",
        f"ci_only_promotion_diagnostics.{candidate_rule}.does_not_count",
        scorecard_json,
    )
    return json.loads(json.dumps(diagnostic))


def load_decision_change_gate_minimums(scorecard_json: Path = SCORECARD_JSON) -> dict[str, Any]:
    scorecard_json = Path(scorecard_json)
    payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
    phase8_gate = require_scorecard_gate_dict(payload, "phase8_promotion_review", scorecard_json)
    anchor_gate = require_scorecard_gate_dict(payload, "anchor_displacement", scorecard_json)
    real_money_gate = require_scorecard_gate_dict(payload, "real_money_discussion", scorecard_json)

    phase8_min = require_scorecard_positive_int(
        phase8_gate,
        "min_roi_complete_settled_observations",
        "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
        scorecard_json,
    )
    anchor_min = require_scorecard_positive_int(
        anchor_gate,
        "min_roi_complete_settled_observations",
        "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
        scorecard_json,
    )
    real_money_min = require_scorecard_positive_int(
        real_money_gate,
        "min_total_settled_observations_with_usable_roi",
        "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
        scorecard_json,
    )
    real_money_requires = require_scorecard_str_list(
        real_money_gate,
        "also_requires",
        "decision_gate_minimums.real_money_discussion.also_requires",
        scorecard_json,
    )
    if NO_BAQ_AS_BEL_PREREQUISITE not in real_money_requires:
        raise ValueError(
            f"{scorecard_json.name} JSON path must include {NO_BAQ_AS_BEL_PREREQUISITE}: "
            "decision_gate_minimums.real_money_discussion.also_requires"
        )

    return {
        "phase8_promotion_review": {
            "minimum_roi_complete_settled_observations": phase8_min,
            "threshold_source": f"{scorecard_json.name}:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
            "observation_scope": "future settled shadow ledger rows for the same candidate with complete ROI coverage",
            "gate_role": "opens promotion-review discussion only; does not displace OP_DURABLE_K7 as anchor by itself",
            "also_requires": [
                "cleaner split-aware forward read than the current anchor/companion pair",
                "cleaner walk-forward/frozen-standard support than the current anchor/companion pair",
            ],
        },
        "anchor_displacement": {
            "minimum_roi_complete_same_candidate_observations": anchor_min,
            "threshold_source": f"{scorecard_json.name}:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
            "observation_scope": "future settled same-candidate paper ledger rows with complete ROI coverage",
            "gate_role": "minimum before any discussion of replacing OP_DURABLE_K7 as safest anchor",
            "also_requires": [
                "cleaner split-aware forward read than OP_DURABLE_K7",
                "walk-forward/frozen-standard support that clearly beats OP_DURABLE_K7's larger sample",
            ],
        },
        "real_money_discussion": {
            "minimum_total_settled_roi_complete_observations": real_money_min,
            "threshold_source": f"{scorecard_json.name}:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
            "observation_scope": "settled paper-trade ledger observations with usable return/cost coverage",
            "gate_role": "minimum before any real-money confidence or bankroll discussion",
            "also_requires": [
                "hit-rate and ROI inside the expected range",
                "concentration checks",
                "payout sanity checks",
                NO_BAQ_AS_BEL_PREREQUISITE,
            ],
        },
    }

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


def file_fingerprint(path: Path) -> dict[str, Any]:
    resolved = Path(path)
    data = resolved.read_bytes()
    return {
        "path": resolved.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def source_file_fingerprints(source_paths: Optional[dict[str, Path]] = None) -> dict[str, dict[str, Any]]:
    merged_paths = dict(SOURCE_PATHS)
    if source_paths:
        merged_paths.update({label: Path(path) for label, path in source_paths.items()})
    return {label: file_fingerprint(path) for label, path in merged_paths.items()}


def format_source_fingerprint_row(label: str, fingerprint: dict[str, Any]) -> str:
    return f"| {label} | `{fingerprint['path']}` | {fingerprint['bytes']} | `{fingerprint['sha256']}` |"


def load_scorecard_ranking_contract(scorecard_json: Path = SCORECARD_JSON) -> dict[str, Any]:
    payload = json.loads(Path(scorecard_json).read_text(encoding="utf-8"))
    contract = payload.get("ranking_contract")
    if not isinstance(contract, dict):
        raise ValueError(f"{Path(scorecard_json).name} is missing ranking_contract")
    if contract.get("rank_is_tier_first_decision_order") is not True:
        raise ValueError(f"{Path(scorecard_json).name} ranking_contract no longer marks rank_is_tier_first_decision_order=true")
    if contract.get("forward_trust_is_secondary_within_tier") is not True:
        raise ValueError(f"{Path(scorecard_json).name} ranking_contract no longer marks forward_trust_is_secondary_within_tier=true")
    if contract.get("raw_score_is_not_an_automatic_deployment_instruction") is not True:
        raise ValueError(f"{Path(scorecard_json).name} ranking_contract no longer says raw score is not an automatic deployment instruction")
    if "CD_CORE_K8 ranks ahead of OP_REFINED_K7" not in str(contract.get("known_rank_override") or ""):
        raise ValueError(f"{Path(scorecard_json).name} ranking_contract no longer preserves the CD_CORE_K8 over OP_REFINED_K7 tier-first override")
    return dict(contract)


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


def require_nonblank_fields(source_name: str, payload: dict[str, Any], dotted_path: str, fields: list[str]) -> None:
    missing = [
        field
        for field in fields
        if not isinstance(payload.get(field), str) or not str(payload.get(field)).strip()
    ]
    if missing:
        raise ValueError(f"{source_name} {dotted_path} missing fields: {', '.join(missing)}")


def require_bool_fields(source_name: str, payload: dict[str, Any], dotted_path: str, fields: list[str]) -> None:
    missing = [field for field in fields if not isinstance(payload.get(field), bool)]
    if missing:
        raise ValueError(f"{source_name} {dotted_path} missing fields: {', '.join(missing)}")


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
    if (
        int(primary.get("current_rows", -1)) != 6
        or int(primary.get("threshold", -1)) != 30
        or primary.get("ready") is not False
    ):
        raise ValueError(f"{source_name} decision_gate_progress primary_first_read must publish uncleared 6/30 progress")
    if (
        anchor.get("candidate_rule_id") != "OP_DURABLE_K7"
        or int(anchor.get("current_rows", -1)) != 0
        or int(anchor.get("threshold", -1)) != 30
        or anchor.get("companion_rows_count_as_anchor_evidence") is not False
    ):
        raise ValueError(f"{source_name} decision_gate_progress must publish OP_DURABLE_K7 same-candidate 0/30 progress")
    if (
        int(phase8.get("weakest_current_rows", -1)) != 0
        or int(phase8.get("threshold_per_candidate", -1)) != 20
        or phase8.get("ready") is not False
    ):
        raise ValueError(f"{source_name} decision_gate_progress must publish Phase 8 weakest 0/20 progress")
    if (
        int(real_money.get("current_primary_roi_complete_rows", -1)) != 6
        or int(real_money.get("threshold", -1)) != 100
        or real_money.get("ready") is not False
    ):
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
    return json.loads(json.dumps(progress))


def validate_operator_read_gate(payload: dict[str, Any], source_name: str) -> dict[str, Any]:
    gate = payload.get("operator_read_gate")
    if not isinstance(gate, dict):
        raise ValueError(f"{source_name} is missing operator_read_gate")
    require_nonblank_fields(
        source_name,
        gate,
        "operator_read_gate",
        REQUIRED_OPERATOR_READ_GATE_TEXT_FIELDS,
    )
    require_bool_fields(
        source_name,
        gate,
        "operator_read_gate",
        REQUIRED_OPERATOR_READ_GATE_BOOL_FIELDS,
    )
    gate_status = gate.get("gate_status")
    if gate_status not in {"refresh_required_before_evidence_read", "current_operator_routing_context_only"}:
        raise ValueError(
            f"{source_name} operator_read_gate.gate_status must be a known instruction/evidence-read state"
        )
    if gate.get("valid_use") != "operator instruction/evidence-read gating only":
        raise ValueError(f"{source_name} operator_read_gate.valid_use drifted")

    for flag in (
        "not_forward_performance_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_real_money_evidence",
    ):
        if gate.get(flag) is not True:
            raise ValueError(f"{source_name} operator_read_gate must mark {flag}=true")
    for flag in (
        "current_top_card_counts_as_no_target_evidence",
        "current_top_card_counts_as_clean_empty_evidence",
        "current_top_card_counts_as_bet_readiness_evidence",
        "current_top_card_counts_as_settled_roi_evidence",
    ):
        if gate.get(flag) is not False:
            raise ValueError(f"{source_name} operator_read_gate must mark {flag}=false")

    read = str(gate.get("read") or "")
    if gate_status == "refresh_required_before_evidence_read":
        if gate.get("recommended_command") != "./run_daily_portfolio_observation.sh":
            raise ValueError(f"{source_name} operator_read_gate must recommend ./run_daily_portfolio_observation.sh")
        required_refresh_flags = (
            "requires_refresh_before_evidence_read",
            "has_wrapper_refresh_action",
        )
        false_refresh_flags = [flag for flag in required_refresh_flags if gate.get(flag) is not True]
        if false_refresh_flags:
            raise ValueError(f"{source_name} operator_read_gate must mark {', '.join(false_refresh_flags)}=true")
        if not any(
            gate.get(flag) is True
            for flag in (
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
        unexpected_refresh_flags = (
            "requires_refresh_before_evidence_read",
            "requires_source_freshness_refresh",
            "has_api_access_failure_context",
            "has_scanner_failure_boundary",
            "has_stale_cache_fallback_context",
            "has_missing_scan_output_artifact_issue",
            "has_wrapper_refresh_action",
            "has_issue_bucket",
        )
        true_refresh_flags = [flag for flag in unexpected_refresh_flags if gate.get(flag) is not False]
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


def validate_scorecard_audit_route(payload: dict[str, Any], source_name: str) -> dict[str, Any]:
    route = payload.get("scorecard_audit_route")
    if not isinstance(route, dict):
        raise ValueError(f"{source_name} is missing scorecard_audit_route")
    for key, expected in EXPECTED_SCORECARD_AUDIT_ROUTE.items():
        if route.get(key) != expected:
            raise ValueError(f"{source_name} scorecard_audit_route.{key} drifted")
    if route.get("gate_floor_snapshot") != EXPECTED_SCORECARD_AUDIT_GATE_FLOOR_SNAPSHOT:
        raise ValueError(f"{source_name} scorecard_audit_route.gate_floor_snapshot drifted")
    for flag in REQUIRED_SCORECARD_AUDIT_ROUTE_FLAGS:
        if route.get(flag) is not True:
            raise ValueError(f"{source_name} scorecard_audit_route.{flag} must be true")
    route_read = str(route.get("route_read") or "")
    for phrase in REQUIRED_SCORECARD_AUDIT_ROUTE_READ_PHRASES:
        if phrase not in route_read:
            raise ValueError(f"{source_name} scorecard_audit_route.route_read missing {phrase!r}")
    return json.loads(json.dumps(route))


def validate_rebuild_validation_contract(payload: dict[str, Any], source_name: str) -> dict[str, Any]:
    contract = payload.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise ValueError(f"{source_name} is missing rebuild_validation_contract")
    for key, expected in EXPECTED_REBUILD_VALIDATION_CONTRACT.items():
        if contract.get(key) != expected:
            raise ValueError(f"{source_name} rebuild_validation_contract.{key} drifted")
    upstream_order = contract.get("upstream_refresh_order")
    if not isinstance(upstream_order, list) or len(upstream_order) != len(EXPECTED_REBUILD_VALIDATION_ORDER_COMMANDS):
        raise ValueError(f"{source_name} rebuild_validation_contract.upstream_refresh_order drifted")
    upstream_commands: list[str] = []
    for expected_index, row in enumerate(upstream_order, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"{source_name} rebuild_validation_contract.upstream_refresh_order row drifted")
        if row.get("order") != expected_index:
            raise ValueError(f"{source_name} rebuild_validation_contract.upstream_refresh_order order drifted")
        command = str(row.get("command") or "")
        reason = str(row.get("reason") or "")
        if not command or not reason:
            raise ValueError(f"{source_name} rebuild_validation_contract.upstream_refresh_order row is incomplete")
        upstream_commands.append(command)
    if upstream_commands != EXPECTED_REBUILD_VALIDATION_ORDER_COMMANDS:
        raise ValueError(f"{source_name} rebuild_validation_contract.upstream_refresh_order command drifted")
    for flag in REQUIRED_REBUILD_VALIDATION_CONTRACT_FLAGS:
        if contract.get(flag) is not True:
            raise ValueError(f"{source_name} rebuild_validation_contract.{flag} must be true")
    valid_use = str(contract.get("upstream_refresh_order_valid_use") or "")
    for phrase in ("current bridge provenance", "scorecard/rules/ledger byte changes"):
        if phrase not in valid_use:
            raise ValueError(f"{source_name} rebuild_validation_contract.upstream_refresh_order_valid_use drifted")
    return json.loads(json.dumps(contract))


def load_current_operator_boundary(current_evidence_json: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    current_evidence_json = Path(current_evidence_json)
    source_name = current_evidence_json.name
    payload = json.loads(current_evidence_json.read_text(encoding="utf-8"))
    if not has_timezone_aware_timestamp(payload.get("generated_at")):
        raise ValueError(f"{source_name} generated_at must be timezone-aware ISO provenance metadata")
    decision_gate_progress = validate_decision_gate_progress(payload, source_name)
    operator_read_gate = validate_operator_read_gate(payload, source_name)
    scorecard_audit_route = validate_scorecard_audit_route(payload, source_name)
    rebuild_validation_contract = validate_rebuild_validation_contract(payload, source_name)

    def require_dict(value: Any, path: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError(f"{source_name} missing {path}")
        return value

    source_freshness = require_dict(payload.get("source_freshness"), "source_freshness")
    require_nonblank_fields(
        source_name,
        source_freshness,
        "source_freshness",
        REQUIRED_SOURCE_FRESHNESS_TEXT_FIELDS,
    )
    refresh_action_boundary = require_dict(
        source_freshness.get("refresh_action_boundary"),
        "source_freshness.refresh_action_boundary",
    )
    require_nonblank_fields(
        source_name,
        refresh_action_boundary,
        "source_freshness.refresh_action_boundary",
        REQUIRED_REFRESH_ACTION_BOUNDARY_TEXT_FIELDS,
    )
    require_bool_fields(
        source_name,
        refresh_action_boundary,
        "source_freshness.refresh_action_boundary",
        REQUIRED_REFRESH_ACTION_BOUNDARY_BOOL_FIELDS,
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
    source_consistency = require_dict(payload.get("source_consistency"), "source_consistency")
    current_paper = require_dict(payload.get("current_paper_status"), "current_paper_status")
    primary = require_dict(current_paper.get("primary"), "current_paper_status.primary")
    recommendation_context = require_dict(
        primary.get("recommendation_context"),
        "current_paper_status.primary.recommendation_context",
    )
    operator_context = require_dict(
        current_paper.get("operator_status_context"),
        "current_paper_status.operator_status_context",
    )
    first_read = require_dict(primary.get("first_read"), "current_paper_status.primary.first_read")
    open_queue = require_dict(
        primary.get("open_settlement_queue_by_rule"),
        "current_paper_status.primary.open_settlement_queue_by_rule",
    )
    primary_rule_progress_raw = primary.get("rule_progress")
    if not isinstance(primary_rule_progress_raw, list):
        raise ValueError(f"{source_name} missing current_paper_status.primary.rule_progress")
    primary_rule_progress = primary_rule_progress_raw
    primary_rule_counts = {
        str(row.get("rule_id")): int(row.get("roi_complete_settled_rows") or 0)
        for row in primary_rule_progress
        if isinstance(row, dict) and row.get("rule_id")
    }
    op_anchor_rows = primary_rule_counts.get("OP_DURABLE_K7", 0)
    cd_companion_rows = primary_rule_counts.get("CD_CORE_K8", 0)
    open_settlement_rows_raw = primary.get("open_settlements", 0)
    if isinstance(open_settlement_rows_raw, bool):
        raise ValueError(f"{source_name} current_paper_status.primary.open_settlements must be an integer")
    try:
        open_settlement_rows = int(open_settlement_rows_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{source_name} current_paper_status.primary.open_settlements must be an integer") from exc
    if open_settlement_rows < 0:
        raise ValueError(f"{source_name} current_paper_status.primary.open_settlements cannot be negative")
    open_settlement_summary = str(primary.get("open_settlement_summary") or "").strip()
    open_settlement_queue_state = str(open_queue.get("open_settlement_queue_state") or "").strip()
    open_settlement_context = str(open_queue.get("open_settlement_context") or "").strip()
    open_settlement_queue_read = str(open_queue.get("detail_read") or "").strip()
    expected_open_settlement_queue_state = "closed" if open_settlement_rows == 0 else "open"
    if open_settlement_queue_state not in {"closed", "open"}:
        raise ValueError(
            f"{source_name} current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_queue_state must be closed or open"
        )
    if open_settlement_queue_state != expected_open_settlement_queue_state:
        raise ValueError(
            f"{source_name} current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_queue_state must match current_paper_status.primary.open_settlements"
        )
    if not open_settlement_context:
        raise ValueError(
            f"{source_name} current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_context must be populated"
        )
    if open_settlement_rows == 0 and open_settlement_context != "no open primary settlement rows":
        raise ValueError(
            f"{source_name} current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_context must read no open primary settlement rows when open_settlements is 0"
        )
    if open_settlement_rows > 0 and open_settlement_context.lower() in {
        "none",
        "no open primary settlement rows",
    }:
        raise ValueError(
            f"{source_name} current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_context must identify open rows when open_settlements is greater than 0"
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

    return {
        "source_path": current_evidence_json.name,
        "generated_at": payload.get("generated_at"),
        "source_consistency_overall_match": bool(source_consistency.get("overall_match")),
        "decision_gate_progress": decision_gate_progress,
        "operator_read_gate": operator_read_gate,
        "scorecard_audit_route": scorecard_audit_route,
        "rebuild_validation_contract": rebuild_validation_contract,
        "source_freshness_generated_reference_date": source_freshness.get("generated_reference_date"),
        "source_freshness_generated_reference_timezone": source_freshness.get("generated_reference_timezone"),
        "source_freshness_staleness_comparison_source": source_freshness.get("staleness_comparison_source"),
        "source_freshness_staleness_comparison_date": source_freshness.get("staleness_comparison_date"),
        "right_now_as_of_date": source_freshness.get("right_now_as_of_date"),
        "right_now_run_date": source_freshness.get("right_now_run_date"),
        "right_now_freshness_state": source_freshness.get("right_now_freshness_state"),
        "requires_refresh_before_right_now_use": bool(source_freshness.get("requires_refresh_before_right_now_use")),
        "source_freshness_read": source_freshness.get("read"),
        "refresh_action_command": refresh_action_boundary.get("command"),
        "refresh_required_before_right_now_instruction_use": bool(
            refresh_action_boundary.get("required_before_right_now_instruction_use")
        ),
        "refresh_source_action_counts_as_current_instruction_before_refresh": bool(
            refresh_action_boundary.get("source_action_counts_as_current_instruction_before_refresh")
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
        "missing_or_invalid_artifact_counts_as_clean_quiet_day": bool(
            refresh_action_boundary.get("missing_or_invalid_artifact_counts_as_clean_quiet_day")
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
        "refresh_boundary_not_real_money_evidence": bool(
            refresh_action_boundary.get("not_real_money_evidence")
        ),
        "best_action_headline": operator_context.get("best_action_headline"),
        "best_action_command": operator_context.get("best_action_command"),
        "best_action_why": operator_context.get("best_action_why"),
        "open_settlement_summary": open_settlement_summary,
        "open_settlement_context": open_settlement_context,
        "open_settlement_queue_state": open_settlement_queue_state,
        "open_settlement_queue_read": open_settlement_queue_read,
        "open_settlement_rows": open_settlement_rows,
        "roi_complete_primary_rows": int(primary.get("roi_complete_settled") or 0),
        "first_read_threshold": int(first_read.get("threshold") or 0),
        "first_read_remaining": int(first_read.get("remaining") or 0),
        "op_anchor_roi_complete_rows": op_anchor_rows,
        "cd_companion_roi_complete_rows": cd_companion_rows,
        "primary_rule_mix_read": primary.get("rule_mix_read"),
        "current_settled_context_is_cd_only": bool(op_anchor_rows == 0 and cd_companion_rows > 0),
        "latest_context_has_no_bet_recommendations": bool(
            recommendation_context.get("latest_context_has_no_bet_recommendations")
        ),
        "latest_context_has_bet_ready_language": bool(
            recommendation_context.get("latest_context_has_bet_ready_language")
        ),
        "latest_context_has_no_qualifying_races": "no qualifying races"
        in str(recommendation_context.get("latest_run_context") or recommendation_context.get("read") or "").lower(),
        "latest_run_context": recommendation_context.get("latest_run_context"),
        "recommendation_context_read": recommendation_context.get("read"),
        "not_forward_performance_evidence": True,
        "not_bet_readiness_evidence_by_itself": True,
    }


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return None if np.isnan(value) else float(value)
    if pd.isna(value) and not isinstance(value, (str, bytes)):
        return None
    return value


def validate_holdout_years(holdout_years: list[int]) -> list[int]:
    normalized = sorted(set(int(y) for y in holdout_years))
    if normalized != DEFAULT_HOLDOUT_YEARS:
        raise ValueError(
            "compare_main_approaches.py is intentionally locked to the frozen 2024-2025 holdout standard; "
            f"received {normalized}. Use the default holdout window so the saved comparison surface stays report-safe."
        )
    return normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fast honest method comparison")
    parser.add_argument(
        "--holdout-years",
        nargs="+",
        type=int,
        default=DEFAULT_HOLDOUT_YEARS,
        help=(
            "Frozen holdout years for the main comparison surface "
            "(must remain 2024 2025; the harness rejects other windows)"
        ),
    )
    parser.add_argument("--cache-path", default=str(CACHE_PATH), help="Race cache path")
    parser.add_argument("--phase7-rules", default=str(PHASE7_RULES_PATH), help="Phase 7 rules JSON path")
    parser.add_argument("--wf-folds", default=str(WF_FOLDS_PATH), help="Walk-forward folds CSV path")
    parser.add_argument("--wf-rules", default=str(WF_RULES_PATH), help="Walk-forward rules CSV path")
    parser.add_argument("--scorecard-csv", default=str(SCORECARD_CSV), help="Forward evidence scorecard CSV path")
    parser.add_argument("--scorecard-json", default=str(SCORECARD_JSON), help="Forward evidence scorecard JSON path")
    parser.add_argument("--current-evidence-json", default=str(CURRENT_EVIDENCE_JSON), help="Current evidence bridge JSON path for operator-boundary context")
    parser.add_argument("--cross-family-csv", default=str(SOURCE_PATHS["cross_family_decision_card"]), help="Cross-family decision CSV path for current anchor / companion / shadow hierarchy labels")
    parser.add_argument("--backtest-csv", default=str(SOURCE_PATHS["backtest_summary"]), help="Backtest summary CSV path for Harville and odds-only ML benchmark rows")
    parser.add_argument("--ab-json", default=str(SOURCE_PATHS["ab_downstream_comparison_results"]), help="Downstream A/B comparison JSON path for XGBoost research-only context")
    parser.add_argument("--csv-output", default=str(OUT_CSV), help="CSV output path")
    parser.add_argument("--md-output", default=str(OUT_MD), help="Markdown report output path")
    parser.add_argument("--json-output", default=str(OUT_JSON), help="JSON sidecar output path")
    parser.add_argument("--runtime-sec", type=float, help="Optional runtime override for reproducible rerenders")
    return parser.parse_args()


def require_columns(df: pd.DataFrame, required: set[str], source_path: Path, label: str) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{source_path.name} is missing required {label} columns: {', '.join(missing)}")


def load_cache(cache_path: Path = CACHE_PATH) -> pd.DataFrame:
    df = pd.read_pickle(cache_path).copy()
    df["second_prob"] = df["fav_prob"] - df["prob_gap"]
    df["top2_mass"] = df["fav_prob"] + df["second_prob"]
    return df


def load_phase7_rules(phase7_rules_path: Path = PHASE7_RULES_PATH) -> list[dict]:
    payload = json.loads(phase7_rules_path.read_text())
    if "rules" not in payload or not isinstance(payload["rules"], list):
        raise ValueError(f"{phase7_rules_path.name} must contain a top-level rules list")
    rules: list[dict] = []
    for raw in payload["rules"]:
        rules.append(
            {
                "rule_id": raw["rule_id"],
                "track": raw["track"],
                "k": int(raw["k"]),
                "field_min": int(raw["field_min"]),
                "field_max": int(raw["field_max"]),
                "gap_min": float(raw["gap_min"]),
                "fav_prob_min": float(raw["fav_prob_min"]),
                "condition": raw["condition"],
                "card_min": int(raw["card_min"]),
                "months": [int(m) for m in raw.get("months", [])],
                "top2_mass_min": (
                    float(raw["top2_mass_min"]) if raw.get("top2_mass_min") is not None else None
                ),
            }
        )
    return rules


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
        mask &= np.isin(df["month"].to_numpy(dtype=np.int16), np.array(rule["months"], dtype=np.int16))

    if rule.get("top2_mass_min") is not None:
        mask &= df["top2_mass"].to_numpy(dtype=np.float64) >= float(rule["top2_mass_min"])

    return mask


def compile_rules(df: pd.DataFrame, rules: list[dict]) -> list[dict]:
    compiled: list[dict] = []
    for rule in rules:
        compiled.append(
            {
                "rule_id": rule["rule_id"],
                "mask": build_mask(df, rule),
                "hit": df[f"hit_{rule['k']}"] .to_numpy(dtype=bool),
                "cost": perm(rule["k"] - 1, 3),
            }
        )
    return compiled


def aggregate_year_rows(rows: list[dict]) -> dict:
    year_df = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
    races = int(year_df["races"].sum()) if not year_df.empty else 0
    hits = int(year_df["hits"].sum()) if not year_df.empty else 0
    wagered = float(year_df["wagered"].sum()) if not year_df.empty else 0.0
    returned = float(year_df["returned"].sum()) if not year_df.empty else 0.0
    profit = float(year_df["profit"].sum()) if not year_df.empty else 0.0
    roi = profit / wagered * 100.0 if wagered else 0.0

    observed = year_df[year_df["races"] > 0].copy() if not year_df.empty else year_df
    observed_years = int(len(observed))
    positive_years = int((observed["roi"] > 0).sum()) if observed_years else 0

    return {
        "year_df": year_df,
        "races": races,
        "hits": hits,
        "wagered": round(wagered, 2),
        "returned": round(returned, 2),
        "profit": round(profit, 2),
        "roi": round(roi, 2),
        "hit_rate": round(hits / races * 100.0, 2) if races else 0.0,
        "positive_years": positive_years,
        "observed_years": observed_years,
    }


def year_snapshot(stats: dict, year: int) -> dict[str, float | int]:
    year_df = stats["year_df"]
    match = year_df[year_df["year"] == year]
    if match.empty:
        return {"races": 0, "roi": 0.0, "profit": 0.0}
    row = match.iloc[0]
    return {
        "races": int(row["races"]),
        "roi": round(float(row["roi"]), 2),
        "profit": round(float(row["profit"]), 2),
    }


def evaluate_fixed_method(df: pd.DataFrame, rules: list[dict], years: list[int]) -> dict:
    compiled = compile_rules(df, rules)
    payout = df["payout"].to_numpy(dtype=np.float64)
    year_arr = df["year"].to_numpy(dtype=np.int16)

    rows: list[dict] = []
    for year in years:
        year_mask = year_arr == year
        total_races = 0
        total_hits = 0
        total_wagered = 0.0
        total_returned = 0.0

        for item in compiled:
            mask = item["mask"] & year_mask
            races = int(mask.sum())
            hits = int((mask & item["hit"]).sum())
            wagered = races * item["cost"]
            returned = float(payout[mask & item["hit"]].sum())
            total_races += races
            total_hits += hits
            total_wagered += wagered
            total_returned += returned

        profit = total_returned - total_wagered
        roi = profit / total_wagered * 100.0 if total_wagered else 0.0
        rows.append(
            {
                "year": int(year),
                "races": total_races,
                "hits": total_hits,
                "wagered": round(total_wagered, 2),
                "returned": round(total_returned, 2),
                "profit": round(profit, 2),
                "roi": round(roi, 2),
            }
        )

    return aggregate_year_rows(rows)


def dynamic_rows_from_folds(folds: pd.DataFrame) -> dict:
    rows = []
    for _, row in folds.sort_values("test_year").iterrows():
        rows.append(
            {
                "year": int(row["test_year"]),
                "races": int(row["test_races"]),
                "hits": int(row["test_hits"]),
                "wagered": float(row["test_wagered"]),
                "returned": round(float(row["test_wagered"]) + float(row["test_profit"]), 2),
                "profit": float(row["test_profit"]),
                "roi": float(row["test_roi"]),
            }
        )
    return aggregate_year_rows(rows)


def dynamic_op_switch_rows(rule_df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    op_rows = rule_df[rule_df["rule_id"].isin(["OP_DURABLE_K7", "OP_REFINED_K7"])].copy()
    chosen_rows: list[pd.Series] = []

    for _, group in op_rows.groupby("test_year"):
        eligible = group[group["qualifies"] == True].copy()  # noqa: E712
        pool = eligible if not eligible.empty else group
        chosen = pool.sort_values(
            ["selection_score", "train_races", "train_roi", "rule_id"],
            ascending=[False, False, False, True],
        ).iloc[0]
        chosen_rows.append(chosen)

    chosen_df = pd.DataFrame(chosen_rows).sort_values("test_year").reset_index(drop=True)
    rows = []
    for _, row in chosen_df.iterrows():
        rows.append(
            {
                "year": int(row["test_year"]),
                "races": int(row["test_races"]),
                "hits": int(row["test_hits"]),
                "wagered": float(row["test_wagered"]),
                "returned": round(float(row["test_wagered"]) + float(row["test_profit"]), 2),
                "profit": float(row["test_profit"]),
                "roi": float(row["test_roi"]),
            }
        )

    return aggregate_year_rows(rows), chosen_df


def conservative_score(row: pd.Series, max_holdout_races: int) -> float:
    def roi_score(value: float) -> float:
        capped = float(np.clip(value, -50, 75))
        return (capped + 50.0) / 125.0 * 100.0

    holdout_year_score = (
        row["holdout_positive_years"] / row["holdout_observed_years"] * 100.0
        if row["holdout_observed_years"]
        else 0.0
    )
    wf_year_score = (
        row["wf_positive_years"] / row["wf_observed_years"] * 100.0
        if row["wf_observed_years"]
        else 0.0
    )
    size_score = (
        np.log1p(row["holdout_races"]) / np.log1p(max_holdout_races) * 100.0
        if row["holdout_races"] > 0 and max_holdout_races > 0
        else 0.0
    )

    score = (
        0.35 * holdout_year_score
        + 0.25 * size_score
        + 0.20 * roi_score(row["holdout_roi"])
        + 0.10 * roi_score(row["wf_roi"])
        + 0.10 * wf_year_score
    )
    return round(float(score), 1)


def fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"


def fmt_plain_pct(value: float) -> str:
    return f"{value:.2f}%"


def fmt_money(value: float) -> str:
    return f"${value:,.2f}"


def md_cell(value: Any, fallback: str = "none") -> str:
    if value is None or value == "":
        return fallback
    return str(value).replace("|", "\\|")


def load_method_family_rows(
    compare_rows: Optional[list[dict]] = None,
    cross_family_csv: Optional[Path] = None,
    backtest_csv: Optional[Path] = None,
    ab_json: Optional[Path] = None,
) -> list[dict]:
    import method_family_decision_card as mfd

    return mfd.build_rows(
        compare_rows=compare_rows,
        cross_family_csv=cross_family_csv,
        backtest_csv=backtest_csv,
        ab_json=ab_json,
    )


def load_scorecard_rows(scorecard_csv: Path = SCORECARD_CSV) -> pd.DataFrame:
    df = pd.read_csv(scorecard_csv)
    require_columns(df, REQUIRED_SCORECARD_COLUMNS, scorecard_csv, "scorecard")
    if "rule_id" not in df.columns:
        raise ValueError(f"{scorecard_csv.name} is missing required scorecard columns: rule_id")
    missing_rules = [rule_id for rule_id in REQUIRED_SCORECARD_RULE_IDS if rule_id not in set(df["rule_id"].astype(str))]
    if missing_rules:
        raise ValueError(
            f"{scorecard_csv.name} is missing required scorecard rows: {', '.join(missing_rules)}"
        )
    return df.set_index("rule_id")


def load_walk_forward_artifacts(
    wf_folds_path: Path = WF_FOLDS_PATH,
    wf_rules_path: Path = WF_RULES_PATH,
    holdout_years: Optional[list[int]] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    folds = pd.read_csv(wf_folds_path)
    require_columns(folds, REQUIRED_WF_FOLD_COLUMNS, wf_folds_path, "walk-forward folds")

    rule_df = pd.read_csv(wf_rules_path)
    require_columns(rule_df, REQUIRED_WF_RULE_COLUMNS, wf_rules_path, "walk-forward rules")

    years_to_check = sorted(set(int(y) for y in (holdout_years or DEFAULT_HOLDOUT_YEARS)))
    for year in years_to_check:
        year_rows = rule_df[rule_df["test_year"] == year]
        if year_rows.empty:
            raise ValueError(f"{wf_rules_path.name} has no walk-forward rule rows for required holdout year {year}")
        for rule_id in REQUIRED_OP_SWITCH_RULES:
            if year_rows[year_rows["rule_id"] == rule_id].empty:
                raise ValueError(
                    f"{wf_rules_path.name} is missing required OP switch row for {rule_id} in holdout year {year}"
                )

    return folds, rule_df


def build_current_rule_ladder(
    selective_family: dict[str, object],
    scorecard_csv: Path = SCORECARD_CSV,
) -> list[dict[str, object]]:
    scorecard = load_scorecard_rows(scorecard_csv)
    ladder_specs = [
        {
            "lane": "Anchor now",
            "rule_id": str(selective_family["current_anchor"]),
        },
        {
            "lane": "Paper-trade companion",
            "rule_id": str(selective_family["primary_shadow"]),
        },
        {
            "lane": "Same-family challenger",
            "rule_id": str(selective_family["secondary_shadow"]),
        },
        {
            "lane": "Dormant Belmont leg",
            "rule_id": "BEL_BROAD1_K7",
        },
    ]

    rows: list[dict[str, object]] = []
    for spec in ladder_specs:
        score_row = scorecard.loc[spec["rule_id"]]
        rows.append(
            {
                "lane": spec["lane"],
                "rule_id": spec["rule_id"],
                "posture": str(score_row["tier"]),
                "holdout_2024_roi": float(score_row["holdout_2024_roi"]),
                "holdout_2024_races": int(score_row["holdout_2024_races"]),
                "holdout_2025_roi": float(score_row["holdout_2025_roi"]),
                "holdout_2025_races": int(score_row["holdout_2025_races"]),
                "wf": f"{int(score_row['wf_selected_count'])}/{int(score_row['wf_total_folds'])}",
                "action_now": str(score_row["action_now"]),
                "why": str(score_row["deployment_reason"]),
            }
        )
    return rows


def build_shadow_watch_triage(scorecard_csv: Path = SCORECARD_CSV) -> list[dict[str, object]]:
    scorecard = load_scorecard_rows(scorecard_csv)
    watch_rule_ids = ["OP_REFINED_K7", "DMR_FALL_K7", "KEE_K9", "SA_K9"]

    rows: list[dict[str, object]] = []
    for rule_id in watch_rule_ids:
        score_row = scorecard.loc[rule_id]
        rows.append(
            {
                "rule_id": rule_id,
                "current_role": str(score_row["current_role"]),
                "holdout_2024_roi": float(score_row["holdout_2024_roi"]),
                "holdout_2024_races": int(score_row["holdout_2024_races"]),
                "holdout_2025_roi": float(score_row["holdout_2025_roi"]),
                "holdout_2025_races": int(score_row["holdout_2025_races"]),
                "wf": f"{int(score_row['wf_selected_count'])}/{int(score_row['wf_total_folds'])}",
                "why": str(score_row["deployment_reason"]),
            }
        )
    return rows


def build_op_challenger_diagnostic(
    selective_family: dict[str, object],
    scorecard_csv: Path = SCORECARD_CSV,
    scorecard_json: Path = SCORECARD_JSON,
) -> dict[str, object]:
    scorecard = load_scorecard_rows(scorecard_csv)
    anchor_rule = str(selective_family["current_anchor"])
    challenger_rule = str(selective_family["secondary_shadow"])
    scorecard_ci_diagnostic = load_scorecard_ci_only_promotion_diagnostic(
        scorecard_json=scorecard_json,
        candidate_rule=challenger_rule,
        anchor_rule=anchor_rule,
    )
    anchor = scorecard.loc[anchor_rule]
    challenger = scorecard.loc[challenger_rule]
    anchor_races = int(anchor["holdout_races"])
    challenger_races = int(challenger["holdout_races"])
    losing_years = [
        year
        for year in (2024, 2025)
        if float(challenger[f"holdout_{year}_roi"]) < 0
    ]

    return {
        "anchor_rule": anchor_rule,
        "challenger_rule": challenger_rule,
        "anchor_holdout_races": anchor_races,
        "challenger_holdout_races": challenger_races,
        "challenger_sample_ratio_pct": round(100.0 * challenger_races / anchor_races, 2),
        "challenger_sample_deficit_races": anchor_races - challenger_races,
        "anchor_wf_selected_count": int(anchor["wf_selected_count"]),
        "challenger_wf_selected_count": int(challenger["wf_selected_count"]),
        "wf_selection_deficit_folds": int(anchor["wf_selected_count"]) - int(challenger["wf_selected_count"]),
        "anchor_ci_lower": float(anchor["ci_lower"]),
        "challenger_ci_lower": float(challenger["ci_lower"]),
        "challenger_has_higher_aggregate_holdout_roi": bool(
            float(challenger["holdout_roi"]) > float(anchor["holdout_roi"])
        ),
        "challenger_has_positive_ci_lower": bool(float(challenger["ci_lower"]) > 0),
        "challenger_losing_holdout_years": losing_years,
        "ci_only_promotion_allowed": bool(scorecard_ci_diagnostic["ci_only_promotion_allowed"]),
        "ci_only_promotion_blockers": [
            "smaller holdout sample",
            "losing holdout-year split",
            "lower walk-forward selection frequency",
            "separate 20-row promotion-review and 30-row anchor-displacement paper-observation gates not cleared",
        ],
        "ci_only_promotion_read": (
            "A positive bootstrap CI lower bound is useful support context, but it is not enough by itself "
            f"to promote {challenger_rule} or displace {anchor_rule}; the challenger still has a smaller "
            "holdout sample, a losing holdout-year split, lower walk-forward recurrence, and no ROI-complete "
            "paper observations clearing the separate promotion or anchor-review gates."
        ),
        "scorecard_ci_only_diagnostic_source": (
            f"{Path(scorecard_json).name}:ci_only_promotion_diagnostics.{challenger_rule}"
        ),
        "scorecard_ci_only_promotion_diagnostic": scorecard_ci_diagnostic,
    }


def build_method_family_evidence_debt(
    selective_family: dict[str, Any],
    harville_family: dict[str, Any],
    xgboost_family: dict[str, Any],
    decision_change_gate_minimums: dict[str, Any],
) -> list[dict[str, Any]]:
    phase8_gate = decision_change_gate_minimums["phase8_promotion_review"]
    anchor_gate = decision_change_gate_minimums["anchor_displacement"]
    real_money_gate = decision_change_gate_minimums["real_money_discussion"]
    phase8_min = int(phase8_gate["minimum_roi_complete_settled_observations"])
    anchor_min = int(anchor_gate["minimum_roi_complete_same_candidate_observations"])
    real_money_min = int(real_money_gate["minimum_total_settled_roi_complete_observations"])
    selective_gate_sources = {
        "phase8_promotion_review": {
            "minimum": phase8_min,
            "threshold_source": str(phase8_gate["threshold_source"]),
        },
        "anchor_displacement": {
            "minimum": anchor_min,
            "threshold_source": str(anchor_gate["threshold_source"]),
        },
        "real_money_discussion": {
            "minimum": real_money_min,
            "threshold_source": str(real_money_gate["threshold_source"]),
        },
    }
    return [
        {
            "family": "Selective OP/CD rule path",
            "still_missing": (
                "Future settled OP/CD paper rows with usable ROI coverage; "
                f"`{selective_family['secondary_shadow']}` also needs {phase8_min}+ complete shadow rows before promotion review; "
                f"{anchor_min}+ same-candidate rows before anchor displacement; "
                f"{real_money_min}+ total ROI-complete observations before any real-money discussion"
            ),
            "invalid_shortcut": (
                "Treating old holdout/replay rows, clean scans, open signals, or a settlement-audit pass "
                "as posture-changing proof"
            ),
            "next_honest_action": (
                f"Keep collecting and settling `{selective_family['current_anchor']}` + "
                f"`{selective_family['primary_shadow']}` observations; log "
                f"`{selective_family['secondary_shadow']}` as shadow-only until the explicit gates are met"
            ),
            "source_gate_minimums": selective_gate_sources,
        },
        {
            "family": "Harville-ranked probabilities",
            "still_missing": (
                "Positive betting evidence on frozen holdout or train-only walk-forward terms, "
                "not just broad hit-rate/calibration context"
            ),
            "invalid_shortcut": (
                f"Promoting from a {fmt_plain_pct(float(harville_family['secondary_metric']))} hit rate "
                f"while the broad betting replay is {fmt_pct(float(harville_family['primary_metric']))} ROI"
            ),
            "next_honest_action": (
                "Keep Harville as a benchmark/calibration sanity check unless a future "
                "betting-evidence surface turns positive"
            ),
        },
        {
            "family": "Current odds-only XGBoost correction path",
            "still_missing": (
                "A materially richer non-odds feature/data class, downstream betting pass-through "
                "improvement, and then settled paper observations"
            ),
            "invalid_shortcut": (
                "Reopening from another odds-only rerun, payout-RMSE gain, or model-fit-only "
                f"downstream A/B result while betting ROI remains {fmt_pct(float(xgboost_family['primary_metric']))}"
            ),
            "next_honest_action": (
                "Keep the current odds-only XGBoost path parked; reopen only if the feature class "
                "changes and the betting pass-through improves before paper observation"
            ),
        },
    ]


def build_report(
    df: pd.DataFrame,
    holdout_years: list[int],
    wf_years: list[int],
    runtime_sec: float,
    family_rows: list[dict],
    csv_output_name: Optional[str] = None,
    md_output_name: Optional[str] = None,
    json_output_name: Optional[str] = None,
    scorecard_csv: Path = SCORECARD_CSV,
    scorecard_json: Path = SCORECARD_JSON,
    current_evidence_json: Path = CURRENT_EVIDENCE_JSON,
    source_paths: Optional[dict[str, Path]] = None,
) -> str:
    ranked = df.sort_values(["rank"]).reset_index(drop=True)
    holdout_label = f"{min(holdout_years)}-{max(holdout_years)}"
    wf_label = f"{min(wf_years)}-{max(wf_years)}"
    family_by_id = {str(row["family_id"]): row for row in family_rows}
    selective_family = family_by_id["selective_rule_path"]
    harville_family = family_by_id["harville_ranked"]
    xgboost_family = family_by_id["xgboost_residual"]
    current_rule_ladder = build_current_rule_ladder(selective_family, scorecard_csv=scorecard_csv)
    shadow_watch_triage = build_shadow_watch_triage(scorecard_csv=scorecard_csv)
    op_challenger_diagnostic = build_op_challenger_diagnostic(
        selective_family,
        scorecard_csv=scorecard_csv,
        scorecard_json=scorecard_json,
    )
    scorecard_ranking_contract = load_scorecard_ranking_contract(scorecard_json)
    decision_change_gate_minimums = load_decision_change_gate_minimums(scorecard_json)
    evidence_debt_rows = build_method_family_evidence_debt(
        selective_family,
        harville_family,
        xgboost_family,
        decision_change_gate_minimums,
    )
    current_operator_boundary = load_current_operator_boundary(current_evidence_json)
    if current_operator_boundary["operator_read_gate"].get("requires_refresh_before_evidence_read"):
        operator_gate_boundary_read = (
            "The saved top card must be refreshed before evidence/instruction use; this read gate is not "
            "no-target evidence, clean-empty evidence, bet readiness, settled ROI, promotion readiness, "
            "live profitability, bankroll guidance, or real-money evidence"
        )
    else:
        operator_gate_boundary_read = (
            "The saved top card can be read as current operator routing context only; this read gate is not "
            "no-target evidence, clean-empty evidence, bet readiness, settled ROI, promotion readiness, "
            "live profitability, bankroll guidance, or real-money evidence"
        )
    rebuild_order_commands = [
        str(row["command"])
        for row in current_operator_boundary["rebuild_validation_contract"]["upstream_refresh_order"]
    ]
    rebuild_order_read = " -> ".join(f"`{command}`" for command in rebuild_order_commands)
    source_fingerprints = source_file_fingerprints(source_paths=source_paths)
    source_file_list = ", ".join(f"`{fingerprint['path']}`" for fingerprint in source_fingerprints.values())

    best_large = ranked.sort_values(
        ["holdout_observed_years", "holdout_positive_years", "holdout_races", "holdout_roi"],
        ascending=[False, False, False, False],
    ).iloc[0]
    op_only = ranked[ranked["op_focus"] == True].copy()  # noqa: E712
    top_op = op_only.sort_values(["score", "holdout_races"], ascending=[False, False]).iloc[0]
    safe_op = ranked[ranked["method_id"] == "op_durable_only"].iloc[0]
    selector = ranked[ranked["method_id"] == "train_only_selector"].iloc[0]

    csv_output_name = csv_output_name or OUT_CSV.name
    md_output_name = md_output_name or OUT_MD.name
    json_output_name = json_output_name or OUT_JSON.name

    lines = [
        "# Main Approach Comparison",
        "",
        "## Usage",
        "",
        "```bash",
        "python3 compare_main_approaches.py",
        "```",
        "",
        "This is a fast comparison harness. It replays a small fixed set of methods and reads the existing walk-forward artifacts. It does not run a new broad search.",
        "",
        "## Scope",
        "",
        f"- Holdout focus: {holdout_label}",
        "- This harness is intentionally locked to the frozen 2024-2025 holdout standard so the main comparison surface cannot drift onto a different evaluation window.",
        f"- Walk-forward test-year window: next-year tests across {wf_label}, excluding 2021 because the project data excludes that year",
        "- Secondary context is intentionally split: fixed methods get frozen replays on those walk-forward test years, while dynamic selectors keep their actual train-only walk-forward totals",
        "- No new BEL->BAQ aliasing is introduced here",
        "- Conservative score weights holdout consistency and holdout sample size more than flashy ROI",
        "- Deployment posture is the operator-facing label. Score is evidence ordering only, not an auto-promotion rule.",
        f"- Inherited scorecard ranking contract: rank is tier-first (`{scorecard_ranking_contract['rank_is_tier_first_decision_order']}`), forward_trust/Score is secondary within tier (`{scorecard_ranking_contract['forward_trust_is_secondary_within_tier']}`), and raw score is not an automatic deployment instruction (`{scorecard_ranking_contract['raw_score_is_not_an_automatic_deployment_instruction']}`).",
        "- Settlement-audit and ledger-quality surfaces are operational guardrails; they do not change this comparison without ROI-complete settled outcomes.",
        f"- Output bundle: `{csv_output_name}`, `{md_output_name}`, and `{json_output_name}` are generated together; the JSON sidecar publishes machine-readable evidence_boundary metadata plus the method-family evidence-debt checklist for automation, not live paper-trade or promotion evidence.",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {MACHINE_READABLE_EVIDENCE_BOUNDARY['artifact_role']}",
        f"- `valid_evidence_scope={MACHINE_READABLE_EVIDENCE_BOUNDARY['valid_evidence_scope']}`",
        f"- Valid use: {MACHINE_READABLE_EVIDENCE_BOUNDARY['valid_use']}",
        "- This bundle is a frozen comparison/reproducibility surface only: it is not new forward evidence, a live paper-trade ledger, current-day scanner output, settled ROI, live profitability, promotion readiness, or real-money evidence.",
        "- Source fingerprints are reproducibility metadata only; row-identical source-byte drift changes provenance only, not ranked rows or performance evidence.",
        "- Decision-change gates are forward-observation requirements, not evidence that a gate has already been cleared.",
        f"- Scorecard rank contract inherited: {scorecard_ranking_contract['known_rank_override']}",
        "- Non-goals: do not promote OP_REFINED_K7 or Phase 8, reopen current odds-only XGBoost, treat Harville as live, substitute BAQ for BEL, quote current `PAPER_TRADE_NOW` instructions without the combined `CURRENT_EVIDENCE_SUMMARY.md` / `operator_status_context` / `source_freshness` / `operator_read_gate` route, or discuss real-money scaling from this artifact.",
        "- Current-evidence bridge data, when shown below, is operator-routing context only and does not convert open signals, recommendation-state context, source freshness, or settlement queue rows into settled ROI or bet readiness.",
        "",
        "## Current Operator Boundary Snapshot",
        "",
        f"This small snapshot is copied from `{current_operator_boundary['source_path']}` so the comparison report can point to the current settlement boundary without becoming a live-paper performance surface.",
        "",
        "| Field | Current bridge read | Evidence boundary |",
        "|---|---|---|",
        f"| Source freshness | `{current_operator_boundary['right_now_freshness_state']}`; refresh before right-now use = `{current_operator_boundary['requires_refresh_before_right_now_use']}` | Source freshness is operator-readiness metadata, not performance proof |",
        f"| Source freshness reference | bridge reference date `{current_operator_boundary['source_freshness_generated_reference_date']}` in `{current_operator_boundary['source_freshness_generated_reference_timezone']}`; compared via `{current_operator_boundary['source_freshness_staleness_comparison_source']}` = `{current_operator_boundary['source_freshness_staleness_comparison_date']}`; right-now as-of `{current_operator_boundary['right_now_as_of_date']}` / run `{current_operator_boundary['right_now_run_date']}` | Reference-date routing is reproducibility metadata for stale-card checks, not performance proof |",
        f"| Refresh action boundary | `{current_operator_boundary['refresh_action_command']}` required before right-now use = `{current_operator_boundary['refresh_required_before_right_now_instruction_use']}`; source action current before refresh = `{current_operator_boundary['refresh_source_action_counts_as_current_instruction_before_refresh']}`; can update operator surfaces = `{current_operator_boundary['refresh_can_update_operator_surfaces']}`; settles rows / creates ROI evidence / clean-empty performance = `{current_operator_boundary['refresh_can_settle_open_rows_by_itself']}` / `{current_operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}` / `{current_operator_boundary['clean_empty_refresh_counts_as_forward_performance']}` | Wrapper refresh is operator routing only; it is not settled ROI, promotion readiness, live profitability, or real-money evidence |",
        f"| Source consistency | overall match = `{current_operator_boundary['source_consistency_overall_match']}` | Fingerprints and bridge consistency are reproducibility checks only |",
        f"| Bridge-published gate progress | `{current_operator_boundary['source_path']}` `decision_gate_progress`: {md_cell(current_operator_boundary['decision_gate_progress']['read'])} Source: `{current_operator_boundary['decision_gate_progress']['source_path']}` `{current_operator_boundary['decision_gate_progress']['source_json_path']}`; gate status = `{current_operator_boundary['decision_gate_progress']['gate_status']}` | Current gates are all uncleared routing context only; they do not create settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
        f"| Scorecard audit route | `{current_operator_boundary['source_path']}` `scorecard_audit_route`: {md_cell(current_operator_boundary['scorecard_audit_route']['route_read'])} Validator: `{current_operator_boundary['scorecard_audit_route']['validator_command']}`; artifacts: `{current_operator_boundary['scorecard_audit_route']['markdown_path']}` / `{current_operator_boundary['scorecard_audit_route']['json_path']}`; gate snapshot = 30/20/100 with no-BAQ-as-BEL required `{current_operator_boundary['scorecard_audit_route']['gate_floor_snapshot']['real_money_no_baq_as_bel_required']}` | Report-synchronization route only; it is not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
        f"| Current bridge rebuild order | `{current_operator_boundary['source_path']}` `rebuild_validation_contract`: "
        f"{rebuild_order_read} before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes | "
        "Provenance/rebuild route only; green checks and rebuild order are not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
        f"| Operator read gate | `{current_operator_boundary['source_path']}` `operator_read_gate`: {md_cell(current_operator_boundary['operator_read_gate']['read'])} Gate status = `{current_operator_boundary['operator_read_gate']['gate_status']}`; recommended command = `{current_operator_boundary['operator_read_gate']['recommended_command']}` | {operator_gate_boundary_read} |",
        f"| Current settled rule mix | OP_DURABLE_K7={current_operator_boundary['op_anchor_roi_complete_rows']}; CD_CORE_K8={current_operator_boundary['cd_companion_roi_complete_rows']}; {md_cell(current_operator_boundary['primary_rule_mix_read'])} | Rule-specific settled rows stay separate; CD-only paper rows are not OP-anchor forward evidence |",
        f"| Settlement queue state | `{current_operator_boundary['open_settlement_queue_state']}`; {md_cell(current_operator_boundary['open_settlement_context'])}; detail: {md_cell(current_operator_boundary['open_settlement_queue_read'])} | Open rows are settlement workflow only; fill outcomes from result/payout evidence before interpreting ROI |",
        f"| Recommendation context | {md_cell(current_operator_boundary['recommendation_context_read'])} | Latest recommendation-state context is operator routing only, not bet readiness or forward-performance evidence |",
        f"| Operator route | `{current_operator_boundary['best_action_command']}` | Use the bridge route to settle or refresh; do not infer profit, promotion, or real-money readiness from the route itself |",
        "",
        "## Source Provenance",
        "",
        f"These fingerprints identify the exact input files used by this comparison rerender. {EVIDENCE_BOUNDARY}.",
        "",
        "| Source | Path | Bytes | SHA-256 |",
        "|---|---|---:|---|",
    ]

    for label, fingerprint in source_fingerprints.items():
        lines.append(format_source_fingerprint_row(label, fingerprint))

    lines.extend([
        "",
        "## Cole's One-Screen Read",
        "",
        "Use this when the full report is too much and Cole needs the decision-safe answer first. This is a routing summary, not new forward evidence.",
        "",
        "| Question | Current read | Evidence boundary |",
        "|---|---|---|",
        f"| What is the primary paper-basket core? | Keep `{selective_family['current_anchor']}` as the anchor and `{selective_family['primary_shadow']}` as the primary paper-basket companion | Paper only; daily target-card availability still comes from the current preflight, and real-money confidence still needs 100+ settled ledger observations with usable ROI coverage plus concentration and payout checks |",
        f"| What is the closest challenger? | `{selective_family['secondary_shadow']}` is the closest same-family OP shadow, not a promoted default | Promotion review needs 20+ future settled shadow ledger observations; replacing the anchor needs 30+ ROI-complete same-candidate observations plus cleaner split-aware/walk-forward support |",
        f"| Does Harville change the current paper path? | No — Harville remains {harville_family['role']} | Current broad replay is {fmt_pct(float(harville_family['primary_metric']))} ROI despite a {fmt_plain_pct(float(harville_family['secondary_metric']))} hit rate; it needs positive betting evidence, not just calibration value |",
        f"| Does current odds-only XGBoost change the current paper path? | No — current odds-only XGBoost remains {xgboost_family['role']} / parked | Best ML betting ROI is {fmt_pct(float(xgboost_family['primary_metric']))}; another odds-only replay is not enough to reopen it |",
        "| Do clean scans or settlement audits change posture? | No — clean scans, open signals, and ledger/settlement audits are operability checks, not performance proof | They can reveal missing templates or ROI-coverage gaps; only settled hit/miss rows with usable return/cost coverage can feed future decision changes |",
        "| Can BAQ stand in for BEL? | No — keep `BEL_BROAD1_K7` dormant until fresh Belmont races exist | BAQ needs independent evidence and must not inherit BEL's rule |",
        "",
        "## Method-Family Action Summary",
        "",
        "Use this when the comparison question is Harville vs current odds-only XGBoost vs the selective OP/CD path. It is an action map, not a profitability upgrade.",
        "",
        "| Family | Use it for now | Do not use it for | Next valid evidence |",
        "|---|---|---|---|",
        f"| Selective rule path | Paper-observe `{selective_family['current_anchor']}` + `{selective_family['primary_shadow']}` and keep `{selective_family['secondary_shadow']}` shadow-only | Real-money confidence or anchor changes before settled ROI-complete paper observations | 100+ settled paper observations with usable ROI coverage for confidence; 20+ settled shadow observations before `{selective_family['secondary_shadow']}` promotion review; 30+ same-candidate ROI-complete observations plus cleaner split-aware/walk-forward support before anchor displacement |",
        f"| Harville-ranked probabilities | Calibration and benchmark sanity checks | Paper-bet selection or deployment promotion from hit rate alone | Positive frozen-holdout or train-only walk-forward betting evidence; calibration-only summaries do not change posture |",
        f"| Current odds-only XGBoost correction path | Research-only diagnostics for what odds-derived models can and cannot add | Reopening the betting path from another odds-only replay or payout-model metric | A materially richer non-odds feature/data class, downstream betting pass-through improvement, and then settled paper observations |",
        "",
        "- Action map verdict: spend operational energy on settled selective paper observations first; Harville and current odds-only XGBoost stay comparison controls unless their evidence class changes. Settlement-audit repairs can make future rows usable, but audit cleanliness alone does not promote any lane.",
        "",
        "## OP Challenger Support Check",
        "",
        "This narrow check keeps OP_REFINED_K7's positive CI lower bound in the right evidence class before the broader method tables.",
        "",
        f"- Scorecard diagnostic source: `{op_challenger_diagnostic['scorecard_ci_only_diagnostic_source']}` (`ci_only_promotion_allowed={str(op_challenger_diagnostic['scorecard_ci_only_promotion_diagnostic']['ci_only_promotion_allowed']).lower()}`).",
        f"- `{op_challenger_diagnostic['challenger_rule']}` has `{op_challenger_diagnostic['challenger_holdout_races']}` holdout races versus `{op_challenger_diagnostic['anchor_holdout_races']}` for `{op_challenger_diagnostic['anchor_rule']}` (`{op_challenger_diagnostic['challenger_sample_ratio_pct']:.2f}%` of the anchor sample; `{op_challenger_diagnostic['challenger_sample_deficit_races']}` fewer races).",
        f"- Walk-forward support is `{op_challenger_diagnostic['challenger_wf_selected_count']}/10` versus `{op_challenger_diagnostic['anchor_wf_selected_count']}/10` for the anchor, a `{op_challenger_diagnostic['wf_selection_deficit_folds']}`-fold deficit.",
        f"- CI-only promotion check: {op_challenger_diagnostic['ci_only_promotion_read']}",
        "- Practical read: positive CI support can keep OP_REFINED_K7 on the closest-shadow watch list, but it cannot by itself promote the rule, displace OP_DURABLE_K7, or change the OP/CD paper core.",
        "",
        "## Method-Family Evidence Debt Checklist",
        "",
        "Use this before starting another experiment. It states what is still missing, what would be an invalid shortcut, and the next honest action for each family.",
        "",
        "| Family | Still missing | Invalid shortcut | Next honest action |",
        "|---|---|---|---|",
    ])

    for row in evidence_debt_rows:
        lines.append(
            f"| {row['family']} | {row['still_missing']} | {row['invalid_shortcut']} | "
            f"{row['next_honest_action']} |"
        )

    lines.extend([
        "",
        f"- Gate floors in this checklist are loaded from `{Path(scorecard_json).name}` `decision_gate_minimums`: phase8_promotion_review={decision_change_gate_minimums['phase8_promotion_review']['minimum_roi_complete_settled_observations']}, anchor_displacement={decision_change_gate_minimums['anchor_displacement']['minimum_roi_complete_same_candidate_observations']}, real_money_discussion={decision_change_gate_minimums['real_money_discussion']['minimum_total_settled_roi_complete_observations']}.",
        "- Evidence-debt verdict: the shortest honest path is still paper observation and settlement completeness for the selective rule path; Harville and current odds-only XGBoost do not need more cosmetic reruns until their missing evidence class changes.",
        "",
        "## Comparison Table",
        "",
        "| Rank | Method | Type | Deployment Posture | Holdout ROI | Holdout Races | Holdout Years+ | Secondary ROI | Secondary Races | Secondary Years+ | Secondary basis | Score | Note |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|",
    ])

    for _, row in ranked.iterrows():
        lines.append(
            f"| {int(row['rank'])} | {row['label']} | {row['method_type']} | {row['deployment_posture']} | "
            f"{fmt_pct(row['holdout_roi'])} | {int(row['holdout_races'])} | "
            f"{int(row['holdout_positive_years'])}/{int(row['holdout_observed_years'])} | "
            f"{fmt_pct(row['wf_roi'])} | {int(row['wf_races'])} | "
            f"{int(row['wf_positive_years'])}/{int(row['wf_observed_years'])} | "
            f"{row['secondary_basis']} | {row['score']:.1f} | {row['note']} |"
        )

    lines.extend(
        [
            "",
            "## Fast Takeaways",
            "",
            f"- Large-sample holdout baseline: **{best_large['label']}** at {fmt_pct(best_large['holdout_roi'])} on {int(best_large['holdout_races'])} holdout races.",
            f"- Safest current OP anchor: **{safe_op['label']}** ({safe_op['deployment_posture']}) at {fmt_pct(safe_op['holdout_roi'])} on {int(safe_op['holdout_races'])} holdout races.",
            f"- Higher-score OP challenger: **{top_op['label']}** at {fmt_pct(top_op['holdout_roi'])} on {int(top_op['holdout_races'])} holdout races, but it stays **{top_op['deployment_posture']}** because the forward sample is still smaller and only {int(top_op['holdout_positive_years'])}/{int(top_op['holdout_observed_years'])} holdout years are positive.",
            f"- Honest selector baseline: **{selector['label']}** stays useful context at {fmt_pct(selector['wf_roi'])} across {int(selector['wf_races'])} actual train-only walk-forward races, but its {holdout_label} holdout is only {fmt_pct(selector['holdout_roi'])} on {int(selector['holdout_races'])} races.",
            "- Fixed-method secondary columns are replay context only. They reuse the frozen rules on the walk-forward test years and should not be read as extra train-only validation.",
            f"- Current paper-companion read: `{selective_family['current_anchor']}` remains the safest anchor, `{selective_family['primary_shadow']}` is the primary OP/CD paper-basket companion, and `{selective_family['secondary_shadow']}` remains the narrower same-family OP shadow challenger.",
            f"- Practical read: use deployment posture for decisions, then use score to compare evidence strength inside that posture instead of auto-promoting smaller-sample challengers. The inherited scorecard contract says: {scorecard_ranking_contract['known_rank_override']}",
            "",
            "## Current Paper-Trade Rule Ladder",
            "",
            "This is the quickest selective-family read when Cole wants the paper-basket rule order rather than the broader method-family guardrail.",
            "",
            "| Lane | Rule | Posture | 2024 ROI (Races) | 2025 ROI (Races) | WF | Action now | Why this is the current read |",
            "|---|---|---|---:|---:|---:|---|---|",
        ]
    )

    for row in current_rule_ladder:
        lines.append(
            f"| {row['lane']} | `{row['rule_id']}` | {row['posture']} | "
            f"{fmt_pct(float(row['holdout_2024_roi']))} ({int(row['holdout_2024_races'])}) | "
            f"{fmt_pct(float(row['holdout_2025_roi']))} ({int(row['holdout_2025_races'])}) | "
            f"{row['wf']} | {row['action_now']} | {row['why']} |"
        )

    lines.extend(
        [
            "",
            f"- Practical read: on the current forward sample, the primary paper-basket core is effectively `{selective_family['current_anchor']}` + `{selective_family['primary_shadow']}`; daily target-card availability still comes from the preflight, `{selective_family['secondary_shadow']}` stays shadow-only, and `BEL_BROAD1_K7` stays dormant until Belmont produces fresh forward races.",
            "- This is a deployment-order table, not a claim that the anchor has the prettiest ROI line. The whole point is to keep sample size and evidence quality ahead of the hottest small-sample number.",
            "",
            "## Phase 8 Shadow-Lane Triage",
            "",
            "This keeps the non-primary watch names in comparison view without letting the Phase 8 shadow lane read like a quiet promotion queue.",
            "",
            "| Rule | Current role | 2024 ROI (Races) | 2025 ROI (Races) | WF | Why it still stays shadow-only |",
            "|---|---|---:|---:|---:|---|",
        ]
    )

    for row in shadow_watch_triage:
        lines.append(
            f"| `{row['rule_id']}` | {row['current_role']} | {fmt_pct(float(row['holdout_2024_roi']))} ({int(row['holdout_2024_races'])}) | "
            f"{fmt_pct(float(row['holdout_2025_roi']))} ({int(row['holdout_2025_races'])}) | {row['wf']} | {row['why']} |"
        )

    lines.extend(
        [
            "",
            f"- Practical read: if Cole wants one shadow name to log most closely, it is still `{selective_family['secondary_shadow']}` because it stays inside the strongest current family.",
            "- The rest of the Phase 8 watch lane is still observation-only context, not a near-promotion bench. Positive pockets there are still too small or too unsupported to displace the current OP+CD paper basket.",
            "",
            "## 2024-2025 Holdout Split",
            "",
            "This is the easiest way to see whether an aggregate holdout ROI is broad enough to trust. The stronger current reads are either positive in both years or carry meaningfully larger samples than the prettier small-sample challengers.",
            "",
            "| Method | Posture | 2024 ROI (Races) | 2025 ROI (Races) | Read |",
            "|---|---|---:|---:|---|",
        ]
    )

    split_reads = {
        "phase7_live_portfolio": "Nearly flat in 2024, then very strong in 2025, on the largest current portfolio holdout sample.",
        "phase8_frozen_portfolio": "Positive in both years, but still weaker overall than Phase 7 on a smaller current sample.",
        "op_refined_only": "Attractive aggregate comes from a smaller sample with a losing 2024 and a very hot 2025.",
        "op_train_switch": "Not independent on holdout yet: it picks OP_REFINED_K7 in both 2024 and 2025, so the split is identical.",
        "op_durable_only": "Ugly 2024, strong 2025 rebound, and still the bigger OP evidence base by far.",
        "train_only_selector": "Helpful benchmark, but the losing 2024 holdout year keeps it out of deployment posture.",
    }
    for _, row in ranked.iterrows():
        lines.append(
            f"| {row['label']} | {row['deployment_posture']} | {fmt_pct(float(row['holdout_2024_roi']))} ({int(row['holdout_2024_races'])}) | "
            f"{fmt_pct(float(row['holdout_2025_roi']))} ({int(row['holdout_2025_races'])}) | {split_reads[str(row['method_id'])]} |"
        )

    lines.extend(
        [
            "",
            "## Method Notes",
            "",
        ]
    )

    for _, row in ranked.iterrows():
        lines.append(f"- **{row['label']}**: {row['note']}")

    lines.extend(
        [
            "",
            "## Method-Family Guardrail",
            "",
            "This table is intentionally not scored against the selective-method rows above. It answers a separate question: should Harville or the current odds-only XGBoost correction path be treated as paper-worthy families at all?",
            "For the selective family, the primary evidence includes the 2024/2025 holdout split because the aggregate number alone is too smooth.",
            "",
            "| Method Family | Role | Primary Evidence | Sample | Secondary Evidence | Why It Still Sits Here |",
            "|---|---|---:|---:|---:|---|",
        ]
    )

    for row in family_rows:
        if str(row["family_id"]) == "selective_rule_path":
            primary = (
                f"{fmt_pct(float(row['primary_metric']))} ({row['primary_metric_label']}; "
                f"2024 {fmt_pct(float(row['holdout_2024_metric']))} on {int(row['holdout_2024_sample'])}, "
                f"2025 {fmt_pct(float(row['holdout_2025_metric']))} on {int(row['holdout_2025_sample'])})"
            )
            why = (
                "Only family here with positive current frozen holdout evidence and a paper-trade observation path. "
                f"In the current holdout, this is effectively the OP+CD basket, with {row['current_anchor']} still the safest anchor, "
                f"{row['primary_shadow']} as the primary OP/CD paper-basket companion, and {row['secondary_shadow']} still the smaller same-family shadow challenger, "
                "but the recent path was uneven rather than a smooth two-year glide."
            )
        else:
            primary = f"{fmt_pct(float(row['primary_metric']))} ({row['primary_metric_label']})"
            why = str(row["why"])
        secondary_label = str(row['secondary_metric_label'])
        secondary_value = fmt_pct(float(row['secondary_metric'])) if "ROI" in secondary_label else fmt_plain_pct(float(row['secondary_metric']))
        lines.append(
            f"| {row['label']} | {row['role']} | {primary} | {int(row['primary_sample'])} | {secondary_value} ({secondary_label}) | {why} |"
        )

    lines.extend(
        [
            "",
            "- Practical read: the ranking table above compares the best current selective deployment options against each other. This guardrail keeps the project from quietly promoting Harville or the parked odds-only XGBoost path back into the current paper path just because a local model metric improves.",
            f"- Selective-family hierarchy read: `{selective_family['current_anchor']}` stays the safest current paper anchor, `{selective_family['primary_shadow']}` is the primary OP/CD paper-basket companion, and `{selective_family['secondary_shadow']}` is still the stronger same-family OP shadow challenger rather than a promoted default.",
            "",
            "## Evidence-Class Triage",
            "",
            "Use this when the question is whether a prettier modeling or benchmark story should change current paper behavior. The answer still depends on evidence class, not just a better-looking metric.",
            "",
            "| Lane | Evidence class | Current decision | What would change it |",
            "|---|---|---|---|",
            f"| Selective rule path | Frozen holdout + train-only walk-forward benchmark ({fmt_pct(float(selective_family['primary_metric']))} on {int(selective_family['primary_sample'])} holdout races; {fmt_pct(float(selective_family['secondary_metric']))} on {int(selective_family['secondary_sample'])} train-only walk-forward races) | PAPER NOW; keep `{selective_family['current_anchor']}` as anchor, `{selective_family['primary_shadow']}` as paper companion, and `{selective_family['secondary_shadow']}` shadow-only | `{selective_family['secondary_shadow']}` promotion review needs 20+ future settled shadow ledger observations with complete ROI coverage and cleaner split-aware/walk-forward support; anchor displacement needs 30+ same-candidate ROI-complete observations; real-money confidence still needs 100+ settled paper observations with usable ROI coverage plus concentration checks |",
            f"| Harville-ranked probabilities | Broad structural benchmark ({fmt_pct(float(harville_family['primary_metric']))} ROI on {int(harville_family['primary_sample'])} races; {fmt_plain_pct(float(harville_family['secondary_metric']))} hit rate) | BENCHMARK ONLY; useful for calibration context, not a paper betting path | Positive frozen holdout / train-only walk-forward betting evidence, not just a high hit rate |",
            f"| Current odds-only XGBoost correction path | Research/model-fit lane ({fmt_pct(float(xgboost_family['primary_metric']))} best ML betting ROI on {int(xgboost_family['primary_sample'])} races; {fmt_plain_pct(float(xgboost_family['secondary_metric']))} matched payout-RMSE reduction context) | RESEARCH ONLY / parked; the enriched horse-history downstream A/B remains separate research-only context too | Material evidence-class change: richer non-odds features plus downstream betting improvement and then settled paper observations; not another odds-only replay |",
            "| Paper-trade operational surfaces | Daily scan results, open signals, settlement audit, and ledger-quality checks | OPERABILITY / REPAIR ONLY; use them to keep the ledger complete before interpreting ROI | They only change posture after they become settled hit/miss rows with usable return/cost coverage; audit cleanliness alone is not forward-performance evidence |",
            "",
            "- This is not new forward evidence. It is a decision-facing guardrail so full-sample benchmarks, model-fit improvements, clean scans, open signals, or ledger audits cannot masquerade as deployment proof.",
            "",
            "## Decision-Change Gates",
            "",
            "Use this as the compact checklist for what would actually be required before the current comparison answer changes. These are gates for future observation, not new claims from this rerun.",
            "",
            f"Machine-readable threshold summary (also copied into the JSON sidecar): anchor_displacement={decision_change_gate_minimums['anchor_displacement']['minimum_roi_complete_same_candidate_observations']} ROI-complete same-candidate observations; phase8_promotion_review={decision_change_gate_minimums['phase8_promotion_review']['minimum_roi_complete_settled_observations']} ROI-complete shadow observations; real_money_discussion={decision_change_gate_minimums['real_money_discussion']['minimum_total_settled_roi_complete_observations']} total settled observations with usable ROI.",
            f"Threshold source: `{Path(scorecard_json).name}` `decision_gate_minimums`; the JSON sidecar records the exact source key for `phase8_promotion_review`, `anchor_displacement`, and `real_money_discussion`.",
            "",
            "| Decision pressure | Current answer | Minimum evidence before the answer changes | Evidence scope | Why the gate exists |",
            "|---|---|---|---|---|",
            f"| Replace `{selective_family['current_anchor']}` anchor with `{selective_family['secondary_shadow']}` | Keep `{selective_family['current_anchor']}` as anchor; `{selective_family['secondary_shadow']}` stays shadow-only | 30+ ROI-complete same-candidate settled paper observations plus cleaner split-aware/walk-forward/frozen support that clearly beats the anchor's larger sample; 20+ shadow rows only starts promotion review | Future settled same-candidate paper ledger rows with complete ROI coverage; historical replay or holdout rows do not count as new promotion evidence | The challenger line is hotter but smaller and uneven: 49 holdout races, a losing 2024 / very hot 2025 split, and only 2/10 walk-forward selections |",
            f"| Move Harville-ranked probabilities into the current paper path | {harville_family['role']} | Positive frozen-holdout or train-only walk-forward betting evidence, not only a high hit rate on a broad benchmark replay | New betting-evidence surface only; calibration or hit-rate summaries without profitable wagering evidence do not change deployment posture | The current broad replay is {fmt_pct(float(harville_family['primary_metric']))} ROI despite a {fmt_plain_pct(float(harville_family['secondary_metric']))} hit rate |",
            f"| Reopen current odds-only XGBoost as a betting path | {xgboost_family['role']} / parked | Richer non-odds features, downstream betting improvement, then settled paper observations; another odds-only replay is not enough | A materially different feature/data class plus downstream betting pass-through; another odds-only rerun is not a new evidence class | Current best ML betting ROI is {fmt_pct(float(xgboost_family['primary_metric']))}, and the downstream A/B remains model-fit context rather than betting proof |",
            "| Substitute BAQ for dormant BEL | Do not substitute; keep `BEL_BROAD1_K7` dormant | Fresh Belmont qualifying races only; BAQ needs its own independent evidence and must not inherit BEL's rule | Fresh Belmont qualifying races only; BAQ needs independent evidence and cannot inherit BEL history | The BEL->BAQ bridge already failed, and the current scorecard has zero BEL holdout races |",
            "| Move from paper to real money | Paper only | 100+ settled paper observations with hit-rate/ROI inside the expected range plus concentration and payout checks | Settled paper-trade ledger observations with usable ROI coverage, not clean scans, open signals, ledger-quality/settlement-audit passes, or replay backtests | Clean runs and clean audits prove operability; they are not forward-profit proof until outcomes settle |",
            "",
            "- Practical read: the next research action is not another odds-only model search. It is disciplined paper observation plus evidence-class changes that would be strong enough to pass these gates; settlement-audit work should repair ledger usability before any ROI interpretation.",
            "",
            "## Narrow Follow-Up Reads",
            "",
            "Use the smaller guardrail artifacts below when the question is narrower than this full comparison stack:",
            "",
            f"- `OP_ANCHOR_METHOD_COMPARISON.md`: use when the question is specifically why `{selective_family['current_anchor']}` still outranks Harville while the current odds-only XGBoost path stays parked unless its evidence class changes materially.",
            "- `AB_DOWNSTREAM_COMPARISON.md`: use when the question is specifically whether the enriched horse-history XGBoost downstream correction is strong enough to change the paper-betting answer. It is not.",
            "- `compare_recommender_scope_paths.md`: use when the question is specifically whether widened `--allow-all-combos` scope should change the current paper default. It should not.",
            "- `out/paper_trade_settlement_audit.md`: use when the question is whether paper-trade ledgers are structurally complete and ROI-covered enough to feed future forward evidence. It is an audit surface, not proof by itself.",
            "",
            "## Validation",
            "",
            f"- Runtime: {runtime_sec:.2f} seconds",
            f"- Data sources: {source_file_list}; see Source Provenance above for exact input-byte fingerprints",
            f"- Wrote: `{csv_output_name}`, `{md_output_name}`, `{json_output_name}`",
            "",
        ]
    )

    return "\n".join(lines)


def build_dataframe(
    holdout_years: list[int],
    cache_path: Path = CACHE_PATH,
    phase7_rules_path: Path = PHASE7_RULES_PATH,
    wf_folds_path: Path = WF_FOLDS_PATH,
    wf_rules_path: Path = WF_RULES_PATH,
) -> tuple[pd.DataFrame, list[int], pd.DataFrame, pd.DataFrame]:
    holdout_years = validate_holdout_years(holdout_years)
    folds, rule_df = load_walk_forward_artifacts(
        wf_folds_path=Path(wf_folds_path),
        wf_rules_path=Path(wf_rules_path),
        holdout_years=holdout_years,
    )
    wf_years = sorted(int(y) for y in folds["test_year"].tolist())

    df = load_cache(Path(cache_path))
    phase7_rules = load_phase7_rules(Path(phase7_rules_path))

    methods: list[dict] = []

    fixed_specs = [
        {
            "method_id": "phase7_live_portfolio",
            "label": "Phase 7 OP/CD rule-component basket",
            "method_type": "fixed portfolio",
            "rules": phase7_rules,
            "op_focus": False,
            "secondary_basis": "frozen replay on walk-forward test years",
            "note": "Frozen 3-rule baseline. BEL contributes zero 2024-2025 races, so the current holdout is effectively the OP+CD legs.",
        },
        {
            "method_id": "phase8_frozen_portfolio",
            "label": "Phase 8 frozen portfolio",
            "method_type": "fixed portfolio",
            "rules": PHASE8_FROZEN_RULES,
            "op_focus": False,
            "secondary_basis": "frozen replay on walk-forward test years",
            "note": "Frozen 7-rule Phase 8 basket. Useful as the headline multi-track challenger, but still full-history-mined before this replay.",
        },
        {
            "method_id": "op_durable_only",
            "label": "OP durable only",
            "method_type": "fixed OP rule",
            "rules": [r for r in phase7_rules if r["rule_id"] == "OP_DURABLE_K7"],
            "op_focus": True,
            "secondary_basis": "frozen replay on walk-forward test years",
            "note": "Largest-sample OP anchor. Lower upside than the refined OP variant, but materially more forward races.",
        },
        {
            "method_id": "op_refined_only",
            "label": "OP refined only",
            "method_type": "fixed OP rule",
            "rules": [r for r in PHASE8_FROZEN_RULES if r["rule_id"] == "OP_REFINED_K7"],
            "op_focus": True,
            "secondary_basis": "frozen replay on walk-forward test years",
            "note": "Higher-ROI OP variant with a much smaller forward sample. Treat as selective, not as the new default.",
        },
    ]

    for spec in fixed_specs:
        wf_stats = evaluate_fixed_method(df, spec["rules"], wf_years)
        holdout_stats = evaluate_fixed_method(df, spec["rules"], holdout_years)
        holdout_2024 = year_snapshot(holdout_stats, 2024)
        holdout_2025 = year_snapshot(holdout_stats, 2025)
        methods.append(
            {
                "method_id": spec["method_id"],
                "label": spec["label"],
                "method_type": spec["method_type"],
                "deployment_posture": DEPLOYMENT_POSTURE[spec["method_id"]],
                "op_focus": spec["op_focus"],
                "note": spec["note"],
                "secondary_basis": spec["secondary_basis"],
                "wf_races": wf_stats["races"],
                "wf_hits": wf_stats["hits"],
                "wf_wagered": wf_stats["wagered"],
                "wf_profit": wf_stats["profit"],
                "wf_roi": wf_stats["roi"],
                "wf_hit_rate": wf_stats["hit_rate"],
                "wf_positive_years": wf_stats["positive_years"],
                "wf_observed_years": wf_stats["observed_years"],
                "holdout_races": holdout_stats["races"],
                "holdout_hits": holdout_stats["hits"],
                "holdout_wagered": holdout_stats["wagered"],
                "holdout_profit": holdout_stats["profit"],
                "holdout_roi": holdout_stats["roi"],
                "holdout_hit_rate": holdout_stats["hit_rate"],
                "holdout_positive_years": holdout_stats["positive_years"],
                "holdout_observed_years": holdout_stats["observed_years"],
                "holdout_2024_roi": float(holdout_2024["roi"]),
                "holdout_2024_races": int(holdout_2024["races"]),
                "holdout_2024_profit": float(holdout_2024["profit"]),
                "holdout_2025_roi": float(holdout_2025["roi"]),
                "holdout_2025_races": int(holdout_2025["races"]),
                "holdout_2025_profit": float(holdout_2025["profit"]),
            }
        )

    selector_wf = dynamic_rows_from_folds(folds[folds["test_year"].isin(wf_years)])
    selector_holdout = dynamic_rows_from_folds(folds[folds["test_year"].isin(holdout_years)])
    selector_holdout_2024 = year_snapshot(selector_holdout, 2024)
    selector_holdout_2025 = year_snapshot(selector_holdout, 2025)
    methods.append(
        {
            "method_id": "train_only_selector",
            "label": "Train-only yearly selector",
            "method_type": "dynamic selector",
            "deployment_posture": DEPLOYMENT_POSTURE["train_only_selector"],
            "op_focus": False,
            "note": "The current honest selector baseline from walk_forward_validation.py. Historical context includes the pre-existing BEL bridge candidate in some earlier folds, but no new aliasing is added here.",
            "secondary_basis": "actual train-only walk-forward",
            "wf_races": selector_wf["races"],
            "wf_hits": selector_wf["hits"],
            "wf_wagered": selector_wf["wagered"],
            "wf_profit": selector_wf["profit"],
            "wf_roi": selector_wf["roi"],
            "wf_hit_rate": selector_wf["hit_rate"],
            "wf_positive_years": selector_wf["positive_years"],
            "wf_observed_years": selector_wf["observed_years"],
            "holdout_races": selector_holdout["races"],
            "holdout_hits": selector_holdout["hits"],
            "holdout_wagered": selector_holdout["wagered"],
            "holdout_profit": selector_holdout["profit"],
            "holdout_roi": selector_holdout["roi"],
            "holdout_hit_rate": selector_holdout["hit_rate"],
            "holdout_positive_years": selector_holdout["positive_years"],
            "holdout_observed_years": selector_holdout["observed_years"],
            "holdout_2024_roi": float(selector_holdout_2024["roi"]),
            "holdout_2024_races": int(selector_holdout_2024["races"]),
            "holdout_2024_profit": float(selector_holdout_2024["profit"]),
            "holdout_2025_roi": float(selector_holdout_2025["roi"]),
            "holdout_2025_races": int(selector_holdout_2025["races"]),
            "holdout_2025_profit": float(selector_holdout_2025["profit"]),
        }
    )

    op_switch_wf, op_switch_choices = dynamic_op_switch_rows(rule_df[rule_df["test_year"].isin(wf_years)])
    op_switch_holdout, holdout_switch_choices = dynamic_op_switch_rows(rule_df[rule_df["test_year"].isin(holdout_years)])
    op_switch_holdout_2024 = year_snapshot(op_switch_holdout, 2024)
    op_switch_holdout_2025 = year_snapshot(op_switch_holdout, 2025)
    switch_pairs = ", ".join(
        f"{int(row.test_year)}={row.rule_id}" for _, row in op_switch_choices.tail(min(4, len(op_switch_choices))).iterrows()
    )
    methods.append(
        {
            "method_id": "op_train_switch",
            "label": "OP train-score switch",
            "method_type": "dynamic OP selector",
            "deployment_posture": DEPLOYMENT_POSTURE["op_train_switch"],
            "op_focus": True,
            "note": f"Each year, pick the better-qualifying OP rule by train-only selection score. Recent picks: {switch_pairs}.",
            "secondary_basis": "actual train-only walk-forward",
            "wf_races": op_switch_wf["races"],
            "wf_hits": op_switch_wf["hits"],
            "wf_wagered": op_switch_wf["wagered"],
            "wf_profit": op_switch_wf["profit"],
            "wf_roi": op_switch_wf["roi"],
            "wf_hit_rate": op_switch_wf["hit_rate"],
            "wf_positive_years": op_switch_wf["positive_years"],
            "wf_observed_years": op_switch_wf["observed_years"],
            "holdout_races": op_switch_holdout["races"],
            "holdout_hits": op_switch_holdout["hits"],
            "holdout_wagered": op_switch_holdout["wagered"],
            "holdout_profit": op_switch_holdout["profit"],
            "holdout_roi": op_switch_holdout["roi"],
            "holdout_hit_rate": op_switch_holdout["hit_rate"],
            "holdout_positive_years": op_switch_holdout["positive_years"],
            "holdout_observed_years": op_switch_holdout["observed_years"],
            "holdout_2024_roi": float(op_switch_holdout_2024["roi"]),
            "holdout_2024_races": int(op_switch_holdout_2024["races"]),
            "holdout_2024_profit": float(op_switch_holdout_2024["profit"]),
            "holdout_2025_roi": float(op_switch_holdout_2025["roi"]),
            "holdout_2025_races": int(op_switch_holdout_2025["races"]),
            "holdout_2025_profit": float(op_switch_holdout_2025["profit"]),
        }
    )

    out_df = pd.DataFrame(methods)
    max_holdout_races = int(out_df["holdout_races"].max()) if not out_df.empty else 0
    out_df["score"] = out_df.apply(lambda row: conservative_score(row, max_holdout_races), axis=1)
    out_df = out_df.sort_values(
        ["score", "holdout_positive_years", "holdout_races", "holdout_roi", "wf_races"],
        ascending=[False, False, False, False, False],
    ).reset_index(drop=True)
    out_df.index = out_df.index + 1
    out_df.index.name = "rank"
    out_df = out_df.reset_index()
    return out_df, wf_years, folds, holdout_switch_choices


def build_json_payload(
    df: pd.DataFrame,
    holdout_years: list[int],
    wf_years: list[int],
    runtime_sec: float,
    family_rows: list[dict],
    csv_output_name: Optional[str] = None,
    md_output_name: Optional[str] = None,
    json_output_name: Optional[str] = None,
    source_paths: Optional[dict[str, Path]] = None,
    scorecard_json: Path = SCORECARD_JSON,
    current_evidence_json: Path = CURRENT_EVIDENCE_JSON,
) -> dict[str, Any]:
    ranked = df.sort_values(["rank"]).reset_index(drop=True)
    family_by_id = {str(row.get("family_id")): row for row in family_rows}
    selective_family = family_by_id.get("selective_rule_path", {})
    harville_family = family_by_id.get("harville_ranked", {})
    xgboost_family = family_by_id.get("xgboost_residual", {})
    scorecard_ranking_contract = load_scorecard_ranking_contract(scorecard_json)
    decision_change_gate_minimums = load_decision_change_gate_minimums(scorecard_json)
    current_operator_boundary = load_current_operator_boundary(current_evidence_json)
    scorecard_csv = Path(source_paths.get("forward_evidence_scorecard", SCORECARD_CSV)) if source_paths else SCORECARD_CSV

    payload = {
        "generated_by": "compare_main_approaches.py",
        "source_scope": "frozen 2024-2025 holdout replay, train-only walk-forward artifacts, forward-evidence scorecard CSV/JSON, current-evidence operator-boundary context, and method-family comparison context",
        "evidence_boundary": MACHINE_READABLE_EVIDENCE_BOUNDARY,
        "evidence_boundary_text": EVIDENCE_BOUNDARY,
        "holdout_years": [int(year) for year in holdout_years],
        "walk_forward_years": [int(year) for year in wf_years],
        "runtime_sec": float(round(runtime_sec, 2)),
        "source_files": source_file_fingerprints(source_paths=source_paths),
        "output_files": {
            "csv": csv_output_name or OUT_CSV.name,
            "markdown": md_output_name or OUT_MD.name,
            "json": json_output_name or OUT_JSON.name,
        },
        "row_count": int(len(ranked)),
        "ranked_rows": ranked.to_dict(orient="records"),
        "method_family_roles": {
            str(row.get("family_id")): {
                "label": str(row.get("label")),
                "role": str(row.get("role")),
                "current_anchor": row.get("current_anchor"),
                "primary_shadow": row.get("primary_shadow"),
                "primary_companion": row.get("primary_shadow"),
                "secondary_shadow": row.get("secondary_shadow"),
            }
            for row in family_rows
        },
        "method_family_evidence_debt": build_method_family_evidence_debt(
            selective_family,
            harville_family,
            xgboost_family,
            decision_change_gate_minimums,
        ),
        "op_challenger_diagnostic": build_op_challenger_diagnostic(
            selective_family,
            scorecard_csv=scorecard_csv,
            scorecard_json=scorecard_json,
        ),
        "decision_change_gate_minimums": decision_change_gate_minimums,
        "scorecard_ranking_contract": scorecard_ranking_contract,
        "scorecard_ranking_contract_read": "rank is tier-first conservative decision order; raw forward_trust/Score is evidence support inside posture, not an automatic promotion queue",
        "current_operator_boundary": current_operator_boundary,
        "decision_read": {
            "active_anchor": selective_family.get("current_anchor", "OP_DURABLE_K7"),
            "paper_companion": selective_family.get("primary_shadow", "CD_CORE_K8"),
            "closest_shadow": selective_family.get("secondary_shadow", "OP_REFINED_K7"),
            "harville_role": harville_family.get("role", "BENCHMARK ONLY"),
            "xgboost_role": xgboost_family.get("role", "RESEARCH ONLY"),
            "baq_boundary": "BAQ is not BEL; dormant BEL history is not transferable to BAQ",
            "posture_change_gate": "requires ROI-complete settled paper rows; anchor_displacement needs 30 same-candidate rows, phase8_promotion_review needs 20 shadow rows, and real_money_discussion needs 100 total settled rows; hashes and clean rerenders are provenance only",
        },
    }
    return json_safe(payload)



def main() -> None:
    start = time.perf_counter()
    args = parse_args()
    holdout_years = validate_holdout_years(args.holdout_years)
    cache_path = Path(args.cache_path)
    phase7_rules_path = Path(args.phase7_rules)
    wf_folds_path = Path(args.wf_folds)
    wf_rules_path = Path(args.wf_rules)
    scorecard_csv = Path(args.scorecard_csv)
    scorecard_json = Path(args.scorecard_json)
    current_evidence_json = Path(args.current_evidence_json)
    cross_family_csv = Path(args.cross_family_csv)
    backtest_csv = Path(args.backtest_csv)
    ab_json = Path(args.ab_json)
    csv_output = Path(args.csv_output)
    md_output = Path(args.md_output)
    json_output = Path(args.json_output)

    out_df, wf_years, _folds, _holdout_switch_choices = build_dataframe(
        holdout_years,
        cache_path=cache_path,
        phase7_rules_path=phase7_rules_path,
        wf_folds_path=wf_folds_path,
        wf_rules_path=wf_rules_path,
    )

    family_rows = load_method_family_rows(
        compare_rows=out_df.to_dict(orient="records"),
        cross_family_csv=cross_family_csv,
        backtest_csv=backtest_csv,
        ab_json=ab_json,
    )
    runtime_sec = round(float(args.runtime_sec if args.runtime_sec is not None else (time.perf_counter() - start)), 2)
    report = build_report(
        out_df,
        holdout_years,
        wf_years,
        runtime_sec,
        family_rows,
        csv_output_name=csv_output.name,
        md_output_name=md_output.name,
        json_output_name=json_output.name,
        scorecard_csv=scorecard_csv,
        scorecard_json=scorecard_json,
        current_evidence_json=current_evidence_json,
        source_paths={
            "phase5_race_cache": cache_path,
            "phase7_live_rules": phase7_rules_path,
            "walk_forward_folds": wf_folds_path,
            "walk_forward_rules": wf_rules_path,
            "forward_evidence_scorecard": scorecard_csv,
            "forward_evidence_scorecard_json": scorecard_json,
            "current_evidence_summary_json": current_evidence_json,
            "cross_family_decision_card": cross_family_csv,
            "backtest_summary": backtest_csv,
            "ab_downstream_comparison_results": ab_json,
        },
    )
    json_payload = build_json_payload(
        out_df,
        holdout_years,
        wf_years,
        runtime_sec,
        family_rows,
        csv_output_name=csv_output.name,
        md_output_name=md_output.name,
        json_output_name=json_output.name,
        source_paths={
            "phase5_race_cache": cache_path,
            "phase7_live_rules": phase7_rules_path,
            "walk_forward_folds": wf_folds_path,
            "walk_forward_rules": wf_rules_path,
            "forward_evidence_scorecard": scorecard_csv,
            "forward_evidence_scorecard_json": scorecard_json,
            "current_evidence_summary_json": current_evidence_json,
            "cross_family_decision_card": cross_family_csv,
            "backtest_summary": backtest_csv,
            "ab_downstream_comparison_results": ab_json,
        },
        scorecard_json=scorecard_json,
        current_evidence_json=current_evidence_json,
    )

    csv_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(csv_output, index=False)
    md_output.write_text(report + "\n", encoding="utf-8")
    json_output.write_text(json.dumps(json_payload, indent=2) + "\n", encoding="utf-8")

    print(report)
    print(f"Saved: {csv_output.name}")
    print(f"Saved: {md_output.name}")
    print(f"Saved: {json_output.name}")


if __name__ == "__main__":
    main()
