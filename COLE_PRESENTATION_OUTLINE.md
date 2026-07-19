# Cole Presentation Outline, Honest Version

**Date:** 2026-04-14 23:16 EDT
**Use case:** short class update, project checkpoint, or report presentation
**Tone:** plain English, no hype, defend only what the evidence actually supports

---

## One-sentence thesis

We found a real-looking but smaller-than-advertised betting edge in a narrow set of superfecta situations, and the honest next step is paper trading the simpler Phase 7 rules, not claiming Phase 8 or ML solved the problem.

---

## 30-second version

If I only get half a minute, I would say this:

> I tested a superfecta strategy across a large historical dataset and found that a small set of simple favorite-gap rules held up better than the more complicated versions. The best honest forward-style number is about **+22.46% ROI in walk-forward testing**, not the flashy **+46.72%** full-sample Phase 8 result. On the actual 2024-2025 holdout, the simpler **Phase 7 portfolio beat Phase 8, +38.68% vs +21.45%**, but that Phase 7 edge was uneven: **2024 was basically flat (+0.37% on 109 races)** and **2025 was much stronger (+105.38% on 66 races)**. So my conclusion is not "mission accomplished." It is "there may be an edge, but it is narrow, track-specific, and needs paper trading before any real-money claim."

---

## Slide 1, The question

### Title
Can simple public-odds filters find a repeatable superfecta edge?

### What to say
- I wanted to test whether the betting market leaves a usable pricing mistake in superfectas.
- I focused on **simple, rule-based filters** built from public odds structure, especially the gap between the favorite and second choice.
- I deliberately compared simple rules against more complex ML and broader portfolio variants.

### Keep this honest
- This is **not** a claim that horse racing is easy to beat.
- This is a search for a narrow, testable edge.

---

## Slide 2, What the project actually built

### Title
What I tested

### What to say
- Historical coverage: about **14 years** of race data.
- Research process: **8 phases** of rule testing and refinement.
- Main betting structure that kept surviving: **Key-1-to-Win** superfecta tickets.
- Main rule variable that mattered: the **favorite-second probability gap**.

### Short line
The project got more complex over time, but the important signal stayed simple.

---

## Slide 3, The strongest evidence, not the prettiest number

### Title
Best honest result: walk-forward, not headline backtest ROI

### What to say
- Full-sample Phase 8 portfolio: **+46.72% ROI** on 887 races.
- Full-sample Phase 7 portfolio: **+27.97% ROI** on 1,075 races.
- But the better honesty check is train-only walk-forward:
  - **+22.46% ROI**
  - **470 races**
  - **8 positive years out of 10**
- That is the number I would defend first, because it uses prior years to choose rules before testing the next year.

### Keep this honest
- Even this is still somewhat optimistic because the candidate rule list came from earlier full-sample mining.
- So the realistic takeaway is closer to **roughly +20% to +25%**, not +47%.

---

## Slide 4, Simpler beat more complicated on the holdout

### Title
Phase 7 beat Phase 8 where it mattered most

### What to say
- On the later untouched holdout window, **2024-2025**:
  - **Phase 7 OP/CD rule-component basket:** **+38.68% ROI**, 175 races, **$10,210.61** profit; split: **2024 +0.37% on 109**, **2025 +105.38% on 66**; target cards still come from daily preflight
  - **Phase 8 frozen portfolio:** **+21.45% ROI**, 118 races, **$5,585.05** profit; split: **2024 +9.50% on 85**, **2025 +50.26% on 33**
- So the more complicated seven-track expansion did **not** beat the simpler three-track portfolio on forward-style data.

### Short line
More rules improved the backtest story, but not the holdout story, and the winning Phase 7 path was not a smooth two-year glide.

---

## Slide 5, What I would trust right now

### Title
Current deployment ranking

### What to say
- **Anchor:** `OP_DURABLE_K7`
  - Holdout: **+22.9% ROI on 115 races**
  - Holdout split: **2024 -47.41% on 68 races; 2025 +124.61% on 47 races**
  - Walk-forward selected in **7 of 10 folds**
  - Best mix of sample size and forward evidence
