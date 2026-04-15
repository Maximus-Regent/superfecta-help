#!/usr/bin/env python3
"""
Forward Evidence Scorecard — ranks rules by holdout & walk-forward quality.

This script reads existing evaluation artifacts and produces a single ranked
view that answers: "Which rules should I actually trust going forward?"

Rules are ranked by forward evidence, then assigned a conservative deployment
bucket so small-sample Phase 8 variants do not outrank the safer OP anchor.

Usage:
    python forward_evidence_scorecard.py

Outputs:
    - Ranked table to stdout
    - forward_evidence_scorecard.txt
    - forward_evidence_scorecard.csv
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent

FROZEN_SUMMARY = BASE / "frozen_portfolio_eval_summary.csv"
WF_FOLDS = BASE / "walk_forward_validation_folds.csv"
TXT_OUTPUT = BASE / "forward_evidence_scorecard.txt"
CSV_OUTPUT = BASE / "forward_evidence_scorecard.csv"


# Phase 8 report bootstrap CIs (lower bound) — hardcoded from report text
# because these aren't stored in the CSV artifacts.
BOOTSTRAP_CI_LOWER: dict[str, float] = {
    "BEL_BROAD1_K7": 44.4,
    "OP_DURABLE_K7": -3.4,
    "OP_REFINED_K7": 11.2,
    "AQU_K9": 3.1,
    "SA_K9": -6.3,
    "KEE_K9": -3.0,
    "CD_CORE_K8": -15.0,
    "CD_REFINED_K9": -26.4,
    "DMR_FALL_K7": -28.8,
}

FULL_SAMPLE_ROI: dict[str, float] = {
    "BEL_BROAD1_K7": 134.9,
    "OP_DURABLE_K7": 35.0,
    "OP_REFINED_K7": 50.0,
    "AQU_K9": 50.2,
    "SA_K9": 25.9,
    "KEE_K9": 30.8,
    "CD_CORE_K8": 13.1,
    "CD_REFINED_K9": 57.0,
    "DMR_FALL_K7": 14.4,
}

FULL_SAMPLE_RACES: dict[str, int] = {
    "BEL_BROAD1_K7": 85,
    "OP_DURABLE_K7": 505,
    "OP_REFINED_K7": 267,
    "AQU_K9": 64,
    "SA_K9": 64,
    "KEE_K9": 111,
    "CD_CORE_K8": 485,
    "CD_REFINED_K9": 151,
    "DMR_FALL_K7": 145,
}

PHASE_ORIGIN: dict[str, str] = {
    "BEL_BROAD1_K7": "P7",
    "OP_DURABLE_K7": "P7",
    "OP_REFINED_K7": "P8",
    "AQU_K9": "P8",
    "SA_K9": "P8",
    "KEE_K9": "P8",
    "CD_CORE_K8": "P7",
    "CD_REFINED_K9": "P8",
    "DMR_FALL_K7": "P8",
}

TIER_PRIORITY = {
    "ANCHOR": 5,
    "PAPER": 4,
    "WATCH": 3,
    "DORMANT": 2,
    "SKIP": 1,
    "NO_DATA": 0,
}


def load_holdout_by_rule() -> pd.DataFrame:
    df = pd.read_csv(FROZEN_SUMMARY)
    holdout = df[(df["slice"] == "holdout_2024_2025") & (df["level"] == "rule")].copy()
    holdout = holdout.rename(columns={
        "name": "rule_id",
        "roi": "holdout_roi",
        "races": "holdout_races",
        "profit": "holdout_profit",
        "hit_rate": "holdout_hit_rate",
    })
    return holdout[["rule_id", "holdout_roi", "holdout_races", "holdout_profit", "holdout_hit_rate"]].copy()


def load_holdout_year_stats() -> dict[str, dict[str, float | int]]:
    df = pd.read_csv(FROZEN_SUMMARY)
    years = df[(df["level"] == "rule") & (df["slice"].str.startswith("year_"))].copy()
    stats: dict[str, dict[str, float | int]] = {}
    for rule_id, grp in years.groupby("name"):
        observed = grp[grp["races"] > 0].copy()
        years_observed = int(len(observed))
        years_positive = int((observed["roi"] > 0).sum()) if years_observed else 0
        worst_year_roi = float(observed["roi"].min()) if years_observed else np.nan
        stats[str(rule_id)] = {
            "years_observed": years_observed,
            "years_positive": years_positive,
            "worst_year_roi": worst_year_roi,
        }
    return stats


def compute_wf_selection_freq() -> dict[str, tuple[int, int]]:
    df = pd.read_csv(WF_FOLDS)
    total_folds = len(df)
    freq: dict[str, int] = {}
    for rule_ids in df["selected_rule_ids"]:
        for rid in str(rule_ids).split(","):
            rid = rid.strip()
            if rid and not rid.endswith("_BRIDGE_BAQ"):
                freq[rid] = freq.get(rid, 0) + 1
    return {k: (v, total_folds) for k, v in freq.items()}


def forward_trust_score(
    holdout_roi: float,
    holdout_races: int,
    wf_frac: float,
    ci_lower: float,
    years_positive: int,
    years_observed: int,
) -> float:
    """Composite score for ordering within conservative tiers."""
    roi_clamped = np.clip(holdout_roi, -50, 75)
    roi_score = (roi_clamped + 50) / 125 * 100

    if holdout_races <= 0:
        size_score = 0.0
    else:
        size_score = min(np.log1p(holdout_races) / np.log1p(150) * 100, 100)

    wf_score = wf_frac * 100

    if ci_lower >= 10:
        ci_score = 100.0
    elif ci_lower >= 0:
        ci_score = 60.0 + ci_lower * 4
    elif ci_lower >= -20:
        ci_score = max(60.0 + ci_lower * 2.0, 0)
    else:
        ci_score = 0.0

    year_score = 0.0 if years_observed == 0 else (years_positive / years_observed) * 100

    return round(
        0.28 * roi_score
        + 0.32 * size_score
        + 0.20 * wf_score
        + 0.10 * ci_score
        + 0.10 * year_score,
        1,
    )


def recommendation_tier(
    rule_id: str,
    holdout_roi: float,
    holdout_races: int,
    wf_sel: int,
    ci_lower: float,
    years_positive: int,
    years_observed: int,
) -> str:
    if holdout_races == 0:
        return "DORMANT" if rule_id.startswith("BEL_") else "NO_DATA"
    if holdout_roi <= 0:
        return "SKIP"
    if holdout_races >= 100 and wf_sel >= 5 and ci_lower >= -5:
        return "ANCHOR"
    if (
        holdout_races >= 50
        and years_observed >= 2
        and years_positive == years_observed
        and wf_sel >= 1
        and ci_lower > -20
    ):
        return "PAPER"
    return "WATCH"


def note_for_rule(
    rule_id: str,
    tier: str,
    holdout_races: int,
    wf_sel: int,
    wf_total: int,
    ci_lower: float,
    years_positive: int,
    years_observed: int,
) -> str:
    notes: list[str] = []

    if tier == "ANCHOR":
        notes.append("best current OP anchor")
    elif tier == "PAPER":
        notes.append("positive holdout in both years")
    elif tier == "DORMANT":
        notes.append("no 2024-2025 forward races")
    elif tier == "SKIP":
        notes.append("negative holdout")

    if holdout_races and holdout_races < 50:
        notes.append(f"small holdout ({holdout_races})")
    if years_observed >= 2 and years_positive < years_observed:
        notes.append(f"mixed holdout years ({years_positive}/{years_observed})")
    if wf_sel <= 2 and wf_total:
        notes.append(f"low WF selection ({wf_sel}/{wf_total})")
    if ci_lower < 0:
        notes.append("CI crosses zero")
    if rule_id == "CD_CORE_K8" and tier == "PAPER":
        notes.append("CD family still variant-sensitive")

    seen: list[str] = []
    for note in notes:
        if note not in seen:
            seen.append(note)
    return "; ".join(seen[:3])


def build_scorecard() -> pd.DataFrame:
    holdout = load_holdout_by_rule().drop_duplicates(subset="rule_id", keep="first")
    year_stats = load_holdout_year_stats()
    wf_freq = compute_wf_selection_freq()

    rows = []
    for rule_id in sorted(FULL_SAMPLE_ROI.keys()):
        h = holdout[holdout["rule_id"] == rule_id]
        if len(h) > 0:
            h_roi = float(h.iloc[0]["holdout_roi"])
            h_races = int(h.iloc[0]["holdout_races"])
            h_profit = float(h.iloc[0]["holdout_profit"])
        else:
            h_roi, h_races, h_profit = 0.0, 0, 0.0

        wf_sel, wf_total = wf_freq.get(rule_id, (0, 10))
        wf_frac = wf_sel / wf_total if wf_total > 0 else 0.0
        ci_lower = BOOTSTRAP_CI_LOWER.get(rule_id, 0.0)
        stats = year_stats.get(rule_id, {})
        years_observed = int(stats.get("years_observed", 0))
        years_positive = int(stats.get("years_positive", 0))
        worst_year_roi = stats.get("worst_year_roi", np.nan)

        score = forward_trust_score(
            h_roi,
            h_races,
            wf_frac,
            ci_lower,
            years_positive,
            years_observed,
        )
        tier = recommendation_tier(
            rule_id,
            h_roi,
            h_races,
            wf_sel,
            ci_lower,
            years_positive,
            years_observed,
        )
        note = note_for_rule(
            rule_id,
            tier,
            h_races,
            wf_sel,
            wf_total,
            ci_lower,
            years_positive,
            years_observed,
        )

        rows.append({
            "rule_id": rule_id,
            "phase": PHASE_ORIGIN.get(rule_id, "?"),
            "backtest_roi": FULL_SAMPLE_ROI.get(rule_id, 0.0),
            "backtest_races": FULL_SAMPLE_RACES.get(rule_id, 0),
            "holdout_roi": h_roi,
            "holdout_races": h_races,
            "holdout_profit": h_profit,
            "holdout_years": f"{years_positive}/{years_observed}",
            "worst_year_roi": worst_year_roi,
            "wf_selected": f"{wf_sel}/{wf_total}",
            "wf_selected_count": wf_sel,
            "wf_total_folds": wf_total,
            "ci_lower": ci_lower,
            "forward_trust": score,
            "tier": tier,
            "note": note,
        })

    df = pd.DataFrame(rows)
    df["tier_priority"] = df["tier"].map(TIER_PRIORITY)
    df = df.sort_values(
        ["tier_priority", "forward_trust", "holdout_races", "holdout_roi"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    df.index = df.index + 1
    df.index.name = "rank"
    return df


def format_report(df: pd.DataFrame) -> str:
    lines = [
        "=" * 132,
        "FORWARD EVIDENCE SCORECARD",
        f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
        "Rules ranked by forward evidence quality, then bucketed conservatively for deployment.",
        "=" * 132,
        "",
    ]

    header = (
        f"{'Rank':<5} {'Rule':<22} {'Ph':<4} "
        f"{'HO ROI':>8} {'HO N':>6} {'Yrs+':>6} {'WF':>6} {'CI Lo':>7} {'Score':>7} {'Tier':<8} Note"
    )
    lines.append(header)
    lines.append("-" * len(header))

    for rank, row in df.iterrows():
        line = (
            f"{rank:<5} {row['rule_id']:<22} {row['phase']:<4} "
            f"{row['holdout_roi']:>+7.1f}% {row['holdout_races']:>5} "
            f"{row['holdout_years']:>6} {row['wf_selected']:>6} "
            f"{row['ci_lower']:>+6.1f}% {row['forward_trust']:>6.1f} "
            f"{row['tier']:<8} {row['note']}"
        )
        lines.append(line)

    lines.extend([
        "",
        "-" * 132,
        "LEGEND:",
        "  HO ROI / HO N = 2024-2025 holdout ROI and race count",
        "  Yrs+          = profitable holdout years / observed holdout years (2024, 2025)",
        "  WF            = walk-forward folds selected / total folds",
        "  CI Lo         = bootstrap 95% CI lower bound from report text",
        "  Score         = forward-trust ordering score, not an automatic deployment instruction",
        "  Tier          = ANCHOR (safest current live-paper anchor), PAPER (paper trade now),",
        "                  WATCH (shadow only / not enough evidence), DORMANT (no forward races), SKIP (negative holdout)",
        "",
        "KEY INSIGHT: OP_DURABLE_K7 is the safest anchor because it has the largest real holdout sample",
        "plus the strongest walk-forward selection frequency. Small-sample Phase 8 winners stay in WATCH until",
        "they earn more forward races.",
        "-" * 132,
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    df = build_scorecard()
    report = format_report(df)
    print(report)

    txt_df = df.drop(columns=["tier_priority"])
    TXT_OUTPUT.write_text(report + "\n", encoding="utf-8")
    txt_df.to_csv(CSV_OUTPUT, index_label="rank")

    print(f"\nSaved to: {TXT_OUTPUT}")
    print(f"Saved to: {CSV_OUTPUT}")
