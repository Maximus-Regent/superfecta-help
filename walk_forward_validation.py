#!/usr/bin/env python3
"""
Concrete walk-forward validation with train-only rule selection.

What this does:
- Reuses the existing race cache and promoted Phase 7 / Phase 8 rule artifacts.
- Selects rules only on years strictly before the test year.
- Tests the selected portfolio on the next year.
- Emits diagnostics that explicitly surface overfitting risk, unstable years,
  sparse coverage, payout concentration, and the BEL vs BAQ coverage break.

Important limitation:
- This is a pragmatic next validation step, not a full historical re-search.
- The candidate universe still comes from previously mined rules, so the
  walk-forward remains somewhat optimistic versus a true from-scratch
  train-only search each year.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from math import perm
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path("/Users/maximusregent_ai/Shared/Superfecta Help")
CACHE_PATH = BASE / "phase5_race_cache.pkl"
PHASE7_RULES_PATH = BASE / "phase7_live_rules.json"

OUT_FOLDS = BASE / "walk_forward_validation_folds.csv"
OUT_RULES = BASE / "walk_forward_validation_rules.csv"
OUT_REPORT = BASE / "WALK_FORWARD_VALIDATION.md"

MIN_TRAIN_YEARS = 5
MAX_PORTFOLIO_RULES = 3

MIN_TRAIN_RACES = 40
MIN_ACTIVE_TRAIN_YEARS = 4
MIN_POSITIVE_YEAR_RATIO = 0.50
MAX_TOP1_SHARE = 0.55
MAX_TOP3_SHARE = 0.85


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


@dataclass(frozen=True)
class Rule:
    rule_id: str
    source: str
    track_group: str
    tracks: tuple[str, ...]
    k: int
    field_min: int
    field_max: int
    gap_min: float
    fav_prob_min: float
    condition: str
    card_min: int
    months: tuple[int, ...] = ()
    top2_mass_min: float | None = None
    alias_mode: str = "strict"

    @property
    def cost(self) -> int:
        return perm(self.k - 1, 3)


def load_data() -> pd.DataFrame:
    df = pd.read_pickle(CACHE_PATH).copy()
    df["second_prob"] = df["fav_prob"] - df["prob_gap"]
    df["top2_mass"] = df["fav_prob"] + df["second_prob"]
    return df


def load_phase7_rules() -> list[dict]:
    payload = json.loads(PHASE7_RULES_PATH.read_text())
    return payload["rules"]


def normalize_rule(rule: dict, source: str) -> Rule:
    track_group = "BEL_FAMILY" if rule["track"] == "BEL" else rule["track"]
    return Rule(
        rule_id=rule["rule_id"],
        source=source,
        track_group=track_group,
        tracks=(rule["track"],),
        k=int(rule["k"]),
        field_min=int(rule["field_min"]),
        field_max=int(rule["field_max"]),
        gap_min=float(rule["gap_min"]),
        fav_prob_min=float(rule["fav_prob_min"]),
        condition=rule["condition"],
        card_min=int(rule["card_min"]),
        months=tuple(int(m) for m in rule.get("months", [])),
        top2_mass_min=(
            float(rule["top2_mass_min"]) if rule.get("top2_mass_min") is not None else None
        ),
        alias_mode="strict",
    )


def bel_baq_bridge(rule: Rule) -> Rule:
    return Rule(
        rule_id=f"{rule.rule_id}_BRIDGE_BAQ",
        source=f"{rule.source}_bridge",
        track_group=rule.track_group,
        tracks=("BEL", "BAQ"),
        k=rule.k,
        field_min=rule.field_min,
        field_max=rule.field_max,
        gap_min=rule.gap_min,
        fav_prob_min=rule.fav_prob_min,
        condition=rule.condition,
        card_min=rule.card_min,
        months=rule.months,
        top2_mass_min=rule.top2_mass_min,
        alias_mode="bel_baq_bridge",
    )


def build_candidate_rules() -> list[Rule]:
    rules: list[Rule] = []
    seen: set[str] = set()

    for raw in load_phase7_rules():
        rule = normalize_rule(raw, "phase7_live")
        if rule.rule_id not in seen:
            rules.append(rule)
            seen.add(rule.rule_id)
        if rule.tracks == ("BEL",):
            bridge = bel_baq_bridge(rule)
            rules.append(bridge)
            seen.add(bridge.rule_id)

    for raw in PHASE8_FROZEN_RULES:
        rule = normalize_rule(raw, "phase8_frozen")
        if rule.rule_id not in seen:
            rules.append(rule)
            seen.add(rule.rule_id)
        if rule.tracks == ("BEL",):
            bridge = bel_baq_bridge(rule)
            if bridge.rule_id not in seen:
                rules.append(bridge)
                seen.add(bridge.rule_id)

    return rules


def build_mask(df: pd.DataFrame, rule: Rule) -> np.ndarray:
    mask = df["track"].isin(rule.tracks).to_numpy()
    mask &= df[f"eligible_{rule.k}"].to_numpy(dtype=bool)
    fs = df["fs"].to_numpy(dtype=np.int16)
    mask &= (fs >= rule.field_min) & (fs <= rule.field_max)
    mask &= df["prob_gap"].to_numpy(dtype=np.float64) >= rule.gap_min
    mask &= df["fav_prob"].to_numpy(dtype=np.float64) >= rule.fav_prob_min

    if rule.condition == "fast":
        mask &= df["is_fast"].to_numpy(dtype=bool)

    mask &= df["rnum"].to_numpy(dtype=np.int16) >= rule.card_min

    if rule.months:
        mask &= np.isin(df["month"].to_numpy(dtype=np.int16), np.array(rule.months))

    if rule.top2_mass_min is not None:
        mask &= df["top2_mass"].to_numpy(dtype=np.float64) >= rule.top2_mass_min

    return mask


def evaluate_subset(mask: np.ndarray, hit: np.ndarray, payout: np.ndarray, cost: int) -> dict:
    races = int(mask.sum())
    if races == 0:
        return {
            "races": 0,
            "hits": 0,
            "wagered": 0,
            "returned": 0.0,
            "profit": 0.0,
            "roi": 0.0,
            "hit_rate": 0.0,
        }

    hit_mask = mask & hit
    hits = int(hit_mask.sum())
    wagered = races * cost
    returned = float(payout[hit_mask].sum())
    profit = returned - wagered
    roi = profit / wagered * 100.0 if wagered else 0.0
    hit_rate = hits / races * 100.0
    return {
        "races": races,
        "hits": hits,
        "wagered": wagered,
        "returned": round(returned, 2),
        "profit": round(profit, 2),
        "roi": round(roi, 2),
        "hit_rate": round(hit_rate, 2),
    }


def concentration_stats(mask: np.ndarray, hit: np.ndarray, payout: np.ndarray) -> dict:
    returns = payout[mask & hit]
    if returns.size == 0:
        return {
            "top1_share": 0.0,
            "top3_share": 0.0,
            "max_hit": 0.0,
        }

    total_return = float(returns.sum())
    sorted_returns = np.sort(returns)[::-1]
    top1 = float(sorted_returns[:1].sum()) / total_return
    top3 = float(sorted_returns[:3].sum()) / total_return
    return {
        "top1_share": round(top1, 4),
        "top3_share": round(top3, 4),
        "max_hit": round(float(sorted_returns[0]), 2),
    }


def yearly_stats(mask: np.ndarray, hit: np.ndarray, payout: np.ndarray, year: np.ndarray, cost: int) -> dict:
    years = sorted(int(y) for y in np.unique(year[mask]))
    rows = []
    for y in years:
        stats = evaluate_subset(mask & (year == y), hit, payout, cost)
        rows.append({"year": y, **stats})

    if not rows:
        return {
            "active_years": 0,
            "positive_years": 0,
            "pos_year_ratio": 0.0,
            "median_year_roi": 0.0,
            "worst_year_roi": 0.0,
            "avg_races_per_active_year": 0.0,
        }

    roi_values = np.array([row["roi"] for row in rows], dtype=np.float64)
    positive_years = int(np.sum(roi_values > 0))
    active_years = len(rows)
    return {
        "active_years": active_years,
        "positive_years": positive_years,
        "pos_year_ratio": round(positive_years / active_years, 4),
        "median_year_roi": round(float(np.median(roi_values)), 2),
        "worst_year_roi": round(float(np.min(roi_values)), 2),
        "avg_races_per_active_year": round(float(np.mean([row["races"] for row in rows])), 2),
    }


def train_rule_diagnostics(
    rule: Rule,
    base_mask: np.ndarray,
    year_arr: np.ndarray,
    payout: np.ndarray,
    hit: np.ndarray,
    test_year: int,
    bridge_mask: np.ndarray | None,
) -> dict:
    train_mask = base_mask & (year_arr < test_year)
    test_mask = base_mask & (year_arr == test_year)
    train_stats = evaluate_subset(train_mask, hit, payout, rule.cost)
    test_stats = evaluate_subset(test_mask, hit, payout, rule.cost)
    train_yearly = yearly_stats(train_mask, hit, payout, year_arr, rule.cost)
    concentration = concentration_stats(train_mask, hit, payout)

    sparse_flag = train_stats["races"] < MIN_TRAIN_RACES or train_yearly["active_years"] < MIN_ACTIVE_TRAIN_YEARS
    unstable_flag = train_yearly["pos_year_ratio"] < MIN_POSITIVE_YEAR_RATIO
    concentrated_flag = (
        concentration["top1_share"] > MAX_TOP1_SHARE or concentration["top3_share"] > MAX_TOP3_SHARE
    )

    score = (
        max(train_stats["roi"], 0.0)
        * min(1.0, train_stats["races"] / 150.0)
        * train_yearly["pos_year_ratio"]
        * min(1.0, train_yearly["active_years"] / 8.0)
        * max(0.1, 1.0 - max(0.0, concentration["top1_share"] - 0.30))
        * max(0.1, 1.0 - max(0.0, concentration["top3_share"] - 0.55))
    )

    strict_zero_but_bridge_has_coverage = False
    if rule.alias_mode == "strict" and rule.tracks == ("BEL",) and bridge_mask is not None:
        strict_zero_but_bridge_has_coverage = bool(
            test_stats["races"] == 0 and int((bridge_mask & (year_arr == test_year)).sum()) > 0
        )

    qualifies = not sparse_flag and not unstable_flag and not concentrated_flag and train_stats["roi"] > 0

    return {
        "test_year": test_year,
        "rule_id": rule.rule_id,
        "source": rule.source,
        "track_group": rule.track_group,
        "tracks": ",".join(rule.tracks),
        "alias_mode": rule.alias_mode,
        "k": rule.k,
        "cost_per_race": rule.cost,
        "train_races": train_stats["races"],
        "train_hits": train_stats["hits"],
        "train_wagered": train_stats["wagered"],
        "train_profit": train_stats["profit"],
        "train_roi": train_stats["roi"],
        "train_hit_rate": train_stats["hit_rate"],
        "active_train_years": train_yearly["active_years"],
        "positive_train_years": train_yearly["positive_years"],
        "positive_train_year_ratio": train_yearly["pos_year_ratio"],
        "median_train_year_roi": train_yearly["median_year_roi"],
        "worst_train_year_roi": train_yearly["worst_year_roi"],
        "avg_races_per_train_year": train_yearly["avg_races_per_active_year"],
        "train_top1_share": concentration["top1_share"],
        "train_top3_share": concentration["top3_share"],
        "train_max_hit": concentration["max_hit"],
        "sparse_flag": sparse_flag,
        "unstable_flag": unstable_flag,
        "concentrated_flag": concentrated_flag,
        "strict_zero_but_bridge_has_coverage": strict_zero_but_bridge_has_coverage,
        "qualifies": qualifies,
        "alias_preference": 1 if rule.alias_mode == "bel_baq_bridge" else 0,
        "selection_score": round(score, 4),
        "test_races": test_stats["races"],
        "test_hits": test_stats["hits"],
        "test_wagered": test_stats["wagered"],
        "test_profit": test_stats["profit"],
        "test_roi": test_stats["roi"],
        "test_hit_rate": test_stats["hit_rate"],
    }


def select_rules_for_fold(rule_rows: pd.DataFrame) -> pd.DataFrame:
    eligible = rule_rows.loc[rule_rows["qualifies"]].copy()
    if eligible.empty:
        eligible = rule_rows.loc[rule_rows["train_roi"] > 0].copy()

    eligible = eligible.sort_values(
        ["selection_score", "alias_preference", "train_races", "positive_train_year_ratio"],
        ascending=[False, False, False, False],
    )

    chosen = []
    used_groups: set[str] = set()
    for _, row in eligible.iterrows():
        if row["track_group"] in used_groups:
            continue
        chosen.append(row)
        used_groups.add(row["track_group"])
        if len(chosen) >= MAX_PORTFOLIO_RULES:
            break

    if not chosen and not rule_rows.empty:
        chosen = [rule_rows.sort_values("selection_score", ascending=False).iloc[0]]

    return pd.DataFrame(chosen)


def portfolio_stats_from_masks(
    masks: list[np.ndarray],
    hits: list[np.ndarray],
    payout: np.ndarray,
    year_mask: np.ndarray,
    costs: list[int],
) -> dict:
    total_races = 0
    total_hits = 0
    total_wagered = 0
    total_returned = 0.0

    for mask, hit, cost in zip(masks, hits, costs):
        stats = evaluate_subset(mask & year_mask, hit, payout, cost)
        total_races += stats["races"]
        total_hits += stats["hits"]
        total_wagered += stats["wagered"]
        total_returned += stats["returned"]

    profit = total_returned - total_wagered
    roi = profit / total_wagered * 100.0 if total_wagered else 0.0
    hit_rate = total_hits / total_races * 100.0 if total_races else 0.0
    return {
        "races": total_races,
        "hits": total_hits,
        "wagered": total_wagered,
        "returned": round(total_returned, 2),
        "profit": round(profit, 2),
        "roi": round(roi, 2),
        "hit_rate": round(hit_rate, 2),
    }


def fixed_portfolio_rules(candidate_rules: list[Rule], source: str) -> list[Rule]:
    return [rule for rule in candidate_rules if rule.source == source and rule.alias_mode == "strict"]


def evaluate_fixed_portfolio(df: pd.DataFrame, rules: list[Rule], test_years: list[int]) -> dict:
    payout = df["payout"].to_numpy(dtype=np.float64)
    year_arr = df["year"].to_numpy(dtype=np.int16)
    masks = [build_mask(df, rule) for rule in rules]
    hits = [df[f"hit_{rule.k}"].to_numpy(dtype=bool) for rule in rules]
    costs = [rule.cost for rule in rules]

    rows = []
    for test_year in test_years:
        stats = portfolio_stats_from_masks(masks, hits, payout, year_arr == test_year, costs)
        rows.append({"year": test_year, **stats})

    result = pd.DataFrame(rows)
    totals = {
        "years": len(result),
        "positive_years": int((result["roi"] > 0).sum()),
        "races": int(result["races"].sum()),
        "wagered": int(result["wagered"].sum()),
        "returned": round(float(result["returned"].sum()), 2),
        "profit": round(float(result["profit"].sum()), 2),
    }
    totals["roi"] = round(totals["profit"] / totals["wagered"] * 100.0, 2) if totals["wagered"] else 0.0
    return totals


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def format_pct(value: float) -> str:
    return f"{value:+.2f}%"


def build_report(
    folds: pd.DataFrame,
    rules: pd.DataFrame,
    candidate_rules: list[Rule],
    strict_bel_holdout: dict,
    bridge_bel_holdout: dict,
    fixed_phase7: dict,
    fixed_phase8: dict,
) -> str:
    selected = rules.loc[rules["selected"]].copy()
    total = {
        "years": int(folds["test_year"].nunique()),
        "positive_years": int((folds["test_roi"] > 0).sum()),
        "races": int(folds["test_races"].sum()),
        "wagered": int(folds["test_wagered"].sum()),
        "returned": round(float(folds["test_returned"].sum()), 2),
        "profit": round(float(folds["test_profit"].sum()), 2),
    }
    total["roi"] = round(total["profit"] / total["wagered"] * 100.0, 2) if total["wagered"] else 0.0

    avg_rules = round(float(folds["selected_rule_count"].mean()), 2)
    sparse_hits = int(selected["sparse_flag"].sum())
    unstable_hits = int(selected["unstable_flag"].sum())
    concentrated_hits = int(selected["concentrated_flag"].sum())
    bel_breaks = int(rules["strict_zero_but_bridge_has_coverage"].sum())

    selection_counts = (
        selected.groupby("rule_id")
        .size()
        .sort_values(ascending=False)
        .reset_index(name="folds_selected")
    )

    unstable_years = folds.loc[folds["test_roi"] <= 0, ["test_year", "selected_rule_ids", "test_races", "test_profit", "test_roi"]]
    selected_view = selected[
        [
            "test_year",
            "rule_id",
            "train_races",
            "train_roi",
            "positive_train_year_ratio",
            "train_top1_share",
            "train_top3_share",
            "test_races",
            "test_roi",
        ]
    ].sort_values(["test_year", "rule_id"])

    lines = [
        "# Walk-Forward Validation",
        "",
        "## What This Is",
        "",
        "- Candidate universe: existing promoted rules from `phase7_live_rules.json` and the frozen Phase 8 rules.",
        "- Selection logic: for each test year, score and select rules using only prior years.",
        "- Test logic: evaluate the selected portfolio on the next year only.",
        "- Limitation: this is still not a true from-scratch yearly rediscovery loop; the candidate universe was originally mined from historical full-sample work.",
        "",
        "## Guardrails",
        "",
        f"- Minimum train races: {MIN_TRAIN_RACES}",
        f"- Minimum active train years: {MIN_ACTIVE_TRAIN_YEARS}",
        f"- Minimum positive-year ratio: {MIN_POSITIVE_YEAR_RATIO:.0%}",
        f"- Maximum top-1 payout share: {MAX_TOP1_SHARE:.0%}",
        f"- Maximum top-3 payout share: {MAX_TOP3_SHARE:.0%}",
        f"- Maximum portfolio size: {MAX_PORTFOLIO_RULES} rules, one per track group",
        "",
        "## Train-Only Walk-Forward Result",
        "",
        f"- Test years: {total['years']}",
        f"- Positive test years: {total['positive_years']}/{total['years']}",
        f"- Total races: {total['races']}",
        f"- Total wagered: {format_currency(total['wagered'])}",
        f"- Total profit: {format_currency(total['profit'])}",
        f"- Total ROI: {format_pct(total['roi'])}",
        f"- Average selected rules per fold: {avg_rules}",
        "",
        "## Full-Sample-Mined Portfolio Comparison",
        "",
        f"- Fixed Phase 7 live portfolio over the same test years: {format_pct(fixed_phase7['roi'])} ROI on {fixed_phase7['races']} races, {fixed_phase7['positive_years']}/{fixed_phase7['years']} positive years.",
        f"- Fixed Phase 8 frozen portfolio over the same test years: {format_pct(fixed_phase8['roi'])} ROI on {fixed_phase8['races']} races, {fixed_phase8['positive_years']}/{fixed_phase8['years']} positive years.",
        f"- Train-only selection result: {format_pct(total['roi'])} ROI on {total['races']} races, {total['positive_years']}/{total['years']} positive years.",
        "",
        "## BEL vs BAQ Coverage Break",
        "",
        f"- Strict BEL broad rule in 2024-2025: {strict_bel_holdout['races']} races, {format_pct(strict_bel_holdout['roi'])} ROI.",
        f"- BEL->BAQ bridge variant in 2024-2025: {bridge_bel_holdout['races']} races, {format_pct(bridge_bel_holdout['roi'])} ROI.",
        f"- Strict BEL zero-coverage folds where the bridge would have had action: {bel_breaks}.",
        "- Takeaway: aliasing fixes the coverage break, but it does not rescue the economics. BAQ did not behave like a hidden continuation of the BEL edge here.",
        "",
        "## Guardrail Diagnostics",
        "",
        f"- Selected-rule sparse flags: {sparse_hits}",
        f"- Selected-rule unstable-year flags: {unstable_hits}",
        f"- Selected-rule payout-concentration flags: {concentrated_hits}",
        "- The selection CSV shows which candidates were blocked by each guardrail in each fold.",
        "",
        "## Most Selected Rules",
        "",
    ]

    if selection_counts.empty:
        lines.append("- No rules were selected.")
    else:
        for row in selection_counts.itertuples(index=False):
            lines.append(f"- {row.rule_id}: selected in {row.folds_selected} folds")

    lines.extend(
        [
            "",
            "## Unstable Test Years",
            "",
        ]
    )

    if unstable_years.empty:
        lines.append("- None. Every walk-forward year was positive.")
    else:
        for row in unstable_years.itertuples(index=False):
            lines.append(
                f"- {row.test_year}: {format_pct(row.test_roi)} ROI on {row.test_races} races, "
                f"{format_currency(row.test_profit)} profit, rules = {row.selected_rule_ids}"
            )

    lines.extend(
        [
            "",
            "## Selected Rule Snapshot",
            "",
            "| Year | Rule | Train Races | Train ROI | Pos Year Ratio | Top1 Share | Top3 Share | Test Races | Test ROI |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for row in selected_view.itertuples(index=False):
        lines.append(
            f"| {row.test_year} | {row.rule_id} | {row.train_races} | {format_pct(row.train_roi)} | "
            f"{row.positive_train_year_ratio:.0%} | {row.train_top1_share:.0%} | "
            f"{row.train_top3_share:.0%} | {row.test_races} | {format_pct(row.test_roi)} |"
        )

    blunt_take = (
        "The edge looks weaker under real train-only selection than the full-sample writeups suggest. "
        "It is still positive in aggregate, but the durable part is basically OP plus occasional help from "
        "CD/KEE, while BEL disappears and the BAQ bridge loses badly."
    )
    if total["roi"] <= 0:
        blunt_take = (
            "The edge does not look durable once rule choice is restricted to train-only data. "
            "The historical edge was mostly a full-sample mining artifact."
        )

    lines.extend(
        [
            "",
            "## Blunt Takeaway",
            "",
            blunt_take,
            "",
            f"Artifacts written: `{OUT_FOLDS.name}`, `{OUT_RULES.name}`, `{OUT_REPORT.name}`.",
            f"Candidate rules evaluated: {len(candidate_rules)}.",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> None:
    df = load_data()
    candidate_rules = build_candidate_rules()

    payout = df["payout"].to_numpy(dtype=np.float64)
    year_arr = df["year"].to_numpy(dtype=np.int16)
    unique_years = sorted(int(y) for y in np.unique(year_arr))
    test_years = unique_years[MIN_TRAIN_YEARS:]

    rule_masks = {rule.rule_id: build_mask(df, rule) for rule in candidate_rules}
    rule_hits = {rule.rule_id: df[f"hit_{rule.k}"].to_numpy(dtype=bool) for rule in candidate_rules}

    folds_rows: list[dict] = []
    rule_rows: list[dict] = []

    bel_bridge_lookup = {
        rule.rule_id.replace("_BRIDGE_BAQ", ""): rule_masks[rule.rule_id]
        for rule in candidate_rules
        if rule.alias_mode == "bel_baq_bridge"
    }

    for test_year in test_years:
        per_rule = []
        for rule in candidate_rules:
            bridge_mask = None
            if rule.alias_mode == "strict" and rule.rule_id in bel_bridge_lookup:
                bridge_mask = bel_bridge_lookup[rule.rule_id]
            diag = train_rule_diagnostics(
                rule=rule,
                base_mask=rule_masks[rule.rule_id],
                year_arr=year_arr,
                payout=payout,
                hit=rule_hits[rule.rule_id],
                test_year=test_year,
                bridge_mask=bridge_mask,
            )
            per_rule.append(diag)

        fold_rule_df = pd.DataFrame(per_rule)
        selected = select_rules_for_fold(fold_rule_df)
        selected_ids = set(selected["rule_id"]) if not selected.empty else set()

        fold_rule_df["selected"] = fold_rule_df["rule_id"].isin(selected_ids)
        rule_rows.extend(fold_rule_df.to_dict(orient="records"))

        selected_rules = [rule for rule in candidate_rules if rule.rule_id in selected_ids]
        masks = [rule_masks[rule.rule_id] for rule in selected_rules]
        hits = [rule_hits[rule.rule_id] for rule in selected_rules]
        costs = [rule.cost for rule in selected_rules]

        train_stats = portfolio_stats_from_masks(masks, hits, payout, year_arr < test_year, costs)
        test_stats = portfolio_stats_from_masks(masks, hits, payout, year_arr == test_year, costs)

        folds_rows.append(
            {
                "test_year": test_year,
                "selected_rule_count": len(selected_rules),
                "selected_rule_ids": ",".join(selected["rule_id"].tolist()),
                "train_races": train_stats["races"],
                "train_hits": train_stats["hits"],
                "train_wagered": train_stats["wagered"],
                "train_returned": train_stats["returned"],
                "train_profit": train_stats["profit"],
                "train_roi": train_stats["roi"],
                "test_races": test_stats["races"],
                "test_hits": test_stats["hits"],
                "test_wagered": test_stats["wagered"],
                "test_returned": test_stats["returned"],
                "test_profit": test_stats["profit"],
                "test_roi": test_stats["roi"],
            }
        )

    folds_df = pd.DataFrame(folds_rows)
    rules_df = pd.DataFrame(rule_rows)

    phase7_strict = fixed_portfolio_rules(candidate_rules, "phase7_live")
    phase8_strict = fixed_portfolio_rules(candidate_rules, "phase8_frozen")
    fixed_phase7 = evaluate_fixed_portfolio(df, phase7_strict, test_years)
    fixed_phase8 = evaluate_fixed_portfolio(df, phase8_strict, test_years)

    strict_bel = next(rule for rule in candidate_rules if rule.rule_id == "BEL_BROAD1_K7" and rule.alias_mode == "strict")
    bridge_bel = next(rule for rule in candidate_rules if rule.rule_id == "BEL_BROAD1_K7_BRIDGE_BAQ")

    strict_bel_holdout = evaluate_subset(
        rule_masks[strict_bel.rule_id] & np.isin(year_arr, np.array([2024, 2025])),
        rule_hits[strict_bel.rule_id],
        payout,
        strict_bel.cost,
    )
    bridge_bel_holdout = evaluate_subset(
        rule_masks[bridge_bel.rule_id] & np.isin(year_arr, np.array([2024, 2025])),
        rule_hits[bridge_bel.rule_id],
        payout,
        bridge_bel.cost,
    )

    folds_df.to_csv(OUT_FOLDS, index=False)
    rules_df.to_csv(OUT_RULES, index=False)

    report = build_report(
        folds=folds_df,
        rules=rules_df,
        candidate_rules=candidate_rules,
        strict_bel_holdout=strict_bel_holdout,
        bridge_bel_holdout=bridge_bel_holdout,
        fixed_phase7=fixed_phase7,
        fixed_phase8=fixed_phase8,
    )
    OUT_REPORT.write_text(report)

    print(f"Wrote {OUT_FOLDS.name}")
    print(f"Wrote {OUT_RULES.name}")
    print(f"Wrote {OUT_REPORT.name}")


if __name__ == "__main__":
    main()
