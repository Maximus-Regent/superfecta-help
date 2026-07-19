#!/usr/bin/env python3
"""
Build the expanded per-lane summary artifact.

Purpose:
- keep each lane summary readable and reproducible
- avoid shell-only summary augmentation so the section layout can be fixture-validated
- tolerate missing detail artifacts with explicit placeholders instead of a failing append step
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = BASE / "out" / "paper_trade_lane_summary.txt"
LANE_SUMMARY_VALID_EVIDENCE_SCOPE = "paper_trade_lane_summary_navigation_context_only"
LANE_SUMMARY_EVIDENCE_BOUNDARY_TEXT = (
    "Lane-summary output is per-lane operator navigation/context metadata only; quick files, "
    "compact lane snapshots, lifted decision-gate wording, Phase 8 review-floor cautions, "
    "pipeline context, clean-empty/no-target routing, issue routing, and saved-live rebuild "
    "cleanliness are not current-day scanner evidence by themselves, live paper-trade ledger "
    "evidence, settled ROI, promotion readiness, live-profitability evidence, real-money support, "
    "or BAQ-as-BEL evidence."
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build the expanded per-lane summary artifact")
    p.add_argument("--base-summary", required=True, help="Path to the one-line base lane summary")
    p.add_argument("--next-steps-text", required=True, help="Path to the lane next-steps text artifact")
    p.add_argument("--next-steps-md", required=True, help="Path to the lane next-steps markdown artifact")
    p.add_argument("--lane-monitor-text", required=True, help="Path to the lane monitor text artifact")
    p.add_argument("--lane-monitor-md", required=True, help="Path to the lane monitor markdown artifact")
    p.add_argument("--forward-check-text", required=True, help="Path to the forward-check text artifact")
    p.add_argument("--forward-check-md", required=True, help="Path to the forward-check markdown artifact")
    p.add_argument("--settlement-ledger", required=True, help="Path to the settlement ledger")
    p.add_argument("--display-summary", help="Optional summary path to show in quick files when writing through a temp file")
    p.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output path")
    return p.parse_args()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BASE.resolve()))
    except Exception:
        return str(path)


def read_text(path: Path, missing_label: str) -> str:
    if not path.exists() or not path.is_file():
        return f"[{missing_label}: {rel(path)}]"
    text = path.read_text(encoding="utf-8").strip()
    return text if text else f"[{missing_label}: {rel(path)} is empty]"


def extract_field(path: Path, missing_label: str, label: str, missing_field_label: str | None = None) -> str:
    if not path.exists() or not path.is_file():
        return f"[{missing_label}: {rel(path)}]"
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return f"[{missing_label}: {rel(path)} is empty]"
    match = re.search(rf"(?:^|\n)\s*-\s*{re.escape(label)}:\s*(.+)", text)
    if not match:
        field_label = missing_field_label or f"missing {label.lower()}"
        return f"[{field_label}: {rel(path)}]"
    return match.group(1).strip()


def extract_optional_field(path: Path, label: str) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"(?:^|\n)\s*-\s*{re.escape(label)}:\s*(.+)", text)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def enrich_base_summary(base_summary: str, roi_coverage: str | None) -> str:
    if not roi_coverage:
        return base_summary
    patterns = [
        r"^(\d+)/(\d+) settled races have return values \((\d+) still missing return/cost coverage\)$",
        r"^(\d+)/(\d+) settled races are ROI-complete with return/cost/timestamp coverage \((\d+) still missing coverage\)$",
    ]
    match = next((match for pattern in patterns if (match := re.search(pattern, roi_coverage))), None)
    if not match:
        return base_summary
    covered, settled, missing = match.groups()
    old = f"ROI coverage {covered}/{settled}"
    new = f"ROI coverage {covered}/{settled} ({missing} missing)"
    return base_summary.replace(old, new, 1)


def render_text(args: argparse.Namespace) -> str:
    base_summary = read_text(Path(args.base_summary), "missing base summary")
    next_steps_text = read_text(Path(args.next_steps_text), "missing next-steps text")
    lane_monitor_text = read_text(Path(args.lane_monitor_text), "missing lane-monitor text")
    forward_check_text = read_text(Path(args.forward_check_text), "missing forward-check text")
    settlement_integrity = extract_field(Path(args.next_steps_text), "missing next-steps text", "Settled races", "missing settlement integrity")
    roi_coverage = extract_field(Path(args.next_steps_text), "missing next-steps text", "ROI coverage", "missing ROI coverage")
    decision_gate = extract_optional_field(Path(args.forward_check_text), "Decision gate") or extract_optional_field(Path(args.lane_monitor_text), "Decision gate")
    decision_gate_caution = (
        extract_optional_field(Path(args.forward_check_md), "Decision-gate caution")
        or extract_optional_field(Path(args.lane_monitor_text), "Decision-gate caution")
        or extract_optional_field(Path(args.next_steps_text), "Decision-gate caution")
    )
    why_now = extract_optional_field(Path(args.next_steps_text), "Why")
    latest_run_context = extract_optional_field(Path(args.next_steps_text), "Latest run context")
    operator_read_gate_issue_flags = extract_optional_field(Path(args.next_steps_text), "Operator read-gate issue flags")
    base_summary = enrich_base_summary(base_summary, roi_coverage)
    forward_check_text = enrich_base_summary(forward_check_text, roi_coverage)

    lines = [
        base_summary,
        "",
        "Evidence frame:",
        f"- valid_evidence_scope={LANE_SUMMARY_VALID_EVIDENCE_SCOPE}",
        f"- Boundary: {LANE_SUMMARY_EVIDENCE_BOUNDARY_TEXT}",
        "",
        "Lane snapshot:",
        *([f"- Settlement integrity: {settlement_integrity}"] if settlement_integrity else []),
        *([f"- ROI coverage: {roi_coverage}"] if roi_coverage else []),
        *([f"- Decision gate: {decision_gate}"] if decision_gate else []),
        *([f"- Decision-gate caution: {decision_gate_caution}"] if decision_gate_caution else []),
        *([f"- Operator read-gate issue flags: {operator_read_gate_issue_flags}"] if operator_read_gate_issue_flags else []),
        *([f"- Why now: {why_now}"] if why_now else []),
        *([f"- Latest run context: {latest_run_context}"] if latest_run_context else []),
        "",
        "Quick files:",
        f"- Summary: {rel(Path(args.display_summary or args.output))}",
        f"- Next steps: {rel(Path(args.next_steps_md))}",
        f"- Lane monitor: {rel(Path(args.lane_monitor_md))}",
        f"- Forward check: {rel(Path(args.forward_check_md))}",
        f"- Settlement ledger: {rel(Path(args.settlement_ledger))}",
        "",
        "Forward check:",
        forward_check_text,
        f"Forward check detail: {rel(Path(args.forward_check_md))}",
        "",
        "Lane monitor:",
        lane_monitor_text,
        f"Lane monitor detail: {rel(Path(args.lane_monitor_md))}",
        "",
        "Next steps:",
        next_steps_text,
        f"Next steps detail: {rel(Path(args.next_steps_md))}",
        "",
    ]
    return "\n".join(lines)


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    content = render_text(args)
    write_output(Path(args.output), content)
    print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
