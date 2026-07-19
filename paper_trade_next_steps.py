#!/usr/bin/env python3
"""
Suggest the next 2-3 commands for a paper-trade lane.

Purpose:
- turn lane state into concrete next actions
- reduce drift when the daily run is empty, waiting on settlement, or finally decision-grade
- keep advice tied to the current frozen-standard lane data
"""

from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from paper_trade_lane_monitor import build_monitor_payload, gate_source_text
from paper_trade_forward_check import DEFAULT_FROZEN_EVAL
from paper_trade_status_summary import (
    STATUS_OPERATOR_READ_GATE_ISSUE_FLAGS,
    is_cache_only_miss,
    json_state as status_json_state,
    read_json as read_status_json,
    resolve_declared_scanner_status_path as resolve_pipeline_declared_scanner_status_path,
)

BASE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = BASE / "out" / "paper_trade_next_steps.md"
DEFAULT_RUNNER = BASE / "run_daily_portfolio_observation.sh"
SETTLEMENT_HELPER = BASE / "paper_trade_settlement_helper.py"
LANE_MONITOR = BASE / "paper_trade_lane_monitor.py"
FORWARD_CHECK = BASE / "paper_trade_forward_check.py"
API_ACCESS_OPERATOR_ACTION = "refresh_daily_wrapper_before_evidence_read"
API_ACCESS_RECHECK_COMMAND = "./run_daily_portfolio_observation.sh"
VALID_EVIDENCE_SCOPE = "paper_trade_next_step_action_routing_only"
EVIDENCE_BOUNDARY_TEXT = (
    "Next-steps output is operator action-routing metadata only: exact commands, "
    "settlement/refresh/repair guidance, sample-readiness wording, issue routing, "
    "and scorecard gate visibility are not scanner evidence, live paper-trade ledger "
    "evidence, settled ROI, promotion readiness, live profitability, real-money support, "
    "or BAQ-as-BEL evidence."
)
EVIDENCE_BOUNDARY: dict[str, Any] = {
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "artifact_role": "paper-trade next-steps source output",
    "valid_use": "operator action routing for settlement, refresh, repair, and sample-readiness commands",
    "not_new_forward_evidence": True,
    "not_current_day_scanner_result": True,
    "not_live_paper_trade_ledger": True,
    "not_settled_roi_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "baq_as_bel_substitution_allowed": False,
}


def next_steps_gate_alignment_read(gate_minimums: dict[str, Any]) -> str:
    if not gate_minimums.get("cli_overrides") and gate_minimums.get("source_loaded") and not gate_minimums.get("fallback_used"):
        active_gate = str(gate_minimums.get("active_first_read_gate") or "the active first-read gate")
        return f"next-steps sample milestones are source-matched to forward_evidence_scorecard.json decision_gate_minimums using {active_gate} for this lane"
    return "next-steps sample milestones are using explicit CLI/fallback values; do not treat fixture/custom thresholds as posture-changing gates"


def next_steps_gate_caution(gate_minimums: dict[str, Any]) -> str:
    active_gate = str(gate_minimums.get("active_first_read_gate") or "").strip()
    if active_gate == "phase8_promotion_review":
        return (
            "Phase 8 shadow first-read status is a review floor, not a promotion entitlement; "
            "lane totals alone do not promote any Phase 8 pocket, scorecard tiers remain binding, "
            "and negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion."
        )
    return ""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Suggest the next few commands for a paper-trade lane")
    p.add_argument("--signals-ledger", required=True, help="Signal ledger CSV path")
    p.add_argument("--recommendation-ledger", required=True, help="Recommendation ledger CSV path")
    p.add_argument("--settlement-ledger", required=True, help="Settlement ledger CSV path")
    p.add_argument("--rules", required=True, help="Rules JSON path for the lane")
    p.add_argument("--frozen-eval", default=str(DEFAULT_FROZEN_EVAL), help="Frozen evaluation summary CSV path")
    p.add_argument("--min-settled", type=int, default=None, help="Decision-grade settled race threshold; defaults to the scorecard anchor-displacement gate")
    p.add_argument("--portfolio-review-settled", type=int, default=None, help="Broader settled-race milestone for portfolio review readiness; defaults to the scorecard real-money discussion gate")
    p.add_argument("--max-open", type=int, default=5, help="Maximum open rows to inspect in the underlying monitor payload")
    p.add_argument("--runner", default=str(DEFAULT_RUNNER), help="Daily runner command path to recommend when more observation is needed")
    p.add_argument("--scanner-status", help="Optional scanner status JSON path for the latest lane run")
    p.add_argument("--pipeline-status", help="Optional pipeline status JSON path for the latest lane run")
    p.add_argument("--preflight-note", help="Optional plain-text preflight note to include in the output")
    p.add_argument("--format", choices=["text", "md", "json"], default="md", help="Output format")
    p.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Optional output path")
    return p.parse_args()


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def display_path(raw: str) -> str:
    path = Path(raw).expanduser()
    candidate = path if path.is_absolute() else (BASE / path)
    try:
        return str(candidate.resolve().relative_to(BASE.resolve()))
    except Exception:
        return raw


def display_runner(raw: str) -> str:
    shown = display_path(raw)
    if shown == raw:
        return shlex.quote(raw)
    return shlex.quote(f"./{shown}")


def read_preflight_context(args: argparse.Namespace) -> dict[str, Any] | None:
    if not args.preflight_note:
        return None
    raw = str(args.preflight_note).strip()
    if not raw:
        return None
    path = Path(raw)
    suffix = path.suffix.lower()

    if path.exists() and path.is_file():
        payload: dict[str, Any] | None = None
        if suffix == ".json":
            payload = read_status_json(path)
        else:
            json_candidate = path.with_suffix(".json") if suffix == ".txt" else None
            if json_candidate and json_candidate.exists() and json_candidate.is_file():
                payload = read_status_json(json_candidate)
        text = path.read_text(encoding="utf-8").strip()
        if payload is None:
            return {"note": text} if text else None
        if text and not payload.get("note"):
            payload["note"] = text
        return payload

    if suffix == ".txt":
        json_candidate = path.with_suffix(".json")
        if json_candidate.exists() and json_candidate.is_file():
            return read_status_json(json_candidate)
        return None
    if suffix == ".json":
        return None

    return {"note": raw}


def preflight_note_text(preflight: dict[str, Any] | None) -> str | None:
    if not preflight:
        return None
    text = str(preflight.get("note") or "").strip()
    return text or None


def preflight_has_active_targets(preflight: dict[str, Any] | None) -> bool:
    if not preflight:
        return False
    calendar_reason = str(preflight.get("calendar_reason") or "").strip().lower()
    if calendar_reason:
        return calendar_reason == "active_targets"
    calendar_state = str(preflight.get("calendar_state") or "").strip().upper()
    if calendar_state:
        return calendar_state == "ACTIVE TARGETS"
    if "has_targets" in preflight:
        return bool(preflight.get("has_targets"))
    note = preflight_note_text(preflight)
    return bool(note and "primary paper-basket target tracks racing today:" in note)


