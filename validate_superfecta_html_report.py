#!/usr/bin/env python3
"""
Validation for Superfecta_Project_Report_2026-04-15.html.

Purpose:
- keep the shareable HTML report aligned with the frozen evaluation standard
- ensure the historical +30.42% selector-scoring result stays distinct from the current frozen selector benchmark
- pin the visible presentation copy to the same anchor / paper / shadow / benchmark posture used elsewhere
"""

from __future__ import annotations

import csv
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from zipfile import ZipFile

BASE = Path(__file__).resolve().parent
REPORT = BASE / "Superfecta_Project_Report_2026-04-15.html"
PDF_REPORT = BASE / "Superfecta_Project_Report_2026-04-15.pdf"
LEGACY_ALIAS = BASE / "Superfecta_Project_Report.html"
LEGACY_PDF_ALIAS = BASE / "Superfecta_Project_Report.pdf"
LEGACY_DOCX_ALIAS = BASE / "Superfecta_Project_Report.docx"
LEGACY_QUICK_START_PDF_ALIAS = BASE / "Superfecta Prediction - Quick Start Guide.pdf"
LEGACY_PROMPT_DOCX_ALIAS = BASE / "OpenClaw Prompt.docx"
PORTFOLIO_CSV = BASE / "portfolio_decision_card.csv"
METHOD_CSV = BASE / "method_family_decision_card.csv"
SCORECARD_CSV = BASE / "forward_evidence_scorecard.csv"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
CROSS_FAMILY_MD = BASE / "CROSS_FAMILY_DECISION.md"
CROSS_FAMILY_VALIDATOR = BASE / "validate_cross_family_decision.py"
OUT_DIR = BASE / "out" / "status_validation" / "superfecta_html_report"
OUT_MD = OUT_DIR / "superfecta_html_report_validation.md"
OUT_JSON = OUT_DIR / "superfecta_html_report_validation.json"
REBUILD_COMMAND = "python3 validate_superfecta_html_report.py"
CI_ONLY_SOURCE = "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7"
EXPECTED_REBUILD_ORDER_COMMANDS = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]


def load_csv_map(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {str(row[key]): row for row in rows}


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "pass", "detail": detail}


def require_positive_non_bool_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{field_name} must be a positive non-boolean integer")
    return value


def require_scorecard_decision_gate_minimums(
    scorecard_json: dict[str, Any],
    source_name: str,
) -> dict[str, Any]:
    gates = scorecard_json.get("decision_gate_minimums")
    if not isinstance(gates, dict):
        raise AssertionError(f"{source_name} is missing decision_gate_minimums")

    anchor = gates.get("anchor_displacement")
    phase8 = gates.get("phase8_promotion_review")
    real_money = gates.get("real_money_discussion")
    if not all(isinstance(item, dict) for item in (anchor, phase8, real_money)):
        raise AssertionError(f"{source_name} decision_gate_minimums is incomplete")

    anchor_min = require_positive_non_bool_int(
        anchor.get("min_roi_complete_settled_observations"),
        "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
    )
    phase8_min = require_positive_non_bool_int(
        phase8.get("min_roi_complete_settled_observations"),
        "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
    )
    real_money_min = require_positive_non_bool_int(
        real_money.get("min_total_settled_observations_with_usable_roi"),
        "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
    )
    also_requires = real_money.get("also_requires")
    if not isinstance(also_requires, list) or any(not isinstance(item, str) for item in also_requires):
        raise AssertionError("decision_gate_minimums.real_money_discussion.also_requires must be a string list")
    if "no BAQ-as-BEL substitution" not in also_requires:
        raise AssertionError(
            "decision_gate_minimums.real_money_discussion.also_requires must include no BAQ-as-BEL substitution"
        )

    return {
        "source": source_name,
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_no_baq_as_bel_required": True,
    }


