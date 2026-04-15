#!/usr/bin/env python3
"""
Quick evaluation harness — one command to compare rule portfolios.

Loads the race cache once, then runs:
  1. Frozen holdout evaluation (2024-2025)
  2. Walk-forward selection frequency
  3. Forward evidence scoring

against both the baseline Phase 7 portfolio and an optional custom rules file.

Usage:
    python quick_eval.py                       # baseline only
    python quick_eval.py --custom my_rules.json  # baseline vs custom side-by-side
    python quick_eval.py --rule-tweak OP_DURABLE_K7 gap_min=0.08  # tweak one param

The custom JSON must have the same shape as phase7_live_rules.json (a "rules" list).
Each rule dict needs: rule_id, track, k, field_min, field_max, gap_min, fav_prob_min,
condition, card_min.  Optional: months, top2_mass_min.

Anchored to the frozen honest evaluation standard:
  - 2024-2025 holdout, walk-forward, forward evidence over headline ROI
  - OP focus, no BEL/BAQ aliasing
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from math import perm
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
CACHE_PATH = BASE / "phase5_race_cache.pkl"
PHASE7_RULES_PATH = BASE / "phase7_live_rules.json"
WF_FOLDS_PATH = BASE / "walk_forward_validation_folds.csv"

HOLDOUT_YEARS = [2024, 2025]
TRAIN_END_YEAR = 2023
MIN_TRAIN_YEARS = 5


# ---------------------------------------------------------------------------
# Data loading (one-time)
# ---------------------------------------------------------------------------

def load_data() -> pd.DataFrame:
    df = pd.read_pickle(CACHE_PATH).copy()
    df["second_prob"] = df["fav_prob"] - df["prob_gap"]
    df["top2_mass"] = df["fav_prob"] + df["second_prob"]
    return df


def load_phase7_rules() -> list[dict]:
    with PHASE7_RULES_PATH.open() as f:
        return json.load(f)["rules"]


def normalize_rule(rule: dict) -> dict:
    return {
        "rule_id": rule["rule_id"],
        "track": rule["track"],
        "k": int(rule["k"]),
        "field_min": int(rule["field_min"]),
        "field_max": int(rule["field_max"]),
        "gap_min": float(rule["gap_min"]),
        "fav_prob_min": float(rule["fav_prob_min"]),
        "condition": rule.get("condition", "all"),
        "card_min": int(rule.get("card_min", 1)),
        "months": rule.get("months"),
        "top2_mass_min": rule.get("top2_mass_min"),
    }


# ---------------------------------------------------------------------------
# Mask building + evaluation (shared with evaluate_frozen_portfolios.py)
# ---------------------------------------------------------------------------

def build_mask(df: pd.DataFrame, rule: dict) -> np.ndarray:
    mask = df["track"].to_numpy() == rule["track"]
    mask &= df[f"eligible_{rule['k']}"].to_numpy(dtype=bool)
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


def eval_mask(mask: np.ndarray, hit: np.ndarray, payout: np.ndarray, cost: int) -> dict:
    n = int(mask.sum())
    if n == 0:
        return {"races": 0, "hits": 0, "wagered": 0, "returned": 0.0, "profit": 0.0, "roi": 0.0, "hit_rate": 0.0}
    h = mask & hit
    hits = int(h.sum())
    wagered = n * cost
    returned = float(payout[h].sum())
    profit = returned - wagered
    roi = profit / wagered * 100.0 if wagered else 0.0
    hit_rate = hits / n * 100.0
    return {"races": n, "hits": hits, "wagered": wagered, "returned": round(returned, 2),
            "profit": round(profit, 2), "roi": round(roi, 2), "hit_rate": round(hit_rate, 2)}


# ---------------------------------------------------------------------------
# Portfolio evaluation
# ---------------------------------------------------------------------------

def evaluate_portfolio(df: pd.DataFrame, rules: list[dict], label: str) -> dict:
    payout = df["payout"].to_numpy(dtype=np.float64)
    year_arr = df["year"].to_numpy(dtype=np.int16)

    compiled = []
    for rule in rules:
        mask = build_mask(df, rule)
        hit = df[f"hit_{rule['k']}"].to_numpy(dtype=bool)
        cost = perm(rule["k"] - 1, 3)
        compiled.append({"rule": rule, "mask": mask, "hit": hit, "cost": cost})

    slices = {
        "full": np.ones(len(df), dtype=bool),
        f"train_2010_{TRAIN_END_YEAR}": year_arr <= TRAIN_END_YEAR,
        "holdout": np.isin(year_arr, HOLDOUT_YEARS),
    }

    result = {"label": label, "rules": [r["rule_id"] for r in rules]}

    # Portfolio-level stats for each slice
    for slice_name, year_mask in slices.items():
        total_w, total_r, total_h, total_n = 0, 0.0, 0, 0
        for item in compiled:
            m = item["mask"] & year_mask
            s = eval_mask(m, item["hit"], payout, item["cost"])
            total_w += s["wagered"]
            total_r += s["returned"]
            total_h += s["hits"]
            total_n += s["races"]
        profit = total_r - total_w
        roi = profit / total_w * 100.0 if total_w else 0.0
        hr = total_h / total_n * 100.0 if total_n else 0.0
        result[slice_name] = {
            "races": total_n, "profit": round(profit, 2),
            "roi": round(roi, 2), "hit_rate": round(hr, 2),
        }

    # Per-rule holdout breakdown
    rule_details = []
    holdout_mask = slices["holdout"]
    for item in compiled:
        m = item["mask"] & holdout_mask
        s = eval_mask(m, item["hit"], payout, item["cost"])
        rule_details.append({
            "rule_id": item["rule"]["rule_id"],
            "holdout_races": s["races"],
            "holdout_roi": s["roi"],
            "holdout_profit": s["profit"],
        })
    result["rule_holdout"] = rule_details

    # Yearly holdout breakdown
    yearly = []
    for y in HOLDOUT_YEARS:
        y_mask = year_arr == y
        total_w, total_r, total_n = 0, 0.0, 0
        for item in compiled:
            m = item["mask"] & y_mask
            s = eval_mask(m, item["hit"], payout, item["cost"])
            total_w += s["wagered"]
            total_r += s["returned"]
            total_n += s["races"]
        profit = total_r - total_w
        roi = profit / total_w * 100.0 if total_w else 0.0
        yearly.append({"year": y, "races": total_n, "profit": round(profit, 2), "roi": round(roi, 2)})
    result["yearly_holdout"] = yearly

    return result


# ---------------------------------------------------------------------------
# Walk-forward selection frequency (from existing artifacts)
# ---------------------------------------------------------------------------

def wf_selection_freq() -> dict[str, tuple[int, int]]:
    if not WF_FOLDS_PATH.exists():
        return {}
    df = pd.read_csv(WF_FOLDS_PATH)
    total_folds = len(df)
    freq: dict[str, int] = {}
    for rule_ids in df["selected_rule_ids"]:
        for rid in str(rule_ids).split(","):
            rid = rid.strip()
            if rid:
                freq[rid] = freq.get(rid, 0) + 1
    return {k: (v, total_folds) for k, v in freq.items()}


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def fmt_currency(v: float) -> str:
    return f"${v:,.0f}"


def fmt_pct(v: float) -> str:
    return f"{v:+.1f}%"


def print_portfolio(result: dict, wf_freq: dict[str, tuple[int, int]]) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {result['label']}")
    print(f"  Rules: {', '.join(result['rules'])}")
    print(f"{'=' * 70}")

    for slice_name in ["full", f"train_2010_{TRAIN_END_YEAR}", "holdout"]:
        s = result[slice_name]
        tag = {"full": "Full sample", f"train_2010_{TRAIN_END_YEAR}": "Train 2010-2023", "holdout": "Holdout 2024-2025"}[slice_name]
        print(f"  {tag:20s}  {s['races']:>5} races  {fmt_pct(s['roi']):>8} ROI  {fmt_currency(s['profit']):>10} profit  {s['hit_rate']:.1f}% hit")

    print(f"\n  Per-rule holdout:")
    for rd in result["rule_holdout"]:
        wf = wf_freq.get(rd["rule_id"])
        wf_str = f"  WF {wf[0]}/{wf[1]}" if wf else ""
        print(f"    {rd['rule_id']:24s}  {rd['holdout_races']:>4} races  {fmt_pct(rd['holdout_roi']):>8} ROI  {fmt_currency(rd['holdout_profit']):>10}{wf_str}")

    print(f"\n  Yearly holdout:")
    for yd in result["yearly_holdout"]:
        print(f"    {yd['year']}  {yd['races']:>4} races  {fmt_pct(yd['roi']):>8} ROI  {fmt_currency(yd['profit']):>10}")


def print_comparison(baseline: dict, custom: dict) -> None:
    print(f"\n{'=' * 70}")
    print(f"  SIDE-BY-SIDE COMPARISON (holdout 2024-2025)")
    print(f"{'=' * 70}")

    bh = baseline["holdout"]
    ch = custom["holdout"]
    print(f"  {'Metric':20s}  {'Baseline':>12}  {'Custom':>12}  {'Delta':>10}")
    print(f"  {'-' * 58}")
    print(f"  {'Races':20s}  {bh['races']:>12}  {ch['races']:>12}  {ch['races'] - bh['races']:>+10}")
    print(f"  {'ROI':20s}  {fmt_pct(bh['roi']):>12}  {fmt_pct(ch['roi']):>12}  {fmt_pct(ch['roi'] - bh['roi']):>10}")
    print(f"  {'Profit':20s}  {fmt_currency(bh['profit']):>12}  {fmt_currency(ch['profit']):>12}  {fmt_currency(ch['profit'] - bh['profit']):>10}")
    print(f"  {'Hit rate':20s}  {bh['hit_rate']:.1f}%{' ' * 7}  {ch['hit_rate']:.1f}%{' ' * 7}  {ch['hit_rate'] - bh['hit_rate']:>+.1f}%")

    # Per-rule diff
    baseline_rules = {r["rule_id"]: r for r in baseline["rule_holdout"]}
    custom_rules = {r["rule_id"]: r for r in custom["rule_holdout"]}
    all_rule_ids = list(dict.fromkeys(list(baseline_rules) + list(custom_rules)))

    if all_rule_ids:
        print(f"\n  Per-rule holdout delta:")
        for rid in all_rule_ids:
            br = baseline_rules.get(rid, {"holdout_races": 0, "holdout_roi": 0, "holdout_profit": 0})
            cr = custom_rules.get(rid, {"holdout_races": 0, "holdout_roi": 0, "holdout_profit": 0})
            delta_r = cr["holdout_races"] - br["holdout_races"]
            delta_roi = cr["holdout_roi"] - br["holdout_roi"]
            tag = ""
            if rid not in baseline_rules:
                tag = " [NEW]"
            elif rid not in custom_rules:
                tag = " [REMOVED]"
            elif delta_r != 0 or abs(delta_roi) > 0.01:
                tag = f" [{delta_r:+d} races, {fmt_pct(delta_roi)} ROI]"
            else:
                tag = " [unchanged]"
            print(f"    {rid:24s}{tag}")


# ---------------------------------------------------------------------------
# Rule tweaking
# ---------------------------------------------------------------------------

def apply_tweaks(rules: list[dict], tweaks: list[str]) -> list[dict]:
    """Apply inline parameter tweaks: 'RULE_ID param=value param2=value2'."""
    rules = copy.deepcopy(rules)
    # Parse tweaks: first token is rule_id, rest are key=value pairs
    i = 0
    while i < len(tweaks):
        target_id = tweaks[i]
        i += 1
        params: dict[str, str] = {}
        while i < len(tweaks) and "=" in tweaks[i]:
            k, v = tweaks[i].split("=", 1)
            params[k] = v
            i += 1

        found = False
        for rule in rules:
            if rule["rule_id"] == target_id:
                for k, v in params.items():
                    if k in ("k", "field_min", "field_max", "card_min"):
                        rule[k] = int(v)
                    elif k in ("gap_min", "fav_prob_min", "top2_mass_min"):
                        rule[k] = float(v)
                    elif k == "condition":
                        rule[k] = v
                    elif k == "months":
                        rule[k] = [int(x) for x in v.split(",")]
                    else:
                        rule[k] = v
                found = True
                break

        if not found:
            print(f"WARNING: Rule '{target_id}' not found in baseline. Tweak skipped.")

    return rules


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Quick evaluation: compare rule portfolios in one pass",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s                                           # baseline Phase 7 only
  %(prog)s --custom my_rules.json                    # compare custom vs baseline
  %(prog)s --rule-tweak OP_DURABLE_K7 gap_min=0.08   # tweak one param
  %(prog)s --rule-tweak OP_DURABLE_K7 gap_min=0.08 field_min=10
  %(prog)s --rule-tweak OP_DURABLE_K7 gap_min=0.08 --rule-tweak CD_CORE_K8 card_min=5
""",
    )
    p.add_argument("--custom", help="Path to custom rules JSON (same format as phase7_live_rules.json)")
    p.add_argument("--rule-tweak", nargs="+", action="append", default=[],
                   help="Inline tweak: RULE_ID param=value [param2=value2 ...]. Can repeat.")
    p.add_argument("--quiet", action="store_true", help="Only print comparison table, not full details")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    t0 = time.time()
    print("Loading race cache...", end=" ", flush=True)
    df = load_data()
    print(f"done ({len(df):,} races, {time.time() - t0:.1f}s)")

    wf_freq = wf_selection_freq()
    baseline_rules = [normalize_rule(r) for r in load_phase7_rules()]

    # Evaluate baseline
    t1 = time.time()
    baseline = evaluate_portfolio(df, baseline_rules, "Phase 7 Baseline")
    if not args.quiet:
        print_portfolio(baseline, wf_freq)
    print(f"\nBaseline eval: {time.time() - t1:.2f}s")

    # Evaluate custom portfolio if provided
    custom_result = None
    if args.custom:
        with open(args.custom) as f:
            custom_raw = json.load(f)
        custom_rules = [normalize_rule(r) for r in custom_raw["rules"]]
        t2 = time.time()
        custom_result = evaluate_portfolio(df, custom_rules, f"Custom ({Path(args.custom).name})")
        if not args.quiet:
            print_portfolio(custom_result, wf_freq)
        print(f"Custom eval: {time.time() - t2:.2f}s")

    elif args.rule_tweak:
        # Flatten the nested list from action="append"
        flat_tweaks: list[str] = []
        for group in args.rule_tweak:
            flat_tweaks.extend(group)

        custom_rules = apply_tweaks(baseline_rules, flat_tweaks)
        tweak_desc = " ".join(flat_tweaks)
        t2 = time.time()
        custom_result = evaluate_portfolio(df, custom_rules, f"Tweaked ({tweak_desc})")
        if not args.quiet:
            print_portfolio(custom_result, wf_freq)
        print(f"Tweak eval: {time.time() - t2:.2f}s")

    if custom_result:
        print_comparison(baseline, custom_result)

    print(f"\nTotal: {time.time() - t0:.2f}s")
    print("\nAnchored to frozen standard: 2024-2025 holdout, walk-forward, forward evidence over headline ROI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
