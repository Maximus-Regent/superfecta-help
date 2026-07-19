# Cross-Family Decision Card

This note compares the three most relevant rules for the current paper-decision hierarchy:
`OP_DURABLE_K7`, `CD_CORE_K8`, and `OP_REFINED_K7`.

Short answer:
- **Keep `OP_DURABLE_K7` as the anchor**
- **Paper trade `CD_CORE_K8`, but do not let it replace the anchor yet**
- **Keep `OP_REFINED_K7` on watch, not as a promoted paper default**
`valid_evidence_scope=split_aware_cross_family_paper_hierarchy_only`
- Treat those roles as evidence-ranked, not statistically clean slam dunks: `OP_DURABLE_K7` still has CI low `-3.40%`, `CD_CORE_K8` still has CI low `-15.00%`, and `OP_REFINED_K7` only gets a positive CI low `+11.20%` on a much smaller holdout sample.
- Scorecard CI-only promotion check: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` says `ci_only_promotion_allowed=false`; the positive OP_REFINED CI lower bound is support context only, not a promotion trigger.
- Inherited scorecard ranking contract: rank is tier-first (`True`), Score is secondary within tier (`True`), and raw Score is not an automatic deployment instruction (`True`).
- Inherited operator read gate: `compare_main_approaches.json` `current_operator_boundary.operator_read_gate` says Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. This is routing context only, not no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money evidence.
- Bridge-published current gate progress: `current_evidence_summary.json` `decision_gate_progress` says Gate progress: primary first-read 6/30; OP anchor same-candidate 0/30; Phase 8 weakest shadow 0/20; real-money discussion floor 6/100. All remain uncleared and are routing context only. This is routing context only, not anchor proof or cross-family promotion evidence.
- Scorecard audit route: `current_evidence_summary.json` `scorecard_audit_route` says Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite drift across report-facing surfaces. This is report-synchronization metadata only, not cross-family evidence, forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- Current bridge rebuild order: `current_evidence_summary.json` `rebuild_validation_contract` routes source-byte changes through `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not cross-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
This note is intentionally pinned to the frozen 2024-2025 holdout standard carried by the scorecard and frozen-evaluation artifacts, so a prettier line from some other window does not quietly rewrite the paper-decision shortlist.

## Comparison Table

This table keeps the shortlist split-aware on purpose: year-specific race counts matter, because a prettier annual ROI line means less when it comes from a much smaller slice.
Here, `WF Selected` is train-only selection recurrence context, not a second profit line or extra train-only validation layer.

| Rule | Family | Role | Holdout ROI | Holdout Races | 2024 ROI / N | 2025 ROI / N | Holdout Years+ | WF Selected | CI Lower | Why It Sits Here |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OP_DURABLE_K7 | OP | ANCHOR | +22.90% | 115 | -47.41% / 68 | +124.61% / 47 | 1/2 | 7/10 | -3.40% | Safest anchor because it has the largest OP holdout sample (115) and the strongest walk-forward selection frequency (7/10), even though the bootstrap CI lower bound still crosses zero at -3.40%. |
| CD_CORE_K8 | CD | PAPER | +55.96% | 60 | +45.65% / 41 | +78.21% / 19 | 2/2 | 1/10 | -15.00% | Paper now because holdout is positive in both years (+45.65%, +78.21%), but the forward sample is still smaller than the OP anchor, walk-forward selection is only 1/10, and the bootstrap CI lower bound still crosses zero at -15.00%. |
| OP_REFINED_K7 | OP | WATCH | +51.43% | 49 | -25.47% / 33 | +210.02% / 16 | 1/2 | 2/10 | +11.20% | Watch only because the ROI is attractive, but the holdout sample is only 49 races and 2024 was a losing year (-25.47%), even though the bootstrap CI lower bound is positive at +11.20%. |

## Why the Current Roles Make Sense

- **OP_DURABLE_K7 (ANCHOR)**: Safest anchor because it has the largest OP holdout sample (115) and the strongest walk-forward selection frequency (7/10), even though the bootstrap CI lower bound still crosses zero at -3.40%.
  - Family caution: OP is the strongest current family, but the refined OP variant still lacks enough forward sample to replace this anchor.
- **CD_CORE_K8 (PAPER)**: Paper now because holdout is positive in both years (+45.65%, +78.21%), but the forward sample is still smaller than the OP anchor, walk-forward selection is only 1/10, and the bootstrap CI lower bound still crosses zero at -15.00%.
  - Family caution: CD family caution: the more selective CD_REFINED_K9 looked better in-sample but lost on 2024-2025 holdout, so keep the simpler CD rule on paper only.
- **OP_REFINED_K7 (WATCH)**: Watch only because the ROI is attractive, but the holdout sample is only 49 races and 2024 was a losing year (-25.47%), even though the bootstrap CI lower bound is positive at +11.20%.
  - Family caution: Interesting OP challenger, but still not strong enough to displace the durable OP rule.

## Paper Companion and Shadow Read

