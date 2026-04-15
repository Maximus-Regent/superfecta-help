#!/usr/bin/env python3
"""
Evaluate frozen superfecta portfolios on chronological holdouts.

Why this exists:
- The old residual-model script used a shuffled train/test split.
- Later rule-search phases used temporal splits, but portfolio selection was still
  mostly judged on full-history summaries.
- This script evaluates already-defined rule sets as frozen portfolios on later years,
  which is closer to how they would behave in deployment.

Outputs:
- frozen_portfolio_eval_summary.csv
- frozen_portfolio_eval_yearly.csv
- FROZEN_PORTFOLIO_EVAL.md
"""

from __future__ import annotations

import json
from math import perm
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path("/Users/maximusregent_ai/Shared/Superfecta Help")
CACHE_PATH = BASE / "phase5_race_cache.pkl"
PHASE7_RULES_PATH = BASE / "phase7_live_rules.json"
OUT_SUMMARY = BASE / "frozen_portfolio_eval_summary.csv"
OUT_YEARLY = BASE / "frozen_portfolio_eval_yearly.csv"
OUT_REPORT = BASE / "FROZEN_PORTFOLIO_EVAL.md"

HOLDOUT_YEARS = [2024, 2025]
TRAIN_END_YEAR = 2023

PHASE8_FROZEN_RULES = [
    {
        "rule_id": "BEL_BROAD1_K7",
        "track": "BEL",
        "k": 7,
        "field_min": 11,
        "field_max": 13,
        "gap_min": 0.22,
        "fav_prob_min": 0.35,
        "condition": "fast",
        "card_min": 5,
    },
    {
        "rule_id": "OP_REFINED_K7",
        "track": "OP",
        "k": 7,
        "field_min": 11,
        "field_max": 12,
        "gap_min": 0.05,
        "fav_prob_min": 0.25,
        "condition": "all",
        "card_min": 9,
    },
    {
        "rule_id": "AQU_K9",
        "track": "AQU",
        "k": 9,
        "field_min": 10,
        "field_max": 11,
        "gap_min": 0.22,
        "fav_prob_min": 0.0,
        "condition": "all",
        "card_min": 9,
    },
    {
        "rule_id": "SA_K9",
        "track": "SA",
        "k": 9,
        "field_min": 11,
        "field_max": 12,
        "gap_min": 0.20,
        "fav_prob_min": 0.0,
        "condition": "fast",
        "card_min": 9,
    },
    {
        "rule_id": "KEE_K9",
        "track": "KEE",
        "k": 9,
        "field_min": 12,
        "field_max": 14,
        "gap_min": 0.05,
        "fav_prob_min": 0.35,
        "condition": "fast",
        "card_min": 1,
    },
    {
        "rule_id": "CD_REFINED_K9",
        "track": "CD",
        "k": 9,
        "field_min": 11,
        "field_max": 12,
        "gap_min": 0.0,
        "fav_prob_min": 0.30,
        "condition": "all",
        "card_min": 7,
        "top2_mass_min": 0.55,
    },
    {
        "rule_id": "DMR_FALL_K7",
        "track": "DMR",
        "k": 7,
        "field_min": 10,
        "field_max": 11,
        "gap_min": 0.10,
        "fav_prob_min": 0.0,
        "condition": "all",
        "card_min": 5,
        "months": [9, 10, 11],
    },
]


def load_data() -> pd.DataFrame:
    df = pd.read_pickle(CACHE_PATH).copy()
    df["second_prob"] = df["fav_prob"] - df["prob_gap"]
    df["top2_mass"] = df["fav_prob"] + df["second_prob"]
    return df


def normalize_phase7_rule(rule: dict) -> dict:
    return {
        "rule_id": rule["rule_id"],
        "track": rule["track"],
        "k": int(rule["k"]),
        "field_min": int(rule["field_min"]),
        "field_max": int(rule["field_max"]),
        "gap_min": float(rule["gap_min"]),
        "fav_prob_min": float(rule["fav_prob_min"]),
        "condition": rule["condition"],
        "card_min": int(rule["card_min"]),
    }


