# Frozen Portfolio Evaluation

This report evaluates already-defined rule portfolios on a later chronological holdout, using the cached major-track race-level dataset.

## Current evidence boundary (2026-07-17)

- Treat this as a **historical frozen replay**, not a live paper-trade ledger and not real-money evidence.
- Valid evidence scope: `valid_evidence_scope=frozen_portfolio_replay_chronological_holdout_only`.
- The stricter read is still: **Phase 7 beat Phase 8 on frozen 2024-2025 holdout** (`+38.68%` on 175 races vs. `+21.45%` on 118 races), so Phase 8 remains shadow/watch rather than a deployment upgrade.
- `OP_DURABLE_K7` remains the safest current paper anchor; `CD_CORE_K8` is the paper companion; `OP_REFINED_K7` and the rest of Phase 8 need forward observation before promotion.
- The separate current operator ledger now has 6 ROI-complete primary-lane settlements (Primary rule mix: OP_DURABLE_K7 has 0 ROI-complete settled row(s); CD_CORE_K8 has 6. Current settled paper context is CD-only, so it should not be counted as OP-anchor forward evidence.), 1 hit(s), 5 miss(es), with no open primary settlement rows awaiting result/payout evidence; open/closed settlement-queue state is operability metadata only and does not change the 6/30 ROI-complete first-read count. Settlement queue state: `closed`; no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence. Latest primary recommendation context: Latest run context: the latest live scan completed cleanly and found no qualifying races across 52 card(s) and 446 race(s). Treat this as operator context only; use recommendation and settlement ledgers before interpreting bet readiness or forward performance. Open/closed queue state is workflow context, not a bet-ready ticket or forward-performance proof. This frozen replay still cannot prove live profitability or justify a strategy change.
- Operator read gate: `operator_read_gate.requires_refresh_before_evidence_read=false`; gate status = `current_operator_routing_context_only`; recommended command = `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`; read: Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. This is instruction/evidence-read routing only, not frozen-replay performance evidence.
- If quoting the current paper top card from this frozen report context, read `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` first and use the combined `operator_status_context` + `source_freshness` + `operator_read_gate` route; wrapper-refresh, missing-output, freshness routing, or read-gate routing is source-readiness context, not frozen-replay performance evidence.
- Current bridge rebuild order: `current_evidence_summary.json` `rebuild_validation_contract` routes source-byte changes through python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not frozen-replay performance, settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence.
- `BAQ` is not `BEL`; the frozen coverage break should not be patched with unsupported aliasing.
- Re-check this report boundary with `python3 validate_frozen_portfolio_eval_caution.py` after edits.

## Source reproducibility

- Generated from exact local source bytes; fingerprints are audit/reproducibility metadata only, not performance evidence.
- Machine-readable evidence boundary: `frozen_portfolio_eval_metadata.json.evidence_boundary_metadata` marks this as frozen chronological holdout replay metadata, requires the combined current-operator route before top-card quotation, and is not live-profitability, promotion, anchor-change, Phase 8 promotion, BAQ/BEL substitution, or real-money evidence.
- Source freshness provenance: bridge reference `2026-07-17` (`America/New_York`); comparison `generated_reference_date` = `2026-07-17`; right-now state `current_run_date`; refresh before right-now use = `False`; read: Right-now source as-of date 2026-07-17 is not older than bridge reference date 2026-07-17 (America/New_York); still treat the bridge as report/navigation context rather than performance evidence. This is source-routing metadata only, not frozen-replay or live-performance evidence.
- Refresh action boundary: `./run_daily_portfolio_observation.sh` valid use = operator-card freshness and rerun routing boundary; required before right-now use = `False`; source action counts as current before refresh = `True`; can update operator surfaces = `True`, but can settle open rows by itself = `False`, counts as ROI-complete evidence by itself = `False`, clean-empty refresh counts as forward performance = `False`, missing/invalid artifacts count as a clean quiet day = `False`; not forward/live-profitability/promotion/real-money evidence = `True` / `True` / `True` / `True`; read: run `./run_daily_portfolio_observation.sh` before using stale right-now instructions; a wrapper refresh can update operator surfaces, but by itself it does not settle open rows, create ROI-complete evidence, promote OP_DURABLE_K7, or support real-money discussion.
- Operator read gate: `operator_read_gate.requires_refresh_before_evidence_read=false`; gate status = `current_operator_routing_context_only`; recommended command = `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`; read: Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. This is instruction/evidence-read routing only, not frozen-replay performance evidence.
- Current bridge rebuild order: `current_evidence_summary.json` `rebuild_validation_contract` routes source-byte changes through python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not frozen-replay performance, settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence.
- Phase 8 frozen rule definitions are embedded in `evaluate_frozen_portfolios.py`, so the generator fingerprint is part of the source contract.
- Source fingerprints (exact bytes used for this frozen replay; same values are copied into `frozen_portfolio_eval_metadata.json`):
- race_cache: phase5_race_cache.pkl (6876552 bytes, sha256=9f38ab5d34cac72175c7ae2126a33bd798a683fdf15f862afffc17632a6084e6)
- phase7_rules: phase7_live_rules.json (1470 bytes, sha256=24f9f071ba7d47937f9b71e9b735cf7cf330ff3debb3d350459310316d9c1b7d)
- generator: evaluate_frozen_portfolios.py (59302 bytes, sha256=8be48505c90008b5efa7339b75b619dd4e7ebf76d493ad585aece7888e91f42a)
- current_evidence_summary: current_evidence_summary.json (50352 bytes, sha256=f86cdd072e9b5073c59c502811c712f21d08effa75e334904c49573f86ba30b9)

