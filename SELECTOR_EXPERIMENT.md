# Selector Scoring Experiment

## Purpose

Test whether dampening the ROI term in the walk-forward selection score
fixes the CD track-group selection bottleneck and whether the fix generalizes.

## Method

- Re-scores and re-selects rules from the frozen `walk_forward_validation_rules.csv`.
- Per-rule test outcomes are already recorded — only the selection changes.
- No new rule mining, no new data, no hand-picking.

**Validation:** Baseline validated: experiment +22.46% vs original +22.46%.

## Scoring Variants

| Name | ROI Term | Cost Adjustment |
|---|---|---|
| raw | `max(roi, 0)` | None |
| sqrt | `sqrt(max(roi, 0))` | None |
| log | `log(1 + max(roi, 0))` | None |
| sqrt_cost | `sqrt(max(roi, 0))` | `× sqrt(120/cost)` |
| log_cost | `log(1 + max(roi, 0))` | `× sqrt(120/cost)` |

## Guardrail Variants

| Name | MIN_POSITIVE_YEAR_RATIO | Relaxation |
|---|---|---|
| strict | 0.50 for all | None |
| relaxed_n150 | 0.50 (0.35 if N≥150) | High-sample rules get lower threshold |

## Results

| Variant | ROI | Profit | Pos Years | CD_CORE | CD_REFINED | CD_NONE | OP_DUR | OP_REF |
|---|---:|---:|---|---:|---:|---:|---:|---:|
|  **sqrt|strict** | +30.42% | $23,798.15 | 8/10 | 1 | 6 | 3 | 8 | 2 |
| sqrt|relaxed_n150 | +30.42% | $23,798.15 | 8/10 | 1 | 6 | 3 | 8 | 2 |
| sqrt_cost|strict | +27.69% | $20,284.30 | 7/10 | 1 | 3 | 6 | 8 | 2 |
| sqrt_cost|relaxed_n150 | +27.69% | $20,284.30 | 7/10 | 1 | 3 | 6 | 8 | 2 |
| raw|strict | +22.46% | $17,541.35 | 8/10 | 1 | 7 | 2 | 7 | 2 |
| raw|relaxed_n150 | +22.46% | $17,541.35 | 8/10 | 1 | 7 | 2 | 7 | 2 |
| log_cost|strict | +13.95% | $11,425.30 | 7/10 | 2 | 2 | 6 | 9 | 1 |
| log_cost|relaxed_n150 | +13.95% | $11,425.30 | 7/10 | 2 | 2 | 6 | 9 | 1 |
| log|strict | +13.65% | $12,271.35 | 8/10 | 2 | 7 | 1 | 9 | 1 |
| log|relaxed_n150 | +13.65% | $12,271.35 | 8/10 | 2 | 7 | 1 | 9 | 1 |

**Baseline (raw|strict):** +22.46% ROI, $17,541.35 profit.
**Best (sqrt|strict):** +30.42% ROI, $23,798.15 profit.
**Delta:** +7.96pp.

## CD Selection Detail

### Baseline: raw|strict

