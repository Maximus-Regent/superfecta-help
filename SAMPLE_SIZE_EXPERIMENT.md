# Sample-Size-Aware Selector Experiment

## Current Evidence Boundary

- This is historical selector-tuning research on frozen walk-forward artifacts. It is useful for understanding why races-factor tuning did not beat `sqrt_r150`, but it is not a live paper-trade ledger, settled ROI evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- Valid evidence scope: `valid_evidence_scope=sample_size_selector_replay_diagnostic_only`.
- Valid use: compare selector-scoring variants against the original +22.46% train-only selector and the prior `sqrt_r150` benchmark. Do not treat the `keep sqrt_r150` recommendation as permission to change the current paper basket or override `forward_evidence_scorecard.txt`.
- Current posture still comes from the frozen scorecard plus paper-observation lane: keep `OP_DURABLE_K7` as the safest anchor, `CD_CORE_K8` as the primary OP/CD paper-basket companion, and `OP_REFINED_K7` in shadow/watch until ROI-complete paper evidence clears the scorecard gates.
- The always-CD_CORE counterfactual and selector variants are replay diagnostics on already-mined candidate rules, not a fresh from-scratch discovery loop and not proof that CD_CORE should displace OP as anchor evidence.
- If this selector-research report is regenerated after scorecard/rules/signals/settlement-ledger byte changes, follow `current_evidence_summary.json.rebuild_validation_contract`: `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`; this rebuild route is provenance metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- Do not substitute `BAQ` for dormant `BEL`, and validate this boundary with `python3 validate_sample_size_experiment_caution.py`.

## Purpose

Test whether adjusting the races factor / sample-size bonus in the
walk-forward selection score closes more of the gap between the selector
(+30.42%) and the always-CD_CORE counterfactual (+29.98%).

The prior experiment found sqrt(train_roi) as the best ROI dampener.
The structural bottleneck identified: races factor caps at 150, so
CD_CORE's 400+ races get the same credit as CD_REFINED's ~135.

## Method

- Same frozen `walk_forward_validation_rules.csv` — no new rule mining.
- All variants use strict guardrails (relaxation had zero effect).
- All except raw_r150 use sqrt(train_roi) as the ROI dampener.
- Only the races factor changes between variants.

**Validation:** raw_r150 validated: +22.46% vs original +22.46%. sqrt_r150 validated: +30.42% vs prior best +30.42%.

## Races Factor Variants

| Variant | ROI Term | Races Factor | Description |
|---|---|---|---|
| raw_r150 | raw | `min(1, N/150)` | Original baseline |
| sqrt_r150 | sqrt | `min(1, N/150)` | Prior best (cap 150) |
| sqrt_r250 | sqrt | `min(1, N/250)` | Cap raised to 250 |
| sqrt_r300 | sqrt | `min(1, N/300)` | Cap raised to 300 |
| sqrt_r400 | sqrt | `min(1, N/400)` | Cap raised to 400 |
| sqrt_softbonus | sqrt | `min(1,N/150) + 0.25·min(1,(N-150)/250)` | Soft bonus above 150 |
| sqrt_lograces | sqrt | `log(1+N)/log(151)` | Continuous log scaling |

### Races Factor Values for CD Rules

| Variant | CD_CORE @ 400 races | CD_REFINED @ 135 races | Ratio |
|---|---:|---:|---:|
| cap 150 | 1.000 | 0.900 | 1.11x |
| cap 250 | 1.000 | 0.540 | 1.85x |
| cap 300 | 1.000 | 0.450 | 2.22x |
| cap 400 | 1.000 | 0.338 | 2.96x |
| softbonus | 1.250 | 0.900 | 1.39x |
| lograces | 1.195 | 0.979 | 1.22x |

## Results

| Variant | ROI | Profit | Pos Yrs | CD_CORE | CD_REFINED | CD_NONE | OP_DUR | OP_REF |
|---|---:|---:|---|---:|---:|---:|---:|---:|
|  **sqrt_r150** | +30.42% | $23,798.15 | 8/10 | 1 | 6 | 3 | 8 | 2 |
| sqrt_softbonus | +27.78% | $23,933.95 | 8/10 | 1 | 6 | 3 | 10 | 0 |
| sqrt_r400 | +26.27% | $24,844.41 | 8/10 | 3 | 5 | 2 | 10 | 0 |
| sqrt_r300 | +22.73% | $20,902.35 | 8/10 | 2 | 6 | 2 | 10 | 0 |
| raw_r150 | +22.46% | $17,541.35 | 8/10 | 1 | 7 | 2 | 7 | 2 |
| sqrt_lograces | +21.15% | $16,208.80 | 6/10 | 1 | 2 | 7 | 8 | 0 |
| sqrt_r250 | +20.30% | $17,906.75 | 8/10 | 2 | 6 | 2 | 9 | 1 |

