#!/usr/bin/env python3
"""
model_main.py

Real-time superfecta prediction system using NYRA API and trained XGBoost model.

This script provides a complete end-to-end pipeline for making superfecta predictions
on live horse races. It integrates with the NYRA API to fetch real-time race data
and betting pools, then applies a trained machine learning model to predict payouts.

Key Features:
1. Real-time data integration with NYRA API
2. Interactive race selection interface
3. Market-implied probability calculation from live betting pools
4. Harville formula application for baseline predictions
5. XGBoost model corrections for market biases
6. Optimized processing for large combination spaces
7. Comprehensive output with rankings and confidence metrics

Workflow:
1. Fetch available race cards from NYRA
2. Allow user to select specific race
3. Get live betting pool data
4. Calculate win probabilities from market data
5. Generate all possible 4-horse combinations
6. Apply Harville formula for baseline predictions
7. Use ML model to correct for known biases
8. Rank combinations by probability and value
9. Output top predictions with detailed analysis


Author: Cole Bender
Version: 3.0
Last Updated: 8/5/2025
"""
import sys
import os
import logging
import argparse
import pandas as pd
import numpy as np
import xgboost as xgb
from decimal import Decimal, getcontext
from math import log
from itertools import permutations
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from ev_ticket_engine import add_ev_metrics

# Import NYRA API functions
from list_cards import list_cards
from list_races import list_races
from get_races import get_race_detail
from get_probables import get_probables

# Set high precision for Decimal calculations
getcontext().prec = 50

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S"
    )

def parse_args():
    parser = argparse.ArgumentParser(description="Predict superfecta payouts using NYRA API")
    parser.add_argument("--model", "-m", required=True, help="Path to trained XGBoost model (.json file)")
    parser.add_argument("--output", "-o", default="nyra_predictions.csv", help="Output CSV file for predictions")
    parser.add_argument("--top-combinations", type=int, default=20, help="Number of top combinations to show (default: 20)")
    parser.add_argument("--sort-by", choices=["jointProb", "ev"], default="jointProb", help="Rank output by raw joint probability or conservative expected value")
    parser.add_argument("--race-id", help="Specific race ID to analyze (optional)")
    parser.add_argument("--threads", type=int, default=max(1, os.cpu_count() or 1), help="Number of CPU threads for model inference")
    return parser.parse_args()

def choose_from_list(items, label_fn):
    for idx, itm in enumerate(items, 1):
        print(f"{idx:>3}) {label_fn(itm)}")
    choice = input("Enter number: ").strip()
    try:
        return items[int(choice) - 1]
    except (ValueError, IndexError):
        logging.error("Invalid selection: %r", choice)
        sys.exit(1)

def fetch_win_pool(race_detail):
    for key in ("poolTypeCode", "iTSPPoolTypeCode"):
        for pool in race_detail.get("pools", []):
            code = pool.get(key, "").strip().upper()
            if code in ("WN", "WIN"):
                return pool
    return None

def compute_win_percentages_and_odds(runners, probables):
    """Build maps {programNumber: implied_win_pct} and {programNumber: odds}."""
    win_pool = {}
    for p in probables:
        sel = str(p.get("selection"))
        if p.get("totalPoolGross"):
            amt = p["totalPoolGross"].get("amount", 0.0)
        elif p.get("totalPoolNet"):
            amt = p["totalPoolNet"].get("amount", 0.0)
        else:
            amt = p.get("stake", {}).get("amount", 0.0)
        win_pool[sel] = amt

    total = sum(win_pool.values())
    if total <= 0:
        logging.error("No money in WIN pool yet; retry in a few minutes.")
        return None, None

    win_pct = {}
    odds_map = {}
    for r in runners:
        prog = str(r.get("programNumber"))
        pct = win_pool.get(prog, 0.0) / total
        win_pct[prog] = pct
        # Convert percentage to cents format odds (multiply by 100)
        if pct > 0:
            decimal_odds = (1.0 - pct) / pct
            cents_odds = int(decimal_odds * 100)  # Convert to cents format
            odds_map[prog] = cents_odds
        else:
            odds_map[prog] = 9900  # High odds for no money bet

    return win_pct, odds_map

