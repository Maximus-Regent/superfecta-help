# Cole — Superfecta Project Status & Plan

**Date:** 2026-04-14
**Author:** Max (via Claude audit)
**Purpose:** Honest assessment for tonight's work session. No hype.

---

## TL;DR

The project has strong structural research (8 phases, 90K races, 75+ strategies tested).
The **Phase 7 three-track portfolio (BEL + OP + CD)** is the most trustworthy result.
Phase 8's seven-track expansion looks better on paper but **underperforms Phase 7 on
the actual holdout data**. That Phase 7 holdout was not smooth: **2024 was basically flat
(+0.37% on 109 races)** and **2025 was much stronger (+105.38% on 66 races)**. The walk-forward
validation is honest and shows the real edge is probably **+20-25% ROI**, not the +47%
headline number. BEL is offline (track closed), the ML model adds zero value, and the daily
paper-trade wrapper is operational with its first 6 ROI-complete `CD_CORE_K8` settlements recorded and no current primary rows open for settlement, but the ROI-complete rows are 1 hit and 5 misses and still only 6/30 toward a first statistical read, so they are not promotion, live-profitability, or real-money evidence.

---

## 1. What Has Worked

| Finding | Evidence Quality | Key Numbers |
|---------|-----------------|-------------|
| **Key-1-to-Win bet structure** | Very strong (confirmed across all 8 phases, all tracks) | Best structure at every K value tested |
| **BEL broad1 rule** (K7, FS 11-13, gap>=22%, fav>=35%, fast, race 5+) | Strong — 10/13 LOOCV years, plateau stability (11/12 neighbors profitable), cross-track test confirms track-specific | +134.9% ROI on 85 races, bootstrap CI [+44%, +239%] |
| **OP durable rule** (K7, FS 11-12, gap>=5%, race 7+) | Solid — largest sample, low payout concentration, survives top-hit removal | +35% ROI on 505 races; still +14% after removing 3 biggest hits |
| **Phase 7 portfolio on 2024-2025 holdout** | Best forward evidence we have | **+38.68% ROI on 175 races** ($10,211 profit); split: 2024 **+0.37% on 109**, 2025 **+105.38% on 66** |
| **Phase 8 portfolio on 2024-2025 holdout** | Also positive but weaker | +21.45% ROI on 118 races ($5,585 profit); split: 2024 +9.50% on 85, 2025 +50.26% on 33 |
| **Probability gap as the key filter** | Strong — every feature engineering attempt confirmed gap captures the signal | All alternative features (fav_dominance, log_odds_ratio, top4_mass) were redundant |

## 2. What Has NOT Worked

| Attempt | Result | Lesson |
|---------|--------|--------|
| **XGBoost residual model** | Zero improvement over simple filters (confirmed in Backtest Report + Phase 1-6) | Without horse-specific features (speed figs, form), ML can't beat the market |
| **BEL -> BAQ bridge** | Walk-forward: **-91.55% ROI** on 7 races in 2024-2025 | BAQ is NOT a continuation of BEL. Do not alias them. |
| **Cross-track rule transfer** | BEL rule at AQU = -34.1%, at KEE = -42.3%, etc. | Edges are track-specific. Do not generalize. |
| **Phase 8 new tracks individually** | SA bootstrap CI crosses zero [-6.3%, +58.1%]; KEE crosses zero [-3.0%, +67.2%]; AQU went 0/3 in 2025 holdout (-100%); CD_REFINED_K9 lost -26.18% on holdout | New pockets need more forward data before real money |
| **Feature engineering** | fav_dominance, log_odds_ratio, top4_mass — all redundant with gap | Stop trying to extract more from odds-only features |
| **DMR fall rule** | Weakest leg: CI [-28.8%, +64.9%], P(loss) = 26.4% | First cut candidate |

## 3. Biggest Time Sinks

| Time Sink | Estimated Effort | What It Produced |
|-----------|-----------------|------------------|
| **Phase escalation (8 phases)** | Huge — 8 backtest scripts, ~300K lines of CSV output | Each phase added complexity. Walk-forward shows the honest edge is ~+22%, well below Phase 8's +47% headline. Diminishing returns after Phase 7. |
| **Multi-track expansion (Phase 8)** | Large — searched 20,160 variants across 7 tracks | Phase 8 (7 tracks) actually did WORSE on holdout than Phase 7 (3 tracks): +21.45% vs +38.68%. More rules = more overfit risk, not more edge. |
| **ML model pipeline** | Moderate — XGBoost training, tuning, prediction scripts | Confirmed dead end. The model's R² on payout correction is decent (0.47) but doesn't translate to betting profit. |
| **Paper trade infrastructure** | Moderate — 4 scripts, EV engine, shell wrappers | Fully built and now exercised by saved daily wrapper runs. Current primary ledgers now show 6 ROI-complete `CD_CORE_K8` settlements, no open primary settlement rows, 17% observed hit rate, and -79% flat-ticket ROI, which proves the scan/log/settle/read path is working but is still only 6/30 toward a first statistical read and not strategy-change proof. |
| **BEL/BAQ investigation** | Small-moderate | Confirmed dead end. BAQ is structurally different from BEL. |

## 4. How to Cut Them

| Problem | Fix |
|---------|-----|
| **Phase inflation** | Freeze at Phase 7 rules for paper trading. Phase 8 additions are research candidates only until they prove themselves forward. |
| **Multi-track overfit** | Paper trade the 3 Phase 7 rules (BEL, OP, CD) as the primary portfolio. Track Phase 8 additions (AQU, SA, KEE, DMR) separately as "watch list" — log but don't size bets. |
| **ML rabbit hole** | Stop. Unless you get horse-specific features (speed figs, form cycle, jockey/trainer stats), the model cannot beat odds-derived filters. Park the XGBoost code. |
| **Paper-trade observation gap** | Keep the daily wrapper running on OP / CD race days. The pipeline is operational; the remaining gap is qualifying observations plus ROI-complete settlements, not more rule tuning or a new edge claim from clean empty/no-target runs. |
| **Report sprawl** | This document is the single source of truth going forward. One file, honest numbers. |

---

## 5. The Evidence Hierarchy (Most to Least Trustworthy)

This is the core ranking Cole needs. Rules are ordered by **forward evidence quality**, not backtest ROI.

### Tier 1 — Deploy to paper trade immediately

| Rule | Holdout ROI (2024-2025) | Holdout Races | Walk-Forward | Backtest ROI | Confidence |
|------|------------------------|---------------|--------------|-------------|------------|
| **OP_DURABLE_K7** (Phase 7) | +22.9% | 115 | Selected in 7/10 folds | +35.0% (505 races) | **HIGH** — largest forward sample, most selected rule in walk-forward |
| **CD_CORE_K8** (Phase 7) | +55.96% | 60 | Selected in 1 fold (but CD_REFINED selected in 7) | +13.1% (485 races) | **MEDIUM-HIGH** — holdout looks great, but CD variants are confusing (K8 vs K9) |

### Tier 2 — Track in paper trade, do NOT size bets yet

| Rule | Holdout ROI | Holdout Races | Walk-Forward | Concern |
|------|------------|---------------|--------------|---------|
| **BEL_BROAD1_K7** | N/A — 0 holdout races | 0 | Selected 3/10 folds (+ bridge 6/10) | Track closed. Cannot validate forward. Strongest backtest signal but untestable. |
| **OP_REFINED_K7** (Phase 8) | +51.43% | 49 | Selected 2/10 folds | Only 49 holdout races; 2024 was -25.47%, 2025 was +210%. Wild variance. |
| **KEE_K9** (Phase 8) | +13.33% | 20 | Selected 3/10 folds | Only 20 holdout races. Bootstrap CI crosses zero. |

### Tier 3 — Watch only, high skepticism

| Rule | Holdout ROI | Holdout Races | Concern |
|------|------------|---------------|---------|
| **AQU_K9** | -4.28% | 8 | **Negative on holdout.** Went 0/3 in 2025. 8 races is nothing. |
| **SA_K9** | +39.28% | 11 | Only 11 holdout races. Bootstrap CI crosses zero on full sample. |
| **CD_REFINED_K9** | -26.18% | 16 | **Negative on holdout** (-14.54% in 2024, -61.12% in 2025). Worse than simpler CD_CORE_K8. |
| **DMR_FALL_K7** | +103.36% | 14 | Only 14 holdout races. P(loss) = 26.4% on full sample. One good hit skews everything. |

### Key Insight

