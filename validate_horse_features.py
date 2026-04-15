#!/usr/bin/env python3
"""
validate_horse_features.py

Compare XGBoost payout-residual model performance:
  - Baseline: race-level features only (current pipeline)
  - Enriched: race-level features + horse-history features

Uses the same chronological train/test split and hyperparameters
as the existing train_test_residual.py pipeline.

Output: prints comparison table and saves validate_horse_features_results.json
"""

from __future__ import annotations

import json
import time
from math import log
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb


# ── Helpers from existing pipeline ──────────────────────────────────

def safe_float(value, default=np.nan):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if np.isfinite(result) else default


def safe_str(value, default=""):
    if pd.isna(value):
        return default
    return str(value).strip()


def moneyline_to_prob(odds: float) -> float:
    odds = safe_float(odds)
    if not np.isfinite(odds):
        return np.nan
    if odds > 0:
        return 100.0 / (odds + 100.0)
    else:
        return (-odds) / (-odds + 100.0)


def harville_expected_payout(p1, p2, p3, p4):
    d1 = 1 - p1
    d2 = 1 - p1 - p2
    d3 = 1 - p1 - p2 - p3
    if d1 <= 0 or d2 <= 0 or d3 <= 0:
        return np.nan
    jp = p1 * (p2 / d1) * (p3 / d2) * (p4 / d3)
    if jp <= 0:
        return np.nan
    return 1.0 / jp


# ── Load and pivot to race level (extended with winner reg numbers) ─

