# Paper Trade Flow

## What it does

This adds a persistent paper-trade recommendation pipeline on top of the live scanner.

Flow:
1. `paper_trade_pipeline.py` runs the explicit pipeline.
2. `scan_live.sh` runs the hardened live scanner with safe defaults.
3. Scanner saves the latest JSON output to `out/live_scan_latest.json`.
4. `paper_trade_recommender.py` scores each qualifying `race_id` with `NYRA/model_main.py --race-id`.
5. The recommender keeps only Phase 7-style key-favorite combos, then applies `ev_ticket_engine.py` bankroll sizing.
6. `paper_trade_logger.py` appends both the raw signal and the recommendation summary into persistent ledgers.
7. Duplicate signals across reruns are ignored.

## Files

- `paper_trade_pipeline.py` — explicit scan -> score -> EV filter -> log orchestrator
- `run_paper_trade_cycle.sh` — one-shot scan + log cycle
- `run_daily_portfolio_observation.sh` — run the primary current-paper basket and the shadow watch-list basket back to back
- `paper_trade_recommender.py` — scan hit -> model scoring -> EV-sized paper-trade plan
- `paper_trade_logger.py` — append-only signal logger
- `paper_trade_status_summary.py` — turn status sidecars into a one-line report-safe summary
- `paper_trade_settlement_sync.py` — keep a settlement template ledger in sync with the signal ledger
- `paper_trade_settlement_helper.py` — list open settlement rows and mark one `signal_key` settled without hand-editing CSV
- `paper_trade_forward_check.py` — compare settled forward observations against frozen hit-rate and flat-ticket ROI baselines when settlement values exist
- `paper_trade_lane_monitor.py` — combine the forward read plus pending settlement queue into one compact lane summary
- `paper_trade_next_steps.py` — turn each lane state into the exact next 2-3 commands to run
- `paper_trade_preflight_note.py` — write a one-line race-calendar note so empty days can say whether OP / CD were even active
- `paper_trade_ops_history.py` — roll recent daily runs into one ops log so quiet stretches can be separated into no-target days, clean no-qualifier days, and failures
- `phase7_current_paper_rules.json` — active Phase 7 paper basket (OP + CD, with dormant BEL removed)
- `phase8_shadow_rules.json` — Phase 8 watch-list basket for shadow logging only
- `paper_trades/paper_trade_signals.csv` — persistent ledger
- `paper_trades/paper_trade_recommendations.csv` — persistent recommendation ledger
- `paper_trades/.logged_signals.json` — dedup state

## Usage

```bash
# Most honest live-paper start: OP anchor only
./run_paper_trade_cycle.sh --rules op_anchor_rules.json

# Current active portfolio paper basket: OP + CD (BEL removed because it is dormant)
./run_paper_trade_cycle.sh --rules phase7_current_paper_rules.json

# Daily primary + shadow run in one command
./run_daily_portfolio_observation.sh

# Broader Phase 7 research scan (includes CD and dormant BEL)
./run_paper_trade_cycle.sh

# Restrict to target cards if needed
./run_paper_trade_cycle.sh --rules op_anchor_rules.json --include-cards oaklawn

# Cache-only / offline replay
./run_daily_portfolio_observation.sh --cache-only

# Use more local CPU on multi-race days
./run_daily_portfolio_observation.sh --workers 0 --threads 1
```

## Recommended deployment order

- Start with `op_anchor_rules.json` when the goal is the single safest active entrypoint.
- Use `phase7_current_paper_rules.json` when the goal is the **current primary paper basket**. That reflects the current operational reality of Phase 7: active OP + CD, with BEL removed because it has no current forward races.
- Use `run_daily_portfolio_observation.sh` when you want the clean daily routine: run the current primary paper basket first, then the Phase 8 shadow basket, and write separate ledgers plus one-line summaries for each.
- Keep `phase8_shadow_rules.json` in shadow mode only. It is for forward observation, not promotion.
- Use the default `phase7_live_rules.json` only when you explicitly want the original broader research basket. It still includes dormant BEL and is not the clearest live-paper entrypoint.

### Daily primary vs shadow runner

`run_daily_portfolio_observation.sh` is the cleanest operational wrapper now.

What it does:
- runs `phase7_current_paper_rules.json` first as the **primary** current paper basket
- runs `phase8_shadow_rules.json` second as the **shadow** watch-list basket
- keeps ledgers and dedup state separate by basket
- syncs a per-lane settlement ledger template so every new signal has a place for final outcome / return values
- writes one-line status, forward-check, lane-monitor, and next-steps summaries for each lane plus a combined `daily_summary.txt`
- writes a shared preflight note once per run, so the daily output can say when there were no active OP / CD cards instead of implying the rules simply missed
- refreshes a rolling `OPS_HISTORY.md` / `ops_history.csv` view after each run, so recent quiet days can be interpreted without opening one date folder at a time
- adds a small "Quick jump index" to `daily_summary.txt` plus per-lane "Quick files" blocks so the combined summary points directly at the right `OPS_HISTORY.md`, `preflight_note.txt`, `next_steps.md`, `lane_monitor.md`, `forward_check.md`, and settlement ledger paths

