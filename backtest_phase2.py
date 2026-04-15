#!/usr/bin/env python3
"""
backtest_phase2.py — Deeper experiments on the most promising strategies.

Findings from Phase 1: Key1Win-8 had best ROI (-22.3%).
This script refines that approach with:
  1. Key1Win binned by field size
  2. Key top-2 strategies (both favorites in specific positions)
  3. Selective race filters + Key1Win
  4. Optimal K per field size
  5. Hybrid strategies (Key + value picks)
  6. Payout-weighted strategies (bet more on high-payout potential)
  7. Low-cost chalk strategies (tiny ticket counts, high selectivity)
"""

import os
import time
import warnings
from math import log, perm
from pathlib import Path
from itertools import permutations, combinations
from collections import defaultdict

import numpy as np
import pandas as pd
import xgboost as xgb

warnings.filterwarnings("ignore")

BASE = Path("/Users/maximusregent_ai/Shared/Superfecta Help")

PERM_CACHE: dict[int, np.ndarray] = {}
for _m in range(4, 21):
    PERM_CACHE[_m] = np.array(list(permutations(range(_m), 4)), dtype=np.int32)


def ml_prob(odds: float) -> float:
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return (-odds) / (-odds + 100.0)


def load_races(csv_path: Path) -> list[dict]:
    """Load CSV → list of race dicts sorted by date."""
    print(f"Loading {csv_path.name}...")
    t0 = time.time()
    df = pd.read_csv(csv_path, parse_dates=["race_date"], dtype={"post_time": str})
    df = df[df["scratch_indicator"].fillna("N") != "Y"].copy()

    races = []
    skip = defaultdict(int)

    for (track, date, rnum), grp in df.groupby(["track_id", "race_date", "race_number"]):
        wrows = grp[grp["winning_numbers"].notna()]
        if wrows.empty:
            skip["no_winner"] += 1
            continue
        wi = wrows.iloc[0]
        wp = [x.strip() for x in str(wi["winning_numbers"]).split("-")]
        if len(wp) != 4:
            skip["bad_sf"] += 1
            continue

        payoff = wi.get("payoff_amount", np.nan)
        ntix = wi.get("number_of_tickets_bet", np.nan)
        if pd.isna(payoff) or pd.isna(ntix) or payoff <= 0 or ntix <= 0:
            skip["bad_pay"] += 1
            continue
        payout = float(payoff) * (100.0 / float(ntix))

        horses = []
        for _, row in grp.iterrows():
            if pd.notna(row["odds"]):
                horses.append({
                    "prog": str(row["program_number"]).strip(),
                    "odds": float(row["odds"]),
                })
        if len(horses) < 4:
            skip["few_horses"] += 1
            continue

        for h in horses:
            h["rp"] = ml_prob(h["odds"])
        tot = sum(h["rp"] for h in horses)
        if tot <= 0:
            skip["zero_prob"] += 1
            continue
        for h in horses:
            h["p"] = h["rp"] / tot
        horses.sort(key=lambda h: h["p"], reverse=True)

        prog_set = {h["prog"] for h in horses}
        if not all(w in prog_set for w in wp):
            skip["winner_missing"] += 1
            continue

        races.append({
            "track": track.strip(),
            "date": date,
            "rnum": rnum,
            "fs": len(horses),
            "horses": horses,
            "win": wp,
            "payout": payout,
            "pool": float(wi.get("total_pool", 0)),
            "surface": str(wi.get("surface", "")).strip(),
            "course_type": str(wi.get("course_type", "")).strip(),
            "condition": str(wi.get("track_condition", "")).strip(),
            "dist": float(wi.get("distance_id", 0)),
            "purse": float(wi.get("purse_usa", 0)),
        })

    races.sort(key=lambda r: r["date"])
    print(f"  {len(races)} races loaded in {time.time() - t0:.1f}s")
    return races


