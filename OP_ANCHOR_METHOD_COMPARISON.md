# OP Anchor vs Harville vs XGBoost

This artifact puts the strongest current OP anchor beside the two broad method families that still tend to resurface in discussion: Harville-ranked probabilities and the current XGBoost residual correction path.

## Guardrail

- This is a deployment-posture comparison, not an apples-to-apples research contest.
- `OP_DURABLE_K7` stays the safest current anchor unless new forward evidence clearly beats it.
- `CD_CORE_K8` is the primary OP/CD paper-basket companion, while `OP_REFINED_K7` remains the smaller same-family OP shadow challenger rather than a promoted default.
- Harville remains `BENCHMARK ONLY`, and XGBoost remains `RESEARCH ONLY`.
- Do not reopen the current odds-only XGBoost path unless the evidence class changes materially (for example new horse-specific features or a real downstream EV improvement); the current odds-only version is a parked dead end for now.

## Evidence Boundary

- Artifact role: OP-anchor method comparison artifact
- `valid_evidence_scope=split_aware_op_anchor_method_posture_comparison_only`
- Valid use: split-aware OP-anchor, Harville benchmark, current odds-only XGBoost posture audit, and current paper-status caveat from source-fingerprinted artifacts
- Machine-readable boundary text: This OP-anchor method comparison is split-aware posture/reproducibility metadata only: it is not new forward evidence, a live paper-trade ledger, current-day scanner output, settled ROI, live profitability, promotion readiness, or real-money evidence. Source fingerprints are reproducibility metadata only, decision gates are forward-observation requirements rather than current evidence that a gate has been cleared, and the current-paper snapshot is operator-routing context only; current PAPER_TRADE_NOW instructions must go through the combined CURRENT_EVIDENCE_SUMMARY operator_status_context/source_freshness/operator_read_gate route before use.
- This artifact is a split-aware posture/reproducibility audit only: it is not new forward evidence, a live paper-trade ledger, current-day scanner output, settled ROI, live profitability, promotion readiness, or real-money evidence.
- Source fingerprints are reproducibility metadata only; decision gates are forward-observation requirements, not current evidence that a gate has been cleared.
- Scorecard ranking contract inherited: tier-first rank is `True`; raw score is not an automatic deployment instruction (`True`). CD_CORE_K8 ranks ahead of OP_REFINED_K7 because PAPER tier outranks WATCH tier even though OP_REFINED_K7 has the higher raw forward_trust score.
- Stronger forward confidence still requires qualifying live paper signals, ROI-complete settled paper rows, settlement-quality checks, or other real forward observations.
- Anchor-review policy: forward_evidence_scorecard.json decision_gate_minimums says 20 ROI-complete settled shadow rows can only open a Phase 8 promotion review; an OP anchor-displacement discussion still needs 30+ ROI-complete same-candidate paper observations plus a cleaner split-aware read and equal-or-better walk-forward support; real-money discussion stays out of scope until 100+ total settled observations with usable ROI, payout sanity, concentration checks, and no BAQ-as-BEL substitution.
- Decision-gate source: `forward_evidence_scorecard.json` `decision_gate_minimums` (`phase8_promotion_review=20`, `anchor_displacement=30`, `real_money_discussion=100`).
- Current-paper snapshot source: `current_evidence_summary.json`; this snapshot is operator routing and settlement coverage context only, not new OP-anchor evidence.
- Non-goals: do not promote OP_REFINED_K7, reopen current odds-only XGBoost, treat Harville as live, substitute BAQ for BEL, quote current PAPER_TRADE_NOW instructions without the combined CURRENT_EVIDENCE_SUMMARY operator_status_context/source_freshness/operator_read_gate route, or discuss real-money scaling from this artifact.

## Current Read

