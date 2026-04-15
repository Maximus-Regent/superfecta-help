# Cole — Superfecta Project Status & Plan

**Date:** 2026-04-14  
**Author:** Max (via Claude audit)  
**Purpose:** Honest assessment for tonight's work session. No hype.

---

## TL;DR

The project has strong structural research (8 phases, 90K races, 75+ strategies tested).
The **Phase 7 three-track portfolio (BEL + OP + CD)** is the most trustworthy result.
Phase 8's seven-track expansion looks better on paper but **underperforms Phase 7 on
the actual holdout data**. The walk-forward validation is honest and shows the real edge
is probably **+20-25% ROI**, not the +47% headline number. BEL is offline (track closed),
the ML model adds zero value, and no live paper trades have been collected yet.

---

## 1. What Has Worked

| Finding | Evidence Quality | Key Numbers |
|---------|-----------------|-------------|
| **Key-1-to-Win bet structure** | Very strong (confirmed across all 8 phases, all tracks) | Best structure at every K value tested |
| **BEL broad1 rule** (K7, FS 11-13, gap>=22%, fav>=35%, fast, race 5+) | Strong — 10/13 LOOCV years, plateau stability (11/12 neighbors profitable), cross-track test confirms track-specific | +134.9% ROI on 85 races, bootstrap CI [+44%, +239%] |
| **OP durable rule** (K7, FS 11-12, gap>=5%, race 7+) | Solid — largest sample, low payout concentration, survives top-hit removal | +35% ROI on 505 races; still +14% after removing 3 biggest hits |
| **Phase 7 portfolio on 2024-2025 holdout** | Best forward evidence we have | **+38.68% ROI on 175 races** ($10,211 profit) |
| **Phase 8 portfolio on 2024-2025 holdout** | Also positive but weaker | +21.45% ROI on 118 races ($5,585 profit) |
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
| **Paper trade infrastructure** | Moderate — 4 scripts, EV engine, shell wrappers | Fully built but **never used**. Zero signals in the ledger. The tooling is ready but untested in production. |
| **BEL/BAQ investigation** | Small-moderate | Confirmed dead end. BAQ is structurally different from BEL. |

## 4. How to Cut Them

| Problem | Fix |
|---------|-----|
| **Phase inflation** | Freeze at Phase 7 rules for paper trading. Phase 8 additions are research candidates only until they prove themselves forward. |
| **Multi-track overfit** | Paper trade the 3 Phase 7 rules (BEL, OP, CD) as the primary portfolio. Track Phase 8 additions (AQU, SA, KEE, DMR) separately as "watch list" — log but don't size bets. |
| **ML rabbit hole** | Stop. Unless you get horse-specific features (speed figs, form cycle, jockey/trainer stats), the model cannot beat odds-derived filters. Park the XGBoost code. |
| **Unused paper trade infra** | Start using it tonight. The pipeline exists. The gap is operational, not technical. |
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

**Phase 7's simpler portfolio beat Phase 8 on forward data.** The 3-track portfolio (+38.68% holdout) outperformed the 7-track portfolio (+21.45% holdout). Simpler wins.

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

### Step 1: Paper trade Phase 7 core (OP + CD) — Start tonight
- Use existing `paper_trade_pipeline.py` to scan daily
- Target: OP races (Jan-May meet is active NOW — Oaklawn runs through ~May)
- Target: CD races (spring meet active NOW — Churchill runs Apr-Nov)
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

### Step 5: After 100+ paper trade observations total
- Compute portfolio-level ROI, hit rate, Sharpe ratio
- Compare to walk-forward expected (+22% ROI)
- If within 1 standard error: consider scaling to real money at small size ($2/combo)
- If below -10% ROI at 100+ races: stop and re-evaluate

### Step 6: Real money (only after Step 5 passes)
- Start at $2/combo flat
- Maximum bankroll at risk: $500
- Stop-loss: if cumulative ROI drops below -30% after 50+ bets, pause for 2 weeks
- Scale up only after 200+ real bets with positive cumulative ROI

---

## 10. Next 16 Hours — Concrete Staged Actions

### Hour 0-1: Orientation & setup
- [ ] Cole reads this document end-to-end
- [ ] Run `python forward_evidence_scorecard.py` (new script, created tonight) to see the rule ranking table
- [ ] Verify Python environment has pandas, numpy installed
- [ ] Test that `paper_trade_pipeline.py` runs without errors on today's cached data

### Hour 1-3: Get paper trading operational
- [ ] Run `./run_paper_trade_cycle.sh` and confirm it produces output
- [ ] Check `.live_scan_cache/` for today's race data (should be there from earlier run)
- [ ] Manually verify one qualifying race against the rules: does the filter logic match?
- [ ] If OP or CD have races today/tomorrow, log the first paper trade signal

### Hour 3-6: Understand the evidence
- [ ] Read `WALK_FORWARD_VALIDATION.md` — this is the most honest validation
- [ ] Read `FROZEN_PORTFOLIO_EVAL.md` — this is the holdout test
- [ ] Compare Phase 7 vs Phase 8 holdout numbers (Phase 7 wins: +38.68% vs +21.45%)
- [ ] Note which Phase 8 rules lost money on holdout (AQU: -4.28%, CD_REFINED: -26.18%)

### Hour 6-10: First real forward observations
- [ ] Set up a daily routine: run paper trade scan before first post time
- [ ] For each qualifying race, record in a simple spreadsheet:
  - Date, Track, Race#, Rule, Field Size, Fav Prob, Gap, Result (hit/miss), Payout if hit
