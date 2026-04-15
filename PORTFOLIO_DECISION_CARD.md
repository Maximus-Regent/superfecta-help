# Portfolio Decision Card

This note compares the three portfolio-level choices that matter most right now:
the **Phase 7 live portfolio**, the **Phase 8 frozen portfolio**, and the **train-only yearly selector**.

Short answer:
- **Paper trade the Phase 7 live portfolio first**
- **Keep the Phase 8 frozen portfolio as a shadow challenger, not the default**
- **Use the train-only yearly selector as an honest benchmark, not as the operating recipe**

## Comparison Table

| Approach | Role | Holdout ROI | Holdout Races | 2024 ROI | 2025 ROI | WF ROI | WF Races | WF Years+ | Why It Sits Here |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Phase 7 live portfolio | PAPER NOW | +38.68% | 175 | +0.37% | +105.38% | +31.34% | 806 | 9/10 | Best current paper baseline because it has the strongest 2024-2025 holdout result (+38.68% on 175 races). BEL is dormant here, so the active holdout is effectively the OP+CD portfolio. |
| Phase 8 frozen portfolio | SHADOW ONLY | +21.45% | 118 | +9.50% | +50.26% | +55.04% | 625 | 10/10 | Useful challenger, but it underperformed Phase 7 on holdout (+21.45% vs +38.68%) despite adding more mined rules and more weak legs. |
| Train-only yearly selector | BENCHMARK | +14.36% | 65 | -19.95% | +98.37% | +22.46% | 470 | 8/10 | Most honest validation benchmark, not the best live default. Its walk-forward ROI is still valuable context (+22.46% on 470 races), but its current 2024-2025 holdout is only +14.36% on 65 races. |

## Why This Ordering Is Conservative

- **Phase 7 live portfolio (PAPER NOW)**: Use as the primary paper-trade basket if Cole wants one frozen portfolio today.
  - Why: Best current paper baseline because it has the strongest 2024-2025 holdout result (+38.68% on 175 races). BEL is dormant here, so the active holdout is effectively the OP+CD portfolio.
  - Caution: 2024 was basically flat (+0.37%), so this is still volatile even though the two-year holdout is strongest overall.
- **Phase 8 frozen portfolio (SHADOW ONLY)**: Track as a shadow basket, not as the default, until it beats Phase 7 on more forward data.
  - Why: Useful challenger, but it underperformed Phase 7 on holdout (+21.45% vs +38.68%) despite adding more mined rules and more weak legs.
  - Caution: Its better walk-forward headline is not enough to offset the weaker current holdout and the negative holdout legs inside the basket.
- **Train-only yearly selector (BENCHMARK)**: Keep as the honest benchmark for reports and sanity checks, not as the daily operating recipe.
  - Why: Most honest validation benchmark, not the best live default. Its walk-forward ROI is still valuable context (+22.46% on 470 races), but its current 2024-2025 holdout is only +14.36% on 65 races.
  - Caution: Some historical folds used the old BEL bridge candidate, so it should stay a benchmark artifact rather than a clean deployment rulebook.

## Head-to-Head vs. Phase 7

| Approach | Holdout ROI vs Phase 7 | Holdout Races vs Phase 7 | Practical Read |
|---|---:|---:|---|
| Phase 8 frozen portfolio | -17.23% | -57 | Track as a shadow basket, not as the default, until it beats Phase 7 on more forward data. |
| Train-only yearly selector | -24.32% | -110 | Keep as the honest benchmark for reports and sanity checks, not as the daily operating recipe. |

## Bottom Line

If Cole wants one portfolio-level decision tonight:

1. **Run the Phase 7 live portfolio as the primary paper baseline**
2. **Log the Phase 8 frozen portfolio separately as a shadow basket**
3. **Keep citing the train-only yearly selector as the honest validation yardstick**

That ordering keeps the live choice tied to the strongest current holdout result instead of to the prettiest mined basket or the most abstract validation artifact.

## Validation

- Sources: `compare_main_approaches.csv`, `frozen_portfolio_eval_summary.csv`, `walk_forward_validation_folds.csv`
- Wrote: `portfolio_decision_card.csv`, `PORTFOLIO_DECISION_CARD.md`
- This card is a read-only synthesis of frozen evaluation artifacts

