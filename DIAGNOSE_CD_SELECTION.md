# CD Track-Group Selection Diagnostic

## Current Evidence Boundary

Valid evidence scope: `valid_evidence_scope=cd_track_group_selector_replay_diagnostic_only`.

This is a historical CD track-group selector diagnostic on frozen walk-forward artifacts. It is not a live paper-trade ledger, settled ROI evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

Valid use: explain why the train-only selector tends to pick `CD_REFINED_K9` over `CD_CORE_K8` and why the current paper lane keeps `CD_CORE_K8` as the OP/CD companion. The `Always CD_CORE` and `No CD rule` rows are replay diagnostics, not current deployment instructions or a new expected ROI range.

Current posture still comes from `forward_evidence_scorecard.txt`, `compare_main_approaches.md`, and the paper-observation gates: keep `OP_DURABLE_K7` as the safest anchor, `CD_CORE_K8` as the primary OP/CD paper companion, and `OP_REFINED_K7` plus Phase 8 in shadow/watch until ROI-complete paper evidence clears the scorecard gates.

The `Always CD_CORE` replay and `No CD rule` replay do not override the +22.46% train-only benchmark, the realistic +20-25% planning range, or settled-observation requirements; they identify selector mechanism debt. BEL bridge rows are historical diagnostics only. Do not substitute `BAQ` for dormant `BEL`.

If this CD diagnostic is regenerated after scorecard/rules/signals/settlement-ledger byte changes, follow `current_evidence_summary.json.rebuild_validation_contract`: `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`; this rebuild route is provenance metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.

Validate this boundary with `python3 validate_diagnose_cd_selection_caution.py`.

## Problem

The walk-forward selector picks CD_REFINED_K9 over CD_CORE_K8 in 7/10 folds.
CD_REFINED has ~10x higher train ROI (66.88% vs 7.01%), which dominates the selection score.
But on the 2024-2025 holdout, CD_CORE = **+55.96%** and CD_REFINED = **-26.18%**.

Two mechanisms cause this:

1. **Guardrail exclusion**: CD_CORE's modest train ROI means its per-year ROI is often slightly negative, dropping its positive-year ratio below the 50% threshold. It gets `qualifies=False` in 6/10 folds.
2. **Score domination**: Even in folds where both qualify, CD_REFINED's selection score is 5-10x higher because raw train ROI is the dominant term in the scoring formula.

## Head-to-Head: CD_CORE vs CD_REFINED by Fold

| Year | Selected | Core Qual | Core Score | Core Test ROI | Refined Qual | Refined Score | Refined Test ROI | Better OOS |
|---:|---|---|---:|---:|---|---:|---:|---|
| 2015 | CD_CORE_K8 | True | 5.5 | -60.65% | False | 0.0 | +90.41% | **CD_REFINED** |
| 2016 | NEITHER | True | 0.83 | -8.87% | True | 0.42 | +179.28% | **CD_REFINED** |
| 2017 | CD_REFINED_K9 | False | 0.27 | +59.30% | True | 7.24 | -88.28% | **CD_CORE** |
| 2018 | NEITHER | True | 5.78 | -37.62% | True | 1.72 | +869.41% | **CD_REFINED** |
| 2019 | CD_REFINED_K9 | False | 2.45 | -13.09% | True | 29.22 | +11.64% | **CD_REFINED** |
| 2020 | CD_REFINED_K9 | False | 1.03 | -16.34% | True | 33.16 | -73.78% | **CD_CORE** |
| 2022 | CD_REFINED_K9 | False | 0.29 | +32.23% | True | 27.56 | +80.95% | **CD_REFINED** |
| 2023 | CD_REFINED_K9 | False | 1.43 | +55.92% | True | 34.61 | -8.53% | **CD_CORE** |
| 2024 | CD_REFINED_K9 | False | 3.24 | +45.65% | True | 32.38 | -14.54% | **CD_CORE** |
| 2025 | CD_REFINED_K9 | True | 5.21 | +78.21% | True | 30.4 | -61.12% | **CD_CORE** |

CD_CORE was the better out-of-sample choice in **5/10** folds.

## Counterfactual Walk-Forward ROI

