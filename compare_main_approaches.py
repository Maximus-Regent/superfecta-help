#!/usr/bin/env python3
"""
Fast honest comparison harness for the main superfecta approaches.

Purpose:
- Compare the current approaches without rerunning a wide search.
- Keep the comparison anchored to the frozen honest standard.
- Put 2024-2025 holdout, walk-forward context, and OP-focused options in one place.

Usage:
    python3 compare_main_approaches.py
    python3 compare_main_approaches.py --holdout-years 2024 2025

Outputs:
    - compare_main_approaches.csv
    - compare_main_approaches.md
"""

from __future__ import annotations

import argparse
import json
import time
from math import perm
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
CACHE_PATH = BASE / "phase5_race_cache.pkl"
PHASE7_RULES_PATH = BASE / "phase7_live_rules.json"
WF_FOLDS_PATH = BASE / "walk_forward_validation_folds.csv"
WF_RULES_PATH = BASE / "walk_forward_validation_rules.csv"

OUT_CSV = BASE / "compare_main_approaches.csv"
OUT_MD = BASE / "compare_main_approaches.md"

DEFAULT_HOLDOUT_YEARS = [2024, 2025]

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fast honest method comparison")
    parser.add_argument(
        "--holdout-years",
        nargs="+",
        type=int,
        default=DEFAULT_HOLDOUT_YEARS,
        help="Holdout years to emphasize in the comparison (default: 2024 2025)",
    )
    return parser.parse_args()


def load_cache() -> pd.DataFrame:
    df = pd.read_pickle(CACHE_PATH).copy()
    df["second_prob"] = df["fav_prob"] - df["prob_gap"]
    df["top2_mass"] = df["fav_prob"] + df["second_prob"]
    return df


def load_phase7_rules() -> list[dict]:
    payload = json.loads(PHASE7_RULES_PATH.read_text())
    rules: list[dict] = []
    for raw in payload["rules"]:
        rules.append(
            {
                "rule_id": raw["rule_id"],
                "track": raw["track"],
                "k": int(raw["k"]),
                "field_min": int(raw["field_min"]),
                "field_max": int(raw["field_max"]),
                "gap_min": float(raw["gap_min"]),
                "fav_prob_min": float(raw["fav_prob_min"]),
                "condition": raw["condition"],
                "card_min": int(raw["card_min"]),
                "months": [int(m) for m in raw.get("months", [])],
                "top2_mass_min": (
                    float(raw["top2_mass_min"]) if raw.get("top2_mass_min") is not None else None
                ),
            }
        )
    return rules


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
        mask &= np.isin(df["month"].to_numpy(dtype=np.int16), np.array(rule["months"], dtype=np.int16))

    if rule.get("top2_mass_min") is not None:
        mask &= df["top2_mass"].to_numpy(dtype=np.float64) >= float(rule["top2_mass_min"])

    return mask


def compile_rules(df: pd.DataFrame, rules: list[dict]) -> list[dict]:
    compiled: list[dict] = []
    for rule in rules:
        compiled.append(
            {
                "rule_id": rule["rule_id"],
                "mask": build_mask(df, rule),
                "hit": df[f"hit_{rule['k']}"] .to_numpy(dtype=bool),
                "cost": perm(rule["k"] - 1, 3),
            }
        )
    return compiled


def aggregate_year_rows(rows: list[dict]) -> dict:
    year_df = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
    races = int(year_df["races"].sum()) if not year_df.empty else 0
    hits = int(year_df["hits"].sum()) if not year_df.empty else 0
    wagered = float(year_df["wagered"].sum()) if not year_df.empty else 0.0
    returned = float(year_df["returned"].sum()) if not year_df.empty else 0.0
    profit = float(year_df["profit"].sum()) if not year_df.empty else 0.0
    roi = profit / wagered * 100.0 if wagered else 0.0

    observed = year_df[year_df["races"] > 0].copy() if not year_df.empty else year_df
    observed_years = int(len(observed))
    positive_years = int((observed["roi"] > 0).sum()) if observed_years else 0

    return {
        "year_df": year_df,
        "races": races,
        "hits": hits,
        "wagered": round(wagered, 2),
        "returned": round(returned, 2),
        "profit": round(profit, 2),
        "roi": round(roi, 2),
        "hit_rate": round(hits / races * 100.0, 2) if races else 0.0,
        "positive_years": positive_years,
        "observed_years": observed_years,
    }


