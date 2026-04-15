#!/usr/bin/env python3
"""
OP family decision card.

Purpose:
- Compare the realistic OP candidates side by side.
- Keep OP_DURABLE_K7 as the default anchor unless a challenger clearly clears
  a conservative replacement bar.
- Produce a short report Cole can use without digging through multiple files.

Outputs:
- op_family_decision.csv
- OP_FAMILY_DECISION.md
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import compare_main_approaches as cma

BASE = Path(__file__).resolve().parent
OUT_CSV = BASE / "op_family_decision.csv"
OUT_MD = BASE / "OP_FAMILY_DECISION.md"


def fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"


def build_method_rows() -> list[dict]:
    df = cma.load_cache()
    phase7_rules = cma.load_phase7_rules()
    rule_df = pd.read_csv(cma.WF_RULES_PATH)

    holdout_years = sorted(set(cma.DEFAULT_HOLDOUT_YEARS))
    wf_years = sorted(int(y) for y in rule_df["test_year"].unique().tolist())

    durable_rules = [r for r in phase7_rules if r["rule_id"] == "OP_DURABLE_K7"]
    refined_rules = [r for r in cma.PHASE8_FROZEN_RULES if r["rule_id"] == "OP_REFINED_K7"]

    durable_wf = cma.evaluate_fixed_method(df, durable_rules, wf_years)
    durable_holdout = cma.evaluate_fixed_method(df, durable_rules, holdout_years)

    refined_wf = cma.evaluate_fixed_method(df, refined_rules, wf_years)
    refined_holdout = cma.evaluate_fixed_method(df, refined_rules, holdout_years)

    op_rules_df = rule_df[rule_df["test_year"].isin(wf_years)].copy()
    switch_wf, switch_choices = cma.dynamic_op_switch_rows(op_rules_df)
    switch_holdout, holdout_choices = cma.dynamic_op_switch_rows(
        rule_df[rule_df["test_year"].isin(holdout_years)].copy()
    )

    recent_switches = ", ".join(
        f"{int(row.test_year)}={row.rule_id}" for _, row in switch_choices.tail(min(4, len(switch_choices))).iterrows()
    )
    holdout_switches = ", ".join(
        f"{int(row.test_year)}={row.rule_id}" for _, row in holdout_choices.iterrows()
    )

    rows = [
        {
            "method_id": "op_durable_only",
            "label": "OP_DURABLE_K7",
            "method_type": "fixed anchor",
            "holdout": durable_holdout,
            "wf": durable_wf,
            "note": "Largest-sample OP path. This is the safest current live-paper anchor.",
        },
        {
            "method_id": "op_refined_only",
            "label": "OP_REFINED_K7",
            "method_type": "fixed challenger",
            "holdout": refined_holdout,
            "wf": refined_wf,
            "note": "Higher ROI, but on much smaller forward samples and with mixed 2024/2025 behavior.",
        },
        {
            "method_id": "op_train_switch",
            "label": "Train-only OP switch",
            "method_type": "dynamic challenger",
            "holdout": switch_holdout,
            "wf": switch_wf,
            "note": f"Train-only yearly selector across the two OP rules. Holdout choices: {holdout_switches}. Recent WF picks: {recent_switches}.",
        },
    ]
    return rows


def worst_year(stats: dict) -> float:
    year_df = stats["year_df"]
    observed = year_df[year_df["races"] > 0].copy()
    if observed.empty:
        return 0.0
    return round(float(observed["roi"].min()), 2)


def build_dataframe() -> pd.DataFrame:
    rows = build_method_rows()
    anchor = next(row for row in rows if row["method_id"] == "op_durable_only")

    out_rows = []
    for row in rows:
        holdout = row["holdout"]
        wf = row["wf"]

        holdout_roi = float(holdout["roi"])
        holdout_races = int(holdout["races"])
        holdout_positive_years = int(holdout["positive_years"])
        holdout_observed_years = int(holdout["observed_years"])
        wf_roi = float(wf["roi"])
        wf_races = int(wf["races"])
        wf_positive_years = int(wf["positive_years"])
        wf_observed_years = int(wf["observed_years"])

        holdout_beats_anchor = holdout_roi > float(anchor["holdout"]["roi"])
        holdout_sample_matches_anchor = holdout_races >= int(anchor["holdout"]["races"])
        holdout_all_years_positive = (
            holdout_observed_years > 0 and holdout_positive_years == holdout_observed_years
        )
        wf_coverage_matches_anchor = wf_races >= int(anchor["wf"]["races"])
        wf_years_match_anchor = wf_positive_years >= int(anchor["wf"]["positive_years"])

        can_replace_anchor = row["method_id"] == "op_durable_only" or all(
            [
                holdout_beats_anchor,
                holdout_sample_matches_anchor,
                holdout_all_years_positive,
                wf_coverage_matches_anchor,
                wf_years_match_anchor,
            ]
        )

        out_rows.append(
            {
                "label": row["label"],
                "method_type": row["method_type"],
                "holdout_roi": holdout_roi,
                "holdout_races": holdout_races,
                "holdout_profit": float(holdout["profit"]),
                "holdout_hit_rate": float(holdout["hit_rate"]),
                "holdout_positive_years": holdout_positive_years,
                "holdout_observed_years": holdout_observed_years,
                "holdout_worst_year_roi": worst_year(holdout),
                "wf_roi": wf_roi,
                "wf_races": wf_races,
                "wf_profit": float(wf["profit"]),
                "wf_hit_rate": float(wf["hit_rate"]),
                "wf_positive_years": wf_positive_years,
                "wf_observed_years": wf_observed_years,
                "wf_worst_year_roi": worst_year(wf),
                "vs_anchor_holdout_roi_delta": round(holdout_roi - float(anchor["holdout"]["roi"]), 2),
                "vs_anchor_holdout_races_delta": holdout_races - int(anchor["holdout"]["races"]),
                "vs_anchor_wf_roi_delta": round(wf_roi - float(anchor["wf"]["roi"]), 2),
                "vs_anchor_wf_races_delta": wf_races - int(anchor["wf"]["races"]),
                "check_holdout_beats_anchor": holdout_beats_anchor,
                "check_holdout_sample_matches_anchor": holdout_sample_matches_anchor,
                "check_holdout_all_years_positive": holdout_all_years_positive,
                "check_wf_coverage_matches_anchor": wf_coverage_matches_anchor,
                "check_wf_years_match_anchor": wf_years_match_anchor,
                "can_replace_anchor": can_replace_anchor,
                "decision": (
                    "KEEP AS ANCHOR"
                    if row["method_id"] == "op_durable_only"
                    else "PROMOTE" if can_replace_anchor else "KEEP AS WATCH / RESEARCH"
                ),
                "note": row["note"],
            }
        )

    df = pd.DataFrame(out_rows)
    order = {
        "KEEP AS ANCHOR": 0,
        "PROMOTE": 1,
        "KEEP AS WATCH / RESEARCH": 2,
    }
    df["sort_order"] = df["decision"].map(order)
    df = df.sort_values(["sort_order", "holdout_races", "wf_races"], ascending=[True, False, False]).reset_index(drop=True)
    return df.drop(columns=["sort_order"])


def build_markdown(df: pd.DataFrame) -> str:
    anchor = df[df["label"] == "OP_DURABLE_K7"].iloc[0]
    lines = [
        "# OP Family Decision Card",
        "",
        "This note compares the three realistic OP paths and asks one narrow question:",
        "**does anything clearly beat `OP_DURABLE_K7` strongly enough to replace it as the safest current anchor?**",
        "",
        "Short answer: **no**. The challengers show higher ROI, but not enough forward sample or coverage to replace the durable anchor yet.",
        "",
        "## Comparison Table",
        "",
        "| Method | Type | Holdout ROI | Holdout Races | Holdout Years+ | Worst Holdout Year | WF ROI | WF Races | WF Years+ | Decision |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for _, row in df.iterrows():
        lines.append(
            f"| {row['label']} | {row['method_type']} | {fmt_pct(row['holdout_roi'])} | {int(row['holdout_races'])} | "
            f"{int(row['holdout_positive_years'])}/{int(row['holdout_observed_years'])} | {fmt_pct(row['holdout_worst_year_roi'])} | "
            f"{fmt_pct(row['wf_roi'])} | {int(row['wf_races'])} | {int(row['wf_positive_years'])}/{int(row['wf_observed_years'])} | {row['decision']} |"
        )

    lines.extend(
        [
            "",
            "## Conservative Replacement Bar vs. Anchor",
            "",
            "A challenger only gets promoted in this note if it clears **all** of these conservative checks:",
            "",
            "1. Better holdout ROI than `OP_DURABLE_K7`",
            "2. At least as many 2024-2025 holdout races as `OP_DURABLE_K7`",
            "3. No losing year inside the 2024-2025 holdout window",
            "4. At least as many walk-forward races as `OP_DURABLE_K7`",
            "5. At least as many positive walk-forward years as `OP_DURABLE_K7`",
            "",
            "That bar is intentionally hard. Replacing the anchor should require clearer evidence than simply posting a prettier ROI on a much smaller sample.",
            "",
            "| Challenger | Better Holdout ROI? | Match Holdout Sample? | No Losing Holdout Year? | Match WF Coverage? | Match WF Positive Years? | Result |",
            "|---|---|---|---|---|---|---|",
        ]
    )

    for _, row in df[df["label"] != "OP_DURABLE_K7"].iterrows():
        lines.append(
            f"| {row['label']} | {'yes' if row['check_holdout_beats_anchor'] else 'no'} | "
            f"{'yes' if row['check_holdout_sample_matches_anchor'] else 'no'} | "
            f"{'yes' if row['check_holdout_all_years_positive'] else 'no'} | "
            f"{'yes' if row['check_wf_coverage_matches_anchor'] else 'no'} | "
            f"{'yes' if row['check_wf_years_match_anchor'] else 'no'} | {row['decision']} |"
        )

    lines.extend(
        [
            "",
            "## What This Means",
            "",
            f"- **Keep `OP_DURABLE_K7` as the live-paper anchor.** It has {int(anchor['holdout_races'])} holdout races and {int(anchor['wf_races'])} walk-forward races, which is the strongest forward sample inside the OP family.",
            "- **Keep `OP_REFINED_K7` as a challenger, not a replacement.** Its ROI is attractive, but its forward sample is much smaller and still includes a losing holdout year.",
            "- **Treat the train-only OP switch as research context.** In the current holdout window it collapses to the refined rule anyway, so it does not add independent forward evidence yet.",
            "",
            "## Notes",
            "",
        ]
    )

    for _, row in df.iterrows():
        lines.append(f"- **{row['label']}**: {row['note']}")

    lines.extend(
        [
            "",
            "## Validation",
            "",
            "- Source logic reused from `compare_main_approaches.py`",
            "- Source files: `phase5_race_cache.pkl`, `phase7_live_rules.json`, `walk_forward_validation_rules.csv`",
            f"- Wrote: `{OUT_CSV.name}`, `{OUT_MD.name}`",
            "",
        ]
    )

    return "\n".join(lines)


if __name__ == "__main__":
    df = build_dataframe()
    df.to_csv(OUT_CSV, index=False)
    report = build_markdown(df)
    OUT_MD.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"Saved: {OUT_CSV.name}")
    print(f"Saved: {OUT_MD.name}")