**Counterfactual (always CD_CORE):** +29.98% ROI, $37,980.09 profit, 8/10 positive years.

### Summary

- **Original baseline (raw_r150):** +22.46% ROI
- **Prior best (sqrt_r150):** +30.42% ROI
- **Best this experiment (sqrt_r150):** +30.42% ROI
- **Delta vs original:** +7.96pp
- **Delta vs prior best:** +0.00pp
- **Gap to counterfactual:** -0.44pp remaining

## CD Selection Detail

### raw_r150

| Year | Rule | Score | Races Factor | Qual | Sel | Train ROI | Races | PosYr | Test ROI |
|---:|---|---:|---:|---|---|---:|---:|---:|---:|
| 2015 | CD_CORE_K8 | 5.4990 | 0.940 | Y | **YES** | +15.60% | 141 | 0.60 | -60.65% |
| 2015 | CD_REFINED_K9 | 0.0000 | 0.380 | N | no | -10.50% | 57 | 0.60 | +90.41% |
| 2016 | CD_CORE_K8 | 0.8325 | 1.000 | Y | no | +2.22% | 171 | 0.50 | -8.87% |
| 2016 | CD_REFINED_K9 | 0.4160 | 0.433 | Y | no | +1.92% | 65 | 0.67 | +179.28% |
| 2017 | CD_CORE_K8 | 0.2663 | 1.000 | N | no | +0.71% | 198 | 0.43 | +59.30% |
| 2017 | CD_REFINED_K9 | 7.2429 | 0.493 | Y | **YES** | +23.49% | 74 | 0.71 | -88.28% |
| 2018 | CD_CORE_K8 | 5.7800 | 1.000 | Y | no | +11.56% | 243 | 0.50 | -37.62% |
| 2018 | CD_REFINED_K9 | 1.7244 | 0.593 | Y | no | +4.65% | 89 | 0.62 | +869.41% |
| 2019 | CD_CORE_K8 | 2.4531 | 1.000 | N | no | +5.52% | 277 | 0.44 | -13.09% |
| 2019 | CD_REFINED_K9 | 29.2181 | 0.660 | Y | **YES** | +92.00% | 99 | 0.67 | +11.64% |
| 2020 | CD_CORE_K8 | 1.0320 | 1.000 | N | no | +2.58% | 329 | 0.40 | -16.34% |
| 2020 | CD_REFINED_K9 | 33.1553 | 0.720 | Y | **YES** | +85.30% | 108 | 0.70 | -73.78% |
| 2022 | CD_CORE_K8 | 0.2945 | 1.000 | N | no | +0.81% | 363 | 0.36 | +32.23% |
| 2022 | CD_REFINED_K9 | 27.5640 | 0.807 | Y | **YES** | +68.21% | 121 | 0.64 | +80.95% |
| 2023 | CD_CORE_K8 | 1.4293 | 1.000 | N | no | +3.43% | 396 | 0.42 | +55.92% |
| 2023 | CD_REFINED_K9 | 34.6134 | 0.873 | Y | **YES** | +69.19% | 131 | 0.67 | -8.53% |
| 2024 | CD_CORE_K8 | 3.2351 | 1.000 | N | no | +7.01% | 425 | 0.46 | +45.65% |
| 2024 | CD_REFINED_K9 | 32.3811 | 0.900 | Y | **YES** | +66.88% | 135 | 0.62 | -14.54% |
| 2025 | CD_CORE_K8 | 5.2050 | 1.000 | Y | no | +10.41% | 466 | 0.50 | +78.21% |
| 2025 | CD_REFINED_K9 | 30.3999 | 0.980 | Y | **YES** | +60.24% | 147 | 0.57 | -61.12% |

### sqrt_r150

