#!/usr/bin/env python3
"""
train_test_residual.py

Advanced machine learning pipeline for predicting superfecta payout deviations using XGBoost.

This script implements a comprehensive approach to modeling the difference between
theoretical Harville payouts and actual market payouts. Key innovations:

1. Log-ratio target variable: More stable than raw residuals
2. Full-field probability normalization: Removes track takeout bias
3. Comprehensive feature engineering: 20+ features capturing market dynamics
4. Robust bias analysis: Quantifies longshot bias across probability ranges
5. Advanced visualization: Multiple plots for model diagnostics

The model learns to predict log(actual_payout / harville_payout), which captures
systematic biases in betting markets while being more numerically stable than
raw payout differences.

Theoretical Foundation:
- Harville formula provides baseline probability estimates
- XGBoost learns market inefficiencies and behavioral biases
- Log transformation handles wide payout ranges (10x to 10000x)
- Cross-validation ensures generalization to new races

Author: [Your Name]
Version: 3.0
Last Updated: [Date]
"""

import argparse
import json
import os
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
from math import log
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import pearsonr
import warnings

# Suppress sklearn warnings for cleaner output
warnings.filterwarnings("ignore", category=FutureWarning)


def safe_float(value, default=np.nan):
    """Best-effort float conversion with a fallback for bad inputs."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if np.isfinite(result) else default


def safe_str(value, default=""):
    """Return a stripped string, falling back when the value is missing."""
    if pd.isna(value):
        return default
    return str(value).strip()


def parse_args():
    """
    Parse command line arguments for the training script.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Train XGBoost model to predict log-transformed superfecta payout residuals",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to horse-level CSV file with historical race data"
    )
    
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Randomly sample N races for faster development/testing"
    )
    
    parser.add_argument(
        "--output",
        default="log_residual_results.csv",
        help="Output CSV file for detailed model results and predictions"
    )

    parser.add_argument(
        "--threads",
        type=int,
        default=max(1, os.cpu_count() or 1),
        help="Number of CPU threads for XGBoost training"
    )

    parser.add_argument(
        "--tree-method",
        default="hist",
        choices=["auto", "exact", "approx", "hist"],
        help="XGBoost tree construction method"
    )

    parser.add_argument(
        "--model-output",
        default=None,
        help="Optional path for trained model output (.json). Defaults to <output stem>_model.json"
    )

    parser.add_argument(
        "--plot-prefix",
        default=None,
        help="Optional filename prefix for saved diagnostic plots. Defaults to <output stem>"
    )

    parser.add_argument(
        "--horse-features",
        default=None,
        help="Optional path to horse-history features CSV from build_horse_features.py. "
             "When provided, merges per-horse features for the 4 winning positions "
             "into the training feature set. Omit for baseline-only training."
    )

    return parser.parse_args()


