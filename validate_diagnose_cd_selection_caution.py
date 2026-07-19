#!/usr/bin/env python3
"""
Validation for DIAGNOSE_CD_SELECTION.md current-evidence boundaries.

Purpose:
- keep the CD selector diagnostic framed as frozen replay research
- prevent the Always-CD_CORE and No-CD counterfactuals from being read as new expected ROI
- preserve the OP_DURABLE / CD_CORE / OP_REFINED posture and no-BAQ-as-BEL boundary
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
REPORT = BASE / "DIAGNOSE_CD_SELECTION.md"
GENERATOR = BASE / "diagnose_cd_selection.py"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
OUT_DIR = BASE / "out" / "status_validation" / "diagnose_cd_selection_caution"
OUT_MD = OUT_DIR / "diagnose_cd_selection_caution_validation.md"
OUT_JSON = OUT_DIR / "diagnose_cd_selection_caution_validation.json"
REBUILD_COMMAND = "python3 validate_diagnose_cd_selection_caution.py"
VALID_EVIDENCE_SCOPE = "cd_track_group_selector_replay_diagnostic_only"
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
    parser = argparse.ArgumentParser(description="Validate DIAGNOSE_CD_SELECTION.md caution wording")
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
    with TemporaryDirectory(prefix="diagnose_cd_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "diagnose_cd_selection_caution"
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
            "validate_diagnose_cd_selection_caution.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial CD diagnostic validation artifacts",
        ))

        weakened_contract_out_dir = tmp_root / "weakened" / "diagnose_cd_selection_caution"
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
            "validate_diagnose_cd_selection_caution.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial CD diagnostic validation artifacts",
        ))

    return checks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name
    text = REPORT.read_text(encoding="utf-8")
    generator_text = GENERATOR.read_text(encoding="utf-8")
    first_32 = "\n".join(text.splitlines()[:32])
    rebuild_contract = current_rebuild_validation_contract_context(Path(args.current_evidence_json))
    rebuild_line = (
        "If this CD diagnostic is regenerated after scorecard/rules/signals/settlement-ledger byte changes, follow "
        "`current_evidence_summary.json.rebuild_validation_contract`: "
        f"`{'` -> `'.join(rebuild_contract['upstream_refresh_commands'])}`; "
        "this rebuild route is provenance metadata only, not settled ROI, promotion readiness, "
        "live profitability, bankroll guidance, or real-money evidence."
    )

    checks: list[dict[str, Any]] = []
    checks.extend(current_bridge_cli_contract_checks(Path(args.current_evidence_json)))
    checks.append(require(
        rebuild_contract["upstream_refresh_commands"] == REQUIRED_REBUILD_REFRESH_ORDER
        and rebuild_contract["upstream_refresh_order_is_provenance_metadata_only"] is True
        and rebuild_contract["not_settled_roi_or_real_money_evidence"] is True,
        "current_evidence_rebuild_validation_contract_read",
        "CD diagnostic validation reads current_evidence_summary.json.rebuild_validation_contract before writing artifacts and keeps the rebuild order as provenance metadata only",
    ))
    checks.append(require(
        "## Current Evidence Boundary" in first_32
        and "historical CD track-group selector diagnostic on frozen walk-forward artifacts" in first_32,
        "current_evidence_boundary_present",
        "CD selection diagnostic opens with a current-evidence boundary before the problem statement",
    ))
    checks.append(require(
        f"Valid evidence scope: `valid_evidence_scope={VALID_EVIDENCE_SCOPE}`." in first_32
        and f'VALID_EVIDENCE_SCOPE = "{VALID_EVIDENCE_SCOPE}"' in generator_text
        and "valid_evidence_scope={VALID_EVIDENCE_SCOPE}" in generator_text,
        "diagnose_cd_selection_valid_evidence_scope_visible",
        "DIAGNOSE_CD_SELECTION.md and diagnose_cd_selection.py expose the raw valid_evidence_scope line so the CD selector replay stays diagnostic context only",
    ))
    checks.append(require(
        "not a live paper-trade ledger" in first_32
        and "settled ROI evidence" in first_32
        and "promotion readiness" in first_32
        and "live profitability" in first_32
        and "bankroll guidance" in first_32
        and "real-money evidence" in first_32,
        "not_live_or_real_money_evidence",
        "top boundary blocks settled ROI, promotion, live-profitability, bankroll, and real-money overreads",
    ))
    checks.append(require(
        "Valid use: explain why the train-only selector tends to pick `CD_REFINED_K9` over `CD_CORE_K8`" in first_32
        and "The `Always CD_CORE` and `No CD rule` rows are replay diagnostics" in first_32
        and "not current deployment instructions or a new expected ROI range" in first_32,
        "counterfactuals_labeled_replay_diagnostics",
        "top boundary keeps Always-CD_CORE and No-CD rows in selector-diagnostic context",
    ))
    checks.append(require(
        "keep `OP_DURABLE_K7` as the safest anchor" in first_32
        and "`CD_CORE_K8` as the primary OP/CD paper companion" in first_32
        and "`OP_REFINED_K7` plus Phase 8 in shadow/watch" in first_32
        and "ROI-complete paper evidence clears the scorecard gates" in first_32,
        "current_operator_posture_visible",
        "top boundary preserves the scorecard-backed anchor / companion / shadow posture",
    ))
    checks.append(require(
        "do not override the +22.46% train-only benchmark" in first_32
        and "the realistic +20-25% planning range" in first_32
        and "settled-observation requirements" in first_32
        and "Do not substitute `BAQ` for dormant `BEL`" in first_32,
        "benchmark_planning_range_and_baq_boundary_visible",
        "top boundary blocks using the counterfactual replay as a replacement expected-ROI range or BAQ/BEL bridge",
    ))
    checks.append(require(
        rebuild_line in first_32
        and "If this CD diagnostic is regenerated after scorecard/rules/signals/settlement-ledger byte changes" in generator_text
        and "current_evidence_summary.json.rebuild_validation_contract" in generator_text
        and "python3 paper_trade_settlement_audit.py" in generator_text
        and "python3 current_evidence_summary.py" in generator_text
        and "python3 validate_current_evidence_summary.py" in generator_text
        and "this rebuild route" in generator_text
        and "is provenance metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance" in generator_text,
        "current_bridge_rebuild_route_visible",
        "CD diagnostic report and generator publish the settlement-audit -> current-bridge -> bridge-validator route as provenance metadata only",
    ))
    checks.append(require(
        "Validate this boundary with `python3 validate_diagnose_cd_selection_caution.py`." in first_32,
        "direct_validator_route_present",
        "report names the direct caution validator in the top boundary",
    ))
    checks.append(require(
        "| Actual selector | $78,108 | $17,541.35 | +22.46% | 8/10 |" in text
        and "| Always CD_CORE | $108,726 | $39,361.89 | +36.20% | 9/10 |" in text
        and "| No CD rule | $49,296 | $27,484.50 | +55.75% | 8/10 |" in text
        and "The `No CD rule` row is a stress-test comparator only; it is not a recommendation to remove `CD_CORE_K8`" in text,
        "counterfactual_table_preserved_but_no_cd_bounded",
        "report preserves the key replay comparison while bounding the tempting No-CD row",
    ))
    checks.append(require(
        "meaningful replay diagnostic" in text
        and "It is not a fresh expected-ROI estimate." in text
        and "not a new expected portfolio ROI or a replacement for the scorecard's planning range" in text
        and "honest number with the correct CD choice is closer" not in text
        and "selector bug" not in text,
        "interpretation_avoids_new_expected_roi_claim",
        "interpretation now frames the improvement as selector-mechanism debt, not a new honest ROI or bug-fix promise",
    ))
    checks.append(require(
        "## Current Evidence Boundary" in generator_text
        and "validate_diagnose_cd_selection_caution.py" in generator_text
        and "not current deployment instructions or a new expected ROI range" in generator_text
        and "Do not substitute `BAQ` for dormant `BEL`" in generator_text,
        "generator_preserves_boundary",
        "diagnose_cd_selection.py will regenerate the same current-evidence boundary",
    ))

    current_read = (
        f"DIAGNOSE_CD_SELECTION.md is validated as frozen CD selector research with valid_evidence_scope={VALID_EVIDENCE_SCOPE}: Always-CD_CORE improves the historical replay "
        "from +22.46% to +36.20%, and No-CD is preserved only as a stress-test comparator, but neither row is a new expected ROI, "
        "deployment instruction, promotion signal, live-profitability claim, bankroll guide, real-money evidence, or BAQ/BEL bridge; "
        "the current bridge rebuild order is read from current_evidence_summary.json.rebuild_validation_contract as provenance metadata only; "
        "current posture remains OP_DURABLE_K7 anchor, CD_CORE_K8 paper companion, and OP_REFINED_K7 / Phase 8 shadow-watch until settled paper gates clear."
    )

    payload: dict[str, Any] = {
        "suite": "diagnose_cd_selection_caution",
        "suite_status": "pass",
        "total_checks": len(checks),
        "check_count": len(checks),
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "source_report": rel(REPORT),
        "source_generator": rel(GENERATOR),
        "report_path": rel(out_md),
        "rebuild_command": REBUILD_COMMAND,
        "current_read": current_read,
        "current_evidence_rebuild_validation_contract_read": rebuild_contract,
        "summary": {
            "current_read": current_read,
            "suite_read": current_read,
        },
        "evidence_boundary": {
            "artifact_role": "CD selector diagnostic caution validator",
            "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
            "valid_use": "historical CD selector replay wording-drift validation",
            "not_new_forward_evidence": True,
            "not_live_paper_trade_ledger": True,
            "not_current_day_scanner_result": True,
            "not_settled_roi_evidence": True,
            "not_live_profitability_evidence": True,
            "not_promotion_readiness_evidence": True,
            "not_bankroll_guidance": True,
            "not_real_money_evidence": True,
            "no_baq_as_bel": True,
            "current_bridge_rebuild_order_is_provenance_metadata_only": True,
        },
        "checks": checks,
    }

    md_lines = [
        "# CD Selection Diagnostic Caution Validation",
        "",
        f"Status: **{payload['suite_status'].upper()}**",
        f"Checks: **{len(checks)}/{len(checks)}**",
        f"Source report: `{rel(REPORT)}`",
        f"Source generator: `{rel(GENERATOR)}`",
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
