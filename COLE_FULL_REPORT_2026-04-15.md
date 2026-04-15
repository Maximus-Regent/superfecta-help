# Cole Superfecta Full Report — 2026-04-15

## Executive summary

Yes, we have improved it enough to justify a full report.

The biggest honest change is not fake headline inflation, it is that the project is now:
- more defensible
- more operational
- easier to explain
- less likely to confuse research with something actually ready to run

### Bottom line
- **Best validated selector improvement:** walk-forward ROI improved from **+22.46%** to **+30.42%** by switching to sqrt-dampened selector scoring.
- **Best current live paper baseline:** still the **Phase 7 / active OP+CD basket**, not the Phase 8 expansion.
- **Best current holdout result:** **+38.68% ROI on 175 races** for the Phase 7 live portfolio.
- **Phase 8 status:** still useful, but it stays **shadow-only**, because its 2024-2025 holdout is weaker at **+21.45% on 118 races**.
- **Method-family verdict:** the **selective rule path** is still the only family that deserves paper-trade treatment. **Harville = benchmark only. XGBoost = research only.**
- **Live/demo status:** the live model stack and demo lane now work on real available cards today, but there has **not** been an honest **+30% EV** live opportunity yet.

## How much we improved it so far

## 1) Honest validation improved materially

This is the cleanest numeric improvement we can defend.

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
- we did **not** justify Phase 8 as the new live default
- we did **not** solve everything with ML

## 2) Portfolio decisions got much clearer

Earlier, the repo had a lot of evidence but too much of it was scattered.
Now the main decision hierarchy is much cleaner:

- **Phase 7 live portfolio** = primary paper baseline
- **Phase 8 frozen portfolio** = shadow challenger only
- **Train-only yearly selector** = honesty benchmark, not the operating recipe

Why:
- Phase 7 still wins on the most important current comparison
- **Phase 7 holdout:** **+38.68% ROI on 175 races**
- **Phase 8 holdout:** **+21.45% ROI on 118 races**

So the project improved not by inventing a prettier story, but by making the deployment story harder to bullshit.

## 3) Rule hierarchy is now easier to defend

The strongest current rule ordering is clearer now:

- **OP_DURABLE_K7** = safest anchor
- **CD_CORE_K8** = paper-trade worthy, but not enough to displace the anchor
- **OP_REFINED_K7** = interesting challenger, still watch-level due to sample size / consistency concerns

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

That last part matters a lot.
A quiet day can now be read honestly as one of these:
- no active-basket tracks were racing
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
- choose the next or best-live candidate
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

1. **The selector got better in a validated way**
   - +22.46% to +30.42% walk-forward
2. **The project is much more operational**
   - daily paper-trade workflow is now clearer and more runnable
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

> The project improved meaningfully, but mainly through better validation, better decision hygiene, and much stronger operational tooling, not through some fake overnight discovery. The best validated numeric gain was the walk-forward selector improvement from +22.46% to +30.42%. The best current deployment stance is still conservative: paper trade the selective rule path, keep Phase 7 as the primary baseline, keep Phase 8 as shadow-only, and treat Harville/XGBoost as benchmark or research rather than live betting engines.

## Short answer to “how much did we improve it?”

In plain English:

- we turned it from a **strong but messy research repo** into something much closer to a **defensible report + operational paper-trade system**
- the biggest clean numeric gain was **+7.96 percentage points** in honest walk-forward ROI
- the biggest practical gain was making the daily paper-trade and live-demo paths actually usable and interpretable
- the biggest honesty win was proving that some “improvements” were **not** worth promoting

That is real progress.
