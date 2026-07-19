# Main Approach Comparison

## Usage

```bash
python3 compare_main_approaches.py
```

This is a fast comparison harness. It replays a small fixed set of methods and reads the existing walk-forward artifacts. It does not run a new broad search.

## Scope

- Holdout focus: 2024-2025
- This harness is intentionally locked to the frozen 2024-2025 holdout standard so the main comparison surface cannot drift onto a different evaluation window.
- Walk-forward test-year window: next-year tests across 2015-2025, excluding 2021 because the project data excludes that year
- Secondary context is intentionally split: fixed methods get frozen replays on those walk-forward test years, while dynamic selectors keep their actual train-only walk-forward totals
- No new BEL->BAQ aliasing is introduced here
- Conservative score weights holdout consistency and holdout sample size more than flashy ROI
- Deployment posture is the operator-facing label. Score is evidence ordering only, not an auto-promotion rule.
- Inherited scorecard ranking contract: rank is tier-first (`True`), forward_trust/Score is secondary within tier (`True`), and raw score is not an automatic deployment instruction (`True`).
- Settlement-audit and ledger-quality surfaces are operational guardrails; they do not change this comparison without ROI-complete settled outcomes.
- Output bundle: `compare_main_approaches.csv`, `compare_main_approaches.md`, and `compare_main_approaches.json` are generated together; the JSON sidecar publishes machine-readable evidence_boundary metadata plus the method-family evidence-debt checklist for automation, not live paper-trade or promotion evidence.

## Evidence Boundary

- Artifact role: main approach comparison bundle
- `valid_evidence_scope=frozen_main_approach_comparison_only`
- Valid use: frozen 2024-2025 holdout, train-only walk-forward, method-family, and paper-lane posture comparison
- This bundle is a frozen comparison/reproducibility surface only: it is not new forward evidence, a live paper-trade ledger, current-day scanner output, settled ROI, live profitability, promotion readiness, or real-money evidence.
- Source fingerprints are reproducibility metadata only; row-identical source-byte drift changes provenance only, not ranked rows or performance evidence.
- Decision-change gates are forward-observation requirements, not evidence that a gate has already been cleared.
- Scorecard rank contract inherited: CD_CORE_K8 ranks ahead of OP_REFINED_K7 because PAPER tier outranks WATCH tier even though OP_REFINED_K7 has the higher raw forward_trust score.
- Non-goals: do not promote OP_REFINED_K7 or Phase 8, reopen current odds-only XGBoost, treat Harville as live, substitute BAQ for BEL, quote current `PAPER_TRADE_NOW` instructions without the combined `CURRENT_EVIDENCE_SUMMARY.md` / `operator_status_context` / `source_freshness` / `operator_read_gate` route, or discuss real-money scaling from this artifact.
- Current-evidence bridge data, when shown below, is operator-routing context only and does not convert open signals, recommendation-state context, source freshness, or settlement queue rows into settled ROI or bet readiness.

## Current Operator Boundary Snapshot

This small snapshot is copied from `current_evidence_summary.json` so the comparison report can point to the current settlement boundary without becoming a live-paper performance surface.

