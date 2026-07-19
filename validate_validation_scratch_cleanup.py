#!/usr/bin/env python3
"""
Validation for validation_scratch_cleanup.py.

Purpose:
- prove the cleanup helper is dry-run-first
- keep deletion scoped to generated validation scratch roots only
- prove non-project roots are refused before inspection
- prove project-local status_validation lookalikes outside out/status_validation are refused
- prove file paths under out/status_validation are refused as cleanup roots
- prove invalid CLI roots return structured errors instead of tracebacks
- prove missing but allowed status roots are reported explicitly as empty/missing
- prove nested scratch roots collapse to the top disposable parent
- prove symlinked scratch-like paths are ignored instead of inventoried or removed
- prove this validator cleans its own fixture root after checks
- preserve the no-new-evidence boundary for low-disk operational hygiene
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import validation_scratch_cleanup as cleanup

BASE = Path(__file__).resolve().parent
FIXTURE_ROOT = BASE / "out" / "status_validation" / "validation_scratch_cleanup_fixture"
MISSING_ROOT = BASE / "out" / "status_validation" / "validation_scratch_cleanup_missing_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "validation_scratch_cleanup"
MD_PATH = OUT_DIR / "validation_scratch_cleanup_validation.md"
JSON_PATH = OUT_DIR / "validation_scratch_cleanup_validation.json"
REBUILD_COMMAND = "python3 validate_validation_scratch_cleanup.py"
VALID_EVIDENCE_SCOPE = cleanup.VALID_EVIDENCE_SCOPE
VALID_EVIDENCE_SCOPE_LINE = f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}"


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    return {"check": name, "status": "pass" if condition else "fail", "detail": detail}


def reset_fixture() -> None:
    if FIXTURE_ROOT.exists():
        shutil.rmtree(FIXTURE_ROOT)
    (FIXTURE_ROOT / "alpha" / "_tmp").mkdir(parents=True)
    (FIXTURE_ROOT / "alpha" / "_tmp" / "nested_fixture").mkdir(parents=True)
    (FIXTURE_ROOT / "beta_fixture").mkdir(parents=True)
    (FIXTURE_ROOT / "keep_reports").mkdir(parents=True)
    (FIXTURE_ROOT / "linked_fixture").symlink_to(FIXTURE_ROOT / "keep_reports", target_is_directory=True)
    (FIXTURE_ROOT / "alpha" / "_tmp" / "scratch.txt").write_text("scratch\n", encoding="utf-8")
    (FIXTURE_ROOT / "alpha" / "_tmp" / "nested_fixture" / "nested.txt").write_text(
        "nested scratch\n",
        encoding="utf-8",
    )
    (FIXTURE_ROOT / "beta_fixture" / "case.json").write_text('{"fixture": true}\n', encoding="utf-8")
    (FIXTURE_ROOT / "keep_reports" / "report.md").write_text("# keep\n", encoding="utf-8")


def cleanup_fixture_roots() -> None:
    for path in [FIXTURE_ROOT, MISSING_ROOT]:
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.exists():
            shutil.rmtree(path)


def run_cli_json(*extra: str) -> dict[str, Any]:
    cmd = [
        "python3",
        str(BASE / "validation_scratch_cleanup.py"),
        "--status-root",
        str(FIXTURE_ROOT),
        "--json",
        *extra,
    ]
    completed = subprocess.run(cmd, cwd=BASE, text=True, capture_output=True, check=True)
    return json.loads(completed.stdout)


def build_checks() -> list[dict[str, Any]]:
    reset_fixture()
    dry_report = cleanup.build_report(FIXTURE_ROOT, apply=False)
    dry_paths = {row["path"] for row in dry_report["scratch_roots"]}
    nested_parent_collapsed = (
        "out/status_validation/validation_scratch_cleanup_fixture/alpha/_tmp" in dry_paths
        and "out/status_validation/validation_scratch_cleanup_fixture/alpha/_tmp/nested_fixture"
        not in dry_paths
    )

    cli_dry_report = run_cli_json()
    dry_run_preserved_files = (
        (FIXTURE_ROOT / "alpha" / "_tmp" / "scratch.txt").exists()
        and (FIXTURE_ROOT / "alpha" / "_tmp" / "nested_fixture" / "nested.txt").exists()
        and (FIXTURE_ROOT / "beta_fixture" / "case.json").exists()
        and (FIXTURE_ROOT / "keep_reports" / "report.md").exists()
        and (FIXTURE_ROOT / "linked_fixture").is_symlink()
    )

    reset_fixture()
    apply_report = cleanup.build_report(FIXTURE_ROOT, apply=True)
    keep_report_exists = (FIXTURE_ROOT / "keep_reports" / "report.md").exists()
    scratch_removed = not (FIXTURE_ROOT / "alpha" / "_tmp").exists() and not (FIXTURE_ROOT / "beta_fixture").exists()
    symlink_preserved = (FIXTURE_ROOT / "linked_fixture").is_symlink()

    reset_fixture()
    cli_apply_report = run_cli_json("--apply")
    cli_keep_report_exists = (FIXTURE_ROOT / "keep_reports" / "report.md").exists()
    cli_scratch_removed = not (FIXTURE_ROOT / "alpha" / "_tmp").exists() and not (FIXTURE_ROOT / "beta_fixture").exists()
    cli_symlink_preserved = (FIXTURE_ROOT / "linked_fixture").is_symlink()

    try:
        cleanup.build_report(BASE.parent, apply=False)
        non_project_refused = False
    except ValueError as exc:
        non_project_refused = "Refusing to inspect a non-project status-validation root" in str(exc)

    try:
        cleanup.build_report(BASE / "status_validation", apply=False)
        project_local_lookalike_refused = False
    except ValueError as exc:
        project_local_lookalike_refused = "Refusing to inspect a non-project status-validation root" in str(exc)

    try:
        cleanup.build_report(FIXTURE_ROOT / "keep_reports" / "report.md", apply=False)
        file_root_refused = False
    except ValueError as exc:
        file_root_refused = "Refusing to inspect a non-directory status-validation root" in str(exc)

    if MISSING_ROOT.exists():
        shutil.rmtree(MISSING_ROOT)
    missing_report = cleanup.build_report(MISSING_ROOT, apply=False)

    missing_json_cli = subprocess.run(
        [
            "python3",
            str(BASE / "validation_scratch_cleanup.py"),
            "--status-root",
            str(MISSING_ROOT),
            "--json",
        ],
        cwd=BASE,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        missing_json_report = json.loads(missing_json_cli.stdout)
    except json.JSONDecodeError:
        missing_json_report = {}

    missing_text_cli = subprocess.run(
        [
            "python3",
            str(BASE / "validation_scratch_cleanup.py"),
            "--status-root",
            str(MISSING_ROOT),
        ],
        cwd=BASE,
        text=True,
        capture_output=True,
        check=False,
    )

    low_pressure = cleanup.disk_pressure_fields(100 * 1024 * 1024, 120 * 1024 * 1024)
    recovered_pressure = cleanup.disk_pressure_fields(100 * 1024 * 1024, 700 * 1024 * 1024)

    bad_json_cli = subprocess.run(
        [
            "python3",
            str(BASE / "validation_scratch_cleanup.py"),
            "--status-root",
            str(BASE.parent),
            "--json",
        ],
        cwd=BASE,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        bad_json_report = json.loads(bad_json_cli.stdout)
    except json.JSONDecodeError:
        bad_json_report = {}

    bad_text_cli = subprocess.run(
        [
            "python3",
            str(BASE / "validation_scratch_cleanup.py"),
            "--status-root",
            str(BASE.parent),
        ],
        cwd=BASE,
        text=True,
        capture_output=True,
        check=False,
    )

    cleanup_fixture_roots()
    fixture_root_cleaned_after_checks = not FIXTURE_ROOT.exists() and not MISSING_ROOT.exists()

    return [
        require(
            dry_report["mode"] == "dry_run" and dry_report["scratch_root_count"] == 2,
            "dry_run_default_inventory",
            "library dry-run mode inventories generated scratch roots without deleting them",
        ),
        require(
            dry_paths
            == {
                "out/status_validation/validation_scratch_cleanup_fixture/alpha/_tmp",
                "out/status_validation/validation_scratch_cleanup_fixture/beta_fixture",
            },
            "scratch_root_filter_is_narrow",
            "helper only targets directories named _tmp or ending in _fixture under the status-validation tree",
        ),
        require(
            nested_parent_collapsed,
            "nested_scratch_roots_collapse_to_parent",
            "nested fixture-like directories inside a disposable scratch root are covered by the parent root rather than double-counted or separately removed",
        ),
        require(
            "out/status_validation/validation_scratch_cleanup_fixture/linked_fixture" not in dry_paths,
            "scratch_like_symlinks_ignored",
            "symlinked paths whose names look like scratch roots are not inventoried as disposable scratch directories",
        ),
        require(
            dry_run_preserved_files,
            "dry_run_does_not_delete",
            "dry-run mode leaves scratch, non-scratch fixture files, and scratch-like symlinks in place",
        ),
        require(
            cli_dry_report["mode"] == "dry_run"
            and cli_dry_report["scratch_root_count"] == 2
            and not cli_dry_report["removed_paths"],
            "cli_json_dry_run_default",
            "CLI JSON mode is dry-run by default and reports no removed paths",
        ),
        require(
            dry_report["low_disk_warning_threshold_bytes"] == cleanup.LOW_DISK_WARNING_THRESHOLD_BYTES
            and dry_report["low_disk_warning_threshold_human"] == cleanup.human_bytes(
                cleanup.LOW_DISK_WARNING_THRESHOLD_BYTES
            )
            and dry_report["disk_free_before_below_threshold"]
            == (dry_report["disk_free_before_bytes"] < cleanup.LOW_DISK_WARNING_THRESHOLD_BYTES)
            and dry_report["disk_free_after_below_threshold"]
            == (dry_report["disk_free_after_bytes"] < cleanup.LOW_DISK_WARNING_THRESHOLD_BYTES)
            and (
                bool(dry_report["low_disk_warning"])
                == dry_report["disk_free_after_below_threshold"]
            ),
            "disk_pressure_fields_published",
            "library dry-run reports the low-disk threshold, before/after below-threshold booleans, and a warning exactly when post-cleanup free space remains below the threshold",
        ),
        require(
            dry_report["reclaimable_validation_scratch_bytes"] == dry_report["total_scratch_bytes"]
            and dry_report["reclaimable_validation_scratch_human"] == cleanup.human_bytes(
                dry_report["total_scratch_bytes"]
            )
            and dry_report["estimated_disk_free_after_scratch_cleanup_bytes"]
            == dry_report["disk_free_before_bytes"] + dry_report["total_scratch_bytes"]
            and dry_report["estimated_disk_free_after_scratch_cleanup_human"]
            == cleanup.human_bytes(dry_report["estimated_disk_free_after_scratch_cleanup_bytes"])
            and dry_report["validation_scratch_cleanup_insufficient_for_threshold"]
            == (
                dry_report["estimated_disk_free_after_scratch_cleanup_bytes"]
                < cleanup.LOW_DISK_WARNING_THRESHOLD_BYTES
            )
            and (
                bool(dry_report["validation_scratch_cleanup_insufficient_warning"])
                == dry_report["validation_scratch_cleanup_insufficient_for_threshold"]
            ),
            "scratch_cleanup_capacity_fields_published",
            "library dry-run publishes reclaimable scratch bytes, estimated free space after removing listed scratch roots, and an explicit below-threshold insufficiency flag",
        ),
        require(
            low_pressure["disk_free_before_below_threshold"] is True
            and low_pressure["disk_free_after_below_threshold"] is True
            and "below 512.0 MiB" in low_pressure["low_disk_warning"]
            and recovered_pressure["disk_free_before_below_threshold"] is True
            and recovered_pressure["disk_free_after_below_threshold"] is False
            and recovered_pressure["low_disk_warning"] == "",
            "disk_pressure_warning_threshold_logic",
            "pure disk-pressure helper warns only when post-cleanup free space remains below the 512 MiB threshold, so warnings do not depend on the current machine's free-space state",
        ),
        require(
            apply_report["mode"] == "apply"
            and scratch_removed
            and keep_report_exists
            and symlink_preserved
            and set(apply_report["removed_paths"])
            == {
                "out/status_validation/validation_scratch_cleanup_fixture/alpha/_tmp",
                "out/status_validation/validation_scratch_cleanup_fixture/beta_fixture",
            },
            "apply_removes_only_scratch_roots",
            "apply mode removes only generated scratch roots and preserves non-scratch report directories plus scratch-like symlinks",
        ),
        require(
            cli_apply_report["mode"] == "apply"
            and cli_scratch_removed
            and cli_keep_report_exists
            and cli_symlink_preserved
            and len(cli_apply_report["removed_paths"]) == 2,
            "cli_apply_removes_only_scratch_roots",
            "CLI apply mode removes the same narrow scratch roots while preserving non-scratch files and scratch-like symlinks",
        ),
        require(
            non_project_refused,
            "non_project_status_root_refused",
            "helper refuses to inspect a path outside the project status-validation tree before inventorying or deleting anything",
        ),
        require(
            project_local_lookalike_refused,
            "project_local_status_validation_lookalike_refused",
            "helper refuses project-local status_validation lookalikes outside out/status_validation before inventorying or deleting anything",
        ),
        require(
            file_root_refused,
            "status_root_file_refused",
            "helper refuses file paths under out/status_validation as cleanup roots instead of reporting a misleading empty inventory",
        ),
        require(
            missing_report["mode"] == "dry_run"
            and missing_report["status_root_exists"] is False
            and missing_report["status_root_missing"] is True
            and missing_report["scratch_root_count"] == 0
            and missing_report["removed_paths"] == []
            and "does not exist" in missing_report.get("warning", ""),
            "missing_status_root_reported_structurally",
            "library reports allowed missing status roots explicitly as missing empty roots rather than normal existing empty inventories",
        ),
        require(
            missing_json_cli.returncode == 0
            and missing_json_report.get("mode") == "dry_run"
            and missing_json_report.get("status_root_exists") is False
            and missing_json_report.get("status_root_missing") is True
            and missing_json_report.get("scratch_root_count") == 0
            and missing_json_report.get("removed_paths") == []
            and "does not exist" in missing_json_report.get("warning", "")
            and "Traceback" not in missing_json_cli.stdout
            and "Traceback" not in missing_json_cli.stderr,
            "cli_json_missing_root_reported_structurally",
            "CLI JSON mode reports allowed missing status roots as explicit empty/missing inventories without tracebacks",
        ),
        require(
            missing_text_cli.returncode == 0
            and "Warning: status-validation root does not exist; nothing was inspected or removed." in missing_text_cli.stdout
            and "Scratch roots: 0" in missing_text_cli.stdout
            and "Traceback" not in missing_text_cli.stdout
            and "Traceback" not in missing_text_cli.stderr,
            "cli_text_missing_root_warning_present",
            "CLI text mode warns when an allowed status root is missing instead of making the empty inventory look like a normal existing tree",
        ),
        require(
            bad_json_cli.returncode == 2
            and bad_json_report.get("mode") == "error"
            and bad_json_report.get("scratch_root_count") == 0
            and not bad_json_report.get("removed_paths")
            and bad_json_report.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and "Refusing to inspect a non-project status-validation root" in bad_json_report.get("error", "")
            and bad_json_report.get("evidence_boundary", {}).get("not_new_forward_evidence") is True
            and bad_json_report.get("evidence_boundary", {}).get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and "Traceback" not in bad_json_cli.stdout
            and "Traceback" not in bad_json_cli.stderr,
            "cli_json_invalid_root_structured_error",
            "CLI JSON mode reports invalid status roots as structured no-deletion errors instead of Python tracebacks",
        ),
        require(
            bad_text_cli.returncode == 2
            and "Mode: error" in bad_text_cli.stdout
            and "Refusing to inspect a non-project status-validation root" in bad_text_cli.stdout
            and VALID_EVIDENCE_SCOPE_LINE in bad_text_cli.stdout
            and "Boundary: validation scratch cleanup is operational hygiene only" in bad_text_cli.stdout
            and "Traceback" not in bad_text_cli.stdout
            and "Traceback" not in bad_text_cli.stderr,
            "cli_text_invalid_root_traceback_free",
            "CLI text mode reports invalid status roots as operator-readable errors with the evidence boundary instead of Python tracebacks",
        ),
        require(
            cleanup.EVIDENCE_BOUNDARY.get("not_new_forward_evidence") is True
            and cleanup.EVIDENCE_BOUNDARY.get("not_current_day_scanner_result") is True
            and cleanup.EVIDENCE_BOUNDARY.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and cleanup.EVIDENCE_BOUNDARY.get("not_settled_roi_evidence") is True
            and cleanup.EVIDENCE_BOUNDARY.get("not_live_profitability_evidence") is True
            and cleanup.EVIDENCE_BOUNDARY.get("not_promotion_readiness_evidence") is True
            and cleanup.EVIDENCE_BOUNDARY.get("not_real_money_evidence") is True,
            "cleanup_evidence_boundary",
            "cleanup helper publishes a no-new-evidence boundary for low-disk operational hygiene",
        ),
        require(
            dry_report.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and dry_report.get("evidence_boundary", {}).get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and cli_dry_report.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and cli_dry_report.get("evidence_boundary", {}).get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE,
            "cleanup_reports_expose_valid_evidence_scope",
            "library and CLI JSON cleanup reports expose the exact valid_evidence_scope so scratch cleanup cannot be copied as paper-trade evidence",
        ),
        require(
            fixture_root_cleaned_after_checks,
            "validator_fixture_root_cleaned_after_checks",
            "cleanup-helper validator removes its own generated fixture root after collecting checks so it does not leave a disposable scratch root for the next cleanup dry-run",
        ),
    ]


def build_summary(checks: list[dict[str, Any]]) -> dict[str, Any]:
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    return {
        "suite_status": status,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "fixture_root": str(FIXTURE_ROOT.relative_to(BASE)),
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "fixture_cleanup": {
            "fixture_root_exists_after_checks": FIXTURE_ROOT.exists(),
            "missing_root_exists_after_checks": MISSING_ROOT.exists(),
            "validator_fixture_root_cleaned_after_checks": not FIXTURE_ROOT.exists() and not MISSING_ROOT.exists(),
            "cleanup_scope": "validator-owned fixture roots only",
            "not_evidence": True,
        },
        "evidence_boundary": cleanup.EVIDENCE_BOUNDARY,
        "summary": {
            "current_read": (
                "validation_scratch_cleanup.py is dry-run-first and only removes generated "
                "status-validation scratch roots under out/status_validation named _tmp or ending in "
                "_fixture when --apply is explicitly supplied, refuses non-project roots and "
                "project-local status_validation lookalikes, refuses file roots, and collapses "
                "nested scratch roots to their top disposable parent while ignoring scratch-like "
                "symlinks, reports allowed missing status roots explicitly, and returns structured "
                "traceback-free CLI errors for invalid roots, while publishing a 512 MiB low-disk "
                "warning threshold and machine-readable before/after disk-pressure fields; "
                "it also publishes reclaimable scratch bytes, estimated post-cleanup free space, "
                "and a structured flag for cases where validation scratch cleanup is insufficient "
                "to clear the warning threshold; the validator removes its own generated fixture root "
                "after checks so repeated validation does not create a cleanup-loop scratch root; "
                f"library/CLI reports and this direct validator report expose exact {VALID_EVIDENCE_SCOPE_LINE}; "
                "this is low-disk operational hygiene only, not scanner, ROI, promotion, "
                "live-profitability, bankroll, or real-money evidence"
            )
        },
    }


def write_outputs(summary: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Validation Scratch Cleanup Validation",
        "",
        "This report checks the dry-run-first cleanup helper for generated validation scratch roots.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Checks: {summary['check_count']}",
        f"- Result: {summary['suite_status'].upper()}",
        "",
        "## Checks",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for check in summary["checks"]:
        lines.append(f"| {check['check']} | {check['status'].upper()} | {check['detail']} |")
    lines.extend(
        [
            "",
            "## Current Read",
            "",
            f"- {summary['summary']['current_read']}",
            "",
            "## Evidence Boundary",
            "",
            "- Scratch cleanup is operational hygiene only.",
            f"- {VALID_EVIDENCE_SCOPE_LINE}",
            "- It is not new forward evidence, not a current-day scanner result, not settled ROI, not live-profitability evidence, not promotion-readiness evidence, and not real-money evidence.",
        ]
    )
    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    checks = build_checks()
    summary = build_summary(checks)
    write_outputs(summary)
    print(f"Wrote {MD_PATH}")
    print(f"Wrote {JSON_PATH}")
    return 0 if summary["suite_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
