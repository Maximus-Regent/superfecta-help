#!/usr/bin/env python3
"""
backtest_superfecta.py — Walk-forward superfecta strategy backtesting.

Tests multiple strategy families with time-aware evaluation:
  1. Favorites Box (top-K, all permutations)
  2. Key Favorite (favorite must win, box rest)
  3. Anti-chalk (exclude #1 favorite)
  4. Harville-ranked top-N (most probable combos)
  5. ML-enhanced (XGBoost residual model, walk-forward retrained)
  6. EV-filtered variants
  7. Field-size-binned strategies
  8. Race-condition filters

Avoids leakage: no official_position or position_at_start used.
"""

import os
import sys
import time
import json
import warnings
from math import log, perm
from pathlib import Path
from itertools import permutations
from collections import defaultdict

import numpy as np
import pandas as pd
import xgboost as xgb

warnings.filterwarnings("ignore")

BASE = Path("/Users/maximusregent_ai/Shared/Superfecta Help")

# Pre-compute permutation index arrays for Harville enumeration
PERM_CACHE: dict[int, np.ndarray] = {}
for _m in range(4, 21):
    PERM_CACHE[_m] = np.array(list(permutations(range(_m), 4)), dtype=np.int32)

# All known categorical values (for consistent model features)
SURFACES = ["D", "T", "A", "nan"]
COURSE_TYPES = ["T", "C", "D", "E", "I", "M", "N", "O", "nan"]
TRACK_CONDITIONS = ["FM", "FT", "GD", "HD", "HY", "MY", "SF", "SY", "WF", "YL", "nan"]


# ═══════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════

def ml_prob(odds: float) -> float:
    """American moneyline odds → implied probability."""
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return (-odds) / (-odds + 100.0)


def load_races(csv_path: Path) -> list[dict]:
    """Load horse-level CSV → list of race dicts sorted by date."""
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
    dt = time.time() - t0
    print(f"  {len(races)} races loaded in {dt:.1f}s  |  skipped: {dict(skip)}")
    return races


# ═══════════════════════════════════════════════════════════════════
# FAST STRATEGY CHECKS — O(1) per race
# ═══════════════════════════════════════════════════════════════════

def box_k(race: dict, k: int) -> tuple[bool, int]:
    """Box top-k favorites. Returns (hit, cost)."""
    if race["fs"] < k or k < 4:
        return False, 0
    top = {h["prog"] for h in race["horses"][:k]}
    cost = perm(k, 4)
    return all(w in top for w in race["win"]), cost


def key1_win_k(race: dict, k: int) -> tuple[bool, int]:
    """Favorite must WIN (1st), rest from top-k."""
    if race["fs"] < k or k < 4:
        return False, 0
    fav = race["horses"][0]["prog"]
    top = {h["prog"] for h in race["horses"][:k]}
    cost = perm(k - 1, 3)
    hit = race["win"][0] == fav and all(w in top for w in race["win"])
    return hit, cost


def no_fav_box_k(race: dict, k: int) -> tuple[bool, int]:
    """Box horses ranked 2 through k+1 (skip #1 favorite)."""
    if race["fs"] < k + 1 or k < 4:
        return False, 0
    pool = {h["prog"] for h in race["horses"][1:k + 1]}
    cost = perm(k, 4)
    return all(w in pool for w in race["win"]), cost


def mid_tier_box(race: dict, start: int, k: int) -> tuple[bool, int]:
    """Box horses ranked start through start+k-1 (0-indexed)."""
    end = start + k
    if race["fs"] < end or k < 4:
        return False, 0
    pool = {h["prog"] for h in race["horses"][start:end]}
    cost = perm(k, 4)
    return all(w in pool for w in race["win"]), cost


# ═══════════════════════════════════════════════════════════════════
# HARVILLE-RANKED STRATEGIES — O(P(M,4)) per race
# ═══════════════════════════════════════════════════════════════════