| Field | Current bridge read | Evidence boundary |
|---|---|---|
| Source freshness | `current_run_date`; refresh before right-now use = `False` | Source freshness is operator-readiness metadata, not performance proof |
| Source freshness reference | bridge reference date `2026-07-17` in `America/New_York`; compared via `generated_reference_date` = `2026-07-17`; right-now as-of `2026-07-17` / run `2026-07-17` | Reference-date routing is reproducibility metadata for stale-card checks, not performance proof |
| Refresh action boundary | `./run_daily_portfolio_observation.sh` required before right-now use = `False`; source action current before refresh = `True`; can update operator surfaces = `True`; settles rows / creates ROI evidence / clean-empty performance = `False` / `False` / `False` | Wrapper refresh is operator routing only; it is not settled ROI, promotion readiness, live profitability, or real-money evidence |
| Source consistency | overall match = `True` | Fingerprints and bridge consistency are reproducibility checks only |
| Bridge-published gate progress | `current_evidence_summary.json` `decision_gate_progress`: Gate progress: primary first-read 6/30; OP anchor same-candidate 0/30; Phase 8 weakest shadow 0/20; real-money discussion floor 6/100. All remain uncleared and are routing context only. Source: `forward_evidence_scorecard.json` `decision_gate_minimums`; gate status = `all_uncleared` | Current gates are all uncleared routing context only; they do not create settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Scorecard audit route | `current_evidence_summary.json` `scorecard_audit_route`: Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite drift across report-facing surfaces. Validator: `python3 validate_scorecard_ranking_contract_audit.py`; artifacts: `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json`; gate snapshot = 30/20/100 with no-BAQ-as-BEL required `True` | Report-synchronization route only; it is not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Current bridge rebuild order | `current_evidence_summary.json` `rebuild_validation_contract`: `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes | Provenance/rebuild route only; green checks and rebuild order are not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Operator read gate | `current_evidence_summary.json` `operator_read_gate`: Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. Gate status = `current_operator_routing_context_only`; recommended command = `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` | The saved top card can be read as current operator routing context only; this read gate is not no-target evidence, clean-empty evidence, bet readiness, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Current settled rule mix | OP_DURABLE_K7=0; CD_CORE_K8=6; Primary rule mix: OP_DURABLE_K7 has 0 ROI-complete settled row(s); CD_CORE_K8 has 6. Current settled paper context is CD-only, so it should not be counted as OP-anchor forward evidence. | Rule-specific settled rows stay separate; CD-only paper rows are not OP-anchor forward evidence |
| Settlement queue state | `closed`; no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence. | Open rows are settlement workflow only; fill outcomes from result/payout evidence before interpreting ROI |
| Recommendation context | Latest run context: the latest live scan completed cleanly and found no qualifying races across 52 card(s) and 446 race(s). Treat this as operator context only; use recommendation and settlement ledgers before interpreting bet readiness or forward performance. | Latest recommendation-state context is operator routing only, not bet readiness or forward-performance evidence |
| Operator route | `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` | Use the bridge route to settle or refresh; do not infer profit, promotion, or real-money readiness from the route itself |

## Source Provenance

These fingerprints identify the exact input files used by this comparison rerender. main-comparison render/sidecar only; source fingerprints, clean rebuilds, and validator passes are reproducibility metadata, not live paper-trade evidence, settled ROI, live profitability, promotion readiness, or real-money evidence; current top-card/operator routing belongs in CURRENT_EVIDENCE_SUMMARY.md / current_evidence_summary.json via the combined operator_status_context/source_freshness/operator_read_gate route.

| Source | Path | Bytes | SHA-256 |
|---|---|---:|---|
| phase5_race_cache | `phase5_race_cache.pkl` | 6876552 | `9f38ab5d34cac72175c7ae2126a33bd798a683fdf15f862afffc17632a6084e6` |
| phase7_live_rules | `phase7_live_rules.json` | 1470 | `24f9f071ba7d47937f9b71e9b735cf7cf330ff3debb3d350459310316d9c1b7d` |
| walk_forward_folds | `walk_forward_validation_folds.csv` | 1424 | `89f1be7dc878f25b52dfe2f4e892ccc4e8c57ea84c6e98c1cbd8442f37a690b8` |
| walk_forward_rules | `walk_forward_validation_rules.csv` | 21202 | `5a1d4edaa27b106b81cd0b355e495c6ff89bf5c2f8891363435eac15e121753e` |
| forward_evidence_scorecard | `forward_evidence_scorecard.csv` | 6955 | `39d2dc6fd0f929060ce6678d58f409c5bdd090563cbc6af41941674159811174` |
| forward_evidence_scorecard_json | `forward_evidence_scorecard.json` | 25686 | `f9862ab5df38e02b45dc508ddffad6735bd388be5c088f1ebde3cc7dc5e08c49` |
| current_evidence_summary_json | `current_evidence_summary.json` | 50352 | `f86cdd072e9b5073c59c502811c712f21d08effa75e334904c49573f86ba30b9` |
| cross_family_decision_card | `cross_family_decision_card.csv` | 2266 | `4be838c8552f2c0909387928a879452ce6b0a5584c2e6f30da5b4985f76059ba` |
| backtest_summary | `backtest_summary.csv` | 3582 | `8e7acddb70efb5554490bc99d2ad2f65abfec467790fcecc3f827c92c42e1d91` |
| ab_downstream_comparison_results | `ab_downstream_comparison_results.json` | 21070 | `d019a7819329818cc271443837f2e5be057266458770a93671a04dcfd3343d31` |

## Cole's One-Screen Read

Use this when the full report is too much and Cole needs the decision-safe answer first. This is a routing summary, not new forward evidence.

| Question | Current read | Evidence boundary |
|---|---|---|
| What is the primary paper-basket core? | Keep `OP_DURABLE_K7` as the anchor and `CD_CORE_K8` as the primary paper-basket companion | Paper only; daily target-card availability still comes from the current preflight, and real-money confidence still needs 100+ settled ledger observations with usable ROI coverage plus concentration and payout checks |
| What is the closest challenger? | `OP_REFINED_K7` is the closest same-family OP shadow, not a promoted default | Promotion review needs 20+ future settled shadow ledger observations; replacing the anchor needs 30+ ROI-complete same-candidate observations plus cleaner split-aware/walk-forward support |
| Does Harville change the current paper path? | No — Harville remains BENCHMARK ONLY | Current broad replay is -24.05% ROI despite a 41.99% hit rate; it needs positive betting evidence, not just calibration value |
| Does current odds-only XGBoost change the current paper path? | No — current odds-only XGBoost remains RESEARCH ONLY / parked | Best ML betting ROI is -24.16%; another odds-only replay is not enough to reopen it |
| Do clean scans or settlement audits change posture? | No — clean scans, open signals, and ledger/settlement audits are operability checks, not performance proof | They can reveal missing templates or ROI-coverage gaps; only settled hit/miss rows with usable return/cost coverage can feed future decision changes |
| Can BAQ stand in for BEL? | No — keep `BEL_BROAD1_K7` dormant until fresh Belmont races exist | BAQ needs independent evidence and must not inherit BEL's rule |

## Method-Family Action Summary

Use this when the comparison question is Harville vs current odds-only XGBoost vs the selective OP/CD path. It is an action map, not a profitability upgrade.

| Family | Use it for now | Do not use it for | Next valid evidence |
|---|---|---|---|
| Selective rule path | Paper-observe `OP_DURABLE_K7` + `CD_CORE_K8` and keep `OP_REFINED_K7` shadow-only | Real-money confidence or anchor changes before settled ROI-complete paper observations | 100+ settled paper observations with usable ROI coverage for confidence; 20+ settled shadow observations before `OP_REFINED_K7` promotion review; 30+ same-candidate ROI-complete observations plus cleaner split-aware/walk-forward support before anchor displacement |
| Harville-ranked probabilities | Calibration and benchmark sanity checks | Paper-bet selection or deployment promotion from hit rate alone | Positive frozen-holdout or train-only walk-forward betting evidence; calibration-only summaries do not change posture |
| Current odds-only XGBoost correction path | Research-only diagnostics for what odds-derived models can and cannot add | Reopening the betting path from another odds-only replay or payout-model metric | A materially richer non-odds feature/data class, downstream betting pass-through improvement, and then settled paper observations |

- Action map verdict: spend operational energy on settled selective paper observations first; Harville and current odds-only XGBoost stay comparison controls unless their evidence class changes. Settlement-audit repairs can make future rows usable, but audit cleanliness alone does not promote any lane.

## OP Challenger Support Check

This narrow check keeps OP_REFINED_K7's positive CI lower bound in the right evidence class before the broader method tables.

- Scorecard diagnostic source: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` (`ci_only_promotion_allowed=false`).
- `OP_REFINED_K7` has `49` holdout races versus `115` for `OP_DURABLE_K7` (`42.61%` of the anchor sample; `66` fewer races).
- Walk-forward support is `2/10` versus `7/10` for the anchor, a `5`-fold deficit.
- CI-only promotion check: A positive bootstrap CI lower bound is useful support context, but it is not enough by itself to promote OP_REFINED_K7 or displace OP_DURABLE_K7; the challenger still has a smaller holdout sample, a losing holdout-year split, lower walk-forward recurrence, and no ROI-complete paper observations clearing the separate promotion or anchor-review gates.
- Practical read: positive CI support can keep OP_REFINED_K7 on the closest-shadow watch list, but it cannot by itself promote the rule, displace OP_DURABLE_K7, or change the OP/CD paper core.