def odds_to_prob(odds):
    """Convert odds to probability using high precision"""
    odds = Decimal(str(odds))
    if odds > 0:
        prob = Decimal('100.0') / (odds + Decimal('100.0'))
    else:
        prob = (-odds) / (-odds + Decimal('100.0'))
    return float(prob)

def normalize_probs(raw_probs):
    """Normalize probabilities to sum to 1"""
    total = sum(raw_probs)
    if total <= 0:
        return raw_probs
    return [p / total for p in raw_probs]

def calc_harville(prob1, prob2, prob3, prob4):
    """Calculate Harville joint probability using high precision arithmetic"""
    p1_d = Decimal(str(prob1))
    p2_d = Decimal(str(prob2))
    p3_d = Decimal(str(prob3))
    p4_d = Decimal(str(prob4))
    
    denom1_d = Decimal('1') - p1_d
    denom2_d = Decimal('1') - p1_d - p2_d
    denom3_d = Decimal('1') - p1_d - p2_d - p3_d
    
    if denom1_d > 0 and denom2_d > 0 and denom3_d > 0:
        joint_prob_d = p1_d * (p2_d/denom1_d) * (p3_d/denom2_d) * (p4_d/denom3_d)
        
        if joint_prob_d > 0:
            return float(joint_prob_d)
        else:
            return np.nan
    else:
        return np.nan

def build_features(combo_indices, probs, race_detail, runners, odds_map):
    """Build feature vector for a combination"""
    
    # Get probabilities for this combination in finishing order
    prob1 = probs[combo_indices[0]]
    prob2 = probs[combo_indices[1]] 
    prob3 = probs[combo_indices[2]]
    prob4 = probs[combo_indices[3]]
    
    # Calculate Harville joint probability
    harville_joint_prob = calc_harville(prob1, prob2, prob3, prob4)
    
    if pd.isna(harville_joint_prob):
        return None
    
    # Calculate payout from joint probability
    harville_payout = 1.0 / harville_joint_prob
    
    # Create feature vector
    features = {}
    
    # Core probability features
    features["prob1"] = prob1
    features["prob2"] = prob2  
    features["prob3"] = prob3
    features["prob4"] = prob4
    
    # Logit features
    features["logit1"] = log(prob1/(1-prob1)) if 0 < prob1 < 1 else 0.0
    features["logit2"] = log(prob2/(1-prob2)) if 0 < prob2 < 1 else 0.0
    features["logit3"] = log(prob3/(1-prob3)) if 0 < prob3 < 1 else 0.0
    features["logit4"] = log(prob4/(1-prob4)) if 0 < prob4 < 1 else 0.0
    
    # Race features from NYRA API
    features["number_of_runners"] = len(runners)
    features["field_size"] = len(runners)
    features["purse_usa"] = float(race_detail.get("totalPurse", {}).get("amount", 90000))
    
    # Convert distance from furlongs/miles to numeric (6 furlongs = 600, 1 mile = 800)
    distance_str = race_detail.get("distance", "5.5 Furlongs")
    try:
        if "Furlong" in distance_str:
            # Extract number before "Furlong" - handle decimals
            distance_num = float(distance_str.split()[0]) * 100
        elif "Mile" in distance_str:
            # Handle mile distances like "1 1/8 Mile"
            parts = distance_str.replace("Mile", "").strip().split()
            if len(parts) == 1:
                # Simple case like "1 Mile"
                distance_num = float(parts[0]) * 800
            elif len(parts) == 2:
                # Fraction case like "1 1/8 Mile"
                whole = float(parts[0])
                frac_parts = parts[1].split('/')
                if len(frac_parts) == 2:
                    fraction = float(frac_parts[0]) / float(frac_parts[1])
                    distance_num = (whole + fraction) * 800
                else:
                    distance_num = whole * 800
            else:
                distance_num = 800  # Default to 1 mile
        else:
            distance_num = float(distance_str)
    except (ValueError, IndexError):
        distance_num = 550  # Default fallback
    features["distance_id"] = distance_num
    
    # Extract total pool amount (estimate)
    total_pool = 0.0
    for pool in race_detail.get("pools", []):
        if pool.get("poolTypeCode", "").upper() in ("WN", "WIN"):
            total_pool = float(pool.get("totalPool", {}).get("amount", 96577))
            break
    features["total_pool"] = total_pool
    
    features["harville_log"] = log(harville_payout)
    
    # Handle post_time from NYRA API
    post_time_str = race_detail.get("postTime", "")
    try:
        if "T" in post_time_str:
            # ISO format like "2024-07-18T14:30:00"
            time_part = post_time_str.split("T")[1]
            post_hour = int(time_part.split(":")[0])
        else:
            post_hour = 14
    except:
        post_hour = 14
    features["post_hour"] = float(post_hour)
    
    # Get raw odds from odds_map for all horses and this combination
    all_odds = []
    for runner in runners:
        prog_num = str(runner.get("programNumber"))
        all_odds.append(odds_map.get(prog_num, 9900))
    
    winner_odds = []
    for i in combo_indices:
        prog_num = str(runners[i].get("programNumber"))
        winner_odds.append(odds_map.get(prog_num, 9900))
    
    features["favorite_odds"] = min(winner_odds)
    features["longshot_odds"] = max(winner_odds)
    features["odds_range"] = features["longshot_odds"] - features["favorite_odds"]
    features["min_prob"] = min([prob1, prob2, prob3, prob4])
    features["max_prob"] = max([prob1, prob2, prob3, prob4])
    features["prob_variance"] = np.var([prob1, prob2, prob3, prob4])
    features["prob_product"] = prob1 * prob2 * prob3 * prob4
    features["prob_sum"] = prob1 + prob2 + prob3 + prob4
    features["prob_entropy"] = -sum(p * log(p + 1e-10) for p in [prob1, prob2, prob3, prob4])
    
    # Field statistics
    features["avg_field_odds"] = np.mean(all_odds)
    features["odds_std"] = np.std(all_odds)
    
    features["pool_per_runner"] = features["total_pool"] / features["number_of_runners"]
    features["purse_per_runner"] = features["purse_usa"] / features["number_of_runners"]
    
    # Default categorical features (can be enhanced with more NYRA data)
    surface = race_detail.get("surface", "T")
    course_type = race_detail.get("courseType", "T")
    track_condition = race_detail.get("trackCondition", "FM")
    
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
    """Make prediction using a loaded XGBoost model"""
    
    # Set categorical features
    for feat in model_features:
        if feat.startswith(('surface_', 'course_type_', 'track_condition_')):
            features[feat] = 0
    
    # Set active categorical features
    features[f"surface_{surface}"] = 1
    features[f"course_type_{course_type}"] = 1  
    features[f"track_condition_{track_condition}"] = 1
    
    # Build feature vector in correct order
    feature_vector = []
    for feat in model_features:
        feature_vector.append(features.get(feat, 0.0))
    
    # Make prediction
    X = np.array([feature_vector])
    dmatrix = xgb.DMatrix(X, feature_names=model_features)
    log_ratio_pred = model.predict(dmatrix)[0]
    
    return log_ratio_pred

