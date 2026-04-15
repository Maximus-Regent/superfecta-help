#!/usr/bin/env python3
"""
Demo wrapper for live superfecta predictions on cards that are actually available today.

This does NOT change the production OP/CD basket in superfecta_ops.py.
It is a separate demo lane so we can generate live predictions today when other
cards like Keeneland are available through the NYRA API.

Examples:
  python3 demo_live_predictions.py
  python3 demo_live_predictions.py --include-cards keeneland
  python3 demo_live_predictions.py --include-cards keeneland --race-number 6
  python3 demo_live_predictions.py --selection-mode best-live --fallback-any --min-ev-roi 0
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
NYRA_DIR = BASE / "NYRA"
if str(NYRA_DIR) not in sys.path:
    sys.path.insert(0, str(NYRA_DIR))

from list_cards import list_cards
from list_races import list_races
from get_races import get_race_detail
from get_probables import get_probables
from model_main import (
    analyze_race_nyra,
    compute_win_percentages_and_odds,
    fetch_win_pool,
    save_results,
)

DEFAULT_MODEL = BASE / "Model" / "log_residual_model_normalized.json"
DEFAULT_OUT_DIR = BASE / "out" / "live_demo"
CACHE_DIR = BASE / ".live_scan_cache"
FINISHED_RACE_STATUSES = {5}
PROMO_CARD_TOKENS = ("P3", "P4", "P5", "DOUBLE", "PICK", "TURF")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate demoable live superfecta predictions for the next available race today.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s
  %(prog)s --include-cards keeneland
  %(prog)s --include-cards keeneland --race-number 6
  %(prog)s --selection-mode best-live --fallback-any --min-ev-roi 0
""",
    )
    p.add_argument(
        "--include-cards",
        nargs="*",
        default=["Keeneland"],
        help="Preferred card-name substrings. Default: Keeneland",
    )
    p.add_argument(
        "--scan-all-cards",
        action="store_true",
        help="Ignore preferred card filters and scan all candidate cards in best-live mode.",
    )
    p.add_argument(
        "--fallback-any",
        action="store_true",
        help="If preferred cards are unavailable, fall back to the best available card set today.",
    )
    p.add_argument(
        "--selection-mode",
        choices=["next", "best-live"],
        default="next",
        help="Pick the next race on the preferred card, or scan scoreable live candidates and choose the best current spot.",
    )
    p.add_argument("--race-number", type=int, help="Optional explicit race number on the selected card")
    p.add_argument("--race-id", help="Optional explicit race id override")
    p.add_argument("--model", default=str(DEFAULT_MODEL), help="Path to model JSON")
    p.add_argument("--sort-by", choices=["jointProb", "ev"], default="ev")
    p.add_argument("--top-combinations", type=int, default=15)
    p.add_argument(
        "--candidate-limit",
        type=int,
        default=4,
        help="Max candidate races to score when using --selection-mode best-live",
    )
    p.add_argument(
        "--max-minutes-to-post",
        type=int,
        default=45,
        help="Only consider races posting within this many minutes in --selection-mode best-live (0 = no limit)",
    )
    p.add_argument(
        "--min-ev-roi",
        type=float,
        help="Optional minimum EV ROI threshold for a hard PLAY label.",
    )
    p.add_argument(
        "--pass-below",
        type=float,
        default=-15.0,
        help="If the best EV ROI falls below this, label the race PASS. Between this and --min-ev-roi is FLOW.",
    )
    p.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help="Directory for CSV and markdown outputs",
    )
    p.add_argument(
        "--save-latest-json",
        action="store_true",
        help="Also write latest run metadata JSON in the output directory",
    )
    return p.parse_args()


def normalize_name(value: str) -> str:
    return " ".join((value or "").strip().upper().split())


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def card_penalty(card_name: str) -> int:
    upper = normalize_name(card_name)
    return 20 if any(token in upper for token in PROMO_CARD_TOKENS) else 0


def card_match_score(card_name: str, filters: list[str]) -> int:
    if not filters:
        return 0 - card_penalty(card_name)
    name = normalize_name(card_name)
    best = -10_000
    for raw_filter in filters:
        flt = normalize_name(raw_filter)
        if not flt:
            continue
        if name == flt:
            score = 100
        elif flt in name:
            score = 60
        else:
            score = -10_000
        score -= card_penalty(card_name)
        best = max(best, score)
    return best


