#!/usr/bin/env python3
"""
Validation for PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md / .json.

Purpose:
- keep the compact paper-trade source-chain matrix source-matched to the direct validators
- verify the scan/recommend/size/log guardrail inventories remain machine-readable
- keep the matrix explicitly framed as reproducibility/readiness, not forward-performance evidence
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import paper_trade_source_chain_guardrails as matrix

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_source_chain_guardrails"
REPORT_MD = OUT_DIR / "paper_trade_source_chain_guardrails_validation.md"
REPORT_JSON = OUT_DIR / "paper_trade_source_chain_guardrails_validation.json"
TMP_PARENT = OUT_DIR / "_tmp"
SAVED_MD = BASE / "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md"
SAVED_JSON = BASE / "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json"
REBUILD_COMMAND = "python3 validate_paper_trade_source_chain_guardrails.py"
EXPECTED_LABELS = [layer["label"] for layer in matrix.EXPECTED_LAYERS]
EXPECTED_GUARDRAILS = {
    layer["label"]: layer["expected_guardrails"] for layer in matrix.EXPECTED_LAYERS
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, check: str, detail: str) -> dict[str, str]:
    if not condition:
        raise AssertionError(f"{check}: {detail}")
    return {"check": check, "status": "pass", "detail": detail}


def prepare_tmp_parent() -> Path:
    if TMP_PARENT.exists():
        shutil.rmtree(TMP_PARENT)
    TMP_PARENT.mkdir(parents=True, exist_ok=True)
    return TMP_PARENT


def run_matrix(
    output_md: Path | None = None,
    output_json: Path | None = None,
    current_evidence_json: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(BASE / "paper_trade_source_chain_guardrails.py")]
    if current_evidence_json is not None:
        cmd.extend(["--current-evidence-json", str(current_evidence_json)])
    if output_md is not None:
        cmd.extend(["--output-md", str(output_md)])
    if output_json is not None:
        cmd.extend(["--output-json", str(output_json)])
    result = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(f"matrix rebuild failed: stdout={result.stdout!r} stderr={result.stderr!r}")
    return result


def normalized_for_custom(payload: dict[str, Any], md_path: Path, json_path: Path) -> dict[str, Any]:
    copy = json.loads(json.dumps(payload))
    copy["rebuild"]["output_md"] = str(md_path.relative_to(BASE)) if md_path.is_relative_to(BASE) else str(md_path)
    copy["rebuild"]["output_json"] = str(json_path.relative_to(BASE)) if json_path.is_relative_to(BASE) else str(json_path)
    return copy


def expected_fingerprint_markdown_rows(payload: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    for label in EXPECTED_LABELS:
        fp = payload["input_fingerprints"][label]
        rows.append(f"| `{fp['path']}` | {fp['bytes']} | `{fp['sha256']}` |")

    for label in EXPECTED_LABELS:
        fingerprints = payload["source_file_fingerprints"][label]
        source_fp = fingerprints["source_script"]
        validator_fp = fingerprints["validator"]
        rows.append(
            f"| `{label}` | `{source_fp['path']}` | {source_fp['bytes']} | `{source_fp['sha256']}` | "
            f"`{validator_fp['path']}` | {validator_fp['bytes']} | `{validator_fp['sha256']}` |"
        )

    tooling = payload["matrix_tooling_fingerprints"]
    rows.append(
        f"| generator | `{tooling['generator']['path']}` | {tooling['generator']['bytes']} | "
        f"`{tooling['generator']['sha256']}` |"
    )
    rows.append(
        f"| validator | `{tooling['validator']['path']}` | {tooling['validator']['bytes']} | "
        f"`{tooling['validator']['sha256']}` |"
    )
    return rows


def source_matrix_artifact_fingerprints() -> dict[str, dict[str, Any]]:
    return {
        "markdown": matrix.file_fingerprint(SAVED_MD),
        "json": matrix.file_fingerprint(SAVED_JSON),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_parent = prepare_tmp_parent()

    run_matrix()
    payload = load_json(SAVED_JSON)
    markdown = SAVED_MD.read_text(encoding="utf-8")
    source_matrix_fingerprints = source_matrix_artifact_fingerprints()
    fresh_payload = matrix.build_payload()
    fresh_payload["rebuild"]["output_md"] = str(SAVED_MD.relative_to(BASE))
    fresh_payload["rebuild"]["output_json"] = str(SAVED_JSON.relative_to(BASE))

    layer_map = {row["label"]: row for row in payload.get("layers", [])}
    parent_rollup = payload.get("parent_rollup_propagation", {})
    parent_rollups = parent_rollup.get("rollups", []) if isinstance(parent_rollup, dict) else []
    current_hierarchy = payload.get("current_hierarchy_boundary")
    if not isinstance(current_hierarchy, dict):
        current_hierarchy = {}
    decision_gates = payload.get("decision_gate_minimums")
    if not isinstance(decision_gates, dict):
        decision_gates = {}
    current_evidence_rebuild_contract = payload.get("current_evidence_rebuild_validation_contract")
    if not isinstance(current_evidence_rebuild_contract, dict):
        current_evidence_rebuild_contract = {}
    evidence_boundary_metadata = payload.get("evidence_boundary_metadata")
    if not isinstance(evidence_boundary_metadata, dict):
        evidence_boundary_metadata = {}
    live_scan_boundary_contract = payload.get("live_scan_boundary_contract")
    if not isinstance(live_scan_boundary_contract, dict):
        live_scan_boundary_contract = {}
    source_file_fingerprints = payload.get("source_file_fingerprints")
    matrix_tooling_fingerprints = payload.get("matrix_tooling_fingerprints")
    scan_reuse_coverage = payload.get("scan_reuse_coverage_contract")
    pipeline_payload = load_json(BASE / "out/status_validation/paper_trade_pipeline/paper_trade_pipeline_validation.json")
    pipeline_case_names = {
        case.get("name")
        for case in pipeline_payload.get("cases", [])
        if isinstance(case, dict) and isinstance(case.get("name"), str)
    }
    checks: list[dict[str, str]] = [
        require(
            payload == fresh_payload,
            "saved_json_matches_fresh_source_chain_rebuild",
            "saved source-chain JSON exactly matches a fresh rebuild from the four direct source-layer validator JSON artifacts",
        ),
        require(
            payload.get("suite_status") == "pass"
            and payload.get("artifact_status") == "pass"
            and payload.get("total_layers") == 4
            and payload.get("total_fixture_scenarios") == 48
            and payload.get("total_source_validator_checks") == 48
            and payload.get("total_guardrail_checks") == 46,
            "matrix_totals_pin_complete_scan_recommend_size_log_chain",
            "matrix totals still cover four source layers, 48 direct fixture checks, and 46 structured guardrails across scan/recommend/size/log",
        ),
        require(
            list(layer_map) == EXPECTED_LABELS
            and all(layer_map[label].get("suite_status") == "pass" for label in EXPECTED_LABELS)
            and all(layer_map[label].get("total_checks") == layer_map[label].get("check_count") for label in EXPECTED_LABELS),
            "matrix_preserves_layer_order_status_and_direct_check_counts",
            "matrix keeps the scan -> recommend -> size -> log order, each child validator PASS status, and direct total/check_count parity visible",
        ),
        require(
            all(
                [check.get("check") for check in layer_map[label].get("guardrail_checks", [])]
                == EXPECTED_GUARDRAILS[label]
                for label in EXPECTED_LABELS
            )
            and all(
                layer_map[label].get("child_guardrail_check_count") == len(EXPECTED_GUARDRAILS[label])
                for label in EXPECTED_LABELS
            ),
            "matrix_preserves_all_source_guardrail_inventories",
            "matrix keeps the exact guardrail inventory for each of pipeline, recommender, EV sizing, and logger without flattening them into prose-only status, including the pipeline, recommender, EV sizing, and logger scorecard-gate boundaries",
        ),
        require(
            isinstance(scan_reuse_coverage, dict)
            and scan_reuse_coverage.get("source_layer") == "paper_trade_pipeline"
            and scan_reuse_coverage.get("source_validator") == "validate_paper_trade_pipeline.py"
            and scan_reuse_coverage.get("policy") == matrix.SCAN_REUSE_COVERAGE_POLICY
            and scan_reuse_coverage.get("required_case_count") == len(matrix.SCAN_REUSE_COVERAGE_REQUIRED_CASES)
            and scan_reuse_coverage.get("required_case_names") == matrix.SCAN_REUSE_COVERAGE_REQUIRED_CASES
            and scan_reuse_coverage.get("covered_rows") == matrix.SCAN_REUSE_COVERAGE_ROWS
            and scan_reuse_coverage.get("intentional_non_expansion") == matrix.SCAN_REUSE_INTENTIONAL_NON_EXPANSION
            and all(case_name in pipeline_case_names for case_name in matrix.SCAN_REUSE_COVERAGE_REQUIRED_CASES)
            and all(row["candidate_case"] not in pipeline_case_names for row in matrix.SCAN_REUSE_INTENTIONAL_NON_EXPANSION)
            and "Do not add another scan-input / sidecar-state fixture solely to grow counts" in scan_reuse_coverage.get("stop_rule", "")
            and "fixture-matrix scope metadata only" in scan_reuse_coverage.get("evidence_boundary", ""),
            "matrix_pins_scan_reuse_coverage_contract_without_fixture_count_growth",
            "matrix now records the direct pipeline scan-reuse coverage policy, required case inventory, intentional non-expansion cases, and stop rule so sidecar-matrix work stays tied to real operator ambiguity rather than count growth",
        ),
        require(
            isinstance(payload.get("input_fingerprints"), dict)
            and set(payload["input_fingerprints"]) == set(EXPECTED_LABELS)
            and all(
                payload["input_fingerprints"][layer["label"]] == matrix.file_fingerprint(BASE / layer["report_json"])
                for layer in matrix.EXPECTED_LAYERS
            ),
            "matrix_fingerprints_exact_validator_json_inputs",
            "matrix records exact byte counts and SHA-256 fingerprints for each summarized validator JSON artifact",
        ),
        require(
            isinstance(source_file_fingerprints, dict)
            and set(source_file_fingerprints) == set(EXPECTED_LABELS)
            and all(
                source_file_fingerprints[layer["label"]].get("source_script") == matrix.file_fingerprint(BASE / layer["source_script"])
                and source_file_fingerprints[layer["label"]].get("validator") == matrix.file_fingerprint(BASE / layer["validator"])
                for layer in matrix.EXPECTED_LAYERS
            ),
            "matrix_fingerprints_exact_source_and_validator_scripts",
            "matrix records exact byte counts and SHA-256 fingerprints for each summarized source script and validator script",
        ),
        require(
            isinstance(matrix_tooling_fingerprints, dict)
            and matrix_tooling_fingerprints.get("generator") == matrix.file_fingerprint(BASE / matrix.MATRIX_GENERATOR)
            and matrix_tooling_fingerprints.get("validator") == matrix.file_fingerprint(BASE / matrix.MATRIX_VALIDATOR),
            "matrix_fingerprints_exact_generator_and_validator_tooling",
            "matrix records exact byte counts and SHA-256 fingerprints for the matrix generator and direct validator, so the compact matrix tooling itself is source-matched",
        ),
        require(
            "operational reproducibility/readiness artifact only" in payload.get("evidence_boundary", "")
            and "not settlement-complete ROI" in payload.get("evidence_boundary", "")
            and "not a promotion signal" in payload.get("evidence_boundary", "")
            and "not real-money profitability evidence" in payload.get("evidence_boundary", "")
            and "not to infer settled ROI, promotion readiness, or live/real-money profitability" in payload.get("summary", {}).get("suite_read", ""),
            "matrix_keeps_no_new_forward_evidence_boundary",
            "matrix explicitly says it is source-chain reproducibility/readiness only, not settled ROI, promotion readiness, live profitability, or real-money evidence",
        ),
        require(
            evidence_boundary_metadata.get("artifact_role") == "paper-trade source-chain guardrail matrix"
            and evidence_boundary_metadata.get("valid_evidence_scope") == matrix.MATRIX_VALID_EVIDENCE_SCOPE
            and evidence_boundary_metadata.get("valid_use")
            == "source-layer reproducibility and failure-mode readiness audit for scan -> recommend -> size -> log"
            and evidence_boundary_metadata.get("source_scope")
            == payload.get("source_scope")
            and evidence_boundary_metadata.get("decision_gate_source") == "forward_evidence_scorecard.json"
            and evidence_boundary_metadata.get("decision_gate_source_path") == "decision_gate_minimums"
            and evidence_boundary_metadata.get("current_evidence_rebuild_contract_source") == "current_evidence_summary.json"
            and evidence_boundary_metadata.get("current_evidence_rebuild_contract_source_path") == "rebuild_validation_contract"
            and evidence_boundary_metadata.get("current_evidence_rebuild_contract_is_provenance_metadata_only") is True
            and evidence_boundary_metadata.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and evidence_boundary_metadata.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and evidence_boundary_metadata.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and evidence_boundary_metadata.get("real_money_no_baq_as_bel_required") is True
            and evidence_boundary_metadata.get("not_live_paper_trade_ledger") is True
            and evidence_boundary_metadata.get("not_current_day_scanner_result") is True
            and evidence_boundary_metadata.get("not_observed_settlement_pnl") is True
            and evidence_boundary_metadata.get("not_settled_roi_evidence") is True
            and evidence_boundary_metadata.get("not_live_profitability_evidence") is True
            and evidence_boundary_metadata.get("not_real_money_evidence") is True
            and evidence_boundary_metadata.get("not_promotion_readiness_evidence") is True
            and evidence_boundary_metadata.get("not_anchor_change_evidence") is True
            and evidence_boundary_metadata.get("not_companion_change_evidence") is True
            and evidence_boundary_metadata.get("not_paper_scope_change_evidence") is True
            and evidence_boundary_metadata.get("not_phase8_promotion_evidence") is True
            and evidence_boundary_metadata.get("not_odds_only_xgboost_reopening_evidence") is True
            and evidence_boundary_metadata.get("baq_as_bel_substitution_allowed") is False
            and "do not treat source-chain readiness as settled ROI"
            in evidence_boundary_metadata.get("non_goals", [])
            and "do not use this matrix to promote OP_REFINED_K7 or widen the current paper scope"
            in evidence_boundary_metadata.get("non_goals", [])
            and "do not substitute BAQ for BEL" in evidence_boundary_metadata.get("non_goals", [])
            and "Machine-readable boundary highlights:" in markdown
            and "Artifact role: `paper-trade source-chain guardrail matrix`." in markdown
            and f"`valid_evidence_scope={matrix.MATRIX_VALID_EVIDENCE_SCOPE}`" in markdown
            and "Decision-gate source: `forward_evidence_scorecard.json` `decision_gate_minimums`." in markdown
            and "Source-driven gates carried here: anchor displacement `30`, Phase 8 promotion review `20`, real-money discussion `100`, no BAQ-as-BEL prerequisite `True`." in markdown
            and "Not evidence for settled ROI, live profitability, promotion readiness, anchor change, companion change, paper-scope change, odds-only XGBoost reopening, BAQ/BEL substitution, or real-money profitability." in markdown,
            "matrix_publishes_machine_readable_evidence_boundary_metadata",
            "matrix now publishes a source-driven evidence_boundary_metadata block that pins its valid use, scorecard-sourced 30/20/100 gates, no-BAQ-as-BEL prerequisite, current-evidence rebuild-contract source/path, and non-evidence boundaries for ROI, promotion, anchor/companion/scope changes, XGBoost reopening, BAQ/BEL substitution, and real-money profitability",
        ),
        require(
            payload.get("valid_evidence_scope") == matrix.MATRIX_VALID_EVIDENCE_SCOPE
            and evidence_boundary_metadata.get("valid_evidence_scope") == matrix.MATRIX_VALID_EVIDENCE_SCOPE
            and f"`valid_evidence_scope={matrix.MATRIX_VALID_EVIDENCE_SCOPE}`" in markdown,
            "matrix_exposes_source_chain_valid_evidence_scope",
            "matrix JSON, evidence-boundary metadata, and markdown now expose exact valid_evidence_scope=source_chain_operational_readiness_guardrail_only so the compact source-chain audit can be copied as readiness metadata only rather than scanner evidence, settled ROI, promotion readiness, live profitability, or real-money support",
        ),
        require(
            current_hierarchy.get("anchor") == "OP_DURABLE_K7"
            and current_hierarchy.get("primary_paper_basket_companion") == "CD_CORE_K8"
            and current_hierarchy.get("same_family_shadow_watch") == "OP_REFINED_K7"
            and "CD_CORE_K8 remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion" in current_hierarchy.get("boundary_read", "")
            and "BAQ is not BEL" in current_hierarchy.get("boundary_read", "")
            and current_hierarchy.get("not_settled_roi_evidence") is True
            and current_hierarchy.get("not_live_profitability_evidence") is True
            and current_hierarchy.get("not_promotion_readiness_evidence") is True
            and current_hierarchy.get("not_anchor_change_evidence") is True
            and current_hierarchy.get("not_real_money_evidence") is True
            and "## Current Hierarchy Boundary" in markdown
            and "`OP_DURABLE_K7` remains the safest current OP anchor." in markdown
            and "`CD_CORE_K8` remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion." in markdown
            and "`OP_REFINED_K7` remains the closest same-family shadow/watch challenger." in markdown
            and "BAQ is not BEL." in markdown
            and "Source-chain readiness and validator cleanliness are not settled ROI, live-profitability evidence, promotion readiness, anchor-change evidence, or real-money evidence." in markdown
            and "keeps OP_DURABLE_K7 as anchor, CD_CORE_K8 as the primary OP/CD paper-basket companion, and OP_REFINED_K7 in shadow/watch" in payload.get("summary", {}).get("suite_read", ""),
            "matrix_preserves_current_hierarchy_boundary",
            "matrix JSON and markdown now publish the OP_DURABLE_K7 anchor, CD_CORE_K8 paper-basket companion, OP_REFINED_K7 shadow/watch, BAQ-not-BEL, and no-ROI/no-promotion/no-anchor-change/no-real-money boundary so source-chain readiness cannot be mistaken for hierarchy-changing evidence",
        ),
        require(
            decision_gates == matrix.load_decision_gate_minimums()
            and decision_gates.get("source_path") == "forward_evidence_scorecard.json"
            and decision_gates.get("source_loaded") is True
            and decision_gates.get("anchor_displacement_min") == 30
            and decision_gates.get("phase8_promotion_review_min") == 20
            and decision_gates.get("real_money_discussion_min") == 100
            and decision_gates.get("real_money_no_baq_as_bel_required") is True
            and "no BAQ-as-BEL substitution" in decision_gates.get("real_money_discussion_also_requires", [])
            and "## Decision-Gate Source" in markdown
            and "Source: `forward_evidence_scorecard.json` `decision_gate_minimums`." in markdown
            and "Anchor displacement: `30` ROI-complete same candidate paper observations." in markdown
            and "Phase 8 promotion review: `20` ROI-complete candidate shadow observations." in markdown
            and "Real-money discussion: `100` total settled observations with usable ROI." in markdown
            and "Real-money prerequisites: positive paper ROI; concentration checks; payout-distribution sanity checks; no BAQ-as-BEL substitution." in markdown
            and "source-chain readiness, scan fallback coverage, fingerprints, and green validators do not clear them" in markdown
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL real-money prerequisite" in payload.get("summary", {}).get("suite_read", ""),
            "matrix_preserves_scorecard_decision_gate_minimums",
            "matrix JSON and markdown now carry the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL real-money prerequisite as source-chain metadata only, so upstream scan/recommend/size/log readiness cannot be mistaken for cleared paper or real-money gates",
        ),
        require(
            current_evidence_rebuild_contract == matrix.load_rebuild_validation_contract()
            and current_evidence_rebuild_contract.get("source") == "current_evidence_summary.json"
            and current_evidence_rebuild_contract.get("source_path") == "rebuild_validation_contract"
            and current_evidence_rebuild_contract.get("upstream_refresh_commands") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and current_evidence_rebuild_contract.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and current_evidence_rebuild_contract.get("requires_source_consistency_before_quoting_current_totals") is True
            and current_evidence_rebuild_contract.get("requires_source_freshness_before_right_now_instruction_use") is True
            and current_evidence_rebuild_contract.get("upstream_refresh_order_is_provenance_metadata_only") is True
            and current_evidence_rebuild_contract.get("not_settled_roi_or_real_money_evidence") is True
            and "## Current-Evidence Rebuild Route" in markdown
            and "Source: `current_evidence_summary.json` `rebuild_validation_contract`." in markdown
            and "Required order after scorecard/rules/signals/settlement-ledger source-byte changes: `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`." in markdown
            and "Use before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes." in markdown
            and "this route is provenance/rebuild metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in markdown
            and "current-evidence rebuild route through settlement audit -> current bridge -> bridge validator before CURRENT_EVIDENCE_SUMMARY totals are quoted" in payload.get("summary", {}).get("suite_read", ""),
            "matrix_preserves_current_evidence_rebuild_validation_contract",
            "matrix JSON and markdown now carry current_evidence_summary.json rebuild_validation_contract so source-chain readers route source-byte changes through settlement audit -> current bridge -> bridge validator before quoting current totals, while keeping that route as provenance/rebuild metadata only",
        ),
        require(
            "## Source-Layer Matrix" in markdown
            and "## Scan Reuse Coverage" in markdown
            and matrix.SCAN_REUSE_COVERAGE_POLICY in markdown
            and "`missing_scan_output`" in markdown
            and "`invalid_scan_output`" in markdown
            and f"Required scan-reuse fixture cases pinned here: {len(matrix.SCAN_REUSE_COVERAGE_REQUIRED_CASES)}" in markdown
            and "Do not add another scan-input / sidecar-state fixture solely to grow counts" in markdown
            and "empty-sidecar provenance for malformed and invalid-shape reused scan inputs" in markdown
            and "None currently; every scan-input / sidecar-state ambiguity named in this matrix has an explicit fixture." in markdown
            and all(row["candidate_case"] in markdown for row in matrix.SCAN_REUSE_INTENTIONAL_NON_EXPANSION)
            and live_scan_boundary_contract.get("source_script") == matrix.LIVE_SCAN_SOURCE_SCRIPT
            and live_scan_boundary_contract.get("source_validator") == matrix.LIVE_SCAN_VALIDATOR
            and live_scan_boundary_contract.get("source_validator_report_json") == matrix.LIVE_SCAN_BOUNDARY_REPORT_JSON
            and live_scan_boundary_contract.get("source_validator_report_md") == matrix.LIVE_SCAN_BOUNDARY_REPORT_MD
            and live_scan_boundary_contract.get("valid_evidence_scope") == matrix.LIVE_SCAN_VALID_EVIDENCE_SCOPE
            and live_scan_boundary_contract.get("status_sidecar_fields_pinned") == [
                "valid_evidence_scope",
                "evidence_boundary",
                "evidence_boundary_text",
            ]
            and live_scan_boundary_contract.get("hit_row_fields_pinned") == [
                "valid_evidence_scope",
                "evidence_boundary",
                "evidence_boundary_text",
            ]
            and live_scan_boundary_contract.get("text_output_scope_line_pinned") is True
            and live_scan_boundary_contract.get("empty_csv_header_fields_pinned") == [
                "valid_evidence_scope",
                "evidence_boundary_text",
            ]
            and live_scan_boundary_contract.get("api_access_status_sidecar_boundary_pinned") is True
            and live_scan_boundary_contract.get("boundary_checks_pinned") == matrix.LIVE_SCAN_BOUNDARY_CHECKS
            and live_scan_boundary_contract.get("evidence_boundary_text") == matrix.LIVE_SCAN_BOUNDARY_TEXT
            and "not a current-day scanner result" in live_scan_boundary_contract.get("evidence_boundary", "")
            and live_scan_boundary_contract.get("validator_report_fingerprint") == matrix.file_fingerprint(BASE / matrix.LIVE_SCAN_BOUNDARY_REPORT_JSON)
            and live_scan_boundary_contract.get("source_script_fingerprint") == matrix.file_fingerprint(BASE / matrix.LIVE_SCAN_SOURCE_SCRIPT)
            and live_scan_boundary_contract.get("validator_script_fingerprint") == matrix.file_fingerprint(BASE / matrix.LIVE_SCAN_VALIDATOR)
            and "## Live Scanner Boundary Contract" in markdown
            and f"`valid_evidence_scope={matrix.LIVE_SCAN_VALID_EVIDENCE_SCOPE}`" in markdown
            and "`valid_evidence_scope, evidence_boundary, evidence_boundary_text`" in markdown
            and "`scanner_publishes_target_coverage_gap_counts, scanner_text_and_empty_csv_outputs_publish_valid_scope, scanner_api_access_failure_or_fallback_sidecar_is_structured`" in markdown
            and "Text output scope line pinned: `True`." in markdown
            and "Empty CSV header fields pinned: `valid_evidence_scope, evidence_boundary_text`." in markdown
            and matrix.LIVE_SCAN_BOUNDARY_TEXT in markdown
            and f"`{matrix.LIVE_SCAN_BOUNDARY_REPORT_JSON}`" in markdown
            and f"`{matrix.LIVE_SCAN_SOURCE_SCRIPT}`" in markdown
            and f"`{matrix.LIVE_SCAN_VALIDATOR}`" in markdown
            and "## Guardrail Inventory" in markdown
            and "## Source Fingerprints" in markdown
            and "## Source Code Fingerprints" in markdown
            and "## Matrix Tooling Fingerprints" in markdown
            and "These fingerprints identify the exact validator JSON artifacts summarized here. They prove source-artifact provenance only, not performance." in markdown
            and "These fingerprints identify the exact source and validator scripts behind each summarized layer. They prove code/artifact provenance only, not performance." in markdown
            and "These fingerprints identify the exact generator and direct validator that build and validate this matrix. They prove matrix-tooling provenance only, not performance." in markdown
            and f"`{matrix.MATRIX_GENERATOR}`" in markdown
            and f"`{matrix.MATRIX_VALIDATOR}`" in markdown
            and all(f"### {layer_map[label]['stage']} — `{label}`" in markdown for label in EXPECTED_LABELS),
            "markdown_report_is_human_readable_and_provenance_aware",
            "markdown report exposes the source-layer matrix, scan-reuse coverage contract, live-scanner source-boundary contract with the exact raw valid_evidence_scope line, per-layer guardrail inventory, validator-JSON fingerprints, source/validator script fingerprints, matrix-tooling fingerprints, and no-performance-provenance warning in a report-ready form",
        ),
        require(
            all(row in markdown for row in expected_fingerprint_markdown_rows(payload)),
            "markdown_fingerprint_tables_match_json_payload",
            "markdown report renders every validator-output, source/validator-code, and matrix-tooling fingerprint row from the JSON payload exactly, so the report-facing tables cannot drift from the machine-readable sidecar",
        ),
        require(
            source_matrix_fingerprints["markdown"]["path"] == "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md"
            and source_matrix_fingerprints["json"]["path"] == "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json"
            and source_matrix_fingerprints["markdown"]["bytes"] == len(markdown.encode("utf-8"))
            and source_matrix_fingerprints["json"] == matrix.file_fingerprint(SAVED_JSON),
            "validation_report_fingerprints_validated_matrix_artifacts",
            "validation report publishes exact byte counts and SHA-256 fingerprints for the validated source-chain markdown and JSON artifacts, so parent rollups can identify the matrix files behind this direct pass",
        ),
        require(
            parent_rollup.get("boundary") == matrix.PARENT_PROPAGATION_BOUNDARY
            and isinstance(parent_rollups, list)
            and [row.get("surface") for row in parent_rollups] == ["operator suite", "project surfaces"]
            and parent_rollups[0].get("validator") == "validate_paper_trade_operator_suite.py"
            and parent_rollups[0].get("embedded_key") == "auxiliary_source_chain_matrix"
            and parent_rollups[0].get("recommended_command") == "python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json"
            and parent_rollups[1].get("validator") == "validate_project_surfaces.py"
            and parent_rollups[1].get("embedded_key") == "paper_trade_operator_suite.auxiliary_source_chain_matrix"
            and parent_rollups[1].get("recommended_command") == "python3 validate_project_surfaces.py --reuse-existing-child-json"
            and "## Parent Rollup Propagation" in markdown
            and "`auxiliary_source_chain_matrix`" in markdown
            and "`paper_trade_operator_suite.auxiliary_source_chain_matrix`" in markdown
            and "matrix-payload rebuild parity" in markdown
            and "rather than a generic umbrella pass" in markdown
            and "not settled ROI, not promotion readiness, not live profitability, and not real-money evidence" in markdown,
            "matrix_documents_parent_rollup_propagation_boundary",
            "matrix now documents how the operator-suite and project-surface parent checks should preserve the embedded source-chain audit plus parent-side matrix-payload rebuild parity as readiness/provenance metadata, not flatten it into a generic green pass or treat it as ROI/promotion/live-profit evidence",
        ),
    ]

    checks.append(
        require(
            tmp_parent == TMP_PARENT
            and tmp_parent.is_relative_to(BASE)
            and tmp_parent.exists(),
            "custom_output_scratch_root_project_local",
            f"custom output matrix rebuild scratch writes use project-local temporary root {tmp_parent}, cleared before validation",
        )
    )
    checks.append(
        require(
            tmp_parent == TMP_PARENT
            and tmp_parent.is_relative_to(BASE)
            and tmp_parent.exists(),
            "custom_output_scratch_metadata_published",
            "validation JSON publishes tmp_parent, tmp_parent_is_project_local, and tmp_parent_cleared_before_fixture_run so parent rollups can audit custom-output scratch hygiene without parsing markdown prose",
        )
    )

    with tempfile.TemporaryDirectory(prefix="source_chain_custom_output_", dir=tmp_parent) as tmp:
        tmpdir = Path(tmp)
        custom_md = tmpdir / "custom_source_chain.md"
        custom_json = tmpdir / "custom_source_chain.json"
        result = run_matrix(custom_md, custom_json)
        custom_payload = load_json(custom_json)
        checks.append(
            require(
                custom_payload == normalized_for_custom(fresh_payload, custom_md, custom_json)
                and "PASS source-chain guardrails: 4 layers, 48 fixture scenarios, 46 guardrails" in result.stdout,
                "custom_output_rebuild_matches_saved_payload_except_output_paths",
                "custom output rerenders preserve the same source-chain matrix payload and stdout totals, changing only the requested output paths",
            )
        )
        bool_gate_scorecard_json = tmpdir / "bool_gate_forward_evidence_scorecard.json"
        bool_gate_output_dir = tmpdir / "bool_gate_nested_output" / "artifacts"
        bool_gate_md = bool_gate_output_dir / "bool_gate_source_chain.md"
        bool_gate_json = bool_gate_output_dir / "bool_gate_source_chain.json"
        bool_gate_payload = load_json(BASE / "forward_evidence_scorecard.json")
        bool_gate_payload["decision_gate_minimums"]["anchor_displacement"][
            "min_roi_complete_settled_observations"
        ] = True
        bool_gate_scorecard_json.write_text(json.dumps(bool_gate_payload, indent=2) + "\n", encoding="utf-8")
        bool_gate_result = subprocess.run(
            [
                sys.executable,
                str(BASE / "paper_trade_source_chain_guardrails.py"),
                "--scorecard-json",
                str(bool_gate_scorecard_json),
                "--output-md",
                str(bool_gate_md),
                "--output-json",
                str(bool_gate_json),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if bool_gate_result.returncode == 0:
            raise AssertionError("source-chain matrix unexpectedly accepted a boolean anchor_displacement gate floor")
        bool_gate_text = f"{bool_gate_result.stdout}\n{bool_gate_result.stderr}"
        if (
            "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations "
            "must be a positive integer"
        ) not in bool_gate_text:
            raise AssertionError("boolean scorecard gate failure no longer names the malformed anchor_displacement threshold")
        checks.append(
            require(
                not bool_gate_output_dir.exists() and not bool_gate_md.exists() and not bool_gate_json.exists(),
                "scorecard_boolean_gate_floor_fails_before_matrix_artifacts",
                "the real source-chain matrix CLI now rejects a boolean scorecard gate floor before creating nested output directories or writing matrix artifacts",
            )
        )
        nonpositive_phase8_scorecard_json = tmpdir / "nonpositive_phase8_forward_evidence_scorecard.json"
        nonpositive_phase8_output_dir = tmpdir / "nonpositive_phase8_nested_output" / "artifacts"
        nonpositive_phase8_md = nonpositive_phase8_output_dir / "source_chain.md"
        nonpositive_phase8_json = nonpositive_phase8_output_dir / "source_chain.json"
        nonpositive_phase8_payload = load_json(BASE / "forward_evidence_scorecard.json")
        nonpositive_phase8_payload["decision_gate_minimums"]["phase8_promotion_review"][
            "min_roi_complete_settled_observations"
        ] = 0
        nonpositive_phase8_scorecard_json.write_text(
            json.dumps(nonpositive_phase8_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        nonpositive_phase8_result = subprocess.run(
            [
                sys.executable,
                str(BASE / "paper_trade_source_chain_guardrails.py"),
                "--scorecard-json",
                str(nonpositive_phase8_scorecard_json),
                "--output-md",
                str(nonpositive_phase8_md),
                "--output-json",
                str(nonpositive_phase8_json),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if nonpositive_phase8_result.returncode == 0:
            raise AssertionError("source-chain matrix unexpectedly accepted a non-positive phase8_promotion_review gate floor")
        nonpositive_phase8_text = f"{nonpositive_phase8_result.stdout}\n{nonpositive_phase8_result.stderr}"
        if (
            "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations "
            "must be a positive integer"
        ) not in nonpositive_phase8_text:
            raise AssertionError("non-positive Phase 8 scorecard gate failure no longer names the malformed threshold")
        checks.append(
            require(
                not nonpositive_phase8_output_dir.exists()
                and not nonpositive_phase8_md.exists()
                and not nonpositive_phase8_json.exists(),
                "scorecard_nonpositive_phase8_gate_floor_fails_before_matrix_artifacts",
                "the real source-chain matrix CLI now rejects a non-positive Phase 8 promotion-review scorecard gate before creating nested output directories or writing matrix artifacts",
            )
        )
        nonpositive_real_money_scorecard_json = tmpdir / "nonpositive_real_money_forward_evidence_scorecard.json"
        nonpositive_real_money_output_dir = tmpdir / "nonpositive_real_money_nested_output" / "artifacts"
        nonpositive_real_money_md = nonpositive_real_money_output_dir / "source_chain.md"
        nonpositive_real_money_json = nonpositive_real_money_output_dir / "source_chain.json"
        nonpositive_real_money_payload = load_json(BASE / "forward_evidence_scorecard.json")
        nonpositive_real_money_payload["decision_gate_minimums"]["real_money_discussion"][
            "min_total_settled_observations_with_usable_roi"
        ] = 0
        nonpositive_real_money_scorecard_json.write_text(
            json.dumps(nonpositive_real_money_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        nonpositive_real_money_result = subprocess.run(
            [
                sys.executable,
                str(BASE / "paper_trade_source_chain_guardrails.py"),
                "--scorecard-json",
                str(nonpositive_real_money_scorecard_json),
                "--output-md",
                str(nonpositive_real_money_md),
                "--output-json",
                str(nonpositive_real_money_json),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if nonpositive_real_money_result.returncode == 0:
            raise AssertionError("source-chain matrix unexpectedly accepted a non-positive real_money_discussion gate floor")
        nonpositive_real_money_text = f"{nonpositive_real_money_result.stdout}\n{nonpositive_real_money_result.stderr}"
        if (
            "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi "
            "must be a positive integer"
        ) not in nonpositive_real_money_text:
            raise AssertionError("non-positive real-money scorecard gate failure no longer names the malformed threshold")
        checks.append(
            require(
                not nonpositive_real_money_output_dir.exists()
                and not nonpositive_real_money_md.exists()
                and not nonpositive_real_money_json.exists(),
                "scorecard_nonpositive_real_money_gate_floor_fails_before_matrix_artifacts",
                "the real source-chain matrix CLI now rejects a non-positive real-money discussion scorecard gate before creating nested output directories or writing matrix artifacts",
            )
        )
        missing_contract_json = tmpdir / "missing_rebuild_contract_current_evidence_summary.json"
        missing_contract_output_dir = tmpdir / "missing_rebuild_contract_output" / "artifacts"
        missing_contract_md = missing_contract_output_dir / "source_chain.md"
        missing_contract_sidecar = missing_contract_output_dir / "source_chain.json"
        missing_contract_payload = load_json(BASE / "current_evidence_summary.json")
        missing_contract_payload.pop("rebuild_validation_contract", None)
        missing_contract_json.write_text(json.dumps(missing_contract_payload, indent=2) + "\n", encoding="utf-8")
        missing_contract_result = subprocess.run(
            [
                sys.executable,
                str(BASE / "paper_trade_source_chain_guardrails.py"),
                "--current-evidence-json",
                str(missing_contract_json),
                "--output-md",
                str(missing_contract_md),
                "--output-json",
                str(missing_contract_sidecar),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_contract_result.returncode == 0:
            raise AssertionError("source-chain matrix unexpectedly accepted current evidence without rebuild_validation_contract")
        missing_contract_text = f"{missing_contract_result.stdout}\n{missing_contract_result.stderr}"
        if "missing rebuild_validation_contract object" not in missing_contract_text:
            raise AssertionError("missing rebuild_validation_contract failure no longer names the missing contract")
        checks.append(
            require(
                not missing_contract_output_dir.exists()
                and not missing_contract_md.exists()
                and not missing_contract_sidecar.exists(),
                "missing_current_evidence_rebuild_contract_fails_before_matrix_artifacts",
                "the real source-chain matrix CLI now rejects a current-evidence JSON without rebuild_validation_contract before creating nested output directories or writing matrix artifacts",
            )
        )
        weakened_contract_json = tmpdir / "weakened_rebuild_contract_current_evidence_summary.json"
        weakened_contract_output_dir = tmpdir / "weakened_rebuild_contract_output" / "artifacts"
        weakened_contract_md = weakened_contract_output_dir / "source_chain.md"
        weakened_contract_sidecar = weakened_contract_output_dir / "source_chain.json"
        weakened_contract_payload = load_json(BASE / "current_evidence_summary.json")
        weakened_contract_payload["rebuild_validation_contract"][
            "upstream_refresh_order_is_provenance_metadata_only"
        ] = False
        weakened_contract_json.write_text(json.dumps(weakened_contract_payload, indent=2) + "\n", encoding="utf-8")
        weakened_contract_result = subprocess.run(
            [
                sys.executable,
                str(BASE / "paper_trade_source_chain_guardrails.py"),
                "--current-evidence-json",
                str(weakened_contract_json),
                "--output-md",
                str(weakened_contract_md),
                "--output-json",
                str(weakened_contract_sidecar),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if weakened_contract_result.returncode == 0:
            raise AssertionError("source-chain matrix unexpectedly accepted current evidence with a weakened rebuild_validation_contract")
        weakened_contract_text = f"{weakened_contract_result.stdout}\n{weakened_contract_result.stderr}"
        if "rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true" not in weakened_contract_text:
            raise AssertionError("weakened rebuild_validation_contract failure no longer names the provenance-only flag")
        checks.append(
            require(
                not weakened_contract_output_dir.exists()
                and not weakened_contract_md.exists()
                and not weakened_contract_sidecar.exists(),
                "weakened_current_evidence_rebuild_contract_fails_before_matrix_artifacts",
                "the real source-chain matrix CLI now rejects a current-evidence JSON whose rebuild_validation_contract weakens the provenance-only flag before creating nested output directories or writing matrix artifacts",
            )
        )

    suite_read = (
        "paper-trade source-chain guardrail matrix is source-matched to the four direct validators, preserves all 46 scan/recommend/size/log guardrails across 48 fixture scenarios, pins the direct live-scanner source-boundary contract for status sidecars and scanner hit rows plus copied text output and empty saved-CSV headers as paper-alert metadata only, exposes the exact raw `valid_evidence_scope=live_scanner_paper_alert_metadata_only` markdown line, fingerprints the summarized validator JSON artifacts plus source/validator scripts and matrix generator/validator tooling, renders markdown fingerprint tables exactly from the JSON sidecar, fingerprints the validated matrix markdown/JSON artifacts, documents parent rollup propagation through `auxiliary_source_chain_matrix` plus parent-side matrix-payload rebuild parity, keeps custom-output rebuild scratch files under a project-local validation root with published scratch metadata, fixture-tests boolean anchor scorecard gate floors, non-positive Phase 8 / real-money scorecard gate floors, and missing/weakened current-evidence rebuild contracts as no-artifact failures, publishes machine-readable evidence_boundary_metadata plus exact raw `valid_evidence_scope=source_chain_operational_readiness_guardrail_only` for source-driven gate/rebuild-route and non-evidence boundaries, publishes the current hierarchy boundary for OP_DURABLE_K7 / CD_CORE_K8 / OP_REFINED_K7 plus BAQ-not-BEL, carries scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL real-money prerequisite, carries current_evidence_summary.json rebuild_validation_contract before current totals are quoted, and stays explicitly non-promotional / non-profitability evidence"
    )
    payload_out = {
        "suite_status": "pass",
        "artifact_status": "pass",
        "valid_evidence_scope": matrix.MATRIX_VALID_EVIDENCE_SCOPE,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "source_matrix_fingerprints": source_matrix_fingerprints,
        "evidence_boundary_metadata": evidence_boundary_metadata,
        "summary": {"current_read": suite_read},
        "scratch": {
            "tmp_parent": str(tmp_parent),
            "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
            "tmp_parent_cleared_before_fixture_run": True,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "report_path": str(REPORT_MD),
            "source_matrix_md": str(SAVED_MD.relative_to(BASE)),
            "source_matrix_json": str(SAVED_JSON.relative_to(BASE)),
        },
    }

    lines = [
        "# Paper-Trade Source Chain Guardrail Matrix Validation",
        "",
        "This report validates the compact scan -> recommend -> size -> log guardrail matrix against the direct source-layer validator JSON artifacts.",
        "",
        "## Current Read",
        "",
        f"- {suite_read}",
        f"- valid_evidence_scope={matrix.MATRIX_VALID_EVIDENCE_SCOPE}",
        "",
        "## Checks",
        "",
    ]
    for check in checks:
        lines.append(f"- PASS `{check['check']}` — {check['detail']}")
    lines.extend(
        [
            "",
            "## Rebuild",
            "",
            f"- Working directory: `{BASE}`",
            f"- Command: `{REBUILD_COMMAND}`",
            f"- Matrix markdown: `{SAVED_MD.relative_to(BASE)}`",
            f"- Matrix JSON: `{SAVED_JSON.relative_to(BASE)}`",
            "",
            "## Scratch",
            "",
            f"- Temporary fixture root: `{tmp_parent}` (cleared before validation)",
            f"- Temporary fixture root project-local: `{tmp_parent.is_relative_to(BASE)}`",
        ]
    )

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(payload_out, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {SAVED_MD}")
    print(f"Wrote {SAVED_JSON}")
    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    print(f"PASS paper_trade_source_chain_guardrails {len(checks)}/{len(checks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
