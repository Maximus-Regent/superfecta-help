#!/usr/bin/env python3
"""
Fixture-driven validation for paper_trade_settlement_sync.py.

Purpose:
- pin the settlement-template ledger contract directly at the source layer
- keep one-row-per-signal-key syncing reproducible before the wrapper reads forward results
- prove that manual settlement fields are preserved while signal metadata stays refreshable
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
from typing import Any, Callable

import paper_trade_settlement_sync as settlement_sync_source

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "paper_trade_settlement_sync.py"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "settlement_sync_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_settlement_sync"
REPORT_MD = OUT_DIR / "paper_trade_settlement_sync_validation.md"
REPORT_JSON = OUT_DIR / "paper_trade_settlement_sync_validation.json"
REBUILD_COMMAND = "python3 validate_paper_trade_settlement_sync.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade settlement-sync validator",
    "valid_evidence_scope": settlement_sync_source.SETTLEMENT_SYNC_VALID_EVIDENCE_SCOPE,
    "source_valid_evidence_scope": settlement_sync_source.SETTLEMENT_SYNC_VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "isolated settlement-sync fixture ledgers",
        "paper_trade_settlement_sync.py",
        "forward_evidence_scorecard.json decision_gate_minimums",
    ],
    "valid_use": "settlement-template reproducibility and signal-to-settlement ledger alignment before ROI-complete outcomes exist",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "settlement_sync_validator_passes_are_ledger_sync_metadata_only": True,
    "non_goals": [
        "do not treat created open settlement rows as ROI-complete observations",
        "do not treat template alignment as profitability evidence",
        "do not promote OP_REFINED_K7 or Phase 8 from settlement-sync validator cleanliness",
        "do not substitute BAQ for BEL",
        "do not treat ledger-sync reproducibility as real-money evidence",
    ],
}


def build_fixture_scratch_metadata() -> dict[str, Any]:
    validation_root = (BASE / "out" / "status_validation").resolve()
    fixture_root = FIXTURE_ROOT.resolve()
    return {
        "fixture_root": str(fixture_root),
        "fixture_root_relative": str(FIXTURE_ROOT.relative_to(BASE)),
        "fixture_root_is_project_local": fixture_root == validation_root or validation_root in fixture_root.parents,
        "case_roots_cleared_by_setup_case": True,
    }


SIGNAL_FIELDS = [
    "signal_key", "scan_ts", "rule_id", "track", "card_name", "race_number", "race_id",
    "surface", "condition", "field_size", "favorite_program", "favorite_name", "favorite_prob",
    "second_prob", "prob_gap", "k", "base_stake", "estimated_cost", "underneath_programs",
    "ticket_structure", "status", "outcome", "notes",
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
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def assert_contains(text: str, needle: str, case_name: str) -> None:
    if needle not in text:
        raise AssertionError(f"{case_name}: expected to find {needle!r}")


def signal_row(
    idx: int,
    *,
    rule_id: str = "OP_DURABLE_K7",
    track: str = "OP",
    race_number: int = 7,
    estimated_cost: str = "24.00",
    signal_key: str | None = None,
) -> dict[str, Any]:
    return {
        "signal_key": signal_key if signal_key is not None else f"{rule_id.lower()}_{idx:03d}",
        "scan_ts": f"2026-05-21T1{idx % 10}:00:00",
        "rule_id": rule_id,
        "track": track,
        "card_name": "Oaklawn Park" if track == "OP" else "Churchill Downs",
        "race_number": str(race_number),
        "race_id": f"{track}-2026-05-21-R{race_number}",
        "surface": "dirt",
        "condition": "fast",
        "field_size": "11" if rule_id == "OP_DURABLE_K7" else "10",
        "favorite_program": "1",
        "favorite_name": f"Favorite {idx}",
        "favorite_prob": "0.32",
        "second_prob": "0.18",
        "prob_gap": "0.14",
        "k": "7" if rule_id == "OP_DURABLE_K7" else "8",
        "base_stake": "1",
        "estimated_cost": estimated_cost,
        "underneath_programs": "2,3,4",
        "ticket_structure": "1 / 2,3,4",
        "status": "",
        "outcome": "",
        "notes": "fixture",
    }


def settlement_row(
    signal_key: str,
    *,
    scan_ts: str = "2026-05-21T11:00:00",
    rule_id: str = "OP_DURABLE_K7",
    track: str = "OP",
    card_name: str = "Oaklawn Park",
    race_number: str = "7",
    race_id: str = "OP-2026-05-21-R7",
    expected_cost: str = "24.00",
    settlement_status: str = "open",
    outcome: str = "",
    actual_cost: str = "",
    actual_return: str = "",
    actual_profit: str = "",
    settled_ts: str = "",
    notes: str = "",
) -> dict[str, Any]:
    return {
        "signal_key": signal_key,
        "scan_ts": scan_ts,
        "rule_id": rule_id,
        "track": track,
        "card_name": card_name,
        "race_number": race_number,
        "race_id": race_id,
        "expected_cost": expected_cost,
        "settlement_status": settlement_status,
        "outcome": outcome,
        "actual_cost": actual_cost,
        "actual_return": actual_return,
        "actual_profit": actual_profit,
        "settled_ts": settled_ts,
        "notes": notes,
    }


CASES: list[dict[str, Any]] = [
    {
        "name": "case_empty_signals_creates_header_only",
        "scenario": "empty signal ledgers still produce a valid empty settlement ledger with the real CLI",
        "signals": [],
        "existing": [],
        "expected_rows": [],
        "stdout_needles": ["Settlement sync complete: 0 row(s), 0 added, 0 preserved."],
    },
    {
        "name": "case_new_signals_create_open_templates",
        "scenario": "new signals create one open template row per signal with expected cost copied from the signal ledger",
        "signals": [signal_row(1), signal_row(2, rule_id="CD_CORE_K8", track="CD", race_number=8, estimated_cost="36.00")],
        "existing": [],
        "expected_rows": [
            settlement_row("op_durable_k7_001", scan_ts="2026-05-21T11:00:00", expected_cost="24.00", notes="", settled_ts=""),
            settlement_row("cd_core_k8_002", scan_ts="2026-05-21T12:00:00", rule_id="CD_CORE_K8", track="CD", card_name="Churchill Downs", race_number="8", race_id="CD-2026-05-21-R8", expected_cost="36.00", notes="", settled_ts=""),
        ],
        "stdout_needles": ["Settlement sync complete: 2 row(s), 2 added, 0 preserved."],
    },
    {
        "name": "case_existing_manual_settlement_fields_are_preserved",
        "scenario": "existing manual settlement fields survive a sync while signal metadata is refreshed from the latest signal ledger",
        "signals": [signal_row(3, estimated_cost="30.00")],
        "existing": [
            settlement_row(
                "op_durable_k7_003",
                scan_ts="2026-05-20T10:00:00",
                expected_cost="24.00",
                settlement_status="settled",
                outcome="HIT",
                actual_cost="24.00",
                actual_return="180.00",
                actual_profit="156.00",
                settled_ts="2026-05-20T19:30:00",
                notes="manual settlement kept",
            )
        ],
        "expected_rows": [
            settlement_row(
                "op_durable_k7_003",
                scan_ts="2026-05-21T13:00:00",
                expected_cost="30.00",
                settlement_status="settled",
                outcome="HIT",
                actual_cost="24.00",
                actual_return="180.00",
                actual_profit="156.00",
                settled_ts="2026-05-20T19:30:00",
                notes="manual settlement kept",
            )
        ],
        "stdout_needles": ["Settlement sync complete: 1 row(s), 0 added, 1 preserved."],
    },
    {
        "name": "case_blank_signal_keys_and_orphan_rows_do_not_survive",
        "scenario": "blank and duplicate signal keys are skipped, blank settlement-key rows are dropped, and orphan settlement rows are reported as dropped so the ledger stays one-row-per-live-signal-key",
        "signals": [
            signal_row(4, signal_key=""),
            signal_row(5),
            signal_row(6, signal_key="op_durable_k7_005", estimated_cost="999.00"),
        ],
        "existing": [
            settlement_row("", notes="blank settlement key should disappear"),
            settlement_row("stale_signal_999", notes="should disappear"),
            settlement_row("op_durable_k7_005", notes="keep me"),
        ],
        "expected_rows": [
            settlement_row("op_durable_k7_005", scan_ts="2026-05-21T15:00:00", expected_cost="24.00", notes="keep me"),
        ],
        "stdout_needles": [
            "Settlement sync complete: 1 row(s), 0 added, 1 preserved.",
            "Cleanup: 1 blank signal-key row(s) skipped; 1 blank settlement-key row(s) dropped; 1 orphan settlement row(s) dropped.",
            "Dedup: 1 duplicate signal-key row(s) skipped.",
        ],
    },
]


def setup_case(case: dict[str, Any]) -> tuple[Path, Path, Path]:
    case_root = FIXTURE_ROOT / case["name"]
    if case_root.exists():
        shutil.rmtree(case_root)
    case_root.mkdir(parents=True, exist_ok=True)

    signals_path = case_root / "paper_trades" / "phase7_current_paper_paper_trade_signals.csv"
    settlement_path = case_root / "paper_trades" / "phase7_current_paper_paper_trade_settlements.csv"
    write_csv(signals_path, SIGNAL_FIELDS, case["signals"])
    write_csv(settlement_path, SETTLEMENT_FIELDS, case["existing"])
    return case_root, signals_path, settlement_path


def compare_rows(actual: list[dict[str, str]], expected: list[dict[str, Any]], case_name: str) -> None:
    normalized_expected = [
        {field: str(row.get(field, "")) for field in SETTLEMENT_FIELDS}
        for row in expected
    ]
    if actual != normalized_expected:
        raise AssertionError(
            f"{case_name}: settlement rows did not match expected output.\n"
            f"actual={json.dumps(actual, indent=2)}\nexpected={json.dumps(normalized_expected, indent=2)}"
        )


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
            "settlement-sync template fixtures and open settlement rows do not count toward "
            "anchor-displacement, Phase 8 promotion-review, or real-money discussion gates"
        ),
    }


def guardrail(condition: bool, check: str, detail: str) -> dict[str, str]:
    if not condition:
        raise AssertionError(f"{check}: {detail}")
    return {"check": check, "status": "pass", "detail": detail}


def configure_output_paths(fixture_root: Path, out_dir: Path) -> None:
    global FIXTURE_ROOT, OUT_DIR, REPORT_MD, REPORT_JSON
    FIXTURE_ROOT = fixture_root
    OUT_DIR = out_dir
    REPORT_MD = OUT_DIR / "paper_trade_settlement_sync_validation.md"
    REPORT_JSON = OUT_DIR / "paper_trade_settlement_sync_validation.json"


def assert_scorecard_failure_before_artifacts(
    *,
    scorecard_json: Path,
    mutation: Callable[[dict[str, Any]], None],
    expected_error: str,
    check: str,
    detail: str,
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="settlement_sync_scorecard_guardrail_") as tmp_name:
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
            check="scorecard_boolean_gate_floor_fails_before_settlement_sync_artifacts",
            detail=(
                "a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before "
                "nested settlement-sync fixture/report artifacts are created"
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
            check="scorecard_nonpositive_phase8_gate_floor_fails_before_settlement_sync_artifacts",
            detail=(
                "a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails "
                "before nested settlement-sync fixture/report artifacts are created"
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
            check="scorecard_nonpositive_real_money_gate_floor_fails_before_settlement_sync_artifacts",
            detail=(
                "a non-positive real-money discussion floor in forward_evidence_scorecard.json fails "
                "before nested settlement-sync fixture/report artifacts are created"
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
            check="scorecard_missing_no_baq_fails_before_settlement_sync_artifacts",
            detail=(
                "a scorecard missing the no-BAQ-as-BEL real-money prerequisite fails before "
                "nested settlement-sync fixture/report artifacts are created"
            ),
        ),
    ]


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_root, signals_path, settlement_path = setup_case(case)
    output_path = case_root / "stdout.txt"
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--signals-ledger",
        str(signals_path),
        "--settlement-ledger",
        str(settlement_path),
    ]
    result = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, check=True)
    stdout = result.stdout.strip()
    output_path.write_text(stdout + "\n", encoding="utf-8")

    for needle in case.get("stdout_needles", []):
        assert_contains(stdout, needle, case["name"])
    assert_contains(
        stdout,
        f"valid_evidence_scope={settlement_sync_source.SETTLEMENT_SYNC_VALID_EVIDENCE_SCOPE}",
        case["name"],
    )
    assert_contains(stdout, settlement_sync_source.SETTLEMENT_SYNC_EVIDENCE_BOUNDARY_TEXT, case["name"])
    assert_contains(stdout, "not settled ROI evidence", case["name"])
    assert_contains(stdout, "not real-money support", case["name"])

    actual_rows = read_csv(settlement_path)
    compare_rows(actual_rows, case["expected_rows"], case["name"])

    return {
        "name": case["name"],
        "scenario": case["scenario"],
        "result": "PASS",
        "stdout": str(output_path.relative_to(BASE)),
        "settlement_ledger": str(settlement_path.relative_to(BASE)),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--fixture-root", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args([] if argv is None else argv)
    scorecard_json = args.scorecard_json.expanduser().resolve()
    configure_output_paths(
        fixture_root=args.fixture_root.expanduser().resolve(),
        out_dir=args.out_dir.expanduser().resolve(),
    )
    scorecard_gates = read_scorecard_gate_minimums(scorecard_json)
    scorecard_guardrails = scorecard_no_artifact_guardrails(scorecard_json)

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = [run_case(case) for case in CASES]
    scratch = build_fixture_scratch_metadata()

    child_checks = [
        {
            "check": "empty_signal_ledgers_still_write_a_stable_header_only_template",
            "status": "pass",
            "detail": "the empty-signals fixture still proves settlement sync writes a stable settlement CSV header with zero rows instead of failing or omitting the ledger structure before the first live signal exists",
        },
        {
            "check": "new_live_signals_still_create_one_open_row_per_signal_with_expected_cost",
            "status": "pass",
            "detail": "the new-signals fixture still proves each live signal produces exactly one open settlement template row with signal-owned metadata like expected_cost, scan_ts, rule_id, and race identifiers copied into the ledger",
        },
        {
            "check": "manual_settlement_fields_still_survive_metadata_refreshes",
            "status": "pass",
            "detail": "the preserved-settlement fixture still proves manually-entered settlement fields such as outcome, actual return, actual profit, settled timestamp, and notes survive a sync while signal-owned fields refresh from the latest signal ledger",
        },
        {
            "check": "blank_signal_and_settlement_keys_plus_orphan_rows_stay_separate",
            "status": "pass",
            "detail": "the cleanup fixture still proves empty signal_key rows are skipped, duplicate live signal keys are skipped, blank settlement-key rows are dropped, stale orphan settlement rows disappear, and the CLI reports those cleanup counts separately so the ledger stays one-row-per-current-live-signal-key instead of accumulating dead entries silently",
        },
        {
            "check": "direct_report_path_and_ledger_sync_boundary_stay_explicit",
            "status": "pass",
            "detail": "the validator still publishes its direct report path at the standard settlement-sync location, every successful fixture stdout now carries the source-level settlement-sync valid_evidence_scope plus evidence boundary, the direct report exposes the same exact valid_evidence_scope line, and the report still says plainly that this helper is a ledger-sync reproducibility surface rather than new forward evidence by itself",
        },
        {
            "check": "direct_validation_report_exposes_settlement_sync_valid_scope",
            "status": "pass",
            "detail": "the settlement-sync validation JSON, evidence-boundary metadata, summary read, and markdown evidence-boundary section now expose exact valid_evidence_scope=settlement_template_ledger_alignment_only so template-alignment fixtures cannot be copied as settled ROI, promotion readiness, live profitability, or real-money support",
        },
        *scorecard_guardrails,
        {
            "check": "settlement_sync_preserves_scorecard_gate_boundary",
            "status": "pass",
            "detail": "the settlement-sync validator now publishes the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite while saying template-sync fixtures and open rows do not count toward those gates and malformed copied gates fail before fixture/report artifacts",
        },
        {
            "check": "fixture_scratch_metadata_published",
            "status": "pass",
            "detail": "the settlement-sync validator JSON publishes project-local fixture scratch metadata so parent rollups can verify the isolated fixture root without parsing markdown prose",
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
        raise AssertionError("settlement-sync scorecard gate boundary no longer matches forward_evidence_scorecard.json")
    if (
        scratch.get("fixture_root_relative") != "out/status_validation/settlement_sync_fixture"
        or scratch.get("fixture_root_is_project_local") is not True
        or scratch.get("case_roots_cleared_by_setup_case") is not True
    ):
        raise AssertionError("settlement-sync fixture scratch metadata no longer proves a project-local cleared fixture root")

    payload = {
        "suite_status": "pass",
        "artifact_status": "pass",
        "total_fixture_scenarios": len(results),
        "total_checks": len(results),
        "check_count": len(results),
        "child_check_count": len(child_checks),
        "child_checks": child_checks,
        "cases": results,
        "valid_evidence_scope": settlement_sync_source.SETTLEMENT_SYNC_VALID_EVIDENCE_SCOPE,
        "summary": {
            "current_read": "settlement-sync still creates one open row per live signal key, preserves manual settlement fields on existing rows, refreshes signal metadata like scan_ts and expected_cost, skips blank and duplicate signal-key rows, drops blank settlement-key rows, drops stale orphan settlement rows, reports those cleanup counts separately so the forward ledger stays reproducible, now prints source-level valid_evidence_scope plus evidence-boundary lines in successful CLI output, now publishes exact valid_evidence_scope=settlement_template_ledger_alignment_only in its direct validator report at the standard settlement-sync validation path plus project-local fixture scratch metadata as a structured guardrail, rejects malformed and non-positive scorecard gates before fixture/report artifacts, and preserves the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that template-sync fixtures and open rows do not advance; settlement sync: ledger-sync/reproducibility surface, not new forward evidence by itself",
        },
        "scratch": scratch,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "fixture_root": str(FIXTURE_ROOT.relative_to(BASE)),
            "report_path": str(REPORT_MD.relative_to(BASE)),
        },
    }

    lines = [
        "# Paper-Trade Settlement Sync Validation",
        "",
        "This report validates `paper_trade_settlement_sync.py` directly inside isolated fixture ledgers.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Fixture root: `{FIXTURE_ROOT.relative_to(BASE)}`",
        f"- Direct report path: `{REPORT_MD.relative_to(BASE)}`",
        "",
        "## Cases",
        "",
        "| Case | Scenario | Settlement ledger |",
        "|---|---|---|",
    ]
    for row in results:
        lines.append(
            f"| `{row['name']}` | {row['scenario']} | `{row['settlement_ledger']}` |"
        )

    lines.extend(
        [
            "",
            "## Current Read",
            "",
            f"- Suite read: {payload['summary']['current_read']}",
            "",
            "## Evidence Boundary",
            "",
            f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
            f"- valid_evidence_scope={settlement_sync_source.SETTLEMENT_SYNC_VALID_EVIDENCE_SCOPE}",
            f"- Source valid evidence scope: `{settlement_sync_source.SETTLEMENT_SYNC_VALID_EVIDENCE_SCOPE}`",
            f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
            "- Boundary: settlement-sync validator cleanliness is ledger-sync metadata only, not new forward evidence, not a live paper-trade ledger, not a current-day scanner result, not settled ROI, not live profitability, not promotion readiness, and not real-money evidence.",
            "- Non-goals: do not treat created open settlement rows as ROI-complete observations, template alignment as profitability evidence, or settlement-sync fixtures as promotion / real-money support.",
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
            "- The settlement sync helper still writes a stable settlement CSV header even when no signals exist yet.",
            "- Successful settlement-sync CLI output and this direct validation report now carry exact `valid_evidence_scope=settlement_template_ledger_alignment_only` plus evidence boundary metadata, so created open rows cannot be copied as settled ROI, promotion readiness, live-profitability, or real-money support.",
            "- New signals still create one open settlement template row per `signal_key`, with the expected cost copied from the first matching signal ledger row.",
            "- Existing settled rows still preserve manual fields like `outcome`, `actual_return`, `actual_profit`, `settled_ts`, and `notes`, while refreshing signal-owned fields like `scan_ts` and `expected_cost` from the latest signal ledger.",
            "- Blank and duplicate signal keys are still skipped, blank settlement-key rows still disappear, and stale orphan settlement rows still disappear with separate explicit CLI cleanup counts, so the ledger stays aligned to the current live signal-key set instead of accumulating stale entries silently.",
            "- Malformed copied scorecard gates, including boolean anchor floors, non-positive Phase 8 / real-money floors, and a missing no-BAQ-as-BEL prerequisite, now fail before nested settlement-sync fixture/report artifacts are created.",
            "",
            "## Sources",
            "",
        ]
    )
    for row in results:
        lines.append(f"- `{row['stdout']}`")
        lines.append(f"- `{row['settlement_ledger']}`")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    for legacy in (
        FIXTURE_ROOT / "settlement_sync_fixture_validation.md",
        FIXTURE_ROOT / "settlement_sync_fixture_validation.json",
    ):
        if legacy.exists():
            legacy.unlink()

    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    for row in results:
        print(f"PASS {row['name']}: {row['settlement_ledger']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
