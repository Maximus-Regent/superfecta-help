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
- `out/live_demo/latest_demo_run.json` *(mutable convenience alias; later demo runs may repoint it)*

## Important distinction

### Production basket
`superfecta_ops.py` is still correct as a production wrapper for the OP/CD primary paper-basket target tracks:
- `ACTIVE_TRACKS = {"OP": "Oaklawn Park", "CD": "Churchill Downs"}`

So when it says no primary paper-basket target tracks today, it means:
- no valid `OP/CD` production fire today

It does **not** mean:
- no live race anywhere
- no demo possible
- no model/API path available

### Demo lane
`demo_live_predictions.py` is intentionally separate.
It exists to generate live predictions on cards that are actually available today, without pretending we changed the production strategy or basket.

What this does **not** mean:
- not a production-basket change
- not proof of betting profitability
- not a reason to treat Keeneland as a validated live deployment lane
- not new forward evidence for the OP/CD paper-trade case by itself; that still requires settled paper trades in the actual paper-trade lane

## Current paper-trade bridge

This dated report is demo-lane operability context. For current OP/CD paper totals, read `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` before quoting `PAPER_TRADE_NOW`, ops-bucket/operator-status context, settlement-audit, or ledger totals.

- source consistency: `matched`
- bridge rebuild order: `current_evidence_summary.json.rebuild_validation_contract`; after scorecard/rules/signals/settlement-ledger byte changes, run `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence
- combined operator read route: check `operator_status_context`, `source_freshness.requires_refresh_before_right_now_use=false`, and `operator_read_gate.requires_refresh_before_evidence_read=false`; the saved `PAPER_TRADE_NOW` best-action card is fresh against the bridge reference date but still goes through operator read-gate routing before instruction or evidence use
- operator read gate: `operator_read_gate.requires_refresh_before_evidence_read=false`; Saved top card can be read as current operator routing context with `python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv --rules phase7_current_paper_rules.json`, but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence.
- decision-gate source: `forward_evidence_scorecard.json` `decision_gate_minimums` sets `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100`; these are future ROI-complete observation floors, not cleared gates
- primary paper gate: `6/30` ROI-complete first-read rows and `6/100` broader-review rows
- current rule mix: `CD_CORE_K8` has `6` ROI-complete settled rows; `OP_DURABLE_K7` has `0` ROI-complete settled rows
- interpretation: current settled sample is CD-only context, not OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence
- direct cross-family caveat route: read `CROSS_FAMILY_DECISION.md` and run `python3 validate_cross_family_decision.py` when the question is whether the anchor / paper / watch shortlist still carries the current-paper caveat; stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green working-status validation are not OP-anchor proof or cross-family promotion evidence
- full-data XGBoost retrain caveat route: read `FULL_DATA_RETRAIN_ARTIFACTS.md` and run `python3 validate_full_data_retrain_artifacts.py` when checking the model lane's full-data retrain artifacts or exact retrain/prediction commands; large RMSE / MAE gains remain model-fit reproducibility context only, not paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence
- settlement queue state: `closed`; no open primary settlement rows; detail: Open settlement queue by rule: OP_DURABLE_K7 has 0 open row(s); CD_CORE_K8 has 0; other primary rules have 0; 0 open row(s) lack published rule IDs. Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence. Latest recommendation-state context: Latest run context: the latest live scan completed cleanly and found no qualifying races across 52 card(s) and 446 race(s). Treat this as operator context only; use recommendation and settlement ledgers before interpreting bet readiness or forward performance.
- if `source_consistency.overall_match=false`, repair source mismatch before using paper totals; then use the combined `operator_status_context` + `source_freshness` + `operator_read_gate` route before using the saved right-now card as current-day guidance or evidence

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

## Report-time verified demo snapshot

This is the report-time verified demo run from **2026-04-15**.
The dated Keeneland CSV/markdown files above are the stable evidence anchor for this note; `out/live_demo/latest_demo_run.json` is a mutable convenience alias and may point at a later demo run.

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
- The **demo result is an operability check, not an edge claim**
- **New forward evidence still requires settled paper trades in the actual paper-trade lane**

That is the corrected state.
