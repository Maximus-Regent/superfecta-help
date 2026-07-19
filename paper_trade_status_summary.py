#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
DEFAULT_SCANNER_STATUS = BASE / "out" / "live_scan_latest.status.json"
DEFAULT_PIPELINE_STATUS = BASE / "out" / "paper_trade_pipeline_status.json"
STATUS_EVIDENCE_BOUNDARY = (
    "Operational status summary only: classifies scanner/pipeline state; "
    "not live profitability, promotion, or real-money evidence."
)
STATUS_VALID_SCOPE = "workflow_state_triage_only"
STATUS_OPERATOR_READ_GATE_ISSUE_FLAGS = (
    "has_api_access_failure_context",
    "has_scanner_failure_boundary",
    "has_stale_cache_fallback_context",
)
STATUS_EVIDENCE_BOUNDARY_METADATA = {
    "artifact_role": "paper-trade base status summary",
    "valid_use": "classify scanner/pipeline operational state before lane enrichment",
    "valid_evidence_scope": STATUS_VALID_SCOPE,
    "not_new_forward_evidence_by_itself": True,
    "not_live_paper_trade_ledger": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_anchor_change_evidence": True,
    "not_companion_change_evidence": True,
    "not_phase8_promotion_evidence": True,
    "not_scope_change_evidence": True,
    "not_real_money_evidence": True,
    "not_baq_as_bel_evidence": True,
    "quiet_run_classification_is_not_performance_evidence": True,
    "clean_empty_run_is_not_forward_performance_evidence": True,
    "limited_coverage_is_operational_context_only": True,
    "api_access_failure_is_operator_context_only": True,
    "broken_sidecars_are_not_clean_empty_evidence": True,
    "requires_lane_enrichment_and_settlement_audit_before_performance_read": True,
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Summarize scanner/pipeline status sidecars into a report-safe one-line note"
    )
    p.add_argument("--scanner-status", default=str(DEFAULT_SCANNER_STATUS), help="Scanner status JSON path")
    p.add_argument("--pipeline-status", default=str(DEFAULT_PIPELINE_STATUS), help="Pipeline status JSON path")
    p.add_argument(
        "--require-pipeline-status",
        action="store_true",
        help="Treat missing, invalid-shape, or unreadable pipeline status as an explicit summary issue when scanner status is readable",
    )
    p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p.add_argument("--output", help="Optional file to save summary")
    return p.parse_args()


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def json_state(path: Path) -> str:
    if not path.exists():
        return "missing"
    if path.stat().st_size == 0:
        return "empty"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "unreadable"
    return "ok" if isinstance(data, dict) else "invalid_shape"


def resolve_declared_scanner_status_path(declared: str, pipeline_path: Path) -> Path:
    declared_path = Path(declared).expanduser()
    if declared_path.is_absolute():
        return declared_path

    local_candidate = pipeline_path.parent / declared_path
    run_root_candidate = pipeline_path.parent.parent / declared_path
    project_candidate = BASE / declared_path
    for option in (local_candidate, run_root_candidate, project_candidate):
        if option.exists() and option.is_file():
            return option

    if declared_path.parts and declared_path.parts[0] == pipeline_path.parent.name:
        return run_root_candidate
    if declared_path.parts and declared_path.parts[0] in {"out", "paper_trades", "logs"}:
        return project_candidate
    return local_candidate


def resolve_scanner_status_path(scanner_path: Path, pipeline_path: Path, pipeline: dict[str, Any] | None = None) -> Path:
    declared = str((pipeline or {}).get("scanner_status_path") or "").strip()
    if declared:
        # The pipeline-declared path is the scanner sidecar the pipeline actually used.
        # If that artifact is missing from a copied surface, report that missing declared
        # path instead of silently falling back to a possibly stale default filename.
        return resolve_declared_scanner_status_path(declared, pipeline_path)
    if scanner_path.exists() and scanner_path.is_file():
        return scanner_path
    return scanner_path


def rules_label(path_str: str | None) -> str:
    name = Path(path_str or "").name
    mapping = {
        "op_anchor_rules.json": "OP anchor",
        "phase7_live_rules.json": "Phase 7 basket",
        "phase7_current_paper_rules.json": "Phase 7 current paper",
        "phase8_shadow_rules.json": "Phase 8 shadow",
    }
    return mapping.get(name, name.replace("_", " ").replace(".json", "") or "unknown rules")


