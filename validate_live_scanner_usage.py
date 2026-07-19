#!/usr/bin/env python3
"""
Validation for LIVE_SCANNER_USAGE.md caution wording.

Purpose:
- keep live scanner usage in paper-alert / operational-routing status
- prevent default broad-rule, cron, base-stake, Discord, or cache-only examples from becoming betting instructions
- preserve the OP_DURABLE_K7 / CD_CORE_K8 / OP_REFINED_K7 hierarchy and no-BAQ-as-BEL boundary
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import live_portfolio_scanner as scanner

BASE = Path(__file__).resolve().parent
DOC = BASE / "LIVE_SCANNER_USAGE.md"
SCANNER = BASE / "live_portfolio_scanner.py"
WRAPPER = BASE / "run_daily_portfolio_observation.sh"
SCAN_WRAPPER = BASE / "scan_live.sh"
TARGETING_VALIDATOR = BASE / "validate_live_scan_targeting_and_limit_status.py"
STATUS_DOC = BASE / "COLE_STATUS_AND_PLAN.md"
STATUS_DOC_VALIDATOR = BASE / "validate_cole_status_and_plan.py"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
OUT_DIR = BASE / "out" / "status_validation" / "live_scanner_usage"
OUT_MD = OUT_DIR / "live_scanner_usage_validation.md"
OUT_JSON = OUT_DIR / "live_scanner_usage_validation.json"
REBUILD_COMMAND = "python3 validate_live_scanner_usage.py"
VALID_EVIDENCE_SCOPE = "live_scanner_usage_paper_alert_runbook_navigation_only"
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
    parser = argparse.ArgumentParser(description="Validate the live scanner usage boundary")
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
    with TemporaryDirectory(prefix="live_scanner_usage_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "live_scanner_usage_validation"
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
            "validate_live_scanner_usage.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial scanner-usage validation artifacts",
        ))

        weakened_contract_out_dir = tmp_root / "weakened" / "live_scanner_usage_validation"
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
            "validate_live_scanner_usage.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial scanner-usage validation artifacts",
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
        and "live paper-alert scanner runbook" in first_35
        and "not a live betting, promotion, bankroll, or real-money guide" in first_35,
        "top_current_evidence_boundary_present",
        "LIVE_SCANNER_USAGE opens with a current evidence-boundary before command examples",
    ))
    checks.append(require(
        f"- Valid evidence scope: `valid_evidence_scope={VALID_EVIDENCE_SCOPE}`." in first_35
        and VALID_EVIDENCE_SCOPE.endswith("_navigation_only"),
        "live_scanner_usage_valid_evidence_scope_visible",
        "LIVE_SCANNER_USAGE now exposes exact valid_evidence_scope=live_scanner_usage_paper_alert_runbook_navigation_only so copied scanner examples stay framed as runbook navigation metadata only",
    ))
    checks.append(require(
        "`./run_daily_portfolio_observation.sh`" in first_35
        and "keeps settlement rows separate from scanner output" in first_35,
        "preferred_daily_wrapper_route_visible",
        "top boundary routes daily observation through the wrapper and keeps scanner output separate from settlement evidence",
    ))
    checks.append(require(
        "Scanner hits" in first_35
        and "Discord alerts" in first_35
        and "clean empty scans" in first_35
        and "capped `--max-races` scans" in first_35
        and "cache-only scans" in first_35
        and "API access failures such as HTTP 403" in first_35
        and f"`valid_evidence_scope={scanner.SCANNER_VALID_EVIDENCE_SCOPE}`" in first_35
        and "`evidence_boundary`" in first_35
        and "`evidence_boundary_text`" in first_35
        and "human and Discord output render the same boundary line" in first_35
        and "not settled ROI" in first_35
        and "live profitability evidence" in first_35
        and "real-money authorization" in first_35,
        "scanner_outputs_labeled_operational_metadata_only",
        "top boundary prevents scanner hits, alerts, clean empty, capped, cache-only, API-access-failure, and validator outputs from being read as performance evidence while naming the scanner's source-level evidence-boundary fields",
    ))
    checks.append(require(
        "`OP_DURABLE_K7` as the safest anchor" in first_35
        and "`CD_CORE_K8` as the primary OP/CD paper companion" in first_35
        and "`OP_REFINED_K7` plus other Phase 8 rules in shadow/watch" in first_35,
        "current_hierarchy_visible",
        "top boundary preserves the current anchor / paper-companion / shadow hierarchy",
    ))
    checks.append(require(
        "Dormant `BEL` must not be replaced with `BAQ`." in first_35
        and "Validate this usage boundary with `python3 validate_live_scanner_usage.py`." in first_35,
        "no_baq_as_bel_and_direct_validator_route_present",
        "top boundary names the no-BAQ-as-BEL rule and direct usage validator",
    ))
    checks.append(require(
        "`COLE_STATUS_AND_PLAN.md`" in first_35
        and "`python3 validate_cole_status_and_plan.py`" in first_35
        and "`status_doc_base_api_access_route_documented`" in first_35
        and "base API-access / HTTP 403 status-summary action-recheck route before lane enrichment" in first_35,
        "main_status_api_access_route_visible",
        "top boundary routes main status-doc / repo-map API-access status-summary questions to validate_cole_status_and_plan.py and status_doc_base_api_access_route_documented",
    ))
    checks.append(require(
        "`current_evidence_summary.json.rebuild_validation_contract`" in first_35
        and "`python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`" in first_35
        and "provenance/rebuild routing only" in first_35
        and "not scanner evidence or settled ROI" in first_35
        and rebuild_contract["upstream_refresh_order_commands"] == EXPECTED_REBUILD_ORDER_COMMANDS
        and rebuild_contract["requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"] is True
        and rebuild_contract["requires_source_consistency_before_quoting_current_totals"] is True
        and rebuild_contract["upstream_refresh_order_is_provenance_metadata_only"] is True
        and rebuild_contract["not_settled_roi_or_real_money_evidence"] is True,
        "current_evidence_rebuild_contract_route_visible",
        "top boundary routes source-byte changes through current_evidence_summary.json.rebuild_validation_contract and keeps the three-command order as provenance metadata only",
    ))
    checks.append(require(
        "# Research-coverage scan" in text
        and "# Default scan" not in text,
        "default_scan_labeled_research_coverage",
        "quick start labels the no-rules override scan as research coverage rather than the default operating route",
    ))
    checks.append(require(
        "python3 live_portfolio_scanner.py --include-cards oaklawn churchill" in text
        and "python3 live_portfolio_scanner.py --include-cards belmont churchill" not in text,
        "track_filter_example_uses_current_primary_tracks",
        "track-filter example uses OP/CD current primary paper-basket tracks instead of dormant Belmont",
    ))
    checks.append(require(
        "`--base-stake N` | `1.0` | Paper-accounting base stake per superfecta combo; not bankroll guidance |" in text,
        "base_stake_labeled_paper_accounting",
        "base-stake flag is labeled as paper-accounting metadata rather than bankroll guidance",
    ))
    checks.append(require(
        "Use `scan_live.sh` for paper-alert cron monitoring" in text
        and "does not settle rows or authorize real-money betting" in text,
        "cron_setup_labeled_paper_alert_monitoring",
        "cron setup is framed as paper-alert monitoring and not settlement or real-money authorization",
    ))
    checks.append(require(
        "A no-hit run with `max_race_limit_hit=true` is operationally limited coverage, not a clean forward observation" in text
        and "partial_cache_*` means the scanner had to skip one or more race-detail files" in text,
        "limited_and_partial_coverage_boundaries_present",
        "machine-readable status section preserves capped and partial-cache non-evidence boundaries",
    ))
    checks.append(require(
        "## API Limits And Access Failures" in text
        and "HTTP 403 Forbidden" in text
        and "scanner_error` / API-unreachable operator context" in text
        and "`api_failure_operator_action=refresh_daily_wrapper_before_evidence_read`" in text
        and "`api_failure_recheck_command=./run_daily_portfolio_observation.sh`" in text
        and "Do not treat it as a no-target day, a clean empty scan, or forward-performance evidence" in text
        and "use `--cache-only` only as explicitly partial/stale operational context" in text,
        "api_access_failures_labeled_operator_context",
        "runbook keeps HTTP 403/API access failures in scanner-error operator context with explicit operator-action/recheck-command fields instead of no-target, clean-empty, or performance evidence",
    ))
    checks.append(require(
        f"`valid_evidence_scope={scanner.SCANNER_VALID_EVIDENCE_SCOPE}`" in text
        and "`evidence_boundary`" in text
        and "`evidence_boundary_text`" in text
        and "Non-empty scanner JSON hit rows carry the same evidence-boundary fields" in text
        and scanner.SCANNER_EVIDENCE_BOUNDARY_TEXT in scanner.format_human([], emit_combos=False)
        and "`api_failure_operator_action`" in text
        and "`api_failure_recheck_command`" in text
        and "operator tooling can route the run without parsing prose" in text,
        "api_failure_action_fields_documented_in_sidecar_section",
        "machine-readable status section documents source-level scanner evidence-boundary fields plus API-failure operator-action and recheck-command fields as structured routing metadata",
    ))
    checks.append(require(
        all(path.exists() for path in [
            DOC,
            SCANNER,
            WRAPPER,
            SCAN_WRAPPER,
            TARGETING_VALIDATOR,
            STATUS_DOC,
            STATUS_DOC_VALIDATOR,
            CURRENT_EVIDENCE_JSON,
        ]),
        "referenced_scanner_files_exist",
        "usage note references real scanner, wrapper, cron wrapper, direct targeting validator, main status doc, direct main-status validator, and current-evidence JSON files",
    ))

    current_read = (
        "LIVE_SCANNER_USAGE.md is validated as live paper-alert scanner guidance: daily observation still routes through "
        "run_daily_portfolio_observation.sh, scanner hits/alerts/clean-empty/capped/cache-only/API-access-failure results are operational metadata only, "
        f"the runbook publishes exact valid_evidence_scope={VALID_EVIDENCE_SCOPE} as paper-alert navigation metadata only, "
        "scanner status sidecars and non-empty scanner hit rows document valid_evidence_scope/evidence_boundary/evidence_boundary_text as copy-safety metadata only, "
        "HTTP 403 / API-access failures keep api_failure_operator_action=refresh_daily_wrapper_before_evidence_read plus "
        "api_failure_recheck_command=./run_daily_portfolio_observation.sh as operator routing only, "
        "main status-doc / repo-map API-access route questions point to COLE_STATUS_AND_PLAN.md plus validate_cole_status_and_plan.py and "
        "status_doc_base_api_access_route_documented before lane enrichment, "
        "source-byte changes before quoting CURRENT_EVIDENCE_SUMMARY.* route through current_evidence_summary.json.rebuild_validation_contract with "
        "python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py as provenance/rebuild metadata only, "
        "OP_DURABLE_K7 stays anchor, CD_CORE_K8 stays paper companion, OP_REFINED_K7 and Phase 8 stay shadow/watch, "
        "BAQ is not BEL, base-stake is paper-accounting metadata, and cron monitoring is not settlement, live-profitability, bankroll, or real-money evidence."
    )
    checks.append(require(
        "api_failure_operator_action=refresh_daily_wrapper_before_evidence_read" in current_read
        and "api_failure_recheck_command=./run_daily_portfolio_observation.sh" in current_read
        and "operator routing only" in current_read,
        "current_read_preserves_api_failure_action_route",
        "validator summary exposes the HTTP 403/API-access operator-action and wrapper recheck command as operator routing only",
    ))
    payload: dict[str, Any] = {
        "suite": "live_scanner_usage",
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
            "artifact_role": "live scanner usage-boundary validator",
            "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
            "valid_use": "live paper-alert scanner usage wording validation",
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
        "# Live Scanner Usage Validation",
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
