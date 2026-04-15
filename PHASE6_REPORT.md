# Phase 6 Report — BEL Robustness

## Verdict: PLAUSIBLE — some concerns but edge may be real

### Concerns
- SMALL SAMPLE: only 61 races

## Best Strategy
- **Strategy:** `K1W7_BEL_FS11-12_Gap0.22_Fav0.40_fast_midlate`
- **Full ROI:** +149.47%
- **Test ROI (Phase 5 split):** +487.50%
- **Races:** 61
- **Hits / Hit Rate:** 21 / 34.4%
- **Avg Payout:** $869.58

## Statistical Tests
- **Bootstrap 95% CI:** [+15.1%, +304.2%]
- **Bootstrap mean ROI:** +145.4%
- **Permutation p-value (ROI):** 0.0000
- **Permutation p-value (hit rate):** 0.0680
- **Observed hit rate:** 34.4% vs baseline 25.4%
- **Bonferroni alpha:** 0.000009 (5346 tests)
- **Survives Bonferroni:** Yes

## Per-Year Breakdown

| Year | Races | Hits | ROI% | Profit |
|------|-------|------|------|--------|
| 2010 | 9 | 2 | -15.8% | $-171.00 |
| 2011 | 3 | 3 | +345.5% | $+1,243.70 |
| 2012 | 9 | 3 | +52.3% | $+565.00 |
| 2013 | 4 | 1 | -73.5% | $-352.75 |
| 2014 | 4 | 2 | +91.3% | $+438.50 |
| 2015 | 7 | 2 | +241.5% | $+2,028.50 |
| 2016 | 5 | 1 | +2.3% | $+14.00 |
| 2017 | 10 | 1 | +262.5% | $+3,150.50 |
| 2018 | 3 | 2 | -19.5% | $-70.30 |
| 2019 | 2 | 2 | +904.4% | $+2,170.50 |
| 2020 | 1 | 1 | +247.1% | $+296.50 |
| 2022 | 1 | 1 | +1656.7% | $+1,988.00 |
| 2023 | 3 | 0 | -100.0% | $-360.00 |

Positive years: 9/13

## Walk-Forward Out-of-Sample

| Train | Test | Train N | Train ROI | Test N | Test ROI | Test Hits |
|-------|------|---------|-----------|--------|----------|-----------|
| 2010-2014 | 2015 | 29 | +49.5% | 7 | +241.5% | 2 |
| 2011-2015 | 2016 | 27 | +121.1% | 5 | +2.3% | 1 |
| 2012-2016 | 2017 | 29 | +77.4% | 10 | +262.5% | 1 |
| 2013-2017 | 2018 | 30 | +146.6% | 3 | -19.5% | 2 |
| 2014-2018 | 2019 | 29 | +159.8% | 2 | +904.4% | 2 |
| 2015-2019 | 2020 | 27 | +225.1% | 1 | +247.1% | 1 |
| 2016-2020 | 2022 | 21 | +220.7% | 1 | +1656.7% | 1 |
| 2017-2022 | 2023 | 17 | +369.4% | 3 | -100.0% | 0 |

OOS positive windows: 6/8

## Alternative Time Splits
- First half (2010-2015): 36 races, ROI +86.8%
- Second half (2016-2023): 25 races, ROI +239.6%
- Even years: 32 races, ROI +79.7%
- Odd years: 29 races, ROI +226.4%

## Payoff Concentration
- Top-1 hit: 23.8% of total returns
- Top-3 hits: 46.1% of total returns
- ROI without biggest hit: +90.0%
- ROI without top-3 hits: +34.3%

## Broadening Attempts