Artifacts land under:
- `OPS_HISTORY.md`
- `ops_history.csv`
- `out/daily_portfolio_runs/YYYY-MM-DD/preflight_note.txt`
- `out/daily_portfolio_runs/YYYY-MM-DD/preflight_note.json`
- `out/daily_portfolio_runs/YYYY-MM-DD/phase7_current_paper/`
- `out/daily_portfolio_runs/YYYY-MM-DD/phase8_shadow/`
- `out/daily_portfolio_runs/YYYY-MM-DD/daily_summary.txt`

Per-lane monitor artifacts:
- `lane_monitor.txt`
- `lane_monitor.md`
- `next_steps.txt`
- `next_steps.md`

Settlement ledgers land under:
- `paper_trades/phase7_current_paper_paper_trade_settlements.csv`
- `paper_trades/phase8_shadow_paper_trade_settlements.csv`

### Forward expectation check

After outcomes start getting filled into the signal ledger, use `paper_trade_forward_check.py` to compare observed hit rate against the frozen 2024-2025 holdout baselines.

```bash
# Current primary paper basket
python3 paper_trade_forward_check.py \
  --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv \
  --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv \
  --rules phase7_current_paper_rules.json \
  --output out/paper_trade_forward_check_current.md

# Shadow basket
python3 paper_trade_forward_check.py \
  --signals-ledger paper_trades/phase8_shadow_paper_trade_signals.csv \
  --recommendation-ledger paper_trades/phase8_shadow_paper_trade_recommendations.csv \
  --rules phase8_shadow_rules.json \
  --output out/paper_trade_forward_check_shadow.md
```

Current scope:
- checks hit rate first, because that is the cleanest forward metric in the current ledger
- also checks flat-ticket ROI when the settlement ledger has `actual_return` values
- labels each lane or rule as `NO DATA`, `TOO EARLY`, `WITHIN EXPECTED NOISE`, `RUNNING COLD`, or `RUNNING HOT`
- uses the frozen holdout rows as the baseline, not flattering full-sample numbers

Rolling ops history:

```bash
python3 paper_trade_ops_history.py
```

What it adds:
- one rolling view across recent `out/daily_portfolio_runs/YYYY-MM-DD/` folders
- a clear split between `NO TARGETS`, `CLEAN EMPTY`, and operational issue days
- a compact daily table plus CSV export for report-safe ops debugging
- gets refreshed automatically by `run_daily_portfolio_observation.sh`

Settlement convention:
- `paper_trade_settlement_sync.py` pre-populates one settlement row per `signal_key`
- simplest settlement convention is `settlement_status=settled`, `outcome=HIT` or `MISS`, and `actual_return=<dollars returned>`
- if `actual_cost` is left blank, the checker falls back to the scanner's estimated ticket cost for flat-ticket ROI

Settlement helper:

```bash
# See which rows still need results entered
python3 paper_trade_settlement_helper.py list-open \
  --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv

# Mark one row settled without opening the CSV manually
python3 paper_trade_settlement_helper.py settle \
  --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv \
  --signal-key '<signal_key>' \
  --outcome HIT \
  --actual-return 480.00 \
  --actual-cost 120.00 \
  --settled-ts 2026-04-15T19:30:00 \
  --notes 'manual settlement entry'
```

The helper keeps the workflow small and explicit:
- `list-open` shows the pending queue with `signal_key`, rule, track, race, and expected cost
- `settle` updates exactly one row and recomputes `actual_profit` when `actual_cost` is provided
- after settlement entry, rerun `paper_trade_forward_check.py` to refresh the forward report

Lane monitor:

```bash
python3 paper_trade_lane_monitor.py \
  --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv \
  --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv \
  --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv \
  --rules phase7_current_paper_rules.json
```

What it adds:
- one compact read of the current forward assessment
- a short queue of still-open settlement rows
- a clearer "what should I do next?" note for each lane

Next-steps helper:

```bash
python3 paper_trade_next_steps.py \
  --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv \
  --recommendation-ledger paper_trades/phase7_current_paper_paper_trade_recommendations.csv \
  --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv \
  --rules phase7_current_paper_rules.json
```

What it adds:
- converts lane state into an explicit `NEEDS SETTLEMENT`, `WAITING FOR FIRST SETTLED RACES`, `COLLECTING SAMPLE`, or `DECISION-GRADE REVIEW` label
- prints the exact next 2-3 commands instead of a generic reminder
- prefers short repo-relative commands when the files live inside this project, so the daily summaries stay readable
- can surface recent run context from the scanner/pipeline status sidecars, for example distinguishing a clean empty run from a partial-cache or scanner-failure empty run
- can also surface a shared preflight note, for example `no active-basket tracks (OP / CD) are racing today`, so empty lanes are easier to interpret honestly
- gets written automatically as `next_steps.txt` and `next_steps.md` by `run_daily_portfolio_observation.sh`

Direct orchestrator usage:

