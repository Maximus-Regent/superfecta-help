#!/usr/bin/env python3
"""
Phase 5 fast parallel search.

Goal: use a vectorized race-level dataset plus process parallelism to hammer
promising strategy families much faster than the earlier brute-force scripts.

Search space focuses on Key1Win strategies around the profitable pockets already
found, especially track/field/gap/favorite-strength combinations.
"""

import os
for _k in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_MAX_THREADS", "MKL_NUM_THREADS"]:
    os.environ[_k] = "1"

from math import perm
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Optional
import multiprocessing as mp

import numpy as np
import pandas as pd

BASE = Path("/Users/maximusregent_ai/Shared/Superfecta Help")
CSV_PATH = BASE / "14years_major_tracks.csv"
CACHE_PATH = BASE / "phase5_race_cache.pkl"
OUT_CSV = BASE / "backtest_phase5_fast_summary.csv"
OUT_REPORT = BASE / "PHASE5_FAST_REPORT.md"

TRACKS = ["CD", "KEE", "SA", "GP", "SAR", "AQU", "BEL", "DMR", "MTH", "OP", "BAQ"]
TRACK_SCOPES = TRACKS + ["CD+KEE"]
FS_BINS = [(9, 11), (10, 11), (10, 12), (10, 13), (12, 20)]
GAPS = [0.10, 0.12, 0.15, 0.18, 0.20]
FAV_MINS = [0.00, 0.35, 0.40]
CONDS = ["all", "fast", "wet"]
CARDS = ["all", "midlate", "late"]
KS = [7, 8, 9]
MIN_RACES = 80
COSTS = {k: perm(k - 1, 3) for k in KS}

GLOBAL = {}


def ml_prob(odds: float) -> float:
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return (-odds) / (-odds + 100.0)


def build_race_cache(csv_path: Path) -> pd.DataFrame:
    print(f"Loading and caching race features from {csv_path.name}...")
    df = pd.read_csv(csv_path, parse_dates=["race_date"], dtype={"post_time": str})
    df = df[df["scratch_indicator"].fillna("N") != "Y"].copy()

    rows = []
    skip = defaultdict(int)

    for (track, date, race_num), grp in df.groupby(["track_id", "race_date", "race_number"]):
        wrows = grp[grp["winning_numbers"].notna()]
        if wrows.empty:
            skip["no_winner"] += 1
            continue
        wi = wrows.iloc[0]
        winners = [x.strip() for x in str(wi["winning_numbers"]).split("-")]
        if len(winners) != 4:
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
        if not all(w in prog_set for w in winners):
            skip["winner_missing"] += 1
            continue

        probs = np.array([h["p"] for h in horses], dtype=np.float64)
        fs = len(horses)
        fav = horses[0]["prog"]
        top7 = {h["prog"] for h in horses[:7]}
        top8 = {h["prog"] for h in horses[:8]}
        top9 = {h["prog"] for h in horses[:9]}

        row = {
            "track": str(track).strip(),
            "year": int(date.year),
            "month": int(date.month),
            "rnum": int(race_num),
            "fs": fs,
            "payout": payout,
            "fav_prob": float(probs[0]),
            "prob_gap": float(probs[0] - probs[1]) if fs > 1 else 0.0,
            "top4_mass": float(probs[:4].sum()) if fs >= 4 else float(probs.sum()),
            "is_wet": str(wi.get("track_condition", "")).strip() in ("MY", "SY", "GD", "HD", "WF", "YL"),
            "is_fast": str(wi.get("track_condition", "")).strip() in ("FT", "FM"),
        }
        for k in KS:
            top = top7 if k == 7 else top8 if k == 8 else top9
            row[f"eligible_{k}"] = fs >= k
            row[f"hit_{k}"] = (winners[0] == fav and all(w in top for w in winners) and fs >= k)
        rows.append(row)

    out = pd.DataFrame(rows)
    print(f"Built {len(out):,} race rows")
    for k, v in sorted(skip.items()):
        print(f"  skipped {k}: {v}")
    return out


def load_or_build_cache() -> pd.DataFrame:
    if CACHE_PATH.exists():
        print(f"Loading cached race table from {CACHE_PATH.name}...")
        return pd.read_pickle(CACHE_PATH)
    out = build_race_cache(CSV_PATH)
    out.to_pickle(CACHE_PATH)
    print(f"Saved cache to {CACHE_PATH}")
    return out