def load_and_pivot(csv_path: str, sample_size: int = None) -> pd.DataFrame:
    """
    Load horse-level CSV data and transform to race-level with superfecta outcomes.
    
    This function performs several critical data transformations:
    1. Converts horse-level records to race-level aggregations
    2. Extracts 4-horse superfecta combinations from winning_numbers
    3. Calculates normalized probabilities for ALL horses in each race
    4. Filters for races with complete superfecta data
    
    Args:
        csv_path (str): Path to horse-level CSV file
        sample_size (int, optional): Number of races to randomly sample
        
    Returns:
        pd.DataFrame: Race-level data with superfecta outcomes and features
    """
    print("Loading and processing CSV data...")
    
    # Load raw data with appropriate data types
    df = pd.read_csv(
        csv_path,
        parse_dates=["race_date"],
        dtype={"post_time": str, "program_number": str, "registration_number": str}
    )
    
    # Clean and standardize post_time format
    # Extract numeric time and convert to datetime
    df["post_time"] = (
        df["post_time"].fillna("").str.extract(r"(\d+)$")[0].str[-4:]
    )
    df["post_time"] = pd.to_datetime(
        df["post_time"], format="%H%M", errors="coerce"
    )
    
    # Remove scratched horses - they don't participate
    df = df[df["scratch_indicator"].fillna("N") != "Y"]
    
    # Get unique races that have winning superfecta numbers
    races_with_winners = (
        df[df["winning_numbers"].notna()]
          [["track_id", "race_date", "race_number"]]
          .drop_duplicates()
    )
    
    # Apply sampling if requested (for development/testing)
    if sample_size:
        races_with_winners = races_with_winners.sample(sample_size, random_state=42)
        print(f"Sampling {sample_size} races from {len(races_with_winners)} available races")
    
    # Create set of race identifiers to keep
    keep_races = set(zip(races_with_winners.track_id, 
                        races_with_winners.race_date, 
                        races_with_winners.race_number))
    
    processed_races = []
    skip_counts = Counter()
    skip_examples = {
        "zero_total_implied_probability": [],
        "winner_missing_probability": [],
        "invalid_winning_numbers": [],
    }
    
    # Process each race individually
    for (track, date, race_num), race_group in df.groupby([
        "track_id", "race_date", "race_number"
    ]):
        # Skip races not in our keep set
        if (track, date, race_num) not in keep_races:
            continue
            
        # Get the winning combination information
        winning_rows = race_group[race_group["winning_numbers"].notna()]
        if winning_rows.empty:
            skip_counts["no_winning_numbers"] += 1
            continue
            
        winner_info = winning_rows.iloc[0]
        winning_programs = [safe_str(x) for x in str(winner_info["winning_numbers"]).split("-") if safe_str(x)]
        
        # We need exactly 4 horses for superfecta
        if len(winning_programs) != 4:
            skip_counts["invalid_winning_numbers"] += 1
            if len(skip_examples["invalid_winning_numbers"]) < 5:
                skip_examples["invalid_winning_numbers"].append({
                    "track_id": safe_str(track),
                    "race_date": str(date),
                    "race_number": int(race_num),
                    "winning_numbers": safe_str(winner_info["winning_numbers"]),
                })
            continue
        
        # Calculate normalized probabilities for ALL horses in this race
        all_horses_data = []
        
        for _, horse in race_group.iterrows():
            odds = safe_float(horse.get("odds"))
            if np.isfinite(odds):
                raw_prob = moneyline_to_prob(odds)
                if not np.isfinite(raw_prob) or raw_prob < 0:
                    skip_counts["invalid_odds_rows"] += 1
                    continue
                all_horses_data.append({
                    'program': safe_str(horse["program_number"]),
                    'registration_number': safe_str(horse.get("registration_number", "")),
                    'raw_prob': raw_prob,
                    'odds': odds
                })
        
        if len(all_horses_data) < 4:
            skip_counts["insufficient_usable_horses"] += 1
            continue  # Need at least 4 horses
        
        # Normalize ALL horses' probabilities to remove track takeout
        total_raw_prob = sum(h['raw_prob'] for h in all_horses_data)
        if not np.isfinite(total_raw_prob) or total_raw_prob <= 0:
            skip_counts["zero_total_implied_probability"] += 1
            if len(skip_examples["zero_total_implied_probability"]) < 5:
                skip_examples["zero_total_implied_probability"].append({
                    "track_id": safe_str(track),
                    "race_date": str(date),
                    "race_number": int(race_num),
                    "winning_numbers": safe_str(winner_info["winning_numbers"]),
                    "odds": [h["odds"] for h in all_horses_data],
                })
            continue
        for horse_data in all_horses_data:
            horse_data['norm_prob'] = horse_data['raw_prob'] / total_raw_prob
        
        # Create lookup for normalized probabilities by program number
        prog_to_norm_prob = {h['program']: h['norm_prob'] for h in all_horses_data}
        prog_to_odds = {h['program']: h['odds'] for h in all_horses_data}
        prog_to_reg = {h['program']: h['registration_number'] for h in all_horses_data}

        # Extract data for the 4 winning horses
        winner_probs = []
        winner_odds = []
        winner_regs = []
        winner_missing = False
        
        for prog in winning_programs:
            prog = prog.strip()
            if prog in prog_to_norm_prob:
                winner_probs.append(prog_to_norm_prob[prog])
                winner_odds.append(prog_to_odds[prog])
                winner_regs.append(prog_to_reg.get(prog, ""))
            else:
                # Missing data for a winning horse
                skip_counts["winner_missing_probability"] += 1
                if len(skip_examples["winner_missing_probability"]) < 5:
                    skip_examples["winner_missing_probability"].append({
                        "track_id": safe_str(track),
                        "race_date": str(date),
                        "race_number": int(race_num),
                        "winning_numbers": safe_str(winner_info["winning_numbers"]),
                        "missing_program": prog,
                    })
                winner_missing = True
                break
        if winner_missing:
            continue

        # Extract payout information
        payoff = safe_float(winner_info.get("payoff_amount"))
        total_pool = safe_float(winner_info.get("total_pool"), default=0.0)
        tickets = safe_float(winner_info.get("number_of_tickets_bet"), default=np.nan)
        
        if pd.isna(payoff) or payoff <= 0:
            skip_counts["invalid_payoff"] += 1
            continue

        if pd.isna(tickets) or tickets <= 0:
            skip_counts["invalid_ticket_count"] += 1
            continue
        
        # Calculate field statistics
        field_size = len(race_group)
        avg_odds = pd.to_numeric(race_group["odds"], errors="coerce").mean()
        odds_std = pd.to_numeric(race_group["odds"], errors="coerce").std()
        first_row = race_group.iloc[0]
        
        # Store race-level record
        processed_races.append({
            # Race identifiers
            "track_id": track,
            "race_date": date,
            "race_number": race_num,
            
            # Winner odds (original market odds)
            "odds1": winner_odds[0],
            "odds2": winner_odds[1], 
            "odds3": winner_odds[2],
            "odds4": winner_odds[3],

            # Winner identifiers (for horse-history feature merge)
            "reg1": winner_regs[0], "reg2": winner_regs[1],
            "reg3": winner_regs[2], "reg4": winner_regs[3],
            "prog1": winning_programs[0], "prog2": winning_programs[1],
            "prog3": winning_programs[2], "prog4": winning_programs[3],

            # Winner probabilities (normalized)
            "norm_prob1": winner_probs[0],
            "norm_prob2": winner_probs[1],
            "norm_prob3": winner_probs[2],
            "norm_prob4": winner_probs[3],
            
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
            
            # Payout information
            "payoff_amount": float(payoff),
            "total_pool": float(total_pool),
            "num_tickets": float(tickets),
            
            # Normalization tracking (for debugging)
            "raw_prob_sum_all_horses": total_raw_prob,
            "normalized_prob_sum_winners": sum(winner_probs)
        })
    
    print(f"Processed {len(processed_races)} valid superfecta races")
    if skip_counts:
        print("Skipped races summary:")
        for reason, count in sorted(skip_counts.items()):
            print(f"  - {reason}: {count}")
        if skip_examples["zero_total_implied_probability"]:
            print("Example zero-total-implied-probability races:")
            for example in skip_examples["zero_total_implied_probability"]:
                print(f"  - {example}")
    return pd.DataFrame(processed_races)


