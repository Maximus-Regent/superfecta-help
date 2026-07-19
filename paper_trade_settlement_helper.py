#!/usr/bin/env python3
"""
Human-facing helper for the paper-trade settlement ledger.

Purpose:
- list open settlement rows cleanly so pending races are easy to see
- update one row by signal_key without hand-editing raw CSV
- keep the forward-check workflow operational and understandable
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shlex
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
DEFAULT_SETTLEMENT_LEDGER = BASE / "paper_trades" / "phase7_current_paper_paper_trade_settlements.csv"
FIELDS = [
    "signal_key",
    "scan_ts",
    "rule_id",
    "track",
    "card_name",
    "race_number",
    "race_id",
    "expected_cost",
    "settlement_status",
    "outcome",
    "actual_cost",
    "actual_return",
    "actual_profit",
    "settled_ts",
    "notes",
]
OPEN_TOKENS = {"", "open", "pending", "unsettled", "todo"}
VALID_OUTCOMES = {"HIT", "MISS"}
SETTLED_STATUS_TOKENS = {"settled", "closed", "complete", "completed", "done"}
SETTLED_TS_PLACEHOLDER_TOKENS = {"", "open", "pending", "unsettled", "todo", "tbd", "na", "n/a", "none", "null"}
SETTLE_COMMAND_TEMPLATE_NOTE = (
    "template only; replace placeholders only after actual result/payout evidence exists. "
    "Add --actual-cost ACTUAL_COST_DOLLARS if actual cost differs from expected_cost or expected_cost is missing/malformed."
)
SETTLEMENT_HELPER_EVIDENCE_BOUNDARY = {
    "artifact_role": "paper-trade settlement-helper output",
    "valid_evidence_scope": "settlement_entry_queue_repair_metadata_only",
    "valid_use": "operator settlement-entry workflow, open-queue visibility, and ROI-coverage repair guidance",
    "not_new_forward_evidence": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence_by_itself": True,
    "not_promotion_readiness_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "roi_complete_rows_require_audit_or_forward_check_after_complete_actual_result_return_cost_and_settled_ts": True,
}
SETTLEMENT_HELPER_VALID_EVIDENCE_SCOPE = SETTLEMENT_HELPER_EVIDENCE_BOUNDARY["valid_evidence_scope"]
SETTLEMENT_HELPER_BOUNDARY_TEXT = (
    "settlement-helper output is settlement-entry and queue metadata only; it is not new forward evidence, "
    "not a current-day scanner result, not settled ROI evidence by itself, not promotion readiness, "
    "not live-profitability evidence, and not real-money support. ROI-complete sample counts require "
    "a later audit or forward check after actual result, return, cost, and settled_ts are complete."
)


def finite_nonnegative_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a finite non-negative dollar amount") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise argparse.ArgumentTypeError("must be a finite non-negative dollar amount")
    return parsed


def finite_positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a finite positive dollar amount") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive dollar amount")
    return parsed


def settled_timestamp(value: str) -> str:
    text = str(value or "").strip()
    normalized = text.lower()
    if normalized in SETTLED_TS_PLACEHOLDER_TOKENS or (text.startswith("<") and text.endswith(">")):
        raise argparse.ArgumentTypeError("must be an actual ISO settlement timestamp, not blank or a placeholder")
    if "T" not in text and " " not in text:
        raise argparse.ArgumentTypeError("must be an actual ISO settlement timestamp, not blank or a placeholder")
    parse_text = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        datetime.fromisoformat(parse_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an actual ISO settlement timestamp, not blank or a placeholder") from exc
    return text


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="List or update paper-trade settlement rows")
    sub = p.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list-open", help="Show still-open settlement rows")
    list_p.add_argument("--settlement-ledger", default=str(DEFAULT_SETTLEMENT_LEDGER), help="Settlement ledger CSV path")
    list_p.add_argument("--limit", type=int, default=20, help="Maximum open rows to show in text / markdown output")
    list_p.add_argument("--format", choices=["text", "md", "json"], default="text", help="Output format")
    list_p.add_argument("--output", help="Optional output file path")

    settle_p = sub.add_parser("settle", help="Mark one settlement row as settled")
    settle_p.add_argument("--settlement-ledger", default=str(DEFAULT_SETTLEMENT_LEDGER), help="Settlement ledger CSV path")
    settle_p.add_argument("--signal-key", required=True, help="signal_key to update")
    settle_p.add_argument(
        "--outcome",
        required=True,
        help="Outcome, must be HIT or MISS after the actual race result is known; placeholder values such as <HIT_OR_MISS> are rejected.",
    )
    settle_p.add_argument(
        "--actual-return",
        required=True,
        type=finite_nonnegative_float,
        help="Actual dollars returned; must be finite and non-negative",
    )
    settle_p.add_argument(
        "--actual-cost",
        type=finite_positive_float,
        help=(
            "Actual dollars wagered; must be finite and positive. Omit to infer from the row's expected_cost when parseable. "
            "The confirmation reports actual_cost_source; missing, malformed, zero, or negative expected_cost keeps cost/profit blank."
        ),
    )
    settle_p.add_argument(
        "--settled-ts",
        type=settled_timestamp,
        help=(
            "Actual settlement timestamp in ISO format; blank or placeholder values such as <SETTLED_TS> are rejected when supplied. "
            "Omitting this timestamp leaves the row out of ROI-complete sample gates until settled_ts is filled."
        ),
    )
    settle_p.add_argument("--notes", default="", help="Optional notes")
    settle_p.add_argument("--output-format", choices=["text", "json"], default="text", help="Confirmation output format")
    settle_p.add_argument("--output", help="Optional output file path")
    return p


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})


def normalize_token(value: str | None) -> str:
    return str(value or "").strip().lower()


def parse_float(value: str | None) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if not math.isfinite(parsed) or parsed < 0:
        return None
    return parsed


def parse_positive_float(value: str | None) -> float | None:
    parsed = parse_float(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def normalize_outcome(value: str | None) -> str:
    outcome = str(value or "").strip().upper()
    if outcome not in VALID_OUTCOMES:
        shown = str(value or "").strip() or "<blank>"
        raise SystemExit(f"invalid outcome {shown!r}; use HIT or MISS after the actual race result is known")
    return outcome


def is_open_row(row: dict[str, str]) -> bool:
    return normalize_token(row.get("settlement_status")) in OPEN_TOKENS


def settled_ts_gap_reason(value: str | None) -> str:
    text = str(value or "").strip()
    normalized = text.lower()
    if not text:
        return "missing settled_ts"
    if normalized in SETTLED_TS_PLACEHOLDER_TOKENS or (text.startswith("<") and text.endswith(">")):
        return "placeholder settled_ts"
    if "T" not in text and " " not in text:
        return "malformed settled_ts"
    parse_text = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        datetime.fromisoformat(parse_text)
    except ValueError:
        return "malformed settled_ts"
    return ""


def settlement_roi_gap_reason(row: dict[str, str]) -> str:
    """Explain why a settled HIT/MISS row still cannot count toward ROI gates."""
    if normalize_token(row.get("settlement_status")) not in SETTLED_STATUS_TOKENS:
        return ""
    if str(row.get("outcome", "")).strip().upper() not in VALID_OUTCOMES:
        return ""

    actual_return = parse_float(row.get("actual_return"))
    actual_cost_text = row.get("actual_cost")
    actual_cost = parse_float(actual_cost_text)
    expected_cost = parse_float(row.get("expected_cost"))
    actual_cost_is_malformed = bool(str(actual_cost_text or "").strip()) and actual_cost is None

    reasons: list[str] = []
    if actual_return is None:
        reasons.append("missing actual_return")
    if actual_cost_is_malformed:
        reasons.append("malformed actual_cost")
    elif actual_cost is not None and actual_cost <= 0:
        reasons.append("non-positive actual_cost")
    elif actual_cost is None and expected_cost is None:
        reasons.append("missing actual_cost and expected_cost")
    elif actual_cost is None and expected_cost <= 0:
        reasons.append("non-positive expected_cost")

    timestamp_reason = settled_ts_gap_reason(row.get("settled_ts"))
    if timestamp_reason:
        reasons.append(timestamp_reason)
    return "; ".join(reasons)


def roi_gap_rows_payload(rows: list[dict[str, str]], limit: int) -> dict[str, Any]:
    gap_rows = [(row, settlement_roi_gap_reason(row)) for row in rows]
    gap_rows = [(row, reason) for row, reason in gap_rows if reason]
    shown = gap_rows[: max(limit, 0)]
    payload_rows = []
    for row, reason in shown:
        payload_rows.append(
            {
                "signal_key": row.get("signal_key", ""),
                "rule_id": row.get("rule_id", ""),
                "track": row.get("track", ""),
                "race_number": row.get("race_number", ""),
                "race_id": row.get("race_id", ""),
                "expected_cost": row.get("expected_cost", ""),
                "actual_return": row.get("actual_return", ""),
                "actual_cost": row.get("actual_cost", ""),
                "settled_ts": row.get("settled_ts", ""),
                "roi_gap_reason": reason,
                "scan_ts": row.get("scan_ts", ""),
            }
        )
    return {
        "count": len(gap_rows),
        "shown_count": len(payload_rows),
        "rows": payload_rows,
    }


def fmt_money(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"


def settle_command_template(signal_key: str) -> str:
    return (
        "python3 paper_trade_settlement_helper.py settle "
        f"--signal-key {shlex.quote(signal_key)} "
        "--outcome HIT_OR_MISS "
        "--actual-return ACTUAL_RETURN_DOLLARS "
        "--settled-ts ISO_SETTLED_TS"
    )


def open_rows_payload(rows: list[dict[str, str]], limit: int) -> dict[str, Any]:
    open_rows = [row for row in rows if is_open_row(row)]
    shown = open_rows[: max(limit, 0)]
    payload_rows = []
    for row in shown:
        payload_rows.append(
            {
                "signal_key": row.get("signal_key", ""),
                "rule_id": row.get("rule_id", ""),
                "track": row.get("track", ""),
                "race_number": row.get("race_number", ""),
                "race_id": row.get("race_id", ""),
                "expected_cost": row.get("expected_cost", ""),
                "scan_ts": row.get("scan_ts", ""),
                "settle_command_template": settle_command_template(row.get("signal_key", "")),
                "settle_command_template_note": SETTLE_COMMAND_TEMPLATE_NOTE,
            }
        )
    gap_payload = roi_gap_rows_payload(rows, limit)
    return {
        "open_count": len(open_rows),
        "shown_count": len(payload_rows),
        "limit": limit,
        "rows": payload_rows,
        "roi_gap_count": gap_payload["count"],
        "roi_gap_shown_count": gap_payload["shown_count"],
        "roi_gap_rows": gap_payload["rows"],
        "valid_evidence_scope": SETTLEMENT_HELPER_VALID_EVIDENCE_SCOPE,
        "evidence_boundary": SETTLEMENT_HELPER_EVIDENCE_BOUNDARY,
        "evidence_boundary_text": SETTLEMENT_HELPER_BOUNDARY_TEXT,
    }


def render_open_rows(rows: list[dict[str, str]], limit: int, fmt: str) -> str:
    payload = open_rows_payload(rows, limit)
    if fmt == "json":
        return json.dumps(payload, indent=2)

    open_count = payload["open_count"]
    shown = payload["rows"]
    roi_gap_count = payload["roi_gap_count"]
    roi_gap_rows = payload["roi_gap_rows"]
    if not shown:
        if fmt == "md":
            lines = ["# Open Settlement Queue", "", "- Open settlement rows: `0`", f"- Settled rows missing ROI-complete coverage: `{roi_gap_count}`"]
            if roi_gap_rows:
                lines.extend([
                    "",
                    "## Settled Rows Missing ROI-Complete Coverage",
                    "",
                    "| Signal Key | Rule | Track | Race # | Race ID | Expected Cost | Actual Return | Actual Cost | Settled TS | Gap Reason |",
                    "|---|---|---|---:|---|---:|---:|---:|---|---|",
                ])
                for row in roi_gap_rows:
                    lines.append(
                        f"| {row['signal_key']} | {row['rule_id']} | {row['track']} | {row['race_number']} | {row['race_id']} | {row['expected_cost']} | {row['actual_return']} | {row['actual_cost']} | {row['settled_ts']} | {row['roi_gap_reason']} |"
                    )
            lines.extend([
                "",
                "## Evidence Boundary",
                "",
                f"- valid_evidence_scope={payload['valid_evidence_scope']}",
                f"- Boundary: {payload['evidence_boundary_text']}",
            ])
            return "\n".join(lines) + "\n"
        lines = ["Open settlement rows: 0", f"Settled rows missing ROI-complete coverage: {roi_gap_count}"]
        if roi_gap_rows:
            lines.append("ROI-complete coverage gaps:")
            for row in roi_gap_rows:
                lines.append(
                    f"- {row['signal_key']} | {row['rule_id']} | {row['track']} R{row['race_number']} | return {row['actual_return'] or 'blank'} | cost {row['actual_cost'] or 'blank'} | settled_ts {row['settled_ts'] or 'blank'} | {row['roi_gap_reason']}"
                )
        lines.append(f"valid_evidence_scope={payload['valid_evidence_scope']}")
        lines.append(f"Evidence boundary: {payload['evidence_boundary_text']}")
        return "\n".join(lines)

    headers = ["signal_key", "rule_id", "track", "race_number", "race_id", "expected_cost", "scan_ts"]
    command_note = "Settlement command templates are templates only; " + SETTLE_COMMAND_TEMPLATE_NOTE.partition("; ")[2]
    if fmt == "md":
        lines = ["# Open Settlement Queue", "", f"- Open settlement rows: `{open_count}`", f"- Settled rows missing ROI-complete coverage: `{roi_gap_count}`"]
        if open_count > len(shown):
            lines.append(f"- Showing first `{len(shown)}` row(s)")
        lines.extend(["", "| Signal Key | Rule | Track | Race # | Race ID | Expected Cost | Scan TS |", "|---|---|---|---:|---|---:|---|"])
        for row in shown:
            lines.append(
                f"| {row['signal_key']} | {row['rule_id']} | {row['track']} | {row['race_number']} | {row['race_id']} | {row['expected_cost']} | {row['scan_ts']} |"
            )
        lines.extend(["", "## Settlement Command Templates", "", f"- {command_note}"])
        for row in shown:
            lines.append(f"- `{row['signal_key']}`: `{row['settle_command_template']}`")
        if roi_gap_rows:
            lines.extend([
                "",
                "## Settled Rows Missing ROI-Complete Coverage",
                "",
                "| Signal Key | Rule | Track | Race # | Race ID | Expected Cost | Actual Return | Actual Cost | Settled TS | Gap Reason |",
                "|---|---|---|---:|---|---:|---:|---:|---|---|",
            ])
            for row in roi_gap_rows:
                lines.append(
                    f"| {row['signal_key']} | {row['rule_id']} | {row['track']} | {row['race_number']} | {row['race_id']} | {row['expected_cost']} | {row['actual_return']} | {row['actual_cost']} | {row['settled_ts']} | {row['roi_gap_reason']} |"
                )
        lines.extend([
            "",
            "## Evidence Boundary",
            "",
            f"- valid_evidence_scope={payload['valid_evidence_scope']}",
            f"- Boundary: {payload['evidence_boundary_text']}",
        ])
        return "\n".join(lines) + "\n"

    widths = {h: len(h) for h in headers}
    for row in shown:
        for h in headers:
            widths[h] = max(widths[h], len(str(row.get(h, ""))))
    header_line = "  ".join(h.ljust(widths[h]) for h in headers)
    separator = "  ".join("-" * widths[h] for h in headers)
    body = ["  ".join(str(row.get(h, "")).ljust(widths[h]) for h in headers) for row in shown]
    lines = [f"Open settlement rows: {open_count}", f"Settled rows missing ROI-complete coverage: {roi_gap_count}"]
    if open_count > len(shown):
        lines.append(f"Showing first {len(shown)} row(s)")
    lines.extend([header_line, separator, *body])
    lines.append("Settlement command templates:")
    lines.append(command_note)
    for row in shown:
        lines.append(f"- {row['signal_key']}: {row['settle_command_template']}")
    if roi_gap_rows:
        lines.append("ROI-complete coverage gaps:")
        for row in roi_gap_rows:
            lines.append(
                f"- {row['signal_key']} | {row['rule_id']} | {row['track']} R{row['race_number']} | return {row['actual_return'] or 'blank'} | cost {row['actual_cost'] or 'blank'} | settled_ts {row['settled_ts'] or 'blank'} | {row['roi_gap_reason']}"
            )
    lines.append(f"valid_evidence_scope={payload['valid_evidence_scope']}")
    lines.append(f"Evidence boundary: {payload['evidence_boundary_text']}")
    return "\n".join(lines)


def render_settle_confirmation(row: dict[str, str], fmt: str) -> str:
    has_settled_ts = bool(str(row.get("settled_ts", "")).strip())
    timestamp_note = (
        "settled_ts present; row can count toward ROI-complete samples if return/cost coverage is also usable"
        if has_settled_ts
        else "missing settled_ts; row remains a settlement-quality gap and does not count toward ROI-complete sample gates"
    )
    payload = {
        "signal_key": row.get("signal_key", ""),
        "settlement_status": row.get("settlement_status", ""),
        "outcome": row.get("outcome", ""),
        "actual_cost": row.get("actual_cost", ""),
        "actual_cost_source": row.get("_actual_cost_source", row.get("actual_cost_source", "")),
        "actual_return": row.get("actual_return", ""),
        "actual_profit": row.get("actual_profit", ""),
        "settled_ts": row.get("settled_ts", ""),
        "roi_complete_timestamp_coverage": has_settled_ts,
        "settled_ts_note": timestamp_note,
        "notes": row.get("notes", ""),
        "valid_evidence_scope": SETTLEMENT_HELPER_VALID_EVIDENCE_SCOPE,
        "evidence_boundary": SETTLEMENT_HELPER_EVIDENCE_BOUNDARY,
        "evidence_boundary_text": SETTLEMENT_HELPER_BOUNDARY_TEXT,
    }
    if fmt == "json":
        return json.dumps(payload, indent=2)
    source_note = f", cost_source={payload['actual_cost_source']}" if payload["actual_cost_source"] else ""
    timestamp_note_text = "" if has_settled_ts else f"; {timestamp_note}"
    return (
        f"Updated {payload['signal_key']}: {payload['settlement_status']} {payload['outcome']}, "
        f"return={payload['actual_return'] or 'n/a'}, cost={payload['actual_cost'] or 'n/a'}, "
        f"profit={payload['actual_profit'] or 'n/a'}{source_note}{timestamp_note_text}\n"
        f"valid_evidence_scope={payload['valid_evidence_scope']}\n"
        f"Evidence boundary: {payload['evidence_boundary_text']}"
    )


def handle_list_open(args: argparse.Namespace) -> str:
    rows = load_csv_rows(Path(args.settlement_ledger))
    return render_open_rows(rows, args.limit, args.format)


def handle_settle(args: argparse.Namespace) -> str:
    outcome = normalize_outcome(args.outcome)
    path = Path(args.settlement_ledger)
    rows = load_csv_rows(path)
    if not rows:
        raise SystemExit(f"Settlement ledger not found or empty: {path}")

    matching_rows = [row for row in rows if row.get("signal_key") == args.signal_key]
    if not matching_rows:
        raise SystemExit(f"signal_key not found in settlement ledger: {args.signal_key}")
    if len(matching_rows) > 1:
        raise SystemExit(
            f"duplicate signal_key in settlement ledger: {args.signal_key} appears {len(matching_rows)} times; "
            "repair the settlement ledger or rerun paper_trade_settlement_sync.py before settling this signal"
        )

    updated_row = matching_rows[0]
    actual_cost = args.actual_cost
    actual_cost_source = "actual_cost_argument"
    if actual_cost is None:
        actual_cost = parse_positive_float(updated_row.get("expected_cost"))
        actual_cost_source = "expected_cost_fallback" if actual_cost is not None else "missing_cost_source"
    actual_return = args.actual_return
    actual_profit = (actual_return - actual_cost) if actual_cost is not None else None
    updated_row["_actual_cost_source"] = actual_cost_source
    updated_row["settlement_status"] = "settled"
    updated_row["outcome"] = outcome
    updated_row["actual_return"] = fmt_money(actual_return)
    updated_row["actual_cost"] = fmt_money(actual_cost)
    updated_row["actual_profit"] = fmt_money(actual_profit)
    if args.settled_ts:
        updated_row["settled_ts"] = args.settled_ts
    if args.notes:
        updated_row["notes"] = args.notes

    write_csv_rows(path, rows)
    return render_settle_confirmation(updated_row, args.output_format)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "list-open":
        rendered = handle_list_open(args)
        output_path = getattr(args, "output", None)
    else:
        rendered = handle_settle(args)
        output_path = getattr(args, "output", None)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered + ("" if rendered.endswith("\n") else "\n"), encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
