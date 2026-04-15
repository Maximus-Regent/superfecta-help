#!/usr/bin/env python3
"""
Portfolio-level decision card for the current superfecta deployment choices.

Purpose:
- Put the main portfolio-level approaches in one report-safe artifact.
- Keep the decision anchored to the frozen 2024-2025 holdout plus walk-forward context.
- Separate the operational default from research challengers and validation benchmarks.

Outputs:
- portfolio_decision_card.csv
- PORTFOLIO_DECISION_CARD.md
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
COMPARE_PATH = BASE / "compare_main_approaches.csv"
FROZEN_EVAL_PATH = BASE / "frozen_portfolio_eval_summary.csv"
WF_FOLDS_PATH = BASE / "walk_forward_validation_folds.csv"
OUT_CSV = BASE / "portfolio_decision_card.csv"
OUT_MD = BASE / "PORTFOLIO_DECISION_CARD.md"

TARGET_METHODS = [
    "phase7_live_portfolio",
    "phase8_frozen_portfolio",
    "train_only_selector",
]


def fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    compare_df = pd.read_csv(COMPARE_PATH)
    frozen_df = pd.read_csv(FROZEN_EVAL_PATH)
    wf_df = pd.read_csv(WF_FOLDS_PATH)
    return compare_df, frozen_df, wf_df


def get_frozen_portfolio_row(frozen_df: pd.DataFrame, portfolio_name: str, slice_name: str) -> pd.Series:
    match = frozen_df[
        (frozen_df["level"] == "portfolio")
        & (frozen_df["name"] == portfolio_name)
        & (frozen_df["slice"] == slice_name)
    ]
    if match.empty:
        raise ValueError(f"Missing frozen eval row for {portfolio_name} / {slice_name}")
    return match.iloc[0]


def get_selector_year_roi(wf_df: pd.DataFrame, year: int) -> float:
    match = wf_df[wf_df["test_year"] == year]
    if match.empty:
        raise ValueError(f"Missing walk-forward fold row for {year}")
    return float(match.iloc[0]["test_roi"])


def current_role(method_id: str) -> str:
    mapping = {
        "phase7_live_portfolio": "PAPER NOW",
        "phase8_frozen_portfolio": "SHADOW ONLY",
        "train_only_selector": "BENCHMARK",
    }
    return mapping[method_id]


def short_label(method_id: str, label: str) -> str:
    mapping = {
        "phase7_live_portfolio": "Phase 7 live portfolio",
        "phase8_frozen_portfolio": "Phase 8 frozen portfolio",
        "train_only_selector": label,
    }
    return mapping[method_id]


def decision_reason(method_id: str, row: pd.Series) -> str:
    if method_id == "phase7_live_portfolio":
        return (
            f"Best current paper baseline because it has the strongest 2024-2025 holdout result "
            f"({fmt_pct(float(row['holdout_roi']))} on {int(row['holdout_races'])} races). "
            f"BEL is dormant here, so the active holdout is effectively the OP+CD portfolio."
        )
    if method_id == "phase8_frozen_portfolio":
        return (
            f"Useful challenger, but it underperformed Phase 7 on holdout "
            f"({fmt_pct(float(row['holdout_roi']))} vs {fmt_pct(float(row['phase7_holdout_roi']))}) "
            f"despite adding more mined rules and more weak legs."
        )
    if method_id == "train_only_selector":
        return (
            f"Most honest validation benchmark, not the best live default. Its walk-forward ROI is still valuable context "
            f"({fmt_pct(float(row['wf_roi']))} on {int(row['wf_races'])} races), but its current 2024-2025 holdout is only "
            f"{fmt_pct(float(row['holdout_roi']))} on {int(row['holdout_races'])} races."
        )
    raise ValueError(method_id)


def operational_read(method_id: str) -> str:
    if method_id == "phase7_live_portfolio":
        return "Use as the primary paper-trade basket if Cole wants one frozen portfolio today."
    if method_id == "phase8_frozen_portfolio":
        return "Track as a shadow basket, not as the default, until it beats Phase 7 on more forward data."
    if method_id == "train_only_selector":
        return "Keep as the honest benchmark for reports and sanity checks, not as the daily operating recipe."
    raise ValueError(method_id)


def caution(method_id: str) -> str:
    if method_id == "phase7_live_portfolio":
        return "2024 was basically flat (+0.37%), so this is still volatile even though the two-year holdout is strongest overall."
    if method_id == "phase8_frozen_portfolio":
        return "Its better walk-forward headline is not enough to offset the weaker current holdout and the negative holdout legs inside the basket."
    if method_id == "train_only_selector":
        return "Some historical folds used the old BEL bridge candidate, so it should stay a benchmark artifact rather than a clean deployment rulebook."
    raise ValueError(method_id)


def build_dataframe() -> pd.DataFrame:
    compare_df, frozen_df, wf_df = load_inputs()
    compare_df = compare_df[compare_df["method_id"].isin(TARGET_METHODS)].copy().set_index("method_id")

    phase7_holdout_roi = float(compare_df.loc["phase7_live_portfolio", "holdout_roi"])
    phase7_holdout_races = int(compare_df.loc["phase7_live_portfolio", "holdout_races"])

    phase7_2024 = get_frozen_portfolio_row(frozen_df, "phase7_live", "year_2024")
    phase7_2025 = get_frozen_portfolio_row(frozen_df, "phase7_live", "year_2025")
    phase8_2024 = get_frozen_portfolio_row(frozen_df, "phase8_frozen", "year_2024")
    phase8_2025 = get_frozen_portfolio_row(frozen_df, "phase8_frozen", "year_2025")

    selector_2024_roi = get_selector_year_roi(wf_df, 2024)
    selector_2025_roi = get_selector_year_roi(wf_df, 2025)

    year_map = {
        "phase7_live_portfolio": (float(phase7_2024["roi"]), float(phase7_2025["roi"])),
        "phase8_frozen_portfolio": (float(phase8_2024["roi"]), float(phase8_2025["roi"])),
        "train_only_selector": (selector_2024_roi, selector_2025_roi),
    }

    rows: list[dict] = []
    for method_id in TARGET_METHODS:
        row = compare_df.loc[method_id]
        holdout_2024_roi, holdout_2025_roi = year_map[method_id]

        enriched = pd.Series(
            {
                **row.to_dict(),
                "holdout_2024_roi": holdout_2024_roi,
                "holdout_2025_roi": holdout_2025_roi,
                "phase7_holdout_roi": phase7_holdout_roi,
            }
        )

        rows.append(
            {
                "method_id": method_id,
                "label": short_label(method_id, str(row["label"])),
                "role": current_role(method_id),
                "method_type": row["method_type"],
                "holdout_roi": float(row["holdout_roi"]),
                "holdout_races": int(row["holdout_races"]),
                "holdout_hits": int(row["holdout_hits"]),
                "holdout_profit": float(row["holdout_profit"]),
                "holdout_2024_roi": holdout_2024_roi,
                "holdout_2025_roi": holdout_2025_roi,
                "holdout_positive_years": f"{int(row['holdout_positive_years'])}/{int(row['holdout_observed_years'])}",
                "wf_roi": float(row["wf_roi"]),
                "wf_races": int(row["wf_races"]),
                "wf_positive_years": f"{int(row['wf_positive_years'])}/{int(row['wf_observed_years'])}",
                "score": float(row["score"]),
                "holdout_roi_vs_phase7": round(float(row["holdout_roi"]) - phase7_holdout_roi, 2),
                "holdout_races_vs_phase7": int(row["holdout_races"]) - phase7_holdout_races,
                "decision_reason": decision_reason(method_id, enriched),
                "operational_read": operational_read(method_id),
                "caution": caution(method_id),
                "note": row["note"],
            }
        )

    df = pd.DataFrame(rows)
    role_order = {"PAPER NOW": 0, "SHADOW ONLY": 1, "BENCHMARK": 2}
    df["sort_order"] = df["role"].map(role_order)
    df = df.sort_values(["sort_order", "holdout_races"], ascending=[True, False]).reset_index(drop=True)
    return df.drop(columns=["sort_order"])


def build_markdown(df: pd.DataFrame) -> str:
    lines = [
        "# Portfolio Decision Card",
        "",
        "This note compares the three portfolio-level choices that matter most right now:",
        "the **Phase 7 live portfolio**, the **Phase 8 frozen portfolio**, and the **train-only yearly selector**.",
        "",
        "Short answer:",
        "- **Paper trade the Phase 7 live portfolio first**",
        "- **Keep the Phase 8 frozen portfolio as a shadow challenger, not the default**",
        "- **Use the train-only yearly selector as an honest benchmark, not as the operating recipe**",
        "",
        "## Comparison Table",
        "",
        "| Approach | Role | Holdout ROI | Holdout Races | 2024 ROI | 2025 ROI | WF ROI | WF Races | WF Years+ | Why It Sits Here |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for _, row in df.iterrows():
        lines.append(
            f"| {row['label']} | {row['role']} | {fmt_pct(float(row['holdout_roi']))} | {int(row['holdout_races'])} | "
            f"{fmt_pct(float(row['holdout_2024_roi']))} | {fmt_pct(float(row['holdout_2025_roi']))} | "
            f"{fmt_pct(float(row['wf_roi']))} | {int(row['wf_races'])} | {row['wf_positive_years']} | {row['decision_reason']} |"
        )

    lines.extend(
        [
            "",
            "## Why This Ordering Is Conservative",
            "",
        ]
    )

    for _, row in df.iterrows():
        lines.append(f"- **{row['label']} ({row['role']})**: {row['operational_read']}")
        lines.append(f"  - Why: {row['decision_reason']}")
        lines.append(f"  - Caution: {row['caution']}")

    lines.extend(
        [
            "",
            "## Head-to-Head vs. Phase 7",
            "",
            "| Approach | Holdout ROI vs Phase 7 | Holdout Races vs Phase 7 | Practical Read |",
            "|---|---:|---:|---|",
        ]
    )

    for _, row in df[df["method_id"] != "phase7_live_portfolio"].iterrows():
        lines.append(
            f"| {row['label']} | {fmt_pct(float(row['holdout_roi_vs_phase7']))} | {int(row['holdout_races_vs_phase7'])} | {row['operational_read']} |"
        )

    lines.extend(
        [
            "",
            "## Bottom Line",
            "",
            "If Cole wants one portfolio-level decision tonight:",
            "",
            "1. **Run the Phase 7 live portfolio as the primary paper baseline**",
            "2. **Log the Phase 8 frozen portfolio separately as a shadow basket**",
            "3. **Keep citing the train-only yearly selector as the honest validation yardstick**",
            "",
            "That ordering keeps the live choice tied to the strongest current holdout result instead of to the prettiest mined basket or the most abstract validation artifact.",
            "",
            "## Validation",
            "",
            f"- Sources: `{COMPARE_PATH.name}`, `{FROZEN_EVAL_PATH.name}`, `{WF_FOLDS_PATH.name}`",
            f"- Wrote: `{OUT_CSV.name}`, `{OUT_MD.name}`",
            "- This card is a read-only synthesis of frozen evaluation artifacts",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    df = build_dataframe()
    df.to_csv(OUT_CSV, index=False)
    OUT_MD.write_text(build_markdown(df) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_CSV}")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