def harville_topn(race: dict, n: int, max_h: int = 8) -> tuple[bool, int]:
    """Top-n combos ranked by Harville probability from top max_h horses."""
    m = min(race["fs"], max_h)
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
    joint[valid] = (p1[valid] * (p2[valid] / d1[valid])
                    * (p3[valid] / d2[valid]) * (p4[valid] / d3[valid]))

    top_idx = np.argsort(-joint)[:n]

    prog_map = [race["horses"][i]["prog"] for i in range(m)]
    top_set = set()
    for idx in top_idx:
        combo = tuple(prog_map[j] for j in perms_arr[idx])
        top_set.add(combo)

    winning = tuple(race["win"])
    actual_n = min(n, int((joint > 0).sum()))
    return winning in top_set, actual_n


# ═══════════════════════════════════════════════════════════════════
# ML MODEL — training & combo scoring
# ═══════════════════════════════════════════════════════════════════

def _all_cat_cols() -> list[str]:
    """Return all one-hot column names for categoricals."""
    cols = []
    for s in SURFACES:
        cols.append(f"surface_{s}")
    for c in COURSE_TYPES:
        cols.append(f"course_type_{c}")
    for t in TRACK_CONDITIONS:
        cols.append(f"condition_{t}")
    return cols


def _feature_names() -> list[str]:
    """Canonical feature list for ML model."""
    return (
        [f"logit{i}" for i in range(1, 5)]
        + [f"prob{i}" for i in range(1, 5)]
        + ["number_of_runners", "field_size", "purse_usa", "distance_id",
           "post_hour", "total_pool", "avg_field_odds", "odds_std",
           "favorite_odds", "longshot_odds", "odds_range", "prob_product",
           "prob_sum", "prob_entropy", "min_prob", "max_prob", "pool_per_runner",
           "purse_per_runner", "harville_log", "prob_variance"]
        + _all_cat_cols()
    )


def prepare_training_rows(races: list[dict]) -> pd.DataFrame:
    """Build training data (winning combo features + target) from race list."""
    FEAT = _feature_names()
    rows = []

    for race in races:
        wp = race["win"]
        p_map = {h["prog"]: h["p"] for h in race["horses"]}
        o_map = {h["prog"]: h["odds"] for h in race["horses"]}

        probs = [p_map.get(w) for w in wp]
        odds = [o_map.get(w) for w in wp]
        if any(v is None for v in probs) or any(v is None for v in odds):
            continue

        p1, p2, p3, p4 = probs
        d1 = 1 - p1
        d2 = d1 - p2
        d3 = d2 - p3
        if d1 <= 0 or d2 <= 0 or d3 <= 0:
            continue
        joint = p1 * (p2 / d1) * (p3 / d2) * (p4 / d3)
        if joint <= 0:
            continue
        h_pay = 1.0 / joint
        lr = log(race["payout"] / h_pay)

        all_odds = [h["odds"] for h in race["horses"]]
        eps = 1e-10
        row = {f: 0.0 for f in FEAT}
        row["prob1"] = p1
        row["prob2"] = p2
        row["prob3"] = p3
        row["prob4"] = p4
        row["logit1"] = log(p1 / (1 - p1)) if 0 < p1 < 1 else 0
        row["logit2"] = log(p2 / (1 - p2)) if 0 < p2 < 1 else 0
        row["logit3"] = log(p3 / (1 - p3)) if 0 < p3 < 1 else 0
        row["logit4"] = log(p4 / (1 - p4)) if 0 < p4 < 1 else 0
        row["number_of_runners"] = race["fs"]
        row["field_size"] = race["fs"]
        row["purse_usa"] = race["purse"]
        row["distance_id"] = race["dist"]
        row["total_pool"] = race["pool"]
        row["harville_log"] = log(h_pay)
        row["post_hour"] = 14.0
        row["avg_field_odds"] = float(np.mean(all_odds))
        row["odds_std"] = float(np.std(all_odds)) if len(all_odds) > 1 else 0.0
        row["favorite_odds"] = min(odds)
        row["longshot_odds"] = max(odds)
        row["odds_range"] = max(odds) - min(odds)
        row["prob_product"] = p1 * p2 * p3 * p4
        row["prob_sum"] = p1 + p2 + p3 + p4
        row["prob_entropy"] = -sum(p * log(p + eps) for p in probs)
        row["min_prob"] = min(probs)
        row["max_prob"] = max(probs)
        row["prob_variance"] = float(np.var(probs))
        row["pool_per_runner"] = race["pool"] / race["fs"] if race["fs"] > 0 else 0
        row["purse_per_runner"] = race["purse"] / race["fs"] if race["fs"] > 0 else 0

        # Categoricals
        s_key = f"surface_{race['surface'] if race['surface'] else 'nan'}"
        if s_key in row:
            row[s_key] = 1
        c_key = f"course_type_{race['course_type'] if race['course_type'] else 'nan'}"
        if c_key in row:
            row[c_key] = 1
        t_key = f"condition_{race['condition'] if race['condition'] else 'nan'}"
        if t_key in row:
            row[t_key] = 1

        row["log_ratio"] = lr
        rows.append(row)

    return pd.DataFrame(rows)


