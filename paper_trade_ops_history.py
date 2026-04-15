#!/usr/bin/env python3
"""
Generate a rolling operations history for the paper-trade daily runner.

Purpose:
- distinguish no-target race days from clean no-qualifier days
- surface operational failures without opening each daily folder manually
- keep the summary tied to existing daily artifacts, not a new state path
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
DEFAULT_RUNS_ROOT = BASE / "out" / "daily_portfolio_runs"
DEFAULT_MD = BASE / "OPS_HISTORY.md"
DEFAULT_CSV = BASE / "ops_history.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate a rolling ops history from daily paper-trade run folders")
    p.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT), help="Directory containing YYYY-MM-DD daily run folders")
    p.add_argument("--limit", type=int, default=14, help="Maximum number of run days to include, newest first")
    p.add_argument("--md-output", default=str(DEFAULT_MD), help="Markdown output path")
    p.add_argument("--csv-output", default=str(DEFAULT_CSV), help="CSV output path")
    return p.parse_args()


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def summarize_calendar(preflight: dict[str, Any] | None) -> tuple[str, str]:
    if not preflight:
        return "MISSING", "Preflight note missing."
    if preflight.get("error"):
        return "UNKNOWN", f"Preflight API error: {preflight['error']}"
    if not preflight.get("api_ok", False):
        return "UNKNOWN", "Preflight API unavailable."
    if preflight.get("has_targets"):
        tracks = ", ".join(preflight.get("relevant_tracks") or []) or "OP / CD"
        return "OP/CD ACTIVE", f"Active-basket tracks racing: {tracks}."
    shadow = ", ".join(preflight.get("shadow_tracks") or [])
    detail = f"No active OP/CD cards across {safe_int(preflight.get('total_cards'))} NYRA card(s)."
    if shadow:
        detail += f" Shadow-only tracks present: {shadow}."
    return "NO TARGETS", detail


def summarize_lane(status: dict[str, Any] | None) -> tuple[str, str, str, int, int, int, bool]:
    if not status:
        return "MISSING", "missing", "Status file missing.", 0, 0, 0, False

    observation = str(status.get("observation_result") or "missing")
    scan_hits = safe_int(status.get("scan_hit_count"))
    recommendations = safe_int(status.get("recommendation_count"))
    bets = safe_int(status.get("bet_count"))
    cache_only = bool(status.get("cache_only", False))
    mode = "cache-only" if cache_only else "live"

    if observation == "bets_ready":
        label = f"BETS READY ({bets} bet{'s' if bets != 1 else ''})"
        detail = f"{mode} run produced {bets} bet(s) from {recommendations} recommendation(s)."
    elif observation == "signals_logged_no_bet":
        label = "SIGNALS, NO BET"
        detail = f"{mode} run logged {scan_hits} hit(s) but produced no BET recommendation."
    elif observation == "clean_empty_run":
        label = "CLEAN EMPTY"
        detail = f"{mode} run completed cleanly with 0 hits and 0 recommendations."
    elif observation == "partial_cache_empty_run":
        label = "PARTIAL CACHE EMPTY"
        detail = "Run finished empty on partial cache coverage, so treat the empty result as operationally limited."
    elif observation == "scanner_failed_empty_run":
        label = "SCANNER FAILED"
        detail = "Scanner failed before producing a usable lane result."
    else:
        result = str(status.get("result") or "missing")
        stage = str(status.get("stage") or "unknown")
        label = observation.upper().replace("_", " ") if observation != "missing" else result.upper()
        detail = f"Observed state: result={result}, stage={stage}, observation={observation}."

    issue = label in {"SCANNER FAILED", "MISSING"} or str(status.get("result") or "").lower() not in {"", "ok"}
    return label, observation, detail, scan_hits, recommendations, bets, issue


def build_takeaway(calendar_label: str, calendar_detail: str, primary_label: str, primary_obs: str,
                   primary_hits: int, primary_recommendations: int, primary_bets: int, primary_issue: bool) -> str:
    if primary_issue:
        return "Primary lane had an operational issue. Read the latest daily summary and sidecars before drawing conclusions."
    if calendar_label == "UNKNOWN":
        return "Calendar state was unknown, so treat the daily result as operationally ambiguous."
    if calendar_label == "NO TARGETS":
        if primary_obs == "clean_empty_run":
            return "No active OP/CD cards. Empty primary lane is expected, not evidence of a miss."
        return "No active OP/CD cards, but the primary lane did not finish with a normal clean-empty read."
    if primary_bets > 0:
        return f"Primary lane produced {primary_bets} bet(s). Review the lane artifacts before the races go off."
    if primary_recommendations > 0 or primary_hits > 0:
        return f"OP/CD were active and the primary lane found {primary_hits} hit(s), but nothing reached a bet-ready state."
    if primary_obs == "clean_empty_run":
        return "OP/CD were active, but the primary lane found no qualifying races."
    return calendar_detail


def collect_rows(runs_root: Path, limit: int) -> list[dict[str, Any]]:
    if not runs_root.exists():
        return []

    run_dirs = sorted([p for p in runs_root.iterdir() if p.is_dir()], reverse=True)
    rows: list[dict[str, Any]] = []

    for run_dir in run_dirs:
        preflight = read_json(run_dir / "preflight_note.json")
        primary = read_json(run_dir / "phase7_current_paper" / "pipeline_status.json")
        shadow = read_json(run_dir / "phase8_shadow" / "pipeline_status.json")
        daily_summary_exists = (run_dir / "daily_summary.txt").exists()
        if not any([preflight, primary, shadow, daily_summary_exists]):
            continue

        calendar_label, calendar_detail = summarize_calendar(preflight)
        primary_label, primary_obs, primary_detail, primary_hits, primary_recs, primary_bets, primary_issue = summarize_lane(primary)
        shadow_label, shadow_obs, shadow_detail, shadow_hits, shadow_recs, shadow_bets, shadow_issue = summarize_lane(shadow)
        takeaway = build_takeaway(
            calendar_label,
            calendar_detail,
            primary_label,
            primary_obs,
            primary_hits,
            primary_recs,
            primary_bets,
            primary_issue,
        )

        row = {
            "date": run_dir.name,
            "run_root": str(run_dir.relative_to(BASE)),
            "calendar_state": calendar_label,
            "calendar_detail": calendar_detail,
            "preflight_note": (preflight or {}).get("note", "Preflight note missing."),
            "primary_state": primary_label,
            "primary_observation_result": primary_obs,
            "primary_scan_hits": primary_hits,
            "primary_recommendations": primary_recs,
            "primary_bets": primary_bets,
            "primary_cache_only": bool((primary or {}).get("cache_only", False)),
            "shadow_state": shadow_label,
            "shadow_observation_result": shadow_obs,
            "shadow_scan_hits": shadow_hits,
            "shadow_recommendations": shadow_recs,
            "shadow_bets": shadow_bets,
            "shadow_cache_only": bool((shadow or {}).get("cache_only", False)),
            "primary_issue": primary_issue,
            "shadow_issue": shadow_issue,
            "takeaway": takeaway,
        }
        rows.append(row)
        if len(rows) >= limit:
            break

    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "date",
        "run_root",
        "calendar_state",
        "calendar_detail",
        "preflight_note",
        "primary_state",
        "primary_observation_result",
        "primary_scan_hits",
        "primary_recommendations",
        "primary_bets",
        "primary_cache_only",
        "shadow_state",
        "shadow_observation_result",
        "shadow_scan_hits",
        "shadow_recommendations",
        "shadow_bets",
        "shadow_cache_only",
        "primary_issue",
        "shadow_issue",
        "takeaway",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_md(path: Path, rows: list[dict[str, Any]], limit: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    run_days = len(rows)
    target_days = sum(1 for row in rows if row["calendar_state"] == "OP/CD ACTIVE")
    no_target_days = sum(1 for row in rows if row["calendar_state"] == "NO TARGETS")
    unknown_days = sum(1 for row in rows if row["calendar_state"] == "UNKNOWN")
    primary_issue_days = sum(1 for row in rows if row["primary_issue"])
    primary_activity_days = sum(1 for row in rows if row["primary_scan_hits"] > 0 or row["primary_recommendations"] > 0 or row["primary_bets"] > 0)

    lines = [
        "# Paper-Trade Ops History",
        "",
        "This note gives a rolling operational read across recent daily paper-trade runs.",
        "It is meant to answer one practical question honestly: was a quiet day caused by the race calendar, a clean no-qualifier scan, or a pipeline problem?",
        "",
        f"Included run days: **{run_days}** (newest first, max `{limit}`)",
        "",
        "## Summary",
        "",
        f"- OP / CD target days: **{target_days}**",
        f"- No-target days: **{no_target_days}**",
        f"- Calendar-unknown days: **{unknown_days}**",
        f"- Primary-lane issue days: **{primary_issue_days}**",
        f"- Primary-lane activity days (hits or recommendations or bets): **{primary_activity_days}**",
        "",
        "## Daily log",
        "",
        "| Date | Calendar | Primary lane | Shadow lane | Takeaway |",
        "|---|---|---|---|---|",
    ]

    if rows:
        for row in rows:
            primary = f"{row['primary_state']} (hits={row['primary_scan_hits']}, recs={row['primary_recommendations']}, bets={row['primary_bets']})"
            shadow = f"{row['shadow_state']} (hits={row['shadow_scan_hits']}, recs={row['shadow_recommendations']}, bets={row['shadow_bets']})"
            lines.append(f"| `{row['date']}` | {row['calendar_state']} | {primary} | {shadow} | {row['takeaway']} |")
        lines.extend([
            "",
            "## Latest preflight notes",
            "",
        ])
        for row in rows[:5]:
            lines.append(f"- `{row['date']}`: {row['preflight_note']}")
    else:
        lines.append("| _none yet_ | _n/a_ | _n/a_ | _n/a_ | No daily run folders were found. |")

    lines.extend([
        "",
        "## Interpretation guardrails",
        "",
        "- `NO TARGETS` means OP / CD were not active that day, so an empty primary lane should not be read as a rules miss.",
        "- `CLEAN EMPTY` means the lane ran normally and simply found no qualifying races for that ruleset.",
        "- `SCANNER FAILED` or `MISSING` means treat the day as operationally unresolved until the sidecars are checked.",
        "- This is an ops artifact, not a performance-evaluation artifact. Use lane monitors and forward checks for settled-race evidence.",
        "",
    ])

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    rows = collect_rows(Path(args.runs_root), args.limit)
    write_csv(Path(args.csv_output), rows)
    write_md(Path(args.md_output), rows, args.limit)
    print(f"Wrote {args.csv_output}")
    print(f"Wrote {args.md_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
