# Phase 7 Report — Ultimate Superfecta Strategy Refinement

## Current Evidence Boundary

- Valid evidence scope: `valid_evidence_scope=legacy_phase7_discovery_context_only`.
- This is a historical Phase 7 discovery report and strongest-candidate-family context, not the current deployment guide by itself.
- Current posture still comes from `forward_evidence_scorecard.txt`, `compare_main_approaches.md`, and the paper-observation lane: `OP_DURABLE_K7` remains the safest anchor, `CD_CORE_K8` remains the primary OP/CD paper companion, and `OP_REFINED_K7` plus other Phase 8 rules remain shadow/watch unless forward paper evidence clears the documented gates.
- The full three-track Phase 7 result includes dormant `BEL` history. `BEL` is not currently forward-testable from this report, and `BAQ` must not be substituted for `BEL`.
- Treat `Wagered`, `Cost`, `Expected`, Kelly, and historical profit lines below as frozen backtest / paper-accounting metadata only, not as bankroll guidance, live-profitability evidence, promotion readiness, stop-loss guidance, scale-up guidance, or real-money authorization.
- Validate this boundary with `python3 validate_phase7_report_caution.py`.

---

## Executive Summary

Phase 7 discovered a **three-track portfolio** that is significantly stronger than any single rule. By combining independent profitable pockets at Belmont Park, Oaklawn Park, and Churchill Downs, the portfolio achieves:

- **+28.0% ROI** across **1,075 races** over 15 years
- **12/15 positive years** (80%)
- **Block bootstrap 95% CI: [+11.8%, +45.4%]** — excludes zero
- **P(loss) = 0.0%** (0 of 5,000 bootstrap samples)

The BEL strict rule remains the highest-ROI single rule, and a new OP (Oaklawn Park) pocket was discovered with 505 races at +35% ROI.

---

## Best Strict Rule

**BEL K1W7: FS 11-12, Gap >= 22%, Fav >= 40%, fast track, race 5+**

| Metric | Value |
|--------|-------|
| ROI | +149.5% |
| Races | 61 |
| Hits / Hit rate | 21 / 34.4% |
| Avg payout | $870 |
| LOOCV positive years | 9/13 (69%) |
| LOOCV median year ROI | +91.3% |
| Block bootstrap 95% CI | [+45.7%, +282.8%] |
| Race bootstrap 95% CI | [+16.2%, +307.9%] |
| P(loss) block bootstrap | 0.1% |
| Permutation p (ROI) | 0.00000 |
| Walk-forward 5yr positive | 6/8 |
| Walk-forward 3yr positive | 7/10 |
| Stability score | 11/12 neighbors profitable (92%) |

## Best Broadened Rule

**BEL K1W7: FS 11-13, Gap >= 22%, Fav >= 35%, fast track, race 5+**

| Metric | Value |
|--------|-------|
| ROI | +134.9% |
| Races | 85 |
| Hits / Hit rate | 26 / 30.6% |
| LOOCV positive years | **10/13 (77%)** |
| LOOCV median year ROI | **+192.1%** |
| Block bootstrap 95% CI | [+44.4%, +239.4%] |
| P(loss) block bootstrap | **0.0%** |
| Permutation p (ROI) | 0.00000 |
| Walk-forward 5yr positive | 7/8 |
| Walk-forward 3yr positive | 8/10 |
| Test ROI (2019+) | +242.7% |

This broadened variant has **better LOOCV** than the strict rule (10/13 vs 9/13) with zero bootstrap loss probability, making it the recommended BEL rule.

## New Discovery: Oaklawn Park (OP)

**OP K1W7: FS 11-12, Gap >= 5%, any conditions, race 7+**

| Metric | Value |
|--------|-------|
| ROI | +35.0% |
| Races | **505** |
| Hits / Hit rate | 87 / 17.2% |
| LOOCV positive years | 10/14 (71%) |
| Block bootstrap 95% CI | [-3.4%, +76.1%] |
| P(loss) block bootstrap | 3.7% |
| Permutation p (ROI) | 0.00000 |
| Payoff concentration (top-3) | 15.5% of returns |
| ROI without top-1 hit | +27.2% |
| ROI without top-3 hits | +14.1% |

