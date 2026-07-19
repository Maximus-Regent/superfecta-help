# OP Family Decision Card

This note compares the three realistic OP paths and asks one narrow question:
**does anything clearly beat `OP_DURABLE_K7` strongly enough to replace it as the safest current anchor?**

Short answer: **no**. The challengers show higher ROI, but not enough forward sample or coverage to replace the durable anchor yet.
`valid_evidence_scope=split_aware_op_family_anchor_review_only`
This note is intentionally locked to the frozen 2024-2025 holdout standard for its primary comparison, so a prettier number from some other window does not quietly rewrite the current OP answer.
Fixed OP rows below use frozen replays on the walk-forward test years as secondary context; only the train-only OP switch row uses actual train-only walk-forward evidence.
For the fixed rows, that secondary context is replay context rather than extra train-only validation.
Inherited scorecard ranking contract: rank is tier-first (`True`), Score is secondary within tier (`True`), and raw Score is not an automatic deployment instruction (`True`).
The anchor itself also still needs caution: `OP_DURABLE_K7` remains the safest current default, but its bootstrap 95% CI lower bound is still `-3.40%`.
Scorecard CI-only promotion check: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` says `ci_only_promotion_allowed=false`; OP_REFINED's positive CI lower bound is support context only, not an anchor-replacement trigger.
Inherited operator read gate: `compare_main_approaches.json` `current_operator_boundary.operator_read_gate` says Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. This is routing context only, not no-target, clean-empty, bet-readiness, settled-ROI, OP-anchor proof, promotion, live-profitability, bankroll, or real-money evidence.
Bridge-published current gate progress: `current_evidence_summary.json` `decision_gate_progress` says Gate progress: primary first-read 6/30; OP anchor same-candidate 0/30; Phase 8 weakest shadow 0/20; real-money discussion floor 6/100. All remain uncleared and are routing context only. This is routing context only, not OP-anchor proof or OP-family promotion evidence.
Current bridge rebuild order: `current_evidence_summary.json` `rebuild_validation_contract` routes source-byte changes through python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not OP-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
Scorecard audit route: `current_evidence_summary.json` `scorecard_audit_route` points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py`; this is report-synchronization metadata only, not OP-family evidence, forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

## Comparison Table

This top table is split-aware on purpose: a prettier aggregate OP holdout line should not outrun the year-by-year sample support behind it, and the secondary columns say explicitly whether they are replay context or true train-only walk-forward evidence.

| Method | Type | Holdout ROI | Holdout Races | 2024 ROI / N | 2025 ROI / N | Holdout Years+ | Worst Holdout Year | Secondary ROI | Secondary Races | Secondary Years+ | Secondary Basis | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| OP_DURABLE_K7 | fixed anchor | +22.90% | 115 | -47.41% / 68 | +124.61% / 47 | 1/2 | -47.41% | +40.21% | 416 | 8/10 | frozen replay on walk-forward test years | KEEP AS ANCHOR |
| Train-only OP switch | dynamic challenger | +51.43% | 49 | -25.47% / 33 | +210.02% / 16 | 1/2 | -25.47% | +47.46% | 350 | 8/10 | actual train-only walk-forward | KEEP AS WATCH / RESEARCH |
| OP_REFINED_K7 | fixed challenger | +51.43% | 49 | -25.47% / 33 | +210.02% / 16 | 1/2 | -25.47% | +66.10% | 207 | 8/10 | frozen replay on walk-forward test years | KEEP AS WATCH / RESEARCH |

## 2024-2025 Holdout Split

This is the simplest honest read on why prettier aggregate ROI is not enough to replace the anchor: the two holdout years behave differently, and the challenger samples are much smaller.

| Method | 2024 ROI (Races) | 2025 ROI (Races) | Read |
|---|---:|---:|---|
| OP_DURABLE_K7 | -47.41% (68) | +124.61% (47) | Bigger sample in both years; ugly 2024 but much stronger evidence base overall. |
| Train-only OP switch | -25.47% (33) | +210.02% (16) | Not independent on holdout yet: it picks OP_REFINED_K7 in both 2024 and 2025, so the split is identical. |
| OP_REFINED_K7 | -25.47% (33) | +210.02% (16) | Prettier aggregate comes from a smaller two-year sample and a very hot 2025 rebound after a losing 2024. |

## Conservative Replacement Bar vs. Anchor

A challenger only gets promoted in this note if it clears **all** of these conservative checks:

1. Better holdout ROI than `OP_DURABLE_K7`
2. At least as many 2024-2025 holdout races as `OP_DURABLE_K7`
3. No losing year inside the 2024-2025 holdout window
4. At least as much secondary-context coverage as `OP_DURABLE_K7`
5. At least as many positive secondary-context years as `OP_DURABLE_K7`

For fixed rules here, that secondary context is a frozen replay on the walk-forward test years; for the train-only switch it is actual train-only walk-forward. Treat the fixed-rule secondary columns as replay context rather than extra train-only validation. The bar is therefore conservative, not perfectly apples-to-apples.

