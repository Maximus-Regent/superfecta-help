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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run the scanner -> scoring -> EV sizing -> ledger paper-trade pipeline"
    )
    p.add_argument("--skip-scan", action="store_true", help="Reuse an existing scanner JSON instead of invoking scan_live.sh")
    p.add_argument("--scan-input", default=str(DEFAULT_SCAN_INPUT), help="Scanner JSON input/output path")
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


def _write_status(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _observation_result(status_payload: dict[str, object]) -> str:
    scanner_result = str(status_payload.get("scanner_result", "unknown"))
    scanner_stage_status = str(status_payload.get("scanner_stage_status", "unknown"))
    scan_hit_count = int(status_payload.get("scan_hit_count", 0) or 0)
    recommendation_count = int(status_payload.get("recommendation_count", 0) or 0)
    bet_count = int(status_payload.get("bet_count", 0) or 0)

    if scanner_stage_status in {"scanner_failed", "missing_scan_output"} or scanner_result == "scanner_failed":
        return "scanner_failed_empty_run"
    if scanner_result.startswith("partial_cache"):
        if scan_hit_count or recommendation_count:
            return "partial_cache_with_activity"
        return "partial_cache_empty_run"
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
    scanner_status_output = scan_input.with_suffix(".status.json")

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
        "stage": "starting",
        "result": "running",
    }

    try:
        _status("Paper-trade pipeline")
        _status(f"Input: {scan_input}")
        _status(f"Rules: {args.rules}")
        _status("Scoring: NYRA/model_main.py --race-id <scanner race_id>")
        _status("EV filtering: paper_trade_recommender.py -> ev_ticket_engine.build_race_plan")
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
                scan_input.parent.mkdir(parents=True, exist_ok=True)
                scan_input.write_text("[]", encoding="utf-8")

        if not scan_input.exists() or scan_input.stat().st_size == 0:
            _status(f"No scanner output at {scan_input}; writing empty hits.")
            status_payload["scanner_stage_status"] = "missing_scan_output"
            scan_input.parent.mkdir(parents=True, exist_ok=True)
            scan_input.write_text("[]", encoding="utf-8")

        scan_hits = _read_json(scan_input)
        if not isinstance(scan_hits, list):
            scan_hits = []
        status_payload["scan_hit_count"] = len(scan_hits)

        scanner_status = _read_json(scanner_status_output)
        if isinstance(scanner_status, dict):
            status_payload["scanner_result"] = scanner_status.get("result", "unknown")
            status_payload["scanner_partial_cache"] = bool(scanner_status.get("partial_cache", False))
            status_payload["scanner_raw_hit_count"] = scanner_status.get("raw_hit_count", len(scan_hits))
            status_payload["scanner_emitted_hit_count"] = scanner_status.get("emitted_hit_count", len(scan_hits))
            status_payload["scanner_missing_race_detail_cache_skips"] = scanner_status.get("missing_race_detail_cache_skips", 0)
        elif status_payload.get("scanner_stage_status") == "scanner_failed":
            status_payload["scanner_result"] = "scanner_failed"
            status_payload["scanner_partial_cache"] = False
        elif args.skip_scan:
            status_payload["scanner_result"] = "reused_input_with_hits" if scan_hits else "reused_input_empty"
            status_payload["scanner_partial_cache"] = False
        else:
            status_payload["scanner_result"] = "unknown"
            status_payload["scanner_partial_cache"] = False

        status_payload["stage"] = "recommender"
        run_recommender(args, scan_input, recommendation_output_dir)

        status_payload["stage"] = "logger"
        run_logger(args, scan_input, recommendations_input)

        recommendations = _read_json(recommendations_input)
        if not isinstance(recommendations, list):
            recommendations = []
        status_payload["recommendation_count"] = len(recommendations)
        status_payload["bet_count"] = sum(1 for rec in recommendations if rec.get("decision") == "BET")
        status_payload["no_bet_count"] = sum(1 for rec in recommendations if rec.get("decision") == "NO BET")
        status_payload["error_count"] = sum(1 for rec in recommendations if rec.get("decision") == "ERROR")
        status_payload["observation_result"] = _observation_result(status_payload)

        status_payload["stage"] = "done"
        status_payload["result"] = "ok"
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
        status_payload["stage"] = status_payload.get("stage", "error")
        status_payload["result"] = "pipeline_error"
        status_payload["error_type"] = exc.__class__.__name__
        status_payload["error"] = str(exc)
        _write_status(status_output, status_payload)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
