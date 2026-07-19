# Portfolio Decision Card

This note compares the three portfolio-level choices that matter most right now:
the **Phase 7 OP/CD rule-component basket**, the **Phase 8 frozen portfolio**, and the **train-only yearly selector**.

Short answer:
- **Paper trade the Phase 7 OP/CD rule-component basket first, with daily preflight confirming target cards**
- **Keep the Phase 8 frozen portfolio as a shadow challenger, not the default**
- **Use the train-only yearly selector as an honest benchmark, not as the operating recipe**
- **These roles are copied from `compare_main_approaches.csv` deployment posture so the portfolio card cannot drift from the main comparison harness**
- **Evidence scope:** `valid_evidence_scope=split_aware_portfolio_decision_hierarchy_only`; this card is a frozen/report portfolio hierarchy only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- **Inherited scorecard ranking contract:** rank is tier-first (`True`), Score is secondary within tier (`True`), and raw Score is not an automatic deployment instruction (`True`)
- **Scorecard CI-only promotion check:** `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` says `ci_only_promotion_allowed=false`; the positive OP_REFINED CI lower bound is support context only, not a portfolio-level Phase 8 default trigger.
- **Inherited operator read gate:** `compare_main_approaches.json` `current_operator_boundary.operator_read_gate` says Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. This is routing context only, not no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money evidence.
- **Bridge-published current gate progress:** `current_evidence_summary.json` `decision_gate_progress` says Gate progress: primary first-read 6/30; OP anchor same-candidate 0/30; Phase 8 weakest shadow 0/20; real-money discussion floor 6/100. All remain uncleared and are routing context only. This is routing context only, not portfolio-ranking evidence.
- **Current bridge rebuild order:** `current_evidence_summary.json` `rebuild_validation_contract` routes source-byte changes through `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not portfolio-ranking evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- **Scorecard audit route:** `current_evidence_summary.json` `scorecard_audit_route` says Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite drift across report-facing surfaces. This is report-synchronization metadata only, not portfolio-ranking evidence, forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- **Inherited decision-change gates:** `phase8_promotion_review=20`, `anchor_displacement=30`, and `real_money_discussion=100` come from `compare_main_approaches.json` `decision_change_gate_minimums`, which source them from `forward_evidence_scorecard.json`
- **This card is split-aware, not CI-backed at the portfolio level**: the frozen portfolio sources used here do not publish a portfolio bootstrap lower bound, so read the year splits and secondary-context basis as the caution surface instead of treating the roles as formal CI-proof rankings.

## Comparison Table

| Approach | Role | Holdout ROI | Holdout Races | 2024 ROI / N | 2025 ROI / N | Secondary ROI | Secondary Races | Secondary Years+ | Secondary Basis | Why It Sits Here |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Phase 7 OP/CD rule-component basket | PAPER NOW | +38.68% | 175 | +0.37% / 109 | +105.38% / 66 | +31.34% | 806 | 9/10 | frozen replay on walk-forward test years | Best current paper baseline because it has the strongest 2024-2025 holdout result (+38.68% on 175 races). Its split was +0.37% on 109 races in 2024 versus +105.38% on 66 in 2025, so the headline is real but not smooth. BEL contributes zero 2024-2025 holdout races here, so the Phase 7 holdout read is effectively OP/CD historical evidence. Its secondary read is only a frozen replay on the walk-forward test years, not an extra train-only validation layer. |
| Phase 8 frozen portfolio | SHADOW ONLY | +21.45% | 118 | +9.50% / 85 | +50.26% / 33 | +55.04% | 625 | 10/10 | frozen replay on walk-forward test years | Useful challenger, but it underperformed Phase 7 on holdout (+21.45% vs +38.68%) despite adding more mined rules and more weak legs. Its split was still smaller at +9.50% on 85 races in 2024 and +50.26% on 33 in 2025, and its prettier secondary line is also only a frozen replay on the walk-forward test years. |
| Train-only yearly selector | BENCHMARK ONLY | +14.36% | 65 | -19.95% / 45 | +98.37% / 20 | +22.46% | 470 | 8/10 | actual train-only walk-forward | Most honest validation benchmark, not the best daily operating default. Its actual train-only walk-forward ROI is still valuable context (+22.46% on 470 races), but its current 2024-2025 holdout is only +14.36% on 65 races, with a split of -19.95% on 45 races in 2024 versus +98.37% on 20 in 2025. |

## Why This Ordering Is Conservative

This portfolio layer is intentionally anchored to the frozen 2024-2025 split and a split secondary context. Unlike the rule-level cards, it does not carry a published portfolio bootstrap CI lower bound from the frozen sources, so the caution lives in the split behavior, sample support, and whether the secondary line is a frozen replay or an actual train-only walk-forward read rather than in a portfolio-level CI field.

- **Phase 7 OP/CD rule-component basket (PAPER NOW)**: Use as the primary paper-trade basket if Cole wants one frozen portfolio today.
  - Why: Best current paper baseline because it has the strongest 2024-2025 holdout result (+38.68% on 175 races). Its split was +0.37% on 109 races in 2024 versus +105.38% on 66 in 2025, so the headline is real but not smooth. BEL contributes zero 2024-2025 holdout races here, so the Phase 7 holdout read is effectively OP/CD historical evidence. Its secondary read is only a frozen replay on the walk-forward test years, not an extra train-only validation layer.
  - Caution: 2024 was basically flat (+0.37% on 109 races) and most of the aggregate holdout edge came from 2025 (+105.38% on 66), so this is still volatile even though the two-year holdout is strongest overall.
- **Phase 8 frozen portfolio (SHADOW ONLY)**: Track as a shadow basket, not as the default, until it beats Phase 7 on more forward data.
  - Why: Useful challenger, but it underperformed Phase 7 on holdout (+21.45% vs +38.68%) despite adding more mined rules and more weak legs. Its split was still smaller at +9.50% on 85 races in 2024 and +50.26% on 33 in 2025, and its prettier secondary line is also only a frozen replay on the walk-forward test years.
  - Caution: Its better replay headline on the walk-forward test years is not enough to offset the weaker current holdout, the smaller two-year split (2024 +9.50% on 85; 2025 +50.26% on 33), and the negative holdout legs inside the basket.
- **Train-only yearly selector (BENCHMARK ONLY)**: Keep as the honest benchmark for reports and sanity checks, not as the daily operating recipe.
  - Why: Most honest validation benchmark, not the best daily operating default. Its actual train-only walk-forward ROI is still valuable context (+22.46% on 470 races), but its current 2024-2025 holdout is only +14.36% on 65 races, with a split of -19.95% on 45 races in 2024 versus +98.37% on 20 in 2025.
  - Caution: Its honest benchmark value comes with a very lopsided recent split (-19.95% on 45 in 2024, +98.37% on 20 in 2025), and some historical folds used the old BEL bridge candidate, so it should stay a benchmark artifact rather than a clean deployment rulebook.

Scorecard rank-contract override: CD_CORE_K8 ranks ahead of OP_REFINED_K7 because PAPER tier outranks WATCH tier even though OP_REFINED_K7 has the higher raw forward_trust score.

## Head-to-Head vs. Phase 7

| Approach | Holdout ROI vs Phase 7 | Holdout Races vs Phase 7 | Practical Read |
|---|---:|---:|---|
| Phase 8 frozen portfolio | -17.23% | -57 | Track as a shadow basket, not as the default, until it beats Phase 7 on more forward data. |
| Train-only yearly selector | -24.32% | -110 | Keep as the honest benchmark for reports and sanity checks, not as the daily operating recipe. |

## Bottom Line

If Cole wants one portfolio-level decision tonight:

1. **Run the Phase 7 OP/CD rule-component basket as the primary paper baseline, with target cards confirmed by daily preflight**
2. **Log the Phase 8 frozen portfolio separately as a shadow basket**
3. **Keep citing the train-only yearly selector as the honest validation yardstick**

That ordering keeps the paper choice tied to the strongest current holdout result instead of to the prettiest mined basket or the most abstract validation artifact.
It also keeps the fixed portfolios from quietly borrowing replay-on-walk-forward-years numbers as if they were extra train-only proof.
It also keeps the portfolio card on the same deployment-posture labels as the main comparison harness, so score ordering and operating advice stay separated consistently.
It also inherits the scorecard ranking contract, so raw Score cannot turn a shadow Phase 8 / OP_REFINED line into an automatic promotion cue.
Because the frozen portfolio sources do not publish a portfolio bootstrap lower bound here, this note should stay read as a split-aware operating ranking, not as a formal CI-backed proof surface.

## Scorecard CI-Only Promotion Check

Source: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7`
- Current decision: Keep OP_REFINED_K7 shadow/watch only.
- CI-only promotion allowed: `false`
- Why not: smaller holdout sample than OP_DURABLE_K7, losing 2024 holdout split, lower walk-forward recurrence than OP_DURABLE_K7, uncleared phase8_promotion_review paper-observation gate, uncleared anchor_displacement paper-observation gate.
- Required before review: phase8 promotion review = 20+ ROI-complete candidate shadow observations plus cleaner split-aware/walk-forward support; anchor displacement = 30+ ROI-complete same-candidate paper observations plus a cleaner split-aware forward read and equal-or-better walk-forward support.
- Does not count: positive bootstrap CI lower bound by itself, hotter aggregate small-sample holdout ROI, historical replay rows, clean rebuilds, green validators.