- [ ] Do NOT optimize or tweak rules based on early results — just observe

### Hour 10-14: Review and adjust infrastructure
- [ ] If pipeline had errors, fix them
- [ ] If API access issues, document them
- [ ] Check: are the NYRA API race fields matching the filter definitions? (field size, condition, etc.)
- [ ] Write down any discrepancies between what the scanner reports and what you see on track sites

### Hour 14-16: Document and plan next session
- [ ] How many races were scanned? How many qualified?
- [ ] Any unexpected behavior from the pipeline?
- [ ] Update this document with "Session 1 notes" section at the bottom
- [ ] Set up tomorrow's scan schedule

---

## 11. What NOT to Do Tonight

1. **Do not tweak rules** based on one day's results. You need 30+ observations minimum.
2. **Do not bet real money.** Paper trade first.
3. **Do not try to fix the XGBoost model.** It's a dead end without new features.
4. **Do not alias BAQ as BEL.** The walk-forward proved this loses.
5. **Do not trust Phase 8 headline numbers** (+47% ROI). Use the walk-forward number (+22%) as your base case.
6. **Do not add complexity.** Phase 7's 3 rules outperformed Phase 8's 7 rules on forward data.

---

## 12. What Changed Tonight (Implementation)

### New file: `forward_evidence_scorecard.py`

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

**Why this matters:**
- Every existing report ranks rules by backtest ROI, which is the wrong metric for deployment decisions
- This script ranks by the evidence that actually predicts future performance
- Cole can run it in 2 seconds and get a clear "what do I trust?" answer

**What it does NOT do:**
- Does not modify any data or models
- Does not connect to any external APIs
- Read-only analysis of existing CSVs

---

## Appendix: File Map (What's Important)

| File | What It Is | Read Priority |
|------|-----------|---------------|
| **This file** (`COLE_STATUS_AND_PLAN.md`) | Honest status + plan | **READ FIRST** |
| `DAILY_ARTIFACT_GUIDE.md` | Compact guide for what to use daily vs benchmark-only | Read after this file when operating the stack |
| `forward_evidence_scorecard.py` | Rule ranking by forward evidence | Run it |
| `OP_FAMILY_DECISION.md` | Short answer to whether anything beats OP_DURABLE_K7 yet | Read after the scorecard |
| `CROSS_FAMILY_DECISION.md` | Compact anchor / paper / watch card for OP_DURABLE_K7 vs CD_CORE_K8 vs OP_REFINED_K7 | Read after the OP card |
| `PORTFOLIO_DECISION_CARD.md` | Compact paper / shadow / benchmark card for Phase 7 vs Phase 8 vs the train-only selector | Read with the cross-family card |
| `METHOD_FAMILY_DECISION.md` | Compact method-level card for Harville vs XGBoost vs the selective rule path | Read when deciding what to retire vs paper trade |
| `WALK_FORWARD_VALIDATION.md` | Most honest validation | Must read |
| `FROZEN_PORTFOLIO_EVAL.md` | Holdout test results | Must read |
| `PHASE7_REPORT.md` | Core portfolio discovery | Reference |
| `phase7_live_rules.json` | Original frozen Phase 7 ruleset, including dormant BEL | Reference |
| `phase7_current_paper_rules.json` | Current active paper basket (OP + CD, with BEL removed because it is dormant) | Use it |
| `phase8_shadow_rules.json` | Shadow-only Phase 8 watch-list basket | Use for observation only |
| `paper_trade_pipeline.py` | Daily scan pipeline | Use it |
| `run_paper_trade_cycle.sh` | One-basket shell wrapper for pipeline | Use it |
| `run_daily_portfolio_observation.sh` | Primary + shadow daily wrapper with separate ledgers, settlement templates, summaries, a shared preflight note, and rolling ops-history refresh | Preferred daily routine |
| `paper_trade_preflight_note.py` | Writes a one-line race-calendar note so empty days can say whether OP / CD were even active | Use with the daily wrapper |
| `paper_trade_ops_history.py` | Builds a rolling ops log across recent run days so quiet stretches can be read as no-target, clean-empty, or operationally broken | Use when daily behavior needs context |
| `paper_trade_settlement_sync.py` | Syncs one settlement row per signal so forward ROI can be recorded cleanly | Use after daily runs |
| `paper_trade_settlement_helper.py` | Lists open settlement rows and updates one signal cleanly without hand-editing CSVs | Use when filling in race results |
| `paper_trade_forward_check.py` | Compares settled forward observations against frozen holdout hit-rate baselines and flat-ticket ROI when available | Use after outcomes start getting filled in |
| `paper_trade_lane_monitor.py` | Combines the current forward read plus pending settlement queue into one compact per-lane monitor | Use after daily runs or manual settlement updates |
| `paper_trade_next_steps.py` | Converts lane state into the exact next 2-3 commands to run | Use when the paper-trade stack feels ambiguous |
| `DIAGNOSE_CD_SELECTION.md` | Why walk-forward picks the wrong CD rule, and what the real benchmark is | Read after walk-forward report |
| `diagnose_cd_selection.py` | Counterfactual walk-forward diagnostic for CD_CORE vs CD_REFINED | Run it |
| `PHASE8_REPORT.md` | Expanded portfolio (treat with skepticism) | Optional |
| `BACKTEST_REPORT.md` | Phase 1-2 results (all negative ROI) | Background |
| `backtest_phase*.py` | Historical scripts | Don't modify |
| `ev_ticket_engine.py` | EV-based bet sizing | Use after paper trade proves edge |
| XGBoost/* | ML model code | **Ignore for now** |
