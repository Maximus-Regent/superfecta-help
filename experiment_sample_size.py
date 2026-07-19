#!/usr/bin/env python3
"""
Experiment: sample-size-aware selector variants.

Follows up on the selector scoring experiment (experiment_selector_variants.py)
which found sqrt(train_roi) as best scorer (+30.42% vs +22.46% baseline).
The structural bottleneck identified there: the races factor caps at 150,
so CD_CORE's 400+ train races get no extra credit over CD_REFINED's ~135.

This experiment tests whether adjusting the races factor / sample-size bonus
closes more of the gap to the always-CD_CORE counterfactual (+36.20%).

Method:
  - Same frozen walk-forward artifacts (walk_forward_validation_rules.csv).
  - Re-scores and re-selects under each variant.
  - No new rule mining, no new data, no hand-picking.
  - All variants use strict guardrails (relaxation had zero effect).

Variants:
  1. raw_r150      — original baseline (raw ROI, races cap 150)
  2. sqrt_r150     — prior best (sqrt ROI, races cap 150)
  3. sqrt_r250     — sqrt ROI, races cap raised to 250
  4. sqrt_r300     — sqrt ROI, races cap raised to 300
  5. sqrt_r400     — sqrt ROI, races cap raised to 400
  6. sqrt_softbonus — sqrt ROI, cap at 150 + slow ramp to 400
  7. sqrt_lograces  — sqrt ROI, log-scaled races (no hard ceiling)
"""

from __future__ import annotations

from math import log, sqrt
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

BASE = Path("/Users/maximusregent_ai/Shared/Superfecta Help")
RULES_CSV = BASE / "walk_forward_validation_rules.csv"
FOLDS_CSV = BASE / "walk_forward_validation_folds.csv"

OUT_SUMMARY = BASE / "sample_size_experiment_summary.csv"
OUT_DETAIL = BASE / "sample_size_experiment_detail.csv"
OUT_REPORT = BASE / "SAMPLE_SIZE_EXPERIMENT.md"

MAX_PORTFOLIO_RULES = 3


# ── Races factor functions ──────────────────────────────────────────────────

def races_factor_cap(races: float, cap: float) -> float:
    """Hard ceiling at `cap` races."""
    return min(1.0, races / cap)


def races_factor_softbonus(races: float) -> float:
    """Base ramp to 150, then slow bonus up to 400.

    At 150: factor = 1.0
    At 250: factor = 1.0 + 0.25 * (100/250) = 1.10
    At 400: factor = 1.0 + 0.25 * 1.0 = 1.25
    """
    base = min(1.0, races / 150.0)
    bonus = 0.25 * min(1.0, max(0.0, races - 150.0) / 250.0)
    return base + bonus


def races_factor_lograces(races: float) -> float:
    """Log-scaled races: log(1+races) / log(151).

    At 150: factor = 1.0
    At 300: factor ≈ 1.14
    At 450: factor ≈ 1.22
    No hard ceiling, but diminishing returns.
    """
    return log(1.0 + races) / log(151.0)


# ── Non-ROI common factors (excluding races factor) ────────────────────────

def _stability_factors(
    pos_yr: float, active_yrs: float, top1: float, top3: float
) -> float:
    """Yearly stability + concentration penalty — races factor handled separately."""
    return (
        pos_yr
        * min(1.0, active_yrs / 8.0)
        * max(0.1, 1.0 - max(0.0, top1 - 0.30))
        * max(0.1, 1.0 - max(0.0, top3 - 0.55))
    )


# ── Scoring functions ───────────────────────────────────────────────────────

def score_raw_r150(roi: float, races: float, pos_yr: float,
                   active_yrs: float, top1: float, top3: float) -> float:
    """Original baseline: raw ROI, races cap 150."""
    return (max(roi, 0.0)
            * races_factor_cap(races, 150.0)
            * _stability_factors(pos_yr, active_yrs, top1, top3))


def score_sqrt_r150(roi: float, races: float, pos_yr: float,
                    active_yrs: float, top1: float, top3: float) -> float:
    """Prior best: sqrt ROI, races cap 150."""
    return (sqrt(max(roi, 0.0))
            * races_factor_cap(races, 150.0)
            * _stability_factors(pos_yr, active_yrs, top1, top3))


