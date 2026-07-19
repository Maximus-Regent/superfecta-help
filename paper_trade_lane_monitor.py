#!/usr/bin/env python3
"""
Compact lane monitor for paper-trade forward observation.

Purpose:
- combine the latest forward-check read with the current settlement queue
- give one small artifact per lane that is easy to review after a daily run
- keep the summary anchored to the frozen evaluation standard
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from paper_trade_forward_check import (
    DEFAULT_FROZEN_EVAL,
    DEFAULT_RECOMMENDATION_LEDGER,
    DEFAULT_RULES,
    DEFAULT_SIGNALS_LEDGER,
    SETTLED_STATUS_TOKENS,
    build_payload,
    classify_outcome,
    default_settlement_ledger_path,
    load_csv_rows,
    normalize_token,
    parse_float,
    pct,
    signed_pct,
    settlement_roi_gap_reason,
)
from paper_trade_settlement_helper import SETTLE_COMMAND_TEMPLATE_NOTE, settle_command_template

BASE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = BASE / "out" / "paper_trade_lane_monitor.md"
OPEN_TOKENS = {"", "open", "pending", "unsettled", "todo"}
LANE_MONITOR_VALID_EVIDENCE_SCOPE = "compact per-lane forward-observation and settlement-queue review"
LANE_MONITOR_EVIDENCE_BOUNDARY = {
    "artifact_role": "paper-trade lane monitor",
    "valid_use": LANE_MONITOR_VALID_EVIDENCE_SCOPE,
    "not_new_forward_evidence": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_real_money_evidence": True,
    "non_goals": [
        "do not treat lane-monitor cleanliness as ROI-complete observations",
        "do not treat open settlement queues as sample progress",
        "do not treat scorecard-gate visibility as promotion readiness",
        "do not treat a green lane-monitor rebuild as live profitability or real-money support",
    ],
}
LANE_MONITOR_BOUNDARY_TEXT = (
    "lane monitor is compact forward-observation and settlement-queue metadata only; "
    "not a current-day scanner result, not settled ROI evidence, not promotion readiness, "
    "not live profitability evidence, and not real-money support"
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Show a compact lane monitor with forward status plus open settlement queue")
    p.add_argument("--signals-ledger", default=str(DEFAULT_SIGNALS_LEDGER), help="Signal ledger CSV path")
    p.add_argument("--recommendation-ledger", default=str(DEFAULT_RECOMMENDATION_LEDGER), help="Recommendation ledger CSV path")
    p.add_argument("--settlement-ledger", help="Optional settlement ledger CSV path; defaults from --signals-ledger")
    p.add_argument("--rules", default=str(DEFAULT_RULES), help="Rules JSON path for the lane being checked")
    p.add_argument("--frozen-eval", default=str(DEFAULT_FROZEN_EVAL), help="Frozen evaluation summary CSV path")
    p.add_argument("--min-settled", type=int, default=None, help="Minimum settled races before treating the check as decision-grade; defaults to the scorecard anchor-displacement gate")
    p.add_argument("--portfolio-review-settled", type=int, default=None, help="Broader settled-race milestone for portfolio review readiness; defaults to the scorecard real-money discussion gate")
    p.add_argument("--max-open", type=int, default=5, help="Maximum open settlement rows to show")
    p.add_argument("--format", choices=["text", "md", "json"], default="md", help="Output format")
    p.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Optional output path")
    return p.parse_args()


def is_open_row(row: dict[str, str]) -> bool:
    return str(row.get("settlement_status", "")).strip().lower() in OPEN_TOKENS


def is_incomplete_settled_row(row: dict[str, str]) -> bool:
    return normalize_token(row.get("settlement_status")) in SETTLED_STATUS_TOKENS and not normalize_token(row.get("outcome"))


def has_text(value: str | None) -> bool:
    return bool(str(value or "").strip())


def display_value(value: str | None) -> str:
    text = str(value or "").strip()
    return text if text else "blank"


def roi_gap_reason(row: dict[str, str]) -> str:
    """Explain why a settled hit/miss row cannot contribute to realized ROI yet."""
    return settlement_roi_gap_reason(row)


def lane_gate_alignment_read(gate_minimums: dict[str, Any]) -> str:
    if not gate_minimums.get("cli_overrides") and gate_minimums.get("source_loaded") and not gate_minimums.get("fallback_used"):
        active_gate = str(gate_minimums.get("active_first_read_gate") or "the active first-read gate")
        return f"lane-monitor sample milestones are source-matched to forward_evidence_scorecard.json decision_gate_minimums using {active_gate} for this lane"
    return "lane-monitor sample milestones are using explicit CLI/fallback values; do not treat fixture/custom thresholds as posture-changing gates"


def lane_gate_caution(gate_minimums: dict[str, Any]) -> str:
    active_gate = str(gate_minimums.get("active_first_read_gate") or "").strip()
    if active_gate == "phase8_promotion_review":
        return (
            "Phase 8 shadow first-read status is a review floor, not a promotion entitlement; "
            "lane totals alone do not promote any Phase 8 pocket, scorecard tiers remain binding, "
            "and negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion."
        )
    return ""


def gate_source_text(gate_minimums: dict[str, Any]) -> str:
    return (
        f"{gate_minimums['source_path']} decision_gate_minimums "
        f"loaded={gate_minimums['source_loaded']} "
        f"anchor_displacement={gate_minimums['anchor_displacement_min_roi_complete_settled_observations']} "
        f"phase8_promotion_review={gate_minimums['phase8_promotion_review_min_roi_complete_settled_observations']} "
        f"real_money_discussion={gate_minimums['real_money_discussion_min_total_settled_observations_with_usable_roi']} "
        f"real_money_no_baq_as_bel_required={gate_minimums['real_money_no_baq_as_bel_required']}"
    )


def is_missing_roi_coverage_row(row: dict[str, str]) -> bool:
    return bool(roi_gap_reason(row))


def build_monitor_payload(args: argparse.Namespace) -> dict[str, Any]:
    settlement_path = Path(args.settlement_ledger) if args.settlement_ledger else default_settlement_ledger_path(Path(args.signals_ledger))
    forward_args = SimpleNamespace(
        signals_ledger=args.signals_ledger,
        recommendation_ledger=args.recommendation_ledger,
        settlement_ledger=str(settlement_path),
        rules=args.rules,
        frozen_eval=args.frozen_eval,
        min_settled=args.min_settled,
        portfolio_review_settled=args.portfolio_review_settled,
        format="json",
        output=None,
    )
    forward_payload = build_payload(forward_args)
    settlement_rows = load_csv_rows(settlement_path)
    open_rows = [row for row in settlement_rows if is_open_row(row)]
    shown_rows = open_rows[: max(args.max_open, 0)]
    incomplete_rows = [row for row in settlement_rows if is_incomplete_settled_row(row)]
    shown_incomplete_rows = incomplete_rows[: max(args.max_open, 0)]
    roi_gap_rows = [row for row in settlement_rows if is_missing_roi_coverage_row(row)]
    shown_roi_gap_rows = roi_gap_rows[: max(args.max_open, 0)]

    def row_view(row: dict[str, str]) -> dict[str, str]:
        return {
            "signal_key": row.get("signal_key", ""),
            "rule_id": row.get("rule_id", ""),
            "track": row.get("track", ""),
            "race_number": row.get("race_number", ""),
            "race_id": row.get("race_id", ""),
            "expected_cost": row.get("expected_cost", ""),
            "actual_return": display_value(row.get("actual_return")),
            "actual_cost": display_value(row.get("actual_cost")),
            "roi_gap_reason": roi_gap_reason(row),
            "scan_ts": row.get("scan_ts", ""),
            "settle_command_template": settle_command_template(row.get("signal_key", "")),
            "settle_command_template_note": SETTLE_COMMAND_TEMPLATE_NOTE,
        }

    return {
        "lane_label": forward_payload["lane_label"],
        "rules_path": forward_payload["rules_path"],
        "signals_ledger": forward_payload["signals_ledger"],
        "recommendation_ledger": forward_payload["recommendation_ledger"],
        "settlement_ledger": forward_payload["settlement_ledger"],
        "forward": forward_payload,
        "decision_gate_minimums": forward_payload["decision_gate_minimums"],
        "decision_gate_caution": lane_gate_caution(forward_payload["decision_gate_minimums"]),
        "valid_evidence_scope": LANE_MONITOR_VALID_EVIDENCE_SCOPE,
        "evidence_boundary": LANE_MONITOR_EVIDENCE_BOUNDARY,
        "evidence_boundary_text": LANE_MONITOR_BOUNDARY_TEXT,
        "open_settlements": {
            "count": len(open_rows),
            "shown": len(shown_rows),
            "max_open": args.max_open,
            "rows": [row_view(row) for row in shown_rows],
        },
        "incomplete_settlements": {
            "count": len(incomplete_rows),
            "shown": len(shown_incomplete_rows),
            "max_open": args.max_open,
            "rows": [row_view(row) for row in shown_incomplete_rows],
        },
        "roi_gap_settlements": {
            "count": len(roi_gap_rows),
            "shown": len(shown_roi_gap_rows),
            "max_open": args.max_open,
            "rows": [row_view(row) for row in shown_roi_gap_rows],
        },
    }


def render_text(payload: dict[str, Any]) -> str:
    forward = payload["forward"]
    observed = forward["portfolio_observed"]
    baseline = forward["portfolio_baseline"]
    open_payload = payload["open_settlements"]
    incomplete_payload = payload["incomplete_settlements"]
    roi_gap_payload = payload["roi_gap_settlements"]

    sample_progress = forward["sample_progress"]
    first_read = sample_progress["first_read"]
    portfolio_review = sample_progress["portfolio_review"]
    gate_minimums = payload["decision_gate_minimums"]

    lines = [
        f"{payload['lane_label']} monitor",
        f"- Forward assessment: {forward['portfolio_assessment']}",
        f"- Observed: {observed['settled']} settled, {observed['open']} open, hit rate {pct(observed['hit_rate']) if observed['settled'] else 'n/a'}",
        (
            f"- Observed flat-ticket ROI: {signed_pct(float(observed['actual_roi']))} on {observed['settled_with_roi']} ROI-complete settled race(s) with return/cost/timestamp coverage"
            if observed.get("actual_roi") is not None else
            "- Observed flat-ticket ROI: n/a"
        ),
        (
            f"- ROI coverage: {observed['settled_with_roi']}/{observed['settled']} settled races are ROI-complete ({max(observed['settled'] - observed['settled_with_roi'], 0)} still missing return/cost/timestamp coverage)"
            if observed['settled'] else
            "- ROI coverage: 0/0 settled races are ROI-complete (no settled outcomes yet)"
        ),
        (
            f"- Frozen baseline: {pct(float(baseline['hit_rate']))} hit rate, {signed_pct(float(baseline['roi']))} ROI on {int(baseline['races'])} holdout races"
            if baseline else
            "- Frozen baseline: missing"
        ),
        (
            f"- Sample progress: {first_read['current']}/{first_read['threshold']} ROI-complete settled ({first_read['remaining']} more to first statistical read)"
            if not first_read["ready"] else
            f"- Sample progress: {first_read['current']}/{first_read['threshold']} ROI-complete settled (first statistical read threshold reached)"
        ),
        (
            f"- Broader review progress: {portfolio_review['current']}/{portfolio_review['threshold']} ROI-complete settled ({portfolio_review['remaining']} more to portfolio review gate)"
            if not portfolio_review["ready"] else
            f"- Broader review progress: {portfolio_review['current']}/{portfolio_review['threshold']} ROI-complete settled (portfolio review gate reached)"
        ),
        f"- Gate source: {gate_source_text(gate_minimums)}",
        f"- Active gates: first_read={forward['min_settled']}; portfolio_review={forward['portfolio_review_settled']}. {lane_gate_alignment_read(gate_minimums)}.",
        f"- Decision gate: {forward['decision_gate']}",
        *( [f"- Decision-gate caution: {payload['decision_gate_caution']}"] if payload.get("decision_gate_caution") else [] ),
        f"- valid_evidence_scope={payload['valid_evidence_scope']}",
        f"- Evidence boundary: {payload['evidence_boundary_text']}.",
        f"- Read: {forward['portfolio_note']}",
        f"- Pending settlement rows: {open_payload['count']}",
    ]
    if incomplete_payload["count"]:
        lines.append(f"- Settled rows missing outcome: {incomplete_payload['count']}")
    if roi_gap_payload["count"]:
        lines.append(f"- Settled rows missing ROI-complete coverage: {roi_gap_payload['count']}")
    for row in open_payload["rows"]:
        lines.append(
            f"  - {row['signal_key']} | {row['rule_id']} | {row['track']} R{row['race_number']} | cost {row['expected_cost']} | {row['scan_ts']}"
        )
    if open_payload["count"] > open_payload["shown"]:
        lines.append(f"  - ... plus {open_payload['count'] - open_payload['shown']} more open row(s)")
    if open_payload["rows"]:
        lines.append("- Settlement command templates:")
        lines.append(f"  - {SETTLE_COMMAND_TEMPLATE_NOTE}")
        for row in open_payload["rows"]:
            lines.append(f"  - {row['signal_key']}: {row['settle_command_template']}")
    if incomplete_payload["rows"]:
        lines.append("- Incomplete settled rows:")
        for row in incomplete_payload["rows"]:
            lines.append(
                f"  - {row['signal_key']} | {row['rule_id']} | {row['track']} R{row['race_number']} | cost {row['expected_cost']} | {row['scan_ts']}"
            )
        if incomplete_payload["count"] > incomplete_payload["shown"]:
            lines.append(f"  - ... plus {incomplete_payload['count'] - incomplete_payload['shown']} more incomplete settled row(s)")
    if roi_gap_payload["rows"]:
        lines.append("- Settled rows missing ROI-complete coverage:")
        for row in roi_gap_payload["rows"]:
            lines.append(
                f"  - {row['signal_key']} | {row['rule_id']} | {row['track']} R{row['race_number']} | expected cost {row['expected_cost']} | actual_return {row['actual_return']} | actual_cost {row['actual_cost']} | {row['roi_gap_reason']} | {row['scan_ts']}"
            )
        if roi_gap_payload["count"] > roi_gap_payload["shown"]:
            lines.append(f"  - ... plus {roi_gap_payload['count'] - roi_gap_payload['shown']} more ROI-complete coverage gap row(s)")
    return "\n".join(lines) + "\n"


def render_md(payload: dict[str, Any]) -> str:
    forward = payload["forward"]
    observed = forward["portfolio_observed"]
    baseline = forward["portfolio_baseline"]
    open_payload = payload["open_settlements"]
    incomplete_payload = payload["incomplete_settlements"]
    roi_gap_payload = payload["roi_gap_settlements"]

    sample_progress = forward["sample_progress"]
    first_read = sample_progress["first_read"]
    portfolio_review = sample_progress["portfolio_review"]
    gate_minimums = payload["decision_gate_minimums"]

    lines = [
        "# Paper-Trade Lane Monitor",
        "",
        f"Lane: **{payload['lane_label']}**",
        "",
        "## Forward Snapshot",
        "",
        f"- Assessment: **{forward['portfolio_assessment']}**",
        f"- Observed signals: `{observed['total']}` total, `{observed['settled']}` settled, `{observed['open']}` still open",
        f"- Observed hit rate: `{pct(observed['hit_rate'])}` ({observed['hits']} hit / {observed['settled']} settled)" if observed["settled"] else "- Observed hit rate: `n/a` (no settled races yet)",
        (
            f"- Observed flat-ticket ROI: `{signed_pct(float(observed['actual_roi']))}` on `{observed['settled_with_roi']}` ROI-complete settled race(s) with return/cost/timestamp coverage"
            if observed.get("actual_roi") is not None else
            "- Observed flat-ticket ROI: `n/a`"
        ),
        (
            f"- ROI coverage: `{observed['settled_with_roi']}/{observed['settled']}` settled races are ROI-complete (`{max(observed['settled'] - observed['settled_with_roi'], 0)}` still missing return/cost/timestamp coverage)"
            if observed['settled'] else
            "- ROI coverage: `0/0` settled races are ROI-complete (no settled outcomes yet)"
        ),
        (
            f"- Frozen baseline: `{pct(float(baseline['hit_rate']))}` hit rate, `{signed_pct(float(baseline['roi']))}` ROI on `{int(baseline['races'])}` holdout races"
            if baseline else
            "- Frozen baseline: `missing`"
        ),
        (
            f"- Sample progress: `{first_read['current']}/{first_read['threshold']}` ROI-complete settled ({first_read['remaining']} more to first statistical read)"
            if not first_read["ready"] else
            f"- Sample progress: `{first_read['current']}/{first_read['threshold']}` ROI-complete settled; first statistical read threshold reached"
        ),
        (
            f"- Broader review progress: `{portfolio_review['current']}/{portfolio_review['threshold']}` ROI-complete settled ({portfolio_review['remaining']} more to portfolio review gate)"
            if not portfolio_review["ready"] else
            f"- Broader review progress: `{portfolio_review['current']}/{portfolio_review['threshold']}` ROI-complete settled; portfolio review gate reached"
        ),
        f"- Decision gate: {forward['decision_gate']}",
        f"- Read: {forward['portfolio_note']}",
        "",
        "## Decision-Gate Source",
        "",
        f"- Source: `{gate_minimums['source_path']}`; loaded={gate_minimums['source_loaded']}; fallback_used={gate_minimums['fallback_used']}.",
        f"- Scorecard `decision_gate_minimums`: anchor_displacement={gate_minimums['anchor_displacement_min_roi_complete_settled_observations']} ROI-complete same-candidate settled observations; phase8_promotion_review={gate_minimums['phase8_promotion_review_min_roi_complete_settled_observations']} ROI-complete shadow observations; real_money_discussion={gate_minimums['real_money_discussion_min_total_settled_observations_with_usable_roi']} total settled observations with usable ROI; real_money_requires={'; '.join(gate_minimums['real_money_discussion_also_requires'])}.",
        f"- Active lane-monitor gates: first_read={forward['min_settled']}; portfolio_review={forward['portfolio_review_settled']}. {lane_gate_alignment_read(gate_minimums)}.",
        *( [f"- Decision-gate caution: {payload['decision_gate_caution']}"] if payload.get("decision_gate_caution") else [] ),
        "",
        "## Evidence Boundary",
        "",
        f"- `valid_evidence_scope={payload['valid_evidence_scope']}`",
        f"- Valid use: {payload['valid_evidence_scope']}.",
        f"- Boundary: {payload['evidence_boundary_text']}.",
        "- Non-goals: do not treat open queues, clean rebuilds, scorecard-gate visibility, or validator passes as ROI-complete observations, promotion support, live-profitability proof, or real-money support.",
        "",
        "## Settlement Queue",
        "",
        f"- Open settlement rows: `{open_payload['count']}`",
        f"- Settled rows missing outcome: `{incomplete_payload['count']}`",
        f"- Settled rows missing ROI-complete coverage: `{roi_gap_payload['count']}`",
        f"- Settlement ledger: `{payload['settlement_ledger']}`",
    ]

    if open_payload["rows"]:
        lines.extend([
            "",
            "| Signal Key | Rule | Track | Race # | Race ID | Expected Cost | Scan TS |",
            "|---|---|---|---:|---|---:|---|",
        ])
        for row in open_payload["rows"]:
            lines.append(
                f"| {row['signal_key']} | {row['rule_id']} | {row['track']} | {row['race_number']} | {row['race_id']} | {row['expected_cost']} | {row['scan_ts']} |"
            )
        if open_payload["count"] > open_payload["shown"]:
            lines.append("")
            lines.append(f"- Showing first `{open_payload['shown']}` open row(s).")
        lines.extend([
            "",
            "### Settlement Command Templates",
            "",
            f"- {SETTLE_COMMAND_TEMPLATE_NOTE}",
        ])
        for row in open_payload["rows"]:
            lines.append(f"- `{row['signal_key']}`: `{row['settle_command_template']}`")
    else:
        lines.extend(["", "- No pending settlement rows."])

    if incomplete_payload["rows"]:
        lines.extend([
            "",
            "### Incomplete Settled Rows",
            "",
            "These rows are marked settled but still have no outcome, so the forward metrics exclude them until the ledger is completed.",
            "",
            "| Signal Key | Rule | Track | Race # | Race ID | Expected Cost | Scan TS |",
            "|---|---|---|---:|---|---:|---|",
        ])
        for row in incomplete_payload["rows"]:
            lines.append(
                f"| {row['signal_key']} | {row['rule_id']} | {row['track']} | {row['race_number']} | {row['race_id']} | {row['expected_cost']} | {row['scan_ts']} |"
            )
        if incomplete_payload["count"] > incomplete_payload["shown"]:
            lines.append("")
            lines.append(f"- Showing first `{incomplete_payload['shown']}` incomplete settled row(s).")

    if roi_gap_payload["rows"]:
        lines.extend([
            "",
            "### Settled Rows Missing ROI-Complete Coverage",
            "",
            "These rows have settled outcomes but still cannot contribute to realized ROI or sample gates because return/cost/timestamp coverage is incomplete or malformed.",
            "",
            "| Signal Key | Rule | Track | Race # | Race ID | Expected Cost | Actual Return | Actual Cost | Gap Reason | Scan TS |",
            "|---|---|---|---:|---|---:|---:|---:|---|---|",
        ])
        for row in roi_gap_payload["rows"]:
            lines.append(
                f"| {row['signal_key']} | {row['rule_id']} | {row['track']} | {row['race_number']} | {row['race_id']} | {row['expected_cost']} | {row['actual_return']} | {row['actual_cost']} | {row['roi_gap_reason']} | {row['scan_ts']} |"
            )
        if roi_gap_payload["count"] > roi_gap_payload["shown"]:
            lines.append("")
            lines.append(f"- Showing first `{roi_gap_payload['shown']}` ROI-coverage gap row(s).")

    lines.extend([
        "",
        "## Next Step",
        "",
        (
            "- Use the row-specific `paper_trade_settlement_helper.py settle` template above only after actual result/payout evidence exists, then rerun the forward check or the daily observation wrapper."
            if open_payload["count"] else
            "- Run `paper_trade_settlement_helper.py settle ...` for the incomplete settled rows above after actual result/payout evidence exists, then rerun the forward check or the daily observation wrapper."
            if incomplete_payload["count"] else
            "- Fill in `actual_return`, `actual_cost` if needed, and an actual ISO `settled_ts` for the settled rows missing ROI-complete coverage above, then rerun the forward check or the daily observation wrapper."
            if roi_gap_payload["count"] else
            "- No manual settlement entry is pending right now. Keep running the daily observation wrapper until settled races start to accumulate."
        ),
        "",
    ])
    return "\n".join(lines)


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    payload = build_monitor_payload(args)

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