**Phase 7's simpler portfolio beat Phase 8 on forward data.** The 3-track portfolio (+38.68% holdout, with 2024 +0.37% on 109 and 2025 +105.38% on 66) outperformed the 7-track portfolio (+21.45% holdout, with 2024 +9.50% on 85 and 2025 +50.26% on 33). Simpler wins, but not because it produced a smooth two-year path.

---

## 6. Walk-Forward Reality Check

The walk-forward validation script (honest implementation, explicit caveats) produced:

| Metric | Full-Sample Phase 8 | Full-Sample Phase 7 | Walk-Forward (Train-Only) |
|--------|---------------------|---------------------|--------------------------|
| **ROI** | +46.7% | +28.0% | **+22.46%** |
| **Positive years** | 14/15 | 12/15 | **8/10** |
| **Races** | 887 | 1,075 | 470 |

The walk-forward result (+22.46%) is the most honest number in this project. It accounts for:
- Rules selected only on prior data (no future leak)
- Portfolio-level evaluation (not cherry-picked single rules)
- Realistic rule switching year-to-year

**But even this is optimistic** because the candidate universe was mined from full-sample research. A true from-scratch search would likely produce +15-20% ROI.

### Unstable years in walk-forward
- **2015**: -39.24% ROI on 55 races
- **2024**: -19.95% ROI on 45 races

Two losing years out of ten. That's real.

---

## 7. Honest Expected ROI Range Going Forward

| Scenario | Expected ROI | Basis |
|----------|-------------|-------|
| **Optimistic** (full-sample Phase 7) | +28% | Backtest on 1,075 races |
| **Realistic** (walk-forward) | +20-25% | Train-only selection, 470 races |
| **Conservative** (walk-forward minus BEL) | +10-18% | OP + CD without BEL anchor |
| **Pessimistic** (single bad year) | -20% to -40% | 2015 and 2024 both happened |

**Do not expect +47%.** That number includes full-sample overfit from Phase 8 track expansion.

---

## 8. BEL / BAQ Status

- **Belmont Park** closed for renovation. Expected reopening 2025-2026 season (unclear exact date).
- **BAQ (Big A at Aqueduct)** has been hosting some races during closure.
- The walk-forward tested a BEL->BAQ bridge: **-91.55% ROI on 7 races**. Dead end.
- Until BEL reopens and produces qualifying races, the BEL rule is **dormant**.
- Do NOT bet BAQ as if it were BEL. The edge does not transfer.

---

## 9. Methodical Test Order

This is the exact sequence to evaluate approaches. Do NOT skip steps or jump ahead.

Gate source: the sample floors in this methodical order are sourced from `forward_evidence_scorecard.json` `decision_gate_minimums`: `anchor_displacement.min_roi_complete_settled_observations=30`, `phase8_promotion_review.min_roi_complete_settled_observations=20`, and `real_money_discussion.min_total_settled_observations_with_usable_roi=100`. These are future ROI-complete paper-observation floors only: 20 shadow rows open Phase 8 review, 30 same-candidate rows open anchor-review discussion, and 100 total rows only open a human real-money-discussion review after settlement-quality/payout/concentration checks. They do not mean any gate has cleared. `current_evidence_summary.json.scorecard_audit_route` is the bridge-owned route to the copied-gate/ranking audit: when the question is whether report-facing surfaces still copy those floors, the tier-first ranking contract, OP_REFINED CI-only support context, generated-at timezone provenance, and the no-BAQ-as-BEL prerequisite correctly, read `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` and run `python3 validate_scorecard_ranking_contract_audit.py`; that route and audit are report-synchronization metadata only, not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

### Step 1: Paper trade Phase 7 core (OP + CD) — Keep the wrapper running on target days
- The first clean runs and the first tiny settled sample are workflow validation and observation collection, not decision-grade forward proof by themselves.
- Current wrapper status: operational, with saved no-target / active-hit surfaces and 6 ROI-complete primary-lane settlements, no open primary settlement rows, observed hit rate 16.67%, observed flat-ticket ROI -79.34%, and 24 more ROI-complete rows still needed before the first 30-race statistical read.
- Use existing `paper_trade_pipeline.py` through `./run_daily_portfolio_observation.sh` to scan daily
- Target: OP races only when the current calendar/preflight says Oaklawn is actually active; the Jan-May meet window is seasonal context, not a standing "now" instruction.
- Target: CD races only when the current calendar/preflight says Churchill is active; the Apr-Nov meet window is seasonal context, not a substitute for the daily target-track check.
- Log every qualifying race, whether you bet or not
- Track: did the race qualify? What was the actual result? What would the P&L have been?
- **Success criteria**: 30+ races logged with actual outcomes before making any changes
- **Timeline**: 2-4 weeks depending on race volume

### Step 2: Validate paper trade results vs. backtest expectations
- After 30+ races: compare actual hit rate to expected (~17% for OP, ~33% for CD)
- Compare actual ROI to expected range (+15% to +35%)
- If actual hit rate is within 2 standard deviations of expected: proceed
- If actual hit rate is significantly below: investigate (are the filters matching correctly? Are odds being computed the same way?)

### Step 3: Add Phase 8 watch-list rules as shadow bets
- Log AQU, SA, KEE, DMR, OP_REFINED, CD_REFINED as paper-only entries
- Do NOT size these. Just record if they would have qualified and what happened.
- **Success criteria**: 20+ shadow observations per rule before any promotion

### Step 4: Evaluate BEL when it reopens
- When Belmont reopens, immediately start logging qualifying races
- First 10 qualifying races are observation only (no bets, even paper)
- Compare hit rate to historical 30.6%
- If 3+ hits in first 10 races: begin paper trading at full size

### Step 5: After 100+ ROI-complete paper observations total — evidence review, not bankroll advice
- Compute portfolio-level ROI, hit rate, Sharpe ratio, payout concentration, and settlement-quality coverage.
- Compare to the walk-forward expected range (+20-25% realistic, not +47% headline) and the OP/CD rule-level baselines.
- If results are within one standard error **and** payout/concentration checks are sane, write a paper-trade review memo and decide whether a separate, human-approved real-money risk plan is even worth discussing; this status doc does not recommend a bet size.
- If results are below -10% ROI at 100+ races, fail settlement-quality checks, or depend on one outlier payout: stop and re-evaluate before any real-money discussion.

### Step 6: Real-money discussion is out of scope until Step 5 passes
- Do not place, size, or scale real-money bets from this document.
- Any future real-money plan needs separate human review after 100+ ROI-complete paper observations, payout/concentration sanity checks, settlement-quality checks, and the no-BAQ-as-BEL guardrail are all satisfied.
- Keep the default posture as paper observation; no bankroll, stop-loss, or scale-up numbers are authorized here.
- If Cole later approves a real-money pilot, document it in a separate risk memo rather than inheriting an old status-doc line.

---

## 10. Next Operator Session — Concrete Current Routine

This is no longer a one-night setup checklist. The stack has been exercised, so the next useful work is repeatable observation with strict evidence boundaries.

### First 5 minutes: current status and calendar read
- [ ] Read `PAPER_TRADE_NOW.md` plus `PAPER_TRADE_NOW.json` first, before opening older run folders.
- [ ] If the card is stale, run `./run_daily_portfolio_observation.sh` before treating any lane detail as current.
- [ ] If OP / CD are not racing or the preflight says no target tracks, stand down; do not backfill a signal, do not substitute BAQ for BEL, and do not treat a clean empty day as performance evidence.

### Target race day: collect observations, not new rules
- [ ] Run `./run_daily_portfolio_observation.sh` as the preferred primary + shadow wrapper.
- [ ] Read `out/daily_portfolio_runs/<YYYY-MM-DD>/daily_summary.txt`, then the refreshed `PAPER_TRADE_NOW.*`, `OPS_HISTORY.md`, and `out/paper_trade_settlement_audit.md`.
- [ ] If a qualifying paper signal appears, sync the settlement template with `paper_trade_settlement_sync.py`; keep the row open until an actual result can be filled.
- [ ] Do NOT optimize filters or widen the combo universe from one good or bad observation.

### After outcomes exist: settlement-quality gate
- [ ] Use `paper_trade_settlement_helper.py` to fill actual result, payout, and cost fields rather than hand-editing rows ad hoc.
- [ ] Run `paper_trade_forward_check.py` and `paper_trade_lane_monitor.py` only after settlement rows are ROI-complete.
- [ ] Require 30+ settled primary observations before changing rules and 100+ total observations before any real-money discussion.

