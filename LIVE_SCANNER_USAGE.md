# Live Portfolio Scanner — Usage

## Current Evidence Boundary

- This is a live paper-alert scanner runbook, not a live betting, promotion, bankroll, or real-money guide.
- Valid evidence scope: `valid_evidence_scope=live_scanner_usage_paper_alert_runbook_navigation_only`.
- The preferred daily observation path remains `./run_daily_portfolio_observation.sh`, which uses current primary and shadow rule files, writes operator summaries, and keeps settlement rows separate from scanner output.
- Scanner hits, Discord alerts, saved alert files, clean empty scans, capped `--max-races` scans, cache-only scans, API access failures such as HTTP 403, or validator passes are operational routing metadata only. They are not settled ROI, live profitability evidence, promotion readiness, OP-anchor replacement evidence, or real-money authorization.
- Scanner status sidecars and non-empty scanner JSON hit rows now publish `valid_evidence_scope=live_scanner_paper_alert_metadata_only`, `evidence_boundary`, and `evidence_boundary_text`; human and Discord output render the same boundary line. These fields are copy-safety metadata only, not a paper-review gate.
- Current posture still keeps `OP_DURABLE_K7` as the safest anchor, `CD_CORE_K8` as the primary OP/CD paper companion, and `OP_REFINED_K7` plus other Phase 8 rules in shadow/watch. Dormant `BEL` must not be replaced with `BAQ`.
- Validate this usage boundary with `python3 validate_live_scanner_usage.py`.
- If the question is whether the main status document / repo map still exposes the base API-access / HTTP 403 status-summary action-recheck route before lane enrichment, read `COLE_STATUS_AND_PLAN.md` and run `python3 validate_cole_status_and_plan.py`; the named check is `status_doc_base_api_access_route_documented`.
- If scorecard, rule, scanner-output, signal-ledger, or settlement-ledger bytes changed before quoting `CURRENT_EVIDENCE_SUMMARY.*`, use `current_evidence_summary.json.rebuild_validation_contract`: run `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`. This is provenance/rebuild routing only, not scanner evidence or settled ROI.

## Quick start

```bash
# Research-coverage scan — fetches today's cards, applies the broader Phase 7 ruleset
python3 live_portfolio_scanner.py

# Conservative forward-evidence scan — OP anchor only
python3 live_portfolio_scanner.py --rules op_anchor_rules.json

# Offline mode — cached data only, no API calls
python3 live_portfolio_scanner.py --rules op_anchor_rules.json --cache-only

# Filter to current primary paper-basket tracks (substring match)
python3 live_portfolio_scanner.py --include-cards oaklawn churchill

# Cap candidate race-detail attempts after rule-card/race-number prefiltering (useful when rate-limited)
python3 live_portfolio_scanner.py --max-races 10

# Discord-ready alert text
python3 live_portfolio_scanner.py --discord

# Full Discord webhook JSON payload
python3 live_portfolio_scanner.py --discord-webhook

# Save results
python3 live_portfolio_scanner.py --save alerts.json
python3 live_portfolio_scanner.py --save alerts.csv
```

## Recommended mode

- For the most conservative current-paper scanner workflow, prefer `--rules op_anchor_rules.json`.
- That keeps the scanner aligned with the forward-evidence ranking: `OP_DURABLE_K7` is the safest current paper anchor, while BEL is dormant and Phase 8 small-sample winners remain watch-list material.
- For the current primary OP/CD paper-basket scan, use `--rules phase7_current_paper_rules.json`.
- In that current basket, `CD_CORE_K8` is the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion.
- `OP_REFINED_K7` remains in the Phase 8 shadow/watch lane for observation only; scanner hits, clean empty scans, capped scans, or validator passes are not settled ROI, live profitability, promotion readiness, or real-money evidence.
- Use the default `phase7_live_rules.json` only when you want broader research coverage rather than the safest current-paper scan.

## All flags

| Flag | Default | Description |
|------|---------|-------------|
| `--rules PATH` | `phase7_live_rules.json` | Path to rules file |
| `--base-stake N` | `1.0` | Paper-accounting base stake per superfecta combo; not bankroll guidance |
| `--emit-combos` | off | Print all ticket permutations |
| `--json` | off | JSON output |
| `--save PATH` | — | Save hits to `.json` or `.csv` |
| `--status-json PATH` | `out/live_scan_latest.status.json` | Save machine-readable run status |
| `--include-cards` | all | Substring filters for card names |
| `--max-races N` | 0 (unlimited) | Max candidate race-detail attempts after rule-card/race-number prefiltering, including skipped cache-only misses |
| `--cache-only` | off | No API calls — cached data only |
| `--cache-ttl N` | 0 | Reuse cache younger than N seconds |
| `--discord` | off | Discord-formatted text output |
| `--discord-webhook` | off | Full Discord webhook JSON |
| `--no-dedup` | off | Skip duplicate alert filtering |

