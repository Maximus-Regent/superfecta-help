#!/usr/bin/env python3
"""
Fixture-driven validation for paper_trade_lane_monitor.py.

Purpose:
- pin the compact lane-monitor surface directly at the source layer
- keep forward-assessment carry-through plus settlement-queue messaging reproducible
- validate the real CLI against isolated fixtures without touching live ledgers
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import paper_trade_lane_monitor as lane_monitor_source

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "paper_trade_lane_monitor.py"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "lane_monitor_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_lane_monitor"
REPORT_MD = OUT_DIR / "paper_trade_lane_monitor_validation.md"
REPORT_JSON = OUT_DIR / "paper_trade_lane_monitor_validation.json"
LIVE_RUNS_ROOT = BASE / "out" / "daily_portfolio_runs"
REBUILD_COMMAND = "python3 validate_paper_trade_lane_monitor.py"
FROZEN_EVAL = BASE / "frozen_portfolio_eval_summary.csv"
DEFAULT_RULES = BASE / "phase7_current_paper_rules.json"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade lane-monitor validator",
    "valid_evidence_scope": lane_monitor_source.LANE_MONITOR_VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "isolated lane-monitor fixture ledgers",
        "saved live lane-monitor source-layer rebuilds",
        "paper_trade_lane_monitor.py",
        "forward_evidence_scorecard.json decision_gate_minimums",
    ],
    "valid_use": "compact per-lane forward-observation and settlement-queue validation",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "lane_monitor_validator_passes_are_compact_observation_metadata_only": True,
    "non_goals": [
        "do not treat lane-monitor cleanliness as ROI-complete observations",
        "do not treat open settlement queues as sample progress",
        "do not treat scorecard-gate visibility as promotion readiness",
        "do not promote OP_REFINED_K7 or Phase 8 from lane-monitor review-floor text",
        "do not substitute BAQ for BEL",
        "do not treat lane-monitor validation as real-money evidence",
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


def build_fixture_scratch_metadata() -> dict[str, Any]:
    return {
        "fixture_root": str(FIXTURE_ROOT),
        "fixture_root_relative": str(FIXTURE_ROOT.relative_to(BASE)),
        "fixture_root_is_project_local": FIXTURE_ROOT.is_relative_to(BASE),
        "case_roots_cleared_by_setup_case": True,
        "evidence_boundary": (
            "lane-monitor fixture scratch metadata is compact-observation reproducibility context only, "
            "not a live paper-trade ledger, settled ROI, promotion readiness, live profitability, bankroll guidance, "
            "or real-money evidence"
        ),
    }


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
        "scan_ts": f"2026-05-02T1{idx % 10}:00:00",
        "rule_id": rule_id,
        "track": track,
        "card_name": "Oaklawn Park" if track == "OP" else "Churchill Downs",
        "race_number": race_number,
        "race_id": f"{track}-2026-05-02-R{race_number}",
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
                   actual_return: float | None = None, *, actual_cost_override: str | None = None,
                   settled_ts: str | None = None) -> dict[str, Any]:
    cost = float(signal["estimated_cost"])
    returned = actual_return if actual_return is not None else ""
    if actual_cost_override is not None:
        actual_cost = actual_cost_override
    else:
        actual_cost = f"{cost:.2f}" if settlement_status == "settled" and actual_return is not None else ""
    profit = ""
    if actual_return is not None and actual_cost:
        try:
            profit = f"{actual_return - float(actual_cost):.2f}"
        except ValueError:
            profit = ""
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
        "actual_return": f"{returned:.2f}" if isinstance(returned, float) else returned,
        "actual_profit": profit,
        "settled_ts": ("2026-05-02T19:30:00" if settled_ts is None else settled_ts) if settlement_status == "settled" else "",
        "notes": "fixture",
    }


def setup_case(case_name: str, rules_name: str, rules_json: dict[str, Any], signals: list[dict[str, Any]],
               settlements: list[dict[str, Any]]) -> tuple[Path, Path, Path, Path, Path]:
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
    write_csv(recs_path, RECOMMENDATION_FIELDS, [])
    write_csv(settlements_path, SETTLEMENT_FIELDS, settlements)
    write_json(rules_path, rules_json)

    return case_root, signals_path, recs_path, settlements_path, rules_path


def assert_contains(text: str, needle: str, case_name: str) -> None:
    if needle not in text:
        raise AssertionError(f"{case_name}: expected to find {needle!r}")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def pass_check(check: str, detail: str) -> dict[str, str]:
    return {"check": check, "status": "pass", "detail": detail}


def require_positive_non_bool_int(value: Any, *, source_name: str, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, source_name: str, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise AssertionError(f"{source_name} {field_name} must be a string list")
    return value


def assert_scorecard_gate_source(payload: dict[str, Any], case_name: str) -> None:
    gate_minimums = payload["decision_gate_minimums"]
    forward_gate_minimums = payload["forward"]["decision_gate_minimums"]
    if gate_minimums != forward_gate_minimums:
        raise AssertionError(f"{case_name}: top-level lane-monitor gate source drifted from the carried forward-check gate source")
    active_gate = str(gate_minimums.get("active_first_read_gate") or "")
    expected_active = {
        "anchor_displacement": (
            "anchor_displacement_min_roi_complete_settled_observations",
            30,
        ),
        "phase8_promotion_review": (
            "phase8_promotion_review_min_roi_complete_settled_observations",
            20,
        ),
    }
    if active_gate not in expected_active:
        raise AssertionError(f"{case_name}: unexpected active first-read gate {active_gate!r}")
    active_gate_key, active_gate_value = expected_active[active_gate]
    expected = {
        "source_path": "forward_evidence_scorecard.json",
        "source_loaded": True,
        "fallback_used": False,
        "anchor_displacement_min_roi_complete_settled_observations": 30,
        "phase8_promotion_review_min_roi_complete_settled_observations": 20,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": 100,
        "real_money_discussion_also_requires": [
            "positive paper ROI",
            "concentration checks",
            "payout-distribution sanity checks",
            "no BAQ-as-BEL substitution",
        ],
        "real_money_no_baq_as_bel_required": True,
        "active_first_read_gate": active_gate,
        "active_first_read_gate_key": active_gate_key,
        "active_min_settled": active_gate_value,
        "active_portfolio_review_settled": 100,
        "cli_overrides": {},
    }
    for key, expected_value in expected.items():
        if gate_minimums.get(key) != expected_value:
            raise AssertionError(
                f"{case_name}: expected lane-monitor gate minimum {key}={expected_value!r}, got {gate_minimums.get(key)!r}"
            )
    expected_alignment = f"source-matched to forward_evidence_scorecard.json decision_gate_minimums using {active_gate} for this lane"
    if expected_alignment not in gate_minimums["alignment_read"]:
        raise AssertionError(f"{case_name}: lane-monitor gate source alignment read drifted: {gate_minimums!r}")


def assert_lane_monitor_evidence_boundary(payload: dict[str, Any], case_name: str) -> None:
    boundary = payload.get("evidence_boundary")
    if not isinstance(boundary, dict):
        raise AssertionError(f"{case_name}: lane monitor payload is missing evidence_boundary")
    expected = {
        "artifact_role": "paper-trade lane monitor",
        "valid_use": "compact per-lane forward-observation and settlement-queue review",
        "not_new_forward_evidence": True,
        "not_current_day_scanner_result": True,
        "not_settled_roi_evidence": True,
        "not_live_profitability_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_real_money_evidence": True,
    }
    for key, value in expected.items():
        if boundary.get(key) != value:
            raise AssertionError(f"{case_name}: lane monitor evidence boundary {key} drifted to {boundary.get(key)!r}")
    if payload.get("valid_evidence_scope") != expected["valid_use"]:
        raise AssertionError(f"{case_name}: lane monitor valid_evidence_scope drifted")
    boundary_text = str(payload.get("evidence_boundary_text") or "")
    for phrase in [
        "compact forward-observation and settlement-queue metadata only",
        "not a current-day scanner result",
        "not settled ROI evidence",
        "not promotion readiness",
        "not live profitability evidence",
        "not real-money support",
    ]:
        if phrase not in boundary_text:
            raise AssertionError(f"{case_name}: lane monitor boundary text no longer carries {phrase!r}")
    non_goals = boundary.get("non_goals")
    if not isinstance(non_goals, list) or not all(isinstance(item, str) for item in non_goals):
        raise AssertionError(f"{case_name}: lane monitor evidence boundary non_goals must be a string list")
    for phrase in [
        "open settlement queues as sample progress",
        "scorecard-gate visibility as promotion readiness",
        "live profitability or real-money support",
    ]:
        if not any(phrase in item for item in non_goals):
            raise AssertionError(f"{case_name}: lane monitor evidence boundary non_goals lost {phrase!r}")


def read_scorecard_gate_minimums(scorecard_json: Path = SCORECARD_JSON) -> dict[str, Any]:
    source_name = display_path(scorecard_json)
    payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
    gates = payload.get("decision_gate_minimums")
    if not isinstance(gates, dict):
        raise AssertionError(f"{source_name} is missing decision_gate_minimums")
    anchor = gates.get("anchor_displacement")
    phase8 = gates.get("phase8_promotion_review")
    real_money = gates.get("real_money_discussion")
    if not isinstance(anchor, dict) or not isinstance(phase8, dict) or not isinstance(real_money, dict):
        raise AssertionError(f"{source_name} decision_gate_minimums is incomplete")
    anchor_min = require_positive_non_bool_int(
        anchor.get("min_roi_complete_settled_observations"),
        source_name=source_name,
        field_name="decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
    )
    phase8_min = require_positive_non_bool_int(
        phase8.get("min_roi_complete_settled_observations"),
        source_name=source_name,
        field_name="decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
    )
    real_money_min = require_positive_non_bool_int(
        real_money.get("min_total_settled_observations_with_usable_roi"),
        source_name=source_name,
        field_name="decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
    )
    real_money_requires = require_string_list(
        real_money.get("also_requires"),
        source_name=source_name,
        field_name="decision_gate_minimums.real_money_discussion.also_requires",
    )
    if NO_BAQ_AS_BEL_PREREQUISITE not in real_money_requires:
        raise AssertionError(
            f"{source_name} decision_gate_minimums.real_money_discussion.also_requires "
            f"must include {NO_BAQ_AS_BEL_PREREQUISITE}"
        )
    return {
        "source": "forward_evidence_scorecard.json",
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_also_requires": real_money_requires,
        "real_money_no_baq_as_bel_required": True,
        "evidence_boundary": (
            "lane-monitor fixture cleanliness, saved-live rebuild cleanliness, open queues, "
            "incomplete-settlement repair lines, scorecard-gate visibility, and Phase 8 review-floor "
            "cautions do not count toward anchor-displacement, Phase 8 promotion-review, or real-money discussion gates"
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--fixture-root", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def configure_output_paths(fixture_root: Path, out_dir: Path) -> None:
    global FIXTURE_ROOT, OUT_DIR, REPORT_MD, REPORT_JSON
    FIXTURE_ROOT = fixture_root
    OUT_DIR = out_dir
    REPORT_MD = OUT_DIR / "paper_trade_lane_monitor_validation.md"
    REPORT_JSON = OUT_DIR / "paper_trade_lane_monitor_validation.json"


def assert_scorecard_failure_before_artifacts(
    *,
    scorecard_json: Path,
    mutation: Any,
    expected_stderr: str,
    check_name: str,
    detail: str,
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix=f"{check_name}_") as tmp:
        tmpdir = Path(tmp)
        bad_scorecard = tmpdir / "forward_evidence_scorecard.json"
        bad_payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
        mutation(bad_payload)
        bad_scorecard.write_text(json.dumps(bad_payload, indent=2) + "\n", encoding="utf-8")

        fixture_root = tmpdir / "fixture_root"
        out_dir = tmpdir / "nested" / "report_artifacts"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(bad_scorecard),
                "--fixture-root",
                str(fixture_root),
                "--out-dir",
                str(out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if result.returncode == 0:
            raise AssertionError(f"{check_name}: malformed scorecard unexpectedly passed")
        if expected_stderr not in result.stderr:
            raise AssertionError(
                f"{check_name}: failure stderr no longer explains the malformed scorecard gate\n"
                f"stderr={result.stderr}"
            )
        if fixture_root.exists() or out_dir.exists():
            raise AssertionError(f"{check_name}: malformed scorecard created fixture/report artifacts")
    return pass_check(check_name, detail)


def scorecard_no_artifact_guardrails(scorecard_json: Path) -> list[dict[str, str]]:
    return [
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["anchor_displacement"].__setitem__(
                "min_roi_complete_settled_observations",
                True,
            ),
            expected_stderr=(
                "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check_name="scorecard_boolean_gate_floor_fails_before_lane_monitor_artifacts",
            detail=(
                "a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before "
                "the lane-monitor validator creates fixture roots or report artifacts"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["phase8_promotion_review"].__setitem__(
                "min_roi_complete_settled_observations",
                0,
            ),
            expected_stderr=(
                "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check_name="scorecard_nonpositive_phase8_gate_floor_fails_before_lane_monitor_artifacts",
            detail=(
                "a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json "
                "fails before the lane-monitor validator creates fixture roots or report artifacts"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                "min_total_settled_observations_with_usable_roi",
                0,
            ),
            expected_stderr=(
                "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi "
                "must be a positive non-boolean integer"
            ),
            check_name="scorecard_nonpositive_real_money_gate_floor_fails_before_lane_monitor_artifacts",
            detail=(
                "a non-positive real-money discussion floor in forward_evidence_scorecard.json "
                "fails before the lane-monitor validator creates fixture roots or report artifacts"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                "also_requires",
                [
                    item
                    for item in payload["decision_gate_minimums"]["real_money_discussion"].get(
                        "also_requires",
                        [],
                    )
                    if item != NO_BAQ_AS_BEL_PREREQUISITE
                ],
            ),
            expected_stderr=(
                "decision_gate_minimums.real_money_discussion.also_requires must include "
                f"{NO_BAQ_AS_BEL_PREREQUISITE}"
            ),
            check_name="scorecard_missing_no_baq_fails_before_lane_monitor_artifacts",
            detail=(
                "a scorecard real-money gate that drops the no BAQ-as-BEL prerequisite fails before "
                "the lane-monitor validator creates fixture roots or report artifacts"
            ),
        ),
    ]


SETTLED_SAMPLE = [signal_row(i) for i in range(1, 31)]
DECISION_SETTLEMENTS = [
    settlement_row(signal, "settled", "HIT" if idx <= 8 else "MISS", 120.0 if idx <= 8 else 0.0)
    for idx, signal in enumerate(SETTLED_SAMPLE, start=1)
]

TRUNCATION_SIGNALS = [signal_row(i) for i in range(1, 7)]
TRUNCATION_STATUSES = ["open", "pending", "unsettled", "todo", "", "open"]
TRUNCATION_SETTLEMENTS = [
    settlement_row(signal, status, "")
    for signal, status in zip(TRUNCATION_SIGNALS, TRUNCATION_STATUSES)
]

CUSTOM_SIGNALS = [signal_row(1, rule_id="TEST_RULE_X", track="OP"), signal_row(2, rule_id="TEST_RULE_X", track="OP")]
CUSTOM_SETTLEMENTS = [
    settlement_row(CUSTOM_SIGNALS[0], "settled", "HIT", 120.0),
    settlement_row(CUSTOM_SIGNALS[1], "settled", "MISS", 0.0),
]

CASES: list[dict[str, Any]] = [
    {
        "name": "case_open_settlement_queue",
        "scenario": "open settlement rows stay visible alongside the forward read",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": [signal_row(1), signal_row(2), signal_row(3)],
        "settlements": [
            settlement_row(signal_row(1), "settled", "HIT", 120.0),
            settlement_row(signal_row(2), "open", ""),
            settlement_row(signal_row(3), "pending", ""),
        ],
        "max_open": 5,
        "assessment": "TOO EARLY",
        "note": "Only 1 ROI-complete settled race(s) (1 outcome-settled).",
        "open_count": 2,
        "shown": 2,
        "text_needles": [
            "- Sample progress: 1/30 ROI-complete settled (29 more to first statistical read)",
            "- Broader review progress: 1/100 ROI-complete settled (99 more to portfolio review gate)",
            "- Pending settlement rows: 2",
            "op_durable_k7_002",
            "op_durable_k7_003",
            "- Settlement command templates:",
            "template only; replace placeholders only after actual result/payout evidence exists.",
            "op_durable_k7_002: python3 paper_trade_settlement_helper.py settle --signal-key op_durable_k7_002 --outcome HIT_OR_MISS --actual-return ACTUAL_RETURN_DOLLARS --settled-ts ISO_SETTLED_TS",
        ],
        "md_needles": [
            "- Sample progress: `1/30` ROI-complete settled (29 more to first statistical read)",
            "- Broader review progress: `1/100` ROI-complete settled (99 more to portfolio review gate)",
            "- Open settlement rows: `2`",
            "### Settlement Command Templates",
            "template only; replace placeholders only after actual result/payout evidence exists.",
            "`op_durable_k7_002`: `python3 paper_trade_settlement_helper.py settle --signal-key op_durable_k7_002 --outcome HIT_OR_MISS --actual-return ACTUAL_RETURN_DOLLARS --settled-ts ISO_SETTLED_TS`",
            "Use the row-specific `paper_trade_settlement_helper.py settle` template above only after actual result/payout evidence exists",
        ],
    },
    {
        "name": "case_incomplete_settlement_outcome",
        "scenario": "rows marked settled without an outcome stay visible as incomplete settlement data instead of disappearing into a quiet lane",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": [signal_row(1)],
        "settlements": [
            settlement_row(signal_row(1), "settled", ""),
        ],
        "max_open": 5,
        "assessment": "NO DATA",
        "note": "No settled races yet, so this lane has no forward evidence one way or the other.",
        "open_count": 0,
        "shown": 0,
        "incomplete_count": 1,
        "incomplete_shown": 1,
        "text_needles": [
            "- Settled rows missing outcome: 1",
            "- Incomplete settled rows:",
            "op_durable_k7_001",
        ],
        "md_needles": [
            "- Settled rows missing outcome: `1`",
            "### Incomplete Settled Rows",
            "forward metrics exclude them until the ledger is completed",
            "Run `paper_trade_settlement_helper.py settle ...` for the incomplete settled rows above",
        ],
    },
    {
        "name": "case_partial_roi_coverage_gap",
        "scenario": "settled outcomes with missing return values stay visible as ROI-coverage gaps in the compact lane monitor",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": [signal_row(i) for i in range(1, 6)],
        "settlements": [
            settlement_row(signal_row(1), "settled", "HIT", 96.0),
            settlement_row(signal_row(2), "settled", "MISS", 0.0),
            settlement_row(signal_row(3), "settled", "MISS", None),
            settlement_row(signal_row(4), "settled", "MISS", None),
            settlement_row(signal_row(5), "settled", "MISS", None),
        ],
        "max_open": 5,
        "assessment": "TOO EARLY",
        "note": "Only 2 ROI-complete settled race(s) (5 outcome-settled).",
        "open_count": 0,
        "shown": 0,
        "roi_gap_count": 3,
        "roi_gap_shown": 3,
        "text_needles": [
            "- ROI coverage: 2/5 settled races are ROI-complete (3 still missing return/cost/timestamp coverage)",
            "- Settled rows missing ROI-complete coverage: 3",
            "- Settled rows missing ROI-complete coverage:",
        ],
        "md_needles": [
            "- ROI coverage: `2/5` settled races are ROI-complete (`3` still missing return/cost/timestamp coverage)",
            "- Settled rows missing ROI-complete coverage: `3`",
            "### Settled Rows Missing ROI-Complete Coverage",
            "Fill in `actual_return`, `actual_cost` if needed, and an actual ISO `settled_ts`",
        ],
    },
    {
        "name": "case_malformed_actual_cost_roi_gap",
        "scenario": "settled outcomes with malformed actual_cost stay visible as ROI-coverage gaps instead of falling back silently to expected_cost",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": [signal_row(i) for i in range(1, 4)],
        "settlements": [
            settlement_row(signal_row(1), "settled", "HIT", 96.0),
            settlement_row(signal_row(2), "settled", "MISS", 0.0, actual_cost_override="bad-cost"),
            settlement_row(signal_row(3), "settled", "MISS", 0.0),
        ],
        "max_open": 5,
        "assessment": "TOO EARLY",
        "note": "Only 2 ROI-complete settled race(s) (3 outcome-settled).",
        "open_count": 0,
        "shown": 0,
        "roi_gap_count": 1,
        "roi_gap_shown": 1,
        "text_needles": [
            "- ROI coverage: 2/3 settled races are ROI-complete (1 still missing return/cost/timestamp coverage)",
            "- Settled rows missing ROI-complete coverage: 1",
            "op_durable_k7_002",
            "actual_return 0.00 | actual_cost bad-cost | malformed actual_cost",
        ],
        "md_needles": [
            "- ROI coverage: `2/3` settled races are ROI-complete (`1` still missing return/cost/timestamp coverage)",
            "- Settled rows missing ROI-complete coverage: `1`",
            "These rows have settled outcomes but still cannot contribute to realized ROI or sample gates because return/cost/timestamp coverage is incomplete or malformed.",
            "| op_durable_k7_002 | OP_DURABLE_K7 | OP | 7 | OP-2026-05-02-R7 | 24.00 | 0.00 | bad-cost | malformed actual_cost |",
        ],
    },
    {
        "name": "case_non_positive_cost_roi_gap",
        "scenario": "settled outcomes with zero actual_cost or zero expected_cost stay visible as ROI-coverage gaps instead of advancing sample gates",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": [signal_row(1), signal_row(2), signal_row(3, estimated_cost=0.0)],
        "settlements": [
            settlement_row(signal_row(1), "settled", "HIT", 96.0),
            settlement_row(signal_row(2), "settled", "MISS", 0.0, actual_cost_override="0.00"),
            settlement_row(signal_row(3, estimated_cost=0.0), "settled", "MISS", 0.0, actual_cost_override=""),
        ],
        "max_open": 5,
        "assessment": "TOO EARLY",
        "note": "Only 1 ROI-complete settled race(s) (3 outcome-settled).",
        "open_count": 0,
        "shown": 0,
        "roi_gap_count": 2,
        "roi_gap_shown": 2,
        "text_needles": [
            "- ROI coverage: 1/3 settled races are ROI-complete (2 still missing return/cost/timestamp coverage)",
            "- Sample progress: 1/30 ROI-complete settled (29 more to first statistical read)",
            "- Settled rows missing ROI-complete coverage: 2",
            "actual_return 0.00 | actual_cost 0.00 | non-positive actual_cost",
            "expected cost 0.00 | actual_return 0.00 | actual_cost blank | non-positive expected_cost",
        ],
        "md_needles": [
            "- ROI coverage: `1/3` settled races are ROI-complete (`2` still missing return/cost/timestamp coverage)",
            "- Sample progress: `1/30` ROI-complete settled (29 more to first statistical read)",
            "- Settled rows missing ROI-complete coverage: `2`",
            "These rows have settled outcomes but still cannot contribute to realized ROI or sample gates because return/cost/timestamp coverage is incomplete or malformed.",
            "| op_durable_k7_002 | OP_DURABLE_K7 | OP | 7 | OP-2026-05-02-R7 | 24.00 | 0.00 | 0.00 | non-positive actual_cost |",
            "| op_durable_k7_003 | OP_DURABLE_K7 | OP | 7 | OP-2026-05-02-R7 | 0.00 | 0.00 | blank | non-positive expected_cost |",
        ],
    },
    {
        "name": "case_settled_timestamp_gap_roi_complete_queue",
        "scenario": "settled rows with return/cost values but missing, placeholder, or malformed settled_ts stay visible as ROI-complete coverage gaps",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": [signal_row(i) for i in range(1, 4)],
        "settlements": [
            settlement_row(signal_row(1), "settled", "HIT", 96.0, settled_ts=""),
            settlement_row(signal_row(2), "settled", "MISS", 0.0, settled_ts="<SETTLED_TS>"),
            settlement_row(signal_row(3), "settled", "MISS", 0.0, settled_ts="not-a-timestamp"),
        ],
        "max_open": 5,
        "assessment": "TOO EARLY",
        "note": "Only 0 ROI-complete settled race(s) (3 outcome-settled).",
        "open_count": 0,
        "shown": 0,
        "roi_gap_count": 3,
        "roi_gap_shown": 3,
        "text_needles": [
            "- ROI coverage: 0/3 settled races are ROI-complete (3 still missing return/cost/timestamp coverage)",
            "- Sample progress: 0/30 ROI-complete settled (30 more to first statistical read)",
            "- Settled rows missing ROI-complete coverage: 3",
            "actual_return 96.00 | actual_cost 24.00 | missing settled_ts",
            "actual_return 0.00 | actual_cost 24.00 | placeholder settled_ts",
            "actual_return 0.00 | actual_cost 24.00 | malformed settled_ts",
        ],
        "md_needles": [
            "- ROI coverage: `0/3` settled races are ROI-complete (`3` still missing return/cost/timestamp coverage)",
            "- Sample progress: `0/30` ROI-complete settled (30 more to first statistical read)",
            "- Settled rows missing ROI-complete coverage: `3`",
            "### Settled Rows Missing ROI-Complete Coverage",
            "These rows have settled outcomes but still cannot contribute to realized ROI or sample gates because return/cost/timestamp coverage is incomplete or malformed.",
            "| op_durable_k7_001 | OP_DURABLE_K7 | OP | 7 | OP-2026-05-02-R7 | 24.00 | 96.00 | 24.00 | missing settled_ts |",
            "| op_durable_k7_002 | OP_DURABLE_K7 | OP | 7 | OP-2026-05-02-R7 | 24.00 | 0.00 | 24.00 | placeholder settled_ts |",
            "| op_durable_k7_003 | OP_DURABLE_K7 | OP | 7 | OP-2026-05-02-R7 | 24.00 | 0.00 | 24.00 | malformed settled_ts |",
        ],
    },
    {
        "name": "case_queue_truncation",
        "scenario": "long open queues truncate cleanly without hiding the queue count",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": TRUNCATION_SIGNALS,
        "settlements": TRUNCATION_SETTLEMENTS,
        "max_open": 3,
        "assessment": "NO DATA",
        "note": "No settled races yet, so this lane has no forward evidence one way or the other.",
        "open_count": 6,
        "shown": 3,
        "text_needles": [
            "- Pending settlement rows: 6",
            "... plus 3 more open row(s)",
        ],
        "md_needles": [
            "- Open settlement rows: `6`",
            "- Showing first `3` open row(s).",
        ],
    },
    {
        "name": "case_no_pending_no_data",
        "scenario": "zero-settled lanes still show the frozen baseline and no-pending note honestly",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": [],
        "settlements": [],
        "max_open": 5,
        "assessment": "NO DATA",
        "note": "No settled races yet, so this lane has no forward evidence one way or the other.",
        "open_count": 0,
        "shown": 0,
        "text_needles": [
            "- Sample progress: 0/30 ROI-complete settled (30 more to first statistical read)",
            "- Broader review progress: 0/100 ROI-complete settled (100 more to portfolio review gate)",
            "- Decision gate: No strategy change: this is still pre-evidence with 0 settled races.",
            "- Pending settlement rows: 0",
            "- Frozen baseline: 27.43% hit rate, +38.68% ROI on 175 holdout races",
        ],
        "md_needles": [
            "- Sample progress: `0/30` ROI-complete settled (30 more to first statistical read)",
            "- Broader review progress: `0/100` ROI-complete settled (100 more to portfolio review gate)",
            "- Decision gate: No strategy change: this is still pre-evidence with 0 settled races.",
            "- No pending settlement rows.",
            "No manual settlement entry is pending right now.",
        ],
    },
    {
        "name": "case_phase8_review_floor_caution",
        "scenario": "Phase 8 shadow lane monitors carry the 20-row review-floor caution instead of implying promotion readiness",
        "rules_name": "phase8_shadow_rules.json",
        "rules_json": rules_payload(["OP_REFINED_K7", "AQU_K9", "SA_K9", "KEE_K9", "CD_REFINED_K9", "DMR_FALL_K7"]),
        "signals": [],
        "settlements": [],
        "max_open": 5,
        "assessment": "NO DATA",
        "note": "No settled races yet, so this lane has no forward evidence one way or the other.",
        "open_count": 0,
        "shown": 0,
        "text_needles": [
            "- Sample progress: 0/20 ROI-complete settled (20 more to first statistical read)",
            "- Broader review progress: 0/100 ROI-complete settled (100 more to portfolio review gate)",
            "- Active gates: first_read=20; portfolio_review=100. lane-monitor sample milestones are source-matched to forward_evidence_scorecard.json decision_gate_minimums using phase8_promotion_review for this lane.",
            "- Decision-gate caution: Phase 8 shadow first-read status is a review floor, not a promotion entitlement; lane totals alone do not promote any Phase 8 pocket, scorecard tiers remain binding, and negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion.",
        ],
        "md_needles": [
            "- Sample progress: `0/20` ROI-complete settled (20 more to first statistical read)",
            "- Broader review progress: `0/100` ROI-complete settled (100 more to portfolio review gate)",
            "- Active lane-monitor gates: first_read=20; portfolio_review=100. lane-monitor sample milestones are source-matched to forward_evidence_scorecard.json decision_gate_minimums using phase8_promotion_review for this lane.",
            "- Decision-gate caution: Phase 8 shadow first-read status is a review floor, not a promotion entitlement; lane totals alone do not promote any Phase 8 pocket, scorecard tiers remain binding, and negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion.",
        ],
    },
    {
        "name": "case_no_baseline_custom_rules",
        "scenario": "custom lanes without a frozen portfolio row say baseline-missing instead of guessing",
        "rules_name": "custom_lane_rules.json",
        "rules_json": rules_payload(["TEST_RULE_X"]),
        "signals": CUSTOM_SIGNALS,
        "settlements": CUSTOM_SETTLEMENTS,
        "max_open": 5,
        "assessment": "NO BASELINE",
        "note": "Lane is missing a frozen portfolio baseline.",
        "open_count": 0,
        "shown": 0,
        "text_needles": [
            "custom lane rules monitor",
            "- Frozen baseline: missing",
        ],
        "md_needles": [
            "Lane: **custom lane rules**",
            "- Frozen baseline: `missing`",
        ],
    },
    {
        "name": "case_decision_grade_with_roi",
        "scenario": "decision-grade samples carry forward assessment and realized ROI through the compact monitor",
        "rules_name": "phase7_current_paper_rules.json",
        "rules_json": rules_payload(["OP_DURABLE_K7", "CD_CORE_K8"]),
        "signals": SETTLED_SAMPLE,
        "settlements": DECISION_SETTLEMENTS,
        "max_open": 5,
        "assessment": "WITHIN EXPECTED NOISE",
        "note": "Observed hit rate sits inside the approximate 2-sigma band",
        "open_count": 0,
        "shown": 0,
        "text_needles": [
            "- Observed flat-ticket ROI: +33.33% on 30 ROI-complete settled race(s)",
            "- Sample progress: 30/30 ROI-complete settled (first statistical read threshold reached)",
            "- Broader review progress: 30/100 ROI-complete settled (70 more to portfolio review gate)",
            "- Decision gate: First read only: 30/100 ROI-complete settled race(s) toward the broader portfolio review gate.",
            "- Pending settlement rows: 0",
        ],
        "md_needles": [
            "- Assessment: **WITHIN EXPECTED NOISE**",
            "- Observed flat-ticket ROI: `+33.33%` on `30` ROI-complete settled race(s) with return/cost/timestamp coverage",
            "- Sample progress: `30/30` ROI-complete settled; first statistical read threshold reached",
            "- Broader review progress: `30/100` ROI-complete settled (70 more to portfolio review gate)",
            "- Decision gate: First read only: 30/100 ROI-complete settled race(s) toward the broader portfolio review gate.",
            "No manual settlement entry is pending right now.",
        ],
    },
]


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_root, signals_path, recs_path, settlements_path, rules_path = setup_case(
        case_name=case["name"],
        rules_name=case["rules_name"],
        rules_json=case["rules_json"],
        signals=case["signals"],
        settlements=case["settlements"],
    )

    json_output = case_root / "lane_monitor.json"
    text_output = case_root / "lane_monitor.txt"
    md_output = case_root / "lane_monitor.md"

    common = [
        sys.executable,
        str(SCRIPT),
        "--signals-ledger", str(signals_path),
        "--recommendation-ledger", str(recs_path),
        "--settlement-ledger", str(settlements_path),
        "--rules", str(rules_path),
        "--frozen-eval", str(FROZEN_EVAL),
        "--max-open", str(case["max_open"]),
    ]

    json_result = subprocess.run(common + ["--format", "json", "--output", str(json_output)], cwd=BASE, capture_output=True, text=True, check=True)
    payload = json.loads(json_result.stdout)
    text_result = subprocess.run(common + ["--format", "text", "--output", str(text_output)], cwd=BASE, capture_output=True, text=True, check=True)
    md_result = subprocess.run(common + ["--format", "md", "--output", str(md_output)], cwd=BASE, capture_output=True, text=True, check=True)

    expected_json = json.dumps(payload, indent=2) + "\n"
    expected_text = lane_monitor_source.render_text(payload)
    expected_md = lane_monitor_source.render_md(payload) + "\n"

    if json_result.stdout != expected_json or json_output.read_text(encoding="utf-8") != expected_json:
        raise AssertionError(f"{case['name']}: lane_monitor.json no longer matches a fresh render from paper_trade_lane_monitor.py")
    if text_result.stdout != expected_text or text_output.read_text(encoding="utf-8") != expected_text:
        raise AssertionError(f"{case['name']}: lane_monitor.txt no longer matches a fresh render from paper_trade_lane_monitor.py")
    if md_result.stdout != expected_md or md_output.read_text(encoding="utf-8") != expected_md:
        raise AssertionError(f"{case['name']}: lane_monitor.md no longer matches a fresh render from paper_trade_lane_monitor.py")

    if payload["forward"]["portfolio_assessment"] != case["assessment"]:
        raise AssertionError(
            f"{case['name']}: expected assessment {case['assessment']!r}, got {payload['forward']['portfolio_assessment']!r}"
        )
    assert_contains(payload["forward"]["portfolio_note"], case["note"], case["name"])
    assert_contains(payload["forward"]["decision_gate"], "settled", case["name"])
    assert_scorecard_gate_source(payload, case["name"])
    assert_lane_monitor_evidence_boundary(payload, case["name"])
    if payload["open_settlements"]["count"] != case["open_count"]:
        raise AssertionError(
            f"{case['name']}: expected open count {case['open_count']}, got {payload['open_settlements']['count']}"
        )
    if payload["open_settlements"]["shown"] != case["shown"]:
        raise AssertionError(
            f"{case['name']}: expected shown count {case['shown']}, got {payload['open_settlements']['shown']}"
        )
    if len(payload["open_settlements"]["rows"]) != case["shown"]:
        raise AssertionError(
            f"{case['name']}: expected {case['shown']} shown row(s), got {len(payload['open_settlements']['rows'])}"
        )
    expected_incomplete_count = case.get("incomplete_count", 0)
    expected_incomplete_shown = case.get("incomplete_shown", 0)
    expected_roi_gap_count = case.get("roi_gap_count", 0)
    expected_roi_gap_shown = case.get("roi_gap_shown", 0)
    if payload["incomplete_settlements"]["count"] != expected_incomplete_count:
        raise AssertionError(
            f"{case['name']}: expected incomplete count {expected_incomplete_count}, got {payload['incomplete_settlements']['count']}"
        )
    if payload["incomplete_settlements"]["shown"] != expected_incomplete_shown:
        raise AssertionError(
            f"{case['name']}: expected incomplete shown count {expected_incomplete_shown}, got {payload['incomplete_settlements']['shown']}"
        )
    if len(payload["incomplete_settlements"]["rows"]) != expected_incomplete_shown:
        raise AssertionError(
            f"{case['name']}: expected {expected_incomplete_shown} incomplete shown row(s), got {len(payload['incomplete_settlements']['rows'])}"
        )
    if payload["roi_gap_settlements"]["count"] != expected_roi_gap_count:
        raise AssertionError(
            f"{case['name']}: expected ROI-gap count {expected_roi_gap_count}, got {payload['roi_gap_settlements']['count']}"
        )
    if payload["roi_gap_settlements"]["shown"] != expected_roi_gap_shown:
        raise AssertionError(
            f"{case['name']}: expected ROI-gap shown count {expected_roi_gap_shown}, got {payload['roi_gap_settlements']['shown']}"
        )
    if len(payload["roi_gap_settlements"]["rows"]) != expected_roi_gap_shown:
        raise AssertionError(
            f"{case['name']}: expected {expected_roi_gap_shown} ROI-gap row(s), got {len(payload['roi_gap_settlements']['rows'])}"
        )

    text = text_output.read_text(encoding="utf-8")
    md = md_output.read_text(encoding="utf-8")
    active_gate = str(payload["decision_gate_minimums"]["active_first_read_gate"])
    active_first_read = int(payload["forward"]["min_settled"])
    alignment = f"lane-monitor sample milestones are source-matched to forward_evidence_scorecard.json decision_gate_minimums using {active_gate} for this lane"
    if active_gate == "phase8_promotion_review":
        caution = "Phase 8 shadow first-read status is a review floor, not a promotion entitlement"
        assert_contains(payload.get("decision_gate_caution", ""), caution, case["name"])
    elif payload.get("decision_gate_caution"):
        raise AssertionError(f"{case['name']}: unexpected decision-gate caution for non-Phase 8 lane")
    assert_contains(text, f"- Forward assessment: {case['assessment']}", case["name"])
    assert_contains(md, f"- Assessment: **{case['assessment']}**", case["name"])
    assert_contains(text, "- ROI coverage:", case["name"])
    assert_contains(md, "- ROI coverage:", case["name"])
    assert_contains(text, "- Decision gate:", case["name"])
    assert_contains(md, "- Decision gate:", case["name"])
    assert_contains(text, "- valid_evidence_scope=compact per-lane forward-observation and settlement-queue review", case["name"])
    assert_contains(text, "- Evidence boundary: lane monitor is compact forward-observation and settlement-queue metadata only; not a current-day scanner result, not settled ROI evidence, not promotion readiness, not live profitability evidence, and not real-money support.", case["name"])
    assert_contains(md, "## Evidence Boundary", case["name"])
    assert_contains(md, "- `valid_evidence_scope=compact per-lane forward-observation and settlement-queue review`", case["name"])
    assert_contains(md, "- Valid use: compact per-lane forward-observation and settlement-queue review.", case["name"])
    assert_contains(md, "- Boundary: lane monitor is compact forward-observation and settlement-queue metadata only; not a current-day scanner result, not settled ROI evidence, not promotion readiness, not live profitability evidence, and not real-money support.", case["name"])
    assert_contains(text, "- Gate source: forward_evidence_scorecard.json decision_gate_minimums loaded=True anchor_displacement=30 phase8_promotion_review=20 real_money_discussion=100 real_money_no_baq_as_bel_required=True", case["name"])
    assert_contains(text, f"- Active gates: first_read={active_first_read}; portfolio_review=100. {alignment}.", case["name"])
    assert_contains(md, "## Decision-Gate Source", case["name"])
    assert_contains(md, "Scorecard `decision_gate_minimums`: anchor_displacement=30", case["name"])
    assert_contains(md, "real_money_requires=positive paper ROI; concentration checks; payout-distribution sanity checks; no BAQ-as-BEL substitution", case["name"])
    assert_contains(md, f"Active lane-monitor gates: first_read={active_first_read}; portfolio_review=100. {alignment}.", case["name"])
    for needle in case["text_needles"]:
        assert_contains(text, needle, case["name"])
    for needle in case["md_needles"]:
        assert_contains(md, needle, case["name"])

    return {
        "case": case["name"],
        "scenario": case["scenario"],
        "assessment": payload["forward"]["portfolio_assessment"],
        "open_count": payload["open_settlements"]["count"],
        "shown": payload["open_settlements"]["shown"],
        "incomplete_count": payload["incomplete_settlements"]["count"],
        "incomplete_shown": payload["incomplete_settlements"]["shown"],
        "lane_label": payload["lane_label"],
        "text_output": str(text_output.relative_to(BASE)),
        "md_output": str(md_output.relative_to(BASE)),
    }


def live_lane_dirs() -> list[Path]:
    lanes: list[Path] = []
    if not LIVE_RUNS_ROOT.exists():
        raise AssertionError(f"no live run folders found under {LIVE_RUNS_ROOT}")
    for run_root in sorted(p for p in LIVE_RUNS_ROOT.iterdir() if p.is_dir()):
        for lane_dir in sorted(p for p in run_root.iterdir() if p.is_dir()):
            if (lane_dir / "lane_monitor.txt").exists() and (lane_dir / "lane_monitor.md").exists():
                lanes.append(lane_dir)
    if not lanes:
        raise AssertionError(f"no live lane-monitor surfaces found under {LIVE_RUNS_ROOT}")
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
            max_open=5,
            format="json",
            output=None,
        )
        payload = lane_monitor_source.build_monitor_payload(args)
        assert_scorecard_gate_source(payload, f"live_surface_{lane_dir.parent.name}_{lane_name}")
        assert_lane_monitor_evidence_boundary(payload, f"live_surface_{lane_dir.parent.name}_{lane_name}")
        expected_text = lane_monitor_source.render_text(payload)
        expected_md = lane_monitor_source.render_md(payload) + "\n"
        text_path = lane_dir / "lane_monitor.txt"
        md_path = lane_dir / "lane_monitor.md"
        if text_path.read_text(encoding="utf-8") != expected_text:
            raise AssertionError(f"live lane_monitor.txt drifted from the current source-layer rebuild: {text_path}")
        if md_path.read_text(encoding="utf-8") != expected_md:
            raise AssertionError(f"live lane_monitor.md drifted from the current source-layer rebuild: {md_path}")
        results.append({
            "case": f"live_surface_{lane_dir.parent.name}_{lane_name}",
            "scenario": "saved live lane-monitor surfaces match the current source-layer rebuild",
            "assessment": payload["forward"]["portfolio_assessment"],
            "open_count": payload["open_settlements"]["count"],
            "shown": payload["open_settlements"]["shown"],
            "lane_label": payload["lane_label"],
            "lane_dir": str(lane_dir.relative_to(BASE)),
            "text_output": str(text_path.relative_to(BASE)),
            "md_output": str(md_path.relative_to(BASE)),
        })
    return results


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    scorecard_json = args.scorecard_json.expanduser().resolve()
    configure_output_paths(args.fixture_root.expanduser().resolve(), args.out_dir.expanduser().resolve())
    scorecard_gates = read_scorecard_gate_minimums(scorecard_json)
    scorecard_artifact_guardrails = scorecard_no_artifact_guardrails(scorecard_json)

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for legacy in [
        FIXTURE_ROOT / "lane_monitor_fixture_validation.md",
        FIXTURE_ROOT / "lane_monitor_fixture_validation.json",
    ]:
        if legacy.exists():
            legacy.unlink()
    scratch = build_fixture_scratch_metadata()
    fixture_results = [run_case(case) for case in CASES]
    live_surfaces = validate_live_surfaces()
    results = fixture_results + live_surfaces
    suite_read = (
        "lane monitor still carries forward assessment, sample-progress milestones, open-settlement queue visibility with row-specific safe settlement-command templates, incomplete-settlement visibility, truncation, missing-baseline handling, "
        "zero-settled pre-evidence wording, decision-grade ROI detail, explicit missing/malformed/non-positive-cost ROI-complete coverage gap visibility including settled_ts timestamp-quality gaps, scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that fixture cleanliness, saved-live rebuilds, open queues, incomplete-settlement repair lines, and review-floor cautions do not advance, rejecting malformed and non-positive scorecard gates before fixture/report artifacts, and the no-overpromotion decision gate plus Phase 8 review-floor caution through the compact per-lane monitor surface, with fixture JSON/text/markdown outputs plus saved live lane-monitor text/markdown surfaces pinned to fresh source-layer output; "
        "the source payload/text/markdown and direct validator report now publish `valid_evidence_scope=compact per-lane forward-observation and settlement-queue review` plus a compact valid-use and evidence-boundary contract, the validator now publishes project-local fixture scratch metadata; lane monitor: compact forward-observation surface, not new forward evidence by itself"
    )
    child_checks = [
        *scorecard_artifact_guardrails,
        {
            "check": "fixture_forward_states_and_queue_modes_stay_covered",
            "status": "pass",
            "detail": "fixture cases still cover the main compact-monitor ladder across no-data, too-early, decision-grade, missing-baseline, queue-truncation, incomplete-settlement, and ROI-gap branches",
        },
        {
            "check": "saved_outputs_and_live_surfaces_match_current_rebuilds",
            "status": "pass",
            "detail": "fixture JSON/text/markdown outputs plus saved live lane_monitor text and markdown surfaces still have to match fresh source-layer rebuilds instead of drifting behind helper changes",
        },
        {
            "check": "incomplete_settlement_and_roi_gap_visibility_stay_explicit",
            "status": "pass",
            "detail": "rows settled without outcomes and settled rows still missing ROI coverage, including malformed actual_cost values, non-positive actual/expected cost values, and missing/placeholder/malformed settled_ts values, stay explicit in the compact monitor instead of disappearing into a quiet no-data read or silent expected-cost fallback",
        },
        {
            "check": "sample_progress_baseline_and_queue_context_stay_pinned",
            "status": "pass",
            "detail": "sample-progress milestones, frozen-baseline carry-through, open-settlement counts, decision-grade ROI context, the scorecard-sourced 30/20/100 gate source, and the no-BAQ-as-BEL real-money prerequisite stay pinned directly in the compact lane-monitor helper layer",
        },
        {
            "check": "open_queue_settlement_templates_stay_safe_and_row_specific",
            "status": "pass",
            "detail": "open settlement rows in the compact lane monitor now carry row-specific helper templates with invalid placeholders and the evidence-first warning, reducing manual command reconstruction without turning open rows into bet-ready or settled-performance evidence",
        },
        {
            "check": "lane_monitor_decision_gate_stays_visible",
            "status": "pass",
            "detail": "the compact lane monitor now carries the forward-check decision gate so 30-settled first reads and zero-settled pre-evidence states do not masquerade as promotion or real-money permission",
        },
        {
            "check": "phase8_review_floor_caution_stays_visible",
            "status": "pass",
            "detail": "Phase 8 shadow lane monitors carry the review-floor caution when the active first-read gate is phase8_promotion_review, so 20-row shadow reads are not displayed as promotion entitlements",
        },
        {
            "check": "lane_monitor_explicitly_stays_compact_observation_not_new_evidence",
            "status": "pass",
            "detail": "the lane-monitor source payload/text/markdown and direct validator summary publish the visible valid_evidence_scope line and say plainly that lane monitor is a compact forward-observation and settlement-queue surface rather than a current-day scanner result, settled ROI evidence, promotion readiness, live-profitability proof, or real-money support",
        },
        {
            "check": "direct_validation_report_exposes_lane_monitor_valid_scope",
            "status": "pass",
            "detail": "the direct lane-monitor validator report now exposes the raw valid_evidence_scope line and keeps green compact-monitor checks classified as observation/queue metadata only",
        },
        {
            "check": "fixture_scratch_metadata_published",
            "status": "pass",
            "detail": "the lane-monitor validator now publishes project-local fixture scratch metadata so parent rollups can verify isolated monitor-fixture hygiene without parsing markdown prose",
        },
        {
            "check": "lane_monitor_preserves_scorecard_gate_boundary",
            "status": "pass",
            "detail": "the lane-monitor validator now publishes the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite while saying fixture cleanliness, saved-live rebuilds, open queues, incomplete-settlement repair lines, and review-floor cautions do not count toward those gates",
        },
    ]
    if (
        scorecard_gates.get("source") != "forward_evidence_scorecard.json"
        or scorecard_gates.get("source_path") != "decision_gate_minimums"
        or scorecard_gates.get("anchor_displacement_min_roi_complete_settled_observations") != 30
        or scorecard_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") != 20
        or scorecard_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") != 100
        or scorecard_gates.get("real_money_no_baq_as_bel_required") is not True
        or "no BAQ-as-BEL substitution" not in scorecard_gates.get("real_money_also_requires", [])
    ):
        raise AssertionError("lane-monitor scorecard gate boundary no longer matches forward_evidence_scorecard.json")

    lines = [
        "# Paper-Trade Lane Monitor Validation",
        "",
        "This report validates `paper_trade_lane_monitor.py` directly against representative fixture cases under `out/status_validation/lane_monitor_fixture/`, while publishing the direct validator readout under `out/status_validation/paper_trade_lane_monitor/`.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Fixture scratch metadata: `{scratch['fixture_root_relative']}` is project-local and each fixture case root is cleared before setup.",
        "",
        "## Fixture cases",
        "",
        "| Case | Scenario | Result |",
        "|---|---|---|",
        *[
            f"| `{row['case']}` | {row['scenario']} | {row['assessment']} ({row['open_count']} open, showing {row['shown']}) |"
            for row in fixture_results
        ],
        "",
        "## Live current surfaces",
        "",
        *[
            f"- `{row['lane_dir']}` -> `{row['text_output']}` and `{row['md_output']}` ({row['assessment']}, {row['open_count']} open showing {row['shown']})"
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
        f"- valid_evidence_scope={EVIDENCE_BOUNDARY['valid_evidence_scope']}",
        f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
        "- Boundary: lane-monitor validator cleanliness is compact observation metadata only, not new forward evidence, not a live paper-trade ledger, not a current-day scanner result, not settled ROI, not live profitability, not promotion readiness, and not real-money evidence.",
        "- Non-goals: do not treat open settlement queues, incomplete-settlement repair lines, scorecard-gate visibility, Phase 8 review-floor cautions, saved-live rebuild cleanliness, or green validators as ROI-complete observations, profitability evidence, promotion support, or real-money support.",
        "",
        "## Decision-Gate Source",
        "",
        f"- Source: `{scorecard_gates['source']}` `{scorecard_gates['source_path']}`.",
        f"- Anchor displacement: `{scorecard_gates['anchor_displacement_min_roi_complete_settled_observations']}` ROI-complete same-candidate paper observations.",
        f"- Phase 8 promotion review: `{scorecard_gates['phase8_promotion_review_min_roi_complete_settled_observations']}` ROI-complete shadow observations.",
        f"- Real-money discussion: `{scorecard_gates['real_money_discussion_min_total_settled_observations_with_usable_roi']}` total settled observations with usable ROI.",
        f"- Real-money prerequisites: {'; '.join(scorecard_gates['real_money_also_requires'])}.",
        f"- Boundary: {scorecard_gates['evidence_boundary']}.",
        "",
        "## Validation result",
        "",
        "- Fixture root: `out/status_validation/lane_monitor_fixture/`",
        "- Direct validator report path: `out/status_validation/paper_trade_lane_monitor/`",
        "- The lane monitor still has direct source-layer fixture coverage for its main compact-monitor branches instead of relying only on downstream summary surfaces.",
        "- Each fixture still requires the saved `lane_monitor.json`, `lane_monitor.txt`, and `lane_monitor.md` outputs to match fresh source-layer renders from `paper_trade_lane_monitor.py`.",
        "- The validator now also fails if any saved live `lane_monitor.txt` or `lane_monitor.md` surface under `out/daily_portfolio_runs/` drifts from the current source-layer rebuild.",
        "- Malformed scorecard gate metadata now fails before fixture roots or report artifacts are created, including boolean anchor-displacement floors, non-positive Phase 8 / real-money floors, and missing no-BAQ-as-BEL real-money prerequisites.",
        "- This pins forward-assessment carry-through, first-read plus broader review sample-progress milestones, the scorecard-sourced 30/20/100 gate source plus the no-BAQ-as-BEL real-money prerequisite, the no-overpromotion decision gate plus Phase 8 review-floor caution, open-settlement queue rendering with row-specific safe settlement-command templates, queue truncation, missing-baseline handling, zero-settled pre-evidence wording, explicit missing/malformed/non-positive-cost ROI-complete coverage-gap messaging including settled_ts gaps, and next-step wording in one reproducible helper-level check across both fixtures and real saved lane surfaces.",
        "- The validator JSON now also publishes fifteen explicit structured guardrails, including malformed-scorecard and non-positive-gate no-artifact checks, project-local fixture scratch metadata, the source monitor valid_evidence_scope / valid-use / evidence-boundary contract, the direct validator valid_evidence_scope exposure, and the scorecard-sourced gate boundary, so parent rollups can verify that lane-monitor fixture cleanliness, saved-live rebuilds, open queues, incomplete-settlement repair lines, and review-floor cautions stay compact observation metadata rather than settled sample progress.",
        "",
    ]
    payload = {
        "suite_status": "pass",
        "valid_evidence_scope": lane_monitor_source.LANE_MONITOR_VALID_EVIDENCE_SCOPE,
        "total_fixture_scenarios": len(fixture_results),
        "total_checks": len(results),
        "check_count": len(results),
        "child_check_count": len(child_checks),
        "child_checks": child_checks,
        "fixture_case_count": len(fixture_results),
        "live_surface_checks": len(live_surfaces),
        "results": results,
        "summary": {
            "suite_read": suite_read,
        },
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "scratch": scratch,
        "fixture_root": display_path(FIXTURE_ROOT),
        "report_path": display_path(OUT_DIR),
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }
    write_text(REPORT_MD, "\n".join(lines))
    write_text(REPORT_JSON, json.dumps(payload, indent=2) + "\n")

    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    for row in results:
        print(f"PASS {row['case']}: {row['assessment']} with {row['open_count']} open row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
