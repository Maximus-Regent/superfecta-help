#!/usr/bin/env python3
"""
OP family decision card.

Purpose:
- Compare the realistic OP candidates side by side.
- Keep OP_DURABLE_K7 as the default anchor unless a challenger clearly clears
  a conservative replacement bar.
- Produce a short report Cole can use without digging through multiple files.

Outputs:
- op_family_decision.csv
- OP_FAMILY_DECISION.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

import compare_main_approaches as cma

BASE = Path(__file__).resolve().parent
CACHE_PATH = BASE / "phase5_race_cache.pkl"
PHASE7_RULES_PATH = BASE / "phase7_live_rules.json"
WF_RULES_PATH = BASE / "walk_forward_validation_rules.csv"
SCORECARD_CSV = BASE / "forward_evidence_scorecard.csv"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
COMPARE_MAIN_JSON = BASE / "compare_main_approaches.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
OUT_CSV = BASE / "op_family_decision.csv"
OUT_MD = BASE / "OP_FAMILY_DECISION.md"
SOURCE_FINGERPRINT_PATHS = {
    "compare_main_approaches": Path(cma.__file__).resolve(),
    "compare_main_approaches_json": COMPARE_MAIN_JSON,
    "current_evidence_summary": CURRENT_EVIDENCE_JSON,
    "phase5_race_cache": CACHE_PATH,
    "phase7_rules": PHASE7_RULES_PATH,
    "walk_forward_rules": WF_RULES_PATH,
    "forward_evidence_scorecard_csv": SCORECARD_CSV,
    "forward_evidence_scorecard_json": SCORECARD_JSON,
}
REQUIRED_PHASE7_RULE_KEYS = {
    "rule_id",
    "track",
    "k",
    "field_min",
    "field_max",
    "gap_min",
    "fav_prob_min",
    "condition",
    "card_min",
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
REQUIRED_SCORECARD_COLUMNS = {"rule_id", "ci_lower"}
REQUIRED_CACHE_COLUMNS = {
    "track",
    "eligible_7",
    "fs",
    "prob_gap",
    "fav_prob",
    "is_fast",
    "rnum",
    "month",
    "hit_7",
    "payout",
    "year",
}
REQUIRED_OP_RULE_IDS = ("OP_DURABLE_K7", "OP_REFINED_K7")
REQUIRED_DECISION_GATE_KEYS = (
    "anchor_displacement",
    "phase8_promotion_review",
    "real_money_discussion",
)
REQUIRED_CURRENT_GATE_PROGRESS_FIELDS = {
    "source_path",
    "source_json_path",
    "valid_use",
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
    "open_settlement_rows",
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
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
VALID_EVIDENCE_SCOPE = "split_aware_op_family_anchor_review_only"
OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY = "ci_only_promotion_diagnostics.OP_REFINED_K7"
REQUIRED_CI_ONLY_WHY_NOT = (
    "smaller holdout sample than OP_DURABLE_K7",
    "losing 2024 holdout split",
    "lower walk-forward recurrence than OP_DURABLE_K7",
    "uncleared phase8_promotion_review paper-observation gate",
    "uncleared anchor_displacement paper-observation gate",
)


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
    p = argparse.ArgumentParser(description="Build the OP family decision card")
    p.add_argument("--cache-pkl", default=str(CACHE_PATH), help="phase5 race cache pickle path")
    p.add_argument("--phase7-rules-json", default=str(PHASE7_RULES_PATH), help="Phase 7 rules JSON path")
    p.add_argument("--wf-rules-csv", default=str(WF_RULES_PATH), help="walk-forward rules CSV path")
    p.add_argument("--scorecard-csv", default=str(SCORECARD_CSV), help="forward evidence scorecard CSV path")
    p.add_argument("--scorecard-json", default=str(SCORECARD_JSON), help="forward evidence scorecard JSON path")
    p.add_argument("--compare-json", default=str(COMPARE_MAIN_JSON), help="compare-main JSON sidecar path")
    p.add_argument("--current-evidence-json", default=str(CURRENT_EVIDENCE_JSON), help="current evidence bridge JSON path")
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


def require_exactly_one_rule_row(df: pd.DataFrame, source_path: Path, *, rule_id: str, label: str) -> None:
    matches = df[df["rule_id"] == rule_id]
    if matches.empty:
        raise ValueError(f"{source_path.name} is missing required {label} rows: {rule_id}")
    if len(matches) != 1:
        raise ValueError(f"{source_path.name} has duplicate required {label} rows: {rule_id}")


def load_cache(cache_path: Path = CACHE_PATH) -> pd.DataFrame:
    df = pd.read_pickle(cache_path).copy()
    require_columns(df, REQUIRED_CACHE_COLUMNS, cache_path, "cache")
    df["second_prob"] = df["fav_prob"] - df["prob_gap"]
    df["top2_mass"] = df["fav_prob"] + df["second_prob"]
    return df


def load_phase7_rules(phase7_rules_path: Path = PHASE7_RULES_PATH) -> list[dict]:
    payload = json.loads(phase7_rules_path.read_text())
    if "rules" not in payload or not isinstance(payload["rules"], list):
        raise ValueError(f"{phase7_rules_path.name} must contain a top-level rules list")

    rules: list[dict] = []
    for idx, raw in enumerate(payload["rules"]):
        missing_keys = sorted(REQUIRED_PHASE7_RULE_KEYS - set(raw.keys()))
        if missing_keys:
            raise ValueError(
                f"{phase7_rules_path.name} rule index {idx} is missing required Phase 7 rule keys: {', '.join(missing_keys)}"
            )
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

    durable_rules = [rule for rule in rules if rule["rule_id"] == "OP_DURABLE_K7"]
    if not durable_rules:
        raise ValueError(f"{phase7_rules_path.name} is missing required Phase 7 OP rule rows: OP_DURABLE_K7")
    if len(durable_rules) != 1:
        raise ValueError(f"{phase7_rules_path.name} has duplicate required Phase 7 OP rule rows: OP_DURABLE_K7")
    return rules


def load_wf_rule_df(wf_rules_path: Path = WF_RULES_PATH) -> pd.DataFrame:
    df = pd.read_csv(wf_rules_path)
    require_columns(df, REQUIRED_WF_RULE_COLUMNS, wf_rules_path, "walk-forward rules")

    observed_years = {int(y) for y in df["test_year"].dropna().tolist()}
    check_years = sorted(observed_years | set(cma.DEFAULT_HOLDOUT_YEARS))
    missing_rows: list[str] = []
    duplicate_rows: list[str] = []
    for year in check_years:
        year_df = df[df["test_year"] == year]
        for rule_id in REQUIRED_OP_RULE_IDS:
            matches = year_df[year_df["rule_id"] == rule_id]
            key = f"{rule_id}/year_{year}"
            if matches.empty:
                missing_rows.append(key)
            elif len(matches) != 1:
                duplicate_rows.append(key)

    if missing_rows:
        raise ValueError(
            f"{wf_rules_path.name} is missing required walk-forward OP rule rows: {', '.join(missing_rows)}"
        )
    if duplicate_rows:
        raise ValueError(
            f"{wf_rules_path.name} has duplicate required walk-forward OP rule rows: {', '.join(duplicate_rows)}"
        )
    return df


def load_scorecard(scorecard_path: Path = SCORECARD_CSV) -> pd.DataFrame:
    df = pd.read_csv(scorecard_path)
    require_columns(df, REQUIRED_SCORECARD_COLUMNS, scorecard_path, "scorecard")
    for rule_id in REQUIRED_OP_RULE_IDS:
        require_exactly_one_rule_row(df, scorecard_path, rule_id=rule_id, label="scorecard rule")

    anchor_ci = df.loc[df["rule_id"] == "OP_DURABLE_K7", "ci_lower"].iloc[0]
    if pd.isna(anchor_ci):
        raise ValueError(f"{scorecard_path.name} has blank required ci_lower for OP_DURABLE_K7")

    return df.set_index("rule_id")


def load_scorecard_ranking_contract(scorecard_json_path: Path = SCORECARD_JSON) -> dict[str, object]:
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


def load_current_operator_boundary(compare_json_path: Path = COMPARE_MAIN_JSON) -> dict[str, Any]:
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
    boundary["operator_read_gate"] = cma.validate_operator_read_gate(
        boundary,
        f"{compare_json_path.name} current_operator_boundary",
    )
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


def load_rebuild_validation_contract(current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
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


def build_method_rows(
    cache_path: Path = CACHE_PATH,
    phase7_rules_path: Path = PHASE7_RULES_PATH,
    wf_rules_path: Path = WF_RULES_PATH,
) -> list[dict]:
    df = load_cache(cache_path)
    phase7_rules = load_phase7_rules(phase7_rules_path)
    rule_df = load_wf_rule_df(wf_rules_path)

    holdout_years = sorted(set(cma.DEFAULT_HOLDOUT_YEARS))
    wf_years = sorted(int(y) for y in rule_df["test_year"].unique().tolist())

    durable_rules = [r for r in phase7_rules if r["rule_id"] == "OP_DURABLE_K7"]
    refined_rules = [r for r in cma.PHASE8_FROZEN_RULES if r["rule_id"] == "OP_REFINED_K7"]
    if len(refined_rules) != 1:
        raise ValueError("compare_main_approaches.PHASE8_FROZEN_RULES must contain exactly one OP_REFINED_K7 rule")

    durable_wf = cma.evaluate_fixed_method(df, durable_rules, wf_years)
    durable_holdout = cma.evaluate_fixed_method(df, durable_rules, holdout_years)

    refined_wf = cma.evaluate_fixed_method(df, refined_rules, wf_years)
    refined_holdout = cma.evaluate_fixed_method(df, refined_rules, holdout_years)

    op_rules_df = rule_df[rule_df["test_year"].isin(wf_years)].copy()
    switch_wf, switch_choices = cma.dynamic_op_switch_rows(op_rules_df)
    switch_holdout, holdout_choices = cma.dynamic_op_switch_rows(
        rule_df[rule_df["test_year"].isin(holdout_years)].copy()
    )

    recent_switches = ", ".join(
        f"{int(row.test_year)}={row.rule_id}" for _, row in switch_choices.tail(min(4, len(switch_choices))).iterrows()
    )
    holdout_switches = ", ".join(
        f"{int(row.test_year)}={row.rule_id}" for _, row in holdout_choices.iterrows()
    )

    rows = [
        {
            "method_id": "op_durable_only",
            "label": "OP_DURABLE_K7",
            "method_type": "fixed anchor",
            "holdout": durable_holdout,
            "wf": durable_wf,
            "secondary_basis": "frozen replay on walk-forward test years",
            "note": "Largest-sample OP path. This is the safest current paper anchor.",
        },
        {
            "method_id": "op_refined_only",
            "label": "OP_REFINED_K7",
            "method_type": "fixed challenger",
            "holdout": refined_holdout,
            "wf": refined_wf,
            "secondary_basis": "frozen replay on walk-forward test years",
            "note": "Higher ROI, but on much smaller forward samples and with mixed 2024/2025 behavior.",
        },
        {
            "method_id": "op_train_switch",
            "label": "Train-only OP switch",
            "method_type": "dynamic challenger",
            "holdout": switch_holdout,
            "wf": switch_wf,
            "secondary_basis": "actual train-only walk-forward",
            "note": f"Train-only yearly selector across the two OP rules. Holdout choices: {holdout_switches}. Recent WF picks: {recent_switches}.",
        },
    ]
    return rows


def worst_year(stats: dict) -> float:
    year_df = stats["year_df"]
    observed = year_df[year_df["races"] > 0].copy()
    if observed.empty:
        return 0.0
    return round(float(observed["roi"].min()), 2)


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


def build_dataframe(
    cache_path: Path = CACHE_PATH,
    phase7_rules_path: Path = PHASE7_RULES_PATH,
    wf_rules_path: Path = WF_RULES_PATH,
    scorecard_path: Path = SCORECARD_CSV,
) -> pd.DataFrame:
    rows = build_method_rows(cache_path=cache_path, phase7_rules_path=phase7_rules_path, wf_rules_path=wf_rules_path)
    anchor = next(row for row in rows if row["method_id"] == "op_durable_only")
    scorecard = load_scorecard(scorecard_path)

    out_rows = []
    for row in rows:
        holdout = row["holdout"]
        wf = row["wf"]
        holdout_2024 = year_snapshot(holdout, 2024)
        holdout_2025 = year_snapshot(holdout, 2025)

        holdout_roi = float(holdout["roi"])
        holdout_races = int(holdout["races"])
        holdout_positive_years = int(holdout["positive_years"])
        holdout_observed_years = int(holdout["observed_years"])
        wf_roi = float(wf["roi"])
        wf_races = int(wf["races"])
        wf_positive_years = int(wf["positive_years"])
        wf_observed_years = int(wf["observed_years"])

        holdout_beats_anchor = holdout_roi > float(anchor["holdout"]["roi"])
        holdout_sample_matches_anchor = holdout_races >= int(anchor["holdout"]["races"])
        holdout_all_years_positive = (
            holdout_observed_years > 0 and holdout_positive_years == holdout_observed_years
        )
        wf_coverage_matches_anchor = wf_races >= int(anchor["wf"]["races"])
        wf_years_match_anchor = wf_positive_years >= int(anchor["wf"]["positive_years"])

        can_replace_anchor = row["method_id"] == "op_durable_only" or all(
            [
                holdout_beats_anchor,
                holdout_sample_matches_anchor,
                holdout_all_years_positive,
                wf_coverage_matches_anchor,
                wf_years_match_anchor,
            ]
        )

        scorecard_ci_lower = None
        if row["label"] in scorecard.index:
            raw_ci = scorecard.loc[row["label"], "ci_lower"]
            if pd.notna(raw_ci):
                scorecard_ci_lower = float(raw_ci)

        out_rows.append(
            {
                "label": row["label"],
                "method_type": row["method_type"],
                "holdout_roi": holdout_roi,
                "holdout_races": holdout_races,
                "holdout_profit": float(holdout["profit"]),
                "holdout_hit_rate": float(holdout["hit_rate"]),
                "holdout_positive_years": holdout_positive_years,
                "holdout_observed_years": holdout_observed_years,
                "holdout_worst_year_roi": worst_year(holdout),
                "holdout_2024_roi": float(holdout_2024["roi"]),
                "holdout_2024_races": int(holdout_2024["races"]),
                "holdout_2024_profit": float(holdout_2024["profit"]),
                "holdout_2025_roi": float(holdout_2025["roi"]),
                "holdout_2025_races": int(holdout_2025["races"]),
                "holdout_2025_profit": float(holdout_2025["profit"]),
                "holdout_ci_lower": scorecard_ci_lower,
                "wf_roi": wf_roi,
                "wf_races": wf_races,
                "wf_profit": float(wf["profit"]),
                "secondary_basis": row["secondary_basis"],
                "wf_hit_rate": float(wf["hit_rate"]),
                "wf_positive_years": wf_positive_years,
                "wf_observed_years": wf_observed_years,
                "wf_worst_year_roi": worst_year(wf),
                "vs_anchor_holdout_roi_delta": round(holdout_roi - float(anchor["holdout"]["roi"]), 2),
                "vs_anchor_holdout_races_delta": holdout_races - int(anchor["holdout"]["races"]),
                "vs_anchor_wf_roi_delta": round(wf_roi - float(anchor["wf"]["roi"]), 2),
                "vs_anchor_wf_races_delta": wf_races - int(anchor["wf"]["races"]),
                "check_holdout_beats_anchor": holdout_beats_anchor,
                "check_holdout_sample_matches_anchor": holdout_sample_matches_anchor,
                "check_holdout_all_years_positive": holdout_all_years_positive,
                "check_wf_coverage_matches_anchor": wf_coverage_matches_anchor,
                "check_wf_years_match_anchor": wf_years_match_anchor,
                "can_replace_anchor": can_replace_anchor,
                "decision": (
                    "KEEP AS ANCHOR"
                    if row["method_id"] == "op_durable_only"
                    else "PROMOTE" if can_replace_anchor else "KEEP AS WATCH / RESEARCH"
                ),
                "note": row["note"],
            }
        )

    df = pd.DataFrame(out_rows)
    order = {
        "KEEP AS ANCHOR": 0,
        "PROMOTE": 1,
        "KEEP AS WATCH / RESEARCH": 2,
    }
    df["sort_order"] = df["decision"].map(order)
    df = df.sort_values(["sort_order", "holdout_races", "wf_races"], ascending=[True, False, False]).reset_index(drop=True)
    return df.drop(columns=["sort_order"])


def build_markdown(
    df: pd.DataFrame,
    cache_name: str = CACHE_PATH.name,
    phase7_rules_name: str = PHASE7_RULES_PATH.name,
    wf_rules_name: str = WF_RULES_PATH.name,
    scorecard_name: str = SCORECARD_CSV.name,
    scorecard_json_name: str = SCORECARD_JSON.name,
    compare_json_name: str = COMPARE_MAIN_JSON.name,
    current_evidence_json_name: str = CURRENT_EVIDENCE_JSON.name,
    csv_output_name: str = OUT_CSV.name,
    md_output_name: str = OUT_MD.name,
    scorecard_json_path: Path = SCORECARD_JSON,
    compare_json_path: Path = COMPARE_MAIN_JSON,
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
    source_paths: dict[str, Path] | None = None,
) -> str:
    anchor = df[df["label"] == "OP_DURABLE_K7"].iloc[0]
    ranking_contract = load_scorecard_ranking_contract(scorecard_json_path)
    decision_gates = load_scorecard_decision_gate_minimums(scorecard_json_path)
    ci_only_diagnostic = load_scorecard_ci_only_diagnostic(scorecard_json_path)
    operator_boundary = load_current_operator_boundary(compare_json_path)
    current_gate_progress = load_current_gate_progress(current_evidence_json_path)
    scorecard_audit_route = load_scorecard_audit_route(current_evidence_json_path)
    rebuild_validation_contract = load_rebuild_validation_contract(current_evidence_json_path)
    fingerprints = source_file_fingerprints(source_paths)
    anchor_gate = decision_gates["anchor_displacement"]
    phase8_gate = decision_gates["phase8_promotion_review"]
    real_money_gate = decision_gates["real_money_discussion"]
    ci_only_source = f"{scorecard_json_name}:{OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}"
    if operator_boundary["operator_read_gate"].get("requires_refresh_before_evidence_read"):
        operator_gate_boundary_read = (
            "The saved top card must be refreshed before evidence/instruction use; this read gate is not "
            "no-target evidence, clean-empty evidence, OP-anchor proof, bet readiness, settled ROI, "
            "promotion readiness, live profitability, bankroll guidance, or real-money evidence"
        )
    else:
        operator_gate_boundary_read = (
            "The saved top card can be read as current operator routing context only; this read gate is not "
            "no-target evidence, clean-empty evidence, OP-anchor proof, bet readiness, settled ROI, "
            "promotion readiness, live profitability, bankroll guidance, or real-money evidence"
        )
    lines = [
        "# OP Family Decision Card",
        "",
        "This note compares the three realistic OP paths and asks one narrow question:",
        "**does anything clearly beat `OP_DURABLE_K7` strongly enough to replace it as the safest current anchor?**",
        "",
        "Short answer: **no**. The challengers show higher ROI, but not enough forward sample or coverage to replace the durable anchor yet.",
        f"`valid_evidence_scope={VALID_EVIDENCE_SCOPE}`",
        "This note is intentionally locked to the frozen 2024-2025 holdout standard for its primary comparison, so a prettier number from some other window does not quietly rewrite the current OP answer.",
        "Fixed OP rows below use frozen replays on the walk-forward test years as secondary context; only the train-only OP switch row uses actual train-only walk-forward evidence.",
        "For the fixed rows, that secondary context is replay context rather than extra train-only validation.",
        f"Inherited scorecard ranking contract: rank is tier-first (`{ranking_contract['rank_is_tier_first_decision_order']}`), Score is secondary within tier (`{ranking_contract['forward_trust_is_secondary_within_tier']}`), and raw Score is not an automatic deployment instruction (`{ranking_contract['raw_score_is_not_an_automatic_deployment_instruction']}`).",
        f"The anchor itself also still needs caution: `OP_DURABLE_K7` remains the safest current default, but its bootstrap 95% CI lower bound is still `{fmt_pct(float(anchor['holdout_ci_lower']))}`.",
        f"Scorecard CI-only promotion check: `{ci_only_source}` says `ci_only_promotion_allowed={str(ci_only_diagnostic['ci_only_promotion_allowed']).lower()}`; OP_REFINED's positive CI lower bound is support context only, not an anchor-replacement trigger.",
        f"Inherited operator read gate: `{compare_json_name}` `current_operator_boundary.operator_read_gate` says {operator_boundary['operator_read_gate']['read']} This is routing context only, not no-target, clean-empty, bet-readiness, settled-ROI, OP-anchor proof, promotion, live-profitability, bankroll, or real-money evidence.",
        f"Bridge-published current gate progress: `{current_evidence_json_name}` `decision_gate_progress` says {current_gate_progress['read']} This is routing context only, not OP-anchor proof or OP-family promotion evidence.",
        f"Current bridge rebuild order: `{current_evidence_json_name}` `rebuild_validation_contract` routes source-byte changes through {' -> '.join(rebuild_validation_contract['upstream_refresh_commands'])} before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not OP-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        f"Scorecard audit route: `{current_evidence_json_name}` `scorecard_audit_route` points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to `{scorecard_audit_route['markdown_path']}` / `{scorecard_audit_route['json_path']}` plus `{scorecard_audit_route['validator_command']}`; this is report-synchronization metadata only, not OP-family evidence, forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "",
        "## Comparison Table",
        "",
        "This top table is split-aware on purpose: a prettier aggregate OP holdout line should not outrun the year-by-year sample support behind it, and the secondary columns say explicitly whether they are replay context or true train-only walk-forward evidence.",
        "",
        "| Method | Type | Holdout ROI | Holdout Races | 2024 ROI / N | 2025 ROI / N | Holdout Years+ | Worst Holdout Year | Secondary ROI | Secondary Races | Secondary Years+ | Secondary Basis | Decision |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]

    for _, row in df.iterrows():
        lines.append(
            f"| {row['label']} | {row['method_type']} | {fmt_pct(row['holdout_roi'])} | {int(row['holdout_races'])} | "
            f"{fmt_pct(row['holdout_2024_roi'])} / {int(row['holdout_2024_races'])} | {fmt_pct(row['holdout_2025_roi'])} / {int(row['holdout_2025_races'])} | "
            f"{int(row['holdout_positive_years'])}/{int(row['holdout_observed_years'])} | {fmt_pct(row['holdout_worst_year_roi'])} | "
            f"{fmt_pct(row['wf_roi'])} | {int(row['wf_races'])} | {int(row['wf_positive_years'])}/{int(row['wf_observed_years'])} | {row['secondary_basis']} | {row['decision']} |"
        )

    lines.extend(
        [
            "",
            "## 2024-2025 Holdout Split",
            "",
            "This is the simplest honest read on why prettier aggregate ROI is not enough to replace the anchor: the two holdout years behave differently, and the challenger samples are much smaller.",
            "",
            "| Method | 2024 ROI (Races) | 2025 ROI (Races) | Read |",
            "|---|---:|---:|---|",
        ]
    )

    for _, row in df.iterrows():
        if row["label"] == "OP_DURABLE_K7":
            read = "Bigger sample in both years; ugly 2024 but much stronger evidence base overall."
        elif row["label"] == "OP_REFINED_K7":
            read = "Prettier aggregate comes from a smaller two-year sample and a very hot 2025 rebound after a losing 2024."
        else:
            read = "Not independent on holdout yet: it picks OP_REFINED_K7 in both 2024 and 2025, so the split is identical."
        lines.append(
            f"| {row['label']} | {fmt_pct(row['holdout_2024_roi'])} ({int(row['holdout_2024_races'])}) | "
            f"{fmt_pct(row['holdout_2025_roi'])} ({int(row['holdout_2025_races'])}) | {read} |"
        )

    lines.extend(
        [
            "",
            "## Conservative Replacement Bar vs. Anchor",
            "",
            "A challenger only gets promoted in this note if it clears **all** of these conservative checks:",
            "",
            "1. Better holdout ROI than `OP_DURABLE_K7`",
            "2. At least as many 2024-2025 holdout races as `OP_DURABLE_K7`",
            "3. No losing year inside the 2024-2025 holdout window",
            "4. At least as much secondary-context coverage as `OP_DURABLE_K7`",
            "5. At least as many positive secondary-context years as `OP_DURABLE_K7`",
            "",
            "For fixed rules here, that secondary context is a frozen replay on the walk-forward test years; for the train-only switch it is actual train-only walk-forward. Treat the fixed-rule secondary columns as replay context rather than extra train-only validation. The bar is therefore conservative, not perfectly apples-to-apples.",
            "",
            "That bar is intentionally hard. Replacing the anchor should require clearer evidence than simply posting a prettier ROI on a much smaller sample.",
            f"The paper-observation floor for any anchor-displacement discussion is inherited from `{scorecard_json_name}`: {anchor_gate['minimum_roi_complete_same_candidate_observations']} ROI-complete settled observations for the same candidate, with cleaner split-aware evidence than `OP_DURABLE_K7`; source `{anchor_gate['threshold_source']}`.",
            f"Scorecard rank-contract override: {ranking_contract['known_rank_override']}",
            "",
            "| Challenger | Better Holdout ROI? | Match Holdout Sample? | No Losing Holdout Year? | Match WF Coverage? | Match WF Positive Years? | Result |",
            "|---|---|---|---|---|---|---|",
        ]
    )

    for _, row in df[df["label"] != "OP_DURABLE_K7"].iterrows():
        lines.append(
            f"| {row['label']} | {'yes' if row['check_holdout_beats_anchor'] else 'no'} | "
            f"{'yes' if row['check_holdout_sample_matches_anchor'] else 'no'} | "
            f"{'yes' if row['check_holdout_all_years_positive'] else 'no'} | "
            f"{'yes' if row['check_wf_coverage_matches_anchor'] else 'no'} | "
            f"{'yes' if row['check_wf_years_match_anchor'] else 'no'} | {row['decision']} |"
        )

    lines.extend(
        [
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
            "## What This Means",
            "",
            f"- **Keep `OP_DURABLE_K7` as the current paper anchor.** It has {int(anchor['holdout_races'])} holdout races and {int(anchor['wf_races'])} secondary-context races (`{anchor['secondary_basis']}`, so replay context rather than extra train-only validation), which is the strongest forward sample inside the OP family, even though that holdout path was uneven (`2024 {fmt_pct(anchor['holdout_2024_roi'])} on {int(anchor['holdout_2024_races'])}`, `2025 {fmt_pct(anchor['holdout_2025_roi'])} on {int(anchor['holdout_2025_races'])}`).",
            f"- **Anchor caution:** that does not make it a statistically clean slam dunk; the bootstrap 95% CI lower bound for `OP_DURABLE_K7` is still `{fmt_pct(float(anchor['holdout_ci_lower']))}`.",
            "- **Keep `OP_REFINED_K7` as a challenger, not a replacement.** Its ROI is attractive, but its forward sample is much smaller and still includes a losing holdout year.",
            f"- **Do not read raw Score as a promotion queue.** {ranking_contract['known_rank_override']}",
            "- **Treat the train-only OP switch as research context.** It is the only row here with true train-only walk-forward secondary evidence, but in the current holdout window it still collapses to the refined rule anyway, so it does not add independent holdout evidence yet.",
            "",
            "## Decision-Change Gates",
            "",
            f"These gates are loaded directly from `{scorecard_json_name}` `decision_gate_minimums`. They are posture-review floors, not proof of profitability.",
            "",
            "| Gate | Scorecard-sourced minimum | What it means here | Threshold source |",
            "|---|---:|---|---|",
            f"| Anchor displacement | {anchor_gate['minimum_roi_complete_same_candidate_observations']} ROI-complete same-candidate observations | Minimum before discussing whether `OP_REFINED_K7` or any OP switch can replace `OP_DURABLE_K7`; still also needs cleaner split-aware and walk-forward/frozen-standard support | `{anchor_gate['threshold_source']}` |",
            f"| Phase 8 promotion review | {phase8_gate['minimum_roi_complete_settled_observations']} ROI-complete shadow observations | Minimum before reviewing a Phase 8 watch rule for promotion; it does not replace the stricter OP-anchor displacement bar | `{phase8_gate['threshold_source']}` |",
            f"| Real-money discussion | {real_money_gate['minimum_total_settled_roi_complete_observations']} total ROI-complete settled paper observations | Minimum before any real-money confidence or bankroll discussion, with concentration/payout sanity checks and no BAQ-as-BEL substitution | `{real_money_gate['threshold_source']}` |",
            "",
            "Clean empty scans, open paper signals, historical replay rows, source fingerprints, green validators, or a WATCH label do not satisfy these gates.",
            "",
            "## Current OP Paper Snapshot",
            "",
            f"This context is inherited from `{compare_json_name}` / `{operator_boundary['source_path']}` so the OP-family card shows the current paper-workflow boundary without turning it into OP-anchor evidence.",
            "",
            "| Field | Current bridge read | Evidence boundary |",
            "|---|---|---|",
            f"| Source freshness | `{operator_boundary['right_now_freshness_state']}`; refresh before right-now use = `{operator_boundary['requires_refresh_before_right_now_use']}`; bridge reference = `{operator_boundary['source_freshness_generated_reference_date']}` (`{operator_boundary['source_freshness_generated_reference_timezone']}`); comparison = `{operator_boundary['source_freshness_staleness_comparison_source']}` / `{operator_boundary['source_freshness_staleness_comparison_date']}`; read = {cma.md_cell(operator_boundary['source_freshness_read'])} | Source freshness is operator-readiness metadata, not OP performance proof |",
            f"| Refresh action boundary | `{operator_boundary['refresh_action_command']}` required before right-now use = `{operator_boundary['refresh_required_before_right_now_instruction_use']}`; can update surfaces = `{operator_boundary['refresh_can_update_operator_surfaces']}`; settles rows / creates ROI evidence / clean-empty performance = `{operator_boundary['refresh_can_settle_open_rows_by_itself']}` / `{operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}` / `{operator_boundary['clean_empty_refresh_counts_as_forward_performance']}` | Wrapper refresh is operator routing only; it is not settled ROI, promotion readiness, live profitability, or real-money evidence |",
            f"| Operator read gate | `{compare_json_name}` `current_operator_boundary.operator_read_gate`: {cma.md_cell(operator_boundary['operator_read_gate']['read'])} Gate status = `{operator_boundary['operator_read_gate']['gate_status']}`; recommended command = `{operator_boundary['operator_read_gate']['recommended_command']}` | {operator_gate_boundary_read} |",
            f"| Bridge-published gate progress | `{current_evidence_json_name}` `decision_gate_progress`: {cma.md_cell(current_gate_progress['read'])} Source: `{current_gate_progress['source_path']}` `{current_gate_progress['source_json_path']}`; gate status = `{current_gate_progress['gate_status']}` | Current gates are all uncleared routing context only; they do not change the OP-family ordering or create settled ROI, OP-anchor proof, promotion readiness, live-profitability, bankroll, or real-money evidence |",
            f"| Current bridge rebuild order | `{current_evidence_json_name}` `rebuild_validation_contract`: {' -> '.join(rebuild_validation_contract['upstream_refresh_commands'])} before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes | Rebuild route only; it is not OP-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
            f"| Scorecard audit route | `{current_evidence_json_name}` `scorecard_audit_route`: {cma.md_cell(scorecard_audit_route['route_read'])} Artifacts: `{scorecard_audit_route['markdown_path']}` / `{scorecard_audit_route['json_path']}`; validator = `{scorecard_audit_route['validator_command']}`; gate source = `{scorecard_audit_route['gate_floor_source']}` | Report-synchronization route only; it is not OP-family evidence, forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
            f"| Current settled rule mix | OP_DURABLE_K7={operator_boundary['op_anchor_roi_complete_rows']}; CD_CORE_K8={operator_boundary['cd_companion_roi_complete_rows']}; {cma.md_cell(operator_boundary['primary_rule_mix_read'])} | Rule-specific settled rows stay separate; CD-only paper rows are not OP-anchor forward evidence |",
            f"| Settlement queue state | `{operator_boundary['open_settlement_queue_state']}`; {cma.md_cell(operator_boundary['open_settlement_context'])}; detail: {cma.md_cell(operator_boundary['open_settlement_queue_read'])} | Open rows are settlement workflow only; fill outcomes from actual result/payout evidence before interpreting ROI |",
            f"| Recommendation context | {cma.md_cell(operator_boundary['recommendation_context_read'])} | Latest recommendation-state context is operator routing only, not bet readiness or forward-performance evidence |",
            f"| Operator route | `{operator_boundary['best_action_command']}` | Use the route to settle or refresh; do not infer profit, promotion, or real-money readiness from the route itself |",
            "",
            "The current operator boundary is routing/provenance context only. It does not change the frozen OP-family ordering above, and it is not settled ROI, OP-anchor proof, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            "",
            "## Notes",
            "",
        ]
    )

    for _, row in df.iterrows():
        lines.append(f"- **{row['label']}**: {row['note']}")

    lines.extend(
        [
            "",
            "## Validation",
            "",
            "- Source logic reused from `compare_main_approaches.py`",
            f"- Source files: `{cache_name}`, `{phase7_rules_name}`, `{wf_rules_name}`, `{scorecard_name}`, `{scorecard_json_name}`, `{compare_json_name}`, `{current_evidence_json_name}`",
            f"- Wrote: `{csv_output_name}`, `{md_output_name}`",
            "",
            "## Source Provenance",
            "",
            "Exact input-byte fingerprints for this OP-family card. Use them as reproducibility metadata only; they do not prove settled paper ROI, promotion readiness, live profitability, or real-money performance.",
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
    cache_path = Path(args.cache_pkl)
    phase7_rules_path = Path(args.phase7_rules_json)
    wf_rules_path = Path(args.wf_rules_csv)
    scorecard_path = Path(args.scorecard_csv)
    scorecard_json_path = Path(args.scorecard_json)
    compare_json_path = Path(args.compare_json)
    current_evidence_json_path = Path(args.current_evidence_json)
    csv_output = Path(args.csv_output)
    md_output = Path(args.md_output)
    source_paths = {
        "compare_main_approaches": Path(cma.__file__).resolve(),
        "compare_main_approaches_json": compare_json_path,
        "current_evidence_summary": current_evidence_json_path,
        "phase5_race_cache": cache_path,
        "phase7_rules": phase7_rules_path,
        "walk_forward_rules": wf_rules_path,
        "forward_evidence_scorecard_csv": scorecard_path,
        "forward_evidence_scorecard_json": scorecard_json_path,
    }

    load_scorecard_ranking_contract(scorecard_json_path)
    load_scorecard_decision_gate_minimums(scorecard_json_path)
    load_scorecard_ci_only_diagnostic(scorecard_json_path)
    load_current_operator_boundary(compare_json_path)
    load_current_gate_progress(current_evidence_json_path)
    load_scorecard_audit_route(current_evidence_json_path)
    load_rebuild_validation_contract(current_evidence_json_path)
    source_file_fingerprints(source_paths)

    df = build_dataframe(
        cache_path=cache_path,
        phase7_rules_path=phase7_rules_path,
        wf_rules_path=wf_rules_path,
        scorecard_path=scorecard_path,
    )
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_output, index=False)
    report = build_markdown(
        df,
        cache_name=cache_path.name,
        phase7_rules_name=phase7_rules_path.name,
        wf_rules_name=wf_rules_path.name,
        scorecard_name=scorecard_path.name,
        scorecard_json_name=scorecard_json_path.name,
        compare_json_name=compare_json_path.name,
        current_evidence_json_name=current_evidence_json_path.name,
        csv_output_name=csv_output.name,
        md_output_name=md_output.name,
        scorecard_json_path=scorecard_json_path,
        compare_json_path=compare_json_path,
        current_evidence_json_path=current_evidence_json_path,
        source_paths=source_paths,
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
