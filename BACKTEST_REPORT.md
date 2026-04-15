# Superfecta Backtesting Report

**Generated:** 2026-04-13
**Data:** 90,005 races from 11 major NA tracks (CD, GP, SA, AQU, BEL, SAR, KEE, DMR, MTH, OP, BAQ), 2010-2025 (excl. 2021)
**Average superfecta payout:** $2,231.88
**Strategies tested:** 75+

## Executive Summary

**No strategy achieved consistent positive out-of-sample ROI.**

The best strategies reduced losses from ~-33% (random betting) to -13% to -17%, a meaningful improvement driven by structural insights about the superfecta market. However, none reliably overcame the ~25% pari-mutuel takeout.

One high-variance strategy (Key1Win-9 in 12+ fields) showed positive ROI in 5 of 15 years, but this is attributable to payout variance, not genuine edge.

## Best Strategies Found

| Rank | Strategy | ROI% | Hit% | Races | AvgPayout | Cost/Race |
|------|----------|------|------|-------|-----------|-----------|
| 1 | Key1Win-8 at KEE only | -13.5% | 24.2% | 3,044 | $751 | $210 |
| 2 | Key1Win-8 at CD only | -15.7% | 25.4% | 5,810 | $697 | $210 |
| 3 | Key1Win-8 + Muddy + Strong Fav | -15.8% | 37.9% | 2,026 | $467 | $210 |
| 4 | Key1Win-8, field 10-11 | -16.6% | 22.5% | 17,867 | $778 | $210 |
| 5 | Key1Win-9, field 12+ | -16.9% | 20.3% | 7,897 | $1,375 | $336 |
| 6 | Key1Win-8, field 10-12 | -17.7% | 20.8% | 24,991 | $831 | $210 |
| 7 | Key1Win-8 + Strong Fav + Med Field | -17.9% | 35.8% | 7,995 | $482 | $210 |
| 8 | Key1Win-8 + FavProb>=0.50 | -18.2% | 54.3% | 2,305 | $317 | $210 |
| 9 | Key1Win-8 (all races) | -22.3% | 27.0% | 56,701 | $605 | $210 |
| 10 | Harville-Top120 | -24.1% | 42.0% | 90,004 | $217 | $120 |

## Year-by-Year: Key1Win-9 in 12+ Fields (Most Volatile Strategy)

| Year | ROI% | Hits | Races | Profit |
|------|------|------|-------|--------|
| 2010 | -15.3% | 80 | 332 | -$17,060 |
| 2011 | -32.9% | 133 | 687 | -$75,968 |
| 2012 | -21.8% | 116 | 610 | -$44,746 |
| 2013 | -37.5% | 91 | 559 | -$70,359 |
| 2014 | -31.6% | 91 | 504 | -$53,498 |
| **2015** | **+9.0%** | **159** | **687** | **+$20,739** |
| 2016 | -29.5% | 123 | 627 | -$62,042 |
| **2017** | **+6.3%** | **125** | **623** | **+$13,247** |
| **2018** | **+0.9%** | **105** | **516** | **+$1,576** |
| 2019 | -21.1% | 101 | 523 | -$37,140 |
| 2020 | -29.9% | 130 | 652 | -$65,423 |
| **2022** | **+1.2%** | **105** | **461** | **+$1,870** |
| 2023 | -16.6% | 92 | 434 | -$24,265 |
| 2024 | -26.3% | 88 | 451 | -$39,856 |
| **2025** | **+5.5%** | **64** | **231** | **+$4,237** |
| **TOTAL** | **-16.9%** | **1,603** | **7,897** | **-$448,689** |

5 positive years out of 15, but overall -16.9%. The positive years are driven by a few large payouts in a high-variance strategy (avg payout $1,375). This is consistent with random luck in a heavy-tailed distribution, not evidence of a genuine edge.

## Year-by-Year: Key1Win-8 in 10-11 Fields (Most Robust Strategy)