# ═══════════════════════════════════════════════════════════════════
# STRATEGY CHECK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def key1_win_k(race, k):
    """Favorite wins (1st), rest from top-k."""
    if race["fs"] < k or k < 4:
        return False, 0
    fav = race["horses"][0]["prog"]
    top = {h["prog"] for h in race["horses"][:k]}
    cost = perm(k - 1, 3)
    hit = race["win"][0] == fav and all(w in top for w in race["win"])
    return hit, cost


def key2_exacta_box(race, k):
    """Top-2 favorites must be 1st AND 2nd (either order). 3rd-4th from top-k."""
    if race["fs"] < k or k < 4:
        return False, 0
    top2 = {race["horses"][0]["prog"], race["horses"][1]["prog"]}
    top_k = {h["prog"] for h in race["horses"][:k]}
    # Combos: 2 orders for top-2 in 1st-2nd, then P(k-2, 2) for 3rd-4th
    cost = 2 * (k - 2) * (k - 3)
    w = race["win"]
    hit = (w[0] in top2 and w[1] in top2 and w[0] != w[1]
           and all(wi in top_k for wi in w))
    return hit, cost


def key1_any_top4(race, k):
    """Favorite must be ANYWHERE in top 4. Rest from top-k."""
    if race["fs"] < k or k < 4:
        return False, 0
    fav = race["horses"][0]["prog"]
    top_k = {h["prog"] for h in race["horses"][:k]}
    # Combos: all 4-perms of top-k that include favorite
    total = perm(k, 4)
    without_fav = perm(k - 1, 4)
    cost = total - without_fav
    hit = fav in race["win"] and all(w in top_k for w in race["win"])
    return hit, cost


def key1_win_key2_place(race, k):
    """Fav 1st, 2nd-fav 2nd. 3rd-4th from top-k."""
    if race["fs"] < k or k < 4:
        return False, 0
    fav1 = race["horses"][0]["prog"]
    fav2 = race["horses"][1]["prog"]
    top_k = {h["prog"] for h in race["horses"][:k]}
    cost = (k - 2) * (k - 3)
    w = race["win"]
    hit = w[0] == fav1 and w[1] == fav2 and all(wi in top_k for wi in w)
    return hit, cost


def box_k(race, k):
    if race["fs"] < k or k < 4:
        return False, 0
    top = {h["prog"] for h in race["horses"][:k]}
    cost = perm(k, 4)
    return all(w in top for w in race["win"]), cost


def chalk_straight(race, n_combos):
    """Bet top-N combos by Harville probability from ALL horses.
    Uses vectorized computation."""
    m = min(race["fs"], 10)
    if m < 4:
        return False, 0

    probs = np.array([race["horses"][i]["p"] for i in range(m)])
    perms_arr = PERM_CACHE[m]

    p1 = probs[perms_arr[:, 0]]
    p2 = probs[perms_arr[:, 1]]
    p3 = probs[perms_arr[:, 2]]
    p4 = probs[perms_arr[:, 3]]
    d1 = 1 - p1
    d2 = d1 - p2
    d3 = d2 - p3
    valid = (d1 > 0) & (d2 > 0) & (d3 > 0)
    joint = np.zeros(len(perms_arr))
    joint[valid] = p1[valid] * (p2[valid] / d1[valid]) * (p3[valid] / d2[valid]) * (p4[valid] / d3[valid])

    top_idx = np.argsort(-joint)[:n_combos]
    prog_map = [race["horses"][i]["prog"] for i in range(m)]
    top_set = set()
    for idx in top_idx:
        top_set.add(tuple(prog_map[j] for j in perms_arr[idx]))

    actual_n = min(n_combos, int((joint > 0).sum()))
    return tuple(race["win"]) in top_set, actual_n


# ═══════════════════════════════════════════════════════════════════
# BACKTESTING ENGINE
# ═══════════════════════════════════════════════════════════════════

