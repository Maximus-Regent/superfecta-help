#!/usr/bin/env python3
"""
ab_downstream_comparison.py — Honest A/B comparison of baseline vs enriched
residual payout models through the downstream EV ticket engine.

Tests whether the enriched horse-history model's improved payout prediction
accuracy translates to better downstream betting decisions.

Approach:
  1. Load 14years_major_tracks.csv, reproduce chronological 75/25 split.
  2. Build race-level features matching the training pipeline.
  3. For the enriched path, merge horse-history features from cache.
  4. Score each winning combo with both pre-trained models.
  5. Apply the EV ticket engine thresholds to both predictions.
  6. Compare: prediction accuracy, EV filter pass rates, implied ROI.

Limitation (stated clearly):
  This compares predictions on the *actual winning combos* only. It does NOT
  test whether the enriched model changes the *ranking* of non-winning combos.
  A full combo-level comparison would require building horse features for every
  horse in every race, which is a larger integration.

Output: ab_downstream_comparison_results.json + printed summary.
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from math import log
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent

# ── EV engine constants (match ev_ticket_engine.py defaults) ────────
PAYOUT_HAIRCUT = 0.75
MIN_EV_ROI = 0.15
MIN_PROB = 0.0005
PAYOUT_UNIT = 1.0


# ═══════════════════════════════════════════════════════════════════
# DATA LOADING (mirrors train_test_residual.py logic)
# ═══════════════════════════════════════════════════════════════════

def safe_float(value, default=np.nan):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if np.isfinite(result) else default


def moneyline_to_prob(odds: float) -> float:
    odds = safe_float(odds)
    if not np.isfinite(odds):
        return np.nan
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return (-odds) / (-odds + 100.0)


def load_and_build(csv_path: Path) -> pd.DataFrame:
    """Load horse-level CSV → race-level DataFrame with features + targets."""
    print(f"Loading {csv_path.name} ...")
    df = pd.read_csv(
        csv_path,
        parse_dates=["race_date"],
        dtype={"post_time": str, "program_number": str, "registration_number": str},
    )
    df["post_time"] = df["post_time"].fillna("").str.extract(r"(\d+)$")[0].str[-4:]
    df["post_time"] = pd.to_datetime(df["post_time"], format="%H%M", errors="coerce")
    df = df[df["scratch_indicator"].fillna("N") != "Y"]

    races_with_winners = (
        df[df["winning_numbers"].notna()]
        [["track_id", "race_date", "race_number"]]
        .drop_duplicates()
    )
    keep = set(zip(races_with_winners.track_id,
                   races_with_winners.race_date,
                   races_with_winners.race_number))

    rows = []
    for (track, date, rnum), grp in df.groupby(["track_id", "race_date", "race_number"]):
        if (track, date, rnum) not in keep:
            continue
        wrows = grp[grp["winning_numbers"].notna()]
        if wrows.empty:
            continue
        wi = wrows.iloc[0]
        wp = [str(x).strip() for x in str(wi["winning_numbers"]).split("-") if str(x).strip()]
        if len(wp) != 4:
            continue

        payoff = safe_float(wi.get("payoff_amount"))
        tickets = safe_float(wi.get("number_of_tickets_bet"))
        if not np.isfinite(payoff) or payoff <= 0 or not np.isfinite(tickets) or tickets <= 0:
            continue

        horses = []
        for _, h in grp.iterrows():
            odds = safe_float(h.get("odds"))
            if np.isfinite(odds):
                rp = moneyline_to_prob(odds)
                if np.isfinite(rp) and rp > 0:
                    horses.append({
                        "prog": str(h["program_number"]).strip(),
                        "reg": str(h.get("registration_number", "")).strip(),
                        "odds": odds,
                        "rp": rp,
                    })
        if len(horses) < 4:
            continue

        tot = sum(h["rp"] for h in horses)
        if tot <= 0:
            continue
        prog_prob = {h["prog"]: h["rp"] / tot for h in horses}
        prog_odds = {h["prog"]: h["odds"] for h in horses}
        prog_reg = {h["prog"]: h["reg"] for h in horses}

        wprobs = [prog_prob.get(p) for p in wp]
        wodds = [prog_odds.get(p) for p in wp]
        wregs = [prog_reg.get(p, "") for p in wp]
        if any(v is None for v in wprobs) or any(v is None for v in wodds):
            continue

        p1, p2, p3, p4 = wprobs
        d1 = 1 - p1
        d2 = d1 - p2
        d3 = d2 - p3
        if d1 <= 0 or d2 <= 0 or d3 <= 0:
            continue
        joint = p1 * (p2 / d1) * (p3 / d2) * (p4 / d3)
        if joint <= 0:
            continue
        h_pay = 1.0 / joint
        actual_payout = float(payoff) * (100.0 / float(tickets))
        lr = log(actual_payout / h_pay)

        all_odds = [h["odds"] for h in horses]
        first = grp.iloc[0]
        post_hour = first["post_time"].hour if pd.notna(first.get("post_time")) else 14
        fs = len(grp)

        rows.append({
            "track_id": track, "race_date": date, "race_number": rnum,
            "prob1": p1, "prob2": p2, "prob3": p3, "prob4": p4,
            "odds1": wodds[0], "odds2": wodds[1], "odds3": wodds[2], "odds4": wodds[3],
            "reg1": wregs[0], "reg2": wregs[1], "reg3": wregs[2], "reg4": wregs[3],
            "number_of_runners": safe_float(first.get("number_of_runners"), default=fs),
            "field_size": fs,
            "purse_usa": safe_float(first.get("purse_usa"), default=0.0),
            "distance_id": safe_float(first.get("distance_id"), default=0.0),
            "post_hour": float(post_hour),
            "total_pool": safe_float(first.get("total_pool"), default=0.0),
            "avg_field_odds": float(np.mean(all_odds)),
            "odds_std": float(np.std(all_odds)) if len(all_odds) > 1 else 0.0,
            "surface": str(first.get("surface", "")).strip(),
            "course_type": str(first.get("course_type", "")).strip(),
            "track_condition": str(first.get("track_condition", "")).strip(),
            "harville_payout": h_pay,
            "actual_payout": actual_payout,
            "joint_prob": joint,
            "log_ratio": lr,
        })

    out = pd.DataFrame(rows).sort_values("race_date").reset_index(drop=True)

    # Remove 3-sigma outliers on log_ratio (same as training)
    mu, sig = out["log_ratio"].mean(), out["log_ratio"].std()
    mask = (out["log_ratio"] >= mu - 3 * sig) & (out["log_ratio"] <= mu + 3 * sig)
    out = out[mask].reset_index(drop=True)

    print(f"  {len(out)} valid races after outlier removal")
    return out


def build_baseline_features(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """Build the ~55-feature matrix matching the baseline model's expectations."""
    eps = 1e-10
    df = df.copy()

    for i in range(1, 5):
        p = df[f"prob{i}"]
        df[f"logit{i}"] = np.where(
            (p > 0) & (p < 1), np.log(p / (1 - p)), 0.0
        )

    df["favorite_odds"] = df[["odds1", "odds2", "odds3", "odds4"]].min(axis=1)
    df["longshot_odds"] = df[["odds1", "odds2", "odds3", "odds4"]].max(axis=1)
    df["odds_range"] = df["longshot_odds"] - df["favorite_odds"]
    df["prob_product"] = df["prob1"] * df["prob2"] * df["prob3"] * df["prob4"]
    df["prob_sum"] = df["prob1"] + df["prob2"] + df["prob3"] + df["prob4"]
    df["min_prob"] = df[["prob1", "prob2", "prob3", "prob4"]].min(axis=1)
    df["max_prob"] = df[["prob1", "prob2", "prob3", "prob4"]].max(axis=1)
    df["prob_variance"] = np.var(
        [df[f"prob{i}"].values for i in range(1, 5)], axis=0
    )
    df["prob_entropy"] = -sum(
        df[f"prob{i}"] * np.log(df[f"prob{i}"] + eps) for i in range(1, 5)
    )
    df["pool_per_runner"] = df["total_pool"] / df["number_of_runners"].replace(0, 1)
    df["purse_per_runner"] = df["purse_usa"] / df["number_of_runners"].replace(0, 1)
    df["harville_log"] = np.log(df["harville_payout"])

    # Categoricals as dummies
    dummies = pd.get_dummies(
        df[["surface", "course_type", "track_condition"]],
        prefix=["surface", "course_type", "track_condition"],
        dummy_na=True,
    )
    df = pd.concat([df, dummies], axis=1)

    feature_cols = (
        [f"logit{i}" for i in range(1, 5)]
        + [f"prob{i}" for i in range(1, 5)]
        + ["number_of_runners", "field_size", "purse_usa", "distance_id",
           "post_hour", "total_pool", "avg_field_odds", "odds_std"]
        + ["favorite_odds", "longshot_odds", "odds_range", "prob_product",
           "prob_sum", "prob_entropy", "min_prob", "max_prob", "pool_per_runner",
           "purse_per_runner", "harville_log", "prob_variance"]
        + list(dummies.columns)
    )

    return df[feature_cols].fillna(0).values, feature_cols, df


