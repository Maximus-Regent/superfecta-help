# EV Ticket Engine Usage

## What changed

The project now has a first-pass expected-value ticket selector:

- `ev_ticket_engine.py` reads combo prediction CSVs and turns them into an actionable bet plan.
- `NYRA/model_main.py` and `XGBoost/predict_single_race.py` now add EV columns directly to their output.
- Both prediction scripts also support `--sort-by ev` if you want the CSV and console output ranked by conservative expected value instead of raw probability.

## Why this matters

Before this, the project mainly answered:
- which combo is most likely
- what payout the model predicts

The new engine answers the harder question:
- should we bet at all
- which tickets are best after a conservative payout haircut
- how much to stake under simple bankroll caps

## Output columns added to prediction CSVs

- `adj_predicted_payout` — predicted payout after the default 25% haircut
- `expected_return_1` — expected return multiple on a $1 normalized payout basis
- `ev_profit_1` — expected profit multiple above stake
- `ev_roi_pct` — expected ROI percent
- `full_kelly_frac` — full-Kelly bankroll fraction for the ticket
- `value_rank` — rank by EV, highest first

## Recommended workflow

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

For EV betting, do **not** leave this tiny unless you intentionally want only the chalkiest set.

- `model_main.py` first scores the top Harville candidates, then ranks that scored set.
- If you only score 20 combos, the EV engine only sees those 20.
- Start around `200`, then push higher if runtime is acceptable.

## 2) Turn predictions into a bet / no-bet plan

Example with a $500 bankroll and dime minimums:

```bash
python3 ev_ticket_engine.py \
  --input out/race_predictions.csv \
  --race-label "BEL Race 7" \
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

A ticket is playable only if all of these are true:

- `jointProb >= 0.0005`
- conservative EV after payout haircut is at least `+15%`
- Kelly stake is positive
- the recommended stake still survives ticket and race risk caps

Default risk limits:

- bankroll = `$500`
- payout haircut = `25%`
- staking = `quarter Kelly`
- max race exposure = `2.0%` of bankroll
- max single-ticket exposure = `0.75%` of bankroll
- max tickets per race = `4`

## Interpretation

- `Decision: BET` means at least one ticket survived all filters and caps.
- `Decision: NO BET` means the race is not good enough under the current assumptions.
- This is deliberate. Passing on weak races is part of the edge.

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

But it is already materially better than betting straight off raw payout predictions or raw combo likelihood.