## Why this matters

- The old residual-model script (`XGBoost/train_test_residual.py`) uses `train_test_split(..., test_size=0.25, shuffle=True)`, which is a random 75/25 split and not deployment-realistic.
- This report instead checks frozen portfolios on **train = 2010-2023** and **holdout = 2024-2025**.
- This is still not a perfect no-lookahead rule-discovery test, because the rule sets themselves were originally discovered from historical research. It is materially closer to a deployment-style replay than shuffled splits, but it still needs train-only walk-forward context and live paper settlement before any rule promotion or bankroll discussion.

## Portfolio Summary

| Portfolio | Full ROI | Train ROI | Holdout ROI | Holdout Profit | Holdout Races | Holdout Hit Rate |
|---|---:|---:|---:|---:|---:|---:|
| Phase 7 current-paper rules | +27.97% | +26.04% | +38.68% | $10,210.61 | 175 | 27.43% |
| Phase 8 frozen rules | +46.72% | +50.71% | +21.45% | $5,585.05 | 118 | 34.75% |

## Holdout by Year

### phase7_live

| Year | Races | Wagered | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|---:|
| 2024 | 109 | $16,770 | $62.10 | +0.37% | 24.77% |
| 2025 | 66 | $9,630 | $10,148.51 | +105.38% | 31.82% |

### phase8_frozen

| Year | Races | Wagered | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|---:|
| 2024 | 85 | $18,408 | $1,749.00 | +9.50% | 32.94% |
| 2025 | 33 | $7,632 | $3,836.05 | +50.26% | 39.39% |

## Interpretation

- The **Phase 7 current-paper rule portfolio** held up best on the later holdout: **+38.68% ROI** on 175 races, for **$10,210.61** profit.
- The **Phase 8 frozen portfolio** also stayed positive on the holdout: **+21.45% ROI** on 118 races, for **$5,585.05** profit.
- The BEL rule has **0 holdout races** in 2024-2025 because the later data uses `BAQ` instead of `BEL`, and the current rule mapping explicitly avoids unsupported aliasing.
- This is a more deployment-realistic historical replay than the old shuffled ML split because it preserves chronology and reports historical replay P&L, but it does **not** by itself prove live profitability.
- The main things still missing are a truly clean no-lookahead discovery loop where rules are searched only on prior years, frozen, then tested on the next period, plus ROI-complete live paper-trade settlements.

## Recommended next evaluation loop

1. Freeze a candidate search space before looking at the test window.
2. Use an expanding yearly walk-forward: train on 2010..Y-1, select rules on train only, test on year Y.
3. Track portfolio-level ROI, profit, races, hit rate, and per-year profitability, not just model R² or full-sample ROI.
4. Keep the most recent 12-24 months as a final untouched holdout until the selection logic is frozen.
5. Promote only rules that survive both train-only selection and frozen-holdout evaluation into **live paper trading**, then wait for ROI-complete settled observations before any real-money discussion.
