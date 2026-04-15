#!/usr/bin/env python3
"""
predict_single_race.py

A comprehensive superfecta prediction system that uses machine learning to improve upon
traditional Harville probability models for horse racing.

This script:
1. Loads race data from CSV files
2. Calculates market-implied probabilities from betting odds
3. Applies the Harville formula for multi-horse finish probabilities
4. Uses a trained XGBoost model to correct for known biases (longshot bias, etc.)
5. Generates predictions for all possible 4-horse finishing combinations

Key Features:
- High-precision decimal arithmetic to avoid floating-point errors
- Normalization of probabilities to remove track takeout effects
- Feature engineering based on race characteristics and betting patterns
- Model-based correction of theoretical Harville payouts

Author: Cole Bender
Version: 2.0
Last Updated: 8/5/2025
"""

from decimal import Decimal, getcontext
import argparse
import os
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
from math import log
from itertools import permutations
from pathlib import Path
import warnings

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from ev_ticket_engine import add_ev_metrics

# Suppress XGBoost warnings for cleaner output
warnings.filterwarnings("ignore")

# Set high precision for Decimal calculations to avoid rounding errors
# in probability calculations where small differences matter significantly
getcontext().prec = 50


def parse_args():
    """
    Parse command line arguments for the prediction script.
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Predict superfecta payouts for a single race using machine learning",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--input", "-i", 
        required=True, 
        help="Path to single race CSV file containing horse data"
    )
    
    parser.add_argument(
        "--model", "-m", 
        required=True, 
        help="Path to trained XGBoost model (.json file)"
    )
    
    parser.add_argument(
        "--output", "-o", 
        default="race_predictions.csv", 
        help="Output CSV file for predictions"
    )
    
    parser.add_argument(
        "--top-combinations", 
        type=int, 
        default=20, 
        help="Number of top combinations to show in output"
    )

    parser.add_argument(
        "--sort-by",
        choices=["jointProb", "ev"],
        default="jointProb",
        help="Rank output by raw joint probability or conservative expected value"
    )

    parser.add_argument(
        "--threads",
        type=int,
        default=max(1, os.cpu_count() or 1),
        help="Number of CPU threads for model inference"
    )
    
    return parser.parse_args()


def load_race_data(csv_path):
    """
    Load and validate single race data from CSV file.
    
    Args:
        csv_path (str): Path to the CSV file containing race data
        
    Returns:
        pd.DataFrame: Cleaned DataFrame with non-scratched horses only
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If required columns are missing
    """
    print(f"Loading race data from {csv_path}...")
    
    try:
        # Load CSV with appropriate data types
        df = pd.read_csv(
            csv_path, 
            parse_dates=["race_date"], 
            dtype={"post_time": str}
        )
    except FileNotFoundError:
        raise FileNotFoundError(f"Could not find race data file: {csv_path}")
    except Exception as e:
        raise ValueError(f"Error loading CSV file: {e}")
    
    # Remove scratched horses - they don't participate in the race
    initial_count = len(df)
    df = df[df["scratch_indicator"].fillna("N") != "Y"]
    scratched_count = initial_count - len(df)
    
    if scratched_count > 0:
        print(f"Removed {scratched_count} scratched horses")
    
    if len(df) == 0:
        raise ValueError("No active horses found in race data")
    
    print(f"Loaded {len(df)} active horses")
    
    # Display race information for verification
    if len(df) > 0:
        race_info = df.iloc[0]
        print(f"Race: {race_info['track_id']} on {race_info['race_date'].date()}, "
              f"Race #{race_info['race_number']}")
    
    return df


def odds_to_prob(odds):
    """
    Convert American moneyline odds to implied probability.
    
    American odds work as follows:
    - Positive odds (e.g., +300): Amount you win for $100 bet
    - Negative odds (e.g., -150): Amount you bet to win $100
    
    Args:
        odds (float): American moneyline odds
        
    Returns:
        float: Implied probability (0.0 to 1.0)
    """
    odds = Decimal(str(odds))
    
    if odds > 0:
        # For positive odds: probability = 100 / (odds + 100)
        prob = Decimal('100.0') / (odds + Decimal('100.0'))
    else:
        # For negative odds: probability = |odds| / (|odds| + 100)
        prob = (-odds) / (-odds + Decimal('100.0'))
    
    return float(prob)


def normalize_probs(raw_probs):
    """
    Normalize a list of probabilities to sum to 1.0.
    
    This removes the track's takeout (profit margin) from the betting market,
    which causes raw probabilities to sum to more than 1.0.
    
    Args:
        raw_probs (list): List of raw market-implied probabilities
        
    Returns:
        list: Normalized probabilities that sum to 1.0
    """
    total = sum(raw_probs)
    
    if total <= 0:
        # Edge case: no valid probabilities
        print("Warning: Total probability is zero or negative")
        return raw_probs
    
    # Divide each probability by the total to normalize
    return [p / total for p in raw_probs]


def calculate_probabilities(df):
    """
    Calculate normalized win probabilities for all horses in the race.
    
    Args:
        df (pd.DataFrame): DataFrame containing horse odds
        
    Returns:
        list: Normalized probabilities for each horse
    """
    print("Calculating probabilities...")
    
    # Convert odds to raw probabilities for all horses
    raw_probs = []
    for _, row in df.iterrows():
        prob = odds_to_prob(row["odds"])
        raw_probs.append(prob)
    
    print(f"Raw total probability: {sum(raw_probs):.4f}")
    
    # Normalize to remove track takeout
    probs = normalize_probs(raw_probs)
    
    print(f"Normalized total probability: {sum(probs):.4f}")
    print(f"First 5 probabilities: {[f'{p:.4f}' for p in probs[:5]]}")
    
    return probs


def calc_harville(prob1, prob2, prob3, prob4):
    """
    Calculate joint probability of 4-horse finishing order using Harville formula.
    
    The Harville formula accounts for the conditional nature of place betting:
    - Horse 1 wins with probability prob1
    - Horse 2 places 2nd with probability prob2/(1-prob1) 
    - Horse 3 places 3rd with probability prob3/(1-prob1-prob2)
    - Horse 4 places 4th with probability prob4/(1-prob1-prob2-prob3)
    
    Args:
        prob1, prob2, prob3, prob4 (float): Win probabilities for horses 1-4
        
    Returns:
        float: Joint probability of this exact finishing order, or NaN if invalid
    """
    # Use high precision arithmetic to avoid compounding errors
    p1_d = Decimal(str(prob1))
    p2_d = Decimal(str(prob2))
    p3_d = Decimal(str(prob3))
    p4_d = Decimal(str(prob4))
    
    # Calculate remaining probability pools after each position
    denom1_d = Decimal('1') - p1_d                    # Remaining after 1st
    denom2_d = Decimal('1') - p1_d - p2_d            # Remaining after 2nd
    denom3_d = Decimal('1') - p1_d - p2_d - p3_d     # Remaining after 3rd
    
    # All denominators must be positive for valid calculation
    if denom1_d > 0 and denom2_d > 0 and denom3_d > 0:
        # Harville joint probability formula
        joint_prob_d = p1_d * (p2_d/denom1_d) * (p3_d/denom2_d) * (p4_d/denom3_d)
        
        if joint_prob_d > 0:
            return float(joint_prob_d)
        else:
            return np.nan
    else:
        # Invalid probability combination
        return np.nan


def build_features(combo_indices, probs, df):
    """
    Build comprehensive feature vector for a 4-horse combination.
    
    Creates features used by the XGBoost model to predict deviations from
    theoretical Harville payouts.
    
    Args:
        combo_indices (tuple): Indices of 4 horses in finishing order
        probs (list): Win probabilities for all horses
        df (pd.DataFrame): Race data
        
    Returns:
        tuple: (features_dict, harville_joint_prob, harville_payout, 
                surface, course_type, track_condition) or None if invalid
    """
    # Extract probabilities for this specific combination
    prob1 = probs[combo_indices[0]]  # 1st place horse
    prob2 = probs[combo_indices[1]]  # 2nd place horse
    prob3 = probs[combo_indices[2]]  # 3rd place horse
    prob4 = probs[combo_indices[3]]  # 4th place horse
    
    # Calculate theoretical Harville probability
    harville_joint_prob = calc_harville(prob1, prob2, prob3, prob4)
    
    if pd.isna(harville_joint_prob):
        # Invalid combination - skip
        return None
    
    # Convert probability to expected payout (for $1 bet)
    harville_payout = 1.0 / harville_joint_prob
    
    # Initialize feature dictionary
    features = {}
    
    # Core probability features - the main predictors
    features["prob1"] = prob1
    features["prob2"] = prob2  
    features["prob3"] = prob3
    features["prob4"] = prob4
    
    # Logit transformation of probabilities for better model performance
    # logit(p) = log(p/(1-p)) maps (0,1) to (-∞,∞)
    features["logit1"] = log(prob1/(1-prob1)) if 0 < prob1 < 1 else 0.0
    features["logit2"] = log(prob2/(1-prob2)) if 0 < prob2 < 1 else 0.0
    features["logit3"] = log(prob3/(1-prob3)) if 0 < prob3 < 1 else 0.0
    features["logit4"] = log(prob4/(1-prob4)) if 0 < prob4 < 1 else 0.0
    
    # Extract race-level characteristics
    race_row = df.iloc[0]  # All horses share same race info
    
    # Field size affects betting dynamics
    features["number_of_runners"] = len(df)
    features["field_size"] = len(df)  # Duplicate for model compatibility
    
    # Economic factors
    features["purse_usa"] = float(race_row.get("purse_usa", 90000))
    features["distance_id"] = float(race_row.get("distance_id", 550))
    features["total_pool"] = float(race_row.get("total_pool", 96577))
    features["harville_log"] = log(harville_payout)  # Log of theoretical payout
    
    # Parse post time to extract hour of day
    post_time_str = str(race_row.get("post_time", "1400"))
    try:
        if len(post_time_str) >= 5:  # Handle "00230" format
            post_hour = int(post_time_str[-4:-2])  # Extract hour from last 4 digits
        elif len(post_time_str) >= 4:
            post_hour = int(post_time_str[-4:-2])
        else:
            post_hour = 14  # Default afternoon time
    except (ValueError, IndexError):
        post_hour = 14
    features["post_hour"] = float(post_hour)
    
    # Odds-based features for the 4 horses in this combination
    all_odds = df["odds"].values  # All horses in race
    winner_odds = [df.iloc[i]["odds"] for i in combo_indices]  # Just our 4 horses
    
    features["favorite_odds"] = min(winner_odds)
    features["longshot_odds"] = max(winner_odds)
    features["odds_range"] = features["longshot_odds"] - features["favorite_odds"]
    
    # Probability distribution features
    features["min_prob"] = min([prob1, prob2, prob3, prob4])
    features["max_prob"] = max([prob1, prob2, prob3, prob4])
    features["prob_variance"] = np.var([prob1, prob2, prob3, prob4])
    features["prob_product"] = prob1 * prob2 * prob3 * prob4
    features["prob_sum"] = prob1 + prob2 + prob3 + prob4
    
    # Information theory: entropy measures uncertainty
    features["prob_entropy"] = -sum(p * log(p + 1e-10) for p in [prob1, prob2, prob3, prob4])
    
    # Market characteristics
    features["avg_field_odds"] = np.mean(all_odds)
    features["odds_std"] = np.std(all_odds)
    
    # Economic ratios
    features["pool_per_runner"] = features["total_pool"] / features["number_of_runners"]
    features["purse_per_runner"] = features["purse_usa"] / features["number_of_runners"]
    
    # Extract categorical features (track conditions)
    surface = str(race_row.get("surface", "T")).strip()
    course_type = str(race_row.get("course_type", "T")).strip()
    track_condition = str(race_row.get("track_condition", "FM")).strip()
    
    return features, harville_joint_prob, harville_payout, surface, course_type, track_condition


def load_model(model_path, threads=None):
    """Load model once and configure inference threads."""
    if threads is None:
        threads = max(1, os.cpu_count() or 1)

    model = xgb.Booster()
    model.load_model(model_path)
    model.set_param({"nthread": threads})
    return model, model.feature_names


def make_prediction(features, surface, course_type, track_condition, model, model_features):
    """
    Generate prediction using trained XGBoost model.
    
    Args:
        features (dict): Feature dictionary
        surface (str): Track surface type
        course_type (str): Course configuration
        track_condition (str): Track condition
        model: Loaded XGBoost model
        model_features (list): Feature names expected by the model
        
    Returns:
        float: Predicted log ratio (log(actual_payout / harville_payout))
    """
    
    # Initialize all categorical features to 0
    for feat in model_features:
        if feat.startswith(('surface_', 'course_type_', 'track_condition_')):
            features[feat] = 0
    
    # Set active categorical features to 1 (one-hot encoding)
    features[f"surface_{surface}"] = 1
    features[f"course_type_{course_type}"] = 1  
    features[f"track_condition_{track_condition}"] = 1
    
    # Build feature vector in the exact order expected by the model
    feature_vector = []
    for feat in model_features:
        feature_vector.append(features.get(feat, 0.0))
    
    # Make prediction
    X = np.array([feature_vector])
    dmatrix = xgb.DMatrix(X, feature_names=model_features)
    log_ratio_pred = model.predict(dmatrix)[0]
    
    return log_ratio_pred


def analyze_race(df, model_path, top_n, sort_by="jointProb", threads=None):
    """
    Analyze all possible superfecta combinations for the race.
    
    This is the main analysis function that:
    1. Calculates probabilities for all horses
    2. Generates all 4-horse permutations  
    3. Applies Harville formula and ML corrections
    4. Returns top combinations by likelihood
    
    Args:
        df (pd.DataFrame): Race data
        model_path (str): Path to trained model
        top_n (int): Number of top combinations to return
        
    Returns:
        pd.DataFrame: Top combinations with predictions
    """
    print("Analyzing superfecta combinations...")

    model, model_features = load_model(model_path, threads=threads)
    print(f"Using inference threads={threads or max(1, os.cpu_count() or 1)}")
    
    # Calculate normalized probabilities for all horses
    probs = calculate_probabilities(df)
    
    # Generate all possible 4-horse finishing order combinations
    horse_indices = list(range(len(df)))
    results = []
    
    combo_count = 0
    total_combinations = len(df) * (len(df)-1) * (len(df)-2) * (len(df)-3)
    print(f"Processing {total_combinations:,} possible combinations...")
    
    for combo_indices in permutations(horse_indices, 4):
        combo_count += 1
        
        # Build features for this combination
        feature_result = build_features(combo_indices, probs, df)
        if feature_result is None:
            continue
            
        features, harville_joint_prob, harville_payout, surface, course_type, track_condition = feature_result
        
        # Get ML prediction for bias correction
        log_ratio_pred = make_prediction(features, surface, course_type, track_condition, model, model_features)
        
        # Calculate final predicted payout: Harville × ML correction factor
        predicted_payout = harville_payout * np.exp(log_ratio_pred)
        
        # Store results with human-readable program numbers
        results.append({
            "combo": "-".join([str(df.iloc[i]['program_number']) for i in combo_indices]),
            "h1": df.iloc[combo_indices[0]]['odds'],    # 1st place horse odds
            "h2": df.iloc[combo_indices[1]]['odds'],    # 2nd place horse odds
            "h3": df.iloc[combo_indices[2]]['odds'],    # 3rd place horse odds
            "h4": df.iloc[combo_indices[3]]['odds'],    # 4th place horse odds
            "winPct1": probs[combo_indices[0]] * 100,   # Win probability %
            "winPct2": probs[combo_indices[1]] * 100,
            "winPct3": probs[combo_indices[2]] * 100,
            "winPct4": probs[combo_indices[3]] * 100,
            "jointProb": harville_joint_prob,           # Raw joint probability
            "jointProbPct": harville_joint_prob * 100,  # Joint probability %
            "harville_payout": harville_payout,         # Theoretical payout
            "predicted_log_ratio": log_ratio_pred,      # ML correction factor
            "predicted_payout": predicted_payout,       # Final predicted payout
            "multiplier": np.exp(log_ratio_pred)        # Harville multiplier
        })
        
        # Progress reporting
        if combo_count % 1000 == 0:
            print(f"Processed {combo_count:,} combinations...")
    
    # Convert to DataFrame and add EV columns
    results_df = pd.DataFrame(results)
    results_df = add_ev_metrics(results_df)

    if sort_by == "ev":
        results_df = results_df.sort_values(['ev_profit_1', 'jointProb'], ascending=[False, False])
    else:
        results_df = results_df.sort_values('jointProb', ascending=False)

    results_df = results_df.reset_index(drop=True)
    results_df['rank'] = range(1, len(results_df) + 1)
    
    # Check if we have the actual winning combination for validation
    winning_numbers = df.iloc[0].get("winning_numbers", None)
    if pd.notna(winning_numbers):
        actual_winner = [x.strip() for x in str(winning_numbers).split("-")]
        actual_combo = "-".join(actual_winner)
        
        print(f"\nActual winning combination: {actual_combo}")
        
        # Find actual winner in our results
        winner_row = results_df[results_df['combo'] == actual_combo]
        if not winner_row.empty:
            rank = winner_row.iloc[0]['rank']
            predicted_payout_val = winner_row.iloc[0]['predicted_payout']
            harville_payout_val = winner_row.iloc[0]['harville_payout']
            
            print(f"✅ Found actual winner at rank {rank}")
            print(f"  Harville expected: ${harville_payout_val:.2f}")
            print(f"  Model predicted: ${predicted_payout_val:.2f}")
            
            # Compare with actual payout if available
            payoff_amount = df.iloc[0].get("payoff_amount", None)
            num_tickets = df.iloc[0].get("number_of_tickets_bet", None)
            if pd.notna(payoff_amount) and pd.notna(num_tickets):
                # Normalize to $1 bet using same formula as training
                actual_payout = float(payoff_amount) * (100.0 / float(num_tickets))
                print(f"  Actual payout: ${actual_payout:.2f}")
                error = abs(predicted_payout_val - actual_payout) / actual_payout * 100
                print(f"  Prediction error: {error:.1f}%")
        else:
            print("❌ Actual winner not found in results")
    
    return results_df.head(top_n)


def save_results(results_df, output_path):
    """
    Save prediction results to CSV file with summary statistics.
    
    Args:
        results_df (pd.DataFrame): Results to save
        output_path (str): Output file path
    """
    print(f"Saving results to {output_path}...")
    
    # Define column order for consistent output format
    column_order = [
        "combo", "h1", "h2", "h3", "h4", 
        "winPct1", "winPct2", "winPct3", "winPct4", 
        "jointProb", "jointProbPct",
        "harville_payout", "predicted_log_ratio", "predicted_payout", "adj_predicted_payout",
        "expected_return_1", "ev_profit_1", "ev_roi_pct", "full_kelly_frac",
        "multiplier", "value_rank", "rank"
    ]
    
    # Reorder columns
    output_df = results_df[column_order].copy()
    
    # Round numerical columns for readability
    percentage_columns = ["winPct1", "winPct2", "winPct3", "winPct4", "jointProbPct"]
    for col in percentage_columns:
        output_df[col] = output_df[col].round(6)  # 6 decimal places for percentages
    
    other_numeric_columns = ["jointProb", "harville_payout", "predicted_log_ratio", 
                           "predicted_payout", "adj_predicted_payout", "expected_return_1",
                           "ev_profit_1", "ev_roi_pct", "full_kelly_frac", "multiplier"]
    for col in other_numeric_columns:
        output_df[col] = output_df[col].round(8)  # 8 decimal places for other numbers
    
    # Save main results file
    output_df.to_csv(output_path, index=False)
    
    # Create summary report
    summary_path = output_path.replace(".csv", "_summary.txt")
    with open(summary_path, "w") as f:
        f.write("=== RACE PREDICTION SUMMARY ===\n\n")
        f.write(f"Total combinations analyzed: {len(results_df):,}\n")
        f.write(f"Most likely combination probability: {results_df['jointProbPct'].max():.4f}%\n")
        f.write(f"Highest predicted payout: ${results_df['predicted_payout'].max():,.2f}\n")
        f.write(f"Average predicted payout: ${results_df['predicted_payout'].mean():,.2f}\n")
        f.write(f"Median predicted payout: ${results_df['predicted_payout'].median():,.2f}\n")
        
        # Distribution analysis
        f.write(f"\nPayout Distribution:\n")
        f.write(f"  10th percentile: ${results_df['predicted_payout'].quantile(0.1):,.2f}\n")
        f.write(f"  25th percentile: ${results_df['predicted_payout'].quantile(0.25):,.2f}\n")
        f.write(f"  75th percentile: ${results_df['predicted_payout'].quantile(0.75):,.2f}\n")
        f.write(f"  90th percentile: ${results_df['predicted_payout'].quantile(0.9):,.2f}\n")
    
    print(f"Summary saved to {summary_path}")


def main():
    """
    Main execution function with comprehensive error handling.
    
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    args = parse_args()
    
    try:
        # Step 1: Load and validate race data
        df = load_race_data(args.input)
        
        # Step 2: Analyze all combinations
        results_df = analyze_race(
            df,
            args.model,
            args.top_combinations,
            sort_by=args.sort_by,
            threads=args.threads,
        )
        
        # Step 3: Save results
        save_results(results_df, args.output)
        
        # Step 4: Display summary to console
        print(f"\n=== ANALYSIS COMPLETE ===")
        print(f"✅ Analyzed {len(df)} horses")
        print(f"🎯 Most likely combination probability: {results_df['jointProbPct'].max():.4f}%")
        print(f"💰 Highest predicted payout: ${results_df['predicted_payout'].max():,.2f}")
        print(f"📊 Results saved to: {args.output}")
        
        # Show top 5 combinations for quick reference
        label = "TOP 5 EV COMBINATIONS" if args.sort_by == "ev" else "TOP 5 MOST LIKELY COMBINATIONS"
        print(f"\n=== {label} ===")
        for _, row in results_df.head(5).iterrows():
            print(f"{row['rank']:2d}. {row['combo']} - "
                  f"Probability: {row['jointProbPct']:.4f}%")
            print(f"     Harville: ${row['harville_payout']:.2f}, "
                  f"Predicted: ${row['predicted_payout']:.2f}, "
                  f"EV ROI: {row['ev_roi_pct']:.2f}%")
            print(f"     ML Multiplier: {row['multiplier']:.2f}x | Value rank: {int(row['value_rank'])}")
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())