| Variant | Races | ROI% | Hits | HR% | CI Lo | CI Hi |
|---------|-------|------|------|-----|-------|-------|
| FS 9-14 | 190 | +36.0% | 67 | 35.3% | -12.2% | +92.4% |
| FS 9-13 | 189 | +36.8% | 67 | 35.5% | -12.2% | +93.1% |
| FS 10-14 | 118 | +74.4% | 40 | 33.9% | +2.9% | +166.4% |
| FS 10-15 | 118 | +74.4% | 40 | 33.9% | +2.9% | +166.4% |
| Gap 0.05 | 64 | +140.8% | 23 | 35.9% | +12.9% | +296.8% |
| Gap 0.08 | 64 | +140.8% | 23 | 35.9% | +12.9% | +296.8% |
| Gap 0.00 | 64 | +140.8% | 23 | 35.9% | +12.9% | +296.8% |
| Fav 0.30 | 86 | +113.0% | 25 | 29.1% | +11.3% | +235.8% |
| Fav 0.35 | 81 | +126.1% | 25 | 30.9% | +21.5% | +249.4% |
| Fav 0.00 | 86 | +113.0% | 25 | 29.1% | +11.3% | +235.8% |
| Card midlate | 61 | +149.5% | 21 | 34.4% | +15.1% | +304.2% |
| Card all | 75 | +121.9% | 26 | 34.7% | +13.8% | +261.3% |
| Cond fast | 61 | +149.5% | 21 | 34.4% | +15.1% | +304.2% |
| Cond all | 76 | +109.5% | 25 | 32.9% | +0.2% | +242.5% |
| FS 9-14 + Gap 0.05 | 205 | +36.5% | 75 | 36.6% | -8.3% | +89.8% |
| FS 10-14 + Fav 0.35 | 147 | +73.5% | 47 | 32.0% | +7.2% | +152.1% |
| FS 10-14 + Gap 0.08 + Fav 0.35 | 218 | +39.2% | 64 | 29.4% | -9.7% | +94.9% |
| FS 10-13 + Card midlate | 117 | +75.8% | 40 | 34.2% | +4.7% | +166.2% |
| All relaxed: FS9-14 Gap0.05 Fav0.30 midlate all-cond | 828 | -11.2% | 201 | 24.3% | -28.8% | +8.0% |

### Best Broadened Variant: Gap 0.05
- ROI: +140.8%
- Races: 64
- Bootstrap CI: [+12.9%, +296.8%]
- Permutation p (ROI): 0.0000
- Walk-forward positive: 6/8

## Candidate Rule (Plain English)

At Belmont Park, in races race 5 or later on the card with fast (FT/FM) track conditions, when the field has 11 to 12 runners, the favorite's implied probability is at least 40%, and the probability gap between the favorite and second choice is at least 22%: play a $2 Key-1-with-7 superfecta keying the favorite on top over the next 6 choices by odds. (Cost: $120 per race.)

## Sweep Summary
- Variants tested: 5346
- Met min-race threshold: 4324
- Full ROI > 0: 3322
- Full + Test ROI > 0: 3315

### Top 20 by Full ROI

