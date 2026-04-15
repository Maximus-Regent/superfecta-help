# Phase 3 Backtesting Report — Squeeze Remaining Edge

**Generated:** 2026-04-14
**Data:** 90,005 races from 11 major NA tracks, 2010-2025 (excl. 2021)
**Builds on:** Phase 1 (75+ strategies) and Phase 2 (Key1Win variants, filters)
**Phase 3 experiments:** 200+ new strategy/filter combinations

## Executive Summary

Phase 3 found **5 strategies with positive overall ROI**, all based on multi-filter stacking atop the Key1Win-8 structure. The best two:

| Strategy | ROI% | Races | Positive Years | OOS Train | OOS Test |
|----------|------|-------|----------------|-----------|----------|
| CD + FS10-11 + Gap>=0.15 | **+13.1%** | 485 | 8/15 | +5.5% | +23.1% |
| KEE + MidLate + Wet | **+12.8%** | 364 | 6/14 | -2.3% | +23.6% |
| CD + FS10-12 + Gap>=0.15 | **+2.7%** | 712 | 9/15 | -3.9% | +12.2% |
| KEE + BigPool + Wet | **+2.4%** | 474 | 5/14 | -14.3% | +13.7% |
| KEE + Wet | **+1.6%** | 498 | 5/14 | -18.0% | +15.0% |

**Verdict:** These results are promising but NOT conclusive proof of edge. The positive strategies all have small sample sizes (350-700 races over 15 years) and were selected from 200+ filter combinations. Multiple-testing correction would reduce or eliminate statistical significance. However, the **CD+Gap+FS10-11** strategy is the strongest candidate — it is the only strategy positive in both the train (2010-2018) and test (2019-2025) periods, and has a plausible structural explanation.

## Phase 3 Experiments

### 3A: Track x Field-Size Interactions

Tested Key1Win-8 at each track x field-size combination. Key findings:

| Track | FS10-11 ROI | FS10-12 ROI | Races (10-11) |
|-------|-------------|-------------|---------------|
| **CD** | **-5.5%** | **-6.3%** | 1,915 |
| **KEE** | **-7.1%** | **-11.5%** | 1,116 |
| **OP** | -10.7% | -12.1% | 1,996 |
| DMR | -14.3% | -16.5% | 1,419 |
| MTH | -17.3% | -18.0% | 1,167 |
| AQU | -18.0% | -19.6% | 1,328 |
| SA | -20.1% | -18.9% | 2,037 |
| GP | -24.0% | -24.8% | 4,220 |
| SAR | -26.6% | -29.5% | 1,086 |

**Finding:** CD and KEE consistently outperform. Oaklawn Park (OP) is a surprise third. Gulfstream (GP) and Saratoga (SAR) are the worst — high-quality, competitive fields make the favorite less reliable.

### 3B: Seasonality

| Filter | ROI% | Races |
|--------|------|-------|
| Q4 (Oct-Dec) | -20.3% | 13,039 |
| Q2 (Apr-Jun) | -20.6% | 14,284 |
| KEE Spring (Apr-May) | -12.8% | 1,240 |
| KEE Fall (Oct-Nov) | -14.4% | 1,768 |

**Finding:** Q2 and Q4 are marginally better than Q1/Q3. KEE Spring meet outperforms Fall. Seasonality provides weak signal at best.

### 3C: Distance (Sprint vs Route)

| Distance | ROI% | Races |
|----------|------|-------|
| Route mid (8-8.5f) | -21.9% | 24,285 |
| Sprint (<=7f) | -22.6% | 29,020 |
| Route long (>8.5f) | -23.4% | 3,396 |
| Route mid + FavStr | **-17.7%** | 6,305 |

**Finding:** No distance category provides meaningful edge alone. Routes with strong favorites (-17.7%) are slightly better than sprints with strong favorites (-21.9%).

### 3D: Card Position