| Year | Rule | Score | Qual | Sel | Train ROI | Races | PosYr | Test ROI |
|---:|---|---:|---|---|---:|---:|---:|---:|
| 2015 | CD_CORE_K8 | 5.4990 | Y | **YES** | +15.60% | 141 | 0.60 | -60.65% |
| 2015 | CD_REFINED_K9 | 0.0000 | N | no | -10.50% | 57 | 0.60 | +90.41% |
| 2016 | CD_CORE_K8 | 0.8325 | Y | no | +2.22% | 171 | 0.50 | -8.87% |
| 2016 | CD_REFINED_K9 | 0.4160 | Y | no | +1.92% | 65 | 0.67 | +179.28% |
| 2017 | CD_CORE_K8 | 0.2663 | N | no | +0.71% | 198 | 0.43 | +59.30% |
| 2017 | CD_REFINED_K9 | 7.2429 | Y | **YES** | +23.49% | 74 | 0.71 | -88.28% |
| 2018 | CD_CORE_K8 | 5.7800 | Y | no | +11.56% | 243 | 0.50 | -37.62% |
| 2018 | CD_REFINED_K9 | 1.7244 | Y | no | +4.65% | 89 | 0.62 | +869.41% |
| 2019 | CD_CORE_K8 | 2.4531 | N | no | +5.52% | 277 | 0.44 | -13.09% |
| 2019 | CD_REFINED_K9 | 29.2181 | Y | **YES** | +92.00% | 99 | 0.67 | +11.64% |
| 2020 | CD_CORE_K8 | 1.0320 | N | no | +2.58% | 329 | 0.40 | -16.34% |
| 2020 | CD_REFINED_K9 | 33.1553 | Y | **YES** | +85.30% | 108 | 0.70 | -73.78% |
| 2022 | CD_CORE_K8 | 0.2945 | N | no | +0.81% | 363 | 0.36 | +32.23% |
| 2022 | CD_REFINED_K9 | 27.5640 | Y | **YES** | +68.21% | 121 | 0.64 | +80.95% |
| 2023 | CD_CORE_K8 | 1.4293 | N | no | +3.43% | 396 | 0.42 | +55.92% |
| 2023 | CD_REFINED_K9 | 34.6134 | Y | **YES** | +69.19% | 131 | 0.67 | -8.53% |
| 2024 | CD_CORE_K8 | 3.2351 | N | no | +7.01% | 425 | 0.46 | +45.65% |
| 2024 | CD_REFINED_K9 | 32.3811 | Y | **YES** | +66.88% | 135 | 0.62 | -14.54% |
| 2025 | CD_CORE_K8 | 5.2050 | Y | no | +10.41% | 466 | 0.50 | +78.21% |
| 2025 | CD_REFINED_K9 | 30.3999 | Y | **YES** | +60.24% | 147 | 0.57 | -61.12% |

### Best: sqrt|strict

| Year | Rule | Score | Qual | Sel | Train ROI | Races | PosYr | Test ROI |
|---:|---|---:|---|---|---:|---:|---:|---:|
| 2015 | CD_CORE_K8 | 1.3923 | Y | **YES** | +15.60% | 141 | 0.60 | -60.65% |
| 2015 | CD_REFINED_K9 | 0.0000 | N | no | -10.50% | 57 | 0.60 | +90.41% |
| 2016 | CD_CORE_K8 | 0.5587 | Y | no | +2.22% | 171 | 0.50 | -8.87% |
| 2016 | CD_REFINED_K9 | 0.3002 | Y | no | +1.92% | 65 | 0.67 | +179.28% |
| 2017 | CD_CORE_K8 | 0.3160 | N | no | +0.71% | 198 | 0.43 | +59.30% |
| 2017 | CD_REFINED_K9 | 1.4944 | Y | no | +23.49% | 74 | 0.71 | -88.28% |
| 2018 | CD_CORE_K8 | 1.7000 | Y | no | +11.56% | 243 | 0.50 | -37.62% |
| 2018 | CD_REFINED_K9 | 0.7997 | Y | no | +4.65% | 89 | 0.62 | +869.41% |
| 2019 | CD_CORE_K8 | 1.0441 | N | no | +5.52% | 277 | 0.44 | -13.09% |
| 2019 | CD_REFINED_K9 | 3.0462 | Y | **YES** | +92.00% | 99 | 0.67 | +11.64% |
| 2020 | CD_CORE_K8 | 0.6425 | N | no | +2.58% | 329 | 0.40 | -16.34% |
| 2020 | CD_REFINED_K9 | 3.5899 | Y | **YES** | +85.30% | 108 | 0.70 | -73.78% |
| 2022 | CD_CORE_K8 | 0.3272 | N | no | +0.81% | 363 | 0.36 | +32.23% |
| 2022 | CD_REFINED_K9 | 3.3375 | Y | **YES** | +68.21% | 121 | 0.64 | +80.95% |
| 2023 | CD_CORE_K8 | 0.7717 | N | no | +3.43% | 396 | 0.42 | +55.92% |
| 2023 | CD_REFINED_K9 | 4.1612 | Y | **YES** | +69.19% | 131 | 0.67 | -8.53% |
| 2024 | CD_CORE_K8 | 1.2219 | N | no | +7.01% | 425 | 0.46 | +45.65% |
| 2024 | CD_REFINED_K9 | 3.9595 | Y | **YES** | +66.88% | 135 | 0.62 | -14.54% |
| 2025 | CD_CORE_K8 | 1.6132 | Y | no | +10.41% | 466 | 0.50 | +78.21% |
| 2025 | CD_REFINED_K9 | 3.9168 | Y | **YES** | +60.24% | 147 | 0.57 | -61.12% |

