#!/usr/bin/env python3
"""
Validation for EV_TICKET_ENGINE_USAGE.md caution wording.

Purpose:
- keep the EV ticket-engine usage note in paper-trade/debugging status
- prevent standalone EV sizing examples from becoming bankroll or real-money instructions
- preserve the current OP/CD/shadow posture plus no-BAQ-as-BEL boundary
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
DOC = BASE / "EV_TICKET_ENGINE_USAGE.md"
ENGINE = BASE / "ev_ticket_engine.py"
ENGINE_VALIDATOR = BASE / "validate_ev_ticket_engine.py"
DAILY_WRAPPER = BASE / "run_daily_portfolio_observation.sh"
RECOMMENDER = BASE / "paper_trade_recommender.py"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
OUT_DIR = BASE / "out" / "status_validation" / "ev_ticket_engine_usage"
OUT_MD = OUT_DIR / "ev_ticket_engine_usage_validation.md"
OUT_JSON = OUT_DIR / "ev_ticket_engine_usage_validation.json"
REBUILD_COMMAND = "python3 validate_ev_ticket_engine_usage.py"
VALID_EVIDENCE_SCOPE = "ev_ticket_engine_usage_source_layer_runbook_navigation_only"
EXPECTED_REBUILD_ORDER_COMMANDS = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]


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
    parser = argparse.ArgumentParser(description="Validate the EV ticket-engine usage boundary")
    parser.add_argument("--current-evidence-json", type=Path, default=CURRENT_EVIDENCE_JSON)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def load_current_evidence_rebuild_contract(current_evidence_json: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    payload = json.loads(Path(current_evidence_json).read_text(encoding="utf-8"))
    contract = payload.get("rebuild_validation_contract")
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
        raise AssertionError("rebuild_validation_contract upstream order must be provenance metadata only")
    if contract.get("not_settled_roi_or_real_money_evidence") is not True:
        raise AssertionError("rebuild_validation_contract must not be settled ROI or real-money evidence")

    return {
        "source": Path(current_evidence_json).name,
        "source_path": "rebuild_validation_contract",
        "upstream_refresh_order_commands": commands,
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


def current_bridge_cli_contract_checks(current_evidence_json: Path = CURRENT_EVIDENCE_JSON) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="ev_ticket_engine_usage_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "ev_ticket_engine_usage_validation"
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
            "validate_ev_ticket_engine_usage.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial EV usage validation artifacts",
        ))

        weakened_contract_out_dir = tmp_root / "weakened" / "ev_ticket_engine_usage_validation"
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
            and "rebuild_validation_contract upstream order must be provenance metadata only" in proc.stderr,
            "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
            "validate_ev_ticket_engine_usage.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial EV usage validation artifacts",
        ))

    return checks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name

    text = DOC.read_text(encoding="utf-8")
    first_35 = "\n".join(text.splitlines()[:35])
    rebuild_contract = load_current_evidence_rebuild_contract(Path(args.current_evidence_json))

    checks: list[dict[str, Any]] = []
    checks.extend(current_bridge_cli_contract_checks(Path(args.current_evidence_json)))
    checks.append(require(
        "## Current Evidence Boundary" in first_35
        and "source-layer paper-trade/debugging runbook" in first_35
        and "not the daily operating path by itself" in first_35,
        "top_current_evidence_boundary_present",
        "EV usage opens with a current-evidence boundary before the operational examples",
    ))
    checks.append(require(
        f"- Valid evidence scope: `valid_evidence_scope={VALID_EVIDENCE_SCOPE}`." in first_35
        and VALID_EVIDENCE_SCOPE.endswith("_navigation_only"),
        "ev_usage_valid_evidence_scope_visible",
        "EV usage now exposes exact valid_evidence_scope=ev_ticket_engine_usage_source_layer_runbook_navigation_only so copied source-layer sizing examples stay framed as runbook navigation metadata only",
    ))
    checks.append(require(
        "`./run_daily_portfolio_observation.sh`" in first_35
        and "`paper_trade_recommender.py`" in first_35
        and "after Phase 7 combo filtering" in first_35,
        "preferred_daily_route_visible",
        "top boundary routes daily use through the wrapper and recommender before the EV engine",
    ))
    checks.append(require(
        "hypothetical paper-ticket plan" in first_35
        and "not live profitability evidence" in first_35
        and "promotion readiness" in first_35
        and "bankroll guidance" in first_35
        and "real-money authorization" in first_35,
        "bet_decision_labeled_paper_only",
        "top boundary prevents a BET decision from being read as live-profitability, promotion, bankroll, or real-money evidence",
    ))
    checks.append(require(
        "`OP_DURABLE_K7` as the safest anchor" in first_35
        and "`CD_CORE_K8` as the primary OP/CD paper companion" in first_35
        and "`OP_REFINED_K7` plus other Phase 8 rules in shadow/watch" in first_35,
        "current_hierarchy_visible",
        "top boundary preserves the current anchor / paper-companion / shadow hierarchy",
    ))
    checks.append(require(
        "substitute `BAQ` for dormant `BEL`" in first_35
        and "widen the live combo universe" in first_35,
        "no_baq_as_bel_and_no_widening_boundary",
        "top boundary blocks BAQ-as-BEL substitution and standalone live-universe widening",
    ))
    checks.append(require(
        "Validate this usage boundary with `python3 validate_ev_ticket_engine_usage.py`." in first_35,
        "direct_validator_route_present",
        "EV usage note names its direct usage-boundary validator",
    ))
    checks.append(require(
        "`current_evidence_summary.json.rebuild_validation_contract`" in first_35
        and "`python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`" in first_35
        and "provenance/rebuild routing only" in first_35
        and "not EV-engine evidence, settled ROI, bankroll guidance, or real-money evidence" in first_35
        and rebuild_contract["upstream_refresh_order_commands"] == EXPECTED_REBUILD_ORDER_COMMANDS
        and rebuild_contract["requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"] is True
        and rebuild_contract["requires_source_consistency_before_quoting_current_totals"] is True
        and rebuild_contract["upstream_refresh_order_is_provenance_metadata_only"] is True
        and rebuild_contract["not_settled_roi_or_real_money_evidence"] is True,
        "current_evidence_rebuild_contract_route_visible",
        "top boundary routes source-byte changes through current_evidence_summary.json.rebuild_validation_contract and keeps the three-command order as provenance metadata only",
    ))
    checks.append(require(
        "Preferred daily use is indirect: run `./run_daily_portfolio_observation.sh`" in text
        and "direct commands below are for source-layer debugging or reproducibility checks, not real-money placement" in text,
        "recommended_workflow_is_indirect_daily_use",
        "recommended workflow now separates daily observation from direct source-layer debugging commands",
    ))
    checks.append(require(
        "For EV paper-ticket sizing" in text
        and "## 2) Turn predictions into a paper bet / no-bet plan" in text
        and "Example with a $500 paper-accounting fixture and dime minimums:" in text
        and "A paper ticket is playable only if all of these are true:" in text
        and "For EV betting" not in text
        and "Example with a $500 bankroll" not in text,
        "lower_workflow_uses_paper_ticket_language",
        "lower workflow sections now label direct sizing as paper-ticket / paper-accounting fixture usage rather than EV betting or bankroll guidance",
    ))
    checks.append(require(
        '--race-label "OP Paper Race 7"' in text
        and '--race-label "BEL Race 7"' not in text,
        "example_race_label_avoids_dormant_bel",
        "direct example avoids using dormant BEL as the label for an EV sizing example",
    ))
    checks.append(require(
        "bankroll = `$500` paper-accounting fixture default, not an authorized bankroll" in text,
        "default_bankroll_labeled_fixture_only",
        "default bankroll amount is labeled as a paper-accounting fixture default rather than an authorized bankroll",
    ))
    checks.append(require(
        "`Decision: BET` means at least one hypothetical paper ticket survived all filters and caps." in text
        and "paper-observation discipline" in text,
        "interpretation_keeps_bet_as_paper_ticket",
        "interpretation section keeps BET as a hypothetical paper-ticket result",
    ))
    checks.append(require(
        "more disciplined than ranking paper tickets straight off raw payout predictions" in text
        and "betting straight off raw payout predictions" not in text,
        "limitations_avoid_direct_betting_claim",
        "limitations section avoids implying the engine is a better live-betting instruction",
    ))
    checks.append(require(
        all(path.exists() for path in [DOC, ENGINE, ENGINE_VALIDATOR, DAILY_WRAPPER, RECOMMENDER, CURRENT_EVIDENCE_JSON]),
        "referenced_source_layer_files_exist",
        "usage note references real wrapper, recommender, EV engine, direct EV validator, and current-evidence JSON files",
    ))

    current_read = (
        "EV_TICKET_ENGINE_USAGE.md is validated as source-layer paper-trade/debugging guidance: "
        "daily use still routes through run_daily_portfolio_observation.sh and paper_trade_recommender.py, "
        f"the runbook publishes exact valid_evidence_scope={VALID_EVIDENCE_SCOPE} as source-layer navigation metadata only, "
        "source-byte changes before quoting CURRENT_EVIDENCE_SUMMARY.* route through current_evidence_summary.json.rebuild_validation_contract with "
        "python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py as provenance/rebuild metadata only, "
        "BET means hypothetical paper-ticket plan only, OP_DURABLE_K7 stays anchor, CD_CORE_K8 stays paper companion, "
        "OP_REFINED_K7 and Phase 8 stay shadow/watch, BAQ is not BEL, and fixture bankroll/stake examples are not live-profitability, "
        "promotion, bankroll, or real-money evidence."
    )
    payload: dict[str, Any] = {
        "suite": "ev_ticket_engine_usage",
        "suite_status": "pass",
        "total_checks": len(checks),
        "check_count": len(checks),
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "source_doc": rel(DOC),
        "report_path": rel(OUT_MD),
        "rebuild_command": REBUILD_COMMAND,
        "current_evidence_rebuild_validation_contract_read": rebuild_contract,
        "current_read": current_read,
        "summary": {
            "current_read": current_read,
            "suite_read": current_read,
        },
        "evidence_boundary": {
            "artifact_role": "EV ticket-engine usage-boundary validator",
            "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
            "valid_use": "paper-trade/source-layer usage wording validation",
            "not_new_forward_evidence": True,
            "not_live_paper_trade_ledger": True,
            "not_current_day_scanner_result": True,
            "not_settled_roi_evidence": True,
            "not_promotion_readiness_evidence": True,
            "not_live_profitability_evidence": True,
            "not_bankroll_guidance": True,
            "not_real_money_evidence": True,
            "no_baq_as_bel": True,
        },
        "checks": checks,
    }

    md_lines = [
        "# EV Ticket Engine Usage Validation",
        "",
        f"Status: **{payload['suite_status'].upper()}**",
        f"Checks: **{len(checks)}/{len(checks)}**",
        f"Source doc: `{rel(DOC)}`",
        f"Rebuild command: `{REBUILD_COMMAND}`",
        f"- valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
        "",
        "## Current Read",
        "",
        current_read,
        "",
        "## Checks",
        "",
    ]
    for check in checks:
        md_lines.append(f"- `{check['check']}` - {check['detail']}")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
