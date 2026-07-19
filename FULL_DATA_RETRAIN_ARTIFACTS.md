# Full Data Retrain Artifacts

## Status
Completed successfully end-to-end on `14years.csv` as a model-fit / research artifact.

## Evidence boundary
- Valid evidence scope: `valid_evidence_scope=full_data_xgboost_retrain_model_fit_diagnostic_only`.
- This file documents a full-data XGBoost retrain and its saved artifacts; it is not a paper-trade signal, current-day scanner output, settled ROI, live-profitability evidence, promotion readiness, bankroll guidance, or real-money evidence.
- The payout RMSE / MAE improvements below are model-fit diagnostics only. They do not reopen the current odds-only XGBoost betting path or change the current paper hierarchy by themselves.
- For the deployment read, use `compare_main_approaches.md`, `OP_ANCHOR_METHOD_COMPARISON.md`, and `AB_DOWNSTREAM_COMPARISON.md`: the selective OP/CD rule path remains the paper path, Harville remains benchmark-only, and XGBoost remains research-only unless its evidence class changes materially and produces downstream betting pass-through plus settled paper observations.
- Current bridge rebuild route for source-byte changes before quoting current paper context: `current_evidence_summary.json.rebuild_validation_contract` routes through `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` as provenance/rebuild metadata only; it is not full-data retrain evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- Machine-readable validation boundary: `out/status_validation/full_data_retrain_artifacts/full_data_retrain_artifacts_validation.json` publishes `evidence_boundary_metadata.artifact_role=full-data XGBoost retrain diagnostic metadata`.
- Validate this artifact's boundary with `python3 validate_full_data_retrain_artifacts.py`.

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
These are model-fit diagnostics, not betting-edge evidence.

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
Diagnostic/research use only: replace `path/to/single_race.csv` with the horse-level CSV for one target race. Do not route this output into the paper-trade path without a separate evidence-class review.

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
