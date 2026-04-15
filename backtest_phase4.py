#!/usr/bin/env python3
"""
backtest_phase4.py — Phase 4: Aggressive profitability search & robustness.

Building on Phase 3 best leads:
  1. CD+FS10-11+Gap>=0.15  → +13.1% ROI (485 races), OOS train +5.5%, test +23.1%
  2. KEE+MidLate+Wet       → +12.8% ROI (364 races), OOS train -2.3%, test +23.7%
  3. KEE+Wet (various)     → +1.6% to +2.4% (300-500 races)

Phase 4 experiments:
  4A: Fine-grained gap sweep on CD (0.08→0.30 step 0.02) × FS × K
  4B: KEE wet-track deep dive: FS × gap × card position × K
  4C: New odds-derived features (concentration, chalky, gap23, top4_mass)
  4D: Combined CD+KEE strategies
  4E: EV-aware combo selection (Harville EV ranking)
  4F: Multi-fold temporal OOS (3 splits) for all positive strategies
  4G: Bootstrap confidence intervals + permutation test
  4H: Conditional Kelly / flat-bet comparison
  4I: Broader track sweep with best filter combos
"""

import time
import warnings
from math import perm
from pathlib import Path
from itertools import permutations
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path("/Users/maximusregent_ai/Shared/Superfecta Help")

# ═══════════════════════════════════════════════════════════════════
# DATA LOADING (shared with phase3)
# ═══════════════════════════════════════════════════════════════════

def ml_prob(odds: float) -> float:
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return (-odds) / (-odds + 100.0)


