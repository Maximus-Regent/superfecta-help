#!/usr/bin/env python3
"""
Phase 8: Advanced superfecta portfolio optimization.

Goal: Beat Phase 7 three-track portfolio (+28.0% ROI, 1,075 races, 12/15 years).

New in Phase 8:
  1. Feature engineering: gap_ratio, entropy proxy, top4_residual, fav_concentration
  2. K=9 search (unexplored in Phase 7)
  3. Monthly/seasonal gating filters
  4. Interaction filters (gap × fs, fav × month)
  5. Score-based portfolio: rank by composite quality, prune weak bets
  6. Expanding walk-forward validation (no lookahead)
  7. Track-specific refinements for OP and CD
  8. Large-sample track exploration (GP, SA) with new features
  9. Direct Phase 7 comparison
"""

import os
for _k in [
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS", "NUMEXPR_MAX_THREADS", "MKL_NUM_THREADS",
]:
    os.environ[_k] = "1"

from math import perm, log
from pathlib import Path
from itertools import product

import numpy as np
import pandas as pd

BASE = Path("/Users/maximusregent_ai/Shared/Superfecta Help")
CACHE_PATH = BASE / "phase5_race_cache.pkl"
OUT_CSV = BASE / "backtest_phase8_summary.csv"
OUT_REPORT = BASE / "PHASE8_REPORT.md"

TRACKS = ["CD", "KEE", "SA", "GP", "SAR", "AQU", "BEL", "DMR", "MTH", "OP"]
N_BOOTSTRAP = 5000
N_PERMUTATIONS = 5000
RNG_SEED = 42


# ── Utility functions ──────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    print(f"Loading {CACHE_PATH.name}...")
    df = pd.read_pickle(CACHE_PATH)

    # Phase 7 features
    df["second_prob"] = df["fav_prob"] - df["prob_gap"]
    df["fav_dominance"] = df["fav_prob"] / df["top4_mass"].clip(lower=0.01)
    df["log_odds_ratio"] = np.log(
        df["fav_prob"].clip(lower=0.01) / df["second_prob"].clip(lower=0.01)
    )

    # Phase 8 new features
    # gap_ratio: relative dominance (how much of fav's strength is the gap?)
    df["gap_ratio"] = df["prob_gap"] / df["fav_prob"].clip(lower=0.01)

    # top4_residual: mass of runners 2-4 (excludes favorite)
    df["top4_residual"] = df["top4_mass"] - df["fav_prob"]

    # fav_concentration: fav_prob relative to field-implied average
    # If field is N runners, uniform would be 1/N. How many multiples is fav?
    df["fav_multiple"] = df["fav_prob"] * df["fs"]

    # Estimated entropy proxy from fav_prob and top4_mass:
    # lower entropy = more predictable field
    # Approx: fav contributes -p*log(p), rest of top4 split, remainder uniform
    p1 = df["fav_prob"].clip(0.01, 0.99)
    top4r = df["top4_residual"].clip(0.01, 0.99)
    rest_mass = (1.0 - df["top4_mass"]).clip(0.01, 0.99)
    n_rest = (df["fs"] - 4).clip(lower=1)
    # Entropy: -p1*log(p1) - top4r*log(top4r/3) - rest_mass*log(rest_mass/n_rest)
    df["entropy_proxy"] = (
        -p1 * np.log(p1)
        - top4r * np.log(top4r / 3.0)
        - rest_mass * np.log(rest_mass / n_rest)
    )

    # Chalk strength: how much does the top-2 dominate?
    df["top2_mass"] = df["fav_prob"] + df["second_prob"]

    print(f"  {len(df):,} races loaded, {len(df.columns)} features")
    return df


def compute_roi(mask: np.ndarray, hit: np.ndarray, payout: np.ndarray,
                cost: int) -> dict:
    n = int(mask.sum())
    if n == 0:
        return {"races": 0, "roi": -100.0, "hits": 0, "hit_rate": 0.0,
                "avg_pay": 0.0, "profit": 0.0, "wagered": 0}
    h = mask & hit
    hits = int(h.sum())
    wagered = n * cost
    returned = float(payout[h].sum())
    profit = returned - wagered
    roi = profit / wagered * 100.0
    return {
        "races": n, "wagered": wagered, "profit": round(profit, 2),
        "roi": round(roi, 2), "hits": hits,
        "hit_rate": round(hits / n * 100.0, 2),
        "avg_pay": round(returned / hits, 2) if hits else 0.0,
    }


def loocv_years(mask: np.ndarray, hit: np.ndarray, payout: np.ndarray,
                year: np.ndarray, cost: int) -> dict:
    years = sorted(set(year[mask]))
    folds = []
    for y in years:
        test_m = mask & (year == y)
        s = compute_roi(test_m, hit, payout, cost)
        folds.append({"year": y, **s})
    pos = sum(1 for f in folds if f["roi"] > 0)
    rois = [f["roi"] for f in folds]
    return {
        "folds": folds,
        "pos_years": pos,
        "total_years": len(folds),
        "pos_ratio": pos / len(folds) if folds else 0,
        "median_roi": float(np.median(rois)) if rois else -100,
        "mean_roi": float(np.mean(rois)) if rois else -100,
    }


def block_bootstrap(mask: np.ndarray, hit: np.ndarray, payout: np.ndarray,
                    year: np.ndarray, cost: int,
                    n_boot: int = N_BOOTSTRAP, seed: int = RNG_SEED) -> dict:
    rng = np.random.default_rng(seed)
    years = sorted(set(year[mask]))
    n_years = len(years)
    if n_years < 3:
        return {"ci_lo": np.nan, "ci_hi": np.nan, "mean": np.nan,
                "p_loss": np.nan}

    year_profits = {}
    year_wagered = {}
    for y in years:
        ym = mask & (year == y)
        s = compute_roi(ym, hit, payout, cost)
        year_profits[y] = s["profit"]
        year_wagered[y] = s["wagered"]

    boot_rois = np.empty(n_boot)
    years_arr = np.array(years)
    for b in range(n_boot):
        sampled = rng.choice(years_arr, size=n_years, replace=True)
        total_profit = sum(year_profits[y] for y in sampled)
        total_wagered = sum(year_wagered[y] for y in sampled)
        boot_rois[b] = total_profit / total_wagered * 100.0 if total_wagered > 0 else -100.0

    return {
        "ci_lo": round(float(np.percentile(boot_rois, 2.5)), 2),
        "ci_hi": round(float(np.percentile(boot_rois, 97.5)), 2),
        "mean": round(float(boot_rois.mean()), 2),
        "median": round(float(np.median(boot_rois)), 2),
        "p_loss": round(float(np.mean(boot_rois < 0)), 4),
    }


def permutation_test(mask: np.ndarray, hit: np.ndarray, payout: np.ndarray,
                     pool_mask: np.ndarray, cost: int,
                     n_perms: int = N_PERMUTATIONS, seed: int = RNG_SEED) -> dict:
    rng = np.random.default_rng(seed)
    n = int(mask.sum())
    if n < 5:
        return {"p_roi": np.nan, "p_hr": np.nan}

    obs = compute_roi(mask, hit, payout, cost)
    pool_idxs = np.where(pool_mask)[0]
    pool_hit = hit[pool_idxs]
    pool_pay = payout[pool_idxs]
    pool_n = len(pool_idxs)

    perm_rois = np.empty(n_perms)
    wagered = n * cost
    for p in range(n_perms):
        sample = rng.choice(pool_n, size=n, replace=False)
        s_hit = pool_hit[sample]
        s_pay = pool_pay[sample]
        ret = float(s_pay[s_hit].sum())
        perm_rois[p] = (ret - wagered) / wagered * 100.0

    return {
        "p_roi": round(float(np.mean(perm_rois >= obs["roi"])), 5),
    }


def walk_forward_expanding(mask: np.ndarray, hit: np.ndarray,
                           payout: np.ndarray, year: np.ndarray,
                           cost: int, min_train_years: int = 3) -> list[dict]:
    """Expanding walk-forward: train on all prior years, test on next year."""
    years = sorted(set(year[mask]))
    results = []
    for i in range(min_train_years, len(years)):
        test_y = years[i]
        train_ys = years[:i]
        train_m = mask & np.isin(year, train_ys)
        test_m = mask & (year == test_y)
        ts = compute_roi(train_m, hit, payout, cost)
        os_ = compute_roi(test_m, hit, payout, cost)
        results.append({
            "train": f"{train_ys[0]}-{train_ys[-1]}", "test": test_y,
            "train_n": ts["races"], "train_roi": ts["roi"],
            "test_n": os_["races"], "test_roi": os_["roi"],
        })
    return results


def walk_forward_rolling(mask: np.ndarray, hit: np.ndarray,
                         payout: np.ndarray, year: np.ndarray,
                         cost: int, window: int = 5) -> list[dict]:
    """Rolling walk-forward with fixed window."""
    years = sorted(set(year[mask]))
    results = []
    for i in range(window, len(years)):
        test_y = years[i]
        train_ys = years[i - window:i]
        train_m = mask & np.isin(year, train_ys)
        test_m = mask & (year == test_y)
        ts = compute_roi(train_m, hit, payout, cost)
        os_ = compute_roi(test_m, hit, payout, cost)
        results.append({
            "train": f"{train_ys[0]}-{train_ys[-1]}", "test": test_y,
            "train_n": ts["races"], "train_roi": ts["roi"],
            "test_n": os_["races"], "test_roi": os_["roi"],
        })
    return results


def _extract_arrays(df: pd.DataFrame, K: int) -> tuple:
    return (
        df["track"].to_numpy(),
        df["year"].to_numpy(dtype=np.int16),
        df["rnum"].to_numpy(dtype=np.int16),
        df["fs"].to_numpy(dtype=np.int16),
        df["fav_prob"].to_numpy(dtype=np.float64),
        df["prob_gap"].to_numpy(dtype=np.float64),
        df["is_fast"].to_numpy(dtype=bool),
        df[f"eligible_{K}"].to_numpy(dtype=bool),
    )