def analyze_race_nyra(race_detail, runners, win_pct, odds_map, model_path, top_n, sort_by="jointProb", threads=None):
    """Analyze superfecta combinations for the race with optimization"""
    print("Analyzing superfecta combinations...")

    model, model_features = load_model(model_path, threads=threads)
    print(f"Using inference threads={threads or max(1, os.cpu_count() or 1)}")
    
    # Convert win percentages to probabilities list
    probs = []
    for runner in runners:
        prog_num = str(runner.get("programNumber"))
        prob = win_pct.get(prog_num, 0.0)
        probs.append(prob)
    
    # STEP 1: Calculate Harville probabilities for ALL combinations (fast)
    print("Step 1: Calculating Harville probabilities for all combinations...")
    horse_indices = list(range(len(runners)))
    harville_results = []
    
    combo_count = 0
    for combo_indices in permutations(horse_indices, 4):
        combo_count += 1
        
        # Get probabilities for this combination
        prob1 = probs[combo_indices[0]]
        prob2 = probs[combo_indices[1]] 
        prob3 = probs[combo_indices[2]]
        prob4 = probs[combo_indices[3]]
        
        # Calculate Harville joint probability
        harville_joint_prob = calc_harville(prob1, prob2, prob3, prob4)
        
        if not pd.isna(harville_joint_prob):
            harville_results.append({
                "combo_indices": combo_indices,
                "jointProb": harville_joint_prob,
                "harville_payout": 1.0 / harville_joint_prob
            })
        
        if combo_count % 1000 == 0:
            print(f"Processed {combo_count} Harville calculations...")
    
    # STEP 2: Sort by Harville probability and take top N for model prediction
    harville_results.sort(key=lambda x: x['jointProb'], reverse=True)
    top_harville = harville_results[:top_n]
    
    print(f"Step 2: Running top {len(top_harville)} combinations through XGBoost model...")
    
    # STEP 3: Run only top combinations through the expensive model
    results = []
    
    for i, harville_result in enumerate(top_harville):
        combo_indices = harville_result["combo_indices"]
        
        # Build features for this combination
        feature_result = build_features(combo_indices, probs, race_detail, runners, odds_map)
        if feature_result is None:
            continue
            
        features, harville_joint_prob, harville_payout, surface, course_type, track_condition = feature_result
        
        # Make prediction
        log_ratio_pred = make_prediction(features, surface, course_type, track_condition, model, model_features)
        
        # Calculate predicted payout
        predicted_payout = harville_payout * np.exp(log_ratio_pred)
        
        # Get raw odds from odds_map for each horse
        h1_prog = str(runners[combo_indices[0]]['programNumber'])
        h2_prog = str(runners[combo_indices[1]]['programNumber'])
        h3_prog = str(runners[combo_indices[2]]['programNumber'])
        h4_prog = str(runners[combo_indices[3]]['programNumber'])
        
        results.append({
            "combo": "-".join([str(runners[i]['programNumber']) for i in combo_indices]),
            "h1": odds_map.get(h1_prog, 9900),
            "h2": odds_map.get(h2_prog, 9900),
            "h3": odds_map.get(h3_prog, 9900),
            "h4": odds_map.get(h4_prog, 9900),
            "winPct1": probs[combo_indices[0]] * 100,
            "winPct2": probs[combo_indices[1]] * 100,
            "winPct3": probs[combo_indices[2]] * 100,
            "winPct4": probs[combo_indices[3]] * 100,
            "jointProb": harville_joint_prob,
            "jointProbPct": harville_joint_prob * 100,
            "harville_payout": harville_payout,
            "predicted_log_ratio": log_ratio_pred,
            "predicted_payout": predicted_payout,
            "multiplier": np.exp(log_ratio_pred)
        })
        
        if (i + 1) % 50 == 0:
            print(f"Processed {i + 1} model predictions...")
    
    # Convert to DataFrame and add EV columns
    results_df = pd.DataFrame(results)
    if results_df.empty:
        raise SystemExit("No modeled combinations survived feature generation for the current race.")
    results_df = add_ev_metrics(results_df)

    if sort_by == "ev":
        results_df = results_df.sort_values(['ev_profit_1', 'jointProb'], ascending=[False, False])
    else:
        results_df = results_df.sort_values('jointProb', ascending=False)

    results_df = results_df.reset_index(drop=True)
    results_df['rank'] = range(1, len(results_df) + 1)
    
    return results_df

