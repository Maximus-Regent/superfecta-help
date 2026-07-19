#!/usr/bin/env python3
"""
Validate current live-hierarchy wording across high-traffic project surfaces.

Purpose:
- keep CD_CORE_K8 framed as the primary OP/CD paper-basket companion, not a Phase 8-style shadow promotion
- keep OP_REFINED_K7 framed as the closest same-family shadow/watch challenger
- preserve legacy `primary_shadow` structured keys only when a matching `primary_companion` key is present
- prevent old human-facing "strongest non-anchor shadow" wording from drifting back into current reports/runbooks
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

BASE = Path(__file__).resolve().parent
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
OUT_DIR = BASE / "out" / "status_validation" / "current_hierarchy_language"
OUT_MD = OUT_DIR / "current_hierarchy_language_validation.md"
OUT_JSON = OUT_DIR / "current_hierarchy_language_validation.json"
REBUILD_COMMAND = "python3 validate_current_hierarchy_language.py"
VALID_EVIDENCE_SCOPE = "current_hierarchy_wording_structured_key_compatibility_only"
EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]

CURRENT_HUMAN_SURFACES = [
    "README.md",
    "COLE_STATUS_AND_PLAN.md",
    "PAPER_TRADE_USAGE.md",
    "PAPER_TRADE_NOW.md",
    "PAPER_TRADE_NOW.txt",
    "CURRENT_EVIDENCE_SUMMARY.md",
    "VALIDATION_QUICKSTART.md",
    "DAILY_ARTIFACT_GUIDE.md",
    "LIVE_SCANNER_USAGE.md",
    "OPS_HISTORY.md",
    "out/paper_trade_settlement_audit.md",
    "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md",
    "forward_evidence_scorecard.txt",
    "compare_main_approaches.md",
    "CROSS_FAMILY_DECISION.md",
    "PORTFOLIO_DECISION_CARD.md",
    "METHOD_FAMILY_DECISION.md",
    "OP_ANCHOR_METHOD_COMPARISON.md",
    "AB_DOWNSTREAM_COMPARISON.md",
    "compare_recommender_scope_paths.md",
    "COLE_FULL_REPORT_2026-04-15.md",
    "COLE_PRESENTATION_OUTLINE.md",
]

BANNED_CURRENT_PHRASES = [
    "strongest overall non-anchor shadow",
    "strongest non-anchor shadow",
    "strongest overall shadow",
    "Current live shadow read",
    "active OP/CD paper companion",
    "active OP/CD primary paper basket",
    "lead non-anchor shadow",
    "primary shadow=CD_CORE_K8",
    "selective shadow read anchor=OP_DURABLE_K7",
]

REQUIRED_SURFACE_PHRASES = {
    "README.md": [
        "**Safest current anchor:** `OP_DURABLE_K7`",
        "**Primary paper baseline:** `Phase 7 OP/CD rule-component basket`",
        "**Phase 8 status:** `Phase 8 frozen portfolio` stays `SHADOW ONLY`",
        "`OP_REFINED_K7` is the closest same-family challenger",
        "context only — not OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
    ],
    "PAPER_TRADE_NOW.md": [
        "CD_CORE_K8 as the primary OP/CD paper-basket companion",
        "not a Phase 8 shadow-lane promotion",
        "OP_REFINED_K7 as the closest shadow-lane challenger",
    ],
    "PAPER_TRADE_NOW.txt": [
        "CD_CORE_K8 as the primary OP/CD paper-basket companion",
        "not a Phase 8 shadow-lane promotion",
        "OP_REFINED_K7 as the closest shadow-lane challenger",
        "not extra train-only validation",
    ],
    "PAPER_TRADE_USAGE.md": [
        "`CD_CORE_K8` remains the primary OP/CD paper-basket companion",
        "not a Phase 8 shadow-lane promotion",
        "the separate Phase 8 shadow/watch routine",
    ],
    "CURRENT_EVIDENCE_SUMMARY.md": [
        "`OP_DURABLE_K7` remains the safest current OP anchor",
        "`CD_CORE_K8` remains the primary OP/CD paper-basket companion",
        "`OP_REFINED_K7` remains shadow/watch only",
        "Current settled paper context is CD-only, so it should not be counted as OP-anchor forward evidence",
        "new forward-performance evidence, live-profitability evidence, promotion-readiness evidence, or real-money evidence",
    ],
    "DAILY_ARTIFACT_GUIDE.md": [
        "run `python3 validate_current_hierarchy_language.py` when the question is specifically the live hierarchy wording",
        "`live_hierarchy`, `primary_companion`, or legacy `primary_shadow` keys",
        "not ROI, promotion, live-profitability, or real-money evidence",
        "the direct current-hierarchy validator stays discoverable",
    ],
    "LIVE_SCANNER_USAGE.md": [
        "phase7_current_paper_rules.json",
        "`CD_CORE_K8` is the primary OP/CD paper-basket companion",
        "`OP_REFINED_K7` remains in the Phase 8 shadow/watch lane",
        "not settled ROI, live profitability, promotion readiness, or real-money evidence",
    ],
    "OPS_HISTORY.md": [
        "`OP_DURABLE_K7` remains the anchor and `CD_CORE_K8` remains the primary OP/CD paper-basket companion",
        "not a Phase 8 shadow-lane promotion",
        "`OP_REFINED_K7` remains the lead same-family challenger",
        "lane streaks or hit-found days alone do not promote OP_REFINED_K7 or any other Phase 8 pocket",
        "BAQ remains not treated as BEL",
        "not settled ROI, live profitability, promotion readiness, or real-money evidence",
    ],
    "out/paper_trade_settlement_audit.md": [
        "`OP_DURABLE_K7` remains the safest OP anchor",
        "`CD_CORE_K8` remains the paper companion",
        "`OP_REFINED_K7` remains shadow/watch only",
        "lane totals alone do not promote OP_REFINED_K7 or any other Phase 8 pocket",
        "`BAQ` is not `BEL`",
        "not live-profitability, promotion, anchor-change, or real-money evidence",
    ],
    "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md": [
        "`OP_DURABLE_K7` remains the safest current OP anchor",
        "`CD_CORE_K8` remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion",
        "`OP_REFINED_K7` remains the closest same-family shadow/watch challenger",
        "Source: `forward_evidence_scorecard.json` `decision_gate_minimums`",
        "Real-money prerequisites: positive paper ROI; concentration checks; payout-distribution sanity checks; no BAQ-as-BEL substitution",
        "BAQ is not BEL",
        "not settled ROI, live-profitability evidence, promotion readiness, anchor-change evidence, or real-money evidence",
    ],
    "forward_evidence_scorecard.txt": [
        "Keep CD_CORE_K8 as the primary OP/CD paper-basket companion, not an anchor replacement and not a Phase 8 shadow-lane promotion",
        "not an anchor replacement and not a Phase 8 shadow-lane promotion",
        "The legacy primary_shadow key, a regenerated scorecard, or a validation pass by itself does not prove promotion readiness or live profitability",
    ],
    "compare_main_approaches.md": [
        "CD_CORE_K8` is the primary OP/CD paper-basket companion",
        "OP_REFINED_K7` remains the narrower same-family OP shadow challenger",
    ],
    "CROSS_FAMILY_DECISION.md": [
        "**Primary paper companion: `CD_CORE_K8`**",
        "**Same-family OP shadow challenger: `OP_REFINED_K7`**",
    ],
    "PORTFOLIO_DECISION_CARD.md": [
        "Phase 7 OP/CD rule-component basket",
        "Keep the Phase 8 frozen portfolio as a shadow challenger, not the default",
        "Scorecard rank-contract override: CD_CORE_K8 ranks ahead of OP_REFINED_K7",
        "raw Score cannot turn a shadow Phase 8 / OP_REFINED line into an automatic promotion cue",
    ],
    "METHOD_FAMILY_DECISION.md": [
        "Current paper-basket companion read",
        "`CD_CORE_K8` is the primary OP/CD paper-basket companion",
    ],
    "OP_ANCHOR_METHOD_COMPARISON.md": [
        "`CD_CORE_K8` is the primary OP/CD paper-basket companion",
        "Current paper-companion read",
    ],
    "AB_DOWNSTREAM_COMPARISON.md": [
        "`CD_CORE_K8` is the primary OP/CD paper-basket companion",
        "same-family OP shadow challenger",
    ],
    "compare_recommender_scope_paths.md": [
        "`CD_CORE_K8` remains the primary OP/CD paper-basket companion",
        "research-only counterfactual",
    ],
    "COLE_FULL_REPORT_2026-04-15.md": [
        "`CD_CORE_K8` is the primary OP/CD paper-basket companion",
        "same-family shadow challenger",
    ],
    "COLE_PRESENTATION_OUTLINE.md": [
        "Current paper-companion read",
        "`CD_CORE_K8` is the primary OP/CD paper-basket companion",
    ],
}

JSON_HIERARCHY_PATHS = {
    "PAPER_TRADE_NOW.json": ["live_hierarchy"],
    "compare_main_approaches.json": ["method_family_roles", "selective_rule_path"],
    "op_anchor_method_comparison.json": ["current_read"],
    "ab_downstream_comparison_results.json": ["selective_shadow_read"],
    "compare_recommender_scope_paths.json": ["guardrail"],
}

RULE_NOTE_PATHS = [
    "op_anchor_rules.json",
    "phase7_current_paper_rules.json",
]

EVIDENCE_BOUNDARY = {
    "artifact_role": "current hierarchy wording / structured-key compatibility validator",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "source_scope": "high-traffic current human-facing surfaces, latest daily summary, ops-history recap, current-evidence bridge markdown/JSON hierarchy/source/gate read, settlement-audit markdown/JSON current read, source-chain matrix markdown/JSON current hierarchy boundary, daily/operator navigation guides, plus selected JSON/CSV hierarchy fields",
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_anchor_change_evidence": True,
    "not_companion_change_evidence": True,
    "non_goals": [
        "do not promote OP_REFINED_K7 or Phase 8 from wording-cleanliness checks",
        "do not demote OP_DURABLE_K7 from stale-language absence alone",
        "do not treat primary_shadow compatibility keys as live-profitability or promotion evidence",
        "do not use this validator as BAQ/BEL substitution evidence",
    ],
    "posture_read": {
        "anchor": "OP_DURABLE_K7",
        "primary_paper_basket_companion": "CD_CORE_K8",
        "same_family_shadow_watch": "OP_REFINED_K7",
    },
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "pass", "detail": detail}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate current live-hierarchy wording")
    parser.add_argument("--current-evidence-json", type=Path, default=CURRENT_EVIDENCE_JSON)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def load_current_evidence_payload(current_evidence_json: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    payload = json.loads(Path(current_evidence_json).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError("current_evidence_summary.json must contain a JSON object")
    contract = payload.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise AssertionError("current_evidence_summary.json must publish rebuild_validation_contract as an object")
    upstream_refresh_order = contract.get("upstream_refresh_order")
    if not isinstance(upstream_refresh_order, list) or len(upstream_refresh_order) != len(EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER):
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract must publish the three-step upstream_refresh_order")

    commands: list[str] = []
    for expected_order, row in enumerate(upstream_refresh_order, start=1):
        if not isinstance(row, dict):
            raise AssertionError("current_evidence_summary.json rebuild_validation_contract upstream_refresh_order rows must be objects")
        if row.get("order") != expected_order:
            raise AssertionError("current_evidence_summary.json rebuild_validation_contract upstream_refresh_order order drifted")
        command = row.get("command")
        if not isinstance(command, str):
            raise AssertionError("current_evidence_summary.json rebuild_validation_contract upstream_refresh_order commands must be strings")
        commands.append(command)

    if commands != EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract upstream order drifted")
    required_values = {
        "prerequisite_rebuild_command": EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER[0],
        "rebuild_command": EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER[1],
        "direct_validation_command": EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER[2],
    }
    for key, expected_value in required_values.items():
        if contract.get(key) != expected_value:
            raise AssertionError(f"current_evidence_summary.json rebuild_validation_contract.{key} drifted")

    required_true_flags = [
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
        "requires_source_consistency_before_quoting_current_totals",
        "requires_source_freshness_before_right_now_instruction_use",
        "green_checks_are_reproducibility_metadata_only",
        "upstream_refresh_order_is_provenance_metadata_only",
        "not_settled_roi_or_real_money_evidence",
    ]
    for flag in required_true_flags:
        if contract.get(flag) is not True:
            raise AssertionError(f"current_evidence_summary.json rebuild_validation_contract must mark {flag}=true")
    return payload


def current_bridge_cli_contract_checks(current_evidence_json: Path = CURRENT_EVIDENCE_JSON) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="current_hierarchy_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "current_hierarchy_validation"
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
        checks.append(require(
            proc.returncode != 0
            and not missing_contract_out_dir.exists()
            and "current_evidence_summary.json must publish rebuild_validation_contract as an object" in proc.stderr,
            "current_evidence_missing_rebuild_contract_fails_before_artifacts",
            "validate_current_hierarchy_language.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial hierarchy-validation artifacts",
        ))

        weakened_contract_out_dir = tmp_root / "weakened" / "current_hierarchy_validation"
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
        checks.append(require(
            proc.returncode != 0
            and not weakened_contract_out_dir.exists()
            and "current_evidence_summary.json rebuild_validation_contract must mark upstream_refresh_order_is_provenance_metadata_only=true" in proc.stderr,
            "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
            "validate_current_hierarchy_language.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial hierarchy-validation artifacts",
        ))

    return checks


def read_text(relative_path: str) -> str:
    return (BASE / relative_path).read_text(encoding="utf-8")


def latest_daily_summary_surface() -> str | None:
    try:
        payload = json.loads((BASE / "PAPER_TRADE_NOW.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    candidate = payload.get("daily_summary")
    if not isinstance(candidate, str) or not candidate.strip():
        return None
    path = (BASE / candidate).resolve()
    try:
        relative = path.relative_to(BASE)
    except ValueError:
        return None
    if path.exists() and path.is_file():
        return str(relative)
    return None


def current_human_surfaces() -> list[str]:
    surfaces = list(CURRENT_HUMAN_SURFACES)
    latest_daily_summary = latest_daily_summary_surface()
    if latest_daily_summary and latest_daily_summary not in surfaces:
        surfaces.append(latest_daily_summary)
    return surfaces


def required_surface_phrases() -> dict[str, list[str]]:
    phrases = {
        surface: list(surface_phrases)
        for surface, surface_phrases in REQUIRED_SURFACE_PHRASES.items()
    }
    latest_daily_summary = latest_daily_summary_surface()
    if latest_daily_summary:
        phrases[latest_daily_summary] = [
            "Current live hierarchy:",
            "`OP_DURABLE_K7` remains the anchor",
            "`CD_CORE_K8` remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion",
            "`OP_REFINED_K7` remains the lead same-family challenger",
            "lane totals alone do not promote OP_REFINED_K7 or any other Phase 8 pocket",
            "BAQ (not treated as BEL)",
        ]
    return phrases


def phrase_hits(relative_path: str, phrase: str) -> list[str]:
    hits: list[str] = []
    for idx, line in enumerate(read_text(relative_path).splitlines(), start=1):
        if phrase in line:
            hits.append(f"{relative_path}:{idx}: {line.strip()}")
    return hits


def nested_get(payload: dict[str, Any], path: list[str]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name
    current_evidence_payload = load_current_evidence_payload(Path(args.current_evidence_json))
    checks: list[dict[str, Any]] = []
    checks.extend(current_bridge_cli_contract_checks(Path(args.current_evidence_json)))
    current_surfaces = current_human_surfaces()
    latest_daily_summary = latest_daily_summary_surface()

    missing_surface_files = [path for path in current_surfaces if not (BASE / path).exists()]
    checks.append(require(
        not missing_surface_files,
        "current_surface_files_exist",
        "all high-traffic current hierarchy surfaces, including the latest daily summary when available, exist before scanning for stale wording",
    ))

    banned_hits: list[str] = []
    for surface in current_surfaces:
        for phrase in BANNED_CURRENT_PHRASES:
            banned_hits.extend(phrase_hits(surface, phrase))
    checks.append(require(
        not banned_hits,
        "no_stale_non_anchor_shadow_wording_in_current_surfaces",
        "current human-facing surfaces no longer use overloaded strongest/non-anchor/primary-shadow wording for CD_CORE_K8; historical logs and progress notes are intentionally outside this scan",
    ))

    missing_required: list[str] = []
    for surface, phrases in required_surface_phrases().items():
        text = read_text(surface)
        for phrase in phrases:
            if phrase not in text:
                missing_required.append(f"{surface}: missing {phrase!r}")
    checks.append(require(
        not missing_required,
        "primary_paper_basket_companion_wording_present",
        "current report/runbook/comparison surfaces explicitly name CD_CORE_K8 as the primary OP/CD paper-basket companion and OP_REFINED_K7 as the separate same-family shadow/watch challenger",
    ))

    json_role_reads: dict[str, dict[str, Any]] = {}
    bad_json_roles: list[str] = []
    for relative_path, json_path in JSON_HIERARCHY_PATHS.items():
        payload = json.loads((BASE / relative_path).read_text(encoding="utf-8"))
        role_block = nested_get(payload, json_path)
        json_role_reads[relative_path] = role_block if isinstance(role_block, dict) else {"_invalid": role_block}
        if not isinstance(role_block, dict):
            bad_json_roles.append(f"{relative_path}: path {'/'.join(json_path)} is not an object")
            continue
        if role_block.get("primary_shadow") == "CD_CORE_K8" and role_block.get("primary_companion") != "CD_CORE_K8":
            bad_json_roles.append(f"{relative_path}: legacy primary_shadow exists without matching primary_companion")
        if role_block.get("secondary_shadow") != "OP_REFINED_K7":
            bad_json_roles.append(f"{relative_path}: secondary_shadow is not OP_REFINED_K7")
    checks.append(require(
        not bad_json_roles,
        "json_legacy_primary_shadow_has_primary_companion",
        "machine-readable surfaces may keep legacy primary_shadow compatibility, but every CD_CORE_K8 instance also carries primary_companion=CD_CORE_K8 and OP_REFINED_K7 as the secondary shadow",
    ))

    top_card = json_role_reads["PAPER_TRADE_NOW.json"]
    checks.append(require(
        top_card.get("current_anchor") == "OP_DURABLE_K7"
        and top_card.get("primary_companion") == "CD_CORE_K8"
        and top_card.get("primary_shadow") == "CD_CORE_K8"
        and "primary OP/CD paper-basket" in str(top_card.get("primary_companion_note", ""))
        and "not the Phase 8 shadow/watch lane" in str(top_card.get("primary_companion_note", ""))
        and top_card.get("secondary_shadow") == "OP_REFINED_K7",
        "top_card_hierarchy_contract",
        "PAPER_TRADE_NOW.json preserves the live hierarchy contract: OP_DURABLE_K7 anchor, CD_CORE_K8 paper-basket companion with legacy primary_shadow compatibility, OP_REFINED_K7 shadow/watch challenger",
    ))

    current_evidence_rebuild_contract = (
        current_evidence_payload.get("rebuild_validation_contract")
        if isinstance(current_evidence_payload.get("rebuild_validation_contract"), dict)
        else {}
    )
    current_evidence_rebuild_order_rows = (
        current_evidence_rebuild_contract.get("upstream_refresh_order")
        if isinstance(current_evidence_rebuild_contract.get("upstream_refresh_order"), list)
        else []
    )
    current_evidence_rebuild_order_commands = [
        str(row.get("command") or "")
        for row in sorted(
            (row for row in current_evidence_rebuild_order_rows if isinstance(row, dict)),
            key=lambda row: int(row.get("order", 0)),
        )
    ]
    current_evidence_frozen = (
        current_evidence_payload.get("frozen_posture")
        if isinstance(current_evidence_payload.get("frozen_posture"), dict)
        else {}
    )
    current_evidence_anchor = current_evidence_frozen.get("anchor") if isinstance(current_evidence_frozen.get("anchor"), dict) else {}
    current_evidence_companion = (
        current_evidence_frozen.get("primary_companion")
        if isinstance(current_evidence_frozen.get("primary_companion"), dict)
        else {}
    )
    current_evidence_shadow = current_evidence_frozen.get("shadow_lead") if isinstance(current_evidence_frozen.get("shadow_lead"), dict) else {}
    current_evidence_summary = (
        current_evidence_payload.get("summary")
        if isinstance(current_evidence_payload.get("summary"), dict)
        else {}
    )
    current_evidence_boundary = (
        current_evidence_payload.get("evidence_boundary")
        if isinstance(current_evidence_payload.get("evidence_boundary"), dict)
        else {}
    )
    current_evidence_source_freshness = (
        current_evidence_payload.get("source_freshness")
        if isinstance(current_evidence_payload.get("source_freshness"), dict)
        else {}
    )
    current_evidence_refresh_boundary = (
        current_evidence_source_freshness.get("refresh_action_boundary")
        if isinstance(current_evidence_source_freshness.get("refresh_action_boundary"), dict)
        else {}
    )
    current_evidence_source_consistency = (
        current_evidence_payload.get("source_consistency")
        if isinstance(current_evidence_payload.get("source_consistency"), dict)
        else {}
    )
    current_evidence_primary_rows = (
        current_evidence_source_consistency.get("primary_roi_complete_settled_rows")
        if isinstance(current_evidence_source_consistency.get("primary_roi_complete_settled_rows"), dict)
        else {}
    )
    current_evidence_open_rows = (
        current_evidence_source_consistency.get("primary_open_settlement_rows")
        if isinstance(current_evidence_source_consistency.get("primary_open_settlement_rows"), dict)
        else {}
    )
    current_evidence_incomplete_rows = (
        current_evidence_source_consistency.get("primary_incomplete_settlement_rows")
        if isinstance(current_evidence_source_consistency.get("primary_incomplete_settlement_rows"), dict)
        else {}
    )
    current_evidence_roi_gap_rows = (
        current_evidence_source_consistency.get("primary_roi_gap_settlement_rows")
        if isinstance(current_evidence_source_consistency.get("primary_roi_gap_settlement_rows"), dict)
        else {}
    )
    current_evidence_cost_return = (
        current_evidence_source_consistency.get("primary_cost_return_sums")
        if isinstance(current_evidence_source_consistency.get("primary_cost_return_sums"), dict)
        else {}
    )
    current_evidence_settled_ts_gap = (
        current_evidence_source_consistency.get("primary_settled_ts_gap_rows")
        if isinstance(current_evidence_source_consistency.get("primary_settled_ts_gap_rows"), dict)
        else {}
    )
    current_evidence_gates = (
        current_evidence_payload.get("decision_gate_minimums")
        if isinstance(current_evidence_payload.get("decision_gate_minimums"), dict)
        else {}
    )
    current_evidence_gate_top_card_values = (
        current_evidence_gates.get("top_card_values")
        if isinstance(current_evidence_gates.get("top_card_values"), dict)
        else {}
    )
    current_evidence_gate_scorecard_values = (
        current_evidence_gates.get("scorecard_values")
        if isinstance(current_evidence_gates.get("scorecard_values"), dict)
        else {}
    )
    current_evidence_gate_effective_values = (
        current_evidence_gates.get("effective_values")
        if isinstance(current_evidence_gates.get("effective_values"), dict)
        else {}
    )
    current_evidence_gate_threshold_sources = (
        current_evidence_gates.get("threshold_sources")
        if isinstance(current_evidence_gates.get("threshold_sources"), dict)
        else {}
    )
    current_evidence_current_paper = (
        current_evidence_payload.get("current_paper_status")
        if isinstance(current_evidence_payload.get("current_paper_status"), dict)
        else {}
    )
    current_evidence_primary_status = (
        current_evidence_current_paper.get("primary")
        if isinstance(current_evidence_current_paper.get("primary"), dict)
        else {}
    )
    current_evidence_anchor_gap = (
        current_evidence_primary_status.get("anchor_settlement_gap")
        if isinstance(current_evidence_primary_status.get("anchor_settlement_gap"), dict)
        else {}
    )
    current_evidence_open_queue = (
        current_evidence_primary_status.get("open_settlement_queue_by_rule")
        if isinstance(current_evidence_primary_status.get("open_settlement_queue_by_rule"), dict)
        else {}
    )
    current_evidence_best_action = (
        current_evidence_current_paper.get("best_action")
        if isinstance(current_evidence_current_paper.get("best_action"), dict)
        else {}
    )
    current_evidence_current_read = str(current_evidence_summary.get("current_read") or "")
    current_evidence_requires_refresh = bool(
        current_evidence_source_freshness.get("requires_refresh_before_right_now_use")
    )
    current_evidence_best_action_command = str(current_evidence_best_action.get("command") or "")
    current_evidence_refresh_route_safe = (
        not current_evidence_requires_refresh
        or "run_daily_portfolio_observation.sh" in current_evidence_best_action_command
    )
    current_evidence_expected_open_queue_cd_only = (
        current_evidence_open_queue.get("total_open_rows", 0) > 0
        and current_evidence_open_queue.get("anchor_open_rows") == 0
        and current_evidence_open_queue.get("companion_open_rows")
        == current_evidence_open_queue.get("total_open_rows")
    )
    current_evidence_json_read = {
        "anchor": current_evidence_anchor.get("rule_id"),
        "anchor_tier": current_evidence_anchor.get("tier"),
        "primary_companion": current_evidence_companion.get("rule_id"),
        "primary_companion_tier": current_evidence_companion.get("tier"),
        "primary_companion_read": current_evidence_companion.get("read"),
        "same_family_shadow_watch": current_evidence_shadow.get("rule_id"),
        "same_family_shadow_watch_tier": current_evidence_shadow.get("tier"),
        "anchor_gap_anchor_rule_id": current_evidence_anchor_gap.get("anchor_rule_id"),
        "anchor_gap_companion_rule_id": current_evidence_anchor_gap.get("companion_rule_id"),
        "anchor_gap_anchor_rows": current_evidence_anchor_gap.get("anchor_roi_complete_settled_rows"),
        "anchor_gap_companion_rows": current_evidence_anchor_gap.get("companion_roi_complete_settled_rows"),
        "anchor_gap_floor": current_evidence_anchor_gap.get("same_candidate_anchor_review_floor"),
        "anchor_gap_rows_needed": current_evidence_anchor_gap.get("anchor_rows_needed_for_same_candidate_review"),
        "anchor_gap_current_sample_is_cd_only": current_evidence_anchor_gap.get("current_sample_is_cd_only"),
        "anchor_gap_companion_rows_count_as_anchor_evidence": current_evidence_anchor_gap.get("companion_rows_count_as_anchor_evidence"),
        "anchor_gap_not_forward_performance_evidence": current_evidence_anchor_gap.get("not_forward_performance_evidence"),
        "open_queue_anchor_rule_id": current_evidence_open_queue.get("anchor_rule_id"),
        "open_queue_companion_rule_id": current_evidence_open_queue.get("companion_rule_id"),
        "open_queue_total_open_rows": current_evidence_open_queue.get("total_open_rows"),
        "open_queue_anchor_open_rows": current_evidence_open_queue.get("anchor_open_rows"),
        "open_queue_companion_open_rows": current_evidence_open_queue.get("companion_open_rows"),
        "open_queue_current_open_queue_is_cd_only": current_evidence_open_queue.get("current_open_queue_is_cd_only"),
        "open_queue_open_rows_count_as_roi_complete": current_evidence_open_queue.get("open_rows_count_as_roi_complete"),
        "open_queue_open_rows_count_as_anchor_evidence": current_evidence_open_queue.get("open_rows_count_as_anchor_evidence"),
        "open_queue_not_forward_performance_evidence": current_evidence_open_queue.get("not_forward_performance_evidence"),
        "not_new_forward_evidence": current_evidence_boundary.get("not_new_forward_evidence"),
        "not_live_profitability_evidence": current_evidence_boundary.get("not_live_profitability_evidence"),
        "not_promotion_readiness_evidence": current_evidence_boundary.get("not_promotion_readiness_evidence"),
        "not_real_money_evidence": current_evidence_boundary.get("not_real_money_evidence"),
        "source_consistency_overall_match": current_evidence_source_consistency.get("overall_match"),
        "primary_roi_complete_rows_match": (
            current_evidence_primary_rows.get("paper_trade_now")
            == current_evidence_primary_rows.get("settlement_audit")
            == current_evidence_primary_rows.get("settlement_csv_recomputed")
        ),
        "primary_open_rows_match": (
            current_evidence_open_rows.get("paper_trade_now")
            == current_evidence_open_rows.get("settlement_audit")
        ),
        "primary_incomplete_rows_match": (
            current_evidence_incomplete_rows.get("paper_trade_now")
            == current_evidence_incomplete_rows.get("settlement_audit")
            == 0
        ),
        "primary_roi_gap_rows_match": (
            current_evidence_roi_gap_rows.get("paper_trade_now")
            == current_evidence_roi_gap_rows.get("settlement_audit")
            == 0
        ),
        "primary_cost_return_sums_match": (
            current_evidence_cost_return.get("settlement_audit_cost")
            == current_evidence_cost_return.get("settlement_csv_cost")
            and current_evidence_cost_return.get("settlement_audit_return")
            == current_evidence_cost_return.get("settlement_csv_return")
        ),
        "primary_settled_ts_gap_rows_clear": (
            current_evidence_settled_ts_gap.get("settlement_audit") == 0
            and current_evidence_settled_ts_gap.get("settlement_csv_recomputed") == 0
        ),
        "source_freshness_state": current_evidence_source_freshness.get("right_now_freshness_state"),
        "source_freshness_state_valid": current_evidence_source_freshness.get("right_now_freshness_state_valid"),
        "source_stale_vs_generated_date": current_evidence_source_freshness.get("is_stale_vs_generated_date"),
        "requires_refresh_before_right_now_use": current_evidence_source_freshness.get("requires_refresh_before_right_now_use"),
        "requires_refresh_reason": current_evidence_source_freshness.get("requires_refresh_reason"),
        "refresh_age_days": current_evidence_source_freshness.get("refresh_age_days"),
        "refresh_boundary_command": current_evidence_refresh_boundary.get("command"),
        "refresh_boundary_required_before_right_now_instruction_use": current_evidence_refresh_boundary.get(
            "required_before_right_now_instruction_use"
        ),
        "refresh_boundary_source_action_counts_as_current_instruction_before_refresh": current_evidence_refresh_boundary.get(
            "source_action_counts_as_current_instruction_before_refresh"
        ),
        "refresh_boundary_can_update_operator_surfaces": current_evidence_refresh_boundary.get(
            "wrapper_refresh_can_update_operator_surfaces"
        ),
        "refresh_boundary_can_settle_open_rows_by_itself": current_evidence_refresh_boundary.get(
            "wrapper_refresh_can_settle_open_rows_by_itself"
        ),
        "refresh_boundary_counts_as_roi_complete_evidence_by_itself": current_evidence_refresh_boundary.get(
            "wrapper_refresh_counts_as_roi_complete_evidence_by_itself"
        ),
        "refresh_boundary_clean_empty_counts_as_forward_performance": current_evidence_refresh_boundary.get(
            "clean_empty_refresh_counts_as_forward_performance"
        ),
        "refresh_boundary_missing_or_invalid_artifact_counts_as_clean_quiet_day": current_evidence_refresh_boundary.get(
            "missing_or_invalid_artifact_counts_as_clean_quiet_day"
        ),
        "refresh_boundary_not_forward_performance_evidence": current_evidence_refresh_boundary.get(
            "not_forward_performance_evidence"
        ),
        "refresh_boundary_not_real_money_evidence": current_evidence_refresh_boundary.get("not_real_money_evidence"),
        "best_action_command": current_evidence_best_action_command,
        "refresh_route_safe": current_evidence_refresh_route_safe,
        "decision_gate_source": current_evidence_gates.get("source_path"),
        "decision_gate_source_loaded": current_evidence_gates.get("source_loaded"),
        "anchor_displacement_min": current_evidence_gates.get("anchor_displacement_min_roi_complete_settled_observations"),
        "phase8_promotion_review_min": current_evidence_gates.get("phase8_promotion_review_min_roi_complete_settled_observations"),
        "real_money_discussion_min": current_evidence_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi"),
        "decision_gate_scorecard_source": current_evidence_gates.get("scorecard_source_path"),
        "decision_gate_source_values_match_scorecard": current_evidence_gates.get("source_values_match_scorecard"),
        "decision_gate_effective_values_source": current_evidence_gates.get("effective_values_source"),
        "decision_gate_missing_top_card_fields": current_evidence_gates.get("missing_top_card_fields"),
        "decision_gate_mismatched_fields": current_evidence_gates.get("mismatched_fields"),
        "effective_anchor_displacement_min": current_evidence_gate_effective_values.get("anchor_displacement_min_roi_complete_settled_observations"),
        "effective_phase8_promotion_review_min": current_evidence_gate_effective_values.get("phase8_promotion_review_min_roi_complete_settled_observations"),
        "effective_real_money_discussion_min": current_evidence_gate_effective_values.get("real_money_discussion_min_total_settled_observations_with_usable_roi"),
        "top_card_anchor_displacement_min": current_evidence_gate_top_card_values.get("anchor_displacement_min_roi_complete_settled_observations"),
        "top_card_phase8_promotion_review_min": current_evidence_gate_top_card_values.get("phase8_promotion_review_min_roi_complete_settled_observations"),
        "top_card_real_money_discussion_min": current_evidence_gate_top_card_values.get("real_money_discussion_min_total_settled_observations_with_usable_roi"),
        "scorecard_anchor_displacement_min": current_evidence_gate_scorecard_values.get("anchor_displacement_min_roi_complete_settled_observations"),
        "scorecard_phase8_promotion_review_min": current_evidence_gate_scorecard_values.get("phase8_promotion_review_min_roi_complete_settled_observations"),
        "scorecard_real_money_discussion_min": current_evidence_gate_scorecard_values.get("real_money_discussion_min_total_settled_observations_with_usable_roi"),
        "decision_gate_anchor_threshold_source": current_evidence_gate_threshold_sources.get("anchor_displacement"),
        "decision_gate_phase8_threshold_source": current_evidence_gate_threshold_sources.get("phase8_promotion_review"),
        "decision_gate_real_money_threshold_source": current_evidence_gate_threshold_sources.get("real_money_discussion"),
        "rebuild_contract_source": "current_evidence_summary.json:rebuild_validation_contract",
        "rebuild_upstream_refresh_order": current_evidence_rebuild_order_commands,
        "rebuild_prerequisite_command": current_evidence_rebuild_contract.get("prerequisite_rebuild_command"),
        "rebuild_command": current_evidence_rebuild_contract.get("rebuild_command"),
        "rebuild_direct_validation_command": current_evidence_rebuild_contract.get("direct_validation_command"),
        "rebuild_requires_settlement_audit_refresh": current_evidence_rebuild_contract.get(
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
        ),
        "rebuild_requires_source_consistency": current_evidence_rebuild_contract.get(
            "requires_source_consistency_before_quoting_current_totals"
        ),
        "rebuild_requires_source_freshness_before_right_now_instruction_use": current_evidence_rebuild_contract.get(
            "requires_source_freshness_before_right_now_instruction_use"
        ),
        "rebuild_green_checks_metadata_only": current_evidence_rebuild_contract.get(
            "green_checks_are_reproducibility_metadata_only"
        ),
        "rebuild_order_provenance_metadata_only": current_evidence_rebuild_contract.get(
            "upstream_refresh_order_is_provenance_metadata_only"
        ),
        "rebuild_not_settled_roi_or_real_money_evidence": current_evidence_rebuild_contract.get(
            "not_settled_roi_or_real_money_evidence"
        ),
    }
    checks.append(require(
        current_evidence_anchor.get("rule_id") == "OP_DURABLE_K7"
        and current_evidence_anchor.get("tier") == "ANCHOR"
        and current_evidence_companion.get("rule_id") == "CD_CORE_K8"
        and current_evidence_companion.get("tier") == "PAPER"
        and "primary OP/CD paper-basket companion" in str(current_evidence_companion.get("read") or "")
        and current_evidence_shadow.get("rule_id") == "OP_REFINED_K7"
        and current_evidence_shadow.get("tier") == "WATCH"
        and "Current settled paper context is CD-only" in current_evidence_current_read
        and "not be counted as OP-anchor forward evidence" in current_evidence_current_read
        and current_evidence_anchor_gap.get("anchor_rule_id") == "OP_DURABLE_K7"
        and current_evidence_anchor_gap.get("companion_rule_id") == "CD_CORE_K8"
        and current_evidence_anchor_gap.get("anchor_roi_complete_settled_rows") == 0
        and current_evidence_anchor_gap.get("companion_roi_complete_settled_rows") == current_evidence_primary_rows.get("paper_trade_now")
        and current_evidence_anchor_gap.get("same_candidate_anchor_review_floor") == 30
        and current_evidence_anchor_gap.get("anchor_rows_needed_for_same_candidate_review") == 30
        and current_evidence_anchor_gap.get("current_sample_is_cd_only") is True
        and current_evidence_anchor_gap.get("companion_rows_count_as_anchor_evidence") is False
        and current_evidence_anchor_gap.get("not_forward_performance_evidence") is True
        and "CD companion rows do not reduce that OP-anchor gap" in str(current_evidence_anchor_gap.get("read") or "")
        and "OP-anchor settlement gap" in current_evidence_current_read
        and current_evidence_open_queue.get("anchor_rule_id") == "OP_DURABLE_K7"
        and current_evidence_open_queue.get("companion_rule_id") == "CD_CORE_K8"
        and current_evidence_open_queue.get("total_open_rows") == current_evidence_open_rows.get("paper_trade_now")
        and current_evidence_open_queue.get("anchor_open_rows") == 0
        and current_evidence_open_queue.get("companion_open_rows") == current_evidence_open_rows.get("paper_trade_now")
        and current_evidence_open_queue.get("open_settlement_queue_state")
        == ("closed" if current_evidence_open_rows.get("paper_trade_now") == 0 else "open")
        and (
            current_evidence_open_queue.get("open_settlement_context") == "no open primary settlement rows"
            if current_evidence_open_rows.get("paper_trade_now") == 0
            else bool(str(current_evidence_open_queue.get("open_settlement_context") or "").strip())
        )
        and current_evidence_open_queue.get("current_open_queue_is_cd_only") == current_evidence_expected_open_queue_cd_only
        and current_evidence_open_queue.get("open_rows_count_as_roi_complete") is False
        and current_evidence_open_queue.get("open_rows_count_as_anchor_evidence") is False
        and current_evidence_open_queue.get("not_forward_performance_evidence") is True
        and "Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence" in str(current_evidence_open_queue.get("read") or "")
        and "Settlement queue state" in current_evidence_current_read
        and "Open settlement queue by rule" in current_evidence_current_read
        and "Phase 8 remains shadow-only" in current_evidence_current_read
        and "lane totals alone do not promote OP_REFINED_K7" in current_evidence_current_read
        and "BAQ is not BEL" in current_evidence_current_read
        and current_evidence_boundary.get("not_new_forward_evidence") is True
        and current_evidence_boundary.get("not_live_profitability_evidence") is True
        and current_evidence_boundary.get("not_promotion_readiness_evidence") is True
        and current_evidence_boundary.get("not_real_money_evidence") is True,
        "current_evidence_json_preserves_hierarchy_boundary",
        "current_evidence_summary.json keeps OP_DURABLE_K7 as ANCHOR, CD_CORE_K8 as PAPER primary companion, OP_REFINED_K7 as WATCH, the CD-only/not-OP-anchor current-read boundary, the settlement-queue state/by-rule context as workflow-only, the Phase 8 shadow-only boundary, the BAQ-not-BEL boundary, and the no-new-evidence flags",
    ))
    checks.append(require(
        current_evidence_source_consistency.get("overall_match") is True
        and current_evidence_primary_rows.get("paper_trade_now")
        == current_evidence_primary_rows.get("settlement_audit")
        == current_evidence_primary_rows.get("settlement_csv_recomputed")
        and current_evidence_open_rows.get("paper_trade_now") == current_evidence_open_rows.get("settlement_audit")
        and current_evidence_incomplete_rows.get("paper_trade_now") == current_evidence_incomplete_rows.get("settlement_audit") == 0
        and current_evidence_roi_gap_rows.get("paper_trade_now") == current_evidence_roi_gap_rows.get("settlement_audit") == 0
        and current_evidence_cost_return.get("settlement_audit_cost") == current_evidence_cost_return.get("settlement_csv_cost")
        and current_evidence_cost_return.get("settlement_audit_return") == current_evidence_cost_return.get("settlement_csv_return")
        and current_evidence_settled_ts_gap.get("settlement_audit") == 0
        and current_evidence_settled_ts_gap.get("settlement_csv_recomputed") == 0
        and current_evidence_source_freshness.get("right_now_freshness_state_valid") is True
        and isinstance(current_evidence_source_freshness.get("is_stale_vs_generated_date"), bool)
        and isinstance(current_evidence_source_freshness.get("requires_refresh_before_right_now_use"), bool)
        and isinstance(current_evidence_source_freshness.get("refresh_age_days"), int)
        and current_evidence_refresh_boundary.get("command") == "./run_daily_portfolio_observation.sh"
        and current_evidence_refresh_boundary.get("required_before_right_now_instruction_use") is current_evidence_requires_refresh
        and current_evidence_refresh_boundary.get("source_action_counts_as_current_instruction_before_refresh") is (not current_evidence_requires_refresh)
        and current_evidence_refresh_boundary.get("wrapper_refresh_can_update_operator_surfaces") is True
        and current_evidence_refresh_boundary.get("wrapper_refresh_can_settle_open_rows_by_itself") is False
        and current_evidence_refresh_boundary.get("wrapper_refresh_counts_as_roi_complete_evidence_by_itself") is False
        and current_evidence_refresh_boundary.get("clean_empty_refresh_counts_as_forward_performance") is False
        and current_evidence_refresh_boundary.get("missing_or_invalid_artifact_counts_as_clean_quiet_day") is False
        and current_evidence_refresh_boundary.get("not_forward_performance_evidence") is True
        and current_evidence_refresh_boundary.get("not_real_money_evidence") is True
        and current_evidence_refresh_route_safe
        and current_evidence_gates.get("source_path") == "forward_evidence_scorecard.json"
        and current_evidence_gates.get("source_loaded") is True
        and current_evidence_gates.get("anchor_displacement_min_roi_complete_settled_observations") == 30
        and current_evidence_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
        and current_evidence_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
        and current_evidence_gates.get("scorecard_source_path") == "forward_evidence_scorecard.json"
        and current_evidence_gates.get("source_values_match_scorecard") is True
        and current_evidence_gates.get("effective_values_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
        and current_evidence_gates.get("missing_top_card_fields") == []
        and current_evidence_gates.get("mismatched_fields") == []
        and current_evidence_gate_top_card_values == current_evidence_gate_scorecard_values == current_evidence_gate_effective_values
        and current_evidence_gate_effective_values.get("anchor_displacement_min_roi_complete_settled_observations") == 30
        and current_evidence_gate_effective_values.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
        and current_evidence_gate_effective_values.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
        and current_evidence_gate_threshold_sources.get("anchor_displacement") == "forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations"
        and current_evidence_gate_threshold_sources.get("phase8_promotion_review") == "forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations"
        and current_evidence_gate_threshold_sources.get("real_money_discussion") == "forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
        "current_evidence_json_source_gate_status_is_current",
        "current_evidence_summary.json must be source-consistent across top-card/audit/settlement CSV counts, refresh-routed when stale, publish the wrapper-refresh non-evidence boundary, and tie both its flattened and canonical effective 30/20/100 decision gates to exact scorecard-sourced keys before its current paper totals are quoted",
    ))
    checks.append(require(
        current_evidence_rebuild_order_commands == EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER
        and current_evidence_rebuild_contract.get("prerequisite_rebuild_command")
        == "python3 paper_trade_settlement_audit.py"
        and current_evidence_rebuild_contract.get("rebuild_command") == "python3 current_evidence_summary.py"
        and current_evidence_rebuild_contract.get("direct_validation_command")
        == "python3 validate_current_evidence_summary.py"
        and current_evidence_rebuild_contract.get(
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
        )
        is True
        and current_evidence_rebuild_contract.get("requires_source_consistency_before_quoting_current_totals") is True
        and current_evidence_rebuild_contract.get("requires_source_freshness_before_right_now_instruction_use") is True
        and current_evidence_rebuild_contract.get("green_checks_are_reproducibility_metadata_only") is True
        and current_evidence_rebuild_contract.get("upstream_refresh_order_is_provenance_metadata_only") is True
        and current_evidence_rebuild_contract.get("not_settled_roi_or_real_money_evidence") is True,
        "current_evidence_json_publishes_rebuild_validation_contract",
        "current hierarchy validator now source-checks current_evidence_summary.json rebuild_validation_contract so hierarchy wording reads cannot become a shortcut around settlement-audit -> current-bridge -> bridge-validator ordering before current totals are quoted",
    ))

    scorecard_payload = json.loads((BASE / "forward_evidence_scorecard.json").read_text(encoding="utf-8"))
    gates = {gate.get("gate_id"): gate for gate in scorecard_payload.get("decision_change_gates", [])}
    checks.append(require(
        gates.get("primary_companion", {}).get("current_decision") == "Keep CD_CORE_K8 as the primary OP/CD paper-basket companion, not an anchor replacement and not a Phase 8 shadow-lane promotion."
        and "legacy primary_shadow key" in gates.get("primary_companion", {}).get("does_not_count", "")
        and "20+ ROI-complete settled shadow observations" in gates.get("phase8_promotion_review", {}).get("what_would_change_it", "")
        and "100+ total settled paper observations" in gates.get("real_money_discussion", {}).get("what_would_change_it", ""),
        "scorecard_decision_gates_preserve_hierarchy_boundary",
        "scorecard JSON decision gates separate CD_CORE_K8 companion changes, OP_REFINED_K7/Phase 8 promotion review, and real-money discussion behind settled-forward-evidence thresholds",
    ))

    settlement_audit_payload = json.loads((BASE / "out" / "paper_trade_settlement_audit.json").read_text(encoding="utf-8"))
    settlement_audit_summary = (
        settlement_audit_payload.get("summary")
        if isinstance(settlement_audit_payload.get("summary"), dict)
        else {}
    )
    settlement_audit_current_read = str(settlement_audit_summary.get("current_read") or "")
    settlement_audit_gates = (
        settlement_audit_payload.get("decision_gate_minimums")
        if isinstance(settlement_audit_payload.get("decision_gate_minimums"), dict)
        else {}
    )
    settlement_lanes = {
        lane.get("name"): lane
        for lane in settlement_audit_payload.get("lanes", [])
        if isinstance(lane, dict) and lane.get("name")
    }
    primary_lane = settlement_lanes.get("primary", {})
    shadow_lane = settlement_lanes.get("shadow", {})
    primary_promotion_gate = (
        primary_lane.get("promotion_gate")
        if isinstance(primary_lane.get("promotion_gate"), dict)
        else {}
    )
    shadow_promotion_gate = (
        shadow_lane.get("promotion_gate")
        if isinstance(shadow_lane.get("promotion_gate"), dict)
        else {}
    )
    settlement_audit_json_read = {
        "artifact_status": settlement_audit_payload.get("artifact_status"),
        "gate_source": settlement_audit_gates.get("source_path"),
        "gate_source_loaded": settlement_audit_gates.get("source_loaded"),
        "gate_fallback_used": settlement_audit_gates.get("fallback_used"),
        "anchor_displacement_min": settlement_audit_gates.get("anchor_displacement_min_roi_complete_settled_observations"),
        "phase8_promotion_review_min": settlement_audit_gates.get("phase8_promotion_review_min_roi_complete_settled_observations"),
        "real_money_discussion_min": settlement_audit_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi"),
        "primary_role": primary_lane.get("role"),
        "primary_assessment": primary_lane.get("assessment"),
        "primary_roi_complete_settled_rows": primary_lane.get("roi_complete_settled_rows"),
        "primary_open_settlement_rows": primary_lane.get("open_settlement_rows"),
        "primary_active_first_read_gate": primary_lane.get("active_first_read_gate"),
        "primary_active_first_read_scope": primary_lane.get("active_first_read_scope"),
        "primary_active_first_read_min_settled": primary_lane.get("active_first_read_min_settled"),
        "shadow_role": shadow_lane.get("role"),
        "shadow_assessment": shadow_lane.get("assessment"),
        "shadow_roi_complete_settled_rows": shadow_lane.get("roi_complete_settled_rows"),
        "shadow_active_first_read_gate": shadow_lane.get("active_first_read_gate"),
        "shadow_active_first_read_scope": shadow_lane.get("active_first_read_scope"),
        "shadow_active_first_read_min_settled": shadow_lane.get("active_first_read_min_settled"),
        "summary_not_new_forward_evidence": "not new forward evidence by itself" in settlement_audit_current_read,
        "summary_no_lane_total_phase8_promotion": "lane totals alone do not promote OP_REFINED_K7" in settlement_audit_current_read,
        "summary_baq_not_bel": "BAQ is not BEL" in settlement_audit_current_read,
    }
    checks.append(require(
        settlement_audit_payload.get("artifact_status") == "pass"
        and settlement_audit_gates.get("source_path") == "forward_evidence_scorecard.json"
        and settlement_audit_gates.get("source_loaded") is True
        and settlement_audit_gates.get("fallback_used") is False
        and settlement_audit_gates.get("anchor_displacement_min_roi_complete_settled_observations") == 30
        and settlement_audit_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
        and settlement_audit_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
        and "settlement-audit sample milestones are source-matched to forward_evidence_scorecard.json decision_gate_minimums" in str(settlement_audit_gates.get("alignment_read") or "")
        and "OP_DURABLE_K7" in str(primary_lane.get("role") or "")
        and "CD_CORE_K8" in str(primary_lane.get("role") or "")
        and primary_lane.get("active_first_read_gate") == "anchor_displacement"
        and primary_lane.get("active_first_read_scope") == "lane_total_first_read"
        and primary_lane.get("active_first_read_min_settled") == 30
        and primary_promotion_gate.get("portfolio_review_settled_lane_total") == 100
        and {"OP_DURABLE_K7", "CD_CORE_K8"}.issubset(set(primary_promotion_gate.get("expected_rule_ids", [])))
        and "OP_REFINED_K7" in str(shadow_lane.get("role") or "")
        and shadow_lane.get("active_first_read_gate") == "phase8_promotion_review"
        and shadow_lane.get("active_first_read_scope") == "per_rule_shadow_watch"
        and shadow_lane.get("active_first_read_min_settled") == 20
        and "OP_REFINED_K7" in set(shadow_promotion_gate.get("expected_rule_ids", []))
        and {"AQU_K9", "CD_REFINED_K9"}.issubset(set(shadow_promotion_gate.get("scorecard_skip_rule_ids", [])))
        and "20-row count is a review floor, not a promotion entitlement" in str(shadow_promotion_gate.get("gate_read") or "")
        and "lane totals alone do not promote OP_REFINED_K7" in str(shadow_promotion_gate.get("gate_read") or "")
        and "ledger-completeness / ROI-coverage audit only, not new forward evidence by itself" in settlement_audit_current_read
        and "OP_DURABLE_K7 remains the safest OP anchor" in settlement_audit_current_read
        and "CD_CORE_K8 remains the paper companion" in settlement_audit_current_read
        and "OP_REFINED_K7 remains shadow/watch only" in settlement_audit_current_read
        and "BAQ is not BEL" in settlement_audit_current_read,
        "settlement_audit_json_preserves_hierarchy_boundary",
        "settlement audit JSON keeps scorecard-sourced 30/20/100 gates, the primary lane-total anchor_displacement scope, the shadow per-rule phase8_promotion_review scope, SKIP-rule caution, and the no-new-evidence OP/CD/Phase 8/BAQ boundary",
    ))

    source_chain_payload = json.loads((BASE / "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json").read_text(encoding="utf-8"))
    source_chain_hierarchy = (
        source_chain_payload.get("current_hierarchy_boundary")
        if isinstance(source_chain_payload.get("current_hierarchy_boundary"), dict)
        else {}
    )
    source_chain_gates = (
        source_chain_payload.get("decision_gate_minimums")
        if isinstance(source_chain_payload.get("decision_gate_minimums"), dict)
        else {}
    )
    source_chain_boundary_read = str(source_chain_hierarchy.get("boundary_read") or "")
    source_chain_matrix_json_read = {
        "artifact_status": source_chain_payload.get("artifact_status"),
        "anchor": source_chain_hierarchy.get("anchor"),
        "primary_paper_basket_companion": source_chain_hierarchy.get("primary_paper_basket_companion"),
        "same_family_shadow_watch": source_chain_hierarchy.get("same_family_shadow_watch"),
        "gate_source": source_chain_gates.get("source_path"),
        "gate_source_loaded": source_chain_gates.get("source_loaded"),
        "anchor_displacement_min": source_chain_gates.get("anchor_displacement_min"),
        "phase8_promotion_review_min": source_chain_gates.get("phase8_promotion_review_min"),
        "real_money_discussion_min": source_chain_gates.get("real_money_discussion_min"),
        "real_money_no_baq_as_bel_required": source_chain_gates.get("real_money_no_baq_as_bel_required"),
        "not_settled_roi_evidence": source_chain_hierarchy.get("not_settled_roi_evidence"),
        "not_live_profitability_evidence": source_chain_hierarchy.get("not_live_profitability_evidence"),
        "not_promotion_readiness_evidence": source_chain_hierarchy.get("not_promotion_readiness_evidence"),
        "not_anchor_change_evidence": source_chain_hierarchy.get("not_anchor_change_evidence"),
        "not_real_money_evidence": source_chain_hierarchy.get("not_real_money_evidence"),
        "summary_preserves_baq_not_bel": "BAQ is not BEL" in source_chain_boundary_read,
        "summary_preserves_no_phase8_promotion": "not a Phase 8 shadow-lane promotion" in source_chain_boundary_read,
    }
    checks.append(require(
        source_chain_payload.get("artifact_status") == "pass"
        and source_chain_hierarchy.get("anchor") == "OP_DURABLE_K7"
        and source_chain_hierarchy.get("primary_paper_basket_companion") == "CD_CORE_K8"
        and source_chain_hierarchy.get("same_family_shadow_watch") == "OP_REFINED_K7"
        and "CD_CORE_K8 remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion" in source_chain_boundary_read
        and "OP_REFINED_K7 remains the closest same-family shadow/watch challenger" in source_chain_boundary_read
        and "BAQ is not BEL" in source_chain_boundary_read
        and source_chain_gates.get("source_path") == "forward_evidence_scorecard.json"
        and source_chain_gates.get("source_loaded") is True
        and source_chain_gates.get("anchor_displacement_min") == 30
        and source_chain_gates.get("phase8_promotion_review_min") == 20
        and source_chain_gates.get("real_money_discussion_min") == 100
        and source_chain_gates.get("real_money_no_baq_as_bel_required") is True
        and "no BAQ-as-BEL substitution" in source_chain_gates.get("real_money_discussion_also_requires", [])
        and source_chain_hierarchy.get("not_settled_roi_evidence") is True
        and source_chain_hierarchy.get("not_live_profitability_evidence") is True
        and source_chain_hierarchy.get("not_promotion_readiness_evidence") is True
        and source_chain_hierarchy.get("not_anchor_change_evidence") is True
        and source_chain_hierarchy.get("not_real_money_evidence") is True,
        "source_chain_matrix_json_preserves_hierarchy_boundary",
        "source-chain matrix JSON keeps OP_DURABLE_K7 as anchor, CD_CORE_K8 as the primary OP/CD paper-basket companion, OP_REFINED_K7 as shadow/watch, BAQ-not-BEL, scorecard-sourced 30/20/100 gate fields with the no-BAQ real-money prerequisite, and no-ROI/no-live-profitability/no-promotion/no-anchor-change/no-real-money boundary flags",
    ))

    rule_notes: dict[str, str] = {}
    for relative_path in RULE_NOTE_PATHS:
        payload = json.loads((BASE / relative_path).read_text(encoding="utf-8"))
        notes = payload.get("notes")
        rule_notes[relative_path] = "\n".join(notes if isinstance(notes, list) else [])
    checks.append(require(
        "largest 2024-2025 OP holdout sample among current candidates" in rule_notes["op_anchor_rules.json"]
        and "among active rules" not in rule_notes["op_anchor_rules.json"]
        and "Current primary paper-trade rule-component basket for Phase 7; target-card availability still comes from daily preflight." in rule_notes["phase7_current_paper_rules.json"]
        and "OP + CD are paper-active rule components rather than a claim that today's card is active" in rule_notes["phase7_current_paper_rules.json"]
        and "active Phase 7 portfolio" not in rule_notes["phase7_current_paper_rules.json"]
        and "active basket is OP + CD" not in rule_notes["phase7_current_paper_rules.json"],
        "rule_file_notes_preserve_preflight_and_historical_evidence_language",
        "rule JSON notes now keep OP-anchor sample language historical/current-candidate based and describe the Phase 7 primary paper file as OP/CD rule components whose target cards still require daily preflight",
    ))

    cross_rows = {row["rule_id"]: row for row in csv.DictReader((BASE / "cross_family_decision_card.csv").open(newline="", encoding="utf-8"))}
    checks.append(require(
        cross_rows["OP_DURABLE_K7"].get("shadow_rank") == "LIVE_DEFAULT"
        and cross_rows["CD_CORE_K8"].get("shadow_rank") == "PRIMARY_SHADOW"
        and cross_rows["CD_CORE_K8"].get("role") == "PAPER"
        and "Paper now" in cross_rows["CD_CORE_K8"].get("decision_reason", "")
        and cross_rows["OP_REFINED_K7"].get("shadow_rank") == "SECONDARY_SHADOW"
        and cross_rows["OP_REFINED_K7"].get("role") == "WATCH",
        "cross_family_structured_legacy_rank_is_compatible",
        "cross-family CSV can retain legacy shadow_rank labels for compatibility, while the roles still keep CD_CORE_K8 in PAPER and OP_REFINED_K7 in WATCH",
    ))

    quickstart_text = read_text("VALIDATION_QUICKSTART.md")
    daily_guide_text = read_text("DAILY_ARTIFACT_GUIDE.md")
    status_text = read_text("COLE_STATUS_AND_PLAN.md")
    checks.append(require(
        "| Current hierarchy wording, `live_hierarchy` JSON fields, or `primary_companion` / legacy `primary_shadow` compatibility | `python3 validate_current_hierarchy_language.py` |" in quickstart_text
        and "out/status_validation/current_hierarchy_language/current_hierarchy_language_validation.md" in quickstart_text
        and "If the edit changes `OP_DURABLE_K7` / `CD_CORE_K8` / `OP_REFINED_K7` hierarchy wording or `primary_companion` / legacy `primary_shadow` structured keys" in quickstart_text
        and "| `validate_current_hierarchy_language.py` | Current hierarchy wording / structured-key compatibility check" in status_text
        and "out/status_validation/current_hierarchy_language/current_hierarchy_language_validation.md" in status_text
        and "without treating legacy `primary_shadow` compatibility as promotion evidence" in status_text,
        "front_door_current_hierarchy_route_present",
        "quickstart and main-status front doors now expose the direct current-hierarchy validator route, output path, and compatibility-only evidence boundary so CD_CORE_K8 companion wording and legacy primary_shadow keys do not drift quietly",
    ))

    checks.append(require(
        "run `python3 validate_current_hierarchy_language.py` when the question is specifically the live hierarchy wording" in daily_guide_text
        and "`live_hierarchy`, `primary_companion`, or legacy `primary_shadow` keys" in daily_guide_text
        and "not ROI, promotion, live-profitability, or real-money evidence" in daily_guide_text
        and "the direct current-hierarchy validator stays discoverable" in daily_guide_text,
        "daily_guide_current_hierarchy_route_present",
        "daily artifact guide now exposes the direct current-hierarchy validator route and evidence boundary so daily operators do not have to infer hierarchy-key coverage from broader top-card, wrapper, or project sweeps",
    ))

    checks.append(require(
        EVIDENCE_BOUNDARY.get("artifact_role") == "current hierarchy wording / structured-key compatibility validator"
        and EVIDENCE_BOUNDARY.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
        and EVIDENCE_BOUNDARY.get("not_settled_roi_evidence") is True
        and EVIDENCE_BOUNDARY.get("not_live_profitability_evidence") is True
        and EVIDENCE_BOUNDARY.get("not_real_money_evidence") is True
        and EVIDENCE_BOUNDARY.get("not_promotion_readiness_evidence") is True
        and EVIDENCE_BOUNDARY.get("not_anchor_change_evidence") is True
        and EVIDENCE_BOUNDARY.get("not_companion_change_evidence") is True
        and EVIDENCE_BOUNDARY.get("posture_read", {}).get("anchor") == "OP_DURABLE_K7"
        and EVIDENCE_BOUNDARY.get("posture_read", {}).get("primary_paper_basket_companion") == "CD_CORE_K8"
        and EVIDENCE_BOUNDARY.get("posture_read", {}).get("same_family_shadow_watch") == "OP_REFINED_K7",
        "current_hierarchy_json_publishes_machine_readable_evidence_boundary",
        "validator JSON publishes an evidence_boundary block so hierarchy wording cleanliness remains reproducibility metadata, not settled ROI, live profitability, promotion readiness, anchor-change, companion-change, or real-money evidence",
    ))
    checks.append(require(
        EVIDENCE_BOUNDARY.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE,
        "current_hierarchy_report_exposes_valid_evidence_scope",
        f"direct current-hierarchy validator report exposes valid_evidence_scope={VALID_EVIDENCE_SCOPE} so hierarchy wording/key compatibility stays classified as report-navigation metadata only",
    ))

    report_payload: dict[str, Any] = {
        "suite": "current_hierarchy_language",
        "suite_status": "pass",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "total_checks": len(checks),
        "check_count": len(checks),
        "current_surfaces_scanned": current_surfaces,
        "latest_daily_summary_surface": latest_daily_summary,
        "banned_current_phrases": BANNED_CURRENT_PHRASES,
        "json_hierarchy_reads": json_role_reads,
        "current_evidence_json_read": current_evidence_json_read,
        "settlement_audit_json_read": settlement_audit_json_read,
        "source_chain_matrix_json_read": source_chain_matrix_json_read,
        "rule_file_notes": rule_notes,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "summary": {
            "suite_read": (
                "Current hierarchy wording scan passes: OP_DURABLE_K7 is the anchor, CD_CORE_K8 is the primary OP/CD paper-basket companion "
                "with legacy primary_shadow compatibility only, and OP_REFINED_K7 remains the closest same-family shadow/watch challenger. "
                "The latest daily summary, current-evidence bridge markdown/JSON sidecar with source-consistency/freshness/gate checks, ops history, settlement audit markdown/JSON, daily guide, quickstart, main status map, live scanner usage, and operator runbook expose the direct validator route or the hierarchy boundary. "
                "The current-evidence bridge also publishes scorecard-backed canonical effective gate values and the settlement-audit -> current-bridge -> bridge-validator rebuild contract so missing or drifted top-card gate fields, stale source bytes, or skipped settlement-audit refreshes stay visible as source/provenance drift rather than changing the hierarchy read. "
                "The paper-trade source-chain matrix also carries the same OP/CD/Phase 8 hierarchy boundary in markdown and JSON alongside its scan/recommend/size/log readiness audit. "
                f"The scan exposes valid_evidence_scope={VALID_EVIDENCE_SCOPE} and is a wording/reproducibility guardrail only, not settled ROI, live profitability, promotion readiness, or real-money evidence."
            )
        },
        "checks": checks,
        "rebuild_command": REBUILD_COMMAND,
        "outputs": {
            "markdown": rel(out_md),
            "json": rel(out_json),
        },
    }

    md_lines = [
        "# Current Hierarchy Language Validation",
        "",
        f"Status: **{report_payload['suite_status'].upper()}**",
        f"Checks: **{len(checks)}/{len(checks)}**",
        f"Valid evidence scope: `valid_evidence_scope={VALID_EVIDENCE_SCOPE}`",
        f"Rebuild command: `{REBUILD_COMMAND}`",
        "",
        "## Current read",
        "",
        report_payload["summary"]["suite_read"],
        "",
        "## Surfaces scanned",
        "",
    ]
    md_lines.extend(f"- `{surface}`" for surface in current_surfaces)
    md_lines.extend([
        "",
        "## Checks",
        "",
    ])
    md_lines.extend(f"- `{check['check']}` — {check['detail']}" for check in checks)
    md_lines.extend([
        "",
        "## Evidence boundary",
        "",
        f"Artifact role: `{EVIDENCE_BOUNDARY['artifact_role']}`",
        "",
        "This validator is a hierarchy-wording and structured-key compatibility audit only. It does not create settled ROI, live profitability, promotion readiness, anchor-change evidence, companion-change evidence, or real-money evidence.",
        "",
        "Current posture preserved by the boundary:",
        f"- Anchor: `{EVIDENCE_BOUNDARY['posture_read']['anchor']}`",
        f"- Primary OP/CD paper-basket companion: `{EVIDENCE_BOUNDARY['posture_read']['primary_paper_basket_companion']}`",
        f"- Same-family shadow/watch challenger: `{EVIDENCE_BOUNDARY['posture_read']['same_family_shadow_watch']}`",
        "",
    ])

    out_dir.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md_lines), encoding="utf-8")
    out_json.write_text(json.dumps(report_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report_payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
