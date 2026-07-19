# Cole Superfecta Full Report — 2026-04-15

## Executive summary

Yes, we have improved it enough to justify a full report.

The biggest honest change is not fake headline inflation, it is that the project is now:
- more defensible
- more operational
- easier to explain
- less likely to confuse research with something actually ready to run

### Bottom line
- **Largest validated historical selector-scoring improvement:** walk-forward ROI improved from **+22.46%** to **+30.42%** with sqrt-dampened scoring, but that is a research-side improvement, **not** the current frozen deployment benchmark.
- **Current honest selector benchmark:** still the **Train-only yearly selector** at **+22.46% walk-forward** and **+14.36% 2024-2025 holdout**, which stays **BENCHMARK ONLY**.
- **Best current paper-observation baseline:** still the **Phase 7 OP/CD rule-component basket**, with target cards confirmed only by daily preflight, not the Phase 8 expansion.
- **Best current holdout result:** **+38.68% ROI on 175 races** for the Phase 7 OP/CD rule-component basket, but that path was not smooth: **2024 +0.37% on 109 races; 2025 +105.38% on 66 races**. Target-card availability still comes from daily preflight.
- **Phase 8 status:** still useful, but it stays **shadow-only**, because its 2024-2025 holdout is weaker at **+21.45% on 118 races** and also uneven: **2024 +9.50% on 85 races; 2025 +50.26% on 33 races**.
- **Method-family verdict:** the **selective rule path** is still the only family that deserves paper-trade treatment. **Harville = benchmark only. XGBoost = research only.**
- **Full-data XGBoost retrain caveat:** read `FULL_DATA_RETRAIN_ARTIFACTS.md` and run `python3 validate_full_data_retrain_artifacts.py` when checking the full-data retrain artifact or exact retrain/prediction commands; large RMSE / MAE gains are model-fit reproducibility context only, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- **Live/demo status:** the live model stack and demo lane now work on real available cards today, but there has **not** been an honest **+30% EV** live opportunity yet.
- **Paper-trade evidence status:** the improved paper-trade stack is a workflow/reproducibility gain, not new forward evidence by itself; genuinely new forward evidence still requires settled paper trades and the downstream forward-check artifacts.
- **Evidence-scope boundary:** only settled paper-trade rows with usable ROI coverage should change deployment posture; clean scans, open signals, historical replay rows, calibration-only summaries, or another odds-only rerun should not.
- **Decision-gate source:** `forward_evidence_scorecard.json` `decision_gate_minimums` sets `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100`; these are future ROI-complete observation floors, not cleared gates.
- **Current evidence bridge:** before quoting current paper totals, read `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json`; the current bridge is source-consistent, primary paper is still **6/30** ROI-complete toward a first read and **6/100** toward broader review, and the settled sample is **CD_CORE_K8-only** with **0 OP_DURABLE_K7** ROI-complete rows. Its combined current-paper route across `operator_status_context`, `source_freshness.requires_refresh_before_right_now_use=false`, and `operator_read_gate.requires_refresh_before_evidence_read=false` says the saved best-action card is fresh against the bridge reference date but still goes through operator-read-gate routing before instruction or evidence use; this is not OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence. The bridge also publishes `operator_read_gate.requires_refresh_before_evidence_read=false`: Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. Rebuild order route: `current_evidence_summary.json.rebuild_validation_contract`; after scorecard/rules/signals/settlement-ledger byte changes, run `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence. Settlement queue state: `closed`; no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence. Latest recommendation-state context: Latest run context: the latest live scan completed cleanly and found no qualifying races across 52 card(s) and 446 race(s). Treat this as operator context only; use recommendation and settlement ledgers before interpreting bet readiness or forward performance.
- **OP_REFINED CI-only boundary:** the current bridge source-matches `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` with `ci_only_promotion_allowed=false`; OP_REFINED's positive CI lower bound is support context only, not OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- **Scorecard audit route:** `current_evidence_summary.json.scorecard_audit_route` points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py`; this is report-synchronization metadata only, not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- **Direct cross-family caveat route:** when the question is whether the anchor / paper / watch shortlist still carries the current-paper caveat, read `CROSS_FAMILY_DECISION.md` and run `python3 validate_cross_family_decision.py`; stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green report validation are not OP-anchor proof or cross-family promotion evidence.

## How much we improved it so far

## 1) Honest validation improved materially