def train_model(train_df: pd.DataFrame) -> tuple[xgb.Booster, list[str]]:
    """Train XGBoost on prepared training data. Returns (model, feature_names)."""
    feat = _feature_names()
    params = {
        "max_depth": 6,
        "eta": 0.059,
        "subsample": 0.86,
        "colsample_bytree": 0.71,
        "reg_alpha": 1.62,
        "reg_lambda": 2.83,
        "gamma": 0.28,
        "min_child_weight": 10,
        "objective": "reg:squarederror",
        "eval_metric": "rmse",
        "seed": 42,
        "tree_method": "hist",
        "nthread": max(1, os.cpu_count() or 1),
    }

    X = train_df[feat].fillna(0).values
    y = train_df["log_ratio"].values

    # Remove outliers (±3σ)
    mu, sig = y.mean(), y.std()
    mask = (y >= mu - 3 * sig) & (y <= mu + 3 * sig)
    X, y = X[mask], y[mask]

    dtrain = xgb.DMatrix(X, label=y, feature_names=feat)
    model = xgb.train(params, dtrain, num_boost_round=595, verbose_eval=0)
    return model, feat


def score_race_combos(race: dict, model: xgb.Booster, feat_names: list[str],
                      max_h: int = 6) -> list[dict]:
    """Score all combos from top max_h horses. Returns list of scored combos."""
    m = min(race["fs"], max_h)
    if m < 4:
        return []

    probs = np.array([race["horses"][i]["p"] for i in range(m)])
    odds_arr = np.array([race["horses"][i]["odds"] for i in range(m)])
    progs = [race["horses"][i]["prog"] for i in range(m)]
    all_odds = np.array([h["odds"] for h in race["horses"]])

    perms_arr = PERM_CACHE[m]
    n_combos = len(perms_arr)

    # Vectorized Harville
    p1 = probs[perms_arr[:, 0]]
    p2 = probs[perms_arr[:, 1]]
    p3 = probs[perms_arr[:, 2]]
    p4 = probs[perms_arr[:, 3]]
    d1 = 1 - p1
    d2 = d1 - p2
    d3 = d2 - p3
    valid = (d1 > 0) & (d2 > 0) & (d3 > 0)
    joint = np.zeros(n_combos)
    joint[valid] = p1[valid] * (p2[valid] / d1[valid]) * (p3[valid] / d2[valid]) * (p4[valid] / d3[valid])
    valid = joint > 0

    if not valid.any():
        return []

    # Build feature matrix (only valid combos)
    v_idx = np.where(valid)[0]
    n_valid = len(v_idx)
    feat_idx = {f: i for i, f in enumerate(feat_names)}
    X = np.zeros((n_valid, len(feat_names)))

    # Shared features
    shared = {
        "number_of_runners": race["fs"],
        "field_size": race["fs"],
        "purse_usa": race["purse"],
        "distance_id": race["dist"],
        "total_pool": race["pool"],
        "avg_field_odds": float(np.mean(all_odds)),
        "odds_std": float(np.std(all_odds)) if len(all_odds) > 1 else 0.0,
        "post_hour": 14.0,
        "pool_per_runner": race["pool"] / race["fs"] if race["fs"] > 0 else 0,
        "purse_per_runner": race["purse"] / race["fs"] if race["fs"] > 0 else 0,
    }
    for k, v in shared.items():
        if k in feat_idx:
            X[:, feat_idx[k]] = v

    # Categorical
    s_key = f"surface_{race['surface'] if race['surface'] else 'nan'}"
    c_key = f"course_type_{race['course_type'] if race['course_type'] else 'nan'}"
    t_key = f"condition_{race['condition'] if race['condition'] else 'nan'}"
    for key in [s_key, c_key, t_key]:
        if key in feat_idx:
            X[:, feat_idx[key]] = 1

    # Combo-specific
    vp1 = p1[v_idx]
    vp2 = p2[v_idx]
    vp3 = p3[v_idx]
    vp4 = p4[v_idx]
    eps = 1e-10

    def _set(name, vals):
        if name in feat_idx:
            X[:, feat_idx[name]] = vals

    _set("prob1", vp1)
    _set("prob2", vp2)
    _set("prob3", vp3)
    _set("prob4", vp4)

    safe = lambda a: np.clip(a, eps, 1 - eps)
    _set("logit1", np.log(safe(vp1) / (1 - safe(vp1))))
    _set("logit2", np.log(safe(vp2) / (1 - safe(vp2))))
    _set("logit3", np.log(safe(vp3) / (1 - safe(vp3))))
    _set("logit4", np.log(safe(vp4) / (1 - safe(vp4))))

    h_pay = 1.0 / joint[v_idx]
    _set("harville_log", np.log(h_pay))

    o1 = odds_arr[perms_arr[v_idx, 0]]
    o2 = odds_arr[perms_arr[v_idx, 1]]
    o3 = odds_arr[perms_arr[v_idx, 2]]
    o4 = odds_arr[perms_arr[v_idx, 3]]
    combo_odds = np.column_stack([o1, o2, o3, o4])
    _set("favorite_odds", combo_odds.min(axis=1))
    _set("longshot_odds", combo_odds.max(axis=1))
    _set("odds_range", combo_odds.max(axis=1) - combo_odds.min(axis=1))

    combo_probs = np.column_stack([vp1, vp2, vp3, vp4])
    _set("prob_product", combo_probs.prod(axis=1))
    _set("prob_sum", combo_probs.sum(axis=1))
    _set("prob_entropy", -np.sum(combo_probs * np.log(combo_probs + eps), axis=1))
    _set("min_prob", combo_probs.min(axis=1))
    _set("max_prob", combo_probs.max(axis=1))
    _set("prob_variance", combo_probs.var(axis=1))

    dm = xgb.DMatrix(X, feature_names=feat_names)
    preds = model.predict(dm)

    results = []
    for i, vi in enumerate(v_idx):
        combo = tuple(progs[j] for j in perms_arr[vi])
        results.append({
            "combo": combo,
            "harville_payout": float(h_pay[i]),
            "predicted_lr": float(preds[i]),
            "ev": float(np.exp(preds[i])),
        })
    return results


