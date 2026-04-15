#!/usr/bin/env python3
"""
Phase 6: BEL robustness pass.

Stress-tests the BEL Key1Win pocket found in Phase 5:
  - K=7, field 10-13, gap 0.10-0.25, fav 0.35-0.45, late/midlate, fast/all

Robustness checks:
  1. Fine-grained parameter sweep (finer grid than Phase 5)
  2. Per-year stability tables
  3. Rolling out-of-sample windows (walk-forward)
  4. Bootstrap confidence intervals on ROI
  5. Permutation test (label shuffle)
  6. Multiple-testing correction (Bonferroni on tested variants)
  7. Broadening attempts: relax one parameter at a time
"""

import os
for _k in [
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS", "NUMEXPR_MAX_THREADS", "MKL_NUM_THREADS",
]:
    os.environ[_k] = "1"

from math import perm
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

BASE = Path("/Users/maximusregent_ai/Shared/Superfecta Help")
CACHE_PATH = BASE / "phase5_race_cache.pkl"
OUT_CSV = BASE / "backtest_phase6_summary.csv"
OUT_REPORT = BASE / "PHASE6_REPORT.md"

K = 7
COST = perm(K - 1, 3)  # 120

# Fine-grained sweeps for BEL
FS_BINS = [
    (10, 11), (10, 12), (10, 13), (10, 14),
    (11, 12), (11, 13), (11, 14),
    (9, 12), (9, 13),
]
GAPS = [0.05, 0.08, 0.10, 0.12, 0.14, 0.15, 0.18, 0.20, 0.22, 0.25, 0.30]
FAV_MINS = [0.00, 0.30, 0.33, 0.35, 0.37, 0.40, 0.42, 0.45, 0.50]
CONDS = ["all", "fast"]
CARDS = ["all", "midlate", "late"]
MIN_RACES = 50  # Lower threshold for exploration

N_BOOTSTRAP = 2000
N_PERMUTATIONS = 2000
RNG_SEED = 42


def load_cache() -> pd.DataFrame:
    print(f"Loading cached race table from {CACHE_PATH.name}...")
    df = pd.read_pickle(CACHE_PATH)
    print(f"  {len(df):,} race rows loaded")
    return df


def filter_races(
    track: np.ndarray, year: np.ndarray, rnum: np.ndarray,
    fs: np.ndarray, fav_prob: np.ndarray, prob_gap: np.ndarray,
    is_fast: np.ndarray, eligible: np.ndarray,
    fs_lo: int, fs_hi: int, gap: float, fav_min: float,
    cond: str, card: str,
) -> np.ndarray:
    """Return boolean mask for qualifying races."""
    m = (
        (track == "BEL")
        & eligible
        & (fs >= fs_lo) & (fs <= fs_hi)
        & (prob_gap >= gap)
        & (fav_prob >= fav_min)
    )
    if cond == "fast":
        m &= is_fast
    if card == "midlate":
        m &= (rnum >= 5)
    elif card == "late":
        m &= (rnum >= 7)
    return m


def compute_roi(mask: np.ndarray, hit: np.ndarray, payout: np.ndarray) -> dict:
    """Compute ROI stats for a boolean mask."""
    n = int(mask.sum())
    if n == 0:
        return {"races": 0, "wagered": 0, "returned": 0.0, "profit": 0.0,
                "roi": -100.0, "hits": 0, "hit_rate": 0.0, "avg_pay": 0.0}
    h = mask & hit
    hits = int(h.sum())
    wagered = n * COST
    returned = float(payout[h].sum())
    profit = returned - wagered
    roi = profit / wagered * 100.0
    return {
        "races": n, "wagered": wagered, "returned": round(returned, 2),
        "profit": round(profit, 2), "roi": round(roi, 2),
        "hits": hits, "hit_rate": round(hits / n * 100.0, 2),
        "avg_pay": round(returned / hits, 2) if hits else 0.0,
    }


def per_year_table(
    mask: np.ndarray, hit: np.ndarray, payout: np.ndarray, year: np.ndarray
) -> list[dict]:
    """Per-year breakdown."""
    years_present = sorted(set(year[mask]))
    rows = []
    for y in years_present:
        ym = mask & (year == y)
        s = compute_roi(ym, hit, payout)
        s["year"] = y
        rows.append(s)
    return rows


