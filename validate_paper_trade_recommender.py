#!/usr/bin/env python3
"""
Fixture-driven validation for paper_trade_recommender.py.

Purpose:
- pin the recommendation builder directly at the source layer
- keep Phase 7 combo filtering, allow-all-combos override, and error handling reproducible
- prove the real CLI still writes stable summary artifacts from reused prediction files without touching live model scoring
"""

from __future__ import annotations

import json
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
import paper_trade_recommender as recommender_source

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "paper_trade_recommender.py"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "paper_trade_recommender_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_recommender"
REPORT_MD = OUT_DIR / "paper_trade_recommender_validation.md"
REPORT_JSON = OUT_DIR / "paper_trade_recommender_validation.json"
REBUILD_COMMAND = "python3 validate_paper_trade_recommender.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade recommender validator",
    "valid_evidence_scope": recommender_source.RECOMMENDER_VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "paper_trade_recommender.py reused-prediction fixtures",
        "forward_evidence_scorecard.json decision_gate_minimums",
    ],
    "valid_use": "source-layer recommendation reproducibility and combo-universe guardrail validation",
    "not_new_forward_evidence": True,
    "not_live_model_scoring_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "recommender_validator_passes_are_source_layer_metadata_only": True,
}


def signal_hit(
    scan_ts: str,
    rule_id: str,
    race_id: str,
    favorite_program: str,
    *,
    track: str = "OP",
    card_name: str = "Oaklawn Park",
    race_number: str = "7",
    underneath_programs: list[str] | None = None,
    estimated_cost: float = 24.0,
) -> dict[str, Any]:
    return {
        "scan_ts": scan_ts,
        "rule_id": rule_id,
        "track": track,
        "card_name": card_name,
        "race_number": race_number,
        "race_id": race_id,
        "surface": "D",
        "condition": "FAST",
        "field_size": 12,
        "favorite_program": favorite_program,
        "favorite_name": "Fixture Favorite",
        "favorite_prob": 0.38,
        "second_prob": 0.23,
        "prob_gap": 0.15,
        "k": 7,
        "base_stake": 1.0,
        "estimated_cost": estimated_cost,
        "underneath_programs": underneath_programs or ["2", "3", "5"],
        "ticket_structure": "1/WIN with 3 underneath",
    }


def signal_key(hit: dict[str, Any]) -> str:
    return f"{hit.get('scan_ts','')}|{hit.get('rule_id','')}|{hit.get('race_id','')}|{hit.get('favorite_program','')}"


HIT_FILTERED = signal_hit("2026-04-20T11:00:00", "OP_DURABLE_K7", "OP-2026-04-20-R7", "1")
HIT_NO_UNIVERSE = signal_hit("2026-04-20T11:05:00", "OP_DURABLE_K7", "OP-2026-04-20-R8", "1")
HIT_MALFORMED = signal_hit("2026-04-20T11:10:00", "OP_DURABLE_K7", "OP-2026-04-20-R9", "1")
HIT_MISSING_RACE_ID = signal_hit("2026-04-20T11:15:00", "OP_DURABLE_K7", "", "1")