- OP_DURABLE_K7 remains the safest current selective anchor because it still has the largest real holdout sample in the paper-candidate lane and the strongest walk-forward selection frequency, even though its own recent holdout path was uneven (2024 -47.41% on 68, 2025 +124.61% on 47) and its bootstrap CI lower bound is still -3.40%, while Harville still loses badly on a huge benchmark sample and the current odds-only XGBoost path still turns modest prediction gains into worse downstream conservative EV pass-through (-7 passes, -3.93% relative, -0.0315 percentage points of test winners); 20 ROI-complete shadow rows can open only a Phase 8 promotion review, not an OP anchor-displacement discussion, which still needs 30+ ROI-complete same-candidate paper observations plus a cleaner split-aware read and equal-or-better walk-forward support; current settled paper context remains CD-only with OP_DURABLE_K7 at 0 ROI-complete settled rows, so it is not OP-anchor forward evidence.
- Current paper-companion read: `CD_CORE_K8` is the primary OP/CD paper-basket companion and `OP_REFINED_K7` is the stronger same-family OP shadow challenger, so the paper hierarchy is more specific than just `selective beats Harville/XGBoost`.
- Paper-basket context read: structured cross-family context keeps OP_DURABLE_K7, CD_CORE_K8, and OP_REFINED_K7 in separate anchor / companion / shadow lanes before comparing Harville or current odds-only XGBoost.
- Scorecard rank-contract read: inherits the forward scorecard tier-first ranking contract: raw forward_trust/Score is support context inside a tier, not an automatic promotion queue; this is why a hotter raw OP_REFINED_K7 score still does not automatically displace the paper-basket companion or the OP anchor.
- This table keeps the OP anchor split-aware on purpose so a mixed 2024/2025 path does not get flattened into one smoother aggregate holdout number.
- Anchor caution: `OP_DURABLE_K7` is still the safest current anchor, not a statistically clean slam dunk; its bootstrap 95% CI lower bound is still `-3.40%`.
- Anchor-review threshold: forward_evidence_scorecard.json decision_gate_minimums says 20 ROI-complete settled shadow rows can only open a Phase 8 promotion review; an OP anchor-displacement discussion still needs 30+ ROI-complete same-candidate paper observations plus a cleaner split-aware read and equal-or-better walk-forward support; real-money discussion stays out of scope until 100+ total settled observations with usable ROI, payout sanity, concentration checks, and no BAQ-as-BEL substitution.

## Current Paper Snapshot

This small snapshot is copied from `current_evidence_summary.json` so the OP-anchor comparison can show the current paper-lane caveat without becoming a live-performance surface.

