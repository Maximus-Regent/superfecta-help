# Training Data Audit

*2026-04-15*

## What the training data contains

**Source:** `14years_major_tracks.csv` (768K rows, 84 MB)

| Column | Type | Description |
|--------|------|-------------|
| registration_number | str | Unique horse identifier (125,169 unique horses) |
| program_number | str | Horse's saddle cloth number per race |
| track_id | str | Track code (BEL, AQU, CD, SA, KEE, OP, DMR) |
| race_date | date | 2010-06-02 through 2025-06-01 |
| race_number | int | Race number within card |
| odds | int | American moneyline odds (e.g. 350 = +350) |
| position_at_start | int | Starting gate position |
| official_position | int | Finish position |
| scratch_indicator | str | Y if scratched |
| winning_numbers | str | Superfecta combination "8-6-2-7" (program numbers of finishers 1-4) |
| number_of_tickets_bet | int | Superfecta pool ticket count |
| total_pool | float | Total superfecta pool dollars |
| payoff_amount | float | Payout for the winning combination |
| distance_id | int | Race distance code |
| surface | str | D (dirt), T (turf), etc. |
| course_type | str | Course configuration |
| purse_usa | float | Race purse in USD |
| post_time | str | Scheduled post time |
| track_condition | str | FT (fast), GD (good), MY (muddy), etc. |
| number_of_runners | int | Field size |
| post_position | int | Post position |

**After pivoting to race-level:** ~89K valid superfecta races with complete data.

## What the current pipeline uses

The existing `XGBoost/train_test_residual.py` builds **52 race-level features** from:

- **Probability features:** Normalized win probabilities for the 4 winners, logit transforms
- **Market structure:** Field size, odds distribution (mean, std, range), favorite/longshot odds
- **Economic features:** Pool size, purse, pool per runner, purse per runner
- **Race conditions:** Surface, course type, track condition (one-hot encoded), distance, post hour
- **Derived:** Harville expected payout, probability product/sum/entropy/variance

**Target:** `log(actual_payout / harville_payout)` — captures market mispricing

## What was missing (biggest gap)

**The pipeline completely ignores horse identity and history.**

Despite having `registration_number` to uniquely identify 125,169 horses across 768K appearances, the pivot-to-race-level step discards all horse identity. The model sees only what the market says today (odds/probabilities) — never what the horse has actually done before.

This was explicitly noted in project docs as a dead-end assumption:
> "XGBoost ML model — Zero improvement over gap-filter rules; needs horse-specific features to work"
> "Horse form/speed figure features (would require new data source)"

**But the data to build horse-history features already existed in the CSV.**

With median 4 starts per horse and 56,435 horses having 5+ starts, there is substantial repeat-appearance data to mine.

## What was changed

### New file: `build_horse_features.py`

Computes 17 per-horse-per-race features using strict lookback (shift-1 expanding windows, no data leakage):

| Feature | Description |
|---------|-------------|
| n_prior_starts | Number of prior starts |
| prior_win_rate | Career win rate from prior starts |
| prior_top3_rate | Career top-3 rate from prior starts |
| avg_finish_all | Average finish position (all prior) |
| avg_finish_last5 | Rolling avg finish, last 5 starts |
| days_since_last | Calendar days since previous start |
| avg_prior_purse | Average purse of prior races (class proxy) |
| class_change | Current purse minus avg_prior_purse |
| surface_prior_starts | Same-surface experience count |
| surface_win_rate | Same-surface win rate |
| surface_avg_finish | Same-surface avg finish |
| distance_prior_starts | Same-distance experience count |
| distance_win_rate | Same-distance win rate |
| distance_avg_finish | Same-distance avg finish |
| track_prior_starts | Same-track experience count |
| track_win_rate | Same-track win rate |
| track_avg_finish | Same-track avg finish |

**Output:** `horse_features_major_tracks.csv` (94 MB, 768K rows)

- 83.7% of rows have prior history
- 16.3% are first-time starters (NaN features — XGBoost handles these natively)
- Build time: 15 seconds

### New file: `validate_horse_features.py`

Side-by-side training comparison:
1. Loads raw CSV, pivots to race-level (also captures winner registration numbers)
2. Computes baseline features (identical to existing pipeline)
3. Merges horse features for each of the 4 winning positions
4. Creates per-position features (w1_, w2_, w3_, w4_) and aggregates (avg_, min_, max_)
5. Trains both baseline and enriched XGBoost models with identical hyperparameters
6. Reports comparison

### Race-level horse features (120 total)