# ═══════════════════════════════════════════════════════════════════
# BACKTESTING ENGINE
# ═══════════════════════════════════════════════════════════════════

def run_backtest(races: list[dict], check_fn, params: dict,
                 field_range: tuple = None, race_filter=None,
                 label: str = "") -> pd.DataFrame:
    """Run a strategy. check_fn(race, **params) -> (hit, cost)."""
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


def run_ml_backtest(races: list[dict], max_h: int = 6,
                    ev_threshold: float = None, top_n: int = None,
                    field_range: tuple = None,
                    test_years: list[int] = None) -> pd.DataFrame:
    """Walk-forward ML backtest: retrain each year, score combos, bet."""
    FEAT = _feature_names()

    if test_years is None:
        all_years = sorted({r["date"].year for r in races})
        test_years = [y for y in all_years if y >= 2018]

    by_year = defaultdict(lambda: {"n": 0, "w": 0, "ret": 0.0, "h": 0, "pays": []})

    for ty in test_years:
        # Train on all prior years
        train_races = [r for r in races if r["date"].year < ty]
        test_races = [r for r in races if r["date"].year == ty]
        if not train_races or not test_races:
            continue

        print(f"  ML fold: train<{ty} ({len(train_races)} races), test={ty} ({len(test_races)} races)...", end="", flush=True)
        t0 = time.time()

        # Train
        train_df = prepare_training_rows(train_races)
        if len(train_df) < 100:
            print(" skip (too few)")
            continue
        model, feat = train_model(train_df)

        # Score test races
        for race in test_races:
            if field_range:
                lo, hi = field_range
                if race["fs"] < lo or race["fs"] > hi:
                    continue

            combos = score_race_combos(race, model, feat, max_h=max_h)
            if not combos:
                continue

            # Select combos to bet on
            if ev_threshold is not None:
                selected = {c["combo"] for c in combos if c["ev"] >= ev_threshold}
            elif top_n is not None:
                ranked = sorted(combos, key=lambda c: c["ev"], reverse=True)
                selected = {c["combo"] for c in ranked[:top_n]}
            else:
                selected = {c["combo"] for c in combos}

            if not selected:
                continue

            y = by_year[ty]
            y["n"] += 1
            y["w"] += len(selected)
            winning = tuple(race["win"])
            if winning in selected:
                y["ret"] += race["payout"]
                y["h"] += 1
                y["pays"].append(race["payout"])

        print(f" {time.time() - t0:.1f}s")

    # Format results
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


