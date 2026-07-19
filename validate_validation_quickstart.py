#!/usr/bin/env python3
"""
Validation for VALIDATION_QUICKSTART.md.

Purpose:
- keep the validation runbook aligned with the current suite hierarchy
- stop the quickstart doc from drifting away from the real broader operator-suite route, direct source-layer rerun map, and documented output paths
- pin the dated-report / legacy-alias policy so the dated HTML trust anchor and dated PDF derivative export stay preferred over the undated HTML/PDF/DOCX, quick-start PDF, and historical-prompt DOCX legacy aliases
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

BASE = Path(__file__).resolve().parent
DOC = BASE / "VALIDATION_QUICKSTART.md"
OUT_DIR = BASE / "out" / "status_validation" / "validation_quickstart"
MD_PATH = OUT_DIR / "validation_quickstart_validation.md"
JSON_PATH = OUT_DIR / "validation_quickstart_validation.json"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
MATRIX_JSON = BASE / "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json"
REBUILD_COMMAND = "python3 validate_validation_quickstart.py"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
CI_ONLY_SOURCE = "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7"
VALID_EVIDENCE_SCOPE = "validation_quickstart_navigation_contract_only"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "validation quickstart / validator-routing runbook",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "VALIDATION_QUICKSTART.md",
        "documented validator command map",
        "documented validation artifact output paths",
        "parent-rollup reuse shortcut guardrails",
        "disk-space preflight for temp-heavy fixture validators",
        "forward_evidence_scorecard.json decision_gate_minimums used by quickstart gate wording",
        "current_evidence_summary.json scorecard_ci_only_promotion_check used by quickstart current-evidence route wording",
        "current_evidence_summary.json operator_read_gate used by quickstart current-evidence route wording",
        "current_evidence_summary.json scorecard_audit_route used by quickstart current-evidence route wording",
        "current_evidence_summary.json rebuild_validation_contract used by quickstart current-bridge rebuild-order wording",
    ],
    "valid_use": "validator-selection, read-order, output-path, and parent-rollup reuse-guardrail alignment audit",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "quickstart_validator_passes_are_navigation_metadata_only": True,
    "stronger_forward_confidence_requires": [
        "qualifying live paper signals",
        "ROI-complete settled paper rows",
        "settlement-quality checks",
        "other real forward observations",
    ],
    "non_goals": [
        "do not use validator-routing cleanliness as settled ROI",
        "do not use quickstart coverage as live profitability evidence",
        "do not promote OP_REFINED_K7 or Phase 8 from navigation validation cleanliness",
        "do not reopen current odds-only XGBoost from navigation validation cleanliness",
        "do not substitute BAQ for BEL",
        "do not treat documented validator output paths as real-money evidence",
    ],
}


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    return {"check": name, "status": "pass" if condition else "fail", "detail": detail}


def require_contains(text: str, snippet: str, name: str, detail: str) -> dict[str, Any]:
    return require(snippet in text, name, detail)


def require_paths_exist(paths: list[str], name: str, detail: str) -> dict[str, Any]:
    missing = [path for path in paths if not (BASE / path).exists()]
    status = "pass" if not missing else "fail"
    suffix = detail if not missing else f"{detail}; missing: {', '.join(missing)}"
    return {"check": name, "status": status, "detail": suffix}


def require_output_paths_exist(paths: list[str], name: str, detail: str) -> dict[str, Any]:
    missing = [path for path in paths if not (BASE / path).exists()]
    status = "pass" if not missing else "fail"
    suffix = detail if not missing else f"{detail}; missing: {', '.join(missing)}"
    return {"check": name, "status": status, "detail": suffix}


def require_positive_non_bool_int(value: Any, *, source_name: str, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, source_name: str, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise AssertionError(f"{source_name} {field_name} must be a list of non-empty strings")
    return value


def scorecard_gate_context(scorecard_json_path: Path = SCORECARD_JSON) -> dict[str, Any]:
    source_path = Path(scorecard_json_path)
    source_name = source_path.name
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    gates = payload.get("decision_gate_minimums")
    if not isinstance(gates, dict):
        raise AssertionError(f"{source_name} is missing decision_gate_minimums")

    anchor_gate = gates.get("anchor_displacement")
    phase8_gate = gates.get("phase8_promotion_review")
    real_money_gate = gates.get("real_money_discussion")
    if not isinstance(anchor_gate, dict) or not isinstance(phase8_gate, dict) or not isinstance(real_money_gate, dict):
        raise AssertionError(f"{source_name} decision_gate_minimums is missing a required gate")

    anchor_min = require_positive_non_bool_int(
        anchor_gate.get("min_roi_complete_settled_observations"),
        source_name=source_name,
        field_name="decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
    )
    phase8_min = require_positive_non_bool_int(
        phase8_gate.get("min_roi_complete_settled_observations"),
        source_name=source_name,
        field_name="decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
    )
    real_money_min = require_positive_non_bool_int(
        real_money_gate.get("min_total_settled_observations_with_usable_roi"),
        source_name=source_name,
        field_name="decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
    )
    real_money_requirements = require_string_list(
        real_money_gate.get("also_requires"),
        source_name=source_name,
        field_name="decision_gate_minimums.real_money_discussion.also_requires",
    )
    if NO_BAQ_AS_BEL_PREREQUISITE not in real_money_requirements:
        raise AssertionError(
            f"{source_name} decision_gate_minimums.real_money_discussion.also_requires "
            f"must include {NO_BAQ_AS_BEL_PREREQUISITE}"
        )
    source_snippet = (
        "When this quickstart names the 30 / 20 / 100 paper-observation floors, treat "
        f"`{SCORECARD_JSON.name}` `decision_gate_minimums` as the source: "
        f"`anchor_displacement={anchor_min}`, `phase8_promotion_review={phase8_min}`, "
        f"and `real_money_discussion={real_money_min}`.\n"
        "These are future ROI-complete paper-observation floors only; they do not mean any gate has cleared, "
        "do not promote Phase 8, do not replace `OP_DURABLE_K7`, and do not authorize real-money betting."
    )
    return {
        "source": SCORECARD_JSON.name,
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_no_baq_as_bel_required": True,
        "source_snippet": source_snippet,
    }


def source_chain_guardrail_context() -> dict[str, Any]:
    payload = json.loads(MATRIX_JSON.read_text(encoding="utf-8"))
    total_guardrail_checks = payload.get("total_guardrail_checks")
    total_fixture_scenarios = payload.get("total_fixture_scenarios")
    if isinstance(total_guardrail_checks, bool) or not isinstance(total_guardrail_checks, int):
        raise AssertionError(f"{MATRIX_JSON.name} is missing integer total_guardrail_checks")
    if isinstance(total_fixture_scenarios, bool) or not isinstance(total_fixture_scenarios, int):
        raise AssertionError(f"{MATRIX_JSON.name} is missing integer total_fixture_scenarios")
    return {
        "source": MATRIX_JSON.name,
        "total_guardrail_checks": total_guardrail_checks,
        "total_fixture_scenarios": total_fixture_scenarios,
    }


def scorecard_ci_only_context(
    scorecard_json_path: Path = SCORECARD_JSON,
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> dict[str, Any]:
    scorecard_payload = json.loads(Path(scorecard_json_path).read_text(encoding="utf-8"))
    current_evidence_payload = json.loads(Path(current_evidence_json_path).read_text(encoding="utf-8"))
    source_diagnostic = scorecard_payload.get("ci_only_promotion_diagnostics", {}).get("OP_REFINED_K7")
    current_check = current_evidence_payload.get("scorecard_ci_only_promotion_check")
    if not isinstance(source_diagnostic, dict):
        raise AssertionError(f"{Path(scorecard_json_path).name} is missing ci_only_promotion_diagnostics.OP_REFINED_K7")
    if not isinstance(current_check, dict):
        raise AssertionError(f"{Path(current_evidence_json_path).name} is missing scorecard_ci_only_promotion_check")
    if current_check.get("source") != CI_ONLY_SOURCE:
        raise AssertionError(
            f"{Path(current_evidence_json_path).name} scorecard_ci_only_promotion_check.source must be {CI_ONLY_SOURCE}"
        )
    if current_check.get("scorecard_ci_only_promotion_diagnostic") != source_diagnostic:
        raise AssertionError(
            f"{Path(current_evidence_json_path).name} scorecard_ci_only_promotion_check must copy the scorecard diagnostic exactly"
        )
    if current_check.get("ci_only_promotion_allowed") is not False:
        raise AssertionError(
            f"{Path(current_evidence_json_path).name} scorecard_ci_only_promotion_check.ci_only_promotion_allowed must be false"
        )
    return {
        "source": CI_ONLY_SOURCE,
        "candidate_rule_id": current_check.get("candidate_rule_id"),
        "current_anchor_rule_id": current_check.get("current_anchor_rule_id"),
        "ci_only_promotion_allowed": current_check.get("ci_only_promotion_allowed"),
        "current_matches_scorecard_diagnostic": True,
        "read": current_check.get("read"),
    }


def operator_read_gate_context(current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    payload = json.loads(Path(current_evidence_json_path).read_text(encoding="utf-8"))
    gate = payload.get("operator_read_gate")
    if not isinstance(gate, dict):
        raise AssertionError(f"{Path(current_evidence_json_path).name} is missing operator_read_gate")
    if gate != payload.get("current_paper_status", {}).get("operator_read_gate"):
        raise AssertionError(
            f"{Path(current_evidence_json_path).name} operator_read_gate must match current_paper_status.operator_read_gate"
        )
    if gate.get("gate_status") not in {
        "refresh_required_before_evidence_read",
        "current_operator_routing_context_only",
    }:
        raise AssertionError(
            f"{Path(current_evidence_json_path).name} operator_read_gate.gate_status must be a known operator-read state"
        )
    if gate.get("valid_use") != "operator instruction/evidence-read gating only":
        raise AssertionError(f"{Path(current_evidence_json_path).name} operator_read_gate.valid_use drifted")
    if not isinstance(gate.get("recommended_command"), str) or not gate.get("recommended_command"):
        raise AssertionError(
            f"{Path(current_evidence_json_path).name} operator_read_gate must publish a recommended command"
        )
    if not isinstance(gate.get("requires_refresh_before_evidence_read"), bool):
        raise AssertionError(
            f"{Path(current_evidence_json_path).name} operator_read_gate.requires_refresh_before_evidence_read must be boolean"
        )
    for flag in (
        "has_api_access_failure_context",
        "has_scanner_failure_boundary",
        "has_stale_cache_fallback_context",
    ):
        if not isinstance(gate.get(flag), bool):
            raise AssertionError(f"{Path(current_evidence_json_path).name} operator_read_gate.{flag} must be boolean")
    for flag in (
        "not_forward_performance_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_real_money_evidence",
    ):
        if gate.get(flag) is not True:
            raise AssertionError(f"{Path(current_evidence_json_path).name} operator_read_gate.{flag} must be true")
    for flag in (
        "current_top_card_counts_as_no_target_evidence",
        "current_top_card_counts_as_clean_empty_evidence",
        "current_top_card_counts_as_bet_readiness_evidence",
        "current_top_card_counts_as_settled_roi_evidence",
    ):
        if gate.get(flag) is not False:
            raise AssertionError(f"{Path(current_evidence_json_path).name} operator_read_gate.{flag} must be false")
    read = str(gate.get("read") or "").strip()
    for phrase in (
        str(gate.get("recommended_command") or ""),
        "settled ROI",
        "real-money",
    ):
        if phrase not in read:
            raise AssertionError(f"{Path(current_evidence_json_path).name} operator_read_gate.read missing {phrase!r}")
    return {
        "source": Path(current_evidence_json_path).name,
        "source_path": "operator_read_gate",
        "gate_status": gate.get("gate_status"),
        "valid_use": gate.get("valid_use"),
        "requires_refresh_before_evidence_read": gate.get("requires_refresh_before_evidence_read"),
        "recommended_command": gate.get("recommended_command"),
        "has_api_access_failure_context": gate.get("has_api_access_failure_context"),
        "has_scanner_failure_boundary": gate.get("has_scanner_failure_boundary"),
        "has_stale_cache_fallback_context": gate.get("has_stale_cache_fallback_context"),
        "current_top_card_counts_as_no_target_evidence": gate.get("current_top_card_counts_as_no_target_evidence"),
        "current_top_card_counts_as_clean_empty_evidence": gate.get("current_top_card_counts_as_clean_empty_evidence"),
        "current_top_card_counts_as_bet_readiness_evidence": gate.get("current_top_card_counts_as_bet_readiness_evidence"),
        "current_top_card_counts_as_settled_roi_evidence": gate.get("current_top_card_counts_as_settled_roi_evidence"),
        "not_forward_performance_evidence": gate.get("not_forward_performance_evidence"),
        "not_promotion_readiness_evidence": gate.get("not_promotion_readiness_evidence"),
        "not_live_profitability_evidence": gate.get("not_live_profitability_evidence"),
        "not_real_money_evidence": gate.get("not_real_money_evidence"),
        "read": read,
    }


def scorecard_audit_route_context(current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    payload = json.loads(Path(current_evidence_json_path).read_text(encoding="utf-8"))
    route = payload.get("scorecard_audit_route")
    if not isinstance(route, dict):
        raise AssertionError(f"{Path(current_evidence_json_path).name} is missing scorecard_audit_route")
    expected_snapshot = {
        "anchor_displacement_min_roi_complete_settled_observations": 30,
        "phase8_promotion_review_min_roi_complete_settled_observations": 20,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": 100,
        "real_money_no_baq_as_bel_required": True,
    }
    expected_fields = {
        "markdown_path": "SCORECARD_RANKING_CONTRACT_AUDIT.md",
        "json_path": "scorecard_ranking_contract_audit.json",
        "validator_command": "python3 validate_scorecard_ranking_contract_audit.py",
        "gate_floor_source": "forward_evidence_scorecard.json:decision_gate_minimums",
        "valid_use": "navigation route for scorecard gate/ranking/CI-only/timezone/no-BAQ synchronization checks",
    }
    for key, expected in expected_fields.items():
        if route.get(key) != expected:
            raise AssertionError(f"{Path(current_evidence_json_path).name} scorecard_audit_route.{key} drifted")
    if route.get("gate_floor_snapshot") != expected_snapshot:
        raise AssertionError(
            f"{Path(current_evidence_json_path).name} scorecard_audit_route.gate_floor_snapshot drifted"
        )
    if route.get("artifacts_present") is not True:
        raise AssertionError(
            f"{Path(current_evidence_json_path).name} scorecard_audit_route.artifacts_present must be true"
        )
    for flag in (
        "not_forward_performance_evidence",
        "not_settled_roi_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_bankroll_guidance",
        "not_real_money_evidence",
    ):
        if route.get(flag) is not True:
            raise AssertionError(f"{Path(current_evidence_json_path).name} scorecard_audit_route.{flag} must be true")
    route_read = str(route.get("route_read") or "").strip()
    for phrase in (
        "copied 30/20/100 gate floors",
        "tier-first ranking",
        "OP_REFINED CI-only support context",
        "generated-at timezone provenance",
        "no-BAQ-as-BEL prerequisite drift",
    ):
        if phrase not in route_read:
            raise AssertionError(
                f"{Path(current_evidence_json_path).name} scorecard_audit_route.route_read missing {phrase!r}"
            )
    return {
        "source": Path(current_evidence_json_path).name,
        "source_path": "scorecard_audit_route",
        "markdown_path": route.get("markdown_path"),
        "json_path": route.get("json_path"),
        "validator_command": route.get("validator_command"),
        "gate_floor_source": route.get("gate_floor_source"),
        "gate_floor_snapshot": route.get("gate_floor_snapshot"),
        "artifacts_present": route.get("artifacts_present"),
        "valid_use": route.get("valid_use"),
        "not_forward_performance_evidence": route.get("not_forward_performance_evidence"),
        "not_settled_roi_evidence": route.get("not_settled_roi_evidence"),
        "not_promotion_readiness_evidence": route.get("not_promotion_readiness_evidence"),
        "not_live_profitability_evidence": route.get("not_live_profitability_evidence"),
        "not_bankroll_guidance": route.get("not_bankroll_guidance"),
        "not_real_money_evidence": route.get("not_real_money_evidence"),
        "route_read": route_read,
    }


def current_bridge_rebuild_contract_context(current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    payload = json.loads(Path(current_evidence_json_path).read_text(encoding="utf-8"))
    contract = payload.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise AssertionError(f"{Path(current_evidence_json_path).name} is missing rebuild_validation_contract")
    expected_order = [
        {
            "order": 1,
            "command": "python3 paper_trade_settlement_audit.py",
            "reason": (
                "refresh settlement-audit source fingerprints after scorecard, rules, signals, or "
                "settlement-ledger byte changes"
            ),
        },
        {
            "order": 2,
            "command": "python3 current_evidence_summary.py",
            "reason": "rebuild the bridge from the refreshed scorecard, right-now card, settlement audit, and CSV recompute",
        },
        {
            "order": 3,
            "command": "python3 validate_current_evidence_summary.py",
            "reason": "confirm source fingerprint parity, gate-source alignment, and non-evidence boundaries before quoting the bridge",
        },
    ]
    expected_fields = {
        "rebuild_command": "python3 current_evidence_summary.py",
        "prerequisite_rebuild_command": "python3 paper_trade_settlement_audit.py",
        "direct_validation_command": "python3 validate_current_evidence_summary.py",
        "upstream_refresh_order_valid_use": (
            "reproducible rebuild order for current bridge provenance after scorecard/rules/ledger byte changes"
        ),
    }
    for key, expected in expected_fields.items():
        if contract.get(key) != expected:
            raise AssertionError(f"{Path(current_evidence_json_path).name} rebuild_validation_contract.{key} drifted")
    if contract.get("upstream_refresh_order") != expected_order:
        raise AssertionError(f"{Path(current_evidence_json_path).name} rebuild_validation_contract.upstream_refresh_order drifted")
    for flag in (
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
        "upstream_refresh_order_is_provenance_metadata_only",
        "green_checks_are_reproducibility_metadata_only",
        "requires_source_consistency_before_quoting_current_totals",
        "not_settled_roi_or_real_money_evidence",
    ):
        if contract.get(flag) is not True:
            raise AssertionError(f"{Path(current_evidence_json_path).name} rebuild_validation_contract.{flag} must be true")
    return {
        "source": Path(current_evidence_json_path).name,
        "source_path": "rebuild_validation_contract",
        "rebuild_command": contract.get("rebuild_command"),
        "prerequisite_rebuild_command": contract.get("prerequisite_rebuild_command"),
        "direct_validation_command": contract.get("direct_validation_command"),
        "upstream_refresh_order": contract.get("upstream_refresh_order"),
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": contract.get(
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
        ),
        "upstream_refresh_order_valid_use": contract.get("upstream_refresh_order_valid_use"),
        "upstream_refresh_order_is_provenance_metadata_only": contract.get(
            "upstream_refresh_order_is_provenance_metadata_only"
        ),
        "not_settled_roi_or_real_money_evidence": contract.get("not_settled_roi_or_real_money_evidence"),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the validation quickstart runbook")
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--current-evidence-json", type=Path, default=CURRENT_EVIDENCE_JSON)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def scorecard_gate_cli_contract_checks(
    scorecard_json_path: Path = SCORECARD_JSON,
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="validation_quickstart_scorecard_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(scorecard_json_path).read_text(encoding="utf-8"))
        scorecard_path = tmp_root / "forward_evidence_scorecard.json"
        bad_out_dir = tmp_root / "nested" / "validation_quickstart_validation"

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
                "--current-evidence-json",
                str(current_evidence_json_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations must be a positive non-boolean integer" in proc.stderr,
                "scorecard_boolean_floor_fails_before_artifacts",
                "validate_validation_quickstart.py rejects a boolean scorecard anchor-displacement gate before creating nested output directories or partial validation artifacts",
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
                "--current-evidence-json",
                str(current_evidence_json_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer" in proc.stderr,
                "scorecard_nonpositive_phase8_floor_fails_before_artifacts",
                "validate_validation_quickstart.py rejects a non-positive Phase 8 promotion-review scorecard gate before creating nested output directories or partial validation artifacts",
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
                "--current-evidence-json",
                str(current_evidence_json_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer" in proc.stderr,
                "scorecard_nonpositive_real_money_floor_fails_before_artifacts",
                "validate_validation_quickstart.py rejects a non-positive real-money discussion scorecard gate before creating nested output directories or partial validation artifacts",
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
                "--current-evidence-json",
                str(current_evidence_json_path),
                "--out-dir",
                str(bad_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not bad_out_dir.exists()
                and "decision_gate_minimums.real_money_discussion.also_requires must include no BAQ-as-BEL substitution" in proc.stderr,
                "scorecard_missing_no_baq_fails_before_artifacts",
                "validate_validation_quickstart.py rejects a scorecard real-money gate that drops the no-BAQ-as-BEL prerequisite before creating nested output directories or partial validation artifacts",
            )
        )

    return checks


def current_bridge_rebuild_cli_contract_checks(
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="validation_quickstart_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json_path).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "validation_quickstart_validation"
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
                and "current_evidence_summary.json is missing rebuild_validation_contract" in proc.stderr,
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "validate_validation_quickstart.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial validation artifacts",
            )
        )

        weakened_contract_out_dir = tmp_root / "weakened" / "validation_quickstart_validation"
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
                and "current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true"
                in proc.stderr,
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "validate_validation_quickstart.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial validation artifacts",
            )
        )

    return checks


def build_checks(
    text: str,
    scorecard_gates: dict[str, Any],
    source_chain_context: dict[str, Any],
    ci_only_context: dict[str, Any],
    operator_read_gate: dict[str, Any],
    scorecard_audit_route: dict[str, Any],
    current_bridge_rebuild_contract: dict[str, Any],
) -> list[dict[str, Any]]:
    source_chain_guardrails = source_chain_context["total_guardrail_checks"]
    source_chain_fixtures = source_chain_context["total_fixture_scenarios"]
    return [
        require_contains(
            text,
            "| `VALIDATION_QUICKSTART.md` wording, top-level validation guidance, broader operator-suite route guidance, direct source-layer route guidance, parent-rollup reuse shortcut guardrails, documented output paths, dated-report / legacy-alias policy, or shareable PDF refresh-helper path | `python3 validate_validation_quickstart.py` | the quickstart keeps the current broad-change command, broader operator-suite route, report-surface sweep, direct source-layer routes, reuse guardrails, documented output paths, dated-report / legacy-alias policy, shareable PDF refresh-helper path, and machine-readable evidence boundary for navigation/read-order reproducibility straight without treating quickstart validation as settled ROI, live profitability, promotion readiness, or real-money evidence |",
            "quickstart_row_present",
            "fast chooser includes a dedicated validator row for quickstart wording, broader operator-suite route guidance, direct source-layer route guidance, parent-rollup reuse shortcut guardrails, documented output paths, dated-report / legacy-alias policy drift, shareable PDF refresh-helper routing, and navigation evidence-boundary preservation",
        ),
        require_contains(
            text,
            "| README + long-form report + working-status report + presentation outline + HTML report together | `python3 validate_report_surfaces.py` | the five main human-facing report surfaces stay aligned on the frozen anchor, paper baseline, benchmark-only selector read, shadow-only Phase 8 stance, method-family roles, the dated demo-vs-production framing, and the README-inherited wrapper-leaf source-of-truth note instead of flattening it away, with machine-readable evidence-boundary metadata keeping a green narrative sweep separate from settled ROI, live profitability, promotion readiness, and real-money evidence |",
            "report_surfaces_row_present",
            "fast chooser includes the narrative report-surfaces row and now says that sweep inherits the README landing-page wrapper-leaf source-of-truth note while keeping green narrative validation out of the settled-ROI / live-profitability / promotion-readiness / real-money lane",
        ),
        require_contains(
            text,
            "| A single decision card or its ordering logic | `python3 validate_decision_cards_suite.py` | OP-family, cross-family, portfolio, and method-family decision cards together as a frozen-evidence ordering check rather than new forward proof |",
            "decision_cards_suite_row_present",
            "fast chooser includes the one-command decision-card sweep and now says it is a frozen-evidence ordering check rather than new forward proof",
        ),
        require_contains(
            text,
            "| `OP_FAMILY_DECISION.md` anchor-replacement wording, inherited scorecard ranking contract, scorecard-audit route, current bridge rebuild route, or OP-family promotion logic | `python3 validate_op_family_decision.py` | the focused OP-family card still keeps the saved surfaces, real CLI output, conservative anchor-replacement bar, inherited forward-scorecard `ranking_contract`, `current_evidence_summary.json.rebuild_validation_contract`, and `current_evidence_summary.json.scorecard_audit_route` straight for `OP_DURABLE_K7` versus the current OP challengers so raw OP_REFINED_K7 score cannot become an automatic promotion cue, current totals route through settlement-audit -> current-bridge -> bridge-validator before quoting, and copied gate/ranking/CI-only/timezone/no-BAQ checks route to the dedicated audit as synchronization metadata only |",
            "op_family_row_present",
            "fast chooser includes the dedicated OP-family validator row for anchor-replacement, current-bridge rebuild-route, and scorecard-audit-route questions inside the OP family",
        ),
        require_contains(
            text,
            "| `CROSS_FAMILY_DECISION.md` shortlist wording, inherited scorecard ranking contract, anchor / paper / watch ordering, or current-paper snapshot caveat | `python3 validate_cross_family_decision.py` | the cross-family shortlist still keeps the saved surfaces, real CLI output, current anchor / paper / watch ordering, the inherited forward-scorecard `ranking_contract` semantics that keep raw OP_REFINED_K7 score from becoming an automatic promotion cue, the explicit near-promotion vs observation-only split straight across `OP_DURABLE_K7`, `CD_CORE_K8`, and `OP_REFINED_K7` plus the smaller Phase 8 pockets, and the current-paper snapshot that keeps stale-card refresh routing / CD-only settled rows / source-published settlement-queue state/context out of OP-anchor proof or cross-family promotion evidence |",
            "cross_family_row_present",
            "fast chooser includes the dedicated cross-family shortlist validator row, including the current-paper snapshot caveat route",
        ),
        require_contains(
            text,
            "| `PORTFOLIO_DECISION_CARD.md` paper / shadow / benchmark ordering, inherited scorecard ranking contract, scorecard-audit route, current bridge rebuild route, or portfolio-level posture | `python3 validate_portfolio_decision_card.py` | the top-level portfolio card still keeps the saved surfaces, real CLI output, current PAPER NOW / SHADOW ONLY / BENCHMARK ONLY ordering, inherited forward-scorecard `ranking_contract`, `current_evidence_summary.json.rebuild_validation_contract`, and `current_evidence_summary.json.scorecard_audit_route` straight so raw Score cannot turn a shadow portfolio line into an automatic promotion cue, current totals route through settlement-audit -> current-bridge -> bridge-validator before quoting, and copied gate/ranking/CI-only/timezone/no-BAQ checks route to the dedicated audit |",
            "portfolio_decision_row_present",
            "fast chooser includes the dedicated portfolio decision-card validator row with current-bridge rebuild-route and scorecard-audit-route questions surfaced",
        ),
        require_contains(
            text,
            "| `METHOD_FAMILY_DECISION.md` selective-rule / Harville / XGBoost retirement posture, inherited scorecard ranking contract, scorecard-audit route, or current bridge rebuild route | `python3 validate_method_family_decision_card.py` | the method-family card still keeps the saved surfaces, real CLI output, current selective-rule / Harville / XGBoost ordering, inherited forward-scorecard `ranking_contract`, `current_evidence_summary.json.rebuild_validation_contract`, and `current_evidence_summary.json.scorecard_audit_route` straight while keeping dead-end method families retired, preventing raw OP_REFINED shadow context from becoming an automatic promotion cue, routing current totals through settlement-audit -> current-bridge -> bridge-validator before quoting, and routing copied gate/ranking/CI-only/timezone/no-BAQ checks to the dedicated audit as synchronization metadata only |",
            "method_family_row_present",
            "fast chooser includes the dedicated method-family decision-card validator row with the current-bridge rebuild-route and scorecard-audit route surfaced",
        ),
        require_contains(
            text,
            "| The forward-evidence scorecard ranking, tier-first ranking contract, bootstrap-CI source-note / report-fingerprint provenance, generated-at timezone provenance, machine-readable evidence boundary, machine-readable decision-gate minimums, or its CSV/text/JSON surfaces | `python3 validate_forward_evidence_scorecard.py` | the saved `forward_evidence_scorecard.csv`, `forward_evidence_scorecard.txt`, and `forward_evidence_scorecard.json` surfaces against a fresh rebuild, including the frozen source-scope / non-live-evidence boundary and bootstrap-CI source-note columns carried into CSV rows, the JSON sidecar's machine-readable `evidence_boundary` plus `evidence_boundary_text`, the JSON/text `ranking_contract` that explains rank is tier-first rather than raw-score order, source-scorecard generated-at timezone-label contract plus no-timezone CLI fail-fast coverage, exact source fingerprints for the frozen CSV inputs plus per-rule bootstrap-CI source notes and `PHASE7_REPORT.md` / `PHASE8_REPORT.md` report fingerprints, machine-readable `decision_gate_minimums` for `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100` settled-observation gates, the current anchor / paper / watch / dormant read, and the explicit closest-challenger vs observation-only-pocket shadow triage |\n| `compare_main_approaches` one-screen read, CSV/markdown/JSON bundle, current paper ladder, inherited scorecard ranking contract, method-family evidence-debt checklist, or method-family comparison wording | `python3 validate_compare_main_approaches.py` | the saved CSV, saved markdown, saved JSON sidecar, and real CLI output stay pinned to the frozen 2024-2025 holdout standard, including Cole's one-screen OP/CD core read, `OP_REFINED_K7` shadow-only caution, Harville benchmark-only lane, current odds-only XGBoost research-only lane, BEL-not-BAQ caution, the inherited forward-scorecard `ranking_contract` semantics that keep raw OP_REFINED_K7 score from becoming an automatic promotion cue, the method-family evidence-debt checklist, scorecard CSV/JSON source provenance, machine-readable evidence_boundary metadata, machine-readable `decision_change_gate_minimums` for `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100` settled-observation gates, and evidence-scope decision gates |\n| Portfolio comparison logic or frozen report-facing evidence | `python3 validate_frozen_evidence_chain.py` | the forward-evidence scorecard, `compare_main_approaches`, the direct frozen-portfolio replay caution / metadata-sidecar check, the direct Phase 8 legacy report caution, the frozen decision stack with inherited scorecard-audit and current bridge rebuild-order routes, the decision-card suite, the scorecard ranking-contract audit, the narrow OP-anchor / downstream A/B / selective-scope comparison validators, and the full-data retrain diagnostic-only guardrail together as a research-side alignment sweep rather than new forward evidence by itself; the parent output fingerprints each child validation JSON and publishes a machine-readable evidence boundary for research reproducibility only |",
            "frozen_evidence_row_present",
            "fast chooser still keeps the direct scorecard route, direct main-comparison route, and broader frozen evidence-chain route for structural research and report-facing edits, now making the scorecard source-scope / non-live-evidence CSV boundary, machine-readable JSON `evidence_boundary` plus `evidence_boundary_text`, generated-at timezone-label contract, bootstrap-CI source notes plus PHASE7/PHASE8 report fingerprints, named machine-readable `decision_gate_minimums`, the explicit closest-challenger vs observation-only-pocket shadow triage, and the scorecard ranking-contract audit visible while still saying the broader sweep is an alignment read rather than new forward evidence",
        ),
        require_contains(
            text,
            "full-data retrain diagnostic-only guardrail together as a research-side alignment sweep rather than new forward evidence by itself",
            "frozen_chain_full_data_retrain_guardrail_present",
            "fast chooser now says the broader frozen evidence-chain sweep includes the full-data retrain diagnostic-only guardrail, so model-fit retrain metrics cannot drift outside the research parent route unnoticed",
        ),
        require_contains(
            text,
            "| Scorecard ranking-contract, gate floors, and CI-only usage across report-facing surfaces | `python3 validate_scorecard_ranking_contract_audit.py` | the audit verifies `forward_evidence_scorecard.json.ranking_contract` is carried by the scorecard text, main comparison, OP-anchor comparison, OP/cross-family/portfolio/method-family cards, and key JSON rollups; it also verifies the scorecard-sourced OP_REFINED CI-only diagnostic route across comparison, current-evidence, runbook, quickstart, daily-guide, full-report, and presentation markdown, verifies `current_evidence_summary.json.scorecard_audit_route` points back to the audit with source-matched gate-floor/non-evidence metadata plus on-disk route-artifact verification, structured route-field / route-read diagnostics exported as a compact parent-rollup payload, gate-floor snapshot fail-fast coverage, validator-command/source fail-fast coverage, non-evidence-flag fail-fast coverage, and route-read phrase fail-fast coverage, verifies `current_evidence_summary.json.rebuild_validation_contract` preserves the settlement-audit -> current-bridge -> bridge-validator order before current totals are quoted, exports structured rebuild-contract diagnostics as a compact parent-rollup payload, fixture-tests a bad rebuild contract, copies `forward_evidence_scorecard.json:decision_gate_minimums` into audit metadata for the 30-row anchor-displacement, 20-row Phase 8 promotion-review, and 100-row real-money-discussion floors plus the no-BAQ-as-BEL prerequisite, and validates the saved `generated_at` rebuild timestamp has an explicit timezone label and is mirrored in markdown; this is report-synchronization/provenance metadata only, not settled ROI, promotion readiness, live profitability, or real-money evidence |",
            "scorecard_ranking_contract_audit_row_present",
            "fast chooser includes the dedicated scorecard ranking-contract, decision-gate floor, CI-only usage, current-evidence scorecard_audit_route, and current-evidence rebuild_validation_contract audit so cross-surface tier-first wording, scorecard-sourced 30/20/100 gate floor metadata, OP_REFINED CI-only routing, no-BAQ-as-BEL prerequisite routing, source-matched bridge-route metadata, source-matched bridge-rebuild metadata, and saved generated_at timezone-label provenance drift can be checked directly without treating the audit as forward evidence",
        ),
        require_contains(
            text,
            "| `FROZEN_PORTFOLIO_EVAL.md` frozen replay wording, source fingerprints, current bridge rebuild route, or live-proof caution | `python3 validate_frozen_portfolio_eval_caution.py` | the frozen portfolio report still opens with the current evidence boundary: historical frozen replay, not live paper-trade ledger or real-money evidence; Phase 7 still beats Phase 8 on frozen holdout; `OP_DURABLE_K7` remains anchor, `CD_CORE_K8` paper companion, Phase 8 shadow/watch, any current top-card quote goes through the combined `operator_status_context` + `source_freshness` + `operator_read_gate` route plus `current_evidence_summary.json.rebuild_validation_contract` so source-byte changes route through settlement-audit -> current-bridge -> bridge-validator before current totals are quoted, `BAQ` is not `BEL`, and the generator/report/metadata sidecar expose exact source-byte fingerprints as reproducibility metadata only |",
            "frozen_portfolio_eval_row_present",
            "fast chooser now includes the direct frozen-portfolio replay caution validator so report wording, source-fingerprint, or current-bridge rebuild-route edits can be checked without over-reading historical replay P&L, rebuild routes, or reproducibility hashes as live paper-trade, real-money, or live-profitability evidence",
        ),
        require_contains(
            text,
            "| `PHASE8_REPORT.md` legacy Phase 8 wording, cost/sizing wording, or anti-overpromotion caution | `python3 validate_phase8_report_caution.py` | the legacy Phase 8 report still opens with the current holdout-over-headline caution, repeats the legacy/deployment split in later high-risk sections, keeps `OP_DURABLE_K7` as anchor, leaves Phase 8 shadow/watch, labels `$2` / `Cost` / `Expected` blocks as historical paper-accounting metadata only, and preserves the no-real-money / BAQ-is-not-BEL boundaries |",
            "phase8_report_row_present",
            "fast chooser now includes the direct Phase 8 legacy-report caution validator so report wording, cost/sizing language, and old full-sample headline edits can be checked without over-reading legacy accounting units as deployment guidance",
        ),
        require_contains(
            text,
            "| `compare_main_approaches` one-screen read, CSV/markdown/JSON bundle, current paper ladder, inherited scorecard ranking contract, method-family evidence-debt checklist, or method-family comparison wording | `python3 validate_compare_main_approaches.py` | the saved CSV, saved markdown, saved JSON sidecar, and real CLI output stay pinned to the frozen 2024-2025 holdout standard, including Cole's one-screen OP/CD core read, `OP_REFINED_K7` shadow-only caution, Harville benchmark-only lane, current odds-only XGBoost research-only lane, BEL-not-BAQ caution, the inherited forward-scorecard `ranking_contract` semantics that keep raw OP_REFINED_K7 score from becoming an automatic promotion cue, the method-family evidence-debt checklist, scorecard CSV/JSON source provenance, machine-readable evidence_boundary metadata, machine-readable `decision_change_gate_minimums` for `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100` settled-observation gates, and evidence-scope decision gates |",
            "compare_main_row_present",
            "fast chooser includes a dedicated main-comparison validator row so one-screen read, paper-ladder, inherited scorecard ranking-contract semantics, method-family evidence-debt checklist, and method-family wording edits do not require jumping straight to the broader frozen evidence chain",
        ),
        require_contains(
            text,
            "matched `compare_main_approaches.csv` / `.md` / `.json` bundle, the current OP/CD paper ladder, the evidence-class triage, the method-family evidence-debt checklist, the machine-readable evidence boundary, machine-readable `decision_change_gate_minimums`, or the evidence-scope decision-change gates",
            "compare_main_evidence_debt_ladder_note_present",
            "recommended escalation ladder routes method-family evidence-debt checklist edits to the direct main-comparison validator before broadening to the frozen-evidence chain",
        ),
        require_contains(
            text,
            "| OP-centered anchor framing, OP-anchor inherited scorecard ranking contract, OP-anchor readable evidence-boundary text, OP-anchor source provenance, or Harville / parked odds-only XGBoost wording | `python3 validate_op_anchor_method_comparison.py` | `OP_DURABLE_K7` versus Harville while the current odds-only XGBoost path stays parked unless its evidence class changes materially, now with explicit evidence-class labeling, inherited forward-scorecard `ranking_contract` semantics that keep raw OP_REFINED_K7 score from becoming an automatic promotion cue, machine-readable `evidence_boundary` plus readable `evidence_boundary_text`, markdown/JSON source-byte provenance across the scorecard CSV/JSON / compare-main / method-family / cross-family / downstream A/B inputs, the OP-refined challenger context, and the replay-only selective-family secondary caution; boundary text and source fingerprints are reproducibility metadata only, not settled ROI, promotion readiness, live profitability, or real-money evidence |",
            "op_anchor_row_present",
            "fast chooser includes the dedicated OP-centered comparison validator, now described with explicit evidence-class labeling, inherited forward-scorecard ranking-contract semantics, OP-anchor readable evidence-boundary text, OP-anchor source provenance, and the parked odds-only XGBoost reopening bar",
        ),
        require_contains(
            text,
            "| Downstream enriched-horse-history XGBoost A/B comparison wording, winner-only limitation framing, current-paper snapshot caveat, current-evidence-only bridge refresh, or raw-input rebuild availability | `python3 validate_ab_downstream_comparison.py` | the matched baseline-vs-enriched-horse-history downstream report, including the enriched-correction prediction-improvement read, the EV pass-count guardrail, the winning-combos-only caveat, saved JSON/markdown parity, dynamic cross-family hierarchy rerendering, the current-evidence bridge snapshot that keeps stale-card refresh routing / CD-only settled rows / source-published settlement-queue state/context / `current_evidence_summary.json.scorecard_audit_route` out of OP-anchor proof, the `ab_downstream_comparison.py --refresh-current-evidence-only` maintenance route for republishing the current bridge / hierarchy / model fingerprints from saved A/B metrics when raw race-level rebuild inputs are absent, and source-aware `SKIP` rows when full raw-input rebuild parity is unavailable |",
            "ab_downstream_row_present",
            "fast chooser includes the dedicated downstream XGBoost A/B validator plus its current-paper bridge snapshot, refresh-only maintenance route, and source-aware raw-input availability contract",
        ),
        require_contains(
            text,
            "| `FULL_DATA_RETRAIN_ARTIFACTS.md` full-data XGBoost retrain metrics, exact retrain/prediction commands, or model-fit-diagnostic-only boundary | `python3 validate_full_data_retrain_artifacts.py` | the retrain artifact keeps large full-data RMSE / MAE improvements framed as model-fit diagnostics only, keeps the exact retrain and prediction commands pinned, and routes deployment interpretation back to the selective OP/CD paper path rather than paper-trade evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
            "full_data_retrain_row_present",
            "fast chooser now includes the dedicated full-data retrain artifact validator so large payout-fit metrics stay routed to model-fit reproducibility rather than paper-trade or live-profitability evidence",
        ),
        require_contains(
            text,
            "| Recommender selective-scope guardrail or `--allow-all-combos` comparison wording | `python3 validate_compare_recommender_scope_paths.py` | the default selective-vs-widened ticket-universe artifact on fixed OP-anchor stub races, including the scorecard-sourced 30/20/100 gate read plus the no-BAQ-as-BEL prerequisite, the `current_evidence_summary.json.scorecard_audit_route` synchronization route, the `current_evidence_summary.json.rebuild_validation_contract` settlement-audit -> current-bridge -> bridge-validator route before quoting current totals, and the modeled stub-EV lift / off-scope ticket-share split that is not observed P&L |",
            "recommender_scope_row_present",
            "fast chooser includes the dedicated selective-scope comparison validator plus its scorecard-sourced gate/no-BAQ boundary and the modeled-EV/off-scope split that stays out of observed-P&L evidence",
        ),
        require_contains(
            text,
            "| `paper_trade_pipeline.py` live pipeline status contract or graceful-fallback behavior | `python3 validate_paper_trade_pipeline.py` | the direct scan -> recommend -> size -> log wrapper still distinguishes clean-empty reuse, malformed/invalid-shape/zero-byte/missing reused scan fallbacks, missing and zero-byte reused scan fallbacks with empty/readable/unreadable sidecar provenance, malformed/invalid-shape reused scan fallbacks with empty/readable/unreadable sidecar provenance, bets-ready reuse, scanner-failure and missing-output fallback with explicit empty-scan fallback metadata, scanner-failure stale-scan overwrite protection, empty/unreadable scanner-status sidecars, partial-cache activity, and signals-logged-no-bet runs through the saved machine-readable status surface, and publishes the scorecard-sourced 30/20/100 gate boundary as workflow-status metadata only |",
            "paper_trade_pipeline_row_present",
            "fast chooser includes the dedicated validator row for the direct paper-trade pipeline status contract",
        ),
        require_contains(
            text,
            "| `paper_trade_recommender.py` Phase 7 combo-universe guardrail, missing-race-id scanner-hit handling, or malformed-prediction fallback | `python3 validate_paper_trade_recommender.py` | the direct recommender still keeps the default selective Phase 7 combo universe narrow, leaves off-universe-only races as honest `NO BET` rows unless `--allow-all-combos` is explicitly requested, turns missing-race-id scanner hits and malformed prediction files into per-hit/per-race `ERROR` rows, and publishes the scorecard-sourced 30/20/100 gate boundary as source-layer metadata only |",
            "paper_trade_recommender_row_present",
            "fast chooser includes the dedicated validator row for the direct paper-trade recommender guardrail",
        ),
        require_contains(
            text,
            "| `ev_ticket_engine.py` conservative stake-sizing / no-bet boundaries | `python3 validate_ev_ticket_engine.py` | the EV sizing layer still rejects empty, negative-edge, low-probability, and under-minimum-stake cases conservatively, sizes only the top positive-EV tickets inside bankroll caps, fails loudly on malformed probability inputs, and publishes the scorecard-sourced 30/20/100 gate boundary as stake-sizing metadata only |",
            "ev_ticket_engine_row_present",
            "fast chooser includes the dedicated validator row for the EV sizing layer",
        ),
        require_contains(
            text,
            "| `paper_trade_logger.py` persistent ledger append / dedup behavior | `python3 validate_paper_trade_logger.py` | the direct logger still creates stable header-only ledgers on empty runs, appends new signal and recommendation rows with serialized list payloads, dedups prior `signal_key` values through state files plus existing ledger rows, rebuilds dedup from the ledger when state is malformed, ignores blank recommendation keys safely, and publishes the scorecard-sourced 30/20/100 gate boundary as ledger-layer metadata only |",
            "paper_trade_logger_row_present",
            "fast chooser includes the dedicated validator row for the persistent paper-trade ledger append contract",
        ),
        require_contains(
            text,
            f"| `PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md` source-chain matrix, current-evidence rebuild route, or scan/recommend/size/log guardrail inventory | `python3 validate_paper_trade_source_chain_guardrails.py` | the compact matrix stays source-matched to the four direct validators, preserves {source_chain_guardrails} guardrails across the scan -> recommend -> size -> log chain, fingerprints validator JSON inputs plus source/validator scripts, matrix generator/validator tooling, and the validated matrix markdown/JSON artifacts, renders markdown fingerprint tables exactly from the JSON sidecar, carries `current_evidence_summary.json.rebuild_validation_contract` before current totals are quoted, and keeps the operational-readiness-only / no-live-evidence boundary explicit |\n| Live scanner target prefiltering, BAQ/BEL exclusion, or `--max-races` limited-coverage status routing | `python3 validate_live_scan_targeting_and_limit_status.py` | the direct scanner/pipeline/status/ops fixture keeps `--max-races` attempts focused on OP/CD rule candidates before detail fetches, keeps BAQ out of BEL/OP/CD targeting, and classifies capped no-hit scans as operationally limited coverage with target-candidate/unattempted counts instead of clean empty forward observations; this is synthetic guardrail metadata only, not a quiet-day, ROI, promotion, live-profitability, or real-money signal |\n| Scanner-status sidecar path resolution or stale default `live_scan.status.json` masking risk | `python3 validate_scanner_sidecar_resolution_contract.py` | the direct copied-sidecar fixture proves a pipeline-declared `scanner_status_path` stays authoritative across status summary, next steps, `PAPER_TRADE_NOW`, `OPS_HISTORY`, and saved-live refresh, including missing declared sidecars, stale default sidecars, and HTTP 403 action/recheck preservation; this is routing metadata only, not a quiet-day, ROI, promotion, live-profitability, or real-money signal |",
            "paper_trade_source_chain_row_present",
            "fast chooser includes a dedicated validator row for the compact scan/recommend/size/log source-chain matrix and current-evidence rebuild route, exposes the live-scan targeting / max-races limited-coverage route as synthetic operational metadata, and exposes the scanner-sidecar path-resolution route as routing metadata rather than quiet-day, ROI, promotion, live-profitability, or real-money evidence",
        ),
        require_contains(
            text,
            "| Operator-facing paper-trade summaries or empty-day/cache messaging | `python3 validate_paper_trade_operator_suite.py` | base lane status summary, per-lane next-step helper, frozen forward checker, compact lane monitor, right-now card, daily wrapper, daily summary, lane summary, rolling ops history, saved-live refresh-helper behavior, preserved primary/shadow recent-run context plus lane why-now lines in the right-now card, combined daily summary, wrapper fallbacks preserving context/why lines, and refresh rebuilds, cache-only messaging, partial-cache messaging, green cache-only / partial-cache checks proving cache-edge routing / reproducibility toward refresh or rerun only rather than quiet-day, current scanner, settled ROI, live profitability, promotion readiness, or real-money evidence, split-aware saved-preflight-JSON fallback coverage when the sibling text note is missing or blank, the routed preflight-note source-path contract in the top card, direct primary/shadow pipeline/scanner status-sidecar pointers in the top card, right-now text/markdown/JSON parity or explicit helper-failure JSON placeholder behavior, missing-status wrapper fallback, markdown-mirror placeholder fallback, lane-summary base-summary fallback, daily-summary placeholder fallback, and the operator-suite machine-readable evidence boundary that keeps parent operator passes separate from settled ROI, live profitability, promotion readiness, and real-money evidence |",
            "paper_trade_operator_suite_row_present",
            "fast chooser includes the broader operator-suite row with the current split-aware missing-or-blank-text JSON fallback coverage, routed preflight-note source-path contract, direct top-card sidecar-pointer contract, cache-edge-only boundary for green cache-only/partial-cache checks, and right-now text/markdown/JSON parity or explicit helper-failure JSON placeholder behavior",
        ),
        require_contains(
            text,
            "| `PAPER_TRADE_NOW` text/markdown/JSON top-card wording or right-now action priority | `python3 validate_paper_trade_now.py` | the single-action operator card keeps settlement-first, decision-grade review, rerun-live, missing scan-output refresh-artifacts, explicit recommender/logger pipeline-failure refresh, and no-target stand-down ordering straight, while pinning `PAPER_TRADE_NOW.json` parity with `paper_trade_now.py --format json` unless the full helper fails into an explicit no-new-forward-evidence placeholder, explicit primary/shadow lane-context plus lane why-now lines, the full routed recommendation-lane quick-reads bundle, the routed preflight-note source path, direct primary/shadow pipeline/scanner status-sidecar pointers, and the explicit live lane hierarchy block across the saved and shell-facing JSON, text, and markdown surfaces, including split-aware saved-preflight-JSON fallback when the sibling text note is missing or blank on both the no-target and active-target branches plus the explicit stale-snapshot note so inherited lane context / counts / quick reads do not masquerade as current state |",
            "paper_trade_now_row_present",
            "fast chooser includes a dedicated validator row for the single top-card paper-trade action surface, including PAPER_TRADE_NOW.json parity with the source helper or an explicit helper-failure placeholder, the routed preflight-note source path, direct sidecar-pointer contract, split-aware missing-or-blank-text JSON fallback contract, and the stale-snapshot honesty note",
        ),
        require_contains(
            text,
            "| `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` / `current_evidence_summary.py` current-evidence bridge, source-consistency, combined operator read route, timestamp-gap exclusion, true no-BET recommendation-context wording, scanner/API-failure recommendation-context wording, structured freshness-state wording, refresh action boundary wording, scorecard CI-only diagnostic routing, scorecard-audit route, or settlement-queue state/by-rule wording | `python3 validate_current_evidence_summary.py` | the report-ready bridge stays source-matched to the frozen scorecard, `PAPER_TRADE_NOW`, settlement audit, and timestamp-aware primary settlement CSV recompute, exposes CSV settled_ts gap exclusion plus the combined route across `operator_status_context`, `source_freshness` / `right_now_freshness_state` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use`, and `operator_read_gate` / `requires_refresh_before_evidence_read` before using a stale or missing-state right-now card as today's operator instruction or evidence, fixture-tests true no-BET recommendation context so it stays recommendation-state routing rather than open-row context and scanner/API-failure recommendation context so the specific API/scanner boundary is not followed by duplicate generic operator-context wording and still preserves `Sidecar action: refresh_daily_wrapper_before_evidence_read` plus `Recheck command: ./run_daily_portfolio_observation.sh`, keeps `OP_DURABLE_K7` / `CD_CORE_K8` / `OP_REFINED_K7` roles intact, copies the scorecard-sourced `scorecard_ci_only_promotion_check` from `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` with `ci_only_promotion_allowed=false`, exposes the CD-only current rule mix, settlement queue state/by rule, bridge-published current gates, the `scorecard_audit_route` to `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks, the wrapper-refresh non-evidence boundary, and the operator-read-gate non-evidence boundary, and keeps source consistency / source freshness / structured freshness-state / refresh action boundary / operator-status context / operator_read_gate / scorecard CI-only diagnostic / scorecard_audit_route / fingerprints as reproducibility and operator-readiness metadata only rather than settled ROI, live profitability, promotion readiness, OP-anchor proof, or real-money evidence |",
            "current_evidence_summary_row_present",
            "fast chooser includes the current-evidence bridge validator row so report-ready current-context edits route to the source-consistency / combined-operator-read-route / no-overclaim check instead of only broader parent sweeps",
        ),
        require(
            "current-evidence bridge, source-consistency, combined operator read route, timestamp-gap exclusion, true no-BET recommendation-context wording, scanner/API-failure recommendation-context wording, structured freshness-state wording, refresh action boundary wording, scorecard CI-only diagnostic routing, scorecard-audit route, or settlement-queue state/by-rule wording" in text
            and "exposes CSV settled_ts gap exclusion plus the combined route across `operator_status_context`, `source_freshness` / `right_now_freshness_state` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use`, and `operator_read_gate` / `requires_refresh_before_evidence_read` before using a stale or missing-state right-now card as today's operator instruction or evidence" in text
            and "fixture-tests true no-BET recommendation context so it stays recommendation-state routing rather than open-row context and scanner/API-failure recommendation context so the specific API/scanner boundary is not followed by duplicate generic operator-context wording and still preserves `Sidecar action: refresh_daily_wrapper_before_evidence_read` plus `Recheck command: ./run_daily_portfolio_observation.sh`" in text
            and "CSV settled_ts gap exclusion" in text
            and "`CURRENT_EVIDENCE_SUMMARY` now requires the combined `operator_status_context` + `source_freshness` / `right_now_freshness_state` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` route before stale or missing-state right-now cards can be treated as today's operator instruction or evidence" in text
            and "API-access failure recommendation context still carries `Sidecar action: refresh_daily_wrapper_before_evidence_read` plus `Recheck command: ./run_daily_portfolio_observation.sh`" in text
            and "the wrapper-refresh boundary says a rerun can update operator surfaces but does not settle open rows, create ROI-complete evidence, count a clean empty refresh as forward performance, or support real-money evidence" in text
            and "combined `operator_status_context` + `source_freshness` / `right_now_freshness_state` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` route before stale or missing-state cards become today's instruction or evidence" in text
            and operator_read_gate.get("source_path") == "operator_read_gate"
            and operator_read_gate.get("gate_status") in {
                "refresh_required_before_evidence_read",
                "current_operator_routing_context_only",
            }
            and operator_read_gate.get("valid_use") == "operator instruction/evidence-read gating only"
            and isinstance(operator_read_gate.get("requires_refresh_before_evidence_read"), bool)
            and isinstance(operator_read_gate.get("recommended_command"), str)
            and bool(operator_read_gate.get("recommended_command"))
            and operator_read_gate.get("current_top_card_counts_as_no_target_evidence") is False
            and operator_read_gate.get("current_top_card_counts_as_clean_empty_evidence") is False
            and operator_read_gate.get("current_top_card_counts_as_bet_readiness_evidence") is False
            and operator_read_gate.get("current_top_card_counts_as_settled_roi_evidence") is False
            and operator_read_gate.get("not_live_profitability_evidence") is True
            and operator_read_gate.get("not_real_money_evidence") is True,
            "current_evidence_combined_operator_read_route",
            "quickstart now pins the combined current-evidence operator_status_context / source_freshness / operator_read_gate route, true no-BET recommendation-context wording, and scanner/API-failure sidecar action/recheck wording across the fast chooser, green-read summary, and broad-change read order as operator-readiness metadata rather than performance evidence",
        ),
        require(
            "`scorecard_ci_only_promotion_check` from `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` with `ci_only_promotion_allowed=false`" in text
            and "scorecard CI-only diagnostic / scorecard_audit_route / fingerprints as reproducibility and operator-readiness metadata" in text
            and "the scorecard-sourced `scorecard_ci_only_promotion_check` for `OP_REFINED_K7` with `ci_only_promotion_allowed=false`" in text
            and ci_only_context.get("source") == CI_ONLY_SOURCE
            and ci_only_context.get("candidate_rule_id") == "OP_REFINED_K7"
            and ci_only_context.get("current_anchor_rule_id") == "OP_DURABLE_K7"
            and ci_only_context.get("ci_only_promotion_allowed") is False
            and ci_only_context.get("current_matches_scorecard_diagnostic") is True,
            "current_evidence_ci_only_diagnostic_route",
            "quickstart current-evidence routing now names the scorecard-sourced OP_REFINED CI-only diagnostic and the validator proves current_evidence_summary.json source-matches forward_evidence_scorecard.json with ci_only_promotion_allowed=false",
        ),
        require(
            "`scorecard_audit_route` to `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks" in text
            and "scorecard CI-only diagnostic / scorecard_audit_route / fingerprints as reproducibility and operator-readiness metadata" in text
            and scorecard_audit_route.get("source_path") == "scorecard_audit_route"
            and scorecard_audit_route.get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route.get("json_path") == "scorecard_ranking_contract_audit.json"
            and scorecard_audit_route.get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route.get("gate_floor_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get(
                "anchor_displacement_min_roi_complete_settled_observations"
            )
            == scorecard_gates["anchor_displacement_min_roi_complete_settled_observations"]
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get(
                "phase8_promotion_review_min_roi_complete_settled_observations"
            )
            == scorecard_gates["phase8_promotion_review_min_roi_complete_settled_observations"]
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get(
                "real_money_discussion_min_total_settled_observations_with_usable_roi"
            )
            == scorecard_gates["real_money_discussion_min_total_settled_observations_with_usable_roi"]
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get("real_money_no_baq_as_bel_required") is True
            and scorecard_audit_route.get("artifacts_present") is True
            and scorecard_audit_route.get("not_forward_performance_evidence") is True
            and scorecard_audit_route.get("not_settled_roi_evidence") is True
            and scorecard_audit_route.get("not_promotion_readiness_evidence") is True
            and scorecard_audit_route.get("not_live_profitability_evidence") is True
            and scorecard_audit_route.get("not_bankroll_guidance") is True
            and scorecard_audit_route.get("not_real_money_evidence") is True,
            "current_evidence_scorecard_audit_route",
            "quickstart current-evidence routing now names current_evidence_summary.json scorecard_audit_route to the scorecard ranking-contract audit and proves its copied 30/20/100 gate floors, validator command, artifact paths, and non-evidence flags from the source JSON",
        ),
        require(
            "combined route across `operator_status_context`, `source_freshness` / `right_now_freshness_state` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use`, and `operator_read_gate` / `requires_refresh_before_evidence_read` before using a stale or missing-state right-now card as today's operator instruction or evidence" in text
            and "`operator_read_gate` / `requires_refresh_before_evidence_read` route before stale or missing-state right-now cards can be treated as today's operator instruction or evidence" in text
            and "operator-read-gate non-evidence boundary" in text
            and operator_read_gate.get("gate_status") in {
                "refresh_required_before_evidence_read",
                "current_operator_routing_context_only",
            }
            and operator_read_gate.get("valid_use") == "operator instruction/evidence-read gating only"
            and isinstance(operator_read_gate.get("requires_refresh_before_evidence_read"), bool)
            and isinstance(operator_read_gate.get("recommended_command"), str)
            and bool(operator_read_gate.get("recommended_command"))
            and operator_read_gate.get("current_top_card_counts_as_no_target_evidence") is False
            and operator_read_gate.get("current_top_card_counts_as_clean_empty_evidence") is False
            and operator_read_gate.get("current_top_card_counts_as_bet_readiness_evidence") is False
            and operator_read_gate.get("current_top_card_counts_as_settled_roi_evidence") is False
            and operator_read_gate.get("not_forward_performance_evidence") is True
            and operator_read_gate.get("not_promotion_readiness_evidence") is True
            and operator_read_gate.get("not_live_profitability_evidence") is True
            and operator_read_gate.get("not_real_money_evidence") is True,
            "current_evidence_operator_read_gate_route",
            "quickstart now treats current_evidence_summary.json operator_read_gate as a first-class current-evidence route, requiring wrapper refresh before stale top-card instruction/evidence use and keeping that read gate out of no-target, clean-empty, bet-readiness, settled-ROI, forward-performance, promotion, live-profitability, bankroll, and real-money evidence",
        ),
        require(
            "missing or invalid `PAPER_TRADE_NOW.run_freshness.freshness_state` must fail closed to the wrapper refresh path" in text
            and "right_now_freshness_state_valid" in text
            and "structured freshness-state / refresh action boundary / operator-status context / operator_read_gate / scorecard CI-only diagnostic / scorecard_audit_route / fingerprints as reproducibility and operator-readiness metadata" in text,
            "current_evidence_structured_freshness_state_route",
            "quickstart now tells future bridge edits that PAPER_TRADE_NOW.run_freshness.freshness_state must be preserved into right_now_freshness_state/right_now_freshness_state_valid and missing or invalid states fail closed to the wrapper refresh path",
        ),
        require(
            "bridge-published current gates" in text
            and "`scorecard_audit_route` to `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks" in text
            and "settlement queue state/by rule" in text
            and "wrapper-refresh non-evidence boundary" in text
            and "refresh action boundary / operator-status context / operator_read_gate / scorecard CI-only diagnostic / scorecard_audit_route / fingerprints as reproducibility and operator-readiness metadata" in text
            and "4/30 and 4/100 gates" not in text
            and "preserves 4/30 and 4/100 current gates" not in text,
            "current_evidence_quickstart_uses_bridge_published_gates",
            "quickstart current-evidence routing now names settlement queue state/by rule, bridge-published gates, scorecard_audit_route synchronization metadata, and wrapper-refresh non-evidence boundary instead of pinning today's paper-count literals or implying a current open settlement row",
        ),
        require(
            "## Current bridge rebuild order" in text
            and "When scorecard, rules, signal-ledger, or settlement-ledger bytes change, refresh the current-evidence bridge in this order before quoting `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json`:" in text
            and "1. `python3 paper_trade_settlement_audit.py` — refresh settlement-audit source fingerprints after scorecard, rules, signals, or settlement-ledger byte changes." in text
            and "2. `python3 current_evidence_summary.py` — rebuild the bridge from the refreshed scorecard, right-now card, settlement audit, and CSV recompute." in text
            and "3. `python3 validate_current_evidence_summary.py` — confirm source fingerprint parity, gate-source alignment, and non-evidence boundaries before quoting the bridge." in text
            and "This order is copied from `current_evidence_summary.json.rebuild_validation_contract`." in text
            and "It is provenance/rebuild metadata only: it does not create settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence." in text
            and current_bridge_rebuild_contract.get("source_path") == "rebuild_validation_contract"
            and current_bridge_rebuild_contract.get("prerequisite_rebuild_command") == "python3 paper_trade_settlement_audit.py"
            and current_bridge_rebuild_contract.get("rebuild_command") == "python3 current_evidence_summary.py"
            and current_bridge_rebuild_contract.get("direct_validation_command") == "python3 validate_current_evidence_summary.py"
            and current_bridge_rebuild_contract.get(
                "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
            )
            is True
            and current_bridge_rebuild_contract.get("upstream_refresh_order_is_provenance_metadata_only") is True
            and current_bridge_rebuild_contract.get("not_settled_roi_or_real_money_evidence") is True,
            "current_bridge_rebuild_order_documented",
            "quickstart now publishes the current bridge settlement-audit -> bridge rebuild -> bridge validator order from current_evidence_summary.json.rebuild_validation_contract and keeps that order as provenance/rebuild metadata only",
        ),
        require_contains(
            text,
            "| Current hierarchy wording, `live_hierarchy` JSON fields, or `primary_companion` / legacy `primary_shadow` compatibility | `python3 validate_current_hierarchy_language.py` | high-traffic surfaces keep `OP_DURABLE_K7` as anchor, `CD_CORE_K8` as the primary OP/CD paper-basket companion with legacy `primary_shadow` compatibility only, and `OP_REFINED_K7` as the same-family shadow/watch challenger; the pass is wording / structured-key compatibility metadata only, not settled ROI, live profitability, promotion readiness, anchor-change, companion-change, or real-money evidence |",
            "current_hierarchy_row_present",
            "fast chooser exposes the direct current-hierarchy wording / structured-key compatibility validator without treating wording cleanliness or legacy primary_shadow compatibility as settled ROI, live profitability, promotion readiness, anchor-change, companion-change, or real-money evidence",
        ),
        require_contains(
            text,
            "| `run_daily_portfolio_observation.sh` wrapper stitching or wrapper-level fallback behavior | `python3 validate_run_daily_portfolio_observation.py` | the real daily wrapper keeps preflight, per-lane summaries, ops history, right-now, `CURRENT_EVIDENCE_SUMMARY`, and the combined daily summary stitched together across no-target / active-target cache misses, readable scanner-status plus missing scan-output refresh days, explicit recommender/logger pipeline-error refresh days, hit-found but no-BET days, settle-first, partial-cache, helper-failure, and placeholder-fallback days, including preservation of saved primary/shadow recent-run context plus why-now lines when the wrapper has to fall back, source-backed current-evidence recommendation-context/open-row separation plus settlement-audit -> current bridge -> current bridge validator rebuild-order publication, direct scorecard-sourced 30/20/100 gate-boundary publication, and the leaf source for a distinct inherited wrapper-guardrail inventory that the broader operator/project rollups are supposed to preserve |",
            "daily_wrapper_row_present",
            "fast chooser includes a dedicated validator row for the real daily wrapper instead of forcing wrapper edits through only the broader operator suite, and now says that wrapper is the leaf source for an inherited guardrail inventory plus source-backed current-evidence recommendation-context/open-row separation, rebuild-order publication, and direct scorecard gate-boundary publication that the broader operator/project rollups should preserve",
        ),
        require_contains(
            text,
            "| `paper_trade_preflight_note.py` shared calendar-note wording or JSON/text branch behavior | `python3 validate_paper_trade_preflight_note.py` | the preflight note keeps active-target, no-target, API-unreachable, and explicit-error days straight across text and JSON outputs without collapsing unknown-calendar days into clean no-target messaging |",
            "preflight_note_row_present",
            "fast chooser includes a dedicated validator row for the shared preflight note instead of forcing that question through only the broader operator suite",
        ),
        require_contains(
            text,
            "| `paper_trade_status_summary.py` one-line base lane summary wording or JSON/text branch behavior | `python3 validate_paper_trade_status_summary.py` | the base status summary keeps scanner-only alerts, bets-ready, clean-empty, partial-cache, cache-only-miss, missing-scan-output, scanner-failure, API-access / HTTP 403 scanner-failure action/recheck routing, stale-cache fallback count/kind/error visibility, empty/unreadable/invalid-shape scanner sidecars, pipeline-recorded empty/unreadable/invalid-shape scanner-status states, wrapper-only required-pipeline missing/empty/unreadable/invalid-shape sidecars, recommender-failure, logger-failure, signals-without-bet, and no-readable-sidecars failure states straight across both text and JSON paths, with API-access routes preserving `refresh_daily_wrapper_before_evidence_read` plus `./run_daily_portfolio_observation.sh` as operator context only and the human-facing recommender/logger failure line keeping stage / error type / detail visible |",
            "status_summary_row_present",
            "fast chooser includes a dedicated validator row for the one-line base lane summary instead of forcing that question through only the broader operator suite, and now names API-access / HTTP 403 action-recheck routing plus stale-cache fallback metadata as operator context only",
        ),
        require_contains(
            text,
            "| `paper_trade_settlement_sync.py` settlement-template sync wording or one-row-per-signal-key ledger behavior | `python3 validate_paper_trade_settlement_sync.py` | the settlement sync helper keeps stable empty headers, one open row per live `signal_key`, preserved manual settlement fields, refreshed signal-owned metadata, blank and duplicate signal-key skips, blank settlement-key drops, and orphan settlement-row cleanup straight through the real CLI |",
            "settlement_sync_row_present",
            "fast chooser includes a dedicated validator row for the settlement-template sync helper instead of forcing that question through only the broader operator suite, with separate blank/duplicate signal-key / blank settlement-key / orphan settlement-row cleanup visibility",
        ),
        require_contains(
            text,
            "| `paper_trade_settlement_helper.py` manual settlement-entry wording or queue / single-row update behavior | `python3 validate_paper_trade_settlement_helper.py` | the settlement helper keeps open-queue rendering, separate settled-row ROI-gap visibility including non-positive cost gaps, queue truncation, exact one-row settlement updates, duplicate signal-key rejection before mutation, zero/non-positive actual-cost rejection, settlement cost-source reporting, positive expected-cost fallback for omitted actual cost, supplied `settled_ts` validation, timestamp-omission warnings that the row stays outside ROI-complete sample gates, true missing/malformed/non-positive-cost handling, and missing-signal failures straight across text, markdown, and JSON outputs |\n| `paper_trade_settlement_audit.py` ledger-completeness / ROI-coverage audit wording, repair labels, custom lane names, or gate reads | `python3 validate_paper_trade_settlement_audit.py` | the settlement audit keeps structural signal/settlement repairs, matched-key metadata mismatches, blank signal-key versus blank settlement-key repair labels, duplicate custom lane-name rejection before output artifacts, ROI-complete row counts, lane-specific sample gates, shadow per-rule review floors, and no-new-forward-evidence boundaries straight across markdown and JSON outputs |",
            "settlement_helper_row_present",
            "fast chooser includes dedicated validator rows for the manual settlement helper and the ledger-completeness / ROI-coverage audit instead of forcing those questions through only the broader operator suite",
        ),
        require_contains(
            text,
            "| `paper_trade_next_steps.py` exact next-command wording or JSON/text/markdown branch behavior | `python3 validate_paper_trade_next_steps.py` | the next-steps helper keeps settlement-first, missing scan-output refresh-artifacts, API-access stale-cache fallback routing, rerun-live, limited-cache, explicit recommender/logger pipeline-failure recovery, waiting-for-first-settled, collecting-sample, and decision-grade-review states straight, including the mixed-state latest-run context line |",
            "next_steps_row_present",
            "fast chooser includes a dedicated validator row for the exact next-command helper instead of forcing that question through only the broader operator suite",
        ),
        require_contains(
            text,
            "| `paper_trade_forward_check.py` frozen-baseline forward assessment wording or JSON/text/markdown branch behavior | `python3 validate_paper_trade_forward_check.py` | the forward check keeps no-data, too-early, within-noise, running-cold, running-hot, missing-baseline, and no-overpromotion decision-gate states straight, including recommendation-flow detail, ROI fallback from expected cost, explicit ROI cost-source counts, and malformed `actual_cost` gap handling |",
            "forward_check_row_present",
            "fast chooser includes a dedicated validator row for the frozen-baseline forward check instead of forcing that question through only the broader operator suite",
        ),
        require_contains(
            text,
            "| `paper_trade_lane_monitor.py` compact per-lane monitor wording or JSON/text/markdown branch behavior | `python3 validate_paper_trade_lane_monitor.py` | the compact lane monitor keeps forward assessment, no-overpromotion decision-gate wording, open-settlement queue visibility, queue truncation, missing-baseline handling, and decision-grade ROI detail straight across JSON, text, and markdown paths |",
            "lane_monitor_row_present",
            "fast chooser includes a dedicated validator row for the compact per-lane monitor instead of forcing that question through only the broader operator suite",
        ),
        require_contains(
            text,
            "| `paper_trade_daily_summary.py` combined daily-summary wording or quick-jump / placeholder behavior | `python3 validate_paper_trade_daily_summary.py` | the combined daily summary keeps its full routed quick-jump bundle, routed top-card focus/timing/freshness/ops snapshot, explicit primary/shadow recent-run context lines, explicit primary/shadow next-step state lines plus lifted no-overpromotion decision-gate snapshot lines, first-read and broader-review readiness lines, preflight context, primary-vs-shadow lane sections, artifacts-root links, explicit recommender/logger failure context, pipeline-recorded scanner-status issue lines, and explicit missing-preflight / missing-lane placeholders straight, so shadow review-readiness stays visible without being read as live promotion |",
            "daily_summary_row_present",
            "fast chooser includes a dedicated validator row for the combined daily-summary surface instead of forcing that question through only the broader operator suite, with the routed top-card snapshot, explicit next-step-state visibility, and the no-live-promotion guardrail pinned",
        ),
        require_contains(
            text,
            "| `refresh_live_paper_trade_surfaces.py` saved-live rebuild behavior or targeted maintenance flags | `python3 validate_refresh_live_paper_trade_surfaces.py` | the saved-live refresh helper still rebuilds stale per-run operator surfaces, saved `preflight_note` text/JSON, plus temp-routed `OPS_HISTORY` / matched `PAPER_TRADE_NOW` text/markdown/JSON and `CURRENT_EVIDENCE_SUMMARY` markdown/JSON outputs from the current generators, keeps refreshed `PAPER_TRADE_NOW.json` source-matched to `paper_trade_now.py --format json` while refreshed text/markdown stay pinned to explicit primary/shadow recent-run context plus lane why-now lines and the full routed recommendation-lane quick-reads bundle, rebuilds `CURRENT_EVIDENCE_SUMMARY` from the refreshed right-now JSON and settlement-audit JSON while preserving the settlement-audit -> current bridge -> current bridge validator rebuild contract plus no-forward/no-real-money boundaries, keeps stale rebuilt top cards explicitly marked as inherited snapshot context rather than current-day state, preserves missing scan-output latest-run context in rebuilt per-run next-steps / lane summaries / daily summaries, rerenders refreshed `daily_summary.txt` files against those top-level outputs so the routed top-card focus/timing/freshness/ops snapshot and quick-jump bundle stay source-matched, keeps `--latest-only` confined to the newest copied run's preflight, lane, and daily-summary surfaces, keeps `--skip-top-level` confined to leaving `OPS_HISTORY` / matched `PAPER_TRADE_NOW` / `CURRENT_EVIDENCE_SUMMARY` outputs untouched while still rebuilding those per-run surfaces against the existing top-level outputs, says explicitly both that a refresh rerenders existing saved artifacts rather than creating new forward evidence and whether `--as-of-date` was actually applied or skipped, and now acts as the leaf source for a distinct inherited wrapper-guardrail inventory that the broader operator/project rollups are supposed to preserve |",
            "refresh_helper_row_present",
            "fast chooser includes a dedicated validator row for the saved-live refresh helper instead of forcing that question through only the broader operator suite, and now pins the right-now JSON parity rebuild, current-evidence bridge rebuild contract, routed daily-summary snapshot inheritance, the separate --latest-only versus --skip-top-level maintenance boundaries, the stale rebuilt-card inherited-snapshot honesty note, missing scan-output saved-live context preservation, the as-of-date applied-vs-skipped honesty note, the not-new-evidence framing, and the fact that this leaf now feeds an inherited guardrail inventory into the broader operator/project rollups",
        ),
        require_contains(
            text,
            "If a source-layer paper-trade helper changed but you did **not** run a fresh daily wrapper cycle, refresh the persisted live artifacts before validating them:\n\n```bash\npython3 refresh_live_paper_trade_surfaces.py\n```\n\nThat is the honest fix when matched `PAPER_TRADE_NOW.txt` / `PAPER_TRADE_NOW.md` / `PAPER_TRADE_NOW.json`, `OPS_HISTORY`, `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json`, saved `preflight_note` text/JSON, or saved per-run summaries drift only because the render logic changed underneath them. The rebuilt `PAPER_TRADE_NOW.json` should stay source-matched to `paper_trade_now.py --format json`; if the full right-now helper fails, JSON should be an explicit no-new-forward-evidence placeholder rather than stale automation data. The rebuilt current-evidence bridge should come from the refreshed right-now JSON plus settlement-audit JSON and preserve `current_evidence_summary.json.rebuild_validation_contract` as provenance/rebuild metadata only, not settled ROI, promotion, live-profitability, or real-money evidence.\n\nIf that rebuilt top-level `PAPER_TRADE_NOW` card is still stale, its downstream lane context / counts / quick reads should remain explicitly labeled as inherited snapshot context rather than current-day state.\n\nIf you need the rebuilt top-level `PAPER_TRADE_NOW` freshness read pinned to a specific calendar reference during validation or backfill rerenders, add `--as-of-date YYYY-MM-DD`; the helper stdout now also says whether that pin was applied or ignored because top-level outputs were skipped.\n\nIf you use `--latest-only`, that narrowed rebuild should stay confined to the newest copied run's preflight, lane, and daily-summary surfaces rather than drifting into older runs or top-level outputs.\n\nIf you use `--skip-top-level`, that targeted maintenance mode should leave `OPS_HISTORY` / matched `PAPER_TRADE_NOW` / `CURRENT_EVIDENCE_SUMMARY` outputs untouched while still rebuilding per-run preflight, lane, and daily-summary surfaces against the existing top-level outputs; in that mode the helper should also say explicitly when `--as-of-date` was ignored because top-level refresh was skipped.\n\nIf you changed the refresh helper itself, run `python3 validate_refresh_live_paper_trade_surfaces.py` before or alongside the broader operator suite.\n\nA passing refresh only means the saved surfaces were re-rendered from existing artifacts — including missing scan-output context preservation in rebuilt per-run surfaces and rerendered daily summaries inheriting refreshed top-level snapshot lines; it is not a new paper-trade outcome or a new forward-observation result.\n\nThe refresh-helper and daily-wrapper validators are still the source of truth for those wrapper contracts. The broader `validate_paper_trade_operator_suite.py` and `validate_project_surfaces.py` sweeps should now carry their inherited wrapper-guardrail inventories upward too, rather than flattening those leaves into one ambiguous pass count.",
            "saved_live_refresh_note_present",
            "quickstart now tells readers to refresh persisted live paper-trade surfaces before validating stale saved artifacts after source-layer changes, to keep rebuilt PAPER_TRADE_NOW text/markdown/JSON outputs source-matched with JSON parity or explicit helper-failure placeholder behavior, to keep the rebuilt current-evidence bridge source-routed through refreshed right-now plus settlement-audit JSON with rebuild-contract provenance only, to keep stale rebuilt top cards labeled as inherited snapshot context rather than current-day state, to use --as-of-date when the rebuilt top-level freshness read must stay calendar-pinned, to see in stdout whether that pin was actually applied or skipped, to keep --latest-only and --skip-top-level as distinct targeted maintenance modes with different scope boundaries, to use the narrow refresh-helper validator when that helper changes, to avoid reading a passing refresh as new forward evidence rather than refreshed snapshot inheritance proof, and to expect the broader operator/project rollups to preserve the wrapper leaves' inherited guardrail inventories rather than flatten them into one pass count",
        ),
        require(
            f"- `python3 validate_paper_trade_source_chain_guardrails.py` when the question is whether the compact `PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md` / `.json` matrix still source-matches all four direct validators, their source/validator scripts, the matrix generator/validator tooling, and the validated matrix markdown/JSON artifacts, preserves the {source_chain_guardrails} guardrails across {source_chain_fixtures} fixture scenarios, renders markdown fingerprint tables exactly from the JSON sidecar, carries `current_evidence_summary.json.rebuild_validation_contract` before current totals are quoted, and keeps the operational reproducibility/readiness boundary explicit" in text
            and "- `python3 validate_live_scan_targeting_and_limit_status.py` when the question is whether the live scanner spends capped race-detail attempts only on OP/CD rule-candidate races, keeps BAQ out of BEL targeting, and routes max-races capped no-hit scans as limited coverage rather than clean empty forward observations; this is synthetic scanner/pipeline/status/ops guardrail metadata only" in text
            and "- `python3 validate_scanner_sidecar_resolution_contract.py` when the question is whether a pipeline-declared `scanner_status_path` stays authoritative over stale default `live_scan.status.json` files across status summary, next steps, `PAPER_TRADE_NOW`, `OPS_HISTORY`, and saved-live refresh, including missing declared sidecars and HTTP 403 action/recheck preservation as routing-fixture metadata only" in text
            and "After the direct source-chain matrix is fresh, use `python3 validate_paper_trade_operator_suite.py --reuse-existing-child-json` and `python3 validate_project_surfaces.py --reuse-existing-child-json` only as parent propagation checks" in text
            and "the operator suite should preserve its embedded `auxiliary_source_chain_matrix`, confirm the matrix artifact fingerprints still match disk, and recompute the matrix payload from current source-layer inputs before accepting reused child JSON" in text
            and f"the project sweep should verify that source-matched {source_chain_guardrails}-guardrail audit plus the current-evidence rebuild route instead of flattening scan/recommend/size/log into one generic operator green light" in text
            and "Those parent passes remain operational reproducibility/readiness checks, not settled ROI, not promotion readiness, not live profitability, and not real-money evidence." in text,
            "source_chain_shortcut_present",
            "source-layer shortcut section now points compact scan/recommend/size/log matrix and current-evidence rebuild-route questions to the dedicated source-chain guardrail validator, exposes the direct live-scan targeting / max-races limited-coverage validator as synthetic scanner/pipeline/status/ops metadata, exposes the scanner-sidecar resolution route for copied-sidecar masking issues, then explains how the operator/project parent rollups should preserve the embedded source-chain matrix and recompute payload parity as propagation/readiness metadata rather than flattening it into a generic green pass",
        ),
        require(
            f"preserves {source_chain_guardrails} guardrails across the scan -> recommend -> size -> log chain" in text
            and f"preserves the {source_chain_guardrails} guardrails across {source_chain_fixtures} fixture scenarios" in text
            and f"source-matched {source_chain_guardrails}-guardrail audit" in text
            and "preserves 24 guardrails" not in text
            and "preserves the 24 guardrails" not in text
            and "source-matched 24-guardrail" not in text,
            "source_chain_guardrail_count_matches_matrix_json",
            f"quickstart source-chain wording now matches {MATRIX_JSON.name}: {source_chain_guardrails} guardrails across {source_chain_fixtures} fixture scenarios, with stale 24-guardrail wording absent",
        ),
        require(
            "## Disk-space preflight for temp-heavy validators" in text
            and "Before running temp-heavy fixture validators, especially the daily-wrapper, refresh-helper, decision-card, frozen-evidence, and project-surface sweeps, run:" in text
            and "df -h ." in text
            and "project-local roots under `out/status_validation/`" in text
            and "low free space can still make helper subprocesses or temporary writes fail before the evidence logic is reached" in text
            and "a successful rerun after clearing space is validation hygiene only, not a current-day scanner result, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in text
            and "For a dry-run inventory of disposable validation scratch roots, use `python3 validation_scratch_cleanup.py --json`" in text
            and "It only targets generated scratch directories under `out/status_validation/` named `_tmp` or ending in `_fixture`" in text
            and "The JSON also publishes `valid_evidence_scope=validation_scratch_cleanup_operational_hygiene_only`, a 512 MiB low-disk warning threshold plus before/after below-threshold fields" in text
            and "estimated free space after removing the listed scratch roots" in text
            and "`validation_scratch_cleanup_insufficient_for_threshold` flag" in text
            and "if that flag remains true after a clean or tiny scratch inventory, look for non-project caches or run only narrow validators instead of treating cleanup as an evidence change" in text
            and "If the helper itself changes, run `python3 validate_validation_scratch_cleanup.py`; that validator should remove its own generated fixture root after checks and publish the same valid scope, and the validation is cleanup-scope hygiene only, not paper-trade evidence." in text,
            "disk_space_preflight_present",
            "quickstart now documents the disk-space preflight, dry-run-first cleanup helper, valid cleanup scope, low-disk warning fields, scratch-cleanup insufficiency flag, and cleanup-validator self-cleaning fixture-root expectation for temp-heavy project-local scratch validators, while framing no-space retries and cleanup-scope validation as operational hygiene rather than scanner, ROI, promotion, live-profitability, bankroll, or real-money evidence",
        ),
        require(
            "Normal cleanup use should omit `--status-root`." in text
            and "That hook is for narrow diagnostics and tests only: the root must resolve under the real `out/status_validation/` tree" in text
            and "project-local lookalikes and file roots are refused" in text
            and "scratch-like symlinks are ignored rather than inventoried or removed" in text
            and "A clean cleanup dry-run or successful `--apply` means only that generated validation scratch space is cleaner" in text
            and "not a scanner result, settlement update, rule signal, promotion cue, live-profitability evidence, bankroll guidance, or real-money evidence" in text,
            "cleanup_helper_safety_scope_present",
            "quickstart now states the validation cleanup helper's normal-use path, narrow --status-root scope, project-local lookalike / file-root refusal behavior, scratch-like symlink handling, and no-new-evidence boundary",
        ),
        require_contains(
            text,
            "10. **`run_daily_portfolio_observation.sh` wrapper or daily-wrapper fallback edit**\n   - `python3 validate_run_daily_portfolio_observation.py`\n   - Use this when the question is whether the wrapper's own structured fallback/rebuild guardrails changed, including the wrapper-generated `CURRENT_EVIDENCE_SUMMARY` refresh/placeholder contract, source-backed recommendation-context/open-row separation, settlement-audit-first current-evidence rebuild-order publication, and direct scorecard-sourced gate-boundary publication, and you want the leaf report that the broader operator/project rollups are supposed to inherit.",
            "daily_wrapper_leaf_guardrail_note_present",
            "quickstart now tells readers that the daily-wrapper validator is the leaf report to read when the wrapper's structured fallback/rebuild guardrails, wrapper-generated current-evidence recommendation-context/open-row separation, settlement-audit-first rebuild-order publication, or direct scorecard gate-boundary publication changed and the broader operator/project rollups are supposed to inherit that inventory",
        ),
        require_contains(
            text,
            "| `paper_trade_lane_summary.py` per-lane summary wording or placeholder / temp-write behavior | `python3 validate_paper_trade_lane_summary.py` | each lane summary keeps its full routed quick-files bundle, forward-check / lane-monitor / next-steps sections, lifted no-overpromotion decision-gate line, missing scan-output fallback context, missing scan-output fallback context, pipeline-recorded scanner-status base headlines, explicit recommender/logger pipeline-failure context, missing-base or missing-detail placeholders, and temp-write display path handling straight |",
            "lane_summary_row_present",
            "fast chooser includes a dedicated validator row for the per-lane summary surface instead of forcing that question through only the broader operator suite",
        ),
        require_contains(
            text,
            "| `OPS_HISTORY.md` rolling ops-log wording or day-bucket / takeaway logic | `python3 validate_paper_trade_ops_history.py` | the rolling ops-history layer keeps bet-ready, no-target, unknown-calendar, zero-hit, limited-coverage, hit-found / no-bet, explicit recommender/logger failure, missing scan-output artifact days, missing/empty/unreadable artifact issue days, and pipeline-recorded scanner-status issue days distinct, with the CSV and markdown surfaces pinned too |",
            "ops_history_row_present",
            "fast chooser includes a dedicated validator row for the rolling ops-history surface instead of forcing that question through only the broader operator suite",
        ),
        require_contains(
            text,
            "| `DAILY_ARTIFACT_GUIDE.md` wording or day-to-day repo-map guidance | `python3 validate_daily_artifact_guide.py` | the generated daily-use guide, including the scorecard-first research path, PAPER_TRADE_NOW-first operator path, the explicit issue-day sidecar-triage route, and validation-ladder routing |",
            "daily_guide_row_present",
            "fast chooser includes a dedicated validator row for the generated daily artifact guide and its repo-map guidance",
        ),
        require_contains(
            text,
            "| `PAPER_TRADE_USAGE.md` wording or operator runbook guidance | `python3 validate_paper_trade_usage.py` | the paper-trade runbook keeps the OP-anchor-first start path, the primary OP/CD paper-basket companion inside the primary basket, the separate Phase 8 shadow/watch routine, the current closest-challenger vs observation-only-pocket shadow split, the OP-anchor markdown/JSON provenance route with audit-only fingerprint boundary, the quiet-vs-broken cache-only / partial-cache evidence boundary, and the operator validator stack straight |",
            "paper_trade_usage_row_present",
            "fast chooser includes a dedicated validator row for the paper-trade operations runbook and now says that runbook also carries the primary OP/CD paper-basket companion versus separate Phase 8 shadow/watch distinction, the current closest-challenger vs observation-only-pocket shadow split, OP-anchor provenance route with audit-only fingerprint boundary, and quiet-vs-broken cache-only / partial-cache evidence boundary",
        ),
        require_contains(
            text,
            "| `COLE_STATUS_AND_PLAN.md` wording or main status-doc / repo-map guidance | `python3 validate_cole_status_and_plan.py` | the main status doc keeps the frozen posture, validation reading order, top repo-map paths, base API-access / HTTP 403 status-summary action-recheck route (`status_doc_base_api_access_route_documented`), and machine-readable status-map evidence boundary straight without treating a green status-doc check as forward evidence |",
            "cole_status_row_present",
            "fast chooser includes a dedicated validator row for the main status document, repo map, base API-access / HTTP 403 status-summary action-recheck route, and machine-readable status-map evidence boundary",
        ),
        require(
            "22. **`COLE_STATUS_AND_PLAN.md` main-status / repo-map edit**\n   - `python3 validate_cole_status_and_plan.py`\n   - Use this when the question is whether the main status map still points base API-access / HTTP 403 one-line status-summary edits to `validate_paper_trade_status_summary.py` before lane enrichment via `status_doc_base_api_access_route_documented`." in text
            and "Use `cole_status_and_plan_validation.md` when the question is whether the main status document still preserves the frozen posture, points cold readers at the right repo-map paths, and exposes `status_doc_base_api_access_route_documented` for base API-access / HTTP 403 status-summary route edits before lane enrichment." in text,
            "cole_status_api_access_route_read_order",
            "quickstart now tells readers to use the main status-doc validator when checking that the status map exposes the base API-access / HTTP 403 status-summary route before lane enrichment",
        ),
        require_contains(
            text,
            "| `WORKING_STATUS_REPORT_2026-04-15.md` demo-vs-production wording or dated live-demo evidence framing | `python3 validate_working_status_report.py` | the dated working-status note keeps the OP/CD production-basket distinction, the separate demo lane, the report-time Keeneland evidence anchor, and the mutable `latest_demo_run.json` alias straight |",
            "working_status_row_present",
            "fast chooser includes a dedicated working-status validator row for the dated live/demo-vs-production note",
        ),
        require_contains(
            text,
            "| `COLE_PRESENTATION_OUTLINE.md` deck wording or presentation-outline posture | `python3 validate_cole_presentation_outline.py` | the presentation outline keeps the frozen anchor, paper baseline, selector benchmark read, shadow-only Phase 8 stance, and method-family roles straight |",
            "presentation_outline_row_present",
            "fast chooser includes a dedicated presentation-outline validator row instead of hiding it inside the narrative sweep",
        ),
        require_contains(
            text,
            "| A broad change and you want one honest top-level answer | `python3 validate_project_surfaces.py` | the frozen evidence chain, the paper-trade operator suite, the narrative report-surface suite, the validation quickstart, the daily artifact guide, the direct current-hierarchy wording guardrail, the main status doc, and the paper-trade runbook together for one cross-layer alignment answer rather than new forward evidence by itself; the parent output fingerprints each child validation JSON and publishes a machine-readable evidence boundary for top-level reproducibility only |",
            "broad_change_row",
            "fast chooser now points broad changes to the top-level project sweep including the direct current-hierarchy wording guardrail, repo-navigation, main-status, and operator-runbook surfaces too, while saying that top-level answer is an alignment read rather than new forward evidence",
        ),
        require_contains(
            text,
            "3. **Main comparison report edit**\n   - `python3 validate_compare_main_approaches.py`\n   - Use this when the question is specifically Cole's one-screen read, the matched `compare_main_approaches.csv` / `.md` / `.json` bundle, the current OP/CD paper ladder, the evidence-class triage, the method-family evidence-debt checklist, the machine-readable evidence boundary, machine-readable `decision_change_gate_minimums`, or the evidence-scope decision-change gates.",
            "compare_main_ladder_step",
            "the escalation ladder now exposes the direct main-comparison validator before the broader frozen evidence-chain sweep, so report wording changes have a smallest matching check",
        ),
        require_contains(
            text,
            "   - After a settlement-audit -> current-bridge rebuild, validate the copied-current-paper fanout before quoting report-facing comparisons: frozen replay, downstream A/B, compare-main, OP-anchor, OP-family, cross-family, method-family, portfolio, selective-scope, scorecard audit, frozen evidence chain, report surfaces, and project surfaces; green rebuilds are drift prevention only, not evidence movement.",
            "current_bridge_fanout_ladder_step",
            "the escalation ladder now names the copied-current-paper fanout that should be checked after a settlement-audit to current-bridge rebuild before report-facing comparison surfaces are quoted",
        ),
        require_contains(
            text,
            "28. **Shareable wording / presentation / dated-report trust-path sweep**\n   - `python3 validate_report_surfaces.py`\n   - Use this when the question is whether the README, long-form report, working-status note, presentation outline, and shareable HTML report still align on the frozen story, the dated-report trust path, and the README-inherited wrapper-leaf source-of-truth note instead of flattening it away, with the report-surface JSON evidence boundary keeping that green narrative sweep out of the settled-ROI / live-profitability / promotion-readiness / real-money lane.",
            "report_surfaces_ladder_step",
            "the escalation ladder now makes the direct report-surfaces sweep explicit for shareable wording, presentation drift, the dated-report trust path, inherited README wrapper-note preservation, and the report-surface JSON evidence boundary question",
        ),
        require_contains(
            text,
            "python3 validate_frozen_evidence_chain.py\npython3 validate_paper_trade_operator_suite.py\npython3 validate_report_surfaces.py",
            "three_main_layers_command_set",
            "smallest useful command set still shows the three main layers separately",
        ),
        require_contains(
            text,
            "python3 validate_decision_cards_suite.py --reuse-existing-child-json\npython3 validate_frozen_evidence_chain.py --reuse-existing-child-json\npython3 validate_paper_trade_operator_suite.py --reuse-existing-child-json\npython3 validate_report_surfaces.py --reuse-existing-child-json\npython3 validate_project_surfaces.py --reuse-existing-child-json",
            "reuse_existing_child_json_command_set",
            "smallest useful command set now documents the artifact-reuse shortcut for parent rollups when child validator outputs are already fresh",
        ),
        require_contains(
            text,
            "Use that shortcut only when the underlying child validator outputs are already known-good for the current code/docs state.",
            "reuse_existing_child_json_guardrail",
            "quickstart keeps the guardrail that reuse mode is only honest when the child validator artifacts already match the current code and docs",
        ),
        require(
            scorecard_gates["source_snippet"] in text
            and scorecard_gates["anchor_displacement_min_roi_complete_settled_observations"] == 30
            and scorecard_gates["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and scorecard_gates["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and scorecard_gates["real_money_no_baq_as_bel_required"] is True,
            "quickstart_gate_source_matches_scorecard_json",
            "quickstart now names forward_evidence_scorecard.json decision_gate_minimums as the source for the 30-row anchor-review floor, 20-row Phase 8 review floor, and 100-row real-money-discussion floor while preserving the no-BAQ-as-BEL prerequisite and saying those floors are future ROI-complete paper-observation requirements rather than cleared gates",
        ),
        require_contains(
            text,
            "python3 validate_validation_quickstart.py\npython3 validate_daily_artifact_guide.py\npython3 validate_paper_trade_usage.py\npython3 validate_cole_status_and_plan.py",
            "navigation_command_set",
            "smallest useful command set now adds the quickstart, daily-guide, paper-trade-usage, and main-status validators when those repo-map surfaces changed",
        ),
        require_contains(
            text,
            "## Dated report / legacy-alias policy\n\nFor the shareable visual report, treat the dated HTML file as the source of truth:\n\n- `Superfecta_Project_Report_2026-04-15.html` is the validated trust anchor.",
            "dated_report_policy_html_anchor",
            "dated-report / legacy-alias policy still names the dated HTML file as the validated trust anchor",
        ),
        require_contains(
            text,
            "- `Superfecta_Project_Report_2026-04-15.pdf` is the preferred derivative export of that HTML surface.\n"
            "- `Superfecta_Project_Report.html` is only a legacy redirect alias to the dated HTML report, not a preferred or separately validated source artifact.\n"
            "- `Superfecta_Project_Report.pdf` is only a legacy undated alias, not a preferred or separately validated source artifact.\n"
            "- `Superfecta_Project_Report.docx` is only a legacy undated alias, not a preferred or separately validated source artifact.\n"
            "- `Superfecta Prediction - Quick Start Guide.pdf` is only a legacy quick-start alias; use `PAPER_TRADE_USAGE.md`, `DAILY_ARTIFACT_GUIDE.md`, and this validation quickstart instead.\n"
            "- `OpenClaw Prompt.docx` is only a historical prompt alias; use `COLE_STATUS_AND_PLAN.md`, `forward_evidence_scorecard.txt`, and the operator runbooks instead.\n"
            "- Use `python3 refresh_shareable_report_pdf.py --check-existing` to verify the existing dated PDF derivative through the HTML report validator without re-exporting it.\n"
            "- Use `python3 refresh_shareable_report_pdf.py` only when you intentionally need to regenerate the dated PDF derivative from the dated HTML trust anchor; the helper records HTML/PDF fingerprints and then reruns `python3 validate_superfecta_html_report.py`.\n"
            "- If the helper itself changed, run `python3 validate_refresh_shareable_report_pdf.py`; its green result is export reproducibility metadata only, not settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence.",
            "dated_report_policy_dated_pdf",
            "dated-report / legacy-alias policy still treats the dated PDF as the preferred derivative export and documents the check-existing / regenerate helper path as reproducibility metadata only",
        ),
        require_contains(
            text,
            "- `Superfecta_Project_Report.html` is only a legacy redirect alias to the dated HTML report, not a preferred or separately validated source artifact.",
            "html_policy_legacy_alias",
            "shareable-report policy now demotes the undated HTML alias to a redirect-only legacy surface rather than a primary artifact",
        ),
        require_contains(
            text,
            "- `Superfecta_Project_Report.pdf` is only a legacy undated alias, not a preferred or separately validated source artifact.",
            "dated_report_policy_pdf_legacy_alias",
            "dated-report / legacy-alias policy still demotes the undated PDF to a legacy alias rather than a primary surface",
        ),
        require_contains(
            text,
            "- the settlement-sync surface still keeps one-row-per-signal-key queue creation, preserved manual settlement fields, refreshed signal-owned metadata, blank and duplicate signal-key skips, blank settlement-key drops, and orphan settlement-row cleanup operationally distinct",
            "settlement_sync_green_read",
            "clean-green-read summary still says the settlement-sync surface remains operationally distinct across its key branches, including the three cleanup-count categories",
        ),
        require(
            "- the settlement-helper surface still keeps open-queue rendering, separate settled-row ROI-gap visibility including non-positive cost gaps, queue truncation, exact one-row updates, duplicate signal-key rejection, zero/non-positive actual-cost rejection, cost-source reporting, positive expected-cost fallback, supplied settled_ts validation, timestamp-omission ROI-gate warnings, true missing/malformed/non-positive-cost handling, and missing-signal failures operationally distinct" in text
            and "- the settlement-audit surface still keeps structural signal/settlement repairs, matched-key metadata mismatches, blank signal-key versus blank settlement-key repair labels, ROI-complete row counting, lane-specific sample gates, shadow per-rule review floors, and no-new-forward-evidence boundaries operationally distinct" in text,
            "settlement_helper_green_read",
            "clean-green-read summary still says the settlement-helper and settlement-audit surfaces remain operationally distinct across their key branches, including blank signal-key versus blank settlement-key repair labels",
        ),
        require_contains(
            text,
            "- `OP_REFINED_K7` remains the closest shadow-lane challenger, while `KEE_K9`, `SA_K9`, and `DMR_FALL_K7` remain observation-only pockets rather than near-promotion cases",
            "source_layer_green_read",
            "clean-green-read summary now keeps the shadow-lane closest-challenger vs observation-only-pocket split explicit instead of falling back to generic watch wording",
        ),
        require(
            "- OP-anchor source fingerprints remain exact input-byte provenance/reproducibility metadata, and OP-anchor `evidence_boundary_text` remains readable no-new-evidence boundary metadata only rather than settled ROI, promotion readiness, live profitability, or real-money evidence" in text
            and "- the current odds-only XGBoost path remains research-only and parked unless its evidence class changes materially" in text
            and "- the live-scan targeting / max-races limited-coverage validator stays discoverable when the question is whether capped scans spent detail attempts on OP/CD rule candidates, kept BAQ out of BEL targeting, and surfaced limited coverage as operational metadata rather than clean empty forward observation" in text
            and "- paper-trade empty-day, cache-miss, partial-cache, missing/empty/unreadable/invalid-shape artifact issue messaging, wrapper-level missing-status fallback, the frozen forward-check contract, and the compact lane-monitor surface remain operationally distinct, while green cache-only / partial-cache messaging checks prove cache-edge routing / reproducibility toward refresh or rerun only rather than quiet-day, scanner, ROI, profitability, promotion, or real-money evidence" in text,
            "xgboost_green_read",
            "clean-green-read summary now says OP-anchor source fingerprints are provenance-only metadata while OP-anchor evidence_boundary_text is readable no-new-evidence boundary metadata, the current odds-only XGBoost lane is parked unless its evidence class changes materially, the live-scan targeting / max-races limited-coverage route is discoverable as operational metadata, and green cache-only/partial-cache messaging checks remain cache-edge routing metadata rather than quiet-day or performance evidence",
        ),
        require_contains(
            text,
            "- `FULL_DATA_RETRAIN_ARTIFACTS.md` remains model-fit reproducibility metadata only: large full-data RMSE / MAE gains do not reopen XGBoost as a paper-trade path, promotion signal, live-profitability claim, bankroll guide, or real-money evidence",
            "full_data_retrain_green_read",
            "clean-green-read summary now keeps the full-data retrain artifact in the model-fit diagnostic lane instead of letting large RMSE / MAE gains reopen XGBoost as a paper-trade or live-profitability path",
        ),
        require_contains(
            text,
            "1. **Read `project_surfaces_validation.md` first**\n   - Use this for the one-line cross-layer answer: do the research story, the operator story, the human-facing report surfaces, the direct current hierarchy wording / structured-key guardrail, and the repo-navigation / main-status / operator-runbook surfaces still agree?",
            "broad_change_read_order_top",
            "broad-change reading order still starts from the top-level project sweep and now says the direct hierarchy guardrail, navigation, main-status, and operator-runbook surfaces are part of that answer",
        ),
        require(
            "2. **Read `forward_evidence_scorecard_validation.md` next when the question is specifically the rule ranking itself**\n   - Use this when the question is whether the scorecard CSV/text/JSON surfaces, CSV bootstrap-CI source-note columns, machine-readable `evidence_boundary`, `evidence_boundary_text`, `decision_gate_minimums`, per-rule bootstrap-CI source notes, and `PHASE7_REPORT.md` / `PHASE8_REPORT.md` report fingerprints still match the frozen anchor / paper / watch / dormant read.\n   - This is the right layer when the question is about scorecard ordering, evidence-boundary metadata, gate-minimum metadata, or whether the text summary drifted from the saved table." in text
            and "3. **Read `frozen_evidence_chain_validation.md` next when the question is research posture**\n   - Use this when you need to confirm the anchor / paper / watch / benchmark story behind the report-facing evidence stack as one rollup, including the forward-evidence scorecard layer, the main comparison layer, the full-data retrain diagnostic-only guardrail, and the narrow OP-anchor / downstream A/B / selective-scope guardrail validators." in text,
            "frozen_chain_read_order",
            "broad-change reading order now sends scorecard ranking, evidence-boundary metadata, decision-gate-minimum metadata, or bootstrap-CI source-note/report-fingerprint questions to the direct forward-evidence scorecard validation layer before widening to the frozen evidence-chain rollup, main comparison layer, and narrow comparison guardrails",
        ),
        require(
            "4. **Read the nearest comparison artifact validator when the question is narrow and already known**" in text
            and "Use `op_anchor_method_comparison_validation.md` when the question is specifically why `OP_DURABLE_K7` still leads Harville while the current odds-only XGBoost path stays parked unless its evidence class changes materially, whether OP-anchor JSON still carries readable `evidence_boundary_text`, or whether the OP-anchor markdown/JSON source fingerprints still prove exact input-byte provenance without implying settled ROI, promotion readiness, live profitability, or real-money evidence." in text,
            "narrow_comparison_read_order",
            "broad-change reading order now points narrow questions to the dedicated main comparison, OP, downstream A/B, and scope validators after the frozen evidence-chain layer, including the OP-anchor readable evidence_boundary_text route",
        ),
        require_contains(
            text,
            "- Use `compare_main_approaches_validation.md` when the question is specifically Cole's one-screen OP/CD paper read, evidence-class triage, method-family comparison, the machine-readable evidence boundary, machine-readable `decision_change_gate_minimums`, or evidence-scope decision-change gates in the main comparison report.",
            "compare_main_read_order",
            "broad-change reading order now points narrow main-report questions to the direct compare-main validator instead of forcing the broader frozen-evidence rollup first",
        ),
        require_contains(
            text,
            "- Use `cross_family_decision_validation.md` when the question is whether the anchor / paper / watch shortlist still carries the current-paper snapshot, including stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and the no OP-anchor / no cross-family-promotion evidence boundary.",
            "cross_family_current_paper_read_order",
            "broad-change reading order now points cross-family current-paper snapshot and CD-only promotion-boundary questions to the direct cross-family validator",
        ),
        require_contains(
            text,
            "- Use `ab_downstream_comparison_validation.md` when the question is specifically whether the enriched horse-history XGBoost downstream correction is promotion-worthy, whether the current-paper snapshot still keeps stale-card refresh routing / CD-only settled rows / source-published settlement-queue state/context / `current_evidence_summary.json.scorecard_audit_route` out of OP-anchor proof, whether the refresh-only maintenance route can republish current bridge / hierarchy / model fingerprints from saved A/B metrics, or whether the current workspace has the raw A/B rebuild inputs needed for full CLI JSON/markdown/stdout parity.",
            "ab_downstream_current_paper_read_order",
            "broad-change reading order now points downstream A/B current-paper snapshot, refresh-only maintenance, and CD-only OP-anchor-gap questions to the direct downstream A/B validator",
        ),
        require_contains(
            text,
            "- Use `full_data_retrain_artifacts_validation.md` when the question is specifically whether the full-data XGBoost retrain artifact still pins exact retrain/prediction commands while keeping RMSE / MAE gains in the model-fit diagnostic lane rather than paper-trade, promotion, live-profitability, bankroll, or real-money evidence.",
            "full_data_retrain_read_order",
            "broad-change reading order now points full-data retrain artifact, exact command, and model-fit-only boundary questions to the direct full-data retrain validator",
        ),
        require_contains(
            text,
            "- Use `compare_recommender_scope_paths_validation.md` when the question is specifically whether widened `--allow-all-combos` scope should change the current paper default, including whether the scorecard-sourced 30/20/100 gate read, no-BAQ-as-BEL prerequisite, `current_evidence_summary.json.scorecard_audit_route` synchronization route, `current_evidence_summary.json.rebuild_validation_contract` settlement-audit -> current-bridge -> bridge-validator route, and modeled stub-EV / off-scope ticket-share boundary are still visible.",
            "recommender_scope_read_order",
            "broad-change reading order now points widened-scope paper-default, gate-boundary, and modeled-EV/off-scope-ticket questions to the direct recommender-scope validator",
        ),
        require_contains(
            text,
            "   - Use this when the question is whether widened `--allow-all-combos` scope should change the current paper default, especially whether modeled EV lift is coming from off-scope tickets rather than observed settlement P&L.",
            "recommender_scope_modeled_ev_boundary_present",
            "quickstart now tells readers to use the direct scope validator for the modeled stub-EV / off-scope-ticket split instead of reading widened expected profit as observed P&L",
        ),
        require_contains(
            text,
            "6. **Read `paper_trade_now_validation.md` when the question is specifically the single top-card action or its text/markdown/JSON parity**\n   - Use this when the question is whether the one-line right-now card still points to the right next command and lane after settlement-first, decision-grade, cache-only, partial-cache, missing scan-output refresh, explicit recommender/logger pipeline-failure refresh, missing/empty/unreadable artifact recovery, or no-target days, while keeping `PAPER_TRADE_NOW.json` source-matched to `paper_trade_now.py --format json` unless the full helper failed into an explicit no-new-forward-evidence placeholder, explicit primary/shadow lane-context plus lane why-now lines, the full routed recommendation-lane quick-reads bundle, the live hierarchy block, and the stale-card inherited-snapshot honesty note intact.",
            "paper_trade_now_read_order",
            "broad-change reading order now exposes the direct validator for the single top-card operator action, including the text/markdown/JSON parity contract and stale-card inherited-snapshot honesty note",
        ),
        require_contains(
            text,
            "   - Read `current_evidence_summary_validation.md` when the question is the short report-ready bridge from frozen ranking to current paper status, including source consistency across `PAPER_TRADE_NOW`, settlement audit, and the timestamp-aware primary settlement CSV recompute, CSV settled_ts gap exclusion, the combined `operator_status_context` + `source_freshness` / `right_now_freshness_state` / `right_now_freshness_state_valid` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` route before stale or missing-state cards become today's instruction or evidence, `source_freshness.refresh_action_boundary` wrapper-refresh non-evidence routing, true no-BET recommendation-context wording that must not become open-row context, scanner/API-failure recommendation-context wording that must keep one specific operator boundary plus `Sidecar action: refresh_daily_wrapper_before_evidence_read` and `Recheck command: ./run_daily_portfolio_observation.sh`, the scorecard-sourced `scorecard_ci_only_promotion_check` for `OP_REFINED_K7` with `ci_only_promotion_allowed=false`, CD-only current rule mix, settlement queue state/by rule, bridge-published current gates, the `scorecard_audit_route` to `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks, and no-new-forward-evidence / no-promotion / no-real-money boundaries.",
            "current_evidence_summary_read_order",
            "broad-change reading order now exposes the direct current-evidence summary validator for the report-ready frozen-to-current bridge and its source-consistency / combined-operator-read-route / no-overclaim contract",
        ),
        require_contains(
            text,
            "7. **Read `run_daily_portfolio_observation_validation.md` when the question is specifically the real daily wrapper orchestration**\n   - Use this when the question is whether the shell entrypoint still stitches preflight, per-lane summaries, rolling ops history, the right-now card, `CURRENT_EVIDENCE_SUMMARY`, and the combined daily summary together honestly across cache misses, settle-first days, missing scan-output refresh days, explicit recommender/logger pipeline-error refresh days, helper failures, and placeholder fallbacks, while preserving saved primary/shadow recent-run context plus why-now lines when it has to fall back and keeping source-backed current-evidence recommendation-context/open-row separation plus settlement-audit-first rebuild-order publication explicit.",
            "daily_wrapper_read_order",
            "broad-change reading order now exposes the direct validator for the real daily wrapper orchestration layer plus its wrapper-generated current-evidence recommendation-context/open-row separation and settlement-audit-first rebuild-order contract",
        ),
        require_contains(
            text,
            "8. **Read `paper_trade_preflight_note_validation.md` when the question is specifically the shared calendar-note surface**\n   - Use this when the question is whether the direct preflight note still keeps active-target, no-target, API-unreachable, and explicit-error days straight across text and JSON outputs without collapsing unknown-calendar days into clean no-target messaging.",
            "preflight_note_read_order",
            "broad-change reading order now exposes the direct validator for the shared preflight-note surface",
        ),
        require_contains(
            text,
            "9. **Read `paper_trade_status_summary_validation.md` when the question is specifically the one-line base lane summary**\n   - Use this when the question is whether the pre-enrichment lane summary still keeps scanner-only alerts, bets-ready, clean-empty, partial-cache, cache-only-miss, missing-scan-output, scanner-failure, API-access / HTTP 403 action/recheck routing, stale-cache fallback count/kind/error visibility, empty/unreadable/invalid-shape scanner sidecars, pipeline-recorded empty/unreadable/invalid-shape scanner-status states, wrapper-only required-pipeline sidecar issues, recommender-failure, logger-failure, signals-without-bet, and no-readable-sidecars failure states straight across text and JSON paths, with API-access routes preserving `refresh_daily_wrapper_before_evidence_read` plus `./run_daily_portfolio_observation.sh` as operator context only and the saved human-facing recommender/logger failure line still carrying stage / error type / detail.",
            "status_summary_read_order",
            "broad-change reading order now exposes the direct validator for the one-line base lane summary surface, including API-access / HTTP 403 action-recheck route preservation plus stale-cache fallback metadata before lane enrichment",
        ),
        require_contains(
            text,
            "10. **Read `paper_trade_settlement_sync_validation.md` when the question is specifically the settlement-template sync surface**\n   - Use this when the question is whether the direct settlement sync helper still keeps stable empty headers, one open row per live `signal_key`, preserved manual settlement fields, refreshed signal-owned metadata like `scan_ts` and `expected_cost`, blank and duplicate signal-key skips, blank settlement-key drops, and orphan settlement-row cleanup straight through the real CLI.",
            "settlement_sync_read_order",
            "broad-change reading order now exposes the direct validator for the settlement-template sync surface, including the separated cleanup-count read",
        ),
        require_contains(
            text,
            "11. **Read `paper_trade_settlement_helper_validation.md` when the question is specifically the manual settlement-entry surface**\n   - Use this when the question is whether the direct settlement helper still keeps open-queue rendering, separate settled-row ROI-gap visibility including non-positive cost gaps, queue truncation, exact one-row updates, duplicate signal-key rejection before mutation, zero/non-positive actual-cost rejection, settlement cost-source reporting, positive expected-cost fallback for omitted actual cost, supplied settled_ts validation, timestamp-omission warnings that the row stays outside ROI-complete sample gates, true missing/malformed/non-positive-cost handling, computed profit, and missing-signal failures straight across text, markdown, and JSON outputs.\n   - Read `paper_trade_settlement_audit_validation.md` instead when the question is whether the ledger-completeness / ROI-coverage audit still keeps structural signal/settlement repairs, matched-key metadata mismatches, blank signal-key versus blank settlement-key repair labels, duplicate custom lane-name rejection before output artifacts, ROI-complete row counting, lane-specific sample gates, shadow per-rule review floors, and no-new-forward-evidence boundaries straight across markdown and JSON outputs.",
            "settlement_helper_read_order",
            "broad-change reading order now exposes the direct validator for the manual settlement-entry surface and points ledger-completeness / ROI-coverage audit questions to the direct settlement-audit validator",
        ),
        require_contains(
            text,
            "12. **Read `paper_trade_next_steps_validation.md` when the question is specifically the exact next-command surface**\n   - Use this when the question is whether the direct next-steps helper still keeps settlement-first, missing scan-output refresh-artifacts, API-access stale-cache fallback routing, rerun-live, limited-cache, explicit recommender/logger pipeline-failure recovery, waiting-for-first-settled, collecting-sample, and decision-grade-review states straight across JSON, text, and markdown paths, including the mixed-state latest-run context line.",
            "next_steps_read_order",
            "broad-change reading order now exposes the direct validator for the exact next-command surface",
        ),
        require_contains(
            text,
            "13. **Read `paper_trade_forward_check_validation.md` when the question is specifically the frozen-baseline forward assessment surface**\n   - Use this when the question is whether the direct forward check still keeps no-data, too-early, within-noise, running-cold, running-hot, missing-baseline, and no-overpromotion decision-gate states straight across JSON, text, and markdown paths, including recommendation-flow, ROI-fallback, ROI cost-source, and malformed `actual_cost` gap detail.",
            "forward_check_read_order",
            "broad-change reading order now exposes the direct validator for the frozen-baseline forward-check surface",
        ),
        require_contains(
            text,
            "14. **Read `paper_trade_lane_monitor_validation.md` when the question is specifically the compact per-lane monitor surface**\n   - Use this when the question is whether the compact lane monitor still keeps forward assessment, no-overpromotion decision-gate wording, open-settlement queue visibility, queue truncation, missing-baseline handling, and decision-grade ROI detail straight across JSON, text, and markdown paths.",
            "lane_monitor_read_order",
            "broad-change reading order now exposes the direct validator for the compact per-lane monitor surface",
        ),
        require_contains(
            text,
            "15. **Read `paper_trade_daily_summary_validation.md` when the question is specifically the combined daily-summary surface**\n   - Use this when the question is whether the direct daily summary still keeps its full routed quick-jump bundle, routed top-card focus/timing/freshness/ops snapshot, explicit primary/shadow recent-run context lines, explicit primary/shadow next-step state lines plus lifted no-overpromotion decision-gate snapshot lines, first-read and broader-review readiness lines, preflight context, primary-vs-shadow lane sections, artifacts-root line, explicit recommender/logger failure context, pipeline-recorded scanner-status issue lines, and explicit missing-preflight / missing-lane placeholders straight, with shadow review-readiness visible but not misread as live promotion.",
            "daily_summary_read_order",
            "broad-change reading order now exposes the direct validator for the combined daily-summary surface, including explicit next-step-state visibility and the no-live-promotion guardrail",
        ),
        require_contains(
            text,
            "16. **Read `paper_trade_lane_summary_validation.md` when the question is specifically the per-lane summary surface**\n   - Use this when the question is whether one lane `summary.txt` still keeps its full routed quick-files bundle, forward-check / lane-monitor / next-steps sections, lifted no-overpromotion decision-gate line, missing scan-output fallback context, missing scan-output fallback context, pipeline-recorded scanner-status base headlines, explicit recommender/logger pipeline-failure context, explicit missing-base or missing-detail placeholders, and temp-write display path handling straight.",
            "lane_summary_read_order",
            "broad-change reading order now exposes the direct validator for the per-lane summary surface",
        ),
        require_contains(
            text,
            "17. **Read `report_surfaces_validation.md` next when the question is shareable wording or presentation drift**\n   - Use this when you need to confirm the README, long-form report, working-status report, presentation outline, and HTML report are still telling the same frozen-story version, including the README-inherited wrapper-leaf source-of-truth note and the machine-readable evidence boundary that keeps a green narrative sweep separate from settled ROI, live profitability, promotion readiness, and real-money evidence.",
            "report_surface_read_order",
            "broad-change reading order still makes the narrative report-surface sweep discoverable after the narrow comparison layer, including the working-status note, presentation outline, README-inherited wrapper-leaf source-of-truth note, and report-surface evidence boundary",
        ),
        require_contains(
            text,
            "18. **Read `validation_quickstart_validation.md`, `daily_artifact_guide_validation.md`, `paper_trade_usage_validation.md`, and `cole_status_and_plan_validation.md` next when the question is repo navigation, the main status doc, or the operator runbook**",
            "navigation_read_order",
            "broad-change reading order now points repo-navigation, main-status, and operator-runbook questions to the quickstart, daily-guide, paper-trade-usage, and status-doc validators",
        ),
        require_contains(
            text,
            f"20. **Read the nearest direct source-layer paper-trade chain validator when the question is upstream scan -> recommend -> size -> log behavior**\n   - Use `paper_trade_source_chain_guardrails_validation.md` first when the question is whether the compact scan -> recommend -> size -> log matrix still source-matches all four direct validators plus their source/validator scripts, matrix generator/validator tooling, and validated matrix markdown/JSON artifact fingerprints, preserves the {source_chain_guardrails} guardrails across {source_chain_fixtures} fixture scenarios, renders markdown fingerprint tables exactly from the JSON sidecar, carries `current_evidence_summary.json.rebuild_validation_contract` before current totals are quoted, and stays operational-readiness-only rather than new forward evidence.\n   - Use `live_scan_targeting_and_limit_status_validation.md` when the question is whether capped live scans target OP/CD rule-candidate races before detail fetches, keep BAQ from being treated as BEL, and route max-races limited no-hit reads as operational limited coverage rather than clean empty forward observations.\n   - Use `scanner_sidecar_resolution_contract_validation.md` when the question is whether copied or moved scanner-status sidecars still follow the pipeline-declared `scanner_status_path` instead of a stale default `live_scan.status.json`, including missing declared sidecars and HTTP 403 action/recheck preservation.\n   - Use `paper_trade_pipeline_validation.md` when the question is whether the machine-readable pipeline status still keeps clean-empty reuse, malformed/invalid-shape/zero-byte/missing reused scan fallbacks, missing and zero-byte reused scan fallbacks with empty/readable/unreadable sidecar provenance, malformed/invalid-shape reused scan fallbacks with empty/readable/unreadable sidecar provenance, bets-ready reuse, scanner-failure and missing-output fallback with explicit empty-scan fallback metadata, scanner-failure stale-scan overwrite protection, empty/unreadable scanner-status sidecars, partial-cache activity, signals-logged-no-bet runs, and the scorecard-sourced 30/20/100 gate boundary distinct.\n   - Use `paper_trade_recommender_validation.md` when the question is whether the direct recommender still keeps the default selective Phase 7 combo universe narrow, leaves off-universe-only races as honest `NO BET` rows, degrades missing-race-id scanner hits and malformed prediction files into explicit `ERROR` rows, and preserves the scorecard-sourced 30/20/100 gate boundary without treating reused-prediction fixtures as settled evidence.\n   - Use `ev_ticket_engine_validation.md` when the question is whether the EV sizing layer still rejects empty, negative-edge, low-probability, and under-minimum-stake cases conservatively while sizing only the top positive-EV tickets inside bankroll caps and preserving the scorecard-sourced 30/20/100 gate boundary without treating stake-sizing fixtures as settled evidence.\n   - Use `paper_trade_logger_validation.md` when the question is whether the persistent ledgers still create stable headers, append serialized payload rows, dedup prior `signal_key` values, ignore blank recommendation keys safely, and keep the scorecard-sourced 30/20/100 gate boundary visible as ledger-layer metadata only.",
            "source_layer_read_order",
            "broad-change reading order now exposes the direct source-layer paper-trade chain matrix plus individual validators for upstream scan-to-log and copied-sidecar questions",
        ),
        require_contains(
            text,
            "The top-level suites and the navigation / narrow comparison / source-layer validators now follow the same basic pattern:",
            "shared_report_pattern_wording",
            "quickstart now includes the source-layer paper-trade chain validators in its shared-report pattern wording",
        ),
        require_contains(
            text,
            "- OP-family decision validator:\n  - `out/status_validation/op_family_decision/op_family_decision_validation.md`",
            "op_family_output_path_documented",
            "output locations now document the validation artifact for the direct OP-family decision validator",
        ),
        require_contains(
            text,
            "- Cross-family decision validator:\n  - `out/status_validation/cross_family_decision/cross_family_decision_validation.md`",
            "cross_family_output_path_documented",
            "output locations now document the validation artifact for the direct cross-family decision validator",
        ),
        require_contains(
            text,
            "- Portfolio decision validator:\n  - `out/status_validation/portfolio_decision_card/portfolio_decision_card_validation.md`",
            "portfolio_decision_output_path_documented",
            "output locations now document the validation artifact for the direct portfolio decision validator",
        ),
        require_contains(
            text,
            "- Method-family decision validator:\n  - `out/status_validation/method_family_decision_card/method_family_decision_card_validation.md`",
            "method_family_output_path_documented",
            "output locations now document the validation artifact for the direct method-family decision validator",
        ),
        require_contains(
            text,
            "- Main comparison report validator:\n  - `out/status_validation/compare_main_approaches/compare_main_approaches_validation.md`",
            "compare_main_output_path_documented",
            "output locations now document the validation artifact for the direct main-comparison report validator",
        ),
        require_contains(
            text,
            "- Frozen portfolio replay caution validator:\n  - `out/status_validation/frozen_portfolio_eval_caution/frozen_portfolio_eval_caution_validation.md`",
            "frozen_portfolio_eval_output_path_documented",
            "output locations now document the validation artifact for the direct frozen portfolio replay caution validator",
        ),
        require_contains(
            text,
            "- Phase 8 legacy-report caution validator:\n  - `out/status_validation/phase8_report_caution/phase8_report_caution_validation.md`",
            "phase8_report_output_path_documented",
            "output locations now document the validation artifact for the direct Phase 8 legacy-report caution validator",
        ),
        require_contains(
            text,
            "- Full-data retrain artifact validator:\n  - `out/status_validation/full_data_retrain_artifacts/full_data_retrain_artifacts_validation.md`",
            "full_data_retrain_output_path_documented",
            "output locations now document the validation artifact for the direct full-data retrain artifact validator",
        ),
        require_contains(
            text,
            "- Paper-trade pipeline validator:\n  - `out/status_validation/paper_trade_pipeline/paper_trade_pipeline_validation.md`",
            "paper_trade_pipeline_output_path_documented",
            "output locations now document the validation artifact for the direct paper-trade pipeline validator",
        ),
        require_contains(
            text,
            "- Paper-trade recommender validator:\n  - `out/status_validation/paper_trade_recommender/paper_trade_recommender_validation.md`",
            "paper_trade_recommender_output_path_documented",
            "output locations now document the validation artifact for the direct paper-trade recommender validator",
        ),
        require_contains(
            text,
            "- EV ticket engine validator:\n  - `out/status_validation/ev_ticket_engine/ev_ticket_engine_validation.md`",
            "ev_ticket_engine_output_path_documented",
            "output locations now document the validation artifact for the direct EV ticket engine validator",
        ),
        require_contains(
            text,
            "- Paper-trade logger validator:\n  - `out/status_validation/paper_trade_logger/paper_trade_logger_validation.md`",
            "paper_trade_logger_output_path_documented",
            "output locations now document the validation artifact for the direct paper-trade logger validator",
        ),
        require_contains(
            text,
            "- Paper-trade source-chain guardrail matrix validator:\n  - `out/status_validation/paper_trade_source_chain_guardrails/paper_trade_source_chain_guardrails_validation.md`\n- Live scan targeting / limited-coverage status validator:\n  - `out/status_validation/live_scan_targeting_and_limit_status/live_scan_targeting_and_limit_status_validation.md`\n- Scanner sidecar resolution contract validator:\n  - `out/status_validation/scanner_sidecar_resolution_contract/scanner_sidecar_resolution_contract_validation.md`",
            "paper_trade_source_chain_output_path_documented",
            "output locations now document the compact source-chain guardrail matrix validator, direct live-scan targeting / max-races limited-coverage validator, and scanner-sidecar resolution contract validator",
        ),
        require_contains(
            text,
            "- Paper-trade right-now validator:\n  - `out/status_validation/paper_trade_now/paper_trade_now_validation.md`",
            "paper_trade_now_output_path_documented",
            "output locations now document the validation artifact for the direct right-now validator",
        ),
        require_contains(
            text,
            "- Current evidence summary validator:\n  - `out/status_validation/current_evidence_summary/current_evidence_summary_validation.md`",
            "current_evidence_summary_output_path_documented",
            "output locations document the validation artifact for the current-evidence bridge validator",
        ),
        require_contains(
            text,
            "- Current hierarchy language validator:\n  - `out/status_validation/current_hierarchy_language/current_hierarchy_language_validation.md`",
            "current_hierarchy_output_path_documented",
            "output locations now document the validation artifact for the direct current hierarchy wording / structured-key compatibility validator",
        ),
        require_contains(
            text,
            "- Daily wrapper validator:\n  - `out/status_validation/run_daily_portfolio_observation/run_daily_portfolio_observation_validation.md`",
            "daily_wrapper_output_path_documented",
            "output locations now document the validation artifact for the direct daily-wrapper validator",
        ),
        require_contains(
            text,
            "- Paper-trade preflight-note validator:\n  - `out/status_validation/paper_trade_preflight_note/paper_trade_preflight_note_validation.md`",
            "preflight_note_output_path_documented",
            "output locations now document the validation artifact for the direct preflight-note validator",
        ),
        require_contains(
            text,
            "- Paper-trade status-summary validator:\n  - `out/status_validation/paper_trade_status_summary/paper_trade_status_summary_validation.md`",
            "status_summary_output_path_documented",
            "output locations now document the validation artifact for the direct one-line base lane summary validator",
        ),
        require_contains(
            text,
            "- Paper-trade settlement-sync validator:\n  - `out/status_validation/paper_trade_settlement_sync/paper_trade_settlement_sync_validation.md`",
            "settlement_sync_output_path_documented",
            "output locations now document the validation artifact for the direct settlement-template sync validator",
        ),
        require(
            "- Paper-trade settlement-helper validator:\n  - `out/status_validation/paper_trade_settlement_helper/paper_trade_settlement_helper_validation.md`" in text
            and "- Paper-trade settlement-audit validator:\n  - `out/status_validation/paper_trade_settlement_audit/paper_trade_settlement_audit_validation.md`" in text,
            "settlement_helper_output_path_documented",
            "output locations now document the validation artifacts for the direct settlement-helper and settlement-audit validators",
        ),
        require_contains(
            text,
            "- Paper-trade next-steps validator:\n  - `out/status_validation/paper_trade_next_steps/paper_trade_next_steps_validation.md`",
            "next_steps_output_path_documented",
            "output locations now document the validation artifact for the direct next-steps validator",
        ),
        require_contains(
            text,
            "- Paper-trade forward-check validator:\n  - `out/status_validation/paper_trade_forward_check/paper_trade_forward_check_validation.md`",
            "forward_check_output_path_documented",
            "output locations now document the validation artifact for the direct frozen-baseline forward-check validator",
        ),
        require_contains(
            text,
            "- Paper-trade lane-monitor validator:\n  - `out/status_validation/paper_trade_lane_monitor/paper_trade_lane_monitor_validation.md`",
            "lane_monitor_output_path_documented",
            "output locations now document the validation artifact for the direct compact per-lane monitor validator",
        ),
        require_contains(
            text,
            "- Paper-trade daily-summary validator:\n  - `out/status_validation/paper_trade_daily_summary/paper_trade_daily_summary_validation.md`",
            "daily_summary_output_path_documented",
            "output locations now document the validation artifact for the direct combined daily-summary validator",
        ),
        require_contains(
            text,
            "- Paper-trade lane-summary validator:\n  - `out/status_validation/paper_trade_lane_summary/paper_trade_lane_summary_validation.md`",
            "lane_summary_output_path_documented",
            "output locations now document the validation artifact for the direct per-lane summary validator",
        ),
        require_contains(
            text,
            "- Paper-trade ops-history validator:\n  - `out/status_validation/paper_trade_ops_history/paper_trade_ops_history_validation.md`",
            "ops_history_output_path_documented",
            "output locations now document the validation artifact for the direct rolling ops-history validator",
        ),
        require_contains(
            text,
            "- Validation quickstart validator:\n  - `out/status_validation/validation_quickstart/validation_quickstart_validation.md`",
            "quickstart_output_path_documented",
            "output locations now document the validation artifact for the quickstart validator itself",
        ),
        require_paths_exist(
            [
                "validate_decision_cards_suite.py",
                "validate_op_family_decision.py",
                "validate_cross_family_decision.py",
                "validate_portfolio_decision_card.py",
                "validate_method_family_decision_card.py",
                "validate_forward_evidence_scorecard.py",
                "validate_compare_main_approaches.py",
                "validate_frozen_evidence_chain.py",
                "validate_frozen_portfolio_eval_caution.py",
                "validate_phase8_report_caution.py",
                "validate_op_anchor_method_comparison.py",
                "validate_ab_downstream_comparison.py",
                "validate_full_data_retrain_artifacts.py",
                "validate_compare_recommender_scope_paths.py",
                "validate_paper_trade_pipeline.py",
                "validate_paper_trade_recommender.py",
                "validate_ev_ticket_engine.py",
                "validate_paper_trade_logger.py",
                "validate_paper_trade_source_chain_guardrails.py",
                "validate_live_scan_targeting_and_limit_status.py",
                "validate_scanner_sidecar_resolution_contract.py",
                "validate_paper_trade_operator_suite.py",
                "validate_refresh_live_paper_trade_surfaces.py",
                "validate_paper_trade_now.py",
                "validate_current_evidence_summary.py",
                "validate_current_hierarchy_language.py",
                "validate_run_daily_portfolio_observation.py",
                "validate_paper_trade_preflight_note.py",
                "validate_paper_trade_status_summary.py",
                "validate_paper_trade_settlement_sync.py",
                "validate_paper_trade_settlement_helper.py",
                "validate_paper_trade_settlement_audit.py",
                "validate_paper_trade_next_steps.py",
                "validate_paper_trade_forward_check.py",
                "validate_paper_trade_lane_monitor.py",
                "validate_paper_trade_daily_summary.py",
                "validate_paper_trade_lane_summary.py",
                "validate_paper_trade_ops_history.py",
                "validate_daily_artifact_guide.py",
                "validate_paper_trade_usage.py",
                "validate_cole_status_and_plan.py",
                "validate_readme_current_status.py",
                "validate_cole_full_report.py",
                "validate_working_status_report.py",
                "validate_cole_presentation_outline.py",
                "validate_superfecta_html_report.py",
                "validate_report_surfaces.py",
                "validate_refresh_shareable_report_pdf.py",
                "validate_project_surfaces.py",
                "validate_validation_quickstart.py",
                "validate_validation_scratch_cleanup.py",
            ],
            "referenced_validator_scripts_exist",
            "all validator scripts referenced by the quickstart currently exist on disk",
        ),
        require_paths_exist(
            [
                "PAPER_TRADE_NOW.md",
                "CURRENT_EVIDENCE_SUMMARY.md",
                "current_evidence_summary.json",
                "current_evidence_summary.py",
                "OPS_HISTORY.md",
                "DAILY_ARTIFACT_GUIDE.md",
                "PAPER_TRADE_USAGE.md",
                "COLE_STATUS_AND_PLAN.md",
                "README.md",
                "COLE_FULL_REPORT_2026-04-15.md",
                "WORKING_STATUS_REPORT_2026-04-15.md",
                "COLE_PRESENTATION_OUTLINE.md",
                "Superfecta_Project_Report_2026-04-15.html",
                "Superfecta_Project_Report_2026-04-15.pdf",
                "Superfecta_Project_Report.docx",
                "Superfecta Prediction - Quick Start Guide.pdf",
                "OpenClaw Prompt.docx",
                "VALIDATION_QUICKSTART.md",
                "compare_main_approaches.md",
                "FROZEN_PORTFOLIO_EVAL.md",
                "PHASE8_REPORT.md",
                "FULL_DATA_RETRAIN_ARTIFACTS.md",
                "forward_evidence_scorecard.txt",
                "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.md",
                "PAPER_TRADE_SOURCE_CHAIN_GUARDRAILS.json",
                "refresh_live_paper_trade_surfaces.py",
                "refresh_shareable_report_pdf.py",
                "validation_scratch_cleanup.py",
            ],
            "referenced_human_facing_artifacts_exist",
            "the main human-facing files and helper scripts named directly in the quickstart currently exist on disk, so the runbook is not pointing at stale filenames",
        ),
        require(
            EVIDENCE_BOUNDARY.get("artifact_role") == "validation quickstart / validator-routing runbook"
            and EVIDENCE_BOUNDARY.get("not_new_forward_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_settled_roi_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_live_profitability_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_real_money_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_promotion_readiness_evidence") is True
            and EVIDENCE_BOUNDARY.get("quickstart_validator_passes_are_navigation_metadata_only") is True
            and "ROI-complete settled paper rows" in EVIDENCE_BOUNDARY.get("stronger_forward_confidence_requires", [])
            and "do not promote OP_REFINED_K7 or Phase 8 from navigation validation cleanliness" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "do not substitute BAQ for BEL" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and EVIDENCE_BOUNDARY.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}" in text
            and "machine-readable evidence boundary for navigation/read-order reproducibility" in text,
            "validation_quickstart_json_publishes_machine_readable_evidence_boundary",
            f"quickstart validator JSON now publishes valid_evidence_scope={VALID_EVIDENCE_SCOPE} plus a machine-readable evidence_boundary block that keeps validator-routing cleanliness, documented output paths, and reuse-guardrail coverage separate from settled ROI, live profitability, promotion readiness, real-money evidence, OP_REFINED_K7 / Phase 8 promotion, odds-only XGBoost reopening, and BAQ/BEL substitution",
        ),
        require_output_paths_exist(
            [
                "out/status_validation/decision_cards_suite/decision_cards_suite_validation.md",
                "out/status_validation/op_family_decision/op_family_decision_validation.md",
                "out/status_validation/cross_family_decision/cross_family_decision_validation.md",
                "out/status_validation/portfolio_decision_card/portfolio_decision_card_validation.md",
                "out/status_validation/method_family_decision_card/method_family_decision_card_validation.md",
                "out/status_validation/forward_evidence_scorecard/forward_evidence_scorecard_validation.md",
                "out/status_validation/compare_main_approaches/compare_main_approaches_validation.md",
                "out/status_validation/frozen_evidence_chain/frozen_evidence_chain_validation.md",
                "out/status_validation/frozen_portfolio_eval_caution/frozen_portfolio_eval_caution_validation.md",
                "out/status_validation/phase8_report_caution/phase8_report_caution_validation.md",
                "out/status_validation/op_anchor_method_comparison/op_anchor_method_comparison_validation.md",
                "out/status_validation/ab_downstream_comparison/ab_downstream_comparison_validation.md",
                "out/status_validation/full_data_retrain_artifacts/full_data_retrain_artifacts_validation.md",
                "out/status_validation/compare_recommender_scope_paths/compare_recommender_scope_paths_validation.md",
                "out/status_validation/paper_trade_pipeline/paper_trade_pipeline_validation.md",
                "out/status_validation/paper_trade_recommender/paper_trade_recommender_validation.md",
                "out/status_validation/ev_ticket_engine/ev_ticket_engine_validation.md",
                "out/status_validation/paper_trade_logger/paper_trade_logger_validation.md",
                "out/status_validation/paper_trade_source_chain_guardrails/paper_trade_source_chain_guardrails_validation.md",
                "out/status_validation/live_scan_targeting_and_limit_status/live_scan_targeting_and_limit_status_validation.md",
                "out/status_validation/scanner_sidecar_resolution_contract/scanner_sidecar_resolution_contract_validation.md",
                "out/status_validation/paper_trade_operator_suite/paper_trade_operator_suite_validation.md",
                "out/status_validation/refresh_live_paper_trade_surfaces/refresh_live_paper_trade_surfaces_validation.md",
                "out/status_validation/paper_trade_now/paper_trade_now_validation.md",
                "out/status_validation/current_evidence_summary/current_evidence_summary_validation.md",
                "out/status_validation/current_hierarchy_language/current_hierarchy_language_validation.md",
                "out/status_validation/run_daily_portfolio_observation/run_daily_portfolio_observation_validation.md",
                "out/status_validation/paper_trade_preflight_note/paper_trade_preflight_note_validation.md",
                "out/status_validation/paper_trade_status_summary/paper_trade_status_summary_validation.md",
                "out/status_validation/paper_trade_settlement_sync/paper_trade_settlement_sync_validation.md",
                "out/status_validation/paper_trade_settlement_helper/paper_trade_settlement_helper_validation.md",
                "out/status_validation/paper_trade_settlement_audit/paper_trade_settlement_audit_validation.md",
                "out/status_validation/paper_trade_next_steps/paper_trade_next_steps_validation.md",
                "out/status_validation/paper_trade_forward_check/paper_trade_forward_check_validation.md",
                "out/status_validation/paper_trade_lane_monitor/paper_trade_lane_monitor_validation.md",
                "out/status_validation/paper_trade_daily_summary/paper_trade_daily_summary_validation.md",
                "out/status_validation/paper_trade_lane_summary/paper_trade_lane_summary_validation.md",
                "out/status_validation/paper_trade_ops_history/paper_trade_ops_history_validation.md",
                "out/status_validation/daily_artifact_guide/daily_artifact_guide_validation.md",
                "out/status_validation/paper_trade_usage/paper_trade_usage_validation.md",
                "out/status_validation/cole_status_and_plan/cole_status_and_plan_validation.md",
                "out/status_validation/readme_current_status/readme_current_status_validation.md",
                "out/status_validation/cole_full_report/cole_full_report_validation.md",
                "out/status_validation/working_status_report/working_status_report_validation.md",
                "out/status_validation/cole_presentation_outline/cole_presentation_outline_validation.md",
                "out/status_validation/superfecta_html_report/superfecta_html_report_validation.md",
                "out/status_validation/shareable_report_pdf_export/shareable_report_pdf_export.md",
                "out/status_validation/refresh_shareable_report_pdf/refresh_shareable_report_pdf_validation.md",
                "out/status_validation/report_surfaces/report_surfaces_validation.md",
                "out/status_validation/validation_quickstart/validation_quickstart_validation.md",
                "out/status_validation/validation_scratch_cleanup/validation_scratch_cleanup_validation.md",
                "out/status_validation/project_surfaces/project_surfaces_validation.md",
            ],
            "documented_output_paths_exist",
            "the documented output paths listed in the quickstart currently exist on disk",
        ),
    ]


def build_summary(
    checks: list[dict[str, Any]],
    scorecard_gates: dict[str, Any],
    source_chain_context: dict[str, Any],
    ci_only_context: dict[str, Any],
    operator_read_gate: dict[str, Any],
    scorecard_audit_route: dict[str, Any],
    current_bridge_rebuild_contract: dict[str, Any],
) -> dict[str, Any]:
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    return {
        "suite_status": status,
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": {
            key: value for key, value in scorecard_gates.items() if key != "source_snippet"
        },
        "source_chain_guardrail_matrix_read": source_chain_context,
        "current_evidence_scorecard_ci_only_read": ci_only_context,
        "current_evidence_operator_read_gate_read": operator_read_gate,
        "current_evidence_scorecard_audit_route_read": scorecard_audit_route,
        "current_evidence_rebuild_validation_contract_read": current_bridge_rebuild_contract,
        "summary": {
            "suite_read": (
                "quickstart still routes broad changes to project surfaces, now includes the direct current-hierarchy wording guardrail plus the repo-navigation, main-status, and operator-runbook surfaces in that top-level sweep, now says the single decision-card sweep is a frozen-evidence ordering check rather than new forward proof, treats the frozen evidence chain as including the scorecard layer plus the main comparison layer plus the direct frozen-portfolio replay caution/metadata-sidecar validator, the full-data retrain diagnostic-only guardrail, and the narrow OP, downstream A/B, and scope-comparison guardrail validators while framing that research-side parent as an alignment sweep rather than new forward evidence with child validation JSON fingerprints and a machine-readable evidence boundary published as reproducibility metadata only, keeps the direct scorecard row explicit that its saved CSV/text/JSON surfaces carry the frozen source-scope / non-live-evidence CSV boundary, machine-readable JSON `evidence_boundary` plus `evidence_boundary_text`, bootstrap-CI source notes plus PHASE7/PHASE8 report fingerprints, and named machine-readable `decision_gate_minimums` for `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100` settled-observation gates, exposes the dedicated main-comparison validator route for Cole's one-screen OP/CD read, matched CSV/markdown/JSON bundle, current paper ladder, method-family evidence-debt checklist, Harville benchmark-only lane, odds-only XGBoost research-only lane, BEL-not-BAQ caution, source-provenance sidecar, machine-readable evidence_boundary metadata, named machine-readable `decision_change_gate_minimums` for `anchor_displacement=30`, `phase8_promotion_review=20`, and `real_money_discussion=100` settled-observation gates, and evidence-scope decision gates, keeps the current shadow-lane triage explicit in the front-door guidance too by naming OP_REFINED_K7 as the closest challenger while KEE_K9 / SA_K9 / DMR_FALL_K7 stay observation-only pockets, exposes the direct frozen-portfolio replay caution validator so `FROZEN_PORTFOLIO_EVAL.md` keeps historical replay P&L separated from live paper-trade, real-money, or live-profitability evidence and routes current top-card quotes through the combined operator_status_context/source_freshness/operator_read_gate route plus current_evidence_summary.json.rebuild_validation_contract before use, exposes the direct Phase 8 legacy-report caution validator so the old full-sample headline remains demoted by the current holdout-over-headline / no-real-money / BAQ-is-not-BEL banner, now also describes the dedicated OP-anchor comparison validator as an evidence-class guardrail with readable `evidence_boundary_text`, markdown/JSON source-byte provenance, and a parked odds-only XGBoost reopening bar, exposes the dedicated OP, downstream A/B, scope-comparison validator with scorecard-sourced 30/20/100 gate and no-BAQ boundary, main-comparison, source-layer paper-trade source-chain matrix plus live-scan targeting / max-races limited-coverage validator plus pipeline / recommender / EV-sizing / logger, plus scanner-sidecar path-resolution for copied-sidecar masking risks, broader operator-suite, paper-trade-now, current-evidence summary route for source-consistency plus CSV settled_ts gap exclusion plus the combined operator_status_context/source_freshness/operator_read_gate route and right_now_freshness_state validity before stale or missing-state PAPER_TRADE_NOW best-action cards become today's instruction or evidence, plus true no-BET recommendation-context wording plus source_freshness.refresh_action_boundary wrapper-refresh non-evidence routing as operator-readiness metadata, current-hierarchy-language, daily-wrapper route for `CURRENT_EVIDENCE_SUMMARY` refresh/placeholder plus source-backed recommendation-context/open-row separation, preflight-note, status-summary, settlement-sync, settlement-helper, settlement-audit, next-steps, forward-check, lane-monitor, daily-summary, lane-summary, ops-history, working-status, presentation-outline, daily-guide, paper-trade-usage, status-doc, and report-surfaces validators, with the paper-trade-usage route now also carrying the primary OP/CD paper-basket companion versus separate Phase 8 shadow/watch distinction, the OP-anchor markdown/JSON provenance plus readable-boundary route, audit-only fingerprint / boundary-text boundary, and quiet-vs-broken cache-only / partial-cache evidence boundary, with the broader operator route now explicitly covering preserved primary/shadow recent-run context across the top card, combined daily summary, wrapper fallbacks, and saved-live refresh rebuilds, plus right-now text/markdown/JSON parity or explicit helper-failure JSON placeholder behavior, split-aware saved-preflight-JSON fallback when the sibling text note is missing or blank, green cache-only / partial-cache checks proving cache-edge routing / reproducibility toward refresh or rerun only rather than quiet-day, scanner, ROI, profitability, promotion, or real-money evidence, the routed preflight-note source-path contract, the wrapper leaves' inherited guardrail inventories that the broader operator/project rollups are supposed to preserve, the operator-suite machine-readable evidence boundary keeping parent operator passes separate from settled ROI / live profitability / promotion readiness / real-money evidence, and the explicit stale-snapshot note so inherited lane context / counts / quick reads do not masquerade as current state, the report-surfaces route now also explicitly carrying shareable wording, presentation drift, the dated-report trust path, the README-inherited wrapper-leaf source-of-truth note rather than flattening it away, and the report-surface evidence boundary keeping green narrative validation separate from settled ROI / live profitability / promotion readiness / real-money evidence, the direct daily-guide route now also explicitly calling out the issue-day sidecar-triage path from PAPER_TRADE_NOW into the direct pipeline/scanner pointers, the direct daily-summary route now explicitly covering primary/shadow recent-run context and next-step-state visibility without implying live promotion, the direct status-summary route now explicitly covering missing-scan-output fallbacks, API-access stale-cache fallback metadata, empty/unreadable and pipeline-recorded scanner-status states plus the saved human-facing recommender/logger failure detail line, the saved-live refresh route now explicitly covering matched PAPER_TRADE_NOW text/markdown/JSON rebuilds with JSON parity, rebuilt daily summaries inheriting refreshed top-level routed top-card snapshot lines while stale rebuilt top cards keep the inherited-snapshot honesty note, while saying that rerendering persisted surfaces is not new forward evidence and whether `--as-of-date` was actually applied or skipped, and now says a fresh source-chain matrix should propagate through the operator suite's embedded `auxiliary_source_chain_matrix` plus parent-side matrix-payload rebuild parity, with the project sweep reading that as readiness-only parent metadata rather than a flattened generic operator green light, keeps the direct live-scan targeting / max-races limited-coverage route visible as scanner/pipeline/status/ops guardrail metadata only, and the top-level project sweep now explicitly reads as one cross-layer alignment answer rather than new forward evidence with the direct current-hierarchy child plus child validation JSON fingerprints and a machine-readable evidence_boundary published as top-level reproducibility metadata only, "
                "direct status-summary issue-day routing now names invalid-shape scanner sidecars, pipeline-recorded invalid-shape scanner-status states, wrapper-only invalid-shape required-pipeline sidecars, API-access stale-cache fallback metadata, and API-access / HTTP 403 action-recheck route preservation as operational issue branches before lane enrichment, "
                "and the current-evidence route now also names the combined current_evidence_summary.json operator_status_context/source_freshness/operator_read_gate path as refresh-before-instruction/evidence-read routing before stale or missing-state right-now cards become today's instruction or evidence, while keeping that route out of no-target, clean-empty, bet-readiness, settled-ROI, forward-performance, promotion, live-profitability, bankroll, and real-money evidence, "
                "and the current-evidence route now also names the scorecard-sourced OP_REFINED CI-only diagnostic from forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7 with ci_only_promotion_allowed=false, "
                "and the current-evidence route now also names current_evidence_summary.json scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus validate_scorecard_ranking_contract_audit.py as gate/ranking/CI-only/timezone/no-BAQ synchronization metadata only, "
                "and the current-evidence route now also publishes current_evidence_summary.json rebuild_validation_contract as the settlement-audit -> current-bridge -> current-bridge-validator order after scorecard/rules/signals/settlement-ledger byte changes, while the source-chain matrix now carries that same rebuild route before current totals are quoted, "
                "while the saved navigation/runbook guides and their direct validator report paths stay pinned across the quickstart ladder, the downstream A/B route now also carries the current-paper bridge snapshot / CD-only OP-anchor-gap caveat as validator-routing metadata rather than model-promotion evidence, the full-data XGBoost retrain artifact route now points exact retrain/prediction command and RMSE / MAE model-fit boundary questions to validate_full_data_retrain_artifacts.py as model-fit reproducibility metadata only rather than paper-trade / live-profitability / promotion / bankroll / real-money evidence, the cross-family current-paper snapshot route for stale-card refresh / CD-only settled rows / no cross-family-promotion evidence is pinned to the direct cross-family validator, the quickstart gate-source note now reads forward_evidence_scorecard.json decision_gate_minimums directly and preserves anchor_displacement=30, phase8_promotion_review=20, real_money_discussion=100, and the no-BAQ-as-BEL prerequisite as future paper-observation floors rather than cleared gates, the status-doc row preserves its machine-readable status-map evidence boundary and named status_doc_base_api_access_route_documented route as alignment metadata rather than forward evidence, the quickstart validator JSON itself now publishes a machine-readable evidence_boundary as navigation/read-order reproducibility metadata only rather than settled ROI / live profitability / promotion readiness / real-money evidence, keeps the dated HTML trust anchor plus dated PDF derivative export explicit while the undated HTML/PDF/DOCX report aliases, old quick-start PDF, and historical OpenClaw prompt DOCX stay legacy aliases, documents the shareable PDF check-existing / regenerate helper path as export reproducibility metadata only rather than settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence, documents a disk-space preflight for temp-heavy project-local scratch validators so no-space/temp-file failures are routed to operational cleanup and rerun rather than evidence changes, now says the validation scratch cleanup helper publishes valid_evidence_scope=validation_scratch_cleanup_operational_hygiene_only plus a 512 MiB low-disk warning threshold, before/after below-threshold fields, estimated post-cleanup free space, and a scratch-cleanup insufficiency flag, says the cleanup validator should remove its own generated fixture root after checks while publishing the same valid scope, and states the validation cleanup helper's normal-use path, narrow --status-root scope, lookalike/file-root refusal behavior, scratch-like symlink handling, and no-new-evidence boundary"
                f", and the quickstart validator/report surfaces now expose `valid_evidence_scope={VALID_EVIDENCE_SCOPE}` as navigation-contract metadata only"
            )
        },
    }


def write_outputs(summary: dict[str, Any], out_dir: Path = OUT_DIR) -> None:
    out_md = out_dir / MD_PATH.name
    out_json = out_dir / JSON_PATH.name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    scorecard_gates = summary["scorecard_decision_gate_minimums_read"]

    lines: list[str] = [
        "# Validation Quickstart Validation",
        "",
        "This report checks that `VALIDATION_QUICKSTART.md` still points to the right validators, the broader operator-suite route, direct source-layer routes, parent-rollup reuse shortcut guardrails, documented output paths, and the dated-report / legacy-alias policy.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Target file: `{DOC.name}`",
        f"- Checks: {summary['check_count']}",
        f"- Result: {summary['suite_status'].upper()}",
        "",
        "## Checks",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]

    for check in summary["checks"]:
        lines.append(f"| {check['check']} | {check['status'].upper()} | {check['detail']} |")

    lines.extend(
        [
            "",
            "## Current Read",
            "",
            f"- {summary['summary']['suite_read']}",
            "",
            "## Evidence Boundary",
            "",
            f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
            f"- valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
            f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
            f"- Scorecard gate source: `{scorecard_gates['source']}` `{scorecard_gates['source_path']}` (`anchor_displacement={scorecard_gates['anchor_displacement_min_roi_complete_settled_observations']}`, `phase8_promotion_review={scorecard_gates['phase8_promotion_review_min_roi_complete_settled_observations']}`, `real_money_discussion={scorecard_gates['real_money_discussion_min_total_settled_observations_with_usable_roi']}`)",
            "- Not new forward evidence; not a live paper-trade ledger; not current-day scanner evidence; not settled ROI; not live-profitability evidence; not real-money evidence; not promotion-readiness evidence.",
            "- Quickstart validator passes are navigation/read-order metadata only.",
            f"- Stronger forward confidence still requires: {', '.join(EVIDENCE_BOUNDARY['stronger_forward_confidence_requires'])}.",
            f"- Non-goals: {', '.join(EVIDENCE_BOUNDARY['non_goals'])}.",
            "",
            "## Bottom Line",
            "",
            "If this validator stays green, `VALIDATION_QUICKSTART.md` remains the fastest front-door read for choosing the smallest honest validator path — including the direct report-surfaces route for shareable wording / presentation drift / dated-report trust-path questions, the direct operator/report leaf routes, and the parent-rollup reuse guardrails.",
            "That green read is navigation/read-order alignment, not new forward evidence by itself; the machine-readable boundary keeps it out of the settled-ROI / live-profitability / promotion-readiness / real-money lane.",
        ]
    )

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    text = load_text(DOC)
    scorecard_gates = scorecard_gate_context(args.scorecard_json)
    source_chain_context = source_chain_guardrail_context()
    ci_only_context = scorecard_ci_only_context(args.scorecard_json, args.current_evidence_json)
    operator_read_gate = operator_read_gate_context(args.current_evidence_json)
    scorecard_audit_route = scorecard_audit_route_context(args.current_evidence_json)
    current_bridge_rebuild_contract = current_bridge_rebuild_contract_context(args.current_evidence_json)
    checks = build_checks(
        text,
        scorecard_gates,
        source_chain_context,
        ci_only_context,
        operator_read_gate,
        scorecard_audit_route,
        current_bridge_rebuild_contract,
    )
    if Path(args.scorecard_json).resolve() == SCORECARD_JSON.resolve():
        checks = scorecard_gate_cli_contract_checks(args.scorecard_json, args.current_evidence_json) + checks
    if Path(args.current_evidence_json).resolve() == CURRENT_EVIDENCE_JSON.resolve():
        checks = current_bridge_rebuild_cli_contract_checks(args.current_evidence_json) + checks
    summary = build_summary(
        checks,
        scorecard_gates,
        source_chain_context,
        ci_only_context,
        operator_read_gate,
        scorecard_audit_route,
        current_bridge_rebuild_contract,
    )
    out_dir = Path(args.out_dir)
    write_outputs(summary, out_dir)
    print(f"Wrote {out_dir / MD_PATH.name}")
    print(f"Wrote {out_dir / JSON_PATH.name}")
    return 0 if summary["suite_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