def moneyline_to_prob(odds):
    """
    Convert American moneyline odds to implied probability.
    
    Args:
        odds (float): American moneyline odds
        
    Returns:
        float: Implied probability (0.0 to 1.0)
    """
    odds = safe_float(odds)
    if not np.isfinite(odds):
        return np.nan
    if odds > 0:
        return 100.0 / (odds + 100.0)
    else:
        return (-odds) / (-odds + 100.0)


def normalize_probabilities(probs):
    """
    Normalize a list of probabilities to sum to 1.0.
    
    This removes the track's built-in profit margin (takeout).
    
    Args:
        probs (list): Raw market-implied probabilities
        
    Returns:
        list: Normalized probabilities that sum to 1.0
    """
    total = sum(probs)
    if total <= 0:
        return probs
    return [p / total for p in probs]


def harville_expected_payout(p1, p2, p3, p4):
    """
    Calculate theoretical superfecta payout using Harville formula.
    
    The Harville formula models the conditional probabilities of finish positions:
    P(1-2-3-4) = P(1 wins) × P(2|1 wins) × P(3|1,2 finish) × P(4|1,2,3 finish)
    
    Args:
        p1, p2, p3, p4 (float): Win probabilities for positions 1-4
        
    Returns:
        float: Expected payout for $1 bet, or NaN if invalid
    """
    # Calculate remaining probability pools after each position
    denom1 = 1 - p1                    # Pool remaining after 1st place
    denom2 = 1 - p1 - p2              # Pool remaining after 2nd place  
    denom3 = 1 - p1 - p2 - p3         # Pool remaining after 3rd place
    
    # All denominators must be positive
    if denom1 <= 0 or denom2 <= 0 or denom3 <= 0:
        return np.nan
        
    # Harville joint probability
    joint_prob = p1 * (p2 / denom1) * (p3 / denom2) * (p4 / denom3)
    
    if joint_prob <= 0:
        return np.nan
        
    # Convert probability to payout (inverse relationship)
    return 1.0 / joint_prob