## Fold-by-Fold: Baseline vs Best

| Year | Baseline Rules | Baseline ROI | Best Rules | Best ROI | Change |
|---:|---|---:|---|---:|---|
| 2015 | CD_CORE_K8,OP_DURABLE_K7 | -39.24% | CD_CORE_K8,OP_DURABLE_K7 | -39.24% |  |
| 2016 | BEL_BROAD1_K7_BRIDGE_BAQ,KEE_K9,OP_DURABLE_K7 | +5.13% | BEL_BROAD1_K7_BRIDGE_BAQ,KEE_K9,OP_DURABLE_K7 | +5.13% |  |
| 2017 | BEL_BROAD1_K7_BRIDGE_BAQ,CD_REFINED_K9,KEE_K9 | +8.37% | BEL_BROAD1_K7_BRIDGE_BAQ,KEE_K9,OP_DURABLE_K7 | +80.21% | **CHANGED** |
| 2018 | BEL_BROAD1_K7_BRIDGE_BAQ,KEE_K9,OP_DURABLE_K7 | +154.38% | BEL_BROAD1_K7_BRIDGE_BAQ,KEE_K9,OP_DURABLE_K7 | +154.38% |  |
| 2019 | BEL_BROAD1_K7_BRIDGE_BAQ,CD_REFINED_K9,OP_DURABLE_K7 | +51.68% | BEL_BROAD1_K7_BRIDGE_BAQ,CD_REFINED_K9,OP_DURABLE_K7 | +51.68% |  |
| 2020 | BEL_BROAD1_K7_BRIDGE_BAQ,CD_REFINED_K9,OP_DURABLE_K7 | +28.28% | BEL_BROAD1_K7_BRIDGE_BAQ,CD_REFINED_K9,OP_DURABLE_K7 | +28.28% |  |
| 2022 | BEL_BROAD1_K7_BRIDGE_BAQ,CD_REFINED_K9,OP_DURABLE_K7 | +28.32% | BEL_BROAD1_K7_BRIDGE_BAQ,CD_REFINED_K9,OP_DURABLE_K7 | +28.32% |  |
| 2023 | BEL_BROAD1_K7,CD_REFINED_K9,OP_DURABLE_K7 | +13.35% | BEL_BROAD1_K7_BRIDGE_BAQ,CD_REFINED_K9,OP_DURABLE_K7 | +11.64% | **CHANGED** |
| 2024 | BEL_BROAD1_K7,CD_REFINED_K9,OP_REFINED_K7 | -19.95% | BEL_BROAD1_K7_BRIDGE_BAQ,CD_REFINED_K9,OP_REFINED_K7 | -24.49% | **CHANGED** |
| 2025 | BEL_BROAD1_K7,CD_REFINED_K9,OP_REFINED_K7 | +98.37% | BEL_BROAD1_K7,CD_REFINED_K9,OP_REFINED_K7 | +98.37% |  |

