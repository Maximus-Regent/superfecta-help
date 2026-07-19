#!/usr/bin/env python3
"""
Operational wrapper for the superfecta paper-trade pipeline.

One command to answer: what should I do right now?

Modes:
  (default)   Auto — runs preflight + status together
  preflight   Are there live races today for the primary paper-basket tracks?
  status      Pipeline state, open settlements, forward-check summary
  post-race   What needs settling after today's races?
  next        Print only the exact next command to run

Reuses the existing NYRA API helpers and pipeline artifacts — no new modeling.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import traceback
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "NYRA"))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PHASE7_RULES = BASE / "phase7_current_paper_rules.json"
PHASE8_RULES = BASE / "phase8_shadow_rules.json"
DAILY_RUNNER = BASE / "run_daily_portfolio_observation.sh"
PIPELINE_STATUS = BASE / "out" / "paper_trade_pipeline_status.json"
SCAN_STATUS = BASE / "out" / "live_scan_latest.status.json"

SIGNAL_LEDGERS = {
    "phase7_current_paper": BASE / "paper_trades" / "phase7_current_paper_paper_trade_signals.csv",
    "phase8_shadow": BASE / "paper_trades" / "phase8_shadow_paper_trade_signals.csv",
}
SETTLEMENT_LEDGERS = {
    "phase7_current_paper": BASE / "paper_trades" / "phase7_current_paper_paper_trade_settlements.csv",
    "phase8_shadow": BASE / "paper_trades" / "phase8_shadow_paper_trade_settlements.csv",
}
RECOMMENDATION_LEDGERS = {
    "phase7_current_paper": BASE / "paper_trades" / "phase7_current_paper_paper_trade_recommendations.csv",
    "phase8_shadow": BASE / "paper_trades" / "phase8_shadow_paper_trade_recommendations.csv",
}

ACTIVE_TRACKS = {"OP": "Oaklawn Park", "CD": "Churchill Downs"}
SHADOW_TRACKS = {
    "KEE": "Keeneland",
    "SA": "Santa Anita",
    "AQU": "Aqueduct",
    "BEL": "Belmont Park",
    "DMR": "Del Mar",
}
OPEN_TOKENS = {"", "open", "pending", "unsettled", "todo"}
BELMONT_BAQ_ALIAS_MARKERS = ("big a", "@ the big a", "aqueduct", "baq")


def _normalized_card_name(card_name: object) -> str:
    return " ".join(str(card_name or "").strip().lower().split())


def _is_belmont_at_big_a(card_name: object) -> bool:
    name = _normalized_card_name(card_name)
    if not name:
        return False
    if name == "baq" or name.startswith("baq "):
        return True
    return "belmont" in name and any(marker in name for marker in BELMONT_BAQ_ALIAS_MARKERS)


def _card_matches_track(card_name: object, track_code: str, track_name: str) -> bool:
    """Return True only for supported track-name matches.

    The BEL branch is intentionally stricter than a plain substring check:
    `Belmont at the Big A` is BAQ/Big A, not Belmont Park, and must not
    wake the dormant BEL rule or shadow lane.
    """
    name = _normalized_card_name(card_name)
    if not name:
        return False
    if track_code == "BEL":
        if _is_belmont_at_big_a(name):
            return False
        return name == "belmont" or "belmont park" in name
    return track_name.lower() in name


def _excluded_track_for_card(card_name: object) -> tuple[str, str] | None:
    if _is_belmont_at_big_a(card_name):
        return ("BAQ", "Belmont/BAQ Big A or Aqueduct card; do not alias it to BEL")
    return None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_et() -> str:
    """Current time string (local)."""
    return datetime.now().strftime("%Y-%m-%d %H:%M %Z").strip()


def _today() -> str:
    return date.today().isoformat()


def _load_json(path: Path) -> Any:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _count_open_settlements(path: Path) -> int:
    rows = _load_csv_rows(path)
    return sum(
        1 for r in rows
        if r.get("settlement_status", "").strip().lower() in OPEN_TOKENS
        and r.get("outcome", "").strip() == ""
    )


def _count_settled(path: Path) -> int:
    rows = _load_csv_rows(path)
    return sum(
        1 for r in rows
        if r.get("settlement_status", "").strip().lower() not in OPEN_TOKENS
        and r.get("outcome", "").strip() != ""
    )


def _signal_count(path: Path) -> int:
    rows = _load_csv_rows(path)
    return len(rows)


def _last_pipeline_run() -> dict[str, Any] | None:
    return _load_json(PIPELINE_STATUS)


def _last_scan_status() -> dict[str, Any] | None:
    return _load_json(SCAN_STATUS)


# ---------------------------------------------------------------------------
# Preflight: check today's cards via NYRA API
# ---------------------------------------------------------------------------

def check_todays_cards() -> dict[str, Any]:
    """Hit the NYRA ListCards API and see if any primary paper-basket tracks are racing."""
    result: dict[str, Any] = {
        "date": _today(),
        "checked_at": _now_et(),
        "api_ok": False,
        "total_cards": 0,
        "relevant_cards": [],
        "relevant_tracks": [],
        "has_targets": False,
        "error": None,
    }

    try:
        from list_cards import list_cards
        cards = list_cards()
        result["api_ok"] = True
        result["total_cards"] = len(cards) if cards else 0

        if not cards:
            return result

        for card in cards:
            card_name = card.get("cardName", "")
            card_date = card.get("cardDate", "")
            # Match against primary paper-basket target tracks.
            for track_code, track_name in ACTIVE_TRACKS.items():
                if _card_matches_track(card_name, track_code, track_name):
                    result["relevant_cards"].append({
                        "track": track_code,
                        "card_name": card_name,
                        "card_date": card_date,
                        "card_id": card.get("cardId", ""),
                        "num_runners": card.get("numberOfRunners", 0),
                    })
                    if track_code not in result["relevant_tracks"]:
                        result["relevant_tracks"].append(track_code)

        result["has_targets"] = len(result["relevant_cards"]) > 0

    except Exception as e:
        result["error"] = str(e)

    return result


def check_todays_cards_extended() -> dict[str, Any]:
    """Also check shadow-basket tracks (KEE, SA, AQU, etc.)."""
    result = check_todays_cards()
    if not result["api_ok"] or result.get("error"):
        return result

    result["shadow_cards"] = []
    result["shadow_tracks"] = []
    result["excluded_cards"] = []
    result["excluded_tracks"] = []

    try:
        from list_cards import list_cards
        cards = list_cards()
        for card in (cards or []):
            card_name = card.get("cardName", "")
            excluded = _excluded_track_for_card(card_name)
            if excluded:
                track_code, reason = excluded
                result["excluded_cards"].append({
                    "track": track_code,
                    "card_name": card_name,
                    "card_id": card.get("cardId", ""),
                    "reason": reason,
                })
                if track_code not in result["excluded_tracks"]:
                    result["excluded_tracks"].append(track_code)

            for track_code, track_name in SHADOW_TRACKS.items():
                if _card_matches_track(card_name, track_code, track_name):
                    result["shadow_cards"].append({
                        "track": track_code,
                        "card_name": card_name,
                        "card_id": card.get("cardId", ""),
                    })
                    if track_code not in result["shadow_tracks"]:
                        result["shadow_tracks"].append(track_code)
    except Exception:
        pass  # shadow info is best-effort

    return result


# ---------------------------------------------------------------------------
# Status: ledger + pipeline state
# ---------------------------------------------------------------------------

def gather_status() -> dict[str, Any]:
    """Gather current operational state from all ledgers and status files."""
    status: dict[str, Any] = {"date": _today(), "checked_at": _now_et(), "lanes": {}}

    for lane_name, sig_path in SIGNAL_LEDGERS.items():
        settle_path = SETTLEMENT_LEDGERS[lane_name]
        reco_path = RECOMMENDATION_LEDGERS[lane_name]
        status["lanes"][lane_name] = {
            "total_signals": _signal_count(sig_path),
            "total_recommendations": _signal_count(reco_path),
            "open_settlements": _count_open_settlements(settle_path),
            "settled_count": _count_settled(settle_path),
        }

    # Last pipeline run
    pipe = _last_pipeline_run()
    if pipe:
        status["last_pipeline"] = {
            "run_ts": pipe.get("run_ts", "unknown"),
            "result": pipe.get("result", "unknown"),
            "observation_result": pipe.get("observation_result", "unknown"),
            "scan_hits": pipe.get("scan_hit_count", 0),
        }
    else:
        status["last_pipeline"] = None

    # Latest daily run folder
    daily_root = BASE / "out" / "daily_portfolio_runs"
    if daily_root.exists():
        folders = sorted(daily_root.iterdir(), reverse=True)
        status["latest_daily_run"] = str(folders[0].name) if folders else None
    else:
        status["latest_daily_run"] = None

    return status


# ---------------------------------------------------------------------------
# Post-race: open settlement detail
# ---------------------------------------------------------------------------

def gather_open_settlements() -> dict[str, list[dict[str, str]]]:
    """List all open settlement rows per lane."""
    result: dict[str, list[dict[str, str]]] = {}
    for lane_name, settle_path in SETTLEMENT_LEDGERS.items():
        rows = _load_csv_rows(settle_path)
        open_rows = [
            {k: r.get(k, "") for k in ("signal_key", "rule_id", "track", "card_name", "race_number", "race_id", "expected_cost")}
            for r in rows
            if r.get("settlement_status", "").strip().lower() in OPEN_TOKENS
            and r.get("outcome", "").strip() == ""
        ]
        result[lane_name] = open_rows
    return result


# ---------------------------------------------------------------------------
# Decision: what command to run next
# ---------------------------------------------------------------------------

def decide_next_action(preflight: dict[str, Any], status: dict[str, Any]) -> dict[str, Any]:
    """Given preflight + status, return the recommended next action."""
    cd_cmd = f'cd "{BASE}"'

    # Check for open settlements first
    total_open = sum(lane.get("open_settlements", 0) for lane in status.get("lanes", {}).values())
    total_settled = sum(lane.get("settled_count", 0) for lane in status.get("lanes", {}).values())

    if total_open > 0:
        return {
            "priority": "SETTLE",
            "reason": f"{total_open} open settlement(s) need outcomes filled",
            "command": f'{cd_cmd} && python3 paper_trade_settlement_helper.py list-open',
            "detail": "Fill in outcome (HIT/MISS) and actual_return for each open row, then rerun forward check.",
        }

    if preflight.get("has_targets"):
        tracks = ", ".join(preflight.get("relevant_tracks", []))
        return {
            "priority": "RUN LIVE",
            "reason": f"Primary paper-basket target tracks racing today: {tracks}",
            "command": f'{cd_cmd} && bash run_daily_portfolio_observation.sh',
            "detail": "Run close to post time for best odds. Do NOT pass --cache-only.",
        }

    if total_settled < 30:
        return {
            "priority": "WAIT",
            "reason": f"No primary paper-basket target tracks today. {total_settled}/30 settled for decision-grade forward check.",
            "command": None,
            "detail": "Check again on the next OP or CD race day. Churchill Downs spring meet opens late April.",
        }

    return {
        "priority": "FORWARD CHECK",
        "reason": f"{total_settled} settled observations — enough for forward check assessment.",
        "command": f'{cd_cmd} && python3 paper_trade_forward_check.py',
        "detail": "Review the forward check to see if the live lane is within expected noise.",
    }


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def _hr() -> str:
    return "-" * 60


def print_preflight(pf: dict[str, Any]) -> None:
    print(f"\n{'=' * 60}")
    print(f"  PREFLIGHT — {pf['date']}")
    print(f"{'=' * 60}")

    if pf.get("error"):
        print(f"  API error: {pf['error']}")
        return

    if not pf["api_ok"]:
        print("  Could not reach NYRA API.")
        return

    print(f"  Cards on NYRA today: {pf['total_cards']}")

    if pf["has_targets"]:
        print(f"  PRIMARY PAPER-BASKET TARGET TRACKS RACING: {', '.join(pf['relevant_tracks'])}")
        for card in pf["relevant_cards"]:
            print(f"    {card['track']} — {card['card_name']} ({card.get('num_runners', '?')} runners)")
    else:
        print("  No primary paper-basket target tracks (OP / CD) racing today.")

    shadow_tracks = pf.get("shadow_tracks", [])
    if shadow_tracks:
        print(f"  Shadow-basket tracks present: {', '.join(shadow_tracks)}")
        for card in pf.get("shadow_cards", []):
            print(f"    {card['track']} — {card['card_name']}")

    excluded_tracks = pf.get("excluded_tracks", [])
    if excluded_tracks:
        print(f"  Excluded track aliases present: {', '.join(excluded_tracks)} (not treated as BEL)")
        for card in pf.get("excluded_cards", []):
            print(f"    {card['track']} — {card['card_name']} | {card.get('reason', '')}")


def print_status(st: dict[str, Any]) -> None:
    print(f"\n{'=' * 60}")
    print(f"  STATUS — {st['date']}")
    print(f"{'=' * 60}")

    for lane_name, lane in st.get("lanes", {}).items():
        label = "PRIMARY" if "phase7" in lane_name else "SHADOW"
        print(f"\n  [{label}] {lane_name}")
        print(f"    Signals logged:    {lane['total_signals']}")
        print(f"    Recommendations:   {lane['total_recommendations']}")
        print(f"    Open settlements:  {lane['open_settlements']}")
        print(f"    Settled races:     {lane['settled_count']}")

    pipe = st.get("last_pipeline")
    if pipe:
        print(f"\n  Last pipeline run: {pipe['run_ts']}")
        print(f"    Result: {pipe['result']}  |  Observation: {pipe['observation_result']}  |  Scan hits: {pipe['scan_hits']}")
    else:
        print("\n  No pipeline status file found.")

    if st.get("latest_daily_run"):
        print(f"  Latest daily run folder: {st['latest_daily_run']}")


def print_open_settlements(open_map: dict[str, list[dict[str, str]]]) -> None:
    print(f"\n{'=' * 60}")
    print(f"  OPEN SETTLEMENTS")
    print(f"{'=' * 60}")

    any_open = False
    for lane_name, rows in open_map.items():
        if not rows:
            continue
        any_open = True
        label = "PRIMARY" if "phase7" in lane_name else "SHADOW"
        print(f"\n  [{label}] {lane_name} — {len(rows)} open")
        for r in rows:
            print(f"    {r.get('track','?')} R{r.get('race_number','?')} | {r.get('rule_id','')} | cost ${r.get('expected_cost','?')} | key: {r.get('signal_key','')}")

    if not any_open:
        print("  No open settlements.")


def print_next_action(action: dict[str, Any]) -> None:
    print(f"\n{'=' * 60}")
    print(f"  NEXT ACTION: {action['priority']}")
    print(f"{'=' * 60}")
    print(f"  {action['reason']}")
    if action.get("command"):
        print(f"\n  >>> {action['command']}")
    if action.get("detail"):
        print(f"\n  {action['detail']}")
    print()


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def mode_preflight() -> None:
    pf = check_todays_cards_extended()
    print_preflight(pf)


def mode_status() -> None:
    st = gather_status()
    print_status(st)


def mode_post_race() -> None:
    open_map = gather_open_settlements()
    print_open_settlements(open_map)


def mode_next() -> None:
    pf = check_todays_cards_extended()
    st = gather_status()
    action = decide_next_action(pf, st)
    print_next_action(action)


def mode_auto() -> None:
    """Default mode: preflight + status + next action."""
    pf = check_todays_cards_extended()
    st = gather_status()

    print_preflight(pf)
    print_status(st)

    open_map = gather_open_settlements()
    total_open = sum(len(rows) for rows in open_map.values())
    if total_open > 0:
        print_open_settlements(open_map)

    action = decide_next_action(pf, st)
    print_next_action(action)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Superfecta operational checker — what should I do right now?",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  (none)      Auto — preflight + status + next action
  preflight   Check if today has primary paper-basket target races
  status      Show pipeline state and settlement counts
  post-race   List all open settlements needing outcomes
  next        Print only the recommended next command
""",
    )
    p.add_argument("mode", nargs="?", default="auto",
                   choices=["auto", "preflight", "status", "post-race", "next"],
                   help="Operating mode (default: auto)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    modes = {
        "auto": mode_auto,
        "preflight": mode_preflight,
        "status": mode_status,
        "post-race": mode_post_race,
        "next": mode_next,
    }

    try:
        modes[args.mode]()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