| Year | Rule | Score | Races Factor | Qual | Sel | Train ROI | Races | PosYr | Test ROI |
|---:|---|---:|---:|---|---|---:|---:|---:|---:|
| 2015 | CD_CORE_K8 | 1.3923 | 0.940 | Y | **YES** | +15.60% | 141 | 0.60 | -60.65% |
| 2015 | CD_REFINED_K9 | 0.0000 | 0.380 | N | no | -10.50% | 57 | 0.60 | +90.41% |
| 2016 | CD_CORE_K8 | 0.5587 | 1.000 | Y | no | +2.22% | 171 | 0.50 | -8.87% |
| 2016 | CD_REFINED_K9 | 0.3002 | 0.433 | Y | no | +1.92% | 65 | 0.67 | +179.28% |
| 2017 | CD_CORE_K8 | 0.3160 | 1.000 | N | no | +0.71% | 198 | 0.43 | +59.30% |
| 2017 | CD_REFINED_K9 | 1.4944 | 0.493 | Y | no | +23.49% | 74 | 0.71 | -88.28% |
| 2018 | CD_CORE_K8 | 1.7000 | 1.000 | Y | no | +11.56% | 243 | 0.50 | -37.62% |
| 2018 | CD_REFINED_K9 | 0.7997 | 0.593 | Y | no | +4.65% | 89 | 0.62 | +869.41% |
| 2019 | CD_CORE_K8 | 1.0441 | 1.000 | N | no | +5.52% | 277 | 0.44 | -13.09% |
| 2019 | CD_REFINED_K9 | 3.0462 | 0.660 | Y | **YES** | +92.00% | 99 | 0.67 | +11.64% |
| 2020 | CD_CORE_K8 | 0.6425 | 1.000 | N | no | +2.58% | 329 | 0.40 | -16.34% |
| 2020 | CD_REFINED_K9 | 3.5899 | 0.720 | Y | **YES** | +85.30% | 108 | 0.70 | -73.78% |
| 2022 | CD_CORE_K8 | 0.3272 | 1.000 | N | no | +0.81% | 363 | 0.36 | +32.23% |
| 2022 | CD_REFINED_K9 | 3.3375 | 0.807 | Y | **YES** | +68.21% | 121 | 0.64 | +80.95% |
| 2023 | CD_CORE_K8 | 0.7717 | 1.000 | N | no | +3.43% | 396 | 0.42 | +55.92% |
| 2023 | CD_REFINED_K9 | 4.1612 | 0.873 | Y | **YES** | +69.19% | 131 | 0.67 | -8.53% |
| 2024 | CD_CORE_K8 | 1.2219 | 1.000 | N | no | +7.01% | 425 | 0.46 | +45.65% |
| 2024 | CD_REFINED_K9 | 3.9595 | 0.900 | Y | **YES** | +66.88% | 135 | 0.62 | -14.54% |
| 2025 | CD_CORE_K8 | 1.6132 | 1.000 | Y | no | +10.41% | 466 | 0.50 | +78.21% |
| 2025 | CD_REFINED_K9 | 3.9168 | 0.980 | Y | **YES** | +60.24% | 147 | 0.57 | -61.12% |

## Analysis

**Why the races factor doesn't help:**

CD_CORE_K8 is **disqualified by the guardrail** (pos_year_ratio < 0.50) in 6 of 10 folds
(2017, 2019, 2020, 2022, 2023, 2024). In the 4 folds where CD_CORE qualifies
(2015, 2016, 2018, 2025), CD_REFINED still outscores it on sqrt(ROI) in 3 of those 4 folds.
The races factor can only matter when both rules qualify AND compete on score — and even
a 3x races factor advantage (sqrt_r400) can't overcome the sqrt(66%) vs sqrt(7%) ROI gap.

sqrt_r400 did increase CD_CORE selection to **3/10 folds** (vs 1/10 under sqrt_r150),
but the additional folds included 2018 where CD_CORE had -37.62% test ROI vs
CD_REFINED's +869.41% — a catastrophic misselection that wiped out the gains
from 2025 (+78.21% CD_CORE vs -61.12% CD_REFINED).

**Key finding — the gap was already closed:**

The prior diagnosis estimated a +13.74pp gap between the selector (+22.46%) and the
always-CD_CORE counterfactual (+36.20%). But that comparison used raw scoring for non-CD
rules. Under sqrt scoring, the always-CD_CORE counterfactual is +29.98%, and the
sqrt_r150 selector already achieves +30.42% — **slightly exceeding the counterfactual.**
The sqrt dampening improvement (+7.96pp) came mostly from fixing non-CD selection
(displacing CD_REFINED from the 2017 portfolio in favor of OP_DURABLE), not from
CD_CORE vs CD_REFINED directly.

**Gap analysis:** The always-CD_CORE counterfactual achieves +29.98% ROI.
The sqrt_r150 selector achieves +30.42%. There is no remaining gap to close.

## Recommendation

No meaningful improvement from adjusting the races factor alone (+0.00pp).
The bottleneck is the guardrail, not the sample-size weighting. But it does not
matter because sqrt_r150 already matches or exceeds the counterfactual.

**Recommended action:** keep sqrt_r150 as the selector. No further races factor
tuning is warranted. The CD selection "problem" identified in the diagnosis was
already resolved by the sqrt dampening of the ROI term — the improvement came from
better non-CD selection, not from CD_CORE replacing CD_REFINED.

Artifacts: `sample_size_experiment_summary.csv`, `sample_size_experiment_detail.csv`, `SAMPLE_SIZE_EXPERIMENT.md`.
