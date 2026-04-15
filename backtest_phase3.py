#!/usr/bin/env python3
"""
backtest_phase3.py — Phase 3: Squeeze remaining edge from current data.

Building on Phase 1-2 findings:
  Best strategy: Key1Win-8 at -13.5% (KEE only), -15.7% (CD only), -16.6% (FS10-11)
  Gap to breakeven: ~15-20% improvement needed in hit rate or avg payout.

Phase 3 experiments:
  3A: Track × field-size interactions
  3B: Seasonality / month / meet-specific strategies
  3C: Distance (sprint vs route) filters
  3D: Card position (race number) filters
  3E: Multi-filter stacking (combinatorial search over atomic filters)
  3F: Dynamic K (adjust number of horses based on probability concentration)
  3G: Henery-adjusted combo ordering (replace Harville with alpha-calibration)
  3H: Favorite post-position filter
  3I: Out-of-sample validation (2010-2018 train / 2019-2025 test)
"""

import time
import warnings
from math import perm
from pathlib import Path
from itertools import permutations, combinations
from collections import defaultdict

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path("/Users/maximusregent_ai/Shared/Superfecta Help")

# Pre-compute permutation arrays for Henery combo ordering
PERM_CACHE: dict[int, np.ndarray] = {}
for _m in range(4, 15):
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
                    "pp": int(row["post_position"]) if pd.notna(row.get("post_position")) else 0,
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

        # Compute probability entropy for dynamic-K
        probs = np.array([h["p"] for h in horses])
        entropy = -np.sum(probs * np.log(probs + 1e-12))

        # Distance bucket
        dist = float(wi.get("distance_id", 0))
        if dist <= 700:
            dist_cat = "sprint"
        elif dist <= 850:
            dist_cat = "route_mid"
        else:
            dist_cat = "route_long"

        races.append({
            "track": track.strip(),
            "date": date,
            "year": date.year,
            "month": date.month,
            "rnum": rnum,
            "fs": len(horses),
            "horses": horses,
            "win": wp,
            "payout": payout,
            "pool": float(wi.get("total_pool", 0)),
            "surface": str(wi.get("surface", "")).strip(),
            "course_type": str(wi.get("course_type", "")).strip(),
            "condition": str(wi.get("track_condition", "")).strip(),
            "dist": dist,
            "dist_cat": dist_cat,
            "purse": float(wi.get("purse_usa", 0)),
            "entropy": entropy,
            "fav_prob": probs[0],
            "fav_pp": horses[0]["pp"],
            "prob_gap": probs[0] - probs[1] if len(probs) > 1 else 0,
        })

    races.sort(key=lambda r: r["date"])
    print(f"  {len(races)} races loaded in {time.time() - t0:.1f}s")
    for k, v in sorted(skip.items()):
        print(f"    skipped {k}: {v}")
    return races


# ═══════════════════════════════════════════════════════════════════
# STRATEGY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def key1_win_k(race: dict, k: int) -> tuple[bool, int]:
    """Favorite wins (1st), rest from top-k."""
    if race["fs"] < k or k < 4:
        return False, 0
    fav = race["horses"][0]["prog"]
    top = {h["prog"] for h in race["horses"][:k]}
    cost = perm(k - 1, 3)
    hit = race["win"][0] == fav and all(w in top for w in race["win"])
    return hit, cost


def key1_win_dynamic_k(race: dict) -> tuple[bool, int]:
    """Dynamic K: use smaller K when favorite is strong, larger when field is open."""
    fp = race["fav_prob"]
    fs = race["fs"]
    # Strong favorite → concentrate bets (fewer horses needed)
    # Weak favorite → wider net
    if fp >= 0.45:
        k = min(6, fs)
    elif fp >= 0.35:
        k = min(7, fs)
    elif fp >= 0.25:
        k = min(8, fs)
    else:
        k = min(9, fs)
    if k < 4:
        return False, 0
    return key1_win_k(race, k)


