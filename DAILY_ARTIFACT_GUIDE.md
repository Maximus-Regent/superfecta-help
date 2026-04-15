# Daily Artifact Guide

This note separates **what Cole should actually use day to day** from the growing pile of benchmark and research artifacts.

## Fast daily routine

1. Run `./run_daily_portfolio_observation.sh`
2. Read the latest `daily_summary.txt`, `preflight_note.txt`, and `OPS_HISTORY.md` when a quiet streak needs context
3. Read `phase7_current_paper/next_steps.md` first, then `phase8_shadow/next_steps.md`
4. Use the lane monitors only when you need more context on why those next steps were suggested
5. If settlement rows are open, use `paper_trade_settlement_helper.py`
6. Only then dip into the decision cards or benchmark reports

Latest detected daily run root: `out/daily_portfolio_runs/2026-04-15`

## Use every day

| File | Status | Why it matters |
|---|---|---|
| `COLE_STATUS_AND_PLAN.md` | `present` | Single honest status document. Read first when deciding what matters. |
| `run_daily_portfolio_observation.sh` | `present` | Preferred daily runner for primary Phase 7 current-paper lane plus Phase 8 shadow lane. |
| `out/daily_portfolio_runs/2026-04-15/daily_summary.txt` | `present` | Combined latest run summary. Current latest run root: `out/daily_portfolio_runs/2026-04-15`. |
| `OPS_HISTORY.md` | `present` | Rolling ops log across recent daily runs. Best first read when several quiet days in a row need explanation. |
| `out/daily_portfolio_runs/2026-04-15/preflight_note.txt` | `present` | Shared calendar note for the latest run. Read this first on empty days to see whether OP / CD were even active. |
| `out/daily_portfolio_runs/2026-04-15/phase7_current_paper/next_steps.md` | `present` | Best immediate operator read for the current primary lane: exact next commands based on the current lane state. |
| `out/daily_portfolio_runs/2026-04-15/phase8_shadow/next_steps.md` | `present` | Best immediate operator read for the shadow lane: exact next commands based on the current lane state. |
| `out/daily_portfolio_runs/2026-04-15/phase7_current_paper/lane_monitor.md` | `present` | Best one-glance context read for the current primary lane: forward state plus settlement queue. |
| `out/daily_portfolio_runs/2026-04-15/phase8_shadow/lane_monitor.md` | `present` | Best one-glance context read for the shadow lane: forward state plus settlement queue. |
| `paper_trade_settlement_helper.py` | `present` | Use after races settle to list open rows and enter one result safely. |
| `phase7_current_paper_rules.json` | `present` | Current active paper basket: OP + CD, with dormant BEL removed. |
| `phase8_shadow_rules.json` | `present` | Shadow-only watch basket. Log it, do not promote it by default. |

## Use after races settle

| File | Status | Why it matters |
|---|---|---|
| `paper_trades/phase7_current_paper_paper_trade_settlements.csv` | `present` | Manual settlement ledger for the primary lane. |
| `paper_trades/phase8_shadow_paper_trade_settlements.csv` | `present` | Manual settlement ledger for the shadow lane. |
| `paper_trade_forward_check.py` | `present` | Conservative forward check against frozen holdout baselines. |
| `out/daily_portfolio_runs/2026-04-15/phase7_current_paper/forward_check.md` | `present` | Detailed current primary forward-check artifact. |
| `out/daily_portfolio_runs/2026-04-15/phase8_shadow/forward_check.md` | `present` | Detailed current shadow forward-check artifact. |
| `paper_trade_lane_monitor.py` | `present` | Regenerate compact lane summaries after settlement updates. |
| `paper_trade_next_steps.py` | `present` | Regenerate exact next-command guidance after settlement updates or manual checks. |

## Read when making decisions, not every run

| File | Status | Why it matters |
|---|---|---|
| `forward_evidence_scorecard.txt` | `present` | Fast rule ranking by forward evidence quality. |
| `OP_FAMILY_DECISION.md` | `present` | Whether anything clearly beats OP_DURABLE_K7 as the safest OP anchor. |
| `CROSS_FAMILY_DECISION.md` | `present` | Anchor / paper / watch roles for OP_DURABLE_K7, CD_CORE_K8, and OP_REFINED_K7. |
| `PORTFOLIO_DECISION_CARD.md` | `present` | Phase 7 vs Phase 8 vs train-only selector at the portfolio level. |
| `METHOD_FAMILY_DECISION.md` | `present` | Harville vs XGBoost vs selective rule path, for retiring dead-end method families. |

## Benchmark / research context only

| File | Status | Why it matters |
|---|---|---|
| `WALK_FORWARD_VALIDATION.md` | `present` | Honest validation benchmark. Use for context, not as the daily operating recipe. |
| `BACKTEST_REPORT.md` | `present` | Large-sample negative baseline for Harville / generic ML / broad structural strategies. |
| `PHASE8_REPORT.md` | `present` | Research context only. Treat with skepticism when it conflicts with frozen holdout. |
| `DIAGNOSE_CD_SELECTION.md` | `present` | Important selector diagnosis, but not part of the daily operating loop. |
| `SELECTOR_EXPERIMENT.md` | `present` | Selector-tuning research context, not a daily-use artifact. |
| `SAMPLE_SIZE_EXPERIMENT.md` | `present` | Follow-up selector experiment context, not a daily-use artifact. |

## Do not let these drive daily behavior

| File | Status | Why it matters |
|---|---|---|
| `XGBoost` | `present` | Model research only. Do not treat this directory as a live decision surface. |
| `phase7_live_rules.json` | `present` | Historical frozen ruleset that still includes dormant BEL. Reference only, not the cleanest live-paper entrypoint. |
| `run_paper_trade_cycle.sh` | `present` | Useful one-basket wrapper, but the two-lane daily wrapper is the preferred routine now. |
| `backtest_phase7_summary.csv` | `present` | Historical discovery output. Useful for research, not for daily deployment decisions. |

## Bottom line

- **Daily operating path**: read the preflight note, then Phase 7 current paper basket first, then Phase 8 shadow
- **Safest anchor inside the live family**: `OP_DURABLE_K7`
- **Paper alongside it**: `CD_CORE_K8`
- **Do not drift back into generic Harville / XGBoost live claims** just because those artifacts are still in the repo
