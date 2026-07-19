#!/usr/bin/env python3
"""
Generate the combined daily paper-trade summary.

Purpose:
- keep the top-level daily summary readable and reproducible
- avoid shell-only summary assembly so the quick-jump surface can be fixture-validated
- tolerate missing lane artifacts with explicit placeholders instead of a hard shell failure
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
DEFAULT_RIGHT_NOW = BASE / "PAPER_TRADE_NOW.md"
DEFAULT_OPS_HISTORY = BASE / "OPS_HISTORY.md"
DEFAULT_SETTLEMENT_AUDIT = BASE / "out" / "paper_trade_settlement_audit.md"
DEFAULT_PRIMARY_LANE = "phase7_current_paper"
DEFAULT_SHADOW_LANE = "phase8_shadow"
DEFAULT_PRIMARY_LABEL = "Phase 7 current paper basket (OP + CD rule components; target cards require preflight)"
DEFAULT_SHADOW_LABEL = "Phase 8 watch-list basket"
OPERATOR_READ_GATE_ISSUE_FLAGS = (
    "has_api_access_failure_context",
    "has_scanner_failure_boundary",
    "has_stale_cache_fallback_context",
)
DAILY_SUMMARY_VALID_EVIDENCE_SCOPE = "daily_operator_workflow_navigation_only"
DAILY_SUMMARY_EVIDENCE_BOUNDARY_TEXT = (
    "Daily summary output is combined operator workflow/navigation metadata only; quick jumps, inherited "
    "right-now snapshots, lane context, preflight notes, readiness lines, settlement-audit action routing, "
    "clean-empty/no-target routing, issue routing, and saved-live rebuild cleanliness are not current-day scanner "
    "evidence by themselves, live paper-trade ledger evidence, settled ROI, promotion readiness, live-profitability "
    "evidence, real-money support, or BAQ-as-BEL evidence."
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate the combined daily paper-trade summary")
    p.add_argument("--run-root", required=True, help="Run root directory for one YYYY-MM-DD daily run")
    p.add_argument("--primary-lane", default=DEFAULT_PRIMARY_LANE, help="Primary lane directory name under the run root")
    p.add_argument("--shadow-lane", default=DEFAULT_SHADOW_LANE, help="Shadow lane directory name under the run root")
    p.add_argument("--primary-label", default=DEFAULT_PRIMARY_LABEL, help="Human label for the primary lane section")
    p.add_argument("--shadow-label", default=DEFAULT_SHADOW_LABEL, help="Human label for the shadow lane section")
    p.add_argument("--right-now", default=str(DEFAULT_RIGHT_NOW), help="Top-level right-now markdown artifact to reference")
    p.add_argument("--ops-history", default=str(DEFAULT_OPS_HISTORY), help="Rolling ops-history markdown artifact to reference")
    p.add_argument("--settlement-audit", default=str(DEFAULT_SETTLEMENT_AUDIT), help="Settlement-ledger completeness audit markdown artifact to reference")
    p.add_argument("--output", help="Output path, defaults to <run-root>/daily_summary.txt")
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


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def right_now_json_path(markdown_path: Path) -> Path:
    if markdown_path.suffix:
        return markdown_path.with_suffix(".json")
    return markdown_path.parent / f"{markdown_path.name}.json"


def operator_issue_flags_line(gate: dict[str, Any]) -> str:
    parts = []
    for flag in OPERATOR_READ_GATE_ISSUE_FLAGS:
        value = gate.get(flag)
        if value is True:
            display = "true"
        elif value is False:
            display = "false"
        else:
            display = "missing"
        parts.append(f"{flag}={display}")
    return "; ".join(parts)


def extract_right_now_operator_read_gate(markdown_path: Path) -> dict[str, Any]:
    json_path = right_now_json_path(markdown_path)
    payload = read_json(json_path)
    if payload is None:
        return {
            "json_path": rel(json_path),
            "read": f"[missing or unreadable right-now JSON operator_read_gate: {rel(json_path)}]",
            "gate_status": "",
            "requires_refresh_before_evidence_read": None,
            "recommended_command": "",
            "issue_flags": operator_issue_flags_line({}),
        }
    gate = payload.get("operator_read_gate")
    if not isinstance(gate, dict):
        return {
            "json_path": rel(json_path),
            "read": f"[missing right-now JSON operator_read_gate: {rel(json_path)}]",
            "gate_status": "",
            "requires_refresh_before_evidence_read": None,
            "recommended_command": "",
            "issue_flags": operator_issue_flags_line({}),
        }
    return {
        "json_path": rel(json_path),
        "read": str(gate.get("read") or "").strip()
        or f"[blank right-now JSON operator_read_gate.read: {rel(json_path)}]",
        "gate_status": str(gate.get("gate_status") or "").strip(),
        "requires_refresh_before_evidence_read": gate.get("requires_refresh_before_evidence_read")
        if isinstance(gate.get("requires_refresh_before_evidence_read"), bool)
        else None,
        "recommended_command": str(gate.get("recommended_command") or "").strip(),
        "issue_flags": operator_issue_flags_line(gate),
    }


def normalize_track_list(raw_tracks: object) -> list[str]:
    if not isinstance(raw_tracks, list):
        return []
    tracks: list[str] = []
    for raw in raw_tracks:
        track = str(raw or "").strip().upper()
        if track and track not in tracks:
            tracks.append(track)
    return tracks


def format_excluded_track_aliases(tracks: list[str]) -> str:
    labels = []
    for track in tracks:
        if track == "BAQ":
            labels.append("BAQ (not treated as BEL)")
        else:
            labels.append(f"{track} (excluded from active/shadow aliases)")
    return ", ".join(labels)


def resolve_preflight_excluded_tracks(run_root: Path) -> list[str]:
    payload = read_json(run_root / "preflight_note.json")
    if payload is None:
        return []
    return normalize_track_list(payload.get("excluded_tracks"))


def settlement_audit_json_path(markdown_path: Path) -> Path:
    return markdown_path.with_suffix(".json")


def read_settlement_audit_lane(markdown_path: Path, lane_name: str) -> tuple[Path, dict[str, Any] | None, str]:
    json_path = settlement_audit_json_path(markdown_path)
    if not json_path.exists() or not json_path.is_file():
        return json_path, None, f"[missing settlement-audit JSON: {rel(json_path)}]"
    try:
        raw_payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return json_path, None, f"[malformed settlement-audit JSON: {rel(json_path)} ({exc.msg} at line {exc.lineno}, column {exc.colno})]"
    except Exception as exc:
        return json_path, None, f"[unreadable settlement-audit JSON: {rel(json_path)} ({exc.__class__.__name__})]"
    if not isinstance(raw_payload, dict):
        return json_path, None, f"[invalid-shape settlement-audit JSON: {rel(json_path)} expected object, got {type(raw_payload).__name__}]"
    payload = raw_payload
    lanes = payload.get("lanes")
    if not isinstance(lanes, list):
        return json_path, None, f"[missing settlement-audit lanes list: {rel(json_path)}]"
    for lane in lanes:
        if isinstance(lane, dict) and lane.get("name") == lane_name:
            return json_path, lane, ""
    return json_path, None, ""


def extract_settlement_audit_action(markdown_path: Path, lane_name: str, label: str) -> tuple[str, str]:
    json_path, lane, error = read_settlement_audit_lane(markdown_path, lane_name)
    if error:
        return error, ""
    if lane is None:
        return f"[missing {label} settlement-audit lane: {rel(json_path)}]", ""
    action = str(lane.get("next_action") or "").strip()
    reason = str(lane.get("next_action_reason") or "").strip()
    if not action:
        return f"[missing {label} settlement-audit next_action: {rel(json_path)}]", reason
    return action, reason


def extract_settlement_audit_promotion_gate(markdown_path: Path, lane_name: str) -> tuple[str, str]:
    _, lane, error = read_settlement_audit_lane(markdown_path, lane_name)
    if error or lane is None:
        return "", ""
    gate = lane.get("promotion_gate")
    if not isinstance(gate, dict):
        return "", ""
    gate_read = str(gate.get("gate_read") or "").strip()
    rule_rows = gate.get("rule_progress")
    progress_bits: list[str] = []
    if isinstance(rule_rows, list):
        for row in rule_rows:
            if not isinstance(row, dict):
                continue
            rule_id = str(row.get("rule_id") or "").strip()
            if not rule_id:
                continue
            promotion_progress = str(row.get("promotion_progress") or "").strip()
            scorecard_tier = str(row.get("scorecard_tier") or "").strip()
            tier_suffix = f" ({scorecard_tier})" if scorecard_tier else ""
            if promotion_progress:
                progress_bits.append(f"{rule_id}{tier_suffix} {promotion_progress}")
            else:
                progress_bits.append(f"{rule_id}{tier_suffix} {row.get('roi_complete_settled_rows', 0)} ROI-complete")
    return gate_read, "; ".join(progress_bits)


def resolve_preflight_surface(run_root: Path) -> tuple[Path, str]:
    text_path = run_root / "preflight_note.txt"
    json_path = run_root / "preflight_note.json"

    if text_path.exists() and text_path.is_file():
        text = text_path.read_text(encoding="utf-8").strip()
        if text:
            return text_path, text

    payload = read_json(json_path)
    if payload is not None:
        note = str(payload.get("note") or "").strip()
        if note:
            return json_path, note

    return text_path, read_text(text_path, "missing preflight note")


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


def strip_inline_markdown(value: str) -> str:
    return value.replace("**", "").replace("`", "").strip()


def extract_right_now_field(path: Path, label: str) -> str | None:
    value = extract_optional_field(path, label)
    if value is None:
        return None
    cleaned = strip_inline_markdown(value)
    return cleaned or None


def extract_state(path: Path, missing_label: str, missing_field_label: str) -> str:
    return extract_field(path, missing_label, "State", missing_field_label=missing_field_label)


def extract_progress(path: Path, missing_label: str, label: str, missing_field_label: str) -> str:
    return extract_field(path, missing_label, label, missing_field_label=missing_field_label)


def extract_recent_context(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?:^|\n)\s*-\s*(Latest run context:.+)", text)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def extract_why_now(path: Path) -> str | None:
    return extract_optional_field(path, "Why")


def has_readable_text(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        return bool(path.read_text(encoding="utf-8").strip())
    except Exception:
        return False


def resolve_next_steps_text_source(lane_dir: Path) -> Path:
    text_path = lane_dir / "next_steps.txt"
    if has_readable_text(text_path):
        return text_path
    markdown_path = lane_dir / "next_steps.md"
    if has_readable_text(markdown_path):
        return markdown_path
    return text_path


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    run_root = Path(args.run_root).expanduser().resolve()
    output = Path(args.output).expanduser() if args.output else run_root / "daily_summary.txt"
    primary_dir = run_root / args.primary_lane
    shadow_dir = run_root / args.shadow_lane
    right_now_path = Path(args.right_now).expanduser()
    right_now_gate = extract_right_now_operator_read_gate(right_now_path)
    settlement_audit_path = Path(args.settlement_audit).expanduser()
    primary_audit_action, primary_audit_reason = extract_settlement_audit_action(settlement_audit_path, "primary", "primary")
    shadow_audit_action, shadow_audit_reason = extract_settlement_audit_action(settlement_audit_path, "shadow", "shadow")
    shadow_promotion_gate, shadow_promotion_progress = extract_settlement_audit_promotion_gate(settlement_audit_path, "shadow")
    preflight_path, preflight_note = resolve_preflight_surface(run_root)
    preflight_excluded_tracks = resolve_preflight_excluded_tracks(run_root)
    primary_summary = primary_dir / "summary.txt"
    shadow_summary = shadow_dir / "summary.txt"
    primary_next_steps_txt = resolve_next_steps_text_source(primary_dir)
    shadow_next_steps_txt = resolve_next_steps_text_source(shadow_dir)

    return {
        "run_date": run_root.name,
        "run_root": rel(run_root),
        "output": str(output),
        "right_now": rel(right_now_path),
        "right_now_json": right_now_gate["json_path"],
        "ops_history": rel(Path(args.ops_history).expanduser()),
        "settlement_audit": rel(settlement_audit_path),
        "primary_settlement_audit_next_action": primary_audit_action,
        "primary_settlement_audit_next_action_reason": primary_audit_reason,
        "shadow_settlement_audit_next_action": shadow_audit_action,
        "shadow_settlement_audit_next_action_reason": shadow_audit_reason,
        "shadow_settlement_audit_promotion_gate": shadow_promotion_gate,
        "shadow_settlement_audit_rule_progress": shadow_promotion_progress,
        "right_now_focus": extract_right_now_field(right_now_path, "Focus") or "",
        "right_now_timing": extract_right_now_field(right_now_path, "Timing") or "",
        "right_now_run_freshness": extract_right_now_field(right_now_path, "Run freshness") or "",
        "right_now_stale_snapshot_note": extract_right_now_field(right_now_path, "Stale snapshot note") or "",
        "right_now_ops_bucket": extract_right_now_field(right_now_path, "Latest ops bucket") or "",
        "right_now_operator_read_gate": right_now_gate["read"],
        "right_now_operator_read_gate_status": right_now_gate["gate_status"],
        "right_now_operator_read_gate_requires_refresh": right_now_gate[
            "requires_refresh_before_evidence_read"
        ],
        "right_now_operator_read_gate_recommended_command": right_now_gate["recommended_command"],
        "right_now_operator_read_gate_issue_flags": right_now_gate["issue_flags"],
        "preflight_note_path": rel(preflight_path),
        "preflight_excluded_tracks": preflight_excluded_tracks,
        "preflight_excluded_track_count": len(preflight_excluded_tracks),
        "preflight_excluded_track_summary": format_excluded_track_aliases(preflight_excluded_tracks),
        "valid_evidence_scope": DAILY_SUMMARY_VALID_EVIDENCE_SCOPE,
        "evidence_boundary_text": DAILY_SUMMARY_EVIDENCE_BOUNDARY_TEXT,
        "evidence_frame_label": "Workflow and navigation surface",
        "evidence_frame_summary": "This daily summary is an operator workflow surface, not a profit-proof or CI-backed forward-validation report.",
        "evidence_frame_detail": "It combines the current run's preflight note, lane summaries, next-step states, settlement/ROI coverage, and quick-jump links, while keeping the lane hierarchy tied to the frozen evidence standard.",
        "evidence_frame_limitation": "Use it to decide what to read or do next; treat forward performance claims as pending until settled paper trades with usable return/cost coverage accumulate in the underlying lane artifacts.",
        "primary_summary_path": rel(primary_summary),
        "primary_decision_gate": extract_optional_field(primary_summary, "Decision gate") or "",
        "primary_next_steps": rel(primary_dir / "next_steps.md"),
        "primary_next_steps_source": rel(primary_next_steps_txt),
        "primary_next_steps_state": extract_state(primary_next_steps_txt, "missing primary next-steps text", "missing primary next-steps state"),
        "primary_recent_run_context": extract_recent_context(primary_next_steps_txt) or "",
        "primary_why_now": extract_why_now(primary_next_steps_txt) or "",
        "primary_sidecar_action": extract_optional_field(primary_next_steps_txt, "Sidecar action") or "",
        "primary_recheck_command": extract_optional_field(primary_next_steps_txt, "Recheck command") or "",
        "primary_first_read_progress": extract_progress(primary_next_steps_txt, "missing primary next-steps text", "First statistical-read progress", "missing primary first-read progress"),
        "primary_portfolio_review_progress": extract_progress(primary_next_steps_txt, "missing primary next-steps text", "Broader portfolio-review progress", "missing primary portfolio-review progress"),
        "primary_settlement_integrity": extract_field(primary_next_steps_txt, "missing primary next-steps text", "Settled races", "missing primary settlement integrity"),
        "primary_roi_coverage": extract_field(primary_next_steps_txt, "missing primary next-steps text", "ROI coverage", "missing primary ROI coverage"),
        "primary_roi_gap_summary": extract_optional_field(primary_next_steps_txt, "Settled rows missing ROI coverage") or "",
        "primary_lane_monitor": rel(primary_dir / "lane_monitor.md"),
        "primary_forward_check": rel(primary_dir / "forward_check.md"),
        "shadow_summary_path": rel(shadow_summary),
        "shadow_decision_gate": extract_optional_field(shadow_summary, "Decision gate") or "",
        "shadow_next_steps": rel(shadow_dir / "next_steps.md"),
        "shadow_next_steps_source": rel(shadow_next_steps_txt),
        "shadow_next_steps_state": extract_state(shadow_next_steps_txt, "missing shadow next-steps text", "missing shadow next-steps state"),
        "shadow_recent_run_context": extract_recent_context(shadow_next_steps_txt) or "",
        "shadow_why_now": extract_why_now(shadow_next_steps_txt) or "",
        "shadow_sidecar_action": extract_optional_field(shadow_next_steps_txt, "Sidecar action") or "",
        "shadow_recheck_command": extract_optional_field(shadow_next_steps_txt, "Recheck command") or "",
        "shadow_first_read_progress": extract_progress(shadow_next_steps_txt, "missing shadow next-steps text", "First statistical-read progress", "missing shadow first-read progress"),
        "shadow_portfolio_review_progress": extract_progress(shadow_next_steps_txt, "missing shadow next-steps text", "Broader portfolio-review progress", "missing shadow portfolio-review progress"),
        "shadow_settlement_integrity": extract_field(shadow_next_steps_txt, "missing shadow next-steps text", "Settled races", "missing shadow settlement integrity"),
        "shadow_roi_coverage": extract_field(shadow_next_steps_txt, "missing shadow next-steps text", "ROI coverage", "missing shadow ROI coverage"),
        "shadow_roi_gap_summary": extract_optional_field(shadow_next_steps_txt, "Settled rows missing ROI coverage") or "",
        "shadow_lane_monitor": rel(shadow_dir / "lane_monitor.md"),
        "shadow_forward_check": rel(shadow_dir / "forward_check.md"),
        "preflight_note": preflight_note,
        "primary_label": args.primary_label,
        "primary_summary": read_text(primary_summary, "missing primary summary"),
        "shadow_label": args.shadow_label,
        "shadow_summary": read_text(shadow_summary, "missing shadow summary"),
    }


def render_text(payload: dict[str, Any]) -> str:
    lines = [
        f"Daily portfolio observation summary ({payload['run_date']})",
        "",
        "Quick jump index:",
        f"- Right now: {payload['right_now']}",
        f"- Right-now JSON: {payload['right_now_json']}",
        f"- Rolling ops history: {payload['ops_history']}",
        f"- Settlement audit: {payload['settlement_audit']}",
        f"- Preflight note: {payload['preflight_note_path']}",
        f"- Primary summary: {payload['primary_summary_path']}",
        f"- Primary next steps: {payload['primary_next_steps']}",
        f"- Primary lane monitor: {payload['primary_lane_monitor']}",
        f"- Primary forward check: {payload['primary_forward_check']}",
        f"- Shadow summary: {payload['shadow_summary_path']}",
        f"- Shadow next steps: {payload['shadow_next_steps']}",
        f"- Shadow lane monitor: {payload['shadow_lane_monitor']}",
        f"- Shadow forward check: {payload['shadow_forward_check']}",
        "",
        "Right-now snapshot:",
        *([f"- Current operator focus: {payload['right_now_focus']}"] if payload.get('right_now_focus') else []),
        *([f"- Current timing: {payload['right_now_timing']}"] if payload.get('right_now_timing') else []),
        *([f"- Current run freshness: {payload['right_now_run_freshness']}"] if payload.get('right_now_run_freshness') else []),
        *([f"- Current stale snapshot note: {payload['right_now_stale_snapshot_note']}"] if payload.get('right_now_stale_snapshot_note') else []),
        *([f"- Current ops bucket: {payload['right_now_ops_bucket']}"] if payload.get('right_now_ops_bucket') else []),
        f"- Current operator read gate: {payload['right_now_operator_read_gate']}",
        *([f"- Current operator read-gate status: {payload['right_now_operator_read_gate_status']}"] if payload.get('right_now_operator_read_gate_status') else []),
        *([f"- Current read gate requires refresh: {payload['right_now_operator_read_gate_requires_refresh']}"] if payload.get('right_now_operator_read_gate_requires_refresh') is not None else []),
        *([f"- Current read-gate command: {payload['right_now_operator_read_gate_recommended_command']}"] if payload.get('right_now_operator_read_gate_recommended_command') else []),
        f"- Current operator read-gate issue flags: {payload['right_now_operator_read_gate_issue_flags']}",
        "",
        "Preflight note:",
        payload['preflight_note'],
        *([f"Excluded track aliases: {payload['preflight_excluded_track_summary']}"] if payload.get('preflight_excluded_track_summary') else []),
        "",
        "Evidence frame:",
        f"- valid_evidence_scope={payload['valid_evidence_scope']}",
        f"- Boundary: {payload['evidence_boundary_text']}",
        f"- {payload['evidence_frame_label']}: {payload['evidence_frame_summary']}",
        f"- Detail: {payload['evidence_frame_detail']}",
        f"- Limitation: {payload['evidence_frame_limitation']}",
        "",
        "Current live hierarchy:",
        "- Primary lane: `OP_DURABLE_K7` remains the anchor; `CD_CORE_K8` remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion.",
        "- Shadow lane: `OP_REFINED_K7` remains the lead same-family challenger; the rest of Phase 8 stays research/watch only until it earns more forward evidence.",
        "- BAQ (not treated as BEL): never substitute BAQ for the dormant BEL rule or count BAQ as BEL forward evidence.",
        "- Settlement-audit actions are ledger-readiness guidance only; they are not new forward evidence by themselves.",
        f"- Primary settlement-audit action: {payload['primary_settlement_audit_next_action']}" + (f" — {payload['primary_settlement_audit_next_action_reason']}" if payload.get('primary_settlement_audit_next_action_reason') else ""),
        f"- Shadow settlement-audit action: {payload['shadow_settlement_audit_next_action']}" + (f" — {payload['shadow_settlement_audit_next_action_reason']}" if payload.get('shadow_settlement_audit_next_action_reason') else ""),
        *([f"- Shadow settlement-audit promotion gate: {payload['shadow_settlement_audit_promotion_gate']}"] if payload.get('shadow_settlement_audit_promotion_gate') else []),
        *([f"- Shadow per-rule promotion coverage: {payload['shadow_settlement_audit_rule_progress']}"] if payload.get('shadow_settlement_audit_rule_progress') else []),
        f"- Primary next-step source artifact: {payload['primary_next_steps_source']}",
        f"- Primary next-step state: {payload['primary_next_steps_state']}",
        *([f"- Primary decision gate: {payload['primary_decision_gate']}"] if payload.get('primary_decision_gate') else []),
        *([f"- Primary lane context: {payload['primary_recent_run_context']}"] if payload.get('primary_recent_run_context') else []),
        *([f"- Primary lane why now: {payload['primary_why_now']}"] if payload.get('primary_why_now') else []),
        *([f"- Primary sidecar action: {payload['primary_sidecar_action']}"] if payload.get('primary_sidecar_action') else []),
        *([f"- Primary recheck command: {payload['primary_recheck_command']}"] if payload.get('primary_recheck_command') else []),
        f"- Primary readiness: first read {payload['primary_first_read_progress']} | broader review {payload['primary_portfolio_review_progress']}",
        *([f"- Primary settlement integrity: {payload['primary_settlement_integrity']}"] if payload.get('primary_settlement_integrity') else []),
        *([f"- Primary ROI coverage: {payload['primary_roi_coverage']}"] if payload.get('primary_roi_coverage') else []),
        *([f"- Primary ROI coverage gaps: {payload['primary_roi_gap_summary']}"] if payload.get('primary_roi_gap_summary') else []),
        f"- Shadow next-step source artifact: {payload['shadow_next_steps_source']}",
        f"- Shadow next-step state: {payload['shadow_next_steps_state']}",
        *([f"- Shadow decision gate: {payload['shadow_decision_gate']}"] if payload.get('shadow_decision_gate') else []),
        *([f"- Shadow lane context: {payload['shadow_recent_run_context']}"] if payload.get('shadow_recent_run_context') else []),
        *([f"- Shadow lane why now: {payload['shadow_why_now']}"] if payload.get('shadow_why_now') else []),
        *([f"- Shadow sidecar action: {payload['shadow_sidecar_action']}"] if payload.get('shadow_sidecar_action') else []),
        *([f"- Shadow recheck command: {payload['shadow_recheck_command']}"] if payload.get('shadow_recheck_command') else []),
        f"- Shadow readiness: first read {payload['shadow_first_read_progress']} | broader review {payload['shadow_portfolio_review_progress']}",
        *([f"- Shadow settlement integrity: {payload['shadow_settlement_integrity']}"] if payload.get('shadow_settlement_integrity') else []),
        *([f"- Shadow ROI coverage: {payload['shadow_roi_coverage']}"] if payload.get('shadow_roi_coverage') else []),
        *([f"- Shadow ROI coverage gaps: {payload['shadow_roi_gap_summary']}"] if payload.get('shadow_roi_gap_summary') else []),
        "",
        f"PRIMARY: {payload['primary_label']}",
        payload['primary_summary'],
        "",
        f"SHADOW: {payload['shadow_label']}",
        payload['shadow_summary'],
        "",
        f"Artifacts root: {payload['run_root']}",
        "",
    ]
    return "\n".join(lines)


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    payload = build_payload(args)
    content = render_text(payload)
    write_output(Path(payload["output"]), content)
    print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
