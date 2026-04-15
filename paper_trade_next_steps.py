#!/usr/bin/env python3
"""
Suggest the next 2-3 commands for a paper-trade lane.

Purpose:
- turn lane state into concrete next actions
- reduce drift when the daily run is empty, waiting on settlement, or finally decision-grade
- keep advice tied to the current frozen-standard lane data
"""

from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from paper_trade_lane_monitor import build_monitor_payload
from paper_trade_forward_check import DEFAULT_FROZEN_EVAL
from paper_trade_status_summary import read_json as read_status_json

BASE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = BASE / "out" / "paper_trade_next_steps.md"
DEFAULT_RUNNER = BASE / "run_daily_portfolio_observation.sh"
SETTLEMENT_HELPER = BASE / "paper_trade_settlement_helper.py"
LANE_MONITOR = BASE / "paper_trade_lane_monitor.py"
FORWARD_CHECK = BASE / "paper_trade_forward_check.py"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Suggest the next few commands for a paper-trade lane")
    p.add_argument("--signals-ledger", required=True, help="Signal ledger CSV path")
    p.add_argument("--recommendation-ledger", required=True, help="Recommendation ledger CSV path")
    p.add_argument("--settlement-ledger", required=True, help="Settlement ledger CSV path")
    p.add_argument("--rules", required=True, help="Rules JSON path for the lane")
    p.add_argument("--frozen-eval", default=str(DEFAULT_FROZEN_EVAL), help="Frozen evaluation summary CSV path")
    p.add_argument("--min-settled", type=int, default=30, help="Decision-grade settled race threshold")
    p.add_argument("--max-open", type=int, default=5, help="Maximum open rows to inspect in the underlying monitor payload")
    p.add_argument("--runner", default=str(DEFAULT_RUNNER), help="Daily runner command path to recommend when more observation is needed")
    p.add_argument("--scanner-status", help="Optional scanner status JSON path for the latest lane run")
    p.add_argument("--pipeline-status", help="Optional pipeline status JSON path for the latest lane run")
    p.add_argument("--preflight-note", help="Optional plain-text preflight note to include in the output")
    p.add_argument("--format", choices=["text", "md", "json"], default="md", help="Output format")
    p.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Optional output path")
    return p.parse_args()


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def display_path(raw: str) -> str:
    path = Path(raw).expanduser()
    candidate = path if path.is_absolute() else (BASE / path)
    try:
        return str(candidate.resolve().relative_to(BASE.resolve()))
    except Exception:
        return raw


def display_runner(raw: str) -> str:
    shown = display_path(raw)
    if shown == raw:
        return shlex.quote(raw)
    return shlex.quote(f"./{shown}")


def read_preflight_note(args: argparse.Namespace) -> str | None:
    if not args.preflight_note:
        return None
    path = Path(args.preflight_note)
    if path.exists() and path.is_file():
        text = path.read_text(encoding="utf-8").strip()
        return text or None
    text = str(args.preflight_note).strip()
    return text or None


