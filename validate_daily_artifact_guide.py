#!/usr/bin/env python3
"""
Validation for DAILY_ARTIFACT_GUIDE.md.

Purpose:
- keep the generated daily artifact guide aligned with its generator
- stop validation-ladder guidance from disappearing on regeneration
- pin the current daily-use posture around PAPER_TRADE_NOW, the current-evidence bridge, preflight, next steps, and the validated quickstart runbook
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import daily_artifact_guide as guide

BASE = Path(__file__).resolve().parent
GENERATOR = BASE / "daily_artifact_guide.py"
DOC = BASE / "DAILY_ARTIFACT_GUIDE.md"
OUT_DIR = BASE / "out" / "status_validation" / "daily_artifact_guide"
MD_PATH = OUT_DIR / "daily_artifact_guide_validation.md"
JSON_PATH = OUT_DIR / "daily_artifact_guide_validation.json"
TMP_PARENT = OUT_DIR / "_tmp"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
SOURCE_CHAIN_JSON = BASE / "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json"
REBUILD_COMMAND = "python3 validate_daily_artifact_guide.py"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "daily artifact guide / day-to-day repo-map validator",
    "valid_evidence_scope": guide.VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "DAILY_ARTIFACT_GUIDE.md",
        "daily_artifact_guide.py",
        "latest detected daily run-root pointers",
        "documented direct-validator routes",
        "documented live scanner usage-boundary route",
        "documented EV ticket-engine usage-boundary route",
        "documented current hierarchy language / live_hierarchy validator route",
        "documented current-evidence summary bridge route",
        "current_evidence_summary.json scorecard_ci_only_promotion_check used by daily-guide current-evidence route wording",
        "current_evidence_summary.json operator_read_gate issue booleans used by daily-guide current-evidence route wording",
        "current_evidence_summary.json scorecard_audit_route used by daily-guide current-evidence route wording",
        "current_evidence_summary.json rebuild_validation_contract used by daily-guide current-evidence rebuild-order wording",
        "documented quiet-vs-broken triage paths",
        "forward_evidence_scorecard.json decision_gate_minimums used by daily-guide gate wording",
        "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json counts used by source-chain guidance wording",
    ],
    "valid_use": "daily read-order, quiet-vs-broken triage, validator-routing, and saved-artifact discoverability audit",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "daily_guide_validator_passes_are_navigation_metadata_only": True,
    "stronger_forward_confidence_requires": [
        "qualifying live paper signals",
        "ROI-complete settled paper rows",
        "settlement-quality checks",
        "other real forward observations",
    ],
    "non_goals": [
        "do not use daily-guide cleanliness as settled ROI",
        "do not use quiet-vs-broken navigation as live profitability evidence",
        "do not promote OP_REFINED_K7 or Phase 8 from daily-guide validation cleanliness",
        "do not reopen current odds-only XGBoost from daily-guide validation cleanliness",
        "do not substitute BAQ for BEL",
        "do not treat documented daily artifact paths as real-money evidence",
    ],
}


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_expected_text() -> str:
    proc = subprocess.run(
        [sys.executable, str(GENERATOR)],
        cwd=BASE,
        capture_output=True,
        text=True,
        check=True,
    )
    expected = load_text(DOC)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    return expected


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    return {"check": name, "status": "pass" if condition else "fail", "detail": detail}


def require_contains(text: str, snippet: str, name: str, detail: str) -> dict[str, Any]:
    return require(snippet in text, name, detail)


def require_paths_exist(paths: list[Path], name: str, detail: str) -> dict[str, Any]:
    missing = [str(path.relative_to(BASE)) if path.is_absolute() and BASE in path.parents else str(path) for path in paths if not path.exists()]
    return require(not missing, name, detail if not missing else f"{detail}; missing: {', '.join(missing)}")


def prepare_tmp_parent() -> Path:
    """Use project-local scratch space so guide fixture writes avoid system temp quotas."""
    if TMP_PARENT.exists():
        shutil.rmtree(TMP_PARENT)
    TMP_PARENT.mkdir(parents=True, exist_ok=True)
    return TMP_PARENT


def scorecard_gate_context() -> dict[str, Any]:
    context = guide.decision_gate_context(SCORECARD_JSON)
    return {
        "source": SCORECARD_JSON.name,
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": context.anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": context.phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": context.real_money_min,
        "real_money_no_baq_as_bel_required": context.no_baq_as_bel_required,
        "source_snippet": context.source_line,
    }


def source_chain_context() -> dict[str, Any]:
    payload = json.loads(SOURCE_CHAIN_JSON.read_text(encoding="utf-8"))
    return {
        "source": SOURCE_CHAIN_JSON.name,
        "total_guardrail_checks": int(payload["total_guardrail_checks"]),
        "total_fixture_scenarios": int(payload["total_fixture_scenarios"]),
        "total_layers": int(payload["total_layers"]),
    }


def scorecard_ci_only_context() -> dict[str, Any]:
    scorecard_payload = json.loads(SCORECARD_JSON.read_text(encoding="utf-8"))
    current_payload = json.loads((BASE / "current_evidence_summary.json").read_text(encoding="utf-8"))
    source_diagnostic = scorecard_payload.get("ci_only_promotion_diagnostics", {}).get("OP_REFINED_K7")
    current_check = current_payload.get("scorecard_ci_only_promotion_check")
    return {
        "source": guide.CI_ONLY_SOURCE,
        "candidate_rule_id": current_check.get("candidate_rule_id") if isinstance(current_check, dict) else None,
        "current_anchor_rule_id": current_check.get("current_anchor_rule_id") if isinstance(current_check, dict) else None,
        "ci_only_promotion_allowed": current_check.get("ci_only_promotion_allowed") if isinstance(current_check, dict) else None,
        "current_matches_scorecard_diagnostic": (
            isinstance(current_check, dict)
            and current_check.get("source") == guide.CI_ONLY_SOURCE
            and current_check.get("scorecard_ci_only_promotion_diagnostic") == source_diagnostic
        ),
    }


def scorecard_audit_route_context() -> dict[str, Any]:
    payload = json.loads((BASE / "current_evidence_summary.json").read_text(encoding="utf-8"))
    route = payload.get("scorecard_audit_route")
    if not isinstance(route, dict):
        raise AssertionError("current_evidence_summary.json must publish scorecard_audit_route as an object")
    return {
        "source": "current_evidence_summary.json",
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
        "route_read": route.get("route_read"),
    }


def rebuild_validation_contract_context() -> dict[str, Any]:
    payload = json.loads((BASE / "current_evidence_summary.json").read_text(encoding="utf-8"))
    contract = payload.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise AssertionError("current_evidence_summary.json must publish rebuild_validation_contract as an object")
    order = contract.get("upstream_refresh_order")
    commands = [step.get("command") for step in order] if isinstance(order, list) else []
    reasons = [step.get("reason") for step in order] if isinstance(order, list) else []
    return {
        "source": "current_evidence_summary.json",
        "source_path": "rebuild_validation_contract",
        "prerequisite_rebuild_command": contract.get("prerequisite_rebuild_command"),
        "rebuild_command": contract.get("rebuild_command"),
        "direct_validation_command": contract.get("direct_validation_command"),
        "upstream_refresh_order_commands": commands,
        "upstream_refresh_order_reasons": reasons,
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": contract.get(
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
        ),
        "requires_source_consistency_before_quoting_current_totals": contract.get(
            "requires_source_consistency_before_quoting_current_totals"
        ),
        "requires_source_freshness_before_right_now_instruction_use": contract.get(
            "requires_source_freshness_before_right_now_instruction_use"
        ),
        "upstream_refresh_order_is_provenance_metadata_only": contract.get(
            "upstream_refresh_order_is_provenance_metadata_only"
        ),
        "not_settled_roi_or_real_money_evidence": contract.get("not_settled_roi_or_real_money_evidence"),
    }


def operator_read_gate_context() -> dict[str, Any]:
    payload = json.loads((BASE / "current_evidence_summary.json").read_text(encoding="utf-8"))
    gate = payload.get("operator_read_gate")
    if not isinstance(gate, dict):
        raise AssertionError("current_evidence_summary.json must publish operator_read_gate as an object")
    if gate != payload.get("current_paper_status", {}).get("operator_read_gate"):
        raise AssertionError("current_evidence_summary.json operator_read_gate must match current_paper_status.operator_read_gate")
    for flag in (
        "has_api_access_failure_context",
        "has_scanner_failure_boundary",
        "has_stale_cache_fallback_context",
    ):
        if not isinstance(gate.get(flag), bool):
            raise AssertionError(f"current_evidence_summary.json operator_read_gate.{flag} must be boolean")
    return {
        "source": "current_evidence_summary.json",
        "source_path": "operator_read_gate",
        "gate_status": gate.get("gate_status"),
        "valid_use": gate.get("valid_use"),
        "requires_refresh_before_evidence_read": gate.get("requires_refresh_before_evidence_read"),
        "recommended_command": gate.get("recommended_command"),
        "has_api_access_failure_context": gate.get("has_api_access_failure_context"),
        "has_scanner_failure_boundary": gate.get("has_scanner_failure_boundary"),
        "has_stale_cache_fallback_context": gate.get("has_stale_cache_fallback_context"),
        "current_top_card_counts_as_no_target_evidence": gate.get("current_top_card_counts_as_no_target_evidence"),
        "current_top_card_counts_as_clean_empty_evidence": gate.get("current_top_card_counts_as_clean_empty_evidence"),
        "current_top_card_counts_as_bet_readiness_evidence": gate.get("current_top_card_counts_as_bet_readiness_evidence"),
        "current_top_card_counts_as_settled_roi_evidence": gate.get("current_top_card_counts_as_settled_roi_evidence"),
        "not_forward_performance_evidence": gate.get("not_forward_performance_evidence"),
        "not_promotion_readiness_evidence": gate.get("not_promotion_readiness_evidence"),
        "not_live_profitability_evidence": gate.get("not_live_profitability_evidence"),
        "not_real_money_evidence": gate.get("not_real_money_evidence"),
        "read": gate.get("read"),
    }


def preflight_surface_contract_checks() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="daily_guide_preflight_", dir=TMP_PARENT) as tmp_dir:
        run_root = Path(tmp_dir)
        text_path = run_root / "preflight_note.txt"
        json_path = run_root / "preflight_note.json"

        text_path.write_text("\n", encoding="utf-8")
        json_path.write_text(json.dumps({"note": "saved JSON note"}), encoding="utf-8")
        checks.append(
            require(
                guide.latest_preflight_surface(run_root) == json_path,
                "latest_preflight_prefers_json_when_text_blank",
                "latest_preflight_surface() now routes to preflight_note.json when the sibling text note exists but is blank and the JSON note is usable",
            )
        )

        text_path.write_text("saved text note\n", encoding="utf-8")
        checks.append(
            require(
                guide.latest_preflight_surface(run_root) == text_path,
                "latest_preflight_prefers_nonblank_text",
                "latest_preflight_surface() still prefers preflight_note.txt when that text artifact is readable and non-blank",
            )
        )

    return checks


def current_evidence_context_contract_checks() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="daily_guide_current_evidence_", dir=TMP_PARENT) as tmp_dir:
        bridge_path = Path(tmp_dir) / "current_evidence_summary.json"
        source_diagnostic = json.loads(SCORECARD_JSON.read_text(encoding="utf-8"))[
            "ci_only_promotion_diagnostics"
        ]["OP_REFINED_K7"]
        ci_only_check = {
            "source": guide.CI_ONLY_SOURCE,
            "candidate_rule_id": "OP_REFINED_K7",
            "current_anchor_rule_id": "OP_DURABLE_K7",
            "ci_only_promotion_allowed": False,
            "scorecard_ci_only_promotion_diagnostic": source_diagnostic,
            "read": (
                "Fixture scorecard CI-only promotion check keeps ci_only_promotion_allowed=false; "
                "positive CI is support context only."
            ),
        }
        scorecard_audit_route = {
            "markdown_path": "SCORECARD_RANKING_CONTRACT_AUDIT.md",
            "json_path": "scorecard_ranking_contract_audit.json",
            "validator_command": "python3 validate_scorecard_ranking_contract_audit.py",
            "gate_floor_source": "forward_evidence_scorecard.json:decision_gate_minimums",
            "gate_floor_snapshot": {
                "anchor_displacement_min_roi_complete_settled_observations": 30,
                "phase8_promotion_review_min_roi_complete_settled_observations": 20,
                "real_money_discussion_min_total_settled_observations_with_usable_roi": 100,
                "real_money_no_baq_as_bel_required": True,
            },
            "artifacts_present": True,
            "valid_use": "navigation route for scorecard gate/ranking/CI-only/timezone/no-BAQ synchronization checks",
            "not_forward_performance_evidence": True,
            "not_settled_roi_evidence": True,
            "not_promotion_readiness_evidence": True,
            "not_live_profitability_evidence": True,
            "not_bankroll_guidance": True,
            "not_real_money_evidence": True,
            "route_read": (
                "Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` "
                "plus `python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 "
                "gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone "
                "provenance, and no-BAQ-as-BEL prerequisite drift across report-facing surfaces."
            ),
        }
        refresh_action_boundary = {
            "command": "./run_daily_portfolio_observation.sh",
            "required_before_right_now_instruction_use": True,
            "source_action_counts_as_current_instruction_before_refresh": False,
            "wrapper_refresh_can_update_operator_surfaces": True,
            "wrapper_refresh_can_settle_open_rows_by_itself": False,
            "wrapper_refresh_counts_as_roi_complete_evidence_by_itself": False,
            "clean_empty_refresh_counts_as_forward_performance": False,
            "missing_or_invalid_artifact_counts_as_clean_quiet_day": False,
            "valid_use": "operator-card freshness and rerun routing boundary",
            "read": "Fixture refresh boundary. Treat this as operator context only.",
            "not_forward_performance_evidence": True,
            "not_promotion_readiness_evidence": True,
            "not_live_profitability_evidence": True,
            "not_real_money_evidence": True,
        }
        rebuild_validation_contract = {
            "rebuild_command": "python3 current_evidence_summary.py",
            "prerequisite_rebuild_command": "python3 paper_trade_settlement_audit.py",
            "upstream_refresh_order": [
                {
                    "order": 1,
                    "command": "python3 paper_trade_settlement_audit.py",
                    "reason": "refresh settlement-audit source fingerprints after scorecard, rules, signals, or settlement-ledger byte changes",
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
            "upstream_refresh_order_valid_use": "reproducible rebuild order for current bridge provenance after scorecard/rules/ledger byte changes",
            "direct_validation_command": "python3 validate_current_evidence_summary.py",
            "requires_source_consistency_before_quoting_current_totals": True,
            "requires_source_freshness_before_right_now_instruction_use": True,
            "upstream_refresh_order_is_provenance_metadata_only": True,
            "not_settled_roi_or_real_money_evidence": True,
        }
        base_payload: dict[str, Any] = {
            "current_paper_status": {
                "primary": {
                    "first_read": {"current": 7, "threshold": 30},
                    "portfolio_review": {"current": 7, "threshold": 100},
                    "rule_progress": [
                        {"rule_id": "OP_DURABLE_K7", "roi_complete_settled_rows": 2},
                        {"rule_id": "CD_CORE_K8", "roi_complete_settled_rows": 5},
                    ],
                    "open_settlements": 1,
                    "open_settlement_summary": "fixture-key|CD_CORE_K8|race-1|7 (CD R9, rule=CD_CORE_K8, key=7, expected_cost=210.0)",
                    "open_settlement_queue_by_rule": {
                        "open_settlement_queue_state": "open",
                        "open_settlement_context": "1 open primary settlement row(s)",
                        "detail_read": (
                            "Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); "
                            "CD_CORE_K8 has 1; other primary rules have 0; "
                            "0 open row(s) lack published rule IDs. Open rows are settlement workflow only."
                        ),
                    },
                    "recommendation_context": {
                        "read": "Fixture recommendation-state read. Treat this as operator context only.",
                    },
                }
            },
            "source_freshness": {
                "requires_refresh_before_right_now_use": False,
                "refresh_action_boundary": refresh_action_boundary,
            },
            "operator_read_gate": {
                "valid_use": "operator instruction/evidence-read gating only",
                "gate_status": "fresh_operator_read_only",
                "requires_refresh_before_evidence_read": False,
                "has_api_access_failure_context": False,
                "has_scanner_failure_boundary": False,
                "has_stale_cache_fallback_context": False,
                "read": "Fixture operator read gate. This is not no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money evidence.",
                "not_forward_performance_evidence": True,
                "not_promotion_readiness_evidence": True,
                "not_live_profitability_evidence": True,
                "not_bankroll_guidance": True,
                "not_real_money_evidence": True,
                "current_top_card_counts_as_no_target_evidence": False,
                "current_top_card_counts_as_clean_empty_evidence": False,
                "current_top_card_counts_as_bet_readiness_evidence": False,
                "current_top_card_counts_as_settled_roi_evidence": False,
            },
            "scorecard_ci_only_promotion_check": ci_only_check,
            "scorecard_audit_route": scorecard_audit_route,
            "rebuild_validation_contract": rebuild_validation_contract,
        }

        bridge_path.write_text(json.dumps(base_payload), encoding="utf-8")
        fresh_context = guide.current_evidence_context(bridge_path)
        checks.append(
            require(
                fresh_context.gate_pair == "7/30 and 7/100"
                and fresh_context.cd_rows == 5
                and fresh_context.op_rows == 2
                and "fresh against the bridge reference date" in fresh_context.source_freshness_instruction
                and "bridge generated date" not in fresh_context.source_freshness_instruction
                and "performance proof" in fresh_context.source_freshness_instruction
                and "combined `operator_status_context`" in fresh_context.combined_operator_route_instruction
                and "`operator_read_gate` / `requires_refresh_before_evidence_read` route" in fresh_context.combined_operator_route_instruction
                and "fresh against the bridge reference date" in fresh_context.combined_operator_route_instruction
                and "performance proof" in fresh_context.combined_operator_route_instruction
                and "operator instruction/evidence gating only" in fresh_context.operator_read_gate_phrase
                and "not no-target, clean-empty, bet-readiness, settled ROI" in fresh_context.operator_read_gate_phrase
                and "source-published settlement queue state `open`" in fresh_context.open_row_context_phrase
                and "1 open primary settlement row(s)" in fresh_context.open_row_context_phrase
                and "Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s)" in fresh_context.open_row_context_phrase
                and "fixture-key|CD_CORE_K8|race-1|7" in fresh_context.open_row_context_phrase
                and "latest recommendation-state context (Fixture recommendation-state read." in fresh_context.open_row_context_phrase
                and "not bet-ready or forward-performance evidence" in fresh_context.open_row_context_phrase
                and fresh_context.bridge_queue_navigation == "open settlement-queue plus recommendation-state context"
                and fresh_context.ci_only_source == guide.CI_ONLY_SOURCE
                and fresh_context.ci_only_allowed is False
                and "ci_only_promotion_allowed=false" in fresh_context.ci_only_phrase
                and "current-paper promotion trigger" in fresh_context.ci_only_phrase
                and "`scorecard_audit_route` to `SCORECARD_RANKING_CONTRACT_AUDIT.md`" in fresh_context.scorecard_audit_route_phrase
                and "copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks" in fresh_context.scorecard_audit_route_phrase
                and "report-synchronization metadata only" in fresh_context.scorecard_audit_route_phrase
                and "`rebuild_validation_contract` for source-byte changes" in fresh_context.rebuild_order_phrase
                and "`python3 paper_trade_settlement_audit.py`, then `python3 current_evidence_summary.py`, then `python3 validate_current_evidence_summary.py`" in fresh_context.rebuild_order_phrase
                and "provenance/rebuild metadata only" in fresh_context.rebuild_order_phrase,
                "current_evidence_context_reads_fresh_branch",
                "current_evidence_context() derives gate counts, rule rows, bridge-reference fresh-card wording, source-published queue-state/detail plus recommendation-state context, source-matched OP_REFINED CI-only wording, scorecard_audit_route wording, and rebuild_validation_contract order from current_evidence_summary.json instead of hardcoded guide text",
            )
        )

        base_payload["source_freshness"]["requires_refresh_before_right_now_use"] = True
        bridge_path.write_text(json.dumps(base_payload), encoding="utf-8")
        stale_context = guide.current_evidence_context(bridge_path)
        checks.append(
            require(
                stale_context.gate_pair == "7/30 and 7/100"
                and "rerun `./run_daily_portfolio_observation.sh`" in stale_context.source_freshness_instruction
                and "stale best-action card" in stale_context.source_freshness_instruction
                and "combined `operator_status_context`" in stale_context.combined_operator_route_instruction
                and "`source_freshness` / `requires_refresh_before_right_now_use`" in stale_context.combined_operator_route_instruction
                and "`operator_read_gate` / `requires_refresh_before_evidence_read` route" in stale_context.combined_operator_route_instruction
                and "stale/API-failure best-action card" in stale_context.combined_operator_route_instruction,
                "current_evidence_context_reads_stale_branch",
                "current_evidence_context() derives stale-card combined operator_status_context/source_freshness/operator_read_gate refresh wording from current_evidence_summary.json instead of assuming today's freshness state or splitting the read route",
            )
        )

        closed_payload = json.loads(json.dumps(base_payload))
        closed_payload["current_paper_status"]["primary"]["open_settlements"] = 0
        closed_payload["current_paper_status"]["primary"]["open_settlement_summary"] = "none"
        closed_payload["current_paper_status"]["primary"]["open_settlement_queue_by_rule"] = {
            "open_settlement_queue_state": "closed",
            "open_settlement_context": "no open primary settlement rows",
            "detail_read": (
                "Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); "
                "CD_CORE_K8 has 0; other primary rules have 0; "
                "0 open row(s) lack published rule IDs. Open rows are settlement workflow only."
            ),
        }
        closed_payload["current_paper_status"]["primary"]["recommendation_context"]["read"] = (
            "Fixture closed-queue API-access recommendation read. "
            "Sidecar action: refresh_daily_wrapper_before_evidence_read. "
            "Recheck command: ./run_daily_portfolio_observation.sh. "
            "Use recommendation and settlement ledgers before interpreting bet readiness or forward performance."
        )
        bridge_path.write_text(json.dumps(closed_payload), encoding="utf-8")
        closed_context = guide.current_evidence_context(bridge_path)
        checks.append(
            require(
                closed_context.bridge_queue_navigation == "closed settlement-queue plus recommendation-state context"
                and "source-published settlement queue state `closed`" in closed_context.open_row_context_phrase
                and "no open primary settlement rows" in closed_context.open_row_context_phrase
                and "Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s)" in closed_context.open_row_context_phrase
                and "fixture-key|CD_CORE_K8|race-1|7" not in closed_context.open_row_context_phrase
                and "Sidecar action: refresh_daily_wrapper_before_evidence_read" in closed_context.open_row_context_phrase
                and "Recheck command: ./run_daily_portfolio_observation.sh" in closed_context.open_row_context_phrase
                and "not bet-ready or forward-performance evidence" in closed_context.open_row_context_phrase,
                "current_evidence_context_reads_closed_queue_branch",
                "current_evidence_context() treats open_settlements=0 plus source-published open_settlement_queue_state=closed as a closed settlement queue while preserving recommendation-state action/recheck context",
            )
        )

        bad_payload = json.loads(json.dumps(base_payload))
        bad_payload["source_freshness"]["refresh_action_boundary"]["clean_empty_refresh_counts_as_forward_performance"] = True
        bridge_path.write_text(json.dumps(bad_payload), encoding="utf-8")
        bad_out = Path(tmp_dir) / "nested" / "DAILY_ARTIFACT_GUIDE.md"
        proc = subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--current-evidence-json",
                str(bridge_path),
                "--out-md",
                str(bad_out),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out.parent.exists()
                and not bad_out.exists()
                and "clean_empty_refresh_counts_as_forward_performance=false" in proc.stderr,
                "current_evidence_refresh_accounting_fails_before_artifacts",
                "daily_artifact_guide.py rejects a current-evidence bridge that treats a clean empty wrapper refresh as forward performance before creating nested output directories or partial guide artifacts",
            )
        )

        bad_payload = json.loads(json.dumps(base_payload))
        bad_payload.pop("scorecard_ci_only_promotion_check", None)
        bridge_path.write_text(json.dumps(bad_payload), encoding="utf-8")
        bad_out = Path(tmp_dir) / "ci_nested" / "DAILY_ARTIFACT_GUIDE.md"
        proc = subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--current-evidence-json",
                str(bridge_path),
                "--out-md",
                str(bad_out),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out.parent.exists()
                and not bad_out.exists()
                and "scorecard_ci_only_promotion_check" in proc.stderr,
                "current_evidence_ci_only_missing_fails_before_artifacts",
                "daily_artifact_guide.py rejects a current-evidence bridge missing the scorecard-sourced OP_REFINED CI-only diagnostic before creating nested output directories or partial guide artifacts",
            )
        )

        bad_payload = json.loads(json.dumps(base_payload))
        bad_payload.pop("scorecard_audit_route", None)
        bridge_path.write_text(json.dumps(bad_payload), encoding="utf-8")
        bad_out = Path(tmp_dir) / "audit_nested" / "DAILY_ARTIFACT_GUIDE.md"
        proc = subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--current-evidence-json",
                str(bridge_path),
                "--out-md",
                str(bad_out),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out.parent.exists()
                and not bad_out.exists()
                and "scorecard_audit_route" in proc.stderr,
                "current_evidence_scorecard_audit_route_missing_fails_before_artifacts",
                "daily_artifact_guide.py rejects a current-evidence bridge missing the scorecard-audit route before creating nested output directories or partial guide artifacts",
            )
        )

        bad_payload = json.loads(json.dumps(base_payload))
        bad_payload.pop("rebuild_validation_contract", None)
        bridge_path.write_text(json.dumps(bad_payload), encoding="utf-8")
        bad_out = Path(tmp_dir) / "rebuild_nested" / "DAILY_ARTIFACT_GUIDE.md"
        proc = subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--current-evidence-json",
                str(bridge_path),
                "--out-md",
                str(bad_out),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out.parent.exists()
                and not bad_out.exists()
                and "rebuild_validation_contract" in proc.stderr,
                "current_evidence_rebuild_order_missing_fails_before_artifacts",
                "daily_artifact_guide.py rejects a current-evidence bridge missing the upstream rebuild-order contract before creating nested output directories or partial guide artifacts",
            )
        )

        bad_payload = json.loads(json.dumps(base_payload))
        bad_payload["rebuild_validation_contract"]["upstream_refresh_order_is_provenance_metadata_only"] = False
        bridge_path.write_text(json.dumps(bad_payload), encoding="utf-8")
        bad_out = Path(tmp_dir) / "rebuild_weakened_nested" / "DAILY_ARTIFACT_GUIDE.md"
        proc = subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--current-evidence-json",
                str(bridge_path),
                "--out-md",
                str(bad_out),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out.parent.exists()
                and not bad_out.exists()
                and "provenance metadata only" in proc.stderr,
                "current_evidence_rebuild_order_weakened_fails_before_artifacts",
                "daily_artifact_guide.py rejects a current-evidence bridge whose rebuild-order contract no longer stays provenance metadata only before creating nested output directories or partial guide artifacts",
            )
        )

    return checks


def decision_gate_context_contract_checks() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="daily_guide_scorecard_gates_", dir=TMP_PARENT) as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(SCORECARD_JSON.read_text(encoding="utf-8"))
        scorecard_path = tmp_root / "forward_evidence_scorecard.json"
        bad_out = tmp_root / "nested" / "DAILY_ARTIFACT_GUIDE.md"

        bool_payload = json.loads(json.dumps(base_payload))
        bool_payload["decision_gate_minimums"]["anchor_displacement"][
            "min_roi_complete_settled_observations"
        ] = True
        scorecard_path.write_text(json.dumps(bool_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--scorecard-json",
                str(scorecard_path),
                "--out-md",
                str(bad_out),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out.parent.exists()
                and not bad_out.exists()
                and "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations must be a positive non-boolean integer" in proc.stderr,
                "decision_gate_boolean_floor_fails_before_artifacts",
                "daily_artifact_guide.py rejects a boolean scorecard anchor-displacement gate before creating nested output directories or partial guide artifacts",
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
                str(GENERATOR),
                "--scorecard-json",
                str(scorecard_path),
                "--out-md",
                str(bad_out),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out.parent.exists()
                and not bad_out.exists()
                and "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer" in proc.stderr,
                "decision_gate_nonpositive_phase8_floor_fails_before_artifacts",
                "daily_artifact_guide.py rejects a non-positive Phase 8 promotion-review scorecard gate before creating nested output directories or partial guide artifacts",
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
                str(GENERATOR),
                "--scorecard-json",
                str(scorecard_path),
                "--out-md",
                str(bad_out),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out.parent.exists()
                and not bad_out.exists()
                and "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer" in proc.stderr,
                "decision_gate_nonpositive_real_money_floor_fails_before_artifacts",
                "daily_artifact_guide.py rejects a non-positive real-money discussion scorecard gate before creating nested output directories or partial guide artifacts",
            )
        )

        missing_no_baq_payload = json.loads(json.dumps(base_payload))
        missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"]["also_requires"] = [
            requirement
            for requirement in missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"].get(
                "also_requires",
                [],
            )
            if requirement != "no BAQ-as-BEL substitution"
        ]
        scorecard_path.write_text(json.dumps(missing_no_baq_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--scorecard-json",
                str(scorecard_path),
                "--out-md",
                str(bad_out),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out.parent.exists()
                and not bad_out.exists()
                and "decision_gate_minimums.real_money_discussion.also_requires must include no BAQ-as-BEL substitution" in proc.stderr,
                "decision_gate_missing_no_baq_fails_before_artifacts",
                "daily_artifact_guide.py rejects a scorecard real-money gate that drops the no-BAQ-as-BEL prerequisite before creating nested output directories or partial guide artifacts",
            )
        )

    return checks


def build_checks(actual: str, expected: str) -> list[dict[str, Any]]:
    latest = guide.latest_run_root()
    latest_label = guide.rel(latest) if latest else "none yet"
    latest_daily = latest / "daily_summary.txt" if latest else BASE / "out" / "daily_portfolio_runs" / "YYYY-MM-DD" / "daily_summary.txt"
    latest_preflight = guide.latest_preflight_surface(latest)
    latest_primary_monitor = latest / "phase7_current_paper" / "lane_monitor.md" if latest else BASE / "out" / "daily_portfolio_runs" / "YYYY-MM-DD" / "phase7_current_paper" / "lane_monitor.md"
    latest_shadow_monitor = latest / "phase8_shadow" / "lane_monitor.md" if latest else BASE / "out" / "daily_portfolio_runs" / "YYYY-MM-DD" / "phase8_shadow" / "lane_monitor.md"
    latest_primary_next = latest / "phase7_current_paper" / "next_steps.md" if latest else BASE / "out" / "daily_portfolio_runs" / "YYYY-MM-DD" / "phase7_current_paper" / "next_steps.md"
    latest_shadow_next = latest / "phase8_shadow" / "next_steps.md" if latest else BASE / "out" / "daily_portfolio_runs" / "YYYY-MM-DD" / "phase8_shadow" / "next_steps.md"
    latest_primary_forward = latest / "phase7_current_paper" / "forward_check.md" if latest else BASE / "out" / "daily_portfolio_runs" / "YYYY-MM-DD" / "phase7_current_paper" / "forward_check.md"
    latest_shadow_forward = latest / "phase8_shadow" / "forward_check.md" if latest else BASE / "out" / "daily_portfolio_runs" / "YYYY-MM-DD" / "phase8_shadow" / "forward_check.md"
    current_context = guide.current_evidence_context()
    scorecard_gates = scorecard_gate_context()
    ci_only_context = scorecard_ci_only_context()
    operator_gate = operator_read_gate_context()
    scorecard_audit_route = scorecard_audit_route_context()
    rebuild_contract = rebuild_validation_contract_context()
    source_chain = source_chain_context()

    return [
        *preflight_surface_contract_checks(),
        *current_evidence_context_contract_checks(),
        *decision_gate_context_contract_checks(),
        require(
            actual == expected,
            "guide_matches_generator",
            "DAILY_ARTIFACT_GUIDE.md still matches a fresh rebuild from daily_artifact_guide.py",
        ),
        require(
            "not the cleanest current-paper entrypoint" in actual
            and "not the cleanest live-paper entrypoint" not in actual,
            "legacy_phase7_current_paper_entrypoint_wording",
            "daily guide now labels the legacy Phase 7 rules file as reference-only rather than the cleanest current-paper entrypoint, avoiding live-paper shorthand",
        ),
        require_contains(
            actual,
            "## Validation after edits",
            "validation_section_present",
            "the generated guide still includes the validation ladder section",
        ),
        require_contains(
            actual,
            f"Valid evidence scope: `valid_evidence_scope={guide.VALID_EVIDENCE_SCOPE}`. This guide is navigation, triage, and validator-routing metadata only; it is not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            "daily_guide_source_exposes_valid_evidence_scope",
            "the generated daily guide now exposes its raw valid_evidence_scope line so copied navigation/runbook snippets cannot be mistaken for settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
        ),
        require(
            f"- run `python3 validate_paper_trade_source_chain_guardrails.py` when the question is whether the compact `PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md` / `.json` matrix still source-matches the scan -> recommend -> size -> log validators plus their source/validator scripts, matrix generator/validator tooling, validated matrix markdown/JSON artifact fingerprints, and live-scanner source-boundary contract, preserves {source_chain['total_guardrail_checks']} guardrails across {source_chain['total_fixture_scenarios']} fixture scenarios, renders markdown fingerprint tables exactly from the JSON sidecar, and stays operational reproducibility/readiness only rather than new forward evidence" in actual
            and "After the source-chain matrix is fresh, use `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json` and `python3 validate_project_surfaces.py --reuse-existing-child-json` only as parent propagation checks" in actual
            and "the operator suite should keep the embedded `auxiliary_source_chain_matrix`, confirm the matrix artifact fingerprints still match disk, and recompute the matrix payload from current source-layer inputs plus the live-scanner boundary contract before accepting reused child JSON" in actual
            and f"the project sweep should verify that source-matched {source_chain['total_guardrail_checks']}-guardrail audit instead of flattening scan/recommend/size/log into one umbrella green light" in actual
            and "- run `python3 validate_scanner_sidecar_resolution_contract.py` when the question is specifically whether a pipeline-declared `scanner_status_path` stays authoritative over stale default `live_scan.status.json` files across status summary, next steps, `PAPER_TRADE_NOW`, `OPS_HISTORY`, and saved-live refresh, including HTTP 403 action/recheck preservation; this is routing-fixture metadata only, not a quiet-day, settled-ROI, promotion, live-profitability, bankroll, or real-money signal" in actual
            and "this remains operational reproducibility/readiness only, not ROI or promotion evidence" in actual,
            "source_chain_matrix_shortcut_present",
            "the validation ladder now points compact scan/recommend/size/log matrix questions to the dedicated source-chain guardrail validator before readers drill into individual source-layer leaves, exposes the narrow scanner-sidecar resolution route for copied-sidecar issues, then explains how parent operator/project rollups should preserve the embedded source-chain matrix, live-scanner boundary contract, and recompute payload parity as propagation/readiness metadata rather than flattening it into one umbrella green light",
        ),
        require(
            f"{source_chain['total_guardrail_checks']} guardrails across {source_chain['total_fixture_scenarios']} fixture scenarios" in actual
            and f"and {source_chain['total_guardrail_checks']} guardrails" in actual
            and "24 guardrails across 43 fixture scenarios" not in actual
            and "source-matched 24-guardrail" not in actual
            and "and 24 guardrails" not in actual,
            "source_chain_guardrail_count_matches_matrix_json",
            "daily artifact guide now reads the source-chain matrix count from PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json and fails if the saved guide drifts back to stale 24-guardrail wording",
        ),
        require_contains(
            actual,
            "   - run `python3 validate_current_hierarchy_language.py` when the question is specifically the live hierarchy wording, `live_hierarchy`, `primary_companion`, or legacy `primary_shadow` keys across the right-now / daily-summary / front-door surfaces; a green read is hierarchy wording / metadata routing only, not ROI, promotion, live-profitability, or real-money evidence",
            "current_hierarchy_validator_command",
            "the validation ladder now points live hierarchy wording and structured-key edits to the dedicated current-hierarchy validator before readers broaden to top-card, wrapper, or project sweeps",
        ),
        require_contains(
            actual,
            "- run `python3 validate_forward_evidence_scorecard.py` for scorecard ordering, tiering, or rendered-text changes",
            "scorecard_validator_command",
            "the validation ladder still points scorecard-only edits to the dedicated direct validator",
        ),
        require_contains(
            actual,
            "   - run `python3 validate_current_evidence_summary.py` for `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` / `current_evidence_summary.py` current-paper bridge, source-consistency, source-freshness, operator-read-gate routing, scanner/API-failure recommendation-context wording, scorecard-sourced OP_REFINED CI-only routing, scorecard_audit_route synchronization-routing, or rebuild_validation_contract order changes",
            "current_evidence_validator_command",
            "the validation ladder now points current-evidence bridge, source-consistency, source-freshness, operator-read-gate routing, scanner/API-failure recommendation-context wording, scorecard-sourced OP_REFINED CI-only routing, scorecard_audit_route synchronization-routing, and rebuild_validation_contract order edits to the dedicated validator before broader decision-card or project sweeps",
        ),
        require_contains(
            actual,
            "2. **Direct preflight-note surface change**",
            "preflight_note_ladder_step",
            "the validation ladder still includes the dedicated direct preflight-note step after the broader operator-suite route",
        ),
        require_contains(
            actual,
            "   - run `python3 validate_paper_trade_preflight_note.py` when the question is specifically the shared calendar note or its JSON / text active-target, no-target, API-unreachable, and explicit-error branches",
            "preflight_note_validator_command",
            "the validation ladder still points shared preflight-note edits to the dedicated direct validator",
        ),
        require_contains(
            actual,
            "3. **Direct base status-summary surface change**",
            "status_summary_ladder_step",
            "the validation ladder still includes the dedicated direct status-summary step after the direct preflight-note route",
        ),
        require_contains(
            actual,
            "- run `python3 validate_paper_trade_status_summary.py` when the question is specifically the one-line base lane summary or its text/JSON cache, alert, scanner/API-access failure, and other failure branches before lane enrichment, including API-access / HTTP 403 action-recheck route preservation with `refresh_daily_wrapper_before_evidence_read` plus `./run_daily_portfolio_observation.sh` as operator context only, stale-cache fallback count/kind/error visibility, missing-scan-output fallbacks, empty/unreadable scanner sidecars, pipeline-recorded empty/unreadable scanner-status states, wrapper-only required-pipeline missing/empty/unreadable sidecars, and saved recommender/logger failure lines that should keep stage / error type / detail visible",
            "status_summary_validator_command",
            "the validation ladder still points one-line base lane summary edits to the dedicated direct validator, including API-access / HTTP 403 action-recheck route preservation, stale-cache fallback metadata, empty/unreadable scanner sidecars, pipeline-recorded scanner-status states, wrapper-only required-pipeline sidecar branches, and the saved recommender/logger failure-detail line",
        ),
        require_contains(
            actual,
            "4. **Direct settlement-sync surface change**",
            "settlement_sync_ladder_step",
            "the validation ladder still includes the dedicated direct settlement-sync step after the direct status-summary route",
        ),
        require_contains(
            actual,
            "   - run `python3 validate_paper_trade_settlement_sync.py` when the question is specifically the settlement-template sync helper or its real-CLI stable-header, one-open-row-per-live-signal-key, preserved-manual-settlement, refreshed-metadata, blank and duplicate signal-key skip, blank settlement-key drop, and orphan-row cleanup branches",
            "settlement_sync_validator_command",
            "the validation ladder still points settlement-template sync edits to the dedicated direct validator, including the three cleanup-count branches",
        ),
        require_contains(
            actual,
            "5. **Direct settlement-helper / settlement-audit surface change**",
            "settlement_helper_ladder_step",
            "the validation ladder still includes the dedicated direct settlement-helper / settlement-audit step after the direct settlement-sync route",
        ),
        require_contains(
            actual,
            "   - run `python3 validate_paper_trade_settlement_helper.py` when the question is specifically the manual settlement-entry flow or its text / markdown / JSON open-queue rendering, separate settled-row ROI-gap visibility, queue truncation, exact one-row settlement updates, duplicate signal-key rejection before mutation, settlement cost-source reporting, expected-cost fallback, supplied settled_ts validation, timestamp-omission ROI-gate warnings, true missing/malformed-cost handling, computed profit, and missing-signal failure branches\n   - run `python3 validate_paper_trade_settlement_audit.py` when the question is specifically the ledger-completeness / ROI-coverage audit, its primary/shadow `next_action` / `next_action_reason` routing, blank signal-key versus blank settlement-key repair labeling, duplicate custom lane-name rejection before output artifacts, ROI-complete row counting, or its no-new-forward-evidence boundary",
            "settlement_helper_validator_command",
            "the validation ladder still points manual settlement-entry edits to the dedicated direct validator and now points ledger-completeness / ROI-coverage audit edits to the direct settlement-audit validator",
        ),
        require_contains(
            actual,
            "6. **Direct next-steps surface change**",
            "next_steps_ladder_step",
            "the validation ladder still includes the dedicated direct next-steps step after the direct settlement-helper route",
        ),
        require_contains(
            actual,
            "   - run `python3 validate_paper_trade_next_steps.py` when the question is specifically the exact next command guidance or its JSON / text / markdown settlement-first, missing scan-output refresh-artifacts, API-access stale-cache fallback, rerun-live, limited-cache, explicit recommender/logger pipeline-failure recovery, waiting-for-first-settled, collecting-sample, and decision-grade-review branches",
            "next_steps_validator_command",
            "the validation ladder still points exact next-command edits to the dedicated direct validator, including explicit pipeline-failure recovery branches",
        ),
        require_contains(
            actual,
            "7. **Direct frozen-baseline forward-check surface change**",
            "forward_check_ladder_step",
            "the validation ladder still includes the dedicated direct forward-check step after the direct next-steps route",
        ),
        require_contains(
            actual,
            "- run `python3 validate_paper_trade_forward_check.py` when the question is specifically the per-lane forward assessment or its JSON / text / markdown no-data, too-early, within-noise, running-cold, running-hot, no-baseline, recommendation-flow, ROI-fallback, ROI cost-source, malformed actual-cost gap, and no-overpromotion decision-gate branches",
            "forward_check_validator_command",
            "the validation ladder still points per-lane forward-check edits to the dedicated direct validator",
        ),
        require_contains(
            actual,
            "8. **Direct compact lane-monitor surface change**",
            "lane_monitor_ladder_step",
            "the validation ladder still includes the dedicated direct lane-monitor step after the direct forward-check route",
        ),
        require_contains(
            actual,
            "- run `python3 validate_paper_trade_lane_monitor.py` when the question is specifically the compact per-lane monitor or its JSON / text / markdown forward-assessment, no-overpromotion decision-gate, queue, truncation, and ROI-detail branches",
            "lane_monitor_validator_command",
            "the validation ladder still points compact per-lane monitor edits to the dedicated direct validator",
        ),
        require_contains(
            actual,
            "9. **Direct combined daily-summary surface change**",
            "daily_summary_ladder_step",
            "the validation ladder still includes the dedicated direct daily-summary step after the direct lane-monitor route",
        ),
        require_contains(
            actual,
            "- run `python3 validate_paper_trade_daily_summary.py` when the question is specifically the combined `daily_summary.txt` full routed quick-jump bundle, routed top-card focus/timing/freshness/ops snapshot, explicit primary/shadow recent-run context lines, explicit primary/shadow next-step state lines plus settlement-audit action lines and lifted no-overpromotion decision-gate snapshot lines, first-read and broader-review readiness lines, lane sections, artifacts-root line, explicit recommender/logger failure context, pipeline-recorded scanner-status issue lines, or missing-preflight / missing-lane placeholders",
            "daily_summary_validator_command",
            "the validation ladder still points combined daily-summary edits to the dedicated direct validator at the full routed quick-jump-bundle level, including the routed top-card snapshot, explicit recent-run context, next-step state lines, settlement-audit action lines, lifted decision-gate snapshot lines, first-read vs broader-review readiness lines, and pipeline-failure context",
        ),
        require_contains(
            actual,
            "10. **Direct per-lane summary surface change**",
            "lane_summary_ladder_step",
            "the validation ladder still includes the dedicated direct lane-summary step after the direct daily-summary route",
        ),
        require_contains(
            actual,
            "- run `python3 validate_paper_trade_lane_summary.py` when the question is specifically one lane `summary.txt` surface, including its full routed quick-files bundle, no-overpromotion decision-gate snapshot line, missing scan-output fallback context, pipeline-recorded scanner-status base headlines, section layout, placeholders, or temp-write display path handling",
            "lane_summary_validator_command",
            "the validation ladder still points per-lane summary edits to the dedicated direct validator at the full routed quick-files-bundle level",
        ),
        require(
            "   - treat that suite as an operator-surface alignment/readiness sweep, not as new forward evidence by itself" in actual
            and "   - run `python3 validate_cache_only_messaging.py` or `python3 validate_partial_cache_messaging.py` first when the question is specifically cache-only-miss or partial-cache operator messaging; green passes prove cache-edge routing / reproducibility toward refresh or rerun only, not quiet-day, current scanner, settled ROI, live profitability, promotion, or real-money evidence" in actual,
            "operator_suite_alignment_note",
            "the validation ladder now says explicitly that the umbrella operator-suite route is an alignment/readiness sweep rather than new forward evidence, and routes cache-only/partial-cache wording edits to their direct validators with the cache-edge-only evidence boundary",
        ),
        require_contains(
            actual,
            "- if saved live paper-trade artifacts drift only because helper/render logic changed underneath them, rebuild first with `python3 refresh_live_paper_trade_surfaces.py` and then check that rebuild path directly with `python3 validate_refresh_live_paper_trade_surfaces.py`; that refresh path now also proves missing scan-output context survives rebuilt per-run surfaces, rebuilt `PAPER_TRADE_NOW.json` parity, rebuilt `CURRENT_EVIDENCE_SUMMARY` bridge surfaces preserve `current_evidence_summary.json.rebuild_validation_contract`, rebuilt daily summaries inherit the routed top-card focus/timing/freshness/ops snapshot from the refreshed top-level surfaces, keeps `--latest-only` confined to the newest copied run's preflight, lane, and daily-summary surfaces, keeps `--skip-top-level` confined to leaving `OPS_HISTORY` / matched `PAPER_TRADE_NOW` / `CURRENT_EVIDENCE_SUMMARY` outputs untouched while still rebuilding those per-run surfaces against the existing top-level outputs, and if you add `--as-of-date YYYY-MM-DD` the helper now says whether that freshness pin was actually applied or skipped (including when top-level refresh was skipped)",
            "refresh_helper_ladder_step",
            "the validation ladder now includes the saved-live refresh path when helper/render logic changes underneath persisted operator artifacts, including rebuilt PAPER_TRADE_NOW.json parity, rebuilt daily-summary top-card snapshot inheritance, the distinct skip-top-level top-card-preservation boundary, and explicit as-of-date applied-vs-skipped stdout behavior",
        ),
        require_contains(
            actual,
            "- if the question is specifically the real shell wrapper's fallback/rebuild orchestration, including wrapper-generated `CURRENT_EVIDENCE_SUMMARY` refresh/placeholder behavior, source-backed recommendation-context/open-row separation, and direct scorecard-sourced 30/20/100 gate-boundary publication, run `python3 validate_run_daily_portfolio_observation.py`; the refresh-helper and daily-wrapper validators are the leaf source-of-truth reports for those wrapper contracts, and the broader operator/project sweeps should preserve their inherited wrapper-guardrail inventories instead of flattening them into one umbrella pass count",
            "daily_wrapper_leaf_guardrail_note_present",
            "the validation ladder now points wrapper-fallback/current-evidence bridge and direct scorecard gate-boundary questions to the real daily-wrapper validator and says the refresh-helper plus daily-wrapper leaves are the source-of-truth wrapper-guardrail reports broader sweeps must preserve",
        ),
        require_contains(
            actual,
            "- a passing refresh only means the saved surfaces were rerendered from existing artifacts; it is not a new paper-trade outcome or a new forward-observation result",
            "refresh_helper_not_new_evidence_note",
            "the validation ladder now says explicitly that a passing saved-live refresh is only a rerender of existing artifacts, not a new forward result",
        ),
        require_contains(
            actual,
            "12. **Main/narrow comparison artifact change**",
            "narrow_comparison_ladder_step",
            "the validation ladder still includes the dedicated main/narrow-comparison step",
        ),
        require_contains(
            actual,
            "- run `python3 validate_compare_main_approaches.py` for Cole's one-screen comparison read, matched CSV/markdown/JSON bundle, current paper ladder, evidence-class triage, method-family comparison, or evidence-scope decision-change gates",
            "compare_main_validator_command",
            "the validation ladder now points main-comparison report edits to the dedicated validator before widening to parent research rollups",
        ),
        require_contains(
            actual,
            "- run `python3 validate_op_anchor_method_comparison.py` for the OP vs Harville vs parked-odds-only-XGBoost evidence-class comparison and OP-anchor markdown/JSON source-fingerprint plus readable `evidence_boundary_text` contract",
            "op_anchor_validator_command",
            "the validation ladder still points OP-centered comparison edits and OP-anchor source-fingerprint questions to the dedicated validator",
        ),
        require_contains(
            actual,
            "- run `python3 validate_cross_family_decision.py` when the anchor / paper / watch shortlist wording or current-paper snapshot caveat changes, including stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and the no OP-anchor / no cross-family-promotion evidence boundary",
            "cross_family_current_paper_validator_command",
            "the validation ladder now points cross-family shortlist and current-paper snapshot caveat edits to the dedicated cross-family validator",
        ),
        require_contains(
            actual,
            "- run `python3 validate_ab_downstream_comparison.py` for the downstream baseline-vs-enriched-horse-history XGBoost guardrail artifact, including saved JSON/markdown parity, dynamic hierarchy rerendering, and source-aware full-CLI `PASS` versus missing-input `SKIP` reporting",
            "ab_downstream_validator_command",
            "the validation ladder still points downstream A/B edits to the dedicated validator",
        ),
        require_contains(
            actual,
            "- run `python3 validate_full_data_retrain_artifacts.py` when the question is specifically the full-data XGBoost retrain artifact, exact retrain/prediction commands, or the model-fit-diagnostic-only boundary",
            "full_data_retrain_validator_command",
            "the validation ladder now points full-data retrain artifact, exact retrain/prediction command, and model-fit-only boundary edits to the dedicated validator",
        ),
        require_contains(
            actual,
            "- run `python3 validate_compare_recommender_scope_paths.py` for selective-vs-widened recommender scope guardrails",
            "recommender_scope_validator_command",
            "the validation ladder still points recommender-scope edits to the dedicated validator",
        ),
        require_contains(
            actual,
            "- if the underlying child validator outputs are already fresh and the edit only touched a parent rollup or top-level wording, the smaller honest reruns are `python3 validate_decision_cards_suite.py --reuse-existing-child-json`, `python3 validate_frozen_evidence_chain.py --reuse-existing-child-json`, `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json`, `python3 validate_report_surfaces.py --reuse-existing-child-json`, or `python3 validate_project_surfaces.py --reuse-existing-child-json`",
            "reuse_shortcut_ladder_note",
            "the validation ladder now keeps the parent-rollup artifact-reuse shortcut visible for top-level wording or parent-only edits when the child validator outputs are already fresh",
        ),
        require_contains(
            actual,
            "- after a settlement-audit -> current-bridge rebuild, validate the copied-current-paper fanout before quoting report-facing comparisons: frozen replay, downstream A/B, compare-main, OP-anchor, OP-family, cross-family, method-family, portfolio, selective-scope, scorecard audit, frozen evidence chain, report surfaces, and project surfaces; green rebuilds are drift prevention only, not evidence movement",
            "current_bridge_fanout_ladder_note",
            "the validation ladder now names the copied-current-paper comparison fanout that should be checked after a settlement-audit to current-bridge rebuild before report-facing comparisons are quoted",
        ),
        require_contains(
            actual,
            "13. **Dated live/demo-vs-production note change**",
            "working_status_ladder_step",
            "the validation ladder still includes the dedicated working-status step after the narrow-comparison layer",
        ),
        require_contains(
            actual,
            "- run `python3 validate_working_status_report.py` when the working-status note or its stable-vs-mutable demo evidence framing changed",
            "working_status_validator_command",
            "the validation ladder still points dated live/demo-vs-production edits to the direct working-status validator",
        ),
        require_contains(
            actual,
            "14. **Shareable wording / presentation / report-trust-path change**",
            "report_surfaces_ladder_step",
            "the validation ladder still includes the dedicated report-surfaces step after the working-status layer",
        ),
        require_contains(
            actual,
            "- run `python3 validate_report_surfaces.py` when the question is specifically README, long-form report, working-status note, presentation outline, or shareable HTML wording drift, including whether the narrative report sweep still preserves the README-inherited wrapper-leaf source-of-truth note instead of flattening it away",
            "report_surfaces_validator_command",
            "the validation ladder still points shareable wording, presentation, and report-trust-path edits to the direct report-surfaces validator, including the inherited README wrapper-note preservation question",
        ),
        require_contains(
            actual,
            "15. **Validation runbook, broader operator-suite route, direct source-layer route guidance, parent-rollup reuse shortcut guardrail, documented output paths, or dated-report / legacy-alias policy change**",
            "quickstart_ladder_step",
            "the validation ladder still includes the dedicated quickstart/broader-operator-route/direct-route/reuse-guardrail/output-path/dated-report-policy step after the report-surfaces layer",
        ),
        require_contains(
            actual,
            "- run `python3 validate_validation_quickstart.py`",
            "quickstart_validator_command",
            "the validation ladder still points runbook/broader-operator-route/direct-route/reuse-guardrail/output-path/dated-report-policy edits to validate_validation_quickstart.py",
        ),
        require_contains(
            actual,
            "16. **Cross-layer or broad change**",
            "project_surfaces_ladder_step",
            "the validation ladder still includes the dedicated broad top-level project-sweep step before the fallback read-the-quickstart note",
        ),
        require_contains(
            actual,
            "   - run `python3 validate_project_surfaces.py`",
            "project_surfaces_validator_command",
            "the validation ladder still points broad changes to the top-level project sweep",
        ),
        require_contains(
            actual,
            "   - treat that top-level sweep as the best cross-layer alignment answer for a broad change, including the direct current-hierarchy child validator, not as new forward evidence by itself",
            "project_surfaces_alignment_note",
            "the validation ladder now says explicitly that the top-level project sweep is a cross-layer alignment answer rather than new forward evidence and includes the direct current-hierarchy child validator",
        ),
        require_contains(
            actual,
            f"Latest detected daily run root: `{latest_label}`",
            "latest_run_root_line",
            "the guide still names the actual latest detected daily run root instead of a stale handwritten path",
        ),
        require_contains(
            actual,
            "## Quiet day vs broken day cheat sheet",
            "quiet_vs_broken_section_present",
            "the generated guide now includes a short cheat sheet for separating true stand-down days from broken-data or helper-failure reads",
        ),
        require_contains(
            actual,
            "## Decision-Gate Source",
            "decision_gate_source_section_present",
            "the daily guide now includes a dedicated scorecard gate-source section before quiet-vs-broken triage",
        ),
        require(
            scorecard_gates["source_snippet"] in actual
            and scorecard_gates["anchor_displacement_min_roi_complete_settled_observations"] == 30
            and scorecard_gates["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and scorecard_gates["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and scorecard_gates["real_money_no_baq_as_bel_required"] is True,
            "daily_guide_gate_source_matches_scorecard_json",
            "the daily guide's visible 30 / 20 / 100 gate-source line is read directly from forward_evidence_scorecard.json decision_gate_minimums and preserves the no-BAQ-as-BEL real-money prerequisite",
        ),
        require_contains(
            actual,
            "- Treat `NO TARGETS` and active-target clean-empty / zero-hit reads as true stand-down days.",
            "quiet_vs_broken_true_quiet_rule",
            "the generated guide now says real quiet days are no-target or active-target clean-empty / zero-hit reads",
        ),
        require_contains(
            actual,
            "- Only call it a true no-target day when the saved preflight note (`preflight_note.txt`, or `preflight_note.json` if the text surface is missing or blank) explicitly says no primary paper-basket target tracks (OP / CD) are racing; if the preflight note says the calendar state is unknown or the upstream card check failed, that is degraded coverage, not a clean no-target read.",
            "quiet_vs_broken_preflight_guardrail",
            "the generated guide now makes the preflight unknown-calendar versus true no-target distinction explicit, including when the sibling text note is blank and the saved JSON note is the strongest surviving source",
        ),
        require_contains(
            actual,
            "- Treat `cache-only-miss` and `partial-cache` as incomplete-data states that need a rerun / refresh, not as evidence that nothing happened; green `validate_cache_only_messaging.py` or `validate_partial_cache_messaging.py` passes prove cache-edge routing / reproducibility only, not a quiet day, current-day scanner result, settled ROI, live profitability, promotion readiness, or real-money readiness.",
            "quiet_vs_broken_incomplete_data_rule",
            "the generated guide now says cache-only misses and partial-cache days are incomplete-data reads, and that green cache-only/partial-cache messaging validators prove cache-edge routing/reproducibility rather than quiet-day, scanner, ROI, profitability, promotion, or real-money evidence",
        ),
        require_contains(
            actual,
            "- Treat explicit `CHECK PIPELINE FAILURE`, `recommender failure`, and `logger failure` reads as operational failures that need a wrapper refresh / sidecar re-check, not as normal no-bet or quiet-market outcomes.",
            "quiet_vs_broken_pipeline_failure_rule",
            "the generated guide now says explicit recommender/logger pipeline-failure reads are operational failures rather than quiet-day or ordinary no-bet outcomes",
        ),
        require_contains(
            actual,
            "- Treat `scanner-failure`, `unreadable-calendar`, missing scan-output artifacts, missing/empty/unreadable artifact states, and helper-failure placeholders as operational issue states, not quiet-market reads.",
            "quiet_vs_broken_issue_rule",
            "the generated guide now says scanner/helper failures and unreadable artifacts are operational issue states rather than quiet days",
        ),
        require_contains(
            actual,
            "- If that distinction is unclear, read the saved preflight note (`preflight_note.txt`, or `preflight_note.json` if the text surface is missing or blank), `PAPER_TRADE_NOW.md` / `PAPER_TRADE_NOW.json`, and `OPS_HISTORY.md` together before deciding the lane was truly quiet, and on issue days follow the direct pipeline/scanner sidecar pointers surfaced in `PAPER_TRADE_NOW.md` before treating the branch as a generic failure.",
            "quiet_vs_broken_triage_rule",
            "the generated guide now gives a compact triage read order when quiet-day versus broken-day interpretation is unclear, including following the top-card sidecar pointers on issue days",
        ),
        require(
            latest is None or latest.exists(),
            "latest_run_root_exists",
            "the current latest daily run root referenced by the guide exists on disk, or the guide is honestly in its no-run-yet fallback state",
        ),
        (
            require_paths_exist(
                [
                    latest_daily,
                    latest_preflight,
                    latest_primary_next,
                    latest_shadow_next,
                    latest_primary_monitor,
                    latest_shadow_monitor,
                    latest_primary_forward,
                    latest_shadow_forward,
                ],
                "latest_run_sidecars_exist",
                "the latest-run daily summary, preflight, next-step, lane-monitor, and forward-check artifacts referenced by the guide all exist on disk",
            )
            if latest is not None
            else require(
                True,
                "latest_run_sidecars_exist",
                "no latest run exists yet, so the guide stays in its placeholder-path fallback state instead of pretending run sidecars are available",
            )
        ),
        require_contains(
            actual,
            "Current expected green read:",
            "green_read_present",
            "the guide still explains the current honest green-read meaning",
        ),
        require_contains(
            actual,
            "- `forward_evidence_scorecard.txt` stays the fastest research-side read, with `OP_DURABLE_K7` still on top",
            "green_read_scorecard_first",
            "the green-read summary still says the scorecard is the fastest research-side entry point",
        ),
        require_contains(
            actual,
            f"- `CURRENT_EVIDENCE_SUMMARY.md` stays the fastest source-checked frozen-to-current bridge, with source consistency, CSV settled_ts gap exclusion, operator-status context, source freshness / refresh-before-right-now-use routing, operator-read-gate routing, {current_context.bridge_queue_navigation} plus branch-specific scanner/API-failure wording when that route is present, scorecard-sourced OP_REFINED CI-only routing, scorecard_audit_route synchronization routing, rebuild_validation_contract order routing, CD-only current rule mix, bridge-published current gates source-matched to `forward_evidence_scorecard.json` `decision_gate_minimums`, and no-new-forward-evidence / no-promotion / no-real-money boundaries visible",
            "green_read_current_evidence_bridge",
            "the green-read summary now keeps the source-checked current-evidence bridge, scorecard-matched gate source, scorecard-sourced OP_REFINED CI-only routing, scorecard_audit_route synchronization routing, rebuild_validation_contract order routing, and open-row/recommendation-state context plus branch-specific scanner/API-failure wording visible as frozen-to-current navigation metadata rather than new forward evidence",
        ),
        require_contains(
            actual,
            f"- the direct current-evidence summary validator stays discoverable when the question is the current-paper bridge, source consistency, timestamp-gap exclusion, source freshness, operator-read-gate routing, {current_context.bridge_queue_navigation} plus branch-specific scanner/API-failure wording when that route is present, scorecard-sourced OP_REFINED CI-only routing, scorecard_audit_route synchronization routing, rebuild_validation_contract order routing, CD-only rule mix, bridge-published current gates, or no-overclaim wording",
            "green_read_current_evidence_discoverability",
            "the green-read summary now says the direct current-evidence summary validator should stay discoverable for bridge, source-consistency, source-freshness, open-row/recommendation-state plus branch-specific scanner/API-failure wording, scorecard-sourced OP_REFINED CI-only routing, scorecard_audit_route synchronization routing, rebuild_validation_contract order routing, rule-mix, gate, and no-overclaim questions",
        ),
        require_contains(
            actual,
            "- the direct main-comparison validator stays discoverable when the question is Cole's one-screen OP/CD paper read, matched CSV/markdown/JSON bundle, evidence-class triage, method-family comparison, or evidence-scope decision-change gates",
            "green_read_compare_main_discoverability",
            "the green-read summary now says the direct main-comparison validator should stay discoverable for the matched CSV/markdown/JSON bundle, one-screen read, evidence-class triage, method-family, and decision-gate questions",
        ),
        require_contains(
            actual,
            "- the direct cross-family validator stays discoverable when the question is the anchor / paper / watch shortlist or current-paper snapshot caveat, including stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and the no OP-anchor / no cross-family-promotion evidence boundary",
            "green_read_cross_family_current_paper_discoverability",
            "the green-read summary now says the direct cross-family validator should stay discoverable for anchor / paper / watch shortlist and current-paper snapshot caveat questions",
        ),
        require_contains(
            actual,
            "- the source-chain matrix plus direct paper-trade pipeline / scanner-sidecar path-resolution / recommender / EV-sizing / logger validators and live-scanner boundary contract stay discoverable when the question is upstream scan -> recommend -> size -> log behavior or copied-sidecar routing rather than downstream operator phrasing",
            "green_read_source_layer_discoverability",
            "the green-read summary still says the source-chain matrix plus direct source-layer paper-trade chain validators, scanner-sidecar path-resolution contract, and live-scanner boundary contract should stay discoverable",
        ),
        require_contains(
            actual,
            "| `PAPER_TRADE_NOW.md` | `present` | Best single-answer operator read: one honest command plus preserved primary/shadow recent-run context and lifted lane why-now lines behind it, with direct primary/shadow pipeline/scanner status-sidecar pointers for issue-day debugging. The adjacent `PAPER_TRADE_NOW.txt` / `PAPER_TRADE_NOW.json` siblings should stay source-matched to the same top-card payload, with JSON serving as the machine-readable automation card rather than separate evidence, including `operator_read_gate` as the first read-gating field. When the card is stale, those downstream lane details are explicitly inherited snapshot context, not current-day state. |",
            "paper_trade_now_daily_entry",
            "the daily-use table still prioritizes PAPER_TRADE_NOW.md as the first operator artifact, now points to PAPER_TRADE_NOW.json as the matched machine-readable sibling with operator_read_gate rather than separate evidence, and still says plainly that stale cards carry inherited snapshot context rather than current-day state",
        ),
        require_contains(
            actual,
            f"| `CURRENT_EVIDENCE_SUMMARY.md` | `present` | Source-checked and source-freshness-aware frozen-to-current bridge for short Cole updates: pairs with `current_evidence_summary.json`, source-checks `PAPER_TRADE_NOW`, the settlement audit, and the timestamp-aware primary settlement CSV recompute that requires actual `settled_ts`, publishes `source_freshness` / `requires_refresh_before_right_now_use` plus `operator_status_context` and `operator_read_gate`, and requires readers to {current_context.combined_operator_route_instruction}. It also {current_context.operator_read_gate_phrase}. It also {current_context.open_row_context_phrase}. It {current_context.ci_only_phrase}. It also {current_context.scorecard_audit_route_phrase}. It also {current_context.rebuild_order_phrase}. It keeps the {current_context.cd_only_sample_phrase} separate from OP-anchor proof, promotion readiness, live profitability, or real-money evidence. |",
            "current_evidence_daily_entry",
            f"the daily-use table now includes the source-checked and source-freshness-aware current-evidence bridge so short status updates do not skip source consistency, the combined operator_status_context/source_freshness/operator_read_gate route, {current_context.bridge_queue_navigation}, scorecard-sourced OP_REFINED CI-only routing, scorecard_audit_route synchronization routing, rebuild_validation_contract order routing, CD-only rule mix, bridge-published current gates, or no-overclaim boundaries",
        ),
        require(
            "| `COLE_STATUS_AND_PLAN.md` | `present` | Single honest status document. Read first when deciding what matters; pair status-doc / repo-map edits with `validate_cole_status_and_plan.py`, including the `status_doc_base_api_access_route_documented` route for base API-access / HTTP 403 status-summary wording before lane enrichment. |" in actual
            and "| `validate_cole_status_and_plan.py` | `present` | Direct validator for the main status document and repo map, including the frozen posture, validation reading order, top paths, machine-readable status-map boundary, and `status_doc_base_api_access_route_documented` for base API-access / HTTP 403 status-summary action-recheck routing before lane enrichment. |" in actual
            and "- run `python3 validate_cole_status_and_plan.py` when the question is whether the main status doc / repo map still exposes `status_doc_base_api_access_route_documented` for base API-access / HTTP 403 status-summary action-recheck route edits before lane enrichment" in actual
            and "- the main status document plus its direct validator stay discoverable when the question is the frozen status map, repo-map paths, or `status_doc_base_api_access_route_documented` for base API-access / HTTP 403 status-summary action-recheck route edits before lane enrichment" in actual,
            "main_status_api_access_route_discoverable",
            "the daily guide now routes main status-doc / repo-map API-access status-summary wording changes to validate_cole_status_and_plan.py and its named status_doc_base_api_access_route_documented check",
        ),
        (
            require(
                "API-access-failure operator context only" in current_context.open_row_context_phrase
                and "not a no-target, clean-empty, or forward-performance read" in current_context.open_row_context_phrase
                and "Sidecar action: refresh_daily_wrapper_before_evidence_read" in current_context.open_row_context_phrase
                and "Recheck command: ./run_daily_portfolio_observation.sh" in current_context.open_row_context_phrase
                and "Use recommendation and settlement ledgers before interpreting bet readiness or forward performance" in current_context.open_row_context_phrase
                and "Sidecar action: refresh_daily_wrapper_before_evidence_read" in actual
                and "Recheck command: ./run_daily_portfolio_observation.sh" in actual
                and "Treat this as operator context only; use recommendation" not in current_context.open_row_context_phrase
                and "Treat this as operator context only; use recommendation" not in actual,
                "current_evidence_recommendation_context_branch_is_current",
                "the daily guide pins the current-evidence API/scanner recommendation context as one specific operator boundary when that branch is current, without the older duplicate generic operator-context sentence",
            )
            if "API-access-failure operator context only" in current_context.open_row_context_phrase
            else require(
                "latest live scan completed cleanly" in current_context.open_row_context_phrase
                and "Treat this as operator context only; use recommendation and settlement ledgers before interpreting bet readiness or forward performance." in current_context.open_row_context_phrase
                and "Sidecar action: refresh_daily_wrapper_before_evidence_read" not in current_context.open_row_context_phrase
                and current_context.open_row_context_phrase in actual,
                "current_evidence_recommendation_context_branch_is_current",
                "the daily guide derives the current recommendation-context branch from current_evidence_summary.json, so a fresh clean/no-target scan is not mislabeled as the API-failure branch while staying operator context only",
            )
        ),
        require(
            f"use its scorecard-sourced `{guide.CI_ONLY_SOURCE}` read before quoting OP_REFINED's positive CI lower bound" in actual
            and "use its `scorecard_audit_route` before checking copied gate/ranking/CI-only/timezone/no-BAQ synchronization drift" in actual
            and current_context.ci_only_source == guide.CI_ONLY_SOURCE
            and current_context.ci_only_allowed is False
            and ci_only_context["source"] == guide.CI_ONLY_SOURCE
            and ci_only_context["candidate_rule_id"] == "OP_REFINED_K7"
            and ci_only_context["current_anchor_rule_id"] == "OP_DURABLE_K7"
            and ci_only_context["ci_only_promotion_allowed"] is False
            and ci_only_context["current_matches_scorecard_diagnostic"] is True,
            "current_evidence_ci_only_route",
            "the daily guide now routes OP_REFINED positive-CI wording through current_evidence_summary.json's scorecard-sourced CI-only diagnostic, pairs it with the bridge scorecard_audit_route, and proves it source-matches forward_evidence_scorecard.json with ci_only_promotion_allowed=false",
        ),
        require(
            current_context.scorecard_audit_route_phrase in actual
            and "`scorecard_audit_route` to `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py`" in actual
            and "copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks as report-synchronization metadata only" in actual,
            "current_evidence_scorecard_audit_route",
            "the daily guide now routes bridge scorecard-audit checks through current_evidence_summary.json.scorecard_audit_route instead of leaving the scorecard audit discoverable only as a separate decision-time artifact",
        ),
        require(
            current_context.rebuild_order_phrase in actual
            and "use its `rebuild_validation_contract` before rebuilding or quoting the bridge after scorecard/rules/signals/settlement-ledger byte changes" in actual
            and rebuild_contract["source"] == "current_evidence_summary.json"
            and rebuild_contract["source_path"] == "rebuild_validation_contract"
            and rebuild_contract["upstream_refresh_order_commands"] == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and rebuild_contract["requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"] is True
            and rebuild_contract["requires_source_consistency_before_quoting_current_totals"] is True
            and rebuild_contract["upstream_refresh_order_is_provenance_metadata_only"] is True
            and rebuild_contract["not_settled_roi_or_real_money_evidence"] is True,
            "current_evidence_rebuild_order_route",
            "the daily guide now routes source-byte bridge rebuilds through current_evidence_summary.json.rebuild_validation_contract and preserves the settlement-audit -> current-bridge -> bridge-validator order as provenance metadata only",
        ),
        require(
            current_context.combined_operator_route_instruction in actual
            and f"publishes `source_freshness` / `requires_refresh_before_right_now_use` plus `operator_status_context` and `operator_read_gate`, and requires readers to {current_context.combined_operator_route_instruction}" in actual
            and current_context.operator_read_gate_phrase in actual
            and "`operator_status_context` + `source_freshness` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read`" in actual
            and "and says to inspect `source_freshness` / `requires_refresh_before_right_now_use`" not in actual,
            "current_evidence_combined_operator_route",
            "the daily guide now makes the combined operator_status_context/source_freshness/operator_read_gate route the daily current-evidence path instead of splitting freshness and read-gate instructions across separate sentences",
        ),
        require_contains(
            actual,
            "Surfaces explicit primary/shadow recent-run context plus next-step states, settlement-audit action lines (`next_action` / `next_action_reason`) with the no-new-evidence boundary, and first-read / broader-review readiness lines so shadow review-readiness is visible, with OP_REFINED_K7 treated as the closest challenger and KEE_K9 / SA_K9 / DMR_FALL_K7 treated as observation-only pockets rather than live-promotion candidates.",
            "latest_daily_summary_entry_present",
            "the daily-use table still says the latest combined daily summary surfaces recent-run context plus next-step, settlement-audit action-line, and readiness lines while keeping OP_REFINED_K7 as the closest challenger and the other shadow names as observation-only pockets rather than live-promotion candidates",
        ),
        require_contains(
            actual,
            "| `forward_evidence_scorecard.txt` | `present` | Read this first for the fastest rule ranking by forward evidence quality. |",
            "forward_scorecard_entry_present",
            "the decision-time table still includes the forward evidence scorecard as the first research-side read",
        ),
        require_contains(
            actual,
            "| `SCORECARD_RANKING_CONTRACT_AUDIT.md` | `present` | Cross-surface scorecard ranking / CI-only / gate-floor audit. Use when Cole needs to know whether report-facing surfaces still carry tier-first ranking, OP_REFINED CI-only support context, copied 30/20/100 gate floors, and the no-BAQ-as-BEL prerequisite as reproducibility metadata only. |",
            "scorecard_audit_entry_present",
            "the decision-time table now includes the scorecard ranking / CI-only / gate-floor audit as the direct read when gate-floor provenance or no-BAQ-as-BEL prerequisite routing is the question",
        ),
        require_contains(
            actual,
            "| `validate_scorecard_ranking_contract_audit.py` | `present` | Direct validator for the scorecard audit, so tier-first ranking, OP_REFINED CI-only diagnostic routing, copied 30/20/100 gate floors, no-BAQ-as-BEL prerequisite routing, generated_at timezone provenance, and no-new-evidence boundaries do not drift quietly. |",
            "scorecard_audit_validator_entry_present",
            "the decision-time table now includes the direct scorecard audit validator so ranking, CI-only, copied gate-floor, no-BAQ prerequisite, timezone, and no-new-evidence boundaries do not require jumping to a parent sweep",
        ),
        require_contains(
            actual,
            f"| `validate_current_evidence_summary.py` | `present` | Direct validator for the source-checked current-evidence bridge, so `CURRENT_EVIDENCE_SUMMARY.md`, `current_evidence_summary.json`, source consistency, CSV settled_ts gap exclusion, operator-status context, source freshness / refresh-before-right-now-use instruction, operator-read-gate routing, settlement-queue state plus recommendation-state context plus branch-specific scanner/API-failure wording when that route is present, scorecard-sourced OP_REFINED CI-only routing, scorecard_audit_route synchronization routing, rebuild_validation_contract order, CD-only rule mix, bridge-published current gates, and no-new-forward-evidence / no-promotion / no-real-money boundaries do not drift quietly. |",
            "current_evidence_validator_entry_present",
            "the decision-time table now includes the direct current-evidence summary validator with queue-state-neutral wording so short bridge and freshness updates do not require jumping straight to broader report/project sweeps",
        ),
        require(
            "open-row identity plus recommendation-state context" not in actual,
            "current_evidence_validator_entry_uses_queue_state_wording",
            "the generated daily guide avoids implying an open settlement row in its static current-evidence validator route when the source bridge may be in a closed-queue state",
        ),
        require_contains(
            actual,
            "| `compare_main_approaches.md` | `present` | Human-facing member of the matched `compare_main_approaches.csv` / `.md` / `.json` bundle for the current OP/CD paper core, OP_REFINED_K7 shadow-only challenger, Harville benchmark-only lane, parked current odds-only XGBoost lane, BEL-not-BAQ caution, source-provenance/parity metadata, and evidence-scope decision gates; JSON is automation/provenance support, not new live or promotion evidence. |",
            "compare_main_entry_present",
            "the decision-time table now includes the main comparison report as the direct one-screen read for OP/CD, shadow, benchmark, research-only, BEL-not-BAQ, and evidence-scope gate posture",
        ),
        require_contains(
            actual,
            "| `validate_compare_main_approaches.py` | `present` | Direct validator for that main comparison bundle, so Cole's one-screen read, matched CSV/markdown/JSON sidecar, current paper ladder, evidence-class triage, method-family comparison, and evidence-scope decision gates do not drift quietly. |",
            "compare_main_validator_entry_present",
            "the decision-time table now includes the direct compare-main validator so main-report wording changes do not require jumping straight to the frozen-evidence parent",
        ),
        require_contains(
            actual,
            "| `VALIDATION_QUICKSTART.md` | `present` | Short runbook for which validator to run after which kind of edit, including the broader operator-suite route, the direct main-comparison route, narrow comparison validators, the direct source-layer paper-trade chain routes, the parent-rollup reuse shortcut guardrails, documented output paths, and the dated-report / legacy-alias policy. |",
            "quickstart_entry_present",
            "the decision-time table still treats VALIDATION_QUICKSTART.md as a report-safe runbook with the broader operator-suite route, narrow comparison routes, direct source-layer routes, parent-rollup reuse shortcut guardrails, documented output paths, and dated-report / legacy-alias policy visible",
        ),
        require_contains(
            actual,
            "| `validate_validation_quickstart.py` | `present` | Validator for the runbook itself, so the documented validation ladder, broader operator-suite route, main-comparison route, narrow comparison routes, direct source-layer paper-trade chain routes, the parent-rollup reuse shortcut guardrails, documented output paths, and the dated-report / legacy-alias policy do not drift quietly. |",
            "quickstart_validator_entry_present",
            "the decision-time table still includes the validator for the quickstart runbook itself, including the broader operator-suite route, parent-rollup reuse shortcut guardrails, documented output paths, and dated-report / legacy-alias policy",
        ),
        require_contains(
            actual,
            "| `PAPER_TRADE_USAGE.md` | `present` | Operator runbook for moving from the daily top cards into exact paper-trade commands. It also names `OP_ANCHOR_METHOD_COMPARISON.md` / `op_anchor_method_comparison.json` plus `validate_op_anchor_method_comparison.py` as the OP-anchor source-provenance plus readable-boundary route, with fingerprints and JSON `evidence_boundary_text` kept as provenance/reproducibility and no-new-evidence metadata only rather than settled ROI, promotion readiness, live profitability, or real-money evidence. |\n| `validate_paper_trade_usage.py` | `present` | Direct validator for that operator runbook, so the OP-anchor-first command path, primary-vs-shadow routine, closest-challenger vs observation-only shadow split, OP-anchor provenance/readable-boundary route, audit-only fingerprint / boundary-text boundary, and operator validator stack do not drift quietly. |",
            "paper_trade_usage_runbook_entry_present",
            "the decision-time table now includes the hands-on paper-trade runbook plus its direct validator so operators can move from daily top cards into exact commands while preserving the OP-anchor source-provenance plus readable-boundary route and audit-only fingerprint / boundary-text boundary",
        ),
        require_contains(
            actual,
            f"| `PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md` | `present` | Compact scan -> recommend -> size -> log source-chain matrix for the four direct source-layer validators, including fixture counts, guardrail inventories, validator JSON fingerprints, source/validator script fingerprints, matrix generator/validator fingerprints, and {source_chain['total_guardrail_checks']} guardrails, plus the direct live-scanner source-boundary contract for status sidecars and scanner hit rows; the direct validation report fingerprints the matrix markdown/JSON artifacts too, and this is not a live paper-trade ledger, settlement-complete ROI, promotion signal, or real-money profitability evidence. |\n| `validate_paper_trade_source_chain_guardrails.py` | `present` | Direct validator for the source-chain matrix, so the saved markdown/JSON matrix and live-scanner boundary contract stay source-matched to the scan, recommender, EV-sizing, and logger validator JSON artifacts plus source/validator scripts, matrix generator/validator tooling, and validated matrix artifact fingerprints before Cole drills into individual source-layer leaves. |\n| `validate_paper_trade_pipeline.py` | `present` | Direct validator for the machine-readable paper-trade pipeline status contract, so clean-empty reuse, malformed/invalid-shape/zero-byte/missing reused scan fallbacks, missing and zero-byte reused scan fallbacks with empty/readable/unreadable sidecar provenance, malformed/invalid-shape reused scan fallbacks with empty/readable/unreadable sidecar provenance, bets-ready reuse, scanner-failure and missing-output fallback with explicit empty-scan fallback metadata, scanner-failure stale-scan overwrite protection, empty/unreadable scanner-status sidecars, partial-cache activity, signals-logged-no-bet runs, and scorecard-sourced gate boundaries do not drift quietly. |\n| `validate_scanner_sidecar_resolution_contract.py` | `present` | Direct validator for scanner-status sidecar path resolution, so a pipeline-declared `scanner_status_path` stays authoritative across status summary, next steps, `PAPER_TRADE_NOW`, `OPS_HISTORY`, and saved-live refresh when stale default `live_scan.status.json` files are present, including HTTP 403 action/recheck preservation. |",
            "source_chain_matrix_entry_present",
            "the decision-time table now includes the compact source-chain matrix, its direct validator, the scanner-sidecar resolution contract, and live-scanner boundary contract so scan/recommend/size/log and copied-sidecar audits do not require jumping straight to individual leaves",
        ),
        require_contains(
            actual,
            "| `validate_paper_trade_pipeline.py` | `present` | Direct validator for the machine-readable paper-trade pipeline status contract, so clean-empty reuse, malformed/invalid-shape/zero-byte/missing reused scan fallbacks, missing and zero-byte reused scan fallbacks with empty/readable/unreadable sidecar provenance, malformed/invalid-shape reused scan fallbacks with empty/readable/unreadable sidecar provenance, bets-ready reuse, scanner-failure and missing-output fallback with explicit empty-scan fallback metadata, scanner-failure stale-scan overwrite protection, empty/unreadable scanner-status sidecars, partial-cache activity, signals-logged-no-bet runs, and scorecard-sourced gate boundaries do not drift quietly. |",
            "pipeline_validator_entry_present",
            "the decision-time table still includes the direct pipeline validator instead of leaving source-layer status questions implicit",
        ),
        require_contains(
            actual,
            "| `validate_paper_trade_recommender.py` | `present` | Direct validator for the recommendation builder, so the selective Phase 7 combo universe, honest `NO BET` handling, missing-race-id scanner-hit errors, and malformed-prediction fallback do not drift quietly. |",
            "recommender_validator_entry_present",
            "the decision-time table still includes the direct recommender validator, including missing-race-id scanner-hit handling, instead of leaving source-layer recommendation questions implicit",
        ),
        require(
            "| `LIVE_SCANNER_USAGE.md` | `present` | Live paper-alert scanner usage note, now framed as operational routing only: valid_evidence_scope=live_scanner_usage_paper_alert_runbook_navigation_only, daily observation still routes through the wrapper, scanner hits/alerts/clean-empty/capped/cache-only/API-access-failure results are not settled ROI or real-money evidence, HTTP 403/API-access failures preserve refresh_daily_wrapper_before_evidence_read plus ./run_daily_portfolio_observation.sh as operator routing only, and BAQ is not BEL. |" in actual
            and "| `validate_live_scanner_usage.py` | `present` | Direct validator for the live scanner usage note, so quick-start examples, OP/CD track filters, base-stake wording, cron monitoring, capped/partial coverage caveats, API-access-failure handling with explicit action/recheck fields, the live-scanner usage valid_evidence_scope, and no-BAQ-as-BEL boundaries do not drift quietly. |" in actual
            and "- run `python3 validate_live_scanner_usage.py` when the question is specifically the live scanner usage note, valid_evidence_scope=live_scanner_usage_paper_alert_runbook_navigation_only, quick-start examples, OP/CD track-filter examples, base-stake wording, cron monitoring, capped/partial coverage caveats, API-access-failure handling such as HTTP 403 including refresh_daily_wrapper_before_evidence_read plus ./run_daily_portfolio_observation.sh, or no-BAQ-as-BEL scanner wording" in actual
            and "- the live scanner usage note plus its direct validator stay discoverable when the question is scanner quick-start examples, valid_evidence_scope=live_scanner_usage_paper_alert_runbook_navigation_only, OP/CD track filters, base-stake wording, cron monitoring, capped/partial coverage caveats, API-access-failure handling such as HTTP 403 including refresh_daily_wrapper_before_evidence_read plus ./run_daily_portfolio_observation.sh, or no-BAQ-as-BEL scanner wording" in actual,
            "live_scanner_usage_entry_present",
            "the daily guide now includes the live scanner usage note plus direct usage-boundary validator so scanner examples, cron monitoring, capped/partial coverage, API-access-failure action/recheck handling, and BAQ/BEL wording have a narrow maintenance route",
        ),
        require_contains(
            actual,
            "| `EV_TICKET_ENGINE_USAGE.md` | `present` | Source-layer EV sizing usage note for paper-trade/debugging context only: valid_evidence_scope=ev_ticket_engine_usage_source_layer_runbook_navigation_only, daily use still routes through the wrapper and recommender, BET means hypothetical paper-ticket plan only, fixture bankroll defaults are not authorized bankroll, BAQ is not BEL, and source-byte changes route through `current_evidence_summary.json.rebuild_validation_contract` before current totals are quoted. |\n| `validate_ev_ticket_engine_usage.py` | `present` | Direct validator for the EV usage note, so source-layer examples stay paper-only, route daily use through the wrapper/recommender, require the EV usage valid_evidence_scope, avoid dormant-BEL labels, preserve the no-bankroll / no-real-money boundary, and source-check the current-evidence rebuild order. |",
            "ev_ticket_engine_usage_entry_present",
            "the decision-time table now includes the EV ticket-engine usage note plus direct usage-boundary validator so source-layer examples cannot drift into bankroll or real-money guidance and current-evidence rebuild-order routing stays discoverable",
        ),
        require_contains(
            actual,
            "| `validate_ev_ticket_engine.py` | `present` | Direct validator for the EV sizing layer, so conservative no-bet boundaries, bankroll-cap sizing, malformed-probability failures, and scorecard-sourced gate boundaries do not drift quietly. |",
            "ev_ticket_engine_validator_entry_present",
            "the decision-time table still includes the direct EV sizing validator instead of leaving source-layer bankroll questions implicit",
        ),
        require_contains(
            actual,
            "| `validate_paper_trade_logger.py` | `present` | Direct validator for the persistent paper-trade ledgers, so stable headers, serialized payload appends, state-plus-ledger dedup, malformed-state ledger rebuild fallback, and blank-key skips do not drift quietly. |",
            "logger_validator_entry_present",
            "the decision-time table still includes the direct logger validator instead of leaving source-layer ledger questions implicit",
        ),
        require_contains(
            actual,
            "| `validate_paper_trade_preflight_note.py` | `present` | Direct validator for the shared preflight note, so active-target, no-target, and unknown-calendar wording do not drift quietly. |",
            "preflight_note_validator_entry_present",
            "the decision-time table still includes the direct preflight-note validator instead of forcing readers through only the broader operator suite",
        ),
        require_contains(
            actual,
            "| `validate_paper_trade_status_summary.py` | `present` | Direct validator for the one-line base lane summary, so its text/JSON branch behavior, scanner/pipeline sidecar issue wording, API-access / HTTP 403 action-recheck route wording, stale-cache fallback metadata, missing-scan-output fallback wording, pipeline-recorded scanner-status state preservation, cache / error state wording, and saved recommender/logger failure detail line do not drift quietly. |\n| `validate_paper_trade_now.py` | `present` | Direct validator for the right-now top-card bundle, so text, markdown, and JSON outputs stay source-matched to `paper_trade_now.py --format json`, markdown-only placeholder fallback stays separate from full helper-failure JSON placeholders, and stale-card inherited-snapshot wording / missing scan-output refresh wording / `operator_read_gate` no-evidence routing / sidecar pointers do not drift quietly. |",
            "status_summary_validator_entry_present",
            "the decision-time table still includes the direct status-summary validator and the direct right-now validator instead of forcing readers through only the broader operator suite, with the base API-access / HTTP 403 action-recheck route plus right-now text/markdown/JSON parity and placeholder-boundary contracts visible",
        ),
        require_contains(
            actual,
            "| `validate_current_hierarchy_language.py` | `present` | Direct validator for current live hierarchy wording and structured keys, so `OP_DURABLE_K7` stays the anchor, `CD_CORE_K8` stays the primary OP/CD paper-basket companion, `OP_REFINED_K7` stays shadow/watch, and legacy `primary_shadow` compatibility does not become promotion, ROI, live-profitability, or real-money evidence. |",
            "current_hierarchy_validator_entry_present",
            "the decision-time table now includes the direct current-hierarchy validator so live hierarchy wording and structured-key compatibility questions do not get flattened into only the right-now or wrapper validators",
        ),
        require_contains(
            actual,
            "| `validate_paper_trade_settlement_sync.py` | `present` | Direct validator for the settlement-template sync helper, so stable empty headers, one-row-per-signal-key syncing, preserved manual settlement fields, blank and duplicate signal-key skips, blank settlement-key drops, and orphan-row cleanup do not drift quietly. |",
            "settlement_sync_validator_entry_present",
            "the decision-time table still includes the direct settlement-sync validator instead of forcing readers through only the broader operator suite, with the separate blank/duplicate signal-key / blank settlement-key / orphan-row cleanup branches visible",
        ),
        require_contains(
            actual,
            "| `validate_paper_trade_settlement_helper.py` | `present` | Direct validator for the human-facing settlement helper, so open-queue rendering, separate settled-row ROI-gap visibility, queue truncation, one-row settlement updates, duplicate signal-key rejection before mutation, settlement cost-source reporting, expected-cost fallback, supplied settled_ts validation, timestamp-omission ROI-gate warnings, true missing/malformed-cost handling, and missing-signal failures do not drift quietly. |\n| `validate_paper_trade_settlement_audit.py` | `present` | Direct validator for the ledger-completeness / ROI-coverage audit, so primary/shadow `next_action` / `next_action_reason` routing, blank signal-key versus blank settlement-key repair labeling, duplicate custom lane-name rejection before output artifacts, ROI-complete row counting, and the no-new-forward-evidence boundary do not drift quietly. |",
            "settlement_helper_validator_entry_present",
            "the decision-time table still includes the direct settlement-helper and settlement-audit validators instead of forcing readers through only the broader operator suite",
        ),
        require_contains(
            actual,
            "| `validate_paper_trade_next_steps.py` | `present` | Direct validator for the per-lane next-step helper, so settlement-first, missing scan-output refresh guidance, pipeline-recorded scanner-status refresh guidance, API-access stale-cache fallback routing, rerun-live, limited-cache, explicit recommender/logger pipeline-failure recovery, and decision-grade command routing do not drift quietly. |",
            "next_steps_validator_entry_present",
            "the decision-time table still includes the direct next-steps validator instead of forcing readers through only the broader operator suite",
        ),
        require_contains(
            actual,
            "| `validate_paper_trade_forward_check.py` | `present` | Direct validator for the frozen-baseline forward check, so its assessment states, recommendation-flow detail, ROI-fallback wording, explicit ROI cost-source counts, malformed actual-cost gap wording, and no-overpromotion decision gate do not drift quietly. |",
            "forward_check_validator_entry_present",
            "the decision-time table still includes the direct forward-check validator instead of forcing readers through only the broader operator suite",
        ),
        require_contains(
            actual,
            "| `validate_paper_trade_lane_monitor.py` | `present` | Direct validator for the compact per-lane monitor, so its forward assessment, no-overpromotion decision gate, queue visibility, and ROI-detail wording do not drift quietly. |",
            "lane_monitor_validator_entry_present",
            "the decision-time table still includes the direct lane-monitor validator instead of forcing readers through only the broader operator suite",
        ),
        require_contains(
            actual,
            "| `validate_paper_trade_daily_summary.py` | `present` | Direct validator for the combined daily summary, so its full routed quick-jump bundle, routed top-card focus/timing/freshness/ops snapshot, explicit primary/shadow recent-run context lines, explicit primary/shadow next-step state lines plus settlement-audit action lines and lifted no-overpromotion decision-gate snapshot lines, first-read and broader-review readiness lines, lane sections, artifacts-root line, explicit recommender/logger failure context, pipeline-recorded scanner-status issue lines, and missing-artifact placeholders do not drift quietly. |",
            "daily_summary_validator_entry_present",
            "the decision-time table still includes the direct daily-summary validator instead of forcing readers through only the broader operator suite, with the stronger full routed quick-jump-bundle, recent-run-context, next-step-state, settlement-audit action-line, and decision-gate contract visible",
        ),
        require_contains(
            actual,
            "| `validate_paper_trade_lane_summary.py` | `present` | Direct validator for one lane summary surface, so its full routed quick-files bundle, no-overpromotion decision-gate snapshot line, missing scan-output fallback context, pipeline-recorded scanner-status base headlines, section layout, placeholders, and temp-write display path handling do not drift quietly. |",
            "lane_summary_validator_entry_present",
            "the decision-time table still includes the direct lane-summary validator instead of forcing readers through only the broader operator suite, with the stronger full routed quick-files-bundle plus decision-gate contract visible",
        ),
        require_contains(
            actual,
            "| `refresh_live_paper_trade_surfaces.py` | `present` | Direct saved-live rebuild path when helper/render logic changes underneath matched `PAPER_TRADE_NOW` text/markdown/JSON outputs, `OPS_HISTORY`, `CURRENT_EVIDENCE_SUMMARY`, saved `preflight_note` text/JSON, or per-run summaries and you want source-matched artifacts without rerunning the full wrapper. It now refreshes per-run lane/preflight artifacts first, then top-level `PAPER_TRADE_NOW` text/markdown/JSON / `OPS_HISTORY` / `CURRENT_EVIDENCE_SUMMARY` markdown/JSON, then each `daily_summary.txt`, so routed top-card snapshot lines and current-evidence bridge reads do not drift behind stale top-level surfaces; the current bridge preserves `current_evidence_summary.json.rebuild_validation_contract` as the settlement-audit -> current-bridge -> bridge-validator route. Optional `--as-of-date YYYY-MM-DD` also pins rebuilt top-card freshness and the helper says in stdout whether that pin was actually applied or skipped, and if a rebuilt top card is still stale it keeps the explicit inherited-snapshot honesty note. Under `--latest-only`, that rebuild scope stays confined to the newest copied run's preflight, lane, and daily-summary surfaces. Under `--skip-top-level`, it leaves `OPS_HISTORY` / matched `PAPER_TRADE_NOW` / `CURRENT_EVIDENCE_SUMMARY` outputs untouched while still rerendering those per-run surfaces against the existing top-level outputs, and the helper says when `--as-of-date` was ignored because top-level refresh was skipped. This rerenders saved surfaces from existing artifacts; it is not a new forward result. |",
            "refresh_helper_entry_present",
            "the decision-time table still includes the saved-live rebuild helper so persisted operator artifacts can be refreshed without rerunning the wrapper, now documents the matched PAPER_TRADE_NOW text/markdown/JSON rebuild scope, optional as-of-date freshness pinning plus applied-vs-skipped stdout behavior, the separate skip-top-level top-card-preservation boundary, says stale rebuilt top cards keep the inherited-snapshot honesty note, and still says plainly that rerendering is not a new forward result",
        ),
        require_contains(
            actual,
            "| `validate_refresh_live_paper_trade_surfaces.py` | `present` | Direct validator for that saved-live rebuild path, so regenerated per-run summaries, saved `preflight_note` text/JSON, plus top-level `PAPER_TRADE_NOW` text/markdown/JSON / `OPS_HISTORY` / `CURRENT_EVIDENCE_SUMMARY` outputs stay source-matched, current-evidence bridge rebuilds preserve `current_evidence_summary.json.rebuild_validation_contract`, rebuilt daily summaries keep missing scan-output context plus the routed top-card focus/timing/freshness/ops snapshot, rebuilt `PAPER_TRADE_NOW.json` matches the source-layer right-now payload while rebuilt text/markdown keep preserved primary/shadow recent-run context plus lifted lane why-now lines when current lane artifacts provide them, still marks stale rebuilt cards as inherited snapshot context rather than current-day state, `--latest-only` stays honest about refreshing only the newest copied run's preflight, lane, and daily-summary surfaces, `--skip-top-level` stays honest about leaving top-level outputs untouched while still rebuilding the per-run preflight/lane/daily layer against those existing top-level outputs, `--as-of-date` applied-vs-skipped stdout behavior stays honest, and the helper keeps saying explicitly that rerendering is not new forward evidence. |",
            "refresh_helper_validator_entry_present",
            "the decision-time table still includes the direct validator for the saved-live rebuild path, including the matched PAPER_TRADE_NOW JSON parity contract, explicit as-of-date stdout honesty contract, the separate skip-top-level top-card-preservation boundary, the stale rebuilt-card inherited-snapshot contract, and the not-new-evidence contract",
        ),
        require_contains(
            actual,
            "| `validate_run_daily_portfolio_observation.py` | `present` | Direct validator for the real daily wrapper, so missing scan-output refresh, helper-failure / placeholder-fallback orchestration, preflight-plus-summary stitching, wrapper-generated `CURRENT_EVIDENCE_SUMMARY` refresh/placeholder behavior, source-backed recommendation-context/open-row separation, direct scorecard-sourced 30/20/100 gate-boundary publication, and the inherited wrapper-guardrail inventory that broader operator/project sweeps are supposed to preserve do not drift quietly. |",
            "daily_wrapper_validator_entry_present",
            "the decision-time table now includes the direct daily-wrapper validator so wrapper fallback/rebuild orchestration, wrapper-generated current-evidence bridge, and direct scorecard gate-boundary questions do not get flattened into only umbrella operator/project sweeps",
        ),
        require_contains(
            actual,
            "| `WORKING_STATUS_REPORT_2026-04-15.md` | `present` | Dated live/demo-vs-production note for the corrected operational state, with the 2026-04-15 Keeneland demo artifacts kept as the stable evidence anchor. |",
            "working_status_entry_present",
            "the decision-time table still includes the dated working-status note as a report-safe operational reference",
        ),
        require_contains(
            actual,
            "| `validate_working_status_report.py` | `present` | Direct validator for that dated working-status note, so the production-basket vs demo-lane distinction and mutable latest-demo alias do not drift quietly. |",
            "working_status_validator_entry_present",
            "the decision-time table still includes the direct working-status validator instead of forcing readers through only the broader report sweep",
        ),
        require_contains(
            actual,
            "| `validate_report_surfaces.py` | `present` | Direct validator for the shareable report layer, so README, the long-form report, the working-status note, the presentation outline, and the HTML report stay aligned on the frozen story, the dated report trust path, and the README-inherited wrapper-leaf source-of-truth note the narrative rollup should preserve rather than flatten away. |",
            "report_surfaces_validator_entry_present",
            "the decision-time table still includes the direct report-surfaces validator as the shareable-wording route, including the inherited README wrapper-note preservation contract",
        ),
        require_contains(
            actual,
            "| `OP_FAMILY_DECISION.md` | `present` | Whether anything clearly beats OP_DURABLE_K7 as the safest OP anchor. |",
            "op_family_entry_present",
            "the decision-time table still includes the OP-family decision card as the first focused anchor-replacement read",
        ),
        require_contains(
            actual,
            "| `validate_op_family_decision.py` | `present` | Direct validator for the OP-family card, so the saved surfaces, real CLI output, and conservative anchor-replacement bar do not drift quietly. |",
            "op_family_validator_entry_present",
            "the decision-time table still includes the direct validator for the OP-family decision card",
        ),
        require_contains(
            actual,
            "| `CROSS_FAMILY_DECISION.md` | `present` | Anchor / paper / watch roles for OP_DURABLE_K7, CD_CORE_K8, and OP_REFINED_K7, plus the current-paper snapshot that keeps CD-only settled context and source-published settlement-queue state/context out of OP-anchor proof or cross-family promotion evidence. |",
            "cross_family_entry_present",
            "the decision-time table still includes the cross-family shortlist card and its current-paper snapshot caveat",
        ),
        require_contains(
            actual,
            "| `validate_cross_family_decision.py` | `present` | Direct validator for the cross-family shortlist, so the saved surfaces, real CLI output, current anchor / paper / watch ordering, current-paper snapshot caveat, and no cross-family promotion-evidence boundary do not drift quietly. |",
            "cross_family_validator_entry_present",
            "the decision-time table still includes the direct validator for the cross-family shortlist and current-paper snapshot caveat",
        ),
        require_contains(
            actual,
            "| `PORTFOLIO_DECISION_CARD.md` | `present` | Phase 7 vs Phase 8 vs train-only selector at the portfolio level. |",
            "portfolio_decision_entry_present",
            "the decision-time table still includes the top-level portfolio decision card",
        ),
        require_contains(
            actual,
            "| `validate_portfolio_decision_card.py` | `present` | Direct validator for the top-level portfolio card, so the saved surfaces, real CLI output, and current paper / shadow / benchmark ordering do not drift quietly. |",
            "portfolio_decision_validator_entry_present",
            "the decision-time table still includes the direct validator for the top-level portfolio decision card",
        ),
        require_contains(
            actual,
            "| `METHOD_FAMILY_DECISION.md` | `present` | Selective rule path versus the Harville benchmark and the parked current odds-only XGBoost path, for retiring dead-end method families. |",
            "method_family_entry_present",
            "the decision-time table still includes the method-family retirement card with the stricter parked-odds-only-XGBoost framing",
        ),
        require_contains(
            actual,
            "| `validate_method_family_decision_card.py` | `present` | Direct validator for the method-family card, so the saved surfaces, real CLI output, and current selective-rule / Harville / XGBoost ordering do not drift quietly. |",
            "method_family_validator_entry_present",
            "the decision-time table still includes the direct validator for the method-family decision card",
        ),
        require_contains(
            actual,
            "| `OP_ANCHOR_METHOD_COMPARISON.md` | `present` | Cold-read OP-centered answer that makes unlike evidence classes explicit, so OP_DURABLE_K7 still outranks Harville while the current odds-only XGBoost path stays parked unless its evidence class changes materially; the matched JSON sidecar carries source-byte provenance for reproducibility only, not settled ROI, promotion readiness, live profitability, or real-money evidence. |",
            "op_anchor_entry_present",
            "the decision-time table still includes the OP-centered comparison artifact and its provenance-only JSON-sidecar boundary",
        ),
        require_contains(
            actual,
            "| `AB_DOWNSTREAM_COMPARISON.md` | `present` | Matched downstream enriched-horse-history XGBoost A/B report showing that modest prediction gains still do not improve the paper-betting case; validate with the source-aware A/B checker because full CLI parity needs raw rebuild inputs. |",
            "ab_downstream_entry_present",
            "the decision-time table still includes the downstream XGBoost A/B artifact",
        ),
        require_contains(
            actual,
            "| `FULL_DATA_RETRAIN_ARTIFACTS.md` | `present` | Full-data XGBoost retrain artifact for model-fit reproducibility only: the large RMSE / MAE improvements are diagnostic metrics, not paper-trade evidence, live profitability, promotion readiness, bankroll guidance, or real-money evidence. |",
            "full_data_retrain_entry_present",
            "the decision-time table now includes the full-data XGBoost retrain artifact but keeps it in model-fit reproducibility context only",
        ),
        require_contains(
            actual,
            "| `validate_full_data_retrain_artifacts.py` | `present` | Direct validator for the full-data retrain artifact, so exact retrain/prediction commands and the model-fit-not-betting-evidence boundary do not drift quietly. |",
            "full_data_retrain_validator_entry_present",
            "the decision-time table now includes the direct full-data retrain validator so the large payout-fit metrics cannot drift into betting-evidence language unnoticed",
        ),
        require_contains(
            actual,
            "| `validate_backtest_report_caution.py` | `present` | Direct validator for the legacy backtest-report caution, so broad negative-baseline context, odds-only XGBoost parking, full-data retrain routing, and no-BAQ-as-BEL wording do not drift quietly. |",
            "backtest_report_caution_validator_entry_present",
            "the benchmark-only table now includes the direct legacy-backtest caution validator so broad Harville / generic odds-only ML baseline wording cannot drift into deployment evidence",
        ),
        require_contains(
            actual,
            "| `PHASE7_REPORT.md` | `present` | Historical Phase 7 discovery report and strongest candidate-family context with valid_evidence_scope=legacy_phase7_discovery_context_only; use it for frozen OP/CD/BEL context, not as a live deployment guide or real-money instruction. |",
            "phase7_report_entry_present",
            "the benchmark-only table now includes PHASE7_REPORT with valid_evidence_scope as historical strongest-candidate-family context rather than a live deployment guide",
        ),
        require_contains(
            actual,
            "| `validate_phase7_report_caution.py` | `present` | Direct validator for the legacy Phase 7 report caution, so the Phase 7 valid_evidence_scope, three-track headline, dormant BEL, cost/Kelly/historical profit lines, OP_DURABLE_K7 anchor, CD_CORE_K8 companion, paper-observation posture, and no-BAQ-as-BEL wording do not drift quietly. |",
            "phase7_report_caution_validator_entry_present",
            "the benchmark-only table now includes the direct legacy-Phase-7 caution validator and valid_evidence_scope so three-track, dormant-BEL, cost/Kelly, and historical-profit wording cannot drift into live deployment or real-money evidence",
        ),
        require_contains(
            actual,
            "| `WALK_FORWARD_VALIDATION.md` | `present` | Honest train-only validation benchmark with valid_evidence_scope=train_only_walk_forward_selector_benchmark_only. Use for context, not as the daily operating recipe. |\n| `validate_walk_forward_validation_caution.py` | `present` | Direct validator for the walk-forward caution boundary, so the +22.46% train-only selector result and valid_evidence_scope stay benchmark context rather than settled ROI, promotion readiness, real-money evidence, or BAQ/BEL aliasing. |",
            "walk_forward_validation_caution_validator_entry_present",
            "the benchmark-only table now includes the direct walk-forward caution validator so the train-only selector result, fixed replay comparison, and BEL/BAQ diagnostic cannot drift into paper-trade or real-money evidence",
        ),
        require_contains(
            actual,
            "| `validate_phase8_report_caution.py` | `present` | Direct validator for the legacy Phase 8 report caution, so the full-sample headline, $2/cost lines, OP_DURABLE_K7 anchor, shadow/watch status, no-real-money boundary, and BAQ-is-not-BEL wording do not drift quietly. |",
            "phase8_report_caution_validator_entry_present",
            "the benchmark-only table now includes the direct legacy-Phase-8 caution validator so full-sample Phase 8 headlines, cost/sizing language, OP-anchor status, shadow/watch status, and BAQ/BEL wording cannot drift into deployment evidence",
        ),
        require_contains(
            actual,
            "| `DIAGNOSE_CD_SELECTION.md` | `present` | Historical CD selector diagnostic, now with valid_evidence_scope=cd_track_group_selector_replay_diagnostic_only; use the Always-CD_CORE and No-CD rows as replay diagnostics only, not as a new expected ROI range or a live paper-basket instruction. |\n| `validate_diagnose_cd_selection_caution.py` | `present` | Direct validator for the CD selector diagnostic boundary, so the CD selector valid_evidence_scope, Always-CD_CORE, and No-CD counterfactuals stay frozen replay research rather than current paper-basket, promotion, live-profitability, bankroll, real-money, or BAQ/BEL evidence. |",
            "diagnose_cd_selection_caution_validator_entry_present",
            "the benchmark-only table now includes the direct CD selector diagnostic caution validator and valid_evidence_scope so Always-CD_CORE and No-CD replay rows cannot drift into expected-ROI, paper-basket, promotion, live-profitability, bankroll, real-money, or BAQ/BEL evidence",
        ),
        require_contains(
            actual,
            "| `SELECTOR_EXPERIMENT.md` | `present` | Selector-scoring research context, not a daily-use artifact; valid_evidence_scope=selector_scoring_replay_diagnostic_only; it shows sqrt|strict improved the frozen replay, but the recommendation is historical research and cannot override the scorecard-backed OP_DURABLE_K7 / CD_CORE_K8 / OP_REFINED_K7 posture. |\n| `validate_selector_experiment_caution.py` | `present` | Direct validator for the selector-scoring experiment boundary, so the selector-scoring valid_evidence_scope, sqrt|strict adoption wording, fold-2017 win, BEL bridge rows, and CD details stay historical selector research rather than current paper-basket, promotion, live-profitability, real-money, or BAQ/BEL evidence. |",
            "selector_experiment_caution_validator_entry_present",
            "the benchmark-only table now includes the direct selector-scoring experiment caution validator and valid_evidence_scope so sqrt|strict adoption wording, fold-2017 wins, BEL bridge rows, and CD details cannot drift into current paper-basket or promotion evidence",
        ),
        require_contains(
            actual,
            "| `SAMPLE_SIZE_EXPERIMENT.md` | `present` | Follow-up selector experiment context, not a daily-use artifact; valid_evidence_scope=sample_size_selector_replay_diagnostic_only; it shows races-factor tuning did not improve on sqrt_r150, but the selector recommendation is historical research and cannot override the scorecard-backed OP_DURABLE_K7 / CD_CORE_K8 / OP_REFINED_K7 posture. |\n| `validate_sample_size_experiment_caution.py` | `present` | Direct validator for the sample-size selector experiment boundary, so the sample-size selector valid_evidence_scope, keep-sqrt_r150 recommendation, always-CD_CORE counterfactual, and races-factor variants stay historical selector research rather than current paper-basket, promotion, live-profitability, real-money, or BAQ/BEL evidence. |",
            "sample_size_experiment_caution_validator_entry_present",
            "the benchmark-only table now includes the direct sample-size selector experiment caution validator and valid_evidence_scope so keep-sqrt_r150 wording, always-CD_CORE counterfactuals, and races-factor variants cannot drift into current paper-basket or promotion evidence",
        ),
        require_contains(
            actual,
            "| `compare_recommender_scope_paths.md` | `present` | Selective-vs-widened recommender scope guardrail, showing why `--allow-all-combos` stays research-only and now breaking out how much modeled stub EV lift comes from off-scope tickets rather than observed P&L. |",
            "recommender_scope_entry_present",
            "the decision-time table still includes the recommender-scope guardrail artifact and now names the modeled stub-EV / off-scope-ticket boundary",
        ),
        require_contains(
            actual,
            "- the direct preflight-note validator stays discoverable when the question is specifically the shared calendar-note surface",
            "green_read_preflight_note_discoverability",
            "the green-read summary still says the direct preflight-note validator should stay discoverable",
        ),
        require_contains(
            actual,
            "- the direct status-summary validator stays discoverable when the question is specifically the one-line base lane summary surface, including API-access / HTTP 403 action-recheck route preservation, stale-cache fallback count/kind/error visibility, missing-scan-output fallbacks, empty/unreadable scanner sidecars, pipeline-recorded empty/unreadable scanner-status states, wrapper-only required-pipeline sidecar issues, and saved recommender/logger failure lines with stage / error type / detail\n- the direct right-now validator stays discoverable when the question is specifically the `PAPER_TRADE_NOW` text/markdown/JSON bundle, source-layer JSON parity, placeholder boundaries, stale-snapshot note, operator-read-gate no-evidence routing, or sidecar pointers",
            "green_read_status_summary_discoverability",
            "the green-read summary still says the direct status-summary validator should stay discoverable for API-access / HTTP 403 route preservation and now keeps the direct right-now validator discoverable for PAPER_TRADE_NOW text/markdown/JSON parity, placeholder-boundary, stale-snapshot, and sidecar-pointer questions",
        ),
        require_contains(
            actual,
            "- the direct current-hierarchy validator stays discoverable when the question is specifically `OP_DURABLE_K7` / `CD_CORE_K8` / `OP_REFINED_K7` live hierarchy wording, `live_hierarchy`, `primary_companion`, or legacy `primary_shadow` keys; the green read is hierarchy wording / metadata routing only, not settled ROI, promotion readiness, live profitability, or real-money evidence",
            "green_read_current_hierarchy_discoverability",
            "the green-read summary now says the direct current-hierarchy validator should stay discoverable for live hierarchy wording and structured-key compatibility questions, with the no-ROI/no-promotion/no-live-profitability/no-real-money boundary visible",
        ),
        require_contains(
            actual,
            "- the direct settlement-sync validator stays discoverable when the question is specifically the settlement-template sync surface",
            "green_read_settlement_sync_discoverability",
            "the green-read summary still says the direct settlement-sync validator should stay discoverable",
        ),
        require_contains(
            actual,
            "- the direct settlement-helper and settlement-audit validators stay discoverable when the question is specifically manual settlement entry or the ledger-completeness / ROI-coverage audit, including primary/shadow action routing, blank signal-key versus blank settlement-key repair labeling, and the no-new-forward-evidence boundary",
            "green_read_settlement_helper_discoverability",
            "the green-read summary still says the direct settlement-helper validator should stay discoverable and now keeps the direct settlement-audit validator discoverable for ledger-readiness action routing",
        ),
        require_contains(
            actual,
            "- the direct next-steps validator stays discoverable when the question is specifically the exact next-command surface, including API-access stale-cache fallback routing and explicit recommender/logger pipeline-failure recovery",
            "green_read_next_steps_discoverability",
            "the green-read summary still says the direct next-steps validator should stay discoverable, including API-access stale-cache fallback routing and explicit pipeline-failure recovery",
        ),
        require_contains(
            actual,
            "- the direct forward-check validator stays discoverable when the question is specifically the per-lane forward assessment surface",
            "green_read_forward_check_discoverability",
            "the green-read summary still says the direct forward-check validator should stay discoverable",
        ),
        require_contains(
            actual,
            "- the direct lane-monitor validator stays discoverable when the question is specifically the compact per-lane monitor surface",
            "green_read_lane_monitor_discoverability",
            "the green-read summary still says the direct lane-monitor validator should stay discoverable",
        ),
        require_contains(
            actual,
            "- the direct daily-summary validator stays discoverable when the question is specifically the combined `daily_summary.txt` surface, including the full routed quick-jump bundle, routed top-card focus/timing/freshness/ops snapshot, explicit primary/shadow recent-run context lines, explicit primary/shadow next-step state lines plus settlement-audit action lines, first-read and broader-review readiness lines, and explicit recommender/logger failure context",
            "green_read_daily_summary_discoverability",
            "the green-read summary still says the direct daily-summary validator should stay discoverable at the full routed quick-jump-bundle level, including explicit recent-run context, next-step state lines, settlement-audit action lines, first-read vs broader-review readiness lines, and pipeline-failure context",
        ),
        require_contains(
            actual,
            "- the direct lane-summary validator stays discoverable when the question is specifically one lane `summary.txt` surface, including the full routed quick-files bundle and lifted no-overpromotion decision-gate line",
            "green_read_lane_summary_discoverability",
            "the green-read summary still says the direct lane-summary validator should stay discoverable at the full routed quick-files-bundle plus decision-gate level",
        ),
        require_contains(
            actual,
            "- the saved-live refresh helper plus its direct validator stay discoverable when matched `PAPER_TRADE_NOW` text/markdown/JSON outputs, `OPS_HISTORY`, saved `preflight_note` text/JSON, or saved per-run summaries need a source-matched rebuild after helper/render edits, with rebuilt `PAPER_TRADE_NOW.json` keeping source-layer payload parity, missing scan-output context preservation in rebuilt per-run surfaces, missing scan-output context surviving rebuilt per-run surfaces, rebuilt daily summaries inheriting the routed top-card focus/timing/freshness/ops snapshot, rebuilt text/markdown preserving primary/shadow recent-run context plus lifted lane why-now lines when current lane artifacts provide them, distinct `--latest-only` newest-run and `--skip-top-level` top-card-preservation boundaries, optional `--as-of-date` freshness pinning reporting whether it was actually applied or skipped, and that path staying explicit about rerendering saved artifacts rather than creating new forward evidence",
            "green_read_refresh_discoverability",
            "the green-read summary still says the saved-live refresh path should stay discoverable when persisted operator artifacts need a source-matched rebuild, now also carries PAPER_TRADE_NOW JSON parity, the separate latest-only versus skip-top-level maintenance boundaries plus the as-of-date applied-vs-skipped honesty note, and still pins the not-new-evidence framing there too",
        ),
        require_contains(
            actual,
            "- the direct daily-wrapper validator stays discoverable when the question is specifically wrapper fallback/rebuild orchestration, wrapper-generated `CURRENT_EVIDENCE_SUMMARY` refresh/placeholder behavior, source-backed recommendation-context/open-row separation, or direct scorecard-sourced gate-boundary publication, and the guide now says that both wrapper leaves feed inherited wrapper-guardrail inventories the broader operator/project sweeps are supposed to preserve rather than flatten",
            "green_read_daily_wrapper_discoverability",
            "the green-read summary now says the direct daily-wrapper validator should stay discoverable for wrapper fallback, wrapper-generated current-evidence bridge, and direct scorecard gate-boundary guardrails, and that the two wrapper leaves feed inherited wrapper-guardrail inventories broader sweeps should preserve rather than flatten",
        ),
        require_contains(
            actual,
            "- the dated working-status note and its direct validator stay discoverable when the question is production basket vs demo lane",
            "green_read_working_status_discoverability",
            "the green-read summary still says the dated working-status note and its direct validator should stay discoverable",
        ),
        require_contains(
            actual,
            "- the direct report-surfaces validator stays discoverable when the question is shareable wording, presentation drift, or report-trust-path wording, including the README-inherited wrapper-leaf source-of-truth note that the narrative rollup is supposed to preserve rather than flatten away",
            "green_read_report_surfaces_discoverability",
            "the green-read summary now says the direct report-surfaces validator should stay discoverable for shareable wording drift, including the inherited README wrapper-note preservation contract",
        ),
        require_contains(
            actual,
            "- the shareable report trust path stays explicit: use `Superfecta_Project_Report_2026-04-15.html` as the validated trust anchor, `Superfecta_Project_Report_2026-04-15.pdf` as its derivative export, and treat `Superfecta_Project_Report.html`, `Superfecta_Project_Report.pdf`, `Superfecta_Project_Report.docx`, `Superfecta Prediction - Quick Start Guide.pdf`, and `OpenClaw Prompt.docx` as legacy aliases only",
            "green_read_report_alias_policy",
            "the green-read summary now says the dated HTML file is the trust anchor, the dated PDF is its derivative export, and the undated HTML/PDF/DOCX report aliases, old quick-start PDF, and historical prompt DOCX stay legacy-only aliases",
        ),
        require_contains(
            actual,
            "- the main comparison plus narrow OP / downstream-XGBoost / recommender-scope comparison artifacts stay discoverable instead of becoming filename-only knowledge, with the OP-anchor route naming source-byte provenance plus readable boundary text as reproducibility/no-new-evidence metadata rather than promotion or live-profitability evidence",
            "green_read_narrow_discoverability",
            "the green-read summary still says the main comparison and narrow comparison artifacts should stay discoverable, including the OP-anchor provenance-only route",
        ),
        require_contains(
            actual,
            "- the full-data XGBoost retrain artifact and its direct validator stay discoverable as model-fit reproducibility metadata only, not a paper-trade signal, deployment route, live-profitability claim, bankroll guide, or real-money evidence",
            "green_read_full_data_retrain_discoverability",
            "the green-read summary now keeps the full-data retrain artifact and validator discoverable while preserving the no-paper/no-live-profitability/no-real-money boundary",
        ),
        require_contains(
            actual,
            "- the validation ladder now keeps the parent-rollup artifact-reuse shortcut visible too, but only when the underlying child validator outputs are already fresh",
            "green_read_reuse_shortcut_discoverability",
            "the green-read summary now says the parent-rollup artifact-reuse shortcut should stay visible, with the guardrail that it is only honest when the child validator outputs are already fresh",
        ),
        require_contains(
            actual,
            f"- **Daily operating path**: read `PAPER_TRADE_NOW.md` first while keeping `PAPER_TRADE_NOW.json` paired as the machine-readable sibling with `operator_read_gate`, read `CURRENT_EVIDENCE_SUMMARY.md` before turning current paper totals or OP_REFINED positive-CI wording into a Cole update and {current_context.combined_operator_route_instruction}, use its `scorecard_audit_route` before checking copied gate/ranking/CI-only/timezone/no-BAQ synchronization drift, use its `rebuild_validation_contract` before rebuilding or quoting the bridge after source-byte changes, then the preflight note and Phase 7 current paper basket, then Phase 8 shadow",
            "daily_path_bottom_line",
            "the bottom line now says daily operators should read the current-evidence bridge, use the combined operator_status_context/source_freshness/operator_read_gate route before turning current paper totals or OP_REFINED positive-CI wording into a Cole update, and use scorecard_audit_route before copied-gate synchronization checks",
        ),
        require_contains(
            actual,
            "- **Research / deployment path**: start with `forward_evidence_scorecard.txt`, use `CURRENT_EVIDENCE_SUMMARY.md` only to bridge frozen posture into current paper context, then drop into the decision cards only if the scorecard leaves a real question unanswered",
            "research_path_bottom_line",
            "the bottom line still says to start research-side reads with the scorecard while treating CURRENT_EVIDENCE_SUMMARY as a frozen-to-current bridge, not a replacement for decision-card evidence",
        ),
        require_contains(
            actual,
            "- **Safest anchor inside the live family**: `OP_DURABLE_K7`",
            "anchor_bottom_line",
            "the bottom line still names OP_DURABLE_K7 as the safest live-family anchor",
        ),
        require_contains(
            actual,
            "| `out/paper_trade_preflight_note.txt` | `present` | Standalone manual preflight-helper cache / scratch output. Do not use it as the validated live calendar surface; daily operator reads should use the run-root `out/daily_portfolio_runs/YYYY-MM-DD/preflight_note.txt` / `.json` pair generated by the wrapper. |",
            "top_level_preflight_scratch_not_daily_driver",
            "the do-not-drive-daily table now separates the stale-prone top-level manual preflight cache from the wrapper-generated run-root preflight note used by operator reads",
        ),
        require(
            EVIDENCE_BOUNDARY.get("artifact_role") == "daily artifact guide / day-to-day repo-map validator"
            and EVIDENCE_BOUNDARY.get("valid_evidence_scope") == guide.VALID_EVIDENCE_SCOPE
            and EVIDENCE_BOUNDARY.get("not_new_forward_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_settled_roi_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_live_profitability_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_real_money_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_promotion_readiness_evidence") is True
            and EVIDENCE_BOUNDARY.get("daily_guide_validator_passes_are_navigation_metadata_only") is True
            and "ROI-complete settled paper rows" in EVIDENCE_BOUNDARY.get("stronger_forward_confidence_requires", [])
            and "do not promote OP_REFINED_K7 or Phase 8 from daily-guide validation cleanliness" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "do not substitute BAQ for BEL" in EVIDENCE_BOUNDARY.get("non_goals", []),
            "daily_artifact_guide_json_publishes_machine_readable_evidence_boundary",
            "daily artifact guide validator JSON now publishes a machine-readable evidence_boundary block with the raw valid_evidence_scope that keeps daily read-order, quiet-vs-broken triage, validator-routing, latest-run pointers, and saved-artifact discoverability separate from settled ROI, live profitability, promotion readiness, real-money evidence, OP_REFINED_K7 / Phase 8 promotion, odds-only XGBoost reopening, and BAQ/BEL substitution",
        ),
        require(
            TMP_PARENT.is_relative_to(BASE) and TMP_PARENT.exists(),
            "fixture_scratch_root_project_local",
            f"daily artifact guide preflight and current-evidence fixtures write under project-local temporary root {TMP_PARENT}, cleared before fixture checks",
        ),
        require(
            TMP_PARENT.is_relative_to(BASE) and TMP_PARENT.exists(),
            "fixture_scratch_metadata_published",
            "daily artifact guide validation publishes top-level project-local scratch metadata so parent navigation rollups can verify the cleared fixture root without parsing markdown prose",
        ),
        require_paths_exist(
            [
                BASE / "COLE_STATUS_AND_PLAN.md",
                BASE / "PAPER_TRADE_NOW.md",
                BASE / "PAPER_TRADE_NOW.json",
                BASE / "OPS_HISTORY.md",
                BASE / "CURRENT_EVIDENCE_SUMMARY.md",
                BASE / "current_evidence_summary.json",
                BASE / "paper_trade_settlement_helper.py",
                BASE / "paper_trade_settlement_audit.py",
                BASE / "out" / "paper_trade_settlement_audit.md",
                BASE / "forward_evidence_scorecard.txt",
                BASE / "SCORECARD_RANKING_CONTRACT_AUDIT.md",
                BASE / "scorecard_ranking_contract_audit.json",
                BASE / "validate_scorecard_ranking_contract_audit.py",
                BASE / "compare_main_approaches.md",
                BASE / "VALIDATION_QUICKSTART.md",
                BASE / "validate_validation_quickstart.py",
                BASE / "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md",
                BASE / "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json",
                BASE / "validate_paper_trade_source_chain_guardrails.py",
                BASE / "validate_forward_evidence_scorecard.py",
                BASE / "validate_current_evidence_summary.py",
                BASE / "validate_decision_cards_suite.py",
                BASE / "validate_frozen_evidence_chain.py",
                BASE / "validate_compare_main_approaches.py",
                BASE / "validate_paper_trade_operator_suite.py",
                BASE / "validate_cache_only_messaging.py",
                BASE / "validate_partial_cache_messaging.py",
                BASE / "validate_paper_trade_pipeline.py",
                BASE / "validate_scanner_sidecar_resolution_contract.py",
                BASE / "validate_paper_trade_recommender.py",
                BASE / "LIVE_SCANNER_USAGE.md",
                BASE / "validate_live_scanner_usage.py",
                BASE / "EV_TICKET_ENGINE_USAGE.md",
                BASE / "validate_ev_ticket_engine_usage.py",
                BASE / "validate_ev_ticket_engine.py",
                BASE / "validate_paper_trade_logger.py",
                BASE / "validate_paper_trade_preflight_note.py",
                BASE / "validate_paper_trade_status_summary.py",
                BASE / "validate_paper_trade_now.py",
                BASE / "validate_current_hierarchy_language.py",
                BASE / "validate_paper_trade_settlement_sync.py",
                BASE / "validate_paper_trade_settlement_helper.py",
                BASE / "validate_paper_trade_settlement_audit.py",
                BASE / "validate_paper_trade_next_steps.py",
                BASE / "validate_paper_trade_forward_check.py",
                BASE / "validate_paper_trade_lane_monitor.py",
                BASE / "validate_paper_trade_daily_summary.py",
                BASE / "validate_paper_trade_lane_summary.py",
                BASE / "refresh_live_paper_trade_surfaces.py",
                BASE / "validate_refresh_live_paper_trade_surfaces.py",
                BASE / "validate_run_daily_portfolio_observation.py",
                BASE / "WORKING_STATUS_REPORT_2026-04-15.md",
                BASE / "validate_working_status_report.py",
                BASE / "validate_report_surfaces.py",
                BASE / "OP_FAMILY_DECISION.md",
                BASE / "validate_op_family_decision.py",
                BASE / "CROSS_FAMILY_DECISION.md",
                BASE / "validate_cross_family_decision.py",
                BASE / "PORTFOLIO_DECISION_CARD.md",
                BASE / "validate_portfolio_decision_card.py",
                BASE / "METHOD_FAMILY_DECISION.md",
                BASE / "validate_method_family_decision_card.py",
                BASE / "OP_ANCHOR_METHOD_COMPARISON.md",
                BASE / "AB_DOWNSTREAM_COMPARISON.md",
                BASE / "FULL_DATA_RETRAIN_ARTIFACTS.md",
                BASE / "validate_full_data_retrain_artifacts.py",
                BASE / "PHASE7_REPORT.md",
                BASE / "validate_phase7_report_caution.py",
                BASE / "DIAGNOSE_CD_SELECTION.md",
                BASE / "validate_diagnose_cd_selection_caution.py",
                BASE / "BACKTEST_REPORT.md",
                BASE / "validate_backtest_report_caution.py",
                BASE / "compare_recommender_scope_paths.md",
                BASE / "validate_op_anchor_method_comparison.py",
                BASE / "validate_ab_downstream_comparison.py",
                BASE / "validate_compare_recommender_scope_paths.py",
            ],
            "core_daily_and_decision_artifacts_exist",
            "the core daily-use, saved-live rebuild, validation-ladder, and decision-time artifacts highlighted by the guide all exist on disk, so the guide is not quietly routing Cole to stale paths",
        ),
    ]


def build_summary(checks: list[dict[str, Any]]) -> dict[str, Any]:
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    current_context = guide.current_evidence_context()
    scorecard_gates = scorecard_gate_context()
    ci_only_context = scorecard_ci_only_context()
    operator_gate = operator_read_gate_context()
    scorecard_audit_route = scorecard_audit_route_context()
    rebuild_contract = rebuild_validation_contract_context()
    source_chain = source_chain_context()
    return {
        "suite_status": status,
        "valid_evidence_scope": guide.VALID_EVIDENCE_SCOPE,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": {
            key: value for key, value in scorecard_gates.items() if key != "source_snippet"
        },
        "current_evidence_scorecard_ci_only_read": ci_only_context,
        "current_evidence_operator_read_gate_read": operator_gate,
        "current_evidence_scorecard_audit_route_read": scorecard_audit_route,
        "current_evidence_rebuild_validation_contract_read": rebuild_contract,
        "source_chain_guardrail_matrix_read": source_chain,
        "scratch": {
            "tmp_parent": str(TMP_PARENT),
            "tmp_parent_is_project_local": TMP_PARENT.is_relative_to(BASE),
            "tmp_parent_cleared_before_fixture_run": True,
        },
        "summary": {
            "suite_read": (
                "daily artifact guide still matches its generator, keeps the validation ladder plus the main-comparison, narrow comparison, cross-family current-paper snapshot route, OP-anchor source-provenance plus readable-boundary route, full-data retrain artifact route, paper-trade usage runbook route, source-chain matrix, scorecard ranking-contract audit / gate-floor route, and direct source-layer paper-trade chain routes visible, now exposes `PAPER_TRADE_USAGE.md` / `validate_paper_trade_usage.py` as the hands-on bridge from daily top cards into exact commands while preserving the OP-anchor source-provenance plus readable-boundary route and audit-only fingerprint / boundary-text boundary, now says a fresh source-chain matrix should propagate through the operator suite's embedded `auxiliary_source_chain_matrix` and parent-side matrix-payload rebuild parity, with the project sweep reading that as readiness-only parent metadata rather than a flattened umbrella green light, keeps the direct settlement-audit route discoverable for ledger-completeness / ROI-coverage action routing plus blank signal-key versus blank settlement-key repair labeling, with the main-comparison route now explicit about the matched CSV/markdown/JSON bundle and evidence-scope decision gates, "
                f"keeps the direct current-evidence summary, main-comparison, main-status, pipeline, scanner-sidecar path-resolution, recommender, EV-sizing, logger, live-scanner usage, preflight-note, status-summary, right-now, current-hierarchy, settlement-sync, settlement-helper, next-steps, forward-check, lane-monitor, daily-summary, lane-summary, saved-live refresh, and real daily-wrapper validators plus the dated working-status note and direct report-surfaces validator discoverable, with the live-scanner usage route preserving API-access-failure handling such as HTTP 403 including refresh_daily_wrapper_before_evidence_read plus ./run_daily_portfolio_observation.sh as operator routing only, with the scanner-sidecar path-resolution route preserving pipeline-declared scanner_status_path precedence over stale default live_scan.status.json files as routing-fixture metadata only, with the main-status route preserving `status_doc_base_api_access_route_documented` for base API-access / HTTP 403 status-summary action-recheck route edits before lane enrichment, with the current-evidence route covering source consistency, CSV settled_ts gap exclusion, operator-status context, CD-only current rule mix, scorecard-sourced OP_REFINED CI-only routing with ci_only_promotion_allowed=false, scorecard_audit_route synchronization routing to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization metadata only, rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only, bridge-published current gates source-matched to forward_evidence_scorecard.json decision_gate_minimums, {current_context.bridge_queue_navigation}, branch-specific scanner/API-failure wording only when that route is present, source freshness / refresh-before-right-now-use routing, operator-read-gate routing, and no-new-forward-evidence / no-promotion / no-real-money boundaries as navigation metadata rather than performance proof, with the current-hierarchy route covering `live_hierarchy`, `primary_companion`, and compatibility-only `primary_shadow` edits as hierarchy wording / metadata routing only rather than ROI, promotion, live-profitability, or real-money evidence, with the daily-summary and lane-summary routes now exposing the stronger full routed quick-jump / quick-files bundle contracts plus explicit primary/shadow recent-run context visibility and the daily-summary settlement-audit action-line / no-new-evidence contract, the report-surfaces route now explicitly covering shareable wording, presentation drift, the dated report trust path, and the README-inherited wrapper-leaf source-of-truth note the narrative rollup should preserve rather than flatten away, and the status-summary route explicitly covering missing-scan-output fallbacks, API-access stale-cache fallback metadata, empty/unreadable scanner sidecars, pipeline-recorded empty/unreadable scanner-status states, wrapper-only required-pipeline sidecar issues, the saved recommender/logger failure detail line, and API-access / HTTP 403 action-recheck route preservation before lane enrichment, while the quiet-vs-broken triage path now also frames green cache-only / partial-cache messaging validators as cache-edge routing / reproducibility metadata only rather than quiet-day, scanner, ROI, profitability, promotion, or real-money evidence and tells readers to follow the direct pipeline/scanner sidecar pointers surfaced in PAPER_TRADE_NOW on issue days, while the top-card entry now says stale cards carry inherited snapshot context rather than current-day state and PAPER_TRADE_NOW.json is the matched machine-readable sibling with operator_read_gate rather than separate evidence, while the direct right-now validator is discoverable for top-card text/markdown/JSON parity, placeholder-boundary, and operator-read-gate questions, while the refresh path now names the source-matched rebuild route for persisted operator artifacts, says that rerendering those saved surfaces is not new forward evidence, now calls out rebuilt daily summaries inheriting refreshed top-level routed top-card snapshot lines plus rebuilt PAPER_TRADE_NOW JSON parity, recent-run-context plus why-now preservation when current lane artifacts provide it, keeps stale rebuilt cards on the inherited-snapshot honesty contract, says the distinct `--latest-only` newest-run versus `--skip-top-level` top-card-preservation maintenance boundaries stay visible, and now says optional `--as-of-date` freshness pinning reports whether it was actually applied or skipped, while the guide also points wrapper-fallback and wrapper-generated `CURRENT_EVIDENCE_SUMMARY` refresh/placeholder plus source-backed recommendation-context/open-row separation questions to the real daily-wrapper validator and says the two wrapper leaves are the source-of-truth guardrail reports broader operator/project sweeps should preserve rather than flatten, while the umbrella operator-suite plus top-level project-sweep ladder routes now say plainly that they are alignment/readiness checks rather than new evidence, "
                f"while the saved daily-use guide and its direct validator report path stay pinned across the daily ladder, including direct settlement-audit action-line guidance, direct current-hierarchy guardrail guidance for top-card/daily-summary role wording, and full-data XGBoost retrain validation as model-fit reproducibility metadata only rather than paper-trade / live-profitability / bankroll / real-money evidence, the daily-guide source markdown and direct validator report now expose exact `valid_evidence_scope={guide.VALID_EVIDENCE_SCOPE}` as daily navigation/readiness metadata only, the daily-guide gate-source note now reads forward_evidence_scorecard.json decision_gate_minimums directly and preserves anchor_displacement=30, phase8_promotion_review=20, real_money_discussion=100, and the no-BAQ-as-BEL prerequisite as future paper-observation floors rather than cleared gates, and the daily artifact guide validator JSON now publishes a machine-readable evidence_boundary as daily navigation/readiness metadata only plus scorecard_decision_gate_minimums_read, current_evidence_operator_read_gate_read, current_evidence_scorecard_audit_route_read, and current_evidence_rebuild_validation_contract_read as daily navigation/readiness metadata only rather than settled ROI / live profitability / promotion readiness / real-money evidence, keeps the shareable report trust path explicit so the dated HTML trust anchor and dated PDF derivative export stay preferred while the undated HTML/PDF/DOCX report aliases, old quick-start PDF, and historical OpenClaw prompt DOCX stay legacy-only aliases, now makes explicit recommender/logger pipeline-failure recovery visible in the quiet-day cheat sheet and direct-validator ladder, pins the latest daily-run root plus its key sidecars to real files on disk, keeps the shadow lane explicit as OP_REFINED_K7 the closest challenger with KEE_K9 / SA_K9 / DMR_FALL_K7 still observation-only pockets, and preserves the current daily path of PAPER_TRADE_NOW first with PAPER_TRADE_NOW.json paired as its machine-readable sibling plus operator_read_gate, CURRENT_EVIDENCE_SUMMARY before current-paper status updates plus its scorecard_audit_route before copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks and its rebuild_validation_contract before bridge rebuilds or quotes after source-byte changes, the source-derived combined operator_status_context/source_freshness/operator_read_gate route as `{current_context.combined_operator_route_instruction}`, the scorecard audit as the direct route for copied gate-floor/ranking/CI-only drift, the scorecard as the fastest research-side read, and OP_DURABLE_K7 as the safest anchor"
            )
        },
    }


def write_outputs(summary: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    scorecard_gates = summary["scorecard_decision_gate_minimums_read"]
    ci_only_read = summary["current_evidence_scorecard_ci_only_read"]
    operator_gate = summary["current_evidence_operator_read_gate_read"]
    scorecard_audit_route = summary["current_evidence_scorecard_audit_route_read"]
    rebuild_contract = summary["current_evidence_rebuild_validation_contract_read"]

    lines: list[str] = [
        "# Daily Artifact Guide Validation",
        "",
        "This report checks that `DAILY_ARTIFACT_GUIDE.md` still matches its generator and current validation guidance.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Target file: `{DOC.name}`",
        f"- Temporary fixture root: `{summary['scratch']['tmp_parent']}` (cleared before fixture checks)",
        f"- Checks: {summary['check_count']}",
        f"- Result: {summary['suite_status'].upper()}",
        "",
        "## Checks",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]

    for check in summary["checks"]:
        lines.append(f"| {check['check']} | {check['status'].upper()} | {check['detail']} |")

    boundary = summary["evidence_boundary"]
    lines.extend([
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {boundary['artifact_role']}",
        f"- valid_evidence_scope={boundary['valid_evidence_scope']}",
        f"- Valid use: {boundary['valid_use']}",
        "- This green read is daily navigation/readiness metadata only: it is not new forward evidence, a live paper-trade ledger, current-day scanner output, settled ROI, live profitability, promotion readiness, or real-money evidence.",
        "- Stronger forward confidence still requires qualifying live paper signals, ROI-complete settled paper rows, settlement-quality checks, or other real forward observations.",
        "- Non-goals: do not promote OP_REFINED_K7 / Phase 8, reopen current odds-only XGBoost, substitute BAQ for BEL, or treat documented daily artifact paths as real-money evidence from this validator pass.",
        "",
        "## Scorecard Gate Source",
        "",
        f"- Source: `{scorecard_gates['source']}` `{scorecard_gates['source_path']}`",
        f"- anchor_displacement={scorecard_gates['anchor_displacement_min_roi_complete_settled_observations']}",
        f"- phase8_promotion_review={scorecard_gates['phase8_promotion_review_min_roi_complete_settled_observations']}",
        f"- real_money_discussion={scorecard_gates['real_money_discussion_min_total_settled_observations_with_usable_roi']}",
        f"- no BAQ-as-BEL required={scorecard_gates['real_money_no_baq_as_bel_required']}",
        "",
        "## Current-Evidence CI-Only Route",
        "",
        f"- Source: `{ci_only_read['source']}`",
        f"- Candidate: `{ci_only_read['candidate_rule_id']}`",
        f"- Current anchor: `{ci_only_read['current_anchor_rule_id']}`",
        f"- ci_only_promotion_allowed={ci_only_read['ci_only_promotion_allowed']}",
        f"- Current bridge matches scorecard diagnostic={ci_only_read['current_matches_scorecard_diagnostic']}",
        "",
        "## Current-Evidence Operator Read Gate",
        "",
        f"- Source: `{operator_gate['source']}` `{operator_gate['source_path']}`",
        f"- Gate status: `{operator_gate['gate_status']}`",
        f"- Requires refresh before evidence read={operator_gate['requires_refresh_before_evidence_read']}",
        f"- API-access failure context={operator_gate['has_api_access_failure_context']}",
        f"- Scanner-failure boundary={operator_gate['has_scanner_failure_boundary']}",
        f"- Stale-cache fallback context={operator_gate['has_stale_cache_fallback_context']}",
        f"- Recommended command: `{operator_gate['recommended_command']}`",
        "- Boundary: instruction/evidence-read routing only, not no-target, clean-empty, bet-readiness, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "",
        "## Current-Evidence Scorecard Audit Route",
        "",
        f"- Source: `{scorecard_audit_route['source']}` `{scorecard_audit_route['source_path']}`",
        f"- Markdown route: `{scorecard_audit_route['markdown_path']}`",
        f"- JSON route: `{scorecard_audit_route['json_path']}`",
        f"- Validator command: `{scorecard_audit_route['validator_command']}`",
        f"- Gate-floor source: `{scorecard_audit_route['gate_floor_source']}`",
        f"- Valid use: {scorecard_audit_route['valid_use']}",
        "- Boundary: report-synchronization metadata only, not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "",
        "## Current-Evidence Rebuild Order",
        "",
        f"- Source: `{rebuild_contract['source']}` `{rebuild_contract['source_path']}`",
        f"- Commands: {' -> '.join(f'`{command}`' for command in rebuild_contract['upstream_refresh_order_commands'])}",
        f"- Requires settlement audit before bridge on source-byte changes={rebuild_contract['requires_settlement_audit_refresh_before_bridge_when_source_bytes_change']}",
        f"- Requires source consistency before quoting current totals={rebuild_contract['requires_source_consistency_before_quoting_current_totals']}",
        "- Boundary: provenance/rebuild metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "",
        "## Current Read",
        "",
        f"- {summary['summary']['suite_read']}",
        "",
        "## Bottom Line",
        "",
        "If this validator stays green, `DAILY_ARTIFACT_GUIDE.md` remains the fastest daily-use map for separating quiet days from broken days, finding the direct operator/report validator routes, and following the real sidecar/trust-path pointers instead of jumping straight to umbrella sweeps.",
        "That green read is daily navigation/readiness alignment, not new forward evidence by itself.",
    ])

    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    prepare_tmp_parent()
    actual_before = load_text(DOC)
    expected = build_expected_text()
    actual_after = load_text(DOC)
    checks = build_checks(actual_after, expected)
    summary = build_summary(checks)
    write_outputs(summary)
    print(f"Wrote {MD_PATH}")
    print(f"Wrote {JSON_PATH}")
    return 0 if summary["suite_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
