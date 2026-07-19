# Walk-Forward Validation

## Current Evidence Boundary

- This is a historical train-only selector benchmark, not a live paper-trade ledger, current-day scanner output, settled ROI evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.
- Valid evidence scope: `valid_evidence_scope=train_only_walk_forward_selector_benchmark_only`.
- Valid use: compare stricter train-only rule selection against fixed Phase 7 / Phase 8 replays and explain why the honest forward expectation is lower than full-sample discovery headlines.
- Limitation: the candidate universe was still mined from previous full-sample research before this walk-forward, so the +22.46% selector result is useful but still optimistic versus a true from-scratch yearly rediscovery loop.
- Current operator posture still comes from the frozen scorecard and current paper-observation lane: keep `OP_DURABLE_K7` as the safest anchor, `CD_CORE_K8` as the primary OP/CD paper-basket companion, and `OP_REFINED_K7` shadow/watch until forward paper gates are met.
- The fixed Phase 7 / Phase 8 comparison below is replay context on the same test years, not extra train-only validation, and the BEL->BAQ bridge rows are a coverage diagnostic only. Do not substitute BAQ for dormant BEL.

## What This Is

- Candidate universe: existing promoted rules from `phase7_live_rules.json` and the frozen Phase 8 rules.
- Selection logic: for each test year, score and select rules using only prior years.
- Test logic: evaluate the selected portfolio on the next year only.
- Limitation: this is still not a true from-scratch yearly rediscovery loop; the candidate universe was originally mined from historical full-sample work.

## Guardrails

- Minimum train races: 40
- Minimum active train years: 4
- Minimum positive-year ratio: 50%
- Maximum top-1 payout share: 55%
- Maximum top-3 payout share: 85%
- Maximum portfolio size: 3 rules, one per track group

## Train-Only Walk-Forward Result

- Test years: 10
- Positive test years: 8/10
- Total races: 470
- Total wagered: $78,108.00
- Total profit: $17,541.35
- Total ROI: +22.46%
- Average selected rules per fold: 2.9

## Full-Sample-Mined Portfolio Comparison

- Fixed Phase 7 current-paper rule portfolio over the same test years: +31.34% ROI on 806 races, 9/10 positive years.
- Fixed Phase 8 frozen portfolio over the same test years: +48.39% ROI on 579 races, 9/10 positive years.
- Train-only selection result: +22.46% ROI on 470 races, 8/10 positive years.

## BEL vs BAQ Coverage Break

- Strict BEL broad rule in 2024-2025: 0 races, +0.00% ROI.
- BEL->BAQ bridge variant in 2024-2025: 7 races, -91.55% ROI.
- Strict BEL zero-coverage folds where the bridge would have had action: 2.
- Takeaway: aliasing fixes the coverage break, but it does not rescue the economics. BAQ did not behave like a hidden continuation of the BEL edge here.

## Guardrail Diagnostics

- Selected-rule sparse flags: 0
- Selected-rule unstable-year flags: 0
- Selected-rule payout-concentration flags: 0
- The selection CSV shows which candidates were blocked by each guardrail in each fold.

## Most Selected Rules

- CD_REFINED_K9: selected in 7 folds
- OP_DURABLE_K7: selected in 7 folds
- BEL_BROAD1_K7_BRIDGE_BAQ: selected in 6 folds
- BEL_BROAD1_K7: selected in 3 folds
- KEE_K9: selected in 3 folds
- OP_REFINED_K7: selected in 2 folds
- CD_CORE_K8: selected in 1 folds

## Unstable Test Years

- 2015: -39.24% ROI on 55 races, $-3,649.00 profit, rules = CD_CORE_K8,OP_DURABLE_K7
- 2024: -19.95% ROI on 45 races, $-1,594.60 profit, rules = BEL_BROAD1_K7,OP_REFINED_K7,CD_REFINED_K9

## Selected Rule Snapshot

