# Main Approach Comparison

## Usage

```bash
python3 compare_main_approaches.py
```

This is a fast comparison harness. It replays a small fixed set of methods and reads the existing walk-forward artifacts. It does not run a new broad search.

## Scope

- Holdout focus: 2024-2025
- Walk-forward context: next-year tests across 2015-2025, excluding 2021 because the project data excludes that year
- No new BEL->BAQ aliasing is introduced here
- Conservative score weights holdout consistency and holdout sample size more than flashy ROI

## Comparison Table

| Rank | Method | Type | Holdout ROI | Holdout Races | Holdout Years+ | WF ROI | WF Races | WF Years+ | Score | Note |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | Phase 7 live portfolio | fixed portfolio | +38.68% | 175 | 2/2 | +31.34% | 806 | 9/10 | 89.7 | Frozen 3-rule baseline. BEL contributes zero 2024-2025 races, so the current holdout is effectively the OP+CD legs. |
| 2 | Phase 8 frozen portfolio | fixed portfolio | +21.45% | 118 | 2/2 | +55.04% | 625 | 10/10 | 87.9 | Frozen 7-rule Phase 8 basket. Useful as the headline multi-track challenger, but still full-history-mined before this replay. |
| 3 | OP refined only | fixed OP rule | +51.43% | 49 | 1/2 | +66.10% | 207 | 8/10 | 69.9 | Higher-ROI OP variant with a much smaller forward sample. Treat as selective, not as the new default. |
| 4 | OP train-score switch | dynamic OP selector | +51.43% | 49 | 1/2 | +47.46% | 350 | 8/10 | 68.4 | Each year, pick the better-qualifying OP rule by train-only selection score. Recent picks: 2022=OP_DURABLE_K7, 2023=OP_DURABLE_K7, 2024=OP_REFINED_K7, 2025=OP_REFINED_K7. |
| 5 | OP durable only | fixed OP rule | +22.90% | 115 | 1/2 | +40.21% | 416 | 8/10 | 67.4 | Largest-sample OP anchor. Lower upside than the refined OP variant, but materially more forward races. |
| 6 | Train-only yearly selector | dynamic selector | +14.36% | 65 | 1/2 | +22.46% | 470 | 8/10 | 61.9 | The current honest selector baseline from walk_forward_validation.py. Historical context includes the pre-existing BEL bridge candidate in some earlier folds, but no new aliasing is added here. |

## Fast Takeaways

- Large-sample holdout baseline: **Phase 7 live portfolio** at +38.68% on 175 holdout races.
- Best OP-focused line in this table: **OP refined only** at +51.43% on 49 holdout races. That is better ROI, but on a smaller sample than the large-sample baseline.
- Honest selector baseline: **Train-only yearly selector** stays useful context at +22.46% across 470 walk-forward races, but its 2024-2025 holdout is only +14.36% on 65 races.
- Practical read: keep the comparison anchored to the big holdout baselines first, then use the OP-focused methods as narrower follow-ups rather than automatic upgrades.

## Method Notes

- **Phase 7 live portfolio**: Frozen 3-rule baseline. BEL contributes zero 2024-2025 races, so the current holdout is effectively the OP+CD legs.
- **Phase 8 frozen portfolio**: Frozen 7-rule Phase 8 basket. Useful as the headline multi-track challenger, but still full-history-mined before this replay.
- **OP refined only**: Higher-ROI OP variant with a much smaller forward sample. Treat as selective, not as the new default.
- **OP train-score switch**: Each year, pick the better-qualifying OP rule by train-only selection score. Recent picks: 2022=OP_DURABLE_K7, 2023=OP_DURABLE_K7, 2024=OP_REFINED_K7, 2025=OP_REFINED_K7.
- **OP durable only**: Largest-sample OP anchor. Lower upside than the refined OP variant, but materially more forward races.
- **Train-only yearly selector**: The current honest selector baseline from walk_forward_validation.py. Historical context includes the pre-existing BEL bridge candidate in some earlier folds, but no new aliasing is added here.

## Validation

- Runtime: 0.04 seconds
- Data sources: `phase5_race_cache.pkl`, `phase7_live_rules.json`, `walk_forward_validation_folds.csv`, `walk_forward_validation_rules.csv`
- Wrote: `compare_main_approaches.csv`, `compare_main_approaches.md`