def filter_mask(track_arr, year_arr, rnum_arr, fs_arr, fav_prob_arr,
                prob_gap_arr, is_fast_arr, eligible_arr,
                track: str, fs_lo: int, fs_hi: int, gap: float,
                fav_min: float, cond: str, card: str,
                extra_mask=None) -> np.ndarray:
    m = (
        (track_arr == track)
        & eligible_arr
        & (fs_arr >= fs_lo) & (fs_arr <= fs_hi)
        & (prob_gap_arr >= gap)
        & (fav_prob_arr >= fav_min)
    )
    if cond == "fast":
        m &= is_fast_arr
    elif cond == "wet":
        m &= ~is_fast_arr
    if card == "midlate":
        m &= (rnum_arr >= 5)
    elif card == "late":
        m &= (rnum_arr >= 7)
    elif card == "verylate":
        m &= (rnum_arr >= 9)
    if extra_mask is not None:
        m &= extra_mask
    return m


# ── Phase 7 Baseline ──────────────────────────────────────────────

def phase7_baseline(df: pd.DataFrame) -> dict:
    """Reproduce Phase 7 portfolio for direct comparison."""
    print("\n" + "=" * 60)
    print("PHASE 7 BASELINE (for comparison)")
    print("=" * 60)

    year = df["year"].to_numpy(dtype=np.int16)
    payout = df["payout"].to_numpy(dtype=np.float64)

    K7 = 7
    cost7 = perm(K7 - 1, 3)  # 120
    hit7 = df[f"hit_{K7}"].to_numpy(dtype=bool)
    arrs7 = _extract_arrays(df, K7)

    K8 = 8
    cost8 = perm(K8 - 1, 3)  # 210
    hit8 = df[f"hit_{K8}"].to_numpy(dtype=bool)
    arrs8 = _extract_arrays(df, K8)

    rules = [
        ("BEL_broad1_K7", filter_mask(*arrs7, track="BEL", fs_lo=11, fs_hi=13,
         gap=0.22, fav_min=0.35, cond="fast", card="midlate"), hit7, cost7),
        ("OP_K7", filter_mask(*arrs7, track="OP", fs_lo=11, fs_hi=12,
         gap=0.05, fav_min=0.0, cond="all", card="late"), hit7, cost7),
        ("CD_K8", filter_mask(*arrs8, track="CD", fs_lo=10, fs_hi=11,
         gap=0.15, fav_min=0.0, cond="all", card="all"), hit8, cost8),
    ]

    years = sorted(df["year"].unique())
    total_wagered = 0
    total_profit = 0.0
    year_results = []

    for name, mask, hit_arr, cost_val in rules:
        s = compute_roi(mask, hit_arr, payout, cost_val)
        loocv = loocv_years(mask, hit_arr, payout, year, cost_val)
        print(f"  {name}: {s['races']} races, ROI {s['roi']:+.1f}%, "
              f"LOOCV {loocv['pos_years']}/{loocv['total_years']}")

    for y in years:
        y_wagered = 0
        y_profit = 0.0
        for name, mask, hit_arr, cost_val in rules:
            ym = mask & (year == y)
            s = compute_roi(ym, hit_arr, payout, cost_val)
            y_wagered += s["wagered"]
            y_profit += s["profit"]
        if y_wagered > 0:
            y_roi = y_profit / y_wagered * 100
            year_results.append({"year": y, "wagered": y_wagered,
                                 "profit": round(y_profit, 2),
                                 "roi": round(y_roi, 2)})
            total_wagered += y_wagered
            total_profit += y_profit

    total_races = sum(r[1].sum() for r in rules)
    total_roi = total_profit / total_wagered * 100 if total_wagered > 0 else 0
    pos_years = sum(1 for yr in year_results if yr["roi"] > 0)

    print(f"\n  Phase 7 Portfolio: {total_races} races, ROI {total_roi:+.1f}%, "
          f"{pos_years}/{len(year_results)} positive years")

    return {
        "total_races": int(total_races),
        "total_roi": round(total_roi, 2),
        "total_wagered": total_wagered,
        "total_profit": round(total_profit, 2),
        "pos_years": pos_years,
        "n_years": len(year_results),
        "year_results": year_results,
    }


# ── Section 1: Enhanced Feature Search ─────────────────────────────

def enhanced_feature_search(df: pd.DataFrame) -> pd.DataFrame:
    """Massively expanded search with new features and K=9."""
    print("\n" + "=" * 60)
    print("SECTION 1: ENHANCED SEARCH (new features + K=9)")
    print("=" * 60)

    year = df["year"].to_numpy(dtype=np.int16)
    month = df["month"].to_numpy(dtype=np.int16)
    payout = df["payout"].to_numpy(dtype=np.float64)
    gap_ratio = df["gap_ratio"].to_numpy(dtype=np.float64)
    entropy = df["entropy_proxy"].to_numpy(dtype=np.float64)
    top2_mass = df["top2_mass"].to_numpy(dtype=np.float64)
    fav_multiple = df["fav_multiple"].to_numpy(dtype=np.float64)

    FS_BINS = [(10, 11), (10, 12), (11, 12), (11, 13), (11, 14), (12, 13), (12, 14)]
    GAPS = [0.0, 0.05, 0.10, 0.15, 0.20, 0.22, 0.25]
    FAV_MINS = [0.00, 0.30, 0.35, 0.40]
    CONDS = ["all", "fast"]
    CARDS = ["all", "midlate", "late", "verylate"]
    MIN_RACES = 40  # Lower threshold to catch small pockets

    # Monthly seasons
    MONTHS = {
        "all": None,
        "winter": [1, 2, 3],
        "spring": [4, 5, 6],
        "fall": [9, 10, 11],
    }

    rows = []
    n_tested = 0

    for K in [7, 8, 9]:
        cost = perm(K - 1, 3)
        hit = df[f"hit_{K}"].to_numpy(dtype=bool)
        arrs = _extract_arrays(df, K)

        for track in TRACKS:
            for fs_lo, fs_hi in FS_BINS:
                for gap in GAPS:
                    for fav_min in FAV_MINS:
                        for cond in CONDS:
                            for card in CARDS:
                                for season_name, season_months in MONTHS.items():
                                    n_tested += 1

                                    params = {
                                        "track": track, "fs_lo": fs_lo,
                                        "fs_hi": fs_hi, "gap": gap,
                                        "fav_min": fav_min, "cond": cond,
                                        "card": card,
                                    }

                                    # Build month mask
                                    month_mask = None
                                    if season_months is not None:
                                        month_mask = np.isin(month, season_months)

                                    m = filter_mask(*arrs, **params,
                                                    extra_mask=month_mask)
                                    n_races = int(m.sum())
                                    if n_races < MIN_RACES:
                                        continue

                                    s = compute_roi(m, hit, payout, cost)
                                    if s["roi"] <= -20:
                                        continue

                                    loocv = loocv_years(m, hit, payout, year, cost)

                                    # Train/test split
                                    train_m = m & (year <= 2018)
                                    test_m = m & (year >= 2019)
                                    train_s = compute_roi(train_m, hit, payout, cost)
                                    test_s = compute_roi(test_m, hit, payout, cost)

                                    label = (f"K1W{K}_{track}_FS{fs_lo}-{fs_hi}_"
                                             f"Gap{gap:.2f}_Fav{fav_min:.2f}_"
                                             f"{cond}_{card}_{season_name}")
                                    rows.append({
                                        "Strategy": label, "K": K,
                                        "Track": track,
                                        "FS": f"{fs_lo}-{fs_hi}",
                                        "Gap": gap, "FavMin": fav_min,
                                        "Cond": cond, "Card": card,
                                        "Season": season_name,
                                        "Races": s["races"],
                                        "Hits": s["hits"],
                                        "ROI%": s["roi"],
                                        "HitRate%": s["hit_rate"],
                                        "AvgPay": s["avg_pay"],
                                        "TrainROI%": train_s["roi"],
                                        "TestROI%": test_s["roi"],
                                        "LOOCV_PosYrs": f"{loocv['pos_years']}/{loocv['total_years']}",
                                        "LOOCV_PosRatio": round(loocv["pos_ratio"], 3),
                                        "LOOCV_MedianROI": loocv["median_roi"],
                                    })

                    if n_tested % 20000 == 0:
                        print(f"  ... {n_tested:,} variants tested, "
                              f"{len(rows)} passing")

    print(f"  Total tested: {n_tested:,}, passing: {len(rows)}")
    result_df = pd.DataFrame(rows)
    if result_df.empty:
        return result_df

    result_df = result_df.sort_values(
        ["LOOCV_PosRatio", "ROI%", "Races"],
        ascending=[False, False, False],
    )
    return result_df


# ── Section 2: Feature-Gated Refinement ────────────────────────────

