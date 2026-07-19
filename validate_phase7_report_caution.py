#!/usr/bin/env python3
"""
Validation for the Phase 7 legacy discovery report caution boundary.

Purpose:
- keep the strongest historical Phase 7 candidate-family report from being read as a current deployment guide by itself
- preserve the OP_DURABLE_K7 / CD_CORE_K8 / OP_REFINED_K7 current posture routed through the frozen scorecard and paper-observation lane
- prevent dormant BEL, Kelly, historical cost/handle/profit, or old automation wording from becoming real-money or live-profitability guidance
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
REPORT = BASE / "PHASE7_REPORT.md"
GENERATOR = BASE / "backtest_phase7.py"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
OUT_DIR = BASE / "out" / "status_validation" / "phase7_report_caution"
OUT_MD = OUT_DIR / "phase7_report_caution_validation.md"
OUT_JSON = OUT_DIR / "phase7_report_caution_validation.json"
REBUILD_COMMAND = "python3 validate_phase7_report_caution.py"
VALID_EVIDENCE_SCOPE = "legacy_phase7_discovery_context_only"
REQUIRED_REBUILD_REFRESH_ORDER = [
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
    parser = argparse.ArgumentParser(description="Validate PHASE7_REPORT.md caution wording")
    parser.add_argument("--current-evidence-json", type=Path, default=CURRENT_EVIDENCE_JSON)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def current_rebuild_validation_contract_context(current_evidence_json: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    payload = json.loads(Path(current_evidence_json).read_text(encoding="utf-8"))
    contract = payload.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise AssertionError("current_evidence_summary.json must publish rebuild_validation_contract as an object")
    order = contract.get("upstream_refresh_order")
    if not isinstance(order, list):
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order must be a list")
    commands: list[str] = []
    for expected_order, row in enumerate(order, start=1):
        if not isinstance(row, dict):
            raise AssertionError("current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order row drifted")
        if row.get("order") != expected_order:
            raise AssertionError("current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order order drifted")
        command = str(row.get("command") or "")
        reason = str(row.get("reason") or "")
        if not command or not reason:
            raise AssertionError("current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order row is incomplete")
        commands.append(command)
    if commands != REQUIRED_REBUILD_REFRESH_ORDER:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract upstream order drifted")
    required_values = {
        "prerequisite_rebuild_command": "python3 paper_trade_settlement_audit.py",
        "rebuild_command": "python3 current_evidence_summary.py",
        "direct_validation_command": "python3 validate_current_evidence_summary.py",
    }
    for key, expected_value in required_values.items():
        if contract.get(key) != expected_value:
            raise AssertionError(f"current_evidence_summary.json rebuild_validation_contract.{key} drifted")
    required_true_flags = [
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
        "requires_source_consistency_before_quoting_current_totals",
        "green_checks_are_reproducibility_metadata_only",
        "upstream_refresh_order_is_provenance_metadata_only",
        "not_settled_roi_or_real_money_evidence",
    ]
    weakened = [flag for flag in required_true_flags if contract.get(flag) is not True]
    if weakened:
        raise AssertionError(
            "current_evidence_summary.json rebuild_validation_contract must mark "
            + ", ".join(weakened)
            + "=true"
        )
    return {
        "source": Path(current_evidence_json).name,
        "source_path": "rebuild_validation_contract",
        "upstream_refresh_commands": commands,
        "prerequisite_rebuild_command": contract["prerequisite_rebuild_command"],
        "rebuild_command": contract["rebuild_command"],
        "direct_validation_command": contract["direct_validation_command"],
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": contract[
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
        ],
        "requires_source_consistency_before_quoting_current_totals": contract[
            "requires_source_consistency_before_quoting_current_totals"
        ],
        "green_checks_are_reproducibility_metadata_only": contract["green_checks_are_reproducibility_metadata_only"],
        "upstream_refresh_order_is_provenance_metadata_only": contract[
            "upstream_refresh_order_is_provenance_metadata_only"
        ],
        "not_settled_roi_or_real_money_evidence": contract["not_settled_roi_or_real_money_evidence"],
    }


def current_bridge_cli_contract_checks(current_evidence_json: Path = CURRENT_EVIDENCE_JSON) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="phase7_report_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "phase7_report_caution_validation"
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
            "validate_phase7_report_caution.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial Phase 7 report-validation artifacts",
        ))

        weakened_contract_out_dir = tmp_root / "weakened" / "phase7_report_caution_validation"
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
            and "current_evidence_summary.json rebuild_validation_contract must mark upstream_refresh_order_is_provenance_metadata_only=true"
            in proc.stderr,
            "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
            "validate_phase7_report_caution.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial Phase 7 report-validation artifacts",
        ))

    return checks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name
    text = REPORT.read_text(encoding="utf-8")
    generator_text = GENERATOR.read_text(encoding="utf-8")
    first_25 = "\n".join(text.splitlines()[:25])
    rebuild_contract = current_rebuild_validation_contract_context(Path(args.current_evidence_json))

    checks: list[dict[str, Any]] = []
    checks.extend(current_bridge_cli_contract_checks(Path(args.current_evidence_json)))
    checks.append(require(
        rebuild_contract["upstream_refresh_commands"] == REQUIRED_REBUILD_REFRESH_ORDER
        and rebuild_contract["upstream_refresh_order_is_provenance_metadata_only"] is True
        and rebuild_contract["not_settled_roi_or_real_money_evidence"] is True,
        "current_evidence_rebuild_validation_contract_read",
        "Phase 7 caution validation reads current_evidence_summary.json.rebuild_validation_contract before writing artifacts and keeps the rebuild order as provenance metadata only",
    ))
    checks.append(require(
        "## Current Evidence Boundary" in first_25
        and "historical Phase 7 discovery report" in first_25
        and "not the current deployment guide by itself" in first_25,
        "top_current_evidence_boundary_present",
        "PHASE7_REPORT opens with a current-evidence boundary before the original executive summary",
    ))
    checks.append(require(
        f"- Valid evidence scope: `valid_evidence_scope={VALID_EVIDENCE_SCOPE}`." in first_25
        and f'VALID_EVIDENCE_SCOPE = "{VALID_EVIDENCE_SCOPE}"' in generator_text
        and "valid_evidence_scope={VALID_EVIDENCE_SCOPE}" in generator_text,
        "phase7_report_valid_evidence_scope_visible",
        "PHASE7_REPORT.md and backtest_phase7.py expose the raw valid_evidence_scope line so the Phase 7 discovery report stays legacy context only",
    ))
    checks.append(require(
        "`OP_DURABLE_K7` remains the safest anchor" in first_25
        and "`CD_CORE_K8` remains the primary OP/CD paper companion" in first_25
        and "`OP_REFINED_K7` plus other Phase 8 rules remain shadow/watch" in first_25,
        "current_anchor_companion_watch_posture_visible",
        "top boundary routes current posture through the scorecard / comparison / paper-observation lane rather than the old full three-track headline alone",
    ))
    checks.append(require(
        "The full three-track Phase 7 result includes dormant `BEL` history" in first_25
        and "`BAQ` must not be substituted for `BEL`" in first_25,
        "bel_dormant_and_baq_boundary_visible",
        "top boundary makes dormant BEL and no-BAQ-as-BEL explicit before BEL-heavy historical sections",
    ))
    checks.append(require(
        "Wagered" in first_25
        and "Cost" in first_25
        and "Expected" in first_25
        and "Kelly" in first_25
        and "paper-accounting metadata only" in first_25
        and "real-money authorization" in first_25,
        "cost_kelly_profit_lines_labeled_metadata",
        "top boundary labels historical cost, expected-volume, Kelly, and profit wording as frozen backtest / paper-accounting metadata only",
    ))
    checks.append(require(
        "Validate this boundary with `python3 validate_phase7_report_caution.py`." in first_25,
        "direct_validator_route_present",
        "PHASE7_REPORT names its direct caution validator in the top boundary",
    ))
    checks.append(require(
        "### Automation Guidance — paper observation only" in text
        and "log the race through the paper-trade lane" in text
        and "do not place, size, bankroll, stop-loss, or scale real-money bets from this report" in text
        and "If all filters pass, place the $2 Key-1-with-7 superfecta" not in text,
        "automation_guidance_is_paper_observation_only",
        "automation guidance no longer tells readers to place a bet and instead routes qualifying races into paper observation",
    ))
    checks.append(require(
        "### Risk Boundary" in text
        and "Kelly / bankroll calculations from the historical replay are intentionally not used as operating instructions here." in text
        and "Real-money discussion requires a separate human-approved risk memo after 100+ total ROI-complete paper observations" in text,
        "risk_boundary_blocks_bankroll_and_real_money_overread",
        "later risk section blocks Kelly/bankroll/real-money interpretation and names the 100-row review floor",
    ))
    checks.append(require(
        "## Current Evidence Boundary" in generator_text
        and "validate_phase7_report_caution.py" in generator_text
        and "log the race through the paper-trade lane" in generator_text
        and "If all filters pass, place the $2 Key-1-with-7 superfecta" not in generator_text,
        "generator_emits_same_boundary_and_paper_only_guidance",
        "backtest_phase7.py now regenerates the top boundary and cannot recreate the old direct-bet automation line",
    ))

    current_read = (
        f"PHASE7_REPORT now opens with a current-evidence boundary and valid_evidence_scope={VALID_EVIDENCE_SCOPE}, and the generator emits the same caution: "
        "Phase 7 remains strongest historical candidate-family context, but current posture still comes from the frozen scorecard and paper-observation lane; "
        "OP_DURABLE_K7 stays anchor, CD_CORE_K8 stays the paper companion, OP_REFINED_K7 and Phase 8 stay shadow/watch, dormant BEL is not BAQ, "
        "and cost/Kelly/historical profit lines are backtest or paper-accounting metadata only, not live-profitability, promotion, bankroll, or real-money evidence; "
        "current bridge rebuild order is read from current_evidence_summary.json.rebuild_validation_contract as provenance metadata only before this validator writes artifacts."
    )
    payload: dict[str, Any] = {
        "suite": "phase7_report_caution",
        "suite_status": "pass",
        "total_checks": len(checks),
        "check_count": len(checks),
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "report_path": rel(OUT_MD),
        "source_report": rel(REPORT),
        "source_generator": rel(GENERATOR),
        "rebuild_command": REBUILD_COMMAND,
        "current_read": current_read,
        "current_evidence_rebuild_validation_contract_read": rebuild_contract,
        "summary": {
            "current_read": current_read,
            "suite_read": current_read,
        },
        "evidence_boundary": {
            "artifact_role": "Phase 7 legacy discovery report caution validator",
            "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
            "valid_use": "historical Phase 7 discovery context wording-drift validation",
            "not_current_deployment_guide": True,
            "not_live_paper_trade_ledger": True,
            "not_settled_roi_evidence": True,
            "not_live_profitability_evidence": True,
            "not_promotion_readiness_evidence": True,
            "not_bankroll_guidance": True,
            "not_real_money_evidence": True,
            "no_baq_as_bel": True,
        },
        "checks": checks,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    md_lines = [
        "# Phase 7 Report Caution Validation",
        "",
        f"Status: **{payload['suite_status'].upper()}**",
        f"Checks: **{len(checks)}/{len(checks)}**",
        f"Source report: `{rel(REPORT)}`",
        f"Source generator: `{rel(GENERATOR)}`",
        f"Rebuild command: `{REBUILD_COMMAND}`",
        f"- valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
        "",
        "## Current read",
        "",
        current_read,
        "",
        "## Checks",
        "",
    ]
    for check in checks:
        md_lines.append(f"- `{check['check']}` — {check['detail']}")
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