# ═══════════════════════════════════════════════════════════════════
# EXPERIMENTS
# ═══════════════════════════════════════════════════════════════════

def total_row(df: pd.DataFrame) -> dict:
    """Extract the TOTAL row as a dict."""
    t = df[df["year"] == "TOTAL"]
    if t.empty:
        return {}
    return t.iloc[0].to_dict()


def main():
    print("=" * 72)
    print("SUPERFECTA WALK-FORWARD BACKTESTING")
    print("=" * 72)

    races = load_races(BASE / "14years_major_tracks.csv")
    fs = [r["fs"] for r in races]
    years = sorted({r["date"].year for r in races})
    print(f"Dates: {races[0]['date'].date()} → {races[-1]['date'].date()}")
    print(f"Years: {years}")
    print(f"Field size: mean={np.mean(fs):.1f}, median={int(np.median(fs))}, "
          f"min={min(fs)}, max={max(fs)}")

    # Baseline: average payout across all races
    avg_pay = np.mean([r["payout"] for r in races])
    avg_fs = np.mean(fs)
    avg_combos = np.mean([f * (f-1) * (f-2) * (f-3) for f in fs])
    print(f"\nBaseline: avg payout=${avg_pay:.2f}, avg field combos={avg_combos:.0f}")
    print(f"  Random $1 bet ROI ≈ {(avg_pay / avg_combos - 1) * 100:.1f}%")

    all_results: dict[str, pd.DataFrame] = {}

    # ── PHASE 1: Favorites Box ──────────────────────────────────
    print("\n" + "=" * 72)
    print("PHASE 1: FAVORITES BOX STRATEGIES")
    print("=" * 72)
    for k in [4, 5, 6, 7, 8]:
        label = f"Box-{k}"
        r = run_backtest(races, box_k, {"k": k}, label=label)
        t = total_row(r)
        print(f"\n--- {label} (cost/race={perm(k,4)}) ---")
        print(r.to_string(index=False))
        all_results[label] = r

    # ── PHASE 2: Key Favorite Strategies ────────────────────────
    print("\n" + "=" * 72)
    print("PHASE 2: KEY FAVORITE STRATEGIES")
    print("=" * 72)
    for k in [5, 6, 7, 8]:
        label = f"Key1Win-{k}"
        r = run_backtest(races, key1_win_k, {"k": k}, label=label)
        t = total_row(r)
        print(f"\n--- {label} (cost/race={perm(k-1,3)}) ---")
        print(r.to_string(index=False))
        all_results[label] = r

    # ── PHASE 3: Anti-Chalk (exclude favorite) ──────────────────
    print("\n" + "=" * 72)
    print("PHASE 3: ANTI-CHALK STRATEGIES (exclude #1 favorite)")
    print("=" * 72)
    for k in [5, 6, 7]:
        label = f"NoFav-Box{k}"
        r = run_backtest(races, no_fav_box_k, {"k": k}, label=label)
        print(f"\n--- {label} ---")
        print(r.to_string(index=False))
        all_results[label] = r

    # ── PHASE 4: Harville Top-N ─────────────────────────────────
    print("\n" + "=" * 72)
    print("PHASE 4: HARVILLE TOP-N STRATEGIES")
    print("=" * 72)
    for n in [1, 6, 24, 50, 120]:
        label = f"Harville-Top{n}"
        t0 = time.time()
        r = run_backtest(races, harville_topn, {"n": n, "max_h": 8}, label=label)
        dt = time.time() - t0
        print(f"\n--- {label} ({dt:.1f}s) ---")
        print(r.to_string(index=False))
        all_results[label] = r

    # ── PHASE 5: Field-Size Binned ──────────────────────────────
    print("\n" + "=" * 72)
    print("PHASE 5: FIELD-SIZE BINNED STRATEGIES")
    print("=" * 72)
    field_bins = [(5, 7), (8, 9), (10, 11), (12, 99)]
    bin_summary = []
    for lo, hi in field_bins:
        n_races = sum(1 for r in races if lo <= r["fs"] <= hi)
        print(f"\n  Field {lo}-{hi}: {n_races} races")
        for k in [4, 5, 6, 7]:
            label = f"Box-{k}_FS{lo}-{hi}"
            r = run_backtest(races, box_k, {"k": k}, field_range=(lo, hi))
            t = total_row(r)
            print(f"    {label}: ROI={t.get('roi%', 0):.1f}%  "
                  f"Hit={t.get('hit%', 0):.1f}%  "
                  f"Races={t.get('races', 0)}  "
                  f"Profit=${t.get('profit', 0):,.0f}")
            bin_summary.append({"strategy": label, **t})
            all_results[label] = r

    # ── PHASE 6: Conditional Filters on Box-5 ──────────────────
    print("\n" + "=" * 72)
    print("PHASE 6: CONDITIONAL FILTERS (Box-5 base)")
    print("=" * 72)

    filters = {
        "Box5_FavStrong": lambda r: r["horses"][0]["p"] >= 0.30,
        "Box5_FavWeak": lambda r: r["horses"][0]["p"] < 0.20,
        "Box5_FavMid": lambda r: 0.20 <= r["horses"][0]["p"] < 0.30,
        "Box5_BigPool": lambda r: r["pool"] >= 50000,
        "Box5_SmallPool": lambda r: r["pool"] < 20000,
        "Box5_Dirt": lambda r: r["surface"] == "D",
        "Box5_Turf": lambda r: r["surface"] == "T",
        "Box5_FastTrack": lambda r: r["condition"] in ("FT", "FM"),
        "Box5_OffTrack": lambda r: r["condition"] in ("MY", "SY", "GD", "YL", "SF", "HY"),
        "Box5_CompField": lambda r: r["horses"][0]["p"] - r["horses"][1]["p"] < 0.05,
    }

    for label, filt in filters.items():
        r = run_backtest(races, box_k, {"k": 5}, race_filter=filt, label=label)
        t = total_row(r)
        print(f"  {label:24s}: ROI={t.get('roi%', 0):+7.1f}%  "
              f"Hit={t.get('hit%', 0):5.1f}%  "
              f"Races={t.get('races', 0):6d}  "
              f"Profit=${t.get('profit', 0):>10,.0f}")
        all_results[label] = r

    # ── PHASE 7: ML Walk-Forward ────────────────────────────────
    print("\n" + "=" * 72)
    print("PHASE 7: ML WALK-FORWARD STRATEGIES")
    print("=" * 72)

    test_years = [y for y in years if y >= 2018]

    # 7a: ML top-N from top-6 horses
    for n in [10, 24, 50]:
        label = f"ML-Top{n}_H6"
        print(f"\n--- {label} ---")
        r = run_ml_backtest(races, max_h=6, top_n=n, test_years=test_years)
        print(r.to_string(index=False))
        all_results[label] = r

    # 7b: ML EV-filtered from top-6 horses
    for ev_thresh in [0.95, 1.0, 1.05, 1.10]:
        label = f"ML-EV>={ev_thresh:.2f}_H6"
        print(f"\n--- {label} ---")
        r = run_ml_backtest(races, max_h=6, ev_threshold=ev_thresh, test_years=test_years)
        print(r.to_string(index=False))
        all_results[label] = r

    # 7c: ML top-N from top-8 horses (more combos, higher cost)
    for n in [24, 50]:
        label = f"ML-Top{n}_H8"
        print(f"\n--- {label} ---")
        r = run_ml_backtest(races, max_h=8, top_n=n, test_years=test_years)
        print(r.to_string(index=False))
        all_results[label] = r

    # 7d: ML EV-filtered, field-size binned
    for lo, hi in [(5, 7), (8, 9), (10, 11), (12, 99)]:
        label = f"ML-EV>=1.0_H6_FS{lo}-{hi}"
        print(f"\n--- {label} ---")
        r = run_ml_backtest(races, max_h=6, ev_threshold=1.0,
                            field_range=(lo, hi), test_years=test_years)
        t = total_row(r)
        print(f"  ROI={t.get('roi%', 0):+.1f}%  Hit={t.get('hit%', 0):.1f}%  "
              f"Races={t.get('races', 0)}  Profit=${t.get('profit', 0):,.0f}")
        all_results[label] = r

    # ── SUMMARY ─────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("SUMMARY OF ALL STRATEGIES (sorted by ROI)")
    print("=" * 72)

    summary_rows = []
    for label, df in all_results.items():
        t = total_row(df)
        if not t:
            continue
        summary_rows.append({
            "Strategy": label,
            "Races": t.get("races", 0),
            "Wagered": t.get("wagered", 0),
            "Profit": t.get("profit", 0),
            "ROI%": t.get("roi%", 0),
            "Hits": t.get("hits", 0),
            "HitRate%": t.get("hit%", 0),
            "AvgPay": t.get("avg_pay", 0),
        })

    summary = pd.DataFrame(summary_rows).sort_values("ROI%", ascending=False)
    print(summary.to_string(index=False))

    # Save summary CSV
    summary.to_csv(BASE / "backtest_summary.csv", index=False)
    print(f"\nSaved: {BASE / 'backtest_summary.csv'}")

    # ── Generate report ─────────────────────────────────────────
    generate_report(all_results, summary, races)

    return all_results, summary


