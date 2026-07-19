#!/usr/bin/env python3
"""
Validation for FULL_DATA_RETRAIN_ARTIFACTS.md.

Purpose:
- keep the full-data XGBoost retrain artifact framed as model research
- prevent payout-fit metrics from being read as paper-trade or real-money evidence
- preserve the route back to the current report-safe comparison artifacts
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
DOC = BASE / "FULL_DATA_RETRAIN_ARTIFACTS.md"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
OUT_DIR = BASE / "out" / "status_validation" / "full_data_retrain_artifacts"
OUT_MD = OUT_DIR / "full_data_retrain_artifacts_validation.md"
OUT_JSON = OUT_DIR / "full_data_retrain_artifacts_validation.json"
REBUILD_COMMAND = "python3 validate_full_data_retrain_artifacts.py"
EXPECTED_REBUILD_ORDER_COMMANDS = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]
VALID_EVIDENCE_SCOPE = "full_data_xgboost_retrain_model_fit_diagnostic_only"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "full-data XGBoost retrain artifact validator",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "valid_use": "model-fit reproducibility and research-context boundary check",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_real_money_evidence": True,
    "xgboost_reopening_requires": [
        "materially different evidence class",
        "downstream betting pass-through improvement",
        "settled paper observations",
    ],
}

EVIDENCE_BOUNDARY_METADATA: dict[str, Any] = {
    "artifact_role": "full-data XGBoost retrain diagnostic metadata",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "source_document": "FULL_DATA_RETRAIN_ARTIFACTS.md",
    "valid_use": "retrain command reproducibility, payout-fit diagnostics, and research-only command routing",
    "metrics_are_model_fit_diagnostics_only": True,
    "not_betting_edge_evidence": True,
    "not_paper_trade_signal": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_bankroll_guidance": True,
    "not_real_money_evidence": True,
    "not_current_odds_only_xgboost_reopening_evidence": True,
    "current_report_safe_route": [
        "compare_main_approaches.md",
        "OP_ANCHOR_METHOD_COMPARISON.md",
        "AB_DOWNSTREAM_COMPARISON.md",
    ],
    "current_method_posture": {
        "selective_op_cd_rule_path": "paper path",
        "harville": "benchmark only",
        "xgboost": "research only unless evidence class changes materially",
    },
    "xgboost_reopening_requires": [
        "materially different evidence class",
        "downstream betting pass-through improvement",
        "ROI-complete settled paper observations",
    ],
    "non_goals": [
        "do not treat payout RMSE / MAE improvement as betting ROI",
        "do not route the single-race prediction command into paper trade by default",
        "do not promote XGBoost from model-fit metrics alone",
        "do not use this artifact for bankroll guidance",
        "do not use this artifact as real-money evidence",
    ],
}


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "pass", "detail": detail}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the full-data retrain artifact boundary")
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
        raise AssertionError(
            "current_evidence_summary.json rebuild_validation_contract must publish the three-step upstream_refresh_order"
        )

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
    with TemporaryDirectory(prefix="full_data_retrain_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "full_data_retrain_artifacts_validation"
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
            "validate_full_data_retrain_artifacts.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial full-data retrain validation artifacts",
        ))

        weakened_contract_out_dir = tmp_root / "weakened" / "full_data_retrain_artifacts_validation"
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
            "validate_full_data_retrain_artifacts.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial full-data retrain validation artifacts",
        ))

    return checks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name

    text = DOC.read_text(encoding="utf-8")
    rebuild_contract = load_current_evidence_rebuild_contract(Path(args.current_evidence_json))

    checks = current_bridge_cli_contract_checks(Path(args.current_evidence_json))
    checks.extend([
        require(
            "# Full Data Retrain Artifacts" in text
            and "Completed successfully end-to-end on `14years.csv` as a model-fit / research artifact." in text,
            "status_research_artifact_boundary",
            "status line still frames the full-data retrain as model-fit research rather than deployment evidence",
        ),
        require(
            "## Evidence boundary" in text
            and f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}" in text
            and "not a paper-trade signal, current-day scanner output, settled ROI, live-profitability evidence, promotion readiness, bankroll guidance, or real-money evidence" in text,
            "evidence_boundary_present",
            "artifact carries a direct valid-scope line plus no-paper/no-profitability/no-real-money boundary",
        ),
        require(
            "The payout RMSE / MAE improvements below are model-fit diagnostics only." in text
            and "They do not reopen the current odds-only XGBoost betting path or change the current paper hierarchy by themselves." in text,
            "fit_metrics_not_betting_evidence",
            "payout-fit improvements cannot be read as a betting-path reopening",
        ),
        require(
            "`compare_main_approaches.md`, `OP_ANCHOR_METHOD_COMPARISON.md`, and `AB_DOWNSTREAM_COMPARISON.md`" in text
            and "the selective OP/CD rule path remains the paper path, Harville remains benchmark-only, and XGBoost remains research-only" in text,
            "deployment_route_points_to_comparison_artifacts",
            "deployment interpretation is routed to the report-safe comparison artifacts",
        ),
        require(
            "`python3 validate_full_data_retrain_artifacts.py`" in text,
            "self_validation_route_present",
            "artifact names its direct validator",
        ),
        require(
            "`current_evidence_summary.json.rebuild_validation_contract`" in text
            and "`python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`" in text
            and "provenance/rebuild metadata only" in text
            and "not full-data retrain evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in text
            and rebuild_contract["upstream_refresh_order_commands"] == EXPECTED_REBUILD_ORDER_COMMANDS
            and rebuild_contract["requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"] is True
            and rebuild_contract["requires_source_consistency_before_quoting_current_totals"] is True
            and rebuild_contract["upstream_refresh_order_is_provenance_metadata_only"] is True
            and rebuild_contract["not_settled_roi_or_real_money_evidence"] is True,
            "current_evidence_rebuild_contract_route_present",
            "artifact names the current-evidence rebuild contract route while keeping it as provenance metadata rather than full-data retrain or ROI evidence",
        ),
        require(
            "These are model-fit diagnostics, not betting-edge evidence." in text
            and "RMSE improvement: 74.17%" in text
            and "MAE improvement: 74.63%" in text,
            "headline_metrics_have_local_caveat",
            "large RMSE/MAE improvements remain present but locally caveated",
        ),
        require(
            "XGBoost/train_test_residual.py" in text
            and "--model-output full_data_retrain_model.json" in text
            and "--plot-prefix full_data_retrain" in text,
            "training_command_pinned",
            "exact training command remains reproducible",
        ),
        require(
            "Diagnostic/research use only: replace `path/to/single_race.csv`" in text
            and "Do not route this output into the paper-trade path without a separate evidence-class review." in text
            and "XGBoost/predict_single_race.py" in text,
            "prediction_command_caveated",
            "single-race prediction command is kept diagnostic/research-only",
        ),
        require(
            "Machine-readable validation boundary: `out/status_validation/full_data_retrain_artifacts/full_data_retrain_artifacts_validation.json` publishes `evidence_boundary_metadata.artifact_role=full-data XGBoost retrain diagnostic metadata`." in text
            and EVIDENCE_BOUNDARY_METADATA["artifact_role"] == "full-data XGBoost retrain diagnostic metadata"
            and EVIDENCE_BOUNDARY_METADATA["valid_evidence_scope"] == VALID_EVIDENCE_SCOPE
            and EVIDENCE_BOUNDARY["valid_evidence_scope"] == VALID_EVIDENCE_SCOPE
            and EVIDENCE_BOUNDARY_METADATA["metrics_are_model_fit_diagnostics_only"] is True
            and EVIDENCE_BOUNDARY_METADATA["not_current_odds_only_xgboost_reopening_evidence"] is True
            and EVIDENCE_BOUNDARY_METADATA["not_bankroll_guidance"] is True
            and EVIDENCE_BOUNDARY_METADATA["not_real_money_evidence"] is True
            and EVIDENCE_BOUNDARY_METADATA["current_method_posture"]["xgboost"] == "research only unless evidence class changes materially"
            and "ROI-complete settled paper observations" in EVIDENCE_BOUNDARY_METADATA["xgboost_reopening_requires"],
            "machine_readable_diagnostic_boundary_metadata",
            "artifact and validator JSON now pin full-data retrain metrics as diagnostic metadata only, not XGBoost reopening, bankroll, promotion, live-profitability, or real-money evidence",
        ),
    ])

    summary = {
        "suite_status": "pass",
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "evidence_boundary_metadata": EVIDENCE_BOUNDARY_METADATA,
        "current_evidence_rebuild_validation_contract_read": rebuild_contract,
        "summary": {
            "suite_read": (
                "FULL_DATA_RETRAIN_ARTIFACTS.md still records the 14years.csv retrain command "
                "and large payout-fit metrics while keeping those metrics in model-research context only; "
                "source-byte changes before quoting current bridge context route through "
                "current_evidence_summary.json.rebuild_validation_contract as provenance/rebuild metadata only; "
                "deployment interpretation stays routed to compare_main_approaches.md, "
                "OP_ANCHOR_METHOD_COMPARISON.md, and AB_DOWNSTREAM_COMPARISON.md, with XGBoost research-only "
                "unless its evidence class changes materially and downstream/paper evidence follows; "
                "missing or weakened current-evidence rebuild contracts fail before validation artifacts are written; "
                "evidence_boundary_metadata keeps full-data retrain diagnostics out of XGBoost reopening, promotion, "
                "bankroll, live-profitability, and real-money claims."
            )
        },
    }

    lines = [
        "# Full Data Retrain Artifacts Validation",
        "",
        "This report checks that `FULL_DATA_RETRAIN_ARTIFACTS.md` keeps full-data XGBoost retrain metrics in research-only context.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
        f"- Checks: {summary['check_count']}",
        f"- Result: {summary['suite_status'].upper()}",
        "",
        "## Checks",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check['check']} | {check['status'].upper()} | {check['detail']} |")
    lines.extend([
        "",
        "## Evidence Boundary",
        "",
        "- This green read is model-fit reproducibility metadata only.",
        "- Current-evidence rebuild routing is provenance metadata only and is validated before artifacts are written.",
        "- It is not settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence.",
        "- Reopening XGBoost for paper use still requires a materially different evidence class, downstream betting pass-through improvement, and settled paper observations.",
        "- Machine-readable metadata: `evidence_boundary_metadata` marks the RMSE / MAE gains as diagnostic-only and not current odds-only XGBoost reopening evidence.",
        f"- Valid evidence scope: `valid_evidence_scope={VALID_EVIDENCE_SCOPE}`.",
        "",
        "## Current Read",
        "",
        f"- {summary['summary']['suite_read']}",
    ])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