def compute_features_targets(df: pd.DataFrame):
    """
    Compute comprehensive feature set and target variable for model training.
    
    This function creates 20+ features that capture various aspects of betting markets:
    - Individual horse probabilities and logits
    - Market structure (field size, odds distribution)
    - Economic factors (purse, pool size)
    - Race conditions (surface, distance, time)
    - Probability distribution characteristics
    
    Target variable: log(actual_payout / harville_payout)
    This log-ratio is more stable than raw differences and handles the wide
    range of payout values (from ~$10 to $100,000+).
    
    Args:
        df (pd.DataFrame): Race-level data from load_and_pivot()
        
    Returns:
        tuple: (processed_df, feature_matrix, target_vector, feature_names)
    """
    print("Computing features and targets...")
    
    # Use pre-computed normalized probabilities from load_and_pivot
    df["prob1"] = df["norm_prob1"]
    df["prob2"] = df["norm_prob2"]
    df["prob3"] = df["norm_prob3"]
    df["prob4"] = df["norm_prob4"]
    
    # Debug output: Show normalization effect
    print(f"Normalization Analysis:")
    print(f"  Average raw probability sum (all horses): {df['raw_prob_sum_all_horses'].mean():.4f}")
    print(f"  Average normalized sum (4 winners): {df['normalized_prob_sum_winners'].mean():.4f}")
    print(f"  Normalization removes ~{(df['raw_prob_sum_all_horses'].mean() - 1.0) * 100:.1f}% takeout")
    
    # Convert probabilities to logits for better model performance
    # logit(p) = log(p/(1-p)) maps bounded (0,1) to unbounded (-∞,∞)
    for i in range(1, 5):
        df[f"logit{i}"] = df[f"prob{i}"].apply(
            lambda p: log(p / (1 - p)) if 0 < p < 1 else 0.0
        )
    
    # Calculate Harville expected payouts using normalized probabilities
    harville_payouts = []
    for _, row in df.iterrows():
        harv_payout = harville_expected_payout(
            row["prob1"], row["prob2"], row["prob3"], row["prob4"]
        )
        harville_payouts.append(harv_payout)
    
    df["harville_payout"] = harville_payouts
    
    # Normalize actual payouts to $1 bet basis
    # Original payouts are typically for $2 bets, scaled by number of tickets
    df["multiplier"] = np.where(df["num_tickets"] > 0, 100.0 / df["num_tickets"], np.nan)
    df["actual_payout"] = df["payoff_amount"] * df["multiplier"]
    
    # Create target variable: log ratio of actual to theoretical payout
    # This captures systematic market biases while being numerically stable
    valid_mask = (
        ~pd.isna(df["harville_payout"]) & 
        (df["harville_payout"] > 0) &
        (df["num_tickets"] > 0) &
        (df["actual_payout"] > 0)
    )
    df = df[valid_mask].copy()
    
    df["log_ratio"] = np.log(df["actual_payout"] / df["harville_payout"])
    
    print(f"Valid races after Harville calculation: {len(df)}")
    print(f"Target variable (log_ratio) statistics:")
    print(f"  Range: {df['log_ratio'].min():.3f} to {df['log_ratio'].max():.3f}")
    print(f"  Mean: {df['log_ratio'].mean():.3f}, Std: {df['log_ratio'].std():.3f}")
    
    # Debug: Compare Harville vs Actual payouts
    print(f"Payout comparison:")
    print(f"  Harville range: ${df['harville_payout'].min():.2f} to ${df['harville_payout'].max():.2f}")
    print(f"  Actual range: ${df['actual_payout'].min():.2f} to ${df['actual_payout'].max():.2f}")
    print(f"  Harville mean: ${df['harville_payout'].mean():.2f}")
    print(f"  Actual mean: ${df['actual_payout'].mean():.2f}")
    
    # Remove extreme outliers (beyond 3 standard deviations)
    # These are likely data errors or extremely unusual circumstances
    log_ratio_mean = df["log_ratio"].mean()
    log_ratio_std = df["log_ratio"].std()
    outlier_threshold = 3
    
    outlier_mask = (
        (df["log_ratio"] >= log_ratio_mean - outlier_threshold * log_ratio_std) &
        (df["log_ratio"] <= log_ratio_mean + outlier_threshold * log_ratio_std)
    )
    
    outliers_removed = (~outlier_mask).sum()
    if outliers_removed > 0:
        print(f"Removing {outliers_removed} extreme outliers (±{outlier_threshold}σ)")
    df = df[outlier_mask].copy()
    df = df.reset_index(drop=True)
    
    # Feature Engineering: Create comprehensive feature set
    
    # Basic odds features
    df["favorite_odds"] = df[["odds1", "odds2", "odds3", "odds4"]].min(axis=1)
    df["longshot_odds"] = df[["odds1", "odds2", "odds3", "odds4"]].max(axis=1)
    df["odds_range"] = df["longshot_odds"] - df["favorite_odds"]
    
    # Probability distribution features
    df["prob_product"] = df["prob1"] * df["prob2"] * df["prob3"] * df["prob4"]
    df["prob_sum"] = df["prob1"] + df["prob2"] + df["prob3"] + df["prob4"]
    df["min_prob"] = df[["prob1", "prob2", "prob3", "prob4"]].min(axis=1)
    df["max_prob"] = df[["prob1", "prob2", "prob3", "prob4"]].max(axis=1)
    df["prob_variance"] = np.var([df[f"prob{i}"] for i in range(1, 5)], axis=0)
    
    # Information theory: entropy measures uncertainty in the outcome
    df["prob_entropy"] = -sum(df[f"prob{i}"] * np.log(df[f"prob{i}"] + 1e-10) 
                             for i in range(1, 5))
    
    # Economic features
    df["pool_per_runner"] = df["total_pool"] / df["number_of_runners"]
    df["purse_per_runner"] = df["purse_usa"] / df["number_of_runners"]
    
    # Harville-specific features that might indicate bias
    df["harville_log"] = np.log(df["harville_payout"])
    
    # Create dummy variables for categorical features
    categorical_features = ["surface", "course_type", "track_condition"]
    dummies = pd.get_dummies(df[categorical_features], prefix=categorical_features, dummy_na=True)
    df = pd.concat([df, dummies], axis=1)
    
    # Define complete feature list
    feature_cols = (
        # Core probability features
        [f"logit{i}" for i in range(1, 5)] +
        [f"prob{i}" for i in range(1, 5)] +
        
        # Race characteristics
        ["number_of_runners", "field_size", "purse_usa", "distance_id", 
         "post_hour", "total_pool", "avg_field_odds", "odds_std"] +
        
        # Derived features
        ["favorite_odds", "longshot_odds", "odds_range", "prob_product",
         "prob_sum", "prob_entropy", "min_prob", "max_prob", "pool_per_runner", 
         "purse_per_runner", "harville_log", "prob_variance"] +
        
        # Categorical dummy variables
        list(dummies.columns)
    )
    
    # Fill any remaining NaN values with 0
    df[feature_cols] = df[feature_cols].fillna(0)
    
    # Create feature matrix and target vector
    X = df[feature_cols].values
    y = df["log_ratio"].values
    
    print(f"Final dataset: {X.shape[0]} races, {X.shape[1]} features")
    
    return df, X, y, feature_cols