## Method-Family Evidence Debt Checklist

Use this before starting another experiment. It states what is still missing, what would be an invalid shortcut, and the next honest action for each family.

| Family | Still missing | Invalid shortcut | Next honest action |
|---|---|---|---|
| Selective OP/CD rule path | Future settled OP/CD paper rows with usable ROI coverage; `OP_REFINED_K7` also needs 20+ complete shadow rows before promotion review; 30+ same-candidate rows before anchor displacement; 100+ total ROI-complete observations before any real-money discussion | Treating old holdout/replay rows, clean scans, open signals, or a settlement-audit pass as posture-changing proof | Keep collecting and settling `OP_DURABLE_K7` + `CD_CORE_K8` observations; log `OP_REFINED_K7` as shadow-only until the explicit gates are met |
| Harville-ranked probabilities | Positive betting evidence on frozen holdout or train-only walk-forward terms, not just broad hit-rate/calibration context | Promoting from a 41.99% hit rate while the broad betting replay is -24.05% ROI | Keep Harville as a benchmark/calibration sanity check unless a future betting-evidence surface turns positive |
| Current odds-only XGBoost correction path | A materially richer non-odds feature/data class, downstream betting pass-through improvement, and then settled paper observations | Reopening from another odds-only rerun, payout-RMSE gain, or model-fit-only downstream A/B result while betting ROI remains -24.16% | Keep the current odds-only XGBoost path parked; reopen only if the feature class changes and the betting pass-through improves before paper observation |

