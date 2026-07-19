# A/B Downstream Comparison

This artifact compares the current baseline payout model against the enriched horse-history XGBoost path on the same chronological test set.

## Guardrail

- This is a research comparison, not a paper-promotion case.
- Valid evidence scope: `valid_evidence_scope=downstream_xgboost_ab_research_comparison_only`.
- The selective rule path remains the only method family in `PAPER NOW` status.
- Inside that paper lane, `OP_DURABLE_K7` remains the safest anchor, `CD_CORE_K8` is the primary OP/CD paper-basket companion, and `OP_REFINED_K7` stays a smaller same-family OP shadow challenger rather than a promoted default.
- Selective paper-lane hierarchy source: `cross_family_decision_card.csv` (`sha256=4be838c8552f2c0909387928a879452ce6b0a5584c2e6f30da5b4985f76059ba`, `2266` bytes).
- A modest payout-prediction improvement is not enough by itself to promote the enriched horse-history XGBoost path into paper-betting logic.
- Non-goal: do not quote current `PAPER_TRADE_NOW` instructions from this A/B artifact without the combined `CURRENT_EVIDENCE_SUMMARY` `operator_status_context` / `source_freshness` / `operator_read_gate` route.

## Current Read

- On 22244 test-set winning combos from 2020-12-19 → 2025-06-01, the enriched horse-history XGBoost path improves payout prediction error by 4.24% and log-ratio RMSE by 2.16%, but it still does not create a cleaner deployment case because conservative EV winner pass counts drift down by 7 (-3.93% relative; -0.0315 percentage points of test winners) from 178 baseline to 171 enriched.

## Current Paper Snapshot

This snapshot is copied from `current_evidence_summary.json` so the A/B model comparison can show the current paper-lane caveat without becoming a live-performance surface.

