#!/usr/bin/env python3
"""
Orchestrate the paper-trade recommendation pipeline.

Run path:
1. live_portfolio_scanner.py / scan_live.sh writes scanner hits
2. NYRA/model_main.py scores each scanner hit's race_id
3. paper_trade_recommender.py filters to Phase 7 combos and sizes via ev_ticket_engine.py
4. paper_trade_logger.py appends both raw signals and recommendation summaries
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).resolve().parent
DEFAULT_SCAN_INPUT = BASE / "out" / "live_scan_latest.json"
DEFAULT_RECOMMENDATION_OUTPUT_DIR = BASE / "out" / "paper_trade_recommendations_latest"
DEFAULT_LEDGER = BASE / "paper_trades" / "paper_trade_signals.csv"
DEFAULT_STATE = BASE / "paper_trades" / ".logged_signals.json"
DEFAULT_RECOMMENDATION_LEDGER = BASE / "paper_trades" / "paper_trade_recommendations.csv"
DEFAULT_RECOMMENDATION_STATE = BASE / "paper_trades" / ".logged_recommendations.json"
DEFAULT_MODEL = BASE / "Model" / "log_residual_model_normalized.json"
DEFAULT_RULES = BASE / "phase7_live_rules.json"
DEFAULT_STATUS_OUTPUT = BASE / "out" / "paper_trade_pipeline_status.json"
PIPELINE_EVIDENCE_BOUNDARY = (
    "Operational pipeline status only: records scan/recommend/log workflow state; "
    "not live profitability, promotion, or real-money evidence."
)
PIPELINE_EVIDENCE_BOUNDARY_METADATA: dict[str, object] = {
    "artifact_role": "paper-trade scan/recommend/log pipeline status sidecar",
    "valid_use": "operator workflow-state routing for scanner, recommender, and logger stages",
    "not_new_forward_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_settled_roi_evidence": True,
    "status_sidecar_is_workflow_metadata_only": True,
    "stronger_forward_confidence_requires": [
        "qualifying live paper signals",
        "ROI-complete settled paper rows",
        "settlement-quality checks",
    ],
    "non_goals": [
        "do not treat clean workflow completion as live profitability evidence",
        "do not treat cache-only misses, partial-cache runs, or max-races-limited scans as clean forward observations",
        "do not promote OP_REFINED_K7 or Phase 8 from pipeline status cleanliness",
        "do not reopen current odds-only XGBoost from pipeline status cleanliness",
        "do not substitute BAQ for BEL",
        "do not discuss real-money scaling from pipeline status cleanliness",
    ],
}
PIPELINE_VALID_SCOPE = "scan_recommend_log_status_only"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run the scanner -> scoring -> EV sizing -> ledger paper-trade pipeline"
    )
    p.add_argument("--skip-scan", action="store_true", help="Reuse an existing scanner JSON instead of invoking scan_live.sh")
    p.add_argument("--scan-input", default=str(DEFAULT_SCAN_INPUT), help="Scanner JSON input/output path")
    p.add_argument("--scanner-status-output", help="Optional scanner status JSON path; defaults to <scan-input>.status.json")
    p.add_argument("--recommendation-output-dir", default=str(DEFAULT_RECOMMENDATION_OUTPUT_DIR), help="Directory for recommendation artifacts")
    p.add_argument("--ledger", default=str(DEFAULT_LEDGER), help="Paper-trade signal ledger CSV path")
    p.add_argument("--state", default=str(DEFAULT_STATE), help="Paper-trade signal dedup state JSON path")
    p.add_argument("--recommendation-ledger", default=str(DEFAULT_RECOMMENDATION_LEDGER), help="Recommendation ledger CSV path")
    p.add_argument("--recommendation-state", default=str(DEFAULT_RECOMMENDATION_STATE), help="Recommendation dedup state JSON path")
    p.add_argument("--status-output", default=str(DEFAULT_STATUS_OUTPUT), help="Machine-readable pipeline status JSON path")

    p.add_argument("--rules", default=str(DEFAULT_RULES), help="Rules JSON passed to scan_live.sh / live_portfolio_scanner.py")
    p.add_argument("--cache-only", action="store_true", help="Pass through to scan_live.sh")
    p.add_argument("--cache-ttl", type=int, default=900, help="Pass through to scan_live.sh")
    p.add_argument("--max-races", type=int, default=12, help="Pass through to scan_live.sh")
    p.add_argument("--base-stake", type=float, default=1.0, help="Pass through to scan_live.sh")
    p.add_argument("--include-cards", nargs="*", help="Optional card-name filters passed to scan_live.sh")

    p.add_argument("--model", default=str(DEFAULT_MODEL), help="Model path for NYRA/model_main.py")
    p.add_argument("--top-combinations", type=int, default=200, help="Top Harville candidates to score per race")
    p.add_argument("--threads", type=int, default=1, help="Inference threads for NYRA/model_main.py")
    p.add_argument("--workers", type=int, default=1,
                   help="Concurrent race scorers for paper_trade_recommender.py (1 = serial, 0 = auto)")
    p.add_argument("--reuse-predictions", action="store_true", help="Reuse recommendation-output-dir/predictions/*.csv if present")
    p.add_argument("--allow-all-combos", action="store_true", help="Skip Phase 7 combo filtering before EV sizing")

    p.add_argument("--bankroll", type=float, default=500.0, help="Bankroll used for EV sizing")
    p.add_argument("--payout-unit", type=float, default=1.0, help="Dollar unit represented by predicted_payout")
    p.add_argument("--ticket-increment", type=float, default=0.10, help="Minimum ticket increment")
    p.add_argument("--payout-haircut", type=float, default=0.75, help="Conservative payout haircut")
    p.add_argument("--kelly-fraction", type=float, default=0.25, help="Fractional Kelly multiplier")
    p.add_argument("--min-ev-roi", type=float, default=0.15, help="Minimum EV ROI after haircut")
    p.add_argument("--min-prob", type=float, default=0.0005, help="Minimum joint probability")
    p.add_argument("--max-tickets", type=int, default=4, help="Maximum selected tickets per race")
    p.add_argument("--max-race-risk", type=float, default=0.02, help="Max bankroll fraction at risk in one race")
    p.add_argument("--max-ticket-risk", type=float, default=0.0075, help="Max bankroll fraction at risk on one ticket")
    return p.parse_args()


def _status(msg: str = "") -> None:
    print(msg, flush=True)


def _run(cmd: list[str]) -> None:
    printable = " ".join(shlex.quote(part) for part in cmd)
    _status(f"$ {printable}")
    subprocess.run(cmd, cwd=BASE, check=True)


def _read_json(path: Path):
    if not path.exists() or path.stat().st_size == 0:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_json_with_state(path: Path) -> tuple[str, object | None, str]:
    if not path.exists():
        return "missing", None, ""
    if path.stat().st_size == 0:
        return "empty", None, ""
    try:
        return "readable", json.loads(path.read_text(encoding="utf-8")), ""
    except json.JSONDecodeError as exc:
        return "unreadable", None, f"{exc.__class__.__name__}: {exc}"


def _read_scan_hits_with_state(path: Path) -> tuple[str, list[dict], str]:
    state, payload, error = _read_optional_json_with_state(path)
    if state != "readable":
        return state, [], error
    if not isinstance(payload, list):
        return "invalid_shape", [], f"expected scanner-output JSON list, got {type(payload).__name__}"
    return "readable", payload, ""


def _write_status(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_empty_scan_fallback(
    scan_input: Path,
    status_payload: dict[str, object],
    *,
    reason: str,
    prior_state: str,
) -> None:
    """Write a safe empty scan file while preserving why the fallback happened."""
    status_payload["scan_input_empty_fallback_applied"] = True
    status_payload["scan_input_empty_fallback_reason"] = reason
    status_payload["scan_input_state_before_empty_fallback"] = prior_state
    status_payload["scan_input_empty_fallback_value"] = "[]"
    scan_input.parent.mkdir(parents=True, exist_ok=True)
    scan_input.write_text("[]", encoding="utf-8")


def _clear_stale_recommendation_artifacts(
    recommendation_output_dir: Path,
    status_payload: dict[str, object],
    *,
    clear_prediction_artifacts: bool,
) -> None:
    """Remove stale actionable recommendation artifacts before a fresh recommender run."""
    summary_paths = [
        recommendation_output_dir / "recommendations_summary.json",
        recommendation_output_dir / "recommendations_summary.csv",
        recommendation_output_dir / "recommendations_summary.txt",
    ]
    plans_dir = recommendation_output_dir / "plans"
    plan_paths: list[Path] = []
    if plans_dir.exists():
        plan_paths = [
            path
            for path in sorted(plans_dir.iterdir())
            if path.is_file() and path.suffix in {".csv", ".json"}
        ]
    prediction_paths: list[Path] = []
    predictions_dir = recommendation_output_dir / "predictions"
    if clear_prediction_artifacts and predictions_dir.exists():
        prediction_paths = [
            path
            for path in sorted(predictions_dir.iterdir())
            if path.is_file() and path.suffix == ".csv"
        ]

    cleared: list[str] = []
    for path in [*summary_paths, *plan_paths, *prediction_paths]:
        if path.exists():
            path.unlink()
            cleared.append(str(path))

    status_payload["recommendation_stale_artifacts_cleared_before_recommender"] = True
    status_payload["recommendation_stale_artifact_count_cleared"] = len(cleared)
    status_payload["recommendation_stale_artifacts_cleared"] = cleared
    status_payload["recommendation_stale_prediction_artifacts_clear_enabled"] = clear_prediction_artifacts
    status_payload["recommendation_stale_artifact_guard"] = (
        "clears stale recommendation summaries, plan files, and non-reuse prediction files before "
        "recommender subprocess so failures cannot publish old actionable tickets or scored-race context"
    )


def _hydrate_scan_context(
    args: argparse.Namespace,
    scan_input: Path,
    scanner_status_output: Path,
    status_payload: dict[str, object],
) -> list[dict]:
    if not scan_input.exists() or scan_input.stat().st_size == 0:
        status_payload["scan_hit_count"] = 0
        status_payload.setdefault("scanner_result", "unknown")
        status_payload.setdefault("scanner_partial_cache", False)
        return []

    scan_state, scan_hits, scan_error = _read_scan_hits_with_state(scan_input)
    if scan_state == "unreadable":
        status_payload["scan_input_error"] = scan_error
    elif scan_state == "invalid_shape":
        status_payload["scan_input_shape_error"] = scan_error
    status_payload["scan_hit_count"] = len(scan_hits)

    scanner_status_state, scanner_status, scanner_status_error = _read_optional_json_with_state(scanner_status_output)
    status_payload["scanner_status_state"] = scanner_status_state
    if scanner_status_error:
        status_payload["scanner_status_error"] = scanner_status_error
    if isinstance(scanner_status, dict):
        status_payload["scanner_result"] = scanner_status.get("result", "unknown")
        status_payload["scanner_error_type"] = scanner_status.get("error_type", "")
        status_payload["scanner_error"] = scanner_status.get("error", "")
        status_payload["scanner_http_status"] = scanner_status.get("http_status")
        status_payload["scanner_api_failure_class"] = scanner_status.get("api_failure_class", "")
        status_payload["scanner_api_access_failure"] = bool(scanner_status.get("api_access_failure", False))
        status_payload["scanner_api_failure_valid_scope"] = scanner_status.get("api_failure_valid_scope", "")
        status_payload["scanner_api_failure_boundary"] = scanner_status.get("api_failure_boundary", "")
        status_payload["scanner_api_failure_operator_action"] = scanner_status.get("api_failure_operator_action", "")
        status_payload["scanner_api_failure_recheck_command"] = scanner_status.get("api_failure_recheck_command", "")
        status_payload["scanner_stale_cache_fallback_applied"] = bool(scanner_status.get("stale_cache_fallback_applied", False))
        status_payload["scanner_stale_cache_fallback_count"] = scanner_status.get("stale_cache_fallback_count", 0)
        status_payload["scanner_stale_cache_fallback_kind"] = scanner_status.get("stale_cache_fallback_kind", "")
        status_payload["scanner_stale_cache_fallback_error_type"] = scanner_status.get("stale_cache_fallback_error_type", "")
        status_payload["scanner_stale_cache_fallback_error"] = scanner_status.get("stale_cache_fallback_error", "")
        status_payload["scanner_partial_cache"] = bool(scanner_status.get("partial_cache", False))
        status_payload["scanner_raw_hit_count"] = scanner_status.get("raw_hit_count", len(scan_hits))
        status_payload["scanner_emitted_hit_count"] = scanner_status.get("emitted_hit_count", len(scan_hits))
        status_payload["scanner_missing_race_detail_cache_skips"] = scanner_status.get("missing_race_detail_cache_skips", 0)
        status_payload["scanner_race_count"] = scanner_status.get("race_count", 0)
        target_race_count = int(scanner_status.get("target_race_count", 0) or 0)
        race_details_attempted = int(scanner_status.get("race_details_attempted", 0) or 0)
        status_payload["scanner_target_race_count"] = target_race_count
        status_payload["scanner_target_card_count"] = scanner_status.get("target_card_count", 0)
        status_payload["scanner_race_details_attempted"] = race_details_attempted
        status_payload["scanner_race_details_loaded"] = scanner_status.get("race_details_loaded", 0)
        status_payload["scanner_max_race_limit_hit"] = bool(scanner_status.get("max_race_limit_hit", False))
        status_payload["scanner_full_target_coverage_min_races"] = int(scanner_status.get("full_target_coverage_min_races", target_race_count) or 0)
        status_payload["scanner_unattempted_target_race_count"] = int(
            scanner_status.get("unattempted_target_race_count", max(0, target_race_count - race_details_attempted)) or 0
        )
        status_payload["scanner_pre_detail_skipped_race_count"] = scanner_status.get("pre_detail_skipped_race_count", 0)
        status_payload["scanner_detail_fetch_scope"] = scanner_status.get("detail_fetch_scope", "")
    elif scanner_status_state == "readable":
        status_payload["scanner_result"] = "scanner_status_invalid_shape"
        status_payload["scanner_status_error"] = f"expected scanner-status JSON object, got {type(scanner_status).__name__}"
        status_payload["scanner_partial_cache"] = False
    elif scanner_status_state == "empty":
        status_payload["scanner_result"] = "scanner_status_empty"
        status_payload["scanner_partial_cache"] = False
    elif scanner_status_state == "unreadable":
        status_payload["scanner_result"] = "scanner_status_unreadable"
        status_payload["scanner_partial_cache"] = False
    elif status_payload.get("scanner_stage_status") == "scanner_failed":
        status_payload["scanner_result"] = "scanner_failed"
        status_payload["scanner_partial_cache"] = False
    elif args.skip_scan:
        status_payload["scanner_result"] = "reused_input_with_hits" if scan_hits else "reused_input_empty"
        status_payload["scanner_partial_cache"] = False
    else:
        status_payload.setdefault("scanner_result", "unknown")
        status_payload.setdefault("scanner_partial_cache", False)

    if status_payload.get("scanner_stage_status") in {"missing_scan_output", "invalid_scan_output"}:
        forced_result = str(status_payload.get("scanner_stage_status"))
        sidecar_result = status_payload.get("scanner_result")
        if (
            scanner_status_state == "readable"
            and sidecar_result
            and sidecar_result != forced_result
        ):
            status_payload["scanner_status_reported_result"] = sidecar_result
        status_payload["scanner_result"] = forced_result
        status_payload["scanner_partial_cache"] = False

    return scan_hits


def _hydrate_recommendation_context(
    recommendations_input: Path,
    status_payload: dict[str, object],
) -> list[dict]:
    recommendations = _read_json(recommendations_input)
    if not isinstance(recommendations, list):
        recommendations = []
    status_payload["recommendation_count"] = len(recommendations)
    status_payload["bet_count"] = sum(1 for rec in recommendations if rec.get("decision") == "BET")
    status_payload["no_bet_count"] = sum(1 for rec in recommendations if rec.get("decision") == "NO BET")
    status_payload["error_count"] = sum(1 for rec in recommendations if rec.get("decision") == "ERROR")
    return recommendations


def _is_cache_only_miss(status_payload: dict[str, object]) -> bool:
    scanner_result = str(status_payload.get("scanner_result", ""))
    cache_only = bool(status_payload.get("cache_only", False))
    error_text = str(status_payload.get("scanner_error", ""))
    return cache_only and scanner_result == "scanner_error" and "No cached data" in error_text


def _is_api_access_failure(status_payload: dict[str, object]) -> bool:
    if bool(status_payload.get("scanner_api_access_failure", False)):
        return True
    try:
        return int(status_payload.get("scanner_http_status") or 0) in {401, 403}
    except (TypeError, ValueError):
        return False


def _is_max_race_limited(status_payload: dict[str, object]) -> bool:
    return bool(status_payload.get("scanner_max_race_limit_hit", False))


def _observation_metadata(status_payload: dict[str, object]) -> tuple[str, str]:
    pipeline_result = str(status_payload.get("result", ""))
    stage = str(status_payload.get("stage", ""))
    observation_result = str(status_payload.get("observation_result", ""))
    scanner_result = str(status_payload.get("scanner_result", ""))

    if pipeline_result == "pipeline_error":
        if stage == "recommender":
            return "operational_failure", "recommender_failure"
        if stage == "logger":
            return "operational_failure", "logger_failure"
        return "operational_failure", "pipeline_error"
    if _is_cache_only_miss(status_payload):
        return "operational_limit", "cache_only_miss"
    if _is_api_access_failure(status_payload):
        return "operational_limit", "api_access_failure"
    if observation_result == "partial_cache_empty_run":
        return "operational_limit", "partial_cache_empty"
    if observation_result == "partial_cache_with_activity":
        return "operational_limit", "partial_cache_with_activity"
    if observation_result == "limited_coverage_empty_run":
        return "operational_limit", "max_race_limit_empty"
    if observation_result == "limited_coverage_with_activity":
        return "operational_limit", "max_race_limit_with_activity"
    if scanner_result == "scanner_status_empty":
        return "operational_limit", "scanner_status_empty"
    if scanner_result == "scanner_status_unreadable":
        return "operational_limit", "scanner_status_unreadable"
    if scanner_result == "scanner_status_invalid_shape":
        return "operational_limit", "scanner_status_invalid_shape"
    if scanner_result == "invalid_scan_output":
        return "operational_limit", "invalid_scan_output"
    if scanner_result == "missing_scan_output":
        return "operational_limit", "missing_scan_output"
    if observation_result == "scanner_failed_empty_run" or scanner_result in {"scanner_failed", "scanner_error"}:
        return "operational_limit", "scanner_failure"
    if observation_result == "clean_empty_run":
        if scanner_result == "no_matching_cards":
            return "clean_observation", "no_matching_cards"
        if scanner_result == "reused_input_empty":
            return "clean_observation", "reused_input_empty"
        return "clean_observation", "no_qualifiers"
    if observation_result == "signals_logged_no_bet":
        return "clean_observation", "signals_logged_no_bet"
    if observation_result == "bets_ready":
        return "bet_ready", "bets_ready"
    if observation_result == "completed_without_activity":
        return "clean_observation", "completed_without_activity"
    if observation_result:
        return "other", observation_result
    return "unknown", "unknown"


def _observation_result(status_payload: dict[str, object]) -> str:
    scanner_result = str(status_payload.get("scanner_result", "unknown"))
    scanner_stage_status = str(status_payload.get("scanner_stage_status", "unknown"))
    scan_hit_count = int(status_payload.get("scan_hit_count", 0) or 0)
    recommendation_count = int(status_payload.get("recommendation_count", 0) or 0)
    bet_count = int(status_payload.get("bet_count", 0) or 0)

    if scanner_stage_status in {"scanner_failed", "missing_scan_output", "invalid_scan_output"} or scanner_result == "scanner_failed":
        return "scanner_failed_empty_run"
    if _is_api_access_failure(status_payload):
        return "scanner_failed_empty_run"
    if scanner_result.startswith("partial_cache"):
        if scan_hit_count or recommendation_count:
            return "partial_cache_with_activity"
        return "partial_cache_empty_run"
    if _is_max_race_limited(status_payload):
        if scan_hit_count or recommendation_count:
            return "limited_coverage_with_activity"
        return "limited_coverage_empty_run"
    if scanner_result in {"scanner_status_empty", "scanner_status_unreadable", "scanner_status_invalid_shape"}:
        if scan_hit_count or recommendation_count:
            return "scanner_status_unavailable_with_activity"
        return "scanner_status_unavailable_empty_run"
    if scanner_result in {"no_qualifiers", "no_matching_cards", "reused_input_empty"}:
        return "clean_empty_run"
    if bet_count > 0:
        return "bets_ready"
    if recommendation_count > 0 or scan_hit_count > 0:
        return "signals_logged_no_bet"
    return "completed_without_activity"


def run_scanner(args: argparse.Namespace, scan_input: Path, scanner_status_output: Path) -> None:
    cmd = [
        str(BASE / "scan_live.sh"),
        "--cache-ttl",
        str(args.cache_ttl),
        "--max-races",
        str(args.max_races),
        "--base-stake",
        str(args.base_stake),
        "--rules",
        str(args.rules),
        "--save",
        str(scan_input),
        "--status-json",
        str(scanner_status_output),
    ]
    if args.cache_only:
        cmd.append("--cache-only")
    if args.include_cards:
        cmd.extend(["--include-cards", *args.include_cards])
    _run(cmd)


def run_recommender(args: argparse.Namespace, scan_input: Path, recommendation_output_dir: Path) -> Path:
    cmd = [
        sys.executable,
        str(BASE / "paper_trade_recommender.py"),
        "--scan-input",
        str(scan_input),
        "--output-dir",
        str(recommendation_output_dir),
        "--model",
        str(args.model),
        "--top-combinations",
        str(args.top_combinations),
        "--threads",
        str(args.threads),
        "--workers",
        str(args.workers),
        "--bankroll",
        str(args.bankroll),
        "--payout-unit",
        str(args.payout_unit),
        "--ticket-increment",
        str(args.ticket_increment),
        "--payout-haircut",
        str(args.payout_haircut),
        "--kelly-fraction",
        str(args.kelly_fraction),
        "--min-ev-roi",
        str(args.min_ev_roi),
        "--min-prob",
        str(args.min_prob),
        "--max-tickets",
        str(args.max_tickets),
        "--max-race-risk",
        str(args.max_race_risk),
        "--max-ticket-risk",
        str(args.max_ticket_risk),
    ]
    if args.reuse_predictions:
        cmd.append("--reuse-predictions")
    if args.allow_all_combos:
        cmd.append("--allow-all-combos")
    _run(cmd)
    return recommendation_output_dir / "recommendations_summary.json"


def run_logger(args: argparse.Namespace, scan_input: Path, recommendations_input: Path) -> None:
    cmd = [
        sys.executable,
        str(BASE / "paper_trade_logger.py"),
        "--input",
        str(scan_input),
        "--ledger",
        str(args.ledger),
        "--state",
        str(args.state),
        "--recommendations-input",
        str(recommendations_input),
        "--recommendation-ledger",
        str(args.recommendation_ledger),
        "--recommendation-state",
        str(args.recommendation_state),
    ]
    _run(cmd)


def main() -> int:
    args = parse_args()
    scan_input = Path(args.scan_input)
    recommendation_output_dir = Path(args.recommendation_output_dir)
    recommendations_input = recommendation_output_dir / "recommendations_summary.json"
    status_output = Path(args.status_output)
    scanner_status_output = (
        Path(args.scanner_status_output)
        if args.scanner_status_output
        else scan_input.with_suffix(".status.json")
    )

    status_payload: dict[str, object] = {
        "run_ts": datetime.now().isoformat(timespec="seconds"),
        "rules_path": str(Path(args.rules).resolve()),
        "scan_input": str(scan_input),
        "scanner_status_path": str(scanner_status_output),
        "recommendation_output_dir": str(recommendation_output_dir),
        "recommendations_input": str(recommendations_input),
        "status_output": str(status_output),
        "cache_only": bool(args.cache_only),
        "skip_scan": bool(args.skip_scan),
        "valid_evidence_scope": PIPELINE_VALID_SCOPE,
        "evidence_boundary": PIPELINE_EVIDENCE_BOUNDARY,
        "evidence_boundary_metadata": PIPELINE_EVIDENCE_BOUNDARY_METADATA,
        "scan_input_empty_fallback_applied": False,
        "scan_input_empty_fallback_reason": "",
        "scan_input_state_before_empty_fallback": "",
        "recommendation_stale_artifacts_cleared_before_recommender": False,
        "recommendation_stale_artifact_count_cleared": 0,
        "recommendation_stale_artifacts_cleared": [],
        "recommendation_stale_prediction_artifacts_clear_enabled": False,
        "recommendation_stale_artifact_guard": "",
        "last_completed_stage": None,
        "stage": "starting",
        "result": "running",
    }

    try:
        _status("Paper-trade pipeline")
        _status(f"Input: {scan_input}")
        _status(f"Rules: {args.rules}")
        _status("Scoring: NYRA/model_main.py --race-id <scanner race_id>")
        _status("EV filtering: paper_trade_recommender.py -> ev_ticket_engine.build_race_plan")
        _status(f"valid_evidence_scope={PIPELINE_VALID_SCOPE}")
        _status(f"Evidence boundary: {PIPELINE_EVIDENCE_BOUNDARY}")
        _status(f"Recommended tickets: {recommendation_output_dir / 'recommendations_summary.csv'}")
        _status()

        status_payload["stage"] = "scanner"
        if args.skip_scan:
            _status(f"Skipping scan step; reusing {scan_input}")
            status_payload["scanner_stage_status"] = "skipped_scan"
        else:
            try:
                run_scanner(args, scan_input, scanner_status_output)
                status_payload["scanner_stage_status"] = "completed"
            except subprocess.CalledProcessError as exc:
                _status(f"Scanner exited with code {exc.returncode}; writing empty hits to {scan_input}")
                status_payload["scanner_stage_status"] = "scanner_failed"
                status_payload["scanner_exit_code"] = exc.returncode
                _write_empty_scan_fallback(
                    scan_input,
                    status_payload,
                    reason="scanner_failed",
                    prior_state="scanner_failed_before_scan_file_replacement",
                )

        if not scan_input.exists() or scan_input.stat().st_size == 0:
            prior_state = "missing" if not scan_input.exists() else "empty"
            _status(f"No scanner output at {scan_input}; writing empty hits.")
            status_payload["scanner_stage_status"] = "missing_scan_output"
            _write_empty_scan_fallback(
                scan_input,
                status_payload,
                reason="missing_or_empty_scan_output",
                prior_state=prior_state,
            )
        else:
            scan_input_state, _, scan_input_error = _read_scan_hits_with_state(scan_input)
            if scan_input_state in {"unreadable", "invalid_shape"}:
                _status(f"Invalid scanner output at {scan_input}; writing empty hits.")
                status_payload["scanner_stage_status"] = "invalid_scan_output"
                if scan_input_state == "unreadable":
                    status_payload["scan_input_error"] = scan_input_error
                else:
                    status_payload["scan_input_shape_error"] = scan_input_error
                _write_empty_scan_fallback(
                    scan_input,
                    status_payload,
                    reason="invalid_scan_output",
                    prior_state=scan_input_state,
                )

        _hydrate_scan_context(args, scan_input, scanner_status_output, status_payload)
        status_payload["last_completed_stage"] = "scanner"

        status_payload["stage"] = "recommender"
        _clear_stale_recommendation_artifacts(
            recommendation_output_dir,
            status_payload,
            clear_prediction_artifacts=not args.reuse_predictions,
        )
        run_recommender(args, scan_input, recommendation_output_dir)
        _hydrate_recommendation_context(recommendations_input, status_payload)
        status_payload["last_completed_stage"] = "recommender"

        status_payload["stage"] = "logger"
        run_logger(args, scan_input, recommendations_input)
        _hydrate_recommendation_context(recommendations_input, status_payload)
        status_payload["last_completed_stage"] = "logger"
        status_payload["observation_result"] = _observation_result(status_payload)

        status_payload["stage"] = "done"
        status_payload["result"] = "ok"
        status_payload["observation_scope"], status_payload["observation_reason"] = _observation_metadata(status_payload)
        _write_status(status_output, status_payload)

        _status()
        _status("Artifacts")
        _status(f"- Scanner hits: {scan_input}")
        _status(f"- Scanner status: {scanner_status_output}")
        _status(f"- Pipeline status: {status_output}")
        _status(f"- Recommendation summary: {recommendations_input}")
        _status(f"- Recommendation tickets: {recommendation_output_dir / 'recommendations_summary.csv'}")
        _status(f"- Signal ledger: {args.ledger}")
        _status(f"- Recommendation ledger: {args.recommendation_ledger}")
        return 0
    except BaseException as exc:
        try:
            _hydrate_scan_context(args, scan_input, scanner_status_output, status_payload)
        except Exception:
            pass
        try:
            _hydrate_recommendation_context(recommendations_input, status_payload)
        except Exception:
            pass

        status_payload["stage"] = status_payload.get("stage", "error")
        status_payload["result"] = "pipeline_error"
        status_payload["error_type"] = exc.__class__.__name__
        status_payload["error"] = str(exc)

        if str(status_payload.get("stage") or "") == "logger" and isinstance(status_payload.get("recommendation_count"), int):
            status_payload["observation_result"] = _observation_result(status_payload)

        status_payload["observation_scope"], status_payload["observation_reason"] = _observation_metadata(status_payload)
        _write_status(status_output, status_payload)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
