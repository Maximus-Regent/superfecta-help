# EV Ticket Engine Usage

## Current Evidence Boundary

- This is a source-layer paper-trade/debugging runbook for `ev_ticket_engine.py`, not the daily operating path by itself.
- Valid evidence scope: `valid_evidence_scope=ev_ticket_engine_usage_source_layer_runbook_navigation_only`.
- The preferred daily observation path remains `./run_daily_portfolio_observation.sh`, which routes through `paper_trade_recommender.py` after Phase 7 combo filtering and then uses the EV engine underneath.
- A `Decision: BET` from this engine means a hypothetical paper-ticket plan under the stated assumptions. It is not live profitability evidence, promotion readiness, bankroll guidance, real-money authorization, or a reason to bypass ROI-complete paper-observation gates.
- Current posture still keeps `OP_DURABLE_K7` as the safest anchor, `CD_CORE_K8` as the primary OP/CD paper companion, and `OP_REFINED_K7` plus other Phase 8 rules in shadow/watch. Do not use this standalone engine to substitute `BAQ` for dormant `BEL` or widen the live combo universe.
- Validate this usage boundary with `python3 validate_ev_ticket_engine_usage.py`.
- If scorecard, rule, prediction-output, recommendation, signal-ledger, or settlement-ledger bytes changed before quoting `CURRENT_EVIDENCE_SUMMARY.*`, use `current_evidence_summary.json.rebuild_validation_contract`: run `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`. This is provenance/rebuild routing only, not EV-engine evidence, settled ROI, bankroll guidance, or real-money evidence.

## What changed

The project now has a first-pass expected-value ticket selector:

- `ev_ticket_engine.py` reads combo prediction CSVs and turns them into a paper-ticket plan.
- `NYRA/model_main.py` and `XGBoost/predict_single_race.py` now add EV columns directly to their output.
- Both prediction scripts also support `--sort-by ev` if you want the CSV and console output ranked by conservative expected value instead of raw probability.

## Why this matters

Before this, the project mainly answered:
- which combo is most likely
- what payout the model predicts

The new engine answers the harder question:
- should a paper lane log a hypothetical bet plan at all
- which tickets are best after a conservative payout haircut
- what hypothetical paper stake would fit simple source-layer caps

## Output columns added to prediction CSVs

- `adj_predicted_payout` — predicted payout after the default 25% haircut
- `expected_return_1` — expected return multiple on a $1 normalized payout basis
- `ev_profit_1` — expected profit multiple above stake
- `ev_roi_pct` — expected ROI percent
- `full_kelly_frac` — full-Kelly bankroll fraction for the ticket
- `value_rank` — rank by EV, highest first

## Recommended workflow

Preferred daily use is indirect: run `./run_daily_portfolio_observation.sh` and let the recommender call this engine after the current Phase 7 paper-basket filters. The direct commands below are for source-layer debugging or reproducibility checks, not real-money placement.

### 1) Generate race predictions

For live NYRA data:

```bash
python3 NYRA/model_main.py \
  --model Model/log_residual_model_normalized.json \
  --top-combinations 200 \
  --sort-by ev \
  --output out/nyra_race_predictions.csv
```

For a local race CSV:

```bash
python3 XGBoost/predict_single_race.py \
  --input path/to/race.csv \
  --model Model/log_residual_model_normalized.json \
  --top-combinations 200 \
  --sort-by ev \
  --output out/race_predictions.csv
```

## Important note on `--top-combinations`

For EV paper-ticket sizing, do **not** leave this tiny unless you intentionally want only the chalkiest set.

- `model_main.py` first scores the top Harville candidates, then ranks that scored set.
- If you only score 20 combos, the EV engine only sees those 20.
- Start around `200`, then push higher if runtime is acceptable.

## 2) Turn predictions into a paper bet / no-bet plan

Example with a $500 paper-accounting fixture and dime minimums:

```bash
python3 ev_ticket_engine.py \
  --input out/race_predictions.csv \
  --race-label "OP Paper Race 7" \
  --bankroll 500 \
  --ticket-increment 0.10 \
  --payout-unit 1.0 \
  --payout-haircut 0.75 \
  --kelly-fraction 0.25 \
  --min-ev-roi 0.15 \
  --min-prob 0.0005 \
  --max-tickets 4 \
  --max-race-risk 0.02 \
  --max-ticket-risk 0.0075 \
  --save-json out/race_plan.json \
  --save-csv out/race_plan.csv
```

## Default decision rule

A paper ticket is playable only if all of these are true:

- `jointProb >= 0.0005`
- conservative EV after payout haircut is at least `+15%`
- Kelly stake is positive
- the recommended stake still survives ticket and race risk caps

Default risk limits:

- bankroll = `$500` paper-accounting fixture default, not an authorized bankroll
- payout haircut = `25%`
- staking = `quarter Kelly`
- max race exposure = `2.0%` of bankroll
- max single-ticket exposure = `0.75%` of bankroll
- max tickets per race = `4`

## Interpretation

- `Decision: BET` means at least one hypothetical paper ticket survived all filters and caps.
- `Decision: NO BET` means the race is not good enough under the current assumptions.
- This is deliberate. Passing on weak races is part of the paper-observation discipline.

## Practical tuning ideas

If the engine is still too aggressive:
- increase `--payout-haircut` conservatism by lowering it, for example `0.65`
- raise `--min-ev-roi` to `0.25`
- reduce `--max-race-risk` to `0.01`
- reduce `--max-tickets` to `2`

If it is too restrictive:
- lower `--min-ev-roi` slightly
- allow more scored combinations upstream with `--top-combinations`
- increase bankroll or lower ticket minimum if your track supports dime supers

## Current limitations

This is intentionally a minimal working engine, not the final bankroll optimizer.

It does **not** yet:
- model correlation between overlapping tickets
- estimate pool impact / your own price slippage
- blend tote probable data directly into expected superfecta return
- optimize across many races at once

But it is already more disciplined than ranking paper tickets straight off raw payout predictions or raw combo likelihood.
