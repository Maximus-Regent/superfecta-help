# Method Family Decision Card

This note compares the three method families that matter most for honest deployment decisions:
**Harville-ranked probabilities, the current XGBoost correction path, and the selective rule path.**

Short answer:
- **Paper trade the selective rule path**
- **Keep Harville as a benchmark only**
- **Keep XGBoost as research, not as a betting decision engine**

## Comparison Table

| Method Family | Role | Primary Evidence | Sample | Secondary Evidence | Why It Sits Here |
|---|---|---:|---:|---:|---|
| Selective rule path | PAPER NOW | +38.68% (2024-2025 holdout ROI) | 175 | +31.34% (walk-forward ROI) | Only family here with positive current frozen holdout evidence and a live paper-trade path. In the current holdout, this is effectively the OP+CD basket, with OP_DURABLE_K7 still the safest anchor. |
| Harville-ranked probabilities | BENCHMARK ONLY | -24.05% (broad backtest ROI) | 90004 | 41.99% (hit rate) | Large-sample structural benchmark, not a live candidate. The hit rate is high, but the ROI stays deeply negative, which means ranking order by Harville probability alone does not beat takeout. |
| XGBoost residual correction | RESEARCH ONLY | -24.16% (best ML betting ROI (ML-EV>=1.0_H6_FS5-7)) | 16724 | 4.24% (matched-model payout RMSE reduction vs current baseline) | The model can improve payout prediction a bit without creating a betting edge. In the matched downstream test, payout RMSE was reduced by 4.24% and log-ratio RMSE was reduced by 2.16%, but EV winner pass counts barely moved (178 baseline vs 171 enriched on 22244 test winners). |

## Why This Ordering Is Conservative

- **Selective rule path (PAPER NOW)**: Only family here with positive current frozen holdout evidence and a live paper-trade path. In the current holdout, this is effectively the OP+CD basket, with OP_DURABLE_K7 still the safest anchor.
  - Practical note: Frozen 3-rule baseline. BEL contributes zero 2024-2025 races, so the current holdout is effectively the OP+CD legs.
- **Harville-ranked probabilities (BENCHMARK ONLY)**: Large-sample structural benchmark, not a live candidate. The hit rate is high, but the ROI stays deeply negative, which means ranking order by Harville probability alone does not beat takeout.
  - Practical note: Best broad Harville line in BACKTEST_REPORT.md: Harville-Top120.
- **XGBoost residual correction (RESEARCH ONLY)**: The model can improve payout prediction a bit without creating a betting edge. In the matched downstream test, payout RMSE was reduced by 4.24% and log-ratio RMSE was reduced by 2.16%, but EV winner pass counts barely moved (178 baseline vs 171 enriched on 22244 test winners).
  - Practical note: Best ML family line in backtest_summary.csv is still negative (ML-EV>=1.0_H6_FS5-7 = -24.16% on 16724 races).

## Why This Is Not an Apples-to-Apples ROI Contest

- The **selective rule path** has earned the strongest current deployment evidence, because it is the only family here with positive frozen 2024-2025 holdout results plus a live paper-trade workflow.
- The **Harville** and **XGBoost** families are judged by their best honest family-level evidence instead of by a fresh 2024-2025 holdout replay, because they already fail on much larger historical samples and never earned a positive deployment case.
- That asymmetry is acceptable here because the question is practical, not academic: **what should Cole still treat as live-worthy?** The answer is the selective rule path, not the generic ranking/modeling families.

## Bottom Line

If Cole wants one clean method-level hierarchy right now:

1. **Selective rule path**: keep as the only paper-trade family
2. **Harville-ranked probabilities**: keep as a structural benchmark, not a live strategy
3. **XGBoost residual correction**: keep as model research only, because prediction gains have not translated into betting gains

This card is intentionally blunt. It should make it easier to stop revisiting dead-end method families every time a modest model metric improves.

## Validation

- Sources: `compare_main_approaches.csv`, `backtest_summary.csv`, `ab_downstream_comparison_results.json`
- Wrote: `method_family_decision_card.csv`, `METHOD_FAMILY_DECISION.md`
- This card is a read-only synthesis of existing frozen artifacts and comparison outputs