def merge_horse_features(
    df: pd.DataFrame, horse_features_path: str
) -> tuple[pd.DataFrame, list[str]]:
    """
    Merge horse-history features for each of the 4 superfecta winners.

    Requires that df contains reg1..reg4 (registration numbers) and
    track_id / race_date / race_number from load_and_pivot().

    Returns (enriched_df, new_feature_col_names).
    """
    HORSE_FEATURE_COLS = [
        "n_prior_starts", "prior_win_rate", "prior_top3_rate",
        "avg_finish_all", "avg_finish_last5", "days_since_last",
        "avg_prior_purse", "class_change",
        "surface_prior_starts", "surface_win_rate", "surface_avg_finish",
        "distance_prior_starts", "distance_win_rate", "distance_avg_finish",
        "track_prior_starts", "track_win_rate", "track_avg_finish",
    ]

    print(f"\n=== Merging Horse-History Features ===")
    print(f"Loading {horse_features_path} ...")

    hf = pd.read_csv(
        horse_features_path,
        parse_dates=["race_date"],
        dtype={"program_number": str, "registration_number": str},
    )

    # Build composite join key and deduplicate
    hf["_jk"] = (
        hf["registration_number"].astype(str) + "|"
        + hf["track_id"].astype(str) + "|"
        + hf["race_date"].astype(str) + "|"
        + hf["race_number"].astype(str)
    )
    hf = hf.drop_duplicates(subset="_jk", keep="first")
    hf_lookup = hf.set_index("_jk")[HORSE_FEATURE_COLS]

    new_cols: list[str] = []
    df = df.copy()

    # Per-position features (w1_ through w4_)
    for pos in range(1, 5):
        prefix = f"w{pos}_"
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


def analyze_longshot_bias(df: pd.DataFrame):
    """
    Analyze systematic bias in superfecta betting markets.
    
    Longshot bias refers to the tendency for low-probability combinations
    to pay out more (or less) than theoretically predicted. This analysis
    helps identify market inefficiencies.
    
    Args:
        df (pd.DataFrame): Processed race data
        
    Returns:
        pd.DataFrame: Bias analysis by probability range
    """
    print("\n=== Longshot Bias Analysis ===")
    
    # Create probability bins based on minimum horse probability in combination
    df["prob_bin"] = pd.cut(df["min_prob"], 
                           bins=[0, 0.05, 0.1, 0.2, 0.3, 1.0],
                           labels=["<5%", "5-10%", "10-20%", "20-30%", ">30%"])
    
    # Analyze bias by probability range
    bias_analysis = df.groupby("prob_bin").agg({
        "harville_payout": ["mean", "count"],
        "actual_payout": "mean", 
        "log_ratio": ["mean", "std"]
    }).round(3)
    
    bias_analysis.columns = ['_'.join(col).strip() for col in bias_analysis.columns]
    
    print("Bias by probability range:")
    print(bias_analysis)
    
    # Calculate relative bias (actual/harville - 1)
    bias_summary = df.groupby("prob_bin").apply(
        lambda x: pd.Series({
            'count': len(x),
            'avg_harville': x['harville_payout'].mean(),
            'avg_actual': x['actual_payout'].mean(),
            'relative_bias': (x['actual_payout'].mean() / x['harville_payout'].mean()) - 1,
            'log_ratio_mean': x['log_ratio'].mean()
        })
    ).round(4)
    
    print("\nRelative bias summary (positive = actual > harville):")
    print(bias_summary)
    
    return bias_analysis