def card_sort_key(card: dict[str, Any], filters: list[str]) -> tuple[Any, ...]:
    post_time = parse_iso(card.get("postTime")) or datetime.max.replace(tzinfo=timezone.utc)
    return (
        -card_match_score(card.get("cardName", ""), filters),
        post_time,
        -len(card.get("cardRaceNumbers", []) or []),
        card.get("cardName", ""),
    )


def filter_candidate_cards(cards: list[dict[str, Any]], filters: list[str], fallback_any: bool) -> list[dict[str, Any]]:
    matched = [c for c in cards if card_match_score(c.get("cardName", ""), filters) > -10_000]
    if matched:
        return sorted(matched, key=lambda c: card_sort_key(c, filters))

    if not fallback_any:
        names = ", ".join(c.get("cardName", "<unknown>") for c in cards)
        raise SystemExit(f"No cards matched {filters!r}. Available cards today: {names}")

    non_promo = [c for c in cards if card_penalty(c.get("cardName", "")) == 0]
    pool = non_promo or cards
    if not pool:
        raise SystemExit("No cards available today.")
    return sorted(pool, key=lambda c: card_sort_key(c, filters))


def choose_race(races: list[dict[str, Any]], race_number: int | None) -> dict[str, Any]:
    if not races:
        raise SystemExit("Selected card has no races.")
    if race_number is not None:
        for race in races:
            if int(race.get("raceNumber", -1)) == race_number:
                return race
        raise SystemExit(f"Race #{race_number} not found on selected card.")

    now = datetime.now(timezone.utc)
    candidates: list[tuple[int, datetime, dict[str, Any]]] = []
    for race in races:
        status = race.get("raceStatus")
        if status in FINISHED_RACE_STATUSES:
            continue
        post_time = parse_iso(race.get("postTime")) or now
        urgency = 0 if post_time >= now else 1
        candidates.append((urgency, post_time, race))

    if not candidates:
        raise SystemExit("No unfinished races found on selected card.")

    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][2]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_latest_cache(kind: str) -> Any | None:
    if not CACHE_DIR.exists():
        return None
    candidates = sorted(CACHE_DIR.glob(f"*_ {kind}_*.json".replace(" ", "")), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return None
    try:
        return json.loads(candidates[0].read_text(encoding="utf-8"))
    except Exception:
        return None


def safe_list_cards() -> list[dict[str, Any]]:
    try:
        return list_cards() or []
    except Exception:
        cached = load_latest_cache("cards")
        if cached:
            return cached
        raise


def run_prediction(race_id: str, model_path: str, top_n: int, sort_by: str) -> tuple[dict[str, Any], Any]:
    details = get_race_detail(race_id)
    if not details:
        raise SystemExit(f"Failed to fetch race details for raceId={race_id}")
    race_detail = details[0]

    active_runners = [r for r in race_detail.get("runners", []) if r.get("runnerStatus") == 1]
    if not active_runners:
        raise SystemExit("No active runners found.")

    win_pool = fetch_win_pool(race_detail)
    if not win_pool:
        raise SystemExit("No WIN pool found for selected race.")
    pool_id = win_pool["poolId"]

    pools = get_probables([pool_id])
    pool_info = next((p for p in pools if p.get("poolId") == pool_id), None)
    if not pool_info:
        raise SystemExit(f"No probables returned for poolId={pool_id}")

    win_pct, odds_map = compute_win_percentages_and_odds(active_runners, pool_info.get("probables", []))
    if not win_pct:
        raise SystemExit("No usable win pool percentages yet. Retry closer to post.")

    results_df = analyze_race_nyra(
        race_detail,
        active_runners,
        win_pct,
        odds_map,
        model_path,
        top_n,
        sort_by=sort_by,
        threads=max(1, os.cpu_count() or 1),
    )
    return race_detail, results_df


def build_paths(out_dir: Path, race_detail: dict[str, Any]) -> tuple[Path, Path]:
    track = normalize_name(race_detail.get("raceMeetingName", "track")).replace(" ", "_").lower()
    race_num = race_detail.get("raceNumber", "x")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = out_dir / f"{track}_race{race_num}_{stamp}.csv"
    report_path = out_dir / f"{track}_race{race_num}_{stamp}.md"
    return csv_path, report_path


def build_command(args: argparse.Namespace) -> str:
    parts = ["python3 demo_live_predictions.py"]
    if args.scan_all_cards:
        parts.append("--scan-all-cards")
    elif args.include_cards:
        parts.append("--include-cards " + " ".join(args.include_cards))
    if args.fallback_any:
        parts.append("--fallback-any")
    if args.selection_mode != "next":
        parts.append(f"--selection-mode {args.selection_mode}")
    if args.race_number:
        parts.append(f"--race-number {args.race_number}")
    if args.race_id:
        parts.append(f"--race-id {args.race_id}")
    if args.min_ev_roi is not None:
        parts.append(f"--min-ev-roi {args.min_ev_roi}")
    if args.pass_below != -15.0:
        parts.append(f"--pass-below {args.pass_below}")
    if args.candidate_limit != 4:
        parts.append(f"--candidate-limit {args.candidate_limit}")
    if args.max_minutes_to_post != 45:
        parts.append(f"--max-minutes-to-post {args.max_minutes_to_post}")
    if args.sort_by != "ev":
        parts.append(f"--sort-by {args.sort_by}")
    if args.top_combinations != 15:
        parts.append(f"--top-combinations {args.top_combinations}")
    if args.save_latest_json:
        parts.append("--save-latest-json")
    return " ".join(parts)


def candidate_summary_row(card: dict[str, Any], race: dict[str, Any], race_detail: dict[str, Any], results_df: Any) -> dict[str, Any]:
    top = results_df.iloc[0]
    return {
        "card_name": card.get("cardName"),
        "race_number": int(race.get("raceNumber", race_detail.get("raceNumber", -1))),
        "race_id": str(race.get("raceId", race_detail.get("raceId", ""))),
        "post_time": race_detail.get("postTime") or race.get("postTime"),
        "surface": race_detail.get("surface"),
        "distance": race_detail.get("distance"),
        "top_combo": top["combo"],
        "top_prob_pct": float(top["jointProbPct"]),
        "top_predicted_payout": float(top["predicted_payout"]),
        "top_ev_roi_pct": float(top["ev_roi_pct"]),
        "best_ev_roi_pct": float(results_df["ev_roi_pct"].max()),
    }


def collect_best_live_candidate(cards: list[dict[str, Any]], args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    now = datetime.now(timezone.utc)
    latest_allowed = None if args.max_minutes_to_post <= 0 else now + timedelta(minutes=args.max_minutes_to_post)
    active_filters = [] if args.scan_all_cards else args.include_cards

    race_candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    eligible_cards: list[dict[str, Any]] = []

    for card in cards:
        card_name = card.get("cardName", "")
        if "(H)" in normalize_name(card_name):
            continue
        if args.scan_all_cards and card.get("countryCode") not in {None, "US"}:
            continue
        status = card.get("raceStatus")
        if status in FINISHED_RACE_STATUSES:
            continue
        card_post = parse_iso(card.get("postTime"))
        if card_post and card_post < now:
            continue
        if latest_allowed and card_post and card_post > latest_allowed:
            continue
        if not card.get("raceId"):
            rejected.append({"card_name": card_name, "reason": "missing raceId on card snapshot"})
            continue
        eligible_cards.append(card)

    eligible_cards.sort(
        key=lambda card: (
            parse_iso(card.get("postTime")) or datetime.max.replace(tzinfo=timezone.utc),
            -card_match_score(card.get("cardName", ""), active_filters),
        )
    )
    cards_to_probe = eligible_cards[: max(args.candidate_limit * 2, args.candidate_limit)]

    for card in cards_to_probe:
        race_candidates.append({
            "card": card,
            "race": {
                "raceId": card.get("raceId"),
                "raceNumber": card.get("cardRaceNumber") or card.get("raceNumber"),
                "postTime": card.get("postTime"),
                "raceStatus": card.get("raceStatus"),
            },
            "post_time": parse_iso(card.get("postTime")) or datetime.max.replace(tzinfo=timezone.utc),
        })

    race_candidates.sort(
        key=lambda item: (
            item["post_time"],
            -card_match_score(item["card"].get("cardName", ""), active_filters),
        )
    )
    race_candidates = race_candidates[: max(1, args.candidate_limit)]

    if not race_candidates:
        raise SystemExit("No candidate live races found in the current scan window.")

    scored: list[dict[str, Any]] = []
    for candidate in race_candidates:
        card = candidate["card"]
        race = candidate["race"]
        race_id = str(race.get("raceId"))
        try:
            race_detail, results_df = run_prediction(
                race_id=race_id,
                model_path=str(args.model),
                top_n=args.top_combinations,
                sort_by=args.sort_by,
            )
            scored.append({
                "card": card,
                "race": race,
                "race_detail": race_detail,
                "results_df": results_df,
                "summary": candidate_summary_row(card, race, race_detail, results_df),
            })
        except SystemExit as exc:
            rejected.append({
                "card_name": card.get("cardName"),
                "race_number": race.get("raceNumber"),
                "race_id": race_id,
                "reason": str(exc),
            })
        except Exception as exc:
            rejected.append({
                "card_name": card.get("cardName"),
                "race_number": race.get("raceNumber"),
                "race_id": race_id,
                "reason": str(exc),
            })

    if not scored:
        reasons = "; ".join(
            f"{row.get('card_name')} R{row.get('race_number', '?')}: {row.get('reason')}" for row in rejected[:5]
        )
        raise SystemExit(f"No scoreable live races found. {reasons}")

    scored.sort(
        key=lambda item: (
            -item["summary"]["best_ev_roi_pct"],
            parse_iso(item["summary"]["post_time"]) or datetime.max.replace(tzinfo=timezone.utc),
        )
    )
    return scored[0], [item["summary"] for item in scored], rejected


def write_report(
    report_path: Path,
    args: argparse.Namespace,
    selected_card: dict[str, Any],
    selected_race: dict[str, Any],
    race_detail: dict[str, Any],
    csv_path: Path,
    results_df: Any,
    decision: str,
    decision_reason: str | None,
    candidate_rows: list[dict[str, Any]] | None,
) -> None:
    top_rows = results_df.head(5).to_dict("records")
    command = build_command(args)
    lines = [
        "# Live Demo Prediction Report",
        "",
        f"Generated: {datetime.now().astimezone().isoformat()}",
        "",
        "## What this is",
        "",
        "This is the demo lane for live predictions on cards that are actually available today.",
        "It does not change the production OP/CD basket in `superfecta_ops.py`.",
        "",
        "## Decision",
        "",
        f"- Decision: **{decision}**",
    ]
    if decision_reason:
        lines.append(f"- Reason: {decision_reason}")

    lines.extend(
        [
            "",
            "## Card and race used",
            "",
            f"- Selected card: {selected_card.get('cardName')}",
            f"- Card date: {selected_card.get('cardDate')}",
            f"- Selected race: Race #{selected_race.get('raceNumber')} (raceId {selected_race.get('raceId')})",
            f"- Post time: {race_detail.get('postTime')}",
            f"- Surface: {race_detail.get('surface')}",
            f"- Distance: {race_detail.get('distance')}",
            f"- Purse: {race_detail.get('totalPurse', {}).get('amount', 'unknown')}",
            "",
            "## Command",
            "",
            "```bash",
            command,
            "```",
            "",
            "## Output",
            "",
            f"- CSV: `{csv_path}`",
            f"- Rows saved: {len(results_df)}",
            f"- Most likely combo probability: {results_df['jointProbPct'].max():.4f}%",
            f"- Best predicted payout in saved set: ${results_df['predicted_payout'].max():,.2f}",
            f"- Best EV ROI in saved set: {results_df['ev_roi_pct'].max():.2f}%",
            "",
            "## Top 5 combos",
            "",
        ]
    )

    for row in top_rows:
        lines.append(
            f"- #{int(row['rank'])} {row['combo']} | prob {row['jointProbPct']:.4f}% | predicted ${row['predicted_payout']:.2f} | EV ROI {row['ev_roi_pct']:.2f}%"
        )

    if candidate_rows:
        lines.extend(["", "## Candidate leaderboard", ""])
        for idx, row in enumerate(candidate_rows[:5], start=1):
            lines.append(
                f"- #{idx} {row['card_name']} R{row['race_number']} | post {row['post_time']} | top combo {row['top_combo']} | best EV ROI {row['best_ev_roi_pct']:.2f}%"
            )

    lines.extend(
        [
            "",
            "## Operational note",
            "",
            "- Production basket status is still governed by `superfecta_ops.py` and remains OP/CD-only.",
            "- This demo mode exists so we can show live predictions on cards that are actually available today without pretending that changes the production trading basket.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_candidate_rows(candidate_rows: list[dict[str, Any]] | None) -> None:
    if not candidate_rows:
        return
    print("\nCandidate leaderboard:")
    for idx, row in enumerate(candidate_rows[:5], start=1):
        print(
            f"  {idx}. {row['card_name']} R{row['race_number']} | post {row['post_time']} | best EV ROI {row['best_ev_roi_pct']:.2f}% | top combo {row['top_combo']}"
        )


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)

    cards = safe_list_cards() or []
    if not cards:
        raise SystemExit("No NYRA API cards available today.")

    card_filters = [] if args.scan_all_cards else args.include_cards
    filtered_cards = filter_candidate_cards(cards, card_filters, args.fallback_any)

    candidate_rows: list[dict[str, Any]] | None = None
    rejected_rows: list[dict[str, Any]] = []

    if args.race_id:
        selected_card: dict[str, Any] = {"cardName": "Direct race-id override", "cardDate": None}
        selected_race: dict[str, Any] = {"raceId": args.race_id, "raceNumber": args.race_number}
        race_id = str(args.race_id)
        race_detail, results_df = run_prediction(
            race_id=race_id,
            model_path=str(args.model),
            top_n=args.top_combinations,
            sort_by=args.sort_by,
        )
    elif args.selection_mode == "best-live":
        best, candidate_rows, rejected_rows = collect_best_live_candidate(filtered_cards, args)
        selected_card = best["card"]
        selected_race = best["race"]
        race_detail = best["race_detail"]
        results_df = best["results_df"]
        race_id = str(selected_race["raceId"])
    else:
        selected_card = filtered_cards[0]
        races = list_races([selected_card["cardId"]])
        selected_race = choose_race(races, args.race_number)
        race_id = str(selected_race["raceId"])
        race_detail, results_df = run_prediction(
            race_id=race_id,
            model_path=str(args.model),
            top_n=args.top_combinations,
            sort_by=args.sort_by,
        )

    decision = "PLAY"
    decision_reason = None
    best_ev_roi = float(results_df["ev_roi_pct"].max())
    play_threshold = args.min_ev_roi if args.min_ev_roi is not None else 0.0
    if best_ev_roi < args.pass_below:
        decision = "PASS"
        decision_reason = (
            f"Best available scoreable live race only reached {best_ev_roi:.2f}% EV ROI, below pass floor {args.pass_below:.2f}%"
        )
    elif best_ev_roi < play_threshold:
        decision = "FLOW"
        decision_reason = (
            f"Best available scoreable live race reached {best_ev_roi:.2f}% EV ROI, below hard PLAY threshold {play_threshold:.2f}% but above pass floor {args.pass_below:.2f}%"
        )

    csv_path, report_path = build_paths(out_dir, race_detail)
    save_results(results_df, str(csv_path), race_detail)
    write_report(
        report_path,
        args,
        selected_card,
        selected_race,
        race_detail,
        csv_path,
        results_df,
        decision,
        decision_reason,
        candidate_rows,
    )

    latest = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "selection_mode": args.selection_mode,
        "decision": decision,
        "decision_reason": decision_reason,
        "pass_reason": decision_reason if decision == "PASS" else None,
        "selected_card": selected_card,
        "selected_race": selected_race,
        "race_detail": {
            "raceMeetingName": race_detail.get("raceMeetingName"),
            "raceNumber": race_detail.get("raceNumber"),
            "postTime": race_detail.get("postTime"),
            "surface": race_detail.get("surface"),
            "distance": race_detail.get("distance"),
        },
        "csv_path": str(csv_path),
        "report_path": str(report_path),
        "candidate_summary": candidate_rows,
        "rejected_candidates": rejected_rows,
        "top_combo": None if results_df.empty else results_df.iloc[0].to_dict(),
    }
    if args.save_latest_json:
        (out_dir / "latest_demo_run.json").write_text(json.dumps(latest, indent=2, default=str), encoding="utf-8")

    print("\n=== LIVE DEMO SUMMARY ===")
    print(f"Decision: {decision}")
    if decision_reason:
        print(f"Reason: {decision_reason}")
    print(f"Card: {selected_card.get('cardName')}")
    print(f"Race: {race_detail.get('raceMeetingName')} Race #{race_detail.get('raceNumber')} (raceId {race_id})")
    print(f"Post time: {race_detail.get('postTime')}")
    print(f"Saved CSV: {csv_path}")
    print(f"Saved report: {report_path}")
    if not results_df.empty:
        top = results_df.iloc[0]
        print(
            f"Top combo: {top['combo']} | prob {top['jointProbPct']:.4f}% | predicted ${top['predicted_payout']:.2f} | EV ROI {top['ev_roi_pct']:.2f}%"
        )
    print_candidate_rows(candidate_rows)
    print("\nNote: production OP/CD basket is unchanged; this is the demo lane for today’s available cards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
