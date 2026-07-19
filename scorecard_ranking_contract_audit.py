#!/usr/bin/env python3
"""Audit that report-facing hierarchy surfaces inherit scorecard guardrails.

This is a report/reproducibility guardrail only. It does not add forward evidence,
settled ROI, promotion readiness, or real-money support.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parent
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
MD_OUTPUT = BASE / "SCORECARD_RANKING_CONTRACT_AUDIT.md"
JSON_OUTPUT = BASE / "scorecard_ranking_contract_audit.json"

CONTRACT_KEYS = (
    "rank_is_tier_first_decision_order",
    "forward_trust_is_secondary_within_tier",
    "raw_score_is_not_an_automatic_deployment_instruction",
    "known_rank_override",
)
OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY = "ci_only_promotion_diagnostics.OP_REFINED_K7"
REQUIRED_CI_ONLY_WHY_NOT = (
    "smaller holdout sample than OP_DURABLE_K7",
    "losing 2024 holdout split",
    "lower walk-forward recurrence than OP_DURABLE_K7",
    "uncleared phase8_promotion_review paper-observation gate",
    "uncleared anchor_displacement paper-observation gate",
)

TEXT_SURFACES: tuple[dict[str, Any], ...] = (
    {
        "name": "forward_evidence_scorecard_text",
        "path": BASE / "forward_evidence_scorecard.txt",
        "role": "source scorecard human table",
        "required": [
            "Rules ranked by tier-first conservative decision order",
            "Rank is not raw-score order: PAPER CD_CORE_K8 intentionally ranks ahead of WATCH OP_REFINED_K7",
            "Score         = forward_trust score used inside a tier; rank is tier-first and not raw-score order",
        ],
    },
    {
        "name": "compare_main_approaches_markdown",
        "path": BASE / "COMPARE_MAIN_APPROACHES.md",
        "role": "main cross-method report bundle",
        "required": [
            "Inherited scorecard ranking contract: rank is tier-first",
            "Scorecard rank contract inherited: CD_CORE_K8 ranks ahead of OP_REFINED_K7",
            "The inherited scorecard contract says: CD_CORE_K8 ranks ahead of OP_REFINED_K7",
            "forward_evidence_scorecard.json",
        ],
    },
    {
        "name": "op_anchor_method_comparison_markdown",
        "path": BASE / "OP_ANCHOR_METHOD_COMPARISON.md",
        "role": "OP anchor vs Harville/XGBoost comparison",
        "required": [
            "Scorecard ranking contract inherited:",
            "raw score is not an automatic deployment instruction",
            "Scorecard rank-contract read:",
            "hotter raw OP_REFINED_K7 score still does not automatically displace",
            "forward_evidence_scorecard.json",
        ],
    },
    {
        "name": "op_family_decision_markdown",
        "path": BASE / "OP_FAMILY_DECISION.md",
        "role": "direct OP-family anchor/challenger card",
        "required": [
            "Inherited scorecard ranking contract: rank is tier-first",
            "Scorecard rank-contract override: CD_CORE_K8 ranks ahead of OP_REFINED_K7",
            "Do not read raw Score as a promotion queue",
            "forward_evidence_scorecard.json",
        ],
    },
    {
        "name": "cross_family_decision_markdown",
        "path": BASE / "CROSS_FAMILY_DECISION.md",
        "role": "direct OP/CD/Phase-8 cross-family card",
        "required": [
            "Inherited scorecard ranking contract: rank is tier-first",
            "Scorecard rank-contract override: CD_CORE_K8 ranks ahead of OP_REFINED_K7",
            "forward_evidence_scorecard.json",
        ],
    },
    {
        "name": "portfolio_decision_markdown",
        "path": BASE / "PORTFOLIO_DECISION_CARD.md",
        "role": "direct Phase 7 / Phase 8 / selector portfolio card",
        "required": [
            "Inherited scorecard ranking contract:",
            "Scorecard rank-contract override: CD_CORE_K8 ranks ahead of OP_REFINED_K7",
            "raw Score cannot turn a shadow Phase 8 / OP_REFINED line into an automatic promotion cue",
            "forward_evidence_scorecard.json",
        ],
    },
    {
        "name": "method_family_decision_markdown",
        "path": BASE / "METHOD_FAMILY_DECISION.md",
        "role": "direct selective/Harville/XGBoost method-family card",
        "required": [
            "Inherited scorecard ranking contract:",
            "Scorecard rank-contract override: CD_CORE_K8 ranks ahead of OP_REFINED_K7",
            "raw Score cannot turn the selective-family OP_REFINED shadow context into an automatic promotion cue",
            "forward_evidence_scorecard.json",
        ],
    },
)

CI_ONLY_TEXT_SURFACES: tuple[dict[str, Any], ...] = (
    {
        "name": "forward_evidence_scorecard_text_ci_only",
        "path": BASE / "forward_evidence_scorecard.txt",
        "role": "source scorecard human CI-only diagnostic",
        "required": [
            "CI-ONLY PROMOTION CHECK",
            "OP_REFINED_K7: positive CI lower bound (+11.2%) is support context only; ci_only_promotion_allowed=false.",
            "20-row promotion-review / 30-row anchor-displacement paper-observation gates are uncleared",
        ],
    },
    {
        "name": "compare_main_approaches_markdown_ci_only",
        "path": BASE / "COMPARE_MAIN_APPROACHES.md",
        "role": "main comparison CI-only diagnostic",
        "required": [
            "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7",
            "ci_only_promotion_allowed=false",
            "positive bootstrap CI lower bound is useful support context",
            "not enough by itself to promote OP_REFINED_K7 or displace OP_DURABLE_K7",
        ],
    },
    {
        "name": "op_anchor_method_comparison_markdown_ci_only",
        "path": BASE / "OP_ANCHOR_METHOD_COMPARISON.md",
        "role": "OP anchor comparison CI-only diagnostic",
        "required": [
            "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7",
            "ci_only_promotion_allowed=false",
            "positive bootstrap CI lower bound is useful support context",
            "separate 20-row promotion-review and 30-row anchor-displacement paper-observation gates",
        ],
    },
    {
        "name": "op_family_decision_markdown_ci_only",
        "path": BASE / "OP_FAMILY_DECISION.md",
        "role": "direct OP-family card CI-only diagnostic",
        "required": [
            "Scorecard CI-only promotion check",
            "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7",
            "CI-only promotion allowed: `false`",
            "not an anchor-replacement trigger",
        ],
    },
    {
        "name": "cross_family_decision_markdown_ci_only",
        "path": BASE / "CROSS_FAMILY_DECISION.md",
        "role": "direct cross-family card CI-only diagnostic",
        "required": [
            "Scorecard CI-only promotion check",
            "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7",
            "CI-only promotion allowed: `false`",
            "not a promotion trigger",
        ],
    },
    {
        "name": "portfolio_decision_markdown_ci_only",
        "path": BASE / "PORTFOLIO_DECISION_CARD.md",
        "role": "direct portfolio card CI-only diagnostic",
        "required": [
            "Scorecard CI-only promotion check",
            "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7",
            "CI-only promotion allowed: `false`",
            "not a portfolio-level Phase 8 default trigger",
        ],
    },
    {
        "name": "method_family_decision_markdown_ci_only",
        "path": BASE / "METHOD_FAMILY_DECISION.md",
        "role": "direct method-family card CI-only diagnostic",
        "required": [
            "Scorecard CI-only promotion check",
            "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7",
            "CI-only promotion allowed: `false`",
            "not a method-family promotion trigger",
        ],
    },
    {
        "name": "current_evidence_summary_markdown_ci_only",
        "path": BASE / "CURRENT_EVIDENCE_SUMMARY.md",
        "role": "current-evidence bridge CI-only diagnostic",
        "required": [
            "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7",
            "ci_only_promotion_allowed=false",
            "positive CI lower bound is support context only",
            "not a current paper promotion trigger",
        ],
    },
    {
        "name": "paper_trade_usage_markdown_ci_only",
        "path": BASE / "PAPER_TRADE_USAGE.md",
        "role": "operator runbook CI-only route",
        "required": [
            "ci_only_promotion_diagnostics.OP_REFINED_K7",
            "ci_only_promotion_allowed=false",
            "OP_REFINED's positive CI lower bound stays support context",
            "rather than a current-paper promotion trigger",
        ],
    },
    {
        "name": "validation_quickstart_markdown_ci_only",
        "path": BASE / "VALIDATION_QUICKSTART.md",
        "role": "validation quickstart CI-only route",
        "required": [
            "scorecard CI-only diagnostic routing",
            "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7",
            "ci_only_promotion_allowed=false",
            "scorecard CI-only diagnostic / scorecard_audit_route / fingerprints as reproducibility and operator-readiness metadata only",
        ],
    },
    {
        "name": "daily_artifact_guide_markdown_ci_only",
        "path": BASE / "DAILY_ARTIFACT_GUIDE.md",
        "role": "daily artifact guide CI-only route",
        "required": [
            "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7",
            "scorecard-sourced OP_REFINED CI-only routing",
            "ci_only_promotion_allowed=false",
            "current-paper promotion trigger",
        ],
    },
    {
        "name": "cole_full_report_markdown_ci_only",
        "path": BASE / "COLE_FULL_REPORT_2026-04-15.md",
        "role": "long-form narrative report CI-only boundary",
        "required": [
            "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7",
            "ci_only_promotion_allowed=false",
            "positive CI lower bound is support context only",
            "not OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
        ],
    },
    {
        "name": "cole_presentation_outline_markdown_ci_only",
        "path": BASE / "COLE_PRESENTATION_OUTLINE.md",
        "role": "presentation outline CI-only boundary",
        "required": [
            "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7",
            "ci_only_promotion_allowed=false",
            "positive CI lower bound is support context only",
            "not OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
        ],
    },
    {
        "name": "superfecta_html_report_ci_only",
        "path": BASE / "Superfecta_Project_Report_2026-04-15.html",
        "role": "shareable HTML report CI-only boundary",
        "required": [
            "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7",
            "ci_only_promotion_allowed=false",
            "positive CI lower bound is support context only",
            "not a current-paper promotion trigger, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
        ],
    },
)

JSON_CONTRACT_SURFACES: tuple[dict[str, Any], ...] = (
    {
        "name": "forward_evidence_scorecard_json",
        "path": SCORECARD_JSON,
        "role": "source machine-readable ranking contract",
        "contract_path": "ranking_contract",
    },
    {
        "name": "compare_main_approaches_json",
        "path": BASE / "compare_main_approaches.json",
        "role": "main comparison JSON sidecar",
        "contract_path": "scorecard_ranking_contract",
    },
    {
        "name": "op_anchor_method_comparison_json",
        "path": BASE / "op_anchor_method_comparison.json",
        "role": "OP-anchor comparison JSON sidecar",
        "contract_path": "scorecard_ranking_contract",
    },
    {
        "name": "op_family_decision_validation_json",
        "path": BASE / "out" / "status_validation" / "op_family_decision" / "op_family_decision_validation.json",
        "role": "direct OP-family validator JSON",
        "contract_path": "scorecard_ranking_contract",
    },
    {
        "name": "cross_family_decision_validation_json",
        "path": BASE / "out" / "status_validation" / "cross_family_decision" / "cross_family_decision_validation.json",
        "role": "direct cross-family validator JSON",
        "contract_path": "scorecard_ranking_contract",
    },
    {
        "name": "portfolio_decision_card_validation_json",
        "path": BASE / "out" / "status_validation" / "portfolio_decision_card" / "portfolio_decision_card_validation.json",
        "role": "direct portfolio-card validator JSON",
        "contract_path": "scorecard_ranking_contract",
    },
    {
        "name": "method_family_decision_card_validation_json",
        "path": BASE / "out" / "status_validation" / "method_family_decision_card" / "method_family_decision_card_validation.json",
        "role": "direct method-family-card validator JSON",
        "contract_path": "scorecard_ranking_contract",
    },
    {
        "name": "decision_cards_suite_validation_json",
        "path": BASE / "out" / "status_validation" / "decision_cards_suite" / "decision_cards_suite_validation.json",
        "role": "decision-card suite rollup validation",
        "contract_path": "scorecard_ranking_contract",
    },
    {
        "name": "frozen_decision_stack_validation_json",
        "path": BASE / "out" / "status_validation" / "frozen_decision_stack" / "frozen_decision_stack_validation.json",
        "role": "frozen decision-stack validation",
        "contract_path": "scorecard_ranking_contract",
    },
)

JSON_CI_ONLY_SURFACES: tuple[dict[str, Any], ...] = (
    {
        "name": "forward_evidence_scorecard_json_ci_only",
        "path": SCORECARD_JSON,
        "role": "source machine-readable CI-only diagnostic",
        "diagnostic_path": OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY,
    },
    {
        "name": "compare_main_approaches_json_ci_only",
        "path": BASE / "compare_main_approaches.json",
        "role": "main comparison JSON CI-only diagnostic",
        "diagnostic_path": "op_challenger_diagnostic.scorecard_ci_only_promotion_diagnostic",
    },
    {
        "name": "op_anchor_method_comparison_json_ci_only",
        "path": BASE / "op_anchor_method_comparison.json",
        "role": "OP-anchor comparison JSON CI-only diagnostic",
        "diagnostic_path": "op_challenger_diagnostic.scorecard_ci_only_promotion_diagnostic",
    },
    {
        "name": "current_evidence_summary_json_ci_only",
        "path": CURRENT_EVIDENCE_JSON,
        "role": "current-evidence bridge JSON CI-only diagnostic",
        "diagnostic_path": "scorecard_ci_only_promotion_check.scorecard_ci_only_promotion_diagnostic",
    },
    {
        "name": "op_family_decision_validation_json_ci_only",
        "path": BASE / "out" / "status_validation" / "op_family_decision" / "op_family_decision_validation.json",
        "role": "direct OP-family validator JSON CI-only diagnostic",
        "diagnostic_path": "scorecard_ci_only_diagnostic",
    },
    {
        "name": "cross_family_decision_validation_json_ci_only",
        "path": BASE / "out" / "status_validation" / "cross_family_decision" / "cross_family_decision_validation.json",
        "role": "direct cross-family validator JSON CI-only diagnostic",
        "diagnostic_path": "scorecard_ci_only_diagnostic",
    },
    {
        "name": "portfolio_decision_card_validation_json_ci_only",
        "path": BASE / "out" / "status_validation" / "portfolio_decision_card" / "portfolio_decision_card_validation.json",
        "role": "direct portfolio-card validator JSON CI-only diagnostic",
        "diagnostic_path": "scorecard_ci_only_diagnostic",
    },
    {
        "name": "method_family_decision_card_validation_json_ci_only",
        "path": BASE / "out" / "status_validation" / "method_family_decision_card" / "method_family_decision_card_validation.json",
        "role": "direct method-family-card validator JSON CI-only diagnostic",
        "diagnostic_path": "scorecard_ci_only_diagnostic",
    },
    {
        "name": "superfecta_html_report_validation_json_ci_only",
        "path": BASE / "out" / "status_validation" / "superfecta_html_report" / "superfecta_html_report_validation.json",
        "role": "shareable HTML report validator JSON CI-only diagnostic",
        "diagnostic_path": "scorecard_ci_only_diagnostic",
    },
)

JSON_SCORECARD_AUDIT_ROUTE_SURFACES: tuple[dict[str, Any], ...] = (
    {
        "name": "current_evidence_summary_json_scorecard_audit_route",
        "path": CURRENT_EVIDENCE_JSON,
        "role": "current-evidence bridge JSON route to this scorecard audit",
        "route_path": "scorecard_audit_route",
    },
)

JSON_REBUILD_VALIDATION_CONTRACT_SURFACES: tuple[dict[str, Any], ...] = (
    {
        "name": "current_evidence_summary_json_rebuild_validation_contract",
        "path": CURRENT_EVIDENCE_JSON,
        "role": "current-evidence bridge JSON rebuild order before quoting current totals",
        "contract_path": "rebuild_validation_contract",
    },
)

CRITICAL_CURRENT_EVIDENCE_ROW_NAMES = {
    "current_evidence_summary_json_ci_only",
    "current_evidence_summary_json_scorecard_audit_route",
    "current_evidence_summary_json_rebuild_validation_contract",
}

SCORECARD_AUDIT_VALID_EVIDENCE_SCOPE = "scorecard_gate_ranking_ci_only_sync_metadata_only"

EVIDENCE_BOUNDARY = {
    "artifact_role": "scorecard ranking-contract and CI-only diagnostic usage audit",
    "valid_evidence_scope": SCORECARD_AUDIT_VALID_EVIDENCE_SCOPE,
    "valid_use": "report-surface synchronization and reproducibility guardrail only",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_real_money_evidence": True,
    "non_goals": [
        "do not use this audit as settled ROI",
        "do not promote OP_REFINED_K7 or Phase 8 from this audit",
        "do not treat CI-only diagnostic coverage as a cleared paper-observation gate",
        "do not reopen current odds-only XGBoost from this audit",
        "do not substitute BAQ for BEL",
        "do not discuss real-money sizing from this audit",
    ],
}


def expected_scorecard_audit_route(decision_gate_minimums: dict[str, Any]) -> dict[str, Any]:
    also_requires = decision_gate_minimums.get("real_money_discussion", {}).get("also_requires", [])
    return {
        "markdown_path": "SCORECARD_RANKING_CONTRACT_AUDIT.md",
        "json_path": "scorecard_ranking_contract_audit.json",
        "validator_command": "python3 validate_scorecard_ranking_contract_audit.py",
        "gate_floor_source": "forward_evidence_scorecard.json:decision_gate_minimums",
        "valid_use": "navigation route for scorecard gate/ranking/CI-only/timezone/no-BAQ synchronization checks",
        "artifacts_present": True,
        "gate_floor_snapshot": {
            "anchor_displacement_min_roi_complete_settled_observations": decision_gate_minimums["anchor_displacement"][
                "min_roi_complete_settled_observations"
            ],
            "phase8_promotion_review_min_roi_complete_settled_observations": decision_gate_minimums[
                "phase8_promotion_review"
            ]["min_roi_complete_settled_observations"],
            "real_money_discussion_min_total_settled_observations_with_usable_roi": decision_gate_minimums[
                "real_money_discussion"
            ]["min_total_settled_observations_with_usable_roi"],
            "real_money_no_baq_as_bel_required": "no BAQ-as-BEL substitution" in also_requires,
        },
        "not_forward_performance_evidence": True,
        "not_settled_roi_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_live_profitability_evidence": True,
        "not_bankroll_guidance": True,
        "not_real_money_evidence": True,
    }


def expected_rebuild_validation_contract() -> dict[str, Any]:
    return {
        "rebuild_command": "python3 current_evidence_summary.py",
        "prerequisite_rebuild_command": "python3 paper_trade_settlement_audit.py",
        "upstream_refresh_order": [
            {
                "order": 1,
                "command": "python3 paper_trade_settlement_audit.py",
                "reason": (
                    "refresh settlement-audit source fingerprints after scorecard, rules, signals, or "
                    "settlement-ledger byte changes"
                ),
            },
            {
                "order": 2,
                "command": "python3 current_evidence_summary.py",
                "reason": "rebuild the bridge from the refreshed scorecard, right-now card, settlement audit, and CSV recompute",
            },
            {
                "order": 3,
                "command": "python3 validate_current_evidence_summary.py",
                "reason": "confirm source fingerprint parity, gate-source alignment, and non-evidence boundaries before quoting the bridge",
            },
        ],
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": True,
        "upstream_refresh_order_valid_use": (
            "reproducible rebuild order for current bridge provenance after scorecard/rules/ledger byte changes"
        ),
        "direct_validation_command": "python3 validate_current_evidence_summary.py",
        "green_checks_are_reproducibility_metadata_only": True,
        "requires_source_consistency_before_quoting_current_totals": True,
        "requires_source_freshness_before_right_now_instruction_use": True,
        "upstream_refresh_order_is_provenance_metadata_only": True,
        "not_settled_roi_or_real_money_evidence": True,
    }


def build_evidence_boundary_metadata(decision_gate_minimums: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_role": "scorecard ranking-contract and CI-only diagnostic usage audit",
        "valid_evidence_scope": SCORECARD_AUDIT_VALID_EVIDENCE_SCOPE,
        "valid_use": "report-surface synchronization and reproducibility guardrail only",
        "decision_gate_minimums_source": "forward_evidence_scorecard.json:decision_gate_minimums",
        "decision_gate_minimums": decision_gate_minimums,
        "decision_gate_minimums_are_future_paper_observation_floors": True,
        "ci_only_coverage_does_not_clear_promotion_or_anchor_gates": True,
        "validator_cleanliness_does_not_clear_gates": True,
        "no_baq_as_bel_prerequisite_preserved": (
            "no BAQ-as-BEL substitution"
            in decision_gate_minimums.get("real_money_discussion", {}).get("also_requires", [])
        ),
        "not_new_forward_evidence": True,
        "not_live_paper_trade_ledger": True,
        "not_settled_roi_evidence": True,
        "not_live_profitability_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_real_money_evidence": True,
    }


def get_nested(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted_path)
        current = current[part]
    return current


def with_current_evidence_json(
    surfaces: tuple[dict[str, Any], ...],
    current_evidence_json: Path,
) -> tuple[dict[str, Any], ...]:
    rewritten: list[dict[str, Any]] = []
    for surface in surfaces:
        copy = dict(surface)
        if Path(copy["path"]) == CURRENT_EVIDENCE_JSON:
            copy["path"] = current_evidence_json
        rewritten.append(copy)
    return tuple(rewritten)


def fingerprint_existing_path(path: Path, exists: bool | None = None) -> dict[str, Any]:
    exists = path.exists() if exists is None else exists
    rel_path = str(path.relative_to(BASE)) if path.is_relative_to(BASE) else str(path)
    if not exists:
        return {"path": rel_path, "bytes": 0, "sha256": None}
    data = path.read_bytes()
    return {
        "path": rel_path,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def load_scorecard_contract(scorecard_json: Path = SCORECARD_JSON) -> dict[str, Any]:
    payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
    contract = payload.get("ranking_contract")
    if not isinstance(contract, dict):
        raise ValueError(f"{scorecard_json.name} is missing ranking_contract")
    missing = [key for key in CONTRACT_KEYS if key not in contract]
    if missing:
        raise ValueError(f"{scorecard_json.name} ranking_contract missing keys: {missing}")
    if contract.get("rank_is_tier_first_decision_order") is not True:
        raise ValueError(f"{scorecard_json.name} ranking_contract no longer marks rank_is_tier_first_decision_order=true")
    if contract.get("forward_trust_is_secondary_within_tier") is not True:
        raise ValueError(f"{scorecard_json.name} ranking_contract no longer marks forward_trust_is_secondary_within_tier=true")
    if contract.get("raw_score_is_not_an_automatic_deployment_instruction") is not True:
        raise ValueError(f"{scorecard_json.name} ranking_contract no longer says raw score is not an automatic deployment instruction")
    if "CD_CORE_K8 ranks ahead of OP_REFINED_K7" not in str(contract.get("known_rank_override") or ""):
        raise ValueError(f"{scorecard_json.name} ranking_contract no longer preserves the CD_CORE_K8 over OP_REFINED_K7 tier-first override")
    return dict(contract)


def load_scorecard_ci_only_diagnostic(scorecard_json: Path = SCORECARD_JSON) -> dict[str, Any]:
    payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
    diagnostics = payload.get("ci_only_promotion_diagnostics")
    if not isinstance(diagnostics, dict):
        raise ValueError(f"{scorecard_json.name} is missing ci_only_promotion_diagnostics")
    diagnostic = diagnostics.get("OP_REFINED_K7")
    if not isinstance(diagnostic, dict):
        raise ValueError(f"{scorecard_json.name} is missing ci_only_promotion_diagnostics.OP_REFINED_K7")
    if diagnostic.get("candidate_rule_id") != "OP_REFINED_K7":
        raise ValueError(f"{scorecard_json.name} OP_REFINED CI-only diagnostic has the wrong candidate_rule_id")
    if diagnostic.get("current_anchor_rule_id") != "OP_DURABLE_K7":
        raise ValueError(f"{scorecard_json.name} OP_REFINED CI-only diagnostic has the wrong current_anchor_rule_id")
    if diagnostic.get("ci_only_promotion_allowed") is not False:
        raise ValueError(f"{scorecard_json.name} OP_REFINED CI-only diagnostic must keep ci_only_promotion_allowed=false")
    if diagnostic.get("positive_ci_lower_bound_is_support_context") is not True:
        raise ValueError(
            f"{scorecard_json.name} OP_REFINED CI-only diagnostic must mark positive_ci_lower_bound_is_support_context=true"
        )
    why_not = diagnostic.get("why_not")
    if not isinstance(why_not, list) or any(item not in why_not for item in REQUIRED_CI_ONLY_WHY_NOT):
        raise ValueError(f"{scorecard_json.name} OP_REFINED CI-only diagnostic is missing required why_not reasons")
    required_before_review = diagnostic.get("required_before_review")
    if not isinstance(required_before_review, dict):
        raise ValueError(f"{scorecard_json.name} OP_REFINED CI-only diagnostic is missing required_before_review")
    for key in ("phase8_promotion_review", "anchor_displacement"):
        if not isinstance(required_before_review.get(key), str) or not required_before_review[key].strip():
            raise ValueError(f"{scorecard_json.name} OP_REFINED CI-only diagnostic is missing required_before_review.{key}")
    does_not_count = diagnostic.get("does_not_count")
    if not isinstance(does_not_count, list) or "green validators" not in does_not_count:
        raise ValueError(f"{scorecard_json.name} OP_REFINED CI-only diagnostic must list green validators as non-counting")
    return dict(diagnostic)


def load_scorecard_decision_gate_minimums(scorecard_json: Path = SCORECARD_JSON) -> dict[str, Any]:
    payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
    gate_minimums = payload.get("decision_gate_minimums")
    if not isinstance(gate_minimums, dict):
        raise ValueError(f"{scorecard_json.name} is missing decision_gate_minimums")
    anchor = gate_minimums.get("anchor_displacement")
    phase8 = gate_minimums.get("phase8_promotion_review")
    real_money = gate_minimums.get("real_money_discussion")
    if not isinstance(anchor, dict) or anchor.get("min_roi_complete_settled_observations") != 30:
        raise ValueError(f"{scorecard_json.name} decision_gate_minimums.anchor_displacement must preserve the 30-row floor")
    if anchor.get("observation_scope") != "same candidate paper observations":
        raise ValueError(f"{scorecard_json.name} decision_gate_minimums.anchor_displacement lost same-candidate scope")
    if not isinstance(phase8, dict) or phase8.get("min_roi_complete_settled_observations") != 20:
        raise ValueError(f"{scorecard_json.name} decision_gate_minimums.phase8_promotion_review must preserve the 20-row floor")
    if phase8.get("observation_scope") != "candidate shadow observations":
        raise ValueError(f"{scorecard_json.name} decision_gate_minimums.phase8_promotion_review lost shadow-observation scope")
    if not isinstance(real_money, dict) or real_money.get("min_total_settled_observations_with_usable_roi") != 100:
        raise ValueError(f"{scorecard_json.name} decision_gate_minimums.real_money_discussion must preserve the 100-row floor")
    if "no BAQ-as-BEL substitution" not in real_money.get("also_requires", []):
        raise ValueError(f"{scorecard_json.name} decision_gate_minimums.real_money_discussion lost no BAQ-as-BEL prerequisite")
    return dict(gate_minimums)


def check_text_surface(surface: dict[str, Any]) -> dict[str, Any]:
    path = Path(surface["path"])
    missing: list[str] = []
    exists = path.exists()
    fingerprint = fingerprint_existing_path(path, exists)
    if exists:
        text = path.read_text(encoding="utf-8")
        missing = [phrase for phrase in surface["required"] if phrase not in text]
    else:
        text = ""
        missing = list(surface["required"])
    return {
        "name": surface["name"],
        "kind": "text",
        "role": surface["role"],
        "path": str(path.relative_to(BASE)) if path.is_relative_to(BASE) else str(path),
        "status": "pass" if exists and not missing else "fail",
        "required_phrase_count": len(surface["required"]),
        "missing_phrases": missing,
        "bytes": fingerprint["bytes"],
        "sha256": fingerprint["sha256"],
        "source_fingerprint": fingerprint,
    }


def check_json_ci_only_surface(surface: dict[str, Any], source_diagnostic: dict[str, Any]) -> dict[str, Any]:
    path = Path(surface["path"])
    exists = path.exists()
    fingerprint = fingerprint_existing_path(path, exists)
    missing_or_mismatch: list[str] = []
    observed_diagnostic: Any = None
    if exists:
        payload = json.loads(path.read_text(encoding="utf-8"))
        try:
            observed_diagnostic = get_nested(payload, surface["diagnostic_path"])
        except KeyError:
            missing_or_mismatch.append(f"missing {surface['diagnostic_path']}")
        else:
            if observed_diagnostic != source_diagnostic:
                missing_or_mismatch.append(
                    f"{surface['diagnostic_path']} does not equal forward_evidence_scorecard.json {OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}"
                )
    else:
        missing_or_mismatch.append("missing file")
    return {
        "name": surface["name"],
        "kind": "json_ci_only_diagnostic",
        "role": surface["role"],
        "path": str(path.relative_to(BASE)) if path.is_relative_to(BASE) else str(path),
        "diagnostic_path": surface["diagnostic_path"],
        "status": "pass" if exists and not missing_or_mismatch else "fail",
        "issues": missing_or_mismatch,
        "diagnostic_matches_source": observed_diagnostic == source_diagnostic,
        "bytes": fingerprint["bytes"],
        "sha256": fingerprint["sha256"],
        "source_fingerprint": fingerprint,
    }


def check_json_contract_surface(surface: dict[str, Any], source_contract: dict[str, Any]) -> dict[str, Any]:
    path = Path(surface["path"])
    exists = path.exists()
    fingerprint = fingerprint_existing_path(path, exists)
    missing_or_mismatch: list[str] = []
    observed_contract: Any = None
    if exists:
        payload = json.loads(path.read_text(encoding="utf-8"))
        try:
            observed_contract = get_nested(payload, surface["contract_path"])
        except KeyError:
            missing_or_mismatch.append(f"missing {surface['contract_path']}")
        else:
            if observed_contract != source_contract:
                missing_or_mismatch.append(f"{surface['contract_path']} does not equal forward_evidence_scorecard.json ranking_contract")
    else:
        missing_or_mismatch.append("missing file")
    return {
        "name": surface["name"],
        "kind": "json_contract",
        "role": surface["role"],
        "path": str(path.relative_to(BASE)) if path.is_relative_to(BASE) else str(path),
        "contract_path": surface["contract_path"],
        "status": "pass" if exists and not missing_or_mismatch else "fail",
        "issues": missing_or_mismatch,
        "contract_matches_source": observed_contract == source_contract,
        "bytes": fingerprint["bytes"],
        "sha256": fingerprint["sha256"],
        "source_fingerprint": fingerprint,
    }


def check_json_scorecard_audit_route_surface(
    surface: dict[str, Any],
    decision_gate_minimums: dict[str, Any],
) -> dict[str, Any]:
    path = Path(surface["path"])
    exists = path.exists()
    fingerprint = fingerprint_existing_path(path, exists)
    missing_or_mismatch: list[str] = []
    observed_route: Any = None
    expected_route = expected_scorecard_audit_route(decision_gate_minimums)
    referenced_markdown_path = ""
    referenced_json_path = ""
    referenced_markdown_path_is_audit_output = False
    referenced_json_path_is_audit_output = False
    referenced_markdown_exists = False
    referenced_json_exists_or_is_current_output = False
    expected_route_mismatches: list[str] = []
    route_read_missing_phrases: list[str] = []
    required_route_read_phrases = (
        "copied 30/20/100 gate floors",
        "tier-first ranking",
        "OP_REFINED CI-only support context",
        "generated-at timezone provenance",
        "no-BAQ-as-BEL prerequisite drift",
    )
    if exists:
        payload = json.loads(path.read_text(encoding="utf-8"))
        try:
            observed_route = get_nested(payload, surface["route_path"])
        except KeyError:
            missing_or_mismatch.append(f"missing {surface['route_path']}")
        else:
            if not isinstance(observed_route, dict):
                missing_or_mismatch.append(f"{surface['route_path']} is not an object")
            else:
                for key, expected_value in expected_route.items():
                    if observed_route.get(key) != expected_value:
                        expected_route_mismatches.append(key)
                        missing_or_mismatch.append(f"{surface['route_path']}.{key} does not match scorecard-audit route contract")
                referenced_markdown_path = str(observed_route.get("markdown_path") or "")
                referenced_json_path = str(observed_route.get("json_path") or "")
                markdown_candidate = BASE / referenced_markdown_path
                json_candidate = BASE / referenced_json_path
                referenced_markdown_path_is_audit_output = markdown_candidate == MD_OUTPUT
                referenced_json_path_is_audit_output = json_candidate == JSON_OUTPUT
                referenced_markdown_exists = markdown_candidate.exists()
                referenced_json_exists_or_is_current_output = json_candidate.exists() or referenced_json_path_is_audit_output
                if not referenced_markdown_path_is_audit_output:
                    missing_or_mismatch.append(f"{surface['route_path']}.markdown_path does not point to the scorecard audit markdown output")
                if not referenced_json_path_is_audit_output:
                    missing_or_mismatch.append(f"{surface['route_path']}.json_path does not point to the scorecard audit JSON output")
                if not referenced_markdown_exists:
                    missing_or_mismatch.append(f"{surface['route_path']}.markdown_path referenced artifact is missing on disk")
                if not referenced_json_exists_or_is_current_output:
                    missing_or_mismatch.append(f"{surface['route_path']}.json_path referenced artifact is missing on disk")
                route_read = str(observed_route.get("route_read") or "")
                for phrase in required_route_read_phrases:
                    if phrase not in route_read:
                        route_read_missing_phrases.append(phrase)
                        missing_or_mismatch.append(f"{surface['route_path']}.route_read missing {phrase!r}")
    else:
        missing_or_mismatch.append("missing file")
    observed_route_is_dict = isinstance(observed_route, dict)
    non_evidence_flag_keys = (
        "not_forward_performance_evidence",
        "not_settled_roi_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_bankroll_guidance",
        "not_real_money_evidence",
    )
    return {
        "name": surface["name"],
        "kind": "json_scorecard_audit_route",
        "role": surface["role"],
        "path": str(path.relative_to(BASE)) if path.is_relative_to(BASE) else str(path),
        "route_path": surface["route_path"],
        "status": "pass" if exists and not missing_or_mismatch else "fail",
        "issues": missing_or_mismatch,
        "route_matches_scorecard_gate_minimums": observed_route_is_dict and not missing_or_mismatch,
        "route_matches_expected_contract": observed_route_is_dict and not missing_or_mismatch,
        "route_field_contract_matches_expected": observed_route_is_dict and not expected_route_mismatches,
        "route_field_contract_mismatches": expected_route_mismatches,
        "route_gate_floor_snapshot_matches_source": (
            observed_route_is_dict
            and observed_route.get("gate_floor_snapshot") == expected_route["gate_floor_snapshot"]
        ),
        "route_validator_command_matches_contract": (
            observed_route_is_dict
            and observed_route.get("validator_command") == expected_route["validator_command"]
        ),
        "route_valid_use_matches_contract": (
            observed_route_is_dict
            and observed_route.get("valid_use") == expected_route["valid_use"]
        ),
        "route_non_evidence_flags_match_contract": (
            observed_route_is_dict
            and all(observed_route.get(key) == expected_route[key] for key in non_evidence_flag_keys)
        ),
        "route_read_required_phrases_present": observed_route_is_dict and not route_read_missing_phrases,
        "route_read_missing_phrases": route_read_missing_phrases,
        "referenced_markdown_path": referenced_markdown_path,
        "referenced_json_path": referenced_json_path,
        "referenced_markdown_path_is_audit_output": referenced_markdown_path_is_audit_output,
        "referenced_json_path_is_audit_output": referenced_json_path_is_audit_output,
        "referenced_markdown_exists": referenced_markdown_exists,
        "referenced_json_exists_or_is_current_output": referenced_json_exists_or_is_current_output,
        "referenced_route_artifacts_verified_on_disk": (
            referenced_markdown_path_is_audit_output
            and referenced_json_path_is_audit_output
            and referenced_markdown_exists
            and referenced_json_exists_or_is_current_output
        ),
        "bytes": fingerprint["bytes"],
        "sha256": fingerprint["sha256"],
        "source_fingerprint": fingerprint,
    }


def check_json_rebuild_validation_contract_surface(surface: dict[str, Any]) -> dict[str, Any]:
    path = Path(surface["path"])
    exists = path.exists()
    fingerprint = fingerprint_existing_path(path, exists)
    missing_or_mismatch: list[str] = []
    observed_contract: Any = None
    expected_contract = expected_rebuild_validation_contract()
    expected_commands = [
        row["command"]
        for row in expected_contract["upstream_refresh_order"]
    ]
    observed_commands: list[str] = []
    expected_contract_mismatches: list[str] = []
    if exists:
        payload = json.loads(path.read_text(encoding="utf-8"))
        try:
            observed_contract = get_nested(payload, surface["contract_path"])
        except KeyError:
            missing_or_mismatch.append(f"missing {surface['contract_path']}")
        else:
            if not isinstance(observed_contract, dict):
                missing_or_mismatch.append(f"{surface['contract_path']} is not an object")
            else:
                for key, expected_value in expected_contract.items():
                    if observed_contract.get(key) != expected_value:
                        expected_contract_mismatches.append(key)
                        missing_or_mismatch.append(
                            f"{surface['contract_path']}.{key} does not match current-evidence rebuild contract"
                        )
                observed_order = observed_contract.get("upstream_refresh_order")
                if isinstance(observed_order, list):
                    observed_commands = [
                        str(row.get("command") or "")
                        for row in observed_order
                        if isinstance(row, dict)
                    ]
                else:
                    missing_or_mismatch.append(f"{surface['contract_path']}.upstream_refresh_order is not a list")
                valid_use = str(observed_contract.get("upstream_refresh_order_valid_use") or "")
                for phrase in ("current bridge provenance", "scorecard/rules/ledger byte changes"):
                    if phrase not in valid_use:
                        missing_or_mismatch.append(
                            f"{surface['contract_path']}.upstream_refresh_order_valid_use missing {phrase!r}"
                        )
    else:
        missing_or_mismatch.append("missing file")
    observed_contract_is_dict = isinstance(observed_contract, dict)
    required_flag_keys = (
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
        "green_checks_are_reproducibility_metadata_only",
        "requires_source_consistency_before_quoting_current_totals",
        "requires_source_freshness_before_right_now_instruction_use",
        "upstream_refresh_order_is_provenance_metadata_only",
        "not_settled_roi_or_real_money_evidence",
    )
    return {
        "name": surface["name"],
        "kind": "json_rebuild_validation_contract",
        "role": surface["role"],
        "path": str(path.relative_to(BASE)) if path.is_relative_to(BASE) else str(path),
        "contract_path": surface["contract_path"],
        "status": "pass" if exists and not missing_or_mismatch else "fail",
        "issues": missing_or_mismatch,
        "expected_upstream_refresh_order_commands": expected_commands,
        "observed_upstream_refresh_order_commands": observed_commands,
        "upstream_refresh_order_commands_match_expected": observed_commands == expected_commands,
        "contract_matches_expected": observed_contract_is_dict and not missing_or_mismatch,
        "contract_field_mismatches": expected_contract_mismatches,
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": (
            observed_contract_is_dict
            and observed_contract.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
        ),
        "required_non_evidence_flags_match_contract": (
            observed_contract_is_dict
            and all(observed_contract.get(key) is True for key in required_flag_keys)
        ),
        "upstream_refresh_order_valid_use_matches_contract": (
            observed_contract_is_dict
            and observed_contract.get("upstream_refresh_order_valid_use")
            == expected_contract["upstream_refresh_order_valid_use"]
        ),
        "direct_validation_command_matches_contract": (
            observed_contract_is_dict
            and observed_contract.get("direct_validation_command") == expected_contract["direct_validation_command"]
        ),
        "bytes": fingerprint["bytes"],
        "sha256": fingerprint["sha256"],
        "source_fingerprint": fingerprint,
    }


def build_payload(
    generated_at: str,
    scorecard_json: Path = SCORECARD_JSON,
    current_evidence_json: Path = CURRENT_EVIDENCE_JSON,
) -> dict[str, Any]:
    current_evidence_json = Path(current_evidence_json)
    contract = load_scorecard_contract(scorecard_json)
    ci_only_diagnostic = load_scorecard_ci_only_diagnostic(scorecard_json)
    decision_gate_minimums = load_scorecard_decision_gate_minimums(scorecard_json)
    text_rows = [check_text_surface(surface) for surface in TEXT_SURFACES]
    ci_text_rows = [check_text_surface(surface) for surface in CI_ONLY_TEXT_SURFACES]
    json_rows = [check_json_contract_surface(surface, contract) for surface in JSON_CONTRACT_SURFACES]
    ci_json_rows = [
        check_json_ci_only_surface(surface, ci_only_diagnostic)
        for surface in with_current_evidence_json(JSON_CI_ONLY_SURFACES, current_evidence_json)
    ]
    route_json_rows = [
        check_json_scorecard_audit_route_surface(surface, decision_gate_minimums)
        for surface in with_current_evidence_json(JSON_SCORECARD_AUDIT_ROUTE_SURFACES, current_evidence_json)
    ]
    rebuild_contract_rows = [
        check_json_rebuild_validation_contract_surface(surface)
        for surface in with_current_evidence_json(JSON_REBUILD_VALIDATION_CONTRACT_SURFACES, current_evidence_json)
    ]
    rows = text_rows + ci_text_rows + json_rows + ci_json_rows + route_json_rows + rebuild_contract_rows
    failed = [row for row in rows if row["status"] != "pass"]
    return {
        "generated_at": generated_at,
        "suite_status": "pass" if not failed else "fail",
        "valid_evidence_scope": SCORECARD_AUDIT_VALID_EVIDENCE_SCOPE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "evidence_boundary_metadata": build_evidence_boundary_metadata(decision_gate_minimums),
        "scorecard_contract_source": str(scorecard_json.relative_to(BASE)) if scorecard_json.is_relative_to(BASE) else str(scorecard_json),
        "scorecard_ranking_contract": contract,
        "scorecard_ci_only_diagnostic_source": (
            f"{scorecard_json.relative_to(BASE) if scorecard_json.is_relative_to(BASE) else scorecard_json}:"
            f"{OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}"
        ),
        "scorecard_ci_only_diagnostic": ci_only_diagnostic,
        "decision_gate_minimums_source": (
            f"{scorecard_json.relative_to(BASE) if scorecard_json.is_relative_to(BASE) else scorecard_json}:"
            "decision_gate_minimums"
        ),
        "decision_gate_minimums": decision_gate_minimums,
        "known_rank_override": contract["known_rank_override"],
        "row_count": len(rows),
        "pass_count": len(rows) - len(failed),
        "fail_count": len(failed),
        "rows": rows,
        "summary": {
            "suite_read": (
                f"{len(rows) - len(failed)}/{len(rows)} checked surfaces carry the tier-first scorecard ranking contract or OP_REFINED CI-only diagnostic; "
                "the current-evidence bridge also carries the source-matched scorecard-audit route and settlement-audit -> current-bridge -> bridge-validator rebuild order; this is wording/provenance synchronization only, not settled ROI, promotion readiness, live profitability, or real-money evidence."
            ),
            "report_safe_read": (
                "Raw Score / forward_trust and positive OP_REFINED CI support remain support context; neither is an automatic promotion queue."
            ),
        },
    }


def assert_critical_current_evidence_rows_pass(payload: dict[str, Any]) -> None:
    failures: list[str] = []
    for row in payload["rows"]:
        if row["name"] not in CRITICAL_CURRENT_EVIDENCE_ROW_NAMES or row["status"] == "pass":
            continue
        issue_text = "; ".join(row.get("issues") or row.get("missing_phrases") or [])
        failures.append(f"{row['name']}: {issue_text or 'status=fail'}")
    if failures:
        raise ValueError(
            "critical current_evidence_summary.json bridge rows failed before writing "
            "scorecard audit artifacts: "
            + " | ".join(failures)
        )


def render_markdown(payload: dict[str, Any]) -> str:
    contract = payload["scorecard_ranking_contract"]
    gates = payload["decision_gate_minimums"]
    lines = [
        "# Scorecard Ranking / CI-Only Usage Audit",
        "",
        f"Generated: {payload['generated_at']}",
        f"Status: **{payload['suite_status'].upper()}** ({payload['pass_count']}/{payload['row_count']} surfaces pass)",
        "",
        "## Evidence Boundary",
        "",
        f"`valid_evidence_scope={payload['valid_evidence_scope']}`",
        "",
        "This audit only checks whether report-facing surfaces carry the frozen scorecard ranking semantics and OP_REFINED CI-only diagnostic. It is **not** new forward evidence, settled ROI, promotion readiness, live profitability, or real-money evidence.",
        "",
        "## Contract Source",
        "",
        f"- Source: `{payload['scorecard_contract_source']}`",
        f"- tier-first rank: `{contract['rank_is_tier_first_decision_order']}`",
        f"- forward_trust / Score secondary within tier: `{contract['forward_trust_is_secondary_within_tier']}`",
        f"- raw Score not automatic deployment instruction: `{contract['raw_score_is_not_an_automatic_deployment_instruction']}`",
        f"- known override: {contract['known_rank_override']}",
        "",
        "## CI-Only Diagnostic Source",
        "",
        f"- Source: `{payload['scorecard_ci_only_diagnostic_source']}`",
        f"- candidate: `{payload['scorecard_ci_only_diagnostic']['candidate_rule_id']}`",
        f"- current anchor: `{payload['scorecard_ci_only_diagnostic']['current_anchor_rule_id']}`",
        f"- ci_only_promotion_allowed: `{str(payload['scorecard_ci_only_diagnostic']['ci_only_promotion_allowed']).lower()}`",
        f"- current decision: {payload['scorecard_ci_only_diagnostic']['current_decision']}",
        "",
        "## Decision Gate Minimums",
        "",
        f"- Source: `{payload['decision_gate_minimums_source']}`",
        f"- anchor_displacement: `{gates['anchor_displacement']['min_roi_complete_settled_observations']}` ROI-complete same-candidate settled observations",
        f"- phase8_promotion_review: `{gates['phase8_promotion_review']['min_roi_complete_settled_observations']}` ROI-complete candidate shadow observations",
        f"- real_money_discussion: `{gates['real_money_discussion']['min_total_settled_observations_with_usable_roi']}` total settled observations with usable ROI",
        "- no BAQ-as-BEL prerequisite: `present`",
        "",
        "These are future paper-observation floors copied from the scorecard. This audit does not clear them.",
        "",
        "## Surface Inventory",
        "",
        "| Status | Surface | Kind | Role | Path | Bytes | SHA-256 | Issue summary |",
        "|---|---|---|---|---|---:|---|---|",
    ]
    for row in payload["rows"]:
        if row["kind"] == "text":
            issues = "ok" if not row["missing_phrases"] else "; ".join(row["missing_phrases"])
        else:
            issues = "ok" if not row["issues"] else "; ".join(row["issues"])
        sha = row["sha256"] or "n/a"
        lines.append(
            f"| {row['status']} | `{row['name']}` | {row['kind']} | {row['role']} | `{row['path']}` | {row['bytes']} | `{sha}` | {issues} |"
        )
    lines.extend(
        [
            "",
            "## Bottom Line",
            "",
            "Use this audit to catch wording/provenance drift after scorecard edits. Do not use it to promote `OP_REFINED_K7`, treat CI-only coverage as a cleared paper-observation gate, reopen odds-only XGBoost, substitute `BAQ` for `BEL`, or discuss real-money sizing.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit scorecard ranking-contract usage across report surfaces")
    parser.add_argument("--generated-at", default=datetime.now(ZoneInfo("Europe/Zagreb")).strftime("%Y-%m-%d %H:%M %Z"), help="timestamp string for deterministic renders")
    parser.add_argument("--scorecard-json", default=str(SCORECARD_JSON), help="scorecard JSON source path")
    parser.add_argument(
        "--current-evidence-json",
        default=str(CURRENT_EVIDENCE_JSON),
        help="current-evidence bridge JSON source path",
    )
    parser.add_argument("--md-output", default=str(MD_OUTPUT), help="markdown output path")
    parser.add_argument("--json-output", default=str(JSON_OUTPUT), help="JSON output path")
    args = parser.parse_args()

    payload = build_payload(
        generated_at=args.generated_at,
        scorecard_json=Path(args.scorecard_json),
        current_evidence_json=Path(args.current_evidence_json),
    )
    assert_critical_current_evidence_rows_pass(payload)
    md = render_markdown(payload)

    md_output = Path(args.md_output)
    json_output = Path(args.json_output)
    md_output.write_text(md, encoding="utf-8")
    json_output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {md_output}")
    print(f"Wrote {json_output}")
    if payload["suite_status"] != "pass":
        print(f"FAIL: {payload['fail_count']} surfaces missing ranking-contract coverage")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