def load_and_pivot_extended(csv_path: str) -> pd.DataFrame:
    """
    Load horse-level CSV and create race-level rows with superfecta outcomes.
    Also captures registration_number for each of the 4 winning positions.
    """
    print("Loading and processing CSV data ...")
    df = pd.read_csv(
        csv_path,
        parse_dates=["race_date"],
        dtype={"post_time": str, "program_number": str, "registration_number": str},
    )

    # Clean post_time
    df["post_time"] = df["post_time"].fillna("").str.extract(r"(\d+)$")[0].str[-4:]
    df["post_time"] = pd.to_datetime(df["post_time"], format="%H%M", errors="coerce")

    # Remove scratched
    df = df[df["scratch_indicator"].fillna("N") != "Y"]

    # Races with winning numbers
    races_with_winners = (
        df[df["winning_numbers"].notna()]
          [["track_id", "race_date", "race_number"]]
          .drop_duplicates()
    )
    keep_races = set(zip(
        races_with_winners.track_id,
        races_with_winners.race_date,
        races_with_winners.race_number,
    ))

    processed = []
    skipped = 0

    for (track, date, race_num), grp in df.groupby(
        ["track_id", "race_date", "race_number"]
    ):
        if (track, date, race_num) not in keep_races:
            continue

        winning_rows = grp[grp["winning_numbers"].notna()]
        if winning_rows.empty:
            skipped += 1
            continue

        winner_info = winning_rows.iloc[0]
        winning_programs = [
            safe_str(x) for x in str(winner_info["winning_numbers"]).split("-")
            if safe_str(x)
        ]
        if len(winning_programs) != 4:
            skipped += 1
            continue

        # Build horse lookup for this race
        all_horses = []
        for _, horse in grp.iterrows():
            odds = safe_float(horse.get("odds"))
            if np.isfinite(odds):
                raw_prob = moneyline_to_prob(odds)
                if not np.isfinite(raw_prob) or raw_prob < 0:
                    continue
                all_horses.append({
                    "program": safe_str(horse["program_number"]),
                    "registration_number": safe_str(horse["registration_number"]),
                    "raw_prob": raw_prob,
                    "odds": odds,
                })

        if len(all_horses) < 4:
            skipped += 1
            continue

        total_raw = sum(h["raw_prob"] for h in all_horses)
        if not np.isfinite(total_raw) or total_raw <= 0:
            skipped += 1
            continue
        for h in all_horses:
            h["norm_prob"] = h["raw_prob"] / total_raw

        prog_to_prob = {h["program"]: h["norm_prob"] for h in all_horses}
        prog_to_odds = {h["program"]: h["odds"] for h in all_horses}
        prog_to_reg = {h["program"]: h["registration_number"] for h in all_horses}

        winner_probs, winner_odds, winner_regs = [], [], []
        missing = False
        for prog in winning_programs:
            prog = prog.strip()
            if prog in prog_to_prob:
                winner_probs.append(prog_to_prob[prog])
                winner_odds.append(prog_to_odds[prog])
                winner_regs.append(prog_to_reg[prog])
            else:
                missing = True
                break
        if missing:
            skipped += 1
            continue

        payoff = safe_float(winner_info.get("payoff_amount"))
        total_pool = safe_float(winner_info.get("total_pool"), default=0.0)
        tickets = safe_float(winner_info.get("number_of_tickets_bet"), default=np.nan)

        if pd.isna(payoff) or payoff <= 0 or pd.isna(tickets) or tickets <= 0:
            skipped += 1
            continue

        field_size = len(grp)
        avg_odds = pd.to_numeric(grp["odds"], errors="coerce").mean()
        odds_std = pd.to_numeric(grp["odds"], errors="coerce").std()
        first_row = grp.iloc[0]

        processed.append({
            "track_id": track,
            "race_date": date,
            "race_number": race_num,
            # Winner odds
            "odds1": winner_odds[0], "odds2": winner_odds[1],
            "odds3": winner_odds[2], "odds4": winner_odds[3],
            # Winner probabilities
            "norm_prob1": winner_probs[0], "norm_prob2": winner_probs[1],
            "norm_prob3": winner_probs[2], "norm_prob4": winner_probs[3],
            # Winner registration numbers (new)
            "reg1": winner_regs[0], "reg2": winner_regs[1],
            "reg3": winner_regs[2], "reg4": winner_regs[3],
            # Winner program numbers (new, for join key)
            "prog1": winning_programs[0], "prog2": winning_programs[1],
            "prog3": winning_programs[2], "prog4": winning_programs[3],
            # Race characteristics
            "distance_id": safe_float(first_row.get("distance_id"), default=0.0),
            "surface": safe_str(first_row.get("surface"), default="UNKNOWN"),
            "course_type": safe_str(first_row.get("course_type"), default="UNKNOWN"),
            "purse_usa": safe_float(first_row.get("purse_usa"), default=0.0),
            "post_hour": (first_row["post_time"].hour
                          if pd.notna(first_row["post_time"]) else 12),
            "track_condition": safe_str(first_row.get("track_condition"), default="UNKNOWN"),
            "number_of_runners": safe_float(first_row.get("number_of_runners"), default=field_size),
            "field_size": field_size,
            "avg_field_odds": avg_odds,
            "odds_std": odds_std,
            # Payout
            "payoff_amount": float(payoff),
            "total_pool": float(total_pool),
            "num_tickets": float(tickets),
            "raw_prob_sum_all_horses": total_raw,
        })

    print(f"  Processed {len(processed):,} valid races (skipped {skipped:,})")
    return pd.DataFrame(processed)


# ── Feature engineering ─────────────────────────────────────────────