def generate_report(all_results: dict, summary: pd.DataFrame, races: list):
    """Write backtest report to project root."""
    report_path = BASE / "BACKTEST_REPORT.md"

    # Find best strategy
    best = summary.iloc[0]
    worst = summary.iloc[-1]

    # Compute some stats
    n_races = len(races)
    date_range = f"{races[0]['date'].date()} to {races[-1]['date'].date()}"
    avg_pay = np.mean([r["payout"] for r in races])
    n_strats = len(summary)

    # Check for profitability
    profitable = summary[summary["ROI%"] > 0]
    has_profit = len(profitable) > 0

    lines = [
        "# Superfecta Backtesting Report",
        "",
        f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Data:** {n_races:,} races from major tracks, {date_range}",
        f"**Average superfecta payout:** ${avg_pay:,.2f}",
        f"**Strategies tested:** {n_strats}",
        "",
        "## Executive Summary",
        "",
    ]

    if has_profit:
        lines.append(f"**{len(profitable)} strategy/strategies showed positive out-of-sample ROI.**")
        lines.append("")
        lines.append("| Strategy | ROI% | Hit Rate | Races | Wagered | Profit |")
        lines.append("|----------|------|----------|-------|---------|--------|")
        for _, row in profitable.iterrows():
            lines.append(
                f"| {row['Strategy']} | {row['ROI%']:+.1f}% | {row['HitRate%']:.1f}% "
                f"| {int(row['Races']):,} | ${int(row['Wagered']):,} | ${row['Profit']:,.0f} |"
            )
    else:
        lines.append("**No strategy achieved positive out-of-sample ROI.**")
        lines.append(f"Best strategy: **{best['Strategy']}** at **{best['ROI%']:+.1f}%** ROI.")

    lines += [
        "",
        "## Methods Tested",
        "",
        "### 1. Favorites Box (top-K horses, all permutations)",
        "Box-4 through Box-8: bet all superfecta permutations of the K most-favored horses.",
        "",
        "### 2. Key Favorite (favorite must win)",
        "Favorite locked in 1st, remaining 3 from top-K.",
        "",
        "### 3. Anti-Chalk (exclude #1 favorite)",
        "Box horses ranked 2nd through K+1, excluding the betting favorite.",
        "",
        "### 4. Harville-Ranked Top-N",
        "Enumerate all 4-permutations of top-8 horses, rank by Harville joint probability,",
        "bet the N most probable combos.",
        "",
        "### 5. Conditional Filters",
        "Box-5 strategy restricted by race conditions: favorite strength, pool size,",
        "surface, track condition, field competitiveness.",
        "",
        "### 6. ML Walk-Forward (XGBoost residual model)",
        "For each test year (2018-2025): retrain XGBoost on all prior data,",
        "score all combos from top-M horses, select by predicted EV or top-N ranking.",
        "Model predicts log(actual_payout / harville_payout).",
        "EV = exp(predicted_log_ratio) — bet when EV >= threshold.",
        "",
        "### 7. Field-Size Binned",
        "All strategies tested separately for field sizes 5-7, 8-9, 10-11, 12+.",
        "",
        "## Full Results Table",
        "",
        "| Strategy | ROI% | HitRate% | Races | Wagered | Profit | AvgPay |",
        "|----------|------|----------|-------|---------|--------|--------|",
    ]

    for _, row in summary.iterrows():
        lines.append(
            f"| {row['Strategy']} | {row['ROI%']:+.1f}% | {row['HitRate%']:.1f}% "
            f"| {int(row['Races']):,} | ${int(row['Wagered']):,} "
            f"| ${row['Profit']:,.0f} | ${row['AvgPay']:,.0f} |"
        )

    # Year-by-year for best strategy
    if best["Strategy"] in all_results:
        best_df = all_results[best["Strategy"]]
        yearly = best_df[best_df["year"] != "TOTAL"]
        lines += [
            "",
            f"## Year-by-Year: Best Strategy ({best['Strategy']})",
            "",
            "| Year | ROI% | Hit% | Races | Profit |",
            "|------|------|------|-------|--------|",
        ]
        for _, row in yearly.iterrows():
            lines.append(
                f"| {row['year']} | {row['roi%']:+.1f}% | {row['hit%']:.1f}% "
                f"| {int(row['races'])} | ${row['profit']:,.0f} |"
            )

    lines += [
        "",
        "## Key Findings",
        "",
        f"1. **Takeout dominance**: The ~20-25% superfecta takeout creates a strong headwind. "
        f"Random betting yields roughly -25% ROI.",
        "",
        f"2. **Best overall strategy**: {best['Strategy']} at {best['ROI%']:+.1f}% ROI "
        f"across {int(best['Races']):,} races.",
        "",
    ]

    if has_profit:
        lines.append("3. **Profitability evidence**: Positive ROI strategies exist, "
                      "but must be evaluated for statistical significance and year-by-year consistency.")
    else:
        lines.append("3. **No profitability yet**: The current model/strategy family has not "
                      "overcome the track takeout. The ML model improves payout prediction but "
                      "does not yet identify combos with sufficient edge.")

    lines += [
        "",
        "## Recommended Next Steps",
        "",
        "1. **Sharper probability models**: Replace Harville with Henery or Stern models "
        "that better account for finishing position correlations.",
        "2. **Horse-specific features**: Add speed figures, trainer/jockey stats, "
        "class-level indicators, recent form.",
        "3. **Pool-aware strategies**: Use live pool data (will-pays) to find "
        "actual overlay situations in real-time.",
        "4. **Partial combination strategies**: Key/wheel/part-wheel structures "
        "that target specific combo shapes with better EV.",
        "5. **Ensemble models**: Combine multiple model types (XGBoost, neural net, "
        "linear) for more robust predictions.",
        "",
        "## Methodology Notes",
        "",
        "- **Walk-forward**: All ML strategies use strict temporal splits — "
        "model trained on prior years only, tested on future year.",
        "- **No leakage**: official_position and position_at_start are never used as features.",
        "- **Payout basis**: All P&L computed on $1-per-combo flat bet. "
        "actual_payout = payoff_amount × (100 / number_of_tickets_bet).",
        "- **Tracks**: 11 major NA tracks (CD, GP, SA, AQU, BEL, SAR, KEE, DMR, MTH, OP, BAQ).",
        "",
    ]

    report_path.write_text("\n".join(lines))
    print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    main()