| Field | Current snapshot | Boundary |
|---|---|---|
| Combined operator route | current_evidence_summary.json combined route: use operator_status_context plus source_freshness.requires_refresh_before_right_now_use=False plus operator_read_gate.requires_refresh_before_evidence_read=False before quoting current PAPER_TRADE_NOW instructions from this OP-anchor artifact; recommended command=python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json. Operator context read = ops bucket/takeaway are routing metadata, not forward-performance evidence.; ops bucket = `NO TARGETS` | The combined route is instruction/evidence-read routing only; do not quote current PAPER_TRADE_NOW instructions from this artifact as no-target, clean-empty, bet-readiness, settled ROI, OP-anchor proof, promotion, live-profitability, bankroll, or real-money evidence |
| Source freshness | `current_run_date`; refresh before right-now use = `False`; bridge reference = `2026-07-17` (`America/New_York`); comparison = `generated_reference_date` / `2026-07-17`; read = Right-now source as-of date 2026-07-17 is not older than bridge reference date 2026-07-17 (America/New_York); still treat the bridge as report/navigation context rather than performance evidence. | Source freshness is operator-readiness metadata, not performance proof |
| Refresh action boundary | `./run_daily_portfolio_observation.sh` required before right-now use = `False`; settles rows / creates ROI evidence / clean-empty performance = `False` / `False` / `False` | Wrapper refresh is operator routing only; it is not settled ROI, promotion readiness, live profitability, or real-money evidence |
| Operator read gate | `current_evidence_summary.json` `operator_read_gate`: Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. Gate status = `current_operator_routing_context_only`; recommended command = `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` | The saved top card can be read as current operator routing context only; this read gate is not no-target evidence, clean-empty evidence, OP-anchor proof, bet readiness, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Bridge-published gate progress | `current_evidence_summary.json` `decision_gate_progress`: Gate progress: primary first-read 6/30; OP anchor same-candidate 0/30; Phase 8 weakest shadow 0/20; real-money discussion floor 6/100. All remain uncleared and are routing context only. Source: `forward_evidence_scorecard.json` `decision_gate_minimums`; gate status = `all_uncleared` | Current gates are all uncleared routing context only; they do not create settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Scorecard audit route | `current_evidence_summary.json` `scorecard_audit_route`: Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite drift across report-facing surfaces. Validator: `python3 validate_scorecard_ranking_contract_audit.py`; artifacts: `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json`; gate snapshot = 30/20/100 with no-BAQ-as-BEL required `True` | Report-synchronization route only; it is not forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Current bridge rebuild order | `current_evidence_summary.json` `rebuild_validation_contract`: `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes | Provenance/rebuild route only; green checks and rebuild order are not settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Current settled rule mix | OP_DURABLE_K7=0; CD_CORE_K8=6; Primary rule mix: OP_DURABLE_K7 has 0 ROI-complete settled row(s); CD_CORE_K8 has 6. Current settled paper context is CD-only, so it should not be counted as OP-anchor forward evidence. | Rule-specific settled rows stay separate; CD-only paper rows are not OP-anchor forward evidence |
| OP-anchor settlement gap | OP-anchor settlement gap: OP_DURABLE_K7 has 0 ROI-complete settled row(s); CD_CORE_K8 has 6. Need 30 more OP_DURABLE_K7 ROI-complete row(s) before the 30-row same-candidate anchor-review floor is even count-complete. CD companion rows do not reduce that OP-anchor gap. | Companion rows do not reduce the OP-anchor same-candidate review gap |
| Settlement queue state | `closed`; no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence. | Open rows are settlement workflow only; fill outcomes from result/payout evidence before interpreting ROI |
| Operator route | `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` | Use the bridge route to settle or refresh; do not infer profit, promotion, or real-money readiness from the route itself |

## Paper Basket / Shadow Context

This table keeps the current selective rule lanes visible before the broader method-family comparison. It is sourced from `cross_family_decision_card.csv` and remains posture context only.

| Rule | Lane | Split-aware evidence | WF | CI lower | Why now | What does not change |
|---|---|---:|---:|---:|---|---|
| OP_DURABLE_K7 | Safest current OP anchor (ANCHOR, P7) | +22.90% on 115; 2024 -47.41% on 68, 2025 +124.61% on 47 | 7/10 | -3.40% | Safest anchor because it has the largest OP holdout sample (115) and the strongest walk-forward selection frequency (7/10), even though the bootstrap CI lower bound still crosses zero at -3.40%. | Anchor role stays separate from companion or promotion review. n/a — this is the current anchor |
| CD_CORE_K8 | Primary OP/CD paper-basket companion (PAPER, P7) | +55.96% on 60; 2024 +45.65% on 41, 2025 +78.21% on 19 | 1/10 | -15.00% | Paper now because holdout is positive in both years (+45.65%, +78.21%), but the forward sample is still smaller than the OP anchor, walk-forward selection is only 1/10, and the bootstrap CI lower bound still crosses zero at -15.00%. | Paper-basket companion is not an anchor replacement. Needs materially more forward sample than 60 holdout races and much better walk-forward recurrence than 1/10. |
| OP_REFINED_K7 | Closest same-family OP shadow challenger (WATCH, P8) | +51.43% on 49; 2024 -25.47% on 33, 2025 +210.02% on 16 | 2/10 | +11.20% | Watch only because the ROI is attractive, but the holdout sample is only 49 races and 2024 was a losing year (-25.47%), even though the bootstrap CI lower bound is positive at +11.20%. | Shadow status stays below the 20-row promotion-review and 30-row anchor-displacement gates. Needs more forward races than 49 plus a non-losing second holdout year; 2024 is still -25.47%. |

## Comparison Table

| Approach | Role | Evidence class | Primary evidence | Sample | Secondary evidence | Why it sits here |
|---|---|---|---:|---:|---|---|
| OP_DURABLE_K7 | ANCHOR | frozen 2024-2025 holdout + walk-forward frequency | +22.90% (2024-2025 holdout ROI; 2024 -47.41% on 68, 2025 +124.61% on 47) | 115 | 7/10 (walk-forward folds selected) | Safest current anchor because it has the biggest forward sample among paper-candidate rules and the strongest walk-forward selection frequency in the OP family, but the 2024-2025 path was uneven rather than smooth and the bootstrap CI lower bound still crosses zero. |
| Harville-ranked probabilities | BENCHMARK ONLY | large-sample broad-family backtest benchmark | -24.05% (broad backtest ROI) | 90004 | 41.99% (hit rate) | Useful structural benchmark only. High hit rate does not rescue a deeply negative ROI on a huge sample. |
| XGBoost residual correction | RESEARCH ONLY | negative betting read + downstream EV A/B check | -24.16% (best ML betting ROI (ML-EV>=1.0_H6_FS5-7)) | 16724 | 4.24% payout RMSE improvement, EV winner passes -7 (-3.93%; -0.0315pp) from 178 to 171 (matched downstream read) | Prediction quality improves a bit, but the paper-betting case still does not improve because the downstream conservative EV picture stays tiny and slightly worse on pass counts. |

## Why OP_DURABLE_K7 Still Holds the Anchor

- `OP_DURABLE_K7` current forward read: `+22.90%` holdout on `115` races, but with an uneven split of `2024 -47.41% on 68` and `2025 +124.61% on 47`, plus `7/10` walk-forward folds selected.
- Anchor caution: the bootstrap 95% CI lower bound for `OP_DURABLE_K7` is still `-3.40%`, so “safest current anchor” is a deployment ranking, not proof of a clean positive lower-bound edge.
- `CD_CORE_K8` is still the primary OP/CD paper-basket companion because it stayed paper-worthy without displacing the anchor, while `OP_REFINED_K7` remains the narrower same-family shadow challenger.
- `OP_REFINED_K7` remains interesting but not promoted: `+51.43%` holdout on only `49` races, with `2/10` walk-forward selection.
- The broader selective family still has the strongest current deployment case through `Phase 7 OP/CD rule-component basket` (`PAPER NOW`) at `+38.68%` holdout on `175` races, but that portfolio result was also uneven: `2024 +0.37% on 109` and `2025 +105.38% on 66`, with `+31.34%` frozen replay on walk-forward test years on `806` races.
- That broader selective-family secondary line is replay context only, not extra train-only validation.

## OP_REFINED_K7 Challenger Diagnostic

- OP_REFINED_K7 has the hotter aggregate holdout ROI and positive bootstrap CI lower bound, but it is still only 49 holdout races (42.61% of the OP_DURABLE_K7 sample), lost 2024, and has only 2/10 walk-forward selections versus 7/10 for the anchor; treat this as shadow evidence until the separate 20-row promotion-review and 30-row anchor-displacement paper-observation gates are actually met.
- Scorecard diagnostic source: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` (`ci_only_promotion_allowed=false`).
- Sample support: `OP_REFINED_K7` has `49` holdout races versus `115` for `OP_DURABLE_K7` (`42.61%` of the anchor sample; `66` fewer races).
- Walk-forward support: `OP_REFINED_K7` was selected in `2/10` folds versus `7/10` for `OP_DURABLE_K7` (`5` fewer folds).
- CI nuance: `OP_REFINED_K7` has a positive CI lower bound (`+11.20%`) while `OP_DURABLE_K7` still crosses zero (`-3.40%`), but the smaller sample, losing 2024 split, and lower walk-forward support keep it in shadow/watch mode rather than anchor status.
- CI-only promotion check: A positive bootstrap CI lower bound is useful support context, but it is not enough by itself to promote OP_REFINED_K7 or displace OP_DURABLE_K7 because the challenger still has a smaller holdout sample, a losing 2024 split, lower walk-forward recurrence, and no ROI-complete paper observations clearing the separate promotion or anchor-review gates.