def bootstrap_roi(
    mask: np.ndarray, hit: np.ndarray, payout: np.ndarray,
    n_boot: int = N_BOOTSTRAP, seed: int = RNG_SEED
) -> dict:
    """Bootstrap CI for ROI. Resamples race-level outcomes."""
    rng = np.random.default_rng(seed)
    idxs = np.where(mask)[0]
    n = len(idxs)
    if n < 5:
        return {"ci_lo": np.nan, "ci_hi": np.nan, "mean": np.nan, "median": np.nan}

    hit_vals = hit[idxs]
    pay_vals = payout[idxs]
    # Each race: profit = (payout if hit else 0) - COST
    race_profits = np.where(hit_vals, pay_vals - COST, -COST).astype(np.float64)

    boot_rois = np.empty(n_boot)
    for b in range(n_boot):
        sample = rng.choice(race_profits, size=n, replace=True)
        boot_rois[b] = sample.sum() / (n * COST) * 100.0

    return {
        "ci_lo": round(float(np.percentile(boot_rois, 2.5)), 2),
        "ci_hi": round(float(np.percentile(boot_rois, 97.5)), 2),
        "mean": round(float(boot_rois.mean()), 2),
        "median": round(float(np.median(boot_rois)), 2),
    }


def permutation_test(
    mask: np.ndarray, hit: np.ndarray, payout: np.ndarray,
    all_eligible_mask: np.ndarray,
    n_perms: int = N_PERMUTATIONS, seed: int = RNG_SEED
) -> dict:
    """Permutation test: randomly sample N races from ALL eligible BEL races.

    Null hypothesis: the filter doesn't improve ROI — the observed result
    could arise from randomly selecting the same number of races from the
    full eligible pool.
    """
    rng = np.random.default_rng(seed)
    idxs = np.where(mask)[0]
    n = len(idxs)
    if n < 5:
        return {"p_value": np.nan, "observed_roi": np.nan, "observed_hr": np.nan,
                "base_hr": np.nan, "null_mean": np.nan, "null_std": np.nan}

    hit_sub = hit[idxs]
    pay_sub = payout[idxs]
    wagered = n * COST

    # Observed
    obs_returned = float(pay_sub[hit_sub].sum())
    obs_roi = (obs_returned - wagered) / wagered * 100.0
    obs_hr = float(hit_sub.mean())

    # Pool: all BEL K1W7-eligible races
    pool_idxs = np.where(all_eligible_mask)[0]
    pool_hit = hit[pool_idxs]
    pool_pay = payout[pool_idxs]
    base_hr = float(pool_hit.mean())

    # Permutation: draw n races from pool, compute ROI
    pool_n = len(pool_idxs)
    perm_rois = np.empty(n_perms)
    perm_hrs = np.empty(n_perms)
    for p in range(n_perms):
        sample = rng.choice(pool_n, size=n, replace=False)
        s_hit = pool_hit[sample]
        s_pay = pool_pay[sample]
        returned = float(s_pay[s_hit].sum())
        perm_rois[p] = (returned - wagered) / wagered * 100.0
        perm_hrs[p] = float(s_hit.mean())

    p_value_roi = float(np.mean(perm_rois >= obs_roi))
    p_value_hr = float(np.mean(perm_hrs >= obs_hr))

    return {
        "p_value_roi": round(p_value_roi, 4),
        "p_value_hr": round(p_value_hr, 4),
        "observed_roi": round(obs_roi, 2),
        "observed_hr": round(obs_hr * 100, 2),
        "base_hr": round(base_hr * 100, 2),
        "null_mean_roi": round(float(perm_rois.mean()), 2),
        "null_std_roi": round(float(perm_rois.std()), 2),
        "null_mean_hr": round(float(perm_hrs.mean()) * 100, 2),
    }


def walk_forward_oos(
    mask: np.ndarray, hit: np.ndarray, payout: np.ndarray, year: np.ndarray,
    train_years: int = 5
) -> list[dict]:
    """Walk-forward: train on N years, test on the next year, roll forward."""
    years_sorted = sorted(set(year[mask]))
    results = []
    for i in range(train_years, len(years_sorted)):
        test_y = years_sorted[i]
        train_ys = years_sorted[max(0, i - train_years):i]
        train_m = mask & np.isin(year, train_ys)
        test_m = mask & (year == test_y)
        train_s = compute_roi(train_m, hit, payout)
        test_s = compute_roi(test_m, hit, payout)
        results.append({
            "train_years": f"{train_ys[0]}-{train_ys[-1]}",
            "test_year": test_y,
            "train_races": train_s["races"],
            "train_roi": train_s["roi"],
            "test_races": test_s["races"],
            "test_roi": test_s["roi"],
            "test_hits": test_s["hits"],
        })
    return results


def half_split_oos(
    mask: np.ndarray, hit: np.ndarray, payout: np.ndarray, year: np.ndarray,
) -> dict:
    """Simple first-half / second-half split."""
    years_sorted = sorted(set(year[mask]))
    mid = len(years_sorted) // 2
    first_ys = years_sorted[:mid]
    second_ys = years_sorted[mid:]
    first_m = mask & np.isin(year, first_ys)
    second_m = mask & np.isin(year, second_ys)
    first_s = compute_roi(first_m, hit, payout)
    second_s = compute_roi(second_m, hit, payout)
    return {
        "first_half_years": f"{first_ys[0]}-{first_ys[-1]}",
        "second_half_years": f"{second_ys[0]}-{second_ys[-1]}",
        "first_half_roi": first_s["roi"],
        "first_half_races": first_s["races"],
        "second_half_roi": second_s["roi"],
        "second_half_races": second_s["races"],
    }


