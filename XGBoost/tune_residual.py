#!/usr/bin/env python3
"""
tune_residual.py

Advanced hyperparameter optimization for superfecta prediction with anti-overfitting strategies.

This script implements sophisticated techniques to find optimal XGBoost parameters while
preventing overfitting, particularly important for time-series financial data like
horse racing where future performance differs from historical patterns.

Key Anti-Overfitting Strategies:
1. Time-based cross-validation (no future data leakage)
2. Conservative parameter ranges for major tracks
3. Feature selection to reduce dimensionality
4. Regularization penalty for overfitting gaps
5. Categorical feature consolidation
6. Outlier capping to reduce noise

The script adapts its optimization strategy based on dataset characteristics,
applying stronger regularization for major tracks where overfitting is more common
due to more sophisticated betting markets.

Theoretical Foundation:
- Uses Optuna's Tree-structured Parzen Estimator (TPE) for efficient search
- Implements temporal validation to simulate real-world deployment
- Balances model complexity with generalization ability
- Monitors overfitting gap as key metric

Author: Cole Bender
Version: 3.0
Last Updated: 7/21/2025
"""

import sys
import os
import pickle
import optuna
import xgboost as xgb
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt
import argparse
import warnings
from train_test_residual import load_and_pivot, compute_features_targets

# Suppress warnings for cleaner output during optimization
warnings.filterwarnings("ignore", message=".*num_round.*not used.*")
warnings.filterwarnings("ignore", category=UserWarning, module="xgboost")