### Validation after operator-surface edits
- [ ] For wrapper / top-card / ops-history edits, run `python3 validate_run_daily_portfolio_observation.py`, `python3 validate_paper_trade_now.py`, `python3 validate_paper_trade_ops_history.py`, then `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json`.
- [ ] For main status / navigation wording edits, run `python3 validate_cole_status_and_plan.py` and `python3 validate_project_surfaces.py --reuse-existing-child-json`.
- [ ] Treat green validators as reproducibility/readiness checks only — not settled ROI, promotion readiness, live profitability, or real-money evidence.

---

## 11. What NOT to Do Tonight

1. **Do not tweak rules** based on one day's results. You need 30+ observations minimum.
2. **Do not bet real money.** Paper trade first.
3. **Do not try to fix the XGBoost model.** It's a dead end without new features.
4. **Do not alias BAQ as BEL.** The walk-forward proved this loses.
5. **Do not trust Phase 8 headline numbers** (+47% ROI). Use the walk-forward number (+22%) as your base case.
6. **Do not add complexity.** Phase 7's 3 rules outperformed Phase 8's 7 rules on forward data.

---

## 12. Implementation Note — Forward Evidence Scorecard

### `forward_evidence_scorecard.py`

A small script that reads the existing evaluation CSVs and produces a single ranked table of rules by **forward evidence quality** — not backtest ROI.

**What it does:**
- Reads `frozen_portfolio_eval_summary.csv` for holdout performance
- Reads `walk_forward_validation_folds.csv` for walk-forward selection frequency
- Computes a composite "forward trust score" based on:
  - Holdout ROI (most important)
  - Holdout sample size
  - Walk-forward selection frequency
  - Whether bootstrap CI excludes zero
- Outputs a ranked table to stdout and to `forward_evidence_scorecard.txt`
- Writes `forward_evidence_scorecard.csv` plus `forward_evidence_scorecard.json` so automated checks can compare the ranked rows, frozen-input source metadata, machine-readable `evidence_boundary` + `evidence_boundary_text`, machine-readable `decision_gate_minimums`, per-rule bootstrap-CI lower-bound source notes, and `PHASE7_REPORT.md` / `PHASE8_REPORT.md` report fingerprints
- Carries the same source-scope / evidence-boundary note into text and CSV, and publishes the JSON boundary both as machine-readable `evidence_boundary` plus legacy `evidence_boundary_text`: frozen 2024-2025 holdout plus train-only walk-forward only, not live scanner, settlement-audit, ledger, settled ROI, promotion readiness, live profitability, real-money evidence, or current-day profitability data; scorecard report fingerprints, bootstrap-CI source notes, and `decision_gate_minimums` are reproducibility / posture-gate metadata only, not settled ROI, promotion readiness, live profitability, or real-money evidence

**Why this matters:**
- Every existing report ranks rules by backtest ROI, which is the wrong metric for deployment decisions
- This script ranks by the evidence that actually predicts future performance
- Cole can run it in 2 seconds and get a clear "what do I trust?" answer

**What it does NOT do:**
- Does not modify any data or models
- Does not connect to any external APIs
- Does not read live paper-trade ledgers, current-day scanner output, settlement audits, or profitability results
- Read-only analysis of existing frozen CSVs

---

## 13. Suggested Reading Order (So You Don't Bounce Around)

If you only need the quickest honest answer, read in this order.

### For the evidence / deployment question

1. `forward_evidence_scorecard.txt` for the current forward-trust ranking
2. `OP_FAMILY_DECISION.md` for the anchor question inside the OP family
3. `CROSS_FAMILY_DECISION.md` for the anchor / paper / watch shortlist, current-paper snapshot caveat, and the explicit boundary that CD-only settled context / source-published settlement-queue state is not OP-anchor proof or cross-family promotion evidence
4. `PORTFOLIO_DECISION_CARD.md` for `PAPER NOW` vs `SHADOW ONLY` vs `BENCHMARK ONLY`
5. `METHOD_FAMILY_DECISION.md` for the selective-rule path versus the Harville benchmark and the parked current odds-only XGBoost path
6. `compare_main_approaches.md` plus its matched `.csv` and `.json` siblings for the one-screen OP/CD/shadow/Harville/XGBoost comparison, evidence-class triage, source-provenance/parity sidecar, machine-readable evidence_boundary metadata, machine-readable `decision_change_gate_minimums` naming `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100`, and evidence-scope decision-change gates

For full-data XGBoost retrain questions, read `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py` only as model-fit reproducibility context: large RMSE / MAE improvements and exact retrain/prediction commands are not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence. Deployment interpretation still routes back to the selective OP/CD paper path and the comparison artifacts above.

If Cole wants one bridge from the frozen ranking to the current paper-trade sample, read `CURRENT_EVIDENCE_SUMMARY.md` plus `current_evidence_summary.json`. It is a report/navigation summary only: 6 ROI-complete primary rows, all currently from `CD_CORE_K8` rather than `OP_DURABLE_K7`, 17% hit rate, and -79% flat-ticket ROI are current context, not promotion readiness, live profitability, OP-anchor forward proof, or real-money evidence. Bridge-published `decision_gate_progress` read: Gate progress: primary first-read 6/30; OP anchor same-candidate 0/30; Phase 8 weakest shadow 0/20; real-money discussion floor 6/100. All remain uncleared and are routing context only. Source-published settlement queue read: settlement queue state: `closed`; no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence. The shadow watch lane now has 1 ROI-complete settled row (1 from `CD_REFINED_K9`, 1/20 (5.0%)), while weakest shadow coverage remains 0/20; that is watch-list bookkeeping, not Phase 8 promotion evidence. The bridge's CSV recompute is timestamp-aware: rows need usable return/cost plus an actual non-placeholder `settled_ts` before they count as ROI-complete. Latest primary recommendation context: Latest run context: the latest live scan completed cleanly and found no qualifying races across 52 card(s) and 446 race(s). Treat this as operator context only; use recommendation and settlement ledgers before interpreting bet readiness or forward performance. The source-published settlement queue state stays `closed` / no open primary settlement rows, and the closed queue is settlement workflow metadata only. Operator read gate from `current_evidence_summary.json.operator_read_gate`: Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence. Gate status `current_operator_routing_context_only` and valid use `operator instruction/evidence-read gating only` are instruction/evidence-read routing only, not no-target evidence, clean-empty evidence, bet readiness, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence. Bridge rebuild order from `current_evidence_summary.json.rebuild_validation_contract`: after scorecard/rules/signals/settlement-ledger source-byte changes, run `python3 paper_trade_settlement_audit.py`, then `python3 current_evidence_summary.py`, then `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this order is provenance/rebuild metadata only, not settled ROI, promotion readiness, live profitability, or real-money evidence. Use the bridge's combined current-paper read route: `operator_status_context`, `source_freshness` / `requires_refresh_before_right_now_use`, and `operator_read_gate` / `requires_refresh_before_evidence_read` together; if the operator context says the right-now card is a wrapper-refresh or missing scan-output issue, or if source freshness says the source as-of date is older than the bridge reference date, refresh `./run_daily_portfolio_observation.sh` before treating the best-action card as today's operator instruction or evidence. Those operator-context, freshness, and read-gate fields are source-readiness metadata, not performance proof.

If that bridge rebuild will feed report-facing comparison quotes, do not stop after the three bridge commands. Run the copied-current-paper fanout first: frozen replay (`python3 validate_frozen_portfolio_eval_caution.py`), downstream A/B (`python3 validate_ab_downstream_comparison.py`), compare-main (`python3 validate_compare_main_approaches.py`), OP-anchor (`python3 validate_op_anchor_method_comparison.py`), OP-family (`python3 validate_op_family_decision.py`), cross-family (`python3 validate_cross_family_decision.py`), method-family (`python3 validate_method_family_decision_card.py`), portfolio (`python3 validate_portfolio_decision_card.py`), selective-scope (`python3 validate_compare_recommender_scope_paths.py`), scorecard audit (`python3 validate_scorecard_ranking_contract_audit.py`), frozen evidence chain (`python3 validate_frozen_evidence_chain.py --reuse-existing-child-json`), report surfaces (`python3 validate_report_surfaces.py --reuse-existing-child-json`), and project surfaces (`python3 validate_project_surfaces.py --reuse-existing-child-json`). Treat this fanout as copied-current-paper snapshot drift prevention only, not evidence movement, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

### For the live paper-trade operator question