## Why the Other Two Still Do Not Dislodge It

- Harville remains benchmark-only because its best honest family read is still negative on a huge sample: `-24.05%` over `90004` races.
- The current odds-only XGBoost path remains research-only because its best betting line is still negative (`-24.16%` on `16724` races), and its matched downstream read now says that better payout prediction still comes with weaker conservative EV pass-through rather than a paper-path upgrade.

## What Would Change This Answer

- A challenger only dislodges `OP_DURABLE_K7` with cleaner forward evidence: more holdout races or a meaningfully stronger split-aware holdout read plus equal-or-better walk-forward support, not just a hotter aggregate ROI on a smaller sample.
- Harville stays parked unless a broad benchmark family flips positive on a large honest sample instead of only on a tiny slice or a prettier presentation layer.
- The current odds-only XGBoost path stays parked unless the evidence class changes materially — for example through horse-specific features or a real downstream EV pass-through improvement that creates a paper-betting case. Until then, treat it as a dead end and move on.

## Decision Gates Before Changing the Anchor

These gates keep the OP decision tied to new forward observations rather than another prettier replay table.

| Gate | Current rule | Evidence required before change | Evidence scope |
|---|---|---|---|
| same-family OP challenger | Keep OP_DURABLE_K7 as anchor; keep OP_REFINED_K7 shadow-only. | Collect 20+ ROI-complete settled shadow observations for OP_REFINED_K7 before even a Phase 8 promotion review; an anchor-displacement discussion needs 30+ ROI-complete same-candidate paper observations plus a cleaner split-aware read and equal-or-better walk-forward support than OP_DURABLE_K7, not merely a hotter aggregate ROI. | Future settled `phase8_shadow` paper-trade ledger rows with complete ROI coverage; the 20-row promotion-review gate and 30-row anchor-displacement gate are separate, and historical replay or holdout rows do not count as new promotion or anchor-displacement evidence. |
| current odds-only XGBoost reopening | Keep the current odds-only XGBoost path parked. | Reopen only if the evidence class changes materially, such as horse-specific features or a downstream EV pass-through improvement that creates a paper-betting case; do not rerun odds-only tuning as if it were new evidence. | A materially different feature/data class plus downstream betting pass-through; another odds-only rerun is not a new evidence class. |
| BEL/BAQ substitution | Keep BEL dormant and do not substitute BAQ for BEL. | Wait for Belmont forward races; BAQ remains a separate track because the BEL->BAQ bridge failed the strict chronological read. | Fresh Belmont qualifying races only; BAQ needs independent evidence and cannot inherit BEL history. |
| real-money scaling | Paper trade only. | Do not consider real-money scaling until 100+ paper observations have settled with positive ROI plus concentration and payout-distribution checks. | Settled paper-trade ledger observations with usable ROI coverage, not clean scans, open signals, or replay backtests. |

