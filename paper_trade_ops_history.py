#!/usr/bin/env python3
"""
Generate a rolling operations history for the paper-trade daily runner.

Purpose:
- distinguish no-target race days from clean no-qualifier days
- surface operational failures without opening each daily folder manually
- keep the summary tied to existing daily artifacts, not a new state path
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from paper_trade_status_summary import is_cache_only_miss, resolve_declared_scanner_status_path

BASE = Path(__file__).resolve().parent
DEFAULT_RUNS_ROOT = BASE / "out" / "daily_portfolio_runs"
DEFAULT_MD = BASE / "OPS_HISTORY.md"
DEFAULT_CSV = BASE / "ops_history.csv"
API_ACCESS_OPERATOR_ACTION = "refresh_daily_wrapper_before_evidence_read"
API_ACCESS_RECHECK_COMMAND = "./run_daily_portfolio_observation.sh"
OPS_HISTORY_VALID_EVIDENCE_SCOPE = "rolling_operator_recap_only"
OPS_HISTORY_EVIDENCE_BOUNDARY_TEXT = (
    "OPS history rows are rolling operator recap metadata only; day buckets, streaks, no-target rows, "
    "clean-empty rows, limited-coverage rows, bet-ready rows, and issue routing are not current-day scanner "
    "evidence by themselves, live paper-trade ledger evidence, settled ROI, promotion readiness, "
    "live-profitability evidence, real-money support, or BAQ-as-BEL evidence."
)


def rel_to_base(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BASE.resolve()))
    except Exception:
        return str(path)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate a rolling ops history from daily paper-trade run folders")
    p.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT), help="Directory containing YYYY-MM-DD daily run folders")
    p.add_argument("--limit", type=int, default=14, help="Maximum number of run days to include, newest first")
    p.add_argument("--md-output", default=str(DEFAULT_MD), help="Markdown output path")
    p.add_argument("--csv-output", default=str(DEFAULT_CSV), help="CSV output path")
    return p.parse_args()


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def json_state(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return "missing"
    if path.stat().st_size == 0:
        return "empty"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "unreadable"
    return "ok" if isinstance(data, dict) else "invalid_shape"


def safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def scanner_failure_detail(status: dict[str, Any] | None, scanner_status: dict[str, Any] | None) -> str:
    """Return the most specific scanner failure detail available in the saved sidecars."""
    candidates = [
        (status or {}).get("scanner_error"),
        (scanner_status or {}).get("error"),
        (status or {}).get("error"),
    ]
    for candidate in candidates:
        detail = str(candidate or "").strip()
        if detail:
            return detail.rstrip(".")
    return ""


def scanner_failure_is_api_access(status: dict[str, Any] | None, scanner_status: dict[str, Any] | None) -> bool:
    if bool((status or {}).get("scanner_api_access_failure", (scanner_status or {}).get("api_access_failure", False))):
        return True
    for raw_status in (
        (status or {}).get("scanner_http_status"),
        (scanner_status or {}).get("http_status"),
    ):
        try:
            if int(raw_status or 0) in {401, 403}:
                return True
        except (TypeError, ValueError):
            pass
    failure_class = str((status or {}).get("scanner_api_failure_class", (scanner_status or {}).get("api_failure_class", ""))).strip()
    if failure_class == "api_access_failure":
        return True
    detail = scanner_failure_detail(status, scanner_status).lower()
    return any(token in detail for token in ("403", "forbidden", "unauthorized", "access denied", "api access"))


def scanner_failure_operator_routing(status: dict[str, Any] | None, scanner_status: dict[str, Any] | None) -> tuple[str, str]:
    action = str(
        (status or {}).get(
            "scanner_api_failure_operator_action",
            (scanner_status or {}).get("api_failure_operator_action", ""),
        ) or ""
    ).strip()
    recheck = str(
        (status or {}).get(
            "scanner_api_failure_recheck_command",
            (scanner_status or {}).get("api_failure_recheck_command", ""),
        ) or ""
    ).strip()
    return action or API_ACCESS_OPERATOR_ACTION, recheck or API_ACCESS_RECHECK_COMMAND


def scanner_stale_cache_fallback_context(status: dict[str, Any] | None, scanner_status: dict[str, Any] | None) -> str:
    applied = bool((status or {}).get(
        "scanner_stale_cache_fallback_applied",
        (scanner_status or {}).get("stale_cache_fallback_applied", False),
    ))
    fallback_kind = str((status or {}).get(
        "scanner_stale_cache_fallback_kind",
        (scanner_status or {}).get("stale_cache_fallback_kind", ""),
    ) or "").strip()
    fallback_error_type = str((status or {}).get(
        "scanner_stale_cache_fallback_error_type",
        (scanner_status or {}).get("stale_cache_fallback_error_type", ""),
    ) or "").strip()
    fallback_error = str((status or {}).get(
        "scanner_stale_cache_fallback_error",
        (scanner_status or {}).get("stale_cache_fallback_error", ""),
    ) or "").strip()
    fallback_count = safe_int((status or {}).get(
        "scanner_stale_cache_fallback_count",
        (scanner_status or {}).get("stale_cache_fallback_count", 0),
    ))
    if not any([applied, fallback_kind, fallback_count, fallback_error_type, fallback_error]):
        return ""

    parts: list[str] = []
    if fallback_kind:
        parts.append(f"Stale-cache fallback used for {fallback_kind}")
    else:
        parts.append("Stale-cache fallback used")
    if fallback_count:
        parts.append(f"{fallback_count} stale-cache fallback(s)")
    if fallback_error_type or fallback_error:
        fallback_detail = fallback_error
        if fallback_error_type:
            fallback_detail = f"{fallback_error_type}: {fallback_error}" if fallback_error else fallback_error_type
        parts.append(f"stale-cache fallback error {fallback_detail}")
    return "; ".join(parts)


def pipeline_recorded_scanner_status_state(status: dict[str, Any] | None) -> str:
    """Return a pipeline-recorded scanner-status state when the scanner sidecar itself is unavailable."""
    if not status:
        return ""
    state = str(status.get("scanner_status_state") or "").strip().lower()
    result = str(status.get("scanner_result") or "").strip().lower()
    if state in {"empty", "unreadable", "invalid_shape"}:
        return state
    if result == "scanner_status_empty":
        return "empty"
    if result == "scanner_status_unreadable":
        return "unreadable"
    if result == "scanner_status_invalid_shape":
        return "invalid_shape"
    if str(status.get("observation_reason") or "").strip().lower() == "scanner_status_invalid_shape":
        return "invalid_shape"
    return ""


def is_missing_scan_output_status(status: dict[str, Any] | None) -> bool:
    if not status:
        return False
    scanner_result = str(status.get("scanner_result") or "").strip().lower()
    observation_reason = str(status.get("observation_reason") or "").strip().lower()
    return scanner_result == "missing_scan_output" or observation_reason == "missing_scan_output"


def summarize_missing_scan_output_detail(status: dict[str, Any] | None) -> str:
    reported = str((status or {}).get("scanner_status_reported_result") or "").strip()
    fallback_value = str((status or {}).get("scan_input_empty_fallback_value") or "").strip()
    detail = "scan-output artifact was missing"
    if reported:
        detail += f" after scanner status reported {reported}"
    if fallback_value:
        detail += f"; pipeline used a safe empty {fallback_value} fallback"
    else:
        detail += "; pipeline used a safe empty-scan fallback"
    detail += ", so this is not a clean no-qualifier observation."
    return detail


def summarize_calendar(preflight: dict[str, Any] | None, preflight_state: str = "ok") -> tuple[str, str]:
    if not preflight:
        if preflight_state == "empty":
            return "EMPTY", "Preflight note empty."
        if preflight_state == "unreadable":
            return "UNREADABLE", "Preflight note unreadable."
        return "MISSING", "Preflight note missing."

    calendar_reason = str(preflight.get("calendar_reason") or "").strip().lower()
    if calendar_reason == "upstream_error":
        error_text = str(preflight.get("error") or "").strip()
        if error_text:
            return "UNKNOWN", f"Preflight API error: {error_text}"
        return "UNKNOWN", "Preflight API error."
    if calendar_reason == "api_unreachable":
        return "UNKNOWN", "Preflight API unavailable."
    if calendar_reason == "active_targets":
        tracks = ", ".join(preflight.get("relevant_tracks") or []) or "OP / CD"
        return "OP/CD ACTIVE", f"Active-basket tracks racing: {tracks}."
    if calendar_reason == "no_targets":
        shadow = ", ".join(preflight.get("shadow_tracks") or [])
        detail = f"No active OP/CD cards across {safe_int(preflight.get('total_cards'))} NYRA card(s)."
        if shadow:
            detail += f" Shadow-only tracks present: {shadow}."
        return "NO TARGETS", detail

    if preflight.get("error"):
        return "UNKNOWN", f"Preflight API error: {preflight['error']}"
    if not preflight.get("api_ok", False):
        return "UNKNOWN", "Preflight API unavailable."
    if preflight.get("has_targets"):
        tracks = ", ".join(preflight.get("relevant_tracks") or []) or "OP / CD"
        return "OP/CD ACTIVE", f"Active-basket tracks racing: {tracks}."
    shadow = ", ".join(preflight.get("shadow_tracks") or [])
    detail = f"No active OP/CD cards across {safe_int(preflight.get('total_cards'))} NYRA card(s)."
    if shadow:
        detail += f" Shadow-only tracks present: {shadow}."
    return "NO TARGETS", detail


def pipeline_failure_context(status: dict[str, Any] | None) -> dict[str, Any] | None:
    if not status or str(status.get("result") or "").lower() != "pipeline_error":
        return None
    stage = str(status.get("stage") or "").lower()
    error_type = str(status.get("error_type") or "")
    error = str(status.get("error") or "")
    failure_name = {
        "recommender": "recommender failure",
        "logger": "logger failure",
    }.get(stage, "pipeline failure")
    return {
        "label": failure_name.upper(),
        "failure_name": failure_name,
        "stage": stage or None,
        "last_completed_stage": str(status.get("last_completed_stage") or "") or None,
        "observation_result": str(status.get("observation_result") or "") or None,
        "scan_hit_count": safe_int(status.get("scan_hit_count")),
        "recommendation_count": safe_int(status.get("recommendation_count")),
        "bet_count": safe_int(status.get("bet_count")),
        "error_type": error_type or None,
        "error": error or None,
    }


def failure_progress_detail(failure: dict[str, Any]) -> str:
    stage = str(failure.get("stage") or "")
    last_completed_stage = str(failure.get("last_completed_stage") or "")
    scan_hits = safe_int(failure.get("scan_hit_count"))
    recommendations = safe_int(failure.get("recommendation_count"))
    bets = safe_int(failure.get("bet_count"))
    observation = str(failure.get("observation_result") or "")

    if stage == "recommender":
        if scan_hits:
            return f"After scanner completed, {scan_hits} hit(s) were already found before the failure."
        if last_completed_stage == "scanner":
            return "After scanner completed, the recommender failed before it could finish the lane review."
    if stage == "logger":
        if recommendations:
            detail = f"After recommender completed, {recommendations} recommendation(s) were already built"
            if bets:
                detail += f" and {bets} BET recommendation(s) were ready"
            if observation:
                detail += f" (context: {observation})"
            return detail + " before the failure."
        if last_completed_stage == "recommender":
            return "After recommender completed, the logger failed before it could finish writing artifacts."
    if last_completed_stage:
        return f"Last completed stage before failure: {last_completed_stage}."
    return ""


def summarize_partial_cache_detail(scanner_status: dict[str, Any] | None) -> str:
    if not scanner_status:
        return ""
    parts: list[str] = []
    missing_race_details = safe_int(scanner_status.get("missing_race_detail_cache_skips"))
    race_details_attempted = safe_int(scanner_status.get("race_details_attempted"))
    max_race_limit_hit = bool(scanner_status.get("max_race_limit_hit", False))
    if missing_race_details:
        parts.append(f"{missing_race_details} missing race detail cache file(s)")
    target_race_count = safe_int(scanner_status.get("target_race_count"))
    if target_race_count:
        parts.append(f"{target_race_count} target candidate race(s)")
    pre_detail_skipped = safe_int(scanner_status.get("pre_detail_skipped_race_count"))
    if pre_detail_skipped:
        parts.append(f"{pre_detail_skipped} non-target race(s) skipped before detail fetch")
    full_target_coverage_min_races = safe_int(scanner_status.get("full_target_coverage_min_races")) or target_race_count
    unattempted_target_race_count = safe_int(scanner_status.get("unattempted_target_race_count"))
    if not unattempted_target_race_count and target_race_count and race_details_attempted:
        unattempted_target_race_count = max(0, target_race_count - race_details_attempted)
    if max_race_limit_hit and race_details_attempted:
        parts.append(f"max-races cap hit after {race_details_attempted} attempt(s)")
        if unattempted_target_race_count:
            parts.append(f"{unattempted_target_race_count} target candidate race(s) unattempted")
        if full_target_coverage_min_races:
            parts.append(f"raise --max-races to at least {full_target_coverage_min_races} for full target coverage")
    return "; ".join(parts)


def summarize_lane(status: dict[str, Any] | None, scanner_status: dict[str, Any] | None = None,
                   status_state: str = "ok", scanner_state: str = "ok") -> tuple[str, str, str, int, int, int, bool, bool]:
    if not status:
        if status_state == "empty":
            return "PIPELINE EMPTY", "missing", "Pipeline status sidecar empty.", 0, 0, 0, True, False
        if status_state == "unreadable":
            return "UNREADABLE", "missing", "Status file unreadable.", 0, 0, 0, True, False
        if status_state == "invalid_shape":
            return "INVALID SHAPE", "missing", "Status file has invalid JSON shape.", 0, 0, 0, True, False
        return "MISSING", "missing", "Status file missing.", 0, 0, 0, True, False

    observation = str(status.get("observation_result") or "missing")
    observation_reason = str(status.get("observation_reason") or "")
    scan_hits = safe_int(status.get("scan_hit_count"))
    recommendations = safe_int(status.get("recommendation_count"))
    bets = safe_int(status.get("bet_count"))
    cache_only = bool(status.get("cache_only", False))
    mode = "cache-only" if cache_only else "live"
    cache_miss = is_cache_only_miss(scanner_status, status)

    if scanner_state == "empty":
        return "SCANNER EMPTY", observation, "Scanner status sidecar empty.", scan_hits, recommendations, bets, True, False
    if scanner_state == "unreadable":
        return "UNREADABLE", observation, "Scanner status sidecar unreadable.", scan_hits, recommendations, bets, True, False
    if scanner_state == "invalid_shape":
        return "SCANNER INVALID SHAPE", observation, "Scanner status sidecar has invalid JSON shape.", scan_hits, recommendations, bets, True, False

    recorded_scanner_state = pipeline_recorded_scanner_status_state(status)
    if recorded_scanner_state == "empty":
        return (
            "SCANNER RECORDED EMPTY",
            observation,
            "Scanner status sidecar was recorded empty by the pipeline.",
            scan_hits,
            recommendations,
            bets,
            True,
            False,
        )
    if recorded_scanner_state == "unreadable":
        return (
            "SCANNER RECORDED UNREADABLE",
            observation,
            "Scanner status sidecar was recorded unreadable by the pipeline.",
            scan_hits,
            recommendations,
            bets,
            True,
            False,
        )
    if recorded_scanner_state == "invalid_shape":
        return (
            "SCANNER RECORDED INVALID SHAPE",
            observation,
            "Scanner status sidecar was recorded invalid-shape by the pipeline.",
            scan_hits,
            recommendations,
            bets,
            True,
            False,
        )

    failure = pipeline_failure_context(status)

    if failure is not None:
        label = str(failure["label"])
        detail_parts = [f"{failure['failure_name'].capitalize()} during {mode} run."]
        progress_detail = failure_progress_detail(failure)
        if progress_detail:
            detail_parts.append(progress_detail)
        if failure["error_type"]:
            detail_parts.append(f"Error type: {failure['error_type']}.")
        if failure["error"]:
            detail_parts.append(f"Detail: {failure['error']}.")
        detail = " ".join(detail_parts)
    elif observation == "bets_ready":
        label = f"BETS READY ({bets} bet{'s' if bets != 1 else ''})"
        detail = f"{mode} run produced {bets} bet(s) from {recommendations} recommendation(s)."
    elif observation == "signals_logged_no_bet":
        label = "SIGNALS, NO BET"
        detail = f"{mode} run logged {scan_hits} hit(s) but produced no BET recommendation."
    elif observation == "clean_empty_run":
        label = "CLEAN EMPTY"
        detail = f"{mode} run completed cleanly with 0 hits and 0 recommendations."
    elif observation_reason == "partial_cache_with_activity" or observation == "partial_cache_with_activity":
        label = "PARTIAL CACHE WITH ACTIVITY"
        partial_cache_detail = summarize_partial_cache_detail(scanner_status)
        detail = f"{mode} run still produced {scan_hits} hit(s)"
        if recommendations:
            detail += f" and {recommendations} recommendation(s)"
        if bets:
            detail += f", including {bets} BET recommendation(s)"
        detail += " on partial cache coverage, so keep the activity but do not treat it like a full live read."
        if partial_cache_detail:
            detail += f" Detail: {partial_cache_detail}."
    elif observation == "partial_cache_empty_run":
        label = "PARTIAL CACHE EMPTY"
        partial_cache_detail = summarize_partial_cache_detail(scanner_status)
        detail = "Run finished empty on partial cache coverage, so treat the empty result as operationally limited."
        if partial_cache_detail:
            detail += f" Detail: {partial_cache_detail}."
    elif observation == "limited_coverage_with_activity":
        label = "LIMITED COVERAGE WITH ACTIVITY"
        partial_cache_detail = summarize_partial_cache_detail(scanner_status)
        detail = f"{mode} run produced {scan_hits} hit(s)"
        if recommendations:
            detail += f" and {recommendations} recommendation(s)"
        if bets:
            detail += f", including {bets} BET recommendation(s)"
        detail += " after the max-races cap was reached, so keep the activity but do not treat it like full candidate coverage."
        if partial_cache_detail:
            detail += f" Detail: {partial_cache_detail}."
    elif observation == "limited_coverage_empty_run":
        label = "LIMITED COVERAGE EMPTY"
        partial_cache_detail = summarize_partial_cache_detail(scanner_status)
        detail = "Run finished empty after the max-races cap was reached, so treat the zero-hit result as operationally limited."
        if partial_cache_detail:
            detail += f" Detail: {partial_cache_detail}."
    elif cache_miss:
        label = "CACHE MISS (CACHE-ONLY)"
        detail = "Cache-only run could not start because today's cache files were missing."
    elif is_missing_scan_output_status(status):
        label = "MISSING SCAN OUTPUT"
        detail = summarize_missing_scan_output_detail(status)
    elif observation == "scanner_failed_empty_run":
        is_api_access = scanner_failure_is_api_access(status, scanner_status)
        label = "SCANNER API ACCESS FAILURE" if is_api_access else "SCANNER FAILED"
        detail = (
            "Scanner API access failure before producing a usable lane result."
            if is_api_access else
            "Scanner failed before producing a usable lane result."
        )
        failure_detail = scanner_failure_detail(status, scanner_status)
        if failure_detail:
            detail += f" Detail: {failure_detail}."
        if is_api_access:
            stale_cache_context = scanner_stale_cache_fallback_context(status, scanner_status)
            action, recheck = scanner_failure_operator_routing(status, scanner_status)
            detail += (
                " Treat this as API-access-failure operator context only, not a no-target, clean-empty, "
                "settled ROI, promotion, live-profitability, or real-money evidence."
            )
            if stale_cache_context:
                detail += f" {stale_cache_context}."
            detail += f" Sidecar action: {action}. Recheck command: {recheck}."
    else:
        result = str(status.get("result") or "missing")
        stage = str(status.get("stage") or "unknown")
        label = observation.upper().replace("_", " ") if observation != "missing" else result.upper()
        detail = f"Observed state: result={result}, stage={stage}, observation={observation}."

    issue = (label in {"MISSING SCAN OUTPUT", "SCANNER FAILED", "SCANNER API ACCESS FAILURE", "MISSING"} or str(status.get("result") or "").lower() not in {"", "ok"}) and not cache_miss
    return label, observation, detail, scan_hits, recommendations, bets, issue, cache_miss


def classify_day_bucket(calendar_label: str, primary_obs: str, primary_hits: int,
                       primary_recommendations: int, primary_bets: int, primary_issue: bool,
                       primary_cache_miss: bool) -> str:
    if primary_cache_miss:
        if calendar_label == "NO TARGETS":
            return "NO TARGETS"
        return "ISSUE"
    if primary_issue:
        return "ISSUE"
    if calendar_label in {"UNKNOWN", "UNREADABLE", "EMPTY", "MISSING"}:
        return "UNKNOWN CALENDAR"
    if calendar_label == "NO TARGETS":
        return "NO TARGETS"
    if primary_obs in {"partial_cache_with_activity", "limited_coverage_with_activity"}:
        return "ACTIVE, LIMITED COVERAGE WITH ACTIVITY"
    if primary_obs in {"partial_cache_empty_run", "limited_coverage_empty_run"}:
        return "ACTIVE, LIMITED COVERAGE"
    if primary_bets > 0:
        return "BETS READY"
    if primary_hits > 0 or primary_recommendations > 0 or primary_obs == "signals_logged_no_bet":
        return "ACTIVE, HITS FOUND"
    if primary_obs == "clean_empty_run":
        return "ACTIVE, ZERO HITS"
    return "OTHER"


def build_takeaway(calendar_label: str, calendar_detail: str, primary_label: str, primary_obs: str,
                   primary_hits: int, primary_recommendations: int, primary_bets: int,
                   primary_issue: bool, primary_cache_miss: bool,
                   primary_status: dict[str, Any] | None = None,
                   primary_detail: str = "") -> str:
    if primary_cache_miss:
        if calendar_label == "NO TARGETS":
            return "No active OP/CD cards. The cache-only run missed today's cache files, but the quiet day is still explained by the race calendar, not by a rules miss."
        return "Primary lane was checked in cache-only mode, but today's cache files were missing. Re-run without --cache-only before drawing conclusions."
    if primary_label == "PIPELINE EMPTY":
        return "Primary lane pipeline status sidecar was empty. Refresh the daily wrapper before drawing conclusions."
    if primary_label == "SCANNER EMPTY":
        return "Primary lane scanner status sidecar was empty. Refresh the daily wrapper before drawing conclusions."
    if primary_label == "SCANNER RECORDED EMPTY":
        return "Primary lane scanner status sidecar was recorded empty by the pipeline. Refresh the daily wrapper before drawing conclusions."
    if primary_label == "SCANNER RECORDED UNREADABLE":
        return "Primary lane scanner status sidecar was recorded unreadable by the pipeline. Refresh the daily wrapper before drawing conclusions."
    if primary_label == "SCANNER RECORDED INVALID SHAPE":
        return "Primary lane scanner status sidecar was recorded invalid-shape by the pipeline. Refresh the daily wrapper before drawing conclusions."
    if primary_label == "MISSING SCAN OUTPUT":
        return f"Primary lane {summarize_missing_scan_output_detail(primary_status)} Refresh the daily wrapper before treating the day as a clean no-qualifier observation."
    if primary_label in {"SCANNER FAILED", "SCANNER API ACCESS FAILURE"}:
        failure_sentence = primary_detail.strip().rstrip(".") if primary_detail else "Scanner failed before producing a usable lane result"
        if failure_sentence.startswith("Scanner "):
            failure_sentence = "Primary lane " + failure_sentence[:1].lower() + failure_sentence[1:]
        elif not failure_sentence.startswith("Primary lane"):
            failure_sentence = f"Primary lane scanner failed: {failure_sentence}"
        return f"{failure_sentence}. Refresh the daily wrapper and re-check sidecars before treating the day as evidence."
    if primary_label == "INVALID SHAPE":
        return "Primary lane pipeline status sidecar has invalid JSON shape. Refresh the daily wrapper before drawing conclusions."
    if primary_label == "SCANNER INVALID SHAPE":
        return "Primary lane scanner status sidecar has invalid JSON shape. Refresh the daily wrapper before drawing conclusions."
    if primary_label in {"MISSING", "UNREADABLE"}:
        return "Primary lane status artifacts were missing or unreadable. Refresh the daily wrapper before drawing conclusions."
    if primary_obs == "partial_cache_with_activity":
        detail_suffix = ""
        if "Detail:" in primary_detail:
            detail_suffix = " " + primary_detail.split("Detail:", 1)[1].strip()
        activity = f"found {primary_hits} hit(s)"
        if primary_recommendations:
            activity += f" and turned them into {primary_recommendations} recommendation(s)"
        if primary_bets:
            activity += f", including {primary_bets} BET recommendation(s)"
        if calendar_label == "NO TARGETS":
            return f"No active OP/CD cards. The primary lane still {activity} on partial cache coverage, so treat that activity as operationally limited rather than evidence of a rules miss.{detail_suffix}".strip()
        return f"OP/CD were active and the primary lane still {activity} on partial cache coverage, so keep the activity but do not treat it like a full live read.{detail_suffix} Re-run live before leaning on it as evidence."
    if primary_obs == "partial_cache_empty_run":
        detail_suffix = ""
        if "Detail:" in primary_detail:
            detail_suffix = " " + primary_detail.split("Detail:", 1)[1].strip()
        if calendar_label == "NO TARGETS":
            return f"No active OP/CD cards. The primary lane also finished on partial cache coverage, so the quiet read is still calendar-explained, not evidence of a rules miss.{detail_suffix}".strip()
        return f"OP/CD were active, but the latest primary-lane read finished empty on partial cache coverage.{detail_suffix} Re-run live before treating it as a true zero-hit day."
    if primary_obs == "limited_coverage_with_activity":
        detail_suffix = ""
        if "Detail:" in primary_detail:
            detail_suffix = " " + primary_detail.split("Detail:", 1)[1].strip()
        activity = f"found {primary_hits} hit(s)"
        if primary_recommendations:
            activity += f" and turned them into {primary_recommendations} recommendation(s)"
        if primary_bets:
            activity += f", including {primary_bets} BET recommendation(s)"
        return f"OP/CD were active and the primary lane {activity}, but the max-races cap limited candidate coverage.{detail_suffix} Raise the cap or rerun before leaning on it as evidence."
    if primary_obs == "limited_coverage_empty_run":
        detail_suffix = ""
        if "Detail:" in primary_detail:
            detail_suffix = " " + primary_detail.split("Detail:", 1)[1].strip()
        if calendar_label == "NO TARGETS":
            return f"No active OP/CD cards. The primary lane also hit its max-races cap, so treat the lane read as operationally limited rather than evidence of a rules miss.{detail_suffix}".strip()
        return f"OP/CD were active, but the latest primary-lane read finished empty after the max-races cap was reached.{detail_suffix} Raise the cap or rerun before treating it as a true zero-hit day."
    if primary_issue:
        failure = pipeline_failure_context(primary_status)
        if failure is not None:
            parts = [f"Primary lane hit a {failure['failure_name']}." ]
            progress_detail = failure_progress_detail(failure)
            if progress_detail:
                parts.append(progress_detail)
            if failure["error_type"]:
                parts.append(f"Error type: {failure['error_type']}.")
            if failure["error"]:
                parts.append(f"Detail: {failure['error']}.")
            parts.append("Refresh the daily wrapper and re-check sidecars before treating the day as evidence.")
            return " ".join(parts)
        return "Primary lane had an operational issue. Read the latest daily summary and sidecars before drawing conclusions."
    if calendar_label == "EMPTY":
        return "Preflight calendar context was empty, so treat the daily result as operationally ambiguous."
    if calendar_label == "UNREADABLE":
        return "Preflight calendar context was unreadable, so treat the daily result as operationally ambiguous."
    if calendar_label == "MISSING":
        return "Preflight calendar context was missing, so treat the daily result as operationally ambiguous."
    if calendar_label == "UNKNOWN":
        return "Calendar state was unknown, so treat the daily result as operationally ambiguous."
    if calendar_label == "NO TARGETS":
        if primary_obs == "clean_empty_run":
            return "No active OP/CD cards. Empty primary lane is expected, not evidence of a miss."
        return "No active OP/CD cards, but the primary lane did not finish with a normal clean-empty read."
    if primary_bets > 0:
        return f"Primary lane produced {primary_bets} bet(s). Review the lane artifacts before the races go off."
    if primary_recommendations > 0 or primary_hits > 0:
        return f"OP/CD were active and the primary lane found {primary_hits} hit(s), but nothing reached a bet-ready state."
    if primary_obs == "clean_empty_run":
        return "OP/CD were active, but the primary lane found zero qualifying hits."
    return calendar_detail


def current_streak(rows: list[dict[str, Any]], predicate) -> int:
    count = 0
    for row in rows:
        if predicate(row):
            count += 1
        else:
            break
    return count


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    unknown_calendar_labels = {"UNKNOWN", "UNREADABLE", "EMPTY", "MISSING"}
    return {
        "run_days": len(rows),
        "target_days": sum(1 for row in rows if row["calendar_state"] == "OP/CD ACTIVE"),
        "no_target_days": sum(1 for row in rows if row["calendar_state"] == "NO TARGETS"),
        "calendar_unknown_days": sum(1 for row in rows if row["calendar_state"] in unknown_calendar_labels),
        "primary_issue_days": sum(1 for row in rows if row["primary_issue"]),
        "primary_activity_days": sum(1 for row in rows if row["primary_scan_hits"] > 0 or row["primary_recommendations"] > 0 or row["primary_bets"] > 0),
        "no_target_expected_empty_days": sum(1 for row in rows if row["day_bucket"] == "NO TARGETS"),
        "active_zero_hit_days": sum(1 for row in rows if row["day_bucket"] == "ACTIVE, ZERO HITS"),
        "active_limited_coverage_days": sum(1 for row in rows if row["day_bucket"] == "ACTIVE, LIMITED COVERAGE"),
        "active_limited_coverage_with_activity_days": sum(1 for row in rows if row["day_bucket"] == "ACTIVE, LIMITED COVERAGE WITH ACTIVITY"),
        "active_hit_found_days": sum(1 for row in rows if row["day_bucket"] == "ACTIVE, HITS FOUND"),
        "bets_ready_days": sum(1 for row in rows if row["day_bucket"] == "BETS READY"),
        "streaks": {
            "no_target": current_streak(rows, lambda row: row["day_bucket"] == "NO TARGETS"),
            "active_zero_hit": current_streak(rows, lambda row: row["day_bucket"] == "ACTIVE, ZERO HITS"),
            "active_limited_coverage": current_streak(rows, lambda row: row["day_bucket"] == "ACTIVE, LIMITED COVERAGE"),
            "active_limited_coverage_with_activity": current_streak(rows, lambda row: row["day_bucket"] == "ACTIVE, LIMITED COVERAGE WITH ACTIVITY"),
            "active_hit_found": current_streak(rows, lambda row: row["day_bucket"] == "ACTIVE, HITS FOUND"),
            "issue": current_streak(rows, lambda row: row["day_bucket"] == "ISSUE"),
        },
    }


def resolve_lane_scanner_status_path(run_dir: Path, lane_name: str, pipeline: dict[str, Any] | None = None) -> Path:
    lane_dir = run_dir / lane_name
    default_path = lane_dir / "live_scan.status.json"
    declared = str((pipeline or {}).get("scanner_status_path") or "").strip()
    if declared:
        pipeline_path = lane_dir / "pipeline_status.json"
        # Preserve the scanner sidecar path recorded by the pipeline even when that
        # artifact is missing from a copied run; a stale default filename should not
        # turn an artifact issue into a clean historical lane read.
        return resolve_declared_scanner_status_path(declared, pipeline_path)
    if default_path.exists() and default_path.is_file():
        return default_path
    return default_path


def collect_rows(runs_root: Path, limit: int) -> list[dict[str, Any]]:
    if not runs_root.exists():
        return []

    run_dirs = sorted([p for p in runs_root.iterdir() if p.is_dir()], reverse=True)
    rows: list[dict[str, Any]] = []

    for run_dir in run_dirs:
        preflight_path = run_dir / "preflight_note.json"
        preflight = read_json(preflight_path)
        preflight_state = json_state(preflight_path)
        primary_status_path = run_dir / "phase7_current_paper" / "pipeline_status.json"
        shadow_status_path = run_dir / "phase8_shadow" / "pipeline_status.json"
        primary_state = json_state(primary_status_path)
        shadow_state = json_state(shadow_status_path)
        primary = read_json(primary_status_path)
        shadow = read_json(shadow_status_path)
        primary_scanner_path = resolve_lane_scanner_status_path(run_dir, "phase7_current_paper", primary)
        shadow_scanner_path = resolve_lane_scanner_status_path(run_dir, "phase8_shadow", shadow)
        primary_scanner_state = json_state(primary_scanner_path)
        shadow_scanner_state = json_state(shadow_scanner_path)
        primary_scanner = read_json(primary_scanner_path)
        shadow_scanner = read_json(shadow_scanner_path)
        daily_summary_exists = (run_dir / "daily_summary.txt").exists()
        if not any([preflight, primary, shadow, daily_summary_exists, preflight_state != "missing", primary_state != "missing", shadow_state != "missing"]):
            continue

        calendar_label, calendar_detail = summarize_calendar(preflight, preflight_state)
        primary_label, primary_obs, primary_detail, primary_hits, primary_recs, primary_bets, primary_issue, primary_cache_miss = summarize_lane(primary, primary_scanner, primary_state, primary_scanner_state)
        shadow_label, shadow_obs, shadow_detail, shadow_hits, shadow_recs, shadow_bets, shadow_issue, shadow_cache_miss = summarize_lane(shadow, shadow_scanner, shadow_state, shadow_scanner_state)
        takeaway = build_takeaway(
            calendar_label,
            calendar_detail,
            primary_label,
            primary_obs,
            primary_hits,
            primary_recs,
            primary_bets,
            primary_issue,
            primary_cache_miss,
            primary,
            primary_detail,
        )
        day_bucket = classify_day_bucket(
            calendar_label,
            primary_obs,
            primary_hits,
            primary_recs,
            primary_bets,
            primary_issue,
            primary_cache_miss,
        )

        row = {
            "date": run_dir.name,
            "run_root": rel_to_base(run_dir),
            "calendar_state": calendar_label,
            "calendar_detail": calendar_detail,
            "preflight_state": preflight_state,
            "preflight_note": (
                (preflight or {}).get("note")
                or (
                    "Preflight note empty."
                    if preflight_state == "empty"
                    else "Preflight note unreadable."
                    if preflight_state == "unreadable"
                    else "Preflight note missing."
                )
            ),
            "primary_state": primary_label,
            "primary_observation_result": primary_obs,
            "primary_pipeline_stage": str((primary or {}).get("stage") or ""),
            "primary_pipeline_last_completed_stage": str((primary or {}).get("last_completed_stage") or ""),
            "primary_pipeline_error_type": str((primary or {}).get("error_type") or ""),
            "primary_scan_hits": primary_hits,
            "primary_recommendations": primary_recs,
            "primary_bets": primary_bets,
            "primary_cache_only": bool((primary or {}).get("cache_only", False)),
            "shadow_state": shadow_label,
            "shadow_observation_result": shadow_obs,
            "shadow_pipeline_stage": str((shadow or {}).get("stage") or ""),
            "shadow_pipeline_last_completed_stage": str((shadow or {}).get("last_completed_stage") or ""),
            "shadow_pipeline_error_type": str((shadow or {}).get("error_type") or ""),
            "shadow_scan_hits": shadow_hits,
            "shadow_recommendations": shadow_recs,
            "shadow_bets": shadow_bets,
            "shadow_cache_only": bool((shadow or {}).get("cache_only", False)),
            "primary_issue": primary_issue,
            "shadow_issue": shadow_issue,
            "primary_cache_miss": primary_cache_miss,
            "shadow_cache_miss": shadow_cache_miss,
            "day_bucket": day_bucket,
            "takeaway": takeaway,
            "valid_evidence_scope": OPS_HISTORY_VALID_EVIDENCE_SCOPE,
            "evidence_boundary_text": OPS_HISTORY_EVIDENCE_BOUNDARY_TEXT,
        }
        rows.append(row)
        if len(rows) >= limit:
            break

    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "date",
        "run_root",
        "calendar_state",
        "calendar_detail",
        "preflight_state",
        "preflight_note",
        "primary_state",
        "primary_observation_result",
        "primary_pipeline_stage",
        "primary_pipeline_last_completed_stage",
        "primary_pipeline_error_type",
        "primary_scan_hits",
        "primary_recommendations",
        "primary_bets",
        "primary_cache_only",
        "shadow_state",
        "shadow_observation_result",
        "shadow_pipeline_stage",
        "shadow_pipeline_last_completed_stage",
        "shadow_pipeline_error_type",
        "shadow_scan_hits",
        "shadow_recommendations",
        "shadow_bets",
        "shadow_cache_only",
        "primary_issue",
        "shadow_issue",
        "primary_cache_miss",
        "shadow_cache_miss",
        "day_bucket",
        "takeaway",
        "valid_evidence_scope",
        "evidence_boundary_text",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_md(path: Path, rows: list[dict[str, Any]], limit: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    summary = summarize_rows(rows)
    streaks = summary["streaks"]

    lines = [
        "# Paper-Trade Ops History",
        "",
        "This note gives a rolling operational read across recent daily paper-trade runs.",
        "It is meant to answer one practical question honestly: was a quiet day caused by the race calendar, a clean no-qualifier scan, or a pipeline problem?",
        "",
        f"Included run days: **{summary['run_days']}** (newest first, max `{limit}`)",
        "",
        "## Live hierarchy context",
        "",
        "- Primary paper basket: `OP_DURABLE_K7` remains the anchor and `CD_CORE_K8` remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion.",
        "- Shadow/watch lane: `OP_REFINED_K7` remains the lead same-family challenger; lane streaks or hit-found days alone do not promote OP_REFINED_K7 or any other Phase 8 pocket.",
        "- Excluded aliases: BAQ remains not treated as BEL; this ops rollup is not settled ROI, live profitability, promotion readiness, or real-money evidence.",
        "",
        "## Evidence boundary",
        "",
        f"- valid_evidence_scope={OPS_HISTORY_VALID_EVIDENCE_SCOPE}",
        f"- Boundary: {OPS_HISTORY_EVIDENCE_BOUNDARY_TEXT}",
        "",
        "## Summary",
        "",
        f"- OP / CD target days: **{summary['target_days']}**",
        f"- No-target days: **{summary['no_target_days']}**",
        f"- Calendar-unknown days: **{summary['calendar_unknown_days']}**",
        f"- Primary-lane issue days: **{summary['primary_issue_days']}**",
        f"- Primary-lane activity days (hits or recommendations or bets): **{summary['primary_activity_days']}**",
        f"- No-target expected-empty days: **{summary['no_target_expected_empty_days']}**",
        f"- Active-target zero-hit days: **{summary['active_zero_hit_days']}**",
        f"- Active-target limited-coverage days: **{summary['active_limited_coverage_days']}**",
        f"- Active-target limited-coverage-with-activity days: **{summary['active_limited_coverage_with_activity_days']}**",
        f"- Active-target hit-found / no-bet days: **{summary['active_hit_found_days']}**",
        f"- Bet-ready days: **{summary['bets_ready_days']}**",
        "",
        "## Current streaks",
        "",
        f"- Consecutive no-target days at the top of the log: **{streaks['no_target']}**",
        f"- Consecutive active-target zero-hit days at the top of the log: **{streaks['active_zero_hit']}**",
        f"- Consecutive active-target limited-coverage days at the top of the log: **{streaks['active_limited_coverage']}**",
        f"- Consecutive active-target limited-coverage-with-activity days at the top of the log: **{streaks['active_limited_coverage_with_activity']}**",
        f"- Consecutive active-target hit-found / no-bet days at the top of the log: **{streaks['active_hit_found']}**",
        f"- Consecutive primary-issue days at the top of the log: **{streaks['issue']}**",
        "",
        "## Daily log",
        "",
        "| Date | Calendar | Primary lane | Shadow lane | Takeaway |",
        "|---|---|---|---|---|",
    ]

    if rows:
        for row in rows:
            primary = f"{row['primary_state']} (hits={row['primary_scan_hits']}, recs={row['primary_recommendations']}, bets={row['primary_bets']})"
            shadow = f"{row['shadow_state']} (hits={row['shadow_scan_hits']}, recs={row['shadow_recommendations']}, bets={row['shadow_bets']})"
            lines.append(f"| `{row['date']}` | {row['calendar_state']} | {primary} | {shadow} | {row['takeaway']} |")
        lines.extend([
            "",
            "## Latest preflight notes",
            "",
        ])
        for row in rows[:5]:
            lines.append(f"- `{row['date']}`: {row['preflight_note']}")
    else:
        lines.append("| _none yet_ | _n/a_ | _n/a_ | _n/a_ | No daily run folders were found. |")

    lines.extend([
        "",
        "## Interpretation guardrails",
        "",
        "- `NO TARGETS` means OP / CD were not active that day, so an empty primary lane should not be read as a rules miss.",
        "- `CLEAN EMPTY` means the lane ran normally and simply found no qualifying races for that ruleset.",
        "- `CACHE MISS (CACHE-ONLY)` means the run was asked to reuse local cache files that were not present for that day. On no-target days this can still be calendar-explained, but on active target days you should rerun without `--cache-only` before interpreting the lane.",
        "- `PARTIAL CACHE EMPTY` means the lane finished empty on incomplete cache coverage. That is still different from a clean no-hit scan, especially on active OP / CD days.",
        "- `MISSING SCAN OUTPUT` means the scanner-status sidecar was readable but the expected scan-output artifact was absent; treat the safe empty fallback as operationally unresolved, not as a clean no-qualifier observation.",
        "- `RECOMMENDER FAILURE`, `LOGGER FAILURE`, `SCANNER FAILED`, `SCANNER API ACCESS FAILURE`, `PIPELINE EMPTY`, `SCANNER EMPTY`, `SCANNER INVALID SHAPE`, `SCANNER RECORDED EMPTY`, `SCANNER RECORDED UNREADABLE`, `SCANNER RECORDED INVALID SHAPE`, `INVALID SHAPE`, `UNREADABLE`, or `MISSING` means treat the day as operationally unresolved until the missing/empty/unreadable/invalid-shape sidecars are checked; API-access failures should preserve their sidecar action, wrapper recheck command, and stale-cache fallback count/kind/error when present as operational routing metadata only.",
        "- `UNKNOWN CALENDAR` means the preflight calendar context was missing, empty, unreadable, or API-ambiguous, so the day should stay operationally ambiguous rather than being over-interpreted.",
        "- `ACTIVE, ZERO HITS` is the important non-calendar quiet case: OP / CD were active, but the primary lane still found no qualifying hits.",
        "- `ACTIVE, LIMITED COVERAGE` means OP / CD were active, but the primary lane only had partial cache coverage, so the empty read should be refreshed live before it is treated as a true zero-hit day.",
        "- `ACTIVE, LIMITED COVERAGE WITH ACTIVITY` means the primary lane still found activity on partial cache coverage, so keep the activity but do not treat it like a full live read until the lane is rerun cleanly.",
        "- `ACTIVE, HITS FOUND` means the scanner did surface target-lane hits on a normal live read, even if none became bet-ready recommendations.",
        "- This is an ops artifact, not a performance-evaluation artifact. Use lane monitors and forward checks for settled-race evidence.",
        "",
    ])

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    rows = collect_rows(Path(args.runs_root), args.limit)
    write_csv(Path(args.csv_output), rows)
    write_md(Path(args.md_output), rows, args.limit)
    print(f"Wrote {args.csv_output}")
    print(f"Wrote {args.md_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