def merge_horse_features(df: pd.DataFrame, hf_path: Path) -> tuple[pd.DataFrame, list[str]]:
    """Merge horse-history features for the 4 winners (mirrors training pipeline)."""
    HORSE_COLS = [
        "n_prior_starts", "prior_win_rate", "prior_top3_rate",
        "avg_finish_all", "avg_finish_last5", "days_since_last",
        "avg_prior_purse", "class_change",
        "surface_prior_starts", "surface_win_rate", "surface_avg_finish",
        "distance_prior_starts", "distance_win_rate", "distance_avg_finish",
        "track_prior_starts", "track_win_rate", "track_avg_finish",
    ]

    print(f"Loading horse features from {hf_path.name} ...")
    hf = pd.read_csv(
        hf_path, parse_dates=["race_date"],
        dtype={"program_number": str, "registration_number": str},
    )
    hf["_jk"] = (
        hf["registration_number"].astype(str) + "|"
        + hf["track_id"].astype(str) + "|"
        + hf["race_date"].astype(str) + "|"
        + hf["race_number"].astype(str)
    )
    hf = hf.drop_duplicates(subset="_jk", keep="first")
    hf_lookup = hf.set_index("_jk")[HORSE_COLS]

    new_cols: list[str] = []
    df = df.copy()

    for pos in range(1, 5):
        prefix = f"w{pos}_"
        jk = (
            df[f"reg{pos}"].astype(str) + "|"
            + df["track_id"].astype(str) + "|"
            + df["race_date"].astype(str) + "|"
            + df["race_number"].astype(str)
        )
        matched = hf_lookup.reindex(jk.values)
        for col in HORSE_COLS:
            new_name = f"{prefix}{col}"
            df[new_name] = matched[col].values
            new_cols.append(new_name)

    for col in HORSE_COLS:
        w_cols = [f"w{i}_{col}" for i in range(1, 5)]
        sub = df[w_cols]
        df[f"avg_{col}"] = sub.mean(axis=1)
        df[f"min_{col}"] = sub.min(axis=1)
        df[f"max_{col}"] = sub.max(axis=1)
        new_cols.extend([f"avg_{col}", f"min_{col}", f"max_{col}"])

    df["n_debut_winners"] = sum(
        (df[f"w{i}_n_prior_starts"] == 0).astype(float) for i in range(1, 5)
    )
    new_cols.append("n_debut_winners")

    match_rate = df["w1_n_prior_starts"].notna().mean()
    print(f"  Horse feature match rate: {match_rate:.1%}")
    print(f"  Added {len(new_cols)} horse-history features")

    return df, new_cols


