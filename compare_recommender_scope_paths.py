#!/usr/bin/env python3
"""
Compare the default selective recommender path against the explicit
--allow-all-combos override on fixed stub races.

Purpose:
- make the Phase 7 combo-scope guardrail visible in one report-safe artifact
- show how default filtering differs from explicit scope widening on the same races
- avoid implying that widened ticket scope is a paper-promotion case
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from ev_ticket_engine import EngineConfig, build_race_plan
from paper_trade_recommender import combo_allowed, filter_predictions

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "compare_recommender_scope_paths.py"
OUT_MD = BASE / "compare_recommender_scope_paths.md"
OUT_JSON = BASE / "compare_recommender_scope_paths.json"
CROSS_FAMILY_CSV = BASE / "cross_family_decision_card.csv"
FORWARD_SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
EV_TICKET_ENGINE = BASE / "ev_ticket_engine.py"
PAPER_TRADE_RECOMMENDER = BASE / "paper_trade_recommender.py"
VALID_EVIDENCE_SCOPE = "selective_vs_allow_all_recommender_scope_counterfactual_only"
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
EVIDENCE_BOUNDARY = {
    "artifact_role": "selective-vs-allow-all recommender scope guardrail",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "valid_use": "controlled counterfactual for how the explicit allow-all-combos override widens ticket scope on fixed stub races",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_observed_settlement_pnl": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_anchor_change_evidence": True,
    "not_current_paper_scope_change_evidence": True,
    "allow_all_override_role": "research_only_counterfactual",
    "default_scope_role": "current_paper_default",
    "scope_change_requires": [
        "ROI-complete settled paper observations",
        "scorecard-sourced 30/20/100 gate review",
        "settlement-quality checks",
        "no BAQ-as-BEL substitution",
        "human review before any real-money discussion",
    ],
    "non_goals": [
        "do not treat widened stub-race EV as observed settlement P&L",
        "do not use allow-all counterfactuals to widen the current paper default",
        "do not promote the same-family shadow rule from this artifact",
        "do not displace the current paper anchor from this artifact",
        "do not substitute BAQ for BEL",
        "do not discuss real-money scaling from this artifact",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare selective versus allow-all recommender scope paths")
    parser.add_argument("--cross-family-csv", default=str(CROSS_FAMILY_CSV), help="cross-family decision CSV path")
    parser.add_argument("--scorecard-json", default=str(FORWARD_SCORECARD_JSON), help="forward-evidence scorecard JSON path")
    parser.add_argument("--current-evidence-json", default=str(CURRENT_EVIDENCE_JSON), help="current-evidence bridge JSON path")
    parser.add_argument("--md-output", default=str(OUT_MD), help="markdown output path")
    parser.add_argument("--json-output", default=str(OUT_JSON), help="JSON output path")
    return parser.parse_args()


def signal_hit(
    scan_ts: str,
    rule_id: str,
    race_id: str,
    favorite_program: str,
    *,
    track: str = "OP",
    card_name: str = "Oaklawn Park",
    race_number: str = "7",
    underneath_programs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "scan_ts": scan_ts,
        "rule_id": rule_id,
        "track": track,
        "card_name": card_name,
        "race_number": race_number,
        "race_id": race_id,
        "favorite_program": favorite_program,
        "underneath_programs": underneath_programs or ["2", "3", "5"],
    }


SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "mixed_universe_op_anchor",
        "label": "Mixed-universe OP anchor race",
        "note": "The selective path already has one allowed BET ticket, but the widened path pulls in two higher-EV off-scope combos that violate the scanner's Phase 7 ticket universe.",
        "hit": signal_hit("2026-04-20T11:00:00", "OP_DURABLE_K7", "OP-2026-04-20-R7", "1"),
        "rows": [
            {"combo": "1-2-3-5", "jointProb": 0.02, "predicted_payout": 120.0, "rank": 1},
            {"combo": "9-2-3-5", "jointProb": 0.05, "predicted_payout": 80.0, "rank": 2},
            {"combo": "1-2-3-4", "jointProb": 0.03, "predicted_payout": 90.0, "rank": 3},
        ],
    },
    {
        "name": "off_universe_only_op_anchor",
        "label": "Off-universe-only OP anchor race",
        "note": "The selective path correctly says NO BET because nothing matches the scanner's allowed scope, while the widened path creates a model-ranked BET only because the scope guardrail was removed.",
        "hit": signal_hit("2026-04-20T11:05:00", "OP_DURABLE_K7", "OP-2026-04-20-R8", "1"),
        "rows": [
            {"combo": "9-8-7-6", "jointProb": 0.08, "predicted_payout": 150.0, "rank": 1},
        ],
    },
]


def load_shadow_read(cross_family_csv: Path = CROSS_FAMILY_CSV) -> dict[str, str]:
    cross_df = pd.read_csv(cross_family_csv)
    by_shadow = {row["shadow_rank"]: row for _, row in cross_df.iterrows() if str(row.get("shadow_rank", ""))}
    return {
        "anchor": str(by_shadow["LIVE_DEFAULT"]["rule_id"]),
        "primary_shadow": str(by_shadow["PRIMARY_SHADOW"]["rule_id"]),
        "primary_companion": str(by_shadow["PRIMARY_SHADOW"]["rule_id"]),
        "secondary_shadow": str(by_shadow["SECONDARY_SHADOW"]["rule_id"]),
    }


def require_dict_key(mapping: dict[str, Any], key: str, dotted_parent: str, source_path: Path) -> Any:
    if key not in mapping:
        raise ValueError(f"{source_path.name} is missing {dotted_parent}.{key}")
    return mapping[key]


def require_positive_int(value: Any, dotted_path: str, source_path: Path) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{source_path.name} {dotted_path} must be a positive integer")
    return value


def require_str_list(value: Any, dotted_path: str, source_path: Path) -> list[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise ValueError(f"{source_path.name} {dotted_path} must be a string list")
    return list(value)


def load_scorecard_gate_summary(scorecard_json: Path = FORWARD_SCORECARD_JSON) -> dict[str, Any]:
    payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
    gates = payload.get("decision_gate_minimums")
    if not isinstance(gates, dict):
        raise ValueError(f"{scorecard_json.name} is missing decision_gate_minimums")

    anchor_gate = require_dict_key(gates, "anchor_displacement", "decision_gate_minimums", scorecard_json)
    phase8_gate = require_dict_key(gates, "phase8_promotion_review", "decision_gate_minimums", scorecard_json)
    real_money_gate = require_dict_key(gates, "real_money_discussion", "decision_gate_minimums", scorecard_json)
    if not isinstance(anchor_gate, dict):
        raise ValueError(f"{scorecard_json.name} decision_gate_minimums.anchor_displacement must be an object")
    if not isinstance(phase8_gate, dict):
        raise ValueError(f"{scorecard_json.name} decision_gate_minimums.phase8_promotion_review must be an object")
    if not isinstance(real_money_gate, dict):
        raise ValueError(f"{scorecard_json.name} decision_gate_minimums.real_money_discussion must be an object")

    anchor_min = require_positive_int(
        require_dict_key(
            anchor_gate,
            "min_roi_complete_settled_observations",
            "decision_gate_minimums.anchor_displacement",
            scorecard_json,
        ),
        "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
        scorecard_json,
    )
    phase8_min = require_positive_int(
        require_dict_key(
            phase8_gate,
            "min_roi_complete_settled_observations",
            "decision_gate_minimums.phase8_promotion_review",
            scorecard_json,
        ),
        "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
        scorecard_json,
    )
    real_money_min = require_positive_int(
        require_dict_key(
            real_money_gate,
            "min_total_settled_observations_with_usable_roi",
            "decision_gate_minimums.real_money_discussion",
            scorecard_json,
        ),
        "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
        scorecard_json,
    )
    real_money_requires = require_str_list(
        require_dict_key(
            real_money_gate,
            "also_requires",
            "decision_gate_minimums.real_money_discussion",
            scorecard_json,
        ),
        "decision_gate_minimums.real_money_discussion.also_requires",
        scorecard_json,
    )
    if "no BAQ-as-BEL substitution" not in real_money_requires:
        raise ValueError(
            f"{scorecard_json.name} decision_gate_minimums.real_money_discussion.also_requires "
            "must include no BAQ-as-BEL substitution"
        )

    return {
        "source": scorecard_json.name,
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_no_baq_as_bel_required": True,
        "read": (
            "widened scope comparisons are counterfactual research only; current paper scope changes still require "
            "scorecard-sourced ROI-complete observation gates and the no-BAQ-as-BEL prerequisite"
        ),
    }


def load_scorecard_audit_route(current_evidence_json: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    current_evidence_json = Path(current_evidence_json)
    payload = json.loads(current_evidence_json.read_text(encoding="utf-8"))
    route = payload.get("scorecard_audit_route")
    if not isinstance(route, dict):
        raise ValueError(f"{current_evidence_json.name} is missing scorecard_audit_route")
    for key, expected in EXPECTED_SCORECARD_AUDIT_ROUTE.items():
        if route.get(key) != expected:
            raise ValueError(f"{current_evidence_json.name} scorecard_audit_route.{key} drifted")
    if route.get("gate_floor_snapshot") != EXPECTED_SCORECARD_AUDIT_GATE_FLOOR_SNAPSHOT:
        raise ValueError(f"{current_evidence_json.name} scorecard_audit_route.gate_floor_snapshot drifted")
    for flag in REQUIRED_SCORECARD_AUDIT_ROUTE_FLAGS:
        if route.get(flag) is not True:
            raise ValueError(f"{current_evidence_json.name} scorecard_audit_route.{flag} must be true")
    route_read = str(route.get("route_read") or "")
    for phrase in REQUIRED_SCORECARD_AUDIT_ROUTE_READ_PHRASES:
        if phrase not in route_read:
            raise ValueError(f"{current_evidence_json.name} scorecard_audit_route.route_read missing {phrase!r}")
    copy = json.loads(json.dumps(route))
    copy["source"] = current_evidence_json.name
    copy["source_path"] = "scorecard_audit_route"
    return copy


def load_rebuild_validation_contract(current_evidence_json: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    current_evidence_json = Path(current_evidence_json)
    payload = json.loads(current_evidence_json.read_text(encoding="utf-8"))
    contract = payload.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise ValueError(f"{current_evidence_json.name} is missing rebuild_validation_contract")
    upstream_refresh_order = contract.get("upstream_refresh_order")
    if not isinstance(upstream_refresh_order, list):
        raise ValueError(f"{current_evidence_json.name} rebuild_validation_contract.upstream_refresh_order must be a list")
    commands = [
        str(row.get("command") or "")
        for row in upstream_refresh_order
        if isinstance(row, dict)
    ]
    if commands != EXPECTED_REBUILD_ORDER_COMMANDS:
        raise ValueError(f"{current_evidence_json.name} rebuild_validation_contract upstream order drifted")
    if contract.get("prerequisite_rebuild_command") != EXPECTED_REBUILD_ORDER_COMMANDS[0]:
        raise ValueError(f"{current_evidence_json.name} rebuild_validation_contract prerequisite command drifted")
    if contract.get("rebuild_command") != EXPECTED_REBUILD_ORDER_COMMANDS[1]:
        raise ValueError(f"{current_evidence_json.name} rebuild_validation_contract rebuild command drifted")
    if contract.get("direct_validation_command") != EXPECTED_REBUILD_ORDER_COMMANDS[2]:
        raise ValueError(f"{current_evidence_json.name} rebuild_validation_contract direct validator command drifted")
    for flag in (
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
        "requires_source_consistency_before_quoting_current_totals",
        "upstream_refresh_order_is_provenance_metadata_only",
        "not_settled_roi_or_real_money_evidence",
    ):
        if contract.get(flag) is not True:
            raise ValueError(f"{current_evidence_json.name} rebuild_validation_contract.{flag} must be true")
    copy = json.loads(json.dumps(contract))
    copy["source"] = current_evidence_json.name
    copy["source_path"] = "rebuild_validation_contract"
    return copy


def fingerprint_file(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(BASE)) if path.is_relative_to(BASE) else str(path),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def build_source_provenance(
    cross_family_csv: Path = CROSS_FAMILY_CSV,
    scorecard_json: Path = FORWARD_SCORECARD_JSON,
    current_evidence_json: Path = CURRENT_EVIDENCE_JSON,
) -> dict[str, Any]:
    return {
        "read": (
            "source fingerprints are reproducibility metadata for the selective-vs-allow-all scope guardrail only; "
            "they are not settled ROI, not promotion readiness, not live profitability, and not real-money evidence"
        ),
        "source_fingerprints": {
            "compare_recommender_scope_paths": fingerprint_file(SCRIPT),
            "cross_family_decision_card": fingerprint_file(cross_family_csv),
            "forward_evidence_scorecard_json": fingerprint_file(scorecard_json),
            "current_evidence_summary_json": fingerprint_file(current_evidence_json),
            "ev_ticket_engine": fingerprint_file(EV_TICKET_ENGINE),
            "paper_trade_recommender": fingerprint_file(PAPER_TRADE_RECOMMENDER),
        },
    }


def plan_summary(plan) -> dict[str, Any]:
    return {
        "decision": plan.decision,
        "reason": plan.reason,
        "tickets_considered": plan.tickets_considered,
        "tickets_selected": plan.tickets_selected,
        "total_stake": plan.total_stake,
        "total_expected_return": plan.total_expected_return,
        "total_expected_profit": plan.total_expected_profit,
        "portfolio_expected_roi_pct": plan.portfolio_expected_roi_pct,
        "ticket_combos": [ticket["combo"] for ticket in plan.tickets],
        "tickets": plan.tickets,
    }


def compare_scenario(case: dict[str, Any], *, rule_id_override: str | None = None) -> dict[str, Any]:
    hit = dict(case["hit"])
    if rule_id_override is not None:
        hit["rule_id"] = rule_id_override
    scored_df = pd.DataFrame(case["rows"])

    default_filtered = filter_predictions(scored_df, hit, allow_all_combos=False)
    widened_filtered = filter_predictions(scored_df, hit, allow_all_combos=True)

    default_plan = build_race_plan(default_filtered, EngineConfig(race_label=case["label"]))
    widened_plan = build_race_plan(widened_filtered, EngineConfig(race_label=case["label"]))

    widened_out_of_scope_tickets = [
        ticket for ticket in widened_plan.tickets
        if not combo_allowed(ticket["combo"], hit)
    ]
    widened_out_of_scope = [ticket["combo"] for ticket in widened_out_of_scope_tickets]
    widened_ticket_count = widened_plan.tickets_selected
    out_of_scope_share_pct = (
        round(100.0 * len(widened_out_of_scope) / widened_ticket_count, 1)
        if widened_ticket_count
        else 0.0
    )
    default_stake = float(default_plan.total_stake)
    widened_stake = float(widened_plan.total_stake)
    default_expected_profit = float(default_plan.total_expected_profit)
    widened_expected_profit = float(widened_plan.total_expected_profit)
    modeled_expected_profit_delta_vs_default = round(widened_expected_profit - default_expected_profit, 2)
    off_scope_stake = round(
        sum(float(ticket.get("recommended_stake", 0.0) or 0.0) for ticket in widened_out_of_scope_tickets),
        2,
    )
    off_scope_expected_profit = round(
        sum(float(ticket.get("expected_profit_dollars", 0.0) or 0.0) for ticket in widened_out_of_scope_tickets),
        2,
    )
    off_scope_expected_profit_share_pct = (
        round(100.0 * off_scope_expected_profit / widened_expected_profit, 1)
        if widened_expected_profit > 0
        else 0.0
    )
    stake_multiple_vs_default = round(widened_stake / default_stake, 1) if default_stake > 0 else None
    stake_delta_vs_default = round(widened_stake - default_stake, 2)
    if stake_multiple_vs_default is None:
        scope_inflation_read = (
            f"widened path creates ${widened_stake:.2f} of new exposure from a selective zero-stake base, "
            f"with {out_of_scope_share_pct:.1f}% of widened tickets off-scope"
        )
    else:
        scope_inflation_read = (
            f"widened path uses {stake_multiple_vs_default:.1f}x the selective stake "
            f"(${widened_stake:.2f} vs ${default_stake:.2f}) and keeps {out_of_scope_share_pct:.1f}% of widened tickets off-scope"
        )
    modeled_ev_boundary_read = (
        f"${modeled_expected_profit_delta_vs_default:+.2f} widened modeled expected-profit lift is stub EV, not observed P&L; "
        f"${off_scope_expected_profit:.2f} ({off_scope_expected_profit_share_pct:.1f}%) of widened modeled expected profit "
        "comes from off-scope tickets"
    )

    return {
        "name": case["name"],
        "label": case["label"],
        "rule_id": hit["rule_id"],
        "track": hit["track"],
        "race_id": hit["race_id"],
        "scored_combo_count": len(scored_df),
        "default_filtered_combo_count": len(default_filtered),
        "allow_all_combo_count": len(widened_filtered),
        "default_path": plan_summary(default_plan),
        "allow_all_path": plan_summary(widened_plan),
        "allow_all_out_of_scope_ticket_count": len(widened_out_of_scope),
        "allow_all_out_of_scope_tickets": widened_out_of_scope,
        "allow_all_out_of_scope_share_pct": out_of_scope_share_pct,
        "allow_all_off_scope_stake": off_scope_stake,
        "allow_all_off_scope_expected_profit": off_scope_expected_profit,
        "allow_all_off_scope_expected_profit_share_pct": off_scope_expected_profit_share_pct,
        "modeled_expected_profit_delta_vs_default": modeled_expected_profit_delta_vs_default,
        "stake_multiple_vs_default": stake_multiple_vs_default,
        "stake_delta_vs_default": stake_delta_vs_default,
        "scope_inflation_read": scope_inflation_read,
        "modeled_ev_boundary_read": modeled_ev_boundary_read,
        "note": case["note"],
    }


def build_markdown(payload: dict[str, Any]) -> str:
    shadow_read = payload["guardrail"]
    gates = payload["scorecard_decision_gate_minimums"]
    scorecard_audit_route = payload["scorecard_audit_route"]
    rebuild_contract = payload["current_evidence_rebuild_validation_contract"]
    rebuild_order = " -> ".join(f"`{command}`" for command in rebuild_contract["upstream_refresh_order_commands"])
    lines = [
        "# Recommender Scope Path Comparison",
        "",
        "This artifact compares the default selective recommender path against the explicit `--allow-all-combos` override on fixed OP-anchor stub races.",
        "",
        "## Guardrail",
        "",
        "- This is a controlled scope comparison, not a paper-promotion test.",
        f"- Valid evidence scope: `valid_evidence_scope={payload.get('valid_evidence_scope') or VALID_EVIDENCE_SCOPE}`.",
        f"- The current paper default still follows the selective Phase 7 path, with `{shadow_read['anchor']}` as the safest current paper anchor.",
        f"- `{shadow_read['primary_companion']}` remains the primary OP/CD paper-basket companion, while `{shadow_read['secondary_shadow']}` stays the smaller same-family OP shadow challenger rather than a promoted default.",
        "- A widened ticket universe can look better on a stub race and still be the wrong paper default, because it steps outside the scanner's allowed selective scope.",
        "- Modeled expected-profit deltas below are stub-race EV diagnostics, not observed settlement P&L or live profitability evidence.",
        "- Machine-readable boundary: `evidence_boundary.not_current_paper_scope_change_evidence=true`; the explicit allow-all override remains `research_only_counterfactual` and does not widen the current paper default.",
        f"- Scorecard-sourced 30/20/100 gates still apply: anchor review needs {gates['anchor_displacement_min_roi_complete_settled_observations']} ROI-complete same-candidate observations, Phase 8 promotion review needs {gates['phase8_promotion_review_min_roi_complete_settled_observations']} ROI-complete shadow observations, and real-money discussion needs {gates['real_money_discussion_min_total_settled_observations_with_usable_roi']} total settled usable-ROI observations plus no BAQ-as-BEL substitution.",
        f"- Scorecard audit route: `{scorecard_audit_route['source']}.{scorecard_audit_route['source_path']}` points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to `{scorecard_audit_route['markdown_path']}` / `{scorecard_audit_route['json_path']}` plus `{scorecard_audit_route['validator_command']}`; this route is synchronization metadata only.",
        f"- Current-evidence rebuild route: `{rebuild_contract['source']}.{rebuild_contract['source_path']}` routes scorecard/rules/signals/settlement-ledger byte changes through {rebuild_order} before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this route is provenance/rebuild metadata only, not scope-change evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "",
        "## Current Read",
        "",
        f"- {payload['summary']['current_read']}",
        f"- This is a scope-only counterfactual around `{shadow_read['anchor']}`, not evidence that widened stub-race tickets should outrank `{shadow_read['primary_companion']}` or the broader frozen paper hierarchy.",
        f"- Gate read: {gates['read']}.",
        f"- Audit route read: {scorecard_audit_route['route_read']} This route is not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        f"- Rebuild route read: source-byte changes that affect current totals require {rebuild_order}; this route is not observed P&L, a paper-default scope change, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "",
        "## Scenario Summary",
        "",
        "| Scenario | Scored combos | Default path | Allow-all path | Stake change vs default | Widened off-scope share | Modeled EV lift source |",
        "|---|---:|---|---|---|---:|---|",
    ]

    for row in payload["scenarios"]:
        default_text = (
            f"{row['default_path']['decision']}"
            f" ({row['default_filtered_combo_count']} combo(s), {row['default_path']['tickets_selected']} ticket(s), "
            f"stake ${row['default_path']['total_stake']:.2f})"
        )
        widened_text = (
            f"{row['allow_all_path']['decision']}"
            f" ({row['allow_all_combo_count']} combo(s), {row['allow_all_path']['tickets_selected']} ticket(s), "
            f"stake ${row['allow_all_path']['total_stake']:.2f})"
        )
        stake_change_text = (
            f"{row['stake_multiple_vs_default']:.1f}x (${row['stake_delta_vs_default']:+.2f})"
            if row['stake_multiple_vs_default'] is not None
            else f"new ${row['allow_all_path']['total_stake']:.2f} exposure"
        )
        modeled_ev_source_text = (
            f"${row['modeled_expected_profit_delta_vs_default']:+.2f} lift; "
            f"${row['allow_all_off_scope_expected_profit']:.2f} / "
            f"{row['allow_all_off_scope_expected_profit_share_pct']:.1f}% off-scope"
        )
        lines.append(
            f"| {row['label']} | {row['scored_combo_count']} | {default_text} | {widened_text} | {stake_change_text} | {row['allow_all_out_of_scope_share_pct']:.1f}% | {modeled_ev_source_text} |"
        )

    for row in payload["scenarios"]:
        lines.extend(
            [
                "",
                f"## {row['label']}",
                "",
                f"- Rule / track: `{row['rule_id']}` on `{row['track']}`",
                f"- Race id: `{row['race_id']}`",
                f"- Scenario note: {row['note']}",
                f"- Default selective path: `{row['default_path']['decision']}` from {row['default_filtered_combo_count']} in-scope combo(s), "
                f"{row['default_path']['tickets_selected']} selected ticket(s), stake `${row['default_path']['total_stake']:.2f}`, expected profit `${row['default_path']['total_expected_profit']:.2f}`",
                f"- Explicit allow-all path: `{row['allow_all_path']['decision']}` from {row['allow_all_combo_count']} scored combo(s), "
                f"{row['allow_all_path']['tickets_selected']} selected ticket(s), stake `${row['allow_all_path']['total_stake']:.2f}`, expected profit `${row['allow_all_path']['total_expected_profit']:.2f}`",
                f"- Widened out-of-scope tickets: {', '.join(f'`{combo}`' for combo in row['allow_all_out_of_scope_tickets']) if row['allow_all_out_of_scope_tickets'] else 'none'}",
                f"- Scope inflation read: {row['scope_inflation_read']}",
                f"- Modeled EV boundary: {row['modeled_ev_boundary_read']}",
                "",
                "### Ticket lists",
                "",
                f"- Default tickets: {', '.join(f'`{combo}`' for combo in row['default_path']['ticket_combos']) if row['default_path']['ticket_combos'] else '`none`'}",
                f"- Allow-all tickets: {', '.join(f'`{combo}`' for combo in row['allow_all_path']['ticket_combos']) if row['allow_all_path']['ticket_combos'] else '`none`'}",
            ]
        )

    lines.extend(
        [
            "",
            "## Source Provenance",
            "",
            "These byte hashes are reproducibility metadata for the scope guardrail only; they are not settled ROI, not promotion readiness, not live profitability, and not real-money evidence.",
            "",
            "| Source | Path | Bytes | SHA-256 |",
            "|---|---|---:|---|",
        ]
    )
    for name, fp in payload["source_provenance"]["source_fingerprints"].items():
        lines.append(f"| `{name}` | `{fp['path']}` | {fp['bytes']} | `{fp['sha256']}` |")

    lines.extend(
        [
            "",
            "## Bottom Line",
            "",
            "- The default selective path remains the honest current paper default because it keeps recommendations inside the scanner's intended ticket universe.",
            "- The explicit `--allow-all-combos` path is useful as a counterfactual research switch, not as evidence that the current paper scope should widen now.",
            "- Any widened expected-profit bump here must be read alongside stake inflation and off-scope ticket share, because the counterfactual often buys that EV by taking materially more exposure outside the scanner's intended universe.",
            "- The modeled expected-profit lift is not observed P&L; in these fixtures the lift comes mostly or entirely from tickets the default selective path would exclude.",
            f"- This comparison is a guardrail artifact: it shows what changes when the scope widens, without claiming that widened stub-race EV should outrank `{shadow_read['anchor']}`, `{shadow_read['primary_companion']}`, or the broader frozen holdout and walk-forward evidence chain.",
        ]
    )
    return "\n".join(lines) + "\n"



def build_payload(
    cross_family_csv: Path = CROSS_FAMILY_CSV,
    scorecard_json: Path = FORWARD_SCORECARD_JSON,
    current_evidence_json: Path = CURRENT_EVIDENCE_JSON,
) -> dict[str, Any]:
    shadow_read = load_shadow_read(cross_family_csv)
    gate_summary = load_scorecard_gate_summary(scorecard_json)
    scorecard_audit_route = load_scorecard_audit_route(current_evidence_json)
    rebuild_contract = load_rebuild_validation_contract(current_evidence_json)
    rebuild_contract["upstream_refresh_order_commands"] = [
        str(row.get("command") or "")
        for row in rebuild_contract.get("upstream_refresh_order", [])
        if isinstance(row, dict)
    ]
    rows = [compare_scenario(case, rule_id_override=shadow_read["anchor"]) for case in SCENARIOS]
    evidence_boundary = json.loads(json.dumps(EVIDENCE_BOUNDARY))
    evidence_boundary["anchor_rule_id"] = shadow_read["anchor"]
    evidence_boundary["primary_companion_rule_id"] = shadow_read["primary_companion"]
    evidence_boundary["same_family_shadow_rule_id"] = shadow_read["secondary_shadow"]
    return {
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "summary": {
            "current_read": "on the same OP-anchor stub races, the default selective recommender path stays inside the scanner's intended ticket universe, while the explicit allow-all override can materially widen tickets, raise stake and off-scope share, turn a selective NO BET into a widened BET, and therefore belongs in research-only counterfactual comparison rather than paper-default logic",
            "modeled_ev_read": "allow-all modeled expected-profit lift is stub-race EV, not observed settlement P&L; the artifact reports how much of that modeled lift comes from tickets outside the selective scanner universe",
        },
        "scenarios": rows,
        "evidence_boundary": evidence_boundary,
        "guardrail": {
            "live_default": "default_selective_phase7_filter",
            "research_override": "allow_all_combos",
            "anchor": shadow_read["anchor"],
            "primary_shadow": shadow_read["primary_shadow"],
            "primary_companion": shadow_read["primary_companion"],
            "secondary_shadow": shadow_read["secondary_shadow"],
            "promotion_read": "not a paper-promotion case",
        },
        "scorecard_decision_gate_minimums": gate_summary,
        "scorecard_audit_route": scorecard_audit_route,
        "current_evidence_rebuild_validation_contract": rebuild_contract,
        "source_provenance": build_source_provenance(cross_family_csv, scorecard_json, current_evidence_json),
    }


def main() -> int:
    args = parse_args()
    cross_family_csv = Path(args.cross_family_csv)
    scorecard_json = Path(args.scorecard_json)
    current_evidence_json = Path(args.current_evidence_json)
    md_output = Path(args.md_output)
    json_output = Path(args.json_output)

    payload = build_payload(
        cross_family_csv=cross_family_csv,
        scorecard_json=scorecard_json,
        current_evidence_json=current_evidence_json,
    )
    json_text = json.dumps(payload, indent=2) + "\n"
    markdown = build_markdown(payload)

    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json_text, encoding="utf-8")
    md_output.write_text(markdown, encoding="utf-8")
    print(markdown, end="")
    print(f"Saved: {md_output.name}")
    print(f"Saved: {json_output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
