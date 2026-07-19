#!/usr/bin/env python3
"""
Run the main research-side, operator-side, report-surface, and navigation-surface validators together.

Purpose:
- give Cole one command for the whole report-safe project surface
- chain the frozen evidence suite, the paper-trade operator suite, the narrative report-surface suite,
  and the repo-navigation, main status-doc, plus operator-runbook surfaces
- summarize whether research conclusions, operator messaging, human-facing report wording,
  and the repo's read / rerun guidance still align
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import validate_cole_status_and_plan as cole_status_and_plan
import validate_current_hierarchy_language as current_hierarchy_language
import validate_daily_artifact_guide as daily_artifact_guide
import validate_frozen_evidence_chain as frozen_evidence
import validate_paper_trade_operator_suite as operator_suite
import validate_paper_trade_usage as paper_trade_usage
import validate_readme_current_status as readme_current_status
import validate_report_surfaces as report_surfaces
import validate_validation_quickstart as validation_quickstart

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "out" / "status_validation" / "project_surfaces"
OUT_MD = OUT_DIR / "project_surfaces_validation.md"
OUT_JSON = OUT_DIR / "project_surfaces_validation.json"
REBUILD_COMMAND = "python3 validate_project_surfaces.py"
REUSE_EXISTING_FLAG = "--reuse-existing-child-json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
ACTIVE_TEXT_SUFFIXES = {".py", ".md", ".txt", ".json"}
STALE_GATE_SHORTHAND_PHRASES = (
    "30 /" + " 100",
    "30/100" + " active gates",
    "same 30" + "/100",
    "same 30 /" + " 100",
    "primary/shadow" + " parity",
    "20 /" + " 30 /" + " 100",
    "20/30" + "/100 thresholds",
    "those 20/30" + "/100",
)
STALE_GATE_SCAN_EXCLUDED_NAMES = {"OVERNIGHT_PROGRESS.md"}
STALE_GATE_SCAN_EXCLUDED_PARTS = {
    ".git",
    ".learnings",
    "__pycache__",
}

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "repo-wide validator rollup",
    "source_scope": [
        "frozen-evidence validator outputs",
        "operator-readiness validator outputs",
        "report-surface validator outputs",
        "README landing-page validator output",
        "navigation/status/runbook validator outputs",
        "current hierarchy wording validator output",
    ],
    "valid_use": "cross-layer alignment and reproducibility audit for report-safe project surfaces, including current hierarchy wording / structured-key compatibility",
    "not_new_forward_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "hashes_are_reproducibility_metadata_only": True,
    "stronger_forward_confidence_requires": [
        "qualifying live paper signals",
        "ROI-complete settled paper rows",
        "settlement-quality checks",
        "other real forward observations",
    ],
    "non_goals": [
        "do not use a green parent sweep as settled ROI",
        "do not use child JSON hashes as performance evidence",
        "do not promote OP_REFINED_K7 or Phase 8 from validation cleanliness",
        "do not treat current hierarchy wording cleanliness as anchor-change or companion-change evidence",
        "do not reopen odds-only XGBoost from validation cleanliness",
        "do not substitute BAQ for BEL",
        "do not discuss real-money scaling from validator passes",
    ],
}

SUITE: list[dict[str, Any]] = [
    {
        "name": "frozen_evidence_chain",
        "label": "Frozen evidence chain",
        "runner": frozen_evidence.main,
        "json_path": BASE / "out" / "status_validation" / "frozen_evidence_chain" / "frozen_evidence_chain_validation.json",
        "metric_key": "total_checks",
        "metric_label": "checks",
    },
    {
        "name": "paper_trade_operator_suite",
        "label": "Paper-trade operator suite",
        "runner": operator_suite.main,
        "json_path": BASE / "out" / "status_validation" / "paper_trade_operator_suite" / "paper_trade_operator_suite_validation.json",
        "metric_key": "total_fixture_scenarios",
        "metric_label": "fixture scenarios",
    },
    {
        "name": "report_surfaces",
        "label": "Narrative report surfaces",
        "runner": report_surfaces.main,
        "json_path": BASE / "out" / "status_validation" / "report_surfaces" / "report_surfaces_validation.json",
        "metric_key": "total_checks",
        "metric_label": "checks",
    },
    {
        "name": "readme_current_status",
        "label": "README landing page",
        "runner": readme_current_status.main,
        "json_path": BASE / "out" / "status_validation" / "readme_current_status" / "readme_current_status_validation.json",
        "metric_key": "total_checks",
        "metric_label": "checks",
    },
    {
        "name": "validation_quickstart",
        "label": "Validation quickstart",
        "runner": validation_quickstart.main,
        "json_path": BASE / "out" / "status_validation" / "validation_quickstart" / "validation_quickstart_validation.json",
        "metric_key": "total_checks",
        "metric_label": "checks",
    },
    {
        "name": "daily_artifact_guide",
        "label": "Daily artifact guide",
        "runner": daily_artifact_guide.main,
        "json_path": BASE / "out" / "status_validation" / "daily_artifact_guide" / "daily_artifact_guide_validation.json",
        "metric_key": "total_checks",
        "metric_label": "checks",
    },
    {
        "name": "current_hierarchy_language",
        "label": "Current hierarchy language",
        "runner": current_hierarchy_language.main,
        "json_path": BASE / "out" / "status_validation" / "current_hierarchy_language" / "current_hierarchy_language_validation.json",
        "metric_key": "total_checks",
        "metric_label": "checks",
    },
    {
        "name": "paper_trade_usage",
        "label": "Paper-trade usage",
        "runner": paper_trade_usage.main,
        "json_path": BASE / "out" / "status_validation" / "paper_trade_usage" / "paper_trade_usage_validation.json",
        "metric_key": "total_checks",
        "metric_label": "checks",
    },
    {
        "name": "cole_status_and_plan",
        "label": "Cole status and plan",
        "runner": cole_status_and_plan.main,
        "json_path": BASE / "out" / "status_validation" / "cole_status_and_plan" / "cole_status_and_plan_validation.json",
        "metric_key": "total_checks",
        "metric_label": "checks",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        REUSE_EXISTING_FLAG,
        dest="reuse_existing_child_json",
        action="store_true",
        help="reuse existing child validator JSON artifacts instead of rerunning every child suite",
    )
    return parser.parse_args()


def run_validator(fn: Callable[[], int | None], label: str) -> None:
    result = fn()
    if result not in (None, 0):
        raise AssertionError(f"{label} returned non-zero status: {result}")


def fingerprint_file(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(BASE)),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def load_child_payload(item: dict[str, Any], reuse_existing_child_json: bool) -> dict[str, Any]:
    if reuse_existing_child_json:
        if not item["json_path"].exists():
            raise AssertionError(
                f"{item['label']} reuse requested but child JSON is missing: {item['json_path']}"
            )
    else:
        run_validator(item["runner"], item["label"])
        if not item["json_path"].exists():
            raise AssertionError(f"{item['label']} did not write expected child JSON: {item['json_path']}")
    return json.loads(item["json_path"].read_text(encoding="utf-8"))


def require(condition: bool, label: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    return {"check": label, "status": "pass", "detail": detail}


def require_child_status(payload: dict[str, Any], label: str) -> str:
    artifact = payload.get("artifact")
    for candidate in (
        payload.get("suite_status"),
        artifact.get("status") if isinstance(artifact, dict) else None,
        payload.get("artifact_status"),
        payload.get("result"),
        payload.get("status"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip().upper()
    raise AssertionError(f"{label} child JSON is missing an explicit status field")


def require_explicit_int(payload: dict[str, Any], key: str, label: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise AssertionError(f"{label} child JSON is missing explicit integer {key}")
    return value


def require_child_checks(payload: dict[str, Any], label: str) -> list[dict[str, Any]]:
    checks = payload.get("checks")
    if not isinstance(checks, list):
        raise AssertionError(f"{label} child JSON is missing checks list")
    return checks


def require_report_text(path: Path, label: str) -> str:
    if not path.exists():
        raise AssertionError(f"{label} report markdown is missing: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise AssertionError(f"{label} report markdown is blank: {path}")
    return text


def find_stale_gate_shorthand_matches() -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for path in BASE.rglob("*"):
        if not path.is_file() or path.suffix not in ACTIVE_TEXT_SUFFIXES:
            continue
        rel = path.relative_to(BASE)
        if path.name in STALE_GATE_SCAN_EXCLUDED_NAMES:
            continue
        if any(part in STALE_GATE_SCAN_EXCLUDED_PARTS for part in rel.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            if any(phrase in line for phrase in STALE_GATE_SHORTHAND_PHRASES):
                matches.append({"path": str(rel), "line": line_no})
    return matches


def build_current_evidence_bridge_read(current_evidence: dict[str, Any]) -> dict[str, Any]:
    source_consistency = current_evidence.get("source_consistency")
    if not isinstance(source_consistency, dict):
        source_consistency = {}
    source_freshness = current_evidence.get("source_freshness")
    if not isinstance(source_freshness, dict):
        source_freshness = {}
    current_paper_status = current_evidence.get("current_paper_status")
    if not isinstance(current_paper_status, dict):
        current_paper_status = {}
    current_primary = current_paper_status.get("primary")
    if not isinstance(current_primary, dict):
        current_primary = {}
    current_gate_minimums = current_evidence.get("decision_gate_minimums")
    if not isinstance(current_gate_minimums, dict):
        current_gate_minimums = {}
    top_card_values = current_gate_minimums.get("top_card_values")
    if not isinstance(top_card_values, dict):
        top_card_values = {}
    scorecard_values = current_gate_minimums.get("scorecard_values")
    if not isinstance(scorecard_values, dict):
        scorecard_values = {}
    effective_values = current_gate_minimums.get("effective_values")
    if not isinstance(effective_values, dict):
        effective_values = {}
    threshold_sources = current_gate_minimums.get("threshold_sources")
    if not isinstance(threshold_sources, dict):
        threshold_sources = {}

    def source_values_match(key: str) -> bool | None:
        values = source_consistency.get(key)
        if not isinstance(values, dict) or not values:
            return None
        return len(set(values.values())) == 1

    return {
        "source_path": CURRENT_EVIDENCE_JSON.name,
        "generated_at": current_evidence.get("generated_at"),
        "source_consistency_overall_match": source_consistency.get("overall_match"),
        "primary_roi_complete_rows_match": source_values_match("primary_roi_complete_settled_rows"),
        "primary_open_rows_match": source_values_match("primary_open_settlement_rows"),
        "primary_incomplete_rows_match": source_values_match("primary_incomplete_settlement_rows"),
        "primary_roi_gap_rows_match": source_values_match("primary_roi_gap_settlement_rows"),
        "source_freshness_state_valid": source_freshness.get("right_now_freshness_state_valid"),
        "right_now_freshness_state": source_freshness.get("right_now_freshness_state"),
        "requires_refresh_before_right_now_use": source_freshness.get(
            "requires_refresh_before_right_now_use"
        ),
        "current_primary_first_read": current_primary.get("first_read"),
        "current_primary_portfolio_review": current_primary.get("portfolio_review"),
        "decision_gate_source": current_gate_minimums.get("source_path"),
        "decision_gate_source_loaded": current_gate_minimums.get("source_loaded"),
        "decision_gate_source_values_match_scorecard": current_gate_minimums.get(
            "source_values_match_scorecard"
        ),
        "decision_gate_effective_values_source": current_gate_minimums.get("effective_values_source"),
        "decision_gate_missing_top_card_fields": current_gate_minimums.get("missing_top_card_fields"),
        "decision_gate_mismatched_fields": current_gate_minimums.get("mismatched_fields"),
        "top_card_anchor_displacement_min": top_card_values.get(
            "anchor_displacement_min_roi_complete_settled_observations"
        ),
        "top_card_phase8_promotion_review_min": top_card_values.get(
            "phase8_promotion_review_min_roi_complete_settled_observations"
        ),
        "top_card_real_money_discussion_min": top_card_values.get(
            "real_money_discussion_min_total_settled_observations_with_usable_roi"
        ),
        "scorecard_anchor_displacement_min_from_bridge": scorecard_values.get(
            "anchor_displacement_min_roi_complete_settled_observations"
        ),
        "scorecard_phase8_promotion_review_min_from_bridge": scorecard_values.get(
            "phase8_promotion_review_min_roi_complete_settled_observations"
        ),
        "scorecard_real_money_discussion_min_from_bridge": scorecard_values.get(
            "real_money_discussion_min_total_settled_observations_with_usable_roi"
        ),
        "effective_anchor_displacement_min": effective_values.get(
            "anchor_displacement_min_roi_complete_settled_observations"
        ),
        "effective_phase8_promotion_review_min": effective_values.get(
            "phase8_promotion_review_min_roi_complete_settled_observations"
        ),
        "effective_real_money_discussion_min": effective_values.get(
            "real_money_discussion_min_total_settled_observations_with_usable_roi"
        ),
        "decision_gate_threshold_sources": threshold_sources,
        "not_new_forward_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_live_profitability_evidence": True,
        "not_real_money_evidence": True,
    }


def row_has_saved_live_component_total(row: dict[str, Any], expected_fixture_scenarios: int, minimum_live_surfaces: int) -> bool:
    fixture_scenarios = row.get("child_total_fixture_scenarios")
    live_surfaces = row.get("child_live_surface_checks")
    total_checks = row.get("child_total_checks")
    check_count = row.get("child_check_count")
    return (
        isinstance(fixture_scenarios, int)
        and not isinstance(fixture_scenarios, bool)
        and fixture_scenarios == expected_fixture_scenarios
        and isinstance(live_surfaces, int)
        and not isinstance(live_surfaces, bool)
        and live_surfaces >= minimum_live_surfaces
        and total_checks == fixture_scenarios + live_surfaces
        and check_count == total_checks
    )


def row_has_saved_live_plus_top_level_artifact_component_total(
    row: dict[str, Any],
    expected_fixture_scenarios: int,
    minimum_live_surfaces: int,
    expected_top_level_default_artifact_checks: int,
) -> bool:
    fixture_scenarios = row.get("child_total_fixture_scenarios")
    live_surfaces = row.get("child_live_surface_checks")
    top_level_artifact_checks = row.get("child_top_level_default_artifact_checks")
    total_checks = row.get("child_total_checks")
    check_count = row.get("child_check_count")
    return (
        isinstance(fixture_scenarios, int)
        and not isinstance(fixture_scenarios, bool)
        and fixture_scenarios == expected_fixture_scenarios
        and isinstance(live_surfaces, int)
        and not isinstance(live_surfaces, bool)
        and live_surfaces >= minimum_live_surfaces
        and isinstance(top_level_artifact_checks, int)
        and not isinstance(top_level_artifact_checks, bool)
        and top_level_artifact_checks == expected_top_level_default_artifact_checks
        and total_checks == fixture_scenarios + live_surfaces + top_level_artifact_checks
        and check_count == total_checks
    )


def operator_rows_publish_child_check_components(operator_payload: dict[str, Any]) -> bool:
    rows = operator_payload.get("rows")
    if not isinstance(rows, list):
        return False
    row_map = {row.get("name"): row for row in rows if isinstance(row, dict)}
    if len(row_map) != len(rows):
        return False

    for row in rows:
        components = row.get("child_check_components")
        if not isinstance(components, dict):
            return False
        if components.get("total_fixture_scenarios") != row.get("child_total_fixture_scenarios"):
            return False
        if components.get("total_checks") != row.get("child_total_checks"):
            return False
        if components.get("check_count") != row.get("child_check_count"):
            return False

    saved_live_expected: dict[str, tuple[int, int]] = {
        "paper_trade_next_steps": (33, 12),
        "paper_trade_forward_check": (13, 10),
        "paper_trade_lane_monitor": (11, 10),
        "paper_trade_lane_summary": (19, 18),
        "paper_trade_now": (37, 1),
        "paper_trade_ops_history": (24, 1),
        "paper_trade_daily_summary": (25, 9),
    }
    for name, (expected_fixture_scenarios, minimum_live_surfaces) in saved_live_expected.items():
        row = row_map.get(name)
        if not isinstance(row, dict):
            return False
        components = row.get("child_check_components")
        if not isinstance(components, dict):
            return False
        live_surfaces = components.get("live_surface_checks")
        total_checks = components.get("total_checks")
        if (
            components.get("total_fixture_scenarios") != expected_fixture_scenarios
            or not isinstance(live_surfaces, int)
            or isinstance(live_surfaces, bool)
            or live_surfaces < minimum_live_surfaces
            or components.get("top_level_default_artifact_checks") is not None
            or total_checks != expected_fixture_scenarios + live_surfaces
            or components.get("check_count") != total_checks
        ):
            return False

    preflight = row_map.get("paper_trade_preflight_note")
    if not isinstance(preflight, dict):
        return False
    preflight_components = preflight.get("child_check_components")
    if not isinstance(preflight_components, dict):
        return False
    preflight_live = preflight_components.get("live_surface_checks")
    return (
        preflight_components.get("total_fixture_scenarios") == 6
        and isinstance(preflight_live, int)
        and not isinstance(preflight_live, bool)
        and preflight_live >= 6
        and preflight_components.get("top_level_default_artifact_checks") == 1
        and preflight_components.get("total_checks") == 6 + preflight_live + 1
        and preflight_components.get("check_count") == preflight_components.get("total_checks")
    )


def operator_rows_publish_complete_metadata_contract(operator_payload: dict[str, Any]) -> bool:
    rows = operator_payload.get("rows")
    if not isinstance(rows, list):
        return False

    expected_row_report_paths = {
        item["name"]: {
            "label": item["label"],
            "report_md": str(item["report_md"].relative_to(BASE)),
            "report_json": str(item["report_json"].relative_to(BASE)),
        }
        for item in operator_suite.SUITE
    }
    row_map = {row.get("name"): row for row in rows if isinstance(row, dict)}
    if {row.get("name") for row in rows if isinstance(row, dict)} != set(expected_row_report_paths):
        return False
    if len(row_map) != len(rows) or len(rows) != len(operator_suite.SUITE):
        return False

    for row in rows:
        name = row.get("name")
        if not isinstance(name, str):
            return False
        expected = expected_row_report_paths.get(name)
        if expected is None:
            return False
        child_checks = row.get("child_checks")
        child_guardrails = row.get("child_guardrail_checks")
        components = row.get("child_check_components")
        if (
            row.get("label") != expected["label"]
            or row.get("result") != "PASS"
            or row.get("report_md") != expected["report_md"]
            or row.get("report_json") != expected["report_json"]
            or not isinstance(row.get("current_read"), str)
            or not row.get("current_read", "").strip()
            or not isinstance(components, dict)
            or components.get("total_checks") != row.get("child_total_checks")
            or components.get("check_count") != row.get("child_check_count")
            or not isinstance(child_guardrails, list)
            or len(child_guardrails) != row.get("child_guardrail_check_count")
        ):
            return False
        if child_checks is not None and (
            not isinstance(child_checks, list) or len(child_checks) != row.get("child_check_count")
        ):
            return False
        for check in list(child_checks or []) + child_guardrails:
            if (
                not isinstance(check, dict)
                or not isinstance(check.get("check"), str)
                or not check.get("check", "").strip()
                or check.get("status") != "pass"
                or not isinstance(check.get("detail"), str)
                or not check.get("detail", "").strip()
            ):
                return False

    return True


def project_rows_publish_complete_metadata_contract(rows: list[dict[str, Any]]) -> bool:
    expected_rows = {
        item["name"]: {
            "label": item["label"],
            "metric_label": item["metric_label"],
            "json_path": str(item["json_path"].relative_to(BASE)),
        }
        for item in SUITE
    }
    if len(rows) != len(SUITE):
        return False
    row_map = {row.get("name"): row for row in rows if isinstance(row, dict)}
    if set(row_map) != set(expected_rows) or len(row_map) != len(rows):
        return False

    for name, row in row_map.items():
        expected = expected_rows[name]
        child_checks = row.get("child_checks")
        fingerprint = row.get("child_json_fingerprint")
        if (
            row.get("label") != expected["label"]
            or row.get("metric_label") != expected["metric_label"]
            or row.get("result") != "PASS"
            or row.get("json_path") != expected["json_path"]
            or not isinstance(row.get("current_read"), str)
            or not row.get("current_read", "").strip()
            or not isinstance(row.get("metric_value"), int)
            or isinstance(row.get("metric_value"), bool)
            or row.get("metric_value") <= 0
            or not isinstance(row.get("child_total_checks"), int)
            or isinstance(row.get("child_total_checks"), bool)
            or row.get("child_total_checks") <= 0
            or not isinstance(row.get("child_check_count"), int)
            or isinstance(row.get("child_check_count"), bool)
            or row.get("child_check_count") <= 0
            or not isinstance(child_checks, list)
            or len(child_checks) != row.get("child_check_count")
            or not isinstance(row.get("child_json_bytes"), int)
            or isinstance(row.get("child_json_bytes"), bool)
            or row.get("child_json_bytes") <= 0
            or not isinstance(row.get("child_json_sha256"), str)
            or len(row.get("child_json_sha256", "")) != 64
            or not all(char in "0123456789abcdef" for char in row.get("child_json_sha256", ""))
            or not isinstance(fingerprint, dict)
            or fingerprint.get("path") != row.get("json_path")
            or fingerprint.get("bytes") != row.get("child_json_bytes")
            or fingerprint.get("sha256") != row.get("child_json_sha256")
        ):
            return False
        for check in child_checks:
            if (
                not isinstance(check, dict)
                or not isinstance(check.get("check"), str)
                or not check.get("check", "").strip()
                or check.get("status") != "pass"
                or not isinstance(check.get("detail"), str)
                or not check.get("detail", "").strip()
            ):
                return False

    return True


def build_child_artifact_fingerprints(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        row["name"]: {
            "path": row["json_path"],
            "bytes": row["child_json_bytes"],
            "sha256": row["child_json_sha256"],
        }
        for row in rows
    }


def child_artifact_fingerprint_map_mirrors_rows(
    child_artifact_fingerprints: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
) -> bool:
    expected = build_child_artifact_fingerprints(rows)
    if child_artifact_fingerprints != expected:
        return False
    for name, fingerprint in child_artifact_fingerprints.items():
        if (
            not isinstance(name, str)
            or not name.strip()
            or not isinstance(fingerprint, dict)
            or set(fingerprint) != {"path", "bytes", "sha256"}
            or not isinstance(fingerprint.get("path"), str)
            or not fingerprint["path"].strip()
            or not isinstance(fingerprint.get("bytes"), int)
            or isinstance(fingerprint.get("bytes"), bool)
            or fingerprint["bytes"] <= 0
            or not isinstance(fingerprint.get("sha256"), str)
            or len(fingerprint["sha256"]) != 64
            or not all(char in "0123456789abcdef" for char in fingerprint["sha256"])
        ):
            return False
    return True


def build_child_artifact_fingerprint_manifest(
    child_artifact_fingerprints: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    entries_in_suite_order = [
        {
            "name": row["name"],
            "path": child_artifact_fingerprints[row["name"]]["path"],
            "bytes": child_artifact_fingerprints[row["name"]]["bytes"],
            "sha256": child_artifact_fingerprints[row["name"]]["sha256"],
        }
        for row in rows
    ]
    return {
        "source": "project_surfaces.rows",
        "fingerprint_map": "child_artifact_fingerprints",
        "row_count": len(rows),
        "fingerprint_count": len(child_artifact_fingerprints),
        "names_in_suite_order": [row["name"] for row in rows],
        "entries_in_suite_order": entries_in_suite_order,
        "hashes_are_reproducibility_metadata_only": True,
    }


def child_artifact_fingerprint_manifest_mirrors_suite_order(
    manifest: dict[str, Any],
    child_artifact_fingerprints: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
) -> bool:
    expected_names = [item["name"] for item in SUITE]
    return (
        manifest.get("source") == "project_surfaces.rows"
        and manifest.get("fingerprint_map") == "child_artifact_fingerprints"
        and manifest.get("row_count") == len(rows) == len(SUITE)
        and manifest.get("fingerprint_count") == len(child_artifact_fingerprints) == len(SUITE)
        and manifest.get("names_in_suite_order") == [row.get("name") for row in rows] == expected_names
        and list(child_artifact_fingerprints) == expected_names
        and manifest.get("hashes_are_reproducibility_metadata_only") is True
    )


def child_artifact_fingerprint_manifest_entries_mirror_rows(
    manifest: dict[str, Any],
    child_artifact_fingerprints: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
) -> bool:
    entries = manifest.get("entries_in_suite_order")
    if not isinstance(entries, list) or len(entries) != len(rows):
        return False

    expected_entries = [
        {
            "name": row["name"],
            "path": row["json_path"],
            "bytes": row["child_json_bytes"],
            "sha256": row["child_json_sha256"],
        }
        for row in rows
    ]
    if entries != expected_entries:
        return False

    for entry in entries:
        if not isinstance(entry, dict):
            return False
        name = entry.get("name")
        fingerprint = child_artifact_fingerprints.get(name)
        if (
            not isinstance(name, str)
            or not name.strip()
            or set(entry) != {"name", "path", "bytes", "sha256"}
            or not isinstance(fingerprint, dict)
            or entry["path"] != fingerprint.get("path")
            or entry["bytes"] != fingerprint.get("bytes")
            or entry["sha256"] != fingerprint.get("sha256")
        ):
            return False

    return True


def build_child_artifact_fingerprint_manifest_markdown_rows(manifest: dict[str, Any]) -> list[str]:
    entries = manifest.get("entries_in_suite_order")
    if not isinstance(entries, list):
        return []
    rows = []
    for entry in entries:
        if not isinstance(entry, dict):
            return []
        rows.append(
            f"| `{entry.get('name')}` | `{entry.get('path')}` | {entry.get('bytes')} | `{entry.get('sha256')}` |"
        )
    return rows


def child_artifact_fingerprint_manifest_markdown_rows_mirror_entries(
    manifest: dict[str, Any],
    markdown_rows: list[str],
) -> bool:
    expected_rows = build_child_artifact_fingerprint_manifest_markdown_rows(manifest)
    return (
        bool(expected_rows)
        and markdown_rows == expected_rows
        and len(markdown_rows) == manifest.get("row_count") == manifest.get("fingerprint_count")
    )


def build_child_artifact_source_list(manifest: dict[str, Any]) -> list[str]:
    entries = manifest.get("entries_in_suite_order")
    if not isinstance(entries, list):
        return []
    source_list = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            return []
        source_list.append(entry["path"])
    return source_list


def child_artifact_source_list_mirrors_manifest_entries(
    source_list: list[str],
    manifest: dict[str, Any],
    rows: list[dict[str, Any]],
) -> bool:
    expected_paths = [row["json_path"] for row in rows]
    manifest_paths = build_child_artifact_source_list(manifest)
    return (
        bool(expected_paths)
        and source_list == expected_paths == manifest_paths
        and len(source_list) == manifest.get("row_count") == manifest.get("fingerprint_count")
        and all(isinstance(path, str) and path.strip() for path in source_list)
    )


def build_child_artifact_source_markdown_lines(source_list: list[str]) -> list[str]:
    lines = []
    for path in source_list:
        if not isinstance(path, str) or not path.strip():
            return []
        lines.append(f"- `{path}`")
    return lines


def child_artifact_source_markdown_lines_mirror_source_list(
    source_list: list[str],
    source_markdown_lines: list[str],
    manifest: dict[str, Any],
) -> bool:
    expected_lines = build_child_artifact_source_markdown_lines(source_list)
    return (
        bool(expected_lines)
        and source_markdown_lines == expected_lines
        and len(source_markdown_lines) == manifest.get("row_count") == manifest.get("fingerprint_count")
    )


def build_child_artifact_fingerprint_bullet_lines(manifest: dict[str, Any]) -> list[str]:
    entries = manifest.get("entries_in_suite_order")
    if not isinstance(entries, list):
        return []
    lines = []
    for entry in entries:
        if not isinstance(entry, dict):
            return []
        lines.append(f"- `{entry.get('path')}` — {entry.get('bytes')} bytes, sha256={entry.get('sha256')}")
    return lines


def child_artifact_fingerprint_bullet_lines_mirror_entries(
    manifest: dict[str, Any],
    bullet_lines: list[str],
) -> bool:
    expected_lines = build_child_artifact_fingerprint_bullet_lines(manifest)
    return (
        bool(expected_lines)
        and bullet_lines == expected_lines
        and len(bullet_lines) == manifest.get("row_count") == manifest.get("fingerprint_count")
    )


def build_child_artifact_provenance_render_bundle(
    manifest: dict[str, Any],
    source_list: list[str],
    manifest_markdown_rows: list[str],
    fingerprint_bullet_lines: list[str],
    source_markdown_lines: list[str],
) -> dict[str, Any]:
    return {
        "source": "child_artifact_fingerprint_manifest.entries_in_suite_order",
        "row_count": manifest.get("row_count"),
        "fingerprint_count": manifest.get("fingerprint_count"),
        "names_in_suite_order": manifest.get("names_in_suite_order"),
        "source_list": source_list,
        "manifest_markdown_rows": manifest_markdown_rows,
        "fingerprint_bullet_lines": fingerprint_bullet_lines,
        "source_markdown_lines": source_markdown_lines,
        "hashes_are_reproducibility_metadata_only": True,
        "not_forward_performance_evidence": True,
    }


def child_artifact_provenance_render_bundle_mirrors_manifest(
    bundle: dict[str, Any],
    manifest: dict[str, Any],
) -> bool:
    source_list = build_child_artifact_source_list(manifest)
    expected = build_child_artifact_provenance_render_bundle(
        manifest=manifest,
        source_list=source_list,
        manifest_markdown_rows=build_child_artifact_fingerprint_manifest_markdown_rows(manifest),
        fingerprint_bullet_lines=build_child_artifact_fingerprint_bullet_lines(manifest),
        source_markdown_lines=build_child_artifact_source_markdown_lines(source_list),
    )
    expected_count = manifest.get("row_count")
    return (
        bundle == expected
        and expected_count == manifest.get("fingerprint_count") == len(source_list) == len(bundle["manifest_markdown_rows"])
        and expected_count == len(bundle["fingerprint_bullet_lines"]) == len(bundle["source_markdown_lines"])
        and bundle.get("hashes_are_reproducibility_metadata_only") is True
        and bundle.get("not_forward_performance_evidence") is True
    )


def build_child_artifact_provenance_markdown_contract(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "child_artifact_provenance_render_bundle",
        "section_headings_in_render_order": [
            "Child Artifact Fingerprint Manifest",
            "Child Validation JSON Fingerprints",
            "Sources",
        ],
        "row_count": bundle.get("row_count"),
        "fingerprint_count": bundle.get("fingerprint_count"),
        "manifest_table_row_count": len(bundle.get("manifest_markdown_rows", [])),
        "fingerprint_bullet_count": len(bundle.get("fingerprint_bullet_lines", [])),
        "source_line_count": len(bundle.get("source_markdown_lines", [])),
        "names_in_suite_order": bundle.get("names_in_suite_order"),
        "hashes_are_reproducibility_metadata_only": True,
        "not_forward_performance_evidence": True,
    }


def child_artifact_provenance_markdown_contract_mirrors_bundle(
    contract: dict[str, Any],
    bundle: dict[str, Any],
) -> bool:
    expected = build_child_artifact_provenance_markdown_contract(bundle)
    expected_count = bundle.get("row_count")
    return (
        contract == expected
        and expected_count == bundle.get("fingerprint_count")
        and expected_count == contract.get("manifest_table_row_count")
        and expected_count == contract.get("fingerprint_bullet_count")
        and expected_count == contract.get("source_line_count")
        and contract.get("section_headings_in_render_order")
        == [
            "Child Artifact Fingerprint Manifest",
            "Child Validation JSON Fingerprints",
            "Sources",
        ]
        and contract.get("hashes_are_reproducibility_metadata_only") is True
        and contract.get("not_forward_performance_evidence") is True
    )


def build_child_artifact_provenance_contract_markdown_lines(contract: dict[str, Any]) -> list[str]:
    headings = contract.get("section_headings_in_render_order")
    if not isinstance(headings, list) or not all(isinstance(item, str) and item.strip() for item in headings):
        return []
    return [
        "## Child Artifact Provenance Render Contract",
        "",
        "This contract summarizes the checked child-artifact provenance sections below. It is render reproducibility metadata only, not settled ROI, live profitability, promotion readiness, or real-money evidence.",
        "",
        f"- Source: `{contract.get('source')}`",
        f"- Section order: {', '.join(headings)}",
        f"- Manifest table rows: {contract.get('manifest_table_row_count')}",
        f"- Fingerprint bullet rows: {contract.get('fingerprint_bullet_count')}",
        f"- Source lines: {contract.get('source_line_count')}",
    ]


def child_artifact_provenance_contract_markdown_lines_mirror_contract(
    contract: dict[str, Any],
    contract_lines: list[str],
) -> bool:
    expected = build_child_artifact_provenance_contract_markdown_lines(contract)
    expected_count = contract.get("row_count")
    return (
        bool(expected)
        and contract_lines == expected
        and expected_count == contract.get("fingerprint_count")
        and expected_count == contract.get("manifest_table_row_count")
        and expected_count == contract.get("fingerprint_bullet_count")
        and expected_count == contract.get("source_line_count")
        and contract_lines[0] == "## Child Artifact Provenance Render Contract"
        and contract_lines[4] == "- Source: `child_artifact_provenance_render_bundle`"
        and contract_lines[-3:] == [
            f"- Manifest table rows: {expected_count}",
            f"- Fingerprint bullet rows: {expected_count}",
            f"- Source lines: {expected_count}",
        ]
    )


def require_child_read(payload: dict[str, Any], label: str) -> str:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise AssertionError(f"{label} child JSON is missing summary metadata")
    for key in ("suite_read", "current_read"):
        value = summary.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise AssertionError(f"{label} child JSON is missing summary.suite_read/current_read")


def build_suite_read(payload_map: dict[str, dict[str, Any]]) -> str:
    research_read = payload_map["frozen_evidence_chain"].get("summary", {}).get("suite_read", "")
    operator_read = payload_map["paper_trade_operator_suite"].get("summary", {}).get("suite_read", "")
    report_read = payload_map["report_surfaces"].get("summary", {}).get("suite_read", "")
    readme_read = payload_map["readme_current_status"].get("summary", {}).get("suite_read", "")
    quickstart_read = payload_map["validation_quickstart"].get("summary", {}).get("suite_read", "")
    daily_read = payload_map["daily_artifact_guide"].get("summary", {}).get("suite_read", "")
    current_hierarchy_read = payload_map["current_hierarchy_language"].get("summary", {}).get("suite_read", "")
    paper_trade_usage_read = payload_map["paper_trade_usage"].get("summary", {}).get("suite_read", "")
    cole_status_read = payload_map["cole_status_and_plan"].get("summary", {}).get("suite_read", "")
    return (
        f"research side: {research_read}; "
        f"operator side: {operator_read}; "
        f"report side: {report_read}; "
        f"navigation side: README: {readme_read}; quickstart: {quickstart_read}; daily guide: {daily_read}; current hierarchy: {current_hierarchy_read}; paper-trade usage: {paper_trade_usage_read}; cole status: {cole_status_read}; "
        "project-surfaces suite layer: repo-wide alignment sweep that keeps frozen-evidence ordering, operator readiness, current hierarchy wording / structured-key compatibility, shareable wording / presentation drift / dated-report trust-path routing, and human-facing navigation/read-order contracts pinned together; cross-layer alignment check, not new forward evidence by itself; stronger forward confidence still requires settled paper trades and other real forward results; exact child-validation JSON byte counts and SHA-256 hashes are published for top-level reproducibility only, not performance evidence; machine-readable evidence_boundary metadata in the project JSON keeps validator passes separate from settled ROI, live profitability, promotion readiness, anchor-change evidence, companion-change evidence, and real-money evidence"
    )


def main() -> int:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rebuild_command = REBUILD_COMMAND + (f" {REUSE_EXISTING_FLAG}" if args.reuse_existing_child_json else "")
    child_validator_mode = "reuse-existing-child-json" if args.reuse_existing_child_json else "rebuild-children"

    rows: list[dict[str, Any]] = []
    total_checks = 0
    total_scenarios = 0
    total_report_checks = 0
    total_navigation_checks = 0
    payload_map: dict[str, dict[str, Any]] = {}

    for item in SUITE:
        payload = load_child_payload(item, args.reuse_existing_child_json)
        child_fingerprint = fingerprint_file(item["json_path"])
        payload_map[item["name"]] = payload
        artifact_status = require_child_status(payload, item["label"])
        value = require_explicit_int(payload, item["metric_key"], item["label"])
        child_check_count = require_explicit_int(payload, "check_count", item["label"])
        child_checks = require_child_checks(payload, item["label"])
        current_read = require_child_read(payload, item["label"])
        if item["name"] == "frozen_evidence_chain":
            total_checks += value
        elif item["name"] == "paper_trade_operator_suite":
            total_scenarios += value
        elif item["name"] == "report_surfaces":
            total_report_checks += value
        else:
            total_navigation_checks += value
        rows.append(
            {
                "name": item["name"],
                "label": item["label"],
                "metric_value": value,
                "metric_label": item["metric_label"],
                "result": artifact_status,
                "current_read": current_read,
                "json_path": child_fingerprint["path"],
                "child_json_bytes": child_fingerprint["bytes"],
                "child_json_sha256": child_fingerprint["sha256"],
                "child_json_fingerprint": child_fingerprint,
                "child_total_checks": payload.get("total_checks"),
                "child_check_count": child_check_count,
                "child_checks": child_checks,
                "child_structured_check_count": payload.get("child_check_count"),
                "child_structured_checks": payload.get("child_checks"),
            }
        )

    overall_pass = all(row["result"] == "PASS" for row in rows)
    if not overall_pass:
        raise AssertionError("Project surfaces suite has at least one failing validator")

    row_map = {row["name"]: row for row in rows}
    child_artifact_fingerprints = build_child_artifact_fingerprints(rows)
    child_artifact_fingerprint_manifest = build_child_artifact_fingerprint_manifest(
        child_artifact_fingerprints,
        rows,
    )
    child_artifact_fingerprint_manifest_markdown_rows = build_child_artifact_fingerprint_manifest_markdown_rows(
        child_artifact_fingerprint_manifest,
    )
    child_artifact_source_list = build_child_artifact_source_list(child_artifact_fingerprint_manifest)
    child_artifact_source_markdown_lines = build_child_artifact_source_markdown_lines(
        child_artifact_source_list,
    )
    child_artifact_fingerprint_bullet_lines = build_child_artifact_fingerprint_bullet_lines(
        child_artifact_fingerprint_manifest,
    )
    child_artifact_provenance_render_bundle = build_child_artifact_provenance_render_bundle(
        manifest=child_artifact_fingerprint_manifest,
        source_list=child_artifact_source_list,
        manifest_markdown_rows=child_artifact_fingerprint_manifest_markdown_rows,
        fingerprint_bullet_lines=child_artifact_fingerprint_bullet_lines,
        source_markdown_lines=child_artifact_source_markdown_lines,
    )
    child_artifact_provenance_markdown_contract = build_child_artifact_provenance_markdown_contract(
        child_artifact_provenance_render_bundle,
    )
    child_artifact_provenance_contract_markdown_lines = build_child_artifact_provenance_contract_markdown_lines(
        child_artifact_provenance_markdown_contract,
    )
    current_evidence = json.loads(CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8"))
    current_evidence_bridge_json_read = build_current_evidence_bridge_read(current_evidence)
    current_gate_progress = current_evidence.get("decision_gate_progress")
    if not isinstance(current_gate_progress, dict):
        raise AssertionError("current_evidence_summary.json must publish decision_gate_progress")
    current_gate_progress_read = str(current_gate_progress.get("read") or "").strip()
    if not current_gate_progress_read:
        raise AssertionError("current_evidence_summary.json decision_gate_progress.read must be populated")
    current_primary = current_evidence["current_paper_status"]["primary"]
    current_open_settlement_summary = str(current_primary.get("open_settlement_summary") or "").strip()
    current_first_gate = f"{current_primary['first_read']['current']}/{current_primary['first_read']['threshold']}"
    current_portfolio_gate = f"{current_primary['portfolio_review']['current']}/{current_primary['portfolio_review']['threshold']}"
    current_roi_complete = int(current_primary["roi_complete_settled"])
    current_remaining_first = int(current_primary["first_read"]["remaining"])
    current_open_rows = int(current_primary["open_settlements"])
    current_open_queue = current_primary.get("open_settlement_queue_by_rule")
    if not isinstance(current_open_queue, dict):
        raise AssertionError("current_evidence_summary.json must publish current_paper_status.primary.open_settlement_queue_by_rule")
    current_open_queue_state = str(current_open_queue.get("open_settlement_queue_state") or "").strip()
    current_open_queue_context = str(current_open_queue.get("open_settlement_context") or "").strip()
    current_open_queue_detail_read = str(current_open_queue.get("detail_read") or "").strip()
    expected_current_open_queue_state = "closed" if current_open_rows == 0 else "open"
    if current_open_queue_state != expected_current_open_queue_state:
        raise AssertionError("current-evidence open_settlement_queue_state must match open_settlements")
    if "Open settlement queue by rule:" not in current_open_queue_detail_read:
        raise AssertionError("current-evidence detail_read must carry by-rule open settlement detail")
    if "Settlement queue state:" in current_open_queue_detail_read:
        raise AssertionError("current-evidence detail_read must not nest the settlement queue state wrapper")
    current_settlement_word = "settlement" if current_roi_complete == 1 else "settlements"
    if current_open_rows == 0:
        cole_status_open_context_phrase = (
            "latest primary recommendation context stays framed as operator context while the closed primary settlement queue stays workflow metadata only"
        )
        cole_status_sample_context_phrase = (
            "clean empty/no-target runs plus the first tiny settled sample and closed settlement queue stay framed as workflow/operability validation and observation collection rather than promotion-grade forward proof"
        )
        cole_status_open_identity_phrase = "no open primary settlement rows currently published"
        paper_usage_open_context_phrase = "current bridge has no open primary settlement rows"
        bridge_queue_navigation = "closed settlement-queue plus recommendation-state context"
    else:
        cole_status_open_context_phrase = (
            "latest primary recommendation context stays framed as operator context while the current open-row identity stays settlement workflow only"
        )
        cole_status_sample_context_phrase = (
            "clean empty/no-target runs plus the first tiny settled sample and open settlement rows stay framed as workflow/operability validation and observation collection rather than promotion-grade forward proof"
        )
        cole_status_open_identity_phrase = "current open-row identity preserved as"
        paper_usage_open_context_phrase = "settlement workflow, not a bet-ready ticket or forward-performance proof"
        bridge_queue_navigation = "current open-row identity plus recommendation-state context"
    report_child_queue_context = (
        f"settlement queue state={current_open_queue_state} / context={current_open_queue_context}"
    )
    report_child_queue_workflow_phrase = (
        "remains workflow context rather than a bet-ready ticket or forward-performance proof"
        if current_open_rows == 0
        else "remains settlement workflow rather than a bet-ready ticket or forward-performance proof"
    )
    working_status_queue_check_name = (
        "current_settlement_queue_recommendation_state_context"
        if current_open_rows == 0
        else "current_open_row_recommendation_state_context"
    )
    working_child_queue_context = (
        f"settlement queue state={current_open_queue_state} / context={current_open_queue_context}"
    )
    working_child_queue_workflow_phrase = (
        "remains workflow context rather than a bet-ready ticket or forward-performance proof"
    )
    current_gate_phrase = f"{current_first_gate} and {current_portfolio_gate} gates"
    current_report_gate_phrase = (
        f"primary paper {current_first_gate} first-read and {current_portfolio_gate} broader-review gates"
    )
    source_freshness_label = (
        "requires refresh before right-now use"
        if current_evidence["source_freshness"].get("requires_refresh_before_right_now_use")
        else "fresh for right-now use"
    )
    combined_operator_route_label = (
        "requires refresh before right-now instruction or evidence use"
        if current_evidence["source_freshness"].get("requires_refresh_before_right_now_use")
        else "is fresh against the bridge reference date but still goes through operator read-gate routing before right-now instruction or evidence use"
    )
    full_report_operator_read_route_phrase = (
        f"combined operator-status/source-freshness/operator-read-gate route {combined_operator_route_label}"
    )
    working_operator_read_route_phrase = (
        f"combined operator-status/source-freshness/operator-read-gate route {combined_operator_route_label}"
    )
    report_operator_read_route_phrase = full_report_operator_read_route_phrase
    expected_operator_read_gate = (
        current_evidence.get("operator_read_gate")
        if isinstance(current_evidence.get("operator_read_gate"), dict)
        else {}
    )
    expected_operator_read_gate_read = str(expected_operator_read_gate.get("read") or "").strip()
    expected_operator_read_gate_line = f"operator_read_gate read={expected_operator_read_gate_read}"
    expected_operator_requires_refresh = bool(
        expected_operator_read_gate.get("requires_refresh_before_evidence_read")
    )
    expected_operator_recommended_command = expected_operator_read_gate.get("recommended_command")
    expected_operator_issue_flags = (
        "has_api_access_failure_context",
        "has_scanner_failure_boundary",
        "has_stale_cache_fallback_context",
    )

    def payload_operator_gate_matches(payload_name: str) -> bool:
        read = payload_map[payload_name].get("current_evidence_operator_read_gate_read")
        return (
            isinstance(read, dict)
            and read.get("source") == "current_evidence_summary.json"
            and read.get("source_path") == "operator_read_gate"
            and read.get("gate_status")
            in {"refresh_required_before_evidence_read", "current_operator_routing_context_only"}
            and read.get("valid_use") == "operator instruction/evidence-read gating only"
            and read.get("requires_refresh_before_evidence_read") is expected_operator_requires_refresh
            and read.get("recommended_command") == expected_operator_recommended_command
            and all(read.get(flag) is expected_operator_read_gate.get(flag) for flag in expected_operator_issue_flags)
            and read.get("current_top_card_counts_as_no_target_evidence") is False
            and read.get("current_top_card_counts_as_clean_empty_evidence") is False
            and read.get("current_top_card_counts_as_bet_readiness_evidence") is False
            and read.get("current_top_card_counts_as_settled_roi_evidence") is False
            and read.get("not_live_profitability_evidence") is True
            and read.get("not_real_money_evidence") is True
        )
    report_surface_rows = {
        row.get("name"): row
        for row in payload_map["report_surfaces"].get("rows", [])
        if isinstance(row, dict)
    }
    operator_markdown_path = OUT_DIR.parent / "paper_trade_operator_suite" / "paper_trade_operator_suite_validation.md"
    operator_markdown = require_report_text(operator_markdown_path, "paper_trade_operator_suite")
    operator_markdown_fingerprint = fingerprint_file(operator_markdown_path)
    operator_markdown_component_render_contract: dict[str, Any] = {
        "path": str(operator_markdown_path.relative_to(BASE)),
        "markdown_fingerprint": operator_markdown_fingerprint,
        "hashes_are_reproducibility_metadata_only": True,
        "required_snippets": [
            "| Validator | Fixture Scenarios | Check Components | Result | Source |",
            "operator_markdown_child_check_components_render_safe_formulas",
            "operator_markdown_table_contains_safe_component_render_snippets",
        ],
            "forbidden_snippets": [
                "| live_scan_targeting_and_limit_status | 1 | 1 fixture = 10 checks | PASS |",
                "| live_scan_targeting_and_limit_status | 1 | 1 fixture = 12 checks | PASS |",
            "| live_scan_targeting_and_limit_status | 1 | 1 fixture; 14 total checks | PASS |",
            "| refresh_live_paper_trade_surfaces | 5 | 5 fixture = 13 checks | PASS |",
            "| refresh_live_paper_trade_surfaces | 5 | 5 fixture = 14 checks | PASS |",
            "| refresh_live_paper_trade_surfaces | 5 | 5 fixture = 23 checks | PASS |",
            "| run_daily_portfolio_observation | 24 | 24 fixture = 12 checks | PASS |",
            "| run_daily_portfolio_observation | 24 | 24 fixture = 13 checks | PASS |",
            "| run_daily_portfolio_observation | 24 | 24 fixture; 16 total checks | PASS |",
        ],
    }
    operator_child_markdown_component_render_contract = payload_map["paper_trade_operator_suite"].get(
        "operator_markdown_component_render_contract"
    )
    if not isinstance(operator_child_markdown_component_render_contract, dict):
        operator_child_markdown_component_render_contract = {}
    operator_child_required_snippets = operator_child_markdown_component_render_contract.get("required_snippets")
    if not isinstance(operator_child_required_snippets, list):
        operator_child_required_snippets = []
    operator_child_forbidden_snippets = operator_child_markdown_component_render_contract.get("forbidden_snippets")
    if not isinstance(operator_child_forbidden_snippets, list):
        operator_child_forbidden_snippets = []
    merged_required_snippets = list(operator_markdown_component_render_contract["required_snippets"])
    for snippet in operator_child_required_snippets:
        if isinstance(snippet, str) and snippet not in merged_required_snippets:
            merged_required_snippets.append(snippet)
    operator_markdown_component_render_contract.update(
        {
            "required_snippets": merged_required_snippets,
            "child_contract_source_json": row_map["paper_trade_operator_suite"]["json_path"],
            "child_required_snippet_count": len(operator_child_required_snippets),
            "child_forbidden_snippet_count": len(operator_child_forbidden_snippets),
        }
    )
    stale_gate_shorthand_matches = find_stale_gate_shorthand_matches()
    stale_gate_shorthand_scan = {
        "scanned_suffixes": sorted(ACTIVE_TEXT_SUFFIXES),
        "excluded_names": sorted(STALE_GATE_SCAN_EXCLUDED_NAMES),
        "excluded_parts": sorted(STALE_GATE_SCAN_EXCLUDED_PARTS),
        "forbidden_pattern_count": len(STALE_GATE_SHORTHAND_PHRASES),
        "match_count": len(stale_gate_shorthand_matches),
        "matches": stale_gate_shorthand_matches,
        "valid_use": "repo-wide active source/report scan for stale compressed gate wording",
        "not_new_forward_evidence": True,
    }

    expected_report_surface_rows: dict[str, dict[str, Any]] = {
        "readme_current_status": {
            "count": 64,
            "json_path": "out/status_validation/readme_current_status/readme_current_status_validation.json",
            "snippets": {
                "anchor=OP_DURABLE_K7",
                "Phase 8=SHADOW ONLY",
                "current_evidence_summary.json scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus validate_scorecard_ranking_contract_audit.py for copied gate-floor/ranking/CI-only/timezone/no-BAQ prerequisite drift as synchronization metadata only",
                "Harville benchmark-only lane, current odds-only XGBoost research-only lane",
                "main status / repo-map route `COLE_STATUS_AND_PLAN.md` plus `validate_cole_status_and_plan.py` now visible for `status_doc_base_api_access_route_documented` base API-access / HTTP 403 status-summary route wording before lane enrichment as status/map alignment metadata only",
                "direct full-data XGBoost retrain caveat route `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py`",
                "RMSE / MAE diagnostics in model-fit context only rather than paper-trade, live-profitability, promotion, bankroll, or real-money evidence",
                "full-data retrain artifact plus direct validator in the report inventory",
                "scorecard audit markdown/JSON plus direct validator in the report inventory as synchronization/reproducibility metadata only",
                "main status document plus direct validator in the report inventory",
                "stale downstream lane details as inherited snapshot context rather than current-day state",
                "frozen-to-current bridge `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` now visible for short Cole updates",
                f"source consistency, the combined operator-status/source-freshness/operator-read-gate route, CD-only current rule mix, {bridge_queue_navigation}, scorecard_audit_route synchronization routing",
                "rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only",
                "bridge-published current gates source-matched to `forward_evidence_scorecard.json` `decision_gate_minimums`",
                "bridge-owned rebuild-order routing in the report inventory",
                expected_operator_read_gate_line,
                "no-new-forward-evidence / no-promotion / no-live-profitability / no-real-money boundaries",
                "operator_read_gate no-evidence routing",
                "source-published settlement queue state/detail read=",
                "anchor_displacement=30, phase8_promotion_review=20, and real_money_discussion=100",
                "direct cross-family current-paper validation path now pins stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and no OP-anchor / no cross-family-promotion evidence",
            },
            "checks": {
                "scorecard_nonpositive_phase8_floor_fails_before_artifacts",
                "scorecard_nonpositive_real_money_floor_fails_before_artifacts",
                "source_freshness_false_branch_is_fresh_not_refresh",
                "source_freshness_true_branch_is_refresh_first",
                "anchor_source_still_op_durable",
                "cold_start_scorecard_read",
                "cold_start_scorecard_audit_read",
                "current_evidence_scorecard_audit_route_read",
                "current_evidence_rebuild_validation_contract_read",
                "cold_start_main_comparison_read",
                "cold_start_full_data_retrain_caveat_read",
                "cold_start_current_evidence_read",
                "cold_start_status_doc_api_access_route",
                "cross_family_current_paper_route_present",
                "full_data_retrain_inventory_lines",
                "current_evidence_inventory_lines",
                "scorecard_audit_inventory_lines",
                "status_doc_api_access_inventory_lines",
                "readme_current_gates_source_match_scorecard_json",
                "current_evidence_api_access_route_line",
                "source_published_settlement_queue_state",
                "current_evidence_combined_operator_read_route",
                "current_evidence_operator_read_gate_route",
                "current_evidence_navigation_uses_bridge_published_gates",
                "readme_wrapper_leaf_source_of_truth_note_present",
                "report_alias_note",
            },
        },
        "cole_full_report": {
            "count": 29,
            "json_path": "out/status_validation/cole_full_report/cole_full_report_validation.json",
            "snippets": {
                "paper companion=CD_CORE_K8",
                "closest shadow=OP_REFINED_K7",
                "operational/reproducibility improvement rather than new forward evidence",
                "settled paper-trade rows with usable ROI coverage",
                "report gates source-matched to forward_evidence_scorecard.json decision_gate_minimums",
                "current evidence bridge=CURRENT_EVIDENCE_SUMMARY.md/current_evidence_summary.json",
                full_report_operator_read_route_phrase,
                expected_operator_read_gate_line,
                "scorecard audit route=current_evidence_summary.json.scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py",
                "rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only",
                current_report_gate_phrase,
                "current settled sample is CD-only context and not OP-anchor evidence",
                report_child_queue_context,
                report_child_queue_workflow_phrase,
                current_open_queue_detail_read,
                "direct cross-family current-paper caveat route=CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py",
                "green report validation not OP-anchor proof or cross-family promotion evidence",
                "full-data retrain caveat route=FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py",
                "large RMSE / MAE gains and exact retrain/prediction commands kept as model-fit reproducibility context",
            },
            "checks": {
                "full_report_evidence_scope_boundary",
                "malformed_scorecard_gate_floors_fail_before_artifacts",
                "paper_trade_ops_not_new_evidence_frame",
                "current_evidence_bridge_read",
                "current_evidence_scorecard_audit_route_present",
                "current_evidence_rebuild_validation_contract_read",
                "source_published_settlement_queue_state",
                "cross_family_current_paper_route_present",
                "full_data_retrain_caveat_route_present",
                "full_report_gate_source_matches_scorecard_json",
                "current_evidence_bridge_effective_gates_are_scorecard_backed",
                "current_evidence_combined_operator_read_route",
                "current_evidence_operator_read_gate_route",
                "rule_hierarchy_year_split",
                "method_family_guardrail_section",
                "stale_live_default_and_live_paper_lane_removed",
            },
        },
        "working_status_report": {
            "count": 26,
            "json_path": "out/status_validation/working_status_report/working_status_report_validation.json",
            "snippets": {
                "operability check rather than a profitability/deployment claim",
                "settled paper trades in the actual paper-trade lane",
                "primary paper-basket target tracks rather than stale basket-status shorthand",
                "current paper totals route through CURRENT_EVIDENCE_SUMMARY.md/current_evidence_summary.json",
                "rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only",
                working_operator_read_route_phrase,
                expected_operator_read_gate_line,
                "report gates source-matched to forward_evidence_scorecard.json decision_gate_minimums",
                current_report_gate_phrase,
                "current settled sample is CD-only context and not OP-anchor evidence",
                "direct cross-family current-paper caveat route=CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py",
                "green working-status validation not OP-anchor proof or cross-family promotion evidence",
                "full-data retrain caveat route=FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py",
                "large RMSE / MAE gains and exact retrain/prediction commands kept as model-fit reproducibility context",
                working_child_queue_context,
                working_child_queue_workflow_phrase,
                current_open_queue_detail_read,
                "mutable convenience alias",
            },
            "checks": {
                "scorecard_nonpositive_phase8_floor_fails_before_artifacts",
                "scorecard_nonpositive_real_money_floor_fails_before_artifacts",
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "production_vs_demo_distinction",
                "preflight_target_tracks_not_active_basket",
                "current_evidence_bridge_section",
                "current_evidence_rebuild_validation_contract_read",
                "cross_family_current_paper_route_present",
                "full_data_retrain_caveat_route_present",
                "working_status_gate_source_matches_scorecard_json",
                "current_evidence_combined_operator_read_route",
                "current_evidence_operator_read_gate_route",
                working_status_queue_check_name,
                "source_published_settlement_queue_state",
                "operational_bottom_line",
                "stale_latest_phrase_removed",
                "ops_active_tracks_still_op_cd",
            },
        },
        "cole_presentation_outline": {
            "count": 25,
            "json_path": "out/status_validation/cole_presentation_outline/cole_presentation_outline_validation.json",
            "snippets": {
                "method roles=PAPER NOW / BENCHMARK ONLY / RESEARCH ONLY",
                "full-data retrain caveat route=FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py",
                "large RMSE / MAE gains and exact retrain/prediction commands kept as model-fit reproducibility context",
                "workflow/observation proof, not live-edge confirmation",
                "remaining Phase 8 pockets=KEE_K9 / SA_K9 / DMR_FALL_K7 stay observation-only",
                "current evidence bridge=CURRENT_EVIDENCE_SUMMARY.md/current_evidence_summary.json",
                f"combined operator-status/source-freshness/operator-read-gate route {combined_operator_route_label}",
                expected_operator_read_gate_line,
                "scorecard audit route=current_evidence_summary.json.scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py",
                "rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only",
                current_report_gate_phrase,
                "current settled sample is CD-only context and not OP-anchor evidence",
                report_child_queue_context,
                current_open_queue_detail_read,
                "direct cross-family current-paper caveat route=CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py",
                "green presentation validation not OP-anchor proof or cross-family promotion evidence",
            },
            "checks": {
                "scorecard_nonpositive_phase8_floor_fails_before_artifacts",
                "scorecard_nonpositive_real_money_floor_fails_before_artifacts",
                "full_data_retrain_caveat_route_present",
                "paper_trade_workflow_not_live_proof",
                "presentation_evidence_scope_gate",
                "current_evidence_bridge_slide",
                "source_published_settlement_queue_state",
                "current_evidence_combined_operator_read_route",
                "current_evidence_operator_read_gate_route",
                "current_evidence_scorecard_audit_route_present",
                "current_evidence_rebuild_validation_contract_route",
                "cross_family_current_paper_route_present",
                "current_evidence_bridge_json_is_source_gate_routed",
                "current_evidence_bridge_effective_gates_are_scorecard_backed",
                "observation_only_pockets",
                "ml_failure_line",
            },
        },
        "superfecta_html_report": {
            "count": 33,
            "json_path": "out/status_validation/superfecta_html_report/superfecta_html_report_validation.json",
            "snippets": {
                "legacy alias=redirect-only warning page",
                "legacy PDF alias=claim-free warning export, not the old XGBoost rerun report or a separate evidence source",
                "legacy DOCX alias=claim-free warning document, not the old XGBoost rerun report or a separate evidence source",
                "legacy quick-start PDF alias=claim-free warning export, not the old ML/live-prediction quick-start or a separate evidence source",
                "legacy OpenClaw prompt DOCX alias=claim-free historical-prompt warning document, not the old ML/profitability-training prompt or a separate evidence source",
                "dated validated HTML trust anchor",
                "workflow/reproducibility improvement rather than new forward evidence",
                "current evidence bridge=CURRENT_EVIDENCE_SUMMARY.md/current_evidence_summary.json",
                report_operator_read_route_phrase,
                expected_operator_read_gate_line,
                "report gates source-matched to forward_evidence_scorecard.json decision_gate_minimums",
                "scorecard audit route=current_evidence_summary.json.scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks as report-synchronization metadata only",
                "rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only",
                "direct cross-family current-paper caveat route=CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py",
                "green HTML/PDF validation not OP-anchor proof or cross-family promotion evidence",
                "full-data retrain caveat route=FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py",
                "RMSE / MAE diagnostics kept as model-fit reproducibility context only",
                "OP_REFINED CI-only route=forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7 with ci_only_promotion_allowed=false",
                "dated PDF derivative export verified for the combined operator-status/source-freshness/operator-read-gate route, current-evidence bridge, rebuild-order route, scorecard-audit route, OP_REFINED CI-only boundary, cross-family current-paper caveat route, and full-data retrain caveat route",
                current_report_gate_phrase,
                "current settled sample is CD-only context and not OP-anchor evidence",
            },
            "checks": {
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "malformed_scorecard_gate_floors_fail_before_artifacts",
                "selective_family_current_paper_credibility_wording",
                "html_report_evidence_scope_boundary",
                "current_evidence_bridge_card",
                "html_report_gate_source_matches_scorecard_json",
                "current_evidence_combined_operator_read_route",
                "current_evidence_operator_read_gate_route",
                "html_pdf_scorecard_ci_only_boundary",
                "html_pdf_scorecard_audit_route",
                "html_pdf_current_evidence_rebuild_validation_contract_route",
                "cross_family_current_paper_route_present",
                "full_data_retrain_caveat_route_present",
                "dated_pdf_derivative_current_evidence_bridge",
                "paper_trade_workflow_not_new_evidence_frame",
                "legacy_alias_redirect_notice",
                "legacy_pdf_alias_claim_boundary",
                "legacy_docx_alias_claim_boundary",
                "legacy_quick_start_pdf_alias_claim_boundary",
                "legacy_prompt_docx_alias_claim_boundary",
                "stale_phrase_removed",
            },
        },
        "shareable_report_pdf_refresh": {
            "count": 5,
            "json_path": "out/status_validation/refresh_shareable_report_pdf/refresh_shareable_report_pdf_validation.json",
            "snippets": {
                "PDF refresh helper check-existing path passes through the dated HTML report validator",
                "dated HTML remains the trust anchor",
                "dated PDF remains a derivative export",
                "legacy undated PDF/DOCX aliases, legacy quick-start PDF alias, and legacy OpenClaw prompt DOCX alias stay claim-free",
                "HTML/PDF combined operator-read route, rebuild-order route, scorecard-audit route, OP_REFINED CI-only boundary, cross-family current-paper caveat route, and full-data retrain caveat route stay pinned",
                "reproducibility metadata only rather than settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence",
            },
            "checks": {
                "helper_script_exposes_safe_check_and_export_paths",
                "helper_check_existing_writes_pass_artifacts",
                "helper_routes_through_html_report_validator",
                "helper_publishes_html_pdf_fingerprints",
                "helper_publishes_report_safe_evidence_boundary",
            },
        },
    }
    checks = [
        require(
            all(row_map[name]["result"] == "PASS" for name in row_map)
            and all(isinstance(row_map[name]["metric_value"], int) and row_map[name]["metric_value"] > 0 for name in row_map)
            and all(isinstance(row_map[name]["child_check_count"], int) and row_map[name]["child_check_count"] > 0 for name in row_map)
            and all(isinstance(row_map[name]["current_read"], str) and row_map[name]["current_read"].strip() for name in row_map),
            "child_project_validators_publish_explicit_status_metrics_counts_and_reads",
            "all eight project-surface child validators now have to publish explicit PASS status, explicit metric integers, nonzero check_count, and non-empty summary read metadata instead of letting the top-level sweep infer them from permissive getters",
        ),
        require(
            len(rows) == len(SUITE)
            and all(isinstance(row.get("child_json_bytes"), int) and row["child_json_bytes"] > 0 for row in rows)
            and all(
                isinstance(row.get("child_json_sha256"), str)
                and len(row["child_json_sha256"]) == 64
                and all(char in "0123456789abcdef" for char in row["child_json_sha256"])
                for row in rows
            )
            and all(
                isinstance(row.get("child_json_fingerprint"), dict)
                and row["child_json_fingerprint"].get("path") == row.get("json_path")
                and row["child_json_fingerprint"].get("bytes") == row.get("child_json_bytes")
                and row["child_json_fingerprint"].get("sha256") == row.get("child_json_sha256")
                for row in rows
            ),
            "project_child_validator_json_fingerprints_are_published",
            "top-level project sweep now publishes exact byte counts and SHA-256 hashes for every child validation JSON it summarized, so repo-wide rollups are reproducible without treating child hashes as performance evidence",
        ),
        require(
            project_rows_publish_complete_metadata_contract(rows),
            "project_rows_publish_complete_metadata_contract",
            "top-level project rows now have to publish a complete metadata contract for every child validator: stable name/label/metric labels, stable validation JSON paths, PASS status, non-empty current reads, explicit metric and check totals, full child check inventories, and exact child JSON fingerprint metadata, so repo-wide rollups cannot silently pass with a flattened or partially stale child row",
        ),
        require(
            child_artifact_fingerprint_map_mirrors_rows(child_artifact_fingerprints, rows),
            "project_child_artifact_fingerprint_map_mirrors_rows",
            "the project JSON's aggregate child_artifact_fingerprints map now has to mirror the row-level child validation JSON paths, byte counts, and SHA-256 hashes exactly, so automation can consume the compact map without losing row-level provenance or treating hashes as performance evidence",
        ),
        require(
            child_artifact_fingerprint_manifest_mirrors_suite_order(
                child_artifact_fingerprint_manifest,
                child_artifact_fingerprints,
                rows,
            ),
            "project_child_artifact_fingerprint_manifest_preserves_suite_order",
            "the project JSON now publishes and checks an explicit child-artifact fingerprint manifest with the top-level validator names in suite order, so automation can consume compact child hashes deterministically while preserving the no-performance-evidence boundary",
        ),
        require(
            child_artifact_fingerprint_manifest_entries_mirror_rows(
                child_artifact_fingerprint_manifest,
                child_artifact_fingerprints,
                rows,
            ),
            "project_child_artifact_fingerprint_manifest_entries_mirror_rows",
            "the project JSON's child-artifact fingerprint manifest now carries per-child name/path/bytes/SHA-256 entries in suite order and checks those entries against both row-level provenance and the compact fingerprint map, so automation can consume one deterministic manifest without treating hashes as performance evidence",
        ),
        require(
            child_artifact_fingerprint_manifest_markdown_rows_mirror_entries(
                child_artifact_fingerprint_manifest,
                child_artifact_fingerprint_manifest_markdown_rows,
            ),
            "project_child_artifact_fingerprint_manifest_markdown_rows_mirror_entries",
            "the generated project markdown now has to render the same per-child fingerprint manifest rows as the JSON manifest entries, so human-readable validation output and machine-readable provenance stay aligned without turning child hashes into performance evidence",
        ),
        require(
            child_artifact_source_list_mirrors_manifest_entries(
                child_artifact_source_list,
                child_artifact_fingerprint_manifest,
                rows,
            ),
            "project_child_artifact_source_list_mirrors_manifest_entries",
            "the project JSON now publishes a compact child_artifact_source_list and checks that the generated markdown Sources section can be rendered from the same suite-order child JSON paths as the fingerprint manifest entries, so human-facing source routing cannot drift from machine-readable provenance",
        ),
        require(
            child_artifact_source_markdown_lines_mirror_source_list(
                child_artifact_source_list,
                child_artifact_source_markdown_lines,
                child_artifact_fingerprint_manifest,
            ),
            "project_child_artifact_sources_markdown_lines_mirror_source_list",
            "the generated project markdown's Sources section now has to render from the checked child_artifact_source_list, so the final human-readable source routing view cannot drift from the suite-order manifest paths",
        ),
        require(
            child_artifact_fingerprint_bullet_lines_mirror_entries(
                child_artifact_fingerprint_manifest,
                child_artifact_fingerprint_bullet_lines,
            ),
            "project_child_artifact_fingerprint_bullets_mirror_manifest_entries",
            "the generated project markdown's Child Validation JSON Fingerprints bullet list now has to render from the same suite-order manifest entries as the JSON sidecar, so the second human-readable provenance view cannot drift from the checked name/path/bytes/SHA-256 manifest",
        ),
        require(
            child_artifact_provenance_render_bundle_mirrors_manifest(
                child_artifact_provenance_render_bundle,
                child_artifact_fingerprint_manifest,
            ),
            "project_child_artifact_provenance_render_bundle_mirrors_manifest",
            "the project JSON now publishes a single child_artifact_provenance_render_bundle tying together the manifest table rows, fingerprint bullet rows, source markdown lines, source list, suite order, and provenance-only evidence boundary, so downstream automation has one checked render contract instead of three implicit human-report sections",
        ),
        require(
            child_artifact_provenance_markdown_contract_mirrors_bundle(
                child_artifact_provenance_markdown_contract,
                child_artifact_provenance_render_bundle,
            ),
            "project_child_artifact_provenance_markdown_contract_mirrors_bundle",
            "the project JSON now publishes a child_artifact_provenance_markdown_contract with the rendered provenance section order and per-section row counts, and checks those counts against the manifest-bound render bundle so the saved report's human provenance sections cannot silently lose rows while the JSON bundle stays green",
        ),
        require(
            child_artifact_provenance_contract_markdown_lines_mirror_contract(
                child_artifact_provenance_markdown_contract,
                child_artifact_provenance_contract_markdown_lines,
            ),
            "project_child_artifact_provenance_contract_markdown_lines_mirror_contract",
            "the project JSON now publishes the exact markdown lines used for the child-artifact provenance render contract and checks them against the contract counts, so the saved report header for the provenance sections is generated from the same machine-readable row-count contract",
        ),
        require(
            not stale_gate_shorthand_matches,
            "active_surfaces_do_not_reintroduce_stale_gate_shorthand",
            "active source and saved report/validation surfaces now fail the top-level sweep if stale compressed gate wording returns; the allowed current contract names primary 30, shadow 20, and portfolio 100 thresholds separately",
        ),
        require(
            current_evidence_bridge_json_read.get("source_path") == CURRENT_EVIDENCE_JSON.name
            and current_evidence_bridge_json_read.get("source_consistency_overall_match") is True
            and current_evidence_bridge_json_read.get("primary_roi_complete_rows_match") is True
            and current_evidence_bridge_json_read.get("primary_open_rows_match") is True
            and current_evidence_bridge_json_read.get("primary_incomplete_rows_match") is True
            and current_evidence_bridge_json_read.get("primary_roi_gap_rows_match") is True
            and current_evidence_bridge_json_read.get("source_freshness_state_valid") is True
            and isinstance(current_evidence_bridge_json_read.get("requires_refresh_before_right_now_use"), bool)
            and current_evidence_bridge_json_read.get("decision_gate_source") == "forward_evidence_scorecard.json"
            and current_evidence_bridge_json_read.get("decision_gate_source_loaded") is True
            and current_evidence_bridge_json_read.get("decision_gate_source_values_match_scorecard") is True
            and current_evidence_bridge_json_read.get("decision_gate_effective_values_source")
            == "forward_evidence_scorecard.json:decision_gate_minimums"
            and current_evidence_bridge_json_read.get("decision_gate_missing_top_card_fields") == []
            and current_evidence_bridge_json_read.get("decision_gate_mismatched_fields") == []
            and current_evidence_bridge_json_read.get("top_card_anchor_displacement_min") == 30
            and current_evidence_bridge_json_read.get("top_card_phase8_promotion_review_min") == 20
            and current_evidence_bridge_json_read.get("top_card_real_money_discussion_min") == 100
            and current_evidence_bridge_json_read.get("scorecard_anchor_displacement_min_from_bridge") == 30
            and current_evidence_bridge_json_read.get("scorecard_phase8_promotion_review_min_from_bridge") == 20
            and current_evidence_bridge_json_read.get("scorecard_real_money_discussion_min_from_bridge") == 100
            and current_evidence_bridge_json_read.get("effective_anchor_displacement_min") == 30
            and current_evidence_bridge_json_read.get("effective_phase8_promotion_review_min") == 20
            and current_evidence_bridge_json_read.get("effective_real_money_discussion_min") == 100
            and current_evidence_bridge_json_read.get("decision_gate_threshold_sources", {}).get("anchor_displacement")
            == "forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations"
            and current_evidence_bridge_json_read.get("decision_gate_threshold_sources", {}).get(
                "phase8_promotion_review"
            )
            == "forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations"
            and current_evidence_bridge_json_read.get("decision_gate_threshold_sources", {}).get(
                "real_money_discussion"
            )
            == "forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi"
            and current_evidence_bridge_json_read.get("not_new_forward_evidence") is True
            and current_evidence_bridge_json_read.get("not_promotion_readiness_evidence") is True
            and current_evidence_bridge_json_read.get("not_live_profitability_evidence") is True
            and current_evidence_bridge_json_read.get("not_real_money_evidence") is True,
            "project_current_evidence_bridge_effective_gates_are_scorecard_backed",
            "the top-level project sweep now directly publishes and verifies the current-evidence bridge's canonical top-card, scorecard, and effective 30 / 20 / 100 gate values with exact scorecard threshold-source paths, so the repo-wide parent cannot rely only on child rollups for current gate provenance",
        ),
        require(
            "OP_DURABLE_K7" in row_map["frozen_evidence_chain"]["current_read"]
            and "CD_CORE_K8" in row_map["frozen_evidence_chain"]["current_read"]
            and "harville_ranked" in row_map["frozen_evidence_chain"]["current_read"]
            and "xgboost_residual" in row_map["frozen_evidence_chain"]["current_read"]
            and "model-fit context, not a betting-evidence line" in row_map["frozen_evidence_chain"]["current_read"]
            and "saved CSV, saved markdown, saved JSON sidecar, and real CLI stdout stay pinned to the same main-comparison render" in row_map["frozen_evidence_chain"]["current_read"]
            and "method-family action summary tells Cole to spend operational energy on settled selective paper observations first while Harville and current odds-only XGBoost stay comparison controls unless their evidence class changes" in row_map["frozen_evidence_chain"]["current_read"]
            and "method-family evidence-debt checklist now names the missing evidence class, invalid shortcuts, and next honest action for the selective OP/CD path, Harville, and current odds-only XGBoost" in row_map["frozen_evidence_chain"]["current_read"]
            and "paper-observation gates now pin OP_REFINED_K7 promotion, current odds-only XGBoost reopening, BEL/BAQ substitution, and real-money scaling behind forward evidence thresholds" in row_map["frozen_evidence_chain"]["current_read"]
            and "machine-readable decision-gate minimums keep anchor_displacement=30 same-candidate rows, phase8_promotion_review=20 shadow rows, and real_money_discussion=100 total settled rows named separately" in row_map["frozen_evidence_chain"]["current_read"]
            and "historical train-only selector benchmark" in row_map["frozen_evidence_chain"]["current_read"]
            and "+22.46% result is useful evaluation context" in row_map["frozen_evidence_chain"]["current_read"]
            and "previously mined candidate universe" in row_map["frozen_evidence_chain"]["current_read"]
            and "BEL->BAQ is a failed coverage diagnostic" in row_map["frozen_evidence_chain"]["current_read"]
            and "historical frozen replay" in row_map["frozen_evidence_chain"]["current_read"]
            and "Phase 7 remains strongest historical candidate-family context" in row_map["frozen_evidence_chain"]["current_read"]
            and "cost/Kelly/historical profit lines are backtest or paper-accounting metadata only" in row_map["frozen_evidence_chain"]["current_read"]
            and "Phase 8 is legacy full-sample discovery context, not the deployment guide" in row_map["frozen_evidence_chain"]["current_read"]
            and "historical paper-accounting metadata only" in row_map["frozen_evidence_chain"]["current_read"]
            and "legacy large-sample negative baseline for broad structural, Harville, and generic odds-only ML families" in row_map["frozen_evidence_chain"]["current_read"]
            and "does not override the scorecard, main comparison, current-evidence bridge, OP_DURABLE_K7 anchor, CD_CORE_K8 paper companion, or the OP/CD paper-observation route" in row_map["frozen_evidence_chain"]["current_read"]
            and "report/metadata sidecar expose exact source-byte fingerprints" in row_map["frozen_evidence_chain"]["current_read"]
            and "without turning hashes into performance evidence" in row_map["frozen_evidence_chain"]["current_read"]
            and "exact child-validation JSON byte counts and SHA-256 hashes are published for reproducibility only, not performance evidence" in row_map["frozen_evidence_chain"]["current_read"]
            and "scorecard ranking-contract audit: scorecard ranking-contract / CI-only audit verifies every configured report-facing text and JSON surface carries the tier-first contract or source-matched OP_REFINED CI-only diagnostic" in row_map["frozen_evidence_chain"]["current_read"]
            and "scorecard-audit route, and rebuild-validation contract from current_evidence_summary.json as routing metadata only" in row_map["frozen_evidence_chain"]["current_read"]
            and "full-data retrain: FULL_DATA_RETRAIN_ARTIFACTS.md still records the 14years.csv retrain command and large payout-fit metrics while keeping those metrics in model-research context only" in row_map["frozen_evidence_chain"]["current_read"]
            and "XGBoost research-only unless its evidence class changes materially and downstream/paper evidence follows" in row_map["frozen_evidence_chain"]["current_read"]
            and "machine-readable evidence_boundary metadata keeps research validator passes, child hashes, and frozen replay alignment separate from settled ROI" in row_map["frozen_evidence_chain"]["current_read"]
            and "research-side evidence-alignment check, not new forward evidence by itself" in row_map["frozen_evidence_chain"]["current_read"],
            "research_layer_keeps_anchor_and_method_roles",
            "research rollup still keeps the OP anchor, the CD paper companion, the Harville/XGBoost benchmark-vs-research guardrails, the OP-anchor forward-observation decision gates, the XGBoost payout-RMSE gain labeled as model-fit context rather than a betting-evidence line, the full-data retrain artifact labeled as model-fit research context only, the main-comparison saved CSV/markdown/JSON sidecar, machine-readable evidence boundary, machine-readable decision-gate minimums, plus CLI reproducibility read, the method-family action-summary guidance, the method-family evidence-debt checklist, the walk-forward train-only benchmark caution, the frozen-replay metadata-sidecar / source-fingerprint boundary, the direct Phase 7 and Phase 8 legacy-report cautions, the legacy broad-backtest negative-baseline caution, the parent child-validation JSON source audit, the scorecard ranking-contract cross-surface audit, the machine-readable frozen-chain evidence boundary, and the research-side no-new-evidence caution visible",
        ),
        require(
            row_map["frozen_evidence_chain"].get("child_check_count") == 36
            and isinstance(row_map["frozen_evidence_chain"].get("child_checks"), list)
            and {check.get("check") for check in row_map["frozen_evidence_chain"]["child_checks"]} == {
                "child_research_validators_publish_explicit_status_metrics_counts_and_reads",
                "child_validator_json_fingerprints_are_published",
                "scorecard_keeps_deployment_tiers",
                "core_research_source_validators_publish_explicit_suite_status_and_totals",
                "walk_forward_caution_keeps_train_only_boundary",
                "walk_forward_caution_publishes_structured_child_checks",
                "frozen_replay_caution_keeps_metadata_boundary",
                "frozen_replay_caution_publishes_structured_child_checks",
                "phase7_report_caution_keeps_anchor_boundary",
                "phase7_report_caution_publishes_structured_child_checks",
                "phase8_report_caution_keeps_cost_boundary",
                "phase8_report_caution_publishes_structured_child_checks",
                "backtest_report_caution_publishes_structured_child_checks",
                "scorecard_publishes_structured_child_checks",
                "comparison_layer_keeps_phase_and_switch_guardrails",
                "comparison_layer_publishes_structured_child_checks",
                "compare_main_scratch_metadata_propagated",
                "frozen_stack_keeps_anchor_benchmark_and_watch_roles",
                "frozen_stack_publishes_structured_child_checks",
                "decision_cards_keep_cross_family_roles",
                "decision_cards_publishes_structured_child_checks",
                "scorecard_ranking_contract_audit_publishes_structured_child_checks",
                "scorecard_audit_route_diagnostics_propagated",
                "scorecard_rebuild_validation_contract_diagnostics_propagated",
                "scorecard_ranking_contract_audit_scratch_metadata_propagated",
                "narrow_research_leaf_validators_publish_explicit_suite_status_and_totals",
                "narrow_research_leaf_scratch_metadata_propagated",
                "op_anchor_comparison_keeps_method_roles_and_companion_order",
                "op_anchor_comparison_publishes_structured_child_checks",
                "downstream_ab_keeps_negative_betting_read",
                "downstream_ab_publishes_structured_child_checks",
                "full_data_retrain_artifact_guardrail_publishes_structured_child_checks",
                "scope_guardrail_keeps_paper_default_vs_counterfactual_split",
                "scope_guardrail_publishes_structured_child_checks",
                "frozen_chain_explicitly_stays_alignment_not_new_evidence",
                "frozen_chain_json_publishes_machine_readable_evidence_boundary",
            },
            "research_layer_publishes_structured_rollup_checks",
            "research rollup now has to publish its thirty-six explicit structured guardrails, including the child-validation JSON source audit, the direct walk-forward train-only benchmark caution, the direct frozen-replay metadata-sidecar boundary, the direct Phase 7 anchor-family caution, the direct Phase 8 legacy/cost-boundary caution, the legacy broad-backtest negative-baseline caution, the scorecard ranking-contract cross-surface audit plus route-diagnostics, rebuild-contract diagnostics, and child_scratch passthrough, the compare-main scratch-passthrough contract, the full-data retrain diagnostic-only guardrail, the machine-readable evidence-boundary contract, the narrow-leaf suite-status/total-check metadata and scratch-passthrough contracts, and the research-side no-new-evidence caution, instead of only a summary string",
        ),
        require(
            isinstance(payload_map["frozen_evidence_chain"].get("rows"), list)
            and any(
                row.get("name") == "walk_forward_validation_caution"
                and row.get("child_check_count") == 15
                and "historical train-only selector benchmark" in str(row.get("current_read") or "")
                and "valid_evidence_scope=train_only_walk_forward_selector_benchmark_only" in str(row.get("current_read") or "")
                and "+22.46% result is useful evaluation context" in str(row.get("current_read") or "")
                and "previously mined candidate universe" in str(row.get("current_read") or "")
                and "fixed Phase 7 / Phase 8 rows are replay context rather than extra train-only validation" in str(row.get("current_read") or "")
                and "BEL->BAQ is a failed coverage diagnostic" in str(row.get("current_read") or "")
                and "not settled paper-trade ROI, promotion readiness, live profitability, bankroll guidance, real-money evidence, or BAQ/BEL aliasing" in str(row.get("current_read") or "")
                and "current bridge rebuild order is read from current_evidence_summary.json.rebuild_validation_contract as provenance metadata only" in str(row.get("current_read") or "")
                and isinstance(row.get("child_checks"), list)
                and {check.get("check") for check in row["child_checks"]} == {
                    "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                    "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                    "current_evidence_rebuild_validation_contract_read",
                    "current_evidence_boundary_present",
                    "walk_forward_valid_evidence_scope_visible",
                    "not_paper_trade_or_real_money_evidence",
                    "valid_use_as_selector_benchmark",
                    "candidate_universe_limitation_visible",
                    "current_operator_posture_visible",
                    "fixed_replay_and_baq_boundaries_visible",
                    "train_only_headline_metrics_present",
                    "fixed_replay_comparison_present",
                    "bel_baq_coverage_break_present",
                    "unstable_years_visible",
                    "generator_preserves_boundary",
                }
                for row in payload_map["frozen_evidence_chain"]["rows"]
            ),
            "project_layer_can_see_walk_forward_boundary_inside_frozen_rows",
            "the project-level sweep can now verify that the frozen-evidence row inventory includes the direct walk-forward validation caution's fifteen structured checks, including current-bridge rebuild-contract fail-closed fixtures, train-only selector benchmark framing plus raw valid_evidence_scope, candidate-universe limitation, current anchor/companion/shadow posture, fixed replay vs train-only separation, failed BEL->BAQ diagnostic, unstable-year visibility, and generator-preserved caution wording",
        ),
        require(
            isinstance(payload_map["frozen_evidence_chain"].get("rows"), list)
            and any(
                row.get("name") == "scorecard_ranking_contract_audit"
                and row.get("child_check_count") == 31
                and isinstance(row.get("child_scorecard_audit_route_diagnostics"), dict)
                and isinstance(row.get("child_rebuild_validation_contract_diagnostics"), dict)
                and row["child_scorecard_audit_route_diagnostics"].get("source_row")
                == "current_evidence_summary_json_scorecard_audit_route"
                and row["child_scorecard_audit_route_diagnostics"].get("route_matches_expected_contract") is True
                and row["child_scorecard_audit_route_diagnostics"].get("route_field_contract_matches_expected") is True
                and row["child_scorecard_audit_route_diagnostics"].get("route_field_contract_mismatches") == []
                and row["child_scorecard_audit_route_diagnostics"].get("route_gate_floor_snapshot_matches_source") is True
                and row["child_scorecard_audit_route_diagnostics"].get("route_validator_command_matches_contract") is True
                and row["child_scorecard_audit_route_diagnostics"].get("route_valid_use_matches_contract") is True
                and row["child_scorecard_audit_route_diagnostics"].get("route_non_evidence_flags_match_contract") is True
                and row["child_scorecard_audit_route_diagnostics"].get("route_read_required_phrases_present") is True
                and row["child_scorecard_audit_route_diagnostics"].get("route_read_missing_phrases") == []
                and row["child_scorecard_audit_route_diagnostics"].get("referenced_route_artifacts_verified_on_disk") is True
                and row["child_rebuild_validation_contract_diagnostics"].get("source_row")
                == "current_evidence_summary_json_rebuild_validation_contract"
                and row["child_rebuild_validation_contract_diagnostics"].get("expected_upstream_refresh_order_commands")
                == [
                    "python3 paper_trade_settlement_audit.py",
                    "python3 current_evidence_summary.py",
                    "python3 validate_current_evidence_summary.py",
                ]
                and row["child_rebuild_validation_contract_diagnostics"].get("observed_upstream_refresh_order_commands")
                == [
                    "python3 paper_trade_settlement_audit.py",
                    "python3 current_evidence_summary.py",
                    "python3 validate_current_evidence_summary.py",
                ]
                and row["child_rebuild_validation_contract_diagnostics"].get(
                    "upstream_refresh_order_commands_match_expected"
                )
                is True
                and row["child_rebuild_validation_contract_diagnostics"].get("contract_matches_expected") is True
                and row["child_rebuild_validation_contract_diagnostics"].get("contract_field_mismatches") == []
                and row["child_rebuild_validation_contract_diagnostics"].get(
                    "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
                )
                is True
                and row["child_rebuild_validation_contract_diagnostics"].get(
                    "required_non_evidence_flags_match_contract"
                )
                is True
                and row["child_rebuild_validation_contract_diagnostics"].get(
                    "upstream_refresh_order_valid_use_matches_contract"
                )
                is True
                and row["child_rebuild_validation_contract_diagnostics"].get(
                    "direct_validation_command_matches_contract"
                )
                is True
                and row.get("child_scratch", {}).get("tmp_parent_is_project_local") is True
                and row.get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
                and "scorecard ranking-contract / CI-only audit" in str(row.get("current_read") or "")
                and "report synchronization only" in str(row.get("current_read") or "")
                and "not forward evidence or promotion readiness" in str(row.get("current_read") or "")
                and isinstance(row.get("child_checks"), list)
                and {check.get("check") for check in row["child_checks"]} == {
                    "saved_artifacts_match_fresh_rebuild",
                    "rebuild_command_matches_saved_timestamp",
                    "generated_at_has_explicit_timezone_label",
                    "all_expected_surfaces_pass",
                    "source_contract_pinned",
                    "source_ci_only_diagnostic_pinned",
                    "source_decision_gate_minimums_pinned",
                    "text_surfaces_inventory",
                    "text_ci_only_surfaces_inventory",
                    "json_contract_surfaces_inventory",
                    "json_ci_only_surfaces_inventory",
                    "json_scorecard_audit_route_surface_inventory",
                    "json_scorecard_audit_route_structured_diagnostics",
                    "json_rebuild_validation_contract_surface_inventory",
                    "json_rebuild_validation_contract_diagnostics_payload_published",
                    "json_scorecard_audit_route_diagnostics_payload_published",
                    "surface_inventory_markdown_matches_json_and_disk",
                    "evidence_boundary_present",
                    "non_goals_present",
                    "cli_scratch_root_project_local",
                    "cli_scratch_metadata_published",
                    "missing_source_contract_fails_fast",
                    "missing_source_ci_only_diagnostic_fails_fast",
                    "bad_scorecard_audit_route_artifacts_fail_in_process",
                    "bad_scorecard_audit_route_gate_floor_snapshot_fails_in_process",
                    "bad_scorecard_audit_route_command_source_fails_in_process",
                    "bad_scorecard_audit_route_non_evidence_flags_fail_in_process",
                    "bad_scorecard_audit_route_read_phrase_fails_in_process",
                    "bad_rebuild_validation_contract_fails_in_process",
                    "missing_current_evidence_rebuild_contract_fails_before_audit_artifacts",
                    "weakened_current_evidence_rebuild_contract_fails_before_audit_artifacts",
                }
                for row in payload_map["frozen_evidence_chain"]["rows"]
            ),
            "project_layer_can_see_scorecard_audit_timestamp_guardrail_inside_frozen_rows",
            "the project-level sweep can now verify that the frozen-evidence row inventory exposes the scorecard ranking-contract / CI-only diagnostic audit's thirty-one structured checks, including generated_at timezone-label provenance, saved-timestamp rebuild-command parity, report-surface fingerprint parity, source-matched OP_REFINED CI-only diagnostic coverage, source-matched current-evidence scorecard_audit_route coverage plus structured route diagnostics exported into the parent row, source-matched rebuild_validation_contract coverage plus diagnostics, bad-route artifact-path, gate-floor snapshot, command/source metadata, non-evidence-flag, route-read phrase, bad-rebuild-contract fail-fast coverage, real-CLI missing/weakened rebuild-contract no-artifact coverage, source-matched 30/20/100 gate floors, project-local scratch metadata, and no-new-forward-evidence boundaries, instead of only seeing the frozen-evidence umbrella summary string",
        ),
        require(
            isinstance(payload_map["frozen_evidence_chain"].get("rows"), list)
            and any(
                row.get("name") == "forward_evidence_scorecard"
                and row.get("child_check_count") == 33
                and row.get("child_scratch", {}).get("tmp_parent_is_project_local") is True
                and row.get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
                and "OP_DURABLE_K7 stays ANCHOR at rank 1" in str(row.get("current_read") or "")
                and "machine-readable decision-gate minimums" in str(row.get("current_read") or "")
                and "valid_evidence_scope=frozen_holdout_walk_forward_scorecard_only" in str(row.get("current_read") or "")
                and "cannot be mistaken for posture-changing evidence" in str(row.get("current_read") or "")
                and isinstance(row.get("child_checks"), list)
                and {check.get("check") for check in row["child_checks"]} == {
                    "anchor_row",
                    "paper_vs_watch_guardrail",
                    "tier_first_ranking_contract",
                    "year_split_columns",
                    "deployment_context_columns",
                    "decision_change_gates",
                    "decision_gate_minimums_json_present",
                    "bel_dormant",
                    "bel_dormant_current_paper_weight_wording",
                    "negative_holdout_skip",
                    "source_scope_text",
                    "source_scope_csv_columns",
                    "scorecard_outputs_expose_valid_evidence_scope",
                    "bootstrap_ci_source_csv_columns",
                    "bootstrap_ci_csv_json_source_parity",
                    "json_sidecar_surface",
                    "generated_at_timezone_contract",
                    "json_machine_readable_evidence_boundary",
                    "bootstrap_ci_report_fingerprints",
                    "phase7_report_paper_only_risk_boundary",
                    "phase8_report_shadow_only_cost_boundary",
                    "holdout_split_text",
                    "watch_triage_text",
                    "key_insight_text",
                    "cli_stdout_surface",
                    "cli_pinned_rerender",
                    "cli_generated_at_requires_timezone_label",
                    "cli_scratch_root_project_local",
                    "cli_scratch_metadata_published",
                    "missing_source_slice_fails_fast",
                    "conflicting_duplicate_slice_fails_fast",
                    "bootstrap_ci_source_text_missing_fails_fast",
                    "phase8_bootstrap_ci_source_text_missing_fails_fast",
                }
                for row in payload_map["frozen_evidence_chain"]["rows"]
            ),
            "project_layer_can_see_scorecard_gate_minimums_guardrail_inside_frozen_rows",
            "the project-level sweep can now verify that the frozen-evidence row inventory still exposes the forward-evidence scorecard validator's thirty-three structured checks, including JSON machine-readable evidence-boundary metadata, exact valid_evidence_scope metadata, tier-first ranking-contract metadata, generated-at timezone-label provenance, decision-gate minimums, dormant-BEL current-paper wording, CSV bootstrap-CI source-note columns, CSV/JSON bootstrap-CI source parity, bootstrap-CI source notes plus report fingerprints, exact Phase 7 and separate Phase 8 bootstrap-CI report-text fail-fast coverage, the PHASE7 report paper-only risk boundary, the PHASE8 report shadow-only cost boundary, source-scope sidecars, year-split columns, no-timezone generated-at CLI fail-fast coverage, project-local CLI scratch-root coverage, top-level scratch metadata, and fail-fast source-slice guards, instead of only seeing the frozen-evidence umbrella summary string",
        ),
        require(
            isinstance(payload_map["frozen_evidence_chain"].get("rows"), list)
            and any(
                row.get("name") == "phase7_report_caution"
                and row.get("child_check_count") == 12
                and "valid_evidence_scope=legacy_phase7_discovery_context_only" in str(row.get("current_read") or "")
                and "Phase 7 remains strongest historical candidate-family context" in str(row.get("current_read") or "")
                and "OP_DURABLE_K7 stays anchor" in str(row.get("current_read") or "")
                and "CD_CORE_K8 stays the paper companion" in str(row.get("current_read") or "")
                and "OP_REFINED_K7 and Phase 8 stay shadow/watch" in str(row.get("current_read") or "")
                and "dormant BEL is not BAQ" in str(row.get("current_read") or "")
                and "cost/Kelly/historical profit lines are backtest or paper-accounting metadata only" in str(row.get("current_read") or "")
                and "current bridge rebuild order is read from current_evidence_summary.json.rebuild_validation_contract as provenance metadata only" in str(row.get("current_read") or "")
                and isinstance(row.get("child_checks"), list)
                and {check.get("check") for check in row["child_checks"]} == {
                    "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                    "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                    "current_evidence_rebuild_validation_contract_read",
                    "top_current_evidence_boundary_present",
                    "phase7_report_valid_evidence_scope_visible",
                    "current_anchor_companion_watch_posture_visible",
                    "bel_dormant_and_baq_boundary_visible",
                    "cost_kelly_profit_lines_labeled_metadata",
                    "direct_validator_route_present",
                    "automation_guidance_is_paper_observation_only",
                    "risk_boundary_blocks_bankroll_and_real_money_overread",
                    "generator_emits_same_boundary_and_paper_only_guidance",
                }
                for row in payload_map["frozen_evidence_chain"]["rows"]
            ),
            "project_layer_can_see_phase7_report_anchor_boundary_inside_frozen_rows",
            "the project-level sweep can now verify that the frozen-evidence row inventory includes the direct Phase 7 report caution validator's twelve structured checks, including current-bridge rebuild-contract fail-closed fixtures, exact valid_evidence_scope metadata, OP anchor / CD companion / Phase 8 shadow posture, dormant BEL / no-BAQ boundary, cost/Kelly paper-accounting boundaries, paper-only automation guidance, and generator-preserved caution wording",
        ),
        require(
            isinstance(payload_map["frozen_evidence_chain"].get("rows"), list)
            and any(
                row.get("name") == "phase8_report_caution"
                and row.get("child_check_count") == 16
                and "legacy full-sample discovery context, not the deployment guide" in str(row.get("current_read") or "")
                and "historical paper-accounting metadata only" in str(row.get("current_read") or "")
                and "not real-money placement, sizing, bankroll, stop-loss, or scale-up guidance" in str(row.get("current_read") or "")
                and "current bridge rebuild order is read from current_evidence_summary.json.rebuild_validation_contract as provenance metadata only" in str(row.get("current_read") or "")
                and isinstance(row.get("child_checks"), list)
                and {check.get("check") for check in row["child_checks"]} == {
                    "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                    "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                    "current_evidence_rebuild_validation_contract_read",
                    "top_caution_banner_present",
                    "strict_holdout_comparison_visible",
                    "current_deployment_posture_visible",
                    "real_money_and_baq_boundaries_visible",
                    "cost_lines_labeled_paper_accounting_not_sizing",
                    "original_summary_labeled_as_full_sample",
                    "legacy_verdict_demoted_by_current_gate",
                    "deep_comparison_section_demoted",
                    "unqualified_legacy_promotion_phrases_removed",
                    "robustness_signals_labeled_as_original_read",
                    "k9_and_top2_mass_findings_demoted",
                    "legacy_fallback_not_current_operator_fallback",
                    "new_track_discoveries_keep_current_status",
                }
                for row in payload_map["frozen_evidence_chain"]["rows"]
            ),
            "project_layer_can_see_phase8_report_cost_boundary_inside_frozen_rows",
            "the project-level sweep can now verify that the frozen-evidence row inventory includes the direct Phase 8 report caution validator's sixteen structured checks, including current-bridge rebuild-contract fail-closed fixtures, cost/sizing paper-accounting boundaries, and legacy full-sample demotion guardrails",
        ),
        require(
            isinstance(payload_map["frozen_evidence_chain"].get("rows"), list)
            and any(
                row.get("name") == "backtest_report_caution"
                and row.get("child_check_count") == 10
                and "legacy large-sample negative baseline" in str(row.get("current_read") or "")
                and "generic odds-only ML families" in str(row.get("current_read") or "")
                and "does not override the scorecard, main comparison, current-evidence bridge, OP_DURABLE_K7 anchor, CD_CORE_K8 paper companion, or the OP/CD paper-observation route" in str(row.get("current_read") or "")
                and "valid_evidence_scope=legacy_broad_backtest_negative_baseline_context_only" in str(row.get("current_read") or "")
                and "full-data XGBoost retrain artifacts stay model-fit reproducibility context only" in str(row.get("current_read") or "")
                and "BAQ is not BEL" in str(row.get("current_read") or "")
                and isinstance(row.get("child_checks"), list)
                and {check.get("check") for check in row["child_checks"]} == {
                    "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                    "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                    "backtest_report_current_evidence_boundary_present",
                    "backtest_generator_preserves_current_evidence_boundary",
                    "backtest_report_valid_evidence_scope_visible",
                    "current_evidence_rebuild_contract_visible_for_legacy_backtest_context",
                    "legacy_negative_baseline_still_present",
                    "odds_only_xgboost_stays_parked",
                    "no_baq_as_bel_boundary_present",
                    "referenced_full_data_retrain_artifacts_exist",
                }
                for row in payload_map["frozen_evidence_chain"]["rows"]
            ),
            "project_layer_can_see_backtest_report_negative_baseline_inside_frozen_rows",
            "the project-level sweep can now verify that the frozen-evidence row inventory includes the direct legacy broad-backtest caution validator's ten structured checks, including current-bridge rebuild-contract fail-closed fixtures, generator-preserved current-evidence boundary wording, raw valid_evidence_scope visibility, negative broad-baseline framing, odds-only XGBoost parked status, full-data retrain routing, and no-BAQ-as-BEL separation",
        ),
        require(
            isinstance(payload_map["frozen_evidence_chain"].get("rows"), list)
            and any(
                row.get("name") == "frozen_portfolio_eval_caution"
                and row.get("child_check_count") == 23
                and "historical frozen replay" in str(row.get("current_read") or "")
                and "valid_evidence_scope=frozen_portfolio_replay_chronological_holdout_only" in str(row.get("current_read") or "")
                and "not live paper-trade or real-money evidence" in str(row.get("current_read") or "")
                and "BAQ is not BEL" in str(row.get("current_read") or "")
                and "current top-card quotes must go through the combined operator_status_context/source_freshness/operator_read_gate route before use" in str(row.get("current_read") or "")
                and "current bridge rebuild route" in str(row.get("current_read") or "")
                and "exact source-byte fingerprints for reproducibility without turning hashes into performance evidence" in str(row.get("current_read") or "")
                and "machine-readable evidence_boundary_metadata" in str(row.get("current_read") or "")
                and "rejects malformed or timezone-naive current-evidence generated_at provenance" in str(row.get("current_read") or "")
                and "missing operator_read_gate provenance" in str(row.get("current_read") or "")
                and "incomplete source_freshness reference provenance" in str(row.get("current_read") or "")
                and "missing refresh_action_boundary provenance" in str(row.get("current_read") or "")
                and "incomplete refresh_action_boundary command/read/Boolean evidence flags" in str(row.get("current_read") or "")
                and "weakened wrapper-refresh accounting" in str(row.get("current_read") or "")
                and "missing rebuild_validation_contract provenance" in str(row.get("current_read") or "")
                and "rejects weakened rebuild_validation_contract provenance before writing frozen-replay artifacts" in str(row.get("current_read") or "")
                and isinstance(row.get("child_checks"), list)
                and {check.get("check") for check in row["child_checks"]} == {
                    "current_boundary_date_source_precedence",
                    "bad_current_evidence_generated_at_fails_fast",
                    "missing_current_evidence_operator_read_gate_fails_fast",
                    "missing_current_evidence_source_freshness_reference_fails_fast",
                    "missing_current_evidence_refresh_action_boundary_fails_fast",
                    "missing_current_evidence_refresh_action_boundary_field_fails_fast",
                    "false_current_evidence_refresh_accounting_fails_fast",
                    "missing_current_evidence_rebuild_validation_contract_fails_fast",
                    "weakened_current_evidence_rebuild_validation_contract_fails_fast",
                    "top_boundary_labels_historical_replay",
                    "frozen_replay_valid_evidence_scope_visible",
                    "tiny_current_paper_sample_not_live_or_real_money_evidence_boundary",
                    "phase7_over_phase8_holdout_posture_visible",
                    "current_rule_roles_visible",
                    "baq_not_bel_boundary_visible",
                    "why_this_matters_keeps_walkforward_and_settlement_gap",
                    "interpretation_replaces_overstrong_pnl_language",
                    "next_loop_requires_settled_paper_before_real_money",
                    "self_recheck_command_documented",
                    "generator_preserves_current_boundary",
                    "source_fingerprints_visible_in_report",
                    "metadata_sidecar_publishes_machine_readable_evidence_boundary",
                    "metadata_sidecar_matches_sources_and_boundary",
                }
                for row in payload_map["frozen_evidence_chain"]["rows"]
            ),
            "project_layer_can_see_frozen_portfolio_eval_boundary_guardrail_inside_frozen_rows",
            "the project-level sweep can now verify that the frozen-evidence row inventory still exposes the frozen-portfolio replay caution validator's twenty-three structured checks, including the raw valid_evidence_scope contract, boundary-date source precedence, malformed current-evidence generated_at fail-fast coverage, missing source-freshness reference fail-fast coverage, missing refresh-action boundary, missing refresh-action no-real-money flag, weakened refresh-accounting fail-fast coverage, missing/weakened rebuild-validation-contract fail-fast coverage, historical-replay labeling, no-live/no-real-money boundaries, Phase 7-over-Phase 8 posture, BAQ-not-BEL separation, current top-card operator-status/source-freshness routing, current bridge rebuild routing, generator-preserved boundary wording, source-fingerprint metadata-sidecar parity, and the metadata sidecar's machine-readable evidence-boundary contract, instead of only seeing the frozen-evidence umbrella summary string",
        ),
        require(
            isinstance(payload_map["frozen_evidence_chain"].get("rows"), list)
            and any(
                row.get("name") == "frozen_decision_stack"
                and row.get("check_count") == 18
                and row.get("child_check_count") == 13
                and "Anchor=OP_DURABLE_K7 KEEP AS ANCHOR" in str(row.get("current_read") or "")
                and "Phase7=PAPER NOW (+38.68%) over Phase8=SHADOW ONLY (+21.45%)" in str(row.get("current_read") or "")
                and "Harville BENCHMARK ONLY and XGBoost RESEARCH ONLY" in str(row.get("current_read") or "")
                and "benchmark context rather than a live override" in str(row.get("current_read") or "")
                and "inherited scorecard ranking contract keeps rank tier-first and raw Score non-promotional" in str(row.get("current_read") or "")
                and "scorecard audit route=SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json via python3 validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization metadata only" in str(row.get("current_read") or "")
                and "current_evidence_summary.json rebuild_validation_contract routes source-byte changes through python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py before quoting CURRENT_EVIDENCE_SUMMARY.* as provenance/rebuild metadata only" in str(row.get("current_read") or "")
                and "saved scorecard JSON/CSV and all four direct decision-card CSV artifacts stay pinned to fresh builder output" in str(row.get("current_read") or "")
                and isinstance(row.get("child_checks"), list)
                and {check.get("check") for check in row["child_checks"]} == {
                    "artifact_rebuilds_cover_scorecard_and_decision_cards",
                    "scorecard_keeps_anchor_paper_watch_roles",
                    "scorecard_ranking_contract_inherited",
                    "scorecard_audit_route_inherited",
                    "current_evidence_rebuild_validation_contract_inherited",
                    "missing_current_evidence_rebuild_contract_fails_before_frozen_stack_artifacts",
                    "weakened_current_evidence_rebuild_contract_fails_before_frozen_stack_artifacts",
                    "phase7_keeps_holdout_edge_and_matches_frozen_eval",
                    "portfolio_and_method_cards_keep_roles",
                    "selector_and_switch_stay_benchmark_only",
                    "method_family_scope_guardrail_stays_explicit",
                    "current_paper_rules_keep_op_cd_without_baq_alias",
                    "shadow_watchlist_keeps_bel_dormant_and_refined_switch_watch",
                }
                for row in payload_map["frozen_evidence_chain"]["rows"]
            ),
            "project_layer_can_see_frozen_decision_stack_role_guardrail_inside_frozen_rows",
            "the project-level sweep can now verify that the frozen-evidence row inventory still exposes the frozen-decision-stack validator's thirteen structured checks and eighteen direct checks, including inherited scorecard ranking-contract semantics, current-evidence scorecard-audit route visibility, current-evidence rebuild-order visibility, missing/weakened rebuild-contract no-artifact fixtures, Phase 7-over-Phase 8 posture, OP/CD paper-basket roles, selector/train-switch benchmark-only treatment, Harville benchmark-only treatment, XGBoost research-only treatment, no BAQ-as-BEL substitution, and scorecard plus decision-card artifact rebuild parity, instead of only seeing the frozen-evidence umbrella summary string",
        ),
        require(
            isinstance(payload_map["frozen_evidence_chain"].get("rows"), list)
            and any(
                row.get("name") == "decision_cards_suite"
                and row.get("check_count") == 174
                and row.get("child_check_count") == 11
                and "OP-family card stays locked to the frozen 2024-2025 holdout standard" in str(row.get("current_read") or "")
                and "scorecard CI-only diagnostic inherited from forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7 keeps ci_only_promotion_allowed=false" in str(row.get("current_read") or "")
                and "current operator boundary inherited from compare-main JSON names stale-card refresh route=./run_daily_portfolio_observation.sh" in str(row.get("current_read") or "")
                and "bridge-published gate progress from current_evidence_summary.json.decision_gate_progress" in str(row.get("current_read") or "")
                and "operator read gate inherited from compare-main says" in str(row.get("current_read") or "")
                and "gate_status=" in str(row.get("current_read") or "")
                and (
                    "gate_status=refresh_required_before_evidence_read" in str(row.get("current_read") or "")
                    or "gate_status=current_operator_routing_context_only" in str(row.get("current_read") or "")
                )
                and "current settled rule mix OP_DURABLE_K7=0 / CD_CORE_K8=" in str(row.get("current_read") or "")
                and "with CD-only context=True" in str(row.get("current_read") or "")
                and "copied current-operator generated_at=" in str(row.get("current_read") or "")
                and "stays parseable timezone-aware provenance metadata only" in str(row.get("current_read") or "")
                and "cross-family promotion readiness" in str(row.get("current_read") or "")
                and "scorecard decision gates inherited directly from forward_evidence_scorecard.json decision_gate_minimums" in str(row.get("current_read") or "")
                and "current_evidence_summary.json.scorecard_audit_route points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py as report-synchronization metadata only" in str(row.get("current_read") or "")
                and "current_evidence_summary.json.rebuild_validation_contract routes source-byte changes through python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py before quoting CURRENT_EVIDENCE_SUMMARY.* as provenance/rebuild metadata only" in str(row.get("current_read") or "")
                and "not OP-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in str(row.get("current_read") or "")
                and "Anchor=OP_DURABLE_K7, paper companion=CD_CORE_K8, closest same-family shadow=OP_REFINED_K7" in str(row.get("current_read") or "")
                and "cross-family card stays pinned to the frozen 2024-2025 holdout standard" in str(row.get("current_read") or "")
                and "method-family card stays pinned to the frozen 2024-2025 holdout standard" in str(row.get("current_read") or "")
                and "scorecard CI-only diagnostic inherited from forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7 keeps ci_only_promotion_allowed=false so positive OP_REFINED CI support stays out of portfolio-level Phase 8 default readiness" in str(row.get("current_read") or "")
                and "current operator rule-mix boundary keeps OP_DURABLE_K7=0 and CD_CORE_K8=" in str(row.get("current_read") or "")
                and "as CD-only current settled context" in str(row.get("current_read") or "")
                and "stale-card refresh boundary says run `./run_daily_portfolio_observation.sh` before using stale right-now instructions" in str(row.get("current_read") or "")
                and "clean-empty-forward-performance=False" in str(row.get("current_read") or "")
                and "structured freshness provenance bridge reference=" in str(row.get("current_read") or "")
                and "(America/New_York), comparison=generated_reference_date /" in str(row.get("current_read") or "")
                and "decision gates inherited from compare-main JSON decision_change_gate_minimums" in str(row.get("current_read") or "")
                and "decision gates loaded directly from scorecard JSON decision_gate_minimums" in str(row.get("current_read") or "")
                and "scorecard CI-only diagnostic inherited from forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7 keeps ci_only_promotion_allowed=false so positive OP_REFINED CI support stays out of method-family promotion readiness" in str(row.get("current_read") or "")
                and "benchmark only=harville_ranked (-24.05% broad ROI on 90004 races)" in str(row.get("current_read") or "")
                and "research only=xgboost_residual (-24.16% best ML betting ROI despite +4.24% payout-RMSE improvement" in str(row.get("current_read") or "")
                and "copied current-operator generated_at=" in str(row.get("current_read") or "")
                and "stays parseable timezone-aware provenance metadata only" in str(row.get("current_read") or "")
                and "scorecard ranking contract inherited=tier-first, raw Score non-promotional" in str(row.get("current_read") or "")
                and "project-local CLI scratch-root reporting stays pinned" in str(row.get("current_read") or "")
                and "decision-card layer=report-facing frozen evidence ordering, not new forward proof" in str(row.get("current_read") or "")
                and "changes in real confidence still require settled paper trades" in str(row.get("current_read") or "")
                and isinstance(row.get("child_checks"), list)
                and {check.get("check") for check in row["child_checks"]} == {
                    "op_family_keeps_anchor_and_watch_bar",
                    "cross_family_keeps_anchor_paper_watch_order",
                    "op_cross_family_scratch_metadata_published",
                    "portfolio_method_scratch_metadata_published",
                    "portfolio_card_keeps_phase7_over_phase8_and_selector",
                    "method_family_keeps_selective_over_harville_and_xgboost",
                    "scorecard_ranking_contract_inherited",
                    "child_decision_validators_publish_explicit_status_counts_and_reads",
                    "core_decision_source_validators_publish_explicit_suite_status_and_totals",
                    "child_decision_validators_publish_structured_checks",
                    "decision_cards_are_frozen_ordering_not_new_evidence",
                }
                for row in payload_map["frozen_evidence_chain"]["rows"]
            ),
            "project_layer_can_see_decision_cards_suite_ordering_guardrail_inside_frozen_rows",
            "the project-level sweep can now verify that the frozen-evidence row inventory still exposes the decision-card suite's one hundred seventy-four direct checks and eleven structured guardrails, including OP-family anchor/watch roles plus project-local scratch-root hygiene, top-level scratch metadata, the current operator-boundary routing/CD-only OP-settlement gap, bridge-published current gate progress, inherited operator_read_gate publication, OP-family current-evidence rebuild-order fail-fast/documented coverage plus broader current-evidence rebuild-order routing through settlement-audit -> current-bridge -> bridge-validator, timezone-aware generated_at provenance, malformed generated_at fail-fast coverage, false refresh-boundary no-real-money-flag fail-fast coverage, OP-family scorecard-sourced CI-only OP_REFINED diagnostic visibility, OP-family and cross-family scorecard-sourced paper-observation gate visibility, OP-family, cross-family, portfolio, and method-family scorecard-audit routing visibility, cross-family scorecard-sourced CI-only OP_REFINED diagnostic visibility, cross-family anchor/paper/shadow order plus current paper-workflow boundary, timezone-aware copied current-operator generated_at provenance, cross-family malformed generated_at and false refresh-boundary no-real-money-flag fail-fast coverage, project-local scratch-root hygiene, and top-level scratch metadata, explicit OP/cross-family plus portfolio/method child scratch metadata, inherited scorecard ranking-contract semantics, Phase 7-over-Phase 8 portfolio posture plus current operator-boundary routing context, portfolio scorecard-sourced CI-only OP_REFINED diagnostic visibility, portfolio current-evidence rebuild-order fail-fast/documented coverage, portfolio scorecard-audit route visibility, the CD-only current settled rule-mix boundary, stale-card wrapper-refresh boundary, portfolio clean-empty refresh-accounting coverage, portfolio timezone-aware copied current-operator generated_at provenance, structured freshness provenance, malformed generated_at fail-fast coverage, missing freshness-reference fail-fast coverage, portfolio false refresh-boundary no-real-money-flag fail-fast coverage, portfolio scorecard-sourced decision-gate visibility plus project-local scratch hygiene and top-level scratch metadata, selective-rule-vs-Harville-vs-XGBoost method-family ordering plus current operator-boundary routing context, method-family current-evidence rebuild-order fail-fast/documented coverage, method-family timezone-aware copied current-operator generated_at provenance, structured freshness provenance, malformed generated_at fail-fast coverage, missing freshness-reference fail-fast coverage, method-family false refresh-boundary no-real-money-flag fail-fast coverage, method-family direct scorecard-gate fail-fast coverage, method-family scorecard-audit route fail-fast coverage, method-family scorecard-sourced decision-gate visibility, method-family scorecard-sourced CI-only OP_REFINED diagnostic visibility, project-local scratch hygiene and top-level scratch metadata, explicit child-validator status/count metadata, and the no-new-forward-proof boundary requiring settled paper trades before confidence changes, instead of only seeing the frozen-evidence umbrella summary string",
        ),
        require(
            isinstance(payload_map["frozen_evidence_chain"].get("rows"), list)
            and any(
                row.get("name") == "op_anchor_method_comparison"
                and row.get("child_check_count") == 45
                and row.get("child_scratch", {}).get("tmp_parent_is_project_local") is True
                and row.get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
                and "paper-basket context table now keeps OP_DURABLE_K7, CD_CORE_K8, and OP_REFINED_K7 in separate anchor / companion / shadow lanes before the broader Harville/XGBoost comparison" in str(row.get("current_read") or "")
                and "scorecard ranking-contract inheritance now pins tier-first rank semantics, forward_trust secondary-within-tier semantics, and raw-score non-deployment semantics so raw OP_REFINED_K7 score does not become an automatic promotion cue" in str(row.get("current_read") or "")
                and "anchor-review policy now reads forward_evidence_scorecard.json decision_gate_minimums directly and separates the 20-row Phase 8 promotion-review threshold from the stricter 30-row OP anchor-displacement discussion threshold plus the 100-row real-money discussion floor" in str(row.get("current_read") or "")
                and "current paper snapshot now carries the combined operator_status_context/source_freshness/operator_read_gate route plus current_evidence_summary.json source freshness, refresh routing, operator_read_gate" in str(row.get("current_read") or "")
                and "scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization metadata only" in str(row.get("current_read") or "")
                and "rebuild_validation_contract order ['python3 paper_trade_settlement_audit.py', 'python3 current_evidence_summary.py', 'python3 validate_current_evidence_summary.py']" in str(row.get("current_read") or "")
                and "settlement-audit -> current-bridge -> bridge-validator provenance before current totals are quoted" in str(row.get("current_read") or "")
                and "primary ROI-complete rows, 0 OP_DURABLE_K7 settled rows" in str(row.get("current_read") or "")
                and "CD_CORE_K8 settled rows" in str(row.get("current_read") or "")
                and "settlement queue state=closed with" in str(row.get("current_read") or "")
                and "open rows as operator context rather than OP-anchor proof" in str(row.get("current_read") or "")
                and "copied current-evidence generated_at=" in str(row.get("current_read") or "")
                and "stays parseable timezone-aware provenance metadata only before the OP-anchor comparison republishes current-paper context" in str(row.get("current_read") or "")
                and "source-freshness bridge reference=" in str(row.get("current_read") or "")
                and "(America/New_York) and comparison=generated_reference_date:" in str(row.get("current_read") or "")
                and "are printed as operator-readiness provenance" in str(row.get("current_read") or "")
                and "refresh-accounting fields stay fail-closed with wrapper-can-settle-rows=False, wrapper-counts-as-ROI-evidence=False, clean-empty-forward-performance=False" in str(row.get("current_read") or "")
                and "missing operator_read_gate, missing/weakened rebuild_validation_contract, missing source_freshness, missing source_freshness reference fields, missing refresh-action boundary, missing-or-false refresh-action non-evidence flags, and weakened clean-empty refresh-accounting flags are fixture-tested as no-output-directory/no-artifact CLI paths before current-paper bridge republishing" in str(row.get("current_read") or "")
                and "stale Phase 7 live-portfolio labels are removed from the OP-anchor markdown/JSON surfaces" in str(row.get("current_read") or "")
                and "scorecard CSV/JSON / compare-main / method-family / cross-family / downstream A/B / current-evidence input bytes" in str(row.get("current_read") or "")
                and "markdown source-provenance table matching the JSON source_fingerprints map" in str(row.get("current_read") or "")
                and "OP-anchor comparison and current-paper snapshot are posture/reproducibility or operator-routing metadata only" in str(row.get("current_read") or "")
                and "saved JSON, saved markdown, source provenance, boundary text, and real CLI stdout stay pinned to the same OP-anchor comparison render" in str(row.get("current_read") or "")
                and isinstance(row.get("child_checks"), list)
                and {check.get("check") for check in row["child_checks"]} == {
                    "json_matches_rebuild",
                    "markdown_matches_rebuild",
                    "cli_json_matches_rebuild",
                    "cli_markdown_matches_rebuild",
                    "cli_stdout_matches_generated_report",
                    "cli_custom_source_inputs_and_output_paths",
                    "cli_scratch_root_project_local",
                    "cli_scratch_metadata_published",
                    "source_byte_drift_updates_provenance_only",
                    "missing_scorecard_row_fails_fast",
                    "bad_forward_trust_ranking_contract_fails_fast",
                    "missing_scorecard_gate_minimum_fails_fast",
                    "missing_primary_shadow_fails_fast",
                    "missing_ab_delta_path_fails_fast",
                    "bad_current_evidence_generated_at_fails_fast",
                    "missing_current_evidence_operator_read_gate_fails_fast",
                    "missing_current_evidence_rebuild_validation_contract_fails_fast",
                    "weakened_current_evidence_rebuild_validation_contract_fails_fast",
                    "missing_current_evidence_source_freshness_fails_fast",
                    "missing_current_evidence_source_freshness_reference_fails_fast",
                    "missing_current_evidence_refresh_action_boundary_fails_fast",
                    "missing_current_evidence_refresh_action_boundary_field_fails_fast",
                    "false_current_evidence_refresh_action_boundary_flag_fails_fast",
                    "false_current_evidence_clean_empty_refresh_accounting_fails_fast",
                    "source_provenance_json_present",
                    "source_provenance_markdown_matches_json",
                    "scorecard_ranking_contract_inherited",
                    "stale_live_portfolio_label_removed",
                    "op_anchor_method_comparison_json_publishes_machine_readable_evidence_boundary",
                    "op_anchor_method_comparison_json_publishes_evidence_boundary_text",
                    "current_operator_boundary_preserves_cd_only_op_gap",
                    "current_operator_boundary_publishes_scorecard_audit_route",
                    "current_operator_boundary_publishes_rebuild_validation_contract",
                    "current_operator_boundary_generated_at_is_timezone_aware",
                    "anchor_review_policy_separates_promotion_from_displacement",
                    "guardrail_roles",
                    "op_anchor_numbers",
                    "harville_stays_negative_benchmark",
                    "xgboost_stays_research_only",
                    "anchor_context_stable",
                    "current_paper_companion_order",
                    "paper_basket_context_table_structured",
                    "current_read_guardrail",
                    "markdown_source_provenance_present",
                    "markdown_sections_present",
                }
                for row in payload_map["frozen_evidence_chain"]["rows"]
            ),
            "project_layer_can_see_op_anchor_source_provenance_guardrail_inside_frozen_rows",
            "the project-level sweep can now verify that the frozen-evidence row inventory still exposes the OP-anchor comparison validator's forty-five structured checks, including custom source/input/output-path coverage, project-local CLI scratch-root coverage plus child_scratch metadata, the structured OP/CD paper-basket plus OP-refined shadow context table, current-paper CD-only operator-boundary snapshot with source-derived settlement-queue state/context plus operator_read_gate, scorecard_audit_route, and rebuild_validation_contract routing, timezone-aware current-evidence generated_at provenance plus missing operator_read_gate, missing/weakened rebuild_validation_contract, missing source_freshness, missing source_freshness reference-field, missing refresh-action boundary, missing-or-false refresh-action non-evidence-flag fail-fast coverage, clean-empty refresh-accounting fail-fast coverage, inherited scorecard ranking-contract semantics with forward_trust secondary-within-tier fail-fast coverage, scorecard decision_gate_minimums fail-fast coverage, stale live-portfolio label removal, source-byte provenance drift handling, markdown/JSON source-provenance parity, the machine-readable evidence boundary plus readable boundary-text parity, and the scorecard-derived anchor-review policy split, instead of only seeing the frozen-evidence umbrella summary string",
        ),
        require(
            isinstance(payload_map["frozen_evidence_chain"].get("rows"), list)
            and any(
                row.get("name") == "ab_downstream_comparison"
                and row.get("child_check_count") == 35
                and row.get("child_scratch", {}).get("tmp_parent_is_project_local") is True
                and row.get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
                and "enriched horse-history XGBoost path remains research-only" in str(row.get("current_read") or "")
                and "cross-family hierarchy source fingerprinting, and custom hierarchy rerendering stay pinned" in str(row.get("current_read") or "")
                and "project-local CLI scratch-root reporting stays pinned" in str(row.get("current_read") or "")
                and "model artifact fingerprints match current disk bytes" in str(row.get("current_read") or "")
                and "current paper snapshot says " in str(row.get("current_read") or "")
                and "wrapper refresh route=./run_daily_portfolio_observation.sh" in str(row.get("current_read") or "")
                and "required_before_right_now_use=" in str(row.get("current_read") or "")
                and "requires the combined operator_status_context/source_freshness/operator_read_gate route before quoting current PAPER_TRADE_NOW instructions from this A/B artifact" in str(row.get("current_read") or "")
                and "operator_read_gate=" in str(row.get("current_read") or "")
                and " via " in str(row.get("current_read") or "")
                and "primary rows are " in str(row.get("current_read") or "")
                and "OP_DURABLE_K7 has 0 ROI-complete row(s), CD_CORE_K8 has" in str(row.get("current_read") or "")
                and "settlement queue state=closed with" in str(row.get("current_read") or "")
                and "open row(s) as operator context rather than OP-anchor proof" in str(row.get("current_read") or "")
                and "scorecard audit route from current_evidence_summary.json.scorecard_audit_route points to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks" in str(row.get("current_read") or "")
                and "rebuild_validation_contract order from current_evidence_summary.json routes source-byte changes through python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py before quoting current totals as provenance metadata only" in str(row.get("current_read") or "")
                and "copied current-evidence generated_at=" in str(row.get("current_read") or "")
                and "stays parseable timezone-aware provenance metadata only before the downstream A/B comparison republishes current-paper context" in str(row.get("current_read") or "")
                and "source-freshness bridge reference=" in str(row.get("current_read") or "")
                and "(America/New_York) and comparison=generated_reference_date:" in str(row.get("current_read") or "")
                and "are printed as operator-readiness provenance" in str(row.get("current_read") or "")
                and "missing operator_read_gate, missing/weakened rebuild_validation_contract, missing source_freshness, missing source_freshness reference fields, missing refresh-action boundary, missing-or-false refresh-action non-evidence flags, and weakened refresh-accounting flags are fixture-tested as no-output-directory/no-artifact CLI paths before current-paper bridge republishing" in str(row.get("current_read") or "")
                and "full CLI JSON/markdown/stdout plus custom CLI source/output-path checks are explicitly skipped because raw rebuild inputs are missing" in str(row.get("current_read") or "")
                and isinstance(row.get("child_checks"), list)
                and {check.get("check") for check in row["child_checks"]} == {
                    "markdown_matches_rebuild",
                    "cli_json_matches_saved",
                    "cli_markdown_matches_saved",
                    "cli_stdout_matches_generated_report",
                    "refresh_current_evidence_only_cli_updates_snapshot",
                    "test_set_shape",
                    "prediction_metrics_improve",
                    "ev_pass_counts_stay_small_and_not_better",
                    "payout_rmse_read_is_stable",
                    "disagreement_buckets_stable",
                    "markdown_guardrail",
                    "evidence_boundary_combined_operator_route_pinned",
                    "current_operator_boundary_preserves_cd_only_op_gap",
                    "current_operator_boundary_publishes_scorecard_audit_route",
                    "current_operator_boundary_publishes_rebuild_validation_contract",
                    "current_operator_boundary_generated_at_is_timezone_aware",
                    "bad_current_evidence_generated_at_fails_fast",
                    "missing_current_evidence_operator_read_gate_fails_fast",
                    "missing_current_evidence_rebuild_validation_contract_fails_fast",
                    "weakened_current_evidence_rebuild_validation_contract_fails_fast",
                    "missing_current_evidence_source_freshness_fails_fast",
                    "missing_current_evidence_source_freshness_reference_fails_fast",
                    "missing_current_evidence_refresh_action_boundary_fails_fast",
                    "missing_current_evidence_refresh_action_boundary_field_fails_fast",
                    "false_current_evidence_refresh_action_boundary_flag_fails_fast",
                    "false_current_evidence_clean_empty_refresh_accounting_fails_fast",
                    "selective_paper_companion_read_is_explicit",
                    "cross_family_hierarchy_source_fingerprint_present",
                    "cross_family_hierarchy_source_matches_disk",
                    "model_source_fingerprints_match_disk",
                    "custom_cross_family_hierarchy_renders_dynamically",
                    "cli_custom_cross_family_and_output_paths",
                    "cli_scratch_root_project_local",
                    "cli_scratch_metadata_published",
                    "limitation_is_explicit",
                }
                for row in payload_map["frozen_evidence_chain"]["rows"]
            ),
            "project_layer_can_see_downstream_ab_xgboost_research_only_guardrail_inside_frozen_rows",
            "the project-level sweep can now verify that the frozen-evidence row inventory still exposes the downstream A/B validator's thirty-five structured checks, including the refresh-current-evidence-only CLI path, current-paper CD-only operator-boundary snapshot plus combined operator route, operator_read_gate, scorecard_audit_route, and rebuild_validation_contract, timezone-aware current-evidence generated_at provenance plus malformed-timestamp, missing operator_read_gate, missing/weakened rebuild_validation_contract, missing source_freshness, missing source_freshness reference-field, missing refresh-action boundary, missing-or-false refresh-action non-evidence-flag fail-fast coverage, clean-empty refresh-accounting fail-fast coverage, machine-readable evidence-boundary routing, research-only XGBoost read, EV-pass-count non-improvement guardrail, cross-family source fingerprint, current-disk hierarchy/model fingerprint parity, custom hierarchy rerender, project-local CLI scratch-root coverage plus child_scratch metadata, and explicit custom CLI source/output-path skip state when raw rebuild inputs are absent, instead of only seeing the frozen-evidence umbrella summary string",
        ),
        require(
            isinstance(payload_map["frozen_evidence_chain"].get("rows"), list)
            and any(
                row.get("name") == "compare_recommender_scope_paths"
                and row.get("child_check_count") == 26
                and row.get("child_scratch", {}).get("tmp_parent_is_project_local") is True
                and row.get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
                and "selective Phase 7 filter as the honest current paper default" in str(row.get("current_read") or "")
                and "allow-all-combos preserved as an explicit research-only counterfactual" in str(row.get("current_read") or "")
                and "evidence_boundary.not_current_paper_scope_change_evidence=true" in str(row.get("current_read") or "")
                and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in str(row.get("current_read") or "")
                and "current_evidence_summary.json scorecard_audit_route is republished so copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py as synchronization metadata only" in str(row.get("current_read") or "")
                and "current_evidence_summary.json rebuild_validation_contract is republished so source-byte changes route through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py before quoting current totals from this counterfactual surface" in str(row.get("current_read") or "")
                and "missing scorecard gate failure is fixture-tested as a no-output-directory/no-artifact CLI path" in str(row.get("current_read") or "")
                and "malformed boolean/non-positive scorecard gate floors plus a missing no-BAQ-as-BEL prerequisite" in str(row.get("current_read") or "")
                and "including non-positive Phase 8 and real-money scorecard floors" in str(row.get("current_read") or "")
                and "missing or weakened current-evidence rebuild contracts are fixture-tested as no-output-directory/no-artifact CLI paths" in str(row.get("current_read") or "")
                and "dynamic cross-family hierarchy rerendering" in str(row.get("current_read") or "")
                and "project-local CLI scratch-root reporting" in str(row.get("current_read") or "")
                and "markdown/JSON/disk source provenance stay pinned to the same scope-comparison render" in str(row.get("current_read") or "")
                and isinstance(row.get("child_checks"), list)
                and {check.get("check") for check in row["child_checks"]} == {
                    "json_matches_rebuild",
                    "markdown_matches_rebuild",
                    "cli_json_matches_rebuild",
                    "cli_markdown_matches_rebuild",
                    "cli_stdout_matches_generated_report",
                    "custom_cross_family_hierarchy_renders_dynamically",
                    "missing_scorecard_gate_block_fails_fast_without_artifacts",
                    "missing_scorecard_gate_fails_fast_without_artifacts",
                    "malformed_scorecard_gate_floor_fails_fast_without_artifacts",
                    "non_positive_scorecard_gate_floor_fails_fast_without_artifacts",
                    "non_positive_real_money_scorecard_gate_floor_fails_fast_without_artifacts",
                    "missing_no_baq_prerequisite_fails_fast_without_artifacts",
                    "scenario_count",
                    "mixed_default_vs_widened",
                    "off_universe_only_default_vs_widened",
                    "paper_companion_order_in_json",
                    "scorecard_decision_gate_minimums_published",
                    "scorecard_audit_route_published",
                    "current_evidence_rebuild_validation_contract_published",
                    "missing_current_evidence_rebuild_contract_fails_fast_without_artifacts",
                    "weakened_current_evidence_rebuild_contract_fails_fast_without_artifacts",
                    "scope_evidence_boundary_published",
                    "markdown_guardrail",
                    "cli_scratch_root_project_local",
                    "cli_scratch_metadata_published",
                    "source_provenance_markdown_matches_json_and_disk",
                }
                for row in payload_map["frozen_evidence_chain"]["rows"]
            ),
            "project_layer_can_see_recommender_scope_live_default_guardrail_inside_frozen_rows",
            "the project-level sweep can now verify that the frozen-evidence row inventory still exposes the recommender-scope validator's twenty-six structured checks, including the selective Phase 7 current-paper guardrail, allow-all-combos research-only counterfactual, machine-readable scope evidence boundary, scorecard-sourced 30/20/100 gate read plus no-BAQ-as-BEL prerequisite, scorecard-audit route publication, current-evidence rebuild-contract publication, missing gate-block / missing-threshold / malformed boolean and non-positive Phase 8 plus real-money gate-floor / missing no-BAQ prerequisite / missing-or-weakened rebuild-contract no-write fixtures, mixed/off-universe scenarios, dynamic hierarchy rerender, real CLI parity, project-local CLI scratch-root coverage plus child_scratch metadata, and markdown/JSON/disk source-provenance parity, instead of only seeing the frozen-evidence umbrella summary string",
        ),
        require(
            isinstance(payload_map["frozen_evidence_chain"].get("rows"), list)
            and any(
                row.get("name") == "compare_main_approaches"
                and row.get("child_check_count") == 65
                and "scorecard ranking-contract inheritance keeps deployment posture tier-first so OP_REFINED_K7's hotter raw score cannot become an automatic promotion cue" in str(row.get("current_read") or "")
                and "custom method-family source paths rerender hierarchy labels and provenance without changing ranked rows" in str(row.get("current_read") or "")
                and "project-local CLI scratch-root metadata stays published for comparison rerenders" in str(row.get("current_read") or "")
                and "machine-readable decision-gate minimums keep anchor_displacement=30 same-candidate rows, phase8_promotion_review=20 shadow rows, and real_money_discussion=100 total settled rows named separately" in str(row.get("current_read") or "")
                and "API/403 sidecar action/recheck route when present, source-freshness reference date/timezone/comparison-source fields" in str(row.get("current_read") or "")
                and "current operator-boundary snapshot carries the combined operator_status_context/source_freshness/operator_read_gate route" in str(row.get("current_read") or "")
                and "wrapper-refresh non-evidence boundary, scorecard-audit route, and rebuild-validation contract from current_evidence_summary.json as routing metadata only" in str(row.get("current_read") or "")
                and "those named anchor_displacement=30, phase8_promotion_review=20, and real_money_discussion=100 thresholds are source-matched against forward_evidence_scorecard.json and now loaded directly from its decision_gate_minimums with fail-fast missing-threshold, non-positive Phase 8 / real-money floor, and missing no-BAQ prerequisite coverage plus changed-threshold fixture coverage" in str(row.get("current_read") or "")
                and isinstance(row.get("child_checks"), list)
                and {check.get("check") for check in row["child_checks"]} == {
                    "markdown_matches_rebuild",
                    "json_sidecar_surface",
                    "method_family_evidence_debt_json_present",
                    "current_operator_boundary_publishes_reference_date_fields",
                    "current_operator_boundary_generated_at_is_timezone_aware",
                    "current_operator_boundary_preserves_api_failure_action_route",
                    "current_operator_boundary_publishes_refresh_action_boundary",
                    "current_operator_boundary_publishes_scorecard_audit_route",
                    "current_operator_boundary_publishes_rebuild_validation_contract",
                    "compare_main_approaches_json_publishes_machine_readable_evidence_boundary",
                    "decision_gate_minimums_json_present",
                    "decision_gate_minimums_match_scorecard_json",
                    "changed_scorecard_gate_minimums_rerender_from_source",
                    "nonpositive_phase8_scorecard_gate_minimum_fails_fast",
                    "nonpositive_real_money_scorecard_gate_minimum_fails_fast",
                    "bad_current_evidence_generated_at_fails_fast",
                    "missing_current_evidence_rebuild_validation_contract_fails_fast",
                    "weakened_current_evidence_rebuild_validation_contract_fails_fast",
                    "missing_current_evidence_source_freshness_fails_fast",
                    "missing_current_evidence_operator_read_gate_fails_fast",
                    "missing_current_evidence_refresh_action_boundary_field_fails_fast",
                    "false_current_evidence_refresh_accounting_fails_fast",
                    "missing_scorecard_gate_minimum_fails_fast",
                    "scorecard_ranking_contract_inherited",
                    "custom_method_family_source_paths_rerender_dynamically",
                    "source_byte_drift_updates_provenance_only",
                    "phase7_matches_frozen_holdout",
                    "phase8_matches_frozen_holdout",
                    "op_durable_matches_rule_holdout",
                    "op_refined_matches_rule_holdout",
                    "selector_matches_walk_forward_folds",
                    "op_holdout_switch_choices",
                    "op_switch_equals_refined_on_holdout",
                    "phase7_holdout_year_split",
                    "phase8_holdout_year_split",
                    "op_holdout_year_split",
                    "selector_holdout_year_split",
                    "comparison_top_order",
                    "secondary_basis_split",
                    "deployment_posture_map",
                    "op_anchor_has_larger_sample",
                    "op_score_vs_posture_guardrail",
                    "source_provenance_section_present",
                    "source_provenance_markdown_matches_json",
                    "one_screen_read_present",
                    "method_family_action_summary_present",
                    "method_family_evidence_debt_present",
                    "holdout_split_section_present",
                    "frozen_holdout_window_rejection",
                    "current_rule_ladder_present",
                    "comparison_consumes_scorecard_deployment_fields",
                    "shadow_watch_triage_present",
                    "method_family_guardrail_present",
                    "decision_change_gates_present",
                    "narrow_follow_up_section",
                    "op_follow_up_entry",
                    "ab_follow_up_entry",
                    "scope_follow_up_entry",
                    "cli_stdout_surface",
                    "cli_pinned_rerender",
                    "cli_scratch_root_project_local",
                    "cli_scratch_metadata_published",
                    "missing_scorecard_row_fails_fast",
                    "missing_op_switch_candidate_fails_fast",
                    "missing_scorecard_no_baq_prerequisite_fails_fast",
                }
                for row in payload_map["frozen_evidence_chain"]["rows"]
            ),
            "project_layer_can_see_compare_main_custom_source_guardrail_inside_frozen_rows",
            "the project-level sweep can now verify that the frozen-evidence row inventory still exposes the compare-main validator's sixty-five structured checks, including the machine-readable method-family evidence-debt checklist, current-evidence reference-date/timezone source-freshness guardrail, timezone-aware copied current-evidence generated_at provenance plus malformed-timestamp, current-evidence scorecard-audit route propagation, current-evidence rebuild-validation contract propagation, missing and weakened rebuild-validation-contract fail-fast coverage, missing-source-freshness, operator_read_gate republishing plus fail-fast coverage, API/403 sidecar action/recheck route preservation, missing refresh-action non-evidence-flag fail-fast coverage, and weakened refresh-accounting fail-fast coverage, wrapper-refresh non-evidence boundary, custom method-family source-path rerender guardrail, project-local CLI scratch-root guardrail plus top-level scratch metadata, inherited scorecard ranking-contract semantics, markdown/JSON source-provenance parity, and scorecard-sourced machine-readable decision-gate minimums with missing-threshold, non-positive Phase 8 / real-money floor, and missing no-BAQ prerequisite fail-fast plus changed-threshold rerender coverage, instead of only seeing the frozen-evidence umbrella summary string",
        ),
        require(
            "full routed recommendation-lane quick-reads bundle" in row_map["paper_trade_operator_suite"]["current_read"]
            and "open primary settlement/recommendation-state context preserved as workflow routing rather than bet-ready or forward-performance posture" in row_map["paper_trade_operator_suite"]["current_read"]
            and "routed preflight-note source path" in row_map["paper_trade_operator_suite"]["current_read"]
            and "direct primary/shadow pipeline/scanner status-sidecar pointers" in row_map["paper_trade_operator_suite"]["current_read"]
            and "stale default scanner filename" in row_map["paper_trade_operator_suite"]["current_read"]
            and "live scanner pre-detail targeting now spends race-detail attempts on rule-card/race-min candidates before --max-races is applied" in row_map["paper_trade_operator_suite"]["current_read"]
            and "does not alias BAQ as BEL" in row_map["paper_trade_operator_suite"]["current_read"]
            and "unattempted target-candidate count" in row_map["paper_trade_operator_suite"]["current_read"]
            and "max-races-limited no-hit reads as operationally limited coverage rather than clean empty forward observations" in row_map["paper_trade_operator_suite"]["current_read"]
            and "pipeline stage / type / detail preserved" in row_map["paper_trade_operator_suite"]["current_read"]
            and "partial cache with activity" in row_map["paper_trade_operator_suite"]["current_read"]
            and "structured `observation_scope` / `observation_reason`" in row_map["paper_trade_operator_suite"]["current_read"]
            and "`operator_read_gate_issue_flags` fields" in row_map["paper_trade_operator_suite"]["current_read"]
            and "every JSON summary carrying `valid_evidence_scope`, an `evidence_boundary`, and `evidence_boundary_metadata`" in row_map["paper_trade_operator_suite"]["current_read"]
            and "limited coverage, API-access failures, stale-cache fallback, or broken-sidecar classifications as live profitability, promotion, anchor movement, scope movement, BAQ/BEL substitution, or real-money proof" in row_map["paper_trade_operator_suite"]["current_read"]
            and "structured observation-scope/reason fields so partial-cache runs with surviving activity do not get mislabeled as limited-cache empty days" in row_map["paper_trade_operator_suite"]["current_read"]
            and "OP_DURABLE_K7 / CD_CORE_K8 / OP_REFINED_K7 live lane hierarchy block" in row_map["paper_trade_operator_suite"]["current_read"]
            and "dual primary/shadow lane-context lines" in row_map["paper_trade_operator_suite"]["current_read"]
            and "dual primary/shadow lane-why lines" in row_map["paper_trade_operator_suite"]["current_read"]
            and "explicit stale-snapshot note so inherited preflight note/artifact, excluded-track aliases, lane context, counts, ops streaks, and quick reads do not masquerade as current state" in row_map["paper_trade_operator_suite"]["current_read"]
            and "broader selective-family secondary lines stay replay context on walk-forward test years rather than extra train-only validation" in row_map["paper_trade_operator_suite"]["current_read"]
            and "explicit routed right-now focus/timing/freshness/stale-snapshot/ops snapshot" in row_map["paper_trade_operator_suite"]["current_read"]
            and "inheriting refreshed top-level routed top-card snapshot lines" in row_map["paper_trade_operator_suite"]["current_read"]
            and "explicit primary/shadow next-step source artifact paths and state lines plus lifted no-overpromotion decision-gate snapshot lines" in row_map["paper_trade_operator_suite"]["current_read"]
            and "shadow settlement-audit per-rule promotion gate plus per-rule coverage line" in row_map["paper_trade_operator_suite"]["current_read"]
            and "ROI-complete settled-evidence boundary visible" in row_map["paper_trade_operator_suite"]["current_read"]
            and "source rendered daily summaries and the direct validator report now publish exact `valid_evidence_scope=daily_operator_workflow_navigation_only` lines plus source-level boundary text" in row_map["paper_trade_operator_suite"]["current_read"]
            and "first-read and broader-review readiness lines" in row_map["paper_trade_operator_suite"]["current_read"]
            and "settled-row ROI-gap-reason lines" in row_map["paper_trade_operator_suite"]["current_read"]
            and "both lane recent-run context plus why-now lines when the saved next-steps artifacts provide them" in row_map["paper_trade_operator_suite"]["current_read"]
            and "without implying live promotion" in row_map["paper_trade_operator_suite"]["current_read"]
            and "both active-target and no-target days" in row_map["paper_trade_operator_suite"]["current_read"]
            and "frozen-baseline comparison surface, not standalone profit proof by itself" in row_map["paper_trade_operator_suite"]["current_read"]
            and "operator action-routing surface, not new forward edge evidence by itself" in row_map["paper_trade_operator_suite"]["current_read"]
            and "including when saved live next-steps surfaces are rebuilt for drift checks" in row_map["paper_trade_operator_suite"]["current_read"]
            and "calendar/context classification surface, not new forward evidence by itself" in row_map["paper_trade_operator_suite"]["current_read"]
            and "structured preflight excluded-track alias visibility" in row_map["paper_trade_operator_suite"]["current_read"]
            and "compact forward-observation surface, not new forward evidence by itself" in row_map["paper_trade_operator_suite"]["current_read"]
            and "rolling operational recap surface, not new forward evidence by itself" in row_map["paper_trade_operator_suite"]["current_read"]
            and "ledger-sync/reproducibility surface, not new forward evidence by itself" in row_map["paper_trade_operator_suite"]["current_read"]
            and "ledger-maintenance surface, not new forward evidence by itself" in row_map["paper_trade_operator_suite"]["current_read"]
            and "ledger-completeness / ROI-coverage audit rather than new forward evidence by itself" in row_map["paper_trade_operator_suite"]["current_read"]
            and "primary anchor_displacement first-read gate separately from the shadow/watch phase8_promotion_review per-rule gate" in row_map["paper_trade_operator_suite"]["current_read"]
            and "shadow audit table shows 0/20 instead of primary-style 0/30" in row_map["paper_trade_operator_suite"]["current_read"]
            and "OP_REFINED_K7 plus other Phase 8 pockets cannot be promoted from aggregate shadow counts" in row_map["paper_trade_operator_suite"]["current_read"]
            and "rejects scorecard gate values that fall below the conservative historical floors" in row_map["paper_trade_operator_suite"]["current_read"]
            and "treats boolean gate floors as malformed instead of int-coercible source-matched values" in row_map["paper_trade_operator_suite"]["current_read"]
            and "saved source-layer renders and direct validator report paths stay pinned across the routed operator surfaces" in row_map["paper_trade_operator_suite"]["current_read"]
            and "compact source-chain matrix report stays available as the source-matched scan -> recommend -> size -> log audit route" in row_map["paper_trade_operator_suite"]["current_read"]
            and "source-of-truth wrapper reports whose inherited wrapper-guardrail inventories broader operator/project sweeps should preserve rather than flatten" in row_map["paper_trade_operator_suite"]["current_read"]
            and "machine-readable evidence_boundary metadata in the operator-suite JSON keeps operator validator passes, clean empty/no-target/cache runs, wrapper alignment, and source-chain matrix propagation separate from settled ROI" in row_map["paper_trade_operator_suite"]["current_read"],
            "operator_layer_keeps_routed_navigation_and_failure_context",
            "operator rollup still keeps the routed top-card navigation bundle, the routed preflight-note source path, structured preflight excluded-track alias visibility, direct primary/shadow status-sidecar pointers with stale-default scanner masking protection, explicit partial-cache-with-activity separation plus structured observation-scope/reason fields, operator read-gate issue flags, and machine-readable status-summary evidence-boundary metadata fields in the operator layer, explicit stale-cache fallback metadata in the API-access status branch, explicit lane hierarchy, preserved primary/shadow recent-run context plus per-lane why lines, the routed daily-summary top-card focus/timing/freshness/stale-snapshot/ops snapshot with refreshed-top-level snapshot inheritance on rebuilt daily summaries, the replay-context caution on broader selective-family secondary lines, split-aware daily-summary next-step-source/state plus no-overpromotion decision-gate visibility, daily-summary shadow per-rule promotion-gate visibility, ROI-complete settled-evidence boundary visibility, daily-summary source-level valid-scope/boundary text, and settled-row ROI-gap-reason visibility, the no-live-promotion guardrail, stage/type/detail failure context, refreshed PAPER_TRADE_NOW context/why preservation, wrapper-fallback context/why preservation, the settlement-audit primary anchor_displacement versus shadow phase8_promotion_review gate split, the operator-side saved-render plus validator-path reproducibility read including saved-live next-steps drift rebuild recovery, plus the preflight, lane-monitor, ops-history, settlement-sync, settlement-helper, settlement-audit, forward-check, and next-steps evidence boundaries",
        ),
        require(
            payload_map["paper_trade_operator_suite"].get("suite_status") == "pass"
            and payload_map["paper_trade_operator_suite"].get("total_checks") == 63
            and row_map["paper_trade_operator_suite"].get("child_total_checks") == 63
            and row_map["paper_trade_operator_suite"].get("child_check_count") == 63
            and operator_rows_publish_child_check_components(payload_map["paper_trade_operator_suite"])
            and isinstance(payload_map["paper_trade_operator_suite"].get("operator_markdown_component_render_contract"), dict)
            and payload_map["paper_trade_operator_suite"]["operator_markdown_component_render_contract"].get("hashes_are_reproducibility_metadata_only") is True
            and "not forward evidence" in payload_map["paper_trade_operator_suite"]["operator_markdown_component_render_contract"].get("evidence_boundary", "")
            and isinstance(payload_map["paper_trade_operator_suite"].get("evidence_boundary"), dict)
            and payload_map["paper_trade_operator_suite"]["evidence_boundary"].get("artifact_role") == "paper-trade operator-suite validator rollup"
            and payload_map["paper_trade_operator_suite"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["paper_trade_operator_suite"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_operator_suite"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["paper_trade_operator_suite"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and "do not use clean empty/no-target/cache runs as profitability evidence" in payload_map["paper_trade_operator_suite"]["evidence_boundary"].get("non_goals", [])
            and isinstance(payload_map["paper_trade_operator_suite"].get("current_evidence_bridge_json_read"), dict)
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "source_consistency_overall_match"
            )
            is True
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "primary_roi_complete_rows_match"
            )
            is True
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "primary_open_rows_match"
            )
            is True
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "primary_incomplete_rows_match"
            )
            is True
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "primary_roi_gap_rows_match"
            )
            is True
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "source_freshness_state_valid"
            )
            is True
            and isinstance(
                payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                    "requires_refresh_before_right_now_use"
                ),
                bool,
            )
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "decision_gate_source"
            )
            == "forward_evidence_scorecard.json"
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "decision_gate_source_loaded"
            )
            is True
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "decision_gate_source_values_match_scorecard"
            )
            is True
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "decision_gate_effective_values_source"
            )
            == "forward_evidence_scorecard.json:decision_gate_minimums"
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "decision_gate_missing_top_card_fields"
            )
            == []
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "decision_gate_mismatched_fields"
            )
            == []
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "effective_anchor_displacement_min"
            )
            == 30
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "effective_phase8_promotion_review_min"
            )
            == 20
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "effective_real_money_discussion_min"
            )
            == 100
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "decision_gate_threshold_sources", {}
            ).get("anchor_displacement")
            == "forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations"
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "decision_gate_threshold_sources", {}
            ).get("phase8_promotion_review")
            == "forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations"
            and payload_map["paper_trade_operator_suite"]["current_evidence_bridge_json_read"].get(
                "decision_gate_threshold_sources", {}
            ).get("real_money_discussion")
            == "forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi"
            and isinstance(row_map["paper_trade_operator_suite"].get("child_checks"), list)
            and {check.get("check") for check in row_map["paper_trade_operator_suite"]["child_checks"]} == {
                "status_summary_keeps_stage_type_detail_guardrail",
                "status_summary_publishes_structured_rollup_checks",
                "operator_rows_preserve_status_summary_structured_guardrails",
                "live_scan_targeting_limit_status_publishes_operator_guardrail",
                "scanner_sidecar_resolution_contract_publishes_operator_guardrail",
                "preflight_note_keeps_calendar_context_evidence_boundary",
                "preflight_note_publishes_structured_rollup_checks",
                "operator_rows_preserve_preflight_note_structured_guardrails",
                "settlement_sync_keeps_ledger_sync_evidence_boundary",
                "settlement_sync_publishes_structured_rollup_checks",
                "operator_rows_preserve_settlement_sync_structured_guardrails",
                "settlement_helper_keeps_ledger_maintenance_evidence_boundary",
                "settlement_helper_publishes_structured_rollup_checks",
                "operator_rows_preserve_settlement_helper_structured_guardrails",
                "settlement_audit_keeps_ledger_completeness_evidence_boundary",
                "settlement_audit_publishes_structured_rollup_checks",
                "operator_rows_preserve_settlement_audit_structured_guardrails",
                "settlement_audit_fails_closed_on_lowered_scorecard_gates",
                "settlement_audit_fails_closed_on_boolean_scorecard_gates",
                "right_now_keeps_navigation_lane_hierarchy_and_split_fallback",
                "operator_rows_preserve_right_now_structured_guardrails",
                "daily_summary_keeps_routed_bundle_failure_context_and_split_fallback",
                "operator_rows_preserve_daily_summary_structured_guardrails",
                "lane_summary_keeps_routed_files_stage_context_and_decision_gate",
                "operator_rows_preserve_lane_summary_structured_guardrails",
                "forward_check_keeps_frozen_baseline_evidence_boundary",
                "forward_check_publishes_structured_rollup_checks",
                "operator_rows_preserve_forward_check_structured_guardrails",
                "lane_monitor_keeps_compact_observation_evidence_boundary",
                "lane_monitor_publishes_structured_rollup_checks",
                "operator_rows_preserve_lane_monitor_structured_guardrails",
                "ops_history_keeps_operational_recap_evidence_boundary",
                "ops_history_publishes_structured_rollup_checks",
                "operator_rows_preserve_ops_history_structured_guardrails",
                "next_steps_keeps_action_routing_evidence_boundary",
                "operator_rows_preserve_next_steps_structured_guardrails",
                "refresh_helper_keeps_saved_live_navigation_scope",
                "refresh_helper_publishes_structured_rollup_checks",
                "operator_rows_preserve_refresh_helper_structured_guardrails",
                "daily_wrapper_keeps_cross_surface_fallback_contract",
                "daily_wrapper_publishes_structured_rollup_checks",
                "operator_rows_preserve_daily_wrapper_structured_guardrails",
                "wrapper_leaf_source_of_truth_note_visible_in_operator_suite",
                "cache_edge_rollups_keep_failure_mode_separation_and_json_fallback",
                "cache_only_messaging_publishes_structured_rollup_checks",
                "operator_rows_preserve_cache_only_structured_guardrails",
                "partial_cache_messaging_publishes_structured_rollup_checks",
                "operator_rows_preserve_partial_cache_structured_guardrails",
                "operator_suite_current_evidence_effective_gates_are_scorecard_backed",
                "operator_state_and_cache_edge_validators_publish_explicit_suite_status_totals_and_counts",
                "operator_wrapper_validators_publish_explicit_suite_status_totals_and_counts",
                "direct_operator_leaf_validators_publish_explicit_suite_status_totals_and_counts",
                "operator_observation_validators_publish_explicit_suite_status_totals_and_counts",
                "operator_reporting_validators_publish_explicit_suite_status_totals_and_counts",
                "operator_rows_publish_child_check_component_breakdowns",
                "operator_rows_publish_complete_metadata_contract",
                "operator_markdown_child_check_components_render_safe_formulas",
                "operator_markdown_table_contains_safe_component_render_snippets",
                "auxiliary_source_validators_publish_explicit_suite_status_totals_and_reads",
                "auxiliary_source_results_embed_pipeline_recommender_ev_and_logger_guardrail_inventories",
                "auxiliary_source_chain_matrix_preserves_compact_audit_contract",
                "operator_suite_explicitly_stays_readiness_not_new_evidence",
                "operator_suite_json_publishes_machine_readable_evidence_boundary",
            },
            "operator_layer_publishes_structured_rollup_checks",
            "operator rollup now has to publish explicit top-level suite_status, explicit total_checks, its machine-readable child_check_components row inventory, and its sixty-three explicit structured guardrails, including the child check-component breakdown contract, complete row metadata contract with full child check inventories when leaf validators publish them, safe markdown component-summary rendering, self-published markdown table render contract, machine-readable operator-suite evidence-boundary contract, and parent-level current-evidence bridge effective gate provenance, the base-status plus live-scan targeting / max-races limit-status plus scanner-sidecar path-resolution plus preflight-note, settlement-sync, settlement-helper, settlement-audit lowered/boolean-gate fail-closed protection, cache-only, and partial-cache structured-guardrail sets, the propagated status-summary, live-scan targeting, scanner-sidecar resolution, preflight-note, settlement-sync, settlement-helper, settlement-audit, right-now top-card, daily-summary, lane-summary, forward-check, lane-monitor, ops-history, next-steps, refresh-helper, daily-wrapper, cache-only, and partial-cache row-level guardrail inventories, the wrapper-leaf source-of-truth preservation note, the cache-edge, wrapper/helper, direct leaf, forward-check structured-guardrail, observation-cluster, lane-monitor plus ops-history structured-guardrail sets, reporting-cluster, auxiliary operator-source metadata contracts plus embedded source-layer result inventories for scan/recommend/size/log, the compact source-chain matrix audit contract, split-aware json-fallback operator checks, the preflight/lane-monitor/ops-history/settlement-sync/settlement-helper/settlement-audit/forward-check/next-steps/daily-summary/lane-summary evidence boundaries, and the no-new-evidence readiness caution, instead of only a summary string",
        ),
        require(
            operator_rows_publish_complete_metadata_contract(payload_map["paper_trade_operator_suite"]),
            "project_layer_can_see_operator_complete_row_metadata_contract",
            "the project-level sweep now independently verifies the operator-suite row inventory's complete metadata contract for every child validator: stable name/label/report paths, PASS status, non-empty current reads, matching child_check_components totals, complete child check inventories when published, and complete structured guardrail inventories, so the top-level project pass cannot inherit a partially flattened operator row set",
        ),
        require(
            all(snippet in operator_markdown for snippet in operator_markdown_component_render_contract["required_snippets"])
            and all(snippet not in operator_markdown for snippet in operator_markdown_component_render_contract["forbidden_snippets"]),
            "project_layer_can_see_operator_component_markdown_rendering",
            "the top-level project sweep now verifies the generated operator-suite markdown table itself, including the Check Components column, representative exact saved-live formulas, representative semicolon-only rows for totals with extra guardrail checks, and the absence of misleading fixture-equals-total formulas on those rows",
        ),
        require(
            isinstance(operator_markdown_component_render_contract.get("markdown_fingerprint"), dict)
            and operator_markdown_component_render_contract["markdown_fingerprint"].get("path")
            == operator_markdown_component_render_contract.get("path")
            and isinstance(operator_markdown_component_render_contract["markdown_fingerprint"].get("bytes"), int)
            and operator_markdown_component_render_contract["markdown_fingerprint"]["bytes"] > 0
            and isinstance(operator_markdown_component_render_contract["markdown_fingerprint"].get("sha256"), str)
            and len(operator_markdown_component_render_contract["markdown_fingerprint"]["sha256"]) == 64
            and all(char in "0123456789abcdef" for char in operator_markdown_component_render_contract["markdown_fingerprint"]["sha256"])
            and operator_markdown_component_render_contract.get("hashes_are_reproducibility_metadata_only") is True,
            "project_layer_publishes_operator_component_markdown_fingerprint",
            "the top-level project JSON now fingerprints the exact generated operator-suite markdown artifact whose component-render snippets it sampled, while labeling that hash as reproducibility metadata rather than performance, promotion, or live-profitability evidence",
        ),
        require(
            bool(operator_child_required_snippets)
            and all(isinstance(snippet, str) and snippet in operator_markdown for snippet in operator_child_required_snippets)
            and all(snippet in operator_markdown_component_render_contract["required_snippets"] for snippet in operator_child_required_snippets)
            and all(isinstance(snippet, str) and snippet not in operator_markdown for snippet in operator_child_forbidden_snippets)
            and all(snippet in operator_markdown_component_render_contract["forbidden_snippets"] for snippet in operator_child_forbidden_snippets)
            and operator_markdown_component_render_contract.get("child_required_snippet_count") == len(operator_child_required_snippets)
            and operator_markdown_component_render_contract.get("child_forbidden_snippet_count") == len(operator_child_forbidden_snippets)
            and operator_markdown_component_render_contract.get("child_contract_source_json")
            == row_map["paper_trade_operator_suite"].get("json_path"),
            "project_layer_syncs_operator_child_markdown_render_contract",
            "the top-level project sweep now proves the operator child JSON's self-published markdown render contract is the source it is sampling: every child required snippet is present in the sampled markdown and parent contract, every child forbidden snippet is absent from the sampled markdown and mirrored in the parent contract, and the child contract source path plus snippet counts are published for reproducibility only",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("auxiliary_source_results"), list)
            and {row.get("label") for row in payload_map["paper_trade_operator_suite"]["auxiliary_source_results"]} == {
                "paper_trade_pipeline",
                "paper_trade_recommender",
                "ev_ticket_engine",
                "paper_trade_logger",
            }
            and any(
                row.get("label") == "paper_trade_pipeline"
                and row.get("suite_status") == "pass"
                and row.get("total_fixture_scenarios") == 32
                and row.get("total_checks") == 32
                and row.get("check_count") == 32
                and row.get("child_guardrail_check_count") == 12
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_pipeline_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_pipeline_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_pipeline_artifacts",
                    "scorecard_missing_no_baq_fails_before_pipeline_artifacts",
                    "pipeline_status_matrix_stays_operationally_distinct",
                    "pipeline_status_publishes_workflow_only_evidence_boundary",
                    "scanner_status_sidecar_paths_and_states_stay_machine_readable",
                    "pipeline_errors_preserve_pre_error_context",
                    "pipeline_validator_stays_source_layer_not_new_evidence",
                    "direct_validation_report_exposes_pipeline_valid_scope",
                    "pipeline_preserves_scorecard_gate_boundary",
                    "fixture_scratch_metadata_published",
                }
                and row.get("valid_evidence_scope") == "scan_recommend_log_status_only"
                and isinstance(row.get("evidence_boundary"), dict)
                and row["evidence_boundary"].get("pipeline_validator_passes_are_workflow_metadata_only") is True
                and row["evidence_boundary"].get("baq_as_bel_substitution_allowed") is False
                and "stdout-visible source-level valid_evidence_scope plus evidence-boundary lines" in row.get("current_read", "")
                and "valid_evidence_scope=scan_recommend_log_status_only" in row.get("current_read", "")
                and "workflow sidecar or copied log as live profitability, promotion, or real-money evidence" in row.get("current_read", "")
                and "project-local fixture scratch metadata" in row.get("current_read", "")
                for row in payload_map["paper_trade_operator_suite"]["auxiliary_source_results"]
            )
            and any(
                row.get("label") == "paper_trade_recommender"
                and row.get("suite_status") == "pass"
                and row.get("total_fixture_scenarios") == 6
                and row.get("total_checks") == 6
                and row.get("check_count") == 6
                and row.get("child_guardrail_check_count") == 12
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_recommender_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_recommender_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_recommender_artifacts",
                    "scorecard_missing_no_baq_fails_before_recommender_artifacts",
                    "empty_scan_input_writes_stable_empty_artifacts",
                    "missing_race_id_hits_become_per_hit_error_rows",
                    "default_phase7_filter_stays_inside_scanner_combo_universe",
                    "off_universe_predictions_stay_no_bet_unless_override_is_explicit",
                    "malformed_prediction_files_become_per_race_error_rows",
                    "fixture_scratch_metadata_published",
                    "recommender_validator_stays_reuse_fixture_not_new_evidence",
                    "recommender_preserves_scorecard_gate_boundary",
                }
                and "source-level valid_evidence_scope plus evidence-boundary lines" in row.get("current_read", "")
                and "not live model scoring, promotion, settled ROI, live profitability, or real-money evidence" in row.get("current_read", "")
                and "rejects malformed and non-positive scorecard gates before fixture/report artifacts" in row.get("current_read", "")
                and "project-local fixture scratch metadata" in row.get("current_read", "")
                for row in payload_map["paper_trade_operator_suite"]["auxiliary_source_results"]
            )
            and any(
                row.get("label") == "ev_ticket_engine"
                and row.get("suite_status") == "pass"
                and row.get("total_fixture_scenarios") == 6
                and row.get("total_checks") == 6
                and row.get("check_count") == 6
                and row.get("child_guardrail_check_count") == 11
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_ev_ticket_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_ev_ticket_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_ev_ticket_artifacts",
                    "scorecard_missing_no_baq_fails_before_ev_ticket_artifacts",
                    "empty_negative_and_low_probability_inputs_stay_no_bet",
                    "risk_caps_and_ticket_increment_floor_stay_conservative",
                    "positive_ev_ticket_sizing_respects_rank_and_caps",
                    "malformed_probability_inputs_fail_loudly_without_plan_artifacts",
                    "fixture_scratch_metadata_published",
                    "ev_ticket_engine_validator_stays_sizing_reproducibility_not_new_evidence",
                    "ev_ticket_engine_preserves_scorecard_gate_boundary",
                }
                and "not live profitability, promotion, or real-money evidence" in row.get("current_read", "")
                and "source-level valid_evidence_scope plus evidence-boundary lines" in row.get("current_read", "")
                and "project-local fixture scratch metadata" in row.get("current_read", "")
                for row in payload_map["paper_trade_operator_suite"]["auxiliary_source_results"]
            )
            and any(
                row.get("label") == "paper_trade_logger"
                and row.get("suite_status") == "pass"
                and row.get("total_fixture_scenarios") == 4
                and row.get("total_checks") == 4
                and row.get("check_count") == 4
                and row.get("child_guardrail_check_count") == 11
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_logger_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_logger_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_logger_artifacts",
                    "scorecard_missing_no_baq_fails_before_logger_artifacts",
                    "empty_inputs_create_header_only_ledgers_and_empty_states",
                    "new_rows_append_serialized_payloads_with_open_status_fields",
                    "existing_state_dedups_old_keys_and_allows_new_keys",
                    "malformed_state_rebuilds_dedup_from_existing_ledgers_and_ignores_blank_recommendation_keys",
                    "fixture_scratch_metadata_published",
                    "paper_trade_logger_validator_stays_ledger_reproducibility_not_settlement_evidence",
                    "logger_preserves_scorecard_gate_boundary",
                }
                and "not settlement-complete ROI, promotion, live profitability, or real-money evidence" in row.get("current_read", "")
                and "project-local fixture scratch metadata" in row.get("current_read", "")
                for row in payload_map["paper_trade_operator_suite"]["auxiliary_source_results"]
            ),
            "project_layer_can_see_auxiliary_pipeline_recommender_ev_and_logger_source_guardrails",
            "the project-level sweep can now verify the operator suite's embedded auxiliary source-layer results, including the direct pipeline missing-output, invalid-shape scanner-status, stdout-visible source-level valid_evidence_scope output, direct validator-report valid_evidence_scope field and boundary, fixture scratch metadata, and scorecard-gate guardrails plus recommender and EV source-level valid_evidence_scope output, EV sizing, and logger fixture scratch metadata, and logger workflow/selective-recommendation/stake-sizing/ledger guardrails and the pipeline/recommender/EV-sizing/logger scorecard-gate boundaries, instead of only trusting the operator umbrella's auxiliary dependency prose",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("auxiliary_source_chain_matrix"), dict)
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("label") == "paper_trade_source_chain_guardrails"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("suite_status") == "pass"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("valid_evidence_scope") == "source_chain_operational_readiness_guardrail_only"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("total_checks") == 26
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("check_count") == 26
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("source_matrix_md") == "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("source_matrix_json") == "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("source_matrix_fingerprints", {}).get("markdown", {}).get("path") == "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("source_matrix_fingerprints", {}).get("json", {}).get("path") == "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("source_matrix_fingerprints_match_disk") is True
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_fingerprints", {}).get("markdown") == payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("source_matrix_fingerprints", {}).get("markdown")
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_fingerprints", {}).get("json") == payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("source_matrix_fingerprints", {}).get("json")
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("source_matrix_payload_matches_parent_rebuild") is True
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("valid_evidence_scope") == "source_chain_operational_readiness_guardrail_only"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("total_layers") == 4
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("total_fixture_scenarios") == 48
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("total_source_validator_checks") == 48
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("total_guardrail_checks") == 46
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("decision_gate_minimums", {}).get("source_path") == "forward_evidence_scorecard.json"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("decision_gate_minimums", {}).get("anchor_displacement_min") == 30
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("decision_gate_minimums", {}).get("phase8_promotion_review_min") == 20
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("decision_gate_minimums", {}).get("real_money_discussion_min") == 100
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("decision_gate_minimums", {}).get("real_money_no_baq_as_bel_required") is True
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("current_evidence_rebuild_validation_contract", {}).get("source") == "current_evidence_summary.json"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("current_evidence_rebuild_validation_contract", {}).get("source_path") == "rebuild_validation_contract"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("current_evidence_rebuild_validation_contract", {}).get("upstream_refresh_commands") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("current_evidence_rebuild_validation_contract", {}).get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("current_evidence_rebuild_validation_contract", {}).get("upstream_refresh_order_is_provenance_metadata_only") is True
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("current_evidence_rebuild_validation_contract", {}).get("not_settled_roi_or_real_money_evidence") is True
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("evidence_boundary_metadata", {}).get("artifact_role") == "paper-trade source-chain guardrail matrix"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("evidence_boundary_metadata", {}).get("valid_evidence_scope") == "source_chain_operational_readiness_guardrail_only"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("evidence_boundary_metadata", {}).get("current_evidence_rebuild_contract_source") == "current_evidence_summary.json"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("evidence_boundary_metadata", {}).get("current_evidence_rebuild_contract_source_path") == "rebuild_validation_contract"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("evidence_boundary_metadata", {}).get("current_evidence_rebuild_contract_is_provenance_metadata_only") is True
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("evidence_boundary_metadata", {}).get("not_paper_scope_change_evidence") is True
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("evidence_boundary_metadata", {}).get("not_odds_only_xgboost_reopening_evidence") is True
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("evidence_boundary_metadata", {}).get("baq_as_bel_substitution_allowed") is False
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("evidence_boundary_metadata", {}).get("artifact_role") == "paper-trade source-chain guardrail matrix"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("evidence_boundary_metadata", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("evidence_boundary_metadata", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("evidence_boundary_metadata", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("evidence_boundary_metadata", {}).get("current_evidence_rebuild_contract_source") == "current_evidence_summary.json"
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("evidence_boundary_metadata", {}).get("baq_as_bel_substitution_allowed") is False
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("matrix_tooling_fingerprints", {}).get("generator") == fingerprint_file(BASE / "paper_trade_source_chain_guardrails.py")
            and payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_source_matrix_rebuild", {}).get("matrix_tooling_fingerprints", {}).get("validator") == fingerprint_file(BASE / "validate_paper_trade_source_chain_guardrails.py")
            and isinstance(payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("checks"), list)
            and {check.get("check") for check in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"]["checks"]} == {
                "saved_json_matches_fresh_source_chain_rebuild",
                "matrix_totals_pin_complete_scan_recommend_size_log_chain",
                "matrix_preserves_layer_order_status_and_direct_check_counts",
                "matrix_preserves_all_source_guardrail_inventories",
                "matrix_pins_scan_reuse_coverage_contract_without_fixture_count_growth",
                "matrix_fingerprints_exact_validator_json_inputs",
                "matrix_fingerprints_exact_source_and_validator_scripts",
                "matrix_fingerprints_exact_generator_and_validator_tooling",
                "matrix_keeps_no_new_forward_evidence_boundary",
                "matrix_publishes_machine_readable_evidence_boundary_metadata",
                "matrix_exposes_source_chain_valid_evidence_scope",
                "matrix_preserves_current_hierarchy_boundary",
                "matrix_preserves_scorecard_decision_gate_minimums",
                "matrix_preserves_current_evidence_rebuild_validation_contract",
                "markdown_report_is_human_readable_and_provenance_aware",
                "markdown_fingerprint_tables_match_json_payload",
                "validation_report_fingerprints_validated_matrix_artifacts",
                "matrix_documents_parent_rollup_propagation_boundary",
                "custom_output_scratch_root_project_local",
                "custom_output_scratch_metadata_published",
                "custom_output_rebuild_matches_saved_payload_except_output_paths",
                "scorecard_boolean_gate_floor_fails_before_matrix_artifacts",
                "scorecard_nonpositive_phase8_gate_floor_fails_before_matrix_artifacts",
                "scorecard_nonpositive_real_money_gate_floor_fails_before_matrix_artifacts",
                "missing_current_evidence_rebuild_contract_fails_before_matrix_artifacts",
                "weakened_current_evidence_rebuild_contract_fails_before_matrix_artifacts",
            }
            and "source-matched" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "all 46 scan/recommend/size/log guardrails" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "source/validator scripts" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "matrix generator/validator tooling" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "renders markdown fingerprint tables exactly from the JSON sidecar" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "fingerprints the validated matrix markdown/JSON artifacts" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "parent rollup propagation" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "parent-side matrix-payload rebuild parity" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "project-local validation root with published scratch metadata" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "`auxiliary_source_chain_matrix`" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "current hierarchy boundary" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "OP_DURABLE_K7 / CD_CORE_K8 / OP_REFINED_K7 plus BAQ-not-BEL" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL real-money prerequisite" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "current_evidence_summary.json rebuild_validation_contract before current totals are quoted" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "non-positive Phase 8 / real-money scorecard gate floors" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "missing/weakened current-evidence rebuild contracts as no-artifact failures" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "machine-readable evidence_boundary_metadata plus exact raw `valid_evidence_scope=source_chain_operational_readiness_guardrail_only`" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", "")
            and "non-promotional / non-profitability evidence" in payload_map["paper_trade_operator_suite"]["auxiliary_source_chain_matrix"].get("current_read", ""),
            "project_layer_can_see_operator_source_chain_matrix_audit_contract",
            "the project-level sweep can now verify the operator suite's embedded compact source-chain matrix result, including the saved PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS markdown/JSON paths, twenty-six matrix checks, the exact source-chain valid_evidence_scope, all-46-guardrails read, scan-reuse coverage stop rule, scorecard-sourced 30/20/100 gate payload with no-BAQ-as-BEL prerequisite, current-evidence rebuild-validation contract, machine-readable evidence-boundary metadata, boolean gate-floor, non-positive Phase 8 / real-money gate-floor, and missing/weakened-rebuild-contract no-artifact fixtures, validator-JSON, code, matrix-tooling, markdown/JSON fingerprint-table parity checks, current hierarchy boundary, validated matrix-artifact fingerprints that still match disk, custom-output scratch-root metadata, published custom-output scratch metadata, parent-side fresh matrix-payload rebuild parity, parent-propagation guidance, and non-promotional/non-profitability boundary",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "paper_trade_status_summary"
                and row.get("child_total_checks") == 47
                and row.get("child_guardrail_check_count") == 16
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_status_summary_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_status_summary_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_status_summary_artifacts",
                    "scorecard_missing_no_baq_fails_before_status_summary_artifacts",
                    "fixture_state_matrix_stays_covered_across_text_json_and_failure_modes",
                    "api_access_scanner_failure_route_stays_explicit",
                    "api_access_stale_cache_fallback_route_stays_explicit",
                    "structured_partial_cache_and_observation_fields_stay_explicit",
                    "pipeline_failure_context_and_pre_error_counts_stay_honest",
                    "relocated_scanner_and_required_pipeline_sidecar_recovery_stay_explicit",
                    "saved_outputs_match_current_source_layer_and_status_summary_stays_base_state_only",
                    "fixture_scratch_metadata_published",
                    "status_summary_preserves_scorecard_gate_boundary",
                    "source_json_summaries_publish_machine_readable_evidence_boundary_metadata",
                    "direct_validation_report_exposes_status_summary_valid_scope",
                    "source_json_summaries_publish_operator_read_gate_issue_flags",
                }
                and "project-local fixture scratch metadata" in str(row.get("current_read") or "")
                and "evidence_boundary_metadata" in str(row.get("current_read") or "")
                and "valid_evidence_scope=workflow_state_triage_only" in str(row.get("current_read") or "")
                and "operator_read_gate_issue_flags" in str(row.get("current_read") or "")
                and "stale-cache fallback metadata" in str(row.get("current_read") or "")
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_status_summary_guardrail_inventory_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory still exposes the status-summary validator's explicit total-check metadata plus its sixteen structured guardrails, including malformed-scorecard and non-positive-gate no-artifact checks, API-access action/recheck routing, API-access stale-cache fallback metadata, operator read-gate issue flags, machine-readable status-summary evidence-boundary metadata fields, direct valid_evidence_scope visibility, stale-default scanner masking protection, invalid-shape sidecar visibility, source-pipeline-recorded scanner-status state preservation, missing-scan-output fallback visibility, project-local fixture scratch metadata, source JSON evidence_boundary_metadata, and scorecard-sourced gate-boundary visibility, instead of only seeing the operator umbrella summary string",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "live_scan_targeting_and_limit_status"
                and row.get("child_total_checks") == 18
                and row.get("child_check_count") == 18
                and row.get("child_guardrail_check_count") == 18
                and row.get("report_json") == "out/status_validation/live_scan_targeting_and_limit_status/live_scan_targeting_and_limit_status_validation.json"
                and "explicit BEL-vs-BAQ fixture" in str(row.get("current_read") or "")
                and "scanner API-access-failure" in str(row.get("current_read") or "")
                and "valid_evidence_scope lines and evidence boundaries" in str(row.get("current_read") or "")
                and "valid_evidence_scope=live_scan_targeting_limited_coverage_guardrail_only" in str(row.get("current_read") or "")
                and "unattempted target-candidate count" in str(row.get("current_read") or "")
                and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in str(row.get("current_read") or "")
                and "non-positive Phase 8 / real-money floors" in str(row.get("current_read") or "")
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_live_scan_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_live_scan_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_live_scan_artifacts",
                    "scorecard_missing_no_baq_fails_before_live_scan_artifacts",
                    "scanner_prefilter_spends_detail_attempts_only_on_rule_candidate_races",
                    "scanner_prefilter_does_not_alias_baq_as_bel",
                    "scanner_prefilter_accepts_true_belmont_without_baq_bridge",
                    "pipeline_max_race_limited_empty_is_not_clean_empty",
                    "pipeline_max_race_limited_activity_stays_limited",
                    "pipeline_clean_empty_still_available_without_limit_hit",
                    "scanner_publishes_target_coverage_gap_counts",
                    "scanner_text_and_empty_csv_outputs_publish_valid_scope",
                    "scanner_api_access_failure_or_fallback_sidecar_is_structured",
                    "pipeline_and_status_summary_preserve_api_access_failure_context",
                    "status_summary_surfaces_limit_hit_and_candidate_count",
                    "ops_history_buckets_limit_hit_as_active_limited_coverage",
                    "scorecard_gate_boundary_preserved_for_synthetic_live_scan_checks",
                    "direct_validation_report_exposes_live_scan_targeting_valid_scope",
                }
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_live_scan_targeting_limit_guardrail_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory exposes the live-scan targeting / max-races limit-status validator's eighteen scanner/pipeline/status/ops guardrails, including malformed-scorecard no-artifact failures for boolean anchor floors, non-positive Phase 8 / real-money floors, and missing no-BAQ prerequisites, the explicit BEL-vs-BAQ fixture, structured API-access-failure or stale-cache-fallback sidecar propagation, target-coverage-gap visibility, text/empty-CSV valid-scope output, direct validator valid_evidence_scope visibility, and scorecard-sourced 30/20/100 gate-boundary visibility, instead of letting capped no-hit scans or API-access fallback be flattened into a generic clean-empty operator read or paper-review evidence",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "scanner_sidecar_resolution_contract"
                and row.get("child_total_checks") == 16
                and row.get("child_check_count") == 16
                and row.get("child_guardrail_check_count") == 16
                and row.get("report_json") == "out/status_validation/scanner_sidecar_resolution_contract/scanner_sidecar_resolution_contract_validation.json"
                and "stale default live_scan.status.json" in str(row.get("current_read") or "")
                and "HTTP 403 operator action and recheck command" in str(row.get("current_read") or "")
                and "valid_evidence_scope=scanner_sidecar_path_resolution_contract_only" in str(row.get("current_read") or "")
                and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in str(row.get("current_read") or "")
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_scanner_sidecar_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_scanner_sidecar_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_scanner_sidecar_artifacts",
                    "scorecard_missing_no_baq_fails_before_scanner_sidecar_artifacts",
                    "status_summary_uses_declared_missing_sidecar_over_stale_default",
                    "next_steps_uses_declared_missing_sidecar_over_stale_default",
                    "right_now_pointer_uses_declared_missing_sidecar_over_stale_default",
                    "ops_history_uses_declared_missing_sidecar_over_stale_default",
                    "saved_live_refresh_uses_declared_missing_sidecar_over_stale_default",
                    "status_summary_cli_surfaces_recorded_missing_declared_sidecar",
                    "next_steps_artifact_issue_surfaces_recorded_missing_declared_sidecar",
                    "stale_default_file_cannot_mask_missing_declared_sidecar",
                    "api_access_declared_sidecar_beats_stale_clean_default",
                    "api_access_declared_sidecar_surfaces_action_fields",
                    "scanner_sidecar_resolution_preserves_scorecard_gate_boundary",
                    "direct_validation_report_exposes_scanner_sidecar_valid_scope",
                }
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_scanner_sidecar_valid_scope_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory exposes the scanner-sidecar path-resolution validator's sixteen structured guardrails, including stale-default masking, missing declared sidecar refresh guidance, API-access action/recheck preservation, direct valid_evidence_scope visibility, and scorecard-sourced 30/20/100 gate-boundary visibility, instead of flattening copied-sidecar routing fixtures into generic quiet-day or paper-review evidence",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "paper_trade_preflight_note"
                and row_has_saved_live_plus_top_level_artifact_component_total(row, 6, 6, 1)
                and row.get("child_guardrail_check_count") == 14
                and row.get("report_json") == "out/status_validation/paper_trade_preflight_note/paper_trade_preflight_note_validation.json"
                and "first-class `calendar_state` / `calendar_reason` classification" in str(row.get("current_read") or "")
                and "`valid_evidence_scope`, `evidence_boundary`, and `evidence_boundary_text`" in str(row.get("current_read") or "")
                and "calendar context cannot be overread as scanner evidence, settled ROI, promotion readiness, live profitability, real-money support, or BAQ-as-BEL evidence" in str(row.get("current_read") or "")
                and "exact valid_evidence_scope=paper_trade_preflight_calendar_context_only" in str(row.get("current_read") or "")
                and "cleared project-local validation scratch root" in str(row.get("current_read") or "")
                and "Belmont at the Big A cannot surface as BEL" in str(row.get("current_read") or "")
                and "dangerous Belmont Park at Big A/Aqueduct plus at-sign Big A labels stay excluded from BEL" in str(row.get("current_read") or "")
                and "rejects malformed and non-positive scorecard gates before fixture/report artifacts" in str(row.get("current_read") or "")
                and "standalone manual probe rather than a validated live surface" in str(row.get("current_read") or "")
                and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in str(row.get("current_read") or "")
                and "not new forward evidence by itself" in str(row.get("current_read") or "")
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_preflight_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_preflight_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_preflight_artifacts",
                    "scorecard_missing_no_baq_fails_before_preflight_artifacts",
                    "fixture_calendar_state_split_stays_covered",
                    "structured_calendar_classification_and_track_counts_stay_explicit",
                    "direct_validation_report_exposes_preflight_valid_scope",
                    "saved_fixture_and_live_surfaces_match_current_rebuilds",
                    "shadow_only_and_no_target_language_stays_honest",
                    "top_level_default_preflight_artifact_stays_inventoried_as_non_live_surface",
                    "preflight_note_explicitly_stays_calendar_context_not_new_evidence",
                    "preflight_note_preserves_scorecard_gate_boundary",
                    "fixture_scratch_root_project_local",
                    "fixture_scratch_metadata_published",
                }
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_preflight_note_calendar_context_guardrail_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory exposes the preflight-note validator's explicit fixture + saved-live + top-level scratch-artifact component total metadata plus its fourteen structured calendar/context guardrails, including malformed-scorecard and non-positive gate no-artifact checks, calendar_state/calendar_reason classification, source-level JSON evidence-boundary fields, direct valid_evidence_scope exposure, active/shadow/excluded track counts, BAQ-not-BEL alias protection, top-level scratch-artifact non-live labeling, saved-live rebuild parity, scorecard-sourced 30/20/100 gate-boundary visibility, project-local scratch hygiene plus top-level scratch metadata, and the no-new-forward-evidence boundary",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "paper_trade_settlement_sync"
                and row.get("child_total_checks") == 4
                and row.get("child_guardrail_check_count") == 12
                and "project-local fixture scratch metadata as a structured guardrail" in str(row.get("current_read") or "")
                and "rejects malformed and non-positive scorecard gates before fixture/report artifacts" in str(row.get("current_read") or "")
                and "skips blank and duplicate signal-key rows" in str(row.get("current_read") or "")
                and "drops blank settlement-key rows" in str(row.get("current_read") or "")
                and "drops stale orphan settlement rows" in str(row.get("current_read") or "")
                and "source-level valid_evidence_scope plus evidence-boundary lines" in str(row.get("current_read") or "")
                and "valid_evidence_scope=settlement_template_ledger_alignment_only" in str(row.get("current_read") or "")
                and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in str(row.get("current_read") or "")
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "empty_signal_ledgers_still_write_a_stable_header_only_template",
                    "new_live_signals_still_create_one_open_row_per_signal_with_expected_cost",
                    "manual_settlement_fields_still_survive_metadata_refreshes",
                    "blank_signal_and_settlement_keys_plus_orphan_rows_stay_separate",
                    "direct_report_path_and_ledger_sync_boundary_stay_explicit",
                    "direct_validation_report_exposes_settlement_sync_valid_scope",
                    "scorecard_boolean_gate_floor_fails_before_settlement_sync_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_settlement_sync_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_settlement_sync_artifacts",
                    "scorecard_missing_no_baq_fails_before_settlement_sync_artifacts",
                    "settlement_sync_preserves_scorecard_gate_boundary",
                    "fixture_scratch_metadata_published",
                }
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_settlement_sync_guardrail_inventory_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory still exposes the settlement-sync validator's explicit total-check metadata plus its twelve structured ledger-sync guardrails, including source-level and direct-report valid_evidence_scope output, project-local fixture scratch metadata, malformed-scorecard no-artifact checks, and scorecard-sourced 30/20/100 gate-boundary visibility, instead of only seeing the operator umbrella summary string",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "paper_trade_settlement_helper"
                and row.get("child_total_checks") == 17
                and row.get("child_check_count") == 17
                and row.get("child_guardrail_check_count") == 18
                and row.get("report_json") == "out/status_validation/paper_trade_settlement_helper/paper_trade_settlement_helper_validation.json"
                and "lists only open rows across text, markdown, and JSON outputs" in str(row.get("current_read") or "")
                and "separately surfacing settled HIT/MISS rows missing ROI-complete return/cost/timestamp coverage" in str(row.get("current_read") or "")
                and "renders row-specific settle command templates with actual result/payout evidence placeholders" in str(row.get("current_read") or "")
                and "updates exactly one row by signal_key" in str(row.get("current_read") or "")
                and "rejects duplicate signal_key matches before mutation" in str(row.get("current_read") or "")
                and "rejects placeholder or unsupported outcome tokens before mutating the ledger" in str(row.get("current_read") or "")
                and "rejects non-finite or negative actual-return inputs plus non-finite or non-positive actual-cost inputs before mutating the ledger" in str(row.get("current_read") or "")
                and "rejects placeholder, blank, or malformed settled-ts inputs before mutating the ledger when a timestamp is supplied" in str(row.get("current_read") or "")
                and "makes timestamp-omitted settlement confirmations say the row remains outside ROI-complete sample gates until settled_ts is filled" in str(row.get("current_read") or "")
                and "actual_cost_source" in str(row.get("current_read") or "")
                and "without adding cost-source columns to the persisted settlement ledger schema" in str(row.get("current_read") or "")
                and "source-level valid_evidence_scope / evidence_boundary / evidence_boundary_text" in str(row.get("current_read") or "")
                and "valid_evidence_scope=settlement_entry_queue_repair_metadata_only" in str(row.get("current_read") or "")
                and "project-local fixture scratch metadata" in str(row.get("current_read") or "")
                and "rejects malformed and non-positive scorecard gates before fixture/report artifacts" in str(row.get("current_read") or "")
                and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in str(row.get("current_read") or "")
                and "not new forward evidence by itself" in str(row.get("current_read") or "")
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_settlement_helper_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_settlement_helper_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_settlement_helper_artifacts",
                    "scorecard_missing_no_baq_fails_before_settlement_helper_artifacts",
                    "open_queue_rendering_stays_honest_across_formats",
                    "truncation_and_open_row_filtering_stay_explicit",
                    "single_row_settlement_updates_and_profit_math_stay_exact",
                    "expected_cost_fallback_and_missing_signal_paths_stay_honest",
                    "duplicate_signal_keys_fail_before_settlement_mutation",
                    "outcome_tokens_are_limited_to_actual_hit_or_miss_results",
                    "settlement_amounts_must_be_finite_and_nonnegative",
                    "settled_timestamps_must_be_actual_iso_values_when_supplied",
                    "fixture_renders_and_ledger_outputs_match_current_source_layer",
                    "direct_validation_report_exposes_settlement_helper_valid_scope",
                    "settlement_ledger_schema_stays_stable_while_confirmation_reports_cost_source",
                    "settle_help_documents_cost_source_and_expected_cost_boundary",
                    "settlement_helper_preserves_scorecard_gate_boundary",
                    "fixture_scratch_metadata_published",
                }
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_settlement_helper_guardrail_inventory_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory exposes the settlement-helper validator's explicit total-check metadata plus its eighteen structured ledger-maintenance guardrails, including malformed-scorecard no-artifact checks, honest open-queue rendering, settled-row ROI-gap visibility with non-positive actual-cost gaps, row-specific settlement command templates with evidence-first placeholders, exact one-row settlement updates, duplicate signal-key rejection before mutation, placeholder/unsupported outcome rejection before mutation, finite non-negative return validation plus positive actual-cost validation before mutation, supplied settled-timestamp validation before mutation, timestamp-omitted confirmation sample-gate warnings, actual-cost-source reporting, stable persisted ledger schema, source-level and direct-report valid_evidence_scope output, positive expected-cost fallback boundaries, missing-signal failures, project-local fixture scratch metadata, the scorecard-sourced 30/20/100 gate-boundary read, and the no-new-forward-evidence frame",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "paper_trade_settlement_audit"
                and row.get("child_total_checks") == 8
                and row.get("child_guardrail_check_count") == 18
                and "blank signal-key rows and blank settlement-key rows separately labeled in repair output" in str(row.get("current_read") or "")
                and "non-positive actual or expected-cost rows out of ROI-complete settled counts" in str(row.get("current_read") or "")
                and "publishes top-level valid_evidence_scope and evidence_boundary_text plus machine-readable evidence_boundary_metadata for ledger-completeness / ROI-coverage audit scope" in str(row.get("current_read") or "")
                and "exposes direct validator report valid_evidence_scope=paper_trade_settlement_quality_audit_only" in str(row.get("current_read") or "")
                and "validates timezone-aware ISO generated_at metadata for live/fixture audit outputs" in str(row.get("current_read") or "")
                and "rejects duplicate custom --lane names before writing audit markdown/json artifacts" in str(row.get("current_read") or "")
                and "treats boolean gate floors as malformed instead of int-coercible source-matched values" in str(row.get("current_read") or "")
                and "treats non-positive Phase 8 and real-money scorecard gate floors as malformed instead of source-matched values" in str(row.get("current_read") or "")
                and "treats a missing no-BAQ-as-BEL real-money prerequisite as malformed instead of source-matched" in str(row.get("current_read") or "")
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "empty_header_only_ledgers_stay_aligned_but_pre_evidence",
                    "structural_template_orphan_blank_and_duplicate_gaps_are_flagged",
                    "settled_row_roi_coverage_gap_reasons_stay_explicit",
                    "settled_ts_gaps_block_roi_complete_rows",
                    "non_positive_cost_gaps_block_roi_complete_rows",
                    "roi_complete_rows_feed_milestones_without_profit_claims",
                    "live_default_audit_keeps_two_lane_hierarchy_and_evidence_boundary",
                    "settlement_audit_publishes_machine_readable_evidence_boundary_metadata",
                    "direct_validation_report_exposes_settlement_audit_valid_scope",
                    "audit_generated_at_is_timezone_aware_metadata",
                    "shadow_watch_promotion_gate_is_per_rule_not_lane_total",
                    "open_settlement_queue_carries_operator_identity_without_performance_claims",
                    "settlement_audit_gates_are_sourced_from_scorecard_minimums",
                    "settlement_audit_boolean_gate_floor_is_malformed_not_source_matched",
                    "settlement_audit_nonpositive_gate_floors_are_malformed_not_source_matched",
                    "settlement_audit_missing_no_baq_requirement_is_malformed_not_source_matched",
                    "fixture_scratch_metadata_published",
                    "duplicate_custom_lane_names_fail_before_output_artifacts",
                }
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_settlement_audit_guardrail_inventory_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory exposes the settlement-audit validator's explicit total-check metadata plus its eighteen structured ledger-completeness / ROI-coverage guardrails, so separated blank signal-key / blank settlement-key repair labeling, structural repair state, ROI-gap reasons, missing/placeholder/malformed settled_ts repair before ROI-complete sample counting, non-positive cost repair before ROI-complete sample counting, milestone counting, machine-readable evidence_boundary_metadata, direct valid_evidence_scope exposure, timezone-aware generated_at metadata, the no-new-forward-evidence live two-lane audit boundary, the primary anchor_displacement versus shadow phase8_promotion_review gate split, open-row identity details, duplicate custom lane-name rejection before output artifacts, project-local fixture scratch metadata, scorecard-sourced 30 / 20 / 100 decision-gate minimums, malformed boolean plus non-positive Phase 8 / real-money gate-floor fallback coverage, and missing no-BAQ-as-BEL prerequisite fallback coverage do not disappear inside the operator umbrella summary",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "paper_trade_forward_check"
                and row_has_saved_live_component_total(row, 13, 10)
                and row.get("child_guardrail_check_count") == 14
                and row.get("report_json") == "out/status_validation/paper_trade_forward_check/paper_trade_forward_check_validation.json"
                and "source-matching the default 30 / 20 / 100 gate minimums" in str(row.get("current_read") or "")
                and "non-positive cost" in str(row.get("current_read") or "")
                and "real CLI malformed-scorecard artifact proving conservative fallback outputs stay labeled as explicit CLI/fallback values" in str(row.get("current_read") or "")
                and "Phase 8 shadow-lane first-read gate mapping" in str(row.get("current_read") or "")
                and "Phase 8 review-floor caution" in str(row.get("current_read") or "")
                and "legacy Phase 7 rules-file display label as a legacy rules lane rather than a live lane" in str(row.get("current_read") or "")
                and "project-local fixture scratch metadata" in str(row.get("current_read") or "")
                and "valid_evidence_scope=frozen-baseline comparison for ROI-complete paper observations" in str(row.get("current_read") or "")
                and "not standalone profit proof by itself" in str(row.get("current_read") or "")
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "fixture_state_ladder_and_recommendation_flow_stay_covered",
                    "saved_fixture_and_live_surfaces_match_current_rebuilds",
                    "zero_settled_and_partial_roi_coverage_gaps_stay_explicit",
                    "sample_progress_roi_fallback_and_missing_baseline_stay_pinned",
                    "roi_cost_source_and_malformed_actual_cost_gaps_stay_visible",
                    "non_positive_cost_rows_do_not_advance_roi_complete_sample_gates",
                    "decision_gate_prevents_first_read_overpromotion",
                    "forward_check_gates_are_sourced_from_scorecard_minimums",
                    "malformed_scorecard_cli_fallback_artifact_stays_conservative",
                    "phase8_review_floor_caution_stays_visible",
                    "direct_validation_report_exposes_forward_check_valid_scope",
                    "forward_check_explicitly_stays_baseline_comparison_not_profit_proof",
                    "legacy_phase7_rules_label_stays_paper_safe",
                    "fixture_scratch_metadata_published",
                }
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_forward_check_guardrail_inventory_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory exposes the forward-check validator's explicit fixture-plus-saved-live total-check metadata plus its fourteen structured frozen-baseline guardrails, including zero-settled and partial-ROI coverage visibility, cost-source / malformed-actual-cost / non-positive-cost settlement-quality gaps, scorecard-sourced 30 / 20 / 100 decision-gate minimums, real-CLI malformed-scorecard conservative fallback artifact coverage, Phase 8 shadow-lane first-read gate mapping, Phase 8 review-floor caution, paper-safe legacy Phase 7 display labeling, direct valid_evidence_scope exposure, project-local fixture scratch metadata, first-read overpromotion protection, and the explicit baseline-comparison-not-profit-proof boundary",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "paper_trade_now"
                and row_has_saved_live_component_total(row, 37, 1)
                and row.get("child_guardrail_check_count") == 13
                and row.get("report_json") == "out/status_validation/paper_trade_now/paper_trade_now_validation.json"
                and "stale-snapshot note" in str(row.get("current_read") or "")
                and "explicit scanner/API-access-failure refresh with stale-cache fallback count/kind/error preservation" in str(row.get("current_read") or "")
                and "scorecard-sourced right-now decision-gate metadata" in str(row.get("current_read") or "")
                and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in str(row.get("current_read") or "")
                and "rejects malformed scorecard gates, including boolean and non-positive copied-gate floors, before creating fixture/report artifacts" in str(row.get("current_read") or "")
                and "project-local fixture scratch metadata is now published as a structured guardrail" in str(row.get("current_read") or "")
                and "BAQ remains explicitly not BEL" in str(row.get("current_read") or "")
                and "valid_evidence_scope=operator_action_routing_only" in str(row.get("current_read") or "")
                and "direct validation report `valid_evidence_scope=operator_action_routing_only`" in str(row.get("current_read") or "")
                and "`operator_read_gate` fields preserve the operator action-priority/read-gating contract" in str(row.get("current_read") or "")
                and "not no-target, clean-empty, settled-ROI, promotion, live-profitability, bankroll, real-money, or new forward evidence by itself" in str(row.get("current_read") or "")
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_right_now_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_right_now_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_right_now_artifacts",
                    "scorecard_missing_no_baq_fails_before_right_now_artifacts",
                    "fixture_branches_and_navigation_bundle_stay_covered",
                    "api_access_stale_cache_fallback_top_card_context_stays_pinned",
                    "live_surface_drift_check_stays_pinned_to_current_render",
                    "stale_snapshot_hierarchy_and_evidence_boundary_stay_explicit",
                    "relocated_sidecar_and_routed_context_pointers_stay_explicit",
                    "right_now_scorecard_gate_source_stays_explicit",
                    "paper_trade_now_explicitly_stays_action_priority_not_new_evidence",
                    "direct_validation_report_exposes_right_now_valid_scope",
                    "fixture_scratch_metadata_published",
                }
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_right_now_top_card_guardrail_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory exposes the right-now top-card validator's explicit fixture-plus-live total-check metadata plus its thirteen structured action-priority/read-gating guardrails, including fail-before-artifacts scorecard checks, API-access stale-cache fallback context, stale-snapshot honesty, OP/CD/shadow hierarchy visibility, BAQ-not-BEL alias visibility, routed sidecar pointers, scorecard-sourced decision-gate metadata with the 30/20/100 gate-boundary read plus no-BAQ-as-BEL prerequisite, direct valid-scope report exposure, project-local fixture scratch metadata, and the operator-read-gate/no-new-forward-evidence boundary",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "paper_trade_next_steps"
                and row_has_saved_live_component_total(row, 33, 12)
                and row.get("child_guardrail_check_count") == 14
                and row.get("report_json") == "out/status_validation/paper_trade_next_steps/paper_trade_next_steps_validation.json"
                and "max-races-limited target-coverage" in str(row.get("current_read") or "")
                and "API-access stale-cache fallback count/kind/error context preserved" in str(row.get("current_read") or "")
                and "JSON `operator_read_gate_issue_flags` plus top-level issue booleans" in str(row.get("current_read") or "")
                and "matching text/markdown issue-flag lines" in str(row.get("current_read") or "")
                and "source JSON/text/markdown outputs now publish `valid_evidence_scope`, `evidence_boundary`, and `evidence_boundary_text`" in str(row.get("current_read") or "")
                and "cannot be overread as scanner evidence, ledger evidence, settled ROI, promotion readiness, live profitability, real-money support, or BAQ-as-BEL evidence" in str(row.get("current_read") or "")
                and "exact valid_evidence_scope=paper_trade_next_step_action_routing_only" in str(row.get("current_read") or "")
                and "scorecard-sourced decision-gate metadata" in str(row.get("current_read") or "")
                and "malformed scorecard gates rejected before fixture/report artifacts" in str(row.get("current_read") or "")
                and "project-local fixture scratch metadata now published as a structured guardrail" in str(row.get("current_read") or "")
                and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in str(row.get("current_read") or "")
                and "routing cleanliness, refresh/rerun guidance, repair prompts, sample-readiness wording, and review-floor cautions do not advance" in str(row.get("current_read") or "")
                and "Phase 8 shadow first-read status" in str(row.get("current_read") or "")
                and "review floor rather than a promotion entitlement" in str(row.get("current_read") or "")
                and "not new forward edge evidence by itself" in str(row.get("current_read") or "")
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_next_steps_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_next_steps_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_next_steps_artifacts",
                    "scorecard_missing_no_baq_fails_before_next_steps_artifacts",
                    "fixture_state_ladder_stays_covered",
                    "latest_run_context_and_pipeline_failure_detail_stay_pinned",
                    "source_json_next_steps_publish_operator_read_gate_issue_flags",
                    "source_outputs_publish_next_steps_evidence_boundary_fields",
                    "direct_validation_report_exposes_next_steps_valid_scope",
                    "saved_outputs_match_source_layer_rebuilds",
                    "saved_live_drift_checks_recover_relocated_scanner_sidecars",
                    "next_steps_explicitly_stays_action_routing_not_new_edge_evidence",
                    "next_steps_preserves_scorecard_gate_boundary",
                    "fixture_scratch_metadata_published",
                }
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_next_steps_action_routing_guardrail_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory exposes the next-steps validator's explicit fixture-plus-saved-live total-check metadata plus its fourteen structured action-routing guardrails, including malformed-scorecard no-artifact checks, non-positive copied Phase 8 and real-money gate floor checks, source JSON/text/markdown operator-read-gate issue flags, source output evidence-boundary fields, direct valid_evidence_scope exposure, max-races-limited target-coverage routing, scorecard-sourced 30/20/100 gate-boundary metadata, relocated scanner-sidecar recovery in saved-live drift checks, project-local fixture scratch metadata, the Phase 8 review-floor-not-promotion-entitlement caution, and the no-new-forward-edge evidence boundary",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "paper_trade_daily_summary"
                and row_has_saved_live_component_total(row, 25, 9)
                and row.get("child_guardrail_check_count") == 15
                and row.get("report_json") == "out/status_validation/paper_trade_daily_summary/paper_trade_daily_summary_validation.json"
                and "full routed quick-jump bundle" in str(row.get("current_read") or "")
                and "operator_read_gate read/status/refresh-command lines" in str(row.get("current_read") or "")
                and "explicit routed right-now focus/timing/freshness/stale-snapshot/ops snapshot" in str(row.get("current_read") or "")
                and "source rendered daily summaries and the direct validator report now publish exact `valid_evidence_scope=daily_operator_workflow_navigation_only` lines plus source-level boundary text" in str(row.get("current_read") or "")
                and "direct primary/shadow settlement-audit next-action lines" in str(row.get("current_read") or "")
                and "malformed/invalid-shape/missing-lanes settlement-audit JSON sidecars separated from missing audit JSON" in str(row.get("current_read") or "")
                and "direct-fixture API-access action/recheck routing" in str(row.get("current_read") or "")
                and "ROI-complete settled-evidence boundary visible" in str(row.get("current_read") or "")
                and "BAQ remains explicitly not BEL" in str(row.get("current_read") or "")
                and "malformed scorecard gates rejected before fixture/report artifacts" in str(row.get("current_read") or "")
                and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in str(row.get("current_read") or "")
                and "not new forward evidence by itself" in str(row.get("current_read") or "")
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_daily_summary_artifacts",
                    "scorecard_phase8_gate_floor_fails_before_daily_summary_artifacts",
                    "scorecard_real_money_gate_floor_fails_before_daily_summary_artifacts",
                    "scorecard_missing_no_baq_fails_before_daily_summary_artifacts",
                    "fixture_bundle_and_snapshot_lines_stay_covered",
                    "saved_live_daily_summaries_match_current_rebuilds",
                    "json_only_preflight_and_missing_artifacts_stay_explicit",
                    "settlement_audit_json_malformed_invalid_shape_and_missing_lanes_stay_distinct",
                    "pipeline_failure_and_readiness_context_stay_pinned",
                    "api_access_stale_cache_fallback_context_stays_pinned",
                    "daily_summary_explicitly_stays_workflow_not_new_evidence",
                    "source_daily_summary_output_publishes_evidence_boundary_fields",
                    "direct_validation_report_exposes_daily_summary_valid_scope",
                    "daily_summary_preserves_scorecard_gate_boundary",
                    "fixture_scratch_metadata_published",
                }
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_daily_summary_workflow_guardrail_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory exposes the daily-summary validator's explicit fixture-plus-saved-live total-check metadata plus its fifteen workflow/navigation guardrails, including malformed-scorecard and non-positive-gate no-artifact checks, routed right-now JSON operator_read_gate visibility, routed right-now freshness and stale-snapshot context, primary/shadow settlement-audit next actions, malformed/invalid-shape/missing-lanes settlement-audit JSON separation, next-step source artifacts and decision-gate lines, source-output valid-scope/boundary fields, direct valid_evidence_scope exposure, BAQ-not-BEL preflight fallback visibility, missing scan-output fallback plus API-access stale-cache fallback and pipeline-failure/readiness context, saved-live rebuild parity, project-local fixture scratch metadata, the scorecard-sourced 30/20/100 gate-boundary read, and the no-new-forward-evidence frame",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "paper_trade_ops_history"
                and row_has_saved_live_component_total(row, 24, 1)
                and row.get("child_guardrail_check_count") == 15
                and row.get("report_json") == "out/status_validation/paper_trade_ops_history/paper_trade_ops_history_validation.json"
                and "bet-ready, no-target, unknown-calendar, zero-hit" in str(row.get("current_read") or "")
                and "limited-coverage empty, limited-coverage with activity" in str(row.get("current_read") or "")
                and "explicit API-access scanner failure, including API-access stale-cache fallback count/kind/error context" in str(row.get("current_read") or "")
                and "preserving API sidecar action/recheck routing" in str(row.get("current_read") or "")
                and "missing/empty/unreadable/invalid-shape artifact issue days" in str(row.get("current_read") or "")
                and "pipeline-recorded scanner-status issue days" in str(row.get("current_read") or "")
                and "relocated scanner sidecars" in str(row.get("current_read") or "")
                and "stale default scanner filename" in str(row.get("current_read") or "")
                and "saved JSON preflight calendar context explicit" in str(row.get("current_read") or "")
                and "fixture and live summary counts are now published as structured JSON" in str(row.get("current_read") or "")
                and "source markdown now carries exact `valid_evidence_scope=rolling_operator_recap_only` plus boundary text" in str(row.get("current_read") or "")
                and "direct validator report exposes exact `valid_evidence_scope=rolling_operator_recap_only`" in str(row.get("current_read") or "")
                and "cannot be overread as scanner evidence, settled ROI, promotion readiness, live profitability, real-money support, or BAQ-as-BEL evidence" in str(row.get("current_read") or "")
                and "rejects malformed scorecard gates before fixture/report artifacts, including non-positive Phase 8 and real-money floors" in str(row.get("current_read") or "")
                and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in str(row.get("current_read") or "")
                and "not new forward evidence by itself" in str(row.get("current_read") or "")
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_ops_history_artifacts",
                    "scorecard_phase8_gate_floor_fails_before_ops_history_artifacts",
                    "scorecard_real_money_gate_floor_fails_before_ops_history_artifacts",
                    "scorecard_missing_no_baq_fails_before_ops_history_artifacts",
                    "fixture_day_bucket_matrix_stays_covered",
                    "saved_fixture_and_live_surfaces_match_current_rebuilds",
                    "saved_json_preflight_context_and_relocated_sidecar_recovery_stay_explicit",
                    "pipeline_failure_and_partial_cache_takeaways_stay_honest",
                    "api_access_stale_cache_fallback_takeaway_stays_explicit",
                    "ops_history_explicitly_stays_operational_recap_not_new_evidence",
                    "source_outputs_publish_ops_history_evidence_boundary_fields",
                    "direct_validation_report_exposes_ops_history_valid_scope",
                    "ops_history_preserves_scorecard_gate_boundary",
                    "fixture_scratch_metadata_published",
                    "summary_counts_published_and_calendar_unknown_counts_source_calendar_state",
                }
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_ops_history_operational_recap_guardrail_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory exposes the ops-history validator's explicit fixture-plus-live total-check metadata plus its fifteen rolling operational-recap guardrails, including malformed-scorecard and non-positive-gate no-artifact checks, distinct day buckets for bet-ready, no-target, unknown-calendar, zero-hit, limited-coverage, hit-found/no-bet, structured summary-count metadata, API-access scanner-failure action/recheck routing, API-access stale-cache fallback kind/count/error detail, recommender/logger failure, missing scan-output artifacts, missing/empty/unreadable/invalid-shape artifacts, pipeline-recorded scanner-status issues, relocated scanner sidecar recovery, saved-JSON preflight fallback, source-output evidence-boundary fields, direct valid_evidence_scope exposure, project-local fixture scratch metadata, the scorecard-sourced 30/20/100 gate-boundary read, and the no-new-forward-evidence frame",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "cache_only_messaging"
                and row.get("child_total_checks") == 6
                and row.get("child_guardrail_check_count") == 14
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_cache_only_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_cache_only_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_cache_only_artifacts",
                    "scorecard_missing_no_baq_fails_before_cache_only_artifacts",
                    "no_target_cache_only_days_stay_stand_down_not_generic_issue",
                    "active_target_cache_only_days_stay_rerun_live_not_empty_or_quiet",
                    "json_only_preflight_fallback_preserves_the_calendar_split",
                    "blank_text_preflight_fallback_preserves_the_calendar_split",
                    "active_target_branch_keeps_relocated_scanner_pointer_and_routed_quick_reads",
                    "cache_only_messaging_stays_cross_surface_and_fixture_routed",
                    "fixture_scratch_metadata_published",
                    "cache_only_messaging_explicitly_stays_operator_routing_not_new_evidence",
                    "cache_only_messaging_preserves_scorecard_gate_boundary",
                    "direct_validation_report_exposes_cache_only_valid_scope",
                }
                and "project-local fixture scratch metadata" in str(row.get("current_read") or "")
                and "valid_evidence_scope=cache_only_missing_cache_routing_only" in str(row.get("current_read") or "")
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_cache_only_guardrail_inventory_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory still exposes the cache-only messaging validator's explicit total-check metadata plus its fourteen structured cache-miss guardrails, including malformed-scorecard and non-positive-gate no-artifact failures, project-local fixture scratch metadata, the cache-only evidence-boundary, direct valid_evidence_scope visibility, and scorecard-gate-boundary guardrails, instead of only seeing the operator umbrella summary string",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "partial_cache_messaging"
                and row.get("child_total_checks") == 7
                and row.get("child_guardrail_check_count") == 14
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_partial_cache_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_partial_cache_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_partial_cache_artifacts",
                    "scorecard_missing_no_baq_fails_before_partial_cache_artifacts",
                    "clean_empty_and_partial_cache_empty_stay_distinct",
                    "partial_cache_with_activity_stays_distinct_from_empty_and_full_cache_miss",
                    "json_only_preflight_fallback_preserves_clean_empty_vs_limited_coverage_split",
                    "blank_text_preflight_fallback_preserves_clean_empty_vs_limited_coverage_split",
                    "partial_cache_activity_branch_keeps_relocated_scanner_pointer_and_routed_quick_reads",
                    "partial_cache_messaging_stays_cross_surface_and_fixture_routed",
                    "fixture_scratch_metadata_published",
                    "partial_cache_messaging_explicitly_stays_operator_routing_not_new_evidence",
                    "partial_cache_messaging_preserves_scorecard_gate_boundary",
                    "direct_validation_report_exposes_partial_cache_valid_scope",
                }
                and "project-local fixture scratch metadata" in str(row.get("current_read") or "")
                and "valid_evidence_scope=partial_cache_limited_coverage_routing_only" in str(row.get("current_read") or "")
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_partial_cache_guardrail_inventory_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory still exposes the partial-cache messaging validator's explicit total-check metadata plus its fourteen structured limited-coverage guardrails, including malformed-scorecard and non-positive-gate no-artifact failures, project-local fixture scratch metadata, the partial-cache evidence-boundary, direct valid_evidence_scope visibility, and scorecard-gate-boundary guardrails, instead of only seeing the operator umbrella summary string",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "paper_trade_lane_monitor"
                and row_has_saved_live_component_total(row, 11, 10)
                and row.get("child_guardrail_check_count") == 15
                and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in str(row.get("current_read") or "")
                and "missing/malformed/non-positive-cost ROI-complete coverage gap visibility" in str(row.get("current_read") or "")
                and "fixture cleanliness, saved-live rebuilds, open queues, incomplete-settlement repair lines, and review-floor cautions do not advance" in str(row.get("current_read") or "")
                and "rejecting malformed and non-positive scorecard gates before fixture/report artifacts" in str(row.get("current_read") or "")
                and "project-local fixture scratch metadata" in str(row.get("current_read") or "")
                and "valid_evidence_scope=compact per-lane forward-observation and settlement-queue review" in str(row.get("current_read") or "")
                and "not new forward evidence by itself" in str(row.get("current_read") or "")
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_lane_monitor_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_lane_monitor_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_lane_monitor_artifacts",
                    "scorecard_missing_no_baq_fails_before_lane_monitor_artifacts",
                    "fixture_forward_states_and_queue_modes_stay_covered",
                    "saved_outputs_and_live_surfaces_match_current_rebuilds",
                    "incomplete_settlement_and_roi_gap_visibility_stay_explicit",
                    "sample_progress_baseline_and_queue_context_stay_pinned",
                    "open_queue_settlement_templates_stay_safe_and_row_specific",
                    "lane_monitor_decision_gate_stays_visible",
                    "phase8_review_floor_caution_stays_visible",
                    "lane_monitor_explicitly_stays_compact_observation_not_new_evidence",
                    "direct_validation_report_exposes_lane_monitor_valid_scope",
                    "fixture_scratch_metadata_published",
                    "lane_monitor_preserves_scorecard_gate_boundary",
                }
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_lane_monitor_guardrail_inventory_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory exposes the lane-monitor validator's explicit fixture-plus-saved-live total-check metadata plus its fifteen compact-observation guardrails, including malformed-scorecard and non-positive-gate no-artifact checks, row-specific safe settlement-command templates, scorecard-sourced 30/20/100 gate-boundary metadata, no-overpromotion decision-gate visibility, Phase 8 review-floor caution, malformed and non-positive-cost ROI-gap coverage, direct valid_evidence_scope exposure, project-local fixture scratch metadata, and the no-new-forward-evidence frame, instead of only seeing the operator umbrella summary string",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "paper_trade_lane_summary"
                and row_has_saved_live_component_total(row, 19, 18)
                and row.get("child_guardrail_check_count") == 16
                and "source rendered lane summaries and the direct validator report now publish exact `valid_evidence_scope=paper_trade_lane_summary_navigation_context_only` lines plus source-level boundary text" in str(row.get("current_read") or "")
                and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in str(row.get("current_read") or "")
                and "rejecting malformed scorecard gates before fixture/report artifacts" in str(row.get("current_read") or "")
                and "direct-fixture API-access action/recheck routing" in str(row.get("current_read") or "")
                and "lifted operator read-gate issue flags" in str(row.get("current_read") or "")
                and "current ROI-complete/timestamp coverage wording" in str(row.get("current_read") or "")
                and row.get("report_json") == "out/status_validation/paper_trade_lane_summary/paper_trade_lane_summary_validation.json"
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_lane_summary_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_lane_summary_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_lane_summary_artifacts",
                    "scorecard_missing_no_baq_fails_before_lane_summary_artifacts",
                    "fixture_quick_files_and_lane_snapshot_stay_covered",
                    "saved_live_lane_summaries_match_current_rebuilds",
                    "relocated_sidecar_and_placeholder_fallbacks_stay_explicit",
                    "pipeline_failure_roi_gap_and_context_lines_stay_pinned",
                    "api_access_stale_cache_fallback_context_stays_pinned",
                    "lane_summary_lifts_decision_gate_when_available",
                    "lane_summary_explicitly_stays_navigation_not_new_evidence",
                    "source_lane_summary_output_publishes_evidence_boundary_fields",
                    "direct_validation_report_exposes_lane_summary_valid_scope",
                    "lane_summary_preserves_scorecard_gate_boundary",
                    "fixture_scratch_root_project_local",
                    "fixture_scratch_metadata_published",
                }
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_lane_summary_guardrail_inventory_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory exposes the lane-summary validator's explicit fixture-plus-saved-live total-check metadata plus its sixteen enriched-summary guardrails, including malformed-scorecard no-artifact checks, non-positive copied Phase 8 and real-money gate floor checks, source-output valid-scope/boundary fields, direct valid_evidence_scope exposure, API-access stale-cache fallback context with lifted operator read-gate issue flags, current ROI-complete/timestamp coverage wording, no-overpromotion decision-gate, Phase 8 review-floor caution visibility, project-local scratch hygiene with published scratch metadata, and the scorecard-sourced gate-boundary guardrail, instead of only seeing the operator umbrella summary string",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "refresh_live_paper_trade_surfaces"
                and row.get("child_total_checks") == 24
                and row.get("child_guardrail_check_count") == 24
                and "missing scan-output artifacts survive saved-live refresh" in str(row.get("current_read") or "")
                and "pipeline-recorded invalid_shape scanner-status states survive saved-live refresh" in str(row.get("current_read") or "")
                and "CURRENT_EVIDENCE_SUMMARY" in str(row.get("current_read") or "")
                and "settlement-audit -> current bridge -> current bridge validator rebuild contract" in str(row.get("current_read") or "")
                and "routed operator_read_gate issue flags" in str(row.get("current_read") or "")
                and "top-card issue flags matched into the current-evidence bridge" in str(row.get("current_read") or "")
                and "preserving existing top-card operator_read_gate issue flags under --skip-top-level" in str(row.get("current_read") or "")
                and "source-documents that route through current_evidence_summary.json.rebuild_validation_contract constants and stdout" in str(row.get("current_read") or "")
                and "validates malformed current-evidence rebuild contracts before fixture/report artifacts" in str(row.get("current_read") or "")
                and "publishes the bridge-owned current_evidence_summary.json rebuild_validation_contract read as refresh-helper boundary metadata only" in str(row.get("current_read") or "")
                and "project-local fixture scratch metadata" in str(row.get("current_read") or "")
                and "validates malformed and non-positive scorecard gates before fixture/report artifacts" in str(row.get("current_read") or "")
                and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in str(row.get("current_read") or "")
                and "valid_evidence_scope=saved_live_refresh_helper_rebuild_metadata_only" in str(row.get("current_read") or "")
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_refresh_helper_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_refresh_helper_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_refresh_helper_artifacts",
                    "scorecard_missing_no_baq_fails_before_refresh_helper_artifacts",
                    "current_evidence_missing_rebuild_contract_fails_before_refresh_helper_artifacts",
                    "current_evidence_weakened_rebuild_contract_fails_before_refresh_helper_artifacts",
                    "full_refresh_rebuilds_saved_live_surfaces",
                    "preflight_note_surfaces_refresh_from_saved_snapshot",
                    "missing_scan_output_survives_saved_live_refresh",
                    "pipeline_recorded_invalid_shape_survives_saved_live_refresh",
                    "daily_summary_keeps_routed_quick_jump_bundle",
                    "daily_summary_next_step_source_artifacts_stay_explicit",
                    "daily_summary_lifts_operator_read_gate_issue_flags_through_saved_live_refresh",
                    "paper_trade_now_keeps_routed_navigation_bundle",
                    "paper_trade_now_keeps_lane_context_and_why_lines",
                    "current_evidence_bridge_refreshes_with_rebuild_contract",
                    "refresh_helper_source_documents_current_evidence_rebuild_contract",
                    "as_of_date_pins_top_level_freshness_for_reproducible_refreshes",
                    "latest_only_refresh_stays_confined_to_newest_preflight_lane_daily_surfaces",
                    "helper_stdout_says_refresh_is_not_new_evidence",
                    "helper_stdout_reports_as_of_date_usage_honestly",
                    "refresh_helper_preserves_scorecard_gate_boundary",
                    "direct_validation_report_exposes_refresh_helper_valid_scope",
                    "fixture_scratch_metadata_published",
                }
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_refresh_helper_guardrail_inventory_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory still exposes the refresh-helper validator's explicit total-check metadata plus its twenty-four structured saved-live rebuild guardrails, including malformed-scorecard, non-positive scorecard, and malformed-current-evidence no-artifact guardrails, the missing scan-output and pipeline-recorded invalid-shape saved-live refresh cases, the separate rebuilt daily-summary next-step source artifact and operator_read_gate issue-flag guardrails, current-evidence rebuild-contract refresh, helper-source rebuild-contract route, newest-run preflight/lane/daily latest-only scope boundary, direct valid_evidence_scope exposure, project-local fixture scratch metadata, and scorecard/current-evidence gate-boundary guardrails, instead of only seeing the operator umbrella summary string",
        ),
        require(
            isinstance(payload_map["paper_trade_operator_suite"].get("rows"), list)
            and any(
                row.get("name") == "run_daily_portfolio_observation"
                and row.get("child_total_checks") == 22
                and row.get("child_guardrail_check_count") == 22
                and "routed PAPER_TRADE_NOW operator_read_gate issue flags" in str(row.get("current_read") or "")
                and "missing scan-output refresh" in str(row.get("current_read") or "")
                and "scorecard-sourced right-now decision-gate metadata" in str(row.get("current_read") or "")
                and "direct wrapper validator itself now validating malformed scorecard gates before any fixture/report artifacts, including boolean and non-positive copied-gate floors, while publishing the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in str(row.get("current_read") or "")
                and "validates malformed current-evidence rebuild contracts before fixture/report artifacts" in str(row.get("current_read") or "")
                and "publishes the bridge-owned current_evidence_summary.json rebuild_validation_contract read as daily-wrapper boundary metadata only" in str(row.get("current_read") or "")
                and "project-local fixture scratch metadata" in str(row.get("current_read") or "")
                and "CURRENT_EVIDENCE_SUMMARY" in str(row.get("current_read") or "")
                and "source-backed current-evidence bridge also keeps recommendation-context/open-row separation explicit" in str(row.get("current_read") or "")
                and "publishes the settlement-audit -> current bridge -> current bridge validator rebuild order" in str(row.get("current_read") or "")
                and "valid_evidence_scope=daily_wrapper_orchestration_and_fallback_validation_only" in str(row.get("current_read") or "")
                and isinstance(row.get("child_guardrail_checks"), list)
                and {check.get("check") for check in row["child_guardrail_checks"]} == {
                    "scorecard_boolean_gate_floor_fails_before_daily_wrapper_artifacts",
                    "scorecard_nonpositive_phase8_gate_floor_fails_before_daily_wrapper_artifacts",
                    "scorecard_nonpositive_real_money_gate_floor_fails_before_daily_wrapper_artifacts",
                    "scorecard_missing_no_baq_fails_before_daily_wrapper_artifacts",
                    "current_evidence_missing_rebuild_contract_fails_before_daily_wrapper_artifacts",
                    "current_evidence_weakened_rebuild_contract_fails_before_daily_wrapper_artifacts",
                    "all_wrapper_fixture_cases_rendered",
                    "cache_and_calendar_modes_stay_distinct",
                    "settlement_and_no_bet_paths_stay_distinct",
                    "artifact_degradation_stays_explicit",
                    "missing_scan_output_wrapper_path_stays_explicit",
                    "wrapper_pins_explicit_scanner_sidecar_paths",
                    "fallback_and_helper_failure_coverage_stays_present",
                    "pipeline_error_refresh_paths_stay_covered",
                    "fallbacks_preserve_lane_why_lines_when_next_steps_exist",
                    "right_now_json_payloads_match_source_or_explicit_placeholder",
                    "daily_summary_lifts_operator_read_gate_issue_flags",
                    "current_evidence_bridge_refreshes_or_explicitly_placeholders",
                    "current_evidence_rebuild_contract_preserved",
                    "daily_wrapper_preserves_scorecard_gate_boundary",
                    "fixture_scratch_metadata_published",
                    "direct_validation_report_exposes_daily_wrapper_valid_scope",
                }
                for row in payload_map["paper_trade_operator_suite"]["rows"]
            ),
            "project_layer_can_see_daily_wrapper_guardrail_inventory_inside_operator_rows",
            "the project-level sweep can now verify that the operator-suite row inventory still exposes the daily-wrapper validator's explicit total-check metadata plus its twenty-two structured orchestration guardrails, including malformed-scorecard and malformed-current-evidence no-artifact guardrails, the missing scan-output wrapper-path guardrail, required PAPER_TRADE_NOW.json parity with scorecard-sourced gate metadata or explicit placeholder behavior, the daily-summary operator-read-gate issue-flag lift, the current-evidence bridge refresh/placeholder plus recommendation-context/open-row separation and rebuild-order contracts, the direct wrapper scorecard gate-boundary read, the bridge-owned current-evidence rebuild-contract read, project-local fixture scratch metadata, and direct valid_evidence_scope visibility, instead of only seeing the operator umbrella summary string",
        ),
        require(
            "anchor=OP_DURABLE_K7" in row_map["report_surfaces"]["current_read"]
            and "operability check rather than a profitability/deployment claim" in row_map["report_surfaces"]["current_read"]
            and "settled paper trades in the actual paper-trade lane" in row_map["report_surfaces"]["current_read"]
            and "frozen-evidence ordering check rather than new proof" in row_map["report_surfaces"]["current_read"]
            and "cross-layer alignment check rather than new forward evidence" in row_map["report_surfaces"]["current_read"]
            and "PDF refresh helper check-existing path passes through the dated HTML report validator" in row_map["report_surfaces"]["current_read"]
            and "dated HTML remains the trust anchor" in row_map["report_surfaces"]["current_read"]
            and "dated PDF remains a derivative export" in row_map["report_surfaces"]["current_read"]
            and "legacy undated PDF/DOCX aliases, legacy quick-start PDF alias, and legacy OpenClaw prompt DOCX alias stay claim-free" in row_map["report_surfaces"]["current_read"]
            and "reproducibility metadata only rather than settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence" in row_map["report_surfaces"]["current_read"]
            and "saved narrative report surfaces, direct validator report paths, and the shareable PDF refresh/check helper path stay pinned across the human-facing rollup" in row_map["report_surfaces"]["current_read"]
            and "shareable wording, presentation drift, the dated-report trust path, PDF derivative refresh-helper, and the README-inherited wrapper-leaf source-of-truth note stay explicit instead of getting flattened away" in row_map["report_surfaces"]["current_read"]
            and "human-facing alignment and export reproducibility check, not new forward evidence by itself" in row_map["report_surfaces"]["current_read"]
            and "evidence scope=settled paper-trade rows with usable ROI coverage can change posture" in row_map["report_surfaces"]["current_read"]
            and "clean scans/open signals/historical replay/calibration-only summaries/odds-only reruns cannot" in row_map["report_surfaces"]["current_read"]
            and "legacy alias=redirect-only warning page" in row_map["report_surfaces"]["current_read"]
            and "claim-free boundary" in row_map["report_surfaces"]["current_read"]
            and "legacy PDF alias=claim-free warning export, not the old XGBoost rerun report or a separate evidence source" in row_map["report_surfaces"]["current_read"]
            and "legacy DOCX alias=claim-free warning document, not the old XGBoost rerun report or a separate evidence source" in row_map["report_surfaces"]["current_read"]
            and "legacy quick-start PDF alias=claim-free warning export, not the old ML/live-prediction quick-start or a separate evidence source" in row_map["report_surfaces"]["current_read"]
            and "legacy OpenClaw prompt DOCX alias=claim-free historical-prompt warning document, not the old ML/profitability-training prompt or a separate evidence source" in row_map["report_surfaces"]["current_read"]
            and "recent-run context plus lifted lane why-now lines" in row_map["report_surfaces"]["current_read"]
            and "direct sidecar-pointer contract" in row_map["report_surfaces"]["current_read"]
            and "stale downstream lane details as inherited snapshot context rather than current-day state" in row_map["report_surfaces"]["current_read"]
            and "daily guide now also explicitly pointing issue-day triage at those top-card sidecar pointers" in row_map["report_surfaces"]["current_read"]
            and "direct one-screen main comparison route `compare_main_approaches.md` plus matched CSV/JSON sidecars" in row_map["report_surfaces"]["current_read"]
            and "Harville benchmark-only lane, current odds-only XGBoost research-only lane" in row_map["report_surfaces"]["current_read"]
            and "machine-readable evidence boundary as reproducibility/navigation metadata rather than new evidence" in row_map["report_surfaces"]["current_read"]
            and "generated main-comparison markdown/CSV/JSON bundle plus direct validator in the report inventory" in row_map["report_surfaces"]["current_read"]
            and "source-checked current-evidence bridge with the combined operator-read route plus direct validator, bridge-owned scorecard-audit routing, and bridge-owned rebuild-order routing in the report inventory" in row_map["report_surfaces"]["current_read"]
            and "the combined operator-status/source-freshness/operator-read-gate route" in row_map["report_surfaces"]["current_read"]
            and "rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only" in row_map["report_surfaces"]["current_read"]
            and "rebuilt top-card recent-run context plus lifted lane why-now lines preserved when current lane artifacts provide them" in row_map["report_surfaces"]["current_read"]
            and "stale rebuilt cards keeping the inherited-snapshot honesty note" in row_map["report_surfaces"]["current_read"]
            and "routed top-card snapshot inheritance" in row_map["report_surfaces"]["current_read"]
            and "`--latest-only` confined to the newest copied run's preflight, lane, and daily-summary surfaces" in row_map["report_surfaces"]["current_read"]
            and "`--skip-top-level` confined to leaving `OPS_HISTORY` / `PAPER_TRADE_NOW` untouched while still rerendering those per-run surfaces against the existing top-level outputs" in row_map["report_surfaces"]["current_read"]
            and "explicit `--as-of-date` freshness pinning that now says whether it was applied or skipped because top-level outputs were refreshed or skipped" in row_map["report_surfaces"]["current_read"]
            and "the real daily-wrapper validator as the other source-of-truth wrapper leaf" in row_map["report_surfaces"]["current_read"]
            and "wrapper-generated CURRENT_EVIDENCE_SUMMARY refresh/placeholder plus source-backed recommendation-context/open-row separation before Cole-facing current-paper wording" in row_map["report_surfaces"]["current_read"]
            and "the operator-suite sweep should preserve those inherited wrapper-guardrail inventories rather than flattening them" in row_map["report_surfaces"]["current_read"]
            and "bridge-published current gates source-matched to `forward_evidence_scorecard.json` `decision_gate_minimums`" in row_map["report_surfaces"]["current_read"]
            and "anchor_displacement=30, phase8_promotion_review=20, and real_money_discussion=100" in row_map["report_surfaces"]["current_read"]
            and "current evidence bridge=CURRENT_EVIDENCE_SUMMARY.md/current_evidence_summary.json" in row_map["report_surfaces"]["current_read"]
            and "source consistency matched" in row_map["report_surfaces"]["current_read"]
            and report_operator_read_route_phrase in row_map["report_surfaces"]["current_read"]
            and expected_operator_read_gate_line in row_map["report_surfaces"]["current_read"]
            and "OP_REFINED CI-only route=forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7 with ci_only_promotion_allowed=false" in row_map["report_surfaces"]["current_read"]
            and "scorecard audit route=current_evidence_summary.json.scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks as report-synchronization metadata only" in row_map["report_surfaces"]["current_read"]
            and "rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only" in row_map["report_surfaces"]["current_read"]
            and "dated PDF derivative export verified for the combined operator-status/source-freshness/operator-read-gate route, current-evidence bridge, rebuild-order route, scorecard-audit route, OP_REFINED CI-only boundary, cross-family current-paper caveat route, and full-data retrain caveat route" in row_map["report_surfaces"]["current_read"]
            and "current settled sample is CD-only context and not OP-anchor evidence" in row_map["report_surfaces"]["current_read"]
            and report_child_queue_context in row_map["report_surfaces"]["current_read"]
            and report_child_queue_workflow_phrase in row_map["report_surfaces"]["current_read"]
            and current_open_queue_detail_read in row_map["report_surfaces"]["current_read"]
            and "direct cross-family current-paper caveat route=CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py" in row_map["report_surfaces"]["current_read"]
            and "green HTML/PDF validation not OP-anchor proof or cross-family promotion evidence" in row_map["report_surfaces"]["current_read"]
            and "green report validation not OP-anchor proof or cross-family promotion evidence" in row_map["report_surfaces"]["current_read"]
            and "full-data retrain caveat route=FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py" in row_map["report_surfaces"]["current_read"]
            and "large RMSE / MAE gains and exact retrain/prediction commands kept as model-fit reproducibility context" in row_map["report_surfaces"]["current_read"]
            and "presentation outline: presentation outline matches frozen posture" in row_map["report_surfaces"]["current_read"]
            and "full-data retrain caveat route=FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py" in row_map["report_surfaces"]["current_read"]
            and "large RMSE / MAE gains and exact retrain/prediction commands kept as model-fit reproducibility context" in row_map["report_surfaces"]["current_read"]
            and "current evidence bridge=CURRENT_EVIDENCE_SUMMARY.md/current_evidence_summary.json" in row_map["report_surfaces"]["current_read"]
            and "current-evidence generated_at provenance is checked as timezone-aware metadata before report-facing summaries quote the bridge" in row_map["report_surfaces"]["current_read"]
            and "green presentation validation not OP-anchor proof or cross-family promotion evidence" in row_map["report_surfaces"]["current_read"]
            and "machine-readable evidence_boundary metadata in the report-surface JSON keeps human-facing wording alignment, dated-report trust-path checks, PDF refresh-helper checks, and narrative validator passes separate from settled ROI" in row_map["report_surfaces"]["current_read"],
            "report_layer_keeps_conservative_story",
            "report rollup still carries the OP anchor, non-promotional demo framing, the settled-paper-trades evidence boundary, the stricter evidence-scope exclusion for clean scans/open signals/replay/calibration/odds-only reruns, the source-consistent/operator-context/freshness/operator-read-gate-routed current-evidence bridge with the CD-only/not-OP-anchor boundary now visible from the long-form report, working-status report, presentation outline, shareable HTML/PDF report, PDF refresh helper, and README landing page, the full-data retrain caveat route in the long-form report, working-status report, presentation outline, README, and shareable HTML/PDF report, the landing-page validation-sweep caution, the landing-page top-card recent-run-context-plus-lifted-lane-why-now contract plus direct sidecar-pointer contract and stale-card inherited-snapshot honesty note, the landing-page daily-guide issue-day sidecar-triage contract, the landing-page one-screen main-comparison route plus report-inventory bundle/validator entries with matched CSV/JSON sidecars and evidence-boundary metadata, the saved-live-refresh rebuild contract with rebuilt-stale-card inherited-snapshot honesty, routed top-card snapshot inheritance, the newest-run preflight/lane/daily latest-only boundary, the separate skip-top-level top-card-preservation boundary, explicit as-of-date-usage honesty, and the wrapper-leaf source-of-truth / inherited-guardrail-preservation note plus wrapper-generated CURRENT_EVIDENCE_SUMMARY refresh/placeholder and recommendation-context/open-row separation guardrail kept visible, plus the report-surface reproducibility read, the direct shareable-wording / presentation-drift / dated-report-trust-path / PDF-refresh-helper / inherited-wrapper-note scope, the report-surface no-new-evidence frame, the report-surface machine-readable evidence boundary, and dated-HTML plus undated-PDF/DOCX, quick-start-PDF, and historical-prompt-DOCX alias demotion with claim-free boundary propagation",
        ),
        require(
            row_map["report_surfaces"].get("child_check_count") == 20
            and isinstance(payload_map["report_surfaces"].get("evidence_boundary"), dict)
            and payload_map["report_surfaces"]["evidence_boundary"].get("artifact_role") == "human-facing report-surface validator rollup"
            and payload_map["report_surfaces"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["report_surfaces"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["report_surfaces"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["report_surfaces"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and "do not promote OP_REFINED_K7 or Phase 8 from narrative validation cleanliness" in payload_map["report_surfaces"]["evidence_boundary"].get("non_goals", [])
            and isinstance(payload_map["report_surfaces"].get("current_evidence_bridge_json_read"), dict)
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get("source_path") == "current_evidence_summary.json"
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get("generated_at") == current_evidence.get("generated_at")
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get("generated_at_timezone_aware") is True
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get("source_consistency_overall_match") is True
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get("primary_roi_complete_rows_match") is True
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get("primary_open_rows_match") is True
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get("primary_incomplete_rows_match") is True
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get("primary_roi_gap_rows_match") is True
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get("source_freshness_state_valid") is True
            and isinstance(payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get("requires_refresh_before_right_now_use"), bool)
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get("decision_gate_source") == "forward_evidence_scorecard.json"
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get("decision_gate_source_loaded") is True
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get("anchor_displacement_min") == 30
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get("phase8_promotion_review_min") == 20
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get("real_money_discussion_min") == 100
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get(
                "decision_gate_source_values_match_scorecard"
            )
            is True
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get(
                "decision_gate_effective_values_source"
            )
            == "forward_evidence_scorecard.json:decision_gate_minimums"
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get(
                "decision_gate_missing_top_card_fields"
            )
            == []
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get(
                "decision_gate_mismatched_fields"
            )
            == []
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get(
                "effective_anchor_displacement_min"
            )
            == 30
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get(
                "effective_phase8_promotion_review_min"
            )
            == 20
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get(
                "effective_real_money_discussion_min"
            )
            == 100
            and isinstance(
                payload_map["report_surfaces"]["current_evidence_bridge_json_read"].get(
                    "rebuild_validation_contract"
                ),
                dict,
            )
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"][
                "rebuild_validation_contract"
            ].get("source") == "current_evidence_summary.json"
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"][
                "rebuild_validation_contract"
            ].get("source_path") == "rebuild_validation_contract"
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"][
                "rebuild_validation_contract"
            ].get("upstream_refresh_order") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"][
                "rebuild_validation_contract"
            ].get("upstream_refresh_order_numbers") == [1, 2, 3]
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"][
                "rebuild_validation_contract"
            ].get("prerequisite_rebuild_command") == "python3 paper_trade_settlement_audit.py"
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"][
                "rebuild_validation_contract"
            ].get("rebuild_command") == "python3 current_evidence_summary.py"
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"][
                "rebuild_validation_contract"
            ].get("direct_validation_command") == "python3 validate_current_evidence_summary.py"
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"][
                "rebuild_validation_contract"
            ].get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"][
                "rebuild_validation_contract"
            ].get("requires_source_consistency_before_quoting_current_totals") is True
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"][
                "rebuild_validation_contract"
            ].get("upstream_refresh_order_is_provenance_metadata_only") is True
            and payload_map["report_surfaces"]["current_evidence_bridge_json_read"][
                "rebuild_validation_contract"
            ].get("not_settled_roi_or_real_money_evidence") is True
            and isinstance(payload_map["report_surfaces"].get("current_evidence_rebuild_validation_contract_read"), dict)
            and payload_map["report_surfaces"]["current_evidence_rebuild_validation_contract_read"]
            == payload_map["report_surfaces"]["current_evidence_bridge_json_read"]["rebuild_validation_contract"]
            and isinstance(payload_map["report_surfaces"].get("full_report_current_evidence_bridge_json_read"), dict)
            and payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                "source_consistency_overall_match"
            )
            is True
            and payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                "primary_roi_complete_rows_match"
            )
            is True
            and payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                "primary_open_rows_match"
            )
            is True
            and payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                "primary_incomplete_rows_match"
            )
            is True
            and payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                "primary_roi_gap_rows_match"
            )
            is True
            and payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                "source_freshness_state_valid"
            )
            is True
            and isinstance(
                payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                    "requires_refresh_before_right_now_use"
                ),
                bool,
            )
            and payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                "decision_gate_source"
            )
            == "forward_evidence_scorecard.json"
            and payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                "decision_gate_source_loaded"
            )
            is True
            and payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                "decision_gate_source_values_match_scorecard"
            )
            is True
            and payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                "decision_gate_effective_values_source"
            )
            == "forward_evidence_scorecard.json:decision_gate_minimums"
            and payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                "decision_gate_missing_top_card_fields"
            )
            == []
            and payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                "decision_gate_mismatched_fields"
            )
            == []
            and payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                "effective_anchor_displacement_min"
            )
            == 30
            and payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                "effective_phase8_promotion_review_min"
            )
            == 20
            and payload_map["report_surfaces"]["full_report_current_evidence_bridge_json_read"].get(
                "effective_real_money_discussion_min"
            )
            == 100
            and isinstance(payload_map["report_surfaces"].get("presentation_outline_current_evidence_bridge_json_read"), dict)
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "source_consistency_overall_match"
            )
            is True
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "primary_roi_complete_rows_match"
            )
            is True
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "primary_open_rows_match"
            )
            is True
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "primary_incomplete_rows_match"
            )
            is True
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "primary_roi_gap_rows_match"
            )
            is True
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "source_freshness_state_valid"
            )
            is True
            and isinstance(
                payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                    "requires_refresh_before_right_now_use"
                ),
                bool,
            )
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "decision_gate_source"
            )
            == "forward_evidence_scorecard.json"
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "decision_gate_source_loaded"
            )
            is True
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "anchor_displacement_min"
            )
            == 30
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "phase8_promotion_review_min"
            )
            == 20
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "real_money_discussion_min"
            )
            == 100
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "decision_gate_source_values_match_scorecard"
            )
            is True
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "decision_gate_effective_values_source"
            )
            == "forward_evidence_scorecard.json:decision_gate_minimums"
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "decision_gate_missing_top_card_fields"
            )
            == []
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "decision_gate_mismatched_fields"
            )
            == []
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "effective_anchor_displacement_min"
            )
            == 30
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "effective_phase8_promotion_review_min"
            )
            == 20
            and payload_map["report_surfaces"]["presentation_outline_current_evidence_bridge_json_read"].get(
                "effective_real_money_discussion_min"
            )
            == 100
            and isinstance(row_map["report_surfaces"].get("child_checks"), list)
            and {check.get("check") for check in row_map["report_surfaces"]["child_checks"]} == {
                "report_surfaces_current_evidence_generated_at_is_timezone_aware",
                "readme_keeps_anchor_and_split_read",
                "full_report_keeps_paper_companion_hierarchy",
                "working_status_stays_non_promotional",
                "presentation_outline_keeps_method_roles",
                "html_report_keeps_alias_guardrail",
                "shareable_pdf_refresh_helper_keeps_derivative_boundary",
                "report_surfaces_current_evidence_bridge_json_is_source_gate_routed",
                "report_surfaces_current_evidence_rebuild_contract_is_source_routed",
                "report_surfaces_current_evidence_effective_gates_are_scorecard_backed",
                "presentation_outline_current_evidence_bridge_json_is_source_gate_routed",
                "presentation_outline_current_evidence_effective_gates_are_scorecard_backed",
                "full_report_current_evidence_effective_gates_are_scorecard_backed",
                "child_report_validators_publish_explicit_status_counts_and_reads",
                "child_report_validators_publish_explicit_total_checks",
                "child_report_validators_publish_structured_checks",
                "report_surfaces_suite_keeps_reproducibility_visible",
                "report_surfaces_suite_names_shareable_wording_trust_path_scope",
                "report_surfaces_suite_explicitly_stays_alignment_not_new_evidence",
                "report_surfaces_json_publishes_machine_readable_evidence_boundary",
            },
            "report_layer_publishes_structured_rollup_checks",
            "report rollup now has to publish its twenty explicit structured guardrails, including current-evidence generated_at timezone-aware provenance, the report-level rebuild contract, the report-level, full-report-child, and presentation-child current-evidence source/gate reads, their canonical effective gate-source checks, the explicit PDF-refresh-helper derivative-boundary check, explicit-status/explicit-summary plus explicit-total-checks child metadata contracts, the direct shareable-wording/presentation-drift/dated-report-trust-path/PDF-refresh-helper scope, the human-facing reproducibility and no-new-evidence cautions, and the machine-readable report-surface evidence-boundary contract, instead of only a summary string",
        ),
        require(
            set(report_surface_rows) == set(expected_report_surface_rows)
            and all(
                report_surface_rows[name].get("result") == "PASS"
                and report_surface_rows[name].get("metric_value") == spec["count"]
                and report_surface_rows[name].get("metric_label") == "checks"
                and report_surface_rows[name].get("child_check_count") == spec["count"]
                and report_surface_rows[name].get("json_path") == spec["json_path"]
                and all(snippet in str(report_surface_rows[name].get("current_read") or "") for snippet in spec["snippets"])
                and {check.get("check") for check in report_surface_rows[name].get("child_checks", [])}.issuperset(spec["checks"])
                for name, spec in expected_report_surface_rows.items()
            ),
            "project_layer_can_see_report_surface_row_inventory",
            "the project-level sweep can now verify that the report-surface row inventory exposes each narrative child surface plus the PDF refresh-helper validator with PASS status, explicit check totals, direct child JSON paths, critical conservative-story / derivative-boundary read snippets, and pinned child-check guardrails instead of only seeing the report-surface umbrella summary string",
        ),
        require(
            "undated HTML/PDF/DOCX report aliases, old quick-start PDF, and historical OpenClaw prompt DOCX stay legacy aliases" in row_map["validation_quickstart"]["current_read"]
            and "single decision-card sweep is a frozen-evidence ordering check rather than new forward proof" in row_map["validation_quickstart"]["current_read"]
            and "dedicated OP-anchor comparison validator as an evidence-class guardrail with readable `evidence_boundary_text`, markdown/JSON source-byte provenance, and a parked odds-only XGBoost reopening bar" in row_map["validation_quickstart"]["current_read"]
            and "dedicated main-comparison validator route for Cole's one-screen OP/CD read" in row_map["validation_quickstart"]["current_read"]
            and "method-family evidence-debt checklist" in row_map["validation_quickstart"]["current_read"]
            and "direct frozen-portfolio replay caution validator" in row_map["validation_quickstart"]["current_read"]
            and "full-data retrain diagnostic-only guardrail" in row_map["validation_quickstart"]["current_read"]
            and "historical replay P&L separated from live paper-trade, real-money, or live-profitability evidence" in row_map["validation_quickstart"]["current_read"]
            and "direct Phase 8 legacy-report caution validator" in row_map["validation_quickstart"]["current_read"]
            and "current holdout-over-headline / no-real-money / BAQ-is-not-BEL banner" in row_map["validation_quickstart"]["current_read"]
            and "source-layer paper-trade source-chain matrix plus live-scan targeting / max-races limited-coverage validator plus pipeline / recommender / EV-sizing / logger" in row_map["validation_quickstart"]["current_read"]
            and "scope-comparison validator with scorecard-sourced 30/20/100 gate and no-BAQ boundary" in row_map["validation_quickstart"]["current_read"]
            and "direct live-scan targeting / max-races limited-coverage route visible as scanner/pipeline/status/ops guardrail metadata only" in row_map["validation_quickstart"]["current_read"]
            and "operator suite's embedded `auxiliary_source_chain_matrix` plus parent-side matrix-payload rebuild parity" in row_map["validation_quickstart"]["current_read"]
            and "project sweep reading that as readiness-only parent metadata" in row_map["validation_quickstart"]["current_read"]
            and "top-level project sweep now explicitly reads as one cross-layer alignment answer rather than new forward evidence with the direct current-hierarchy child" in row_map["validation_quickstart"]["current_read"]
            and "saved navigation/runbook guides and their direct validator report paths stay pinned across the quickstart ladder" in row_map["validation_quickstart"]["current_read"]
            and "quickstart validator JSON itself now publishes a machine-readable evidence_boundary as navigation/read-order reproducibility metadata only rather than settled ROI / live profitability / promotion readiness / real-money evidence" in row_map["validation_quickstart"]["current_read"]
            and "quickstart validator/report surfaces now expose `valid_evidence_scope=validation_quickstart_navigation_contract_only` as navigation-contract metadata only" in row_map["validation_quickstart"]["current_read"]
            and "validation scratch cleanup helper publishes valid_evidence_scope=validation_scratch_cleanup_operational_hygiene_only plus a 512 MiB low-disk warning threshold" in row_map["validation_quickstart"]["current_read"]
            and "cleanup validator should remove its own generated fixture root after checks while publishing the same valid scope" in row_map["validation_quickstart"]["current_read"]
            and "report-surfaces route now also explicitly carrying shareable wording, presentation drift, the dated-report trust path, the README-inherited wrapper-leaf source-of-truth note rather than flattening it away, and the report-surface evidence boundary keeping green narrative validation separate from settled ROI / live profitability / promotion readiness / real-money evidence" in row_map["validation_quickstart"]["current_read"]
            and "right-now text/markdown/JSON parity or explicit helper-failure JSON placeholder behavior" in row_map["validation_quickstart"]["current_read"]
            and "current-evidence summary route for source-consistency plus CSV settled_ts gap exclusion plus the combined operator_status_context/source_freshness/operator_read_gate route and right_now_freshness_state validity before stale or missing-state PAPER_TRADE_NOW best-action cards become today's instruction or evidence" in row_map["validation_quickstart"]["current_read"]
            and "source_freshness.refresh_action_boundary wrapper-refresh non-evidence routing" in row_map["validation_quickstart"]["current_read"]
            and "combined current_evidence_summary.json operator_status_context/source_freshness/operator_read_gate path as refresh-before-instruction/evidence-read routing before stale or missing-state right-now cards become today's instruction or evidence" in row_map["validation_quickstart"]["current_read"]
            and "current-evidence route now also names the scorecard-sourced OP_REFINED CI-only diagnostic from forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7 with ci_only_promotion_allowed=false" in row_map["validation_quickstart"]["current_read"]
            and "current-evidence route now also names current_evidence_summary.json scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus validate_scorecard_ranking_contract_audit.py as gate/ranking/CI-only/timezone/no-BAQ synchronization metadata only" in row_map["validation_quickstart"]["current_read"]
            and "current-evidence route now also publishes current_evidence_summary.json rebuild_validation_contract as the settlement-audit -> current-bridge -> current-bridge-validator order after scorecard/rules/signals/settlement-ledger byte changes" in row_map["validation_quickstart"]["current_read"]
            and "downstream A/B route now also carries the current-paper bridge snapshot / CD-only OP-anchor-gap caveat" in row_map["validation_quickstart"]["current_read"]
            and "full-data XGBoost retrain artifact route now points exact retrain/prediction command and RMSE / MAE model-fit boundary questions to validate_full_data_retrain_artifacts.py as model-fit reproducibility metadata only rather than paper-trade / live-profitability / promotion / bankroll / real-money evidence" in row_map["validation_quickstart"]["current_read"]
            and "cross-family current-paper snapshot route for stale-card refresh / CD-only settled rows / no cross-family-promotion evidence" in row_map["validation_quickstart"]["current_read"]
            and "daily-wrapper route for `CURRENT_EVIDENCE_SUMMARY` refresh/placeholder plus source-backed recommendation-context/open-row separation" in row_map["validation_quickstart"]["current_read"]
            and "current-hierarchy-language" in row_map["validation_quickstart"]["current_read"]
            and "green cache-only / partial-cache checks proving cache-edge routing / reproducibility toward refresh or rerun only rather than quiet-day, scanner, ROI, profitability, promotion, or real-money evidence" in row_map["validation_quickstart"]["current_read"]
            and "matched PAPER_TRADE_NOW text/markdown/JSON rebuilds with JSON parity" in row_map["validation_quickstart"]["current_read"]
            and "rebuilt daily summaries inheriting refreshed top-level routed top-card snapshot lines" in row_map["validation_quickstart"]["current_read"]
            and "inherited lane context / counts / quick reads do not masquerade as current state" in row_map["validation_quickstart"]["current_read"]
            and "whether `--as-of-date` was actually applied or skipped" in row_map["validation_quickstart"]["current_read"]
            and "bootstrap-CI source notes plus PHASE7/PHASE8 report fingerprints" in row_map["validation_quickstart"]["current_read"]
            and "named machine-readable `decision_gate_minimums` for `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100` settled-observation gates" in row_map["validation_quickstart"]["current_read"]
            and "quickstart gate-source note now reads forward_evidence_scorecard.json decision_gate_minimums directly" in row_map["validation_quickstart"]["current_read"]
            and "preserves anchor_displacement=30, phase8_promotion_review=20, real_money_discussion=100, and the no-BAQ-as-BEL prerequisite" in row_map["validation_quickstart"]["current_read"]
            and "direct status-summary issue-day routing now names invalid-shape scanner sidecars, pipeline-recorded invalid-shape scanner-status states, wrapper-only invalid-shape required-pipeline sidecars, API-access stale-cache fallback metadata, and API-access / HTTP 403 action-recheck route preservation as operational issue branches before lane enrichment" in row_map["validation_quickstart"]["current_read"]
            and "daily-guide gate-source note now reads forward_evidence_scorecard.json decision_gate_minimums directly" in row_map["daily_artifact_guide"]["current_read"]
            and "preserves anchor_displacement=30, phase8_promotion_review=20, real_money_discussion=100, and the no-BAQ-as-BEL prerequisite" in row_map["daily_artifact_guide"]["current_read"]
            and "scorecard_decision_gate_minimums_read, current_evidence_operator_read_gate_read, current_evidence_scorecard_audit_route_read, and current_evidence_rebuild_validation_contract_read as daily navigation/readiness metadata only" in row_map["daily_artifact_guide"]["current_read"]
            and "umbrella operator-suite plus top-level project-sweep ladder routes now say plainly that they are alignment/readiness checks rather than new evidence" in row_map["daily_artifact_guide"]["current_read"]
            and "saved daily-use guide and its direct validator report path stay pinned across the daily ladder" in row_map["daily_artifact_guide"]["current_read"]
            and "daily-guide source markdown and direct validator report now expose exact `valid_evidence_scope=daily_artifact_guide_navigation_routing_only` as daily navigation/readiness metadata only" in row_map["daily_artifact_guide"]["current_read"]
            and "daily artifact guide validator JSON now publishes a machine-readable evidence_boundary as daily navigation/readiness metadata only" in row_map["daily_artifact_guide"]["current_read"]
            and "undated HTML/PDF/DOCX report aliases, old quick-start PDF, and historical OpenClaw prompt DOCX stay legacy-only aliases" in row_map["daily_artifact_guide"]["current_read"]
            and "direct settlement-audit action-line guidance" in row_map["daily_artifact_guide"]["current_read"]
            and "direct settlement-audit route discoverable" in row_map["daily_artifact_guide"]["current_read"]
            and "direct current-evidence summary" in row_map["daily_artifact_guide"]["current_read"]
            and "source consistency, CSV settled_ts gap exclusion, operator-status context, CD-only current rule mix, scorecard-sourced OP_REFINED CI-only routing with ci_only_promotion_allowed=false, scorecard_audit_route synchronization routing to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization metadata only, rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only, bridge-published current gates" in row_map["daily_artifact_guide"]["current_read"]
            and "scorecard_audit_route synchronization routing to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization metadata only" in row_map["daily_artifact_guide"]["current_read"]
            and "source freshness / refresh-before-right-now-use routing" in row_map["daily_artifact_guide"]["current_read"]
            and "operator-read-gate routing" in row_map["daily_artifact_guide"]["current_read"]
            and "branch-specific scanner/API-failure wording only when that route is present" in row_map["daily_artifact_guide"]["current_read"]
            and "the source-derived combined operator_status_context/source_freshness/operator_read_gate route as" in row_map["daily_artifact_guide"]["current_read"]
            and (
                (
                    "requires_refresh_before_right_now_use" in row_map["daily_artifact_guide"]["current_read"]
                    and "rerun `./run_daily_portfolio_observation.sh`" in row_map["daily_artifact_guide"]["current_read"]
                    and "before treating a stale/API-failure best-action card as today's operator instruction or evidence" in row_map["daily_artifact_guide"]["current_read"]
                )
                if current_evidence["source_freshness"].get("requires_refresh_before_right_now_use")
                else (
                    "requires_refresh_before_right_now_use=false" in row_map["daily_artifact_guide"]["current_read"]
                    and "fresh against the bridge reference date" in row_map["daily_artifact_guide"]["current_read"]
                )
            )
            and "settlement-audit action-line / no-new-evidence contract" in row_map["daily_artifact_guide"]["current_read"]
            and "cross-family current-paper snapshot route" in row_map["daily_artifact_guide"]["current_read"]
            and "full-data retrain artifact route" in row_map["daily_artifact_guide"]["current_read"]
            and "top-card entry now says stale cards carry inherited snapshot context rather than current-day state" in row_map["daily_artifact_guide"]["current_read"]
            and "PAPER_TRADE_NOW.json is the matched machine-readable sibling with operator_read_gate rather than separate evidence" in row_map["daily_artifact_guide"]["current_read"]
            and "direct right-now validator is discoverable for top-card text/markdown/JSON parity, placeholder-boundary, and operator-read-gate questions" in row_map["daily_artifact_guide"]["current_read"]
            and "rebuilt PAPER_TRADE_NOW JSON parity" in row_map["daily_artifact_guide"]["current_read"]
            and "recent-run-context plus why-now preservation" in row_map["daily_artifact_guide"]["current_read"]
            and "rebuilt daily summaries inheriting refreshed top-level routed top-card snapshot lines" in row_map["daily_artifact_guide"]["current_read"]
            and "optional `--as-of-date` freshness pinning reports whether it was actually applied or skipped" in row_map["daily_artifact_guide"]["current_read"]
            and "current-evidence summary, main-comparison" in row_map["daily_artifact_guide"]["current_read"]
            and "main-status route preserving `status_doc_base_api_access_route_documented`" in row_map["daily_artifact_guide"]["current_read"]
            and "OP-anchor source-provenance plus readable-boundary" in row_map["daily_artifact_guide"]["current_read"]
            and "paper-trade usage runbook route" in row_map["daily_artifact_guide"]["current_read"]
            and "hands-on bridge from daily top cards into exact commands while preserving the OP-anchor source-provenance plus readable-boundary route and audit-only fingerprint / boundary-text boundary" in row_map["daily_artifact_guide"]["current_read"]
            and "real daily-wrapper validator" in row_map["daily_artifact_guide"]["current_read"]
            and "wrapper-generated `CURRENT_EVIDENCE_SUMMARY` refresh/placeholder plus source-backed recommendation-context/open-row separation" in row_map["daily_artifact_guide"]["current_read"]
            and "direct report-surfaces validator discoverable" in row_map["daily_artifact_guide"]["current_read"]
            and "README-inherited wrapper-leaf source-of-truth note" in row_map["daily_artifact_guide"]["current_read"]
            and "source-of-truth guardrail reports broader operator/project sweeps should preserve rather than flatten" in row_map["daily_artifact_guide"]["current_read"]
            and "source-chain matrix" in row_map["daily_artifact_guide"]["current_read"]
            and "scorecard ranking-contract audit / gate-floor route" in row_map["daily_artifact_guide"]["current_read"]
            and "scorecard audit as the direct route for copied gate-floor/ranking/CI-only drift" in row_map["daily_artifact_guide"]["current_read"]
            and "quiet-vs-broken triage path now also frames green cache-only / partial-cache messaging validators as cache-edge routing / reproducibility metadata only rather than quiet-day, scanner, ROI, profitability, promotion, or real-money evidence" in row_map["daily_artifact_guide"]["current_read"]
            and "operator suite's embedded `auxiliary_source_chain_matrix` and parent-side matrix-payload rebuild parity" in row_map["daily_artifact_guide"]["current_read"]
            and "project sweep reading that as readiness-only parent metadata" in row_map["daily_artifact_guide"]["current_read"]
            and "CURRENT_EVIDENCE_SUMMARY before current-paper status updates plus its scorecard_audit_route before copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks and its rebuild_validation_contract before bridge rebuilds or quotes after source-byte changes" in row_map["daily_artifact_guide"]["current_read"]
            and "full-data XGBoost retrain validation as model-fit reproducibility metadata only rather than paper-trade / live-profitability / bankroll / real-money evidence" in row_map["daily_artifact_guide"]["current_read"]
            and "OP_DURABLE_K7 as the safest anchor" in row_map["daily_artifact_guide"]["current_read"]
            and "live-scanner usage route preserving" in row_map["daily_artifact_guide"]["current_read"]
            and "API-access-failure handling such as HTTP 403 including refresh_daily_wrapper_before_evidence_read plus ./run_daily_portfolio_observation.sh" in row_map["daily_artifact_guide"]["current_read"]
            and "compact source-chain matrix is now exposed" in row_map["paper_trade_usage"]["current_read"]
            and "operational-readiness-only / no-live-evidence boundary" in row_map["paper_trade_usage"]["current_read"]
            and "operator suite embeds that fresh matrix as `auxiliary_source_chain_matrix`, checks disk hashes, and recomputes payload parity while the project sweep verifies the embedded result as propagation/readiness metadata" in row_map["paper_trade_usage"]["current_read"]
            and "OP-anchor research provenance/readable-boundary route is now exposed in the runbook as `OP_ANCHOR_METHOD_COMPARISON.md` / `op_anchor_method_comparison.json` plus `validate_op_anchor_method_comparison.py`" in row_map["paper_trade_usage"]["current_read"]
            and "preserving fingerprints and boundary text as provenance/reproducibility and no-new-evidence metadata only rather than settled ROI, promotion readiness, live profitability, or real-money evidence" in row_map["paper_trade_usage"]["current_read"]
            and "direct cross-family current-paper route is now exposed in the operator runbook as `CROSS_FAMILY_DECISION.md` plus `validate_cross_family_decision.py`" in row_map["paper_trade_usage"]["current_read"]
            and "current-paper snapshot caveat for stale-card refresh routing, CD-only settled rows, and source-published settlement-queue state/context stay out of OP-anchor proof, cross-family promotion evidence, live profitability, bankroll guidance, and real-money evidence" in row_map["paper_trade_usage"]["current_read"]
            and "current-evidence bridge route is now exposed in the runbook as `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` plus `current_evidence_summary.py` and `validate_current_evidence_summary.py`" in row_map["paper_trade_usage"]["current_read"]
            and "source-consistency check across `PAPER_TRADE_NOW.json`, settlement audit, and the primary settlement CSV plus the combined `operator_status_context` + `source_freshness` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` / `recommended_command` route" in row_map["paper_trade_usage"]["current_read"]
            and "before stale or missing-state right-now cards are treated as today's operator instruction or evidence" in row_map["paper_trade_usage"]["current_read"]
            and "source-matches the OP_REFINED CI-only diagnostic to `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` with `ci_only_promotion_allowed=false`" in row_map["paper_trade_usage"]["current_read"]
            and "source-matches the operator gate floors to `forward_evidence_scorecard.json` `decision_gate_minimums`" in row_map["paper_trade_usage"]["current_read"]
            and "no-BAQ-as-BEL prerequisite" in row_map["paper_trade_usage"]["current_read"]
            and "treated as future ROI-complete paper-observation requirements rather than cleared gates" in row_map["paper_trade_usage"]["current_read"]
            and "source_freshness.right_now_freshness_state_valid` as wrapper-refresh-first" in row_map["paper_trade_usage"]["current_read"]
            and "source_freshness.requires_refresh_before_right_now_use=true` as refresh-the-wrapper-before-use" in row_map["paper_trade_usage"]["current_read"]
            and "operator_read_gate.requires_refresh_before_evidence_read=true` as wrapper-refresh-before-instruction/evidence-read" in row_map["paper_trade_usage"]["current_read"]
            and "consumes current_evidence_summary.json rebuild_validation_contract for the required `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` rebuild order after source-byte changes as provenance metadata only" in row_map["paper_trade_usage"]["current_read"]
            and "clean current-bridge rebuild is not enough before report-facing comparison quotes" in row_map["paper_trade_usage"]["current_read"]
            and "copied-current-paper fanout drift prevention only, not evidence movement" in row_map["paper_trade_usage"]["current_read"]
            and f"source-consistency / operator-status context / structured source-freshness / operator-read-gate routing / {bridge_queue_navigation} / scorecard CI-only boundary / scorecard audit route / rebuild order / no-overclaim metadata only" in row_map["paper_trade_usage"]["current_read"]
            and f"bridge-published `decision_gate_progress` read ({current_gate_progress_read}) plus the CD-only settled sample / OP_DURABLE_K7 ROI-complete row boundary plus {bridge_queue_navigation}" in row_map["paper_trade_usage"]["current_read"]
            and bridge_queue_navigation in row_map["paper_trade_usage"]["current_read"]
            and f"{bridge_queue_navigation} / scorecard CI-only boundary / scorecard audit route / rebuild order / no-overclaim metadata only" in row_map["paper_trade_usage"]["current_read"]
            and paper_usage_open_context_phrase in row_map["paper_trade_usage"]["current_read"]
            and (
                not current_open_settlement_summary
                or current_open_settlement_summary == "none"
                or current_open_settlement_summary in row_map["paper_trade_usage"]["current_read"]
            )
            and "source_consistency.overall_match=false` as repair-first" in row_map["paper_trade_usage"]["current_read"]
            and "top-card/rebuild path carries preserved primary/shadow recent-run context plus lane why-now lines" in row_map["paper_trade_usage"]["current_read"]
            and "stale cards explicitly mark downstream lane context/counts/quick reads as inherited snapshot state rather than current-day state" in row_map["paper_trade_usage"]["current_read"]
            and "across both the immediate operator card and rebuilt saved-live refresh path" in row_map["paper_trade_usage"]["current_read"]
            and "rebuilt daily summaries inheriting routed top-card snapshot lines from refreshed top-level surfaces" in row_map["paper_trade_usage"]["current_read"]
            and "distinct `--latest-only` newest-run versus `--skip-top-level` top-card-preservation maintenance boundaries staying visible" in row_map["paper_trade_usage"]["current_read"]
            and "optional `--as-of-date` freshness pinning saying whether it was applied to rebuilt top-level freshness or ignored because top-level outputs were skipped" in row_map["paper_trade_usage"]["current_read"]
            and "current hierarchy language route is now exposed in the operator runbook for `live_hierarchy`, `primary_companion`, and compatibility-only `primary_shadow` edits" in row_map["paper_trade_usage"]["current_read"]
            and "saved operator runbook and its direct validator report path stay pinned across the operator ladder" in row_map["paper_trade_usage"]["current_read"]
            and "paper-trade usage validator JSON now publishes exact valid_evidence_scope=paper_trade_usage_operator_runbook_navigation_only plus a machine-readable evidence_boundary as operator workflow/navigation metadata only" in row_map["paper_trade_usage"]["current_read"]
            and "direct report-surfaces validator plus its saved markdown output are now exposed" in row_map["paper_trade_usage"]["current_read"]
            and "README-inherited wrapper-leaf note the narrative rollup should preserve rather than flatten" in row_map["paper_trade_usage"]["current_read"]
            and "operator-suite and top-level project-sweep routes now also say plainly that they are alignment/readiness checks rather than new evidence" in row_map["paper_trade_usage"]["current_read"]
            and "right-now text/markdown/JSON bundle must keep machine-readable JSON parity unless the full helper failed into an explicit no-new-forward-evidence placeholder" in row_map["paper_trade_usage"]["current_read"]
            and "source-of-truth wrapper reports broader operator/project sweeps should preserve rather than flatten" in row_map["paper_trade_usage"]["current_read"]
            and "including wrapper-generated `CURRENT_EVIDENCE_SUMMARY` refresh/placeholder plus source-backed recommendation-context/open-row separation before Cole-facing current-paper wording" in row_map["paper_trade_usage"]["current_read"]
            and "broader selective-family secondary shadow read staying replay-context rather than extra train-only proof" in row_map["paper_trade_usage"]["current_read"]
            and "settlement-audit action-line contract" in row_map["paper_trade_usage"]["current_read"]
            and "daily_summary lifts them with the no-new-evidence boundary" in row_map["paper_trade_usage"]["current_read"]
            and "action slugs are ledger-readiness routing rather than profitability proof" in row_map["paper_trade_usage"]["current_read"]
            and "settlement layer now calls out separate direct validator routes for template sync, manual settlement entry, and ledger-completeness / ROI-coverage audit repair-label checks" in row_map["paper_trade_usage"]["current_read"]
            and "top-level out/paper_trade_preflight_note.txt file separated as a standalone manual scratch cache rather than a daily operator proof source" in row_map["paper_trade_usage"]["current_read"]
            and "no-target proof must come from the saved run-root preflight note" in row_map["paper_trade_usage"]["current_read"]
            and "direct status-summary route now points API-access / HTTP 403 action-recheck route preservation and stale-cache fallback metadata at `validate_paper_trade_status_summary.py` before lane enrichment" in row_map["paper_trade_usage"]["current_read"]
            and "direct main-status route is now exposed in the operator runbook as `COLE_STATUS_AND_PLAN.md` plus `validate_cole_status_and_plan.py`" in row_map["paper_trade_usage"]["current_read"]
            and "`status_doc_base_api_access_route_documented` keeps base API-access / HTTP 403 status-summary action-recheck route edits visible before lane enrichment" in row_map["paper_trade_usage"]["current_read"]
            and "scorecard audit route is now exposed in the operator runbook as `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `validate_scorecard_ranking_contract_audit.py`" in row_map["paper_trade_usage"]["current_read"]
            and "copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only diagnostic context, generated-at timezone provenance, and the no-BAQ-as-BEL prerequisite stay report-synchronization metadata" in row_map["paper_trade_usage"]["current_read"]
            and "consumes current_evidence_summary.json scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks as report-synchronization metadata only" in row_map["paper_trade_usage"]["current_read"]
            and "operator workflow/navigation check, not new forward evidence by itself" in row_map["paper_trade_usage"]["current_read"]
            and "keeps green cache-only / partial-cache messaging validators framed as cache-edge routing and reproducibility metadata rather than quiet-day, current scanner, settled ROI, live-profitability, promotion-readiness, or real-money evidence" in row_map["paper_trade_usage"]["current_read"]
            and "+20-25%" in row_map["cole_status_and_plan"]["current_read"]
            and f"paper-trade wrapper is now described as operational with {current_roi_complete} ROI-complete `CD_CORE_K8` primary-lane {current_settlement_word}" in row_map["cole_status_and_plan"]["current_read"]
            and f"{current_remaining_first} more ROI-complete rows still needed before the first 30-race statistical read" in row_map["cole_status_and_plan"]["current_read"]
            and cole_status_open_context_phrase in row_map["cole_status_and_plan"]["current_read"]
            and (
                not current_open_settlement_summary
                or current_open_settlement_summary == "none"
                or current_open_settlement_summary in row_map["cole_status_and_plan"]["current_read"]
            )
            and (
                current_open_settlement_summary in {"", "none"}
                or cole_status_open_identity_phrase in row_map["cole_status_and_plan"]["current_read"]
            )
            and cole_status_sample_context_phrase in row_map["cole_status_and_plan"]["current_read"]
            and "real-money path in the methodical test order now stops at paper-evidence review plus a separate human-approved risk-plan discussion rather than status-doc bet sizing" in row_map["cole_status_and_plan"]["current_read"]
            and "methodical-test gates are source-matched to `forward_evidence_scorecard.json` `decision_gate_minimums`" in row_map["cole_status_and_plan"]["current_read"]
            and "treated as future ROI-complete paper-observation floors rather than already-cleared gates" in row_map["cole_status_and_plan"]["current_read"]
            and "current-evidence bridge now requires a combined current-paper read route across `operator_status_context`, `source_freshness` / `requires_refresh_before_right_now_use`, and `operator_read_gate` / `requires_refresh_before_evidence_read`" in row_map["cole_status_and_plan"]["current_read"]
            and "source-readiness metadata rather than performance proof" in row_map["cole_status_and_plan"]["current_read"]
            and "current-evidence bridge still exposes `operator_read_gate` as structured instruction/evidence-read routing before a stale/API-failure top card is used" in row_map["cole_status_and_plan"]["current_read"]
            and "keeps that read gate out of no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, and real-money evidence" in row_map["cole_status_and_plan"]["current_read"]
            and "main status map now routes cross-family current-paper snapshot caveats to the direct cross-family validator" in row_map["cole_status_and_plan"]["current_read"]
            and "main status map now also routes full-data XGBoost retrain questions to `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py` as model-fit reproducibility metadata only rather than paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in row_map["cole_status_and_plan"]["current_read"]
            and "stale one-night setup checklist is now replaced by a current operator-session route" in row_map["cole_status_and_plan"]["current_read"]
            and "uses `./run_daily_portfolio_observation.sh` as the preferred daily primary+shadow wrapper" in row_map["cole_status_and_plan"]["current_read"]
            and "target-track lines now treat OP/CD meet windows as seasonal context and require the current calendar/preflight instead of static active-NOW wording" in row_map["cole_status_and_plan"]["current_read"]
            and "named `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100` decision-change gates" in row_map["cole_status_and_plan"]["current_read"]
            and "preserving primary/shadow recent-run context" in row_map["cole_status_and_plan"]["current_read"]
            and "machine-readable JSON parity" in row_map["cole_status_and_plan"]["current_read"]
            and "current hierarchy language validator" in row_map["cole_status_and_plan"]["current_read"]
            and "direct live-scan targeting / max-races limited-coverage validation route" in row_map["cole_status_and_plan"]["current_read"]
            and "direct live-scan targeting / limited-coverage route plus source-layer paper-trade chain" in row_map["cole_status_and_plan"]["current_read"]
            and "direct full-data retrain validator route" in row_map["cole_status_and_plan"]["current_read"]
            and "live operator route that starts with the matched right-now text/markdown/JSON bundle" in row_map["cole_status_and_plan"]["current_read"]
            and "OP-anchor markdown/JSON source-provenance plus readable-boundary route" in row_map["cole_status_and_plan"]["current_read"]
            and "lifted lane why-now lines" in row_map["cole_status_and_plan"]["current_read"]
            and "stale cards explicitly mark downstream lane details as inherited snapshot context rather than current-day state" in row_map["cole_status_and_plan"]["current_read"]
            and "`--latest-only` and `--skip-top-level` as distinct targeted maintenance modes" in row_map["cole_status_and_plan"]["current_read"]
            and "freshness pinning that now says whether it was actually applied or ignored because top-level outputs were skipped" in row_map["cole_status_and_plan"]["current_read"]
            and "wrapper-leaf source-of-truth note explicit" in row_map["cole_status_and_plan"]["current_read"]
            and "quickstart navigation/read-order machine-readable evidence boundary" in row_map["cole_status_and_plan"]["current_read"]
            and "main status-doc status/map machine-readable evidence boundary" in row_map["cole_status_and_plan"]["current_read"]
            and "machine-readable status-map evidence boundary published as status/read-order/repo-map metadata only" in row_map["cole_status_and_plan"]["current_read"]
            and "report-surfaces route explicit about preserving the README-inherited wrapper-leaf source-of-truth note" in row_map["cole_status_and_plan"]["current_read"]
            and "scorecard implementation/file map now points cold readers at matched text/CSV/JSON surfaces with the frozen source-scope / non-live-evidence boundary, CSV bootstrap-CI source-note columns, machine-readable JSON evidence boundary, machine-readable decision-gate minimums, plus bootstrap-CI source notes and PHASE7/PHASE8 report fingerprints" in row_map["cole_status_and_plan"]["current_read"]
            and "consumes `current_evidence_summary.json.scorecard_audit_route` before routing scorecard gate-floor / tier-first ranking / OP_REFINED CI-only / timezone / no-BAQ prerequisite drift questions to `SCORECARD_RANKING_CONTRACT_AUDIT.md` plus `validate_scorecard_ranking_contract_audit.py` as report-synchronization metadata only" in row_map["cole_status_and_plan"]["current_read"]
            and "current-evidence bridge now also exposes `rebuild_validation_contract` as the settlement-audit -> current-bridge -> current-bridge-validator order after source-byte changes while keeping that order as provenance/rebuild metadata only" in row_map["cole_status_and_plan"]["current_read"]
            and "clean current-bridge rebuild is not enough before report-facing comparison quotes" in row_map["cole_status_and_plan"]["current_read"]
            and "copied-current-paper fanout must run first as snapshot drift prevention only, not evidence movement" in row_map["cole_status_and_plan"]["current_read"]
            and "frozen status/map alignment check, not new forward evidence by itself" in row_map["cole_status_and_plan"]["current_read"],
            "navigation_layer_keeps_read_order_and_honest_expectations",
            "navigation/status-doc rollups still point readers to the right trust anchors, keep routed operator reading paths explicit, surface quickstart-side method-family evidence-debt checklist plus OP-anchor source-provenance plus readable-boundary routing, the live-scan targeting / max-races limited-coverage validator route, daily-guide, operator-runbook current-evidence bridge, and main-status top-card/rebuild reproducibility, preserve the realistic +20-25% expectation, keep the quickstart/status scorecard routes explicit about bootstrap-CI source notes plus PHASE7/PHASE8 report fingerprints as provenance metadata and the named anchor_displacement=30 / phase8_promotion_review=20 / real_money_discussion=100 decision-gate minimums as posture-gate metadata, keep the status-doc OP/CD target-track instructions calendar/preflight-checked rather than static active-NOW text, keep the runbook-side OP-anchor provenance/readable-boundary route plus audit-only fingerprint / boundary-text boundary visible, keep the runbook-side replay-context caution on broader selective-family secondary shadow reads and settlement-audit action-line/no-new-evidence contract visible, keep the daily-guide direct main-comparison route visible for Cole's one-screen OP/CD read before widening to parent research rollups, keep the main-status, quickstart, and daily-guide refresh paths explicit about both the separate `--latest-only` versus `--skip-top-level` maintenance boundaries and whether freshness pinning was actually applied or skipped, keep the main-status route explicit about the quickstart navigation/read-order machine-readable evidence boundary and its own status/map machine-readable evidence boundary, keep the daily-guide route explicit about its own daily navigation/readiness machine-readable evidence boundary, keep the operator runbook on that same separate maintenance-boundary plus applied-vs-skipped freshness-pin honesty, keep the daily-guide wrapper-fallback route pointed at the real daily-wrapper validator including wrapper-generated CURRENT_EVIDENCE_SUMMARY refresh/placeholder and recommendation-context/open-row separation coverage, keep the paper-trade runbook carrying that same wrapper-generated CURRENT_EVIDENCE_SUMMARY refresh/placeholder plus recommendation-context/open-row separation guardrail before Cole-facing current-paper wording, keep the daily-guide route explicit that the direct report-surfaces validator covers shareable wording drift plus the README-inherited wrapper-leaf note the narrative rollup should preserve, keep the quickstart right-now JSON parity and matched text/markdown/JSON refresh route visible, keep the daily-guide PAPER_TRADE_NOW.json sibling and direct right-now-validator parity route visible, keep the wrapper-leaf source-of-truth / inherited-guardrail preservation note visible at the navigation layer, keep the operator runbook on that same source-of-truth wrapper-leaf preservation wording, keep the main-status route explicit that the report-surfaces sweep should preserve the README-inherited wrapper-leaf note rather than flatten it away, keep the runbook-side right-now text/markdown/JSON parity contract visible, keep the main-status right-now JSON parity contract visible, keep the main-status live-operator read order anchored on the matched right-now text/markdown/JSON bundle before broader runbook/audit context, and keep the runbook-side plus main-status top-card/rebuild contract stated positively across the immediate card, rebuilt refresh path, and the navigation-layer quickstart/daily-guide/main-status summaries with routed top-card snapshot inheritance on rebuilt daily summaries while stale cards stay explicitly marked as inherited snapshot context rather than current-day state, while framing the quickstart plus daily/operator umbrella sweeps as alignment/order checks rather than new evidence",
        ),
        require(
            payload_map["validation_quickstart"].get("suite_status") == "pass"
            and payload_map["validation_quickstart"].get("total_checks") == 139
            and payload_map["validation_quickstart"].get("check_count") == 139
            and payload_map["validation_quickstart"].get("valid_evidence_scope") == validation_quickstart.VALID_EVIDENCE_SCOPE
            and isinstance(payload_map["validation_quickstart"].get("scorecard_decision_gate_minimums_read"), dict)
            and payload_map["validation_quickstart"]["scorecard_decision_gate_minimums_read"].get("source") == "forward_evidence_scorecard.json"
            and payload_map["validation_quickstart"]["scorecard_decision_gate_minimums_read"].get("source_path") == "decision_gate_minimums"
            and payload_map["validation_quickstart"]["scorecard_decision_gate_minimums_read"].get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["validation_quickstart"]["scorecard_decision_gate_minimums_read"].get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["validation_quickstart"]["scorecard_decision_gate_minimums_read"].get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["validation_quickstart"]["scorecard_decision_gate_minimums_read"].get("real_money_no_baq_as_bel_required") is True
            and isinstance(payload_map["validation_quickstart"].get("current_evidence_scorecard_ci_only_read"), dict)
            and payload_map["validation_quickstart"]["current_evidence_scorecard_ci_only_read"].get("source") == "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7"
            and payload_map["validation_quickstart"]["current_evidence_scorecard_ci_only_read"].get("candidate_rule_id") == "OP_REFINED_K7"
            and payload_map["validation_quickstart"]["current_evidence_scorecard_ci_only_read"].get("current_anchor_rule_id") == "OP_DURABLE_K7"
            and payload_map["validation_quickstart"]["current_evidence_scorecard_ci_only_read"].get("ci_only_promotion_allowed") is False
            and payload_map["validation_quickstart"]["current_evidence_scorecard_ci_only_read"].get("current_matches_scorecard_diagnostic") is True
            and payload_operator_gate_matches("validation_quickstart")
            and payload_map["validation_quickstart"]["current_evidence_operator_read_gate_read"].get("not_live_profitability_evidence") is True
            and payload_map["validation_quickstart"]["current_evidence_operator_read_gate_read"].get("not_real_money_evidence") is True
            and isinstance(payload_map["validation_quickstart"].get("current_evidence_scorecard_audit_route_read"), dict)
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("source") == "current_evidence_summary.json"
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("source_path") == "scorecard_audit_route"
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("json_path") == "scorecard_ranking_contract_audit.json"
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("real_money_no_baq_as_bel_required") is True
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("artifacts_present") is True
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("not_forward_performance_evidence") is True
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("not_settled_roi_evidence") is True
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("not_promotion_readiness_evidence") is True
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("not_live_profitability_evidence") is True
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("not_bankroll_guidance") is True
            and payload_map["validation_quickstart"]["current_evidence_scorecard_audit_route_read"].get("not_real_money_evidence") is True
            and isinstance(payload_map["validation_quickstart"].get("current_evidence_rebuild_validation_contract_read"), dict)
            and payload_map["validation_quickstart"]["current_evidence_rebuild_validation_contract_read"].get("source") == "current_evidence_summary.json"
            and payload_map["validation_quickstart"]["current_evidence_rebuild_validation_contract_read"].get("source_path") == "rebuild_validation_contract"
            and payload_map["validation_quickstart"]["current_evidence_rebuild_validation_contract_read"].get("prerequisite_rebuild_command") == "python3 paper_trade_settlement_audit.py"
            and payload_map["validation_quickstart"]["current_evidence_rebuild_validation_contract_read"].get("rebuild_command") == "python3 current_evidence_summary.py"
            and payload_map["validation_quickstart"]["current_evidence_rebuild_validation_contract_read"].get("direct_validation_command") == "python3 validate_current_evidence_summary.py"
            and payload_map["validation_quickstart"]["current_evidence_rebuild_validation_contract_read"].get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and payload_map["validation_quickstart"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order_is_provenance_metadata_only") is True
            and payload_map["validation_quickstart"]["current_evidence_rebuild_validation_contract_read"].get("not_settled_roi_or_real_money_evidence") is True
            and isinstance(payload_map["validation_quickstart"].get("source_chain_guardrail_matrix_read"), dict)
            and payload_map["validation_quickstart"]["source_chain_guardrail_matrix_read"].get("source") == "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json"
            and payload_map["validation_quickstart"]["source_chain_guardrail_matrix_read"].get("total_guardrail_checks") == 46
            and payload_map["validation_quickstart"]["source_chain_guardrail_matrix_read"].get("total_fixture_scenarios") == 48
            and isinstance(payload_map["validation_quickstart"].get("evidence_boundary"), dict)
            and payload_map["validation_quickstart"]["evidence_boundary"].get("artifact_role") == "validation quickstart / validator-routing runbook"
            and payload_map["validation_quickstart"]["evidence_boundary"].get("valid_evidence_scope") == validation_quickstart.VALID_EVIDENCE_SCOPE
            and payload_map["validation_quickstart"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["validation_quickstart"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["validation_quickstart"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["validation_quickstart"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["daily_artifact_guide"].get("suite_status") == "pass"
            and payload_map["daily_artifact_guide"].get("valid_evidence_scope") == "daily_artifact_guide_navigation_routing_only"
            and payload_map["daily_artifact_guide"].get("total_checks") == 171
            and payload_map["daily_artifact_guide"].get("check_count") == 171
            and isinstance(payload_map["daily_artifact_guide"].get("evidence_boundary"), dict)
            and payload_map["daily_artifact_guide"]["evidence_boundary"].get("artifact_role") == "daily artifact guide / day-to-day repo-map validator"
            and payload_map["daily_artifact_guide"]["evidence_boundary"].get("valid_evidence_scope") == "daily_artifact_guide_navigation_routing_only"
            and payload_map["daily_artifact_guide"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["daily_artifact_guide"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["daily_artifact_guide"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["daily_artifact_guide"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["daily_artifact_guide"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and payload_map["daily_artifact_guide"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and isinstance(payload_map["daily_artifact_guide"].get("scorecard_decision_gate_minimums_read"), dict)
            and payload_map["daily_artifact_guide"]["scorecard_decision_gate_minimums_read"].get("source") == "forward_evidence_scorecard.json"
            and payload_map["daily_artifact_guide"]["scorecard_decision_gate_minimums_read"].get("source_path") == "decision_gate_minimums"
            and payload_map["daily_artifact_guide"]["scorecard_decision_gate_minimums_read"].get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["daily_artifact_guide"]["scorecard_decision_gate_minimums_read"].get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["daily_artifact_guide"]["scorecard_decision_gate_minimums_read"].get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["daily_artifact_guide"]["scorecard_decision_gate_minimums_read"].get("real_money_no_baq_as_bel_required") is True
            and isinstance(payload_map["daily_artifact_guide"].get("current_evidence_scorecard_ci_only_read"), dict)
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_ci_only_read"].get("source") == "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7"
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_ci_only_read"].get("candidate_rule_id") == "OP_REFINED_K7"
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_ci_only_read"].get("current_anchor_rule_id") == "OP_DURABLE_K7"
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_ci_only_read"].get("ci_only_promotion_allowed") is False
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_ci_only_read"].get("current_matches_scorecard_diagnostic") is True
            and isinstance(payload_map["daily_artifact_guide"].get("current_evidence_scorecard_audit_route_read"), dict)
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("source") == "current_evidence_summary.json"
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("source_path") == "scorecard_audit_route"
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("json_path") == "scorecard_ranking_contract_audit.json"
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("real_money_no_baq_as_bel_required") is True
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("artifacts_present") is True
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("not_forward_performance_evidence") is True
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("not_settled_roi_evidence") is True
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("not_promotion_readiness_evidence") is True
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("not_live_profitability_evidence") is True
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("not_bankroll_guidance") is True
            and payload_map["daily_artifact_guide"]["current_evidence_scorecard_audit_route_read"].get("not_real_money_evidence") is True
            and isinstance(payload_map["daily_artifact_guide"].get("current_evidence_rebuild_validation_contract_read"), dict)
            and payload_map["daily_artifact_guide"]["current_evidence_rebuild_validation_contract_read"].get("source") == "current_evidence_summary.json"
            and payload_map["daily_artifact_guide"]["current_evidence_rebuild_validation_contract_read"].get("source_path") == "rebuild_validation_contract"
            and payload_map["daily_artifact_guide"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order_commands") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and payload_map["daily_artifact_guide"]["current_evidence_rebuild_validation_contract_read"].get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and payload_map["daily_artifact_guide"]["current_evidence_rebuild_validation_contract_read"].get("requires_source_consistency_before_quoting_current_totals") is True
            and payload_map["daily_artifact_guide"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order_is_provenance_metadata_only") is True
            and payload_map["daily_artifact_guide"]["current_evidence_rebuild_validation_contract_read"].get("not_settled_roi_or_real_money_evidence") is True
            and payload_operator_gate_matches("daily_artifact_guide")
            and payload_map["daily_artifact_guide"]["current_evidence_operator_read_gate_read"].get("not_live_profitability_evidence") is True
            and payload_map["daily_artifact_guide"]["current_evidence_operator_read_gate_read"].get("not_real_money_evidence") is True
            and isinstance(payload_map["daily_artifact_guide"].get("source_chain_guardrail_matrix_read"), dict)
            and payload_map["daily_artifact_guide"]["source_chain_guardrail_matrix_read"].get("source") == "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json"
            and payload_map["daily_artifact_guide"]["source_chain_guardrail_matrix_read"].get("total_guardrail_checks") == 46
            and payload_map["daily_artifact_guide"]["source_chain_guardrail_matrix_read"].get("total_fixture_scenarios") == 48
            and payload_map["paper_trade_usage"].get("suite_status") == "pass"
            and payload_map["paper_trade_usage"].get("valid_evidence_scope") == "paper_trade_usage_operator_runbook_navigation_only"
            and payload_map["paper_trade_usage"].get("total_checks") == 65
            and payload_map["paper_trade_usage"].get("check_count") == 65
            and isinstance(payload_map["paper_trade_usage"].get("scorecard_decision_gate_minimums_read"), dict)
            and payload_map["paper_trade_usage"]["scorecard_decision_gate_minimums_read"].get("source") == "forward_evidence_scorecard.json"
            and payload_map["paper_trade_usage"]["scorecard_decision_gate_minimums_read"].get("source_path") == "decision_gate_minimums"
            and payload_map["paper_trade_usage"]["scorecard_decision_gate_minimums_read"].get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["paper_trade_usage"]["scorecard_decision_gate_minimums_read"].get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["paper_trade_usage"]["scorecard_decision_gate_minimums_read"].get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["paper_trade_usage"]["scorecard_decision_gate_minimums_read"].get("real_money_no_baq_as_bel_required") is True
            and isinstance(payload_map["paper_trade_usage"].get("current_evidence_gate_progress_read"), dict)
            and payload_map["paper_trade_usage"]["current_evidence_gate_progress_read"].get("source") == "current_evidence_summary.json"
            and payload_map["paper_trade_usage"]["current_evidence_gate_progress_read"].get("source_path") == "decision_gate_progress"
            and payload_map["paper_trade_usage"]["current_evidence_gate_progress_read"].get("scorecard_source") == "forward_evidence_scorecard.json"
            and payload_map["paper_trade_usage"]["current_evidence_gate_progress_read"].get("scorecard_source_json_path") == "decision_gate_minimums"
            and payload_map["paper_trade_usage"]["current_evidence_gate_progress_read"].get("gate_status") == "all_uncleared"
            and payload_map["paper_trade_usage"]["current_evidence_gate_progress_read"].get("all_gates_ready") is False
            and payload_map["paper_trade_usage"]["current_evidence_gate_progress_read"].get("read") == current_gate_progress_read
            and payload_map["paper_trade_usage"]["current_evidence_gate_progress_read"].get("not_forward_performance_evidence") is True
            and payload_map["paper_trade_usage"]["current_evidence_gate_progress_read"].get("not_promotion_readiness_evidence") is True
            and payload_map["paper_trade_usage"]["current_evidence_gate_progress_read"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_usage"]["current_evidence_gate_progress_read"].get("not_real_money_evidence") is True
            and payload_operator_gate_matches("paper_trade_usage")
            and payload_map["paper_trade_usage"]["current_evidence_operator_read_gate_read"].get("current_top_card_counts_as_bet_readiness_evidence") is False
            and payload_map["paper_trade_usage"]["current_evidence_operator_read_gate_read"].get("current_top_card_counts_as_settled_roi_evidence") is False
            and payload_map["paper_trade_usage"]["current_evidence_operator_read_gate_read"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_usage"]["current_evidence_operator_read_gate_read"].get("not_real_money_evidence") is True
            and isinstance(payload_map["paper_trade_usage"].get("current_evidence_scorecard_audit_route_read"), dict)
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("source") == "current_evidence_summary.json"
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("source_path") == "scorecard_audit_route"
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("json_path") == "scorecard_ranking_contract_audit.json"
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("real_money_no_baq_as_bel_required") is True
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("artifacts_present") is True
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("not_forward_performance_evidence") is True
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("not_settled_roi_evidence") is True
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("not_promotion_readiness_evidence") is True
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("not_bankroll_guidance") is True
            and payload_map["paper_trade_usage"]["current_evidence_scorecard_audit_route_read"].get("not_real_money_evidence") is True
            and isinstance(payload_map["paper_trade_usage"].get("current_evidence_rebuild_validation_contract_read"), dict)
            and payload_map["paper_trade_usage"]["current_evidence_rebuild_validation_contract_read"].get("source") == "current_evidence_summary.json"
            and payload_map["paper_trade_usage"]["current_evidence_rebuild_validation_contract_read"].get("source_path") == "rebuild_validation_contract"
            and payload_map["paper_trade_usage"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order_commands") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and payload_map["paper_trade_usage"]["current_evidence_rebuild_validation_contract_read"].get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and payload_map["paper_trade_usage"]["current_evidence_rebuild_validation_contract_read"].get("requires_source_consistency_before_quoting_current_totals") is True
            and payload_map["paper_trade_usage"]["current_evidence_rebuild_validation_contract_read"].get("requires_source_freshness_before_right_now_instruction_use") is True
            and payload_map["paper_trade_usage"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order_is_provenance_metadata_only") is True
            and payload_map["paper_trade_usage"]["current_evidence_rebuild_validation_contract_read"].get("not_settled_roi_or_real_money_evidence") is True
            and isinstance(payload_map["paper_trade_usage"].get("source_chain_guardrail_matrix_read"), dict)
            and payload_map["paper_trade_usage"]["source_chain_guardrail_matrix_read"].get("source") == "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json"
            and payload_map["paper_trade_usage"]["source_chain_guardrail_matrix_read"].get("total_guardrail_checks") == 46
            and payload_map["paper_trade_usage"]["source_chain_guardrail_matrix_read"].get("total_fixture_scenarios") == 48
            and isinstance(payload_map["paper_trade_usage"].get("evidence_boundary"), dict)
            and payload_map["paper_trade_usage"]["evidence_boundary"].get("artifact_role") == "paper-trade usage / operator workflow runbook validator"
            and payload_map["paper_trade_usage"]["evidence_boundary"].get("valid_evidence_scope") == "paper_trade_usage_operator_runbook_navigation_only"
            and payload_map["paper_trade_usage"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["paper_trade_usage"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["paper_trade_usage"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["paper_trade_usage"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["cole_status_and_plan"].get("suite_status") == "pass"
            and payload_map["cole_status_and_plan"].get("total_checks") == 64
            and payload_map["cole_status_and_plan"].get("check_count") == 64
            and isinstance(payload_map["cole_status_and_plan"].get("scorecard_decision_gate_minimums_read"), dict)
            and payload_map["cole_status_and_plan"]["scorecard_decision_gate_minimums_read"].get("source") == "forward_evidence_scorecard.json"
            and payload_map["cole_status_and_plan"]["scorecard_decision_gate_minimums_read"].get("source_path") == "decision_gate_minimums"
            and payload_map["cole_status_and_plan"]["scorecard_decision_gate_minimums_read"].get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["cole_status_and_plan"]["scorecard_decision_gate_minimums_read"].get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["cole_status_and_plan"]["scorecard_decision_gate_minimums_read"].get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["cole_status_and_plan"]["scorecard_decision_gate_minimums_read"].get("real_money_no_baq_as_bel_required") is True
            and isinstance(payload_map["cole_status_and_plan"].get("current_evidence_scorecard_audit_route_read"), dict)
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("source") == "current_evidence_summary.json"
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("source_path") == "scorecard_audit_route"
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("json_path") == "scorecard_ranking_contract_audit.json"
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("gate_floor_snapshot", {}).get("real_money_no_baq_as_bel_required") is True
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("artifacts_present") is True
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("not_forward_performance_evidence") is True
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("not_settled_roi_evidence") is True
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("not_promotion_readiness_evidence") is True
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("not_live_profitability_evidence") is True
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("not_bankroll_guidance") is True
            and payload_map["cole_status_and_plan"]["current_evidence_scorecard_audit_route_read"].get("not_real_money_evidence") is True
            and isinstance(payload_map["cole_status_and_plan"].get("current_evidence_gate_progress_read"), dict)
            and payload_map["cole_status_and_plan"]["current_evidence_gate_progress_read"].get("source") == "current_evidence_summary.json"
            and payload_map["cole_status_and_plan"]["current_evidence_gate_progress_read"].get("source_path") == "decision_gate_progress"
            and payload_map["cole_status_and_plan"]["current_evidence_gate_progress_read"].get("gate_status") == "all_uncleared"
            and payload_map["cole_status_and_plan"]["current_evidence_gate_progress_read"].get("read") == current_gate_progress_read
            and payload_map["cole_status_and_plan"]["current_evidence_gate_progress_read"].get("not_forward_performance_evidence") is True
            and payload_map["cole_status_and_plan"]["current_evidence_gate_progress_read"].get("not_promotion_readiness_evidence") is True
            and payload_map["cole_status_and_plan"]["current_evidence_gate_progress_read"].get("not_live_profitability_evidence") is True
            and payload_map["cole_status_and_plan"]["current_evidence_gate_progress_read"].get("not_real_money_evidence") is True
            and payload_operator_gate_matches("cole_status_and_plan")
            and payload_map["cole_status_and_plan"]["current_evidence_operator_read_gate_read"].get("not_live_profitability_evidence") is True
            and payload_map["cole_status_and_plan"]["current_evidence_operator_read_gate_read"].get("not_real_money_evidence") is True
            and isinstance(payload_map["cole_status_and_plan"].get("current_evidence_rebuild_validation_contract_read"), dict)
            and payload_map["cole_status_and_plan"]["current_evidence_rebuild_validation_contract_read"].get("source") == "current_evidence_summary.json"
            and payload_map["cole_status_and_plan"]["current_evidence_rebuild_validation_contract_read"].get("source_path") == "rebuild_validation_contract"
            and payload_map["cole_status_and_plan"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order_commands") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and payload_map["cole_status_and_plan"]["current_evidence_rebuild_validation_contract_read"].get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and payload_map["cole_status_and_plan"]["current_evidence_rebuild_validation_contract_read"].get("requires_source_consistency_before_quoting_current_totals") is True
            and payload_map["cole_status_and_plan"]["current_evidence_rebuild_validation_contract_read"].get("requires_source_freshness_before_right_now_instruction_use") is True
            and payload_map["cole_status_and_plan"]["current_evidence_rebuild_validation_contract_read"].get("upstream_refresh_order_is_provenance_metadata_only") is True
            and payload_map["cole_status_and_plan"]["current_evidence_rebuild_validation_contract_read"].get("not_settled_roi_or_real_money_evidence") is True
            and isinstance(payload_map["cole_status_and_plan"].get("evidence_boundary"), dict)
            and payload_map["cole_status_and_plan"]["evidence_boundary"].get("artifact_role") == "main status / repo-map validator"
            and payload_map["cole_status_and_plan"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["cole_status_and_plan"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["cole_status_and_plan"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["cole_status_and_plan"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True,
            "navigation_layer_validators_publish_explicit_total_checks",
            "the quickstart, daily guide, operator runbook, and main-status validators now publish explicit top-level total_checks alongside check_count; the quickstart, daily guide, operator runbook, and main-status validators now also publish scorecard-sourced 30/20/100 gate minimums with the no-BAQ-as-BEL prerequisite, the quickstart, daily guide, operator runbook, and main-status validators now fixture-test non-positive Phase 8 and real-money scorecard floors before writing artifacts, the main-status validator now publishes the bridge-owned current_evidence_summary.json scorecard_audit_route, the operator runbook and main-status validators now publish the current-evidence decision_gate_progress read as all-uncleared routing metadata, the quickstart, daily guide, operator runbook, and main-status validators now publish the structured current-evidence operator_read_gate read with issue booleans as instruction/evidence-read routing metadata, the daily guide, operator runbook, and main-status validators now publish the bridge-owned rebuild_validation_contract order as provenance metadata, the quickstart, daily guide, operator runbook, README landing-page, and main-status validators now fixture-test malformed current-evidence rebuild contracts before writing artifacts, the daily guide publishes project-local fixture scratch metadata through a named child check, and the quickstart, daily guide, operator runbook, plus main-status validators now publish their own machine-readable navigation/status-map evidence boundaries, so the top-level project sweep does not have to treat check_count alone as the full navigation/status-doc scope contract",
        ),
        require(
            row_map["validation_quickstart"].get("child_check_count") == 139
            and isinstance(row_map["validation_quickstart"].get("child_checks"), list)
            and {check.get("check") for check in row_map["validation_quickstart"]["child_checks"]} == {
                "quickstart_row_present",
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "scorecard_boolean_floor_fails_before_artifacts",
                "scorecard_nonpositive_phase8_floor_fails_before_artifacts",
                "scorecard_nonpositive_real_money_floor_fails_before_artifacts",
                "scorecard_missing_no_baq_fails_before_artifacts",
                "report_surfaces_row_present",
                "decision_cards_suite_row_present",
                "op_family_row_present",
                "cross_family_row_present",
                "portfolio_decision_row_present",
                "method_family_row_present",
                "frozen_evidence_row_present",
                "frozen_chain_full_data_retrain_guardrail_present",
                "scorecard_ranking_contract_audit_row_present",
                "frozen_portfolio_eval_row_present",
                "phase8_report_row_present",
                "compare_main_row_present",
                "compare_main_evidence_debt_ladder_note_present",
                "op_anchor_row_present",
                "ab_downstream_row_present",
                "full_data_retrain_row_present",
                "recommender_scope_row_present",
                "paper_trade_pipeline_row_present",
                "paper_trade_recommender_row_present",
                "ev_ticket_engine_row_present",
                "paper_trade_logger_row_present",
                "paper_trade_source_chain_row_present",
                "source_chain_shortcut_present",
                "source_chain_guardrail_count_matches_matrix_json",
                "disk_space_preflight_present",
                "cleanup_helper_safety_scope_present",
                "paper_trade_operator_suite_row_present",
                "paper_trade_now_row_present",
                "current_evidence_summary_row_present",
                "current_evidence_combined_operator_read_route",
                "current_evidence_ci_only_diagnostic_route",
                "current_evidence_scorecard_audit_route",
                "current_evidence_operator_read_gate_route",
                "current_evidence_structured_freshness_state_route",
                "current_evidence_quickstart_uses_bridge_published_gates",
                "current_bridge_rebuild_order_documented",
                "current_hierarchy_row_present",
                "daily_wrapper_row_present",
                "preflight_note_row_present",
                "status_summary_row_present",
                "settlement_sync_row_present",
                "settlement_helper_row_present",
                "next_steps_row_present",
                "forward_check_row_present",
                "lane_monitor_row_present",
                "daily_summary_row_present",
                "refresh_helper_row_present",
                "saved_live_refresh_note_present",
                "daily_wrapper_leaf_guardrail_note_present",
                "lane_summary_row_present",
                "ops_history_row_present",
                "daily_guide_row_present",
                "paper_trade_usage_row_present",
                "cole_status_row_present",
                "cole_status_api_access_route_read_order",
                "working_status_row_present",
                "presentation_outline_row_present",
                "broad_change_row",
                "compare_main_ladder_step",
                "current_bridge_fanout_ladder_step",
                "report_surfaces_ladder_step",
                "three_main_layers_command_set",
                "reuse_existing_child_json_command_set",
                "reuse_existing_child_json_guardrail",
                "quickstart_gate_source_matches_scorecard_json",
                "navigation_command_set",
                "dated_report_policy_html_anchor",
                "dated_report_policy_dated_pdf",
                "html_policy_legacy_alias",
                "dated_report_policy_pdf_legacy_alias",
                "settlement_sync_green_read",
                "settlement_helper_green_read",
                "source_layer_green_read",
                "xgboost_green_read",
                "full_data_retrain_green_read",
                "broad_change_read_order_top",
                "frozen_chain_read_order",
                "narrow_comparison_read_order",
                "compare_main_read_order",
                "cross_family_current_paper_read_order",
                "ab_downstream_current_paper_read_order",
                "full_data_retrain_read_order",
                "recommender_scope_read_order",
                "recommender_scope_modeled_ev_boundary_present",
                "paper_trade_now_read_order",
                "current_evidence_summary_read_order",
                "daily_wrapper_read_order",
                "preflight_note_read_order",
                "status_summary_read_order",
                "settlement_sync_read_order",
                "settlement_helper_read_order",
                "next_steps_read_order",
                "forward_check_read_order",
                "lane_monitor_read_order",
                "daily_summary_read_order",
                "lane_summary_read_order",
                "report_surface_read_order",
                "navigation_read_order",
                "source_layer_read_order",
                "shared_report_pattern_wording",
                "op_family_output_path_documented",
                "cross_family_output_path_documented",
                "portfolio_decision_output_path_documented",
                "method_family_output_path_documented",
                "compare_main_output_path_documented",
                "frozen_portfolio_eval_output_path_documented",
                "phase8_report_output_path_documented",
                "full_data_retrain_output_path_documented",
                "paper_trade_pipeline_output_path_documented",
                "paper_trade_recommender_output_path_documented",
                "ev_ticket_engine_output_path_documented",
                "paper_trade_logger_output_path_documented",
                "paper_trade_source_chain_output_path_documented",
                "paper_trade_now_output_path_documented",
                "current_evidence_summary_output_path_documented",
                "current_hierarchy_output_path_documented",
                "daily_wrapper_output_path_documented",
                "preflight_note_output_path_documented",
                "status_summary_output_path_documented",
                "settlement_sync_output_path_documented",
                "settlement_helper_output_path_documented",
                "next_steps_output_path_documented",
                "forward_check_output_path_documented",
                "lane_monitor_output_path_documented",
                "daily_summary_output_path_documented",
                "lane_summary_output_path_documented",
                "ops_history_output_path_documented",
                "quickstart_output_path_documented",
                "referenced_validator_scripts_exist",
                "referenced_human_facing_artifacts_exist",
                "validation_quickstart_json_publishes_machine_readable_evidence_boundary",
                "documented_output_paths_exist",
            }
            and row_map["daily_artifact_guide"].get("child_check_count") == 171
            and isinstance(row_map["daily_artifact_guide"].get("child_checks"), list)
            and {check.get("check") for check in row_map["daily_artifact_guide"]["child_checks"]} == {
                "latest_preflight_prefers_json_when_text_blank",
                "latest_preflight_prefers_nonblank_text",
                "current_evidence_context_reads_fresh_branch",
                "current_evidence_context_reads_stale_branch",
                "current_evidence_context_reads_closed_queue_branch",
                "current_evidence_refresh_accounting_fails_before_artifacts",
                "current_evidence_ci_only_missing_fails_before_artifacts",
                "current_evidence_scorecard_audit_route_missing_fails_before_artifacts",
                "current_evidence_rebuild_order_missing_fails_before_artifacts",
                "current_evidence_rebuild_order_weakened_fails_before_artifacts",
                "decision_gate_boolean_floor_fails_before_artifacts",
                "decision_gate_nonpositive_phase8_floor_fails_before_artifacts",
                "decision_gate_nonpositive_real_money_floor_fails_before_artifacts",
                "decision_gate_missing_no_baq_fails_before_artifacts",
                "guide_matches_generator",
                "legacy_phase7_current_paper_entrypoint_wording",
                "validation_section_present",
                "daily_guide_source_exposes_valid_evidence_scope",
                "source_chain_matrix_shortcut_present",
                "source_chain_guardrail_count_matches_matrix_json",
                "current_hierarchy_validator_command",
                "scorecard_validator_command",
                "current_evidence_validator_command",
                "preflight_note_ladder_step",
                "preflight_note_validator_command",
                "status_summary_ladder_step",
                "status_summary_validator_command",
                "settlement_sync_ladder_step",
                "settlement_sync_validator_command",
                "settlement_helper_ladder_step",
                "settlement_helper_validator_command",
                "next_steps_ladder_step",
                "next_steps_validator_command",
                "forward_check_ladder_step",
                "forward_check_validator_command",
                "lane_monitor_ladder_step",
                "lane_monitor_validator_command",
                "daily_summary_ladder_step",
                "daily_summary_validator_command",
                "lane_summary_ladder_step",
                "lane_summary_validator_command",
                "operator_suite_alignment_note",
                "refresh_helper_ladder_step",
                "daily_wrapper_leaf_guardrail_note_present",
                "refresh_helper_not_new_evidence_note",
                "narrow_comparison_ladder_step",
                "compare_main_validator_command",
                "op_anchor_validator_command",
                "cross_family_current_paper_validator_command",
                "ab_downstream_validator_command",
                "full_data_retrain_validator_command",
                "recommender_scope_validator_command",
                "current_bridge_fanout_ladder_note",
                "reuse_shortcut_ladder_note",
                "working_status_ladder_step",
                "working_status_validator_command",
                "report_surfaces_ladder_step",
                "report_surfaces_validator_command",
                "quickstart_ladder_step",
                "quickstart_validator_command",
                "project_surfaces_ladder_step",
                "project_surfaces_validator_command",
                "project_surfaces_alignment_note",
                "latest_run_root_line",
                "quiet_vs_broken_section_present",
                "decision_gate_source_section_present",
                "daily_guide_gate_source_matches_scorecard_json",
                "quiet_vs_broken_true_quiet_rule",
                "quiet_vs_broken_preflight_guardrail",
                "quiet_vs_broken_incomplete_data_rule",
                "quiet_vs_broken_pipeline_failure_rule",
                "quiet_vs_broken_issue_rule",
                "quiet_vs_broken_triage_rule",
                "latest_run_root_exists",
                "latest_run_sidecars_exist",
                "green_read_present",
                "green_read_scorecard_first",
                "green_read_current_evidence_bridge",
                "green_read_current_evidence_discoverability",
                "green_read_compare_main_discoverability",
                "green_read_cross_family_current_paper_discoverability",
                "green_read_source_layer_discoverability",
                "paper_trade_now_daily_entry",
                "current_evidence_daily_entry",
                "main_status_api_access_route_discoverable",
                "current_evidence_recommendation_context_branch_is_current",
                "current_evidence_ci_only_route",
                "current_evidence_scorecard_audit_route",
                "current_evidence_rebuild_order_route",
                "current_evidence_combined_operator_route",
                "latest_daily_summary_entry_present",
                "forward_scorecard_entry_present",
                "scorecard_audit_entry_present",
                "scorecard_audit_validator_entry_present",
                "current_evidence_validator_entry_present",
                "current_evidence_validator_entry_uses_queue_state_wording",
                "compare_main_entry_present",
                "compare_main_validator_entry_present",
                "quickstart_entry_present",
                "quickstart_validator_entry_present",
                "paper_trade_usage_runbook_entry_present",
                "source_chain_matrix_entry_present",
                "pipeline_validator_entry_present",
                "recommender_validator_entry_present",
                "live_scanner_usage_entry_present",
                "ev_ticket_engine_usage_entry_present",
                "ev_ticket_engine_validator_entry_present",
                "logger_validator_entry_present",
                "preflight_note_validator_entry_present",
                "status_summary_validator_entry_present",
                "current_hierarchy_validator_entry_present",
                "settlement_sync_validator_entry_present",
                "settlement_helper_validator_entry_present",
                "next_steps_validator_entry_present",
                "forward_check_validator_entry_present",
                "lane_monitor_validator_entry_present",
                "daily_summary_validator_entry_present",
                "lane_summary_validator_entry_present",
                "refresh_helper_entry_present",
                "refresh_helper_validator_entry_present",
                "daily_wrapper_validator_entry_present",
                "working_status_entry_present",
                "working_status_validator_entry_present",
                "report_surfaces_validator_entry_present",
                "op_family_entry_present",
                "op_family_validator_entry_present",
                "cross_family_entry_present",
                "cross_family_validator_entry_present",
                "portfolio_decision_entry_present",
                "portfolio_decision_validator_entry_present",
                "method_family_entry_present",
                "method_family_validator_entry_present",
                "op_anchor_entry_present",
                "ab_downstream_entry_present",
                "full_data_retrain_entry_present",
                "full_data_retrain_validator_entry_present",
                "recommender_scope_entry_present",
                "phase7_report_entry_present",
                "phase7_report_caution_validator_entry_present",
                "green_read_preflight_note_discoverability",
                "green_read_status_summary_discoverability",
                "green_read_current_hierarchy_discoverability",
                "green_read_settlement_sync_discoverability",
                "green_read_settlement_helper_discoverability",
                "green_read_next_steps_discoverability",
                "green_read_forward_check_discoverability",
                "green_read_lane_monitor_discoverability",
                "green_read_daily_summary_discoverability",
                "green_read_lane_summary_discoverability",
                "green_read_refresh_discoverability",
                "green_read_daily_wrapper_discoverability",
                "green_read_working_status_discoverability",
                "green_read_report_surfaces_discoverability",
                "green_read_report_alias_policy",
                "green_read_narrow_discoverability",
                "green_read_full_data_retrain_discoverability",
                "backtest_report_caution_validator_entry_present",
                "walk_forward_validation_caution_validator_entry_present",
                "phase7_report_caution_validator_entry_present",
                "phase8_report_caution_validator_entry_present",
                "diagnose_cd_selection_caution_validator_entry_present",
                "selector_experiment_caution_validator_entry_present",
                "sample_size_experiment_caution_validator_entry_present",
                "green_read_reuse_shortcut_discoverability",
                "daily_path_bottom_line",
                "research_path_bottom_line",
                "anchor_bottom_line",
                "top_level_preflight_scratch_not_daily_driver",
                "daily_artifact_guide_json_publishes_machine_readable_evidence_boundary",
                "fixture_scratch_root_project_local",
                "fixture_scratch_metadata_published",
                "core_daily_and_decision_artifacts_exist",
            }
            and row_map["paper_trade_usage"].get("child_check_count") == 65
            and isinstance(row_map["paper_trade_usage"].get("child_checks"), list)
            and {check.get("check") for check in row_map["paper_trade_usage"]["child_checks"]} == {
                "scorecard_boolean_floor_fails_before_artifacts",
                "scorecard_nonpositive_phase8_floor_fails_before_artifacts",
                "scorecard_nonpositive_real_money_floor_fails_before_artifacts",
                "scorecard_missing_no_baq_fails_before_artifacts",
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "workflow_not_proof_frame",
                "paper_trade_usage_valid_evidence_scope_visible",
                "evidence_sources_named",
                "cross_family_current_paper_route_documented",
                "main_status_api_access_route_documented",
                "current_evidence_bridge_route_documented",
                "current_bridge_rebuild_order_documented",
                "current_bridge_copied_current_fanout_documented",
                "current_evidence_combined_operator_read_route_documented",
                "current_evidence_scorecard_audit_route_documented",
                "scorecard_gate_source_documented_for_operator_runbook",
                "scorecard_audit_gate_route_documented",
                "current_evidence_source_freshness_route_documented",
                "current_evidence_structured_freshness_state_route_documented",
                "current_evidence_operator_read_gate_route_documented",
                "op_anchor_start_command",
                "primary_and_daily_commands",
                "deployment_order_guardrails",
                "cd_companion_not_anchor_section",
                "op_refined_shadow_only_section",
                "operator_suite_route",
                "source_chain_matrix_route_documented",
                "source_chain_guardrail_count_matches_matrix_json",
                "paper_trade_now_inventory_uses_stronger_context_why_wording",
                "refresh_helper_inventory_documented",
                "refresh_helper_not_evidence_note_documented",
                "wrapper_leaf_guardrail_route_documented",
                "refresh_helper_as_of_date_documented",
                "quickstart_alias_policy_documented",
                "working_status_route_present",
                "working_status_route_documented",
                "report_surfaces_route_present",
                "report_surfaces_route_documented",
                "project_sweep_route_present",
                "missing_operator_validators_restored",
                "status_summary_contract_documented",
                "scanner_sidecar_resolution_contract_documented",
                "refresh_helper_direct_validator_note",
                "settlement_sync_route_documented",
                "settlement_helper_route_documented",
                "settlement_audit_contract_documented",
                "daily_wrapper_route_documented",
                "next_steps_contract_documented",
                "right_now_quick_read_bundle_documented",
                "daily_summary_helper_bundle_documented",
                "self_validator_note",
                "quickstart_revalidation_note",
                "reuse_shortcut_documented",
                "daily_surface_inventory",
                "top_level_preflight_scratch_cache_boundary",
                "pipeline_status_contract",
                "quiet_vs_broken_day_contract",
                "pipeline_failure_sidecar_contract_documented",
                "expanded_navigation_bundle_contracts_documented",
                "named_operator_artifacts_exist",
                "named_operator_validators_exist",
                "named_validation_outputs_exist",
                "paper_trade_usage_json_publishes_machine_readable_evidence_boundary",
                "paper_trade_usage_summary_explicitly_stays_navigation_not_new_evidence",
            }
            and row_map["cole_status_and_plan"].get("child_check_count") == 64
            and isinstance(row_map["cole_status_and_plan"].get("child_checks"), list)
            and {check.get("check") for check in row_map["cole_status_and_plan"]["child_checks"]} == {
                "scorecard_boolean_floor_fails_before_artifacts",
                "scorecard_nonpositive_phase8_floor_fails_before_artifacts",
                "scorecard_nonpositive_real_money_floor_fails_before_artifacts",
                "scorecard_missing_no_baq_fails_before_artifacts",
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "main_sections_present",
                "tldr_realistic_roi_guardrail",
                "tldr_phase7_split_note",
                "phase7_beats_phase8_key_insight",
                "phase7_holdout_row_split",
                "phase8_holdout_row_split",
                "phase7_vs_phase8_split_key_insight",
                "op_anchor_tier1_row",
                "cd_core_tier1_row",
                "realistic_roi_range_row",
                "conservative_roi_range_row",
                "tldr_wrapper_operational_with_tiny_settled_sample",
                "paper_trade_infra_operational_with_pre_evidence_settlements",
                "paper_trade_observation_gap_not_rule_tuning",
                "step1_sample_collection_not_decision_grade",
                "methodical_test_gates_source_matched_to_scorecard",
                "scorecard_audit_gate_route_documented",
                "current_evidence_scorecard_audit_route_present",
                "target_tracks_are_calendar_checked_not_static_now",
                "real_money_path_deferred_to_separate_review",
                "next_operator_session_uses_current_wrapper",
                "legacy_tonight_checklist_removed",
                "baq_context_present",
                "baq_bridge_dead_end",
                "baq_aliasing_guardrail",
                "evidence_reading_order_present",
                "full_data_retrain_evidence_route_present",
                "cross_family_current_paper_route_present",
                "operator_reading_order_present",
                "current_evidence_counts_match_bridge_json",
                "closed_queue_does_not_render_none_as_open_identity",
                "current_evidence_combined_operator_read_route_present",
                "current_evidence_operator_read_gate_route_present",
                "current_evidence_rebuild_order_route_present",
                "current_bridge_copied_current_fanout_documented",
                "validation_reading_order_present",
                "full_data_retrain_validation_route_present",
                "validation_reuse_shortcut_present",
                "self_validator_row_present",
                "paper_trade_now_validator_row_present",
                "current_hierarchy_validator_row_present",
                "quickstart_row_present",
                "quickstart_validator_row_present",
                "daily_guide_validator_row_present",
                "paper_trade_usage_row_present",
                "project_surfaces_scope_row_present",
                "working_status_validator_row_present",
                "named_main_repo_artifacts_exist",
                "named_validation_outputs_exist",
                "report_and_guardrail_rows_present",
                "report_surfaces_row_preserves_wrapper_leaf_note",
                "named_report_and_rule_artifacts_exist",
                "paper_trade_helper_rows_present",
                "named_operator_helper_artifacts_exist",
                "status_doc_wrapper_leaf_source_of_truth_note_present",
                "status_doc_base_api_access_route_documented",
                "cole_status_summary_explicitly_stays_status_not_new_evidence",
                "cole_status_json_publishes_machine_readable_evidence_boundary",
            },
            "navigation_layer_publishes_structured_child_checks",
            "navigation/status-doc layer now has to publish the exact quickstart, daily-guide, runbook, and main-status structured check sets — including the quickstart method-family evidence-debt checklist route, the refresh helper's separate latest-only versus skip-top-level maintenance-boundary documentation plus the as-of-date guardrail, the main-status target-track calendar/preflight guardrail, and the main-status wrapper-leaf / report-surfaces inheritance notes — instead of only summary strings",
        ),
    ]

    checks.append(
        require(
            row_map["current_hierarchy_language"].get("child_check_count") == 19
            and isinstance(row_map["current_hierarchy_language"].get("child_checks"), list)
            and {check.get("check") for check in row_map["current_hierarchy_language"]["child_checks"]} == {
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "current_surface_files_exist",
                "no_stale_non_anchor_shadow_wording_in_current_surfaces",
                "primary_paper_basket_companion_wording_present",
                "json_legacy_primary_shadow_has_primary_companion",
                "top_card_hierarchy_contract",
                "current_evidence_json_preserves_hierarchy_boundary",
                "current_evidence_json_source_gate_status_is_current",
                "current_evidence_json_publishes_rebuild_validation_contract",
                "scorecard_decision_gates_preserve_hierarchy_boundary",
                "settlement_audit_json_preserves_hierarchy_boundary",
                "source_chain_matrix_json_preserves_hierarchy_boundary",
                "rule_file_notes_preserve_preflight_and_historical_evidence_language",
                "cross_family_structured_legacy_rank_is_compatible",
                "front_door_current_hierarchy_route_present",
                "daily_guide_current_hierarchy_route_present",
                "current_hierarchy_json_publishes_machine_readable_evidence_boundary",
                "current_hierarchy_report_exposes_valid_evidence_scope",
            }
            and isinstance(payload_map["current_hierarchy_language"].get("evidence_boundary"), dict)
            and payload_map["current_hierarchy_language"]["evidence_boundary"].get("artifact_role") == "current hierarchy wording / structured-key compatibility validator"
            and payload_map["current_hierarchy_language"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["current_hierarchy_language"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["current_hierarchy_language"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["current_hierarchy_language"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["current_hierarchy_language"]["evidence_boundary"].get("not_anchor_change_evidence") is True
            and payload_map["current_hierarchy_language"]["evidence_boundary"].get("not_companion_change_evidence") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("anchor") == "OP_DURABLE_K7"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("anchor_tier") == "ANCHOR"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("primary_companion") == "CD_CORE_K8"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("primary_companion_tier") == "PAPER"
            and "primary OP/CD paper-basket companion" in str(payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("primary_companion_read") or "")
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("same_family_shadow_watch") == "OP_REFINED_K7"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("same_family_shadow_watch_tier") == "WATCH"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("anchor_gap_anchor_rule_id") == "OP_DURABLE_K7"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("anchor_gap_companion_rule_id") == "CD_CORE_K8"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("anchor_gap_anchor_rows") == 0
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("anchor_gap_companion_rows") > 0
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("anchor_gap_floor") == 30
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("anchor_gap_rows_needed") == 30
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("anchor_gap_anchor_rows") + payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("anchor_gap_rows_needed") == payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("anchor_gap_floor")
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("anchor_gap_current_sample_is_cd_only") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("anchor_gap_companion_rows_count_as_anchor_evidence") is False
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("anchor_gap_not_forward_performance_evidence") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("open_queue_anchor_rule_id") == "OP_DURABLE_K7"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("open_queue_companion_rule_id") == "CD_CORE_K8"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("open_queue_total_open_rows") == payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("open_queue_companion_open_rows")
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("open_queue_anchor_open_rows") == 0
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("open_queue_current_open_queue_is_cd_only") == (
                payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("open_queue_total_open_rows") > 0
                and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("open_queue_anchor_open_rows") == 0
                and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("open_queue_companion_open_rows")
                == payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("open_queue_total_open_rows")
            )
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("open_queue_open_rows_count_as_roi_complete") is False
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("open_queue_open_rows_count_as_anchor_evidence") is False
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("open_queue_not_forward_performance_evidence") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("not_new_forward_evidence") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("not_live_profitability_evidence") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("not_promotion_readiness_evidence") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("not_real_money_evidence") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("source_consistency_overall_match") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("primary_roi_complete_rows_match") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("primary_open_rows_match") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("primary_incomplete_rows_match") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("primary_roi_gap_rows_match") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("primary_cost_return_sums_match") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("primary_settled_ts_gap_rows_clear") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("source_freshness_state_valid") is True
            and isinstance(payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("source_freshness_state"), str)
            and isinstance(payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("source_stale_vs_generated_date"), bool)
            and isinstance(payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("requires_refresh_before_right_now_use"), bool)
            and isinstance(payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("refresh_age_days"), int)
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("refresh_boundary_command") == "./run_daily_portfolio_observation.sh"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("refresh_boundary_required_before_right_now_instruction_use") == payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("requires_refresh_before_right_now_use")
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("refresh_boundary_can_update_operator_surfaces") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("refresh_boundary_can_settle_open_rows_by_itself") is False
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("refresh_boundary_counts_as_roi_complete_evidence_by_itself") is False
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("refresh_boundary_clean_empty_counts_as_forward_performance") is False
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("refresh_boundary_missing_or_invalid_artifact_counts_as_clean_quiet_day") is False
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("refresh_boundary_not_forward_performance_evidence") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("refresh_boundary_not_real_money_evidence") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("refresh_route_safe") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("decision_gate_source") == "forward_evidence_scorecard.json"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("decision_gate_source_loaded") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("anchor_displacement_min") == 30
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("phase8_promotion_review_min") == 20
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("real_money_discussion_min") == 100
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("decision_gate_scorecard_source") == "forward_evidence_scorecard.json"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("decision_gate_source_values_match_scorecard") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("decision_gate_effective_values_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("decision_gate_missing_top_card_fields") == []
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("decision_gate_mismatched_fields") == []
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("effective_anchor_displacement_min") == 30
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("effective_phase8_promotion_review_min") == 20
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("effective_real_money_discussion_min") == 100
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("top_card_anchor_displacement_min") == 30
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("top_card_phase8_promotion_review_min") == 20
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("top_card_real_money_discussion_min") == 100
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("scorecard_anchor_displacement_min") == 30
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("scorecard_phase8_promotion_review_min") == 20
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("scorecard_real_money_discussion_min") == 100
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("decision_gate_anchor_threshold_source") == "forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("decision_gate_phase8_threshold_source") == "forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("decision_gate_real_money_threshold_source") == "forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("rebuild_contract_source") == "current_evidence_summary.json:rebuild_validation_contract"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("rebuild_upstream_refresh_order") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("rebuild_prerequisite_command") == "python3 paper_trade_settlement_audit.py"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("rebuild_command") == "python3 current_evidence_summary.py"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("rebuild_direct_validation_command") == "python3 validate_current_evidence_summary.py"
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("rebuild_requires_settlement_audit_refresh") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("rebuild_requires_source_consistency") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("rebuild_requires_source_freshness_before_right_now_instruction_use") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("rebuild_green_checks_metadata_only") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("rebuild_order_provenance_metadata_only") is True
            and payload_map["current_hierarchy_language"].get("current_evidence_json_read", {}).get("rebuild_not_settled_roi_or_real_money_evidence") is True
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("artifact_status") == "pass"
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("gate_source") == "forward_evidence_scorecard.json"
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("gate_source_loaded") is True
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("gate_fallback_used") is False
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("anchor_displacement_min") == 30
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("phase8_promotion_review_min") == 20
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("real_money_discussion_min") == 100
            and "OP_DURABLE_K7" in str(payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("primary_role") or "")
            and "CD_CORE_K8" in str(payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("primary_role") or "")
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("primary_active_first_read_gate") == "anchor_displacement"
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("primary_active_first_read_scope") == "lane_total_first_read"
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("primary_active_first_read_min_settled") == 30
            and "OP_REFINED_K7" in str(payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("shadow_role") or "")
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("shadow_active_first_read_gate") == "phase8_promotion_review"
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("shadow_active_first_read_scope") == "per_rule_shadow_watch"
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("shadow_active_first_read_min_settled") == 20
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("summary_not_new_forward_evidence") is True
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("summary_no_lane_total_phase8_promotion") is True
            and payload_map["current_hierarchy_language"].get("settlement_audit_json_read", {}).get("summary_baq_not_bel") is True
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("artifact_status") == "pass"
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("anchor") == "OP_DURABLE_K7"
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("primary_paper_basket_companion") == "CD_CORE_K8"
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("same_family_shadow_watch") == "OP_REFINED_K7"
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("gate_source") == "forward_evidence_scorecard.json"
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("gate_source_loaded") is True
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("anchor_displacement_min") == 30
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("phase8_promotion_review_min") == 20
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("real_money_discussion_min") == 100
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("real_money_no_baq_as_bel_required") is True
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("not_settled_roi_evidence") is True
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("not_live_profitability_evidence") is True
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("not_promotion_readiness_evidence") is True
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("not_anchor_change_evidence") is True
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("not_real_money_evidence") is True
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("summary_preserves_baq_not_bel") is True
            and payload_map["current_hierarchy_language"].get("source_chain_matrix_json_read", {}).get("summary_preserves_no_phase8_promotion") is True
            and payload_map["current_hierarchy_language"].get("valid_evidence_scope") == current_hierarchy_language.VALID_EVIDENCE_SCOPE
            and payload_map["current_hierarchy_language"].get("evidence_boundary", {}).get("valid_evidence_scope") == current_hierarchy_language.VALID_EVIDENCE_SCOPE
            and "current_hierarchy_report_exposes_valid_evidence_scope" in {
                check.get("check") for check in payload_map["current_hierarchy_language"].get("checks", [])
            }
            and f"valid_evidence_scope={current_hierarchy_language.VALID_EVIDENCE_SCOPE}" in str(row_map["current_hierarchy_language"].get("current_read") or "")
            and "README.md" in payload_map["current_hierarchy_language"].get("current_surfaces_scanned", [])
            and "PAPER_TRADE_NOW.txt" in payload_map["current_hierarchy_language"].get("current_surfaces_scanned", [])
            and isinstance(payload_map["current_hierarchy_language"].get("latest_daily_summary_surface"), str)
            and payload_map["current_hierarchy_language"].get("latest_daily_summary_surface") in payload_map["current_hierarchy_language"].get("current_surfaces_scanned", [])
            and "CURRENT_EVIDENCE_SUMMARY.md" in payload_map["current_hierarchy_language"].get("current_surfaces_scanned", [])
            and "OPS_HISTORY.md" in payload_map["current_hierarchy_language"].get("current_surfaces_scanned", [])
            and "out/paper_trade_settlement_audit.md" in payload_map["current_hierarchy_language"].get("current_surfaces_scanned", [])
            and "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md" in payload_map["current_hierarchy_language"].get("current_surfaces_scanned", [])
            and "LIVE_SCANNER_USAGE.md" in payload_map["current_hierarchy_language"].get("current_surfaces_scanned", []),
            "current_hierarchy_layer_publishes_structured_guardrails",
            "top-level project sweep now consumes the direct current-hierarchy validator as its own child artifact, including README, shell-facing PAPER_TRADE_NOW.txt top-card coverage, latest daily-summary coverage, current-evidence bridge markdown/JSON sidecar with source-consistency/freshness/canonical scorecard-backed gate checks plus rebuild_validation_contract ordering, ops-history recap coverage, settlement-audit markdown/JSON current-read coverage with scorecard-sourced 30/20/100 gates, source-chain matrix markdown/JSON hierarchy and scorecard-gate coverage, and live-scanner usage coverage, the daily-guide route check, structured-key compatibility checks, direct valid_evidence_scope exposure, and the no-ROI/no-promotion/no-anchor-change/no-companion-change evidence boundary instead of seeing hierarchy safety only indirectly through navigation parents",
        )
    )
    checks.append(
        require(
            row_map["readme_current_status"].get("child_check_count") == 64
            and isinstance(row_map["readme_current_status"].get("child_checks"), list)
            and payload_map["readme_current_status"].get("suite_status") == "pass"
            and payload_map["readme_current_status"].get("total_checks") == 64
            and payload_map["readme_current_status"].get("check_count") == 64
            and "anchor=OP_DURABLE_K7" in row_map["readme_current_status"]["current_read"]
            and "Phase 8=SHADOW ONLY" in row_map["readme_current_status"]["current_read"]
            and "current_evidence_summary.json scorecard_audit_route" in row_map["readme_current_status"]["current_read"]
            and "rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only" in row_map["readme_current_status"]["current_read"]
            and expected_operator_read_gate_line in row_map["readme_current_status"]["current_read"]
            and "source-published settlement queue state/detail read=" in row_map["readme_current_status"]["current_read"]
            and "Harville benchmark-only lane, current odds-only XGBoost research-only lane" in row_map["readme_current_status"]["current_read"]
            and {
                "scorecard_nonpositive_phase8_floor_fails_before_artifacts",
                "scorecard_nonpositive_real_money_floor_fails_before_artifacts",
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "current_evidence_scorecard_audit_route_read",
                "current_evidence_rebuild_validation_contract_read",
                "current_evidence_operator_read_gate_route",
                "readme_current_gates_source_match_scorecard_json",
            }.issubset({check.get("check") for check in row_map["readme_current_status"]["child_checks"]})
            and payload_map["readme_current_status"]["current_evidence_operator_read_gate_read"].get(
                "recommended_command"
            )
            == expected_operator_recommended_command
            and payload_map["readme_current_status"]["current_evidence_rebuild_validation_contract_read"].get(
                "upstream_refresh_order"
            )
            == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ],
            "readme_current_status_promoted_to_project_child",
            "top-level project sweep now consumes the README landing-page validator as its own child artifact, including anchor/Phase 8 hierarchy wording, scorecard-audit route, current-evidence rebuild-order route, operator-read-gate routing, settlement-queue context, method-family guardrails, non-positive scorecard gate fixtures, and malformed current-evidence rebuild-contract fixtures instead of seeing the landing page only through the narrative report rollup",
        )
    )

    suite_read = build_suite_read(payload_map)
    checks.append(
        require(
            "repo-wide alignment sweep that keeps frozen-evidence ordering, operator readiness, current hierarchy wording / structured-key compatibility, shareable wording / presentation drift / dated-report trust-path routing, and human-facing navigation/read-order contracts pinned together" in suite_read,
            "project_surfaces_suite_names_repo_wide_scope",
            "project-surfaces suite summary now says plainly that this repo-wide parent sweep combines frozen-evidence ordering, operator readiness, current hierarchy wording / structured-key compatibility, report trust-path alignment, and navigation/read-order contracts instead of reading like a generic umbrella pass",
        )
    )
    checks.append(
        require(
            "cross-layer alignment check, not new forward evidence by itself" in suite_read
            and "stronger forward confidence still requires settled paper trades and other real forward results" in suite_read
            and "exact child-validation JSON byte counts and SHA-256 hashes are published for top-level reproducibility only, not performance evidence" in suite_read,
            "project_surfaces_suite_explicitly_stays_alignment_not_new_evidence",
            "project-surfaces suite summary now says plainly that a green repo-wide sweep is cross-layer alignment checking rather than new forward evidence while publishing child validation JSON fingerprints as reproducibility metadata only",
        )
    )
    checks.append(
        require(
            EVIDENCE_BOUNDARY.get("artifact_role") == "repo-wide validator rollup"
            and EVIDENCE_BOUNDARY.get("not_new_forward_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_live_profitability_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_real_money_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_promotion_readiness_evidence") is True
            and EVIDENCE_BOUNDARY.get("hashes_are_reproducibility_metadata_only") is True
            and "ROI-complete settled paper rows" in EVIDENCE_BOUNDARY.get("stronger_forward_confidence_requires", [])
            and "do not promote OP_REFINED_K7 or Phase 8 from validation cleanliness" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "do not substitute BAQ for BEL" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "machine-readable evidence_boundary metadata" in suite_read
            and "do not treat current hierarchy wording cleanliness as anchor-change or companion-change evidence" in EVIDENCE_BOUNDARY.get("non_goals", []),
            "project_surfaces_json_publishes_machine_readable_evidence_boundary",
            "top-level project JSON now publishes a machine-readable evidence_boundary block that keeps validator passes, child hashes, and current hierarchy wording cleanliness separated from settled ROI, live profitability, promotion readiness, anchor-change evidence, companion-change evidence, real-money evidence, Phase 8 promotion, odds-only XGBoost reopening, and BAQ/BEL substitution",
        )
    )

    payload = {
        "suite_status": "pass",
        "validators_run": len(rows),
        "frozen_evidence_checks": total_checks,
        "operator_fixture_scenarios": total_scenarios,
        "report_surface_checks": total_report_checks,
        "navigation_surface_checks": total_navigation_checks,
        "rows": rows,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "child_artifact_fingerprints": child_artifact_fingerprints,
        "child_artifact_fingerprint_manifest": child_artifact_fingerprint_manifest,
        "child_artifact_source_list": child_artifact_source_list,
        "child_artifact_source_markdown_lines": child_artifact_source_markdown_lines,
        "child_artifact_provenance_render_bundle": child_artifact_provenance_render_bundle,
        "child_artifact_provenance_markdown_contract": child_artifact_provenance_markdown_contract,
        "child_artifact_provenance_contract_markdown_lines": child_artifact_provenance_contract_markdown_lines,
        "current_evidence_bridge_json_read": current_evidence_bridge_json_read,
        "operator_markdown_component_render_contract": operator_markdown_component_render_contract,
        "stale_gate_shorthand_scan": stale_gate_shorthand_scan,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "summary": {
            "suite_read": suite_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": rebuild_command,
            "child_validator_mode": child_validator_mode,
        },
    }

    lines = [
        "# Project Surfaces Validation",
        "",
        "This report runs the top-level project validators together: the frozen evidence chain, the operator-facing paper-trade layer, the current hierarchy wording guardrail, the README landing page, the human-facing narrative report surfaces (including the dated working-status note), and the repo-navigation, main status-doc, plus operator-runbook surfaces that tell Cole what to read, rerun, and do.",
        "It is the repo-wide alignment sweep for frozen-evidence ordering, operator readiness, current hierarchy wording / structured-key compatibility, shareable wording / presentation drift / dated-report trust-path routing, and human-facing navigation/read-order contracts.",
        "",
        f"- Validators run: {len(rows)}",
        f"- Frozen evidence checks: {total_checks}",
        f"- Operator fixture scenarios: {total_scenarios}",
        f"- Report-surface checks: {total_report_checks}",
        f"- Navigation / hierarchy / status-doc / runbook checks: {total_navigation_checks}",
        "- Overall result: PASS",
        "",
        "## Suite Summary",
        "",
        "| Suite | Scope Metric | Result | Source | Source bytes | Source sha256 |",
        "|---|---:|---|---|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['label']} | {row['metric_value']} {row['metric_label']} | {row['result']} | `{row['json_path']}` | {row['child_json_bytes']} | `{row['child_json_sha256']}` |"
        )

    lines.extend(
        [
            "",
            "## Operator Component Markdown Contract",
            "",
            f"- Source: `{operator_markdown_component_render_contract['path']}` — {operator_markdown_fingerprint['bytes']} bytes, sha256={operator_markdown_fingerprint['sha256']}",
            f"- Child render contract: `{operator_markdown_component_render_contract['child_contract_source_json']}` — {operator_markdown_component_render_contract['child_required_snippet_count']} required snippets / {operator_markdown_component_render_contract['child_forbidden_snippet_count']} forbidden snippets mirrored into the project contract.",
            "- Snippet checks and hashes are report-render reproducibility metadata only, not settled ROI, live-profitability, promotion-readiness, or real-money evidence.",
            "",
            "## Current Evidence Bridge Gate Read",
            "",
            f"- Source: `{current_evidence_bridge_json_read['source_path']}`",
            f"- Effective gate source: `{current_evidence_bridge_json_read['decision_gate_effective_values_source']}`",
            f"- Effective gates: anchor_displacement={current_evidence_bridge_json_read['effective_anchor_displacement_min']}; phase8_promotion_review={current_evidence_bridge_json_read['effective_phase8_promotion_review_min']}; real_money_discussion={current_evidence_bridge_json_read['effective_real_money_discussion_min']}",
            f"- Top-card/scorecard drift: missing={current_evidence_bridge_json_read['decision_gate_missing_top_card_fields']}; mismatched={current_evidence_bridge_json_read['decision_gate_mismatched_fields']}",
            "- This parent-level read is provenance metadata only; it is not settled ROI, live-profitability, promotion-readiness, or real-money evidence.",
            "",
            "## Stale Gate Shorthand Scan",
            "",
            f"- Active text suffixes scanned: {', '.join(stale_gate_shorthand_scan['scanned_suffixes'])}",
            f"- Historical/progress paths excluded: {', '.join(stale_gate_shorthand_scan['excluded_names'])}; {', '.join(stale_gate_shorthand_scan['excluded_parts'])}",
            f"- Forbidden compressed-gate pattern count: {stale_gate_shorthand_scan['forbidden_pattern_count']}",
            f"- Matches found: {stale_gate_shorthand_scan['match_count']}",
            "- This scan is wording hygiene only; it does not create settled ROI, live-profitability, promotion-readiness, or real-money evidence.",
            "",
            "## Rollup Checks",
            "",
        ]
    )
    for check in checks:
        lines.append(f"- PASS `{check['check']}` — {check['detail']}")

    lines.extend(
        [
            "",
            "## Current Read",
            "",
            f"- Suite read: {suite_read}",
            "",
            "## Rebuild",
            "",
            f"- Working directory: `{BASE}`",
            f"- Command: `{rebuild_command}`",
            f"- Child validator mode: `{child_validator_mode}`",
            "",
            "## Evidence Boundary",
            "",
            f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
            f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
            "- Not new forward evidence; not live-profitability evidence; not real-money evidence; not promotion-readiness evidence.",
            "- Child hashes are reproducibility metadata only.",
            f"- Stronger forward confidence still requires: {', '.join(EVIDENCE_BOUNDARY['stronger_forward_confidence_requires'])}.",
            f"- Non-goals: {', '.join(EVIDENCE_BOUNDARY['non_goals'])}.",
            "",
            "## Child Suite Reads",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- **{row['label']}**: {row['current_read']}")

    lines.extend(
        [
            "",
            "## Bottom Line",
            "",
            "The project is currently aligned across the layers that matter most for safe operation and honest sharing — and this repo-wide sweep remains the fastest validated answer for frozen-evidence ordering, operator readiness, current hierarchy wording / structured-key compatibility, shareable wording / presentation drift / dated-report trust-path routing, and human-facing navigation/read-order contracts:",
            "",
            f"- research layer: {next(row['current_read'] for row in rows if row['name'] == 'frozen_evidence_chain')}",
            f"- operator layer: {next(row['current_read'] for row in rows if row['name'] == 'paper_trade_operator_suite')}",
            f"- report layer: {next(row['current_read'] for row in rows if row['name'] == 'report_surfaces')}",
            f"- current hierarchy layer: {next(row['current_read'] for row in rows if row['name'] == 'current_hierarchy_language')}",
            f"- navigation layer: quickstart: {next(row['current_read'] for row in rows if row['name'] == 'validation_quickstart')}; daily guide: {next(row['current_read'] for row in rows if row['name'] == 'daily_artifact_guide')}; paper-trade usage: {next(row['current_read'] for row in rows if row['name'] == 'paper_trade_usage')}; cole status: {next(row['current_read'] for row in rows if row['name'] == 'cole_status_and_plan')}",
            "",
            "If this suite stays green after broader edits, Cole can be more confident that the research story, the live-operational surfaces, the human-facing report wording/trust-path routing, and the repo's read / rerun guidance still agree with each other.",
            "That green read is a cross-layer alignment check, not new forward evidence by itself; genuinely stronger forward confidence still has to come from settled paper trades and other real forward results.",
            "",
            *child_artifact_provenance_contract_markdown_lines,
            "",
            "## Child Artifact Fingerprint Manifest",
            "",
            "This table mirrors `child_artifact_fingerprint_manifest.entries_in_suite_order` from the JSON sidecar. It is deterministic provenance metadata only, not settled ROI, live profitability, promotion readiness, or real-money evidence.",
            "",
            "| Child | JSON path | Source bytes | Source sha256 |",
            "|---|---|---:|---|",
            *child_artifact_fingerprint_manifest_markdown_rows,
            "",
            "## Child Validation JSON Fingerprints",
            "",
            "These hashes identify the exact child validation JSON artifacts summarized by this top-level project sweep. They are reproducibility metadata only, not settled ROI, live profitability, promotion readiness, or real-money evidence.",
            "",
        ]
    )
    lines.extend(child_artifact_fingerprint_bullet_lines)

    lines.extend(
        [
            "",
            "## Sources",
            "",
        ]
    )
    lines.extend(child_artifact_source_markdown_lines)

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