- Gate floors in this checklist are loaded from `forward_evidence_scorecard.json` `decision_gate_minimums`: phase8_promotion_review=20, anchor_displacement=30, real_money_discussion=100.
- Evidence-debt verdict: the shortest honest path is still paper observation and settlement completeness for the selective rule path; Harville and current odds-only XGBoost do not need more cosmetic reruns until their missing evidence class changes.

## Comparison Table

| Rank | Method | Type | Deployment Posture | Holdout ROI | Holdout Races | Holdout Years+ | Secondary ROI | Secondary Races | Secondary Years+ | Secondary basis | Score | Note |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| 1 | Phase 7 OP/CD rule-component basket | fixed portfolio | PAPER NOW | +38.68% | 175 | 2/2 | +31.34% | 806 | 9/10 | frozen replay on walk-forward test years | 89.7 | Frozen 3-rule baseline. BEL contributes zero 2024-2025 races, so the current holdout is effectively the OP+CD legs. |
| 2 | Phase 8 frozen portfolio | fixed portfolio | SHADOW ONLY | +21.45% | 118 | 2/2 | +55.04% | 625 | 10/10 | frozen replay on walk-forward test years | 87.9 | Frozen 7-rule Phase 8 basket. Useful as the headline multi-track challenger, but still full-history-mined before this replay. |
| 3 | OP refined only | fixed OP rule | WATCH | +51.43% | 49 | 1/2 | +66.10% | 207 | 8/10 | frozen replay on walk-forward test years | 69.9 | Higher-ROI OP variant with a much smaller forward sample. Treat as selective, not as the new default. |
| 4 | OP train-score switch | dynamic OP selector | BENCHMARK ONLY | +51.43% | 49 | 1/2 | +47.46% | 350 | 8/10 | actual train-only walk-forward | 68.4 | Each year, pick the better-qualifying OP rule by train-only selection score. Recent picks: 2022=OP_DURABLE_K7, 2023=OP_DURABLE_K7, 2024=OP_REFINED_K7, 2025=OP_REFINED_K7. |
| 5 | OP durable only | fixed OP rule | ANCHOR | +22.90% | 115 | 1/2 | +40.21% | 416 | 8/10 | frozen replay on walk-forward test years | 67.4 | Largest-sample OP anchor. Lower upside than the refined OP variant, but materially more forward races. |
| 6 | Train-only yearly selector | dynamic selector | BENCHMARK ONLY | +14.36% | 65 | 1/2 | +22.46% | 470 | 8/10 | actual train-only walk-forward | 61.9 | The current honest selector baseline from walk_forward_validation.py. Historical context includes the pre-existing BEL bridge candidate in some earlier folds, but no new aliasing is added here. |