| Year | ROI% | Hits | Races | Profit |
|------|------|------|-------|--------|
| 2010 | -7.0% | 172 | 665 | -$9,738 |
| 2011 | -24.4% | 229 | 1,109 | -$56,746 |
| 2012 | -16.5% | 301 | 1,291 | -$44,730 |
| 2013 | -23.2% | 278 | 1,270 | -$61,889 |
| 2014 | -25.1% | 298 | 1,443 | -$76,069 |
| 2015 | -17.2% | 322 | 1,575 | -$56,929 |
| 2016 | -17.6% | 343 | 1,504 | -$55,620 |
| 2017 | -8.8% | 317 | 1,382 | -$25,637 |
| 2018 | -21.4% | 293 | 1,319 | -$59,215 |
| 2019 | -16.3% | 294 | 1,215 | -$41,682 |
| 2020 | -9.6% | 288 | 1,173 | -$23,719 |
| 2022 | -5.2% | 266 | 1,153 | -$12,503 |
| 2023 | -18.5% | 233 | 1,016 | -$39,422 |
| 2024 | -20.8% | 268 | 1,268 | -$55,463 |
| 2025 | -5.0% | 120 | 484 | -$5,112 |
| **TOTAL** | **-16.6%** | **4,022** | **17,867** | **-$624,475** |

Never positive, but consistently the least negative. Ranges from -5% to -25% per year.

## Methods Tested

### 1. Favorites Box (top-K horses, all permutations)
Box-4 through Box-8. All 4 superfecta finishers must be among the K most-favored horses.
- **Best:** Box-8 at -29.5% ROI (80.7% hit rate, 56,701 races)
- **Finding:** High hit rates but high cost dilutes returns.

### 2. Key Favorite to Win (favorite must finish 1st)
Favorite locked in 1st place, remaining 3 positions from top-K.
- **Best:** Key1Win-8 at -22.3% ROI (27.0% hit rate)
- **Finding:** The strongest structural strategy. By requiring the favorite to win, we dramatically reduce cost while retaining a disproportionate share of wins (favorites win ~30% of races, and when they do, the next-best horses fill the remaining places ~90% of the time).

### 3. Key Top-2 Strategies
Both top favorites must be in 1st+2nd or both in top-4.
- **Best:** Key2-Exacta-Box8 at -22.4%, Key1Win-Key2Place-8 at -22.7%
- **Finding:** Similar to Key1Win but more restrictive. Doesn't improve ROI because the additional constraint reduces hits more than it reduces cost.

### 4. Anti-Chalk (exclude #1 favorite)
Box horses ranked 2nd through K+1.
- **Best:** NoFav-Box7 at -31.9%
- **Finding:** Significantly worse than including the favorite. Confirms that the favorite adds genuine predictive value.

### 5. Harville-Ranked Top-N
Rank all permutations by Harville joint probability, bet the N most probable.
- **Best:** Harville-Top120 at -24.1% (42.0% hit rate)
- **Finding:** Better than equivalent-cost box strategies because it concentrates on the most probable orderings. But still well below breakeven.

### 6. ML Walk-Forward (XGBoost Residual Model)
Retrained XGBoost model each year on prior data. Scored all combos from top-M horses, selected by predicted EV or top-N ranking.
- **Best:** ML-EV>=1.10 at -25.4%, ML-Top10 at -24.3%
- **Finding:** The ML model does NOT improve over simple strategies. It predicts payout corrections (log-ratio) with very low R-squared. The features (odds-based probabilities, field size, pool) are already reflected in market prices and don't contain independent information about which horses will finish in specific positions.

### 7. Conditional Filters
Box-5 or Key1Win-8 restricted by race conditions: favorite strength, field size, surface, track condition, pool size, specific tracks, Harville payout thresholds.
- **Best:** Key1Win-8 at Keeneland at -13.5% (3,044 races)
- **Finding:** Filtering helps but never reaches profitability. The best filters combine strong favorites with medium-to-large field sizes, which maximizes the ratio of payout to cost.

### 8. Field-Size Binned Strategies
Every strategy tested separately for field sizes 5-7, 8-9, 10-11, 12+.
- **Finding:** Optimal field size is 10-11 for Key1Win strategies. Small fields have low payouts; very large fields have low hit rates. 10-11 is the sweet spot.

## Key Findings

### 1. Takeout Dominance
The ~25% superfecta takeout is the overwhelmingly dominant factor. Random betting yields approximately -34% ROI (worse than the raw takeout because of how payouts scale with field size). Even the best strategies only reduce losses to -13% to -17%.