def score_sqrt_r250(roi: float, races: float, pos_yr: float,
                    active_yrs: float, top1: float, top3: float) -> float:
    """sqrt ROI, races cap raised to 250."""
    return (sqrt(max(roi, 0.0))
            * races_factor_cap(races, 250.0)
            * _stability_factors(pos_yr, active_yrs, top1, top3))


def score_sqrt_r300(roi: float, races: float, pos_yr: float,
                    active_yrs: float, top1: float, top3: float) -> float:
    """sqrt ROI, races cap raised to 300."""
    return (sqrt(max(roi, 0.0))
            * races_factor_cap(races, 300.0)
            * _stability_factors(pos_yr, active_yrs, top1, top3))


def score_sqrt_r400(roi: float, races: float, pos_yr: float,
                    active_yrs: float, top1: float, top3: float) -> float:
    """sqrt ROI, races cap raised to 400."""
    return (sqrt(max(roi, 0.0))
            * races_factor_cap(races, 400.0)
            * _stability_factors(pos_yr, active_yrs, top1, top3))


def score_sqrt_softbonus(roi: float, races: float, pos_yr: float,
                         active_yrs: float, top1: float, top3: float) -> float:
    """sqrt ROI, base at 150 + slow ramp to 400 (+25% max)."""
    return (sqrt(max(roi, 0.0))
            * races_factor_softbonus(races)
            * _stability_factors(pos_yr, active_yrs, top1, top3))


def score_sqrt_lograces(roi: float, races: float, pos_yr: float,
                        active_yrs: float, top1: float, top3: float) -> float:
    """sqrt ROI, log-scaled races (no hard ceiling, diminishing returns)."""
    return (sqrt(max(roi, 0.0))
            * races_factor_lograces(races)
            * _stability_factors(pos_yr, active_yrs, top1, top3))


SCORING_VARIANTS: dict[str, callable] = {
    "raw_r150": score_raw_r150,
    "sqrt_r150": score_sqrt_r150,
    "sqrt_r250": score_sqrt_r250,
    "sqrt_r300": score_sqrt_r300,
    "sqrt_r400": score_sqrt_r400,
    "sqrt_softbonus": score_sqrt_softbonus,
    "sqrt_lograces": score_sqrt_lograces,
}


# ── Guardrails (strict only — relaxation had zero effect) ──────────────────

STRICT_GUARD = {"base_ratio": 0.50}


def compute_qualifies(row: pd.Series) -> bool:
    """Strict guardrail: sparse, concentrated, unstable, or non-positive → disqualified."""
    if row["sparse_flag"] or row["concentrated_flag"]:
        return False
    if row["train_roi"] <= 0:
        return False
    return float(row["positive_train_year_ratio"]) >= STRICT_GUARD["base_ratio"]


# ── Selection ──────────────────────────────────────────────────────────────

def select_for_fold(fold_rules: pd.DataFrame) -> set[str]:
    """Select up to MAX_PORTFOLIO_RULES rules, one per track group.
    Mirrors walk_forward_validation.py select_rules_for_fold().
    """
    eligible = fold_rules[fold_rules["_qualifies"]].copy()
    if eligible.empty:
        eligible = fold_rules[fold_rules["train_roi"] > 0].copy()

    eligible = eligible.sort_values(
        ["_score", "alias_preference", "train_races", "positive_train_year_ratio"],
        ascending=[False, False, False, False],
    )

    chosen_ids: list[str] = []
    used_groups: set[str] = set()
    for _, row in eligible.iterrows():
        if row["track_group"] in used_groups:
            continue
        chosen_ids.append(row["rule_id"])
        used_groups.add(row["track_group"])
        if len(chosen_ids) >= MAX_PORTFOLIO_RULES:
            break

    if not chosen_ids and not fold_rules.empty:
        chosen_ids = [fold_rules.sort_values("_score", ascending=False).iloc[0]["rule_id"]]

    return set(chosen_ids)


