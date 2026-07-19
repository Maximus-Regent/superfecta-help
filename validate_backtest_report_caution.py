#!/usr/bin/env python3
"""
Validation for BACKTEST_REPORT.md caution wording.

Purpose:
- keep the legacy large-sample backtest framed as background context
- prevent odds-only XGBoost or Harville baselines from being promoted by old report text
- preserve the no-BAQ-as-BEL and no-real-money boundaries in the archived report
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
REPORT = BASE / "BACKTEST_REPORT.md"
GENERATOR = BASE / "backtest_superfecta.py"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
FULL_DATA_RETRAIN = BASE / "FULL_DATA_RETRAIN_ARTIFACTS.md"
FULL_DATA_RETRAIN_VALIDATOR = BASE / "validate_full_data_retrain_artifacts.py"
OUT_DIR = BASE / "out" / "status_validation" / "backtest_report_caution"
OUT_MD = OUT_DIR / "backtest_report_caution_validation.md"
OUT_JSON = OUT_DIR / "backtest_report_caution_validation.json"
REBUILD_COMMAND = "python3 validate_backtest_report_caution.py"
VALID_EVIDENCE_SCOPE = "legacy_broad_backtest_negative_baseline_context_only"
REQUIRED_REBUILD_REFRESH_ORDER = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "pass", "detail": detail}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate BACKTEST_REPORT.md caution wording")
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
        "green_checks_are_reproducibility_metadata_only": contract[
            "green_checks_are_reproducibility_metadata_only"
        ],
        "upstream_refresh_order_is_provenance_metadata_only": contract[
            "upstream_refresh_order_is_provenance_metadata_only"
        ],
        "not_settled_roi_or_real_money_evidence": contract["not_settled_roi_or_real_money_evidence"],
    }


def current_bridge_cli_contract_checks(current_evidence_json: Path = CURRENT_EVIDENCE_JSON) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="backtest_report_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "backtest_report_caution_validation"
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
                "validate_backtest_report_caution.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial legacy-backtest validation artifacts",
            )
        )

        weakened_contract_out_dir = tmp_root / "weakened" / "backtest_report_caution_validation"
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
                "validate_backtest_report_caution.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial legacy-backtest validation artifacts",
            )
        )

    return checks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name

    report_text = REPORT.read_text(encoding="utf-8")
    generator_text = GENERATOR.read_text(encoding="utf-8")
    rebuild_contract = current_rebuild_validation_contract_context(Path(args.current_evidence_json))
    rebuild_line = (
        "- If quoting `CURRENT_EVIDENCE_SUMMARY.*` from this legacy backtest context after "
        "scorecard/rules/signals/settlement-ledger byte changes, follow "
        f"`current_evidence_summary.json.rebuild_validation_contract`: "
        f"`{'` -> `'.join(rebuild_contract['upstream_refresh_commands'])}`; "
        "green rebuild checks are provenance metadata only, not settled ROI, promotion readiness, "
        "live profitability, bankroll guidance, or real-money evidence."
    )

    boundary_lines = [
        f"- Valid evidence scope: `valid_evidence_scope={VALID_EVIDENCE_SCOPE}`.",
        "- This is a legacy large-sample negative baseline for broad structural, Harville, and generic odds-only ML families. It is background context, not the current deployment or paper-trade decision surface.",
        "- It does not override `forward_evidence_scorecard.txt` / `.json`, `compare_main_approaches.md`, `CURRENT_EVIDENCE_SUMMARY.md`, or the selective OP/CD paper-observation route. Current posture still keeps `OP_DURABLE_K7` as the safest anchor and `CD_CORE_K8` as the paper companion until ROI-complete paper evidence changes that.",
        rebuild_line,
        "- The XGBoost language below refers to odds-derived residual modeling. Full-data XGBoost retrain artifacts and exact retrain/prediction commands route to `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py` as model-fit reproducibility context only, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "- `BAQ` appearing in the track universe is not permission to alias it as `BEL`; the BEL->BAQ bridge remains a failed coverage patch, not a deployment route.",
        "- Validate this legacy-report caution with `python3 validate_backtest_report_caution.py`.",
    ]

    checks: list[dict[str, Any]] = []
    checks.extend(current_bridge_cli_contract_checks(Path(args.current_evidence_json)))
    checks.append(
        require(
            "## Current Evidence Boundary" in report_text
            and all(line in report_text for line in boundary_lines),
            "backtest_report_current_evidence_boundary_present",
            "BACKTEST_REPORT.md now opens with a current evidence-boundary banner that keeps the legacy report in background-context status",
        )
    )
    checks.append(
        require(
            all(line in generator_text for line in boundary_lines),
            "backtest_generator_preserves_current_evidence_boundary",
            "backtest_superfecta.py will preserve the same caution if the legacy backtest report is regenerated",
        )
    )
    checks.append(
        require(
            f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}" in report_text
            and f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}" in generator_text,
            "backtest_report_valid_evidence_scope_visible",
            "BACKTEST_REPORT.md and backtest_superfecta.py now expose the raw valid_evidence_scope line so the broad backtest stays background negative-baseline context only",
        )
    )
    checks.append(
        require(
            rebuild_contract["upstream_refresh_commands"] == REQUIRED_REBUILD_REFRESH_ORDER
            and rebuild_line in report_text
            and rebuild_line in generator_text
            and rebuild_contract["requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"] is True
            and rebuild_contract["requires_source_consistency_before_quoting_current_totals"] is True
            and rebuild_contract["green_checks_are_reproducibility_metadata_only"] is True
            and rebuild_contract["upstream_refresh_order_is_provenance_metadata_only"] is True
            and rebuild_contract["not_settled_roi_or_real_money_evidence"] is True,
            "current_evidence_rebuild_contract_visible_for_legacy_backtest_context",
            "the legacy backtest report and generator now carry the source-matched settlement-audit -> current-bridge -> bridge-validator route before current totals are quoted from this archived context",
        )
    )
    checks.append(
        require(
            "**No strategy achieved consistent positive out-of-sample ROI.**" in report_text
            and "Does the Evidence Support Profitability?" in report_text
            and "**No.** The current data and model family has not reached profitability" in report_text,
            "legacy_negative_baseline_still_present",
            "the broad backtest still reads as a negative baseline instead of a profitability claim",
        )
    )
    checks.append(
        require(
            "The XGBoost residual model" in report_text
            and "does not identify profitable combos" in report_text
            and "Without **horse-specific performance data**" in report_text,
            "odds_only_xgboost_stays_parked",
            "the legacy XGBoost section remains parked as odds-only model research that did not find a betting edge",
        )
    )
    checks.append(
        require(
            "`BAQ` appearing in the track universe is not permission to alias it as `BEL`" in report_text
            and "BEL->BAQ bridge remains a failed coverage patch" in report_text,
            "no_baq_as_bel_boundary_present",
            "the legacy report now explicitly prevents the BAQ track-universe listing from being read as BEL substitution permission",
        )
    )
    checks.append(
        require(
            FULL_DATA_RETRAIN.exists() and FULL_DATA_RETRAIN_VALIDATOR.exists(),
            "referenced_full_data_retrain_artifacts_exist",
            "the caution points to real full-data retrain artifact and validator files",
        )
    )

    suite_read = (
        "BACKTEST_REPORT.md is validated as a legacy large-sample negative baseline for broad structural, "
        "Harville, and generic odds-only ML families; it does not override the scorecard, main comparison, "
        "current-evidence bridge, OP_DURABLE_K7 anchor, CD_CORE_K8 paper companion, or the OP/CD paper-observation route; "
        f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}; "
        "current bridge totals route through the settlement-audit -> current-bridge -> bridge-validator rebuild contract before quotation after source-byte changes; "
        "full-data XGBoost retrain artifacts stay model-fit reproducibility context only; BAQ is not BEL; "
        "a green backtest-report caution validation is not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence"
    )

    payload = {
        "suite_status": "pass",
        "total_checks": len(checks),
        "check_count": len(checks),
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "checks": checks,
        "summary": {"suite_read": suite_read},
        "current_evidence_rebuild_validation_contract_read": rebuild_contract,
        "evidence_boundary": {
            "artifact_role": "legacy broad-backtest caution validator",
            "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
            "valid_use": "background-context and wording-drift validation for BACKTEST_REPORT.md",
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
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }

    lines = [
        "# Backtest Report Caution Validation",
        "",
        "This validator checks that `BACKTEST_REPORT.md` remains a legacy background baseline, not a current deployment, promotion, or real-money surface.",
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
            f"- valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
            "- Full-data retrain route: `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py`",
            f"- Current bridge rebuild route: {' -> '.join(rebuild_contract['upstream_refresh_commands'])}",
            "- BAQ/BEL boundary: BAQ is not BEL; the bridge remains failed coverage-patch context.",
            "",
            "## Sources",
            "",
            f"- `{REPORT.name}`",
            f"- `{GENERATOR.name}`",
            f"- `{CURRENT_EVIDENCE_JSON.name}`",
            f"- `{FULL_DATA_RETRAIN.name}`",
            f"- `{FULL_DATA_RETRAIN_VALIDATOR.name}`",
        ]
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