def even_odd_year_split(
    mask: np.ndarray, hit: np.ndarray, payout: np.ndarray, year: np.ndarray,
) -> dict:
    """Even vs odd year split for additional robustness."""
    even_m = mask & (year % 2 == 0)
    odd_m = mask & (year % 2 == 1)
    even_s = compute_roi(even_m, hit, payout)
    odd_s = compute_roi(odd_m, hit, payout)
    return {
        "even_year_roi": even_s["roi"],
        "even_year_races": even_s["races"],
        "odd_year_roi": odd_s["roi"],
        "odd_year_races": odd_s["races"],
    }


def main():
    df = load_cache()

    # Extract arrays
    track = df["track"].to_numpy()
    year = df["year"].to_numpy(dtype=np.int16)
    rnum = df["rnum"].to_numpy(dtype=np.int16)
    fs = df["fs"].to_numpy(dtype=np.int16)
    payout = df["payout"].to_numpy(dtype=np.float64)
    fav_prob = df["fav_prob"].to_numpy(dtype=np.float64)
    prob_gap = df["prob_gap"].to_numpy(dtype=np.float64)
    is_fast = df["is_fast"].to_numpy(dtype=bool)
    eligible = df[f"eligible_{K}"].to_numpy(dtype=bool)
    hit = df[f"hit_{K}"].to_numpy(dtype=bool)

    # ── 1. Fine-grained parameter sweep ──
    print("\n=== Phase 6 Fine-Grained Sweep ===")
    sweep_rows = []
    n_tested = 0
    for fs_lo, fs_hi in FS_BINS:
        for gap in GAPS:
            for fav_min in FAV_MINS:
                for cond in CONDS:
                    for card in CARDS:
                        n_tested += 1
                        m = filter_races(
                            track, year, rnum, fs, fav_prob, prob_gap,
                            is_fast, eligible,
                            fs_lo, fs_hi, gap, fav_min, cond, card,
                        )
                        s = compute_roi(m, hit, payout)
                        if s["races"] < MIN_RACES:
                            continue

                        # Phase 5-compatible train/test
                        train_m = m & (year <= 2018)
                        test_m = m & (year >= 2019) & (year != 2021)
                        train_s = compute_roi(train_m, hit, payout)
                        test_s = compute_roi(test_m, hit, payout)

                        # Per-year positive count
                        yt = per_year_table(m, hit, payout, year)
                        pos_y = sum(1 for r in yt if r["roi"] > 0)
                        total_y = len(yt)

                        label = (
                            f"K1W{K}_BEL_FS{fs_lo}-{fs_hi}_Gap{gap:.2f}"
                            f"_Fav{fav_min:.2f}_{cond}_{card}"
                        )
                        sweep_rows.append({
                            "Strategy": label,
                            "FS": f"{fs_lo}-{fs_hi}",
                            "Gap": gap,
                            "FavMin": fav_min,
                            "Cond": cond,
                            "Card": card,
                            "Races": s["races"],
                            "Hits": s["hits"],
                            "ROI%": s["roi"],
                            "HitRate%": s["hit_rate"],
                            "AvgPay": s["avg_pay"],
                            "TrainROI%": train_s["roi"],
                            "TestROI%": test_s["roi"],
                            "TrainRaces": train_s["races"],
                            "TestRaces": test_s["races"],
                            "PosYears": f"{pos_y}/{total_y}",
                        })

    sweep_df = pd.DataFrame(sweep_rows)
    sweep_df = sweep_df.sort_values(
        ["ROI%", "Races"], ascending=[False, False]
    )
    sweep_df.to_csv(OUT_CSV, index=False)
    print(f"  Tested {n_tested} variants, {len(sweep_df)} met min-race threshold")

    # Find strategies with full ROI > 0
    profitable = sweep_df[sweep_df["ROI%"] > 0].copy()
    both_positive = profitable[profitable["TestROI%"] > 0].copy()
    print(f"  Full ROI > 0: {len(profitable)} strategies")
    print(f"  Full ROI > 0 AND Test ROI > 0: {len(both_positive)} strategies")

    # ── Bonferroni correction ──
    bonferroni_alpha = 0.05 / n_tested
    print(f"  Bonferroni-corrected alpha: {bonferroni_alpha:.6f} ({n_tested} tests)")

    # ── 2. Deep dive on best candidate ──
    # Pick the strategy with highest full-sample ROI that also has test ROI > 0
    if both_positive.empty:
        print("\n*** NO STRATEGY HAS BOTH FULL AND TEST ROI > 0 ***")
        if profitable.empty:
            print("*** NO STRATEGY IS PROFITABLE AT ALL ***")
            # Write a collapse report
            report = _write_collapse_report(sweep_df, n_tested)
            OUT_REPORT.write_text(report)
            print(f"\nReport: {OUT_REPORT}")
            return

        # Fall back to best full-sample ROI
        best_row = profitable.iloc[0]
        print(f"\n  Falling back to best full-sample: {best_row['Strategy']}")
    else:
        best_row = both_positive.iloc[0]

    best_label = best_row["Strategy"]
    print(f"\n=== Deep Dive: {best_label} ===")

    # Parse best parameters
    best_params = _parse_label(best_label)
    m_best = filter_races(
        track, year, rnum, fs, fav_prob, prob_gap,
        is_fast, eligible, **best_params,
    )

    full_stats = compute_roi(m_best, hit, payout)
    print(f"  Full: {full_stats['races']} races, ROI {full_stats['roi']:+.1f}%, "
          f"hits {full_stats['hits']}, hit rate {full_stats['hit_rate']:.1f}%")

    # ── 3. Per-year table ──
    print("\n  Per-year breakdown:")
    yt = per_year_table(m_best, hit, payout, year)
    print(f"  {'Year':>6} {'Races':>6} {'Hits':>5} {'ROI%':>8} {'Profit':>10}")
    for r in yt:
        print(f"  {r['year']:>6} {r['races']:>6} {r['hits']:>5} "
              f"{r['roi']:>+8.1f} {r['profit']:>+10.2f}")
    pos_years = sum(1 for r in yt if r["roi"] > 0)
    total_years = len(yt)
    print(f"  Positive years: {pos_years}/{total_years}")

    # ── 4. Bootstrap CI ──
    print("\n  Bootstrap confidence interval (2000 resamples):")
    boot = bootstrap_roi(m_best, hit, payout)
    print(f"  95% CI: [{boot['ci_lo']:+.1f}%, {boot['ci_hi']:+.1f}%]")
    print(f"  Bootstrap mean: {boot['mean']:+.1f}%, median: {boot['median']:+.1f}%")
    ci_covers_zero = boot["ci_lo"] <= 0 <= boot["ci_hi"]
    print(f"  CI covers zero: {'YES — not statistically significant' if ci_covers_zero else 'NO — edge is significant at 95%'}")

    # ── 5. Permutation test ──
    # Baseline: all BEL K1W7-eligible races (no filter beyond track + eligibility)
    all_bel_eligible = (track == "BEL") & eligible
    print(f"\n  Baseline BEL K1W7 pool: {int(all_bel_eligible.sum())} races, "
          f"hit rate {hit[all_bel_eligible].mean()*100:.1f}%")
    print(f"  Permutation test (2000 draws from full BEL pool):")
    perm_result = permutation_test(m_best, hit, payout, all_bel_eligible)
    print(f"  Observed ROI: {perm_result['observed_roi']:+.1f}%, "
          f"hit rate: {perm_result['observed_hr']:.1f}%")
    print(f"  Baseline hit rate: {perm_result['base_hr']:.1f}%")
    print(f"  Null mean ROI: {perm_result['null_mean_roi']:+.1f}% ± {perm_result['null_std_roi']:.1f}%")
    print(f"  p-value (ROI): {perm_result['p_value_roi']:.4f}")
    print(f"  p-value (hit rate): {perm_result['p_value_hr']:.4f}")
    survives_bonferroni = perm_result["p_value_roi"] < bonferroni_alpha
    print(f"  Survives Bonferroni ({bonferroni_alpha:.6f}): "
          f"{'YES' if survives_bonferroni else 'NO'}")

    # ── 6. Walk-forward OOS ──
    print("\n  Walk-forward OOS (5-year train window):")
    wf = walk_forward_oos(m_best, hit, payout, year)
    print(f"  {'Train':>12} {'Test':>6} {'TrnN':>5} {'TrnROI':>8} {'TstN':>5} {'TstROI':>8} {'TstHits':>7}")
    wf_oos_positive = 0
    wf_oos_total = 0
    for r in wf:
        print(f"  {r['train_years']:>12} {r['test_year']:>6} {r['train_races']:>5} "
              f"{r['train_roi']:>+8.1f} {r['test_races']:>5} {r['test_roi']:>+8.1f} {r['test_hits']:>7}")
        if r["test_races"] > 0:
            wf_oos_total += 1
            if r["test_roi"] > 0:
                wf_oos_positive += 1
    print(f"  OOS positive windows: {wf_oos_positive}/{wf_oos_total}")

    # ── 7. Half split and even/odd ──
    print("\n  Alternative time splits:")
    hs = half_split_oos(m_best, hit, payout, year)
    print(f"  First half ({hs['first_half_years']}): "
          f"{hs['first_half_races']} races, ROI {hs['first_half_roi']:+.1f}%")
    print(f"  Second half ({hs['second_half_years']}): "
          f"{hs['second_half_races']} races, ROI {hs['second_half_roi']:+.1f}%")

    eo = even_odd_year_split(m_best, hit, payout, year)
    print(f"  Even years: {eo['even_year_races']} races, ROI {eo['even_year_roi']:+.1f}%")
    print(f"  Odd years:  {eo['odd_year_races']} races, ROI {eo['odd_year_roi']:+.1f}%")

    # ── 8. Broadening attempts ──
    print("\n=== Broadening Attempts ===")
    broaden_results = []

    # Base params for broadening
    bp = best_params.copy()

    # Try broadening each parameter individually
    broaden_specs = [
        # Relax field size
        ("FS 9-14", {**bp, "fs_lo": 9, "fs_hi": 14}),
        ("FS 9-13", {**bp, "fs_lo": 9, "fs_hi": 13}),
        ("FS 10-14", {**bp, "fs_lo": 10, "fs_hi": 14}),
        ("FS 10-15", {**bp, "fs_lo": 10, "fs_hi": 15}),
        # Relax gap
        ("Gap 0.05", {**bp, "gap": 0.05}),
        ("Gap 0.08", {**bp, "gap": 0.08}),
        ("Gap 0.00", {**bp, "gap": 0.00}),
        # Relax favorite min
        ("Fav 0.30", {**bp, "fav_min": 0.30}),
        ("Fav 0.35", {**bp, "fav_min": 0.35}),
        ("Fav 0.00", {**bp, "fav_min": 0.00}),
        # Relax card position
        ("Card midlate", {**bp, "card": "midlate"}),
        ("Card all", {**bp, "card": "all"}),
        # Relax condition
        ("Cond fast", {**bp, "cond": "fast"}),
        ("Cond all", {**bp, "cond": "all"}),
        # Combined relaxations
        ("FS 9-14 + Gap 0.05", {**bp, "fs_lo": 9, "fs_hi": 14, "gap": 0.05}),
        ("FS 10-14 + Fav 0.35", {**bp, "fs_lo": 10, "fs_hi": 14, "fav_min": 0.35}),
        ("FS 10-14 + Gap 0.08 + Fav 0.35",
         {**bp, "fs_lo": 10, "fs_hi": 14, "gap": 0.08, "fav_min": 0.35}),
        ("FS 10-13 + Card midlate",
         {**bp, "fs_lo": 10, "fs_hi": 13, "card": "midlate"}),
        ("All relaxed: FS9-14 Gap0.05 Fav0.30 midlate all-cond",
         {**bp, "fs_lo": 9, "fs_hi": 14, "gap": 0.05, "fav_min": 0.30,
          "card": "midlate", "cond": "all"}),
    ]

    print(f"  {'Variant':<55} {'Races':>6} {'ROI%':>8} {'Hits':>5} {'HR%':>6} {'CI_lo':>8} {'CI_hi':>8}")
    for name, params in broaden_specs:
        mb = filter_races(
            track, year, rnum, fs, fav_prob, prob_gap,
            is_fast, eligible, **params,
        )
        sb = compute_roi(mb, hit, payout)
        bci = bootstrap_roi(mb, hit, payout) if sb["races"] >= 10 else {"ci_lo": np.nan, "ci_hi": np.nan}
        print(f"  {name:<55} {sb['races']:>6} {sb['roi']:>+8.1f} {sb['hits']:>5} "
              f"{sb['hit_rate']:>6.1f} {bci['ci_lo']:>+8.1f} {bci['ci_hi']:>+8.1f}")
        broaden_results.append({
            "name": name,
            "params": params,
            "stats": sb,
            "boot_ci": bci,
        })

    # ── 9. Find best broadened variant that's still profitable ──
    best_broad = None
    for br in broaden_results:
        if br["stats"]["roi"] > 0 and br["stats"]["races"] > full_stats["races"]:
            if best_broad is None or br["stats"]["races"] > best_broad["stats"]["races"]:
                # Prefer more races if still profitable
                best_broad = br
    # Also consider: highest ROI among those with more races
    best_broad_roi = None
    for br in broaden_results:
        if br["stats"]["roi"] > 0 and br["stats"]["races"] > full_stats["races"]:
            if best_broad_roi is None or br["stats"]["roi"] > best_broad_roi["stats"]["roi"]:
                best_broad_roi = br

    # ── 10. Deep dive on best broadened if exists ──
    broad_deep = None
    if best_broad_roi and best_broad_roi["stats"]["races"] >= 50:
        print(f"\n=== Deep Dive: Best Broadened ({best_broad_roi['name']}) ===")
        bparams = best_broad_roi["params"]
        mb = filter_races(
            track, year, rnum, fs, fav_prob, prob_gap,
            is_fast, eligible, **bparams,
        )
        bs = compute_roi(mb, hit, payout)
        print(f"  Full: {bs['races']} races, ROI {bs['roi']:+.1f}%")

        byt = per_year_table(mb, hit, payout, year)
        print(f"  {'Year':>6} {'Races':>6} {'Hits':>5} {'ROI%':>8}")
        for r in byt:
            print(f"  {r['year']:>6} {r['races']:>6} {r['hits']:>5} {r['roi']:>+8.1f}")

        bbci = bootstrap_roi(mb, hit, payout)
        print(f"  Bootstrap 95% CI: [{bbci['ci_lo']:+.1f}%, {bbci['ci_hi']:+.1f}%]")

        bperm = permutation_test(mb, hit, payout, all_bel_eligible)
        print(f"  Permutation p-value (ROI): {bperm['p_value_roi']:.4f}")

        bwf = walk_forward_oos(mb, hit, payout, year)
        wf_pos = sum(1 for r in bwf if r["test_races"] > 0 and r["test_roi"] > 0)
        wf_tot = sum(1 for r in bwf if r["test_races"] > 0)
        print(f"  Walk-forward OOS positive: {wf_pos}/{wf_tot}")

        broad_deep = {
            "name": best_broad_roi["name"],
            "params": bparams,
            "stats": bs,
            "boot": bbci,
            "perm": bperm,
            "per_year": byt,
            "wf": bwf,
            "wf_pos": wf_pos,
            "wf_tot": wf_tot,
        }

    # ── 11. Inspect individual big payoffs ──
    print("\n=== Big Payoff Inspection ===")
    hit_idxs = np.where(m_best & hit)[0]
    hit_payouts = payout[hit_idxs]
    hit_years = year[hit_idxs]
    sort_order = np.argsort(-hit_payouts)
    print(f"  {'#':>3} {'Year':>6} {'Payout':>12}")
    for i, idx in enumerate(sort_order[:10]):
        print(f"  {i+1:>3} {hit_years[idx]:>6} {hit_payouts[idx]:>12,.2f}")

    total_return = float(hit_payouts.sum())
    top1_pct = float(hit_payouts[sort_order[0]]) / total_return * 100.0 if total_return > 0 else 0
    top3_pct = float(hit_payouts[sort_order[:3]].sum()) / total_return * 100.0 if total_return > 0 else 0
    print(f"  Top-1 payoff is {top1_pct:.1f}% of total returns")
    print(f"  Top-3 payoffs are {top3_pct:.1f}% of total returns")

    # ── 12. "Leave one out" — ROI without biggest hit ──
    if len(hit_payouts) > 1:
        without_top1 = total_return - float(hit_payouts[sort_order[0]])
        wagered_all = full_stats["races"] * COST
        roi_no_top1 = (without_top1 - wagered_all) / wagered_all * 100.0
        print(f"  ROI without biggest hit: {roi_no_top1:+.1f}%")

        without_top3 = total_return - float(hit_payouts[sort_order[:3]].sum())
        roi_no_top3 = (without_top3 - wagered_all) / wagered_all * 100.0
        print(f"  ROI without top-3 hits: {roi_no_top3:+.1f}%")
    else:
        roi_no_top1 = -100.0
        roi_no_top3 = -100.0

    # ── SUMMARY & VERDICT ──
    print("\n" + "=" * 60)
    print("PHASE 6 ROBUSTNESS VERDICT")
    print("=" * 60)

    # Collect verdict flags
    flags = []
    if full_stats["races"] < 100:
        flags.append(f"SMALL SAMPLE: only {full_stats['races']} races")
    if ci_covers_zero:
        flags.append("BOOTSTRAP CI COVERS ZERO — edge not significant at 95%")
    if perm_result["p_value_roi"] > 0.05:
        flags.append(f"PERMUTATION p={perm_result['p_value_roi']:.3f} — not significant at 5%")
    if not survives_bonferroni:
        flags.append("FAILS BONFERRONI correction for multiple testing")
    if pos_years < total_years // 2:
        flags.append(f"ONLY {pos_years}/{total_years} POSITIVE YEARS")
    if wf_oos_positive < wf_oos_total // 2:
        flags.append(f"WALK-FORWARD: only {wf_oos_positive}/{wf_oos_total} OOS windows positive")
    if top1_pct > 40:
        flags.append(f"TOP-1 HIT = {top1_pct:.0f}% of returns — concentration risk")
    if roi_no_top1 < 0:
        flags.append("STRATEGY UNPROFITABLE without single biggest hit")

    if not flags:
        verdict = "ROBUST — edge survives all checks"
    elif len(flags) <= 2 and not ci_covers_zero:
        verdict = "PLAUSIBLE — some concerns but edge may be real"
    elif ci_covers_zero and perm_result["p_value_roi"] < 0.10:
        verdict = "MARGINAL — suggestive but not proven"
    else:
        verdict = "FRAGILE — edge likely illusory or too weak to trade"

    print(f"\nBest full ROI:  {full_stats['roi']:+.1f}%")
    print(f"Best OOS ROI:   {best_row['TestROI%']:+.1f}% (Phase 5 split)")
    print(f"Sample size:    {full_stats['races']} races")
    print(f"Bootstrap 95% CI: [{boot['ci_lo']:+.1f}%, {boot['ci_hi']:+.1f}%]")
    print(f"Permutation p (ROI): {perm_result['p_value_roi']:.4f}")
    print(f"Permutation p (HR):  {perm_result['p_value_hr']:.4f}")
    print(f"Verdict:        {verdict}")
    if flags:
        print("\nConcerns:")
        for f in flags:
            print(f"  • {f}")

    if broad_deep:
        print(f"\nBest broadened variant: {broad_deep['name']}")
        print(f"  ROI: {broad_deep['stats']['roi']:+.1f}%, "
              f"Races: {broad_deep['stats']['races']}, "
              f"CI: [{broad_deep['boot']['ci_lo']:+.1f}%, {broad_deep['boot']['ci_hi']:+.1f}%]")

    # ── Plain English rule for best candidate ──
    bp = best_params
    rule_text = (
        f"At Belmont Park, in races {_card_desc(bp['card'])} on the card "
        f"with {_cond_desc(bp['cond'])} track conditions, "
        f"when the field has {bp['fs_lo']} to {bp['fs_hi']} runners, "
        f"the favorite's implied probability is at least {bp['fav_min']:.0%}, "
        f"and the probability gap between the favorite and second choice is at least "
        f"{bp['gap']:.0%}: "
        f"play a $2 Key-1-with-7 superfecta keying the favorite on top "
        f"over the next 6 choices by odds. "
        f"(Cost: ${COST} per race.)"
    )
    print(f"\n=== Candidate Rule (Plain English) ===\n{rule_text}")

    print(f"\n=== File Paths ===")
    print(f"  Script:  {Path(__file__).resolve()}")
    print(f"  Summary: {OUT_CSV}")
    print(f"  Report:  {OUT_REPORT}")

    # ── Write report ──
    report = _build_report(
        best_row, full_stats, yt, boot, perm_result, wf,
        wf_oos_positive, wf_oos_total, hs, eo,
        broaden_results, broad_deep, hit_payouts, sort_order,
        top1_pct, top3_pct, roi_no_top1, roi_no_top3,
        sweep_df, n_tested, bonferroni_alpha, verdict, flags,
        rule_text, best_params,
    )
    OUT_REPORT.write_text(report)
    print(f"\nReport written to {OUT_REPORT}")