def run(races, check_fn, params, field_range=None, race_filter=None, label=""):
    by_year = defaultdict(lambda: {"n": 0, "w": 0, "ret": 0.0, "h": 0, "pays": []})
    for race in races:
        if field_range:
            lo, hi = field_range
            if race["fs"] < lo or race["fs"] > hi:
                continue
        if race_filter and not race_filter(race):
            continue
        hit, cost = check_fn(race, **params)
        if cost == 0:
            continue
        y = race["date"].year
        r = by_year[y]
        r["n"] += 1
        r["w"] += cost
        if hit:
            r["ret"] += race["payout"]
            r["h"] += 1
            r["pays"].append(race["payout"])

    rows = []
    tw, tr, th, tn = 0, 0.0, 0, 0
    for year in sorted(by_year):
        r = by_year[year]
        roi = (r["ret"] - r["w"]) / r["w"] * 100 if r["w"] > 0 else 0
        rows.append({
            "year": year, "races": r["n"], "wagered": r["w"],
            "returned": round(r["ret"], 2), "profit": round(r["ret"] - r["w"], 2),
            "roi%": round(roi, 2), "hits": r["h"],
            "hit%": round(r["h"] / r["n"] * 100, 2) if r["n"] > 0 else 0,
            "avg_pay": round(np.mean(r["pays"]), 2) if r["pays"] else 0,
        })
        tw += r["w"]
        tr += r["ret"]
        th += r["h"]
        tn += r["n"]

    roi = (tr - tw) / tw * 100 if tw > 0 else 0
    rows.append({
        "year": "TOTAL", "races": tn, "wagered": tw,
        "returned": round(tr, 2), "profit": round(tr - tw, 2),
        "roi%": round(roi, 2), "hits": th,
        "hit%": round(th / tn * 100, 2) if tn > 0 else 0,
        "avg_pay": round(tr / th, 2) if th > 0 else 0,
    })
    return pd.DataFrame(rows)


def total_row(df):
    t = df[df["year"] == "TOTAL"]
    return t.iloc[0].to_dict() if not t.empty else {}


def print_total(label, df):
    t = total_row(df)
    print(f"  {label:36s}: ROI={t.get('roi%', 0):+7.1f}%  "
          f"Hit={t.get('hit%', 0):5.1f}%  "
          f"Races={t.get('races', 0):6d}  "
          f"CostPerRace={t.get('wagered', 0) / max(t.get('races', 1), 1):7.0f}  "
          f"Profit=${t.get('profit', 0):>12,.0f}  "
          f"AvgPay=${t.get('avg_pay', 0):7.0f}")