def feature_gated_refinement(df: pd.DataFrame, search_df: pd.DataFrame) -> list[dict]:
    """Take top rules from search and try adding feature gates."""
    print("\n" + "=" * 60)
    print("SECTION 2: FEATURE-GATED REFINEMENT")
    print("=" * 60)

    if search_df.empty:
        print("  No search results to refine.")
        return []

    year = df["year"].to_numpy(dtype=np.int16)
    month = df["month"].to_numpy(dtype=np.int16)
    payout = df["payout"].to_numpy(dtype=np.float64)
    gap_ratio = df["gap_ratio"].to_numpy(dtype=np.float64)
    entropy = df["entropy_proxy"].to_numpy(dtype=np.float64)
    top2_mass = df["top2_mass"].to_numpy(dtype=np.float64)
    fav_multiple = df["fav_multiple"].to_numpy(dtype=np.float64)

    # Top candidates: profitable, good LOOCV, different tracks
    top = search_df[
        (search_df["ROI%"] > 5)
        & (search_df["LOOCV_PosRatio"] >= 0.55)
        & (search_df["Races"] >= 40)
    ].head(50)

    MONTHS_MAP = {
        "all": None,
        "winter": [1, 2, 3],
        "spring": [4, 5, 6],
        "fall": [9, 10, 11],
    }

    # Feature gates to try
    feature_gates = {
        "gap_ratio>=0.30": gap_ratio >= 0.30,
        "gap_ratio>=0.40": gap_ratio >= 0.40,
        "gap_ratio>=0.50": gap_ratio >= 0.50,
        "top2>=0.55": top2_mass >= 0.55,
        "top2>=0.60": top2_mass >= 0.60,
        "top2>=0.65": top2_mass >= 0.65,
        "fav_mult>=3.0": fav_multiple >= 3.0,
        "fav_mult>=3.5": fav_multiple >= 3.5,
        "fav_mult>=4.0": fav_multiple >= 4.0,
        "entropy<=1.5": entropy <= 1.5,
        "entropy<=1.8": entropy <= 1.8,
    }

    refined = []
    for _, row in top.iterrows():
        k = row["K"]
        cost = perm(k - 1, 3)
        hit = df[f"hit_{k}"].to_numpy(dtype=bool)
        arrs = _extract_arrays(df, k)

        season_months = MONTHS_MAP.get(row["Season"])
        month_mask = np.isin(month, season_months) if season_months else None

        params = {
            "track": row["Track"],
            "fs_lo": int(row["FS"].split("-")[0]),
            "fs_hi": int(row["FS"].split("-")[1]),
            "gap": row["Gap"], "fav_min": row["FavMin"],
            "cond": row["Cond"], "card": row["Card"],
        }
        base_m = filter_mask(*arrs, **params, extra_mask=month_mask)
        base_s = compute_roi(base_m, hit, payout, cost)
        base_loocv = loocv_years(base_m, hit, payout, year, cost)

        for gate_name, gate_mask in feature_gates.items():
            m = base_m & gate_mask
            n = int(m.sum())
            if n < 30:
                continue
            s = compute_roi(m, hit, payout, cost)
            if s["roi"] <= base_s["roi"]:
                continue

            loocv = loocv_years(m, hit, payout, year, cost)
            if loocv["pos_ratio"] < base_loocv["pos_ratio"]:
                continue

            # Genuine improvement: higher ROI AND same/better LOOCV
            refined.append({
                "base": row["Strategy"],
                "gate": gate_name,
                "races": s["races"],
                "roi": s["roi"],
                "base_roi": base_s["roi"],
                "loocv_pos": f"{loocv['pos_years']}/{loocv['total_years']}",
                "loocv_ratio": loocv["pos_ratio"],
                "median_roi": loocv["median_roi"],
                "K": k, "Track": row["Track"],
            })

    refined.sort(key=lambda x: (-x["loocv_ratio"], -x["roi"]))
    print(f"\n  Found {len(refined)} feature-gated improvements")
    for r in refined[:20]:
        print(f"    {r['base']} + {r['gate']}: {r['races']} races, "
              f"ROI {r['roi']:+.1f}% (base {r['base_roi']:+.1f}%), "
              f"LOOCV {r['loocv_pos']}")

    return refined


# ── Section 3: OP Refinement ───────────────────────────────────────

def refine_op(df: pd.DataFrame) -> dict:
    """Deep dive into OP: monthly splits, tighter filters, feature gates."""
    print("\n" + "=" * 60)
    print("SECTION 3: OP REFINEMENT")
    print("=" * 60)

    K = 7
    cost = perm(K - 1, 3)
    hit = df[f"hit_{K}"].to_numpy(dtype=bool)
    payout = df["payout"].to_numpy(dtype=np.float64)
    year = df["year"].to_numpy(dtype=np.int16)
    month = df["month"].to_numpy(dtype=np.int16)
    arrs = _extract_arrays(df, K)

    gap_ratio = df["gap_ratio"].to_numpy(dtype=np.float64)
    top2_mass = df["top2_mass"].to_numpy(dtype=np.float64)
    fav_multiple = df["fav_multiple"].to_numpy(dtype=np.float64)

    # Base OP rule from Phase 7
    base_params = {"track": "OP", "fs_lo": 11, "fs_hi": 12, "gap": 0.05,
                   "fav_min": 0.0, "cond": "all", "card": "late"}
    base_m = filter_mask(*arrs, **base_params)
    base_s = compute_roi(base_m, hit, payout, cost)
    base_loocv = loocv_years(base_m, hit, payout, year, cost)
    print(f"\n  OP base: {base_s['races']} races, ROI {base_s['roi']:+.1f}%, "
          f"LOOCV {base_loocv['pos_years']}/{base_loocv['total_years']}")

    results = {"base": base_s}

    # Monthly breakdown
    print("\n  Monthly breakdown (base OP):")
    for m_val in range(1, 13):
        mm = base_m & (month == m_val)
        s = compute_roi(mm, hit, payout, cost)
        if s["races"] > 0:
            print(f"    Month {m_val:>2}: {s['races']:>4} races, ROI {s['roi']:>+8.1f}%, "
                  f"HR {s['hit_rate']:.1f}%")
            results[f"month_{m_val}"] = s

    # OP with tighter gap
    print("\n  OP gap sweep:")
    best_op = None
    for gap in [0.05, 0.10, 0.15, 0.20]:
        for fav_min in [0.0, 0.25, 0.30, 0.35]:
            for card in ["late", "verylate"]:
                for fs_hi in [12, 13]:
                    params = {"track": "OP", "fs_lo": 11, "fs_hi": fs_hi,
                              "gap": gap, "fav_min": fav_min, "cond": "all",
                              "card": card}
                    m = filter_mask(*arrs, **params)
                    s = compute_roi(m, hit, payout, cost)
                    if s["races"] < 40:
                        continue
                    loocv = loocv_years(m, hit, payout, year, cost)
                    if loocv["pos_ratio"] >= 0.6 and s["roi"] > 30:
                        if best_op is None or s["roi"] > best_op["roi"]:
                            best_op = {**s, "params": params,
                                       "loocv": loocv, "label": str(params)}

    if best_op:
        print(f"  Best OP variant: {best_op['races']} races, "
              f"ROI {best_op['roi']:+.1f}%, "
              f"LOOCV {best_op['loocv']['pos_years']}/{best_op['loocv']['total_years']}")
        print(f"    Params: {best_op['params']}")
        results["best_variant"] = best_op

    # OP with feature gates
    print("\n  OP + feature gates:")
    gates = [
        ("gap_ratio>=0.15", gap_ratio >= 0.15),
        ("gap_ratio>=0.20", gap_ratio >= 0.20),
        ("gap_ratio>=0.30", gap_ratio >= 0.30),
        ("top2>=0.50", top2_mass >= 0.50),
        ("top2>=0.55", top2_mass >= 0.55),
        ("fav_mult>=2.5", fav_multiple >= 2.5),
        ("fav_mult>=3.0", fav_multiple >= 3.0),
        ("fav_mult>=3.5", fav_multiple >= 3.5),
    ]
    for gate_name, gate_mask in gates:
        m = base_m & gate_mask
        s = compute_roi(m, hit, payout, cost)
        if s["races"] >= 30:
            loocv = loocv_years(m, hit, payout, year, cost)
            improved = "***" if s["roi"] > base_s["roi"] and loocv["pos_ratio"] >= base_loocv["pos_ratio"] else ""
            print(f"    OP + {gate_name}: {s['races']:>4} races, "
                  f"ROI {s['roi']:>+8.1f}%, "
                  f"LOOCV {loocv['pos_years']}/{loocv['total_years']} {improved}")
            results[f"gate_{gate_name}"] = {**s, "loocv": loocv}

    # OP monthly-restricted variants
    print("\n  OP month-restricted:")
    for months_name, months_list in [("jan-mar", [1, 2, 3]), ("feb-apr", [2, 3, 4]),
                                      ("jan-apr", [1, 2, 3, 4]), ("mar-may", [3, 4, 5])]:
        mm = base_m & np.isin(month, months_list)
        s = compute_roi(mm, hit, payout, cost)
        if s["races"] >= 30:
            loocv = loocv_years(mm, hit, payout, year, cost)
            print(f"    OP {months_name}: {s['races']:>4} races, "
                  f"ROI {s['roi']:>+8.1f}%, "
                  f"LOOCV {loocv['pos_years']}/{loocv['total_years']}")

    return results


# ── Section 4: CD Refinement ───────────────────────────────────────

def refine_cd(df: pd.DataFrame) -> dict:
    """Deep dive into CD: improve the weakest portfolio leg."""
    print("\n" + "=" * 60)
    print("SECTION 4: CD REFINEMENT")
    print("=" * 60)

    year = df["year"].to_numpy(dtype=np.int16)
    month = df["month"].to_numpy(dtype=np.int16)
    payout = df["payout"].to_numpy(dtype=np.float64)

    gap_ratio = df["gap_ratio"].to_numpy(dtype=np.float64)
    top2_mass = df["top2_mass"].to_numpy(dtype=np.float64)
    fav_multiple = df["fav_multiple"].to_numpy(dtype=np.float64)

    results = {}
    best_cd = {"roi": -100}

    for K in [7, 8, 9]:
        cost = perm(K - 1, 3)
        hit = df[f"hit_{K}"].to_numpy(dtype=bool)
        arrs = _extract_arrays(df, K)

        # Broad CD sweep
        for fs_lo, fs_hi in [(10, 11), (10, 12), (10, 13), (11, 12), (11, 13)]:
            for gap in [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]:
                for fav_min in [0.0, 0.25, 0.30, 0.35, 0.40]:
                    for cond in ["all", "fast"]:
                        for card in ["all", "midlate", "late"]:
                            params = {"track": "CD", "fs_lo": fs_lo,
                                      "fs_hi": fs_hi, "gap": gap,
                                      "fav_min": fav_min, "cond": cond,
                                      "card": card}
                            m = filter_mask(*arrs, **params)
                            s = compute_roi(m, hit, payout, cost)
                            if s["races"] < 50 or s["roi"] <= 0:
                                continue
                            loocv = loocv_years(m, hit, payout, year, cost)
                            if loocv["pos_ratio"] < 0.5:
                                continue

                            # Feature gates
                            for gate_name, gate_mask in [
                                ("none", None),
                                ("gap_ratio>=0.30", gap_ratio >= 0.30),
                                ("gap_ratio>=0.40", gap_ratio >= 0.40),
                                ("top2>=0.55", top2_mass >= 0.55),
                                ("fav_mult>=3.0", fav_multiple >= 3.0),
                                ("fav_mult>=3.5", fav_multiple >= 3.5),
                            ]:
                                if gate_mask is not None:
                                    mg = m & gate_mask
                                else:
                                    mg = m
                                sg = compute_roi(mg, hit, payout, cost)
                                if sg["races"] < 40 or sg["roi"] <= 0:
                                    continue
                                loocv_g = loocv_years(mg, hit, payout, year, cost)
                                if loocv_g["pos_ratio"] < 0.5:
                                    continue

                                # Score: combine ROI, LOOCV, and sample size
                                score = (sg["roi"] * loocv_g["pos_ratio"]
                                         * min(sg["races"] / 100, 1.0))
                                if score > best_cd.get("score", -999):
                                    best_cd = {
                                        **sg, "params": params, "K": K,
                                        "gate": gate_name, "loocv": loocv_g,
                                        "score": score,
                                    }

    if best_cd["roi"] > -100:
        print(f"\n  Best CD: K={best_cd['K']}, {best_cd['races']} races, "
              f"ROI {best_cd['roi']:+.1f}%, "
              f"LOOCV {best_cd['loocv']['pos_years']}/{best_cd['loocv']['total_years']}, "
              f"gate={best_cd['gate']}")
        print(f"    Params: {best_cd['params']}")
        results["best"] = best_cd

    # Also check CD base for monthly patterns
    K8 = 8
    cost8 = perm(K8 - 1, 3)
    hit8 = df[f"hit_{K8}"].to_numpy(dtype=bool)
    arrs8 = _extract_arrays(df, K8)
    base_cd = filter_mask(*arrs8, track="CD", fs_lo=10, fs_hi=11,
                           gap=0.15, fav_min=0.0, cond="all", card="all")
    print("\n  CD K8 base monthly breakdown:")
    for m_val in range(1, 13):
        mm = base_cd & (month == m_val)
        s = compute_roi(mm, hit8, payout, cost8)
        if s["races"] > 0:
            print(f"    Month {m_val:>2}: {s['races']:>4} races, "
                  f"ROI {s['roi']:>+8.1f}%, HR {s['hit_rate']:.1f}%")

    return results


