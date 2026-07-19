#!/usr/bin/env python3
"""
Live scanner for the configured superfecta portfolio rules.

Uses the existing racing API helpers in NYRA/ to fetch today's cards, races,
and runners, then applies whichever frozen rules JSON you pass in.

Features:
  - Retry with exponential backoff (handles 429 / 5xx gracefully)
  - Date-stamped JSON cache with configurable TTL
  - --cache-only offline mode (no API calls)
  - Rule-targeted race-detail fetching before --max-races caps API load
  - Substring card-name matching via --include-cards
  - Duplicate alert detection via a ledger file
  - --discord output mode (webhook-ready)
"""

import argparse
import hashlib
import json
import time
from datetime import date, datetime
from itertools import permutations
from math import perm
from pathlib import Path
from typing import Any, Optional
import sys

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "NYRA"))

from list_cards import list_cards
from list_races import list_races
from get_races import get_race_detail

DEFAULT_RULES_PATH = BASE / "phase7_live_rules.json"
DEFAULT_STATUS_PATH = BASE / "out" / "live_scan_latest.status.json"
CACHE_DIR = BASE / ".live_scan_cache"
ALERT_LEDGER = BASE / ".live_scan_alerts.json"
FAST_CONDITIONS = {"FAST", "FIRM"}
ACTIVE_RUNNER_STATUSES = {1, "1", None}
RUN_STATS: dict[str, int] = {}
API_ACCESS_STATUS_CODES = {401, 403}
API_FAILURE_BOUNDARY_TEXT = (
    "API-access-failure operator context only; not a no-target, clean-empty, "
    "forward-performance, settled ROI, promotion, live-profitability, bankroll, "
    "or real-money evidence."
)
API_FAILURE_OPERATOR_ACTION = "refresh_daily_wrapper_before_evidence_read"
API_FAILURE_RECHECK_COMMAND = "./run_daily_portfolio_observation.sh"
SCANNER_VALID_EVIDENCE_SCOPE = "live_scanner_paper_alert_metadata_only"
SCANNER_EVIDENCE_BOUNDARY_TEXT = (
    "live scanner output is source-layer paper-alert metadata only; it is not settled ROI evidence, "
    "not live-profitability evidence, not promotion readiness, not OP-anchor replacement evidence, "
    "not Phase 8 promotion evidence, not bankroll guidance, and not real-money support."
)
SCANNER_EVIDENCE_BOUNDARY_METADATA = {
    "artifact_role": "live portfolio scanner output",
    "valid_evidence_scope": SCANNER_VALID_EVIDENCE_SCOPE,
    "source_scope": "current API/cache race-card scan plus frozen rule filters; not settlement ledger or forward ROI evidence",
    "current_day_scanner_result_only": True,
    "not_live_paper_trade_ledger": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_anchor_change_evidence": True,
    "not_phase8_promotion_evidence": True,
    "not_bankroll_guidance": True,
    "not_real_money_evidence": True,
    "baq_as_bel_substitution_allowed": False,
    "stronger_forward_confidence_requires": [
        "paper-trade logger append",
        "settlement template sync",
        "actual result, return, cost, and settled_ts completion",
        "settlement audit or forward-check review before ROI-complete sample gates advance",
    ],
}
BEL_ALIAS_EXCLUSION_TOKENS = (
    "BAQ",
    "BIG A",
    "AQUEDUCT",
    "BELMONT AT THE BIG A",
    "BELMONT PARK AT THE BIG A",
    "BELMONT PARK AT AQUEDUCT",
)


def reset_run_stats() -> None:
    RUN_STATS.clear()
    RUN_STATS.update({
        "cards_fallback_uses": 0,
        "races_fallback_uses": 0,
        "stale_cache_fallback_count": 0,
        "stale_cache_fallback_applied": False,
        "missing_race_detail_cache_skips": 0,
        "race_details_attempted": 0,
        "race_details_loaded": 0,
        "max_race_limit_hit": 0,
        "pre_detail_skipped_race_count": 0,
    })


def target_coverage_counts(target_race_count: int, race_details_attempted: int) -> dict[str, int]:
    """Return machine-readable coverage counts for rule-targeted race-detail attempts."""
    target_count = max(0, int(target_race_count or 0))
    attempted_count = max(0, int(race_details_attempted or 0))
    return {
        "full_target_coverage_min_races": target_count,
        "unattempted_target_race_count": max(0, target_count - attempted_count),
    }

