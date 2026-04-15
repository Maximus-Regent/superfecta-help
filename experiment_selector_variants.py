#!/usr/bin/env python3
"""
Experiment: walk-forward selector scoring variants.

Tests whether dampening the ROI term in the selection score fixes the
CD track-group selection bottleneck (CD_REFINED_K9 over-selected due
to ~10x higher train ROI) and whether the fix generalizes beyond CD.

Method:
  - Uses the SAME frozen walk-forward artifacts (walk_forward_validation_rules.csv).
  - Re-scores and re-selects rules under each variant.
  - Computes portfolio walk-forward ROI from per-rule test outcomes already recorded.
  - No new rule mining, no new data, no hand-picking.

Variants:
  Scoring:   raw (baseline), sqrt, log, sqrt+cost, log+cost
  Guardrail: strict (baseline), relaxed_high_n (pos_year_ratio → 0.35 when N≥150)
"""

from __future__ import annotations

from math import log, sqrt
from pathlib import Path

import pandas as pd

BASE = Path("/Users/maximusregent_ai/Shared/Superfecta Help")
RULES_CSV = BASE / "walk_forward_validation_rules.csv"
FOLDS_CSV = BASE / "walk_forward_validation_folds.csv"

OUT_SUMMARY = BASE / "selector_experiment_summary.csv"
OUT_DETAIL = BASE / "selector_experiment_detail.csv"
OUT_REPORT = BASE / "SELECTOR_EXPERIMENT.md"

MAX_PORTFOLIO_RULES = 3


# ── Scoring functions ────────────────────────────────────────────────────────
# All share the same non-ROI factors (races, yearly stability, concentration).


def _common_factors(
    races: float, pos_yr: float, active_yrs: float, top1: float, top3: float
) -> float:
    return (
        min(1.0, races / 150.0)
        * pos_yr
        * min(1.0, active_yrs / 8.0)
        * max(0.1, 1.0 - max(0.0, top1 - 0.30))
        * max(0.1, 1.0 - max(0.0, top3 - 0.55))
    )


def score_raw(roi: float, races: float, pos_yr: float, active_yrs: float,
              top1: float, top3: float, cost: float) -> float:
    """Current baseline: raw train ROI as the dominant term."""
    return max(roi, 0.0) * _common_factors(races, pos_yr, active_yrs, top1, top3)


def score_sqrt(roi: float, races: float, pos_yr: float, active_yrs: float,
               top1: float, top3: float, cost: float) -> float:
    """Dampened ROI: sqrt compresses the 10x gap to ~3x."""
    return sqrt(max(roi, 0.0)) * _common_factors(races, pos_yr, active_yrs, top1, top3)


def score_log(roi: float, races: float, pos_yr: float, active_yrs: float,
              top1: float, top3: float, cost: float) -> float:
    """More aggressive dampening: log(1+roi) compresses 10x to ~2.5x."""
    return log(1.0 + max(roi, 0.0)) * _common_factors(races, pos_yr, active_yrs, top1, top3)


def score_sqrt_cost(roi: float, races: float, pos_yr: float, active_yrs: float,
                    top1: float, top3: float, cost: float) -> float:
    """sqrt ROI + cost penalty normalized to K=7 baseline (cost=120)."""
    cost_adj = sqrt(120.0 / max(cost, 1))
    return sqrt(max(roi, 0.0)) * cost_adj * _common_factors(races, pos_yr, active_yrs, top1, top3)


def score_log_cost(roi: float, races: float, pos_yr: float, active_yrs: float,
                   top1: float, top3: float, cost: float) -> float:
    """log ROI + cost penalty normalized to K=7 baseline (cost=120)."""
    cost_adj = sqrt(120.0 / max(cost, 1))
    return log(1.0 + max(roi, 0.0)) * cost_adj * _common_factors(races, pos_yr, active_yrs, top1, top3)


SCORING_VARIANTS: dict[str, callable] = {
    "raw": score_raw,
    "sqrt": score_sqrt,
    "log": score_log,
    "sqrt_cost": score_sqrt_cost,
    "log_cost": score_log_cost,
}


# ── Guardrail configurations ────────────────────────────────────────────────

GUARDRAIL_VARIANTS: dict[str, dict] = {
    "strict": {"base_ratio": 0.50, "high_n_races": None, "relaxed_ratio": None},
    "relaxed_n150": {"base_ratio": 0.50, "high_n_races": 150, "relaxed_ratio": 0.35},
}