def is_cache_only_miss(scanner: dict[str, Any] | None, pipeline: dict[str, Any] | None = None) -> bool:
    observation_reason = str((pipeline or {}).get("observation_reason") or "")
    if observation_reason == "cache_only_miss":
        return True
    scanner_result = str((pipeline or {}).get("scanner_result") or (scanner or {}).get("result") or "")
    cache_only = bool((pipeline or {}).get("cache_only", (scanner or {}).get("cache_only", False)))
    error_text = str((pipeline or {}).get("scanner_error") or (scanner or {}).get("error") or "")
    return cache_only and scanner_result == "scanner_error" and "No cached data" in error_text


def status_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def summarize(
    scanner: dict[str, Any] | None,
    pipeline: dict[str, Any] | None,
    scanner_state: str = "ok",
    pipeline_state: str = "ok",
    require_pipeline_status: bool = False,
) -> dict[str, Any]:
    rules = rules_label((pipeline or scanner or {}).get("rules_path"))
    run_ts = (pipeline or scanner or {}).get("run_ts")
    scanner_result = (pipeline or {}).get("scanner_result") or (scanner or {}).get("result") or "missing"
    observation_result = (pipeline or {}).get("observation_result")
    observation_scope = str((pipeline or {}).get("observation_scope") or "")
    observation_reason = str((pipeline or {}).get("observation_reason") or "")
    pipeline_scanner_status_state = str((pipeline or {}).get("scanner_status_state") or "")
    pipeline_scanner_status_error = str((pipeline or {}).get("scanner_status_error") or "")
    pipeline_recorded_scanner_empty = (
        pipeline is not None
        and scanner_state == "missing"
        and (pipeline_scanner_status_state == "empty" or scanner_result == "scanner_status_empty")
    )
    pipeline_recorded_scanner_unreadable = (
        pipeline is not None
        and scanner_state == "missing"
        and (pipeline_scanner_status_state == "unreadable" or scanner_result == "scanner_status_unreadable")
    )
    pipeline_recorded_scanner_invalid_shape = (
        pipeline is not None
        and scanner_state == "missing"
        and scanner_result == "scanner_status_invalid_shape"
    )
    effective_scanner_status_state = (
        "empty" if pipeline_recorded_scanner_empty
        else "unreadable" if pipeline_recorded_scanner_unreadable
        else "invalid_shape" if pipeline_recorded_scanner_invalid_shape
        else scanner_state
    )
    pipeline_result = str((pipeline or {}).get("result") or "")
    pipeline_stage = str((pipeline or {}).get("stage") or "")
    pipeline_last_completed_stage = str((pipeline or {}).get("last_completed_stage") or "")
    pipeline_error_type = str((pipeline or {}).get("error_type") or "")
    pipeline_error = str((pipeline or {}).get("error") or "")
    scan_input_empty_fallback_applied = bool((pipeline or {}).get("scan_input_empty_fallback_applied", False))
    scan_input_empty_fallback_reason = str((pipeline or {}).get("scan_input_empty_fallback_reason") or "")
    scan_input_state_before_empty_fallback = str((pipeline or {}).get("scan_input_state_before_empty_fallback") or "")
    scan_input_empty_fallback_value = str((pipeline or {}).get("scan_input_empty_fallback_value") or "")
    scanner_status_reported_result = str((pipeline or {}).get("scanner_status_reported_result") or "")
    scanner_http_status = status_int((pipeline or {}).get("scanner_http_status", (scanner or {}).get("http_status", 0)))
    scanner_api_failure_class = str((pipeline or {}).get("scanner_api_failure_class", (scanner or {}).get("api_failure_class", "")) or "")
    scanner_api_access_failure = bool((pipeline or {}).get("scanner_api_access_failure", (scanner or {}).get("api_access_failure", False)))
    scanner_api_failure_valid_scope = str((pipeline or {}).get("scanner_api_failure_valid_scope", (scanner or {}).get("api_failure_valid_scope", "")) or "")
    scanner_api_failure_boundary = str((pipeline or {}).get("scanner_api_failure_boundary", (scanner or {}).get("api_failure_boundary", "")) or "")
    scanner_api_failure_operator_action = str((pipeline or {}).get("scanner_api_failure_operator_action", (scanner or {}).get("api_failure_operator_action", "")) or "")
    scanner_api_failure_recheck_command = str((pipeline or {}).get("scanner_api_failure_recheck_command", (scanner or {}).get("api_failure_recheck_command", "")) or "")
    scanner_stale_cache_fallback_applied = bool((pipeline or {}).get(
        "scanner_stale_cache_fallback_applied",
        (scanner or {}).get("stale_cache_fallback_applied", False),
    ))
    scanner_stale_cache_fallback_count = int((pipeline or {}).get(
        "scanner_stale_cache_fallback_count",
        (scanner or {}).get("stale_cache_fallback_count", 0),
    ) or 0)
    scanner_stale_cache_fallback_kind = str((pipeline or {}).get(
        "scanner_stale_cache_fallback_kind",
        (scanner or {}).get("stale_cache_fallback_kind", ""),
    ) or "")
    scanner_stale_cache_fallback_error_type = str((pipeline or {}).get(
        "scanner_stale_cache_fallback_error_type",
        (scanner or {}).get("stale_cache_fallback_error_type", ""),
    ) or "")
    scanner_stale_cache_fallback_error = str((pipeline or {}).get(
        "scanner_stale_cache_fallback_error",
        (scanner or {}).get("stale_cache_fallback_error", ""),
    ) or "")

    scan_hit_count = int((pipeline or {}).get("scan_hit_count", (scanner or {}).get("emitted_hit_count", 0)) or 0)
    raw_hit_count = int((pipeline or {}).get("scanner_raw_hit_count", (scanner or {}).get("raw_hit_count", scan_hit_count)) or 0)
    recommendation_count = int((pipeline or {}).get("recommendation_count", 0) or 0)
    bet_count = int((pipeline or {}).get("bet_count", 0) or 0)
    error_count = int((pipeline or {}).get("error_count", 0) or 0)
    missing_race_details = int((pipeline or {}).get(
        "scanner_missing_race_detail_cache_skips",
        (scanner or {}).get("missing_race_detail_cache_skips", 0),
    ) or 0)
    race_details_attempted = int((pipeline or {}).get("scanner_race_details_attempted", (scanner or {}).get("race_details_attempted", 0)) or 0)
    max_race_limit_hit = bool((pipeline or {}).get("scanner_max_race_limit_hit", (scanner or {}).get("max_race_limit_hit", 0)))
    target_race_count = int((pipeline or {}).get("scanner_target_race_count", (scanner or {}).get("target_race_count", 0)) or 0)
    full_target_coverage_min_races = int(
        (pipeline or {}).get(
            "scanner_full_target_coverage_min_races",
            (scanner or {}).get("full_target_coverage_min_races", target_race_count),
        ) or 0
    )
    unattempted_target_race_count = int(
        (pipeline or {}).get(
            "scanner_unattempted_target_race_count",
            (scanner or {}).get("unattempted_target_race_count", max(0, target_race_count - race_details_attempted)),
        ) or 0
    )
    pre_detail_skipped_race_count = int((pipeline or {}).get("scanner_pre_detail_skipped_race_count", (scanner or {}).get("pre_detail_skipped_race_count", 0)) or 0)
    scanner_partial_cache = bool((pipeline or {}).get("scanner_partial_cache", (scanner or {}).get("partial_cache", False)))
    cache_only_miss = is_cache_only_miss(scanner, pipeline)

    if pipeline is not None and scanner_state == "empty":
        headline = "scanner sidecar empty"
    elif pipeline is not None and scanner_state == "unreadable":
        headline = "scanner sidecar unreadable"
    elif pipeline is not None and scanner_state == "invalid_shape":
        headline = "scanner sidecar invalid shape"
    elif pipeline_recorded_scanner_empty:
        headline = "scanner sidecar recorded empty"
    elif pipeline_recorded_scanner_unreadable:
        headline = "scanner sidecar recorded unreadable"
    elif pipeline_recorded_scanner_invalid_shape:
        headline = "scanner sidecar recorded invalid shape"
    elif pipeline is not None and scanner_state == "missing":
        headline = "scanner sidecar missing"
    elif require_pipeline_status and scanner is not None and pipeline_state == "empty":
        headline = "pipeline sidecar empty"
    elif require_pipeline_status and scanner is not None and pipeline_state == "unreadable":
        headline = "pipeline sidecar unreadable"
    elif require_pipeline_status and scanner is not None and pipeline_state == "invalid_shape":
        headline = "pipeline sidecar invalid shape"
    elif require_pipeline_status and scanner is not None and pipeline_state == "missing":
        headline = "pipeline sidecar missing"
    elif cache_only_miss:
        headline = "cache miss (cache-only)"
    elif pipeline_result == "pipeline_error":
        if pipeline_stage == "recommender":
            headline = "recommender failure"
        elif pipeline_stage == "logger":
            headline = "logger failure"
        else:
            headline = "pipeline failure"
    elif scanner_result == "missing_scan_output" or observation_reason == "missing_scan_output":
        headline = "missing scanner output"
    elif observation_result == "scanner_failed_empty_run" or scanner_result == "scanner_error":
        if scanner_api_access_failure:
            headline = "scanner API access failure"
        else:
            headline = "scanner failure"
    elif observation_reason == "partial_cache_with_activity" or observation_result == "partial_cache_with_activity":
        headline = "partial cache with activity"
    elif observation_reason == "partial_cache_empty" or observation_result == "partial_cache_empty_run" or scanner_result == "partial_cache_no_qualifiers":
        headline = "partial cache"
    elif observation_reason == "max_race_limit_with_activity" or observation_result == "limited_coverage_with_activity":
        headline = "limited coverage with activity"
    elif observation_reason == "max_race_limit_empty" or observation_result == "limited_coverage_empty_run":
        headline = "limited coverage"
    elif observation_result == "clean_empty_run" or scanner_result in {"no_qualifiers", "no_matching_cards", "reused_input_empty"}:
        headline = "clean empty run"
    elif observation_result == "bets_ready":
        headline = "bets ready"
    elif observation_result == "signals_logged_no_bet":
        headline = "signals logged, no bet"
    elif scanner_result == "alerts_found":
        headline = "scanner alerts found"
    else:
        headline = str(observation_result or scanner_result).replace("_", " ")

    details: list[str] = []
    details.append(f"{scan_hit_count} scanner hit(s)")
    if raw_hit_count != scan_hit_count:
        details.append(f"{raw_hit_count} raw before dedup")
    if pipeline is not None:
        details.append(f"{recommendation_count} recommendation(s)")
        if bet_count:
            details.append(f"{bet_count} BET")
        if error_count:
            details.append(f"{error_count} ERROR")
    if pipeline_result == "pipeline_error":
        if pipeline_last_completed_stage:
            details.append(f"last completed stage {pipeline_last_completed_stage}")
        if pipeline_stage:
            details.append(f"stage {pipeline_stage}")
        if pipeline_stage == "recommender" and scan_hit_count:
            details.append(f"scanner hits before failure {scan_hit_count}")
        if pipeline_stage == "logger" and recommendation_count:
            details.append(f"recommendations built before failure {recommendation_count}")
            if bet_count:
                details.append(f"BET recommendations before failure {bet_count}")
            if observation_result:
                details.append(f"pre-error context {observation_result}")
        if pipeline_error_type:
            details.append(pipeline_error_type)
        if pipeline_error:
            details.append(f"detail: {pipeline_error}")
    if scanner_status_reported_result and scanner_status_reported_result != scanner_result:
        details.append(f"scanner-status reported {scanner_status_reported_result}")
    if scanner_api_access_failure:
        if scanner_http_status:
            details.append(f"HTTP {scanner_http_status}")
        details.append("API-access-failure operator context only")
        if scanner_api_failure_operator_action:
            details.append(f"operator action {scanner_api_failure_operator_action}")
        if scanner_api_failure_recheck_command:
            details.append(f"recheck command {scanner_api_failure_recheck_command}")
    if scanner_stale_cache_fallback_applied:
        if scanner_stale_cache_fallback_kind:
            details.append(f"stale cache fallback used for {scanner_stale_cache_fallback_kind}")
        else:
            details.append("stale cache fallback used")
        if scanner_stale_cache_fallback_count:
            details.append(f"{scanner_stale_cache_fallback_count} stale cache fallback(s)")
        if scanner_stale_cache_fallback_error_type or scanner_stale_cache_fallback_error:
            fallback_error = scanner_stale_cache_fallback_error
            if scanner_stale_cache_fallback_error_type:
                fallback_error = (
                    f"{scanner_stale_cache_fallback_error_type}: {fallback_error}"
                    if fallback_error
                    else scanner_stale_cache_fallback_error_type
                )
            details.append(f"stale cache fallback error {fallback_error}")
    if scanner_api_failure_class and scanner_api_failure_class != "scanner_exception":
        details.append(f"scanner failure class {scanner_api_failure_class}")
    if scan_input_empty_fallback_applied:
        if scan_input_empty_fallback_reason:
            details.append(f"safe empty scan fallback {scan_input_empty_fallback_reason}")
        else:
            details.append("safe empty scan fallback applied")
        if scan_input_state_before_empty_fallback:
            details.append(f"scan input was {scan_input_state_before_empty_fallback} before fallback")
    if scanner_partial_cache or missing_race_details:
        details.append(f"{missing_race_details} missing race detail cache file(s)")
    if target_race_count:
        details.append(f"{target_race_count} target candidate race(s)")
    if pre_detail_skipped_race_count:
        details.append(f"{pre_detail_skipped_race_count} non-target race(s) skipped before detail fetch")
    if max_race_limit_hit and race_details_attempted:
        details.append(f"max-races cap hit after {race_details_attempted} attempt(s)")
        if unattempted_target_race_count:
            details.append(f"{unattempted_target_race_count} target candidate race(s) unattempted")
        if full_target_coverage_min_races:
            details.append(f"raise --max-races to at least {full_target_coverage_min_races} for full target coverage")
    if scanner_result == "scanner_status_invalid_shape" and pipeline_scanner_status_error:
        details.append(f"scanner-status error: {pipeline_scanner_status_error}")
    if pipeline_scanner_status_state and pipeline_scanner_status_state != scanner_state:
        if scanner_state == "missing" and (pipeline_scanner_status_state in {"empty", "unreadable"} or scanner_result == "scanner_status_invalid_shape"):
            details.append("current scanner sidecar file missing")
        details.append(f"pipeline recorded scanner-status state {pipeline_scanner_status_state}")

    scanner_failure_boundary = bool(
        scanner_api_access_failure
        or (
            not cache_only_miss
            and (
                headline
                in {
                    "scanner failure",
                    "scanner API access failure",
                    "missing scanner output",
                    "scanner sidecar empty",
                    "scanner sidecar unreadable",
                    "scanner sidecar invalid shape",
                    "scanner sidecar missing",
                    "scanner sidecar recorded empty",
                    "scanner sidecar recorded unreadable",
                    "scanner sidecar recorded invalid shape",
                }
                or scanner_result
                in {
                    "scanner_error",
                    "missing_scan_output",
                    "invalid_scan_output",
                    "scanner_status_empty",
                    "scanner_status_unreadable",
                    "scanner_status_invalid_shape",
                }
                or pipeline_scanner_status_state in {"empty", "unreadable", "invalid_shape"}
            )
        )
    )
    issue_flags = {
        "has_api_access_failure_context": scanner_api_access_failure,
        "has_scanner_failure_boundary": scanner_failure_boundary,
        "has_stale_cache_fallback_context": scanner_stale_cache_fallback_applied,
    }

    line = f"{rules} run"
    if run_ts:
        line += f" {run_ts}"
    line += f": {headline}, " + ", ".join(details)

    return {
        "rules_label": rules,
        "run_ts": run_ts,
        "headline": headline,
        "scanner_result": scanner_result,
        "observation_result": observation_result,
        "observation_scope": observation_scope or None,
        "observation_reason": observation_reason or None,
        "scan_hit_count": scan_hit_count,
        "raw_hit_count": raw_hit_count,
        "recommendation_count": recommendation_count,
        "bet_count": bet_count,
        "error_count": error_count,
        "cache_only_miss": cache_only_miss,
        "scanner_partial_cache": scanner_partial_cache,
        "missing_race_detail_cache_skips": missing_race_details,
        "race_details_attempted": race_details_attempted,
        "max_race_limit_hit": max_race_limit_hit,
        "target_race_count": target_race_count,
        "full_target_coverage_min_races": full_target_coverage_min_races,
        "unattempted_target_race_count": unattempted_target_race_count,
        "pre_detail_skipped_race_count": pre_detail_skipped_race_count,
        "detail_parts": details,
        "summary_line": line,
        "pipeline_result": pipeline_result or None,
        "pipeline_stage": pipeline_stage or None,
        "pipeline_last_completed_stage": pipeline_last_completed_stage or None,
        "pipeline_error_type": pipeline_error_type or None,
        "pipeline_error": pipeline_error or None,
        "scan_input_empty_fallback_applied": scan_input_empty_fallback_applied,
        "scan_input_empty_fallback_reason": scan_input_empty_fallback_reason or None,
        "scan_input_state_before_empty_fallback": scan_input_state_before_empty_fallback or None,
        "scan_input_empty_fallback_value": scan_input_empty_fallback_value or None,
        "scanner_status_reported_result": scanner_status_reported_result or None,
        "scanner_http_status": scanner_http_status or None,
        "scanner_api_failure_class": scanner_api_failure_class or None,
        "scanner_api_access_failure": scanner_api_access_failure,
        "scanner_api_failure_valid_scope": scanner_api_failure_valid_scope or None,
        "scanner_api_failure_boundary": scanner_api_failure_boundary or None,
        "scanner_api_failure_operator_action": scanner_api_failure_operator_action or None,
        "scanner_api_failure_recheck_command": scanner_api_failure_recheck_command or None,
        "scanner_stale_cache_fallback_applied": scanner_stale_cache_fallback_applied,
        "scanner_stale_cache_fallback_count": scanner_stale_cache_fallback_count,
        "scanner_stale_cache_fallback_kind": scanner_stale_cache_fallback_kind or None,
        "scanner_stale_cache_fallback_error_type": scanner_stale_cache_fallback_error_type or None,
        "scanner_stale_cache_fallback_error": scanner_stale_cache_fallback_error or None,
        "has_api_access_failure_context": issue_flags["has_api_access_failure_context"],
        "has_scanner_failure_boundary": issue_flags["has_scanner_failure_boundary"],
        "has_stale_cache_fallback_context": issue_flags["has_stale_cache_fallback_context"],
        "operator_read_gate_issue_flags": issue_flags,
        "scanner_status_state": scanner_state,
        "effective_scanner_status_state": effective_scanner_status_state,
        "pipeline_scanner_status_state": pipeline_scanner_status_state or None,
        "pipeline_scanner_status_error": pipeline_scanner_status_error or None,
        "pipeline_status_state": pipeline_state,
        "valid_evidence_scope": STATUS_VALID_SCOPE,
        "evidence_boundary": STATUS_EVIDENCE_BOUNDARY,
        "evidence_boundary_metadata": STATUS_EVIDENCE_BOUNDARY_METADATA,
    }


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    scanner_path = Path(args.scanner_status)
    pipeline_path = Path(args.pipeline_status)
    pipeline_state = json_state(pipeline_path)
    pipeline = read_json(pipeline_path)
    resolved_scanner_path = resolve_scanner_status_path(scanner_path, pipeline_path, pipeline)
    scanner_state = json_state(resolved_scanner_path)
    scanner = read_json(resolved_scanner_path)

    if scanner is None and pipeline is None:
        raise SystemExit("No readable status JSON found. Pass --scanner-status and/or --pipeline-status.")

    payload = summarize(
        scanner,
        pipeline,
        scanner_state=scanner_state,
        pipeline_state=pipeline_state,
        require_pipeline_status=args.require_pipeline_status,
    )
    if args.format == "json":
        output = json.dumps(payload, indent=2) + "\n"
    else:
        output = payload["summary_line"] + "\n"

    if args.output:
        write_output(Path(args.output), output)
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
