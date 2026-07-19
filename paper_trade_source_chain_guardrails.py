#!/usr/bin/env python3
"""
Build a compact source-chain guardrail matrix for the paper-trade path.

Purpose:
- make the direct scan -> recommend -> size -> log source validators readable as one bundle
- preserve the machine-readable guardrail names that parent rollups depend on
- keep the artifact explicitly framed as operational reproducibility, not live edge/profit evidence
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
OUT_MD = BASE / "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md"
OUT_JSON = BASE / "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json"
SCORECARD_JSON = "forward_evidence_scorecard.json"
CURRENT_EVIDENCE_JSON = "current_evidence_summary.json"
REBUILD_COMMAND = "python3 paper_trade_source_chain_guardrails.py"
MATRIX_GENERATOR = "paper_trade_source_chain_guardrails.py"
MATRIX_VALIDATOR = "validate_paper_trade_source_chain_guardrails.py"
MATRIX_VALID_EVIDENCE_SCOPE = "source_chain_operational_readiness_guardrail_only"
MATRIX_SOURCE_SCOPE = (
    "saved direct source-layer validator JSON artifacts for paper_trade_pipeline, paper_trade_recommender, "
    "ev_ticket_engine, and paper_trade_logger, plus the direct live-scan validator's scanner-boundary contract"
)
LIVE_SCAN_BOUNDARY_REPORT_JSON = "out/status_validation/live_scan_targeting_and_limit_status/live_scan_targeting_and_limit_status_validation.json"
LIVE_SCAN_BOUNDARY_REPORT_MD = "out/status_validation/live_scan_targeting_and_limit_status/live_scan_targeting_and_limit_status_validation.md"
LIVE_SCAN_SOURCE_SCRIPT = "live_portfolio_scanner.py"
LIVE_SCAN_VALIDATOR = "validate_live_scan_targeting_and_limit_status.py"
LIVE_SCAN_VALID_EVIDENCE_SCOPE = "live_scanner_paper_alert_metadata_only"
LIVE_SCAN_BOUNDARY_TEXT = (
    "live scanner output is source-layer paper-alert metadata only; it is not settled ROI evidence, "
    "not live-profitability evidence, not promotion readiness, not OP-anchor replacement evidence, "
    "not Phase 8 promotion evidence, not bankroll guidance, and not real-money support."
)
LIVE_SCAN_BOUNDARY_CHECKS = [
    "scanner_publishes_target_coverage_gap_counts",
    "scanner_text_and_empty_csv_outputs_publish_valid_scope",
    "scanner_api_access_failure_or_fallback_sidecar_is_structured",
]
EVIDENCE_BOUNDARY = (
    "This matrix summarizes saved source-layer validation JSON for the scan -> recommend -> size -> log "
    "paper-trade chain. It is an operational reproducibility/readiness artifact only: it is not a live "
    "paper-trade ledger, not settlement-complete ROI, not a promotion signal, and not real-money profitability evidence."
)
PARENT_PROPAGATION_BOUNDARY = (
    "Parent rollup passes preserve this matrix as propagation/readiness metadata only: not settled ROI, "
    "not promotion readiness, not live profitability, and not real-money evidence."
)
CURRENT_HIERARCHY_BOUNDARY = {
    "anchor": "OP_DURABLE_K7",
    "primary_paper_basket_companion": "CD_CORE_K8",
    "same_family_shadow_watch": "OP_REFINED_K7",
    "boundary_read": (
        "OP_DURABLE_K7 remains the safest current OP anchor; CD_CORE_K8 remains the primary OP/CD "
        "paper-basket companion, not a Phase 8 shadow-lane promotion; OP_REFINED_K7 remains the closest "
        "same-family shadow/watch challenger; BAQ is not BEL; source-chain readiness and validator cleanliness "
        "are not settled ROI, live-profitability evidence, promotion readiness, anchor-change evidence, or real-money evidence."
    ),
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_anchor_change_evidence": True,
    "not_real_money_evidence": True,
}


def build_evidence_boundary_metadata(decision_gate_minimums: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_role": "paper-trade source-chain guardrail matrix",
        "valid_evidence_scope": MATRIX_VALID_EVIDENCE_SCOPE,
        "valid_use": (
            "source-layer reproducibility and failure-mode readiness audit for scan -> recommend -> size -> log"
        ),
        "source_scope": MATRIX_SOURCE_SCOPE,
        "decision_gate_source": decision_gate_minimums["source_path"],
        "decision_gate_source_path": "decision_gate_minimums",
        "current_evidence_rebuild_contract_source": "current_evidence_summary.json",
        "current_evidence_rebuild_contract_source_path": "rebuild_validation_contract",
        "current_evidence_rebuild_contract_is_provenance_metadata_only": True,
        "anchor_displacement_min_roi_complete_settled_observations": decision_gate_minimums[
            "anchor_displacement_min"
        ],
        "phase8_promotion_review_min_roi_complete_settled_observations": decision_gate_minimums[
            "phase8_promotion_review_min"
        ],
        "real_money_discussion_min_total_settled_observations_with_usable_roi": decision_gate_minimums[
            "real_money_discussion_min"
        ],
        "real_money_no_baq_as_bel_required": decision_gate_minimums["real_money_no_baq_as_bel_required"],
        "not_live_paper_trade_ledger": True,
        "not_current_day_scanner_result": True,
        "not_observed_settlement_pnl": True,
        "not_settled_roi_evidence": True,
        "not_live_profitability_evidence": True,
        "not_real_money_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_anchor_change_evidence": True,
        "not_companion_change_evidence": True,
        "not_paper_scope_change_evidence": True,
        "not_phase8_promotion_evidence": True,
        "not_odds_only_xgboost_reopening_evidence": True,
        "baq_as_bel_substitution_allowed": False,
        "non_goals": [
            "do not treat source-chain readiness as settled ROI",
            "do not treat green source validators as promotion readiness",
            "do not use this matrix to change the OP_DURABLE_K7 anchor",
            "do not use this matrix to promote OP_REFINED_K7 or widen the current paper scope",
            "do not reopen odds-only XGBoost from this artifact",
            "do not substitute BAQ for BEL",
            "do not discuss real-money profitability from this artifact",
        ],
    }


PARENT_ROLLUP_PROPAGATION: list[dict[str, str]] = [
    {
        "surface": "operator suite",
        "validator": "validate_paper_trade_operator_suite.py",
        "recommended_command": "python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json",
        "embedded_key": "auxiliary_source_chain_matrix",
        "preserves": "saved matrix paths, direct matrix checks, all-46-guardrails read, validator-JSON fingerprints, code fingerprints, matrix-tooling fingerprints, matrix-payload rebuild parity, and non-promotional boundary",
        "use_only_after": "Run the direct scan/recommend/size/log validators and validate_paper_trade_source_chain_guardrails.py first so child JSON is fresh.",
    },
    {
        "surface": "project surfaces",
        "validator": "validate_project_surfaces.py",
        "recommended_command": "python3 validate_project_surfaces.py --reuse-existing-child-json",
        "embedded_key": "paper_trade_operator_suite.auxiliary_source_chain_matrix",
        "preserves": "the operator-embedded matrix result and parent-side matrix-payload rebuild parity as project-level readiness metadata rather than a generic umbrella pass",
        "use_only_after": "Use after the operator suite has refreshed or reused a fresh source-chain validator JSON.",
    },
]

EXPECTED_LAYERS: list[dict[str, Any]] = [
    {
        "label": "paper_trade_pipeline",
        "stage": "scan wrapper",
        "source_script": "paper_trade_pipeline.py",
        "validator": "validate_paper_trade_pipeline.py",
        "report_json": "out/status_validation/paper_trade_pipeline/paper_trade_pipeline_validation.json",
        "report_md": "out/status_validation/paper_trade_pipeline/paper_trade_pipeline_validation.md",
        "expected_fixture_scenarios": 32,
        "expected_direct_checks": 32,
        "expected_guardrails": [
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
        ],
        "plain_role": "keeps live scan/recommend/log wrapper status, stdout-visible valid_evidence_scope plus boundary lines, direct validator valid_evidence_scope exposure, scanner sidecars, cache misses, API-access stale-cache fallback metadata, scanner-failure stale-scan overwrite protection, recommender-failure stale recommendation/prediction cleanup, pipeline errors, malformed/non-positive scorecard gates, project-local fixture scratch metadata, and scorecard gate boundaries operationally distinct",
    },
    {
        "label": "paper_trade_recommender",
        "stage": "recommend",
        "source_script": "paper_trade_recommender.py",
        "validator": "validate_paper_trade_recommender.py",
        "report_json": "out/status_validation/paper_trade_recommender/paper_trade_recommender_validation.json",
        "report_md": "out/status_validation/paper_trade_recommender/paper_trade_recommender_validation.md",
        "expected_fixture_scenarios": 6,
        "expected_direct_checks": 6,
        "expected_guardrails": [
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
        ],
        "plain_role": "keeps the default Phase 7 combo universe narrow and explicit about missing-race-id scanner hits, off-universe rows, malformed-prediction fallback behavior, stale plan-file and non-reuse prediction cleanup on direct reruns, source-level valid_evidence_scope plus evidence-boundary output, direct validator valid_evidence_scope exposure, malformed/non-positive scorecard gates, project-local fixture scratch metadata, and scorecard gate boundaries",
    },
    {
        "label": "ev_ticket_engine",
        "stage": "size",
        "source_script": "ev_ticket_engine.py",
        "validator": "validate_ev_ticket_engine.py",
        "report_json": "out/status_validation/ev_ticket_engine/ev_ticket_engine_validation.json",
        "report_md": "out/status_validation/ev_ticket_engine/ev_ticket_engine_validation.md",
        "expected_fixture_scenarios": 6,
        "expected_direct_checks": 6,
        "expected_guardrails": [
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
        ],
        "plain_role": "keeps conservative no-bet filters, risk caps, ticket floors, malformed probability-input failures, source-level valid_evidence_scope plus evidence-boundary output, direct validator valid_evidence_scope exposure, malformed/non-positive scorecard gates, project-local fixture scratch metadata, and scorecard gate boundaries pinned",
    },
    {
        "label": "paper_trade_logger",
        "stage": "log",
        "source_script": "paper_trade_logger.py",
        "validator": "validate_paper_trade_logger.py",
        "report_json": "out/status_validation/paper_trade_logger/paper_trade_logger_validation.json",
        "report_md": "out/status_validation/paper_trade_logger/paper_trade_logger_validation.md",
        "expected_fixture_scenarios": 4,
        "expected_direct_checks": 4,
        "expected_guardrails": [
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
        ],
        "plain_role": "keeps signal/recommendation ledger headers, append rows, state-plus-ledger dedup, malformed-state ledger rebuild fallback, blank-key handling, source-level valid_evidence_scope plus evidence-boundary output, direct validator valid_evidence_scope exposure, project-local fixture scratch metadata, scorecard gate boundaries, and malformed/non-positive-scorecard no-artifact failures pinned",
    },
]

SCAN_REUSE_COVERAGE_REQUIRED_CASES = [
    "case_skip_scan_missing_reuse",
    "case_skip_scan_missing_reuse_with_sidecar",
    "case_skip_scan_missing_reuse_with_empty_sidecar",
    "case_skip_scan_missing_reuse_with_unreadable_sidecar",
    "case_skip_scan_zero_byte_reuse",
    "case_skip_scan_zero_byte_reuse_with_sidecar",
    "case_skip_scan_zero_byte_reuse_with_empty_sidecar",
    "case_skip_scan_zero_byte_reuse_with_unreadable_sidecar",
    "case_skip_scan_malformed_reuse",
    "case_skip_scan_malformed_reuse_with_sidecar",
    "case_skip_scan_malformed_reuse_with_empty_sidecar",
    "case_skip_scan_malformed_reuse_with_unreadable_sidecar",
    "case_skip_scan_invalid_shape_reuse",
    "case_skip_scan_invalid_shape_reuse_with_sidecar",
    "case_skip_scan_invalid_shape_reuse_with_empty_sidecar",
    "case_skip_scan_invalid_shape_reuse_with_unreadable_sidecar",
]

SCAN_REUSE_COVERAGE_ROWS = [
    {
        "scan_input_state": "missing",
        "sidecar_states_pinned": "missing/default, readable, empty, unreadable",
        "controlling_result": "missing_scan_output",
        "operator_meaning": "the scan payload is absent, so the day is refresh-required even if a sidecar looks active",
    },
    {
        "scan_input_state": "empty",
        "sidecar_states_pinned": "missing/default, readable, empty, unreadable",
        "controlling_result": "missing_scan_output",
        "operator_meaning": "the scan payload is zero-byte, so the day is refresh-required rather than a clean empty observation",
    },
    {
        "scan_input_state": "unreadable",
        "sidecar_states_pinned": "missing/default, readable, empty, unreadable",
        "controlling_result": "invalid_scan_output",
        "operator_meaning": "the scan payload is malformed JSON, so the invalid scan outranks sidecar provenance",
    },
    {
        "scan_input_state": "invalid_shape",
        "sidecar_states_pinned": "missing/default, readable, empty, unreadable",
        "controlling_result": "invalid_scan_output",
        "operator_meaning": "the scan payload is readable but not the scanner-output list shape, so the invalid scan outranks sidecar provenance",
    },
]

SCAN_REUSE_INTENTIONAL_NON_EXPANSION: list[dict[str, str]] = []

SCAN_REUSE_COVERAGE_POLICY = (
    "The direct pipeline fixtures pin every missing/zero-byte scan-input sidecar state because those are the "
    "most likely copied or partial-artifact failure modes. Malformed and invalid-shape scan inputs are now also "
    "pinned against no sidecar, readable active-looking sidecar provenance, empty sidecar metadata, and unreadable "
    "sidecar metadata so invalid scan payloads consistently outrank sidecar provenance."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=Path(SCORECARD_JSON), help="forward evidence scorecard JSON input")
    parser.add_argument(
        "--current-evidence-json",
        type=Path,
        default=Path(CURRENT_EVIDENCE_JSON),
        help="current evidence summary JSON input for the rebuild-order contract",
    )
    parser.add_argument("--output-md", type=Path, default=OUT_MD, help="markdown output path")
    parser.add_argument("--output-json", type=Path, default=OUT_JSON, help="JSON sidecar output path")
    return parser.parse_args()


def resolve_input_path(path: str | Path) -> Path:
    path_obj = Path(path)
    return path_obj if path_obj.is_absolute() else BASE / path_obj


def display_input_path(path: str | Path) -> str:
    resolved = resolve_input_path(path)
    try:
        return str(resolved.relative_to(BASE))
    except ValueError:
        return str(resolved)


def file_fingerprint(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(BASE)),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def load_json(relative_path: str | Path) -> dict[str, Any]:
    path = resolve_input_path(relative_path)
    if not path.exists():
        raise FileNotFoundError(f"required validator JSON is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def require_positive_int(value: Any, dotted_path: str, source_display: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_display}: {dotted_path} must be a positive integer")
    return value


def load_decision_gate_minimums(scorecard_json: str | Path = SCORECARD_JSON) -> dict[str, Any]:
    source_display = display_input_path(scorecard_json)
    payload = load_json(scorecard_json)
    gates = payload.get("decision_gate_minimums")
    if not isinstance(gates, dict):
        raise AssertionError(f"{source_display}: missing decision_gate_minimums object")

    anchor = gates.get("anchor_displacement")
    phase8 = gates.get("phase8_promotion_review")
    real_money = gates.get("real_money_discussion")
    if not isinstance(anchor, dict) or not isinstance(phase8, dict) or not isinstance(real_money, dict):
        raise AssertionError(f"{source_display}: incomplete decision_gate_minimums object")

    anchor_min = require_positive_int(
        anchor.get("min_roi_complete_settled_observations"),
        "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
        source_display,
    )
    phase8_min = require_positive_int(
        phase8.get("min_roi_complete_settled_observations"),
        "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
        source_display,
    )
    real_money_min = require_positive_int(
        real_money.get("min_total_settled_observations_with_usable_roi"),
        "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
        source_display,
    )
    also_requires = real_money.get("also_requires")
    if not isinstance(also_requires, list) or not all(isinstance(item, str) for item in also_requires):
        raise AssertionError(f"{source_display}: real_money_discussion.also_requires must be a string list")

    no_baq_required = "no BAQ-as-BEL substitution" in also_requires
    if not no_baq_required:
        raise AssertionError(f"{source_display}: real_money_discussion.also_requires must include no BAQ-as-BEL substitution")

    return {
        "source_path": source_display,
        "source_loaded": True,
        "anchor_displacement_min": anchor_min,
        "anchor_displacement_scope": anchor.get("observation_scope"),
        "phase8_promotion_review_min": phase8_min,
        "phase8_promotion_review_scope": phase8.get("observation_scope"),
        "real_money_discussion_min": real_money_min,
        "real_money_discussion_also_requires": also_requires,
        "real_money_no_baq_as_bel_required": no_baq_required,
        "evidence_boundary": (
            "These are future ROI-complete paper-observation gates sourced from the scorecard; "
            "source-chain readiness, scan fallback coverage, fingerprints, and green validators do not clear them."
        ),
        "gate_read": (
            f"scorecard-sourced decision gates: anchor_displacement={anchor_min}, "
            f"phase8_promotion_review={phase8_min}, real_money_discussion={real_money_min}; "
            f"real-money discussion also requires {', '.join(also_requires)}"
        ),
    }


def load_rebuild_validation_contract(current_evidence_json: str | Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    source_display = display_input_path(current_evidence_json)
    payload = load_json(current_evidence_json)
    contract = payload.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise AssertionError(f"{source_display}: missing rebuild_validation_contract object")

    order = contract.get("upstream_refresh_order")
    if not isinstance(order, list) or len(order) != 3:
        raise AssertionError(f"{source_display}: rebuild_validation_contract.upstream_refresh_order must have three steps")
    commands = [row.get("command") for row in order if isinstance(row, dict)]
    expected_commands = [
        "python3 paper_trade_settlement_audit.py",
        "python3 current_evidence_summary.py",
        "python3 validate_current_evidence_summary.py",
    ]
    if commands != expected_commands:
        raise AssertionError(f"{source_display}: rebuild_validation_contract upstream order drifted")
    if [row.get("order") for row in order if isinstance(row, dict)] != [1, 2, 3]:
        raise AssertionError(f"{source_display}: rebuild_validation_contract order numbers drifted")
    if contract.get("prerequisite_rebuild_command") != expected_commands[0]:
        raise AssertionError(f"{source_display}: rebuild_validation_contract prerequisite command drifted")
    if contract.get("rebuild_command") != expected_commands[1]:
        raise AssertionError(f"{source_display}: rebuild_validation_contract rebuild command drifted")
    if contract.get("direct_validation_command") != expected_commands[2]:
        raise AssertionError(f"{source_display}: rebuild_validation_contract direct validation command drifted")

    for flag in (
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
        "requires_source_consistency_before_quoting_current_totals",
        "requires_source_freshness_before_right_now_instruction_use",
        "green_checks_are_reproducibility_metadata_only",
        "upstream_refresh_order_is_provenance_metadata_only",
        "not_settled_roi_or_real_money_evidence",
    ):
        if contract.get(flag) is not True:
            raise AssertionError(f"{source_display}: rebuild_validation_contract.{flag} must be true")

    copied = json.loads(json.dumps(contract))
    copied.update(
        {
            "source": source_display,
            "source_path": "rebuild_validation_contract",
            "upstream_refresh_commands": commands,
            "rebuild_route_read": (
                f"{source_display} rebuild_validation_contract routes source-byte changes through "
                f"{' -> '.join(commands)} before quoting CURRENT_EVIDENCE_SUMMARY.* as provenance/rebuild metadata only"
            ),
        }
    )
    return copied


def require_expected_layer(layer: dict[str, Any], payload: dict[str, Any]) -> None:
    expected_guardrails = layer["expected_guardrails"]
    actual_guardrails = [check.get("check") for check in payload.get("child_checks", [])]
    if payload.get("suite_status") != "pass":
        raise AssertionError(f"{layer['label']}: expected suite_status=pass, got {payload.get('suite_status')!r}")
    if payload.get("total_fixture_scenarios") != layer["expected_fixture_scenarios"]:
        raise AssertionError(
            f"{layer['label']}: expected {layer['expected_fixture_scenarios']} fixture scenarios, "
            f"got {payload.get('total_fixture_scenarios')!r}"
        )
    if payload.get("total_checks") != layer["expected_direct_checks"] or payload.get("check_count") != layer["expected_direct_checks"]:
        raise AssertionError(
            f"{layer['label']}: expected total/check_count {layer['expected_direct_checks']}, "
            f"got {payload.get('total_checks')!r}/{payload.get('check_count')!r}"
        )
    if payload.get("child_check_count") != len(expected_guardrails):
        raise AssertionError(
            f"{layer['label']}: expected {len(expected_guardrails)} child guardrails, "
            f"got {payload.get('child_check_count')!r}"
        )
    if actual_guardrails != expected_guardrails:
        raise AssertionError(
            f"{layer['label']}: guardrail inventory drifted\nactual={actual_guardrails}\nexpected={expected_guardrails}"
        )


def build_scan_reuse_coverage_contract(pipeline_payload: dict[str, Any]) -> dict[str, Any]:
    case_names = [
        case.get("name")
        for case in pipeline_payload.get("cases", [])
        if isinstance(case, dict) and isinstance(case.get("name"), str)
    ]
    case_name_set = set(case_names)
    missing_required = [
        case_name
        for case_name in SCAN_REUSE_COVERAGE_REQUIRED_CASES
        if case_name not in case_name_set
    ]
    unexpected_non_expansion = [
        row["candidate_case"]
        for row in SCAN_REUSE_INTENTIONAL_NON_EXPANSION
        if row["candidate_case"] in case_name_set
    ]
    if missing_required:
        raise AssertionError(f"pipeline scan-reuse coverage missing required cases: {missing_required}")
    if unexpected_non_expansion:
        raise AssertionError(
            "pipeline scan-reuse non-expansion cases are now present; update the coverage contract before publishing: "
            f"{unexpected_non_expansion}"
        )
    return {
        "source_layer": "paper_trade_pipeline",
        "source_validator": "validate_paper_trade_pipeline.py",
        "policy": SCAN_REUSE_COVERAGE_POLICY,
        "required_case_count": len(SCAN_REUSE_COVERAGE_REQUIRED_CASES),
        "required_case_names": SCAN_REUSE_COVERAGE_REQUIRED_CASES,
        "covered_rows": SCAN_REUSE_COVERAGE_ROWS,
        "intentional_non_expansion": SCAN_REUSE_INTENTIONAL_NON_EXPANSION,
        "stop_rule": (
            "Do not add another scan-input / sidecar-state fixture solely to grow counts; add one only when it "
            "reduces a real operator ambiguity in whether a run is refresh-required, clean observation, or activity-looking provenance. "
            "The current matrix explicitly covers empty-sidecar provenance for malformed and invalid-shape reused scan inputs."
        ),
        "evidence_boundary": "This coverage contract is fixture-matrix scope metadata only, not settled ROI, promotion readiness, live profitability, or real-money evidence.",
    }


def require_scanner_boundary_fields(row: dict[str, Any], row_label: str) -> None:
    boundary = row.get("evidence_boundary")
    if row.get("valid_evidence_scope") != LIVE_SCAN_VALID_EVIDENCE_SCOPE:
        raise AssertionError(f"{row_label}: scanner valid_evidence_scope drifted")
    if row.get("evidence_boundary_text") != LIVE_SCAN_BOUNDARY_TEXT:
        raise AssertionError(f"{row_label}: scanner evidence_boundary_text drifted")
    if not isinstance(boundary, dict):
        raise AssertionError(f"{row_label}: missing scanner evidence_boundary metadata")
    for flag in (
        "not_live_paper_trade_ledger",
        "not_settled_roi_evidence",
        "not_live_profitability_evidence",
        "not_promotion_readiness_evidence",
        "not_anchor_change_evidence",
        "not_phase8_promotion_evidence",
        "not_bankroll_guidance",
        "not_real_money_evidence",
    ):
        if boundary.get(flag) is not True:
            raise AssertionError(f"{row_label}: scanner evidence_boundary.{flag} must be true")
    if boundary.get("baq_as_bel_substitution_allowed") is not False:
        raise AssertionError(f"{row_label}: scanner evidence_boundary must reject BAQ-as-BEL substitution")
    required_forward_steps = [
        "paper-trade logger append",
        "settlement template sync",
        "actual result, return, cost, and settled_ts completion",
        "settlement audit or forward-check review before ROI-complete sample gates advance",
    ]
    if boundary.get("stronger_forward_confidence_requires") != required_forward_steps:
        raise AssertionError(f"{row_label}: scanner stronger-forward-confidence requirements drifted")


def build_live_scan_boundary_contract() -> dict[str, Any]:
    payload = load_json(LIVE_SCAN_BOUNDARY_REPORT_JSON)
    checks = {
        check.get("check"): check
        for check in payload.get("child_checks", [])
        if isinstance(check, dict) and isinstance(check.get("check"), str)
    }
    missing_checks = [check for check in LIVE_SCAN_BOUNDARY_CHECKS if check not in checks]
    if payload.get("suite_status") != "pass":
        raise AssertionError("live-scan boundary validator is not passing")
    if missing_checks:
        raise AssertionError(f"live-scan boundary validator missing boundary checks: {missing_checks}")

    scanner_boundary_hit = payload.get("synthetic_scanner_boundary_hit")
    api_access_status = payload.get("synthetic_api_access_scanner_status")
    if not isinstance(scanner_boundary_hit, dict):
        raise AssertionError("live-scan boundary validator missing synthetic_scanner_boundary_hit")
    if not isinstance(api_access_status, dict):
        raise AssertionError("live-scan boundary validator missing synthetic_api_access_scanner_status")
    require_scanner_boundary_fields(scanner_boundary_hit, "synthetic_scanner_boundary_hit")
    require_scanner_boundary_fields(api_access_status, "synthetic_api_access_scanner_status")

    return {
        "source_validator": LIVE_SCAN_VALIDATOR,
        "source_validator_report_json": LIVE_SCAN_BOUNDARY_REPORT_JSON,
        "source_validator_report_md": LIVE_SCAN_BOUNDARY_REPORT_MD,
        "source_script": LIVE_SCAN_SOURCE_SCRIPT,
        "suite_status": payload.get("suite_status"),
        "total_checks": payload.get("total_checks"),
        "valid_evidence_scope": LIVE_SCAN_VALID_EVIDENCE_SCOPE,
        "status_sidecar_fields_pinned": [
            "valid_evidence_scope",
            "evidence_boundary",
            "evidence_boundary_text",
        ],
        "hit_row_fields_pinned": [
            "valid_evidence_scope",
            "evidence_boundary",
            "evidence_boundary_text",
        ],
        "text_output_scope_line_pinned": True,
        "empty_csv_header_fields_pinned": [
            "valid_evidence_scope",
            "evidence_boundary_text",
        ],
        "api_access_status_sidecar_boundary_pinned": True,
        "boundary_checks_pinned": LIVE_SCAN_BOUNDARY_CHECKS,
        "evidence_boundary_text": LIVE_SCAN_BOUNDARY_TEXT,
        "evidence_boundary": (
            "This contract is source-level scanner boundary metadata only. It is not a current-day scanner result, "
            "not a paper-trade ledger append, not settled ROI, not promotion readiness, not live profitability, "
            "not bankroll guidance, and not real-money evidence."
        ),
        "validator_report_fingerprint": file_fingerprint(BASE / LIVE_SCAN_BOUNDARY_REPORT_JSON),
        "source_script_fingerprint": file_fingerprint(BASE / LIVE_SCAN_SOURCE_SCRIPT),
        "validator_script_fingerprint": file_fingerprint(BASE / LIVE_SCAN_VALIDATOR),
    }


def build_payload(
    scorecard_json: str | Path = SCORECARD_JSON,
    current_evidence_json: str | Path = CURRENT_EVIDENCE_JSON,
) -> dict[str, Any]:
    layers: list[dict[str, Any]] = []
    input_fingerprints: dict[str, dict[str, Any]] = {}
    source_file_fingerprints: dict[str, dict[str, dict[str, Any]]] = {}
    scan_reuse_coverage_contract: dict[str, Any] | None = None
    decision_gate_minimums = load_decision_gate_minimums(scorecard_json)
    current_evidence_rebuild_validation_contract = load_rebuild_validation_contract(current_evidence_json)
    live_scan_boundary_contract = build_live_scan_boundary_contract()

    for layer in EXPECTED_LAYERS:
        payload = load_json(layer["report_json"])
        require_expected_layer(layer, payload)
        if layer["label"] == "paper_trade_pipeline":
            scan_reuse_coverage_contract = build_scan_reuse_coverage_contract(payload)
        report_path = BASE / layer["report_json"]
        input_fingerprints[layer["label"]] = file_fingerprint(report_path)
        source_file_fingerprints[layer["label"]] = {
            "source_script": file_fingerprint(BASE / layer["source_script"]),
            "validator": file_fingerprint(BASE / layer["validator"]),
        }
        child_checks = payload.get("child_checks", [])
        layers.append(
            {
                "label": layer["label"],
                "stage": layer["stage"],
                "source_script": layer["source_script"],
                "validator": layer["validator"],
                "report_json": layer["report_json"],
                "report_md": layer["report_md"],
                "suite_status": payload.get("suite_status"),
                "total_fixture_scenarios": payload.get("total_fixture_scenarios"),
                "total_checks": payload.get("total_checks"),
                "check_count": payload.get("check_count"),
                "child_guardrail_check_count": payload.get("child_check_count"),
                "guardrail_checks": child_checks,
                "current_read": payload.get("summary", {}).get("current_read", ""),
                "plain_role": layer["plain_role"],
            }
        )

    total_fixture_scenarios = sum(int(layer["total_fixture_scenarios"]) for layer in layers)
    total_direct_checks = sum(int(layer["total_checks"]) for layer in layers)
    total_guardrails = sum(int(layer["child_guardrail_check_count"]) for layer in layers)
    matrix_tooling_fingerprints = {
        "generator": file_fingerprint(BASE / MATRIX_GENERATOR),
        "validator": file_fingerprint(BASE / MATRIX_VALIDATOR),
    }
    suite_read = (
        f"scan/recommend/size/log source validators are all passing and publish {total_guardrails} machine-readable guardrails "
        f"across {total_fixture_scenarios} fixture scenarios, fingerprint the summarized validator JSON artifacts, their source/validator scripts, and the matrix generator/validator tooling, and document how "
        "operator/project parent rollups should preserve `auxiliary_source_chain_matrix` with parent-side matrix-payload rebuild parity as readiness-only propagation "
        "metadata rather than flattening the chain into a generic green pass; it also publishes the current hierarchy boundary "
        "that keeps OP_DURABLE_K7 as anchor, CD_CORE_K8 as the primary OP/CD paper-basket companion, and OP_REFINED_K7 in shadow/watch, "
        "and carries the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL real-money prerequisite plus the current-evidence rebuild route "
        "through settlement audit -> current bridge -> bridge validator before CURRENT_EVIDENCE_SUMMARY totals are quoted; it exposes exact "
        f"valid_evidence_scope={MATRIX_VALID_EVIDENCE_SCOPE} as matrix-scope metadata only; it also pins the direct live-scanner "
        "source-boundary fields for status sidecars, scanner hit rows, copied text output, and empty saved-CSV headers as paper-alert metadata only; use this matrix to audit paper-trade "
        "source-chain readiness and failure-mode meaning, not to infer settled ROI, promotion readiness, or "
        "live/real-money profitability"
    )

    return {
        "suite_status": "pass",
        "artifact_status": "pass",
        "valid_evidence_scope": MATRIX_VALID_EVIDENCE_SCOPE,
        "source_scope": MATRIX_SOURCE_SCOPE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "evidence_boundary_metadata": build_evidence_boundary_metadata(decision_gate_minimums),
        "current_hierarchy_boundary": CURRENT_HIERARCHY_BOUNDARY,
        "decision_gate_minimums": decision_gate_minimums,
        "current_evidence_rebuild_validation_contract": current_evidence_rebuild_validation_contract,
        "live_scan_boundary_contract": live_scan_boundary_contract,
        "input_fingerprints": input_fingerprints,
        "source_file_fingerprints": source_file_fingerprints,
        "matrix_tooling_fingerprints": matrix_tooling_fingerprints,
        "total_layers": len(layers),
        "total_fixture_scenarios": total_fixture_scenarios,
        "total_source_validator_checks": total_direct_checks,
        "total_guardrail_checks": total_guardrails,
        "layers": layers,
        "scan_reuse_coverage_contract": scan_reuse_coverage_contract,
        "parent_rollup_propagation": {
            "boundary": PARENT_PROPAGATION_BOUNDARY,
            "rollups": PARENT_ROLLUP_PROPAGATION,
        },
        "summary": {
            "suite_read": suite_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "output_md": str(OUT_MD.relative_to(BASE)),
            "output_json": str(OUT_JSON.relative_to(BASE)),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    evidence_boundary = payload["evidence_boundary_metadata"]
    lines = [
        "# Paper-Trade Source Chain Guardrails",
        "",
        "This is a compact read of the direct source-layer validators for the paper-trade path.",
        "",
        "## Evidence Boundary",
        "",
        payload["evidence_boundary"],
        "",
        "Machine-readable boundary highlights:",
        "",
        f"- Artifact role: `{evidence_boundary['artifact_role']}`.",
        f"- `valid_evidence_scope={payload['valid_evidence_scope']}`.",
        f"- Valid use: {evidence_boundary['valid_use']}.",
        f"- Decision-gate source: `{evidence_boundary['decision_gate_source']}` `{evidence_boundary['decision_gate_source_path']}`.",
        (
            "- Source-driven gates carried here: "
            f"anchor displacement `{evidence_boundary['anchor_displacement_min_roi_complete_settled_observations']}`, "
            f"Phase 8 promotion review `{evidence_boundary['phase8_promotion_review_min_roi_complete_settled_observations']}`, "
            f"real-money discussion `{evidence_boundary['real_money_discussion_min_total_settled_observations_with_usable_roi']}`, "
            f"no BAQ-as-BEL prerequisite `{evidence_boundary['real_money_no_baq_as_bel_required']}`."
        ),
        (
            "- Not evidence for settled ROI, live profitability, promotion readiness, anchor change, companion change, "
            "paper-scope change, odds-only XGBoost reopening, BAQ/BEL substitution, or real-money profitability."
        ),
        "",
        "## Current Hierarchy Boundary",
        "",
        f"- `{payload['current_hierarchy_boundary']['anchor']}` remains the safest current OP anchor.",
        f"- `{payload['current_hierarchy_boundary']['primary_paper_basket_companion']}` remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion.",
        f"- `{payload['current_hierarchy_boundary']['same_family_shadow_watch']}` remains the closest same-family shadow/watch challenger.",
        "- BAQ is not BEL.",
        "- Source-chain readiness and validator cleanliness are not settled ROI, live-profitability evidence, promotion readiness, anchor-change evidence, or real-money evidence.",
        "",
        "## Decision-Gate Source",
        "",
        f"- Source: `{payload['decision_gate_minimums']['source_path']}` `decision_gate_minimums`.",
        f"- Anchor displacement: `{payload['decision_gate_minimums']['anchor_displacement_min']}` ROI-complete {payload['decision_gate_minimums']['anchor_displacement_scope']}.",
        f"- Phase 8 promotion review: `{payload['decision_gate_minimums']['phase8_promotion_review_min']}` ROI-complete {payload['decision_gate_minimums']['phase8_promotion_review_scope']}.",
        f"- Real-money discussion: `{payload['decision_gate_minimums']['real_money_discussion_min']}` total settled observations with usable ROI.",
        f"- Real-money prerequisites: {'; '.join(payload['decision_gate_minimums']['real_money_discussion_also_requires'])}.",
        f"- Evidence boundary: {payload['decision_gate_minimums']['evidence_boundary']}",
        "",
        "## Current-Evidence Rebuild Route",
        "",
        (
            f"- Source: `{payload['current_evidence_rebuild_validation_contract']['source']}` "
            "`rebuild_validation_contract`."
        ),
        (
            "- Required order after scorecard/rules/signals/settlement-ledger source-byte changes: "
            f"`{'` -> `'.join(payload['current_evidence_rebuild_validation_contract']['upstream_refresh_commands'])}`."
        ),
        "- Use before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes.",
        (
            "- Evidence boundary: this route is provenance/rebuild metadata only, not settled ROI, "
            "promotion readiness, live profitability, bankroll guidance, or real-money evidence."
        ),
        "",
        "## Source-Layer Matrix",
        "",
        "| Stage | Source | Direct validator | Fixture checks | Guardrails | What it protects |",
        "|---|---|---|---:|---:|---|",
    ]
    for layer in payload["layers"]:
        lines.append(
            f"| {layer['stage']} | `{layer['source_script']}` | `{layer['validator']}` | "
            f"{layer['total_checks']} | {layer['child_guardrail_check_count']} | {layer['plain_role']} |"
        )

    scan_reuse = payload["scan_reuse_coverage_contract"]
    lines.extend(
        [
            "",
            "## Scan Reuse Coverage",
            "",
            scan_reuse["policy"],
            "",
            "| Scan input state | Sidecar states pinned | Controlling result | Operator meaning |",
            "|---|---|---|---|",
        ]
    )
    for row in scan_reuse["covered_rows"]:
        lines.append(
            f"| `{row['scan_input_state']}` | {row['sidecar_states_pinned']} | "
            f"`{row['controlling_result']}` | {row['operator_meaning']} |"
        )
    lines.extend(
        [
            "",
            f"- Required scan-reuse fixture cases pinned here: {scan_reuse['required_case_count']}",
            f"- Stop rule: {scan_reuse['stop_rule']}",
            f"- Evidence boundary: {scan_reuse['evidence_boundary']}",
            "",
            "Intentional non-expansion cases:",
            "",
        ]
    )
    if scan_reuse["intentional_non_expansion"]:
        for row in scan_reuse["intentional_non_expansion"]:
            lines.append(f"- `{row['candidate_case']}` - {row['reason']}")
    else:
        lines.append("- None currently; every scan-input / sidecar-state ambiguity named in this matrix has an explicit fixture.")

    live_scan = payload["live_scan_boundary_contract"]
    lines.extend(
        [
            "",
            "## Live Scanner Boundary Contract",
            "",
            (
                "This auxiliary contract ties the compact source-chain matrix back to the direct live-scan "
                "targeting / limited-coverage validator without counting scanner fixture checks as settled ROI."
            ),
            "",
            f"- Source script: `{live_scan['source_script']}`.",
            f"- Direct validator: `{live_scan['source_validator']}`.",
            f"- Validator JSON: `{live_scan['source_validator_report_json']}`.",
            f"- `valid_evidence_scope={live_scan['valid_evidence_scope']}`.",
            f"- Status-sidecar fields pinned: `{', '.join(live_scan['status_sidecar_fields_pinned'])}`.",
            f"- Scanner-hit row fields pinned: `{', '.join(live_scan['hit_row_fields_pinned'])}`.",
            f"- Text output scope line pinned: `{live_scan['text_output_scope_line_pinned']}`.",
            f"- Empty CSV header fields pinned: `{', '.join(live_scan['empty_csv_header_fields_pinned'])}`.",
            f"- API-access sidecar boundary pinned: `{live_scan['api_access_status_sidecar_boundary_pinned']}`.",
            f"- Boundary checks pinned: `{', '.join(live_scan['boundary_checks_pinned'])}`.",
            f"- Evidence boundary text: {live_scan['evidence_boundary_text']}",
            f"- Evidence boundary: {live_scan['evidence_boundary']}",
            "",
            "| Scanner boundary source | Bytes | SHA-256 |",
            "|---|---:|---|",
            (
                f"| `{live_scan['validator_report_fingerprint']['path']}` | "
                f"{live_scan['validator_report_fingerprint']['bytes']} | "
                f"`{live_scan['validator_report_fingerprint']['sha256']}` |"
            ),
            (
                f"| `{live_scan['source_script_fingerprint']['path']}` | "
                f"{live_scan['source_script_fingerprint']['bytes']} | "
                f"`{live_scan['source_script_fingerprint']['sha256']}` |"
            ),
            (
                f"| `{live_scan['validator_script_fingerprint']['path']}` | "
                f"{live_scan['validator_script_fingerprint']['bytes']} | "
                f"`{live_scan['validator_script_fingerprint']['sha256']}` |"
            ),
        ]
    )

    lines.extend(
        [
            "",
            "## Guardrail Inventory",
            "",
        ]
    )
    for layer in payload["layers"]:
        lines.append(f"### {layer['stage']} — `{layer['label']}`")
        lines.append("")
        for check in layer["guardrail_checks"]:
            lines.append(f"- `{check['check']}` — {check['detail']}")
        lines.append("")

    lines.extend(
        [
            "## Source Fingerprints",
            "",
            "These fingerprints identify the exact validator JSON artifacts summarized here. They prove source-artifact provenance only, not performance.",
            "",
            "| Validator JSON | Bytes | SHA-256 |",
            "|---|---:|---|",
        ]
    )
    for fp in payload["input_fingerprints"].values():
        lines.append(f"| `{fp['path']}` | {fp['bytes']} | `{fp['sha256']}` |")

    lines.extend(
        [
            "",
            "## Source Code Fingerprints",
            "",
            "These fingerprints identify the exact source and validator scripts behind each summarized layer. They prove code/artifact provenance only, not performance.",
            "",
            "| Layer | Source script | Bytes | SHA-256 | Validator script | Bytes | SHA-256 |",
            "|---|---|---:|---|---|---:|---|",
        ]
    )
    for label, fingerprints in payload["source_file_fingerprints"].items():
        source_fp = fingerprints["source_script"]
        validator_fp = fingerprints["validator"]
        lines.append(
            f"| `{label}` | `{source_fp['path']}` | {source_fp['bytes']} | `{source_fp['sha256']}` | "
            f"`{validator_fp['path']}` | {validator_fp['bytes']} | `{validator_fp['sha256']}` |"
        )

    tooling = payload["matrix_tooling_fingerprints"]
    lines.extend(
        [
            "",
            "## Matrix Tooling Fingerprints",
            "",
            "These fingerprints identify the exact generator and direct validator that build and validate this matrix. They prove matrix-tooling provenance only, not performance.",
            "",
            "| Tooling role | Path | Bytes | SHA-256 |",
            "|---|---|---:|---|",
            f"| generator | `{tooling['generator']['path']}` | {tooling['generator']['bytes']} | `{tooling['generator']['sha256']}` |",
            f"| validator | `{tooling['validator']['path']}` | {tooling['validator']['bytes']} | `{tooling['validator']['sha256']}` |",
        ]
    )

    lines.extend(
        [
            "",
            "## Parent Rollup Propagation",
            "",
            "Use these parent checks only after the direct source-chain matrix is fresh. They preserve the scan -> recommend -> size -> log audit path in broader surfaces rather than creating new evidence.",
            "",
            payload["parent_rollup_propagation"]["boundary"],
            "",
            "| Parent surface | Validator | Embedded key | Recommended check | What it preserves |",
            "|---|---|---|---|---|",
        ]
    )
    for rollup in payload["parent_rollup_propagation"]["rollups"]:
        lines.append(
            f"| {rollup['surface']} | `{rollup['validator']}` | `{rollup['embedded_key']}` | "
            f"`{rollup['recommended_command']}` | {rollup['preserves']}; {rollup['use_only_after']} |"
        )

    lines.extend(
        [
            "",
            "## Current Read",
            "",
            f"- {payload['summary']['suite_read']}",
            "",
            "## Rebuild",
            "",
            f"- Working directory: `{payload['rebuild']['workdir']}`",
            f"- Command: `{payload['rebuild']['command']}`",
            f"- Markdown: `{payload['rebuild']['output_md']}`",
            f"- JSON: `{payload['rebuild']['output_json']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    payload = build_payload(args.scorecard_json, args.current_evidence_json)
    md_path = args.output_md if args.output_md.is_absolute() else BASE / args.output_md
    json_path = args.output_json if args.output_json.is_absolute() else BASE / args.output_json
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload["rebuild"]["output_md"] = str(md_path.relative_to(BASE)) if md_path.is_relative_to(BASE) else str(md_path)
    payload["rebuild"]["output_json"] = str(json_path.relative_to(BASE)) if json_path.is_relative_to(BASE) else str(json_path)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(
        f"PASS source-chain guardrails: {payload['total_layers']} layers, "
        f"{payload['total_fixture_scenarios']} fixture scenarios, "
        f"{payload['total_guardrail_checks']} guardrails"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