def parse_args():
    """
    Parse command line arguments for hyperparameter tuning.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Optimize XGBoost hyperparameters with anti-overfitting strategies",
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
        help="Sample N races for faster development (None = use all data)"
    )
    
    parser.add_argument(
        "--trials", 
        type=int, 
        default=100, 
        help="Number of optimization trials to run"
    )
    
    parser.add_argument(
        "--major-tracks-only", 
        action="store_true", 
        help="Apply conservative tuning for major tracks (stronger regularization)"
    )

    parser.add_argument(
        "--threads",
        type=int,
        default=max(1, os.cpu_count() or 1),
        help="Number of CPU threads per XGBoost training job"
    )

    parser.add_argument(
        "--parallel-trials",
        type=int,
        default=1,
        help="Number of Optuna trials to run in parallel"
    )

    parser.add_argument(
        "--tree-method",
        default="hist",
        choices=["auto", "exact", "approx", "hist"],
        help="XGBoost tree construction method"
    )
    
    return parser.parse_args()


def preprocess_for_generalization(df):
    """
    Apply preprocessing strategies to improve model generalization.
    
    This function reduces overfitting risk by:
    1. Consolidating rare categorical values
    2. Capping extreme numerical values
    3. Reducing noise in the feature space
    
    Args:
        df (pd.DataFrame): Raw race data
        
    Returns:
        pd.DataFrame: Preprocessed data with improved generalization properties
    """
    print("Applying generalization preprocessing...")
    df_processed = df.copy()
    
    # 1. Consolidate rare categorical values to reduce overfitting
    # Values appearing less than 100 times become 'other'
    categorical_cols = ['course_type', 'track_condition', 'surface']
    for col in categorical_cols:
        if col in df_processed.columns:
            value_counts = df_processed[col].value_counts()
            rare_values = value_counts[value_counts < 100].index
            
            if len(rare_values) > 0:
                print(f"  Consolidating {len(rare_values)} rare values in {col}")
                df_processed[col] = df_processed[col].replace(rare_values, 'other')
    
    # 2. Cap extreme values to reduce outlier influence
    # Use 99th and 1st percentiles as caps
    numeric_cols = ['odds_range', 'longshot_odds', 'favorite_odds', 
                   'total_pool', 'purse_usa', 'avg_field_odds']
    
    for col in numeric_cols:
        if col in df_processed.columns:
            q99 = df_processed[col].quantile(0.99)
            q01 = df_processed[col].quantile(0.01)
            
            # Count outliers being capped
            outliers = ((df_processed[col] > q99) | (df_processed[col] < q01)).sum()
            if outliers > 0:
                print(f"  Capping {outliers} outliers in {col}")
                df_processed[col] = df_processed[col].clip(lower=q01, upper=q99)
    
    print(f"✅ Preprocessing complete")
    return df_processed


def select_robust_features(X, y, feature_names, top_n=15, verbose=False, threads=1, tree_method="hist"):
    """
    Select the most important features to reduce overfitting risk.
    
    Uses a quick XGBoost model to rank features by importance, then selects
    the top N features. This reduces model complexity and improves generalization.
    
    Args:
        X (np.ndarray): Feature matrix
        y (np.ndarray): Target vector
        feature_names (list): Names of features
        top_n (int): Number of top features to select
        verbose (bool): Print feature selection details
        
    Returns:
        tuple: (feature_indices, selected_feature_names)
    """
    if verbose:
        print(f"Selecting top {top_n} features from {len(feature_names)} candidates...")
    
    # Quick feature importance ranking using XGBoost
    dtrain = xgb.DMatrix(X, label=y, feature_names=feature_names)
    
    # Simple model for feature ranking
    params = {
        "max_depth": 4,
        "eta": 0.1,
        "objective": "reg:squarederror",
        "seed": 42,
        "tree_method": tree_method,
        "nthread": threads,
    }
    
    model = xgb.train(params, dtrain, num_boost_round=50, verbose_eval=False)
    importance = model.get_score(importance_type="gain")
    
    # Sort features by importance and select top N
    sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    selected_features = [feat for feat, _ in sorted_features[:top_n]]
    
    if verbose:
        print(f"Selected top {len(selected_features)} features:")
        for i, (feat, score) in enumerate(sorted_features[:top_n]):
            print(f"  {i+1:2d}. {feat:<25} {score:.0f}")
    
    # Get indices of selected features
    feature_indices = [i for i, feat in enumerate(feature_names) if feat in selected_features]
    
    return feature_indices, selected_features


def time_based_cv_splits(df, n_splits=5, verbose=False):
    """
    Create time-based cross-validation splits to prevent data leakage.
    
    Traditional random CV can leak future information into training, which
    is unrealistic for time-series data. This function creates progressive
    time-based splits that simulate real-world deployment.
    
    Args:
        df (pd.DataFrame): Dataset with race_date column
        n_splits (int): Number of CV splits to create
        verbose (bool): Print split details
        
    Returns:
        list: List of (train_indices, validation_indices) tuples
    """
    # Sort by date to ensure temporal order
    df_sorted = df.sort_values('race_date').reset_index(drop=True)
    n = len(df_sorted)
    
    splits = []
    
    for i in range(n_splits):
        # Progressive time-based splits
        # Each split uses more historical data for training
        train_size = 0.6 + i * 0.06  # 60%, 66%, 72%, 78%, 84%
        val_size = 0.15              # Always 15% for validation
        
        train_end = int(n * train_size)
        val_start = train_end
        val_end = min(int(n * (train_size + val_size)), n)
        
        # Skip if validation set would be empty
        if val_end <= val_start:
            continue
            
        train_idx = df_sorted.index[:train_end].tolist()
        val_idx = df_sorted.index[val_start:val_end].tolist()
        
        splits.append((train_idx, val_idx))
    
    if verbose:
        print(f"Created {len(splits)} time-based CV splits")
        for i, (train_idx, val_idx) in enumerate(splits):
            train_start = df_sorted.iloc[train_idx[0]]['race_date'].date()
            train_end = df_sorted.iloc[train_idx[-1]]['race_date'].date()
            val_start = df_sorted.iloc[val_idx[0]]['race_date'].date()
            val_end = df_sorted.iloc[val_idx[-1]]['race_date'].date()
            print(f"  Split {i+1}: Train {train_start} to {train_end}, "
                  f"Val {val_start} to {val_end}")
    
    return splits


def objective_anti_overfitting(trial, X, y, feature_names, df, is_major_tracks=False, threads=1, tree_method="hist"):
    """
    Objective function for hyperparameter optimization with overfitting prevention.
    
    This function defines the search space and evaluation strategy for finding
    optimal XGBoost parameters. It adapts the parameter ranges based on dataset
    characteristics and includes penalties for overfitting.
    
    Args:
        trial (optuna.Trial): Optuna trial object
        X (np.ndarray): Feature matrix
        y (np.ndarray): Target vector
        feature_names (list): Feature names
        df (pd.DataFrame): Full dataset for time-based splitting
        is_major_tracks (bool): Whether to use conservative parameters
        
    Returns:
        float: Cross-validation score to minimize (lower is better)
    """
    # Adaptive parameter ranges based on dataset characteristics
    if is_major_tracks:
        # Conservative parameters for major tracks (sophisticated betting markets)
        print(f"Trial {trial.number}: Using conservative major tracks parameters")
        params = {
            "max_depth":        trial.suggest_int("max_depth", 3, 4),           # Shallow trees
            "eta":              trial.suggest_float("eta", 0.01, 0.05, log=True), # Slow learning
            "subsample":        trial.suggest_float("subsample", 0.6, 0.8),      # More sampling
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 0.8), # Fewer features
            "gamma":            trial.suggest_float("gamma", 0.5, 2.0),          # Higher min split loss
            "min_child_weight": trial.suggest_int("min_child_weight", 20, 40),   # Larger leaves
            "reg_alpha":        trial.suggest_float("reg_alpha", 2.0, 5.0),      # Strong L1 reg
            "reg_lambda":       trial.suggest_float("reg_lambda", 3.0, 7.0),     # Strong L2 reg
            "num_round":        trial.suggest_int("num_round", 200, 400),        # Fewer rounds
        }
    else:
        # Standard parameter ranges for all tracks
        print(f"Trial {trial.number}: Using standard parameter ranges")
        params = {
            "max_depth":        trial.suggest_int("max_depth", 4, 6),
            "eta":              trial.suggest_float("eta", 0.02, 0.08, log=True),
            "subsample":        trial.suggest_float("subsample", 0.7, 0.9),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.7, 0.9),
            "gamma":            trial.suggest_float("gamma", 0.0, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 10, 25),
            "reg_alpha":        trial.suggest_float("reg_alpha", 0.5, 3.0),
            "reg_lambda":       trial.suggest_float("reg_lambda", 1.0, 5.0),
            "num_round":        trial.suggest_int("num_round", 300, 600),
        }
    
    # Extract num_round and add fixed parameters
    num_round = params.pop("num_round")
    params.update({
        "objective": "reg:squarederror",
        "eval_metric": "rmse",
        "seed": 42,
        "tree_method": tree_method,
        "nthread": threads,
    })
    
    # Feature selection to reduce overfitting
    top_n_features = 15 if is_major_tracks else 20
    feature_indices, selected_features = select_robust_features(
        X, y, feature_names, top_n=top_n_features,
        threads=threads, tree_method=tree_method,
    )
    
    X_selected = X[:, feature_indices]
    
    # Time-based cross-validation
    cv_splits = time_based_cv_splits(df, n_splits=5)
    cv_scores = []
    overfitting_penalties = []
    
    for fold, (train_idx, val_idx) in enumerate(cv_splits):
        X_train = X_selected[train_idx]
        X_val = X_selected[val_idx]
        y_train = y[train_idx]
        y_val = y[val_idx]
        
        # Create XGBoost datasets
        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=selected_features)
        dval = xgb.DMatrix(X_val, label=y_val, feature_names=selected_features)
        
        # Train with early stopping
        model = xgb.train(
            params=params,
            dtrain=dtrain,
            num_boost_round=num_round,
            evals=[(dval, "val")],
            early_stopping_rounds=15,  # Aggressive early stopping
            verbose_eval=False
        )
        
        # Evaluate on validation set
        y_pred_val = model.predict(dval)
        val_rmse = np.sqrt(mean_squared_error(y_val, y_pred_val))
        cv_scores.append(val_rmse)
        
        # Check for overfitting (train vs validation performance)
        y_pred_train = model.predict(dtrain)
        train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
        overfitting_gap = val_rmse - train_rmse
        
        # Apply penalty if significant overfitting detected
        if overfitting_gap > 0.15:  # If validation RMSE > train RMSE by more than 0.15
            penalty = overfitting_gap * 2  # Penalty proportional to gap
            cv_scores[-1] += penalty
            overfitting_penalties.append(penalty)
        else:
            overfitting_penalties.append(0.0)
    
    # Calculate final cross-validation score
    mean_cv_score = np.mean(cv_scores)
    mean_penalty = np.mean(overfitting_penalties)
    
    # Log trial details for monitoring
    print(f"  CV Score: {mean_cv_score:.4f}, Overfitting Penalty: {mean_penalty:.4f}")
    
    return mean_cv_score


def evaluate_best_params_robust(best_params, X, y, feature_names, df, is_major_tracks=False, threads=1, tree_method="hist"):
    """
    Perform robust evaluation of optimized parameters using temporal train/test split.
    
    This function simulates real-world deployment by training on historical data
    and testing on future data, providing an unbiased estimate of model performance.
    
    Args:
        best_params (dict): Optimized hyperparameters
        X (np.ndarray): Feature matrix
        y (np.ndarray): Target vector
        feature_names (list): Feature names
        df (pd.DataFrame): Full dataset
        is_major_tracks (bool): Whether using major tracks parameters
        
    Returns:
        tuple: (trained_model, evaluation_metrics)
    """
    print(f"\n=== Robust Evaluation of Optimized Parameters ===")
    
    # Time-based train/test split (prevents future data leakage)
    df_sorted = df.sort_values('race_date').reset_index(drop=True)
    split_point = int(len(df_sorted) * 0.75)  # 75% train, 25% test
    
    train_idx = df_sorted.index[:split_point].tolist()
    test_idx = df_sorted.index[split_point:].tolist()
    
    # Display temporal split information
    train_start = df_sorted.iloc[0]['race_date'].date()
    train_end = df_sorted.iloc[split_point-1]['race_date'].date()
    test_start = df_sorted.iloc[split_point]['race_date'].date()
    test_end = df_sorted.iloc[-1]['race_date'].date()
    
    print(f"Training period: {train_start} to {train_end} ({len(train_idx)} races)")
    print(f"Testing period:  {test_start} to {test_end} ({len(test_idx)} races)")
    
    # Feature selection using same strategy as optimization
    top_n_features = 15 if is_major_tracks else 20
    feature_indices, selected_features = select_robust_features(
        X[train_idx], y[train_idx], feature_names, 
        top_n=top_n_features, verbose=True,
        threads=threads, tree_method=tree_method,
    )
    
    # Apply feature selection
    X_train = X[train_idx][:, feature_indices]
    X_test = X[test_idx][:, feature_indices]
    y_train = y[train_idx]
    y_test = y[test_idx]
    
    # Train final model with optimized parameters
    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=selected_features)
    dtest = xgb.DMatrix(X_test, label=y_test, feature_names=selected_features)
    
    # Extract num_round if present, otherwise use default
    num_round = best_params.get("num_round", 300)
    train_params = {k: v for k, v in best_params.items() if k != "num_round"}
    train_params.setdefault("tree_method", tree_method)
    train_params.setdefault("nthread", threads)
    
    model = xgb.train(
        params=train_params,
        dtrain=dtrain,
        num_boost_round=num_round,
        evals=[(dtrain, "train"), (dtest, "test")],
        early_stopping_rounds=15,
        verbose_eval=False
    )
    
    # Comprehensive evaluation
    y_pred_train = model.predict(dtrain)
    y_pred_test = model.predict(dtest)
    
    # Calculate performance metrics
    train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    train_r2 = r2_score(y_train, y_pred_train)
    test_r2 = r2_score(y_test, y_pred_test)
    
    overfitting_gap = test_rmse - train_rmse
    
    # Performance assessment
    print(f"\n📊 Final Model Performance:")
    print(f"  Training RMSE: {train_rmse:.4f}, R²: {train_r2:.4f}")
    print(f"  Testing RMSE:  {test_rmse:.4f}, R²: {test_r2:.4f}")
    print(f"  Overfitting gap: {overfitting_gap:.4f}")
    
    # Generalization assessment
    if overfitting_gap < 0.05:
        print("✅ Excellent generalization - minimal overfitting!")
    elif overfitting_gap < 0.1:
        print("✅ Good generalization - acceptable overfitting")
    elif overfitting_gap < 0.15:
        print("⚠️  Moderate overfitting - consider more regularization")
    else:
        print("🚨 Significant overfitting - model may not generalize well")
    
    # Feature importance for final model
    print(f"\n🎯 Top 10 Most Important Features:")
    importance = model.get_score(importance_type="gain")
    sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    
    for i, (feature, score) in enumerate(sorted_importance[:10]):
        print(f"  {i+1:2d}. {feature:<25} {score:.0f}")
    
    return model, {
        "train_rmse": train_rmse, 
        "test_rmse": test_rmse,
        "train_r2": train_r2, 
        "test_r2": test_r2,
        "overfitting_gap": overfitting_gap,
        "selected_features": selected_features,
        "feature_importance": sorted_importance
    }


def main():
    """
    Main hyperparameter optimization pipeline with comprehensive analysis.
    
    This function orchestrates the complete optimization process:
    1. Data loading and preprocessing
    2. Anti-overfitting hyperparameter search
    3. Robust evaluation with temporal validation
    4. Model and results saving
    
    Returns:
        None
    """
    args = parse_args()
    
    # Generate unique identifier for this optimization run
    sample_tag = f"sample{args.sample}" if args.sample else "full_anti_overfit"
    if args.major_tracks_only:
        sample_tag += "_major_tracks"
    
    data_file = f"anti_overfit_data_{sample_tag}.pkl"
    
    print("=== ANTI-OVERFITTING HYPERPARAMETER OPTIMIZATION ===\n")
    
    # Step 1: Load or create preprocessed data
    if os.path.exists(data_file):
        print(f"📁 Loading precomputed data from {data_file}...")
        with open(data_file, "rb") as f:
            df, X, y, feature_cols = pickle.load(f)
        print("✅ Data loaded successfully")
    else:
        print("⏳ Loading and processing raw data...")
        
        # Load raw data
        df = load_and_pivot(args.csv, sample_size=args.sample)
        if df.empty:
            print("❌ No valid races found. Please check your data file.")
            sys.exit(1)
        
        # Apply preprocessing for better generalization
        df = preprocess_for_generalization(df)
        
        # Feature engineering
        df, X, y, feature_cols = compute_features_targets(df)
        
        # Cache processed data for future runs
        with open(data_file, "wb") as f:
            pickle.dump((df, X, y, feature_cols), f)
        print(f"✅ Processed data saved to {data_file}")
    
    # Dataset summary
    print(f"\n📊 Dataset Summary:")
    print(f"  Races: {X.shape[0]:,}")
    print(f"  Features: {X.shape[1]:,}")
    print(f"  Date range: {df['race_date'].min().date()} to {df['race_date'].max().date()}")
    print(f"  Major tracks mode: {args.major_tracks_only}")
    
    # Step 2: Set up optimization study
    study_name = f"anti_overfit_{sample_tag}"
    study = optuna.create_study(
        direction="minimize",  # Minimize cross-validation RMSE
        sampler=optuna.samplers.TPESampler(seed=42),  # Tree-structured Parzen Estimator
        study_name=study_name,
        storage=f"sqlite:///anti_overfit_tuning.db",  # Persistent storage
        load_if_exists=True,  # Resume if study exists
    )
    
    print(f"\n🔍 Starting hyperparameter optimization...")
    print(f"  Strategy: {'Conservative (Major Tracks)' if args.major_tracks_only else 'Standard'}")
    print(f"  Trials: {args.trials}")
    print(f"  CV Strategy: Time-based (no future leakage)")
    print(f"  Overfitting penalty: Enabled")
    print(f"  Tree method: {args.tree_method}")
    print(f"  Threads per trial: {args.threads}")
    print(f"  Parallel trials: {args.parallel_trials}")
    
    # Step 3: Run optimization
    try:
        study.optimize(
            lambda trial: objective_anti_overfitting(
                trial, X, y, feature_cols, df, args.major_tracks_only,
                threads=args.threads, tree_method=args.tree_method,
            ),
            n_trials=args.trials,
            n_jobs=args.parallel_trials,
            show_progress_bar=True
        )
    except KeyboardInterrupt:
        print("\n⚠️  Optimization interrupted by user")
    
    # Step 4: Display optimization results
    print(f"\n🏆 Optimization Results:")
    print(f"  Best CV RMSE: {study.best_value:.4f}")
    print(f"  Total trials: {len(study.trials)}")
    print(f"  Best parameters:")
    
    for key, value in study.best_params.items():
        if isinstance(value, float):
            print(f"    {key}: {value:.6f}")
        else:
            print(f"    {key}: {value}")
    
    # Step 5: Robust evaluation with temporal validation
    model, eval_metrics = evaluate_best_params_robust(
        study.best_params, X, y, feature_cols, df, args.major_tracks_only,
        threads=args.threads, tree_method=args.tree_method,
    )
    
    # Step 6: Save results and model
    results_filename = f"best_params_anti_overfit_{sample_tag}.pkl"
    model_filename = f"anti_overfit_model_{sample_tag}.json"
    
    # Save optimization results
    results_data = {
        "best_params": study.best_params,
        "best_value": study.best_value,
        "eval_metrics": eval_metrics,
        "selected_features": eval_metrics["selected_features"],
        "optimization_summary": {
            "total_trials": len(study.trials),
            "dataset_size": X.shape[0],
            "feature_count": X.shape[1],
            "major_tracks_mode": args.major_tracks_only,
            "sample_size": args.sample
        }
    }
    
    with open(results_filename, "wb") as f:
        pickle.dump(results_data, f)
    
    # Save trained model
    model.save_model(model_filename)
    
    print(f"\n💾 Results and Model Saved:")
    print(f"  Parameters: {results_filename}")
    print(f"  Model: {model_filename}")
    
    # Step 7: Final summary and recommendations
    print(f"\n🎯 Final Optimization Summary:")
    print(f"  ✅ Completed {len(study.trials)} trials")
    print(f"  📈 Best CV Score: {study.best_value:.4f}")
    print(f"  🔬 Test RMSE: {eval_metrics['test_rmse']:.4f}")
    print(f"  📊 Overfitting Gap: {eval_metrics['overfitting_gap']:.4f}")
    
    # Performance assessment
    gap = eval_metrics['overfitting_gap']
    if gap < 0.05:
        assessment = "🌟 Excellent - Ready for production"
    elif gap < 0.1:
        assessment = "✅ Good - Suitable for deployment"
    elif gap < 0.15:
        assessment = "⚠️  Moderate - Consider more data or regularization"
    else:
        assessment = "🚨 High - Needs more regularization"
    
    print(f"  🎭 Generalization: {assessment}")
    
    # Feature selection summary
    selected_count = len(eval_metrics["selected_features"])
    total_count = len(feature_cols)
    print(f"  🎯 Features Used: {selected_count}/{total_count} "
          f"({selected_count/total_count*100:.1f}%)")
    
    print(f"\n🚀 Model ready for superfecta predictions!")
    
    # Optional: Display optimization history plot
    if len(study.trials) > 1:
        try:
            print(f"\n📈 Generating optimization history plot...")
            
            # Extract trial values
            trial_values = [trial.value for trial in study.trials if trial.value is not None]
            
            if len(trial_values) > 0:
                plt.figure(figsize=(12, 6))
                
                # Plot trial history
                plt.subplot(1, 2, 1)
                plt.plot(trial_values, 'b-', alpha=0.7)
                plt.axhline(y=study.best_value, color='r', linestyle='--', 
                           label=f'Best: {study.best_value:.4f}')
                plt.xlabel('Trial')
                plt.ylabel('CV RMSE')
                plt.title('Optimization Progress')
                plt.legend()
                plt.grid(True, alpha=0.3)
                
                # Plot value distribution
                plt.subplot(1, 2, 2)
                plt.hist(trial_values, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
                plt.axvline(x=study.best_value, color='r', linestyle='--', 
                           label=f'Best: {study.best_value:.4f}')
                plt.xlabel('CV RMSE')
                plt.ylabel('Frequency')
                plt.title('Score Distribution')
                plt.legend()
                plt.grid(True, alpha=0.3)
                
                plt.tight_layout()
                
                # Save plot
                plot_filename = f"optimization_history_{sample_tag}.png"
                plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
                print(f"📊 Optimization plot saved to {plot_filename}")
                
                plt.show()
                
        except Exception as e:
            print(f"⚠️  Could not create optimization plot: {e}")


if __name__ == "__main__":
    main()