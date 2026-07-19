#!/usr/bin/env python3
"""
Create a compact method-family comparison card.

Goal:
- line up Harville, the XGBoost correction path, and the strongest selective rule path
- keep the comparison honest about evidence scope
- make it easy to retire dead-end modeling paths in reports
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

BASE = Path(__file__).resolve().parent
COMPARE_MAIN = BASE / "compare_main_approaches.csv"
COMPARE_MAIN_JSON = BASE / "compare_main_approaches.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
BACKTEST_SUMMARY = BASE / "backtest_summary.csv"
AB_RESULTS = BASE / "ab_downstream_comparison_results.json"
CROSS_FAMILY_CSV = BASE / "cross_family_decision_card.csv"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
OUT_CSV = BASE / "method_family_decision_card.csv"
OUT_MD = BASE / "METHOD_FAMILY_DECISION.md"

VALID_EVIDENCE_SCOPE = "split_aware_method_family_hierarchy_only"

SOURCE_FINGERPRINT_PATHS = {
    "compare_main_approaches": COMPARE_MAIN,
    "compare_main_approaches_json": COMPARE_MAIN_JSON,
    "current_evidence_summary": CURRENT_EVIDENCE_JSON,
    "cross_family_decision_card": CROSS_FAMILY_CSV,
    "forward_evidence_scorecard": SCORECARD_JSON,
    "backtest_summary": BACKTEST_SUMMARY,
    "ab_downstream_comparison": AB_RESULTS,
}

REQUIRED_COMPARE_COLUMNS = {
    "method_id",
    "note",
    "wf_roi",
    "wf_races",
    "holdout_roi",
    "holdout_races",
    "holdout_2024_roi",
    "holdout_2024_races",
    "holdout_2025_roi",
    "holdout_2025_races",
}
REQUIRED_COMPARE_METHODS = {"phase7_live_portfolio", "train_only_selector"}
REQUIRED_CROSS_COLUMNS = {"rule_id", "shadow_rank"}
REQUIRED_CROSS_SHADOWS = {"LIVE_DEFAULT", "PRIMARY_SHADOW", "SECONDARY_SHADOW"}
REQUIRED_BACKTEST_COLUMNS = {"Strategy", "Races", "ROI%", "HitRate%"}
REQUIRED_BACKTEST_STRATEGIES = {"Harville-Top120"}
REQUIRED_AB_PATHS = {
    "prediction_accuracy.baseline.payout_rmse",
    "prediction_accuracy.baseline.log_ratio_rmse",
    "prediction_accuracy.enriched.payout_rmse",
    "prediction_accuracy.enriched.log_ratio_rmse",
    "ev_engine_comparison.baseline.ev_pass_count",
    "ev_engine_comparison.enriched.ev_pass_count",
    "ev_engine_comparison.delta.ev_pass_count_delta",
    "ev_engine_comparison.delta.ev_pass_count_relative_change_pct",
    "ev_engine_comparison.delta.ev_pass_pct_point_delta",
    "test_set.n_races",
}
REQUIRED_OPERATOR_BOUNDARY_FIELDS = {
    "source_path",
    "generated_at",
    "source_consistency_overall_match",
    "right_now_freshness_state",
    "requires_refresh_before_right_now_use",
    "source_freshness_read",
    "source_freshness_generated_reference_date",
    "source_freshness_generated_reference_timezone",
    "source_freshness_staleness_comparison_source",
    "source_freshness_staleness_comparison_date",
    "refresh_action_command",
    "refresh_required_before_right_now_instruction_use",
    "refresh_can_update_operator_surfaces",
    "refresh_can_settle_open_rows_by_itself",
    "refresh_counts_as_roi_complete_evidence_by_itself",
    "clean_empty_refresh_counts_as_forward_performance",
    "refresh_boundary_not_forward_performance_evidence",
    "refresh_boundary_not_promotion_readiness_evidence",
    "refresh_boundary_not_live_profitability_evidence",
    "refresh_boundary_not_real_money_evidence",
    "best_action_command",
    "open_settlement_summary",
    "open_settlement_context",
    "open_settlement_queue_state",
    "open_settlement_queue_read",
    "open_settlement_rows",
    "roi_complete_primary_rows",
    "first_read_threshold",
    "first_read_remaining",
    "op_anchor_roi_complete_rows",
    "cd_companion_roi_complete_rows",
    "current_settled_context_is_cd_only",
    "primary_rule_mix_read",
    "latest_context_has_no_bet_recommendations",
    "latest_context_has_bet_ready_language",
    "latest_context_has_no_qualifying_races",
    "latest_run_context",
    "recommendation_context_read",
    "not_forward_performance_evidence",
    "not_bet_readiness_evidence_by_itself",
    "operator_read_gate",
}
REQUIRED_OPERATOR_READ_GATE_TEXT_FIELDS = {
    "gate_status",
    "reason_text",
    "recommended_command",
    "valid_use",
    "read",
}
REQUIRED_OPERATOR_READ_GATE_BOOL_FIELDS = {
    "requires_refresh_before_evidence_read",
    "requires_source_freshness_refresh",
    "has_api_access_failure_context",
    "has_scanner_failure_boundary",
    "has_stale_cache_fallback_context",
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
}
REQUIRED_OPERATOR_BOUNDARY_TRUE_FLAGS = (
    "refresh_boundary_not_forward_performance_evidence",
    "refresh_boundary_not_promotion_readiness_evidence",
    "refresh_boundary_not_live_profitability_evidence",
    "refresh_boundary_not_real_money_evidence",
)
REQUIRED_OPERATOR_BOUNDARY_FALSE_FLAGS = (
    "refresh_can_settle_open_rows_by_itself",
    "refresh_counts_as_roi_complete_evidence_by_itself",
    "clean_empty_refresh_counts_as_forward_performance",
)
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
REQUIRED_SCORECARD_AUDIT_ROUTE_FIELDS = {
    "markdown_path",
    "json_path",
    "validator_command",
    "gate_floor_source",
    "gate_floor_snapshot",
    "route_read",
    "valid_use",
    "artifacts_present",
    "not_forward_performance_evidence",
    "not_settled_roi_evidence",
    "not_promotion_readiness_evidence",
    "not_live_profitability_evidence",
    "not_bankroll_guidance",
    "not_real_money_evidence",
}
REQUIRED_SCORECARD_AUDIT_ROUTE_TRUE_FLAGS = (
    "artifacts_present",
    "not_forward_performance_evidence",
    "not_settled_roi_evidence",
    "not_promotion_readiness_evidence",
    "not_live_profitability_evidence",
    "not_bankroll_guidance",
    "not_real_money_evidence",
)
REQUIRED_SCORECARD_AUDIT_ROUTE_READ_PHRASES = (
    "copied 30/20/100 gate floors",
    "tier-first ranking",
    "OP_REFINED CI-only support context",
    "generated-at timezone provenance",
    "no-BAQ-as-BEL prerequisite",
)
REQUIRED_REBUILD_REFRESH_ORDER = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]
REQUIRED_REBUILD_VALIDATION_TRUE_FLAGS = (
    "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
    "requires_source_consistency_before_quoting_current_totals",
    "requires_source_freshness_before_right_now_instruction_use",
    "green_checks_are_reproducibility_metadata_only",
    "upstream_refresh_order_is_provenance_metadata_only",
    "not_settled_roi_or_real_money_evidence",
)
EXPECTED_DECISION_GATE_SOURCES = {
    "phase8_promotion_review": (
        "minimum_roi_complete_settled_observations",
        "forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
    ),
    "anchor_displacement": (
        "minimum_roi_complete_same_candidate_observations",
        "forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
    ),
    "real_money_discussion": (
        "minimum_total_settled_roi_complete_observations",
        "forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
    ),
}
REQUIRED_DECISION_GATE_KEYS = (
    "anchor_displacement",
    "phase8_promotion_review",
    "real_money_discussion",
)
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY = "ci_only_promotion_diagnostics.OP_REFINED_K7"
REQUIRED_CI_ONLY_WHY_NOT = (
    "smaller holdout sample than OP_DURABLE_K7",
    "losing 2024 holdout split",
    "lower walk-forward recurrence than OP_DURABLE_K7",
    "uncleared phase8_promotion_review paper-observation gate",
    "uncleared anchor_displacement paper-observation gate",
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create the method-family decision card")
    p.add_argument("--compare-csv", default=str(COMPARE_MAIN), help="compare_main_approaches CSV path")
    p.add_argument("--compare-json", default=str(COMPARE_MAIN_JSON), help="compare_main_approaches JSON sidecar path")
    p.add_argument("--current-evidence-json", default=str(CURRENT_EVIDENCE_JSON), help="current evidence JSON sidecar path")
    p.add_argument("--cross-family-csv", default=str(CROSS_FAMILY_CSV), help="cross-family decision CSV path")
    p.add_argument("--scorecard-json", default=str(SCORECARD_JSON), help="forward evidence scorecard JSON path")
    p.add_argument("--backtest-csv", default=str(BACKTEST_SUMMARY), help="backtest summary CSV path")
    p.add_argument("--ab-json", default=str(AB_RESULTS), help="AB downstream comparison JSON path")
    p.add_argument("--csv-output", default=str(OUT_CSV), help="CSV output path")
    p.add_argument("--md-output", default=str(OUT_MD), help="Markdown output path")
    return p.parse_args()


def require_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required source file: {path}")


def fingerprint_file(path: Path) -> dict[str, Any]:
    require_exists(path)
    data = path.read_bytes()
    return {
        "path": path.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def source_file_fingerprints(source_paths: dict[str, Path] | None = None) -> dict[str, dict[str, Any]]:
    paths = source_paths or SOURCE_FINGERPRINT_PATHS
    return {label: fingerprint_file(path) for label, path in paths.items()}


def load_csv(path: Path) -> list[dict[str, str]]:
    require_exists(path)
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def require_columns(rows: list[dict[str, str]], required: set[str], source_path: Path, label: str) -> None:
    columns = set(rows[0].keys()) if rows else set()
    missing = sorted(required - columns)
    if missing:
        raise ValueError(f"{source_path.name} is missing required {label} columns: {', '.join(missing)}")


def require_keyed_rows(rows: list[dict[str, str]], key_field: str, required: set[str], source_path: Path, label: str) -> None:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        key = str(row.get(key_field, ""))
        grouped.setdefault(key, []).append(row)

    missing = sorted(key for key in required if key not in grouped)
    if missing:
        raise ValueError(f"{source_path.name} is missing required {label} rows: {', '.join(missing)}")

    conflicts: list[str] = []
    for key in sorted(required):
        row_group = grouped.get(key, [])
        normalized = {tuple(sorted(item.items())) for item in row_group}
        if len(normalized) > 1:
            conflicts.append(key)
    if conflicts:
        raise ValueError(f"{source_path.name} has conflicting duplicate {label} rows: {', '.join(conflicts)}")


def require_nested_path(payload: dict[str, Any], dotted_path: str, source_path: Path) -> None:
    current: Any = payload
    for part in dotted_path.split('.'):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"{source_path.name} is missing required JSON path: {dotted_path}")
        current = current[part]


def load_scorecard_ranking_contract(scorecard_json_path: Path = SCORECARD_JSON) -> dict[str, object]:
    require_exists(scorecard_json_path)
    payload = json.loads(scorecard_json_path.read_text(encoding="utf-8"))
    contract = payload.get("ranking_contract")
    if not isinstance(contract, dict):
        raise ValueError(f"{scorecard_json_path.name} is missing ranking_contract")
    if contract.get("rank_is_tier_first_decision_order") is not True:
        raise ValueError(f"{scorecard_json_path.name} ranking_contract no longer marks rank_is_tier_first_decision_order=true")
    if contract.get("forward_trust_is_secondary_within_tier") is not True:
        raise ValueError(f"{scorecard_json_path.name} ranking_contract no longer marks forward_trust_is_secondary_within_tier=true")
    if contract.get("raw_score_is_not_an_automatic_deployment_instruction") is not True:
        raise ValueError(f"{scorecard_json_path.name} ranking_contract no longer says raw score is not an automatic deployment instruction")
    if "CD_CORE_K8 ranks ahead of OP_REFINED_K7" not in str(contract.get("known_rank_override") or ""):
        raise ValueError(f"{scorecard_json_path.name} ranking_contract no longer preserves the CD_CORE_K8 over OP_REFINED_K7 tier-first override")
    return dict(contract)


def require_positive_non_bool_int(value: Any, *, field_name: str, scorecard_json_path: Path) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{scorecard_json_path.name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, field_name: str, scorecard_json_path: Path) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{scorecard_json_path.name} {field_name} must be a list of strings")
    return list(value)


def load_scorecard_decision_gate_minimums(scorecard_json_path: Path = SCORECARD_JSON) -> dict[str, dict[str, Any]]:
    require_exists(scorecard_json_path)
    payload = json.loads(scorecard_json_path.read_text(encoding="utf-8"))
    gate_payload = payload.get("decision_gate_minimums")
    if not isinstance(gate_payload, dict):
        raise ValueError(f"{scorecard_json_path.name} is missing decision_gate_minimums")
    missing = [key for key in REQUIRED_DECISION_GATE_KEYS if key not in gate_payload]
    if missing:
        raise ValueError(f"{scorecard_json_path.name} decision_gate_minimums missing required gates: {', '.join(missing)}")

    anchor = gate_payload["anchor_displacement"]
    phase8 = gate_payload["phase8_promotion_review"]
    real_money = gate_payload["real_money_discussion"]
    for gate_name, gate_value in (
        ("anchor_displacement", anchor),
        ("phase8_promotion_review", phase8),
        ("real_money_discussion", real_money),
    ):
        if not isinstance(gate_value, dict):
            raise ValueError(f"{scorecard_json_path.name} decision_gate_minimums.{gate_name} must be an object")
    if "min_roi_complete_settled_observations" not in anchor:
        raise ValueError(f"{scorecard_json_path.name} anchor_displacement gate is missing min_roi_complete_settled_observations")
    if "min_roi_complete_settled_observations" not in phase8:
        raise ValueError(f"{scorecard_json_path.name} phase8_promotion_review gate is missing min_roi_complete_settled_observations")
    if "min_total_settled_observations_with_usable_roi" not in real_money:
        raise ValueError(f"{scorecard_json_path.name} real_money_discussion gate is missing min_total_settled_observations_with_usable_roi")

    anchor_min = require_positive_non_bool_int(
        anchor["min_roi_complete_settled_observations"],
        field_name="decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
        scorecard_json_path=scorecard_json_path,
    )
    phase8_min = require_positive_non_bool_int(
        phase8["min_roi_complete_settled_observations"],
        field_name="decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
        scorecard_json_path=scorecard_json_path,
    )
    real_money_min = require_positive_non_bool_int(
        real_money["min_total_settled_observations_with_usable_roi"],
        field_name="decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
        scorecard_json_path=scorecard_json_path,
    )
    anchor_requires = require_string_list(
        anchor.get("also_requires", []),
        field_name="decision_gate_minimums.anchor_displacement.also_requires",
        scorecard_json_path=scorecard_json_path,
    )
    anchor_does_not_count = require_string_list(
        anchor.get("does_not_count", []),
        field_name="decision_gate_minimums.anchor_displacement.does_not_count",
        scorecard_json_path=scorecard_json_path,
    )
    phase8_requires = require_string_list(
        phase8.get("also_requires", []),
        field_name="decision_gate_minimums.phase8_promotion_review.also_requires",
        scorecard_json_path=scorecard_json_path,
    )
    phase8_does_not_count = require_string_list(
        phase8.get("does_not_count", []),
        field_name="decision_gate_minimums.phase8_promotion_review.does_not_count",
        scorecard_json_path=scorecard_json_path,
    )
    real_money_requires = require_string_list(
        real_money.get("also_requires", []),
        field_name="decision_gate_minimums.real_money_discussion.also_requires",
        scorecard_json_path=scorecard_json_path,
    )
    real_money_does_not_count = require_string_list(
        real_money.get("does_not_count", []),
        field_name="decision_gate_minimums.real_money_discussion.does_not_count",
        scorecard_json_path=scorecard_json_path,
    )
    if NO_BAQ_AS_BEL_PREREQUISITE not in real_money_requires:
        raise ValueError(
            f"{scorecard_json_path.name} decision_gate_minimums.real_money_discussion.also_requires "
            f"must include {NO_BAQ_AS_BEL_PREREQUISITE!r}"
        )

    return {
        "anchor_displacement": {
            "minimum_roi_complete_same_candidate_observations": anchor_min,
            "threshold_source": f"{scorecard_json_path.name}:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
            "observation_scope": str(anchor.get("observation_scope", "same candidate paper observations")),
            "also_requires": anchor_requires,
            "does_not_count": anchor_does_not_count,
        },
        "phase8_promotion_review": {
            "minimum_roi_complete_settled_observations": phase8_min,
            "threshold_source": f"{scorecard_json_path.name}:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
            "observation_scope": str(phase8.get("observation_scope", "candidate shadow observations")),
            "also_requires": phase8_requires,
            "does_not_count": phase8_does_not_count,
        },
        "real_money_discussion": {
            "minimum_total_settled_roi_complete_observations": real_money_min,
            "threshold_source": f"{scorecard_json_path.name}:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
            "also_requires": real_money_requires,
            "does_not_count": real_money_does_not_count,
        },
    }


def load_scorecard_ci_only_diagnostic(scorecard_json_path: Path = SCORECARD_JSON) -> dict[str, Any]:
    require_exists(scorecard_json_path)
    payload = json.loads(scorecard_json_path.read_text(encoding="utf-8"))
    diagnostics = payload.get("ci_only_promotion_diagnostics")
    if not isinstance(diagnostics, dict):
        raise ValueError(f"{scorecard_json_path.name} is missing ci_only_promotion_diagnostics")
    diagnostic = diagnostics.get("OP_REFINED_K7")
    if not isinstance(diagnostic, dict):
        raise ValueError(f"{scorecard_json_path.name} is missing {OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}")
    if diagnostic.get("candidate_rule_id") != "OP_REFINED_K7":
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic has the wrong candidate_rule_id")
    if diagnostic.get("current_anchor_rule_id") != "OP_DURABLE_K7":
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic has the wrong current_anchor_rule_id")
    if diagnostic.get("positive_ci_lower_bound_is_support_context") is not True:
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic must mark positive CI as support context")
    if diagnostic.get("ci_only_promotion_allowed") is not False:
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic must keep ci_only_promotion_allowed=false")
    why_not = require_string_list(
        diagnostic.get("why_not"),
        field_name=f"{OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}.why_not",
        scorecard_json_path=scorecard_json_path,
    )
    missing_why_not = [reason for reason in REQUIRED_CI_ONLY_WHY_NOT if reason not in why_not]
    if missing_why_not:
        raise ValueError(
            f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic missing blockers: {', '.join(missing_why_not)}"
        )
    required_before_review = diagnostic.get("required_before_review")
    if not isinstance(required_before_review, dict):
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic is missing required_before_review")
    for gate_name in ("phase8_promotion_review", "anchor_displacement"):
        if not str(required_before_review.get(gate_name) or "").strip():
            raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic missing {gate_name} review requirement")
    does_not_count = require_string_list(
        diagnostic.get("does_not_count"),
        field_name=f"{OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}.does_not_count",
        scorecard_json_path=scorecard_json_path,
    )
    if "positive bootstrap CI lower bound by itself" not in does_not_count:
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic must say positive CI alone does not count")
    return dict(diagnostic)


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


def validate_operator_read_gate(boundary: dict[str, Any], compare_json_path: Path) -> dict[str, Any]:
    gate = boundary.get("operator_read_gate")
    if not isinstance(gate, dict):
        raise ValueError(f"{compare_json_path.name} current_operator_boundary is missing operator_read_gate")
    missing_text = [
        field
        for field in REQUIRED_OPERATOR_READ_GATE_TEXT_FIELDS
        if not isinstance(gate.get(field), str) or not str(gate.get(field)).strip()
    ]
    missing_bool = [
        field
        for field in REQUIRED_OPERATOR_READ_GATE_BOOL_FIELDS
        if not isinstance(gate.get(field), bool)
    ]
    if missing_text or missing_bool:
        raise ValueError(
            f"{compare_json_path.name} current_operator_boundary.operator_read_gate missing fields: "
            f"{', '.join(missing_text + missing_bool)}"
        )
    gate_status = gate.get("gate_status")
    if gate_status not in {"refresh_required_before_evidence_read", "current_operator_routing_context_only"}:
        raise ValueError(
            f"{compare_json_path.name} current_operator_boundary.operator_read_gate.gate_status "
            "must be a known instruction/evidence-read state"
        )
    if gate.get("valid_use") != "operator instruction/evidence-read gating only":
        raise ValueError(f"{compare_json_path.name} current_operator_boundary.operator_read_gate.valid_use drifted")
    for flag in (
        "not_forward_performance_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_real_money_evidence",
    ):
        if gate.get(flag) is not True:
            raise ValueError(f"{compare_json_path.name} current_operator_boundary.operator_read_gate must mark {flag}=true")
    for flag in (
        "current_top_card_counts_as_no_target_evidence",
        "current_top_card_counts_as_clean_empty_evidence",
        "current_top_card_counts_as_bet_readiness_evidence",
        "current_top_card_counts_as_settled_roi_evidence",
    ):
        if gate.get(flag) is not False:
            raise ValueError(f"{compare_json_path.name} current_operator_boundary.operator_read_gate must mark {flag}=false")
    read = str(gate.get("read") or "")
    if gate_status == "refresh_required_before_evidence_read":
        if gate.get("recommended_command") != "./run_daily_portfolio_observation.sh":
            raise ValueError(
                f"{compare_json_path.name} current_operator_boundary.operator_read_gate must recommend "
                "./run_daily_portfolio_observation.sh"
            )
        required_refresh_flags = (
            "requires_refresh_before_evidence_read",
            "has_wrapper_refresh_action",
        )
        false_refresh_flags = [flag for flag in required_refresh_flags if gate.get(flag) is not True]
        if false_refresh_flags:
            raise ValueError(
                f"{compare_json_path.name} current_operator_boundary.operator_read_gate must mark "
                f"{', '.join(false_refresh_flags)}=true"
            )
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
            raise ValueError(
                f"{compare_json_path.name} current_operator_boundary.operator_read_gate refresh branch "
                "must publish a refresh cause"
            )
        for phrase in (
            "Refresh/recheck with `./run_daily_portfolio_observation.sh`",
            "not a no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money read",
        ):
            if phrase not in read:
                raise ValueError(f"{compare_json_path.name} current_operator_boundary.operator_read_gate.read is missing {phrase!r}")
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
                f"{compare_json_path.name} current_operator_boundary.operator_read_gate current branch "
                f"must mark {', '.join(true_refresh_flags)}=false"
            )
        for phrase in (
            "current operator routing context",
            "not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence",
        ):
            if phrase not in read:
                raise ValueError(f"{compare_json_path.name} current_operator_boundary.operator_read_gate.read is missing {phrase!r}")
    return dict(gate)


def load_current_operator_boundary(compare_json_path: Path = COMPARE_MAIN_JSON) -> dict[str, Any]:
    require_exists(compare_json_path)
    payload = json.loads(compare_json_path.read_text(encoding="utf-8"))
    boundary = payload.get("current_operator_boundary")
    if not isinstance(boundary, dict):
        raise ValueError(f"{compare_json_path.name} is missing current_operator_boundary")
    missing = sorted(REQUIRED_OPERATOR_BOUNDARY_FIELDS - set(boundary))
    if missing:
        raise ValueError(f"{compare_json_path.name} current_operator_boundary is missing fields: {', '.join(missing)}")
    if not has_timezone_aware_timestamp(boundary.get("generated_at")):
        raise ValueError(f"{compare_json_path.name} current_operator_boundary generated_at must be timezone-aware ISO provenance metadata")
    if boundary.get("not_forward_performance_evidence") is not True:
        raise ValueError(f"{compare_json_path.name} current_operator_boundary must mark not_forward_performance_evidence=true")
    if boundary.get("not_bet_readiness_evidence_by_itself") is not True:
        raise ValueError(f"{compare_json_path.name} current_operator_boundary must mark not_bet_readiness_evidence_by_itself=true")
    if boundary.get("refresh_can_update_operator_surfaces") is not True:
        raise ValueError(f"{compare_json_path.name} current_operator_boundary must preserve refresh_can_update_operator_surfaces=true")
    for flag in REQUIRED_OPERATOR_BOUNDARY_FALSE_FLAGS:
        if boundary.get(flag) is not False:
            raise ValueError(f"{compare_json_path.name} current_operator_boundary must preserve {flag}=false")
    for flag in REQUIRED_OPERATOR_BOUNDARY_TRUE_FLAGS:
        if boundary.get(flag) is not True:
            raise ValueError(f"{compare_json_path.name} current_operator_boundary must mark {flag}=true")
    for key in (
        "source_freshness_generated_reference_date",
        "source_freshness_generated_reference_timezone",
        "source_freshness_staleness_comparison_source",
        "source_freshness_staleness_comparison_date",
        "source_freshness_read",
    ):
        if not isinstance(boundary.get(key), str) or not boundary[key].strip():
            raise ValueError(f"{compare_json_path.name} current_operator_boundary must preserve non-empty {key}")
    boundary = dict(boundary)
    boundary["operator_read_gate"] = validate_operator_read_gate(boundary, compare_json_path)
    return boundary


def load_current_gate_progress(current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    require_exists(current_evidence_json_path)
    payload = json.loads(current_evidence_json_path.read_text(encoding="utf-8"))
    progress = payload.get("decision_gate_progress")
    if not isinstance(progress, dict):
        raise ValueError(f"{current_evidence_json_path.name} is missing decision_gate_progress")
    missing = sorted(REQUIRED_CURRENT_GATE_PROGRESS_FIELDS - set(progress))
    if missing:
        raise ValueError(f"{current_evidence_json_path.name} decision_gate_progress is missing fields: {', '.join(missing)}")
    if progress.get("gate_status") != "all_uncleared":
        raise ValueError(f"{current_evidence_json_path.name} decision_gate_progress must remain gate_status=all_uncleared")
    if progress.get("all_gates_ready") is not False:
        raise ValueError(f"{current_evidence_json_path.name} decision_gate_progress must keep all_gates_ready=false")
    for flag in (
        "not_forward_performance_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_real_money_evidence",
    ):
        if progress.get(flag) is not True:
            raise ValueError(f"{current_evidence_json_path.name} decision_gate_progress must mark {flag}=true")

    primary = progress.get("primary_first_read")
    anchor = progress.get("op_anchor_same_candidate_review")
    phase8 = progress.get("phase8_promotion_review")
    real_money = progress.get("real_money_discussion")
    if not all(isinstance(item, dict) for item in (primary, anchor, phase8, real_money)):
        raise ValueError(f"{current_evidence_json_path.name} decision_gate_progress must publish structured gate-detail blocks")
    if int(primary.get("current_rows", -1)) != 6 or int(primary.get("threshold", -1)) != 30 or primary.get("ready") is not False:
        raise ValueError(f"{current_evidence_json_path.name} decision_gate_progress primary_first_read must publish uncleared 6/30 progress")
    if (
        anchor.get("candidate_rule_id") != "OP_DURABLE_K7"
        or int(anchor.get("current_rows", -1)) != 0
        or int(anchor.get("threshold", -1)) != 30
        or anchor.get("companion_rows_count_as_anchor_evidence") is not False
    ):
        raise ValueError(f"{current_evidence_json_path.name} decision_gate_progress must publish OP_DURABLE_K7 same-candidate 0/30 progress")
    if int(phase8.get("weakest_current_rows", -1)) != 0 or int(phase8.get("threshold_per_candidate", -1)) != 20 or phase8.get("ready") is not False:
        raise ValueError(f"{current_evidence_json_path.name} decision_gate_progress must publish Phase 8 weakest 0/20 progress")
    if int(real_money.get("current_primary_roi_complete_rows", -1)) != 6 or int(real_money.get("threshold", -1)) != 100 or real_money.get("ready") is not False:
        raise ValueError(f"{current_evidence_json_path.name} decision_gate_progress must publish real-money discussion 6/100 progress")
    read = str(progress.get("read") or "")
    for phrase in (
        "Gate progress: primary first-read 6/30",
        "OP anchor same-candidate 0/30",
        "Phase 8 weakest shadow 0/20",
        "real-money discussion floor 6/100",
        "All remain uncleared",
    ):
        if phrase not in read:
            raise ValueError(f"{current_evidence_json_path.name} decision_gate_progress.read is missing {phrase!r}")
    return dict(progress)


def load_scorecard_audit_route(current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    require_exists(current_evidence_json_path)
    payload = json.loads(current_evidence_json_path.read_text(encoding="utf-8"))
    route = payload.get("scorecard_audit_route")
    if not isinstance(route, dict):
        raise ValueError(f"{current_evidence_json_path.name} is missing scorecard_audit_route")
    missing = sorted(REQUIRED_SCORECARD_AUDIT_ROUTE_FIELDS - set(route))
    if missing:
        raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route is missing fields: {', '.join(missing)}")
    if route.get("markdown_path") != "SCORECARD_RANKING_CONTRACT_AUDIT.md":
        raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route markdown_path must point to SCORECARD_RANKING_CONTRACT_AUDIT.md")
    if route.get("json_path") != "scorecard_ranking_contract_audit.json":
        raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route json_path must point to scorecard_ranking_contract_audit.json")
    if route.get("validator_command") != "python3 validate_scorecard_ranking_contract_audit.py":
        raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route validator_command must run validate_scorecard_ranking_contract_audit.py")
    if route.get("gate_floor_source") != "forward_evidence_scorecard.json:decision_gate_minimums":
        raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route must source gate floors from forward_evidence_scorecard.json:decision_gate_minimums")
    if route.get("valid_use") != "navigation route for scorecard gate/ranking/CI-only/timezone/no-BAQ synchronization checks":
        raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route valid_use drifted")
    for flag in REQUIRED_SCORECARD_AUDIT_ROUTE_TRUE_FLAGS:
        if route.get(flag) is not True:
            raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route must mark {flag}=true")
    snapshot = route.get("gate_floor_snapshot")
    if not isinstance(snapshot, dict):
        raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route gate_floor_snapshot must be an object")
    expected_snapshot = {
        "anchor_displacement_min_roi_complete_settled_observations": 30,
        "phase8_promotion_review_min_roi_complete_settled_observations": 20,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": 100,
        "real_money_no_baq_as_bel_required": True,
    }
    for key, expected in expected_snapshot.items():
        if snapshot.get(key) != expected:
            raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route gate_floor_snapshot.{key} must be {expected!r}")
    route_read = str(route.get("route_read") or "")
    for phrase in REQUIRED_SCORECARD_AUDIT_ROUTE_READ_PHRASES:
        if phrase not in route_read:
            raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route.route_read is missing {phrase!r}")
    for artifact_key in ("markdown_path", "json_path"):
        artifact_path = current_evidence_json_path.parent / str(route[artifact_key])
        if not artifact_path.exists():
            raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route references missing artifact {artifact_path.name}")
    return dict(route)


def load_rebuild_validation_contract(current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    require_exists(current_evidence_json_path)
    payload = json.loads(current_evidence_json_path.read_text(encoding="utf-8"))
    contract = payload.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise ValueError(f"{current_evidence_json_path.name} is missing rebuild_validation_contract")
    order = contract.get("upstream_refresh_order")
    if not isinstance(order, list):
        raise ValueError(f"{current_evidence_json_path.name} rebuild_validation_contract.upstream_refresh_order must be a list")
    commands = [str(item.get("command") or "") for item in order if isinstance(item, dict)]
    if commands != REQUIRED_REBUILD_REFRESH_ORDER:
        raise ValueError(f"{current_evidence_json_path.name} rebuild_validation_contract upstream order drifted")
    if [item.get("order") for item in order if isinstance(item, dict)] != [1, 2, 3]:
        raise ValueError(f"{current_evidence_json_path.name} rebuild_validation_contract order numbers drifted")
    if contract.get("prerequisite_rebuild_command") != REQUIRED_REBUILD_REFRESH_ORDER[0]:
        raise ValueError(f"{current_evidence_json_path.name} rebuild_validation_contract prerequisite command drifted")
    if contract.get("rebuild_command") != REQUIRED_REBUILD_REFRESH_ORDER[1]:
        raise ValueError(f"{current_evidence_json_path.name} rebuild_validation_contract rebuild command drifted")
    if contract.get("direct_validation_command") != REQUIRED_REBUILD_REFRESH_ORDER[2]:
        raise ValueError(f"{current_evidence_json_path.name} rebuild_validation_contract direct validator command drifted")
    for flag in REQUIRED_REBUILD_VALIDATION_TRUE_FLAGS:
        if contract.get(flag) is not True:
            raise ValueError(f"{current_evidence_json_path.name} rebuild_validation_contract.{flag} must be true")
    copied = dict(contract)
    copied["source_path"] = "rebuild_validation_contract"
    copied["upstream_refresh_commands"] = commands
    return copied


def load_decision_change_gate_minimums(compare_json_path: Path = COMPARE_MAIN_JSON) -> dict[str, Any]:
    require_exists(compare_json_path)
    payload = json.loads(compare_json_path.read_text(encoding="utf-8"))
    gates = payload.get("decision_change_gate_minimums")
    if not isinstance(gates, dict):
        raise ValueError(f"{compare_json_path.name} is missing decision_change_gate_minimums")

    for gate_name, (minimum_key, expected_source) in EXPECTED_DECISION_GATE_SOURCES.items():
        gate = gates.get(gate_name)
        if not isinstance(gate, dict):
            raise ValueError(f"{compare_json_path.name} is missing decision_change_gate_minimums.{gate_name}")
        value = gate.get(minimum_key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{compare_json_path.name} decision_change_gate_minimums.{gate_name}.{minimum_key} must be a positive integer")
        if gate.get("threshold_source") != expected_source:
            raise ValueError(
                f"{compare_json_path.name} decision_change_gate_minimums.{gate_name}.threshold_source must be {expected_source}"
            )
    return dict(gates)


def pct(value: float) -> str:
    return f"{value:.2f}%"


def signed_pct(value: float) -> str:
    return f"{value:+.2f}%"


def md_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def build_rows(
    compare_rows: Optional[list[dict[str, Any]]] = None,
    compare_csv: Optional[Path] = None,
    cross_family_csv: Optional[Path] = None,
    backtest_csv: Optional[Path] = None,
    ab_json: Optional[Path] = None,
) -> list[dict[str, Any]]:
    compare_csv = compare_csv or COMPARE_MAIN
    cross_family_csv = cross_family_csv or CROSS_FAMILY_CSV
    backtest_csv = backtest_csv or BACKTEST_SUMMARY
    ab_json = ab_json or AB_RESULTS
    compare_rows = compare_rows if compare_rows is not None else load_csv(compare_csv)
    require_columns(compare_rows, REQUIRED_COMPARE_COLUMNS, compare_csv, "compare-main")
    require_keyed_rows(compare_rows, "method_id", REQUIRED_COMPARE_METHODS, compare_csv, "compare-main method")
    compare_by_id = {str(row["method_id"]): row for row in compare_rows}
    selective = compare_by_id["phase7_live_portfolio"]
    selector = compare_by_id["train_only_selector"]

    cross_rows = load_csv(cross_family_csv)
    require_columns(cross_rows, REQUIRED_CROSS_COLUMNS, cross_family_csv, "cross-family")
    require_keyed_rows(cross_rows, "shadow_rank", REQUIRED_CROSS_SHADOWS, cross_family_csv, "cross-family shadow")
    cross_by_shadow = {row["shadow_rank"]: row for row in cross_rows if row.get("shadow_rank")}
    anchor_rule = cross_by_shadow["LIVE_DEFAULT"]["rule_id"]
    primary_shadow_rule = cross_by_shadow["PRIMARY_SHADOW"]["rule_id"]
    secondary_shadow_rule = cross_by_shadow["SECONDARY_SHADOW"]["rule_id"]
    if not anchor_rule or not primary_shadow_rule or not secondary_shadow_rule:
        raise ValueError(f"{cross_family_csv.name} has blank rule_id values for required shadow ranks")

    backtest_rows = load_csv(backtest_csv)
    require_columns(backtest_rows, REQUIRED_BACKTEST_COLUMNS, backtest_csv, "backtest")
    require_keyed_rows(backtest_rows, "Strategy", REQUIRED_BACKTEST_STRATEGIES, backtest_csv, "backtest strategy")
    harville = next(row for row in backtest_rows if row["Strategy"] == "Harville-Top120")
    ml_rows = [row for row in backtest_rows if row["Strategy"].startswith("ML-")]
    if not ml_rows:
        raise ValueError(f"{backtest_csv.name} is missing required backtest rows: ML-* strategy")
    best_ml = max(ml_rows, key=lambda row: float(row["ROI%"]))

    require_exists(ab_json)
    ab = json.loads(ab_json.read_text(encoding="utf-8"))
    for dotted_path in sorted(REQUIRED_AB_PATHS):
        require_nested_path(ab, dotted_path, ab_json)
    baseline = ab["prediction_accuracy"]["baseline"]
    enriched = ab["prediction_accuracy"]["enriched"]
    ev_base = ab["ev_engine_comparison"]["baseline"]
    ev_enriched = ab["ev_engine_comparison"]["enriched"]
    ev_delta = ab["ev_engine_comparison"]["delta"]
    test_set = ab["test_set"]

    payout_rmse_reduction_pct = (1.0 - enriched["payout_rmse"] / baseline["payout_rmse"]) * 100.0
    log_rmse_reduction_pct = (1.0 - enriched["log_ratio_rmse"] / baseline["log_ratio_rmse"]) * 100.0

    rows = [
        {
            "family_id": "selective_rule_path",
            "label": "Selective rule path",
            "role": "PAPER NOW",
            "primary_metric": float(selective["holdout_roi"]),
            "primary_metric_label": "2024-2025 holdout ROI",
            "primary_sample": int(float(selective["holdout_races"])),
            "holdout_2024_metric": float(selective["holdout_2024_roi"]),
            "holdout_2024_sample": int(float(selective["holdout_2024_races"])),
            "holdout_2025_metric": float(selective["holdout_2025_roi"]),
            "holdout_2025_sample": int(float(selective["holdout_2025_races"])),
            "secondary_metric": float(selector["wf_roi"]),
            "secondary_metric_label": "train-only selector walk-forward ROI",
            "secondary_sample": int(float(selector["wf_races"])),
            "evidence_scope": "frozen holdout + train-only walk-forward benchmark",
            "current_anchor": anchor_rule,
            "primary_shadow": primary_shadow_rule,
            "secondary_shadow": secondary_shadow_rule,
            "why": (
                "Only family here with positive current frozen holdout evidence and a paper-trade observation path. "
                f"In the current holdout, this is effectively the OP+CD basket, with {anchor_rule} still the safest anchor. "
                "Family-level walk-forward context comes from the honest train-only selector benchmark rather than replaying the frozen Phase 7 basket."
            ),
            "note": selective["note"],
        },
        {
            "family_id": "harville_ranked",
            "label": "Harville-ranked probabilities",
            "role": "BENCHMARK ONLY",
            "primary_metric": float(harville["ROI%"]),
            "primary_metric_label": "broad backtest ROI",
            "primary_sample": int(float(harville["Races"])),
            "secondary_metric": float(harville["HitRate%"]),
            "secondary_metric_label": "hit rate",
            "secondary_sample": int(float(harville["Races"])),
            "evidence_scope": "2010-2025 broad backtest",
            "why": (
                "Large-sample structural benchmark, not a paper candidate. The hit rate is high, but the ROI stays deeply negative, "
                "which means ranking order by Harville probability alone does not beat takeout."
            ),
            "note": "Best broad Harville line in BACKTEST_REPORT.md: Harville-Top120.",
        },
        {
            "family_id": "xgboost_residual",
            "label": "XGBoost residual correction",
            "role": "RESEARCH ONLY",
            "primary_metric": float(best_ml["ROI%"]),
            "primary_metric_label": f"best ML betting ROI ({best_ml['Strategy']})",
            "primary_sample": int(float(best_ml["Races"])),
            "secondary_metric": payout_rmse_reduction_pct,
            "secondary_metric_label": "matched-model payout RMSE reduction vs current baseline",
            "secondary_sample": int(test_set["n_races"]),
            "evidence_scope": "broad backtest + matched downstream A/B",
            "why": (
                "The model can improve payout prediction a bit without creating a betting edge. "
                f"In the matched downstream test, payout RMSE was reduced by {pct(payout_rmse_reduction_pct)} and log-ratio RMSE was reduced by {pct(log_rmse_reduction_pct)}, "
                f"but conservative EV winner pass counts drifted down by {abs(int(ev_delta['ev_pass_count_delta']))} "
                f"({float(ev_delta['ev_pass_count_relative_change_pct']):+.2f}% relative; {float(ev_delta['ev_pass_pct_point_delta']):+.4f} percentage points of {test_set['n_races']} test winners), "
                f"from {ev_base['ev_pass_count']} baseline to {ev_enriched['ev_pass_count']} enriched."
            ),
            "note": (
                f"Best ML family line in backtest_summary.csv is still negative ({best_ml['Strategy']} = {signed_pct(float(best_ml['ROI%']))} on {best_ml['Races']} races)."
            ),
        },
    ]
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "family_id",
        "label",
        "role",
        "primary_metric_label",
        "primary_metric",
        "primary_sample",
        "holdout_2024_metric",
        "holdout_2024_sample",
        "holdout_2025_metric",
        "holdout_2025_sample",
        "secondary_metric_label",
        "secondary_metric",
        "secondary_sample",
        "evidence_scope",
        "current_anchor",
        "primary_shadow",
        "secondary_shadow",
        "why",
        "note",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def render_md(
    rows: list[dict[str, Any]],
    compare_csv_name: str = COMPARE_MAIN.name,
    compare_json_name: str = COMPARE_MAIN_JSON.name,
    cross_family_csv_name: str = CROSS_FAMILY_CSV.name,
    scorecard_json_name: str = SCORECARD_JSON.name,
    backtest_csv_name: str = BACKTEST_SUMMARY.name,
    ab_json_name: str = AB_RESULTS.name,
    csv_output_name: str = OUT_CSV.name,
    md_output_name: str = OUT_MD.name,
    scorecard_json_path: Path = SCORECARD_JSON,
    compare_json_path: Path = COMPARE_MAIN_JSON,
    current_evidence_json_name: str = CURRENT_EVIDENCE_JSON.name,
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
    source_paths: dict[str, Path] | None = None,
) -> str:
    ranking_contract = load_scorecard_ranking_contract(scorecard_json_path)
    operator_boundary = load_current_operator_boundary(compare_json_path)
    current_gate_progress = load_current_gate_progress(current_evidence_json_path)
    scorecard_audit_route = load_scorecard_audit_route(current_evidence_json_path)
    rebuild_validation_contract = load_rebuild_validation_contract(current_evidence_json_path)
    compare_decision_gates = load_decision_change_gate_minimums(compare_json_path)
    decision_gates = load_scorecard_decision_gate_minimums(scorecard_json_path)
    ci_only_diagnostic = load_scorecard_ci_only_diagnostic(scorecard_json_path)
    ci_only_source = f"{scorecard_json_name}:{OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}"
    rebuild_order_read = " -> ".join(f"`{command}`" for command in rebuild_validation_contract["upstream_refresh_commands"])
    if operator_boundary["operator_read_gate"].get("requires_refresh_before_evidence_read"):
        operator_gate_boundary_read = (
            "The saved top card must be refreshed before evidence/instruction use; this read gate is not "
            "no-target evidence, clean-empty evidence, method-family proof, bet readiness, settled ROI, "
            "promotion readiness, live profitability, bankroll guidance, or real-money evidence"
        )
    else:
        operator_gate_boundary_read = (
            "The saved top card can be read as current operator routing context only; this read gate is not "
            "no-target evidence, clean-empty evidence, method-family proof, bet readiness, settled ROI, "
            "promotion readiness, live profitability, bankroll guidance, or real-money evidence"
        )
    if (
        compare_decision_gates["phase8_promotion_review"]["minimum_roi_complete_settled_observations"]
        != decision_gates["phase8_promotion_review"]["minimum_roi_complete_settled_observations"]
        or compare_decision_gates["anchor_displacement"]["minimum_roi_complete_same_candidate_observations"]
        != decision_gates["anchor_displacement"]["minimum_roi_complete_same_candidate_observations"]
        or compare_decision_gates["real_money_discussion"]["minimum_total_settled_roi_complete_observations"]
        != decision_gates["real_money_discussion"]["minimum_total_settled_roi_complete_observations"]
    ):
        raise ValueError(
            f"{compare_json_path.name} decision_change_gate_minimums no longer match "
            f"{scorecard_json_path.name} decision_gate_minimums"
        )
    fingerprints = source_file_fingerprints(
        source_paths
        or {
            "compare_main_approaches": Path(compare_csv_name) if Path(compare_csv_name).exists() else COMPARE_MAIN,
            "compare_main_approaches_json": compare_json_path,
            "current_evidence_summary": current_evidence_json_path,
            "cross_family_decision_card": Path(cross_family_csv_name) if Path(cross_family_csv_name).exists() else CROSS_FAMILY_CSV,
            "forward_evidence_scorecard": scorecard_json_path,
            "backtest_summary": Path(backtest_csv_name) if Path(backtest_csv_name).exists() else BACKTEST_SUMMARY,
            "ab_downstream_comparison": Path(ab_json_name) if Path(ab_json_name).exists() else AB_RESULTS,
        }
    )
    selective = next(row for row in rows if row["family_id"] == "selective_rule_path")
    harville = next(row for row in rows if row["family_id"] == "harville_ranked")
    xgb = next(row for row in rows if row["family_id"] == "xgboost_residual")

    lines = [
        "# Method Family Decision Card",
        "",
        "This note compares the three method families that matter most for honest deployment decisions:",
        "**Harville-ranked probabilities, the current XGBoost correction path, and the selective rule path.**",
        "",
        "Short answer:",
        "- **Paper trade the selective rule path**",
        "- **Keep Harville as a benchmark only**",
        "- **Keep XGBoost as research, not as a betting decision engine**",
        f"- **Evidence scope:** `valid_evidence_scope={VALID_EVIDENCE_SCOPE}`; this card is a frozen/report method hierarchy only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "- **This card is split-aware, not family-CI-backed at the top level**: the selective family wins here on frozen 2024-2025 holdout plus an honest train-only walk-forward benchmark, then gets cross-checked by rule-level anchor/shadow evidence, but the frozen sources do not publish a selective-family bootstrap CI lower bound.",
        f"- **Inherited scorecard ranking contract:** rank is tier-first (`{ranking_contract['rank_is_tier_first_decision_order']}`), Score is secondary within tier (`{ranking_contract['forward_trust_is_secondary_within_tier']}`), and raw Score is not an automatic deployment instruction (`{ranking_contract['raw_score_is_not_an_automatic_deployment_instruction']}`).",
        f"- **Inherited operator read gate:** `{compare_json_name}` `current_operator_boundary.operator_read_gate` says {operator_boundary['operator_read_gate']['read']} This is routing context only, not no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money evidence.",
        f"- **Current bridge rebuild order:** `{current_evidence_json_name}` `rebuild_validation_contract` routes source-byte changes through {rebuild_order_read} before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not method-family evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        f"- **Scorecard audit route:** `{current_evidence_json_name}` `scorecard_audit_route` points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to `{scorecard_audit_route['markdown_path']}` / `{scorecard_audit_route['json_path']}` plus `{scorecard_audit_route['validator_command']}`; this is report-synchronization metadata only, not method-family evidence, forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "This card is intentionally pinned to the frozen 2024-2025 holdout standard carried by the compare-main, cross-family, and forward-scorecard JSON artifacts, so a prettier number from some other window or method slice does not quietly rewrite the current paper method hierarchy.",
        "",
        "## Comparison Table",
        "",
        "For the selective family, the primary evidence includes the 2024/2025 holdout split because the aggregate holdout number alone is too smooth. Its secondary evidence is the honest train-only selector walk-forward benchmark, not a replay of the frozen Phase 7 basket.",
        "For XGBoost, the secondary column is model-fit context from the matched downstream A/B, not a betting-evidence line.",
        "",
        "| Method Family | Role | Primary Evidence | Sample | Secondary Evidence | Why It Sits Here |",
        "|---|---|---:|---:|---:|---|",
    ]

    for row in rows:
        if row["family_id"] == "selective_rule_path":
            primary = (
                f"{signed_pct(float(row['primary_metric']))} ({row['primary_metric_label']}; "
                f"2024 {signed_pct(float(row['holdout_2024_metric']))} on {int(row['holdout_2024_sample'])}, "
                f"2025 {signed_pct(float(row['holdout_2025_metric']))} on {int(row['holdout_2025_sample'])})"
            )
            why = (
                "Only family here with positive current frozen holdout evidence and a paper-trade observation path. "
                f"In the current holdout, this is effectively the OP+CD basket, with {row['current_anchor']} still the safest anchor, "
                "but the recent path was uneven rather than a smooth two-year glide."
            )
        else:
            primary = f"{signed_pct(float(row['primary_metric']))} ({row['primary_metric_label']})"
            why = row["why"]
        secondary_label = row["secondary_metric_label"]
        secondary_value = signed_pct(float(row["secondary_metric"])) if "ROI" in secondary_label else pct(float(row["secondary_metric"]))
        lines.append(
            f"| {row['label']} | {row['role']} | {primary} | {int(row['primary_sample'])} | {secondary_value} ({secondary_label}) | {why} |"
        )

    lines.extend([
        "",
        "## Why This Ordering Is Conservative",
        "",
        "At the method-family layer, this card does not have a published family-level bootstrap CI field. The caution surface here is the selective family holdout split, the honest train-only walk-forward benchmark, and the rule-level anchor/shadow evidence beneath it rather than a top-level family CI claim.",
        f"Scorecard rank-contract override: {ranking_contract['known_rank_override']}",
        "",
        f"- **{selective['label']} ({selective['role']})**: {selective['why']}",
        f"  - Practical note: {selective['note']}",
        f"  - Holdout split: 2024 {signed_pct(float(selective['holdout_2024_metric']))} on {int(selective['holdout_2024_sample'])} races; 2025 {signed_pct(float(selective['holdout_2025_metric']))} on {int(selective['holdout_2025_sample'])} races. That is positive in both years, but most of the aggregate holdout edge came in 2025, so the family still needs paper-trade confirmation instead of victory-lap language.",
        f"  - Current paper-basket companion read: `{selective['current_anchor']}` stays the safest anchor, `{selective['primary_shadow']}` is the primary OP/CD paper-basket companion, and `{selective['secondary_shadow']}` remains the stronger same-family OP shadow challenger rather than a promoted default.",
        f"  - Scorecard CI-only promotion check: `{ci_only_source}` says `ci_only_promotion_allowed={str(ci_only_diagnostic['ci_only_promotion_allowed']).lower()}`; the positive OP_REFINED CI lower bound is support context only, not a method-family promotion trigger.",
        f"- **{harville['label']} ({harville['role']})**: {harville['why']}",
        f"  - Practical note: {harville['note']}",
        f"- **{xgb['label']} ({xgb['role']})**: {xgb['why']}",
        "  - Read the payout-RMSE gain as model-fit context only; it does not become deployment-worthy unless the downstream betting behavior improves too.",
        f"  - Practical note: {xgb['note']}",
        "",
        "## Why This Is Not an Apples-to-Apples ROI Contest",
        "",
        "- The **selective rule path** has earned the strongest current deployment evidence, because it is the only family here with positive frozen 2024-2025 holdout results plus a paper-trade observation workflow.",
        f"  - Its frozen holdout split is still worth saying plainly: 2024 {signed_pct(float(selective['holdout_2024_metric']))} on {int(selective['holdout_2024_sample'])} races versus 2025 {signed_pct(float(selective['holdout_2025_metric']))} on {int(selective['holdout_2025_sample'])} races. That is better than Harville/XGBoost, but it is not a smooth straight-line edge.",
        "- The **Harville** and **XGBoost** families are judged by their best honest family-level evidence instead of by a fresh 2024-2025 holdout replay, because they already fail on much larger historical samples and never earned a positive deployment case.",
        "  - For XGBoost specifically, the payout-RMSE improvement is still just model-fit context from the matched downstream test, not a separate betting-proof column.",
        "- That asymmetry is acceptable here because the question is practical, not academic: **what should Cole still treat as paper-worthy?** The answer is the selective rule path, not the generic ranking/modeling families.",
        "",
        "## Current Operator Boundary",
        "",
        f"This context is inherited from `{compare_json_name}` / `{operator_boundary['source_path']}` so the method-family card points to the current paper-workflow boundary without using it as method-ranking evidence.",
        "",
        "| Field | Current bridge read | Evidence boundary |",
        "|---|---|---|",
        f"| Source freshness | `{operator_boundary['right_now_freshness_state']}`; refresh before right-now use = `{operator_boundary['requires_refresh_before_right_now_use']}`; bridge reference = `{operator_boundary['source_freshness_generated_reference_date']}` (`{operator_boundary['source_freshness_generated_reference_timezone']}`); comparison = `{operator_boundary['source_freshness_staleness_comparison_source']}` / `{operator_boundary['source_freshness_staleness_comparison_date']}`; read = {md_cell(operator_boundary['source_freshness_read'])} | Source freshness is operator-readiness metadata, not method-ranking or performance proof |",
        f"| Refresh action boundary | `{operator_boundary['refresh_action_command']}` required before right-now use = `{operator_boundary['refresh_required_before_right_now_instruction_use']}`; can update surfaces = `{operator_boundary['refresh_can_update_operator_surfaces']}`; settles rows / creates ROI evidence / clean-empty performance = `{operator_boundary['refresh_can_settle_open_rows_by_itself']}` / `{operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}` / `{operator_boundary['clean_empty_refresh_counts_as_forward_performance']}` | Wrapper refresh is operator routing only; it is not settled ROI, promotion readiness, live profitability, or real-money evidence |",
        f"| Operator read gate | `{compare_json_name}` `current_operator_boundary.operator_read_gate`: {md_cell(operator_boundary['operator_read_gate']['read'])} Gate status = `{operator_boundary['operator_read_gate']['gate_status']}`; recommended command = `{operator_boundary['operator_read_gate']['recommended_command']}` | {operator_gate_boundary_read} |",
        f"| Bridge-published gate progress | `{current_evidence_json_name}` `decision_gate_progress`: {md_cell(current_gate_progress['read'])} Source: `{current_gate_progress['source_path']}` `{current_gate_progress['source_json_path']}`; gate status = `{current_gate_progress['gate_status']}` | Current gates are all uncleared routing context only; they do not change the method-family ordering or create settled ROI, OP-anchor proof, promotion readiness, live-profitability, bankroll, or real-money evidence |",
        f"| Current bridge rebuild order | `{current_evidence_json_name}` `rebuild_validation_contract`: {rebuild_order_read} before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes | Rebuild route only; it is not method-family evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
        f"| Scorecard audit route | `{current_evidence_json_name}` `scorecard_audit_route`: {md_cell(scorecard_audit_route['route_read'])} Artifacts: `{scorecard_audit_route['markdown_path']}` / `{scorecard_audit_route['json_path']}`; validator: `{scorecard_audit_route['validator_command']}`; gate source: `{scorecard_audit_route['gate_floor_source']}` | Route metadata checks copied gate/ranking/CI-only/timezone/no-BAQ synchronization only; it is not method-family evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
        f"| Current settled rule mix | OP_DURABLE_K7={operator_boundary['op_anchor_roi_complete_rows']}; CD_CORE_K8={operator_boundary['cd_companion_roi_complete_rows']}; {md_cell(operator_boundary['primary_rule_mix_read'])} | Rule-specific settled rows stay separate; CD-only paper rows are not OP-anchor forward evidence |",
        f"| Settlement queue state | `{operator_boundary['open_settlement_queue_state']}`; {md_cell(operator_boundary['open_settlement_context'])}; detail: {md_cell(operator_boundary['open_settlement_queue_read'])} | Open rows are settlement workflow only; fill outcomes from actual result/payout evidence before interpreting ROI |",
        f"| Recommendation context | {md_cell(operator_boundary['recommendation_context_read'])} | Latest recommendation-state context is operator routing only, not bet readiness or forward-performance evidence |",
        f"| Operator route | `{operator_boundary['best_action_command']}` | Use the route to settle or refresh; do not infer profit, promotion, or real-money readiness from the route itself |",
        "",
        "The current operator boundary is routing/provenance context only. It does not change the selective-rule vs Harville vs XGBoost ordering above, and it is not settled ROI, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "",
        "## Scorecard CI-Only Promotion Check",
        "",
        f"Source: `{ci_only_source}`",
        f"- Current decision: {ci_only_diagnostic['current_decision']}",
        f"- CI-only promotion allowed: `{str(ci_only_diagnostic['ci_only_promotion_allowed']).lower()}`",
        f"- Why not: {', '.join(ci_only_diagnostic['why_not'])}.",
        f"- Required before review: phase8 promotion review = {ci_only_diagnostic['required_before_review']['phase8_promotion_review']}; anchor displacement = {ci_only_diagnostic['required_before_review']['anchor_displacement']}.",
        f"- Does not count: {', '.join(ci_only_diagnostic['does_not_count'])}.",
        "",
        "This keeps the closest selective-family shadow rule in the right evidence class before the broader Harville/XGBoost comparison: positive CI support can justify continued observation, but it cannot by itself promote `OP_REFINED_K7`, displace `OP_DURABLE_K7`, or change the method-family ordering.",
        "",
        "## Decision Gate Source",
        "",
        f"These gate minimums are loaded directly from `{scorecard_json_name}` `decision_gate_minimums`; `{compare_json_name}` also carries matching copied gate values in `decision_change_gate_minimums`. They are posture gates for future settled paper observations, not new proof from this card.",
        "",
        "| Gate | Minimum | Threshold source | Method-family boundary |",
        "|---|---:|---|---|",
        f"| phase8_promotion_review | {decision_gates['phase8_promotion_review']['minimum_roi_complete_settled_observations']} ROI-complete settled shadow observations | `{decision_gates['phase8_promotion_review']['threshold_source']}` | Opens a Phase 8 promotion-review discussion only; it does not displace the OP anchor by itself |",
        f"| anchor_displacement | {decision_gates['anchor_displacement']['minimum_roi_complete_same_candidate_observations']} ROI-complete same-candidate paper observations | `{decision_gates['anchor_displacement']['threshold_source']}` | Minimum before discussing replacement of `OP_DURABLE_K7` as safest anchor |",
        f"| real_money_discussion | {decision_gates['real_money_discussion']['minimum_total_settled_roi_complete_observations']} total settled observations with usable ROI | `{decision_gates['real_money_discussion']['threshold_source']}` | Real-money discussion remains out of scope until this floor plus payout/concentration sanity checks and no BAQ-as-BEL substitution |",
        "",
        "The 20-row Phase 8 promotion-review gate is not an anchor-displacement gate, and the 100-row real-money discussion floor is not bankroll guidance.",
        "",
        "## Bottom Line",
        "",
        "If Cole wants one clean method-level hierarchy right now:",
        "",
        "1. **Selective rule path**: keep as the only paper-trade family",
        "2. **Harville-ranked probabilities**: keep as a structural benchmark, not a paper strategy",
        "3. **XGBoost residual correction**: keep as model research only, because prediction gains have not translated into betting gains",
        "",
        "This card is intentionally blunt. It should make it easier to stop revisiting dead-end method families every time a modest model metric improves.",
        "It should also stay read as a split-aware operating hierarchy, not as a formal family-level CI proof surface.",
        "It also inherits the scorecard ranking contract, so raw Score cannot turn the selective-family OP_REFINED shadow context into an automatic promotion cue.",
        "",
        "## Narrow Follow-Up Reads",
        "",
        "Use the smaller guardrail artifacts below when the question is narrower than the whole method-family hierarchy:",
        "",
        f"- `CROSS_FAMILY_DECISION.md`: use when the question is how the paper-basket companion and same-family OP shadow challenger line up behind `{selective['current_anchor']}`.",
        f"- `OP_ANCHOR_METHOD_COMPARISON.md`: use when the question is specifically why `{selective['current_anchor']}` still outranks Harville while the current odds-only XGBoost path stays parked unless its evidence class changes materially.",
        "- `AB_DOWNSTREAM_COMPARISON.md`: use when the question is specifically whether the enriched horse-history XGBoost downstream correction is strong enough to change the paper-betting answer. It is not.",
        "- `compare_recommender_scope_paths.md`: use when the question is specifically whether widened `--allow-all-combos` scope should change the current paper default. It should not.",
        "",
        "## Validation",
        "",
        f"- Sources: `{compare_csv_name}`, `{compare_json_name}`, `{current_evidence_json_name}`, `{cross_family_csv_name}`, `{scorecard_json_name}`, `{backtest_csv_name}`, `{ab_json_name}`",
        f"- Wrote: `{csv_output_name}`, `{md_output_name}`",
        "- This card is a read-only synthesis of existing frozen artifacts and comparison outputs",
        "",
        "## Source Provenance",
        "",
        "Exact input-byte fingerprints for this method-family card. Use them as reproducibility metadata only; they do not prove settled paper ROI, promotion readiness, live profitability, or real-money performance.",
        "",
        "| Source | Path | Bytes | SHA-256 |",
        "|---|---|---:|---|",
    ])
    for label, fingerprint in fingerprints.items():
        lines.append(f"| `{label}` | `{fingerprint['path']}` | {fingerprint['bytes']} | `{fingerprint['sha256']}` |")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    compare_csv = Path(args.compare_csv)
    compare_json = Path(args.compare_json)
    current_evidence_json = Path(args.current_evidence_json)
    cross_family_csv = Path(args.cross_family_csv)
    scorecard_json = Path(args.scorecard_json)
    backtest_csv = Path(args.backtest_csv)
    ab_json = Path(args.ab_json)
    csv_output = Path(args.csv_output)
    md_output = Path(args.md_output)

    rows = build_rows(
        compare_csv=compare_csv,
        cross_family_csv=cross_family_csv,
        backtest_csv=backtest_csv,
        ab_json=ab_json,
    )
    report = render_md(
        rows,
        compare_csv_name=compare_csv.name,
        compare_json_name=compare_json.name,
        cross_family_csv_name=cross_family_csv.name,
        scorecard_json_name=scorecard_json.name,
        backtest_csv_name=backtest_csv.name,
        ab_json_name=ab_json.name,
        csv_output_name=csv_output.name,
        md_output_name=md_output.name,
        scorecard_json_path=scorecard_json,
        compare_json_path=compare_json,
        current_evidence_json_name=current_evidence_json.name,
        current_evidence_json_path=current_evidence_json,
        source_paths={
            "compare_main_approaches": compare_csv,
            "compare_main_approaches_json": compare_json,
            "current_evidence_summary": current_evidence_json,
            "cross_family_decision_card": cross_family_csv,
            "forward_evidence_scorecard": scorecard_json,
            "backtest_summary": backtest_csv,
            "ab_downstream_comparison": ab_json,
        },
    )
    if not report.endswith("\n"):
        report += "\n"
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(csv_output, rows)
    md_output.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"Saved: {csv_output.name}")
    print(f"Saved: {md_output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