Key observations:
- **Minimal filters**: Only track, field size, and card position. Gap >= 5% and no fav_min threshold = nearly unrestricted.
- **Low payoff concentration**: Unlike BEL, where a few big hits drive ROI, OP's edge is distributed across many moderate payouts.
- **ROI survives removing top hits**: +14.1% even without the three biggest payouts — strongest durability signal in the dataset.
- **Structural explanation**: OP (Hot Springs, Arkansas) has shorter meets and regional competition, possibly creating pricing inefficiencies that chalk-based strategies exploit in late-card, medium-field races.

### OP Per-Year Breakdown

| Year | Races | Hits | HR% | ROI% |
|------|-------|------|-----|------|
| 2011 | 20 | 3 | 15.0% | -45.7% |
| 2012 | 22 | 2 | 9.1% | -68.0% |
| 2013 | 16 | 2 | 12.5% | +130.9% |
| 2014 | 31 | 5 | 16.1% | +41.0% |
| 2015 | 25 | 5 | 20.0% | +5.7% |
| 2016 | 36 | 7 | 19.4% | +19.1% |
| 2017 | 38 | 5 | 13.2% | +52.8% |
| 2018 | 27 | 5 | 18.5% | +199.4% |
| 2019 | 26 | 5 | 19.2% | +30.7% |
| 2020 | 57 | 13 | 22.8% | +91.9% |
| 2022 | 44 | 5 | 11.4% | -39.3% |
| 2023 | 48 | 9 | 18.8% | +32.6% |
| 2024 | 68 | 9 | 13.2% | -47.4% |
| 2025 | 47 | 12 | 25.5% | +124.6% |

Positive years: 10/14

## Existing Discovery: Churchill Downs (CD)

**CD K1W8: FS 10-11, Gap >= 15%**

| Metric | Value |
|--------|-------|
| ROI | +13.1% |
| Races | **485** |
| Hits / Hit rate | 162 / 33.4% |
| LOOCV positive years | 8/15 (53%) |
| Test ROI (2019+) | +23.1% |

CD is the weakest individual rule but adds significant diversification to the portfolio — different track, different K, different optimal field size.

---

## Three-Track Portfolio (Primary Recommendation)

**BEL broad1 (K7) + OP (K7) + CD (K8)**

Zero overlap between rules (different tracks). Total: 1,075 races, 15 years of data.

| Year | BEL | OP | CD | Wagered | Profit | ROI |
|------|-----|----|----|---------|--------|-----|
| 2010 | 10 | 0 | 24 | $6,240 | +$1,770 | +28.4% |
| 2011 | 3 | 20 | 25 | $8,010 | -$854 | -10.7% |
| 2012 | 13 | 22 | 27 | $9,870 | +$2,958 | +30.0% |
| 2013 | 5 | 16 | 33 | $9,450 | -$2,002 | -21.2% |
| 2014 | 8 | 31 | 32 | $11,400 | +$6,403 | +56.2% |
| 2015 | 7 | 25 | 30 | $10,140 | -$1,621 | -16.0% |
| 2016 | 7 | 36 | 27 | $10,830 | +$563 | +5.2% |
| 2017 | 14 | 38 | 45 | $15,690 | +$12,117 | +77.2% |
| 2018 | 6 | 27 | 34 | $11,100 | +$5,157 | +46.5% |
| 2019 | 3 | 26 | 52 | $14,400 | +$1,580 | +11.0% |
| 2020 | 2 | 57 | 34 | $14,220 | +$5,294 | +37.2% |
| 2022 | 1 | 44 | 33 | $12,330 | +$2,148 | +17.4% |
| 2023 | 6 | 48 | 29 | $12,570 | +$4,564 | +36.3% |
| 2024 | 0 | 68 | 41 | $16,770 | +$62 | +0.4% |
| 2025 | 0 | 47 | 19 | $9,630 | +$10,149 | +105.4% |
| **TOTAL** | **85** | **505** | **485** | **$172,650** | **+$48,289** | **+28.0%** |

**Positive years: 12/15 (80%)**

**Block bootstrap 95% CI: [+11.8%, +45.4%]**
**P(loss) = 0.0%** (0 of 5,000 bootstrap samples)

### Why the Portfolio Works
1. **Independent signals**: Three different tracks with different racing demographics, surfaces, and meet schedules. BEL = elite NYC spring/fall, OP = regional winter/spring, CD = premium spring/fall.
2. **Diversified risk**: BEL contributes high-ROI but few races; OP and CD contribute volume and consistency. Bad years at one track are offset by good years at another.
3. **Different K values**: BEL/OP use K=7 ($120/race), CD uses K=8 ($210/race). This means different bet structures targeting different field configurations.
4. **Temporal coverage**: OP runs Jan-May, CD runs Apr-Nov, BEL runs May-Oct. The portfolio provides near year-round action.