What if the selector had always chosen CD_CORE_K8 instead of CD_REFINED_K9?

| Year | Actual Rules | Actual ROI | Swap→CD_CORE ROI | No CD ROI |
|---:|---|---:|---:|---:|
| 2015 | CD_CORE_K8,OP_DURABLE_K7 | -39.24% | -39.24% | +5.74% |
| 2016 | BEL_BROAD1_K7_BRIDGE_BAQ,KEE_K9,OP_DURABLE_K7 | +5.13% | +5.13% | +5.13% |
| 2017 | BEL_BROAD1_K7_BRIDGE_BAQ,KEE_K9,CD_REFINED_K9 | +8.37% | +75.20% | +105.01% |
| 2018 | BEL_BROAD1_K7_BRIDGE_BAQ,KEE_K9,OP_DURABLE_K7 | +154.38% | +154.38% | +154.38% |
| 2019 | BEL_BROAD1_K7_BRIDGE_BAQ,OP_DURABLE_K7,CD_REFINED_K9 | +51.68% | +10.97% | +86.46% |
| 2020 | BEL_BROAD1_K7_BRIDGE_BAQ,CD_REFINED_K9,OP_DURABLE_K7 | +28.28% | +37.23% | +91.25% |
| 2022 | BEL_BROAD1_K7_BRIDGE_BAQ,OP_DURABLE_K7,CD_REFINED_K9 | +28.32% | +16.29% | -3.72% |
| 2023 | BEL_BROAD1_K7,CD_REFINED_K9,OP_DURABLE_K7 | +13.35% | +36.31% | +17.88% |
| 2024 | BEL_BROAD1_K7,OP_REFINED_K7,CD_REFINED_K9 | -19.95% | +23.25% | -25.47% |
| 2025 | BEL_BROAD1_K7,CD_REFINED_K9,OP_REFINED_K7 | +98.37% | +121.03% | +210.02% |

### Aggregate

| Scenario | Wagered | Profit | ROI | Positive Years |
|---|---:|---:|---:|---|
| Actual selector | $78,108 | $17,541.35 | +22.46% | 8/10 |
| Always CD_CORE | $108,726 | $39,361.89 | +36.20% | 9/10 |
| No CD rule | $49,296 | $27,484.50 | +55.75% | 8/10 |

The `No CD rule` row is a stress-test comparator only; it is not a recommendation to remove `CD_CORE_K8` from the current OP/CD paper basket.

## Interpretation

Substituting CD_CORE for CD_REFINED across all folds changes the historical walk-forward replay ROI from **+22.46%** to **+36.20%** (delta: +13.74pp).

This is a meaningful replay diagnostic that comes entirely from fixing the CD selection, not from mining new rules or loosening thresholds. It is not a fresh expected-ROI estimate.

## Root Cause

The selection score formula uses raw train ROI as the dominant term. A rule with 66% train ROI on 135 races will always outscore a rule with 7% train ROI on 425 races, even though the second rule is more likely to be durable. The guardrail system compounds this by disqualifying the stable-but-modest rule for failing the positive-year-ratio check.

## What This Means for Cole

1. **The current walk-forward benchmark (+22.46%) likely understates the CD selection mechanism** because it systematically picks the wrong CD variant, but the **+36.20%** replay is a counterfactual diagnostic, not a new expected portfolio ROI or a replacement for the scorecard's planning range.
2. **No rule change is needed.** CD_CORE_K8 is already in phase7_live_rules.json and the current paper basket. The problem is only in how the walk-forward validator selects rules — it picks CD_REFINED from the Phase 8 candidate pool instead of CD_CORE.
3. **The fix is methodological, not operational.** The live paper-trade basket already uses CD_CORE_K8. Cole is already running the right rule. This diagnostic just shows that the walk-forward validation report was penalized by a selector-mechanism weakness, not by a real edge weakness.
4. **If the walk-forward selector is ever updated**, the selection score should dampen the ROI term (e.g., log or sqrt) and/or include a cost penalty. High train ROI on a small sample with expensive tickets is an overfit signal, not an edge signal.

Artifacts: `diagnose_cd_selection_comparison.csv`, `DIAGNOSE_CD_SELECTION.md`.

