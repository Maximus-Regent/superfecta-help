#!/usr/bin/env python3
"""
Build paper-trade recommendations from Phase 7 scanner hits.

Pipeline:
1. Read qualifying scanner hits from live_portfolio_scanner.py output
2. Score each hit's race via NYRA/model_main.py
3. Restrict the scored combos to the scanner's key-favorite ticket universe
4. Apply ev_ticket_engine bankroll sizing to that narrowed combo set
5. Save per-race plans plus a consolidated recommendation summary

This keeps the Phase 7 live scanner as the trusted gate, while using the
existing EV engine to turn a qualifying race into sized paper-trade tickets.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ev_ticket_engine import EngineConfig, add_ev_metrics, build_race_plan

BASE = Path(__file__).resolve().parent
DEFAULT_SCAN_INPUT = BASE / "out" / "live_scan_latest.json"
DEFAULT_OUTPUT_DIR = BASE / "out" / "paper_trade_recommendations_latest"
DEFAULT_MODEL = BASE / "Model" / "log_residual_model_normalized.json"


def display_path(path: Path) -> str:
    path = path.resolve()
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Turn Phase 7 scanner hits into EV-sized paper-trade recommendations"
    )
    p.add_argument("--scan-input", default=str(DEFAULT_SCAN_INPUT), help="Scanner JSON path")
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for recommendation artifacts")
    p.add_argument("--model", default=str(DEFAULT_MODEL), help="Model path for NYRA/model_main.py")
    p.add_argument("--top-combinations", type=int, default=200, help="Top Harville candidates to score per race")
    p.add_argument("--threads", type=int, default=1, help="Inference threads passed to model_main.py")
    p.add_argument("--workers", type=int, default=1,
                   help="Concurrent race scorers (1 = serial, 0 = auto based on CPU and --threads)")
    p.add_argument("--reuse-predictions", action="store_true", help="Reuse existing prediction CSVs in output-dir if present")
    p.add_argument("--allow-all-combos", action="store_true", help="Skip Phase 7 combo filtering and size across the full scored race")

    p.add_argument("--bankroll", type=float, default=500.0, help="Bankroll used for stake sizing")
    p.add_argument("--payout-unit", type=float, default=1.0, help="Dollar unit represented by predicted_payout")
    p.add_argument("--ticket-increment", type=float, default=0.10, help="Minimum ticket increment")
    p.add_argument("--payout-haircut", type=float, default=0.75, help="Conservative payout haircut")
    p.add_argument("--kelly-fraction", type=float, default=0.25, help="Fractional Kelly multiplier")
    p.add_argument("--min-ev-roi", type=float, default=0.15, help="Minimum EV ROI after haircut")
    p.add_argument("--min-prob", type=float, default=0.0005, help="Minimum joint probability")
    p.add_argument("--max-tickets", type=int, default=4, help="Maximum selected tickets per race")
    p.add_argument("--max-race-risk", type=float, default=0.02, help="Max bankroll fraction at risk in one race")
    p.add_argument("--max-ticket-risk", type=float, default=0.0075, help="Max bankroll fraction on one ticket")
    return p.parse_args()


def load_hits(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Scanner input not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    data = json.loads(text)
    if not isinstance(data, list):
        raise SystemExit(f"Scanner input must be a JSON list: {path}")
    return data


def signal_key(hit: dict[str, Any]) -> str:
    return (
        f"{hit.get('scan_ts','')}|{hit.get('rule_id','')}|"
        f"{hit.get('race_id','')}|{hit.get('favorite_program','')}"
    )


def combo_allowed(combo: str, hit: dict[str, Any]) -> bool:
    parts = [p.strip() for p in str(combo).split("-")]
    if len(parts) != 4:
        return False

    favorite_program = str(hit.get("favorite_program", "")).strip()
    underneath = {str(x).strip() for x in hit.get("underneath_programs", [])}
    if parts[0] != favorite_program:
        return False
    if len(set(parts)) != 4:
        return False
    return all(part in underneath for part in parts[1:])


def filter_predictions(df: pd.DataFrame, hit: dict[str, Any], allow_all_combos: bool) -> pd.DataFrame:
    enriched_df = df.copy()
    if "ev_profit_1" not in enriched_df.columns:
        enriched_df = add_ev_metrics(enriched_df)

    if allow_all_combos:
        return enriched_df
    if "combo" not in enriched_df.columns:
        raise KeyError("Prediction CSV is missing combo column")
    mask = enriched_df["combo"].map(lambda value: combo_allowed(str(value), hit))
    out = enriched_df[mask].copy()
    sort_cols = [col for col in ["ev_profit_1", "jointProb", "predicted_payout"] if col in out.columns]
    ascending = [False] * len(sort_cols)
    if sort_cols:
        out = out.sort_values(sort_cols, ascending=ascending).reset_index(drop=True)
    else:
        out = out.reset_index(drop=True)
    return out


def run_model_main(hit: dict[str, Any], output_csv: Path, args: argparse.Namespace) -> None:
    cmd = [
        sys.executable,
        str(BASE / "NYRA" / "model_main.py"),
        "--model",
        str(args.model),
        "--race-id",
        str(hit["race_id"]),
        "--top-combinations",
        str(args.top_combinations),
        "--sort-by",
        "ev",
        "--threads",
        str(args.threads),
        "--output",
        str(output_csv),
    ]
    subprocess.run(cmd, cwd=BASE, check=True)


def resolve_workers(requested_workers: int, threads_per_worker: int, job_count: int) -> int:
    if job_count <= 1:
        return 1
    if requested_workers > 0:
        return min(requested_workers, job_count)

    cpu_total = max(1, os.cpu_count() or 1)
    threads_per_worker = max(1, threads_per_worker)
    auto_workers = max(1, cpu_total // threads_per_worker)
    return min(4, auto_workers, job_count)


def ensure_prediction_files(
    hits: list[dict[str, Any]],
    predictions_dir: Path,
    args: argparse.Namespace,
) -> dict[str, dict[str, Any]]:
    race_hits: dict[str, dict[str, Any]] = {}
    for hit in hits:
        race_id = hit.get("race_id")
        if race_id in (None, ""):
            continue
        race_hits.setdefault(str(race_id), hit)

    if not race_hits:
        return {}

    workers = resolve_workers(args.workers, args.threads, len(race_hits))
    print(
        f"Scoring {len(race_hits)} unique race(s) with {workers} worker(s) "
        f"and {max(1, args.threads)} inference thread(s) each."
    )

    def score_one(race_id: str, hit: dict[str, Any]) -> tuple[str, Path]:
        prediction_csv = predictions_dir / f"race_{race_id}_predictions.csv"
        if not (args.reuse_predictions and prediction_csv.exists()):
            run_model_main(hit, prediction_csv, args)
        return race_id, prediction_csv

    results: dict[str, dict[str, Any]] = {}
    jobs = list(race_hits.items())

    if workers == 1:
        for race_id, hit in jobs:
            prediction_csv = predictions_dir / f"race_{race_id}_predictions.csv"
            try:
                _, prediction_csv = score_one(race_id, hit)
                results[race_id] = {"prediction_csv": str(prediction_csv), "error": None}
            except Exception as exc:
                results[race_id] = {"prediction_csv": str(prediction_csv), "error": str(exc)}
        return results

    with ThreadPoolExecutor(max_workers=workers) as ex:
        future_map = {
            ex.submit(score_one, race_id, hit): race_id
            for race_id, hit in jobs
        }
        for future in as_completed(future_map):
            race_id = future_map[future]
            prediction_csv = predictions_dir / f"race_{race_id}_predictions.csv"
            try:
                _, prediction_csv = future.result()
                results[race_id] = {"prediction_csv": str(prediction_csv), "error": None}
            except Exception as exc:
                results[race_id] = {"prediction_csv": str(prediction_csv), "error": str(exc)}
    return results


def build_engine_config(args: argparse.Namespace, race_label: str) -> EngineConfig:
    return EngineConfig(
        bankroll=args.bankroll,
        payout_unit=args.payout_unit,
        ticket_increment=args.ticket_increment,
        payout_haircut=args.payout_haircut,
        kelly_fraction=args.kelly_fraction,
        min_ev_roi=args.min_ev_roi,
        min_prob=args.min_prob,
        max_tickets=args.max_tickets,
        max_race_risk=args.max_race_risk,
        max_ticket_risk=args.max_ticket_risk,
        race_label=race_label,
    )


def normalize_for_json(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {k: normalize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_for_json(v) for v in value]
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def write_text_summary(summary_path: Path, recommendations: list[dict[str, Any]]) -> None:
    lines = [
        "Paper-trade recommendation summary",
        "",
        "Flow: scanner hit -> model_main scoring -> Phase 7 combo filter -> EV sizing",
        "",
        f"Races processed: {len(recommendations)}",
        f"BET decisions: {sum(1 for rec in recommendations if rec['decision'] == 'BET')}",
        f"NO BET decisions: {sum(1 for rec in recommendations if rec['decision'] != 'BET')}",
        "",
    ]
    for rec in recommendations:
        lines.append(f"{rec['race_label']} | {rec['decision']}")
        lines.append(f"  Rule: {rec['rule_id']} | Signal: {rec['signal_key']}")
        lines.append(
            f"  Filtered combos: {rec['filtered_combo_count']} / {rec['scored_combo_count']} | "
            f"Stake: ${rec['total_stake']:.2f} | Exp profit: ${rec['total_expected_profit']:.2f}"
        )
        lines.append(f"  Reason: {rec['reason']}")
        if rec["decision"] == "BET":
            for idx, ticket in enumerate(rec["tickets"], 1):
                lines.append(
                    f"  {idx}. {ticket['combo']} | stake ${ticket['recommended_stake']:.2f} | "
                    f"EV ROI {ticket['ev_roi_pct']:.2f}%"
                )
        lines.append("")
    summary_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    scan_input = Path(args.scan_input).resolve()
    output_dir = Path(args.output_dir).resolve()
    predictions_dir = output_dir / "predictions"
    plans_dir = output_dir / "plans"
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_dir.mkdir(parents=True, exist_ok=True)
    plans_dir.mkdir(parents=True, exist_ok=True)

    hits = load_hits(scan_input)
    run_ts = datetime.now().isoformat(timespec="seconds")
    recommendations: list[dict[str, Any]] = []
    prediction_results = ensure_prediction_files(hits, predictions_dir, args)

    for hit in hits:
        race_id = hit.get("race_id")
        if race_id in (None, ""):
            continue

        race_label = f"{hit.get('card_name', 'Unknown')} Race {hit.get('race_number', '?')} (raceId={race_id})"
        prediction_csv = predictions_dir / f"race_{race_id}_predictions.csv"

        try:
            prediction_info = prediction_results.get(str(race_id))
            if prediction_info and prediction_info.get("prediction_csv"):
                prediction_csv = Path(prediction_info["prediction_csv"])
            if prediction_info and prediction_info.get("error"):
                raise RuntimeError(prediction_info["error"])

            scored_df = pd.read_csv(prediction_csv)
            filtered_df = filter_predictions(scored_df, hit, allow_all_combos=args.allow_all_combos)
            plan = build_race_plan(filtered_df, build_engine_config(args, race_label))

            plan_json_path = plans_dir / f"race_{race_id}_plan.json"
            plan_csv_path = plans_dir / f"race_{race_id}_plan.csv"
            plan_json_path.write_text(json.dumps(asdict(plan), indent=2), encoding="utf-8")
            if plan.tickets:
                pd.DataFrame(plan.tickets).to_csv(plan_csv_path, index=False)
            elif plan_csv_path.exists():
                plan_csv_path.unlink()

            recommendations.append(normalize_for_json({
                "run_ts": run_ts,
                "signal_key": signal_key(hit),
                "rule_id": hit.get("rule_id", ""),
                "track": hit.get("track", ""),
                "card_name": hit.get("card_name", ""),
                "race_number": hit.get("race_number", ""),
                "race_id": race_id,
                "race_label": race_label,
                "decision": plan.decision,
                "reason": plan.reason,
                "favorite_program": hit.get("favorite_program", ""),
                "underneath_programs": hit.get("underneath_programs", []),
                "scanner_estimated_cost": hit.get("estimated_cost", ""),
                "scored_combo_count": len(scored_df),
                "filtered_combo_count": len(filtered_df),
                "prediction_csv": display_path(prediction_csv),
                "plan_json": display_path(plan_json_path),
                "plan_csv": display_path(plan_csv_path) if plan_csv_path.exists() else "",
                "bankroll": plan.bankroll,
                "race_risk_budget": plan.race_risk_budget,
                "total_stake": plan.total_stake,
                "total_expected_return": plan.total_expected_return,
                "total_expected_profit": plan.total_expected_profit,
                "portfolio_expected_roi_pct": plan.portfolio_expected_roi_pct,
                "tickets_selected": plan.tickets_selected,
                "tickets": plan.tickets,
                "source_hit": hit,
            }))
        except Exception as exc:
            recommendations.append({
                "run_ts": run_ts,
                "signal_key": signal_key(hit),
                "rule_id": hit.get("rule_id", ""),
                "track": hit.get("track", ""),
                "card_name": hit.get("card_name", ""),
                "race_number": hit.get("race_number", ""),
                "race_id": race_id,
                "race_label": race_label,
                "decision": "ERROR",
                "reason": str(exc),
                "favorite_program": hit.get("favorite_program", ""),
                "underneath_programs": hit.get("underneath_programs", []),
                "scanner_estimated_cost": hit.get("estimated_cost", ""),
                "scored_combo_count": 0,
                "filtered_combo_count": 0,
                "prediction_csv": display_path(prediction_csv),
                "plan_json": "",
                "plan_csv": "",
                "bankroll": args.bankroll,
                "race_risk_budget": round(args.bankroll * args.max_race_risk, 2),
                "total_stake": 0.0,
                "total_expected_return": 0.0,
                "total_expected_profit": 0.0,
                "portfolio_expected_roi_pct": 0.0,
                "tickets_selected": 0,
                "tickets": [],
                "source_hit": normalize_for_json(hit),
            })

    summary_json = output_dir / "recommendations_summary.json"
    summary_csv = output_dir / "recommendations_summary.csv"
    summary_txt = output_dir / "recommendations_summary.txt"

    summary_json.write_text(json.dumps(recommendations, indent=2), encoding="utf-8")

    flat_rows: list[dict[str, Any]] = []
    for rec in recommendations:
        if rec["tickets"]:
            for ticket in rec["tickets"]:
                flat_rows.append({
                    "run_ts": rec["run_ts"],
                    "signal_key": rec["signal_key"],
                    "rule_id": rec["rule_id"],
                    "track": rec["track"],
                    "card_name": rec["card_name"],
                    "race_number": rec["race_number"],
                    "race_id": rec["race_id"],
                    "decision": rec["decision"],
                    "reason": rec["reason"],
                    "favorite_program": rec["favorite_program"],
                    "prediction_csv": rec["prediction_csv"],
                    "plan_json": rec["plan_json"],
                    **ticket,
                })
        else:
            flat_rows.append({
                "run_ts": rec["run_ts"],
                "signal_key": rec["signal_key"],
                "rule_id": rec["rule_id"],
                "track": rec["track"],
                "card_name": rec["card_name"],
                "race_number": rec["race_number"],
                "race_id": rec["race_id"],
                "decision": rec["decision"],
                "reason": rec["reason"],
                "favorite_program": rec["favorite_program"],
                "prediction_csv": rec["prediction_csv"],
                "plan_json": rec["plan_json"],
            })

    pd.DataFrame(flat_rows).to_csv(summary_csv, index=False)
    write_text_summary(summary_txt, recommendations)

    bet_count = sum(1 for rec in recommendations if rec["decision"] == "BET")
    print(
        f"Processed {len(recommendations)} scanner hit(s); "
        f"{bet_count} BET / {len(recommendations) - bet_count} non-BET. "
        f"Summary: {summary_json}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