def save_results(results_df, output_path, race_detail):
    """Save results to CSV"""
    print(f"Saving results to {output_path}...")
    
    # Reorder columns to match requested format
    column_order = [
        "combo", "h1", "h2", "h3", "h4", 
        "winPct1", "winPct2", "winPct3", "winPct4", 
        "jointProb", "jointProbPct",
        "harville_payout", "predicted_log_ratio", "predicted_payout", "adj_predicted_payout",
        "expected_return_1", "ev_profit_1", "ev_roi_pct", "full_kelly_frac",
        "multiplier", "value_rank", "rank"
    ]
    
    output_df = results_df[column_order].copy()
    
    # Round numerical columns for readability
    percentage_columns = ["winPct1", "winPct2", "winPct3", "winPct4", "jointProbPct"]
    for col in percentage_columns:
        output_df[col] = output_df[col].round(6)
    
    other_numeric_columns = ["jointProb", "harville_payout", "predicted_log_ratio", "predicted_payout", "adj_predicted_payout", "expected_return_1", "ev_profit_1", "ev_roi_pct", "full_kelly_frac", "multiplier"]
    for col in other_numeric_columns:
        output_df[col] = output_df[col].round(8)
    
    # Save results
    output_df.to_csv(output_path, index=False)
    
    # Create summary
    summary_path = output_path.replace(".csv", "_summary.txt")
    with open(summary_path, "w") as f:
        f.write("=== NYRA RACE PREDICTION SUMMARY ===\n\n")
        f.write(f"Race: {race_detail['raceMeetingName']} Race #{race_detail['raceNumber']}\n")
        f.write(f"Post Time: {race_detail['postTime']}\n")
        f.write(f"Total combinations analyzed: {len(results_df):,}\n")
        f.write(f"Most likely combination probability: {results_df['jointProbPct'].max():.4f}%\n")
        f.write(f"Highest predicted payout: ${results_df['predicted_payout'].max():,.2f}\n")
        f.write(f"Average predicted payout: ${results_df['predicted_payout'].mean():,.2f}\n")
    
    print(f"Summary saved to {summary_path}")

