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
SETTLEMENT_SYNC_EVIDENCE_BOUNDARY_TEXT = (
    "settlement-sync output is settlement-template and ledger-alignment metadata only; it is not new forward evidence, "
    "not a current-day scanner result, not settled ROI evidence, not promotion readiness, not live-profitability evidence, "
    "and not real-money support. Created open rows require actual result, return, cost, and settled_ts completion plus "
    "later audit or forward-check review before they can count toward ROI-complete sample gates."
)
SETTLEMENT_SYNC_VALID_EVIDENCE_SCOPE = "settlement_template_ledger_alignment_only"


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
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})


def clean_key(row: dict[str, str]) -> str:
    return str(row.get("signal_key", "")).strip()


def settlement_template(signal: dict[str, str], signal_key: str) -> dict[str, str]:
    return {
        "signal_key": signal_key,
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
    existing_by_key = {clean_key(row): row for row in existing_rows if clean_key(row)}

    synced_rows: list[dict[str, str]] = []
    added = 0
    preserved = 0
    blank_signal_keys_skipped = 0
    duplicate_signal_keys_skipped = 0
    active_signal_keys: set[str] = set()

    for signal in signal_rows:
        key = clean_key(signal)
        if not key:
            blank_signal_keys_skipped += 1
            continue
        if key in active_signal_keys:
            duplicate_signal_keys_skipped += 1
            continue
        active_signal_keys.add(key)
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
            synced_rows.append(settlement_template(signal, key))
            added += 1

    orphan_settlement_rows_dropped = sum(
        1 for row in existing_rows if clean_key(row) and clean_key(row) not in active_signal_keys
    )
    blank_settlement_keys_dropped = sum(1 for row in existing_rows if not clean_key(row))

    write_csv_rows(settlement_path, synced_rows)
    print(
        f"Settlement sync complete: {len(synced_rows)} row(s), {added} added, {preserved} preserved. "
        f"Ledger: {settlement_path}"
    )
    print(
        f"Cleanup: {blank_signal_keys_skipped} blank signal-key row(s) skipped; "
        f"{blank_settlement_keys_dropped} blank settlement-key row(s) dropped; "
        f"{orphan_settlement_rows_dropped} orphan settlement row(s) dropped."
    )
    print(f"Dedup: {duplicate_signal_keys_skipped} duplicate signal-key row(s) skipped.")
    print(f"valid_evidence_scope={SETTLEMENT_SYNC_VALID_EVIDENCE_SCOPE}")
    print(f"Evidence boundary: {SETTLEMENT_SYNC_EVIDENCE_BOUNDARY_TEXT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
