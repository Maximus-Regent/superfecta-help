#!/usr/bin/env python3
"""
Build a compact OP-centered comparison artifact.

Purpose:
- keep OP_DURABLE_K7 visible as the safest current selective anchor
- show Harville and the current odds-only XGBoost path on the same cold-read page
- make the method-family guardrail easier to read without losing the OP focus
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

BASE = Path(__file__).resolve().parent
SCORECARD_CSV = BASE / "forward_evidence_scorecard.csv"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
COMPARE_CSV = BASE / "compare_main_approaches.csv"
METHOD_CSV = BASE / "method_family_decision_card.csv"
CROSS_FAMILY_CSV = BASE / "cross_family_decision_card.csv"
AB_JSON = BASE / "ab_downstream_comparison_results.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
OUT_MD = BASE / "OP_ANCHOR_METHOD_COMPARISON.md"
OUT_JSON = BASE / "op_anchor_method_comparison.json"
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
EXPECTED_REBUILD_ORDER_COMMANDS = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]

SOURCE_SCOPE = "read-only synthesis of frozen scorecard CSV/JSON, compare-main, method-family, cross-family, downstream A/B, and current-evidence bridge artifacts"
VALID_EVIDENCE_SCOPE = "split_aware_op_anchor_method_posture_comparison_only"
EVIDENCE_BOUNDARY = "source fingerprints prove exact input-byte provenance and render reproducibility only; they are not live paper-trade evidence, promotion readiness, live profitability, or real-money evidence"
EVIDENCE_BOUNDARY_TEXT = (
    "This OP-anchor method comparison is split-aware posture/reproducibility metadata only: "
    "it is not new forward evidence, a live paper-trade ledger, current-day scanner output, settled ROI, "
    "live profitability, promotion readiness, or real-money evidence. Source fingerprints are reproducibility "
    "metadata only, decision gates are forward-observation requirements rather than current evidence that a gate has been cleared, "
    "and the current-paper snapshot is operator-routing context only; current PAPER_TRADE_NOW instructions must go through "
    "the combined CURRENT_EVIDENCE_SUMMARY operator_status_context/source_freshness/operator_read_gate route before use."
)
MACHINE_READABLE_EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "OP-anchor method comparison artifact",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "forward_evidence_scorecard.csv",
        "forward_evidence_scorecard.json",
        "compare_main_approaches.csv",
        "method_family_decision_card.csv",
        "cross_family_decision_card.csv",
        "ab_downstream_comparison_results.json",
        "current_evidence_summary.json",
    ],
    "valid_use": "split-aware OP-anchor, Harville benchmark, current odds-only XGBoost posture audit, and current paper-status caveat from source-fingerprinted artifacts",
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
        "decision_gate_progress",
        "rebuild_validation_contract",
    ],
    "current_operator_routing_requires_combined_route": True,
    "current_operator_routing_is_source_readiness_not_performance": True,
    "source_fingerprints_are_reproducibility_metadata_only": True,
    "decision_gates_are_forward_observation_requirements_not_current_evidence": True,
    "current_operator_boundary_snapshot_is_context_only": True,
    "stronger_forward_confidence_requires": [
        "qualifying live paper signals",
        "ROI-complete settled paper rows",
        "20+ ROI-complete settled shadow rows before Phase 8 promotion review",
        "30+ ROI-complete same-candidate paper rows before anchor-displacement review",
        "settlement-quality checks",
        "other real forward observations",
    ],
    "non_goals": [
        "do not use OP-anchor comparison cleanliness as settled ROI",
        "do not promote OP_REFINED_K7 from this artifact",
        "do not reopen current odds-only XGBoost from this artifact",
        "do not treat Harville benchmark-only output as a live approach",
        "do not substitute BAQ for BEL",
        "do not discuss real-money scaling from this artifact",
        "do not quote current PAPER_TRADE_NOW instructions from this artifact; use the combined operator_status_context/source_freshness/operator_read_gate route from CURRENT_EVIDENCE_SUMMARY instead",
        "do not treat the copied current-evidence operator snapshot as settled ROI or bet readiness",
    ],
}
SOURCE_LABELS = {
    "forward_evidence_scorecard": SCORECARD_CSV,
    "forward_evidence_scorecard_json": SCORECARD_JSON,
    "compare_main_approaches": COMPARE_CSV,
    "method_family_decision_card": METHOD_CSV,
    "cross_family_decision_card": CROSS_FAMILY_CSV,
    "ab_downstream_comparison_results": AB_JSON,
    "current_evidence_summary": CURRENT_EVIDENCE_JSON,
}

REQUIRED_SCORECARD_COLUMNS = {
    "rule_id",
    "holdout_roi",
    "holdout_races",
    "holdout_2024_roi",
    "holdout_2024_races",
    "holdout_2025_roi",
    "holdout_2025_races",
    "wf_selected_count",
    "wf_total_folds",
    "ci_lower",
    "note",
}
REQUIRED_SCORECARD_RULES = {"OP_DURABLE_K7", "OP_REFINED_K7"}
REQUIRED_SCORECARD_JSON_PATHS = {
    "decision_gate_minimums.anchor_displacement.also_requires",
    "decision_gate_minimums.anchor_displacement.does_not_count",
    "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
    "decision_gate_minimums.anchor_displacement.observation_scope",
    "decision_gate_minimums.phase8_promotion_review.also_requires",
    "decision_gate_minimums.phase8_promotion_review.does_not_count",
    "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
    "decision_gate_minimums.phase8_promotion_review.observation_scope",
    "decision_gate_minimums.real_money_discussion.also_requires",
    "decision_gate_minimums.real_money_discussion.does_not_count",
    "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
    "ranking_contract.rank_is_tier_first_decision_order",
    "ranking_contract.forward_trust_is_secondary_within_tier",
    "ranking_contract.raw_score_is_not_an_automatic_deployment_instruction",
    "ranking_contract.known_rank_override",
    "ranking_standard",
}
REQUIRED_COMPARE_COLUMNS = {
    "method_id",
    "label",
    "deployment_posture",
    "holdout_roi",
    "holdout_races",
    "holdout_2024_roi",
    "holdout_2024_races",
    "holdout_2025_roi",
    "holdout_2025_races",
    "wf_roi",
    "wf_races",
    "secondary_basis",
}
REQUIRED_COMPARE_METHODS = {"phase7_live_portfolio"}
REQUIRED_METHOD_COLUMNS = {
    "family_id",
    "role",
    "primary_metric_label",
    "primary_metric",
    "primary_sample",
    "secondary_metric_label",
    "secondary_metric",
    "note",
}
REQUIRED_METHOD_ROWS = {"harville_ranked", "xgboost_residual"}
REQUIRED_CROSS_COLUMNS = {
    "shadow_rank",
    "rule_id",
    "family",
    "phase",
    "role",
    "holdout_roi",
    "holdout_races",
    "holdout_2024_roi",
    "holdout_2024_races",
    "holdout_2025_roi",
    "holdout_2025_races",
    "wf_selected_count",
    "wf_total_folds",
    "ci_lower",
    "forward_trust",
    "scorecard_tier",
    "decision_reason",
    "promotion_blocker",
    "family_caution",
    "note",
}
REQUIRED_CROSS_RANKS = {"LIVE_DEFAULT", "PRIMARY_SHADOW", "SECONDARY_SHADOW"}
REQUIRED_AB_PATHS = {
    "ev_engine_comparison.baseline.ev_pass_count",
    "ev_engine_comparison.enriched.ev_pass_count",
    "ev_engine_comparison.delta.ev_pass_count_delta",
    "ev_engine_comparison.delta.ev_pass_count_relative_change_pct",
    "ev_engine_comparison.delta.ev_pass_pct_point_delta",
}
REQUIRED_CURRENT_GATE_PROGRESS_FIELDS = {
    "source_path",
    "source_json_path",
    "gate_status",
    "all_gates_ready",
    "primary_first_read",
    "op_anchor_same_candidate_review",
    "phase8_promotion_review",
    "real_money_discussion",
    "read",
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
    p = argparse.ArgumentParser(description="Build the OP-anchor method comparison artifact")
    p.add_argument("--scorecard-csv", default=str(SCORECARD_CSV), help="forward evidence scorecard CSV path")
    p.add_argument("--scorecard-json", default=str(SCORECARD_JSON), help="forward evidence scorecard JSON path")
    p.add_argument("--compare-csv", default=str(COMPARE_CSV), help="compare-main CSV path")
    p.add_argument("--method-csv", default=str(METHOD_CSV), help="method-family decision CSV path")
    p.add_argument("--cross-family-csv", default=str(CROSS_FAMILY_CSV), help="cross-family decision CSV path")
    p.add_argument("--ab-json", default=str(AB_JSON), help="AB downstream comparison JSON path")
    p.add_argument("--current-evidence-json", default=str(CURRENT_EVIDENCE_JSON), help="current evidence bridge JSON path")
    p.add_argument("--md-output", default=str(OUT_MD), help="Markdown output path")
    p.add_argument("--json-output", default=str(OUT_JSON), help="JSON output path")
    return p.parse_args()


def require_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)


def require_columns(df: pd.DataFrame, required: set[str], source_path: Path, label: str) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{source_path.name} is missing required {label} columns: {', '.join(missing)}")


def require_index_rows(df: pd.DataFrame, required: set[str], source_path: Path, label: str) -> None:
    missing = sorted(required - set(df.index.astype(str)))
    if missing:
        raise ValueError(f"{source_path.name} is missing required {label} rows: {', '.join(missing)}")


def require_nested_path(payload: dict, dotted_path: str, source_path: Path) -> None:
    current = payload
    for part in dotted_path.split('.'):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"{source_path.name} is missing required JSON path: {dotted_path}")
        current = current[part]


def require_positive_int(value: Any, dotted_path: str, source_path: Path) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{source_path.name} JSON path must be a positive integer: {dotted_path}")
    return value


def require_str(value: Any, dotted_path: str, source_path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{source_path.name} JSON path must be a non-empty string: {dotted_path}")
    return value


def require_str_list(value: Any, dotted_path: str, source_path: Path) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise ValueError(f"{source_path.name} JSON path must be a non-empty string list: {dotted_path}")
    return list(value)


def require_ci_only_promotion_diagnostic(
    scorecard_payload: dict[str, Any],
    candidate_rule: str,
    anchor_rule: str,
    scorecard_json_path: Path = SCORECARD_JSON,
) -> dict[str, Any]:
    diagnostics = scorecard_payload.get("ci_only_promotion_diagnostics")
    if not isinstance(diagnostics, dict):
        raise ValueError(f"{scorecard_json_path.name} is missing ci_only_promotion_diagnostics")
    diagnostic = diagnostics.get(candidate_rule)
    if not isinstance(diagnostic, dict):
        raise ValueError(f"{scorecard_json_path.name} is missing ci_only_promotion_diagnostics.{candidate_rule}")
    if diagnostic.get("candidate_rule_id") != candidate_rule:
        raise ValueError(
            f"{scorecard_json_path.name} ci_only_promotion_diagnostics.{candidate_rule}.candidate_rule_id "
            f"must equal {candidate_rule}"
        )
    if diagnostic.get("current_anchor_rule_id") != anchor_rule:
        raise ValueError(
            f"{scorecard_json_path.name} ci_only_promotion_diagnostics.{candidate_rule}.current_anchor_rule_id "
            f"must equal {anchor_rule}"
        )
    if diagnostic.get("positive_ci_lower_bound_is_support_context") is not True:
        raise ValueError(
            f"{scorecard_json_path.name} ci_only_promotion_diagnostics.{candidate_rule} must mark "
            "positive_ci_lower_bound_is_support_context=true"
        )
    if diagnostic.get("ci_only_promotion_allowed") is not False:
        raise ValueError(
            f"{scorecard_json_path.name} ci_only_promotion_diagnostics.{candidate_rule} must mark "
            "ci_only_promotion_allowed=false"
        )
    require_str_list(
        diagnostic.get("why_not"),
        f"ci_only_promotion_diagnostics.{candidate_rule}.why_not",
        scorecard_json_path,
    )
    required_before_review = diagnostic.get("required_before_review")
    if not isinstance(required_before_review, dict) or not all(
        isinstance(required_before_review.get(key), str) and required_before_review.get(key, "").strip()
        for key in ("phase8_promotion_review", "anchor_displacement")
    ):
        raise ValueError(
            f"{scorecard_json_path.name} JSON path must include string review requirements: "
            f"ci_only_promotion_diagnostics.{candidate_rule}.required_before_review"
        )
    require_str_list(
        diagnostic.get("does_not_count"),
        f"ci_only_promotion_diagnostics.{candidate_rule}.does_not_count",
        scorecard_json_path,
    )
    return json.loads(json.dumps(diagnostic))


def build_anchor_review_policy(scorecard_payload: dict[str, Any], scorecard_json_path: Path = SCORECARD_JSON) -> dict[str, Any]:
    gate_minimums = scorecard_payload["decision_gate_minimums"]
    anchor_gate = gate_minimums["anchor_displacement"]
    phase8_gate = gate_minimums["phase8_promotion_review"]
    real_money_gate = gate_minimums["real_money_discussion"]

    phase8_min = require_positive_int(
        phase8_gate.get("min_roi_complete_settled_observations"),
        "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
        scorecard_json_path,
    )
    anchor_min = require_positive_int(
        anchor_gate.get("min_roi_complete_settled_observations"),
        "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
        scorecard_json_path,
    )
    real_money_min = require_positive_int(
        real_money_gate.get("min_total_settled_observations_with_usable_roi"),
        "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
        scorecard_json_path,
    )
    phase8_scope = require_str(
        phase8_gate.get("observation_scope"),
        "decision_gate_minimums.phase8_promotion_review.observation_scope",
        scorecard_json_path,
    )
    anchor_scope = require_str(
        anchor_gate.get("observation_scope"),
        "decision_gate_minimums.anchor_displacement.observation_scope",
        scorecard_json_path,
    )
    source_does_not_count = {
        "anchor_displacement": require_str_list(
            anchor_gate.get("does_not_count"),
            "decision_gate_minimums.anchor_displacement.does_not_count",
            scorecard_json_path,
        ),
        "phase8_promotion_review": require_str_list(
            phase8_gate.get("does_not_count"),
            "decision_gate_minimums.phase8_promotion_review.does_not_count",
            scorecard_json_path,
        ),
        "real_money_discussion": require_str_list(
            real_money_gate.get("does_not_count"),
            "decision_gate_minimums.real_money_discussion.does_not_count",
            scorecard_json_path,
        ),
    }
    source_also_requires = {
        "anchor_displacement": require_str_list(
            anchor_gate.get("also_requires"),
            "decision_gate_minimums.anchor_displacement.also_requires",
            scorecard_json_path,
        ),
        "phase8_promotion_review": require_str_list(
            phase8_gate.get("also_requires"),
            "decision_gate_minimums.phase8_promotion_review.also_requires",
            scorecard_json_path,
        ),
        "real_money_discussion": require_str_list(
            real_money_gate.get("also_requires"),
            "decision_gate_minimums.real_money_discussion.also_requires",
            scorecard_json_path,
        ),
    }
    does_not_count = sorted(
        {
            "frozen holdout rows",
            "clean scans",
            "open signals",
            "another odds-only rerun",
            *source_does_not_count["anchor_displacement"],
            *source_does_not_count["phase8_promotion_review"],
            *source_does_not_count["real_money_discussion"],
        }
    )
    return {
        "source_path": Path(scorecard_json_path).name,
        "source_json_path": "decision_gate_minimums",
        "phase8_promotion_review_min_roi_complete_settled_rows": phase8_min,
        "phase8_promotion_review_scope": phase8_scope,
        "anchor_displacement_review_min_roi_complete_same_candidate_rows": anchor_min,
        "anchor_displacement_review_scope": anchor_scope,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "policy_read": (
            f"{Path(scorecard_json_path).name} decision_gate_minimums says {phase8_min} ROI-complete "
            f"settled shadow rows can only open a Phase 8 promotion review; an OP anchor-displacement "
            f"discussion still needs {anchor_min}+ ROI-complete same-candidate paper observations plus "
            f"a cleaner split-aware read and equal-or-better walk-forward support; real-money discussion "
            f"stays out of scope until {real_money_min}+ total settled observations with usable ROI, payout sanity, "
            "concentration checks, and no BAQ-as-BEL substitution."
        ),
        "does_not_count": does_not_count,
        "source_gate_also_requires": source_also_requires,
        "source_gate_does_not_count": source_does_not_count,
    }


def file_fingerprint(path: Path) -> dict[str, Any]:
    data = Path(path).read_bytes()
    return {
        "path": Path(path).name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def md_cell(text: Any) -> str:
    return str(text).replace("|", "\\|")


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
    upstream_refresh_order = contract.get("upstream_refresh_order")
    if not isinstance(upstream_refresh_order, list):
        raise ValueError(f"{source_name} rebuild_validation_contract.upstream_refresh_order must be a list")
    commands = [
        str(row.get("command") or "")
        for row in upstream_refresh_order
        if isinstance(row, dict)
    ]
    if commands != EXPECTED_REBUILD_ORDER_COMMANDS:
        raise ValueError(f"{source_name} rebuild_validation_contract upstream order drifted")
    if contract.get("prerequisite_rebuild_command") != EXPECTED_REBUILD_ORDER_COMMANDS[0]:
        raise ValueError(f"{source_name} rebuild_validation_contract prerequisite command drifted")
    if contract.get("rebuild_command") != EXPECTED_REBUILD_ORDER_COMMANDS[1]:
        raise ValueError(f"{source_name} rebuild_validation_contract rebuild command drifted")
    if contract.get("direct_validation_command") != EXPECTED_REBUILD_ORDER_COMMANDS[2]:
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
    return json.loads(json.dumps(contract))


def load_current_operator_boundary(current_evidence_json: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    current_evidence_json = Path(current_evidence_json)
    source_name = current_evidence_json.name
    payload = json.loads(current_evidence_json.read_text(encoding="utf-8"))
    if not has_timezone_aware_timestamp(payload.get("generated_at")):
        raise ValueError(f"{source_name} generated_at must be timezone-aware ISO provenance metadata")
    operator_read_gate = validate_operator_read_gate(payload, source_name)
    scorecard_audit_route = validate_scorecard_audit_route(payload, source_name)
    rebuild_validation_contract = validate_rebuild_validation_contract(payload, source_name)

    def require_dict(value: Any, path: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError(f"{source_name} missing {path}")
        return value

    source_freshness = require_dict(payload.get("source_freshness"), "source_freshness")
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
    refresh_action_boundary = require_dict(
        source_freshness.get("refresh_action_boundary"),
        "source_freshness.refresh_action_boundary",
    )
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
    current_paper = require_dict(payload.get("current_paper_status"), "current_paper_status")
    operator_status_context = require_dict(
        current_paper.get("operator_status_context"),
        "current_paper_status.operator_status_context",
    )
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
    best_action = require_dict(current_paper.get("best_action"), "current_paper_status.best_action")
    primary = require_dict(current_paper.get("primary"), "current_paper_status.primary")
    first_read = require_dict(primary.get("first_read"), "current_paper_status.primary.first_read")
    anchor_gap = require_dict(
        primary.get("anchor_settlement_gap"),
        "current_paper_status.primary.anchor_settlement_gap",
    )
    open_queue = require_dict(
        primary.get("open_settlement_queue_by_rule"),
        "current_paper_status.primary.open_settlement_queue_by_rule",
    )
    raw_rule_progress = primary.get("rule_progress")
    if not isinstance(raw_rule_progress, list):
        raise ValueError(f"{source_name} missing current_paper_status.primary.rule_progress")
    rule_progress = {
        str(row.get("rule_id")): row
        for row in raw_rule_progress
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
        f"instructions from this OP-anchor artifact; recommended command="
        f"{operator_read_gate.get('recommended_command')}."
    )

    return {
        "source_path": current_evidence_json.name,
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
        "scorecard_audit_route": scorecard_audit_route,
        "rebuild_validation_contract": rebuild_validation_contract,
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
        "roi_complete_primary_rows": int(primary.get("roi_complete_settled") or 0),
        "first_read_threshold": int(first_read.get("threshold") or 0),
        "first_read_remaining": int(first_read.get("remaining") or 0),
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


def load_current_gate_progress(current_evidence_json: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    require_exists(current_evidence_json)
    payload = json.loads(Path(current_evidence_json).read_text(encoding="utf-8"))
    progress = payload.get("decision_gate_progress")
    if not isinstance(progress, dict):
        raise ValueError(f"{Path(current_evidence_json).name} is missing decision_gate_progress")
    missing = sorted(REQUIRED_CURRENT_GATE_PROGRESS_FIELDS - set(progress))
    if missing:
        raise ValueError(
            f"{Path(current_evidence_json).name} decision_gate_progress is missing fields: {', '.join(missing)}"
        )
    if progress.get("gate_status") != "all_uncleared":
        raise ValueError(f"{Path(current_evidence_json).name} decision_gate_progress must remain gate_status=all_uncleared")
    if progress.get("all_gates_ready") is not False:
        raise ValueError(f"{Path(current_evidence_json).name} decision_gate_progress must keep all_gates_ready=false")
    for flag in (
        "not_forward_performance_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_real_money_evidence",
    ):
        if progress.get(flag) is not True:
            raise ValueError(f"{Path(current_evidence_json).name} decision_gate_progress must mark {flag}=true")

    primary = progress.get("primary_first_read")
    anchor = progress.get("op_anchor_same_candidate_review")
    phase8 = progress.get("phase8_promotion_review")
    real_money = progress.get("real_money_discussion")
    if not all(isinstance(item, dict) for item in (primary, anchor, phase8, real_money)):
        raise ValueError(f"{Path(current_evidence_json).name} decision_gate_progress must publish structured gate-detail blocks")
    if (
        int(primary.get("current_rows", -1)) != 6
        or int(primary.get("threshold", -1)) != 30
        or primary.get("ready") is not False
    ):
        raise ValueError(
            f"{Path(current_evidence_json).name} decision_gate_progress primary_first_read must publish uncleared 6/30 progress"
        )
    if (
        anchor.get("candidate_rule_id") != "OP_DURABLE_K7"
        or int(anchor.get("current_rows", -1)) != 0
        or int(anchor.get("threshold", -1)) != 30
        or anchor.get("companion_rows_count_as_anchor_evidence") is not False
    ):
        raise ValueError(
            f"{Path(current_evidence_json).name} decision_gate_progress must publish OP_DURABLE_K7 same-candidate 0/30 progress"
        )
    if (
        int(phase8.get("weakest_current_rows", -1)) != 0
        or int(phase8.get("threshold_per_candidate", -1)) != 20
        or phase8.get("ready") is not False
    ):
        raise ValueError(
            f"{Path(current_evidence_json).name} decision_gate_progress must publish Phase 8 weakest 0/20 progress"
        )
    if (
        int(real_money.get("current_primary_roi_complete_rows", -1)) != 6
        or int(real_money.get("threshold", -1)) != 100
        or real_money.get("ready") is not False
    ):
        raise ValueError(
            f"{Path(current_evidence_json).name} decision_gate_progress must publish real-money discussion 6/100 progress"
        )
    read = str(progress.get("read") or "")
    for phrase in (
        "Gate progress: primary first-read 6/30",
        "OP anchor same-candidate 0/30",
        "Phase 8 weakest shadow 0/20",
        "real-money discussion floor 6/100",
        "All remain uncleared",
    ):
        if phrase not in read:
            raise ValueError(f"{Path(current_evidence_json).name} decision_gate_progress.read is missing {phrase!r}")
    return dict(progress)


def source_file_fingerprints(source_paths: dict[str, Path] | None = None) -> dict[str, dict[str, Any]]:
    paths = dict(SOURCE_LABELS)
    if source_paths:
        paths.update({label: Path(path) for label, path in source_paths.items()})
    return {label: file_fingerprint(path) for label, path in paths.items()}


def format_source_fingerprint_row(label: str, fingerprint: dict[str, Any]) -> str:
    return f"| {label} | `{fingerprint['path']}` | {fingerprint['bytes']} | `{fingerprint['sha256']}` |"



def build_payload(
    scorecard_csv: Path = SCORECARD_CSV,
    scorecard_json: Path = SCORECARD_JSON,
    compare_csv: Path = COMPARE_CSV,
    method_csv: Path = METHOD_CSV,
    cross_family_csv: Path = CROSS_FAMILY_CSV,
    ab_json: Path = AB_JSON,
    current_evidence_json: Path = CURRENT_EVIDENCE_JSON,
) -> dict:
    for path in [scorecard_csv, scorecard_json, compare_csv, method_csv, cross_family_csv, ab_json, current_evidence_json]:
        require_exists(path)

    scorecard_raw = pd.read_csv(scorecard_csv)
    require_columns(scorecard_raw, REQUIRED_SCORECARD_COLUMNS, scorecard_csv, "scorecard")
    scorecard = scorecard_raw.set_index("rule_id")
    require_index_rows(scorecard, REQUIRED_SCORECARD_RULES, scorecard_csv, "scorecard")

    scorecard_payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
    for dotted_path in sorted(REQUIRED_SCORECARD_JSON_PATHS):
        require_nested_path(scorecard_payload, dotted_path, scorecard_json)
    scorecard_ranking_contract = dict(scorecard_payload["ranking_contract"])
    if scorecard_ranking_contract.get("rank_is_tier_first_decision_order") is not True:
        raise ValueError(f"{scorecard_json.name} ranking_contract no longer marks rank_is_tier_first_decision_order=true")
    if scorecard_ranking_contract.get("forward_trust_is_secondary_within_tier") is not True:
        raise ValueError(f"{scorecard_json.name} ranking_contract no longer marks forward_trust_is_secondary_within_tier=true")
    if scorecard_ranking_contract.get("raw_score_is_not_an_automatic_deployment_instruction") is not True:
        raise ValueError(f"{scorecard_json.name} ranking_contract no longer says raw score is not an automatic deployment instruction")
    if "CD_CORE_K8 ranks ahead of OP_REFINED_K7" not in str(scorecard_ranking_contract.get("known_rank_override") or ""):
        raise ValueError(f"{scorecard_json.name} ranking_contract no longer preserves the CD_CORE_K8 over OP_REFINED_K7 tier-first override")
    anchor_review_policy = build_anchor_review_policy(scorecard_payload, scorecard_json)
    scorecard_ci_diagnostic = require_ci_only_promotion_diagnostic(
        scorecard_payload,
        candidate_rule="OP_REFINED_K7",
        anchor_rule="OP_DURABLE_K7",
        scorecard_json_path=scorecard_json,
    )
    decision_gate_minimums = dict(scorecard_payload["decision_gate_minimums"])

    compare_raw = pd.read_csv(compare_csv)
    require_columns(compare_raw, REQUIRED_COMPARE_COLUMNS, compare_csv, "compare-main")
    compare_df = compare_raw.set_index("method_id")
    require_index_rows(compare_df, REQUIRED_COMPARE_METHODS, compare_csv, "compare-main")

    method_raw = pd.read_csv(method_csv)
    require_columns(method_raw, REQUIRED_METHOD_COLUMNS, method_csv, "method-family")
    method_df = method_raw.set_index("family_id")
    require_index_rows(method_df, REQUIRED_METHOD_ROWS, method_csv, "method-family")

    cross_df = pd.read_csv(cross_family_csv)
    require_columns(cross_df, REQUIRED_CROSS_COLUMNS, cross_family_csv, "cross-family")
    present_cross_ranks = set(cross_df["shadow_rank"].astype(str))
    missing_cross_ranks = sorted(REQUIRED_CROSS_RANKS - present_cross_ranks)
    if missing_cross_ranks:
        raise ValueError(
            f"{cross_family_csv.name} is missing required cross-family shadow ranks: {', '.join(missing_cross_ranks)}"
        )

    ab = json.loads(ab_json.read_text(encoding="utf-8"))
    for dotted_path in sorted(REQUIRED_AB_PATHS):
        require_nested_path(ab, dotted_path, ab_json)

    current_operator_boundary = load_current_operator_boundary(current_evidence_json)
    current_gate_progress = load_current_gate_progress(current_evidence_json)

    source_fingerprints = source_file_fingerprints(
        {
            "forward_evidence_scorecard": scorecard_csv,
            "forward_evidence_scorecard_json": scorecard_json,
            "compare_main_approaches": compare_csv,
            "method_family_decision_card": method_csv,
            "cross_family_decision_card": cross_family_csv,
            "ab_downstream_comparison_results": ab_json,
            "current_evidence_summary": current_evidence_json,
        }
    )

    op_anchor = scorecard.loc["OP_DURABLE_K7"]
    op_refined = scorecard.loc["OP_REFINED_K7"]
    phase7 = compare_df.loc["phase7_live_portfolio"]
    harville = method_df.loc["harville_ranked"]
    xgb = method_df.loc["xgboost_residual"]

    ev_base = ab["ev_engine_comparison"]["baseline"]
    ev_enriched = ab["ev_engine_comparison"]["enriched"]
    ev_delta = ab["ev_engine_comparison"]["delta"]
    cross_by_shadow = {row["shadow_rank"]: row for _, row in cross_df.iterrows() if str(row.get("shadow_rank", ""))}
    primary_shadow = str(cross_by_shadow["PRIMARY_SHADOW"]["rule_id"])
    secondary_shadow = str(cross_by_shadow["SECONDARY_SHADOW"]["rule_id"])
    if not primary_shadow or not secondary_shadow:
        raise ValueError(f"{cross_family_csv.name} has blank rule_id values for required shadow ranks")
    paper_context_order = [
        (
            "LIVE_DEFAULT",
            "Safest current OP anchor",
            "Anchor role stays separate from companion or promotion review.",
        ),
        (
            "PRIMARY_SHADOW",
            "Primary OP/CD paper-basket companion",
            "Paper-basket companion is not an anchor replacement.",
        ),
        (
            "SECONDARY_SHADOW",
            "Closest same-family OP shadow challenger",
            "Shadow status stays below the 20-row promotion-review and 30-row anchor-displacement gates.",
        ),
    ]
    paper_basket_context = []
    for shadow_rank, lane_read, gate_read in paper_context_order:
        row = cross_by_shadow[shadow_rank]
        paper_basket_context.append(
            {
                "shadow_rank": shadow_rank,
                "rule_id": str(row["rule_id"]),
                "family": str(row["family"]),
                "phase": str(row["phase"]),
                "role": str(row["role"]),
                "lane_read": lane_read,
                "scorecard_tier": str(row["scorecard_tier"]),
                "holdout_roi": float(row["holdout_roi"]),
                "holdout_races": int(row["holdout_races"]),
                "holdout_2024_roi": float(row["holdout_2024_roi"]),
                "holdout_2024_races": int(row["holdout_2024_races"]),
                "holdout_2025_roi": float(row["holdout_2025_roi"]),
                "holdout_2025_races": int(row["holdout_2025_races"]),
                "wf_selected_count": int(row["wf_selected_count"]),
                "wf_total_folds": int(row["wf_total_folds"]),
                "ci_lower": float(row["ci_lower"]),
                "forward_trust": float(row["forward_trust"]),
                "decision_reason": str(row["decision_reason"]),
                "promotion_blocker": str(row["promotion_blocker"]),
                "family_caution": str(row["family_caution"]),
                "note": str(row["note"]),
                "gate_read": gate_read,
            }
        )

    payload = {
        "evidence_boundary": MACHINE_READABLE_EVIDENCE_BOUNDARY,
        "evidence_boundary_text": EVIDENCE_BOUNDARY_TEXT,
        "anchor_review_policy": anchor_review_policy,
        "scorecard_decision_gate_minimums": decision_gate_minimums,
        "scorecard_ranking_contract": scorecard_ranking_contract,
        "scorecard_ranking_standard": scorecard_payload["ranking_standard"],
        "scorecard_generated_at": scorecard_payload.get("generated_at"),
        "current_operator_boundary": current_operator_boundary,
        "current_gate_progress": current_gate_progress,
        "current_read": {
            "summary": (
                "OP_DURABLE_K7 remains the safest current selective anchor because it still has the largest real holdout sample in the paper-candidate lane and the strongest walk-forward selection frequency, even though its own recent holdout path was uneven (2024 -47.41% on 68, 2025 +124.61% on 47) and its bootstrap CI lower bound is still -3.40%, while Harville still loses badly on a huge benchmark sample and the current odds-only XGBoost path still turns modest prediction gains into worse downstream conservative EV pass-through (-7 passes, -3.93% relative, -0.0315 percentage points of test winners); "
                f"{anchor_review_policy['phase8_promotion_review_min_roi_complete_settled_rows']} ROI-complete shadow rows can open only a Phase 8 promotion review, not an OP anchor-displacement discussion, which still needs {anchor_review_policy['anchor_displacement_review_min_roi_complete_same_candidate_rows']}+ ROI-complete same-candidate paper observations plus a cleaner split-aware read and equal-or-better walk-forward support; current settled paper context remains CD-only with OP_DURABLE_K7 at 0 ROI-complete settled rows, so it is not OP-anchor forward evidence."
            ),
            "anchor_rule": "OP_DURABLE_K7",
            "primary_shadow": primary_shadow,
            "primary_companion": primary_shadow,
            "secondary_shadow": secondary_shadow,
            "selective_family_context": str(phase7["label"]),
            "paper_basket_context_read": "structured cross-family context keeps OP_DURABLE_K7, CD_CORE_K8, and OP_REFINED_K7 in separate anchor / companion / shadow lanes before comparing Harville or current odds-only XGBoost",
            "scorecard_rank_contract_read": "inherits the forward scorecard tier-first ranking contract: raw forward_trust/Score is support context inside a tier, not an automatic promotion queue",
        },
        "paper_basket_context": paper_basket_context,
        "rows": [
            {
                "approach_id": "op_durable_k7_anchor",
                "label": "OP_DURABLE_K7",
                "role": "ANCHOR",
                "scope": "selective OP rule",
                "evidence_class": "frozen 2024-2025 holdout + walk-forward frequency",
                "primary_metric_label": "2024-2025 holdout ROI",
                "primary_metric": float(op_anchor["holdout_roi"]),
                "primary_sample_label": "holdout races",
                "primary_sample": int(op_anchor["holdout_races"]),
                "holdout_2024_metric": float(op_anchor["holdout_2024_roi"]),
                "holdout_2024_sample": int(op_anchor["holdout_2024_races"]),
                "holdout_2025_metric": float(op_anchor["holdout_2025_roi"]),
                "holdout_2025_sample": int(op_anchor["holdout_2025_races"]),
                "secondary_metric_label": "walk-forward folds selected",
                "secondary_metric": f"{int(op_anchor['wf_selected_count'])}/{int(op_anchor['wf_total_folds'])}",
                "ci_lower": float(op_anchor["ci_lower"]),
                "supporting_note": str(op_anchor["note"]),
                "why": "Safest current anchor because it has the biggest forward sample among paper-candidate rules and the strongest walk-forward selection frequency in the OP family, but the 2024-2025 path was uneven rather than smooth and the bootstrap CI lower bound still crosses zero.",
            },
            {
                "approach_id": "harville_ranked_benchmark",
                "label": "Harville-ranked probabilities",
                "role": str(harville["role"]),
                "scope": "broad benchmark family",
                "evidence_class": "large-sample broad-family backtest benchmark",
                "primary_metric_label": str(harville["primary_metric_label"]),
                "primary_metric": float(harville["primary_metric"]),
                "primary_sample_label": "races",
                "primary_sample": int(harville["primary_sample"]),
                "secondary_metric_label": str(harville["secondary_metric_label"]),
                "secondary_metric": f"{float(harville['secondary_metric']):.2f}%",
                "supporting_note": str(harville["note"]),
                "why": "Useful structural benchmark only. High hit rate does not rescue a deeply negative ROI on a huge sample.",
            },
            {
                "approach_id": "xgboost_residual_research",
                "label": "XGBoost residual correction",
                "role": str(xgb["role"]),
                "scope": "ML correction family",
                "evidence_class": "negative betting read + downstream EV A/B check",
                "primary_metric_label": str(xgb["primary_metric_label"]),
                "primary_metric": float(xgb["primary_metric"]),
                "primary_sample_label": "races",
                "primary_sample": int(xgb["primary_sample"]),
                "secondary_metric_label": "matched downstream read",
                "secondary_metric": (
                    f"{float(xgb['secondary_metric']):.2f}% payout RMSE improvement, "
                    f"EV winner passes -{abs(int(ev_delta['ev_pass_count_delta']))} "
                    f"({float(ev_delta['ev_pass_count_relative_change_pct']):+.2f}%; {float(ev_delta['ev_pass_pct_point_delta']):+.4f}pp) "
                    f"from {int(ev_base['ev_pass_count'])} to {int(ev_enriched['ev_pass_count'])}"
                ),
                "supporting_note": str(xgb["note"]),
                "why": "Prediction quality improves a bit, but the paper-betting case still does not improve because the downstream conservative EV picture stays tiny and slightly worse on pass counts.",
            },
        ],
        "anchor_context": {
            "phase7_label": str(phase7["label"]),
            "phase7_role": str(phase7["deployment_posture"]),
            "phase7_holdout_roi": float(phase7["holdout_roi"]),
            "phase7_holdout_races": int(phase7["holdout_races"]),
            "phase7_holdout_2024_roi": float(phase7["holdout_2024_roi"]),
            "phase7_holdout_2024_races": int(phase7["holdout_2024_races"]),
            "phase7_holdout_2025_roi": float(phase7["holdout_2025_roi"]),
            "phase7_holdout_2025_races": int(phase7["holdout_2025_races"]),
            "phase7_wf_roi": float(phase7["wf_roi"]),
            "phase7_wf_races": int(phase7["wf_races"]),
            "phase7_secondary_basis": str(phase7["secondary_basis"]),
            "phase7_secondary_read_note": "That broader selective-family secondary line is replay context only, not extra train-only validation.",
            "op_refined_holdout_roi": float(op_refined["holdout_roi"]),
            "op_refined_holdout_races": int(op_refined["holdout_races"]),
            "op_refined_wf_selected": f"{int(op_refined['wf_selected_count'])}/{int(op_refined['wf_total_folds'])}",
            "op_anchor_ci_lower": float(op_anchor["ci_lower"]),
        },
        "op_challenger_diagnostic": {
            "anchor_rule": "OP_DURABLE_K7",
            "challenger_rule": "OP_REFINED_K7",
            "anchor_holdout_races": int(op_anchor["holdout_races"]),
            "challenger_holdout_races": int(op_refined["holdout_races"]),
            "challenger_sample_ratio_pct": round(100.0 * float(op_refined["holdout_races"]) / float(op_anchor["holdout_races"]), 2),
            "challenger_sample_deficit_races": int(op_anchor["holdout_races"]) - int(op_refined["holdout_races"]),
            "anchor_wf_selected_count": int(op_anchor["wf_selected_count"]),
            "challenger_wf_selected_count": int(op_refined["wf_selected_count"]),
            "wf_selection_deficit_folds": int(op_anchor["wf_selected_count"]) - int(op_refined["wf_selected_count"]),
            "anchor_ci_lower": float(op_anchor["ci_lower"]),
            "challenger_ci_lower": float(op_refined["ci_lower"]),
            "challenger_has_higher_aggregate_holdout_roi": bool(float(op_refined["holdout_roi"]) > float(op_anchor["holdout_roi"])),
            "challenger_has_positive_ci_lower": bool(float(op_refined["ci_lower"]) > 0),
            "challenger_losing_holdout_years": ["2024"] if float(op_refined["holdout_2024_roi"]) < 0 else [],
            "ci_only_promotion_allowed": bool(scorecard_ci_diagnostic["ci_only_promotion_allowed"]),
            "ci_only_promotion_blockers": [
                "smaller holdout sample",
                "losing 2024 holdout split",
                "lower walk-forward selection frequency",
                "separate 20-row promotion-review and 30-row anchor-displacement paper-observation gates not cleared",
            ],
            "ci_only_promotion_read": (
                "A positive bootstrap CI lower bound is useful support context, but it is not enough by itself "
                "to promote OP_REFINED_K7 or displace OP_DURABLE_K7 because the challenger still has a smaller "
                "holdout sample, a losing 2024 split, lower walk-forward recurrence, and no ROI-complete paper "
                "observations clearing the separate promotion or anchor-review gates."
            ),
            "scorecard_ci_only_diagnostic_source": (
                f"{scorecard_json.name}:ci_only_promotion_diagnostics.OP_REFINED_K7"
            ),
            "scorecard_ci_only_promotion_diagnostic": scorecard_ci_diagnostic,
            "diagnostic_read": "OP_REFINED_K7 has the hotter aggregate holdout ROI and positive bootstrap CI lower bound, but it is still only 49 holdout races (42.61% of the OP_DURABLE_K7 sample), lost 2024, and has only 2/10 walk-forward selections versus 7/10 for the anchor; treat this as shadow evidence until the separate 20-row promotion-review and 30-row anchor-displacement paper-observation gates are actually met.",
        },
        "guardrail": {
            "paper_now": "Selective rule path",
            "anchor": "OP_DURABLE_K7",
            "primary_shadow": primary_shadow,
            "primary_companion": primary_shadow,
            "secondary_shadow": secondary_shadow,
            "benchmark_only": "Harville-ranked probabilities",
            "research_only": "XGBoost residual correction",
        },
        "decision_gates": [
            {
                "gate": "same-family OP challenger",
                "current_rule": "Keep OP_DURABLE_K7 as anchor; keep OP_REFINED_K7 shadow-only.",
                "evidence_required_before_change": f"Collect {anchor_review_policy['phase8_promotion_review_min_roi_complete_settled_rows']}+ ROI-complete settled shadow observations for OP_REFINED_K7 before even a Phase 8 promotion review; an anchor-displacement discussion needs {anchor_review_policy['anchor_displacement_review_min_roi_complete_same_candidate_rows']}+ ROI-complete same-candidate paper observations plus a cleaner split-aware read and equal-or-better walk-forward support than OP_DURABLE_K7, not merely a hotter aggregate ROI.",
                "evidence_scope": f"Future settled `phase8_shadow` paper-trade ledger rows with complete ROI coverage; the {anchor_review_policy['phase8_promotion_review_min_roi_complete_settled_rows']}-row promotion-review gate and {anchor_review_policy['anchor_displacement_review_min_roi_complete_same_candidate_rows']}-row anchor-displacement gate are separate, and historical replay or holdout rows do not count as new promotion or anchor-displacement evidence.",
            },
            {
                "gate": "current odds-only XGBoost reopening",
                "current_rule": "Keep the current odds-only XGBoost path parked.",
                "evidence_required_before_change": "Reopen only if the evidence class changes materially, such as horse-specific features or a downstream EV pass-through improvement that creates a paper-betting case; do not rerun odds-only tuning as if it were new evidence.",
                "evidence_scope": "A materially different feature/data class plus downstream betting pass-through; another odds-only rerun is not a new evidence class.",
            },
            {
                "gate": "BEL/BAQ substitution",
                "current_rule": "Keep BEL dormant and do not substitute BAQ for BEL.",
                "evidence_required_before_change": "Wait for Belmont forward races; BAQ remains a separate track because the BEL->BAQ bridge failed the strict chronological read.",
                "evidence_scope": "Fresh Belmont qualifying races only; BAQ needs independent evidence and cannot inherit BEL history.",
            },
            {
                "gate": "real-money scaling",
                "current_rule": "Paper trade only.",
                "evidence_required_before_change": f"Do not consider real-money scaling until {anchor_review_policy['real_money_discussion_min_total_settled_observations_with_usable_roi']}+ paper observations have settled with positive ROI plus concentration and payout-distribution checks.",
                "evidence_scope": "Settled paper-trade ledger observations with usable ROI coverage, not clean scans, open signals, or replay backtests.",
            },
        ],
        "source_provenance": {
            "source_scope": SOURCE_SCOPE,
            "evidence_boundary": EVIDENCE_BOUNDARY,
            "source_fingerprints": source_fingerprints,
        },
    }
    return payload



def build_markdown(
    payload: dict,
    scorecard_csv_name: str = SCORECARD_CSV.name,
    scorecard_json_name: str = SCORECARD_JSON.name,
    compare_csv_name: str = COMPARE_CSV.name,
    method_csv_name: str = METHOD_CSV.name,
    cross_family_csv_name: str = CROSS_FAMILY_CSV.name,
    ab_json_name: str = AB_JSON.name,
    current_evidence_json_name: str = CURRENT_EVIDENCE_JSON.name,
    md_output_name: str = OUT_MD.name,
    json_output_name: str = OUT_JSON.name,
) -> str:
    rows = payload["rows"]
    anchor_context = payload["anchor_context"]
    challenger_diagnostic = payload["op_challenger_diagnostic"]
    current = payload["current_read"]
    current_operator_boundary = payload["current_operator_boundary"]
    current_gate_progress = payload["current_gate_progress"]
    if current_operator_boundary["operator_read_gate"].get("requires_refresh_before_evidence_read"):
        operator_gate_boundary_read = (
            "The saved top card must be refreshed before evidence/instruction use; this read gate is not "
            "no-target evidence, clean-empty evidence, OP-anchor proof, bet readiness, settled ROI, "
            "promotion readiness, live profitability, bankroll guidance, or real-money evidence"
        )
        combined_route_boundary_read = (
            "The combined route is refresh-before-instruction/evidence-read routing only; do not quote "
            "current PAPER_TRADE_NOW instructions from this artifact as no-target, clean-empty, bet-readiness, "
            "settled ROI, OP-anchor proof, promotion, live-profitability, bankroll, or real-money evidence"
        )
    else:
        operator_gate_boundary_read = (
            "The saved top card can be read as current operator routing context only; this read gate is not "
            "no-target evidence, clean-empty evidence, OP-anchor proof, bet readiness, settled ROI, "
            "promotion readiness, live profitability, bankroll guidance, or real-money evidence"
        )
        combined_route_boundary_read = (
            "The combined route is instruction/evidence-read routing only; do not quote current "
            "PAPER_TRADE_NOW instructions from this artifact as no-target, clean-empty, bet-readiness, "
            "settled ROI, OP-anchor proof, promotion, live-profitability, bankroll, or real-money evidence"
        )
    paper_basket_context = payload["paper_basket_context"]
    decision_gates = payload.get("decision_gates", [])
    evidence_boundary = payload["evidence_boundary"]
    evidence_boundary_text = payload["evidence_boundary_text"]
    anchor_review_policy = payload["anchor_review_policy"]
    scorecard_ranking_contract = payload["scorecard_ranking_contract"]
    source_provenance = payload["source_provenance"]
    source_fingerprints = source_provenance["source_fingerprints"]

    lines = [
        "# OP Anchor vs Harville vs XGBoost",
        "",
        "This artifact puts the strongest current OP anchor beside the two broad method families that still tend to resurface in discussion: Harville-ranked probabilities and the current XGBoost residual correction path.",
        "",
        "## Guardrail",
        "",
        "- This is a deployment-posture comparison, not an apples-to-apples research contest.",
        "- `OP_DURABLE_K7` stays the safest current anchor unless new forward evidence clearly beats it.",
        f"- `{current['primary_companion']}` is the primary OP/CD paper-basket companion, while `{current['secondary_shadow']}` remains the smaller same-family OP shadow challenger rather than a promoted default.",
        "- Harville remains `BENCHMARK ONLY`, and XGBoost remains `RESEARCH ONLY`.",
        "- Do not reopen the current odds-only XGBoost path unless the evidence class changes materially (for example new horse-specific features or a real downstream EV improvement); the current odds-only version is a parked dead end for now.",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {evidence_boundary['artifact_role']}",
        f"- `valid_evidence_scope={evidence_boundary['valid_evidence_scope']}`",
        f"- Valid use: {evidence_boundary['valid_use']}",
        f"- Machine-readable boundary text: {evidence_boundary_text}",
        "- This artifact is a split-aware posture/reproducibility audit only: it is not new forward evidence, a live paper-trade ledger, current-day scanner output, settled ROI, live profitability, promotion readiness, or real-money evidence.",
        "- Source fingerprints are reproducibility metadata only; decision gates are forward-observation requirements, not current evidence that a gate has been cleared.",
        f"- Scorecard ranking contract inherited: tier-first rank is `{scorecard_ranking_contract['rank_is_tier_first_decision_order']}`; raw score is not an automatic deployment instruction (`{scorecard_ranking_contract['raw_score_is_not_an_automatic_deployment_instruction']}`). {scorecard_ranking_contract['known_rank_override']}",
        "- Stronger forward confidence still requires qualifying live paper signals, ROI-complete settled paper rows, settlement-quality checks, or other real forward observations.",
        f"- Anchor-review policy: {anchor_review_policy['policy_read']}",
        f"- Decision-gate source: `{anchor_review_policy['source_path']}` `{anchor_review_policy['source_json_path']}` (`phase8_promotion_review={anchor_review_policy['phase8_promotion_review_min_roi_complete_settled_rows']}`, `anchor_displacement={anchor_review_policy['anchor_displacement_review_min_roi_complete_same_candidate_rows']}`, `real_money_discussion={anchor_review_policy['real_money_discussion_min_total_settled_observations_with_usable_roi']}`).",
        f"- Current-paper snapshot source: `{current_operator_boundary['source_path']}`; this snapshot is operator routing and settlement coverage context only, not new OP-anchor evidence.",
        "- Non-goals: do not promote OP_REFINED_K7, reopen current odds-only XGBoost, treat Harville as live, substitute BAQ for BEL, quote current PAPER_TRADE_NOW instructions without the combined CURRENT_EVIDENCE_SUMMARY operator_status_context/source_freshness/operator_read_gate route, or discuss real-money scaling from this artifact.",
        "",
        "## Current Read",
        "",
        f"- {current['summary']}",
        f"- Current paper-companion read: `{current['primary_companion']}` is the primary OP/CD paper-basket companion and `{current['secondary_shadow']}` is the stronger same-family OP shadow challenger, so the paper hierarchy is more specific than just `selective beats Harville/XGBoost`.",
        f"- Paper-basket context read: {current['paper_basket_context_read']}.",
        f"- Scorecard rank-contract read: {current['scorecard_rank_contract_read']}; this is why a hotter raw OP_REFINED_K7 score still does not automatically displace the paper-basket companion or the OP anchor.",
        "- This table keeps the OP anchor split-aware on purpose so a mixed 2024/2025 path does not get flattened into one smoother aggregate holdout number.",
        f"- Anchor caution: `OP_DURABLE_K7` is still the safest current anchor, not a statistically clean slam dunk; its bootstrap 95% CI lower bound is still `{anchor_context['op_anchor_ci_lower']:+.2f}%`.",
        f"- Anchor-review threshold: {anchor_review_policy['policy_read']}",
        "",
        "## Current Paper Snapshot",
        "",
        f"This small snapshot is copied from `{current_operator_boundary['source_path']}` so the OP-anchor comparison can show the current paper-lane caveat without becoming a live-performance surface.",
        "",
        "| Field | Current snapshot | Boundary |",
        "|---|---|---|",
        f"| Combined operator route | {md_cell(current_operator_boundary['combined_operator_route_read'])} Operator context read = {md_cell(current_operator_boundary['operator_status_context_read'])}; ops bucket = `{current_operator_boundary['operator_status_context_ops_day_bucket']}` | {combined_route_boundary_read} |",
        f"| Source freshness | `{current_operator_boundary['right_now_freshness_state']}`; refresh before right-now use = `{current_operator_boundary['requires_refresh_before_right_now_use']}`; bridge reference = `{current_operator_boundary['source_freshness_generated_reference_date']}` (`{current_operator_boundary['source_freshness_generated_reference_timezone']}`); comparison = `{current_operator_boundary['source_freshness_staleness_comparison_source']}` / `{current_operator_boundary['source_freshness_staleness_comparison_date']}`; read = {md_cell(current_operator_boundary['source_freshness_read'])} | Source freshness is operator-readiness metadata, not performance proof |",
        f"| Refresh action boundary | `{current_operator_boundary['refresh_action_command']}` required before right-now use = `{current_operator_boundary['refresh_required_before_right_now_instruction_use']}`; settles rows / creates ROI evidence / clean-empty performance = `{current_operator_boundary['refresh_can_settle_open_rows_by_itself']}` / `{current_operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}` / `{current_operator_boundary['clean_empty_refresh_counts_as_forward_performance']}` | Wrapper refresh is operator routing only; it is not settled ROI, promotion readiness, live profitability, or real-money evidence |",
        f"| Operator read gate | `{current_operator_boundary['source_path']}` `operator_read_gate`: {md_cell(current_operator_boundary['operator_read_gate']['read'])} Gate status = `{current_operator_boundary['operator_read_gate']['gate_status']}`; recommended command = `{current_operator_boundary['operator_read_gate']['recommended_command']}` | {operator_gate_boundary_read} |",
        f"| Bridge-published gate progress | `{current_evidence_json_name}` `decision_gate_progress`: {md_cell(current_gate_progress['read'])} Source: `{current_gate_progress['source_path']}` `{current_gate_progress['source_json_path']}`; gate status = `{current_gate_progress['gate_status']}` | Current gates are all uncleared routing context only; they do not create settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
        f"| Scorecard audit route | `{current_operator_boundary['source_path']}` `scorecard_audit_route`: {md_cell(current_operator_boundary['scorecard_audit_route']['route_read'])} Validator: `{current_operator_boundary['scorecard_audit_route']['validator_command']}`; artifacts: `{current_operator_boundary['scorecard_audit_route']['markdown_path']}` / `{current_operator_boundary['scorecard_audit_route']['json_path']}`; gate snapshot = 30/20/100 with no-BAQ-as-BEL required `{current_operator_boundary['scorecard_audit_route']['gate_floor_snapshot']['real_money_no_baq_as_bel_required']}` | Report-synchronization route only; it is not forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
        f"| Current bridge rebuild order | `{current_operator_boundary['source_path']}` `rebuild_validation_contract`: `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes | Provenance/rebuild route only; green checks and rebuild order are not settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
        f"| Current settled rule mix | OP_DURABLE_K7={current_operator_boundary['op_anchor_roi_complete_rows']}; CD_CORE_K8={current_operator_boundary['cd_companion_roi_complete_rows']}; {md_cell(current_operator_boundary['primary_rule_mix_read'])} | Rule-specific settled rows stay separate; CD-only paper rows are not OP-anchor forward evidence |",
        f"| OP-anchor settlement gap | {md_cell(current_operator_boundary['anchor_settlement_gap_read'])} | Companion rows do not reduce the OP-anchor same-candidate review gap |",
        f"| Settlement queue state | `{current_operator_boundary['open_settlement_queue_state']}`; {md_cell(current_operator_boundary['open_settlement_context'])}; detail: {md_cell(current_operator_boundary['open_settlement_queue_read'])} | Open rows are settlement workflow only; fill outcomes from result/payout evidence before interpreting ROI |",
        f"| Operator route | `{current_operator_boundary['best_action_command']}` | Use the bridge route to settle or refresh; do not infer profit, promotion, or real-money readiness from the route itself |",
        "",
        "## Paper Basket / Shadow Context",
        "",
        "This table keeps the current selective rule lanes visible before the broader method-family comparison. It is sourced from `cross_family_decision_card.csv` and remains posture context only.",
        "",
        "| Rule | Lane | Split-aware evidence | WF | CI lower | Why now | What does not change |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in paper_basket_context:
        split = (
            f"{row['holdout_roi']:+.2f}% on {row['holdout_races']}; "
            f"2024 {row['holdout_2024_roi']:+.2f}% on {row['holdout_2024_races']}, "
            f"2025 {row['holdout_2025_roi']:+.2f}% on {row['holdout_2025_races']}"
        )
        lines.append(
            f"| {row['rule_id']} | {row['lane_read']} ({row['role']}, {row['phase']}) | {split} | "
            f"{row['wf_selected_count']}/{row['wf_total_folds']} | {row['ci_lower']:+.2f}% | "
            f"{row['decision_reason']} | {row['gate_read']} {row['promotion_blocker']} |"
        )

    lines.extend(
        [
            "",
            "## Comparison Table",
            "",
            "| Approach | Role | Evidence class | Primary evidence | Sample | Secondary evidence | Why it sits here |",
            "|---|---|---|---:|---:|---|---|",
        ]
    )

    for row in rows:
        if row["approach_id"] == "op_durable_k7_anchor":
            primary = (
                f"{row['primary_metric']:+.2f}% ({row['primary_metric_label']}; "
                f"2024 {row['holdout_2024_metric']:+.2f}% on {row['holdout_2024_sample']}, "
                f"2025 {row['holdout_2025_metric']:+.2f}% on {row['holdout_2025_sample']})"
            )
        else:
            primary = f"{row['primary_metric']:+.2f}% ({row['primary_metric_label']})"
        secondary = f"{row['secondary_metric']} ({row['secondary_metric_label']})"
        lines.append(
            f"| {row['label']} | {row['role']} | {row['evidence_class']} | {primary} | {row['primary_sample']} | {secondary} | {row['why']} |"
        )

    lines.extend(
        [
            "",
            "## Why OP_DURABLE_K7 Still Holds the Anchor",
            "",
            f"- `OP_DURABLE_K7` current forward read: `+{rows[0]['primary_metric']:.2f}%` holdout on `{rows[0]['primary_sample']}` races, but with an uneven split of `2024 {rows[0]['holdout_2024_metric']:+.2f}% on {rows[0]['holdout_2024_sample']}` and `2025 {rows[0]['holdout_2025_metric']:+.2f}% on {rows[0]['holdout_2025_sample']}`, plus `7/10` walk-forward folds selected.",
            f"- Anchor caution: the bootstrap 95% CI lower bound for `OP_DURABLE_K7` is still `{anchor_context['op_anchor_ci_lower']:+.2f}%`, so “safest current anchor” is a deployment ranking, not proof of a clean positive lower-bound edge.",
            f"- `{current['primary_companion']}` is still the primary OP/CD paper-basket companion because it stayed paper-worthy without displacing the anchor, while `OP_REFINED_K7` remains the narrower same-family shadow challenger.",
            f"- `OP_REFINED_K7` remains interesting but not promoted: `+{anchor_context['op_refined_holdout_roi']:.2f}%` holdout on only `{anchor_context['op_refined_holdout_races']}` races, with `{anchor_context['op_refined_wf_selected']}` walk-forward selection.",
            f"- The broader selective family still has the strongest current deployment case through `{anchor_context['phase7_label']}` (`{anchor_context['phase7_role']}`) at `+{anchor_context['phase7_holdout_roi']:.2f}%` holdout on `{anchor_context['phase7_holdout_races']}` races, but that portfolio result was also uneven: `2024 {anchor_context['phase7_holdout_2024_roi']:+.2f}% on {anchor_context['phase7_holdout_2024_races']}` and `2025 {anchor_context['phase7_holdout_2025_roi']:+.2f}% on {anchor_context['phase7_holdout_2025_races']}`, with `+{anchor_context['phase7_wf_roi']:.2f}%` {anchor_context['phase7_secondary_basis']} on `{anchor_context['phase7_wf_races']}` races.",
            f"- {anchor_context['phase7_secondary_read_note']}",
            "",
            "## OP_REFINED_K7 Challenger Diagnostic",
            "",
            f"- {challenger_diagnostic['diagnostic_read']}",
            f"- Scorecard diagnostic source: `{challenger_diagnostic['scorecard_ci_only_diagnostic_source']}` (`ci_only_promotion_allowed={str(challenger_diagnostic['scorecard_ci_only_promotion_diagnostic']['ci_only_promotion_allowed']).lower()}`).",
            f"- Sample support: `{challenger_diagnostic['challenger_rule']}` has `{challenger_diagnostic['challenger_holdout_races']}` holdout races versus `{challenger_diagnostic['anchor_holdout_races']}` for `{challenger_diagnostic['anchor_rule']}` (`{challenger_diagnostic['challenger_sample_ratio_pct']:.2f}%` of the anchor sample; `{challenger_diagnostic['challenger_sample_deficit_races']}` fewer races).",
            f"- Walk-forward support: `{challenger_diagnostic['challenger_rule']}` was selected in `{challenger_diagnostic['challenger_wf_selected_count']}/10` folds versus `{challenger_diagnostic['anchor_wf_selected_count']}/10` for `{challenger_diagnostic['anchor_rule']}` (`{challenger_diagnostic['wf_selection_deficit_folds']}` fewer folds).",
            f"- CI nuance: `{challenger_diagnostic['challenger_rule']}` has a positive CI lower bound (`{challenger_diagnostic['challenger_ci_lower']:+.2f}%`) while `{challenger_diagnostic['anchor_rule']}` still crosses zero (`{challenger_diagnostic['anchor_ci_lower']:+.2f}%`), but the smaller sample, losing 2024 split, and lower walk-forward support keep it in shadow/watch mode rather than anchor status.",
            f"- CI-only promotion check: {challenger_diagnostic['ci_only_promotion_read']}",
            "",
            "## Why the Other Two Still Do Not Dislodge It",
            "",
            f"- Harville remains benchmark-only because its best honest family read is still negative on a huge sample: `{rows[1]['primary_metric']:+.2f}%` over `{rows[1]['primary_sample']}` races.",
            f"- The current odds-only XGBoost path remains research-only because its best betting line is still negative (`{rows[2]['primary_metric']:+.2f}%` on `{rows[2]['primary_sample']}` races), and its matched downstream read now says that better payout prediction still comes with weaker conservative EV pass-through rather than a paper-path upgrade.",
            "",
            "## What Would Change This Answer",
            "",
            "- A challenger only dislodges `OP_DURABLE_K7` with cleaner forward evidence: more holdout races or a meaningfully stronger split-aware holdout read plus equal-or-better walk-forward support, not just a hotter aggregate ROI on a smaller sample.",
            "- Harville stays parked unless a broad benchmark family flips positive on a large honest sample instead of only on a tiny slice or a prettier presentation layer.",
            "- The current odds-only XGBoost path stays parked unless the evidence class changes materially — for example through horse-specific features or a real downstream EV pass-through improvement that creates a paper-betting case. Until then, treat it as a dead end and move on.",
            "",
            "## Decision Gates Before Changing the Anchor",
            "",
            "These gates keep the OP decision tied to new forward observations rather than another prettier replay table.",
            "",
            "| Gate | Current rule | Evidence required before change | Evidence scope |",
            "|---|---|---|---|",
        ]
    )
    for gate in decision_gates:
        lines.append(
            f"| {gate['gate']} | {gate['current_rule']} | {gate['evidence_required_before_change']} | {gate['evidence_scope']} |"
        )

    lines.extend(
        [
            "",
            "## Bottom Line",
            "",
            "- If Cole wants one OP-centered answer right now, keep `OP_DURABLE_K7` as the safest anchor.",
            f"- Treat `{current['primary_companion']}` as the primary OP/CD paper-basket companion and `{current['secondary_shadow']}` as the smaller same-family shadow challenger, not as reasons to demote the anchor prematurely.",
            "- Keep the broader selective rule path as the only `PAPER NOW` family.",
            "- Keep Harville as the structural benchmark and XGBoost as research, not as live-decision challengers.",
            "- Park the current odds-only XGBoost path unless a materially different evidence class appears; the current version is a documented dead end, not a near-promotion candidate.",
            "",
            "## Source Provenance",
            "",
            "Exact input-byte fingerprints for this OP-anchor comparison. Use them as reproducibility metadata only; they do not prove live paper-trade edge, promotion readiness, live profitability, or real-money performance.",
            "",
            f"- Source scope: {source_provenance['source_scope']}",
            f"- Evidence boundary: {source_provenance['evidence_boundary']}.",
            "",
            "| Source | File | Bytes | SHA-256 |",
            "|---|---|---:|---|",
        ]
    )
    for label in sorted(source_fingerprints):
        lines.append(format_source_fingerprint_row(label, source_fingerprints[label]))

    lines.extend(
        [
            "",
            "## Validation",
            "",
            f"- Sources: `{scorecard_csv_name}`, `{scorecard_json_name}`, `{compare_csv_name}`, `{method_csv_name}`, `{cross_family_csv_name}`, `{ab_json_name}`, `{current_evidence_json_name}`",
            f"- Wrote: `{md_output_name}`, `{json_output_name}`",
            "- This artifact is a read-only synthesis of the frozen scorecard, decision cards, downstream A/B evidence, and the current-evidence bridge snapshot",
        ]
    )
    return "\n".join(lines) + "\n"



def main() -> int:
    args = parse_args()
    scorecard_csv = Path(args.scorecard_csv)
    scorecard_json = Path(args.scorecard_json)
    compare_csv = Path(args.compare_csv)
    method_csv = Path(args.method_csv)
    cross_family_csv = Path(args.cross_family_csv)
    ab_json = Path(args.ab_json)
    current_evidence_json = Path(args.current_evidence_json)
    md_output = Path(args.md_output)
    json_output = Path(args.json_output)

    payload = build_payload(
        scorecard_csv=scorecard_csv,
        scorecard_json=scorecard_json,
        compare_csv=compare_csv,
        method_csv=method_csv,
        cross_family_csv=cross_family_csv,
        ab_json=ab_json,
        current_evidence_json=current_evidence_json,
    )
    json_text = json.dumps(payload, indent=2) + "\n"
    markdown = build_markdown(
        payload,
        scorecard_csv_name=scorecard_csv.name,
        scorecard_json_name=scorecard_json.name,
        compare_csv_name=compare_csv.name,
        method_csv_name=method_csv.name,
        cross_family_csv_name=cross_family_csv.name,
        ab_json_name=ab_json.name,
        current_evidence_json_name=current_evidence_json.name,
        md_output_name=md_output.name,
        json_output_name=json_output.name,
    )
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json_text, encoding="utf-8")
    md_output.write_text(markdown, encoding="utf-8")
    print(markdown, end="")
    print(f"Saved: {md_output.name}")
    print(f"Saved: {json_output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
