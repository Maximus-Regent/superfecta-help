# Method Family Decision Card

This note compares the three method families that matter most for honest deployment decisions:
**Harville-ranked probabilities, the current XGBoost correction path, and the selective rule path.**

Short answer:
- **Paper trade the selective rule path**
- **Keep Harville as a benchmark only**
- **Keep XGBoost as research, not as a betting decision engine**
- **Evidence scope:** `valid_evidence_scope=split_aware_method_family_hierarchy_only`; this card is a frozen/report method hierarchy only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- **This card is split-aware, not family-CI-backed at the top level**: the selective family wins here on frozen 2024-2025 holdout plus an honest train-only walk-forward benchmark, then gets cross-checked by rule-level anchor/shadow evidence, but the frozen sources do not publish a selective-family bootstrap CI lower bound.
- **Inherited scorecard ranking contract:** rank is tier-first (`True`), Score is secondary within tier (`True`), and raw Score is not an automatic deployment instruction (`True`).
- **Inherited operator read gate:** `compare_main_approaches.json` `current_operator_boundary.operator_read_gate` says Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. This is routing context only, not no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money evidence.
- **Current bridge rebuild order:** `current_evidence_summary.json` `rebuild_validation_contract` routes source-byte changes through `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not method-family evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- **Scorecard audit route:** `current_evidence_summary.json` `scorecard_audit_route` points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py`; this is report-synchronization metadata only, not method-family evidence, forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
This card is intentionally pinned to the frozen 2024-2025 holdout standard carried by the compare-main, cross-family, and forward-scorecard JSON artifacts, so a prettier number from some other window or method slice does not quietly rewrite the current paper method hierarchy.

## Comparison Table

For the selective family, the primary evidence includes the 2024/2025 holdout split because the aggregate holdout number alone is too smooth. Its secondary evidence is the honest train-only selector walk-forward benchmark, not a replay of the frozen Phase 7 basket.
For XGBoost, the secondary column is model-fit context from the matched downstream A/B, not a betting-evidence line.

| Method Family | Role | Primary Evidence | Sample | Secondary Evidence | Why It Sits Here |
|---|---|---:|---:|---:|---|
| Selective rule path | PAPER NOW | +38.68% (2024-2025 holdout ROI; 2024 +0.37% on 109, 2025 +105.38% on 66) | 175 | +22.46% (train-only selector walk-forward ROI) | Only family here with positive current frozen holdout evidence and a paper-trade observation path. In the current holdout, this is effectively the OP+CD basket, with OP_DURABLE_K7 still the safest anchor, but the recent path was uneven rather than a smooth two-year glide. |
| Harville-ranked probabilities | BENCHMARK ONLY | -24.05% (broad backtest ROI) | 90004 | 41.99% (hit rate) | Large-sample structural benchmark, not a paper candidate. The hit rate is high, but the ROI stays deeply negative, which means ranking order by Harville probability alone does not beat takeout. |
| XGBoost residual correction | RESEARCH ONLY | -24.16% (best ML betting ROI (ML-EV>=1.0_H6_FS5-7)) | 16724 | 4.24% (matched-model payout RMSE reduction vs current baseline) | The model can improve payout prediction a bit without creating a betting edge. In the matched downstream test, payout RMSE was reduced by 4.24% and log-ratio RMSE was reduced by 2.16%, but conservative EV winner pass counts drifted down by 7 (-3.93% relative; -0.0315 percentage points of 22244 test winners), from 178 baseline to 171 enriched. |

## Why This Ordering Is Conservative

At the method-family layer, this card does not have a published family-level bootstrap CI field. The caution surface here is the selective family holdout split, the honest train-only walk-forward benchmark, and the rule-level anchor/shadow evidence beneath it rather than a top-level family CI claim.
Scorecard rank-contract override: CD_CORE_K8 ranks ahead of OP_REFINED_K7 because PAPER tier outranks WATCH tier even though OP_REFINED_K7 has the higher raw forward_trust score.