| Strategy | FS | Gap | FavMin | Cond | Card | Races | Hits | ROI% | HitRate% | AvgPay | TrainROI% | TestROI% | TrainRaces | TestRaces | PosYears |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| K1W7_BEL_FS11-12_Gap0.22_Fav0.40_fast_midlate | 11-12 | 0.22 | 0.4 | fast | midlate | 61 | 21 | 149.47 | 34.43 | 869.58 | 105.65 | 487.5 | 54 | 7 | 9/13 |
| K1W7_BEL_FS11-12_Gap0.20_Fav0.40_fast_midlate | 11-12 | 0.2 | 0.4 | fast | midlate | 62 | 22 | 147.57 | 35.48 | 837.23 | 105.65 | 430.52 | 54 | 8 | 9/13 |
| K1W7_BEL_FS11-12_Gap0.15_Fav0.40_fast_midlate | 11-12 | 0.15 | 0.4 | fast | midlate | 63 | 22 | 143.64 | 34.92 | 837.23 | 101.91 | 430.52 | 55 | 8 | 9/13 |
| K1W7_BEL_FS11-12_Gap0.18_Fav0.40_fast_midlate | 11-12 | 0.18 | 0.4 | fast | midlate | 63 | 22 | 143.64 | 34.92 | 837.23 | 101.91 | 430.52 | 55 | 8 | 9/13 |
| K1W7_BEL_FS11-12_Gap0.05_Fav0.40_fast_midlate | 11-12 | 0.05 | 0.4 | fast | midlate | 64 | 23 | 140.82 | 35.94 | 804.12 | 99.43 | 430.52 | 56 | 8 | 9/13 |
| K1W7_BEL_FS11-12_Gap0.08_Fav0.40_fast_midlate | 11-12 | 0.08 | 0.4 | fast | midlate | 64 | 23 | 140.82 | 35.94 | 804.12 | 99.43 | 430.52 | 56 | 8 | 9/13 |
| K1W7_BEL_FS11-12_Gap0.10_Fav0.40_fast_midlate | 11-12 | 0.1 | 0.4 | fast | midlate | 64 | 23 | 140.82 | 35.94 | 804.12 | 99.43 | 430.52 | 56 | 8 | 9/13 |
| K1W7_BEL_FS11-12_Gap0.12_Fav0.40_fast_midlate | 11-12 | 0.12 | 0.4 | fast | midlate | 64 | 23 | 140.82 | 35.94 | 804.12 | 99.43 | 430.52 | 56 | 8 | 9/13 |
| K1W7_BEL_FS11-12_Gap0.14_Fav0.40_fast_midlate | 11-12 | 0.14 | 0.4 | fast | midlate | 64 | 23 | 140.82 | 35.94 | 804.12 | 99.43 | 430.52 | 56 | 8 | 9/13 |
| K1W7_BEL_FS11-13_Gap0.22_Fav0.40_fast_midlate | 11-13 | 0.22 | 0.4 | fast | midlate | 64 | 21 | 137.78 | 32.81 | 869.58 | 98.31 | 414.06 | 56 | 8 | 9/13 |
| K1W7_BEL_FS11-13_Gap0.20_Fav0.40_fast_midlate | 11-13 | 0.2 | 0.4 | fast | midlate | 65 | 22 | 136.14 | 33.85 | 837.23 | 98.31 | 371.57 | 56 | 9 | 9/13 |
| K1W7_BEL_FS11-13_Gap0.22_Fav0.35_fast_midlate | 11-13 | 0.22 | 0.35 | fast | midlate | 85 | 26 | 134.92 | 30.59 | 921.62 | 117.2 | 242.71 | 73 | 12 | 10/13 |
| K1W7_BEL_FS11-12_Gap0.22_Fav0.37_fast_midlate | 11-12 | 0.22 | 0.37 | fast | midlate | 78 | 25 | 134.81 | 32.05 | 879.15 | 108.87 | 311.25 | 68 | 10 | 10/13 |
| K1W7_BEL_FS11-14_Gap0.22_Fav0.40_fast_midlate | 11-14 | 0.22 | 0.4 | fast | midlate | 65 | 21 | 134.12 | 32.31 | 869.58 | 94.83 | 414.06 | 57 | 8 | 9/13 |
| K1W7_BEL_FS11-13_Gap0.15_Fav0.40_fast_midlate | 11-13 | 0.15 | 0.4 | fast | midlate | 66 | 22 | 132.57 | 33.33 | 837.23 | 94.83 | 371.57 | 57 | 9 | 9/13 |
| K1W7_BEL_FS11-13_Gap0.18_Fav0.40_fast_midlate | 11-13 | 0.18 | 0.4 | fast | midlate | 66 | 22 | 132.57 | 33.33 | 837.23 | 94.83 | 371.57 | 57 | 9 | 9/13 |
| K1W7_BEL_FS11-14_Gap0.20_Fav0.40_fast_midlate | 11-14 | 0.2 | 0.4 | fast | midlate | 66 | 22 | 132.57 | 33.33 | 837.23 | 94.83 | 371.57 | 57 | 9 | 9/13 |
| K1W7_BEL_FS11-14_Gap0.22_Fav0.35_fast_midlate | 11-14 | 0.22 | 0.35 | fast | midlate | 86 | 26 | 132.19 | 30.23 | 921.62 | 114.27 | 242.71 | 74 | 12 | 10/13 |
| K1W7_BEL_FS11-13_Gap0.05_Fav0.40_fast_midlate | 11-13 | 0.05 | 0.4 | fast | midlate | 67 | 23 | 130.03 | 34.33 | 804.12 | 92.55 | 371.57 | 58 | 9 | 9/13 |
| K1W7_BEL_FS11-13_Gap0.08_Fav0.40_fast_midlate | 11-13 | 0.08 | 0.4 | fast | midlate | 67 | 23 | 130.03 | 34.33 | 804.12 | 92.55 | 371.57 | 58 | 9 | 9/13 |