def read_pipeline_payload(args: argparse.Namespace) -> dict[str, Any] | None:
    return read_status_json(Path(args.pipeline_status)) if args.pipeline_status else None


def resolve_declared_scanner_status_path(declared: str, pipeline_path: Path | None) -> Path:
    if pipeline_path is not None:
        return resolve_pipeline_declared_scanner_status_path(declared, pipeline_path)

    candidate = Path(declared).expanduser()
    if candidate.is_absolute():
        return candidate
    project_candidate = BASE / candidate
    if candidate.parts and candidate.parts[0] in {"out", "paper_trades", "logs"}:
        return project_candidate
    return project_candidate


def resolve_scanner_status_path(args: argparse.Namespace, pipeline: dict[str, Any] | None = None) -> Path | None:
    explicit = Path(args.scanner_status).expanduser() if args.scanner_status else None
    pipeline = pipeline if pipeline is not None else read_pipeline_payload(args)
    pipeline_declared = str((pipeline or {}).get("scanner_status_path") or "").strip()
    if pipeline_declared:
        pipeline_path = Path(args.pipeline_status).expanduser() if args.pipeline_status else None
        # The pipeline-declared path is authoritative even when the copied scanner
        # sidecar is missing; falling back to an existing default path can mask a
        # stale or wrong-sidecar artifact as a clean lane read.
        return resolve_declared_scanner_status_path(pipeline_declared, pipeline_path)

    if explicit and explicit.exists() and explicit.is_file():
        return explicit

    return explicit


def read_scanner_payload(args: argparse.Namespace, pipeline: dict[str, Any] | None = None) -> dict[str, Any] | None:
    scanner_path = resolve_scanner_status_path(args, pipeline)
    if scanner_path is None or not scanner_path.exists() or not scanner_path.is_file():
        return None
    return read_status_json(scanner_path)


def latest_status_artifact_issue(args: argparse.Namespace) -> str | None:
    pipeline = read_pipeline_payload(args)
    if args.pipeline_status:
        pipeline_path = Path(args.pipeline_status)
        pipeline_state = status_json_state(pipeline_path)
        if pipeline_state == "missing":
            return "The latest lane pipeline status artifact is missing. Refresh the daily wrapper before treating this lane as empty."
        if pipeline_state == "empty":
            return "The latest lane pipeline status artifact is empty. Refresh the daily wrapper before treating this lane as empty."
        if pipeline_state == "invalid_shape":
            return "The latest lane pipeline status artifact has invalid JSON shape. Refresh the daily wrapper before treating this lane as empty."
        if pipeline_state == "unreadable":
            return "The latest lane pipeline status artifact is unreadable. Refresh the daily wrapper before treating this lane as empty."
    if is_missing_scan_output(pipeline):
        return describe_missing_scan_output(pipeline, prefix="The latest lane ") + " Refresh the daily wrapper before treating this lane as empty."
    scanner_path = resolve_scanner_status_path(args, pipeline)
    if scanner_path:
        scanner_state = status_json_state(scanner_path)
        if scanner_state == "empty":
            return "The latest scanner status sidecar is empty. Refresh the daily wrapper before treating this lane as empty."
        if scanner_state == "invalid_shape":
            return "The latest scanner status sidecar has invalid JSON shape. Refresh the daily wrapper before treating this lane as empty."
        if scanner_state == "unreadable":
            return "The latest scanner status sidecar is unreadable. Refresh the daily wrapper before treating this lane as empty."
    pipeline_scanner_status_state = str((pipeline or {}).get("scanner_status_state") or "").strip().lower()
    scanner_result = str((pipeline or {}).get("scanner_result") or "").strip().lower()
    observation_reason = str((pipeline or {}).get("observation_reason") or "").strip().lower()
    scanner_sidecar_missing = scanner_path is None or not scanner_path.exists() or not scanner_path.is_file()
    if scanner_sidecar_missing and (pipeline_scanner_status_state == "empty" or scanner_result == "scanner_status_empty"):
        return "The latest scanner status sidecar was recorded empty by the pipeline, and the current scanner sidecar file is missing from this surface. Refresh the daily wrapper before treating this lane as empty."
    if scanner_sidecar_missing and (pipeline_scanner_status_state == "unreadable" or scanner_result == "scanner_status_unreadable"):
        return "The latest scanner status sidecar was recorded unreadable by the pipeline, and the current scanner sidecar file is missing from this surface. Refresh the daily wrapper before treating this lane as empty."
    if scanner_sidecar_missing and (pipeline_scanner_status_state == "invalid_shape" or scanner_result == "scanner_status_invalid_shape" or observation_reason == "scanner_status_invalid_shape"):
        return "The latest scanner status sidecar was recorded invalid-shape by the pipeline, and the current scanner sidecar file is missing from this surface. Refresh the daily wrapper before treating this lane as empty."
    return None


def is_partial_cache_empty(args: argparse.Namespace) -> bool:
    pipeline = read_pipeline_payload(args)
    scanner = read_scanner_payload(args, pipeline)
    if scanner is None and pipeline is None:
        return False
    observation_reason = str((pipeline or {}).get("observation_reason") or "")
    scanner_result = str((pipeline or {}).get("scanner_result") or (scanner or {}).get("result") or "")
    observation_result = str((pipeline or {}).get("observation_result") or "")
    if observation_reason:
        return observation_reason == "partial_cache_empty"
    return observation_result == "partial_cache_empty_run" or scanner_result == "partial_cache_no_qualifiers"


def is_missing_scan_output(pipeline: dict[str, Any] | None) -> bool:
    if pipeline is None:
        return False
    scanner_result = str(pipeline.get("scanner_result") or "")
    observation_reason = str(pipeline.get("observation_reason") or "")
    return scanner_result == "missing_scan_output" or observation_reason == "missing_scan_output"


def describe_missing_scan_output(pipeline: dict[str, Any] | None, *, prefix: str) -> str:
    reported = str((pipeline or {}).get("scanner_status_reported_result") or "").strip()
    fallback_value = str((pipeline or {}).get("scan_input_empty_fallback_value") or "").strip()
    note = f"{prefix}scanner status was readable, but the scan-output artifact was missing"
    if reported:
        note += f" after scanner status reported {reported}"
    if fallback_value:
        note += f"; the pipeline used a safe empty {fallback_value} fallback"
    else:
        note += "; the pipeline used a safe empty-scan fallback"
    note += ". Treat this as an artifact issue, not a clean no-qualifier observation."
    return note