- **Selective rule path (PAPER NOW)**: Only family here with positive current frozen holdout evidence and a paper-trade observation path. In the current holdout, this is effectively the OP+CD basket, with OP_DURABLE_K7 still the safest anchor. Family-level walk-forward context comes from the honest train-only selector benchmark rather than replaying the frozen Phase 7 basket.
  - Practical note: Frozen 3-rule baseline. BEL contributes zero 2024-2025 races, so the current holdout is effectively the OP+CD legs.
  - Holdout split: 2024 +0.37% on 109 races; 2025 +105.38% on 66 races. That is positive in both years, but most of the aggregate holdout edge came in 2025, so the family still needs paper-trade confirmation instead of victory-lap language.
  - Current paper-basket companion read: `OP_DURABLE_K7` stays the safest anchor, `CD_CORE_K8` is the primary OP/CD paper-basket companion, and `OP_REFINED_K7` remains the stronger same-family OP shadow challenger rather than a promoted default.
  - Scorecard CI-only promotion check: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` says `ci_only_promotion_allowed=false`; the positive OP_REFINED CI lower bound is support context only, not a method-family promotion trigger.
- **Harville-ranked probabilities (BENCHMARK ONLY)**: Large-sample structural benchmark, not a paper candidate. The hit rate is high, but the ROI stays deeply negative, which means ranking order by Harville probability alone does not beat takeout.
  - Practical note: Best broad Harville line in BACKTEST_REPORT.md: Harville-Top120.
- **XGBoost residual correction (RESEARCH ONLY)**: The model can improve payout prediction a bit without creating a betting edge. In the matched downstream test, payout RMSE was reduced by 4.24% and log-ratio RMSE was reduced by 2.16%, but conservative EV winner pass counts drifted down by 7 (-3.93% relative; -0.0315 percentage points of 22244 test winners), from 178 baseline to 171 enriched.
  - Read the payout-RMSE gain as model-fit context only; it does not become deployment-worthy unless the downstream betting behavior improves too.
  - Practical note: Best ML family line in backtest_summary.csv is still negative (ML-EV>=1.0_H6_FS5-7 = -24.16% on 16724 races).

## Why This Is Not an Apples-to-Apples ROI Contest

- The **selective rule path** has earned the strongest current deployment evidence, because it is the only family here with positive frozen 2024-2025 holdout results plus a paper-trade observation workflow.
  - Its frozen holdout split is still worth saying plainly: 2024 +0.37% on 109 races versus 2025 +105.38% on 66 races. That is better than Harville/XGBoost, but it is not a smooth straight-line edge.
- The **Harville** and **XGBoost** families are judged by their best honest family-level evidence instead of by a fresh 2024-2025 holdout replay, because they already fail on much larger historical samples and never earned a positive deployment case.
  - For XGBoost specifically, the payout-RMSE improvement is still just model-fit context from the matched downstream test, not a separate betting-proof column.
- That asymmetry is acceptable here because the question is practical, not academic: **what should Cole still treat as paper-worthy?** The answer is the selective rule path, not the generic ranking/modeling families.

## Current Operator Boundary

This context is inherited from `compare_main_approaches.json` / `current_evidence_summary.json` so the method-family card points to the current paper-workflow boundary without using it as method-ranking evidence.

| Field | Current bridge read | Evidence boundary |
|---|---|---|
| Source freshness | `current_run_date`; refresh before right-now use = `False`; bridge reference = `2026-07-17` (`America/New_York`); comparison = `generated_reference_date` / `2026-07-17`; read = Right-now source as-of date 2026-07-17 is not older than bridge reference date 2026-07-17 (America/New_York); still treat the bridge as report/navigation context rather than performance evidence. | Source freshness is operator-readiness metadata, not method-ranking or performance proof |
| Refresh action boundary | `./run_daily_portfolio_observation.sh` required before right-now use = `False`; can update surfaces = `True`; settles rows / creates ROI evidence / clean-empty performance = `False` / `False` / `False` | Wrapper refresh is operator routing only; it is not settled ROI, promotion readiness, live profitability, or real-money evidence |
| Operator read gate | `compare_main_approaches.json` `current_operator_boundary.operator_read_gate`: Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. Gate status = `current_operator_routing_context_only`; recommended command = `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` | The saved top card can be read as current operator routing context only; this read gate is not no-target evidence, clean-empty evidence, method-family proof, bet readiness, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Bridge-published gate progress | `current_evidence_summary.json` `decision_gate_progress`: Gate progress: primary first-read 6/30; OP anchor same-candidate 0/30; Phase 8 weakest shadow 0/20; real-money discussion floor 6/100. All remain uncleared and are routing context only. Source: `forward_evidence_scorecard.json` `decision_gate_minimums`; gate status = `all_uncleared` | Current gates are all uncleared routing context only; they do not change the method-family ordering or create settled ROI, OP-anchor proof, promotion readiness, live-profitability, bankroll, or real-money evidence |
| Current bridge rebuild order | `current_evidence_summary.json` `rebuild_validation_contract`: `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes | Rebuild route only; it is not method-family evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Scorecard audit route | `current_evidence_summary.json` `scorecard_audit_route`: Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite drift across report-facing surfaces. Artifacts: `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json`; validator: `python3 validate_scorecard_ranking_contract_audit.py`; gate source: `forward_evidence_scorecard.json:decision_gate_minimums` | Route metadata checks copied gate/ranking/CI-only/timezone/no-BAQ synchronization only; it is not method-family evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Current settled rule mix | OP_DURABLE_K7=0; CD_CORE_K8=6; Primary rule mix: OP_DURABLE_K7 has 0 ROI-complete settled row(s); CD_CORE_K8 has 6. Current settled paper context is CD-only, so it should not be counted as OP-anchor forward evidence. | Rule-specific settled rows stay separate; CD-only paper rows are not OP-anchor forward evidence |
| Settlement queue state | `closed`; no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence. | Open rows are settlement workflow only; fill outcomes from actual result/payout evidence before interpreting ROI |
| Recommendation context | Latest run context: the latest live scan completed cleanly and found no qualifying races across 52 card(s) and 446 race(s). Treat this as operator context only; use recommendation and settlement ledgers before interpreting bet readiness or forward performance. | Latest recommendation-state context is operator routing only, not bet readiness or forward-performance evidence |
| Operator route | `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` | Use the route to settle or refresh; do not infer profit, promotion, or real-money readiness from the route itself |