CASES: list[dict[str, Any]] = [
    {
        "name": "case_empty_scan_input",
        "scenario": "empty scan inputs still produce stable empty summary artifacts and clear stale plan/prediction files without trying to score races",
        "hits": [],
        "initial_stale_plan_artifacts": True,
        "initial_stale_prediction_artifacts": True,
        "reuse_predictions": False,
        "prediction_rows": {},
        "stdout_needles": [
            "Processed 0 scanner hit(s); 0 BET / 0 non-BET.",
            "Cleared 2 stale plan artifact(s).",
            "Cleared 1 stale prediction artifact(s).",
        ],
        "expectations": {
            "recommendation_count": 0,
            "stale_plan_artifacts_cleared": True,
            "stale_prediction_artifacts_cleared": True,
            "summary_text_needles": ["Races processed: 0", "BET decisions: 0", "NO BET decisions: 0"],
        },
    },
    {
        "name": "case_missing_race_id_yields_error_row",
        "scenario": "scanner hits with no race_id become explicit ERROR rows instead of disappearing from the recommender summary",
        "hits": [HIT_MISSING_RACE_ID],
        "prediction_rows": {},
        "stdout_needles": ["Processed 1 scanner hit(s); 0 BET / 1 non-BET."],
        "expectations": {
            "recommendation_count": 1,
            "decision": "ERROR",
            "filtered_combo_count": 0,
            "scored_combo_count": 0,
            "tickets_selected": 0,
            "reason_contains": "Scanner hit is missing race_id; cannot score recommendations.",
            "summary_text_needles": [
                "Oaklawn Park Race 7 (missing race_id) | ERROR",
                "Reason: Scanner hit is missing race_id; cannot score recommendations.",
            ],
        },
    },
    {
        "name": "case_phase7_filter_keeps_allowed_combo_only",
        "scenario": "default Phase 7 filtering still ignores off-universe combos and sizes only the allowed ticket set",
        "hits": [HIT_FILTERED],
        "prediction_rows": {
            HIT_FILTERED["race_id"]: [
                {"combo": "1-2-3-5", "jointProb": 0.02, "predicted_payout": 120.0, "rank": 1},
                {"combo": "9-2-3-5", "jointProb": 0.05, "predicted_payout": 80.0, "rank": 2},
                {"combo": "1-2-3-4", "jointProb": 0.03, "predicted_payout": 90.0, "rank": 3},
            ]
        },
        "stdout_needles": ["Processed 1 scanner hit(s); 1 BET / 0 non-BET."],
        "expectations": {
            "recommendation_count": 1,
            "decision": "BET",
            "filtered_combo_count": 1,
            "scored_combo_count": 3,
            "tickets_selected": 1,
            "ticket_combos": ["1-2-3-5"],
            "summary_text_needles": ["BET decisions: 1", "Oaklawn Park Race 7 (raceId=OP-2026-04-20-R7) | BET"],
        },
    },
    {
        "name": "case_default_filter_no_bet_when_universe_empty",
        "scenario": "default filtering still turns an off-universe-only race into an honest NO BET instead of sizing outside the scanner universe",
        "hits": [HIT_NO_UNIVERSE],
        "prediction_rows": {
            HIT_NO_UNIVERSE["race_id"]: [
                {"combo": "9-8-7-6", "jointProb": 0.08, "predicted_payout": 150.0, "rank": 1},
            ]
        },
        "stdout_needles": ["Processed 1 scanner hit(s); 0 BET / 1 non-BET."],
        "expectations": {
            "recommendation_count": 1,
            "decision": "NO BET",
            "filtered_combo_count": 0,
            "scored_combo_count": 1,
            "tickets_selected": 0,
            "reason_contains": "No rows were available in the prediction file.",
            "summary_text_needles": ["NO BET decisions: 1", "Reason: No rows were available in the prediction file."],
        },
    },
    {
        "name": "case_allow_all_combos_can_promote_bet",
        "scenario": "allow-all-combos still makes the override explicit by letting an off-universe combo become a BET recommendation",
        "hits": [HIT_NO_UNIVERSE],
        "prediction_rows": {
            HIT_NO_UNIVERSE["race_id"]: [
                {"combo": "9-8-7-6", "jointProb": 0.08, "predicted_payout": 150.0, "rank": 1},
            ]
        },
        "allow_all_combos": True,
        "stdout_needles": ["Processed 1 scanner hit(s); 1 BET / 0 non-BET."],
        "expectations": {
            "recommendation_count": 1,
            "decision": "BET",
            "filtered_combo_count": 1,
            "scored_combo_count": 1,
            "tickets_selected": 1,
            "ticket_combos": ["9-8-7-6"],
            "summary_text_needles": ["BET decisions: 1", "1. 9-8-7-6 | stake $3.70 | EV ROI 800.00%"],
        },
    },
    {
        "name": "case_malformed_prediction_file_yields_error_row",
        "scenario": "malformed prediction files still become explicit ERROR recommendations instead of killing the whole summary build",
        "hits": [HIT_MALFORMED],
        "prediction_rows": {
            HIT_MALFORMED["race_id"]: [
                {"jointProb": 0.03, "predicted_payout": 90.0, "rank": 1},
            ]
        },
        "stdout_needles": ["Processed 1 scanner hit(s); 0 BET / 1 non-BET."],
        "expectations": {
            "recommendation_count": 1,
            "decision": "ERROR",
            "filtered_combo_count": 0,
            "scored_combo_count": 0,
            "tickets_selected": 0,
            "reason_contains": "Prediction CSV is missing combo column",
            "summary_text_needles": ["NO BET decisions: 1", "| ERROR"],
        },
    },
]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_predictions(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def stale_plan_artifact_paths(output_dir: Path) -> list[Path]:
    plans_dir = output_dir / "plans"
    return [
        plans_dir / "race_STALE_plan.json",
        plans_dir / "race_STALE_plan.csv",
    ]


def stale_prediction_artifact_paths(output_dir: Path) -> list[Path]:
    predictions_dir = output_dir / "predictions"
    return [
        predictions_dir / "race_STALE_predictions.csv",
    ]


def write_stale_plan_artifacts(output_dir: Path) -> None:
    json_path, csv_path = stale_plan_artifact_paths(output_dir)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text('{"stale": true}\n', encoding="utf-8")
    csv_path.write_text("combo,recommended_stake\n1-2-3-4,9.90\n", encoding="utf-8")


def write_stale_prediction_artifacts(output_dir: Path) -> None:
    (csv_path,) = stale_prediction_artifact_paths(output_dir)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text("combo,jointProb,predicted_payout\n1-2-3-4,0.05,120.00\n", encoding="utf-8")


def guardrail(condition: bool, check: str, detail: str) -> dict[str, str]:
    if not condition:
        raise AssertionError(f"{check}: {detail}")
    return {"check": check, "status": "pass", "detail": detail}


def display_scorecard_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BASE.resolve()))
    except Exception:
        return str(path)