def _parse_label(label: str) -> dict:
    """Parse strategy label back to filter params."""
    # K1W7_BEL_FS10-12_Gap0.20_Fav0.40_all_late
    parts = label.split("_")
    fs_part = parts[2].replace("FS", "").split("-")
    gap = float(parts[3].replace("Gap", ""))
    fav_min = float(parts[4].replace("Fav", ""))
    cond = parts[5]
    card = parts[6]
    return {
        "fs_lo": int(fs_part[0]),
        "fs_hi": int(fs_part[1]),
        "gap": gap,
        "fav_min": fav_min,
        "cond": cond,
        "card": card,
    }


def _card_desc(card: str) -> str:
    if card == "late":
        return "race 7 or later"
    elif card == "midlate":
        return "race 5 or later"
    return "any position"


def _cond_desc(cond: str) -> str:
    if cond == "fast":
        return "fast (FT/FM)"
    return "any"


def _write_collapse_report(sweep_df: pd.DataFrame, n_tested: int) -> str:
    return f"""# Phase 6 Report — BEL Robustness

## Verdict: COLLAPSED

The BEL pocket from Phase 5 does not survive Phase 6 testing.
No strategy variant produced a positive full-sample ROI with {n_tested} variants tested.

### Top strategies by ROI
(see backtest_phase6_summary.csv)
"""


