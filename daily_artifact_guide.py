#!/usr/bin/env python3
"""
Generate a compact guide for which artifacts matter in daily use.

Purpose:
- keep the growing report stack navigable
- separate daily-use artifacts from benchmark-only and research-only files
- point Cole at the latest run outputs without hand-editing paths
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

BASE = Path(__file__).resolve().parent
OUT_MD = BASE / "DAILY_ARTIFACT_GUIDE.md"
RUNS_ROOT = BASE / "out" / "daily_portfolio_runs"


@dataclass
class Item:
    path: Path
    why: str


def latest_run_root() -> Path | None:
    if not RUNS_ROOT.exists():
        return None
    candidates = [p for p in RUNS_ROOT.iterdir() if p.is_dir()]
    if not candidates:
        return None
    return sorted(candidates)[-1]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def status(path: Path) -> str:
    return "present" if path.exists() else "missing"


def render_items(items: Iterable[Item]) -> list[str]:
    lines: list[str] = []
    for item in items:
        lines.append(f"| `{rel(item.path)}` | `{status(item.path)}` | {item.why} |")
    return lines


def main() -> int:
    latest = latest_run_root()
    latest_label = rel(latest) if latest else "none yet"

    latest_daily = latest / "daily_summary.txt" if latest else BASE / "out" / "daily_portfolio_runs" / "YYYY-MM-DD" / "daily_summary.txt"
    latest_preflight = latest / "preflight_note.txt" if latest else BASE / "out" / "daily_portfolio_runs" / "YYYY-MM-DD" / "preflight_note.txt"
    latest_primary_monitor = latest / "phase7_current_paper" / "lane_monitor.md" if latest else BASE / "out" / "daily_portfolio_runs" / "YYYY-MM-DD" / "phase7_current_paper" / "lane_monitor.md"
    latest_shadow_monitor = latest / "phase8_shadow" / "lane_monitor.md" if latest else BASE / "out" / "daily_portfolio_runs" / "YYYY-MM-DD" / "phase8_shadow" / "lane_monitor.md"
    latest_primary_next = latest / "phase7_current_paper" / "next_steps.md" if latest else BASE / "out" / "daily_portfolio_runs" / "YYYY-MM-DD" / "phase7_current_paper" / "next_steps.md"
    latest_shadow_next = latest / "phase8_shadow" / "next_steps.md" if latest else BASE / "out" / "daily_portfolio_runs" / "YYYY-MM-DD" / "phase8_shadow" / "next_steps.md"
    latest_primary_forward = latest / "phase7_current_paper" / "forward_check.md" if latest else BASE / "out" / "daily_portfolio_runs" / "YYYY-MM-DD" / "phase7_current_paper" / "forward_check.md"
    latest_shadow_forward = latest / "phase8_shadow" / "forward_check.md" if latest else BASE / "out" / "daily_portfolio_runs" / "YYYY-MM-DD" / "phase8_shadow" / "forward_check.md"

    daily_use = [
        Item(BASE / "COLE_STATUS_AND_PLAN.md", "Single honest status document. Read first when deciding what matters."),
        Item(BASE / "run_daily_portfolio_observation.sh", "Preferred daily runner for primary Phase 7 current-paper lane plus Phase 8 shadow lane."),
        Item(latest_daily, f"Combined latest run summary. Current latest run root: `{latest_label}`."),
        Item(BASE / "OPS_HISTORY.md", "Rolling ops log across recent daily runs. Best first read when several quiet days in a row need explanation."),
        Item(latest_preflight, "Shared calendar note for the latest run. Read this first on empty days to see whether OP / CD were even active."),
        Item(latest_primary_next, "Best immediate operator read for the current primary lane: exact next commands based on the current lane state."),
        Item(latest_shadow_next, "Best immediate operator read for the shadow lane: exact next commands based on the current lane state."),
        Item(latest_primary_monitor, "Best one-glance context read for the current primary lane: forward state plus settlement queue."),
        Item(latest_shadow_monitor, "Best one-glance context read for the shadow lane: forward state plus settlement queue."),
        Item(BASE / "paper_trade_settlement_helper.py", "Use after races settle to list open rows and enter one result safely."),
        Item(BASE / "phase7_current_paper_rules.json", "Current active paper basket: OP + CD, with dormant BEL removed."),
        Item(BASE / "phase8_shadow_rules.json", "Shadow-only watch basket. Log it, do not promote it by default."),
    ]

    decision_cards = [
        Item(BASE / "forward_evidence_scorecard.txt", "Fast rule ranking by forward evidence quality."),
        Item(BASE / "OP_FAMILY_DECISION.md", "Whether anything clearly beats OP_DURABLE_K7 as the safest OP anchor."),
        Item(BASE / "CROSS_FAMILY_DECISION.md", "Anchor / paper / watch roles for OP_DURABLE_K7, CD_CORE_K8, and OP_REFINED_K7."),
        Item(BASE / "PORTFOLIO_DECISION_CARD.md", "Phase 7 vs Phase 8 vs train-only selector at the portfolio level."),
        Item(BASE / "METHOD_FAMILY_DECISION.md", "Harville vs XGBoost vs selective rule path, for retiring dead-end method families."),
    ]

    after_settlement = [
        Item(BASE / "paper_trades" / "phase7_current_paper_paper_trade_settlements.csv", "Manual settlement ledger for the primary lane."),
        Item(BASE / "paper_trades" / "phase8_shadow_paper_trade_settlements.csv", "Manual settlement ledger for the shadow lane."),
        Item(BASE / "paper_trade_forward_check.py", "Conservative forward check against frozen holdout baselines."),
        Item(latest_primary_forward, "Detailed current primary forward-check artifact."),
        Item(latest_shadow_forward, "Detailed current shadow forward-check artifact."),
        Item(BASE / "paper_trade_lane_monitor.py", "Regenerate compact lane summaries after settlement updates."),
        Item(BASE / "paper_trade_next_steps.py", "Regenerate exact next-command guidance after settlement updates or manual checks."),
    ]

    benchmark_only = [
        Item(BASE / "WALK_FORWARD_VALIDATION.md", "Honest validation benchmark. Use for context, not as the daily operating recipe."),
        Item(BASE / "BACKTEST_REPORT.md", "Large-sample negative baseline for Harville / generic ML / broad structural strategies."),
        Item(BASE / "PHASE8_REPORT.md", "Research context only. Treat with skepticism when it conflicts with frozen holdout."),
        Item(BASE / "DIAGNOSE_CD_SELECTION.md", "Important selector diagnosis, but not part of the daily operating loop."),
        Item(BASE / "SELECTOR_EXPERIMENT.md", "Selector-tuning research context, not a daily-use artifact."),
        Item(BASE / "SAMPLE_SIZE_EXPERIMENT.md", "Follow-up selector experiment context, not a daily-use artifact."),
    ]

    do_not_drive_daily = [
        Item(BASE / "XGBoost", "Model research only. Do not treat this directory as a live decision surface."),
        Item(BASE / "phase7_live_rules.json", "Historical frozen ruleset that still includes dormant BEL. Reference only, not the cleanest live-paper entrypoint."),
        Item(BASE / "run_paper_trade_cycle.sh", "Useful one-basket wrapper, but the two-lane daily wrapper is the preferred routine now."),
        Item(BASE / "backtest_phase7_summary.csv", "Historical discovery output. Useful for research, not for daily deployment decisions."),
    ]

    lines = [
        "# Daily Artifact Guide",
        "",
        "This note separates **what Cole should actually use day to day** from the growing pile of benchmark and research artifacts.",
        "",
        "## Fast daily routine",
        "",
        "1. Run `./run_daily_portfolio_observation.sh`",
        "2. Read the latest `daily_summary.txt`, `preflight_note.txt`, and `OPS_HISTORY.md` when a quiet streak needs context",
        "3. Read `phase7_current_paper/next_steps.md` first, then `phase8_shadow/next_steps.md`",
        "4. Use the lane monitors only when you need more context on why those next steps were suggested",
        "5. If settlement rows are open, use `paper_trade_settlement_helper.py`",
        "6. Only then dip into the decision cards or benchmark reports",
        "",
        f"Latest detected daily run root: `{latest_label}`",
        "",
        "## Use every day",
        "",
        "| File | Status | Why it matters |",
        "|---|---|---|",
        *render_items(daily_use),
        "",
        "## Use after races settle",
        "",
        "| File | Status | Why it matters |",
        "|---|---|---|",
        *render_items(after_settlement),
        "",
        "## Read when making decisions, not every run",
        "",
        "| File | Status | Why it matters |",
        "|---|---|---|",
        *render_items(decision_cards),
        "",
        "## Benchmark / research context only",
        "",
        "| File | Status | Why it matters |",
        "|---|---|---|",
        *render_items(benchmark_only),
        "",
        "## Do not let these drive daily behavior",
        "",
        "| File | Status | Why it matters |",
        "|---|---|---|",
        *render_items(do_not_drive_daily),
        "",
        "## Bottom line",
        "",
        "- **Daily operating path**: read the preflight note, then Phase 7 current paper basket first, then Phase 8 shadow",
        "- **Safest anchor inside the live family**: `OP_DURABLE_K7`",
        "- **Paper alongside it**: `CD_CORE_K8`",
        "- **Do not drift back into generic Harville / XGBoost live claims** just because those artifacts are still in the repo",
        "",
    ]

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