If Cole asks how the non-anchor paper roles split in the current hierarchy:
- **Primary paper companion: `CD_CORE_K8`**. It is the cleanest non-anchor paper companion because both holdout years are positive (`2024 +45.65% on 41`, `2025 +78.21% on 19`), but it still trails the anchor badly on sample depth (`60` vs `115`), walk-forward selection (`1/10` vs `7/10`), and CI strength (still `-15.00%` at the lower bound).
- **Same-family OP shadow challenger: `OP_REFINED_K7`**. It is the more explosive OP upside path, and its CI lower bound is positive at `+11.20%`, but it still needs more forward races than `49` and a non-losing second holdout year before it can seriously challenge the anchor (`2024 -25.47%`, `2025 +210.02%`).

### Scorecard CI-Only Promotion Check

Source: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7`
- Current decision: Keep OP_REFINED_K7 shadow/watch only.
- CI-only promotion allowed: `false`
- Why not: smaller holdout sample than OP_DURABLE_K7, losing 2024 holdout split, lower walk-forward recurrence than OP_DURABLE_K7, uncleared phase8_promotion_review paper-observation gate, uncleared anchor_displacement paper-observation gate.
- Required before review: phase8 promotion review = 20+ ROI-complete candidate shadow observations plus cleaner split-aware/walk-forward support; anchor displacement = 30+ ROI-complete same-candidate paper observations plus a cleaner split-aware forward read and equal-or-better walk-forward support.
- Does not count: positive bootstrap CI lower bound by itself, hotter aggregate small-sample holdout ROI, historical replay rows, clean rebuilds, green validators.

## Not in the near-promotion shortlist

The rest of the current Phase 8 watch list is still observation-only, not part of the near-term cross-family promotion queue:
- `KEE_K9`: keep logging it, but it still has only 20 holdout races, CI low -3.00%, and only 3/10 walk-forward support.
- `SA_K9`: still only 11 holdout races and 0/10 walk-forward support, even though both observed holdout years are positive.
- `DMR_FALL_K7`: still only 14 holdout races, just one observed holdout year, and 0/10 walk-forward support.
Those pockets are worth observing, but they are not peers of `CD_CORE_K8` or `OP_REFINED_K7` for current paper-hierarchy promotion decisions.

## Decision-Change Gates

These gates are loaded directly from `forward_evidence_scorecard.json` `decision_gate_minimums`. They are posture-review floors, not proof of profitability.

| Gate | Scorecard-sourced minimum | What it means here | Threshold source |
|---|---:|---|---|
| Anchor displacement | 30 ROI-complete same-candidate observations | Minimum before any non-anchor rule can challenge `OP_DURABLE_K7`; `CD_CORE_K8` can remain the paper companion, but it does not become the anchor from holdout ROI alone | `forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations` |
| Phase 8 promotion review | 20 ROI-complete shadow observations | Minimum before reviewing `OP_REFINED_K7` or another Phase 8 watch rule for promotion; this does not override the stricter anchor-displacement bar | `forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations` |
| Real-money discussion | 100 total ROI-complete settled paper observations | Minimum before any real-money confidence or bankroll discussion, with concentration/payout sanity checks and no BAQ-as-BEL substitution | `forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi` |

Clean empty scans, open paper signals, historical replay rows, source fingerprints, green validators, compatibility labels, or a WATCH label do not satisfy these gates.

## Current Paper Snapshot

This context is inherited from `compare_main_approaches.json` / `current_evidence_summary.json` so the cross-family card shows the current paper-workflow boundary without turning it into cross-family promotion evidence.

| Field | Current bridge read | Evidence boundary |
|---|---|---|
| Source freshness | `current_run_date`; refresh before right-now use = `False`; bridge reference = `2026-07-17` (`America/New_York`); comparison = `generated_reference_date` / `2026-07-17`; read = Right-now source as-of date 2026-07-17 is not older than bridge reference date 2026-07-17 (America/New_York); still treat the bridge as report/navigation context rather than performance evidence. | Source freshness is operator-readiness metadata, not performance proof |
| Refresh action boundary | `./run_daily_portfolio_observation.sh` required before right-now use = `False`; can update surfaces = `True`; settles rows / creates ROI evidence / clean-empty performance = `False` / `False` / `False` | Wrapper refresh is operator routing only; it is not settled ROI, promotion readiness, live profitability, or real-money evidence |
| Operator read gate | `compare_main_approaches.json` `current_operator_boundary.operator_read_gate`: Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. Gate status = `current_operator_routing_context_only`; recommended command = `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` | The saved top card can be read as current operator routing context only; this read gate is not no-target evidence, clean-empty evidence, bet readiness, settled ROI, cross-family promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Bridge-published gate progress | `current_evidence_summary.json` `decision_gate_progress`: Gate progress: primary first-read 6/30; OP anchor same-candidate 0/30; Phase 8 weakest shadow 0/20; real-money discussion floor 6/100. All remain uncleared and are routing context only. Source: `forward_evidence_scorecard.json` `decision_gate_minimums`; gate status = `all_uncleared` | Current gates are all uncleared routing context only; they do not change the frozen ANCHOR / PAPER / WATCH ordering or create settled ROI, OP-anchor proof, cross-family promotion readiness, live-profitability, bankroll, or real-money evidence |
| Scorecard audit route | `current_evidence_summary.json` `scorecard_audit_route`: Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite drift across report-facing surfaces. Validator: `python3 validate_scorecard_ranking_contract_audit.py`; artifacts: `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json`; gate snapshot = 30/20/100 with no-BAQ-as-BEL required `True` | Report-synchronization route only; it is not cross-family evidence, forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Current bridge rebuild order | `current_evidence_summary.json` `rebuild_validation_contract`: `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes | Provenance/rebuild route only; green checks and rebuild order are not cross-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |
| Current settled rule mix | OP_DURABLE_K7=0; CD_CORE_K8=6; Primary rule mix: OP_DURABLE_K7 has 0 ROI-complete settled row(s); CD_CORE_K8 has 6. Current settled paper context is CD-only, so it should not be counted as OP-anchor forward evidence. | Rule-specific settled rows stay separate; CD-only paper rows are not OP-anchor or cross-family promotion evidence |
| Settlement queue state | `closed`; no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence. | Open rows are settlement workflow only; fill outcomes from actual result/payout evidence before interpreting ROI |
| Recommendation context | Latest run context: the latest live scan completed cleanly and found no qualifying races across 52 card(s) and 446 race(s). Treat this as operator context only; use recommendation and settlement ledgers before interpreting bet readiness or forward performance. | Latest recommendation-state context is operator routing only, not bet readiness or forward-performance evidence |
| Operator route | `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json` | Use the route to settle or refresh; do not infer profit, promotion, or real-money readiness from the route itself |