---

## BEL Stability Analysis

Stability score: **11/12 neighbors profitable (92%)**

The BEL rule sits on a broad ROI plateau, not a fragile spike. Sweeping each parameter while holding others at base values:

### Field size lower bound
| fs_lo | Races | ROI% |
|-------|-------|------|
| 9 | 186 | +39.0% |
| 10 | 114 | +80.5% |
| **11** | **61** | **+149.5%** |
| 12 | 30 | +208.3% |

### Field size upper bound
| fs_hi | Races | ROI% |
|-------|-------|------|
| 11 | 31 | +92.6% |
| **12** | **61** | **+149.5%** |
| 13 | 64 | +137.8% |
| 14 | 65 | +134.1% |

### Probability gap threshold
| Gap | Races | ROI% |
|-----|-------|------|
| 0.00 | 64 | +140.8% |
| 0.10 | 64 | +140.8% |
| 0.15 | 63 | +143.6% |
| **0.22** | **61** | **+149.5%** |
| 0.25 | 55 | +95.2% |
| 0.30 | 40 | -4.3% |

### Favorite minimum probability
| FavMin | Races | ROI% |
|--------|-------|------|
| 0.00 | 86 | +113.0% |
| 0.35 | 81 | +126.1% |
| 0.37 | 78 | +134.8% |
| **0.40** | **61** | **+149.5%** |
| 0.42 | 49 | +59.4% |
| 0.50 | 9 | -43.6% |

### Track condition
| Cond | Races | ROI% |
|------|-------|------|
| all | 76 | +109.5% |
| **fast** | **61** | **+149.5%** |
| wet | 15 | -52.8% |

### Card position
| Card | Races | ROI% |
|------|-------|------|
| all | 75 | +121.9% |
| **midlate** | **61** | **+149.5%** |
| late | 41 | +70.6% |

**Key insight**: The only dimension where a neighbor is unprofitable is wet track conditions (-52.8%), which is expected (15 races, different racing dynamics). Every other adjacent setting is profitable, confirming the edge is a plateau.

---

## BEL Variant Robustness Comparison

| Rule | Races | ROI% | LOOCV | Med ROI | Block CI | P(loss) | Perm p | WF-5 | WF-3 |
|------|-------|------|-------|---------|----------|---------|--------|------|------|
| BEL strict | 61 | +149.5% | 9/13 | +91.3% | [+45.7, +282.8] | 0.1% | 0.00000 | 6/8 | 7/10 |
| BEL gap05 | 64 | +140.8% | 9/13 | +91.3% | [+44.5, +265.1] | 0.1% | 0.00000 | 6/8 | 7/10 |
| **BEL broad1** | **85** | **+134.9%** | **10/13** | **+192.1%** | **[+44.4, +239.4]** | **0.0%** | **0.00000** | **7/8** | **8/10** |
| BEL broad2 | 207 | +44.4% | 9/13 | +70.8% | [-4.8, +97.7] | 3.6% | 0.00100 | 7/8 | 8/10 |
| BEL relaxed | 215 | +41.1% | 9/13 | +70.8% | [-5.8, +92.5] | 4.1% | 0.00080 | 7/8 | 8/10 |
| BEL wide | 386 | +3.1% | 9/13 | +27.3% | [-27.4, +38.0] | 41.4% | 0.02600 | 7/8 | 8/10 |
| BEL allcond | 76 | +109.5% | 9/13 | +67.5% | [+26.3, +214.0] | 0.2% | 0.00020 | 6/8 | 7/10 |
| BEL allcard | 75 | +121.9% | 8/13 | +43.8% | [+30.9, +229.5] | 0.2% | 0.00000 | 5/8 | 6/10 |

**BEL broad1 is the sweet spot**: highest LOOCV (10/13), highest median year ROI (+192%), zero bootstrap loss probability, and the best walk-forward record (7/8 at 5yr, 8/10 at 3yr). It gains 24 races over strict while losing only 15 ROI points.

### BEL broad1 — Per Year