# ── Section 5: New Track Discovery ─────────────────────────────────

def new_track_discovery(df: pd.DataFrame, search_df: pd.DataFrame) -> dict:
    """Look for undiscovered pockets at non-portfolio tracks."""
    print("\n" + "=" * 60)
    print("SECTION 5: NEW TRACK DISCOVERY")
    print("=" * 60)

    if search_df.empty:
        print("  No search results.")
        return {}

    year = df["year"].to_numpy(dtype=np.int16)
    payout = df["payout"].to_numpy(dtype=np.float64)
    gap_ratio = df["gap_ratio"].to_numpy(dtype=np.float64)
    top2_mass = df["top2_mass"].to_numpy(dtype=np.float64)
    fav_multiple = df["fav_multiple"].to_numpy(dtype=np.float64)

    # Find best rules at non-portfolio tracks
    non_portfolio = search_df[
        ~search_df["Track"].isin(["BEL", "OP", "CD"])
        & (search_df["ROI%"] > 0)
        & (search_df["LOOCV_PosRatio"] >= 0.5)
        & (search_df["Races"] >= 40)
    ].copy()

    if non_portfolio.empty:
        print("  No promising non-portfolio tracks.")
        return {}

    # Group by track, take best per track
    best_per_track = {}
    for track in non_portfolio["Track"].unique():
        track_df = non_portfolio[non_portfolio["Track"] == track]
        best = track_df.sort_values(
            ["LOOCV_PosRatio", "ROI%"], ascending=[False, False]
        ).head(1).iloc[0]
        best_per_track[track] = best

    print(f"\n  Best rule per non-portfolio track:")
    discoveries = {}
    for track, row in sorted(best_per_track.items(),
                              key=lambda x: -x[1]["ROI%"]):
        print(f"    {track}: {row['Strategy']}")
        print(f"      {row['Races']} races, ROI {row['ROI%']:+.1f}%, "
              f"LOOCV {row['LOOCV_PosYrs']}, "
              f"Train {row['TrainROI%']:+.1f}%, Test {row['TestROI%']:+.1f}%")

        # Full robustness check on top candidates
        k = row["K"]
        cost = perm(k - 1, 3)
        hit = df[f"hit_{k}"].to_numpy(dtype=bool)
        arrs = _extract_arrays(df, k)

        season_map = {"all": None, "winter": [1, 2, 3],
                      "spring": [4, 5, 6], "fall": [9, 10, 11]}
        season_months = season_map.get(row["Season"])
        month_arr = df["month"].to_numpy(dtype=np.int16)
        month_mask = np.isin(month_arr, season_months) if season_months else None

        params = {
            "track": row["Track"],
            "fs_lo": int(row["FS"].split("-")[0]),
            "fs_hi": int(row["FS"].split("-")[1]),
            "gap": row["Gap"], "fav_min": row["FavMin"],
            "cond": row["Cond"], "card": row["Card"],
        }
        m = filter_mask(*arrs, **params, extra_mask=month_mask)
        s = compute_roi(m, hit, payout, cost)
        loocv = loocv_years(m, hit, payout, year, cost)
        bb = block_bootstrap(m, hit, payout, year, cost)

        print(f"      Block bootstrap CI: [{bb['ci_lo']:+.1f}%, {bb['ci_hi']:+.1f}%], "
              f"P(loss): {bb.get('p_loss', 'N/A')}")

        # Test feature gates
        best_gated = None
        for gate_name, gate_mask in [
            ("gap_ratio>=0.30", gap_ratio >= 0.30),
            ("gap_ratio>=0.40", gap_ratio >= 0.40),
            ("top2>=0.55", top2_mass >= 0.55),
            ("fav_mult>=3.0", fav_multiple >= 3.0),
        ]:
            mg = m & gate_mask
            sg = compute_roi(mg, hit, payout, cost)
            if sg["races"] >= 30 and sg["roi"] > s["roi"]:
                lg = loocv_years(mg, hit, payout, year, cost)
                if lg["pos_ratio"] >= loocv["pos_ratio"]:
                    print(f"      + {gate_name}: {sg['races']} races, "
                          f"ROI {sg['roi']:+.1f}%, "
                          f"LOOCV {lg['pos_years']}/{lg['total_years']}")
                    if best_gated is None or sg["roi"] > best_gated["roi"]:
                        best_gated = {**sg, "gate": gate_name, "loocv": lg}

        discoveries[track] = {
            "strategy": row["Strategy"],
            "stats": s, "loocv": loocv, "bootstrap": bb,
            "params": params, "K": k, "season": row["Season"],
            "best_gated": best_gated,
        }

    return discoveries


# ── Section 6: Optimized Portfolio Construction ────────────────────