def require_current_evidence_rebuild_contract(current_evidence: dict[str, Any]) -> dict[str, Any]:
    contract = current_evidence.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise AssertionError("current_evidence_summary.json must publish rebuild_validation_contract as an object")
    upstream_refresh_order = contract.get("upstream_refresh_order")
    if not isinstance(upstream_refresh_order, list) or len(upstream_refresh_order) != len(EXPECTED_REBUILD_ORDER_COMMANDS):
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract must publish the three-step upstream_refresh_order")

    commands: list[str] = []
    for expected_order, step in enumerate(upstream_refresh_order, start=1):
        if not isinstance(step, dict):
            raise AssertionError("current_evidence_summary.json upstream_refresh_order steps must be objects")
        if step.get("order") != expected_order:
            raise AssertionError("current_evidence_summary.json upstream_refresh_order order values drifted")
        command = step.get("command")
        if not isinstance(command, str):
            raise AssertionError("current_evidence_summary.json upstream_refresh_order commands must be strings")
        commands.append(command)

    if commands != EXPECTED_REBUILD_ORDER_COMMANDS:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract upstream order drifted")
    if contract.get("prerequisite_rebuild_command") != EXPECTED_REBUILD_ORDER_COMMANDS[0]:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract prerequisite command drifted")
    if contract.get("rebuild_command") != EXPECTED_REBUILD_ORDER_COMMANDS[1]:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract rebuild command drifted")
    if contract.get("direct_validation_command") != EXPECTED_REBUILD_ORDER_COMMANDS[2]:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract direct validator command drifted")
    if contract.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is not True:
        raise AssertionError("rebuild_validation_contract must require settlement-audit refresh before bridge rebuilds")
    if contract.get("requires_source_consistency_before_quoting_current_totals") is not True:
        raise AssertionError("rebuild_validation_contract must require source consistency before current totals are quoted")
    if contract.get("upstream_refresh_order_is_provenance_metadata_only") is not True:
        raise AssertionError("rebuild_validation_contract upstream order must be provenance metadata only")
    if contract.get("not_settled_roi_or_real_money_evidence") is not True:
        raise AssertionError("rebuild_validation_contract must not be settled ROI or real-money evidence")

    return {
        "source": CURRENT_EVIDENCE_JSON.name,
        "source_path": "rebuild_validation_contract",
        "prerequisite_rebuild_command": contract.get("prerequisite_rebuild_command"),
        "rebuild_command": contract.get("rebuild_command"),
        "direct_validation_command": contract.get("direct_validation_command"),
        "upstream_refresh_order": commands,
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": contract.get(
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
        ),
        "requires_source_consistency_before_quoting_current_totals": contract.get(
            "requires_source_consistency_before_quoting_current_totals"
        ),
        "upstream_refresh_order_valid_use": contract.get("upstream_refresh_order_valid_use"),
        "upstream_refresh_order_is_provenance_metadata_only": contract.get(
            "upstream_refresh_order_is_provenance_metadata_only"
        ),
        "green_checks_are_reproducibility_metadata_only": contract.get(
            "green_checks_are_reproducibility_metadata_only"
        ),
        "not_settled_roi_or_real_money_evidence": contract.get(
            "not_settled_roi_or_real_money_evidence"
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the shareable Superfecta HTML/PDF report")
    parser.add_argument("--current-evidence-json", type=Path, default=CURRENT_EVIDENCE_JSON)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def current_bridge_cli_contract_checks(
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="html_report_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json_path).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "superfecta_html_report_validation"
        missing_contract_payload = json.loads(json.dumps(base_payload))
        missing_contract_payload.pop("rebuild_validation_contract", None)
        current_evidence_path.write_text(json.dumps(missing_contract_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--current-evidence-json",
                str(current_evidence_path),
                "--out-dir",
                str(missing_contract_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not missing_contract_out_dir.exists()
                and "current_evidence_summary.json must publish rebuild_validation_contract as an object"
                in proc.stderr,
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "validate_superfecta_html_report.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial HTML/PDF report validation artifacts",
            )
        )

        weakened_contract_out_dir = tmp_root / "weakened" / "superfecta_html_report_validation"
        weakened_contract_payload = json.loads(json.dumps(base_payload))
        weakened_contract_payload["rebuild_validation_contract"][
            "upstream_refresh_order_is_provenance_metadata_only"
        ] = False
        current_evidence_path.write_text(json.dumps(weakened_contract_payload), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--current-evidence-json",
                str(current_evidence_path),
                "--out-dir",
                str(weakened_contract_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not weakened_contract_out_dir.exists()
                and "rebuild_validation_contract upstream order must be provenance metadata only"
                in proc.stderr,
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "validate_superfecta_html_report.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial HTML/PDF report validation artifacts",
            )
        )

    return checks


def scorecard_cli_gate_contract_checks(
    scorecard_json_path: Path = SCORECARD_JSON,
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> list[dict[str, Any]]:
    with TemporaryDirectory(prefix="html_report_scorecard_gates_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(scorecard_json_path).read_text(encoding="utf-8"))
        errors: list[str] = []
        cases = [
            (
                "boolean_anchor",
                lambda payload: payload["decision_gate_minimums"]["anchor_displacement"].__setitem__(
                    "min_roi_complete_settled_observations",
                    True,
                ),
                "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations must be a positive non-boolean integer",
            ),
            (
                "nonpositive_phase8",
                lambda payload: payload["decision_gate_minimums"]["phase8_promotion_review"].__setitem__(
                    "min_roi_complete_settled_observations",
                    0,
                ),
                "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer",
            ),
            (
                "nonpositive_real_money",
                lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                    "min_total_settled_observations_with_usable_roi",
                    0,
                ),
                "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer",
            ),
            (
                "missing_no_baq",
                lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                    "also_requires",
                    [
                        item
                        for item in payload["decision_gate_minimums"]["real_money_discussion"].get(
                            "also_requires",
                            [],
                        )
                        if item != "no BAQ-as-BEL substitution"
                    ],
                ),
                "decision_gate_minimums.real_money_discussion.also_requires must include no BAQ-as-BEL substitution",
            ),
        ]

        for case_name, mutate, expected_error in cases:
            payload = json.loads(json.dumps(base_payload))
            mutate(payload)
            scorecard_path = tmp_root / f"{case_name}_scorecard.json"
            out_dir = tmp_root / case_name / "superfecta_html_report_validation"
            scorecard_path.write_text(json.dumps(payload), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--scorecard-json",
                    str(scorecard_path),
                    "--current-evidence-json",
                    str(current_evidence_json_path),
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=BASE,
                capture_output=True,
                text=True,
            )
            combined = f"{proc.stdout}\n{proc.stderr}"
            if proc.returncode == 0:
                errors.append(f"{case_name}: malformed scorecard was accepted")
            if out_dir.exists():
                errors.append(f"{case_name}: output directory was created before scorecard gate validation failed")
            if expected_error not in combined:
                errors.append(f"{case_name}: expected error text was missing")

    return [
        require(
            not errors,
            "malformed_scorecard_gate_floors_fail_before_artifacts",
            "validate_superfecta_html_report.py rejects boolean anchor floors, non-positive Phase 8 / real-money floors, and a missing no-BAQ-as-BEL prerequisite before creating nested HTML/PDF report validation artifacts",
        )
    ]


def extract_normalized_pdf_text(path: Path) -> tuple[str, int, int]:
    if not path.exists():
        raise AssertionError(f"Missing dated PDF derivative export: {path}")
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - environment dependency check
        raise AssertionError("pypdf is required to validate the dated PDF derivative export") from exc

    reader = PdfReader(str(path))
    raw_text = "\n".join((page.extract_text() or "") for page in reader.pages)
    normalized_text = re.sub(r"-\s+", "-", raw_text)
    normalized_text = re.sub(r"\s+", " ", normalized_text).strip()
    return normalized_text, len(reader.pages), path.stat().st_size


def extract_normalized_docx_text(path: Path) -> tuple[str, int]:
    if not path.exists():
        raise AssertionError(f"Missing legacy DOCX alias: {path}")
    try:
        with ZipFile(path) as archive:
            raw_xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
    except Exception as exc:
        raise AssertionError(f"Could not read DOCX text from {path}") from exc
    text = re.sub(r"<[^>]+>", " ", raw_xml)
    text = re.sub(r"\s+", " ", text).strip()
    return text, path.stat().st_size


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    scorecard_json_path = Path(args.scorecard_json)
    scorecard_json = json.loads(scorecard_json_path.read_text(encoding="utf-8"))
    scorecard_gate_read = require_scorecard_decision_gate_minimums(
        scorecard_json,
        scorecard_json_path.name,
    )
    current_evidence = json.loads(Path(args.current_evidence_json).read_text(encoding="utf-8"))
    rebuild_validation_contract_json_read = require_current_evidence_rebuild_contract(current_evidence)
    text = REPORT.read_text(encoding="utf-8")
    pdf_text, pdf_page_count, pdf_byte_count = extract_normalized_pdf_text(PDF_REPORT)
    legacy_pdf_text, legacy_pdf_page_count, legacy_pdf_byte_count = extract_normalized_pdf_text(LEGACY_PDF_ALIAS)
    legacy_quick_start_pdf_text, legacy_quick_start_page_count, legacy_quick_start_byte_count = (
        extract_normalized_pdf_text(LEGACY_QUICK_START_PDF_ALIAS)
    )
    legacy_docx_text, legacy_docx_byte_count = extract_normalized_docx_text(LEGACY_DOCX_ALIAS)
    legacy_prompt_docx_text, legacy_prompt_docx_byte_count = extract_normalized_docx_text(LEGACY_PROMPT_DOCX_ALIAS)
    legacy_alias_text = LEGACY_ALIAS.read_text(encoding="utf-8")
    portfolio = load_csv_map(PORTFOLIO_CSV, "method_id")
    method_family = load_csv_map(METHOD_CSV, "family_id")
    scorecard = load_csv_map(SCORECARD_CSV, "rule_id")

    anchor = scorecard["OP_DURABLE_K7"]
    phase7 = portfolio["phase7_live_portfolio"]
    selector = portfolio["train_only_selector"]
    phase8 = portfolio["phase8_frozen_portfolio"]
    selective = method_family["selective_rule_path"]
    harville = method_family["harville_ranked"]
    xgboost = method_family["xgboost_residual"]
    current_primary = current_evidence["current_paper_status"]["primary"]
    rule_progress = {
        row["rule_id"]: row for row in current_primary["rule_progress"]
    }
    current_first_read = current_primary["first_read"]
    current_portfolio_review = current_primary["portfolio_review"]
    scorecard_ci_only_diagnostic = scorecard_json["ci_only_promotion_diagnostics"]["OP_REFINED_K7"]
    current_ci_only_check = current_evidence["scorecard_ci_only_promotion_check"]
    source_consistency_label = (
        "matched" if current_evidence["source_consistency"]["overall_match"] is True else "not matched"
    )
    source_freshness = current_evidence["source_freshness"]
    requires_refresh = bool(source_freshness.get("requires_refresh_before_right_now_use"))
    source_freshness_label = "requires refresh before right-now use" if requires_refresh else "fresh for right-now use"
    combined_operator_route_label = (
        "requires refresh before right-now instruction or evidence use"
        if requires_refresh
        else "is fresh against the bridge reference date but still goes through operator read-gate routing before right-now instruction or evidence use"
    )
    operator_read_gate = (
        current_evidence.get("operator_read_gate")
        if isinstance(current_evidence.get("operator_read_gate"), dict)
        else {}
    )
    operator_read_gate_read = str(operator_read_gate.get("read") or "").strip()
    operator_read_gate_requires_refresh = bool(
        operator_read_gate.get("requires_refresh_before_evidence_read")
    )
    operator_read_gate_requires_refresh_label = (
        "true" if operator_read_gate_requires_refresh else "false"
    )
    operator_read_gate_json_read = {
        "source": CURRENT_EVIDENCE_JSON.name,
        "source_path": "operator_read_gate",
        "gate_status": operator_read_gate.get("gate_status"),
        "valid_use": operator_read_gate.get("valid_use"),
        "requires_refresh_before_evidence_read": operator_read_gate.get("requires_refresh_before_evidence_read"),
        "has_api_access_failure_context": operator_read_gate.get("has_api_access_failure_context"),
        "has_scanner_failure_boundary": operator_read_gate.get("has_scanner_failure_boundary"),
        "has_stale_cache_fallback_context": operator_read_gate.get("has_stale_cache_fallback_context"),
        "recommended_command": operator_read_gate.get("recommended_command"),
        "current_top_card_counts_as_no_target_evidence": operator_read_gate.get(
            "current_top_card_counts_as_no_target_evidence"
        ),
        "current_top_card_counts_as_clean_empty_evidence": operator_read_gate.get(
            "current_top_card_counts_as_clean_empty_evidence"
        ),
        "current_top_card_counts_as_bet_readiness_evidence": operator_read_gate.get(
            "current_top_card_counts_as_bet_readiness_evidence"
        ),
        "current_top_card_counts_as_settled_roi_evidence": operator_read_gate.get(
            "current_top_card_counts_as_settled_roi_evidence"
        ),
        "not_forward_performance_evidence": operator_read_gate.get("not_forward_performance_evidence"),
        "not_promotion_readiness_evidence": operator_read_gate.get("not_promotion_readiness_evidence"),
        "not_live_profitability_evidence": operator_read_gate.get("not_live_profitability_evidence"),
        "not_real_money_evidence": operator_read_gate.get("not_real_money_evidence"),
        "read": operator_read_gate_read,
    }
    scorecard_audit_route = (
        current_evidence.get("scorecard_audit_route")
        if isinstance(current_evidence.get("scorecard_audit_route"), dict)
        else {}
    )
    scorecard_audit_route_read = str(scorecard_audit_route.get("route_read") or "").strip()
    scorecard_audit_route_json_read = {
        "source": CURRENT_EVIDENCE_JSON.name,
        "source_path": "scorecard_audit_route",
        "markdown_path": scorecard_audit_route.get("markdown_path"),
        "json_path": scorecard_audit_route.get("json_path"),
        "validator_command": scorecard_audit_route.get("validator_command"),
        "gate_floor_source": scorecard_audit_route.get("gate_floor_source"),
        "gate_floor_snapshot": scorecard_audit_route.get("gate_floor_snapshot"),
        "valid_use": scorecard_audit_route.get("valid_use"),
        "artifacts_present": scorecard_audit_route.get("artifacts_present"),
        "not_forward_performance_evidence": scorecard_audit_route.get("not_forward_performance_evidence"),
        "not_settled_roi_evidence": scorecard_audit_route.get("not_settled_roi_evidence"),
        "not_promotion_readiness_evidence": scorecard_audit_route.get("not_promotion_readiness_evidence"),
        "not_live_profitability_evidence": scorecard_audit_route.get("not_live_profitability_evidence"),
        "not_bankroll_guidance": scorecard_audit_route.get("not_bankroll_guidance"),
        "not_real_money_evidence": scorecard_audit_route.get("not_real_money_evidence"),
        "read": scorecard_audit_route_read,
    }
    upstream_refresh_commands = rebuild_validation_contract_json_read["upstream_refresh_order"]
    rebuild_order_arrow = " -> ".join(upstream_refresh_commands)
    scorecard_anchor_min = scorecard_gate_read["anchor_displacement_min_roi_complete_settled_observations"]
    scorecard_phase8_min = scorecard_gate_read["phase8_promotion_review_min_roi_complete_settled_observations"]
    scorecard_real_money_min = scorecard_gate_read["real_money_discussion_min_total_settled_observations_with_usable_roi"]
    expected_combined_operator_route_card_fragment = (
        "Combined operator read route says check <code>operator_status_context</code>, <code>source_freshness.requires_refresh_before_right_now_use=true</code>, and <code>operator_read_gate.requires_refresh_before_evidence_read=true</code>; rerun <code>./run_daily_portfolio_observation.sh</code> before treating wrapper-refresh, missing-output, stale <code>PAPER_TRADE_NOW</code>, or its best-action card as today's operator instruction or evidence. This is not no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money evidence."
        if requires_refresh
        else (
            "Combined operator read route says check <code>operator_status_context</code>, "
            "<code>source_freshness.requires_refresh_before_right_now_use=false</code>, and "
            f"<code>operator_read_gate.requires_refresh_before_evidence_read={operator_read_gate_requires_refresh_label}</code>; "
            "the saved <code>PAPER_TRADE_NOW</code> best-action card is fresh against the bridge reference date but still goes "
            "through operator read-gate routing before right-now instruction or evidence use. This is not no-target, clean-empty, "
            "bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money evidence."
        )
    )
    expected_source_repair_fragment = (
        "If <code>source_consistency.overall_match=false</code>, repair the top-card / audit / CSV mismatch before quoting current paper numbers. Then use the combined <code>operator_status_context</code> + <code>source_freshness.requires_refresh_before_right_now_use=true</code> + <code>operator_read_gate.requires_refresh_before_evidence_read=true</code> route and refresh the daily OP/CD + shadow wrapper (`./run_daily_portfolio_observation.sh`) before using the saved right-now card as current-day guidance or evidence."
        if requires_refresh
        else (
            "If <code>source_consistency.overall_match=false</code>, repair the top-card / audit / CSV mismatch before quoting "
            "current paper numbers. Then use the combined <code>operator_status_context</code> + "
            "<code>source_freshness.requires_refresh_before_right_now_use=false</code> + "
            f"<code>operator_read_gate.requires_refresh_before_evidence_read={operator_read_gate_requires_refresh_label}</code> "
            "route before using the saved right-now card as current-day guidance or evidence."
        )
    )
    expected_pdf_combined_operator_route_fragment = (
        "Combined operator read route says check operator_status_context, source_freshness.requires_refresh_before_right_now_use=true, and operator_read_gate.requires_refresh_before_evidence_read=true; rerun ./run_daily_portfolio_observation.sh before treating wrapper-refresh, missing-output, stale PAPER_TRADE_NOW, or its best-action card as today's operator instruction or evidence. This is not no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money evidence."
        if requires_refresh
        else (
            "Combined operator read route says check operator_status_context, "
            "source_freshness.requires_refresh_before_right_now_use=false, and "
            f"operator_read_gate.requires_refresh_before_evidence_read={operator_read_gate_requires_refresh_label}; "
            "the saved PAPER_TRADE_NOW best-action card is fresh against the bridge reference date but still goes through "
            "operator read-gate routing before right-now instruction or evidence use. This is not no-target, clean-empty, "
            "bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money evidence."
        )
    )
    expected_pdf_source_repair_fragment = (
        "If source_consistency.overall_match=false, repair the top-card / audit / CSV mismatch before quoting current paper numbers. Then use the combined operator_status_context + source_freshness.requires_refresh_before_right_now_use=true + operator_read_gate.requires_refresh_before_evidence_read=true route and refresh the daily OP/CD + shadow wrapper (`./run_daily_portfolio_observation.sh`) before using the saved right-now card as current-day guidance or evidence."
        if requires_refresh
        else (
            "If source_consistency.overall_match=false, repair the top-card / audit / CSV mismatch before quoting current paper "
            f"numbers. Then use the combined operator_status_context + source_freshness.requires_refresh_before_right_now_use=false + "
            f"operator_read_gate.requires_refresh_before_evidence_read={operator_read_gate_requires_refresh_label} route before using "
            "the saved right-now card as current-day guidance or evidence."
        )
    )

    hero_fragment = (
        "Historical selector-scoring improvement: walk-forward ROI improved from <strong>+22.46%</strong> to <strong>+30.42%</strong> "
        "with sqrt-dampened scoring, but the current frozen selector benchmark still remains the <strong>Train-only yearly selector</strong> "
        "at <strong>+22.46%</strong> walk-forward and <strong>+14.36%</strong> holdout."
    )
    metric_fragment = (
        "Historical selector-scoring result after cleanup. The current frozen selector benchmark still remains <strong>+22.46%</strong> "
        "walk-forward and <strong>+14.36%</strong> holdout for the <strong>Train-only yearly selector</strong>."
    )
    holdout_winner_fragment = (
        "Phase 7 holdout ROI on <strong>175 races</strong>, currently the strongest practical paper baseline, but with an uneven recent path: <strong>2024 +0.37% on 109</strong>, <strong>2025 +105.38% on 66</strong>."
    )
    phase7_rule_component_fragments = [
        "The strongest practical evidence still belongs to the Phase 7 OP/CD rule-component basket, not the bigger Phase 8 expansion.",
        "Use the Phase 7 OP/CD rule-component basket as the real paper-trade default, with target cards confirmed by daily preflight, because it owns the best current holdout evidence.",
    ]
    table_evidence_fragment = "Phase 7: +38.68% on 175 (2024 +0.37% on 109; 2025 +105.38% on 66) vs Phase 8: +21.45% on 118 (2024 +9.50% on 85; 2025 +50.26% on 33)"
    table_decision_fragment = (
        "Run Phase 7 as primary paper baseline and keep Phase 8 in shadow, but do not talk about that win like it was a smooth two-year glide."
    )
    operational_shift_fragment = (
        "Daily paper-trade, settlement, forward-check, lane monitor, and preflight note path are now in place. That is workflow hardening, not new forward evidence by itself."
    )
    operations_decision_fragment = (
        "Treat this as an operating system for forward evidence, not just a research folder; genuinely new forward evidence still requires settled paper trades."
    )
    html_evidence_scope_fragment = (
        "Only settled paper-trade rows with usable ROI coverage should change deployment posture; clean scans, open signals, historical replay rows, calibration-only summaries, or another odds-only rerun should not."
    )
    operational_hardening_fragment = (
        "The strongest practical gain is not a headline stat, it’s that the daily operating path stopped being hand-wavy. That makes the workflow more reproducible, not newly profitable by itself."
    )
    current_evidence_table_fragment = (
        f"CURRENT_EVIDENCE_SUMMARY.md / current_evidence_summary.json; source consistency {source_consistency_label}; "
        f"combined operator-status/source-freshness/operator-read-gate route {combined_operator_route_label}; "
        f"gate source {SCORECARD_JSON.name} decision_gate_minimums anchor_displacement={scorecard_anchor_min}, "
        f"phase8_promotion_review={scorecard_phase8_min}, real_money_discussion={scorecard_real_money_min}; "
        f"scorecard audit route {CURRENT_EVIDENCE_JSON.name} scorecard_audit_route -> "
        f"{scorecard_audit_route.get('markdown_path')} / {scorecard_audit_route.get('json_path')} + "
        f"{scorecard_audit_route.get('validator_command')}; "
        f"rebuild order {CURRENT_EVIDENCE_JSON.name} rebuild_validation_contract -> {rebuild_order_arrow}; "
        f"primary paper {current_first_read['current']}/{current_first_read['threshold']} first-read, "
        f"{current_portfolio_review['current']}/{current_portfolio_review['threshold']} broader-review; "
        f"CD_CORE_K8 {rule_progress['CD_CORE_K8']['roi_complete_settled_rows']} ROI-complete rows, "
        f"OP_DURABLE_K7 {rule_progress['OP_DURABLE_K7']['roi_complete_settled_rows']}"
    )
    current_evidence_decision_fragment = (
        f"Treat the {rule_progress['CD_CORE_K8']['roi_complete_settled_rows']} settled CD rows as operational context only, not OP-anchor proof, Phase 8 promotion readiness, live profitability, bankroll guidance, or real-money evidence; use the combined operator_status_context + source_freshness.requires_refresh_before_right_now_use=true + operator_read_gate.requires_refresh_before_evidence_read=true route and rerun ./run_daily_portfolio_observation.sh before using a wrapper-refresh, missing-output, or stale PAPER_TRADE_NOW / best-action card as today's operator instruction or evidence; do not treat the saved top card as no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money evidence; repair any source_consistency.overall_match=false mismatch before quoting totals."
        if requires_refresh
        else (
            f"Treat the {rule_progress['CD_CORE_K8']['roi_complete_settled_rows']} settled CD rows as operational context only, "
            "not OP-anchor proof, Phase 8 promotion readiness, live profitability, bankroll guidance, or real-money evidence; "
            "use the combined operator_status_context + source_freshness.requires_refresh_before_right_now_use=false + "
            f"operator_read_gate.requires_refresh_before_evidence_read={operator_read_gate_requires_refresh_label} route before using "
            "the saved PAPER_TRADE_NOW best-action card as today's operator instruction or evidence; repair any "
            "source_consistency.overall_match=false mismatch before quoting totals."
        )
    )
    current_evidence_card_fragments = [
        "<span class=\"status-chip blue\">Current paper bridge</span>",
        "<h3>Quote the bridge before the totals</h3>",
        "For short Cole updates, read <code>CURRENT_EVIDENCE_SUMMARY.md</code> / <code>current_evidence_summary.json</code> before quoting <code>PAPER_TRADE_NOW</code>, ops-bucket/operator-status context, settlement-audit, or primary-ledger totals.",
        f"Source consistency is <strong>{source_consistency_label}</strong> across the top card, audit, and primary settlement CSV.",
        expected_combined_operator_route_card_fragment,
        f"Primary paper is still <strong>{current_first_read['current']}/{current_first_read['threshold']}</strong> ROI-complete toward a first read and <strong>{current_portfolio_review['current']}/{current_portfolio_review['threshold']}</strong> toward broader review.",
        f"Gate source is <code>{SCORECARD_JSON.name}</code> <code>decision_gate_minimums</code>: <strong>anchor_displacement={scorecard_anchor_min}</strong>, <strong>phase8_promotion_review={scorecard_phase8_min}</strong>, <strong>real_money_discussion={scorecard_real_money_min}</strong>; these are future ROI-complete observation floors, not cleared gates.",
        (
            "Scorecard audit route: <code>current_evidence_summary.json</code> source path <code>scorecard_audit_route</code> "
            "points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to "
            f"<code>{scorecard_audit_route.get('markdown_path')}</code> / "
            f"<code>{scorecard_audit_route.get('json_path')}</code> plus "
            f"<code>{scorecard_audit_route.get('validator_command')}</code>; this route is "
            "report-synchronization metadata only, not forward performance, settled ROI, promotion readiness, "
            "live profitability, bankroll guidance, or real-money evidence."
        ),
        (
            "Rebuild-order route: <code>current_evidence_summary.json</code> "
            "source path <code>rebuild_validation_contract</code> routes scorecard/rules/signals/settlement-ledger "
            "byte changes through <code>python3 paper_trade_settlement_audit.py</code> -> "
            "<code>python3 current_evidence_summary.py</code> -> "
            "<code>python3 validate_current_evidence_summary.py</code> before quoting "
            "<code>CURRENT_EVIDENCE_SUMMARY.*</code>; this is provenance/rebuild metadata only, not "
            "settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence."
        ),
        f"Current settled sample is <strong>CD-only</strong>: <strong>CD_CORE_K8 {rule_progress['CD_CORE_K8']['roi_complete_settled_rows']}</strong>, <strong>OP_DURABLE_K7 {rule_progress['OP_DURABLE_K7']['roi_complete_settled_rows']}</strong>; this is not OP-anchor proof, promotion readiness, live profitability, bankroll guidance, real-money evidence, or cross-family promotion evidence.",
        expected_source_repair_fragment,
    ]
    cross_family_current_paper_fragment = (
        "For anchor / paper / watch caveats, read <code>CROSS_FAMILY_DECISION.md</code> and run <code>python3 validate_cross_family_decision.py</code>; stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green HTML/PDF validation are not OP-anchor proof."
    )
    full_data_retrain_html_fragments = [
        "<td data-label=\"Category\"><strong>Full-data retrain caveat</strong></td>",
        "Full-data XGBoost retrain artifacts are command and diagnostic reproducibility only.",
        "FULL_DATA_RETRAIN_ARTIFACTS.md + validate_full_data_retrain_artifacts.py; RMSE / MAE model-fit diagnostics",
        "Do not treat exact retrain/prediction commands or RMSE / MAE gains as paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "Full-data XGBoost retrain commands and RMSE / MAE gains stay in <code>FULL_DATA_RETRAIN_ARTIFACTS.md</code> / <code>validate_full_data_retrain_artifacts.py</code> as model-fit diagnostics only",
    ]
    full_data_retrain_pdf_fragments = [
        "Full-data retrain caveat",
        "Full-data XGBoost retrain artifacts are command and diagnostic reproducibility only.",
        "Full-data XGBoost retrain commands and RMSE / MAE gains stay in FULL_DATA_RETRAIN_ARTIFACTS.md / validate_full_data_retrain_artifacts.py as model-fit diagnostics only",
    ]
    pdf_current_evidence_fragments = [
        "Quote the bridge before the totals",
        "For short Cole updates, read CURRENT_EVIDENCE_SUMMARY.md / current_evidence_summary.json before quoting PAPER_TRADE_NOW, ops-bucket/operator-status context, settlement-audit, or primary-ledger totals.",
        f"Source consistency is {source_consistency_label} across the top card, audit, and primary settlement CSV.",
        expected_pdf_combined_operator_route_fragment,
        f"Primary paper is still {current_first_read['current']}/{current_first_read['threshold']} ROI-complete toward a first read and {current_portfolio_review['current']}/{current_portfolio_review['threshold']} toward broader review.",
        f"Gate source is {SCORECARD_JSON.name} decision_gate_minimums: anchor_displacement={scorecard_anchor_min}, phase8_promotion_review={scorecard_phase8_min}, real_money_discussion={scorecard_real_money_min}; these are future ROI-complete observation floors, not cleared gates.",
        (
            "Scorecard audit route: current_evidence_summary.json source path scorecard_audit_route points copied "
            "gate/ranking/CI-only/timezone/no-BAQ synchronization checks to "
            f"{scorecard_audit_route.get('markdown_path')} / {scorecard_audit_route.get('json_path')} "
            f"plus {scorecard_audit_route.get('validator_command')}; this route is report-synchronization metadata only"
        ),
        (
            "Rebuild-order route: current_evidence_summary.json source path rebuild_validation_contract routes "
            "scorecard/rules/signals/settlement-ledger byte change through "
            "python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> "
            "python3 validate_current_evidence_summary.py before quoting CURRENT_EVIDENCE_SUMMARY.*; "
            "this is provenance/rebuild metadata only"
        ),
        f"Current settled sample is CD-only: CD_CORE_K8 {rule_progress['CD_CORE_K8']['roi_complete_settled_rows']}, OP_DURABLE_K7 {rule_progress['OP_DURABLE_K7']['roi_complete_settled_rows']}; this is not OP-anchor proof, promotion readiness, live profitability, bankroll guidance, real-money evidence, or cross-family promotion evidence.",
        expected_pdf_source_repair_fragment,
    ]
    pdf_cross_family_current_paper_fragment = (
        "For anchor / paper / watch caveats, read CROSS_FAMILY_DECISION.md and run python3 validate_cross_family_decision.py; stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context and green HTML/PDF validation are not OP-anchor proof."
    )
    html_ci_only_fragment = (
        "OP_REFINED CI-only check: Scorecard CI-only promotion check: "
        f"<code>{CI_ONLY_SOURCE}</code> keeps <code>ci_only_promotion_allowed=false</code>; "
        "OP_REFINED's positive CI lower bound is support context only, not a current-paper promotion trigger, "
        "OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence."
    )
    pdf_ci_only_fragments = [
        "OP_REFINED CI-only check: Scorecard CI-only promotion check:",
        "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K",
        "ci_only_promotion_allowed=false",
        "OP_REFINED's positive CI lower bound",
        "not a current-paper promotion trigger, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
    ]
    scorecard_audit_route_pdf_fragments = [
        "Scorecard audit route:",
        "current_evidence_summary.json source path scorecard_audit_route",
        "copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks",
        "SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json",
        "python3 validate_scorecard_ranking_contract_audit.py",
        "not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
    ]
    rebuild_validation_contract_pdf_fragments = [
        "Rebuild-order route:",
        "current_evidence_summary.json source path rebuild_validation_contract",
        "python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py",
        "before quoting CURRENT_EVIDENCE_SUMMARY.*",
        "provenance/rebuild metadata only",
    ]
    card_fragment = (
        "Current frozen selector benchmark still remains the <strong>Train-only yearly selector</strong> at <strong>+22.46%</strong> walk-forward and <strong>+14.36%</strong> holdout"
    )
    rule_hierarchy_fragments = [
        "The year split is what makes the hierarchy easier to defend honestly.",
        "<li><strong>OP_DURABLE_K7</strong> = safest anchor: mixed holdout, but on the largest OP holdout sample (<strong>2024 -47.41% on 68; 2025 +124.61% on 47</strong>) plus the strongest walk-forward support (<strong>7/10 folds</strong>)</li>",
        "<li><strong>CD_CORE_K8</strong> = paper-worthy, still useful in the primary paper lane: the steadier current paper candidate because it stayed positive in both holdout years (<strong>2024 +45.65% on 41; 2025 +78.21% on 19</strong>)</li>",
        "<li><strong>OP_REFINED_K7</strong> = interesting, but still a challenger not a replacement: prettier aggregate ROI, but still a smaller mixed-year spike (<strong>2024 -25.47% on 33; 2025 +210.02% on 16</strong>)</li>",
        "So the real read is not “highest ROI wins.” It is that CD currently looks steadier, OP_DURABLE still has the stronger anchor-grade evidence base, and OP_REFINED still needs more forward sample before it can challenge the anchor seriously.",
    ]
    story_fragment = (
        "The strongest clean historical numeric gain is the selector-scoring improvement from <strong>+22.46%</strong> to <strong>+30.42%</strong>, "
        "using frozen artifacts and no new rule mining, while the current frozen selector benchmark still remains the <strong>Train-only yearly selector</strong>."
    )
    bar_title_fragment = "<div class=\"bar-title\">Historical selector-scoring ROI</div>"
    phase7_portfolio_row = (
        f"<td data-label=\"Approach\"><strong>{phase7['label']}</strong></td>"
    )
    phase7_portfolio_holdout = (
        f"<td data-label=\"Holdout\" class=\"mono\">{float(phase7['holdout_roi']):+.2f}% • {int(phase7['holdout_races'])} races • 2024 {float(phase7['holdout_2024_roi']):+.2f}% on {int(phase7['holdout_2024_races'])} • 2025 {float(phase7['holdout_2025_roi']):+.2f}% on {int(phase7['holdout_2025_races'])}</td>"
    )
    phase8_portfolio_holdout = (
        f"<td data-label=\"Holdout\" class=\"mono\">{float(phase8['holdout_roi']):+.2f}% • {int(phase8['holdout_races'])} races • 2024 {float(phase8['holdout_2024_roi']):+.2f}% on {int(phase8['holdout_2024_races'])} • 2025 {float(phase8['holdout_2025_roi']):+.2f}% on {int(phase8['holdout_2025_races'])}</td>"
    )
    current_selector_row = (
        f"<td data-label=\"Approach\"><strong>{selector['label']}</strong></td>"
    )
    current_selector_read = "Still the honesty yardstick, just not the best operating recipe for daily use."
    selective_family_fragment = (
        f"+{abs(float(selective['primary_metric'])):.2f}% holdout • 2024 {float(phase7['holdout_2024_roi']):+.2f}% on {int(phase7['holdout_2024_races'])} • 2025 {float(phase7['holdout_2025_roi']):+.2f}% on {int(phase7['holdout_2025_races'])} • +31.34% WF"
    )
    selective_family_read = "Only family with positive current frozen holdout evidence and a practical paper-trade observation path, but the recent path was uneven rather than smooth."
    selective_family_replay_note = "The broader selective-family secondary lines elsewhere in the repo are replay context on walk-forward test years, not extra train-only validation."
    final_stance_fragment = (
        "paper trade the selective rule path, keep Phase 7 as the primary baseline, keep Phase 8 as shadow-only, and keep Harville/XGBoost out of the live betting decision path."
    )
    guardrail_header = "<span class=\"eyeline\">Method-family guardrail</span>"
    guardrail_intro = (
        "This is intentionally separate from the selective-method ranking. First rule out dead-end families, then compare the serious selective contenders against each other."
    )
    stale_phrase = "Use sqrt-dampened selector scoring as the strongest current benchmarked selector variant."
    legacy_alias_title = "<title>Legacy report alias — use dated Superfecta report</title>"
    legacy_alias_redirect = '<meta http-equiv="refresh" content="0; url=Superfecta_Project_Report_2026-04-15.html" />'
    legacy_alias_warning = "This undated HTML file is only a convenience alias. It is not the report trust anchor and should not be treated as a separately validated surface."
    legacy_alias_claim_boundary = (
        "Do not quote ROI, rule hierarchy, paper-trade status, promotion readiness, live profitability, bankroll guidance, or real-money claims from this alias. Use the dated report and validator outputs for those statements."
    )
    legacy_alias_html_target = "<code>Superfecta_Project_Report_2026-04-15.html</code>"
    legacy_alias_pdf_target = "<code>Superfecta_Project_Report_2026-04-15.pdf</code>"
    legacy_alias_disallowed_fragments = [
        "OP_DURABLE_K7",
        "CD_CORE_K8",
        "OP_REFINED_K7",
        "+22.46%",
        "+30.42%",
        "+38.68%",
        "current paper bridge",
        "promotion-ready",
        "real-money evidence",
    ]
    legacy_pdf_alias_required_fragments = [
        "Legacy report alias",
        "Use the dated validated report instead",
        "This undated PDF file is only a convenience alias.",
        "It is not the report trust anchor and should not be treated as a separately validated surface.",
        "Do not quote ROI, rule hierarchy, paper-trade status, promotion readiness, live profitability, bankroll guidance, or real-money claims from this alias.",
        "Superfecta_Project_Report_2026-04-15.html",
        "Superfecta_Project_Report_2026-04-15.pdf",
    ]
    legacy_pdf_alias_disallowed_fragments = [
        "Harville + XGBoost Residual Model Full Training Reruns Complete",
        "strong payout-estimation baseline",
        "validated as a useful payout-correction baseline",
        "two-stage expected-value system",
        "Full Training Rerun Results",
        "ROI engine still needs ranking",
    ]
    legacy_docx_alias_required_fragments = [
        "Legacy report alias",
        "Use the dated validated report instead",
        "This undated DOCX file is only a convenience alias.",
        "It is not the report trust anchor and should not be treated as a separately validated surface.",
        "Do not quote ROI, rule hierarchy, paper-trade status, promotion readiness, live profitability, bankroll guidance, or real-money claims from this alias.",
        "Superfecta_Project_Report_2026-04-15.html",
        "Superfecta_Project_Report_2026-04-15.pdf",
    ]
    legacy_docx_alias_disallowed_fragments = legacy_pdf_alias_disallowed_fragments
    legacy_quick_start_alias_required_fragments = [
        "Legacy quick-start alias",
        "Use the current validated paper-trade runbooks instead.",
        "This PDF is only a legacy convenience alias.",
        "It is not the current quick-start, not a model-deployment guide, and not a separately validated evidence surface.",
        "Do not quote model-performance targets, ML deployment claims, live prediction guidance, bankroll guidance, ROI, promotion readiness, live profitability, or real-money claims from this alias.",
        "PAPER_TRADE_USAGE.md",
        "DAILY_ARTIFACT_GUIDE.md",
        "VALIDATION_QUICKSTART.md",
        "Superfecta_Project_Report_2026-04-15.html",
        "Superfecta_Project_Report_2026-04-15.pdf",
        "BAQ must not be treated as BEL.",
    ]
    legacy_quick_start_alias_disallowed_fragments = [
        "A machine learning system for predicting horse racing superfecta payouts",
        "uses machine learning to improve upon traditional Harville probability models",
        "learns market biases and inefficiencies",
        "Production-ready prediction pipeline",
        "Live prediction workflow",
        "Model Performance Targets",
        "RMSE Improvement: 15-25%",
        "R² Score: 0.65-0.85",
        "validated as a useful payout-correction baseline",
    ]
    legacy_prompt_docx_alias_required_fragments = [
        "Legacy historical prompt alias",
        "Use the current validated project runbooks instead.",
        "This DOCX is only a legacy historical prompt alias.",
        "It is not the current project brief, not a model-training instruction, not a betting-profitability plan, and not a separately validated evidence surface.",
        "Do not quote ML training instructions, 80/20 split guidance, profitability targets, model-deployment claims, bankroll guidance, ROI, promotion readiness, live profitability, or real-money claims from this alias.",
        "COLE_STATUS_AND_PLAN.md",
        "forward_evidence_scorecard.txt",
        "PAPER_TRADE_USAGE.md",
        "DAILY_ARTIFACT_GUIDE.md",
        "VALIDATION_QUICKSTART.md",
        "Superfecta_Project_Report_2026-04-15.html",
        "Historical prompts, old model-training tasks, validation passes, clean scanner runs, model-fit diagnostics, and open paper signals are not live profitability or real-money evidence.",
        "BAQ must not be treated as BEL.",
    ]
    legacy_prompt_docx_alias_disallowed_fragments = [
        "optimizing perimutuel wagering for the superfecta bet",
        "first attempt at using XGBoost",
        "ideally rank the winning combination closer to the top",
        "you should on average win frequently enough to be profitable",
        "beat harville method by atleast 16%",
        "make superfecta betting profitable",
        "80/20 train test split",
        "train whatever ML model you think works best",
        "A100 GPU in google colab",
    ]

    checks: list[dict[str, Any]] = []
    checks.extend(current_bridge_cli_contract_checks(args.current_evidence_json))
    checks.extend(scorecard_cli_gate_contract_checks(args.scorecard_json, args.current_evidence_json))
    checks.append(
        require(
            anchor["tier"] == "ANCHOR" and anchor["rank"] == "1",
            "anchor_source_still_op_durable",
            "forward evidence scorecard still ranks OP_DURABLE_K7 first in the ANCHOR tier",
        )
    )
    checks.append(
        require(
            hero_fragment in text,
            "hero_fragment",
            "hero panel still states the historical selector gain separately from the current frozen benchmark",
        )
    )
    checks.append(
        require(
            metric_fragment in text
            and holdout_winner_fragment in text
            and all(fragment in text for fragment in phase7_rule_component_fragments),
            "metric_fragment",
            "top metric cards still label +30.42% as historical selector-scoring output, make the Phase 7 holdout winner split-aware, and name Phase 7 as the OP/CD rule-component basket with target cards confirmed by daily preflight",
        )
    )
    checks.append(
        require(
            table_evidence_fragment in text and table_decision_fragment in text,
            "selector_table_row",
            "master findings register still distinguishes historical selector scoring from the current BENCHMARK ONLY selector read",
        )
    )
    checks.append(
        require(
            "Selective rules are the only family that earned current-paper credibility." in text
            and "live-paper credibility" not in text,
            "selective_family_current_paper_credibility_wording",
            "HTML trust anchor now describes selective-rule credibility as current-paper rather than live-paper credibility",
        )
    )
    checks.append(
        require(
            operational_shift_fragment in text
            and operations_decision_fragment in text
            and operational_hardening_fragment in text,
            "paper_trade_workflow_not_new_evidence_frame",
            "HTML report now says the paper-trade operating-path upgrade is workflow/reproducibility hardening, not new forward evidence by itself, and that genuinely new forward evidence still requires settled paper trades",
        )
    )
    checks.append(
        require(
            html_evidence_scope_fragment in text,
            "html_report_evidence_scope_boundary",
            "HTML report now says posture changes require settled paper-trade rows with usable ROI coverage, not clean scans, open signals, replay rows, calibration summaries, or another odds-only rerun",
        )
    )
    checks.append(
        require(
            current_evidence["source_consistency"]["overall_match"] is True
            and current_evidence_table_fragment in text
            and current_evidence_decision_fragment in text
            and all(fragment in text for fragment in current_evidence_card_fragments),
            "current_evidence_bridge_card",
            "HTML report now routes current paper-total wording through CURRENT_EVIDENCE_SUMMARY.md / current_evidence_summary.json, pins the matched source-consistency read, routes wrapper-refresh/missing-output/stale right-now cards through the combined operator-status/source-freshness/operator-read-gate path, keeps the source-derived current gates visible, and separates the CD-only settled sample from OP-anchor proof, Phase 8 promotion readiness, live profitability, bankroll guidance, and real-money evidence",
        )
    )
    checks.append(
        require(
            scorecard_gate_read["anchor_displacement_min_roi_complete_settled_observations"]
            == current_first_read["threshold"]
            and scorecard_gate_read["real_money_discussion_min_total_settled_observations_with_usable_roi"]
            == current_portfolio_review["threshold"]
            and scorecard_gate_read["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and scorecard_gate_read["real_money_no_baq_as_bel_required"] is True
            and f"gate source {SCORECARD_JSON.name} decision_gate_minimums anchor_displacement={scorecard_anchor_min}, phase8_promotion_review={scorecard_phase8_min}, real_money_discussion={scorecard_real_money_min}" in text
            and f"Gate source is <code>{SCORECARD_JSON.name}</code> <code>decision_gate_minimums</code>" in text,
            "html_report_gate_source_matches_scorecard_json",
            "HTML report now source-matches its current-paper gate floors to forward_evidence_scorecard.json decision_gate_minimums and preserves the no-BAQ-as-BEL real-money prerequisite as gate metadata",
        )
    )
    checks.append(
        require(
            cross_family_current_paper_fragment in text
            and pdf_cross_family_current_paper_fragment in pdf_text,
            "cross_family_current_paper_route_present",
            "HTML/PDF report now routes anchor / paper / watch current-paper caveat questions to CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py and keeps stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green HTML/PDF validation out of OP-anchor proof or cross-family promotion evidence",
        )
    )
    checks.append(
        require(
            scorecard_ci_only_diagnostic["candidate_rule_id"] == "OP_REFINED_K7"
            and scorecard_ci_only_diagnostic["current_anchor_rule_id"] == "OP_DURABLE_K7"
            and scorecard_ci_only_diagnostic["ci_only_promotion_allowed"] is False
            and scorecard_ci_only_diagnostic["positive_ci_lower_bound_is_support_context"] is True
            and current_ci_only_check["source"] == CI_ONLY_SOURCE
            and current_ci_only_check["scorecard_ci_only_promotion_diagnostic"] == scorecard_ci_only_diagnostic
            and current_ci_only_check["ci_only_promotion_allowed"] is False
            and html_ci_only_fragment in text
            and all(fragment in pdf_text for fragment in pdf_ci_only_fragments),
            "html_pdf_scorecard_ci_only_boundary",
            "HTML/PDF report now carries the scorecard-sourced OP_REFINED CI-only diagnostic from forward_evidence_scorecard.json and current_evidence_summary.json, keeping positive CI support out of current-paper promotion triggers, OP-anchor proof, live profitability, bankroll guidance, and real-money evidence",
        )
    )
    checks.append(
        require(
            scorecard_audit_route_json_read["source"] == "current_evidence_summary.json"
            and scorecard_audit_route_json_read["source_path"] == "scorecard_audit_route"
            and scorecard_audit_route_json_read["markdown_path"] == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route_json_read["json_path"] == "scorecard_ranking_contract_audit.json"
            and scorecard_audit_route_json_read["validator_command"] == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route_json_read["gate_floor_source"] == "forward_evidence_scorecard.json:decision_gate_minimums"
            and scorecard_audit_route_json_read["gate_floor_snapshot"].get(
                "anchor_displacement_min_roi_complete_settled_observations"
            )
            == scorecard_anchor_min
            and scorecard_audit_route_json_read["gate_floor_snapshot"].get(
                "phase8_promotion_review_min_roi_complete_settled_observations"
            )
            == scorecard_phase8_min
            and scorecard_audit_route_json_read["gate_floor_snapshot"].get(
                "real_money_discussion_min_total_settled_observations_with_usable_roi"
            )
            == scorecard_real_money_min
            and scorecard_audit_route_json_read["gate_floor_snapshot"].get("real_money_no_baq_as_bel_required") is True
            and scorecard_audit_route_json_read["artifacts_present"] is True
            and scorecard_audit_route_json_read["not_forward_performance_evidence"] is True
            and scorecard_audit_route_json_read["not_settled_roi_evidence"] is True
            and scorecard_audit_route_json_read["not_promotion_readiness_evidence"] is True
            and scorecard_audit_route_json_read["not_live_profitability_evidence"] is True
            and scorecard_audit_route_json_read["not_bankroll_guidance"] is True
            and scorecard_audit_route_json_read["not_real_money_evidence"] is True
            and "copied 30/20/100 gate floors" in scorecard_audit_route_read
            and "tier-first ranking" in scorecard_audit_route_read
            and "OP_REFINED CI-only support context" in scorecard_audit_route_read
            and "generated-at timezone provenance" in scorecard_audit_route_read
            and "no-BAQ-as-BEL prerequisite" in scorecard_audit_route_read
            and current_evidence_card_fragments[7] in text
            and all(fragment in pdf_text for fragment in scorecard_audit_route_pdf_fragments),
            "html_pdf_scorecard_audit_route",
            "HTML/PDF report now carries current_evidence_summary.json.scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks, while keeping that route out of forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, and real-money evidence",
        )
    )
    checks.append(
        require(
            rebuild_validation_contract_json_read["source"] == "current_evidence_summary.json"
            and rebuild_validation_contract_json_read["source_path"] == "rebuild_validation_contract"
            and rebuild_validation_contract_json_read["upstream_refresh_order"]
            == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and rebuild_validation_contract_json_read["prerequisite_rebuild_command"]
            == "python3 paper_trade_settlement_audit.py"
            and rebuild_validation_contract_json_read["rebuild_command"] == "python3 current_evidence_summary.py"
            and rebuild_validation_contract_json_read["direct_validation_command"]
            == "python3 validate_current_evidence_summary.py"
            and rebuild_validation_contract_json_read[
                "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
            ]
            is True
            and rebuild_validation_contract_json_read["requires_source_consistency_before_quoting_current_totals"]
            is True
            and rebuild_validation_contract_json_read["upstream_refresh_order_is_provenance_metadata_only"] is True
            and rebuild_validation_contract_json_read["green_checks_are_reproducibility_metadata_only"] is True
            and rebuild_validation_contract_json_read["not_settled_roi_or_real_money_evidence"] is True
            and current_evidence_card_fragments[8] in text
            and all(fragment in pdf_text for fragment in rebuild_validation_contract_pdf_fragments),
            "html_pdf_current_evidence_rebuild_validation_contract_route",
            "HTML/PDF report now carries current_evidence_summary.json.rebuild_validation_contract so source-byte changes route through settlement audit -> current bridge -> bridge validator before current totals are quoted, while keeping that route as provenance/rebuild metadata only rather than settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
        )
    )
    checks.append(
        require(
            all(fragment in text for fragment in full_data_retrain_html_fragments)
            and all(fragment in pdf_text for fragment in full_data_retrain_pdf_fragments),
            "full_data_retrain_caveat_route_present",
            "HTML/PDF report now routes full-data XGBoost retrain questions to FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py and keeps exact commands plus RMSE / MAE diagnostics in model-fit context only",
        )
    )
    checks.append(
        require(
            expected_combined_operator_route_card_fragment in text
            and expected_source_repair_fragment in text
            and f"combined operator-status/source-freshness/operator-read-gate route {combined_operator_route_label}" in text
            and (not requires_refresh or "./run_daily_portfolio_observation.sh" in text),
            "current_evidence_combined_operator_read_route",
            "HTML/PDF report now carries the combined operator_status_context / source_freshness / operator_read_gate route, so refresh-required right-now cards trigger the daily wrapper and fresh cards stay in current operator-routing context before instruction or evidence use",
        )
    )
    checks.append(
        require(
            expected_combined_operator_route_card_fragment in text
            and expected_pdf_combined_operator_route_fragment in pdf_text
            and operator_read_gate_json_read.get("source") == "current_evidence_summary.json"
            and operator_read_gate_json_read.get("source_path") == "operator_read_gate"
            and operator_read_gate_json_read.get("gate_status") in {
                "refresh_required_before_evidence_read",
                "current_operator_routing_context_only",
            }
            and operator_read_gate_json_read.get("valid_use") == "operator instruction/evidence-read gating only"
            and isinstance(operator_read_gate_json_read.get("requires_refresh_before_evidence_read"), bool)
            and isinstance(operator_read_gate_json_read.get("has_api_access_failure_context"), bool)
            and isinstance(operator_read_gate_json_read.get("has_scanner_failure_boundary"), bool)
            and isinstance(operator_read_gate_json_read.get("has_stale_cache_fallback_context"), bool)
            and isinstance(operator_read_gate_json_read.get("recommended_command"), str)
            and bool(operator_read_gate_json_read.get("recommended_command"))
            and operator_read_gate_json_read.get("current_top_card_counts_as_no_target_evidence") is False
            and operator_read_gate_json_read.get("current_top_card_counts_as_clean_empty_evidence") is False
            and operator_read_gate_json_read.get("current_top_card_counts_as_bet_readiness_evidence") is False
            and operator_read_gate_json_read.get("current_top_card_counts_as_settled_roi_evidence") is False
            and operator_read_gate_json_read.get("not_forward_performance_evidence") is True
            and operator_read_gate_json_read.get("not_promotion_readiness_evidence") is True
            and operator_read_gate_json_read.get("not_live_profitability_evidence") is True
            and operator_read_gate_json_read.get("not_real_money_evidence") is True,
            "current_evidence_operator_read_gate_route",
            "HTML/PDF report now carries current_evidence_summary.json operator_read_gate as refresh-before-evidence-read routing before stale, stale-cache fallback, or missing-state top-card instruction/evidence use, without treating that state as no-target, clean-empty, bet-readiness, settled-ROI, forward-performance, promotion, live-profitability, bankroll, or real-money evidence",
        )
    )
    checks.append(
        require(
            PDF_REPORT.exists()
            and pdf_page_count >= 1
            and pdf_byte_count > 100_000
            and all(fragment in pdf_text for fragment in pdf_current_evidence_fragments),
            "dated_pdf_derivative_current_evidence_bridge",
            "dated PDF derivative export exists and its extracted text carries the same combined operator-status/source-freshness/operator-read-gate current-evidence bridge, source-derived current gates, CD-only rule mix, and no OP-anchor / no-promotion / no-live-profitability / no-bankroll / no-real-money boundary as the dated HTML trust anchor",
        )
    )
    checks.append(
        require(
            card_fragment in text,
            "validation_upgrade_card",
            "validation-upgrade card still names the current frozen selector benchmark explicitly",
        )
    )
    checks.append(
        require(
            all(fragment in text for fragment in rule_hierarchy_fragments),
            "rule_hierarchy_year_split",
            "HTML report now explains the anchor / paper / watch hierarchy with the explicit 2024-vs-2025 split instead of only aggregate labels",
        )
    )
    checks.append(
        require(
            story_fragment in text,
            "improvement_story",
            "what-got-better story still keeps the historical selector gain separate from the current benchmark",
        )
    )
    checks.append(
        require(
            bar_title_fragment in text,
            "bar_title",
            "quantified-change bar now labels the selector series as historical selector-scoring ROI",
        )
    )
    checks.append(
        require(
            phase7_portfolio_row in text
            and phase7_portfolio_holdout in text
            and phase8_portfolio_holdout in text
            and current_selector_row in text
            and current_selector_read in text,
            "selector_row_preserved",
            "approach table still includes the split-aware Phase 7 and Phase 8 holdout rows plus the train-only yearly selector as the honesty benchmark read",
        )
    )
    checks.append(
        require(
            guardrail_header in text
            and guardrail_intro in text
            and selective_family_fragment in text
            and selective_family_read in text
            and selective_family_replay_note in text,
            "method_family_guardrail_section",
            "HTML report now labels the method-family block as an explicit guardrail, keeps the selective family split-aware instead of only quoting aggregate holdout evidence, and states that broader selective-family secondary lines are replay context rather than extra train-only proof",
        )
    )
    checks.append(
        require(
            final_stance_fragment in text,
            "final_stance_fragment",
            "final stance still preserves the current conservative deployment posture",
        )
    )
    checks.append(
        require(
            legacy_alias_title in legacy_alias_text
            and legacy_alias_redirect in legacy_alias_text
            and legacy_alias_warning in legacy_alias_text
            and legacy_alias_claim_boundary in legacy_alias_text
            and legacy_alias_html_target in legacy_alias_text
            and legacy_alias_pdf_target in legacy_alias_text
            and not any(fragment in legacy_alias_text for fragment in legacy_alias_disallowed_fragments),
            "legacy_alias_redirect_notice",
            "legacy undated HTML alias now redirects to the dated validated pair, says plainly that it is not its own trust anchor, and stays free of ROI / rule / paper-trade / promotion / live-profitability / bankroll / real-money claims",
        )
    )
    checks.append(
        require(
            LEGACY_PDF_ALIAS.exists()
            and legacy_pdf_page_count >= 1
            and legacy_pdf_byte_count > 1_000
            and all(fragment in legacy_pdf_text for fragment in legacy_pdf_alias_required_fragments)
            and not any(fragment in legacy_pdf_text for fragment in legacy_pdf_alias_disallowed_fragments),
            "legacy_pdf_alias_claim_boundary",
            "legacy undated PDF alias is now a claim-free warning/export surface pointing to the dated validated HTML/PDF pair, not the old XGBoost rerun report or a separate evidence source",
        )
    )
    checks.append(
        require(
            LEGACY_DOCX_ALIAS.exists()
            and legacy_docx_byte_count > 1_000
            and all(fragment in legacy_docx_text for fragment in legacy_docx_alias_required_fragments)
            and not any(fragment in legacy_docx_text for fragment in legacy_docx_alias_disallowed_fragments),
            "legacy_docx_alias_claim_boundary",
            "legacy undated DOCX alias is now a claim-free warning document pointing to the dated validated HTML/PDF pair, not the old XGBoost rerun report or a separate evidence source",
        )
    )
    checks.append(
        require(
            LEGACY_QUICK_START_PDF_ALIAS.exists()
            and legacy_quick_start_page_count >= 1
            and legacy_quick_start_byte_count > 1_000
            and all(fragment in legacy_quick_start_pdf_text for fragment in legacy_quick_start_alias_required_fragments)
            and not any(fragment in legacy_quick_start_pdf_text for fragment in legacy_quick_start_alias_disallowed_fragments),
            "legacy_quick_start_pdf_alias_claim_boundary",
            "legacy quick-start PDF alias is now a claim-free warning export pointing to the current paper-trade runbooks, validation guide, and dated report trust anchor, not the old ML/live-prediction quick-start or a separate evidence source",
        )
    )
    checks.append(
        require(
            LEGACY_PROMPT_DOCX_ALIAS.exists()
            and legacy_prompt_docx_byte_count > 1_000
            and all(fragment in legacy_prompt_docx_text for fragment in legacy_prompt_docx_alias_required_fragments)
            and not any(fragment in legacy_prompt_docx_text for fragment in legacy_prompt_docx_alias_disallowed_fragments),
            "legacy_prompt_docx_alias_claim_boundary",
            "legacy OpenClaw prompt DOCX is now a claim-free historical-prompt alias pointing to current status, scorecard, operator, validation, and dated report surfaces, not the old ML/profitability-training prompt or a separate evidence source",
        )
    )
    checks.append(
        require(
            stale_phrase not in text
            and "biggest active OP sample" not in text
            and "still useful in the active lane" not in text
            and "Phase 7 live basket" not in text
            and "Phase 7 live basket" not in pdf_text
            and "Phase 7 live portfolio" not in text
            and "Phase 7 live portfolio" not in pdf_text
            and "live basket" not in text
            and "live basket" not in pdf_text
            and "biggest active OP sample" not in pdf_text
            and "still useful in the active lane" not in pdf_text
            and "Phase 7 OP/CD rule-component basket • 2024 +0.37% on 109 • 2025 +105.38% on 66" in text,
            "stale_phrase_removed",
            "HTML/PDF report no longer calls sqrt-dampened scoring the strongest current benchmarked selector variant and no longer uses active-lane, live-basket, or live-portfolio wording for historical OP/CD hierarchy evidence",
        )
    )

    suite_read = (
        f"HTML report matches frozen posture: anchor={anchor['rule_id']} ({float(anchor['holdout_roi']):+.1f}% on {int(anchor['holdout_races'])}; "
        f"2024={float(anchor['holdout_2024_roi']):+.2f}% on {int(anchor['holdout_2024_races'])}, "
        f"2025={float(anchor['holdout_2025_roi']):+.2f}% on {int(anchor['holdout_2025_races'])}); "
        f"paper={phase7['label']} ({float(phase7['holdout_roi']):+.2f}% on {int(phase7['holdout_races'])}; 2024={float(phase7['holdout_2024_roi']):+.2f}% on {int(phase7['holdout_2024_races'])}, 2025={float(phase7['holdout_2025_roi']):+.2f}% on {int(phase7['holdout_2025_races'])}); "
        "shareable report Phase 7 wording=OP/CD rule-component basket with target cards confirmed by daily preflight, not a standing live-basket/live-portfolio claim; "
        f"selector current benchmark={selector['label']} ({float(selector['wf_roi']):+.2f}% WF, {float(selector['holdout_roi']):+.2f}% holdout, {selector['role']}); "
        f"historical selector improvement=+22.46% to +30.42%; paper-trade hardening=workflow/reproducibility improvement rather than new forward evidence by itself, with genuinely new forward evidence still requiring settled paper trades; evidence scope=settled paper-trade rows with usable ROI coverage can change posture, while clean scans/open signals/historical replay/calibration-only summaries/odds-only reruns cannot; current evidence bridge=CURRENT_EVIDENCE_SUMMARY.md/current_evidence_summary.json source consistency {source_consistency_label}, combined operator-status/source-freshness/operator-read-gate route {combined_operator_route_label}, report gates source-matched to forward_evidence_scorecard.json decision_gate_minimums with anchor_displacement={scorecard_anchor_min}, phase8_promotion_review={scorecard_phase8_min}, and real_money_discussion={scorecard_real_money_min}, scorecard audit route={CURRENT_EVIDENCE_JSON.name}.scorecard_audit_route to {scorecard_audit_route.get('markdown_path')} / {scorecard_audit_route.get('json_path')} plus {scorecard_audit_route.get('validator_command')} for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks as report-synchronization metadata only, rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only, primary paper {current_first_read['current']}/{current_first_read['threshold']} first-read and {current_portfolio_review['current']}/{current_portfolio_review['threshold']} broader-review gates, CD_CORE_K8={rule_progress['CD_CORE_K8']['roi_complete_settled_rows']} ROI-complete rows, OP_DURABLE_K7={rule_progress['OP_DURABLE_K7']['roi_complete_settled_rows']} ROI-complete rows, current settled sample is CD-only context and not OP-anchor evidence, Phase 8 promotion readiness, live profitability, bankroll guidance, or real-money evidence; operator_read_gate read={operator_read_gate_read}; OP_REFINED CI-only route={CI_ONLY_SOURCE} with ci_only_promotion_allowed=false, source-matched between forward_evidence_scorecard.json and current_evidence_summary.json, and positive CI support not a current-paper promotion trigger, OP-anchor proof, live profitability, bankroll guidance, or real-money evidence; direct cross-family current-paper caveat route=CROSS_FAMILY_DECISION.md plus validate_cross_family_decision.py, with stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and green HTML/PDF validation not OP-anchor proof or cross-family promotion evidence; full-data retrain caveat route=FULL_DATA_RETRAIN_ARTIFACTS.md plus validate_full_data_retrain_artifacts.py, with exact retrain/prediction commands and RMSE / MAE diagnostics kept as model-fit reproducibility context only; dated PDF derivative export verified for the combined operator-status/source-freshness/operator-read-gate route, current-evidence bridge, rebuild-order route, scorecard-audit route, OP_REFINED CI-only boundary, cross-family current-paper caveat route, and full-data retrain caveat route; Phase 8={phase8['role']} ({float(phase8['holdout_roi']):+.2f}% on {int(phase8['holdout_races'])}; 2024={float(phase8['holdout_2024_roi']):+.2f}% on {int(phase8['holdout_2024_races'])}, 2025={float(phase8['holdout_2025_roi']):+.2f}% on {int(phase8['holdout_2025_races'])}); method roles={selective['role']} / {harville['role']} / {xgboost['role']}; broader selective-family secondary lines elsewhere stay replay-context rather than extra train-only proof; legacy alias=redirect-only warning page with claim-free boundary to the dated validated HTML trust anchor and its derivative PDF export; legacy PDF alias=claim-free warning export, not the old XGBoost rerun report or a separate evidence source; legacy DOCX alias=claim-free warning document, not the old XGBoost rerun report or a separate evidence source; legacy quick-start PDF alias=claim-free warning export, not the old ML/live-prediction quick-start or a separate evidence source; legacy OpenClaw prompt DOCX alias=claim-free historical-prompt warning document, not the old ML/profitability-training prompt or a separate evidence source"
    )

    payload = {
        "suite_status": "pass",
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "scorecard_decision_gate_minimums_read": scorecard_gate_read,
        "scorecard_ci_only_diagnostic": scorecard_ci_only_diagnostic,
        "current_evidence_ci_only_check": current_ci_only_check,
        "current_evidence_operator_read_gate_read": operator_read_gate_json_read,
        "current_evidence_scorecard_audit_route_read": scorecard_audit_route_json_read,
        "current_evidence_rebuild_validation_contract_read": rebuild_validation_contract_json_read,
        "summary": {
            "suite_read": suite_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }

    out_dir = Path(args.out_dir)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name
    out_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Superfecta HTML Report Validation",
        "",
        "This report checks that the shareable HTML report keeps the historical selector-scoring gain separate from the current frozen selector benchmark, deployment posture, and evidence-scope boundary.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Target file: `{REPORT.name}`",
        f"- Checks: {len(checks)}",
        "- Result: PASS",
        "",
        "## Checks",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for item in checks:
        lines.append(f"| {item['check']} | {item['status'].upper()} | {item['detail']} |")

    lines.extend(
        [
            "",
            "## Current Read",
            "",
            f"- Suite read: {suite_read}",
            f"- Hero fragment: {hero_fragment}",
            f"- Metric fragment: {metric_fragment}",
            f"- Selector table evidence: {table_evidence_fragment}",
            f"- Selector table decision: {table_decision_fragment}",
            f"- Operational shift fragment: {operational_shift_fragment}",
            f"- Operations decision fragment: {operations_decision_fragment}",
            f"- Evidence-scope line: {html_evidence_scope_fragment}",
            f"- Current-evidence table fragment: {current_evidence_table_fragment}",
            f"- Current-evidence decision fragment: {current_evidence_decision_fragment}",
            f"- Current-evidence operator-read-gate read: {operator_read_gate_read}",
            f"- Scorecard gate source: `{SCORECARD_JSON.name}` `decision_gate_minimums` (`anchor_displacement={scorecard_anchor_min}`, `phase8_promotion_review={scorecard_phase8_min}`, `real_money_discussion={scorecard_real_money_min}`)",
            f"- Scorecard audit route: `{CURRENT_EVIDENCE_JSON.name}` `scorecard_audit_route` points to `{scorecard_audit_route.get('markdown_path')}` / `{scorecard_audit_route.get('json_path')}` plus `{scorecard_audit_route.get('validator_command')}` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks; this is report-synchronization metadata only, not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- Rebuild validation contract: `{CURRENT_EVIDENCE_JSON.name}` `rebuild_validation_contract` order `{rebuild_order_arrow}`; this is provenance/rebuild metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- OP_REFINED CI-only route: `{CI_ONLY_SOURCE}` with `ci_only_promotion_allowed=false`; positive CI support is not a current-paper promotion trigger, OP-anchor proof, live profitability, bankroll guidance, or real-money evidence.",
            f"- Direct cross-family caveat route: `{CROSS_FAMILY_MD.name}` plus `{CROSS_FAMILY_VALIDATOR.name}`; green HTML/PDF validation is not OP-anchor proof or cross-family promotion evidence.",
            "- Full-data retrain caveat route: `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py`; exact retrain/prediction commands and RMSE / MAE diagnostics are model-fit reproducibility context only.",
            f"- Operational hardening fragment: {operational_hardening_fragment}",
            f"- Rule hierarchy anchor fragment: {rule_hierarchy_fragments[1]}",
            f"- Rule hierarchy paper fragment: {rule_hierarchy_fragments[2]}",
            f"- Rule hierarchy watch fragment: {rule_hierarchy_fragments[3]}",
            f"- Method-family guardrail header: {guardrail_header}",
            f"- Legacy alias warning: {legacy_alias_warning}",
            f"- Legacy alias claim boundary: {legacy_alias_claim_boundary}",
            f"- Dated PDF derivative: `{PDF_REPORT.name}` ({pdf_page_count} pages, {pdf_byte_count} bytes)",
            f"- Legacy PDF alias: `{LEGACY_PDF_ALIAS.name}` ({legacy_pdf_page_count} pages, {legacy_pdf_byte_count} bytes)",
            f"- Legacy DOCX alias: `{LEGACY_DOCX_ALIAS.name}` ({legacy_docx_byte_count} bytes)",
            "",
            "## Source Artifacts",
            "",
            f"- `{SCORECARD_CSV.name}`",
            f"- `{SCORECARD_JSON.name}`",
            f"- `{PORTFOLIO_CSV.name}`",
            f"- `{METHOD_CSV.name}`",
            f"- `{CURRENT_EVIDENCE_JSON.name}`",
            "- `SCORECARD_RANKING_CONTRACT_AUDIT.md`",
            "- `scorecard_ranking_contract_audit.json`",
            "- `validate_scorecard_ranking_contract_audit.py`",
            f"- `{CROSS_FAMILY_MD.name}`",
            f"- `{CROSS_FAMILY_VALIDATOR.name}`",
            "- `FULL_DATA_RETRAIN_ARTIFACTS.md`",
            "- `validate_full_data_retrain_artifacts.py`",
            f"- `{PDF_REPORT.name}`",
            f"- `{LEGACY_ALIAS.name}`",
            f"- `{LEGACY_PDF_ALIAS.name}`",
            f"- `{LEGACY_DOCX_ALIAS.name}`",
        ]
    )

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
