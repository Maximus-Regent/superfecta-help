# Cross-Family Decision Card

This note compares the three most relevant active rules for current live-paper use:
`OP_DURABLE_K7`, `CD_CORE_K8`, and `OP_REFINED_K7`.

Short answer:
- **Keep `OP_DURABLE_K7` as the anchor**
- **Paper trade `CD_CORE_K8`, but do not let it replace the anchor yet**
- **Keep `OP_REFINED_K7` on watch, not as a promoted live default**

## Comparison Table

| Rule | Family | Role | Holdout ROI | Holdout Races | 2024 ROI | 2025 ROI | Holdout Years+ | WF Selected | CI Lower | Why It Sits Here |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| OP_DURABLE_K7 | OP | ANCHOR | +22.90% | 115 | -47.41% | +124.61% | 1/2 | 7/10 | -3.40% | Safest anchor because it has the largest active holdout sample (115) and the strongest walk-forward selection frequency (7/10). |
| CD_CORE_K8 | CD | PAPER | +55.96% | 60 | +45.65% | +78.21% | 2/2 | 1/10 | -15.00% | Paper now because holdout is positive in both years (+45.65%, +78.21%), but the forward sample is still smaller than the OP anchor and walk-forward selection is only 1/10. |
| OP_REFINED_K7 | OP | WATCH | +51.43% | 49 | -25.47% | +210.02% | 1/2 | 2/10 | +11.20% | Watch only because the ROI is attractive, but the holdout sample is only 49 races and 2024 was a losing year (-25.47%). |

## Why the Current Roles Make Sense

- **OP_DURABLE_K7 (ANCHOR)**: Safest anchor because it has the largest active holdout sample (115) and the strongest walk-forward selection frequency (7/10).
  - Family caution: OP is the strongest current family, but the refined OP variant still lacks enough forward sample to replace this anchor.
- **CD_CORE_K8 (PAPER)**: Paper now because holdout is positive in both years (+45.65%, +78.21%), but the forward sample is still smaller than the OP anchor and walk-forward selection is only 1/10.
  - Family caution: CD family caution: the more selective CD_REFINED_K9 looked better in-sample but lost on 2024-2025 holdout, so keep the simpler CD rule on paper only.
- **OP_REFINED_K7 (WATCH)**: Watch only because the ROI is attractive, but the holdout sample is only 49 races and 2024 was a losing year (-25.47%).
  - Family caution: Interesting OP challenger, but still not strong enough to displace the durable OP rule.

## Head-to-Head vs. the Anchor

| Rule | Holdout ROI vs Anchor | Holdout Races vs Anchor | WF Selected vs Anchor | Practical Read |
|---|---:|---:|---:|---|
| CD_CORE_K8 | +33.06% | -55 | -6 | Better holdout ROI than the anchor, but on only 60 races and with much weaker walk-forward selection. |
| OP_REFINED_K7 | +28.53% | -66 | -5 | Higher ROI than the anchor, but smaller sample and still includes a losing holdout year. |

## Bottom Line

If Cole wants one clean live-paper hierarchy right now:

1. **Anchor:** `OP_DURABLE_K7`
2. **Paper alongside it:** `CD_CORE_K8`
3. **Watch / shadow only:** `OP_REFINED_K7`

That ordering is intentionally conservative. It protects against promoting the prettiest small-sample ROI line over the strongest forward-evidence anchor.

## Validation

- Sources: `forward_evidence_scorecard.csv`, `frozen_portfolio_eval_summary.csv`
- Wrote: `cross_family_decision_card.csv`, `CROSS_FAMILY_DECISION.md`
- This card is a read-only synthesis of existing frozen evaluation artifacts

