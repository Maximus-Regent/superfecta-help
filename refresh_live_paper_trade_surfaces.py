#!/usr/bin/env python3
"""
Refresh saved live paper-trade surfaces from the current source-layer generators.

Purpose:
- rebuild persisted operator-facing artifacts after source-layer paper-trade helpers change
- keep saved daily run folders, OPS_HISTORY, PAPER_TRADE_NOW, and CURRENT_EVIDENCE_SUMMARY in sync with the current renderers
- preserve the current bridge route published at current_evidence_summary.json.rebuild_validation_contract: settlement audit -> current bridge -> bridge validator
- reduce the stale-surface failure mode where validation is right but the saved live read is still old
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import paper_trade_preflight_note as preflight_source
from paper_trade_status_summary import resolve_declared_scanner_status_path

BASE = Path(__file__).resolve().parent
DEFAULT_RUNS_ROOT = BASE / "out" / "daily_portfolio_runs"
DEFAULT_OPS_LIMIT = 14
CURRENT_EVIDENCE_REBUILD_CONTRACT_SOURCE = "current_evidence_summary.json.rebuild_validation_contract"
CURRENT_EVIDENCE_REBUILD_COMMANDS = (
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
)


@dataclass(frozen=True)
class LaneConfig:
    name: str
    rules: Path
    signals_ledger: Path
    recommendation_ledger: Path
    settlement_ledger: Path


LANES: tuple[LaneConfig, ...] = (
    LaneConfig(
        name="phase7_current_paper",
        rules=BASE / "phase7_current_paper_rules.json",
        signals_ledger=BASE / "paper_trades" / "phase7_current_paper_paper_trade_signals.csv",
        recommendation_ledger=BASE / "paper_trades" / "phase7_current_paper_paper_trade_recommendations.csv",
        settlement_ledger=BASE / "paper_trades" / "phase7_current_paper_paper_trade_settlements.csv",
    ),
    LaneConfig(
        name="phase8_shadow",
        rules=BASE / "phase8_shadow_rules.json",
        signals_ledger=BASE / "paper_trades" / "phase8_shadow_paper_trade_signals.csv",
        recommendation_ledger=BASE / "paper_trades" / "phase8_shadow_paper_trade_recommendations.csv",
        settlement_ledger=BASE / "paper_trades" / "phase8_shadow_paper_trade_settlements.csv",
    ),
)


class RefreshError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Refresh saved live paper-trade surfaces from current source-layer helpers")
    p.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT), help="Directory containing YYYY-MM-DD daily run folders")
    p.add_argument("--run-root", action="append", default=[], help="Specific run root(s) to refresh; repeatable")
    p.add_argument("--latest-only", action="store_true", help="Refresh only the latest run folder under --runs-root")
    p.add_argument("--sync-settlements", action="store_true", help="Also rerun settlement-ledger template sync before rebuilding surfaces")
    p.add_argument("--ops-limit", type=int, default=DEFAULT_OPS_LIMIT, help="Rolling day limit for OPS_HISTORY and PAPER_TRADE_NOW context")
    p.add_argument("--as-of-date", help="Optional YYYY-MM-DD date to treat as 'today' when rebuilding PAPER_TRADE_NOW freshness for reproducible rerenders")
    p.add_argument("--skip-top-level", action="store_true", help="Skip OPS_HISTORY and PAPER_TRADE_NOW refresh")
    p.add_argument("--ops-history-md-output", default=str(BASE / "OPS_HISTORY.md"), help="Markdown output path for the refreshed rolling ops history")
    p.add_argument("--ops-history-csv-output", default=str(BASE / "ops_history.csv"), help="CSV output path for the refreshed rolling ops history")
    p.add_argument("--paper-trade-now-text-output", default=str(BASE / "PAPER_TRADE_NOW.txt"), help="Text output path for the refreshed top-level right-now surface")
    p.add_argument("--paper-trade-now-md-output", default=str(BASE / "PAPER_TRADE_NOW.md"), help="Markdown output path for the refreshed top-level right-now surface")
    p.add_argument("--paper-trade-now-json-output", default=str(BASE / "PAPER_TRADE_NOW.json"), help="JSON output path for the refreshed top-level right-now payload")
    p.add_argument("--settlement-audit-md-output", default=str(BASE / "out" / "paper_trade_settlement_audit.md"), help="Markdown output path for the refreshed settlement audit surface")
    p.add_argument("--settlement-audit-json-output", default=str(BASE / "out" / "paper_trade_settlement_audit.json"), help="JSON output path for the refreshed settlement audit surface")
    p.add_argument("--current-evidence-md-output", default=str(BASE / "CURRENT_EVIDENCE_SUMMARY.md"), help="Markdown output path for the refreshed current-evidence bridge")
    p.add_argument(
        "--current-evidence-json-output",
        default=str(BASE / "current_evidence_summary.json"),
        help=(
            "JSON output path for the refreshed current-evidence bridge; the generated sidecar "
            f"publishes {CURRENT_EVIDENCE_REBUILD_CONTRACT_SOURCE}"
        ),
    )
    p.add_argument("--keep-going", action="store_true", help="Continue other run folders after one refresh failure, then fail at the end")
    return p.parse_args()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BASE.resolve()))
    except Exception:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RefreshError(f"could not read JSON from {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RefreshError(f"expected JSON object at {path}")
    return data


def read_json_optional(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def resolve_lane_scanner_status_path(lane_dir: Path) -> Path:
    default_path = lane_dir / "live_scan.status.json"
    pipeline_status = lane_dir / "pipeline_status.json"
    pipeline_payload = read_json_optional(pipeline_status)
    pipeline_declared = str((pipeline_payload or {}).get("scanner_status_path") or "").strip()
    if pipeline_declared:
        # Rebuild saved-live surfaces from the scanner sidecar the pipeline recorded.
        # If that declared artifact is missing, surface the missing declared path
        # rather than borrowing a stale default filename from the lane directory.
        return resolve_declared_scanner_status_path(pipeline_declared, pipeline_status)
    if default_path.exists() and default_path.is_file():
        return default_path
    return default_path


def run_cmd(parts: Sequence[str], label: str) -> None:
    proc = subprocess.run(
        list(parts),
        cwd=BASE,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
        raise RefreshError(f"{label} failed: {detail}")


def discover_run_roots(args: argparse.Namespace) -> list[Path]:
    if args.run_root:
        run_roots = [Path(raw).expanduser().resolve() for raw in args.run_root]
    else:
        runs_root = Path(args.runs_root).expanduser().resolve()
        if not runs_root.exists() or not runs_root.is_dir():
            raise RefreshError(f"runs root not found: {runs_root}")
        run_roots = sorted(path for path in runs_root.iterdir() if path.is_dir())
        if args.latest_only and run_roots:
            run_roots = [run_roots[-1]]
    if not run_roots:
        raise RefreshError("no run folders selected for refresh")
    return run_roots


def refresh_preflight(run_root: Path) -> list[str]:
    json_path = run_root / "preflight_note.json"
    text_path = run_root / "preflight_note.txt"
    if not json_path.exists():
        raise RefreshError(f"preflight note JSON not found: {json_path}")

    saved_payload = read_json(json_path)
    seed_payload = {
        "date": saved_payload.get("date"),
        "checked_at": saved_payload.get("checked_at"),
        "api_ok": saved_payload.get("api_ok"),
        "has_targets": saved_payload.get("has_targets"),
        "relevant_tracks": saved_payload.get("relevant_tracks"),
        "shadow_tracks": saved_payload.get("shadow_tracks"),
        "excluded_tracks": saved_payload.get("excluded_tracks"),
        "total_cards": saved_payload.get("total_cards"),
        "error": saved_payload.get("error"),
    }

    original_checker = preflight_source.check_todays_cards_extended
    try:
        preflight_source.check_todays_cards_extended = lambda payload=seed_payload: payload
        rebuilt_payload = preflight_source.build_payload()
    finally:
        preflight_source.check_todays_cards_extended = original_checker

    text_path.write_text(str(rebuilt_payload["note"]) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(rebuilt_payload, indent=2) + "\n", encoding="utf-8")
    return [rel(text_path), rel(json_path)]


def refresh_lane(py: str, run_root: Path, lane: LaneConfig, sync_settlements: bool) -> list[str]:
    lane_dir = run_root / lane.name
    scanner_status = resolve_lane_scanner_status_path(lane_dir)
    pipeline_status = lane_dir / "pipeline_status.json"
    preflight_note = run_root / "preflight_note.txt"
    summary_path = lane_dir / "summary.txt"
    forward_check_txt = lane_dir / "forward_check.txt"
    forward_check_md = lane_dir / "forward_check.md"
    lane_monitor_txt = lane_dir / "lane_monitor.txt"
    lane_monitor_md = lane_dir / "lane_monitor.md"
    next_steps_txt = lane_dir / "next_steps.txt"
    next_steps_md = lane_dir / "next_steps.md"
    base_summary_tmp = lane_dir / ".summary.base.refresh.tmp"
    outputs: list[str] = []

    if sync_settlements:
        run_cmd(
            [
                py,
                "paper_trade_settlement_sync.py",
                "--signals-ledger",
                str(lane.signals_ledger),
                "--settlement-ledger",
                str(lane.settlement_ledger),
            ],
            f"{lane.name} settlement sync",
        )

    run_cmd(
        [
            py,
            "paper_trade_status_summary.py",
            "--scanner-status",
            str(scanner_status),
            "--pipeline-status",
            str(pipeline_status),
            "--require-pipeline-status",
            "--output",
            str(base_summary_tmp),
        ],
        f"{lane.name} base summary",
    )

    run_cmd(
        [
            py,
            "paper_trade_forward_check.py",
            "--signals-ledger",
            str(lane.signals_ledger),
            "--recommendation-ledger",
            str(lane.recommendation_ledger),
            "--settlement-ledger",
            str(lane.settlement_ledger),
            "--rules",
            str(lane.rules),
            "--format",
            "text",
            "--output",
            str(forward_check_txt),
        ],
        f"{lane.name} forward_check.txt",
    )
    outputs.append(rel(forward_check_txt))

    run_cmd(
        [
            py,
            "paper_trade_forward_check.py",
            "--signals-ledger",
            str(lane.signals_ledger),
            "--recommendation-ledger",
            str(lane.recommendation_ledger),
            "--settlement-ledger",
            str(lane.settlement_ledger),
            "--rules",
            str(lane.rules),
            "--format",
            "md",
            "--output",
            str(forward_check_md),
        ],
        f"{lane.name} forward_check.md",
    )
    outputs.append(rel(forward_check_md))

    run_cmd(
        [
            py,
            "paper_trade_lane_monitor.py",
            "--signals-ledger",
            str(lane.signals_ledger),
            "--recommendation-ledger",
            str(lane.recommendation_ledger),
            "--settlement-ledger",
            str(lane.settlement_ledger),
            "--rules",
            str(lane.rules),
            "--format",
            "text",
            "--output",
            str(lane_monitor_txt),
        ],
        f"{lane.name} lane_monitor.txt",
    )
    outputs.append(rel(lane_monitor_txt))

    run_cmd(
        [
            py,
            "paper_trade_lane_monitor.py",
            "--signals-ledger",
            str(lane.signals_ledger),
            "--recommendation-ledger",
            str(lane.recommendation_ledger),
            "--settlement-ledger",
            str(lane.settlement_ledger),
            "--rules",
            str(lane.rules),
            "--format",
            "md",
            "--output",
            str(lane_monitor_md),
        ],
        f"{lane.name} lane_monitor.md",
    )
    outputs.append(rel(lane_monitor_md))

    run_cmd(
        [
            py,
            "paper_trade_next_steps.py",
            "--signals-ledger",
            str(lane.signals_ledger),
            "--recommendation-ledger",
            str(lane.recommendation_ledger),
            "--settlement-ledger",
            str(lane.settlement_ledger),
            "--rules",
            str(lane.rules),
            "--runner",
            str(BASE / "run_daily_portfolio_observation.sh"),
            "--scanner-status",
            str(scanner_status),
            "--pipeline-status",
            str(pipeline_status),
            "--preflight-note",
            str(preflight_note),
            "--format",
            "text",
            "--output",
            str(next_steps_txt),
        ],
        f"{lane.name} next_steps.txt",
    )
    outputs.append(rel(next_steps_txt))

    run_cmd(
        [
            py,
            "paper_trade_next_steps.py",
            "--signals-ledger",
            str(lane.signals_ledger),
            "--recommendation-ledger",
            str(lane.recommendation_ledger),
            "--settlement-ledger",
            str(lane.settlement_ledger),
            "--rules",
            str(lane.rules),
            "--runner",
            str(BASE / "run_daily_portfolio_observation.sh"),
            "--scanner-status",
            str(scanner_status),
            "--pipeline-status",
            str(pipeline_status),
            "--preflight-note",
            str(preflight_note),
            "--format",
            "md",
            "--output",
            str(next_steps_md),
        ],
        f"{lane.name} next_steps.md",
    )
    outputs.append(rel(next_steps_md))

    try:
        run_cmd(
            [
                py,
                "paper_trade_lane_summary.py",
                "--base-summary",
                str(base_summary_tmp),
                "--next-steps-text",
                str(next_steps_txt),
                "--next-steps-md",
                str(next_steps_md),
                "--lane-monitor-text",
                str(lane_monitor_txt),
                "--lane-monitor-md",
                str(lane_monitor_md),
                "--forward-check-text",
                str(forward_check_txt),
                "--forward-check-md",
                str(forward_check_md),
                "--settlement-ledger",
                str(lane.settlement_ledger),
                "--display-summary",
                str(summary_path),
                "--output",
                str(summary_path),
            ],
            f"{lane.name} summary.txt",
        )
        outputs.append(rel(summary_path))
    finally:
        base_summary_tmp.unlink(missing_ok=True)

    return outputs


def refresh_run_root(
    py: str,
    run_root: Path,
    sync_settlements: bool,
) -> list[str]:
    if not run_root.exists() or not run_root.is_dir():
        raise RefreshError(f"run root not found: {run_root}")

    outputs: list[str] = []
    outputs.extend(refresh_preflight(run_root))
    for lane in LANES:
        outputs.extend(refresh_lane(py, run_root, lane, sync_settlements=sync_settlements))
    return outputs



def refresh_settlement_audit(
    py: str,
    settlement_audit_md: Path,
    settlement_audit_json: Path,
) -> list[str]:
    run_cmd(
        [
            py,
            "paper_trade_settlement_audit.py",
            "--format",
            "text",
            "--output-md",
            str(settlement_audit_md),
            "--output-json",
            str(settlement_audit_json),
        ],
        "settlement audit refresh",
    )
    return [rel(settlement_audit_md), rel(settlement_audit_json)]


def refresh_daily_summary(
    py: str,
    run_root: Path,
    right_now_md: Path,
    ops_history_md: Path,
    settlement_audit_md: Path,
) -> str:
    daily_summary = run_root / "daily_summary.txt"
    run_cmd(
        [
            py,
            "paper_trade_daily_summary.py",
            "--run-root",
            str(run_root),
            "--right-now",
            str(right_now_md),
            "--ops-history",
            str(ops_history_md),
            "--settlement-audit",
            str(settlement_audit_md),
            "--output",
            str(daily_summary),
        ],
        f"{run_root.name} daily_summary.txt",
    )
    return rel(daily_summary)


def refresh_top_level(
    py: str,
    runs_root: Path,
    ops_limit: int,
    ops_history_md: Path,
    ops_history_csv: Path,
    paper_trade_now_txt: Path,
    paper_trade_now_md: Path,
    paper_trade_now_json: Path,
    settlement_audit_md: Path,
    as_of_date: str | None,
) -> list[str]:
    outputs: list[str] = []

    run_cmd(
        [
            py,
            "paper_trade_ops_history.py",
            "--runs-root",
            str(runs_root),
            "--limit",
            str(ops_limit),
            "--md-output",
            str(ops_history_md),
            "--csv-output",
            str(ops_history_csv),
        ],
        "OPS_HISTORY refresh",
    )
    outputs.extend([rel(ops_history_md), rel(ops_history_csv)])

    text_cmd = [
        py,
        "paper_trade_now.py",
        "--runs-root",
        str(runs_root),
        "--ops-limit",
        str(ops_limit),
        "--ops-history-md",
        str(ops_history_md),
        "--settlement-audit",
        str(settlement_audit_md),
        "--format",
        "text",
        "--output",
        str(paper_trade_now_txt),
    ]
    if as_of_date:
        text_cmd.extend(["--as-of-date", as_of_date])
    run_cmd(
        text_cmd,
        "PAPER_TRADE_NOW.txt refresh",
    )
    outputs.append(rel(paper_trade_now_txt))

    json_cmd = [
        py,
        "paper_trade_now.py",
        "--runs-root",
        str(runs_root),
        "--ops-limit",
        str(ops_limit),
        "--ops-history-md",
        str(ops_history_md),
        "--settlement-audit",
        str(settlement_audit_md),
        "--format",
        "json",
        "--output",
        str(paper_trade_now_json),
    ]
    if as_of_date:
        json_cmd.extend(["--as-of-date", as_of_date])
    run_cmd(
        json_cmd,
        "PAPER_TRADE_NOW.json refresh",
    )
    outputs.append(rel(paper_trade_now_json))

    md_cmd = [
        py,
        "paper_trade_now.py",
        "--runs-root",
        str(runs_root),
        "--ops-limit",
        str(ops_limit),
        "--ops-history-md",
        str(ops_history_md),
        "--settlement-audit",
        str(settlement_audit_md),
        "--format",
        "md",
        "--output",
        str(paper_trade_now_md),
    ]
    if as_of_date:
        md_cmd.extend(["--as-of-date", as_of_date])
    run_cmd(
        md_cmd,
        "PAPER_TRADE_NOW.md refresh",
    )
    outputs.append(rel(paper_trade_now_md))
    return outputs


def refresh_current_evidence(
    py: str,
    right_now_json: Path,
    settlement_audit_json: Path,
    current_evidence_md: Path,
    current_evidence_json: Path,
) -> list[str]:
    run_cmd(
        [
            py,
            "current_evidence_summary.py",
            "--right-now-json",
            str(right_now_json),
            "--settlement-audit-json",
            str(settlement_audit_json),
            "--md-output",
            str(current_evidence_md),
            "--json-output",
            str(current_evidence_json),
        ],
        "CURRENT_EVIDENCE_SUMMARY refresh",
    )
    return [rel(current_evidence_md), rel(current_evidence_json)]


def main() -> int:
    args = parse_args()
    py = sys.executable or "python3"
    runs_root = Path(args.runs_root).expanduser().resolve()
    run_roots = discover_run_roots(args)
    ops_history_md = Path(args.ops_history_md_output).expanduser().resolve()
    ops_history_csv = Path(args.ops_history_csv_output).expanduser().resolve()
    paper_trade_now_txt = Path(args.paper_trade_now_text_output).expanduser().resolve()
    paper_trade_now_md = Path(args.paper_trade_now_md_output).expanduser().resolve()
    paper_trade_now_json = Path(args.paper_trade_now_json_output).expanduser().resolve()
    settlement_audit_md = Path(args.settlement_audit_md_output).expanduser().resolve()
    settlement_audit_json = Path(args.settlement_audit_json_output).expanduser().resolve()
    current_evidence_md = Path(args.current_evidence_md_output).expanduser().resolve()
    current_evidence_json = Path(args.current_evidence_json_output).expanduser().resolve()

    refreshed_outputs: list[str] = []
    failures: list[str] = []

    for run_root in run_roots:
        try:
            refreshed_outputs.extend(
                refresh_run_root(
                    py,
                    run_root,
                    sync_settlements=args.sync_settlements,
                )
            )
        except RefreshError as exc:
            if not args.keep_going:
                raise SystemExit(str(exc))
            failures.append(str(exc))

    if not args.skip_top_level:
        try:
            refreshed_outputs.extend(
                refresh_settlement_audit(
                    py,
                    settlement_audit_md=settlement_audit_md,
                    settlement_audit_json=settlement_audit_json,
                )
            )
            refreshed_outputs.extend(
                refresh_top_level(
                    py,
                    runs_root,
                    ops_limit=args.ops_limit,
                    ops_history_md=ops_history_md,
                    ops_history_csv=ops_history_csv,
                    paper_trade_now_txt=paper_trade_now_txt,
                    paper_trade_now_md=paper_trade_now_md,
                    paper_trade_now_json=paper_trade_now_json,
                    settlement_audit_md=settlement_audit_md,
                    as_of_date=args.as_of_date,
                )
            )
            refreshed_outputs.extend(
                refresh_current_evidence(
                    py,
                    right_now_json=paper_trade_now_json,
                    settlement_audit_json=settlement_audit_json,
                    current_evidence_md=current_evidence_md,
                    current_evidence_json=current_evidence_json,
                )
            )
        except RefreshError as exc:
            if not args.keep_going:
                raise SystemExit(str(exc))
            failures.append(str(exc))

    for run_root in run_roots:
        try:
            refreshed_outputs.append(
                refresh_daily_summary(
                    py,
                    run_root,
                    right_now_md=paper_trade_now_md,
                    ops_history_md=ops_history_md,
                    settlement_audit_md=settlement_audit_md,
                )
            )
        except RefreshError as exc:
            if not args.keep_going:
                raise SystemExit(str(exc))
            failures.append(str(exc))

    scope_note = "per-run preflight, lane, and daily-summary surfaces only; top-level outputs skipped" if args.skip_top_level else "including top-level settlement audit / OPS_HISTORY / PAPER_TRADE_NOW / CURRENT_EVIDENCE_SUMMARY outputs"
    print(f"Refreshed {len(refreshed_outputs)} saved surface(s) across {len(run_roots)} run folder(s) ({scope_note}).")
    print("Note: this helper re-renders saved operator surfaces and the settlement-audit guardrail from existing artifacts; it does not create new paper-trade outcomes or new forward evidence.")
    if args.as_of_date:
        if args.skip_top_level:
            print(f"Note: --as-of-date {args.as_of_date} was ignored because top-level PAPER_TRADE_NOW refresh was skipped.")
        else:
            print(f"Note: rebuilt PAPER_TRADE_NOW freshness was pinned to as-of date {args.as_of_date}.")
    if not args.skip_top_level:
        print(
            "Current-evidence rebuild route: "
            f"{CURRENT_EVIDENCE_REBUILD_CONTRACT_SOURCE}: "
            f"{' -> '.join(CURRENT_EVIDENCE_REBUILD_COMMANDS)}; "
            "provenance/rebuild metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence."
        )
    for path in refreshed_outputs:
        print(f"- {path}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