def main():
    setup_logging()
    args = parse_args()
    
    try:
        # If specific race ID provided, use it
        if args.race_id:
            race_id = args.race_id
            logging.info("Using provided race ID: %s", race_id)
        else:
            # Interactive selection
            logging.info("Fetching today's cards…")
            cards = list_cards()
            if not cards:
                logging.error("No cards available today. Exiting.")
                return

            selected_card = choose_from_list(
                cards,
                lambda c: f"{c['cardName']} on {c['cardDate']} ({len(c['cardRaceNumbers'])} races)"
            )
            logging.info("Selected card %r", selected_card["cardName"])

            races = list_races([selected_card["cardId"]])
            if not races:
                logging.error("No races found on that card. Exiting.")
                return

            selected_race = choose_from_list(
                races,
                lambda r: f"Race #{r['raceNumber']} at {r['raceMeetingName']} on {r['postTime'][:10]} "
                          f"({r['numberOfRunners']} runners)"
            )
            race_id = selected_race["raceId"]
            logging.info("Selected raceId %s", race_id)

        # Get race details
        details = get_race_detail(race_id)
        if not details:
            logging.error("Failed to fetch race details. Exiting.")
            return
        race_detail = details[0]

        # Filter active runners
        active_runners = [r for r in race_detail["runners"] if r.get("runnerStatus") == 1]
        if not active_runners:
            logging.error("No active runners. Exiting.")
            return

        # Get win pool
        win_pool = fetch_win_pool(race_detail)
        if not win_pool:
            logging.error("No WIN pool found. Exiting.")
            return
        pool_id = win_pool["poolId"]
        logging.info("Found WIN poolId %s", pool_id)

        # Get probables
        pools = get_probables([pool_id])
        pool_info = next(p for p in pools if p["poolId"] == pool_id)

        # Compute win percentages and odds
        win_pct, odds_map = compute_win_percentages_and_odds(active_runners, pool_info["probables"])
        if not win_pct:
            return

        # Analyze race
        results_df = analyze_race_nyra(
            race_detail,
            active_runners,
            win_pct,
            odds_map,
            args.model,
            args.top_combinations,
            sort_by=args.sort_by,
            threads=args.threads,
        )
        
        # Save results
        save_results(results_df, args.output, race_detail)
        
        # Print quick summary to console
        print(f"\n=== QUICK SUMMARY ===")
        print(f"✅ Analyzed superfecta combinations for {race_detail['raceMeetingName']} Race #{race_detail['raceNumber']}")
        print(f"🎯 Most likely combination probability: {results_df['jointProbPct'].max():.4f}%")
        print(f"📊 Results saved to: {args.output}")
        
        # Show top 5 combinations
        label = "TOP 5 EV COMBINATIONS" if args.sort_by == "ev" else "TOP 5 MOST LIKELY COMBINATIONS"
        print(f"\n=== {label} ===")
        for _, row in results_df.head(5).iterrows():
            print(f"{row['rank']}. {row['combo']} - Probability: {row['jointProbPct']:.4f}%")
            print(f"   Harville: ${row['harville_payout']:.2f}, Predicted: ${row['predicted_payout']:.2f}, EV ROI: {row['ev_roi_pct']:.2f}%")
            print(f"   Multiplier: {row['multiplier']:.2f}x | Value rank: {int(row['value_rank'])}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())