| Position | ROI% | Races |
|----------|------|-------|
| Mid card (5-8) | -21.4% | 26,301 |
| Sprint (<=7f) | -22.6% | 29,020 |
| Early card (1-4) | -23.2% | 16,757 |
| Late card (9+) | -23.0% | 13,643 |

**Finding:** Mid-card races are marginally best but the difference is small (~2 percentage points).

### 3E: Multi-Filter Stacking (Key Finding)

Tested all 2-filter and 3-filter combinations from a pool of 15 atomic filters. This is where positive ROI strategies emerged.

**Top 2-filter combos (min 200 races):**

| Filters | ROI% | Races | AvgPay |
|---------|------|-------|--------|
| KEE + Wet | +1.6% | 498 | $824 |
| CD + FS10-11 | -5.5% | 1,915 | $878 |
| CD + FS10-12 | -6.3% | 2,857 | $956 |
| KEE + FS10-11 | -7.1% | 1,116 | $892 |
| KEE + Sprint | -7.8% | 1,529 | $750 |

**Top 3-filter combos (min 150 races):**

| Filters | ROI% | Races | AvgPay | Pos Years |
|---------|------|-------|--------|-----------|
| **KEE + Sprint + Wet** | **+17.5%** | 190 | $837 | — |
| **CD + FS10-11 + Gap>=0.15** | **+13.1%** | 485 | $711 | 8/15 |
| **KEE + MidLate + Wet** | **+12.8%** | 364 | $880 | 6/14 |
| CD + FS10-12 + Gap>=0.15 | +2.7% | 712 | $738 | 9/15 |
| KEE + Dirt + Wet | +4.2% | 181 | $683 | — |
| CD + FS10-11 + Dirt | -0.3% | 1,381 | $893 | 7/15 |
| KEE + FS10-11 + Dirt | -1.8% | 774 | $918 | — |
| CD + FS10-12 + Dirt | -1.5% | 2,058 | $985 | 7/15 |

### 3F: Dynamic K

Adjusting K based on favorite strength or probability entropy did NOT improve ROI (-21% to -25%). The static Key1Win-8 remains optimal.

### 3G: Henery Model

Alpha-calibrated Henery combo ordering (tested alpha 0.70 to 1.20) showed minimal ROI variation (-23.8% to -24.4% for Top120). The Harville model (alpha=1.0) is essentially optimal — Henery corrections are too small to matter at this cost level.

### 3H: Favorite Post Position

| Post Position | ROI% | Races |
|---------------|------|-------|
| Outside (9+) | -21.1% | 7,921 |
| Middle (5-8) | -21.4% | 23,447 |
| Inside (1-4) | -23.6% | 25,333 |

**Finding:** Favorites from outside posts slightly outperform those from inside posts, possibly because outside-drawn favorites tend to be more dominant (lower odds) to overcome post-position disadvantage. Not a strong enough signal to build a strategy on.

## Deep Dive: Best Strategy — CD + FS10-11 + Gap>=0.15

**Description:** Key1Win-8 at Churchill Downs only, field size 10-11, with the favorite's implied probability at least 0.15 higher than the second choice.

**Why it might be real:**
1. Churchill Downs has one of the fairest track configurations in North America — no extreme inside/outside bias, which makes favorites more reliable
2. Field size 10-11 is the structural sweet spot: enough runners for decent payouts ($711 avg) but not so many that longshots disrupt the order
3. A large probability gap (>=0.15) indicates a dominant favorite — when the public consensus strongly favors one horse, that signal is particularly reliable at CD's fair track
4. Positive in both train (+5.5%) and test (+23.1%) periods — the only strategy to achieve this

**Why it might be noise:**
1. Only 485 races over 15 years (~32/year)
2. Selected from 200+ filter combinations (multiple testing problem)
3. Year-by-year ROI is extremely volatile: -60.7% to +82.3%
4. Recent hot streak (2022-2025 all positive) could be driving the overall positive
5. A single-year swing of $4,000 can flip annual ROI by 40+ percentage points

