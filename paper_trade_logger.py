#!/usr/bin/env python3
"""
Append scanner hits and recommendation summaries into persistent paper-trade ledgers.

The original flow logs raw scanner signals.
The recommendation flow additionally logs EV-sized paper-trade plans generated
from paper_trade_recommender.py.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Set

BASE = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE / "out" / "live_scan_latest.json"
DEFAULT_LEDGER = BASE / "paper_trades" / "paper_trade_signals.csv"
DEFAULT_STATE = BASE / "paper_trades" / ".logged_signals.json"
DEFAULT_RECOMMENDATIONS_INPUT = BASE / "out" / "paper_trade_recommendations_latest" / "recommendations_summary.json"
DEFAULT_RECOMMENDATION_LEDGER = BASE / "paper_trades" / "paper_trade_recommendations.csv"
DEFAULT_RECOMMENDATION_STATE = BASE / "paper_trades" / ".logged_recommendations.json"

FIELDS = [
    "signal_key",
    "scan_ts",
    "rule_id",
    "track",
    "card_name",
    "race_number",
    "race_id",
    "surface",
    "condition",
    "field_size",
    "favorite_program",
    "favorite_name",
    "favorite_prob",
    "second_prob",
    "prob_gap",
    "k",
    "base_stake",
    "estimated_cost",
    "underneath_programs",
    "ticket_structure",
    "status",
    "outcome",
    "notes",
]

RECOMMENDATION_FIELDS = [
    "signal_key",
    "run_ts",
    "rule_id",
    "track",
    "card_name",
    "race_number",
    "race_id",
    "decision",
    "reason",
    "favorite_program",
    "underneath_programs",
    "scanner_estimated_cost",
    "scored_combo_count",
    "filtered_combo_count",
    "bankroll",
    "race_risk_budget",
    "total_stake",
    "total_expected_return",
    "total_expected_profit",
    "portfolio_expected_roi_pct",
    "tickets_selected",
    "tickets_json",
    "prediction_csv",
    "plan_json",
    "plan_csv",
    "status",
    "outcome",
    "notes",
]
LOGGER_VALID_EVIDENCE_SCOPE = "paper_trade_logger_append_dedup_metadata_only"
LOGGER_EVIDENCE_BOUNDARY_TEXT = (
    "paper-trade logger output is ledger-append and dedup metadata only; it is not new forward evidence, "
    "not a current-day scanner result by itself, not settled ROI evidence, not promotion readiness, "
    "not live-profitability evidence, and not real-money support. Logged open rows require settlement-sync, "
    "actual result, return, cost, and settled_ts completion plus later audit or forward-check review before "
    "they can count toward ROI-complete sample gates."
)


def parse_args():
    p = argparse.ArgumentParser(description="Log live scanner hits into a paper-trade ledger")
    p.add_argument("--input", default=str(DEFAULT_INPUT), help="Scanner JSON output path")
    p.add_argument("--ledger", default=str(DEFAULT_LEDGER), help="CSV ledger path")
    p.add_argument("--state", default=str(DEFAULT_STATE), help="Dedup state JSON path")
    p.add_argument(
        "--recommendations-input",
        default=str(DEFAULT_RECOMMENDATIONS_INPUT),
        help="Recommendation summary JSON path from paper_trade_recommender.py",
    )
    p.add_argument(
        "--recommendation-ledger",
        default=str(DEFAULT_RECOMMENDATION_LEDGER),
        help="Recommendation CSV ledger path",
    )
    p.add_argument(
        "--recommendation-state",
        default=str(DEFAULT_RECOMMENDATION_STATE),
        help="Recommendation dedup state JSON path",
    )
    return p.parse_args()


def load_hits(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    data = json.loads(text)
    if isinstance(data, list):
        return data
    return []


def load_recommendations(path: Path) -> List[Dict]:
    return load_hits(path)


def signal_key(hit: Dict) -> str:
    return f"{hit.get('scan_ts','')}|{hit.get('rule_id','')}|{hit.get('race_id','')}|{hit.get('favorite_program','')}"


def load_state(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("logged", []))
    except Exception:
        return set()


def load_logged_keys_from_ledger(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return {str(row.get("signal_key", "")).strip() for row in reader if str(row.get("signal_key", "")).strip()}
    except Exception:
        return set()


def save_state(path: Path, logged: Set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"logged": sorted(logged)}, indent=2), encoding="utf-8")


def ensure_ledger(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()


def ensure_recommendation_ledger(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=RECOMMENDATION_FIELDS, lineterminator="\n")
            writer.writeheader()


def append_rows(path: Path, rows: List[Dict]) -> None:
    if not rows:
        return
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        for row in rows:
            writer.writerow(row)


def append_recommendation_rows(path: Path, rows: List[Dict]) -> None:
    if not rows:
        return
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RECOMMENDATION_FIELDS, lineterminator="\n")
        for row in rows:
            writer.writerow(row)


def main():
    args = parse_args()
    input_path = Path(args.input)
    ledger_path = Path(args.ledger)
    state_path = Path(args.state)
    recommendations_input_path = Path(args.recommendations_input)
    recommendation_ledger_path = Path(args.recommendation_ledger)
    recommendation_state_path = Path(args.recommendation_state)

    hits = load_hits(input_path)
    ensure_ledger(ledger_path)
    logged = load_state(state_path) | load_logged_keys_from_ledger(ledger_path)

    new_rows = []
    for hit in hits:
        key = signal_key(hit)
        if key in logged:
            continue
        logged.add(key)
        new_rows.append({
            "signal_key": key,
            "scan_ts": hit.get("scan_ts", ""),
            "rule_id": hit.get("rule_id", ""),
            "track": hit.get("track", ""),
            "card_name": hit.get("card_name", ""),
            "race_number": hit.get("race_number", ""),
            "race_id": hit.get("race_id", ""),
            "surface": hit.get("surface", ""),
            "condition": hit.get("condition", ""),
            "field_size": hit.get("field_size", ""),
            "favorite_program": hit.get("favorite_program", ""),
            "favorite_name": hit.get("favorite_name", ""),
            "favorite_prob": hit.get("favorite_prob", ""),
            "second_prob": hit.get("second_prob", ""),
            "prob_gap": hit.get("prob_gap", ""),
            "k": hit.get("k", ""),
            "base_stake": hit.get("base_stake", ""),
            "estimated_cost": hit.get("estimated_cost", ""),
            "underneath_programs": json.dumps(hit.get("underneath_programs", [])),
            "ticket_structure": hit.get("ticket_structure", ""),
            "status": "open",
            "outcome": "",
            "notes": "",
        })

    append_rows(ledger_path, new_rows)
    save_state(state_path, logged)

    recommendations = load_recommendations(recommendations_input_path)
    ensure_recommendation_ledger(recommendation_ledger_path)
    logged_recommendations = load_state(recommendation_state_path) | load_logged_keys_from_ledger(recommendation_ledger_path)

    new_recommendation_rows = []
    for rec in recommendations:
        key = rec.get("signal_key", "")
        if not key or key in logged_recommendations:
            continue
        logged_recommendations.add(key)
        new_recommendation_rows.append({
            "signal_key": key,
            "run_ts": rec.get("run_ts", ""),
            "rule_id": rec.get("rule_id", ""),
            "track": rec.get("track", ""),
            "card_name": rec.get("card_name", ""),
            "race_number": rec.get("race_number", ""),
            "race_id": rec.get("race_id", ""),
            "decision": rec.get("decision", ""),
            "reason": rec.get("reason", ""),
            "favorite_program": rec.get("favorite_program", ""),
            "underneath_programs": json.dumps(rec.get("underneath_programs", [])),
            "scanner_estimated_cost": rec.get("scanner_estimated_cost", ""),
            "scored_combo_count": rec.get("scored_combo_count", ""),
            "filtered_combo_count": rec.get("filtered_combo_count", ""),
            "bankroll": rec.get("bankroll", ""),
            "race_risk_budget": rec.get("race_risk_budget", ""),
            "total_stake": rec.get("total_stake", ""),
            "total_expected_return": rec.get("total_expected_return", ""),
            "total_expected_profit": rec.get("total_expected_profit", ""),
            "portfolio_expected_roi_pct": rec.get("portfolio_expected_roi_pct", ""),
            "tickets_selected": rec.get("tickets_selected", ""),
            "tickets_json": json.dumps(rec.get("tickets", [])),
            "prediction_csv": rec.get("prediction_csv", ""),
            "plan_json": rec.get("plan_json", ""),
            "plan_csv": rec.get("plan_csv", ""),
            "status": "open",
            "outcome": "",
            "notes": "",
        })

    append_recommendation_rows(recommendation_ledger_path, new_recommendation_rows)
    save_state(recommendation_state_path, logged_recommendations)

    print(f"Logged {len(new_rows)} new paper-trade signal(s) to {ledger_path}")
    print(
        f"Logged {len(new_recommendation_rows)} new recommendation row(s) "
        f"to {recommendation_ledger_path}"
    )
    print(f"valid_evidence_scope={LOGGER_VALID_EVIDENCE_SCOPE}")
    print(f"Evidence boundary: {LOGGER_EVIDENCE_BOUNDARY_TEXT}")


if __name__ == "__main__":
    main()
