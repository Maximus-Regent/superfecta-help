#!/usr/bin/env python3
"""
Validation for COLE_STATUS_AND_PLAN.md.

Purpose:
- keep the main status document aligned with the frozen evaluation standard
- stop the top repo map from drifting away from the real validation and operator entrypoints
- make the primary cold-start document fail loudly when it points at stale paths or stale posture
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

BASE = Path(__file__).resolve().parent
DOC = BASE / "COLE_STATUS_AND_PLAN.md"
OUT_DIR = BASE / "out" / "status_validation" / "cole_status_and_plan"
OUT_MD = OUT_DIR / "cole_status_and_plan_validation.md"
OUT_JSON = OUT_DIR / "cole_status_and_plan_validation.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
REBUILD_COMMAND = "python3 validate_cole_status_and_plan.py"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
COPIED_CURRENT_FANOUT_TEXT = (
    "If that bridge rebuild will feed report-facing comparison quotes, do not stop after the three bridge "
    "commands. Run the copied-current-paper fanout first: frozen replay (`python3 "
    "validate_frozen_portfolio_eval_caution.py`), downstream A/B (`python3 "
    "validate_ab_downstream_comparison.py`), compare-main (`python3 validate_compare_main_approaches.py`), "
    "OP-anchor (`python3 validate_op_anchor_method_comparison.py`), OP-family (`python3 "
    "validate_op_family_decision.py`), cross-family (`python3 validate_cross_family_decision.py`), "
    "method-family (`python3 validate_method_family_decision_card.py`), portfolio (`python3 "
    "validate_portfolio_decision_card.py`), selective-scope (`python3 validate_compare_recommender_scope_paths.py`), "
    "scorecard audit (`python3 validate_scorecard_ranking_contract_audit.py`), frozen evidence chain "
    "(`python3 validate_frozen_evidence_chain.py --reuse-existing-child-json`), report surfaces (`python3 "
    "validate_report_surfaces.py --reuse-existing-child-json`), and project surfaces (`python3 "
    "validate_project_surfaces.py --reuse-existing-child-json`). Treat this fanout as copied-current-paper "
    "snapshot drift prevention only, not evidence movement, settled ROI, promotion readiness, live profitability, "
    "bankroll guidance, or real-money evidence."
)

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "main status / repo-map validator",
    "source_scope": [
        "COLE_STATUS_AND_PLAN.md",
        "forward_evidence_scorecard.json decision_gate_minimums",
        "suggested reading order",
        "appendix file map",
        "documented validator routes",
        "documented operator entrypoints",
    ],
    "valid_use": "cold-start status, read-order, validator-routing, and repo-map alignment audit",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "status_validator_passes_are_status_map_metadata_only": True,
    "stronger_forward_confidence_requires": [
        "qualifying live paper signals",
        "ROI-complete settled paper rows",
        "settlement-quality checks",
        "other real forward observations",
    ],
    "non_goals": [
        "do not use status-doc alignment as settled ROI",
        "do not use repo-map cleanliness as live profitability evidence",
        "do not promote OP_REFINED_K7 or Phase 8 from status-doc validation cleanliness",
        "do not reopen current odds-only XGBoost from status-doc validation cleanliness",
        "do not substitute BAQ for BEL",
        "do not treat documented file paths as real-money evidence",
    ],
}


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "pass", "detail": detail}


def require_contains(text: str, needle: str, name: str, detail: str) -> dict[str, Any]:
    return require(needle in text, name, detail)


def require_not_contains(text: str, needle: str, name: str, detail: str) -> dict[str, Any]:
    return require(needle not in text, name, detail)


def require_paths_exist(paths: list[Path], name: str, detail: str) -> dict[str, Any]:
    missing = [str(path.relative_to(BASE)) if BASE in path.parents else str(path) for path in paths if not path.exists()]
    if missing:
        raise AssertionError(f"{name}: {detail}; missing: {', '.join(missing)}")
    return {"check": name, "status": "pass", "detail": detail}


def require_positive_non_bool_int(value: Any, *, source_name: str, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, source_name: str, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise AssertionError(f"{source_name} {field_name} must be a list of non-empty strings")
    return value


def current_paper_context(current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    payload = json.loads(Path(current_evidence_json_path).read_text(encoding="utf-8"))
    primary = payload["current_paper_status"]["primary"]
    shadow = payload["current_paper_status"]["shadow"]
    rebuild_contract = payload.get("rebuild_validation_contract")
    if not isinstance(rebuild_contract, dict):
        raise AssertionError("current_evidence_summary.json must publish rebuild_validation_contract as an object")
    upstream_refresh_order = rebuild_contract.get("upstream_refresh_order")
    if not isinstance(upstream_refresh_order, list):
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order must be a list")
    upstream_refresh_order_commands = [
        str(item.get("command") or "").strip() for item in upstream_refresh_order if isinstance(item, dict)
    ]
    expected_rebuild_order = [
        "python3 paper_trade_settlement_audit.py",
        "python3 current_evidence_summary.py",
        "python3 validate_current_evidence_summary.py",
    ]
    if upstream_refresh_order_commands != expected_rebuild_order:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order drifted")
    expected_rebuild_fields = {
        "prerequisite_rebuild_command": "python3 paper_trade_settlement_audit.py",
        "rebuild_command": "python3 current_evidence_summary.py",
        "direct_validation_command": "python3 validate_current_evidence_summary.py",
        "upstream_refresh_order_valid_use": (
            "reproducible rebuild order for current bridge provenance after scorecard/rules/ledger byte changes"
        ),
    }
    for key, expected in expected_rebuild_fields.items():
        if rebuild_contract.get(key) != expected:
            raise AssertionError(f"current_evidence_summary.json rebuild_validation_contract.{key} drifted")
    for flag in (
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
        "requires_source_consistency_before_quoting_current_totals",
        "requires_source_freshness_before_right_now_instruction_use",
        "upstream_refresh_order_is_provenance_metadata_only",
        "not_settled_roi_or_real_money_evidence",
    ):
        if rebuild_contract.get(flag) is not True:
            raise AssertionError(f"current_evidence_summary.json rebuild_validation_contract.{flag} must be true")
    rebuild_order_read = (
        "Bridge rebuild order from `current_evidence_summary.json.rebuild_validation_contract`: after "
        "scorecard/rules/signals/settlement-ledger source-byte changes, run "
        "`python3 paper_trade_settlement_audit.py`, then `python3 current_evidence_summary.py`, then "
        "`python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*`; "
        "this order is provenance/rebuild metadata only, not settled ROI, promotion readiness, "
        "live profitability, or real-money evidence."
    )
    gate_progress = payload.get("decision_gate_progress")
    if not isinstance(gate_progress, dict):
        raise AssertionError("current_evidence_summary.json must publish decision_gate_progress as an object")
    gate_progress_read = str(gate_progress.get("read") or "").strip()
    if not gate_progress_read:
        raise AssertionError("current_evidence_summary.json decision_gate_progress.read must be populated")
    if gate_progress.get("gate_status") != "all_uncleared" or gate_progress.get("all_gates_ready") is not False:
        raise AssertionError("current_evidence_summary.json decision_gate_progress must keep all gates uncleared")
    for flag in (
        "not_forward_performance_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_real_money_evidence",
    ):
        if gate_progress.get(flag) is not True:
            raise AssertionError(f"current_evidence_summary.json decision_gate_progress.{flag} must be true")
    operator_read_gate = payload.get("operator_read_gate")
    if not isinstance(operator_read_gate, dict):
        raise AssertionError("current_evidence_summary.json must publish operator_read_gate as an object")
    if operator_read_gate != payload.get("current_paper_status", {}).get("operator_read_gate"):
        raise AssertionError("current_evidence_summary.json operator_read_gate must match current_paper_status.operator_read_gate")
    if operator_read_gate.get("gate_status") not in {
        "refresh_required_before_evidence_read",
        "current_operator_routing_context_only",
    }:
        raise AssertionError("current_evidence_summary.json operator_read_gate must publish a known routing state")
    if operator_read_gate.get("valid_use") != "operator instruction/evidence-read gating only":
        raise AssertionError("current_evidence_summary.json operator_read_gate valid_use drifted")
    if not isinstance(operator_read_gate.get("recommended_command"), str) or not operator_read_gate.get("recommended_command"):
        raise AssertionError("current_evidence_summary.json operator_read_gate must publish a recommended command")
    for flag in (
        "requires_refresh_before_evidence_read",
        "requires_source_freshness_refresh",
        "has_wrapper_refresh_action",
        "has_api_access_failure_context",
        "has_scanner_failure_boundary",
        "has_stale_cache_fallback_context",
        "has_issue_bucket",
    ):
        if not isinstance(operator_read_gate.get(flag), bool):
            raise AssertionError(f"current_evidence_summary.json operator_read_gate.{flag} must be boolean")
    for flag in (
        "not_forward_performance_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_real_money_evidence",
    ):
        if operator_read_gate.get(flag) is not True:
            raise AssertionError(f"current_evidence_summary.json operator_read_gate.{flag} must be true")
    for flag in (
        "current_top_card_counts_as_no_target_evidence",
        "current_top_card_counts_as_clean_empty_evidence",
        "current_top_card_counts_as_bet_readiness_evidence",
        "current_top_card_counts_as_settled_roi_evidence",
    ):
        if operator_read_gate.get(flag) is not False:
            raise AssertionError(f"current_evidence_summary.json operator_read_gate.{flag} must be false")
    operator_read_gate_read = str(operator_read_gate.get("read") or "").strip()
    if not operator_read_gate_read:
        raise AssertionError("current_evidence_summary.json operator_read_gate.read must be populated")
    for phrase in (
        str(operator_read_gate.get("recommended_command") or ""),
        "settled ROI",
        "real-money",
    ):
        if phrase not in operator_read_gate_read:
            raise AssertionError(f"current_evidence_summary.json operator_read_gate.read missing {phrase!r}")
    recommendation_context = primary.get("recommendation_context", {})
    if not isinstance(recommendation_context, dict):
        recommendation_context = {}
    first = primary["first_read"]
    broader = primary["portfolio_review"]
    rule_rows = {row["rule_id"]: row for row in primary.get("rule_progress", [])}
    shadow_rule_rows = {row["rule_id"]: row for row in shadow.get("rule_progress", [])}

    roi_complete = int(primary["roi_complete_settled"])
    open_rows = int(primary["open_settlements"])
    open_queue = primary.get("open_settlement_queue_by_rule")
    if not isinstance(open_queue, dict):
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule must be an object"
        )
    open_settlement_queue_state = str(open_queue.get("open_settlement_queue_state") or "").strip()
    open_settlement_context = str(open_queue.get("open_settlement_context") or "").strip()
    open_settlement_detail_read = str(open_queue.get("detail_read") or "").strip()
    expected_open_settlement_queue_state = "closed" if open_rows == 0 else "open"
    if open_settlement_queue_state not in {"closed", "open"}:
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_queue_state must be closed or open"
        )
    if open_settlement_queue_state != expected_open_settlement_queue_state:
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_queue_state must match current_paper_status.primary.open_settlements"
        )
    if open_rows == 0 and open_settlement_context != "no open primary settlement rows":
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_context must publish the closed-queue context when no rows are open"
        )
    if open_rows > 0 and not open_settlement_context:
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_context must be populated when rows are open"
        )
    if "Open settlement queue by rule:" not in open_settlement_detail_read:
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "detail_read must carry by-rule queue detail"
        )
    if "Settlement queue state:" in open_settlement_detail_read:
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "detail_read must not nest the settlement queue state wrapper"
        )
    source_published_queue_read = (
        f"settlement queue state: `{open_settlement_queue_state}`; "
        f"{open_settlement_context}; detail: {open_settlement_detail_read}"
    )
    open_settlement_summary = str(primary.get("open_settlement_summary") or "").strip()
    if open_rows and (not open_settlement_summary or open_settlement_summary == "none"):
        open_settlement_summary = "open row identity missing from current evidence bridge; inspect settlement audit before settlement"
    hit_count = int(primary["hit_count"])
    miss_count = int(primary["miss_count"])
    first_gate = f"{int(first['current'])}/{int(first['threshold'])}"
    broader_gate = f"{int(broader['current'])}/{int(broader['threshold'])}"
    hit_rate_pct = float(primary["hit_rate"]) * 100.0
    flat_roi_pct = float(primary["flat_ticket_roi"]) * 100.0
    cd_rows = int(rule_rows.get("CD_CORE_K8", {}).get("roi_complete_settled_rows", 0))
    op_rows = int(rule_rows.get("OP_DURABLE_K7", {}).get("roi_complete_settled_rows", 0))
    shadow_roi_complete = int(shadow.get("roi_complete_settled", 0))
    cd_refined_shadow_rows = int(shadow_rule_rows.get("CD_REFINED_K9", {}).get("roi_complete_settled_rows", 0))
    cd_refined_shadow_progress = str(shadow_rule_rows.get("CD_REFINED_K9", {}).get("promotion_progress", "0/20 (0.0%)"))
    shadow_weakest_progress = "0/20"
    gate_read = str(shadow.get("promotion_gate_read", ""))
    marker = "weakest current rule coverage is "
    if marker in gate_read:
        shadow_weakest_progress = gate_read.split(marker, 1)[1].split(".", 1)[0]

    settlement_word = "settlement" if roi_complete == 1 else "settlements"
    open_row_word = "row" if open_rows == 1 else "rows"
    shadow_row_word = "row" if shadow_roi_complete == 1 else "rows"
    if hit_count == 0:
        outcome_phrase = "all misses"
    else:
        hit_word = "hit" if hit_count == 1 else "hits"
        miss_word = "miss" if miss_count == 1 else "misses"
        outcome_phrase = f"{hit_count} {hit_word} and {miss_count} {miss_word}"
    recommendation_read = str(recommendation_context.get("read") or "").strip()
    if not recommendation_read:
        recommendation_read = "Latest primary recommendation context is unavailable; inspect PAPER_TRADE_NOW before inferring bet readiness."
    if open_rows == 0:
        tldr_open_phrase = "no current primary rows open for settlement"
        infra_open_phrase = "no open primary settlement rows"
        step_open_phrase = "no open primary settlement rows"
        bridge_open_phrase = source_published_queue_read
        latest_recommendation_note = (
            f"Latest primary recommendation context: {recommendation_read} "
            f"The source-published settlement queue state stays `{open_settlement_queue_state}` / {open_settlement_context}, "
            "and the closed queue is settlement workflow metadata only."
        )
        latest_recommendation_file_map = (
            "latest primary recommendation context separated from source-published settlement-queue state/context, "
            "closed settlement-queue context with by-rule detail, "
        )
        summary_open_context = (
            "the latest primary recommendation context stays framed as operator context while the closed primary settlement queue stays workflow metadata only"
        )
        summary_sample_context = (
            "clean empty/no-target runs plus the first tiny settled sample and closed settlement queue stay framed as workflow/operability validation and observation collection rather than promotion-grade forward proof"
        )
        bridge_queue_route = "source-published settlement-queue state/context/detail with no currently open primary rows"
        bridge_read_scope = (
            "without mistaking a stale right-now source, latest recommendation-state operator context, closed settlement workflow, or the tiny settled sample for OP-anchor proof or strategy-change evidence"
        )
        summary_open_identity = "with no open primary settlement rows currently published"
    else:
        tldr_open_phrase = f"{open_rows} current primary {open_row_word} open for settlement"
        infra_open_phrase = f"{open_rows} open primary settlement {open_row_word}"
        step_open_phrase = f"{open_rows} open primary settlement {open_row_word}"
        bridge_open_phrase = f"{open_rows} open primary settlement {open_row_word} awaiting result/payout evidence"
        latest_recommendation_note = (
            f"Latest primary recommendation context: {recommendation_read} "
            f"The source-published settlement queue state stays `{open_settlement_queue_state}` / {open_settlement_context}. "
            f"The bridge-published open settlement identity is `{open_settlement_summary}` and remains settlement workflow only."
        )
        latest_recommendation_file_map = (
            "latest primary recommendation context separated from open-row settlement workflow, "
            "source-published settlement-queue state/context/detail plus exact open settlement row identity details, "
        )
        summary_open_context = (
            "the latest primary recommendation context stays framed as operator context while the current open-row identity stays settlement workflow only"
        )
        summary_sample_context = (
            "clean empty/no-target runs plus the first tiny settled sample and open settlement rows stay framed as workflow/operability validation and observation collection rather than promotion-grade forward proof"
        )
        bridge_queue_route = "source-published settlement-queue state/context/detail for open rows with exact open-row identity details"
        bridge_read_scope = (
            "without mistaking a stale right-now source, latest recommendation-state operator context, open settlement workflow, or the tiny settled sample for OP-anchor proof or strategy-change evidence"
        )
        summary_open_identity = f"with the current open-row identity preserved as {open_settlement_summary or 'none'} when present"

    return {
        "roi_complete": roi_complete,
        "open_rows": open_rows,
        "open_row_word": open_row_word,
        "settlement_word": settlement_word,
        "outcome_phrase": outcome_phrase,
        "first_gate": first_gate,
        "broader_gate": broader_gate,
        "first_threshold": int(first["threshold"]),
        "remaining_first": int(first["remaining"]),
        "hit_rate_int": f"{hit_rate_pct:.0f}%",
        "hit_rate_2": f"{hit_rate_pct:.2f}%",
        "flat_roi_int": f"{flat_roi_pct:.0f}%",
        "flat_roi_2": f"{flat_roi_pct:.2f}%",
        "cd_rows": cd_rows,
        "op_rows": op_rows,
        "shadow_roi_complete": shadow_roi_complete,
        "shadow_row_word": shadow_row_word,
        "cd_refined_shadow_rows": cd_refined_shadow_rows,
        "cd_refined_shadow_progress": cd_refined_shadow_progress,
        "shadow_weakest_progress": shadow_weakest_progress,
        "latest_recommendation_note": latest_recommendation_note,
        "latest_recommendation_file_map": latest_recommendation_file_map,
        "summary_open_context": summary_open_context,
        "summary_sample_context": summary_sample_context,
        "tldr_open_phrase": tldr_open_phrase,
        "infra_open_phrase": infra_open_phrase,
        "step_open_phrase": step_open_phrase,
        "bridge_open_phrase": bridge_open_phrase,
        "bridge_queue_route": bridge_queue_route,
        "bridge_read_scope": bridge_read_scope,
        "summary_open_identity": summary_open_identity,
        "open_settlement_summary": open_settlement_summary,
        "open_settlement_queue_state": open_settlement_queue_state,
        "open_settlement_context": open_settlement_context,
        "open_settlement_detail_read": open_settlement_detail_read,
        "source_published_queue_read": source_published_queue_read,
        "gate_progress_read": gate_progress_read,
        "gate_progress_gate_status": gate_progress.get("gate_status"),
        "operator_read_gate_read": operator_read_gate_read,
        "operator_read_gate_gate_status": operator_read_gate.get("gate_status"),
        "operator_read_gate_valid_use": operator_read_gate.get("valid_use"),
        "operator_read_gate_recommended_command": operator_read_gate.get("recommended_command"),
        "operator_read_gate_has_api_access_failure_context": operator_read_gate.get("has_api_access_failure_context"),
        "operator_read_gate_has_scanner_failure_boundary": operator_read_gate.get("has_scanner_failure_boundary"),
        "operator_read_gate_has_stale_cache_fallback_context": operator_read_gate.get(
            "has_stale_cache_fallback_context"
        ),
        "operator_read_gate_requires_refresh_before_evidence_read": operator_read_gate.get(
            "requires_refresh_before_evidence_read"
        ),
        "operator_read_gate_not_forward_performance_evidence": operator_read_gate.get(
            "not_forward_performance_evidence"
        ),
        "operator_read_gate_not_promotion_readiness_evidence": operator_read_gate.get(
            "not_promotion_readiness_evidence"
        ),
        "operator_read_gate_not_live_profitability_evidence": operator_read_gate.get(
            "not_live_profitability_evidence"
        ),
        "operator_read_gate_not_real_money_evidence": operator_read_gate.get("not_real_money_evidence"),
        "operator_read_gate_no_target_evidence": operator_read_gate.get("current_top_card_counts_as_no_target_evidence"),
        "operator_read_gate_clean_empty_evidence": operator_read_gate.get(
            "current_top_card_counts_as_clean_empty_evidence"
        ),
        "operator_read_gate_bet_readiness_evidence": operator_read_gate.get(
            "current_top_card_counts_as_bet_readiness_evidence"
        ),
        "operator_read_gate_settled_roi_evidence": operator_read_gate.get(
            "current_top_card_counts_as_settled_roi_evidence"
        ),
        "rebuild_order_read": rebuild_order_read,
        "rebuild_order_commands": upstream_refresh_order_commands,
        "rebuild_prerequisite_command": rebuild_contract.get("prerequisite_rebuild_command"),
        "rebuild_command": rebuild_contract.get("rebuild_command"),
        "rebuild_direct_validation_command": rebuild_contract.get("direct_validation_command"),
        "rebuild_requires_settlement_audit_refresh": rebuild_contract.get(
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
        ),
        "rebuild_requires_source_consistency": rebuild_contract.get(
            "requires_source_consistency_before_quoting_current_totals"
        ),
        "rebuild_requires_source_freshness": rebuild_contract.get(
            "requires_source_freshness_before_right_now_instruction_use"
        ),
        "rebuild_order_is_provenance_metadata_only": rebuild_contract.get(
            "upstream_refresh_order_is_provenance_metadata_only"
        ),
        "rebuild_not_settled_roi_or_real_money_evidence": rebuild_contract.get(
            "not_settled_roi_or_real_money_evidence"
        ),
    }


def scorecard_gate_context(scorecard_json_path: Path = SCORECARD_JSON) -> dict[str, Any]:
    source_path = Path(scorecard_json_path)
    source_name = source_path.name
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    gates = payload.get("decision_gate_minimums")
    if not isinstance(gates, dict):
        raise AssertionError(f"{source_name} is missing decision_gate_minimums")

    anchor_gate = gates.get("anchor_displacement")
    phase8_gate = gates.get("phase8_promotion_review")
    real_money_gate = gates.get("real_money_discussion")
    if not isinstance(anchor_gate, dict) or not isinstance(phase8_gate, dict) or not isinstance(real_money_gate, dict):
        raise AssertionError(f"{source_name} decision_gate_minimums is missing a required gate")

    anchor_min = require_positive_non_bool_int(
        anchor_gate.get("min_roi_complete_settled_observations"),
        source_name=source_name,
        field_name="decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
    )
    phase8_min = require_positive_non_bool_int(
        phase8_gate.get("min_roi_complete_settled_observations"),
        source_name=source_name,
        field_name="decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
    )
    real_money_min = require_positive_non_bool_int(
        real_money_gate.get("min_total_settled_observations_with_usable_roi"),
        source_name=source_name,
        field_name="decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
    )
    real_money_requirements = require_string_list(
        real_money_gate.get("also_requires"),
        source_name=source_name,
        field_name="decision_gate_minimums.real_money_discussion.also_requires",
    )
    if NO_BAQ_AS_BEL_PREREQUISITE not in real_money_requirements:
        raise AssertionError(
            f"{source_name} decision_gate_minimums.real_money_discussion.also_requires "
            f"must include {NO_BAQ_AS_BEL_PREREQUISITE}"
        )
    source_snippet = (
        "Gate source: the sample floors in this methodical order are sourced from "
        f"`{SCORECARD_JSON.name}` `decision_gate_minimums`: "
        f"`anchor_displacement.min_roi_complete_settled_observations={anchor_min}`, "
        f"`phase8_promotion_review.min_roi_complete_settled_observations={phase8_min}`, "
        f"and `real_money_discussion.min_total_settled_observations_with_usable_roi={real_money_min}`. "
        "These are future ROI-complete paper-observation floors only: "
        f"{phase8_min} shadow rows open Phase 8 review, "
        f"{anchor_min} same-candidate rows open anchor-review discussion, "
        f"and {real_money_min} total rows only open a human real-money-discussion review after settlement-quality/payout/concentration checks. "
        "They do not mean any gate has cleared."
    )
    return {
        "source": SCORECARD_JSON.name,
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_no_baq_as_bel_required": True,
        "source_snippet": source_snippet,
    }


def scorecard_audit_route_context(current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    payload = json.loads(Path(current_evidence_json_path).read_text(encoding="utf-8"))
    route = payload.get("scorecard_audit_route")
    if not isinstance(route, dict):
        raise AssertionError(f"{Path(current_evidence_json_path).name} is missing scorecard_audit_route")
    expected_snapshot = {
        "anchor_displacement_min_roi_complete_settled_observations": 30,
        "phase8_promotion_review_min_roi_complete_settled_observations": 20,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": 100,
        "real_money_no_baq_as_bel_required": True,
    }
    expected_fields = {
        "markdown_path": "SCORECARD_RANKING_CONTRACT_AUDIT.md",
        "json_path": "scorecard_ranking_contract_audit.json",
        "validator_command": "python3 validate_scorecard_ranking_contract_audit.py",
        "gate_floor_source": "forward_evidence_scorecard.json:decision_gate_minimums",
        "valid_use": "navigation route for scorecard gate/ranking/CI-only/timezone/no-BAQ synchronization checks",
    }
    for key, expected in expected_fields.items():
        if route.get(key) != expected:
            raise AssertionError(f"{Path(current_evidence_json_path).name} scorecard_audit_route.{key} drifted")
    if route.get("gate_floor_snapshot") != expected_snapshot:
        raise AssertionError(
            f"{Path(current_evidence_json_path).name} scorecard_audit_route.gate_floor_snapshot drifted"
        )
    if route.get("artifacts_present") is not True:
        raise AssertionError(
            f"{Path(current_evidence_json_path).name} scorecard_audit_route.artifacts_present must be true"
        )
    for flag in (
        "not_forward_performance_evidence",
        "not_settled_roi_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_bankroll_guidance",
        "not_real_money_evidence",
    ):
        if route.get(flag) is not True:
            raise AssertionError(f"{Path(current_evidence_json_path).name} scorecard_audit_route.{flag} must be true")
    route_read = str(route.get("route_read") or "").strip()
    for phrase in (
        "copied 30/20/100 gate floors",
        "tier-first ranking",
        "OP_REFINED CI-only support context",
        "generated-at timezone provenance",
        "no-BAQ-as-BEL prerequisite drift",
    ):
        if phrase not in route_read:
            raise AssertionError(
                f"{Path(current_evidence_json_path).name} scorecard_audit_route.route_read missing {phrase!r}"
            )
    return {
        "source": Path(current_evidence_json_path).name,
        "source_path": "scorecard_audit_route",
        "markdown_path": route.get("markdown_path"),
        "json_path": route.get("json_path"),
        "validator_command": route.get("validator_command"),
        "gate_floor_source": route.get("gate_floor_source"),
        "gate_floor_snapshot": route.get("gate_floor_snapshot"),
        "artifacts_present": route.get("artifacts_present"),
        "valid_use": route.get("valid_use"),
        "not_forward_performance_evidence": route.get("not_forward_performance_evidence"),
        "not_settled_roi_evidence": route.get("not_settled_roi_evidence"),
        "not_promotion_readiness_evidence": route.get("not_promotion_readiness_evidence"),
        "not_live_profitability_evidence": route.get("not_live_profitability_evidence"),
        "not_bankroll_guidance": route.get("not_bankroll_guidance"),
        "not_real_money_evidence": route.get("not_real_money_evidence"),
        "route_read": route_read,
    }


def current_status_snippets(context: dict[str, Any]) -> dict[str, str]:
    tldr = (
        "headline number. BEL is offline (track closed), the ML model adds zero value, and the daily\n"
        f"paper-trade wrapper is operational with its first {context['roi_complete']} ROI-complete `CD_CORE_K8` "
        f"{context['settlement_word']} recorded and {context['tldr_open_phrase']}, but the ROI-complete rows are {context['outcome_phrase']} and still only "
        f"{context['first_gate']} toward a first statistical read, so they are not promotion, live-profitability, "
        "or real-money evidence."
    )
    infra = (
        "| **Paper trade infrastructure** | Moderate — 4 scripts, EV engine, shell wrappers | Fully built and now exercised by saved daily wrapper runs. "
        f"Current primary ledgers now show {context['roi_complete']} ROI-complete `CD_CORE_K8` {context['settlement_word']}, "
        f"{context['infra_open_phrase']}, {context['hit_rate_int']} observed hit rate, "
        f"and {context['flat_roi_int']} flat-ticket ROI, which proves the scan/log/settle/read path is working but is still only "
        f"{context['first_gate']} toward a first statistical read and not strategy-change proof. |"
    )
    step1 = (
        "### Step 1: Paper trade Phase 7 core (OP + CD) — Keep the wrapper running on target days\n"
        "- The first clean runs and the first tiny settled sample are workflow validation and observation collection, not decision-grade forward proof by themselves.\n"
        f"- Current wrapper status: operational, with saved no-target / active-hit surfaces and {context['roi_complete']} ROI-complete primary-lane {context['settlement_word']}, "
        f"{context['step_open_phrase']}, observed hit rate {context['hit_rate_2']}, observed flat-ticket ROI {context['flat_roi_2']}, "
        f"and {context['remaining_first']} more ROI-complete rows still needed before the first {context['first_threshold']}-race statistical read.\n"
        "- Use existing `paper_trade_pipeline.py` through `./run_daily_portfolio_observation.sh` to scan daily"
    )
    bridge_context = (
        f"It is a report/navigation summary only: {context['roi_complete']} ROI-complete primary rows, all currently from `CD_CORE_K8` rather than `OP_DURABLE_K7`, "
        f"{context['hit_rate_int']} hit rate, "
        f"and {context['flat_roi_int']} flat-ticket ROI are current context, not promotion readiness, live profitability, OP-anchor forward proof, or real-money evidence. "
        f"Bridge-published `decision_gate_progress` read: {context['gate_progress_read']} "
        f"Source-published settlement queue read: {context['source_published_queue_read']} "
        f"The shadow watch lane now has {context['shadow_roi_complete']} ROI-complete settled {context['shadow_row_word']} "
        f"({context['cd_refined_shadow_rows']} from `CD_REFINED_K9`, {context['cd_refined_shadow_progress']}), while weakest shadow coverage remains {context['shadow_weakest_progress']}; "
        "that is watch-list bookkeeping, not Phase 8 promotion evidence. "
        "The bridge's CSV recompute is timestamp-aware: rows need usable return/cost plus an actual non-placeholder `settled_ts` before they count as ROI-complete. "
        f"{context['latest_recommendation_note']} "
        f"Operator read gate from `current_evidence_summary.json.operator_read_gate`: {context['operator_read_gate_read']} "
        f"Gate status `{context['operator_read_gate_gate_status']}` and valid use `{context['operator_read_gate_valid_use']}` "
        "are instruction/evidence-read routing only, not no-target evidence, clean-empty evidence, bet readiness, settled ROI, "
        "promotion readiness, live profitability, bankroll guidance, or real-money evidence. "
        f"{context['rebuild_order_read']}"
    )
    bridge_row = (
        "| `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` | Report-ready bridge from the frozen scorecard posture to the current `PAPER_TRADE_NOW` / settlement-audit paper status, "
        f"including source fingerprints, top-card / settlement-audit / timestamp-aware CSV source-consistency checks that require actual `settled_ts`, {context['bridge_queue_route']}, `operator_status_context`, "
        f"`source_freshness` / `requires_refresh_before_right_now_use` operator-readiness metadata, `operator_read_gate` instruction/evidence-read routing, OP anchor / CD companion / OP refined shadow roles, current primary rule mix showing {context['op_rows']} `OP_DURABLE_K7` and {context['cd_rows']} `CD_CORE_K8` ROI-complete settled rows, "
        f"current shadow watch coverage showing {context['shadow_roi_complete']} ROI-complete settled {context['shadow_row_word']} with `CD_REFINED_K9` at {context['cd_refined_shadow_progress']} and weakest shadow coverage still {context['shadow_weakest_progress']}, "
        f"direct `decision_gate_progress` read ({context['gate_progress_read']}), source-published `scorecard_audit_route` to `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py`, "
        "source-published `rebuild_validation_contract` order (`python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`) as provenance/rebuild metadata only, "
        f"{context['latest_recommendation_file_map']}and explicit no-new-forward-evidence / no-promotion / no-real-money boundaries | Read when Cole wants the shortest current-context summary {context['bridge_read_scope']} |"
    )
    summary_wrapper = (
        f"the paper-trade wrapper is now described as operational with {context['roi_complete']} ROI-complete `CD_CORE_K8` primary-lane {context['settlement_word']}, "
        f"{context['step_open_phrase']}, observed hit rate {context['hit_rate_2']}, observed flat-ticket ROI {context['flat_roi_2']}, "
        f"and {context['remaining_first']} more ROI-complete rows still needed before the first {context['first_threshold']}-race statistical read, "
        f"{context['summary_open_identity']}"
    )
    return {
        "tldr": tldr,
        "infra": infra,
        "step1": step1,
        "bridge_context": bridge_context,
        "bridge_row": bridge_row,
        "summary_wrapper": summary_wrapper,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the main Cole status and plan document")
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--current-evidence-json", type=Path, default=CURRENT_EVIDENCE_JSON)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def scorecard_gate_cli_contract_checks(scorecard_json_path: Path = SCORECARD_JSON) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="cole_status_scorecard_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(scorecard_json_path).read_text(encoding="utf-8"))
        scorecard_path = tmp_root / "forward_evidence_scorecard.json"
        bad_out_dir = tmp_root / "nested" / "cole_status_and_plan_validation"

        bool_payload = json.loads(json.dumps(base_payload))
        bool_payload["decision_gate_minimums"]["anchor_displacement"][
            "min_roi_complete_settled_observations"
        ] = True
        scorecard_path.write_text(json.dumps(bool_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(scorecard_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations must be a positive non-boolean integer" in proc.stderr,
                "scorecard_boolean_floor_fails_before_artifacts",
                "validate_cole_status_and_plan.py rejects a boolean scorecard anchor-displacement gate before creating nested output directories or partial validation artifacts",
            )
        )

        nonpositive_phase8_payload = json.loads(json.dumps(base_payload))
        nonpositive_phase8_payload["decision_gate_minimums"]["phase8_promotion_review"][
            "min_roi_complete_settled_observations"
        ] = 0
        scorecard_path.write_text(json.dumps(nonpositive_phase8_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(scorecard_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer" in proc.stderr,
                "scorecard_nonpositive_phase8_floor_fails_before_artifacts",
                "validate_cole_status_and_plan.py rejects a non-positive scorecard Phase 8 review gate before creating nested output directories or partial validation artifacts",
            )
        )

        nonpositive_real_money_payload = json.loads(json.dumps(base_payload))
        nonpositive_real_money_payload["decision_gate_minimums"]["real_money_discussion"][
            "min_total_settled_observations_with_usable_roi"
        ] = 0
        scorecard_path.write_text(json.dumps(nonpositive_real_money_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(scorecard_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer" in proc.stderr,
                "scorecard_nonpositive_real_money_floor_fails_before_artifacts",
                "validate_cole_status_and_plan.py rejects a non-positive scorecard real-money discussion gate before creating nested output directories or partial validation artifacts",
            )
        )

        missing_no_baq_payload = json.loads(json.dumps(base_payload))
        missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"]["also_requires"] = [
            requirement
            for requirement in missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"].get(
                "also_requires",
                [],
            )
            if requirement != NO_BAQ_AS_BEL_PREREQUISITE
        ]
        scorecard_path.write_text(json.dumps(missing_no_baq_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(scorecard_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.real_money_discussion.also_requires must include no BAQ-as-BEL substitution" in proc.stderr,
                "scorecard_missing_no_baq_fails_before_artifacts",
                "validate_cole_status_and_plan.py rejects a scorecard real-money gate that drops the no-BAQ-as-BEL prerequisite before creating nested output directories or partial validation artifacts",
            )
        )

    return checks


def current_bridge_cli_contract_checks(
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="cole_status_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json_path).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "cole_status_and_plan_validation"
        missing_contract_payload = json.loads(json.dumps(base_payload))
        missing_contract_payload.pop("rebuild_validation_contract", None)
        current_evidence_path.write_text(json.dumps(missing_contract_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--current-evidence-json",
                str(current_evidence_path),
                "--out-dir",
                str(missing_contract_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not missing_contract_out_dir.exists()
                and "current_evidence_summary.json must publish rebuild_validation_contract as an object"
                in proc.stderr,
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "validate_cole_status_and_plan.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial status-doc validation artifacts",
            )
        )

        weakened_contract_out_dir = tmp_root / "weakened" / "cole_status_and_plan_validation"
        weakened_contract_payload = json.loads(json.dumps(base_payload))
        weakened_contract_payload["rebuild_validation_contract"][
            "upstream_refresh_order_is_provenance_metadata_only"
        ] = False
        current_evidence_path.write_text(json.dumps(weakened_contract_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--current-evidence-json",
                str(current_evidence_path),
                "--out-dir",
                str(weakened_contract_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not weakened_contract_out_dir.exists()
                and "current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true"
                in proc.stderr,
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "validate_cole_status_and_plan.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial status-doc validation artifacts",
            )
        )

    return checks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    text = DOC.read_text(encoding="utf-8")
    current_context = current_paper_context(args.current_evidence_json)
    scorecard_gates = scorecard_gate_context(args.scorecard_json)
    scorecard_audit_route = scorecard_audit_route_context(args.current_evidence_json)
    current_snippets = current_status_snippets(current_context)

    checks: list[dict[str, Any]] = []
    if Path(args.scorecard_json).resolve() == SCORECARD_JSON.resolve():
        checks.extend(scorecard_gate_cli_contract_checks(args.scorecard_json))
    if Path(args.current_evidence_json).resolve() == CURRENT_EVIDENCE_JSON.resolve():
        checks.extend(current_bridge_cli_contract_checks(args.current_evidence_json))
    checks.append(
        require(
            all(
                marker in text
                for marker in [
                    "## TL;DR",
                    "## 5. The Evidence Hierarchy (Most to Least Trustworthy)",
                    "## 7. Honest Expected ROI Range Going Forward",
                    "## 13. Suggested Reading Order (So You Don't Bounce Around)",
                    "## Appendix: File Map (What's Important)",
                ]
            ),
            "main_sections_present",
            "the main status doc still includes the expected headline, evidence, ROI-range, reading-order, and file-map sections",
        )
    )
    checks.append(
        require_contains(
            text,
            "validation is honest and shows the real edge is probably **+20-25% ROI**, not the +47%\nheadline number.",
            "tldr_realistic_roi_guardrail",
            "the TLDR still keeps the realistic +20-25% read separate from the stale +47% headline",
        )
    )
    checks.append(
        require_contains(
            text,
            "That Phase 7 holdout was not smooth: **2024 was basically flat\n(+0.37% on 109 races)** and **2025 was much stronger (+105.38% on 66 races)**.",
            "tldr_phase7_split_note",
            "the TLDR now says plainly that the Phase 7 holdout lead came from a flat 2024 and much stronger 2025, not a smooth two-year path",
        )
    )
    checks.append(
        require_contains(
            text,
            "**Phase 7's simpler portfolio beat Phase 8 on forward data.**",
            "phase7_beats_phase8_key_insight",
            "the main status doc still says plainly that the simpler Phase 7 portfolio beat Phase 8 on forward data",
        )
    )
    checks.append(
        require_contains(
            text,
            "| **Phase 7 portfolio on 2024-2025 holdout** | Best forward evidence we have | **+38.68% ROI on 175 races** ($10,211 profit); split: 2024 **+0.37% on 109**, 2025 **+105.38% on 66** |",
            "phase7_holdout_row_split",
            "the main status doc now keeps the winning Phase 7 holdout row tied to its explicit 2024 and 2025 split counts",
        )
    )
    checks.append(
        require_contains(
            text,
            "| **Phase 8 portfolio on 2024-2025 holdout** | Also positive but weaker | +21.45% ROI on 118 races ($5,585 profit); split: 2024 +9.50% on 85, 2025 +50.26% on 33 |",
            "phase8_holdout_row_split",
            "the main status doc now keeps the weaker Phase 8 holdout row tied to its explicit 2024 and 2025 split counts too",
        )
    )
    checks.append(
        require_contains(
            text,
            "The 3-track portfolio (+38.68% holdout, with 2024 +0.37% on 109 and 2025 +105.38% on 66) outperformed the 7-track portfolio (+21.45% holdout, with 2024 +9.50% on 85 and 2025 +50.26% on 33). Simpler wins, but not because it produced a smooth two-year path.",
            "phase7_vs_phase8_split_key_insight",
            "the main status doc now says plainly that the Phase 7 over Phase 8 win was real but not a smooth year-by-year glide path",
        )
    )
    checks.append(
        require_contains(
            text,
            "| **OP_DURABLE_K7** (Phase 7) | +22.9% | 115 | Selected in 7/10 folds | +35.0% (505 races) | **HIGH** — largest forward sample, most selected rule in walk-forward |",
            "op_anchor_tier1_row",
            "the evidence hierarchy still presents OP_DURABLE_K7 as the safest current anchor with the larger holdout sample and strongest walk-forward coverage",
        )
    )
    checks.append(
        require_contains(
            text,
            "| **CD_CORE_K8** (Phase 7) | +55.96% | 60 | Selected in 1 fold (but CD_REFINED selected in 7) | +13.1% (485 races) | **MEDIUM-HIGH** — holdout looks great, but CD variants are confusing (K8 vs K9) |",
            "cd_core_tier1_row",
            "the evidence hierarchy still keeps CD_CORE_K8 in the deploy-now tier without silently promoting it above the OP anchor",
        )
    )
    checks.append(
        require_contains(
            text,
            "| **Realistic** (walk-forward) | +20-25% | Train-only selection, 470 races |",
            "realistic_roi_range_row",
            "the honest ROI range still centers the walk-forward +20-25% expectation instead of a headline backtest number",
        )
    )
    checks.append(
        require_contains(
            text,
            "| **Conservative** (walk-forward minus BEL) | +10-18% | OP + CD without BEL anchor |",
            "conservative_roi_range_row",
            "the honest ROI range still keeps the BEL-free conservative case visible",
        )
    )
    checks.append(
        require_contains(
            text,
            current_snippets["tldr"],
            "tldr_wrapper_operational_with_tiny_settled_sample",
            "the TL;DR now reflects that the wrapper has its first tiny settled paper sample while preserving the too-early / no-promotion / no-live-profitability / no-real-money boundary",
        )
    )
    checks.append(
        require_contains(
            text,
            current_snippets["infra"],
            "paper_trade_infra_operational_with_pre_evidence_settlements",
            f"the main status doc now says plainly that paper-trade infrastructure has settled rows and a readable forward check, but that the tiny {current_context['first_gate']} sample is operational/ledger evidence rather than strategy-change proof",
        )
    )
    checks.append(
        require_contains(
            text,
            "| **Paper-trade observation gap** | Keep the daily wrapper running on OP / CD race days. The pipeline is operational; the remaining gap is qualifying observations plus ROI-complete settlements, not more rule tuning or a new edge claim from clean empty/no-target runs. |",
            "paper_trade_observation_gap_not_rule_tuning",
            "the how-to-cut row now says plainly that the remaining paper-trade gap is qualifying observations and ROI-complete settlements, not claiming a new edge from clean empty/no-target runs",
        )
    )
    checks.append(
        require_contains(
            text,
            current_snippets["step1"],
            "step1_sample_collection_not_decision_grade",
            f"the step-1 action list now keeps the first tiny settled sample framed as observation collection while naming the operational wrapper status, tiny {current_context['first_gate']} sample, and no-decision-grade boundary",
        )
    )
    checks.append(
        require(
            scorecard_gates["source_snippet"] in text
            and scorecard_gates["anchor_displacement_min_roi_complete_settled_observations"] == 30
            and scorecard_gates["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and scorecard_gates["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and "They do not mean any gate has cleared." in text,
            "methodical_test_gates_source_matched_to_scorecard",
            "the read-first methodical-test order now names the scorecard JSON decision_gate_minimums as the source for the 30-row anchor-review, 20-row Phase 8 review, and 100-row real-money-discussion floors, while saying those floors are future paper-observation requirements rather than cleared gates",
        )
    )
    checks.append(
        require(
            "`current_evidence_summary.json.scorecard_audit_route` is the bridge-owned route to the copied-gate/ranking audit" in text
            and "when the question is whether report-facing surfaces still copy those floors, the tier-first ranking contract, OP_REFINED CI-only support context, generated-at timezone provenance, and the no-BAQ-as-BEL prerequisite correctly, read `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` and run `python3 validate_scorecard_ranking_contract_audit.py`; that route and audit are report-synchronization metadata only, not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence." in text
            and "| `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` | Cross-surface audit that the scorecard ranking contract, OP_REFINED CI-only diagnostic context, copied 30/20/100 gate floors, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite still match the source scorecard; this is report-synchronization / reproducibility metadata only, not promotion readiness, live profitability, bankroll guidance, or real-money evidence | Read when checking whether report-facing scorecard copies drifted |" in text
            and "| `validate_scorecard_ranking_contract_audit.py` | Direct validator for the scorecard ranking-contract audit, including source-matched report-surface fingerprints, source-copied `decision_gate_minimums`, no-BAQ prerequisite routing, generated-at timezone provenance, and no-new-evidence boundaries | Run when changing scorecard ranking, gate-floor, OP_REFINED CI-only, or no-BAQ-as-BEL wording across report-facing surfaces |" in text,
            "scorecard_audit_gate_route_documented",
            "the main status doc now points scorecard gate-floor / tier-first ranking / OP_REFINED CI-only / timezone / no-BAQ prerequisite questions through the current-evidence bridge-owned route to the direct scorecard audit and validator while keeping that route as report-synchronization metadata only",
        )
    )
    checks.append(
        require(
            scorecard_audit_route["source"] == CURRENT_EVIDENCE_JSON.name
            and scorecard_audit_route["source_path"] == "scorecard_audit_route"
            and scorecard_audit_route["markdown_path"] == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route["json_path"] == "scorecard_ranking_contract_audit.json"
            and scorecard_audit_route["validator_command"] == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route["gate_floor_source"] == "forward_evidence_scorecard.json:decision_gate_minimums"
            and scorecard_audit_route["gate_floor_snapshot"]["anchor_displacement_min_roi_complete_settled_observations"] == 30
            and scorecard_audit_route["gate_floor_snapshot"]["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and scorecard_audit_route["gate_floor_snapshot"]["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and scorecard_audit_route["gate_floor_snapshot"]["real_money_no_baq_as_bel_required"] is True
            and scorecard_audit_route["artifacts_present"] is True
            and scorecard_audit_route["not_forward_performance_evidence"] is True
            and scorecard_audit_route["not_settled_roi_evidence"] is True
            and scorecard_audit_route["not_promotion_readiness_evidence"] is True
            and scorecard_audit_route["not_live_profitability_evidence"] is True
            and scorecard_audit_route["not_bankroll_guidance"] is True
            and scorecard_audit_route["not_real_money_evidence"] is True
            and "`scorecard_audit_route`" in current_snippets["bridge_row"]
            and "source-published `scorecard_audit_route` to `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py`" in text,
            "current_evidence_scorecard_audit_route_present",
            "the main status doc now consumes current_evidence_summary.json scorecard_audit_route as the source-backed route for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks, with the 30/20/100/no-BAQ snapshot and non-evidence flags intact",
        )
    )
    checks.append(
        require(
            "- Target: OP races only when the current calendar/preflight says Oaklawn is actually active; the Jan-May meet window is seasonal context, not a standing \"now\" instruction." in text
            and "- Target: CD races only when the current calendar/preflight says Churchill is active; the Apr-Nov meet window is seasonal context, not a substitute for the daily target-track check." in text
            and "Jan-May meet is active NOW" not in text
            and "spring meet active NOW" not in text,
            "target_tracks_are_calendar_checked_not_static_now",
            "the status doc no longer says OP or CD meets are active NOW; it treats meet windows as seasonal context and routes actual action through the daily calendar/preflight check",
        )
    )
    checks.append(
        require(
            "### Step 5: After 100+ ROI-complete paper observations total — evidence review, not bankroll advice" in text
            and "payout concentration, and settlement-quality coverage" in text
            and "write a paper-trade review memo and decide whether a separate, human-approved real-money risk plan is even worth discussing; this status doc does not recommend a bet size" in text
            and "Do not place, size, or scale real-money bets from this document." in text
            and "no bankroll, stop-loss, or scale-up numbers are authorized here" in text
            and "Start at $2/combo flat" not in text
            and "Maximum bankroll at risk: $500" not in text
            and "Scale up only after 200+ real bets" not in text,
            "real_money_path_deferred_to_separate_review",
            "the methodical test order now stops the main status doc at paper-evidence review and separate human-approved risk planning instead of carrying concrete bankroll, stop-loss, or scale-up instructions",
        )
    )
    checks.append(
        require(
            "## 10. Next Operator Session — Concrete Current Routine" in text
            and "Read `PAPER_TRADE_NOW.md` plus `PAPER_TRADE_NOW.json` first, before opening older run folders." in text
            and "If OP / CD are not racing or the preflight says no target tracks, stand down; do not backfill a signal, do not substitute BAQ for BEL, and do not treat a clean empty day as performance evidence." in text
            and "Run `./run_daily_portfolio_observation.sh` as the preferred primary + shadow wrapper." in text
            and "Treat green validators as reproducibility/readiness checks only — not settled ROI, promotion readiness, live profitability, or real-money evidence." in text,
            "next_operator_session_uses_current_wrapper",
            "the current operator-session checklist starts with the right-now bundle, routes target days through the daily primary+shadow wrapper, preserves the no-target/no-BAQ/no-performance-evidence boundary, and frames validators as readiness checks only",
        )
    )
    checks.append(
        require(
            "## 10. Next 16 Hours" not in text
            and "Run `./run_paper_trade_cycle.sh` and confirm it produces output" not in text
            and "(new script, created tonight)" not in text
            and 'Update this document with "Session 1 notes" section at the bottom' not in text,
            "legacy_tonight_checklist_removed",
            "the main status doc no longer carries the stale one-night setup checklist, legacy one-basket wrapper as the first operator action, or session-1/today-tonight phrasing after the daily wrapper has already been exercised",
        )
    )
    checks.append(
        require_contains(
            text,
            "- **BAQ (Big A at Aqueduct)** has been hosting some races during closure.",
            "baq_context_present",
            "the status doc still names BAQ explicitly instead of letting BEL and BAQ blur together",
        )
    )
    checks.append(
        require_contains(
            text,
            "- The walk-forward tested a BEL->BAQ bridge: **-91.55% ROI on 7 races**. Dead end.",
            "baq_bridge_dead_end",
            "the status doc still records the BEL-to-BAQ bridge as a dead end",
        )
    )
    checks.append(
        require_contains(
            text,
            "- Do NOT bet BAQ as if it were BEL. The edge does not transfer.",
            "baq_aliasing_guardrail",
            "the status doc still says plainly not to alias BAQ as BEL",
        )
    )
    checks.append(
        require_contains(
            text,
            "1. `forward_evidence_scorecard.txt` for the current forward-trust ranking\n2. `OP_FAMILY_DECISION.md` for the anchor question inside the OP family\n3. `CROSS_FAMILY_DECISION.md` for the anchor / paper / watch shortlist, current-paper snapshot caveat, and the explicit boundary that CD-only settled context / source-published settlement-queue state is not OP-anchor proof or cross-family promotion evidence\n4. `PORTFOLIO_DECISION_CARD.md` for `PAPER NOW` vs `SHADOW ONLY` vs `BENCHMARK ONLY`\n5. `METHOD_FAMILY_DECISION.md` for the selective-rule path versus the Harville benchmark and the parked current odds-only XGBoost path\n6. `compare_main_approaches.md` plus its matched `.csv` and `.json` siblings for the one-screen OP/CD/shadow/Harville/XGBoost comparison, evidence-class triage, source-provenance/parity sidecar, machine-readable evidence_boundary metadata, machine-readable `decision_change_gate_minimums` naming `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100`, and evidence-scope decision-change gates",
            "evidence_reading_order_present",
            "the suggested evidence reading order still starts with the scorecard, walks through the current decision-card stack, and now routes cross-family current-paper snapshot caveats before broad comparison questions",
        )
    )
    checks.append(
        require_contains(
            text,
            "For full-data XGBoost retrain questions, read `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py` only as model-fit reproducibility context: large RMSE / MAE improvements and exact retrain/prediction commands are not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence. Deployment interpretation still routes back to the selective OP/CD paper path and the comparison artifacts above.",
            "full_data_retrain_evidence_route_present",
            "the suggested evidence reading order now routes full-data XGBoost retrain metrics and exact command checks to the dedicated artifact/validator while keeping them model-fit-only rather than deployment evidence",
        )
    )
    checks.append(
        require(
            "`CROSS_FAMILY_DECISION.md` for the anchor / paper / watch shortlist, current-paper snapshot caveat" in text
            and "CD-only settled context / source-published settlement-queue state is not OP-anchor proof or cross-family promotion evidence" in text
            and "`validate_cross_family_decision.py` | Rebuild/consistency check for the cross-family shortlist, including saved CSV/markdown surfaces, real CLI stdout, the current anchor / paper / watch ordering, current-paper snapshot caveat, and no cross-family promotion-evidence boundary" in text,
            "cross_family_current_paper_route_present",
            "the main status doc now routes cross-family current-paper snapshot caveats to the direct cross-family validator and keeps CD-only/open-row context out of OP-anchor proof or promotion evidence",
        )
    )
    checks.append(
        require_contains(
            text,
            "1. `PAPER_TRADE_NOW.md` plus its matched `PAPER_TRADE_NOW.txt` and `PAPER_TRADE_NOW.json` siblings for the right-now top-card action; JSON should be source-matched to `paper_trade_now.py --format json` unless the full helper failed into an explicit no-new-forward-evidence placeholder.\n2. `PAPER_TRADE_USAGE.md` for the OP-anchor-first command path, the primary OP/CD paper-basket companion inside the primary basket, the separate Phase 8 shadow/watch routine, and OP-anchor provenance/readable-boundary route (`OP_ANCHOR_METHOD_COMPARISON.md` / `op_anchor_method_comparison.json` plus `validate_op_anchor_method_comparison.py`, including JSON `evidence_boundary_text`) with fingerprints and boundary text kept audit-only rather than settled ROI, promotion readiness, live profitability, or real-money evidence.\n3. `DAILY_ARTIFACT_GUIDE.md` for quiet-vs-broken triage, saved-live refresh scope, and the day-to-day repo map.\n4. `out/paper_trade_settlement_audit.md` / `.json` for ledger-readiness and ROI-complete coverage routing only, not profitability proof.\n5. `OPS_HISTORY.md` for rolling quiet-day versus issue-day context before over-reading one run folder.",
            "operator_reading_order_present",
            "the suggested live-operator reading order now starts with the matched right-now text/markdown/JSON bundle, then routes to the runbook with the OP-anchor provenance/readable-boundary route and audit-only fingerprint / boundary-text boundary, daily guide, settlement audit, and rolling ops history without treating audit or refresh outputs as profitability proof",
        )
    )
    checks.append(
        require(
            current_snippets["bridge_context"] in text
            and current_snippets["bridge_row"] in text,
            "current_evidence_counts_match_bridge_json",
            "the main status doc current-evidence bridge paragraph and file-map row now derive current paper counts, gate progress, rule mix, and open-settlement wording from current_evidence_summary.json",
        )
    )
    if current_context["open_rows"] == 0:
        checks.append(
            require_not_contains(
                text,
                "The bridge-published open settlement identity is `none`",
                "closed_queue_does_not_render_none_as_open_identity",
                "the main status doc must not render open_settlement_summary=none as a current open-row identity when the source bridge has zero open primary settlement rows",
            )
        )
    checks.append(
        require(
            "Use the bridge's combined current-paper read route: `operator_status_context`, `source_freshness` / `requires_refresh_before_right_now_use`, and `operator_read_gate` / `requires_refresh_before_evidence_read` together" in text
            and "right-now card is a wrapper-refresh or missing scan-output issue" in text
            and "refresh `./run_daily_portfolio_observation.sh` before treating the best-action card as today's operator instruction or evidence" in text
            and "operator-context, freshness, and read-gate fields are source-readiness metadata, not performance proof" in text
            and current_context["bridge_read_scope"] in text
            and "source-freshness checks that compare right-now as-of date to bridge reference date" in text,
            "current_evidence_combined_operator_read_route_present",
            "the main status doc now tells readers to use the current-evidence bridge's operator-status context, source-freshness fields, and operator_read_gate together before treating the best-action card as today's operator instruction or evidence, without treating wrapper-refresh, freshness routing, or read-gate routing as performance proof",
        )
    )
    checks.append(
        require(
            "`current_evidence_summary.json.operator_read_gate`" in text
            and current_context["operator_read_gate_read"] in text
            and f"Gate status `{current_context['operator_read_gate_gate_status']}`" in text
            and f"valid use `{current_context['operator_read_gate_valid_use']}`" in text
            and "`operator_read_gate` instruction/evidence-read routing" in text
            and "not no-target evidence, clean-empty evidence, bet readiness, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in text
            and isinstance(current_context["operator_read_gate_requires_refresh_before_evidence_read"], bool)
            and isinstance(current_context["operator_read_gate_recommended_command"], str)
            and bool(current_context["operator_read_gate_recommended_command"])
            and current_context["operator_read_gate_no_target_evidence"] is False
            and current_context["operator_read_gate_clean_empty_evidence"] is False
            and current_context["operator_read_gate_bet_readiness_evidence"] is False
            and current_context["operator_read_gate_settled_roi_evidence"] is False
            and current_context["operator_read_gate_not_live_profitability_evidence"] is True
            and current_context["operator_read_gate_not_real_money_evidence"] is True,
            "current_evidence_operator_read_gate_route_present",
            "the main status doc now routes stale or API-failure top-card reads through current_evidence_summary.json operator_read_gate before instruction/evidence use, while keeping that read gate out of no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, and real-money evidence",
        )
    )
    checks.append(
        require(
            current_context["rebuild_order_read"] in text
            and "`rebuild_validation_contract`" in current_snippets["bridge_row"]
            and "source-published `rebuild_validation_contract` order (`python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`) as provenance/rebuild metadata only" in text
            and current_context["rebuild_order_commands"] == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and current_context["rebuild_requires_settlement_audit_refresh"] is True
            and current_context["rebuild_requires_source_consistency"] is True
            and current_context["rebuild_requires_source_freshness"] is True
            and current_context["rebuild_order_is_provenance_metadata_only"] is True
            and current_context["rebuild_not_settled_roi_or_real_money_evidence"] is True,
            "current_evidence_rebuild_order_route_present",
            "the main status doc now consumes current_evidence_summary.json rebuild_validation_contract so cold-start readers see the settlement-audit -> current-bridge -> current-bridge-validator order before quoting current bridge totals after source-byte changes, while keeping that order as provenance/rebuild metadata only",
        )
    )
    checks.append(
        require(
            COPIED_CURRENT_FANOUT_TEXT in text
            and "copied-current-paper fanout first" in text
            and "validate_frozen_portfolio_eval_caution.py" in text
            and "validate_ab_downstream_comparison.py" in text
            and "validate_compare_main_approaches.py" in text
            and "validate_op_anchor_method_comparison.py" in text
            and "validate_op_family_decision.py" in text
            and "validate_cross_family_decision.py" in text
            and "validate_method_family_decision_card.py" in text
            and "validate_portfolio_decision_card.py" in text
            and "validate_compare_recommender_scope_paths.py" in text
            and "validate_scorecard_ranking_contract_audit.py" in text
            and "validate_frozen_evidence_chain.py --reuse-existing-child-json" in text
            and "validate_report_surfaces.py --reuse-existing-child-json" in text
            and "validate_project_surfaces.py --reuse-existing-child-json" in text
            and "copied-current-paper snapshot drift prevention only, not evidence movement" in text,
            "current_bridge_copied_current_fanout_documented",
            "the main status doc now says a clean settlement-audit -> current-bridge -> bridge-validator rebuild is not enough before report-facing comparison quotes; it pins the copied-current-paper fanout and keeps that fanout as drift prevention only rather than evidence movement",
        )
    )
    checks.append(
        require_contains(
            text,
            '1. `out/status_validation/project_surfaces/project_surfaces_validation.md` for the top-level cross-layer read\n2. `out/status_validation/frozen_evidence_chain/frozen_evidence_chain_validation.md` when the question is research posture\n3. `out/status_validation/frozen_portfolio_eval_caution/frozen_portfolio_eval_caution_validation.md` when the question is whether `FROZEN_PORTFOLIO_EVAL.md` still labels historical replay P&L as frozen evaluation rather than live paper-trade, real-money, or live-profitability evidence\n4. `out/status_validation/compare_main_approaches/compare_main_approaches_validation.md` when the question is the one-screen main comparison, matched CSV/markdown/JSON bundle, evidence-class triage, method-family comparison, machine-readable evidence boundary, machine-readable `decision_change_gate_minimums`, or evidence-scope decision-change gates\n5. `out/status_validation/paper_trade_operator_suite/paper_trade_operator_suite_validation.md` when the question is live paper-trade behavior\n6. `out/status_validation/paper_trade_now/paper_trade_now_validation.md` when the question is whether the single top-card operator action, text/markdown/JSON parity, or helper-failure JSON placeholder still points at the right next command and lane\n7. `out/status_validation/current_hierarchy_language/current_hierarchy_language_validation.md` when the question is whether `OP_DURABLE_K7` / `CD_CORE_K8` / `OP_REFINED_K7` wording and `live_hierarchy` structured keys still preserve anchor / paper-basket companion / same-family shadow-watch roles without treating legacy `primary_shadow` compatibility as promotion evidence\n8. `out/status_validation/live_scan_targeting_and_limit_status/live_scan_targeting_and_limit_status_validation.md` for scanner target prefilter / `--max-races` limited-coverage status routing, then `out/status_validation/paper_trade_pipeline/paper_trade_pipeline_validation.md`, `out/status_validation/paper_trade_recommender/paper_trade_recommender_validation.md`, `out/status_validation/ev_ticket_engine/ev_ticket_engine_validation.md`, and `out/status_validation/paper_trade_logger/paper_trade_logger_validation.md` when the question is upstream scan -> recommend -> size -> log behavior rather than downstream operator phrasing\n9. `out/status_validation/report_surfaces/report_surfaces_validation.md` when the question is shareable wording or presentation drift, including whether the narrative report sweep preserved the README-inherited wrapper-leaf source-of-truth note instead of flattening it away and kept its machine-readable evidence boundary separate from settled ROI, live profitability, promotion readiness, and real-money evidence\n10. `out/status_validation/working_status_report/working_status_report_validation.md` when the question is whether the dated live/demo-vs-production note still keeps the report-time evidence anchor and mutable `latest_demo_run.json` alias straight\n11. `out/status_validation/validation_quickstart/validation_quickstart_validation.md` when the question is whether the validation runbook still points to the right validators, the broader operator-suite route, direct source-layer routes, parent-rollup reuse shortcut guardrails, documented output paths, the dated-report / legacy-alias policy, and its machine-readable navigation evidence boundary\n12. `out/status_validation/daily_artifact_guide/daily_artifact_guide_validation.md` when the question is what to read day to day or whether the daily repo-map guidance drifted\n13. `out/status_validation/paper_trade_usage/paper_trade_usage_validation.md` when the question is whether the hands-on operator runbook still reflects the current OP-anchor-first start path, primary OP/CD paper-basket companion inside the primary basket, separate Phase 8 shadow/watch routine, OP-anchor provenance/readable-boundary route, audit-only fingerprint and boundary-text boundary, and direct source-layer validator ladder\n14. `out/status_validation/cole_status_and_plan/cole_status_and_plan_validation.md` when the question is whether this main status document and repo map still point at the right frozen story, file paths, and machine-readable status-map evidence boundary\n15. `out/status_validation/decision_cards_suite/decision_cards_suite_validation.md` only when you need the direct card-level wording and ordering details',
            "validation_reading_order_present",
            "the validation reading order now includes the direct compare-main evidence-scope report, the direct live-scan targeting / max-races limited-coverage route plus source-layer paper-trade chain, parent-rollup reuse shortcut guardrails, output-path coverage, and the main status-doc evidence boundary alongside the working-status validator, top-card validator, daily guide, paper-trade runbook, and this main status-doc validator",
        )
    )
    checks.append(
        require_contains(
            text,
            "For the full-data XGBoost retrain artifact specifically, use `out/status_validation/full_data_retrain_artifacts/full_data_retrain_artifacts_validation.md`; its green read is model-fit reproducibility metadata only, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            "full_data_retrain_validation_route_present",
            "the validation reading order now exposes the dedicated full-data retrain validation artifact while keeping its green read out of the paper-trade / promotion / live-profitability / bankroll / real-money lane",
        )
    )
    checks.append(
        require_contains(
            text,
            "Parent-rollup shortcut: if the underlying child validator outputs are already fresh and the edit only touched a parent rollup or top-level wording, the smaller honest reruns are `python3 validate_decision_cards_suite.py --reuse-existing-child-json`, `python3 validate_frozen_evidence_chain.py --reuse-existing-child-json`, `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json`, `python3 validate_report_surfaces.py --reuse-existing-child-json`, or `python3 validate_project_surfaces.py --reuse-existing-child-json`.",
            "validation_reuse_shortcut_present",
            "the main status doc now keeps the parent-rollup reuse shortcut visible for parent-only or top-level wording edits, with the guardrail that child validator outputs already need to be fresh",
        )
    )
    checks.append(
        require_contains(
            text,
            "| `validate_cole_status_and_plan.py` | Rebuild/consistency check for the main status doc, including the frozen headline posture, the validation reading order, the main repo-map paths, and a machine-readable evidence boundary for status/map alignment only | Run when changing `COLE_STATUS_AND_PLAN.md` or the main status-doc / repo-map guidance |",
            "self_validator_row_present",
            "the file map now includes a direct validator row for the main status document itself and says its machine-readable evidence boundary is status/map alignment only",
        )
    )
    checks.append(
        require_contains(
            text,
            "| `validate_paper_trade_now.py` | Fixture validation for the top-level right-now launcher, including saved and shell-facing JSON, text, and markdown output rebuilds, `PAPER_TRADE_NOW.json` parity with `paper_trade_now.py --format json` or the explicit full-helper-failure placeholder, the live hierarchy, preserved primary/shadow recent-run context plus lifted lane why-now lines, pipeline-recorded scanner-status refresh actions, the stale-card inherited-snapshot honesty note, and direct primary/shadow pipeline/scanner status-sidecar pointers in the direct `paper_trade_now_validation.md` report | Run when changing `paper_trade_now.py`, `PAPER_TRADE_NOW.md` / `.txt` / `.json`, or the operator-priority card |",
            "paper_trade_now_validator_row_present",
            "the file map now includes the direct right-now validator close to the top-card entry itself",
        )
    )
    checks.append(
        require_contains(
            text,
            "| `validate_current_hierarchy_language.py` | Current hierarchy wording / structured-key compatibility check across high-traffic surfaces and selected JSON/CSV fields; keeps `OP_DURABLE_K7` as anchor, `CD_CORE_K8` as the primary OP/CD paper-basket companion with legacy `primary_shadow` compatibility only, and `OP_REFINED_K7` as the same-family shadow/watch challenger; evidence boundary is wording / structured-key compatibility metadata only, not settled ROI, live profitability, promotion readiness, anchor-change, companion-change, or real-money evidence | Run when changing live hierarchy wording, `primary_companion` / `primary_shadow` keys, or paper companion versus Phase 8 shadow/watch phrasing |",
            "current_hierarchy_validator_row_present",
            "the file map now includes the direct current-hierarchy wording / structured-key compatibility validator and its evidence boundary",
        )
    )
    checks.append(
        require_contains(
            text,
            "| `VALIDATION_QUICKSTART.md` | Short guide for which validator to run after which kind of change, including the broader operator-suite route, the direct source-layer paper-trade chain routes, the live-scan targeting / max-races limited-coverage route, the parent-rollup reuse shortcut guardrails, documented output paths, and the dated-report / legacy-alias policy | Read when the validation stack feels too nested |",
            "quickstart_row_present",
            "the file map now says plainly that the quickstart includes the broader operator-suite route, the direct source-layer paper-trade chain routes, the live-scan targeting / max-races limited-coverage route, the parent-rollup reuse shortcut guardrails, documented output paths, dated-report / legacy-alias policy, and machine-readable navigation evidence boundary",
        )
    )
    checks.append(
        require_contains(
            text,
            "| `validate_validation_quickstart.py` | Rebuild/consistency check for the quickstart runbook, including the current suite hierarchy, the broader operator-suite route, source-layer routes, live-scan targeting / limited-coverage route, parent-rollup reuse shortcut guardrails, documented output paths, dated-report / legacy-alias policy, and machine-readable evidence boundary for navigation/read-order reproducibility only | Run when changing `VALIDATION_QUICKSTART.md` or the documented validation ladder |",
            "quickstart_validator_row_present",
            "the file map now says plainly that the quickstart validator protects the broader operator-suite route, source-layer routes, live-scan targeting / limited-coverage route, parent-rollup reuse shortcut guardrails, documented output paths, report-alias policy, and navigation evidence boundary too",
        )
    )
    checks.append(
        require_contains(
            text,
            "| `validate_daily_artifact_guide.py` | Rebuild/consistency check for the daily-use guide, including the scorecard-first research path, the matched PAPER_TRADE_NOW text/markdown/JSON operator path, the latest-run pointers, the issue-day sidecar-triage route, and the validation-ladder routing | Run when changing `DAILY_ARTIFACT_GUIDE.md` or the day-to-day repo-map guidance |",
            "daily_guide_validator_row_present",
            "the file map now includes the direct daily-artifact-guide validator instead of only naming the guide itself",
        )
    )
    checks.append(
        require_contains(
            text,
            "| `PAPER_TRADE_USAGE.md` | Hands-on operator runbook for the live paper-trade stack, including the OP-anchor-first start path, the primary OP/CD paper-basket companion inside the primary basket, the separate Phase 8 shadow/watch routine, the OP-anchor markdown/JSON provenance plus readable-boundary route, and the audit-only fingerprint / boundary-text boundary | Read when you want the operational command path, provenance route, readable boundary-text route, and validator map in one place |\n| `validate_paper_trade_usage.py` | Consistency check for the paper-trade operations runbook, including the OP-anchor start command, the primary OP/CD paper-basket companion inside the primary basket, the separate Phase 8 shadow/watch routine, OP-anchor provenance/readable-boundary route, audit-only fingerprint / boundary-text boundary, and the full operator-validator inventory | Run when changing `PAPER_TRADE_USAGE.md` or the operator runbook guidance |",
            "paper_trade_usage_row_present",
            "the file map now pins the paper-trade usage runbook plus direct validator as the operational command path, OP-anchor provenance/readable-boundary route, and audit-only fingerprint / boundary-text bridge",
        )
    )
    checks.append(
        require_contains(
            text,
            "| `validate_project_surfaces.py` | One-command sweep across the frozen evidence chain, the operator-facing paper-trade suite, the narrative report-surface suite, the direct current-hierarchy wording guardrail, and the repo-navigation, main status-doc, plus operator-runbook surfaces, with child validation JSON fingerprints and a machine-readable evidence boundary published as top-level reproducibility metadata only | Run after broader edits when you want one quick green/red read across research, live-ops, hierarchy wording, shareable report surfaces, and rerun/read guidance |",
            "project_surfaces_scope_row_present",
            "the file map now says plainly that the top-level project sweep covers the current-hierarchy wording guardrail and the main status doc too",
        )
    )
    checks.append(
        require_contains(
            text,
            "| `validate_working_status_report.py` | Rebuild/consistency check for the dated working-status note, including the OP/CD production-basket distinction, the separate demo lane, the report-time evidence anchor, and the mutable `latest_demo_run.json` alias | Run when changing `WORKING_STATUS_REPORT_2026-04-15.md` or the dated live/demo-vs-production framing |",
            "working_status_validator_row_present",
            "the file map now includes a direct validator row for the dated working-status note and its stable-vs-mutable evidence framing",
        )
    )
    checks.append(
        require_paths_exist(
            [
                BASE / "COLE_STATUS_AND_PLAN.md",
                BASE / "validate_cole_status_and_plan.py",
                BASE / "DAILY_ARTIFACT_GUIDE.md",
                BASE / "validate_daily_artifact_guide.py",
                BASE / "PAPER_TRADE_NOW.md",
                BASE / "PAPER_TRADE_NOW.txt",
                BASE / "PAPER_TRADE_NOW.json",
                BASE / "OPS_HISTORY.md",
                BASE / "validate_paper_trade_now.py",
                BASE / "validate_current_hierarchy_language.py",
                BASE / "forward_evidence_scorecard.py",
                BASE / "forward_evidence_scorecard.txt",
                BASE / "forward_evidence_scorecard.csv",
                BASE / "forward_evidence_scorecard.json",
                BASE / "validate_forward_evidence_scorecard.py",
                BASE / "SCORECARD_RANKING_CONTRACT_AUDIT.md",
                BASE / "scorecard_ranking_contract_audit.json",
                BASE / "validate_scorecard_ranking_contract_audit.py",
                BASE / "CURRENT_EVIDENCE_SUMMARY.md",
                BASE / "current_evidence_summary.py",
                BASE / "current_evidence_summary.json",
                BASE / "validate_current_evidence_summary.py",
                BASE / "PAPER_TRADE_USAGE.md",
                BASE / "validate_paper_trade_usage.py",
                BASE / "WORKING_STATUS_REPORT_2026-04-15.md",
                BASE / "validate_working_status_report.py",
                BASE / "VALIDATION_QUICKSTART.md",
                BASE / "validate_validation_quickstart.py",
                BASE / "validate_project_surfaces.py",
                BASE / "OP_FAMILY_DECISION.md",
                BASE / "validate_op_family_decision.py",
                BASE / "CROSS_FAMILY_DECISION.md",
                BASE / "validate_cross_family_decision.py",
                BASE / "PORTFOLIO_DECISION_CARD.md",
                BASE / "validate_portfolio_decision_card.py",
                BASE / "METHOD_FAMILY_DECISION.md",
                BASE / "validate_method_family_decision_card.py",
                BASE / "validate_decision_cards_suite.py",
            ],
            "named_main_repo_artifacts_exist",
            "the main status-doc file map still points at real cold-start and decision artifacts on disk",
        )
    )
    checks.append(
        require_paths_exist(
            [
                BASE / "out" / "status_validation" / "project_surfaces" / "project_surfaces_validation.md",
                BASE / "out" / "status_validation" / "frozen_evidence_chain" / "frozen_evidence_chain_validation.md",
                BASE / "out" / "status_validation" / "compare_main_approaches" / "compare_main_approaches_validation.md",
                BASE / "out" / "status_validation" / "paper_trade_operator_suite" / "paper_trade_operator_suite_validation.md",
                BASE / "out" / "status_validation" / "paper_trade_now" / "paper_trade_now_validation.md",
                BASE / "out" / "status_validation" / "current_hierarchy_language" / "current_hierarchy_language_validation.md",
                BASE / "out" / "status_validation" / "paper_trade_pipeline" / "paper_trade_pipeline_validation.md",
                BASE / "out" / "status_validation" / "live_scan_targeting_and_limit_status" / "live_scan_targeting_and_limit_status_validation.md",
                BASE / "out" / "status_validation" / "paper_trade_recommender" / "paper_trade_recommender_validation.md",
                BASE / "out" / "status_validation" / "ev_ticket_engine" / "ev_ticket_engine_validation.md",
                BASE / "out" / "status_validation" / "paper_trade_logger" / "paper_trade_logger_validation.md",
                BASE / "out" / "status_validation" / "report_surfaces" / "report_surfaces_validation.md",
                BASE / "out" / "status_validation" / "working_status_report" / "working_status_report_validation.md",
                BASE / "out" / "status_validation" / "validation_quickstart" / "validation_quickstart_validation.md",
                BASE / "out" / "status_validation" / "full_data_retrain_artifacts" / "full_data_retrain_artifacts_validation.md",
                BASE / "out" / "status_validation" / "daily_artifact_guide" / "daily_artifact_guide_validation.md",
                BASE / "out" / "status_validation" / "paper_trade_usage" / "paper_trade_usage_validation.md",
                BASE / "out" / "status_validation" / "cole_status_and_plan" / "cole_status_and_plan_validation.md",
                BASE / "out" / "status_validation" / "decision_cards_suite" / "decision_cards_suite_validation.md",
            ],
            "named_validation_outputs_exist",
            "the validation outputs named directly in the status doc currently exist, so the main repo map is not routing readers to stale reports",
        )
    )
    checks.append(
        require(
            all(
                needle in text
                for needle in [
                    "| `forward_evidence_scorecard.py` | Rule ranking by forward evidence; writes matched text, CSV, and JSON sidecar surfaces with frozen source-scope / non-live-evidence metadata, machine-readable evidence boundary, machine-readable decision-gate minimums, plus bootstrap-CI source notes and report fingerprints | Run it |",
                    "| `forward_evidence_scorecard.txt` / `.csv` / `.json` | Generated scorecard surfaces: human read, tabular rows with CSV-visible bootstrap-CI source columns, and machine-readable metadata + ranked rows from the same frozen inputs, including structured `evidence_boundary`, legacy `evidence_boundary_text`, `decision_gate_minimums` for `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100` settled-observation gates, plus per-rule bootstrap-CI source notes and `PHASE7_REPORT.md` / `PHASE8_REPORT.md` report fingerprints | Read the text first; use CSV/JSON for parity and automation checks |",
                    "| `validate_forward_evidence_scorecard.py` | Rebuild/consistency check for the scorecard CSV, text, and JSON sidecar surfaces, including the current anchor / paper / watch / dormant read, source-scope / non-live-evidence boundary, CSV bootstrap-CI source-note columns, machine-readable JSON evidence boundary, machine-readable decision-gate minimums, and bootstrap-CI source-note / report-fingerprint provenance | Run when changing `forward_evidence_scorecard.py`, report-source fingerprints, bootstrap-CI source notes, CSV source-note columns, evidence-boundary metadata, gate-minimum metadata, or the scorecard ordering / wording |",
                    "| `COLE_PRESENTATION_OUTLINE.md` | Shareable deck-outline surface for Cole's presentation story, kept aligned with the frozen anchor / paper / benchmark posture | Read when preparing slides or checking concise presentation wording |",
                    "| `validate_cole_presentation_outline.py` | Rebuild/consistency check for the presentation outline, including the frozen anchor, paper baseline, selector benchmark read, Phase 8 shadow-only stance, and method-family roles | Run when changing `COLE_PRESENTATION_OUTLINE.md` or deck-facing posture wording |",
                    "| `validate_report_surfaces.py` | One-command sweep across README, the long-form report, the working-status report, the presentation outline, and the shareable HTML report so the main human-facing story stays aligned, including the README-inherited wrapper-leaf source-of-truth note that the narrative rollup should preserve rather than flatten away plus a machine-readable evidence boundary that keeps narrative validation separate from settled ROI, live profitability, promotion readiness, and real-money evidence | Run after report/deck wording edits when you want one quick green/red read across the narrative surfaces |",
                    "| `WORKING_STATUS_REPORT_2026-04-15.md` | Dated live/demo-vs-production status note, with the 2026-04-15 Keeneland demo artifacts as the stable evidence anchor and `latest_demo_run.json` treated as a mutable convenience alias | Read when you need the corrected operational state for production basket vs demo lane |",
                    "| `validate_working_status_report.py` | Rebuild/consistency check for the dated working-status note, including the OP/CD production-basket distinction, the separate demo lane, the report-time evidence anchor, and the mutable `latest_demo_run.json` alias | Run when changing `WORKING_STATUS_REPORT_2026-04-15.md` or the dated live/demo-vs-production framing |",
                    "| `AB_DOWNSTREAM_COMPARISON.md` | Report-safe downstream A/B summary for the baseline payout model versus the enriched horse-history XGBoost path, with an explicit guardrail that modest prediction gains still do not make that enriched path a paper-betting case | Read when explaining why the enriched horse-history XGBoost path remains research-only even after matched downstream prediction improvements |",
                    "| `validate_ab_downstream_comparison.py` | Source-aware consistency check for `ab_downstream_comparison.py`, including saved JSON/markdown surfaces, the winning-combos-only limitation, the current prediction-metric improvement read, and the still-not-better conservative EV pass counts; real CLI stdout / custom-output parity checks run when raw rebuild inputs are present, and otherwise publish explicit `SKIP` rows naming the missing inputs (`14years_major_tracks.csv`, `horse_features_major_tracks.csv` in this workspace) | Run when changing `ab_downstream_comparison.py`, the matched A/B model artifacts, raw A/B rebuild inputs, or the XGBoost downstream comparison layer |",
                    "| `FULL_DATA_RETRAIN_ARTIFACTS.md` | Full-data XGBoost retrain artifact for model-fit reproducibility only: large RMSE / MAE improvements and exact retrain/prediction commands are diagnostics, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence | Read only when checking the full-data retrain artifact or diagnostic commands; deployment interpretation still belongs to the selective OP/CD paper path and comparison artifacts |",
                    "| `validate_full_data_retrain_artifacts.py` | Direct validator for the full-data retrain artifact, including the evidence boundary, headline-metric caveat, exact retrain command, and diagnostic-only prediction command | Run when changing `FULL_DATA_RETRAIN_ARTIFACTS.md`, full-data retrain metrics, retrain/prediction commands, or XGBoost model-fit boundary wording |",
                    "| `OP_ANCHOR_METHOD_COMPARISON.md` / `op_anchor_method_comparison.json` | Compact cold-read comparison placing `OP_DURABLE_K7` beside Harville and the current odds-only XGBoost path, while making unlike evidence classes explicit, showing why OP still leads the paper-candidate lane, keeping the broader selective-family secondary line as replay-only context rather than extra train-only proof, and carrying exact source-byte provenance plus readable JSON `evidence_boundary_text` for the scorecard / compare-main / method-family / cross-family / downstream A/B inputs | Read when Cole wants one OP-centered answer for why the selective anchor still outranks the broad benchmark while the current odds-only XGBoost path stays parked unless its evidence class changes materially; treat the JSON boundary text/source fingerprints as reproducibility metadata only, not settled ROI, promotion readiness, live profitability, or real-money evidence |",
                    "| `validate_op_anchor_method_comparison.py` | Rebuild/consistency check for the OP-centered comparison artifact, including saved JSON/markdown surfaces, readable `evidence_boundary_text`, source provenance, row-identical source-byte drift coverage, real CLI stdout, the frozen OP anchor numbers, the explicit evidence-class labels, the Harville benchmark read, the parked current odds-only XGBoost reopening bar, the current OP-refined challenger context, and the replay-only selective-family secondary caution | Run when changing `op_anchor_method_comparison.py`, the OP anchor comparison layer, its readable boundary-text / source-fingerprint contract, or the method-family guardrail framing around `OP_DURABLE_K7` |",
                    "| `CROSS_FAMILY_DECISION.md` | Compact anchor / paper / watch card for OP_DURABLE_K7 vs CD_CORE_K8 vs OP_REFINED_K7, plus the current-paper snapshot caveat that keeps CD-only settled context and source-published settlement-queue state out of OP-anchor proof or cross-family promotion evidence | Read after the OP card |",
                    "| `validate_cross_family_decision.py` | Rebuild/consistency check for the cross-family shortlist, including saved CSV/markdown surfaces, real CLI stdout, the current anchor / paper / watch ordering, current-paper snapshot caveat, and no cross-family promotion-evidence boundary | Run when changing `cross_family_decision_card.py`, the active-rule ordering logic, or the current-paper snapshot caveat |",
                    "| `compare_recommender_scope_paths.py` | Report-safe side-by-side artifact for the default selective recommender path versus the explicit `--allow-all-combos` override on the same OP-anchor stub races, with an explicit guardrail that widened scope is a research counterfactual, not a paper-promotion case, plus modeled stub-EV lift / off-scope ticket-share splits that are not observed P&L | Read when explaining why the paper-trade recommender keeps the selective Phase 7 combo universe by default |",
                    "| `validate_compare_recommender_scope_paths.py` | Rebuild/consistency check for the selective-vs-widened recommender scope artifact, including saved JSON/markdown surfaces, real CLI stdout, the current mixed-universe and off-universe-only guardrail scenarios, and the not-observed-P&L modeled EV lift source | Run when changing `compare_recommender_scope_paths.py`, recommender combo-scope guardrails, or the live-vs-research scope comparison layer |",
                    "| `compare_main_approaches.md` / `.csv` / `.json` | Matched main-comparison bundle for the current OP/CD paper core, `OP_REFINED_K7` shadow-only challenger, Harville benchmark-only lane, parked current odds-only XGBoost lane, BEL-not-BAQ caution, source provenance, machine-readable evidence_boundary metadata, machine-readable `decision_change_gate_minimums` naming `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100`, and evidence-scope decision-change gates; the JSON sidecar carries parity/provenance plus evidence_boundary and decision_change_gate_minimums metadata, not new live or promotion evidence | Read the markdown when Cole needs the broad method/portfolio comparison; use CSV/JSON for automation/parity without treating clean scans, open signals, replay rows, hashes, or odds-only reruns as promotion evidence |",
                    "| `validate_compare_main_approaches.py` | Rebuild/consistency check for the main comparison harness against frozen holdout and walk-forward sources, including saved CSV/markdown/JSON sidecar surfaces, real CLI stdout, the machine-readable evidence_boundary contract, the machine-readable `decision_change_gate_minimums` contract, and the current evidence-scope deployment-posture guardrails | Run when changing `compare_main_approaches.py` or the portfolio/method comparison layer |",
                    "| `validate_frozen_evidence_chain.py` | One-command sweep across the forward-evidence scorecard, main comparison harness, direct frozen-portfolio replay caution / metadata-sidecar check, frozen stack, decision-card suite, and the narrow OP-anchor / downstream A/B / selective-scope comparison validators for the full report-facing evidence chain, with child validation JSON fingerprints plus a machine-readable evidence boundary published as reproducibility metadata only | Run after structural/report-facing edits when you want one quick green/red read across the whole evidence chain |",
                    "| `FROZEN_PORTFOLIO_EVAL.md` / `frozen_portfolio_eval_metadata.json` | Frozen 2024-2025 portfolio replay with the current evidence boundary plus exact source-byte fingerprints; holdout P&L is historical replay and hashes are reproducibility metadata, not a live paper-trade ledger or real-money evidence | Must read |",
                    "| `validate_frozen_portfolio_eval_caution.py` | Direct check that the frozen portfolio report and metadata sidecar keep the historical-replay / no-live-paper / no-real-money boundary, Phase 7-over-Phase 8 holdout read, `OP_DURABLE_K7` anchor, `CD_CORE_K8` paper companion, Phase 8 shadow/watch posture, exact source fingerprints, and `BAQ`-is-not-`BEL` caution | Run when changing `FROZEN_PORTFOLIO_EVAL.md`, `frozen_portfolio_eval_metadata.json`, `evaluate_frozen_portfolios.py`, or frozen replay wording |",
                ]
            ),
            "report_and_guardrail_rows_present",
            "the main status-doc file map still includes the report-facing comparison artifacts, their direct validators, and the broader narrative and frozen-evidence sweeps",
        )
    )
    checks.append(
        require_contains(
            text,
            "| `validate_report_surfaces.py` | One-command sweep across README, the long-form report, the working-status report, the presentation outline, and the shareable HTML report so the main human-facing story stays aligned, including the README-inherited wrapper-leaf source-of-truth note that the narrative rollup should preserve rather than flatten away plus a machine-readable evidence boundary that keeps narrative validation separate from settled ROI, live profitability, promotion readiness, and real-money evidence | Run after report/deck wording edits when you want one quick green/red read across the narrative surfaces |",
            "report_surfaces_row_preserves_wrapper_leaf_note",
            "the main status doc now says plainly that the report-surfaces sweep must preserve the README-inherited wrapper-leaf source-of-truth note instead of flattening it away while keeping narrative validation separate from settled ROI, live profitability, promotion readiness, and real-money evidence",
        )
    )
    checks.append(
        require_paths_exist(
            [
                BASE / "COLE_PRESENTATION_OUTLINE.md",
                BASE / "validate_cole_presentation_outline.py",
                BASE / "WORKING_STATUS_REPORT_2026-04-15.md",
                BASE / "validate_working_status_report.py",
                BASE / "validate_report_surfaces.py",
                BASE / "compare_main_approaches.py",
                BASE / "compare_main_approaches.csv",
                BASE / "compare_main_approaches.md",
                BASE / "compare_main_approaches.json",
                BASE / "validate_compare_main_approaches.py",
                BASE / "AB_DOWNSTREAM_COMPARISON.md",
                BASE / "validate_ab_downstream_comparison.py",
                BASE / "FULL_DATA_RETRAIN_ARTIFACTS.md",
                BASE / "validate_full_data_retrain_artifacts.py",
                BASE / "OP_ANCHOR_METHOD_COMPARISON.md",
                BASE / "validate_op_anchor_method_comparison.py",
                BASE / "compare_recommender_scope_paths.py",
                BASE / "validate_compare_recommender_scope_paths.py",
                BASE / "validate_frozen_decision_stack.py",
                BASE / "validate_frozen_evidence_chain.py",
                BASE / "validate_frozen_portfolio_eval_caution.py",
                BASE / "WALK_FORWARD_VALIDATION.md",
                BASE / "FROZEN_PORTFOLIO_EVAL.md",
                BASE / "frozen_portfolio_eval_metadata.json",
                BASE / "phase7_live_rules.json",
                BASE / "phase7_current_paper_rules.json",
                BASE / "phase8_shadow_rules.json",
            ],
            "named_report_and_rule_artifacts_exist",
            "the report-facing comparison artifacts including the main-comparison CSV/markdown/JSON bundle, frozen-evidence validators, and current rule-basket files named in the main status doc all exist on disk",
        )
    )
    checks.append(
        require(
            all(
                needle in text
                for needle in [
                    "| `OPS_HISTORY.md` | Rolling quiet-day vs issue-day context across recent runs, so daily behavior is not judged from one folder in isolation | Read when a quiet stretch might be operational rather than market-driven |",
                    "| `PAPER_TRADE_NOW.md` | Single best human operator action for the latest run, paired with `PAPER_TRADE_NOW.txt` and the matched machine-readable `PAPER_TRADE_NOW.json` sibling rather than separate evidence, with preserved primary/shadow recent-run context plus lifted lane why-now lines behind it and direct primary/shadow pipeline/scanner status-sidecar pointers for issue-day debugging. When the card is stale, those downstream lane details are inherited snapshot context rather than current-day state. | Read first on a live paper-trade day when you just want the next move, and keep the JSON sibling source-matched |",
                    "| `validate_paper_trade_pipeline.py` | Fixture validation for the pipeline orchestrator, including skip-scan empty reuse, bets-ready reuse, scanner-failure fallback, empty/unreadable scanner-status sidecars, partial-cache activity, and signals-logged-no-bet status classification | Run when changing `paper_trade_pipeline.py` or the machine-readable pipeline status contract |",
                    "| `validate_live_scan_targeting_and_limit_status.py` | Direct scanner / pipeline / status-summary / ops-history guardrail for live-scan target prefiltering and `--max-races` limited coverage; proves capped scans spend detail attempts on OP/CD rule-candidate races, do not alias BAQ as BEL, and classify capped no-hit reads as operationally limited coverage with target-candidate/unattempted counts rather than clean empty forward observations | Run when changing live scanner targeting, `--max-races` coverage metadata, or limited-coverage status/ops routing; treat the pass as synthetic operational metadata only |",
                    "| `validate_paper_trade_recommender.py` | Fixture validation for the recommender, including empty-scan summaries, default Phase 7 combo filtering, off-universe honest NO BET behavior, explicit `--allow-all-combos` widening, and malformed-prediction ERROR rows | Run when changing `paper_trade_recommender.py` or the combo-filter / recommendation-summary contract |",
                    "| `paper_trade_logger.py` | Source-layer ledger writer that appends persistent signal and recommendation rows while deduping prior `signal_key` values | Use it through the pipeline unless you are debugging ledger append behavior directly |",
                    "| `validate_paper_trade_logger.py` | Fixture validation for the persistent signal and recommendation ledgers, including empty-run header creation, serialized payload appends, dedup behavior, malformed-state fallback, and blank recommendation-key skips | Run when changing `paper_trade_logger.py` or the ledger append / dedup contract |",
                    "| `paper_trade_now.py` | Collapses the latest daily run into one best operator action plus a matched text/markdown/JSON top-card bundle, preserved primary/shadow recent-run context, lifted lane why-now lines, and rolling ops context, while marking stale downstream lane details as inherited snapshot context rather than current-day state | Use when you want one honest answer before opening several artifacts |",
                    "| `refresh_live_paper_trade_surfaces.py` | Rebuilds saved per-run operator surfaces, saved `preflight_note` text/JSON, plus top-level `OPS_HISTORY` / matched `PAPER_TRADE_NOW` text/markdown/JSON / `CURRENT_EVIDENCE_SUMMARY` markdown/JSON after source-layer render changes, preserving `current_evidence_summary.json.rebuild_validation_contract` as the settlement-audit -> current-bridge -> bridge-validator route, then rerenders each per-run `daily_summary.txt` against those refreshed top-level surfaces so the routed top-card focus/timing/freshness/ops snapshot, recent-run context, lifted lane why-now lines, and machine-readable JSON sibling stay source-matched without rerunning the full live wrapper, keeps `--latest-only` confined to the newest copied run's preflight, lane, and daily-summary surfaces, keeps `--skip-top-level` confined to leaving `OPS_HISTORY` / matched `PAPER_TRADE_NOW` / `CURRENT_EVIDENCE_SUMMARY` outputs untouched while still rerendering those per-run surfaces against the existing top-level outputs, and supports optional `--as-of-date` freshness pinning with stdout that says whether that pin was actually applied or ignored because top-level outputs were skipped, while keeping the inherited-snapshot honesty note if a rebuilt top card is still stale | Use after helper/render edits when the saved live paper-trade surfaces need a clean refresh |",
                    "| `paper_trade_daily_summary.py` | Builds the combined `daily_summary.txt` quick-jump surface from the current run artifacts, including the routed top-card focus/timing/freshness/ops snapshot, the explicit primary/shadow next-step states plus first-read and broader-review readiness lines, and the visible-but-not-live-promoted shadow review cue | Auto-used by the daily wrapper |",
                    "| `validate_paper_trade_forward_check.py` | Fixture validation for the frozen-baseline forward checker, including no-data, too-early, within-noise, running-cold, running-hot, ROI fallback with explicit actual-vs-expected-cost source counts, malformed `actual_cost` gap wording, no-overpromotion decision-gate wording, and missing-baseline states, with the JSON, text, and markdown outputs pinned against fresh source-layer renders | Run when changing `paper_trade_forward_check.py` or the frozen forward-comparison contract |",
                    "| `validate_paper_trade_lane_monitor.py` | Fixture validation for the compact lane monitor, including open-queue, truncation, no-data, missing-baseline, decision-grade ROI carry-through, and no-overpromotion decision-gate cases, with the JSON, text, and markdown renders pinned against fresh source-layer output | Run when changing `paper_trade_lane_monitor.py` or the compact forward-plus-queue surface |",
                    "| `validate_paper_trade_status_summary.py` | Fixture validation for the one-line base lane summary, including bet-ready, clean-empty, partial-cache, scanner-only alerts, cache-only-miss, missing-scan-output, generic scanner-failure, API-access / HTTP 403 action-recheck route preservation with `refresh_daily_wrapper_before_evidence_read` plus `./run_daily_portfolio_observation.sh` as operator context only, empty/unreadable/invalid-shape scanner sidecars, pipeline-recorded empty/unreadable/invalid-shape scanner-status states when a copied surface lacks the physical scanner sidecar, wrapper-only required-pipeline missing/empty/unreadable/invalid-shape sidecars, recommender-failure, logger-failure, and signals-without-bet across text and JSON paths, plus no-readable-sidecars cases, with saved human-facing recommender/logger failure lines preserving stage, error type, and detail and the saved summaries pinned against fresh source-layer renders | Run when changing `paper_trade_status_summary.py` or the wrapper's base-summary contract before lane enrichment |",
                    "| `validate_paper_trade_daily_summary.py` | Fixture validation for the combined daily summary surface, including the routed top-card focus/timing/freshness/ops snapshot, explicit primary/shadow next-step state lines plus lifted no-overpromotion decision-gate snapshot lines, first-read and broader-review readiness lines, the visible-without-live-promotion shadow review cue, pipeline-recorded scanner-status issue lines, explicit recommender/logger failure context, explicit missing-preflight and missing-lane-summary placeholders, plus a rebuild match on the rendered text | Run when changing the quick-jump / summary layer |",
                    "| `validate_paper_trade_lane_summary.py` | Fixture validation for the expanded per-lane summary surface, including lifted no-overpromotion decision-gate visibility, pipeline-recorded scanner-status base headlines, explicit recommender/logger pipeline-failure context, missing-base and missing-detail placeholders, plus a rebuild match on the rendered text | Run when changing the per-lane summary layer |",
                    "| `validate_paper_trade_next_steps.py` | Fixture validation for the per-lane next-step helper, including settlement-first, refresh-artifacts with distinct missing/empty/unreadable and pipeline-recorded scanner-status states, rerun-live, limited-cache, explicit recommender/logger pipeline-failure recovery, early-observation, collecting-sample, and decision-grade states, plus mixed-state `Latest run context` wording | Run when changing `paper_trade_next_steps.py` or the lane-state to command mapping |",
                    "| `validate_paper_trade_ops_history.py` | Fixture validation for the rolling ops-history surface, including bet-ready, no-target, zero-hit, limited-coverage, hit-found / no-bet, explicit recommender/logger failure, unreadable-calendar, missing/empty/unreadable artifact issue days, and pipeline-recorded scanner-status issue days | Run when changing `paper_trade_ops_history.py` or the day-bucket / takeaway logic |",
                    "| `validate_refresh_live_paper_trade_surfaces.py` | Fixture validation for the saved-live refresh helper, including per-run summary rebuilds, regenerated saved `preflight_note` text/JSON, regenerated top-level `OPS_HISTORY` / matched `PAPER_TRADE_NOW` text/markdown/JSON / `CURRENT_EVIDENCE_SUMMARY` markdown/JSON with JSON parity and `current_evidence_summary.json.rebuild_validation_contract` preserved, preserved rebuilt daily-summary top-card snapshot lines plus routed quick-read integrity, preserved rebuilt top-card recent-run context plus lifted lane why-now lines when current lane artifacts provide them, the stale rebuilt-card inherited-snapshot honesty note, `--latest-only` confined to the newest copied run's preflight, lane, and daily-summary surfaces, `--skip-top-level` leaving top-level outputs untouched while still rebuilding the per-run preflight/lane/daily layer against those existing top-level outputs, and honest `--as-of-date` applied-vs-skipped stdout behavior. Together with `validate_run_daily_portfolio_observation.py`, this is one of the two leaf source-of-truth wrapper reports whose inherited wrapper-guardrail inventory broader operator/project sweeps should preserve rather than flatten. | Run when changing `refresh_live_paper_trade_surfaces.py` or the saved-live rebuild path |",
                    "| `validate_run_daily_portfolio_observation.py` | End-to-end fixture validation for the real daily wrapper, including no-target and active-target cache-miss days, explicit recommender/logger pipeline-error refresh days, active hit-found but no-BET days, settle-first, partial-cache refresh, malformed-preflight, preflight-helper-failure, ops-history-fallback, right-now-helper-failure, forward-check-helper-failure, lane-monitor-helper-failure, and next-steps-helper-failure days, required `PAPER_TRADE_NOW.json` parity or explicit helper-failure placeholder behavior, missing-status placeholder, markdown-mirror fallback, lane-summary fallback, and daily-summary fallback days. Together with `validate_refresh_live_paper_trade_surfaces.py`, this is the other leaf source-of-truth wrapper report whose inherited wrapper-guardrail inventory broader operator/project sweeps should preserve rather than flatten. | Run when changing `run_daily_portfolio_observation.sh` or the way the wrapper stitches helper artifacts together |",
                    "| `validate_paper_trade_operator_suite.py` | One-command sweep across the main operator-facing paper-trade validators and messaging fixtures, including direct base-status, preflight-note, settlement-sync, settlement-helper, next-steps, forward-check, lane-monitor, daily-summary, lane-summary, rolling ops-history, saved-live refresh-helper coverage, daily-wrapper coverage with explicit recommender/logger failure messaging, and the top-card pipeline/scanner sidecar-pointer contract, plus an auxiliary dependency note for the upstream scan -> recommend -> size -> log chain. This umbrella sweep is supposed to preserve the inherited wrapper-guardrail inventories from those two leaf wrapper reports rather than replacing them with one flattened green light, and now publishes a machine-readable operator-suite evidence boundary so a parent pass cannot be mistaken for settled ROI, live profitability, promotion readiness, or real-money evidence. | Run after editing operator-facing paper-trade summaries or empty-day messaging when you want one quick green/red read |",
                ]
            ),
            "paper_trade_helper_rows_present",
            "the main status-doc file map still includes the paper-trade human-facing ops-history surface, helper validators, saved-live refresh path, and wrapper-level operator sweep that protect live operator behavior",
        )
    )
    checks.append(
        require_paths_exist(
            [
                BASE / "paper_trade_pipeline.py",
                BASE / "validate_paper_trade_pipeline.py",
                BASE / "validate_live_scan_targeting_and_limit_status.py",
                BASE / "run_paper_trade_cycle.sh",
                BASE / "run_daily_portfolio_observation.sh",
                BASE / "paper_trade_recommender.py",
                BASE / "validate_paper_trade_recommender.py",
                BASE / "paper_trade_logger.py",
                BASE / "validate_paper_trade_logger.py",
                BASE / "ev_ticket_engine.py",
                BASE / "validate_ev_ticket_engine.py",
                BASE / "paper_trade_preflight_note.py",
                BASE / "refresh_live_paper_trade_surfaces.py",
                BASE / "paper_trade_daily_summary.py",
                BASE / "paper_trade_lane_summary.py",
                BASE / "paper_trade_ops_history.py",
                BASE / "paper_trade_settlement_sync.py",
                BASE / "paper_trade_settlement_helper.py",
                BASE / "paper_trade_forward_check.py",
                BASE / "paper_trade_lane_monitor.py",
                BASE / "paper_trade_next_steps.py",
                BASE / "validate_paper_trade_status_summary.py",
                BASE / "validate_paper_trade_daily_summary.py",
                BASE / "validate_paper_trade_lane_summary.py",
                BASE / "validate_paper_trade_next_steps.py",
                BASE / "validate_paper_trade_settlement_sync.py",
                BASE / "validate_paper_trade_settlement_helper.py",
                BASE / "validate_paper_trade_preflight_note.py",
                BASE / "validate_paper_trade_forward_check.py",
                BASE / "validate_paper_trade_lane_monitor.py",
                BASE / "validate_paper_trade_ops_history.py",
                BASE / "validate_refresh_live_paper_trade_surfaces.py",
                BASE / "validate_run_daily_portfolio_observation.py",
                BASE / "validate_cache_only_messaging.py",
                BASE / "validate_partial_cache_messaging.py",
                BASE / "validate_paper_trade_operator_suite.py",
            ],
            "named_operator_helper_artifacts_exist",
            "the paper-trade source helpers, refresh-maintenance helpers, wrapper scripts, and direct operator validators named in the main status doc all exist on disk",
        )
    )
    checks.append(
        require(
            "leaf source-of-truth wrapper reports whose inherited wrapper-guardrail inventory broader operator/project sweeps should preserve rather than flatten" in text
            and "the other leaf source-of-truth wrapper report whose inherited wrapper-guardrail inventory broader operator/project sweeps should preserve rather than flatten" in text
            and "preserve the inherited wrapper-guardrail inventories from those two leaf wrapper reports rather than replacing them with one flattened green light" in text
            and "machine-readable operator-suite evidence boundary so a parent pass cannot be mistaken for settled ROI, live profitability, promotion readiness, or real-money evidence" in text,
            "status_doc_wrapper_leaf_source_of_truth_note_present",
            "the main status doc now says plainly that the refresh-helper and daily-wrapper validators are the leaf source-of-truth wrapper reports, that the umbrella operator sweep should preserve rather than flatten their inherited guardrail inventories, and that the operator-suite parent boundary is not settled ROI / live-profitability / promotion / real-money evidence",
        )
    )
    checks.append(
        require(
            "API-access / HTTP 403 action-recheck route preservation" in text
            and "`refresh_daily_wrapper_before_evidence_read` plus `./run_daily_portfolio_observation.sh` as operator context only" in text
            and "before lane enrichment" in text,
            "status_doc_base_api_access_route_documented",
            "the main status-doc validator map now routes base one-line status-summary API-access / HTTP 403 action-recheck edits to the direct status-summary validator before lane enrichment, with the wrapper-refresh action preserved as operator context only",
        )
    )

    suite_read = (
        "COLE_STATUS_AND_PLAN still keeps the conservative frozen story intact: OP_DURABLE_K7 remains the safest anchor, "
        "Phase 7 still beats Phase 8 on forward data, but the status doc now says plainly that the Phase 7 portfolio lead came from a basically flat 2024 (+0.37% on 109) and much stronger 2025 (+105.38% on 66) rather than a smooth two-year glide path, "
        f"the realistic expectation stays +20-25% instead of the +47% headline, the scorecard implementation/file map now points cold readers at matched text/CSV/JSON surfaces with the frozen source-scope / non-live-evidence boundary, CSV bootstrap-CI source-note columns, machine-readable JSON evidence boundary, machine-readable decision-gate minimums, plus bootstrap-CI source notes and PHASE7/PHASE8 report fingerprints, and now consumes `current_evidence_summary.json.scorecard_audit_route` before routing scorecard gate-floor / tier-first ranking / OP_REFINED CI-only / timezone / no-BAQ prerequisite drift questions to `SCORECARD_RANKING_CONTRACT_AUDIT.md` plus `validate_scorecard_ranking_contract_audit.py` as report-synchronization metadata only, {current_snippets['summary_wrapper']}, and {current_context['summary_open_context']}, so {current_context['summary_sample_context']}, the real-money path in the methodical test order now stops at paper-evidence review plus a separate human-approved risk-plan discussion rather than status-doc bet sizing, the current-evidence bridge now requires a combined current-paper read route across `operator_status_context`, `source_freshness` / `requires_refresh_before_right_now_use`, and `operator_read_gate` / `requires_refresh_before_evidence_read` before treating a wrapper-refresh, missing scan-output, or stale/API-failure right-now source as today's operator instruction or evidence, while keeping those operator-context/freshness/read-gate fields as source-readiness metadata rather than performance proof, the current-evidence bridge still exposes `operator_read_gate` as structured instruction/evidence-read routing before a stale/API-failure top card is used and keeps that read gate out of no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, and real-money evidence, the current-evidence bridge now also exposes `rebuild_validation_contract` as the settlement-audit -> current-bridge -> current-bridge-validator order after source-byte changes while keeping that order as provenance/rebuild metadata only, and the main status doc now says a clean current-bridge rebuild is not enough before report-facing comparison quotes because the copied-current-paper fanout must run first as snapshot drift prevention only, not evidence movement, the main status map now routes cross-family current-paper snapshot caveats to the direct cross-family validator and keeps CD-only settled context plus source-published settlement-queue state out of OP-anchor proof or cross-family promotion evidence, the main status map now also routes full-data XGBoost retrain questions to `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py` as model-fit reproducibility metadata only rather than paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence, the stale one-night setup checklist is now replaced by a current operator-session route that starts with `PAPER_TRADE_NOW` and uses `./run_daily_portfolio_observation.sh` as the preferred daily primary+shadow wrapper, target-track lines now treat OP/CD meet windows as seasonal context and require the current calendar/preflight instead of static active-NOW wording, BAQ still stays explicitly separate from BEL, and the main status-doc reading order now includes a live operator route that starts with the matched right-now text/markdown/JSON bundle before the runbook/daily-guide/settlement-audit/ops-history reads, with the runbook route explicitly preserving the OP-anchor provenance/readable-boundary route and audit-only fingerprint / boundary-text boundary, plus the direct frozen-portfolio replay caution validation path, the parent frozen-evidence child JSON fingerprint audit, the compare-main CSV/markdown/JSON bundle and its machine-readable evidence boundary, named `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100` decision-change gates, the OP-anchor markdown/JSON source-provenance plus readable-boundary route, and evidence-scope validation route, the direct live-scan targeting / max-races limited-coverage validation route, the frozen-chain and top-level project child JSON fingerprint audits plus machine-readable evidence boundaries, including the current-hierarchy child guardrail, the quickstart navigation/read-order machine-readable evidence boundary, the main status-doc status/map machine-readable evidence boundary, and the direct live-scan targeting / limited-coverage route plus source-layer paper-trade chain alongside the working-status validator, the direct full-data retrain validator route, the direct top-card validator, the current hierarchy language validator, the daily guide, the paper-trade runbook, this status-doc validator, and a stage-aware operator helper map that now also names the human-facing `OPS_HISTORY.md` surface plus the top-card/rebuild path for matched `PAPER_TRADE_NOW` text/markdown/JSON as preserving primary/shadow recent-run context, machine-readable JSON parity, and lifted lane why-now lines when current lane artifacts provide them, while stale cards explicitly mark downstream lane details as inherited snapshot context rather than current-day state and rebuilt stale top cards keep that honesty note, with the refresh path now treating `--latest-only` and `--skip-top-level` as distinct targeted maintenance modes and optional `--as-of-date` freshness pinning that now says whether it was actually applied or ignored because top-level outputs were skipped, makes the daily guide explicitly point issue-day triage at the direct pipeline/scanner sidecar pointers surfaced from `PAPER_TRADE_NOW`, says the combined daily summary surfaces explicit primary/shadow next-step states plus first-read and broader-review readiness lines with visible shadow review that does not imply live promotion, keeps the wrapper-leaf source-of-truth note explicit so the refresh-helper and daily-wrapper reports stay named as the contract broader operator/project sweeps inherit rather than flatten, keeps the machine-readable operator-suite evidence boundary visible so a parent operator pass stays separate from settled ROI / live profitability / promotion readiness / real-money evidence, keeps the report-surfaces route explicit about preserving the README-inherited wrapper-leaf source-of-truth note inside the narrative rollup rather than flattening it away plus the report-surface machine-readable evidence boundary that keeps narrative validation separate from settled ROI / live profitability / promotion readiness / real-money evidence, keeps the base status-summary API-access / HTTP 403 action-recheck route visible before lane enrichment as operator context only, and keeps the base-summary failure line's recommender/logger stage, error type, and detail visible across the linked next steps, daily summary, lane summary, ops history, refresh path, wrapper, and operator-suite sweep; "
        "methodical-test gates are source-matched to `forward_evidence_scorecard.json` `decision_gate_minimums` with `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100` treated as future ROI-complete paper-observation floors rather than already-cleared gates; "
        "cole-status runbook layer: frozen status/map alignment check, not new forward evidence by itself, with a machine-readable status-map evidence boundary published as status/read-order/repo-map metadata only; stronger forward confidence still requires settled paper trades and other real forward results"
    )

    checks.append(
        require(
            "cole-status runbook layer: frozen status/map alignment check, not new forward evidence by itself" in suite_read
            and "stronger forward confidence still requires settled paper trades and other real forward results" in suite_read,
            "cole_status_summary_explicitly_stays_status_not_new_evidence",
            "cole-status summary now says plainly that a green main-status sweep is status/map alignment checking rather than new forward evidence",
        )
    )
    checks.append(
        require(
            EVIDENCE_BOUNDARY.get("artifact_role") == "main status / repo-map validator"
            and EVIDENCE_BOUNDARY.get("not_new_forward_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_settled_roi_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_live_profitability_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_real_money_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_promotion_readiness_evidence") is True
            and EVIDENCE_BOUNDARY.get("status_validator_passes_are_status_map_metadata_only") is True
            and "ROI-complete settled paper rows" in EVIDENCE_BOUNDARY.get("stronger_forward_confidence_requires", [])
            and "do not promote OP_REFINED_K7 or Phase 8 from status-doc validation cleanliness" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "do not substitute BAQ for BEL" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "machine-readable status-map evidence boundary" in text
            and "machine-readable evidence boundary for status/map alignment only" in text,
            "cole_status_json_publishes_machine_readable_evidence_boundary",
            "main status validator JSON now publishes a machine-readable evidence_boundary block that keeps cold-start status, read-order, validator-routing, operator-entrypoint, and repo-map cleanliness separate from settled ROI, live profitability, promotion readiness, real-money evidence, OP_REFINED_K7 / Phase 8 promotion, odds-only XGBoost reopening, and BAQ/BEL substitution",
        )
    )

    payload = {
        "suite_status": "pass",
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "current_evidence_scorecard_audit_route_read": scorecard_audit_route,
        "current_evidence_gate_progress_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            "source_path": "decision_gate_progress",
            "gate_status": current_context["gate_progress_gate_status"],
            "read": current_context["gate_progress_read"],
            "not_forward_performance_evidence": True,
            "not_promotion_readiness_evidence": True,
            "not_live_profitability_evidence": True,
            "not_real_money_evidence": True,
        },
        "current_evidence_operator_read_gate_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            "source_path": "operator_read_gate",
            "gate_status": current_context["operator_read_gate_gate_status"],
            "valid_use": current_context["operator_read_gate_valid_use"],
            "requires_refresh_before_evidence_read": current_context[
                "operator_read_gate_requires_refresh_before_evidence_read"
            ],
            "recommended_command": current_context["operator_read_gate_recommended_command"],
            "has_api_access_failure_context": current_context[
                "operator_read_gate_has_api_access_failure_context"
            ],
            "has_scanner_failure_boundary": current_context[
                "operator_read_gate_has_scanner_failure_boundary"
            ],
            "has_stale_cache_fallback_context": current_context[
                "operator_read_gate_has_stale_cache_fallback_context"
            ],
            "read": current_context["operator_read_gate_read"],
            "current_top_card_counts_as_no_target_evidence": current_context[
                "operator_read_gate_no_target_evidence"
            ],
            "current_top_card_counts_as_clean_empty_evidence": current_context[
                "operator_read_gate_clean_empty_evidence"
            ],
            "current_top_card_counts_as_bet_readiness_evidence": current_context[
                "operator_read_gate_bet_readiness_evidence"
            ],
            "current_top_card_counts_as_settled_roi_evidence": current_context[
                "operator_read_gate_settled_roi_evidence"
            ],
            "not_forward_performance_evidence": current_context[
                "operator_read_gate_not_forward_performance_evidence"
            ],
            "not_promotion_readiness_evidence": current_context[
                "operator_read_gate_not_promotion_readiness_evidence"
            ],
            "not_live_profitability_evidence": current_context["operator_read_gate_not_live_profitability_evidence"],
            "not_real_money_evidence": current_context["operator_read_gate_not_real_money_evidence"],
        },
        "current_evidence_rebuild_validation_contract_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            "source_path": "rebuild_validation_contract",
            "upstream_refresh_order_commands": current_context["rebuild_order_commands"],
            "prerequisite_rebuild_command": current_context["rebuild_prerequisite_command"],
            "rebuild_command": current_context["rebuild_command"],
            "direct_validation_command": current_context["rebuild_direct_validation_command"],
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": current_context[
                "rebuild_requires_settlement_audit_refresh"
            ],
            "requires_source_consistency_before_quoting_current_totals": current_context[
                "rebuild_requires_source_consistency"
            ],
            "requires_source_freshness_before_right_now_instruction_use": current_context[
                "rebuild_requires_source_freshness"
            ],
            "upstream_refresh_order_is_provenance_metadata_only": current_context[
                "rebuild_order_is_provenance_metadata_only"
            ],
            "not_settled_roi_or_real_money_evidence": current_context[
                "rebuild_not_settled_roi_or_real_money_evidence"
            ],
            "read": current_context["rebuild_order_read"],
        },
        "summary": {"suite_read": suite_read},
        "rebuild": {"workdir": str(BASE), "command": REBUILD_COMMAND},
    }

    out_dir = Path(args.out_dir)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name
    out_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Cole Status And Plan Validation",
        "",
        "This report checks that `COLE_STATUS_AND_PLAN.md` still preserves the frozen project posture and still points cold readers at the right validation and operator surfaces.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Target file: `{DOC.name}`",
        f"- Checks: {len(checks)}",
        "- Result: PASS",
        "",
        "## Checks",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for item in checks:
        lines.append(f"| {item['check']} | {item['status'].upper()} | {item['detail']} |")

    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
            f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
            "- Not new forward evidence; not a live paper-trade ledger; not current-day scanner evidence; not settled ROI; not live-profitability evidence; not real-money evidence; not promotion-readiness evidence.",
            "- Status-doc validator passes are status/map metadata only.",
            f"- Stronger forward confidence still requires: {', '.join(EVIDENCE_BOUNDARY['stronger_forward_confidence_requires'])}.",
            f"- Non-goals: {', '.join(EVIDENCE_BOUNDARY['non_goals'])}.",
            "",
            "## Current Read",
            "",
            f"- Suite read: {suite_read}",
            "",
            "## Bottom Line",
            "",
            "If this validator stays green, `COLE_STATUS_AND_PLAN.md` remains the fastest cold-start status/map read for the frozen evidence posture, the paper-trade workflow/trust-path map, and the direct validator routes Cole should follow before reaching for broader umbrella sweeps.",
            "That green read is status/map alignment, not new forward evidence by itself; the machine-readable boundary keeps it out of the settled-ROI / live-profitability / promotion-readiness / real-money lane.",
            "",
            "## Source Artifacts",
            "",
            "- `COLE_STATUS_AND_PLAN.md`",
            "- `VALIDATION_QUICKSTART.md`",
            "- `DAILY_ARTIFACT_GUIDE.md`",
            "- `PAPER_TRADE_USAGE.md`",
            "- `WORKING_STATUS_REPORT_2026-04-15.md`",
        ]
    )

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