## Fast Takeaways

- Large-sample holdout baseline: **Phase 7 OP/CD rule-component basket** at +38.68% on 175 holdout races.
- Safest current OP anchor: **OP durable only** (ANCHOR) at +22.90% on 115 holdout races.
- Higher-score OP challenger: **OP refined only** at +51.43% on 49 holdout races, but it stays **WATCH** because the forward sample is still smaller and only 1/2 holdout years are positive.
- Honest selector baseline: **Train-only yearly selector** stays useful context at +22.46% across 470 actual train-only walk-forward races, but its 2024-2025 holdout is only +14.36% on 65 races.
- Fixed-method secondary columns are replay context only. They reuse the frozen rules on the walk-forward test years and should not be read as extra train-only validation.
- Current paper-companion read: `OP_DURABLE_K7` remains the safest anchor, `CD_CORE_K8` is the primary OP/CD paper-basket companion, and `OP_REFINED_K7` remains the narrower same-family OP shadow challenger.
- Practical read: use deployment posture for decisions, then use score to compare evidence strength inside that posture instead of auto-promoting smaller-sample challengers. The inherited scorecard contract says: CD_CORE_K8 ranks ahead of OP_REFINED_K7 because PAPER tier outranks WATCH tier even though OP_REFINED_K7 has the higher raw forward_trust score.

## Current Paper-Trade Rule Ladder

This is the quickest selective-family read when Cole wants the paper-basket rule order rather than the broader method-family guardrail.

| Lane | Rule | Posture | 2024 ROI (Races) | 2025 ROI (Races) | WF | Action now | Why this is the current read |
|---|---|---|---:|---:|---:|---|---|
| Anchor now | `OP_DURABLE_K7` | ANCHOR | -47.41% (68) | +124.61% (47) | 7/10 | Keep as safest current anchor | Largest current OP holdout sample plus the strongest walk-forward selection frequency, even though the 2024/2025 path was uneven. |
| Paper-trade companion | `CD_CORE_K8` | PAPER | +45.65% (41) | +78.21% (19) | 1/10 | Keep in the primary paper-basket mix, not as an anchor replacement | Primary OP/CD paper-basket companion: positive in both holdout years, but still a smaller forward sample with low walk-forward selection. |
| Same-family challenger | `OP_REFINED_K7` | WATCH | -25.47% (33) | +210.02% (16) | 2/10 | Shadow/watch only | Hotter aggregate holdout ROI, but on a much smaller forward sample with a losing 2024 and only 2/10 walk-forward selections. |
| Dormant Belmont leg | `BEL_BROAD1_K7` | DORMANT | +0.00% (0) | +0.00% (0) | 3/10 | Wait for Belmont forward races; do not substitute BAQ | Strong historical rule, but it has zero 2024-2025 forward races, so it cannot currently carry current-paper weight. |

- Practical read: on the current forward sample, the primary paper-basket core is effectively `OP_DURABLE_K7` + `CD_CORE_K8`; daily target-card availability still comes from the preflight, `OP_REFINED_K7` stays shadow-only, and `BEL_BROAD1_K7` stays dormant until Belmont produces fresh forward races.
- This is a deployment-order table, not a claim that the anchor has the prettiest ROI line. The whole point is to keep sample size and evidence quality ahead of the hottest small-sample number.

## Phase 8 Shadow-Lane Triage

This keeps the non-primary watch names in comparison view without letting the Phase 8 shadow lane read like a quiet promotion queue.

