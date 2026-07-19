#!/usr/bin/env python3
"""
Fixture-driven validation for paper_trade_logger.py.

Purpose:
- pin the persistent paper-trade ledger append contract directly at the source layer
- keep signal / recommendation dedup behavior reproducible
- verify the real CLI still writes stable ledgers and state files under empty, new-row, and malformed-state cases
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import paper_trade_logger as logger_source

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "paper_trade_logger.py"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "paper_trade_logger_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_logger"
REPORT_MD = OUT_DIR / "paper_trade_logger_validation.md"
REPORT_JSON = OUT_DIR / "paper_trade_logger_validation.json"
REBUILD_COMMAND = "python3 validate_paper_trade_logger.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade logger validator",
    "source_valid_evidence_scope": logger_source.LOGGER_VALID_EVIDENCE_SCOPE,
    "valid_evidence_scope": logger_source.LOGGER_VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "paper_trade_logger.py isolated ledger fixtures",
        "forward_evidence_scorecard.json decision_gate_minimums",
    ],
    "valid_use": "source-layer ledger append and dedup reproducibility validation",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "logger_validator_passes_are_source_layer_metadata_only": True,
    "logger_validator_passes_are_ledger_metadata_only": True,
}

SIGNAL_FIELDS = [
    "signal_key",
    "scan_ts",
    "rule_id",
    "track",
    "card_name",
    "race_number",
    "race_id",
    "surface",
    "condition",
    "field_size",
    "favorite_program",
    "favorite_name",
    "favorite_prob",
    "second_prob",
    "prob_gap",
    "k",
    "base_stake",
    "estimated_cost",
    "underneath_programs",
    "ticket_structure",
    "status",
    "outcome",
    "notes",
]

RECOMMENDATION_FIELDS = [
    "signal_key",
    "run_ts",
    "rule_id",
    "track",
    "card_name",
    "race_number",
    "race_id",
    "decision",
    "reason",
    "favorite_program",
    "underneath_programs",
    "scanner_estimated_cost",
    "scored_combo_count",
    "filtered_combo_count",
    "bankroll",
    "race_risk_budget",
    "total_stake",
    "total_expected_return",
    "total_expected_profit",
    "portfolio_expected_roi_pct",
    "tickets_selected",
    "tickets_json",
    "prediction_csv",
    "plan_json",
    "plan_csv",
    "status",
    "outcome",
    "notes",
]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def guardrail(condition: bool, check: str, detail: str) -> dict[str, str]:
    if not condition:
        raise AssertionError(f"{check}: {detail}")
    return {"check": check, "status": "pass", "detail": detail}


def require_positive_non_bool_int(value: Any, *, source_name: str, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, source_name: str, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise AssertionError(f"{source_name} {field_name} must be a list of non-empty strings")
    return value


def read_scorecard_gate_minimums(scorecard_json_path: Path = SCORECARD_JSON) -> dict[str, Any]:
    source_path = Path(scorecard_json_path)
    source_name = source_path.name
    payload = json.loads(source_path.read_text(encoding="utf-8"))
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
        "source": source_name,
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_also_requires": real_money_requires,
        "real_money_no_baq_as_bel_required": True,
        "evidence_boundary": (
            "logger fixture ledgers, append rows, dedup state files, and validator passes do not count toward "
            "anchor-displacement, Phase 8 promotion-review, or real-money discussion gates"
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def scorecard_gate_cli_contract_checks(scorecard_json_path: Path = SCORECARD_JSON) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    with TemporaryDirectory(prefix="paper_trade_logger_scorecard_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(scorecard_json_path).read_text(encoding="utf-8"))
        scorecard_path = tmp_root / "forward_evidence_scorecard.json"
        bad_out_dir = tmp_root / "nested" / "paper_trade_logger_validation"

        bool_payload = json.loads(json.dumps(base_payload))
        bool_payload["decision_gate_minimums"]["anchor_displacement"][
            "min_roi_complete_settled_observations"
        ] = True
        scorecard_path.write_text(json.dumps(bool_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(scorecard_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            guardrail(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations must be a positive non-boolean integer" in proc.stderr,
                "scorecard_boolean_gate_floor_fails_before_logger_artifacts",
                "a malformed boolean anchor-displacement scorecard gate fails before nested logger validation outputs are created",
            )
        )

        nonpositive_phase8_payload = json.loads(json.dumps(base_payload))
        nonpositive_phase8_payload["decision_gate_minimums"]["phase8_promotion_review"][
            "min_roi_complete_settled_observations"
        ] = 0
        scorecard_path.write_text(json.dumps(nonpositive_phase8_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(scorecard_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            guardrail(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer" in proc.stderr,
                "scorecard_nonpositive_phase8_gate_floor_fails_before_logger_artifacts",
                "a non-positive Phase 8 promotion-review scorecard gate fails before nested logger validation outputs are created",
            )
        )

        nonpositive_real_money_payload = json.loads(json.dumps(base_payload))
        nonpositive_real_money_payload["decision_gate_minimums"]["real_money_discussion"][
            "min_total_settled_observations_with_usable_roi"
        ] = 0
        scorecard_path.write_text(json.dumps(nonpositive_real_money_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(scorecard_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            guardrail(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer" in proc.stderr,
                "scorecard_nonpositive_real_money_gate_floor_fails_before_logger_artifacts",
                "a non-positive real-money discussion scorecard gate fails before nested logger validation outputs are created",
            )
        )

        missing_no_baq_payload = json.loads(json.dumps(base_payload))
        missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"]["also_requires"] = [
            requirement
            for requirement in missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"].get(
                "also_requires",
                [],
            )
            if requirement != NO_BAQ_AS_BEL_PREREQUISITE
        ]
        scorecard_path.write_text(json.dumps(missing_no_baq_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(scorecard_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            guardrail(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.real_money_discussion.also_requires must include no BAQ-as-BEL substitution" in proc.stderr,
                "scorecard_missing_no_baq_fails_before_logger_artifacts",
                "a scorecard gate missing the no-BAQ-as-BEL real-money prerequisite fails before nested logger validation outputs are created",
            )
        )
    return checks


def build_fixture_scratch_metadata() -> dict[str, Any]:
    return {
        "fixture_root": str(FIXTURE_ROOT),
        "fixture_root_relative": str(FIXTURE_ROOT.relative_to(BASE)),
        "fixture_root_is_project_local": FIXTURE_ROOT.is_relative_to(BASE),
        "case_roots_cleared_by_setup_case": True,
        "evidence_boundary": (
            "paper-trade logger fixture scratch metadata is ledger reproducibility context only, "
            "not a live paper-trade ledger read, settled ROI, promotion readiness, live profitability, "
            "bankroll guidance, or real-money evidence"
        ),
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
    favorite_name: str = "Anchor Favorite",
    underneath_programs: list[str] | None = None,
    estimated_cost: str = "24.00",
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
        "favorite_name": favorite_name,
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


def recommendation_row(key: str, *, run_ts: str = "2026-04-20T12:00:00", decision: str = "BET") -> dict[str, Any]:
    return {
        "signal_key": key,
        "run_ts": run_ts,
        "rule_id": "OP_DURABLE_K7",
        "track": "OP",
        "card_name": "Oaklawn Park",
        "race_number": "7",
        "race_id": "OP-2026-04-20-R7",
        "decision": decision,
        "reason": "positive EV",
        "favorite_program": "1",
        "underneath_programs": ["2", "3", "5"],
        "scanner_estimated_cost": "24.00",
        "scored_combo_count": 200,
        "filtered_combo_count": 6,
        "bankroll": 500.0,
        "race_risk_budget": 10.0,
        "total_stake": 4.2,
        "total_expected_return": 6.4,
        "total_expected_profit": 2.2,
        "portfolio_expected_roi_pct": 52.38,
        "tickets_selected": 2,
        "tickets": [
            {"combo": "1-2-3-5", "recommended_stake": 2.1, "ev_roi_pct": 55.0},
            {"combo": "1-2-5-3", "recommended_stake": 2.1, "ev_roi_pct": 49.7},
        ],
        "prediction_csv": "out/paper_trade_recommendations_latest/predictions/race_OP-2026-04-20-R7_predictions.csv",
        "plan_json": "out/paper_trade_recommendations_latest/plans/race_OP-2026-04-20-R7_plan.json",
        "plan_csv": "out/paper_trade_recommendations_latest/plans/race_OP-2026-04-20-R7_plan.csv",
    }


def expected_signal_ledger_row(hit: dict[str, Any]) -> dict[str, str]:
    return {
        "signal_key": signal_key(hit),
        "scan_ts": str(hit.get("scan_ts", "")),
        "rule_id": str(hit.get("rule_id", "")),
        "track": str(hit.get("track", "")),
        "card_name": str(hit.get("card_name", "")),
        "race_number": str(hit.get("race_number", "")),
        "race_id": str(hit.get("race_id", "")),
        "surface": str(hit.get("surface", "")),
        "condition": str(hit.get("condition", "")),
        "field_size": str(hit.get("field_size", "")),
        "favorite_program": str(hit.get("favorite_program", "")),
        "favorite_name": str(hit.get("favorite_name", "")),
        "favorite_prob": str(hit.get("favorite_prob", "")),
        "second_prob": str(hit.get("second_prob", "")),
        "prob_gap": str(hit.get("prob_gap", "")),
        "k": str(hit.get("k", "")),
        "base_stake": str(hit.get("base_stake", "")),
        "estimated_cost": str(hit.get("estimated_cost", "")),
        "underneath_programs": json.dumps(hit.get("underneath_programs", [])),
        "ticket_structure": str(hit.get("ticket_structure", "")),
        "status": "open",
        "outcome": "",
        "notes": "",
    }


def expected_recommendation_ledger_row(rec: dict[str, Any]) -> dict[str, str]:
    return {
        "signal_key": str(rec.get("signal_key", "")),
        "run_ts": str(rec.get("run_ts", "")),
        "rule_id": str(rec.get("rule_id", "")),
        "track": str(rec.get("track", "")),
        "card_name": str(rec.get("card_name", "")),
        "race_number": str(rec.get("race_number", "")),
        "race_id": str(rec.get("race_id", "")),
        "decision": str(rec.get("decision", "")),
        "reason": str(rec.get("reason", "")),
        "favorite_program": str(rec.get("favorite_program", "")),
        "underneath_programs": json.dumps(rec.get("underneath_programs", [])),
        "scanner_estimated_cost": str(rec.get("scanner_estimated_cost", "")),
        "scored_combo_count": str(rec.get("scored_combo_count", "")),
        "filtered_combo_count": str(rec.get("filtered_combo_count", "")),
        "bankroll": str(rec.get("bankroll", "")),
        "race_risk_budget": str(rec.get("race_risk_budget", "")),
        "total_stake": str(rec.get("total_stake", "")),
        "total_expected_return": str(rec.get("total_expected_return", "")),
        "total_expected_profit": str(rec.get("total_expected_profit", "")),
        "portfolio_expected_roi_pct": str(rec.get("portfolio_expected_roi_pct", "")),
        "tickets_selected": str(rec.get("tickets_selected", "")),
        "tickets_json": json.dumps(rec.get("tickets", [])),
        "prediction_csv": str(rec.get("prediction_csv", "")),
        "plan_json": str(rec.get("plan_json", "")),
        "plan_csv": str(rec.get("plan_csv", "")),
        "status": "open",
        "outcome": "",
        "notes": "",
    }


HIT_A = signal_hit("2026-04-20T11:00:00", "OP_DURABLE_K7", "OP-2026-04-20-R7", "1")
HIT_B = signal_hit(
    "2026-04-20T11:05:00",
    "CD_CORE_K8",
    "CD-2026-04-20-R8",
    "4",
    track="CD",
    card_name="Churchill Downs",
    race_number="8",
    favorite_name="Core Favorite",
    underneath_programs=["1", "6", "8"],
    estimated_cost="36.00",
)
REC_A = recommendation_row(signal_key(HIT_A))
REC_B = {
    **recommendation_row(signal_key(HIT_B), run_ts="2026-04-20T12:05:00", decision="NO BET"),
    "rule_id": "CD_CORE_K8",
    "track": "CD",
    "card_name": "Churchill Downs",
    "race_number": "8",
    "race_id": "CD-2026-04-20-R8",
    "favorite_program": "4",
    "underneath_programs": ["1", "6", "8"],
    "scanner_estimated_cost": "36.00",
    "reason": "filtered EV below threshold",
    "filtered_combo_count": 4,
    "total_stake": 0.0,
    "total_expected_return": 0.0,
    "total_expected_profit": 0.0,
    "portfolio_expected_roi_pct": 0.0,
    "tickets_selected": 0,
    "tickets": [],
    "prediction_csv": "out/paper_trade_recommendations_latest/predictions/race_CD-2026-04-20-R8_predictions.csv",
    "plan_json": "out/paper_trade_recommendations_latest/plans/race_CD-2026-04-20-R8_plan.json",
    "plan_csv": "",
}


CASES: list[dict[str, Any]] = [
    {
        "name": "case_empty_inputs_create_headers_only",
        "scenario": "empty signal and recommendation inputs still create stable ledgers plus empty dedup state files",
        "hits": [],
        "recommendations": [],
        "stdout_needles": [
            "Logged 0 new paper-trade signal(s)",
            "Logged 0 new recommendation row(s)",
        ],
        "expected_signal_rows": [],
        "expected_recommendation_rows": [],
        "expected_signal_state": {"logged": []},
        "expected_recommendation_state": {"logged": []},
    },
    {
        "name": "case_new_rows_append_and_serialize_payloads",
        "scenario": "new hits and recommendations still append one row each with stable serialized list payloads and open status fields",
        "hits": [HIT_A],
        "recommendations": [REC_A],
        "stdout_needles": [
            "Logged 1 new paper-trade signal(s)",
            "Logged 1 new recommendation row(s)",
        ],
        "expected_signal_rows": [expected_signal_ledger_row(HIT_A)],
        "expected_recommendation_rows": [expected_recommendation_ledger_row(REC_A)],
        "expected_signal_state": {"logged": [signal_key(HIT_A)]},
        "expected_recommendation_state": {"logged": [signal_key(HIT_A)]},
    },
    {
        "name": "case_existing_state_dedups_old_rows_and_only_appends_new",
        "scenario": "existing state files still prevent duplicate appends while allowing new signal keys through",
        "hits": [HIT_A, HIT_B],
        "recommendations": [REC_A, REC_B],
        "pre_signal_rows": [expected_signal_ledger_row(HIT_A)],
        "pre_recommendation_rows": [expected_recommendation_ledger_row(REC_A)],
        "pre_signal_state": {"logged": [signal_key(HIT_A)]},
        "pre_recommendation_state": {"logged": [signal_key(HIT_A)]},
        "stdout_needles": [
            "Logged 1 new paper-trade signal(s)",
            "Logged 1 new recommendation row(s)",
        ],
        "expected_signal_rows": [expected_signal_ledger_row(HIT_A), expected_signal_ledger_row(HIT_B)],
        "expected_recommendation_rows": [expected_recommendation_ledger_row(REC_A), expected_recommendation_ledger_row(REC_B)],
        "expected_signal_state": {"logged": sorted([signal_key(HIT_A), signal_key(HIT_B)])},
        "expected_recommendation_state": {"logged": sorted([signal_key(HIT_A), signal_key(HIT_B)])},
    },
    {
        "name": "case_malformed_state_and_blank_recommendation_key",
        "scenario": "malformed state JSON still rebuilds dedup from existing ledgers, appends only new keys, and ignores blank recommendation keys",
        "hits": [HIT_A, HIT_B],
        "recommendations": [{"signal_key": "", "decision": "BET"}, REC_A, REC_B],
        "pre_signal_rows": [expected_signal_ledger_row(HIT_A)],
        "pre_recommendation_rows": [expected_recommendation_ledger_row(REC_A)],
        "raw_signal_state": "{not valid json\n",
        "raw_recommendation_state": "{not valid json\n",
        "stdout_needles": [
            "Logged 1 new paper-trade signal(s)",
            "Logged 1 new recommendation row(s)",
        ],
        "expected_signal_rows": [expected_signal_ledger_row(HIT_A), expected_signal_ledger_row(HIT_B)],
        "expected_recommendation_rows": [expected_recommendation_ledger_row(REC_A), expected_recommendation_ledger_row(REC_B)],
        "expected_signal_state": {"logged": sorted([signal_key(HIT_A), signal_key(HIT_B)])},
        "expected_recommendation_state": {"logged": sorted([signal_key(HIT_A), signal_key(HIT_B)])},
    },
]


def compare_rows(actual: list[dict[str, str]], expected: list[dict[str, str]], case_name: str, label: str) -> None:
    if actual != expected:
        raise AssertionError(
            f"{case_name}: {label} mismatch\nactual={json.dumps(actual, indent=2)}\nexpected={json.dumps(expected, indent=2)}"
        )


def compare_json(actual: Any, expected: Any, case_name: str, label: str) -> None:
    if actual != expected:
        raise AssertionError(
            f"{case_name}: {label} mismatch\nactual={json.dumps(actual, indent=2)}\nexpected={json.dumps(expected, indent=2)}"
        )


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_root = FIXTURE_ROOT / case["name"]
    if case_root.exists():
        shutil.rmtree(case_root)
    case_root.mkdir(parents=True, exist_ok=True)

    signal_input = case_root / "out" / "live_scan_latest.json"
    rec_input = case_root / "out" / "paper_trade_recommendations_latest" / "recommendations_summary.json"
    signal_ledger = case_root / "paper_trades" / "paper_trade_signals.csv"
    signal_state = case_root / "paper_trades" / ".logged_signals.json"
    rec_ledger = case_root / "paper_trades" / "paper_trade_recommendations.csv"
    rec_state = case_root / "paper_trades" / ".logged_recommendations.json"

    write_json(signal_input, case["hits"])
    write_json(rec_input, case["recommendations"])

    if case.get("pre_signal_rows") is not None:
        write_csv(signal_ledger, SIGNAL_FIELDS, case["pre_signal_rows"])
    if case.get("pre_recommendation_rows") is not None:
        write_csv(rec_ledger, RECOMMENDATION_FIELDS, case["pre_recommendation_rows"])
    if case.get("pre_signal_state") is not None:
        write_json(signal_state, case["pre_signal_state"])
    if case.get("pre_recommendation_state") is not None:
        write_json(rec_state, case["pre_recommendation_state"])
    if case.get("raw_signal_state") is not None:
        write_text(signal_state, case["raw_signal_state"])
    if case.get("raw_recommendation_state") is not None:
        write_text(rec_state, case["raw_recommendation_state"])

    cmd = [
        sys.executable,
        str(SCRIPT),
        "--input",
        str(signal_input),
        "--ledger",
        str(signal_ledger),
        "--state",
        str(signal_state),
        "--recommendations-input",
        str(rec_input),
        "--recommendation-ledger",
        str(rec_ledger),
        "--recommendation-state",
        str(rec_state),
    ]
    result = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)
    (case_root / "stdout.txt").write_text(result.stdout, encoding="utf-8")
    (case_root / "stderr.txt").write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise AssertionError(f"{case['name']}: unexpected non-zero exit: {result.stderr}")

    for needle in case["stdout_needles"]:
        if needle not in result.stdout:
            raise AssertionError(f"{case['name']}: expected stdout to contain {needle!r}")
    for boundary_text in (
        f"valid_evidence_scope={logger_source.LOGGER_VALID_EVIDENCE_SCOPE}",
        logger_source.LOGGER_EVIDENCE_BOUNDARY_TEXT,
        "not settled ROI evidence",
        "not real-money support",
    ):
        if boundary_text not in result.stdout:
            raise AssertionError(f"{case['name']}: logger stdout lost boundary text {boundary_text!r}")

    compare_rows(read_csv(signal_ledger), case["expected_signal_rows"], case["name"], "signal ledger")
    compare_rows(read_csv(rec_ledger), case["expected_recommendation_rows"], case["name"], "recommendation ledger")
    compare_json(read_json(signal_state), case["expected_signal_state"], case["name"], "signal state")
    compare_json(read_json(rec_state), case["expected_recommendation_state"], case["name"], "recommendation state")

    return {
        "name": case["name"],
        "scenario": case["scenario"],
        "result": "PASS",
        "signal_ledger": str(signal_ledger.relative_to(BASE)),
        "signal_state": str(signal_state.relative_to(BASE)),
        "recommendation_ledger": str(rec_ledger.relative_to(BASE)),
        "recommendation_state": str(rec_state.relative_to(BASE)),
        "stdout": str((case_root / "stdout.txt").relative_to(BASE)),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    scorecard_gates = read_scorecard_gate_minimums(args.scorecard_json)
    scorecard_cli_checks = scorecard_gate_cli_contract_checks(args.scorecard_json)
    out_dir = Path(args.out_dir)
    report_md = out_dir / "paper_trade_logger_validation.md"
    report_json = out_dir / "paper_trade_logger_validation.json"

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    for legacy in (
        FIXTURE_ROOT / "paper_trade_logger_fixture_validation.md",
        FIXTURE_ROOT / "paper_trade_logger_fixture_validation.json",
    ):
        legacy.unlink(missing_ok=True)

    results = [run_case(case) for case in CASES]
    result_map = {row["name"]: row for row in results}
    signal_rows_by_case = {
        name: read_csv(BASE / row["signal_ledger"])
        for name, row in result_map.items()
    }
    recommendation_rows_by_case = {
        name: read_csv(BASE / row["recommendation_ledger"])
        for name, row in result_map.items()
    }
    signal_state_by_case = {
        name: read_json(BASE / row["signal_state"])
        for name, row in result_map.items()
    }
    recommendation_state_by_case = {
        name: read_json(BASE / row["recommendation_state"])
        for name, row in result_map.items()
    }
    scratch = build_fixture_scratch_metadata()
    current_read = "paper-trade logger still creates stable signal and recommendation ledgers on empty runs, appends new rows with serialized list payloads, dedups previously logged signal keys via state files plus existing ledger rows, tolerates malformed state by rebuilding dedup from the ledger before appending only new keys, ignores blank recommendation keys instead of polluting the ledger, prints source-level valid_evidence_scope plus evidence-boundary lines in successful CLI output, publishes project-local fixture scratch metadata, exposes exact valid_evidence_scope=paper_trade_logger_append_dedup_metadata_only as direct validator-report metadata only, rejects malformed/non-positive scorecard gates before fixture/report artifacts, preserves the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that fixture ledgers and state files do not advance, and now publishes its direct validator report at the standard paper-trade-logger validation path; this is a source-layer ledger reproducibility check, not settlement-complete ROI, promotion, live profitability, or real-money evidence"
    child_checks = [
        *scorecard_cli_checks,
        guardrail(
            signal_rows_by_case["case_empty_inputs_create_headers_only"] == []
            and recommendation_rows_by_case["case_empty_inputs_create_headers_only"] == []
            and signal_state_by_case["case_empty_inputs_create_headers_only"] == {"logged": []}
            and recommendation_state_by_case["case_empty_inputs_create_headers_only"] == {"logged": []},
            "empty_inputs_create_header_only_ledgers_and_empty_states",
            "empty signal and recommendation inputs still create stable header-only ledgers plus empty dedup state files instead of leaving downstream append targets undefined",
        ),
        guardrail(
            len(signal_rows_by_case["case_new_rows_append_and_serialize_payloads"]) == 1
            and len(recommendation_rows_by_case["case_new_rows_append_and_serialize_payloads"]) == 1
            and signal_rows_by_case["case_new_rows_append_and_serialize_payloads"][0].get("status") == "open"
            and recommendation_rows_by_case["case_new_rows_append_and_serialize_payloads"][0].get("status") == "open"
            and recommendation_rows_by_case["case_new_rows_append_and_serialize_payloads"][0].get("tickets_json", "").startswith("[")
            and signal_rows_by_case["case_new_rows_append_and_serialize_payloads"][0].get("underneath_programs", "").startswith("["),
            "new_rows_append_serialized_payloads_with_open_status_fields",
            "new signal and recommendation rows still append with serialized list payloads and open status/outcome fields that settlement and monitoring tools can update later",
        ),
        guardrail(
            [row.get("signal_key") for row in signal_rows_by_case["case_existing_state_dedups_old_rows_and_only_appends_new"]] == [signal_key(HIT_A), signal_key(HIT_B)]
            and [row.get("signal_key") for row in recommendation_rows_by_case["case_existing_state_dedups_old_rows_and_only_appends_new"]] == [signal_key(HIT_A), signal_key(HIT_B)]
            and signal_state_by_case["case_existing_state_dedups_old_rows_and_only_appends_new"] == {"logged": sorted([signal_key(HIT_A), signal_key(HIT_B)])}
            and recommendation_state_by_case["case_existing_state_dedups_old_rows_and_only_appends_new"] == {"logged": sorted([signal_key(HIT_A), signal_key(HIT_B)])},
            "existing_state_dedups_old_keys_and_allows_new_keys",
            "existing dedup state still blocks duplicate signal keys while allowing genuinely new signal/recommendation keys through and preserving sorted state files",
        ),
        guardrail(
            len(signal_rows_by_case["case_malformed_state_and_blank_recommendation_key"]) == 2
            and len(recommendation_rows_by_case["case_malformed_state_and_blank_recommendation_key"]) == 2
            and [row.get("signal_key") for row in signal_rows_by_case["case_malformed_state_and_blank_recommendation_key"]] == [signal_key(HIT_A), signal_key(HIT_B)]
            and [row.get("signal_key") for row in recommendation_rows_by_case["case_malformed_state_and_blank_recommendation_key"]] == [signal_key(HIT_A), signal_key(HIT_B)]
            and signal_state_by_case["case_malformed_state_and_blank_recommendation_key"] == {"logged": sorted([signal_key(HIT_A), signal_key(HIT_B)])}
            and recommendation_state_by_case["case_malformed_state_and_blank_recommendation_key"] == {"logged": sorted([signal_key(HIT_A), signal_key(HIT_B)])},
            "malformed_state_rebuilds_dedup_from_existing_ledgers_and_ignores_blank_recommendation_keys",
            "malformed dedup-state JSON now rebuilds the dedup set from existing signal/recommendation ledger rows, appends only new keys, and still ignores blank recommendation keys rather than creating garbage rows or state entries",
        ),
        guardrail(
            scratch.get("fixture_root_relative") == "out/status_validation/paper_trade_logger_fixture"
            and scratch.get("fixture_root_is_project_local") is True
            and scratch.get("case_roots_cleared_by_setup_case") is True,
            "fixture_scratch_metadata_published",
            "the direct logger validator now publishes project-local fixture scratch metadata so parent rollups can verify isolated ledger-fixture hygiene without parsing markdown prose",
        ),
        guardrail(
            "source-layer ledger reproducibility check" in current_read
            and "source-level valid_evidence_scope plus evidence-boundary lines" in current_read
            and f"valid_evidence_scope={logger_source.LOGGER_VALID_EVIDENCE_SCOPE}" in current_read
            and EVIDENCE_BOUNDARY.get("valid_evidence_scope") == logger_source.LOGGER_VALID_EVIDENCE_SCOPE
            and EVIDENCE_BOUNDARY.get("logger_validator_passes_are_ledger_metadata_only") is True
            and "not settlement-complete ROI, promotion, live profitability, or real-money evidence" in current_read,
            "paper_trade_logger_validator_stays_ledger_reproducibility_not_settlement_evidence",
            "the direct logger validator summary now frames a green fixture sweep as ledger append/dedup reproducibility, every successful fixture stdout and the validator report itself carry exact valid_evidence_scope metadata, and the summary stays out of settled ROI, promotion, live profitability, or real-money evidence",
        ),
        guardrail(
            scorecard_gates.get("source") == "forward_evidence_scorecard.json"
            and scorecard_gates.get("source_path") == "decision_gate_minimums"
            and scorecard_gates.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and scorecard_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and scorecard_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and scorecard_gates.get("real_money_no_baq_as_bel_required") is True
            and "no BAQ-as-BEL substitution" in scorecard_gates.get("real_money_also_requires", []),
            "logger_preserves_scorecard_gate_boundary",
            "the direct logger validator now reads forward_evidence_scorecard.json decision_gate_minimums and publishes the 30-row anchor-review floor, 20-row Phase 8 review floor, 100-row real-money discussion floor, and no-BAQ-as-BEL prerequisite as ledger-layer boundary metadata only",
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
        "valid_evidence_scope": logger_source.LOGGER_VALID_EVIDENCE_SCOPE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scratch": scratch,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "cases": results,
        "summary": {
            "current_read": current_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "fixture_root": str(FIXTURE_ROOT),
            "report_path": str(report_md),
        },
    }

    lines = [
        "# Paper-Trade Logger Validation",
        "",
        "This report validates `paper_trade_logger.py` directly inside isolated fixture ledgers while publishing the saved validator artifact at the standard paper-trade-logger report path.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Fixture root: `{FIXTURE_ROOT}`",
        f"- Fixture scratch metadata: `{scratch['fixture_root_relative']}` is project-local and each fixture case root is cleared before setup.",
        f"- Report path: `{report_md}`",
        "",
        "## Cases",
        "",
        "| Case | Scenario | Signal ledger | Recommendation ledger |",
        "|---|---|---|---|",
    ]
    for row in results:
        lines.append(
            f"| `{row['name']}` | {row['scenario']} | `{row['signal_ledger']}` | `{row['recommendation_ledger']}` |"
        )

    lines.extend([
        "",
        "## Rollup Guardrails",
        "",
        *[f"- PASS `{check['check']}` — {check['detail']}" for check in child_checks],
        "",
        "## Current Read",
        "",
        f"- Suite read: {payload['summary']['current_read']}",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
        f"- valid_evidence_scope={logger_source.LOGGER_VALID_EVIDENCE_SCOPE}",
        f"- Source valid evidence scope: `{logger_source.LOGGER_VALID_EVIDENCE_SCOPE}`",
        "- Validator passes, fixture ledgers, appended open rows, serialized payloads, and dedup state files are source-layer metadata only.",
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
        "- Empty runs still create header-only ledgers plus stable empty dedup state files instead of leaving the pipeline without append targets.",
        "- New signal and recommendation rows still append with serialized list payloads and open status fields so downstream settlement and monitoring tools see a stable contract.",
        "- Successful logger CLI output now carries source-level `valid_evidence_scope` plus evidence boundary lines, so appended open rows cannot be copied as settled ROI, promotion readiness, live-profitability proof, or real-money support.",
        "- Existing state files and ledger rows still block duplicate appends while allowing genuinely new signal keys through.",
        "- Malformed state files now rebuild dedup from existing ledger rows before appending only new keys, and blank recommendation keys are still ignored instead of creating garbage ledger rows.",
        "- Project-local fixture scratch metadata is published for parent rollups as reproducibility context only.",
        "- Scorecard-sourced paper-observation gates stay visible without treating fixture ledgers or validator passes as settled evidence.",
        "",
        "## Sources",
        "",
    ])
    for row in results:
        lines.append(f"- `{row['stdout']}`")
        lines.append(f"- `{row['signal_ledger']}`")
        lines.append(f"- `{row['recommendation_ledger']}`")

    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {report_md}")
    print(f"Wrote {report_json}")
    for row in results:
        print(f"PASS {row['name']}: {row['signal_ledger']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