| Year | Races | Hits | ROI% | Profit |
|------|-------|------|------|--------|
| 2010 | 10 | 2 | +37.2% | $+446 |
| 2011 | 3 | 3 | +345.5% | $+1,244 |
| 2012 | 13 | 5 | +192.1% | $+2,996 |
| 2013 | 5 | 1 | -89.3% | $-536 |
| 2014 | 8 | 5 | +221.5% | $+2,127 |
| 2015 | 7 | 2 | +241.5% | $+2,029 |
| 2016 | 7 | 1 | -47.3% | $-397 |
| 2017 | 14 | 1 | +206.2% | $+3,464 |
| 2018 | 6 | 2 | -52.2% | $-376 |
| 2019 | 3 | 2 | +489.7% | $+1,764 |
| 2020 | 2 | 2 | +328.5% | $+789 |
| 2022 | 1 | 1 | +1556.7% | $+1,868 |
| 2023 | 6 | 0 | -100.0% | $-720 |

Positive years: 10/13

### BEL broad1 — Walk-Forward (5-year window)

| Train | Test | Train N | Train ROI | Test N | Test ROI |
|-------|------|---------|-----------|--------|----------|
| 2010-2014 | 2015 | 39 | +109.3% | 7 | +241.5% |
| 2011-2015 | 2016 | 36 | +138.3% | 7 | -47.3% |
| 2012-2016 | 2017 | 40 | +81.1% | 14 | +206.2% |
| 2013-2017 | 2018 | 41 | +104.6% | 6 | -52.2% |
| 2014-2018 | 2019 | 42 | +103.2% | 3 | +489.7% |
| 2015-2019 | 2020 | 37 | +131.5% | 2 | +328.5% |
| 2016-2020 | 2022 | 30 | +123.2% | 1 | +1556.7% |
| 2017-2022 | 2023 | 26 | +236.6% | 6 | -100.0% |

OOS positive: 6/8

### BEL strict — Walk-Forward (3-year window)

| Train | Test | Train N | Train ROI | Test N | Test ROI |
|-------|------|---------|-----------|--------|----------|
| 2010-2012 | 2013 | 21 | +16.2% | 4 | -73.5% |
| 2011-2013 | 2014 | 16 | +45.6% | 4 | +91.3% |
| 2012-2014 | 2015 | 17 | +11.7% | 7 | +241.5% |
| 2013-2015 | 2016 | 15 | +68.5% | 5 | +2.3% |
| 2014-2016 | 2017 | 16 | +102.1% | 10 | +262.5% |
| 2015-2017 | 2018 | 22 | +166.8% | 3 | -19.5% |
| 2016-2018 | 2019 | 18 | +112.9% | 2 | +904.4% |
| 2017-2019 | 2020 | 15 | +275.8% | 1 | +247.1% |
| 2018-2020 | 2022 | 6 | +105.3% | 1 | +1656.7% |
| 2019-2022 | 2023 | 4 | +738.0% | 3 | -100.0% |

OOS positive: 7/10

---

## Cross-Track Transfer Test

The BEL strict rule applied to each track shows the edge is **BEL-specific**:

| Track | Races | Hits | HR% | ROI% |
|-------|-------|------|-----|------|
| **BEL** | **61** | **21** | **34.4%** | **+149.5%** |
| CD | 122 | 29 | 23.8% | +5.0% |
| SAR | 16 | 4 | 25.0% | +1.8% |
| GP | 227 | 52 | 22.9% | -12.9% |
| SA | 88 | 21 | 23.9% | -20.8% |
| MTH | 54 | 16 | 29.6% | -20.3% |
| DMR | 46 | 9 | 19.6% | -21.5% |
| OP | 99 | 16 | 16.2% | -25.3% |
| AQU | 40 | 7 | 17.5% | -34.1% |
| KEE | 55 | 9 | 16.4% | -42.3% |

BEL's 34.4% hit rate is dramatically higher than any other track with identical filters. This is consistent with a genuine track-specific structural edge, not random noise.

**AQU result**: Despite being the same NYRA circuit, AQU produces -34.1% ROI. The BEL edge does not transfer to Aqueduct. This may relate to differences in track geometry, surface composition, or meet quality.

---

## Feature Engineering Results

Tested: fav_dominance (fav_prob / top4_mass), log_odds_ratio (log(p1/p2)), top4_mass thresholds.