def compute_baseline_features(df: pd.DataFrame):
    """Race-level features matching the existing pipeline."""
    df = df.copy()

    for i in range(1, 5):
        df[f"prob{i}"] = df[f"norm_prob{i}"]
        df[f"logit{i}"] = df[f"prob{i}"].apply(
            lambda p: log(p / (1 - p)) if 0 < p < 1 else 0.0
        )

    # Harville payout
    df["harville_payout"] = [
        harville_expected_payout(r.prob1, r.prob2, r.prob3, r.prob4)
        for _, r in df.iterrows()
    ]

    # Actual payout normalized to $1
    df["multiplier"] = np.where(df["num_tickets"] > 0, 100.0 / df["num_tickets"], np.nan)
    df["actual_payout"] = df["payoff_amount"] * df["multiplier"]

    # Target
    valid = (
        df["harville_payout"].notna()
        & (df["harville_payout"] > 0)
        & (df["num_tickets"] > 0)
        & (df["actual_payout"] > 0)
    )
    df = df[valid].copy()
    df["log_ratio"] = np.log(df["actual_payout"] / df["harville_payout"])

    # Remove 3-sigma outliers
    mu, sigma = df["log_ratio"].mean(), df["log_ratio"].std()
    df = df[(df["log_ratio"] >= mu - 3 * sigma) & (df["log_ratio"] <= mu + 3 * sigma)].copy()

    # Derived features (same as existing pipeline)
    df["favorite_odds"] = df[["odds1", "odds2", "odds3", "odds4"]].min(axis=1)
    df["longshot_odds"] = df[["odds1", "odds2", "odds3", "odds4"]].max(axis=1)
    df["odds_range"] = df["longshot_odds"] - df["favorite_odds"]
    df["prob_product"] = df["prob1"] * df["prob2"] * df["prob3"] * df["prob4"]
    df["prob_sum"] = df["prob1"] + df["prob2"] + df["prob3"] + df["prob4"]
    df["min_prob"] = df[["prob1", "prob2", "prob3", "prob4"]].min(axis=1)
    df["max_prob"] = df[["prob1", "prob2", "prob3", "prob4"]].max(axis=1)
    df["prob_variance"] = np.var(
        [df[f"prob{i}"] for i in range(1, 5)], axis=0
    )
    df["prob_entropy"] = -sum(
        df[f"prob{i}"] * np.log(df[f"prob{i}"] + 1e-10) for i in range(1, 5)
    )
    df["pool_per_runner"] = df["total_pool"] / df["number_of_runners"]
    df["purse_per_runner"] = df["purse_usa"] / df["number_of_runners"]
    df["harville_log"] = np.log(df["harville_payout"])

    # Categoricals
    cat_cols = ["surface", "course_type", "track_condition"]
    dummies = pd.get_dummies(df[cat_cols], prefix=cat_cols, dummy_na=True)
    df = pd.concat([df, dummies], axis=1)

    baseline_features = (
        [f"logit{i}" for i in range(1, 5)]
        + [f"prob{i}" for i in range(1, 5)]
        + ["number_of_runners", "field_size", "purse_usa", "distance_id",
           "post_hour", "total_pool", "avg_field_odds", "odds_std"]
        + ["favorite_odds", "longshot_odds", "odds_range", "prob_product",
           "prob_sum", "prob_entropy", "min_prob", "max_prob", "pool_per_runner",
           "purse_per_runner", "harville_log", "prob_variance"]
        + list(dummies.columns)
    )

    df[baseline_features] = df[baseline_features].fillna(0)

    return df, baseline_features


def attach_horse_features(
    race_df: pd.DataFrame, horse_features_path: str
) -> tuple[pd.DataFrame, list[str]]:
    """
    Merge horse-history features for each of the 4 winning positions.
    Returns the enriched dataframe and the list of new feature column names.
    """
    from build_horse_features import HORSE_FEATURE_COLS

    print(f"Loading horse features from {horse_features_path} ...")
    hf = pd.read_csv(
        horse_features_path,
        parse_dates=["race_date"],
        dtype={"program_number": str, "registration_number": str},
    )

    # Create join key and deduplicate (keep first occurrence per key)
    hf["_join_key"] = (
        hf["registration_number"].astype(str) + "|"
        + hf["track_id"].astype(str) + "|"
        + hf["race_date"].astype(str) + "|"
        + hf["race_number"].astype(str)
    )
    hf = hf.drop_duplicates(subset="_join_key", keep="first")
    hf_lookup = hf.set_index("_join_key")[HORSE_FEATURE_COLS]

    new_cols = []
    df = race_df.copy()

    for pos in range(1, 5):
        prefix = f"w{pos}_"
        # Build join key for this winner
        jk = (
            df[f"reg{pos}"].astype(str) + "|"
            + df["track_id"].astype(str) + "|"
            + df["race_date"].astype(str) + "|"
            + df["race_number"].astype(str)
        )

        matched = hf_lookup.reindex(jk.values)
        for col in HORSE_FEATURE_COLS:
            new_name = f"{prefix}{col}"
            df[new_name] = matched[col].values
            new_cols.append(new_name)

    # Aggregate features across the 4 winners
    for col in HORSE_FEATURE_COLS:
        w_cols = [f"w{i}_{col}" for i in range(1, 5)]
        sub = df[w_cols]
        df[f"avg_{col}"] = sub.mean(axis=1)
        df[f"min_{col}"] = sub.min(axis=1)
        df[f"max_{col}"] = sub.max(axis=1)
        new_cols.extend([f"avg_{col}", f"min_{col}", f"max_{col}"])

    # Count first-time starters among the 4 winners
    df["n_debut_winners"] = sum(
        (df[f"w{i}_n_prior_starts"] == 0).astype(float) for i in range(1, 5)
    )
    new_cols.append("n_debut_winners")

    match_rate = df["w1_n_prior_starts"].notna().mean()
    print(f"  Horse feature match rate: {match_rate:.1%}")
    print(f"  Added {len(new_cols)} horse-history features")

    return df, new_cols