def evaluate_fixed_method(df: pd.DataFrame, rules: list[dict], years: list[int]) -> dict:
    compiled = compile_rules(df, rules)
    payout = df["payout"].to_numpy(dtype=np.float64)
    year_arr = df["year"].to_numpy(dtype=np.int16)

    rows: list[dict] = []
    for year in years:
        year_mask = year_arr == year
        total_races = 0
        total_hits = 0
        total_wagered = 0.0
        total_returned = 0.0

        for item in compiled:
            mask = item["mask"] & year_mask
            races = int(mask.sum())
            hits = int((mask & item["hit"]).sum())
            wagered = races * item["cost"]
            returned = float(payout[mask & item["hit"]].sum())
            total_races += races
            total_hits += hits
            total_wagered += wagered
            total_returned += returned

        profit = total_returned - total_wagered
        roi = profit / total_wagered * 100.0 if total_wagered else 0.0
        rows.append(
            {
                "year": int(year),
                "races": total_races,
                "hits": total_hits,
                "wagered": round(total_wagered, 2),
                "returned": round(total_returned, 2),
                "profit": round(profit, 2),
                "roi": round(roi, 2),
            }
        )

    return aggregate_year_rows(rows)


def dynamic_rows_from_folds(folds: pd.DataFrame) -> dict:
    rows = []
    for _, row in folds.sort_values("test_year").iterrows():
        rows.append(
            {
                "year": int(row["test_year"]),
                "races": int(row["test_races"]),
                "hits": int(row["test_hits"]),
                "wagered": float(row["test_wagered"]),
                "returned": round(float(row["test_wagered"]) + float(row["test_profit"]), 2),
                "profit": float(row["test_profit"]),
                "roi": float(row["test_roi"]),
            }
        )
    return aggregate_year_rows(rows)