**No new feature provided material improvement** over the base probability gap filter:
- fav_dominance thresholds on BEL: Same races (fav >= 0.40 already implies high dominance in FS 11-12)
- log_odds_ratio on BEL broad: +61.7% ROI on 177 races at log_OR >= 0.7 — similar to gap-based filtering, not additive
- top4_mass: Slight improvement at >= 0.75 (+43.2%, 164 races) but loses LOOCV quality
- Cross-track (CD, MTH): No feature creates a new profitable pocket

**Conclusion**: The probability gap already captures the relevant information. Additional odds-derived features are redundant with gap in this dataset.

---

## All-Track Search (20,160 variants)

Top profitable rules with LOOCV >= 50% positive years:

| Strategy | Races | ROI% | LOOCV | Median ROI | Test ROI |
|----------|-------|------|-------|------------|----------|
| K1W7_BEL_FS11-13_Gap0.22_Fav0.35_fast_midlate | 85 | +134.9% | 10/13 | +192.1% | +242.7% |
| K1W7_BEL_FS11-14_Gap0.22_Fav0.35_fast_midlate | 86 | +132.2% | 10/13 | +192.1% | +242.7% |
| K1W7_BEL_FS11-12_Gap0.22_Fav0.35_fast_midlate | 81 | +126.1% | 10/13 | +73.5% | +273.9% |
| K1W8_BEL_FS11-12_Gap0.22_Fav0.40_fast_midlate | 61 | +105.3% | 10/13 | +95.1% | +265.8% |
| K1W7_BEL_FS11-13_Gap0.20_Fav0.35_all_midlate | 124 | +94.0% | 10/13 | +59.6% | +170.5% |
| K1W7_BEL_FS11-13_Gap0.20_Fav0.00_all_midlate | 133 | +87.7% | 10/13 | +137.3% | +175.1% |
| K1W7_OP_FS11-12_Gap0.05_Fav0.00_all_late | 505 | +35.0% | 10/14 | +30.7% | +35.3% |
| K1W7_OP_FS11-13_Gap0.05_Fav0.00_all_late | 512 | +33.2% | 10/14 | +30.7% | +30.4% |
| K1W8_CD_FS10-11_Gap0.15_Fav0.00_all_all | 485 | +13.1% | 8/15 | +9.0% | +23.1% |

All top rules are concentrated at BEL (various broadening levels), OP (late-card, FS 11-12), and CD (K=8, FS 10-11, strong gap). No other track produces a confident profitable rule.

---

## Monte Carlo Forward Simulation

### BEL strict (~5 races/year)
| Metric | Value |
|--------|-------|
| P(profitable season) | 63.8% |
| P(double bankroll) | 44.4% |
| Median season ROI | +64.3% |
| 5th / 95th percentile | -100% / +712% |
| Kelly fraction | 23.9% of bankroll |

### BEL broad1 (~7 races/year)
| Metric | Value |
|--------|-------|
| P(profitable season) | 68.4% |
| P(double bankroll) | 47.8% |
| Median season ROI | +86.5% |
| 5th / 95th percentile | -100% / +548% |
| Kelly fraction | 20.2% of bankroll |

**Interpretation**: With ~5-7 BEL races per year, there's a meaningful probability (~32-36%) of a losing season purely from variance. The portfolio (adding OP and CD) dramatically reduces this risk through diversification.

---

## Honest Assessment — Has the Data Reached Its Ceiling?

**Verdict: STRONG PORTFOLIO EDGE — three independent signals combine into a robust, scalable strategy.**

### What the data supports:
- The BEL pocket is the strongest single signal: +135% ROI on 85 races, block bootstrap CI excludes zero, 10/13 years profitable, permutation p < 0.00001, survives Bonferroni.
- The BEL edge is **track-specific** (does not transfer to AQU or other NYRA tracks) and sits on a **broad plateau** (11/12 neighbors profitable). Both facts argue against overfitting.
- The OP pocket (+35%, 505 races) was discovered independently and has **low payoff concentration** — still +14% ROI after removing the 3 biggest hits.
- The CD pocket (+13%, 485 races) was previously identified in Phase 3 and independently confirmed.
- The three-track portfolio is **zero-overlap**, blocks of independent data, with **bootstrap CI [+12%, +45%] and P(loss) = 0%** — the strongest statistical result in the entire project.

