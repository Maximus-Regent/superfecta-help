#!/usr/bin/env python3
"""
Validation for the dated shareable PDF refresh helper.

Purpose:
- keep `refresh_shareable_report_pdf.py --check-existing` runnable as a safe
  preflight before sharing the dated PDF derivative export
- pin the helper to the direct HTML report validator instead of letting the PDF
  become a separate trust anchor
- keep PDF refresh success framed as reproducibility metadata only
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
HELPER = BASE / "refresh_shareable_report_pdf.py"
HELPER_JSON = BASE / "out" / "status_validation" / "shareable_report_pdf_export" / "shareable_report_pdf_export.json"
HELPER_MD = BASE / "out" / "status_validation" / "shareable_report_pdf_export" / "shareable_report_pdf_export.md"
OUT_DIR = BASE / "out" / "status_validation" / "refresh_shareable_report_pdf"
OUT_JSON = OUT_DIR / "refresh_shareable_report_pdf_validation.json"
OUT_MD = OUT_DIR / "refresh_shareable_report_pdf_validation.md"
REBUILD_COMMAND = "python3 validate_refresh_shareable_report_pdf.py"


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "pass", "detail": detail}


def run_helper_check() -> dict[str, Any]:
    result = subprocess.run(
        ["python3", str(HELPER.name), "--check-existing"],
        cwd=BASE,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "refresh_shareable_report_pdf.py --check-existing failed:\n"
            + result.stdout[-4000:]
            + result.stderr[-4000:]
        )
    if not HELPER_JSON.exists():
        raise AssertionError(f"helper did not write expected JSON: {HELPER_JSON}")
    payload = json.loads(HELPER_JSON.read_text(encoding="utf-8"))
    payload["runner_stdout_tail"] = result.stdout[-1000:]
    payload["runner_stderr_tail"] = result.stderr[-1000:]
    return payload


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    helper_payload = run_helper_check()
    boundary = helper_payload.get("evidence_boundary")
    html_validator = helper_payload.get("html_validator")

    checks = [
        require(
            HELPER.exists()
            and "--check-existing" in HELPER.read_text(encoding="utf-8")
            and "kill_processes_for_profile" in HELPER.read_text(encoding="utf-8")
            and "accepted_completed_pdf_after_timeout" in HELPER.read_text(encoding="utf-8"),
            "helper_script_exposes_safe_check_and_export_paths",
            "refresh helper exists, exposes a check-existing path, and contains the timeout cleanup / completed-PDF-after-timeout handling needed for reproducible PDF exports",
        ),
        require(
            helper_payload.get("status") == "pass"
            and helper_payload.get("mode") == "check-existing"
            and HELPER_MD.exists(),
            "helper_check_existing_writes_pass_artifacts",
            "helper check-existing mode writes pass-status JSON/markdown artifacts without running Chrome or rewriting the PDF",
        ),
        require(
            isinstance(html_validator, dict)
            and html_validator.get("suite_status") == "pass"
            and html_validator.get("check_count") == 33
            and html_validator.get("total_checks") == 33
            and html_validator.get("contains_dated_pdf_derivative_check") is True
            and html_validator.get("contains_current_evidence_combined_operator_read_route_check") is True
            and html_validator.get("contains_current_evidence_operator_read_gate_route_check") is True
            and html_validator.get("contains_current_evidence_rebuild_validation_contract_route_check") is True
            and html_validator.get("contains_current_evidence_missing_rebuild_contract_no_write_fixture") is True
            and html_validator.get("contains_current_evidence_weakened_rebuild_contract_no_write_fixture") is True
            and html_validator.get("contains_malformed_scorecard_gate_no_write_fixture") is True
            and html_validator.get("contains_full_data_retrain_caveat_route_check") is True
            and html_validator.get("contains_cross_family_current_paper_route_check") is True
            and html_validator.get("contains_scorecard_ci_only_boundary_check") is True
            and html_validator.get("contains_scorecard_audit_route_check") is True
            and html_validator.get("contains_legacy_pdf_alias_claim_boundary_check") is True
            and html_validator.get("contains_legacy_docx_alias_claim_boundary_check") is True
            and html_validator.get("contains_legacy_quick_start_pdf_alias_claim_boundary_check") is True
            and html_validator.get("contains_legacy_prompt_docx_alias_claim_boundary_check") is True,
            "helper_routes_through_html_report_validator",
            "helper verification routes through validate_superfecta_html_report.py and requires the dated PDF derivative current-evidence check, the combined current-evidence operator-read route check, the current-evidence operator-read-gate route check, the rebuild-order route check, the missing/weakened rebuild-contract and malformed scorecard-gate no-write fixtures, the cross-family current-paper route check, the OP_REFINED CI-only boundary check, the scorecard-audit route check, the legacy PDF/DOCX/quick-start PDF/OpenClaw prompt alias claim-boundary checks, and the full-data retrain caveat route check rather than treating convenience exports as separate trust anchors",
        ),
        require(
            isinstance(helper_payload.get("html"), dict)
            and helper_payload["html"].get("path") == "Superfecta_Project_Report_2026-04-15.html"
            and isinstance(helper_payload["html"].get("sha256"), str)
            and len(helper_payload["html"]["sha256"]) == 64
            and isinstance(helper_payload.get("pdf"), dict)
            and helper_payload["pdf"].get("path") == "Superfecta_Project_Report_2026-04-15.pdf"
            and isinstance(helper_payload["pdf"].get("sha256"), str)
            and len(helper_payload["pdf"]["sha256"]) == 64
            and helper_payload["pdf"].get("bytes", 0) > 100_000,
            "helper_publishes_html_pdf_fingerprints",
            "helper publishes HTML/PDF byte counts and SHA-256 fingerprints so PDF-share checks are reproducible metadata rather than invisible manual export steps",
        ),
        require(
            isinstance(boundary, dict)
            and boundary.get("html_is_trust_anchor") is True
            and boundary.get("pdf_is_derivative_export_only") is True
            and boundary.get("not_new_forward_evidence") is True
            and boundary.get("not_settled_roi_evidence") is True
            and boundary.get("not_live_profitability_evidence") is True
            and boundary.get("not_promotion_readiness_evidence") is True
            and boundary.get("not_bankroll_guidance") is True
            and boundary.get("not_real_money_evidence") is True
            and "do not substitute BAQ for BEL" in boundary.get("non_goals", []),
            "helper_publishes_report_safe_evidence_boundary",
            "helper JSON keeps PDF refresh success separate from forward evidence, settled ROI, OP-anchor proof, live profitability, promotion readiness, bankroll guidance, real-money evidence, and BAQ/BEL substitution",
        ),
    ]

    suite_read = (
        "PDF refresh helper check-existing path passes through the dated HTML report validator; "
        "the dated HTML remains the trust anchor, the dated PDF remains a derivative export, the legacy undated PDF/DOCX aliases, legacy quick-start PDF alias, and legacy OpenClaw prompt DOCX alias stay claim-free, the HTML/PDF combined operator-read route, rebuild-order route, scorecard-audit route, OP_REFINED CI-only boundary, cross-family current-paper caveat route, and full-data retrain caveat route stay pinned, and the helper output is reproducibility metadata only rather than settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence"
    )
    payload = {
        "suite_status": "pass",
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "summary": {"suite_read": suite_read},
        "helper_artifact": {
            "json_path": str(HELPER_JSON.relative_to(BASE)),
            "md_path": str(HELPER_MD.relative_to(BASE)),
            "payload_status": helper_payload.get("status"),
            "payload_mode": helper_payload.get("mode"),
        },
        "rebuild": {"workdir": str(BASE), "command": REBUILD_COMMAND},
    }

    lines = [
        "# Shareable Report PDF Refresh Helper Validation",
        "",
        "This report checks the safe check-existing path for the dated PDF derivative refresh helper.",
        "It is reproducibility metadata only, not performance evidence.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Checks: {len(checks)}",
        "- Result: PASS",
        "",
        "## Checks",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check['check']} | {check['status'].upper()} | {check['detail']} |")
    lines.extend(
        [
            "",
            "## Current Read",
            "",
            f"- Suite read: {suite_read}",
            f"- Helper JSON: `{HELPER_JSON.relative_to(BASE)}`",
            f"- Helper markdown: `{HELPER_MD.relative_to(BASE)}`",
        ]
    )

    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