For each of the 17 per-horse features, the validation attaches:
- **Per-position:** w1_X, w2_X, w3_X, w4_X (winner positions 1-4)
- **Aggregates:** avg_X, min_X, max_X (across the 4 winners)
- **Plus:** n_debut_winners (count of first-time starters among the 4)

## Validation results

Chronological 75/25 split on 88,974 major-track races. Same XGBoost hyperparameters.

| Metric | Baseline (52 features) | Enriched (172 features) | Change |
|--------|----------------------|------------------------|--------|
| Log-ratio RMSE | 0.4201 | 0.4109 | **-2.2%** |
| Log-ratio MAE | 0.3324 | 0.3248 | **-2.3%** |
| Log-ratio R² | 0.6027 | 0.6197 | **+2.8%** |
| Log-ratio Correlation | 0.7825 | 0.7911 | **+1.1%** |
| Payout RMSE (corrected) | $6,204 | $5,955 | **-4.0%** |
| Payout MAE (corrected) | $724 | $709 | **-2.1%** |
| Payout RMSE improvement over Harville | 75.7% | 76.7% | +1.0pp |

Horse feature match rate: 100%. Every winner in every race had features.

## Why this should help

1. **The model now sees horse quality, not just market opinion.** A horse with a 0.30 win rate and 3.0 avg finish position running at 8:1 is a fundamentally different bet than a horse with a 0.05 win rate and 7.5 avg finish at the same odds. The old model couldn't distinguish these.

2. **Surface/distance/track affinity captures hidden form.** A horse switching from turf (where it won 3 of 5) to dirt (where it's 0 for 4) will likely underperform its current odds. The old model had no way to know this.

3. **Days-since-last and class changes add context.** Horses returning from long layoffs behave differently than horses on a regular schedule. Horses stepping up in class (class_change > 0) tend to underperform their odds.

4. **The improvement is consistent across all metrics.** No cherry-picking — RMSE, MAE, R², and correlation all improved on the out-of-sample test set.

## What is still missing

- **Jockey/trainer statistics** — not in the data, would require external source
- **Speed figures / Beyer numbers** — proprietary, not available
- **Weather / track maintenance** — not in the data
- **Workouts** — not in the data
- **Equipment changes** — not in the data
- **Medication / Lasix** — not in the data
- **Post position bias per track** — derivable from existing data (future improvement)
- **Pace figures** — not in the data (would need fractional times)

## Integration into main training pipeline

*2026-04-15*

Horse-history features are now available in the production training path via an optional flag:

```bash
# Baseline (unchanged behavior):
python3 XGBoost/train_test_residual.py --csv 14years_major_tracks.csv

# Enriched (with horse-history features):
python3 XGBoost/train_test_residual.py --csv 14years_major_tracks.csv \
    --horse-features horse_features_major_tracks.csv
```

**Changes to `XGBoost/train_test_residual.py`:**
1. `load_and_pivot()` now captures winner registration numbers (`reg1`-`reg4`) and program numbers (`prog1`-`prog4`) for each race, enabling the horse feature join.
2. New `merge_horse_features()` function loads the pre-built horse features CSV and merges per-position (w1\_ through w4\_) and aggregate (avg\_, min\_, max\_) features for the 4 superfecta winners. Same logic as `validate_horse_features.py::attach_horse_features()`.
3. New `--horse-features` CLI argument. When omitted, baseline behavior is identical to before.
4. Fixed a latent index-alignment bug in `compute_features_targets()` where outlier removal left non-contiguous DataFrame indices that conflicted with numpy positional indexing in `train_and_evaluate()`.

**Leakage prevention:** Unchanged. Horse features are built by `build_horse_features.py` using strict shift-1 expanding windows (no future data). The merge step only looks up pre-computed values by (registration_number, track_id, race_date, race_number) — no new computation occurs during training.

**Reproducibility:** The enriched model trains deterministically from `horse_features_major_tracks.csv` + `14years_major_tracks.csv` with the same XGBoost seed (42) and chronological 75/25 split.

## Files changed

| File | Action | Description |
|------|--------|-------------|
| `build_horse_features.py` | **NEW** | Horse history feature builder |
| `validate_horse_features.py` | **NEW** | Baseline vs enriched validation |
| `horse_features_major_tracks.csv` | **NEW** | Feature cache (94 MB) |
| `validate_horse_features_results.json` | **NEW** | Validation metrics |
| `XGBoost/train_test_residual.py` | **MODIFIED** | Integrated horse-history merge (optional `--horse-features` flag) |
| `TRAINING_DATA_AUDIT.md` | **NEW** | This document |