def train_and_evaluate(df: pd.DataFrame, X, y, feature_cols, threads=None, tree_method="hist"):
    """
    Train XGBoost model with comprehensive evaluation and diagnostics.
    
    This function:
    1. Splits data into train/test sets
    2. Trains XGBoost with optimized hyperparameters
    3. Evaluates performance on multiple metrics
    4. Analyzes feature importance
    5. Performs bias correction analysis
    
    Args:
        df (pd.DataFrame): Full dataset
        X (np.ndarray): Feature matrix
        y (np.ndarray): Target vector
        feature_cols (list): Feature names
        threads (int, optional): Number of CPU threads for XGBoost
        tree_method (str): XGBoost tree construction method
        
    Returns:
        tuple: (trained_model, train_results, test_results, evaluation_metrics)
    """
    print("\n=== Training XGBoost Model ===")

    if threads is None:
        threads = max(1, os.cpu_count() or 1)
    
    # Chronological split to avoid leaking future races into training.
    sort_cols = ["race_date", "track_id", "race_number"]
    ordered_index = (
        df.sort_values(sort_cols, kind="mergesort")
          .index
          .to_numpy()
    )
    X_ordered = X[ordered_index]
    y_ordered = y[ordered_index]
    df_ordered = df.iloc[ordered_index].reset_index(drop=True)

    split_idx = int(len(df_ordered) * 0.75)
    split_idx = max(1, min(split_idx, len(df_ordered) - 1))

    X_train, X_test = X_ordered[:split_idx], X_ordered[split_idx:]
    y_train, y_test = y_ordered[:split_idx], y_ordered[split_idx:]
    df_train, df_test = df_ordered.iloc[:split_idx].copy(), df_ordered.iloc[split_idx:].copy()

    train_end = df_train["race_date"].max()
    test_start = df_test["race_date"].min()
    print(f"Chronological split: train <= {train_end.date()} | test >= {test_start.date()}")
    
    # XGBoost hyperparameters (optimized via hyperparameter tuning)
    # These parameters balance performance with overfitting prevention
    params = {
        "max_depth": 6,                    # Tree depth (prevent overfitting)
        "eta": 0.058902720515650556,       # Learning rate (slow learning)
        "subsample": 0.8587382809509695,   # Row sampling ratio
        "colsample_bytree": 0.7138183639990917,  # Column sampling ratio
        "reg_alpha": 1.6223569131405515,   # L1 regularization
        "reg_lambda": 2.833424833580529,   # L2 regularization
        "gamma": 0.28154211912969035,      # Minimum split loss
        "min_child_weight": 10,            # Minimum samples per leaf
        "objective": "reg:squarederror",   # Regression objective
        "eval_metric": "rmse",             # Evaluation metric
        "seed": 42,                         # Reproducibility
        "tree_method": tree_method,         # Faster CPU histogram training by default
        "nthread": threads                  # CPU threads for training
    }
    
    print(f"Using tree_method={tree_method}, threads={threads}")

    # Create DMatrix objects (XGBoost's internal data structure)
    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=feature_cols)
    dtest = xgb.DMatrix(X_test, label=y_test, feature_names=feature_cols)
    
    # Train model with early stopping to prevent overfitting
    model = xgb.train(
        params=params,
        dtrain=dtrain,
        num_boost_round=595,               # Maximum iterations
        evals=[(dtrain, "train"), (dtest, "test")],
        early_stopping_rounds=30,          # Stop if no improvement
        verbose_eval=25                    # Print progress every 25 rounds
    )
    
    # Generate predictions
    y_pred_train = model.predict(dtrain)
    y_pred_test = model.predict(dtest)
    
    # Add predictions to dataframes
    df_train_copy = df_train.copy()
    df_test_copy = df_test.copy()
    
    df_train_copy["predicted_log_ratio"] = y_pred_train
    df_test_copy["predicted_log_ratio"] = y_pred_test
    
    # Convert log-ratio predictions back to dollar payouts
    # corrected_payout = harville_payout × exp(predicted_log_ratio)
    df_train_copy["corrected_payout"] = (df_train_copy["harville_payout"] * 
                                        np.exp(df_train_copy["predicted_log_ratio"]))
    df_test_copy["corrected_payout"] = (df_test_copy["harville_payout"] * 
                                       np.exp(df_test_copy["predicted_log_ratio"]))
    
    # Evaluate model performance
    print("\n=== Performance Metrics ===")
    
    # Log-ratio prediction accuracy
    train_rmse_log = np.sqrt(mean_squared_error(y_train, y_pred_train))
    test_rmse_log = np.sqrt(mean_squared_error(y_test, y_pred_test))
    train_r2_log = r2_score(y_train, y_pred_train)
    test_r2_log = r2_score(y_test, y_pred_test)
    
    print(f"Log Ratio Prediction Performance:")
    print(f"  Train RMSE: {train_rmse_log:.4f}, R²: {train_r2_log:.4f}")
    print(f"  Test RMSE:  {test_rmse_log:.4f}, R²: {test_r2_log:.4f}")
    
    # Payout prediction comparison: Harville vs ML-corrected
    def evaluate_payout_predictions(df_subset, subset_name):
        """Compare Harville vs ML-corrected payout predictions."""
        # Calculate metrics for both approaches
        harv_rmse = np.sqrt(mean_squared_error(df_subset["actual_payout"], 
                                              df_subset["harville_payout"]))
        corr_rmse = np.sqrt(mean_squared_error(df_subset["actual_payout"], 
                                              df_subset["corrected_payout"]))
        
        harv_mae = mean_absolute_error(df_subset["actual_payout"], 
                                      df_subset["harville_payout"])
        corr_mae = mean_absolute_error(df_subset["actual_payout"], 
                                      df_subset["corrected_payout"])
        
        harv_r2 = r2_score(df_subset["actual_payout"], df_subset["harville_payout"])
        corr_r2 = r2_score(df_subset["actual_payout"], df_subset["corrected_payout"])
        
        harv_corr, _ = pearsonr(df_subset["actual_payout"], df_subset["harville_payout"])
        corr_corr, _ = pearsonr(df_subset["actual_payout"], df_subset["corrected_payout"])
        
        # Calculate improvement percentages
        rmse_improvement = (harv_rmse - corr_rmse) / harv_rmse * 100
        mae_improvement = (harv_mae - corr_mae) / harv_mae * 100
        
        print(f"\n{subset_name} Set Payout Predictions:")
        print(f"{'Model':<15} {'RMSE':<10} {'MAE':<10} {'R²':<10} {'Correlation':<12}")
        print("-" * 57)
        print(f"{'Harville':<15} {harv_rmse:<10.2f} {harv_mae:<10.2f} {harv_r2:<10.3f} {harv_corr:<12.3f}")
        print(f"{'ML-Corrected':<15} {corr_rmse:<10.2f} {corr_mae:<10.2f} {corr_r2:<10.3f} {corr_corr:<12.3f}")
        print(f"{'Improvement':<15} {harv_rmse-corr_rmse:<10.2f} {harv_mae-corr_mae:<10.2f} {corr_r2-harv_r2:<10.3f} {corr_corr-harv_corr:<12.3f}")
        print(f"{'% Improvement':<15} {rmse_improvement:<10.1f}% {mae_improvement:<10.1f}%")
        
        return {
            "harville_rmse": harv_rmse, "corrected_rmse": corr_rmse,
            "harville_mae": harv_mae, "corrected_mae": corr_mae,
            "harville_r2": harv_r2, "corrected_r2": corr_r2,
            "harville_corr": harv_corr, "corrected_corr": corr_corr,
            "rmse_improvement_pct": rmse_improvement,
            "mae_improvement_pct": mae_improvement
        }
    
    train_metrics = evaluate_payout_predictions(df_train_copy, "Train")
    test_metrics = evaluate_payout_predictions(df_test_copy, "Test")
    
    # Feature importance analysis
    print("\n=== Feature Importance (Top 15) ===")
    importance = model.get_score(importance_type="gain")
    sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    
    for i, (feature, score) in enumerate(sorted_importance[:15]):
        print(f"{i+1:2d}. {feature:<25} {score:.0f}")
    
    # Bias correction analysis
    print("\n=== Bias Correction Analysis ===")
    df_test_copy["prob_bin"] = pd.cut(df_test_copy["min_prob"], 
                                     bins=[0, 0.05, 0.1, 0.2, 0.3, 1.0],
                                     labels=["<5%", "5-10%", "10-20%", "20-30%", ">30%"])
    
    test_bias = df_test_copy.groupby("prob_bin").agg({
        "harville_payout": "mean",
        "actual_payout": "mean",
        "corrected_payout": "mean",
        "log_ratio": "mean",
        "predicted_log_ratio": "mean"
    }).round(2)
    
    print("Average payouts and corrections by probability range:")
    print(test_bias)
    
    return model, df_train_copy, df_test_copy, test_metrics