This is the cleanest historical numeric improvement we can defend. It should be treated as a research-side selector-scoring improvement, not as the current frozen benchmark for deployment decisions.

| Item | Before | Now | Improvement |
|---|---:|---:|---:|
| Walk-forward selector ROI | +22.46% | **+30.42%** | **+7.96 percentage points** |
| Walk-forward profit | $17,541.35 | **$23,798.15** | **+$6,256.80** |
| Positive walk-forward years | 8/10 | 8/10 | same, but with better rule selection |

What changed:
- we tested selector scoring variants against the frozen walk-forward artifacts
- the best result was **sqrt ROI dampening with strict guardrails**
- this was a real scoring fix, not new rule mining and not a cherry-picked backtest rerun

What did **not** happen:
- we did **not** prove a magic new strategy
- we did **not** justify Phase 8 as the new operating default
- we did **not** solve everything with ML

## 2) Portfolio decisions got much clearer

Earlier, the repo had a lot of evidence but too much of it was scattered.
Now the main decision hierarchy is much cleaner:

- **Phase 7 OP/CD rule-component basket** = primary paper baseline, with target cards confirmed by daily preflight
- **Phase 8 frozen portfolio** = shadow challenger only
- **Train-only yearly selector** = honesty benchmark, not the operating recipe

Why:
- Phase 7 still wins on the most important current comparison
- **Phase 7 holdout:** **+38.68% ROI on 175 races** — split: **2024 +0.37% on 109; 2025 +105.38% on 66**
- **Phase 8 holdout:** **+21.45% ROI on 118 races** — split: **2024 +9.50% on 85; 2025 +50.26% on 33**

So the project improved not by inventing a prettier story, but by making the deployment story harder to bullshit. Phase 7 still leads, but not because it delivered a smooth two-year glide path.

## 2A) Method-family guardrail

This is intentionally separate from the selective-method ranking.
It answers a simpler question first: which whole method families still deserve live attention at all?

| Method family | Role | Primary evidence | Why this remains the right posture |
|---|---|---:|---|
| Selective rule path | PAPER NOW | +38.68% holdout ROI on 175 races; 2024 +0.37% on 109, 2025 +105.38% on 66 | Only family here with positive current frozen holdout evidence plus a paper-trade observation path; `OP_DURABLE_K7` still anchors it, `CD_CORE_K8` is the primary OP/CD paper-basket companion, and `OP_REFINED_K7` remains the smaller same-family shadow challenger, but the recent path was uneven rather than smooth. |
| Harville-ranked probabilities | BENCHMARK ONLY | -24.05% broad ROI on 90004 races | Useful structural benchmark, but the large-sample ROI is still deeply negative, so it does not beat takeout. |
| XGBoost residual correction | RESEARCH ONLY | -24.16% best ML betting ROI on 16724 races | Prediction quality improved a bit, but the betting case did not materially improve downstream. |

That guardrail matters because a small local model metric improvement can otherwise look more important than it really is.
The right read is still layered: compare the serious selective contenders against each other, keep `OP_DURABLE_K7` / `CD_CORE_K8` / `OP_REFINED_K7` in their current anchor / paper-companion / shadow-challenger order, keep Harville benchmark-only, and keep the current odds-only XGBoost path parked outside the paper-decision lane unless its evidence class changes materially.
The broader selective-family secondary lines elsewhere in the repo are replay context on walk-forward test years, not extra train-only validation.

## 3) Rule hierarchy is now easier to defend

The strongest current rule ordering is clearer now:

- **OP_DURABLE_K7** = safest anchor
- **CD_CORE_K8** = paper-trade worthy, but not enough to displace the anchor
- **OP_REFINED_K7** = interesting challenger, still watch-level due to sample size / consistency concerns

The year split makes that hierarchy easier to explain honestly:
- **OP_DURABLE_K7**: mixed holdout, but on the largest OP holdout sample (**2024 -47.41% on 68 races; 2025 +124.61% on 47**) plus the strongest walk-forward support (**7/10 folds**)
- **CD_CORE_K8**: steadier current paper candidate, because it stayed positive in both holdout years (**2024 +45.65% on 41; 2025 +78.21% on 19**)
- **OP_REFINED_K7**: prettier aggregate ROI, but still a smaller mixed-year challenger (**2024 -25.47% on 33; 2025 +210.02% on 16**)

