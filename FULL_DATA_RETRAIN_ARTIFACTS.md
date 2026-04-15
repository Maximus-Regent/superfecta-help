# Full Data Retrain Artifacts

## Status
Completed successfully end-to-end on `14years.csv`.

## Exact training command run
```bash
cd "/Users/maximusregent_ai/Shared/Superfecta Help"
python3 -u XGBoost/train_test_residual.py \
  --csv 14years.csv \
  --output full_data_retrain_results.csv \
  --model-output full_data_retrain_model.json \
  --plot-prefix full_data_retrain \
  --threads 10 \
  --tree-method hist
```

## Key metrics
- Valid races loaded before outlier trim: 559,786
- Final training dataset: 552,927 races
- Feature count: 55
- Log-ratio performance:
  - Train RMSE: 0.4364
  - Test RMSE: 0.4547
  - Train R²: 0.6297
  - Test R²: 0.5971
- Payout prediction, test set:
  - Harville RMSE: $22,296.76
  - ML-corrected RMSE: $5,759.36
  - RMSE improvement: 74.17%
  - Harville MAE: $2,964.75
  - ML-corrected MAE: $752.19
  - MAE improvement: 74.63%
  - Harville correlation: 0.5709
  - ML-corrected correlation: 0.6990

## Output files
- `full_data_retrain_model.json`
- `full_data_retrain_results.csv`
- `full_data_retrain_results_metrics.json`
- `full_data_retrain_log_ratio_diagnostics.png`
- `full_data_retrain_payout_comparison.png`
- `full_data_retrain_longshot_bias.png`

## Script hardening applied
- Switched matplotlib to headless `Agg`
- Saved plots to PNG files instead of blocking on `plt.show()`
- Added explicit `--model-output` and `--plot-prefix` support
- Added metrics JSON output

## Recommended next prediction command
Replace `path/to/single_race.csv` with the horse-level CSV for one target race.

```bash
cd "/Users/maximusregent_ai/Shared/Superfecta Help"
python3 XGBoost/predict_single_race.py \
  --input path/to/single_race.csv \
  --model full_data_retrain_model.json \
  --output next_race_predictions.csv \
  --top-combinations 50 \
  --sort-by ev \
  --threads 10
```