# ── Training ────────────────────────────────────────────────────────

XGBOOST_PARAMS = {
    "max_depth": 6,
    "eta": 0.058902720515650556,
    "subsample": 0.8587382809509695,
    "colsample_bytree": 0.7138183639990917,
    "reg_alpha": 1.6223569131405515,
    "reg_lambda": 2.833424833580529,
    "gamma": 0.28154211912969035,
    "min_child_weight": 10,
    "objective": "reg:squarederror",
    "eval_metric": "rmse",
    "seed": 42,
    "tree_method": "hist",
    "nthread": 4,
}


def train_and_eval(
    df: pd.DataFrame,
    feature_cols: list[str],
    label: str,
) -> dict:
    """Train XGBoost with chronological split and return test metrics."""
    # Chronological sort
    df_sorted = df.sort_values(
        ["race_date", "track_id", "race_number"], kind="mergesort"
    ).reset_index(drop=True)

    split_idx = int(len(df_sorted) * 0.75)
    split_idx = max(1, min(split_idx, len(df_sorted) - 1))

    df_train = df_sorted.iloc[:split_idx]
    df_test = df_sorted.iloc[split_idx:]

    X_train = df_train[feature_cols].fillna(0).values
    y_train = df_train["log_ratio"].values
    X_test = df_test[feature_cols].fillna(0).values
    y_test = df_test["log_ratio"].values

    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=feature_cols)
    dtest = xgb.DMatrix(X_test, label=y_test, feature_names=feature_cols)

    model = xgb.train(
        params=XGBOOST_PARAMS,
        dtrain=dtrain,
        num_boost_round=595,
        evals=[(dtrain, "train"), (dtest, "test")],
        early_stopping_rounds=30,
        verbose_eval=50,
    )

    y_pred = model.predict(dtest)

    # Metrics
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    corr, _ = pearsonr(y_test, y_pred)

    # Payout-level metrics
    df_test = df_test.copy()
    df_test["predicted_log_ratio"] = y_pred
    df_test["corrected_payout"] = df_test["harville_payout"] * np.exp(y_pred)

    harv_rmse = np.sqrt(mean_squared_error(
        df_test["actual_payout"], df_test["harville_payout"]
    ))
    corr_rmse = np.sqrt(mean_squared_error(
        df_test["actual_payout"], df_test["corrected_payout"]
    ))
    harv_mae = mean_absolute_error(
        df_test["actual_payout"], df_test["harville_payout"]
    )
    corr_mae = mean_absolute_error(
        df_test["actual_payout"], df_test["corrected_payout"]
    )

    # Feature importance (top 10)
    importance = model.get_score(importance_type="gain")
    top_feats = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:15]

    metrics = {
        "label": label,
        "n_features": len(feature_cols),
        "train_size": len(df_train),
        "test_size": len(df_test),
        "train_end": str(df_train["race_date"].max().date()),
        "test_start": str(df_test["race_date"].min().date()),
        "log_ratio_rmse": float(rmse),
        "log_ratio_mae": float(mae),
        "log_ratio_r2": float(r2),
        "log_ratio_corr": float(corr),
        "payout_harville_rmse": float(harv_rmse),
        "payout_corrected_rmse": float(corr_rmse),
        "payout_rmse_improvement_pct": float((harv_rmse - corr_rmse) / harv_rmse * 100),
        "payout_harville_mae": float(harv_mae),
        "payout_corrected_mae": float(corr_mae),
        "payout_mae_improvement_pct": float((harv_mae - corr_mae) / harv_mae * 100),
        "top_features": [(f, float(s)) for f, s in top_feats],
    }

    return metrics