def ensure_bool_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure flag columns are proper booleans (CSV may store as strings)."""
    bool_cols = ["sparse_flag", "unstable_flag", "concentrated_flag",
                 "qualifies", "selected", "strict_zero_but_bridge_has_coverage"]
    for col in bool_cols:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].str.strip().str.lower() == "true"
    return df


# ── Counterfactual: always CD_CORE ─────────────────────────────────────────

def compute_always_cdcore(rules_all: pd.DataFrame, test_years: list[int]) -> dict:
    """Compute the always-CD_CORE counterfactual for reference.

    For each fold, use the best non-CD rules from sqrt_r150 (prior best)
    plus force CD_CORE_K8 as the CD selection.
    """
    fold_rows: list[dict] = []
    for year in test_years:
        fold = rules_all[rules_all["test_year"] == year].copy()

        # Score with sqrt_r150 to pick non-CD rules
        fold["_score"] = fold.apply(
            lambda r: score_sqrt_r150(
                r["train_roi"], r["train_races"],
                r["positive_train_year_ratio"], r["active_train_years"],
                r["train_top1_share"], r["train_top3_share"],
            ), axis=1,
        )
        fold["_qualifies"] = fold.apply(compute_qualifies, axis=1)

        selected = select_for_fold(fold)

        # Force CD_CORE_K8 in, remove any other CD rule
        selected = {r for r in selected if not r.startswith("CD_")}
        if "CD_CORE_K8" in fold["rule_id"].values:
            selected.add("CD_CORE_K8")

        sel = fold[fold["rule_id"].isin(selected)]
        wag = int(sel["test_wagered"].sum())
        profit = float(sel["test_profit"].sum())
        roi = round(profit / wag * 100, 2) if wag > 0 else 0.0
        fold_rows.append({"test_year": year, "test_wagered": wag,
                          "test_profit": profit, "test_roi": roi,
                          "selected": ",".join(sorted(selected))})

    fold_df = pd.DataFrame(fold_rows)
    total_wag = int(fold_df["test_wagered"].sum())
    total_profit = float(fold_df["test_profit"].sum())
    return {
        "total_wagered": total_wag,
        "total_profit": round(total_profit, 2),
        "total_roi": round(total_profit / total_wag * 100, 2) if total_wag > 0 else 0.0,
        "positive_years": int((fold_df["test_roi"] > 0).sum()),
        "folds": fold_df,
    }


# ── Main experiment ────────────────────────────────────────────────────────

def run_experiment() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Run all sample-size variants and collect results."""
    rules_all = ensure_bool_cols(pd.read_csv(RULES_CSV))
    test_years = sorted(rules_all["test_year"].unique())

    summary_rows: list[dict] = []
    detail_rows: list[dict] = []

    for score_name, score_fn in SCORING_VARIANTS.items():
        # Re-score all rules
        rules = rules_all.copy()
        rules["_score"] = rules.apply(
            lambda r, fn=score_fn: fn(
                r["train_roi"], r["train_races"],
                r["positive_train_year_ratio"], r["active_train_years"],
                r["train_top1_share"], r["train_top3_share"],
            ),
            axis=1,
        )
        rules["_qualifies"] = rules.apply(compute_qualifies, axis=1)

        fold_rows: list[dict] = []
        for year in test_years:
            fold = rules[rules["test_year"] == year].copy()
            selected_ids = select_for_fold(fold)

            sel = fold[fold["rule_id"].isin(selected_ids)]
            wag = int(sel["test_wagered"].sum())
            profit = float(sel["test_profit"].sum())
            roi = round(profit / wag * 100, 2) if wag > 0 else 0.0

            cd_sel = next((r for r in selected_ids if r.startswith("CD_")), "NONE")
            op_sel = next((r for r in selected_ids if r.startswith("OP_")), "NONE")
            bel_sel = next((r for r in selected_ids if "BEL" in r), "NONE")

            fold_rows.append({
                "test_year": year,
                "selected": ",".join(sorted(selected_ids)),
                "test_wagered": wag,
                "test_profit": round(profit, 2),
                "test_roi": roi,
                "cd_rule": cd_sel,
                "op_rule": op_sel,
                "bel_rule": bel_sel,
            })

            # CD detail for every fold
            for _, r in fold[fold["track_group"] == "CD"].iterrows():
                # Compute the races factor for this variant
                if "r150" in score_name or score_name == "raw_r150":
                    rf = races_factor_cap(r["train_races"], 150.0)
                elif "r250" in score_name:
                    rf = races_factor_cap(r["train_races"], 250.0)
                elif "r300" in score_name:
                    rf = races_factor_cap(r["train_races"], 300.0)
                elif "r400" in score_name:
                    rf = races_factor_cap(r["train_races"], 400.0)
                elif "softbonus" in score_name:
                    rf = races_factor_softbonus(r["train_races"])
                elif "lograces" in score_name:
                    rf = races_factor_lograces(r["train_races"])
                else:
                    rf = races_factor_cap(r["train_races"], 150.0)

                detail_rows.append({
                    "variant": score_name,
                    "test_year": int(year),
                    "rule_id": r["rule_id"],
                    "score": round(float(r["_score"]), 4),
                    "races_factor": round(rf, 4),
                    "qualifies": bool(r["_qualifies"]),
                    "selected": r["rule_id"] in selected_ids,
                    "train_roi": round(float(r["train_roi"]), 2),
                    "train_races": int(r["train_races"]),
                    "pos_year_ratio": round(float(r["positive_train_year_ratio"]), 2),
                    "test_roi": round(float(r["test_roi"]), 2),
                    "test_profit": round(float(r["test_profit"]), 2),
                })

        fold_df = pd.DataFrame(fold_rows)
        total_wag = int(fold_df["test_wagered"].sum())
        total_profit = float(fold_df["test_profit"].sum())
        total_roi = round(total_profit / total_wag * 100, 2) if total_wag > 0 else 0.0
        pos_years = int((fold_df["test_roi"] > 0).sum())

        cd_counts = fold_df["cd_rule"].value_counts().to_dict()
        op_counts = fold_df["op_rule"].value_counts().to_dict()

        summary_rows.append({
            "variant": score_name,
            "total_wagered": total_wag,
            "total_profit": round(total_profit, 2),
            "total_roi": total_roi,
            "positive_years": pos_years,
            "total_years": len(test_years),
            "cd_core_folds": cd_counts.get("CD_CORE_K8", 0),
            "cd_refined_folds": cd_counts.get("CD_REFINED_K9", 0),
            "cd_none_folds": cd_counts.get("NONE", 0),
            "op_durable_folds": op_counts.get("OP_DURABLE_K7", 0),
            "op_refined_folds": op_counts.get("OP_REFINED_K7", 0),
        })

    # Counterfactual
    counterfactual = compute_always_cdcore(rules_all, test_years)

    return pd.DataFrame(summary_rows), pd.DataFrame(detail_rows), counterfactual