def require_positive_non_bool_int(value: Any, *, source_name: str, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, source_name: str, field_name: str) -> list[str]:
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
            "recommender fixtures and reused-prediction summaries do not count toward anchor-displacement, "
            "Phase 8 promotion-review, or real-money discussion gates"
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
    REPORT_MD = OUT_DIR / "paper_trade_recommender_validation.md"
    REPORT_JSON = OUT_DIR / "paper_trade_recommender_validation.json"


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
    return guardrail(True, check_name, detail)


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
            check_name="scorecard_boolean_gate_floor_fails_before_recommender_artifacts",
            detail=(
                "a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before "
                "the recommender validator creates fixture roots or report artifacts"
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
            check_name="scorecard_nonpositive_phase8_gate_floor_fails_before_recommender_artifacts",
            detail=(
                "a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails before "
                "the recommender validator creates fixture roots or report artifacts"
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
            check_name="scorecard_nonpositive_real_money_gate_floor_fails_before_recommender_artifacts",
            detail=(
                "a non-positive real-money discussion floor in forward_evidence_scorecard.json fails before "
                "the recommender validator creates fixture roots or report artifacts"
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
            check_name="scorecard_missing_no_baq_fails_before_recommender_artifacts",
            detail=(
                "a scorecard real-money gate that drops the no BAQ-as-BEL prerequisite fails before "
                "the recommender validator creates fixture roots or report artifacts"
            ),
        ),
    ]


def build_fixture_scratch_metadata() -> dict[str, Any]:
    return {
        "fixture_root": str(FIXTURE_ROOT),
        "fixture_root_relative": str(FIXTURE_ROOT.relative_to(BASE)),
        "fixture_root_is_project_local": FIXTURE_ROOT.is_relative_to(BASE),
        "case_roots_cleared_by_setup_case": True,
        "evidence_boundary": "paper-trade recommender fixture scratch metadata is reproducibility context only, not live model scoring, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
    }


def setup_case(case: dict[str, Any]) -> tuple[Path, Path, Path]:
    case_root = FIXTURE_ROOT / case["name"]
    if case_root.exists():
        shutil.rmtree(case_root)
    case_root.mkdir(parents=True, exist_ok=True)
    scan_input = case_root / "out" / "live_scan_latest.json"
    output_dir = case_root / "out" / "paper_trade_recommendations_latest"
    predictions_dir = output_dir / "predictions"
    write_json(scan_input, case["hits"])
    if case.get("initial_stale_plan_artifacts"):
        write_stale_plan_artifacts(output_dir)
    if case.get("initial_stale_prediction_artifacts"):
        write_stale_prediction_artifacts(output_dir)
    for race_id, rows in case.get("prediction_rows", {}).items():
        write_predictions(predictions_dir / f"race_{race_id}_predictions.csv", rows)
    return case_root, scan_input, output_dir


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_root, scan_input, output_dir = setup_case(case)
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--scan-input",
        str(scan_input),
        "--output-dir",
        str(output_dir),
    ]
    if case.get("reuse_predictions", True):
        cmd.append("--reuse-predictions")
    if case.get("allow_all_combos"):
        cmd.append("--allow-all-combos")

    result = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)
    (case_root / "stdout.txt").write_text(result.stdout, encoding="utf-8")
    (case_root / "stderr.txt").write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise AssertionError(f"{case['name']}: unexpected non-zero exit: {result.stderr}")
    for needle in case.get("stdout_needles", []):
        if needle not in result.stdout:
            raise AssertionError(f"{case['name']}: expected stdout to contain {needle!r}")
    scope_line = f"valid_evidence_scope={recommender_source.RECOMMENDER_VALID_EVIDENCE_SCOPE}"
    if scope_line not in result.stdout:
        raise AssertionError(f"{case['name']}: recommender stdout lost the source-level valid_evidence_scope")
    boundary_line = f"Evidence boundary: {recommender_source.RECOMMENDER_EVIDENCE_BOUNDARY_TEXT}"
    if boundary_line not in result.stdout:
        raise AssertionError(f"{case['name']}: recommender stdout lost the source-level evidence boundary")

    summary_json = output_dir / "recommendations_summary.json"
    summary_txt = output_dir / "recommendations_summary.txt"
    summary_csv = output_dir / "recommendations_summary.csv"
    if not summary_json.exists() or not summary_txt.exists() or not summary_csv.exists():
        raise AssertionError(f"{case['name']}: expected summary artifacts were not all created")

    recommendations = read_json(summary_json)
    expected = case["expectations"]
    if len(recommendations) != expected["recommendation_count"]:
        raise AssertionError(
            f"{case['name']}: expected {expected['recommendation_count']} recommendations, got {len(recommendations)}"
        )

    for idx, rec in enumerate(recommendations, 1):
        if rec.get("valid_evidence_scope") != recommender_source.RECOMMENDER_VALID_EVIDENCE_SCOPE:
            raise AssertionError(f"{case['name']}: recommendation {idx} lost valid_evidence_scope")
        if rec.get("evidence_boundary_text") != recommender_source.RECOMMENDER_EVIDENCE_BOUNDARY_TEXT:
            raise AssertionError(f"{case['name']}: recommendation {idx} lost evidence_boundary_text")
        boundary = rec.get("evidence_boundary")
        if not isinstance(boundary, dict):
            raise AssertionError(f"{case['name']}: recommendation {idx} lost machine-readable evidence_boundary")
        for flag in (
            "not_live_paper_trade_ledger",
            "not_settled_roi_evidence",
            "not_promotion_readiness_evidence",
            "not_live_profitability_evidence",
            "not_real_money_evidence",
            "requires_later_audit_or_forward_check_review_before_sample_gate_use",
        ):
            if boundary.get(flag) is not True:
                raise AssertionError(f"{case['name']}: recommendation {idx} evidence_boundary lost true {flag}")

    if recommendations:
        rec = recommendations[0]
        for key in ("decision", "filtered_combo_count", "scored_combo_count", "tickets_selected"):
            if key in expected and rec.get(key) != expected[key]:
                raise AssertionError(f"{case['name']}: expected {key}={expected[key]!r}, got {rec.get(key)!r}")
        if "ticket_combos" in expected:
            combos = [ticket.get("combo") for ticket in rec.get("tickets", [])]
            if combos != expected["ticket_combos"]:
                raise AssertionError(f"{case['name']}: expected ticket combos {expected['ticket_combos']!r}, got {combos!r}")
        if "reason_contains" in expected and expected["reason_contains"] not in str(rec.get("reason", "")):
            raise AssertionError(
                f"{case['name']}: expected reason to contain {expected['reason_contains']!r}, got {rec.get('reason')!r}"
            )

    summary_text = summary_txt.read_text(encoding="utf-8")
    if scope_line not in summary_text:
        raise AssertionError(f"{case['name']}: summary text lost the source-level valid_evidence_scope")
    if boundary_line not in summary_text:
        raise AssertionError(f"{case['name']}: summary text lost the source-level evidence boundary")
    for needle in expected.get("summary_text_needles", []):
        if needle not in summary_text:
            raise AssertionError(f"{case['name']}: expected summary text to contain {needle!r}")
    if recommendations:
        summary_df = pd.read_csv(summary_csv)
        if "valid_evidence_scope" not in summary_df.columns:
            raise AssertionError(f"{case['name']}: summary CSV lost valid_evidence_scope")
        csv_scope_values = set(summary_df["valid_evidence_scope"].astype(str))
        if csv_scope_values != {recommender_source.RECOMMENDER_VALID_EVIDENCE_SCOPE}:
            raise AssertionError(
                f"{case['name']}: summary CSV valid_evidence_scope values drifted: {csv_scope_values!r}"
            )
        if "evidence_boundary_text" not in summary_df.columns:
            raise AssertionError(f"{case['name']}: summary CSV lost evidence_boundary_text")
        csv_boundary_values = set(summary_df["evidence_boundary_text"].astype(str))
        if csv_boundary_values != {recommender_source.RECOMMENDER_EVIDENCE_BOUNDARY_TEXT}:
            raise AssertionError(
                f"{case['name']}: summary CSV evidence boundary values drifted: {csv_boundary_values!r}"
            )
    if expected.get("stale_plan_artifacts_cleared"):
        remaining = [str(path.relative_to(case_root)) for path in stale_plan_artifact_paths(output_dir) if path.exists()]
        if remaining:
            raise AssertionError(f"{case['name']}: stale plan artifacts were not cleared: {remaining}")
    if expected.get("stale_prediction_artifacts_cleared"):
        remaining = [str(path.relative_to(case_root)) for path in stale_prediction_artifact_paths(output_dir) if path.exists()]
        if remaining:
            raise AssertionError(f"{case['name']}: stale prediction artifacts were not cleared: {remaining}")

    return {
        "name": case["name"],
        "scenario": case["scenario"],
        "result": "PASS",
        "summary_json": str(summary_json.relative_to(BASE)),
        "stdout": str((case_root / "stdout.txt").relative_to(BASE)),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_output_paths(args.fixture_root, args.out_dir)
    scorecard_gates = read_scorecard_gate_minimums(args.scorecard_json)
    scorecard_guardrails = scorecard_no_artifact_guardrails(args.scorecard_json)

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for legacy in (
        FIXTURE_ROOT / "paper_trade_recommender_fixture_validation.md",
        FIXTURE_ROOT / "paper_trade_recommender_fixture_validation.json",
    ):
        legacy.unlink(missing_ok=True)

    results = [run_case(case) for case in CASES]
    recs_by_case = {row["name"]: read_json(BASE / row["summary_json"]) for row in results}
    scratch = build_fixture_scratch_metadata()
    current_read = f"paper-trade recommender still preserves the default Phase 7 combo filter, keeps off-universe-only races as honest NO BETs, allows the explicit allow-all-combos override to widen the ticket universe when requested, turns missing race_id scanner hits and malformed prediction files into ERROR rows instead of letting scanner hits disappear or aborting the whole summary build, writes stable summary artifacts even when the scan input is empty, clears stale plan artifacts and non-reuse prediction CSVs on direct empty reruns so old tickets or scored-race context cannot survive as current plan/prediction files, prints source-level valid_evidence_scope plus evidence-boundary lines in successful CLI and text-summary output, exposes exact valid_evidence_scope={recommender_source.RECOMMENDER_VALID_EVIDENCE_SCOPE} in the direct validator report as recommendation/sizing metadata only, carries source-level valid_evidence_scope plus machine-readable evidence-boundary fields in non-empty recommendation JSON rows, carries valid_evidence_scope plus evidence-boundary text in non-empty summary CSV rows, rejects malformed and non-positive scorecard gates before fixture/report artifacts, publishes project-local fixture scratch metadata, preserves the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that reused-prediction fixtures do not advance, and now publishes its direct validator report at the standard paper-trade-recommender validation path; this is mostly reused-prediction source-layer reproducibility plus one no-reuse cleanup check, not live model scoring, promotion, settled ROI, live profitability, or real-money evidence"
    child_checks = [
        *scorecard_guardrails,
        guardrail(
            recs_by_case["case_empty_scan_input"] == [],
            "empty_scan_input_writes_stable_empty_artifacts",
            "empty scan inputs still write stable JSON/TXT/CSV summary artifacts, clear stale per-race plan files plus non-reuse prediction CSVs, and do not try to score nonexistent races",
        ),
        guardrail(
            len(recs_by_case["case_missing_race_id_yields_error_row"]) == 1
            and recs_by_case["case_missing_race_id_yields_error_row"][0].get("decision") == "ERROR"
            and "Scanner hit is missing race_id" in str(recs_by_case["case_missing_race_id_yields_error_row"][0].get("reason", ""))
            and recs_by_case["case_missing_race_id_yields_error_row"][0].get("race_id") == ""
            and recs_by_case["case_missing_race_id_yields_error_row"][0].get("tickets_selected") == 0,
            "missing_race_id_hits_become_per_hit_error_rows",
            "scanner hits that lack race_id now produce explicit per-hit ERROR recommendation rows instead of disappearing from the summary artifacts",
        ),
        guardrail(
            len(recs_by_case["case_phase7_filter_keeps_allowed_combo_only"]) == 1
            and recs_by_case["case_phase7_filter_keeps_allowed_combo_only"][0].get("decision") == "BET"
            and recs_by_case["case_phase7_filter_keeps_allowed_combo_only"][0].get("filtered_combo_count") == 1
            and recs_by_case["case_phase7_filter_keeps_allowed_combo_only"][0].get("scored_combo_count") == 3
            and [ticket.get("combo") for ticket in recs_by_case["case_phase7_filter_keeps_allowed_combo_only"][0].get("tickets", [])] == ["1-2-3-5"],
            "default_phase7_filter_stays_inside_scanner_combo_universe",
            "the default recommender path still sizes only the scanner-approved Phase 7 ticket universe instead of widening to all model-scored combos",
        ),
        guardrail(
            len(recs_by_case["case_default_filter_no_bet_when_universe_empty"]) == 1
            and recs_by_case["case_default_filter_no_bet_when_universe_empty"][0].get("decision") == "NO BET"
            and recs_by_case["case_default_filter_no_bet_when_universe_empty"][0].get("filtered_combo_count") == 0
            and recs_by_case["case_default_filter_no_bet_when_universe_empty"][0].get("tickets_selected") == 0
            and len(recs_by_case["case_allow_all_combos_can_promote_bet"]) == 1
            and recs_by_case["case_allow_all_combos_can_promote_bet"][0].get("decision") == "BET"
            and [ticket.get("combo") for ticket in recs_by_case["case_allow_all_combos_can_promote_bet"][0].get("tickets", [])] == ["9-8-7-6"],
            "off_universe_predictions_stay_no_bet_unless_override_is_explicit",
            "off-universe-only prediction rows remain honest NO BETs by default, and the allow-all-combos widening path is only accepted when the explicit override is present",
        ),
        guardrail(
            len(recs_by_case["case_malformed_prediction_file_yields_error_row"]) == 1
            and recs_by_case["case_malformed_prediction_file_yields_error_row"][0].get("decision") == "ERROR"
            and "Prediction CSV is missing combo column" in str(recs_by_case["case_malformed_prediction_file_yields_error_row"][0].get("reason", ""))
            and recs_by_case["case_malformed_prediction_file_yields_error_row"][0].get("tickets_selected") == 0,
            "malformed_prediction_files_become_per_race_error_rows",
            "malformed prediction files still produce explicit per-race ERROR recommendation rows instead of aborting the whole consolidated summary build",
        ),
        guardrail(
            scratch.get("fixture_root_relative") == "out/status_validation/paper_trade_recommender_fixture"
            and scratch.get("fixture_root_is_project_local") is True
            and scratch.get("case_roots_cleared_by_setup_case") is True,
            "fixture_scratch_metadata_published",
            "the direct recommender validator now publishes project-local fixture scratch metadata so parent rollups can verify isolated recommender-fixture hygiene without parsing markdown prose",
        ),
        guardrail(
            "mostly reused-prediction source-layer reproducibility plus one no-reuse cleanup check" in current_read
            and "prints source-level valid_evidence_scope plus evidence-boundary lines" in current_read
            and f"valid_evidence_scope={recommender_source.RECOMMENDER_VALID_EVIDENCE_SCOPE}" in current_read
            and EVIDENCE_BOUNDARY.get("valid_evidence_scope") == recommender_source.RECOMMENDER_VALID_EVIDENCE_SCOPE
            and "not live model scoring, promotion, settled ROI, live profitability, or real-money evidence" in current_read,
            "recommender_validator_stays_reuse_fixture_not_new_evidence",
            "the direct recommender validator summary now frames a green reused-prediction fixture sweep plus a no-reuse cleanup check as source-layer reproducibility, exposes the exact raw valid_evidence_scope in its own report, and keeps every successful stdout/text summary plus non-empty JSON/CSV payload carrying source-level valid_evidence_scope plus evidence-boundary metadata rather than live scoring, promotion, settled ROI, live profitability, or real-money evidence",
        ),
        guardrail(
            scorecard_gates.get("source") == "forward_evidence_scorecard.json"
            and scorecard_gates.get("source_path") == "decision_gate_minimums"
            and scorecard_gates.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and scorecard_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and scorecard_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and scorecard_gates.get("real_money_no_baq_as_bel_required") is True
            and "no BAQ-as-BEL substitution" in scorecard_gates.get("real_money_also_requires", []),
            "recommender_preserves_scorecard_gate_boundary",
            "the direct recommender validator now reads forward_evidence_scorecard.json decision_gate_minimums and publishes the 30-row anchor-review floor, 20-row Phase 8 review floor, 100-row real-money discussion floor, and no-BAQ-as-BEL prerequisite as source-layer boundary metadata only",
        ),
    ]

    payload = {
        "suite_status": "pass",
        "artifact_status": "pass",
        "valid_evidence_scope": recommender_source.RECOMMENDER_VALID_EVIDENCE_SCOPE,
        "total_fixture_scenarios": len(results),
        "total_checks": len(results),
        "check_count": len(results),
        "child_check_count": len(child_checks),
        "child_checks": child_checks,
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
        "# Paper-Trade Recommender Validation",
        "",
        "This report validates `paper_trade_recommender.py` directly inside isolated reused-prediction fixtures while publishing the saved validator artifact at the standard paper-trade-recommender report path.",
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
        "| Case | Scenario | Summary artifact |",
        "|---|---|---|",
    ]
    for row in results:
        lines.append(f"| `{row['name']}` | {row['scenario']} | `{row['summary_json']}` |")

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
        f"- valid_evidence_scope={recommender_source.RECOMMENDER_VALID_EVIDENCE_SCOPE}",
        "- Validator passes, reused prediction artifacts, off-universe `NO BET` rows, `ERROR` rows, and `--allow-all-combos` fixtures are source-layer metadata only.",
        f"- Successful recommender CLI/text output now carries `valid_evidence_scope={recommender_source.RECOMMENDER_VALID_EVIDENCE_SCOPE}` plus a source-level evidence boundary, and non-empty recommendation JSON/CSV rows carry the same scope plus machine-readable or row-level boundary fields.",
        "- They are not settled ROI, live profitability, promotion readiness, live model-scoring proof, or real-money evidence.",
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
        "- Empty scan inputs still produce stable empty summary artifacts and clear stale per-race plan files plus non-reuse prediction CSVs instead of trying to score nonexistent races or leaving old tickets/scored-race context behind.",
        "- Scanner hits missing `race_id` now become explicit per-hit `ERROR` rows instead of disappearing from the summary artifacts.",
        "- Default Phase 7 filtering still keeps the recommender inside the scanner's allowed ticket universe.",
        "- Off-universe-only prediction files still become honest `NO BET` results unless the explicit `--allow-all-combos` override is used.",
        "- The explicit override still widens the ticket universe when requested, so the selective-rule guardrail is both testable and intentional.",
        "- Malformed prediction files still turn into per-race `ERROR` rows instead of killing the whole consolidated summary build.",
        "- Malformed and non-positive scorecard gates now fail before recommender fixture roots or report artifacts are created, so a weakened decision-gate sidecar cannot produce green-looking source-layer recommendation reports.",
        "",
        "## Sources",
        "",
    ])
    for row in results:
        lines.append(f"- `{row['stdout']}`")
        lines.append(f"- `{row['summary_json']}`")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    for row in results:
        print(f"PASS {row['name']}: {row['summary_json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
