#!/usr/bin/env python3
"""
Print the single best operator action for the paper-trade stack right now.

Purpose:
- collapse the current daily run, lane next-step logic, and rolling ops context into one read
- give Cole one honest answer before opening several artifacts
- keep the recommendation tied to the frozen-standard paper-trade helpers
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from paper_trade_forward_check import DEFAULT_FROZEN_EVAL
from paper_trade_lane_monitor import gate_source_text
from paper_trade_next_steps import build_payload as build_next_steps_payload
from paper_trade_ops_history import collect_rows, current_streak
from paper_trade_status_summary import resolve_declared_scanner_status_path as resolve_pipeline_declared_scanner_status_path

BASE = Path(__file__).resolve().parent
DEFAULT_RUNS_ROOT = BASE / "out" / "daily_portfolio_runs"
DEFAULT_MD = BASE / "PAPER_TRADE_NOW.md"
DEFAULT_RUNNER = BASE / "run_daily_portfolio_observation.sh"
DEFAULT_PAPER_TRADES_DIR = BASE / "paper_trades"
DEFAULT_PRIMARY_RULES = BASE / "phase7_current_paper_rules.json"
DEFAULT_SHADOW_RULES = BASE / "phase8_shadow_rules.json"
DEFAULT_OPS_HISTORY_MD = BASE / "OPS_HISTORY.md"
DEFAULT_SETTLEMENT_AUDIT = BASE / "out" / "paper_trade_settlement_audit.md"

LANES = {
    "primary": {
        "label": "Primary lane",
        "name": "phase7_current_paper",
    },
    "shadow": {
        "label": "Shadow lane",
        "name": "phase8_shadow",
    },
}
RIGHT_NOW_VALID_EVIDENCE_SCOPE = "operator_action_routing_only"
RIGHT_NOW_EVIDENCE_BOUNDARY = {
    "artifact_role": "paper-trade right-now operator action-priority top card",
    "valid_evidence_scope": RIGHT_NOW_VALID_EVIDENCE_SCOPE,
    "not_new_forward_evidence": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_anchor_displacement_evidence": True,
    "not_real_money_evidence": True,
    "decision_gate_advancement_requires_roi_complete_settlements": True,
    "boundary_text": "PAPER_TRADE_NOW is a single-action operator top card driven by current run artifacts and frozen hierarchy metadata; it is not new forward evidence, settled ROI evidence, live profitability evidence, promotion readiness evidence, anchor-displacement evidence, or real-money evidence.",
}
RIGHT_NOW_ACTION_CONTRACT_TEXT = (
    "Single best-action routing only: read `best_action` with `run_freshness` / `stale_snapshot_note` "
    "before treating lane context as current; the card routes settlement, refresh, stand-down, or forward-check "
    "next steps but does not advance decision gates by itself."
)
RIGHT_NOW_ACTION_PRIORITY_CONTRACT = {
    "contract": "single_best_operator_action",
    "primary_action_field": "best_action",
    "freshness_field": "run_freshness",
    "stale_context_field": "stale_snapshot_note",
    "boundary_field": "evidence_boundary",
    "source_fields": [
        "preflight_note",
        "primary",
        "shadow",
        "ops",
        "settlement_audit",
        "active_decision_gates",
        "live_hierarchy",
        "operator_read_gate",
    ],
    "action_contract_text": RIGHT_NOW_ACTION_CONTRACT_TEXT,
}

OPERATOR_READ_GATE_ISSUE_FLAGS = (
    "has_api_access_failure_context",
    "has_scanner_failure_boundary",
    "has_stale_cache_fallback_context",
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Print the single best operator action for the latest paper-trade run")
    p.add_argument("--run-root", help="Specific YYYY-MM-DD run root to summarize. Defaults to the latest run folder.")
    p.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT), help="Directory containing YYYY-MM-DD run folders")
    p.add_argument("--ops-limit", type=int, default=14, help="Number of recent run days to read for streak context")
    p.add_argument("--min-settled", type=int, default=None, help="Decision-grade settled race threshold; defaults to the scorecard anchor-displacement gate")
    p.add_argument("--portfolio-review-settled", type=int, default=None, help="Broader settled-race milestone for portfolio review readiness; defaults to the scorecard real-money discussion gate")
    p.add_argument("--max-open", type=int, default=5, help="Maximum open settlement rows to inspect per lane")
    p.add_argument("--runner", default=str(DEFAULT_RUNNER), help="Runner command to recommend when more observation is needed")
    p.add_argument("--paper-trades-dir", default=str(DEFAULT_PAPER_TRADES_DIR), help="Ledger root to read instead of the default paper_trades directory")
    p.add_argument("--primary-rules", default=str(DEFAULT_PRIMARY_RULES), help="Rules JSON for the primary lane")
    p.add_argument("--shadow-rules", default=str(DEFAULT_SHADOW_RULES), help="Rules JSON for the shadow lane")
    p.add_argument("--frozen-eval", default=str(DEFAULT_FROZEN_EVAL), help="Frozen evaluation summary CSV path")
    p.add_argument("--ops-history-md", default=str(DEFAULT_OPS_HISTORY_MD), help="Ops-history markdown path to reference in quick reads")
    p.add_argument("--settlement-audit", default=str(DEFAULT_SETTLEMENT_AUDIT), help="Settlement-audit markdown path whose adjacent JSON carries shadow promotion gates")
    p.add_argument("--as-of-date", help="Optional YYYY-MM-DD date to treat as 'today' when deciding whether the latest run is stale")
    p.add_argument("--format", choices=["text", "md", "json"], default="md", help="Output format")
    p.add_argument("--output", default=str(DEFAULT_MD), help="Optional output path")
    return p.parse_args()


def latest_run_root(runs_root: Path) -> Path | None:
    if not runs_root.exists():
        return None
    candidates = sorted(p for p in runs_root.iterdir() if p.is_dir())
    return candidates[-1] if candidates else None


def parse_iso_date(raw: str | None) -> date | None:
    text = str(raw or "").strip()
    if not text:
        return None
    candidate = text[:10]
    if len(candidate) != 10:
        return None
    try:
        return date.fromisoformat(candidate)
    except ValueError:
        return None


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BASE.resolve()))
    except Exception:
        return str(path)


def read_text(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return text or None


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def settlement_audit_json_path(markdown_path: Path) -> Path:
    return markdown_path.with_suffix(".json")


def read_settlement_audit_lane(markdown_path: Path, lane_name: str) -> tuple[Path, dict[str, Any] | None, str]:
    json_path = settlement_audit_json_path(markdown_path)
    payload = read_json(json_path)
    if payload is None:
        return json_path, None, f"[missing settlement-audit JSON: {rel(json_path)}]"
    lanes = payload.get("lanes")
    if not isinstance(lanes, list):
        return json_path, None, f"[missing settlement-audit lanes list: {rel(json_path)}]"
    for lane in lanes:
        if isinstance(lane, dict) and lane.get("name") == lane_name:
            return json_path, lane, ""
    return json_path, None, ""


def extract_settlement_audit_promotion_gate(markdown_path: Path, lane_name: str) -> tuple[str, str]:
    json_path, lane, error = read_settlement_audit_lane(markdown_path, lane_name)
    if error:
        return error, ""
    if lane is None:
        return f"[missing {lane_name} settlement-audit lane: {rel(json_path)}]", ""
    gate = lane.get("promotion_gate")
    if not isinstance(gate, dict):
        return "", ""
    gate_read = str(gate.get("gate_read") or "").strip()
    rule_rows = gate.get("rule_progress")
    progress_bits: list[str] = []
    if isinstance(rule_rows, list):
        for row in rule_rows:
            if not isinstance(row, dict):
                continue
            rule_id = str(row.get("rule_id") or "").strip()
            if not rule_id:
                continue
            promotion_progress = str(row.get("promotion_progress") or "").strip()
            scorecard_tier = str(row.get("scorecard_tier") or "").strip()
            tier_suffix = f" ({scorecard_tier})" if scorecard_tier else ""
            if promotion_progress:
                progress_bits.append(f"{rule_id}{tier_suffix} {promotion_progress}")
            else:
                progress_bits.append(f"{rule_id}{tier_suffix} {row.get('roi_complete_settled_rows', 0)} ROI-complete")
    return gate_read, "; ".join(progress_bits)


def normalize_track_list(raw_tracks: object) -> list[str]:
    if not isinstance(raw_tracks, list):
        return []
    tracks: list[str] = []
    for raw in raw_tracks:
        track = str(raw or "").strip().upper()
        if track and track not in tracks:
            tracks.append(track)
    return tracks


def format_excluded_track_aliases(tracks: list[str]) -> str:
    labels = []
    for track in tracks:
        if track == "BAQ":
            labels.append("BAQ (not treated as BEL)")
        else:
            labels.append(f"{track} (excluded from active/shadow aliases)")
    return ", ".join(labels)


def resolve_preflight_excluded_tracks(run_root: Path) -> list[str]:
    payload = read_json(run_root / "preflight_note.json")
    if payload is None:
        return []
    return normalize_track_list(payload.get("excluded_tracks"))


def resolve_preflight_note_surface(run_root: Path) -> tuple[Path, str]:
    text_path = run_root / "preflight_note.txt"
    json_path = run_root / "preflight_note.json"

    text = read_text(text_path)
    if text:
        return text_path, text

    payload = read_json(json_path)
    if payload is not None:
        note = str(payload.get("note") or "").strip()
        if note:
            return json_path, note
        return json_path, f"[missing preflight note field: {rel(json_path)}]"

    if json_path.exists() and json_path.is_file():
        return json_path, f"[unreadable preflight note JSON: {rel(json_path)}]"
    if text_path.exists() and text_path.is_file():
        return text_path, f"[missing preflight note text: {rel(text_path)} is empty]"
    return text_path, f"[missing preflight note artifact: {rel(text_path)} and {rel(json_path)}]"


def resolve_lane_scanner_status_path(lane_dir: Path) -> Path:
    default_path = lane_dir / "live_scan.status.json"
    pipeline_status = lane_dir / "pipeline_status.json"
    pipeline_payload = read_json(pipeline_status)
    pipeline_declared = str((pipeline_payload or {}).get("scanner_status_path") or "").strip()
    if pipeline_declared:
        # Keep the pipeline's scanner_status_path as the machine-readable pointer
        # even if the declared sidecar is absent from a copied surface; otherwise a
        # stale default live_scan.status.json can masquerade as the lane's scanner read.
        return resolve_pipeline_declared_scanner_status_path(pipeline_declared, pipeline_status)
    if default_path.exists() and default_path.is_file():
        return default_path
    return default_path


def build_lane_payload(run_root: Path, lane_key: str, args: argparse.Namespace) -> dict[str, Any]:
    lane = LANES[lane_key]
    lane_name = lane["name"]
    lane_dir = run_root / lane_name
    paper_trades_dir = Path(args.paper_trades_dir).expanduser()
    rules_path = Path(args.primary_rules if lane_key == "primary" else args.shadow_rules).expanduser()
    scanner_status_path = resolve_lane_scanner_status_path(lane_dir)
    ns = SimpleNamespace(
        signals_ledger=str(paper_trades_dir / f"{lane_name}_paper_trade_signals.csv"),
        recommendation_ledger=str(paper_trades_dir / f"{lane_name}_paper_trade_recommendations.csv"),
        settlement_ledger=str(paper_trades_dir / f"{lane_name}_paper_trade_settlements.csv"),
        rules=str(rules_path),
        frozen_eval=str(Path(args.frozen_eval).expanduser()),
        min_settled=getattr(args, "min_settled", None),
        portfolio_review_settled=getattr(args, "portfolio_review_settled", None),
        max_open=args.max_open,
        runner=str(args.runner),
        scanner_status=str(scanner_status_path),
        pipeline_status=str(lane_dir / "pipeline_status.json"),
        preflight_note=str(run_root / "preflight_note.txt"),
        format="json",
        output=None,
    )
    payload = build_next_steps_payload(ns)
    payload["lane_key"] = lane_key
    payload["lane_name"] = lane_name
    payload["lane_dir"] = rel(lane_dir)
    payload["next_steps_md"] = rel(lane_dir / "next_steps.md")
    payload["lane_monitor_md"] = rel(lane_dir / "lane_monitor.md")
    payload["forward_check_md"] = rel(lane_dir / "forward_check.md")
    payload["summary_txt"] = rel(lane_dir / "summary.txt")
    payload["pipeline_status_json"] = rel(lane_dir / "pipeline_status.json")
    payload["scanner_status_json"] = rel(scanner_status_path)
    return payload


def build_ops_context(run_root: Path, runs_root: Path, limit: int) -> dict[str, Any]:
    rows = collect_rows(runs_root, limit)
    latest = rows[0] if rows else None
    matched = next((row for row in rows if row["date"] == run_root.name), None)
    return {
        "latest_row": latest,
        "current_row": matched,
        "rows": rows,
        "streaks": {
            "no_target": current_streak(rows, lambda row: row["day_bucket"] == "NO TARGETS"),
            "active_zero_hit": current_streak(rows, lambda row: row["day_bucket"] == "ACTIVE, ZERO HITS"),
            "active_limited_coverage": current_streak(rows, lambda row: row["day_bucket"] == "ACTIVE, LIMITED COVERAGE"),
            "active_limited_coverage_with_activity": current_streak(rows, lambda row: row["day_bucket"] == "ACTIVE, LIMITED COVERAGE WITH ACTIVITY"),
            "active_hit_found": current_streak(rows, lambda row: row["day_bucket"] == "ACTIVE, HITS FOUND"),
            "issue": current_streak(rows, lambda row: row["day_bucket"] == "ISSUE"),
        },
    }


def build_run_freshness(run_root: Path, as_of_date_raw: str | None) -> dict[str, Any]:
    run_date = parse_iso_date(run_root.name)
    as_of_date = parse_iso_date(as_of_date_raw) or date.today()
    if run_date is None:
        return {
            "run_date": run_root.name,
            "as_of_date": as_of_date.isoformat(),
            "age_days": None,
            "is_stale": True,
            "freshness_state": "unknown_run_date",
            "summary": f"Latest run folder `{run_root.name}` is not an ISO date, so the saved top card is stale until the daily wrapper is rerun or a dated run folder is selected.",
        }

    age_days = (as_of_date - run_date).days
    if age_days < 0:
        summary = f"Latest run date `{run_date.isoformat()}` is ahead of the as-of date `{as_of_date.isoformat()}`, so treat the saved top card cautiously until the calendar reference is corrected."
        is_stale = True
        freshness_state = "future_run_date"
    elif age_days == 0:
        summary = f"Latest run date matches the as-of date (`{as_of_date.isoformat()}`), so this top card is current for today."
        is_stale = False
        freshness_state = "current_run_date"
    else:
        summary = f"Latest run date `{run_date.isoformat()}` is {age_days} day(s) behind the as-of date `{as_of_date.isoformat()}`, so the saved top card is stale until the daily wrapper is rerun."
        is_stale = True
        freshness_state = "stale_past_run"

    return {
        "run_date": run_date.isoformat(),
        "as_of_date": as_of_date.isoformat(),
        "age_days": age_days,
        "is_stale": is_stale,
        "freshness_state": freshness_state,
        "summary": summary,
    }


def choose_lane_monitor_command(lane_payload: dict[str, Any]) -> str:
    return next(
        (cmd for cmd in lane_payload.get("commands", []) if "paper_trade_lane_monitor.py" in cmd),
        lane_payload["commands"][0],
    )


def choose_runner_command(lane_payload: dict[str, Any]) -> str:
    return next(
        (cmd for cmd in lane_payload.get("commands", []) if "run_daily_portfolio_observation.sh" in cmd),
        f"./{DEFAULT_RUNNER.name}",
    )


def roi_gap_count(lane_payload: dict[str, Any]) -> int:
    return int(lane_payload.get("roi_gap_settlements", lane_payload.get("roi_missing_settled", 0)) or 0)


def roi_gap_reason(lane_payload: dict[str, Any]) -> str:
    return str(lane_payload.get("roi_gap_reason_summary") or "missing return/cost/timestamp coverage").strip()


def roi_context_text(lane_payload: dict[str, Any]) -> str:
    covered = lane_payload["roi_covered_settled"]
    settled = lane_payload["settled"]
    missing = int(lane_payload.get("roi_missing_settled", 0) or 0)
    gap_count = roi_gap_count(lane_payload)
    base = f"{covered}/{settled} ({missing} missing)"
    if gap_count:
        return f"{base}; ROI gaps={gap_count}: {roi_gap_reason(lane_payload)}"
    return base


def roi_context_md(lane_payload: dict[str, Any]) -> str:
    covered = lane_payload["roi_covered_settled"]
    settled = lane_payload["settled"]
    missing = int(lane_payload.get("roi_missing_settled", 0) or 0)
    gap_count = roi_gap_count(lane_payload)
    base = f"`{covered}/{settled}` (`{missing}` missing)"
    if gap_count:
        return f"{base}; ROI gaps=`{gap_count}`: {roi_gap_reason(lane_payload)}"
    return base


def right_now_gate_alignment_read(gate_minimums: dict[str, Any]) -> str:
    if not gate_minimums.get("cli_overrides") and gate_minimums.get("source_loaded") and not gate_minimums.get("fallback_used"):
        return "right-now action gates are source-matched to forward_evidence_scorecard.json decision_gate_minimums"
    return "right-now action gates are using explicit CLI/fallback values; do not treat fixture/custom thresholds as posture-changing gates"


def active_decision_gates(primary: dict[str, Any], shadow: dict[str, Any]) -> dict[str, Any]:
    gate_minimums = primary.get("decision_gate_minimums") if isinstance(primary, dict) else {}
    if not isinstance(gate_minimums, dict):
        gate_minimums = {}
    primary_min_settled = int(primary.get("min_settled", 0) or 0)
    shadow_min_settled = int(shadow.get("min_settled", 0) or 0)
    primary_portfolio_review_settled = int(primary.get("portfolio_review_settled", 0) or 0)
    shadow_portfolio_review_settled = int(shadow.get("portfolio_review_settled", 0) or 0)
    return {
        "source_path": gate_minimums.get("source_path"),
        "source_loaded": bool(gate_minimums.get("source_loaded")),
        "fallback_used": bool(gate_minimums.get("fallback_used")),
        "min_settled": primary_min_settled,
        "portfolio_review_settled": primary_portfolio_review_settled,
        "primary_min_settled": primary_min_settled,
        "shadow_min_settled": shadow_min_settled,
        "primary_portfolio_review_settled": primary_portfolio_review_settled,
        "shadow_portfolio_review_settled": shadow_portfolio_review_settled,
        "first_read_gate_parity": primary_min_settled == shadow_min_settled,
        "portfolio_review_gate_parity": primary_portfolio_review_settled == shadow_portfolio_review_settled,
        "primary_shadow_gate_parity": (
            primary_min_settled == shadow_min_settled
            and primary_portfolio_review_settled == shadow_portfolio_review_settled
            and primary.get("decision_gate_minimums") == shadow.get("decision_gate_minimums")
        ),
        "alignment_read": right_now_gate_alignment_read(gate_minimums),
    }


def active_gate_line(active_gates: dict[str, Any], *, markdown: bool = False) -> str:
    primary_min = active_gates.get("primary_min_settled", active_gates.get("min_settled"))
    shadow_min = active_gates.get("shadow_min_settled", active_gates.get("min_settled"))
    portfolio = active_gates.get("portfolio_review_settled")
    if markdown:
        return (
            f"primary_min_settled=`{primary_min}`; shadow_min_settled=`{shadow_min}`; "
            f"portfolio_review_settled=`{portfolio}`. {active_gates['alignment_read']}."
        )
    return (
        f"primary_min_settled={primary_min}; shadow_min_settled={shadow_min}; "
        f"portfolio_review_settled={portfolio}. {active_gates['alignment_read']}."
    )


def operator_issue_flags_line(read_gate: dict[str, Any], *, markdown: bool = False) -> str:
    parts = []
    for flag in OPERATOR_READ_GATE_ISSUE_FLAGS:
        value = "true" if read_gate.get(flag) is True else "false"
        parts.append(f"{flag}=`{value}`" if markdown else f"{flag}={value}")
    return "; ".join(parts)


def operator_read_gate(primary: dict[str, Any], shadow: dict[str, Any], ops: dict[str, Any], freshness: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    row = ops.get("current_row") or ops.get("latest_row") or {}
    day_bucket = str(row.get("day_bucket") or "").strip()
    action_headline = str(action.get("headline") or "")
    action_command = str(action.get("command") or "")
    lane_text = " ".join(
        str(value or "")
        for value in (
            primary.get("state"),
            primary.get("recent_run_context"),
            primary.get("why"),
            shadow.get("state"),
            shadow.get("recent_run_context"),
            shadow.get("why"),
        )
    )
    api_access_context = "API-access" in lane_text or "403 Client Error" in lane_text
    stale_cache_fallback_context = "stale-cache fallback" in lane_text or "stale cache fallback" in lane_text
    scanner_failure_boundary = (
        api_access_context
        or "CHECK SCANNER FAILURE" in lane_text
        or "scanner failed before producing signals" in lane_text
        or "scanner failure" in lane_text
    )

    reasons: list[str] = []
    if freshness.get("is_stale"):
        reasons.append("run freshness requires wrapper refresh")
    if api_access_context:
        reasons.append("scanner/API-access failure context is present")
    elif scanner_failure_boundary:
        reasons.append("scanner failure context is present")
    if "REFRESH RUN ARTIFACTS" in lane_text:
        reasons.append("run artifacts need refresh")
    if "CHECK PIPELINE FAILURE" in lane_text:
        reasons.append("pipeline failure context is present")
    if "cache-only" in lane_text or "No cached data" in lane_text:
        reasons.append("cache-only miss context is present")
    if "partial cache" in lane_text or day_bucket.startswith("ACTIVE, LIMITED COVERAGE"):
        reasons.append("partial-cache coverage context is present")
    if day_bucket == "UNKNOWN CALENDAR":
        reasons.append("calendar state is unknown")
    if day_bucket == "ISSUE":
        reasons.append("ops bucket is ISSUE")

    wrapper_refresh_action = (
        "run_daily_portfolio_observation.sh" in action_command
        and (action_headline.startswith("Refresh") or action_headline.startswith("Rerun"))
    )
    if wrapper_refresh_action:
        reasons.append("best action points to wrapper refresh")

    requires_refresh = bool(
        freshness.get("is_stale")
        or wrapper_refresh_action
        or day_bucket in {"ISSUE", "UNKNOWN CALENDAR"}
        or scanner_failure_boundary
        or "CHECK PIPELINE FAILURE" in lane_text
        or "REFRESH RUN ARTIFACTS" in lane_text
        or "partial cache" in lane_text
    )
    settlement_repair = action_headline.startswith(("Settle", "Complete", "Repair"))
    if not reasons:
        reasons.append("single-action operator routing only")

    if requires_refresh:
        gate_status = "refresh_required_before_evidence_read"
        recommended_command = "./run_daily_portfolio_observation.sh"
        read = (
            "Refresh/recheck with `./run_daily_portfolio_observation.sh` before using the saved top card "
            "as today's instruction or evidence; reasons: "
            + "; ".join(dict.fromkeys(reasons))
            + ". This is not a no-target, clean-empty, bet-readiness, settled-ROI, promotion, "
            "live-profitability, bankroll, or real-money read."
        )
    elif settlement_repair:
        gate_status = "settlement_or_roi_repair_before_forward_read"
        recommended_command = action_command
        read = (
            "Complete the routed settlement or ROI repair before reading this lane as forward evidence. "
            "This is workflow routing only, not settled-ROI, promotion, live-profitability, bankroll, or real-money evidence."
        )
    else:
        gate_status = "operator_action_routing_only"
        recommended_command = action_command
        read = (
            "Use this as a single-action operator routing card only; performance movement still requires "
            "ROI-complete settlements and the dedicated forward-check/settlement-audit reads."
        )

    return {
        "valid_use": "operator instruction/evidence-read gating only",
        "gate_status": gate_status,
        "requires_refresh_before_evidence_read": requires_refresh,
        "requires_settlement_or_roi_repair_before_forward_read": settlement_repair,
        "has_api_access_failure_context": api_access_context,
        "has_scanner_failure_boundary": scanner_failure_boundary,
        "has_stale_cache_fallback_context": stale_cache_fallback_context,
        "recommended_command": recommended_command,
        "reasons": list(dict.fromkeys(reasons)),
        "read": read,
        "current_top_card_counts_as_no_target_evidence": False,
        "current_top_card_counts_as_clean_empty_evidence": False,
        "current_top_card_counts_as_bet_readiness_evidence": False,
        "current_top_card_counts_as_settled_roi_evidence": False,
        "not_forward_performance_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_live_profitability_evidence": True,
        "not_bankroll_guidance": True,
        "not_real_money_evidence": True,
    }


def choose_best_action(primary: dict[str, Any], shadow: dict[str, Any], ops: dict[str, Any], freshness: dict[str, Any]) -> dict[str, Any]:
    row = ops.get("current_row") or ops.get("latest_row")
    streaks = ops.get("streaks") or {}

    if freshness.get("is_stale"):
        age_days = freshness.get("age_days")
        age_text = f"{age_days} day(s) old" if isinstance(age_days, int) and age_days >= 0 else "out of sync with the as-of date"
        return {
            "headline": "Refresh the daily wrapper, latest operator card is stale",
            "lane_key": primary["lane_key"],
            "lane": primary["lane_label"],
            "command": choose_runner_command(primary),
            "why": f"The latest saved operator card is {age_text} (`{freshness.get('run_date')}` vs `{freshness.get('as_of_date')}`), so rerun the daily wrapper before treating this settlement/readiness state as current today.",
            "timing": "now",
        }

    if primary["open_settlements"] > 0:
        why = f"{primary['open_settlements']} primary settlement row(s) are still open, so result entry is the cleanest next move before interpreting forward performance."
        if primary.get("incomplete_settlements", 0) > 0:
            why += f" There are also {primary['incomplete_settlements']} primary row(s) already marked settled but still missing outcome data, so the ledger needs full cleanup before the forward read is trustworthy."
        return {
            "headline": "Settle the primary lane first",
            "lane_key": primary["lane_key"],
            "lane": primary["lane_label"],
            "command": primary["commands"][0],
            "why": why,
            "timing": "now",
        }

    if primary.get("incomplete_settlements", 0) > 0:
        return {
            "headline": "Complete the primary lane settlement entries",
            "lane_key": primary["lane_key"],
            "lane": primary["lane_label"],
            "command": primary["commands"][1] if len(primary["commands"]) > 1 else primary["commands"][0],
            "why": f"{primary['incomplete_settlements']} primary settlement row(s) are already marked settled but still missing outcome data, so fix those ledger rows before treating the forward metrics as complete.",
            "timing": "now",
        }

    primary_roi_gap_count = roi_gap_count(primary)
    if primary_roi_gap_count > 0:
        return {
            "headline": "Repair the primary lane ROI coverage",
            "lane_key": primary["lane_key"],
            "lane": primary["lane_label"],
            "command": choose_lane_monitor_command(primary),
            "why": f"{primary_roi_gap_count} primary settled row(s) still lack usable ROI coverage ({roi_gap_reason(primary)}), so realized ROI only reflects {primary['roi_covered_settled']}/{primary['settled']} settled races. Repair those missing or malformed return/cost/timestamp values before treating the forward read as fully measured.",
            "timing": "now",
        }

    if shadow["open_settlements"] > 0:
        why = f"Primary is clear, but {shadow['open_settlements']} shadow settlement row(s) still need results if you want the watch list to stay audit-ready."
        if shadow.get("incomplete_settlements", 0) > 0:
            why += f" There are also {shadow['incomplete_settlements']} shadow row(s) already marked settled but still missing outcome data."
        return {
            "headline": "Settle the shadow lane queue",
            "lane_key": shadow["lane_key"],
            "lane": shadow["lane_label"],
            "command": shadow["commands"][0],
            "why": why,
            "timing": "now",
        }

    if shadow.get("incomplete_settlements", 0) > 0:
        return {
            "headline": "Complete the shadow lane settlement entries",
            "lane_key": shadow["lane_key"],
            "lane": shadow["lane_label"],
            "command": shadow["commands"][1] if len(shadow["commands"]) > 1 else shadow["commands"][0],
            "why": f"Primary is clear, but {shadow['incomplete_settlements']} shadow settlement row(s) are already marked settled and still missing outcome data, so clean those up before leaving the watch lane unattended.",
            "timing": "now",
        }

    shadow_roi_gap_count = roi_gap_count(shadow)
    if shadow_roi_gap_count > 0:
        return {
            "headline": "Repair the shadow lane ROI coverage",
            "lane_key": shadow["lane_key"],
            "lane": shadow["lane_label"],
            "command": choose_lane_monitor_command(shadow),
            "why": f"Primary is clear, but {shadow_roi_gap_count} shadow settled row(s) still lack usable ROI coverage ({roi_gap_reason(shadow)}), so the watch-lane ROI only reflects {shadow['roi_covered_settled']}/{shadow['settled']} settled races. Repair those missing or malformed return/cost/timestamp values before treating the shadow read as fully measured.",
            "timing": "now",
        }

    if primary["state"] == "DECISION-GRADE REVIEW":
        return {
            "headline": "Read the primary forward check",
            "lane_key": primary["lane_key"],
            "lane": primary["lane_label"],
            "command": primary["commands"][0],
            "why": f"The primary lane has {primary['settled']} settled races, which is finally enough to treat the forward read as a real comparison instead of early noise.",
            "timing": "now",
        }

    if shadow["state"] == "DECISION-GRADE REVIEW":
        return {
            "headline": "Read the shadow forward check",
            "lane_key": shadow["lane_key"],
            "lane": shadow["lane_label"],
            "command": shadow["commands"][0],
            "why": f"The primary lane is clear, and the shadow lane now has {shadow['settled']} settled races, which is enough to review the watch-list forward read directly instead of leaving it as unresolved background noise.",
            "timing": "now",
        }

    if primary["state"] == "REFRESH RUN ARTIFACTS":
        refresh_why = str(primary.get("why") or "")
        if "pipeline status artifact is missing" in refresh_why:
            headline = "Refresh the daily wrapper, primary lane pipeline status is missing"
        elif "pipeline status artifact is empty" in refresh_why:
            headline = "Refresh the daily wrapper, primary lane pipeline status is empty"
        elif "pipeline status artifact has invalid JSON shape" in refresh_why:
            headline = "Refresh the daily wrapper, primary lane pipeline status has invalid shape"
        elif "pipeline status artifact is unreadable" in refresh_why:
            headline = "Refresh the daily wrapper, primary lane pipeline status is unreadable"
        elif "scanner status sidecar was recorded empty by the pipeline" in refresh_why:
            headline = "Refresh the daily wrapper, primary lane scanner sidecar was recorded empty"
        elif "scanner status sidecar was recorded unreadable by the pipeline" in refresh_why:
            headline = "Refresh the daily wrapper, primary lane scanner sidecar was recorded unreadable"
        elif "scanner status sidecar was recorded invalid-shape by the pipeline" in refresh_why:
            headline = "Refresh the daily wrapper, primary lane scanner sidecar was recorded invalid-shape"
        elif "scan-output artifact was missing" in refresh_why:
            headline = "Refresh the daily wrapper, primary lane scan-output artifact is missing"
        elif "scanner status sidecar is empty" in refresh_why:
            headline = "Refresh the daily wrapper, primary lane scanner sidecar is empty"
        elif "scanner status sidecar has invalid JSON shape" in refresh_why:
            headline = "Refresh the daily wrapper, primary lane scanner sidecar has invalid shape"
        elif "scanner status sidecar is unreadable" in refresh_why:
            headline = "Refresh the daily wrapper, primary lane scanner sidecar is unreadable"
        else:
            headline = "Refresh the daily wrapper, latest run artifacts are incomplete"
        return {
            "headline": headline,
            "lane_key": primary["lane_key"],
            "lane": primary["lane_label"],
            "command": primary["commands"][0],
            "why": refresh_why or "The latest run folder exists, but the primary-lane status sidecars need refresh before the lane is interpreted.",
            "timing": "now",
        }

    if row and row.get("calendar_state") == "OP/CD ACTIVE" and primary["state"] == "RERUN LIVE CHECK":
        return {
            "headline": "Rerun the primary lane live, without --cache-only",
            "lane_key": primary["lane_key"],
            "lane": primary["lane_label"],
            "command": primary["commands"][0],
            "why": "OP / CD are active today, but the latest cache-only check missed the day's cache files. Re-run the daily wrapper live before treating the lane as empty.",
            "timing": "now",
        }

    if row and row.get("calendar_state") == "OP/CD ACTIVE" and row.get("day_bucket") == "ACTIVE, LIMITED COVERAGE WITH ACTIVITY":
        return {
            "headline": "Refresh the primary lane live after the partial-cache activity read",
            "lane_key": primary["lane_key"],
            "lane": primary["lane_label"],
            "command": primary["commands"][0],
            "why": "OP / CD are active today, and the latest primary-lane read still found activity on partial cache coverage. Keep the activity, but refresh the daily wrapper live before leaning on it like a full clean read.",
            "timing": "now",
        }

    if row and row.get("calendar_state") == "OP/CD ACTIVE" and primary["state"] == "LIMITED CACHE COVERAGE":
        return {
            "headline": "Refresh the primary lane live after the partial-cache read",
            "lane_key": primary["lane_key"],
            "lane": primary["lane_label"],
            "command": primary["commands"][0],
            "why": "OP / CD are active today, but the latest primary-lane read finished empty on partial cache coverage. Refresh the daily wrapper live before treating it as a true zero-hit day.",
            "timing": "now",
        }

    if primary["state"] == "CHECK PIPELINE FAILURE":
        recent = str(primary.get("recent_run_context") or "")
        if "recommender failure" in recent:
            failure_label = "recommender failure"
        elif "logger failure" in recent:
            failure_label = "logger failure"
        else:
            failure_label = "pipeline failure"
        return {
            "headline": f"Refresh the daily wrapper, primary lane hit a {failure_label}",
            "lane_key": primary["lane_key"],
            "lane": primary["lane_label"],
            "command": primary["commands"][0],
            "why": primary["why"],
            "timing": "now",
        }

    if primary["state"] == "CHECK SCANNER FAILURE":
        scanner_failure_headline = (
            "Refresh the daily wrapper, primary lane hit an API access failure"
            if "API-access" in str(primary.get("why") or "")
            else "Refresh the daily wrapper, primary lane hit a scanner failure"
        )
        return {
            "headline": scanner_failure_headline,
            "lane_key": primary["lane_key"],
            "lane": primary["lane_label"],
            "command": primary["commands"][0],
            "why": primary["why"],
            "timing": "now",
        }

    if row and row.get("day_bucket") == "UNKNOWN CALENDAR":
        return {
            "headline": "Refresh the daily wrapper, calendar state is unknown",
            "lane_key": primary["lane_key"],
            "lane": primary["lane_label"],
            "command": primary["commands"][0],
            "why": "The latest preflight note did not confirm either active OP / CD cards or a true no-target day, so the quiet read is operationally ambiguous. Refresh the daily wrapper before treating this as a stand-down.",
            "timing": "now",
        }

    if row and row.get("day_bucket") == "NO TARGETS":
        streak = streaks.get("no_target", 0)
        if streak == 1:
            streak_note = " This is the first no-target day at the top of the ops log."
        elif streak > 1:
            streak_note = f" This is {streak} straight no-target days at the top of the ops log."
        else:
            streak_note = ""
        cache_miss_note = ""
        if "cache-only check could not start" in str(primary.get("recent_run_context") or ""):
            cache_miss_note = " The latest wrapper run also missed today's cache files in cache-only mode, which is an operational cache miss, not a rules failure."
        return {
            "headline": "Stand down, no OP / CD target action tonight",
            "lane_key": primary["lane_key"],
            "lane": primary["lane_label"],
            "command": primary["commands"][0],
            "why": f"Latest ops bucket is NO TARGETS, so the quiet primary lane is explained by the race calendar, not by a rules miss.{streak_note}{cache_miss_note}",
            "timing": "next OP / CD race day",
        }

    return {
        "headline": f"Follow the {primary['lane_label']} next-step lead",
        "lane_key": primary["lane_key"],
        "lane": primary["lane_label"],
        "command": primary["commands"][0],
        "why": primary["why"],
        "timing": "now",
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    runs_root = Path(args.runs_root).expanduser()
    run_root = Path(args.run_root).expanduser() if args.run_root else latest_run_root(runs_root)
    if run_root is None:
        raise FileNotFoundError(f"No run folders found under {runs_root}")

    preflight_note_path, preflight_note = resolve_preflight_note_surface(run_root)
    preflight_excluded_tracks = resolve_preflight_excluded_tracks(run_root)
    settlement_audit_path = Path(getattr(args, "settlement_audit", DEFAULT_SETTLEMENT_AUDIT)).expanduser()
    shadow_promotion_gate, shadow_promotion_progress = extract_settlement_audit_promotion_gate(settlement_audit_path, "shadow")
    primary = build_lane_payload(run_root, "primary", args)
    shadow = build_lane_payload(run_root, "shadow", args)
    ops = build_ops_context(run_root, runs_root, args.ops_limit)
    freshness = build_run_freshness(run_root, getattr(args, "as_of_date", None))
    action = choose_best_action(primary, shadow, ops, freshness)
    read_gate = operator_read_gate(primary, shadow, ops, freshness, action)
    row = ops.get("current_row") or ops.get("latest_row")
    gate_minimums = primary.get("decision_gate_minimums") if isinstance(primary.get("decision_gate_minimums"), dict) else {}
    gate_summary = active_decision_gates(primary, shadow)

    stale_snapshot_note = None
    if freshness.get("is_stale"):
        stale_snapshot_note = (
            f"The preflight note/artifact, excluded-track aliases, lane context, current-state counts, ops streaks, and quick reads below are inherited from the latest saved run (`{run_root.name}`) and should be treated as stale snapshot context until the daily wrapper is rerun."
        )

    return {
        "run_root": rel(run_root),
        "run_date": run_root.name,
        "run_freshness": freshness,
        "stale_snapshot_note": stale_snapshot_note,
        "preflight_note": preflight_note,
        "preflight_note_path": rel(preflight_note_path),
        "preflight_excluded_tracks": preflight_excluded_tracks,
        "preflight_excluded_track_count": len(preflight_excluded_tracks),
        "preflight_excluded_track_summary": format_excluded_track_aliases(preflight_excluded_tracks),
        "daily_summary": rel(run_root / "daily_summary.txt"),
        "settlement_audit": rel(settlement_audit_path),
        "shadow_settlement_audit_promotion_gate": shadow_promotion_gate,
        "shadow_settlement_audit_rule_progress": shadow_promotion_progress,
        "best_action": action,
        "operator_read_gate": read_gate,
        "valid_evidence_scope": RIGHT_NOW_VALID_EVIDENCE_SCOPE,
        "evidence_boundary": RIGHT_NOW_EVIDENCE_BOUNDARY,
        "action_priority_contract": RIGHT_NOW_ACTION_PRIORITY_CONTRACT,
        "evidence_frame": {
            "label": "Operational priority surface",
            "summary": "This card is an operational priority read, not a profit-proof or CI-backed forward-validation surface.",
            "detail": "The action is driven by current run artifacts (preflight note, pipeline/scanner status, ledger coverage, and ops streaks), while the lane hierarchy is inherited from the frozen evidence standard: OP_DURABLE_K7 as anchor, CD_CORE_K8 as the primary OP/CD paper-basket companion (not a Phase 8 shadow-lane promotion), and OP_REFINED_K7 as the closest shadow-lane challenger, while KEE_K9 / SA_K9 / DMR_FALL_K7 remain observation-only pockets rather than promotion candidates. The broader selective-family secondary lines stay replay context on walk-forward test years, not extra train-only validation.",
            "limitation": "Treat this as an operator runbook for what to do next; forward performance still needs settled paper trades before the lane says anything new about live edge.",
        },
        "decision_gate_minimums": gate_minimums,
        "active_decision_gates": gate_summary,
        "live_hierarchy": {
            "current_anchor": "OP_DURABLE_K7",
            "primary_shadow": "CD_CORE_K8",
            "primary_companion": "CD_CORE_K8",
            "primary_companion_note": "CD_CORE_K8 is in the primary OP/CD paper-basket, not the Phase 8 shadow/watch lane.",
            "secondary_shadow": "OP_REFINED_K7",
            "observation_only_pockets": ["KEE_K9", "SA_K9", "DMR_FALL_K7"],
        },
        "primary": primary,
        "shadow": shadow,
        "ops": {
            "day_bucket": row.get("day_bucket") if row else None,
            "takeaway": row.get("takeaway") if row else None,
            "streaks": ops["streaks"],
            "ops_history_md": rel(Path(args.ops_history_md).expanduser()),
        },
    }


def render_text(payload: dict[str, Any]) -> str:
    action = payload["best_action"]
    ops = payload["ops"]
    focus_lane = payload[action["lane_key"]]
    evidence = payload["evidence_frame"]
    gate_minimums = payload["decision_gate_minimums"]
    active_gates = payload["active_decision_gates"]
    lines = [
        "Paper-trade right now",
        f"- Latest run: {payload['run_root']}",
        f"- Run freshness: {payload['run_freshness']['summary']}",
        f"- Freshness state: {payload['run_freshness']['freshness_state']}",
        *( [f"- Stale snapshot note: {payload['stale_snapshot_note']}"] if payload.get('stale_snapshot_note') else [] ),
        f"- Best action: {action['headline']}",
        f"- Timing: {action['timing']}",
        f"- Command: {action['command']}",
        f"- Why: {action['why']}",
        f"- valid_evidence_scope={payload['valid_evidence_scope']}",
        f"- Evidence frame: {evidence['label']} — {evidence['summary']}",
        f"- Evidence detail: {evidence['detail']}",
        f"- Limitation: {evidence['limitation']}",
        f"- Action contract: {payload['action_priority_contract']['action_contract_text']}",
        f"- Operator read gate: {payload['operator_read_gate']['read']}",
        f"- Operator read-gate issue flags: {operator_issue_flags_line(payload['operator_read_gate'])}",
        f"- Decision-gate source: {gate_source_text(gate_minimums)}",
        f"- Active right-now gates: {active_gate_line(active_gates)}",
    ]
    if payload.get("preflight_note"):
        lines.append(f"- Preflight note: {payload['preflight_note']}")
    lines.append(f"- Preflight note artifact: {payload['preflight_note_path']}")
    if payload.get("preflight_excluded_track_summary"):
        lines.append(f"- Excluded track aliases: {payload['preflight_excluded_track_summary']}")
    lines.append(f"- Settlement audit: {payload['settlement_audit']}")
    hierarchy = payload["live_hierarchy"]
    lines.extend([
        "- Current live hierarchy:",
        f"  - Primary lane anchor: {hierarchy['current_anchor']} (with {hierarchy['primary_companion']} as the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion)",
        f"  - Shadow lane lead: {hierarchy['secondary_shadow']} (closest challenger only; {', '.join(hierarchy['observation_only_pockets'])} stay observation-only pockets, not promotion candidates)",
    ])
    if payload["primary"].get("recent_run_context"):
        lines.append(f"- Primary lane context: {payload['primary']['recent_run_context']}")
    if payload["primary"].get("why"):
        lines.append(f"- Primary lane why now: {payload['primary']['why']}")
    lines.append(
        f"- Primary lane status sidecars: pipeline={payload['primary']['pipeline_status_json']} | scanner={payload['primary']['scanner_status_json']}"
    )
    if payload["shadow"].get("recent_run_context"):
        lines.append(f"- Shadow lane context: {payload['shadow']['recent_run_context']}")
    if payload["shadow"].get("why"):
        lines.append(f"- Shadow lane why now: {payload['shadow']['why']}")
    lines.append(
        f"- Shadow lane status sidecars: pipeline={payload['shadow']['pipeline_status_json']} | scanner={payload['shadow']['scanner_status_json']}"
    )
    if payload.get("shadow_settlement_audit_promotion_gate"):
        lines.append(f"- Shadow settlement-audit promotion gate: {payload['shadow_settlement_audit_promotion_gate']}")
    if payload.get("shadow_settlement_audit_rule_progress"):
        lines.append(f"- Shadow per-rule promotion coverage: {payload['shadow_settlement_audit_rule_progress']}")
    if ops.get("day_bucket"):
        lines.append(f"- Latest ops bucket: {ops['day_bucket']}")
    if ops.get("takeaway"):
        lines.append(f"- Ops takeaway: {ops['takeaway']}")
    lines.extend([
        f"- Current streaks: no-target={ops['streaks']['no_target']}, active-zero-hit={ops['streaks']['active_zero_hit']}, active-limited-coverage={ops['streaks']['active_limited_coverage']}, active-limited-coverage-with-activity={ops['streaks']['active_limited_coverage_with_activity']}, active-hit-found={ops['streaks']['active_hit_found']}, issue={ops['streaks']['issue']}",
        f"- Primary lane: {payload['primary']['state']} | assessment={payload['primary']['assessment']} | settled={payload['primary']['settled']} | open settlements={payload['primary']['open_settlements']} | incomplete settlements={payload['primary'].get('incomplete_settlements', 0)} | ROI coverage={roi_context_text(payload['primary'])}",
        f"- Shadow lane: {payload['shadow']['state']} | assessment={payload['shadow']['assessment']} | settled={payload['shadow']['settled']} | open settlements={payload['shadow']['open_settlements']} | incomplete settlements={payload['shadow'].get('incomplete_settlements', 0)} | ROI coverage={roi_context_text(payload['shadow'])}",
        "- Quick reads:",
        f"  1. {focus_lane['summary_txt']}",
        f"  2. {focus_lane['next_steps_md']}",
        f"  3. {focus_lane['lane_monitor_md']}",
        f"  4. {payload['daily_summary']}",
        f"  5. {payload['ops']['ops_history_md']}",
    ])
    return "\n".join(lines) + "\n"


def render_md(payload: dict[str, Any]) -> str:
    action = payload["best_action"]
    ops = payload["ops"]
    focus_lane = payload[action["lane_key"]]
    evidence = payload["evidence_frame"]
    gate_minimums = payload["decision_gate_minimums"]
    active_gates = payload["active_decision_gates"]
    lines = [
        "# Paper-Trade Right Now",
        "",
        f"Latest run: `{payload['run_root']}`",
        "",
        "## Best operator action now",
        "",
        f"- Run freshness: {payload['run_freshness']['summary']}",
        f"- Freshness state: `{payload['run_freshness']['freshness_state']}`",
        *( [f"- Stale snapshot note: {payload['stale_snapshot_note']}"] if payload.get('stale_snapshot_note') else [] ),
        f"- Focus: **{action['headline']}**",
        f"- Timing: **{action['timing']}**",
        f"- Command: `{action['command']}`",
        f"- Why: {action['why']}",
        f"- `valid_evidence_scope={payload['valid_evidence_scope']}`",
        f"- Evidence frame: **{evidence['label']}** — {evidence['summary']}",
        f"- Evidence detail: {evidence['detail']}",
        f"- Limitation: {evidence['limitation']}",
        f"- Action contract: {payload['action_priority_contract']['action_contract_text']}",
        f"- Operator read gate: {payload['operator_read_gate']['read']}",
        f"- Operator read-gate issue flags: {operator_issue_flags_line(payload['operator_read_gate'], markdown=True)}",
    ]
    if payload.get("preflight_note"):
        lines.append(f"- Preflight note: {payload['preflight_note']}")
    lines.append(f"- Preflight note artifact: `{payload['preflight_note_path']}`")
    if payload.get("preflight_excluded_track_summary"):
        lines.append(f"- Excluded track aliases: {payload['preflight_excluded_track_summary']}")
    lines.append(f"- Settlement audit: `{payload['settlement_audit']}`")
    lines.extend([
        "",
        "## Decision-Gate Source",
        "",
        f"- Source: `{gate_minimums['source_path']}`; loaded={gate_minimums['source_loaded']}; fallback_used={gate_minimums['fallback_used']}.",
        f"- Scorecard `decision_gate_minimums`: anchor_displacement={gate_minimums['anchor_displacement_min_roi_complete_settled_observations']} ROI-complete same-candidate settled observations; phase8_promotion_review={gate_minimums['phase8_promotion_review_min_roi_complete_settled_observations']} ROI-complete shadow observations; real_money_discussion={gate_minimums['real_money_discussion_min_total_settled_observations_with_usable_roi']} total settled observations with usable ROI.",
        f"- Active right-now gates: {active_gate_line(active_gates, markdown=True)}",
    ])
    hierarchy = payload["live_hierarchy"]
    lines.extend([
        "",
        "## Live lane hierarchy",
        "",
        f"- Primary lane anchor: **{hierarchy['current_anchor']}**; primary OP/CD paper-basket companion: **{hierarchy['primary_companion']}** (not a Phase 8 shadow-lane promotion).",
        f"- Shadow lane lead: **{hierarchy['secondary_shadow']}**; closest challenger only, while **{' / '.join(hierarchy['observation_only_pockets'])}** stay observation-only pockets rather than promotion candidates.",
        *( [f"- Primary lane context: {payload['primary']['recent_run_context']}"] if payload['primary'].get('recent_run_context') else [] ),
        *( [f"- Primary lane why now: {payload['primary']['why']}"] if payload['primary'].get('why') else [] ),
        f"- Primary lane status sidecars: pipeline=`{payload['primary']['pipeline_status_json']}`, scanner=`{payload['primary']['scanner_status_json']}`",
        *( [f"- Shadow lane context: {payload['shadow']['recent_run_context']}"] if payload['shadow'].get('recent_run_context') else [] ),
        *( [f"- Shadow lane why now: {payload['shadow']['why']}"] if payload['shadow'].get('why') else [] ),
        f"- Shadow lane status sidecars: pipeline=`{payload['shadow']['pipeline_status_json']}`, scanner=`{payload['shadow']['scanner_status_json']}`",
        *( [f"- Shadow settlement-audit promotion gate: {payload['shadow_settlement_audit_promotion_gate']}"] if payload.get('shadow_settlement_audit_promotion_gate') else [] ),
        *( [f"- Shadow per-rule promotion coverage: {payload['shadow_settlement_audit_rule_progress']}"] if payload.get('shadow_settlement_audit_rule_progress') else [] ),
        "",
        "## Current context",
        "",
        f"- Latest ops bucket: **{ops.get('day_bucket') or 'unknown'}**",
        f"- Ops takeaway: {ops.get('takeaway') or 'No recent ops row found.'}",
        f"- Current streaks: no-target=`{ops['streaks']['no_target']}`, active-zero-hit=`{ops['streaks']['active_zero_hit']}`, active-limited-coverage=`{ops['streaks']['active_limited_coverage']}`, active-limited-coverage-with-activity=`{ops['streaks']['active_limited_coverage_with_activity']}`, active-hit-found=`{ops['streaks']['active_hit_found']}`, issue=`{ops['streaks']['issue']}`",
        f"- Primary lane: **{payload['primary']['state']}** (`assessment={payload['primary']['assessment']}`, settled=`{payload['primary']['settled']}`, open-settlements=`{payload['primary']['open_settlements']}`, incomplete-settlements=`{payload['primary'].get('incomplete_settlements', 0)}`, roi-coverage={roi_context_md(payload['primary'])})",
        f"- Shadow lane: **{payload['shadow']['state']}** (`assessment={payload['shadow']['assessment']}`, settled=`{payload['shadow']['settled']}`, open-settlements=`{payload['shadow']['open_settlements']}`, incomplete-settlements=`{payload['shadow'].get('incomplete_settlements', 0)}`, roi-coverage={roi_context_md(payload['shadow'])})",
        "",
        "## Quick reads behind this recommendation",
        "",
        f"1. `{focus_lane['summary_txt']}`",
        f"2. `{focus_lane['next_steps_md']}`",
        f"3. `{focus_lane['lane_monitor_md']}`",
        f"4. `{payload['daily_summary']}`",
        f"5. `{payload['ops']['ops_history_md']}`",
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