# ---------------------------------------------------------------------------
# Retry / backoff
# ---------------------------------------------------------------------------

MAX_RETRIES = 3
BACKOFF_BASE = 2.0  # seconds
BACKOFF_429 = 30.0  # longer pause for rate limits


def _call_with_retry(fn, *args, label: str = "API") -> Any:
    """Call *fn* with positional *args*, retrying on transient failures."""
    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args)
        except Exception as exc:
            last_exc = exc
            status = _extract_status(exc)
            if status == 429:
                wait = BACKOFF_429
                _log(f"[rate-limit] 429 on {label}, waiting {wait}s (attempt {attempt + 1}/{MAX_RETRIES})")
            elif status and status >= 500:
                wait = BACKOFF_BASE * (2 ** attempt)
                _log(f"[server-error] {status} on {label}, retrying in {wait:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
            elif status and 400 <= status < 500:
                # Client error other than 429 — don't retry
                raise
            else:
                wait = BACKOFF_BASE * (2 ** attempt)
                _log(f"[error] {label}: {exc}, retrying in {wait:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
            time.sleep(wait)
    raise last_exc  # type: ignore[misc]


def _extract_status(exc: Exception) -> Optional[int]:
    """Try to pull an HTTP status code out of a requests exception."""
    resp = getattr(exc, "response", None)
    if resp is not None:
        return getattr(resp, "status_code", None)
    return None


def scanner_failure_metadata(exc: BaseException) -> dict[str, Any]:
    """Return stable machine-readable metadata for scanner failures."""
    status = _extract_status(exc) if isinstance(exc, Exception) else None
    failure_class = "scanner_exception"
    if status == 429:
        failure_class = "api_rate_limit"
    elif status in API_ACCESS_STATUS_CODES:
        failure_class = "api_access_failure"
    elif status is not None and 400 <= status < 500:
        failure_class = "api_client_error"
    elif status is not None and status >= 500:
        failure_class = "api_server_error"

    return {
        "http_status": status,
        "api_failure_class": failure_class,
        "api_access_failure": failure_class == "api_access_failure",
        "api_rate_limited": failure_class == "api_rate_limit",
        "api_client_error": bool(status is not None and 400 <= status < 500),
        "api_server_error": bool(status is not None and status >= 500),
        "api_failure_valid_scope": "operator_refresh_context_only",
        "api_failure_boundary": API_FAILURE_BOUNDARY_TEXT,
        "api_failure_operator_action": API_FAILURE_OPERATOR_ACTION if failure_class == "api_access_failure" else "",
        "api_failure_recheck_command": API_FAILURE_RECHECK_COMMAND if failure_class == "api_access_failure" else "",
    }


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  {ts}  {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Caching (date-stamped, TTL-aware)
# ---------------------------------------------------------------------------

def _today_str() -> str:
    return date.today().isoformat()


def cache_path(kind: str, key: str) -> Path:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{_today_str()}_{kind}_{digest}.json"


def latest_cache_path(kind: str) -> Optional[Path]:
    """Return the newest cache file for *kind* from today, if any."""
    candidates = sorted(
        CACHE_DIR.glob(f"{_today_str()}_{kind}_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def cached_call(kind: str, key: str, fn, *args, cache_only: bool = False, cache_ttl: int = 0) -> Any:
    """Fetch via *fn* with caching.

    - If *cache_only*, never call the API; raise if no cache exists.
    - If *cache_ttl* > 0 and a cache file younger than *cache_ttl* seconds
      exists, return it without calling the API.
    """
    path = cache_path(kind, key)

    # Return fresh-enough cache without hitting the network
    if path.exists():
        age = time.time() - path.stat().st_mtime
        if cache_only or (cache_ttl > 0 and age < cache_ttl):
            return json.loads(path.read_text(encoding="utf-8"))

    if cache_only:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        if kind in {"cards", "races"}:
            fallback = latest_cache_path(kind)
            if fallback is not None:
                RUN_STATS[f"{kind}_fallback_uses"] = RUN_STATS.get(f"{kind}_fallback_uses", 0) + 1
                _log(
                    f"[cache-only] Exact cache miss for {kind}/{key[:24]}, "
                    f"using latest {fallback.name}"
                )
                return json.loads(fallback.read_text(encoding="utf-8"))
        raise SystemExit(f"[cache-only] No cached data for {kind}/{key} — run without --cache-only first.")

    try:
        data = _call_with_retry(fn, *args, label=f"{kind}/{key[:24]}")
        path.write_text(json.dumps(data), encoding="utf-8")
        return data
    except Exception as exc:
        if path.exists():
            RUN_STATS[f"{kind}_fallback_uses"] = RUN_STATS.get(f"{kind}_fallback_uses", 0) + 1
            RUN_STATS["stale_cache_fallback_count"] = RUN_STATS.get("stale_cache_fallback_count", 0) + 1
            RUN_STATS["stale_cache_fallback_applied"] = True
            RUN_STATS["stale_cache_fallback_kind"] = kind
            RUN_STATS["stale_cache_fallback_key_prefix"] = key[:24]
            RUN_STATS["stale_cache_fallback_error_type"] = exc.__class__.__name__
            RUN_STATS["stale_cache_fallback_error"] = str(exc)
            RUN_STATS.update(scanner_failure_metadata(exc))
            _log(f"[fallback] Using stale cache for {kind}/{key[:24]}")
            return json.loads(path.read_text(encoding="utf-8"))
        raise


# ---------------------------------------------------------------------------
# Name matching
# ---------------------------------------------------------------------------

def normalize_name(s: str) -> str:
    return " ".join((s or "").strip().upper().split())


def card_matches_filter(card_name: str, filters: list[str]) -> bool:
    """Substring match: any filter token is contained in the card name."""
    norm = normalize_name(card_name)
    return any(normalize_name(f) in norm for f in filters)


def card_matches_rule(card_name: str, rule: dict[str, Any]) -> bool:
    """Check if a card name matches any of the rule's card_names.

    Tries exact match first, then substring containment.
    """
    norm = normalize_name(card_name)
    if rule_targets_belmont(rule) and is_excluded_belmont_alias(norm):
        return False
    for rn in rule["card_names"]:
        rn_norm = normalize_name(rn)
        if norm == rn_norm or rn_norm in norm or norm in rn_norm:
            return True
    return False


def rule_targets_belmont(rule: dict[str, Any]) -> bool:
    if normalize_name(str(rule.get("track", ""))) == "BEL":
        return True
    return any(normalize_name(str(name)) == "BELMONT PARK" for name in rule.get("card_names", []))


def is_excluded_belmont_alias(normalized_card_name: str) -> bool:
    """Return true for BAQ / Big A labels that must not inherit BEL rules."""
    return any(token in normalized_card_name for token in BEL_ALIAS_EXCLUSION_TOKENS)


def race_number_from_summary(race: dict[str, Any]) -> int:
    """Return the race number available from a list-races row, or 0 if absent."""
    try:
        return int(race.get("raceNumber") or 0)
    except (TypeError, ValueError):
        return 0


def race_matches_rule_prefetch(card_name: str, race: dict[str, Any], rule: dict[str, Any]) -> bool:
    """True when a race-summary row is worth fetching for a rule.

    Field size, live prices, and condition need race-detail data, but card name and
    race number are already present in the list-races row. Applying those two
    cheap filters before fetching details prevents a small --max-races cap from
    being exhausted by unrelated cards on busy racing days.
    """
    if not card_matches_rule(card_name, rule):
        return False
    return race_number_from_summary(race) >= int(rule.get("card_min", 0) or 0)


def candidate_races_for_rules(
    races: list[dict[str, Any]],
    rules: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Filter list-races rows down to races that can still match a rule.

    Returns (candidate_races, skipped_race_count). This is intentionally a
    pre-detail filter only; final rule checks still happen in analyze_race after
    runner, condition, and price data are loaded.
    """
    candidates: list[dict[str, Any]] = []
    skipped = 0
    for race in races:
        card_name = race.get("raceMeetingName") or race.get("cardName") or ""
        if any(race_matches_rule_prefetch(card_name, race, rule) for rule in rules):
            candidates.append(race)
        else:
            skipped += 1
    return candidates, skipped


# ---------------------------------------------------------------------------
# Track condition extraction
# ---------------------------------------------------------------------------

def extract_track_condition(race_detail: dict[str, Any]) -> Optional[str]:
    for tagged in race_detail.get("raceTaggedValues", []):
        val = str(tagged.get("value", ""))
        parts = [x.strip() for x in val.split("|")]
        if len(parts) >= 3:
            cond = parts[-1].upper()
            if cond in {"FAST", "FIRM", "GOOD", "MUDDY", "SLOPPY", "YIELDING", "SOFT", "HEAVY", "WET FAST"}:
                return cond
    return None


# ---------------------------------------------------------------------------
# Runner / probability helpers
# ---------------------------------------------------------------------------

def is_active_runner(runner: dict[str, Any]) -> bool:
    return runner.get("runnerStatus") in ACTIVE_RUNNER_STATUSES


def get_win_prob_map(race_detail: dict[str, Any]) -> dict[str, float]:
    """Build normalized implied win probabilities from live prices.

    Uses currentWinPrice falling back to morningLineOdds.
    """
    raw: dict[str, float] = {}
    total = 0.0
    for runner in race_detail.get("runners", []):
        if not is_active_runner(runner):
            continue
        prog = str(runner.get("programNumber", "")).strip()
        price = runner.get("currentWinPrice")
        if price in (None, 0, 0.0, "", "SCR"):
            price = runner.get("morningLineOdds")
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue
        if not prog or price <= 0:
            continue
        implied = 1.0 / price
        raw[prog] = implied
        total += implied

    if total <= 0:
        return {}
    return {prog: val / total for prog, val in raw.items()}


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyze_race(
    card_name: str,
    race: dict[str, Any],
    race_detail: dict[str, Any],
    rules: list[dict[str, Any]],
    base_stake: float,
    emit_combos: bool,
) -> list[dict[str, Any]]:
    runners = [r for r in race_detail.get("runners", []) if is_active_runner(r)]
    field_size = len(runners)
    if field_size < 4:
        return []

    probs = get_win_prob_map(race_detail)
    if not probs:
        return []

    ranked = []
    for r in runners:
        prog = str(r.get("programNumber", "")).strip()
        p = probs.get(prog, 0.0)
        ranked.append({"program": prog, "name": r.get("runnerName"), "prob": p})
    ranked = [r for r in ranked if r["program"] and r["prob"] > 0]
    ranked.sort(key=lambda x: x["prob"], reverse=True)
    if len(ranked) < 4:
        return []

    fav_prob = ranked[0]["prob"]
    second_prob = ranked[1]["prob"] if len(ranked) > 1 else 0.0
    prob_gap = fav_prob - second_prob
    race_num = int(race_detail.get("raceNumber") or race.get("raceNumber") or 0)
    cond = extract_track_condition(race_detail)

    out: list[dict[str, Any]] = []
    for rule in rules:
        if not card_matches_rule(card_name, rule):
            continue
        if field_size < rule["field_min"] or field_size > rule["field_max"]:
            continue
        if race_num < rule["card_min"]:
            continue
        if prob_gap < rule["gap_min"]:
            continue
        if fav_prob < rule.get("fav_prob_min", 0.0):
            continue
        if rule.get("condition") == "fast" and (cond or "") not in FAST_CONDITIONS:
            continue

        k = int(rule["k"])
        if len(ranked) < k:
            continue

        key = ranked[0]["program"]
        underneath = [r["program"] for r in ranked[1:k]]
        combos: list[str] = []
        if emit_combos:
            combos = ["-".join((key,) + combo) for combo in permutations(underneath, 3)]

        cost = round(perm(k - 1, 3) * base_stake, 2)
        out.append({
            "rule_id": rule["rule_id"],
            "track": rule["track"],
            "card_name": card_name,
            "race_number": race_num,
            "race_id": race_detail.get("raceId"),
            "surface": race_detail.get("surface"),
            "condition": cond,
            "field_size": field_size,
            "favorite_program": key,
            "favorite_name": ranked[0]["name"],
            "favorite_prob": round(fav_prob, 4),
            "second_prob": round(second_prob, 4),
            "prob_gap": round(prob_gap, 4),
            "k": k,
            "base_stake": base_stake,
            "estimated_cost": cost,
            "underneath_programs": underneath,
            "top_ranked": ranked[:k],
            "ticket_structure": f"Key favorite {key} over next {k-1} choices for 2nd/3rd/4th",
            "combos": combos,
            "why": rule["plain_english"],
            "scan_ts": datetime.now().isoformat(timespec="seconds"),
            "valid_evidence_scope": SCANNER_VALID_EVIDENCE_SCOPE,
            "evidence_boundary": SCANNER_EVIDENCE_BOUNDARY_METADATA,
            "evidence_boundary_text": SCANNER_EVIDENCE_BOUNDARY_TEXT,
        })

    return out


# ---------------------------------------------------------------------------
# Duplicate alert ledger
# ---------------------------------------------------------------------------

def _alert_key(hit: dict[str, Any]) -> str:
    """Unique key for a specific alert on a specific day."""
    return f"{_today_str()}|{hit['rule_id']}|{hit['race_id']}|{hit['favorite_program']}"


def load_ledger() -> set[str]:
    if ALERT_LEDGER.exists():
        try:
            data = json.loads(ALERT_LEDGER.read_text(encoding="utf-8"))
            return set(data.get("posted", []))
        except (json.JSONDecodeError, KeyError):
            pass
    return set()


def save_ledger(posted: set[str]) -> None:
    ALERT_LEDGER.write_text(
        json.dumps({"date": _today_str(), "posted": sorted(posted)}, indent=2),
        encoding="utf-8",
    )


def filter_new_alerts(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only hits not already in today's ledger, then update ledger."""
    posted = load_ledger()
    # Flush stale ledger from previous days
    if posted and not any(k.startswith(_today_str()) for k in posted):
        posted = set()

    new = [h for h in hits if _alert_key(h) not in posted]
    if new:
        for h in new:
            posted.add(_alert_key(h))
        save_ledger(posted)
    return new


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def format_human(hits: list[dict[str, Any]], emit_combos: bool) -> str:
    scope_line = f"valid_evidence_scope={SCANNER_VALID_EVIDENCE_SCOPE}"
    boundary_line = f"Evidence boundary: {SCANNER_EVIDENCE_BOUNDARY_TEXT}"
    if not hits:
        return f"No qualifying races for the active ruleset.\n{scope_line}\n{boundary_line}"
    lines = [f"Found {len(hits)} qualifying race(s).", scope_line, boundary_line, ""]
    for h in hits:
        lines.append(f"[{h['track']}] {h['card_name']} Race {h['race_number']} (raceId={h['race_id']})")
        lines.append(f"  Rule: {h['rule_id']}")
        lines.append(f"  Surface/cond: {h['surface']} / {h['condition']}")
        lines.append(f"  Field: {h['field_size']} | Fav {h['favorite_program']} {h['favorite_name']} @ {h['favorite_prob']:.1%} | Gap {h['prob_gap']:.1%}")
        lines.append(f"  Ticket: {h['ticket_structure']}")
        lines.append(f"  Underneath: {', '.join(h['underneath_programs'])}")
        lines.append(f"  Est. cost (@ ${h['base_stake']:.2f} base): ${h['estimated_cost']:.2f}")
        if emit_combos:
            lines.append(f"  Combos ({len(h['combos'])}): {', '.join(h['combos'])}")
        lines.append("")
    return "\n".join(lines)


def format_discord(hits: list[dict[str, Any]]) -> str:
    """Format hits as a Discord-ready message (plain text with markdown)."""
    if not hits:
        return ""
    lines = [f"**Superfecta Scanner** — {_today_str()} — {len(hits)} alert(s)\n"]
    for h in hits:
        lines.append(f"🏇 **{h['card_name']} R{h['race_number']}** ({h['track']})")
        lines.append(f"  Rule `{h['rule_id']}` | Field {h['field_size']} | {h['surface']}/{h['condition']}")
        lines.append(f"  Fav **#{h['favorite_program']} {h['favorite_name']}** {h['favorite_prob']:.0%} (gap {h['prob_gap']:.0%})")
        lines.append(f"  Key {h['favorite_program']} / {','.join(h['underneath_programs'])} → ${h['estimated_cost']:.2f}")
        lines.append("")
    lines.append(f"_valid_evidence_scope={SCANNER_VALID_EVIDENCE_SCOPE}_")
    lines.append(f"_Evidence boundary: {SCANNER_EVIDENCE_BOUNDARY_TEXT}_")
    return "\n".join(lines)


def format_discord_webhook(hits: list[dict[str, Any]]) -> str:
    """Return JSON payload suitable for posting to a Discord webhook."""
    content = format_discord(hits)
    if not content:
        return ""
    payload = {"content": content}
    return json.dumps(payload, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def write_status(path: Optional[str], payload: dict[str, Any]) -> None:
    if not path:
        return
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def summarize_result(raw_hit_count: int, emitted_hit_count: int, partial_cache: bool) -> str:
    if emitted_hit_count > 0:
        return "partial_cache_alerts" if partial_cache else "alerts_found"
    if raw_hit_count > 0:
        return "partial_cache_duplicate_only" if partial_cache else "duplicate_only"
    return "partial_cache_no_qualifiers" if partial_cache else "no_qualifiers"


def parse_args():
    p = argparse.ArgumentParser(
        description="Scan live cards for the configured portfolio rules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s                           # scan all cards, human output
  %(prog)s --cache-only              # offline mode, use cached data only
  %(prog)s --include-cards belmont   # substring match on card name
  %(prog)s --discord                 # Discord-ready alert text
  %(prog)s --discord-webhook         # full Discord webhook JSON payload
  %(prog)s --max-races 5             # cap at 5 race detail fetches
  %(prog)s --no-dedup                # skip duplicate detection
  %(prog)s --cache-ttl 300           # reuse cache <5 min old
""",
    )
    p.add_argument("--rules", default=str(DEFAULT_RULES_PATH), help="Path to live rules JSON")
    p.add_argument("--base-stake", type=float, default=1.0, help="Base stake per combination")
    p.add_argument("--emit-combos", action="store_true", help="Emit exact ticket combos")
    p.add_argument("--json", action="store_true", help="Print JSON instead of human-readable text")
    p.add_argument("--save", help="Output path (.json or .csv)")
    p.add_argument("--status-json", default=str(DEFAULT_STATUS_PATH),
                   help="Optional JSON sidecar with machine-readable run status")

    p.add_argument("--include-cards", nargs="*", help="Substring filters for card names (e.g. 'belmont')")
    p.add_argument("--max-races", type=int, default=0, help="Max race details to fetch (0 = unlimited)")
    p.add_argument("--cache-only", action="store_true", help="Offline mode — only use cached data, no API calls")
    p.add_argument("--cache-ttl", type=int, default=0,
                    help="Cache TTL in seconds — reuse cached data younger than this (0 = always refresh)")

    p.add_argument("--discord", action="store_true", help="Print Discord-formatted alert text")
    p.add_argument("--discord-webhook", action="store_true", help="Print full Discord webhook JSON payload")
    p.add_argument("--no-dedup", action="store_true", help="Skip duplicate alert detection")

    return p.parse_args()


def load_rules(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["rules"]


def main():
    args = parse_args()
    reset_run_stats()
    status: dict[str, Any] = {
        "run_ts": datetime.now().isoformat(timespec="seconds"),
        "rules_path": str(Path(args.rules).resolve()),
        "cache_only": bool(args.cache_only),
        "cache_ttl": int(args.cache_ttl),
        "max_races": int(args.max_races),
        "base_stake": float(args.base_stake),
        "include_cards": args.include_cards or [],
        "dedup_enabled": not args.no_dedup,
        "valid_evidence_scope": SCANNER_VALID_EVIDENCE_SCOPE,
        "evidence_boundary": SCANNER_EVIDENCE_BOUNDARY_METADATA,
        "evidence_boundary_text": SCANNER_EVIDENCE_BOUNDARY_TEXT,
        "result": "running",
    }

    try:
        rules = load_rules(args.rules)
        status["rule_count"] = len(rules)

        cards = cached_call("cards", "today", list_cards,
                            cache_only=args.cache_only, cache_ttl=args.cache_ttl)

        if args.include_cards:
            cards = [c for c in cards if card_matches_filter(c.get("cardName", ""), args.include_cards)]

        status["card_count"] = len(cards)
        status["target_card_count"] = sum(
            1
            for card in cards
            if any(card_matches_rule(card.get("cardName", ""), rule) for rule in rules)
        )
        if not cards:
            status.update({
                "race_count": 0,
                "target_race_count": 0,
                **target_coverage_counts(0, 0),
                "raw_hit_count": 0,
                "emitted_hit_count": 0,
                "dedup_suppressed_count": 0,
                "partial_cache": False,
                "result": "no_matching_cards",
                **RUN_STATS,
            })
            write_status(args.status_json, status)
            print(
                "No matching cards found.\n"
                f"valid_evidence_scope={SCANNER_VALID_EVIDENCE_SCOPE}\n"
                f"Evidence boundary: {SCANNER_EVIDENCE_BOUNDARY_TEXT}"
            )
            return

        card_names = [c.get("cardName", "") for c in cards]
        card_ids = [c["cardId"] for c in cards if c.get("cardId")]

        races = cached_call("races", ",".join(map(str, sorted(card_ids))), list_races, card_ids,
                            cache_only=args.cache_only, cache_ttl=args.cache_ttl)
        status["race_count"] = len(races)
        candidate_races, pre_detail_skipped = candidate_races_for_rules(races, rules)
        RUN_STATS["pre_detail_skipped_race_count"] = pre_detail_skipped
        status["target_race_count"] = len(candidate_races)
        status["detail_fetch_scope"] = "rule_card_and_min_race_prefilter"

        hits: list[dict[str, Any]] = []
        for race in candidate_races:
            card_name = race.get("raceMeetingName") or race.get("cardName") or ""
            if card_name not in card_names and card_name:
                pass

            if args.max_races and RUN_STATS.get("race_details_attempted", 0) >= args.max_races:
                RUN_STATS["max_race_limit_hit"] = 1
                _log(f"[max-races] Reached limit of {args.max_races} candidate race-detail attempts, stopping.")
                break

            RUN_STATS["race_details_attempted"] = RUN_STATS.get("race_details_attempted", 0) + 1
            try:
                detail_list = cached_call(
                    "race",
                    str(race["raceId"]),
                    get_race_detail,
                    race["raceId"],
                    cache_only=args.cache_only,
                    cache_ttl=args.cache_ttl,
                )
            except SystemExit as exc:
                if args.cache_only and str(exc).startswith("[cache-only]"):
                    RUN_STATS["missing_race_detail_cache_skips"] = RUN_STATS.get("missing_race_detail_cache_skips", 0) + 1
                    _log(f"[cache-only] Skipping raceId={race['raceId']} with no cached detail")
                    continue
                raise
            RUN_STATS["race_details_loaded"] = RUN_STATS.get("race_details_loaded", 0) + 1

            if not detail_list:
                continue
            hits.extend(analyze_race(card_name, race, detail_list[0], rules, args.base_stake, args.emit_combos))

        raw_hit_count = len(hits)
        if not args.no_dedup:
            hits = filter_new_alerts(hits)
        emitted_hit_count = len(hits)
        dedup_suppressed_count = raw_hit_count - emitted_hit_count
        partial_cache = RUN_STATS.get("missing_race_detail_cache_skips", 0) > 0

        status.update({
            "raw_hit_count": raw_hit_count,
            "emitted_hit_count": emitted_hit_count,
            "dedup_suppressed_count": dedup_suppressed_count,
            "partial_cache": partial_cache,
            "result": summarize_result(raw_hit_count, emitted_hit_count, partial_cache),
            **target_coverage_counts(len(candidate_races), RUN_STATS.get("race_details_attempted", 0)),
            **RUN_STATS,
        })

        if args.save:
            _save_output(hits, args.save)
        write_status(args.status_json, status)

        if args.discord_webhook:
            payload = format_discord_webhook(hits)
            if payload:
                print(payload)
            return

        if args.discord:
            text = format_discord(hits)
            if text:
                print(text)
            return

        if args.json:
            print(json.dumps(hits, indent=2))
            return

        print(format_human(hits, args.emit_combos))
    except BaseException as exc:
        status.update({
            "result": "scanner_error",
            "error_type": exc.__class__.__name__,
            "error": str(exc),
            **scanner_failure_metadata(exc),
            **RUN_STATS,
        })
        write_status(args.status_json, status)
        raise


def _save_output(hits: list[dict[str, Any]], dest: str) -> None:
    path = Path(dest)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(hits, indent=2), encoding="utf-8")
    elif path.suffix.lower() == ".csv":
        import csv
        rows = []
        for h in hits:
            rows.append({
                k: json.dumps(v) if isinstance(v, (list, dict)) else v
                for k, v in h.items()
            })
        with open(path, "w", newline="", encoding="utf-8") as f:
            if rows:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
                w.writeheader()
                w.writerows(rows)
            else:
                f.write("rule_id,track,card_name,race_number,valid_evidence_scope,evidence_boundary_text\n")
    else:
        raise SystemExit("--save must end in .json or .csv")


if __name__ == "__main__":
    main()