def score_with_model(
    model: xgb.Booster,
    model_feats: list[str],
    df_feats: pd.DataFrame,
    all_feature_cols: list[str],
) -> np.ndarray:
    """Score rows using a pre-trained model, aligning features by name."""
    # Build feature matrix in the order the model expects
    X = np.zeros((len(df_feats), len(model_feats)))
    col_map = {c: i for i, c in enumerate(all_feature_cols)}

    for j, mf in enumerate(model_feats):
        if mf in col_map:
            X[:, j] = df_feats.iloc[:, col_map[mf]].values
        # else: stays 0 (missing feature → 0, same as training fillna(0))

    dm = xgb.DMatrix(X, feature_names=model_feats)
    return model.predict(dm)


def ev_pass(joint_prob: float, predicted_payout: float) -> tuple[bool, float]:
    """Apply the EV engine's core bet/no-bet decision for a single ticket."""
    if joint_prob < MIN_PROB:
        return False, 0.0
    adj = predicted_payout * PAYOUT_HAIRCUT
    gross = adj / PAYOUT_UNIT
    ev_profit = joint_prob * gross - 1.0

    if ev_profit < MIN_EV_ROI:
        return False, 0.0

    # Kelly check (simplified — same as ev_ticket_engine)
    net = gross - 1.0
    if gross < 1.05:
        return False, 0.0
    kelly = (joint_prob * net - (1.0 - joint_prob)) / net
    if kelly <= 0:
        return False, 0.0

    return True, ev_profit


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main() -> None:
    t0 = time.time()

    # ── 1. Load data ────────────────────────────────────────────────
    csv_path = BASE / "14years_major_tracks.csv"
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found"); sys.exit(1)

    races = load_and_build(csv_path)
    print(f"  Date range: {races['race_date'].min().date()} → {races['race_date'].max().date()}")

    # ── 2. Chronological 75/25 split (same as validation) ──────────
    n = len(races)
    split_idx = int(n * 0.75)
    test = races.iloc[split_idx:].copy().reset_index(drop=True)
    split_date = test["race_date"].iloc[0].date()
    print(f"\nChronological split: train {split_idx} races, test {len(test)} races")
    print(f"  Test set starts: {split_date}")

    # ── 3. Load both models ─────────────────────────────────────────
    # Use matched models trained on the SAME dataset (major tracks, 88K races)
    # for a fair apples-to-apples comparison.  The full_data_retrain artifacts
    # use different training sets (552K all-track vs 88K major) and should NOT
    # be compared directly for downstream A/B.
    baseline_path = BASE / "ab_baseline_model.json"
    enriched_path = BASE / "ab_enriched_model.json"

    for p in [baseline_path, enriched_path]:
        if not p.exists():
            print(f"ERROR: {p} not found"); sys.exit(1)

    bl_model = xgb.Booster()
    bl_model.load_model(str(baseline_path))
    bl_feats = bl_model.feature_names
    print(f"\nBaseline model: {len(bl_feats)} features")

    en_model = xgb.Booster()
    en_model.load_model(str(enriched_path))
    en_feats = en_model.feature_names
    print(f"Enriched model: {len(en_feats)} features")

    # ── 4. Build features ───────────────────────────────────────────
    print("\nBuilding baseline features ...")
    X_bl, bl_cols, test_feat = build_baseline_features(test)

    print("Building enriched features ...")
    hf_path = BASE / "horse_features_major_tracks.csv"
    if not hf_path.exists():
        print(f"ERROR: {hf_path} not found"); sys.exit(1)
    test_horse, horse_cols = merge_horse_features(test_feat, hf_path)

    # Combine all feature columns for the enriched path
    all_enriched_cols = bl_cols + horse_cols
    enriched_feat_df = test_horse[all_enriched_cols].fillna(0)

    # ── 5. Score with both models ───────────────────────────────────
    print("\nScoring test set ...")
    bl_preds = score_with_model(bl_model, bl_feats, test_feat[bl_cols].fillna(0), bl_cols)
    en_preds = score_with_model(en_model, en_feats, enriched_feat_df, all_enriched_cols)

    test["bl_log_ratio"] = bl_preds
    test["en_log_ratio"] = en_preds
    test["bl_predicted_payout"] = test["harville_payout"] * np.exp(bl_preds)
    test["en_predicted_payout"] = test["harville_payout"] * np.exp(en_preds)

    # ── 6. Prediction accuracy ──────────────────────────────────────
    actual_lr = test["log_ratio"].values
    actual_pay = test["actual_payout"].values

    def metrics(preds_lr, preds_pay, label):
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        from scipy.stats import pearsonr
        lr_rmse = float(np.sqrt(mean_squared_error(actual_lr, preds_lr)))
        lr_r2 = float(r2_score(actual_lr, preds_lr))
        lr_corr = float(pearsonr(actual_lr, preds_lr)[0])
        pay_rmse = float(np.sqrt(mean_squared_error(actual_pay, preds_pay)))
        pay_mae = float(mean_absolute_error(actual_pay, preds_pay))
        harv_rmse = float(np.sqrt(mean_squared_error(actual_pay, test["harville_payout"].values)))
        payout_imp = (harv_rmse - pay_rmse) / harv_rmse * 100
        return {
            "label": label,
            "log_ratio_rmse": round(lr_rmse, 6),
            "log_ratio_r2": round(lr_r2, 6),
            "log_ratio_corr": round(lr_corr, 6),
            "payout_rmse": round(pay_rmse, 2),
            "payout_mae": round(pay_mae, 2),
            "payout_rmse_improvement_vs_harville_pct": round(payout_imp, 2),
        }

    bl_metrics = metrics(bl_preds, test["bl_predicted_payout"].values, "baseline")
    en_metrics = metrics(en_preds, test["en_predicted_payout"].values, "enriched")

    # ── 7. EV engine pass-through ───────────────────────────────────
    print("\nApplying EV engine thresholds ...")
    bl_bets = []
    en_bets = []

    for i in range(len(test)):
        jp = test.iloc[i]["joint_prob"]
        ap = test.iloc[i]["actual_payout"]
        h_pay = test.iloc[i]["harville_payout"]

        bl_pass, bl_ev = ev_pass(jp, test.iloc[i]["bl_predicted_payout"])
        en_pass, en_ev = ev_pass(jp, test.iloc[i]["en_predicted_payout"])

        bl_bets.append({"pass": bl_pass, "ev": bl_ev, "actual": ap, "cost": 1.0})
        en_bets.append({"pass": en_pass, "ev": en_ev, "actual": ap, "cost": 1.0})

    test["bl_ev_pass"] = [b["pass"] for b in bl_bets]
    test["en_ev_pass"] = [b["pass"] for b in en_bets]

    n_test = len(test)

    def ev_summary(bets, label):
        passed = [b for b in bets if b["pass"]]
        n_pass = len(passed)
        if n_pass == 0:
            return {
                "label": label,
                "ev_pass_count": 0,
                "ev_pass_pct": 0.0,
                "note": "No winning combos passed the EV filter — this is expected "
                        "because the EV engine is very conservative (25% haircut + "
                        "15% min ROI + Kelly). Most winning combos do NOT pass.",
            }
        total_cost = sum(b["cost"] for b in passed)
        total_return = sum(b["actual"] for b in passed)
        roi = (total_return - total_cost) / total_cost * 100
        avg_ev = np.mean([b["ev"] for b in passed])
        return {
            "label": label,
            "ev_pass_count": n_pass,
            "ev_pass_pct": round(n_pass / n_test * 100, 4),
            "total_wagered": round(total_cost, 2),
            "total_returned": round(total_return, 2),
            "implied_flat_roi_pct": round(roi, 2),
            "avg_ev_profit_at_filter": round(avg_ev, 4),
        }

    bl_ev = ev_summary(bl_bets, "baseline")
    en_ev = ev_summary(en_bets, "enriched")

    # ── 8. Disagreement analysis ────────────────────────────────────
    both_pass = sum(1 for i in range(n_test) if bl_bets[i]["pass"] and en_bets[i]["pass"])
    only_bl = sum(1 for i in range(n_test) if bl_bets[i]["pass"] and not en_bets[i]["pass"])
    only_en = sum(1 for i in range(n_test) if not bl_bets[i]["pass"] and en_bets[i]["pass"])
    neither = sum(1 for i in range(n_test) if not bl_bets[i]["pass"] and not en_bets[i]["pass"])

    # ROI for each disagreement bucket
    def bucket_roi(indices):
        if not indices:
            return {"count": 0}
        total_ret = sum(test.iloc[i]["actual_payout"] for i in indices)
        total_cost = len(indices)
        return {
            "count": len(indices),
            "total_returned": round(total_ret, 2),
            "roi_pct": round((total_ret - total_cost) / total_cost * 100, 2),
        }

    only_en_idx = [i for i in range(n_test) if not bl_bets[i]["pass"] and en_bets[i]["pass"]]
    only_bl_idx = [i for i in range(n_test) if bl_bets[i]["pass"] and not en_bets[i]["pass"]]
    both_idx = [i for i in range(n_test) if bl_bets[i]["pass"] and en_bets[i]["pass"]]

    disagreement = {
        "both_pass": bucket_roi(both_idx),
        "only_baseline_pass": bucket_roi(only_bl_idx),
        "only_enriched_pass": bucket_roi(only_en_idx),
        "neither_pass": neither,
    }

    # ── 9. Payout prediction comparison at percentiles ──────────────
    bl_err = np.abs(test["bl_predicted_payout"].values - actual_pay)
    en_err = np.abs(test["en_predicted_payout"].values - actual_pay)
    pct_labels = [10, 25, 50, 75, 90]
    payout_percentile_comparison = {}
    for pct in pct_labels:
        payout_percentile_comparison[f"p{pct}"] = {
            "baseline_mae": round(float(np.percentile(bl_err, pct)), 2),
            "enriched_mae": round(float(np.percentile(en_err, pct)), 2),
        }

    # ── 10. Assemble results ────────────────────────────────────────
    elapsed = time.time() - t0
    results = {
        "test_set": {
            "n_races": n_test,
            "split_date": str(split_date),
            "date_range": f"{test['race_date'].min().date()} → {test['race_date'].max().date()}",
        },
        "prediction_accuracy": {
            "baseline": bl_metrics,
            "enriched": en_metrics,
            "delta": {
                "log_ratio_rmse": round(en_metrics["log_ratio_rmse"] - bl_metrics["log_ratio_rmse"], 6),
                "log_ratio_r2": round(en_metrics["log_ratio_r2"] - bl_metrics["log_ratio_r2"], 6),
                "payout_rmse": round(en_metrics["payout_rmse"] - bl_metrics["payout_rmse"], 2),
            },
        },
        "ev_engine_comparison": {
            "baseline": bl_ev,
            "enriched": en_ev,
        },
        "disagreement_analysis": disagreement,
        "payout_error_percentiles": payout_percentile_comparison,
        "elapsed_seconds": round(elapsed, 1),
        "limitation": (
            "This comparison tests predictions on actual winning combos only. "
            "It does NOT test whether the enriched model changes the ranking of "
            "non-winning combos. The EV pass rates here indicate how often each "
            "model's payout prediction for the *true winner* would have cleared "
            "the conservative EV filter."
        ),
    }

    out_path = BASE / "ab_downstream_comparison_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nResults saved to {out_path.name}")

    # ── 11. Print summary ───────────────────────────────────────────
    print("\n" + "=" * 72)
    print("A/B DOWNSTREAM COMPARISON: BASELINE vs ENRICHED HORSE-HISTORY MODEL")
    print("=" * 72)

    print(f"\nTest set: {n_test} races, {split_date} onward")

    print("\n── Prediction accuracy (winning combos) ──")
    print(f"  {'Metric':<35} {'Baseline':>12} {'Enriched':>12} {'Delta':>10}")
    print(f"  {'log_ratio RMSE':<35} {bl_metrics['log_ratio_rmse']:>12.4f} {en_metrics['log_ratio_rmse']:>12.4f} {en_metrics['log_ratio_rmse'] - bl_metrics['log_ratio_rmse']:>+10.4f}")
    print(f"  {'log_ratio R²':<35} {bl_metrics['log_ratio_r2']:>12.4f} {en_metrics['log_ratio_r2']:>12.4f} {en_metrics['log_ratio_r2'] - bl_metrics['log_ratio_r2']:>+10.4f}")
    print(f"  {'payout RMSE ($)':<35} {bl_metrics['payout_rmse']:>12.2f} {en_metrics['payout_rmse']:>12.2f} {en_metrics['payout_rmse'] - bl_metrics['payout_rmse']:>+10.2f}")
    print(f"  {'payout RMSE improvement vs Harv.':<35} {bl_metrics['payout_rmse_improvement_vs_harville_pct']:>11.1f}% {en_metrics['payout_rmse_improvement_vs_harville_pct']:>11.1f}%")

    print("\n── EV engine pass-through (conservative thresholds) ──")
    print(f"  EV filter: {PAYOUT_HAIRCUT:.0%} haircut, {MIN_EV_ROI:.0%} min ROI, Kelly > 0")
    print(f"  Baseline: {bl_ev['ev_pass_count']} winners passed ({bl_ev.get('ev_pass_pct', 0):.2f}%)")
    print(f"  Enriched: {en_ev['ev_pass_count']} winners passed ({en_ev.get('ev_pass_pct', 0):.2f}%)")
    if bl_ev["ev_pass_count"] > 0:
        print(f"  Baseline implied flat-bet ROI: {bl_ev.get('implied_flat_roi_pct', 0):+.1f}%")
    if en_ev["ev_pass_count"] > 0:
        print(f"  Enriched implied flat-bet ROI: {en_ev.get('implied_flat_roi_pct', 0):+.1f}%")

    print("\n── Disagreement analysis ──")
    print(f"  Both pass:           {disagreement['both_pass']['count']}")
    print(f"  Only baseline pass:  {disagreement['only_baseline_pass']['count']}")
    print(f"  Only enriched pass:  {disagreement['only_enriched_pass']['count']}")
    print(f"  Neither pass:        {disagreement['neither_pass']}")
    if disagreement["only_enriched_pass"]["count"] > 0:
        print(f"  Enriched-only ROI:   {disagreement['only_enriched_pass']['roi_pct']:+.1f}%")
    if disagreement["only_baseline_pass"]["count"] > 0:
        print(f"  Baseline-only ROI:   {disagreement['only_baseline_pass']['roi_pct']:+.1f}%")

    print(f"\nCompleted in {elapsed:.1f}s")
    print("=" * 72)


if __name__ == "__main__":
    main()
