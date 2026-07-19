#!/usr/bin/env python3
"""
Validation for PAPER_TRADE_USAGE.md.

Purpose:
- keep the operator runbook aligned with the current paper-trade workflow
- stop the OP-anchor-first, primary OP/CD paper-basket companion, and separate Phase 8 shadow/watch routine from drifting
- pin the visible validator stack for the operator layer so missing helpers do not quietly disappear from the docs
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
DOC = BASE / "PAPER_TRADE_USAGE.md"
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_usage"
OUT_MD = OUT_DIR / "paper_trade_usage_validation.md"
OUT_JSON = OUT_DIR / "paper_trade_usage_validation.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
SOURCE_CHAIN_JSON = BASE / "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json"
REBUILD_COMMAND = "python3 validate_paper_trade_usage.py"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
VALID_EVIDENCE_SCOPE = "paper_trade_usage_operator_runbook_navigation_only"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade usage / operator workflow runbook validator",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "PAPER_TRADE_USAGE.md",
        "documented OP-anchor-first, primary OP/CD paper-basket companion, and separate Phase 8 shadow/watch command paths",
        "documented paper-trade operator validator ladder",
        "documented source-chain, settlement, right-now, refresh, and wrapper routes",
        "documented current-evidence bridge / combined operator_status_context, source_freshness, and operator_read_gate route",
        "documented current-evidence bridge / source-consistency / structured source-freshness route",
        "documented current-evidence bridge / operator_read_gate instruction-and-evidence gating route",
        "documented current-evidence bridge OP_REFINED scorecard CI-only diagnostic route",
        "documented current-evidence bridge scorecard_audit_route synchronization route",
        "documented current-evidence bridge rebuild_validation_contract order route",
        "documented copied-current-paper fanout after current-evidence bridge rebuilds",
        "documented cross-family current-paper snapshot route",
        "documented scorecard ranking-contract / gate-floor audit route",
        "forward_evidence_scorecard.json decision_gate_minimums used by operator gate wording",
        "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json counts used by source-chain guidance wording",
        "documented current hierarchy language / live_hierarchy validator route",
    ],
    "valid_use": "operator workflow, command routing, paper-trade runbook, and validator-ladder alignment audit",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "paper_trade_usage_validator_passes_are_navigation_metadata_only": True,
    "stronger_forward_confidence_requires": [
        "qualifying live paper signals",
        "ROI-complete settled paper rows",
        "settlement-quality checks",
        "other real forward observations",
    ],
    "non_goals": [
        "do not use operator-runbook cleanliness as settled ROI",
        "do not use command-route coverage as live profitability evidence",
        "do not promote OP_REFINED_K7 or Phase 8 from runbook validation cleanliness",
        "do not reopen current odds-only XGBoost from runbook validation cleanliness",
        "do not substitute BAQ for BEL",
        "do not treat documented paper-trade commands as real-money evidence",
    ],
}


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "pass", "detail": detail}


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
    no_baq_as_bel_required = True
    no_baq_clause = (
        "; the real-money discussion floor also requires no BAQ-as-BEL substitution"
        if no_baq_as_bel_required
        else ""
    )
    source_snippet = (
        "Decision-gate source: the runbook's primary first-read, Phase 8 review, and broader real-money-discussion floors are sourced from "
        f"`{source_path.name}` `decision_gate_minimums`: "
        f"`anchor_displacement.min_roi_complete_settled_observations={anchor_min}`, "
        f"`phase8_promotion_review.min_roi_complete_settled_observations={phase8_min}`, "
        f"and `real_money_discussion.min_total_settled_observations_with_usable_roi={real_money_min}`{no_baq_clause}. "
        "These are future ROI-complete paper-observation floors only; they do not mean any gate has cleared, "
        "do not promote Phase 8, do not replace `OP_DURABLE_K7`, and do not authorize real-money betting."
    )
    return {
        "source": SCORECARD_JSON.name,
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_no_baq_as_bel_required": no_baq_as_bel_required,
        "source_snippet": source_snippet,
    }


def source_chain_context() -> dict[str, Any]:
    payload = json.loads(SOURCE_CHAIN_JSON.read_text(encoding="utf-8"))
    return {
        "source": SOURCE_CHAIN_JSON.name,
        "total_guardrail_checks": require_positive_non_bool_int(
            payload.get("total_guardrail_checks"),
            source_name=SOURCE_CHAIN_JSON.name,
            field_name="total_guardrail_checks",
        ),
        "total_fixture_scenarios": require_positive_non_bool_int(
            payload.get("total_fixture_scenarios"),
            source_name=SOURCE_CHAIN_JSON.name,
            field_name="total_fixture_scenarios",
        ),
        "total_layers": require_positive_non_bool_int(
            payload.get("total_layers"),
            source_name=SOURCE_CHAIN_JSON.name,
            field_name="total_layers",
        ),
    }


def rebuild_validation_contract_context(current_evidence: dict[str, Any]) -> dict[str, Any]:
    contract = current_evidence.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise AssertionError("current_evidence_summary.json must publish rebuild_validation_contract as an object")
    order = contract.get("upstream_refresh_order")
    if not isinstance(order, list):
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order must be a list")
    commands = [item.get("command") for item in order if isinstance(item, dict)]
    expected_commands = [
        "python3 paper_trade_settlement_audit.py",
        "python3 current_evidence_summary.py",
        "python3 validate_current_evidence_summary.py",
    ]
    if commands != expected_commands:
        raise AssertionError(
            "current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order commands drifted"
        )
    expected_fields = {
        "rebuild_command": "python3 current_evidence_summary.py",
        "prerequisite_rebuild_command": "python3 paper_trade_settlement_audit.py",
        "direct_validation_command": "python3 validate_current_evidence_summary.py",
        "upstream_refresh_order_valid_use": (
            "reproducible rebuild order for current bridge provenance after scorecard/rules/ledger byte changes"
        ),
    }
    for key, expected in expected_fields.items():
        if contract.get(key) != expected:
            raise AssertionError(f"current_evidence_summary.json rebuild_validation_contract.{key} must be {expected!r}")
    for flag in (
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
        "requires_source_consistency_before_quoting_current_totals",
        "requires_source_freshness_before_right_now_instruction_use",
        "upstream_refresh_order_is_provenance_metadata_only",
        "green_checks_are_reproducibility_metadata_only",
        "not_settled_roi_or_real_money_evidence",
    ):
        if contract.get(flag) is not True:
            raise AssertionError(f"current_evidence_summary.json rebuild_validation_contract.{flag} must be true")
    return {
        "source": CURRENT_EVIDENCE_JSON.name,
        "source_path": "rebuild_validation_contract",
        "upstream_refresh_order_commands": commands,
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the paper-trade usage runbook")
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--current-evidence-json", type=Path, default=CURRENT_EVIDENCE_JSON)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def scorecard_gate_cli_contract_checks(
    scorecard_json_path: Path = SCORECARD_JSON,
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="paper_trade_usage_scorecard_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(scorecard_json_path).read_text(encoding="utf-8"))
        scorecard_path = tmp_root / "forward_evidence_scorecard.json"
        bad_out_dir = tmp_root / "nested" / "paper_trade_usage_validation"

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
                "--current-evidence-json",
                str(current_evidence_json_path),
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
                "validate_paper_trade_usage.py rejects a boolean scorecard anchor-displacement gate before creating nested output directories or partial validation artifacts",
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
                "--current-evidence-json",
                str(current_evidence_json_path),
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
                "validate_paper_trade_usage.py rejects a non-positive scorecard Phase 8 review gate before creating nested output directories or partial validation artifacts",
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
                "--current-evidence-json",
                str(current_evidence_json_path),
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
                "validate_paper_trade_usage.py rejects a non-positive scorecard real-money discussion gate before creating nested output directories or partial validation artifacts",
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
                "--current-evidence-json",
                str(current_evidence_json_path),
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
                "validate_paper_trade_usage.py rejects a scorecard real-money gate that drops the no-BAQ-as-BEL prerequisite before creating nested output directories or partial validation artifacts",
            )
        )

    return checks


def current_bridge_rebuild_cli_contract_checks(
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="paper_trade_usage_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json_path).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "paper_trade_usage_validation"
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
                "validate_paper_trade_usage.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial validation artifacts",
            )
        )

        weakened_contract_out_dir = tmp_root / "weakened" / "paper_trade_usage_validation"
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
                "validate_paper_trade_usage.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial validation artifacts",
            )
        )

    return checks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    text = DOC.read_text(encoding="utf-8")
    current_evidence = json.loads(Path(args.current_evidence_json).read_text(encoding="utf-8"))
    scorecard_payload = json.loads(Path(args.scorecard_json).read_text(encoding="utf-8"))
    scorecard_gates = scorecard_gate_context(args.scorecard_json)
    source_chain = source_chain_context()
    rebuild_contract = rebuild_validation_contract_context(current_evidence)
    out_dir = Path(args.out_dir)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name
    out_dir.mkdir(parents=True, exist_ok=True)
    current_primary = current_evidence["current_paper_status"]["primary"]
    current_rules = {row["rule_id"]: row for row in current_primary["rule_progress"]}
    first_gate = f"{int(current_primary['first_read']['current'])}/{int(current_primary['first_read']['threshold'])}"
    broad_gate = f"{int(current_primary['portfolio_review']['current'])}/{int(current_primary['portfolio_review']['threshold'])}"
    gate_progress = current_evidence.get("decision_gate_progress")
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
    operator_read_gate = current_evidence.get("operator_read_gate")
    if not isinstance(operator_read_gate, dict):
        raise AssertionError("current_evidence_summary.json must publish operator_read_gate as an object")
    if operator_read_gate != current_evidence.get("current_paper_status", {}).get("operator_read_gate"):
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
        "has_api_access_failure_context",
        "has_scanner_failure_boundary",
        "has_stale_cache_fallback_context",
        "has_wrapper_refresh_action",
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
        "promotion",
        "live-profitability",
        "bankroll",
        "real-money",
    ):
        if phrase not in operator_read_gate_read:
            raise AssertionError(f"current_evidence_summary.json operator_read_gate.read missing {phrase!r}")
    operator_read_gate_bridge_phrase = (
        f"It also publishes `operator_read_gate` from `current_evidence_summary.json`: {operator_read_gate_read} "
        f"Gate status `{operator_read_gate['gate_status']}` and recommended command `{operator_read_gate['recommended_command']}` are "
        "operator instruction/evidence-read gating only, not no-target evidence, clean-empty evidence, bet readiness, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence."
    )
    combined_operator_route_phrase = (
        "use the combined `operator_status_context` + `source_freshness` / `right_now_freshness_state_valid` / "
        "`requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` / "
        "`recommended_command` route before using stale or missing-state right-now cards as today's operator instruction or evidence"
    )
    cd_rows = int(current_rules["CD_CORE_K8"]["roi_complete_settled_rows"])
    op_rows = int(current_rules["OP_DURABLE_K7"]["roi_complete_settled_rows"])
    open_settlements = int(current_primary.get("open_settlements", 0))
    open_settlement_summary = str(current_primary.get("open_settlement_summary") or "").strip()
    open_queue = current_primary.get("open_settlement_queue_by_rule")
    if not isinstance(open_queue, dict):
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule must be an object"
        )
    open_settlement_queue_state = str(open_queue.get("open_settlement_queue_state") or "").strip()
    open_settlement_context = str(open_queue.get("open_settlement_context") or "").strip()
    open_settlement_detail_read = str(open_queue.get("detail_read") or "").strip()
    expected_open_settlement_queue_state = "closed" if open_settlements == 0 else "open"
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
    if open_settlements == 0 and open_settlement_context != "no open primary settlement rows":
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_context must publish the closed-queue context when no rows are open"
        )
    if open_settlements > 0 and not open_settlement_context:
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
        f"source-published settlement queue read: settlement queue state `{open_settlement_queue_state}` / "
        f"{open_settlement_context}; detail: {open_settlement_detail_read}"
    )
    if open_settlements and (not open_settlement_summary or open_settlement_summary == "none"):
        open_settlement_summary = "open row identity missing from current evidence bridge; inspect settlement audit before settlement"
    recommendation_context = current_primary.get("recommendation_context", {})
    recommendation_read = str(recommendation_context.get("read") or "").strip()
    if open_settlements and recommendation_read:
        queue_recommendation_context_label = "current open-row identity plus recommendation-state context"
        current_open_row_context_phrase = (
            f"{source_published_queue_read}; current open settlement row `{open_settlement_summary}` remains settlement workflow, not a bet-ready "
            f"ticket or forward-performance proof; latest recommendation-state context: {recommendation_read}"
        )
        bridge_open_row_context_phrase = (
            f"{source_published_queue_read}; current open settlement row `{open_settlement_summary}` beside the latest recommendation-state context"
        )
    elif open_settlements:
        queue_recommendation_context_label = "current open-row identity plus recommendation-state context"
        current_open_row_context_phrase = (
            f"{source_published_queue_read}; current open settlement row `{open_settlement_summary}` is settlement workflow, not a bet-ready "
            "ticket or forward-performance proof"
        )
        bridge_open_row_context_phrase = f"{source_published_queue_read}; current open settlement row `{open_settlement_summary}`"
    else:
        queue_recommendation_context_label = "closed settlement-queue plus recommendation-state context"
        current_open_row_context_phrase = (
            f"{source_published_queue_read} The current bridge has no open primary settlement rows; do not leave stale open-row identity wording in "
            "the runbook"
        )
        bridge_open_row_context_phrase = source_published_queue_read
    current_gate_progress_phrase = f"bridge-published `decision_gate_progress` read (`{gate_progress_read}`)"
    current_gate_detail_phrase = "bridge-published `decision_gate_progress` split"
    current_cd_only_phrase = "bridge-published CD-only settled primary sample / `OP_DURABLE_K7` settled-row boundary"
    current_ci_only = current_evidence.get("scorecard_ci_only_promotion_check", {})
    source_ci_only = scorecard_payload.get("ci_only_promotion_diagnostics", {}).get("OP_REFINED_K7", {})
    ci_only_source = "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7"
    scorecard_audit_route = current_evidence.get("scorecard_audit_route")
    if not isinstance(scorecard_audit_route, dict):
        raise AssertionError("current_evidence_summary.json must publish scorecard_audit_route as an object")
    expected_gate_floor_snapshot = {
        "anchor_displacement_min_roi_complete_settled_observations": scorecard_gates[
            "anchor_displacement_min_roi_complete_settled_observations"
        ],
        "phase8_promotion_review_min_roi_complete_settled_observations": scorecard_gates[
            "phase8_promotion_review_min_roi_complete_settled_observations"
        ],
        "real_money_discussion_min_total_settled_observations_with_usable_roi": scorecard_gates[
            "real_money_discussion_min_total_settled_observations_with_usable_roi"
        ],
        "real_money_no_baq_as_bel_required": scorecard_gates["real_money_no_baq_as_bel_required"],
    }
    expected_scorecard_audit_fields = {
        "markdown_path": "SCORECARD_RANKING_CONTRACT_AUDIT.md",
        "json_path": "scorecard_ranking_contract_audit.json",
        "validator_command": "python3 validate_scorecard_ranking_contract_audit.py",
        "gate_floor_source": "forward_evidence_scorecard.json:decision_gate_minimums",
        "valid_use": "navigation route for scorecard gate/ranking/CI-only/timezone/no-BAQ synchronization checks",
    }
    for key, expected in expected_scorecard_audit_fields.items():
        if scorecard_audit_route.get(key) != expected:
            raise AssertionError(f"current_evidence_summary.json scorecard_audit_route.{key} must be {expected!r}")
    if scorecard_audit_route.get("gate_floor_snapshot") != expected_gate_floor_snapshot:
        raise AssertionError("current_evidence_summary.json scorecard_audit_route.gate_floor_snapshot must copy scorecard gates")
    if scorecard_audit_route.get("artifacts_present") is not True:
        raise AssertionError("current_evidence_summary.json scorecard_audit_route.artifacts_present must be true")
    for flag in (
        "not_forward_performance_evidence",
        "not_settled_roi_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_bankroll_guidance",
        "not_real_money_evidence",
    ):
        if scorecard_audit_route.get(flag) is not True:
            raise AssertionError(f"current_evidence_summary.json scorecard_audit_route.{flag} must be true")
    scorecard_audit_route_read = str(scorecard_audit_route.get("route_read") or "").strip()
    for phrase in (
        "copied 30/20/100 gate floors",
        "tier-first ranking",
        "OP_REFINED CI-only support context",
        "generated-at timezone provenance",
        "no-BAQ-as-BEL prerequisite",
    ):
        if phrase not in scorecard_audit_route_read:
            raise AssertionError(f"current_evidence_summary.json scorecard_audit_route.route_read missing {phrase!r}")
    scorecard_audit_route_phrase = (
        "It also publishes `scorecard_audit_route` from `current_evidence_summary.json`: "
        "Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus "
        "`python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 gate floors, "
        "tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, "
        "and no-BAQ-as-BEL prerequisite drift across report-facing surfaces."
    )
    rebuild_contract_phrase = (
        "It also publishes `rebuild_validation_contract` from `current_evidence_summary.json`: after scorecard, rules, "
        "signals, settlement-ledger, or other bridge source-byte changes, run `python3 paper_trade_settlement_audit.py`, "
        "then `python3 current_evidence_summary.py`, then `python3 validate_current_evidence_summary.py` before quoting "
        "the bridge. Treat that order as provenance/rebuild metadata only, not settled ROI, promotion readiness, live "
        "profitability, bankroll guidance, or real-money evidence."
    )
    copied_current_fanout_intro = (
        "After the bridge regenerates cleanly, do not stop at the three-command bridge check if report-facing "
        "comparisons will be quoted."
    )
    copied_current_fanout_boundary = (
        "That fanout is drift prevention for copied current-paper snapshots, not evidence movement, settled ROI, "
        "promotion readiness, live profitability, bankroll guidance, or real-money evidence."
    )
    inventory_progress_phrase = f"current primary progress at {first_gate} and {broad_gate}"
    validator_gate_phrase = "bridge-published current gates"
    stale_open_identity_phrase_allowed = open_settlements > 0
    stale_open_identity_phrase_absent_or_expected = (
        "current open-row identity plus recommendation-state context" in text
        if stale_open_identity_phrase_allowed
        else "current open-row identity plus recommendation-state context" not in text
    )
    suite_gate_phrase = (
        f"bridge-published `decision_gate_progress` read ({gate_progress_read}) plus the CD-only settled sample / OP_DURABLE_K7 ROI-complete "
        f"row boundary plus {queue_recommendation_context_label}"
    )

    checks: list[dict[str, Any]] = []
    if Path(args.scorecard_json).resolve() == SCORECARD_JSON.resolve():
        checks.extend(scorecard_gate_cli_contract_checks(args.scorecard_json, args.current_evidence_json))
    if Path(args.current_evidence_json).resolve() == CURRENT_EVIDENCE_JSON.resolve():
        checks.extend(current_bridge_rebuild_cli_contract_checks(args.current_evidence_json))
    checks.append(
        require(
            "This document is a **workflow and operator runbook**, not a profit-proof or CI-backed forward-validation report." in text
            and f"- Valid evidence scope: `valid_evidence_scope={VALID_EVIDENCE_SCOPE}`." in text
            and "Fast boundary checklist:" in text
            and "- Not a current-day scanner result." in text
            and "- Not a live paper-trade ledger." in text
            and "- Not settled ROI, live profitability, promotion readiness, anchor displacement, bankroll guidance, or real-money evidence." in text
            and "- Clean validators, quiet/no-target/cache runs, and top-card freshness are operator-readiness metadata only." in text
            and "- Stronger confidence still requires qualifying live paper signals, ROI-complete settled paper rows, settlement-quality checks, and no BAQ-as-BEL substitution." in text
            and "Operational summaries and machine-readable operator cards such as `PAPER_TRADE_NOW.md`, `PAPER_TRADE_NOW.txt`, `PAPER_TRADE_NOW.json`, `daily_summary.txt`, `summary.txt`, `OPS_HISTORY.md`, and this runbook can explain what to do next, but they do not replace settled forward results." in text
            and "## Settlement-audit action-line contract" in text
            and "`paper_trade_settlement_audit.py` publishes lane-level `next_action` and `next_action_reason` values for the primary and shadow ledgers." in text
            and "direct `Primary settlement-audit action:` and `Shadow settlement-audit action:` lines" in text
            and "Settlement-audit actions are ledger-readiness guidance only; they are not new forward evidence by themselves." in text
            and "Treat action slugs such as `collect_signals`, `settle_open_rows`, and `repair_roi_coverage` as operational routing for ledger readiness." in text
            and "They do not prove a lane is profitable, do not promote `OP_REFINED_K7`, and do not change the `OP_DURABLE_K7` anchor without ROI-complete settled forward evidence." in text
            and "duplicate custom lane-name rejection before output artifacts" in text
            and "blank signal-key rows in signal ledgers, blank settlement-key rows in settlement ledgers, structural repairs, matched-key metadata mismatches, duplicate custom lane-name rejection before output artifacts, ROI-complete row counts, primary/shadow sample gates, and shadow per-rule review floors stay separately labeled without becoming new forward evidence" in text
            and "The direct daily-summary validator, saved-live refresh validator, and daily-wrapper validator all pin this path" in text
            and "## Right-now top-card JSON contract" in text
            and "`PAPER_TRADE_NOW.txt`, `PAPER_TRADE_NOW.md`, and `PAPER_TRADE_NOW.json` are a matched top-card bundle." in text
            and "The JSON file is the machine-readable sibling used by validators and automation, so do not treat it as optional" in text
            and "The markdown mirror may fall back to a placeholder if only markdown rendering fails, but `PAPER_TRADE_NOW.json` should still match the source-layer `paper_trade_now.py --format json` payload." in text
            and "Only a full right-now-helper failure should leave an explicit no-new-forward-evidence JSON placeholder." in text
            and "This JSON parity is operator-routing reproducibility, not new forward evidence." in text
            and "If the edit changes the live hierarchy block, `live_hierarchy` keys, `primary_companion`, or the legacy compatibility-only `primary_shadow` key, run `python3 validate_current_hierarchy_language.py` before the broader right-now / daily-wrapper validations." in text
            and "out/status_validation/current_hierarchy_language/current_hierarchy_language_validation.md" in text
            and "a green read is hierarchy wording / metadata routing only — not anchor displacement, companion promotion, live profitability, or real-money evidence" in text,
            "workflow_not_proof_frame",
            "paper-trade usage now says plainly that it is workflow guidance for operators, not forward-proof, opens with a compact no-current-scanner/no-live-ledger/no-ROI/no-promotion/no-real-money checklist, says clean validators, quiet/no-target/cache runs, and top-card freshness are operator-readiness metadata only, says stronger confidence requires qualifying live paper signals, ROI-complete settled rows, settlement-quality checks, and no BAQ-as-BEL substitution, keeps operator surfaces from replacing settled forward results, keeps settlement-audit action lines as ledger-readiness routing pinned through the daily-summary, refresh, and wrapper validators rather than profitability evidence, routes settlement-audit repair labels and ledger-completeness / ROI-coverage wording to the direct audit validator, requires right-now text/markdown/JSON parity unless the full right-now helper failed into an explicit no-new-evidence placeholder, and routes live hierarchy wording / metadata-key edits to the current-hierarchy validator before broader top-card or wrapper validations",
        )
    )
    checks.append(
        require(
            f"- Valid evidence scope: `valid_evidence_scope={VALID_EVIDENCE_SCOPE}`." in text
            and EVIDENCE_BOUNDARY.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and VALID_EVIDENCE_SCOPE.endswith("_navigation_only"),
            "paper_trade_usage_valid_evidence_scope_visible",
            "paper-trade usage now exposes exact valid_evidence_scope=paper_trade_usage_operator_runbook_navigation_only in the runbook and validator boundary metadata so copied operator-runbook snippets stay framed as navigation metadata only",
        )
    )
    checks.append(
        require(
            "- `forward_evidence_scorecard.txt` for the current rule-family hierarchy" in text
            and "- `CROSS_FAMILY_DECISION.md` for the direct anchor / paper / watch shortlist plus the current-paper snapshot caveat; use `validate_cross_family_decision.py` when the question is stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, or whether the current paper context can be read as OP-anchor proof or cross-family promotion evidence. It cannot." in text
            and "- `OP_ANCHOR_METHOD_COMPARISON.md` / `op_anchor_method_comparison.json` for the OP-centered Harville / current odds-only XGBoost evidence-class comparison and exact source-byte provenance plus readable `evidence_boundary_text`; those fingerprints and boundary text are reproducibility/no-new-evidence metadata only, not settled ROI, promotion readiness, live profitability, or real-money evidence" in text
            and "- `paper_trade_forward_check.py` and the saved per-lane forward-check artifacts once settled paper trades exist" in text
            and "- the 2024-2025 holdout and train-only walk-forward posture summarized in `COLE_STATUS_AND_PLAN.md`" in text
            and "For the OP-anchor research provenance/readable-boundary route behind the paper-trade posture, read `OP_ANCHOR_METHOD_COMPARISON.md` beside `op_anchor_method_comparison.json` and run `python3 validate_op_anchor_method_comparison.py`." in text
            and "That pair ties the OP / Harville / current odds-only XGBoost wording back to exact input bytes for `forward_evidence_scorecard.csv`, `compare_main_approaches.csv`, `method_family_decision_card.csv`, `cross_family_decision_card.csv`, and `ab_downstream_comparison_results.json`, and the JSON sidecar publishes readable `evidence_boundary_text` beside the machine-readable boundary." in text
            and "Treat the source fingerprints and boundary text as provenance/reproducibility and no-new-evidence metadata only — not settled ROI, not promotion readiness, not live profitability, and not real-money evidence." in text,
            "evidence_sources_named",
            "paper-trade usage now points readers to the actual frozen evidence sources, including the OP-anchor markdown/JSON source-provenance plus readable-boundary route, instead of letting the runbook read like proof on its own",
        )
    )
    checks.append(
        require(
            "For the cross-family shortlist and current-paper caveat route, read `CROSS_FAMILY_DECISION.md` and run `python3 validate_cross_family_decision.py`." in text
            and "That direct card is the narrow check for `OP_DURABLE_K7` as `ANCHOR`, `CD_CORE_K8` as `PAPER`, `OP_REFINED_K7` as `WATCH`, plus the current-paper snapshot showing stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and the boundary that those rows and queue state are not OP-anchor proof, cross-family promotion evidence, live profitability, bankroll guidance, or real-money evidence." in text
            and "- `CROSS_FAMILY_DECISION.md` / `cross_family_decision_card.csv` — direct anchor / paper / watch card for `OP_DURABLE_K7`, `CD_CORE_K8`, and `OP_REFINED_K7`, including the current-paper snapshot caveat that keeps stale-card refresh routing, CD-only settled rows, and source-published settlement-queue state/context out of OP-anchor proof or cross-family promotion evidence" in text
            and "- `validate_cross_family_decision.py` — direct validator for the cross-family card, including saved CSV/markdown parity, real CLI stdout, current anchor / paper / watch ordering, current-paper snapshot caveat, and no cross-family-promotion evidence boundary" in text,
            "cross_family_current_paper_route_documented",
            "paper-trade usage now points operator-runbook readers to the direct cross-family card and validator when the issue is anchor / paper / watch ordering plus the current-paper snapshot caveat, while keeping stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green validation out of OP-anchor proof or cross-family promotion evidence",
        )
    )
    checks.append(
        require(
            "For the main status document and repo-map route, read `COLE_STATUS_AND_PLAN.md` and run `python3 validate_cole_status_and_plan.py`." in text
            and "Use that direct validator when the question is whether the main status map still exposes `status_doc_base_api_access_route_documented` for base API-access / HTTP 403 status-summary action-recheck edits before lane enrichment." in text
            and "A green status-doc read is status/map alignment only, not settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence." in text
            and "- `COLE_STATUS_AND_PLAN.md` — main status document and repo map, including the frozen posture, reading order, and base API-access / HTTP 403 status-summary route into the direct status-doc validator before lane enrichment" in text
            and "- `validate_cole_status_and_plan.py` — direct validator for the main status document, including `status_doc_base_api_access_route_documented` so base API-access / HTTP 403 action-recheck route wording does not drift quietly in the status map" in text,
            "main_status_api_access_route_documented",
            "paper-trade usage now points operator-runbook readers to the direct main-status validator when the issue is whether the status map exposes status_doc_base_api_access_route_documented for base API-access / HTTP 403 status-summary action-recheck route edits before lane enrichment",
        )
    )
    checks.append(
        require(
            f"- `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` for the source-checked bridge from frozen hierarchy to current paper totals; it cross-checks `PAPER_TRADE_NOW.json`, the settlement audit, and the primary settlement CSV, exposes a combined current-paper read route across `operator_status_context`, `source_freshness` / `right_now_freshness_state` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use`, and `operator_read_gate`, keeps the {queue_recommendation_context_label} visible, carries the scorecard-sourced `ci_only_promotion_diagnostics.OP_REFINED_K7` boundary with `ci_only_promotion_allowed=false`, publishes `scorecard_audit_route` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks, publishes `rebuild_validation_contract` for the settlement-audit -> current-bridge -> bridge-validator order after source-byte changes, and only then turns the {current_gate_progress_phrase} into report-ready wording" in text
            and f"When the question is what the current paper totals mean for Cole-facing wording, read `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` before quoting top-card, ops-bucket, audit, or ledger totals; treat `source_consistency.overall_match=false` as repair-first before using those numbers; require the combined `operator_status_context` + `source_freshness` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` / `recommended_command` route before using stale or missing-state right-now cards as today's operator instruction or evidence; and if that route requires refresh, run `./run_daily_portfolio_observation.sh` before treating the best-action card as today's operator instruction. Current bridge context: {current_open_row_context_phrase}" in text
            and "## Current-evidence bridge contract" in text
            and f"Use them when turning the latest paper totals into a short update for Cole, especially before summarizing {current_gate_detail_phrase}, the {current_cd_only_phrase}, the {queue_recommendation_context_label}, or the OP_REFINED positive-CI warning." in text
            and "The bridge reads `forward_evidence_scorecard.json`, `PAPER_TRADE_NOW.json`, `out/paper_trade_settlement_audit.json`, and the primary settlement CSV, then publishes `source_consistency`, `operator_status_context`, `source_freshness`, and `operator_read_gate` blocks." in text
            and "Use those blocks together, not as separable shortcuts" in text
            and combined_operator_route_phrase in text
            and "It also publishes the scorecard-sourced `scorecard_ci_only_promotion_check` for `OP_REFINED_K7`: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` with `ci_only_promotion_allowed=false`, so OP_REFINED's positive CI lower bound stays support context rather than a current-paper promotion trigger." in text
            and f"It also publishes `scorecard_audit_route` from `current_evidence_summary.json`: {scorecard_audit_route_read} Treat that route as report-synchronization metadata only, not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence." in text
            and rebuild_contract_phrase in text
            and f"It also publishes `decision_gate_progress` from `current_evidence_summary.json` as a report-routing read: {gate_progress_read}" in text
            and bridge_open_row_context_phrase in text
            and operator_read_gate_bridge_phrase in text
            and stale_open_identity_phrase_absent_or_expected
            and "If `source_consistency.overall_match` is false, repair the top-card / audit / CSV mismatch before quoting current paper numbers." in text
            and "If `source_freshness.right_now_freshness_state_valid` is not true, treat the right-now source as under-specified and rerun `./run_daily_portfolio_observation.sh` before using the best-action card." in text
            and f"source-consistency, operator-status context, structured source-freshness, operator-read-gate routing, {queue_recommendation_context_label}, scorecard CI-only boundary, scorecard audit route, and no-overclaim metadata — not settled ROI, live profitability, promotion readiness, anchor displacement, bankroll guidance, or real-money evidence" in text
            and current_ci_only.get("source") == ci_only_source
            and current_ci_only.get("scorecard_ci_only_promotion_diagnostic") == source_ci_only
            and current_ci_only.get("ci_only_promotion_allowed") is False
            and "python3 paper_trade_settlement_audit.py" in text
            and "python3 current_evidence_summary.py" in text
            and "python3 validate_current_evidence_summary.py" in text,
            "current_evidence_bridge_route_documented",
            f"paper-trade usage now routes Cole-facing current paper-total wording through the source-checked current-evidence bridge, including source_consistency repair-first behavior, the combined operator_status_context/source_freshness/operator_read_gate route, structured source_freshness state validity, source_freshness true/false behavior, operator_read_gate instruction/evidence-read routing, the CD-only settled-sample boundary, {queue_recommendation_context_label}, scorecard-sourced OP_REFINED CI-only diagnostic, bridge-published scorecard_audit_route synchronization route, bridge-published rebuild_validation_contract order, bridge-published gate wording, and the direct settlement-audit/regenerate/validate commands",
        )
    )
    checks.append(
        require(
            rebuild_contract_phrase in text
            and rebuild_contract["upstream_refresh_order_commands"] == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and rebuild_contract["requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"] is True
            and rebuild_contract["requires_source_consistency_before_quoting_current_totals"] is True
            and rebuild_contract["requires_source_freshness_before_right_now_instruction_use"] is True
            and rebuild_contract["upstream_refresh_order_is_provenance_metadata_only"] is True
            and rebuild_contract["not_settled_roi_or_real_money_evidence"] is True
            and "After settlement, top-card, audit, scorecard, or right-now source-freshness state changes, regenerate and validate the bridge with:" in text
            and "python3 paper_trade_settlement_audit.py" in text
            and "then `python3 current_evidence_summary.py`, then `python3 validate_current_evidence_summary.py` before quoting the bridge" in text,
            "current_bridge_rebuild_order_documented",
            "paper-trade usage now sources the current bridge rebuild order from current_evidence_summary.json.rebuild_validation_contract and preserves the settlement-audit -> current-bridge -> bridge-validator order as provenance metadata only",
        )
    )
    checks.append(
        require(
            copied_current_fanout_intro in text
            and "Validate the copied-current-paper fanout first:" in text
            and "python3 validate_frozen_portfolio_eval_caution.py" in text
            and "python3 validate_ab_downstream_comparison.py" in text
            and "python3 validate_compare_main_approaches.py" in text
            and "python3 validate_op_anchor_method_comparison.py" in text
            and "python3 validate_op_family_decision.py" in text
            and "python3 validate_cross_family_decision.py" in text
            and "python3 validate_method_family_decision_card.py" in text
            and "python3 validate_portfolio_decision_card.py" in text
            and "python3 validate_compare_recommender_scope_paths.py" in text
            and "python3 validate_scorecard_ranking_contract_audit.py" in text
            and "python3 validate_frozen_evidence_chain.py --reuse-existing-child-json" in text
            and "python3 validate_report_surfaces.py --reuse-existing-child-json" in text
            and "python3 validate_project_surfaces.py --reuse-existing-child-json" in text
            and copied_current_fanout_boundary in text,
            "current_bridge_copied_current_fanout_documented",
            "paper-trade usage now says a clean current-bridge rebuild is not enough before report-facing comparison quotes; the copied-current-paper fanout has to be checked as drift prevention only, not evidence movement",
        )
    )
    checks.append(
        require(
            scorecard_audit_route_phrase in text
            and scorecard_audit_route.get("gate_floor_snapshot") == expected_gate_floor_snapshot
            and scorecard_audit_route.get("artifacts_present") is True
            and scorecard_audit_route.get("not_forward_performance_evidence") is True
            and scorecard_audit_route.get("not_settled_roi_evidence") is True
            and scorecard_audit_route.get("not_promotion_readiness_evidence") is True
            and scorecard_audit_route.get("not_live_profitability_evidence") is True
            and scorecard_audit_route.get("not_bankroll_guidance") is True
            and scorecard_audit_route.get("not_real_money_evidence") is True
            and "Treat that route as report-synchronization metadata only, not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence." in text,
            "current_evidence_scorecard_audit_route_documented",
            "paper-trade usage now consumes current_evidence_summary.json.scorecard_audit_route for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks instead of only naming the scorecard audit as a separate direct artifact",
        )
    )
    checks.append(
        require(
            combined_operator_route_phrase in text
            and "Use those blocks together, not as separable shortcuts" in text
            and "require the combined `operator_status_context` + `source_freshness` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` / `recommended_command` route before using stale or missing-state right-now cards as today's operator instruction or evidence" in text
            and "if that route requires refresh, run `./run_daily_portfolio_observation.sh` before treating the best-action card as today's operator instruction" in text
            and "operator_status_context` plus `source_freshness` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use` gate and the structured `operator_read_gate` read" not in text,
            "current_evidence_combined_operator_read_route_documented",
            "paper-trade usage now requires the current-evidence bridge's operator_status_context, source_freshness, and operator_read_gate blocks as one combined read route before stale or missing-state right-now cards become today's instruction or evidence",
        )
    )
    checks.append(
        require(
            scorecard_gates["source_snippet"] in text
            and scorecard_gates["anchor_displacement_min_roi_complete_settled_observations"] == 30
            and scorecard_gates["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and scorecard_gates["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and scorecard_gates["real_money_no_baq_as_bel_required"] is True,
            "scorecard_gate_source_documented_for_operator_runbook",
            "paper-trade usage now names forward_evidence_scorecard.json decision_gate_minimums as the source for the 30-row primary/anchor first-read floor, 20-row Phase 8 review floor, and 100-row real-money-discussion floor while preserving the no-BAQ-as-BEL prerequisite and saying those are future ROI-complete observation requirements rather than cleared gates",
        )
    )
    checks.append(
        require(
            "When the question is whether report-facing surfaces still copy those scorecard gates, the tier-first ranking contract, OP_REFINED CI-only support context, generated-at timezone provenance, and the no-BAQ-as-BEL prerequisite correctly, read `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` and run `python3 validate_scorecard_ranking_contract_audit.py`. Treat that audit as report-synchronization / reproducibility metadata only, not a live paper-trade result, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence." in text,
            "scorecard_audit_gate_route_documented",
            "paper-trade usage now points scorecard gate-floor / tier-first ranking / OP_REFINED CI-only / no-BAQ prerequisite questions to the direct scorecard audit and validator while keeping that route as report-synchronization metadata only",
        )
    )
    checks.append(
        require(
            "If `source_freshness.requires_refresh_before_right_now_use` is true, rerun `./run_daily_portfolio_observation.sh` before treating `PAPER_TRADE_NOW`'s best-action card as today's operator instruction or evidence." in text
            and "If `source_freshness.requires_refresh_before_right_now_use` is true, rerun `./run_daily_portfolio_observation.sh` before treating `PAPER_TRADE_NOW`'s best-action card as today's operator instruction or evidence." in text
            and "If `source_freshness.requires_refresh_before_right_now_use` is false, the saved best-action card is fresh against the bridge reference date, but still treat that as operator-readiness metadata rather than performance proof." in text
            and f"source-freshness comparison between the right-now as-of date and bridge reference date, operator-status context preservation, operator-read-gate routing, {queue_recommendation_context_label}, the scorecard-sourced OP_REFINED CI-only boundary, bridge-published `scorecard_audit_route`, plus preservation of `PAPER_TRADE_NOW.run_freshness.freshness_state`" in text
            and "source-freshness refresh instruction" in text
            and "right-now source-freshness state changes" in text,
            "current_evidence_source_freshness_route_documented",
            "paper-trade usage now makes source_freshness a first-class runbook gate: refresh the daily wrapper before using a stale best-action card as today's instruction, distinguish fresh cards from refresh-required cards, and treat freshness as operator-readiness metadata rather than performance proof",
        )
    )
    checks.append(
        require(
            "`source_freshness` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use`" in text
            and "`source_freshness.right_now_freshness_state_valid` is not true" in text
            and "`right_now_freshness_state` / `right_now_freshness_state_valid`" in text
            and "structured source-freshness state" in text
            and f"operator-status context, structured source-freshness, operator-read-gate routing, {queue_recommendation_context_label}, scorecard CI-only boundary, scorecard audit route, and no-overclaim metadata" in text,
            "current_evidence_structured_freshness_state_route_documented",
            "paper-trade usage now says the current-evidence bridge must preserve right_now_freshness_state/right_now_freshness_state_valid from PAPER_TRADE_NOW and fail closed to the wrapper refresh path when the state is missing or invalid",
        )
    )
    checks.append(
        require(
            "+ `operator_read_gate` / `requires_refresh_before_evidence_read` / `recommended_command` route before using stale or missing-state right-now cards as today's operator instruction or evidence" in text
            and operator_read_gate_bridge_phrase in text
            and "`operator_read_gate` from `current_evidence_summary.json`" in text
            and "combined operator-status / source-freshness / operator-read-gate route" in text
            and "operator-read-gate routing" in text
            and isinstance(operator_read_gate.get("requires_refresh_before_evidence_read"), bool)
            and isinstance(operator_read_gate.get("recommended_command"), str)
            and bool(operator_read_gate.get("recommended_command"))
            and operator_read_gate.get("current_top_card_counts_as_no_target_evidence") is False
            and operator_read_gate.get("current_top_card_counts_as_clean_empty_evidence") is False
            and operator_read_gate.get("current_top_card_counts_as_bet_readiness_evidence") is False
            and operator_read_gate.get("current_top_card_counts_as_settled_roi_evidence") is False
            and operator_read_gate.get("not_live_profitability_evidence") is True
            and operator_read_gate.get("not_real_money_evidence") is True,
            "current_evidence_operator_read_gate_route_documented",
            "paper-trade usage now treats current_evidence_summary.json operator_read_gate as a first-class runbook gate, requiring the recommended wrapper refresh command before stale best-action-card instruction/evidence use and keeping that gate out of no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, and real-money evidence",
        )
    )
    checks.append(
        require(
            "# Most honest current-paper start: OP anchor only" in text
            and "./run_paper_trade_cycle.sh --rules op_anchor_rules.json" in text
            and "# Most honest live-paper start: OP anchor only" not in text,
            "op_anchor_start_command",
            "paper-trade usage still gives the OP-anchor-only start command as the safest current-paper entrypoint without the old live-paper start label",
        )
    )
    checks.append(
        require(
            "./run_paper_trade_cycle.sh --rules phase7_current_paper_rules.json" in text
            and "# Current primary paper basket rules: OP + CD (BEL dormant; daily preflight still decides whether target cards exist)" in text
            and "# Current active portfolio paper basket: OP + CD" not in text
            and "./run_daily_portfolio_observation.sh" in text,
            "primary_and_daily_commands",
            "paper-trade usage still shows both the current primary paper basket command and the preferred daily wrapper command, while the command comment no longer implies OP/CD target cards are calendar-active without preflight",
        )
    )
    checks.append(
        require(
            "Start with `op_anchor_rules.json` when the goal is the single safest current-paper entrypoint." in text
            and "Use `phase7_current_paper_rules.json` when the goal is the **current primary paper basket**." in text
            and "That reflects the current rule-basket posture of Phase 7: OP + CD are paper-active rule components, with BEL removed because it has no current forward races; the daily wrapper preflight still decides whether OP or CD target cards actually exist today." in text
            and "Inside that basket, `OP_DURABLE_K7` remains the safest anchor and `CD_CORE_K8` remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion." in text
            and "Start with `op_anchor_rules.json` when the goal is the single safest active entrypoint." not in text
            and "current operational reality of Phase 7: active OP + CD" not in text
            and "strongest overall non-anchor shadow" not in text
            and "strongest non-anchor shadow inside the live lane" not in text
            and "Keep `phase8_shadow_rules.json` in shadow mode only." in text
            and "Inside that shadow lane, `OP_REFINED_K7` is still the narrower same-family challenger, not a promoted replacement for the primary OP anchor, while `KEE_K9`, `SA_K9`, and `DMR_FALL_K7` remain observation-only pockets rather than near-promotion cases. The broader selective-family secondary lines behind that shadow read are replay context on walk-forward test years, not extra train-only validation." in text,
            "deployment_order_guardrails",
            "paper-trade usage still keeps OP anchor first, Phase 7 primary, and Phase 8 shadow-only in the recommended deployment order, now distinguishes paper-active rule-basket posture from daily target-card availability, names CD_CORE_K8 as the primary OP/CD paper-basket companion rather than a Phase 8 shadow-lane promotion, names OP_REFINED_K7 as the closest same-family shadow challenger, keeps KEE_K9 / SA_K9 / DMR_FALL_K7 as observation-only pockets, and says plainly that the broader selective-family secondary shadow read is replay-context rather than extra train-only proof",
        )
    )
    checks.append(
        require(
            "### Why `CD_CORE_K8` is in the primary basket but not the safest anchor" in text
            and "| Question | `OP_DURABLE_K7` | `CD_CORE_K8` | Practical read |" in text
            and "| 2024-2025 holdout sample | 115 races | 60 races | OP has the larger forward sample, so it is the safer single-rule anchor. |" in text
            and "| 2024/2025 split | -47.41% on 68, then +124.61% on 47 | +45.65% on 41, then +78.21% on 19 | CD is cleaner across both years, but on a meaningfully smaller sample. |" in text
            and "| Walk-forward selection | 7/10 folds | 1/10 folds | OP keeps winning the durability vote in train-only selection. |" in text
            and "| Deployment role now | `ANCHOR` | `PAPER` | Keep CD in the current paper basket, but do not let it displace OP as the safest current paper anchor yet. |" in text
            and "If you want the single safest current paper-trade start, use `op_anchor_rules.json` and let `OP_DURABLE_K7` carry the lane." in text
            and "If you want the current primary paper basket, use `phase7_current_paper_rules.json` and keep `CD_CORE_K8` alongside OP as the paper-worthy companion, not as proof that the anchor should flip." in text
            and "BEL still stays dormant until real Belmont forward races exist. Do **not** backfill it with BAQ." in text,
            "cd_companion_not_anchor_section",
            "paper-trade usage now carries one compact OP-vs-CD operator table that explains why CD_CORE_K8 is paper-worthy inside the primary basket without displacing OP_DURABLE_K7 as the safest current paper anchor",
        )
    )
    checks.append(
        require(
            "### Why `OP_REFINED_K7` stays in the shadow lane" in text
            and "| Question | `OP_DURABLE_K7` | `OP_REFINED_K7` | Practical read |" in text
            and "| 2024-2025 holdout sample | 115 races | 49 races | Durable still has the much larger forward sample. |" in text
            and "| 2024/2025 split | -47.41% on 68, then +124.61% on 47 | -25.47% on 33, then +210.02% on 16 | Refined has the prettier aggregate, but it still comes from a smaller, hotter 2025 burst after a losing 2024. |" in text
            and "| Walk-forward selection | 7/10 folds | 2/10 folds | Durable is still the rule the train-only process trusted most often. |" in text
            and "| Deployment role now | `ANCHOR` | `WATCH` | Keep refined in observation mode until it earns a meaningfully larger forward sample. |" in text
            and "If you want the safest current OP exposure, keep `OP_DURABLE_K7` as the active anchor." in text
            and "If you want to monitor the narrower same-family challenger, keep `OP_REFINED_K7` in `phase8_shadow_rules.json` and treat its signals as observation-only." in text
            and "Keep `KEE_K9`, `SA_K9`, and `DMR_FALL_K7` in that same shadow basket strictly as observation-only pockets; they are worth logging, not promoting." in text
            and "Do not promote refined on the strength of the aggregate `+51.43%` holdout alone; that number is still riding on just 49 forward races and a very hot 2025 slice." in text,
            "op_refined_shadow_only_section",
            "paper-trade usage now carries one compact OP-durable-vs-refined operator table that explains why OP_REFINED_K7 stays shadow-only despite the hotter aggregate holdout ROI, while also keeping the other Phase 8 shadow names in the worth-logging-but-not-promoting bucket",
        )
    )
    checks.append(
        require(
            "validate_paper_trade_operator_suite.py" in text
            and "out/status_validation/paper_trade_operator_suite/paper_trade_operator_suite_validation.md" in text
            and "Treat that suite as an operator-surface alignment/readiness sweep, not as new forward evidence by itself." in text,
            "operator_suite_route",
            "paper-trade usage still routes operator-surface edits to the paper-trade operator suite first, names its output report, and says that umbrella operator sweep is alignment/readiness rather than new forward evidence",
        )
    )
    checks.append(
        require(
            "which compact source-chain matrix summarizes scan -> recommend -> size -> log guardrails before drilling into direct validators" in text
            and "For a compact audit of the source chain, read `PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md` before drilling into individual scan / recommend / size / log validators." in text
            and f"Its markdown and JSON outputs summarize validator-output fingerprints, source/validator script fingerprints, matrix generator/validator fingerprints, {source_chain['total_fixture_scenarios']} fixture scenarios, and {source_chain['total_guardrail_checks']} guardrails, plus the direct live-scanner boundary contract for `valid_evidence_scope`, `evidence_boundary`, and `evidence_boundary_text` on status sidecars and scanner hit rows. The direct validator checks markdown/JSON fingerprint-table parity, validated matrix markdown/JSON artifact fingerprints, and that scanner-boundary contract for operational reproducibility/readiness only; they are not a live paper-trade ledger, not settlement-complete ROI, not a promotion signal, and not real-money profitability evidence." in text
            and "After that direct matrix is fresh, the parent rollups should preserve it too: `validate_paper_trade_operator_suite.py` embeds it as `auxiliary_source_chain_matrix`, confirms the matrix artifact fingerprints still match disk, and recomputes the matrix payload from current source-layer inputs before accepting reused child JSON; `validate_project_surfaces.py` verifies that embedded result rather than flattening the upstream chain into a generic operator-suite pass." in text
            and "Treat those parent passes as propagation/readiness checks only — not settled ROI, not promotion readiness, not live profitability, and not real-money evidence." in text
            and "- `paper_trade_source_chain_guardrails.py` — generate the compact scan -> recommend -> size -> log guardrail matrix from the four direct source-layer validator JSON reports, plus the direct live-scanner boundary contract" in text
            and f"- `PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md` / `PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json` — saved human/machine-readable source-chain matrix with validator JSON fingerprints, source/validator script fingerprints, matrix generator/validator fingerprints, {source_chain['total_fixture_scenarios']} fixture scenarios, and {source_chain['total_guardrail_checks']} guardrails, plus a source-matched live-scanner boundary contract for status sidecars and scanner hit rows; its direct validation report fingerprints the matrix markdown/JSON artifacts too, framed as operational reproducibility/readiness only rather than live evidence" in text
            and "- `validate_paper_trade_source_chain_guardrails.py` — direct validator for that source-chain matrix so the saved markdown/JSON outputs and live-scanner boundary contract stay source-matched before operators drill into individual scan, recommender, EV-sizing, or logger leaves" in text
            and "When the question is the whole upstream scan -> recommend -> size -> log guardrail inventory rather than one leaf, read the compact matrix and run:" in text
            and "python3 validate_paper_trade_source_chain_guardrails.py" in text
            and "out/status_validation/paper_trade_source_chain_guardrails/paper_trade_source_chain_guardrails_validation.md" in text
            and "a green result is operational reproducibility/readiness only — not settled ROI, not promotion readiness, not live profitability, and not real-money evidence" in text
            and f"- `validate_paper_trade_source_chain_guardrails.py`: the compact matrix still source-matches the scan, recommender, EV-sizing, and logger validator JSON reports plus source/validator scripts and matrix generator/validator tooling, preserves {source_chain['total_guardrail_checks']} guardrails across {source_chain['total_fixture_scenarios']} fixture scenarios, pins the direct live-scanner source-boundary contract for status sidecars and scanner hit rows as paper-alert metadata only, renders markdown fingerprint tables exactly from the JSON sidecar, fingerprints the validated matrix markdown/JSON artifacts, and keeps the operational reproducibility/readiness-only boundary explicit before operators drill into individual leaves" in text,
            "source_chain_matrix_route_documented",
            "paper-trade usage now exposes the compact source-chain guardrail matrix, its generator, its markdown/JSON outputs, its direct validator/report path, and the boundary that this is operational reproducibility/readiness rather than live ROI or promotion evidence",
        )
    )
    checks.append(
        require(
            f"{source_chain['total_fixture_scenarios']} fixture scenarios, and {source_chain['total_guardrail_checks']} guardrails" in text
            and f"preserves {source_chain['total_guardrail_checks']} guardrails across {source_chain['total_fixture_scenarios']} fixture scenarios" in text
            and "24 guardrails across 43 fixture scenarios" not in text
            and "43 fixture scenarios, and 24 guardrails" not in text,
            "source_chain_guardrail_count_matches_matrix_json",
            "paper-trade usage now reads the source-chain matrix count from PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json and fails if the runbook drifts back to stale 24-guardrail wording",
        )
    )
    checks.append(
        require(
            "- `paper_trade_now.py` — collapse the latest daily run into one best operator action plus preserved primary/shadow recent-run context and lifted lane why-now lines behind it, sourced from the saved lane next-step surfaces, with matched text / markdown / JSON top-card outputs, missing scan-output artifacts, missing/empty/unreadable primary pipeline/scanner artifacts, plus pipeline-recorded empty/unreadable scanner-status states surfaced as distinct refresh actions, and on stale cards say plainly that downstream lane context, counts, and quick reads are inherited snapshot state rather than current-day state" in text
            and "- `validate_current_hierarchy_language.py` — direct validator for current live hierarchy wording across right-now / daily-summary / front-door surfaces, including `live_hierarchy`, `primary_companion`, and legacy compatibility-only `primary_shadow` keys, so `CD_CORE_K8` stays the primary OP/CD paper-basket companion and `OP_REFINED_K7` stays shadow/watch rather than promotion evidence" in text,
            "paper_trade_now_inventory_uses_stronger_context_why_wording",
            "paper-trade usage now describes `paper_trade_now.py` as carrying matched text / markdown / JSON top-card outputs, preserved primary/shadow recent-run context plus lifted lane why-now lines, distinct missing scan-output, missing/empty/unreadable primary sidecar, and pipeline-recorded scanner-status refresh actions, and, on stale cards, an explicit inherited-snapshot note instead of leaving stale lane detail to read like current-day state; it also names the current-hierarchy validator as the direct route for live hierarchy wording and structured-key edits",
        )
    )
    checks.append(
        require(
            "- `refresh_live_paper_trade_surfaces.py` — rebuild saved per-run operator surfaces, saved `preflight_note` text/JSON, plus top-level `OPS_HISTORY` / matched `PAPER_TRADE_NOW` text / markdown / JSON artifacts after source-layer render changes, with preserved primary/shadow recent-run context plus lane why-now lines carried forward into rebuilt right-now surfaces from current lane artifacts and missing scan-output latest-run context preserved in rebuilt per-run next-steps / lane summaries / daily summaries; under `--latest-only`, that rebuild scope stays confined to the newest copied run's preflight, lane, and daily-summary surfaces, and under `--skip-top-level` it leaves `OPS_HISTORY` / `PAPER_TRADE_NOW` untouched while still rerendering those per-run surfaces against the existing top-level cards, while helper stdout says whether optional `--as-of-date` freshness pinning was applied to rebuilt top-level freshness or ignored because top-level outputs were skipped" in text
            and "- `validate_refresh_live_paper_trade_surfaces.py` — build and check direct fixture cases for the saved-live refresh helper so stale per-run operator surfaces, saved `preflight_note` text/JSON, plus temp-routed `OPS_HISTORY` / matched `PAPER_TRADE_NOW` text / markdown / JSON rebuild cleanly from the current generators, refreshed `PAPER_TRADE_NOW.json` matches the source-layer right-now payload while the text / markdown cards keep the full routed recommendation-lane quick-reads bundle plus preserved primary/shadow recent-run context and lane why-now lines, preserves the explicit stale-snapshot note when the rebuilt top card is still stale, refreshed `daily_summary.txt` inherits the routed top-card focus/timing/freshness/ops snapshot from those refreshed top-level outputs while keeping preserved primary/shadow recent-run context lines, proves missing scan-output artifact context survives saved-live rebuilds, proves declared scanner sidecars still beat stale default scanner filenames during saved-live rebuilds, `--latest-only` stays scoped to the newest copied run's preflight, lane, and daily-summary surfaces, `--skip-top-level` leaves top-level outputs untouched while still rebuilding the per-run preflight/lane/daily layer against those existing top-level cards, and helper stdout stays honest about whether optional `--as-of-date` freshness pinning was applied or ignored because top-level refresh was skipped" in text,
            "refresh_helper_inventory_documented",
            "paper-trade usage now lists both the saved-live refresh helper and its direct validator in the operator tooling inventory, including the stronger refreshed PAPER_TRADE_NOW text/markdown/JSON bundle contract and JSON source-layer parity check, the stale-snapshot carry-through on rebuilt stale cards, and the routed top-card snapshot inheritance for rebuilt daily summaries",
        )
    )
    checks.append(
        require(
            "- says explicitly in its own success output that this is a saved-surface rerender from existing artifacts, **not** new paper-trade outcomes or new forward evidence" in text,
            "refresh_helper_not_evidence_note_documented",
            "paper-trade usage now says the saved-live refresh helper announces that it rerenders existing artifacts rather than creating new forward evidence",
        )
    )
    checks.append(
        require(
            "- together with `validate_run_daily_portfolio_observation.py`, this is one of the two leaf source-of-truth wrapper reports; broader operator/project sweeps should preserve their inherited wrapper-guardrail inventories rather than flattening them into one umbrella pass count" in text
            and "- when the question is specifically wrapper rebuild/orchestration, read `validate_refresh_live_paper_trade_surfaces.py` and `validate_run_daily_portfolio_observation.py` as the leaf source-of-truth reports; the broader operator-suite and project-sweep passes are supposed to preserve those inherited wrapper-guardrail inventories rather than flatten them into one umbrella green light" in text,
            "wrapper_leaf_guardrail_route_documented",
            "paper-trade usage now says plainly that the refresh-helper and daily-wrapper validators are the leaf source-of-truth wrapper reports and that broader operator/project sweeps should preserve rather than flatten their inherited guardrail inventories",
        )
    )
    checks.append(
        require(
            "- accepts `--as-of-date YYYY-MM-DD` when you need the rebuilt top-level `PAPER_TRADE_NOW` freshness banner pinned to a specific calendar reference during validation or reproducible rerenders" in text
            and "- says explicitly in its own success output whether that `--as-of-date` pin was applied to rebuilt top-level `PAPER_TRADE_NOW` freshness or ignored because top-level outputs were skipped" in text,
            "refresh_helper_as_of_date_documented",
            "paper-trade usage now documents the refresh helper's explicit --as-of-date option and says its stdout reports whether that freshness pin was actually applied or ignored because top-level outputs were skipped",
        )
    )
    checks.append(
        require(
            "- `VALIDATION_QUICKSTART.md` — validated runbook for which validator to run after which kind of change, including the broader operator-suite route, the paper-trade suite versus the top-level project sweep, the source-chain matrix plus direct source-layer routes, the parent-rollup reuse shortcut guardrails, documented output paths, and the dated-report / legacy-alias policy" in text
            and "- `validate_validation_quickstart.py` — consistency check for that runbook so the documented validation ladder, the broader operator-suite route, direct source-layer routes, reuse guardrails, documented output paths, and dated-report / legacy-alias guidance do not drift quietly" in text,
            "quickstart_alias_policy_documented",
            "paper-trade usage now describes the quickstart as carrying the broader operator-suite route, source-chain matrix plus direct source-layer routes, parent-rollup reuse shortcut guardrails, documented output paths, and the dated-report / legacy-alias policy, and says the quickstart validator pins that wider contract too",
        )
    )
    checks.append(
        require(
            "WORKING_STATUS_REPORT_2026-04-15.md" in text
            and "validate_working_status_report.py" in text,
            "working_status_route_present",
            "paper-trade usage now names the dated working-status note and its direct validator when the question is production basket versus demo lane",
        )
    )
    checks.append(
        require(
            "That is the smallest honest check when the question is whether a behavior belongs to the real paper basket or the separate live/demo lane described in `WORKING_STATUS_REPORT_2026-04-15.md`." in text,
            "working_status_route_documented",
            "paper-trade usage now explains when to use the direct working-status validator instead of jumping straight to the umbrella project sweep",
        )
    )
    checks.append(
        require(
            "If the change touched shareable wording, presentation drift, the dated-report trust path, or whether the narrative report sweep still preserves the README-inherited wrapper-leaf source-of-truth note instead of flattening it away, run:" in text
            and "python3 validate_report_surfaces.py" in text,
            "report_surfaces_route_present",
            "paper-trade usage now names the direct report-surfaces validator when the real question is shareable wording or report-trust-path drift rather than operator behavior",
        )
    )
    checks.append(
        require(
            "out/status_validation/report_surfaces/report_surfaces_validation.md" in text
            and "That is the smallest honest check when the question is README, the long-form report, the working-status note, the presentation outline, or the shareable HTML report layer rather than the operator workflow itself." in text,
            "report_surfaces_route_documented",
            "paper-trade usage now names the saved report-surfaces validation output and explains when to read that direct narrative/report-facing route instead of stepping straight to the broad project sweep",
        )
    )
    checks.append(
        require(
            "If the change touched both paper-trade operations and the research / report-facing layer, step up to:" in text
            and "python3 validate_project_surfaces.py" in text
            and "That top-level sweep is the best cross-layer alignment answer for a broad change, including the direct current-hierarchy child validator, not new forward evidence by itself." in text,
            "project_sweep_route_present",
            "paper-trade usage still points mixed ops + research/report changes to the top-level project sweep and now says that broad answer includes the direct current-hierarchy child validator while remaining alignment rather than new forward evidence",
        )
    )
    checks.append(
        require(
            "python3 validate_paper_trade_status_summary.py" in text
            and "python3 validate_paper_trade_settlement_sync.py" in text
            and "python3 validate_paper_trade_settlement_helper.py" in text
            and "python3 validate_paper_trade_settlement_audit.py" in text
            and "python3 validate_paper_trade_next_steps.py" in text
            and "python3 validate_current_hierarchy_language.py" in text
            and "python3 validate_scanner_sidecar_resolution_contract.py" in text,
            "missing_operator_validators_restored",
            "paper-trade usage now lists the base-status, scanner-sidecar path-resolution, settlement-sync, settlement-helper, settlement-audit, next-steps, and current-hierarchy validators in the individual operator-validator block",
        )
    )
    checks.append(
        require(
            "- `validate_paper_trade_status_summary.py`: the one-line base lane summary still keeps bet-ready, clean-empty, partial-cache, max-races-limited, scanner-only alert, cache-only-miss, missing-scan-output, generic scanner-failure, API-access / HTTP 403 action-recheck route preservation, stale-cache fallback count/kind/error visibility, empty/unreadable scanner sidecars, pipeline-recorded empty/unreadable scanner-status states when a copied surface lacks the physical scanner sidecar, wrapper-only required-pipeline missing/empty/unreadable sidecars, explicit recommender/logger failure lines with stage + error type + detail, and signals-without-bet states distinct across both text and JSON paths" in text,
            "status_summary_contract_documented",
            "paper-trade usage now documents the direct status-summary validator contract, including API-access / HTTP 403 action-recheck route preservation, stale-cache fallback metadata, empty/unreadable scanner sidecars, pipeline-recorded scanner-status state preservation, wrapper-only required-pipeline sidecar issues, and the saved human-facing recommender/logger failure detail line",
        )
    )
    checks.append(
        require(
            "- `validate_scanner_sidecar_resolution_contract.py`: the focused path-resolution contract still proves a pipeline-declared `scanner_status_path` stays authoritative across status summary, next steps, `PAPER_TRADE_NOW`, `OPS_HISTORY`, and saved-live refresh when a stale default `live_scan.status.json` exists; it also proves declared API-access sidecars preserve HTTP 403 action/recheck fields over stale clean defaults, rejects malformed scorecard gates before copied-sidecar fixture/report artifacts, and its saved report carries the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite as routing-fixture boundary metadata, not paper-review or real-money evidence" in text,
            "scanner_sidecar_resolution_contract_documented",
            "paper-trade usage now documents the focused scanner-sidecar path-resolution validator, including stale-default masking, declared API-access action/recheck preservation across the operator surfaces, malformed-scorecard no-artifact rejection, and the scorecard-sourced 30/20/100 plus no-BAQ-as-BEL gate boundary",
        )
    )
    checks.append(
        require(
            "If you changed the saved-live refresh helper itself, run this narrower check too:" in text
            and "python3 validate_refresh_live_paper_trade_surfaces.py" in text,
            "refresh_helper_direct_validator_note",
            "paper-trade usage now tells readers to run the narrow refresh-helper validator when that helper changes",
        )
    )
    checks.append(
        require(
            "Three shortcuts matter enough to call out separately:" in text
            and "run `python3 validate_paper_trade_settlement_sync.py` when the question is whether live `signal_key` rows still turn into one reproducible open settlement queue" in text
            and "explicit cleanup counts for blank and duplicate signal-key rows skipped, blank settlement-key rows dropped, and orphan settlement rows dropped" in text
            and "out/status_validation/paper_trade_settlement_sync/paper_trade_settlement_sync_validation.md" in text,
            "settlement_sync_route_documented",
            "paper-trade usage now calls out the direct settlement-sync validator as the smallest honest check for the template-sync queue surface, names its saved report path, and explains the blank/duplicate signal-key plus blank-settlement-key plus orphan cleanup count line",
        )
    )
    checks.append(
        require(
            "run `python3 validate_paper_trade_settlement_helper.py` when the question is whether the human settlement workflow still shows open rows separately from settled-row ROI gaps, truncates long queues honestly, updates exactly one `signal_key` without hand-editing CSV, rejects duplicate `signal_key` matches and zero/non-positive `--actual-cost` values before mutation" in text
            and "run `python3 validate_paper_trade_settlement_audit.py` when the question is whether the ledger-completeness / ROI-coverage audit keeps blank signal-key versus blank settlement-key repair labels, structural signal/settlement repairs, matched-key metadata mismatches, duplicate custom lane-name rejection before output artifacts" in text
            and "structural signal/settlement repairs, matched-key metadata mismatches, duplicate custom lane-name rejection before output artifacts, ROI-complete row counts, primary/shadow sample gates, shadow per-rule review floors, and the no-new-forward-evidence boundary separate" in text
            and "out/status_validation/paper_trade_settlement_audit/paper_trade_settlement_audit_validation.md" in text
            and "Omit --actual-cost when the row's expected_cost is the right flat-ticket cost." in text
            and "row-specific `settle` command template" in text
            and "template placeholders must be replaced only after actual result/payout evidence exists" in text
            and "reports `actual_cost_source` in the confirmation without adding a cost-source column to the persisted settlement ledger" in text
            and "actual_cost_source=missing_cost_source" in text
            and "rejects explicit zero/non-positive `--actual-cost` values before mutation" in text
            and "reports the settlement cost source" in text
            and "infers `actual_cost` from positive `expected_cost` when actual cost is omitted" in text
            and "keeps missing/malformed/non-positive cost sources blank" in text
            and "out/status_validation/paper_trade_settlement_helper/paper_trade_settlement_helper_validation.md" in text,
            "settlement_helper_route_documented",
            "paper-trade usage now calls out the direct settlement-helper validator as the smallest honest check for the manual settlement-entry surface, and the direct settlement-audit validator as the smallest honest check for ledger-completeness / ROI-coverage audit wording, including blank signal-key versus blank settlement-key repair labels and the saved report path",
        )
    )
    checks.append(
        require(
            "- `validate_paper_trade_settlement_audit.py`: the ledger-completeness / ROI-coverage audit keeps structural signal/settlement repairs, matched-key metadata mismatches, blank signal-key rows in signal ledgers, blank settlement-key rows in settlement ledgers, missing/placeholder/malformed `settled_ts` gaps, duplicate custom lane-name rejection before output artifacts, ROI-complete row counts, primary/shadow sample gates, shadow per-rule review floors, and no-new-forward-evidence boundaries distinct across markdown and JSON outputs" in text,
            "settlement_audit_contract_documented",
            "paper-trade usage now documents the direct settlement-audit validator contract, including structural repairs, separated blank signal-key versus blank settlement-key repair labels, ROI-complete row counts, lane gates, shadow review floors, and no-new-forward-evidence boundaries",
        )
    )
    checks.append(
        require(
            "run `python3 validate_run_daily_portfolio_observation.py` when the question is whether the real shell wrapper still degrades safely through helper failures and placeholder fallbacks while keeping preflight, per-lane summaries, rolling ops history, `PAPER_TRADE_NOW`, and `daily_summary.txt` stitched together with saved primary/shadow recent-run context plus why-now lines preserved when wrapper fallbacks trigger" in text
            and "out/status_validation/run_daily_portfolio_observation/run_daily_portfolio_observation_validation.md" in text,
            "daily_wrapper_route_documented",
            "paper-trade usage now calls out the direct daily-wrapper validator as the smallest honest check for end-to-end helper-failure and placeholder-fallback orchestration and names its saved report path",
        )
    )
    checks.append(
        require(
            "- `validate_paper_trade_next_steps.py`: the per-lane next-step helper still preserves settlement-first, refresh-artifacts with distinct missing scan-output plus missing/empty/unreadable sidecar wording plus pipeline-recorded scanner-status states, API-access stale-cache fallback routing, rerun-live, limited-cache, explicit recommender/logger pipeline-failure recovery, early-observation, collecting-sample, and decision-grade transitions" in text,
            "next_steps_contract_documented",
            "paper-trade usage now documents the direct next-steps validator contract, including distinct missing/empty/unreadable sidecar wording, pipeline-recorded scanner-status preservation, API-access stale-cache fallback routing, and explicit recommender/logger pipeline-failure recovery",
        )
    )
    checks.append(
        require(
            "- combines the latest daily run, both lane next-step payloads, preserved primary/shadow recent-run context plus lane why-now lines, and rolling ops-history streak context" in text
            and "- on stale cards, says explicitly that the downstream lane context, counts, and quick reads are inherited snapshot context from the latest saved run rather than current-day state" in text
            and "- points its quick-read list at the lane behind the actual recommendation, and keeps the full routed recommendation-lane bundle (`summary.txt`, `next_steps.md`, `lane_monitor.md`, routed `daily_summary.txt`, routed `OPS_HISTORY.md`) plus the explicit live hierarchy block and preserved primary/shadow recent-run context plus lane why-now lines intact before deeper digging, without letting stale inherited lane detail read like current-day state" in text,
            "right_now_quick_read_bundle_documented",
            "paper-trade usage now documents that the right-now helper preserves the full routed recommendation-lane quick-reads bundle, the explicit live hierarchy block, preserved primary/shadow recent-run context lines, and the stale-card inherited-snapshot warning instead of only one representative link",
        )
    )
    checks.append(
        require(
            "- keeps the full routed quick-jump bundle, routed top-card focus/timing/freshness/ops snapshot, explicit current live hierarchy block, preserved primary/shadow recent-run context lines, explicit primary/shadow next-step state lines plus first-read and broader-review readiness lines, preflight note, lane sections, and artifacts-root line in one reproducible generator" in text
            and "- makes shadow review-readiness visible from the combined summary itself while keeping the Phase 7 primary lane as the live deployment anchor" in text,
            "daily_summary_helper_bundle_documented",
            "paper-trade usage now documents the daily-summary helper as preserving the full routed quick-jump bundle plus the routed top-card snapshot, preserved primary/shadow recent-run context lines, explicit next-step state lines, and first-read vs broader-review readiness lines, and says shadow review-readiness is visible without implying live promotion",
        )
    )
    checks.append(
        require(
            "If you changed this paper-trade operations note itself, run `python3 validate_paper_trade_usage.py` too." in text,
            "self_validator_note",
            "paper-trade usage now tells readers how to validate this operator runbook when its wording changes",
        )
    )
    checks.append(
        require(
            "If you changed that runbook itself, its broader operator-suite or source-chain matrix / direct source-layer route guidance, its documented output paths, or the dated-report / legacy-alias guidance it carries, run `python3 validate_validation_quickstart.py` too." in text,
            "quickstart_revalidation_note",
            "paper-trade usage now tells readers to re-run the quickstart validator when the quickstart route map, documented output paths, or dated-report / legacy-alias guidance changes",
        )
    )
    checks.append(
        require(
            "If the underlying child validator outputs are already fresh and the edit only touched a parent rollup or top-level wording, the smaller honest reruns are:" in text
            and "python3 validate_decision_cards_suite.py --reuse-existing-child-json" in text
            and "python3 validate_frozen_evidence_chain.py --reuse-existing-child-json" in text
            and "python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json" in text
            and "python3 validate_report_surfaces.py --reuse-existing-child-json" in text
            and "python3 validate_project_surfaces.py --reuse-existing-child-json" in text
            and "That shortcut is only honest when the child validator artifacts already match the current code and docs state." in text,
            "reuse_shortcut_documented",
            "paper-trade usage now documents the parent-rollup artifact-reuse shortcut for parent-only or top-level wording edits, with the guardrail that child validator artifacts already need to match the current code and docs state",
        )
    )
    checks.append(
        require(
            "`PAPER_TRADE_NOW.md`" in text
            and "`OPS_HISTORY.md`" in text
            and "`preflight_note.txt`" in text
            and "`preflight_note.json`" in text
            and "`daily_summary.txt`" in text
            and "It still includes dormant BEL and is not the clearest current-paper entrypoint." in text
            and "It still includes dormant BEL and is not the clearest live-paper entrypoint." not in text
            and "runs `phase7_current_paper_rules.json` first as the **primary** current paper basket (`OP_DURABLE_K7` anchor first, with `CD_CORE_K8` as the primary OP/CD paper-basket companion inside the primary basket, not a Phase 8 shadow-lane promotion)" in text
            and "runs `phase8_shadow_rules.json` second as the **shadow** watch-list basket (`OP_REFINED_K7` stays in observation mode as the smaller same-family challenger, while `KEE_K9`, `SA_K9`, and `DMR_FALL_K7` stay observation-only pockets, with broader selective-family secondary lines treated as replay context on walk-forward test years rather than extra train-only proof)" in text
            and "makes that combined `daily_summary.txt` surface the explicit `Primary next-step state:` / `Shadow next-step state:` lines plus `Primary readiness:` / `Shadow readiness:` progress, so a shadow `DECISION-GRADE REVIEW` read is visible immediately without being mistaken for a paper-lane promotion" in text
            and "refreshes `PAPER_TRADE_NOW.md` / `PAPER_TRADE_NOW.txt` / `PAPER_TRADE_NOW.json` after each run, so there is one top-level answer to \"what do I do right now?\" plus a matched machine-readable payload, and stale cards now say plainly that downstream lane context, counts, and quick reads are inherited from the latest saved run rather than current-day state" in text
            and "rebuilds `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` after the right-now card and settlement audit refresh; if that bridge helper cannot publish a source-backed bridge, the wrapper leaves an explicit no-forward-performance / no-real-money placeholder instead of silently preserving stale current-evidence wording, and the direct wrapper validator checks source-backed recommendation-context/open-row separation before those outputs are used in Cole-facing wording" in text
            and "`python3 refresh_live_paper_trade_surfaces.py` can rebuild the saved per-run summaries, saved `preflight_note` text/JSON, plus `OPS_HISTORY` and matched `PAPER_TRADE_NOW` text / markdown / JSON from the current generators before validation, preserving missing scan-output latest-run context in rebuilt per-run surfaces and rerendering daily summaries against those refreshed top-level surfaces so the routed top-card snapshot lines stay source-matched while keeping the rebuilt stale-snapshot note aligned with the refreshed top card when the saved run is still old; under `--latest-only`, that rebuild stays confined to the newest copied run's preflight, lane, and daily-summary surfaces; under `--skip-top-level`, it leaves `OPS_HISTORY` / `PAPER_TRADE_NOW` untouched but still rerenders those per-run surfaces against the existing top-level cards, and the helper says explicitly when `--as-of-date` was ignored because of that skip mode" in text
            and "can route those top-level outputs somewhere else during validation, so the helper itself can be fixture-checked without mutating the live operator surfaces" in text
            and "with preserved primary/shadow recent-run context plus lane why-now lines carried forward into rebuilt right-now surfaces from current lane artifacts" in text,
            "daily_surface_inventory",
            "paper-trade usage still names the main daily operator surfaces Cole actually reads after running the wrapper, makes the primary paper basket plus separate shadow/watch hierarchy explicit, and now says the top-card text/markdown/JSON bundle, wrapper-generated current-evidence bridge/placeholder path, and saved-live rerender path preserve stale/current-source honesty while keeping a matched machine-readable payload",
        )
    )
    checks.append(
        require(
            "Do **not** substitute the top-level `out/paper_trade_preflight_note.txt` for the run-root preflight note above in daily reads." in text
            and "That top-level file is a standalone manual preflight-helper cache / scratch output unless `paper_trade_preflight_note.py` is rerun directly" in text
            and "the validated operator path is the wrapper-generated `out/daily_portfolio_runs/YYYY-MM-DD/preflight_note.txt` / `.json` pair" in text,
            "top_level_preflight_scratch_cache_boundary",
            "paper-trade usage now separates the stale-prone top-level manual preflight-helper cache from the wrapper-generated run-root preflight note that should drive daily operator reads",
        )
    )
    checks.append(
        require(
            "`observation_result` (`scanner_failed_empty_run`, `partial_cache_empty_run`, `limited_coverage_empty_run`, `limited_coverage_with_activity`, `clean_empty_run`, `bets_ready`, `signals_logged_no_bet`)" in text
            and "`scanner_status_path` when the lane's real scanner-status sidecar is not the default `live_scan.status.json`" in text
            and "treat that declared sidecar as the run's scanner source of truth whenever it exists, even if an older default `live_scan.status.json` is still sitting in the lane folder" in text
            and "relative paths are checked as lane-local first, run-root-relative second, and project-relative third" in text
            and "Examples now covered by direct fixtures include lane-local `renamed_live_scan_lane_local.status.json`, run-root-relative `phase8_shadow/renamed_live_scan_run_root.status.json`, project-relative `out/status_validation/.../project_relative_scanners/phase7_project_relative_live_scan.status.json`, and a stale-default masking case" in text
            and "those relocated sidecars should stay connected to `summary.txt`, `next_steps.md`, `PAPER_TRADE_NOW.md`, `OPS_HISTORY.md`, and the saved-live refresh wrapper" in text
            and "The narrow cross-surface contract is `python3 validate_scanner_sidecar_resolution_contract.py`; its report also proves that a declared API-access sidecar keeps `HTTP 403`, `refresh_daily_wrapper_before_evidence_read`, and `./run_daily_portfolio_observation.sh` visible instead of letting a stale default clean sidecar turn the day into a quiet read." in text
            and "It rejects malformed scorecard gates before copied-sidecar fixture/report artifacts, then carries the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite so copied-sidecar routing fixtures stay boundary metadata rather than paper-review, promotion, profitability, bankroll, or real-money evidence." in text,
            "pipeline_status_contract",
            "paper-trade usage still documents the machine-readable observation-result states behind the honest empty-day messaging and now documents the shared scanner_status_path relocated-sidecar resolution contract for lane-local, run-root-relative, project-relative, stale-default-masking, and declared API-access action/recheck cases, plus the direct path-resolution validator's scorecard gate boundary",
        )
    )
    checks.append(
        require(
            "How to read a quiet day versus a broken day:" in text
            and "a true quiet day is either `NO TARGETS`" in text
            and "only call it a true no-target day when the saved run-root preflight note (`preflight_note.txt`, or `preflight_note.json` if the text surface is missing or blank) explicitly says no primary paper-basket target tracks (OP / CD) are racing" in text
            and "do not use the top-level `out/paper_trade_preflight_note.txt` scratch cache as that proof" in text
            and "`cache-only-miss`, `partial-cache`, and `max-races-limited` reads are **not** quiet-day reads" in text
            and "green `validate_cache_only_messaging.py` or `validate_partial_cache_messaging.py` passes are cache-edge routing / reproducibility metadata only" in text
            and "they prove the operator surfaces route incomplete market-data views toward refresh or rerun, not that a quiet day, current-day scanner result, settled ROI, live profitability, promotion readiness, or real-money readiness was observed" in text
            and "explicit `CHECK PIPELINE FAILURE`, `recommender failure`, and `logger failure` reads are operational failure states" in text
            and "`scanner-failure`, missing scan-output artifacts, `preflight-helper-failure`, `right-now-helper-failure`, missing/empty/unreadable artifact states, and `unreadable-calendar` are operational issue states" in text
            and "when that distinction is in doubt, check the saved run-root preflight note (`preflight_note.txt`, or `preflight_note.json` if the text surface is missing or blank), `OPS_HISTORY.md`, and `PAPER_TRADE_NOW.md` together before drawing a conclusion" in text,
            "quiet_vs_broken_day_contract",
            "paper-trade usage now gives one compact operator rule for separating real stand-down days from incomplete-data states, explicitly frames green cache-only/partial-cache validators as routing/reproducibility metadata rather than scanner/ROI/profitability/promotion/real-money evidence, and preserves recommender/logger pipeline-failure plus helper-failure states",
        )
    )
    checks.append(
        require(
            "Pipeline status (`paper_trade_pipeline_status.json`) adds wrapper context such as:" in text
            and "explicit `result == pipeline_error` plus `stage` (`recommender` or `logger`) and error detail when the lane failed after scanning" in text
            and "That human-readable line is now supposed to preserve the concrete recommender/logger failure context too, and the wrapper can opt into explicit pipeline-sidecar issue wording, so operators do not have to open the JSON sidecar just to see what broke." in text
            and "This is the fastest way to tell the difference between a real no-signal day, a partial offline replay, a capped `--max-races` read, and an actual recommender/logger pipeline failure." in text
            and "the scanner/status surfaces also carry `unattempted_target_race_count` plus `full_target_coverage_min_races`" in text
            and "raise `--max-races` to at least that full-coverage floor or rerun before calling the day a true zero-hit read" in text,
            "pipeline_failure_sidecar_contract_documented",
            "paper-trade usage now documents that both the machine-readable sidecar and the saved human-facing summary line carry explicit recommender/logger failure detail, plus the wrapper-only pipeline-sidecar issue wording, capped-read coverage-gap counts, and full-coverage max-races floor",
        )
    )
    checks.append(
        require(
            "- `validate_paper_trade_now.py` — build and check fixture cases for the right-now launcher without touching live ledgers, including missing scan-output artifact refresh actions, missing/empty/unreadable primary pipeline/scanner artifact refresh actions, plus pipeline-recorded empty/unreadable scanner-status refresh actions, pinning the saved and shell-facing JSON, text, and markdown outputs to fresh source-layer renders while proving the full routed recommendation-lane quick-reads bundle, explicit live hierarchy block, preserved primary/shadow recent-run context plus lane why-now lines, and the explicit stale-snapshot note that keeps inherited lane detail from masquerading as current-day state" in text
            and "- `validate_paper_trade_daily_summary.py`: the combined `daily_summary.txt` keeps the full routed quick-jump bundle, routed top-card focus/timing/freshness/ops snapshot, explicit current live hierarchy block, preserved primary/shadow recent-run context lines, explicit primary/shadow next-step state lines plus lifted no-overpromotion decision-gate snapshot lines, first-read and broader-review readiness lines, preflight note section, lane sections, artifacts-root line, explicit recommender/logger failure context, and pipeline-recorded empty/unreadable scanner-status issue lines intact across empty, settlement-pending, active-target, scanner-status-issue, missing-lane-summary, and missing-preflight fixture days, and the saved text still matches a fresh rebuild from `paper_trade_daily_summary.py`" in text
            and "- `validate_paper_trade_lane_summary.py` — build and check fixture cases for the expanded per-lane summary surface, including the full routed quick-files bundle, lifted no-overpromotion decision-gate visibility, missing scan-output fallback context, pipeline-recorded empty/unreadable scanner-status base headlines when copied lane surfaces lack the physical scanner sidecar, missing-base and missing-detail placeholders, plus an exact rendered-surface rebuild check" in text
            and "- `validate_cache_only_messaging.py` — build and check both no-target and active-target cache-only-miss fixtures across status summary, next steps, ops history, and the right-now card while proving the full routed recommendation-lane quick-reads bundle plus preserved primary/shadow recent-run context lines" in text
            and "- `validate_partial_cache_messaging.py` — build and check active-target partial-cache fixtures so limited offline coverage stays distinct from both cache misses and clean-empty scans while proving the full routed recommendation-lane quick-reads bundle plus preserved primary/shadow recent-run context lines" in text
            and "- `validate_current_hierarchy_language.py`: the current hierarchy language route keeps `OP_DURABLE_K7` as anchor, `CD_CORE_K8` as primary OP/CD paper-basket companion, and `OP_REFINED_K7` as shadow/watch across the top-card, daily-summary, quickstart, and main-status surfaces, preserves `live_hierarchy.primary_companion` while treating `primary_shadow` as legacy compatibility only, and keeps hierarchy metadata separate from ROI, promotion, live-profitability, and real-money evidence" in text,
            "expanded_navigation_bundle_contracts_documented",
            "paper-trade usage now pins the strengthened routed navigation-bundle, routed top-card snapshot, preserved primary/shadow recent-run context wording, stale-card inherited-snapshot note, and current-hierarchy guardrail route for the right-now, daily-summary, lane-summary, cache-only, partial-cache, and hierarchy-language validator inventory entries",
        )
    )
    checks.append(
        require_paths_exist(
            [
                BASE / "op_anchor_rules.json",
                BASE / "phase7_current_paper_rules.json",
                BASE / "phase8_shadow_rules.json",
                BASE / "run_daily_portfolio_observation.sh",
                BASE / "refresh_live_paper_trade_surfaces.py",
                BASE / "validate_refresh_live_paper_trade_surfaces.py",
                BASE / "PAPER_TRADE_NOW.md",
                BASE / "PAPER_TRADE_NOW.json",
                BASE / "OPS_HISTORY.md",
                BASE / "paper_trade_source_chain_guardrails.py",
                BASE / "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md",
                BASE / "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json",
                BASE / "OP_ANCHOR_METHOD_COMPARISON.md",
                BASE / "op_anchor_method_comparison.json",
                BASE / "CROSS_FAMILY_DECISION.md",
                BASE / "cross_family_decision_card.csv",
                BASE / "current_evidence_summary.py",
                BASE / "CURRENT_EVIDENCE_SUMMARY.md",
                BASE / "current_evidence_summary.json",
                BASE / "forward_evidence_scorecard.json",
                BASE / "SCORECARD_RANKING_CONTRACT_AUDIT.md",
                BASE / "scorecard_ranking_contract_audit.json",
                BASE / "VALIDATION_QUICKSTART.md",
                BASE / "WORKING_STATUS_REPORT_2026-04-15.md",
            ],
            "named_operator_artifacts_exist",
            "the core operator artifacts and refresh helpers named directly in PAPER_TRADE_USAGE currently exist on disk",
        )
    )
    checks.append(
        require_paths_exist(
            [
                BASE / "validate_decision_cards_suite.py",
                BASE / "validate_forward_evidence_scorecard.py",
                BASE / "validate_frozen_evidence_chain.py",
                BASE / "validate_op_anchor_method_comparison.py",
                BASE / "validate_cross_family_decision.py",
                BASE / "validate_current_evidence_summary.py",
                BASE / "validate_scorecard_ranking_contract_audit.py",
                BASE / "validate_ab_downstream_comparison.py",
                BASE / "validate_compare_recommender_scope_paths.py",
                BASE / "validate_paper_trade_operator_suite.py",
                BASE / "validate_refresh_live_paper_trade_surfaces.py",
                BASE / "validate_paper_trade_now.py",
                BASE / "validate_current_hierarchy_language.py",
                BASE / "validate_run_daily_portfolio_observation.py",
                BASE / "validate_paper_trade_source_chain_guardrails.py",
                BASE / "validate_paper_trade_pipeline.py",
                BASE / "validate_paper_trade_recommender.py",
                BASE / "validate_ev_ticket_engine.py",
                BASE / "validate_paper_trade_logger.py",
                BASE / "validate_paper_trade_preflight_note.py",
                BASE / "validate_paper_trade_status_summary.py",
                BASE / "validate_paper_trade_settlement_sync.py",
                BASE / "validate_paper_trade_settlement_helper.py",
                BASE / "validate_paper_trade_next_steps.py",
                BASE / "validate_paper_trade_forward_check.py",
                BASE / "validate_paper_trade_lane_monitor.py",
                BASE / "validate_paper_trade_daily_summary.py",
                BASE / "validate_paper_trade_lane_summary.py",
                BASE / "validate_paper_trade_ops_history.py",
                BASE / "validate_daily_artifact_guide.py",
                BASE / "validate_paper_trade_usage.py",
                BASE / "validate_cole_status_and_plan.py",
                BASE / "validate_readme_current_status.py",
                BASE / "validate_cole_full_report.py",
                BASE / "validate_working_status_report.py",
                BASE / "validate_cole_presentation_outline.py",
                BASE / "validate_superfecta_html_report.py",
                BASE / "validate_report_surfaces.py",
                BASE / "validate_validation_quickstart.py",
                BASE / "validate_project_surfaces.py",
            ],
            "named_operator_validators_exist",
            "every validator script named directly in PAPER_TRADE_USAGE currently exists, so the runbook is not routing Cole to stale helper names",
        )
    )
    checks.append(
        require_paths_exist(
            [
                BASE / "out" / "status_validation" / "paper_trade_operator_suite" / "paper_trade_operator_suite_validation.md",
                BASE / "out" / "status_validation" / "paper_trade_source_chain_guardrails" / "paper_trade_source_chain_guardrails_validation.md",
                BASE / "out" / "status_validation" / "paper_trade_settlement_sync" / "paper_trade_settlement_sync_validation.md",
                BASE / "out" / "status_validation" / "paper_trade_settlement_helper" / "paper_trade_settlement_helper_validation.md",
                BASE / "out" / "status_validation" / "run_daily_portfolio_observation" / "run_daily_portfolio_observation_validation.md",
                BASE / "out" / "status_validation" / "cross_family_decision" / "cross_family_decision_validation.md",
                BASE / "out" / "status_validation" / "current_hierarchy_language" / "current_hierarchy_language_validation.md",
                BASE / "out" / "status_validation" / "current_evidence_summary" / "current_evidence_summary_validation.md",
                BASE / "out" / "status_validation" / "report_surfaces" / "report_surfaces_validation.md",
            ],
            "named_validation_outputs_exist",
            "the operator-suite, report-surfaces, daily-wrapper, and direct settlement-layer validation outputs named directly in PAPER_TRADE_USAGE currently exist on disk",
        )
    )

    checks.append(
        require(
            EVIDENCE_BOUNDARY.get("artifact_role") == "paper-trade usage / operator workflow runbook validator"
            and EVIDENCE_BOUNDARY.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and EVIDENCE_BOUNDARY.get("not_new_forward_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_live_paper_trade_ledger") is True
            and EVIDENCE_BOUNDARY.get("not_current_day_scanner_result") is True
            and EVIDENCE_BOUNDARY.get("not_settled_roi_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_live_profitability_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_real_money_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_promotion_readiness_evidence") is True
            and EVIDENCE_BOUNDARY.get("paper_trade_usage_validator_passes_are_navigation_metadata_only") is True
            and "documented OP-anchor-first, primary OP/CD paper-basket companion, and separate Phase 8 shadow/watch command paths" in EVIDENCE_BOUNDARY.get("source_scope", [])
            and "documented scorecard ranking-contract / gate-floor audit route" in EVIDENCE_BOUNDARY.get("source_scope", [])
            and "documented copied-current-paper fanout after current-evidence bridge rebuilds" in EVIDENCE_BOUNDARY.get("source_scope", [])
            and "documented OP-anchor-first, active OP/CD paper-companion, and separate Phase 8 shadow/watch command paths" not in EVIDENCE_BOUNDARY.get("source_scope", [])
            and "ROI-complete settled paper rows" in EVIDENCE_BOUNDARY.get("stronger_forward_confidence_requires", [])
            and "do not promote OP_REFINED_K7 or Phase 8 from runbook validation cleanliness" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "do not substitute BAQ for BEL" in EVIDENCE_BOUNDARY.get("non_goals", []),
            "paper_trade_usage_json_publishes_machine_readable_evidence_boundary",
            f"paper-trade usage validator JSON now publishes exact valid_evidence_scope={VALID_EVIDENCE_SCOPE} plus a machine-readable evidence_boundary block that keeps operator workflow, command routing, paper-trade runbook guidance, validator-ladder alignment, primary OP/CD paper-basket companion wording, source-chain routing, settlement routing, right-now routing, refresh routing, and wrapper routing separate from settled ROI, live profitability, promotion readiness, real-money evidence, OP_REFINED_K7 / Phase 8 promotion, odds-only XGBoost reopening, and BAQ/BEL substitution",
        )
    )

    suite_read = (
        "paper-trade usage now opens with an explicit workflow-not-proof evidence frame and names the frozen evidence sources that do carry the real comparison burden, "
        "so the runbook no longer risks being read as standalone profit proof, "
        "while still matching the current operator posture: OP-anchor-first start path still leads, "
        "the Phase 7 current-paper basket and daily primary-basket-plus-shadow/watch wrapper remain the main routine, with OP/CD paper-active as rule components rather than a claim that today's calendar has target cards before preflight, with OP_DURABLE_K7 as the current paper anchor, CD_CORE_K8 as the primary OP/CD paper-basket companion inside the primary basket rather than a Phase 8 shadow-lane promotion, and OP_REFINED_K7 still parked in the shadow lane as the smaller same-family challenger while KEE_K9 / SA_K9 / DMR_FALL_K7 remain observation-only pockets, with the broader selective-family secondary shadow read staying replay-context rather than extra train-only proof, "
        "the runbook now also gives one compact OP-vs-CD operator table that says plainly why CD_CORE_K8 is paper-worthy in the primary basket without outranking OP_DURABLE_K7 as the safest current paper anchor: CD is cleaner across both current holdout years, but OP still owns the larger forward sample and the much stronger walk-forward selection frequency, "
        "and it now gives the same compact treatment to the shadow lane by saying plainly why OP_REFINED_K7 remains observation-only: the aggregate holdout is hotter, but it still rests on a much smaller forward sample, a losing 2024, and much weaker walk-forward selection frequency than the durable anchor, while the other current Phase 8 shadow names stay in the worth-logging-but-not-promoting bucket, "
        "the combined daily summary now calls out preserved primary/shadow recent-run context lines plus explicit primary/shadow next-step state lines, lifted no-overpromotion decision-gate snapshot lines, and first-read and broader-review readiness lines so shadow decision-grade review is visible without being mistaken for live promotion, "
        "the runbook now documents the settlement-audit action-line contract: audit JSON publishes primary/shadow next_action / next_action_reason, daily_summary lifts them with the no-new-evidence boundary, refresh and daily-wrapper validators preserve them, and action slugs are ledger-readiness routing rather than profitability proof, "
        f"the compact source-chain matrix is now exposed as the first audit read when the question is the whole upstream scan -> recommend -> size -> log guardrail inventory, including its generator, markdown/JSON outputs, direct validator/report path, its {source_chain['total_guardrail_checks']} scan/recommend/size/log guardrails, the direct live-scanner source-boundary contract for status sidecars and scanner hit rows, and operational-readiness-only / no-live-evidence boundary, and the runbook now says the operator suite embeds that fresh matrix as `auxiliary_source_chain_matrix`, checks disk hashes, and recomputes payload parity while the project sweep verifies the embedded result as propagation/readiness metadata rather than flattening the upstream chain into a generic operator-suite pass, "
        "the OP-anchor research provenance/readable-boundary route is now exposed in the runbook as `OP_ANCHOR_METHOD_COMPARISON.md` / `op_anchor_method_comparison.json` plus `validate_op_anchor_method_comparison.py`, tying the OP / Harville / current odds-only XGBoost wording back to exact source bytes and JSON `evidence_boundary_text` while preserving fingerprints and boundary text as provenance/reproducibility and no-new-evidence metadata only rather than settled ROI, promotion readiness, live profitability, or real-money evidence, "
        "the direct cross-family current-paper route is now exposed in the operator runbook as `CROSS_FAMILY_DECISION.md` plus `validate_cross_family_decision.py`, so anchor / paper / watch ordering and the current-paper snapshot caveat for stale-card refresh routing, CD-only settled rows, and source-published settlement-queue state/context stay out of OP-anchor proof, cross-family promotion evidence, live profitability, bankroll guidance, and real-money evidence, "
        "the direct main-status route is now exposed in the operator runbook as `COLE_STATUS_AND_PLAN.md` plus `validate_cole_status_and_plan.py`, so `status_doc_base_api_access_route_documented` keeps base API-access / HTTP 403 status-summary action-recheck route edits visible before lane enrichment as status/map alignment metadata rather than settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence, "
        "the scorecard audit route is now exposed in the operator runbook as `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `validate_scorecard_ranking_contract_audit.py`, so copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only diagnostic context, generated-at timezone provenance, and the no-BAQ-as-BEL prerequisite stay report-synchronization metadata rather than live paper results, promotion readiness, live profitability, bankroll guidance, or real-money evidence, "
        f"the current-evidence bridge route is now exposed in the runbook as `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` plus `current_evidence_summary.py` and `validate_current_evidence_summary.py`, so Cole-facing current paper-total wording has to pass through the source-consistency check across `PAPER_TRADE_NOW.json`, settlement audit, and the primary settlement CSV plus the combined `operator_status_context` + `source_freshness` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` / `recommended_command` route before stale or missing-state right-now cards are treated as today's operator instruction or evidence, keeps the {suite_gate_phrase} visible, preserves the source-derived {current_open_row_context_phrase}, source-matches the OP_REFINED CI-only diagnostic to `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` with `ci_only_promotion_allowed=false`, consumes current_evidence_summary.json scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks as report-synchronization metadata only, consumes current_evidence_summary.json rebuild_validation_contract for the required `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` rebuild order after source-byte changes as provenance metadata only, source-matches the operator gate floors to `forward_evidence_scorecard.json` `decision_gate_minimums` with `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100` plus the no-BAQ-as-BEL prerequisite treated as future ROI-complete paper-observation requirements rather than cleared gates, treats `source_consistency.overall_match=false` as repair-first, treats invalid `source_freshness.right_now_freshness_state_valid` as wrapper-refresh-first, treats `source_freshness.requires_refresh_before_right_now_use=true` as refresh-the-wrapper-before-use, treats `source_freshness.requires_refresh_before_right_now_use=false` as fresh-against-the-bridge but still not performance proof, treats `operator_read_gate.requires_refresh_before_evidence_read=true` as wrapper-refresh-before-instruction/evidence-read, and stays source-consistency / operator-status context / structured source-freshness / operator-read-gate routing / {queue_recommendation_context_label} / scorecard CI-only boundary / scorecard audit route / rebuild order / no-overclaim metadata only rather than settled ROI, live profitability, promotion readiness, anchor displacement, bankroll guidance, or real-money evidence, "
        "the runbook now also says a clean current-bridge rebuild is not enough before report-facing comparison quotes: frozen replay, downstream A/B, compare-main, OP-anchor, OP-family, cross-family, method-family, portfolio, selective-scope, scorecard audit, frozen evidence chain, report surfaces, and project surfaces have to be checked as copied-current-paper fanout drift prevention only, not evidence movement, "
        "the settlement layer now calls out separate direct validator routes for template sync, manual settlement entry, and ledger-completeness / ROI-coverage audit repair-label checks, "
        "the daily-wrapper fallback path now calls out its own canonical direct validator report route, and the runbook now says plainly that the refresh-helper plus daily-wrapper leaves are the source-of-truth wrapper reports broader operator/project sweeps should preserve rather than flatten, including wrapper-generated `CURRENT_EVIDENCE_SUMMARY` refresh/placeholder plus source-backed recommendation-context/open-row separation before Cole-facing current-paper wording, "
        f"the right-now inventory and saved-live sections now say plainly that the top-card/rebuild path carries preserved primary/shadow recent-run context plus lane why-now lines across both the immediate operator card and rebuilt saved-live refresh path, including missing scan-output context preservation in rebuilt per-run surfaces, while the right-now text/markdown/JSON bundle must keep machine-readable JSON parity unless the full helper failed into an explicit no-new-forward-evidence placeholder, while stale cards explicitly mark downstream lane context/counts/quick reads as inherited snapshot state rather than current-day state, with rebuilt daily summaries inheriting routed top-card snapshot lines from refreshed top-level surfaces, the distinct `--latest-only` newest-run versus `--skip-top-level` top-card-preservation maintenance boundaries staying visible, and optional `--as-of-date` freshness pinning saying whether it was applied to rebuilt top-level freshness or ignored because top-level outputs were skipped, while the saved-live refresh helper now says explicitly that it rerenders existing artifacts rather than creating new forward evidence, while the current hierarchy language route is now exposed in the operator runbook for `live_hierarchy`, `primary_companion`, and compatibility-only `primary_shadow` edits before broader top-card/wrapper validations, while the top-level project-sweep route now explicitly says broad cross-layer checks include the direct current-hierarchy child validator, while the saved operator runbook and its direct validator report path stay pinned across the operator ladder, while the paper-trade usage validator JSON now publishes exact valid_evidence_scope={VALID_EVIDENCE_SCOPE} plus a machine-readable evidence_boundary as operator workflow/navigation metadata only rather than settled ROI / live profitability / promotion readiness / real-money evidence, and the umbrella operator-suite and top-level project-sweep routes now also say plainly that they are alignment/readiness checks rather than new evidence, "
        "the runbook now keeps the top-level out/paper_trade_preflight_note.txt file separated as a standalone manual scratch cache rather than a daily operator proof source, "
        "the runbook now gives one compact quiet-day versus broken-day interpretation rule that explicitly names recommender/logger pipeline failures, says no-target proof must come from the saved run-root preflight note, and keeps green cache-only / partial-cache messaging validators framed as cache-edge routing and reproducibility metadata rather than quiet-day, current scanner, settled ROI, live-profitability, promotion-readiness, or real-money evidence, "
        "the direct status-summary route now points API-access / HTTP 403 action-recheck route preservation and stale-cache fallback metadata at `validate_paper_trade_status_summary.py` before lane enrichment, "
        "the machine-readable pipeline sidecar section plus the human-readable summary example now say those failures carry explicit stage/error/detail context, and the sidecar section now documents the shared scanner_status_path relocated-sidecar resolution contract so lane-local, run-root-relative, project-relative, stale-default-masked, and API-access scanner sidecars stay connected to the operator surfaces instead of falling back silently to a missing, stale, or clean-looking default path, "
        "the dated working-status note plus its direct validator are now exposed for production-basket versus demo-lane questions, "
        "the direct report-surfaces validator plus its saved markdown output are now exposed for shareable wording, presentation drift, dated-report trust-path questions, and the README-inherited wrapper-leaf note the narrative rollup should preserve rather than flatten, "
        "the quickstart is described as carrying the dated-report / legacy-alias policy rather than only a PDF-export note, "
        "and the runbook names its own validator so operator-doc drift fails more loudly; "
        "paper-trade-usage runbook layer: operator workflow/navigation check, not new forward evidence by itself; stronger forward confidence still requires settled paper trades and other real forward results"
    )

    checks.append(
        require(
            "paper-trade-usage runbook layer: operator workflow/navigation check, not new forward evidence by itself" in suite_read
            and "OP/CD paper-active as rule components rather than a claim that today's calendar has target cards before preflight" in suite_read
            and "primary OP/CD paper-basket companion inside the primary basket rather than a Phase 8 shadow-lane promotion" in suite_read
            and "current-evidence bridge route is now exposed in the runbook as `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` plus `current_evidence_summary.py` and `validate_current_evidence_summary.py`" in suite_read
            and "source-consistency check across `PAPER_TRADE_NOW.json`, settlement audit, and the primary settlement CSV plus the combined `operator_status_context` + `source_freshness` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` / `recommended_command` route" in suite_read
            and "before stale or missing-state right-now cards are treated as today's operator instruction or evidence" in suite_read
            and "source-matches the OP_REFINED CI-only diagnostic to `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` with `ci_only_promotion_allowed=false`" in suite_read
            and "consumes current_evidence_summary.json scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks as report-synchronization metadata only" in suite_read
            and "consumes current_evidence_summary.json rebuild_validation_contract for the required `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` rebuild order after source-byte changes as provenance metadata only" in suite_read
            and "clean current-bridge rebuild is not enough before report-facing comparison quotes" in suite_read
            and "copied-current-paper fanout drift prevention only, not evidence movement" in suite_read
            and "direct cross-family current-paper route is now exposed in the operator runbook as `CROSS_FAMILY_DECISION.md` plus `validate_cross_family_decision.py`" in suite_read
            and "current-paper snapshot caveat for stale-card refresh routing, CD-only settled rows, and source-published settlement-queue state/context stay out of OP-anchor proof, cross-family promotion evidence, live profitability, bankroll guidance, and real-money evidence" in suite_read
            and "direct main-status route is now exposed in the operator runbook as `COLE_STATUS_AND_PLAN.md` plus `validate_cole_status_and_plan.py`" in suite_read
            and "`status_doc_base_api_access_route_documented` keeps base API-access / HTTP 403 status-summary action-recheck route edits visible before lane enrichment" in suite_read
            and "scorecard audit route is now exposed in the operator runbook as `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `validate_scorecard_ranking_contract_audit.py`" in suite_read
            and "copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only diagnostic context, generated-at timezone provenance, and the no-BAQ-as-BEL prerequisite stay report-synchronization metadata" in suite_read
            and "source-matches the operator gate floors to `forward_evidence_scorecard.json` `decision_gate_minimums`" in suite_read
            and "no-BAQ-as-BEL prerequisite" in suite_read
            and "treated as future ROI-complete paper-observation requirements rather than cleared gates" in suite_read
            and "source_freshness.right_now_freshness_state_valid` as wrapper-refresh-first" in suite_read
            and "source_freshness.requires_refresh_before_right_now_use=true` as refresh-the-wrapper-before-use" in suite_read
            and "source_freshness.requires_refresh_before_right_now_use=false` as fresh-against-the-bridge but still not performance proof" in suite_read
            and "operator_read_gate.requires_refresh_before_evidence_read=true` as wrapper-refresh-before-instruction/evidence-read" in suite_read
            and f"source-consistency / operator-status context / structured source-freshness / operator-read-gate routing / {queue_recommendation_context_label} / scorecard CI-only boundary / scorecard audit route / rebuild order / no-overclaim metadata only" in suite_read
            and suite_gate_phrase in suite_read
            and current_open_row_context_phrase in suite_read
            and "including wrapper-generated `CURRENT_EVIDENCE_SUMMARY` refresh/placeholder plus source-backed recommendation-context/open-row separation before Cole-facing current-paper wording" in suite_read
            and "current hierarchy language route is now exposed in the operator runbook for `live_hierarchy`, `primary_companion`, and compatibility-only `primary_shadow` edits" in suite_read
            and "top-level project-sweep route now explicitly says broad cross-layer checks include the direct current-hierarchy child validator" in suite_read
            and "direct status-summary route now points API-access / HTTP 403 action-recheck route preservation and stale-cache fallback metadata at `validate_paper_trade_status_summary.py` before lane enrichment" in suite_read
            and "primary non-anchor shadow" not in suite_read
            and "stronger forward confidence still requires settled paper trades and other real forward results" in suite_read,
            "paper_trade_usage_summary_explicitly_stays_navigation_not_new_evidence",
            "paper-trade-usage summary now says plainly that a green operator runbook sweep is workflow/navigation checking rather than new forward evidence",
        )
    )

    payload = {
        "suite_status": "pass",
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "current_evidence_gate_progress_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            "source_path": "decision_gate_progress",
            "scorecard_source": gate_progress.get("source_path"),
            "scorecard_source_json_path": gate_progress.get("source_json_path"),
            "gate_status": gate_progress.get("gate_status"),
            "all_gates_ready": gate_progress.get("all_gates_ready"),
            "read": gate_progress_read,
            "not_forward_performance_evidence": gate_progress.get("not_forward_performance_evidence"),
            "not_promotion_readiness_evidence": gate_progress.get("not_promotion_readiness_evidence"),
            "not_live_profitability_evidence": gate_progress.get("not_live_profitability_evidence"),
            "not_real_money_evidence": gate_progress.get("not_real_money_evidence"),
        },
        "current_evidence_operator_read_gate_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            "source_path": "operator_read_gate",
            "gate_status": operator_read_gate.get("gate_status"),
            "valid_use": operator_read_gate.get("valid_use"),
            "requires_refresh_before_evidence_read": operator_read_gate.get("requires_refresh_before_evidence_read"),
            "recommended_command": operator_read_gate.get("recommended_command"),
            "has_api_access_failure_context": operator_read_gate.get("has_api_access_failure_context"),
            "has_scanner_failure_boundary": operator_read_gate.get("has_scanner_failure_boundary"),
            "has_stale_cache_fallback_context": operator_read_gate.get("has_stale_cache_fallback_context"),
            "current_top_card_counts_as_no_target_evidence": operator_read_gate.get("current_top_card_counts_as_no_target_evidence"),
            "current_top_card_counts_as_clean_empty_evidence": operator_read_gate.get("current_top_card_counts_as_clean_empty_evidence"),
            "current_top_card_counts_as_bet_readiness_evidence": operator_read_gate.get("current_top_card_counts_as_bet_readiness_evidence"),
            "current_top_card_counts_as_settled_roi_evidence": operator_read_gate.get("current_top_card_counts_as_settled_roi_evidence"),
            "not_forward_performance_evidence": operator_read_gate.get("not_forward_performance_evidence"),
            "not_promotion_readiness_evidence": operator_read_gate.get("not_promotion_readiness_evidence"),
            "not_live_profitability_evidence": operator_read_gate.get("not_live_profitability_evidence"),
            "not_real_money_evidence": operator_read_gate.get("not_real_money_evidence"),
            "read": operator_read_gate_read,
        },
        "current_evidence_scorecard_audit_route_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            "source_path": "scorecard_audit_route",
            "markdown_path": scorecard_audit_route.get("markdown_path"),
            "json_path": scorecard_audit_route.get("json_path"),
            "validator_command": scorecard_audit_route.get("validator_command"),
            "gate_floor_source": scorecard_audit_route.get("gate_floor_source"),
            "gate_floor_snapshot": scorecard_audit_route.get("gate_floor_snapshot"),
            "artifacts_present": scorecard_audit_route.get("artifacts_present"),
            "valid_use": scorecard_audit_route.get("valid_use"),
            "not_forward_performance_evidence": scorecard_audit_route.get("not_forward_performance_evidence"),
            "not_settled_roi_evidence": scorecard_audit_route.get("not_settled_roi_evidence"),
            "not_promotion_readiness_evidence": scorecard_audit_route.get("not_promotion_readiness_evidence"),
            "not_live_profitability_evidence": scorecard_audit_route.get("not_live_profitability_evidence"),
            "not_bankroll_guidance": scorecard_audit_route.get("not_bankroll_guidance"),
            "not_real_money_evidence": scorecard_audit_route.get("not_real_money_evidence"),
            "route_read": scorecard_audit_route_read,
        },
        "current_evidence_rebuild_validation_contract_read": rebuild_contract,
        "source_chain_guardrail_matrix_read": source_chain,
        "summary": {
            "suite_read": suite_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }

    lines = [
        "# Paper Trade Usage Validation",
        "",
        "This report checks that `PAPER_TRADE_USAGE.md` still reflects the current operator workflow, validator stack, and OP-anchor-first deployment posture.",
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

    boundary = payload["evidence_boundary"]
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            f"- Artifact role: {boundary['artifact_role']}",
            f"- valid_evidence_scope={boundary['valid_evidence_scope']}",
            f"- Valid use: {boundary['valid_use']}",
            "- This green read is operator workflow/navigation metadata only: it is not new forward evidence, a live paper-trade ledger, current-day scanner output, settled ROI, live profitability, promotion readiness, or real-money evidence.",
            "- Stronger forward confidence still requires qualifying live paper signals, ROI-complete settled paper rows, settlement-quality checks, or other real forward observations.",
            "- Non-goals: do not promote OP_REFINED_K7 / Phase 8, reopen current odds-only XGBoost, substitute BAQ for BEL, or treat documented paper-trade commands as real-money evidence from this validator pass.",
            "",
            "## Current Read",
            "",
            f"- Suite read: {suite_read}",
            "- Individual validator additions / hierarchy/current-evidence routes restored: `validate_paper_trade_status_summary.py`, `validate_paper_trade_settlement_sync.py`, `validate_paper_trade_settlement_helper.py`, `validate_paper_trade_next_steps.py`, `validate_current_hierarchy_language.py`, `validate_current_evidence_summary.py`",
            "- Preferred current-paper start: `./run_paper_trade_cycle.sh --rules op_anchor_rules.json`",
            "- Preferred daily routine: `./run_daily_portfolio_observation.sh`",
            "",
            "## Bottom Line",
            "",
            "If this validator stays green, `PAPER_TRADE_USAGE.md` remains the fastest operator runbook for day-to-day paper-trade workflow, including the direct wrapper, settlement, status-summary, and report-surfaces routes plus the guardrail that broader sweeps are navigation/readiness checks rather than fresh forward proof.",
            "That green read is operator workflow alignment, not new forward evidence by itself.",
            "",
            "## Source Artifacts",
            "",
            "- `PAPER_TRADE_USAGE.md`",
            "- `VALIDATION_QUICKSTART.md`",
            "- `PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md`",
            "- `WORKING_STATUS_REPORT_2026-04-15.md`",
            "- `validate_paper_trade_operator_suite.py`",
            "- `validate_working_status_report.py`",
        ]
    )

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