1. `PAPER_TRADE_NOW.md` plus its matched `PAPER_TRADE_NOW.txt` and `PAPER_TRADE_NOW.json` siblings for the right-now top-card action; JSON should be source-matched to `paper_trade_now.py --format json` unless the full helper failed into an explicit no-new-forward-evidence placeholder.
2. `PAPER_TRADE_USAGE.md` for the OP-anchor-first command path, the primary OP/CD paper-basket companion inside the primary basket, the separate Phase 8 shadow/watch routine, and OP-anchor provenance/readable-boundary route (`OP_ANCHOR_METHOD_COMPARISON.md` / `op_anchor_method_comparison.json` plus `validate_op_anchor_method_comparison.py`, including JSON `evidence_boundary_text`) with fingerprints and boundary text kept audit-only rather than settled ROI, promotion readiness, live profitability, or real-money evidence.
3. `DAILY_ARTIFACT_GUIDE.md` for quiet-vs-broken triage, saved-live refresh scope, and the day-to-day repo map.
4. `out/paper_trade_settlement_audit.md` / `.json` for ledger-readiness and ROI-complete coverage routing only, not profitability proof.
5. `OPS_HISTORY.md` for rolling quiet-day versus issue-day context before over-reading one run folder.

### For the validation / "did I break anything?" question

1. `out/status_validation/project_surfaces/project_surfaces_validation.md` for the top-level cross-layer read
2. `out/status_validation/frozen_evidence_chain/frozen_evidence_chain_validation.md` when the question is research posture
3. `out/status_validation/frozen_portfolio_eval_caution/frozen_portfolio_eval_caution_validation.md` when the question is whether `FROZEN_PORTFOLIO_EVAL.md` still labels historical replay P&L as frozen evaluation rather than live paper-trade, real-money, or live-profitability evidence
4. `out/status_validation/compare_main_approaches/compare_main_approaches_validation.md` when the question is the one-screen main comparison, matched CSV/markdown/JSON bundle, evidence-class triage, method-family comparison, machine-readable evidence boundary, machine-readable `decision_change_gate_minimums`, or evidence-scope decision-change gates
5. `out/status_validation/paper_trade_operator_suite/paper_trade_operator_suite_validation.md` when the question is live paper-trade behavior
6. `out/status_validation/paper_trade_now/paper_trade_now_validation.md` when the question is whether the single top-card operator action, text/markdown/JSON parity, or helper-failure JSON placeholder still points at the right next command and lane
7. `out/status_validation/current_hierarchy_language/current_hierarchy_language_validation.md` when the question is whether `OP_DURABLE_K7` / `CD_CORE_K8` / `OP_REFINED_K7` wording and `live_hierarchy` structured keys still preserve anchor / paper-basket companion / same-family shadow-watch roles without treating legacy `primary_shadow` compatibility as promotion evidence
8. `out/status_validation/live_scan_targeting_and_limit_status/live_scan_targeting_and_limit_status_validation.md` for scanner target prefilter / `--max-races` limited-coverage status routing, then `out/status_validation/paper_trade_pipeline/paper_trade_pipeline_validation.md`, `out/status_validation/paper_trade_recommender/paper_trade_recommender_validation.md`, `out/status_validation/ev_ticket_engine/ev_ticket_engine_validation.md`, and `out/status_validation/paper_trade_logger/paper_trade_logger_validation.md` when the question is upstream scan -> recommend -> size -> log behavior rather than downstream operator phrasing
9. `out/status_validation/report_surfaces/report_surfaces_validation.md` when the question is shareable wording or presentation drift, including whether the narrative report sweep preserved the README-inherited wrapper-leaf source-of-truth note instead of flattening it away and kept its machine-readable evidence boundary separate from settled ROI, live profitability, promotion readiness, and real-money evidence
10. `out/status_validation/working_status_report/working_status_report_validation.md` when the question is whether the dated live/demo-vs-production note still keeps the report-time evidence anchor and mutable `latest_demo_run.json` alias straight
11. `out/status_validation/validation_quickstart/validation_quickstart_validation.md` when the question is whether the validation runbook still points to the right validators, the broader operator-suite route, direct source-layer routes, parent-rollup reuse shortcut guardrails, documented output paths, the dated-report / legacy-alias policy, and its machine-readable navigation evidence boundary
12. `out/status_validation/daily_artifact_guide/daily_artifact_guide_validation.md` when the question is what to read day to day or whether the daily repo-map guidance drifted
13. `out/status_validation/paper_trade_usage/paper_trade_usage_validation.md` when the question is whether the hands-on operator runbook still reflects the current OP-anchor-first start path, primary OP/CD paper-basket companion inside the primary basket, separate Phase 8 shadow/watch routine, OP-anchor provenance/readable-boundary route, audit-only fingerprint and boundary-text boundary, and direct source-layer validator ladder
14. `out/status_validation/cole_status_and_plan/cole_status_and_plan_validation.md` when the question is whether this main status document and repo map still point at the right frozen story, file paths, and machine-readable status-map evidence boundary
15. `out/status_validation/decision_cards_suite/decision_cards_suite_validation.md` only when you need the direct card-level wording and ordering details

For the full-data XGBoost retrain artifact specifically, use `out/status_validation/full_data_retrain_artifacts/full_data_retrain_artifacts_validation.md`; its green read is model-fit reproducibility metadata only, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

Parent-rollup shortcut: if the underlying child validator outputs are already fresh and the edit only touched a parent rollup or top-level wording, the smaller honest reruns are `python3 validate_decision_cards_suite.py --reuse-existing-child-json`, `python3 validate_frozen_evidence_chain.py --reuse-existing-child-json`, `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json`, `python3 validate_report_surfaces.py --reuse-existing-child-json`, or `python3 validate_project_surfaces.py --reuse-existing-child-json`.

Practical rule: start with the top project-surface card, then drill down only if the higher layer leaves a real question unanswered.

---

## Appendix: File Map (What's Important)