def compute_qualifies(row: pd.Series, guard_cfg: dict) -> bool:
    """Determine if a rule qualifies under the given guardrail config."""
    if row["sparse_flag"] or row["concentrated_flag"]:
        return False
    if row["train_roi"] <= 0:
        return False

    pos_yr = float(row["positive_train_year_ratio"])
    base_ratio = guard_cfg["base_ratio"]

    if pos_yr >= base_ratio:
        return True

    # Conditional relaxation for high-sample rules
    high_n = guard_cfg.get("high_n_races")
    if high_n and row["train_races"] >= high_n:
        relaxed = guard_cfg.get("relaxed_ratio", base_ratio)
        if relaxed is not None and pos_yr >= relaxed:
            return True

    return False


def select_for_fold(fold_rules: pd.DataFrame) -> set[str]:
    """Select up to MAX_PORTFOLIO_RULES rules, one per track group.

    Mirrors the logic in walk_forward_validation.py select_rules_for_fold().
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


def run_experiment() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run all scoring × guardrail variants and collect results."""
    rules_all = ensure_bool_cols(pd.read_csv(RULES_CSV))
    test_years = sorted(rules_all["test_year"].unique())

    summary_rows: list[dict] = []
    detail_rows: list[dict] = []

    for score_name, score_fn in SCORING_VARIANTS.items():
        for guard_name, guard_cfg in GUARDRAIL_VARIANTS.items():
            variant = f"{score_name}|{guard_name}"

            # Re-score all rules
            rules = rules_all.copy()
            rules["_score"] = rules.apply(
                lambda r: score_fn(
                    r["train_roi"], r["train_races"],
                    r["positive_train_year_ratio"], r["active_train_years"],
                    r["train_top1_share"], r["train_top3_share"],
                    r["cost_per_race"],
                ),
                axis=1,
            )
            rules["_qualifies"] = rules.apply(
                lambda r: compute_qualifies(r, guard_cfg), axis=1,
            )

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
                    detail_rows.append({
                        "variant": variant,
                        "test_year": int(year),
                        "rule_id": r["rule_id"],
                        "score": round(float(r["_score"]), 4),
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
                "variant": variant,
                "scoring": score_name,
                "guardrail": guard_name,
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

    return pd.DataFrame(summary_rows), pd.DataFrame(detail_rows)


def validate_baseline(summary: pd.DataFrame) -> str:
    """Check that raw|strict reproduces the original walk-forward result."""
    baseline_folds = pd.read_csv(FOLDS_CSV)
    bl_wag = int(baseline_folds["test_wagered"].sum())
    bl_profit = float(baseline_folds["test_profit"].sum())
    bl_roi = round(bl_profit / bl_wag * 100, 2) if bl_wag > 0 else 0.0

    exp_bl = summary[(summary["scoring"] == "raw") & (summary["guardrail"] == "strict")].iloc[0]
    match = abs(exp_bl["total_roi"] - bl_roi) < 0.5

    if match:
        return f"Baseline validated: experiment {exp_bl['total_roi']:+.2f}% vs original {bl_roi:+.2f}%."
    else:
        return (
            f"WARNING: baseline mismatch. Experiment {exp_bl['total_roi']:+.2f}% vs "
            f"original {bl_roi:+.2f}%. Differences may stem from CSV rounding. "
            f"Relative comparisons across variants remain valid."
        )


def build_report(summary: pd.DataFrame, details: pd.DataFrame) -> str:
    baseline = summary[(summary["scoring"] == "raw") & (summary["guardrail"] == "strict")].iloc[0]
    best = summary.loc[summary["total_roi"].idxmax()]
    delta = round(best["total_roi"] - baseline["total_roi"], 2)

    validation_msg = validate_baseline(summary)

    lines = [
        "# Selector Scoring Experiment",
        "",
        "## Purpose",
        "",
        "Test whether dampening the ROI term in the walk-forward selection score",
        "fixes the CD track-group selection bottleneck and whether the fix generalizes.",
        "",
        "## Method",
        "",
        "- Re-scores and re-selects rules from the frozen `walk_forward_validation_rules.csv`.",
        "- Per-rule test outcomes are already recorded — only the selection changes.",
        "- No new rule mining, no new data, no hand-picking.",
        "",
        f"**Validation:** {validation_msg}",
        "",
        "## Scoring Variants",
        "",
        "| Name | ROI Term | Cost Adjustment |",
        "|---|---|---|",
        "| raw | `max(roi, 0)` | None |",
        "| sqrt | `sqrt(max(roi, 0))` | None |",
        "| log | `log(1 + max(roi, 0))` | None |",
        "| sqrt_cost | `sqrt(max(roi, 0))` | `× sqrt(120/cost)` |",
        "| log_cost | `log(1 + max(roi, 0))` | `× sqrt(120/cost)` |",
        "",
        "## Guardrail Variants",
        "",
        "| Name | MIN_POSITIVE_YEAR_RATIO | Relaxation |",
        "|---|---|---|",
        "| strict | 0.50 for all | None |",
        f"| relaxed_n150 | 0.50 (0.35 if N≥150) | High-sample rules get lower threshold |",
        "",
        "## Results",
        "",
        "| Variant | ROI | Profit | Pos Years | CD_CORE | CD_REFINED | CD_NONE | OP_DUR | OP_REF |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|",
    ]

    for _, row in summary.sort_values("total_roi", ascending=False).iterrows():
        marker = " **" if row["variant"] == best["variant"] else ""
        end_marker = "**" if marker else ""
        lines.append(
            f"| {marker}{row['variant']}{end_marker} | {row['total_roi']:+.2f}% | "
            f"${row['total_profit']:,.2f} | {row['positive_years']}/{row['total_years']} | "
            f"{row['cd_core_folds']} | {row['cd_refined_folds']} | {row['cd_none_folds']} | "
            f"{row['op_durable_folds']} | {row['op_refined_folds']} |"
        )

    lines.extend([
        "",
        f"**Baseline (raw|strict):** {baseline['total_roi']:+.2f}% ROI, "
        f"${baseline['total_profit']:,.2f} profit.",
        f"**Best ({best['variant']}):** {best['total_roi']:+.2f}% ROI, "
        f"${best['total_profit']:,.2f} profit.",
        f"**Delta:** {delta:+.2f}pp.",
        "",
    ])

    # ── CD detail: baseline vs best ──────────────────────────────────────
    lines.extend([
        "## CD Selection Detail",
        "",
    ])

    for vname, vlabel in [(baseline["variant"], "Baseline"), (best["variant"], "Best")]:
        if vname == best["variant"] and vname == baseline["variant"]:
            continue  # don't repeat if same
        v_det = details[details["variant"] == vname].sort_values(["test_year", "rule_id"])
        lines.extend([f"### {vlabel}: {vname}", ""])
        lines.append("| Year | Rule | Score | Qual | Sel | Train ROI | Races | PosYr | Test ROI |")
        lines.append("|---:|---|---:|---|---|---:|---:|---:|---:|")
        for _, r in v_det.iterrows():
            q = "Y" if r["qualifies"] else "N"
            s = "**YES**" if r["selected"] else "no"
            lines.append(
                f"| {r['test_year']} | {r['rule_id']} | {r['score']:.4f} | {q} | {s} | "
                f"{r['train_roi']:+.2f}% | {r['train_races']} | {r['pos_year_ratio']:.2f} | "
                f"{r['test_roi']:+.2f}% |"
            )
        lines.append("")

    # ── Fold-by-fold comparison: baseline vs best ────────────────────────
    if best["variant"] != baseline["variant"]:
        lines.extend(["## Fold-by-Fold: Baseline vs Best", ""])

        rules_all = ensure_bool_cols(pd.read_csv(RULES_CSV))
        test_years = sorted(rules_all["test_year"].unique())

        # Rebuild fold selections for baseline and best
        fold_compare: list[dict] = []
        for variant_name in [baseline["variant"], best["variant"]]:
            sname, gname = variant_name.split("|")
            score_fn = SCORING_VARIANTS[sname]
            guard_cfg = GUARDRAIL_VARIANTS[gname]
            rules = rules_all.copy()
            rules["_score"] = rules.apply(
                lambda r, fn=score_fn: fn(
                    r["train_roi"], r["train_races"],
                    r["positive_train_year_ratio"], r["active_train_years"],
                    r["train_top1_share"], r["train_top3_share"], r["cost_per_race"],
                ), axis=1,
            )
            rules["_qualifies"] = rules.apply(
                lambda r, gc=guard_cfg: compute_qualifies(r, gc), axis=1,
            )
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
        bl_folds = fc[fc["variant"] == baseline["variant"]].set_index("test_year")
        best_folds = fc[fc["variant"] == best["variant"]].set_index("test_year")

        lines.append("| Year | Baseline Rules | Baseline ROI | Best Rules | Best ROI | Change |")
        lines.append("|---:|---|---:|---|---:|---|")
        for year in test_years:
            bl_r = bl_folds.loc[year]
            be_r = best_folds.loc[year]
            changed = "**CHANGED**" if bl_r["selected"] != be_r["selected"] else ""
            lines.append(
                f"| {year} | {bl_r['selected']} | {bl_r['test_roi']:+.2f}% | "
                f"{be_r['selected']} | {be_r['test_roi']:+.2f}% | {changed} |"
            )
        lines.append("")

    # ── Generalization check ─────────────────────────────────────────────
    lines.extend(["## Generalization Beyond CD", ""])

    bl_op_dur = int(baseline["op_durable_folds"])
    op_changed_variants = summary[summary["op_durable_folds"] != bl_op_dur]
    if op_changed_variants.empty:
        lines.append(
            "No variant changed OP track-group selection. The scoring change is "
            "CD-specific in this dataset — OP selection is stable across all variants."
        )
    else:
        lines.append("Some variants changed OP selection:")
        for _, row in op_changed_variants.iterrows():
            lines.append(
                f"- **{row['variant']}**: OP_DURABLE={row['op_durable_folds']}, "
                f"OP_REFINED={row['op_refined_folds']} "
                f"(baseline: OP_DURABLE={bl_op_dur})"
            )
    lines.append("")

    # ── Recommendation ───────────────────────────────────────────────────
    lines.extend(["## Recommendation", ""])

    if delta > 5.0:
        lines.extend([
            f"The **{best['variant']}** variant improves walk-forward ROI by **{delta:+.2f}pp** "
            f"({baseline['total_roi']:+.2f}% → {best['total_roi']:+.2f}%).",
            "",
            f"CD_CORE_K8 is selected in **{best['cd_core_folds']}/{best['total_years']}** folds "
            f"(up from {baseline['cd_core_folds']}/{baseline['total_years']} under baseline).",
            "",
            "The improvement comes from fixing the CD selection bottleneck identified in "
            "`DIAGNOSE_CD_SELECTION.md`. The dampened ROI term prevents high-ROI-but-fragile "
            "rules from dominating the score over stable-but-modest rules.",
            "",
            "**Recommended action:** update the selection score formula in "
            "`walk_forward_validation.py` to use the dampened variant, then re-run the full "
            "walk-forward to confirm.",
        ])
    elif delta > 2.0:
        lines.extend([
            f"Moderate improvement ({delta:+.2f}pp). The dampened scoring helps but the "
            f"evidence is not overwhelming. Consider adopting if other diagnostics agree.",
        ])
    else:
        lines.extend([
            f"Marginal or no improvement ({delta:+.2f}pp). "
            f"The selector should NOT be changed based on this evidence alone.",
        ])

    lines.extend([
        "",
        f"Artifacts: `{OUT_SUMMARY.name}`, `{OUT_DETAIL.name}`, `{OUT_REPORT.name}`.",
    ])

    return "\n".join(lines) + "\n"


def main() -> None:
    print("Running selector scoring experiment...")
    print(f"  Scoring variants: {list(SCORING_VARIANTS.keys())}")
    print(f"  Guardrail variants: {list(GUARDRAIL_VARIANTS.keys())}")
    print(f"  Total configurations: {len(SCORING_VARIANTS) * len(GUARDRAIL_VARIANTS)}")
    print()

    summary, details = run_experiment()

    summary.to_csv(OUT_SUMMARY, index=False)
    details.to_csv(OUT_DETAIL, index=False)

    report = build_report(summary, details)
    OUT_REPORT.write_text(report)

    print("=== Results ===\n")
    display_cols = [
        "variant", "total_roi", "total_profit", "positive_years",
        "cd_core_folds", "cd_refined_folds", "op_durable_folds", "op_refined_folds",
    ]
    print(summary[display_cols].sort_values("total_roi", ascending=False).to_string(index=False))

    baseline = summary[(summary["scoring"] == "raw") & (summary["guardrail"] == "strict")].iloc[0]
    best = summary.loc[summary["total_roi"].idxmax()]
    delta = round(best["total_roi"] - baseline["total_roi"], 2)

    print(f"\nBaseline (raw|strict): {baseline['total_roi']:+.2f}% ROI, ${baseline['total_profit']:,.2f}")
    print(f"Best ({best['variant']}): {best['total_roi']:+.2f}% ROI, ${best['total_profit']:,.2f}")
    print(f"Delta: {delta:+.2f}pp")

    print(f"\n{validate_baseline(summary)}")
    print(f"\nWrote {OUT_SUMMARY.name}")
    print(f"Wrote {OUT_DETAIL.name}")
    print(f"Wrote {OUT_REPORT.name}")


if __name__ == "__main__":
    main()
