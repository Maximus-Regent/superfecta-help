# Live Portfolio Scanner — Usage

## Quick start

```bash
# Default scan — fetches today's cards, applies the broader Phase 7 ruleset
python3 live_portfolio_scanner.py

# Conservative forward-evidence scan — OP anchor only
python3 live_portfolio_scanner.py --rules op_anchor_rules.json

# Offline mode — cached data only, no API calls
python3 live_portfolio_scanner.py --rules op_anchor_rules.json --cache-only

# Filter to specific tracks (substring match)
python3 live_portfolio_scanner.py --include-cards belmont churchill

# Cap API calls (useful when rate-limited)
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

- For the most conservative live-paper workflow, prefer `--rules op_anchor_rules.json`.
- That keeps the scanner aligned with the forward-evidence ranking: `OP_DURABLE_K7` is the safest active anchor, while BEL is dormant and Phase 8 small-sample winners remain watch-list material.
- Use the default `phase7_live_rules.json` when you want broader research coverage rather than the safest deployment-style scan.

## All flags

| Flag | Default | Description |
|------|---------|-------------|
| `--rules PATH` | `phase7_live_rules.json` | Path to rules file |
| `--base-stake N` | `1.0` | Base stake per superfecta combo |
| `--emit-combos` | off | Print all ticket permutations |
| `--json` | off | JSON output |
| `--save PATH` | — | Save hits to `.json` or `.csv` |
| `--status-json PATH` | `out/live_scan_latest.status.json` | Save machine-readable run status |
| `--include-cards` | all | Substring filters for card names |
| `--max-races N` | 0 (unlimited) | Max race-detail attempts, including skipped cache-only misses |
| `--cache-only` | off | No API calls — cached data only |
| `--cache-ttl N` | 0 | Reuse cache younger than N seconds |
| `--discord` | off | Discord-formatted text output |
| `--discord-webhook` | off | Full Discord webhook JSON |
| `--no-dedup` | off | Skip duplicate alert filtering |

## Cron setup

Use `scan_live.sh` for cron — it handles logging and errors:

```cron
# Every 30 minutes during race hours (noon–7pm ET), Mon–Sat
*/30 12-19 * * 1-6 /path/to/scan_live.sh --discord >> /path/to/scan.log 2>&1
```

## Rate limiting

The NYRA API returns HTTP 429 when called too aggressively. The scanner handles this with:

1. **Retry with backoff** — 429 triggers a 30-second pause, 5xx errors use exponential backoff
2. **Cache fallback** — if all retries fail, stale cached data is used (with a warning)
3. **`--cache-ttl`** — avoids re-fetching data that was just fetched (e.g. `--cache-ttl 300` = 5 min)
4. **`--max-races`** — hard cap on the number of race-detail attempts per run, including cache-only misses
5. **Date-stamped cache** — cache files include today's date, preventing cross-day staleness

If the API is persistently rate-limited, use `--cache-only` to work from previously cached data.

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