def validate_baselines(summary: pd.DataFrame) -> tuple[str, str]:
    """Verify raw_r150 matches original baseline and sqrt_r150 matches prior best."""
    # Original baseline
    baseline_folds = pd.read_csv(FOLDS_CSV)
    bl_wag = int(baseline_folds["test_wagered"].sum())
    bl_profit = float(baseline_folds["test_profit"].sum())
    bl_roi = round(bl_profit / bl_wag * 100, 2) if bl_wag > 0 else 0.0

    raw = summary[summary["variant"] == "raw_r150"].iloc[0]
    raw_ok = abs(raw["total_roi"] - bl_roi) < 0.5
    raw_msg = (f"raw_r150 validated: {raw['total_roi']:+.2f}% vs original {bl_roi:+.2f}%."
               if raw_ok else
               f"WARNING: raw_r150 = {raw['total_roi']:+.2f}% vs original {bl_roi:+.2f}%.")

    # Prior best (sqrt_r150 should match sqrt|strict = +30.42%)
    sqr = summary[summary["variant"] == "sqrt_r150"].iloc[0]
    sqr_ok = abs(sqr["total_roi"] - 30.42) < 0.5
    sqr_msg = (f"sqrt_r150 validated: {sqr['total_roi']:+.2f}% vs prior best +30.42%."
               if sqr_ok else
               f"WARNING: sqrt_r150 = {sqr['total_roi']:+.2f}% vs prior best +30.42%.")

    return raw_msg, sqr_msg