def describe_recent_run(args: argparse.Namespace) -> str | None:
    scanner = read_status_json(Path(args.scanner_status)) if args.scanner_status else None
    pipeline = read_status_json(Path(args.pipeline_status)) if args.pipeline_status else None
    if scanner is None and pipeline is None:
        return None

    scanner_result = (pipeline or {}).get("scanner_result") or (scanner or {}).get("result") or "missing"
    observation_result = (pipeline or {}).get("observation_result")
    cache_only = bool((pipeline or {}).get("cache_only", (scanner or {}).get("cache_only", False)))
    card_count = int((scanner or {}).get("card_count", 0) or 0)
    race_count = int((scanner or {}).get("race_count", 0) or 0)
    raw_hits = int((pipeline or {}).get("scanner_raw_hit_count", (scanner or {}).get("raw_hit_count", 0)) or 0)
    bet_count = int((pipeline or {}).get("bet_count", 0) or 0)
    recommendation_count = int((pipeline or {}).get("recommendation_count", 0) or 0)

    if observation_result == "scanner_failed_empty_run" or scanner_result == "scanner_error":
        note = "Latest run context: scanner failed before producing signals."
        if cache_only:
            note += " In cache-only mode, that usually means the needed cache files were missing for this day."
        return note

    if observation_result == "partial_cache_empty_run" or str(scanner_result).startswith("partial_cache"):
        return "Latest run context: the latest run depended on partial cache data and finished empty, so treat the empty result as an operational limitation, not evidence."

    if observation_result == "clean_empty_run" or scanner_result in {"no_qualifiers", "no_matching_cards", "reused_input_empty"}:
        if scanner_result == "no_matching_cards" or (card_count == 0 and race_count == 0):
            return "Latest run context: no matching cards were available for this ruleset in the latest scan window."
        mode = "cache-only check" if cache_only else "live scan"
        scope = f" across {card_count} card(s) and {race_count} race(s)" if card_count or race_count else ""
        return f"Latest run context: the latest {mode} completed cleanly and found no qualifying races{scope}."

    if observation_result == "bets_ready":
        return f"Latest run context: the latest run produced {bet_count} BET recommendation(s) out of {recommendation_count} total recommendation(s)."

    if observation_result == "signals_logged_no_bet":
        return f"Latest run context: the latest run logged signals but produced no BET recommendations ({recommendation_count} recommendation(s), {raw_hits} raw hit(s))."

    return None


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    monitor_args = SimpleNamespace(
        signals_ledger=args.signals_ledger,
        recommendation_ledger=args.recommendation_ledger,
        settlement_ledger=args.settlement_ledger,
        rules=args.rules,
        frozen_eval=args.frozen_eval,
        min_settled=args.min_settled,
        max_open=args.max_open,
        format="json",
        output=None,
    )
    monitor_payload = build_monitor_payload(monitor_args)
    forward = monitor_payload["forward"]
    observed = forward["portfolio_observed"]
    open_payload = monitor_payload["open_settlements"]
    recent_run_context = describe_recent_run(args)
    preflight_note = read_preflight_note(args)

    signals_ledger_disp = display_path(args.signals_ledger)
    recommendation_ledger_disp = display_path(args.recommendation_ledger)
    settlement_ledger_disp = display_path(args.settlement_ledger)
    rules_disp = display_path(args.rules)
    settlement_helper_disp = display_path(str(SETTLEMENT_HELPER))
    lane_monitor_disp = display_path(str(LANE_MONITOR))
    forward_check_disp = display_path(str(FORWARD_CHECK))

    lane_monitor_cmd = shell_join([
        "python3", lane_monitor_disp,
        "--signals-ledger", signals_ledger_disp,
        "--recommendation-ledger", recommendation_ledger_disp,
        "--settlement-ledger", settlement_ledger_disp,
        "--rules", rules_disp,
    ])
    forward_check_cmd = shell_join([
        "python3", forward_check_disp,
        "--signals-ledger", signals_ledger_disp,
        "--recommendation-ledger", recommendation_ledger_disp,
        "--settlement-ledger", settlement_ledger_disp,
        "--rules", rules_disp,
    ])
    list_open_cmd = shell_join([
        "python3", settlement_helper_disp,
        "list-open",
        "--settlement-ledger", settlement_ledger_disp,
    ])
    settle_example_key = open_payload["rows"][0]["signal_key"] if open_payload["rows"] else "<signal_key>"
    settle_cmd = shell_join([
        "python3", settlement_helper_disp,
        "settle",
        "--settlement-ledger", settlement_ledger_disp,
        "--signal-key", settle_example_key,
        "--outcome", "HIT",
        "--actual-return", "<dollars_returned>",
        "--actual-cost", "<dollars_wagered>",
        "--settled-ts", "YYYY-MM-DDTHH:MM:SS",
        "--notes", "manual settlement entry",
    ])
    runner_cmd = display_runner(args.runner)

    if open_payload["count"] > 0:
        state = "NEEDS SETTLEMENT"
        why = (
            f"{open_payload['count']} settlement row(s) are still open, so the clean next step is result entry before asking the forward checker for a fresher read."
        )
        commands = [list_open_cmd, settle_cmd, lane_monitor_cmd]
    elif observed["settled"] <= 0:
        state = "WAITING FOR FIRST SETTLED RACES"
        why = "No races are settled yet, so the right move is to keep the daily observation loop running instead of over-reading empty forward metrics."
        commands = [runner_cmd, lane_monitor_cmd, list_open_cmd]
    elif observed["settled"] < args.min_settled:
        state = "COLLECTING SAMPLE"
        why = (
            f"There are {observed['settled']} settled races, which is still below the decision-grade threshold of {args.min_settled}. Keep refreshing the lane read, but do not treat it as promotion-grade evidence yet."
        )
        commands = [lane_monitor_cmd, forward_check_cmd, runner_cmd]
    else:
        state = "DECISION-GRADE REVIEW"
        why = (
            f"The lane has reached {observed['settled']} settled races, so it is worth reading the forward check and lane monitor as a genuine benchmark comparison instead of just an early-noise snapshot."
        )
        commands = [forward_check_cmd, lane_monitor_cmd, list_open_cmd]

    return {
        "lane_label": monitor_payload["lane_label"],
        "state": state,
        "why": why,
        "assessment": forward["portfolio_assessment"],
        "settled": observed["settled"],
        "open": observed["open"],
        "open_settlements": open_payload["count"],
        "min_settled": args.min_settled,
        "recent_run_context": recent_run_context,
        "preflight_note": preflight_note,
        "commands": commands,
        "files": {
            "signals_ledger": signals_ledger_disp,
            "recommendation_ledger": recommendation_ledger_disp,
            "settlement_ledger": settlement_ledger_disp,
            "rules": rules_disp,
        },
    }