def _build_report(
    best_row, full_stats, yt, boot, perm_result, wf,
    wf_oos_positive, wf_oos_total, hs, eo,
    broaden_results, broad_deep, hit_payouts, sort_order,
    top1_pct, top3_pct, roi_no_top1, roi_no_top3,
    sweep_df, n_tested, bonferroni_alpha, verdict, flags,
    rule_text, best_params,
) -> str:
    lines = [
        "# Phase 6 Report — BEL Robustness",
        "",
        f"## Verdict: {verdict}",
        "",
    ]
    if flags:
        lines.append("### Concerns")
        for f in flags:
            lines.append(f"- {f}")
        lines.append("")

    lines += [
        "## Best Strategy",
        f"- **Strategy:** `{best_row['Strategy']}`",
        f"- **Full ROI:** {full_stats['roi']:+.2f}%",
        f"- **Test ROI (Phase 5 split):** {best_row['TestROI%']:+.2f}%",
        f"- **Races:** {full_stats['races']}",
        f"- **Hits / Hit Rate:** {full_stats['hits']} / {full_stats['hit_rate']:.1f}%",
        f"- **Avg Payout:** ${full_stats['avg_pay']:,.2f}",
        "",
        "## Statistical Tests",
        f"- **Bootstrap 95% CI:** [{boot['ci_lo']:+.1f}%, {boot['ci_hi']:+.1f}%]",
        f"- **Bootstrap mean ROI:** {boot['mean']:+.1f}%",
        f"- **Permutation p-value (ROI):** {perm_result['p_value_roi']:.4f}",
        f"- **Permutation p-value (hit rate):** {perm_result['p_value_hr']:.4f}",
        f"- **Observed hit rate:** {perm_result['observed_hr']:.1f}% vs baseline {perm_result['base_hr']:.1f}%",
        f"- **Bonferroni alpha:** {bonferroni_alpha:.6f} ({n_tested} tests)",
        f"- **Survives Bonferroni:** {'Yes' if perm_result['p_value_roi'] < bonferroni_alpha else 'No'}",
        "",
        "## Per-Year Breakdown",
        "",
        "| Year | Races | Hits | ROI% | Profit |",
        "|------|-------|------|------|--------|",
    ]
    for r in yt:
        lines.append(
            f"| {r['year']} | {r['races']} | {r['hits']} | "
            f"{r['roi']:+.1f}% | ${r['profit']:+,.2f} |"
        )
    pos_y = sum(1 for r in yt if r["roi"] > 0)
    lines += [
        "",
        f"Positive years: {pos_y}/{len(yt)}",
        "",
        "## Walk-Forward Out-of-Sample",
        "",
        "| Train | Test | Train N | Train ROI | Test N | Test ROI | Test Hits |",
        "|-------|------|---------|-----------|--------|----------|-----------|",
    ]
    for r in wf:
        lines.append(
            f"| {r['train_years']} | {r['test_year']} | {r['train_races']} | "
            f"{r['train_roi']:+.1f}% | {r['test_races']} | {r['test_roi']:+.1f}% | {r['test_hits']} |"
        )
    lines += [
        "",
        f"OOS positive windows: {wf_oos_positive}/{wf_oos_total}",
        "",
        "## Alternative Time Splits",
        f"- First half ({hs['first_half_years']}): {hs['first_half_races']} races, ROI {hs['first_half_roi']:+.1f}%",
        f"- Second half ({hs['second_half_years']}): {hs['second_half_races']} races, ROI {hs['second_half_roi']:+.1f}%",
        f"- Even years: {eo['even_year_races']} races, ROI {eo['even_year_roi']:+.1f}%",
        f"- Odd years: {eo['odd_year_races']} races, ROI {eo['odd_year_roi']:+.1f}%",
        "",
        "## Payoff Concentration",
        f"- Top-1 hit: {top1_pct:.1f}% of total returns",
        f"- Top-3 hits: {top3_pct:.1f}% of total returns",
        f"- ROI without biggest hit: {roi_no_top1:+.1f}%",
        f"- ROI without top-3 hits: {roi_no_top3:+.1f}%",
        "",
        "## Broadening Attempts",
        "",
        "| Variant | Races | ROI% | Hits | HR% | CI Lo | CI Hi |",
        "|---------|-------|------|------|-----|-------|-------|",
    ]
    for br in broaden_results:
        s = br["stats"]
        c = br["boot_ci"]
        lo = f"{c['ci_lo']:+.1f}" if not np.isnan(c.get("ci_lo", np.nan)) else "n/a"
        hi = f"{c['ci_hi']:+.1f}" if not np.isnan(c.get("ci_hi", np.nan)) else "n/a"
        lines.append(
            f"| {br['name']} | {s['races']} | {s['roi']:+.1f}% | "
            f"{s['hits']} | {s['hit_rate']:.1f}% | {lo}% | {hi}% |"
        )

    if broad_deep:
        bd = broad_deep
        lines += [
            "",
            f"### Best Broadened Variant: {bd['name']}",
            f"- ROI: {bd['stats']['roi']:+.1f}%",
            f"- Races: {bd['stats']['races']}",
            f"- Bootstrap CI: [{bd['boot']['ci_lo']:+.1f}%, {bd['boot']['ci_hi']:+.1f}%]",
            f"- Permutation p (ROI): {bd['perm']['p_value_roi']:.4f}",
            f"- Walk-forward positive: {bd['wf_pos']}/{bd['wf_tot']}",
        ]

    lines += [
        "",
        "## Candidate Rule (Plain English)",
        "",
        rule_text,
        "",
        "## Sweep Summary",
        f"- Variants tested: {n_tested}",
        f"- Met min-race threshold: {len(sweep_df)}",
        f"- Full ROI > 0: {len(sweep_df[sweep_df['ROI%'] > 0])}",
        f"- Full + Test ROI > 0: {len(sweep_df[(sweep_df['ROI%'] > 0) & (sweep_df['TestROI%'] > 0)])}",
        "",
        f"### Top 20 by Full ROI",
        "",
    ]
    # Manual markdown table instead of to_markdown (avoids tabulate dep)
    top20 = sweep_df.head(20)
    cols = list(top20.columns)
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, r in top20.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
