#!/usr/bin/env python3
"""
Dry-run-first cleanup for generated validation scratch roots.

This helper only targets disposable validator scratch directories under
out/status_validation: directories named "_tmp" or ending in "_fixture".
It does not touch saved validation reports, live daily run artifacts, ledgers,
rule files, or paper-trade evidence surfaces.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
DEFAULT_STATUS_ROOT = BASE / "out" / "status_validation"
LOW_DISK_WARNING_THRESHOLD_BYTES = 512 * 1024 * 1024
VALID_EVIDENCE_SCOPE = "validation_scratch_cleanup_operational_hygiene_only"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "validation scratch cleanup helper",
    "valid_use": "dry-run inventory and optional cleanup of generated validator scratch roots",
    "target_scope": "out/status_validation directories named _tmp or ending in _fixture only",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "not_new_forward_evidence": True,
    "not_current_day_scanner_result": True,
    "not_live_paper_trade_ledger": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_real_money_evidence": True,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="remove the discovered validation scratch roots after listing them",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of a text table",
    )
    parser.add_argument(
        "--status-root",
        default=str(DEFAULT_STATUS_ROOT),
        help="advanced/test hook: status-validation root to inspect",
    )
    return parser.parse_args()


def is_safe_status_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(DEFAULT_STATUS_ROOT.resolve())
    except ValueError:
        return False
    return True


def is_scratch_dir(path: Path) -> bool:
    return not path.is_symlink() and path.is_dir() and (path.name == "_tmp" or path.name.endswith("_fixture"))


def dir_size_bytes(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        if child.is_file() or child.is_symlink():
            try:
                total += child.lstat().st_size
            except FileNotFoundError:
                continue
    return total


def human_bytes(value: int) -> str:
    units = ["B", "KiB", "MiB", "GiB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} {unit}"
        amount /= 1024
    return f"{value} B"


def disk_pressure_fields(before_free_bytes: int, after_free_bytes: int) -> dict[str, Any]:
    before_low = before_free_bytes < LOW_DISK_WARNING_THRESHOLD_BYTES
    after_low = after_free_bytes < LOW_DISK_WARNING_THRESHOLD_BYTES
    warning = ""
    if after_low:
        warning = (
            f"Disk free after cleanup is below {human_bytes(LOW_DISK_WARNING_THRESHOLD_BYTES)}; "
            "if disposable validation scratch is small, look for non-project caches or run only narrow validators."
        )
    return {
        "low_disk_warning_threshold_bytes": LOW_DISK_WARNING_THRESHOLD_BYTES,
        "low_disk_warning_threshold_human": human_bytes(LOW_DISK_WARNING_THRESHOLD_BYTES),
        "disk_free_before_below_threshold": before_low,
        "disk_free_after_below_threshold": after_low,
        "low_disk_warning": warning,
    }


def scratch_cleanup_estimate_fields(
    free_before_bytes: int,
    free_after_bytes: int,
    scratch_bytes: int,
    apply: bool,
) -> dict[str, Any]:
    estimated_after_bytes = free_after_bytes if apply else free_before_bytes + scratch_bytes
    estimated_after_below = estimated_after_bytes < LOW_DISK_WARNING_THRESHOLD_BYTES
    warning = ""
    if estimated_after_below:
        warning = (
            f"Removing all discovered validation scratch roots would still leave disk free below "
            f"{human_bytes(LOW_DISK_WARNING_THRESHOLD_BYTES)}; investigate non-project caches or run only narrow validators."
        )
    return {
        "reclaimable_validation_scratch_bytes": scratch_bytes,
        "reclaimable_validation_scratch_human": human_bytes(scratch_bytes),
        "estimated_disk_free_after_scratch_cleanup_bytes": estimated_after_bytes,
        "estimated_disk_free_after_scratch_cleanup_human": human_bytes(estimated_after_bytes),
        "validation_scratch_cleanup_insufficient_for_threshold": estimated_after_below,
        "validation_scratch_cleanup_insufficient_warning": warning,
    }


def scratch_roots(status_root: Path) -> list[Path]:
    if not status_root.exists():
        return []
    roots: list[Path] = []
    for path in status_root.rglob("*"):
        if not is_scratch_dir(path):
            continue
        if any(parent in roots for parent in path.parents):
            continue
        roots.append(path)
    return sorted(roots, key=lambda item: str(item.relative_to(BASE)))


def build_report(status_root: Path, apply: bool = False) -> dict[str, Any]:
    resolved_root = status_root.resolve()
    if not is_safe_status_root(resolved_root):
        raise ValueError(f"Refusing to inspect a non-project status-validation root: {status_root}")
    if resolved_root.exists() and not resolved_root.is_dir():
        raise ValueError(f"Refusing to inspect a non-directory status-validation root: {status_root}")

    status_root_exists = resolved_root.exists()
    before_usage = shutil.disk_usage(BASE)
    roots = scratch_roots(resolved_root)
    rows = [
        {
            "path": str(path.relative_to(BASE)),
            "bytes": dir_size_bytes(path),
        }
        for path in roots
    ]
    total_scratch_bytes = sum(row["bytes"] for row in rows)

    removed: list[str] = []
    if apply:
        for path in sorted(roots, key=lambda item: len(item.parts), reverse=True):
            if not is_scratch_dir(path):
                continue
            shutil.rmtree(path)
            removed.append(str(path.relative_to(BASE)))

    after_usage = shutil.disk_usage(BASE)
    pressure = disk_pressure_fields(before_usage.free, after_usage.free)
    scratch_estimate = scratch_cleanup_estimate_fields(
        before_usage.free,
        after_usage.free,
        total_scratch_bytes,
        apply,
    )
    report = {
        "mode": "apply" if apply else "dry_run",
        "status_root": str(resolved_root.relative_to(BASE)),
        "status_root_exists": status_root_exists,
        "status_root_missing": not status_root_exists,
        "scratch_root_count": len(rows),
        "total_scratch_bytes": total_scratch_bytes,
        "total_scratch_human": human_bytes(total_scratch_bytes),
        "disk_free_before_bytes": before_usage.free,
        "disk_free_after_bytes": after_usage.free,
        "disk_free_before_human": human_bytes(before_usage.free),
        "disk_free_after_human": human_bytes(after_usage.free),
        "removed_paths": removed,
        "scratch_roots": rows,
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        **pressure,
        **scratch_estimate,
    }
    if not status_root_exists:
        report["warning"] = "status-validation root does not exist; nothing was inspected or removed"
    return report


def print_text(report: dict[str, Any]) -> None:
    print("Validation scratch cleanup")
    print(f"Mode: {report['mode']}")
    print(f"Status root: {report['status_root']}")
    if report.get("status_root_missing"):
        print("Warning: status-validation root does not exist; nothing was inspected or removed.")
    print(f"Scratch roots: {report['scratch_root_count']}")
    print(f"Scratch total: {report['total_scratch_human']}")
    print(f"Disk free before: {report['disk_free_before_human']}")
    print(f"Disk free after: {report['disk_free_after_human']}")
    print(f"Estimated free after listed scratch cleanup: {report['estimated_disk_free_after_scratch_cleanup_human']}")
    print(f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}")
    if report.get("low_disk_warning"):
        print(f"Warning: {report['low_disk_warning']}")
    if report.get("validation_scratch_cleanup_insufficient_warning"):
        print(f"Warning: {report['validation_scratch_cleanup_insufficient_warning']}")
    print(
        "Boundary: validation scratch cleanup is operational hygiene only, not scanner, ROI, "
        "promotion, live-profitability, bankroll, or real-money evidence."
    )
    for row in sorted(report["scratch_roots"], key=lambda item: item["bytes"], reverse=True):
        print(f"- {row['path']}: {human_bytes(row['bytes'])}")
    if report["mode"] == "dry_run":
        print("Dry run only. Rerun with --apply to remove these scratch roots after review.")
    elif report["removed_paths"]:
        print("Removed:")
        for path in report["removed_paths"]:
            print(f"- {path}")


def main() -> int:
    args = parse_args()
    try:
        report = build_report(Path(args.status_root), apply=args.apply)
    except ValueError as exc:
        report = {
            "mode": "error",
            "status_root": args.status_root,
            "error": str(exc),
            "scratch_root_count": 0,
            "removed_paths": [],
            "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
            "evidence_boundary": EVIDENCE_BOUNDARY,
        }
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print("Validation scratch cleanup")
            print("Mode: error")
            print(f"Status root: {args.status_root}")
            print(f"Error: {exc}")
            print(f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}")
            print(
                "Boundary: validation scratch cleanup is operational hygiene only, not scanner, ROI, "
                "promotion, live-profitability, bankroll, or real-money evidence."
            )
        return 2
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
