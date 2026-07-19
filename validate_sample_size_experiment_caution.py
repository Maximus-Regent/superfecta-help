#!/usr/bin/env python3
"""
Validation for SAMPLE_SIZE_EXPERIMENT.md current-evidence boundaries.

Purpose:
- keep the sample-size selector experiment framed as historical selector research
- prevent the "keep sqrt_r150" recommendation from being read as a live rule change
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
REPORT = BASE / "SAMPLE_SIZE_EXPERIMENT.md"
GENERATOR = BASE / "experiment_sample_size.py"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
OUT_DIR = BASE / "out" / "status_validation" / "sample_size_experiment_caution"
OUT_MD = OUT_DIR / "sample_size_experiment_caution_validation.md"
OUT_JSON = OUT_DIR / "sample_size_experiment_caution_validation.json"
REBUILD_COMMAND = "python3 validate_sample_size_experiment_caution.py"
VALID_EVIDENCE_SCOPE = "sample_size_selector_replay_diagnostic_only"
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
    parser = argparse.ArgumentParser(description="Validate SAMPLE_SIZE_EXPERIMENT.md caution wording")
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
    with TemporaryDirectory(prefix="sample_size_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "sample_size_experiment_caution"
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
            "validate_sample_size_experiment_caution.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial sample-size validation artifacts",
        ))

        weakened_contract_out_dir = tmp_root / "weakened" / "sample_size_experiment_caution"
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
            "validate_sample_size_experiment_caution.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial sample-size validation artifacts",
        ))

    return checks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name
    text = REPORT.read_text(encoding="utf-8")
    generator_text = GENERATOR.read_text(encoding="utf-8")
    first_22 = "\n".join(text.splitlines()[:22])
    rebuild_contract = current_rebuild_validation_contract_context(Path(args.current_evidence_json))
    rebuild_line = (
        "- If this selector-research report is regenerated after scorecard/rules/signals/settlement-ledger byte changes, "
        "follow `current_evidence_summary.json.rebuild_validation_contract`: "
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
        "sample-size experiment validation reads current_evidence_summary.json.rebuild_validation_contract before writing artifacts and keeps the rebuild order as provenance metadata only",
    ))
    checks.append(require(
        "## Current Evidence Boundary" in first_22
        and "historical selector-tuning research on frozen walk-forward artifacts" in first_22
        and "races-factor tuning did not beat `sqrt_r150`" in first_22,
        "current_evidence_boundary_present",
        "sample-size selector report opens with a current-evidence boundary before purpose/method details",
    ))
    checks.append(require(
        "not a live paper-trade ledger" in first_22
        and "settled ROI evidence" in first_22
        and "promotion readiness" in first_22
        and "live profitability" in first_22
        and "real-money evidence" in first_22,
        "not_paper_trade_or_real_money_evidence",
        "top boundary blocks settled-ROI, promotion, live-profitability, bankroll, and real-money overreads",
    ))
    checks.append(require(
        f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}" in first_22
        and f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}" in generator_text,
        "sample_size_experiment_valid_evidence_scope_visible",
        "sample-size selector report, generator, and direct validator now expose the raw valid_evidence_scope=sample_size_selector_replay_diagnostic_only marker so copied races-factor and always-CD_CORE replay rows stay out of paper-trade, promotion, live-profitability, bankroll, and real-money evidence lanes",
    ))
    checks.append(require(
        "Valid use: compare selector-scoring variants against the original +22.46% train-only selector" in first_22
        and "Do not treat the `keep sqrt_r150` recommendation as permission to change the current paper basket" in first_22
        and "override `forward_evidence_scorecard.txt`" in first_22,
        "valid_use_as_selector_research",
        "top boundary keeps the selector recommendation in research context rather than current paper-basket authority",
    ))
    checks.append(require(
        "keep `OP_DURABLE_K7` as the safest anchor" in first_22
        and "`CD_CORE_K8` as the primary OP/CD paper-basket companion" in first_22
        and "`OP_REFINED_K7` in shadow/watch" in first_22
        and "ROI-complete paper evidence clears the scorecard gates" in first_22,
        "current_operator_posture_visible",
        "top boundary preserves the scorecard-backed anchor / companion / shadow posture",
    ))
    checks.append(require(
        "always-CD_CORE counterfactual and selector variants are replay diagnostics" in first_22
        and "already-mined candidate rules" in first_22
        and "not a fresh from-scratch discovery loop" in first_22
        and "not proof that CD_CORE should displace OP as anchor evidence" in first_22,
        "counterfactual_limitation_visible",
        "top boundary labels counterfactual and selector rows as replay diagnostics, not fresh discovery or OP-anchor displacement proof",
    ))
    checks.append(require(
        rebuild_line in first_22
        and rebuild_line in generator_text,
        "current_bridge_rebuild_route_visible",
        "sample-size report and generator publish the settlement-audit -> current-bridge -> bridge-validator route as provenance metadata only",
    ))
    checks.append(require(
        "Do not substitute `BAQ` for dormant `BEL`" in first_22
        and "validate this boundary with `python3 validate_sample_size_experiment_caution.py`" in first_22,
        "baq_bel_and_validator_route_visible",
        "top boundary keeps the BAQ/BEL guardrail and names the direct validator route",
    ))
    checks.append(require(
        "**Prior best (sqrt_r150):** +30.42% ROI" in text
        and "**Best this experiment (sqrt_r150):** +30.42% ROI" in text
        and "**Delta vs prior best:** +0.00pp" in text,
        "no_incremental_sample_size_gain_visible",
        "report still shows the core finding that races-factor variants did not improve on sqrt_r150",
    ))
    checks.append(require(
        "No meaningful improvement from adjusting the races factor alone (+0.00pp)" in text
        and "**Recommended action:** keep sqrt_r150 as the selector" in text,
        "recommendation_still_present_but_bounded",
        "report preserves the selector recommendation while the top boundary prevents over-reading it as a live posture change",
    ))
    checks.append(require(
        "## Current Evidence Boundary" in generator_text
        and "Do not substitute `BAQ` for dormant `BEL`" in generator_text
        and "validate_sample_size_experiment_caution.py" in generator_text,
        "generator_preserves_boundary",
        "experiment_sample_size.py will regenerate the same current-evidence boundary",
    ))

    current_read = (
        "SAMPLE_SIZE_EXPERIMENT.md is validated as historical selector-tuning research: races-factor variants did not improve "
        "on sqrt_r150, the always-CD_CORE counterfactual and selector rows are replay diagnostics on already-mined candidates, "
        f"valid_evidence_scope={VALID_EVIDENCE_SCOPE} keeps the artifact in replay-diagnostic scope only, "
        "the current bridge rebuild order is read from current_evidence_summary.json.rebuild_validation_contract as provenance metadata only, "
        "and the report cannot override the scorecard-backed OP_DURABLE_K7 anchor, CD_CORE_K8 paper companion, OP_REFINED_K7 shadow/watch posture, "
        "settled paper-observation gates, or the no-BAQ-as-BEL boundary."
    )

    payload: dict[str, Any] = {
        "suite": "sample_size_experiment_caution",
        "suite_status": "pass",
        "total_checks": len(checks),
        "check_count": len(checks),
        "source_report": rel(REPORT),
        "source_generator": rel(GENERATOR),
        "report_path": rel(out_md),
        "rebuild_command": REBUILD_COMMAND,
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "current_read": current_read,
        "current_evidence_rebuild_validation_contract_read": rebuild_contract,
        "summary": {
            "current_read": current_read,
            "suite_read": current_read,
        },
        "evidence_boundary": {
            "artifact_role": "sample-size selector experiment caution validator",
            "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
            "valid_use": "historical selector-research wording-drift validation",
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
        "# Sample-Size Experiment Caution Validation",
        "",
        f"Status: **{payload['suite_status'].upper()}**",
        f"Checks: **{len(checks)}/{len(checks)}**",
        f"Source report: `{rel(REPORT)}`",
        f"Source generator: `{rel(GENERATOR)}`",
        f"Rebuild command: `{REBUILD_COMMAND}`",
        f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
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
