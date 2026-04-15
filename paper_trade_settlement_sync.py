#!/usr/bin/env python3
"""
Sync a settlement ledger template from the paper-trade signal ledger.

Purpose:
- Create one settlement row per signal_key.
- Preserve any existing manual settlement data.
- Give the forward checker a stable place to read actual return/cost values.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
DEFAULT_SIGNALS_LEDGER = BASE / "paper_trades" / "phase7_current_paper_paper_trade_signals.csv"
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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sync settlement ledger rows from the paper-trade signal ledger")
    p.add_argument("--signals-ledger", default=str(DEFAULT_SIGNALS_LEDGER), help="Signal ledger CSV path")
    p.add_argument("--settlement-ledger", default=str(DEFAULT_SETTLEMENT_LEDGER), help="Settlement ledger CSV path")
    return p.parse_args()


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


def settlement_template(signal: dict[str, str]) -> dict[str, str]:
    return {
        "signal_key": signal.get("signal_key", ""),
        "scan_ts": signal.get("scan_ts", ""),
        "rule_id": signal.get("rule_id", ""),
        "track": signal.get("track", ""),
        "card_name": signal.get("card_name", ""),
        "race_number": signal.get("race_number", ""),
        "race_id": signal.get("race_id", ""),
        "expected_cost": signal.get("estimated_cost", ""),
        "settlement_status": "open",
        "outcome": "",
        "actual_cost": "",
        "actual_return": "",
        "actual_profit": "",
        "settled_ts": "",
        "notes": "",
    }


def main() -> int:
    args = parse_args()
    signals_path = Path(args.signals_ledger)
    settlement_path = Path(args.settlement_ledger)

    signal_rows = load_csv_rows(signals_path)
    existing_rows = load_csv_rows(settlement_path)
    existing_by_key = {row.get("signal_key", ""): row for row in existing_rows if row.get("signal_key")}

    synced_rows: list[dict[str, str]] = []
    added = 0
    preserved = 0

    for signal in signal_rows:
        key = signal.get("signal_key", "")
        if not key:
            continue
        if key in existing_by_key:
            row = dict(existing_by_key[key])
            row.update({
                "scan_ts": signal.get("scan_ts", row.get("scan_ts", "")),
                "rule_id": signal.get("rule_id", row.get("rule_id", "")),
                "track": signal.get("track", row.get("track", "")),
                "card_name": signal.get("card_name", row.get("card_name", "")),
                "race_number": signal.get("race_number", row.get("race_number", "")),
                "race_id": signal.get("race_id", row.get("race_id", "")),
                "expected_cost": signal.get("estimated_cost", row.get("expected_cost", "")),
            })
            synced_rows.append(row)
            preserved += 1
        else:
            synced_rows.append(settlement_template(signal))
            added += 1

    write_csv_rows(settlement_path, synced_rows)
    print(
        f"Settlement sync complete: {len(synced_rows)} row(s), {added} added, {preserved} preserved. "
        f"Ledger: {settlement_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