That bar is intentionally hard. Replacing the anchor should require clearer evidence than simply posting a prettier ROI on a much smaller sample.
The paper-observation floor for any anchor-displacement discussion is inherited from `forward_evidence_scorecard.json`: 30 ROI-complete settled observations for the same candidate, with cleaner split-aware evidence than `OP_DURABLE_K7`; source `forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations`.
Scorecard rank-contract override: CD_CORE_K8 ranks ahead of OP_REFINED_K7 because PAPER tier outranks WATCH tier even though OP_REFINED_K7 has the higher raw forward_trust score.

| Challenger | Better Holdout ROI? | Match Holdout Sample? | No Losing Holdout Year? | Match WF Coverage? | Match WF Positive Years? | Result |
|---|---|---|---|---|---|---|
| Train-only OP switch | yes | no | no | no | yes | KEEP AS WATCH / RESEARCH |
| OP_REFINED_K7 | yes | no | no | no | yes | KEEP AS WATCH / RESEARCH |

## Scorecard CI-Only Promotion Check

Source: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7`
- Current decision: Keep OP_REFINED_K7 shadow/watch only.
- CI-only promotion allowed: `false`
- Why not: smaller holdout sample than OP_DURABLE_K7, losing 2024 holdout split, lower walk-forward recurrence than OP_DURABLE_K7, uncleared phase8_promotion_review paper-observation gate, uncleared anchor_displacement paper-observation gate.
- Required before review: phase8 promotion review = 20+ ROI-complete candidate shadow observations plus cleaner split-aware/walk-forward support; anchor displacement = 30+ ROI-complete same-candidate paper observations plus a cleaner split-aware forward read and equal-or-better walk-forward support.
- Does not count: positive bootstrap CI lower bound by itself, hotter aggregate small-sample holdout ROI, historical replay rows, clean rebuilds, green validators.

## What This Means

- **Keep `OP_DURABLE_K7` as the current paper anchor.** It has 115 holdout races and 416 secondary-context races (`frozen replay on walk-forward test years`, so replay context rather than extra train-only validation), which is the strongest forward sample inside the OP family, even though that holdout path was uneven (`2024 -47.41% on 68`, `2025 +124.61% on 47`).
- **Anchor caution:** that does not make it a statistically clean slam dunk; the bootstrap 95% CI lower bound for `OP_DURABLE_K7` is still `-3.40%`.
- **Keep `OP_REFINED_K7` as a challenger, not a replacement.** Its ROI is attractive, but its forward sample is much smaller and still includes a losing holdout year.
- **Do not read raw Score as a promotion queue.** CD_CORE_K8 ranks ahead of OP_REFINED_K7 because PAPER tier outranks WATCH tier even though OP_REFINED_K7 has the higher raw forward_trust score.
- **Treat the train-only OP switch as research context.** It is the only row here with true train-only walk-forward secondary evidence, but in the current holdout window it still collapses to the refined rule anyway, so it does not add independent holdout evidence yet.

## Decision-Change Gates

These gates are loaded directly from `forward_evidence_scorecard.json` `decision_gate_minimums`. They are posture-review floors, not proof of profitability.

| Gate | Scorecard-sourced minimum | What it means here | Threshold source |
|---|---:|---|---|
| Anchor displacement | 30 ROI-complete same-candidate observations | Minimum before discussing whether `OP_REFINED_K7` or any OP switch can replace `OP_DURABLE_K7`; still also needs cleaner split-aware and walk-forward/frozen-standard support | `forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations` |
| Phase 8 promotion review | 20 ROI-complete shadow observations | Minimum before reviewing a Phase 8 watch rule for promotion; it does not replace the stricter OP-anchor displacement bar | `forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations` |
| Real-money discussion | 100 total ROI-complete settled paper observations | Minimum before any real-money confidence or bankroll discussion, with concentration/payout sanity checks and no BAQ-as-BEL substitution | `forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi` |

Clean empty scans, open paper signals, historical replay rows, source fingerprints, green validators, or a WATCH label do not satisfy these gates.

## Current OP Paper Snapshot

This context is inherited from `compare_main_approaches.json` / `current_evidence_summary.json` so the OP-family card shows the current paper-workflow boundary without turning it into OP-anchor evidence.

| Field | Current bridge read | Evidence boundary |
|---|---|---|
| Source freshness | `current_run_date`; refresh before right-now use = `False`; bridge reference = `2026-07-17` (`America/New_York`); comparison = `generated_reference_date` / `2026-07-17`; read = Right-now source as-of date 2026-07-17 is not older than bridge reference date 2026-07-17 (America/New_York); still treat the bridge as report/navigation context rather than performance evidence. | Source freshness is operator-readiness metadata, not OP performance proof |
| Refresh action boundary | `./run_daily_portfolio_observation.sh` required before right-now use = `False`; can update surfaces = `True`; settles rows / creates ROI evidence / clean-empty performance = `False` / `False` / `False` | Wrapper refresh is operator routing only; it is not settled ROI, promotion readiness, live profitability, or real-money evidence |
| Operator read gate | `compare_main_approaches.json` `current_operator_boundary.operator_read_gate`: Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. Gate status = `current_operator_routing_context_only`; recommended command = `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` | The saved top card can be read as current operator routing context only; this read gate is not no-target evidence, clean-empty evidence, OP-anchor proof, bet readiness, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Bridge-published gate progress | `current_evidence_summary.json` `decision_gate_progress`: Gate progress: primary first-read 6/30; OP anchor same-candidate 0/30; Phase 8 weakest shadow 0/20; real-money discussion floor 6/100. All remain uncleared and are routing context only. Source: `forward_evidence_scorecard.json` `decision_gate_minimums`; gate status = `all_uncleared` | Current gates are all uncleared routing context only; they do not change the OP-family ordering or create settled ROI, OP-anchor proof, promotion readiness, live-profitability, bankroll, or real-money evidence |
| Current bridge rebuild order | `current_evidence_summary.json` `rebuild_validation_contract`: python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes | Rebuild route only; it is not OP-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Scorecard audit route | `current_evidence_summary.json` `scorecard_audit_route`: Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite drift across report-facing surfaces. Artifacts: `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json`; validator = `python3 validate_scorecard_ranking_contract_audit.py`; gate source = `forward_evidence_scorecard.json:decision_gate_minimums` | Report-synchronization route only; it is not OP-family evidence, forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Current settled rule mix | OP_DURABLE_K7=0; CD_CORE_K8=6; Primary rule mix: OP_DURABLE_K7 has 0 ROI-complete settled row(s); CD_CORE_K8 has 6. Current settled paper context is CD-only, so it should not be counted as OP-anchor forward evidence. | Rule-specific settled rows stay separate; CD-only paper rows are not OP-anchor forward evidence |
| Settlement queue state | `closed`; no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence. | Open rows are settlement workflow only; fill outcomes from actual result/payout evidence before interpreting ROI |
| Recommendation context | Latest run context: the latest live scan completed cleanly and found no qualifying races across 52 card(s) and 446 race(s). Treat this as operator context only; use recommendation and settlement ledgers before interpreting bet readiness or forward performance. | Latest recommendation-state context is operator routing only, not bet readiness or forward-performance evidence |
| Operator route | `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` | Use the route to settle or refresh; do not infer profit, promotion, or real-money readiness from the route itself |

The current operator boundary is routing/provenance context only. It does not change the frozen OP-family ordering above, and it is not settled ROI, OP-anchor proof, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

## Notes

- **OP_DURABLE_K7**: Largest-sample OP path. This is the safest current paper anchor.
- **Train-only OP switch**: Train-only yearly selector across the two OP rules. Holdout choices: 2024=OP_REFINED_K7, 2025=OP_REFINED_K7. Recent WF picks: 2022=OP_DURABLE_K7, 2023=OP_DURABLE_K7, 2024=OP_REFINED_K7, 2025=OP_REFINED_K7.
- **OP_REFINED_K7**: Higher ROI, but on much smaller forward samples and with mixed 2024/2025 behavior.

## Validation

- Source logic reused from `compare_main_approaches.py`
- Source files: `phase5_race_cache.pkl`, `phase7_live_rules.json`, `walk_forward_validation_rules.csv`, `forward_evidence_scorecard.csv`, `forward_evidence_scorecard.json`, `compare_main_approaches.json`, `current_evidence_summary.json`
- Wrote: `op_family_decision.csv`, `OP_FAMILY_DECISION.md`

## Source Provenance

Exact input-byte fingerprints for this OP-family card. Use them as reproducibility metadata only; they do not prove settled paper ROI, promotion readiness, live profitability, or real-money performance.

| Source | Path | Bytes | SHA-256 |
|---|---|---:|---|
| `compare_main_approaches` | `compare_main_approaches.py` | 127645 | `8cad3fdd48178130ebeb2dc5505e800dd02177655977fec7776bc198448efc12` |
| `compare_main_approaches_json` | `compare_main_approaches.json` | 35843 | `fa683c296bf127845610a4c06a57e1da6adf9fa821486e6f728c8feba2ac667f` |
| `current_evidence_summary` | `current_evidence_summary.json` | 50352 | `f86cdd072e9b5073c59c502811c712f21d08effa75e334904c49573f86ba30b9` |
| `phase5_race_cache` | `phase5_race_cache.pkl` | 6876552 | `9f38ab5d34cac72175c7ae2126a33bd798a683fdf15f862afffc17632a6084e6` |
| `phase7_rules` | `phase7_live_rules.json` | 1470 | `24f9f071ba7d47937f9b71e9b735cf7cf330ff3debb3d350459310316d9c1b7d` |
| `walk_forward_rules` | `walk_forward_validation_rules.csv` | 21202 | `5a1d4edaa27b106b81cd0b355e495c6ff89bf5c2f8891363435eac15e121753e` |
| `forward_evidence_scorecard_csv` | `forward_evidence_scorecard.csv` | 6955 | `39d2dc6fd0f929060ce6678d58f409c5bdd090563cbc6af41941674159811174` |
| `forward_evidence_scorecard_json` | `forward_evidence_scorecard.json` | 25686 | `f9862ab5df38e02b45dc508ddffad6735bd388be5c088f1ebde3cc7dc5e08c49` |