def _status_int(pipeline: dict[str, Any] | None, scanner: dict[str, Any] | None, pipeline_key: str, scanner_key: str, default: int = 0) -> int:
    try:
        return int((pipeline or {}).get(pipeline_key, (scanner or {}).get(scanner_key, default)) or 0)
    except (TypeError, ValueError):
        return default


def latest_target_coverage_limit(args: argparse.Namespace) -> dict[str, Any] | None:
    pipeline = read_pipeline_payload(args)
    scanner = read_scanner_payload(args, pipeline)
    if scanner is None and pipeline is None:
        return None

    observation_reason = str((pipeline or {}).get("observation_reason") or "")
    observation_result = str((pipeline or {}).get("observation_result") or "")
    max_race_limit_hit = bool((pipeline or {}).get("scanner_max_race_limit_hit", (scanner or {}).get("max_race_limit_hit", False)))
    raw_hits = _status_int(pipeline, scanner, "scanner_raw_hit_count", "raw_hit_count")
    scan_hits = _status_int(pipeline, scanner, "scan_hit_count", "emitted_hit_count")
    recommendation_count = _status_int(pipeline, scanner, "recommendation_count", "recommendation_count")
    bet_count = _status_int(pipeline, scanner, "bet_count", "bet_count")
    race_details_attempted = _status_int(pipeline, scanner, "scanner_race_details_attempted", "race_details_attempted")
    target_race_count = _status_int(pipeline, scanner, "scanner_target_race_count", "target_race_count")
    is_limited = (
        observation_reason in {"max_race_limit_empty", "max_race_limit_with_activity"}
        or observation_result in {"limited_coverage_empty_run", "limited_coverage_with_activity"}
        or (max_race_limit_hit and target_race_count > 0)
    )
    if not is_limited:
        return None
    full_target_coverage_min_races = _status_int(
        pipeline,
        scanner,
        "scanner_full_target_coverage_min_races",
        "full_target_coverage_min_races",
        target_race_count,
    )
    unattempted_target_race_count = _status_int(
        pipeline,
        scanner,
        "scanner_unattempted_target_race_count",
        "unattempted_target_race_count",
        max(0, target_race_count - race_details_attempted),
    )
    with_activity = (
        observation_reason == "max_race_limit_with_activity"
        or observation_result == "limited_coverage_with_activity"
        or any(count > 0 for count in (raw_hits, scan_hits, recommendation_count, bet_count))
    )
    return {
        "with_activity": with_activity,
        "raw_hits": raw_hits,
        "scan_hits": scan_hits,
        "recommendation_count": recommendation_count,
        "bet_count": bet_count,
        "race_details_attempted": race_details_attempted,
        "target_race_count": target_race_count,
        "full_target_coverage_min_races": full_target_coverage_min_races,
        "unattempted_target_race_count": unattempted_target_race_count,
    }


def describe_target_coverage_limit(limit: dict[str, Any]) -> str:
    attempted = int(limit.get("race_details_attempted") or 0)
    target_count = int(limit.get("target_race_count") or 0)
    unattempted = int(limit.get("unattempted_target_race_count") or 0)
    min_races = int(limit.get("full_target_coverage_min_races") or 0)
    scan_hits = int(limit.get("scan_hits") or 0)
    raw_hits = int(limit.get("raw_hits") or 0)
    recommendations = int(limit.get("recommendation_count") or 0)

    attempted_phrase = f" after {attempted} candidate race-detail attempt(s)" if attempted else " before full target coverage"
    note = f"Latest run context: the latest live scan hit the --max-races cap{attempted_phrase}"
    coverage_parts: list[str] = []
    if target_count:
        coverage_parts.append(f"{target_count} target candidate race(s)")
    if unattempted:
        coverage_parts.append(f"{unattempted} target candidate race(s) unattempted")
    if min_races:
        coverage_parts.append(f"raise --max-races to at least {min_races} for full target coverage")
    if coverage_parts:
        note += " (" + "; ".join(coverage_parts) + ")"

    if limit.get("with_activity"):
        activity_hits = raw_hits or scan_hits
        activity_label = f"{activity_hits} raw hit(s)" if raw_hits else f"{activity_hits} scanner hit(s)"
        note += f", while still preserving {recommendations} recommendation(s) from {activity_label}. Keep that activity, but rerun with a high enough cap before reading the day as full-coverage evidence."
    else:
        note += ", so treat the empty result as limited target coverage, not a clean zero-hit observation. Rerun with a high enough cap before reading the lane as quiet."
    return note