## Bottom Line

- If Cole wants one OP-centered answer right now, keep `OP_DURABLE_K7` as the safest anchor.
- Treat `CD_CORE_K8` as the primary OP/CD paper-basket companion and `OP_REFINED_K7` as the smaller same-family shadow challenger, not as reasons to demote the anchor prematurely.
- Keep the broader selective rule path as the only `PAPER NOW` family.
- Keep Harville as the structural benchmark and XGBoost as research, not as live-decision challengers.
- Park the current odds-only XGBoost path unless a materially different evidence class appears; the current version is a documented dead end, not a near-promotion candidate.

## Source Provenance

Exact input-byte fingerprints for this OP-anchor comparison. Use them as reproducibility metadata only; they do not prove live paper-trade edge, promotion readiness, live profitability, or real-money performance.

- Source scope: read-only synthesis of frozen scorecard CSV/JSON, compare-main, method-family, cross-family, downstream A/B, and current-evidence bridge artifacts
- Evidence boundary: source fingerprints prove exact input-byte provenance and render reproducibility only; they are not live paper-trade evidence, promotion readiness, live profitability, or real-money evidence.

| Source | File | Bytes | SHA-256 |
|---|---|---:|---|
| ab_downstream_comparison_results | `ab_downstream_comparison_results.json` | 21224 | `f6d39388240488378cc8ead707284591cb8bca223b5b0e1cf698743643faf16f` |
| compare_main_approaches | `compare_main_approaches.csv` | 2646 | `ec338c61ad34500594b285d409c352232d3b5884142c68c4d8ac028c4ced9903` |
| cross_family_decision_card | `cross_family_decision_card.csv` | 2266 | `4be838c8552f2c0909387928a879452ce6b0a5584c2e6f30da5b4985f76059ba` |
| current_evidence_summary | `current_evidence_summary.json` | 50352 | `f86cdd072e9b5073c59c502811c712f21d08effa75e334904c49573f86ba30b9` |
| forward_evidence_scorecard | `forward_evidence_scorecard.csv` | 6955 | `39d2dc6fd0f929060ce6678d58f409c5bdd090563cbc6af41941674159811174` |
| forward_evidence_scorecard_json | `forward_evidence_scorecard.json` | 25686 | `f9862ab5df38e02b45dc508ddffad6735bd388be5c088f1ebde3cc7dc5e08c49` |
| method_family_decision_card | `method_family_decision_card.csv` | 2083 | `95403d8b2a032c9e6fc294fc6dbe02749b58c94dee57ec338e8e312130b41999` |

## Validation

- Sources: `forward_evidence_scorecard.csv`, `forward_evidence_scorecard.json`, `compare_main_approaches.csv`, `method_family_decision_card.csv`, `cross_family_decision_card.csv`, `ab_downstream_comparison_results.json`, `current_evidence_summary.json`
- Wrote: `OP_ANCHOR_METHOD_COMPARISON.md`, `op_anchor_method_comparison.json`
- This artifact is a read-only synthesis of the frozen scorecard, decision cards, downstream A/B evidence, and the current-evidence bridge snapshot