def main():
    print("=" * 80)
    print("PHASE 2: REFINED STRATEGY EXPERIMENTS")
    print("=" * 80)

    races = load_races(BASE / "14years_major_tracks.csv")
    all_results = {}

    # ── Experiment 1: Key1Win by field size ─────────────────────
    print("\n" + "=" * 80)
    print("EXP 1: Key1Win-K binned by field size")
    print("=" * 80)

    field_bins = [(6, 7), (8, 9), (10, 11), (12, 20)]
    for lo, hi in field_bins:
        print(f"\n  Field {lo}-{hi}:")
        for k in [5, 6, 7, 8, 9, 10]:
            label = f"Key1Win-{k}_FS{lo}-{hi}"
            r = run(races, key1_win_k, {"k": k}, field_range=(lo, hi))
            all_results[label] = r
            print_total(label, r)

    # ── Experiment 2: Key top-2 strategies ──────────────────────
    print("\n" + "=" * 80)
    print("EXP 2: Key Top-2 Favorites Strategies")
    print("=" * 80)

    for k in [5, 6, 7, 8]:
        label = f"Key2-Exacta-Box{k}"
        r = run(races, key2_exacta_box, {"k": k})
        all_results[label] = r
        print_total(label, r)

    for k in [5, 6, 7, 8]:
        label = f"Key1Win-Key2Place-{k}"
        r = run(races, key1_win_key2_place, {"k": k})
        all_results[label] = r
        print_total(label, r)

    # ── Experiment 3: Favorite anywhere in top-4 ────────────────
    print("\n" + "=" * 80)
    print("EXP 3: Favorite Anywhere in Top 4")
    print("=" * 80)

    for k in [5, 6, 7, 8]:
        label = f"FavAnyTop4-{k}"
        r = run(races, key1_any_top4, {"k": k})
        all_results[label] = r
        print_total(label, r)

    # ── Experiment 4: Selective race filters + Key1Win ──────────
    print("\n" + "=" * 80)
    print("EXP 4: Selective Filters + Key1Win-8")
    print("=" * 80)

    filters = {
        # Favorite strength
        "FavProb>=0.35": lambda r: r["horses"][0]["p"] >= 0.35,
        "FavProb>=0.40": lambda r: r["horses"][0]["p"] >= 0.40,
        "FavProb>=0.45": lambda r: r["horses"][0]["p"] >= 0.45,
        "FavProb>=0.50": lambda r: r["horses"][0]["p"] >= 0.50,

        # Odds gap: big gap between fav and 2nd
        "OddsGap>=0.10": lambda r: r["horses"][0]["p"] - r["horses"][1]["p"] >= 0.10,
        "OddsGap>=0.15": lambda r: r["horses"][0]["p"] - r["horses"][1]["p"] >= 0.15,
        "OddsGap>=0.20": lambda r: r["horses"][0]["p"] - r["horses"][1]["p"] >= 0.20,

        # Pool size
        "Pool>=100K": lambda r: r["pool"] >= 100000,
        "Pool>=200K": lambda r: r["pool"] >= 200000,
        "Pool<30K": lambda r: r["pool"] < 30000,

        # Combined: strong fav + small field
        "FavStr+SmallField": lambda r: r["horses"][0]["p"] >= 0.35 and r["fs"] <= 8,
        "FavStr+MedField": lambda r: r["horses"][0]["p"] >= 0.35 and 8 < r["fs"] <= 11,
        "VeryStrFav+SmallField": lambda r: r["horses"][0]["p"] >= 0.45 and r["fs"] <= 8,

        # Surface + favorite
        "Dirt+FavStr": lambda r: r["surface"] == "D" and r["horses"][0]["p"] >= 0.35,
        "Turf+FavStr": lambda r: r["surface"] == "T" and r["horses"][0]["p"] >= 0.35,

        # Track condition
        "Muddy": lambda r: r["condition"] in ("MY", "SY", "GD", "HD"),
        "Muddy+FavStr": lambda r: r["condition"] in ("MY", "SY", "GD", "HD") and r["horses"][0]["p"] >= 0.35,

        # High purse
        "HighPurse>=200K": lambda r: r["purse"] >= 200000,
        "HighPurse>=500K": lambda r: r["purse"] >= 500000,

        # Specific tracks
        "TrackSAR": lambda r: r["track"] == "SAR",
        "TrackKEE": lambda r: r["track"] == "KEE",
        "TrackCD": lambda r: r["track"] == "CD",
        "TrackGP": lambda r: r["track"] == "GP",
        "TrackSA": lambda r: r["track"] == "SA",
    }

    for label_suffix, filt in filters.items():
        label = f"Key1Win8_{label_suffix}"
        r = run(races, key1_win_k, {"k": 8}, race_filter=filt)
        all_results[label] = r
        print_total(label, r)

    # ── Experiment 5: Very low cost chalk strategies ────────────
    print("\n" + "=" * 80)
    print("EXP 5: Low-Cost Chalk Strategies")
    print("=" * 80)

    # Chalk straight: bet only the N most probable combos
    for n in [1, 2, 3, 4, 5, 6, 10, 12]:
        label = f"ChalkStraight-{n}"
        t0 = time.time()
        r = run(races, chalk_straight, {"n_combos": n})
        dt = time.time() - t0
        all_results[label] = r
        print_total(label + f" ({dt:.0f}s)", r)

    # Key1Win with very selective K (just top-4 or top-5)
    for k in [4, 5]:
        for lo, hi in [(6, 7), (6, 8), (6, 9)]:
            label = f"Key1Win-{k}_FS{lo}-{hi}"
            r = run(races, key1_win_k, {"k": k}, field_range=(lo, hi))
            all_results[label] = r
            print_total(label, r)

    # ── Experiment 6: High-payout hunting ───────────────────────
    print("\n" + "=" * 80)
    print("EXP 6: High Payout Hunting (large field + box strategies)")
    print("=" * 80)

    # In large fields, payouts are higher. Key1Win with larger K
    for lo, hi in [(10, 12), (12, 20)]:
        for k in [8, 9, 10]:
            label = f"Key1Win-{k}_FS{lo}-{hi}"
            r = run(races, key1_win_k, {"k": k}, field_range=(lo, hi))
            all_results[label] = r
            print_total(label, r)

    # ── Experiment 7: Key1Win + EV filter via Harville analysis ─
    print("\n" + "=" * 80)
    print("EXP 7: Harville-adjusted filters")
    print("=" * 80)

    # Filter: only bet when Harville-expected payout exceeds threshold
    def make_harville_filter(min_payout_threshold):
        """Only bet when the most probable combo has Harville payout >= threshold."""
        def filt(race):
            m = min(race["fs"], 10)
            probs = [race["horses"][i]["p"] for i in range(m)]
            # Most probable combo: top-4 in order
            p1, p2, p3, p4 = probs[0], probs[1], probs[2], probs[3]
            d1, d2, d3 = 1 - p1, 1 - p1 - p2, 1 - p1 - p2 - p3
            if d1 <= 0 or d2 <= 0 or d3 <= 0:
                return False
            jp = p1 * (p2 / d1) * (p3 / d2) * (p4 / d3)
            if jp <= 0:
                return False
            h_payout = 1 / jp
            return h_payout >= min_payout_threshold
        return filt

    for thresh in [30, 50, 80, 100, 150, 200]:
        label = f"Key1Win8_MinHarv>={thresh}"
        r = run(races, key1_win_k, {"k": 8},
                race_filter=make_harville_filter(thresh))
        all_results[label] = r
        print_total(label, r)

    # ── Summary ─────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("PHASE 2 SUMMARY — Top 30 strategies by ROI")
    print("=" * 80)

    summary_rows = []
    for label, df in all_results.items():
        t = total_row(df)
        if not t or t.get("races", 0) < 500:
            continue
        summary_rows.append({
            "Strategy": label,
            "Races": int(t.get("races", 0)),
            "Wagered": int(t.get("wagered", 0)),
            "Profit": round(t.get("profit", 0), 0),
            "ROI%": t.get("roi%", 0),
            "Hits": int(t.get("hits", 0)),
            "HitRate%": t.get("hit%", 0),
            "AvgPay": round(t.get("avg_pay", 0), 0),
            "CostPerRace": round(t.get("wagered", 0) / max(t.get("races", 1), 1), 0),
        })

    summary = pd.DataFrame(summary_rows).sort_values("ROI%", ascending=False)
    print(summary.head(30).to_string(index=False))

    # Save
    summary.to_csv(BASE / "backtest_phase2_summary.csv", index=False)
    print(f"\nSaved: {BASE / 'backtest_phase2_summary.csv'}")

    # Show best per category
    print("\n--- Best by Category (min 500 races) ---")
    cats = {
        "Key1Win Field-Binned": [l for l in all_results if l.startswith("Key1Win") and "_FS" in l],
        "Key2 Exacta": [l for l in all_results if l.startswith("Key2")],
        "Selective Filter": [l for l in all_results if "Key1Win8_" in l and "_FS" not in l],
        "Chalk Straight": [l for l in all_results if l.startswith("ChalkStraight")],
        "Harville Filter": [l for l in all_results if "MinHarv" in l],
    }
    for cat_name, labels in cats.items():
        candidates = []
        for l in labels:
            t = total_row(all_results[l])
            if t and t.get("races", 0) >= 500:
                candidates.append((l, t.get("roi%", -100)))
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_l, best_roi = candidates[0]
            t = total_row(all_results[best_l])
            print(f"  {cat_name:24s}: {best_l:40s} ROI={best_roi:+.1f}%  "
                  f"Races={t.get('races', 0)}  AvgPay=${t.get('avg_pay', 0):.0f}")

    return all_results, summary


if __name__ == "__main__":
    main()