**Year-by-Year:**

| Year | ROI% | Races | Hits | Profit |
|------|------|-------|------|--------|
| 2010 | +40.9% | 24 | 11 | +$2,061 |
| 2011 | -19.1% | 25 | 6 | -$1,001 |
| 2012 | +82.3% | 27 | 15 | +$4,668 |
| 2013 | -58.3% | 33 | 10 | -$4,043 |
| 2014 | +43.7% | 32 | 9 | +$2,934 |
| 2015 | -60.7% | 30 | 7 | -$3,821 |
| 2016 | -8.9% | 27 | 8 | -$503 |
| 2017 | +59.3% | 45 | 15 | +$5,604 |
| 2018 | -37.6% | 34 | 7 | -$2,686 |
| 2019 | -13.1% | 52 | 16 | -$1,429 |
| 2020 | -16.3% | 34 | 8 | -$1,167 |
| 2022 | +32.2% | 33 | 11 | +$2,234 |
| 2023 | +55.9% | 29 | 12 | +$3,406 |
| 2024 | +45.6% | 41 | 18 | +$3,930 |
| 2025 | +78.2% | 19 | 9 | +$3,121 |
| **TOTAL** | **+13.1%** | **485** | **162** | **+$13,307** |

## Out-of-Sample Validation

Train: 2010-2018, Test: 2019-2025 (excl. 2021). Only strategies tested in OOS are shown.

| Strategy | Train ROI | Test ROI | Train N | Test N | Delta |
|----------|-----------|----------|---------|--------|-------|
| **CD+FS10-11+Gap15** | **+5.5%** | **+23.1%** | 277 | 208 | +17.6 |
| CD+FS10-12+Gap15 | -3.9% | +12.2% | 418 | 294 | +16.1 |
| KEE+MidLate+Wet | -2.3% | +23.6% | 152 | 212 | +25.9 |
| KEE+Sprint | -20.1% | +11.1% | 924 | 605 | +31.2 |
| FS10-11+FavVStr | -16.9% | +6.1% | 682 | 405 | +23.0 |
| CD+FS10-12 | -11.8% | +1.9% | 1,698 | 1,159 | +13.7 |
| CD+FS10-11 | -8.7% | -0.8% | 1,121 | 794 | +7.9 |
| KEE (all) | -22.1% | +0.3% | 1,881 | 1,163 | +22.4 |
| FS10-11 (all tracks) | -18.4% | -13.4% | 11,558 | 6,309 | +5.0 |

**Key observation:** Nearly every strategy performs BETTER in the test period (2019-2025) than in training (2010-2018). This pattern suggests either (a) a structural shift in the superfecta market favoring chalk bettors in recent years, or (b) small-sample variance. A market structural shift is plausible — as superfecta pools grow and more sophisticated bettors enter, the favorite-driven payout distribution may have shifted to slightly favor systematic approaches.

## Near-Breakeven Strategies (Larger Samples)

These strategies aren't positive but have large enough samples to be more statistically meaningful:

| Strategy | ROI% | Races | Positive Years |
|----------|------|-------|----------------|
| CD + FS10-11 + Dirt | -0.3% | 1,381 | 7/15 |
| KEE + Dirt + Gap15 | -0.6% | 571 | — |
| CD + FS10-12 + Dirt | -1.5% | 2,058 | 7/15 |
| KEE + FS10-11 + Dirt | -1.8% | 774 | — |
| CD + FS10-11 | -5.5% | 1,915 | 6/15 |
| CD + FS10-12 | -6.3% | 2,857 | — |
| KEE + FS10-11 | -7.1% | 1,116 | 6/15 |

**CD + FS10-11 + Dirt at -0.3%** is the closest to breakeven with a meaningful sample size — 1,381 races over 15 years (~92/year). Positive in 7 of 15 years. This is essentially a coin flip, consistent with a true ROI near zero after the ~25% takeout.