def build_optimized_portfolio(df: pd.DataFrame, search_df: pd.DataFrame,
                              op_results: dict, cd_results: dict,
                              discoveries: dict) -> dict:
    """Build the best portfolio by scoring and selecting rules."""
    print("\n" + "=" * 60)
    print("SECTION 6: OPTIMIZED PORTFOLIO CONSTRUCTION")
    print("=" * 60)

    year = df["year"].to_numpy(dtype=np.int16)
    month = df["month"].to_numpy(dtype=np.int16)
    payout = df["payout"].to_numpy(dtype=np.float64)
    gap_ratio = df["gap_ratio"].to_numpy(dtype=np.float64)
    top2_mass = df["top2_mass"].to_numpy(dtype=np.float64)
    fav_multiple = df["fav_multiple"].to_numpy(dtype=np.float64)

    # Assemble candidate rules
    candidates = []

    # BEL broad1 (Phase 7, always include as anchor)
    K7 = 7
    cost7 = perm(K7 - 1, 3)
    hit7 = df[f"hit_{K7}"].to_numpy(dtype=bool)
    arrs7 = _extract_arrays(df, K7)

    bel_m = filter_mask(*arrs7, track="BEL", fs_lo=11, fs_hi=13, gap=0.22,
                         fav_min=0.35, cond="fast", card="midlate")
    candidates.append(("BEL_broad1_K7", bel_m, hit7, cost7, "BEL"))

    # Best OP variant
    # Try both base and any improvement found
    op_base_m = filter_mask(*arrs7, track="OP", fs_lo=11, fs_hi=12,
                            gap=0.05, fav_min=0.0, cond="all", card="late")
    candidates.append(("OP_base_K7", op_base_m, hit7, cost7, "OP"))

    if "best_variant" in op_results:
        bv = op_results["best_variant"]
        op_var_m = filter_mask(*arrs7, **bv["params"])
        candidates.append(("OP_refined", op_var_m, hit7, cost7, "OP"))

    # Best CD
    K8 = 8
    cost8 = perm(K8 - 1, 3)
    hit8 = df[f"hit_{K8}"].to_numpy(dtype=bool)
    arrs8 = _extract_arrays(df, K8)

    cd_base_m = filter_mask(*arrs8, track="CD", fs_lo=10, fs_hi=11,
                            gap=0.15, fav_min=0.0, cond="all", card="all")
    candidates.append(("CD_base_K8", cd_base_m, hit8, cost8, "CD"))

    if "best" in cd_results and cd_results["best"]["roi"] > 13.1:
        bcd = cd_results["best"]
        k_cd = bcd["K"]
        cost_cd = perm(k_cd - 1, 3)
        hit_cd = df[f"hit_{k_cd}"].to_numpy(dtype=bool)
        arrs_cd = _extract_arrays(df, k_cd)
        cd_ref_m = filter_mask(*arrs_cd, **bcd["params"])
        if bcd["gate"] != "none":
            gate_masks = {
                "gap_ratio>=0.30": gap_ratio >= 0.30,
                "gap_ratio>=0.40": gap_ratio >= 0.40,
                "top2>=0.55": top2_mass >= 0.55,
                "fav_mult>=3.0": fav_multiple >= 3.0,
                "fav_mult>=3.5": fav_multiple >= 3.5,
            }
            if bcd["gate"] in gate_masks:
                cd_ref_m = cd_ref_m & gate_masks[bcd["gate"]]
        candidates.append((f"CD_refined_K{k_cd}", cd_ref_m, hit_cd, cost_cd, "CD"))

    # K=9 candidates
    K9 = 9
    cost9 = perm(K9 - 1, 3)  # 336
    hit9 = df[f"hit_{K9}"].to_numpy(dtype=bool)
    arrs9 = _extract_arrays(df, K9)

    if not search_df.empty:
        k9_rules = search_df[
            (search_df["K"] == 9)
            & (search_df["ROI%"] > 10)
            & (search_df["LOOCV_PosRatio"] >= 0.5)
            & (search_df["Races"] >= 40)
        ].head(5)
        for _, row in k9_rules.iterrows():
            season_map = {"all": None, "winter": [1, 2, 3],
                          "spring": [4, 5, 6], "fall": [9, 10, 11]}
            season_months = season_map.get(row["Season"])
            month_mask = np.isin(month, season_months) if season_months else None
            params = {
                "track": row["Track"],
                "fs_lo": int(row["FS"].split("-")[0]),
                "fs_hi": int(row["FS"].split("-")[1]),
                "gap": row["Gap"], "fav_min": row["FavMin"],
                "cond": row["Cond"], "card": row["Card"],
            }
            m9 = filter_mask(*arrs9, **params, extra_mask=month_mask)
            candidates.append((f"K9_{row['Strategy']}", m9, hit9, cost9,
                               row["Track"]))

    # Discovery tracks
    for track, disc in discoveries.items():
        k = disc["K"]
        cost_d = perm(k - 1, 3)
        hit_d = df[f"hit_{k}"].to_numpy(dtype=bool)
        arrs_d = _extract_arrays(df, k)
        season_map = {"all": None, "winter": [1, 2, 3],
                      "spring": [4, 5, 6], "fall": [9, 10, 11]}
        season_months = season_map.get(disc["season"])
        month_mask = np.isin(month, season_months) if season_months else None
        m_d = filter_mask(*arrs_d, **disc["params"], extra_mask=month_mask)
        candidates.append((f"DISC_{track}", m_d, hit_d, cost_d, track))

    # Score each candidate
    print(f"\n  Scoring {len(candidates)} candidates...")
    scored = []
    for name, mask, hit_arr, cost_val, track in candidates:
        s = compute_roi(mask, hit_arr, payout, cost_val)
        if s["races"] == 0 or s["roi"] <= -50:
            continue
        loocv = loocv_years(mask, hit_arr, payout, year, cost_val)
        bb = block_bootstrap(mask, hit_arr, payout, year, cost_val)

        # Walk-forward
        wf = walk_forward_expanding(mask, hit_arr, payout, year, cost_val)
        wf_pos = sum(1 for r in wf if r["test_n"] > 0 and r["test_roi"] > 0)
        wf_tot = sum(1 for r in wf if r["test_n"] > 0)

        # Composite quality score
        # Heavily weight LOOCV ratio, bootstrap CI lower bound, and walk-forward
        ci_lo = bb.get("ci_lo", -100) if not np.isnan(bb.get("ci_lo", np.nan)) else -100
        p_loss = bb.get("p_loss", 1.0) if not np.isnan(bb.get("p_loss", np.nan)) else 1.0
        wf_ratio = wf_pos / wf_tot if wf_tot > 0 else 0

        quality_score = (
            s["roi"] * 0.20
            + loocv["pos_ratio"] * 100 * 0.25
            + max(ci_lo, -50) * 0.15
            + (1 - p_loss) * 100 * 0.20
            + wf_ratio * 100 * 0.20
        )

        scored.append({
            "name": name, "mask": mask, "hit": hit_arr,
            "cost": cost_val, "track": track,
            "stats": s, "loocv": loocv, "bootstrap": bb,
            "wf_pos": wf_pos, "wf_tot": wf_tot,
            "quality_score": round(quality_score, 2),
        })

        print(f"    {name}: {s['races']} races, ROI {s['roi']:+.1f}%, "
              f"LOOCV {loocv['pos_years']}/{loocv['total_years']}, "
              f"BB [{ci_lo:+.1f}%, {bb.get('ci_hi', 0):+.1f}%], "
              f"WF {wf_pos}/{wf_tot}, Score={quality_score:.1f}")

    scored.sort(key=lambda x: -x["quality_score"])

    # Build portfolio: pick best per track, no overlap
    # Require minimum sample size and LOOCV quality to avoid overfit pockets
    MIN_PORTFOLIO_RACES = 60
    MIN_LOOCV_RATIO = 0.50
    print(f"\n  Building portfolio (best per track, min {MIN_PORTFOLIO_RACES} races, "
          f"LOOCV >= {MIN_LOOCV_RATIO:.0%})...")
    selected_tracks = set()
    portfolio_rules = []
    for cand in scored:
        if cand["track"] in selected_tracks:
            continue
        if cand["stats"]["roi"] <= 0:
            continue
        if cand["stats"]["races"] < MIN_PORTFOLIO_RACES:
            continue
        if cand["loocv"]["pos_ratio"] < MIN_LOOCV_RATIO:
            continue

        selected_tracks.add(cand["track"])
        portfolio_rules.append(cand)
        print(f"    SELECTED: {cand['name']} ({cand['track']}): "
              f"{cand['stats']['races']} races, ROI {cand['stats']['roi']:+.1f}%, "
              f"Score={cand['quality_score']:.1f}")

    # Evaluate portfolio
    if not portfolio_rules:
        print("  ERROR: No rules selected!")
        return {"portfolio_rules": [], "total_roi": -100}

    years = sorted(df["year"].unique())
    year_results = []
    total_wagered = 0
    total_profit = 0.0

    for y in years:
        y_wagered = 0
        y_profit = 0.0
        y_detail = {}
        for rule in portfolio_rules:
            ym = rule["mask"] & (year == y)
            s = compute_roi(ym, rule["hit"], payout, rule["cost"])
            y_wagered += s["wagered"]
            y_profit += s["profit"]
            y_detail[rule["name"]] = s["races"]
        if y_wagered > 0:
            y_roi = y_profit / y_wagered * 100
            year_results.append({
                "year": y, "wagered": y_wagered,
                "profit": round(y_profit, 2),
                "roi": round(y_roi, 2),
                **{f"n_{r['name']}": y_detail.get(r["name"], 0) for r in portfolio_rules}
            })
            total_wagered += y_wagered
            total_profit += y_profit

    total_races = sum(r["stats"]["races"] for r in portfolio_rules)
    total_roi = total_profit / total_wagered * 100 if total_wagered > 0 else 0
    pos_years = sum(1 for yr in year_results if yr["roi"] > 0)

    # Portfolio block bootstrap
    print(f"\n  Portfolio: {total_races} races, ROI {total_roi:+.1f}%, "
          f"{pos_years}/{len(year_results)} positive years")

    # Block bootstrap on portfolio
    rng = np.random.default_rng(RNG_SEED)
    yr_arr = np.array([yr["year"] for yr in year_results])
    yr_profits = np.array([yr["profit"] for yr in year_results])
    yr_wagered_arr = np.array([yr["wagered"] for yr in year_results])
    n_yrs = len(year_results)

    if n_yrs >= 3:
        boot_rois = np.empty(N_BOOTSTRAP)
        for b in range(N_BOOTSTRAP):
            idx = rng.choice(n_yrs, size=n_yrs, replace=True)
            tp = yr_profits[idx].sum()
            tw = yr_wagered_arr[idx].sum()
            boot_rois[b] = tp / tw * 100 if tw > 0 else -100
        port_ci_lo = float(np.percentile(boot_rois, 2.5))
        port_ci_hi = float(np.percentile(boot_rois, 97.5))
        port_p_loss = float(np.mean(boot_rois < 0))
        print(f"  Portfolio bootstrap CI: [{port_ci_lo:+.1f}%, {port_ci_hi:+.1f}%], "
              f"P(loss): {port_p_loss:.1%}")
    else:
        port_ci_lo, port_ci_hi, port_p_loss = np.nan, np.nan, np.nan

    print(f"\n  Year-by-year:")
    print(f"    {'Year':>6} {'Wagered':>10} {'Profit':>10} {'ROI':>8}")
    for yr in year_results:
        print(f"    {yr['year']:>6} {yr['wagered']:>10,} {yr['profit']:>+10,.0f} "
              f"{yr['roi']:>+8.1f}%")

    return {
        "portfolio_rules": portfolio_rules,
        "year_results": year_results,
        "total_races": total_races,
        "total_roi": round(total_roi, 2),
        "total_wagered": total_wagered,
        "total_profit": round(total_profit, 2),
        "pos_years": pos_years,
        "n_years": len(year_results),
        "ci_lo": round(port_ci_lo, 2) if not np.isnan(port_ci_lo) else None,
        "ci_hi": round(port_ci_hi, 2) if not np.isnan(port_ci_hi) else None,
        "p_loss": round(port_p_loss, 4) if not np.isnan(port_p_loss) else None,
    }


# ── Section 7: Alternative Portfolios ──────────────────────────────

