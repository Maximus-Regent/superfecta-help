#!/usr/bin/env python3
"""
Validation for WALK_FORWARD_VALIDATION.md current-evidence boundaries.

Purpose:
- keep the train-only walk-forward report useful as an evaluation benchmark
- prevent the +22.46% selector result from being read as settled paper-trade proof
- preserve the candidate-universe limitation, fixed-replay caveat, and no-BAQ-as-BEL diagnostic
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
REPORT = BASE / "WALK_FORWARD_VALIDATION.md"
GENERATOR = BASE / "walk_forward_validation.py"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
OUT_DIR = BASE / "out" / "status_validation" / "walk_forward_validation_caution"
OUT_MD = OUT_DIR / "walk_forward_validation_caution_validation.md"
OUT_JSON = OUT_DIR / "walk_forward_validation_caution_validation.json"
REBUILD_COMMAND = "python3 validate_walk_forward_validation_caution.py"
VALID_EVIDENCE_SCOPE = "train_only_walk_forward_selector_benchmark_only"
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
    parser = argparse.ArgumentParser(description="Validate WALK_FORWARD_VALIDATION.md caution wording")
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
    with TemporaryDirectory(prefix="walk_forward_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "walk_forward_validation_caution"
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
            "validate_walk_forward_validation_caution.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial walk-forward validation artifacts",
        ))

        weakened_contract_out_dir = tmp_root / "weakened" / "walk_forward_validation_caution"
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
            "validate_walk_forward_validation_caution.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial walk-forward validation artifacts",
        ))

    return checks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name
    text = REPORT.read_text(encoding="utf-8")
    generator_text = GENERATOR.read_text(encoding="utf-8")
    first_20 = "\n".join(text.splitlines()[:20])
    rebuild_contract = current_rebuild_validation_contract_context(Path(args.current_evidence_json))

    checks: list[dict[str, Any]] = []
    checks.extend(current_bridge_cli_contract_checks(Path(args.current_evidence_json)))
    checks.append(require(
        rebuild_contract["upstream_refresh_commands"] == REQUIRED_REBUILD_REFRESH_ORDER
        and rebuild_contract["upstream_refresh_order_is_provenance_metadata_only"] is True
        and rebuild_contract["not_settled_roi_or_real_money_evidence"] is True,
        "current_evidence_rebuild_validation_contract_read",
        "walk-forward validation caution reads current_evidence_summary.json.rebuild_validation_contract before writing artifacts and keeps the rebuild order as provenance metadata only",
    ))
    checks.append(require(
        "## Current Evidence Boundary" in first_20
        and "historical train-only selector benchmark" in first_20
        and "not a live paper-trade ledger" in first_20
        and "not_current live-paper" not in first_20,
        "current_evidence_boundary_present",
        "walk-forward report opens with a current-evidence boundary before the method details",
    ))
    checks.append(require(
        f"- Valid evidence scope: `valid_evidence_scope={VALID_EVIDENCE_SCOPE}`." in first_20
        and VALID_EVIDENCE_SCOPE.endswith("_benchmark_only"),
        "walk_forward_valid_evidence_scope_visible",
        "walk-forward report now exposes exact valid_evidence_scope=train_only_walk_forward_selector_benchmark_only so copied +22.46% selector snippets stay framed as benchmark metadata only",
    ))
    checks.append(require(
        "settled ROI evidence" in first_20
        and "promotion readiness" in first_20
        and "live profitability" in first_20
        and "real-money evidence" in first_20,
        "not_paper_trade_or_real_money_evidence",
        "top boundary blocks settled-ROI, promotion, live-profitability, bankroll, and real-money overreads",
    ))
    checks.append(require(
        "Valid use: compare stricter train-only rule selection against fixed Phase 7 / Phase 8 replays" in first_20
        and "honest forward expectation is lower than full-sample discovery headlines" in first_20,
        "valid_use_as_selector_benchmark",
        "top boundary names the valid benchmark use without making it the deployment guide",
    ))
    checks.append(require(
        "candidate universe was still mined from previous full-sample research" in first_20
        and "+22.46% selector result is useful but still optimistic" in first_20
        and "true from-scratch yearly rediscovery loop" in first_20,
        "candidate_universe_limitation_visible",
        "top boundary keeps the full-sample-mined candidate-universe limitation beside the headline selector result",
    ))
    checks.append(require(
        "keep `OP_DURABLE_K7` as the safest anchor" in first_20
        and "`CD_CORE_K8` as the primary OP/CD paper-basket companion" in first_20
        and "`OP_REFINED_K7` shadow/watch" in first_20,
        "current_operator_posture_visible",
        "top boundary keeps the current anchor / companion / shadow posture separate from the walk-forward benchmark",
    ))
    checks.append(require(
        "fixed Phase 7 / Phase 8 comparison below is replay context on the same test years, not extra train-only validation" in first_20
        and "BEL->BAQ bridge rows are a coverage diagnostic only" in first_20
        and "Do not substitute BAQ for dormant BEL" in first_20,
        "fixed_replay_and_baq_boundaries_visible",
        "top boundary keeps fixed replays out of the train-only evidence lane and keeps BAQ from inheriting BEL",
    ))
    checks.append(require(
        "Total ROI: +22.46%" in text
        and "Positive test years: 8/10" in text
        and "Total races: 470" in text,
        "train_only_headline_metrics_present",
        "report still publishes the key train-only selector metrics",
    ))
    checks.append(require(
        "Fixed Phase 7 current-paper rule portfolio over the same test years: +31.34% ROI on 806 races" in text
        and "Fixed Phase 8 frozen portfolio over the same test years: +48.39% ROI on 579 races" in text
        and "Train-only selection result: +22.46% ROI on 470 races" in text,
        "fixed_replay_comparison_present",
        "report still compares train-only selection against fixed Phase 7 / Phase 8 replay context",
    ))
    checks.append(require(
        "BEL->BAQ bridge variant in 2024-2025: 7 races, -91.55% ROI" in text
        and "BAQ did not behave like a hidden continuation of the BEL edge here" in text,
        "bel_baq_coverage_break_present",
        "report keeps the BEL/BAQ bridge as a failed coverage diagnostic rather than an alias",
    ))
    checks.append(require(
        "2015: -39.24% ROI on 55 races" in text
        and "2024: -19.95% ROI on 45 races" in text,
        "unstable_years_visible",
        "report keeps the losing walk-forward years visible beside the aggregate positive result",
    ))
    checks.append(require(
        "## Current Evidence Boundary" in generator_text
        and f'VALID_EVIDENCE_SCOPE = "{VALID_EVIDENCE_SCOPE}"' in generator_text
        and "valid_evidence_scope={VALID_EVIDENCE_SCOPE}" in generator_text
        and "Do not substitute BAQ for dormant BEL" in generator_text,
        "generator_preserves_boundary",
        "walk_forward_validation.py will regenerate the same current-evidence boundary and raw valid_evidence_scope line",
    ))

    current_read = (
        "WALK_FORWARD_VALIDATION.md is a historical train-only selector benchmark with explicit boundaries: "
        f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}; the +22.46% result is useful evaluation context but still uses a previously mined candidate universe, "
        "fixed Phase 7 / Phase 8 rows are replay context rather than extra train-only validation, BEL->BAQ is a failed coverage diagnostic, "
        "and the artifact is not settled paper-trade ROI, promotion readiness, live profitability, bankroll guidance, real-money evidence, or BAQ/BEL aliasing; "
        "current bridge rebuild order is read from current_evidence_summary.json.rebuild_validation_contract as provenance metadata only before this validator writes artifacts."
    )

    payload: dict[str, Any] = {
        "suite": "walk_forward_validation_caution",
        "suite_status": "pass",
        "total_checks": len(checks),
        "check_count": len(checks),
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "source_report": rel(REPORT),
        "source_generator": rel(GENERATOR),
        "report_path": rel(OUT_MD),
        "rebuild_command": REBUILD_COMMAND,
        "current_read": current_read,
        "current_evidence_rebuild_validation_contract_read": rebuild_contract,
        "evidence_boundary": {
            "artifact_role": "walk-forward validation caution validator",
            "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
            "valid_use": "historical train-only selector benchmark caution validation",
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
        "summary": {
            "current_read": current_read,
            "suite_read": current_read,
        },
        "checks": checks,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    md_lines = [
        "# Walk-Forward Validation Caution",
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

    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