## Current Operator Boundary

This context is inherited from `compare_main_approaches.json` / `current_evidence_summary.json` so the portfolio card points to the current paper-workflow boundary without using it as portfolio-ranking evidence.

| Field | Current bridge read | Evidence boundary |
|---|---|---|
| Source freshness | `current_run_date`; refresh before right-now use = `False`; bridge reference = `2026-07-17` (`America/New_York`); comparison = `generated_reference_date` / `2026-07-17`; read = Right-now source as-of date 2026-07-17 is not older than bridge reference date 2026-07-17 (America/New_York); still treat the bridge as report/navigation context rather than performance evidence. | Source freshness is operator-readiness metadata, not portfolio-ranking or performance proof |
| Operator read gate | `compare_main_approaches.json` `current_operator_boundary.operator_read_gate`: Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. Gate status = `current_operator_routing_context_only`; recommended command = `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` | The saved top card can be read as current operator routing context only; this read gate is not no-target evidence, clean-empty evidence, bet readiness, settled ROI, portfolio-ranking evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Bridge-published gate progress | `current_evidence_summary.json` `decision_gate_progress`: Gate progress: primary first-read 6/30; OP anchor same-candidate 0/30; Phase 8 weakest shadow 0/20; real-money discussion floor 6/100. All remain uncleared and are routing context only. Source: `forward_evidence_scorecard.json` `decision_gate_minimums`; gate status = `all_uncleared` | Current gates are all uncleared routing context only; this does not change the portfolio ordering or create settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence |
| Current bridge rebuild order | `current_evidence_summary.json` `rebuild_validation_contract`: `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes | Rebuild route only; it is not portfolio-ranking evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Scorecard audit route | `current_evidence_summary.json` `scorecard_audit_route`: Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite drift across report-facing surfaces. Validator: `python3 validate_scorecard_ranking_contract_audit.py`; artifacts: `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json`; gate snapshot = 30/20/100 with no-BAQ-as-BEL required `True` | Report-synchronization route only; it is not portfolio-ranking evidence, forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Current settled rule mix | OP_DURABLE_K7=0; CD_CORE_K8=6; Primary rule mix: OP_DURABLE_K7 has 0 ROI-complete settled row(s); CD_CORE_K8 has 6. Current settled paper context is CD-only, so it should not be counted as OP-anchor forward evidence. | Current settled sample is CD-only context, not OP-anchor forward evidence or a portfolio-ranking change |
| Stale-card refresh boundary | run `./run_daily_portfolio_observation.sh` before using stale right-now instructions; a wrapper refresh can update operator surfaces, but by itself it does not settle open rows, create ROI-complete evidence, promote OP_DURABLE_K7, or support real-money discussion.; clean-empty forward performance = `False` | Wrapper refresh can update operator surfaces, but it cannot settle rows, create ROI-complete evidence, promote OP_DURABLE_K7, count clean-empty refreshes as performance, or support live-profitability / real-money claims |
| Settlement queue state | `closed`; no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence. | Open rows are settlement workflow only; fill outcomes from actual result/payout evidence before interpreting ROI |
| Recommendation context | Latest run context: the latest live scan completed cleanly and found no qualifying races across 52 card(s) and 446 race(s). Treat this as operator context only; use recommendation and settlement ledgers before interpreting bet readiness or forward performance. | Latest recommendation-state context is operator routing only, not bet readiness or forward-performance evidence |
| Operator route | `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` | Use the route as the current operator action; do not infer profit, promotion, or real-money readiness from the route itself |

The current operator boundary is routing/provenance context only. It does not change the Phase 7 vs Phase 8 vs train-only selector ordering above, and it is not settled ROI, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

## Decision Gate Source

These gate minimums are inherited from `compare_main_approaches.json` `decision_change_gate_minimums`; compare-main records their `threshold_source` keys as `forward_evidence_scorecard.json` `decision_gate_minimums`. They are posture gates for future settled paper observations, not new proof from this card.

| Gate | Minimum | Threshold source | Portfolio read |
|---|---:|---|---|
| phase8_promotion_review | 20 ROI-complete settled shadow observations | `forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations` | Opens a Phase 8 portfolio/shadow-basket promotion-review discussion only; it does not make Phase 8 the default |
| anchor_displacement | 30 ROI-complete same-candidate paper observations | `forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations` | Minimum before discussing replacement of `OP_DURABLE_K7` as safest anchor or treating the Phase 7 ordering as displaced |
| real_money_discussion | 100 total settled observations with usable ROI | `forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi` | Real-money discussion remains out of scope until this floor plus payout/concentration sanity checks and no BAQ-as-BEL substitution |

The 20-row Phase 8 promotion-review gate is not the 30-row anchor-displacement gate, and the 100-row real-money discussion floor is not bankroll guidance.

## Validation

- Sources: `compare_main_approaches.csv`, `compare_main_approaches.json`, `frozen_portfolio_eval_summary.csv`, `walk_forward_validation_folds.csv`, `forward_evidence_scorecard.json`, `current_evidence_summary.json`
- Wrote: `portfolio_decision_card.csv`, `PORTFOLIO_DECISION_CARD.md`
- This card is a read-only synthesis of frozen evaluation artifacts

## Source Provenance

Exact input-byte fingerprints for this portfolio card. Use them as reproducibility metadata only; they do not prove settled paper ROI, promotion readiness, live profitability, or real-money performance.

| Source | Path | Bytes | SHA-256 |
|---|---|---:|---|
| `compare_main_approaches` | `compare_main_approaches.csv` | 2646 | `ec338c61ad34500594b285d409c352232d3b5884142c68c4d8ac028c4ced9903` |
| `compare_main_approaches_json` | `compare_main_approaches.json` | 35843 | `fa683c296bf127845610a4c06a57e1da6adf9fa821486e6f728c8feba2ac667f` |
| `frozen_portfolio_eval` | `frozen_portfolio_eval_summary.csv` | 5184 | `98ac5d1cd74861c080e4fc096fe4f3a5bc4102100a950a8186cc9f9c0af9f18d` |
| `walk_forward_folds` | `walk_forward_validation_folds.csv` | 1424 | `89f1be7dc878f25b52dfe2f4e892ccc4e8c57ea84c6e98c1cbd8442f37a690b8` |
| `forward_evidence_scorecard` | `forward_evidence_scorecard.json` | 25686 | `f9862ab5df38e02b45dc508ddffad6735bd388be5c088f1ebde3cc7dc5e08c49` |
| `current_evidence_summary` | `current_evidence_summary.json` | 50352 | `f86cdd072e9b5073c59c502811c712f21d08effa75e334904c49573f86ba30b9` |