def alternative_portfolios(df: pd.DataFrame, search_df: pd.DataFrame) -> list[dict]:
    """Try multiple portfolio compositions to find the best."""
    print("\n" + "=" * 60)
    print("SECTION 7: ALTERNATIVE PORTFOLIO COMPOSITIONS")
    print("=" * 60)

    year = df["year"].to_numpy(dtype=np.int16)
    payout = df["payout"].to_numpy(dtype=np.float64)
    gap_ratio = df["gap_ratio"].to_numpy(dtype=np.float64)
    top2_mass = df["top2_mass"].to_numpy(dtype=np.float64)
    fav_multiple = df["fav_multiple"].to_numpy(dtype=np.float64)

    # Define rule variants
    K7 = 7
    cost7 = perm(K7 - 1, 3)
    hit7 = df[f"hit_{K7}"].to_numpy(dtype=bool)
    arrs7 = _extract_arrays(df, K7)

    K8 = 8
    cost8 = perm(K8 - 1, 3)
    hit8 = df[f"hit_{K8}"].to_numpy(dtype=bool)
    arrs8 = _extract_arrays(df, K8)

    # BEL variants
    bel_broad1 = filter_mask(*arrs7, track="BEL", fs_lo=11, fs_hi=13,
                              gap=0.22, fav_min=0.35, cond="fast", card="midlate")
    bel_strict = filter_mask(*arrs7, track="BEL", fs_lo=11, fs_hi=12,
                              gap=0.22, fav_min=0.40, cond="fast", card="midlate")

    # OP variants
    op_base = filter_mask(*arrs7, track="OP", fs_lo=11, fs_hi=12,
                          gap=0.05, fav_min=0.0, cond="all", card="late")
    op_tight = filter_mask(*arrs7, track="OP", fs_lo=11, fs_hi=12,
                           gap=0.10, fav_min=0.0, cond="all", card="late")
    op_fav = filter_mask(*arrs7, track="OP", fs_lo=11, fs_hi=12,
                         gap=0.05, fav_min=0.25, cond="all", card="late")
    # OP with gap_ratio gate
    op_gapratio = op_base & (gap_ratio >= 0.15)

    # CD variants
    cd_base = filter_mask(*arrs8, track="CD", fs_lo=10, fs_hi=11,
                          gap=0.15, fav_min=0.0, cond="all", card="all")
    cd_tight = filter_mask(*arrs8, track="CD", fs_lo=10, fs_hi=11,
                           gap=0.20, fav_min=0.0, cond="all", card="all")
    cd_midlate = filter_mask(*arrs8, track="CD", fs_lo=10, fs_hi=11,
                              gap=0.15, fav_min=0.0, cond="all", card="midlate")
    cd_fast = filter_mask(*arrs8, track="CD", fs_lo=10, fs_hi=11,
                          gap=0.15, fav_min=0.0, cond="fast", card="all")
    cd_fav30 = filter_mask(*arrs8, track="CD", fs_lo=10, fs_hi=11,
                            gap=0.15, fav_min=0.30, cond="all", card="all")
    # CD with gap_ratio gate
    cd_gapratio = cd_base & (gap_ratio >= 0.30)
    cd_gapratio40 = cd_base & (gap_ratio >= 0.40)
    # CD with fav_multiple gate
    cd_favmult = cd_base & (fav_multiple >= 3.5)

    # Define portfolio compositions to test
    portfolios = {
        "P7_baseline": [
            ("BEL_broad1", bel_broad1, hit7, cost7),
            ("OP_base", op_base, hit7, cost7),
            ("CD_base", cd_base, hit8, cost8),
        ],
        "BEL+OP_tight+CD": [
            ("BEL_broad1", bel_broad1, hit7, cost7),
            ("OP_tight", op_tight, hit7, cost7),
            ("CD_base", cd_base, hit8, cost8),
        ],
        "BEL+OP_fav+CD": [
            ("BEL_broad1", bel_broad1, hit7, cost7),
            ("OP_fav", op_fav, hit7, cost7),
            ("CD_base", cd_base, hit8, cost8),
        ],
        "BEL+OP_gapratio+CD": [
            ("BEL_broad1", bel_broad1, hit7, cost7),
            ("OP_gapratio", op_gapratio, hit7, cost7),
            ("CD_base", cd_base, hit8, cost8),
        ],
        "BEL+OP+CD_tight": [
            ("BEL_broad1", bel_broad1, hit7, cost7),
            ("OP_base", op_base, hit7, cost7),
            ("CD_tight", cd_tight, hit8, cost8),
        ],
        "BEL+OP+CD_midlate": [
            ("BEL_broad1", bel_broad1, hit7, cost7),
            ("OP_base", op_base, hit7, cost7),
            ("CD_midlate", cd_midlate, hit8, cost8),
        ],
        "BEL+OP+CD_fast": [
            ("BEL_broad1", bel_broad1, hit7, cost7),
            ("OP_base", op_base, hit7, cost7),
            ("CD_fast", cd_fast, hit8, cost8),
        ],
        "BEL+OP+CD_fav30": [
            ("BEL_broad1", bel_broad1, hit7, cost7),
            ("OP_base", op_base, hit7, cost7),
            ("CD_fav30", cd_fav30, hit8, cost8),
        ],
        "BEL+OP+CD_gapratio30": [
            ("BEL_broad1", bel_broad1, hit7, cost7),
            ("OP_base", op_base, hit7, cost7),
            ("CD_gapratio", cd_gapratio, hit8, cost8),
        ],
        "BEL+OP+CD_gapratio40": [
            ("BEL_broad1", bel_broad1, hit7, cost7),
            ("OP_base", op_base, hit7, cost7),
            ("CD_gapratio40", cd_gapratio40, hit8, cost8),
        ],
        "BEL+OP+CD_favmult": [
            ("BEL_broad1", bel_broad1, hit7, cost7),
            ("OP_base", op_base, hit7, cost7),
            ("CD_favmult", cd_favmult, hit8, cost8),
        ],
        "BEL+OP_tight+CD_tight": [
            ("BEL_broad1", bel_broad1, hit7, cost7),
            ("OP_tight", op_tight, hit7, cost7),
            ("CD_tight", cd_tight, hit8, cost8),
        ],
        "BEL+OP_tight+CD_gapratio40": [
            ("BEL_broad1", bel_broad1, hit7, cost7),
            ("OP_tight", op_tight, hit7, cost7),
            ("CD_gapratio40", cd_gapratio40, hit8, cost8),
        ],
        "BEL_strict+OP+CD": [
            ("BEL_strict", bel_strict, hit7, cost7),
            ("OP_base", op_base, hit7, cost7),
            ("CD_base", cd_base, hit8, cost8),
        ],
        "BEL_only": [
            ("BEL_broad1", bel_broad1, hit7, cost7),
        ],
        "BEL+OP_only": [
            ("BEL_broad1", bel_broad1, hit7, cost7),
            ("OP_base", op_base, hit7, cost7),
        ],
    }

    years = sorted(df["year"].unique())
    results = []

    print(f"\n  {'Portfolio':<35} {'Races':>6} {'ROI%':>7} {'PosYrs':>8} {'CI_lo':>7} {'P(loss)':>8}")
    for port_name, rules in portfolios.items():
        year_data = []
        for y in years:
            y_w = 0
            y_p = 0.0
            for _, mask, hit_arr, cost_val in rules:
                ym = mask & (year == y)
                s = compute_roi(ym, hit_arr, payout, cost_val)
                y_w += s["wagered"]
                y_p += s["profit"]
            if y_w > 0:
                year_data.append({"year": y, "wagered": y_w, "profit": y_p,
                                  "roi": y_p / y_w * 100})

        if not year_data:
            continue

        total_w = sum(yd["wagered"] for yd in year_data)
        total_p = sum(yd["profit"] for yd in year_data)
        total_roi = total_p / total_w * 100 if total_w > 0 else -100
        total_races = sum(int(r[1].sum()) for r in rules)
        pos_yrs = sum(1 for yd in year_data if yd["roi"] > 0)

        # Quick bootstrap
        rng = np.random.default_rng(RNG_SEED)
        yr_profits = np.array([yd["profit"] for yd in year_data])
        yr_wagered_a = np.array([yd["wagered"] for yd in year_data])
        n_y = len(year_data)
        if n_y >= 3:
            boot = np.empty(2000)
            for b in range(2000):
                idx = rng.choice(n_y, size=n_y, replace=True)
                tp = yr_profits[idx].sum()
                tw = yr_wagered_a[idx].sum()
                boot[b] = tp / tw * 100 if tw > 0 else -100
            ci_lo = float(np.percentile(boot, 2.5))
            ci_hi = float(np.percentile(boot, 97.5))
            p_loss = float(np.mean(boot < 0))
        else:
            ci_lo, ci_hi, p_loss = np.nan, np.nan, np.nan

        print(f"  {port_name:<35} {total_races:>6} {total_roi:>+7.1f} "
              f"{pos_yrs:>2}/{len(year_data):<2}   {ci_lo:>+7.1f} {p_loss:>8.1%}")

        results.append({
            "name": port_name,
            "races": total_races,
            "roi": round(total_roi, 2),
            "pos_years": pos_yrs,
            "n_years": len(year_data),
            "ci_lo": round(ci_lo, 2) if not np.isnan(ci_lo) else None,
            "ci_hi": round(ci_hi, 2) if not np.isnan(ci_hi) else None,
            "p_loss": round(p_loss, 4) if not np.isnan(p_loss) else None,
            "year_data": year_data,
            "rules": [(name, int(m.sum())) for name, m, _, _ in rules],
        })

    results.sort(key=lambda x: -(x["roi"] if x["ci_lo"] and x["ci_lo"] > 0 else x["roi"] * 0.5))
    return results


# ── Section 8: Final Validation ────────────────────────────────────