| Rule | Current role | 2024 ROI (Races) | 2025 ROI (Races) | WF | Why it still stays shadow-only |
|---|---|---:|---:|---:|---|
| `OP_REFINED_K7` | Closest OP challenger | -25.47% (33) | +210.02% (16) | 2/10 | Hotter aggregate holdout ROI, but on a much smaller forward sample with a losing 2024 and only 2/10 walk-forward selections. |
| `DMR_FALL_K7` | One-year pocket only | +103.36% (14) | +0.00% (0) | 0/10 | Only one observed holdout year so far, with no train-only walk-forward support yet. |
| `KEE_K9` | Tiny cross-track watch | +0.28% (14) | +43.76% (6) | 3/10 | Positive in both holdout years, but still only 20 forward races and CI crosses zero. |
| `SA_K9` | Tiny cross-track watch | +29.80% (7) | +55.88% (4) | 0/10 | Positive pocket so far, but only 11 forward races and no train-only walk-forward support yet. |

- Practical read: if Cole wants one shadow name to log most closely, it is still `OP_REFINED_K7` because it stays inside the strongest current family.
- The rest of the Phase 8 watch lane is still observation-only context, not a near-promotion bench. Positive pockets there are still too small or too unsupported to displace the current OP+CD paper basket.

## 2024-2025 Holdout Split

This is the easiest way to see whether an aggregate holdout ROI is broad enough to trust. The stronger current reads are either positive in both years or carry meaningfully larger samples than the prettier small-sample challengers.

| Method | Posture | 2024 ROI (Races) | 2025 ROI (Races) | Read |
|---|---|---:|---:|---|
| Phase 7 OP/CD rule-component basket | PAPER NOW | +0.37% (109) | +105.38% (66) | Nearly flat in 2024, then very strong in 2025, on the largest current portfolio holdout sample. |
| Phase 8 frozen portfolio | SHADOW ONLY | +9.50% (85) | +50.26% (33) | Positive in both years, but still weaker overall than Phase 7 on a smaller current sample. |
| OP refined only | WATCH | -25.47% (33) | +210.02% (16) | Attractive aggregate comes from a smaller sample with a losing 2024 and a very hot 2025. |
| OP train-score switch | BENCHMARK ONLY | -25.47% (33) | +210.02% (16) | Not independent on holdout yet: it picks OP_REFINED_K7 in both 2024 and 2025, so the split is identical. |
| OP durable only | ANCHOR | -47.41% (68) | +124.61% (47) | Ugly 2024, strong 2025 rebound, and still the bigger OP evidence base by far. |
| Train-only yearly selector | BENCHMARK ONLY | -19.95% (45) | +98.37% (20) | Helpful benchmark, but the losing 2024 holdout year keeps it out of deployment posture. |

## Method Notes

- **Phase 7 OP/CD rule-component basket**: Frozen 3-rule baseline. BEL contributes zero 2024-2025 races, so the current holdout is effectively the OP+CD legs.
- **Phase 8 frozen portfolio**: Frozen 7-rule Phase 8 basket. Useful as the headline multi-track challenger, but still full-history-mined before this replay.
- **OP refined only**: Higher-ROI OP variant with a much smaller forward sample. Treat as selective, not as the new default.
- **OP train-score switch**: Each year, pick the better-qualifying OP rule by train-only selection score. Recent picks: 2022=OP_DURABLE_K7, 2023=OP_DURABLE_K7, 2024=OP_REFINED_K7, 2025=OP_REFINED_K7.
- **OP durable only**: Largest-sample OP anchor. Lower upside than the refined OP variant, but materially more forward races.
- **Train-only yearly selector**: The current honest selector baseline from walk_forward_validation.py. Historical context includes the pre-existing BEL bridge candidate in some earlier folds, but no new aliasing is added here.

## Method-Family Guardrail

This table is intentionally not scored against the selective-method rows above. It answers a separate question: should Harville or the current odds-only XGBoost correction path be treated as paper-worthy families at all?
For the selective family, the primary evidence includes the 2024/2025 holdout split because the aggregate number alone is too smooth.