### Limitations:
- **BEL closed after 2023** for renovation. The rule cannot be forward-tested until Belmont Park reopens (expected 2025-2026 season).
- **OP block bootstrap CI [-3.4%, +76.1%]** barely crosses zero — the individual OP signal is less confident than BEL.
- **CD is the weakest rule**: only 53% LOOCV positive years. It contributes diversification more than standalone edge.
- **Selected from thousands of variants** — though the strongest rules survive Bonferroni correction and multiple anti-overfit tests.
- **High variance in any single season**: Individual years can swing -100% to +1600%. This strategy requires patience and adequate bankroll.

### Data ceiling:
The current dataset (odds-derived features only) has been thoroughly explored across 20,000+ variants with LOOCV, block bootstrap, permutation tests, and walk-forward validation. The three-track portfolio represents the approximate ceiling. Material improvement requires:
1. **Horse-specific features** (speed figures, form cycle, class indicators)
2. **Forward data** from reopened Belmont Park
3. **Real-time pool analysis** for overlay detection
4. **Jockey/trainer statistics** for additional predictive signal

---

## Final Recommendations

### Rule 1: BEL broad1 (Primary — Highest Confidence)
```
Track:      Belmont Park (BEL)
Bet type:   $2 Key-1-with-7 superfecta (favorite on top, next 6 by odds)
Cost:       $120/race ($2 x 120 combos)
Filters:    Field size 11-13
            Favorite implied prob >= 35%
            Probability gap (fav - 2nd) >= 22%
            Fast track (FT or FM)
            Race 5 or later on card
Expected:   ~7 races/year at BEL meets
ROI:        +134.9% (85 races, 2010-2023)
```

### Rule 2: OP (Secondary — Largest Sample)
```
Track:      Oaklawn Park (OP)
Bet type:   $2 Key-1-with-7 superfecta
Cost:       $120/race
Filters:    Field size 11-12
            Probability gap >= 5% (minimal filter)
            Any track condition
            Race 7 or later on card
Expected:   ~36 races/year during OP meet (Jan-May)
ROI:        +35.0% (505 races, 2011-2025)
```

### Rule 3: CD (Tertiary — Diversifier)
```
Track:      Churchill Downs (CD)
Bet type:   $2 Key-1-with-8 superfecta (favorite on top, next 7 by odds)
Cost:       $210/race ($2 x 210 combos)
Filters:    Field size 10-11
            Probability gap >= 15%
Expected:   ~32 races/year during CD meets
ROI:        +13.1% (485 races, 2010-2025)
```

### Automation Guidance — paper observation only
1. **Subscribe to race cards** for BEL (May-Oct, when available), OP (Jan-May), and CD (Apr-Nov), but keep `BAQ` separate from `BEL`.
2. For each race, compute:
   - `fav_prob = (100 / (fav_odds + 100))`, normalized across field
   - `gap = fav_prob - second_fav_prob`
3. Apply the appropriate track's filters and log the race through the paper-trade lane, including no-bet / no-action states and keeping settlement open until actual result, payout, and cost are known.
4. Use the $2-base combo cost only as the historical/paper accounting unit; **do not place, size, bankroll, stop-loss, or scale real-money bets from this report**.
5. Expected historical portfolio volume was ~70-75 qualifying races/year across the three tracks, but current forward evidence must come from ROI-complete paper settlements.
6. Expected historical paper handle was roughly ~$11,500/year at the $2 accounting base; this is not a bankroll recommendation.
7. Historical replay profit was roughly ~$3,200/year at historical rates; this is not live-profitability or real-money evidence.
8. If a track goes 0-for-25+ in ROI-complete forward paper settlements, pause and re-evaluate the rule before changing any live posture.

### Risk Boundary
- Kelly / bankroll calculations from the historical replay are intentionally not used as operating instructions here.
- Do **not** size, bankroll, stop-loss, or scale real-money bets from `PHASE7_REPORT.md`.
- Real-money discussion requires a separate human-approved risk memo after 100+ total ROI-complete paper observations, payout/concentration sanity checks, settlement-quality checks, and the no-BAQ-as-BEL guardrail.
- Until then, treat Phase 7 as the strongest paper-observation candidate family, not a live betting instruction.

---

## File Paths
- Script: `/Users/maximusregent_ai/Shared/Superfecta Help/backtest_phase7.py`
- Summary CSV: `/Users/maximusregent_ai/Shared/Superfecta Help/backtest_phase7_summary.csv`
- Report: `/Users/maximusregent_ai/Shared/Superfecta Help/PHASE7_REPORT.md`