```bash
# Explicit pipeline entrypoint, conservative OP anchor mode
python3 paper_trade_pipeline.py --rules op_anchor_rules.json

# Explicit pipeline entrypoint, broader Phase 7 research mode
python3 paper_trade_pipeline.py

# Parallel scoring fast path for multi-race days
python3 paper_trade_pipeline.py --workers 0 --threads 1

# Reuse an existing scanner JSON and existing predictions
python3 paper_trade_pipeline.py \
  --skip-scan \
  --scan-input out/sample_inputs/live_scan_sample.json \
  --recommendation-output-dir out/paper_trade_sample_run \
  --reuse-predictions \
  --ledger out/paper_trade_sample_run/paper_trade_signals.csv \
  --state out/paper_trade_sample_run/.logged_signals.json \
  --recommendation-ledger out/paper_trade_sample_run/paper_trade_recommendations.csv \
  --recommendation-state out/paper_trade_sample_run/.logged_recommendations.json
```

## Artifacts

- `out/live_scan_latest.json` — latest qualifying scanner hits
- `out/live_scan_latest.status.json` — machine-readable scanner status sidecar
- `out/paper_trade_pipeline_status.json` — machine-readable pipeline status sidecar
- `out/paper_trade_recommendations_latest/predictions/` — per-race model scoring CSVs
- `out/paper_trade_recommendations_latest/plans/` — per-race EV plan JSON/CSV
- `out/paper_trade_recommendations_latest/recommendations_summary.{json,csv,txt}` — consolidated recommendation output

### Status sidecars

Use the JSON sidecars when a run is empty and you need to know why.

Scanner status (`*.status.json`) now distinguishes cases like:
- `alerts_found`
- `no_qualifiers`
- `partial_cache_no_qualifiers`
- `duplicate_only`
- `scanner_error`

Pipeline status (`paper_trade_pipeline_status.json`) adds wrapper context such as:
- `scanner_failed`
- `reused_input_with_hits`
- `reused_input_empty`
- `observation_result` (`scanner_failed_empty_run`, `partial_cache_empty_run`, `clean_empty_run`, `bets_ready`, `signals_logged_no_bet`)
- recommendation counts (`BET`, `NO BET`, `ERROR`)

This is the fastest way to tell the difference between a real no-signal day, a partial offline replay, and an actual pipeline failure.

If you want a quick human-readable summary instead of opening JSON directly:

```bash
python3 paper_trade_status_summary.py
python3 paper_trade_status_summary.py \
  --scanner-status out/status_validation/partial_scan.status.json
```

Example output:
- `OP anchor run 2026-04-15T01:18:56: partial cache, 0 scanner hit(s), 3 missing race detail cache file(s), max-races cap hit after 3 attempt(s)`

## Explicit run path

Input: `out/live_scan_latest.json` or another scanner JSON passed via `--scan-input`

Scoring: `paper_trade_recommender.py` calls `NYRA/model_main.py --race-id <race_id> --output <prediction_csv>`

EV filtering and sizing: `paper_trade_recommender.py` narrows those scored combos to the scanner's Phase 7 ticket universe, then calls `ev_ticket_engine.build_race_plan`

Final recommended tickets: `out/paper_trade_recommendations_latest/recommendations_summary.csv`

Persistent ledger append: `paper_trade_logger.py` writes raw hits to `paper_trades/paper_trade_signals.csv` and recommendation rows to `paper_trades/paper_trade_recommendations.csv`

## Offline proof path

If there are no live hits or the current cache is incomplete, use the bundled local sample:

```bash
python3 paper_trade_pipeline.py \
  --skip-scan \
  --scan-input out/sample_inputs/live_scan_sample.json \
  --recommendation-output-dir out/paper_trade_sample_run \
  --reuse-predictions \
  --ledger out/paper_trade_sample_run/paper_trade_signals.csv \
  --state out/paper_trade_sample_run/.logged_signals.json \
  --recommendation-ledger out/paper_trade_sample_run/paper_trade_recommendations.csv \
  --recommendation-state out/paper_trade_sample_run/.logged_recommendations.json
```

That path uses:
- sample scanner hit: `out/sample_inputs/live_scan_sample.json`
- sample scored combos: `out/paper_trade_sample_run/predictions/race_SAMPLE_BEL_R8_predictions.csv`
- generated ticket plan: `out/paper_trade_sample_run/plans/race_SAMPLE_BEL_R8_plan.csv`
- generated summary: `out/paper_trade_sample_run/recommendations_summary.csv`

## Parallel scoring note

`paper_trade_recommender.py` can now score distinct race IDs concurrently.

- `--workers 1` keeps the old serial behavior.
- `--workers 0` auto-sizes workers from local CPU count and `--threads`.
- Keep `--threads 1` when using multiple workers, so CPU is spread across races instead of oversubscribing one race.
- Repeated hits for the same `race_id` reuse one prediction file instead of re-scoring the same race twice.

## Current limitation

This is still a thin integration layer. If live API access or a model score fails for a qualifying race, that race is recorded as `ERROR` or `NO BET` in the recommendation summary instead of silently disappearing.