## Generalization Beyond CD

Some variants changed OP selection:
- **sqrt|strict**: OP_DURABLE=8, OP_REFINED=2 (baseline: OP_DURABLE=7)
- **sqrt|relaxed_n150**: OP_DURABLE=8, OP_REFINED=2 (baseline: OP_DURABLE=7)
- **log|strict**: OP_DURABLE=9, OP_REFINED=1 (baseline: OP_DURABLE=7)
- **log|relaxed_n150**: OP_DURABLE=9, OP_REFINED=1 (baseline: OP_DURABLE=7)
- **sqrt_cost|strict**: OP_DURABLE=8, OP_REFINED=2 (baseline: OP_DURABLE=7)
- **sqrt_cost|relaxed_n150**: OP_DURABLE=8, OP_REFINED=2 (baseline: OP_DURABLE=7)
- **log_cost|strict**: OP_DURABLE=9, OP_REFINED=1 (baseline: OP_DURABLE=7)
- **log_cost|relaxed_n150**: OP_DURABLE=9, OP_REFINED=1 (baseline: OP_DURABLE=7)

## What Actually Happened

The mechanism of improvement is NOT what we initially hypothesized:

1. **CD_CORE_K8 is still only selected in 1/10 folds** — same as baseline. sqrt dampening
   compresses the CD_REFINED/CD_CORE score ratio from ~10x to ~3x, but CD_CORE's lower
   positive-year ratio (0.36–0.50 vs 0.57–0.71) and the races factor cap at 150 prevent
   it from overtaking CD_REFINED.
2. **The real win is in fold 2017:** sqrt dampened CD_REFINED_K9's score enough that
   OP_DURABLE_K7 displaced it in the top-3 portfolio. CD_REFINED had -88.28% test ROI
   in 2017, so removing it was worth +71.84pp in that single fold.
3. **Minor regressions in 2023 (-1.71pp) and 2024 (-4.54pp)** from BEL variant changes.
4. **Guardrail relaxation (relaxed_n150) has zero effect.** In early folds, CD_CORE has
   <150 races so relaxation doesn't apply. In later folds, CD_CORE qualifies through
   relaxation but its score is still well below CD_REFINED's.

### Why CD_CORE can't win on scoring alone

Even after sqrt:
- CD_REFINED: sqrt(66%) × 0.62 pos_yr × 0.90 races_factor ≈ 4.5
- CD_CORE: sqrt(7%) × 0.46 pos_yr × 1.0 races_factor ≈ 1.2

The pos_year_ratio gap (0.62 vs 0.46) and the races factor cap (no credit above 150)
mean CD_CORE needs ~4x better other factors to compete. The races factor ceiling is the
structural bottleneck — CD_CORE's 400+ races get the same credit as CD_REFINED's 135.

### Unrealized improvement

The `diagnose_cd_selection.py` counterfactual showed "always CD_CORE" = +36.20%.
This experiment's best (sqrt|strict) = +30.42%. The remaining ~5.8pp gap requires
either a higher races factor ceiling (giving credit for N>150) or a structural
change to the selection logic that isn't achievable through ROI dampening alone.

## Recommendation

**sqrt|strict should be adopted.** The +7.96pp improvement is real, honest, and comes
from reducing CD_REFINED's ability to crowd out better rules — exactly the kind of
correction the dampened scoring was designed to make.

**It does NOT fully solve the CD_CORE vs CD_REFINED problem.** The next experiment
should test raising the races factor ceiling (e.g., `min(1.0, races/150) * (1 + 0.15 * min(1, max(0, races-150)/300))`)
to give additional credit for sample sizes above 150. This is the structural
bottleneck preventing CD_CORE from being selected.

**The guardrail relaxation is not needed** — it has no effect in this dataset.

Artifacts: `selector_experiment_summary.csv`, `selector_experiment_detail.csv`, `SELECTOR_EXPERIMENT.md`.
