# Superfecta Working Status Report - 2026-04-15

## Honest bottom line

The core live prediction stack is working.

What was broken was the operational framing:
- `superfecta_ops.py` is a **production basket wrapper** for `OP` and `CD`
- I treated that like it meant **no live prediction path existed today**
- that was wrong

Today, the NYRA API is returning **Keeneland** cards and the existing model stack can generate live predictions on those races right now.

## What is actually working

### 1) Live card discovery through the NYRA API
Confirmed today:
- `list_cards()` returned live cards for `Keeneland`
- `list_races()` returned today’s race ladder
- upcoming races were available for Race 6, 7, and 8

### 2) Live race-level prediction generation
Confirmed today:
- `python3 NYRA/model_main.py --model Model/log_residual_model_normalized.json --race-id 102075970 --output out/demo_kee_r5.csv --sort-by ev --top-combinations 15`
- this completed successfully and wrote output

### 3) One-command demo wrapper for today’s available cards
Added:
- `demo_live_predictions.py`

Confirmed today:
- `python3 demo_live_predictions.py --include-cards keeneland --save-latest-json`
- selected the next available live/demo race automatically
- generated predictions for **Keeneland Race 6**
- wrote CSV + markdown report to `out/live_demo/`

## Files added

- `demo_live_predictions.py`
- `out/live_demo/keeneland_race6_20260415_151943.csv`
- `out/live_demo/keeneland_race6_20260415_151943.md`
- `out/live_demo/latest_demo_run.json`

## Important distinction

### Production basket
`superfecta_ops.py` is still correct as a production wrapper for the current active basket:
- `ACTIVE_TRACKS = {"OP": "Oaklawn Park", "CD": "Churchill Downs"}`

So when it says no active-basket target today, it means:
- no valid `OP/CD` production fire today

It does **not** mean:
- no live race anywhere
- no demo possible
- no model/API path available

### Demo lane
`demo_live_predictions.py` is intentionally separate.
It exists to generate live predictions on cards that are actually available today, without pretending we changed the production strategy or basket.

## Aqueduct / NYRA website note

Aqueduct website behavior was inconsistent across requests.
What I can say safely:
- earlier extracted content showed Aqueduct entries for April 15
- later direct requests with explicit day params showed `No race entries found` and `Racing returns Apr 16`
- the NYRA API path used by our code did **not** return Aqueduct today

So the clean move was to stop arguing about stale/inconsistent page state and use the track data the API is actually returning live today.

## Current demo command

```bash
cd "/Users/maximusregent_ai/Shared/Superfecta Help"
python3 demo_live_predictions.py --include-cards keeneland --save-latest-json
```

## Current result snapshot

Latest verified demo run:
- card: `Keeneland`
- race: `Race #6`
- race id: `102075971`
- post time: `2026-04-15T19:40:00Z`
- top combo: `5-7-10-2`
- top combo predicted payout: `$182.75`
- top combo EV ROI: `-30.66%`

## What this means operationally

- The **model lane works**
- The **API lane works**
- The **demo lane works today**
- The **production OP/CD basket is still unchanged**

That is the corrected state.
