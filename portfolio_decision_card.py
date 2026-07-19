#!/usr/bin/env python3
"""
Portfolio-level decision card for the current superfecta deployment choices.

Purpose:
- Put the main portfolio-level approaches in one report-safe artifact.
- Keep the decision anchored to the frozen 2024-2025 holdout plus walk-forward context.
- Separate the operational default from research challengers and validation benchmarks.

Outputs:
- portfolio_decision_card.csv
- PORTFOLIO_DECISION_CARD.md
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
COMPARE_PATH = BASE / "compare_main_approaches.csv"
COMPARE_JSON_PATH = BASE / "compare_main_approaches.json"
FROZEN_EVAL_PATH = BASE / "frozen_portfolio_eval_summary.csv"
WF_FOLDS_PATH = BASE / "walk_forward_validation_folds.csv"
SCORECARD_JSON_PATH = BASE / "forward_evidence_scorecard.json"
CURRENT_EVIDENCE_JSON_PATH = BASE / "current_evidence_summary.json"
OUT_CSV = BASE / "portfolio_decision_card.csv"
OUT_MD = BASE / "PORTFOLIO_DECISION_CARD.md"

VALID_EVIDENCE_SCOPE = "split_aware_portfolio_decision_hierarchy_only"

SOURCE_FINGERPRINT_PATHS = {
    "compare_main_approaches": COMPARE_PATH,
    "compare_main_approaches_json": COMPARE_JSON_PATH,
    "frozen_portfolio_eval": FROZEN_EVAL_PATH,
    "walk_forward_folds": WF_FOLDS_PATH,
    "forward_evidence_scorecard": SCORECARD_JSON_PATH,
    "current_evidence_summary": CURRENT_EVIDENCE_JSON_PATH,
}

TARGET_METHODS = [
    "phase7_live_portfolio",
    "phase8_frozen_portfolio",
    "train_only_selector",
]

REQUIRED_COMPARE_COLUMNS = {
    "method_id",
    "label",
    "method_type",
    "deployment_posture",
    "note",
    "secondary_basis",
    "wf_roi",
    "wf_races",
    "wf_positive_years",
    "wf_observed_years",
    "holdout_roi",
    "holdout_races",
    "holdout_hits",
    "holdout_profit",
    "holdout_positive_years",
    "holdout_observed_years",
    "holdout_2024_roi",
    "holdout_2024_races",
    "holdout_2025_roi",
    "holdout_2025_races",
    "score",
}
REQUIRED_COMPARE_METHODS = set(TARGET_METHODS)
REQUIRED_FROZEN_COLUMNS = {"level", "name", "slice", "races", "roi"}
REQUIRED_FROZEN_ROWS = {
    ("phase7_live", "holdout_2024_2025"),
    ("phase7_live", "year_2024"),
    ("phase7_live", "year_2025"),
    ("phase8_frozen", "holdout_2024_2025"),
    ("phase8_frozen", "year_2024"),
    ("phase8_frozen", "year_2025"),
}
REQUIRED_WF_COLUMNS = {"test_year", "test_races", "test_roi"}
REQUIRED_WF_YEARS = {2024, 2025}
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
    "best_action_command",
    "refresh_action_command",
    "refresh_action_boundary_read",
    "refresh_required_before_right_now_instruction_use",
    "refresh_can_update_operator_surfaces",
    "refresh_can_settle_open_rows_by_itself",
    "refresh_counts_as_roi_complete_evidence_by_itself",
    "clean_empty_refresh_counts_as_forward_performance",
    "refresh_boundary_not_forward_performance_evidence",
    "refresh_boundary_not_live_profitability_evidence",
    "refresh_boundary_not_promotion_readiness_evidence",
    "refresh_boundary_not_real_money_evidence",
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
    "recommendation_context_read",
    "not_forward_performance_evidence",
    "not_bet_readiness_evidence_by_itself",
    "operator_read_gate",
}
REQUIRED_CURRENT_GATE_PROGRESS_FIELDS = {
    "source_path",
    "source_json_path",
    "valid_use",
    "not_forward_performance_evidence",
    "not_promotion_readiness_evidence",
    "not_live_profitability_evidence",
    "not_real_money_evidence",
    "gate_status",
    "primary_first_read",
    "op_anchor_same_candidate_review",
    "phase8_promotion_review",
    "real_money_discussion",
    "all_gates_ready",
    "read",
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
OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY = "ci_only_promotion_diagnostics.OP_REFINED_K7"
REQUIRED_CI_ONLY_WHY_NOT = (
    "smaller holdout sample than OP_DURABLE_K7",
    "losing 2024 holdout split",
    "lower walk-forward recurrence than OP_DURABLE_K7",
    "uncleared phase8_promotion_review paper-observation gate",
    "uncleared anchor_displacement paper-observation gate",
)
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
    "SCORECARD_RANKING_CONTRACT_AUDIT.md",
    "scorecard_ranking_contract_audit.json",
    "python3 validate_scorecard_ranking_contract_audit.py",
    "30/20/100 gate floors",
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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build the portfolio decision card")
    p.add_argument("--compare-csv", default=str(COMPARE_PATH), help="compare-main CSV path")
    p.add_argument("--compare-json", default=str(COMPARE_JSON_PATH), help="compare-main JSON sidecar path")
    p.add_argument("--frozen-eval-csv", default=str(FROZEN_EVAL_PATH), help="frozen portfolio evaluation CSV path")
    p.add_argument("--wf-folds-csv", default=str(WF_FOLDS_PATH), help="walk-forward folds CSV path")
    p.add_argument("--scorecard-json", default=str(SCORECARD_JSON_PATH), help="forward evidence scorecard JSON path")
    p.add_argument("--current-evidence-json", default=str(CURRENT_EVIDENCE_JSON_PATH), help="current evidence summary JSON path")
    p.add_argument("--csv-output", default=str(OUT_CSV), help="CSV output path")
    p.add_argument("--md-output", default=str(OUT_MD), help="Markdown output path")
    return p.parse_args()


def fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"


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


def require_columns(df: pd.DataFrame, required: set[str], source_path: Path, label: str) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{source_path.name} is missing required {label} columns: {', '.join(missing)}")


def require_index_rows(df: pd.DataFrame, required: set[str | int], source_path: Path, label: str) -> None:
    missing = sorted(required - set(df.index))
    if missing:
        raise ValueError(f"{source_path.name} is missing required {label} rows: {', '.join(str(item) for item in missing)}")


def require_unique_index_rows(df: pd.DataFrame, required: set[str | int], source_path: Path, label: str) -> None:
    require_index_rows(df, required, source_path, label)
    conflicts: list[str] = []
    for key in sorted(required):
        if key not in df.index:
            continue
        match = df.loc[[key]] if not isinstance(df.loc[key], pd.Series) else df.loc[[key]]
        row_tuples = {tuple(row) for row in match.itertuples(index=False, name=None)}
        if len(row_tuples) > 1:
            conflicts.append(str(key))
    if conflicts:
        raise ValueError(f"{source_path.name} has conflicting duplicate {label} rows: {', '.join(conflicts)}")


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
        required_refresh_flags = ("requires_refresh_before_evidence_read", "has_wrapper_refresh_action")
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


def load_scorecard_ranking_contract(scorecard_json_path: Path = SCORECARD_JSON_PATH) -> dict[str, object]:
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


def load_scorecard_ci_only_diagnostic(scorecard_json_path: Path = SCORECARD_JSON_PATH) -> dict[str, Any]:
    require_exists(scorecard_json_path)
    payload = json.loads(scorecard_json_path.read_text(encoding="utf-8"))
    diagnostics = payload.get("ci_only_promotion_diagnostics")
    if not isinstance(diagnostics, dict):
        raise ValueError(f"{scorecard_json_path.name} is missing ci_only_promotion_diagnostics")
    diagnostic = diagnostics.get("OP_REFINED_K7")
    if not isinstance(diagnostic, dict):
        raise ValueError(f"{scorecard_json_path.name} is missing ci_only_promotion_diagnostics.OP_REFINED_K7")
    if diagnostic.get("candidate_rule_id") != "OP_REFINED_K7":
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic has the wrong candidate_rule_id")
    if diagnostic.get("current_anchor_rule_id") != "OP_DURABLE_K7":
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic has the wrong current_anchor_rule_id")
    if diagnostic.get("ci_only_promotion_allowed") is not False:
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic must keep ci_only_promotion_allowed=false")
    if diagnostic.get("positive_ci_lower_bound_is_support_context") is not True:
        raise ValueError(
            f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic must mark positive_ci_lower_bound_is_support_context=true"
        )
    why_not = diagnostic.get("why_not")
    if not isinstance(why_not, list) or any(item not in why_not for item in REQUIRED_CI_ONLY_WHY_NOT):
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic is missing required why_not reasons")
    required_before_review = diagnostic.get("required_before_review")
    if not isinstance(required_before_review, dict):
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic is missing required_before_review")
    for key in ("phase8_promotion_review", "anchor_displacement"):
        if not isinstance(required_before_review.get(key), str) or not required_before_review[key].strip():
            raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic is missing required_before_review.{key}")
    does_not_count = diagnostic.get("does_not_count")
    if not isinstance(does_not_count, list) or "green validators" not in does_not_count:
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic must list green validators as non-counting")
    return dict(diagnostic)


def load_current_operator_boundary(compare_json_path: Path = COMPARE_JSON_PATH) -> dict[str, Any]:
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
    if boundary.get("current_settled_context_is_cd_only") is not True:
        raise ValueError(f"{compare_json_path.name} current_operator_boundary must preserve current_settled_context_is_cd_only=true")
    if int(boundary.get("op_anchor_roi_complete_rows", -1)) != 0:
        raise ValueError(f"{compare_json_path.name} current_operator_boundary must keep OP_DURABLE_K7 current settled rows separate")
    if int(boundary.get("cd_companion_roi_complete_rows", -1)) < 0:
        raise ValueError(f"{compare_json_path.name} current_operator_boundary has invalid CD companion settled rows")
    if "CD-only" not in str(boundary.get("primary_rule_mix_read") or ""):
        raise ValueError(f"{compare_json_path.name} current_operator_boundary must explain that current settled context is CD-only")
    if boundary.get("refresh_can_update_operator_surfaces") is not True:
        raise ValueError(f"{compare_json_path.name} current_operator_boundary must preserve refresh_can_update_operator_surfaces=true")
    if boundary.get("refresh_can_settle_open_rows_by_itself") is not False:
        raise ValueError(f"{compare_json_path.name} current_operator_boundary must preserve refresh_can_settle_open_rows_by_itself=false")
    if boundary.get("refresh_counts_as_roi_complete_evidence_by_itself") is not False:
        raise ValueError(f"{compare_json_path.name} current_operator_boundary must preserve refresh_counts_as_roi_complete_evidence_by_itself=false")
    if boundary.get("clean_empty_refresh_counts_as_forward_performance") is not False:
        raise ValueError(f"{compare_json_path.name} current_operator_boundary must preserve clean_empty_refresh_counts_as_forward_performance=false")
    for key in (
        "source_freshness_generated_reference_date",
        "source_freshness_generated_reference_timezone",
        "source_freshness_staleness_comparison_source",
        "source_freshness_staleness_comparison_date",
        "source_freshness_read",
    ):
        if not isinstance(boundary.get(key), str) or not boundary[key].strip():
            raise ValueError(f"{compare_json_path.name} current_operator_boundary must preserve non-empty {key}")
    for flag in (
        "refresh_boundary_not_forward_performance_evidence",
        "refresh_boundary_not_live_profitability_evidence",
        "refresh_boundary_not_promotion_readiness_evidence",
        "refresh_boundary_not_real_money_evidence",
    ):
        if boundary.get(flag) is not True:
            raise ValueError(f"{compare_json_path.name} current_operator_boundary must mark {flag}=true")
    boundary = dict(boundary)
    boundary["operator_read_gate"] = validate_operator_read_gate(boundary, compare_json_path)
    return boundary


def load_current_gate_progress(current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON_PATH) -> dict[str, Any]:
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


def load_scorecard_audit_route(current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON_PATH) -> dict[str, Any]:
    require_exists(current_evidence_json_path)
    payload = json.loads(current_evidence_json_path.read_text(encoding="utf-8"))
    route = payload.get("scorecard_audit_route")
    if not isinstance(route, dict):
        raise ValueError(f"{current_evidence_json_path.name} is missing scorecard_audit_route")
    missing = sorted(REQUIRED_SCORECARD_AUDIT_ROUTE_FIELDS - set(route))
    if missing:
        raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route is missing fields: {', '.join(missing)}")
    expected_values = {
        "markdown_path": "SCORECARD_RANKING_CONTRACT_AUDIT.md",
        "json_path": "scorecard_ranking_contract_audit.json",
        "validator_command": "python3 validate_scorecard_ranking_contract_audit.py",
        "gate_floor_source": "forward_evidence_scorecard.json:decision_gate_minimums",
        "valid_use": "navigation route for scorecard gate/ranking/CI-only/timezone/no-BAQ synchronization checks",
    }
    for key, expected in expected_values.items():
        if route.get(key) != expected:
            raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route.{key} must be {expected!r}")
    snapshot = route.get("gate_floor_snapshot")
    if not isinstance(snapshot, dict):
        raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route.gate_floor_snapshot must be an object")
    expected_snapshot = {
        "anchor_displacement_min_roi_complete_settled_observations": 30,
        "phase8_promotion_review_min_roi_complete_settled_observations": 20,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": 100,
        "real_money_no_baq_as_bel_required": True,
    }
    for key, expected in expected_snapshot.items():
        if snapshot.get(key) != expected:
            raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route.gate_floor_snapshot.{key} must be {expected!r}")
    for flag in REQUIRED_SCORECARD_AUDIT_ROUTE_TRUE_FLAGS:
        if route.get(flag) is not True:
            raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route must mark {flag}=true")
    route_read = str(route.get("route_read") or "")
    for phrase in REQUIRED_SCORECARD_AUDIT_ROUTE_READ_PHRASES:
        if phrase not in route_read:
            raise ValueError(f"{current_evidence_json_path.name} scorecard_audit_route.route_read is missing {phrase!r}")
    markdown_path = BASE / str(route["markdown_path"])
    json_path = BASE / str(route["json_path"])
    if not markdown_path.exists() or not json_path.exists():
        raise ValueError(
            f"{current_evidence_json_path.name} scorecard_audit_route referenced audit artifacts must exist on disk"
        )
    return dict(route)


def load_rebuild_validation_contract(current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON_PATH) -> dict[str, Any]:
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


def load_decision_change_gate_minimums(compare_json_path: Path = COMPARE_JSON_PATH) -> dict[str, Any]:
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


def md_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def require_frozen_rows(df: pd.DataFrame, required: set[tuple[str, str]], source_path: Path) -> None:
    portfolio_df = df[df["level"] == "portfolio"].copy()
    present = {tuple(row) for row in portfolio_df[["name", "slice"]].itertuples(index=False, name=None)}
    missing = sorted(required - present)
    if missing:
        raise ValueError(
            f"{source_path.name} is missing required frozen portfolio rows: {', '.join(f'{name}/{slice_name}' for name, slice_name in missing)}"
        )

    duplicate_df = portfolio_df[portfolio_df.duplicated(subset=["name", "slice"], keep=False)]
    conflicts: list[str] = []
    for (name, slice_name), group in duplicate_df.groupby(["name", "slice"], dropna=False):
        row_tuples = {tuple(row) for row in group.itertuples(index=False, name=None)}
        if len(row_tuples) > 1:
            conflicts.append(f"{name}/{slice_name}")
    if conflicts:
        raise ValueError(f"{source_path.name} has conflicting duplicate frozen portfolio rows: {', '.join(sorted(conflicts))}")


def load_inputs(
    compare_path: Path = COMPARE_PATH,
    frozen_eval_path: Path = FROZEN_EVAL_PATH,
    wf_folds_path: Path = WF_FOLDS_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    require_exists(compare_path)
    require_exists(frozen_eval_path)
    require_exists(wf_folds_path)

    compare_df = pd.read_csv(compare_path)
    frozen_df = pd.read_csv(frozen_eval_path)
    wf_df = pd.read_csv(wf_folds_path)

    require_columns(compare_df, REQUIRED_COMPARE_COLUMNS, compare_path, "compare-main")
    require_unique_index_rows(compare_df.set_index("method_id"), REQUIRED_COMPARE_METHODS, compare_path, "compare-main method")

    require_columns(frozen_df, REQUIRED_FROZEN_COLUMNS, frozen_eval_path, "frozen-eval")
    require_frozen_rows(frozen_df, REQUIRED_FROZEN_ROWS, frozen_eval_path)

    require_columns(wf_df, REQUIRED_WF_COLUMNS, wf_folds_path, "walk-forward")
    require_unique_index_rows(wf_df.set_index("test_year"), REQUIRED_WF_YEARS, wf_folds_path, "walk-forward year")
    return compare_df, frozen_df, wf_df


def get_frozen_portfolio_row(frozen_df: pd.DataFrame, portfolio_name: str, slice_name: str) -> pd.Series:
    match = frozen_df[
        (frozen_df["level"] == "portfolio")
        & (frozen_df["name"] == portfolio_name)
        & (frozen_df["slice"] == slice_name)
    ]
    if match.empty:
        raise ValueError(f"Missing frozen eval row for {portfolio_name} / {slice_name}")
    row_tuples = {tuple(row) for row in match.itertuples(index=False, name=None)}
    if len(row_tuples) > 1:
        raise ValueError(f"Conflicting frozen eval rows for {portfolio_name} / {slice_name}")
    return match.iloc[0]


def get_selector_year_roi(wf_df: pd.DataFrame, year: int) -> float:
    match = wf_df[wf_df["test_year"] == year]
    if match.empty:
        raise ValueError(f"Missing walk-forward fold row for {year}")
    row_tuples = {tuple(row) for row in match.itertuples(index=False, name=None)}
    if len(row_tuples) > 1:
        raise ValueError(f"Conflicting walk-forward fold rows for {year}")
    return float(match.iloc[0]["test_roi"])


def current_role(row: pd.Series) -> str:
    return str(row["deployment_posture"])


def short_label(method_id: str, label: str) -> str:
    mapping = {
        "phase7_live_portfolio": "Phase 7 OP/CD rule-component basket",
        "phase8_frozen_portfolio": "Phase 8 frozen portfolio",
        "train_only_selector": label,
    }
    return mapping[method_id]


def decision_reason(method_id: str, row: pd.Series) -> str:
    if method_id == "phase7_live_portfolio":
        return (
            f"Best current paper baseline because it has the strongest 2024-2025 holdout result "
            f"({fmt_pct(float(row['holdout_roi']))} on {int(row['holdout_races'])} races). "
            f"Its split was {fmt_pct(float(row['holdout_2024_roi']))} on {int(row['holdout_2024_races'])} races in 2024 versus "
            f"{fmt_pct(float(row['holdout_2025_roi']))} on {int(row['holdout_2025_races'])} in 2025, so the headline is real but not smooth. "
            f"BEL contributes zero 2024-2025 holdout races here, so the Phase 7 holdout read is effectively OP/CD historical evidence. "
            f"Its secondary read is only a frozen replay on the walk-forward test years, not an extra train-only validation layer."
        )
    if method_id == "phase8_frozen_portfolio":
        return (
            f"Useful challenger, but it underperformed Phase 7 on holdout "
            f"({fmt_pct(float(row['holdout_roi']))} vs {fmt_pct(float(row['phase7_holdout_roi']))}) "
            f"despite adding more mined rules and more weak legs. Its split was still smaller at "
            f"{fmt_pct(float(row['holdout_2024_roi']))} on {int(row['holdout_2024_races'])} races in 2024 and "
            f"{fmt_pct(float(row['holdout_2025_roi']))} on {int(row['holdout_2025_races'])} in 2025, and its prettier secondary line is also only a frozen replay on the walk-forward test years."
        )
    if method_id == "train_only_selector":
        return (
            f"Most honest validation benchmark, not the best daily operating default. Its actual train-only walk-forward ROI is still valuable context "
            f"({fmt_pct(float(row['wf_roi']))} on {int(row['wf_races'])} races), but its current 2024-2025 holdout is only "
            f"{fmt_pct(float(row['holdout_roi']))} on {int(row['holdout_races'])} races, with a split of "
            f"{fmt_pct(float(row['holdout_2024_roi']))} on {int(row['holdout_2024_races'])} races in 2024 versus "
            f"{fmt_pct(float(row['holdout_2025_roi']))} on {int(row['holdout_2025_races'])} in 2025."
        )
    raise ValueError(method_id)


def operational_read(method_id: str) -> str:
    if method_id == "phase7_live_portfolio":
        return "Use as the primary paper-trade basket if Cole wants one frozen portfolio today."
    if method_id == "phase8_frozen_portfolio":
        return "Track as a shadow basket, not as the default, until it beats Phase 7 on more forward data."
    if method_id == "train_only_selector":
        return "Keep as the honest benchmark for reports and sanity checks, not as the daily operating recipe."
    raise ValueError(method_id)


def caution(method_id: str) -> str:
    if method_id == "phase7_live_portfolio":
        return "2024 was basically flat (+0.37% on 109 races) and most of the aggregate holdout edge came from 2025 (+105.38% on 66), so this is still volatile even though the two-year holdout is strongest overall."
    if method_id == "phase8_frozen_portfolio":
        return "Its better replay headline on the walk-forward test years is not enough to offset the weaker current holdout, the smaller two-year split (2024 +9.50% on 85; 2025 +50.26% on 33), and the negative holdout legs inside the basket."
    if method_id == "train_only_selector":
        return "Its honest benchmark value comes with a very lopsided recent split (-19.95% on 45 in 2024, +98.37% on 20 in 2025), and some historical folds used the old BEL bridge candidate, so it should stay a benchmark artifact rather than a clean deployment rulebook."
    raise ValueError(method_id)


def build_dataframe(
    compare_path: Path = COMPARE_PATH,
    frozen_eval_path: Path = FROZEN_EVAL_PATH,
    wf_folds_path: Path = WF_FOLDS_PATH,
) -> pd.DataFrame:
    compare_df, frozen_df, wf_df = load_inputs(compare_path=compare_path, frozen_eval_path=frozen_eval_path, wf_folds_path=wf_folds_path)
    compare_df = compare_df[compare_df["method_id"].isin(TARGET_METHODS)].copy().set_index("method_id")

    phase7_holdout_roi = float(compare_df.loc["phase7_live_portfolio", "holdout_roi"])
    phase7_holdout_races = int(compare_df.loc["phase7_live_portfolio", "holdout_races"])

    phase7_2024 = get_frozen_portfolio_row(frozen_df, "phase7_live", "year_2024")
    phase7_2025 = get_frozen_portfolio_row(frozen_df, "phase7_live", "year_2025")
    phase8_2024 = get_frozen_portfolio_row(frozen_df, "phase8_frozen", "year_2024")
    phase8_2025 = get_frozen_portfolio_row(frozen_df, "phase8_frozen", "year_2025")

    selector_2024_roi = get_selector_year_roi(wf_df, 2024)
    selector_2025_roi = get_selector_year_roi(wf_df, 2025)

    year_map = {
        "phase7_live_portfolio": (
            float(phase7_2024["roi"]),
            int(compare_df.loc["phase7_live_portfolio", "holdout_2024_races"]),
            float(phase7_2025["roi"]),
            int(compare_df.loc["phase7_live_portfolio", "holdout_2025_races"]),
        ),
        "phase8_frozen_portfolio": (
            float(phase8_2024["roi"]),
            int(compare_df.loc["phase8_frozen_portfolio", "holdout_2024_races"]),
            float(phase8_2025["roi"]),
            int(compare_df.loc["phase8_frozen_portfolio", "holdout_2025_races"]),
        ),
        "train_only_selector": (
            selector_2024_roi,
            int(compare_df.loc["train_only_selector", "holdout_2024_races"]),
            selector_2025_roi,
            int(compare_df.loc["train_only_selector", "holdout_2025_races"]),
        ),
    }

    rows: list[dict] = []
    for method_id in TARGET_METHODS:
        row = compare_df.loc[method_id]
        holdout_2024_roi, holdout_2024_races, holdout_2025_roi, holdout_2025_races = year_map[method_id]

        enriched = pd.Series(
            {
                **row.to_dict(),
                "holdout_2024_roi": holdout_2024_roi,
                "holdout_2024_races": holdout_2024_races,
                "holdout_2025_roi": holdout_2025_roi,
                "holdout_2025_races": holdout_2025_races,
                "phase7_holdout_roi": phase7_holdout_roi,
            }
        )

        rows.append(
            {
                "method_id": method_id,
                "label": short_label(method_id, str(row["label"])),
                "role": current_role(row),
                "method_type": row["method_type"],
                "holdout_roi": float(row["holdout_roi"]),
                "holdout_races": int(row["holdout_races"]),
                "holdout_hits": int(row["holdout_hits"]),
                "holdout_profit": float(row["holdout_profit"]),
                "holdout_2024_roi": holdout_2024_roi,
                "holdout_2024_races": holdout_2024_races,
                "holdout_2025_roi": holdout_2025_roi,
                "holdout_2025_races": holdout_2025_races,
                "holdout_positive_years": f"{int(row['holdout_positive_years'])}/{int(row['holdout_observed_years'])}",
                "wf_roi": float(row["wf_roi"]),
                "wf_races": int(row["wf_races"]),
                "wf_positive_years": f"{int(row['wf_positive_years'])}/{int(row['wf_observed_years'])}",
                "secondary_basis": str(row["secondary_basis"]),
                "score": float(row["score"]),
                "holdout_roi_vs_phase7": round(float(row["holdout_roi"]) - phase7_holdout_roi, 2),
                "holdout_races_vs_phase7": int(row["holdout_races"]) - phase7_holdout_races,
                "decision_reason": decision_reason(method_id, enriched),
                "operational_read": operational_read(method_id),
                "caution": caution(method_id),
                "note": row["note"],
            }
        )

    df = pd.DataFrame(rows)
    role_order = {"PAPER NOW": 0, "SHADOW ONLY": 1, "BENCHMARK ONLY": 2}
    df["sort_order"] = df["role"].map(role_order)
    df = df.sort_values(["sort_order", "holdout_races"], ascending=[True, False]).reset_index(drop=True)
    return df.drop(columns=["sort_order"])


def build_markdown(
    df: pd.DataFrame,
    compare_csv_name: str = COMPARE_PATH.name,
    compare_json_name: str = COMPARE_JSON_PATH.name,
    frozen_eval_csv_name: str = FROZEN_EVAL_PATH.name,
    wf_folds_csv_name: str = WF_FOLDS_PATH.name,
    scorecard_json_name: str = SCORECARD_JSON_PATH.name,
    current_evidence_json_name: str = CURRENT_EVIDENCE_JSON_PATH.name,
    csv_output_name: str = OUT_CSV.name,
    md_output_name: str = OUT_MD.name,
    scorecard_json_path: Path = SCORECARD_JSON_PATH,
    compare_json_path: Path = COMPARE_JSON_PATH,
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON_PATH,
    source_paths: dict[str, Path] | None = None,
) -> str:
    ranking_contract = load_scorecard_ranking_contract(scorecard_json_path)
    ci_only_diagnostic = load_scorecard_ci_only_diagnostic(scorecard_json_path)
    ci_only_source = f"{scorecard_json_name}:{OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}"
    operator_boundary = load_current_operator_boundary(compare_json_path)
    current_gate_progress = load_current_gate_progress(current_evidence_json_path)
    scorecard_audit_route = load_scorecard_audit_route(current_evidence_json_path)
    rebuild_validation_contract = load_rebuild_validation_contract(current_evidence_json_path)
    decision_gates = load_decision_change_gate_minimums(compare_json_path)
    rebuild_order_read = " -> ".join(f"`{command}`" for command in rebuild_validation_contract["upstream_refresh_commands"])
    if operator_boundary["operator_read_gate"].get("requires_refresh_before_evidence_read"):
        operator_gate_boundary_read = (
            "The saved top card must be refreshed before evidence/instruction use; this read gate is not "
            "no-target evidence, clean-empty evidence, bet readiness, settled ROI, portfolio-ranking "
            "evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence"
        )
    else:
        operator_gate_boundary_read = (
            "The saved top card can be read as current operator routing context only; this read gate is not "
            "no-target evidence, clean-empty evidence, bet readiness, settled ROI, portfolio-ranking "
            "evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence"
        )
    fingerprints = source_file_fingerprints(
        source_paths
        or {
            "compare_main_approaches": Path(compare_csv_name) if Path(compare_csv_name).exists() else COMPARE_PATH,
            "compare_main_approaches_json": compare_json_path,
            "frozen_portfolio_eval": Path(frozen_eval_csv_name) if Path(frozen_eval_csv_name).exists() else FROZEN_EVAL_PATH,
            "walk_forward_folds": Path(wf_folds_csv_name) if Path(wf_folds_csv_name).exists() else WF_FOLDS_PATH,
            "forward_evidence_scorecard": scorecard_json_path,
            "current_evidence_summary": current_evidence_json_path,
        }
    )
    lines = [
        "# Portfolio Decision Card",
        "",
        "This note compares the three portfolio-level choices that matter most right now:",
        "the **Phase 7 OP/CD rule-component basket**, the **Phase 8 frozen portfolio**, and the **train-only yearly selector**.",
        "",
        "Short answer:",
        "- **Paper trade the Phase 7 OP/CD rule-component basket first, with daily preflight confirming target cards**",
        "- **Keep the Phase 8 frozen portfolio as a shadow challenger, not the default**",
        "- **Use the train-only yearly selector as an honest benchmark, not as the operating recipe**",
        "- **These roles are copied from `compare_main_approaches.csv` deployment posture so the portfolio card cannot drift from the main comparison harness**",
        f"- **Evidence scope:** `valid_evidence_scope={VALID_EVIDENCE_SCOPE}`; this card is a frozen/report portfolio hierarchy only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        f"- **Inherited scorecard ranking contract:** rank is tier-first (`{ranking_contract['rank_is_tier_first_decision_order']}`), Score is secondary within tier (`{ranking_contract['forward_trust_is_secondary_within_tier']}`), and raw Score is not an automatic deployment instruction (`{ranking_contract['raw_score_is_not_an_automatic_deployment_instruction']}`)",
        f"- **Scorecard CI-only promotion check:** `{ci_only_source}` says `ci_only_promotion_allowed={str(ci_only_diagnostic['ci_only_promotion_allowed']).lower()}`; the positive OP_REFINED CI lower bound is support context only, not a portfolio-level Phase 8 default trigger.",
        f"- **Inherited operator read gate:** `{compare_json_name}` `current_operator_boundary.operator_read_gate` says {operator_boundary['operator_read_gate']['read']} This is routing context only, not no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money evidence.",
        f"- **Bridge-published current gate progress:** `{current_evidence_json_name}` `decision_gate_progress` says {current_gate_progress['read']} This is routing context only, not portfolio-ranking evidence.",
        f"- **Current bridge rebuild order:** `{current_evidence_json_name}` `rebuild_validation_contract` routes source-byte changes through {rebuild_order_read} before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not portfolio-ranking evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        f"- **Scorecard audit route:** `{current_evidence_json_name}` `scorecard_audit_route` says {scorecard_audit_route['route_read']} This is report-synchronization metadata only, not portfolio-ranking evidence, forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        f"- **Inherited decision-change gates:** `phase8_promotion_review={decision_gates['phase8_promotion_review']['minimum_roi_complete_settled_observations']}`, `anchor_displacement={decision_gates['anchor_displacement']['minimum_roi_complete_same_candidate_observations']}`, and `real_money_discussion={decision_gates['real_money_discussion']['minimum_total_settled_roi_complete_observations']}` come from `compare_main_approaches.json` `decision_change_gate_minimums`, which source them from `forward_evidence_scorecard.json`",
        "- **This card is split-aware, not CI-backed at the portfolio level**: the frozen portfolio sources used here do not publish a portfolio bootstrap lower bound, so read the year splits and secondary-context basis as the caution surface instead of treating the roles as formal CI-proof rankings.",
        "",
        "## Comparison Table",
        "",
        "| Approach | Role | Holdout ROI | Holdout Races | 2024 ROI / N | 2025 ROI / N | Secondary ROI | Secondary Races | Secondary Years+ | Secondary Basis | Why It Sits Here |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]

    for _, row in df.iterrows():
        lines.append(
            f"| {row['label']} | {row['role']} | {fmt_pct(float(row['holdout_roi']))} | {int(row['holdout_races'])} | "
            f"{fmt_pct(float(row['holdout_2024_roi']))} / {int(row['holdout_2024_races'])} | {fmt_pct(float(row['holdout_2025_roi']))} / {int(row['holdout_2025_races'])} | "
            f"{fmt_pct(float(row['wf_roi']))} | {int(row['wf_races'])} | {row['wf_positive_years']} | {row['secondary_basis']} | {row['decision_reason']} |"
        )

    lines.extend(
        [
            "",
            "## Why This Ordering Is Conservative",
            "",
            "This portfolio layer is intentionally anchored to the frozen 2024-2025 split and a split secondary context. Unlike the rule-level cards, it does not carry a published portfolio bootstrap CI lower bound from the frozen sources, so the caution lives in the split behavior, sample support, and whether the secondary line is a frozen replay or an actual train-only walk-forward read rather than in a portfolio-level CI field.",
            "",
        ]
    )

    for _, row in df.iterrows():
        lines.append(f"- **{row['label']} ({row['role']})**: {row['operational_read']}")
        lines.append(f"  - Why: {row['decision_reason']}")
        lines.append(f"  - Caution: {row['caution']}")

    lines.extend(
        [
            "",
            "Scorecard rank-contract override: " + str(ranking_contract["known_rank_override"]),
            "",
            "## Head-to-Head vs. Phase 7",
            "",
            "| Approach | Holdout ROI vs Phase 7 | Holdout Races vs Phase 7 | Practical Read |",
            "|---|---:|---:|---|",
        ]
    )

    for _, row in df[df["method_id"] != "phase7_live_portfolio"].iterrows():
        lines.append(
            f"| {row['label']} | {fmt_pct(float(row['holdout_roi_vs_phase7']))} | {int(row['holdout_races_vs_phase7'])} | {row['operational_read']} |"
        )

    lines.extend(
        [
            "",
            "## Bottom Line",
            "",
            "If Cole wants one portfolio-level decision tonight:",
            "",
            "1. **Run the Phase 7 OP/CD rule-component basket as the primary paper baseline, with target cards confirmed by daily preflight**",
            "2. **Log the Phase 8 frozen portfolio separately as a shadow basket**",
            "3. **Keep citing the train-only yearly selector as the honest validation yardstick**",
            "",
            "That ordering keeps the paper choice tied to the strongest current holdout result instead of to the prettiest mined basket or the most abstract validation artifact.",
            "It also keeps the fixed portfolios from quietly borrowing replay-on-walk-forward-years numbers as if they were extra train-only proof.",
            "It also keeps the portfolio card on the same deployment-posture labels as the main comparison harness, so score ordering and operating advice stay separated consistently.",
            "It also inherits the scorecard ranking contract, so raw Score cannot turn a shadow Phase 8 / OP_REFINED line into an automatic promotion cue.",
            "Because the frozen portfolio sources do not publish a portfolio bootstrap lower bound here, this note should stay read as a split-aware operating ranking, not as a formal CI-backed proof surface.",
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
            "## Current Operator Boundary",
            "",
            f"This context is inherited from `{compare_json_name}` / `{operator_boundary['source_path']}` so the portfolio card points to the current paper-workflow boundary without using it as portfolio-ranking evidence.",
            "",
            "| Field | Current bridge read | Evidence boundary |",
            "|---|---|---|",
            f"| Source freshness | `{operator_boundary['right_now_freshness_state']}`; refresh before right-now use = `{operator_boundary['requires_refresh_before_right_now_use']}`; bridge reference = `{operator_boundary['source_freshness_generated_reference_date']}` (`{operator_boundary['source_freshness_generated_reference_timezone']}`); comparison = `{operator_boundary['source_freshness_staleness_comparison_source']}` / `{operator_boundary['source_freshness_staleness_comparison_date']}`; read = {md_cell(operator_boundary['source_freshness_read'])} | Source freshness is operator-readiness metadata, not portfolio-ranking or performance proof |",
            f"| Operator read gate | `{compare_json_name}` `current_operator_boundary.operator_read_gate`: {md_cell(operator_boundary['operator_read_gate']['read'])} Gate status = `{operator_boundary['operator_read_gate']['gate_status']}`; recommended command = `{operator_boundary['operator_read_gate']['recommended_command']}` | {operator_gate_boundary_read} |",
            f"| Bridge-published gate progress | `{current_evidence_json_name}` `decision_gate_progress`: {md_cell(current_gate_progress['read'])} Source: `{current_gate_progress['source_path']}` `{current_gate_progress['source_json_path']}`; gate status = `{current_gate_progress['gate_status']}` | Current gates are all uncleared routing context only; this does not change the portfolio ordering or create settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence |",
            f"| Current bridge rebuild order | `{current_evidence_json_name}` `rebuild_validation_contract`: {rebuild_order_read} before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes | Rebuild route only; it is not portfolio-ranking evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
            f"| Scorecard audit route | `{current_evidence_json_name}` `scorecard_audit_route`: {md_cell(scorecard_audit_route['route_read'])} Validator: `{scorecard_audit_route['validator_command']}`; artifacts: `{scorecard_audit_route['markdown_path']}` / `{scorecard_audit_route['json_path']}`; gate snapshot = 30/20/100 with no-BAQ-as-BEL required `{scorecard_audit_route['gate_floor_snapshot']['real_money_no_baq_as_bel_required']}` | Report-synchronization route only; it is not portfolio-ranking evidence, forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
            f"| Current settled rule mix | OP_DURABLE_K7={operator_boundary['op_anchor_roi_complete_rows']}; CD_CORE_K8={operator_boundary['cd_companion_roi_complete_rows']}; {md_cell(operator_boundary['primary_rule_mix_read'])} | Current settled sample is CD-only context, not OP-anchor forward evidence or a portfolio-ranking change |",
            f"| Stale-card refresh boundary | {md_cell(operator_boundary['refresh_action_boundary_read'])}; clean-empty forward performance = `{operator_boundary['clean_empty_refresh_counts_as_forward_performance']}` | Wrapper refresh can update operator surfaces, but it cannot settle rows, create ROI-complete evidence, promote OP_DURABLE_K7, count clean-empty refreshes as performance, or support live-profitability / real-money claims |",
            f"| Settlement queue state | `{operator_boundary['open_settlement_queue_state']}`; {md_cell(operator_boundary['open_settlement_context'])}; detail: {md_cell(operator_boundary['open_settlement_queue_read'])} | Open rows are settlement workflow only; fill outcomes from actual result/payout evidence before interpreting ROI |",
            f"| Recommendation context | {md_cell(operator_boundary['recommendation_context_read'])} | Latest recommendation-state context is operator routing only, not bet readiness or forward-performance evidence |",
            f"| Operator route | `{operator_boundary['best_action_command']}` | Use the route as the current operator action; do not infer profit, promotion, or real-money readiness from the route itself |",
            "",
            "The current operator boundary is routing/provenance context only. It does not change the Phase 7 vs Phase 8 vs train-only selector ordering above, and it is not settled ROI, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            "",
            "## Decision Gate Source",
            "",
            f"These gate minimums are inherited from `{compare_json_name}` `decision_change_gate_minimums`; compare-main records their `threshold_source` keys as `forward_evidence_scorecard.json` `decision_gate_minimums`. They are posture gates for future settled paper observations, not new proof from this card.",
            "",
            "| Gate | Minimum | Threshold source | Portfolio read |",
            "|---|---:|---|---|",
            f"| phase8_promotion_review | {decision_gates['phase8_promotion_review']['minimum_roi_complete_settled_observations']} ROI-complete settled shadow observations | `{decision_gates['phase8_promotion_review']['threshold_source']}` | Opens a Phase 8 portfolio/shadow-basket promotion-review discussion only; it does not make Phase 8 the default |",
            f"| anchor_displacement | {decision_gates['anchor_displacement']['minimum_roi_complete_same_candidate_observations']} ROI-complete same-candidate paper observations | `{decision_gates['anchor_displacement']['threshold_source']}` | Minimum before discussing replacement of `OP_DURABLE_K7` as safest anchor or treating the Phase 7 ordering as displaced |",
            f"| real_money_discussion | {decision_gates['real_money_discussion']['minimum_total_settled_roi_complete_observations']} total settled observations with usable ROI | `{decision_gates['real_money_discussion']['threshold_source']}` | Real-money discussion remains out of scope until this floor plus payout/concentration sanity checks and no BAQ-as-BEL substitution |",
            "",
            "The 20-row Phase 8 promotion-review gate is not the 30-row anchor-displacement gate, and the 100-row real-money discussion floor is not bankroll guidance.",
            "",
            "## Validation",
            "",
            f"- Sources: `{compare_csv_name}`, `{compare_json_name}`, `{frozen_eval_csv_name}`, `{wf_folds_csv_name}`, `{scorecard_json_name}`, `{current_evidence_json_name}`",
            f"- Wrote: `{csv_output_name}`, `{md_output_name}`",
            "- This card is a read-only synthesis of frozen evaluation artifacts",
            "",
            "## Source Provenance",
            "",
            "Exact input-byte fingerprints for this portfolio card. Use them as reproducibility metadata only; they do not prove settled paper ROI, promotion readiness, live profitability, or real-money performance.",
            "",
            "| Source | Path | Bytes | SHA-256 |",
            "|---|---|---:|---|",
        ]
    )
    for label, fingerprint in fingerprints.items():
        lines.append(f"| `{label}` | `{fingerprint['path']}` | {fingerprint['bytes']} | `{fingerprint['sha256']}` |")

    lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    compare_path = Path(args.compare_csv)
    compare_json_path = Path(args.compare_json)
    frozen_eval_path = Path(args.frozen_eval_csv)
    wf_folds_path = Path(args.wf_folds_csv)
    scorecard_json_path = Path(args.scorecard_json)
    current_evidence_json_path = Path(args.current_evidence_json)
    csv_output = Path(args.csv_output)
    md_output = Path(args.md_output)

    df = build_dataframe(compare_path=compare_path, frozen_eval_path=frozen_eval_path, wf_folds_path=wf_folds_path)
    report = build_markdown(
        df,
        compare_csv_name=compare_path.name,
        compare_json_name=compare_json_path.name,
        frozen_eval_csv_name=frozen_eval_path.name,
            wf_folds_csv_name=wf_folds_path.name,
            scorecard_json_name=scorecard_json_path.name,
            current_evidence_json_name=current_evidence_json_path.name,
            csv_output_name=csv_output.name,
            md_output_name=md_output.name,
            scorecard_json_path=scorecard_json_path,
            compare_json_path=compare_json_path,
            current_evidence_json_path=current_evidence_json_path,
            source_paths={
                "compare_main_approaches": compare_path,
                "compare_main_approaches_json": compare_json_path,
                "frozen_portfolio_eval": frozen_eval_path,
                "walk_forward_folds": wf_folds_path,
                "forward_evidence_scorecard": scorecard_json_path,
                "current_evidence_summary": current_evidence_json_path,
            },
    )
    if not report.endswith("\n"):
        report += "\n"
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_output, index=False)
    md_output.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"Saved: {csv_output.name}")
    print(f"Saved: {md_output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