def load_races(csv_path: Path) -> list[dict]:
    """Load CSV → list of race dicts with enriched features."""
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

        probs = np.array([h["p"] for h in horses])
        fs = len(horses)

        # === ENRICHED FEATURES ===
        # Basic
        fav_prob = probs[0]
        gap12 = probs[0] - probs[1] if fs > 1 else 0
        gap23 = probs[1] - probs[2] if fs > 2 else 0

        # Concentration metrics
        top2_mass = probs[:2].sum() if fs >= 2 else probs[0]
        top3_mass = probs[:3].sum() if fs >= 3 else top2_mass
        top4_mass = probs[:4].sum() if fs >= 4 else top3_mass
        hhi = float(np.sum(probs ** 2))  # Herfindahl index

        # Chalky indicator: how much probability is in top-4 vs rest
        chalk_ratio = top4_mass / (1 - top4_mass + 1e-9)

        # Odds-implied value: ratio of fav odds to "fair" odds
        fav_odds = horses[0]["odds"]

        # Entropy
        entropy = float(-np.sum(probs * np.log(probs + 1e-12)))

        # Distance bucket
        dist = float(wi.get("distance_id", 0))
        if dist <= 700:
            dist_cat = "sprint"
        elif dist <= 850:
            dist_cat = "route_mid"
        else:
            dist_cat = "route_long"

        # Condition categories
        cond = str(wi.get("track_condition", "")).strip()
        is_wet = cond in ("MY", "SY", "GD", "HD", "WF", "YL")
        is_fast = cond in ("FT", "FM")

        races.append({
            "track": track.strip(),
            "date": date,
            "year": date.year,
            "month": date.month,
            "rnum": rnum,
            "fs": fs,
            "horses": horses,
            "win": wp,
            "payout": payout,
            "pool": float(wi.get("total_pool", 0)),
            "surface": str(wi.get("surface", "")).strip(),
            "course_type": str(wi.get("course_type", "")).strip(),
            "condition": cond,
            "is_wet": is_wet,
            "is_fast": is_fast,
            "dist": dist,
            "dist_cat": dist_cat,
            "purse": float(wi.get("purse_usa", 0)),
            "entropy": entropy,
            "fav_prob": fav_prob,
            "fav_pp": horses[0]["pp"],
            "fav_odds": fav_odds,
            "prob_gap": gap12,
            "gap23": gap23,
            "top2_mass": top2_mass,
            "top3_mass": top3_mass,
            "top4_mass": top4_mass,
            "hhi": hhi,
            "chalk_ratio": chalk_ratio,
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


def key12_win_k(race: dict, k: int) -> tuple[bool, int]:
    """Top-2 favorites in 1st/2nd (either order), rest from top-k."""
    if race["fs"] < k or k < 4:
        return False, 0
    top2 = {race["horses"][0]["prog"], race["horses"][1]["prog"]}
    top_k = {h["prog"] for h in race["horses"][:k]}
    w = race["win"]
    # 1st and 2nd must both be in top-2
    hit = (w[0] in top2 and w[1] in top2 and w[0] != w[1]
           and w[2] in top_k and w[3] in top_k)
    # Cost: 2 * perm(k-2, 2) — 2 orderings for 1st/2nd, then permute rest from remaining
    cost = 2 * perm(k - 2, 2)
    return hit, cost


def key1_win_var_k(race: dict, k: int, min_gap: float = 0.0) -> tuple[bool, int]:
    """Key1Win-K but only bet when fav gap exceeds threshold."""
    if race["prob_gap"] < min_gap:
        return False, 0
    return key1_win_k(race, k)


# ═══════════════════════════════════════════════════════════════════
# BACKTESTING ENGINE
# ═══════════════════════════════════════════════════════════════════

def run(races: list[dict], check_fn, params: dict,
        race_filter=None) -> pd.DataFrame:
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
    return (f"  {label:55s}: ROI={roi:+7.1f}%  "
            f"Hit={t.get('hit%', 0):5.1f}%  Races={n:6d}  "
            f"AvgPay=${t.get('avg_pay', 0):7.0f}  "
            f"Profit=${t.get('profit', 0):>12,.0f}")


def year_roi_details(df: pd.DataFrame) -> str:
    """Show year-by-year ROI for a strategy."""
    lines = []
    for _, row in df.iterrows():
        if row["year"] == "TOTAL":
            continue
        lines.append(f"    {row['year']}: ROI={row['roi%']:+7.1f}% ({row['races']} races, {row['hits']} hits)")
    return "\n".join(lines)


def positive_year_count(df: pd.DataFrame) -> tuple[int, int]:
    """Count years with positive ROI and total years."""
    yearly = df[df["year"] != "TOTAL"]
    pos = (yearly["roi%"] > 0).sum()
    return int(pos), len(yearly)


# ═══════════════════════════════════════════════════════════════════
# MULTI-FOLD TEMPORAL OOS
# ═══════════════════════════════════════════════════════════════════

def multi_fold_oos(races: list[dict], check_fn, params: dict,
                   race_filter=None) -> dict:
    """3-fold temporal cross-validation:
      Fold 1: train 2010-2015, test 2016-2020 (excl 2021)
      Fold 2: train 2010-2018, test 2019-2025 (excl 2021)
      Fold 3: train 2015-2020, test 2022-2025
    Also: full walkforward (train on all prior years, test each year)
    """
    folds = [
        ("F1: 10-15→16-20", set(range(2010, 2016)), set(range(2016, 2021))),
        ("F2: 10-18→19-25", set(range(2010, 2019)), set(range(2019, 2026)) - {2021}),
        ("F3: 15-20→22-25", set(range(2015, 2021)), set(range(2022, 2026))),
    ]

    results = {}
    for fold_name, train_yrs, test_yrs in folds:
        def train_filt(r, ty=train_yrs, bf=race_filter):
            if r["year"] not in ty:
                return False
            return bf(r) if bf else True

        def test_filt(r, ty=test_yrs, bf=race_filter):
            if r["year"] not in ty:
                return False
            return bf(r) if bf else True

        train_df = run(races, check_fn, params, race_filter=train_filt)
        test_df = run(races, check_fn, params, race_filter=test_filt)
        train_t = total_row(train_df)
        test_t = total_row(test_df)
        results[fold_name] = {
            "train_roi": train_t.get("roi%", -100),
            "test_roi": test_t.get("roi%", -100),
            "train_n": int(train_t.get("races", 0)),
            "test_n": int(test_t.get("races", 0)),
        }

    return results


# ═══════════════════════════════════════════════════════════════════
# BOOTSTRAP CONFIDENCE INTERVAL
# ═══════════════════════════════════════════════════════════════════

def bootstrap_roi(races: list[dict], check_fn, params: dict,
                  race_filter=None, n_boot: int = 5000) -> dict:
    """Bootstrap 95% CI for ROI by resampling race-level outcomes."""
    # Collect per-race profit/loss
    pnls = []
    for race in races:
        if race_filter and not race_filter(race):
            continue
        hit, cost = check_fn(race, **params)
        if cost == 0:
            continue
        if hit:
            pnls.append(race["payout"] - cost)
        else:
            pnls.append(-cost)

    if len(pnls) < 30:
        return {"n": len(pnls), "roi": 0, "ci_lo": -100, "ci_hi": -100, "p_positive": 0}

    pnls = np.array(pnls)
    n = len(pnls)
    total_cost_per_race = np.mean([abs(x) for x in pnls if x < 0]) if any(x < 0 for x in pnls) else 210

    roi = float(pnls.sum() / (n * total_cost_per_race) * 100)

    # Bootstrap
    rng = np.random.default_rng(42)
    boot_rois = np.empty(n_boot)
    for i in range(n_boot):
        sample = rng.choice(pnls, size=n, replace=True)
        boot_rois[i] = sample.mean() / total_cost_per_race * 100

    ci_lo, ci_hi = float(np.percentile(boot_rois, 2.5)), float(np.percentile(boot_rois, 97.5))
    p_positive = float((boot_rois > 0).mean())

    return {
        "n": n,
        "roi": roi,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "p_positive": p_positive,
    }


# ═══════════════════════════════════════════════════════════════════
# PERMUTATION TEST FOR MULTIPLE TESTING
# ═══════════════════════════════════════════════════════════════════

def permutation_test(races: list[dict], check_fn, params: dict,
                     race_filter=None, n_perm: int = 2000) -> float:
    """Shuffle payouts among bet races, compute null ROI distribution.
    Returns p-value: fraction of permuted ROIs >= observed."""
    bet_races = []
    for race in races:
        if race_filter and not race_filter(race):
            continue
        hit, cost = check_fn(race, **params)
        if cost == 0:
            continue
        bet_races.append((hit, cost, race["payout"]))

    if len(bet_races) < 30:
        return 1.0

    hits = np.array([b[0] for b in bet_races], dtype=bool)
    costs = np.array([b[1] for b in bet_races], dtype=float)
    payouts = np.array([b[2] for b in bet_races], dtype=float)
    total_cost = costs.sum()

    # Observed ROI
    observed_return = payouts[hits].sum()
    observed_roi = (observed_return - total_cost) / total_cost

    # Permutation: shuffle which races are "hits" (keeping same number of hits)
    rng = np.random.default_rng(42)
    n_hits = hits.sum()
    n_races = len(bet_races)
    count_ge = 0

    for _ in range(n_perm):
        # Randomly assign hits to different races
        perm_hits = np.zeros(n_races, dtype=bool)
        perm_hits[rng.choice(n_races, size=n_hits, replace=False)] = True
        perm_return = payouts[perm_hits].sum()
        perm_roi = (perm_return - total_cost) / total_cost
        if perm_roi >= observed_roi:
            count_ge += 1

    return count_ge / n_perm


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    print("=" * 100)
    print("PHASE 4: AGGRESSIVE PROFITABILITY SEARCH & ROBUSTNESS TESTING")
    print("=" * 100)

    races = load_races(BASE / "14years_major_tracks.csv")
    summary_rows: list[dict] = []

    def record(label: str, df: pd.DataFrame, extra: dict = None):
        t = total_row(df)
        n = int(t.get("races", 0))
        if n < 50:
            return
        row = {
            "Strategy": label,
            "Races": n,
            "Wagered": int(t.get("wagered", 0)),
            "Profit": round(t.get("profit", 0), 0),
            "ROI%": t.get("roi%", 0),
            "Hits": int(t.get("hits", 0)),
            "HitRate%": t.get("hit%", 0),
            "AvgPay": round(t.get("avg_pay", 0), 0),
            "CostPerRace": round(t.get("wagered", 0) / max(n, 1), 0),
        }
        pos_yrs, tot_yrs = positive_year_count(df)
        row["PosYears"] = f"{pos_yrs}/{tot_yrs}"
        if extra:
            row.update(extra)
        summary_rows.append(row)

    # ════════════════════════════════════════════════════════════════
    # 4A: FINE-GRAINED GAP SWEEP ON CD (Churchill Downs)
    # ════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("4A: Fine-Grained Gap Sweep on Churchill Downs")
    print("=" * 100)

    gap_thresholds = [0.06, 0.08, 0.10, 0.12, 0.14, 0.15, 0.16, 0.18, 0.20, 0.22, 0.25, 0.30]
    fs_ranges = [(8, 9), (9, 11), (10, 11), (10, 12), (10, 13), (11, 13), (8, 13)]
    k_values = [7, 8, 9]

    print(f"\n  {'Strategy':<60s} {'ROI%':>8s} {'Races':>7s} {'Hit%':>7s} {'AvgPay':>8s} {'PosYrs':>8s}")
    print("  " + "-" * 100)

    cd_positive = []
    for k in k_values:
        for fs_lo, fs_hi in fs_ranges:
            for gap in gap_thresholds:
                filt = lambda r, g=gap, lo=fs_lo, hi=fs_hi: (
                    r["track"] == "CD" and lo <= r["fs"] <= hi and r["prob_gap"] >= g
                )
                label = f"K1W{k}_CD_FS{fs_lo}-{fs_hi}_Gap{gap:.2f}"
                df = run(races, key1_win_k, {"k": k}, race_filter=filt)
                t = total_row(df)
                n = int(t.get("races", 0))
                if n >= 80:
                    record(label, df)
                    roi = t.get("roi%", -100)
                    pos_yrs, tot_yrs = positive_year_count(df)
                    if roi > -5:
                        print(f"  {label:<60s} {roi:>+7.1f}% {n:>7d} {t.get('hit%',0):>6.1f}% ${t.get('avg_pay',0):>7.0f} {pos_yrs}/{tot_yrs}")
                    if roi > 0:
                        cd_positive.append((label, roi, n, df, filt))

    print(f"\n  → Found {len(cd_positive)} positive-ROI CD strategies")

    # ════════════════════════════════════════════════════════════════
    # 4B: KEE WET-TRACK DEEP DIVE
    # ════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("4B: KEE Wet-Track Deep Dive")
    print("=" * 100)

    print(f"\n  {'Strategy':<60s} {'ROI%':>8s} {'Races':>7s} {'Hit%':>7s} {'AvgPay':>8s} {'PosYrs':>8s}")
    print("  " + "-" * 100)

    kee_positive = []
    for k in [7, 8, 9]:
        for fs_lo, fs_hi in [(0, 99), (8, 10), (9, 11), (10, 12), (10, 13), (8, 13)]:
            for gap in [0.0, 0.06, 0.10, 0.15, 0.20]:
                for card_lo, card_hi, cname in [(1, 99, "All"), (5, 99, "Mid+"), (7, 99, "Late")]:
                    filt = lambda r, g=gap, lo=fs_lo, hi=fs_hi, cl=card_lo, ch=card_hi: (
                        r["track"] == "KEE" and r["is_wet"]
                        and lo <= r["fs"] <= hi and r["prob_gap"] >= g
                        and cl <= r["rnum"] <= ch
                    )
                    label = f"K1W{k}_KEE_Wet_FS{fs_lo}-{fs_hi}_Gap{gap:.2f}_Card{cname}"
                    df = run(races, key1_win_k, {"k": k}, race_filter=filt)
                    t = total_row(df)
                    n = int(t.get("races", 0))
                    if n >= 50:
                        record(label, df)
                        roi = t.get("roi%", -100)
                        pos_yrs, tot_yrs = positive_year_count(df)
                        if roi > 0:
                            print(f"  {label:<60s} {roi:>+7.1f}% {n:>7d} {t.get('hit%',0):>6.1f}% ${t.get('avg_pay',0):>7.0f} {pos_yrs}/{tot_yrs}")
                            kee_positive.append((label, roi, n, df, filt))

    # Also try KEE wet + surface combos
    for surface in ["D", "T"]:
        for k in [7, 8, 9]:
            filt = lambda r, s=surface, kk=k: (
                r["track"] == "KEE" and r["is_wet"] and r["surface"] == s
            )
            label = f"K1W{k}_KEE_Wet_{surface}"
            df = run(races, key1_win_k, {"k": k}, race_filter=filt)
            t = total_row(df)
            n = int(t.get("races", 0))
            if n >= 50:
                record(label, df)
                roi = t.get("roi%", -100)
                pos_yrs, tot_yrs = positive_year_count(df)
                if roi > -5:
                    print(f"  {label:<60s} {roi:>+7.1f}% {n:>7d} {t.get('hit%',0):>6.1f}% ${t.get('avg_pay',0):>7.0f} {pos_yrs}/{tot_yrs}")
                if roi > 0:
                    kee_positive.append((label, roi, n, df, filt))

    print(f"\n  → Found {len(kee_positive)} positive-ROI KEE wet strategies")

    # ════════════════════════════════════════════════════════════════
    # 4C: NEW ODDS-DERIVED FEATURES
    # ════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("4C: New Odds-Derived Feature Filters")
    print("=" * 100)

    feature_filters = {
        # Chalky races: top-4 horses dominate
        "Chalk_Hi": lambda r: r["top4_mass"] >= 0.70,
        "Chalk_VHi": lambda r: r["top4_mass"] >= 0.75,
        # Low entropy = concentrated probability
        "LowEntropy": lambda r: r["entropy"] < 1.8,
        "VLowEntropy": lambda r: r["entropy"] < 1.5,
        # High HHI = dominant horse
        "HHI_Hi": lambda r: r["hhi"] >= 0.15,
        "HHI_VHi": lambda r: r["hhi"] >= 0.20,
        # Gap between 2nd and 3rd (separation of top 2)
        "Gap23_Hi": lambda r: r["gap23"] >= 0.08,
        "Gap23_VHi": lambda r: r["gap23"] >= 0.12,
        # Top-2 mass high (top 2 dominate)
        "Top2Mass_Hi": lambda r: r["top2_mass"] >= 0.50,
        "Top2Mass_VHi": lambda r: r["top2_mass"] >= 0.55,
        # Combined: dominant fav + separated field
        "DomFav": lambda r: r["fav_prob"] >= 0.35 and r["gap23"] >= 0.06,
        "SuperDom": lambda r: r["fav_prob"] >= 0.40 and r["prob_gap"] >= 0.15,
    }

    print(f"\n  {'Strategy':<60s} {'ROI%':>8s} {'Races':>7s} {'Hit%':>7s} {'AvgPay':>8s}")
    print("  " + "-" * 100)

    feature_positive = []
    for fname, ffilt in feature_filters.items():
        for k in [7, 8]:
            # Standalone
            label = f"K1W{k}_{fname}"
            df = run(races, key1_win_k, {"k": k}, race_filter=ffilt)
            t = total_row(df)
            n = int(t.get("races", 0))
            if n >= 100:
                record(label, df)
                roi = t.get("roi%", -100)
                if roi > -10:
                    print(f"  {label:<60s} {roi:>+7.1f}% {n:>7d} {t.get('hit%',0):>6.1f}% ${t.get('avg_pay',0):>7.0f}")

            # + CD
            filt_cd = lambda r, ff=ffilt: r["track"] == "CD" and ff(r)
            label = f"K1W{k}_{fname}_CD"
            df = run(races, key1_win_k, {"k": k}, race_filter=filt_cd)
            t = total_row(df)
            n = int(t.get("races", 0))
            if n >= 80:
                record(label, df)
                roi = t.get("roi%", -100)
                if roi > -5:
                    print(f"  {label:<60s} {roi:>+7.1f}% {n:>7d} {t.get('hit%',0):>6.1f}% ${t.get('avg_pay',0):>7.0f}")
                if roi > 0:
                    feature_positive.append((label, roi, n, df, filt_cd))

            # + KEE
            filt_kee = lambda r, ff=ffilt: r["track"] == "KEE" and ff(r)
            label = f"K1W{k}_{fname}_KEE"
            df = run(races, key1_win_k, {"k": k}, race_filter=filt_kee)
            t = total_row(df)
            n = int(t.get("races", 0))
            if n >= 80:
                record(label, df)
                roi = t.get("roi%", -100)
                if roi > -5:
                    print(f"  {label:<60s} {roi:>+7.1f}% {n:>7d} {t.get('hit%',0):>6.1f}% ${t.get('avg_pay',0):>7.0f}")
                if roi > 0:
                    feature_positive.append((label, roi, n, df, filt_kee))

            # + FS10-12
            filt_fs = lambda r, ff=ffilt: 10 <= r["fs"] <= 12 and ff(r)
            label = f"K1W{k}_{fname}_FS10-12"
            df = run(races, key1_win_k, {"k": k}, race_filter=filt_fs)
            t = total_row(df)
            n = int(t.get("races", 0))
            if n >= 100:
                record(label, df)
                roi = t.get("roi%", -100)
                if roi > -10:
                    print(f"  {label:<60s} {roi:>+7.1f}% {n:>7d} {t.get('hit%',0):>6.1f}% ${t.get('avg_pay',0):>7.0f}")

    print(f"\n  → Found {len(feature_positive)} positive-ROI feature strategies")

    # ════════════════════════════════════════════════════════════════
    # 4D: COMBINED CD+KEE STRATEGIES
    # ════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("4D: Combined CD + KEE Strategies")
    print("=" * 100)

    print(f"\n  {'Strategy':<60s} {'ROI%':>8s} {'Races':>7s} {'Hit%':>7s} {'AvgPay':>8s} {'PosYrs':>8s}")
    print("  " + "-" * 100)

    combined_positive = []
    for k in [7, 8, 9]:
        for fs_lo, fs_hi in [(9, 12), (10, 11), (10, 12), (10, 13)]:
            for gap in [0.0, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20]:
                # CD+KEE with gap
                filt = lambda r, g=gap, lo=fs_lo, hi=fs_hi: (
                    r["track"] in ("CD", "KEE") and lo <= r["fs"] <= hi and r["prob_gap"] >= g
                )
                label = f"K1W{k}_CDKEE_FS{fs_lo}-{fs_hi}_Gap{gap:.2f}"
                df = run(races, key1_win_k, {"k": k}, race_filter=filt)
                t = total_row(df)
                n = int(t.get("races", 0))
                if n >= 100:
                    record(label, df)
                    roi = t.get("roi%", -100)
                    pos_yrs, tot_yrs = positive_year_count(df)
                    if roi > -5:
                        print(f"  {label:<60s} {roi:>+7.1f}% {n:>7d} {t.get('hit%',0):>6.1f}% ${t.get('avg_pay',0):>7.0f} {pos_yrs}/{tot_yrs}")
                    if roi > 0:
                        combined_positive.append((label, roi, n, df, filt))

        # CD+KEE + wet
        filt = lambda r, kk=k: r["track"] in ("CD", "KEE") and r["is_wet"]
        label = f"K1W{k}_CDKEE_Wet"
        df = run(races, key1_win_k, {"k": k}, race_filter=filt)
        t = total_row(df)
        n = int(t.get("races", 0))
        if n >= 100:
            record(label, df)
            roi = t.get("roi%", -100)
            pos_yrs, tot_yrs = positive_year_count(df)
            if roi > -5:
                print(f"  {label:<60s} {roi:>+7.1f}% {n:>7d} {t.get('hit%',0):>6.1f}% ${t.get('avg_pay',0):>7.0f} {pos_yrs}/{tot_yrs}")
            if roi > 0:
                combined_positive.append((label, roi, n, df, filt))

    print(f"\n  → Found {len(combined_positive)} positive-ROI combined strategies")

    # ════════════════════════════════════════════════════════════════
    # 4E: KEY12 (Top-2 exacta box) strategies on best pockets
    # ════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("4E: Key12 (Top-2 Exacta Box) on Best Pockets")
    print("=" * 100)

    print(f"\n  {'Strategy':<60s} {'ROI%':>8s} {'Races':>7s} {'Hit%':>7s} {'AvgPay':>8s}")
    print("  " + "-" * 100)

    for k in [8, 9, 10]:
        for gap in [0.0, 0.10, 0.15]:
            for track_set, tname in [({"CD"}, "CD"), ({"KEE"}, "KEE"), ({"CD", "KEE"}, "CDKEE")]:
                filt = lambda r, g=gap, ts=track_set: (
                    r["track"] in ts and r["prob_gap"] >= g
                )
                label = f"K12W{k}_{tname}_Gap{gap:.2f}"
                df = run(races, key12_win_k, {"k": k}, race_filter=filt)
                t = total_row(df)
                n = int(t.get("races", 0))
                if n >= 100:
                    record(label, df)
                    roi = t.get("roi%", -100)
                    if roi > -15:
                        print(f"  {label:<60s} {roi:>+7.1f}% {n:>7d} {t.get('hit%',0):>6.1f}% ${t.get('avg_pay',0):>7.0f}")

    # ════════════════════════════════════════════════════════════════
    # 4F: BROADER TRACK SWEEP WITH BEST FILTER COMBOS
    # ════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("4F: Broader Track Sweep with Best Filter Combos")
    print("=" * 100)

    all_tracks = ["CD", "KEE", "SA", "GP", "SAR", "AQU", "BEL", "DMR", "MTH", "OP"]
    print(f"\n  {'Strategy':<60s} {'ROI%':>8s} {'Races':>7s} {'Hit%':>7s} {'AvgPay':>8s}")
    print("  " + "-" * 100)

    track_positive = []
    for track in all_tracks:
        for gap in [0.10, 0.15, 0.20]:
            for fs_lo, fs_hi in [(10, 11), (10, 12), (9, 12)]:
                filt = lambda r, t=track, g=gap, lo=fs_lo, hi=fs_hi: (
                    r["track"] == t and r["prob_gap"] >= g and lo <= r["fs"] <= hi
                )
                label = f"K1W8_{track}_FS{fs_lo}-{fs_hi}_Gap{gap:.2f}"
                df = run(races, key1_win_k, {"k": 8}, race_filter=filt)
                t_row = total_row(df)
                n = int(t_row.get("races", 0))
                if n >= 80:
                    record(label, df)
                    roi = t_row.get("roi%", -100)
                    if roi > -5:
                        print(f"  {label:<60s} {roi:>+7.1f}% {n:>7d} {t_row.get('hit%',0):>6.1f}% ${t_row.get('avg_pay',0):>7.0f}")
                    if roi > 0:
                        track_positive.append((label, roi, n, df, filt))

        # Wet track for each
        filt = lambda r, t=track: r["track"] == t and r["is_wet"]
        label = f"K1W8_{track}_Wet"
        df = run(races, key1_win_k, {"k": 8}, race_filter=filt)
        t_row = total_row(df)
        n = int(t_row.get("races", 0))
        if n >= 80:
            record(label, df)
            roi = t_row.get("roi%", -100)
            if roi > -5:
                print(f"  {label:<60s} {roi:>+7.1f}% {n:>7d} {t_row.get('hit%',0):>6.1f}% ${t_row.get('avg_pay',0):>7.0f}")
            if roi > 0:
                track_positive.append((label, roi, n, df, filt))

    print(f"\n  → Found {len(track_positive)} positive-ROI track strategies beyond CD/KEE")

    # ════════════════════════════════════════════════════════════════
    # 4G: COLLECT ALL POSITIVE STRATEGIES FOR ROBUSTNESS TESTING
    # ════════════════════════════════════════════════════════════════
    all_positive = cd_positive + kee_positive + feature_positive + combined_positive + track_positive
    # Deduplicate by label
    seen = set()
    unique_positive = []
    for item in all_positive:
        if item[0] not in seen:
            seen.add(item[0])
            unique_positive.append(item)

    # Sort by ROI descending
    unique_positive.sort(key=lambda x: x[1], reverse=True)

    print("\n" + "=" * 100)
    print(f"4G: ROBUSTNESS TESTING — {len(unique_positive)} positive-ROI strategies")
    print("=" * 100)

    robustness_rows = []

    for label, roi, n, df, filt in unique_positive[:40]:  # Top 40
        print(f"\n  Testing: {label} (ROI={roi:+.1f}%, N={n})")

        # Multi-fold OOS
        oos = multi_fold_oos(races, key1_win_k, {"k": 8}, race_filter=filt)
        # Extract K from label
        k_match = 8
        if label.startswith("K1W7"):
            k_match = 7
        elif label.startswith("K1W9"):
            k_match = 9
        if k_match != 8:
            oos = multi_fold_oos(races, key1_win_k, {"k": k_match}, race_filter=filt)

        # Bootstrap CI
        boot = bootstrap_roi(races, key1_win_k, {"k": k_match}, race_filter=filt)

        # Year-by-year
        pos_yrs, tot_yrs = positive_year_count(df)

        # Collect
        row = {
            "Strategy": label,
            "FullROI%": round(roi, 2),
            "Races": n,
            "PosYears": f"{pos_yrs}/{tot_yrs}",
            "Boot_CI_Lo": round(boot["ci_lo"], 1),
            "Boot_CI_Hi": round(boot["ci_hi"], 1),
            "Boot_P_Pos": round(boot["p_positive"], 3),
        }
        for fold_name, fold_data in oos.items():
            short = fold_name.split(":")[0]
            row[f"{short}_Train"] = round(fold_data["train_roi"], 1)
            row[f"{short}_Test"] = round(fold_data["test_roi"], 1)
            row[f"{short}_TestN"] = fold_data["test_n"]

        robustness_rows.append(row)

        print(f"    Bootstrap 95% CI: [{boot['ci_lo']:+.1f}%, {boot['ci_hi']:+.1f}%]  "
              f"P(ROI>0)={boot['p_positive']:.3f}")
        for fold_name, fold_data in oos.items():
            print(f"    {fold_name}: Train={fold_data['train_roi']:+.1f}% ({fold_data['train_n']}), "
                  f"Test={fold_data['test_roi']:+.1f}% ({fold_data['test_n']})")

    # ════════════════════════════════════════════════════════════════
    # 4H: PERMUTATION TEST FOR TOP 5 STRATEGIES
    # ════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("4H: Permutation Test for Top Strategies")
    print("=" * 100)

    for label, roi, n, df, filt in unique_positive[:5]:
        k_match = 8
        if label.startswith("K1W7"):
            k_match = 7
        elif label.startswith("K1W9"):
            k_match = 9
        pval = permutation_test(races, key1_win_k, {"k": k_match}, race_filter=filt)
        print(f"  {label:<60s} ROI={roi:+.1f}%  p-value={pval:.4f}")
        # Update robustness row
        for row in robustness_rows:
            if row["Strategy"] == label:
                row["Perm_pval"] = round(pval, 4)

    # ════════════════════════════════════════════════════════════════
    # SUMMARY & OUTPUT
    # ════════════════════════════════════════════════════════════════
    print("\n" + "=" * 100)
    print("PHASE 4 COMPLETE SUMMARY")
    print("=" * 100)

    # Save all strategies
    summary_df = pd.DataFrame(summary_rows)
    if not summary_df.empty:
        summary_df = summary_df.sort_values("ROI%", ascending=False)
        summary_df.to_csv(BASE / "backtest_phase4_summary.csv", index=False)
        print(f"\nSaved: {BASE / 'backtest_phase4_summary.csv'} ({len(summary_df)} strategies)")

        print("\n  --- TOP 30 STRATEGIES BY ROI (min 50 races) ---")
        print(summary_df.head(30).to_string(index=False))

    # Save robustness results
    if robustness_rows:
        rob_df = pd.DataFrame(robustness_rows)
        rob_df = rob_df.sort_values("FullROI%", ascending=False)
        rob_df.to_csv(BASE / "backtest_phase4_robustness.csv", index=False)
        print(f"\nSaved: {BASE / 'backtest_phase4_robustness.csv'}")

        # Print robustness summary
        print("\n  --- ROBUSTNESS VERDICT ---")
        print(f"  {'Strategy':<55s} {'ROI%':>6s} {'N':>6s} {'CI_Lo':>7s} {'CI_Hi':>7s} {'P>0':>6s} {'F1Test':>7s} {'F2Test':>7s} {'F3Test':>7s}")
        print("  " + "-" * 110)
        for _, row in rob_df.iterrows():
            print(f"  {row['Strategy']:<55s} "
                  f"{row['FullROI%']:>+5.1f}% "
                  f"{row['Races']:>6.0f} "
                  f"{row.get('Boot_CI_Lo', 0):>+6.1f}% "
                  f"{row.get('Boot_CI_Hi', 0):>+6.1f}% "
                  f"{row.get('Boot_P_Pos', 0):>5.3f} "
                  f"{row.get('F1_Test', 0):>+6.1f}% "
                  f"{row.get('F2_Test', 0):>+6.1f}% "
                  f"{row.get('F3_Test', 0):>+6.1f}%")

        # Identify truly robust strategies
        robust = rob_df[
            (rob_df["Boot_P_Pos"] >= 0.70) &
            (rob_df["FullROI%"] > 0)
        ]
        if not robust.empty:
            print(f"\n  *** {len(robust)} strategies with P(ROI>0) >= 70% ***")
            for _, row in robust.iterrows():
                print(f"    {row['Strategy']}: ROI={row['FullROI%']:+.1f}%, "
                      f"CI=[{row['Boot_CI_Lo']:+.1f}%, {row['Boot_CI_Hi']:+.1f}%], "
                      f"P>0={row['Boot_P_Pos']:.3f}")
        else:
            print("\n  *** NO strategies with P(ROI>0) >= 70% ***")

        # Strategies that are positive in at least 2 of 3 OOS folds
        multi_oos = []
        for _, row in rob_df.iterrows():
            oos_pos = sum([
                1 if row.get("F1_Test", -100) > 0 else 0,
                1 if row.get("F2_Test", -100) > 0 else 0,
                1 if row.get("F3_Test", -100) > 0 else 0,
            ])
            if oos_pos >= 2 and row["FullROI%"] > 0:
                multi_oos.append((row["Strategy"], row["FullROI%"], oos_pos))

        if multi_oos:
            print(f"\n  *** {len(multi_oos)} strategies positive in 2+ of 3 OOS folds ***")
            for name, roi, oos_pos in multi_oos:
                print(f"    {name}: ROI={roi:+.1f}%, OOS positive folds={oos_pos}/3")
        else:
            print("\n  *** NO strategies positive in 2+ of 3 OOS folds ***")

    # ════════════════════════════════════════════════════════════════
    # FINAL BEST STRATEGY DETAIL
    # ════════════════════════════════════════════════════════════════
    if unique_positive:
        best_label, best_roi, best_n, best_df, best_filt = unique_positive[0]
        print("\n" + "=" * 100)
        print(f"BEST STRATEGY DETAIL: {best_label}")
        print("=" * 100)
        print(f"\n  Overall ROI: {best_roi:+.1f}%")
        print(f"  Races: {best_n}")
        print(f"  Year-by-year:")
        print(year_roi_details(best_df))

    return summary_df if not summary_df.empty else pd.DataFrame(), robustness_rows


if __name__ == "__main__":
    main()
