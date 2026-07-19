#!/usr/bin/env python3
"""
Fixture-driven validation for paper_trade_settlement_helper.py.

Purpose:
- pin the human-facing settlement-helper contract directly at the source layer
- keep open-queue rendering and single-row settlement updates reproducible
- prove the real CLI stays honest about both successful updates and missing-signal failures
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

import paper_trade_settlement_helper as settlement_helper_source

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "paper_trade_settlement_helper.py"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "settlement_helper_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_settlement_helper"
REPORT_MD = OUT_DIR / "paper_trade_settlement_helper_validation.md"
REPORT_JSON = OUT_DIR / "paper_trade_settlement_helper_validation.json"
REBUILD_COMMAND = "python3 validate_paper_trade_settlement_helper.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade settlement-helper validator",
    "valid_evidence_scope": settlement_helper_source.SETTLEMENT_HELPER_VALID_EVIDENCE_SCOPE,
    "source_valid_evidence_scope": settlement_helper_source.SETTLEMENT_HELPER_VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "isolated settlement-helper fixture ledgers",
        "paper_trade_settlement_helper.py",
        "forward_evidence_scorecard.json decision_gate_minimums",
    ],
    "valid_use": "human settlement-entry workflow validation, open-queue visibility, and ROI-complete repair guidance",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "settlement_helper_validator_passes_are_ledger_maintenance_metadata_only": True,
    "non_goals": [
        "do not treat helper-rendered open queues as ROI-complete observations",
        "do not treat a settlement update without settled_ts as clearing sample gates",
        "do not treat helper fixture cleanliness as profitability evidence",
        "do not promote OP_REFINED_K7 or Phase 8 from settlement-helper validator cleanliness",
        "do not substitute BAQ for BEL",
        "do not treat settlement-helper reproducibility as real-money evidence",
    ],
}
FIELDS = [
    "signal_key",
    "scan_ts",
    "rule_id",
    "track",
    "card_name",
    "race_number",
    "race_id",
    "expected_cost",
    "settlement_status",
    "outcome",
    "actual_cost",
    "actual_return",
    "actual_profit",
    "settled_ts",
    "notes",
]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def assert_contains(text: str, needle: str, case_name: str) -> None:
    if needle not in text:
        raise AssertionError(f"{case_name}: expected to find {needle!r}")


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
            "settlement-helper fixtures, open queue renders, and timestamp-incomplete settlement "
            "updates do not count toward anchor-displacement, Phase 8 promotion-review, or "
            "real-money discussion gates"
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
    REPORT_MD = OUT_DIR / "paper_trade_settlement_helper_validation.md"
    REPORT_JSON = OUT_DIR / "paper_trade_settlement_helper_validation.json"


def assert_scorecard_failure_before_artifacts(
    *,
    scorecard_json: Path,
    mutation: Callable[[dict[str, Any]], None],
    expected_error: str,
    check: str,
    detail: str,
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="settlement_helper_scorecard_guardrail_") as tmp_name:
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
            check="scorecard_boolean_gate_floor_fails_before_settlement_helper_artifacts",
            detail=(
                "a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before "
                "nested settlement-helper fixture/report artifacts are created"
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
            check="scorecard_nonpositive_phase8_gate_floor_fails_before_settlement_helper_artifacts",
            detail=(
                "a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails "
                "before nested settlement-helper fixture/report artifacts are created"
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
            check="scorecard_nonpositive_real_money_gate_floor_fails_before_settlement_helper_artifacts",
            detail=(
                "a non-positive real-money discussion floor in forward_evidence_scorecard.json fails "
                "before nested settlement-helper fixture/report artifacts are created"
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
            check="scorecard_missing_no_baq_fails_before_settlement_helper_artifacts",
            detail=(
                "a scorecard missing the no-BAQ-as-BEL real-money prerequisite fails before "
                "nested settlement-helper fixture/report artifacts are created"
            ),
        ),
    ]


def settlement_row(
    signal_key: str,
    *,
    scan_ts: str = "2026-05-22T11:00:00",
    rule_id: str = "OP_DURABLE_K7",
    track: str = "OP",
    card_name: str = "Oaklawn Park",
    race_number: str = "7",
    race_id: str = "OP-2026-05-22-R7",
    expected_cost: str = "24.00",
    settlement_status: str = "open",
    outcome: str = "",
    actual_cost: str = "",
    actual_return: str = "",
    actual_profit: str = "",
    settled_ts: str = "",
    notes: str = "",
    actual_cost_source: str = "",
) -> dict[str, Any]:
    row = {
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
    if actual_cost_source:
        row["actual_cost_source"] = actual_cost_source
    return row


CASES: list[dict[str, Any]] = [
    {
        "name": "case_list_open_empty_text",
        "scenario": "empty ledgers still report a clean zero-row open queue in text mode",
        "command": ["list-open", "--format", "text"],
        "rows": [],
        "stdout_needles": [
            "Open settlement rows: 0",
            "Settled rows missing ROI-complete coverage: 0",
        ],
    },
    {
        "name": "case_list_open_md_truncation",
        "scenario": "markdown open-queue output still truncates honestly when the queue exceeds the display limit",
        "command": ["list-open", "--format", "md", "--limit", "2"],
        "rows": [
            settlement_row("op_durable_k7_001"),
            settlement_row("cd_core_k8_002", rule_id="CD_CORE_K8", track="CD", card_name="Churchill Downs", race_number="8", race_id="CD-2026-05-22-R8", expected_cost="36.00"),
            settlement_row("op_durable_k7_003", race_number="9", race_id="OP-2026-05-22-R9"),
            settlement_row("settled_gap_004", settlement_status="settled", outcome="MISS", actual_cost="24.00", actual_return="0.00", actual_profit="-24.00"),
        ],
        "stdout_needles": [
            "# Open Settlement Queue",
            "- Open settlement rows: `3`",
            "- Settled rows missing ROI-complete coverage: `1`",
            "- Showing first `2` row(s)",
            "| op_durable_k7_001 | OP_DURABLE_K7 | OP | 7 | OP-2026-05-22-R7 | 24.00 | 2026-05-22T11:00:00 |",
            "## Settlement Command Templates",
            "Settlement command templates are templates only; replace placeholders only after actual result/payout evidence exists.",
            "`op_durable_k7_001`: `python3 paper_trade_settlement_helper.py settle --signal-key op_durable_k7_001 --outcome HIT_OR_MISS --actual-return ACTUAL_RETURN_DOLLARS --settled-ts ISO_SETTLED_TS`",
            "## Settled Rows Missing ROI-Complete Coverage",
            "| settled_gap_004 | OP_DURABLE_K7 | OP | 7 | OP-2026-05-22-R7 | 24.00 | 0.00 | 24.00 |  | missing settled_ts |",
        ],
    },
    {
        "name": "case_list_open_json_filters_settled_rows",
        "scenario": "JSON open-queue output still counts only open rows and ignores settled ones",
        "command": ["list-open", "--format", "json", "--limit", "5"],
        "rows": [
            settlement_row("open_001"),
            settlement_row("settled_002", settlement_status="settled", outcome="MISS", actual_cost="24.00", actual_return="0.00", actual_profit="-24.00", settled_ts="2026-05-22T19:30:00"),
            settlement_row("pending_003", settlement_status="pending"),
            settlement_row("settled_gap_004", settlement_status="settled", outcome="HIT", actual_return="120.00", actual_cost="", actual_profit="", settled_ts="<SETTLED_TS>"),
            settlement_row("settled_zero_cost_005", settlement_status="settled", outcome="HIT", actual_return="120.00", actual_cost="0.00", actual_profit="120.00", settled_ts="2026-05-22T20:15:00"),
        ],
        "expected_json": {
            "open_count": 2,
            "shown_count": 2,
            "limit": 5,
            "signal_keys": ["open_001", "pending_003"],
            "roi_gap_count": 2,
            "roi_gap_shown_count": 2,
            "roi_gap_signal_keys": ["settled_gap_004", "settled_zero_cost_005"],
        },
        "stdout_needles": [
            "\"settle_command_template\"",
            "python3 paper_trade_settlement_helper.py settle --signal-key open_001 --outcome HIT_OR_MISS --actual-return ACTUAL_RETURN_DOLLARS --settled-ts ISO_SETTLED_TS",
            "replace placeholders only after actual result/payout evidence exists",
            "Add --actual-cost ACTUAL_COST_DOLLARS if actual cost differs from expected_cost",
            "non-positive actual_cost",
        ],
    },
    {
        "name": "case_settle_text_with_actual_cost",
        "scenario": "settle updates exactly one row, computes profit when actual cost is provided, and leaves other rows untouched",
        "command": [
            "settle",
            "--signal-key", "op_durable_k7_004",
            "--outcome", "HIT",
            "--actual-return", "180",
            "--actual-cost", "24",
            "--settled-ts", "2026-05-22T19:30:00",
            "--notes", "manual settlement entry",
        ],
        "rows": [
            settlement_row("op_durable_k7_004"),
            settlement_row("cd_core_k8_005", rule_id="CD_CORE_K8", track="CD", card_name="Churchill Downs", race_number="8", race_id="CD-2026-05-22-R8", expected_cost="36.00"),
        ],
        "stdout_needles": [
            "Updated op_durable_k7_004: settled HIT, return=180.00, cost=24.00, profit=156.00, cost_source=actual_cost_argument",
        ],
        "expected_rows": [
            settlement_row("op_durable_k7_004", settlement_status="settled", outcome="HIT", actual_cost="24.00", actual_return="180.00", actual_profit="156.00", settled_ts="2026-05-22T19:30:00", notes="manual settlement entry", actual_cost_source="actual_cost_argument"),
            settlement_row("cd_core_k8_005", rule_id="CD_CORE_K8", track="CD", card_name="Churchill Downs", race_number="8", race_id="CD-2026-05-22-R8", expected_cost="36.00"),
        ],
    },
    {
        "name": "case_settle_json_uses_expected_cost_when_actual_cost_omitted",
        "scenario": "JSON settle confirmation infers actual cost from expected cost when only actual return is entered",
        "command": [
            "settle",
            "--signal-key", "op_durable_k7_006",
            "--outcome", "MISS",
            "--actual-return", "0",
            "--output-format", "json",
        ],
        "rows": [settlement_row("op_durable_k7_006")],
        "expected_json": {
            "signal_key": "op_durable_k7_006",
            "settlement_status": "settled",
            "outcome": "MISS",
            "actual_cost": "24.00",
            "actual_cost_source": "expected_cost_fallback",
            "actual_return": "0.00",
            "actual_profit": "-24.00",
            "settled_ts": "",
            "roi_complete_timestamp_coverage": False,
            "settled_ts_note": "missing settled_ts; row remains a settlement-quality gap and does not count toward ROI-complete sample gates",
            "notes": "",
        },
        "expected_rows": [
            settlement_row("op_durable_k7_006", settlement_status="settled", outcome="MISS", actual_cost="24.00", actual_return="0.00", actual_profit="-24.00", actual_cost_source="expected_cost_fallback"),
        ],
    },
    {
        "name": "case_settle_json_true_missing_cost_stays_blank",
        "scenario": "JSON settle confirmation still leaves actual cost and profit blank when neither actual nor expected cost is available",
        "command": [
            "settle",
            "--signal-key", "op_durable_k7_006_no_cost",
            "--outcome", "MISS",
            "--actual-return", "0",
            "--output-format", "json",
        ],
        "rows": [settlement_row("op_durable_k7_006_no_cost", expected_cost="")],
        "expected_json": {
            "signal_key": "op_durable_k7_006_no_cost",
            "settlement_status": "settled",
            "outcome": "MISS",
            "actual_cost": "",
            "actual_cost_source": "missing_cost_source",
            "actual_return": "0.00",
            "actual_profit": "",
            "settled_ts": "",
            "roi_complete_timestamp_coverage": False,
            "settled_ts_note": "missing settled_ts; row remains a settlement-quality gap and does not count toward ROI-complete sample gates",
            "notes": "",
        },
        "expected_rows": [
            settlement_row("op_durable_k7_006_no_cost", expected_cost="", settlement_status="settled", outcome="MISS", actual_return="0.00", actual_cost_source="missing_cost_source"),
        ],
    },
    {
        "name": "case_settle_json_malformed_expected_cost_stays_blank",
        "scenario": "JSON settle confirmation leaves actual cost and profit blank and reports a missing cost source when expected cost is malformed",
        "command": [
            "settle",
            "--signal-key", "op_durable_k7_006_bad_cost",
            "--outcome", "MISS",
            "--actual-return", "0",
            "--output-format", "json",
        ],
        "rows": [settlement_row("op_durable_k7_006_bad_cost", expected_cost="not-a-number")],
        "expected_json": {
            "signal_key": "op_durable_k7_006_bad_cost",
            "settlement_status": "settled",
            "outcome": "MISS",
            "actual_cost": "",
            "actual_cost_source": "missing_cost_source",
            "actual_return": "0.00",
            "actual_profit": "",
            "settled_ts": "",
            "roi_complete_timestamp_coverage": False,
            "settled_ts_note": "missing settled_ts; row remains a settlement-quality gap and does not count toward ROI-complete sample gates",
            "notes": "",
        },
        "expected_rows": [
            settlement_row("op_durable_k7_006_bad_cost", expected_cost="not-a-number", settlement_status="settled", outcome="MISS", actual_return="0.00", actual_cost_source="missing_cost_source"),
        ],
    },
    {
        "name": "case_settle_json_negative_expected_cost_stays_blank",
        "scenario": "JSON settle confirmation treats a negative expected-cost fallback as missing instead of computing impossible profit",
        "command": [
            "settle",
            "--signal-key", "op_durable_k7_006_negative_expected_cost",
            "--outcome", "MISS",
            "--actual-return", "0",
            "--output-format", "json",
        ],
        "rows": [settlement_row("op_durable_k7_006_negative_expected_cost", expected_cost="-24.00")],
        "expected_json": {
            "signal_key": "op_durable_k7_006_negative_expected_cost",
            "settlement_status": "settled",
            "outcome": "MISS",
            "actual_cost": "",
            "actual_cost_source": "missing_cost_source",
            "actual_return": "0.00",
            "actual_profit": "",
            "settled_ts": "",
            "roi_complete_timestamp_coverage": False,
            "settled_ts_note": "missing settled_ts; row remains a settlement-quality gap and does not count toward ROI-complete sample gates",
            "notes": "",
        },
        "expected_rows": [
            settlement_row("op_durable_k7_006_negative_expected_cost", expected_cost="-24.00", settlement_status="settled", outcome="MISS", actual_return="0.00", actual_cost_source="missing_cost_source"),
        ],
    },
    {
        "name": "case_settle_json_zero_expected_cost_stays_blank",
        "scenario": "JSON settle confirmation treats a zero expected-cost fallback as missing instead of computing impossible profit",
        "command": [
            "settle",
            "--signal-key", "op_durable_k7_006_zero_expected_cost",
            "--outcome", "MISS",
            "--actual-return", "0",
            "--output-format", "json",
        ],
        "rows": [settlement_row("op_durable_k7_006_zero_expected_cost", expected_cost="0.00")],
        "expected_json": {
            "signal_key": "op_durable_k7_006_zero_expected_cost",
            "settlement_status": "settled",
            "outcome": "MISS",
            "actual_cost": "",
            "actual_cost_source": "missing_cost_source",
            "actual_return": "0.00",
            "actual_profit": "",
            "settled_ts": "",
            "roi_complete_timestamp_coverage": False,
            "settled_ts_note": "missing settled_ts; row remains a settlement-quality gap and does not count toward ROI-complete sample gates",
            "notes": "",
        },
        "expected_rows": [
            settlement_row("op_durable_k7_006_zero_expected_cost", expected_cost="0.00", settlement_status="settled", outcome="MISS", actual_return="0.00", actual_cost_source="missing_cost_source"),
        ],
    },
    {
        "name": "case_settle_placeholder_outcome_fails_before_mutation",
        "scenario": "placeholder or unsupported outcome tokens fail before mutating the settlement ledger",
        "command": [
            "settle",
            "--signal-key", "op_durable_k7_007_placeholder",
            "--outcome", "<HIT_OR_MISS>",
            "--actual-return", "0",
        ],
        "rows": [settlement_row("op_durable_k7_007_placeholder")],
        "expect_failure": "invalid outcome '<HIT_OR_MISS>'; use HIT or MISS after the actual race result is known",
    },
    {
        "name": "case_settle_nan_actual_return_fails_before_mutation",
        "scenario": "non-finite actual-return input fails before mutating the settlement ledger",
        "command": [
            "settle",
            "--signal-key", "op_durable_k7_007_nan_return",
            "--outcome", "MISS",
            "--actual-return", "nan",
        ],
        "rows": [settlement_row("op_durable_k7_007_nan_return")],
        "expect_failure": "argument --actual-return: must be a finite non-negative dollar amount",
    },
    {
        "name": "case_settle_negative_actual_cost_fails_before_mutation",
        "scenario": "negative actual-cost input fails before mutating the settlement ledger",
        "command": [
            "settle",
            "--signal-key", "op_durable_k7_007_negative_cost",
            "--outcome", "MISS",
            "--actual-return", "0",
            "--actual-cost", "-24",
        ],
        "rows": [settlement_row("op_durable_k7_007_negative_cost")],
        "expect_failure": "argument --actual-cost: must be a finite positive dollar amount",
    },
    {
        "name": "case_settle_zero_actual_cost_fails_before_mutation",
        "scenario": "zero actual-cost input fails before mutating the settlement ledger",
        "command": [
            "settle",
            "--signal-key", "op_durable_k7_007_zero_cost",
            "--outcome", "MISS",
            "--actual-return", "0",
            "--actual-cost", "0",
        ],
        "rows": [settlement_row("op_durable_k7_007_zero_cost")],
        "expect_failure": "argument --actual-cost: must be a finite positive dollar amount",
    },
    {
        "name": "case_settle_placeholder_settled_ts_fails_before_mutation",
        "scenario": "placeholder settled-ts input fails before mutating the settlement ledger",
        "command": [
            "settle",
            "--signal-key", "op_durable_k7_007_placeholder_ts",
            "--outcome", "MISS",
            "--actual-return", "0",
            "--settled-ts", "<SETTLED_TS>",
        ],
        "rows": [settlement_row("op_durable_k7_007_placeholder_ts")],
        "expect_failure": "argument --settled-ts: must be an actual ISO settlement timestamp, not blank or a placeholder",
    },
    {
        "name": "case_settle_malformed_settled_ts_fails_before_mutation",
        "scenario": "malformed settled-ts input fails before mutating the settlement ledger",
        "command": [
            "settle",
            "--signal-key", "op_durable_k7_007_bad_ts",
            "--outcome", "MISS",
            "--actual-return", "0",
            "--settled-ts", "after-race",
        ],
        "rows": [settlement_row("op_durable_k7_007_bad_ts")],
        "expect_failure": "argument --settled-ts: must be an actual ISO settlement timestamp, not blank or a placeholder",
    },
    {
        "name": "case_settle_missing_signal_fails_cleanly",
        "scenario": "missing signal keys still fail loudly instead of silently mutating the wrong row",
        "command": [
            "settle",
            "--signal-key", "missing_signal_999",
            "--outcome", "HIT",
            "--actual-return", "50",
        ],
        "rows": [settlement_row("op_durable_k7_007")],
        "expect_failure": "signal_key not found in settlement ledger: missing_signal_999",
    },
    {
        "name": "case_settle_duplicate_signal_key_fails_before_mutation",
        "scenario": "duplicate signal keys fail loudly before mutating either matching row",
        "command": [
            "settle",
            "--signal-key", "duplicate_signal_008",
            "--outcome", "MISS",
            "--actual-return", "0",
            "--settled-ts", "2026-05-22T19:30:00",
        ],
        "rows": [
            settlement_row("duplicate_signal_008", expected_cost="24.00"),
            settlement_row("duplicate_signal_008", race_number="8", race_id="OP-2026-05-22-R8", expected_cost="36.00"),
        ],
        "expect_failure": (
            "duplicate signal_key in settlement ledger: duplicate_signal_008 appears 2 times; "
            "repair the settlement ledger or rerun paper_trade_settlement_sync.py before settling this signal"
        ),
    },
]


def setup_case(case: dict[str, Any]) -> tuple[Path, Path]:
    case_root = FIXTURE_ROOT / case["name"]
    if case_root.exists():
        shutil.rmtree(case_root)
    case_root.mkdir(parents=True, exist_ok=True)
    settlement_path = case_root / "paper_trades" / "phase7_current_paper_paper_trade_settlements.csv"
    write_csv(settlement_path, case["rows"])
    return case_root, settlement_path


def compare_rows(actual: list[dict[str, str]], expected: list[dict[str, Any]], case_name: str) -> None:
    normalized_expected = [{field: str(row.get(field, "")) for field in FIELDS} for row in expected]
    if actual != normalized_expected:
        raise AssertionError(
            f"{case_name}: settlement rows did not match expected output.\n"
            f"actual={json.dumps(actual, indent=2)}\nexpected={json.dumps(normalized_expected, indent=2)}"
        )


def assert_schema_stable(path: Path, case_name: str) -> None:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, [])
    if header != FIELDS:
        raise AssertionError(f"{case_name}: settlement ledger header changed. actual={header!r} expected={FIELDS!r}")
    leaked = {"_actual_cost_source", "actual_cost_source"}.intersection(header)
    if leaked:
        raise AssertionError(f"{case_name}: confirmation-only cost-source fields leaked into the settlement ledger schema: {sorted(leaked)!r}")


def assert_source_output_evidence_boundary(command: list[str], stdout: str, case_name: str) -> None:
    if command[0] == "list-open":
        fmt = command_value(command, "--format", "text") or "text"
    else:
        fmt = command_value(command, "--output-format", "text") or "text"
    if fmt == "json":
        payload = json.loads(stdout)
        if payload.get("valid_evidence_scope") != settlement_helper_source.SETTLEMENT_HELPER_VALID_EVIDENCE_SCOPE:
            raise AssertionError(f"{case_name}: JSON output lost the source-level valid_evidence_scope")
        if payload.get("evidence_boundary") != settlement_helper_source.SETTLEMENT_HELPER_EVIDENCE_BOUNDARY:
            raise AssertionError(f"{case_name}: JSON output lost the source-level evidence_boundary")
        if payload.get("evidence_boundary_text") != settlement_helper_source.SETTLEMENT_HELPER_BOUNDARY_TEXT:
            raise AssertionError(f"{case_name}: JSON output lost the source-level evidence_boundary_text")
        return
    assert_contains(
        stdout,
        f"valid_evidence_scope={settlement_helper_source.SETTLEMENT_HELPER_VALID_EVIDENCE_SCOPE}",
        case_name,
    )
    assert_contains(stdout, settlement_helper_source.SETTLEMENT_HELPER_BOUNDARY_TEXT, case_name)
    assert_contains(stdout, "not settled ROI evidence by itself", case_name)
    assert_contains(stdout, "not real-money support", case_name)


def rendered_stdout(text: str) -> str:
    return text + "\n"


def command_value(command: list[str], flag: str, default: str | None = None) -> str | None:
    if flag not in command:
        return default
    idx = command.index(flag)
    if idx + 1 >= len(command):
        return default
    return command[idx + 1]


def expected_stdout(case: dict[str, Any], expected_rows: list[dict[str, str]] | None = None) -> str:
    command = case["command"]
    if command[0] == "list-open":
        fmt = command_value(command, "--format", "text") or "text"
        limit = int(command_value(command, "--limit", "20") or "20")
        rendered = settlement_helper_source.render_open_rows(case["rows"], limit, fmt)
        return rendered_stdout(rendered)

    signal_key = command_value(command, "--signal-key")
    if not signal_key:
        raise AssertionError(f"{case['name']}: missing --signal-key in settle command")
    output_format = command_value(command, "--output-format", "text") or "text"
    source_rows = expected_rows or case.get("expected_rows") or []
    updated = next((row for row in source_rows if row.get("signal_key") == signal_key), None)
    if updated is None:
        raise AssertionError(f"{case['name']}: expected updated row for {signal_key} not found")
    rendered = settlement_helper_source.render_settle_confirmation(updated, output_format)
    return rendered_stdout(rendered)


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_root, settlement_path = setup_case(case)
    stdout_path = case_root / "stdout.txt"
    stderr_path = case_root / "stderr.txt"
    cmd = [
        sys.executable,
        str(SCRIPT),
        *case["command"],
        "--settlement-ledger",
        str(settlement_path),
    ]
    result = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")

    if "expect_failure" in case:
        if result.returncode == 0:
            raise AssertionError(f"{case['name']}: expected non-zero exit")
        assert_contains((result.stderr or result.stdout).strip(), case["expect_failure"], case["name"])
        compare_rows(read_csv(settlement_path), case["rows"], case["name"])
        assert_schema_stable(settlement_path, case["name"])
        return {
            "name": case["name"],
            "scenario": case["scenario"],
            "result": "PASS",
            "stdout": str(stdout_path.relative_to(BASE)),
            "settlement_ledger": str(settlement_path.relative_to(BASE)),
            "mode": "expected_failure",
        }

    if result.returncode != 0:
        raise AssertionError(f"{case['name']}: unexpected non-zero exit: {result.stderr}")

    expected_output = expected_stdout(case, case.get("expected_rows"))
    if result.stdout != expected_output:
        raise AssertionError(f"{case['name']}: stdout no longer matches a fresh render from paper_trade_settlement_helper.py")

    stdout = result.stdout.strip()
    assert_source_output_evidence_boundary(case["command"], result.stdout, case["name"])
    for needle in case.get("stdout_needles", []):
        assert_contains(stdout, needle, case["name"])

    if "expected_json" in case:
        payload = json.loads(result.stdout)
        for key, value in case["expected_json"].items():
            if key == "signal_keys":
                actual_keys = [row.get("signal_key", "") for row in payload.get("rows", [])]
                if actual_keys != value:
                    raise AssertionError(f"{case['name']}: expected signal_keys {value!r}, got {actual_keys!r}")
            elif key == "roi_gap_signal_keys":
                actual_keys = [row.get("signal_key", "") for row in payload.get("roi_gap_rows", [])]
                if actual_keys != value:
                    raise AssertionError(f"{case['name']}: expected roi_gap_signal_keys {value!r}, got {actual_keys!r}")
            elif payload.get(key) != value:
                raise AssertionError(f"{case['name']}: expected {key}={value!r}, got {payload.get(key)!r}")

    if "expected_rows" in case:
        compare_rows(read_csv(settlement_path), case["expected_rows"], case["name"])

    assert_schema_stable(settlement_path, case["name"])

    return {
        "name": case["name"],
        "scenario": case["scenario"],
        "result": "PASS",
        "stdout": str(stdout_path.relative_to(BASE)),
        "settlement_ledger": str(settlement_path.relative_to(BASE)),
    }


def validate_help_contract() -> dict[str, Any]:
    help_root = FIXTURE_ROOT / "case_settle_help_documents_cost_source"
    if help_root.exists():
        shutil.rmtree(help_root)
    help_root.mkdir(parents=True, exist_ok=True)
    stdout_path = help_root / "stdout.txt"
    stderr_path = help_root / "stderr.txt"
    result = subprocess.run([sys.executable, str(SCRIPT), "settle", "--help"], cwd=BASE, capture_output=True, text=True)
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise AssertionError(f"settle --help unexpectedly failed: {result.stderr}")
    normalized_stdout = " ".join(result.stdout.split()).replace("non- negative", "non-negative")
    for needle in (
        "--outcome",
        "must be HIT or MISS after the actual race result is known",
        "placeholder values such as <HIT_OR_MISS> are rejected",
        "--actual-return",
        "Actual dollars returned; must be finite and non-negative",
        "--actual-cost",
        "Actual dollars wagered; must be finite and positive",
        "Omit to infer from the row's expected_cost when parseable",
        "confirmation reports actual_cost_source",
        "missing, malformed, zero, or negative expected_cost keeps cost/profit blank",
        "--settled-ts",
        "Actual settlement timestamp in ISO format",
        "blank or placeholder values such as <SETTLED_TS> are rejected when supplied",
        "Omitting this timestamp leaves the row out of ROI-complete sample gates until settled_ts is filled",
    ):
        assert_contains(normalized_stdout, needle, "case_settle_help_documents_cost_source")
    return {
        "name": "case_settle_help_documents_cost_source",
        "scenario": "settle --help documents the expected-cost fallback, cost-source confirmation, and missing/malformed/negative cost boundary",
        "result": "PASS",
        "stdout": str(stdout_path.relative_to(BASE)),
        "settlement_ledger": "n/a (help-only check)",
        "mode": "help_contract",
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
    help_contract = validate_help_contract()
    if BASE.resolve() not in FIXTURE_ROOT.resolve().parents:
        raise AssertionError("settlement-helper fixture root is not project-local")
    scratch = {
        "fixture_root_relative": str(FIXTURE_ROOT.relative_to(BASE)),
        "fixture_root_is_project_local": True,
        "case_roots_cleared_by_setup_case": True,
        "report_root_relative": str(OUT_DIR.relative_to(BASE)),
        "evidence_boundary": "settlement-helper fixture scratch metadata is reproducibility context only, not new forward evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
    }
    child_checks = [
        *scorecard_guardrails,
        {
            "check": "open_queue_rendering_stays_honest_across_formats",
            "status": "pass",
            "detail": "the helper still renders a clean zero-row queue in text mode, keeps markdown queue output human-readable, exposes the same open-row state through JSON, carries row-specific settle command templates with actual result/payout evidence placeholders, and now carries settled-row ROI-gap counts into those queue reads instead of letting zero-open wording hide timestamp/cost gaps",
        },
        {
            "check": "truncation_and_open_row_filtering_stay_explicit",
            "status": "pass",
            "detail": "long open queues still truncate honestly, JSON open-queue output still excludes settled rows from the pending-settlement list, and settled HIT/MISS rows that are missing ROI-complete return/cost/timestamp coverage, including non-positive actual_cost gaps, appear separately as repair work",
        },
        {
            "check": "single_row_settlement_updates_and_profit_math_stay_exact",
            "status": "pass",
            "detail": "settle still updates exactly one matching row by signal_key, leaves neighboring rows untouched, and computes actual_profit when return plus actual cost or expected-cost fallback are available",
        },
        {
            "check": "expected_cost_fallback_and_missing_signal_paths_stay_honest",
            "status": "pass",
            "detail": "settle confirmations now report actual_cost_source explicitly, infer actual_cost and actual_profit from positive expected_cost when actual cost is omitted, keep true missing, malformed, zero, or negative expected-cost rows blank, and still fail loudly on missing signal keys instead of mutating the wrong ledger row",
        },
        {
            "check": "duplicate_signal_keys_fail_before_settlement_mutation",
            "status": "pass",
            "detail": "settle now rejects duplicate signal_key matches before mutating either row, so manually damaged settlement templates cannot quietly update only the first matching signal",
        },
        {
            "check": "outcome_tokens_are_limited_to_actual_hit_or_miss_results",
            "status": "pass",
            "detail": "settle now rejects placeholder or unsupported outcome tokens before mutating the ledger, so copied next-step examples cannot accidentally settle a row with <HIT_OR_MISS> or any non-HIT/MISS value",
        },
        {
            "check": "settlement_amounts_must_be_finite_and_nonnegative",
            "status": "pass",
            "detail": "settle now rejects non-finite or negative actual-return inputs, rejects non-finite or non-positive actual-cost inputs before mutating the ledger, and treats zero or negative expected_cost fallback values as missing rather than computing impossible ROI math",
        },
        {
            "check": "settled_timestamps_must_be_actual_iso_values_when_supplied",
            "status": "pass",
            "detail": "settle now rejects placeholder, blank, or malformed settled-ts inputs before mutating the ledger, while confirmations for timestamp-omitted updates say the row remains outside ROI-complete sample gates until settled_ts is filled",
        },
        {
            "check": "fixture_renders_and_ledger_outputs_match_current_source_layer",
            "status": "pass",
            "detail": "every fixture stdout capture and resulting settlement ledger still has to match a fresh source-layer render or update from paper_trade_settlement_helper.py, every successful text/markdown/JSON helper output now carries source-level valid_evidence_scope plus evidence boundary fields/lines, the direct validator report exposes the same exact valid_evidence_scope line, and the direct validator summary still says plainly this is ledger maintenance rather than new forward evidence",
        },
        {
            "check": "direct_validation_report_exposes_settlement_helper_valid_scope",
            "status": "pass",
            "detail": "the settlement-helper validation JSON, evidence-boundary metadata, summary read, and markdown evidence-boundary section now expose exact valid_evidence_scope=settlement_entry_queue_repair_metadata_only so open queues, timestamp-incomplete updates, and helper fixtures cannot be copied as settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money support",
        },
        {
            "check": "settlement_ledger_schema_stays_stable_while_confirmation_reports_cost_source",
            "status": "pass",
            "detail": "the validator now proves actual_cost_source is a confirmation/reporting field and that temporary _actual_cost_source values do not leak into the persisted settlement CSV header",
        },
        {
            "check": "settle_help_documents_cost_source_and_expected_cost_boundary",
            "status": "pass",
            "detail": "settle --help now tells the operator that omitted actual cost uses parseable positive expected_cost, that confirmations report actual_cost_source, that missing, malformed, zero, or negative expected_cost keeps cost/profit blank, and that omitting settled_ts leaves the row out of ROI-complete sample gates",
        },
        {
            "check": "settlement_helper_preserves_scorecard_gate_boundary",
            "status": "pass",
            "detail": "the settlement-helper validator now publishes the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite while saying helper fixtures, open queues, and timestamp-incomplete settlement updates do not count toward those gates and malformed copied gates fail before fixture/report artifacts",
        },
        {
            "check": "fixture_scratch_metadata_published",
            "status": "pass",
            "detail": "the settlement-helper validator now publishes project-local fixture scratch metadata so parent rollups can verify isolated ledger-fixture hygiene without parsing markdown prose",
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
        raise AssertionError("settlement-helper scorecard gate boundary no longer matches forward_evidence_scorecard.json")

    payload = {
        "suite_status": "pass",
        "artifact_status": "pass",
        "total_fixture_scenarios": len(results),
        "total_checks": len(results),
        "check_count": len(results),
        "child_check_count": len(child_checks),
        "child_checks": child_checks,
        "cases": results,
        "help_contract": help_contract,
        "valid_evidence_scope": settlement_helper_source.SETTLEMENT_HELPER_VALID_EVIDENCE_SCOPE,
        "summary": {
            "current_read": "settlement-helper still lists only open rows across text, markdown, and JSON outputs while separately surfacing settled HIT/MISS rows missing ROI-complete return/cost/timestamp coverage, including non-positive actual_cost gaps, renders row-specific settle command templates with actual result/payout evidence placeholders, truncates long queues honestly, updates exactly one row by signal_key, rejects duplicate signal_key matches before mutation, rejects placeholder or unsupported outcome tokens before mutating the ledger, rejects non-finite or negative actual-return inputs plus non-finite or non-positive actual-cost inputs before mutating the ledger, rejects placeholder, blank, or malformed settled-ts inputs before mutating the ledger when a timestamp is supplied, makes timestamp-omitted settlement confirmations say the row remains outside ROI-complete sample gates until settled_ts is filled, reports actual_cost_source in settlement confirmations without adding cost-source columns to the persisted settlement ledger schema, computes profit when actual cost is supplied or can be inferred from positive expected_cost, keeps true missing, malformed, zero, or negative expected-cost rows blank, documents the outcome, amount, timestamp, timestamp-omission, and cost-source boundaries in settle --help, fails loudly on missing keys, keeps those saved renders pinned to fresh source-layer formatter output, now carries source-level valid_evidence_scope / evidence_boundary / evidence_boundary_text through successful JSON helper outputs and visible valid-scope plus boundary lines through successful text/markdown helper outputs, now publishes exact valid_evidence_scope=settlement_entry_queue_repair_metadata_only in its direct validator report plus project-local fixture scratch metadata at the standard settlement-helper validation path, rejects malformed and non-positive scorecard gates before fixture/report artifacts, and preserves the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that helper fixtures, open queues, and timestamp-incomplete settlement updates do not advance; settlement helper: ledger-maintenance surface, not new forward evidence by itself",
        },
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "scratch": scratch,
        "fixture_root": str(FIXTURE_ROOT.relative_to(BASE)),
        "report_path": str(OUT_DIR.relative_to(BASE)),
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "fixture_root": str(FIXTURE_ROOT.relative_to(BASE)),
            "report_path": str(REPORT_MD.relative_to(BASE)),
        },
    }

    lines = [
        "# Paper-Trade Settlement Helper Validation",
        "",
        "This report validates `paper_trade_settlement_helper.py` directly inside isolated fixture ledgers while publishing the direct validator readout under `out/status_validation/paper_trade_settlement_helper/`.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Fixture root: `{FIXTURE_ROOT.relative_to(BASE)}`",
        f"- Direct report path: `{REPORT_MD.relative_to(BASE)}`",
        f"- Fixture scratch metadata: `{scratch['fixture_root_relative']}` is project-local and each fixture case root is cleared before setup.",
        "",
        "## Cases",
        "",
        "| Case | Scenario | Settlement ledger |",
        "|---|---|---|",
    ]
    for row in results:
        lines.append(f"| `{row['name']}` | {row['scenario']} | `{row['settlement_ledger']}` |")
    lines.append(f"| `{help_contract['name']}` | {help_contract['scenario']} | `{help_contract['settlement_ledger']}` |")

    lines.extend([
        "",
        "## Current Read",
        "",
        f"- Suite read: {payload['summary']['current_read']}",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
        f"- valid_evidence_scope={settlement_helper_source.SETTLEMENT_HELPER_VALID_EVIDENCE_SCOPE}",
        f"- Source valid evidence scope: `{settlement_helper_source.SETTLEMENT_HELPER_VALID_EVIDENCE_SCOPE}`",
        f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
        "- Boundary: settlement-helper validator cleanliness is ledger-maintenance metadata only, not new forward evidence, not a live paper-trade ledger, not a current-day scanner result, not settled ROI, not live profitability, not promotion readiness, and not real-money evidence.",
        "- Non-goals: do not treat helper-rendered open queues, timestamp-incomplete updates, or fixture cleanliness as ROI-complete observations, profitability evidence, promotion support, or real-money support.",
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
        "- The settlement helper still reports an honest zero-row queue when nothing is open.",
        "- Each fixture now requires the saved stdout capture to match a fresh source-layer render from `paper_trade_settlement_helper.py`, whether the helper is emitting text, markdown, or JSON.",
        "- Successful helper outputs and this direct validation report now carry exact `valid_evidence_scope=settlement_entry_queue_repair_metadata_only`; JSON helper outputs also carry `evidence_boundary` and `evidence_boundary_text`, and successful text/markdown helper outputs render the same visible valid-scope plus boundary lines.",
        "- Open-queue text, markdown, and JSON renders now include row-specific `settle` command templates with placeholders that must be replaced only after actual result/payout evidence exists.",
        "- Long open queues still truncate explicitly in markdown output instead of implying the visible rows are the full queue.",
        "- Text, markdown, and JSON queue reads now also show settled rows missing ROI-complete coverage, so `0` open rows cannot hide timestamp/cost/return/non-positive-cost repair work.",
        "- JSON queue output still counts only open rows in the pending-settlement list and reports settled HIT/MISS ROI-gap rows separately.",
        "- `settle` still updates exactly one row by `signal_key`, reports `actual_cost_source`, computes `actual_profit` when positive `actual_cost` is supplied or can be inferred from positive `expected_cost`, and preserves blank cost / profit only when no parseable positive cost source is available.",
        "- `settle` now rejects duplicate `signal_key` matches before mutating the ledger, so a damaged settlement template cannot quietly update only the first matching row.",
        "- `settle` now rejects placeholder or unsupported outcome tokens before mutating the ledger, so copied next-step examples cannot accidentally persist `<HIT_OR_MISS>` or another non-result value.",
        "- `settle` now rejects non-finite or negative `actual-return` inputs, rejects non-finite or non-positive `actual-cost` inputs before mutating the ledger, and treats zero or negative `expected_cost` fallback values as missing rather than computing impossible ROI math.",
        "- `settle` now rejects placeholder, blank, or malformed `settled-ts` values before mutating the ledger when a timestamp is supplied, so copied examples cannot persist `<SETTLED_TS>` as if it were an actual settlement time.",
        "- When `settle` is run without `--settled-ts`, text and JSON confirmations now say the row remains outside ROI-complete sample gates until `settled_ts` is filled.",
        "- The persisted settlement ledger schema stays stable: `actual_cost_source` is confirmation/reporting context, and temporary `_actual_cost_source` fields do not leak into the CSV header.",
        "- `settle --help` now documents the accepted `HIT` / `MISS` outcome boundary, non-negative amount boundary, ISO timestamp boundary, timestamp-omission consequence, expected-cost fallback, `actual_cost_source` confirmation field, and missing/malformed cost-source boundary so the operator sees the same rule before editing a ledger row.",
        "- Missing `signal_key` updates still fail loudly instead of mutating the wrong row or silently succeeding.",
        "- Malformed copied scorecard gates, including boolean anchor floors, non-positive Phase 8 / real-money floors, and a missing no-BAQ-as-BEL prerequisite, now fail before nested settlement-helper fixture/report artifacts are created.",
        "",
        "## Sources",
        "",
    ])
    for row in results:
        lines.append(f"- `{row['stdout']}`")
        lines.append(f"- `{row['settlement_ledger']}`")
    lines.append(f"- `{help_contract['stdout']}`")

    for legacy in (
        FIXTURE_ROOT / "settlement_helper_fixture_validation.md",
        FIXTURE_ROOT / "settlement_helper_fixture_validation.json",
    ):
        legacy.unlink(missing_ok=True)

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    for row in results:
        if row.get("mode") == "expected_failure":
            print(f"PASS {row['name']}: expected failure")
        else:
            print(f"PASS {row['name']}: {row['settlement_ledger']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