| Item | Current Read | Boundary |
|---|---|---|
| Combined operator route | current_evidence_summary.json combined route: use operator_status_context plus source_freshness.requires_refresh_before_right_now_use=False plus operator_read_gate.requires_refresh_before_evidence_read=False before quoting current PAPER_TRADE_NOW instructions from this downstream A/B artifact; recommended command=python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json. Operator context read = ops bucket/takeaway are routing metadata, not forward-performance evidence.; ops bucket = `NO TARGETS` | The combined route is instruction/evidence-read gating only; the saved top card is fresh operator-routing context, not no-target, clean-empty, bet-readiness, settled ROI, model-family proof, OP-anchor proof, promotion, live-profitability, bankroll, or real-money evidence |
| Source freshness | `current_run_date`; refresh before right-now use = `False`; bridge reference = `2026-07-17` (`America/New_York`); comparison = `generated_reference_date` / `2026-07-17`; read = Right-now source as-of date 2026-07-17 is not older than bridge reference date 2026-07-17 (America/New_York); still treat the bridge as report/navigation context rather than performance evidence. | Source freshness is operator-readiness metadata, not performance proof |
| Refresh action boundary | `./run_daily_portfolio_observation.sh` required before right-now use = `False`; settles rows / creates ROI evidence / clean-empty performance = `False` / `False` / `False` | Wrapper refresh is operator routing only; it is not settled ROI, promotion readiness, live profitability, or real-money evidence |
| Operator read gate | `current_evidence_summary.json` `operator_read_gate`: Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. Gate status = `current_operator_routing_context_only`; recommended command = `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` | The saved top card can be read only as current operator instruction/evidence gating context; this read gate is not no-target evidence, clean-empty evidence, model-family proof, OP-anchor proof, bet readiness, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Bridge-published gate progress | `current_evidence_summary.json` `decision_gate_progress`: Gate progress: primary first-read 6/30; OP anchor same-candidate 0/30; Phase 8 weakest shadow 0/20; real-money discussion floor 6/100. All remain uncleared and are routing context only. Source: `forward_evidence_scorecard.json` `decision_gate_minimums`; gate status = `all_uncleared` | Current gates are all uncleared routing context only; they do not change the downstream A/B model comparison or create settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll, or real-money evidence |
| Scorecard audit route | `current_evidence_summary.json` `scorecard_audit_route`: Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite drift across report-facing surfaces. Validator: `python3 validate_scorecard_ranking_contract_audit.py`; artifacts: `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json`; gate snapshot = 30/20/100 with no-BAQ-as-BEL required `True` | Report-synchronization route only; it is not downstream A/B evidence, forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Current bridge rebuild order | `current_evidence_summary.json` `rebuild_validation_contract`: `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes | Provenance/rebuild route only; green checks and rebuild order are not downstream A/B evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Current settled rule mix | OP_DURABLE_K7=0; CD_CORE_K8=6; Primary rule mix: OP_DURABLE_K7 has 0 ROI-complete settled row(s); CD_CORE_K8 has 6. Current settled paper context is CD-only, so it should not be counted as OP-anchor forward evidence. | Rule-specific settled rows stay separate; CD-only paper rows are not OP-anchor forward evidence |
| Settlement queue state | `closed`; no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence. | Open rows are settlement workflow only; fill outcomes from result/payout evidence before interpreting ROI |
| Operator route | `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` | Use the bridge route for operator context; do not infer profit, promotion, or real-money readiness from the route itself |

## Test Set

- Chronological split date: `2020-12-19`
- Test races: `22244` winning combos
- Date range: `2020-12-19 → 2025-06-01`

## Prediction Accuracy (winning combos only)

| Metric | Baseline | Enriched | Delta |
|---|---:|---:|---:|
| log-ratio RMSE | 0.420546 | 0.411458 | -0.009088 |
| log-ratio R² | 0.601585 | 0.618619 | +0.017034 |
| payout RMSE | 6191.69 | 5929.40 | -262.29 |
| payout RMSE improvement vs Harville | 75.77% | 76.80% | +1.03pp |

## Conservative EV Pass-Through

- EV filter: `75%` payout haircut, `15%` minimum EV ROI, `Kelly > 0`, `joint_prob >= 0.0005`
- These pass counts are computed on the true winning combos only, so the flat ROI figures below are diagnostic outputs, not deployable ROI claims.

| Path | Winner pass count | Winner pass % | Avg EV profit at filter | Diagnostic flat ROI on passing winners |
|---|---:|---:|---:|---:|
| Baseline | 178 | 0.8002% | 0.2213 | +39666.87% |
| Enriched | 171 | 0.7687% | 0.2277 | +40781.30% |

- Pass-through delta vs baseline: `-7` winner passes, `-3.93%` relative, `-0.0315` percentage points of the winning-combo test set.
- Even where the enriched path shows slightly higher average EV profit on the winning-combo subset, that read remains diagnostic only because it comes from a tiny, winner-only slice rather than a full paper-candidate ranking test.

## Disagreement Analysis

| Bucket | Count | Diagnostic ROI on winning-combo subset |
|---|---:|---:|
| Both pass | 108 | +36144.01% |
| Only baseline passes | 70 | +45102.14% |
| Only enriched passes | 63 | +48730.95% |
| Neither passes | 22003 | n/a |

## Model Source Fingerprints

Exact model artifact fingerprints for this saved A/B read. Use them as reproducibility metadata only; they do not prove paper ROI, promotion readiness, live profitability, or real-money performance.

| Source | Path | Bytes | SHA-256 |
|---|---|---:|---|
| `baseline_model` | `ab_baseline_model.json` | 2542034 | `920babc8b81c9fdd951b814adf3b92bc97f6e89ebc600da8ff641966f47faeec` |
| `enriched_model` | `ab_enriched_model.json` | 3334964 | `43463d2ab888870b5db40d412ce0f4ec7aaedba40341746b985150bd00d4fccb` |

## Limitation

- This comparison tests predictions on actual winning combos only. It does NOT test whether the enriched model changes the ranking of non-winning combos. The EV pass rates here indicate how often each model's payout prediction for the *true winner* would have cleared the conservative EV filter.

## Bottom Line

- The enriched horse-history XGBoost path is still useful as model research because it modestly improves payout prediction quality on the matched test set.
- That prediction gain still does not outrank the frozen selective-rule evidence chain, because the downstream conservative EV picture stays small, winner-only, and not clearly better on pass counts.
- Keep the enriched horse-history XGBoost path in `RESEARCH ONLY`, keep Harville in `BENCHMARK ONLY`, and keep the selective rule path as the only `PAPER NOW` family, with `OP_DURABLE_K7` still the safest anchor, `CD_CORE_K8` as the primary OP/CD paper-basket companion, and `OP_REFINED_K7` as the same-family OP shadow challenger.