## Cron setup

Use `scan_live.sh` for paper-alert cron monitoring — it handles logging and errors, but it does not settle rows or authorize real-money betting:

```cron
# Every 30 minutes during race hours (noon–7pm ET), Mon–Sat
*/30 12-19 * * 1-6 /path/to/scan_live.sh --discord >> /path/to/scan.log 2>&1
```

## API Limits And Access Failures

The NYRA API returns HTTP 429 when called too aggressively. The scanner handles this with:

1. **Retry with backoff** — 429 triggers a 30-second pause, 5xx errors use exponential backoff
2. **Cache fallback** — if all retries fail, stale cached data is used (with a warning)
3. **`--cache-ttl`** — avoids re-fetching data that was just fetched (e.g. `--cache-ttl 300` = 5 min)
4. **Rule-card prefilter + `--max-races`** — the scanner first skips races that cannot match the rules by card name and minimum race number, then applies the hard cap to candidate race-detail attempts, including cache-only misses
5. **Date-stamped cache** — cache files include today's date, preventing cross-day staleness

If the API is persistently rate-limited, use `--cache-only` to work from previously cached data.

If the API returns HTTP 403 Forbidden or another access failure before cards/races can be fetched, treat the run as `scanner_error` / API-unreachable operator context. Do not treat it as a no-target day, a clean empty scan, or forward-performance evidence. Inspect the scanner status sidecar, follow its `api_failure_operator_action=refresh_daily_wrapper_before_evidence_read` / `api_failure_recheck_command=./run_daily_portfolio_observation.sh` fields, or use `--cache-only` only as explicitly partial/stale operational context.

In `--cache-only` mode, the scanner now falls back to the latest same-day cache for cards/races when the exact cache key is missing, and it skips uncached race-detail files instead of aborting the whole run. That makes offline paper-trade checks much more operational, but it also means a cache-only run may be partial if only some races were cached.

## Duplicate detection

By default, the scanner tracks which alerts have already been emitted today in `.live_scan_alerts.json`. Re-running the scanner will only show new alerts. Use `--no-dedup` to see all qualifying races regardless.

The ledger auto-resets each day.

## Machine-readable status

When you pass `--status-json` (or use the default wrapper path), the scanner writes a JSON sidecar with counts and a `result` field.

Useful `result` values:
- `alerts_found`
- `no_qualifiers`
- `partial_cache_alerts`
- `partial_cache_no_qualifiers`
- `duplicate_only`
- `scanner_error`

`partial_cache_*` means the scanner had to skip one or more race-detail files in `--cache-only` mode, so an empty run should be treated as incomplete rather than as strong evidence that no races qualified.

The status sidecar also publishes `valid_evidence_scope=live_scanner_paper_alert_metadata_only`, `evidence_boundary`, `evidence_boundary_text`, `target_card_count`, `target_race_count`, `detail_fetch_scope=rule_card_and_min_race_prefilter`, `pre_detail_skipped_race_count`, `race_details_attempted`, `max_race_limit_hit`, `unattempted_target_race_count`, and `full_target_coverage_min_races`. Non-empty scanner JSON hit rows carry the same evidence-boundary fields. For API failures it publishes `http_status`, `api_failure_class`, `api_failure_valid_scope`, `api_failure_boundary`, `api_failure_operator_action`, and `api_failure_recheck_command` so operator tooling can route the run without parsing prose. A no-hit run with `max_race_limit_hit=true` is operationally limited coverage, not a clean forward observation; if `unattempted_target_race_count` is above zero, raise `--max-races` to at least `full_target_coverage_min_races` or rerun before treating it like a true zero-hit day.

## Files

| File | Purpose |
|------|---------|
| `live_portfolio_scanner.py` | Main scanner |
| `phase7_live_rules.json` | Rule definitions |
| `scan_live.sh` | Cron-safe shell wrapper |
| `out/live_scan_latest.status.json` | Machine-readable scanner status sidecar |
| `.live_scan_cache/` | Cached API responses (date-stamped) |
| `.live_scan_alerts.json` | Duplicate alert ledger |
| `logs/` | Daily log files from `scan_live.sh` |