def render_text(payload: dict[str, Any]) -> str:
    lines = [
        f"{payload['lane_label']} next steps",
        f"- State: {payload['state']}",
        f"- Forward assessment: {payload['assessment']}",
        f"- Settled races: {payload['settled']} | open races: {payload['open']} | open settlement rows: {payload['open_settlements']}",
        f"- Why: {payload['why']}",
        *( [f"- {payload['recent_run_context']}"] if payload.get('recent_run_context') else [] ),
        *( [f"- {payload['preflight_note']}"] if payload.get('preflight_note') else [] ),
        "- Recommended commands:",
    ]
    for i, cmd in enumerate(payload["commands"], start=1):
        lines.append(f"  {i}. {cmd}")
    return "\n".join(lines) + "\n"


def render_md(payload: dict[str, Any]) -> str:
    lines = [
        "# Paper-Trade Next Steps",
        "",
        f"Lane: **{payload['lane_label']}**",
        "",
        "## Current State",
        "",
        f"- State: **{payload['state']}**",
        f"- Forward assessment: **{payload['assessment']}**",
        f"- Settled races: `{payload['settled']}`",
        f"- Open races: `{payload['open']}`",
        f"- Open settlement rows: `{payload['open_settlements']}`",
        f"- Why: {payload['why']}",
        *( [f"- {payload['recent_run_context']}"] if payload.get('recent_run_context') else [] ),
        *( [f"- {payload['preflight_note']}"] if payload.get('preflight_note') else [] ),
        "",
        "## Recommended next commands",
        "",
    ]
    for i, cmd in enumerate(payload["commands"], start=1):
        lines.append(f"{i}. `{cmd}`")
    lines.extend([
        "",
        "## Files behind this recommendation",
        "",
        f"- Signals ledger: `{payload['files']['signals_ledger']}`",
        f"- Recommendation ledger: `{payload['files']['recommendation_ledger']}`",
        f"- Settlement ledger: `{payload['files']['settlement_ledger']}`",
        f"- Rules: `{payload['files']['rules']}`",
        "",
    ])
    return "\n".join(lines)


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    payload = build_payload(args)

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