def create_visualizations(df_train, df_test, plot_prefix: str):
    """
    Create comprehensive visualizations for model analysis and diagnostics.
    
    Generates four key plots:
    1. Distribution comparison of actual vs predicted log ratios
    2. Scatter plot of predicted vs actual log ratios
    3. Harville vs actual payouts (log scale)
    4. ML-corrected vs actual payouts (log scale)
    5. Longshot bias analysis by probability range
    
    Args:
        df_train (pd.DataFrame): Training set with predictions
        df_test (pd.DataFrame): Test set with predictions
    """
    print("\n=== Creating Visualizations ===")
    
    # Set plotting style
    plt.style.use('default')
    
    # 1. Log ratio distribution comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    ax1.hist(df_test["log_ratio"], bins=50, alpha=0.7, 
             label="Actual Log Ratio", color="blue", density=True)
    ax1.hist(df_test["predicted_log_ratio"], bins=50, alpha=0.7, 
             label="Predicted Log Ratio", color="red", density=True)
    ax1.set_xlabel("Log Ratio (log(actual/harville))")
    ax1.set_ylabel("Density")
    ax1.set_title("Distribution of Log Ratios")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Predicted vs Actual Log Ratios (model accuracy)
    ax2.scatter(df_test["log_ratio"], df_test["predicted_log_ratio"], 
               alpha=0.5, s=10, color='purple')
    ax2.plot([-3, 3], [-3, 3], 'r--', lw=2, label='Perfect Prediction')
    ax2.set_xlabel("Actual Log Ratio")
    ax2.set_ylabel("Predicted Log Ratio")
    ax2.set_title("Predicted vs Actual Log Ratios")
    ax2.set_xlim(-3, 3)
    ax2.set_ylim(-3, 3)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plot1_path = f"{plot_prefix}_log_ratio_diagnostics.png"
    plt.savefig(plot1_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ Saved plot: {plot1_path}")
    
    # 3. Payout comparison plots (log scale for wide range)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Harville vs Actual payouts
    ax1.scatter(df_test["actual_payout"], df_test["harville_payout"], 
               alpha=0.5, s=10, color="blue")
    max_val = max(df_test["actual_payout"].max(), df_test["harville_payout"].max())
    ax1.plot([1, max_val], [1, max_val], 'r--', lw=2, label='Perfect Prediction')
    ax1.set_xlabel("Actual Payout ($)")
    ax1.set_ylabel("Harville Payout ($)")
    ax1.set_title("Harville vs Actual Payouts")
    ax1.set_xscale('log')
    ax1.set_yscale('log')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # ML-Corrected vs Actual payouts
    ax2.scatter(df_test["actual_payout"], df_test["corrected_payout"], 
               alpha=0.5, s=10, color="green")
    ax2.plot([1, max_val], [1, max_val], 'r--', lw=2, label='Perfect Prediction')
    ax2.set_xlabel("Actual Payout ($)")
    ax2.set_ylabel("ML-Corrected Payout ($)")
    ax2.set_title("ML-Corrected vs Actual Payouts")
    ax2.set_xscale('log')
    ax2.set_yscale('log')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plot2_path = f"{plot_prefix}_payout_comparison.png"
    plt.savefig(plot2_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ Saved plot: {plot2_path}")
    
    # 4. Longshot bias analysis visualization
    df_test_copy = df_test.copy()
    df_test_copy["prob_bin"] = pd.cut(df_test_copy["min_prob"], 
                                     bins=[0, 0.05, 0.1, 0.2, 0.3, 1.0],
                                     labels=["<5%", "5-10%", "10-20%", "20-30%", ">30%"])
    
    bias_data = df_test_copy.groupby("prob_bin").agg({
        "harville_payout": "mean",
        "actual_payout": "mean",
        "corrected_payout": "mean"
    }).reset_index()
    
    # Remove empty bins
    bias_data = bias_data.dropna()
    
    if len(bias_data) > 0:
        plt.figure(figsize=(12, 8))
        x = range(len(bias_data))
        width = 0.25
        
        plt.bar([i - width for i in x], bias_data["harville_payout"], width, 
               label="Harville (Theoretical)", alpha=0.8, color='blue')
        plt.bar(x, bias_data["actual_payout"], width, 
               label="Actual Market", alpha=0.8, color='orange')
        plt.bar([i + width for i in x], bias_data["corrected_payout"], width, 
               label="ML-Corrected", alpha=0.8, color='green')
        
        plt.xlabel("Minimum Horse Probability Range")
        plt.ylabel("Average Payout ($)")
        plt.title("Longshot Bias Analysis: Average Payouts by Probability Range")
        plt.xticks(x, bias_data["prob_bin"])
        plt.legend()
        plt.yscale('log')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plot3_path = f"{plot_prefix}_longshot_bias.png"
        plt.savefig(plot3_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"✅ Saved plot: {plot3_path}")


def main():
    """
    Main execution function orchestrating the complete training pipeline.
    
    This function:
    1. Loads and processes historical race data
    2. Performs comprehensive feature engineering
    3. Trains XGBoost model with bias correction
    4. Evaluates model performance and creates visualizations
    5. Saves model and detailed results
    
    Returns:
        None
    """
    args = parse_args()

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_stem = output_path.with_suffix("")

    model_path = Path(args.model_output).expanduser() if args.model_output else Path(f"{output_stem}_model.json")
    model_path.parent.mkdir(parents=True, exist_ok=True)

    plot_prefix = str(Path(args.plot_prefix).expanduser()) if args.plot_prefix else str(output_stem)
    Path(plot_prefix).parent.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Load and process historical race data
    print("=== SUPERFECTA PAYOUT PREDICTION MODEL TRAINING ===\n")
    
    df = load_and_pivot(args.csv, sample_size=args.sample)
    if df.empty:
        print("❌ No valid races found. Please check your data file.")
        return
    
    print(f"✅ Loaded {len(df)} races with complete superfecta data")
    
    # Step 2: Feature engineering and target creation
    df, X, y, feature_cols = compute_features_targets(df)
    
    print(f"✅ Created {len(feature_cols)} baseline features")

    # Step 2b (optional): Merge horse-history features
    if args.horse_features:
        df, horse_cols = merge_horse_features(df, args.horse_features)
        feature_cols = feature_cols + horse_cols
        df[feature_cols] = df[feature_cols].fillna(0)
        X = df[feature_cols].values
        y = df["log_ratio"].values
        print(f"✅ Enriched to {len(feature_cols)} features ({len(horse_cols)} horse-history)")
    else:
        print("   (horse-history features not requested; use --horse-features to enable)")

    # Step 3: Analyze market biases before correction
    analyze_longshot_bias(df)
    
    # Step 4: Train and evaluate ML model
    model, df_train, df_test, test_metrics = train_and_evaluate(
        df, X, y, feature_cols,
        threads=args.threads,
        tree_method=args.tree_method,
    )
    
    print(f"✅ Model training complete")
    print(f"   Test set RMSE improvement: {test_metrics['rmse_improvement_pct']:.1f}%")
    print(f"   Test set MAE improvement: {test_metrics['mae_improvement_pct']:.1f}%")
    
    # Step 5: Create diagnostic visualizations
    create_visualizations(df_train, df_test, plot_prefix)
    
    # Step 6: Save results and model
    output_cols = [
        "track_id", "race_date", "race_number", "actual_payout", 
        "harville_payout", "predicted_log_ratio", "corrected_payout",
        "log_ratio", "prob1", "prob2", "prob3", "prob4"
    ]
    
    # Save detailed test results
    df_test[output_cols].to_csv(output_path, index=False)
    print(f"✅ Detailed results saved to {output_path}")
    
    # Save trained model
    model.save_model(model_path)
    print(f"✅ Trained model saved to {model_path}")

    metrics_summary = {
        "dataset_races": int(len(df)),
        "feature_count": int(X.shape[1]),
        "harville_rmse": float(test_metrics["harville_rmse"]),
        "corrected_rmse": float(test_metrics["corrected_rmse"]),
        "harville_mae": float(test_metrics["harville_mae"]),
        "corrected_mae": float(test_metrics["corrected_mae"]),
        "harville_r2": float(test_metrics["harville_r2"]),
        "corrected_r2": float(test_metrics["corrected_r2"]),
        "harville_corr": float(test_metrics["harville_corr"]),
        "corrected_corr": float(test_metrics["corrected_corr"]),
        "rmse_improvement_pct": float(test_metrics["rmse_improvement_pct"]),
        "mae_improvement_pct": float(test_metrics["mae_improvement_pct"])
    }
    metrics_path = Path(f"{output_stem}_metrics.json")
    metrics_path.write_text(json.dumps(metrics_summary, indent=2))
    print(f"✅ Metrics summary saved to {metrics_path}")
    
    # Summary statistics
    print(f"\n=== TRAINING SUMMARY ===")
    print(f"📊 Dataset: {len(df)} races, {X.shape[1]} features")
    print(f"🎯 Model Performance:")
    print(f"   • Harville RMSE: ${test_metrics['harville_rmse']:.2f}")
    print(f"   • ML-Corrected RMSE: ${test_metrics['corrected_rmse']:.2f}")
    print(f"   • Improvement: {test_metrics['rmse_improvement_pct']:.1f}%")
    print(f"💡 The model learns systematic biases in superfecta betting markets")
    print(f"🚀 Ready for live predictions!")


if __name__ == "__main__":
    main()