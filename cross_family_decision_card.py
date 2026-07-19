#!/usr/bin/env python3
"""
Cross-family decision card for the current paper-decision shortlist.

Purpose:
- Put the three most relevant paper-decision rules in one place:
  OP_DURABLE_K7, CD_CORE_K8, OP_REFINED_K7.
- Keep the comparison anchored to 2024-2025 holdout plus walk-forward context.
- Explain why the current roles are anchor / paper / watch in plain language.

Outputs:
- cross_family_decision_card.csv
- CROSS_FAMILY_DECISION.md
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
SCORECARD_PATH = BASE / "forward_evidence_scorecard.csv"
SCORECARD_JSON_PATH = BASE / "forward_evidence_scorecard.json"
FROZEN_EVAL_PATH = BASE / "frozen_portfolio_eval_summary.csv"
COMPARE_MAIN_JSON_PATH = BASE / "compare_main_approaches.json"
CURRENT_EVIDENCE_JSON_PATH = BASE / "current_evidence_summary.json"
OUT_CSV = BASE / "cross_family_decision_card.csv"
OUT_MD = BASE / "CROSS_FAMILY_DECISION.md"
VALID_EVIDENCE_SCOPE = "split_aware_cross_family_paper_hierarchy_only"

SOURCE_FINGERPRINT_PATHS = {
    "forward_evidence_scorecard_csv": SCORECARD_PATH,
    "forward_evidence_scorecard_json": SCORECARD_JSON_PATH,
    "frozen_portfolio_eval": FROZEN_EVAL_PATH,
    "compare_main_approaches_json": COMPARE_MAIN_JSON_PATH,
    "current_evidence_summary": CURRENT_EVIDENCE_JSON_PATH,
}

TARGET_RULES = ["OP_DURABLE_K7", "CD_CORE_K8", "OP_REFINED_K7"]
WATCH_CONTEXT_RULES = ["KEE_K9", "SA_K9", "DMR_FALL_K7"]

REQUIRED_SCORECARD_COLUMNS = {
    "rule_id",
    "phase",
    "backtest_roi",
    "backtest_races",
    "holdout_roi",
    "holdout_races",
    "holdout_profit",
    "holdout_years",
    "holdout_2024_roi",
    "holdout_2024_races",
    "holdout_2025_roi",
    "holdout_2025_races",
    "worst_year_roi",
    "wf_selected",
    "wf_selected_count",
    "wf_total_folds",
    "ci_lower",
    "forward_trust",
    "tier",
    "note",
}
REQUIRED_SCORECARD_RULES = set(TARGET_RULES + WATCH_CONTEXT_RULES)
REQUIRED_FROZEN_COLUMNS = {"level", "name", "slice", "roi"}
REQUIRED_FROZEN_RULE_ROWS = {
    ("OP_DURABLE_K7", "year_2024"),
    ("OP_DURABLE_K7", "year_2025"),
    ("CD_CORE_K8", "year_2024"),
    ("CD_CORE_K8", "year_2025"),
    ("OP_REFINED_K7", "year_2024"),
    ("OP_REFINED_K7", "year_2025"),
}
REQUIRED_DECISION_GATE_KEYS = (
    "anchor_displacement",
    "phase8_promotion_review",
    "real_money_discussion",
)
REQUIRED_OPERATOR_BOUNDARY_FIELDS = {
    "source_path",
    "generated_at",
    "source_consistency_overall_match",
    "right_now_freshness_state",
    "requires_refresh_before_right_now_use",
    "source_freshness_generated_reference_date",
    "source_freshness_generated_reference_timezone",
    "source_freshness_staleness_comparison_source",
    "source_freshness_staleness_comparison_date",
    "source_freshness_read",
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
    "roi_complete_primary_rows",
    "first_read_threshold",
    "first_read_remaining",
    "op_anchor_roi_complete_rows",
    "cd_companion_roi_complete_rows",
    "current_settled_context_is_cd_only",
    "primary_rule_mix_read",
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
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY = "ci_only_promotion_diagnostics.OP_REFINED_K7"
REQUIRED_CI_ONLY_WHY_NOT = (
    "smaller holdout sample than OP_DURABLE_K7",
    "losing 2024 holdout split",
    "lower walk-forward recurrence than OP_DURABLE_K7",
    "uncleared phase8_promotion_review paper-observation gate",
    "uncleared anchor_displacement paper-observation gate",
)


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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build the cross-family decision card")
    p.add_argument("--scorecard-csv", default=str(SCORECARD_PATH), help="forward evidence scorecard CSV path")
    p.add_argument("--scorecard-json", default=str(SCORECARD_JSON_PATH), help="forward evidence scorecard JSON path")
    p.add_argument("--frozen-eval-csv", default=str(FROZEN_EVAL_PATH), help="frozen portfolio evaluation CSV path")
    p.add_argument("--compare-main-json", default=str(COMPARE_MAIN_JSON_PATH), help="compare-main JSON path with current operator boundary")
    p.add_argument("--current-evidence-json", default=str(CURRENT_EVIDENCE_JSON_PATH), help="current-evidence bridge JSON path")
    p.add_argument("--csv-output", default=str(OUT_CSV), help="CSV output path")
    p.add_argument("--md-output", default=str(OUT_MD), help="Markdown output path")
    return p.parse_args()


def fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"


def md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


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


def require_index_rows(df: pd.DataFrame, required: set[str], source_path: Path, label: str) -> None:
    missing = sorted(required - set(df.index))
    if missing:
        raise ValueError(f"{source_path.name} is missing required {label} rows: {', '.join(missing)}")


def require_unique_index_rows(df: pd.DataFrame, required: set[str], source_path: Path, label: str) -> None:
    require_index_rows(df, required, source_path, label)
    conflicts: list[str] = []
    for key in sorted(required):
        if key not in df.index:
            continue
        match = df.loc[[key]]
        row_tuples = {tuple(row) for row in match.itertuples(index=False, name=None)}
        if len(row_tuples) > 1:
            conflicts.append(str(key))
    if conflicts:
        raise ValueError(f"{source_path.name} has conflicting duplicate {label} rows: {', '.join(conflicts)}")


def require_frozen_rule_rows(df: pd.DataFrame, required: set[tuple[str, str]], source_path: Path) -> None:
    rule_df = df[df["level"] == "rule"].copy()
    present = {tuple(row) for row in rule_df[["name", "slice"]].itertuples(index=False, name=None)}
    missing = sorted(required - present)
    if missing:
        raise ValueError(
            f"{source_path.name} is missing required frozen rule rows: {', '.join(f'{name}/{slice_name}' for name, slice_name in missing)}"
        )

    duplicate_df = rule_df[rule_df.duplicated(subset=["name", "slice"], keep=False)]
    conflicts: list[str] = []
    for name, slice_name in sorted(required):
        group = duplicate_df[(duplicate_df["name"] == name) & (duplicate_df["slice"] == slice_name)]
        if group.empty:
            continue
        row_tuples = {tuple(row) for row in group.itertuples(index=False, name=None)}
        if len(row_tuples) > 1:
            conflicts.append(f"{name}/{slice_name}")
    if conflicts:
        raise ValueError(f"{source_path.name} has conflicting duplicate frozen rule rows: {', '.join(sorted(conflicts))}")


def load_scorecard_df(scorecard_path: Path = SCORECARD_PATH) -> pd.DataFrame:
    require_exists(scorecard_path)
    score_df = pd.read_csv(scorecard_path)
    require_columns(score_df, REQUIRED_SCORECARD_COLUMNS, scorecard_path, "scorecard")
    require_unique_index_rows(score_df.set_index("rule_id"), REQUIRED_SCORECARD_RULES, scorecard_path, "scorecard rule")
    return score_df


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


def require_positive_non_bool_int(value: Any, *, field_name: str, scorecard_json_path: Path) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{scorecard_json_path.name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, field_name: str, scorecard_json_path: Path) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{scorecard_json_path.name} {field_name} must be a list of strings")
    return list(value)


def load_scorecard_decision_gate_minimums(scorecard_json_path: Path = SCORECARD_JSON_PATH) -> dict[str, dict[str, Any]]:
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


def load_scorecard_ci_only_diagnostic(scorecard_json_path: Path = SCORECARD_JSON_PATH) -> dict[str, Any]:
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


def load_current_operator_boundary(compare_json_path: Path = COMPARE_MAIN_JSON_PATH) -> dict[str, Any]:
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
        if not str(boundary.get(key) or "").strip():
            raise ValueError(f"{compare_json_path.name} current_operator_boundary must preserve non-empty {key}")
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
    commands = [str(row.get("command") or "") for row in order if isinstance(row, dict)]
    order_values = [row.get("order") for row in order if isinstance(row, dict)]
    if commands != REQUIRED_REBUILD_REFRESH_ORDER:
        raise ValueError(f"{current_evidence_json_path.name} rebuild_validation_contract upstream order drifted")
    if order_values != [1, 2, 3]:
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
    copied = json.loads(json.dumps(contract))
    copied["source_path"] = "rebuild_validation_contract"
    copied["upstream_refresh_commands"] = commands
    return copied


def load_frozen_df(frozen_eval_path: Path = FROZEN_EVAL_PATH) -> pd.DataFrame:
    require_exists(frozen_eval_path)
    frozen_df = pd.read_csv(frozen_eval_path)
    require_columns(frozen_df, REQUIRED_FROZEN_COLUMNS, frozen_eval_path, "frozen-eval")
    require_frozen_rule_rows(frozen_df, REQUIRED_FROZEN_RULE_ROWS, frozen_eval_path)
    return frozen_df


def load_inputs(
    scorecard_path: Path = SCORECARD_PATH,
    frozen_eval_path: Path = FROZEN_EVAL_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    score_df = load_scorecard_df(scorecard_path)
    frozen_df = load_frozen_df(frozen_eval_path)
    return score_df, frozen_df


def get_rule_slice(frozen_df: pd.DataFrame, rule_id: str, slice_name: str) -> pd.Series:
    match = frozen_df[
        (frozen_df["level"] == "rule")
        & (frozen_df["name"] == rule_id)
        & (frozen_df["slice"] == slice_name)
    ]
    if match.empty:
        raise ValueError(f"Missing frozen eval row for {rule_id} / {slice_name}")
    row_tuples = {tuple(row) for row in match.itertuples(index=False, name=None)}
    if len(row_tuples) > 1:
        raise ValueError(f"Conflicting frozen eval rows for {rule_id} / {slice_name}")
    return match.iloc[0]


def current_role(rule_id: str) -> str:
    mapping = {
        "OP_DURABLE_K7": "ANCHOR",
        "CD_CORE_K8": "PAPER",
        "OP_REFINED_K7": "WATCH",
    }
    return mapping[rule_id]


def family(rule_id: str) -> str:
    if rule_id.startswith("OP_"):
        return "OP"
    if rule_id.startswith("CD_"):
        return "CD"
    return "OTHER"


def decision_reason(rule_id: str, row: pd.Series) -> str:
    if rule_id == "OP_DURABLE_K7":
        return (
            f"Safest anchor because it has the largest OP holdout sample ({int(row['holdout_races'])}) "
            f"and the strongest walk-forward selection frequency ({int(row['wf_selected_count'])}/{int(row['wf_total_folds'])}), "
            f"even though the bootstrap CI lower bound still crosses zero at {fmt_pct(float(row['ci_lower']))}."
        )
    if rule_id == "CD_CORE_K8":
        return (
            f"Paper now because holdout is positive in both years ({fmt_pct(float(row['holdout_2024_roi']))}, "
            f"{fmt_pct(float(row['holdout_2025_roi']))}), but the forward sample is still smaller than the OP anchor, "
            f"walk-forward selection is only {int(row['wf_selected_count'])}/{int(row['wf_total_folds'])}, "
            f"and the bootstrap CI lower bound still crosses zero at {fmt_pct(float(row['ci_lower']))}."
        )
    if rule_id == "OP_REFINED_K7":
        return (
            f"Watch only because the ROI is attractive, but the holdout sample is only {int(row['holdout_races'])} races "
            f"and 2024 was a losing year ({fmt_pct(float(row['holdout_2024_roi']))}), even though the bootstrap CI lower bound is positive at {fmt_pct(float(row['ci_lower']))}."
        )
    raise ValueError(rule_id)


def family_caution(rule_id: str) -> str:
    if rule_id == "OP_DURABLE_K7":
        return "OP is the strongest current family, but the refined OP variant still lacks enough forward sample to replace this anchor."
    if rule_id == "CD_CORE_K8":
        return "CD family caution: the more selective CD_REFINED_K9 looked better in-sample but lost on 2024-2025 holdout, so keep the simpler CD rule on paper only."
    if rule_id == "OP_REFINED_K7":
        return "Interesting OP challenger, but still not strong enough to displace the durable OP rule."
    raise ValueError(rule_id)


def shadow_rank(rule_id: str) -> str:
    mapping = {
        "OP_DURABLE_K7": "LIVE_DEFAULT",
        "CD_CORE_K8": "PRIMARY_SHADOW",
        "OP_REFINED_K7": "SECONDARY_SHADOW",
    }
    return mapping[rule_id]


def promotion_blocker(rule_id: str, row: pd.Series) -> str:
    if rule_id == "OP_DURABLE_K7":
        return "n/a — this is the current anchor"
    if rule_id == "CD_CORE_K8":
        return (
            f"Needs materially more forward sample than {int(row['holdout_races'])} holdout races and much better walk-forward recurrence than "
            f"{int(row['wf_selected_count'])}/{int(row['wf_total_folds'])}."
        )
    if rule_id == "OP_REFINED_K7":
        return (
            f"Needs more forward races than {int(row['holdout_races'])} plus a non-losing second holdout year; "
            f"2024 is still {fmt_pct(float(row['holdout_2024_roi']))}."
        )
    raise ValueError(rule_id)


def build_dataframe(
    scorecard_path: Path = SCORECARD_PATH,
    frozen_eval_path: Path = FROZEN_EVAL_PATH,
) -> pd.DataFrame:
    score_df, frozen_df = load_inputs(scorecard_path=scorecard_path, frozen_eval_path=frozen_eval_path)
    score_df = score_df[score_df["rule_id"].isin(TARGET_RULES)].copy()
    score_df = score_df.set_index("rule_id")

    anchor_holdout_races = int(score_df.loc["OP_DURABLE_K7", "holdout_races"])
    anchor_wf_selected = int(score_df.loc["OP_DURABLE_K7", "wf_selected_count"])
    anchor_holdout_roi = float(score_df.loc["OP_DURABLE_K7", "holdout_roi"])

    rows: list[dict] = []
    for rule_id in TARGET_RULES:
        row = score_df.loc[rule_id]
        year_2024 = get_rule_slice(frozen_df, rule_id, "year_2024")
        year_2025 = get_rule_slice(frozen_df, rule_id, "year_2025")

        holdout_roi = float(row["holdout_roi"])
        holdout_races = int(row["holdout_races"])
        wf_selected_count = int(row["wf_selected_count"])
        wf_total_folds = int(row["wf_total_folds"])

        enriched_row = pd.Series(
            {
                **row.to_dict(),
                "holdout_2024_roi": float(year_2024["roi"]),
                "holdout_2025_roi": float(year_2025["roi"]),
            }
        )

        rows.append(
            {
                "rule_id": rule_id,
                "family": family(rule_id),
                "phase": row["phase"],
                "role": current_role(rule_id),
                "shadow_rank": shadow_rank(rule_id),
                "holdout_roi": holdout_roi,
                "holdout_races": holdout_races,
                "holdout_profit": float(row["holdout_profit"]),
                "holdout_2024_roi": float(year_2024["roi"]),
                "holdout_2024_races": int(row["holdout_2024_races"]),
                "holdout_2025_roi": float(year_2025["roi"]),
                "holdout_2025_races": int(row["holdout_2025_races"]),
                "holdout_years_positive": row["holdout_years"],
                "holdout_worst_year_roi": float(row["worst_year_roi"]),
                "wf_selected_count": wf_selected_count,
                "wf_total_folds": wf_total_folds,
                "wf_selected": row["wf_selected"],
                "ci_lower": float(row["ci_lower"]) if pd.notna(row["ci_lower"]) else None,
                "backtest_roi": float(row["backtest_roi"]),
                "backtest_races": int(row["backtest_races"]),
                "forward_trust": float(row["forward_trust"]),
                "scorecard_tier": row["tier"],
                "holdout_roi_vs_anchor": round(holdout_roi - anchor_holdout_roi, 2),
                "holdout_races_vs_anchor": holdout_races - anchor_holdout_races,
                "wf_selected_vs_anchor": wf_selected_count - anchor_wf_selected,
                "decision_reason": decision_reason(rule_id, enriched_row),
                "promotion_blocker": promotion_blocker(rule_id, enriched_row),
                "family_caution": family_caution(rule_id),
                "note": row["note"],
            }
        )

    df = pd.DataFrame(rows)
    role_order = {"ANCHOR": 0, "PAPER": 1, "WATCH": 2}
    df["sort_order"] = df["role"].map(role_order)
    df = df.sort_values(["sort_order", "holdout_races"], ascending=[True, False]).reset_index(drop=True)
    return df.drop(columns=["sort_order"])


def build_markdown(
    df: pd.DataFrame,
    scorecard_csv_name: str = SCORECARD_PATH.name,
    scorecard_json_name: str = SCORECARD_JSON_PATH.name,
    frozen_eval_csv_name: str = FROZEN_EVAL_PATH.name,
    compare_json_name: str = COMPARE_MAIN_JSON_PATH.name,
    current_evidence_json_name: str = CURRENT_EVIDENCE_JSON_PATH.name,
    csv_output_name: str = OUT_CSV.name,
    md_output_name: str = OUT_MD.name,
    scorecard_path: Path = SCORECARD_PATH,
    scorecard_json_path: Path = SCORECARD_JSON_PATH,
    compare_json_path: Path = COMPARE_MAIN_JSON_PATH,
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON_PATH,
    source_paths: dict[str, Path] | None = None,
) -> str:
    broader_watch = load_scorecard_df(scorecard_path).set_index("rule_id")
    ranking_contract = load_scorecard_ranking_contract(scorecard_json_path)
    decision_gates = load_scorecard_decision_gate_minimums(scorecard_json_path)
    ci_only_diagnostic = load_scorecard_ci_only_diagnostic(scorecard_json_path)
    operator_boundary = load_current_operator_boundary(compare_json_path)
    current_gate_progress = load_current_gate_progress(current_evidence_json_path)
    scorecard_audit_route = load_scorecard_audit_route(current_evidence_json_path)
    rebuild_validation_contract = load_rebuild_validation_contract(current_evidence_json_path)
    fingerprints = source_file_fingerprints(source_paths)
    kee = broader_watch.loc["KEE_K9"]
    sa = broader_watch.loc["SA_K9"]
    dmr = broader_watch.loc["DMR_FALL_K7"]
    anchor_gate = decision_gates["anchor_displacement"]
    phase8_gate = decision_gates["phase8_promotion_review"]
    real_money_gate = decision_gates["real_money_discussion"]
    ci_only_source = f"{scorecard_json_name}:{OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}"
    rebuild_order_read = " -> ".join(f"`{command}`" for command in rebuild_validation_contract["upstream_refresh_commands"])
    if operator_boundary["operator_read_gate"].get("requires_refresh_before_evidence_read"):
        operator_gate_boundary_read = (
            "The saved top card must be refreshed before evidence/instruction use; this read gate is not "
            "no-target evidence, clean-empty evidence, bet readiness, settled ROI, cross-family promotion "
            "readiness, live profitability, bankroll guidance, or real-money evidence"
        )
    else:
        operator_gate_boundary_read = (
            "The saved top card can be read as current operator routing context only; this read gate is not "
            "no-target evidence, clean-empty evidence, bet readiness, settled ROI, cross-family promotion "
            "readiness, live profitability, bankroll guidance, or real-money evidence"
        )

    lines = [
        "# Cross-Family Decision Card",
        "",
        "This note compares the three most relevant rules for the current paper-decision hierarchy:",
        "`OP_DURABLE_K7`, `CD_CORE_K8`, and `OP_REFINED_K7`.",
        "",
        "Short answer:",
        "- **Keep `OP_DURABLE_K7` as the anchor**",
            "- **Paper trade `CD_CORE_K8`, but do not let it replace the anchor yet**",
            "- **Keep `OP_REFINED_K7` on watch, not as a promoted paper default**",
            f"`valid_evidence_scope={VALID_EVIDENCE_SCOPE}`",
            "- Treat those roles as evidence-ranked, not statistically clean slam dunks: `OP_DURABLE_K7` still has CI low `-3.40%`, `CD_CORE_K8` still has CI low `-15.00%`, and `OP_REFINED_K7` only gets a positive CI low `+11.20%` on a much smaller holdout sample.",
            f"- Scorecard CI-only promotion check: `{ci_only_source}` says `ci_only_promotion_allowed={str(ci_only_diagnostic['ci_only_promotion_allowed']).lower()}`; the positive OP_REFINED CI lower bound is support context only, not a promotion trigger.",
            f"- Inherited scorecard ranking contract: rank is tier-first (`{ranking_contract['rank_is_tier_first_decision_order']}`), Score is secondary within tier (`{ranking_contract['forward_trust_is_secondary_within_tier']}`), and raw Score is not an automatic deployment instruction (`{ranking_contract['raw_score_is_not_an_automatic_deployment_instruction']}`).",
            f"- Inherited operator read gate: `{compare_json_name}` `current_operator_boundary.operator_read_gate` says {(operator_boundary['operator_read_gate'])['read']} This is routing context only, not no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money evidence.",
            f"- Bridge-published current gate progress: `{current_evidence_json_name}` `decision_gate_progress` says {current_gate_progress['read']} This is routing context only, not anchor proof or cross-family promotion evidence.",
            f"- Scorecard audit route: `{current_evidence_json_name}` `scorecard_audit_route` says {scorecard_audit_route['route_read']} This is report-synchronization metadata only, not cross-family evidence, forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- Current bridge rebuild order: `{current_evidence_json_name}` `rebuild_validation_contract` routes source-byte changes through {rebuild_order_read} before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not cross-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            "This note is intentionally pinned to the frozen 2024-2025 holdout standard carried by the scorecard and frozen-evaluation artifacts, so a prettier line from some other window does not quietly rewrite the paper-decision shortlist.",
        "",
        "## Comparison Table",
        "",
        "This table keeps the shortlist split-aware on purpose: year-specific race counts matter, because a prettier annual ROI line means less when it comes from a much smaller slice.",
        "Here, `WF Selected` is train-only selection recurrence context, not a second profit line or extra train-only validation layer.",
        "",
        "| Rule | Family | Role | Holdout ROI | Holdout Races | 2024 ROI / N | 2025 ROI / N | Holdout Years+ | WF Selected | CI Lower | Why It Sits Here |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for _, row in df.iterrows():
        ci = "n/a" if pd.isna(row["ci_lower"]) else fmt_pct(float(row["ci_lower"]))
        lines.append(
            f"| {row['rule_id']} | {row['family']} | {row['role']} | {fmt_pct(float(row['holdout_roi']))} | "
            f"{int(row['holdout_races'])} | {fmt_pct(float(row['holdout_2024_roi']))} / {int(row['holdout_2024_races'])} | "
            f"{fmt_pct(float(row['holdout_2025_roi']))} / {int(row['holdout_2025_races'])} | "
            f"{row['holdout_years_positive']} | {row['wf_selected']} | {ci} | {row['decision_reason']} |"
        )

    lines.extend(
        [
            "",
            "## Why the Current Roles Make Sense",
            "",
        ]
    )

    for _, row in df.iterrows():
        lines.append(f"- **{row['rule_id']} ({row['role']})**: {row['decision_reason']}")
        lines.append(f"  - Family caution: {row['family_caution']}")

    lines.extend(
        [
            "",
            "## Paper Companion and Shadow Read",
            "",
            "If Cole asks how the non-anchor paper roles split in the current hierarchy:",
            f"- **Primary paper companion: `CD_CORE_K8`**. It is the cleanest non-anchor paper companion because both holdout years are positive (`2024 {fmt_pct(float(df.loc[df['rule_id'] == 'CD_CORE_K8', 'holdout_2024_roi'].iloc[0]))} on {int(df.loc[df['rule_id'] == 'CD_CORE_K8', 'holdout_2024_races'].iloc[0])}`, `2025 {fmt_pct(float(df.loc[df['rule_id'] == 'CD_CORE_K8', 'holdout_2025_roi'].iloc[0]))} on {int(df.loc[df['rule_id'] == 'CD_CORE_K8', 'holdout_2025_races'].iloc[0])}`), but it still trails the anchor badly on sample depth (`60` vs `115`), walk-forward selection (`1/10` vs `7/10`), and CI strength (still `{fmt_pct(float(df.loc[df['rule_id'] == 'CD_CORE_K8', 'ci_lower'].iloc[0]))}` at the lower bound).",
            f"- **Same-family OP shadow challenger: `OP_REFINED_K7`**. It is the more explosive OP upside path, and its CI lower bound is positive at `{fmt_pct(float(df.loc[df['rule_id'] == 'OP_REFINED_K7', 'ci_lower'].iloc[0]))}`, but it still needs more forward races than `{int(df.loc[df['rule_id'] == 'OP_REFINED_K7', 'holdout_races'].iloc[0])}` and a non-losing second holdout year before it can seriously challenge the anchor (`2024 {fmt_pct(float(df.loc[df['rule_id'] == 'OP_REFINED_K7', 'holdout_2024_roi'].iloc[0]))}`, `2025 {fmt_pct(float(df.loc[df['rule_id'] == 'OP_REFINED_K7', 'holdout_2025_roi'].iloc[0]))}`).",
            "",
            "### Scorecard CI-Only Promotion Check",
            "",
            f"Source: `{ci_only_source}`",
            f"- Current decision: {ci_only_diagnostic['current_decision']}",
            f"- CI-only promotion allowed: `{str(ci_only_diagnostic['ci_only_promotion_allowed']).lower()}`",
            f"- Why not: {', '.join(ci_only_diagnostic['why_not'])}.",
            f"- Required before review: phase8 promotion review = {ci_only_diagnostic['required_before_review']['phase8_promotion_review']}; anchor displacement = {ci_only_diagnostic['required_before_review']['anchor_displacement']}.",
            f"- Does not count: {', '.join(ci_only_diagnostic['does_not_count'])}.",
            "",
            "## Not in the near-promotion shortlist",
            "",
            "The rest of the current Phase 8 watch list is still observation-only, not part of the near-term cross-family promotion queue:",
            f"- `KEE_K9`: keep logging it, but it still has only {int(kee['holdout_races'])} holdout races, CI low {fmt_pct(float(kee['ci_lower']))}, and only {kee['wf_selected']} walk-forward support.",
            f"- `SA_K9`: still only {int(sa['holdout_races'])} holdout races and {sa['wf_selected']} walk-forward support, even though both observed holdout years are positive.",
            f"- `DMR_FALL_K7`: still only {int(dmr['holdout_races'])} holdout races, just one observed holdout year, and {dmr['wf_selected']} walk-forward support.",
            "Those pockets are worth observing, but they are not peers of `CD_CORE_K8` or `OP_REFINED_K7` for current paper-hierarchy promotion decisions.",
            "",
            "## Decision-Change Gates",
            "",
            f"These gates are loaded directly from `{scorecard_json_name}` `decision_gate_minimums`. They are posture-review floors, not proof of profitability.",
            "",
            "| Gate | Scorecard-sourced minimum | What it means here | Threshold source |",
            "|---|---:|---|---|",
            f"| Anchor displacement | {anchor_gate['minimum_roi_complete_same_candidate_observations']} ROI-complete same-candidate observations | Minimum before any non-anchor rule can challenge `OP_DURABLE_K7`; `CD_CORE_K8` can remain the paper companion, but it does not become the anchor from holdout ROI alone | `{anchor_gate['threshold_source']}` |",
            f"| Phase 8 promotion review | {phase8_gate['minimum_roi_complete_settled_observations']} ROI-complete shadow observations | Minimum before reviewing `OP_REFINED_K7` or another Phase 8 watch rule for promotion; this does not override the stricter anchor-displacement bar | `{phase8_gate['threshold_source']}` |",
            f"| Real-money discussion | {real_money_gate['minimum_total_settled_roi_complete_observations']} total ROI-complete settled paper observations | Minimum before any real-money confidence or bankroll discussion, with concentration/payout sanity checks and no BAQ-as-BEL substitution | `{real_money_gate['threshold_source']}` |",
            "",
            "Clean empty scans, open paper signals, historical replay rows, source fingerprints, green validators, compatibility labels, or a WATCH label do not satisfy these gates.",
            "",
            "## Current Paper Snapshot",
            "",
            f"This context is inherited from `{compare_json_name}` / `{operator_boundary['source_path']}` so the cross-family card shows the current paper-workflow boundary without turning it into cross-family promotion evidence.",
            "",
            "| Field | Current bridge read | Evidence boundary |",
            "|---|---|---|",
            f"| Source freshness | `{operator_boundary['right_now_freshness_state']}`; refresh before right-now use = `{operator_boundary['requires_refresh_before_right_now_use']}`; bridge reference = `{operator_boundary['source_freshness_generated_reference_date']}` (`{operator_boundary['source_freshness_generated_reference_timezone']}`); comparison = `{operator_boundary['source_freshness_staleness_comparison_source']}` / `{operator_boundary['source_freshness_staleness_comparison_date']}`; read = {md_cell(operator_boundary['source_freshness_read'])} | Source freshness is operator-readiness metadata, not performance proof |",
            f"| Refresh action boundary | `{operator_boundary['refresh_action_command']}` required before right-now use = `{operator_boundary['refresh_required_before_right_now_instruction_use']}`; can update surfaces = `{operator_boundary['refresh_can_update_operator_surfaces']}`; settles rows / creates ROI evidence / clean-empty performance = `{operator_boundary['refresh_can_settle_open_rows_by_itself']}` / `{operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}` / `{operator_boundary['clean_empty_refresh_counts_as_forward_performance']}` | Wrapper refresh is operator routing only; it is not settled ROI, promotion readiness, live profitability, or real-money evidence |",
            f"| Operator read gate | `{compare_json_name}` `current_operator_boundary.operator_read_gate`: {md_cell(operator_boundary['operator_read_gate']['read'])} Gate status = `{operator_boundary['operator_read_gate']['gate_status']}`; recommended command = `{operator_boundary['operator_read_gate']['recommended_command']}` | {operator_gate_boundary_read} |",
            f"| Bridge-published gate progress | `{current_evidence_json_name}` `decision_gate_progress`: {md_cell(current_gate_progress['read'])} Source: `{current_gate_progress['source_path']}` `{current_gate_progress['source_json_path']}`; gate status = `{current_gate_progress['gate_status']}` | Current gates are all uncleared routing context only; they do not change the frozen ANCHOR / PAPER / WATCH ordering or create settled ROI, OP-anchor proof, cross-family promotion readiness, live-profitability, bankroll, or real-money evidence |",
            f"| Scorecard audit route | `{current_evidence_json_name}` `scorecard_audit_route`: {md_cell(scorecard_audit_route['route_read'])} Validator: `{scorecard_audit_route['validator_command']}`; artifacts: `{scorecard_audit_route['markdown_path']}` / `{scorecard_audit_route['json_path']}`; gate snapshot = 30/20/100 with no-BAQ-as-BEL required `{scorecard_audit_route['gate_floor_snapshot']['real_money_no_baq_as_bel_required']}` | Report-synchronization route only; it is not cross-family evidence, forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
            f"| Current bridge rebuild order | `{current_evidence_json_name}` `rebuild_validation_contract`: {rebuild_order_read} before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes | Provenance/rebuild route only; green checks and rebuild order are not cross-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
            f"| Current settled rule mix | OP_DURABLE_K7={operator_boundary['op_anchor_roi_complete_rows']}; CD_CORE_K8={operator_boundary['cd_companion_roi_complete_rows']}; {md_cell(operator_boundary['primary_rule_mix_read'])} | Rule-specific settled rows stay separate; CD-only paper rows are not OP-anchor or cross-family promotion evidence |",
            f"| Settlement queue state | `{operator_boundary['open_settlement_queue_state']}`; {md_cell(operator_boundary['open_settlement_context'])}; detail: {md_cell(operator_boundary['open_settlement_queue_read'])} | Open rows are settlement workflow only; fill outcomes from actual result/payout evidence before interpreting ROI |",
            f"| Recommendation context | {md_cell(operator_boundary['recommendation_context_read'])} | Latest recommendation-state context is operator routing only, not bet readiness or forward-performance evidence |",
            f"| Operator route | `{operator_boundary['best_action_command']}` | Use the route to settle or refresh; do not infer profit, promotion, or real-money readiness from the route itself |",
            "",
            "The current operator boundary is routing/provenance context only. It does not change the frozen ANCHOR / PAPER / WATCH ordering above, and it is not settled ROI, OP-anchor proof, cross-family promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            "",
            "## Head-to-Head vs. the Anchor",
            "",
            "| Rule | Holdout ROI vs Anchor | Holdout Races vs Anchor | WF Selected vs Anchor | Promotion Blocker | Practical Read |",
            "|---|---:|---:|---:|---|---|",
        ]
    )

    for _, row in df[df["rule_id"] != "OP_DURABLE_K7"].iterrows():
        if row["rule_id"] == "CD_CORE_K8":
            practical = "Better holdout ROI than the anchor, but on only 60 races and with much weaker walk-forward selection."
        else:
            practical = "Higher ROI than the anchor, but smaller sample and still includes a losing holdout year."
        lines.append(
            f"| {row['rule_id']} | {fmt_pct(float(row['holdout_roi_vs_anchor']))} | {int(row['holdout_races_vs_anchor'])} | "
            f"{int(row['wf_selected_vs_anchor'])} | {row['promotion_blocker']} | {practical} |"
        )

    lines.extend(
        [
            "",
            "## Bottom Line",
            "",
            "If Cole wants one clean current paper hierarchy:",
            "- read the shortlist with the split counts attached, not just the aggregate ROI columns; `OP_DURABLE_K7` still leads, but its own holdout path was uneven (`2024 -47.41% on 68`, `2025 +124.61% on 47`).",
            "",
            "1. **Anchor:** `OP_DURABLE_K7`",
            "2. **Paper companion alongside it:** `CD_CORE_K8`",
            "3. **Watch / same-family shadow challenger:** `OP_REFINED_K7`",
            "",
            "That ordering is intentionally conservative. It protects against promoting the prettiest small-sample ROI line over the strongest forward-evidence anchor.",
            f"Scorecard rank-contract override: {ranking_contract['known_rank_override']}",
            "Treat the walk-forward-selected counts as recurrence context for how often each rule survives train-only yearly selection, not as fresh standalone profit proof.",
            "",
            "## Validation",
            "",
            f"- Sources: `{scorecard_csv_name}`, `{scorecard_json_name}`, `{frozen_eval_csv_name}`, `{compare_json_name}`, `{current_evidence_json_name}`",
            f"- Wrote: `{csv_output_name}`, `{md_output_name}`",
            "- This card is a read-only synthesis of existing frozen evaluation artifacts",
            "",
            "## Source Provenance",
            "",
            "Exact input-byte fingerprints for this cross-family card. Use them as reproducibility metadata only; they do not prove settled paper ROI, promotion readiness, live profitability, or real-money performance.",
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
    scorecard_path = Path(args.scorecard_csv)
    scorecard_json_path = Path(args.scorecard_json)
    frozen_eval_path = Path(args.frozen_eval_csv)
    compare_json_path = Path(args.compare_main_json)
    current_evidence_json_path = Path(args.current_evidence_json)
    csv_output = Path(args.csv_output)
    md_output = Path(args.md_output)

    load_scorecard_ranking_contract(scorecard_json_path)
    load_scorecard_decision_gate_minimums(scorecard_json_path)
    load_scorecard_ci_only_diagnostic(scorecard_json_path)
    load_current_operator_boundary(compare_json_path)
    load_current_gate_progress(current_evidence_json_path)
    load_scorecard_audit_route(current_evidence_json_path)
    load_rebuild_validation_contract(current_evidence_json_path)

    df = build_dataframe(scorecard_path=scorecard_path, frozen_eval_path=frozen_eval_path)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_output, index=False)
    report = build_markdown(
        df,
        scorecard_csv_name=scorecard_path.name,
        scorecard_json_name=scorecard_json_path.name,
        frozen_eval_csv_name=frozen_eval_path.name,
        compare_json_name=compare_json_path.name,
        current_evidence_json_name=current_evidence_json_path.name,
        csv_output_name=csv_output.name,
        md_output_name=md_output.name,
        scorecard_path=scorecard_path,
        scorecard_json_path=scorecard_json_path,
        compare_json_path=compare_json_path,
        current_evidence_json_path=current_evidence_json_path,
        source_paths={
            "forward_evidence_scorecard_csv": scorecard_path,
            "forward_evidence_scorecard_json": scorecard_json_path,
            "frozen_portfolio_eval": frozen_eval_path,
            "compare_main_approaches_json": compare_json_path,
            "current_evidence_summary": current_evidence_json_path,
        },
    )
    if not report.endswith("\n"):
        report += "\n"
    md_output.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"Saved: {csv_output.name}")
    print(f"Saved: {md_output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
