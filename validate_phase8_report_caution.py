#!/usr/bin/env python3
"""
Validation for the Phase 8 legacy-report caution banner and deep-section demotions.

Purpose:
- stop the original Phase 8 full-sample headline from being read as the current deployment guide
- keep the stricter frozen holdout / walk-forward standard visible at the top of the legacy report
- preserve explicit boundaries around OP_DURABLE_K7, Phase 8 shadow/watch status, BAQ/BEL, and real-money claims
- prevent later sections from quietly re-promoting the legacy full-sample composite, 12/12 OOS line, BEL+OP refined fallback, or new-track discovery labels
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
REPORT = BASE / "PHASE8_REPORT.md"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
OUT_DIR = BASE / "out" / "status_validation" / "phase8_report_caution"
OUT_MD = OUT_DIR / "phase8_report_caution_validation.md"
OUT_JSON = OUT_DIR / "phase8_report_caution_validation.json"
REBUILD_COMMAND = "python3 validate_phase8_report_caution.py"
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
    parser = argparse.ArgumentParser(description="Validate PHASE8_REPORT.md caution wording")
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
    with TemporaryDirectory(prefix="phase8_report_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "phase8_report_caution_validation"
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
                "validate_phase8_report_caution.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial Phase 8 report-validation artifacts",
            )
        )

        weakened_contract_out_dir = tmp_root / "weakened" / "phase8_report_caution_validation"
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
                and "current_evidence_summary.json rebuild_validation_contract must mark upstream_refresh_order_is_provenance_metadata_only=true"
                in proc.stderr,
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "validate_phase8_report_caution.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial Phase 8 report-validation artifacts",
            )
        )

    return checks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name
    text = REPORT.read_text(encoding="utf-8")
    lines = text.splitlines()
    first_25 = "\n".join(lines[:25])
    rebuild_contract = current_rebuild_validation_contract_context(Path(args.current_evidence_json))

    checks: list[dict[str, Any]] = []
    checks.extend(current_bridge_cli_contract_checks(Path(args.current_evidence_json)))
    checks.append(require(
        rebuild_contract["upstream_refresh_commands"] == REQUIRED_REBUILD_REFRESH_ORDER
        and rebuild_contract["upstream_refresh_order_is_provenance_metadata_only"] is True
        and rebuild_contract["not_settled_roi_or_real_money_evidence"] is True,
        "current_evidence_rebuild_validation_contract_read",
        "Phase 8 caution validation reads current_evidence_summary.json.rebuild_validation_contract before writing artifacts and keeps the rebuild order as provenance metadata only",
    ))
    checks.append(require(
        "Current evidence update (2026-05-20)" in first_25
        and "legacy discovery report, not the deployment guide" in first_25,
        "top_caution_banner_present",
        "PHASE8_REPORT starts with a current-evidence banner before the original executive summary",
    ))
    checks.append(require(
        "+38.68% ROI on 175 races" in first_25
        and "+21.45% ROI on 118 races" in first_25
        and "Phase 7 portfolio beat Phase 8 on 2024-2025 holdout" in first_25,
        "strict_holdout_comparison_visible",
        "top banner shows the stricter 2024-2025 holdout comparison where Phase 7 beat Phase 8",
    ))
    checks.append(require(
        "`OP_DURABLE_K7` remains the safest current paper anchor" in first_25
        and "Phase 8 rules belong in shadow/watch observation" in first_25,
        "current_deployment_posture_visible",
        "top banner keeps OP_DURABLE_K7 as anchor and Phase 8 as shadow/watch rather than promotion-ready",
    ))
    checks.append(require(
        "Do not treat the 7-track full-sample result below as live profitability proof or promotion readiness." in first_25
        and "Do not place, size, bankroll, stop-loss, or scale real-money bets from this report" in first_25
        and "Do not substitute `BAQ` for dormant `BEL`" in first_25,
        "real_money_and_baq_boundaries_visible",
        "top banner prevents live-profitability, promotion-readiness, real-money, and BAQ/BEL overread",
    ))
    checks.append(require(
        "Treat every `$2`, `Cost`, and `Expected` line below as historical/paper accounting metadata, not a deployment size." in first_25
        and "separate human-approved risk memo" in first_25
        and "30 / 20 / 100 ROI-complete paper-evidence gates" in first_25
        and "payout/concentration checks" in first_25
        and "settlement-quality checks" in first_25
        and "no-BAQ-as-BEL guardrail" in first_25
        and "do not use real money from this report alone" not in text,
        "cost_lines_labeled_paper_accounting_not_sizing",
        "top banner now labels the legacy $2/cost/expected blocks as historical paper-accounting metadata and blocks direct sizing/bankroll/scale interpretation",
    ))
    checks.append(require(
        "## Original Full-Sample Executive Summary (superseded for deployment decisions)" in text
        and "on the original full-sample research read" in text,
        "original_summary_labeled_as_full_sample",
        "the old Phase 8 executive summary is now explicitly labeled as a superseded full-sample research read",
    ))
    checks.append(require(
        "Original full-sample verdict: MATERIAL IMPROVEMENT" in text
        and "Current deployment verdict: keep Phase 8 in shadow/watch" in text
        and "forward-settled evidence beats the frozen Phase 7 / OP anchor standard" in text,
        "legacy_verdict_demoted_by_current_gate",
        "the old material-improvement verdict is preserved as historical but demoted by the current forward-evidence gate",
    ))
    checks.append(require(
        "## Original Full-Sample Alternative Portfolio Comparison (legacy, not deployment ranking)" in text
        and "This is not the current deployment ranking" in text
        and "frozen 2024-2025 holdout still favors the simpler Phase 7 portfolio" in text
        and "current paper anchor remains `OP_DURABLE_K7`" in text
        and "current live-paper anchor" not in text
        and "safest active anchor" not in text,
        "deep_comparison_section_demoted",
        "the later portfolio-comparison section labels itself as legacy and repeats that the current ranking still favors Phase 7 / OP_DURABLE_K7",
    ))
    checks.append(require(
        "The Phase 8 optimized portfolio dominates on every composite metric" not in text
        and "Phase 8 achieved a material improvement (+18.8 ROI points) through:" not in text
        and "**OOS positive: 12/12** — every single out-of-sample year is profitable." not in text
        and "**The portfolio remains profitable (+18.8%) even after removing the 5 largest payouts.**" not in text,
        "unqualified_legacy_promotion_phrases_removed",
        "old unqualified deep-section phrases no longer re-promote Phase 8 dominance or material improvement without a full-sample caveat",
    ))
    checks.append(require(
        "## Original Validation (legacy full-sample-selected portfolio)" in text
        and "**Original OOS positive: 12/12**" in text
        and "does not outrank the frozen 2024-2025 Phase 7-vs-Phase 8 holdout comparison" in text
        and "Original 12/12 OOS sequence" in text
        and "does not outrank the frozen 2024-2025 holdout" in text
        and "Original full-sample ROI survives top-5 removal" in text
        and "historical durability signal, not a current deployment proof" in text,
        "robustness_signals_labeled_as_original_read",
        "the 12/12 OOS and top-5 removal lines are preserved as historical signals but no longer outrank frozen holdout or settled paper evidence",
    ))
    checks.append(require(
        "profitable-looking pockets at AQU, SA, KEE, and an improved CD rule" in text
        and "Current frozen evidence keeps those pockets in SKIP/WATCH" in text
        and "not a reason to prefer `CD_REFINED_K9` over the simpler `CD_CORE_K8`" in text
        and "`CD_REFINED_K9` lost on the frozen 2024-2025 holdout" in text,
        "k9_and_top2_mass_findings_demoted",
        "the K=9 track-pocket and CD top2_mass findings are labeled as original-search findings, not current reasons to prefer Phase 8 / CD_REFINED_K9",
    ))
    checks.append(require(
        "### Legacy fallback (not current operator fallback):" in text
        and "Current operator fallback is stricter: keep `OP_DURABLE_K7` as anchor with `CD_CORE_K8` as the paper companion" in text
        and "Do not use this legacy fallback as a live deployment instruction" in text,
        "legacy_fallback_not_current_operator_fallback",
        "the BEL+OP refined fallback is explicitly historical and cannot displace the current OP_DURABLE_K7 / CD_CORE_K8 operator posture",
    ))
    checks.append(require(
        "## New Track Discoveries (legacy discoveries; current status from frozen evidence)" in text
        and "### AQU (K=9) — Legacy discovery; current SKIP" in text
        and "frozen holdout is negative/small (`-4.28%` on 8 races)" in text
        and "### KEE (K=9) — Legacy discovery; current WATCH" in text
        and "### SA (K=9) — Legacy discovery; current WATCH" in text
        and "### DMR (K=7) — Legacy discovery; current WATCH / weakest" in text,
        "new_track_discoveries_keep_current_status",
        "new Phase 8 track pockets are labeled as legacy discoveries with current SKIP/WATCH status rather than promotion-ready discoveries",
    ))

    current_read = (
        "PHASE8_REPORT now opens with a current-evidence caution banner and repeats the demotion in later high-risk sections: "
        "Phase 8 is legacy full-sample discovery context, not the deployment guide; stricter 2024-2025 holdout favors Phase 7, "
        "OP_DURABLE_K7 remains the current paper anchor, Phase 8 stays shadow/watch, BAQ is not BEL, and the report's $2/cost/expected blocks "
        "are historical paper-accounting metadata only, not real-money placement, sizing, bankroll, stop-loss, or scale-up guidance; "
        "current bridge rebuild order is read from current_evidence_summary.json.rebuild_validation_contract as provenance metadata only before this validator writes artifacts."
    )

    payload: dict[str, Any] = {
        "suite": "phase8_report_caution",
        "suite_status": "pass",
        "total_checks": len(checks),
        "check_count": len(checks),
        "report_path": rel(OUT_MD),
        "source_report": rel(REPORT),
        "rebuild_command": REBUILD_COMMAND,
        "current_read": current_read,
        "current_evidence_rebuild_validation_contract_read": rebuild_contract,
        "summary": {
            "current_read": current_read,
            "suite_read": current_read,
        },
        "checks": checks,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    md_lines = [
        "# Phase 8 Report Caution Validation",
        "",
        f"Status: **{payload['suite_status'].upper()}**",
        f"Checks: **{len(checks)}/{len(checks)}**",
        f"Source report: `{rel(REPORT)}`",
        f"Rebuild command: `{REBUILD_COMMAND}`",
        "",
        "## Current read",
        "",
        payload["current_read"],
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