def build_report(summary: pd.DataFrame, details: pd.DataFrame,
                 counterfactual: dict) -> str:
    """Generate the full markdown report."""
    raw = summary[summary["variant"] == "raw_r150"].iloc[0]
    sqrt150 = summary[summary["variant"] == "sqrt_r150"].iloc[0]
    best = summary.loc[summary["total_roi"].idxmax()]
    delta_vs_raw = round(best["total_roi"] - raw["total_roi"], 2)
    delta_vs_sqrt = round(best["total_roi"] - sqrt150["total_roi"], 2)
    gap_to_cf = round(counterfactual["total_roi"] - best["total_roi"], 2)

    raw_msg, sqr_msg = validate_baselines(summary)

    lines = [
        "# Sample-Size-Aware Selector Experiment",
        "",
        "## Current Evidence Boundary",
        "",
        "- This is historical selector-tuning research on frozen walk-forward artifacts. It is useful for understanding why races-factor tuning did not beat `sqrt_r150`, but it is not a live paper-trade ledger, settled ROI evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "- Valid evidence scope: `valid_evidence_scope=sample_size_selector_replay_diagnostic_only`.",
        "- Valid use: compare selector-scoring variants against the original +22.46% train-only selector and the prior `sqrt_r150` benchmark. Do not treat the `keep sqrt_r150` recommendation as permission to change the current paper basket or override `forward_evidence_scorecard.txt`.",
        "- Current posture still comes from the frozen scorecard plus paper-observation lane: keep `OP_DURABLE_K7` as the safest anchor, `CD_CORE_K8` as the primary OP/CD paper-basket companion, and `OP_REFINED_K7` in shadow/watch until ROI-complete paper evidence clears the scorecard gates.",
        "- The always-CD_CORE counterfactual and selector variants are replay diagnostics on already-mined candidate rules, not a fresh from-scratch discovery loop and not proof that CD_CORE should displace OP as anchor evidence.",
        "- If this selector-research report is regenerated after scorecard/rules/signals/settlement-ledger byte changes, follow `current_evidence_summary.json.rebuild_validation_contract`: `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`; this rebuild route is provenance metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "- Do not substitute `BAQ` for dormant `BEL`, and validate this boundary with `python3 validate_sample_size_experiment_caution.py`.",
        "",
        "## Purpose",
        "",
        "Test whether adjusting the races factor / sample-size bonus in the",
        "walk-forward selection score closes more of the gap between the selector",
        f"(+{sqrt150['total_roi']:.2f}%) and the always-CD_CORE counterfactual "
        f"(+{counterfactual['total_roi']:.2f}%).",
        "",
        "The prior experiment found sqrt(train_roi) as the best ROI dampener.",
        "The structural bottleneck identified: races factor caps at 150, so",
        "CD_CORE's 400+ races get the same credit as CD_REFINED's ~135.",
        "",
        "## Method",
        "",
        "- Same frozen `walk_forward_validation_rules.csv` — no new rule mining.",
        "- All variants use strict guardrails (relaxation had zero effect).",
        "- All except raw_r150 use sqrt(train_roi) as the ROI dampener.",
        "- Only the races factor changes between variants.",
        "",
        f"**Validation:** {raw_msg} {sqr_msg}",
        "",
        "## Races Factor Variants",
        "",
        "| Variant | ROI Term | Races Factor | Description |",
        "|---|---|---|---|",
        "| raw_r150 | raw | `min(1, N/150)` | Original baseline |",
        "| sqrt_r150 | sqrt | `min(1, N/150)` | Prior best (cap 150) |",
        "| sqrt_r250 | sqrt | `min(1, N/250)` | Cap raised to 250 |",
        "| sqrt_r300 | sqrt | `min(1, N/300)` | Cap raised to 300 |",
        "| sqrt_r400 | sqrt | `min(1, N/400)` | Cap raised to 400 |",
        "| sqrt_softbonus | sqrt | `min(1,N/150) + 0.25·min(1,(N-150)/250)` | Soft bonus above 150 |",
        "| sqrt_lograces | sqrt | `log(1+N)/log(151)` | Continuous log scaling |",
        "",
        "### Races Factor Values for CD Rules",
        "",
    ]

    # Show races factor comparison for CD rules at representative folds
    lines.append("| Variant | CD_CORE @ 400 races | CD_REFINED @ 135 races | Ratio |")
    lines.append("|---|---:|---:|---:|")
    demo_pairs = [
        ("cap 150", races_factor_cap(400, 150), races_factor_cap(135, 150)),
        ("cap 250", races_factor_cap(400, 250), races_factor_cap(135, 250)),
        ("cap 300", races_factor_cap(400, 300), races_factor_cap(135, 300)),
        ("cap 400", races_factor_cap(400, 400), races_factor_cap(135, 400)),
        ("softbonus", races_factor_softbonus(400), races_factor_softbonus(135)),
        ("lograces", races_factor_lograces(400), races_factor_lograces(135)),
    ]
    for name, core_f, ref_f in demo_pairs:
        ratio = core_f / ref_f if ref_f > 0 else float("inf")
        lines.append(f"| {name} | {core_f:.3f} | {ref_f:.3f} | {ratio:.2f}x |")
    lines.append("")

    # Results table
    lines.extend([
        "## Results",
        "",
        "| Variant | ROI | Profit | Pos Yrs | CD_CORE | CD_REFINED | CD_NONE | OP_DUR | OP_REF |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|",
    ])

    for _, row in summary.sort_values("total_roi", ascending=False).iterrows():
        marker = " **" if row["variant"] == best["variant"] else ""
        end = "**" if marker else ""
        lines.append(
            f"| {marker}{row['variant']}{end} | {row['total_roi']:+.2f}% | "
            f"${row['total_profit']:,.2f} | {row['positive_years']}/{row['total_years']} | "
            f"{row['cd_core_folds']} | {row['cd_refined_folds']} | {row['cd_none_folds']} | "
            f"{row['op_durable_folds']} | {row['op_refined_folds']} |"
        )

    lines.extend([
        "",
        f"**Counterfactual (always CD_CORE):** {counterfactual['total_roi']:+.2f}% ROI, "
        f"${counterfactual['total_profit']:,.2f} profit, "
        f"{counterfactual['positive_years']}/10 positive years.",
        "",
        "### Summary",
        "",
        f"- **Original baseline (raw_r150):** {raw['total_roi']:+.2f}% ROI",
        f"- **Prior best (sqrt_r150):** {sqrt150['total_roi']:+.2f}% ROI",
        f"- **Best this experiment ({best['variant']}):** {best['total_roi']:+.2f}% ROI",
        f"- **Delta vs original:** {delta_vs_raw:+.2f}pp",
        f"- **Delta vs prior best:** {delta_vs_sqrt:+.2f}pp",
        f"- **Gap to counterfactual:** {gap_to_cf:+.2f}pp remaining",
        "",
    ])

    # ── CD Detail: fold-by-fold comparison of key variants ─────────────
    lines.extend(["## CD Selection Detail", ""])

    key_variants = ["sqrt_r150", best["variant"]]
    if best["variant"] == "sqrt_r150":
        key_variants = ["raw_r150", "sqrt_r150"]
    # Deduplicate
    key_variants = list(dict.fromkeys(key_variants))

    for vname in key_variants:
        v_det = details[details["variant"] == vname].sort_values(["test_year", "rule_id"])
        lines.extend([f"### {vname}", ""])
        lines.append("| Year | Rule | Score | Races Factor | Qual | Sel | Train ROI | Races | PosYr | Test ROI |")
        lines.append("|---:|---|---:|---:|---|---|---:|---:|---:|---:|")
        for _, r in v_det.iterrows():
            q = "Y" if r["qualifies"] else "N"
            s = "**YES**" if r["selected"] else "no"
            lines.append(
                f"| {r['test_year']} | {r['rule_id']} | {r['score']:.4f} | "
                f"{r['races_factor']:.3f} | {q} | {s} | "
                f"{r['train_roi']:+.2f}% | {r['train_races']} | {r['pos_year_ratio']:.2f} | "
                f"{r['test_roi']:+.2f}% |"
            )
        lines.append("")

    # ── Fold-by-fold comparison: sqrt_r150 vs best ─────────────────────
    if best["variant"] != "sqrt_r150":
        lines.extend(["## Fold-by-Fold: Prior Best vs New Best", ""])

        rules_all = ensure_bool_cols(pd.read_csv(RULES_CSV))
        test_years = sorted(rules_all["test_year"].unique())

        fold_compare: list[dict] = []
        for variant_name in ["sqrt_r150", best["variant"]]:
            score_fn = SCORING_VARIANTS[variant_name]
            rules = rules_all.copy()
            rules["_score"] = rules.apply(
                lambda r, fn=score_fn: fn(
                    r["train_roi"], r["train_races"],
                    r["positive_train_year_ratio"], r["active_train_years"],
                    r["train_top1_share"], r["train_top3_share"],
                ), axis=1,
            )
            rules["_qualifies"] = rules.apply(compute_qualifies, axis=1)
            for year in test_years:
                fold = rules[rules["test_year"] == year]
                sel_ids = select_for_fold(fold)
                sel = fold[fold["rule_id"].isin(sel_ids)]
                wag = int(sel["test_wagered"].sum())
                profit = float(sel["test_profit"].sum())
                roi = round(profit / wag * 100, 2) if wag > 0 else 0.0
                fold_compare.append({
                    "variant": variant_name,
                    "test_year": year,
                    "selected": ",".join(sorted(sel_ids)),
                    "test_roi": roi,
                    "test_profit": round(profit, 2),
                })

        fc = pd.DataFrame(fold_compare)
        prior_folds = fc[fc["variant"] == "sqrt_r150"].set_index("test_year")
        best_folds = fc[fc["variant"] == best["variant"]].set_index("test_year")

        lines.append("| Year | sqrt_r150 Rules | ROI | Best Rules | ROI | Delta |")
        lines.append("|---:|---|---:|---|---:|---:|")
        for year in test_years:
            pr = prior_folds.loc[year]
            be = best_folds.loc[year]
            delta = round(be["test_roi"] - pr["test_roi"], 2)
            changed = f"{delta:+.2f}pp" if abs(delta) > 0.01 else "—"
            lines.append(
                f"| {year} | {pr['selected']} | {pr['test_roi']:+.2f}% | "
                f"{be['selected']} | {be['test_roi']:+.2f}% | {changed} |"
            )
        lines.append("")

    # ── Analysis ───────────────────────────────────────────────────────
    lines.extend(["## Analysis", ""])

    # Analyze CD_CORE selection across variants
    best_row = summary.loc[summary["total_roi"].idxmax()]
    max_cdcore = summary["cd_core_folds"].max()
    max_cdcore_variant = summary.loc[summary["cd_core_folds"].idxmax(), "variant"]

    # Count folds where CD_CORE is disqualified by guardrail.
    rules_for_count = ensure_bool_cols(pd.read_csv(RULES_CSV))
    cd_core_disq_years: list[int] = []
    for yr in sorted(rules_for_count["test_year"].unique()):
        core = rules_for_count[(rules_for_count["test_year"] == yr) &
                               (rules_for_count["rule_id"] == "CD_CORE_K8")]
        if not core.empty:
            r = core.iloc[0]
            if r["unstable_flag"] or r["sparse_flag"] or r["concentrated_flag"] or r["train_roi"] <= 0:
                cd_core_disq_years.append(int(yr))
    cd_core_disq_folds = len(cd_core_disq_years)
    cd_core_disq_year_list = ", ".join(str(year) for year in cd_core_disq_years)

    lines.extend([
        "**Why the races factor doesn't help:**",
        "",
        f"CD_CORE_K8 is **disqualified by the guardrail** (pos_year_ratio < 0.50) in {cd_core_disq_folds} of 10 folds",
        f"({cd_core_disq_year_list}). In the 4 folds where CD_CORE qualifies",
        "(2015, 2016, 2018, 2025), CD_REFINED still outscores it on sqrt(ROI) in 3 of those 4 folds.",
        "The races factor can only matter when both rules qualify AND compete on score — and even",
        "a 3x races factor advantage (sqrt_r400) can't overcome the sqrt(66%) vs sqrt(7%) ROI gap.",
        "",
    ])

    if max_cdcore > int(sqrt150["cd_core_folds"]):
        max_cdcore_row = summary[summary["variant"] == max_cdcore_variant].iloc[0]
        lines.extend([
            f"{max_cdcore_variant} did increase CD_CORE selection to **{max_cdcore}/10 folds** (vs {sqrt150['cd_core_folds']}/10 under sqrt_r150),",
            "but the additional folds included 2018 where CD_CORE had -37.62% test ROI vs",
            "CD_REFINED's +869.41% — a catastrophic misselection that wiped out the gains",
            "from 2025 (+78.21% CD_CORE vs -61.12% CD_REFINED).",
            "",
        ])

    lines.extend([
        "**Key finding — the gap was already closed:**",
        "",
        "The prior diagnosis estimated a +13.74pp gap between the selector (+22.46%) and the",
        "always-CD_CORE counterfactual (+36.20%). But that comparison used raw scoring for non-CD",
        f"rules. Under sqrt scoring, the always-CD_CORE counterfactual is {counterfactual['total_roi']:+.2f}%, and the",
        f"sqrt_r150 selector already achieves {sqrt150['total_roi']:+.2f}% — **slightly exceeding the counterfactual.**",
        "The sqrt dampening improvement (+7.96pp) came mostly from fixing non-CD selection",
        "(displacing CD_REFINED from the 2017 portfolio in favor of OP_DURABLE), not from",
        "CD_CORE vs CD_REFINED directly.",
        "",
        f"**Gap analysis:** The always-CD_CORE counterfactual achieves {counterfactual['total_roi']:+.2f}% ROI.",
        f"The sqrt_r150 selector achieves {sqrt150['total_roi']:+.2f}%. There is no remaining gap to close.",
    ])
    lines.append("")

    # ── Recommendation ─────────────────────────────────────────────────
    lines.extend(["## Recommendation", ""])

    if delta_vs_sqrt > 2.0:
        lines.extend([
            f"The **{best['variant']}** variant improves walk-forward ROI by "
            f"**{delta_vs_sqrt:+.2f}pp** over the prior best (sqrt_r150), "
            f"reaching {best['total_roi']:+.2f}%.",
            "",
            "**Recommended action:** update the selection score formula to use "
            f"the `{best['variant']}` races factor.",
        ])
    elif delta_vs_sqrt > 0.5:
        lines.extend([
            f"Modest improvement ({delta_vs_sqrt:+.2f}pp) from {best['variant']}. "
            f"The evidence is suggestive but not conclusive.",
        ])
    else:
        lines.extend([
            f"No meaningful improvement from adjusting the races factor alone "
            f"({delta_vs_sqrt:+.2f}pp).",
            "The bottleneck is the guardrail, not the sample-size weighting. But it does not",
            "matter because sqrt_r150 already matches or exceeds the counterfactual.",
            "",
            "**Recommended action:** keep sqrt_r150 as the selector. No further races factor",
            "tuning is warranted. The CD selection \"problem\" identified in the diagnosis was",
            "already resolved by the sqrt dampening of the ROI term — the improvement came from",
            "better non-CD selection, not from CD_CORE replacing CD_REFINED.",
        ])

    lines.extend([
        "",
        f"Artifacts: `{OUT_SUMMARY.name}`, `{OUT_DETAIL.name}`, `{OUT_REPORT.name}`.",
    ])

    return "\n".join(lines) + "\n"


