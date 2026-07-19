#!/usr/bin/env python3
"""
Validation for op_anchor_method_comparison.py.

Purpose:
- keep the OP-centered method comparison reproducible
- pin the current read that OP_DURABLE_K7 stays the safest anchor
- make sure Harville and the current odds-only XGBoost path remain in benchmark/research lanes
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

import op_anchor_method_comparison as oamc

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "op_anchor_method_comparison.py"
OUT_MD = BASE / "OP_ANCHOR_METHOD_COMPARISON.md"
OUT_JSON = BASE / "op_anchor_method_comparison.json"
REPORT_DIR = BASE / "out" / "status_validation" / "op_anchor_method_comparison"
REPORT_MD = REPORT_DIR / "op_anchor_method_comparison_validation.md"
REPORT_JSON = REPORT_DIR / "op_anchor_method_comparison_validation.json"
TMP_PARENT = REPORT_DIR / "_tmp"
REBUILD_COMMAND = "python3 validate_op_anchor_method_comparison.py"


def require(condition: bool, label: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    return {"check": label, "status": "pass", "detail": detail}


def build_expected_json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2) + "\n"


def build_expected_cli_stdout(markdown: str, md_name: str = "OP_ANCHOR_METHOD_COMPARISON.md", json_name: str = "op_anchor_method_comparison.json") -> str:
    return markdown + f"Saved: {md_name}\nSaved: {json_name}\n"


def parse_source_provenance_table(markdown: str) -> dict[str, dict[str, Any]]:
    try:
        section = markdown.split("## Source Provenance\n\n", 1)[1].split("## Validation", 1)[0]
    except IndexError as exc:
        raise AssertionError("OP_ANCHOR_METHOD_COMPARISON.md source provenance section could not be isolated") from exc

    rows_started = False
    row_lines: list[str] = []
    for line in section.splitlines():
        if line == "| Source | File | Bytes | SHA-256 |":
            rows_started = True
            continue
        if rows_started and line == "|---|---|---:|---|":
            continue
        if rows_started:
            if not line.startswith("| "):
                break
            row_lines.append(line)

    if not row_lines:
        raise AssertionError("OP_ANCHOR_METHOD_COMPARISON.md source provenance table could not be parsed")

    parsed: dict[str, dict[str, Any]] = {}
    for line in row_lines:
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) != 4:
            raise AssertionError(f"unexpected OP-anchor source provenance row shape: {line}")
        label, path_cell, bytes_cell, sha_cell = parts
        parsed[label] = {
            "path": path_cell.strip("`"),
            "bytes": int(bytes_cell),
            "sha256": sha_cell.strip("`"),
        }
    return parsed


def prepare_tmp_parent() -> Path:
    """Use project-local scratch space so CLI fixture writes avoid system temp quotas."""
    if TMP_PARENT.exists():
        shutil.rmtree(TMP_PARENT)
    TMP_PARENT.mkdir(parents=True, exist_ok=True)
    return TMP_PARENT


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_parent = prepare_tmp_parent()
    scratch_meta = {
        "tmp_parent": str(tmp_parent),
        "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
        "tmp_parent_cleared_before_fixture_run": True,
    }

    if not OUT_MD.exists() or not OUT_JSON.exists():
        raise AssertionError("expected OP-anchor comparison artifacts were not created")

    rebuilt_payload = oamc.build_payload()
    rebuilt_json_text = build_expected_json_text(rebuilt_payload)
    rebuilt_markdown = oamc.build_markdown(rebuilt_payload)
    saved_json_text = OUT_JSON.read_text(encoding="utf-8")
    saved_md = OUT_MD.read_text(encoding="utf-8")
    if saved_json_text != rebuilt_json_text:
        raise AssertionError("op_anchor_method_comparison.json drifted from a fresh build_payload() rebuild")
    if saved_md != rebuilt_markdown:
        raise AssertionError("OP_ANCHOR_METHOD_COMPARISON.md drifted from a fresh build_markdown() rebuild")

    payload = json.loads(saved_json_text)
    markdown = saved_md
    rows = {row["approach_id"]: row for row in payload["rows"]}
    anchor_context = payload["anchor_context"]
    paper_basket_context_rows = payload["paper_basket_context"]
    paper_basket_context = {row["rule_id"]: row for row in paper_basket_context_rows}
    challenger_diagnostic = payload["op_challenger_diagnostic"]
    current = payload["current_read"]
    current_operator_boundary = payload["current_operator_boundary"]
    current_gate_progress = payload["current_gate_progress"]
    decision_gates = {gate["gate"]: gate for gate in payload["decision_gates"]}
    evidence_boundary = payload["evidence_boundary"]
    evidence_boundary_text = payload["evidence_boundary_text"]
    anchor_review_policy = payload["anchor_review_policy"]
    scorecard_decision_gate_minimums = payload["scorecard_decision_gate_minimums"]
    source_provenance = payload["source_provenance"]
    source_fingerprints = source_provenance["source_fingerprints"]
    scorecard_ranking_contract = payload["scorecard_ranking_contract"]
    source_scorecard_payload = json.loads(oamc.SCORECARD_JSON.read_text(encoding="utf-8"))
    source_ci_diagnostic = source_scorecard_payload["ci_only_promotion_diagnostics"]["OP_REFINED_K7"]
    expected_anchor_review_policy = oamc.build_anchor_review_policy(source_scorecard_payload, oamc.SCORECARD_JSON)
    expected_current_operator_boundary = oamc.load_current_operator_boundary(oamc.CURRENT_EVIDENCE_JSON)
    expected_current_gate_progress = oamc.load_current_gate_progress(oamc.CURRENT_EVIDENCE_JSON)
    source_current_evidence_payload = json.loads(oamc.CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8"))
    source_current_gate_progress = source_current_evidence_payload["decision_gate_progress"]
    source_operator_read_gate = source_current_evidence_payload["operator_read_gate"]
    source_scorecard_audit_route = source_current_evidence_payload["scorecard_audit_route"]
    source_rebuild_validation_contract = source_current_evidence_payload["rebuild_validation_contract"]
    source_operator_status_context = source_current_evidence_payload["current_paper_status"]["operator_status_context"]
    source_operator_gate_status = source_operator_read_gate.get("gate_status")
    source_operator_gate_read = str(source_operator_read_gate.get("read") or "")
    source_operator_requires_refresh = bool(source_operator_read_gate.get("requires_refresh_before_evidence_read"))
    if source_operator_requires_refresh:
        operator_read_gate_branch_ok = (
            source_operator_gate_status == "refresh_required_before_evidence_read"
            and source_operator_read_gate.get("recommended_command") == "./run_daily_portfolio_observation.sh"
            and source_operator_read_gate.get("has_wrapper_refresh_action") is True
            and "Refresh/recheck with `./run_daily_portfolio_observation.sh`" in source_operator_gate_read
            and "not a no-target, clean-empty, bet-readiness, settled-ROI" in source_operator_gate_read
        )
    else:
        operator_read_gate_branch_ok = (
            source_operator_gate_status == "current_operator_routing_context_only"
            and source_operator_read_gate.get("recommended_command")
            == source_operator_status_context.get("best_action_command")
            and source_operator_read_gate.get("has_wrapper_refresh_action") is False
            and "current operator routing context" in source_operator_gate_read
            and "not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence"
            in source_operator_gate_read
        )
    source_open_queue = source_current_evidence_payload["current_paper_status"]["primary"][
        "open_settlement_queue_by_rule"
    ]
    scorecard_audit_route = current_operator_boundary.get("scorecard_audit_route", {})
    scorecard_audit_snapshot = scorecard_audit_route.get("gate_floor_snapshot", {})
    rebuild_validation_contract = current_operator_boundary.get("rebuild_validation_contract", {})
    rebuild_order_commands = [
        str(row.get("command") or "")
        for row in rebuild_validation_contract.get("upstream_refresh_order", [])
        if isinstance(row, dict)
    ]

    checks: list[dict[str, Any]] = []
    checks.append(
        require(
            saved_json_text == rebuilt_json_text,
            "json_matches_rebuild",
            "op_anchor_method_comparison.json still matches a fresh build_payload() rebuild",
        )
    )
    checks.append(
        require(
            saved_md == rebuilt_markdown,
            "markdown_matches_rebuild",
            "OP_ANCHOR_METHOD_COMPARISON.md still matches a fresh build_markdown() rebuild",
        )
    )

    with tempfile.TemporaryDirectory(prefix="op_anchor_method_comparison_", dir=tmp_parent) as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        pinned_dir = tmpdir / "pinned_out"
        pinned_md = pinned_dir / "OP_ANCHOR_CUSTOM.md"
        pinned_json = pinned_dir / "op_anchor_custom.json"
        alt_scorecard_csv = tmpdir / "alt_forward_evidence_scorecard.csv"
        alt_scorecard_json = tmpdir / "alt_forward_evidence_scorecard.json"
        alt_compare_csv = tmpdir / "alt_compare_main_approaches.csv"
        alt_method_csv = tmpdir / "alt_method_family_decision_card.csv"
        alt_cross_csv = tmpdir / "alt_cross_family_decision_card.csv"
        alt_ab_json = tmpdir / "alt_ab_downstream_comparison_results.json"
        alt_current_evidence_json = tmpdir / "alt_current_evidence_summary.json"
        drift_scorecard_csv = tmpdir / "drift_forward_evidence_scorecard.csv"
        drift_md = tmpdir / "OP_ANCHOR_DRIFT.md"
        drift_json = tmpdir / "op_anchor_drift.json"
        missing_scorecard_csv = tmpdir / "missing_op_refined_scorecard.csv"
        missing_cross_csv = tmpdir / "missing_primary_shadow_cross_family.csv"
        missing_ab_json = tmpdir / "missing_delta_ab_results.json"
        bad_forward_trust_contract_json = tmpdir / "bad_forward_trust_contract_scorecard.json"
        missing_gate_minimum_json = tmpdir / "missing_gate_minimum_scorecard.json"
        missing_gate_output_dir = tmpdir / "missing_gate_should_not_exist"
        missing_gate_should_not_write_md = missing_gate_output_dir / "OP_ANCHOR_MISSING_GATE.md"
        missing_gate_should_not_write_json = missing_gate_output_dir / "op_anchor_missing_gate.json"
        bad_current_evidence_json = tmpdir / "bad_generated_at_current_evidence_summary.json"
        bad_current_evidence_output_dir = tmpdir / "bad_current_evidence_nested_output" / "artifacts"
        bad_current_evidence_should_not_write_md = (
            bad_current_evidence_output_dir / "bad_current_evidence_should_not_write.md"
        )
        bad_current_evidence_should_not_write_json = (
            bad_current_evidence_output_dir / "bad_current_evidence_should_not_write.json"
        )
        missing_operator_read_gate_json = tmpdir / "missing_operator_read_gate_current_evidence_summary.json"
        missing_operator_read_gate_output_dir = tmpdir / "missing_operator_read_gate_nested_output" / "artifacts"
        missing_operator_read_gate_should_not_write_md = (
            missing_operator_read_gate_output_dir / "missing_operator_read_gate_should_not_write.md"
        )
        missing_operator_read_gate_should_not_write_json = (
            missing_operator_read_gate_output_dir / "missing_operator_read_gate_should_not_write.json"
        )
        missing_rebuild_contract_json = tmpdir / "missing_rebuild_contract_current_evidence_summary.json"
        missing_rebuild_contract_output_dir = tmpdir / "missing_rebuild_contract_nested_output" / "artifacts"
        missing_rebuild_contract_should_not_write_md = (
            missing_rebuild_contract_output_dir / "missing_rebuild_contract_should_not_write.md"
        )
        missing_rebuild_contract_should_not_write_json = (
            missing_rebuild_contract_output_dir / "missing_rebuild_contract_should_not_write.json"
        )
        weakened_rebuild_contract_json = tmpdir / "weakened_rebuild_contract_current_evidence_summary.json"
        weakened_rebuild_contract_output_dir = tmpdir / "weakened_rebuild_contract_nested_output" / "artifacts"
        weakened_rebuild_contract_should_not_write_md = (
            weakened_rebuild_contract_output_dir / "weakened_rebuild_contract_should_not_write.md"
        )
        weakened_rebuild_contract_should_not_write_json = (
            weakened_rebuild_contract_output_dir / "weakened_rebuild_contract_should_not_write.json"
        )
        missing_source_freshness_json = tmpdir / "missing_source_freshness_current_evidence_summary.json"
        missing_source_freshness_output_dir = tmpdir / "missing_source_freshness_nested_output" / "artifacts"
        missing_source_freshness_should_not_write_md = (
            missing_source_freshness_output_dir / "missing_source_freshness_should_not_write.md"
        )
        missing_source_freshness_should_not_write_json = (
            missing_source_freshness_output_dir / "missing_source_freshness_should_not_write.json"
        )
        missing_source_freshness_reference_json = (
            tmpdir / "missing_source_freshness_reference_current_evidence_summary.json"
        )
        missing_source_freshness_reference_output_dir = (
            tmpdir / "missing_source_freshness_reference_nested_output" / "artifacts"
        )
        missing_source_freshness_reference_should_not_write_md = (
            missing_source_freshness_reference_output_dir
            / "missing_source_freshness_reference_should_not_write.md"
        )
        missing_source_freshness_reference_should_not_write_json = (
            missing_source_freshness_reference_output_dir
            / "missing_source_freshness_reference_should_not_write.json"
        )
        missing_refresh_action_boundary_json = (
            tmpdir / "missing_refresh_action_boundary_current_evidence_summary.json"
        )
        missing_refresh_action_boundary_output_dir = (
            tmpdir / "missing_refresh_action_boundary_nested_output" / "artifacts"
        )
        missing_refresh_action_boundary_should_not_write_md = (
            missing_refresh_action_boundary_output_dir
            / "missing_refresh_action_boundary_should_not_write.md"
        )
        missing_refresh_action_boundary_should_not_write_json = (
            missing_refresh_action_boundary_output_dir
            / "missing_refresh_action_boundary_should_not_write.json"
        )
        missing_refresh_action_boundary_field_json = (
            tmpdir / "missing_refresh_action_boundary_field_current_evidence_summary.json"
        )
        missing_refresh_action_boundary_field_output_dir = (
            tmpdir / "missing_refresh_action_boundary_field_nested_output" / "artifacts"
        )
        missing_refresh_action_boundary_field_should_not_write_md = (
            missing_refresh_action_boundary_field_output_dir
            / "missing_refresh_action_boundary_field_should_not_write.md"
        )
        missing_refresh_action_boundary_field_should_not_write_json = (
            missing_refresh_action_boundary_field_output_dir
            / "missing_refresh_action_boundary_field_should_not_write.json"
        )
        false_refresh_action_boundary_flag_json = (
            tmpdir / "false_refresh_action_boundary_flag_current_evidence_summary.json"
        )
        false_refresh_action_boundary_flag_output_dir = (
            tmpdir / "false_refresh_action_boundary_flag_nested_output" / "artifacts"
        )
        false_refresh_action_boundary_flag_should_not_write_md = (
            false_refresh_action_boundary_flag_output_dir
            / "false_refresh_action_boundary_flag_should_not_write.md"
        )
        false_refresh_action_boundary_flag_should_not_write_json = (
            false_refresh_action_boundary_flag_output_dir
            / "false_refresh_action_boundary_flag_should_not_write.json"
        )
        false_refresh_accounting_flag_json = (
            tmpdir / "false_refresh_accounting_flag_current_evidence_summary.json"
        )
        false_refresh_accounting_flag_output_dir = (
            tmpdir / "false_refresh_accounting_flag_nested_output" / "artifacts"
        )
        false_refresh_accounting_flag_should_not_write_md = (
            false_refresh_accounting_flag_output_dir
            / "false_refresh_accounting_flag_should_not_write.md"
        )
        false_refresh_accounting_flag_should_not_write_json = (
            false_refresh_accounting_flag_output_dir
            / "false_refresh_accounting_flag_should_not_write.json"
        )
        for src in [
            SCRIPT,
            oamc.SCORECARD_CSV,
            oamc.SCORECARD_JSON,
            oamc.COMPARE_CSV,
            oamc.METHOD_CSV,
            oamc.CROSS_FAMILY_CSV,
            oamc.AB_JSON,
            oamc.CURRENT_EVIDENCE_JSON,
        ]:
            shutil.copy2(src, tmpdir / src.name)
        shutil.copy2(oamc.SCORECARD_CSV, alt_scorecard_csv)
        shutil.copy2(oamc.SCORECARD_JSON, alt_scorecard_json)
        shutil.copy2(oamc.COMPARE_CSV, alt_compare_csv)
        shutil.copy2(oamc.METHOD_CSV, alt_method_csv)
        shutil.copy2(oamc.CROSS_FAMILY_CSV, alt_cross_csv)
        shutil.copy2(oamc.AB_JSON, alt_ab_json)
        shutil.copy2(oamc.CURRENT_EVIDENCE_JSON, alt_current_evidence_json)
        cli_result = subprocess.run(
            [sys.executable, SCRIPT.name],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        cli_json_text = (tmpdir / OUT_JSON.name).read_text(encoding="utf-8")
        cli_md = (tmpdir / OUT_MD.name).read_text(encoding="utf-8")
        if cli_json_text != rebuilt_json_text:
            raise AssertionError("CLI-generated op_anchor_method_comparison.json drifted from a fresh build_payload() rebuild")
        if cli_md != rebuilt_markdown:
            raise AssertionError("CLI-generated OP_ANCHOR_METHOD_COMPARISON.md drifted from a fresh build_markdown() rebuild")
        expected_cli_stdout = build_expected_cli_stdout(cli_md)
        if cli_result.stdout != expected_cli_stdout:
            raise AssertionError("op_anchor_method_comparison.py CLI stdout no longer matches the generated markdown plus Saved: lines")

        pinned_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--scorecard-csv",
                str(alt_scorecard_csv),
                "--scorecard-json",
                str(alt_scorecard_json),
                "--compare-csv",
                str(alt_compare_csv),
                "--method-csv",
                str(alt_method_csv),
                "--cross-family-csv",
                str(alt_cross_csv),
                "--ab-json",
                str(alt_ab_json),
                "--current-evidence-json",
                str(alt_current_evidence_json),
                "--md-output",
                str(pinned_md),
                "--json-output",
                str(pinned_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        pinned_json_text = pinned_json.read_text(encoding="utf-8")
        pinned_md_text = pinned_md.read_text(encoding="utf-8")
        pinned_payload = oamc.build_payload(
            scorecard_csv=alt_scorecard_csv,
            scorecard_json=alt_scorecard_json,
            compare_csv=alt_compare_csv,
            method_csv=alt_method_csv,
            cross_family_csv=alt_cross_csv,
            ab_json=alt_ab_json,
            current_evidence_json=alt_current_evidence_json,
        )
        pinned_expected_json_text = build_expected_json_text(pinned_payload)
        pinned_expected_md = oamc.build_markdown(
            pinned_payload,
            scorecard_csv_name=alt_scorecard_csv.name,
            scorecard_json_name=alt_scorecard_json.name,
            compare_csv_name=alt_compare_csv.name,
            method_csv_name=alt_method_csv.name,
            cross_family_csv_name=alt_cross_csv.name,
            ab_json_name=alt_ab_json.name,
            current_evidence_json_name=alt_current_evidence_json.name,
            md_output_name=pinned_md.name,
            json_output_name=pinned_json.name,
        )
        if pinned_json_text != pinned_expected_json_text:
            raise AssertionError("Pinned/custom-output op_anchor_method_comparison.json drifted from a fresh rebuild")
        if pinned_md_text != pinned_expected_md:
            raise AssertionError("Pinned/custom-output OP-anchor markdown drifted from a fresh rebuild")
        expected_pinned_stdout = build_expected_cli_stdout(pinned_md_text, md_name=pinned_md.name, json_name=pinned_json.name)
        if pinned_result.stdout != expected_pinned_stdout:
            raise AssertionError("Pinned/custom-output op_anchor_method_comparison.py CLI stdout no longer matches the generated markdown plus Saved: lines")

        drift_scorecard_csv.write_text(alt_scorecard_csv.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        drift_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--scorecard-csv",
                str(drift_scorecard_csv),
                "--scorecard-json",
                str(alt_scorecard_json),
                "--compare-csv",
                str(alt_compare_csv),
                "--method-csv",
                str(alt_method_csv),
                "--cross-family-csv",
                str(alt_cross_csv),
                "--ab-json",
                str(alt_ab_json),
                "--current-evidence-json",
                str(alt_current_evidence_json),
                "--md-output",
                str(drift_md),
                "--json-output",
                str(drift_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        drift_payload = json.loads(drift_json.read_text(encoding="utf-8"))
        pinned_without_provenance = {key: value for key, value in pinned_payload.items() if key != "source_provenance"}
        drift_without_provenance = {key: value for key, value in drift_payload.items() if key != "source_provenance"}
        if drift_without_provenance != pinned_without_provenance:
            raise AssertionError("Row-identical scorecard byte drift changed the OP-anchor comparison evidence rows or guardrails")
        pinned_scorecard_fingerprint = pinned_payload["source_provenance"]["source_fingerprints"]["forward_evidence_scorecard"]
        drift_scorecard_fingerprint = drift_payload["source_provenance"]["source_fingerprints"]["forward_evidence_scorecard"]
        if drift_scorecard_fingerprint["sha256"] == pinned_scorecard_fingerprint["sha256"]:
            raise AssertionError("Row-identical scorecard byte drift did not update the scorecard source fingerprint")
        if drift_scorecard_fingerprint["bytes"] <= pinned_scorecard_fingerprint["bytes"]:
            raise AssertionError("Row-identical scorecard byte drift did not increase the recorded scorecard byte count")
        if "drift_forward_evidence_scorecard.csv" not in drift_result.stdout:
            raise AssertionError("Row-identical scorecard byte drift render did not show the custom scorecard source filename in stdout")

        missing_scorecard_df = pd.read_csv(alt_scorecard_csv)
        missing_scorecard_df = missing_scorecard_df[missing_scorecard_df["rule_id"] != "OP_REFINED_K7"].copy()
        missing_scorecard_df.to_csv(missing_scorecard_csv, index=False)
        missing_scorecard_result = subprocess.run(
            [sys.executable, SCRIPT.name, "--scorecard-csv", str(missing_scorecard_csv)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_scorecard_result.returncode == 0:
            raise AssertionError("op_anchor_method_comparison.py unexpectedly accepted a scorecard missing OP_REFINED_K7")
        missing_scorecard_text = f"{missing_scorecard_result.stdout}\n{missing_scorecard_result.stderr}"
        if "missing required scorecard rows: OP_REFINED_K7" not in missing_scorecard_text:
            raise AssertionError("scorecard-row failure no longer explains that OP_REFINED_K7 is required for the OP-anchor comparison")

        bad_forward_trust_contract_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        bad_forward_trust_contract_payload["ranking_contract"]["forward_trust_is_secondary_within_tier"] = False
        bad_forward_trust_contract_json.write_text(
            json.dumps(bad_forward_trust_contract_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        bad_forward_trust_result = subprocess.run(
            [sys.executable, SCRIPT.name, "--scorecard-json", str(bad_forward_trust_contract_json)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if bad_forward_trust_result.returncode == 0:
            raise AssertionError("op_anchor_method_comparison.py unexpectedly accepted a scorecard JSON that demoted forward_trust from secondary-within-tier metadata")
        bad_forward_trust_text = f"{bad_forward_trust_result.stdout}\n{bad_forward_trust_result.stderr}"
        if "ranking_contract no longer marks forward_trust_is_secondary_within_tier=true" not in bad_forward_trust_text:
            raise AssertionError("scorecard ranking-contract failure no longer explains that forward_trust must remain secondary within tier")

        missing_gate_minimum_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        del missing_gate_minimum_payload["decision_gate_minimums"]["phase8_promotion_review"]["min_roi_complete_settled_observations"]
        missing_gate_minimum_json.write_text(
            json.dumps(missing_gate_minimum_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_gate_minimum_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--scorecard-json",
                str(missing_gate_minimum_json),
                "--md-output",
                str(missing_gate_should_not_write_md),
                "--json-output",
                str(missing_gate_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_gate_minimum_result.returncode == 0:
            raise AssertionError("op_anchor_method_comparison.py unexpectedly accepted a scorecard JSON missing a decision_gate_minimums threshold")
        missing_gate_minimum_text = f"{missing_gate_minimum_result.stdout}\n{missing_gate_minimum_result.stderr}"
        if "missing required JSON path: decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations" not in missing_gate_minimum_text:
            raise AssertionError("scorecard gate-minimum failure no longer explains that the Phase 8 promotion-review threshold is required")
        if missing_gate_output_dir.exists() or missing_gate_should_not_write_md.exists() or missing_gate_should_not_write_json.exists():
            raise AssertionError("missing scorecard gate failure created partial OP-anchor output paths before failing")

        missing_cross_df = pd.read_csv(alt_cross_csv)
        missing_cross_df = missing_cross_df[missing_cross_df["shadow_rank"] != "PRIMARY_SHADOW"].copy()
        missing_cross_df.to_csv(missing_cross_csv, index=False)
        missing_cross_result = subprocess.run(
            [sys.executable, SCRIPT.name, "--cross-family-csv", str(missing_cross_csv)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_cross_result.returncode == 0:
            raise AssertionError("op_anchor_method_comparison.py unexpectedly accepted a cross-family card missing PRIMARY_SHADOW")
        missing_cross_text = f"{missing_cross_result.stdout}\n{missing_cross_result.stderr}"
        if "missing required cross-family shadow ranks: PRIMARY_SHADOW" not in missing_cross_text:
            raise AssertionError("cross-family failure no longer explains the missing PRIMARY_SHADOW source row")

        missing_ab_payload = json.loads(alt_ab_json.read_text(encoding="utf-8"))
        del missing_ab_payload["ev_engine_comparison"]["delta"]
        missing_ab_json.write_text(json.dumps(missing_ab_payload, indent=2) + "\n", encoding="utf-8")
        missing_ab_result = subprocess.run(
            [sys.executable, SCRIPT.name, "--ab-json", str(missing_ab_json)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_ab_result.returncode == 0:
            raise AssertionError("op_anchor_method_comparison.py unexpectedly accepted AB JSON missing the delta block")
        missing_ab_text = f"{missing_ab_result.stdout}\n{missing_ab_result.stderr}"
        if "missing required JSON path: ev_engine_comparison.delta.ev_pass_count_delta" not in missing_ab_text:
            raise AssertionError("AB-json failure no longer explains the missing ev_engine_comparison.delta path")

        bad_current_evidence_payload = json.loads(alt_current_evidence_json.read_text(encoding="utf-8"))
        bad_current_evidence_payload["generated_at"] = "2026-06-26 18:12:48"
        bad_current_evidence_json.write_text(
            json.dumps(bad_current_evidence_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        bad_current_evidence_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(bad_current_evidence_json),
                "--md-output",
                str(bad_current_evidence_should_not_write_md),
                "--json-output",
                str(bad_current_evidence_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if bad_current_evidence_result.returncode == 0:
            raise AssertionError("op_anchor_method_comparison.py unexpectedly accepted current-evidence JSON with a timezone-naive generated_at")
        bad_current_evidence_text = f"{bad_current_evidence_result.stdout}\n{bad_current_evidence_result.stderr}"
        if "generated_at must be timezone-aware ISO provenance metadata" not in bad_current_evidence_text:
            raise AssertionError("current-evidence generated_at failure no longer explains that timestamp provenance must be timezone-aware")
        if (
            bad_current_evidence_output_dir.exists()
            or bad_current_evidence_should_not_write_md.exists()
            or bad_current_evidence_should_not_write_json.exists()
        ):
            raise AssertionError("bad current-evidence CLI path created output directories or wrote OP-anchor comparison artifacts before failing provenance validation")

        missing_operator_read_gate_payload = json.loads(alt_current_evidence_json.read_text(encoding="utf-8"))
        del missing_operator_read_gate_payload["operator_read_gate"]
        missing_operator_read_gate_json.write_text(
            json.dumps(missing_operator_read_gate_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_operator_read_gate_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(missing_operator_read_gate_json),
                "--md-output",
                str(missing_operator_read_gate_should_not_write_md),
                "--json-output",
                str(missing_operator_read_gate_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_operator_read_gate_result.returncode == 0:
            raise AssertionError("op_anchor_method_comparison.py unexpectedly accepted current-evidence JSON missing operator_read_gate")
        missing_operator_read_gate_text = (
            f"{missing_operator_read_gate_result.stdout}\n{missing_operator_read_gate_result.stderr}"
        )
        if "is missing operator_read_gate" not in missing_operator_read_gate_text:
            raise AssertionError("current-evidence operator_read_gate failure no longer names the missing bridge block")
        if (
            missing_operator_read_gate_output_dir.exists()
            or missing_operator_read_gate_should_not_write_md.exists()
            or missing_operator_read_gate_should_not_write_json.exists()
        ):
            raise AssertionError("missing operator_read_gate CLI path created output directories or wrote OP-anchor comparison artifacts before failing source validation")

        missing_rebuild_contract_payload = json.loads(alt_current_evidence_json.read_text(encoding="utf-8"))
        missing_rebuild_contract_payload.pop("rebuild_validation_contract", None)
        missing_rebuild_contract_json.write_text(
            json.dumps(missing_rebuild_contract_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_rebuild_contract_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(missing_rebuild_contract_json),
                "--md-output",
                str(missing_rebuild_contract_should_not_write_md),
                "--json-output",
                str(missing_rebuild_contract_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_rebuild_contract_result.returncode == 0:
            raise AssertionError("op_anchor_method_comparison.py unexpectedly accepted current-evidence JSON missing rebuild_validation_contract")
        missing_rebuild_contract_text = (
            f"{missing_rebuild_contract_result.stdout}\n{missing_rebuild_contract_result.stderr}"
        )
        if "is missing rebuild_validation_contract" not in missing_rebuild_contract_text:
            raise AssertionError("current-evidence rebuild_validation_contract failure no longer names the missing bridge contract")
        if (
            missing_rebuild_contract_output_dir.exists()
            or missing_rebuild_contract_should_not_write_md.exists()
            or missing_rebuild_contract_should_not_write_json.exists()
        ):
            raise AssertionError("missing rebuild_validation_contract CLI path created output directories or wrote OP-anchor comparison artifacts before failing source validation")

        weakened_rebuild_contract_payload = json.loads(alt_current_evidence_json.read_text(encoding="utf-8"))
        weakened_rebuild_contract_payload["rebuild_validation_contract"][
            "upstream_refresh_order_is_provenance_metadata_only"
        ] = False
        weakened_rebuild_contract_json.write_text(
            json.dumps(weakened_rebuild_contract_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        weakened_rebuild_contract_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(weakened_rebuild_contract_json),
                "--md-output",
                str(weakened_rebuild_contract_should_not_write_md),
                "--json-output",
                str(weakened_rebuild_contract_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if weakened_rebuild_contract_result.returncode == 0:
            raise AssertionError("op_anchor_method_comparison.py unexpectedly accepted current-evidence JSON with a weakened rebuild_validation_contract")
        weakened_rebuild_contract_text = (
            f"{weakened_rebuild_contract_result.stdout}\n{weakened_rebuild_contract_result.stderr}"
        )
        if (
            "rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true"
            not in weakened_rebuild_contract_text
        ):
            raise AssertionError("current-evidence weakened rebuild_validation_contract failure no longer names the provenance-only flag")
        if (
            weakened_rebuild_contract_output_dir.exists()
            or weakened_rebuild_contract_should_not_write_md.exists()
            or weakened_rebuild_contract_should_not_write_json.exists()
        ):
            raise AssertionError("weakened rebuild_validation_contract CLI path created output directories or wrote OP-anchor comparison artifacts before failing source validation")

        missing_source_freshness_payload = json.loads(alt_current_evidence_json.read_text(encoding="utf-8"))
        del missing_source_freshness_payload["source_freshness"]
        missing_source_freshness_json.write_text(
            json.dumps(missing_source_freshness_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_source_freshness_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(missing_source_freshness_json),
                "--md-output",
                str(missing_source_freshness_should_not_write_md),
                "--json-output",
                str(missing_source_freshness_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_source_freshness_result.returncode == 0:
            raise AssertionError("op_anchor_method_comparison.py unexpectedly accepted current-evidence JSON missing source_freshness")
        missing_source_freshness_text = f"{missing_source_freshness_result.stdout}\n{missing_source_freshness_result.stderr}"
        if "missing source_freshness" not in missing_source_freshness_text:
            raise AssertionError("current-evidence source_freshness failure no longer names the missing bridge block")
        if (
            missing_source_freshness_output_dir.exists()
            or missing_source_freshness_should_not_write_md.exists()
            or missing_source_freshness_should_not_write_json.exists()
        ):
            raise AssertionError("missing source_freshness CLI path created output directories or wrote OP-anchor comparison artifacts before failing source validation")

        missing_source_freshness_reference_payload = json.loads(
            alt_current_evidence_json.read_text(encoding="utf-8")
        )
        del missing_source_freshness_reference_payload["source_freshness"]["generated_reference_timezone"]
        missing_source_freshness_reference_json.write_text(
            json.dumps(missing_source_freshness_reference_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_source_freshness_reference_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(missing_source_freshness_reference_json),
                "--md-output",
                str(missing_source_freshness_reference_should_not_write_md),
                "--json-output",
                str(missing_source_freshness_reference_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_source_freshness_reference_result.returncode == 0:
            raise AssertionError("op_anchor_method_comparison.py unexpectedly accepted current-evidence JSON missing source_freshness generated_reference_timezone")
        missing_source_freshness_reference_text = (
            f"{missing_source_freshness_reference_result.stdout}\n"
            f"{missing_source_freshness_reference_result.stderr}"
        )
        if "source_freshness missing fields: generated_reference_timezone" not in missing_source_freshness_reference_text:
            raise AssertionError("current-evidence source_freshness reference failure no longer names the missing bridge reference field")
        if (
            missing_source_freshness_reference_output_dir.exists()
            or missing_source_freshness_reference_should_not_write_md.exists()
            or missing_source_freshness_reference_should_not_write_json.exists()
        ):
            raise AssertionError("missing source_freshness reference CLI path created output directories or wrote OP-anchor comparison artifacts before failing source validation")

        missing_refresh_action_boundary_payload = json.loads(
            alt_current_evidence_json.read_text(encoding="utf-8")
        )
        del missing_refresh_action_boundary_payload["source_freshness"]["refresh_action_boundary"]
        missing_refresh_action_boundary_json.write_text(
            json.dumps(missing_refresh_action_boundary_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_refresh_action_boundary_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(missing_refresh_action_boundary_json),
                "--md-output",
                str(missing_refresh_action_boundary_should_not_write_md),
                "--json-output",
                str(missing_refresh_action_boundary_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_refresh_action_boundary_result.returncode == 0:
            raise AssertionError("op_anchor_method_comparison.py unexpectedly accepted current-evidence JSON missing source_freshness.refresh_action_boundary")
        missing_refresh_action_boundary_text = (
            f"{missing_refresh_action_boundary_result.stdout}\n"
            f"{missing_refresh_action_boundary_result.stderr}"
        )
        if "missing source_freshness.refresh_action_boundary" not in missing_refresh_action_boundary_text:
            raise AssertionError("current-evidence refresh-action boundary failure no longer names the missing bridge sub-block")
        if (
            missing_refresh_action_boundary_output_dir.exists()
            or missing_refresh_action_boundary_should_not_write_md.exists()
            or missing_refresh_action_boundary_should_not_write_json.exists()
        ):
            raise AssertionError("missing refresh_action_boundary CLI path created output directories or wrote OP-anchor comparison artifacts before failing source validation")

        missing_refresh_action_boundary_field_payload = json.loads(
            alt_current_evidence_json.read_text(encoding="utf-8")
        )
        del missing_refresh_action_boundary_field_payload["source_freshness"]["refresh_action_boundary"][
            "not_real_money_evidence"
        ]
        missing_refresh_action_boundary_field_json.write_text(
            json.dumps(missing_refresh_action_boundary_field_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_refresh_action_boundary_field_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(missing_refresh_action_boundary_field_json),
                "--md-output",
                str(missing_refresh_action_boundary_field_should_not_write_md),
                "--json-output",
                str(missing_refresh_action_boundary_field_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_refresh_action_boundary_field_result.returncode == 0:
            raise AssertionError("op_anchor_method_comparison.py unexpectedly accepted current-evidence JSON missing source_freshness.refresh_action_boundary.not_real_money_evidence")
        missing_refresh_action_boundary_field_text = (
            f"{missing_refresh_action_boundary_field_result.stdout}\n"
            f"{missing_refresh_action_boundary_field_result.stderr}"
        )
        if (
            "source_freshness.refresh_action_boundary missing fields: not_real_money_evidence"
            not in missing_refresh_action_boundary_field_text
        ):
            raise AssertionError("current-evidence refresh-action field failure no longer names the missing not-real-money flag")
        if (
            missing_refresh_action_boundary_field_output_dir.exists()
            or missing_refresh_action_boundary_field_should_not_write_md.exists()
            or missing_refresh_action_boundary_field_should_not_write_json.exists()
        ):
            raise AssertionError("missing refresh_action_boundary field CLI path created output directories or wrote OP-anchor comparison artifacts before failing source validation")

        false_refresh_action_boundary_flag_payload = json.loads(
            alt_current_evidence_json.read_text(encoding="utf-8")
        )
        false_refresh_action_boundary_flag_payload["source_freshness"]["refresh_action_boundary"][
            "not_real_money_evidence"
        ] = False
        false_refresh_action_boundary_flag_json.write_text(
            json.dumps(false_refresh_action_boundary_flag_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        false_refresh_action_boundary_flag_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(false_refresh_action_boundary_flag_json),
                "--md-output",
                str(false_refresh_action_boundary_flag_should_not_write_md),
                "--json-output",
                str(false_refresh_action_boundary_flag_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if false_refresh_action_boundary_flag_result.returncode == 0:
            raise AssertionError("op_anchor_method_comparison.py unexpectedly accepted current-evidence JSON with source_freshness.refresh_action_boundary.not_real_money_evidence=false")
        false_refresh_action_boundary_flag_text = (
            f"{false_refresh_action_boundary_flag_result.stdout}\n"
            f"{false_refresh_action_boundary_flag_result.stderr}"
        )
        if (
            "source_freshness.refresh_action_boundary must mark not_real_money_evidence=true"
            not in false_refresh_action_boundary_flag_text
        ):
            raise AssertionError("current-evidence refresh-action false-flag failure no longer names the weakened not-real-money flag")
        if (
            false_refresh_action_boundary_flag_output_dir.exists()
            or false_refresh_action_boundary_flag_should_not_write_md.exists()
            or false_refresh_action_boundary_flag_should_not_write_json.exists()
        ):
            raise AssertionError("false refresh_action_boundary flag CLI path created output directories or wrote OP-anchor comparison artifacts before failing source validation")

        false_refresh_accounting_flag_payload = json.loads(
            alt_current_evidence_json.read_text(encoding="utf-8")
        )
        false_refresh_accounting_flag_payload["source_freshness"]["refresh_action_boundary"][
            "clean_empty_refresh_counts_as_forward_performance"
        ] = True
        false_refresh_accounting_flag_json.write_text(
            json.dumps(false_refresh_accounting_flag_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        false_refresh_accounting_flag_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(false_refresh_accounting_flag_json),
                "--md-output",
                str(false_refresh_accounting_flag_should_not_write_md),
                "--json-output",
                str(false_refresh_accounting_flag_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if false_refresh_accounting_flag_result.returncode == 0:
            raise AssertionError("op_anchor_method_comparison.py unexpectedly accepted current-evidence JSON with source_freshness.refresh_action_boundary.clean_empty_refresh_counts_as_forward_performance=true")
        false_refresh_accounting_flag_text = (
            f"{false_refresh_accounting_flag_result.stdout}\n"
            f"{false_refresh_accounting_flag_result.stderr}"
        )
        if (
            "source_freshness.refresh_action_boundary must mark clean_empty_refresh_counts_as_forward_performance=false"
            not in false_refresh_accounting_flag_text
        ):
            raise AssertionError("current-evidence refresh-action accounting failure no longer names the weakened clean-empty refresh flag")
        if (
            false_refresh_accounting_flag_output_dir.exists()
            or false_refresh_accounting_flag_should_not_write_md.exists()
            or false_refresh_accounting_flag_should_not_write_json.exists()
        ):
            raise AssertionError("false refresh-accounting flag CLI path created output directories or wrote OP-anchor comparison artifacts before failing source validation")

    checks.append(
        require(
            True,
            "cli_json_matches_rebuild",
            "op_anchor_method_comparison.py CLI still writes JSON that matches a fresh build_payload() rebuild",
        )
    )
    checks.append(
        require(
            True,
            "cli_markdown_matches_rebuild",
            "op_anchor_method_comparison.py CLI still writes markdown that matches a fresh build_markdown() rebuild",
        )
    )
    checks.append(
        require(
            True,
            "cli_stdout_matches_generated_report",
            "op_anchor_method_comparison.py CLI stdout still matches the generated markdown plus its Saved: lines",
        )
    )
    checks.append(
        require(
            True,
            "cli_custom_source_inputs_and_output_paths",
            "op_anchor_method_comparison.py can now rerender from explicit scorecard / compare-main / method-family / cross-family / AB / current-evidence source paths and write custom markdown/JSON outputs without depending on the default upstream artifact names",
        )
    )
    checks.append(
        require(
            True,
            "cli_scratch_root_project_local",
            "op_anchor_method_comparison.py CLI fixture now writes temporary rebuild, custom-source, source-drift, and negative-test files under the project-local status-validation scratch root, and that scratch root is cleared before each fixture run",
        )
    )
    checks.append(
        require(
            scratch_meta["tmp_parent_is_project_local"] is True
            and scratch_meta["tmp_parent_cleared_before_fixture_run"] is True
            and Path(scratch_meta["tmp_parent"]) == TMP_PARENT
            and tmp_parent.exists(),
            "cli_scratch_metadata_published",
            "OP-anchor validation now publishes top-level project-local scratch metadata so parent rollups can verify the cleared fixture root without parsing prose or nested artifact fields",
        )
    )
    checks.append(
        require(
            True,
            "source_byte_drift_updates_provenance_only",
            "a row-identical scorecard byte drift updates the OP-anchor source fingerprint and custom-source stdout while leaving the comparison rows, guardrails, and decision gates unchanged",
        )
    )
    checks.append(
        require(
            True,
            "missing_scorecard_row_fails_fast",
            "the real OP-anchor CLI now fails fast if a required scorecard rule row disappears instead of quietly degrading the anchor/challenger comparison",
        )
    )
    checks.append(
        require(
            True,
            "bad_forward_trust_ranking_contract_fails_fast",
            "the real OP-anchor CLI now fails fast if the scorecard JSON stops marking forward_trust as secondary within tier, so a hotter raw OP_REFINED_K7 score cannot quietly become a deployment-order signal",
        )
    )
    checks.append(
        require(
            True,
            "missing_scorecard_gate_minimum_fails_fast",
            "the real OP-anchor CLI now fails fast without creating output directories or writing artifacts if the scorecard JSON loses the phase8_promotion_review decision_gate_minimums threshold instead of quietly publishing local 20/30/100 gate wording",
        )
    )
    checks.append(
        require(
            True,
            "missing_primary_shadow_fails_fast",
            "the real OP-anchor CLI now fails fast if the cross-family PRIMARY_SHADOW row disappears instead of quietly publishing an incomplete live shadow order",
        )
    )
    checks.append(
        require(
            True,
            "missing_ab_delta_path_fails_fast",
            "the real OP-anchor CLI now fails fast if the downstream A/B JSON loses its required delta path instead of quietly weakening the XGBoost caution block",
        )
    )
    checks.append(
        require(
            True,
            "bad_current_evidence_generated_at_fails_fast",
            "the real OP-anchor CLI now fails fast without creating output directories or writing artifacts if current_evidence_summary.json generated_at is timezone-naive before republishing the current-paper snapshot",
        )
    )
    checks.append(
        require(
            True,
            "missing_current_evidence_operator_read_gate_fails_fast",
            "the real OP-anchor CLI now fails fast without creating output directories or writing artifacts if current_evidence_summary.json loses operator_read_gate before republishing the stale-card/API-failure read gate in the current-paper snapshot",
        )
    )
    checks.append(
        require(
            True,
            "missing_current_evidence_rebuild_validation_contract_fails_fast",
            "the real OP-anchor CLI now fails fast without creating output directories or writing artifacts if current_evidence_summary.json loses rebuild_validation_contract before republishing the current bridge rebuild-order route",
        )
    )
    checks.append(
        require(
            True,
            "weakened_current_evidence_rebuild_validation_contract_fails_fast",
            "the real OP-anchor CLI now fails fast without creating output directories or writing artifacts if current_evidence_summary.json keeps rebuild_validation_contract but weakens the provenance-only upstream-refresh flag before republishing the current bridge rebuild-order route",
        )
    )
    checks.append(
        require(
            True,
            "missing_current_evidence_source_freshness_fails_fast",
            "the real OP-anchor CLI now fails fast without creating output directories or writing artifacts if current_evidence_summary.json loses source_freshness before republishing the current-paper snapshot",
        )
    )
    checks.append(
        require(
            True,
            "missing_current_evidence_source_freshness_reference_fails_fast",
            "the real OP-anchor CLI now fails fast without creating output directories or writing artifacts if current_evidence_summary.json loses a source_freshness bridge-reference field before republishing the current-paper snapshot",
        )
    )
    checks.append(
        require(
            True,
            "missing_current_evidence_refresh_action_boundary_fails_fast",
            "the real OP-anchor CLI now fails fast without creating output directories or writing artifacts if current_evidence_summary.json loses source_freshness.refresh_action_boundary before republishing the wrapper-refresh action boundary",
        )
    )
    checks.append(
        require(
            True,
            "missing_current_evidence_refresh_action_boundary_field_fails_fast",
            "the real OP-anchor CLI now fails fast without creating output directories or writing artifacts if current_evidence_summary.json loses source_freshness.refresh_action_boundary.not_real_money_evidence before republishing the wrapper-refresh action boundary",
        )
    )
    checks.append(
        require(
            True,
            "false_current_evidence_refresh_action_boundary_flag_fails_fast",
            "the real OP-anchor CLI now fails fast without creating output directories or writing artifacts if current_evidence_summary.json marks source_freshness.refresh_action_boundary.not_real_money_evidence=false before republishing the wrapper-refresh action boundary",
        )
    )
    checks.append(
        require(
            True,
            "false_current_evidence_clean_empty_refresh_accounting_fails_fast",
            "the real OP-anchor CLI now fails fast without creating output directories or writing artifacts if current_evidence_summary.json marks source_freshness.refresh_action_boundary.clean_empty_refresh_counts_as_forward_performance=true before republishing weakened wrapper-refresh accounting",
        )
    )
    checks.append(
        require(
            source_provenance["source_scope"] == oamc.SOURCE_SCOPE
            and source_provenance["evidence_boundary"] == oamc.EVIDENCE_BOUNDARY
            and set(source_fingerprints) == set(oamc.SOURCE_LABELS)
            and all(source_fingerprints[label]["path"] == path.name for label, path in oamc.SOURCE_LABELS.items())
            and all(isinstance(source_fingerprints[label]["bytes"], int) and source_fingerprints[label]["bytes"] > 0 for label in oamc.SOURCE_LABELS)
            and all(isinstance(source_fingerprints[label]["sha256"], str) and len(source_fingerprints[label]["sha256"]) == 64 for label in oamc.SOURCE_LABELS),
            "source_provenance_json_present",
            "JSON now carries exact input-byte fingerprints plus a source scope and evidence boundary for the OP-anchor comparison",
        )
    )
    parsed_source_rows = parse_source_provenance_table(markdown)
    checks.append(
        require(
            parsed_source_rows == source_fingerprints == oamc.source_file_fingerprints(),
            "source_provenance_markdown_matches_json",
            "OP_ANCHOR_METHOD_COMPARISON.md Source Provenance table now matches op_anchor_method_comparison.json source_fingerprints exactly for every path, byte count, and SHA-256 fingerprint",
        )
    )
    checks.append(
        require(
            scorecard_ranking_contract == oamc.build_payload()["scorecard_ranking_contract"]
            and scorecard_ranking_contract.get("rank_is_tier_first_decision_order") is True
            and scorecard_ranking_contract.get("forward_trust_is_secondary_within_tier") is True
            and scorecard_ranking_contract.get("raw_score_is_not_an_automatic_deployment_instruction") is True
            and "CD_CORE_K8 ranks ahead of OP_REFINED_K7" in scorecard_ranking_contract.get("known_rank_override", "")
            and payload.get("scorecard_ranking_standard") == "rules ranked by tier-first conservative decision order, then forward_trust within tier; not an automatic deployment instruction"
            and "Scorecard ranking contract inherited:" in markdown
            and "raw score is not an automatic deployment instruction" in markdown
            and "Scorecard rank-contract read:" in markdown
            and "hotter raw OP_REFINED_K7 score still does not automatically displace" in markdown
            and "forward_evidence_scorecard_json" in source_fingerprints,
            "scorecard_ranking_contract_inherited",
            "OP-anchor comparison now consumes the forward-evidence scorecard JSON ranking_contract so the OP-vs-Harville/XGBoost page inherits the tier-first ranking semantics and cannot treat OP_REFINED_K7's hotter raw score as an automatic promotion above the OP anchor or paper-basket companion",
        )
    )

    checks.append(
        require(
            current.get("selective_family_context") == "Phase 7 OP/CD rule-component basket"
            and anchor_context.get("phase7_label") == "Phase 7 OP/CD rule-component basket"
            and "Phase 7 OP/CD rule-component basket" in markdown
            and "paper hierarchy is more specific" in markdown
            and "paper-candidate lane" in current["summary"]
            and "paper-candidate rules" in rows["op_durable_k7_anchor"]["why"]
            and "Phase 7 live portfolio" not in markdown
            and "Phase 7 live portfolio" not in saved_json_text
            and "live-candidate lane" not in saved_json_text
            and "live-candidate rules" not in saved_json_text
            and "live hierarchy is more specific" not in markdown,
            "stale_live_portfolio_label_removed",
            "OP-anchor comparison now inherits the Phase 7 OP/CD rule-component basket label from compare-main and avoids stale live-portfolio / live-candidate / live-hierarchy shortcuts",
        )
    )

    checks.append(
        require(
            evidence_boundary == oamc.MACHINE_READABLE_EVIDENCE_BOUNDARY
            and evidence_boundary.get("artifact_role") == "OP-anchor method comparison artifact"
            and evidence_boundary.get("valid_evidence_scope") == oamc.VALID_EVIDENCE_SCOPE
            and evidence_boundary.get("not_new_forward_evidence") is True
            and evidence_boundary.get("not_live_paper_trade_ledger") is True
            and evidence_boundary.get("not_current_day_scanner_result") is True
            and evidence_boundary.get("not_settled_roi_evidence") is True
            and evidence_boundary.get("not_live_profitability_evidence") is True
            and evidence_boundary.get("not_real_money_evidence") is True
            and evidence_boundary.get("not_promotion_readiness_evidence") is True
            and evidence_boundary.get("current_operator_routing_source")
            == "CURRENT_EVIDENCE_SUMMARY.md / current_evidence_summary.json"
            and "operator_read_gate" in evidence_boundary.get("current_operator_routing_fields", [])
            and "operator_status_context" in evidence_boundary.get("current_operator_routing_fields", [])
            and "source_freshness" in evidence_boundary.get("current_operator_routing_fields", [])
            and "source_consistency" in evidence_boundary.get("current_operator_routing_fields", [])
            and "decision_gate_progress" in evidence_boundary.get("current_operator_routing_fields", [])
            and evidence_boundary.get("current_operator_routing_requires_combined_route") is True
            and evidence_boundary.get("current_operator_routing_is_source_readiness_not_performance") is True
            and evidence_boundary.get("source_fingerprints_are_reproducibility_metadata_only") is True
            and evidence_boundary.get("decision_gates_are_forward_observation_requirements_not_current_evidence") is True
            and evidence_boundary.get("current_operator_boundary_snapshot_is_context_only") is True
            and "ROI-complete settled paper rows" in evidence_boundary.get("stronger_forward_confidence_requires", [])
            and "20+ ROI-complete settled shadow rows before Phase 8 promotion review" in evidence_boundary.get("stronger_forward_confidence_requires", [])
            and "30+ ROI-complete same-candidate paper rows before anchor-displacement review" in evidence_boundary.get("stronger_forward_confidence_requires", [])
            and "do not promote OP_REFINED_K7 from this artifact" in evidence_boundary.get("non_goals", [])
            and "do not reopen current odds-only XGBoost from this artifact" in evidence_boundary.get("non_goals", [])
            and "do not substitute BAQ for BEL" in evidence_boundary.get("non_goals", [])
            and "do not quote current PAPER_TRADE_NOW instructions from this artifact; use the combined operator_status_context/source_freshness/operator_read_gate route from CURRENT_EVIDENCE_SUMMARY instead" in evidence_boundary.get("non_goals", [])
            and "do not treat the copied current-evidence operator snapshot as settled ROI or bet readiness" in evidence_boundary.get("non_goals", []),
            "op_anchor_method_comparison_json_publishes_machine_readable_evidence_boundary",
            "OP-anchor comparison JSON now publishes a machine-readable evidence_boundary block that keeps split-aware OP-anchor comparison, Harville benchmarking, current odds-only XGBoost parking, current-paper status snapshots, source fingerprints, and decision gates separate from new forward evidence, live paper ledgers, scanner output, settled ROI, live profitability, promotion readiness, real-money evidence, OP_REFINED_K7 promotion, odds-only XGBoost reopening, Harville live treatment, current PAPER_TRADE_NOW quotation without the combined operator_status_context/source_freshness/operator_read_gate route, and BAQ/BEL substitution",
        )
    )
    checks.append(
        require(
            evidence_boundary_text == oamc.EVIDENCE_BOUNDARY_TEXT
            and "Machine-readable boundary text:" in markdown
            and f"- `valid_evidence_scope={oamc.VALID_EVIDENCE_SCOPE}`" in markdown
            and oamc.EVIDENCE_BOUNDARY_TEXT in markdown
            and "it is not new forward evidence" in evidence_boundary_text
            and "live paper-trade ledger" in evidence_boundary_text
            and "settled ROI" in evidence_boundary_text
            and "live profitability" in evidence_boundary_text
            and "real-money evidence" in evidence_boundary_text
            and "decision gates are forward-observation requirements" in evidence_boundary_text
            and "combined CURRENT_EVIDENCE_SUMMARY operator_status_context/source_freshness/operator_read_gate route" in evidence_boundary_text,
            "op_anchor_method_comparison_json_publishes_evidence_boundary_text",
            "OP-anchor comparison JSON now carries a legacy-readable evidence_boundary_text that matches the markdown Evidence Boundary section and keeps source fingerprints plus decision gates from being mistaken for new forward evidence, live paper ledger data, settled ROI, live profitability, promotion readiness, or real-money evidence",
        )
    )
    checks.append(
        require(
            current_operator_boundary == expected_current_operator_boundary
            and current_operator_boundary.get("source_path") == oamc.CURRENT_EVIDENCE_JSON.name
            and current_operator_boundary.get("operator_status_context_read")
            == expected_current_operator_boundary.get("operator_status_context_read")
            == source_operator_status_context.get("read")
            and current_operator_boundary.get("operator_status_context_valid_use")
            == source_operator_status_context.get("valid_use")
            and current_operator_boundary.get("operator_status_context_best_action_command")
            == source_operator_status_context.get("best_action_command")
            and current_operator_boundary.get("operator_status_context_ops_day_bucket")
            == source_operator_status_context.get("ops_day_bucket")
            and current_operator_boundary.get("operator_status_context_not_forward_performance_evidence") is True
            and current_operator_boundary.get("combined_operator_route_read")
            == expected_current_operator_boundary.get("combined_operator_route_read")
            and (
                "combined route: use operator_status_context plus source_freshness.requires_refresh_before_right_now_use="
                in str(current_operator_boundary.get("combined_operator_route_read") or "")
            )
            and "before quoting current PAPER_TRADE_NOW instructions"
            in str(current_operator_boundary.get("combined_operator_route_read") or "")
            and current_operator_boundary.get("operator_read_gate")
            == expected_current_operator_boundary.get("operator_read_gate")
            == source_operator_read_gate
            and operator_read_gate_branch_ok
            and current_operator_boundary.get("operator_read_gate", {}).get("gate_status")
            == source_operator_gate_status
            and current_operator_boundary.get("operator_read_gate", {}).get("recommended_command")
            == source_operator_read_gate.get("recommended_command")
            and current_operator_boundary.get("operator_read_gate", {}).get("requires_refresh_before_evidence_read")
            is source_operator_read_gate.get("requires_refresh_before_evidence_read")
            and current_operator_boundary.get("operator_read_gate", {}).get("requires_source_freshness_refresh")
            is source_operator_read_gate.get("requires_source_freshness_refresh")
            and current_operator_boundary.get("operator_read_gate", {}).get("has_api_access_failure_context")
            is source_operator_read_gate.get("has_api_access_failure_context")
            and current_operator_boundary.get("operator_read_gate", {}).get("has_scanner_failure_boundary")
            is source_operator_read_gate.get("has_scanner_failure_boundary")
            and current_operator_boundary.get("operator_read_gate", {}).get("has_stale_cache_fallback_context")
            is source_operator_read_gate.get("has_stale_cache_fallback_context")
            and current_operator_boundary.get("operator_read_gate", {}).get("has_wrapper_refresh_action")
            is source_operator_read_gate.get("has_wrapper_refresh_action")
            and current_operator_boundary.get("operator_read_gate", {}).get("has_issue_bucket")
            is source_operator_read_gate.get("has_issue_bucket")
            and current_operator_boundary.get("operator_read_gate", {}).get("current_top_card_counts_as_no_target_evidence")
            is False
            and current_operator_boundary.get("operator_read_gate", {}).get("current_top_card_counts_as_clean_empty_evidence")
            is False
            and current_operator_boundary.get("operator_read_gate", {}).get("current_top_card_counts_as_bet_readiness_evidence")
            is False
            and current_operator_boundary.get("operator_read_gate", {}).get("current_top_card_counts_as_settled_roi_evidence")
            is False
            and current_operator_boundary.get("operator_read_gate", {}).get("not_forward_performance_evidence") is True
            and current_operator_boundary.get("operator_read_gate", {}).get("not_promotion_readiness_evidence") is True
            and current_operator_boundary.get("operator_read_gate", {}).get("not_live_profitability_evidence") is True
            and current_operator_boundary.get("operator_read_gate", {}).get("not_real_money_evidence") is True
            and str(current_operator_boundary.get("operator_read_gate", {}).get("read") or "")
            == source_operator_gate_read
            and current_operator_boundary.get("right_now_freshness_state")
            == expected_current_operator_boundary.get("right_now_freshness_state")
            and current_operator_boundary.get("requires_refresh_before_right_now_use")
            == expected_current_operator_boundary.get("requires_refresh_before_right_now_use")
            and current_operator_boundary.get("refresh_action_command") == "./run_daily_portfolio_observation.sh"
            and current_operator_boundary.get("refresh_source_action_counts_as_current_instruction_before_refresh")
            == expected_current_operator_boundary.get("refresh_source_action_counts_as_current_instruction_before_refresh")
            and current_operator_boundary.get("refresh_can_update_operator_surfaces") is True
            and current_operator_boundary.get("refresh_can_settle_open_rows_by_itself") is False
            and current_operator_boundary.get("refresh_counts_as_roi_complete_evidence_by_itself") is False
            and current_operator_boundary.get("clean_empty_refresh_counts_as_forward_performance") is False
            and current_operator_boundary.get("refresh_boundary_not_forward_performance_evidence") is True
            and current_operator_boundary.get("refresh_boundary_not_promotion_readiness_evidence") is True
            and current_operator_boundary.get("refresh_boundary_not_live_profitability_evidence") is True
            and current_operator_boundary.get("refresh_boundary_not_real_money_evidence") is True
            and current_operator_boundary.get("roi_complete_primary_rows")
            == expected_current_operator_boundary.get("roi_complete_primary_rows")
            and current_operator_boundary.get("first_read_threshold")
            == expected_current_operator_boundary.get("first_read_threshold")
            and current_operator_boundary.get("first_read_remaining")
            == expected_current_operator_boundary.get("first_read_remaining")
            and current_operator_boundary.get("op_anchor_roi_complete_rows")
            == expected_current_operator_boundary.get("op_anchor_roi_complete_rows")
            and current_operator_boundary.get("cd_companion_roi_complete_rows")
            == expected_current_operator_boundary.get("cd_companion_roi_complete_rows")
            and current_operator_boundary.get("current_settled_context_is_cd_only")
            == expected_current_operator_boundary.get("current_settled_context_is_cd_only")
            and current_operator_boundary.get("companion_rows_count_as_anchor_evidence")
            == expected_current_operator_boundary.get("companion_rows_count_as_anchor_evidence")
            and current_operator_boundary.get("anchor_rows_needed_for_same_candidate_review")
            == expected_current_operator_boundary.get("anchor_rows_needed_for_same_candidate_review")
            and current_operator_boundary.get("open_settlement_rows")
            == expected_current_operator_boundary.get("open_settlement_rows")
            and current_operator_boundary.get("open_settlement_queue_state")
            == ("closed" if current_operator_boundary.get("open_settlement_rows") == 0 else "open")
            and current_operator_boundary.get("open_settlement_queue_state")
            == expected_current_operator_boundary.get("open_settlement_queue_state")
            and current_operator_boundary.get("open_settlement_queue_state")
            == source_open_queue.get("open_settlement_queue_state")
            and current_operator_boundary.get("open_settlement_context")
            == expected_current_operator_boundary.get("open_settlement_context")
            and current_operator_boundary.get("open_settlement_context")
            == source_open_queue.get("open_settlement_context")
            and (
                current_operator_boundary.get("open_settlement_rows") != 0
                or current_operator_boundary.get("open_settlement_context") == "no open primary settlement rows"
            )
            and current_operator_boundary.get("anchor_open_rows")
            == expected_current_operator_boundary.get("anchor_open_rows")
            and current_operator_boundary.get("companion_open_rows")
            == expected_current_operator_boundary.get("companion_open_rows")
            and current_operator_boundary.get("current_open_queue_is_cd_only")
            == expected_current_operator_boundary.get("current_open_queue_is_cd_only")
            and current_operator_boundary.get("open_rows_count_as_roi_complete")
            == expected_current_operator_boundary.get("open_rows_count_as_roi_complete")
            and current_operator_boundary.get("open_rows_count_as_anchor_evidence")
            == expected_current_operator_boundary.get("open_rows_count_as_anchor_evidence")
            and current_operator_boundary.get("open_settlement_queue_read") == source_open_queue.get("detail_read")
            and "Settlement queue state:" not in str(current_operator_boundary.get("open_settlement_queue_read") or "")
            and "Current settled paper context is CD-only" in str(current_operator_boundary.get("primary_rule_mix_read") or "")
            and (
                f"Need {current_operator_boundary.get('anchor_rows_needed_for_same_candidate_review')} more "
                "OP_DURABLE_K7 ROI-complete row"
            ) in str(current_operator_boundary.get("anchor_settlement_gap_read") or "")
            and "Open rows are settlement workflow only" in str(current_operator_boundary.get("open_settlement_queue_read") or "")
            and "does not settle open rows" in str(current_operator_boundary.get("refresh_action_boundary_read") or "")
            and current_gate_progress == expected_current_gate_progress == source_current_gate_progress
            and current_gate_progress.get("source_path") == "forward_evidence_scorecard.json"
            and current_gate_progress.get("source_json_path") == "decision_gate_minimums"
            and current_gate_progress.get("gate_status") == "all_uncleared"
            and current_gate_progress.get("all_gates_ready") is False
            and current_gate_progress.get("not_forward_performance_evidence") is True
            and current_gate_progress.get("not_promotion_readiness_evidence") is True
            and current_gate_progress.get("not_live_profitability_evidence") is True
            and current_gate_progress.get("not_real_money_evidence") is True
            and current_gate_progress.get("primary_first_read", {}).get("current_rows") == 6
            and current_gate_progress.get("primary_first_read", {}).get("threshold") == 30
            and current_gate_progress.get("op_anchor_same_candidate_review", {}).get("candidate_rule_id")
            == "OP_DURABLE_K7"
            and current_gate_progress.get("op_anchor_same_candidate_review", {}).get("current_rows") == 0
            and current_gate_progress.get("op_anchor_same_candidate_review", {}).get("threshold") == 30
            and current_gate_progress.get("op_anchor_same_candidate_review", {}).get(
                "companion_rows_count_as_anchor_evidence"
            )
            is False
            and current_gate_progress.get("phase8_promotion_review", {}).get("weakest_current_rows") == 0
            and current_gate_progress.get("phase8_promotion_review", {}).get("threshold_per_candidate") == 20
            and current_gate_progress.get("real_money_discussion", {}).get("current_primary_roi_complete_rows") == 6
            and current_gate_progress.get("real_money_discussion", {}).get("threshold") == 100
            and "Gate progress: primary first-read 6/30" in current_gate_progress.get("read", "")
            and "OP anchor same-candidate 0/30" in current_gate_progress.get("read", "")
            and "Phase 8 weakest shadow 0/20" in current_gate_progress.get("read", "")
            and "real-money discussion floor 6/100" in current_gate_progress.get("read", "")
            and "## Current Paper Snapshot" in markdown
            and "This small snapshot is copied from `current_evidence_summary.json`" in markdown
            and (
                f"| Combined operator route | {oamc.md_cell(current_operator_boundary['combined_operator_route_read'])} "
                f"Operator context read = {oamc.md_cell(current_operator_boundary.get('operator_status_context_read'))}; "
                f"ops bucket = `{current_operator_boundary.get('operator_status_context_ops_day_bucket')}` |"
            ) in markdown
            and f"| Source freshness | `{current_operator_boundary['right_now_freshness_state']}`; refresh before right-now use = `{current_operator_boundary['requires_refresh_before_right_now_use']}`; bridge reference = `{current_operator_boundary['source_freshness_generated_reference_date']}` (`{current_operator_boundary['source_freshness_generated_reference_timezone']}`); comparison = `{current_operator_boundary['source_freshness_staleness_comparison_source']}` / `{current_operator_boundary['source_freshness_staleness_comparison_date']}`; read = {oamc.md_cell(current_operator_boundary['source_freshness_read'])} |" in markdown
            and (
                f"| Operator read gate | `{oamc.CURRENT_EVIDENCE_JSON.name}` `operator_read_gate`: "
                f"{oamc.md_cell(current_operator_boundary.get('operator_read_gate', {}).get('read'))} "
                f"Gate status = `{current_operator_boundary.get('operator_read_gate', {}).get('gate_status')}`; "
                f"recommended command = `{current_operator_boundary.get('operator_read_gate', {}).get('recommended_command')}` |"
            )
            in markdown
            and (
                f"| Bridge-published gate progress | `{oamc.CURRENT_EVIDENCE_JSON.name}` `decision_gate_progress`: "
                f"{oamc.md_cell(current_gate_progress.get('read'))} Source: `{current_gate_progress.get('source_path')}` "
                f"`{current_gate_progress.get('source_json_path')}`; gate status = `{current_gate_progress.get('gate_status')}` |"
            )
            in markdown
            and "| Primary first-read gate |" not in markdown
            and (
                "| Current settled rule mix | OP_DURABLE_K7="
                f"{current_operator_boundary.get('op_anchor_roi_complete_rows')}; "
                "CD_CORE_K8="
                f"{current_operator_boundary.get('cd_companion_roi_complete_rows')};"
            ) in markdown
            and "CD-only paper rows are not OP-anchor forward evidence" in markdown
            and (
                f"| OP-anchor settlement gap | "
                f"{oamc.md_cell(current_operator_boundary.get('anchor_settlement_gap_read'))} |"
            ) in markdown
            and (
                f"| Settlement queue state | `{current_operator_boundary.get('open_settlement_queue_state')}`; "
                f"{oamc.md_cell(current_operator_boundary.get('open_settlement_context'))}; detail: "
                f"{oamc.md_cell(current_operator_boundary.get('open_settlement_queue_read'))} |"
            ) in markdown
            and "| Open settlement queue |" not in markdown
            and "Wrapper refresh is operator routing only; it is not settled ROI, promotion readiness, live profitability, or real-money evidence" in markdown,
            "current_operator_boundary_preserves_cd_only_op_gap",
            "OP-anchor comparison carries the current_evidence_summary.json paper-status snapshot with the combined operator_status_context/source_freshness/operator_read_gate route, source freshness, refresh routing, operator_read_gate, the bridge-published all-uncleared decision_gate_progress split, 0 OP_DURABLE_K7 settled rows, the current CD_CORE_K8 settled count, source-published settlement-queue state/context plus by-rule detail, and explicit non-evidence flags so stale/API-failure or current CD-only paper context cannot be mistaken for OP-anchor proof",
        )
    )
    checks.append(
        require(
            scorecard_audit_route == source_scorecard_audit_route
            and scorecard_audit_route.get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route.get("json_path") == "scorecard_ranking_contract_audit.json"
            and scorecard_audit_route.get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route.get("gate_floor_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and scorecard_audit_route.get("valid_use") == "navigation route for scorecard gate/ranking/CI-only/timezone/no-BAQ synchronization checks"
            and scorecard_audit_snapshot.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and scorecard_audit_snapshot.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and scorecard_audit_snapshot.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and scorecard_audit_snapshot.get("real_money_no_baq_as_bel_required") is True
            and scorecard_audit_route.get("artifacts_present") is True
            and scorecard_audit_route.get("not_forward_performance_evidence") is True
            and scorecard_audit_route.get("not_settled_roi_evidence") is True
            and scorecard_audit_route.get("not_promotion_readiness_evidence") is True
            and scorecard_audit_route.get("not_live_profitability_evidence") is True
            and scorecard_audit_route.get("not_bankroll_guidance") is True
            and scorecard_audit_route.get("not_real_money_evidence") is True
            and "30/20/100 gate floors" in str(scorecard_audit_route.get("route_read") or "")
            and "OP_REFINED CI-only support context" in str(scorecard_audit_route.get("route_read") or "")
            and "generated-at timezone provenance" in str(scorecard_audit_route.get("route_read") or "")
            and "no-BAQ-as-BEL prerequisite" in str(scorecard_audit_route.get("route_read") or "")
            and "| Scorecard audit route | `current_evidence_summary.json` `scorecard_audit_route`:" in markdown,
            "current_operator_boundary_publishes_scorecard_audit_route",
            "OP-anchor comparison JSON and markdown now republish current_evidence_summary.json scorecard_audit_route so copied gate/ranking/CI-only/timezone/no-BAQ synchronization questions route to the dedicated audit without becoming forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
        )
    )
    checks.append(
        require(
            rebuild_validation_contract == source_rebuild_validation_contract
            and rebuild_validation_contract.get("prerequisite_rebuild_command")
            == "python3 paper_trade_settlement_audit.py"
            and rebuild_validation_contract.get("rebuild_command") == "python3 current_evidence_summary.py"
            and rebuild_validation_contract.get("direct_validation_command")
            == "python3 validate_current_evidence_summary.py"
            and rebuild_order_commands == oamc.EXPECTED_REBUILD_ORDER_COMMANDS
            and rebuild_validation_contract.get(
                "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
            )
            is True
            and rebuild_validation_contract.get("requires_source_consistency_before_quoting_current_totals")
            is True
            and rebuild_validation_contract.get("requires_source_freshness_before_right_now_instruction_use")
            is True
            and rebuild_validation_contract.get("green_checks_are_reproducibility_metadata_only") is True
            and rebuild_validation_contract.get("upstream_refresh_order_is_provenance_metadata_only") is True
            and rebuild_validation_contract.get("not_settled_roi_or_real_money_evidence") is True
            and "| Current bridge rebuild order | `current_evidence_summary.json` `rebuild_validation_contract`:"
            in markdown
            and "`python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`"
            in markdown
            and "before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes" in markdown
            and "Provenance/rebuild route only" in markdown,
            "current_operator_boundary_publishes_rebuild_validation_contract",
            "OP-anchor comparison JSON and markdown now republish current_evidence_summary.json rebuild_validation_contract so source-byte changes route through settlement audit -> current bridge -> bridge validator before current totals are quoted, while keeping the route as provenance/rebuild metadata rather than settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
        )
    )
    checks.append(
        require(
            oamc.has_timezone_aware_timestamp(current_operator_boundary.get("generated_at"))
            and current_operator_boundary.get("generated_at") == expected_current_operator_boundary.get("generated_at"),
            "current_operator_boundary_generated_at_is_timezone_aware",
            f"copied current-evidence generated_at={current_operator_boundary.get('generated_at')!r} stays parseable timezone-aware provenance metadata only before the OP-anchor comparison republishes current-paper context",
        )
    )
    checks.append(
        require(
            anchor_review_policy == expected_anchor_review_policy
            and anchor_review_policy["phase8_promotion_review_min_roi_complete_settled_rows"] == 20
            and anchor_review_policy["anchor_displacement_review_min_roi_complete_same_candidate_rows"] == 30
            and anchor_review_policy["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and anchor_review_policy["source_path"] == "forward_evidence_scorecard.json"
            and anchor_review_policy["source_json_path"] == "decision_gate_minimums"
            and anchor_review_policy["phase8_promotion_review_scope"] == "candidate shadow observations"
            and anchor_review_policy["anchor_displacement_review_scope"] == "same candidate paper observations"
            and "20 ROI-complete settled shadow rows can only open a Phase 8 promotion review" in anchor_review_policy["policy_read"]
            and "30+ ROI-complete same-candidate paper observations" in anchor_review_policy["policy_read"]
            and "100+ total settled observations with usable ROI" in anchor_review_policy["policy_read"]
            and "historical replay rows" in anchor_review_policy["does_not_count"]
            and "green validators" in anchor_review_policy["does_not_count"]
            and scorecard_decision_gate_minimums == source_scorecard_payload["decision_gate_minimums"]
            and scorecard_decision_gate_minimums["phase8_promotion_review"]["min_roi_complete_settled_observations"] == 20
            and scorecard_decision_gate_minimums["anchor_displacement"]["min_roi_complete_settled_observations"] == 30
            and scorecard_decision_gate_minimums["real_money_discussion"]["min_total_settled_observations_with_usable_roi"] == 100
            and "Anchor-review policy:" in markdown
            and "Anchor-review threshold:" in markdown
            and "Decision-gate source: `forward_evidence_scorecard.json` `decision_gate_minimums` (`phase8_promotion_review=20`, `anchor_displacement=30`, `real_money_discussion=100`)." in markdown
            and "20-row promotion-review gate and 30-row anchor-displacement gate are separate" in decision_gates["same-family OP challenger"]["evidence_scope"]
            and "30+ ROI-complete same-candidate paper observations" in decision_gates["same-family OP challenger"]["evidence_required_before_change"],
            "anchor_review_policy_separates_promotion_from_displacement",
            "OP-anchor comparison now publishes a scorecard-derived machine-readable anchor_review_policy, matching scorecard_decision_gate_minimums, and markdown/gate language that separates the 20-row Phase 8 promotion-review threshold from the stricter 30-row OP anchor-displacement discussion threshold plus the 100-row real-money discussion floor",
        )
    )
    checks.append(
        require(
            payload["guardrail"]["anchor"] == "OP_DURABLE_K7"
            and payload["guardrail"].get("primary_companion") == "CD_CORE_K8"
            and payload["guardrail"]["primary_shadow"] == "CD_CORE_K8"
            and payload["guardrail"]["secondary_shadow"] == "OP_REFINED_K7"
            and payload["guardrail"]["benchmark_only"] == "Harville-ranked probabilities"
            and payload["guardrail"]["research_only"] == "XGBoost residual correction",
            "guardrail_roles",
            "guardrail still keeps OP_DURABLE_K7 as anchor, CD_CORE_K8 as paper-basket companion (with legacy primary_shadow compatibility), OP_REFINED_K7 as same-family shadow challenger, Harville as benchmark-only, and XGBoost as research-only",
        )
    )
    checks.append(
        require(
            rows["op_durable_k7_anchor"]["role"] == "ANCHOR"
            and rows["op_durable_k7_anchor"]["evidence_class"] == "frozen 2024-2025 holdout + walk-forward frequency"
            and abs(rows["op_durable_k7_anchor"]["primary_metric"] - 22.9) < 1e-9
            and rows["op_durable_k7_anchor"]["primary_sample"] == 115
            and abs(rows["op_durable_k7_anchor"]["holdout_2024_metric"] + 47.41) < 1e-9
            and rows["op_durable_k7_anchor"]["holdout_2024_sample"] == 68
            and abs(rows["op_durable_k7_anchor"]["holdout_2025_metric"] - 124.61) < 1e-9
            and rows["op_durable_k7_anchor"]["holdout_2025_sample"] == 47
            and rows["op_durable_k7_anchor"]["secondary_metric"] == "7/10"
            and abs(rows["op_durable_k7_anchor"]["ci_lower"] + 3.4) < 1e-9,
            "op_anchor_numbers",
            "OP_DURABLE_K7 row still matches the frozen scorecard holdout, split-year, walk-forward, and CI-lower-bound anchor read",
        )
    )
    checks.append(
        require(
            rows["harville_ranked_benchmark"]["role"] == "BENCHMARK ONLY"
            and rows["harville_ranked_benchmark"]["evidence_class"] == "large-sample broad-family backtest benchmark"
            and abs(rows["harville_ranked_benchmark"]["primary_metric"] + 24.05) < 1e-9
            and rows["harville_ranked_benchmark"]["primary_sample"] == 90004,
            "harville_stays_negative_benchmark",
            "Harville row still shows a negative large-sample benchmark result",
        )
    )
    checks.append(
        require(
            rows["xgboost_residual_research"]["role"] == "RESEARCH ONLY"
            and rows["xgboost_residual_research"]["evidence_class"] == "negative betting read + downstream EV A/B check"
            and abs(rows["xgboost_residual_research"]["primary_metric"] + 24.16) < 1e-9
            and rows["xgboost_residual_research"]["primary_sample"] == 16724
            and "EV winner passes -7" in rows["xgboost_residual_research"]["secondary_metric"]
            and "-3.93%" in rows["xgboost_residual_research"]["secondary_metric"]
            and "-0.0315pp" in rows["xgboost_residual_research"]["secondary_metric"]
            and "from 178 to 171" in rows["xgboost_residual_research"]["secondary_metric"],
            "xgboost_stays_research_only",
            "XGBoost row still points to the negative betting line and the normalized weaker EV winner pass-through read",
        )
    )
    checks.append(
        require(
            abs(anchor_context["phase7_holdout_roi"] - 38.68) < 1e-9
            and anchor_context["phase7_holdout_races"] == 175
            and abs(anchor_context["phase7_holdout_2024_roi"] - 0.37) < 1e-9
            and anchor_context["phase7_holdout_2024_races"] == 109
            and abs(anchor_context["phase7_holdout_2025_roi"] - 105.38) < 1e-9
            and anchor_context["phase7_holdout_2025_races"] == 66
            and anchor_context["phase7_secondary_basis"] == "frozen replay on walk-forward test years"
            and anchor_context["phase7_secondary_read_note"] == "That broader selective-family secondary line is replay context only, not extra train-only validation."
            and abs(anchor_context["op_refined_holdout_roi"] - 51.43) < 1e-9
            and anchor_context["op_refined_holdout_races"] == 49
            and abs(anchor_context["op_anchor_ci_lower"] + 3.4) < 1e-9
            and challenger_diagnostic["anchor_rule"] == "OP_DURABLE_K7"
            and challenger_diagnostic["challenger_rule"] == "OP_REFINED_K7"
            and challenger_diagnostic["anchor_holdout_races"] == 115
            and challenger_diagnostic["challenger_holdout_races"] == 49
            and abs(challenger_diagnostic["challenger_sample_ratio_pct"] - 42.61) < 1e-9
            and challenger_diagnostic["challenger_sample_deficit_races"] == 66
            and challenger_diagnostic["anchor_wf_selected_count"] == 7
            and challenger_diagnostic["challenger_wf_selected_count"] == 2
            and challenger_diagnostic["wf_selection_deficit_folds"] == 5
            and abs(challenger_diagnostic["anchor_ci_lower"] + 3.4) < 1e-9
            and abs(challenger_diagnostic["challenger_ci_lower"] - 11.2) < 1e-9
            and challenger_diagnostic["challenger_has_higher_aggregate_holdout_roi"] is True
            and challenger_diagnostic["challenger_has_positive_ci_lower"] is True
            and challenger_diagnostic["challenger_losing_holdout_years"] == ["2024"]
            and challenger_diagnostic["ci_only_promotion_allowed"] is False
            and challenger_diagnostic["ci_only_promotion_blockers"]
            == [
                "smaller holdout sample",
                "losing 2024 holdout split",
                "lower walk-forward selection frequency",
                "separate 20-row promotion-review and 30-row anchor-displacement paper-observation gates not cleared",
            ]
            and "not enough by itself to promote OP_REFINED_K7" in challenger_diagnostic["ci_only_promotion_read"]
            and "no ROI-complete paper observations clearing the separate promotion or anchor-review gates" in challenger_diagnostic["ci_only_promotion_read"]
            and challenger_diagnostic["scorecard_ci_only_diagnostic_source"] == "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7"
            and challenger_diagnostic["scorecard_ci_only_promotion_diagnostic"] == source_ci_diagnostic
            and "Scorecard diagnostic source: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` (`ci_only_promotion_allowed=false`)." in markdown
            and "hotter aggregate holdout ROI and positive bootstrap CI lower bound" in challenger_diagnostic["diagnostic_read"]
            and "42.61% of the OP_DURABLE_K7 sample" in challenger_diagnostic["diagnostic_read"]
            and "2/10 walk-forward selections versus 7/10" in challenger_diagnostic["diagnostic_read"]
            and "20-row promotion-review and 30-row anchor-displacement" in challenger_diagnostic["diagnostic_read"],
            "anchor_context_stable",
            "Phase 7 context, explicit replay-only secondary-basis caution, OP anchor CI caution, and the scorecard-sourced OP refined challenger diagnostic still match the current frozen evidence, including the uneven 2024/2025 split, smaller challenger sample, lower walk-forward support, positive-CI nuance, explicit CI-only promotion block, and separate 20/30 paper-observation gates",
        )
    )
    checks.append(
        require(
            current.get("primary_companion") == "CD_CORE_K8"
            and current["primary_shadow"] == "CD_CORE_K8"
            and current["secondary_shadow"] == "OP_REFINED_K7",
            "current_paper_companion_order",
            "JSON current-read block now carries the primary OP/CD paper-basket companion and same-family OP shadow challenger explicitly, while preserving the legacy primary_shadow key",
        )
    )
    checks.append(
        require(
            [row["rule_id"] for row in paper_basket_context_rows]
            == ["OP_DURABLE_K7", "CD_CORE_K8", "OP_REFINED_K7"]
            and paper_basket_context["OP_DURABLE_K7"]["shadow_rank"] == "LIVE_DEFAULT"
            and paper_basket_context["OP_DURABLE_K7"]["lane_read"] == "Safest current OP anchor"
            and paper_basket_context["OP_DURABLE_K7"]["role"] == "ANCHOR"
            and paper_basket_context["OP_DURABLE_K7"]["holdout_races"] == 115
            and paper_basket_context["OP_DURABLE_K7"]["wf_selected_count"] == 7
            and paper_basket_context["OP_DURABLE_K7"]["ci_lower"] == -3.4
            and paper_basket_context["CD_CORE_K8"]["shadow_rank"] == "PRIMARY_SHADOW"
            and paper_basket_context["CD_CORE_K8"]["lane_read"] == "Primary OP/CD paper-basket companion"
            and paper_basket_context["CD_CORE_K8"]["role"] == "PAPER"
            and paper_basket_context["CD_CORE_K8"]["scorecard_tier"] == "PAPER"
            and paper_basket_context["CD_CORE_K8"]["holdout_races"] == 60
            and paper_basket_context["CD_CORE_K8"]["holdout_2024_roi"] == 45.65
            and paper_basket_context["CD_CORE_K8"]["holdout_2025_roi"] == 78.21
            and paper_basket_context["CD_CORE_K8"]["wf_selected_count"] == 1
            and paper_basket_context["CD_CORE_K8"]["ci_lower"] == -15.0
            and "not an anchor replacement" in paper_basket_context["CD_CORE_K8"]["gate_read"]
            and paper_basket_context["OP_REFINED_K7"]["shadow_rank"] == "SECONDARY_SHADOW"
            and paper_basket_context["OP_REFINED_K7"]["lane_read"] == "Closest same-family OP shadow challenger"
            and paper_basket_context["OP_REFINED_K7"]["role"] == "WATCH"
            and paper_basket_context["OP_REFINED_K7"]["holdout_races"] == 49
            and paper_basket_context["OP_REFINED_K7"]["holdout_2024_roi"] == -25.47
            and paper_basket_context["OP_REFINED_K7"]["wf_selected_count"] == 2
            and paper_basket_context["OP_REFINED_K7"]["ci_lower"] == 11.2
            and "20-row promotion-review and 30-row anchor-displacement gates" in paper_basket_context["OP_REFINED_K7"]["gate_read"]
            and current.get("paper_basket_context_read")
            == "structured cross-family context keeps OP_DURABLE_K7, CD_CORE_K8, and OP_REFINED_K7 in separate anchor / companion / shadow lanes before comparing Harville or current odds-only XGBoost"
            and "## Paper Basket / Shadow Context" in markdown
            and "This table keeps the current selective rule lanes visible before the broader method-family comparison. It is sourced from `cross_family_decision_card.csv` and remains posture context only." in markdown
            and "| Rule | Lane | Split-aware evidence | WF | CI lower | Why now | What does not change |" in markdown
            and "| OP_DURABLE_K7 | Safest current OP anchor (ANCHOR, P7) | +22.90% on 115; 2024 -47.41% on 68, 2025 +124.61% on 47 | 7/10 | -3.40%" in markdown
            and "| CD_CORE_K8 | Primary OP/CD paper-basket companion (PAPER, P7) | +55.96% on 60; 2024 +45.65% on 41, 2025 +78.21% on 19 | 1/10 | -15.00%" in markdown
            and "Paper-basket companion is not an anchor replacement. Needs materially more forward sample than 60 holdout races" in markdown
            and "| OP_REFINED_K7 | Closest same-family OP shadow challenger (WATCH, P8) | +51.43% on 49; 2024 -25.47% on 33, 2025 +210.02% on 16 | 2/10 | +11.20%" in markdown
            and "Shadow status stays below the 20-row promotion-review and 30-row anchor-displacement gates." in markdown,
            "paper_basket_context_table_structured",
            "OP-anchor comparison now carries a source-driven paper-basket / shadow context table in JSON and markdown, keeping OP_DURABLE_K7, CD_CORE_K8, and OP_REFINED_K7 in distinct anchor, companion, and shadow lanes before the broader Harville/XGBoost method-family comparison",
        )
    )
    checks.append(
        require(
            "OP_DURABLE_K7 remains the safest current selective anchor" in current["summary"]
            and "paper-candidate lane" in current["summary"]
            and "2024 -47.41% on 68, 2025 +124.61% on 47" in current["summary"]
            and "bootstrap CI lower bound is still -3.40%" in current["summary"]
            and "Harville still loses badly on a huge benchmark sample" in current["summary"]
            and "worse downstream conservative EV pass-through" in current["summary"]
            and "-7 passes, -3.93% relative, -0.0315 percentage points of test winners" in current["summary"]
            and "20 ROI-complete shadow rows can open only a Phase 8 promotion review" in current["summary"]
            and "30+ ROI-complete same-candidate paper observations" in current["summary"],
            "current_read_guardrail",
            "JSON current-read summary still carries the OP anchor guardrail plus the paper-candidate lane wording, mixed 2024/2025 split, CI caution, and normalized downstream loss read",
        )
    )
    checks.append(
        require(
            "## Evidence Boundary" in markdown
            and "This artifact is a split-aware posture/reproducibility audit only" in markdown
            and "decision gates are forward-observation requirements, not current evidence" in markdown
            and "Stronger forward confidence still requires qualifying live paper signals, ROI-complete settled paper rows" in markdown
            and "Anchor-review policy: forward_evidence_scorecard.json decision_gate_minimums says 20 ROI-complete settled shadow rows can only open a Phase 8 promotion review" in markdown
            and "Decision-gate source: `forward_evidence_scorecard.json` `decision_gate_minimums` (`phase8_promotion_review=20`, `anchor_displacement=30`, `real_money_discussion=100`)." in markdown
            and "30+ ROI-complete same-candidate paper observations" in markdown
            and "do not promote OP_REFINED_K7, reopen current odds-only XGBoost, treat Harville as live, substitute BAQ for BEL" in markdown
            and "## Source Provenance" in markdown
            and "Exact input-byte fingerprints for this OP-anchor comparison" in markdown
            and "Use them as reproducibility metadata only" in markdown
            and "they do not prove live paper-trade edge, promotion readiness, live profitability, or real-money performance" in markdown
            and f"- Source scope: {oamc.SOURCE_SCOPE}" in markdown
            and f"- Evidence boundary: {oamc.EVIDENCE_BOUNDARY}." in markdown
            and "| Source | File | Bytes | SHA-256 |" in markdown
            and all(f"| {label} | `{source_fingerprints[label]['path']}` | {source_fingerprints[label]['bytes']} | `{source_fingerprints[label]['sha256']}` |" in markdown for label in oamc.SOURCE_LABELS),
            "markdown_source_provenance_present",
            "markdown now exposes exact source fingerprints while clearly labeling them as reproducibility metadata, not live paper-trade, promotion, profitability, or real-money evidence",
        )
    )
    checks.append(
        require(
            "# OP Anchor vs Harville vs XGBoost" in markdown
            and "`CD_CORE_K8` is the primary OP/CD paper-basket companion" in markdown
            and "Current paper-companion read: `CD_CORE_K8` is the primary OP/CD paper-basket companion and `OP_REFINED_K7` is the stronger same-family OP shadow challenger, so the paper hierarchy is more specific than just `selective beats Harville/XGBoost`." in markdown
            and "Do not reopen the current odds-only XGBoost path unless the evidence class changes materially" in markdown
            and "| Approach | Role | Evidence class | Primary evidence | Sample | Secondary evidence | Why it sits here |" in markdown
            and "frozen 2024-2025 holdout + walk-forward frequency" in markdown
            and "negative betting read + downstream EV A/B check" in markdown
            and "This table keeps the OP anchor split-aware on purpose" in markdown
            and "## Paper Basket / Shadow Context" in markdown
            and "Paper-basket context read: structured cross-family context keeps OP_DURABLE_K7, CD_CORE_K8, and OP_REFINED_K7 in separate anchor / companion / shadow lanes before comparing Harville or current odds-only XGBoost." in markdown
            and "Anchor caution: `OP_DURABLE_K7` is still the safest current anchor, not a statistically clean slam dunk; its bootstrap 95% CI lower bound is still `-3.40%`." in markdown
            and "Why OP_DURABLE_K7 Still Holds the Anchor" in markdown
            and "Anchor caution: the bootstrap 95% CI lower bound for `OP_DURABLE_K7` is still `-3.40%`, so “safest current anchor” is a deployment ranking, not proof of a clean positive lower-bound edge." in markdown
            and "That broader selective-family secondary line is replay context only, not extra train-only validation." in markdown
            and "2024 -47.41% on 68" in markdown
            and "## OP_REFINED_K7 Challenger Diagnostic" in markdown
            and "OP_REFINED_K7 has the hotter aggregate holdout ROI and positive bootstrap CI lower bound" in markdown
            and "`OP_REFINED_K7` has `49` holdout races versus `115` for `OP_DURABLE_K7` (`42.61%` of the anchor sample; `66` fewer races)" in markdown
            and "`OP_REFINED_K7` was selected in `2/10` folds versus `7/10` for `OP_DURABLE_K7` (`5` fewer folds)" in markdown
            and "has a positive CI lower bound (`+11.20%`) while `OP_DURABLE_K7` still crosses zero (`-3.40%`)" in markdown
            and "CI-only promotion check: A positive bootstrap CI lower bound is useful support context, but it is not enough by itself to promote OP_REFINED_K7 or displace OP_DURABLE_K7" in markdown
            and "no ROI-complete paper observations clearing the separate promotion or anchor-review gates" in markdown
            and "Treat `CD_CORE_K8` as the primary OP/CD paper-basket companion and `OP_REFINED_K7` as the smaller same-family shadow challenger" in markdown
            and "## What Would Change This Answer" in markdown
            and "A challenger only dislodges `OP_DURABLE_K7` with cleaner forward evidence" in markdown
            and "Until then, treat it as a dead end and move on." in markdown
            and "## Decision Gates Before Changing the Anchor" in markdown
            and "These gates keep the OP decision tied to new forward observations rather than another prettier replay table." in markdown
            and "| Gate | Current rule | Evidence required before change | Evidence scope |" in markdown
            and "20+ ROI-complete settled shadow observations for OP_REFINED_K7" in markdown
            and "30+ ROI-complete same-candidate paper observations" in markdown
            and "Future settled `phase8_shadow` paper-trade ledger rows with complete ROI coverage; the 20-row promotion-review gate and 30-row anchor-displacement gate are separate" in markdown
            and "do not rerun odds-only tuning as if it were new evidence" in markdown
            and "another odds-only rerun is not a new evidence class" in markdown
            and "Keep BEL dormant and do not substitute BAQ for BEL" in markdown
            and "BAQ needs independent evidence and cannot inherit BEL history" in markdown
            and "100+ paper observations" in markdown
            and "not clean scans, open signals, or replay backtests" in markdown
            and decision_gates["same-family OP challenger"]["current_rule"] == "Keep OP_DURABLE_K7 as anchor; keep OP_REFINED_K7 shadow-only."
            and "20+ ROI-complete settled shadow observations" in decision_gates["same-family OP challenger"]["evidence_required_before_change"]
            and "30+ ROI-complete same-candidate paper observations" in decision_gates["same-family OP challenger"]["evidence_required_before_change"]
            and "20-row promotion-review gate and 30-row anchor-displacement gate are separate" in decision_gates["same-family OP challenger"]["evidence_scope"]
            and "historical replay or holdout rows do not count as new promotion or anchor-displacement evidence" in decision_gates["same-family OP challenger"]["evidence_scope"]
            and "do not rerun odds-only tuning" in decision_gates["current odds-only XGBoost reopening"]["evidence_required_before_change"]
            and "another odds-only rerun is not a new evidence class" in decision_gates["current odds-only XGBoost reopening"]["evidence_scope"]
            and "do not substitute BAQ for BEL" in decision_gates["BEL/BAQ substitution"]["current_rule"]
            and "cannot inherit BEL history" in decision_gates["BEL/BAQ substitution"]["evidence_scope"]
            and "100+ paper observations" in decision_gates["real-money scaling"]["evidence_required_before_change"]
            and "not clean scans, open signals, or replay backtests" in decision_gates["real-money scaling"]["evidence_scope"]
            and "Keep Harville as the structural benchmark and XGBoost as research" in markdown
            and "Park the current odds-only XGBoost path unless a materially different evidence class appears; the current version is a documented dead end" in markdown
            and "## Validation" in markdown
            and "- Sources: `forward_evidence_scorecard.csv`, `forward_evidence_scorecard.json`, `compare_main_approaches.csv`, `method_family_decision_card.csv`, `cross_family_decision_card.csv`, `ab_downstream_comparison_results.json`, `current_evidence_summary.json`" in markdown
            and "- Wrote: `OP_ANCHOR_METHOD_COMPARISON.md`, `op_anchor_method_comparison.json`" in markdown,
            "markdown_sections_present",
            "markdown artifact still includes the split-aware OP-anchor framing, explicit paper-companion / shadow-challenger ordering, current-paper hierarchy wording, current paper snapshot, evidence-class labeling, replay-only selective-family caution, CI caution, dead-end XGBoost parking rule, explicit forward-observation decision gates, anchor rationale, bottom-line guardrail, and validation source/output footer",
        )
    )

    suite_read = (
        f"OP_DURABLE_K7 stays anchor at +{rows['op_durable_k7_anchor']['primary_metric']:.2f}% on "
        f"{rows['op_durable_k7_anchor']['primary_sample']} holdout races (2024={rows['op_durable_k7_anchor']['holdout_2024_metric']:+.2f}% on {rows['op_durable_k7_anchor']['holdout_2024_sample']}, "
        f"2025={rows['op_durable_k7_anchor']['holdout_2025_metric']:+.2f}% on {rows['op_durable_k7_anchor']['holdout_2025_sample']}) with {rows['op_durable_k7_anchor']['secondary_metric']} walk-forward selection and CI low {rows['op_durable_k7_anchor']['ci_lower']:+.2f}%; "
        f"paper companion={current['primary_companion']}, closest shadow={current['secondary_shadow']}; "
        "paper-basket context table now keeps OP_DURABLE_K7, CD_CORE_K8, and OP_REFINED_K7 in separate anchor / companion / shadow lanes before the broader Harville/XGBoost comparison; "
        f"Harville stays benchmark-only at {rows['harville_ranked_benchmark']['primary_metric']:+.2f}% on {rows['harville_ranked_benchmark']['primary_sample']} races; "
        f"XGBoost stays research-only at {rows['xgboost_residual_research']['primary_metric']:+.2f}% on {rows['xgboost_residual_research']['primary_sample']} races with {rows['xgboost_residual_research']['secondary_metric']}; "
        "the broader selective-family comparison line stays explicitly replay-only rather than extra train-only proof; "
        "OP_REFINED_K7 challenger diagnostic now makes the smaller 49/115 sample, 2/10 vs 7/10 walk-forward support, positive-CI nuance, explicit CI-only promotion block, and separate 20/30 paper-observation gates explicit before any anchor-change discussion; "
        "stale Phase 7 live-portfolio labels are removed from the OP-anchor markdown/JSON surfaces and replaced by the Phase 7 OP/CD rule-component basket label; "
        "the current odds-only XGBoost path stays parked unless the evidence class changes materially; "
        f"current paper snapshot now carries the combined operator_status_context/source_freshness/operator_read_gate route plus current_evidence_summary.json source freshness, refresh routing, operator_read_gate ({current_operator_boundary['operator_read_gate']['gate_status']} via {current_operator_boundary['operator_read_gate']['recommended_command']}), scorecard_audit_route to {scorecard_audit_route['markdown_path']} / {scorecard_audit_route['json_path']} plus {scorecard_audit_route['validator_command']} for copied gate/ranking/CI-only/timezone/no-BAQ synchronization metadata only, rebuild_validation_contract order {rebuild_order_commands} for settlement-audit -> current-bridge -> bridge-validator provenance before current totals are quoted, bridge-published decision_gate_progress ({current_gate_progress['read']}), {current_operator_boundary['roi_complete_primary_rows']}/{current_operator_boundary['first_read_threshold']} primary ROI-complete rows, 0 OP_DURABLE_K7 settled rows, {current_operator_boundary['cd_companion_roi_complete_rows']} CD_CORE_K8 settled rows, and settlement queue state={current_operator_boundary['open_settlement_queue_state']} with {current_operator_boundary['open_settlement_rows']} open rows as operator context rather than OP-anchor proof; "
        "the settlement queue state/context now comes from the source-published current-evidence bridge fields while the detail cell uses the source detail_read rather than nesting the state wrapper; "
        f"copied current-evidence generated_at={current_operator_boundary['generated_at']} stays parseable timezone-aware provenance metadata only before the OP-anchor comparison republishes current-paper context; "
        f"source-freshness bridge reference={current_operator_boundary['source_freshness_generated_reference_date']} ({current_operator_boundary['source_freshness_generated_reference_timezone']}) and comparison={current_operator_boundary['source_freshness_staleness_comparison_source']}:{current_operator_boundary['source_freshness_staleness_comparison_date']} are printed as operator-readiness provenance; "
        f"refresh-accounting fields stay fail-closed with wrapper-can-settle-rows={current_operator_boundary['refresh_can_settle_open_rows_by_itself']}, wrapper-counts-as-ROI-evidence={current_operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}, clean-empty-forward-performance={current_operator_boundary['clean_empty_refresh_counts_as_forward_performance']}; "
        "missing operator_read_gate, missing/weakened rebuild_validation_contract, missing source_freshness, missing source_freshness reference fields, missing refresh-action boundary, missing-or-false refresh-action non-evidence flags, and weakened clean-empty refresh-accounting flags are fixture-tested as no-output-directory/no-artifact CLI paths before current-paper bridge republishing; "
        "paper-observation gates now pin OP_REFINED_K7 promotion, current odds-only XGBoost reopening, BEL/BAQ substitution, and real-money scaling behind forward evidence thresholds, with evidence scope now distinguishing future settled ledger observations from historical replay, clean scans, open signals, or another odds-only rerun; "
        "anchor-review policy now reads forward_evidence_scorecard.json decision_gate_minimums directly and separates the 20-row Phase 8 promotion-review threshold from the stricter 30-row OP anchor-displacement discussion threshold plus the 100-row real-money discussion floor; "
        "scorecard ranking-contract inheritance now pins tier-first rank semantics, forward_trust secondary-within-tier semantics, and raw-score non-deployment semantics so raw OP_REFINED_K7 score does not become an automatic promotion cue; "
        "source fingerprints now pin the exact scorecard CSV/JSON / compare-main / method-family / cross-family / downstream A/B / current-evidence input bytes, with the markdown source-provenance table matching the JSON source_fingerprints map, as reproducibility metadata only; "
        "artifact-level machine-readable evidence_boundary plus evidence_boundary_text metadata now says the OP-anchor comparison and current-paper snapshot are posture/reproducibility or operator-routing metadata only rather than settled ROI, live profitability, promotion readiness, or real-money evidence; "
        "saved JSON, saved markdown, source provenance, boundary text, and real CLI stdout stay pinned to the same OP-anchor comparison render"
    )

    report_payload = {
        "suite_status": "pass",
        "artifact": {
            "markdown": OUT_MD.name,
            "json": OUT_JSON.name,
            "status": "pass",
            "tmp_parent": str(tmp_parent),
            "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
            "tmp_parent_cleared_before_fixture_run": True,
        },
        "scratch": scratch_meta,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "evidence_boundary": oamc.MACHINE_READABLE_EVIDENCE_BOUNDARY,
        "evidence_boundary_text": oamc.EVIDENCE_BOUNDARY_TEXT,
        "scorecard_ranking_contract": scorecard_ranking_contract,
        "scorecard_decision_gate_minimums": scorecard_decision_gate_minimums,
        "anchor_review_policy": anchor_review_policy,
        "current_evidence_gate_progress_read": current_gate_progress,
        "current_evidence_rebuild_validation_contract_read": rebuild_validation_contract,
        "summary": {
            "suite_read": suite_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "tmp_parent": str(tmp_parent),
            "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
            "tmp_parent_cleared_before_fixture_run": True,
        },
    }

    lines = [
        "# OP Anchor Method Comparison Validation",
        "",
        "This validator rebuilds `op_anchor_method_comparison.py` and pins the saved JSON/markdown artifacts plus the real CLI stdout report against the current OP-centered read versus Harville and the current odds-only XGBoost path, including the inherited scorecard tier-first ranking contract, the mixed 2024/2025 OP anchor split, CI-lower-bound caution, explicit OP_REFINED_K7 challenger diagnostics, the scorecard-derived decision-gate evidence-scope column, the separate 20-row promotion-review versus 30-row anchor-displacement thresholds plus 100-row real-money floor, exact source fingerprints, source-byte drift behavior, and the fail-fast checks for missing scorecard/cross-family rows, malformed scorecard gate minima, or malformed downstream A/B JSON.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Temporary fixture root: `{tmp_parent}` (cleared before CLI fixture run)",
        f"- Artifacts checked: `{OUT_MD.name}`, `{OUT_JSON.name}`",
        "",
        "## Frozen Checks",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for item in checks:
        lines.append(f"| {item['check']} | {item['status'].upper()} | {item['detail']} |")

    boundary = report_payload["evidence_boundary"]
    boundary_text = report_payload["evidence_boundary_text"]
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            f"- Artifact role: {boundary['artifact_role']}",
            f"- `valid_evidence_scope={boundary['valid_evidence_scope']}`",
            f"- Valid use: {boundary['valid_use']}",
            f"- Machine-readable boundary text: {boundary_text}",
            "- This validator green read is OP-anchor comparison/reproducibility metadata only: it is not new forward evidence, a live paper-trade ledger, current-day scanner output, settled ROI, live profitability, promotion readiness, or real-money evidence.",
            "- Source fingerprints are reproducibility metadata only; decision gates are forward-observation requirements, not current evidence that a gate has been cleared.",
            "- Stronger forward confidence still requires qualifying live paper signals, ROI-complete settled paper rows, settlement-quality checks, or other real forward observations.",
            f"- Anchor-review policy: {anchor_review_policy['policy_read']}",
            "- Non-goals: do not promote OP_REFINED_K7, reopen current odds-only XGBoost, treat Harville as live, substitute BAQ for BEL, or discuss real-money scaling from this validator pass.",
            "",
            "## Current Read",
            "",
            f"- {suite_read}",
            "- Source-drift guardrail: required scorecard anchor/challenger rows, forward-scorecard ranking-contract semantics, cross-family shadow rows, and downstream A/B delta fields now fail fast, including the forward_trust secondary-within-tier ranking-contract flag, while row-identical scorecard byte drift updates source provenance only instead of degrading into a polished-looking but incomplete OP-anchor comparison",
            "- Anchor-review policy guardrail: scorecard decision_gate_minimums source the 20 ROI-complete shadow-row Phase 8 review gate, 30+ ROI-complete same-candidate anchor-displacement gate, and 100+ settled-observation real-money discussion floor; local comparison prose must not drift from those source gates.",
            "",
            "## Sources",
            "",
            f"- `{OUT_MD.name}`",
            f"- `{OUT_JSON.name}`",
        ]
    )

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(report_payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    print("PASS op_anchor_method_comparison")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