- **Paper trade now:** `CD_CORE_K8`
  - Holdout: **+55.96% ROI on 60 races**
  - Holdout split: **2024 +45.65% on 41 races; 2025 +78.21% on 19 races**
  - Good holdout, and positive in both holdout years
- **Watch only:** `OP_REFINED_K7`
  - Holdout: **+51.43% ROI on 49 races**
  - Holdout split: **2024 -25.47% on 33 races; 2025 +210.02% on 16 races**
  - Too small and too mixed to trust yet
- **Observation-only pockets:** `KEE_K9`, `SA_K9`, `DMR_FALL_K7`
  - Interesting enough to log, but still too small for near-promotion talk

### Short line
CD is the steadier two-positive-year paper candidate, OP_DURABLE is still the safest anchor because it has the bigger OP sample plus the strongest walk-forward support, OP_REFINED still looks more like a smaller hot-2025 challenger than a replacement, and the other Phase 8 names stay observation-only.

### Keep this honest
- Small-sample winners are not proof.
- Stronger forward evidence matters more than the highest ROI.
- OP_REFINED's positive CI lower bound is support context only; the current bridge source-matches `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` with `ci_only_promotion_allowed=false`, so it is not OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

---

## Slide 5A, Method-family guardrail

### Title
Which whole method families are still paper-worthy?

### What to say
- **Selective rule path = PAPER NOW**
  - Current frozen holdout: **+38.68% ROI on 175 races**; split: **2024 +0.37% on 109**, **2025 +105.38% on 66**
  - This is the only family here with positive current frozen holdout evidence and an actual paper-trade workflow, but the recent path was uneven rather than smooth
  - Current paper-companion read: `OP_DURABLE_K7` stays the safest anchor, `CD_CORE_K8` is the primary OP/CD paper-basket companion, and `OP_REFINED_K7` remains the narrower same-family OP shadow challenger rather than a promoted default
- **Harville-ranked probabilities = BENCHMARK ONLY**
  - Broad benchmark: **-24.05% ROI on 90004 races**
  - Useful structural baseline, but still not a paper candidate
- **XGBoost residual correction = RESEARCH ONLY**
  - Best ML betting line: **-24.16% ROI on 16724 races**
  - Prediction metrics improved a bit, but the downstream betting case still did not
  - Full-data retrain artifacts and exact retrain/prediction commands route to `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py`; large RMSE / MAE gains are model-fit reproducibility context only, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence

### Keep this honest
- A small model-metric improvement is **not** the same thing as a promotion case.
- First rule out dead-end method families, then compare the serious selective contenders against each other.
- The broader selective-family secondary lines elsewhere in the repo are replay context on walk-forward test years, not extra train-only validation.
- Inside the selective family, do not let the highest small-sample ROI outrun the current anchor / paper companion / same-family shadow challenger order.

---

## Slide 6, What failed

### Title
What did not survive scrutiny

### What to say
- **ML / XGBoost** did not improve betting decisions in a usable way.
- **BEL to BAQ bridging** failed badly: **-91.55% ROI on 7 races**.
- Several Phase 8 additions are weak or negative on holdout:
  - `CD_REFINED_K9`: **-26.18%** on 16 holdout races
  - `AQU_K9`: **-4.28%** on 8 holdout races
- Conclusion: the edge is **track-specific** and **fragile**. Generalizing too far makes it worse.

### Short line
Complexity produced more candidates, not more trust.

---

## Slide 7, What I would do next

### Title
Next step: operational proof, not more optimization

### What to say
- Start **paper trading the Phase 7 core**, mainly OP and CD.
- A clean first paper-trade run would prove the workflow works and observations are being captured, not that the edge is already confirmed live.
- The improved paper-trade stack is workflow hardening and observation capture, not new forward evidence by itself; genuinely new forward evidence starts when settled paper trades accumulate.
- Evidence-scope rule: only settled paper-trade rows with usable ROI coverage should change deployment posture; clean scans, open signals, historical replay rows, calibration-only summaries, or another odds-only rerun should not.
- Decision-gate source: `forward_evidence_scorecard.json` `decision_gate_minimums` sets `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100`; these are future ROI-complete observation floors, not cleared gates.
- Do **not** use real money yet.
- Do **not** tweak rules off one day or one week of results.
- Goal: log at least **30+ paper-trade observations** before changing anything.
- Treat Phase 8 extras as **shadow or watch-list rules**, not core bets.