def key1_win_entropy_k(race: dict) -> tuple[bool, int]:
    """Entropy-based K: low entropy (concentrated) → small K, high → larger K."""
    e = race["entropy"]
    fs = race["fs"]
    # Entropy of uniform(n) = ln(n). For n=8, ~2.08; n=12, ~2.48
    if e < 1.6:
        k = min(6, fs)
    elif e < 1.9:
        k = min(7, fs)
    elif e < 2.2:
        k = min(8, fs)
    else:
        k = min(9, fs)
    if k < 4:
        return False, 0
    return key1_win_k(race, k)


def henery_top_n(race: dict, n_combos: int, alpha: float = 0.81) -> tuple[bool, int]:
    """Henery model: use p^alpha for position-dependent probabilities.
    Alpha < 1 compresses probs (favorites less dominant in lower positions).
    Harville = alpha=1.0."""
    m = min(race["fs"], 12)
    if m < 4:
        return False, 0

    probs = np.array([race["horses"][i]["p"] for i in range(m)])
    # Henery transform
    hp = probs ** alpha
    hp /= hp.sum()

    if m not in PERM_CACHE:
        return False, 0
    perms_arr = PERM_CACHE[m]

    p1 = hp[perms_arr[:, 0]]
    p2 = hp[perms_arr[:, 1]]
    p3 = hp[perms_arr[:, 2]]
    p4 = hp[perms_arr[:, 3]]
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

def run(races: list[dict], check_fn, params: dict,
        race_filter=None, label: str = "") -> pd.DataFrame:
    by_year = defaultdict(lambda: {"n": 0, "w": 0, "ret": 0.0, "h": 0, "pays": []})
    for race in races:
        if race_filter and not race_filter(race):
            continue
        hit, cost = check_fn(race, **params)
        if cost == 0:
            continue
        y = race["year"]
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


def total_row(df: pd.DataFrame) -> dict:
    t = df[df["year"] == "TOTAL"]
    return t.iloc[0].to_dict() if not t.empty else {}


def fmt(label: str, df: pd.DataFrame) -> str:
    t = total_row(df)
    n = t.get("races", 0)
    roi = t.get("roi%", 0)
    return (f"  {label:50s}: ROI={roi:+7.1f}%  "
            f"Hit={t.get('hit%', 0):5.1f}%  Races={n:6d}  "
            f"AvgPay=${t.get('avg_pay', 0):7.0f}  "
            f"Profit=${t.get('profit', 0):>12,.0f}")


def run_oos(races: list[dict], check_fn, params: dict,
            race_filter=None, train_years: range = None,
            test_years: range = None) -> tuple[dict, dict]:
    """Run strategy on train and test year splits."""
    def year_filter(years, base_filter):
        def f(race):
            if race["year"] not in years:
                return False
            if base_filter and not base_filter(race):
                return False
            return True
        return f

    train_df = run(races, check_fn, params,
                   race_filter=year_filter(train_years, race_filter))
    test_df = run(races, check_fn, params,
                  race_filter=year_filter(test_years, race_filter))
    return total_row(train_df), total_row(test_df)


