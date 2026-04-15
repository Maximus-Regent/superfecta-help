#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
DEFAULT_SCANNER_STATUS = BASE / "out" / "live_scan_latest.status.json"
DEFAULT_PIPELINE_STATUS = BASE / "out" / "paper_trade_pipeline_status.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Summarize scanner/pipeline status sidecars into a report-safe one-line note"
    )
    p.add_argument("--scanner-status", default=str(DEFAULT_SCANNER_STATUS), help="Scanner status JSON path")
    p.add_argument("--pipeline-status", default=str(DEFAULT_PIPELINE_STATUS), help="Pipeline status JSON path")
    p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p.add_argument("--output", help="Optional file to save summary")
    return p.parse_args()


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def rules_label(path_str: str | None) -> str:
    name = Path(path_str or "").name
    mapping = {
        "op_anchor_rules.json": "OP anchor",
        "phase7_live_rules.json": "Phase 7 basket",
        "phase7_current_paper_rules.json": "Phase 7 current paper",
        "phase8_shadow_rules.json": "Phase 8 shadow",
    }
    return mapping.get(name, name.replace("_", " ").replace(".json", "") or "unknown rules")


def summarize(scanner: dict[str, Any] | None, pipeline: dict[str, Any] | None) -> dict[str, Any]:
    rules = rules_label((pipeline or scanner or {}).get("rules_path"))
    run_ts = (pipeline or scanner or {}).get("run_ts")
    scanner_result = (pipeline or {}).get("scanner_result") or (scanner or {}).get("result") or "missing"
    observation_result = (pipeline or {}).get("observation_result")

    scan_hit_count = int((pipeline or {}).get("scan_hit_count", (scanner or {}).get("emitted_hit_count", 0)) or 0)
    raw_hit_count = int((pipeline or {}).get("scanner_raw_hit_count", (scanner or {}).get("raw_hit_count", scan_hit_count)) or 0)
    recommendation_count = int((pipeline or {}).get("recommendation_count", 0) or 0)
    bet_count = int((pipeline or {}).get("bet_count", 0) or 0)
    error_count = int((pipeline or {}).get("error_count", 0) or 0)
    missing_race_details = int((pipeline or {}).get(
        "scanner_missing_race_detail_cache_skips",
        (scanner or {}).get("missing_race_detail_cache_skips", 0),
    ) or 0)
    race_details_attempted = int((scanner or {}).get("race_details_attempted", 0) or 0)
    max_race_limit_hit = bool((scanner or {}).get("max_race_limit_hit", 0))
    scanner_partial_cache = bool((pipeline or {}).get("scanner_partial_cache", (scanner or {}).get("partial_cache", False)))

    if observation_result == "scanner_failed_empty_run" or scanner_result == "scanner_error":
        headline = "scanner failure"
    elif observation_result == "partial_cache_empty_run" or scanner_result.startswith("partial_cache"):
        headline = "partial cache"
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
    if scanner_partial_cache or missing_race_details:
        details.append(f"{missing_race_details} missing race detail cache file(s)")
    if max_race_limit_hit and race_details_attempted:
        details.append(f"max-races cap hit after {race_details_attempted} attempt(s)")

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
        "scan_hit_count": scan_hit_count,
        "raw_hit_count": raw_hit_count,
        "recommendation_count": recommendation_count,
        "bet_count": bet_count,
        "error_count": error_count,
        "missing_race_detail_cache_skips": missing_race_details,
        "race_details_attempted": race_details_attempted,
        "max_race_limit_hit": max_race_limit_hit,
        "summary_line": line,
    }


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    scanner = read_json(Path(args.scanner_status))
    pipeline = read_json(Path(args.pipeline_status))

    if scanner is None and pipeline is None:
        raise SystemExit("No readable status JSON found. Pass --scanner-status and/or --pipeline-status.")

    payload = summarize(scanner, pipeline)
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