# ── Main ────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate horse-history features vs baseline"
    )
    parser.add_argument("--csv", required=True, help="Raw horse-level CSV")
    parser.add_argument(
        "--horse-features",
        required=True,
        help="Horse features cache CSV from build_horse_features.py",
    )
    parser.add_argument(
        "--output",
        default="validate_horse_features_results.json",
        help="Output JSON with comparison results",
    )
    args = parser.parse_args()

    t_total = time.time()

    # 1. Load and pivot
    race_df = load_and_pivot_extended(args.csv)
    print(f"  {len(race_df):,} race-level rows")

    # 2. Compute baseline features
    print("\n--- Computing baseline features ---")
    df_base, base_feats = compute_baseline_features(race_df)
    print(f"  {len(base_feats)} baseline features, {len(df_base):,} races")

    # 3. Attach horse features
    print("\n--- Attaching horse-history features ---")
    df_enriched, horse_feats = attach_horse_features(df_base, args.horse_features)
    all_feats = base_feats + horse_feats
    print(f"  {len(all_feats)} total features ({len(horse_feats)} horse-history)")

    # 4. Train baseline
    print("\n" + "=" * 60)
    print("TRAINING BASELINE MODEL (race features only)")
    print("=" * 60)
    baseline_metrics = train_and_eval(df_base, base_feats, "baseline")

    # 5. Train enriched
    print("\n" + "=" * 60)
    print("TRAINING ENRICHED MODEL (race + horse-history features)")
    print("=" * 60)
    enriched_metrics = train_and_eval(df_enriched, all_feats, "enriched")

    # 6. Comparison
    print("\n" + "=" * 60)
    print("COMPARISON: BASELINE vs ENRICHED")
    print("=" * 60)

    def fmt_delta(base_val, enr_val, lower_is_better=True):
        delta = enr_val - base_val
        pct = delta / abs(base_val) * 100 if base_val != 0 else 0
        improved = (delta < 0) if lower_is_better else (delta > 0)
        arrow = "v" if improved else "^"
        return f"{delta:+.4f} ({pct:+.1f}%) {arrow}"

    print(f"\n{'Metric':<30} {'Baseline':>12} {'Enriched':>12} {'Delta':>25}")
    print("-" * 82)

    rows = [
        ("Log-ratio RMSE", "log_ratio_rmse", True),
        ("Log-ratio MAE", "log_ratio_mae", True),
        ("Log-ratio R²", "log_ratio_r2", False),
        ("Log-ratio Correlation", "log_ratio_corr", False),
        ("Payout RMSE (Harville)", "payout_harville_rmse", True),
        ("Payout RMSE (Corrected)", "payout_corrected_rmse", True),
        ("Payout RMSE Improvement %", "payout_rmse_improvement_pct", False),
        ("Payout MAE (Corrected)", "payout_corrected_mae", True),
        ("Payout MAE Improvement %", "payout_mae_improvement_pct", False),
    ]

    for label, key, lib in rows:
        bv = baseline_metrics[key]
        ev = enriched_metrics[key]
        print(f"{label:<30} {bv:>12.4f} {ev:>12.4f} {fmt_delta(bv, ev, lib):>25}")

    # Top features in enriched model
    print(f"\nTop 15 features (enriched model):")
    for i, (feat, score) in enumerate(enriched_metrics["top_features"]):
        marker = " ** HORSE" if any(
            feat.startswith(p) for p in ["w1_", "w2_", "w3_", "w4_", "avg_", "min_", "max_", "n_debut"]
        ) else ""
        print(f"  {i+1:2d}. {feat:<35} {score:>10.0f}{marker}")

    # 7. Save results
    results = {
        "baseline": baseline_metrics,
        "enriched": enriched_metrics,
        "improvement": {
            "log_ratio_rmse_delta": enriched_metrics["log_ratio_rmse"] - baseline_metrics["log_ratio_rmse"],
            "log_ratio_r2_delta": enriched_metrics["log_ratio_r2"] - baseline_metrics["log_ratio_r2"],
            "payout_rmse_improvement_delta": (
                enriched_metrics["payout_rmse_improvement_pct"]
                - baseline_metrics["payout_rmse_improvement_pct"]
            ),
        },
        "elapsed_seconds": time.time() - t_total,
    }

    out_path = Path(args.output)
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to {out_path}")
    print(f"Total elapsed: {results['elapsed_seconds']:.0f}s")


if __name__ == "__main__":
    main()