### 2. The Key1Win Structure is Optimal
Keying the betting favorite to WIN (1st place) and boxing the remaining positions with the next-best horses is consistently the best approach. This works because:
- Favorites win ~30% of races (strong baseline signal)
- When the favorite wins, the remaining top horses fill places 2-4 with high probability (~90% for top-8)
- The cost is much lower than a full box (210 vs 1680 for 8 horses)

### 3. The ML Model Adds No Value
The XGBoost residual model, despite being well-tuned and properly walk-forward evaluated, does not identify profitable combos. The model's features (odds-derived probabilities, field metrics, race conditions) are fully reflected in the market. Without **horse-specific performance data** (speed figures, recent form, jockey/trainer statistics, running style), the model cannot identify systematic mispricings.

### 4. Variance Creates Illusions
Some strategies show positive ROI in individual years (Key1Win-9 in 12+ fields had 5 positive years). This is expected with heavy-tailed payout distributions -- a single $15,000 superfecta payout can swing an entire year from -30% to +10%. These outcomes are not evidence of edge; they are the natural consequence of betting on high-variance instruments with sample sizes of ~500 races per year.

### 5. Gap to Profitability
The best strategy (Key1Win-8 in 10-11 fields at -16.6%) needs either:
- **Hit rate improvement**: from 22.5% to 27.0% (+20% relative), OR
- **Average payout improvement**: from $778 to $933 (+20% relative)

A 20% edge over the market is a high bar that likely requires independent information sources not present in the current dataset.

## Does the Evidence Support Profitability?

**No.** The current data and model family has not reached profitability and is unlikely to do so without fundamentally different input data.

The structural insights discovered (Key1Win, optimal field size, favorite strength filters) reduce the takeout drag by approximately 50% (from -33% to -17%), which is valuable for loss minimization but insufficient for profit generation.

## Recommended Next Steps

### Near-Term (Highest Impact)
1. **Add horse-specific features**: Speed figures (Beyer, TimeForm), recent form cycle, class indicators, distance/surface preferences. This is the single most impactful change because it provides information that ISN'T already in the odds.

2. **Add jockey/trainer statistics**: Win rates by category, hot streaks, trainer-jockey combos. These capture real-world edges that the betting public underweights.

3. **Pace analysis features**: Early speed, running style (front-runner vs closer), pace scenario predictions. Superfecta outcomes are heavily influenced by pace dynamics.

### Medium-Term
4. **Pool-aware live strategies**: Use real-time will-pay data from superfecta pools to identify actual overlay situations. The pari-mutuel system creates inefficiencies when the pool distribution diverges from true probabilities.

5. **Conditional probability models**: Replace Harville with the Henery or Stern model, which better account for finishing-position correlations (Harville tends to overestimate the chances of favorites finishing 2nd/3rd/4th).

6. **Ensemble prediction**: Combine multiple model types (gradient boosting, neural net, ordinal regression) for more robust probability estimates.

### Longer-Term
7. **Track-specific models**: The Keeneland result (-13.5%) suggests track-specific patterns may exist. Train separate models per track or track-type.

8. **Multi-race integration**: Use information from earlier races on the same card (track bias, pace bias, jockey patterns) to improve predictions for later races.

## Methodology Notes

- **Walk-forward validation**: All ML strategies use strict temporal splits -- model trained only on prior years, tested on the subsequent year. Simple strategies are evaluated year-by-year for consistency.
- **No leakage**: `official_position` and `position_at_start` are never used as features.
- **Payout basis**: All P&L computed on $1-per-combo flat bet. `actual_payout = payoff_amount * (100 / number_of_tickets_bet)`.
- **No data snooping**: Filter thresholds and field-size bins were not tuned to specific years.
- **Tracks**: 11 major NA tracks only (CD, GP, SA, AQU, BEL, SAR, KEE, DMR, MTH, OP, BAQ).

## Scripts Produced

| File | Purpose |
|------|---------|
| `backtest_superfecta.py` | Main backtesting framework (Phases 1-7) |
| `backtest_phase2.py` | Refined experiments (Key1Win variants, filters, chalk) |
| `backtest_summary.csv` | Phase 1 results table |
| `backtest_phase2_summary.csv` | Phase 2 results table |
| `BACKTEST_REPORT.md` | This report |
