# OP Family Decision Card

This note compares the three realistic OP paths and asks one narrow question:
**does anything clearly beat `OP_DURABLE_K7` strongly enough to replace it as the safest current anchor?**

Short answer: **no**. The challengers show higher ROI, but not enough forward sample or coverage to replace the durable anchor yet.

## Comparison Table

| Method | Type | Holdout ROI | Holdout Races | Holdout Years+ | Worst Holdout Year | WF ROI | WF Races | WF Years+ | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OP_DURABLE_K7 | fixed anchor | +22.90% | 115 | 1/2 | -47.41% | +40.21% | 416 | 8/10 | KEEP AS ANCHOR |
| Train-only OP switch | dynamic challenger | +51.43% | 49 | 1/2 | -25.47% | +47.46% | 350 | 8/10 | KEEP AS WATCH / RESEARCH |
| OP_REFINED_K7 | fixed challenger | +51.43% | 49 | 1/2 | -25.47% | +66.10% | 207 | 8/10 | KEEP AS WATCH / RESEARCH |

## Conservative Replacement Bar vs. Anchor

A challenger only gets promoted in this note if it clears **all** of these conservative checks:

1. Better holdout ROI than `OP_DURABLE_K7`
2. At least as many 2024-2025 holdout races as `OP_DURABLE_K7`
3. No losing year inside the 2024-2025 holdout window
4. At least as many walk-forward races as `OP_DURABLE_K7`
5. At least as many positive walk-forward years as `OP_DURABLE_K7`

That bar is intentionally hard. Replacing the anchor should require clearer evidence than simply posting a prettier ROI on a much smaller sample.

| Challenger | Better Holdout ROI? | Match Holdout Sample? | No Losing Holdout Year? | Match WF Coverage? | Match WF Positive Years? | Result |
|---|---|---|---|---|---|---|
| Train-only OP switch | yes | no | no | no | yes | KEEP AS WATCH / RESEARCH |
| OP_REFINED_K7 | yes | no | no | no | yes | KEEP AS WATCH / RESEARCH |

## What This Means

- **Keep `OP_DURABLE_K7` as the live-paper anchor.** It has 115 holdout races and 416 walk-forward races, which is the strongest forward sample inside the OP family.
- **Keep `OP_REFINED_K7` as a challenger, not a replacement.** Its ROI is attractive, but its forward sample is much smaller and still includes a losing holdout year.
- **Treat the train-only OP switch as research context.** In the current holdout window it collapses to the refined rule anyway, so it does not add independent forward evidence yet.

## Notes

- **OP_DURABLE_K7**: Largest-sample OP path. This is the safest current live-paper anchor.
- **Train-only OP switch**: Train-only yearly selector across the two OP rules. Holdout choices: 2024=OP_REFINED_K7, 2025=OP_REFINED_K7. Recent WF picks: 2022=OP_DURABLE_K7, 2023=OP_DURABLE_K7, 2024=OP_REFINED_K7, 2025=OP_REFINED_K7.
- **OP_REFINED_K7**: Higher ROI, but on much smaller forward samples and with mixed 2024/2025 behavior.

## Validation

- Source logic reused from `compare_main_approaches.py`
- Source files: `phase5_race_cache.pkl`, `phase7_live_rules.json`, `walk_forward_validation_rules.csv`
- Wrote: `op_family_decision.csv`, `OP_FAMILY_DECISION.md`