def main():
    print("=" * 90)
    print("PHASE 3: SQUEEZE REMAINING EDGE FROM CURRENT DATA")
    print("=" * 90)

    races = load_races(BASE / "14years_major_tracks.csv")
    all_results: dict[str, pd.DataFrame] = {}
    summary_rows: list[dict] = []

    def record(label: str, df: pd.DataFrame):
        all_results[label] = df
        t = total_row(df)
        n = int(t.get("races", 0))
        if n < 100:
            return
        summary_rows.append({
            "Strategy": label,
            "Races": n,
            "Wagered": int(t.get("wagered", 0)),
            "Profit": round(t.get("profit", 0), 0),
            "ROI%": t.get("roi%", 0),
            "Hits": int(t.get("hits", 0)),
            "HitRate%": t.get("hit%", 0),
            "AvgPay": round(t.get("avg_pay", 0), 0),
            "CostPerRace": round(t.get("wagered", 0) / max(n, 1), 0),
        })

    # ────────────────────────────────────────────────────────────────
    # 3A: Track × Field-Size interactions
    # ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("3A: Track × Field-Size Interactions (Key1Win-8)")
    print("=" * 90)

    top_tracks = ["KEE", "CD", "SA", "SAR", "GP", "AQU", "DMR", "MTH", "OP"]
    fs_bins = [(8, 9), (10, 11), (10, 12), (12, 20)]

    for track in top_tracks:
        for lo, hi in fs_bins:
            filt = lambda r, t=track, l=lo, h=hi: (
                r["track"] == t and l <= r["fs"] <= h
            )
            label = f"K1W8_{track}_FS{lo}-{hi}"
            df = run(races, key1_win_k, {"k": 8}, race_filter=filt)
            record(label, df)
            t = total_row(df)
            if t.get("races", 0) >= 100:
                print(fmt(label, df))

    # ────────────────────────────────────────────────────────────────
    # 3B: Seasonality / Month / Meet filters
    # ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("3B: Seasonality & Meet-Specific (Key1Win-8)")
    print("=" * 90)

    # Quarter-based
    for q, months in [(1, [1, 2, 3]), (2, [4, 5, 6]), (3, [7, 8, 9]), (4, [10, 11, 12])]:
        filt = lambda r, ms=months: r["month"] in ms
        label = f"K1W8_Q{q}"
        df = run(races, key1_win_k, {"k": 8}, race_filter=filt)
        record(label, df)
        print(fmt(label, df))

    # KEE spring vs fall
    for meet_name, months in [("KEE_Spring", [4, 5]), ("KEE_Fall", [10, 11])]:
        filt = lambda r, ms=months: r["track"] == "KEE" and r["month"] in ms
        label = f"K1W8_{meet_name}"
        df = run(races, key1_win_k, {"k": 8}, race_filter=filt)
        record(label, df)
        print(fmt(label, df))

    # SAR summer
    filt = lambda r: r["track"] == "SAR" and r["month"] in [7, 8]
    label = "K1W8_SAR_Summer"
    df = run(races, key1_win_k, {"k": 8}, race_filter=filt)
    record(label, df)
    print(fmt(label, df))

    # ────────────────────────────────────────────────────────────────
    # 3C: Distance filters (Sprint vs Route)
    # ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("3C: Distance Filters (Key1Win-8)")
    print("=" * 90)

    for dist_cat in ["sprint", "route_mid", "route_long"]:
        filt = lambda r, dc=dist_cat: r["dist_cat"] == dc
        label = f"K1W8_{dist_cat}"
        df = run(races, key1_win_k, {"k": 8}, race_filter=filt)
        record(label, df)
        print(fmt(label, df))

    # Sprint + strong fav
    for dist_cat in ["sprint", "route_mid", "route_long"]:
        filt = lambda r, dc=dist_cat: r["dist_cat"] == dc and r["fav_prob"] >= 0.35
        label = f"K1W8_{dist_cat}_FavStr"
        df = run(races, key1_win_k, {"k": 8}, race_filter=filt)
        record(label, df)
        print(fmt(label, df))

    # ────────────────────────────────────────────────────────────────
    # 3D: Card Position (race number) filters
    # ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("3D: Card Position / Race Number (Key1Win-8)")
    print("=" * 90)

    for lo, hi, name in [(1, 4, "Early"), (5, 8, "Mid"), (9, 14, "Late")]:
        filt = lambda r, l=lo, h=hi: l <= r["rnum"] <= h
        label = f"K1W8_Card{name}_{lo}-{hi}"
        df = run(races, key1_win_k, {"k": 8}, race_filter=filt)
        record(label, df)
        print(fmt(label, df))

    # Late card + strong fav (feature races)
    filt = lambda r: r["rnum"] >= 7 and r["fav_prob"] >= 0.35
    label = "K1W8_LateCard+FavStr"
    df = run(races, key1_win_k, {"k": 8}, race_filter=filt)
    record(label, df)
    print(fmt(label, df))

    # ────────────────────────────────────────────────────────────────
    # 3E: Multi-filter stacking (combinatorial search)
    # ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("3E: Multi-Filter Stacking (Key1Win-8)")
    print("=" * 90)

    # Define atomic filter pool
    atomic_filters = {
        "KEE": lambda r: r["track"] == "KEE",
        "CD": lambda r: r["track"] == "CD",
        "FS10-11": lambda r: 10 <= r["fs"] <= 11,
        "FS10-12": lambda r: 10 <= r["fs"] <= 12,
        "FavStr": lambda r: r["fav_prob"] >= 0.35,
        "FavVStr": lambda r: r["fav_prob"] >= 0.45,
        "Gap15": lambda r: r["prob_gap"] >= 0.15,
        "Sprint": lambda r: r["dist_cat"] == "sprint",
        "Route": lambda r: r["dist_cat"] != "sprint",
        "Dirt": lambda r: r["surface"] == "D",
        "Turf": lambda r: r["surface"] == "T",
        "Fast": lambda r: r["condition"] in ("FT", "FM"),
        "Wet": lambda r: r["condition"] in ("MY", "SY", "GD", "HD", "WF", "YL"),
        "MidLate": lambda r: r["rnum"] >= 5,
        "BigPool": lambda r: r["pool"] >= 50000,
    }

    # Test all 2-filter combinations
    print("\n  --- 2-filter combos (top 30 by ROI, min 200 races) ---")
    combo_results = []
    filter_names = list(atomic_filters.keys())
    for i, (n1, n2) in enumerate(combinations(filter_names, 2)):
        f1, f2 = atomic_filters[n1], atomic_filters[n2]
        filt = lambda r, a=f1, b=f2: a(r) and b(r)
        label = f"K1W8_{n1}+{n2}"
        df = run(races, key1_win_k, {"k": 8}, race_filter=filt)
        t = total_row(df)
        n = int(t.get("races", 0))
        if n >= 200:
            record(label, df)
            combo_results.append((label, t.get("roi%", -100), n, df))

    combo_results.sort(key=lambda x: x[1], reverse=True)
    for label, roi, n, df in combo_results[:30]:
        print(fmt(label, df))

    # Test top-10 three-filter combos (from best 2-filter parents)
    print("\n  --- 3-filter combos (from top 2-filter parents, min 150 races) ---")
    best_2f_names = set()
    for label, roi, n, _ in combo_results[:15]:
        parts = label.replace("K1W8_", "").split("+")
        best_2f_names.update(parts)

    triple_results = []
    for n1, n2, n3 in combinations(best_2f_names, 3):
        if n1 not in atomic_filters or n2 not in atomic_filters or n3 not in atomic_filters:
            continue
        f1, f2, f3 = atomic_filters[n1], atomic_filters[n2], atomic_filters[n3]
        filt = lambda r, a=f1, b=f2, c=f3: a(r) and b(r) and c(r)
        label = f"K1W8_{n1}+{n2}+{n3}"
        df = run(races, key1_win_k, {"k": 8}, race_filter=filt)
        t = total_row(df)
        n = int(t.get("races", 0))
        if n >= 150:
            record(label, df)
            triple_results.append((label, t.get("roi%", -100), n, df))

    triple_results.sort(key=lambda x: x[1], reverse=True)
    for label, roi, n, df in triple_results[:20]:
        print(fmt(label, df))

    # ────────────────────────────────────────────────────────────────
    # 3F: Dynamic K strategies
    # ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("3F: Dynamic K Strategies")
    print("=" * 90)

    # Dynamic K based on favorite probability
    label = "K1W_DynK_FavProb"
    df = run(races, key1_win_dynamic_k, {})
    record(label, df)
    print(fmt(label, df))

    # Dynamic K based on entropy
    label = "K1W_DynK_Entropy"
    df = run(races, key1_win_entropy_k, {})
    record(label, df)
    print(fmt(label, df))

    # Dynamic K + field size filter
    for lo, hi in [(10, 11), (10, 12)]:
        filt = lambda r, l=lo, h=hi: l <= r["fs"] <= h
        label = f"K1W_DynK_FavProb_FS{lo}-{hi}"
        df = run(races, key1_win_dynamic_k, {}, race_filter=filt)
        record(label, df)
        print(fmt(label, df))

    # Dynamic K + best tracks
    for track in ["KEE", "CD"]:
        filt = lambda r, t=track: r["track"] == t
        label = f"K1W_DynK_FavProb_{track}"
        df = run(races, key1_win_dynamic_k, {}, race_filter=filt)
        record(label, df)
        print(fmt(label, df))

    # ────────────────────────────────────────────────────────────────
    # 3G: Henery-adjusted combo ordering
    # ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("3G: Henery Model (alpha-calibrated combo ordering)")
    print("=" * 90)

    # Test different alpha values with moderate ticket counts
    for alpha in [0.70, 0.81, 0.90, 1.0, 1.10, 1.20]:
        for n_combos in [120, 210]:
            label = f"Henery_a{alpha:.2f}_Top{n_combos}"
            t0 = time.time()
            df = run(races, henery_top_n, {"n_combos": n_combos, "alpha": alpha})
            dt = time.time() - t0
            record(label, df)
            print(fmt(label + f" ({dt:.0f}s)", df))

    # Henery with field size filter
    for alpha in [0.81, 0.90]:
        filt = lambda r: 10 <= r["fs"] <= 12
        label = f"Henery_a{alpha:.2f}_Top210_FS10-12"
        df = run(races, henery_top_n, {"n_combos": 210, "alpha": alpha},
                 race_filter=filt)
        record(label, df)
        print(fmt(label, df))

    # ────────────────────────────────────────────────────────────────
    # 3H: Favorite post-position filter
    # ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("3H: Favorite Post-Position Filter (Key1Win-8)")
    print("=" * 90)

    # Inside post (1-4) vs middle (5-8) vs outside (9+)
    for lo, hi, name in [(1, 4, "Inside"), (5, 8, "Middle"), (9, 20, "Outside")]:
        filt = lambda r, l=lo, h=hi: l <= r["fav_pp"] <= h
        label = f"K1W8_FavPP_{name}_{lo}-{hi}"
        df = run(races, key1_win_k, {"k": 8}, race_filter=filt)
        record(label, df)
        if total_row(df).get("races", 0) >= 100:
            print(fmt(label, df))

    # Inside post + strong fav + medium field
    filt = lambda r: 1 <= r["fav_pp"] <= 5 and r["fav_prob"] >= 0.35 and 9 <= r["fs"] <= 12
    label = "K1W8_InsidePP+FavStr+MedField"
    df = run(races, key1_win_k, {"k": 8}, race_filter=filt)
    record(label, df)
    if total_row(df).get("races", 0) >= 100:
        print(fmt(label, df))

    # ────────────────────────────────────────────────────────────────
    # 3I: Out-of-Sample validation for top strategies
    # ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("3I: Out-of-Sample Validation (Train 2010-2018, Test 2019-2025)")
    print("=" * 90)

    train_yrs = set(range(2010, 2019))  # 2010-2018
    test_yrs = set(range(2019, 2026)) - {2021}  # 2019-2025 excl 2021

    # Collect top strategies from this phase (by ROI, min 200 races)
    top_strats = sorted(summary_rows, key=lambda x: x["ROI%"], reverse=True)
    oos_candidates = [s for s in top_strats if s["Races"] >= 200][:25]

    # Also add the Phase 2 best strategies for OOS comparison
    phase2_filters = {
        "K1W8_KEE": lambda r: r["track"] == "KEE",
        "K1W8_CD": lambda r: r["track"] == "CD",
        "K1W8_FS10-11": lambda r: 10 <= r["fs"] <= 11,
        "K1W8_FavStr+FS10-11": lambda r: r["fav_prob"] >= 0.35 and 10 <= r["fs"] <= 11,
        "K1W8_Muddy+FavStr": lambda r: r["condition"] in ("MY", "SY", "GD", "HD") and r["fav_prob"] >= 0.35,
    }

    oos_results = []
    print(f"\n  {'Strategy':<50s} {'Train ROI':>10s} {'Test ROI':>10s} {'Train N':>8s} {'Test N':>8s} {'Delta':>8s}")
    print("  " + "-" * 96)

    # For OOS, we need to reconstruct filters from strategy names
    # Build a mapping of known strategy names to filters
    all_oos_filters: dict[str, callable] = {}
    all_oos_filters.update(phase2_filters)

    # Add the top combo filters found in 3E
    for label, roi, n, df in combo_results[:15]:
        parts = label.replace("K1W8_", "").split("+")
        filters_list = [atomic_filters[p] for p in parts if p in atomic_filters]
        if len(filters_list) == len(parts):
            all_oos_filters[label] = lambda r, fl=filters_list: all(f(r) for f in fl)

    for label, roi, n, df in triple_results[:10]:
        parts = label.replace("K1W8_", "").split("+")
        filters_list = [atomic_filters[p] for p in parts if p in atomic_filters]
        if len(filters_list) == len(parts):
            all_oos_filters[label] = lambda r, fl=filters_list: all(f(r) for f in fl)

    for label, filt in all_oos_filters.items():
        train_t, test_t = run_oos(races, key1_win_k, {"k": 8},
                                   race_filter=filt,
                                   train_years=train_yrs,
                                   test_years=test_yrs)
        tr_roi = train_t.get("roi%", -100)
        te_roi = test_t.get("roi%", -100)
        tr_n = int(train_t.get("races", 0))
        te_n = int(test_t.get("races", 0))
        delta = te_roi - tr_roi
        oos_results.append({
            "Strategy": label, "TrainROI%": tr_roi, "TestROI%": te_roi,
            "TrainN": tr_n, "TestN": te_n, "Delta": round(delta, 1),
        })
        print(f"  {label:<50s} {tr_roi:>+9.1f}% {te_roi:>+9.1f}% {tr_n:>8d} {te_n:>8d} {delta:>+7.1f}")

    # ────────────────────────────────────────────────────────────────
    # SUMMARY
    # ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("PHASE 3 SUMMARY — Top 40 strategies by ROI (min 200 races)")
    print("=" * 90)

    summary = pd.DataFrame(summary_rows)
    summary = summary[summary["Races"] >= 200].sort_values("ROI%", ascending=False)
    print(summary.head(40).to_string(index=False))

    summary.to_csv(BASE / "backtest_phase3_summary.csv", index=False)
    print(f"\nSaved: {BASE / 'backtest_phase3_summary.csv'}")

    # Save OOS results
    oos_df = pd.DataFrame(oos_results).sort_values("TestROI%", ascending=False)
    oos_df.to_csv(BASE / "backtest_phase3_oos.csv", index=False)
    print(f"Saved: {BASE / 'backtest_phase3_oos.csv'}")

    # Print best finding
    if not summary.empty:
        best = summary.iloc[0]
        print(f"\n*** BEST STRATEGY: {best['Strategy']} → ROI={best['ROI%']:+.1f}%, "
              f"Races={int(best['Races'])}, AvgPay=${best['AvgPay']:.0f} ***")

    # Print OOS verdict
    print("\n*** OUT-OF-SAMPLE VERDICT ***")
    if oos_results:
        oos_df_sorted = oos_df.head(5)
        for _, row in oos_df_sorted.iterrows():
            print(f"  {row['Strategy']:<50s} Train={row['TrainROI%']:+.1f}%  "
                  f"Test={row['TestROI%']:+.1f}%  Delta={row['Delta']:+.1f}")

    return all_results, summary, oos_df


if __name__ == "__main__":
    main()
