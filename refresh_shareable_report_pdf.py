#!/usr/bin/env python3
"""
Refresh or verify the dated shareable PDF derivative export.

This is a reproducibility helper for `Superfecta_Project_Report_2026-04-15.pdf`.
The dated HTML report remains the trust anchor; the PDF is only a derivative
sharing artifact. A successful run is report-readiness metadata, not settled ROI,
live profitability, promotion readiness, bankroll guidance, or real-money evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
HTML_REPORT = BASE / "Superfecta_Project_Report_2026-04-15.html"
PDF_REPORT = BASE / "Superfecta_Project_Report_2026-04-15.pdf"
HTML_VALIDATOR = BASE / "validate_superfecta_html_report.py"
HTML_VALIDATION_JSON = (
    BASE
    / "out"
    / "status_validation"
    / "superfecta_html_report"
    / "superfecta_html_report_validation.json"
)
OUT_DIR = BASE / "out" / "status_validation" / "shareable_report_pdf_export"
OUT_JSON = OUT_DIR / "shareable_report_pdf_export.json"
OUT_MD = OUT_DIR / "shareable_report_pdf_export.md"

CHROME_CANDIDATES = [
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
    Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
    Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
]

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "dated shareable PDF derivative refresh/verification helper",
    "source_scope": [
        "Superfecta_Project_Report_2026-04-15.html",
        "Superfecta_Project_Report_2026-04-15.pdf",
        "validate_superfecta_html_report.py",
    ],
    "valid_use": "regenerate or verify the PDF derivative export after dated HTML report changes",
    "html_is_trust_anchor": True,
    "pdf_is_derivative_export_only": True,
    "not_new_forward_evidence": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_bankroll_guidance": True,
    "not_real_money_evidence": True,
    "non_goals": [
        "do not use PDF refresh success as settled ROI",
        "do not use PDF refresh success as live profitability evidence",
        "do not use PDF refresh success as OP-anchor proof",
        "do not promote OP_REFINED_K7 or Phase 8 from PDF refresh success",
        "do not substitute BAQ for BEL",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-existing",
        action="store_true",
        help="do not run Chrome; verify the existing dated PDF with the HTML report validator",
    )
    parser.add_argument(
        "--chrome-bin",
        type=Path,
        default=None,
        help="optional path to a Chromium-compatible browser binary",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=45.0,
        help="seconds to wait for headless PDF export before accepting a completed temp PDF or failing",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise AssertionError(f"missing expected file: {path}")
    return {
        "path": str(path.relative_to(BASE)),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def is_valid_pdf(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 100_000:
        return False
    with path.open("rb") as handle:
        return handle.read(5) == b"%PDF-"


def find_chrome(override: Path | None) -> Path:
    if override is not None:
        if override.exists():
            return override
        raise AssertionError(f"requested Chrome/Chromium binary does not exist: {override}")
    for candidate in CHROME_CANDIDATES:
        if candidate.exists():
            return candidate
    raise AssertionError(
        "no Chrome/Chromium binary found; pass --chrome-bin or use --check-existing"
    )


def processes_for_profile(profile_dir: Path) -> list[int]:
    result = subprocess.run(
        ["ps", "-ax", "-o", "pid=", "-o", "command="],
        text=True,
        capture_output=True,
        check=False,
    )
    pids: list[int] = []
    profile_text = str(profile_dir)
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped or profile_text not in stripped:
            continue
        pid_text = stripped.split(maxsplit=1)[0]
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        if pid != os.getpid():
            pids.append(pid)
    return sorted(set(pids))


def kill_processes_for_profile(profile_dir: Path) -> dict[str, Any]:
    killed: list[int] = []
    for sig in (signal.SIGTERM, signal.SIGKILL):
        pids = processes_for_profile(profile_dir)
        if not pids:
            break
        for pid in pids:
            try:
                os.kill(pid, sig)
                killed.append(pid)
            except ProcessLookupError:
                pass
        time.sleep(0.5)
    return {"profile_dir": str(profile_dir), "killed_pids": sorted(set(killed))}


def run_html_validator() -> dict[str, Any]:
    result = subprocess.run(
        ["python3", str(HTML_VALIDATOR.name)],
        cwd=BASE,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "validate_superfecta_html_report.py failed:\n"
            + result.stdout[-4000:]
            + result.stderr[-4000:]
        )
    payload = json.loads(HTML_VALIDATION_JSON.read_text(encoding="utf-8"))
    check_names = [check.get("check") for check in payload.get("checks", [])]
    if payload.get("suite_status") != "pass":
        raise AssertionError("HTML report validator did not publish suite_status=pass")
    if payload.get("check_count") != payload.get("total_checks"):
        raise AssertionError("HTML report validator check_count/total_checks mismatch")
    if "dated_pdf_derivative_current_evidence_bridge" not in check_names:
        raise AssertionError("HTML report validator is missing the dated PDF derivative check")
    if "current_evidence_combined_operator_read_route" not in check_names:
        raise AssertionError("HTML report validator is missing the combined current-evidence operator-read route check")
    if "current_evidence_operator_read_gate_route" not in check_names:
        raise AssertionError("HTML report validator is missing the current-evidence operator-read-gate route check")
    if "cross_family_current_paper_route_present" not in check_names:
        raise AssertionError("HTML report validator is missing the cross-family current-paper route check")
    if "full_data_retrain_caveat_route_present" not in check_names:
        raise AssertionError("HTML report validator is missing the full-data retrain caveat route check")
    if "html_pdf_scorecard_ci_only_boundary" not in check_names:
        raise AssertionError("HTML report validator is missing the OP_REFINED CI-only boundary check")
    if "html_pdf_scorecard_audit_route" not in check_names:
        raise AssertionError("HTML report validator is missing the scorecard-audit route check")
    if "html_pdf_current_evidence_rebuild_validation_contract_route" not in check_names:
        raise AssertionError("HTML report validator is missing the current-evidence rebuild-order route check")
    if "current_evidence_missing_rebuild_contract_fails_before_artifacts" not in check_names:
        raise AssertionError("HTML report validator is missing the missing-rebuild-contract no-write fixture check")
    if "current_evidence_weakened_rebuild_contract_fails_before_artifacts" not in check_names:
        raise AssertionError("HTML report validator is missing the weakened-rebuild-contract no-write fixture check")
    if "malformed_scorecard_gate_floors_fail_before_artifacts" not in check_names:
        raise AssertionError("HTML report validator is missing the malformed scorecard-gate no-write fixture check")
    if "legacy_pdf_alias_claim_boundary" not in check_names:
        raise AssertionError("HTML report validator is missing the legacy PDF alias claim-boundary check")
    if "legacy_docx_alias_claim_boundary" not in check_names:
        raise AssertionError("HTML report validator is missing the legacy DOCX alias claim-boundary check")
    if "legacy_quick_start_pdf_alias_claim_boundary" not in check_names:
        raise AssertionError("HTML report validator is missing the legacy quick-start PDF alias claim-boundary check")
    if "legacy_prompt_docx_alias_claim_boundary" not in check_names:
        raise AssertionError("HTML report validator is missing the legacy OpenClaw prompt DOCX alias claim-boundary check")
    return {
        "command": "python3 validate_superfecta_html_report.py",
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-1000:],
        "stderr_tail": result.stderr[-1000:],
        "suite_status": payload.get("suite_status"),
        "check_count": payload.get("check_count"),
        "total_checks": payload.get("total_checks"),
        "contains_dated_pdf_derivative_check": True,
        "contains_current_evidence_combined_operator_read_route_check": True,
        "contains_current_evidence_operator_read_gate_route_check": True,
        "contains_cross_family_current_paper_route_check": True,
        "contains_full_data_retrain_caveat_route_check": True,
        "contains_scorecard_ci_only_boundary_check": True,
        "contains_scorecard_audit_route_check": True,
        "contains_current_evidence_rebuild_validation_contract_route_check": True,
        "contains_current_evidence_missing_rebuild_contract_no_write_fixture": True,
        "contains_current_evidence_weakened_rebuild_contract_no_write_fixture": True,
        "contains_malformed_scorecard_gate_no_write_fixture": True,
        "contains_legacy_pdf_alias_claim_boundary_check": True,
        "contains_legacy_docx_alias_claim_boundary_check": True,
        "contains_legacy_quick_start_pdf_alias_claim_boundary_check": True,
        "contains_legacy_prompt_docx_alias_claim_boundary_check": True,
    }


def export_pdf(chrome_path: Path, timeout_seconds: float) -> dict[str, Any]:
    if not HTML_REPORT.exists():
        raise AssertionError(f"missing dated HTML trust anchor: {HTML_REPORT}")

    profile_dir = Path(tempfile.mkdtemp(prefix="superfecta_pdf_profile_"))
    fd, tmp_pdf_name = tempfile.mkstemp(
        prefix=".tmp_superfecta_report_", suffix=".pdf", dir=BASE
    )
    os.close(fd)
    tmp_pdf = Path(tmp_pdf_name)
    tmp_pdf.unlink(missing_ok=True)
    command = [
        str(chrome_path),
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        f"--user-data-dir={profile_dir}",
        f"--print-to-pdf={tmp_pdf}",
        "--no-pdf-header-footer",
        HTML_REPORT.resolve().as_uri(),
    ]

    timed_out = False
    stdout = ""
    stderr = ""
    returncode: int | None = None
    cleanup: dict[str, Any] = {"profile_dir": str(profile_dir), "killed_pids": []}
    process = subprocess.Popen(
        command,
        cwd=BASE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            cleanup = kill_processes_for_profile(profile_dir)
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate(timeout=5)
        returncode = process.returncode

        if not is_valid_pdf(tmp_pdf):
            raise AssertionError(
                "headless browser did not produce a valid temp PDF; "
                f"returncode={returncode}, timed_out={timed_out}, stderr={stderr[-1000:]}"
            )
        if returncode not in (0, None) and not timed_out:
            raise AssertionError(
                "headless browser returned nonzero before writing a valid PDF; "
                f"returncode={returncode}, stderr={stderr[-1000:]}"
            )

        backup = None
        if PDF_REPORT.exists():
            backup = BASE / f".tmp_backup_{PDF_REPORT.name}.{os.getpid()}"
            shutil.copy2(PDF_REPORT, backup)
        shutil.move(str(tmp_pdf), PDF_REPORT)
        try:
            validator = run_html_validator()
        except Exception:
            if backup is not None and backup.exists():
                shutil.move(str(backup), PDF_REPORT)
            raise
        else:
            if backup is not None and backup.exists():
                backup.unlink()

        return {
            "mode": "export",
            "chrome_path": str(chrome_path),
            "command": command,
            "timed_out": timed_out,
            "accepted_completed_pdf_after_timeout": timed_out and is_valid_pdf(PDF_REPORT),
            "returncode": returncode,
            "stdout_tail": stdout[-1000:],
            "stderr_tail": stderr[-1000:],
            "cleanup": cleanup,
            "html_validator": validator,
        }
    finally:
        tmp_pdf.unlink(missing_ok=True)
        shutil.rmtree(profile_dir, ignore_errors=True)


def build_payload(mode: str, export_result: dict[str, Any] | None) -> dict[str, Any]:
    validator = run_html_validator() if export_result is None else export_result["html_validator"]
    return {
        "status": "pass",
        "mode": mode,
        "html": file_fingerprint(HTML_REPORT),
        "pdf": file_fingerprint(PDF_REPORT),
        "html_validator": validator,
        "export_result": export_result,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "summary": {
            "suite_read": (
                "dated shareable PDF derivative is verified against the HTML report validator; "
                "this is shareable-report reproducibility metadata only, not settled ROI, "
                "live profitability, promotion readiness, bankroll guidance, or real-money evidence"
            )
        },
    }


def write_outputs(payload: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Shareable Report PDF Export Check",
        "",
        "This artifact verifies the dated PDF derivative export against the dated HTML trust anchor.",
        "It is reproducibility metadata only, not forward evidence or real-money evidence.",
        "",
        f"- Status: `{payload['status']}`",
        f"- Mode: `{payload['mode']}`",
        f"- HTML: `{payload['html']['path']}` ({payload['html']['bytes']} bytes, sha256 `{payload['html']['sha256']}`)",
        f"- PDF: `{payload['pdf']['path']}` ({payload['pdf']['bytes']} bytes, sha256 `{payload['pdf']['sha256']}`)",
        f"- HTML validator: `{payload['html_validator']['suite_status']}` "
        f"({payload['html_validator']['check_count']}/{payload['html_validator']['total_checks']})",
        "- Evidence boundary: derivative export / reproducibility metadata only; not ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence.",
    ]
    if payload.get("export_result"):
        export = payload["export_result"]
        lines.extend(
            [
                "",
                "## Export Run",
                "",
                f"- Chrome: `{export['chrome_path']}`",
                f"- Timed out: `{export['timed_out']}`",
                f"- Accepted completed PDF after timeout: `{export['accepted_completed_pdf_after_timeout']}`",
                f"- Return code: `{export['returncode']}`",
            ]
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.check_existing:
        payload = build_payload("check-existing", None)
    else:
        chrome_path = find_chrome(args.chrome_bin)
        export_result = export_pdf(chrome_path, args.timeout_seconds)
        payload = build_payload("export", export_result)
    write_outputs(payload)
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    print(payload["summary"]["suite_read"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
