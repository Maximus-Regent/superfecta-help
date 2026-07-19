#!/usr/bin/env python3
"""
Fixture-driven validation for ev_ticket_engine.py.

Purpose:
- pin the EV sizing layer directly instead of trusting stake math implicitly
- keep the conservative no-bet guardrails reproducible
- verify the real CLI writes stable JSON / CSV artifacts for both bet and no-bet cases
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
import ev_ticket_engine as ev_engine_source

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "ev_ticket_engine.py"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "ev_ticket_engine_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "ev_ticket_engine"
REPORT_MD = OUT_DIR / "ev_ticket_engine_validation.md"
REPORT_JSON = OUT_DIR / "ev_ticket_engine_validation.json"
REBUILD_COMMAND = "python3 validate_ev_ticket_engine.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "EV ticket engine validator",
    "valid_evidence_scope": ev_engine_source.EV_TICKET_ENGINE_VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "ev_ticket_engine.py isolated stake-sizing fixtures",
        "forward_evidence_scorecard.json decision_gate_minimums",
    ],
    "valid_use": "source-layer stake-sizing reproducibility validation",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "ev_ticket_engine_validator_passes_are_source_layer_metadata_only": True,
    "ev_ticket_engine_validator_passes_are_sizing_metadata_only": True,
}


CASES: list[dict[str, Any]] = [
    {
        "name": "case_empty_prediction_file_no_bet",
        "scenario": "empty prediction files still produce a stable NO BET plan and no selected-ticket CSV",
        "rows": [],
        "expect_exit": 0,
        "stdout_needles": [
            "Decision: NO BET",
            "Reason: No rows were available in the prediction file.",
        ],
        "expected_plan": {
            "decision": "NO BET",
            "reason": "No rows were available in the prediction file.",
            "tickets_considered": 0,
            "tickets_selected": 0,
            "total_stake": 0.0,
            "portfolio_expected_roi_pct": 0.0,
        },
        "expect_csv": False,
    },
    {
        "name": "case_negative_ev_rejected",
        "scenario": "negative-EV tickets still stop at an honest NO BET instead of forcing bankroll through a bad edge",
        "rows": [
            {"combo": "1-2-3-4", "jointProb": 0.01, "predicted_payout": 80.0, "rank": 1},
        ],
        "expect_exit": 0,
        "stdout_needles": [
            "Decision: NO BET",
            "Reason: Best ticket is still negative EV after the conservative payout haircut.",
        ],
        "expected_plan": {
            "decision": "NO BET",
            "reason": "Best ticket is still negative EV after the conservative payout haircut.",
            "tickets_considered": 1,
            "tickets_selected": 0,
            "total_stake": 0.0,
        },
        "expect_csv": False,
    },
    {
        "name": "case_low_probability_rejected",
        "scenario": "very low-probability longshots still stay out even when their raw payout would look tempting",
        "rows": [
            {"combo": "1-2-3-4", "jointProb": 0.0004, "predicted_payout": 5000.0, "rank": 1},
        ],
        "expect_exit": 0,
        "stdout_needles": [
            "Decision: NO BET",
            "Reason: Best ticket is too low-probability for the current filters.",
        ],
        "expected_plan": {
            "decision": "NO BET",
            "reason": "Best ticket is too low-probability for the current filters.",
            "tickets_considered": 1,
            "tickets_selected": 0,
            "total_stake": 0.0,
        },
        "expect_csv": False,
    },
    {
        "name": "case_min_ticket_increment_blocks_underfloor_stakes",
        "scenario": "eligible tickets still degrade to NO BET when risk caps push every stake below the minimum ticket increment",
        "rows": [
            {"combo": "1-2-3-4", "jointProb": 0.02, "predicted_payout": 120.0, "rank": 1},
        ],
        "cli_args": ["--bankroll", "10", "--ticket-increment", "1.0"],
        "expect_exit": 0,
        "stdout_needles": [
            "Decision: NO BET",
            "Reason: Risk caps pushed every recommended stake below the minimum ticket increment.",
        ],
        "expected_plan": {
            "decision": "NO BET",
            "reason": "Risk caps pushed every recommended stake below the minimum ticket increment.",
            "tickets_considered": 1,
            "tickets_selected": 0,
            "bankroll": 10.0,
            "race_risk_budget": 0.2,
            "total_stake": 0.0,
        },
        "expect_csv": False,
    },
    {
        "name": "case_multi_ticket_bet_respects_rank_and_caps",
        "scenario": "positive-EV races still size the top tickets, respect max-ticket selection, and write selected-ticket artifacts",
        "rows": [
            {"combo": "1-2-3-4", "jointProb": 0.02, "predicted_payout": 120.0, "rank": 1},
            {"combo": "1-2-4-3", "jointProb": 0.015, "predicted_payout": 140.0, "rank": 2},
            {"combo": "1-3-2-4", "jointProb": 0.01, "predicted_payout": 200.0, "rank": 3},
        ],
        "cli_args": ["--max-tickets", "2"],
        "expect_exit": 0,
        "stdout_needles": [
            "Decision: BET",
            "Stake $1.70 -> expected return $2.93 (expected profit $1.23, ROI 72.35%)",
            "1. 1-2-3-4 | stake $1.10 | p=2.0000% | adj payout $90.00 | EV ROI 80.00%",
            "2. 1-2-4-3 | stake $0.60 | p=1.5000% | adj payout $105.00 | EV ROI 57.50%",
        ],
        "expected_plan": {
            "decision": "BET",
            "reason": "At least one ticket cleared the EV filters and fit inside bankroll caps.",
            "tickets_considered": 3,
            "tickets_selected": 2,
            "race_risk_budget": 10.0,
            "total_stake": 1.7,
            "total_expected_return": 2.93,
            "total_expected_profit": 1.23,
            "portfolio_expected_roi_pct": 72.35,
        },
        "ticket_expectations": [
            {"combo": "1-2-3-4", "recommended_stake": 1.1, "ev_roi_pct": 80.0},
            {"combo": "1-2-4-3", "recommended_stake": 0.6, "ev_roi_pct": 57.5},
        ],
        "expect_csv": True,
    },
    {
        "name": "case_missing_probability_column_fails_loudly",
        "scenario": "missing required probability columns still fail loudly instead of fabricating a plan from malformed input",
        "rows": [
            {"combo": "1-2-3-4", "predicted_payout": 120.0, "rank": 1},
        ],
        "expect_exit": 1,
        "stderr_needles": ["Missing probability column: jointProb"],
        "expect_json": False,
        "expect_csv": False,
    },
]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        df = pd.DataFrame(rows)
    else:
        df = pd.DataFrame(columns=["combo", "jointProb", "predicted_payout", "rank"])
    df.to_csv(path, index=False)



def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))



def guardrail(condition: bool, check: str, detail: str) -> dict[str, str]:
    if not condition:
        raise AssertionError(f"{check}: {detail}")
    return {"check": check, "status": "pass", "detail": detail}


def display_scorecard_path(scorecard_json: Path) -> str:
    try:
        return str(scorecard_json.relative_to(BASE))
    except ValueError:
        return str(scorecard_json)


def require_positive_non_bool_int(value: Any, *, field_name: str, source_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, field_name: str, source_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise AssertionError(f"{source_name} {field_name} must be a string list")
    return value


def read_scorecard_gate_minimums(scorecard_json: Path = SCORECARD_JSON) -> dict[str, Any]:
    source_name = display_scorecard_path(scorecard_json)
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
        field_name="decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
        source_name=source_name,
    )
    phase8_min = require_positive_non_bool_int(
        phase8.get("min_roi_complete_settled_observations"),
        field_name="decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
        source_name=source_name,
    )
    real_money_min = require_positive_non_bool_int(
        real_money.get("min_total_settled_observations_with_usable_roi"),
        field_name="decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
        source_name=source_name,
    )
    real_money_requires = require_string_list(
        real_money.get("also_requires"),
        field_name="decision_gate_minimums.real_money_discussion.also_requires",
        source_name=source_name,
    )
    if NO_BAQ_AS_BEL_PREREQUISITE not in real_money_requires:
        raise AssertionError(
            f"{source_name} decision_gate_minimums.real_money_discussion.also_requires "
            f"must include {NO_BAQ_AS_BEL_PREREQUISITE}"
        )
    return {
        "source": source_name,
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_also_requires": real_money_requires,
        "real_money_no_baq_as_bel_required": True,
        "evidence_boundary": (
            "EV sizing fixtures, stake plans, selected-ticket artifacts, and validator passes do not count toward "
            "anchor-displacement, Phase 8 promotion-review, or real-money discussion gates"
        ),
    }


def configure_output_paths(fixture_root: Path, out_dir: Path) -> None:
    global FIXTURE_ROOT, OUT_DIR, REPORT_MD, REPORT_JSON
    FIXTURE_ROOT = fixture_root
    OUT_DIR = out_dir
    REPORT_MD = OUT_DIR / "ev_ticket_engine_validation.md"
    REPORT_JSON = OUT_DIR / "ev_ticket_engine_validation.json"


def build_fixture_scratch_metadata() -> dict[str, Any]:
    return {
        "fixture_root": str(FIXTURE_ROOT),
        "fixture_root_relative": str(FIXTURE_ROOT.relative_to(BASE)),
        "fixture_root_is_project_local": FIXTURE_ROOT.is_relative_to(BASE),
        "case_roots_cleared_by_setup_case": True,
        "evidence_boundary": "EV ticket-engine fixture scratch metadata is reproducibility context only, not stake-sizing proof, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
    }


def assert_scorecard_failure_before_artifacts(
    *,
    scorecard_json: Path,
    mutation: Any,
    expected_error: str,
    check: str,
    detail: str,
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="ev_ticket_engine_scorecard_guardrail_") as tmp_name:
        tmpdir = Path(tmp_name)
        bad_scorecard = tmpdir / "forward_evidence_scorecard.json"
        bad_payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
        mutation(bad_payload)
        bad_scorecard.write_text(json.dumps(bad_payload, indent=2) + "\n", encoding="utf-8")
        nested_fixture_root = tmpdir / "nested" / "fixture"
        nested_out_dir = tmpdir / "nested" / "out"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(bad_scorecard),
                "--fixture-root",
                str(nested_fixture_root),
                "--out-dir",
                str(nested_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        combined_output = result.stdout + result.stderr
        if result.returncode == 0:
            raise AssertionError(f"{check}: malformed scorecard unexpectedly passed")
        if expected_error not in combined_output:
            raise AssertionError(
                f"{check}: expected error {expected_error!r}, got stdout={result.stdout!r} stderr={result.stderr!r}"
            )
        if nested_fixture_root.exists() or nested_out_dir.exists():
            raise AssertionError(f"{check}: malformed scorecard created fixture/report artifacts")
    return guardrail(True, check, detail)


def scorecard_no_artifact_guardrails(scorecard_json: Path) -> list[dict[str, str]]:
    return [
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["anchor_displacement"].__setitem__(
                "min_roi_complete_settled_observations",
                True,
            ),
            expected_error=(
                "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check="scorecard_boolean_gate_floor_fails_before_ev_ticket_artifacts",
            detail=(
                "a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before "
                "nested EV ticket-engine fixture/report artifacts are created"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["phase8_promotion_review"].__setitem__(
                "min_roi_complete_settled_observations",
                0,
            ),
            expected_error=(
                "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check="scorecard_nonpositive_phase8_gate_floor_fails_before_ev_ticket_artifacts",
            detail=(
                "a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails before "
                "nested EV ticket-engine fixture/report artifacts are created"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                "min_total_settled_observations_with_usable_roi",
                0,
            ),
            expected_error=(
                "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi "
                "must be a positive non-boolean integer"
            ),
            check="scorecard_nonpositive_real_money_gate_floor_fails_before_ev_ticket_artifacts",
            detail=(
                "a non-positive real-money discussion floor in forward_evidence_scorecard.json fails before "
                "nested EV ticket-engine fixture/report artifacts are created"
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
            expected_error=(
                "decision_gate_minimums.real_money_discussion.also_requires "
                f"must include {NO_BAQ_AS_BEL_PREREQUISITE}"
            ),
            check="scorecard_missing_no_baq_fails_before_ev_ticket_artifacts",
            detail=(
                "a scorecard missing the no-BAQ-as-BEL real-money prerequisite fails before "
                "nested EV ticket-engine fixture/report artifacts are created"
            ),
        ),
    ]



def setup_case(case: dict[str, Any]) -> tuple[Path, Path, Path, Path]:
    case_root = FIXTURE_ROOT / case["name"]
    if case_root.exists():
        shutil.rmtree(case_root)
    case_root.mkdir(parents=True, exist_ok=True)
    input_csv = case_root / "input.csv"
    plan_json = case_root / "plan.json"
    plan_csv = case_root / "plan.csv"
    write_csv(input_csv, case["rows"])
    return case_root, input_csv, plan_json, plan_csv



def assert_plan_fields(case_name: str, plan: dict[str, Any], expected: dict[str, Any]) -> None:
    for key, value in expected.items():
        if plan.get(key) != value:
            raise AssertionError(f"{case_name}: expected {key}={value!r}, got {plan.get(key)!r}")



def run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_root, input_csv, plan_json, plan_csv = setup_case(case)
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--input",
        str(input_csv),
        "--race-label",
        case["name"],
        "--save-json",
        str(plan_json),
        "--save-csv",
        str(plan_csv),
    ]
    cmd.extend(case.get("cli_args", []))

    result = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)
    (case_root / "stdout.txt").write_text(result.stdout, encoding="utf-8")
    (case_root / "stderr.txt").write_text(result.stderr, encoding="utf-8")

    expect_exit = case.get("expect_exit", 0)
    if result.returncode != expect_exit:
        raise AssertionError(
            f"{case['name']}: expected exit {expect_exit}, got {result.returncode} with stderr {result.stderr!r}"
        )

    for needle in case.get("stdout_needles", []):
        if needle not in result.stdout:
            raise AssertionError(f"{case['name']}: expected stdout to contain {needle!r}")
    scope_line = f"valid_evidence_scope={ev_engine_source.EV_TICKET_ENGINE_VALID_EVIDENCE_SCOPE}"
    if expect_exit == 0 and scope_line not in result.stdout:
        raise AssertionError(f"{case['name']}: EV ticket-engine stdout lost the source-level valid_evidence_scope")
    boundary_line = f"Evidence boundary: {ev_engine_source.EV_TICKET_ENGINE_BOUNDARY_TEXT}"
    if expect_exit == 0 and boundary_line not in result.stdout:
        raise AssertionError(f"{case['name']}: EV ticket-engine stdout lost the source-level evidence boundary")
    for needle in case.get("stderr_needles", []):
        if needle not in result.stderr:
            raise AssertionError(f"{case['name']}: expected stderr to contain {needle!r}")

    expect_json = case.get("expect_json", True)
    if expect_json:
        if not plan_json.exists():
            raise AssertionError(f"{case['name']}: expected JSON plan artifact")
        plan = read_json(plan_json)
        assert_plan_fields(case["name"], plan, case["expected_plan"])
        if plan.get("valid_evidence_scope") != ev_engine_source.EV_TICKET_ENGINE_VALID_EVIDENCE_SCOPE:
            raise AssertionError(f"{case['name']}: plan JSON lost valid_evidence_scope")
        if plan.get("evidence_boundary_text") != ev_engine_source.EV_TICKET_ENGINE_BOUNDARY_TEXT:
            raise AssertionError(f"{case['name']}: plan JSON lost evidence_boundary_text")
        boundary = plan.get("evidence_boundary")
        if not isinstance(boundary, dict):
            raise AssertionError(f"{case['name']}: plan JSON lost machine-readable evidence_boundary")
        for flag in (
            "not_current_day_scanner_result",
            "not_live_paper_trade_ledger",
            "not_settled_roi_evidence",
            "not_promotion_readiness_evidence",
            "not_live_profitability_evidence",
            "not_real_money_evidence",
            "requires_later_audit_or_forward_check_review_before_sample_gate_use",
        ):
            if boundary.get(flag) is not True:
                raise AssertionError(f"{case['name']}: plan JSON evidence_boundary lost true {flag}")
        ticket_expectations = case.get("ticket_expectations", [])
        if ticket_expectations:
            tickets = plan.get("tickets", [])
            if len(tickets) != len(ticket_expectations):
                raise AssertionError(
                    f"{case['name']}: expected {len(ticket_expectations)} tickets, got {len(tickets)}"
                )
            for idx, expected_ticket in enumerate(ticket_expectations):
                for key, value in expected_ticket.items():
                    if tickets[idx].get(key) != value:
                        raise AssertionError(
                            f"{case['name']}: expected ticket {idx} {key}={value!r}, got {tickets[idx].get(key)!r}"
                        )
    else:
        if plan_json.exists():
            raise AssertionError(f"{case['name']}: did not expect JSON artifact on failure")

    expect_csv = case.get("expect_csv", False)
    if expect_csv and not plan_csv.exists():
        raise AssertionError(f"{case['name']}: expected selected-ticket CSV artifact")
    if not expect_csv and plan_csv.exists():
        raise AssertionError(f"{case['name']}: did not expect selected-ticket CSV artifact")
    if expect_csv:
        ticket_df = pd.read_csv(plan_csv)
        if "valid_evidence_scope" not in ticket_df.columns:
            raise AssertionError(f"{case['name']}: selected-ticket CSV lost valid_evidence_scope")
        scope_values = set(ticket_df["valid_evidence_scope"].astype(str))
        if scope_values != {ev_engine_source.EV_TICKET_ENGINE_VALID_EVIDENCE_SCOPE}:
            raise AssertionError(f"{case['name']}: selected-ticket CSV valid_evidence_scope values drifted: {scope_values!r}")
        if "evidence_boundary_text" not in ticket_df.columns:
            raise AssertionError(f"{case['name']}: selected-ticket CSV lost evidence_boundary_text")
        boundary_values = set(ticket_df["evidence_boundary_text"].astype(str))
        if boundary_values != {ev_engine_source.EV_TICKET_ENGINE_BOUNDARY_TEXT}:
            raise AssertionError(f"{case['name']}: selected-ticket CSV boundary values drifted: {boundary_values!r}")

    return {
        "name": case["name"],
        "scenario": case["scenario"],
        "result": "PASS",
        "plan_json": str(plan_json.relative_to(BASE)) if plan_json.exists() else "",
        "stdout": str((case_root / "stdout.txt").relative_to(BASE)),
        "stderr": str((case_root / "stderr.txt").relative_to(BASE)),
    }



def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--fixture-root", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    scorecard_json = args.scorecard_json.expanduser().resolve()
    configure_output_paths(
        fixture_root=args.fixture_root.expanduser().resolve(),
        out_dir=args.out_dir.expanduser().resolve(),
    )
    scorecard_gates = read_scorecard_gate_minimums(scorecard_json)
    scorecard_guardrails = scorecard_no_artifact_guardrails(scorecard_json)

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for legacy in (
        FIXTURE_ROOT / "ev_ticket_engine_fixture_validation.md",
        FIXTURE_ROOT / "ev_ticket_engine_fixture_validation.json",
    ):
        legacy.unlink(missing_ok=True)

    results = [run_case(case) for case in CASES]
    plan_by_case = {
        row["name"]: read_json(BASE / row["plan_json"])
        for row in results
        if row["plan_json"]
    }
    stderr_by_case = {
        row["name"]: (BASE / row["stderr"]).read_text(encoding="utf-8")
        for row in results
    }
    scratch = build_fixture_scratch_metadata()
    current_read = "the EV sizing engine still rejects empty, negative-edge, low-probability, and under-minimum-stake cases conservatively, selects only the top positive-EV tickets that fit inside bankroll caps, fails loudly on malformed probability inputs instead of fabricating a plan, prints source-level valid_evidence_scope plus evidence-boundary lines in successful CLI output, carries source-level valid_evidence_scope plus machine-readable evidence-boundary fields in successful JSON plan artifacts, carries valid_evidence_scope plus evidence-boundary text in selected-ticket CSV rows, rejects malformed and non-positive scorecard gates before fixture/report artifacts, publishes project-local fixture scratch metadata, exposes exact valid_evidence_scope=ev_ticket_stake_sizing_metadata_only as direct validator-report metadata only, preserves the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that stake-sizing fixtures do not advance, and now publishes its direct validator report at the standard ev-ticket-engine validation path; this is a source-layer stake-sizing reproducibility check, not live profitability, promotion, or real-money evidence"
    child_checks = [
        *scorecard_guardrails,
        guardrail(
            plan_by_case["case_empty_prediction_file_no_bet"].get("decision") == "NO BET"
            and plan_by_case["case_empty_prediction_file_no_bet"].get("tickets_selected") == 0
            and plan_by_case["case_negative_ev_rejected"].get("decision") == "NO BET"
            and plan_by_case["case_negative_ev_rejected"].get("tickets_selected") == 0
            and plan_by_case["case_low_probability_rejected"].get("decision") == "NO BET"
            and plan_by_case["case_low_probability_rejected"].get("tickets_selected") == 0,
            "empty_negative_and_low_probability_inputs_stay_no_bet",
            "empty prediction files, negative-edge tickets, and too-low-probability longshots still stop as conservative NO BET plans before any stake is allocated",
        ),
        guardrail(
            plan_by_case["case_min_ticket_increment_blocks_underfloor_stakes"].get("decision") == "NO BET"
            and plan_by_case["case_min_ticket_increment_blocks_underfloor_stakes"].get("bankroll") == 10.0
            and plan_by_case["case_min_ticket_increment_blocks_underfloor_stakes"].get("race_risk_budget") == 0.2
            and plan_by_case["case_min_ticket_increment_blocks_underfloor_stakes"].get("total_stake") == 0.0,
            "risk_caps_and_ticket_increment_floor_stay_conservative",
            "eligible edges still degrade to NO BET when bankroll caps and ticket-increment floors push every playable stake below the minimum ticket increment",
        ),
        guardrail(
            plan_by_case["case_multi_ticket_bet_respects_rank_and_caps"].get("decision") == "BET"
            and plan_by_case["case_multi_ticket_bet_respects_rank_and_caps"].get("tickets_selected") == 2
            and plan_by_case["case_multi_ticket_bet_respects_rank_and_caps"].get("total_stake") == 1.7
            and [ticket.get("combo") for ticket in plan_by_case["case_multi_ticket_bet_respects_rank_and_caps"].get("tickets", [])] == ["1-2-3-4", "1-2-4-3"]
            and [ticket.get("recommended_stake") for ticket in plan_by_case["case_multi_ticket_bet_respects_rank_and_caps"].get("tickets", [])] == [1.1, 0.6],
            "positive_ev_ticket_sizing_respects_rank_and_caps",
            "positive-EV cases still select only the top ranked tickets allowed by `--max-tickets`, keep stakes inside the race risk budget, and write stable selected-ticket artifacts",
        ),
        guardrail(
            "Missing probability column: jointProb" in stderr_by_case["case_missing_probability_column_fails_loudly"]
            and "case_missing_probability_column_fails_loudly" not in plan_by_case,
            "malformed_probability_inputs_fail_loudly_without_plan_artifacts",
            "malformed prediction inputs still fail loudly on the required probability column instead of fabricating a JSON/CSV betting plan",
        ),
        guardrail(
            scratch.get("fixture_root_relative") == "out/status_validation/ev_ticket_engine_fixture"
            and scratch.get("fixture_root_is_project_local") is True
            and scratch.get("case_roots_cleared_by_setup_case") is True,
            "fixture_scratch_metadata_published",
            "the direct EV ticket-engine validator now publishes project-local fixture scratch metadata so parent rollups can verify isolated stake-sizing fixture hygiene without parsing markdown prose",
        ),
        guardrail(
            "source-layer stake-sizing reproducibility check" in current_read
            and "prints source-level valid_evidence_scope plus evidence-boundary lines" in current_read
            and f"valid_evidence_scope={ev_engine_source.EV_TICKET_ENGINE_VALID_EVIDENCE_SCOPE}" in current_read
            and EVIDENCE_BOUNDARY.get("valid_evidence_scope") == ev_engine_source.EV_TICKET_ENGINE_VALID_EVIDENCE_SCOPE
            and EVIDENCE_BOUNDARY.get("ev_ticket_engine_validator_passes_are_sizing_metadata_only") is True
            and "not live profitability, promotion, or real-money evidence" in current_read,
            "ev_ticket_engine_validator_stays_sizing_reproducibility_not_new_evidence",
            "the direct EV sizing validator summary now frames a green fixture sweep as stake-sizing reproducibility, with successful stdout, JSON plans, selected-ticket CSV rows, and the validator report itself carrying exact valid_evidence_scope metadata rather than live profitability, promotion, or real-money evidence",
        ),
        guardrail(
            scorecard_gates.get("source") == "forward_evidence_scorecard.json"
            and scorecard_gates.get("source_path") == "decision_gate_minimums"
            and scorecard_gates.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and scorecard_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and scorecard_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and scorecard_gates.get("real_money_no_baq_as_bel_required") is True
            and "no BAQ-as-BEL substitution" in scorecard_gates.get("real_money_also_requires", []),
            "ev_ticket_engine_preserves_scorecard_gate_boundary",
            "the direct EV sizing validator now reads forward_evidence_scorecard.json decision_gate_minimums and publishes the 30-row anchor-review floor, 20-row Phase 8 review floor, 100-row real-money discussion floor, and no-BAQ-as-BEL prerequisite as stake-sizing boundary metadata only",
        ),
    ]

    payload = {
        "suite_status": "pass",
        "artifact_status": "pass",
        "total_fixture_scenarios": len(results),
        "total_checks": len(results),
        "check_count": len(results),
        "child_check_count": len(child_checks),
        "child_checks": child_checks,
        "valid_evidence_scope": ev_engine_source.EV_TICKET_ENGINE_VALID_EVIDENCE_SCOPE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "scratch": scratch,
        "cases": results,
        "summary": {
            "current_read": current_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "fixture_root": str(FIXTURE_ROOT),
            "report_path": str(REPORT_MD),
        },
    }

    lines = [
        "# EV Ticket Engine Validation",
        "",
        "This report validates `ev_ticket_engine.py` directly inside isolated CLI fixtures while publishing the saved validator artifact at the standard ev-ticket-engine report path.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Fixture root: `{FIXTURE_ROOT}`",
        f"- Report path: `{REPORT_MD}`",
        "",
        "## Cases",
        "",
        "| Case | Scenario | Plan artifact |",
        "|---|---|---|",
    ]
    for row in results:
        plan_artifact = f"`{row['plan_json']}`" if row["plan_json"] else "failure-only case"
        lines.append(f"| `{row['name']}` | {row['scenario']} | {plan_artifact} |")

    lines.extend([
        "",
        "## Rollup Guardrails",
        "",
        *[f"- PASS `{check['check']}` — {check['detail']}" for check in child_checks],
        "",
        "## Current Read",
        "",
        f"- Suite read: {payload['summary']['current_read']}",
        f"- Fixture scratch metadata: `{scratch['fixture_root_relative']}` is project-local and each fixture case root is cleared before setup.",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
        f"- valid_evidence_scope={ev_engine_source.EV_TICKET_ENGINE_VALID_EVIDENCE_SCOPE}",
        "- Validator passes, fixture stake plans, selected-ticket artifacts, and CLI stdout rows are source-layer metadata only.",
        f"- Successful EV ticket-engine CLI output and JSON plans now carry `valid_evidence_scope={ev_engine_source.EV_TICKET_ENGINE_VALID_EVIDENCE_SCOPE}` plus source-level evidence boundaries, and selected-ticket CSV rows carry the same scope plus boundary text.",
        "- They are not settled ROI, live profitability, promotion readiness, a live paper-trade ledger read, or real-money evidence.",
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
        "- Empty prediction files still degrade to a stable `NO BET` plan instead of crashing or inventing stake sizing.",
        "- Negative-edge and too-low-probability tickets still stop at the correct conservative reason before any bankroll is allocated.",
        "- Risk caps and ticket-increment floors still interact honestly: a mathematically eligible edge can still become `NO BET` if the playable stake rounds below the minimum increment.",
        "- Positive-EV races still size the top tickets, respect `--max-tickets`, and write stable JSON / CSV plan artifacts through the real CLI.",
        "- Missing required probability inputs still fail loudly instead of fabricating a recommendation from malformed data.",
        "- Scorecard-sourced paper-observation gates stay visible without treating fixture stake plans or validator passes as settled evidence.",
        "",
        "## Sources",
        "",
    ])
    for row in results:
        lines.append(f"- `{row['stdout']}`")
        lines.append(f"- `{row['stderr']}`")
        if row["plan_json"]:
            lines.append(f"- `{row['plan_json']}`")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    for row in results:
        artifact = row["plan_json"] or row["stderr"]
        print(f"PASS {row['name']}: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