def summarize_roi_gap_reasons(rows: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        raw_reason = str(row.get("roi_gap_reason") or "missing return/cost/timestamp coverage").strip()
        for part in [piece.strip() for piece in raw_reason.split(";") if piece.strip()]:
            counts[part] = counts.get(part, 0) + 1
    if not counts:
        return "missing return/cost/timestamp coverage"
    return ", ".join(f"{reason}: {count}" for reason, count in sorted(counts.items()))


def latest_pipeline_failure(args: argparse.Namespace) -> dict[str, Any] | None:
    pipeline = read_pipeline_payload(args)
    if pipeline is None or str(pipeline.get("result") or "") != "pipeline_error":
        return None
    stage = str(pipeline.get("stage") or "")
    error_type = str(pipeline.get("error_type") or "")
    error = str(pipeline.get("error") or pipeline.get("scanner_error") or "")
    headline = {
        "recommender": "recommender failure",
        "logger": "logger failure",
    }.get(stage, "pipeline failure")
    return {
        "headline": headline,
        "stage": stage,
        "last_completed_stage": str(pipeline.get("last_completed_stage") or ""),
        "scan_hit_count": int(pipeline.get("scan_hit_count", 0) or 0),
        "recommendation_count": int(pipeline.get("recommendation_count", 0) or 0),
        "bet_count": int(pipeline.get("bet_count", 0) or 0),
        "observation_result": str(pipeline.get("observation_result") or ""),
        "error_type": error_type,
        "error": error,
    }


def scanner_failure_detail(pipeline: dict[str, Any] | None, scanner: dict[str, Any] | None) -> str:
    for key, source in (
        ("scanner_error", pipeline),
        ("error", scanner),
        ("error", pipeline),
    ):
        detail = str((source or {}).get(key) or "").strip()
        if detail:
            return detail
    return ""


def scanner_failure_is_api_access(
    detail: str,
    pipeline: dict[str, Any] | None = None,
    scanner: dict[str, Any] | None = None,
) -> bool:
    if bool((pipeline or {}).get("scanner_api_access_failure", (scanner or {}).get("api_access_failure", False))):
        return True
    for raw_status in (
        (pipeline or {}).get("scanner_http_status"),
        (scanner or {}).get("http_status"),
    ):
        try:
            if int(raw_status or 0) in {401, 403}:
                return True
        except (TypeError, ValueError):
            pass
    failure_class = str((pipeline or {}).get("scanner_api_failure_class", (scanner or {}).get("api_failure_class", ""))).strip()
    if failure_class == "api_access_failure":
        return True
    lowered = detail.lower()
    return any(token in lowered for token in ("403", "forbidden", "unauthorized", "access denied", "api access"))


def scanner_failure_operator_routing(
    pipeline: dict[str, Any] | None,
    scanner: dict[str, Any] | None,
    *,
    is_api_access: bool = False,
) -> tuple[str, str]:
    action = str(
        (pipeline or {}).get(
            "scanner_api_failure_operator_action",
            (scanner or {}).get("api_failure_operator_action", ""),
        ) or ""
    ).strip()
    recheck_command = str(
        (pipeline or {}).get(
            "scanner_api_failure_recheck_command",
            (scanner or {}).get("api_failure_recheck_command", ""),
        ) or ""
    ).strip()
    if is_api_access:
        action = action or API_ACCESS_OPERATOR_ACTION
        recheck_command = recheck_command or API_ACCESS_RECHECK_COMMAND
    return action, recheck_command


def scanner_stale_cache_fallback_context(
    pipeline: dict[str, Any] | None,
    scanner: dict[str, Any] | None,
) -> str:
    applied = bool((pipeline or {}).get(
        "scanner_stale_cache_fallback_applied",
        (scanner or {}).get("stale_cache_fallback_applied", False),
    ))
    if not applied:
        return ""

    fallback_kind = str((pipeline or {}).get(
        "scanner_stale_cache_fallback_kind",
        (scanner or {}).get("stale_cache_fallback_kind", ""),
    ) or "").strip()
    fallback_error_type = str((pipeline or {}).get(
        "scanner_stale_cache_fallback_error_type",
        (scanner or {}).get("stale_cache_fallback_error_type", ""),
    ) or "").strip()
    fallback_error = str((pipeline or {}).get(
        "scanner_stale_cache_fallback_error",
        (scanner or {}).get("stale_cache_fallback_error", ""),
    ) or "").strip()
    try:
        fallback_count = int((pipeline or {}).get(
            "scanner_stale_cache_fallback_count",
            (scanner or {}).get("stale_cache_fallback_count", 0),
        ) or 0)
    except (TypeError, ValueError):
        fallback_count = 0

    parts: list[str] = []
    if fallback_kind:
        parts.append(f"stale-cache fallback used for {fallback_kind}")
    else:
        parts.append("stale-cache fallback used")
    if fallback_count:
        parts.append(f"{fallback_count} stale-cache fallback(s)")
    if fallback_error_type or fallback_error:
        fallback_detail = fallback_error
        if fallback_error_type:
            fallback_detail = f"{fallback_error_type}: {fallback_error}" if fallback_error else fallback_error_type
        parts.append(f"stale-cache fallback error {fallback_detail}")
    return "; ".join(parts)


def latest_scanner_failure(args: argparse.Namespace) -> dict[str, Any] | None:
    pipeline = read_pipeline_payload(args)
    scanner = read_scanner_payload(args, pipeline)
    if scanner is None and pipeline is None:
        return None
    if is_cache_only_miss(scanner, pipeline):
        return None

    scanner_result = str((pipeline or {}).get("scanner_result") or (scanner or {}).get("result") or "").strip()
    observation_result = str((pipeline or {}).get("observation_result") or "").strip()
    observation_reason = str((pipeline or {}).get("observation_reason") or "").strip()
    if not (
        observation_result == "scanner_failed_empty_run"
        or scanner_result == "scanner_error"
        or observation_reason in {"scanner_failure", "api_access_failure"}
    ):
        return None

    detail = scanner_failure_detail(pipeline, scanner)
    is_api_access = scanner_failure_is_api_access(detail, pipeline, scanner)
    operator_action, recheck_command = scanner_failure_operator_routing(
        pipeline,
        scanner,
        is_api_access=is_api_access,
    )
    return {
        "detail": detail,
        "is_api_access_failure": is_api_access,
        "label": "API-access scanner failure" if is_api_access else "scanner failure",
        "operator_action": operator_action if is_api_access else "",
        "recheck_command": recheck_command if is_api_access else "",
        "stale_cache_fallback_context": scanner_stale_cache_fallback_context(pipeline, scanner),
    }


def operator_read_gate_issue_flags(
    args: argparse.Namespace,
    *,
    pipeline: dict[str, Any] | None = None,
    scanner: dict[str, Any] | None = None,
    scanner_failure: dict[str, Any] | None = None,
) -> dict[str, bool]:
    pipeline = pipeline if pipeline is not None else read_pipeline_payload(args)
    scanner = scanner if scanner is not None else read_scanner_payload(args, pipeline)

    detail = scanner_failure_detail(pipeline, scanner)
    api_access_failure = scanner_failure_is_api_access(detail, pipeline, scanner)
    stale_cache_fallback = bool((pipeline or {}).get(
        "scanner_stale_cache_fallback_applied",
        (scanner or {}).get("stale_cache_fallback_applied", False),
    ))
    cache_miss = is_cache_only_miss(scanner, pipeline)
    scanner_result = str((pipeline or {}).get("scanner_result") or (scanner or {}).get("result") or "").strip()
    observation_result = str((pipeline or {}).get("observation_result") or "").strip()
    observation_reason = str((pipeline or {}).get("observation_reason") or "").strip()
    pipeline_scanner_status_state = str((pipeline or {}).get("scanner_status_state") or "").strip().lower()
    scanner_state = ""
    scanner_path = resolve_scanner_status_path(args, pipeline)
    if scanner_path is not None:
        scanner_state = status_json_state(scanner_path)

    scanner_failure_boundary = bool(
        api_access_failure
        or stale_cache_fallback
        or (
            not cache_miss
            and (
                scanner_failure is not None
                or observation_result == "scanner_failed_empty_run"
                or scanner_result
                in {
                    "scanner_error",
                    "missing_scan_output",
                    "invalid_scan_output",
                    "scanner_status_empty",
                    "scanner_status_unreadable",
                    "scanner_status_invalid_shape",
                }
                or observation_reason
                in {
                    "scanner_failure",
                    "api_access_failure",
                    "missing_scan_output",
                    "scanner_status_empty",
                    "scanner_status_unreadable",
                    "scanner_status_invalid_shape",
                }
                or pipeline_scanner_status_state in {"empty", "unreadable", "invalid_shape"}
                or scanner_state in {"empty", "unreadable", "invalid_shape"}
            )
        )
    )

    return {
        "has_api_access_failure_context": api_access_failure,
        "has_scanner_failure_boundary": scanner_failure_boundary,
        "has_stale_cache_fallback_context": stale_cache_fallback,
    }


def format_operator_read_gate_issue_flags(issue_flags: dict[str, Any]) -> str:
    parts: list[str] = []
    for flag in STATUS_OPERATOR_READ_GATE_ISSUE_FLAGS:
        value = issue_flags.get(flag)
        if value is True:
            display = "true"
        elif value is False:
            display = "false"
        else:
            display = "missing"
        parts.append(f"{flag}={display}")
    return "; ".join(parts)


def describe_recent_run(args: argparse.Namespace) -> str | None:
    pipeline = read_pipeline_payload(args)
    scanner = read_scanner_payload(args, pipeline)
    if scanner is None and pipeline is None:
        return None

    scanner_result = (pipeline or {}).get("scanner_result") or (scanner or {}).get("result") or "missing"
    observation_result = (pipeline or {}).get("observation_result")
    observation_reason = str((pipeline or {}).get("observation_reason") or "")
    cache_only = bool((pipeline or {}).get("cache_only", (scanner or {}).get("cache_only", False)))
    card_count = int((scanner or {}).get("card_count", 0) or 0)
    race_count = int((scanner or {}).get("race_count", 0) or 0)
    raw_hits = int((pipeline or {}).get("scanner_raw_hit_count", (scanner or {}).get("raw_hit_count", 0)) or 0)
    scan_hits = int((pipeline or {}).get("scan_hit_count", (scanner or {}).get("emitted_hit_count", 0)) or 0)
    bet_count = int((pipeline or {}).get("bet_count", 0) or 0)
    recommendation_count = int((pipeline or {}).get("recommendation_count", 0) or 0)
    pipeline_failure = latest_pipeline_failure(args)

    if pipeline_failure:
        note = f"Latest run context: the latest lane run ended in {pipeline_failure['headline']}."
        if pipeline_failure["last_completed_stage"]:
            note += f" Last completed stage: {pipeline_failure['last_completed_stage']}."
        if pipeline_failure["stage"]:
            note += f" Stage: {pipeline_failure['stage']}."
        if pipeline_failure["stage"] == "recommender" and pipeline_failure["scan_hit_count"]:
            note += f" Scanner hits before failure: {pipeline_failure['scan_hit_count']}."
        if pipeline_failure["stage"] == "logger" and pipeline_failure["recommendation_count"]:
            note += f" Recommendations built before failure: {pipeline_failure['recommendation_count']}."
            if pipeline_failure["bet_count"]:
                note += f" BET recommendations before failure: {pipeline_failure['bet_count']}."
            if pipeline_failure["observation_result"]:
                note += f" Pre-error lane context: {pipeline_failure['observation_result']}."
        if pipeline_failure["error_type"]:
            note += f" Error type: {pipeline_failure['error_type']}."
        if pipeline_failure["error"]:
            note += f" Detail: {pipeline_failure['error']}"
        return note

    if is_cache_only_miss(scanner, pipeline):
        return "Latest run context: the latest cache-only check could not start because today's cache files were missing. That is a cache miss, not evidence about the lane rules."

    if is_missing_scan_output(pipeline):
        return describe_missing_scan_output(pipeline, prefix="Latest run context: ")

    if observation_result == "scanner_failed_empty_run" or scanner_result == "scanner_error":
        note = "Latest run context: scanner failed before producing signals."
        detail = scanner_failure_detail(pipeline, scanner)
        if detail:
            note += f" Detail: {detail}"
        if scanner_failure_is_api_access(detail, pipeline, scanner):
            note += " Treat this as API-access-failure operator context only, not a no-target, clean-empty, or forward-performance read."
            stale_cache_fallback_context = scanner_stale_cache_fallback_context(pipeline, scanner)
            if stale_cache_fallback_context:
                note += f" {stale_cache_fallback_context}."
            operator_action, recheck_command = scanner_failure_operator_routing(
                pipeline,
                scanner,
                is_api_access=True,
            )
            if operator_action:
                note += f" Sidecar action: {operator_action}."
            if recheck_command:
                note += f" Recheck command: {recheck_command}."
        elif not cache_only:
            note += " Treat this as scanner-error operator context only, not a no-target, clean-empty, or forward-performance read."
        if cache_only:
            note += " This was not a normal empty read, so check the sidecars before treating it as evidence."
        return note

    if observation_reason == "partial_cache_with_activity" or observation_result == "partial_cache_with_activity":
        activity_hits = raw_hits or scan_hits
        hit_label = f"{activity_hits} raw hit(s)" if raw_hits else f"{activity_hits} hit(s)"
        return f"Latest run context: the latest run depended on partial cache data but still produced {recommendation_count} recommendation(s) from {hit_label}, so keep the activity but do not read it like full-coverage evidence."

    if observation_reason == "partial_cache_empty" or observation_result == "partial_cache_empty_run" or scanner_result == "partial_cache_no_qualifiers":
        return "Latest run context: the latest run depended on partial cache data and finished empty, so treat the empty result as an operational limitation, not evidence."

    target_coverage_limit = latest_target_coverage_limit(args)
    if target_coverage_limit:
        return describe_target_coverage_limit(target_coverage_limit)

    if observation_result == "clean_empty_run" or scanner_result in {"no_qualifiers", "no_matching_cards", "reused_input_empty"}:
        if scanner_result == "no_matching_cards" or (card_count == 0 and race_count == 0):
            return "Latest run context: no matching cards were available for this ruleset in the latest scan window."
        mode = "cache-only check" if cache_only else "live scan"
        scope = f" across {card_count} card(s) and {race_count} race(s)" if card_count or race_count else ""
        return f"Latest run context: the latest {mode} completed cleanly and found no qualifying races{scope}."

    if observation_result == "bets_ready":
        return f"Latest run context: the latest run produced {bet_count} BET recommendation(s) out of {recommendation_count} total recommendation(s)."

    if observation_result == "signals_logged_no_bet":
        return f"Latest run context: the latest run logged signals but produced no BET recommendations ({recommendation_count} recommendation(s), {raw_hits} raw hit(s))."

    return None


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    requested_min_settled = getattr(args, "min_settled", None)
    requested_portfolio_review_settled = getattr(args, "portfolio_review_settled", None)
    monitor_args = SimpleNamespace(
        signals_ledger=args.signals_ledger,
        recommendation_ledger=args.recommendation_ledger,
        settlement_ledger=args.settlement_ledger,
        rules=args.rules,
        frozen_eval=args.frozen_eval,
        min_settled=requested_min_settled,
        portfolio_review_settled=requested_portfolio_review_settled,
        max_open=args.max_open,
        format="json",
        output=None,
    )
    monitor_payload = build_monitor_payload(monitor_args)
    forward = monitor_payload["forward"]
    observed = forward["portfolio_observed"]
    open_payload = monitor_payload["open_settlements"]
    incomplete_payload = monitor_payload["incomplete_settlements"]
    roi_gap_payload = monitor_payload["roi_gap_settlements"]
    roi_gap_reason_summary = summarize_roi_gap_reasons(roi_gap_payload["rows"])
    recent_run_context = describe_recent_run(args)
    preflight_context = read_preflight_context(args)
    preflight_note = preflight_note_text(preflight_context)
    active_targets_today = preflight_has_active_targets(preflight_context)
    status_artifact_issue = latest_status_artifact_issue(args)
    partial_cache_empty = is_partial_cache_empty(args)
    pipeline_failure = latest_pipeline_failure(args)
    scanner_failure = latest_scanner_failure(args)
    issue_flags = operator_read_gate_issue_flags(args, scanner_failure=scanner_failure)
    target_coverage_limit = latest_target_coverage_limit(args)
    sample_progress = forward["sample_progress"]
    first_read = sample_progress["first_read"]
    portfolio_review = sample_progress["portfolio_review"]
    gate_minimums = monitor_payload["decision_gate_minimums"]
    gate_caution = next_steps_gate_caution(gate_minimums)
    active_min_settled = int(forward["min_settled"])
    active_portfolio_review_settled = int(forward["portfolio_review_settled"])

    signals_ledger_disp = display_path(args.signals_ledger)
    recommendation_ledger_disp = display_path(args.recommendation_ledger)
    settlement_ledger_disp = display_path(args.settlement_ledger)
    rules_disp = display_path(args.rules)
    settlement_helper_disp = display_path(str(SETTLEMENT_HELPER))
    lane_monitor_disp = display_path(str(LANE_MONITOR))
    forward_check_disp = display_path(str(FORWARD_CHECK))

    lane_monitor_cmd = shell_join([
        "python3", lane_monitor_disp,
        "--signals-ledger", signals_ledger_disp,
        "--recommendation-ledger", recommendation_ledger_disp,
        "--settlement-ledger", settlement_ledger_disp,
        "--rules", rules_disp,
    ])
    forward_check_cmd = shell_join([
        "python3", forward_check_disp,
        "--signals-ledger", signals_ledger_disp,
        "--recommendation-ledger", recommendation_ledger_disp,
        "--settlement-ledger", settlement_ledger_disp,
        "--rules", rules_disp,
    ])
    list_open_cmd = shell_join([
        "python3", settlement_helper_disp,
        "list-open",
        "--settlement-ledger", settlement_ledger_disp,
    ])
    settle_example_key = (
        open_payload["rows"][0]["signal_key"]
        if open_payload["rows"] else
        incomplete_payload["rows"][0]["signal_key"] if incomplete_payload["rows"] else
        "<signal_key>"
    )
    settle_cmd = shell_join([
        "python3", settlement_helper_disp,
        "settle",
        "--settlement-ledger", settlement_ledger_disp,
        "--signal-key", settle_example_key,
        "--outcome", "<HIT_OR_MISS>",
        "--actual-return", "<dollars_returned>",
        "--actual-cost", "<dollars_wagered>",
        "--settled-ts", "YYYY-MM-DDTHH:MM:SS",
        "--notes", "manual settlement entry",
    ])
    runner_cmd = display_runner(args.runner)

    if open_payload["count"] > 0 or incomplete_payload["count"] > 0:
        state = "NEEDS SETTLEMENT"
        if open_payload["count"] > 0 and incomplete_payload["count"] > 0:
            why = (
                f"{open_payload['count']} settlement row(s) are still open and {incomplete_payload['count']} row(s) are marked settled but still missing outcome data, so the clean next step is ledger cleanup before asking the forward checker for a fresher read."
            )
            commands = [list_open_cmd, settle_cmd, lane_monitor_cmd]
        elif open_payload["count"] > 0:
            why = (
                f"{open_payload['count']} settlement row(s) are still open, so the clean next step is result entry before asking the forward checker for a fresher read."
            )
            commands = [list_open_cmd, settle_cmd, lane_monitor_cmd]
        else:
            why = (
                f"{incomplete_payload['count']} settlement row(s) are marked settled but still missing outcome data, so fix those ledger rows before treating the forward metrics as complete."
            )
            commands = [lane_monitor_cmd, settle_cmd, forward_check_cmd]
    elif roi_gap_payload["count"] > 0:
        state = "REPAIR ROI COVERAGE"
        why = (
            f"{roi_gap_payload['count']} settled outcome row(s) still cannot contribute to realized ROI ({roi_gap_reason_summary}), so fill the missing or malformed return/cost/timestamp values before treating the forward metrics as complete."
        )
        commands = [lane_monitor_cmd, settle_cmd, forward_check_cmd]
    elif status_artifact_issue:
        state = "REFRESH RUN ARTIFACTS"
        why = status_artifact_issue
        commands = [runner_cmd, lane_monitor_cmd, list_open_cmd]
    elif active_targets_today and recent_run_context and "cache-only check could not start" in recent_run_context:
        state = "RERUN LIVE CHECK"
        why = "Active-basket tracks are racing today, but the latest cache-only check could not start because today's cache files were missing. Re-run without --cache-only before treating this lane as empty."
        commands = [runner_cmd, lane_monitor_cmd, list_open_cmd]
    elif active_targets_today and partial_cache_empty:
        state = "LIMITED CACHE COVERAGE"
        why = "Active-basket tracks are racing today, but the latest run finished empty on partial cache coverage. Refresh the lane live before treating this as a true zero-hit day."
        commands = [runner_cmd, lane_monitor_cmd, list_open_cmd]
    elif pipeline_failure:
        state = "CHECK PIPELINE FAILURE"
        failure_context = ""
        if pipeline_failure["stage"] == "recommender" and pipeline_failure["scan_hit_count"]:
            failure_context = f" The scanner had already found {pipeline_failure['scan_hit_count']} hit(s) before the recommender failed."
        elif pipeline_failure["stage"] == "logger" and pipeline_failure["recommendation_count"]:
            failure_context = f" The recommender had already produced {pipeline_failure['recommendation_count']} recommendation(s)"
            if pipeline_failure["bet_count"]:
                failure_context += f", including {pipeline_failure['bet_count']} BET recommendation(s)"
            failure_context += ", before logging failed."
        why = f"The latest lane run ended in {pipeline_failure['headline']}, so treat this as an operational issue instead of normal observation noise.{failure_context} Refresh the daily wrapper and re-check the lane before reading it as evidence."
        commands = [runner_cmd, lane_monitor_cmd, list_open_cmd]
    elif scanner_failure:
        state = "CHECK SCANNER FAILURE"
        detail = scanner_failure["detail"]
        detail_text = f" Detail: {detail}" if detail else ""
        failure_label = scanner_failure["label"]
        sidecar_action_text = ""
        stale_cache_fallback_text = ""
        if scanner_failure.get("stale_cache_fallback_context"):
            stale_cache_fallback_text = f" {scanner_failure['stale_cache_fallback_context']}."
        if scanner_failure.get("operator_action"):
            sidecar_action_text += f" Sidecar action: {scanner_failure['operator_action']}."
        if scanner_failure.get("recheck_command"):
            sidecar_action_text += f" Recheck command: {scanner_failure['recheck_command']}."
        why = (
            f"The latest lane scanner failed before producing signals.{detail_text} "
            f"Treat this as {failure_label} operator context, not a no-target day, clean-empty scan, "
            "settled ROI, promotion, live-profitability, or real-money evidence. Refresh the daily wrapper "
            f"and re-check scanner/preflight sidecars before reading the lane as evidence.{stale_cache_fallback_text}{sidecar_action_text}"
        )
        commands = [scanner_failure.get("recheck_command") or runner_cmd, lane_monitor_cmd, list_open_cmd]
    elif target_coverage_limit:
        state = "LIMITED TARGET COVERAGE"
        min_races = int(target_coverage_limit.get("full_target_coverage_min_races") or 0)
        unattempted = int(target_coverage_limit.get("unattempted_target_race_count") or 0)
        cap_detail = f" raise --max-races to at least {min_races} for full target coverage" if min_races else " rerun with a high enough --max-races cap for full target coverage"
        unattempted_detail = f" with {unattempted} target candidate race(s) still unattempted" if unattempted else ""
        why = f"The latest lane run hit the --max-races cap{unattempted_detail}, so it is limited target coverage rather than a clean empty observation;{cap_detail} before reading this lane as quiet or full-coverage evidence."
        commands = [runner_cmd, lane_monitor_cmd, list_open_cmd]
    elif observed["settled_with_roi"] <= 0:
        state = "WAITING FOR FIRST SETTLED RACES"
        why = (
            f"No ROI-complete races are settled yet. The first statistical read is still {first_read['current']}/{first_read['threshold']} ROI-complete settled rows, and the broader portfolio review gate is {portfolio_review['current']}/{portfolio_review['threshold']}, so the right move is to keep the daily observation loop running instead of over-reading empty forward metrics."
        )
        if gate_caution:
            why += f" {gate_caution}"
        commands = [runner_cmd, lane_monitor_cmd, list_open_cmd]
    elif observed["settled_with_roi"] < active_min_settled:
        state = "COLLECTING SAMPLE"
        why = (
            f"There are {observed['settled_with_roi']} ROI-complete settled races ({observed['settled']} outcome-settled), which is still below the first statistical-read threshold of {active_min_settled} ({first_read['remaining']} more needed). The broader portfolio review gate is still {portfolio_review['current']}/{portfolio_review['threshold']}, so keep refreshing the lane read but do not treat it as promotion-grade evidence yet."
        )
        if gate_caution:
            why += f" {gate_caution}"
        commands = [lane_monitor_cmd, forward_check_cmd, runner_cmd]
    else:
        state = "DECISION-GRADE REVIEW"
        why = (
            f"The lane has reached the first statistical-read threshold at {first_read['current']}/{first_read['threshold']} ROI-complete settled races, so it is worth reading the forward check and lane monitor as a genuine benchmark comparison instead of just an early-noise snapshot. "
            + (
                f"It has also reached the broader portfolio review gate at {portfolio_review['current']}/{portfolio_review['threshold']}."
                if portfolio_review['ready'] else
                f"The broader portfolio review gate is still {portfolio_review['current']}/{portfolio_review['threshold']} ({portfolio_review['remaining']} more needed)."
            )
        )
        if gate_caution:
            why += f" {gate_caution}"
        commands = [forward_check_cmd, lane_monitor_cmd, list_open_cmd]

    return {
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "evidence_boundary_text": EVIDENCE_BOUNDARY_TEXT,
        "lane_label": monitor_payload["lane_label"],
        "state": state,
        "why": why,
        "assessment": forward["portfolio_assessment"],
        "settled": observed["settled"],
        "open": observed["open"],
        "open_settlements": open_payload["count"],
        "incomplete_settlements": incomplete_payload["count"],
        "roi_gap_settlements": roi_gap_payload["count"],
        "roi_gap_reason_summary": roi_gap_reason_summary,
        "roi_covered_settled": observed["settled_with_roi"],
        "roi_missing_settled": max(observed["settled"] - observed["settled_with_roi"], 0),
        "min_settled": active_min_settled,
        "portfolio_review_settled": active_portfolio_review_settled,
        "decision_gate_minimums": gate_minimums,
        "decision_gate_caution": gate_caution,
        "sample_progress": sample_progress,
        "recent_run_context": recent_run_context,
        "scanner_failure_operator_action": scanner_failure.get("operator_action") if scanner_failure else None,
        "scanner_failure_recheck_command": scanner_failure.get("recheck_command") if scanner_failure else None,
        "has_api_access_failure_context": issue_flags["has_api_access_failure_context"],
        "has_scanner_failure_boundary": issue_flags["has_scanner_failure_boundary"],
        "has_stale_cache_fallback_context": issue_flags["has_stale_cache_fallback_context"],
        "operator_read_gate_issue_flags": {
            key: issue_flags[key]
            for key in STATUS_OPERATOR_READ_GATE_ISSUE_FLAGS
        },
        "status_artifact_issue": status_artifact_issue,
        "preflight_note": preflight_note,
        "commands": commands,
        "files": {
            "signals_ledger": signals_ledger_disp,
            "recommendation_ledger": recommendation_ledger_disp,
            "settlement_ledger": settlement_ledger_disp,
            "rules": rules_disp,
        },
    }


def render_text(payload: dict[str, Any]) -> str:
    first_read = payload["sample_progress"]["first_read"]
    portfolio_review = payload["sample_progress"]["portfolio_review"]

    roi_line = (
        f"- ROI coverage: {payload['roi_covered_settled']}/{payload['settled']} settled races are ROI-complete with return/cost/timestamp coverage ({payload['roi_missing_settled']} still missing coverage)"
        if payload['settled'] else
        "- ROI coverage: 0/0 settled races are ROI-complete (no settled outcomes yet)"
    )

    lines = [
        f"{payload['lane_label']} next steps",
        f"- valid_evidence_scope={payload['valid_evidence_scope']}",
        f"- Evidence boundary: {payload['evidence_boundary_text']}",
        f"- State: {payload['state']}",
        f"- Forward assessment: {payload['assessment']}",
        f"- Settled races: {payload['settled']} | open races: {payload['open']} | open settlement rows: {payload['open_settlements']} | settled rows missing outcome: {payload['incomplete_settlements']}",
        roi_line,
        *(
            [f"- Settled rows missing ROI-complete coverage: {payload['roi_gap_settlements']} ({payload['roi_gap_reason_summary']})"]
            if payload.get("roi_gap_settlements") else []
        ),
        (
            f"- First statistical-read progress: {first_read['current']}/{first_read['threshold']} ROI-complete settled ({first_read['remaining']} more needed)"
            if not first_read["ready"] else
            f"- First statistical-read progress: {first_read['current']}/{first_read['threshold']} ROI-complete settled (threshold reached)"
        ),
        (
            f"- Broader portfolio-review progress: {portfolio_review['current']}/{portfolio_review['threshold']} ROI-complete settled ({portfolio_review['remaining']} more needed)"
            if not portfolio_review["ready"] else
            f"- Broader portfolio-review progress: {portfolio_review['current']}/{portfolio_review['threshold']} ROI-complete settled (threshold reached)"
        ),
        f"- Gate source: {gate_source_text(payload['decision_gate_minimums'])}",
        f"- Active gates: first_read={payload['min_settled']}; portfolio_review={payload['portfolio_review_settled']}. {next_steps_gate_alignment_read(payload['decision_gate_minimums'])}.",
        f"- Operator read-gate issue flags: {format_operator_read_gate_issue_flags(payload.get('operator_read_gate_issue_flags') or {})}",
        *( [f"- Decision-gate caution: {payload['decision_gate_caution']}"] if payload.get("decision_gate_caution") else [] ),
        f"- Why: {payload['why']}",
        *(
            [f"- Run artifact caution: {payload['status_artifact_issue']}"]
            if payload.get("status_artifact_issue") and payload.get("status_artifact_issue") != payload.get("why") else []
        ),
        *( [f"- {payload['recent_run_context']}"] if payload.get('recent_run_context') else [] ),
        *( [f"- {payload['preflight_note']}"] if payload.get('preflight_note') else [] ),
        "- Recommended commands:",
    ]
    for i, cmd in enumerate(payload["commands"], start=1):
        lines.append(f"  {i}. {cmd}")
    return "\n".join(lines) + "\n"


def render_md(payload: dict[str, Any]) -> str:
    first_read = payload["sample_progress"]["first_read"]
    portfolio_review = payload["sample_progress"]["portfolio_review"]

    roi_line = (
        f"- ROI coverage: `{payload['roi_covered_settled']}/{payload['settled']}` settled races are ROI-complete with return/cost/timestamp coverage (`{payload['roi_missing_settled']}` still missing coverage)"
        if payload['settled'] else
        "- ROI coverage: `0/0` settled races are ROI-complete (no settled outcomes yet)"
    )

    lines = [
        "# Paper-Trade Next Steps",
        "",
        f"Lane: **{payload['lane_label']}**",
        "",
        "## Evidence Boundary",
        "",
        f"- `valid_evidence_scope={payload['valid_evidence_scope']}`",
        f"- {payload['evidence_boundary_text']}",
        "",
        "## Decision-Gate Source",
        "",
        f"- Source: `{payload['decision_gate_minimums']['source_path']}`; loaded={payload['decision_gate_minimums']['source_loaded']}; fallback_used={payload['decision_gate_minimums']['fallback_used']}.",
        f"- Scorecard `decision_gate_minimums`: anchor_displacement={payload['decision_gate_minimums']['anchor_displacement_min_roi_complete_settled_observations']} ROI-complete same-candidate settled observations; phase8_promotion_review={payload['decision_gate_minimums']['phase8_promotion_review_min_roi_complete_settled_observations']} ROI-complete shadow observations; real_money_discussion={payload['decision_gate_minimums']['real_money_discussion_min_total_settled_observations_with_usable_roi']} total settled observations with usable ROI; real_money_requires={'; '.join(payload['decision_gate_minimums']['real_money_discussion_also_requires'])}.",
        f"- Active next-step gates: min_settled={payload['min_settled']}; portfolio_review_settled={payload['portfolio_review_settled']}. {next_steps_gate_alignment_read(payload['decision_gate_minimums'])}.",
        *( [f"- Decision-gate caution: {payload['decision_gate_caution']}"] if payload.get("decision_gate_caution") else [] ),
        "- These thresholds are posture-gate metadata for action routing only; they are not live-profitability, promotion, anchor-change, or real-money evidence.",
        "",
        "## Current State",
        "",
        f"- State: **{payload['state']}**",
        f"- Forward assessment: **{payload['assessment']}**",
        f"- Settled races: `{payload['settled']}`",
        f"- Open races: `{payload['open']}`",
        f"- Open settlement rows: `{payload['open_settlements']}`",
        f"- Settled rows missing outcome: `{payload['incomplete_settlements']}`",
        roi_line,
        *(
            [f"- Settled rows missing ROI-complete coverage: `{payload['roi_gap_settlements']}` ({payload['roi_gap_reason_summary']})"]
            if payload.get("roi_gap_settlements") else []
        ),
        (
            f"- First statistical-read progress: `{first_read['current']}/{first_read['threshold']}` ROI-complete settled ({first_read['remaining']} more needed)"
            if not first_read["ready"] else
            f"- First statistical-read progress: `{first_read['current']}/{first_read['threshold']}` ROI-complete settled; threshold reached"
        ),
        (
            f"- Broader portfolio-review progress: `{portfolio_review['current']}/{portfolio_review['threshold']}` ROI-complete settled ({portfolio_review['remaining']} more needed)"
            if not portfolio_review["ready"] else
            f"- Broader portfolio-review progress: `{portfolio_review['current']}/{portfolio_review['threshold']}` ROI-complete settled; threshold reached"
        ),
        f"- Operator read-gate issue flags: `{format_operator_read_gate_issue_flags(payload.get('operator_read_gate_issue_flags') or {})}`",
        f"- Why: {payload['why']}",
        *(
            [f"- Run artifact caution: {payload['status_artifact_issue']}"]
            if payload.get("status_artifact_issue") and payload.get("status_artifact_issue") != payload.get("why") else []
        ),
        *( [f"- {payload['recent_run_context']}"] if payload.get('recent_run_context') else [] ),
        *( [f"- {payload['preflight_note']}"] if payload.get('preflight_note') else [] ),
        "",
        "## Recommended next commands",
        "",
    ]
    for i, cmd in enumerate(payload["commands"], start=1):
        lines.append(f"{i}. `{cmd}`")
    lines.extend([
        "",
        "## Files behind this recommendation",
        "",
        f"- Signals ledger: `{payload['files']['signals_ledger']}`",
        f"- Recommendation ledger: `{payload['files']['recommendation_ledger']}`",
        f"- Settlement ledger: `{payload['files']['settlement_ledger']}`",
        f"- Rules: `{payload['files']['rules']}`",
        "",
    ])
    return "\n".join(lines)


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    payload = build_payload(args)

    if args.format == "json":
        output = json.dumps(payload, indent=2) + "\n"
    elif args.format == "text":
        output = render_text(payload)
    else:
        output = render_md(payload) + "\n"

    if args.output:
        write_output(Path(args.output), output)
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