## What Phase 3 Proved

### 1. Profitable Strategies Exist on Paper, But Barely
The best strategy (+13.1%) averages only $888/year profit on $6,790/year wagered. At $1 per combo this is trivial; at realistic $2 minimums it doubles to ~$1,776/year on ~$13,580 wagered. This is not a living — it's a hobby with beer money upside.

### 2. CD and KEE Are Structurally Better Tracks for Chalk Betting
These two tracks consistently show lower negative (or slightly positive) ROI across nearly every filter combination. Structural explanation: fairer track configurations and higher-quality fields where form holds up better.

### 3. The Probability Gap Is the Strongest Single Filter
When the favorite's implied probability is >=0.15 above the second choice, Key1Win-8 outcomes improve materially. This makes intuitive sense — a dominant favorite is more likely to win AND the remaining favorites are more likely to fill the remaining places in order.

### 4. Wet Track at KEE Is a Plausible but Thin Signal
KEE + Wet shows +1.6% overall and +15.0% in the test period. Structural explanation: better-bred horses (which dominate at KEE) tend to handle off tracks better, increasing chalk outcomes. But the sample is thin (498 races, many years with <30 races).

### 5. Dynamic K and Henery Calibration Don't Help
Neither adaptive ticket sizing nor alternative probability models improved ROI. The market-implied probabilities are already well-calibrated for ranking purposes.

## Gap to Profitability — Updated Assessment

| Strategy | Current ROI | Races/Year | Gap to Break Even |
|----------|------------|------------|-------------------|
| CD+FS10-11+Gap15 | +13.1% | 32 | Already positive (thinly) |
| CD+FS10-11+Dirt | -0.3% | 92 | ~0.3% (essentially there) |
| CD+FS10-11 | -5.5% | 128 | ~5.5% |
| KEE overall | -13.5% | 203 | ~13.5% |
| All tracks FS10-11 | -16.6% | 1,191 | ~16.6% |

The tradeoff is clear: narrower filters get closer to (or past) breakeven but have fewer qualifying races and higher variance.

## What Would Confirm or Deny Edge

1. **Forward testing (2026 season):** Run the CD+Gap+FS10-11 filter live at Churchill Downs. The spring meet (April-June) should produce ~15-20 qualifying races. Track performance at $1/combo paper bets.

2. **Expanded data:** The all-tracks CSV (531MB) has many more tracks. Testing whether the CD pattern generalizes to similar fair-configuration tracks (e.g., Belmont at the Big A, Woodbine) would strengthen or weaken the case.

3. **Bootrap confidence intervals:** Resample-with-replacement the 485 qualifying races 10,000 times. If the 95% CI for ROI includes zero (likely), the finding is not statistically robust.

4. **Horse-specific features:** Speed figures, trainer/jockey stats, and pace analysis remain the highest-impact data addition. These provide information NOT already in the odds and could push near-breakeven strategies firmly positive.

## Scripts and Files Produced

| File | Purpose |
|------|---------|
| `backtest_phase3.py` | Phase 3 experiment script |
| `backtest_phase3_summary.csv` | All Phase 3 strategy results |
| `backtest_phase3_oos.csv` | Out-of-sample validation results |
| `PHASE3_REPORT.md` | This report |

## Bottom Line

Phase 3 found the first positive-ROI strategies in this dataset, but they rely on narrow filter combinations with small sample sizes. The strongest candidate (**CD + FS10-11 + probability gap >= 0.15**) shows +13.1% ROI over 485 races with both train and test halves positive. This is encouraging but not conclusive.

The honest assessment: **we are at the boundary between noise and signal.** The current data provides enough structure to reduce the ~25% takeout to near zero under the right conditions, but not enough independent information to reliably overcome it. Horse-specific performance data remains the most promising path to confirmed profitability.