The current operator boundary is routing/provenance context only. It does not change the frozen ANCHOR / PAPER / WATCH ordering above, and it is not settled ROI, OP-anchor proof, cross-family promotion readiness, live profitability, bankroll guidance, or real-money evidence.

## Head-to-Head vs. the Anchor

| Rule | Holdout ROI vs Anchor | Holdout Races vs Anchor | WF Selected vs Anchor | Promotion Blocker | Practical Read |
|---|---:|---:|---:|---|---|
| CD_CORE_K8 | +33.06% | -55 | -6 | Needs materially more forward sample than 60 holdout races and much better walk-forward recurrence than 1/10. | Better holdout ROI than the anchor, but on only 60 races and with much weaker walk-forward selection. |
| OP_REFINED_K7 | +28.53% | -66 | -5 | Needs more forward races than 49 plus a non-losing second holdout year; 2024 is still -25.47%. | Higher ROI than the anchor, but smaller sample and still includes a losing holdout year. |

## Bottom Line

If Cole wants one clean current paper hierarchy:
- read the shortlist with the split counts attached, not just the aggregate ROI columns; `OP_DURABLE_K7` still leads, but its own holdout path was uneven (`2024 -47.41% on 68`, `2025 +124.61% on 47`).

1. **Anchor:** `OP_DURABLE_K7`
2. **Paper companion alongside it:** `CD_CORE_K8`
3. **Watch / same-family shadow challenger:** `OP_REFINED_K7`

That ordering is intentionally conservative. It protects against promoting the prettiest small-sample ROI line over the strongest forward-evidence anchor.
Scorecard rank-contract override: CD_CORE_K8 ranks ahead of OP_REFINED_K7 because PAPER tier outranks WATCH tier even though OP_REFINED_K7 has the higher raw forward_trust score.
Treat the walk-forward-selected counts as recurrence context for how often each rule survives train-only yearly selection, not as fresh standalone profit proof.

## Validation

- Sources: `forward_evidence_scorecard.csv`, `forward_evidence_scorecard.json`, `frozen_portfolio_eval_summary.csv`, `compare_main_approaches.json`, `current_evidence_summary.json`
- Wrote: `cross_family_decision_card.csv`, `CROSS_FAMILY_DECISION.md`
- This card is a read-only synthesis of existing frozen evaluation artifacts

## Source Provenance

Exact input-byte fingerprints for this cross-family card. Use them as reproducibility metadata only; they do not prove settled paper ROI, promotion readiness, live profitability, or real-money performance.

| Source | Path | Bytes | SHA-256 |
|---|---|---:|---|
| `forward_evidence_scorecard_csv` | `forward_evidence_scorecard.csv` | 6955 | `39d2dc6fd0f929060ce6678d58f409c5bdd090563cbc6af41941674159811174` |
| `forward_evidence_scorecard_json` | `forward_evidence_scorecard.json` | 25686 | `f9862ab5df38e02b45dc508ddffad6735bd388be5c088f1ebde3cc7dc5e08c49` |
| `frozen_portfolio_eval` | `frozen_portfolio_eval_summary.csv` | 5184 | `98ac5d1cd74861c080e4fc096fe4f3a5bc4102100a950a8186cc9f9c0af9f18d` |
| `compare_main_approaches_json` | `compare_main_approaches.json` | 35843 | `fa683c296bf127845610a4c06a57e1da6adf9fa821486e6f728c8feba2ac667f` |
| `current_evidence_summary` | `current_evidence_summary.json` | 50352 | `f86cdd072e9b5073c59c502811c712f21d08effa75e334904c49573f86ba30b9` |