The current operator boundary is routing/provenance context only. It does not change the selective-rule vs Harville vs XGBoost ordering above, and it is not settled ROI, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

## Scorecard CI-Only Promotion Check

Source: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7`
- Current decision: Keep OP_REFINED_K7 shadow/watch only.
- CI-only promotion allowed: `false`
- Why not: smaller holdout sample than OP_DURABLE_K7, losing 2024 holdout split, lower walk-forward recurrence than OP_DURABLE_K7, uncleared phase8_promotion_review paper-observation gate, uncleared anchor_displacement paper-observation gate.
- Required before review: phase8 promotion review = 20+ ROI-complete candidate shadow observations plus cleaner split-aware/walk-forward support; anchor displacement = 30+ ROI-complete same-candidate paper observations plus a cleaner split-aware forward read and equal-or-better walk-forward support.
- Does not count: positive bootstrap CI lower bound by itself, hotter aggregate small-sample holdout ROI, historical replay rows, clean rebuilds, green validators.

This keeps the closest selective-family shadow rule in the right evidence class before the broader Harville/XGBoost comparison: positive CI support can justify continued observation, but it cannot by itself promote `OP_REFINED_K7`, displace `OP_DURABLE_K7`, or change the method-family ordering.

## Decision Gate Source

These gate minimums are loaded directly from `forward_evidence_scorecard.json` `decision_gate_minimums`; `compare_main_approaches.json` also carries matching copied gate values in `decision_change_gate_minimums`. They are posture gates for future settled paper observations, not new proof from this card.

| Gate | Minimum | Threshold source | Method-family boundary |
|---|---:|---|---|
| phase8_promotion_review | 20 ROI-complete settled shadow observations | `forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations` | Opens a Phase 8 promotion-review discussion only; it does not displace the OP anchor by itself |
| anchor_displacement | 30 ROI-complete same-candidate paper observations | `forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations` | Minimum before discussing replacement of `OP_DURABLE_K7` as safest anchor |
| real_money_discussion | 100 total settled observations with usable ROI | `forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi` | Real-money discussion remains out of scope until this floor plus payout/concentration sanity checks and no BAQ-as-BEL substitution |

The 20-row Phase 8 promotion-review gate is not an anchor-displacement gate, and the 100-row real-money discussion floor is not bankroll guidance.

## Bottom Line

If Cole wants one clean method-level hierarchy right now:

1. **Selective rule path**: keep as the only paper-trade family
2. **Harville-ranked probabilities**: keep as a structural benchmark, not a paper strategy
3. **XGBoost residual correction**: keep as model research only, because prediction gains have not translated into betting gains

This card is intentionally blunt. It should make it easier to stop revisiting dead-end method families every time a modest model metric improves.
It should also stay read as a split-aware operating hierarchy, not as a formal family-level CI proof surface.
It also inherits the scorecard ranking contract, so raw Score cannot turn the selective-family OP_REFINED shadow context into an automatic promotion cue.

## Narrow Follow-Up Reads

Use the smaller guardrail artifacts below when the question is narrower than the whole method-family hierarchy:

- `CROSS_FAMILY_DECISION.md`: use when the question is how the paper-basket companion and same-family OP shadow challenger line up behind `OP_DURABLE_K7`.
- `OP_ANCHOR_METHOD_COMPARISON.md`: use when the question is specifically why `OP_DURABLE_K7` still outranks Harville while the current odds-only XGBoost path stays parked unless its evidence class changes materially.
- `AB_DOWNSTREAM_COMPARISON.md`: use when the question is specifically whether the enriched horse-history XGBoost downstream correction is strong enough to change the paper-betting answer. It is not.
- `compare_recommender_scope_paths.md`: use when the question is specifically whether widened `--allow-all-combos` scope should change the current paper default. It should not.

## Validation

- Sources: `compare_main_approaches.csv`, `compare_main_approaches.json`, `current_evidence_summary.json`, `cross_family_decision_card.csv`, `forward_evidence_scorecard.json`, `backtest_summary.csv`, `ab_downstream_comparison_results.json`
- Wrote: `method_family_decision_card.csv`, `METHOD_FAMILY_DECISION.md`
- This card is a read-only synthesis of existing frozen artifacts and comparison outputs

## Source Provenance

Exact input-byte fingerprints for this method-family card. Use them as reproducibility metadata only; they do not prove settled paper ROI, promotion readiness, live profitability, or real-money performance.

| Source | Path | Bytes | SHA-256 |
|---|---|---:|---|
| `compare_main_approaches` | `compare_main_approaches.csv` | 2646 | `ec338c61ad34500594b285d409c352232d3b5884142c68c4d8ac028c4ced9903` |
| `compare_main_approaches_json` | `compare_main_approaches.json` | 35843 | `fa683c296bf127845610a4c06a57e1da6adf9fa821486e6f728c8feba2ac667f` |
| `current_evidence_summary` | `current_evidence_summary.json` | 50352 | `f86cdd072e9b5073c59c502811c712f21d08effa75e334904c49573f86ba30b9` |
| `cross_family_decision_card` | `cross_family_decision_card.csv` | 2266 | `4be838c8552f2c0909387928a879452ce6b0a5584c2e6f30da5b4985f76059ba` |
| `forward_evidence_scorecard` | `forward_evidence_scorecard.json` | 25686 | `f9862ab5df38e02b45dc508ddffad6735bd388be5c088f1ebde3cc7dc5e08c49` |
| `backtest_summary` | `backtest_summary.csv` | 3582 | `8e7acddb70efb5554490bc99d2ad2f65abfec467790fcecc3f827c92c42e1d91` |
| `ab_downstream_comparison` | `ab_downstream_comparison_results.json` | 21070 | `d019a7819329818cc271443837f2e5be057266458770a93671a04dcfd3343d31` |