def build_mask(df: pd.DataFrame, rule: dict) -> np.ndarray:
    mask = (df["track"].to_numpy() == rule["track"])
    mask &= df[f"eligible_{rule['k']}"] .to_numpy(dtype=bool)
    fs = df["fs"].to_numpy(dtype=np.int16)
    mask &= (fs >= rule["field_min"]) & (fs <= rule["field_max"])
    mask &= df["prob_gap"].to_numpy(dtype=np.float64) >= rule["gap_min"]
    mask &= df["fav_prob"].to_numpy(dtype=np.float64) >= rule["fav_prob_min"]

    if rule["condition"] == "fast":
        mask &= df["is_fast"].to_numpy(dtype=bool)

    mask &= df["rnum"].to_numpy(dtype=np.int16) >= rule["card_min"]

    if rule.get("months"):
        mask &= np.isin(df["month"].to_numpy(dtype=np.int16), rule["months"])

    if rule.get("top2_mass_min") is not None:
        mask &= df["top2_mass"].to_numpy(dtype=np.float64) >= float(rule["top2_mass_min"])

    return mask


def evaluate_mask(mask: np.ndarray, hit: np.ndarray, payout: np.ndarray, cost: int) -> dict:
    n = int(mask.sum())
    if n == 0:
        return {
            "races": 0,
            "hits": 0,
            "wagered": 0,
            "returned": 0.0,
            "profit": 0.0,
            "roi": 0.0,
            "hit_rate": 0.0,
        }

    h = mask & hit
    hits = int(h.sum())
    wagered = n * cost
    returned = float(payout[h].sum())
    profit = returned - wagered
    roi = profit / wagered * 100.0 if wagered else 0.0
    hit_rate = hits / n * 100.0
    return {
        "races": n,
        "hits": hits,
        "wagered": wagered,
        "returned": round(returned, 2),
        "profit": round(profit, 2),
        "roi": round(roi, 2),
        "hit_rate": round(hit_rate, 2),
    }