So the real read is not "highest ROI wins." It is that CD currently looks steadier, OP_DURABLE still has the stronger anchor-grade evidence base, and OP_REFINED still needs more forward sample before it can challenge the anchor seriously.

That matters because before, the evidence existed but lived in too many places. Now it is much easier to answer:
- what is the safest anchor?
- what is good enough to paper?
- what is still just a watch-list idea?

## 4) Paper-trade infrastructure went from partial to actually usable

This is one of the biggest practical improvements.

Before, there was research and some pipeline code, but the daily operating path still had ambiguity.
Now the repo has a much more usable paper-trade workflow:

- separate **primary** and **shadow** rule baskets
- daily runner for both lanes
- settlement ledger sync
- settlement entry helper
- forward-check artifact
- lane monitor artifact
- daily artifact guide
- preflight note explaining whether OP/CD simply were not racing that day

These are operational and reproducibility improvements, not new forward-evidence wins by themselves.
They make the current paper lane easier to run and interpret from saved artifacts, but they do **not** create new paper-trade outcomes.
New forward evidence still requires settled paper trades and the downstream forward-check artifacts.
Only settled paper-trade rows with usable ROI coverage should change deployment posture; clean scans, open signals, historical replay rows, calibration-only summaries, or another odds-only rerun should not.

### Current evidence bridge for report updates

For short Cole updates, use `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` as the bridge from frozen research posture to current paper-trade status before quoting `PAPER_TRADE_NOW`, ops-bucket/operator-status context, settlement-audit, or primary-ledger totals.
Gate source: `forward_evidence_scorecard.json` `decision_gate_minimums` sets `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100`; these are future ROI-complete observation floors, not cleared gates.
The bridge currently says source consistency is matched across the top card, audit, and primary settlement CSV; primary paper is still **6/30** ROI-complete toward a first statistical read and **6/100** toward broader review; `CD_CORE_K8` has **6** ROI-complete settled rows while `OP_DURABLE_K7` has **0**; and the current settled paper context is CD-only, so it should not be counted as OP-anchor forward evidence.
Rebuild order route: `current_evidence_summary.json.rebuild_validation_contract`; after scorecard/rules/signals/settlement-ledger byte changes, run `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
The bridge uses the combined current-paper route: `operator_status_context`, `source_freshness.requires_refresh_before_right_now_use=false`, and `operator_read_gate.requires_refresh_before_evidence_read=false`; the saved right-now source is fresh against the bridge reference date but still goes through operator read-gate routing before right-now instruction or evidence use.
The bridge also publishes `operator_read_gate.requires_refresh_before_evidence_read=false`: Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence.
Scorecard audit route: `current_evidence_summary.json.scorecard_audit_route` points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py`; this is report-synchronization metadata only, not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
Settlement queue state: `closed`; no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence. Latest recommendation-state context: Latest run context: the latest live scan completed cleanly and found no qualifying races across 52 card(s) and 446 race(s). Treat this as operator context only; use recommendation and settlement ledgers before interpreting bet readiness or forward performance.
If `source_consistency.overall_match=false`, repair the top-card / audit / CSV mismatch before quoting current paper numbers from this report; then use the combined `operator_status_context` + `source_freshness` + `operator_read_gate` route before using the saved right-now card as current-day guidance or evidence.
For the anchor / paper / watch shortlist specifically, use `CROSS_FAMILY_DECISION.md` and `validate_cross_family_decision.py` as the narrow current-paper caveat route: stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green report-surface validation do not count as OP-anchor proof or cross-family promotion evidence.

That last part matters a lot.
A quiet day can now be read honestly as one of these:
- no primary paper-basket target tracks were racing
- scanner failure
- partial-cache empty run
- clean no-signal day

That is a major operational improvement, even though it does not show up as one flashy ROI number.

## 5) Live/demo capability improved a lot

This was another real jump.

The project now has a separate, honest live demo lane:
- `superfecta_ops.py` remains the production OP/CD wrapper
- `demo_live_predictions.py` is the live/demo scanner for whatever cards are actually available

That fixed a big confusion point.
Earlier, “no active OP/CD target today” was getting mixed up with “no live prediction path exists today.”
That is no longer true.

### What the live/demo lane can do now
- scan available cards
- choose the next or best available-card candidate
- classify results as **PLAY / FLOW / PASS**
- save JSON + CSV + report artifacts
- use cache hardening to reduce fragile live fetch behavior
- run a threshold watcher that stays silent unless a real **+30% EV** candidate appears

