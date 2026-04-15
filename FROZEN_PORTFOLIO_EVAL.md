# Frozen Portfolio Evaluation

This report evaluates already-defined rule portfolios on a later chronological holdout, using the cached major-track race-level dataset.

## Why this matters

- The old residual-model script (`XGBoost/train_test_residual.py`) uses `train_test_split(..., test_size=0.25, shuffle=True)`, which is a random 75/25 split and not deployment-realistic.
- This report instead checks frozen portfolios on **train = 2010-2023** and **holdout = 2024-2025**.
- This is still not a perfect no-lookahead rule-discovery test, because the rule sets themselves were originally discovered from historical research, but it is materially closer to live deployment than shuffled splits.

## Portfolio Summary

| Portfolio | Full ROI | Train ROI | Holdout ROI | Holdout Profit | Holdout Races | Holdout Hit Rate |
|---|---:|---:|---:|---:|---:|---:|
| Phase 7 live rules | +27.97% | +26.04% | +38.68% | $10,210.61 | 175 | 27.43% |
| Phase 8 frozen rules | +46.72% | +50.71% | +21.45% | $5,585.05 | 118 | 34.75% |

## Holdout by Year

### phase7_live

| Year | Races | Wagered | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|---:|
| 2024 | 109 | $16,770 | $62.10 | +0.37% | 24.77% |
| 2025 | 66 | $9,630 | $10,148.51 | +105.38% | 31.82% |

### phase8_frozen

| Year | Races | Wagered | Profit | ROI | Hit Rate |
|---|---:|---:|---:|---:|---:|
| 2024 | 85 | $18,408 | $1,749.00 | +9.50% | 32.94% |
| 2025 | 33 | $7,632 | $3,836.05 | +50.26% | 39.39% |

## Interpretation

- The **Phase 7 live portfolio** held up best on the later holdout: **+38.68% ROI** on 175 races, for **$10,210.61** profit.
- The **Phase 8 frozen portfolio** also stayed positive on the holdout: **+21.45% ROI** on 118 races, for **$5,585.05** profit.
- The BEL rule has **0 holdout races** in 2024-2025 because the later data uses `BAQ` instead of `BEL`, and the current live-rule mapping explicitly avoids unsupported aliasing.
- That is much more encouraging than the old shuffled ML split, because this test preserves chronology and reports actual betting P&L.
- The main thing still missing is a truly clean no-lookahead discovery loop where rules are searched only on prior years, frozen, then tested on the next period.

## Recommended next evaluation loop

1. Freeze a candidate search space before looking at the test window.
2. Use an expanding yearly walk-forward: train on 2010..Y-1, select rules on train only, test on year Y.
3. Track portfolio-level ROI, profit, races, hit rate, and per-year profitability, not just model R² or full-sample ROI.
4. Keep the most recent 12-24 months as a final untouched holdout until the selection logic is frozen.
5. Promote only rules that survive both train-only selection and frozen-holdout evaluation, then paper trade them live.
