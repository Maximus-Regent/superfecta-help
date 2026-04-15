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

> I tested a superfecta strategy across a large historical dataset and found that a small set of simple favorite-gap rules held up better than the more complicated versions. The best honest forward-style number is about **+22.46% ROI in walk-forward testing**, not the flashy **+46.72%** full-sample Phase 8 result. On the actual 2024-2025 holdout, the simpler **Phase 7 portfolio beat Phase 8, +38.68% vs +21.45%**. So my conclusion is not "mission accomplished." It is "there may be an edge, but it is narrow, track-specific, and needs paper trading before any real-money claim."

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
  - **Phase 7 live portfolio:** **+38.68% ROI**, 175 races, **$10,210.61** profit
  - **Phase 8 frozen portfolio:** **+21.45% ROI**, 118 races, **$5,585.05** profit
- So the more complicated seven-track expansion did **not** beat the simpler three-track portfolio on forward-style data.

### Short line
More rules improved the backtest story, but not the holdout story.

---

## Slide 5, What I would trust right now

### Title
Current deployment ranking

### What to say
- **Anchor:** `OP_DURABLE_K7`
  - Holdout: **+22.9% ROI on 115 races**
  - Walk-forward selected in **7 of 10 folds**
  - Best mix of sample size and forward evidence
- **Paper trade now:** `CD_CORE_K8`
  - Holdout: **+55.96% ROI on 60 races**
  - Good holdout, but less walk-forward support
- **Watch only:** `OP_REFINED_K7`
  - Holdout: **+51.43% ROI on 49 races**
  - Too small and too mixed to trust yet

### Keep this honest
- Small-sample winners are not proof.
- Stronger forward evidence matters more than the highest ROI.

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
- Do **not** use real money yet.
- Do **not** tweak rules off one day or one week of results.
- Goal: log at least **30+ paper-trade observations** before changing anything.
- Treat Phase 8 extras as **shadow or watch-list rules**, not core bets.

### Recommendation line
The bottleneck is no longer code. It is collecting real forward observations.

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

### Q4. Why is BEL not part of the live plan?
Because it had **0 holdout races in 2024-2025**, and the BAQ substitute lost badly. So BEL may still be a historical edge, but it is dormant, not deployable.

### Q5. What would change your mind?
A decent paper-trade sample. If live-style logging comes in far below expectation, I would lower confidence quickly. If it tracks the current range over enough races, confidence improves.

---

## Numbers checked against current artifacts

Validated against:
- `frozen_portfolio_eval_summary.csv`
- `walk_forward_validation_folds.csv`
- `forward_evidence_scorecard.csv`
- `phase7_live_rules.json`

Key checked values:
- Phase 7 holdout portfolio: **+38.68% ROI on 175 races**
- Phase 8 holdout portfolio: **+21.45% ROI on 118 races**
- Walk-forward portfolio: **+22.46% ROI, 470 races, 8/10 positive years**
- `OP_DURABLE_K7`: **+22.9% holdout ROI on 115 races**
- `CD_CORE_K8`: **+55.96% holdout ROI on 60 races**
- `OP_REFINED_K7`: **+51.43% holdout ROI on 49 races**
- `CD_REFINED_K9`: **-26.18% holdout ROI on 16 races**
- `AQU_K9`: **-4.28% holdout ROI on 8 races**

---

## If Cole needs the shortest possible recommendation tomorrow

Use `COLE_STATUS_AND_PLAN.md` as the main report, and use this file as the speaking version.

If forced to give a single recommendation:

> Paper trade the Phase 7 core, especially OP and CD, and judge the project by holdout plus walk-forward evidence, not the Phase 8 headline backtest.
