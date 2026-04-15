# Superfecta Help

A working research + operations repo for Superfecta modeling, validation, paper trading, and live/demo scanning.

## Current honest status

This project is strongest when treated conservatively:

- **Primary paper baseline:** Phase 7 live portfolio
- **Best current holdout result:** **+38.68% ROI on 175 races**
- **Best validated walk-forward selector result:** **+30.42% ROI**
- **Phase 8 status:** shadow-only, not the default
- **Method-family hierarchy:**
  - Selective rule path = paper-trade worthy
  - Harville = benchmark only
  - XGBoost residual correction = research only

## What is in this repo

### Core strategy / evaluation
- `compare_main_approaches.py`
- `forward_evidence_scorecard.py`
- `portfolio_decision_card.py`
- `method_family_decision_card.py`
- `experiment_selector_variants.py`
- `experiment_sample_size.py`
- `walk_forward_validation.py`
- `evaluate_frozen_portfolios.py`

### Live + demo operations
- `superfecta_ops.py`
- `demo_live_predictions.py`
- `live_portfolio_scanner.py`
- `scan_live.sh`

### Paper-trade operations
- `run_daily_portfolio_observation.sh`
- `paper_trade_pipeline.py`
- `paper_trade_forward_check.py`
- `paper_trade_lane_monitor.py`
- `paper_trade_settlement_sync.py`
- `paper_trade_settlement_helper.py`
- `paper_trade_preflight_note.py`

### Reports / docs
- `COLE_STATUS_AND_PLAN.md`
- `COLE_FULL_REPORT_2026-04-15.md`
- `Superfecta_Project_Report_2026-04-15.html`
- `Superfecta_Project_Report_2026-04-15.pdf`
- `WORKING_STATUS_REPORT_2026-04-15.md`
- `OVERNIGHT_PROGRESS.md`

## Notes

- Large raw datasets, caches, local logs, and paper-trade outputs are intentionally excluded from Git tracking.
- This repo is meant to preserve the code, docs, and decision artifacts without stuffing GitHub with local runtime junk.
- The live watcher threshold used in current ops is **+30% EV ROI**.