| Method Family | Role | Primary Evidence | Sample | Secondary Evidence | Why It Still Sits Here |
|---|---|---:|---:|---:|---|
| Selective rule path | PAPER NOW | +38.68% (2024-2025 holdout ROI; 2024 +0.37% on 109, 2025 +105.38% on 66) | 175 | +22.46% (train-only selector walk-forward ROI) | Only family here with positive current frozen holdout evidence and a paper-trade observation path. In the current holdout, this is effectively the OP+CD basket, with OP_DURABLE_K7 still the safest anchor, CD_CORE_K8 as the primary OP/CD paper-basket companion, and OP_REFINED_K7 still the smaller same-family shadow challenger, but the recent path was uneven rather than a smooth two-year glide. |
| Harville-ranked probabilities | BENCHMARK ONLY | -24.05% (broad backtest ROI) | 90004 | 41.99% (hit rate) | Large-sample structural benchmark, not a paper candidate. The hit rate is high, but the ROI stays deeply negative, which means ranking order by Harville probability alone does not beat takeout. |
| XGBoost residual correction | RESEARCH ONLY | -24.16% (best ML betting ROI (ML-EV>=1.0_H6_FS5-7)) | 16724 | 4.24% (matched-model payout RMSE reduction vs current baseline) | The model can improve payout prediction a bit without creating a betting edge. In the matched downstream test, payout RMSE was reduced by 4.24% and log-ratio RMSE was reduced by 2.16%, but conservative EV winner pass counts drifted down by 7 (-3.93% relative; -0.0315 percentage points of 22244 test winners), from 178 baseline to 171 enriched. |

- Practical read: the ranking table above compares the best current selective deployment options against each other. This guardrail keeps the project from quietly promoting Harville or the parked odds-only XGBoost path back into the current paper path just because a local model metric improves.
- Selective-family hierarchy read: `OP_DURABLE_K7` stays the safest current paper anchor, `CD_CORE_K8` is the primary OP/CD paper-basket companion, and `OP_REFINED_K7` is still the stronger same-family OP shadow challenger rather than a promoted default.

## Evidence-Class Triage

Use this when the question is whether a prettier modeling or benchmark story should change current paper behavior. The answer still depends on evidence class, not just a better-looking metric.

| Lane | Evidence class | Current decision | What would change it |
|---|---|---|---|
| Selective rule path | Frozen holdout + train-only walk-forward benchmark (+38.68% on 175 holdout races; +22.46% on 470 train-only walk-forward races) | PAPER NOW; keep `OP_DURABLE_K7` as anchor, `CD_CORE_K8` as paper companion, and `OP_REFINED_K7` shadow-only | `OP_REFINED_K7` promotion review needs 20+ future settled shadow ledger observations with complete ROI coverage and cleaner split-aware/walk-forward support; anchor displacement needs 30+ same-candidate ROI-complete observations; real-money confidence still needs 100+ settled paper observations with usable ROI coverage plus concentration checks |
| Harville-ranked probabilities | Broad structural benchmark (-24.05% ROI on 90004 races; 41.99% hit rate) | BENCHMARK ONLY; useful for calibration context, not a paper betting path | Positive frozen holdout / train-only walk-forward betting evidence, not just a high hit rate |
| Current odds-only XGBoost correction path | Research/model-fit lane (-24.16% best ML betting ROI on 16724 races; 4.24% matched payout-RMSE reduction context) | RESEARCH ONLY / parked; the enriched horse-history downstream A/B remains separate research-only context too | Material evidence-class change: richer non-odds features plus downstream betting improvement and then settled paper observations; not another odds-only replay |
| Paper-trade operational surfaces | Daily scan results, open signals, settlement audit, and ledger-quality checks | OPERABILITY / REPAIR ONLY; use them to keep the ledger complete before interpreting ROI | They only change posture after they become settled hit/miss rows with usable return/cost coverage; audit cleanliness alone is not forward-performance evidence |

- This is not new forward evidence. It is a decision-facing guardrail so full-sample benchmarks, model-fit improvements, clean scans, open signals, or ledger audits cannot masquerade as deployment proof.

## Decision-Change Gates

Use this as the compact checklist for what would actually be required before the current comparison answer changes. These are gates for future observation, not new claims from this rerun.

Machine-readable threshold summary (also copied into the JSON sidecar): anchor_displacement=30 ROI-complete same-candidate observations; phase8_promotion_review=20 ROI-complete shadow observations; real_money_discussion=100 total settled observations with usable ROI.
Threshold source: `forward_evidence_scorecard.json` `decision_gate_minimums`; the JSON sidecar records the exact source key for `phase8_promotion_review`, `anchor_displacement`, and `real_money_discussion`.

