#!/usr/bin/env python3
"""
Fixture-driven validation for paper_trade_settlement_audit.py.

Purpose:
- pin the direct settlement-ledger completeness audit before forward ROI is interpreted
- prove structural ledger gaps and settled-row ROI-coverage gaps are surfaced separately
- keep the audit's evidence boundary explicit: no deployment or profitability claim follows
  from this artifact by itself
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import paper_trade_settlement_audit as audit

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "paper_trade_settlement_audit.py"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "settlement_audit_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_settlement_audit"
REPORT_MD = OUT_DIR / "paper_trade_settlement_audit_validation.md"
REPORT_JSON = OUT_DIR / "paper_trade_settlement_audit_validation.json"
REBUILD_COMMAND = "python3 validate_paper_trade_settlement_audit.py"
VALID_EVIDENCE_SCOPE = audit.SETTLEMENT_AUDIT_VALID_EVIDENCE_SCOPE
EVIDENCE_BOUNDARY = {
    "artifact_role": "paper-trade settlement-audit validator",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "valid_use": "settlement-audit fixture and saved-live ledger-quality guardrail metadata only",
    "not_new_forward_evidence_by_itself": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_anchor_change_evidence": True,
    "not_phase8_promotion_evidence": True,
    "not_real_money_evidence": True,
    "not_baq_as_bel_evidence": True,
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


def assert_contains(text: str, needle: str, case_name: str) -> None:
    if needle not in text:
        raise AssertionError(f"{case_name}: expected to find {needle!r}")


def assert_not_contains(text: str, needle: str, case_name: str) -> None:
    if needle in text:
        raise AssertionError(f"{case_name}: did not expect to find {needle!r}")


def source_fingerprint_matches_disk(fp: dict[str, Any]) -> bool:
    path_text = str(fp.get("path") or "").strip()
    if not path_text:
        return False
    path = Path(path_text)
    if not path.is_absolute():
        path = BASE / path
    return audit.file_fingerprint(path) == fp


def has_timezone_aware_generated_at(payload: dict[str, Any]) -> bool:
    value = payload.get("generated_at")
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def signal_row(
    signal_key: str,
    *,
    rule_id: str = "OP_DURABLE_K7",
    track: str = "OP",
    race_number: str = "7",
    estimated_cost: str = "24.00",
) -> dict[str, Any]:
    return {
        "signal_key": signal_key,
        "scan_ts": "2026-05-23T11:00:00",
        "rule_id": rule_id,
        "track": track,
        "card_name": "Oaklawn Park" if track == "OP" else "Churchill Downs",
        "race_number": race_number,
        "race_id": f"{track}-2026-05-23-R{race_number}",
        "surface": "dirt",
        "condition": "fast",
        "field_size": "11",
        "favorite_program": "1",
        "favorite_name": "Fixture Favorite",
        "favorite_prob": "0.34",
        "second_prob": "0.20",
        "prob_gap": "0.14",
        "k": "7" if rule_id == "OP_DURABLE_K7" else "8",
        "base_stake": "1",
        "estimated_cost": estimated_cost,
        "underneath_programs": "2,3,4,5",
        "ticket_structure": "1 / 2,3,4,5",
        "status": "",
        "outcome": "",
        "notes": "fixture",
    }


def settlement_row(
    signal_key: str,
    *,
    rule_id: str = "OP_DURABLE_K7",
    track: str = "OP",
    race_number: str = "7",
    expected_cost: str = "24.00",
    settlement_status: str = "open",
    outcome: str = "",
    actual_cost: str = "",
    actual_return: str = "",
    actual_profit: str = "",
    settled_ts: str | None = None,
) -> dict[str, Any]:
    if settled_ts is None:
        settled_ts = "2026-05-23T19:30:00" if settlement_status == "settled" else ""
    return {
        "signal_key": signal_key,
        "scan_ts": "2026-05-23T11:00:00",
        "rule_id": rule_id,
        "track": track,
        "card_name": "Oaklawn Park" if track == "OP" else "Churchill Downs",
        "race_number": race_number,
        "race_id": f"{track}-2026-05-23-R{race_number}",
        "expected_cost": expected_cost,
        "settlement_status": settlement_status,
        "outcome": outcome,
        "actual_cost": actual_cost,
        "actual_return": actual_return,
        "actual_profit": actual_profit,
        "settled_ts": settled_ts,
        "notes": "fixture settlement",
    }


CASES: list[dict[str, Any]] = [
    {
        "name": "case_empty_header_only_ledgers_stay_pre_evidence",
        "scenario": "empty/header-only signal and settlement ledgers are aligned but remain pre-evidence",
        "signals": [],
        "settlements": [],
        "expected": {
            "assessment": "pre_evidence_waiting_for_roi_complete_settlements",
            "signal_rows": 0,
            "settlement_rows": 0,
            "missing_settlement_template_count": 0,
            "orphan_settlement_count": 0,
            "roi_complete_settled_rows": 0,
            "roi_gap_settled_rows": 0,
            "next_action": "collect_signals",
        },
        "stdout_needles": ["ledger-completeness / ROI-coverage audit only", "0 ROI-complete settled row(s)", "`collect_signals`"],
    },
    {
        "name": "case_structural_gaps_are_separated_from_settlement_quality",
        "scenario": "missing templates, orphan settlements, blank signal/settlement keys, duplicate keys, and matched-key metadata mismatches are flagged as structural ledger repairs",
        "signals": [
            signal_row("dup_key"),
            signal_row("dup_key"),
            signal_row("missing_template"),
            signal_row("metadata_mismatch", rule_id="OP_DURABLE_K7", track="OP"),
            signal_row(""),
        ],
        "settlements": [
            settlement_row("dup_key"),
            settlement_row("orphan_key"),
            settlement_row("orphan_key"),
            settlement_row("metadata_mismatch", rule_id="CD_CORE_K8", track="CD"),
            settlement_row(""),
        ],
        "expected": {
            "assessment": "ledger_structure_repair_required",
            "signal_rows": 5,
            "settlement_rows": 5,
            "blank_signal_key_rows": 1,
            "blank_settlement_key_rows": 1,
            "duplicate_signal_key_count": 1,
            "duplicate_settlement_key_count": 1,
            "missing_settlement_template_count": 1,
            "orphan_settlement_count": 1,
            "metadata_mismatch_count": 1,
            "next_action": "repair_ledger_structure",
        },
        "stdout_needles": [
            "ledger_structure_repair_required",
            "`repair_ledger_structure`",
            "1 blank signal-key row(s) in signal ledger",
            "1 blank settlement-key row(s) in settlement ledger",
            "missing settlement templates: missing_template",
            "orphan settlement rows: orphan_key",
            "metadata mismatches: metadata_mismatch",
        ],
        "stdout_forbidden": ["blank signal-key row(s) in settlement ledger"],
    },
    {
        "name": "case_settled_row_quality_gaps_carry_explicit_roi_reasons",
        "scenario": "settled rows missing outcome or usable return/cost coverage are repair items, not forward evidence",
        "signals": [
            signal_row("needs_outcome"),
            signal_row("missing_return"),
            signal_row("malformed_cost"),
            signal_row("missing_all_cost"),
        ],
        "settlements": [
            settlement_row("needs_outcome", settlement_status="settled", outcome=""),
            settlement_row("missing_return", settlement_status="settled", outcome="HIT", actual_cost="24.00", actual_return=""),
            settlement_row("malformed_cost", settlement_status="settled", outcome="MISS", actual_cost="abc", actual_return="0"),
            settlement_row("missing_all_cost", expected_cost="", settlement_status="settled", outcome="MISS", actual_cost="", actual_return="0"),
        ],
        "expected": {
            "assessment": "settlement_quality_repair_required",
            "incomplete_settled_rows": 1,
            "settled_outcome_rows": 3,
            "roi_complete_settled_rows": 0,
            "roi_gap_settled_rows": 3,
            "roi_gap_reason_counts": {
                "malformed actual_cost": 1,
                "missing actual_cost and expected_cost": 1,
                "missing actual_return": 1,
            },
            "next_action": "complete_settlement_outcomes",
        },
        "stdout_needles": ["settlement_quality_repair_required", "`complete_settlement_outcomes`", "missing actual_return: 1", "malformed actual_cost: 1", "missing actual_cost and expected_cost: 1"],
    },
    {
        "name": "case_settled_timestamp_gaps_block_roi_complete_rows",
        "scenario": "settled rows with missing, placeholder, or malformed settled_ts values stay repair items even when return/cost coverage is usable",
        "signals": [
            signal_row("missing_ts"),
            signal_row("placeholder_ts"),
            signal_row("malformed_ts"),
            signal_row("complete_ts"),
        ],
        "settlements": [
            settlement_row("missing_ts", settlement_status="settled", outcome="HIT", actual_cost="24.00", actual_return="96.00", settled_ts=""),
            settlement_row("placeholder_ts", settlement_status="settled", outcome="MISS", actual_cost="24.00", actual_return="0.00", settled_ts="<SETTLED_TS>"),
            settlement_row("malformed_ts", settlement_status="settled", outcome="MISS", actual_cost="24.00", actual_return="0.00", settled_ts="2026-05-23"),
            settlement_row("complete_ts", settlement_status="settled", outcome="MISS", actual_cost="24.00", actual_return="0.00", settled_ts="2026-05-23T19:30:00"),
        ],
        "expected": {
            "assessment": "settlement_quality_repair_required",
            "incomplete_settled_rows": 0,
            "settled_outcome_rows": 4,
            "roi_complete_settled_rows": 1,
            "roi_gap_settled_rows": 3,
            "roi_gap_reason_counts": {
                "malformed settled_ts": 1,
                "missing settled_ts": 1,
                "placeholder settled_ts": 1,
            },
            "next_action": "repair_roi_coverage",
        },
        "stdout_needles": ["settlement_quality_repair_required", "`repair_roi_coverage`", "missing settled_ts: 1", "placeholder settled_ts: 1", "malformed settled_ts: 1"],
    },
    {
        "name": "case_non_positive_cost_gaps_block_roi_complete_rows",
        "scenario": "settled rows with zero actual or expected cost stay repair items rather than sample-complete ROI rows",
        "signals": [
            signal_row("zero_actual_cost"),
            signal_row("zero_expected_cost", estimated_cost="0.00"),
            signal_row("complete_positive_cost"),
        ],
        "settlements": [
            settlement_row("zero_actual_cost", settlement_status="settled", outcome="MISS", actual_cost="0.00", actual_return="0.00"),
            settlement_row("zero_expected_cost", expected_cost="0.00", settlement_status="settled", outcome="MISS", actual_cost="", actual_return="0.00"),
            settlement_row("complete_positive_cost", settlement_status="settled", outcome="MISS", actual_cost="24.00", actual_return="0.00"),
        ],
        "expected": {
            "assessment": "settlement_quality_repair_required",
            "incomplete_settled_rows": 0,
            "settled_outcome_rows": 3,
            "roi_complete_settled_rows": 1,
            "roi_gap_settled_rows": 2,
            "roi_gap_reason_counts": {
                "non-positive actual_cost": 1,
                "non-positive expected_cost": 1,
            },
            "next_action": "repair_roi_coverage",
        },
        "stdout_needles": ["settlement_quality_repair_required", "`repair_roi_coverage`", "non-positive actual_cost: 1", "non-positive expected_cost: 1"],
    },
    {
        "name": "case_roi_complete_rows_feed_milestones_without_profit_claims",
        "scenario": "ROI-complete settled rows count toward first-read milestones but still do not create standalone profit proof",
        "signals": [signal_row("complete_hit"), signal_row("complete_miss")],
        "settlements": [
            settlement_row("complete_hit", settlement_status="settled", outcome="HIT", actual_cost="24.00", actual_return="180.00"),
            settlement_row("complete_miss", settlement_status="settled", outcome="MISS", actual_cost="", actual_return="0.00", expected_cost="30.00"),
        ],
        "extra_args": ["--min-settled", "3", "--portfolio-review-settled", "5"],
        "expected": {
            "assessment": "collecting_first_read_pre_evidence",
            "roi_complete_settled_rows": 2,
            "roi_gap_settled_rows": 0,
            "first_read_progress": "2/3 (66.7%)",
            "portfolio_review_progress": "2/5 (40.0%)",
            "roi_complete_cost_sum": 54.0,
            "roi_complete_return_sum": 180.0,
            "next_action": "continue_collecting_roi_complete_settlements",
        },
        "stdout_needles": ["collecting_first_read_pre_evidence", "`continue_collecting_roi_complete_settlements`", "2/3 (66.7%)", "Only settled paper trades with usable return/cost coverage"],
    },
]


def setup_case(case: dict[str, Any]) -> tuple[Path, Path, Path, Path, Path]:
    case_root = FIXTURE_ROOT / case["name"]
    if case_root.exists():
        shutil.rmtree(case_root)
    case_root.mkdir(parents=True, exist_ok=True)
    signals_path = case_root / "signals.csv"
    settlement_path = case_root / "settlements.csv"
    md_path = case_root / "audit.md"
    json_path = case_root / "audit.json"
    write_csv(signals_path, SIGNAL_FIELDS, case["signals"])
    write_csv(settlement_path, SETTLEMENT_FIELDS, case["settlements"])
    return case_root, signals_path, settlement_path, md_path, json_path


def assert_expected(actual: dict[str, Any], expected: dict[str, Any], case_name: str) -> None:
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if actual_value != expected_value:
            raise AssertionError(f"{case_name}: expected {key}={expected_value!r}, got {actual_value!r}")


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_root, signals_path, settlement_path, md_path, json_path = setup_case(case)
    stdout_path = case_root / "stdout.md"
    lane_label = case["name"].replace(",", "-")
    lane_arg = f"fixture,{lane_label},{signals_path},{settlement_path},fixture lane under audit"
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--lane",
        lane_arg,
        "--output-md",
        str(md_path),
        "--output-json",
        str(json_path),
    ] + case.get("extra_args", [])
    result = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, check=True)
    stdout = result.stdout
    stdout_path.write_text(stdout, encoding="utf-8")

    for needle in case.get("stdout_needles", []):
        assert_contains(stdout, needle, case["name"])
    for needle in case.get("stdout_forbidden", []):
        assert_not_contains(stdout, needle, case["name"])

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if payload.get("artifact_status") != "pass":
        raise AssertionError(f"{case['name']}: expected artifact_status pass")
    if not has_timezone_aware_generated_at(payload):
        raise AssertionError(f"{case['name']}: generated_at must be timezone-aware ISO metadata")
    if payload.get("valid_evidence_scope") != audit.SETTLEMENT_AUDIT_VALID_EVIDENCE_SCOPE:
        raise AssertionError(f"{case['name']}: settlement audit JSON lost the source valid_evidence_scope")
    if payload.get("evidence_boundary_text") != audit.SETTLEMENT_AUDIT_EVIDENCE_BOUNDARY_TEXT:
        raise AssertionError(f"{case['name']}: settlement audit JSON lost the source evidence_boundary_text")
    if payload["summary"].get("evidence_boundary") != audit.SETTLEMENT_AUDIT_EVIDENCE_BOUNDARY_TEXT:
        raise AssertionError(f"{case['name']}: settlement audit summary boundary drifted from the source text")
    if payload["evidence_boundary_metadata"].get("valid_evidence_scope") != audit.SETTLEMENT_AUDIT_VALID_EVIDENCE_SCOPE:
        raise AssertionError(f"{case['name']}: settlement audit metadata lost the source valid_evidence_scope")
    assert_contains(payload["summary"]["current_read"], "not new forward evidence by itself", case["name"])
    assert_contains(payload["summary"]["current_read"], "BAQ is not BEL", case["name"])
    lane = payload["lanes"][0]
    assert_expected(lane, case["expected"], case["name"])
    md_text = md_path.read_text(encoding="utf-8")
    assert_contains(md_text, f"valid_evidence_scope={audit.SETTLEMENT_AUDIT_VALID_EVIDENCE_SCOPE}", case["name"])
    assert_contains(md_text, audit.SETTLEMENT_AUDIT_EVIDENCE_BOUNDARY_TEXT, case["name"])
    assert_contains(md_text, "## Next Actions", case["name"])
    assert_contains(md_text, f"`{case['expected']['next_action']}`", case["name"])

    return {
        "name": case["name"],
        "scenario": case["scenario"],
        "result": "PASS",
        "audit_md": str(md_path.relative_to(BASE)),
        "audit_json": str(json_path.relative_to(BASE)),
        "stdout": str(stdout_path.relative_to(BASE)),
        "assessment": lane["assessment"],
        "next_action": lane["next_action"],
    }


def run_live_default() -> dict[str, Any]:
    live_md = BASE / "out" / "paper_trade_settlement_audit.md"
    live_json = BASE / "out" / "paper_trade_settlement_audit.json"
    cmd = [sys.executable, str(SCRIPT), "--output-md", str(live_md), "--output-json", str(live_json)]
    result = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, check=True)
    stdout = result.stdout
    for needle in (
        "Paper Trade Settlement Audit",
        "OP_DURABLE_K7",
        "CD_CORE_K8",
        "OP_REFINED_K7",
        "BAQ` is not `BEL`",
        "Only settled paper trades with usable return/cost coverage",
        f"valid_evidence_scope={audit.SETTLEMENT_AUDIT_VALID_EVIDENCE_SCOPE}",
        "Settlement-audit output is ledger-completeness / ROI-coverage metadata only",
        "Machine-readable boundary: `evidence_boundary_metadata.artifact_role`",
        "green_audit_is_not_profit_proof=true",
        "roi_complete_counts_are_sample_coverage_not_profitability=true",
        "not_real_money_evidence=true",
        "## Decision-Gate Source",
        "forward_evidence_scorecard.json",
        "Scorecard `decision_gate_minimums`",
        "anchor_displacement=30",
        "phase8_promotion_review=20",
        "real_money_discussion=100",
        "real_money_requires=positive paper ROI; concentration checks; payout-distribution sanity checks; no BAQ-as-BEL substitution",
        "loaded=True",
        "## Promotion Gates",
        "Shadow/watch phase8_promotion_review gate is per-rule",
        "the 20-row count is a review floor, not a promotion entitlement",
        "scorecard tiers remain binding",
        "negative-holdout/SKIP rules still need cleaner split-aware evidence",
        "OP_REFINED_K7 (WATCH) 0/20",
        "CD_REFINED_K9 (SKIP)",
        "lane totals alone do not promote OP_REFINED_K7",
        "## Next Actions",
        "## Source Fingerprints",
        "forward_evidence_scorecard_json",
        "primary_signals_ledger",
        "primary_settlement_ledger",
        "primary_rules_json",
        "shadow_signals_ledger",
        "shadow_settlement_ledger",
        "shadow_rules_json",
    ):
        assert_contains(stdout, needle, "live_default")
    payload = json.loads(live_json.read_text(encoding="utf-8"))
    if not has_timezone_aware_generated_at(payload):
        raise AssertionError("live_default: generated_at must be timezone-aware ISO metadata")
    if payload.get("valid_evidence_scope") != audit.SETTLEMENT_AUDIT_VALID_EVIDENCE_SCOPE:
        raise AssertionError("live_default: expected top-level settlement-audit valid_evidence_scope")
    if payload.get("evidence_boundary_text") != audit.SETTLEMENT_AUDIT_EVIDENCE_BOUNDARY_TEXT:
        raise AssertionError("live_default: expected top-level settlement-audit evidence_boundary_text")
    if payload["summary"].get("evidence_boundary") != audit.SETTLEMENT_AUDIT_EVIDENCE_BOUNDARY_TEXT:
        raise AssertionError("live_default: summary evidence_boundary drifted from source text")
    if len(payload.get("lanes", [])) != 2:
        raise AssertionError("live_default: expected primary and shadow lanes")
    boundary = payload.get("evidence_boundary_metadata", {})
    if not isinstance(boundary, dict):
        raise AssertionError("live_default: expected evidence_boundary_metadata object")
    if boundary.get("valid_evidence_scope") != audit.SETTLEMENT_AUDIT_VALID_EVIDENCE_SCOPE:
        raise AssertionError("live_default: evidence_boundary_metadata lost valid_evidence_scope")
    assert_contains(payload["summary"]["current_read"], "ledger-completeness / ROI-coverage audit only", "live_default")
    assert_contains(payload["summary"]["current_read"], "current odds-only XGBoost remains research-only", "live_default")
    lane_names = {lane["name"] for lane in payload["lanes"]}
    if lane_names != {"primary", "shadow"}:
        raise AssertionError(f"live_default: unexpected lane names {lane_names!r}")
    shadow_lane = next(lane for lane in payload["lanes"] if lane["name"] == "shadow")
    shadow_progress = {
        row["rule_id"]: row
        for row in shadow_lane.get("promotion_gate", {}).get("rule_progress", [])
    }
    cd_refined = shadow_progress.get("CD_REFINED_K9")
    if not cd_refined:
        raise AssertionError("live_default: missing CD_REFINED_K9 shadow rule progress")
    cd_refined_line = (
        f"CD_REFINED_K9 ({cd_refined['scorecard_tier']}) "
        f"{cd_refined['promotion_progress']}"
    )
    assert_contains(stdout, cd_refined_line, "live_default")
    if bool(cd_refined.get("promotion_ready")):
        raise AssertionError("live_default: CD_REFINED_K9 must not be promotion-ready from current live audit")
    expected_sources = {
        "forward_evidence_scorecard_json",
        "primary_signals_ledger",
        "primary_settlement_ledger",
        "primary_rules_json",
        "shadow_signals_ledger",
        "shadow_settlement_ledger",
        "shadow_rules_json",
    }
    source_files = payload.get("source_files", {})
    if set(source_files) != expected_sources:
        raise AssertionError(f"live_default: unexpected source_files keys {sorted(source_files)!r}")
    for label, fp in source_files.items():
        if fp.get("exists") is not True or int(fp.get("bytes", 0) or 0) <= 0 or len(str(fp.get("sha256") or "")) != 64:
            raise AssertionError(f"live_default: malformed fingerprint for {label}: {fp!r}")
        if not source_fingerprint_matches_disk(fp):
            raise AssertionError(f"live_default: fingerprint drift for {label}: {fp!r}")
    return {
        "name": "live_default_two_lane_audit",
        "scenario": "default live audit renders primary and shadow settlement ledgers with the report-safe evidence boundary",
        "result": "PASS",
        "audit_md": str(live_md.relative_to(BASE)),
        "audit_json": str(live_json.relative_to(BASE)),
        "stdout": "stdout not persisted for live default",
        "assessment": ", ".join(f"{lane['name']}={lane['assessment']}" for lane in payload["lanes"]),
        "next_action": ", ".join(f"{lane['name']}={lane['next_action']}" for lane in payload["lanes"]),
    }


def run_duplicate_lane_name_failure_case() -> dict[str, Any]:
    case_name = "case_duplicate_lane_names_fail_before_outputs"
    case_root = FIXTURE_ROOT / case_name
    if case_root.exists():
        shutil.rmtree(case_root)
    case_root.mkdir(parents=True, exist_ok=True)
    output_dir = case_root / "nested" / "outputs"
    md_path = output_dir / "audit.md"
    json_path = output_dir / "audit.json"
    stdout_path = case_root / "stdout.txt"
    stderr_path = case_root / "stderr.txt"
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--lane",
        f"duplicate,First lane,{case_root / 'signals_a.csv'},{case_root / 'settlements_a.csv'},fixture role",
        "--lane",
        f"duplicate,Second lane,{case_root / 'signals_b.csv'},{case_root / 'settlements_b.csv'},fixture role",
        "--output-md",
        str(md_path),
        "--output-json",
        str(json_path),
    ]
    result = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    if result.returncode == 0:
        raise AssertionError(f"{case_name}: expected duplicate lane names to fail")
    assert_contains(
        (result.stderr or result.stdout).strip(),
        "duplicate lane name in --lane overrides: duplicate; use unique lane names so audit lane payloads and source fingerprints stay unambiguous",
        case_name,
    )
    if output_dir.exists() or md_path.exists() or json_path.exists():
        raise AssertionError(f"{case_name}: duplicate lane failure created output artifacts")
    return {
        "name": case_name,
        "scenario": "duplicate custom lane names fail before audit markdown/json outputs or their parent directory are created",
        "result": "PASS",
        "audit_md": str(md_path.relative_to(BASE)) + " (not created)",
        "audit_json": str(json_path.relative_to(BASE)) + " (not created)",
        "stdout": str(stdout_path.relative_to(BASE)),
        "stderr": str(stderr_path.relative_to(BASE)),
        "assessment": "expected_failure_no_outputs",
        "next_action": "use_unique_lane_names",
        "mode": "expected_failure",
    }


def require(condition: bool, label: str, detail: str) -> dict[str, str]:
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    return {"check": label, "status": "pass", "detail": detail}


def main() -> int:
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = [run_case(case) for case in CASES]
    live_result = run_live_default()
    results.append(live_result)
    duplicate_lane_failure = run_duplicate_lane_name_failure_case()
    results.append(duplicate_lane_failure)

    live_payload = json.loads((BASE / live_result["audit_json"]).read_text(encoding="utf-8"))
    fixture_payloads = [
        json.loads((BASE / row["audit_json"]).read_text(encoding="utf-8"))
        for row in results
        if row["name"] != "live_default_two_lane_audit" and row.get("mode") != "expected_failure"
    ]
    live_lane_map = {lane["name"]: lane for lane in live_payload["lanes"]}
    live_md_text = (BASE / live_result["audit_md"]).read_text(encoding="utf-8")
    shadow_gate = live_lane_map["shadow"]["promotion_gate"]
    live_gate_minimums = live_payload["decision_gate_minimums"]
    override_fixture_gate_minimums = fixture_payloads[5]["decision_gate_minimums"]
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
    lowered_gate_minimums = audit.load_scorecard_gate_minimums(lowered_gate_path)
    boolean_gate_path = FIXTURE_ROOT / "boolean_scorecard_gate_minimums.json"
    boolean_gate_path.write_text(
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
    boolean_gate_minimums = audit.load_scorecard_gate_minimums(boolean_gate_path)
    nonpositive_phase8_gate_path = FIXTURE_ROOT / "nonpositive_phase8_scorecard_gate_minimums.json"
    nonpositive_phase8_gate_path.write_text(
        json.dumps(
            {
                "decision_gate_minimums": {
                    "anchor_displacement": {"min_roi_complete_settled_observations": 30},
                    "phase8_promotion_review": {"min_roi_complete_settled_observations": 0},
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
    nonpositive_phase8_gate_minimums = audit.load_scorecard_gate_minimums(nonpositive_phase8_gate_path)
    nonpositive_real_money_gate_path = FIXTURE_ROOT / "nonpositive_real_money_scorecard_gate_minimums.json"
    nonpositive_real_money_gate_path.write_text(
        json.dumps(
            {
                "decision_gate_minimums": {
                    "anchor_displacement": {"min_roi_complete_settled_observations": 30},
                    "phase8_promotion_review": {"min_roi_complete_settled_observations": 20},
                    "real_money_discussion": {
                        "min_total_settled_observations_with_usable_roi": 0,
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
    nonpositive_real_money_gate_minimums = audit.load_scorecard_gate_minimums(nonpositive_real_money_gate_path)
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
    missing_no_baq_gate_minimums = audit.load_scorecard_gate_minimums(missing_no_baq_gate_path)
    if BASE.resolve() not in FIXTURE_ROOT.resolve().parents:
        raise AssertionError("settlement-audit fixture root is not project-local")
    scratch = {
        "fixture_root_relative": str(FIXTURE_ROOT.relative_to(BASE)),
        "fixture_root_is_project_local": True,
        "case_roots_cleared_by_setup_case": True,
        "report_root_relative": str(OUT_DIR.relative_to(BASE)),
        "evidence_boundary": "settlement-audit fixture scratch metadata is reproducibility context only, not new forward evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
    }

    child_checks = [
        require(
            fixture_payloads[0]["lanes"][0]["assessment"] == "pre_evidence_waiting_for_roi_complete_settlements"
            and fixture_payloads[0]["lanes"][0]["roi_complete_settled_rows"] == 0
            and fixture_payloads[0]["lanes"][0]["next_action"] == "collect_signals",
            "empty_header_only_ledgers_stay_aligned_but_pre_evidence",
            "header-only signal and settlement ledgers render as structurally aligned but still pre-evidence because no ROI-complete settled rows exist, with a direct collect-signals next action instead of a performance read",
        ),
        require(
            fixture_payloads[1]["lanes"][0]["assessment"] == "ledger_structure_repair_required"
            and fixture_payloads[1]["lanes"][0]["missing_settlement_template_count"] == 1
            and fixture_payloads[1]["lanes"][0]["orphan_settlement_count"] == 1
            and fixture_payloads[1]["lanes"][0]["blank_signal_key_rows"] == 1
            and fixture_payloads[1]["lanes"][0]["blank_settlement_key_rows"] == 1
            and fixture_payloads[1]["lanes"][0]["duplicate_signal_key_count"] == 1
            and fixture_payloads[1]["lanes"][0]["duplicate_settlement_key_count"] == 1
            and fixture_payloads[1]["lanes"][0]["metadata_mismatch_count"] == 1
            and fixture_payloads[1]["lanes"][0]["next_action"] == "repair_ledger_structure",
            "structural_template_orphan_blank_and_duplicate_gaps_are_flagged",
            "missing settlement templates, stale/orphan settlement rows, blank signal-key rows, blank settlement-key rows, duplicate keys, and matched-key metadata mismatches remain separate structural repair signals before settlement quality is interpreted, with a direct repair-ledger-structure next action",
        ),
        require(
            fixture_payloads[2]["lanes"][0]["assessment"] == "settlement_quality_repair_required"
            and fixture_payloads[2]["lanes"][0]["incomplete_settled_rows"] == 1
            and fixture_payloads[2]["lanes"][0]["roi_gap_reason_counts"] == {
                "malformed actual_cost": 1,
                "missing actual_cost and expected_cost": 1,
                "missing actual_return": 1,
            }
            and fixture_payloads[2]["lanes"][0]["next_action"] == "complete_settlement_outcomes",
            "settled_row_roi_coverage_gap_reasons_stay_explicit",
            "settled rows missing outcome or usable ROI coverage stay visible with explicit missing-return, malformed-cost, and missing-cost reason counts, and outcome completion stays ahead of ROI interpretation",
        ),
        require(
            fixture_payloads[3]["lanes"][0]["assessment"] == "settlement_quality_repair_required"
            and fixture_payloads[3]["lanes"][0]["roi_complete_settled_rows"] == 1
            and fixture_payloads[3]["lanes"][0]["roi_gap_reason_counts"] == {
                "malformed settled_ts": 1,
                "missing settled_ts": 1,
                "placeholder settled_ts": 1,
            }
            and fixture_payloads[3]["lanes"][0]["next_action"] == "repair_roi_coverage",
            "settled_ts_gaps_block_roi_complete_rows",
            "settled rows with usable return/cost values still stay out of audit-grade ROI-complete counts when settled_ts is missing, placeholder, or malformed, so timestamp repair happens before sample milestones advance",
        ),
        require(
            fixture_payloads[4]["lanes"][0]["roi_complete_settled_rows"] == 1
            and fixture_payloads[4]["lanes"][0]["roi_gap_reason_counts"] == {
                "non-positive actual_cost": 1,
                "non-positive expected_cost": 1,
            }
            and fixture_payloads[4]["lanes"][0]["next_action"] == "repair_roi_coverage",
            "non_positive_cost_gaps_block_roi_complete_rows",
            "settled rows with zero actual_cost or zero expected-cost fallback stay out of audit-grade ROI-complete counts so sample milestones require a positive realized or expected ticket cost",
        ),
        require(
            fixture_payloads[5]["lanes"][0]["roi_complete_settled_rows"] == 2
            and fixture_payloads[5]["lanes"][0]["first_read_progress"] == "2/3 (66.7%)"
            and fixture_payloads[5]["lanes"][0]["assessment"] == "collecting_first_read_pre_evidence"
            and fixture_payloads[5]["lanes"][0]["next_action"] == "continue_collecting_roi_complete_settlements",
            "roi_complete_rows_feed_milestones_without_profit_claims",
            "ROI-complete settled rows count toward the first-read and portfolio-review milestones without being framed as standalone profitability proof, and the direct next action stays on collecting enough ROI-complete settlements",
        ),
        require(
            {lane["name"] for lane in live_payload["lanes"]} == {"primary", "shadow"}
            and all(lane.get("next_action") for lane in live_payload["lanes"])
            and "OP_DURABLE_K7 remains the safest OP anchor" in live_payload["summary"]["current_read"]
            and "BAQ is not BEL" in live_payload["summary"]["current_read"]
            and "not new forward evidence by itself" in live_payload["summary"]["current_read"]
            and set(live_payload.get("source_files", {})) == {
                "forward_evidence_scorecard_json",
                "primary_signals_ledger",
                "primary_settlement_ledger",
                "primary_rules_json",
                "shadow_signals_ledger",
                "shadow_settlement_ledger",
                "shadow_rules_json",
            }
            and all(source_fingerprint_matches_disk(fp) for fp in live_payload.get("source_files", {}).values()),
            "live_default_audit_keeps_two_lane_hierarchy_and_evidence_boundary",
            "the saved live settlement audit renders both primary and shadow lanes while preserving the unchanged OP/CD/shadow hierarchy, BAQ/BEL warning, next-action guidance, no-new-evidence boundary, and source fingerprint parity for scorecard/rules/signals/settlements",
        ),
        require(
            live_payload["valid_evidence_scope"] == audit.SETTLEMENT_AUDIT_VALID_EVIDENCE_SCOPE
            and live_payload["evidence_boundary_text"] == audit.SETTLEMENT_AUDIT_EVIDENCE_BOUNDARY_TEXT
            and live_payload["summary"]["evidence_boundary"] == audit.SETTLEMENT_AUDIT_EVIDENCE_BOUNDARY_TEXT
            and live_payload["evidence_boundary_metadata"]["artifact_role"]
            == "paper-trade settlement ledger completeness / ROI-coverage audit"
            and live_payload["evidence_boundary_metadata"]["valid_evidence_scope"]
            == audit.SETTLEMENT_AUDIT_VALID_EVIDENCE_SCOPE
            and live_payload["evidence_boundary_metadata"]["decision_gate_source"]
            == "forward_evidence_scorecard.json decision_gate_minimums"
            and live_payload["evidence_boundary_metadata"]["decision_gate_source_loaded"] is True
            and live_payload["evidence_boundary_metadata"]["decision_gate_fallback_used"] is False
            and live_payload["evidence_boundary_metadata"]["anchor_displacement_min_roi_complete_settled_observations"] == 30
            and live_payload["evidence_boundary_metadata"]["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and live_payload["evidence_boundary_metadata"]["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and live_payload["evidence_boundary_metadata"]["real_money_no_baq_as_bel_required"] is True
            and live_payload["evidence_boundary_metadata"]["requires_actual_settled_ts_for_roi_complete"] is True
            and live_payload["evidence_boundary_metadata"]["open_rows_are_not_performance_evidence"] is True
            and live_payload["evidence_boundary_metadata"]["roi_complete_counts_are_sample_coverage_not_profitability"] is True
            and live_payload["evidence_boundary_metadata"]["green_audit_is_not_profit_proof"] is True
            and live_payload["evidence_boundary_metadata"]["not_new_forward_evidence_by_itself"] is True
            and live_payload["evidence_boundary_metadata"]["not_forward_performance_evidence_by_itself"] is True
            and live_payload["evidence_boundary_metadata"]["not_live_profitability_evidence"] is True
            and live_payload["evidence_boundary_metadata"]["not_promotion_readiness_evidence"] is True
            and live_payload["evidence_boundary_metadata"]["not_anchor_change_evidence"] is True
            and live_payload["evidence_boundary_metadata"]["not_companion_change_evidence"] is True
            and live_payload["evidence_boundary_metadata"]["not_phase8_promotion_evidence"] is True
            and live_payload["evidence_boundary_metadata"]["not_scope_change_evidence"] is True
            and live_payload["evidence_boundary_metadata"]["not_baq_as_bel_evidence"] is True
            and live_payload["evidence_boundary_metadata"]["not_real_money_evidence"] is True
            and live_payload["evidence_boundary_metadata"]["current_anchor_rule_id"] == "OP_DURABLE_K7"
            and live_payload["evidence_boundary_metadata"]["current_primary_companion_rule_id"] == "CD_CORE_K8"
            and live_payload["evidence_boundary_metadata"]["current_same_family_shadow_rule_id"] == "OP_REFINED_K7"
            and "settlement-quality and payout-concentration checks"
            in live_payload["evidence_boundary_metadata"]["posture_change_requires"],
            "settlement_audit_publishes_machine_readable_evidence_boundary_metadata",
            "the saved live settlement audit now publishes top-level valid_evidence_scope and evidence_boundary_text plus a machine-readable evidence_boundary_metadata block that keeps ledger alignment, open-row queues, ROI-complete coverage, and scorecard-sourced 30 / 20 / 100 gate progress separate from settled profit proof, promotion readiness, live profitability, scope movement, BAQ/BEL substitution, or real-money evidence",
        ),
        require(
            VALID_EVIDENCE_SCOPE == audit.SETTLEMENT_AUDIT_VALID_EVIDENCE_SCOPE
            and EVIDENCE_BOUNDARY["artifact_role"] == "paper-trade settlement-audit validator"
            and EVIDENCE_BOUNDARY["valid_evidence_scope"] == audit.SETTLEMENT_AUDIT_VALID_EVIDENCE_SCOPE
            and EVIDENCE_BOUNDARY["not_new_forward_evidence_by_itself"] is True
            and EVIDENCE_BOUNDARY["not_settled_roi_evidence"] is True
            and EVIDENCE_BOUNDARY["not_live_profitability_evidence"] is True
            and EVIDENCE_BOUNDARY["not_real_money_evidence"] is True,
            "direct_validation_report_exposes_settlement_audit_valid_scope",
            f"the settlement-audit validation JSON, evidence-boundary metadata, summary read, and markdown evidence-boundary section now expose exact valid_evidence_scope={VALID_EVIDENCE_SCOPE} so ledger-quality fixture passes, live audit parity, open-row queues, and scorecard-gate visibility cannot be copied as new forward evidence, settled ROI, promotion readiness, live profitability, or real-money support",
        ),
        require(
            has_timezone_aware_generated_at(live_payload)
            and all(has_timezone_aware_generated_at(payload) for payload in fixture_payloads),
            "audit_generated_at_is_timezone_aware_metadata",
            "every fixture and live settlement-audit payload now has to publish parseable timezone-aware ISO generated_at metadata so provenance timestamps stay explicit without becoming performance evidence",
        ),
        require(
            shadow_gate["scope"] == "per_rule_shadow_watch"
            and live_lane_map["primary"]["active_first_read_gate"] == "anchor_displacement"
            and live_lane_map["primary"]["first_read_progress"].startswith(
                f"{live_lane_map['primary']['roi_complete_settled_rows']}/30 "
            )
            and live_lane_map["shadow"]["active_first_read_gate"] == "phase8_promotion_review"
            and live_lane_map["shadow"]["active_first_read_min_settled"] == 20
            and live_lane_map["shadow"]["first_read_progress"] == "0/20 (0.0%)"
            and shadow_gate["active_first_read_gate"] == "phase8_promotion_review"
            and shadow_gate["active_first_read_scope"] == "per_rule_shadow_watch"
            and shadow_gate["active_first_read_progress"] == "0/20 (0.0%)"
            and shadow_gate["min_roi_complete_settled_per_rule"] == 20
            and "phase8_promotion_review gate is per-rule" in shadow_gate["gate_read"]
            and "20-row count is a review floor, not a promotion entitlement" in shadow_gate["gate_read"]
            and "scorecard tiers remain binding" in shadow_gate["gate_read"]
            and "negative-holdout/SKIP rules still need cleaner split-aware evidence" in shadow_gate["gate_read"]
            and "lane totals alone do not promote OP_REFINED_K7" in shadow_gate["gate_read"]
            and shadow_gate["scorecard_rule_metadata"]["source_loaded"] is True
            and shadow_gate["scorecard_skip_rule_ids"] == ["AQU_K9", "CD_REFINED_K9"]
            and {row["rule_id"] for row in shadow_gate["rule_progress"]} == {
                "OP_REFINED_K7",
                "AQU_K9",
                "SA_K9",
                "KEE_K9",
                "CD_REFINED_K9",
                "DMR_FALL_K7",
            }
            and {row["rule_id"]: row["scorecard_tier"] for row in shadow_gate["rule_progress"]}["OP_REFINED_K7"] == "WATCH"
            and {row["rule_id"]: row["scorecard_tier"] for row in shadow_gate["rule_progress"]}["CD_REFINED_K9"] == "SKIP"
            and not any(row["promotion_ready"] for row in shadow_gate["rule_progress"])
            and any(row["promotion_progress"] != "0/20 (0.0%)" for row in shadow_gate["rule_progress"])
            and shadow_gate["active_first_read_progress"] == "0/20 (0.0%)",
            "shadow_watch_promotion_gate_is_per_rule_not_lane_total",
            "the saved live settlement audit now pins the shadow/watch phase8_promotion_review gate as 20 ROI-complete settled rows per rule, renders the shadow first-read column from the weakest per-rule coverage instead of primary-style lane totals, carries scorecard tier context into each rule row, and says the 20-row count is a review floor rather than a promotion entitlement, especially for negative-holdout/SKIP rules",
        ),
        require(
            (
                live_lane_map["primary"]["open_settlement_rows"] == 0
                and live_lane_map["primary"]["open_settlement_row_details"] == []
                and live_lane_map["primary"]["open_settlement_summary"] == "none"
                and "No open settlement rows are visible" in live_md_text
            )
            or (
                live_lane_map["primary"]["open_settlement_rows"] > 0
                and len(live_lane_map["primary"]["open_settlement_row_details"]) == live_lane_map["primary"]["open_settlement_rows"]
                and live_lane_map["primary"]["open_settlement_summary"] != "none"
                and live_lane_map["primary"]["open_settlement_summary"] in live_md_text
                and all(
                    row.get("signal_key")
                    and row.get("rule_id")
                    and row.get("track")
                    and row.get("race_id")
                    and row.get("key_program")
                    for row in live_lane_map["primary"]["open_settlement_row_details"]
                )
            ),
            "open_settlement_queue_carries_operator_identity_without_performance_claims",
            "the saved live settlement audit now publishes compact open-row identity details (signal_key, rule, track/race, key program, expected cost) when rows are waiting for result/payout evidence, while the markdown reminds operators that open rows are not performance evidence",
        ),
        require(
            live_gate_minimums["source_loaded"] is True
            and live_gate_minimums["fallback_used"] is False
            and live_gate_minimums["source_path"] == "forward_evidence_scorecard.json"
            and live_gate_minimums["anchor_displacement_min_roi_complete_settled_observations"] == 30
            and live_gate_minimums["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and live_gate_minimums["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and live_gate_minimums["real_money_discussion_also_requires"] == [
                "positive paper ROI",
                "concentration checks",
                "payout-distribution sanity checks",
                "no BAQ-as-BEL substitution",
            ]
            and live_gate_minimums["real_money_no_baq_as_bel_required"] is True
            and live_payload["min_settled"] == 30
            and live_payload["portfolio_review_settled"] == 100
            and live_payload["shadow_rule_min_settled"] == 20
            and not live_gate_minimums["cli_overrides"]
            and "source-matched to forward_evidence_scorecard.json decision_gate_minimums" in live_payload["summary"]["current_read"]
            and override_fixture_gate_minimums["cli_overrides"]["min_settled"] == {"scorecard_value": 30, "active_value": 3}
            and override_fixture_gate_minimums["cli_overrides"]["portfolio_review_settled"] == {"scorecard_value": 100, "active_value": 5}
            and lowered_gate_minimums["source_loaded"] is True
            and lowered_gate_minimums["fallback_used"] is True
            and "fell below conservative historical floors" in lowered_gate_minimums["fallback_reason"]
            and lowered_gate_minimums["anchor_displacement_min_roi_complete_settled_observations"] == 30
            and lowered_gate_minimums["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and lowered_gate_minimums["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and lowered_gate_minimums["real_money_discussion_also_requires"] == [
                "positive paper ROI",
                "concentration checks",
                "payout-distribution sanity checks",
                "no BAQ-as-BEL substitution",
            ]
            and lowered_gate_minimums["real_money_no_baq_as_bel_required"] is True
            and lowered_gate_minimums["rejected_lowered_values"]["anchor_displacement_min_roi_complete_settled_observations"] == {"loaded_value": 5, "conservative_floor": 30}
            and lowered_gate_minimums["rejected_lowered_values"]["phase8_promotion_review_min_roi_complete_settled_observations"] == {"loaded_value": 3, "conservative_floor": 20}
            and lowered_gate_minimums["rejected_lowered_values"]["real_money_discussion_min_total_settled_observations_with_usable_roi"] == {"loaded_value": 25, "conservative_floor": 100},
            "settlement_audit_gates_are_sourced_from_scorecard_minimums",
            "the saved live settlement audit loads forward_evidence_scorecard.json decision_gate_minimums as its default 30 anchor-displacement, 20 Phase 8 promotion-review, and 100 real-money-discussion thresholds plus the no-BAQ-as-BEL real-money prerequisite, fixture CLI overrides stay explicit and non-posture-changing, and a malformed scorecard that tries to lower those gates fails closed to the conservative historical floors",
        ),
        require(
            boolean_gate_minimums["source_loaded"] is True
            and boolean_gate_minimums["fallback_used"] is True
            and "malformed" in boolean_gate_minimums["fallback_reason"]
            and "positive non-boolean integer" in boolean_gate_minimums["malformed_gate_error"]
            and boolean_gate_minimums["anchor_displacement_min_roi_complete_settled_observations"] == 30
            and boolean_gate_minimums["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and boolean_gate_minimums["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and boolean_gate_minimums["real_money_discussion_also_requires"] == ["no BAQ-as-BEL substitution"]
            and boolean_gate_minimums["real_money_no_baq_as_bel_required"] is True,
            "settlement_audit_boolean_gate_floor_is_malformed_not_source_matched",
            "a scorecard sidecar that sets a boolean gate floor is treated as malformed source data and falls back to conservative 30 / 20 / 100 settlement-audit gates with the no-BAQ-as-BEL prerequisite, rather than being coerced through int(True) or described as source-matched",
        ),
        require(
            nonpositive_phase8_gate_minimums["source_loaded"] is True
            and nonpositive_phase8_gate_minimums["fallback_used"] is True
            and "malformed" in nonpositive_phase8_gate_minimums["fallback_reason"]
            and "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer"
            in nonpositive_phase8_gate_minimums["malformed_gate_error"]
            and nonpositive_phase8_gate_minimums["anchor_displacement_min_roi_complete_settled_observations"] == 30
            and nonpositive_phase8_gate_minimums["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and nonpositive_phase8_gate_minimums["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and nonpositive_phase8_gate_minimums["real_money_discussion_also_requires"] == ["no BAQ-as-BEL substitution"]
            and nonpositive_phase8_gate_minimums["real_money_no_baq_as_bel_required"] is True
            and nonpositive_real_money_gate_minimums["source_loaded"] is True
            and nonpositive_real_money_gate_minimums["fallback_used"] is True
            and "malformed" in nonpositive_real_money_gate_minimums["fallback_reason"]
            and "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer"
            in nonpositive_real_money_gate_minimums["malformed_gate_error"]
            and nonpositive_real_money_gate_minimums["anchor_displacement_min_roi_complete_settled_observations"] == 30
            and nonpositive_real_money_gate_minimums["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and nonpositive_real_money_gate_minimums["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and nonpositive_real_money_gate_minimums["real_money_discussion_also_requires"] == ["no BAQ-as-BEL substitution"]
            and nonpositive_real_money_gate_minimums["real_money_no_baq_as_bel_required"] is True,
            "settlement_audit_nonpositive_gate_floors_are_malformed_not_source_matched",
            "scorecard sidecars with non-positive Phase 8 promotion-review or real-money discussion floors are treated as malformed source data and fall back to conservative 30 / 20 / 100 settlement-audit gates with the no-BAQ-as-BEL prerequisite",
        ),
        require(
            missing_no_baq_gate_minimums["source_loaded"] is True
            and missing_no_baq_gate_minimums["fallback_used"] is True
            and "malformed" in missing_no_baq_gate_minimums["fallback_reason"]
            and "decision_gate_minimums.real_money_discussion.also_requires must include no BAQ-as-BEL substitution"
            in missing_no_baq_gate_minimums["malformed_gate_error"]
            and missing_no_baq_gate_minimums["anchor_displacement_min_roi_complete_settled_observations"] == 30
            and missing_no_baq_gate_minimums["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and missing_no_baq_gate_minimums["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and missing_no_baq_gate_minimums["real_money_discussion_also_requires"] == ["no BAQ-as-BEL substitution"]
            and missing_no_baq_gate_minimums["real_money_no_baq_as_bel_required"] is True,
            "settlement_audit_missing_no_baq_requirement_is_malformed_not_source_matched",
            "a scorecard sidecar missing the no-BAQ-as-BEL real-money prerequisite is treated as malformed source data and falls back to conservative 30 / 20 / 100 settlement-audit gates with the no-BAQ-as-BEL prerequisite restored",
        ),
        require(
            scratch["fixture_root_is_project_local"] is True
            and scratch["case_roots_cleared_by_setup_case"] is True
            and scratch["fixture_root_relative"] == "out/status_validation/settlement_audit_fixture",
            "fixture_scratch_metadata_published",
            "the settlement-audit validator now publishes project-local fixture scratch metadata so parent rollups can verify isolated audit-fixture hygiene without parsing markdown prose",
        ),
        require(
            duplicate_lane_failure["mode"] == "expected_failure"
            and duplicate_lane_failure["assessment"] == "expected_failure_no_outputs"
            and not (FIXTURE_ROOT / "case_duplicate_lane_names_fail_before_outputs" / "nested" / "outputs").exists(),
            "duplicate_custom_lane_names_fail_before_output_artifacts",
            "duplicate custom --lane names now fail before audit markdown/json outputs or their parent output directory are created, keeping lane payloads and source-fingerprint keys unambiguous",
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
        "cases": results,
        "scratch": scratch,
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "summary": {
            "current_read": f"settlement-audit validator now proves the direct audit separates structural signal/settlement template gaps and matched-key metadata mismatches from settled-row ROI-coverage gaps, keeps blank signal-key rows and blank settlement-key rows separately labeled in repair output, keeps missing/placeholder/malformed settled_ts values out of ROI-complete settled counts even when return/cost fields are usable, keeps non-positive actual or expected-cost rows out of ROI-complete settled counts, publishes explicit lane next_action guidance for collect/repair/settle/review states plus compact open-row identity details for settlement work, treats header-only ledgers as aligned but pre-evidence, counts only ROI-complete settled rows toward lane-specific first-read and portfolio-review milestones, renders the default primary/shadow live audit with source fingerprint parity for scorecard/rules/signals/settlements, publishes top-level valid_evidence_scope and evidence_boundary_text plus machine-readable evidence_boundary_metadata for ledger-completeness / ROI-coverage audit scope, validates timezone-aware ISO generated_at metadata for live/fixture audit outputs, rejects duplicate custom --lane names before writing audit markdown/json artifacts so lane payloads and source-fingerprint keys stay unambiguous, now pins the primary anchor_displacement first-read gate separately from the shadow/watch phase8_promotion_review per-rule gate so the shadow audit table shows 0/20 instead of primary-style 0/30, carries scorecard tier context into shadow rule progress, and says the 20-row count is a review floor rather than a promotion entitlement so OP_REFINED_K7 plus other Phase 8 pockets cannot be promoted from aggregate shadow counts or negative-holdout/SKIP status, loads the default 30 / 20 / 100 settlement sample gates plus the no-BAQ-as-BEL real-money prerequisite from forward_evidence_scorecard.json decision_gate_minimums, keeps fixture CLI gate overrides explicit, rejects scorecard gate values that fall below the conservative historical floors, treats boolean gate floors as malformed instead of int-coercible source-matched values, treats non-positive Phase 8 and real-money scorecard gate floors as malformed instead of source-matched values, treats a missing no-BAQ-as-BEL real-money prerequisite as malformed instead of source-matched, publishes project-local fixture scratch metadata, exposes direct validator report valid_evidence_scope={VALID_EVIDENCE_SCOPE}, and says plainly this is a ledger-completeness / ROI-coverage audit rather than new forward evidence by itself",
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "fixture_root": str(FIXTURE_ROOT.relative_to(BASE)),
            "report_path": str(REPORT_MD.relative_to(BASE)),
        },
    }

    lines = [
        "# Paper-Trade Settlement Audit Validation",
        "",
        "This report validates `paper_trade_settlement_audit.py` directly against isolated fixture ledgers plus the default live primary/shadow audit.",
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
        "| Case | Scenario | Assessment | Next action | Audit JSON |",
        "|---|---|---|---|---|",
    ]
    for row in results:
        lines.append(
            f"| `{row['name']}` | {row['scenario']} | `{row['assessment']}` | `{row.get('next_action', 'n/a')}` | `{row['audit_json']}` |"
        )

    lines.extend([
        "",
        "## Current Read",
        "",
        f"- Suite read: {payload['summary']['current_read']}",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
        f"- valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
        f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
        "- Boundary: settlement-audit validator cleanliness is ledger-quality and ROI-coverage metadata only, not a current-day scanner result, not new forward evidence by itself, not settled ROI evidence, not live profitability, not promotion readiness, and not real-money evidence.",
        "- Non-goals: do not treat fixture passes, saved-live parity, open-row queues, scorecard-gate visibility, or green settlement-audit reports as rule-change permission, promotion support, BAQ/BEL substitution, live-profitability proof, or real-money support.",
        "",
        "## Validation result",
        "",
        "- Header-only ledgers are structurally aligned but still pre-evidence.",
        "- Signal/settlement structural gaps, including matched-key metadata mismatches, are surfaced before any forward-performance read.",
        "- Blank signal-key rows and blank settlement-key rows stay separately labeled in the repair queue.",
        "- Each lane now carries a machine-readable `next_action` so collect/repair/settle/review states are not inferred from assessment prose.",
        "- Open settlement rows now carry compact identity details for operator settlement work, without turning open rows into performance evidence.",
        "- Settled rows missing outcome or usable return/cost coverage carry explicit repair reasons.",
        "- Settled rows with missing, placeholder, or malformed `settled_ts` values stay repair items even when return/cost coverage is usable.",
        "- ROI-complete settled rows feed sample milestones but do not create standalone profit proof.",
        "- The default live audit preserves the primary/shadow lane hierarchy, `BAQ`/`BEL` boundary, next-action guidance, and no-new-evidence frame.",
        "- The default live audit publishes source fingerprints for the scorecard, rule files, signal ledgers, and settlement ledgers, and the validator compares those byte counts and SHA-256 hashes to disk.",
        "- The default live audit publishes top-level `valid_evidence_scope` / `evidence_boundary_text` plus machine-readable `evidence_boundary_metadata` so ledger alignment, open-row queues, ROI-complete coverage, and scorecard gate progress cannot be over-read as settled profit proof, promotion readiness, live profitability, scope movement, `BAQ`/`BEL` substitution, or real-money evidence.",
        "- Fixture and live audit payloads publish timezone-aware ISO `generated_at` metadata for provenance only.",
        "- Duplicate custom `--lane` names now fail before audit markdown/JSON outputs are created, so lane payloads and source-fingerprint keys stay unambiguous.",
        "- The shadow/watch `phase8_promotion_review` gate is pinned per rule (20 ROI-complete settled rows each), so the shadow first-read audit column renders 0/20 and aggregate shadow-lane totals alone cannot promote `OP_REFINED_K7` or any Phase 8 pocket.",
        "- Shadow rule progress now carries scorecard tiers, making the 20-row count a review floor rather than a promotion entitlement and keeping negative-holdout/SKIP rules such as `CD_REFINED_K9` visibly below promotion posture until split-aware evidence improves.",
        "- The live settlement audit now loads its default 30 / 20 / 100 sample gates plus the no-BAQ-as-BEL real-money prerequisite from `forward_evidence_scorecard.json` `decision_gate_minimums`, while fixture CLI overrides remain explicit and do not become posture-changing gates.",
        "- Lowered scorecard gate values now fail closed to the conservative historical floors instead of reducing the 30 / 20 / 100 observation thresholds by accident.",
        "- Boolean scorecard gate values now fail as malformed source data instead of being coerced through `int(True)` or described as source-matched.",
        "- Non-positive Phase 8 promotion-review and real-money discussion scorecard gate values now fail as malformed source data instead of being described as source-matched.",
        "- Scorecard gate values missing the no-BAQ-as-BEL real-money prerequisite now fail as malformed source data instead of being described as source-matched.",
        "",
        "## Sources",
        "",
    ])
    for row in results:
        lines.append(f"- `{row['audit_md']}`")
        lines.append(f"- `{row['audit_json']}`")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    for row in results:
        print(f"PASS {row['name']}: {row['assessment']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