### Recommendation line
The bottleneck is no longer code. It is collecting real forward observations.

---

## Slide 7A, Current paper-read bridge

### Title
What the current paper totals mean right now

### What to say
- For current paper totals, read `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` before quoting `PAPER_TRADE_NOW`, ops-bucket/operator-status context, settlement-audit, or primary-ledger numbers.
- The bridge currently says source consistency is matched across the top card, settlement audit, and primary settlement CSV.
- The bridge uses the combined current-paper route: `operator_status_context`, `source_freshness.requires_refresh_before_right_now_use=false`, and `operator_read_gate.requires_refresh_before_evidence_read=false`; the saved `PAPER_TRADE_NOW` best-action card is fresh against the bridge reference date, but operator read-gate routing still governs instruction/evidence use and is not performance evidence.
- The bridge also publishes `operator_read_gate.requires_refresh_before_evidence_read=false`: Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence.
- Scorecard audit route: `current_evidence_summary.json.scorecard_audit_route` -> `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks; this is report-synchronization metadata only, not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- Rebuild-order route: `current_evidence_summary.json.rebuild_validation_contract` -> `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` after scorecard/rules/signals/settlement-ledger byte changes and before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- Primary paper is still **6/30** ROI-complete toward a first statistical read and **6/100** toward broader review.
- The current settled sample is **CD-only**: `CD_CORE_K8` has **6** ROI-complete settled rows, while `OP_DURABLE_K7` has **0**.
- Latest primary recommendation context: Latest run context: the latest live scan completed cleanly and found no qualifying races across 52 card(s) and 446 race(s). Treat this as operator context only; use recommendation and settlement ledgers before interpreting bet readiness or forward performance.
- Settlement queue state: `closed`; no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence.
- So these current paper totals are operational context, not OP-anchor evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- If `source_consistency.overall_match=false`, repair the top-card / audit / CSV mismatch before quoting current paper numbers; then use the combined `operator_status_context` + `source_freshness` + `operator_read_gate` route before using the saved right-now card as current-day guidance or evidence.
- For the anchor / paper / watch shortlist specifically, use `CROSS_FAMILY_DECISION.md` and `validate_cross_family_decision.py` as the direct current-paper caveat route; stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green presentation validation are not OP-anchor proof or cross-family promotion evidence.

### Keep this honest
- Do not change rules from this tiny settled sample.
- Do not promote `OP_REFINED_K7` or Phase 8 from this sample.
- Do not substitute `BAQ` for `BEL`.
- Do not discuss real-money scaling until the scorecard-sourced 30 / 20 / 100 usable-settlement gates are actually supported.

---

## Slide 8, Bottom-line conclusion

### Title
Final conclusion

### What to say
- I do **not** think the project proved a stable +47% edge.
- I **do** think it found a narrower, more believable edge worth paper trading.
- The safest current summary is:
  - simple rules beat complex ones,
  - Phase 7 currently looks more trustworthy than Phase 8,
  - walk-forward evidence suggests a smaller but still interesting signal,
  - and live paper-trade validation is the real next test.

### One-line finish
This project moved from "interesting backtest" to "possibly real, but still unproven in live conditions."

---

## Likely questions and short answers

### Q1. Why not lead with the +46.72% ROI number?
Because that is a full-sample Phase 8 result and it is the easiest number to overstate. The more honest walk-forward result is **+22.46%**, and the holdout comparison says the simpler portfolio held up better anyway.

### Q2. Why trust OP more than some higher-ROI rules?
Because `OP_DURABLE_K7` has the best forward evidence mix: **115 holdout races** plus **7/10 walk-forward selections**. A smaller rule with a higher ROI can still be much less trustworthy.

### Q3. Did machine learning help?
Not in a betting-useful way. Without horse-specific features like speed figures or form, the ML pipeline did not beat the simpler odds-gap rules where it mattered.
For the full-data retrain artifact specifically, read `FULL_DATA_RETRAIN_ARTIFACTS.md` and run `python3 validate_full_data_retrain_artifacts.py`; large RMSE / MAE gains remain model-fit diagnostics, not paper-trade evidence.

### Q4. Why is BEL not part of the live plan?
Because it had **0 holdout races in 2024-2025**, and the BAQ substitute lost badly. So BEL may still be a historical edge, but it is dormant, not deployable.

### Q5. What would change your mind?
A decent settled paper-trade sample with usable ROI coverage. If live-style logging comes in far below expectation, I would lower confidence quickly. If it tracks the current range over enough races, confidence improves. Clean scans, open signals, historical replay rows, calibration-only summaries, or another odds-only rerun would not change deployment posture.

---

## Numbers checked against current artifacts

Validated against:
- `frozen_portfolio_eval_summary.csv`
- `walk_forward_validation_folds.csv`
- `forward_evidence_scorecard.csv`
- `phase7_live_rules.json`
- `FULL_DATA_RETRAIN_ARTIFACTS.md`
- `validate_full_data_retrain_artifacts.py`
- `CURRENT_EVIDENCE_SUMMARY.md`
- `current_evidence_summary.json`
- `validate_current_evidence_summary.py`
- `SCORECARD_RANKING_CONTRACT_AUDIT.md`
- `scorecard_ranking_contract_audit.json`
- `validate_scorecard_ranking_contract_audit.py`

Key checked values:
- Phase 7 holdout portfolio: **+38.68% ROI on 175 races**; split: **2024 +0.37% on 109**, **2025 +105.38% on 66**
- Phase 8 holdout portfolio: **+21.45% ROI on 118 races**; split: **2024 +9.50% on 85**, **2025 +50.26% on 33**
- Walk-forward portfolio: **+22.46% ROI, 470 races, 8/10 positive years**
- `OP_DURABLE_K7`: **+22.9% holdout ROI on 115 races**
- `CD_CORE_K8`: **+55.96% holdout ROI on 60 races**
- `OP_REFINED_K7`: **+51.43% holdout ROI on 49 races**
- `CD_REFINED_K9`: **-26.18% holdout ROI on 16 races**
- `AQU_K9`: **-4.28% holdout ROI on 8 races**
- Current paper bridge: source consistency matched; combined operator-status / source-freshness / operator-read-gate route is fresh against the bridge reference date but still goes through operator read-gate routing before right-now instruction or evidence use; primary paper **6/30** first-read and **6/100** broader-review gates; `CD_CORE_K8` has **6** ROI-complete settled rows and `OP_DURABLE_K7` has **0**, so current settled paper context is CD-only and not OP-anchor evidence.
- Current operator read gate: `operator_read_gate.requires_refresh_before_evidence_read=false`; Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence.
- Scorecard audit route: `current_evidence_summary.json.scorecard_audit_route` points to `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks as report-synchronization metadata only.
- Rebuild-order route: `current_evidence_summary.json.rebuild_validation_contract` points to `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` after scorecard/rules/signals/settlement-ledger byte changes and before quoting `CURRENT_EVIDENCE_SUMMARY.*` as provenance/rebuild metadata only.
- Current settlement queue state: `closed`; no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence. Latest primary recommendation context is recommendation-state routing, not a bet-ready ticket or forward-performance proof.
- Direct cross-family current-paper caveat route: `CROSS_FAMILY_DECISION.md` plus `validate_cross_family_decision.py`; stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green presentation validation are not OP-anchor proof or cross-family promotion evidence.
- Full-data retrain caveat route: `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py`; exact retrain/prediction commands and large RMSE / MAE gains are model-fit reproducibility context only, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

---

## If Cole needs the shortest possible recommendation tomorrow

Use `COLE_STATUS_AND_PLAN.md` as the main report, and use this file as the speaking version.

If forced to give a single recommendation:

> Paper trade the Phase 7 core, especially OP and CD, and judge the project by holdout plus walk-forward evidence, not the Phase 8 headline backtest; only change the posture after settled, ROI-complete forward observations clear the explicit gates.