| Decision pressure | Current answer | Minimum evidence before the answer changes | Evidence scope | Why the gate exists |
|---|---|---|---|---|
| Replace `OP_DURABLE_K7` anchor with `OP_REFINED_K7` | Keep `OP_DURABLE_K7` as anchor; `OP_REFINED_K7` stays shadow-only | 30+ ROI-complete same-candidate settled paper observations plus cleaner split-aware/walk-forward/frozen support that clearly beats the anchor's larger sample; 20+ shadow rows only starts promotion review | Future settled same-candidate paper ledger rows with complete ROI coverage; historical replay or holdout rows do not count as new promotion evidence | The challenger line is hotter but smaller and uneven: 49 holdout races, a losing 2024 / very hot 2025 split, and only 2/10 walk-forward selections |
| Move Harville-ranked probabilities into the current paper path | BENCHMARK ONLY | Positive frozen-holdout or train-only walk-forward betting evidence, not only a high hit rate on a broad benchmark replay | New betting-evidence surface only; calibration or hit-rate summaries without profitable wagering evidence do not change deployment posture | The current broad replay is -24.05% ROI despite a 41.99% hit rate |
| Reopen current odds-only XGBoost as a betting path | RESEARCH ONLY / parked | Richer non-odds features, downstream betting improvement, then settled paper observations; another odds-only replay is not enough | A materially different feature/data class plus downstream betting pass-through; another odds-only rerun is not a new evidence class | Current best ML betting ROI is -24.16%, and the downstream A/B remains model-fit context rather than betting proof |
| Substitute BAQ for dormant BEL | Do not substitute; keep `BEL_BROAD1_K7` dormant | Fresh Belmont qualifying races only; BAQ needs its own independent evidence and must not inherit BEL's rule | Fresh Belmont qualifying races only; BAQ needs independent evidence and cannot inherit BEL history | The BEL->BAQ bridge already failed, and the current scorecard has zero BEL holdout races |
| Move from paper to real money | Paper only | 100+ settled paper observations with hit-rate/ROI inside the expected range plus concentration and payout checks | Settled paper-trade ledger observations with usable ROI coverage, not clean scans, open signals, ledger-quality/settlement-audit passes, or replay backtests | Clean runs and clean audits prove operability; they are not forward-profit proof until outcomes settle |

- Practical read: the next research action is not another odds-only model search. It is disciplined paper observation plus evidence-class changes that would be strong enough to pass these gates; settlement-audit work should repair ledger usability before any ROI interpretation.

## Narrow Follow-Up Reads

Use the smaller guardrail artifacts below when the question is narrower than this full comparison stack:

- `OP_ANCHOR_METHOD_COMPARISON.md`: use when the question is specifically why `OP_DURABLE_K7` still outranks Harville while the current odds-only XGBoost path stays parked unless its evidence class changes materially.
- `AB_DOWNSTREAM_COMPARISON.md`: use when the question is specifically whether the enriched horse-history XGBoost downstream correction is strong enough to change the paper-betting answer. It is not.
- `compare_recommender_scope_paths.md`: use when the question is specifically whether widened `--allow-all-combos` scope should change the current paper default. It should not.
- `out/paper_trade_settlement_audit.md`: use when the question is whether paper-trade ledgers are structurally complete and ROI-covered enough to feed future forward evidence. It is an audit surface, not proof by itself.

## Validation

- Runtime: 0.05 seconds
- Data sources: `phase5_race_cache.pkl`, `phase7_live_rules.json`, `walk_forward_validation_folds.csv`, `walk_forward_validation_rules.csv`, `forward_evidence_scorecard.csv`, `forward_evidence_scorecard.json`, `current_evidence_summary.json`, `cross_family_decision_card.csv`, `backtest_summary.csv`, `ab_downstream_comparison_results.json`; see Source Provenance above for exact input-byte fingerprints
- Wrote: `compare_main_approaches.csv`, `compare_main_approaches.md`, `compare_main_approaches.json`

