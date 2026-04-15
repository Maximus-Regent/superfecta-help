#!/usr/bin/env python3
"""
Cross-family decision card for the current live-paper shortlist.

Purpose:
- Put the three most relevant active rules in one place:
  OP_DURABLE_K7, CD_CORE_K8, OP_REFINED_K7.
- Keep the comparison anchored to 2024-2025 holdout plus walk-forward context.
- Explain why the current roles are anchor / paper / watch in plain language.

Outputs:
- cross_family_decision_card.csv
- CROSS_FAMILY_DECISION.md
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
SCORECARD_PATH = BASE / "forward_evidence_scorecard.csv"
FROZEN_EVAL_PATH = BASE / "frozen_portfolio_eval_summary.csv"
OUT_CSV = BASE / "cross_family_decision_card.csv"
OUT_MD = BASE / "CROSS_FAMILY_DECISION.md"

TARGET_RULES = ["OP_DURABLE_K7", "CD_CORE_K8", "OP_REFINED_K7"]


def fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    score_df = pd.read_csv(SCORECARD_PATH)
    frozen_df = pd.read_csv(FROZEN_EVAL_PATH)
    return score_df, frozen_df


def get_rule_slice(frozen_df: pd.DataFrame, rule_id: str, slice_name: str) -> pd.Series:
    match = frozen_df[
        (frozen_df["level"] == "rule")
        & (frozen_df["name"] == rule_id)
        & (frozen_df["slice"] == slice_name)
    ]
    if match.empty:
        raise ValueError(f"Missing frozen eval row for {rule_id} / {slice_name}")
    return match.iloc[0]


def current_role(rule_id: str) -> str:
    mapping = {
        "OP_DURABLE_K7": "ANCHOR",
        "CD_CORE_K8": "PAPER",
        "OP_REFINED_K7": "WATCH",
    }
    return mapping[rule_id]


def family(rule_id: str) -> str:
    if rule_id.startswith("OP_"):
        return "OP"
    if rule_id.startswith("CD_"):
        return "CD"
    return "OTHER"


def decision_reason(rule_id: str, row: pd.Series) -> str:
    if rule_id == "OP_DURABLE_K7":
        return (
            f"Safest anchor because it has the largest active holdout sample ({int(row['holdout_races'])}) "
            f"and the strongest walk-forward selection frequency ({int(row['wf_selected_count'])}/{int(row['wf_total_folds'])})."
        )
    if rule_id == "CD_CORE_K8":
        return (
            f"Paper now because holdout is positive in both years ({fmt_pct(float(row['holdout_2024_roi']))}, "
            f"{fmt_pct(float(row['holdout_2025_roi']))}), but the forward sample is still smaller than the OP anchor "
            f"and walk-forward selection is only {int(row['wf_selected_count'])}/{int(row['wf_total_folds'])}."
        )
    if rule_id == "OP_REFINED_K7":
        return (
            f"Watch only because the ROI is attractive, but the holdout sample is only {int(row['holdout_races'])} races "
            f"and 2024 was a losing year ({fmt_pct(float(row['holdout_2024_roi']))})."
        )
    raise ValueError(rule_id)


def family_caution(rule_id: str) -> str:
    if rule_id == "OP_DURABLE_K7":
        return "OP is the strongest current family, but the refined OP variant still lacks enough forward sample to replace this anchor."
    if rule_id == "CD_CORE_K8":
        return "CD family caution: the more selective CD_REFINED_K9 looked better in-sample but lost on 2024-2025 holdout, so keep the simpler CD rule on paper only."
    if rule_id == "OP_REFINED_K7":
        return "Interesting OP challenger, but still not strong enough to displace the durable OP rule."
    raise ValueError(rule_id)


def build_dataframe() -> pd.DataFrame:
    score_df, frozen_df = load_inputs()
    score_df = score_df[score_df["rule_id"].isin(TARGET_RULES)].copy()
    score_df = score_df.set_index("rule_id")

    anchor_holdout_races = int(score_df.loc["OP_DURABLE_K7", "holdout_races"])
    anchor_wf_selected = int(score_df.loc["OP_DURABLE_K7", "wf_selected_count"])
    anchor_holdout_roi = float(score_df.loc["OP_DURABLE_K7", "holdout_roi"])

    rows: list[dict] = []
    for rule_id in TARGET_RULES:
        row = score_df.loc[rule_id]
        year_2024 = get_rule_slice(frozen_df, rule_id, "year_2024")
        year_2025 = get_rule_slice(frozen_df, rule_id, "year_2025")

        holdout_roi = float(row["holdout_roi"])
        holdout_races = int(row["holdout_races"])
        wf_selected_count = int(row["wf_selected_count"])
        wf_total_folds = int(row["wf_total_folds"])

        rows.append(
            {
                "rule_id": rule_id,
                "family": family(rule_id),
                "phase": row["phase"],
                "role": current_role(rule_id),
                "holdout_roi": holdout_roi,
                "holdout_races": holdout_races,
                "holdout_profit": float(row["holdout_profit"]),
                "holdout_2024_roi": float(year_2024["roi"]),
                "holdout_2025_roi": float(year_2025["roi"]),
                "holdout_years_positive": row["holdout_years"],
                "holdout_worst_year_roi": float(row["worst_year_roi"]),
                "wf_selected_count": wf_selected_count,
                "wf_total_folds": wf_total_folds,
                "wf_selected": row["wf_selected"],
                "ci_lower": float(row["ci_lower"]) if pd.notna(row["ci_lower"]) else None,
                "backtest_roi": float(row["backtest_roi"]),
                "backtest_races": int(row["backtest_races"]),
                "forward_trust": float(row["forward_trust"]),
                "scorecard_tier": row["tier"],
                "holdout_roi_vs_anchor": round(holdout_roi - anchor_holdout_roi, 2),
                "holdout_races_vs_anchor": holdout_races - anchor_holdout_races,
                "wf_selected_vs_anchor": wf_selected_count - anchor_wf_selected,
                "decision_reason": decision_reason(rule_id, pd.Series({
                    **row.to_dict(),
                    "holdout_2024_roi": float(year_2024["roi"]),
                    "holdout_2025_roi": float(year_2025["roi"]),
                })),
                "family_caution": family_caution(rule_id),
                "note": row["note"],
            }
        )

    df = pd.DataFrame(rows)
    role_order = {"ANCHOR": 0, "PAPER": 1, "WATCH": 2}
    df["sort_order"] = df["role"].map(role_order)
    df = df.sort_values(["sort_order", "holdout_races"], ascending=[True, False]).reset_index(drop=True)
    return df.drop(columns=["sort_order"])


def build_markdown(df: pd.DataFrame) -> str:
    lines = [
        "# Cross-Family Decision Card",
        "",
        "This note compares the three most relevant active rules for current live-paper use:",
        "`OP_DURABLE_K7`, `CD_CORE_K8`, and `OP_REFINED_K7`.",
        "",
        "Short answer:",
        "- **Keep `OP_DURABLE_K7` as the anchor**",
        "- **Paper trade `CD_CORE_K8`, but do not let it replace the anchor yet**",
        "- **Keep `OP_REFINED_K7` on watch, not as a promoted live default**",
        "",
        "## Comparison Table",
        "",
        "| Rule | Family | Role | Holdout ROI | Holdout Races | 2024 ROI | 2025 ROI | Holdout Years+ | WF Selected | CI Lower | Why It Sits Here |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for _, row in df.iterrows():
        ci = "n/a" if pd.isna(row["ci_lower"]) else fmt_pct(float(row["ci_lower"]))
        lines.append(
            f"| {row['rule_id']} | {row['family']} | {row['role']} | {fmt_pct(float(row['holdout_roi']))} | "
            f"{int(row['holdout_races'])} | {fmt_pct(float(row['holdout_2024_roi']))} | {fmt_pct(float(row['holdout_2025_roi']))} | "
            f"{row['holdout_years_positive']} | {row['wf_selected']} | {ci} | {row['decision_reason']} |"
        )

    lines.extend(
        [
            "",
            "## Why the Current Roles Make Sense",
            "",
        ]
    )

    for _, row in df.iterrows():
        lines.append(f"- **{row['rule_id']} ({row['role']})**: {row['decision_reason']}")
        lines.append(f"  - Family caution: {row['family_caution']}")

    lines.extend(
        [
            "",
            "## Head-to-Head vs. the Anchor",
            "",
            "| Rule | Holdout ROI vs Anchor | Holdout Races vs Anchor | WF Selected vs Anchor | Practical Read |",
            "|---|---:|---:|---:|---|",
        ]
    )

    for _, row in df[df["rule_id"] != "OP_DURABLE_K7"].iterrows():
        if row["rule_id"] == "CD_CORE_K8":
            practical = "Better holdout ROI than the anchor, but on only 60 races and with much weaker walk-forward selection."
        else:
            practical = "Higher ROI than the anchor, but smaller sample and still includes a losing holdout year."
        lines.append(
            f"| {row['rule_id']} | {fmt_pct(float(row['holdout_roi_vs_anchor']))} | {int(row['holdout_races_vs_anchor'])} | "
            f"{int(row['wf_selected_vs_anchor'])} | {practical} |"
        )

    lines.extend(
        [
            "",
            "## Bottom Line",
            "",
            "If Cole wants one clean live-paper hierarchy right now:",
            "",
            "1. **Anchor:** `OP_DURABLE_K7`",
            "2. **Paper alongside it:** `CD_CORE_K8`",
            "3. **Watch / shadow only:** `OP_REFINED_K7`",
            "",
            "That ordering is intentionally conservative. It protects against promoting the prettiest small-sample ROI line over the strongest forward-evidence anchor.",
            "",
            "## Validation",
            "",
            f"- Sources: `{SCORECARD_PATH.name}`, `{FROZEN_EVAL_PATH.name}`",
            f"- Wrote: `{OUT_CSV.name}`, `{OUT_MD.name}`",
            "- This card is a read-only synthesis of existing frozen evaluation artifacts",
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