| File | What It Is | Read Priority |
|------|-----------|---------------|
| **This file** (`COLE_STATUS_AND_PLAN.md`) | Honest status + plan | **READ FIRST** |
| `validate_cole_status_and_plan.py` | Rebuild/consistency check for the main status doc, including the frozen headline posture, the validation reading order, the main repo-map paths, and a machine-readable evidence boundary for status/map alignment only | Run when changing `COLE_STATUS_AND_PLAN.md` or the main status-doc / repo-map guidance |
| `DAILY_ARTIFACT_GUIDE.md` | Compact daily-vs-benchmark guide, including where issue-day triage should jump from `PAPER_TRADE_NOW.md` / `PAPER_TRADE_NOW.json` into the direct pipeline/scanner sidecar pointers | Read after this file when operating the stack |
| `validate_daily_artifact_guide.py` | Rebuild/consistency check for the daily-use guide, including the scorecard-first research path, the matched PAPER_TRADE_NOW text/markdown/JSON operator path, the latest-run pointers, the issue-day sidecar-triage route, and the validation-ladder routing | Run when changing `DAILY_ARTIFACT_GUIDE.md` or the day-to-day repo-map guidance |
| `PAPER_TRADE_NOW.md` | Single best human operator action for the latest run, paired with `PAPER_TRADE_NOW.txt` and the matched machine-readable `PAPER_TRADE_NOW.json` sibling rather than separate evidence, with preserved primary/shadow recent-run context plus lifted lane why-now lines behind it and direct primary/shadow pipeline/scanner status-sidecar pointers for issue-day debugging. When the card is stale, those downstream lane details are inherited snapshot context rather than current-day state. | Read first on a live paper-trade day when you just want the next move, and keep the JSON sibling source-matched |
| `OPS_HISTORY.md` | Rolling quiet-day vs issue-day context across recent runs, so daily behavior is not judged from one folder in isolation | Read when a quiet stretch might be operational rather than market-driven |
| `validate_paper_trade_now.py` | Fixture validation for the top-level right-now launcher, including saved and shell-facing JSON, text, and markdown output rebuilds, `PAPER_TRADE_NOW.json` parity with `paper_trade_now.py --format json` or the explicit full-helper-failure placeholder, the live hierarchy, preserved primary/shadow recent-run context plus lifted lane why-now lines, pipeline-recorded scanner-status refresh actions, the stale-card inherited-snapshot honesty note, and direct primary/shadow pipeline/scanner status-sidecar pointers in the direct `paper_trade_now_validation.md` report | Run when changing `paper_trade_now.py`, `PAPER_TRADE_NOW.md` / `.txt` / `.json`, or the operator-priority card |
| `validate_current_hierarchy_language.py` | Current hierarchy wording / structured-key compatibility check across high-traffic surfaces and selected JSON/CSV fields; keeps `OP_DURABLE_K7` as anchor, `CD_CORE_K8` as the primary OP/CD paper-basket companion with legacy `primary_shadow` compatibility only, and `OP_REFINED_K7` as the same-family shadow/watch challenger; evidence boundary is wording / structured-key compatibility metadata only, not settled ROI, live profitability, promotion readiness, anchor-change, companion-change, or real-money evidence | Run when changing live hierarchy wording, `primary_companion` / `primary_shadow` keys, or paper companion versus Phase 8 shadow/watch phrasing |
| `forward_evidence_scorecard.py` | Rule ranking by forward evidence; writes matched text, CSV, and JSON sidecar surfaces with frozen source-scope / non-live-evidence metadata, machine-readable evidence boundary, machine-readable decision-gate minimums, plus bootstrap-CI source notes and report fingerprints | Run it |
| `forward_evidence_scorecard.txt` / `.csv` / `.json` | Generated scorecard surfaces: human read, tabular rows with CSV-visible bootstrap-CI source columns, and machine-readable metadata + ranked rows from the same frozen inputs, including structured `evidence_boundary`, legacy `evidence_boundary_text`, `decision_gate_minimums` for `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100` settled-observation gates, plus per-rule bootstrap-CI source notes and `PHASE7_REPORT.md` / `PHASE8_REPORT.md` report fingerprints | Read the text first; use CSV/JSON for parity and automation checks |
| `validate_forward_evidence_scorecard.py` | Rebuild/consistency check for the scorecard CSV, text, and JSON sidecar surfaces, including the current anchor / paper / watch / dormant read, source-scope / non-live-evidence boundary, CSV bootstrap-CI source-note columns, machine-readable JSON evidence boundary, machine-readable decision-gate minimums, and bootstrap-CI source-note / report-fingerprint provenance | Run when changing `forward_evidence_scorecard.py`, report-source fingerprints, bootstrap-CI source notes, CSV source-note columns, evidence-boundary metadata, gate-minimum metadata, or the scorecard ordering / wording |
| `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` | Cross-surface audit that the scorecard ranking contract, OP_REFINED CI-only diagnostic context, copied 30/20/100 gate floors, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite still match the source scorecard; this is report-synchronization / reproducibility metadata only, not promotion readiness, live profitability, bankroll guidance, or real-money evidence | Read when checking whether report-facing scorecard copies drifted |
| `validate_scorecard_ranking_contract_audit.py` | Direct validator for the scorecard ranking-contract audit, including source-matched report-surface fingerprints, source-copied `decision_gate_minimums`, no-BAQ prerequisite routing, generated-at timezone provenance, and no-new-evidence boundaries | Run when changing scorecard ranking, gate-floor, OP_REFINED CI-only, or no-BAQ-as-BEL wording across report-facing surfaces |
| `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` | Report-ready bridge from the frozen scorecard posture to the current `PAPER_TRADE_NOW` / settlement-audit paper status, including source fingerprints, top-card / settlement-audit / timestamp-aware CSV source-consistency checks that require actual `settled_ts`, source-published settlement-queue state/context/detail with no currently open primary rows, `operator_status_context`, `source_freshness` / `requires_refresh_before_right_now_use` operator-readiness metadata, `operator_read_gate` instruction/evidence-read routing, OP anchor / CD companion / OP refined shadow roles, current primary rule mix showing 0 `OP_DURABLE_K7` and 6 `CD_CORE_K8` ROI-complete settled rows, current shadow watch coverage showing 1 ROI-complete settled row with `CD_REFINED_K9` at 1/20 (5.0%) and weakest shadow coverage still 0/20, direct `decision_gate_progress` read (Gate progress: primary first-read 6/30; OP anchor same-candidate 0/30; Phase 8 weakest shadow 0/20; real-money discussion floor 6/100. All remain uncleared and are routing context only.), source-published `scorecard_audit_route` to `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py`, source-published `rebuild_validation_contract` order (`python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`) as provenance/rebuild metadata only, latest primary recommendation context separated from source-published settlement-queue state/context, closed settlement-queue context with by-rule detail, and explicit no-new-forward-evidence / no-promotion / no-real-money boundaries | Read when Cole wants the shortest current-context summary without mistaking a stale right-now source, latest recommendation-state operator context, closed settlement workflow, or the tiny settled sample for OP-anchor proof or strategy-change evidence |
| `validate_current_evidence_summary.py` | Rebuild/parity check for the current evidence bridge, including timestamp-pinned CLI rerender parity, evidence-boundary flags, role hierarchy, source-consistency checks across `PAPER_TRADE_NOW`, settlement audit, and the timestamp-aware settlement CSV recompute, operator-status context checks that keep right-now ops routing separate from performance evidence, source-freshness checks that compare right-now as-of date to bridge reference date, bridge-published current CD-only settled-sample read, CSV settled_ts gap exclusion, 30 / 20 / 100 gates, BAQ-is-not-BEL wording, source fingerprints, and rebuild_validation_contract order | Run when changing `current_evidence_summary.py`, `CURRENT_EVIDENCE_SUMMARY.md`, `current_evidence_summary.json`, or the report-ready current-context bridge |
| `VALIDATION_QUICKSTART.md` | Short guide for which validator to run after which kind of change, including the broader operator-suite route, the direct source-layer paper-trade chain routes, the live-scan targeting / max-races limited-coverage route, the parent-rollup reuse shortcut guardrails, documented output paths, and the dated-report / legacy-alias policy | Read when the validation stack feels too nested |
| `validate_validation_quickstart.py` | Rebuild/consistency check for the quickstart runbook, including the current suite hierarchy, the broader operator-suite route, source-layer routes, live-scan targeting / limited-coverage route, parent-rollup reuse shortcut guardrails, documented output paths, dated-report / legacy-alias policy, and machine-readable evidence boundary for navigation/read-order reproducibility only | Run when changing `VALIDATION_QUICKSTART.md` or the documented validation ladder |
| `COLE_PRESENTATION_OUTLINE.md` | Shareable deck-outline surface for Cole's presentation story, kept aligned with the frozen anchor / paper / benchmark posture | Read when preparing slides or checking concise presentation wording |
| `validate_cole_presentation_outline.py` | Rebuild/consistency check for the presentation outline, including the frozen anchor, paper baseline, selector benchmark read, Phase 8 shadow-only stance, and method-family roles | Run when changing `COLE_PRESENTATION_OUTLINE.md` or deck-facing posture wording |
| `validate_report_surfaces.py` | One-command sweep across README, the long-form report, the working-status report, the presentation outline, and the shareable HTML report so the main human-facing story stays aligned, including the README-inherited wrapper-leaf source-of-truth note that the narrative rollup should preserve rather than flatten away plus a machine-readable evidence boundary that keeps narrative validation separate from settled ROI, live profitability, promotion readiness, and real-money evidence | Run after report/deck wording edits when you want one quick green/red read across the narrative surfaces |
| `WORKING_STATUS_REPORT_2026-04-15.md` | Dated live/demo-vs-production status note, with the 2026-04-15 Keeneland demo artifacts as the stable evidence anchor and `latest_demo_run.json` treated as a mutable convenience alias | Read when you need the corrected operational state for production basket vs demo lane |
| `validate_working_status_report.py` | Rebuild/consistency check for the dated working-status note, including the OP/CD production-basket distinction, the separate demo lane, the report-time evidence anchor, and the mutable `latest_demo_run.json` alias | Run when changing `WORKING_STATUS_REPORT_2026-04-15.md` or the dated live/demo-vs-production framing |
| `OP_FAMILY_DECISION.md` | Short answer to whether anything beats OP_DURABLE_K7 yet | Read after the scorecard |
| `validate_op_family_decision.py` | Rebuild/consistency check for the OP-family card, including saved CSV/markdown surfaces, real CLI stdout, and the conservative anchor-replacement bar | Run when changing `op_family_decision.py` or the OP-family promotion logic |
| `CROSS_FAMILY_DECISION.md` | Compact anchor / paper / watch card for OP_DURABLE_K7 vs CD_CORE_K8 vs OP_REFINED_K7, plus the current-paper snapshot caveat that keeps CD-only settled context and source-published settlement-queue state out of OP-anchor proof or cross-family promotion evidence | Read after the OP card |
| `validate_cross_family_decision.py` | Rebuild/consistency check for the cross-family shortlist, including saved CSV/markdown surfaces, real CLI stdout, the current anchor / paper / watch ordering, current-paper snapshot caveat, and no cross-family promotion-evidence boundary | Run when changing `cross_family_decision_card.py`, the active-rule ordering logic, or the current-paper snapshot caveat |
| `PORTFOLIO_DECISION_CARD.md` | Compact paper / shadow / benchmark card for Phase 7 vs Phase 8 vs the train-only selector | Read with the cross-family card |
| `validate_portfolio_decision_card.py` | Rebuild/consistency check for the top-level portfolio card, including saved CSV/markdown surfaces, real CLI stdout, and the current paper / shadow / benchmark ordering | Run when changing `portfolio_decision_card.py` or the portfolio-level ordering logic |
| `METHOD_FAMILY_DECISION.md` | Compact method-level card for the selective rule path versus the Harville benchmark and the parked current odds-only XGBoost path | Read when deciding what to retire vs paper trade |
| `validate_method_family_decision_card.py` | Rebuild/consistency check for the method-family card, including saved CSV/markdown surfaces, real CLI stdout, and the current selective-rule / Harville / XGBoost ordering | Run when changing `method_family_decision_card.py` or the method-family retirement logic |
| `validate_decision_cards_suite.py` | One-command sweep across the four direct decision-card validators with a compact summary report | Run after editing any report-facing decision card when you want one quick green/red read |
| `compare_main_approaches.md` / `.csv` / `.json` | Matched main-comparison bundle for the current OP/CD paper core, `OP_REFINED_K7` shadow-only challenger, Harville benchmark-only lane, parked current odds-only XGBoost lane, BEL-not-BAQ caution, source provenance, machine-readable evidence_boundary metadata, machine-readable `decision_change_gate_minimums` naming `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100`, and evidence-scope decision-change gates; the JSON sidecar carries parity/provenance plus evidence_boundary and decision_change_gate_minimums metadata, not new live or promotion evidence | Read the markdown when Cole needs the broad method/portfolio comparison; use CSV/JSON for automation/parity without treating clean scans, open signals, replay rows, hashes, or odds-only reruns as promotion evidence |
| `validate_compare_main_approaches.py` | Rebuild/consistency check for the main comparison harness against frozen holdout and walk-forward sources, including saved CSV/markdown/JSON sidecar surfaces, real CLI stdout, the machine-readable evidence_boundary contract, the machine-readable `decision_change_gate_minimums` contract, and the current evidence-scope deployment-posture guardrails | Run when changing `compare_main_approaches.py` or the portfolio/method comparison layer |
| `AB_DOWNSTREAM_COMPARISON.md` | Report-safe downstream A/B summary for the baseline payout model versus the enriched horse-history XGBoost path, with an explicit guardrail that modest prediction gains still do not make that enriched path a paper-betting case | Read when explaining why the enriched horse-history XGBoost path remains research-only even after matched downstream prediction improvements |
| `validate_ab_downstream_comparison.py` | Source-aware consistency check for `ab_downstream_comparison.py`, including saved JSON/markdown surfaces, the winning-combos-only limitation, the current prediction-metric improvement read, and the still-not-better conservative EV pass counts; real CLI stdout / custom-output parity checks run when raw rebuild inputs are present, and otherwise publish explicit `SKIP` rows naming the missing inputs (`14years_major_tracks.csv`, `horse_features_major_tracks.csv` in this workspace) | Run when changing `ab_downstream_comparison.py`, the matched A/B model artifacts, raw A/B rebuild inputs, or the XGBoost downstream comparison layer |
| `FULL_DATA_RETRAIN_ARTIFACTS.md` | Full-data XGBoost retrain artifact for model-fit reproducibility only: large RMSE / MAE improvements and exact retrain/prediction commands are diagnostics, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence | Read only when checking the full-data retrain artifact or diagnostic commands; deployment interpretation still belongs to the selective OP/CD paper path and comparison artifacts |
| `validate_full_data_retrain_artifacts.py` | Direct validator for the full-data retrain artifact, including the evidence boundary, headline-metric caveat, exact retrain command, and diagnostic-only prediction command | Run when changing `FULL_DATA_RETRAIN_ARTIFACTS.md`, full-data retrain metrics, retrain/prediction commands, or XGBoost model-fit boundary wording |
| `OP_ANCHOR_METHOD_COMPARISON.md` / `op_anchor_method_comparison.json` | Compact cold-read comparison placing `OP_DURABLE_K7` beside Harville and the current odds-only XGBoost path, while making unlike evidence classes explicit, showing why OP still leads the paper-candidate lane, keeping the broader selective-family secondary line as replay-only context rather than extra train-only proof, and carrying exact source-byte provenance plus readable JSON `evidence_boundary_text` for the scorecard / compare-main / method-family / cross-family / downstream A/B inputs | Read when Cole wants one OP-centered answer for why the selective anchor still outranks the broad benchmark while the current odds-only XGBoost path stays parked unless its evidence class changes materially; treat the JSON boundary text/source fingerprints as reproducibility metadata only, not settled ROI, promotion readiness, live profitability, or real-money evidence |
| `validate_op_anchor_method_comparison.py` | Rebuild/consistency check for the OP-centered comparison artifact, including saved JSON/markdown surfaces, readable `evidence_boundary_text`, source provenance, row-identical source-byte drift coverage, real CLI stdout, the frozen OP anchor numbers, the explicit evidence-class labels, the Harville benchmark read, the parked current odds-only XGBoost reopening bar, the current OP-refined challenger context, and the replay-only selective-family secondary caution | Run when changing `op_anchor_method_comparison.py`, the OP anchor comparison layer, its readable boundary-text / source-fingerprint contract, or the method-family guardrail framing around `OP_DURABLE_K7` |
| `compare_recommender_scope_paths.py` | Report-safe side-by-side artifact for the default selective recommender path versus the explicit `--allow-all-combos` override on the same OP-anchor stub races, with an explicit guardrail that widened scope is a research counterfactual, not a paper-promotion case, plus modeled stub-EV lift / off-scope ticket-share splits that are not observed P&L | Read when explaining why the paper-trade recommender keeps the selective Phase 7 combo universe by default |
| `validate_compare_recommender_scope_paths.py` | Rebuild/consistency check for the selective-vs-widened recommender scope artifact, including saved JSON/markdown surfaces, real CLI stdout, the current mixed-universe and off-universe-only guardrail scenarios, and the not-observed-P&L modeled EV lift source | Run when changing `compare_recommender_scope_paths.py`, recommender combo-scope guardrails, or the live-vs-research scope comparison layer |
| `validate_frozen_decision_stack.py` | Rebuild/consistency check for the main scorecard and decision-card stack | Run when changing frozen rankings, rule roles, or report-facing decision cards |
| `validate_frozen_evidence_chain.py` | One-command sweep across the forward-evidence scorecard, main comparison harness, direct frozen-portfolio replay caution / metadata-sidecar check, frozen stack, decision-card suite, and the narrow OP-anchor / downstream A/B / selective-scope comparison validators for the full report-facing evidence chain, with child validation JSON fingerprints plus a machine-readable evidence boundary published as reproducibility metadata only | Run after structural/report-facing edits when you want one quick green/red read across the whole evidence chain |
| `validate_project_surfaces.py` | One-command sweep across the frozen evidence chain, the operator-facing paper-trade suite, the narrative report-surface suite, the direct current-hierarchy wording guardrail, and the repo-navigation, main status-doc, plus operator-runbook surfaces, with child validation JSON fingerprints and a machine-readable evidence boundary published as top-level reproducibility metadata only | Run after broader edits when you want one quick green/red read across research, live-ops, hierarchy wording, shareable report surfaces, and rerun/read guidance |
| `WALK_FORWARD_VALIDATION.md` | Most honest validation | Must read |
| `FROZEN_PORTFOLIO_EVAL.md` / `frozen_portfolio_eval_metadata.json` | Frozen 2024-2025 portfolio replay with the current evidence boundary plus exact source-byte fingerprints; holdout P&L is historical replay and hashes are reproducibility metadata, not a live paper-trade ledger or real-money evidence | Must read |
| `validate_frozen_portfolio_eval_caution.py` | Direct check that the frozen portfolio report and metadata sidecar keep the historical-replay / no-live-paper / no-real-money boundary, Phase 7-over-Phase 8 holdout read, `OP_DURABLE_K7` anchor, `CD_CORE_K8` paper companion, Phase 8 shadow/watch posture, exact source fingerprints, and `BAQ`-is-not-`BEL` caution | Run when changing `FROZEN_PORTFOLIO_EVAL.md`, `frozen_portfolio_eval_metadata.json`, `evaluate_frozen_portfolios.py`, or frozen replay wording |
| `PHASE7_REPORT.md` | Core portfolio discovery | Reference |
| `phase7_live_rules.json` | Original frozen Phase 7 ruleset, including dormant BEL | Reference |
| `phase7_current_paper_rules.json` | Current primary paper rule-component basket (OP + CD, with BEL removed because it is dormant; target cards still require daily preflight) | Use it |
| `phase8_shadow_rules.json` | Shadow-only Phase 8 watch-list basket | Use for observation only |
| `paper_trade_pipeline.py` | Daily scan pipeline | Use it |
| `validate_paper_trade_pipeline.py` | Fixture validation for the pipeline orchestrator, including skip-scan empty reuse, bets-ready reuse, scanner-failure fallback, empty/unreadable scanner-status sidecars, partial-cache activity, and signals-logged-no-bet status classification | Run when changing `paper_trade_pipeline.py` or the machine-readable pipeline status contract |
| `validate_live_scan_targeting_and_limit_status.py` | Direct scanner / pipeline / status-summary / ops-history guardrail for live-scan target prefiltering and `--max-races` limited coverage; proves capped scans spend detail attempts on OP/CD rule-candidate races, do not alias BAQ as BEL, and classify capped no-hit reads as operationally limited coverage with target-candidate/unattempted counts rather than clean empty forward observations | Run when changing live scanner targeting, `--max-races` coverage metadata, or limited-coverage status/ops routing; treat the pass as synthetic operational metadata only |
| `run_paper_trade_cycle.sh` | Legacy one-basket shell wrapper for pipeline | Keep for targeted debugging, but prefer `run_daily_portfolio_observation.sh` for the daily primary + shadow routine |
| `run_daily_portfolio_observation.sh` | Primary + shadow daily wrapper with separate ledgers, settlement templates, summaries, a shared preflight note, rolling ops-history refresh, explicit recommender/logger pipeline-error refresh behavior, and placeholder degradation when a lane loses its status sidecars | Preferred daily routine |
| `paper_trade_recommender.py` | Source-layer recommendation builder that turns scanner hits into Phase 7-filtered EV-sized plans | Use it through the pipeline unless you are debugging recommendation behavior directly |
| `validate_paper_trade_recommender.py` | Fixture validation for the recommender, including empty-scan summaries, default Phase 7 combo filtering, off-universe honest NO BET behavior, explicit `--allow-all-combos` widening, and malformed-prediction ERROR rows | Run when changing `paper_trade_recommender.py` or the combo-filter / recommendation-summary contract |
| `paper_trade_logger.py` | Source-layer ledger writer that appends persistent signal and recommendation rows while deduping prior `signal_key` values | Use it through the pipeline unless you are debugging ledger append behavior directly |
| `validate_paper_trade_logger.py` | Fixture validation for the persistent signal and recommendation ledgers, including empty-run header creation, serialized payload appends, dedup behavior, malformed-state fallback, and blank recommendation-key skips | Run when changing `paper_trade_logger.py` or the ledger append / dedup contract |
| `paper_trade_preflight_note.py` | Writes a one-line race-calendar note so empty days can say whether OP / CD were even active | Use with the daily wrapper |
| `paper_trade_daily_summary.py` | Builds the combined `daily_summary.txt` quick-jump surface from the current run artifacts, including the routed top-card focus/timing/freshness/ops snapshot, the explicit primary/shadow next-step states plus first-read and broader-review readiness lines, and the visible-but-not-live-promoted shadow review cue | Auto-used by the daily wrapper |
| `paper_trade_lane_summary.py` | Builds the expanded per-lane `summary.txt` block from the current lane artifacts, including the lifted no-overpromotion decision gate when forward/monitor artifacts provide it | Auto-used by the daily wrapper |
| `paper_trade_ops_history.py` | Builds a rolling ops log across recent run days so quiet stretches can be read as no-target, clean-empty, limited-coverage, explicit recommender/logger failure, pipeline-recorded scanner-status issue, or other operational issue days | Use when daily behavior needs context |
| `paper_trade_settlement_sync.py` | Syncs one settlement row per signal so forward ROI can be recorded cleanly | Use after daily runs |
| `paper_trade_settlement_helper.py` | Lists open settlement rows and updates one signal cleanly without hand-editing CSVs | Use when filling in race results |
| `paper_trade_forward_check.py` | Compares settled forward observations against frozen holdout hit-rate baselines and flat-ticket ROI when available | Use after outcomes start getting filled in |
| `paper_trade_lane_monitor.py` | Combines the current forward read plus pending settlement queue into one compact per-lane monitor | Use after daily runs or manual settlement updates |
| `paper_trade_next_steps.py` | Converts lane state into the exact next 2-3 commands to run | Use when the paper-trade stack feels ambiguous |
| `paper_trade_now.py` | Collapses the latest daily run into one best operator action plus a matched text/markdown/JSON top-card bundle, preserved primary/shadow recent-run context, lifted lane why-now lines, and rolling ops context, while marking stale downstream lane details as inherited snapshot context rather than current-day state | Use when you want one honest answer before opening several artifacts |
| `refresh_live_paper_trade_surfaces.py` | Rebuilds saved per-run operator surfaces, saved `preflight_note` text/JSON, plus top-level `OPS_HISTORY` / matched `PAPER_TRADE_NOW` text/markdown/JSON / `CURRENT_EVIDENCE_SUMMARY` markdown/JSON after source-layer render changes, preserving `current_evidence_summary.json.rebuild_validation_contract` as the settlement-audit -> current-bridge -> bridge-validator route, then rerenders each per-run `daily_summary.txt` against those refreshed top-level surfaces so the routed top-card focus/timing/freshness/ops snapshot, recent-run context, lifted lane why-now lines, and machine-readable JSON sibling stay source-matched without rerunning the full live wrapper, keeps `--latest-only` confined to the newest copied run's preflight, lane, and daily-summary surfaces, keeps `--skip-top-level` confined to leaving `OPS_HISTORY` / matched `PAPER_TRADE_NOW` / `CURRENT_EVIDENCE_SUMMARY` outputs untouched while still rerendering those per-run surfaces against the existing top-level outputs, and supports optional `--as-of-date` freshness pinning with stdout that says whether that pin was actually applied or ignored because top-level outputs were skipped, while keeping the inherited-snapshot honesty note if a rebuilt top card is still stale | Use after helper/render edits when the saved live paper-trade surfaces need a clean refresh |
| `PAPER_TRADE_USAGE.md` | Hands-on operator runbook for the live paper-trade stack, including the OP-anchor-first start path, the primary OP/CD paper-basket companion inside the primary basket, the separate Phase 8 shadow/watch routine, the OP-anchor markdown/JSON provenance plus readable-boundary route, and the audit-only fingerprint / boundary-text boundary | Read when you want the operational command path, provenance route, readable boundary-text route, and validator map in one place |
| `validate_paper_trade_usage.py` | Consistency check for the paper-trade operations runbook, including the OP-anchor start command, the primary OP/CD paper-basket companion inside the primary basket, the separate Phase 8 shadow/watch routine, OP-anchor provenance/readable-boundary route, audit-only fingerprint / boundary-text boundary, and the full operator-validator inventory | Run when changing `PAPER_TRADE_USAGE.md` or the operator runbook guidance |
| `validate_paper_trade_status_summary.py` | Fixture validation for the one-line base lane summary, including bet-ready, clean-empty, partial-cache, scanner-only alerts, cache-only-miss, missing-scan-output, generic scanner-failure, API-access / HTTP 403 action-recheck route preservation with `refresh_daily_wrapper_before_evidence_read` plus `./run_daily_portfolio_observation.sh` as operator context only, empty/unreadable/invalid-shape scanner sidecars, pipeline-recorded empty/unreadable/invalid-shape scanner-status states when a copied surface lacks the physical scanner sidecar, wrapper-only required-pipeline missing/empty/unreadable/invalid-shape sidecars, recommender-failure, logger-failure, and signals-without-bet across text and JSON paths, plus no-readable-sidecars cases, with saved human-facing recommender/logger failure lines preserving stage, error type, and detail and the saved summaries pinned against fresh source-layer renders | Run when changing `paper_trade_status_summary.py` or the wrapper's base-summary contract before lane enrichment |
| `validate_paper_trade_daily_summary.py` | Fixture validation for the combined daily summary surface, including the routed top-card focus/timing/freshness/ops snapshot, explicit primary/shadow next-step state lines plus lifted no-overpromotion decision-gate snapshot lines, first-read and broader-review readiness lines, the visible-without-live-promotion shadow review cue, pipeline-recorded scanner-status issue lines, explicit recommender/logger failure context, explicit missing-preflight and missing-lane-summary placeholders, plus a rebuild match on the rendered text | Run when changing the quick-jump / summary layer |
| `validate_paper_trade_lane_summary.py` | Fixture validation for the expanded per-lane summary surface, including lifted no-overpromotion decision-gate visibility, pipeline-recorded scanner-status base headlines, explicit recommender/logger pipeline-failure context, missing-base and missing-detail placeholders, plus a rebuild match on the rendered text | Run when changing the per-lane summary layer |
| `validate_paper_trade_next_steps.py` | Fixture validation for the per-lane next-step helper, including settlement-first, refresh-artifacts with distinct missing/empty/unreadable and pipeline-recorded scanner-status states, rerun-live, limited-cache, explicit recommender/logger pipeline-failure recovery, early-observation, collecting-sample, and decision-grade states, plus mixed-state `Latest run context` wording | Run when changing `paper_trade_next_steps.py` or the lane-state to command mapping |
| `validate_paper_trade_settlement_sync.py` | Fixture validation for the settlement-template sync helper, including empty-ledger, new-row, preserved-manual-settlement, and orphan-row cleanup behavior | Run when changing `paper_trade_settlement_sync.py` or the settlement-ledger contract |
| `validate_paper_trade_settlement_helper.py` | Fixture validation for the human-facing settlement helper, including open-queue rendering, separate settled-row ROI-gap visibility, queue truncation, exact single-row updates, settlement cost-source reporting, expected-cost fallback for omitted actual cost, supplied `settled_ts` validation, timestamp-omission warnings that the row stays outside ROI-complete sample gates, true missing/malformed-cost preservation, and missing-signal failure behavior, with the saved text, markdown, and JSON renders pinned against fresh source-layer formatter output | Run when changing `paper_trade_settlement_helper.py` or the operator settlement-edit flow |
| `validate_paper_trade_preflight_note.py` | Fixture validation for the shared preflight-note helper, including active-target, no-target, API-unreachable, explicit-error, and JSON payload behavior | Run when changing `paper_trade_preflight_note.py` or the empty-day calendar-read contract |
| `validate_paper_trade_forward_check.py` | Fixture validation for the frozen-baseline forward checker, including no-data, too-early, within-noise, running-cold, running-hot, ROI fallback with explicit actual-vs-expected-cost source counts, malformed `actual_cost` gap wording, no-overpromotion decision-gate wording, and missing-baseline states, with the JSON, text, and markdown outputs pinned against fresh source-layer renders | Run when changing `paper_trade_forward_check.py` or the frozen forward-comparison contract |
| `validate_paper_trade_lane_monitor.py` | Fixture validation for the compact lane monitor, including open-queue, truncation, no-data, missing-baseline, decision-grade ROI carry-through, and no-overpromotion decision-gate cases, with the JSON, text, and markdown renders pinned against fresh source-layer output | Run when changing `paper_trade_lane_monitor.py` or the compact forward-plus-queue surface |
| `validate_paper_trade_ops_history.py` | Fixture validation for the rolling ops-history surface, including bet-ready, no-target, zero-hit, limited-coverage, hit-found / no-bet, explicit recommender/logger failure, unreadable-calendar, missing/empty/unreadable artifact issue days, and pipeline-recorded scanner-status issue days | Run when changing `paper_trade_ops_history.py` or the day-bucket / takeaway logic |
| `validate_refresh_live_paper_trade_surfaces.py` | Fixture validation for the saved-live refresh helper, including per-run summary rebuilds, regenerated saved `preflight_note` text/JSON, regenerated top-level `OPS_HISTORY` / matched `PAPER_TRADE_NOW` text/markdown/JSON / `CURRENT_EVIDENCE_SUMMARY` markdown/JSON with JSON parity and `current_evidence_summary.json.rebuild_validation_contract` preserved, preserved rebuilt daily-summary top-card snapshot lines plus routed quick-read integrity, preserved rebuilt top-card recent-run context plus lifted lane why-now lines when current lane artifacts provide them, the stale rebuilt-card inherited-snapshot honesty note, `--latest-only` confined to the newest copied run's preflight, lane, and daily-summary surfaces, `--skip-top-level` leaving top-level outputs untouched while still rebuilding the per-run preflight/lane/daily layer against those existing top-level outputs, and honest `--as-of-date` applied-vs-skipped stdout behavior. Together with `validate_run_daily_portfolio_observation.py`, this is one of the two leaf source-of-truth wrapper reports whose inherited wrapper-guardrail inventory broader operator/project sweeps should preserve rather than flatten. | Run when changing `refresh_live_paper_trade_surfaces.py` or the saved-live rebuild path |
| `validate_run_daily_portfolio_observation.py` | End-to-end fixture validation for the real daily wrapper, including no-target and active-target cache-miss days, explicit recommender/logger pipeline-error refresh days, active hit-found but no-BET days, settle-first, partial-cache refresh, malformed-preflight, preflight-helper-failure, ops-history-fallback, right-now-helper-failure, forward-check-helper-failure, lane-monitor-helper-failure, and next-steps-helper-failure days, required `PAPER_TRADE_NOW.json` parity or explicit helper-failure placeholder behavior, missing-status placeholder, markdown-mirror fallback, lane-summary fallback, and daily-summary fallback days. Together with `validate_refresh_live_paper_trade_surfaces.py`, this is the other leaf source-of-truth wrapper report whose inherited wrapper-guardrail inventory broader operator/project sweeps should preserve rather than flatten. | Run when changing `run_daily_portfolio_observation.sh` or the way the wrapper stitches helper artifacts together |
| `validate_cache_only_messaging.py` | Fixture validation for no-target and active-target cache-only-miss messaging across the operator surfaces | Run when changing empty-day / cache-only messaging |
| `validate_partial_cache_messaging.py` | Fixture validation for active-target partial-cache messaging across the same operator surfaces | Run when changing partial-cache / limited-coverage messaging |
| `validate_paper_trade_operator_suite.py` | One-command sweep across the main operator-facing paper-trade validators and messaging fixtures, including direct base-status, preflight-note, settlement-sync, settlement-helper, next-steps, forward-check, lane-monitor, daily-summary, lane-summary, rolling ops-history, saved-live refresh-helper coverage, daily-wrapper coverage with explicit recommender/logger failure messaging, and the top-card pipeline/scanner sidecar-pointer contract, plus an auxiliary dependency note for the upstream scan -> recommend -> size -> log chain. This umbrella sweep is supposed to preserve the inherited wrapper-guardrail inventories from those two leaf wrapper reports rather than replacing them with one flattened green light, and now publishes a machine-readable operator-suite evidence boundary so a parent pass cannot be mistaken for settled ROI, live profitability, promotion readiness, or real-money evidence. | Run after editing operator-facing paper-trade summaries or empty-day messaging when you want one quick green/red read |
| `DIAGNOSE_CD_SELECTION.md` | Why walk-forward picks the wrong CD rule, and what the real benchmark is | Read after walk-forward report |
| `diagnose_cd_selection.py` | Counterfactual walk-forward diagnostic for CD_CORE vs CD_REFINED | Run it |
| `PHASE8_REPORT.md` | Legacy expanded-portfolio discovery report with a current-evidence caution banner; treat with skepticism when it conflicts with frozen holdout / walk-forward evidence | Optional context, not deployment guidance |
| `validate_phase8_report_caution.py` | Direct check that the Phase 8 legacy report opens with the current holdout-over-headline caution, keeps `OP_DURABLE_K7` as anchor, leaves Phase 8 shadow/watch, and preserves the no-real-money / BAQ-is-not-BEL boundaries | Run when changing `PHASE8_REPORT.md` or Phase 8 legacy-report wording |
| `BACKTEST_REPORT.md` | Phase 1-2 results (all negative ROI) | Background |
| `backtest_phase*.py` | Historical scripts | Don't modify |
| `ev_ticket_engine.py` | Conservative EV-based sizing engine that turns filtered combo predictions into a paper-trade stake plan | Use through the recommender / pipeline unless you are debugging stake sizing directly |
| `validate_ev_ticket_engine.py` | Fixture validation for the EV sizing layer, including empty-file NO BET behavior, negative-edge rejection, low-probability rejection, minimum-increment floor rejection, capped multi-ticket BET sizing, and malformed-input failure paths | Run when changing `ev_ticket_engine.py` or the stake-sizing contract |
| XGBoost/* | ML model code | **Ignore for now** |