def final_validation(df: pd.DataFrame, best_portfolio: dict,
                     p7_baseline: dict) -> dict:
    """Rigorous validation of the best Phase 8 portfolio."""
    print("\n" + "=" * 60)
    print("SECTION 8: FINAL VALIDATION")
    print("=" * 60)

    year = df["year"].to_numpy(dtype=np.int16)
    payout = df["payout"].to_numpy(dtype=np.float64)

    if not best_portfolio.get("portfolio_rules"):
        print("  No portfolio to validate.")
        return {}

    rules = best_portfolio["portfolio_rules"]
    years = sorted(df["year"].unique())

    # Expanding walk-forward on portfolio
    print("\n  Expanding walk-forward (portfolio level):")
    min_train = 3
    wf_results = []
    for i in range(min_train, len(years)):
        test_y = years[i]
        train_ys = years[:i]

        # Train-period portfolio ROI
        train_w = 0
        train_p = 0.0
        test_w = 0
        test_p = 0.0
        for rule in rules:
            train_m = rule["mask"] & np.isin(year, train_ys)
            test_m = rule["mask"] & (year == test_y)
            ts = compute_roi(train_m, rule["hit"], payout, rule["cost"])
            os_ = compute_roi(test_m, rule["hit"], payout, rule["cost"])
            train_w += ts["wagered"]
            train_p += ts["profit"]
            test_w += os_["wagered"]
            test_p += os_["profit"]

        train_roi = train_p / train_w * 100 if train_w > 0 else 0
        test_roi = test_p / test_w * 100 if test_w > 0 else 0
        test_n = sum(int((rule["mask"] & (year == test_y)).sum()) for rule in rules)

        wf_results.append({
            "train": f"{years[0]}-{train_ys[-1]}", "test": test_y,
            "train_roi": round(train_roi, 1),
            "test_n": test_n, "test_roi": round(test_roi, 1),
        })
        status = "+" if test_roi > 0 else "-"
        print(f"    {years[0]}-{train_ys[-1]} -> {test_y}: "
              f"train {train_roi:+.1f}%, test ({test_n} races) {test_roi:+.1f}% {status}")

    wf_pos = sum(1 for r in wf_results if r["test_n"] > 0 and r["test_roi"] > 0)
    wf_tot = sum(1 for r in wf_results if r["test_n"] > 0)
    print(f"\n  Walk-forward OOS positive: {wf_pos}/{wf_tot}")

    # Payoff concentration
    print("\n  Payoff concentration analysis:")
    all_profits = []
    for rule in rules:
        m = rule["mask"]
        h = m & rule["hit"]
        payouts = payout[h] - rule["cost"]
        all_profits.extend(payouts.tolist())
        # Also add misses
        n_miss = int(m.sum()) - int(h.sum())
        all_profits.extend([-rule["cost"]] * n_miss)

    all_profits.sort(reverse=True)
    total_profit = sum(all_profits)
    if total_profit > 0 and len(all_profits) > 0:
        top1_share = all_profits[0] / total_profit * 100
        top3_share = sum(all_profits[:3]) / total_profit * 100
        top5_share = sum(all_profits[:5]) / total_profit * 100
        print(f"    Top-1 hit share: {top1_share:.1f}% of total profit")
        print(f"    Top-3 hit share: {top3_share:.1f}% of total profit")
        print(f"    Top-5 hit share: {top5_share:.1f}% of total profit")

        # ROI without top hits
        for remove_n in [1, 3, 5]:
            reduced = sum(all_profits[remove_n:])
            total_w = best_portfolio["total_wagered"]
            reduced_roi = reduced / total_w * 100
            print(f"    ROI without top-{remove_n}: {reduced_roi:+.1f}%")

    # Direct comparison
    print("\n" + "=" * 60)
    print("PHASE 7 vs PHASE 8 COMPARISON")
    print("=" * 60)

    p8_roi = best_portfolio["total_roi"]
    p7_roi = p7_baseline["total_roi"]
    p8_races = best_portfolio["total_races"]
    p7_races = p7_baseline["total_races"]
    p8_pos = best_portfolio["pos_years"]
    p7_pos = p7_baseline["pos_years"]
    p8_n_yrs = best_portfolio["n_years"]
    p7_n_yrs = p7_baseline["n_years"]

    print(f"  {'Metric':<25} {'Phase 7':>12} {'Phase 8':>12} {'Delta':>10}")
    print(f"  {'-'*25} {'-'*12} {'-'*12} {'-'*10}")
    print(f"  {'Races':<25} {p7_races:>12,} {p8_races:>12,} {p8_races-p7_races:>+10,}")
    print(f"  {'ROI%':<25} {p7_roi:>+12.1f} {p8_roi:>+12.1f} {p8_roi-p7_roi:>+10.1f}")
    print(f"  {'Positive years':<25} {p7_pos:>2}/{p7_n_yrs:<2}{'':<7} "
          f"{p8_pos:>2}/{p8_n_yrs:<2}{'':<7} ")
    print(f"  {'Wagered':<25} ${p7_baseline['total_wagered']:>10,} "
          f"${best_portfolio['total_wagered']:>10,}")
    print(f"  {'Profit':<25} ${p7_baseline['total_profit']:>10,.0f} "
          f"${best_portfolio['total_profit']:>10,.0f}")

    if best_portfolio.get("ci_lo") is not None:
        print(f"  {'Bootstrap CI lower':<25} {'':>12} "
              f"{best_portfolio['ci_lo']:>+12.1f}")
    if best_portfolio.get("p_loss") is not None:
        print(f"  {'P(loss)':<25} {'':>12} "
              f"{best_portfolio['p_loss']:>12.1%}")

    improvement = p8_roi - p7_roi
    if improvement > 5:
        verdict = "MATERIAL IMPROVEMENT"
    elif improvement > 2:
        verdict = "MARGINAL IMPROVEMENT"
    elif improvement > -2:
        verdict = "EFFECTIVELY EQUAL"
    else:
        verdict = "REGRESSION"

    print(f"\n  Verdict: {verdict} ({improvement:+.1f} ROI points)")

    return {
        "wf_results": wf_results,
        "wf_pos": wf_pos, "wf_tot": wf_tot,
        "improvement": round(improvement, 2),
        "verdict": verdict,
    }


# ── Report Generation ──────────────────────────────────────────────