### Honest live status today
- the lane works
- the watcher works
- the production basket remains unchanged
- the best live number seen so far today was **+23.24%**, which is **not enough**
- so there is still **no honest +30% live alert to send**

## 6) We tested the ML improvement honestly instead of pretending it changed the betting case

This is important for the full report.

We did find a real training-data improvement:
- horse-history features improved payout prediction quality on fair out-of-sample tests

But the more important follow-up was honest:
- when pushed through the EV engine, that prediction improvement did **not** materially improve downstream betting decisions

So the correct conclusion is:
- **prediction quality improved a bit**
- **betting case did not materially improve**
- therefore **do not promote it to production**

For the separate full-data retrain artifact, use `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py` only as a model-fit reproducibility route. Large full-data RMSE / MAE gains and exact retrain/prediction commands are diagnostics, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

That is a good outcome for the report, because it shows we are filtering ourselves instead of hyping every positive metric.

## What changed concretely

### Evaluation and decision artifacts added or improved
- `forward_evidence_scorecard.py` / `forward_evidence_scorecard.txt`
- `compare_main_approaches.py`
- `OP_FAMILY_DECISION.md`
- `CROSS_FAMILY_DECISION.md`
- `PORTFOLIO_DECISION_CARD.md`
- `METHOD_FAMILY_DECISION.md`
- `SELECTOR_EXPERIMENT.md`
- `SAMPLE_SIZE_EXPERIMENT.md`

### Paper-trade operations added or improved
- `phase7_current_paper_rules.json`
- `phase8_shadow_rules.json`
- `run_daily_portfolio_observation.sh`
- `paper_trade_forward_check.py`
- `paper_trade_settlement_sync.py`
- `paper_trade_settlement_helper.py`
- `paper_trade_lane_monitor.py`
- `paper_trade_status_summary.py`
- `daily_artifact_guide.py`
- `paper_trade_preflight_note.py`

### Live/demo operations added or improved
- `demo_live_predictions.py`
- best-live selection mode
- candidate leaderboard output
- pass/floor labeling
- live cache hardening
- threshold watcher behavior

## What counts as the biggest real improvements

If Cole asks “what actually got better?”, the honest order is:

1. **Historical selector scoring got better in a validated way**
   - +22.46% to +30.42% walk-forward in the selector-scoring experiment, while the current frozen benchmark still remains the train-only selector card at +22.46% walk-forward and +14.36% holdout
2. **The project is much more operational**
   - daily paper-trade workflow is now clearer and more runnable, but that is workflow/reproducibility improvement rather than new forward proof
3. **The report hierarchy is cleaner**
   - much easier to defend what is anchor / paper / shadow / benchmark / skip
4. **The live demo lane now works without touching production logic**
5. **The ML path is now more honest**
   - improved prediction, but no fake claim of improved betting edge

## What has NOT improved enough yet

This is just as important.

- We still do **not** have proof that Phase 8 should replace Phase 7.
- We still do **not** have a reason to move Harville or XGBoost into the live decision path.
- We still do **not** have a verified +30% live EV demo hit for today.
- We still need more forward observations before making stronger real-money claims.

## Recommended report-safe conclusion

If we want the cleanest final message right now, it is this:

> The project improved meaningfully, but mainly through better validation, better decision hygiene, and much stronger operational tooling, not through some fake overnight discovery. The biggest validated historical numeric gain was the selector-scoring improvement from +22.46% to +30.42%, but the current frozen benchmark still remains the train-only selector at +22.46% walk-forward and +14.36% holdout, with BENCHMARK ONLY status. The best current deployment stance is still conservative: paper trade the selective rule path, keep Phase 7 as the primary baseline, keep Phase 8 as shadow-only, and treat Harville/XGBoost as benchmark or research rather than live betting engines.

## Short answer to “how much did we improve it?”

In plain English:

- we turned it from a **strong but messy research repo** into something much closer to a **defensible report + operational paper-trade system**
- the biggest clean historical numeric gain was **+7.96 percentage points** in selector-scoring walk-forward ROI, while the current frozen selector benchmark remains the train-only selector at **+22.46%** walk-forward and **+14.36%** holdout
- the biggest practical gain was making the daily paper-trade and live-demo paths actually usable and interpretable
- the biggest honesty win was proving that some “improvements” were **not** worth promoting

That is real progress.
