#!/usr/bin/env python3
"""
Validation for WORKING_STATUS_REPORT_2026-04-15.md.

Purpose:
- keep the dated live/demo status note honest about what was proven on 2026-04-15
- preserve the production-basket vs demo-lane distinction around OP/CD vs available live cards
- stop the mutable latest-demo alias from being mistaken for the dated report-time evidence anchor
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
REPORT = BASE / "WORKING_STATUS_REPORT_2026-04-15.md"
DEMO_SCRIPT = BASE / "demo_live_predictions.py"
OPS_SCRIPT = BASE / "superfecta_ops.py"
OUT_DIR = BASE / "out" / "status_validation" / "working_status_report"
OUT_MD = OUT_DIR / "working_status_report_validation.md"
OUT_JSON = OUT_DIR / "working_status_report_validation.json"
CURRENT_EVIDENCE_MD = BASE / "CURRENT_EVIDENCE_SUMMARY.md"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
CROSS_FAMILY_MD = BASE / "CROSS_FAMILY_DECISION.md"
CROSS_FAMILY_VALIDATOR = BASE / "validate_cross_family_decision.py"
FULL_DATA_RETRAIN_MD = BASE / "FULL_DATA_RETRAIN_ARTIFACTS.md"
FULL_DATA_RETRAIN_VALIDATOR = BASE / "validate_full_data_retrain_artifacts.py"
REBUILD_COMMAND = "python3 validate_working_status_report.py"
EXPECTED_REBUILD_ORDER_COMMANDS = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"


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

    return {
        "payload": payload,
        "read": {
            "source": source_name,
            "source_path": "decision_gate_minimums",
            "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
            "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
            "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
            "real_money_no_baq_as_bel_required": True,
        },
    }


def require_current_evidence_rebuild_contract(current_evidence: dict[str, Any]) -> dict[str, Any]:
    contract = current_evidence.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise AssertionError("current_evidence_summary.json must publish rebuild_validation_contract as an object")
    upstream_refresh_order = contract.get("upstream_refresh_order")
    if not isinstance(upstream_refresh_order, list) or len(upstream_refresh_order) != len(EXPECTED_REBUILD_ORDER_COMMANDS):
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract must publish the three-step upstream_refresh_order")

    commands: list[str] = []
    for expected_order, step in enumerate(upstream_refresh_order, start=1):
        if not isinstance(step, dict):
            raise AssertionError("current_evidence_summary.json upstream_refresh_order steps must be objects")
        if step.get("order") != expected_order:
            raise AssertionError("current_evidence_summary.json upstream_refresh_order order values drifted")
        command = step.get("command")
        if not isinstance(command, str):
            raise AssertionError("current_evidence_summary.json upstream_refresh_order commands must be strings")
        commands.append(command)

    if commands != EXPECTED_REBUILD_ORDER_COMMANDS:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract upstream order drifted")
    if contract.get("prerequisite_rebuild_command") != EXPECTED_REBUILD_ORDER_COMMANDS[0]:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract prerequisite command drifted")
    if contract.get("rebuild_command") != EXPECTED_REBUILD_ORDER_COMMANDS[1]:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract rebuild command drifted")
    if contract.get("direct_validation_command") != EXPECTED_REBUILD_ORDER_COMMANDS[2]:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract direct validator command drifted")
    if contract.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is not True:
        raise AssertionError("rebuild_validation_contract must require settlement-audit refresh before bridge rebuilds")
    if contract.get("requires_source_consistency_before_quoting_current_totals") is not True:
        raise AssertionError("rebuild_validation_contract must require source consistency before current totals are quoted")
    if contract.get("upstream_refresh_order_is_provenance_metadata_only") is not True:
        raise AssertionError(
            "current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true"
        )
    if contract.get("not_settled_roi_or_real_money_evidence") is not True:
        raise AssertionError("rebuild_validation_contract must not be settled ROI or real-money evidence")

    return {
        "source": CURRENT_EVIDENCE_JSON.name,
        "source_path": "rebuild_validation_contract",
        "upstream_refresh_order": commands,
        "prerequisite_rebuild_command": contract.get("prerequisite_rebuild_command"),
        "rebuild_command": contract.get("rebuild_command"),
        "direct_validation_command": contract.get("direct_validation_command"),
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": contract.get(
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
        ),
        "requires_source_consistency_before_quoting_current_totals": contract.get(
            "requires_source_consistency_before_quoting_current_totals"
        ),
        "upstream_refresh_order_is_provenance_metadata_only": contract.get(
            "upstream_refresh_order_is_provenance_metadata_only"
        ),
        "not_settled_roi_or_real_money_evidence": contract.get("not_settled_roi_or_real_money_evidence"),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the dated working status report")
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--current-evidence-json", type=Path, default=CURRENT_EVIDENCE_JSON)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def scorecard_gate_cli_contract_checks(
    scorecard_json_path: Path = SCORECARD_JSON,
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="working_status_scorecard_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(scorecard_json_path).read_text(encoding="utf-8"))
        scorecard_path = tmp_root / "forward_evidence_scorecard.json"

        nonpositive_phase8_out_dir = tmp_root / "nonpositive_phase8" / "working_status_report_validation"
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
                str(nonpositive_phase8_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not nonpositive_phase8_out_dir.exists()
                and "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer"
                in proc.stderr,
                "scorecard_nonpositive_phase8_floor_fails_before_artifacts",
                "validate_working_status_report.py rejects a non-positive Phase 8 promotion-review scorecard gate before creating nested output directories or partial working-status validation artifacts",
            )
        )

        nonpositive_real_money_out_dir = tmp_root / "nonpositive_real_money" / "working_status_report_validation"
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
                str(nonpositive_real_money_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not nonpositive_real_money_out_dir.exists()
                and "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer"
                in proc.stderr,
                "scorecard_nonpositive_real_money_floor_fails_before_artifacts",
                "validate_working_status_report.py rejects a non-positive real-money discussion scorecard gate before creating nested output directories or partial working-status validation artifacts",
            )
        )

    return checks


def current_bridge_cli_contract_checks(
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="working_status_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json_path).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "working_status_report_validation"
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
                "validate_working_status_report.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial working-status validation artifacts",
            )
        )

        weakened_contract_out_dir = tmp_root / "weakened" / "working_status_report_validation"
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
                "validate_working_status_report.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial working-status validation artifacts",
            )
        )

    return checks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    current_evidence = json.loads(Path(args.current_evidence_json).read_text(encoding="utf-8"))
    rebuild_contract_read = require_current_evidence_rebuild_contract(current_evidence)
    scorecard_gate_context_read = scorecard_gate_context(args.scorecard_json)
    scorecard_json = scorecard_gate_context_read["payload"]
    primary_status = current_evidence["current_paper_status"]["primary"]
    first_read = primary_status["first_read"]
    portfolio_review = primary_status["portfolio_review"]
    rule_progress = {row["rule_id"]: row for row in primary_status["rule_progress"]}
    open_settlements = int(primary_status.get("open_settlements", 0) or 0)
    open_settlement_summary = primary_status["open_settlement_summary"]
    open_queue = primary_status.get("open_settlement_queue_by_rule")
    if not isinstance(open_queue, dict):
        raise AssertionError("current_paper_status.primary.open_settlement_queue_by_rule must be present")
    open_settlement_queue_state = str(open_queue.get("open_settlement_queue_state") or "").strip()
    open_settlement_context = str(open_queue.get("open_settlement_context") or "").strip()
    open_settlement_queue_read = str(open_queue.get("detail_read") or "").strip()
    expected_open_settlement_queue_state = "closed" if open_settlements == 0 else "open"
    if open_settlement_queue_state not in {"closed", "open"}:
        raise AssertionError("open_settlement_queue_state must be closed or open")
    if open_settlement_queue_state != expected_open_settlement_queue_state:
        raise AssertionError("open_settlement_queue_state must match primary open_settlements")
    if open_settlements == 0 and open_settlement_context != "no open primary settlement rows":
        raise AssertionError("closed settlement queue must use the source no-open-primary-rows context")
    if open_settlements > 0 and "open" not in open_settlement_context.lower():
        raise AssertionError("open settlement queue context must identify open rows")
    if "Open settlement queue by rule:" not in open_settlement_queue_read:
        raise AssertionError("detail_read must preserve the by-rule open settlement detail")
    if "Settlement queue state:" in open_settlement_queue_read:
        raise AssertionError("detail_read must not nest the settlement queue state wrapper")
    recommendation_context = primary_status["recommendation_context"]
    recommendation_read = str(recommendation_context.get("read") or "").strip()
    api_access_action_route_present = (
        "Sidecar action: refresh_daily_wrapper_before_evidence_read" in recommendation_read
        and "Recheck command: ./run_daily_portfolio_observation.sh" in recommendation_read
    )
    source_consistency_label = "matched" if current_evidence["source_consistency"].get("overall_match") else "mismatch"
    source_freshness = current_evidence["source_freshness"]
    requires_refresh = bool(source_freshness.get("requires_refresh_before_right_now_use"))
    source_freshness_label = "requires_refresh_before_right_now_use=true" if requires_refresh else "requires_refresh_before_right_now_use=false"
    source_freshness_read = "requires refresh before right-now use" if requires_refresh else "fresh for right-now use"
    combined_operator_route_label = (
        "requires refresh before right-now instruction or evidence use"
        if requires_refresh
        else "is fresh against the bridge reference date but still goes through operator read-gate routing before right-now instruction or evidence use"
    )
    operator_read_gate = (
        current_evidence.get("operator_read_gate")
        if isinstance(current_evidence.get("operator_read_gate"), dict)
        else {}
    )
    operator_read_gate_read = str(operator_read_gate.get("read") or "").strip()
    api_access_action_route_required = bool(
        operator_read_gate.get("has_api_access_failure_context")
        or operator_read_gate.get("has_scanner_failure_boundary")
        or operator_read_gate.get("has_stale_cache_fallback_context")
    )
    operator_read_gate_requires_refresh = bool(
        operator_read_gate.get("requires_refresh_before_evidence_read")
    )
    operator_read_gate_requires_refresh_label = (
        "true" if operator_read_gate_requires_refresh else "false"
    )
    operator_read_gate_json_read = {
        "source": CURRENT_EVIDENCE_JSON.name,
        "source_path": "operator_read_gate",
        "gate_status": operator_read_gate.get("gate_status"),
        "valid_use": operator_read_gate.get("valid_use"),
        "requires_refresh_before_evidence_read": operator_read_gate.get("requires_refresh_before_evidence_read"),
        "has_api_access_failure_context": operator_read_gate.get("has_api_access_failure_context"),
        "has_scanner_failure_boundary": operator_read_gate.get("has_scanner_failure_boundary"),
        "has_stale_cache_fallback_context": operator_read_gate.get("has_stale_cache_fallback_context"),
        "recommended_command": operator_read_gate.get("recommended_command"),
        "current_top_card_counts_as_no_target_evidence": operator_read_gate.get(
            "current_top_card_counts_as_no_target_evidence"
        ),
        "current_top_card_counts_as_clean_empty_evidence": operator_read_gate.get(
            "current_top_card_counts_as_clean_empty_evidence"
        ),
        "current_top_card_counts_as_bet_readiness_evidence": operator_read_gate.get(
            "current_top_card_counts_as_bet_readiness_evidence"
        ),
        "current_top_card_counts_as_settled_roi_evidence": operator_read_gate.get(
            "current_top_card_counts_as_settled_roi_evidence"
        ),
        "not_forward_performance_evidence": operator_read_gate.get("not_forward_performance_evidence"),
        "not_promotion_readiness_evidence": operator_read_gate.get("not_promotion_readiness_evidence"),
        "not_live_profitability_evidence": operator_read_gate.get("not_live_profitability_evidence"),
        "not_real_money_evidence": operator_read_gate.get("not_real_money_evidence"),
        "read": operator_read_gate_read,
    }
    scorecard_gate_read = scorecard_gate_context_read["read"]
    scorecard_anchor_min = scorecard_gate_read["anchor_displacement_min_roi_complete_settled_observations"]
    scorecard_phase8_min = scorecard_gate_read["phase8_promotion_review_min_roi_complete_settled_observations"]
    scorecard_real_money_min = scorecard_gate_read[
        "real_money_discussion_min_total_settled_observations_with_usable_roi"
    ]
    expected_source_freshness_line = (
        "- combined operator read route: check `operator_status_context`, `source_freshness.requires_refresh_before_right_now_use=true`, and `operator_read_gate.requires_refresh_before_evidence_read=true`; rerun `./run_daily_portfolio_observation.sh` before treating wrapper-refresh, missing-output, stale/API-failure `PAPER_TRADE_NOW`, or its best-action card as today's operator instruction or evidence"
        if requires_refresh
        else (
            "- combined operator read route: check `operator_status_context`, "
            "`source_freshness.requires_refresh_before_right_now_use=false`, and "
            f"`operator_read_gate.requires_refresh_before_evidence_read={operator_read_gate_requires_refresh_label}`; "
            "the saved `PAPER_TRADE_NOW` best-action card is fresh against the bridge reference date but still goes "
            "through operator read-gate routing before instruction or evidence use"
        )
    )
    expected_source_repair_line = (
        "- if `source_consistency.overall_match=false`, repair source mismatch before using paper totals; then use the combined `operator_status_context` + `source_freshness` + `operator_read_gate` route before using the saved right-now card as current-day guidance or evidence"
        if requires_refresh
        else "- if `source_consistency.overall_match=false`, repair source mismatch before using paper totals; then use the combined `operator_status_context` + `source_freshness` + `operator_read_gate` route before using the saved right-now card as current-day guidance or evidence"
    )
    expected_operator_read_gate_line = (
        f"- operator read gate: `operator_read_gate.requires_refresh_before_evidence_read="
        f"{operator_read_gate_requires_refresh_label}`; "
        f"{operator_read_gate_read}"
    )
    expected_rebuild_order_line = (
        "- bridge rebuild order: `current_evidence_summary.json.rebuild_validation_contract`; after "
        "scorecard/rules/signals/settlement-ledger byte changes, run `python3 paper_trade_settlement_audit.py` -> "
        "`python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting "
        "`CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not settled ROI, promotion readiness, "
        "live profitability, bankroll guidance, or real-money evidence"
    )
    expected_queue_context_line = (
        f"- settlement queue state: `{open_settlement_queue_state}`; {open_settlement_context}; detail: "
        f"{open_settlement_queue_read} Latest recommendation-state context: {recommendation_read}"
    )
    queue_recommendation_context_label = "source-published settlement queue state plus recommendation-state context"
    suite_queue_context = (
        f"settlement queue state={open_settlement_queue_state} / context={open_settlement_context} remains workflow context "
        f"rather than a bet-ready ticket or forward-performance proof, with source detail_read={open_settlement_queue_read} "
        f"and latest recommendation-state context saying {recommendation_read}"
    )

    report_text = REPORT.read_text(encoding="utf-8")
    demo_text = DEMO_SCRIPT.read_text(encoding="utf-8")
    ops_text = OPS_SCRIPT.read_text(encoding="utf-8")

    expected_bottom_line = (
        "The core live prediction stack is working.\n\n"
        "What was broken was the operational framing:\n"
        "- `superfecta_ops.py` is a **production basket wrapper** for `OP` and `CD`\n"
        "- I treated that like it meant **no live prediction path existed today**\n"
        "- that was wrong"
    )
    expected_demo_wrapper_section = (
        "### 3) One-command demo wrapper for today’s available cards\n"
        "Added:\n"
        "- `demo_live_predictions.py`\n\n"
        "Confirmed today:\n"
        "- `python3 demo_live_predictions.py --include-cards keeneland --save-latest-json`\n"
        "- selected the next available live/demo race automatically\n"
        "- generated predictions for **Keeneland Race 6**\n"
        "- wrote CSV + markdown report to `out/live_demo/`"
    )
    expected_files_added = (
        "## Files added\n\n"
        "- `demo_live_predictions.py`\n"
        "- `out/live_demo/keeneland_race6_20260415_151943.csv`\n"
        "- `out/live_demo/keeneland_race6_20260415_151943.md`\n"
        "- `out/live_demo/latest_demo_run.json` *(mutable convenience alias; later demo runs may repoint it)*"
    )
    expected_production_distinction = (
        "### Production basket\n"
        "`superfecta_ops.py` is still correct as a production wrapper for the OP/CD primary paper-basket target tracks:\n"
        "- `ACTIVE_TRACKS = {\"OP\": \"Oaklawn Park\", \"CD\": \"Churchill Downs\"}`\n\n"
        "So when it says no primary paper-basket target tracks today, it means:\n"
        "- no valid `OP/CD` production fire today\n\n"
        "It does **not** mean:\n"
        "- no live race anywhere\n"
        "- no demo possible\n"
        "- no model/API path available"
    )
    expected_demo_lane = (
        "### Demo lane\n"
        "`demo_live_predictions.py` is intentionally separate.\n"
        "It exists to generate live predictions on cards that are actually available today, without pretending we changed the production strategy or basket.\n\n"
        "What this does **not** mean:\n"
        "- not a production-basket change\n"
        "- not proof of betting profitability\n"
        "- not a reason to treat Keeneland as a validated live deployment lane\n"
        "- not new forward evidence for the OP/CD paper-trade case by itself; that still requires settled paper trades in the actual paper-trade lane"
    )
    expected_current_paper_bridge = (
        "## Current paper-trade bridge\n\n"
        "This dated report is demo-lane operability context. For current OP/CD paper totals, read `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` before quoting `PAPER_TRADE_NOW`, ops-bucket/operator-status context, settlement-audit, or ledger totals.\n\n"
        f"- source consistency: `{source_consistency_label}`\n"
        f"{expected_rebuild_order_line}\n"
        f"{expected_source_freshness_line}\n"
        f"{expected_operator_read_gate_line}\n"
        f"- decision-gate source: `{SCORECARD_JSON.name}` `decision_gate_minimums` sets `anchor_displacement={scorecard_anchor_min}`, `phase8_promotion_review={scorecard_phase8_min}`, and `real_money_discussion={scorecard_real_money_min}`; these are future ROI-complete observation floors, not cleared gates\n"
        f"- primary paper gate: `{first_read['current']}/{first_read['threshold']}` ROI-complete first-read rows and `{portfolio_review['current']}/{portfolio_review['threshold']}` broader-review rows\n"
        f"- current rule mix: `CD_CORE_K8` has `{rule_progress['CD_CORE_K8']['roi_complete_settled_rows']}` ROI-complete settled rows; `OP_DURABLE_K7` has `{rule_progress['OP_DURABLE_K7']['roi_complete_settled_rows']}` ROI-complete settled rows\n"
        "- interpretation: current settled sample is CD-only context, not OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence\n"
        "- direct cross-family caveat route: read `CROSS_FAMILY_DECISION.md` and run `python3 validate_cross_family_decision.py` when the question is whether the anchor / paper / watch shortlist still carries the current-paper caveat; stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green working-status validation are not OP-anchor proof or cross-family promotion evidence\n"
        "- full-data XGBoost retrain caveat route: read `FULL_DATA_RETRAIN_ARTIFACTS.md` and run `python3 validate_full_data_retrain_artifacts.py` when checking the model lane's full-data retrain artifacts or exact retrain/prediction commands; large RMSE / MAE gains remain model-fit reproducibility context only, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence\n"
        f"{expected_queue_context_line}\n"
        f"{expected_source_repair_line}"
    )
    expected_command_block = (
        "## Current demo command\n\n"
        "```bash\n"
        "cd \"/Users/maximusregent_ai/Shared/Superfecta Help\"\n"
        "python3 demo_live_predictions.py --include-cards keeneland --save-latest-json\n"
        "```"
    )
    expected_snapshot = (
        "## Report-time verified demo snapshot\n\n"
        "This is the report-time verified demo run from **2026-04-15**.\n"
        "The dated Keeneland CSV/markdown files above are the stable evidence anchor for this note; `out/live_demo/latest_demo_run.json` is a mutable convenience alias and may point at a later demo run.\n\n"
        "- card: `Keeneland`\n"
        "- race: `Race #6`\n"
        "- race id: `102075971`\n"
        "- post time: `2026-04-15T19:40:00Z`\n"
        "- top combo: `5-7-10-2`\n"
        "- top combo predicted payout: `$182.75`\n"
        "- top combo EV ROI: `-30.66%`"
    )
    expected_operational_bottom_line = (
        "## What this means operationally\n\n"
        "- The **model lane works**\n"
        "- The **API lane works**\n"
        "- The **demo lane works today**\n"
        "- The **production OP/CD basket is still unchanged**\n"
        "- The **demo result is an operability check, not an edge claim**\n"
        "- **New forward evidence still requires settled paper trades in the actual paper-trade lane**"
    )

    checks: list[dict[str, Any]] = []
    checks.extend(scorecard_gate_cli_contract_checks(args.scorecard_json, args.current_evidence_json))
    if Path(args.current_evidence_json).resolve() == CURRENT_EVIDENCE_JSON.resolve():
        checks.extend(current_bridge_cli_contract_checks(args.current_evidence_json))
    checks.append(
        require(
            expected_bottom_line in report_text,
            "bottom_line_framing",
            "working-status report still says the issue was operational framing, not absence of a live prediction path",
        )
    )
    checks.append(
        require(
            expected_demo_wrapper_section in report_text,
            "demo_wrapper_section",
            "working-status report still pins the dated keeneland demo-wrapper evidence and command",
        )
    )
    checks.append(
        require(
            expected_files_added in report_text,
            "files_added_section",
            "working-status report now marks latest_demo_run.json as a mutable alias instead of implying it is a frozen dated artifact",
        )
    )
    checks.append(
        require(
            expected_production_distinction in report_text,
            "production_vs_demo_distinction",
            "working-status report still keeps the OP/CD production-basket meaning separate from general live/demo availability",
        )
    )
    checks.append(
        require(
            f"current {'active'} basket" not in report_text
            and f"{'active'}-basket target" not in report_text
            and f"{'active'}-basket tracks" not in ops_text
            and f"{'active'}-basket races" not in ops_text
            and "primary paper-basket target tracks" in report_text
            and "primary paper-basket target tracks" in ops_text,
            "preflight_target_tracks_not_active_basket",
            "working-status report and superfecta_ops help now use primary paper-basket target-track wording instead of stale basket-status shorthand",
        )
    )
    checks.append(
        require(
            expected_demo_lane in report_text,
            "demo_lane_section",
            "working-status report still says the demo lane is intentionally separate and does not imply a production-basket change, profitability proof, or validated Keeneland deployment lane",
        )
    )
    checks.append(
        require(
            expected_current_paper_bridge in report_text,
            "current_evidence_bridge_section",
            f"working-status report now routes current OP/CD paper-total wording through CURRENT_EVIDENCE_SUMMARY.md / current_evidence_summary.json, pins source consistency, pins the source-owned bridge rebuild order, routes wrapper-refresh/missing-output/stale or API-failure right-now cards through the combined operator-status/source-freshness/operator-read-gate path, keeps the source-derived current gates visible, preserves the source-derived {queue_recommendation_context_label} as workflow context rather than bet-ready or forward-performance proof, and separates the CD-only settled sample from OP-anchor proof, promotion readiness, live profitability, bankroll guidance, and real-money evidence",
        )
    )
    checks.append(
        require(
            expected_rebuild_order_line in report_text
            and rebuild_contract_read.get("source") == "current_evidence_summary.json"
            and rebuild_contract_read.get("source_path") == "rebuild_validation_contract"
            and rebuild_contract_read.get("upstream_refresh_order") == EXPECTED_REBUILD_ORDER_COMMANDS
            and rebuild_contract_read.get("prerequisite_rebuild_command") == EXPECTED_REBUILD_ORDER_COMMANDS[0]
            and rebuild_contract_read.get("rebuild_command") == EXPECTED_REBUILD_ORDER_COMMANDS[1]
            and rebuild_contract_read.get("direct_validation_command") == EXPECTED_REBUILD_ORDER_COMMANDS[2]
            and rebuild_contract_read.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and rebuild_contract_read.get("requires_source_consistency_before_quoting_current_totals") is True
            and rebuild_contract_read.get("upstream_refresh_order_is_provenance_metadata_only") is True
            and rebuild_contract_read.get("not_settled_roi_or_real_money_evidence") is True,
            "current_evidence_rebuild_validation_contract_read",
            "working-status report now source-checks current_evidence_summary.json rebuild_validation_contract so dated report readers see the settlement-audit -> current-bridge -> current-bridge-validator order before quoting current bridge totals after source-byte changes, while keeping that route as provenance/rebuild metadata only",
        )
    )
    checks.append(
        require(
            expected_queue_context_line in report_text
            and "Current open-row context: `none`" not in report_text
            and "current open-row context: `none`" not in report_text,
            "source_published_settlement_queue_state",
            "working-status report consumes the bridge-published settlement queue state/context/detail and does not render a closed queue as open-row `none`",
        )
    )
    checks.append(
        require(
            "- direct cross-family caveat route: read `CROSS_FAMILY_DECISION.md` and run `python3 validate_cross_family_decision.py` when the question is whether the anchor / paper / watch shortlist still carries the current-paper caveat; stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green working-status validation are not OP-anchor proof or cross-family promotion evidence" in report_text,
            "cross_family_current_paper_route_present",
            "working-status report now routes anchor / paper / watch current-paper caveat questions to CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py and keeps stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green working-status validation out of OP-anchor proof or cross-family promotion evidence",
        )
    )
    checks.append(
        require(
            "- full-data XGBoost retrain caveat route: read `FULL_DATA_RETRAIN_ARTIFACTS.md` and run `python3 validate_full_data_retrain_artifacts.py` when checking the model lane's full-data retrain artifacts or exact retrain/prediction commands; large RMSE / MAE gains remain model-fit reproducibility context only, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in report_text,
            "full_data_retrain_caveat_route_present",
            "working-status report now routes model-lane full-data retrain artifact and exact retrain/prediction command questions to FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py while keeping large RMSE / MAE gains in model-fit reproducibility context only",
        )
    )
    checks.append(
        require(
            scorecard_gate_read["anchor_displacement_min_roi_complete_settled_observations"] == first_read["threshold"]
            and scorecard_gate_read["real_money_discussion_min_total_settled_observations_with_usable_roi"] == portfolio_review["threshold"]
            and scorecard_gate_read["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and scorecard_gate_read["real_money_no_baq_as_bel_required"] is True
            and f"`{SCORECARD_JSON.name}` `decision_gate_minimums` sets `anchor_displacement={scorecard_anchor_min}`, `phase8_promotion_review={scorecard_phase8_min}`, and `real_money_discussion={scorecard_real_money_min}`" in report_text
            and "future ROI-complete observation floors, not cleared gates" in report_text,
            "working_status_gate_source_matches_scorecard_json",
            "working-status report now source-matches its current-paper gate floors to forward_evidence_scorecard.json decision_gate_minimums and preserves the no-BAQ-as-BEL real-money prerequisite as gate metadata",
        )
    )
    checks.append(
        require(
            recommendation_read
            and recommendation_context.get("not_forward_performance_evidence") is True
            and recommendation_context.get("not_bet_readiness_evidence_by_itself") is True
            and (api_access_action_route_present if api_access_action_route_required else True)
            and expected_queue_context_line in report_text,
            "current_settlement_queue_recommendation_state_context",
            "working-status report now preserves the bridge-published settlement-queue state plus the latest recommendation-state context as workflow context rather than bet-ready or forward-performance proof",
        )
    )
    checks.append(
        require(
            expected_source_freshness_line in report_text
            and expected_source_repair_line in report_text
            and "source_freshness.requires_refresh_before_right_now_use" in report_text
            and "operator_read_gate.requires_refresh_before_evidence_read" in report_text
            and (not requires_refresh or "./run_daily_portfolio_observation.sh" in report_text),
            "current_evidence_combined_operator_read_route",
            "working-status report now carries the combined operator_status_context / source_freshness / operator_read_gate route, so refresh-required right-now cards trigger the daily wrapper and fresh cards stay in current operator-routing context before instruction or evidence use",
        )
    )
    checks.append(
        require(
            expected_operator_read_gate_line in report_text
            and operator_read_gate_json_read.get("source") == "current_evidence_summary.json"
            and operator_read_gate_json_read.get("source_path") == "operator_read_gate"
            and operator_read_gate_json_read.get("gate_status") in {
                "refresh_required_before_evidence_read",
                "current_operator_routing_context_only",
            }
            and operator_read_gate_json_read.get("valid_use") == "operator instruction/evidence-read gating only"
            and isinstance(operator_read_gate_json_read.get("requires_refresh_before_evidence_read"), bool)
            and isinstance(operator_read_gate_json_read.get("has_api_access_failure_context"), bool)
            and isinstance(operator_read_gate_json_read.get("has_scanner_failure_boundary"), bool)
            and isinstance(operator_read_gate_json_read.get("has_stale_cache_fallback_context"), bool)
            and isinstance(operator_read_gate_json_read.get("recommended_command"), str)
            and bool(operator_read_gate_json_read.get("recommended_command"))
            and operator_read_gate_json_read.get("current_top_card_counts_as_no_target_evidence") is False
            and operator_read_gate_json_read.get("current_top_card_counts_as_clean_empty_evidence") is False
            and operator_read_gate_json_read.get("current_top_card_counts_as_bet_readiness_evidence") is False
            and operator_read_gate_json_read.get("current_top_card_counts_as_settled_roi_evidence") is False
            and operator_read_gate_json_read.get("not_forward_performance_evidence") is True
            and operator_read_gate_json_read.get("not_promotion_readiness_evidence") is True
            and operator_read_gate_json_read.get("not_live_profitability_evidence") is True
            and operator_read_gate_json_read.get("not_real_money_evidence") is True,
            "current_evidence_operator_read_gate_route",
            "working-status report now carries current_evidence_summary.json operator_read_gate as refresh-before-evidence-read routing before stale, stale-cache fallback, or missing-state top-card instruction/evidence use, without treating that state as no-target, clean-empty, bet-readiness, settled-ROI, forward-performance, promotion, live-profitability, bankroll, or real-money evidence",
        )
    )
    checks.append(
        require(
            expected_command_block in report_text,
            "demo_command_block",
            "working-status report still shows the dated demo command used to prove the live/demo lane",
        )
    )
    checks.append(
        require(
            expected_snapshot in report_text,
            "report_time_snapshot",
            "working-status report now makes the report-time demo snapshot and the mutable latest-demo alias distinction explicit",
        )
    )
    checks.append(
        require(
            expected_operational_bottom_line in report_text,
            "operational_bottom_line",
            "working-status report still ends with the corrected operational read and explicitly frames the demo run as an operability check rather than an edge claim",
        )
    )
    checks.append(
        require(
            "Latest verified demo run:" not in report_text,
            "stale_latest_phrase_removed",
            "working-status report no longer uses the stale 'Latest verified demo run' wording for a dated historical snapshot",
        )
    )
    checks.append(
        require(
            'ACTIVE_TRACKS = {"OP": "Oaklawn Park", "CD": "Churchill Downs"}' in ops_text,
            "ops_active_tracks_still_op_cd",
            "superfecta_ops.py still defines the production basket as OP/CD, matching the report's distinction",
        )
    )
    checks.append(
        require(
            "--include-cards" in demo_text and "--save-latest-json" in demo_text,
            "demo_cli_flags_exist",
            "demo_live_predictions.py still exposes the include-cards and save-latest-json flags named in the report",
        )
    )
    checks.append(
        require_paths_exist(
            [
                DEMO_SCRIPT,
                OPS_SCRIPT,
                BASE / "out" / "live_demo" / "keeneland_race6_20260415_151943.csv",
                BASE / "out" / "live_demo" / "keeneland_race6_20260415_151943.md",
                BASE / "out" / "live_demo" / "latest_demo_run.json",
                CURRENT_EVIDENCE_MD,
                CURRENT_EVIDENCE_JSON,
                SCORECARD_JSON,
                CROSS_FAMILY_MD,
                CROSS_FAMILY_VALIDATOR,
                FULL_DATA_RETRAIN_MD,
                FULL_DATA_RETRAIN_VALIDATOR,
            ],
            "referenced_artifacts_exist",
            "the dated working-status note still points at real demo and ops artifacts on disk",
        )
    )

    suite_read = (
        "working-status report stays honest: superfecta_ops remains an OP/CD production-basket wrapper, "
        "demo_live_predictions remains a separate live/demo lane, the 2026-04-15 Keeneland CSV/markdown files stay the dated evidence anchor, "
        "the demo run is explicitly framed as an operability check rather than a profitability/deployment claim, "
        "new forward evidence still requires settled paper trades in the actual paper-trade lane, "
        "the production-wrapper wording now says primary paper-basket target tracks rather than stale basket-status shorthand, "
        f"current paper totals route through CURRENT_EVIDENCE_SUMMARY.md/current_evidence_summary.json with source consistency {source_consistency_label}, "
        "rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only, "
        f"combined operator-status/source-freshness/operator-read-gate route {combined_operator_route_label}, "
        "report gates source-matched to forward_evidence_scorecard.json decision_gate_minimums, "
        f"primary paper {first_read['current']}/{first_read['threshold']} first-read and {portfolio_review['current']}/{portfolio_review['threshold']} broader-review gates, "
        f"CD_CORE_K8={rule_progress['CD_CORE_K8']['roi_complete_settled_rows']} ROI-complete rows, OP_DURABLE_K7={rule_progress['OP_DURABLE_K7']['roi_complete_settled_rows']} ROI-complete rows, "
        "the current settled sample is CD-only context and not OP-anchor evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence, "
        "direct cross-family current-paper caveat route=CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py, with stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green working-status validation not OP-anchor proof or cross-family promotion evidence, "
        "full-data retrain caveat route=FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py, with large RMSE / MAE gains and exact retrain/prediction commands kept as model-fit reproducibility context rather than paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence, "
        f"{suite_queue_context}, "
        f"operator_read_gate read={operator_read_gate_read}, "
        "and latest_demo_run.json is explicitly treated as a mutable convenience alias"
    )

    payload = {
        "suite_status": "pass",
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "scorecard_decision_gate_minimums_read": scorecard_gate_read,
        "current_evidence_operator_read_gate_read": operator_read_gate_json_read,
        "current_evidence_rebuild_validation_contract_read": rebuild_contract_read,
        "summary": {
            "suite_read": suite_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }

    lines = [
        "# Working Status Report Validation",
        "",
        "This report checks that `WORKING_STATUS_REPORT_2026-04-15.md` keeps the dated live/demo proof separate from the OP/CD production basket, treats the demo run as operability proof rather than profitability proof, and treats mutable demo aliases honestly.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Target file: `{REPORT.name}`",
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
            "## Current Read",
            "",
            f"- Suite read: {suite_read}",
            "- Production basket line: `ACTIVE_TRACKS = {\"OP\": \"Oaklawn Park\", \"CD\": \"Churchill Downs\"}`",
            "- Dated evidence anchor: `out/live_demo/keeneland_race6_20260415_151943.csv` and `out/live_demo/keeneland_race6_20260415_151943.md`",
            "- Mutable alias: `out/live_demo/latest_demo_run.json`",
            f"- Current paper bridge: `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` ({source_consistency_label}; {source_freshness_label}; primary paper {first_read['current']}/{first_read['threshold']} first-read and {portfolio_review['current']}/{portfolio_review['threshold']} broader-review gates; CD_CORE_K8={rule_progress['CD_CORE_K8']['roi_complete_settled_rows']}, OP_DURABLE_K7={rule_progress['OP_DURABLE_K7']['roi_complete_settled_rows']})",
            "- Current evidence rebuild order: `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`",
            f"- Current evidence operator-read-gate read: {operator_read_gate_read}",
            f"- Scorecard gate source: `{SCORECARD_JSON.name}` `decision_gate_minimums` (`anchor_displacement={scorecard_anchor_min}`, `phase8_promotion_review={scorecard_phase8_min}`, `real_money_discussion={scorecard_real_money_min}`)",
            f"- Direct cross-family caveat route: `{CROSS_FAMILY_MD.name}` plus `{CROSS_FAMILY_VALIDATOR.name}`; green working-status validation is not OP-anchor proof or cross-family promotion evidence.",
            f"- Full-data retrain caveat route: `{FULL_DATA_RETRAIN_MD.name}` plus `{FULL_DATA_RETRAIN_VALIDATOR.name}`; large RMSE / MAE gains and exact retrain/prediction commands stay model-fit reproducibility context only.",
            expected_queue_context_line,
            "",
            "## Sources",
            "",
            f"- `{REPORT.name}`",
            f"- `{DEMO_SCRIPT.name}`",
            f"- `{OPS_SCRIPT.name}`",
            f"- `{CURRENT_EVIDENCE_MD.name}`",
            f"- `{CURRENT_EVIDENCE_JSON.name}`",
            f"- `{SCORECARD_JSON.name}`",
            f"- `{CROSS_FAMILY_MD.name}`",
            f"- `{CROSS_FAMILY_VALIDATOR.name}`",
            f"- `{FULL_DATA_RETRAIN_MD.name}`",
            f"- `{FULL_DATA_RETRAIN_VALIDATOR.name}`",
        ]
    )

    out_dir = Path(args.out_dir)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name
    out_dir.mkdir(parents=True, exist_ok=True)

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
