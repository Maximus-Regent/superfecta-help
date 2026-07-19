#!/usr/bin/env python3
"""
Run the direct decision-card validators as one compact reproducibility sweep.

Purpose:
- give Cole one command for the report-facing decision-card stack
- keep the direct validator layer easy to rerun after edits
- summarize the current anchor / paper / shadow / benchmark / retirement reads in one place
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

import validate_cross_family_decision as cross_family
import validate_method_family_decision_card as method_family
import validate_op_family_decision as op_family
import validate_portfolio_decision_card as portfolio

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "out" / "status_validation" / "decision_cards_suite"
OUT_MD = OUT_DIR / "decision_cards_suite_validation.md"
OUT_JSON = OUT_DIR / "decision_cards_suite_validation.json"
REBUILD_COMMAND = "python3 validate_decision_cards_suite.py"
REUSE_EXISTING_FLAG = "--reuse-existing-child-json"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"

SUITE: list[dict[str, Any]] = [
    {
        "name": "op_family_decision",
        "label": "OP family decision",
        "runner": op_family.main,
        "json_path": BASE / "out" / "status_validation" / "op_family_decision" / "op_family_decision_validation.json",
        "current_read": lambda payload: payload.get("summary", {}).get(
            "suite_read",
            (
                f"Anchor {payload['summary']['anchor_decision']} with {payload['summary']['anchor_holdout_races']} holdout races; "
                f"switch choices {', '.join(f'{year}={rule}' for year, rule in payload['summary']['switch_holdout_choice_map'].items())}"
            ),
        ),
    },
    {
        "name": "cross_family_decision",
        "label": "Cross-family decision",
        "runner": cross_family.main,
        "json_path": BASE / "out" / "status_validation" / "cross_family_decision" / "cross_family_decision_validation.json",
        "current_read": lambda payload: payload.get("summary", {}).get(
            "suite_read",
            f"Anchor={payload['summary']['anchor_rule']}, paper={payload['summary']['paper_rule']}, watch={payload['summary']['watch_rule']}",
        ),
    },
    {
        "name": "portfolio_decision_card",
        "label": "Portfolio decision card",
        "runner": portfolio.main,
        "json_path": BASE / "out" / "status_validation" / "portfolio_decision_card" / "portfolio_decision_card_validation.json",
        "current_read": lambda payload: payload.get("summary", {}).get(
            "suite_read",
            f"Paper now={payload['summary']['paper_now']}, shadow only={payload['summary']['shadow_only']}, benchmark only={payload['summary'].get('benchmark_only', payload['summary']['benchmark'])}",
        ),
    },
    {
        "name": "method_family_decision_card",
        "label": "Method-family decision card",
        "runner": method_family.main,
        "json_path": BASE / "out" / "status_validation" / "method_family_decision_card" / "method_family_decision_card_validation.json",
        "current_read": lambda payload: payload.get("summary", {}).get(
            "suite_read",
            f"Paper now={payload['summary']['paper_now']}, benchmark only={payload['summary']['benchmark_only']}, research only={payload['summary']['research_only']}",
        ),
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        REUSE_EXISTING_FLAG,
        dest="reuse_existing_child_json",
        action="store_true",
        help="reuse existing child validator JSON artifacts instead of rerunning every child suite",
    )
    return parser.parse_args()


def run_validator(fn: Callable[[], int | None], label: str) -> None:
    result = fn()
    if result not in (None, 0):
        raise AssertionError(f"{label} returned non-zero status: {result}")


def load_child_payload(item: dict[str, Any], reuse_existing_child_json: bool) -> dict[str, Any]:
    if reuse_existing_child_json:
        if not item["json_path"].exists():
            raise AssertionError(
                f"{item['label']} reuse requested but child JSON is missing: {item['json_path']}"
            )
    else:
        run_validator(item["runner"], item["label"])
        if not item["json_path"].exists():
            raise AssertionError(f"{item['label']} did not write expected child JSON: {item['json_path']}")
    return json.loads(item["json_path"].read_text(encoding="utf-8"))


def require(condition: bool, label: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    return {"check": label, "status": "pass", "detail": detail}


def require_child_status(payload: dict[str, Any], label: str) -> str:
    artifact = payload.get("artifact")
    for candidate in (
        artifact.get("status") if isinstance(artifact, dict) else None,
        payload.get("suite_status"),
        payload.get("artifact_status"),
        payload.get("result"),
        payload.get("status"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip().upper()
    raise AssertionError(f"{label} child JSON is missing an explicit status field")


def require_child_check_count(payload: dict[str, Any], label: str) -> int:
    value = payload.get("check_count")
    if isinstance(value, bool) or not isinstance(value, int):
        raise AssertionError(f"{label} child JSON is missing explicit integer check_count")
    return value


def require_child_read(payload: dict[str, Any], label: str) -> str:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise AssertionError(f"{label} child JSON is missing summary metadata")
    for key in ("suite_read", "current_read"):
        value = summary.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise AssertionError(f"{label} child JSON is missing summary.suite_read/current_read")


def load_scorecard_ranking_contract(path: Path = SCORECARD_JSON) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    contract = payload.get("ranking_contract")
    if not isinstance(contract, dict):
        raise AssertionError(f"{path.name} is missing ranking_contract")
    if contract.get("rank_is_tier_first_decision_order") is not True:
        raise AssertionError(f"{path.name} ranking_contract no longer marks rank_is_tier_first_decision_order=true")
    if contract.get("forward_trust_is_secondary_within_tier") is not True:
        raise AssertionError(f"{path.name} ranking_contract no longer marks forward_trust_is_secondary_within_tier=true")
    if contract.get("raw_score_is_not_an_automatic_deployment_instruction") is not True:
        raise AssertionError(f"{path.name} ranking_contract no longer says raw score is not an automatic deployment instruction")
    if "CD_CORE_K8 ranks ahead of OP_REFINED_K7" not in str(contract.get("known_rank_override") or ""):
        raise AssertionError(f"{path.name} ranking_contract no longer preserves the CD_CORE_K8 over OP_REFINED_K7 tier-first override")
    return dict(contract)


def main() -> int:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rebuild_command = REBUILD_COMMAND + (f" {REUSE_EXISTING_FLAG}" if args.reuse_existing_child_json else "")
    child_validator_mode = "reuse-existing-child-json" if args.reuse_existing_child_json else "rebuild-children"

    rows: list[dict[str, Any]] = []
    total_checks = 0
    child_payloads: dict[str, Any] = {}

    for item in SUITE:
        payload = load_child_payload(item, args.reuse_existing_child_json)
        child_payloads[item["name"]] = payload
        artifact_status = require_child_status(payload, item["label"])
        check_count = require_child_check_count(payload, item["label"])
        child_checks = payload.get("checks")
        if not isinstance(child_checks, list):
            raise AssertionError(f"{item['label']} child JSON is missing checks list")
        failed = [check["check"] for check in child_checks if check.get("status") != "pass"]
        current_read = require_child_read(payload, item["label"])
        total_checks += check_count
        rows.append(
            {
                "name": item["name"],
                "label": item["label"],
                "artifact_status": artifact_status,
                "check_count": check_count,
                "failed_checks": failed,
                "current_read": current_read,
                "json_path": str(item["json_path"].relative_to(BASE)),
                "child_check_count": check_count,
                "child_checks": child_checks,
                "child_scratch": payload.get("scratch") if isinstance(payload.get("scratch"), dict) else {},
            }
        )

    overall_pass = all(row["artifact_status"] == "PASS" and not row["failed_checks"] for row in rows)
    if not overall_pass:
        raise AssertionError("Decision-card suite has at least one failing validator")

    row_map = {row["name"]: row for row in rows}
    op_summary = child_payloads["op_family_decision"]["summary"]
    cross_summary = child_payloads["cross_family_decision"]["summary"]
    portfolio_summary = child_payloads["portfolio_decision_card"]["summary"]
    method_summary = child_payloads["method_family_decision_card"]["summary"]
    scorecard_ranking_contract = load_scorecard_ranking_contract(SCORECARD_JSON)
    op_operator_boundary = child_payloads["op_family_decision"].get("current_operator_boundary", {})
    op_current_gate_progress = child_payloads["op_family_decision"].get("current_evidence_gate_progress_read", {})
    op_rebuild_validation_contract = child_payloads["op_family_decision"].get("current_evidence_rebuild_validation_contract_read", {})
    op_scorecard_audit_route = child_payloads["op_family_decision"].get("current_evidence_scorecard_audit_route_read", {})
    cross_operator_boundary = child_payloads["cross_family_decision"].get("current_operator_boundary", {})
    portfolio_operator_boundary = portfolio_summary.get("current_operator_boundary", {})
    portfolio_scorecard_audit_route = portfolio_summary.get("scorecard_audit_route_read", {})
    portfolio_rebuild_validation_contract = child_payloads["portfolio_decision_card"].get(
        "current_evidence_rebuild_validation_contract_read", {}
    )
    method_operator_boundary = method_summary.get("current_operator_boundary", {})
    method_scorecard_audit_route = method_summary.get("scorecard_audit_route_read", {})
    method_rebuild_validation_contract = child_payloads["method_family_decision_card"].get(
        "current_evidence_rebuild_validation_contract_read", {}
    )

    rollup_checks = [
        require(
            op_summary["anchor_decision"] == "KEEP AS ANCHOR"
            and op_summary["anchor_holdout_races"] > op_summary["refined_holdout_races"]
            and op_summary["switch_holdout_choice_map"] == {"2024": "OP_REFINED_K7", "2025": "OP_REFINED_K7"}
            and "replay context rather than extra train-only validation" in row_map["op_family_decision"]["current_read"]
            and "scorecard CI-only diagnostic inherited from forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7 keeps ci_only_promotion_allowed=false" in row_map["op_family_decision"]["current_read"]
            and "scorecard decision gates inherited directly from forward_evidence_scorecard.json decision_gate_minimums" in row_map["op_family_decision"]["current_read"]
            and "bridge-published gate progress from current_evidence_summary.json.decision_gate_progress" in row_map["op_family_decision"]["current_read"]
            and "current_evidence_summary.json.rebuild_validation_contract routes source-byte changes through python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py before quoting CURRENT_EVIDENCE_SUMMARY.* as provenance/rebuild metadata only" in row_map["op_family_decision"]["current_read"]
            and op_rebuild_validation_contract.get("upstream_refresh_commands") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and op_rebuild_validation_contract.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and op_rebuild_validation_contract.get("requires_source_consistency_before_quoting_current_totals") is True
            and op_rebuild_validation_contract.get("upstream_refresh_order_is_provenance_metadata_only") is True
            and op_rebuild_validation_contract.get("not_settled_roi_or_real_money_evidence") is True
            and "current_evidence_summary.json.scorecard_audit_route points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py as report-synchronization metadata only" in row_map["op_family_decision"]["current_read"]
            and op_scorecard_audit_route.get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and op_scorecard_audit_route.get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and op_scorecard_audit_route.get("json_path") == "scorecard_ranking_contract_audit.json"
            and op_scorecard_audit_route.get("not_forward_performance_evidence") is True
            and op_scorecard_audit_route.get("not_settled_roi_evidence") is True
            and op_scorecard_audit_route.get("not_promotion_readiness_evidence") is True
            and op_scorecard_audit_route.get("not_live_profitability_evidence") is True
            and op_scorecard_audit_route.get("not_bankroll_guidance") is True
            and op_scorecard_audit_route.get("not_real_money_evidence") is True
            and op_current_gate_progress.get("gate_status") == "all_uncleared"
            and op_current_gate_progress.get("all_gates_ready") is False
            and "source provenance fingerprints compare-main logic/JSON, race-cache, Phase 7 rules, walk-forward rules, and scorecard inputs as reproducibility metadata only" in row_map["op_family_decision"]["current_read"]
            and "current operator boundary inherited from compare-main JSON names stale-card refresh route=./run_daily_portfolio_observation.sh" in row_map["op_family_decision"]["current_read"]
            and (
                "current settled rule mix OP_DURABLE_K7="
                f"{op_operator_boundary.get('op_anchor_roi_complete_rows')} / CD_CORE_K8="
                f"{op_operator_boundary.get('cd_companion_roi_complete_rows')} with CD-only context="
                f"{op_operator_boundary.get('current_settled_context_is_cd_only')}"
            ) in row_map["op_family_decision"]["current_read"]
            and f"copied current-operator generated_at={op_operator_boundary.get('generated_at')} stays parseable timezone-aware provenance metadata only" in row_map["op_family_decision"]["current_read"]
            and "rather than settled ROI, OP-anchor proof, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in row_map["op_family_decision"]["current_read"]
            and "saved CSV, saved markdown, and real CLI stdout stay pinned to the same OP-family decision render" in row_map["op_family_decision"]["current_read"],
            "op_family_keeps_anchor_and_watch_bar",
            "the OP family rollup still keeps OP_DURABLE_K7 as the anchor on the larger forward sample while OP_REFINED_K7 and the train-only switch stay watch-level challengers, says plainly that the fixed-rule secondary read is replay context rather than extra train-only validation, carries the scorecard-sourced CI-only OP_REFINED diagnostic, paper-observation gates, scorecard-audit routing, and the current operator boundary as routing/provenance only, and surfaces source provenance plus saved-artifact and CLI reproducibility directly",
        ),
        require(
            cross_summary["anchor_rule"] == "OP_DURABLE_K7"
            and cross_summary["paper_rule"] == "CD_CORE_K8"
            and cross_summary["watch_rule"] == "OP_REFINED_K7"
            and "valid_evidence_scope=split_aware_cross_family_paper_hierarchy_only" in row_map["cross_family_decision"]["current_read"]
            and "broader Phase 8 pockets KEE_K9 / SA_K9 / DMR_FALL_K7 stay observation-only rather than entering the near-term promotion queue" in row_map["cross_family_decision"]["current_read"]
            and "anchor still leads on OP holdout sample" in row_map["cross_family_decision"]["current_read"]
            and "recurrence context rather than a second profit line" in row_map["cross_family_decision"]["current_read"]
            and "scorecard decision gates inherited directly from forward_evidence_scorecard.json decision_gate_minimums" in row_map["cross_family_decision"]["current_read"]
            and "current_evidence_summary.json.scorecard_audit_route points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py as report-synchronization metadata only" in row_map["cross_family_decision"]["current_read"]
            and "current_evidence_summary.json.rebuild_validation_contract routes source-byte changes through python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py before quoting CURRENT_EVIDENCE_SUMMARY.* as provenance/rebuild metadata only" in row_map["cross_family_decision"]["current_read"]
            and "current operator boundary inherited from compare-main JSON names stale-card refresh route=./run_daily_portfolio_observation.sh" in row_map["cross_family_decision"]["current_read"]
            and (
                "current settled rule mix OP_DURABLE_K7="
                f"{cross_operator_boundary.get('op_anchor_roi_complete_rows')} / CD_CORE_K8="
                f"{cross_operator_boundary.get('cd_companion_roi_complete_rows')} with CD-only context="
                f"{cross_operator_boundary.get('current_settled_context_is_cd_only')}"
            ) in row_map["cross_family_decision"]["current_read"]
            and f"copied current-operator generated_at={cross_operator_boundary.get('generated_at')} stays parseable timezone-aware provenance metadata only" in row_map["cross_family_decision"]["current_read"]
            and "rather than settled ROI, OP-anchor proof, cross-family promotion readiness, live profitability, bankroll guidance, or real-money evidence" in row_map["cross_family_decision"]["current_read"]
            and "source provenance fingerprints the scorecard CSV/JSON, frozen-eval, compare-main, and current-evidence inputs as reproducibility metadata only" in row_map["cross_family_decision"]["current_read"]
            and "saved CSV, saved markdown, and real CLI stdout stay pinned to the same cross-family decision render" in row_map["cross_family_decision"]["current_read"],
            "cross_family_keeps_anchor_paper_watch_order",
            "the cross-family rollup still orders the shortlist as OP_DURABLE_K7 anchor, CD_CORE_K8 paper, and OP_REFINED_K7 watch, carries the exact cross-family valid_evidence_scope, keeps the smaller Phase 8 names explicit as observation-only pockets outside the near-term promotion queue, says plainly that the walk-forward-selection counts are recurrence context rather than a second profit line, carries scorecard-sourced paper-observation gates, scorecard-audit routing, plus the current operator boundary as routing/provenance only, and surfaces source provenance plus saved-artifact and CLI reproducibility directly",
        ),
        require(
            child_payloads["op_family_decision"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and child_payloads["op_family_decision"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and row_map["op_family_decision"].get("child_scratch", {}).get("tmp_parent_is_project_local") is True
            and row_map["op_family_decision"].get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and any(
                check.get("check") == "cli_scratch_metadata_published"
                for check in row_map["op_family_decision"].get("child_checks", [])
            )
            and child_payloads["cross_family_decision"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and child_payloads["cross_family_decision"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and row_map["cross_family_decision"].get("child_scratch", {}).get("tmp_parent_is_project_local") is True
            and row_map["cross_family_decision"].get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and any(
                check.get("check") == "cli_scratch_metadata_published"
                for check in row_map["cross_family_decision"].get("child_checks", [])
            ),
            "op_cross_family_scratch_metadata_published",
            "the OP-family and cross-family direct card validators now have to publish project-local scratch metadata through the decision-card suite rows, and both leaves must expose that metadata as a named structured check",
        ),
        require(
            child_payloads["portfolio_decision_card"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and child_payloads["portfolio_decision_card"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and row_map["portfolio_decision_card"].get("child_scratch", {}).get("tmp_parent_is_project_local") is True
            and row_map["portfolio_decision_card"].get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and any(
                check.get("check") == "cli_scratch_metadata_published"
                for check in row_map["portfolio_decision_card"].get("child_checks", [])
            )
            and child_payloads["method_family_decision_card"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and child_payloads["method_family_decision_card"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and row_map["method_family_decision_card"].get("child_scratch", {}).get("tmp_parent_is_project_local") is True
            and row_map["method_family_decision_card"].get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and any(
                check.get("check") == "cli_scratch_metadata_published"
                for check in row_map["method_family_decision_card"].get("child_checks", [])
            ),
            "portfolio_method_scratch_metadata_published",
            "the portfolio and method-family direct card validators now have to publish project-local scratch metadata through the decision-card suite rows, and both leaves must expose that metadata as a named structured check",
        ),
        require(
            scorecard_ranking_contract.get("rank_is_tier_first_decision_order") is True
            and scorecard_ranking_contract.get("forward_trust_is_secondary_within_tier") is True
            and scorecard_ranking_contract.get("raw_score_is_not_an_automatic_deployment_instruction") is True
            and "CD_CORE_K8 ranks ahead of OP_REFINED_K7" in str(scorecard_ranking_contract.get("known_rank_override") or ""),
            "scorecard_ranking_contract_inherited",
            "the decision-card suite now consumes forward_evidence_scorecard.json ranking_contract so ANCHOR / PAPER / WATCH card wording inherits tier-first semantics and raw OP_REFINED_K7 score cannot become an automatic promotion cue",
        ),
        require(
            portfolio_summary["paper_now"] == "phase7_live_portfolio"
            and portfolio_summary["shadow_only"] == "phase8_frozen_portfolio"
            and portfolio_summary["benchmark_only"] == "train_only_selector"
            and portfolio_summary["phase7_holdout_roi"] > portfolio_summary["phase8_holdout_roi"] > portfolio_summary["selector_holdout_roi"]
            and isinstance(portfolio_summary.get("current_operator_boundary"), dict)
            and portfolio_summary["current_operator_boundary"].get("not_forward_performance_evidence") is True
            and portfolio_summary["current_operator_boundary"].get("not_bet_readiness_evidence_by_itself") is True
            and portfolio_summary["current_operator_boundary"].get("current_settled_context_is_cd_only") is True
            and portfolio_summary["current_operator_boundary"].get("op_anchor_roi_complete_rows") == 0
            and portfolio_summary["current_operator_boundary"].get("cd_companion_roi_complete_rows")
            == portfolio_summary["current_operator_boundary"].get("roi_complete_primary_rows")
            and portfolio_summary["current_operator_boundary"].get("refresh_can_update_operator_surfaces") is True
            and portfolio_summary["current_operator_boundary"].get("refresh_can_settle_open_rows_by_itself") is False
            and portfolio_summary["current_operator_boundary"].get("refresh_counts_as_roi_complete_evidence_by_itself") is False
            and portfolio_summary["current_operator_boundary"].get("clean_empty_refresh_counts_as_forward_performance") is False
            and child_payloads["portfolio_decision_card"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and child_payloads["portfolio_decision_card"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and isinstance(portfolio_summary.get("decision_change_gate_minimums"), dict)
            and portfolio_summary["decision_change_gate_minimums"].get("phase8_promotion_review", {}).get("minimum_roi_complete_settled_observations") == 20
            and portfolio_summary["decision_change_gate_minimums"].get("anchor_displacement", {}).get("minimum_roi_complete_same_candidate_observations") == 30
            and portfolio_summary["decision_change_gate_minimums"].get("real_money_discussion", {}).get("minimum_total_settled_roi_complete_observations") == 100
            and portfolio_summary.get("current_evidence_gate_progress_read", {}).get("gate_status") == "all_uncleared"
            and portfolio_summary.get("current_evidence_gate_progress_read", {}).get("all_gates_ready") is False
            and "Gate progress: primary first-read 6/30" in portfolio_summary.get("current_evidence_gate_progress_read", {}).get("read", "")
            and "OP anchor same-candidate 0/30" in portfolio_summary.get("current_evidence_gate_progress_read", {}).get("read", "")
            and "Phase 8 weakest shadow 0/20" in portfolio_summary.get("current_evidence_gate_progress_read", {}).get("read", "")
            and "real-money discussion floor 6/100" in portfolio_summary.get("current_evidence_gate_progress_read", {}).get("read", "")
            and portfolio_scorecard_audit_route.get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and portfolio_scorecard_audit_route.get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and portfolio_scorecard_audit_route.get("json_path") == "scorecard_ranking_contract_audit.json"
            and portfolio_scorecard_audit_route.get("not_forward_performance_evidence") is True
            and portfolio_scorecard_audit_route.get("not_settled_roi_evidence") is True
            and portfolio_scorecard_audit_route.get("not_promotion_readiness_evidence") is True
            and portfolio_scorecard_audit_route.get("not_live_profitability_evidence") is True
            and portfolio_scorecard_audit_route.get("not_bankroll_guidance") is True
            and portfolio_scorecard_audit_route.get("not_real_money_evidence") is True
            and child_payloads["portfolio_decision_card"].get("scorecard_ci_only_diagnostic", {}).get("ci_only_promotion_allowed") is False
            and "bridge-published gate progress from current_evidence_summary.json.decision_gate_progress" in row_map["portfolio_decision_card"]["current_read"]
            and "current_evidence_summary.json.rebuild_validation_contract routes source-byte changes through python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py before quoting CURRENT_EVIDENCE_SUMMARY.* as provenance/rebuild metadata only" in row_map["portfolio_decision_card"]["current_read"]
            and portfolio_rebuild_validation_contract.get("upstream_refresh_commands") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and portfolio_rebuild_validation_contract.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and portfolio_rebuild_validation_contract.get("requires_source_consistency_before_quoting_current_totals") is True
            and portfolio_rebuild_validation_contract.get("upstream_refresh_order_is_provenance_metadata_only") is True
            and portfolio_rebuild_validation_contract.get("not_settled_roi_or_real_money_evidence") is True
            and "current_evidence_summary.json.scorecard_audit_route points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py as report-synchronization metadata only" in row_map["portfolio_decision_card"]["current_read"]
            and "current operator boundary inherited from compare-main JSON" in row_map["portfolio_decision_card"]["current_read"]
            and "scorecard CI-only diagnostic inherited from forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7 keeps ci_only_promotion_allowed=false so positive OP_REFINED CI support stays out of portfolio-level Phase 8 default readiness" in row_map["portfolio_decision_card"]["current_read"]
            and (
                "current operator rule-mix boundary keeps OP_DURABLE_K7="
                f"{portfolio_operator_boundary.get('op_anchor_roi_complete_rows')} and CD_CORE_K8="
                f"{portfolio_operator_boundary.get('cd_companion_roi_complete_rows')} as CD-only current settled context"
            ) in row_map["portfolio_decision_card"]["current_read"]
            and "stale-card refresh boundary says run `./run_daily_portfolio_observation.sh` before using stale right-now instructions" in row_map["portfolio_decision_card"]["current_read"]
            and "clean-empty-forward-performance=False" in row_map["portfolio_decision_card"]["current_read"]
            and f"copied current-operator generated_at={portfolio_operator_boundary.get('generated_at')} stays parseable timezone-aware provenance metadata only" in row_map["portfolio_decision_card"]["current_read"]
            and f"structured freshness provenance bridge reference={portfolio_operator_boundary.get('source_freshness_generated_reference_date')} ({portfolio_operator_boundary.get('source_freshness_generated_reference_timezone')}), comparison={portfolio_operator_boundary.get('source_freshness_staleness_comparison_source')} / {portfolio_operator_boundary.get('source_freshness_staleness_comparison_date')}" in row_map["portfolio_decision_card"]["current_read"]
            and "decision gates inherited from compare-main JSON decision_change_gate_minimums" in row_map["portfolio_decision_card"]["current_read"]
            and "rather than settled ROI, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in row_map["portfolio_decision_card"]["current_read"]
            and "saved CSV, saved markdown, and real CLI stdout stay pinned to the same portfolio decision render" in row_map["portfolio_decision_card"]["current_read"],
            "portfolio_card_keeps_phase7_over_phase8_and_selector",
            "the portfolio decision card still keeps Phase 7 as PAPER NOW ahead of Phase 8 shadow and the train-only selector benchmark, carries the current operator boundary, bridge-published current gate progress, scorecard-audit route, CD-only current settled rule mix, stale-card refresh boundary, scorecard-sourced decision gates, and the scorecard-sourced OP_REFINED CI-only diagnostic as routing/provenance rather than performance evidence, and surfaces saved-artifact, CLI reproducibility, plus project-local scratch-root hygiene directly",
        ),
        require(
            method_summary["paper_now"] == "selective_rule_path"
            and method_summary["benchmark_only"] == "harville_ranked"
            and method_summary["research_only"] == "xgboost_residual"
            and float(method_summary["best_ml_roi"]) < 0
            and float(method_summary["payout_rmse_reduction_pct"]) > 0
            and "model-fit context, not a betting-evidence line" in row_map["method_family_decision_card"]["current_read"]
            and isinstance(method_summary.get("current_operator_boundary"), dict)
            and method_summary["current_operator_boundary"].get("not_forward_performance_evidence") is True
            and method_summary["current_operator_boundary"].get("not_bet_readiness_evidence_by_itself") is True
            and child_payloads["method_family_decision_card"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and child_payloads["method_family_decision_card"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and isinstance(method_summary.get("decision_change_gate_minimums"), dict)
            and method_summary["decision_change_gate_minimums"].get("phase8_promotion_review", {}).get("minimum_roi_complete_settled_observations") == 20
            and method_summary["decision_change_gate_minimums"].get("anchor_displacement", {}).get("minimum_roi_complete_same_candidate_observations") == 30
            and method_summary["decision_change_gate_minimums"].get("real_money_discussion", {}).get("minimum_total_settled_roi_complete_observations") == 100
            and isinstance(method_summary.get("scorecard_decision_gate_minimums"), dict)
            and method_summary["scorecard_decision_gate_minimums"].get("phase8_promotion_review", {}).get("minimum_roi_complete_settled_observations") == 20
            and method_summary["scorecard_decision_gate_minimums"].get("anchor_displacement", {}).get("minimum_roi_complete_same_candidate_observations") == 30
            and method_summary["scorecard_decision_gate_minimums"].get("real_money_discussion", {}).get("minimum_total_settled_roi_complete_observations") == 100
            and "current operator boundary inherited from compare-main JSON" in row_map["method_family_decision_card"]["current_read"]
            and f"copied current-operator generated_at={method_operator_boundary.get('generated_at')} stays parseable timezone-aware provenance metadata only" in row_map["method_family_decision_card"]["current_read"]
            and f"structured freshness provenance bridge reference={method_operator_boundary.get('source_freshness_generated_reference_date')} ({method_operator_boundary.get('source_freshness_generated_reference_timezone')}), comparison={method_operator_boundary.get('source_freshness_staleness_comparison_source')} / {method_operator_boundary.get('source_freshness_staleness_comparison_date')}" in row_map["method_family_decision_card"]["current_read"]
            and "decision gates loaded directly from scorecard JSON decision_gate_minimums" in row_map["method_family_decision_card"]["current_read"]
            and "current_evidence_summary.json.rebuild_validation_contract routes source-byte changes through python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py before quoting CURRENT_EVIDENCE_SUMMARY.* as provenance/rebuild metadata only" in row_map["method_family_decision_card"]["current_read"]
            and method_rebuild_validation_contract.get("upstream_refresh_commands") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and method_rebuild_validation_contract.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and method_rebuild_validation_contract.get("requires_source_consistency_before_quoting_current_totals") is True
            and method_rebuild_validation_contract.get("upstream_refresh_order_is_provenance_metadata_only") is True
            and method_rebuild_validation_contract.get("not_settled_roi_or_real_money_evidence") is True
            and "current_evidence_summary.json.scorecard_audit_route points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py as report-synchronization metadata only" in row_map["method_family_decision_card"]["current_read"]
            and method_scorecard_audit_route.get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and method_scorecard_audit_route.get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and method_scorecard_audit_route.get("json_path") == "scorecard_ranking_contract_audit.json"
            and method_scorecard_audit_route.get("not_forward_performance_evidence") is True
            and method_scorecard_audit_route.get("not_settled_roi_evidence") is True
            and method_scorecard_audit_route.get("not_promotion_readiness_evidence") is True
            and method_scorecard_audit_route.get("not_live_profitability_evidence") is True
            and method_scorecard_audit_route.get("not_bankroll_guidance") is True
            and method_scorecard_audit_route.get("not_real_money_evidence") is True
            and "scorecard CI-only diagnostic inherited from forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7 keeps ci_only_promotion_allowed=false" in row_map["method_family_decision_card"]["current_read"]
            and "rather than settled ROI, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in row_map["method_family_decision_card"]["current_read"]
            and "saved CSV, saved markdown, and real CLI stdout stay pinned to the same method-family decision render" in row_map["method_family_decision_card"]["current_read"],
            "method_family_keeps_selective_over_harville_and_xgboost",
            "the method-family card still keeps selective rules paper-first, Harville benchmark-only, and XGBoost research-only despite modest prediction-metric improvement, says plainly that the payout-RMSE gain is model-fit context rather than a betting-evidence line, carries the current operator boundary, scorecard-audit route, scorecard-sourced decision gates, and scorecard-sourced OP_REFINED CI-only diagnostic as routing/provenance rather than performance evidence, and surfaces saved-artifact, CLI reproducibility, plus project-local scratch-root hygiene directly",
        ),
        require(
            all(row_map[name]["artifact_status"] == "PASS" for name in row_map)
            and all(isinstance(row_map[name]["current_read"], str) and row_map[name]["current_read"].strip() for name in row_map)
            and all(isinstance(row_map[name]["child_check_count"], int) and row_map[name]["child_check_count"] > 0 for name in row_map),
            "child_decision_validators_publish_explicit_status_counts_and_reads",
            "all four direct decision-card validators now have to publish explicit status, nonzero check_count, and summary read metadata instead of letting the parent suite infer them from partial payloads",
        ),
        require(
            child_payloads["op_family_decision"].get("suite_status") == "pass"
            and int(child_payloads["op_family_decision"].get("total_checks", 0)) == 41
            and child_payloads["cross_family_decision"].get("suite_status") == "pass"
            and int(child_payloads["cross_family_decision"].get("total_checks", 0)) == 43
            and child_payloads["portfolio_decision_card"].get("suite_status") == "pass"
            and int(child_payloads["portfolio_decision_card"].get("total_checks", 0)) == 43
            and child_payloads["method_family_decision_card"].get("suite_status") == "pass"
            and int(child_payloads["method_family_decision_card"].get("total_checks", 0)) == 47,
            "core_decision_source_validators_publish_explicit_suite_status_and_totals",
            "the four direct decision-card source validators now publish explicit top-level suite_status plus total_checks metadata, including OP-family, cross-family, portfolio, method-family project-local CLI scratch-root metadata, malformed generated_at fail-fast coverage, inherited current-operator generated_at provenance, operator_read_gate publication, scorecard-audit route publication, current bridge rebuild-route publication, false refresh-boundary no-real-money flag fail-fast coverage, portfolio clean-empty refresh-accounting fail-fast coverage, and scorecard CI-only diagnostic fail-fast coverage, instead of relying only on nested artifact status and raw check arrays",
        ),
        require(
            row_map["op_family_decision"].get("child_check_count") == 41
            and isinstance(row_map["op_family_decision"].get("child_checks"), list)
            and {check.get("check") for check in row_map["op_family_decision"]["child_checks"]} == {
                "markdown_matches_rebuild",
                "csv_year_count_columns_present",
                "cli_csv_matches_saved",
                "cli_markdown_matches_rebuild",
                "cli_stdout_matches_generated_report",
                "cli_scratch_root_project_local",
                "cli_scratch_metadata_published",
                "cli_custom_input_and_output_paths",
                "cli_cache_contract_required",
                "cli_phase7_anchor_rule_required",
                "cli_walk_forward_rule_rows_required",
                "cli_scorecard_rule_rows_required",
                "cli_scorecard_ranking_contract_required",
                "cli_scorecard_ci_only_diagnostic_required",
                "cli_scorecard_decision_gate_minimums_required",
                "bad_current_operator_generated_at_fails_fast",
                "false_current_operator_refresh_not_real_money_flag_fails_fast",
                "missing_scorecard_audit_route_fails_fast",
                "missing_rebuild_validation_contract_fails_fast",
                "scorecard_ranking_contract_inherited",
                "scorecard_ci_only_diagnostic_documented",
                "scorecard_decision_gate_minimums_documented",
                "current_operator_boundary_documented",
                "current_operator_read_gate_documented",
                "current_evidence_gate_progress_documented",
                "current_evidence_rebuild_validation_contract_documented",
                "current_evidence_scorecard_audit_route_documented",
                "current_operator_boundary_generated_at_is_timezone_aware",
                "source_provenance_markdown_matches_disk",
                "anchor_stays_anchor",
                "durable_matches_frozen_holdout",
                "refined_matches_frozen_holdout",
                "switch_holdout_choices",
                "switch_collapses_to_refined_on_holdout",
                "refined_replacement_bar",
                "switch_replacement_bar",
                "durable_holdout_year_split",
                "refined_holdout_year_split",
                "holdout_split_section_present",
                "anchor_has_larger_forward_sample",
                "matches_compare_main_rows",
            }
            and row_map["cross_family_decision"].get("child_check_count") == 43
            and isinstance(row_map["cross_family_decision"].get("child_checks"), list)
            and {check.get("check") for check in row_map["cross_family_decision"]["child_checks"]} == {
                "markdown_matches_rebuild",
                "csv_year_count_columns_present",
                "csv_shadow_columns_present",
                "cli_csv_matches_saved",
                "cli_markdown_matches_rebuild",
                "cli_stdout_matches_generated_report",
                "cli_scratch_root_project_local",
                "cli_scratch_metadata_published",
                "cli_custom_input_and_output_paths",
                "missing_shortlist_rule_fails_fast",
                "missing_watch_context_rule_fails_fast",
                "missing_frozen_year_slice_fails_fast",
                "missing_scorecard_ranking_contract_fails_fast",
                "missing_scorecard_decision_gate_minimums_fails_fast",
                "missing_operator_boundary_fails_fast",
                "missing_scorecard_audit_route_fails_fast",
                "missing_rebuild_validation_contract_fails_fast",
                "bad_current_operator_generated_at_fails_fast",
                "false_current_operator_refresh_not_real_money_flag_fails_fast",
                "scorecard_ranking_contract_inherited",
                "scorecard_decision_gate_minimums_documented",
                "current_operator_boundary_documented",
                "current_evidence_scorecard_audit_route_documented",
                "current_evidence_rebuild_validation_contract_documented",
                "current_operator_read_gate_documented",
                "current_operator_boundary_generated_at_is_timezone_aware",
                "source_provenance_markdown_matches_disk",
                "cross_family_roles",
                "scorecard_tier_alignment",
                "shadow_rank_ordering",
                "op_durable_k7_matches_scorecard",
                "cd_core_k8_matches_scorecard",
                "op_refined_k7_matches_scorecard",
                "op_durable_k7_matches_year_slices",
                "cd_core_k8_matches_year_slices",
                "op_refined_k7_matches_year_slices",
                "anchor_has_larger_sample_than_cd",
                "cd_is_paper_not_anchor",
                "op_refined_stays_watch",
                "markdown_split_counts_present",
                "markdown_shadow_read_present",
                "markdown_scorecard_ci_only_diagnostic_present",
                "markdown_observation_only_pockets_present",
            }
            and row_map["portfolio_decision_card"].get("child_check_count") == 43
            and isinstance(row_map["portfolio_decision_card"].get("child_checks"), list)
            and {check.get("check") for check in row_map["portfolio_decision_card"]["child_checks"]} == {
                "markdown_matches_rebuild",
                "cli_csv_matches_saved",
                "cli_markdown_matches_rebuild",
                "cli_stdout_matches_generated_report",
                "cli_scratch_root_project_local",
                "cli_scratch_metadata_published",
                "cli_custom_source_and_output_paths",
                "missing_compare_method_fails_fast",
                "missing_frozen_year_slice_fails_fast",
                "missing_walk_forward_year_fails_fast",
                "missing_scorecard_ranking_contract_fails_fast",
                "missing_scorecard_ci_only_diagnostic_fails_fast",
                "missing_operator_boundary_fails_fast",
                "bad_current_operator_generated_at_fails_fast",
                "missing_current_operator_freshness_reference_fails_fast",
                "false_current_operator_refresh_not_real_money_flag_fails_fast",
                "false_current_operator_clean_empty_refresh_accounting_fails_fast",
                "missing_decision_gate_minimums_fails_fast",
                "missing_rebuild_validation_contract_fails_fast",
                "scorecard_ranking_contract_inherited",
                "scorecard_ci_only_diagnostic_inherited",
                "source_provenance_markdown_matches_disk",
                "current_operator_boundary_documented",
                "scorecard_audit_route_documented",
                "current_evidence_rebuild_validation_contract_documented",
                "current_operator_read_gate_documented",
                "current_operator_boundary_generated_at_is_timezone_aware",
                "current_operator_rule_mix_and_refresh_boundary_documented",
                "decision_gate_minimums_documented",
                "portfolio_roles",
                "phase7_live_portfolio_matches_compare_main",
                "phase8_frozen_portfolio_matches_compare_main",
                "train_only_selector_matches_compare_main",
                "phase7_matches_frozen_holdout",
                "phase8_matches_frozen_holdout",
                "phase7_year_slices",
                "phase8_year_slices",
                "selector_year_slices",
                "current_holdout_order",
                "phase8_stays_shadow",
                "selector_stays_benchmark",
                "selector_not_best_daily_operating_default_wording",
                "year_split_counts_documented",
            }
            and row_map["method_family_decision_card"].get("child_check_count") == 47
            and isinstance(row_map["method_family_decision_card"].get("child_checks"), list)
            and {check.get("check") for check in row_map["method_family_decision_card"]["child_checks"]} == {
                "markdown_matches_rebuild",
                "cli_csv_matches_saved",
                "cli_markdown_matches_rebuild",
                "cli_stdout_matches_generated_report",
                "cli_scratch_root_project_local",
                "cli_scratch_metadata_published",
                "cli_custom_source_and_output_paths",
                "custom_cross_family_hierarchy_renders_dynamically",
                "missing_compare_method_fails_fast",
                "missing_primary_shadow_fails_fast",
                "missing_harville_backtest_line_fails_fast",
                "missing_ab_delta_path_fails_fast",
                "missing_scorecard_ranking_contract_fails_fast",
                "malformed_scorecard_decision_gate_minimums_fails_fast",
                "missing_scorecard_audit_route_fails_fast",
                "missing_rebuild_validation_contract_fails_fast",
                "missing_scorecard_ci_only_diagnostic_fails_fast",
                "missing_operator_boundary_fails_fast",
                "bad_current_operator_generated_at_fails_fast",
                "missing_current_operator_freshness_reference_fails_fast",
                "false_current_operator_refresh_not_real_money_flag_fails_fast",
                "missing_decision_gate_minimums_fails_fast",
                "scorecard_ranking_contract_inherited",
                "scorecard_ci_only_diagnostic_inherited",
                "source_provenance_markdown_matches_disk",
                "current_operator_boundary_documented",
                "current_operator_read_gate_documented",
                "current_operator_boundary_generated_at_is_timezone_aware",
                "current_evidence_rebuild_validation_contract_documented",
                "decision_gate_minimums_documented",
                "scorecard_audit_route_documented",
                "method_family_roles",
                "csv_shadow_columns_present",
                "selective_matches_compare_main",
                "harville_matches_backtest",
                "xgboost_best_ml_line",
                "xgboost_ab_metric",
                "only_selective_is_paper_positive",
                "selective_holdout_split_documented",
                "selective_shadow_read_documented",
                "harville_negative_on_huge_sample",
                "xgboost_prediction_gain_not_betting_gain",
                "narrow_follow_up_section",
                "cross_family_follow_up_entry",
                "op_follow_up_entry",
                "ab_follow_up_entry",
                "scope_follow_up_entry",
            },
            "child_decision_validators_publish_structured_checks",
            "all four direct decision-card validators now have to publish their pinned structured child-check sets instead of only raw check arrays",
        ),
    ]

    suite_read_parts = [
        row_map["op_family_decision"]["current_read"],
        row_map["cross_family_decision"]["current_read"],
        row_map["portfolio_decision_card"]["current_read"],
        row_map["method_family_decision_card"]["current_read"],
        f"scorecard ranking contract inherited=tier-first, raw Score non-promotional ({scorecard_ranking_contract['known_rank_override']})",
        "decision-card layer=report-facing frozen evidence ordering, not new forward proof; changes in real confidence still require settled paper trades in the operator lane",
    ]
    suite_read = "; ".join(suite_read_parts)
    rollup_checks.append(
        require(
            "decision-card layer=report-facing frozen evidence ordering, not new forward proof" in suite_read
            and "changes in real confidence still require settled paper trades in the operator lane" in suite_read,
            "decision_cards_are_frozen_ordering_not_new_evidence",
            "the decision-card suite now says plainly that these card-level roles rank frozen evidence and that stronger forward confidence still requires settled paper trades",
        )
    )

    payload = {
        "suite_status": "pass",
        "validators_run": len(rows),
        "total_frozen_checks": total_checks,
        "rows": rows,
        "scorecard_ranking_contract": scorecard_ranking_contract,
        "scorecard_ranking_contract_source": str(SCORECARD_JSON.relative_to(BASE)),
        "total_checks": len(rollup_checks),
        "check_count": len(rollup_checks),
        "checks": rollup_checks,
        "summary": {
            "suite_read": suite_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": rebuild_command,
            "child_validator_mode": child_validator_mode,
        },
    }

    lines = [
        "# Decision Cards Validation Suite",
        "",
        "This report runs the four direct decision-card validators together and summarizes the current report-facing hierarchy in one place.",
        "",
        f"- Validators run: {len(rows)}",
        f"- Total frozen / ordering checks: {total_checks}",
        "- Overall result: PASS",
        "",
        "## Validator Summary",
        "",
        "| Validator | Artifact | Frozen Checks | Source |",
        "|---|---|---:|---|",
    ]

    for row in rows:
        lines.append(
            f"| {row['label']} | {row['artifact_status']} | {row['check_count']} | `{row['json_path']}` |"
        )

    lines.extend(
        [
            "",
            "## Rollup Checks",
            "",
        ]
    )
    for check in rollup_checks:
        lines.append(f"- PASS `{check['check']}` — {check['detail']}")

    lines.extend(
        [
            "",
            "## Current Read",
            "",
            f"- Suite read: {suite_read}",
            "",
            "## Rebuild",
            "",
            f"- Working directory: `{BASE}`",
            f"- Command: `{rebuild_command}`",
            f"- Child validator mode: `{child_validator_mode}`",
            "",
            "## Child Validator Reads",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- **{row['label']}**: {row['current_read']}")

    lines.extend(
        [
            "",
            "## Bottom Line",
            "",
            "The direct validator layer is currently aligned end-to-end:",
            "",
            "- `OP_DURABLE_K7` still stays the OP anchor",
            "- the active shortlist still reads `ANCHOR / PAPER / WATCH`",
            f"- the scorecard ranking contract is inherited from `{SCORECARD_JSON.name}`: tier-first={scorecard_ranking_contract['rank_is_tier_first_decision_order']}; raw-score-promotional={not scorecard_ranking_contract['raw_score_is_not_an_automatic_deployment_instruction']}",
            "- the top portfolio choice still reads `PAPER NOW / SHADOW ONLY / BENCHMARK ONLY`",
            "- the method-family hierarchy still retires Harville and odds-only XGBoost behind the selective rule path",
            "",
            "If this suite stays green after edits, the report-facing decision cards are still telling the same conservative story.",
            "They are a frozen-evidence ordering surface, not a new forward-evidence surface; stronger forward confidence still requires settled paper trades in the operator lane.",
            "",
            "## Sources",
            "",
            f"- `{SCORECARD_JSON.relative_to(BASE)}` — inherited scorecard ranking contract",
        ]
    )
    for row in rows:
        lines.append(f"- `{row['json_path']}`")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