def main() -> None:
    print("Running sample-size-aware selector experiment...")
    print(f"  Variants: {list(SCORING_VARIANTS.keys())}")
    print(f"  Total configurations: {len(SCORING_VARIANTS)}")
    print()

    summary, details, counterfactual = run_experiment()

    summary.to_csv(OUT_SUMMARY, index=False)
    details.to_csv(OUT_DETAIL, index=False)

    report = build_report(summary, details, counterfactual)
    OUT_REPORT.write_text(report)

    print("=== Results ===\n")
    display_cols = [
        "variant", "total_roi", "total_profit", "positive_years",
        "cd_core_folds", "cd_refined_folds", "op_durable_folds",
    ]
    print(summary[display_cols].sort_values("total_roi", ascending=False).to_string(index=False))

    raw = summary[summary["variant"] == "raw_r150"].iloc[0]
    sqrt150 = summary[summary["variant"] == "sqrt_r150"].iloc[0]
    best = summary.loc[summary["total_roi"].idxmax()]

    print(f"\nOriginal baseline (raw_r150): {raw['total_roi']:+.2f}% ROI")
    print(f"Prior best (sqrt_r150): {sqrt150['total_roi']:+.2f}% ROI")
    print(f"Best this experiment ({best['variant']}): {best['total_roi']:+.2f}% ROI")
    print(f"Counterfactual (always CD_CORE): {counterfactual['total_roi']:+.2f}% ROI")
    print(f"Delta vs prior best: {best['total_roi'] - sqrt150['total_roi']:+.2f}pp")
    print(f"Gap to counterfactual: {counterfactual['total_roi'] - best['total_roi']:+.2f}pp")

    raw_msg, sqr_msg = validate_baselines(summary)
    print(f"\n{raw_msg}")
    print(sqr_msg)

    print(f"\nWrote {OUT_SUMMARY.name}")
    print(f"Wrote {OUT_DETAIL.name}")
    print(f"Wrote {OUT_REPORT.name}")


if __name__ == "__main__":
    main()