def dynamic_op_switch_rows(rule_df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    op_rows = rule_df[rule_df["rule_id"].isin(["OP_DURABLE_K7", "OP_REFINED_K7"])].copy()
    chosen_rows: list[pd.Series] = []

    for _, group in op_rows.groupby("test_year"):
        eligible = group[group["qualifies"] == True].copy()  # noqa: E712
        pool = eligible if not eligible.empty else group
        chosen = pool.sort_values(
            ["selection_score", "train_races", "train_roi", "rule_id"],
            ascending=[False, False, False, True],
        ).iloc[0]
        chosen_rows.append(chosen)

    chosen_df = pd.DataFrame(chosen_rows).sort_values("test_year").reset_index(drop=True)
    rows = []
    for _, row in chosen_df.iterrows():
        rows.append(
            {
                "year": int(row["test_year"]),
                "races": int(row["test_races"]),
                "hits": int(row["test_hits"]),
                "wagered": float(row["test_wagered"]),
                "returned": round(float(row["test_wagered"]) + float(row["test_profit"]), 2),
                "profit": float(row["test_profit"]),
                "roi": float(row["test_roi"]),
            }
        )

    return aggregate_year_rows(rows), chosen_df


def conservative_score(row: pd.Series, max_holdout_races: int) -> float:
    def roi_score(value: float) -> float:
        capped = float(np.clip(value, -50, 75))
        return (capped + 50.0) / 125.0 * 100.0

    holdout_year_score = (
        row["holdout_positive_years"] / row["holdout_observed_years"] * 100.0
        if row["holdout_observed_years"]
        else 0.0
    )
    wf_year_score = (
        row["wf_positive_years"] / row["wf_observed_years"] * 100.0
        if row["wf_observed_years"]
        else 0.0
    )
    size_score = (
        np.log1p(row["holdout_races"]) / np.log1p(max_holdout_races) * 100.0
        if row["holdout_races"] > 0 and max_holdout_races > 0
        else 0.0
    )

    score = (
        0.35 * holdout_year_score
        + 0.25 * size_score
        + 0.20 * roi_score(row["holdout_roi"])
        + 0.10 * roi_score(row["wf_roi"])
        + 0.10 * wf_year_score
    )
    return round(float(score), 1)


def fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"


def fmt_money(value: float) -> str:
    return f"${value:,.2f}"


def build_report(df: pd.DataFrame, holdout_years: list[int], wf_years: list[int], runtime_sec: float) -> str:
    ranked = df.sort_values(["rank"]).reset_index(drop=True)
    holdout_label = f"{min(holdout_years)}-{max(holdout_years)}"
    wf_label = f"{min(wf_years)}-{max(wf_years)}"

    lines = [
        "# Main Approach Comparison",
        "",
        "## Usage",
        "",
        "```bash",
        "python3 compare_main_approaches.py",
        "```",
        "",
        "This is a fast comparison harness. It replays a small fixed set of methods and reads the existing walk-forward artifacts. It does not run a new broad search.",
        "",
        "## Scope",
        "",
        f"- Holdout focus: {holdout_label}",
        f"- Walk-forward context: next-year tests across {wf_label}, excluding 2021 because the project data excludes that year",
        "- No new BEL->BAQ aliasing is introduced here",
        "- Conservative score weights holdout consistency and holdout sample size more than flashy ROI",
        "",
        "## Comparison Table",
        "",
        "| Rank | Method | Type | Holdout ROI | Holdout Races | Holdout Years+ | WF ROI | WF Races | WF Years+ | Score | Note |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for _, row in ranked.iterrows():
        lines.append(
            f"| {int(row['rank'])} | {row['label']} | {row['method_type']} | "
            f"{fmt_pct(row['holdout_roi'])} | {int(row['holdout_races'])} | "
            f"{int(row['holdout_positive_years'])}/{int(row['holdout_observed_years'])} | "
            f"{fmt_pct(row['wf_roi'])} | {int(row['wf_races'])} | "
            f"{int(row['wf_positive_years'])}/{int(row['wf_observed_years'])} | "
            f"{row['score']:.1f} | {row['note']} |"
        )

    best_large = ranked.sort_values(
        ["holdout_observed_years", "holdout_positive_years", "holdout_races", "holdout_roi"],
        ascending=[False, False, False, False],
    ).iloc[0]
    op_only = ranked[ranked["op_focus"] == True].copy()  # noqa: E712
    top_op = op_only.sort_values(["rank", "holdout_races"], ascending=[True, False]).iloc[0]
    selector = ranked[ranked["method_id"] == "train_only_selector"].iloc[0]

    lines.extend(
        [
            "",
            "## Fast Takeaways",
            "",
            f"- Large-sample holdout baseline: **{best_large['label']}** at {fmt_pct(best_large['holdout_roi'])} on {int(best_large['holdout_races'])} holdout races.",
            f"- Best OP-focused line in this table: **{top_op['label']}** at {fmt_pct(top_op['holdout_roi'])} on {int(top_op['holdout_races'])} holdout races. That is better ROI, but on a smaller sample than the large-sample baseline.",
            f"- Honest selector baseline: **{selector['label']}** stays useful context at {fmt_pct(selector['wf_roi'])} across {int(selector['wf_races'])} walk-forward races, but its {holdout_label} holdout is only {fmt_pct(selector['holdout_roi'])} on {int(selector['holdout_races'])} races.",
            "- Practical read: keep the comparison anchored to the big holdout baselines first, then use the OP-focused methods as narrower follow-ups rather than automatic upgrades.",
            "",
            "## Method Notes",
            "",
        ]
    )

    for _, row in ranked.iterrows():
        lines.append(f"- **{row['label']}**: {row['note']}")

    lines.extend(
        [
            "",
            "## Validation",
            "",
            f"- Runtime: {runtime_sec:.2f} seconds",
            f"- Data sources: `{CACHE_PATH.name}`, `{PHASE7_RULES_PATH.name}`, `{WF_FOLDS_PATH.name}`, `{WF_RULES_PATH.name}`",
            f"- Wrote: `{OUT_CSV.name}`, `{OUT_MD.name}`",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    start = time.perf_counter()
    args = parse_args()
    holdout_years = sorted(set(args.holdout_years))

    folds = pd.read_csv(WF_FOLDS_PATH)
    rule_df = pd.read_csv(WF_RULES_PATH)
    wf_years = sorted(int(y) for y in folds["test_year"].tolist())

    df = load_cache()
    phase7_rules = load_phase7_rules()

    methods: list[dict] = []

    fixed_specs = [
        {
            "method_id": "phase7_live_portfolio",
            "label": "Phase 7 live portfolio",
            "method_type": "fixed portfolio",
            "rules": phase7_rules,
            "op_focus": False,
            "note": "Frozen 3-rule baseline. BEL contributes zero 2024-2025 races, so the current holdout is effectively the OP+CD legs.",
        },
        {
            "method_id": "phase8_frozen_portfolio",
            "label": "Phase 8 frozen portfolio",
            "method_type": "fixed portfolio",
            "rules": PHASE8_FROZEN_RULES,
            "op_focus": False,
            "note": "Frozen 7-rule Phase 8 basket. Useful as the headline multi-track challenger, but still full-history-mined before this replay.",
        },
        {
            "method_id": "op_durable_only",
            "label": "OP durable only",
            "method_type": "fixed OP rule",
            "rules": [r for r in phase7_rules if r["rule_id"] == "OP_DURABLE_K7"],
            "op_focus": True,
            "note": "Largest-sample OP anchor. Lower upside than the refined OP variant, but materially more forward races.",
        },
        {
            "method_id": "op_refined_only",
            "label": "OP refined only",
            "method_type": "fixed OP rule",
            "rules": [r for r in PHASE8_FROZEN_RULES if r["rule_id"] == "OP_REFINED_K7"],
            "op_focus": True,
            "note": "Higher-ROI OP variant with a much smaller forward sample. Treat as selective, not as the new default.",
        },
    ]

    for spec in fixed_specs:
        wf_stats = evaluate_fixed_method(df, spec["rules"], wf_years)
        holdout_stats = evaluate_fixed_method(df, spec["rules"], holdout_years)
        methods.append(
            {
                "method_id": spec["method_id"],
                "label": spec["label"],
                "method_type": spec["method_type"],
                "op_focus": spec["op_focus"],
                "note": spec["note"],
                "wf_races": wf_stats["races"],
                "wf_hits": wf_stats["hits"],
                "wf_wagered": wf_stats["wagered"],
                "wf_profit": wf_stats["profit"],
                "wf_roi": wf_stats["roi"],
                "wf_hit_rate": wf_stats["hit_rate"],
                "wf_positive_years": wf_stats["positive_years"],
                "wf_observed_years": wf_stats["observed_years"],
                "holdout_races": holdout_stats["races"],
                "holdout_hits": holdout_stats["hits"],
                "holdout_wagered": holdout_stats["wagered"],
                "holdout_profit": holdout_stats["profit"],
                "holdout_roi": holdout_stats["roi"],
                "holdout_hit_rate": holdout_stats["hit_rate"],
                "holdout_positive_years": holdout_stats["positive_years"],
                "holdout_observed_years": holdout_stats["observed_years"],
            }
        )

    selector_wf = dynamic_rows_from_folds(folds[folds["test_year"].isin(wf_years)])
    selector_holdout = dynamic_rows_from_folds(folds[folds["test_year"].isin(holdout_years)])
    methods.append(
        {
            "method_id": "train_only_selector",
            "label": "Train-only yearly selector",
            "method_type": "dynamic selector",
            "op_focus": False,
            "note": "The current honest selector baseline from walk_forward_validation.py. Historical context includes the pre-existing BEL bridge candidate in some earlier folds, but no new aliasing is added here.",
            "wf_races": selector_wf["races"],
            "wf_hits": selector_wf["hits"],
            "wf_wagered": selector_wf["wagered"],
            "wf_profit": selector_wf["profit"],
            "wf_roi": selector_wf["roi"],
            "wf_hit_rate": selector_wf["hit_rate"],
            "wf_positive_years": selector_wf["positive_years"],
            "wf_observed_years": selector_wf["observed_years"],
            "holdout_races": selector_holdout["races"],
            "holdout_hits": selector_holdout["hits"],
            "holdout_wagered": selector_holdout["wagered"],
            "holdout_profit": selector_holdout["profit"],
            "holdout_roi": selector_holdout["roi"],
            "holdout_hit_rate": selector_holdout["hit_rate"],
            "holdout_positive_years": selector_holdout["positive_years"],
            "holdout_observed_years": selector_holdout["observed_years"],
        }
    )

    op_switch_wf, op_switch_choices = dynamic_op_switch_rows(rule_df[rule_df["test_year"].isin(wf_years)])
    op_switch_holdout, _ = dynamic_op_switch_rows(rule_df[rule_df["test_year"].isin(holdout_years)])
    switch_pairs = ", ".join(
        f"{int(row.test_year)}={row.rule_id}" for _, row in op_switch_choices.tail(min(4, len(op_switch_choices))).iterrows()
    )
    methods.append(
        {
            "method_id": "op_train_switch",
            "label": "OP train-score switch",
            "method_type": "dynamic OP selector",
            "op_focus": True,
            "note": f"Each year, pick the better-qualifying OP rule by train-only selection score. Recent picks: {switch_pairs}.",
            "wf_races": op_switch_wf["races"],
            "wf_hits": op_switch_wf["hits"],
            "wf_wagered": op_switch_wf["wagered"],
            "wf_profit": op_switch_wf["profit"],
            "wf_roi": op_switch_wf["roi"],
            "wf_hit_rate": op_switch_wf["hit_rate"],
            "wf_positive_years": op_switch_wf["positive_years"],
            "wf_observed_years": op_switch_wf["observed_years"],
            "holdout_races": op_switch_holdout["races"],
            "holdout_hits": op_switch_holdout["hits"],
            "holdout_wagered": op_switch_holdout["wagered"],
            "holdout_profit": op_switch_holdout["profit"],
            "holdout_roi": op_switch_holdout["roi"],
            "holdout_hit_rate": op_switch_holdout["hit_rate"],
            "holdout_positive_years": op_switch_holdout["positive_years"],
            "holdout_observed_years": op_switch_holdout["observed_years"],
        }
    )

    out_df = pd.DataFrame(methods)
    max_holdout_races = int(out_df["holdout_races"].max()) if not out_df.empty else 0
    out_df["score"] = out_df.apply(lambda row: conservative_score(row, max_holdout_races), axis=1)
    out_df = out_df.sort_values(
        ["score", "holdout_positive_years", "holdout_races", "holdout_roi", "wf_races"],
        ascending=[False, False, False, False, False],
    ).reset_index(drop=True)
    out_df.index = out_df.index + 1
    out_df.index.name = "rank"
    out_df = out_df.reset_index()

    runtime_sec = time.perf_counter() - start
    report = build_report(out_df, holdout_years, wf_years, runtime_sec)

    out_df.to_csv(OUT_CSV, index=False)
    OUT_MD.write_text(report + "\n", encoding="utf-8")

    print(report)
    print(f"Saved: {OUT_CSV.name}")
    print(f"Saved: {OUT_MD.name}")


if __name__ == "__main__":
    main()