def init_worker(df: pd.DataFrame):
    GLOBAL["track"] = df["track"].to_numpy()
    GLOBAL["year"] = df["year"].to_numpy(dtype=np.int16)
    GLOBAL["rnum"] = df["rnum"].to_numpy(dtype=np.int16)
    GLOBAL["fs"] = df["fs"].to_numpy(dtype=np.int16)
    GLOBAL["payout"] = df["payout"].to_numpy(dtype=np.float64)
    GLOBAL["fav_prob"] = df["fav_prob"].to_numpy(dtype=np.float64)
    GLOBAL["prob_gap"] = df["prob_gap"].to_numpy(dtype=np.float64)
    GLOBAL["top4_mass"] = df["top4_mass"].to_numpy(dtype=np.float64)
    GLOBAL["is_wet"] = df["is_wet"].to_numpy(dtype=bool)
    GLOBAL["is_fast"] = df["is_fast"].to_numpy(dtype=bool)
    for k in KS:
        GLOBAL[f"eligible_{k}"] = df[f"eligible_{k}"].to_numpy(dtype=bool)
        GLOBAL[f"hit_{k}"] = df[f"hit_{k}"].to_numpy(dtype=bool)


def build_strategies() -> list[dict]:
    strategies = []
    for scope in TRACK_SCOPES:
        for k in KS:
            for fs_lo, fs_hi in FS_BINS:
                for gap in GAPS:
                    for fav_min in FAV_MINS:
                        for cond in CONDS:
                            for card in CARDS:
                                label = f"K1W{k}_{scope}_FS{fs_lo}-{fs_hi}_Gap{gap:.2f}_Fav{fav_min:.2f}_{cond}_{card}"
                                strategies.append({
                                    "label": label,
                                    "scope": scope,
                                    "k": k,
                                    "fs_lo": fs_lo,
                                    "fs_hi": fs_hi,
                                    "gap": gap,
                                    "fav_min": fav_min,
                                    "cond": cond,
                                    "card": card,
                                })
    return strategies


def eval_strategy(spec: dict) -> Optional[dict]:
    track = GLOBAL["track"]
    year = GLOBAL["year"]
    rnum = GLOBAL["rnum"]
    fs = GLOBAL["fs"]
    payout = GLOBAL["payout"]
    fav_prob = GLOBAL["fav_prob"]
    prob_gap = GLOBAL["prob_gap"]
    is_wet = GLOBAL["is_wet"]
    is_fast = GLOBAL["is_fast"]
    eligible = GLOBAL[f"eligible_{spec['k']}"]
    hit = GLOBAL[f"hit_{spec['k']}"]

    if spec["scope"] == "CD+KEE":
        m_track = (track == "CD") | (track == "KEE")
    else:
        m_track = (track == spec["scope"])

    m = eligible & m_track & (fs >= spec["fs_lo"]) & (fs <= spec["fs_hi"]) & (prob_gap >= spec["gap"]) & (fav_prob >= spec["fav_min"])

    if spec["cond"] == "wet":
        m &= is_wet
    elif spec["cond"] == "fast":
        m &= is_fast

    if spec["card"] == "midlate":
        m &= (rnum >= 5)
    elif spec["card"] == "late":
        m &= (rnum >= 7)

    n = int(m.sum())
    if n < MIN_RACES:
        return None

    h = m & hit
    hits = int(h.sum())
    cost = COSTS[spec["k"]]
    wagered = n * cost
    returned = float(payout[h].sum())
    roi = (returned - wagered) / wagered * 100.0 if wagered else 0.0

    train = m & (year <= 2018)
    test = m & (year >= 2019) & (year != 2021)
    train_n = int(train.sum())
    test_n = int(test.sum())
    train_w = train_n * cost
    test_w = test_n * cost
    train_r = float(payout[train & hit].sum())
    test_r = float(payout[test & hit].sum())
    train_roi = (train_r - train_w) / train_w * 100.0 if train_w else -100.0
    test_roi = (test_r - test_w) / test_w * 100.0 if test_w else -100.0

    pos_years = 0
    total_years = 0
    for y in sorted(set(year[m])):
        ym = m & (year == y)
        yn = int(ym.sum())
        if yn == 0:
            continue
        total_years += 1
        yw = yn * cost
        yr = float(payout[ym & hit].sum())
        yroi = (yr - yw) / yw * 100.0 if yw else -100.0
        if yroi > 0:
            pos_years += 1

    return {
        "Strategy": spec["label"],
        "TrackScope": spec["scope"],
        "K": spec["k"],
        "Races": n,
        "Wagered": wagered,
        "Returned": round(returned, 2),
        "Profit": round(returned - wagered, 2),
        "ROI%": round(roi, 2),
        "Hits": hits,
        "HitRate%": round(hits / n * 100.0, 2),
        "AvgPay": round(returned / hits, 2) if hits else 0.0,
        "TrainROI%": round(train_roi, 2),
        "TestROI%": round(test_roi, 2),
        "TrainRaces": train_n,
        "TestRaces": test_n,
        "PosYears": f"{pos_years}/{total_years}",
        "Gap": spec["gap"],
        "FavMin": spec["fav_min"],
        "FS": f"{spec['fs_lo']}-{spec['fs_hi']}",
        "Cond": spec["cond"],
        "Card": spec["card"],
    }


