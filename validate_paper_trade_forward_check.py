#!/usr/bin/env python3
"""
Fixture-driven validation for paper_trade_forward_check.py.

Purpose:
- pin the frozen-baseline forward-check contract directly at the source layer
- keep NO DATA / TOO EARLY / WITHIN EXPECTED NOISE / RUNNING COLD / RUNNING HOT / NO BASELINE states reproducible
- validate the real CLI against isolated fixtures without touching live ledgers
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import paper_trade_forward_check as forward_check_source
import paper_trade_lane_monitor as lane_monitor_source
import paper_trade_next_steps as next_steps_source
import paper_trade_now as paper_now_source

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "paper_trade_forward_check.py"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "forward_check_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_forward_check"
REPORT_MD = OUT_DIR / "paper_trade_forward_check_validation.md"
REPORT_JSON = OUT_DIR / "paper_trade_forward_check_validation.json"
LIVE_RUNS_ROOT = BASE / "out" / "daily_portfolio_runs"
REBUILD_COMMAND = "python3 validate_paper_trade_forward_check.py"
FROZEN_EVAL = BASE / "frozen_portfolio_eval_summary.csv"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade forward-check validator",
    "valid_evidence_scope": forward_check_source.FORWARD_CHECK_VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "isolated forward-check fixture ledgers",
        "saved live forward-check surfaces",
        "paper_trade_forward_check.py",
        "forward_evidence_scorecard.json decision_gate_minimums",
    ],
    "valid_use": "validator report for frozen-baseline forward-check comparison reproducibility",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "forward_check_validator_passes_are_baseline_comparison_metadata_only": True,
    "non_goals": [
        "do not treat forward-check validator cleanliness as new paper observations",
        "do not treat sub-threshold hot or cold reads as rule-change permission",
        "do not treat scorecard-gate visibility as promotion readiness",
        "do not treat saved-live forward-check parity as live profitability or real-money support",
        "do not substitute BAQ for BEL",
    ],
}

SIGNAL_FIELDS = [
    "signal_key", "scan_ts", "rule_id", "track", "card_name", "race_number", "race_id",
    "surface", "condition", "field_size", "favorite_program", "favorite_name", "favorite_prob",
    "second_prob", "prob_gap", "k", "base_stake", "estimated_cost", "underneath_programs",
    "ticket_structure", "status", "outcome", "notes",
]
RECOMMENDATION_FIELDS = [
    "signal_key", "run_ts", "rule_id", "track", "card_name", "race_number", "race_id", "decision",
    "reason", "favorite_program", "underneath_programs", "scanner_estimated_cost", "scored_combo_count",
    "filtered_combo_count", "bankroll", "race_risk_budget", "total_stake", "total_expected_return",
    "total_expected_profit", "portfolio_expected_roi_pct", "tickets_selected", "tickets_json",
    "prediction_csv", "plan_json", "plan_csv", "status", "outcome", "notes",
]
SETTLEMENT_FIELDS = [
    "signal_key", "scan_ts", "rule_id", "track", "card_name", "race_number", "race_id", "expected_cost",
    "settlement_status", "outcome", "actual_cost", "actual_return", "actual_profit", "settled_ts", "notes",
]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def empty_ledgers(case_root: Path) -> None:
    paper_trades = case_root / "paper_trades"
    write_csv(paper_trades / "phase7_current_paper_paper_trade_signals.csv", SIGNAL_FIELDS, [])
    write_csv(paper_trades / "phase7_current_paper_paper_trade_recommendations.csv", RECOMMENDATION_FIELDS, [])
    write_csv(paper_trades / "phase7_current_paper_paper_trade_settlements.csv", SETTLEMENT_FIELDS, [])


def rules_payload(rule_ids: list[str]) -> dict[str, Any]:
    return {"rules": [{"rule_id": rule_id} for rule_id in rule_ids]}


def signal_row(idx: int, rule_id: str = "OP_DURABLE_K7", track: str = "OP", race_number: int = 7,
               estimated_cost: float = 24.0) -> dict[str, Any]:
    return {
        "signal_key": f"{rule_id.lower()}_{idx:03d}",
        "scan_ts": f"2026-05-03T1{idx % 10}:00:00",
        "rule_id": rule_id,
        "track": track,
        "card_name": "Oaklawn Park" if track == "OP" else "Churchill Downs",
        "race_number": race_number,
        "race_id": f"{track}-2026-05-03-R{race_number}",
        "surface": "dirt",
        "condition": "fast",
        "field_size": 11 if rule_id == "OP_DURABLE_K7" else 10,
        "favorite_program": "1",
        "favorite_name": f"Favorite {idx}",
        "favorite_prob": "0.32",
        "second_prob": "0.18",
        "prob_gap": "0.14",
        "k": "7" if rule_id == "OP_DURABLE_K7" else "8",
        "base_stake": "1",
        "estimated_cost": f"{estimated_cost:.2f}",
        "underneath_programs": "2,3,4",
        "ticket_structure": "1 / 2,3,4",
        "status": "",
        "outcome": "",
        "notes": "fixture",
    }


def settlement_row(signal: dict[str, Any], settlement_status: str, outcome: str,
                   actual_return: float | None = None, *, fill_actual_cost: bool = True,
                   fill_actual_profit: bool = True, actual_cost_override: str | None = None,
                   settled_ts: str | None = None) -> dict[str, Any]:
    cost = float(signal["estimated_cost"])
    if actual_cost_override is not None:
        actual_cost = actual_cost_override
    else:
        actual_cost = f"{cost:.2f}" if settlement_status == "settled" and fill_actual_cost and actual_return is not None else ""
    actual_profit = ""
    if settlement_status == "settled" and fill_actual_profit and actual_return is not None and actual_cost:
        try:
            actual_profit = f"{actual_return - float(actual_cost):.2f}"
        except ValueError:
            actual_profit = ""
    return {
        "signal_key": signal["signal_key"],
        "scan_ts": signal["scan_ts"],
        "rule_id": signal["rule_id"],
        "track": signal["track"],
        "card_name": signal["card_name"],
        "race_number": signal["race_number"],
        "race_id": signal["race_id"],
        "expected_cost": signal["estimated_cost"],
        "settlement_status": settlement_status,
        "outcome": outcome,
        "actual_cost": actual_cost,
        "actual_return": f"{actual_return:.2f}" if isinstance(actual_return, float) else "",
        "actual_profit": actual_profit,
        "settled_ts": ("2026-05-03T19:30:00" if settled_ts is None else settled_ts) if settlement_status == "settled" else "",
        "notes": "fixture",
    }


def recommendation_row(signal: dict[str, Any], decision: str) -> dict[str, Any]:
    return {
        "signal_key": signal["signal_key"],
        "run_ts": signal["scan_ts"],
        "rule_id": signal["rule_id"],
        "track": signal["track"],
        "card_name": signal["card_name"],
        "race_number": signal["race_number"],
        "race_id": signal["race_id"],
        "decision": decision,
        "reason": "fixture",
        "favorite_program": signal["favorite_program"],
        "underneath_programs": signal["underneath_programs"],
        "scanner_estimated_cost": signal["estimated_cost"],
        "scored_combo_count": "3",
        "filtered_combo_count": "1",
        "bankroll": "1000",
        "race_risk_budget": "50",
        "total_stake": signal["estimated_cost"],
        "total_expected_return": "0",
        "total_expected_profit": "0",
        "portfolio_expected_roi_pct": "0",
        "tickets_selected": "1",
        "tickets_json": "[]",
        "prediction_csv": "",
        "plan_json": "",
        "plan_csv": "",
        "status": "done",
        "outcome": "",
        "notes": "fixture",
    }


def setup_case(case_name: str, rules_name: str, rules_json: dict[str, Any], signals: list[dict[str, Any]],
               recommendations: list[dict[str, Any]], settlements: list[dict[str, Any]]) -> tuple[Path, Path, Path, Path, Path]:
    case_root = FIXTURE_ROOT / case_name
    if case_root.exists():
        shutil.rmtree(case_root)
    empty_ledgers(case_root)

    paper_trades = case_root / "paper_trades"
    signals_path = paper_trades / "phase7_current_paper_paper_trade_signals.csv"
    recs_path = paper_trades / "phase7_current_paper_paper_trade_recommendations.csv"
    settlements_path = paper_trades / "phase7_current_paper_paper_trade_settlements.csv"
    rules_path = case_root / rules_name

    write_csv(signals_path, SIGNAL_FIELDS, signals)
    write_csv(recs_path, RECOMMENDATION_FIELDS, recommendations)
    write_csv(settlements_path, SETTLEMENT_FIELDS, settlements)
    write_json(rules_path, rules_json)

    return case_root, signals_path, recs_path, settlements_path, rules_path


def assert_contains(text: str, needle: str, case_name: str) -> None:
    if needle not in text:
        raise AssertionError(f"{case_name}: expected to find {needle!r}")


def assert_forward_check_evidence_boundary(payload: dict[str, Any], case_name: str) -> None:
    boundary = payload.get("evidence_boundary")
    if not isinstance(boundary, dict):
        raise AssertionError(f"{case_name}: forward-check payload is missing evidence_boundary")
    expected = {
        "artifact_role": "paper-trade forward check",
        "valid_use": "frozen-baseline comparison for ROI-complete paper observations",
        "not_new_forward_evidence_by_itself": True,
        "not_current_day_scanner_result": True,
        "not_anchor_change_evidence": True,
        "not_phase8_promotion_evidence": True,
        "not_live_profitability_evidence": True,
        "not_real_money_evidence": True,
    }
    for key, value in expected.items():
        if boundary.get(key) != value:
            raise AssertionError(f"{case_name}: forward-check evidence boundary {key} drifted to {boundary.get(key)!r}")
    if payload.get("valid_evidence_scope") != expected["valid_use"]:
        raise AssertionError(f"{case_name}: forward-check valid_evidence_scope drifted")
    boundary_text = str(payload.get("evidence_boundary_text") or "")
    for phrase in [
        "frozen-baseline comparison for ROI-complete paper observations only",
        "not a current-day scanner result",
        "not new forward evidence by itself",
        "not anchor-change evidence",
        "not Phase 8 promotion evidence",
        "not live-profitability evidence",
        "not real-money support",
    ]:
        if phrase not in boundary_text:
            raise AssertionError(f"{case_name}: forward-check boundary text no longer carries {phrase!r}")
    non_goals = boundary.get("non_goals")
    if not isinstance(non_goals, list) or not all(isinstance(item, str) for item in non_goals):
        raise AssertionError(f"{case_name}: forward-check evidence boundary non_goals must be a string list")
    for phrase in [
        "new observations",
        "rule-change permission",
        "promotion readiness",
        "live-profitability or real-money support",
    ]:
        if not any(phrase in item for item in non_goals):
            raise AssertionError(f"{case_name}: forward-check evidence boundary non_goals lost {phrase!r}")


TOO_EARLY_SIGNALS = [signal_row(i) for i in range(1, 6)]
WITHIN_SIGNALS = [signal_row(i) for i in range(1, 31)]
COLD_SIGNALS = [signal_row(i) for i in range(1, 31)]
HOT_SIGNALS = [signal_row(i) for i in range(1, 31)]
REVIEW_SIGNALS = [signal_row(i) for i in range(1, 101)]
CUSTOM_SIGNALS = [signal_row(1, rule_id="TEST_RULE_X"), signal_row(2, rule_id="TEST_RULE_X")]
TIMESTAMP_GAP_SIGNALS = [signal_row(i) for i in range(1, 31)]
NON_POSITIVE_COST_SIGNALS = [
    signal_row(90, rule_id="OP_DURABLE_K7", estimated_cost=24.0),
    signal_row(91, rule_id="OP_DURABLE_K7", estimated_cost=0.0),
    signal_row(92, rule_id="OP_DURABLE_K7", estimated_cost=24.0),
]

CASES: list[dict[str, Any]] = [
    {
        "name": "case_no_data_open_only",
        "scenario": "open-only ledgers stay NO DATA and keep the frozen baseline visible",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": [signal_row(1), signal_row(2)],
        "recommendations": [],
        "settlements": [
            settlement_row(signal_row(1), "open", ""),
            settlement_row(signal_row(2), "pending", ""),
        ],
        "assessment": "NO DATA",
        "note": "No settled races yet, so this lane has no forward evidence one way or the other.",
        "text_needles": [
            "Phase 7 current paper lane: NO DATA",
            "0 settled / 2 open",
            "sample progress 0/30 ROI-complete",
            "portfolio review progress 0/100 ROI-complete",
            "baseline hit rate 27.43%",
            "decision gate No strategy change: this is still pre-evidence with 0 settled races.",
        ],
        "md_needles": [
            "- Assessment: **NO DATA**",
            "- Observed hit rate: `n/a` (no settled races yet)",
            "- Observed flat-ticket ROI: `n/a` (no settled return values yet)",
            "- Sample progress: `0/30` ROI-complete settled toward the first statistical read (30 more needed)",
            "- Broader review progress: `0/100` ROI-complete settled toward the portfolio review gate (100 more needed)",
            "- Decision gate: No strategy change: this is still pre-evidence with 0 settled races.",
        ],
        "rule_checks": {"OP_DURABLE_K7": "NO DATA", "CD_CORE_K8": "NO DATA"},
    },
    {
        "name": "case_phase8_shadow_uses_promotion_review_gate",
        "scenario": "Phase 8 shadow lanes default to the 20-row promotion-review first-read gate instead of the 30-row anchor-displacement gate",
        "rules_name": "phase8_shadow_rules.json",
        "rules_json": rules_payload(["OP_REFINED_K7"]),
        "signals": [],
        "recommendations": [],
        "settlements": [],
        "assessment": "NO DATA",
        "note": "No settled races yet, so this lane has no forward evidence one way or the other.",
        "text_needles": [
            "Phase 8 shadow lane: NO DATA",
            "gate source forward_evidence_scorecard.json decision_gate_minimums loaded=True anchor_displacement=30 phase8_promotion_review=20 real_money_discussion=100 real_money_no_baq_as_bel_required=True active_first_read_gate=phase8_promotion_review",
            "decision-gate caution Phase 8 shadow first-read status is a review floor, not a promotion entitlement; lane totals alone do not promote any Phase 8 pocket, scorecard tiers remain binding, and negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion.",
            "0 settled / 0 open",
            "sample progress 0/20 ROI-complete",
            "portfolio review progress 0/100 ROI-complete",
            "ROI coverage 0/0 ROI-complete",
            "decision gate No strategy change: this is still pre-evidence with 0 settled races. Collect 20 more ROI-complete settled race(s) for the first statistical read and 100 more for the broader portfolio review gate.",
        ],
        "md_needles": [
            "Lane: **Phase 8 shadow lane**",
            "Active forward-check gates: first_read_gate=phase8_promotion_review; min_settled=20; portfolio_review_settled=100",
            "- Decision-gate caution: Phase 8 shadow first-read status is a review floor, not a promotion entitlement; lane totals alone do not promote any Phase 8 pocket, scorecard tiers remain binding, and negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion.",
            "Sample progress: `0/20` ROI-complete settled toward the first statistical read",
            "Decision-grade first-read threshold in this checker: `20` ROI-complete settled races from `phase8_promotion_review`.",
        ],
        "rule_checks": {"OP_REFINED_K7": "NO DATA"},
        "expected_first_read_gate": "phase8_promotion_review",
        "expected_min_settled": 20,
    },
    {
        "name": "case_incomplete_settlement_outcome",
        "scenario": "rows marked settled without an outcome stay visible as a settlement data gap instead of silently looking like open noise",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": [signal_row(1)],
        "recommendations": [],
        "settlements": [
            settlement_row(signal_row(1), "settled", ""),
        ],
        "assessment": "NO DATA",
        "note": "No settled races yet, so this lane has no forward evidence one way or the other.",
        "text_needles": [
            "Phase 7 current paper lane: NO DATA",
            "0 settled / 0 open",
            "1 settled row(s) missing outcome",
            "sample progress 0/30 ROI-complete",
            "decision gate No strategy change: this is still pre-evidence with 0 settled races.",
        ],
        "md_needles": [
            "- Assessment: **NO DATA**",
            "- Settlement data gap: `1` row(s) are marked settled but still missing an outcome, so they are excluded from hit-rate and ROI checks",
            "Rows marked `settled` with a blank outcome are treated as incomplete settlement data until the outcome is filled.",
            "- Decision gate: No strategy change: this is still pre-evidence with 0 settled races.",
        ],
        "rule_checks": {"OP_DURABLE_K7": "NO DATA", "CD_CORE_K8": "NO DATA"},
    },
    {
        "name": "case_partial_roi_coverage_gap",
        "scenario": "settled outcomes with missing return values keep ROI coverage explicit instead of making realized ROI look fully measured",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": TOO_EARLY_SIGNALS,
        "recommendations": [],
        "settlements": [
            settlement_row(TOO_EARLY_SIGNALS[0], "settled", "HIT", 96.0),
            settlement_row(TOO_EARLY_SIGNALS[1], "settled", "MISS", 0.0, fill_actual_cost=False),
            settlement_row(TOO_EARLY_SIGNALS[2], "settled", "MISS", 0.0, actual_cost_override="bad-cost"),
            settlement_row(TOO_EARLY_SIGNALS[3], "settled", "MISS", None),
            settlement_row(TOO_EARLY_SIGNALS[4], "settled", "MISS", None),
        ],
        "assessment": "TOO EARLY",
        "note": "Only 2 ROI-complete settled race(s) (5 outcome-settled).",
        "text_needles": [
            "Phase 7 current paper lane: TOO EARLY",
            "sample progress 2/30 ROI-complete",
            "portfolio review progress 2/100 ROI-complete",
            "ROI coverage 2/5 ROI-complete",
            "ROI cost source actual=1 expected_fallback=1 missing_or_malformed_cost=1 non_positive_cost=0 missing_return=2",
            "observed ROI +100.00% on 2/5 ROI-complete settled races",
            "decision gate No strategy change: 2 ROI-complete settled race(s) (5 outcome-settled) is below the first statistical-read gate of 30",
        ],
        "md_needles": [
            "- ROI coverage: `2/5` settled race(s) are ROI-complete (`3` still missing return/cost/timestamp coverage)",
            "- ROI timestamp gaps: `0` settled outcome row(s) missing usable settled_ts (`0` missing, `0` placeholder, `0` malformed)",
            "- ROI cost source: `1` actual-cost row(s), `1` expected-cost fallback row(s), `1` missing/malformed cost row(s), `0` non-positive cost row(s)",
            "- ROI return gaps: `2` settled outcome row(s) missing return values; malformed actual-cost rows: `1`",
            "ROI uses 2/5 ROI-complete settled rows; 3 still missing return/cost/timestamp coverage.",
            "- If `actual_cost` is present but malformed, the row is treated as a settlement-quality gap rather than silently falling back to `expected_cost`.",
            "- Missing, placeholder, or malformed `settled_ts` values are settlement-quality gaps and do not count toward ROI-complete sample milestones.",
            "- Decision gate: No strategy change: 2 ROI-complete settled race(s) (5 outcome-settled) is below the first statistical-read gate of 30",
        ],
        "rule_checks": {"OP_DURABLE_K7": "TOO EARLY", "CD_CORE_K8": "NO DATA"},
        "expect_roi": 100.0,
        "expect_roi_cost_source": {
            "roi_actual_cost_rows": 1,
            "roi_expected_cost_fallback_rows": 1,
            "roi_missing_or_malformed_cost_rows": 1,
            "roi_non_positive_cost_rows": 0,
            "roi_missing_return_rows": 2,
            "roi_malformed_actual_cost_rows": 1,
        },
    },
    {
        "name": "case_non_positive_cost_blocks_roi_complete_sample",
        "scenario": "settled outcomes with zero actual or expected cost stay out of ROI-complete sample gates",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": NON_POSITIVE_COST_SIGNALS,
        "recommendations": [],
        "settlements": [
            settlement_row(
                NON_POSITIVE_COST_SIGNALS[0],
                "settled",
                "MISS",
                0.0,
                actual_cost_override="0.00",
            ),
            settlement_row(
                NON_POSITIVE_COST_SIGNALS[1],
                "settled",
                "MISS",
                0.0,
                fill_actual_cost=False,
            ),
            settlement_row(NON_POSITIVE_COST_SIGNALS[2], "settled", "MISS", 0.0),
        ],
        "assessment": "TOO EARLY",
        "note": "Only 1 ROI-complete settled race(s) (3 outcome-settled).",
        "text_needles": [
            "Phase 7 current paper lane: TOO EARLY",
            "sample progress 1/30 ROI-complete",
            "portfolio review progress 1/100 ROI-complete",
            "ROI coverage 1/3 ROI-complete",
            "ROI cost source actual=1 expected_fallback=0 missing_or_malformed_cost=0 non_positive_cost=2 missing_return=0",
            "decision gate No strategy change: 1 ROI-complete settled race(s) (3 outcome-settled) is below the first statistical-read gate of 30",
        ],
        "md_needles": [
            "- ROI coverage: `1/3` settled race(s) are ROI-complete (`2` still missing return/cost/timestamp coverage)",
            "- ROI cost source: `1` actual-cost row(s), `0` expected-cost fallback row(s), `0` missing/malformed cost row(s), `2` non-positive cost row(s)",
            "ROI uses 1/3 ROI-complete settled rows; 2 still missing return/cost/timestamp coverage.",
            "- Decision gate: No strategy change: 1 ROI-complete settled race(s) (3 outcome-settled) is below the first statistical-read gate of 30",
        ],
        "rule_checks": {"OP_DURABLE_K7": "TOO EARLY", "CD_CORE_K8": "NO DATA"},
        "expect_roi": -100.0,
        "expect_roi_cost_source": {
            "roi_actual_cost_rows": 1,
            "roi_expected_cost_fallback_rows": 0,
            "roi_missing_or_malformed_cost_rows": 0,
            "roi_non_positive_cost_rows": 2,
            "roi_missing_return_rows": 0,
            "roi_malformed_actual_cost_rows": 0,
        },
    },
    {
        "name": "case_settled_timestamp_gaps_block_roi_complete_sample",
        "scenario": "settled outcomes with return/cost values but missing, placeholder, or malformed settled_ts values stay below sample-complete gates",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": TIMESTAMP_GAP_SIGNALS,
        "recommendations": [],
        "settlements": [
            settlement_row(
                signal,
                "settled",
                "HIT" if idx <= 8 else "MISS",
                120.0 if idx <= 8 else 0.0,
                settled_ts={1: "", 2: "<SETTLED_TS>", 3: "2026-13-99T99:99:99"}.get(idx),
            )
            for idx, signal in enumerate(TIMESTAMP_GAP_SIGNALS, start=1)
        ],
        "assessment": "TOO EARLY",
        "note": "Only 27 ROI-complete settled race(s) (30 outcome-settled).",
        "text_needles": [
            "Phase 7 current paper lane: TOO EARLY",
            "30 settled / 0 open",
            "sample progress 27/30 ROI-complete",
            "portfolio review progress 27/100 ROI-complete",
            "ROI coverage 27/30 ROI-complete",
            "timestamp_gaps=3 missing_ts=1 placeholder_ts=1 malformed_ts=1",
            "observed ROI -7.41% on 27/30 ROI-complete settled races",
            "decision gate No strategy change: 27 ROI-complete settled race(s) (30 outcome-settled) is below the first statistical-read gate of 30",
        ],
        "md_needles": [
            "- Assessment: **TOO EARLY**",
            "- Observed flat-ticket ROI: `-7.41%` on `27` ROI-complete settled race(s) with return/cost/timestamp coverage",
            "- ROI coverage: `27/30` settled race(s) are ROI-complete (`3` still missing return/cost/timestamp coverage)",
            "- ROI timestamp gaps: `3` settled outcome row(s) missing usable settled_ts (`1` missing, `1` placeholder, `1` malformed)",
            "- Sample progress: `27/30` ROI-complete settled toward the first statistical read (3 more needed)",
            "- Broader review progress: `27/100` ROI-complete settled toward the portfolio review gate (73 more needed)",
            "ROI uses 27/30 ROI-complete settled rows; 3 still missing return/cost/timestamp coverage.",
            "- Decision gate: No strategy change: 27 ROI-complete settled race(s) (30 outcome-settled) is below the first statistical-read gate of 30",
        ],
        "rule_checks": {"OP_DURABLE_K7": "TOO EARLY", "CD_CORE_K8": "NO DATA"},
        "expect_roi": -7.4074074074,
        "expect_roi_cost_source": {
            "roi_actual_cost_rows": 27,
            "roi_expected_cost_fallback_rows": 0,
            "roi_missing_or_malformed_cost_rows": 0,
            "roi_missing_return_rows": 0,
            "roi_malformed_actual_cost_rows": 0,
            "roi_settled_ts_gap_rows": 3,
            "roi_missing_settled_ts_rows": 1,
            "roi_placeholder_settled_ts_rows": 1,
            "roi_malformed_settled_ts_rows": 1,
        },
    },
    {
        "name": "case_too_early_with_recommendation_mix",
        "scenario": "sub-threshold settled samples stay TOO EARLY while recommendation counts remain visible",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": TOO_EARLY_SIGNALS,
        "recommendations": [
            recommendation_row(TOO_EARLY_SIGNALS[0], "BET"),
            recommendation_row(TOO_EARLY_SIGNALS[1], "NO BET"),
            recommendation_row(TOO_EARLY_SIGNALS[2], "ERROR"),
        ],
        "settlements": [
            settlement_row(TOO_EARLY_SIGNALS[0], "settled", "HIT", 120.0),
            settlement_row(TOO_EARLY_SIGNALS[1], "settled", "HIT", 120.0),
            settlement_row(TOO_EARLY_SIGNALS[2], "settled", "MISS", 0.0),
            settlement_row(TOO_EARLY_SIGNALS[3], "settled", "MISS", 0.0),
            settlement_row(TOO_EARLY_SIGNALS[4], "settled", "MISS", 0.0),
        ],
        "assessment": "TOO EARLY",
        "note": "Only 5 ROI-complete settled race(s) (5 outcome-settled).",
        "text_needles": [
            "Phase 7 current paper lane: TOO EARLY",
            "sample progress 5/30 ROI-complete",
            "portfolio review progress 5/100 ROI-complete",
            "observed hit rate 40.00%",
            "observed ROI +100.00%",
            "decision gate No strategy change: 5 ROI-complete settled race(s) (5 outcome-settled) is below the first statistical-read gate of 30",
        ],
        "md_needles": [
            "- Assessment: **TOO EARLY**",
            "- Sample progress: `5/30` ROI-complete settled toward the first statistical read (25 more needed)",
            "- Broader review progress: `5/100` ROI-complete settled toward the portfolio review gate (95 more needed)",
            "- Recommendation flow so far: `3` row(s), `1` BET, `1` NO BET, `1` ERROR",
            "Only 5 ROI-complete settled race(s) (5 outcome-settled).",
            "- Decision gate: No strategy change: 5 ROI-complete settled race(s) (5 outcome-settled) is below the first statistical-read gate of 30",
        ],
        "rule_checks": {"OP_DURABLE_K7": "TOO EARLY", "CD_CORE_K8": "NO DATA"},
    },
    {
        "name": "case_within_expected_noise_cost_fallback",
        "scenario": "decision-grade samples can compute ROI from expected cost fallback and stay within the frozen noise band",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": WITHIN_SIGNALS,
        "recommendations": [],
        "settlements": [
            settlement_row(signal, "settled", "HIT" if idx <= 8 else "MISS", 120.0 if idx <= 8 else 0.0, fill_actual_cost=False, fill_actual_profit=False)
            for idx, signal in enumerate(WITHIN_SIGNALS, start=1)
        ],
        "assessment": "WITHIN EXPECTED NOISE",
        "note": "Observed hit rate sits inside the approximate 2-sigma band",
        "text_needles": [
            "Phase 7 current paper lane: WITHIN EXPECTED NOISE",
            "30 settled / 0 open",
            "sample progress 30/30 ROI-complete",
            "portfolio review progress 30/100 ROI-complete",
            "observed ROI +33.33%",
            "decision gate First read only: 30/100 ROI-complete settled race(s) toward the broader portfolio review gate.",
        ],
        "md_needles": [
            "- Assessment: **WITHIN EXPECTED NOISE**",
            "- Observed flat-ticket ROI: `+33.33%` on `30` ROI-complete settled race(s) with return/cost/timestamp coverage",
            "- Sample progress: `30/30` ROI-complete settled; first statistical read threshold reached",
            "- Broader review progress: `30/100` ROI-complete settled toward the portfolio review gate (70 more needed)",
            "- Approximate 2-sigma hit-rate band at current sample:",
            "- Decision gate: First read only: 30/100 ROI-complete settled race(s) toward the broader portfolio review gate.",
        ],
        "rule_checks": {"OP_DURABLE_K7": "WITHIN EXPECTED NOISE", "CD_CORE_K8": "NO DATA"},
        "expect_roi": 33.3333333333,
    },
    {
        "name": "case_running_cold",
        "scenario": "materially weak settled hit rates trigger RUNNING COLD",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": COLD_SIGNALS,
        "recommendations": [],
        "settlements": [
            settlement_row(signal, "settled", "HIT" if idx <= 1 else "MISS", 120.0 if idx <= 1 else 0.0)
            for idx, signal in enumerate(COLD_SIGNALS, start=1)
        ],
        "assessment": "RUNNING COLD",
        "note": "Observed hit rate is below the approximate 2-sigma band",
        "text_needles": [
            "Phase 7 current paper lane: RUNNING COLD",
            "observed hit rate 3.33%",
            "decision gate First read only: 30/100 ROI-complete settled race(s) toward the broader portfolio review gate.",
        ],
        "md_needles": [
            "- Assessment: **RUNNING COLD**",
            "Observed hit rate is below the approximate 2-sigma band",
            "- Decision gate: First read only: 30/100 ROI-complete settled race(s) toward the broader portfolio review gate.",
        ],
        "rule_checks": {"OP_DURABLE_K7": "RUNNING COLD", "CD_CORE_K8": "NO DATA"},
    },
    {
        "name": "case_running_hot",
        "scenario": "materially strong settled hit rates trigger RUNNING HOT",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": HOT_SIGNALS,
        "recommendations": [],
        "settlements": [
            settlement_row(signal, "settled", "HIT" if idx <= 14 else "MISS", 120.0 if idx <= 14 else 0.0)
            for idx, signal in enumerate(HOT_SIGNALS, start=1)
        ],
        "assessment": "RUNNING HOT",
        "note": "Observed hit rate is above the approximate 2-sigma band",
        "text_needles": [
            "Phase 7 current paper lane: RUNNING HOT",
            "observed hit rate 46.67%",
            "decision gate First read only: 30/100 ROI-complete settled race(s) toward the broader portfolio review gate.",
        ],
        "md_needles": [
            "- Assessment: **RUNNING HOT**",
            "Observed hit rate is above the approximate 2-sigma band",
            "- Decision gate: First read only: 30/100 ROI-complete settled race(s) toward the broader portfolio review gate.",
        ],
        "rule_checks": {"OP_DURABLE_K7": "RUNNING HOT", "CD_CORE_K8": "NO DATA"},
    },
    {
        "name": "case_portfolio_review_gate_reached",
        "scenario": "100 settled rows can reach the broader review gate while still requiring frozen-hierarchy and payout-risk checks before rule changes",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": REVIEW_SIGNALS,
        "recommendations": [],
        "settlements": [
            settlement_row(signal, "settled", "HIT" if idx <= 28 else "MISS", 120.0 if idx <= 28 else 0.0)
            for idx, signal in enumerate(REVIEW_SIGNALS, start=1)
        ],
        "assessment": "WITHIN EXPECTED NOISE",
        "note": "Observed hit rate sits inside the approximate 2-sigma band",
        "text_needles": [
            "Phase 7 current paper lane: WITHIN EXPECTED NOISE",
            "100 settled / 0 open",
            "sample progress 100/30 ROI-complete",
            "portfolio review progress 100/100 ROI-complete",
            "decision gate Portfolio review count reached with ROI-complete settled coverage.",
        ],
        "md_needles": [
            "- Assessment: **WITHIN EXPECTED NOISE**",
            "- Sample progress: `100/30` ROI-complete settled; first statistical read threshold reached",
            "- Broader review progress: `100/100` ROI-complete settled; portfolio review gate reached",
            "- Decision gate: Portfolio review count reached with ROI-complete settled coverage. Still compare hit rate, flat-ticket ROI, concentration/payout risk, and the frozen OP/CD/shadow hierarchy before any rule-promotion or real-money decision.",
        ],
        "rule_checks": {"OP_DURABLE_K7": "RUNNING HOT", "CD_CORE_K8": "NO DATA"},
    },
    {
        "name": "case_no_baseline_custom_rules",
        "scenario": "custom lanes without frozen rows say NO BASELINE instead of guessing",
        "rules_name": "custom_lane_rules.json",
        "rules_json": rules_payload(["TEST_RULE_X"]),
        "signals": CUSTOM_SIGNALS,
        "recommendations": [],
        "settlements": [
            settlement_row(CUSTOM_SIGNALS[0], "settled", "HIT", 120.0),
            settlement_row(CUSTOM_SIGNALS[1], "settled", "MISS", 0.0),
        ],
        "assessment": "NO BASELINE",
        "note": "Lane is missing a frozen portfolio baseline.",
        "text_needles": [
            "custom lane rules: NO BASELINE",
            "observed hit rate 50.00%",
            "decision gate No strategy change: 2 ROI-complete settled race(s) (2 outcome-settled) is below the first statistical-read gate of 30",
        ],
        "md_needles": [
            "Lane: **custom lane rules**",
            "- Frozen baseline: `missing`",
            "Rule is missing from the frozen holdout summary.",
            "- Decision gate: No strategy change: 2 ROI-complete settled race(s) (2 outcome-settled) is below the first statistical-read gate of 30",
        ],
        "rule_checks": {"TEST_RULE_X": "NO BASELINE"},
    },
]


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_root, signals_path, recs_path, settlements_path, rules_path = setup_case(
        case_name=case["name"],
        rules_name=case["rules_name"],
        rules_json=case["rules_json"],
        signals=case["signals"],
        recommendations=case["recommendations"],
        settlements=case["settlements"],
    )

    json_output = case_root / "forward_check.json"
    text_output = case_root / "forward_check.txt"
    md_output = case_root / "forward_check.md"

    common = [
        sys.executable,
        str(SCRIPT),
        "--signals-ledger", str(signals_path),
        "--recommendation-ledger", str(recs_path),
        "--settlement-ledger", str(settlements_path),
        "--rules", str(rules_path),
        "--frozen-eval", str(FROZEN_EVAL),
    ]

    json_result = subprocess.run(common + ["--format", "json", "--output", str(json_output)], cwd=BASE, capture_output=True, text=True, check=True)
    payload = json.loads(json_result.stdout)
    subprocess.run(common + ["--format", "text", "--output", str(text_output)], cwd=BASE, capture_output=True, text=True, check=True)
    subprocess.run(common + ["--format", "md", "--output", str(md_output)], cwd=BASE, capture_output=True, text=True, check=True)

    gate_minimums = payload["decision_gate_minimums"]
    expected_first_read_gate = case.get("expected_first_read_gate", "anchor_displacement")
    expected_min_settled = case.get("expected_min_settled", 30)
    if not (
        gate_minimums["source_path"] == "forward_evidence_scorecard.json"
        and gate_minimums["source_loaded"] is True
        and gate_minimums["fallback_used"] is False
        and gate_minimums["anchor_displacement_min_roi_complete_settled_observations"] == 30
        and gate_minimums["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
        and gate_minimums["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
        and gate_minimums["real_money_discussion_also_requires"] == [
            "positive paper ROI",
            "concentration checks",
            "payout-distribution sanity checks",
            "no BAQ-as-BEL substitution",
        ]
        and gate_minimums["real_money_no_baq_as_bel_required"] is True
        and gate_minimums["active_first_read_gate"] == expected_first_read_gate
        and payload["min_settled"] == expected_min_settled
        and payload["portfolio_review_settled"] == 100
        and not gate_minimums["cli_overrides"]
        and f"using {expected_first_read_gate} for this lane" in gate_minimums["alignment_read"]
    ):
        raise AssertionError(f"{case['name']}: forward-check gate minimums drifted from scorecard decision_gate_minimums: {gate_minimums!r}")
    if expected_first_read_gate == "phase8_promotion_review":
        assert_contains(payload.get("decision_gate_caution", ""), "Phase 8 shadow first-read status is a review floor", case["name"])
    elif payload.get("decision_gate_caution"):
        raise AssertionError(f"{case['name']}: unexpected decision-gate caution for non-Phase 8 lane")
    assert_forward_check_evidence_boundary(payload, case["name"])

    if payload["portfolio_assessment"] != case["assessment"]:
        raise AssertionError(
            f"{case['name']}: expected assessment {case['assessment']!r}, got {payload['portfolio_assessment']!r}"
        )
    assert_contains(payload["portfolio_note"], case["note"], case["name"])

    rule_map = {row["rule_id"]: row["assessment"] for row in payload["rule_summaries"]}
    for rule_id, expected in case["rule_checks"].items():
        if rule_map.get(rule_id) != expected:
            raise AssertionError(
                f"{case['name']}: expected rule {rule_id} assessment {expected!r}, got {rule_map.get(rule_id)!r}"
            )

    if "expect_roi" in case:
        actual_roi = float(payload["portfolio_observed"]["actual_roi"])
        if abs(actual_roi - float(case["expect_roi"])) > 0.01:
            raise AssertionError(f"{case['name']}: expected ROI about {case['expect_roi']}, got {actual_roi}")

    for key, expected in case.get("expect_roi_cost_source", {}).items():
        actual = payload["portfolio_observed"].get(key)
        if actual != expected:
            raise AssertionError(f"{case['name']}: expected portfolio_observed.{key}={expected!r}, got {actual!r}")

    text = text_output.read_text(encoding="utf-8")
    md = md_output.read_text(encoding="utf-8")
    expected_json = json.dumps(payload, indent=2) + "\n"
    expected_text = forward_check_source.render_text(payload)
    expected_md = forward_check_source.render_md(payload) + "\n"

    saved_json = json_output.read_text(encoding="utf-8")
    if saved_json != expected_json:
        raise AssertionError(f"{case['name']}: forward_check.json no longer matches the current JSON render")
    if text != expected_text:
        raise AssertionError(f"{case['name']}: forward_check.txt no longer matches a fresh text render from paper_trade_forward_check.py")
    if md != expected_md:
        raise AssertionError(f"{case['name']}: forward_check.md no longer matches a fresh markdown render from paper_trade_forward_check.py")

    assert_contains(text, f": {case['assessment']}", case["name"])
    assert_contains(md, f"- Assessment: **{case['assessment']}**", case["name"])
    assert_contains(text, "gate source forward_evidence_scorecard.json decision_gate_minimums", case["name"])
    assert_contains(text, "anchor_displacement=30", case["name"])
    assert_contains(text, "phase8_promotion_review=20", case["name"])
    assert_contains(text, "real_money_discussion=100", case["name"])
    assert_contains(text, "real_money_no_baq_as_bel_required=True", case["name"])
    assert_contains(text, "valid_evidence_scope=frozen-baseline comparison for ROI-complete paper observations", case["name"])
    assert_contains(text, "evidence boundary forward check is a frozen-baseline comparison for ROI-complete paper observations only; not a current-day scanner result, not new forward evidence by itself, not anchor-change evidence, not Phase 8 promotion evidence, not live-profitability evidence, and not real-money support", case["name"])
    assert_contains(text, "ROI coverage", case["name"])
    assert_contains(text, "ROI cost source actual=", case["name"])
    assert_contains(text, "timestamp_gaps=", case["name"])
    assert_contains(md, "## Decision-Gate Source", case["name"])
    assert_contains(md, "Scorecard `decision_gate_minimums`", case["name"])
    assert_contains(md, "anchor_displacement=30", case["name"])
    assert_contains(md, "phase8_promotion_review=20", case["name"])
    assert_contains(md, "real_money_discussion=100", case["name"])
    assert_contains(md, "real_money_requires=positive paper ROI; concentration checks; payout-distribution sanity checks; no BAQ-as-BEL substitution", case["name"])
    assert_contains(md, "not live-profitability, promotion, anchor-change, or real-money evidence", case["name"])
    assert_contains(md, "## Evidence Boundary", case["name"])
    assert_contains(md, "- `valid_evidence_scope=frozen-baseline comparison for ROI-complete paper observations`", case["name"])
    assert_contains(md, "- Valid use: frozen-baseline comparison for ROI-complete paper observations.", case["name"])
    assert_contains(md, "- Boundary: forward check is a frozen-baseline comparison for ROI-complete paper observations only; not a current-day scanner result, not new forward evidence by itself, not anchor-change evidence, not Phase 8 promotion evidence, not live-profitability evidence, and not real-money support.", case["name"])
    assert_contains(md, "- ROI coverage:", case["name"])
    assert_contains(md, "- ROI cost source:", case["name"])
    assert_contains(md, "- ROI return gaps:", case["name"])
    assert_contains(md, "- ROI timestamp gaps:", case["name"])
    assert_contains(payload["decision_gate"], "settled", case["name"])
    assert_contains(text, "decision gate", case["name"])
    assert_contains(md, "- Decision gate:", case["name"])
    for needle in case["text_needles"]:
        assert_contains(text, needle, case["name"])
    for needle in case["md_needles"]:
        assert_contains(md, needle, case["name"])

    return {
        "case": case["name"],
        "scenario": case["scenario"],
        "assessment": payload["portfolio_assessment"],
        "portfolio_note": payload["portfolio_note"],
        "settled": payload["portfolio_observed"]["settled"],
        "open": payload["portfolio_observed"]["open"],
        "text_output": str(text_output.relative_to(BASE)),
        "md_output": str(md_output.relative_to(BASE)),
    }


def live_lane_dirs() -> list[Path]:
    lanes: list[Path] = []
    if not LIVE_RUNS_ROOT.exists():
        raise AssertionError(f"no live run folders found under {LIVE_RUNS_ROOT}")
    for run_root in sorted(p for p in LIVE_RUNS_ROOT.iterdir() if p.is_dir()):
        for lane_dir in sorted(p for p in run_root.iterdir() if p.is_dir()):
            if (lane_dir / "forward_check.txt").exists() and (lane_dir / "forward_check.md").exists():
                lanes.append(lane_dir)
    if not lanes:
        raise AssertionError(f"no live forward-check surfaces found under {LIVE_RUNS_ROOT}")
    return lanes


def validate_live_surfaces() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for lane_dir in live_lane_dirs():
        lane_name = lane_dir.name
        args = argparse.Namespace(
            signals_ledger=str(BASE / "paper_trades" / f"{lane_name}_paper_trade_signals.csv"),
            recommendation_ledger=str(BASE / "paper_trades" / f"{lane_name}_paper_trade_recommendations.csv"),
            settlement_ledger=str(BASE / "paper_trades" / f"{lane_name}_paper_trade_settlements.csv"),
            rules=str(BASE / f"{lane_name}_rules.json"),
            frozen_eval=str(FROZEN_EVAL),
            min_settled=None,
            portfolio_review_settled=None,
            format="json",
            output=None,
        )
        payload = forward_check_source.build_payload(args)
        assert_forward_check_evidence_boundary(payload, f"live_surface_{lane_dir.parent.name}_{lane_name}")
        expected_text = forward_check_source.render_text(payload)
        expected_md = forward_check_source.render_md(payload) + "\n"
        text_path = lane_dir / "forward_check.txt"
        md_path = lane_dir / "forward_check.md"
        if text_path.read_text(encoding="utf-8") != expected_text:
            raise AssertionError(f"live forward_check.txt drifted from the current source-layer rebuild: {text_path}")
        if md_path.read_text(encoding="utf-8") != expected_md:
            raise AssertionError(f"live forward_check.md drifted from the current source-layer rebuild: {md_path}")
        results.append({
            "case": f"live_surface_{lane_dir.parent.name}_{lane_name}",
            "scenario": "saved live forward-check surfaces match the current source-layer rebuild",
            "assessment": payload["portfolio_assessment"],
            "portfolio_note": payload["portfolio_note"],
            "settled": payload["portfolio_observed"]["settled"],
            "open": payload["portfolio_observed"]["open"],
            "lane_dir": str(lane_dir.relative_to(BASE)),
            "text_output": str(text_path.relative_to(BASE)),
            "md_output": str(md_path.relative_to(BASE)),
        })
    return results


def validate_legacy_phase7_label() -> dict[str, str]:
    portfolio_name, lane_label, rule_ids = forward_check_source.read_rules(BASE / "phase7_live_rules.json")
    if portfolio_name != "phase7_live":
        raise AssertionError(f"legacy Phase 7 portfolio key changed unexpectedly: {portfolio_name!r}")
    if lane_label != "Phase 7 legacy rules lane":
        raise AssertionError(f"legacy Phase 7 rules label should stay paper-safe, got {lane_label!r}")
    if "live lane" in lane_label.lower():
        raise AssertionError(f"legacy Phase 7 rules label must not render as a live lane: {lane_label!r}")
    if rule_ids != ["BEL_BROAD1_K7", "OP_DURABLE_K7", "CD_CORE_K8"]:
        raise AssertionError(f"legacy Phase 7 rule ids changed unexpectedly: {rule_ids!r}")
    return {
        "case": "case_legacy_phase7_rules_label_is_paper_safe",
        "scenario": "phase7_live_rules.json keeps its compatibility baseline key but renders as a legacy rules lane rather than a live lane",
        "assessment": "PASS",
        "portfolio_name": portfolio_name,
        "lane_label": lane_label,
        "rule_ids": ", ".join(rule_ids),
        "settled": 0,
        "open": 0,
    }


def validate_gate_fallback_alignment_read(fallback_gate_minimums: dict[str, Any]) -> dict[str, str]:
    original_loader = forward_check_source.load_scorecard_gate_minimums

    def patched_loader(path: Path = FROZEN_EVAL) -> dict[str, Any]:
        return fallback_gate_minimums

    forward_check_source.load_scorecard_gate_minimums = patched_loader
    try:
        resolved = forward_check_source.resolve_gate_minimums(
            argparse.Namespace(min_settled=None, portfolio_review_settled=None),
            "phase7_live",
            BASE / "phase7_current_paper_rules.json",
        )
    finally:
        forward_check_source.load_scorecard_gate_minimums = original_loader

    alignment_reads = {
        "forward_check": resolved["alignment_read"],
        "lane_monitor": lane_monitor_source.lane_gate_alignment_read(resolved),
        "next_steps": next_steps_source.next_steps_gate_alignment_read(resolved),
        "right_now": paper_now_source.right_now_gate_alignment_read(resolved),
    }
    for name, read in alignment_reads.items():
        if "explicit CLI/fallback values" not in read:
            raise AssertionError(f"{name} fallback alignment read did not label the gate source as fallback/custom: {read!r}")
        if "source-matched to forward_evidence_scorecard.json decision_gate_minimums" in read:
            raise AssertionError(f"{name} fallback alignment read still claims source-matched gates: {read!r}")
    if resolved["active_min_settled"] != 30 or resolved["active_portfolio_review_settled"] != 100:
        raise AssertionError(f"fallback alignment fixture shrank active gates unexpectedly: {resolved!r}")

    return {
        "case": "case_gate_fallback_alignment_reads_are_not_source_matched",
        "scenario": "lowered or malformed scorecard gate metadata still uses conservative active gates and renders as fallback/custom alignment reads",
        "assessment": "PASS",
        "forward_check_alignment_read": alignment_reads["forward_check"],
        "lane_monitor_alignment_read": alignment_reads["lane_monitor"],
        "next_steps_alignment_read": alignment_reads["next_steps"],
        "right_now_alignment_read": alignment_reads["right_now"],
    }


def validate_malformed_scorecard_cli_fallback_artifact() -> dict[str, Any]:
    case_name = "case_malformed_scorecard_cli_fallback_artifact"
    signal = signal_row(1)
    case_root, signals_path, recs_path, settlements_path, rules_path = setup_case(
        case_name=case_name,
        rules_name="phase7_current_paper_rules.json",
        rules_json=rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        signals=[signal],
        recommendations=[],
        settlements=[settlement_row(signal, "open", "")],
    )
    bad_scorecard = case_root / "bad_scorecard_gate_minimums.json"
    write_json(
        bad_scorecard,
        {
            "decision_gate_minimums": {
                "anchor_displacement": {"min_roi_complete_settled_observations": True},
                "phase8_promotion_review": {"min_roi_complete_settled_observations": 20},
                "real_money_discussion": {
                    "min_total_settled_observations_with_usable_roi": 100,
                    "also_requires": [
                        "positive paper ROI",
                        "concentration checks",
                        "payout-distribution sanity checks",
                        "no BAQ-as-BEL substitution",
                    ],
                },
            }
        },
    )
    json_output = case_root / "forward_check_bad_scorecard.json"
    text_output = case_root / "forward_check_bad_scorecard.txt"
    md_output = case_root / "forward_check_bad_scorecard.md"
    common = [
        sys.executable,
        str(SCRIPT),
        "--signals-ledger", str(signals_path),
        "--recommendation-ledger", str(recs_path),
        "--settlement-ledger", str(settlements_path),
        "--rules", str(rules_path),
        "--frozen-eval", str(FROZEN_EVAL),
        "--scorecard-json", str(bad_scorecard),
    ]

    json_result = subprocess.run(common + ["--format", "json", "--output", str(json_output)], cwd=BASE, capture_output=True, text=True, check=True)
    payload = json.loads(json_result.stdout)
    subprocess.run(common + ["--format", "text", "--output", str(text_output)], cwd=BASE, capture_output=True, text=True, check=True)
    subprocess.run(common + ["--format", "md", "--output", str(md_output)], cwd=BASE, capture_output=True, text=True, check=True)

    gate_minimums = payload["decision_gate_minimums"]
    if not (
        gate_minimums["source_path"].endswith("bad_scorecard_gate_minimums.json")
        and gate_minimums["source_loaded"] is True
        and gate_minimums["fallback_used"] is True
        and "malformed" in gate_minimums["fallback_reason"]
        and "positive non-boolean integer" in gate_minimums["malformed_gate_error"]
        and gate_minimums["anchor_displacement_min_roi_complete_settled_observations"] == 30
        and gate_minimums["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
        and gate_minimums["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
        and gate_minimums["real_money_discussion_also_requires"] == ["no BAQ-as-BEL substitution"]
        and gate_minimums["real_money_no_baq_as_bel_required"] is True
        and gate_minimums["active_first_read_gate"] == "anchor_displacement"
        and payload["min_settled"] == 30
        and payload["portfolio_review_settled"] == 100
        and "explicit CLI/fallback values" in gate_minimums["alignment_read"]
        and "source-matched to forward_evidence_scorecard.json decision_gate_minimums" not in gate_minimums["alignment_read"]
    ):
        raise AssertionError(f"{case_name}: malformed scorecard CLI fallback did not stay conservative and labeled: {gate_minimums!r}")

    expected_json = json.dumps(payload, indent=2) + "\n"
    expected_text = forward_check_source.render_text(payload)
    expected_md = forward_check_source.render_md(payload) + "\n"
    if json_output.read_text(encoding="utf-8") != expected_json:
        raise AssertionError(f"{case_name}: fallback JSON artifact no longer matches the current JSON render")
    text = text_output.read_text(encoding="utf-8")
    md = md_output.read_text(encoding="utf-8")
    if text != expected_text:
        raise AssertionError(f"{case_name}: fallback text artifact no longer matches a fresh text render")
    if md != expected_md:
        raise AssertionError(f"{case_name}: fallback markdown artifact no longer matches a fresh markdown render")
    assert_contains(text, "bad_scorecard_gate_minimums.json decision_gate_minimums loaded=True", case_name)
    assert_contains(text, "anchor_displacement=30", case_name)
    assert_contains(text, "real_money_no_baq_as_bel_required=True", case_name)
    assert_contains(md, "fallback_used=True", case_name)
    assert_contains(md, "forward-check sample milestones are using explicit CLI/fallback values", case_name)
    assert_contains(md, "not live-profitability, promotion, anchor-change, or real-money evidence", case_name)

    return {
        "case": case_name,
        "scenario": "real CLI outputs stay conservative and visibly fallback/custom when the scorecard sidecar has malformed gate metadata",
        "assessment": payload["portfolio_assessment"],
        "portfolio_note": payload["portfolio_note"],
        "settled": payload["portfolio_observed"]["settled"],
        "open": payload["portfolio_observed"]["open"],
        "text_output": str(text_output.relative_to(BASE)),
        "md_output": str(md_output.relative_to(BASE)),
    }


def main() -> int:
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for legacy in (
        FIXTURE_ROOT / "forward_check_fixture_validation.md",
        FIXTURE_ROOT / "forward_check_fixture_validation.json",
    ):
        legacy.unlink(missing_ok=True)

    fixture_results = [run_case(case) for case in CASES]
    fixture_results.append(validate_malformed_scorecard_cli_fallback_artifact())
    live_surfaces = validate_live_surfaces()
    label_guardrail = validate_legacy_phase7_label()
    results = fixture_results + live_surfaces
    lowered_gate_path = FIXTURE_ROOT / "lowered_scorecard_gate_minimums.json"
    lowered_gate_path.write_text(
        json.dumps(
            {
                "decision_gate_minimums": {
                    "anchor_displacement": {"min_roi_complete_settled_observations": 5},
                    "phase8_promotion_review": {"min_roi_complete_settled_observations": 3},
                    "real_money_discussion": {
                        "min_total_settled_observations_with_usable_roi": 25,
                        "also_requires": [
                            "positive paper ROI",
                            "concentration checks",
                            "payout-distribution sanity checks",
                            "no BAQ-as-BEL substitution",
                        ],
                    },
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    lowered_gate_minimums = forward_check_source.load_scorecard_gate_minimums(lowered_gate_path)
    bool_gate_path = FIXTURE_ROOT / "bool_scorecard_gate_minimums.json"
    bool_gate_path.write_text(
        json.dumps(
            {
                "decision_gate_minimums": {
                    "anchor_displacement": {"min_roi_complete_settled_observations": True},
                    "phase8_promotion_review": {"min_roi_complete_settled_observations": 20},
                    "real_money_discussion": {
                        "min_total_settled_observations_with_usable_roi": 100,
                        "also_requires": [
                            "positive paper ROI",
                            "concentration checks",
                            "payout-distribution sanity checks",
                            "no BAQ-as-BEL substitution",
                        ],
                    },
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    bool_gate_minimums = forward_check_source.load_scorecard_gate_minimums(bool_gate_path)
    missing_no_baq_gate_path = FIXTURE_ROOT / "missing_no_baq_scorecard_gate_minimums.json"
    missing_no_baq_gate_path.write_text(
        json.dumps(
            {
                "decision_gate_minimums": {
                    "anchor_displacement": {"min_roi_complete_settled_observations": 30},
                    "phase8_promotion_review": {"min_roi_complete_settled_observations": 20},
                    "real_money_discussion": {
                        "min_total_settled_observations_with_usable_roi": 100,
                        "also_requires": [
                            "positive paper ROI",
                            "concentration checks",
                            "payout-distribution sanity checks",
                        ],
                    },
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    missing_no_baq_gate_minimums = forward_check_source.load_scorecard_gate_minimums(missing_no_baq_gate_path)
    if not (
        lowered_gate_minimums["source_loaded"] is True
        and lowered_gate_minimums["fallback_used"] is True
        and "fell below conservative historical floors" in lowered_gate_minimums["fallback_reason"]
        and lowered_gate_minimums["anchor_displacement_min_roi_complete_settled_observations"] == 30
        and lowered_gate_minimums["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
        and lowered_gate_minimums["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
        and lowered_gate_minimums["real_money_no_baq_as_bel_required"] is True
        and lowered_gate_minimums["rejected_lowered_values"]["anchor_displacement_min_roi_complete_settled_observations"] == {"loaded_value": 5, "conservative_floor": 30}
        and lowered_gate_minimums["rejected_lowered_values"]["phase8_promotion_review_min_roi_complete_settled_observations"] == {"loaded_value": 3, "conservative_floor": 20}
        and lowered_gate_minimums["rejected_lowered_values"]["real_money_discussion_min_total_settled_observations_with_usable_roi"] == {"loaded_value": 25, "conservative_floor": 100}
    ):
        raise AssertionError(f"lowered scorecard gate floors did not fall back to conservative values: {lowered_gate_minimums!r}")
    if not (
        bool_gate_minimums["source_loaded"] is True
        and bool_gate_minimums["fallback_used"] is True
        and "malformed" in bool_gate_minimums["fallback_reason"]
        and bool_gate_minimums["anchor_displacement_min_roi_complete_settled_observations"] == 30
        and bool_gate_minimums["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
        and bool_gate_minimums["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
        and bool_gate_minimums["real_money_no_baq_as_bel_required"] is True
        and "positive non-boolean integer" in bool_gate_minimums["malformed_gate_error"]
    ):
        raise AssertionError(f"boolean scorecard gate floors were not treated as malformed conservative fallback: {bool_gate_minimums!r}")
    if not (
        missing_no_baq_gate_minimums["source_loaded"] is True
        and missing_no_baq_gate_minimums["fallback_used"] is True
        and "malformed" in missing_no_baq_gate_minimums["fallback_reason"]
        and missing_no_baq_gate_minimums["anchor_displacement_min_roi_complete_settled_observations"] == 30
        and missing_no_baq_gate_minimums["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
        and missing_no_baq_gate_minimums["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
        and missing_no_baq_gate_minimums["real_money_discussion_also_requires"] == ["no BAQ-as-BEL substitution"]
        and missing_no_baq_gate_minimums["real_money_no_baq_as_bel_required"] is True
        and "no BAQ-as-BEL substitution" in missing_no_baq_gate_minimums["malformed_gate_error"]
    ):
        raise AssertionError(f"missing no-BAQ scorecard prerequisite was not treated as malformed conservative fallback: {missing_no_baq_gate_minimums!r}")
    gate_fallback_alignment = validate_gate_fallback_alignment_read(bool_gate_minimums)
    if BASE.resolve() not in FIXTURE_ROOT.resolve().parents:
        raise AssertionError("forward-check fixture root is not project-local")
    scratch = {
        "fixture_root_relative": str(FIXTURE_ROOT.relative_to(BASE)),
        "fixture_root_is_project_local": True,
        "case_roots_cleared_by_setup_case": True,
        "report_root_relative": str(OUT_DIR.relative_to(BASE)),
        "evidence_boundary": "forward-check fixture scratch metadata is reproducibility context only, not new forward evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
    }
    suite_read = (
        "forward-check helper still preserves NO DATA, TOO EARLY, WITHIN EXPECTED NOISE, RUNNING COLD, RUNNING HOT, "
        "and NO BASELINE states against the frozen holdout baseline, now making zero-settled lanes explicit pre-evidence rather than a silent weak-result read, while also surfacing first-read and broader portfolio-review sample progress plus explicit ROI-coverage visibility when realized ROI only covers part of the settled sample, including non-positive cost and settled_ts timestamp-quality gaps, now source-matching the default 30 / 20 / 100 gate minimums to forward_evidence_scorecard.json decision_gate_minimums plus the no-BAQ-as-BEL real-money prerequisite, with a real CLI malformed-scorecard artifact proving conservative fallback outputs stay labeled as explicit CLI/fallback values rather than source-matched scorecard evidence, with Phase 8 shadow-lane first-read gate mapping using the 20-row promotion-review gate instead of the 30-row anchor-displacement gate, keeping the legacy Phase 7 rules-file display label as a legacy rules lane rather than a live lane while preserving the compatibility baseline key, and now publishing an explicit decision gate so hot/cold first reads do not masquerade as anchor-change, shadow-promotion, or real-money permission before the 100+ ROI-complete settled portfolio-review gate and settlement-quality checks, with the JSON, text, and markdown surfaces all pinned to fresh source-layer renders including recommendation-flow, ROI-fallback, and ROI cost-source detail with explicit cost-source counts, malformed/non-positive actual-cost settlement-quality gaps, and missing/placeholder/malformed settled_ts sample-gate gaps; "
        f"Phase 8 forward-check reads now also carry the Phase 8 review-floor caution so 20-row shadow reads are not promotion entitlements, while the source payload/text/markdown and direct validator report publish exact valid_evidence_scope={forward_check_source.FORWARD_CHECK_VALID_EVIDENCE_SCOPE} plus evidence-boundary contracts, and project-local fixture scratch metadata is published as a structured guardrail; forward check: frozen-baseline comparison surface, not standalone profit proof by itself"
    )
    child_checks = [
        {
            "check": "fixture_state_ladder_and_recommendation_flow_stay_covered",
            "status": "pass",
            "detail": "fixture cases still cover NO DATA, TOO EARLY, WITHIN EXPECTED NOISE, RUNNING COLD, RUNNING HOT, and NO BASELINE reads, while keeping recommendation-flow counts visible when bets, no-bets, and errors have already appeared",
        },
        {
            "check": "saved_fixture_and_live_surfaces_match_current_rebuilds",
            "status": "pass",
            "detail": "fixture forward_check JSON/text/markdown outputs plus the saved live forward_check text/markdown surfaces still have to match fresh source-layer rebuilds instead of drifting behind helper changes",
        },
        {
            "check": "zero_settled_and_partial_roi_coverage_gaps_stay_explicit",
            "status": "pass",
            "detail": "zero-settled lanes and rows marked settled without outcomes stay explicit pre-evidence, while partial return/cost/timestamp coverage remains visible instead of overstating realized ROI coverage or sample completeness",
        },
        {
            "check": "sample_progress_roi_fallback_and_missing_baseline_stay_pinned",
            "status": "pass",
            "detail": "first-read and broader portfolio-review milestones, expected-cost ROI fallback, and missing-baseline handling all stay pinned where the forward assessment is actually rendered",
        },
        {
            "check": "roi_cost_source_and_malformed_actual_cost_gaps_stay_visible",
            "status": "pass",
            "detail": "forward-check outputs now disclose how many ROI rows used actual_cost versus expected_cost fallback, and malformed actual_cost entries and missing/placeholder/malformed settled_ts values remain settlement-quality gaps instead of silently falling back to expected_cost or counting as ROI-complete sample rows",
        },
        {
            "check": "non_positive_cost_rows_do_not_advance_roi_complete_sample_gates",
            "status": "pass",
            "detail": "settled HIT/MISS rows with zero or negative effective cost remain settlement-quality gaps, so they do not advance first-read or portfolio-review ROI-complete sample counts or distort flat-ticket ROI denominators",
        },
        {
            "check": "decision_gate_prevents_first_read_overpromotion",
            "status": "pass",
            "detail": "NO DATA and sub-threshold samples stay no-strategy-change, 30-settled hot/cold/within-noise reads stay first-read-only, and 100-settled samples still require frozen-hierarchy plus concentration/payout checks before rule promotion or real-money decisions",
        },
        {
            "check": "forward_check_gates_are_sourced_from_scorecard_minimums",
            "status": "pass",
            "detail": "forward-check JSON, text, and markdown now expose that the default first-read and portfolio-review gates are loaded from forward_evidence_scorecard.json decision_gate_minimums: 30 anchor-displacement observations, 20 Phase 8 promotion-review observations, 100 real-money-discussion observations, and the no-BAQ-as-BEL real-money prerequisite; lowered gate floors fall back to those conservative historical floors, while boolean gate floors or missing no-BAQ prerequisites are treated as malformed source data instead of shrinking the sample gates, and fallback alignment reads are labeled as explicit CLI/fallback values rather than source-matched scorecard gates",
        },
        {
            "check": "malformed_scorecard_cli_fallback_artifact_stays_conservative",
            "status": "pass",
            "detail": "a real forward-check CLI run pointed at a malformed scorecard sidecar still writes JSON/text/markdown outputs with conservative 30/20/100 gates, fallback_used=true in markdown/JSON, no-BAQ-as-BEL preserved, and fallback/custom alignment text instead of source-matched scorecard wording",
        },
        {
            "check": "phase8_review_floor_caution_stays_visible",
            "status": "pass",
            "detail": "Phase 8 shadow forward-check surfaces carry the review-floor caution when the active first-read gate is phase8_promotion_review, so 20-row shadow reads are not displayed as promotion entitlements",
        },
        {
            "check": "legacy_phase7_rules_label_stays_paper_safe",
            "status": "pass",
            "detail": "phase7_live_rules.json still maps to the historical Phase 7 baseline key for compatibility, but renders as a legacy rules lane rather than a live lane so dormant BEL cannot be mistaken for the current-paper entrypoint",
        },
        {
            "check": "forward_check_explicitly_stays_baseline_comparison_not_profit_proof",
            "status": "pass",
            "detail": "the forward-check source payload/text/markdown and direct validator summary now publish visible valid_evidence_scope plus evidence-boundary wording that says plainly forward check is a frozen-baseline comparison for ROI-complete paper observations rather than a current-day scanner result, new forward evidence by itself, anchor-change evidence, Phase 8 promotion evidence, live-profitability proof, or real-money support",
        },
        {
            "check": "direct_validation_report_exposes_forward_check_valid_scope",
            "status": "pass",
            "detail": "the forward-check validation JSON, evidence-boundary metadata, summary read, and markdown evidence-boundary section now expose exact valid_evidence_scope=frozen-baseline comparison for ROI-complete paper observations so fixture cleanliness, saved-live parity, hot/cold reads, and scorecard-gate visibility cannot be copied as new forward evidence, settled ROI, promotion readiness, live profitability, or real-money support",
        },
        {
            "check": "fixture_scratch_metadata_published",
            "status": "pass",
            "detail": "the forward-check validator now publishes project-local fixture scratch metadata so parent rollups can verify isolated forward-check fixture hygiene without parsing markdown prose",
        },
    ]

    lines = [
        "# Paper-Trade Forward Check Validation",
        "",
        "This report validates `paper_trade_forward_check.py` directly against representative fixture cases under `out/status_validation/forward_check_fixture/`, while publishing the direct validator readout under `out/status_validation/paper_trade_forward_check/`.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Fixture root: `{FIXTURE_ROOT.relative_to(BASE)}`",
        f"- Direct report path: `{REPORT_MD.relative_to(BASE)}`",
        f"- Fixture scratch metadata: `{scratch['fixture_root_relative']}` is project-local and each fixture case root is cleared before setup.",
        "",
        "## Fixture cases",
        "",
        "| Case | Scenario | Result |",
        "|---|---|---|",
        *[
            f"| `{row['case']}` | {row['scenario']} | {row['assessment']} ({row['settled']} settled / {row['open']} open) |"
            for row in fixture_results
        ],
        f"| `{label_guardrail['case']}` | {label_guardrail['scenario']} | {label_guardrail['assessment']} (`{label_guardrail['lane_label']}`) |",
        "",
        "## Live current surfaces",
        "",
        *[
            f"- `{row['lane_dir']}` -> `{row['text_output']}` and `{row['md_output']}` ({row['assessment']}, {row['settled']} settled / {row['open']} open)"
            for row in live_surfaces
        ],
        "",
        "## Current Read",
        "",
        f"- Suite read: {suite_read}",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
        f"- valid_evidence_scope={forward_check_source.FORWARD_CHECK_VALID_EVIDENCE_SCOPE}",
        f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
        "- Boundary: forward-check validator cleanliness is frozen-baseline comparison metadata only, not a live paper-trade ledger, not a current-day scanner result, not settled ROI evidence, not live profitability, not promotion readiness, and not real-money evidence.",
        "- Non-goals: do not treat source-render parity, saved-live parity, scorecard-gate visibility, or hot/cold sub-threshold reads as new observations, rule-change permission, promotion support, BAQ/BEL substitution, live-profitability proof, or real-money support.",
        "",
        "## Validation result",
        "",
        "- The forward checker still has direct source-layer fixture coverage for its main frozen-baseline states instead of relying only on downstream lane-monitor or next-step tests.",
        "- Each fixture still requires `forward_check.json`, `forward_check.txt`, and `forward_check.md` to match fresh source-layer renders from `paper_trade_forward_check.py`, not just selected phrases inside those files.",
        "- The validator now also fails if any saved live `forward_check.txt` or `forward_check.md` surface under `out/daily_portfolio_runs/` drifts from the current source-layer rebuild.",
        "- This pins the honest hit-rate comparison contract, recommendation-flow summary, ROI fallback from expected cost, explicit ROI cost-source counts, malformed actual-cost and settled_ts settlement-quality gaps, explicit ROI-coverage visibility, zero-settled pre-evidence wording, source-matched scorecard decision-gate minimums, first-read plus broader review sample-progress milestones, decision-gate wording that blocks overpromotion from hot/cold first reads, source-level and direct-report valid_evidence_scope / evidence-boundary wording, and missing-baseline handling where the forward assessment is actually generated, both in fixtures and in the saved live lane surfaces.",
        f"- Gate fallback alignment fixture: `{gate_fallback_alignment['case']}` -> {gate_fallback_alignment['scenario']}.",
        "",
    ]
    payload = {
        "suite_status": "pass",
        "total_fixture_scenarios": len(fixture_results),
        "total_checks": len(results),
        "check_count": len(results),
        "child_check_count": len(child_checks),
        "child_checks": child_checks,
        "fixture_case_count": len(fixture_results),
        "live_surface_checks": len(live_surfaces),
        "results": results,
        "label_guardrail": label_guardrail,
        "gate_fallback_alignment_read": gate_fallback_alignment,
        "scratch": scratch,
        "valid_evidence_scope": forward_check_source.FORWARD_CHECK_VALID_EVIDENCE_SCOPE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "summary": {
            "suite_read": suite_read,
        },
        "fixture_root": str(FIXTURE_ROOT.relative_to(BASE)),
        "report_path": str(OUT_DIR.relative_to(BASE)),
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "fixture_root": str(FIXTURE_ROOT.relative_to(BASE)),
            "report_path": str(REPORT_MD.relative_to(BASE)),
        },
    }

    write_text(REPORT_MD, "\n".join(lines))
    write_text(REPORT_JSON, json.dumps(payload, indent=2) + "\n")

    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    for row in results:
        print(f"PASS {row['case']}: {row['assessment']} ({row['settled']} settled / {row['open']} open)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