| Year | Rule | Train Races | Train ROI | Pos Year Ratio | Top1 Share | Top3 Share | Test Races | Test ROI |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2015 | CD_CORE_K8 | 141 | +15.60% | 60% | 11% | 25% | 30 | -60.65% |
| 2015 | OP_DURABLE_K7 | 89 | +10.76% | 50% | 33% | 62% | 25 | +5.74% |
| 2016 | BEL_BROAD1_K7_BRIDGE_BAQ | 46 | +82.16% | 67% | 20% | 53% | 7 | +28.87% |
| 2016 | KEE_K9 | 42 | +72.58% | 83% | 28% | 63% | 7 | -28.94% |
| 2016 | OP_DURABLE_K7 | 114 | +9.66% | 60% | 26% | 49% | 36 | +19.07% |
| 2017 | BEL_BROAD1_K7_BRIDGE_BAQ | 53 | +75.13% | 71% | 18% | 48% | 14 | +244.40% |
| 2017 | CD_REFINED_K9 | 74 | +23.49% | 71% | 25% | 41% | 15 | -88.28% |
| 2017 | KEE_K9 | 49 | +58.08% | 71% | 27% | 59% | 10 | +35.31% |
| 2018 | BEL_BROAD1_K7_BRIDGE_BAQ | 67 | +110.50% | 75% | 26% | 49% | 6 | +192.11% |
| 2018 | KEE_K9 | 59 | +54.22% | 75% | 23% | 50% | 4 | +25.68% |
| 2018 | OP_DURABLE_K7 | 188 | +20.18% | 71% | 15% | 34% | 27 | +199.38% |
| 2019 | BEL_BROAD1_K7_BRIDGE_BAQ | 73 | +117.20% | 78% | 23% | 44% | 3 | +569.58% |
| 2019 | CD_REFINED_K9 | 99 | +92.00% | 67% | 49% | 65% | 9 | +11.64% |
| 2019 | OP_DURABLE_K7 | 215 | +42.68% | 75% | 13% | 33% | 26 | +30.72% |
| 2020 | BEL_BROAD1_K7_BRIDGE_BAQ | 76 | +135.06% | 80% | 20% | 39% | 2 | +73.54% |
| 2020 | CD_REFINED_K9 | 108 | +85.30% | 70% | 47% | 62% | 13 | -73.78% |
| 2020 | OP_DURABLE_K7 | 241 | +41.39% | 78% | 12% | 30% | 57 | +91.87% |
| 2022 | BEL_BROAD1_K7_BRIDGE_BAQ | 78 | +133.48% | 82% | 20% | 38% | 2 | +778.33% |
| 2022 | CD_REFINED_K9 | 121 | +68.21% | 64% | 46% | 61% | 10 | +80.95% |
| 2022 | OP_DURABLE_K7 | 298 | +51.05% | 80% | 9% | 23% | 44 | -39.27% |
| 2023 | BEL_BROAD1_K7 | 79 | +152.77% | 83% | 18% | 35% | 6 | -100.00% |
| 2023 | CD_REFINED_K9 | 131 | +69.19% | 67% | 42% | 57% | 4 | -8.53% |
| 2023 | OP_DURABLE_K7 | 342 | +39.43% | 73% | 8% | 22% | 48 | +32.62% |
| 2024 | BEL_BROAD1_K7 | 85 | +134.92% | 77% | 18% | 35% | 0 | +0.00% |
| 2024 | CD_REFINED_K9 | 135 | +66.88% | 62% | 42% | 56% | 12 | -14.54% |
| 2024 | OP_REFINED_K7 | 218 | +49.74% | 67% | 10% | 28% | 33 | -25.47% |
| 2025 | BEL_BROAD1_K7 | 85 | +134.92% | 77% | 18% | 35% | 0 | +0.00% |
| 2025 | CD_REFINED_K9 | 147 | +60.24% | 57% | 40% | 54% | 4 | -61.12% |
| 2025 | OP_REFINED_K7 | 251 | +39.85% | 62% | 9% | 26% | 16 | +210.02% |

## Blunt Takeaway

The edge looks weaker under real train-only selection than the full-sample writeups suggest. It is still positive in aggregate, but the durable part is basically OP plus occasional help from CD/KEE, while BEL disappears and the BAQ bridge loses badly.

Artifacts written: `walk_forward_validation_folds.csv`, `walk_forward_validation_rules.csv`, `WALK_FORWARD_VALIDATION.md`.
Candidate rules evaluated: 10.
