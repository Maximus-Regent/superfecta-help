#!/usr/bin/env python3
"""
build_horse_features.py

Build horse-history features from raw race data using strict lookback
(no data leakage).  Each row gets features computed from that horse's
PRIOR appearances only.

Features produced per horse-race row:
  - n_prior_starts          experience count
  - prior_win_rate          career win rate (prior starts only)
  - prior_top3_rate         career top-3 rate
  - avg_finish_all          career average finish position
  - avg_finish_last5        rolling avg finish over last 5 starts
  - days_since_last         layoff in calendar days
  - avg_prior_purse         class proxy (avg purse of prior races)
  - class_change            current purse minus avg_prior_purse
  - surface_prior_starts    same-surface experience
  - surface_win_rate        same-surface win rate
  - surface_avg_finish      same-surface avg finish
  - distance_prior_starts   same-distance experience
  - distance_win_rate       same-distance win rate
  - distance_avg_finish     same-distance avg finish
  - track_prior_starts      same-track experience
  - track_win_rate          same-track win rate
  - track_avg_finish        same-track avg finish

All rates use shift(1) so the current race is never included.
First-time starters get NaN for rate columns; XGBoost handles these natively.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


HORSE_FEATURE_COLS = [
    "n_prior_starts", "prior_win_rate", "prior_top3_rate",
    "avg_finish_all", "avg_finish_last5", "days_since_last",
    "avg_prior_purse", "class_change",
    "surface_prior_starts", "surface_win_rate", "surface_avg_finish",
    "distance_prior_starts", "distance_win_rate", "distance_avg_finish",
    "track_prior_starts", "track_win_rate", "track_avg_finish",
]

KEY_COLS = [
    "registration_number", "program_number",
    "track_id", "race_date", "race_number",
]


def build_horse_features(
    csv_path: str, output_path: str | None = None
) -> pd.DataFrame:
    """Build historical features for every horse-race combination."""
    print("=== Building Horse History Features ===")
    t0 = time.time()

    print(f"Loading {csv_path} ...")
    df = pd.read_csv(
        csv_path,
        parse_dates=["race_date"],
        dtype={
            "program_number": str,
            "registration_number": str,
            "post_time": str,
        },
    )

    # Remove scratched horses
    n_before = len(df)
    df = df[df["scratch_indicator"].fillna("N") != "Y"].copy()
    print(f"  {n_before:,} rows -> {len(df):,} after removing scratches")

    # Drop rows with missing registration numbers
    df = df[
        df["registration_number"].notna()
        & (df["registration_number"].str.strip() != "")
    ].copy()

    # Coerce numeric columns
    for col in ["odds", "official_position", "purse_usa", "distance_id",
                "number_of_runners"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Sort chronologically within each horse
    df = df.sort_values(
        ["registration_number", "race_date", "race_number"]
    ).reset_index(drop=True)

    n_horses = df["registration_number"].nunique()
    print(f"  {n_horses:,} unique horses")
    print(f"  Date range: {df['race_date'].min().date()} to "
          f"{df['race_date'].max().date()}")

    # ── helper columns ──────────────────────────────────────────────
    df["won"] = (df["official_position"] == 1).astype(float)
    df["top3"] = (df["official_position"] <= 3).astype(float)

    # ── per-horse expanding features (strict lookback via shift) ────
    print("Computing per-horse history features ...")
    t1 = time.time()

    g = df.groupby("registration_number", sort=False)

    # Number of prior starts (0 for debut)
    df["n_prior_starts"] = g.cumcount()

    # Cumulative stats, shifted so current race is excluded
    df["_cw"] = g["won"].cumsum().shift(1, fill_value=0)
    df["_ct"] = g["top3"].cumsum().shift(1, fill_value=0)
    df["_cf"] = g["official_position"].cumsum().shift(1, fill_value=0)

    has_history = df["n_prior_starts"] > 0
    df["prior_win_rate"]  = np.where(has_history, df["_cw"] / df["n_prior_starts"], np.nan)
    df["prior_top3_rate"] = np.where(has_history, df["_ct"] / df["n_prior_starts"], np.nan)
    df["avg_finish_all"]  = np.where(has_history, df["_cf"] / df["n_prior_starts"], np.nan)

    # Recent form: rolling mean of last 5 finishes (shifted)
    df["avg_finish_last5"] = g["official_position"].transform(
        lambda x: x.shift(1).rolling(5, min_periods=1).mean()
    )

    # Days since last start
    df["days_since_last"] = g["race_date"].diff().dt.days

    # Class proxy
    df["_cp"] = g["purse_usa"].cumsum().shift(1, fill_value=0)
    df["avg_prior_purse"] = np.where(has_history, df["_cp"] / df["n_prior_starts"], np.nan)
    df["class_change"] = df["purse_usa"] - df["avg_prior_purse"]

    print(f"  Basic features: {time.time() - t1:.1f}s")

    # ── condition-specific features (surface / distance / track) ────
    t2 = time.time()

    for label, group_cols in [
        ("surface",  ["registration_number", "surface"]),
        ("distance", ["registration_number", "distance_id"]),
        ("track",    ["registration_number", "track_id"]),
    ]:
        gc = df.groupby(group_cols, sort=False)
        starts_col = f"{label}_prior_starts"
        wr_col     = f"{label}_win_rate"
        af_col     = f"{label}_avg_finish"

        df[starts_col] = gc.cumcount()
        cum_w = gc["won"].cumsum().shift(1, fill_value=0)
        cum_f = gc["official_position"].cumsum().shift(1, fill_value=0)

        cond_has = df[starts_col] > 0
        df[wr_col] = np.where(cond_has, cum_w / df[starts_col], np.nan)
        df[af_col] = np.where(cond_has, cum_f / df[starts_col], np.nan)

    print(f"  Condition-specific features: {time.time() - t2:.1f}s")

    # ── select & save ───────────────────────────────────────────────
    result = df[KEY_COLS + HORSE_FEATURE_COLS].copy()

    if output_path:
        out_p = Path(output_path)
        print(f"Saving {len(result):,} rows to {out_p} ...")
        result.to_csv(out_p, index=False)
        size_mb = out_p.stat().st_size / 1e6
        print(f"  Saved ({size_mb:.1f} MB)")

    elapsed = time.time() - t0
    with_history = (result["n_prior_starts"] > 0).sum()
    print(f"\n=== Summary ===")
    print(f"  Total rows:           {len(result):,}")
    print(f"  Rows with history:    {with_history:,} "
          f"({100 * with_history / len(result):.1f}%)")
    print(f"  First-time starters:  {len(result) - with_history:,}")
    print(f"  Total time:           {elapsed:.1f}s")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build horse history features from raw race CSV"
    )
    parser.add_argument("--csv", required=True, help="Path to raw horse-level CSV")
    parser.add_argument(
        "--output",
        default="horse_features_cache.csv",
        help="Output CSV path (default: horse_features_cache.csv)",
    )
    args = parser.parse_args()

    build_horse_features(args.csv, args.output)