def evaluate_portfolio(df: pd.DataFrame, portfolio_name: str, rules: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    payout = df["payout"].to_numpy(dtype=np.float64)
    year_arr = df["year"].to_numpy(dtype=np.int16)

    summary_rows: list[dict] = []
    yearly_rows: list[dict] = []

    compiled = []
    for rule in rules:
        mask = build_mask(df, rule)
        hit = df[f"hit_{rule['k']}"] .to_numpy(dtype=bool)
        cost = perm(rule["k"] - 1, 3)
        compiled.append({"rule": rule, "mask": mask, "hit": hit, "cost": cost})

    slices = {
        "full": None,
        f"train_2010_{TRAIN_END_YEAR}": year_arr <= TRAIN_END_YEAR,
        f"holdout_{HOLDOUT_YEARS[0]}_{HOLDOUT_YEARS[-1]}": np.isin(year_arr, HOLDOUT_YEARS),
    }
    for y in HOLDOUT_YEARS:
        slices[f"year_{y}"] = year_arr == y

    for item in compiled:
        rule = item["rule"]
        for slice_name, year_mask in slices.items():
            mask = item["mask"] if year_mask is None else (item["mask"] & year_mask)
            stats = evaluate_mask(mask, item["hit"], payout, item["cost"])
            summary_rows.append({
                "portfolio": portfolio_name,
                "level": "rule",
                "name": rule["rule_id"],
                "slice": slice_name,
                "cost_per_race": item["cost"],
                **stats,
            })

    for slice_name, year_mask in slices.items():
        total_wagered = 0
        total_returned = 0.0
        total_hits = 0
        total_races = 0
        for item in compiled:
            mask = item["mask"] if year_mask is None else (item["mask"] & year_mask)
            stats = evaluate_mask(mask, item["hit"], payout, item["cost"])
            total_wagered += stats["wagered"]
            total_returned += stats["returned"]
            total_hits += stats["hits"]
            total_races += stats["races"]
        profit = total_returned - total_wagered
        roi = profit / total_wagered * 100.0 if total_wagered else 0.0
        hit_rate = total_hits / total_races * 100.0 if total_races else 0.0
        summary_rows.append({
            "portfolio": portfolio_name,
            "level": "portfolio",
            "name": portfolio_name,
            "slice": slice_name,
            "cost_per_race": np.nan,
            "races": total_races,
            "hits": total_hits,
            "wagered": total_wagered,
            "returned": round(total_returned, 2),
            "profit": round(profit, 2),
            "roi": round(roi, 2),
            "hit_rate": round(hit_rate, 2),
        })

    for y in sorted(df["year"].unique()):
        total_wagered = 0
        total_returned = 0.0
        total_hits = 0
        total_races = 0
        for item in compiled:
            mask = item["mask"] & (year_arr == y)
            stats = evaluate_mask(mask, item["hit"], payout, item["cost"])
            total_wagered += stats["wagered"]
            total_returned += stats["returned"]
            total_hits += stats["hits"]
            total_races += stats["races"]
        profit = total_returned - total_wagered
        roi = profit / total_wagered * 100.0 if total_wagered else 0.0
        hit_rate = total_hits / total_races * 100.0 if total_races else 0.0
        yearly_rows.append({
            "portfolio": portfolio_name,
            "year": int(y),
            "races": total_races,
            "hits": total_hits,
            "wagered": total_wagered,
            "returned": round(total_returned, 2),
            "profit": round(profit, 2),
            "roi": round(roi, 2),
            "hit_rate": round(hit_rate, 2),
        })

    return pd.DataFrame(summary_rows), pd.DataFrame(yearly_rows)


def build_report(summary_df: pd.DataFrame, yearly_df: pd.DataFrame) -> str:
    def row(portfolio: str, slice_name: str) -> pd.Series:
        return summary_df[
            (summary_df["portfolio"] == portfolio)
            & (summary_df["level"] == "portfolio")
            & (summary_df["slice"] == slice_name)
        ].iloc[0]

    p7_hold = row("phase7_live", f"holdout_{HOLDOUT_YEARS[0]}_{HOLDOUT_YEARS[-1]}")
    p8_hold = row("phase8_frozen", f"holdout_{HOLDOUT_YEARS[0]}_{HOLDOUT_YEARS[-1]}")
    p7_train = row("phase7_live", f"train_2010_{TRAIN_END_YEAR}")
    p8_train = row("phase8_frozen", f"train_2010_{TRAIN_END_YEAR}")
    p7_full = row("phase7_live", "full")
    p8_full = row("phase8_frozen", "full")

    lines = [
        "# Frozen Portfolio Evaluation",
        "",
        "This report evaluates already-defined rule portfolios on a later chronological holdout, using the cached major-track race-level dataset.",
        "",
        "## Why this matters",
        "",
        "- The old residual-model script (`XGBoost/train_test_residual.py`) uses `train_test_split(..., test_size=0.25, shuffle=True)`, which is a random 75/25 split and not deployment-realistic.",
        f"- This report instead checks frozen portfolios on **train = 2010-{TRAIN_END_YEAR}** and **holdout = {HOLDOUT_YEARS[0]}-{HOLDOUT_YEARS[-1]}**.",
        "- This is still not a perfect no-lookahead rule-discovery test, because the rule sets themselves were originally discovered from historical research, but it is materially closer to live deployment than shuffled splits.",
        "",
        "## Portfolio Summary",
        "",
        "| Portfolio | Full ROI | Train ROI | Holdout ROI | Holdout Profit | Holdout Races | Holdout Hit Rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Phase 7 live rules | {p7_full['roi']:+.2f}% | {p7_train['roi']:+.2f}% | {p7_hold['roi']:+.2f}% | ${p7_hold['profit']:,.2f} | {int(p7_hold['races'])} | {p7_hold['hit_rate']:.2f}% |",
        f"| Phase 8 frozen rules | {p8_full['roi']:+.2f}% | {p8_train['roi']:+.2f}% | {p8_hold['roi']:+.2f}% | ${p8_hold['profit']:,.2f} | {int(p8_hold['races'])} | {p8_hold['hit_rate']:.2f}% |",
        "",
        "## Holdout by Year",
        "",
    ]

    for portfolio in ["phase7_live", "phase8_frozen"]:
        lines.append(f"### {portfolio}")
        lines.append("")
        lines.append("| Year | Races | Wagered | Profit | ROI | Hit Rate |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        sub = yearly_df[(yearly_df["portfolio"] == portfolio) & (yearly_df["year"].isin(HOLDOUT_YEARS))]
        for _, r in sub.iterrows():
            lines.append(
                f"| {int(r['year'])} | {int(r['races'])} | ${r['wagered']:,.0f} | ${r['profit']:,.2f} | {r['roi']:+.2f}% | {r['hit_rate']:.2f}% |"
            )
        lines.append("")

    lines.extend([
        "## Interpretation",
        "",
        f"- The **Phase 7 live portfolio** held up best on the later holdout: **{p7_hold['roi']:+.2f}% ROI** on {int(p7_hold['races'])} races, for **${p7_hold['profit']:,.2f}** profit.",
        f"- The **Phase 8 frozen portfolio** also stayed positive on the holdout: **{p8_hold['roi']:+.2f}% ROI** on {int(p8_hold['races'])} races, for **${p8_hold['profit']:,.2f}** profit.",
        "- The BEL rule has **0 holdout races** in 2024-2025 because the later data uses `BAQ` instead of `BEL`, and the current live-rule mapping explicitly avoids unsupported aliasing.",
        "- That is much more encouraging than the old shuffled ML split, because this test preserves chronology and reports actual betting P&L.",
        "- The main thing still missing is a truly clean no-lookahead discovery loop where rules are searched only on prior years, frozen, then tested on the next period.",
        "",
        "## Recommended next evaluation loop",
        "",
        "1. Freeze a candidate search space before looking at the test window.",
        f"2. Use an expanding yearly walk-forward: train on 2010..Y-1, select rules on train only, test on year Y.",
        "3. Track portfolio-level ROI, profit, races, hit rate, and per-year profitability, not just model R² or full-sample ROI.",
        "4. Keep the most recent 12-24 months as a final untouched holdout until the selection logic is frozen.",
        "5. Promote only rules that survive both train-only selection and frozen-holdout evaluation, then paper trade them live.",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    df = load_data()

    with PHASE7_RULES_PATH.open() as f:
        phase7_rules = [normalize_phase7_rule(r) for r in json.load(f)["rules"]]

    phase7_summary, phase7_yearly = evaluate_portfolio(df, "phase7_live", phase7_rules)
    phase8_summary, phase8_yearly = evaluate_portfolio(df, "phase8_frozen", PHASE8_FROZEN_RULES)

    summary_df = pd.concat([phase7_summary, phase8_summary], ignore_index=True)
    yearly_df = pd.concat([phase7_yearly, phase8_yearly], ignore_index=True)

    summary_df.to_csv(OUT_SUMMARY, index=False)
    yearly_df.to_csv(OUT_YEARLY, index=False)
    OUT_REPORT.write_text(build_report(summary_df, yearly_df))

    print("Saved:")
    print(f"  {OUT_SUMMARY.name}")
    print(f"  {OUT_YEARLY.name}")
    print(f"  {OUT_REPORT.name}")

    hold_slice = f"holdout_{HOLDOUT_YEARS[0]}_{HOLDOUT_YEARS[-1]}"
    for portfolio in ["phase7_live", "phase8_frozen"]:
        row = summary_df[
            (summary_df["portfolio"] == portfolio)
            & (summary_df["level"] == "portfolio")
            & (summary_df["slice"] == hold_slice)
        ].iloc[0]
        print(
            f"{portfolio}: holdout ROI {row['roi']:+.2f}% | "
            f"profit ${row['profit']:,.2f} | races {int(row['races'])}"
        )


if __name__ == "__main__":
    main()
