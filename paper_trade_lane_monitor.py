#!/usr/bin/env python3
"""
Compact lane monitor for paper-trade forward observation.

Purpose:
- combine the latest forward-check read with the current settlement queue
- give one small artifact per lane that is easy to review after a daily run
- keep the summary anchored to the frozen evaluation standard
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from paper_trade_forward_check import (
    DEFAULT_FROZEN_EVAL,
    DEFAULT_RECOMMENDATION_LEDGER,
    DEFAULT_RULES,
    DEFAULT_SIGNALS_LEDGER,
    build_payload,
    default_settlement_ledger_path,
    load_csv_rows,
    pct,
    signed_pct,
)

BASE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = BASE / "out" / "paper_trade_lane_monitor.md"
OPEN_TOKENS = {"", "open", "pending", "unsettled", "todo"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Show a compact lane monitor with forward status plus open settlement queue")
    p.add_argument("--signals-ledger", default=str(DEFAULT_SIGNALS_LEDGER), help="Signal ledger CSV path")
    p.add_argument("--recommendation-ledger", default=str(DEFAULT_RECOMMENDATION_LEDGER), help="Recommendation ledger CSV path")
    p.add_argument("--settlement-ledger", help="Optional settlement ledger CSV path; defaults from --signals-ledger")
    p.add_argument("--rules", default=str(DEFAULT_RULES), help="Rules JSON path for the lane being checked")
    p.add_argument("--frozen-eval", default=str(DEFAULT_FROZEN_EVAL), help="Frozen evaluation summary CSV path")
    p.add_argument("--min-settled", type=int, default=30, help="Minimum settled races before treating the check as decision-grade")
    p.add_argument("--max-open", type=int, default=5, help="Maximum open settlement rows to show")
    p.add_argument("--format", choices=["text", "md", "json"], default="md", help="Output format")
    p.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Optional output path")
    return p.parse_args()


def is_open_row(row: dict[str, str]) -> bool:
    return str(row.get("settlement_status", "")).strip().lower() in OPEN_TOKENS


def build_monitor_payload(args: argparse.Namespace) -> dict[str, Any]:
    settlement_path = Path(args.settlement_ledger) if args.settlement_ledger else default_settlement_ledger_path(Path(args.signals_ledger))
    forward_args = SimpleNamespace(
        signals_ledger=args.signals_ledger,
        recommendation_ledger=args.recommendation_ledger,
        settlement_ledger=str(settlement_path),
        rules=args.rules,
        frozen_eval=args.frozen_eval,
        min_settled=args.min_settled,
        format="json",
        output=None,
    )
    forward_payload = build_payload(forward_args)
    settlement_rows = load_csv_rows(settlement_path)
    open_rows = [row for row in settlement_rows if is_open_row(row)]
    shown_rows = open_rows[: max(args.max_open, 0)]

    return {
        "lane_label": forward_payload["lane_label"],
        "rules_path": forward_payload["rules_path"],
        "signals_ledger": forward_payload["signals_ledger"],
        "recommendation_ledger": forward_payload["recommendation_ledger"],
        "settlement_ledger": forward_payload["settlement_ledger"],
        "forward": forward_payload,
        "open_settlements": {
            "count": len(open_rows),
            "shown": len(shown_rows),
            "max_open": args.max_open,
            "rows": [
                {
                    "signal_key": row.get("signal_key", ""),
                    "rule_id": row.get("rule_id", ""),
                    "track": row.get("track", ""),
                    "race_number": row.get("race_number", ""),
                    "race_id": row.get("race_id", ""),
                    "expected_cost": row.get("expected_cost", ""),
                    "scan_ts": row.get("scan_ts", ""),
                }
                for row in shown_rows
            ],
        },
    }


def render_text(payload: dict[str, Any]) -> str:
    forward = payload["forward"]
    observed = forward["portfolio_observed"]
    baseline = forward["portfolio_baseline"]
    open_payload = payload["open_settlements"]

    lines = [
        f"{payload['lane_label']} monitor",
        f"- Forward assessment: {forward['portfolio_assessment']}",
        f"- Observed: {observed['settled']} settled, {observed['open']} open, hit rate {pct(observed['hit_rate']) if observed['settled'] else 'n/a'}",
        (
            f"- Observed flat-ticket ROI: {signed_pct(float(observed['actual_roi']))} on {observed['settled_with_roi']} settled race(s)"
            if observed.get("actual_roi") is not None else
            "- Observed flat-ticket ROI: n/a"
        ),
        (
            f"- Frozen baseline: {pct(float(baseline['hit_rate']))} hit rate, {signed_pct(float(baseline['roi']))} ROI on {int(baseline['races'])} holdout races"
            if baseline else
            "- Frozen baseline: missing"
        ),
        f"- Read: {forward['portfolio_note']}",
        f"- Pending settlement rows: {open_payload['count']}",
    ]
    for row in open_payload["rows"]:
        lines.append(
            f"  - {row['signal_key']} | {row['rule_id']} | {row['track']} R{row['race_number']} | cost {row['expected_cost']} | {row['scan_ts']}"
        )
    if open_payload["count"] > open_payload["shown"]:
        lines.append(f"  - ... plus {open_payload['count'] - open_payload['shown']} more open row(s)")
    return "\n".join(lines) + "\n"


def render_md(payload: dict[str, Any]) -> str:
    forward = payload["forward"]
    observed = forward["portfolio_observed"]
    baseline = forward["portfolio_baseline"]
    open_payload = payload["open_settlements"]

    lines = [
        "# Paper-Trade Lane Monitor",
        "",
        f"Lane: **{payload['lane_label']}**",
        "",
        "## Forward Snapshot",
        "",
        f"- Assessment: **{forward['portfolio_assessment']}**",
        f"- Observed signals: `{observed['total']}` total, `{observed['settled']}` settled, `{observed['open']}` still open",
        f"- Observed hit rate: `{pct(observed['hit_rate'])}` ({observed['hits']} hit / {observed['settled']} settled)" if observed["settled"] else "- Observed hit rate: `n/a` (no settled races yet)",
        (
            f"- Observed flat-ticket ROI: `{signed_pct(float(observed['actual_roi']))}` on `{observed['settled_with_roi']}` settled race(s) with return values"
            if observed.get("actual_roi") is not None else
            "- Observed flat-ticket ROI: `n/a`"
        ),
        (
            f"- Frozen baseline: `{pct(float(baseline['hit_rate']))}` hit rate, `{signed_pct(float(baseline['roi']))}` ROI on `{int(baseline['races'])}` holdout races"
            if baseline else
            "- Frozen baseline: `missing`"
        ),
        f"- Read: {forward['portfolio_note']}",
        "",
        "## Settlement Queue",
        "",
        f"- Open settlement rows: `{open_payload['count']}`",
        f"- Settlement ledger: `{payload['settlement_ledger']}`",
    ]

    if open_payload["rows"]:
        lines.extend([
            "",
            "| Signal Key | Rule | Track | Race # | Race ID | Expected Cost | Scan TS |",
            "|---|---|---|---:|---|---:|---|",
        ])
        for row in open_payload["rows"]:
            lines.append(
                f"| {row['signal_key']} | {row['rule_id']} | {row['track']} | {row['race_number']} | {row['race_id']} | {row['expected_cost']} | {row['scan_ts']} |"
            )
        if open_payload["count"] > open_payload["shown"]:
            lines.append("")
            lines.append(f"- Showing first `{open_payload['shown']}` open row(s).")
    else:
        lines.extend(["", "- No pending settlement rows."])

    lines.extend([
        "",
        "## Next Step",
        "",
        (
            "- Run `paper_trade_settlement_helper.py settle ...` for the open rows above, then rerun the forward check or the daily observation wrapper."
            if open_payload["count"] else
            "- No manual settlement entry is pending right now. Keep running the daily observation wrapper until settled races start to accumulate."
        ),
        "",
    ])
    return "\n".join(lines)


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    payload = build_monitor_payload(args)

    if args.format == "json":
        output = json.dumps(payload, indent=2) + "\n"
    elif args.format == "text":
        output = render_text(payload)
    else:
        output = render_md(payload) + "\n"

    if args.output:
        write_output(Path(args.output), output)
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