def build_report(p7: dict, search_df: pd.DataFrame,
                 op_results: dict, cd_results: dict,
                 discoveries: dict, best_portfolio: dict,
                 alt_portfolios: list, validation: dict) -> str:
    lines = []
    lines.append("# Phase 8 Report — Advanced Superfecta Portfolio Optimization")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")

    p8_roi = best_portfolio.get("total_roi", -100)
    p7_roi = p7.get("total_roi", 28.0)
    delta = p8_roi - p7_roi
    verdict = validation.get("verdict", "UNKNOWN")

    lines.append(f"Phase 8 portfolio: **{best_portfolio.get('total_races', 0):,} races**, "
                 f"**{p8_roi:+.1f}% ROI**, "
                 f"**{best_portfolio.get('pos_years', 0)}/{best_portfolio.get('n_years', 0)} "
                 f"positive years**")
    lines.append(f"")
    lines.append(f"Phase 7 baseline: {p7.get('total_races', 1075):,} races, "
                 f"{p7_roi:+.1f}% ROI, "
                 f"{p7.get('pos_years', 12)}/{p7.get('n_years', 15)} positive years")
    lines.append(f"")
    lines.append(f"**Delta: {delta:+.1f} ROI points — {verdict}**")
    lines.append("")

    ci_lo = best_portfolio.get("ci_lo")
    ci_hi = best_portfolio.get("ci_hi")
    p_loss_val = best_portfolio.get("p_loss")
    if ci_lo is not None and ci_hi is not None:
        lines.append(f"Block bootstrap 95% CI: [{ci_lo:+.1f}%, {ci_hi:+.1f}%]")
    if p_loss_val is not None:
        lines.append(f"P(loss) = {p_loss_val:.1%}")
    lines.append("")

    # Portfolio composition
    lines.append("---")
    lines.append("")
    lines.append("## Phase 8 Portfolio Composition")
    lines.append("")

    for rule in best_portfolio.get("portfolio_rules", []):
        s = rule["stats"]
        loocv = rule["loocv"]
        bb = rule["bootstrap"]
        lines.append(f"### {rule['name']}")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Track | {rule['track']} |")
        lines.append(f"| Races | {s['races']} |")
        lines.append(f"| ROI | {s['roi']:+.1f}% |")
        lines.append(f"| Hit rate | {s['hit_rate']:.1f}% |")
        lines.append(f"| LOOCV positive years | {loocv['pos_years']}/{loocv['total_years']} |")
        ci_lo_val = bb.get('ci_lo', 'N/A')
        ci_hi_val = bb.get('ci_hi', 'N/A')
        if isinstance(ci_lo_val, (int, float)) and not np.isnan(ci_lo_val):
            lines.append(f"| Block bootstrap 95% CI | [{ci_lo_val:+.1f}%, {ci_hi_val:+.1f}%] |")
        p_loss_val = bb.get('p_loss', 'N/A')
        if isinstance(p_loss_val, (int, float)) and not np.isnan(p_loss_val):
            lines.append(f"| P(loss) | {p_loss_val:.1%} |")
        lines.append(f"| Walk-forward OOS | {rule.get('wf_pos', '?')}/{rule.get('wf_tot', '?')} |")
        lines.append(f"| Quality score | {rule['quality_score']:.1f} |")
        lines.append(f"")

    # Year-by-year portfolio
    lines.append("## Year-by-Year Portfolio Performance")
    lines.append("")
    lines.append("| Year | Wagered | Profit | ROI |")
    lines.append("|------|---------|--------|-----|")
    for yr in best_portfolio.get("year_results", []):
        lines.append(f"| {yr['year']} | ${yr['wagered']:,} | ${yr['profit']:+,.0f} | "
                     f"{yr['roi']:+.1f}% |")
    lines.append(f"| **TOTAL** | **${best_portfolio.get('total_wagered', 0):,}** | "
                 f"**${best_portfolio.get('total_profit', 0):+,.0f}** | "
                 f"**{p8_roi:+.1f}%** |")
    lines.append("")

    # Alternative portfolios
    lines.append("---")
    lines.append("")
    lines.append("## Alternative Portfolio Comparison")
    lines.append("")
    lines.append("| Portfolio | Races | ROI% | Pos Years | CI Lower | P(loss) |")
    lines.append("|-----------|-------|------|-----------|----------|---------|")
    for ap in alt_portfolios[:15]:
        ci_str = f"{ap['ci_lo']:+.1f}%" if ap.get('ci_lo') is not None else "N/A"
        pl_str = f"{ap['p_loss']:.1%}" if ap.get('p_loss') is not None else "N/A"
        lines.append(f"| {ap['name']} | {ap['races']:,} | {ap['roi']:+.1f} | "
                     f"{ap['pos_years']}/{ap['n_years']} | {ci_str} | {pl_str} |")
    lines.append("")

    # Validation
    lines.append("---")
    lines.append("")
    lines.append("## Validation")
    lines.append("")
    wf = validation.get("wf_results", [])
    if wf:
        lines.append("### Expanding Walk-Forward (Portfolio)")
        lines.append("")
        lines.append("| Train | Test Year | Test Races | Test ROI |")
        lines.append("|-------|-----------|------------|----------|")
        for r in wf:
            lines.append(f"| {r['train']} | {r['test']} | {r['test_n']} | "
                         f"{r['test_roi']:+.1f}% |")
        lines.append(f"")
        lines.append(f"OOS positive: **{validation.get('wf_pos', 0)}/"
                     f"{validation.get('wf_tot', 0)}**")
        lines.append("")

    # Phase 7 vs 8 comparison
    lines.append("---")
    lines.append("")
    lines.append("## Phase 7 vs Phase 8")
    lines.append("")
    lines.append("| Metric | Phase 7 | Phase 8 | Delta |")
    lines.append("|--------|---------|---------|-------|")
    lines.append(f"| Races | {p7.get('total_races', 1075):,} | "
                 f"{best_portfolio.get('total_races', 0):,} | "
                 f"{best_portfolio.get('total_races', 0) - p7.get('total_races', 1075):+,} |")
    lines.append(f"| ROI% | {p7_roi:+.1f} | {p8_roi:+.1f} | {delta:+.1f} |")
    lines.append(f"| Positive years | {p7.get('pos_years', 12)}/{p7.get('n_years', 15)} | "
                 f"{best_portfolio.get('pos_years', 0)}/{best_portfolio.get('n_years', 0)} | |")
    lines.append(f"| Wagered | ${p7.get('total_wagered', 0):,} | "
                 f"${best_portfolio.get('total_wagered', 0):,} | |")
    lines.append(f"| Profit | ${p7.get('total_profit', 0):+,.0f} | "
                 f"${best_portfolio.get('total_profit', 0):+,.0f} | |")
    lines.append("")

    # Data ceiling analysis
    lines.append("---")
    lines.append("")
    lines.append("## Data Ceiling Analysis")
    lines.append("")
    if delta > 5:
        lines.append("Phase 8 achieved a material improvement over Phase 7, "
                     "suggesting the data had not yet been fully exploited.")
    elif delta > 0:
        lines.append("Phase 8 achieved a marginal improvement. The odds-derived feature "
                     "space is approaching its ceiling for this dataset.")
    else:
        lines.append("Phase 8 could not meaningfully beat Phase 7. "
                     "The current dataset is effectively **plateaued** for odds-based strategies.")
    lines.append("")
    lines.append("### What could move the needle:")
    lines.append("1. **Horse-specific features** (speed figures, form cycle, class)")
    lines.append("2. **Forward data** from reopened Belmont Park")
    lines.append("3. **Real-time pool analysis** for overlay detection")
    lines.append("4. **Jockey/trainer statistics**")
    lines.append("5. **Weather and track variant data** (beyond fast/wet binary)")
    lines.append("6. **Pool size / liquidity features** — bet into deep pools only")
    lines.append("")

    # New discoveries
    if discoveries:
        lines.append("---")
        lines.append("")
        lines.append("## New Track Discoveries")
        lines.append("")
        for track, disc in discoveries.items():
            s = disc["stats"]
            loocv = disc["loocv"]
            bb = disc["bootstrap"]
            lines.append(f"### {track}")
            lines.append(f"- Strategy: {disc['strategy']}")
            lines.append(f"- Races: {s['races']}, ROI: {s['roi']:+.1f}%")
            lines.append(f"- LOOCV: {loocv['pos_years']}/{loocv['total_years']}")
            ci_lo_val = bb.get('ci_lo', 'N/A')
            if isinstance(ci_lo_val, (int, float)) and not np.isnan(ci_lo_val):
                lines.append(f"- Bootstrap CI: [{ci_lo_val:+.1f}%, {bb['ci_hi']:+.1f}%]")
            lines.append("")

    # File paths
    lines.append("---")
    lines.append("")
    lines.append("## File Paths")
    lines.append(f"- Script: `{BASE / 'backtest_phase8.py'}`")
    lines.append(f"- Summary CSV: `{OUT_CSV}`")
    lines.append(f"- Report: `{OUT_REPORT}`")

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("PHASE 8: ADVANCED SUPERFECTA PORTFOLIO OPTIMIZATION")
    print("=" * 60)

    df = load_data()

    # Phase 7 baseline
    p7 = phase7_baseline(df)

    # Section 1: Enhanced search
    search_df = enhanced_feature_search(df)

    # Print top search results
    if not search_df.empty:
        top = search_df[
            (search_df["ROI%"] > 0) & (search_df["LOOCV_PosRatio"] >= 0.5)
        ]
        print(f"\n  Top profitable rules (LOOCV >= 50%): {len(top)}")
        if len(top) > 0:
            print(f"\n  {'Strategy':<55} {'R':>5} {'ROI%':>7} {'LOOCV':>8} "
                  f"{'MedROI':>7} {'Test':>6}")
            for _, r in top.head(25).iterrows():
                print(f"  {r['Strategy']:<55} {r['Races']:>5} {r['ROI%']:>+7.1f} "
                      f"{r['LOOCV_PosYrs']:>8} {r['LOOCV_MedianROI']:>+7.1f} "
                      f"{r['TestROI%']:>+6.1f}")

    # Section 2: Feature-gated refinement
    refined = feature_gated_refinement(df, search_df)

    # Section 3: OP refinement
    op_results = refine_op(df)

    # Section 4: CD refinement
    cd_results = refine_cd(df)

    # Section 5: New track discovery
    discoveries = new_track_discovery(df, search_df)

    # Section 6: Optimized portfolio
    best_portfolio = build_optimized_portfolio(df, search_df, op_results,
                                               cd_results, discoveries)

    # Section 7: Alternative portfolios
    alt_portfolios = alternative_portfolios(df, search_df)

    # Compare Section 6 optimized portfolio vs alternatives using composite score
    # Score = ROI * 0.30 + CI_lower * 0.25 + pos_year_ratio * 100 * 0.25
    #         + (1 - p_loss) * 100 * 0.20
    # Must have >= 200 races
    def _portfolio_score(roi, ci_lo, pos_yrs, n_yrs, p_loss, n_races):
        if n_races < 200:
            return -999
        ci = ci_lo if ci_lo is not None else -50
        pl = p_loss if p_loss is not None else 1.0
        pr = pos_yrs / n_yrs if n_yrs > 0 else 0
        return roi * 0.30 + max(ci, -50) * 0.25 + pr * 100 * 0.25 + (1 - pl) * 100 * 0.20

    opt_score = _portfolio_score(
        best_portfolio["total_roi"],
        best_portfolio.get("ci_lo"),
        best_portfolio["pos_years"],
        best_portfolio["n_years"],
        best_portfolio.get("p_loss"),
        best_portfolio["total_races"],
    )
    print(f"\n  Section 6 optimized portfolio score: {opt_score:.1f}")

    for ap in alt_portfolios:
        ap["score"] = _portfolio_score(
            ap["roi"], ap.get("ci_lo"), ap["pos_years"],
            ap["n_years"], ap.get("p_loss"), ap["races"])
        if ap["score"] > opt_score and ap["races"] >= 200:
            print(f"  Alternative '{ap['name']}' has higher composite score "
                  f"({ap['score']:.1f} vs {opt_score:.1f})")

    best_alt = max(
        [ap for ap in alt_portfolios if ap["races"] >= 200],
        key=lambda x: x["score"], default=None
    )

    # Only adopt alternative if it genuinely beats optimized portfolio
    if best_alt and best_alt["score"] > opt_score:
        print(f"\n  *** Adopting '{best_alt['name']}' (score {best_alt['score']:.1f} "
              f"vs optimized {opt_score:.1f}) ***")
        best_portfolio["total_roi"] = best_alt["roi"]
        best_portfolio["total_races"] = best_alt["races"]
        best_portfolio["pos_years"] = best_alt["pos_years"]
        best_portfolio["n_years"] = best_alt["n_years"]
        best_portfolio["ci_lo"] = best_alt.get("ci_lo")
        best_portfolio["ci_hi"] = best_alt.get("ci_hi")
        best_portfolio["p_loss"] = best_alt.get("p_loss")
        best_portfolio["year_results"] = [
            {"year": yd["year"], "wagered": yd["wagered"],
             "profit": round(yd["profit"], 2),
             "roi": round(yd["roi"], 2)}
            for yd in best_alt["year_data"]
        ]
        best_portfolio["total_wagered"] = sum(yd["wagered"] for yd in best_alt["year_data"])
        best_portfolio["total_profit"] = round(sum(yd["profit"] for yd in best_alt["year_data"]), 2)
        best_portfolio["adopted_alt"] = best_alt["name"]
    else:
        print(f"\n  Section 6 optimized portfolio is the best (score {opt_score:.1f}).")

    # Section 8: Final validation
    validation = final_validation(df, best_portfolio, p7)

    # Save CSV
    if not search_df.empty:
        search_df.to_csv(OUT_CSV, index=False)
        print(f"\n  Summary CSV saved: {OUT_CSV}")

    # Build and save report
    report = build_report(p7, search_df, op_results, cd_results,
                          discoveries, best_portfolio, alt_portfolios,
                          validation)
    OUT_REPORT.write_text(report)
    print(f"  Report saved: {OUT_REPORT}")

    # Final stdout summary
    print("\n" + "=" * 60)
    print("PHASE 8 FINAL SUMMARY")
    print("=" * 60)
    p8_roi = best_portfolio["total_roi"]
    p7_roi = p7["total_roi"]
    print(f"  Phase 7: {p7['total_races']:,} races, {p7_roi:+.1f}% ROI, "
          f"{p7['pos_years']}/{p7['n_years']} positive years")
    print(f"  Phase 8: {best_portfolio['total_races']:,} races, {p8_roi:+.1f}% ROI, "
          f"{best_portfolio['pos_years']}/{best_portfolio['n_years']} positive years")
    print(f"  Delta: {p8_roi - p7_roi:+.1f} ROI points")
    print(f"  Verdict: {validation.get('verdict', 'UNKNOWN')}")
    ci_lo = best_portfolio.get("ci_lo")
    ci_hi = best_portfolio.get("ci_hi")
    if ci_lo is not None and ci_hi is not None:
        print(f"  Bootstrap CI: [{ci_lo:+.1f}%, {ci_hi:+.1f}%]")
    if best_portfolio.get("p_loss") is not None:
        print(f"  P(loss): {best_portfolio['p_loss']:.1%}")

    adopted = best_portfolio.get("adopted_alt")
    if adopted:
        print(f"  Best portfolio composition: {adopted}")

    if validation.get("verdict") in ("EFFECTIVELY EQUAL", "REGRESSION"):
        print(f"\n  CONCLUSION: Dataset is plateaued for odds-only features.")
        print(f"  Next data needed: speed figures, jockey/trainer stats, "
              f"pool liquidity, weather details.")
    elif validation.get("verdict") == "MARGINAL IMPROVEMENT":
        print(f"\n  CONCLUSION: Small gains found, but approaching ceiling.")
    else:
        print(f"\n  CONCLUSION: Material improvement achieved through "
              f"better portfolio construction.")


if __name__ == "__main__":
    main()
