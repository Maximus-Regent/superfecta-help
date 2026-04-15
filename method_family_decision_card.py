#!/usr/bin/env python3
"""
Create a compact method-family comparison card.

Goal:
- line up Harville, the XGBoost correction path, and the strongest selective rule path
- keep the comparison honest about evidence scope
- make it easy to retire dead-end modeling paths in reports
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
COMPARE_MAIN = BASE / "compare_main_approaches.csv"
BACKTEST_SUMMARY = BASE / "backtest_summary.csv"
AB_RESULTS = BASE / "ab_downstream_comparison_results.json"
OUT_CSV = BASE / "method_family_decision_card.csv"
OUT_MD = BASE / "METHOD_FAMILY_DECISION.md"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def pct(value: float) -> str:
    return f"{value:.2f}%"


def signed_pct(value: float) -> str:
    return f"{value:+.2f}%"


def build_rows() -> list[dict[str, Any]]:
    compare_rows = load_csv(COMPARE_MAIN)
    compare_by_id = {row["method_id"]: row for row in compare_rows}
    selective = compare_by_id["phase7_live_portfolio"]

    backtest_rows = load_csv(BACKTEST_SUMMARY)
    harville = next(row for row in backtest_rows if row["Strategy"] == "Harville-Top120")
    ml_rows = [row for row in backtest_rows if row["Strategy"].startswith("ML-")]
    best_ml = max(ml_rows, key=lambda row: float(row["ROI%"]))

    ab = json.loads(AB_RESULTS.read_text(encoding="utf-8"))
    baseline = ab["prediction_accuracy"]["baseline"]
    enriched = ab["prediction_accuracy"]["enriched"]
    ev_base = ab["ev_engine_comparison"]["baseline"]
    ev_enriched = ab["ev_engine_comparison"]["enriched"]
    test_set = ab["test_set"]

    payout_rmse_reduction_pct = (1.0 - enriched["payout_rmse"] / baseline["payout_rmse"]) * 100.0
    log_rmse_reduction_pct = (1.0 - enriched["log_ratio_rmse"] / baseline["log_ratio_rmse"]) * 100.0

    rows = [
        {
            "family_id": "selective_rule_path",
            "label": "Selective rule path",
            "role": "PAPER NOW",
            "primary_metric": float(selective["holdout_roi"]),
            "primary_metric_label": "2024-2025 holdout ROI",
            "primary_sample": int(float(selective["holdout_races"])),
            "secondary_metric": float(selective["wf_roi"]),
            "secondary_metric_label": "walk-forward ROI",
            "secondary_sample": int(float(selective["wf_races"])),
            "evidence_scope": "frozen holdout + walk-forward",
            "why": (
                "Only family here with positive current frozen holdout evidence and a live paper-trade path. "
                "In the current holdout, this is effectively the OP+CD basket, with OP_DURABLE_K7 still the safest anchor."
            ),
            "note": selective["note"],
        },
        {
            "family_id": "harville_ranked",
            "label": "Harville-ranked probabilities",
            "role": "BENCHMARK ONLY",
            "primary_metric": float(harville["ROI%"]),
            "primary_metric_label": "broad backtest ROI",
            "primary_sample": int(float(harville["Races"])),
            "secondary_metric": float(harville["HitRate%"]),
            "secondary_metric_label": "hit rate",
            "secondary_sample": int(float(harville["Races"])),
            "evidence_scope": "2010-2025 broad backtest",
            "why": (
                "Large-sample structural benchmark, not a live candidate. The hit rate is high, but the ROI stays deeply negative, "
                "which means ranking order by Harville probability alone does not beat takeout."
            ),
            "note": "Best broad Harville line in BACKTEST_REPORT.md: Harville-Top120.",
        },
        {
            "family_id": "xgboost_residual",
            "label": "XGBoost residual correction",
            "role": "RESEARCH ONLY",
            "primary_metric": float(best_ml["ROI%"]),
            "primary_metric_label": f"best ML betting ROI ({best_ml['Strategy']})",
            "primary_sample": int(float(best_ml["Races"])),
            "secondary_metric": payout_rmse_reduction_pct,
            "secondary_metric_label": "matched-model payout RMSE reduction vs current baseline",
            "secondary_sample": int(test_set["n_races"]),
            "evidence_scope": "broad backtest + matched downstream A/B",
            "why": (
                "The model can improve payout prediction a bit without creating a betting edge. "
                f"In the matched downstream test, payout RMSE was reduced by {pct(payout_rmse_reduction_pct)} and log-ratio RMSE was reduced by {pct(log_rmse_reduction_pct)}, "
                f"but EV winner pass counts barely moved ({ev_base['ev_pass_count']} baseline vs {ev_enriched['ev_pass_count']} enriched on {test_set['n_races']} test winners)."
            ),
            "note": (
                f"Best ML family line in backtest_summary.csv is still negative ({best_ml['Strategy']} = {signed_pct(float(best_ml['ROI%']))} on {best_ml['Races']} races)."
            ),
        },
    ]
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "family_id",
        "label",
        "role",
        "primary_metric_label",
        "primary_metric",
        "primary_sample",
        "secondary_metric_label",
        "secondary_metric",
        "secondary_sample",
        "evidence_scope",
        "why",
        "note",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def render_md(rows: list[dict[str, Any]]) -> str:
    selective = next(row for row in rows if row["family_id"] == "selective_rule_path")
    harville = next(row for row in rows if row["family_id"] == "harville_ranked")
    xgb = next(row for row in rows if row["family_id"] == "xgboost_residual")

    lines = [
        "# Method Family Decision Card",
        "",
        "This note compares the three method families that matter most for honest deployment decisions:",
        "**Harville-ranked probabilities, the current XGBoost correction path, and the selective rule path.**",
        "",
        "Short answer:",
        "- **Paper trade the selective rule path**",
        "- **Keep Harville as a benchmark only**",
        "- **Keep XGBoost as research, not as a betting decision engine**",
        "",
        "## Comparison Table",
        "",
        "| Method Family | Role | Primary Evidence | Sample | Secondary Evidence | Why It Sits Here |",
        "|---|---|---:|---:|---:|---|",
    ]

    for row in rows:
        primary = f"{signed_pct(float(row['primary_metric']))} ({row['primary_metric_label']})"
        secondary_label = row["secondary_metric_label"]
        secondary_value = signed_pct(float(row["secondary_metric"])) if "ROI" in secondary_label else pct(float(row["secondary_metric"]))
        lines.append(
            f"| {row['label']} | {row['role']} | {primary} | {int(row['primary_sample'])} | {secondary_value} ({secondary_label}) | {row['why']} |"
        )

    lines.extend([
        "",
        "## Why This Ordering Is Conservative",
        "",
        f"- **{selective['label']} ({selective['role']})**: {selective['why']}",
        f"  - Practical note: {selective['note']}",
        f"- **{harville['label']} ({harville['role']})**: {harville['why']}",
        f"  - Practical note: {harville['note']}",
        f"- **{xgb['label']} ({xgb['role']})**: {xgb['why']}",
        f"  - Practical note: {xgb['note']}",
        "",
        "## Why This Is Not an Apples-to-Apples ROI Contest",
        "",
        "- The **selective rule path** has earned the strongest current deployment evidence, because it is the only family here with positive frozen 2024-2025 holdout results plus a live paper-trade workflow.",
        "- The **Harville** and **XGBoost** families are judged by their best honest family-level evidence instead of by a fresh 2024-2025 holdout replay, because they already fail on much larger historical samples and never earned a positive deployment case.",
        "- That asymmetry is acceptable here because the question is practical, not academic: **what should Cole still treat as live-worthy?** The answer is the selective rule path, not the generic ranking/modeling families.",
        "",
        "## Bottom Line",
        "",
        "If Cole wants one clean method-level hierarchy right now:",
        "",
        "1. **Selective rule path**: keep as the only paper-trade family",
        "2. **Harville-ranked probabilities**: keep as a structural benchmark, not a live strategy",
        "3. **XGBoost residual correction**: keep as model research only, because prediction gains have not translated into betting gains",
        "",
        "This card is intentionally blunt. It should make it easier to stop revisiting dead-end method families every time a modest model metric improves.",
        "",
        "## Validation",
        "",
        "- Sources: `compare_main_approaches.csv`, `backtest_summary.csv`, `ab_downstream_comparison_results.json`",
        "- Wrote: `method_family_decision_card.csv`, `METHOD_FAMILY_DECISION.md`",
        "- This card is a read-only synthesis of existing frozen artifacts and comparison outputs",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    rows = build_rows()
    write_csv(OUT_CSV, rows)
    OUT_MD.write_text(render_md(rows), encoding="utf-8")
    print(f"Wrote {OUT_CSV.name} and {OUT_MD.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
