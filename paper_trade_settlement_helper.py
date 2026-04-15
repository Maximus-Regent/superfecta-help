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
    settle_p.add_argument("--outcome", required=True, help="Outcome, usually HIT or MISS")
    settle_p.add_argument("--actual-return", required=True, type=float, help="Actual dollars returned")
    settle_p.add_argument("--actual-cost", type=float, help="Actual dollars wagered; optional")
    settle_p.add_argument("--settled-ts", help="Settlement timestamp")
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
        writer = csv.DictWriter(f, fieldnames=FIELDS)
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
        return float(text)
    except ValueError:
        return None


def is_open_row(row: dict[str, str]) -> bool:
    return normalize_token(row.get("settlement_status")) in OPEN_TOKENS


def fmt_money(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"


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
            }
        )
    return {
        "open_count": len(open_rows),
        "shown_count": len(payload_rows),
        "limit": limit,
        "rows": payload_rows,
    }


def render_open_rows(rows: list[dict[str, str]], limit: int, fmt: str) -> str:
    payload = open_rows_payload(rows, limit)
    if fmt == "json":
        return json.dumps(payload, indent=2)

    open_count = payload["open_count"]
    shown = payload["rows"]
    if not shown:
        line = f"Open settlement rows: 0"
        return line if fmt == "text" else f"# Open Settlement Queue\n\n- Open settlement rows: `0`\n"

    headers = ["signal_key", "rule_id", "track", "race_number", "race_id", "expected_cost", "scan_ts"]
    if fmt == "md":
        lines = ["# Open Settlement Queue", "", f"- Open settlement rows: `{open_count}`"]
        if open_count > len(shown):
            lines.append(f"- Showing first `{len(shown)}` row(s)")
        lines.extend(["", "| Signal Key | Rule | Track | Race # | Race ID | Expected Cost | Scan TS |", "|---|---|---|---:|---|---:|---|"])
        for row in shown:
            lines.append(
                f"| {row['signal_key']} | {row['rule_id']} | {row['track']} | {row['race_number']} | {row['race_id']} | {row['expected_cost']} | {row['scan_ts']} |"
            )
        return "\n".join(lines) + "\n"

    widths = {h: len(h) for h in headers}
    for row in shown:
        for h in headers:
            widths[h] = max(widths[h], len(str(row.get(h, ""))))
    header_line = "  ".join(h.ljust(widths[h]) for h in headers)
    separator = "  ".join("-" * widths[h] for h in headers)
    body = ["  ".join(str(row.get(h, "")).ljust(widths[h]) for h in headers) for row in shown]
    lines = [f"Open settlement rows: {open_count}"]
    if open_count > len(shown):
        lines.append(f"Showing first {len(shown)} row(s)")
    lines.extend([header_line, separator, *body])
    return "\n".join(lines)


def render_settle_confirmation(row: dict[str, str], fmt: str) -> str:
    payload = {
        "signal_key": row.get("signal_key", ""),
        "settlement_status": row.get("settlement_status", ""),
        "outcome": row.get("outcome", ""),
        "actual_cost": row.get("actual_cost", ""),
        "actual_return": row.get("actual_return", ""),
        "actual_profit": row.get("actual_profit", ""),
        "settled_ts": row.get("settled_ts", ""),
        "notes": row.get("notes", ""),
    }
    if fmt == "json":
        return json.dumps(payload, indent=2)
    return (
        f"Updated {payload['signal_key']}: {payload['settlement_status']} {payload['outcome']}, "
        f"return={payload['actual_return'] or 'n/a'}, cost={payload['actual_cost'] or 'n/a'}, "
        f"profit={payload['actual_profit'] or 'n/a'}"
    )


def handle_list_open(args: argparse.Namespace) -> str:
    rows = load_csv_rows(Path(args.settlement_ledger))
    return render_open_rows(rows, args.limit, args.format)


def handle_settle(args: argparse.Namespace) -> str:
    path = Path(args.settlement_ledger)
    rows = load_csv_rows(path)
    if not rows:
        raise SystemExit(f"Settlement ledger not found or empty: {path}")

    updated_row: dict[str, str] | None = None
    for row in rows:
        if row.get("signal_key") != args.signal_key:
            continue
        actual_cost = args.actual_cost
        actual_return = args.actual_return
        actual_profit = (actual_return - actual_cost) if actual_cost is not None else None
        row["settlement_status"] = "settled"
        row["outcome"] = args.outcome
        row["actual_return"] = fmt_money(actual_return)
        row["actual_cost"] = fmt_money(actual_cost)
        row["actual_profit"] = fmt_money(actual_profit)
        if args.settled_ts:
            row["settled_ts"] = args.settled_ts
        if args.notes:
            row["notes"] = args.notes
        updated_row = row
        break

    if updated_row is None:
        raise SystemExit(f"signal_key not found in settlement ledger: {args.signal_key}")

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