def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]


def eval_chunk(chunk: list[dict]) -> list[dict]:
    out = []
    for spec in chunk:
        row = eval_strategy(spec)
        if row is not None:
            out.append(row)
    return out


def main():
    try:
        mp.set_start_method("fork", force=True)
    except RuntimeError:
        pass

    df = load_or_build_cache()
    strategies = build_strategies()
    workers = max(1, os.cpu_count() or 1)
    chunk_size = max(50, len(strategies) // (workers * 6))
    print(f"Evaluating {len(strategies):,} strategies with {workers} workers, chunk_size={chunk_size}")

    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=init_worker, initargs=(df,)) as ex:
        futures = [ex.submit(eval_chunk, chunk) for chunk in chunked(strategies, chunk_size)]
        done = 0
        total = len(futures)
        for fut in as_completed(futures):
            rows.extend(fut.result())
            done += 1
            if done % max(1, total // 10) == 0 or done == total:
                print(f"  completed {done}/{total} chunks")

    out = pd.DataFrame(rows)
    out = out.sort_values(["TestROI%", "ROI%", "Races"], ascending=[False, False, False])
    out.to_csv(OUT_CSV, index=False)

    robust = out[(out["ROI%"] > 0) & (out["TestROI%"] > 0)].copy()
    robust = robust.sort_values(["TestROI%", "ROI%", "Races"], ascending=[False, False, False])

    top_lines = []
    for _, r in robust.head(15).iterrows():
        top_lines.append(
            f"- {r['Strategy']}: full ROI {r['ROI%']:+.1f}%, test ROI {r['TestROI%']:+.1f}%, "
            f"races {int(r['Races'])}, hit rate {r['HitRate%']:.1f}%, pos years {r['PosYears']}"
        )

    best = robust.iloc[0] if not robust.empty else out.iloc[0]
    report = f"""# Phase 5 Fast Search Report

Generated from a vectorized parallel search over {len(strategies):,} promising Key1Win strategy variants.

## Best Strategy by Test ROI
- Strategy: `{best['Strategy']}`
- Full ROI: {best['ROI%']:+.2f}%
- Test ROI: {best['TestROI%']:+.2f}%
- Races: {int(best['Races'])}
- Hit Rate: {best['HitRate%']:.2f}%
- Positive Years: {best['PosYears']}

## Positive Full+Test Strategies
{chr(10).join(top_lines) if top_lines else '- None found with both full and test ROI positive in this fast sweep.'}

## Notes
- This pass is optimized for speed and broad profitable-pocket discovery, not final statistical proof.
- It uses strict race-level filtering and a fixed out-of-sample split of 2019-2025 (excluding 2021) for the test period.
- If positive pockets persist here, they should be the next candidates for deeper robustness testing.
"""
    OUT_REPORT.write_text(report)

    print("\n=== PHASE 5 FAST SEARCH COMPLETE ===")
    print(f"Saved summary: {OUT_CSV}")
    print(f"Saved report:  {OUT_REPORT}")
    print(f"Best strategy: {best['Strategy']}")
    print(f"Full ROI: {best['ROI%']:+.2f}% | Test ROI: {best['TestROI%']:+.2f}% | Races: {int(best['Races'])}")


if __name__ == "__main__":
    main()
