#!/usr/bin/env python3
"""Validate SCORECARD_RANKING_CONTRACT_AUDIT artifacts."""
from __future__ import annotations

import json
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import scorecard_ranking_contract_audit as audit

BASE = Path(__file__).resolve().parent
MD_OUTPUT = BASE / "SCORECARD_RANKING_CONTRACT_AUDIT.md"
JSON_OUTPUT = BASE / "scorecard_ranking_contract_audit.json"
OUT_DIR = BASE / "out" / "status_validation" / "scorecard_ranking_contract_audit"
VALIDATION_MD = OUT_DIR / "scorecard_ranking_contract_audit_validation.md"
VALIDATION_JSON = OUT_DIR / "scorecard_ranking_contract_audit_validation.json"
TMP_PARENT = OUT_DIR / "_tmp"
GENERATED_AT_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d{2}:\d{2}) (?P<tz>UTC|CET|CEST)$"
)
REPORT_TIMEZONES = {
    "UTC": timezone.utc,
    "CET": timezone(timedelta(hours=1), "CET"),
    "CEST": timezone(timedelta(hours=2), "CEST"),
}


def rebuild_command_for(generated_at: str) -> str:
    return f"python3 scorecard_ranking_contract_audit.py --generated-at '{generated_at}'"


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    return {"check": name, "status": "pass" if condition else "fail", "detail": detail}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_report_generated_at(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    match = GENERATED_AT_RE.match(value)
    if not match:
        return None
    try:
        parsed = datetime.strptime(f"{match.group('date')} {match.group('time')}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    return parsed.replace(tzinfo=REPORT_TIMEZONES[match.group("tz")])


def strip_code_cell(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        return value[1:-1]
    return value


def fingerprint_path(path_text: str) -> dict[str, Any]:
    path = BASE / path_text
    if not path.exists():
        return {"path": path_text, "bytes": 0, "sha256": None}
    data = path.read_bytes()
    return {
        "path": path_text,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def prepare_tmp_parent() -> Path:
    """Use project-local scratch space so CLI fixture writes avoid system temp quotas."""
    if TMP_PARENT.exists():
        shutil.rmtree(TMP_PARENT)
    TMP_PARENT.mkdir(parents=True, exist_ok=True)
    return TMP_PARENT


def parse_surface_inventory(md_text: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    in_table = False
    for line in md_text.splitlines():
        if line == "| Status | Surface | Kind | Role | Path | Bytes | SHA-256 | Issue summary |":
            in_table = True
            continue
        if not in_table:
            continue
        if line.startswith("|---"):
            continue
        if not line.startswith("|"):
            break
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) != 8:
            raise AssertionError(f"unexpected surface inventory row shape: {line}")
        status, name, kind, role, path, byte_text, sha256, issues = parts
        name = strip_code_cell(name)
        path = strip_code_cell(path)
        sha256 = strip_code_cell(sha256)
        rows[name] = {
            "status": status,
            "name": name,
            "kind": kind,
            "role": role,
            "path": path,
            "bytes": int(byte_text),
            "sha256": None if sha256 == "n/a" else sha256,
            "issues": issues,
        }
    if not rows:
        raise AssertionError("surface inventory table was not found or had no rows")
    return rows


def main() -> int:
    tmp_parent = prepare_tmp_parent()
    scratch = {
        "tmp_parent": str(tmp_parent),
        "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
        "tmp_parent_cleared_before_fixture_run": True,
    }
    saved_payload = read_json(JSON_OUTPUT)
    saved_md = MD_OUTPUT.read_text(encoding="utf-8")
    rebuild_command = rebuild_command_for(saved_payload["generated_at"])
    fresh_payload = audit.build_payload(generated_at=saved_payload["generated_at"])
    fresh_md = audit.render_markdown(fresh_payload)
    contract = audit.load_scorecard_contract(audit.SCORECARD_JSON)
    ci_only_diagnostic = audit.load_scorecard_ci_only_diagnostic(audit.SCORECARD_JSON)
    decision_gate_minimums = audit.load_scorecard_decision_gate_minimums(audit.SCORECARD_JSON)
    rows_by_name = {row["name"]: row for row in saved_payload["rows"]}

    checks: list[dict[str, Any]] = []
    checks.append(
        require(
            saved_payload == fresh_payload and saved_md == fresh_md,
            "saved_artifacts_match_fresh_rebuild",
            "saved scorecard ranking-contract audit markdown/JSON match a fresh in-process rebuild at the saved timestamp",
        )
    )
    checks.append(
        require(
            rebuild_command.endswith(f"--generated-at '{saved_payload['generated_at']}'"),
            "rebuild_command_matches_saved_timestamp",
            "validation output publishes the exact saved generated_at timestamp instead of a stale fixed rebuild command",
        )
    )
    parsed_generated_at = parse_report_generated_at(saved_payload.get("generated_at"))
    checks.append(
        require(
            parsed_generated_at is not None
            and parsed_generated_at.utcoffset() is not None
            and f"Generated: {saved_payload['generated_at']}" in saved_md,
            "generated_at_has_explicit_timezone_label",
            "scorecard ranking-contract audit generated_at is a parseable report timestamp with an explicit timezone label, and the markdown mirrors the JSON timestamp exactly",
        )
    )
    checks.append(
        require(
            saved_payload["suite_status"] == "pass"
            and saved_payload["row_count"]
            == (
                len(audit.TEXT_SURFACES)
                + len(audit.CI_ONLY_TEXT_SURFACES)
                + len(audit.JSON_CONTRACT_SURFACES)
                + len(audit.JSON_CI_ONLY_SURFACES)
                + len(audit.JSON_SCORECARD_AUDIT_ROUTE_SURFACES)
                + len(audit.JSON_REBUILD_VALIDATION_CONTRACT_SURFACES)
            )
            and saved_payload["pass_count"] == saved_payload["row_count"]
            and saved_payload["fail_count"] == 0,
            "all_expected_surfaces_pass",
            "every configured text and JSON contract/CI-only surface carries the scorecard tier-first ranking contract, source-matched OP_REFINED CI-only diagnostic, scorecard-audit route, or current bridge rebuild order",
        )
    )
    checks.append(
        require(
            saved_payload["scorecard_ranking_contract"] == contract
            and saved_payload["known_rank_override"] == contract["known_rank_override"]
            and contract["rank_is_tier_first_decision_order"] is True
            and contract["forward_trust_is_secondary_within_tier"] is True
            and contract["raw_score_is_not_an_automatic_deployment_instruction"] is True
            and "CD_CORE_K8 ranks ahead of OP_REFINED_K7" in contract["known_rank_override"],
            "source_contract_pinned",
            "audit source contract matches forward_evidence_scorecard.json and preserves the CD_CORE_K8-over-OP_REFINED_K7 tier-first override",
        )
    )
    checks.append(
        require(
            saved_payload["scorecard_ci_only_diagnostic"] == ci_only_diagnostic
            and saved_payload["scorecard_ci_only_diagnostic_source"]
            == "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7"
            and ci_only_diagnostic["candidate_rule_id"] == "OP_REFINED_K7"
            and ci_only_diagnostic["current_anchor_rule_id"] == "OP_DURABLE_K7"
            and ci_only_diagnostic["ci_only_promotion_allowed"] is False
            and ci_only_diagnostic["positive_ci_lower_bound_is_support_context"] is True
            and "CI-Only Diagnostic Source" in saved_md
            and "ci_only_promotion_allowed: `false`" in saved_md,
            "source_ci_only_diagnostic_pinned",
            "audit source CI-only diagnostic matches forward_evidence_scorecard.json and keeps OP_REFINED_K7 positive-CI support out of promotion readiness",
        )
    )
    boundary_metadata = saved_payload.get("evidence_boundary_metadata", {})
    checks.append(
        require(
            saved_payload["decision_gate_minimums"] == decision_gate_minimums
            and saved_payload["decision_gate_minimums_source"] == "forward_evidence_scorecard.json:decision_gate_minimums"
            and isinstance(boundary_metadata, dict)
            and saved_payload.get("valid_evidence_scope") == audit.SCORECARD_AUDIT_VALID_EVIDENCE_SCOPE
            and saved_payload.get("evidence_boundary", {}).get("valid_evidence_scope") == audit.SCORECARD_AUDIT_VALID_EVIDENCE_SCOPE
            and boundary_metadata.get("valid_evidence_scope") == audit.SCORECARD_AUDIT_VALID_EVIDENCE_SCOPE
            and boundary_metadata.get("decision_gate_minimums_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and boundary_metadata.get("decision_gate_minimums") == decision_gate_minimums
            and boundary_metadata.get("decision_gate_minimums_are_future_paper_observation_floors") is True
            and boundary_metadata.get("ci_only_coverage_does_not_clear_promotion_or_anchor_gates") is True
            and boundary_metadata.get("validator_cleanliness_does_not_clear_gates") is True
            and boundary_metadata.get("no_baq_as_bel_prerequisite_preserved") is True
            and boundary_metadata.get("not_promotion_readiness_evidence") is True
            and boundary_metadata.get("not_real_money_evidence") is True
            and saved_payload["decision_gate_minimums"]["anchor_displacement"]["min_roi_complete_settled_observations"] == 30
            and saved_payload["decision_gate_minimums"]["phase8_promotion_review"]["min_roi_complete_settled_observations"] == 20
            and saved_payload["decision_gate_minimums"]["real_money_discussion"]["min_total_settled_observations_with_usable_roi"] == 100
            and "no BAQ-as-BEL substitution"
            in saved_payload["decision_gate_minimums"]["real_money_discussion"]["also_requires"]
            and "Decision Gate Minimums" in saved_md
            and "anchor_displacement: `30` ROI-complete same-candidate settled observations" in saved_md
            and "phase8_promotion_review: `20` ROI-complete candidate shadow observations" in saved_md
            and "real_money_discussion: `100` total settled observations with usable ROI" in saved_md
            and "This audit does not clear them." in saved_md,
            "source_decision_gate_minimums_pinned",
            "audit output now copies the scorecard-sourced 30/20/100 gate floors plus the no-BAQ-as-BEL prerequisite and source valid_evidence_scope into machine-readable boundary metadata and markdown without treating audit cleanliness as promotion or real-money evidence",
        )
    )
    checks.append(
        require(
            all(rows_by_name[name]["status"] == "pass" for name in [
                "forward_evidence_scorecard_text",
                "compare_main_approaches_markdown",
                "op_anchor_method_comparison_markdown",
                "op_family_decision_markdown",
                "cross_family_decision_markdown",
                "portfolio_decision_markdown",
                "method_family_decision_markdown",
            ])
            and all(rows_by_name[name]["kind"] == "text" for name in [
                "forward_evidence_scorecard_text",
                "compare_main_approaches_markdown",
                "op_anchor_method_comparison_markdown",
                "op_family_decision_markdown",
                "cross_family_decision_markdown",
                "portfolio_decision_markdown",
                "method_family_decision_markdown",
            ]),
            "text_surfaces_inventory",
            "audit verifies the scorecard text plus all report-facing comparison/card markdown surfaces that mention OP_DURABLE, CD_CORE, OP_REFINED, Phase 7, Phase 8, Harville, or XGBoost hierarchy context",
        )
    )
    checks.append(
        require(
            all(rows_by_name[name]["status"] == "pass" for name in [
                "forward_evidence_scorecard_text_ci_only",
                "compare_main_approaches_markdown_ci_only",
                "op_anchor_method_comparison_markdown_ci_only",
                "op_family_decision_markdown_ci_only",
                "cross_family_decision_markdown_ci_only",
                "portfolio_decision_markdown_ci_only",
                "method_family_decision_markdown_ci_only",
                "current_evidence_summary_markdown_ci_only",
                "paper_trade_usage_markdown_ci_only",
                "validation_quickstart_markdown_ci_only",
                "daily_artifact_guide_markdown_ci_only",
                "cole_full_report_markdown_ci_only",
                "cole_presentation_outline_markdown_ci_only",
                "superfecta_html_report_ci_only",
            ])
            and all(rows_by_name[name]["kind"] == "text" for name in [
                "forward_evidence_scorecard_text_ci_only",
                "compare_main_approaches_markdown_ci_only",
                "op_anchor_method_comparison_markdown_ci_only",
                "op_family_decision_markdown_ci_only",
                "cross_family_decision_markdown_ci_only",
                "portfolio_decision_markdown_ci_only",
                "method_family_decision_markdown_ci_only",
                "current_evidence_summary_markdown_ci_only",
                "paper_trade_usage_markdown_ci_only",
                "validation_quickstart_markdown_ci_only",
                "daily_artifact_guide_markdown_ci_only",
                "cole_full_report_markdown_ci_only",
                "cole_presentation_outline_markdown_ci_only",
                "superfecta_html_report_ci_only",
            ]),
            "text_ci_only_surfaces_inventory",
            "audit verifies scorecard, comparison/card, current-evidence, runbook, quickstart, daily-guide, cold-read narrative report markdown, and shareable HTML surfaces carry the OP_REFINED CI-only diagnostic source path and ci_only_promotion_allowed=false boundary",
        )
    )
    checks.append(
        require(
            all(rows_by_name[name]["status"] == "pass" for name in [
                "forward_evidence_scorecard_json",
                "compare_main_approaches_json",
                "op_anchor_method_comparison_json",
                "op_family_decision_validation_json",
                "cross_family_decision_validation_json",
                "portfolio_decision_card_validation_json",
                "method_family_decision_card_validation_json",
                "decision_cards_suite_validation_json",
                "frozen_decision_stack_validation_json",
            ])
            and all(rows_by_name[name]["contract_matches_source"] is True for name in [
                "forward_evidence_scorecard_json",
                "compare_main_approaches_json",
                "op_anchor_method_comparison_json",
                "op_family_decision_validation_json",
                "cross_family_decision_validation_json",
                "portfolio_decision_card_validation_json",
                "method_family_decision_card_validation_json",
                "decision_cards_suite_validation_json",
                "frozen_decision_stack_validation_json",
            ]),
            "json_contract_surfaces_inventory",
            "audit verifies JSON sidecars, direct decision-card validator payloads, and rollup validations copy the exact scorecard ranking_contract rather than merely repeating similar text",
        )
    )
    checks.append(
        require(
            all(rows_by_name[name]["status"] == "pass" for name in [
                "forward_evidence_scorecard_json_ci_only",
                "compare_main_approaches_json_ci_only",
                "op_anchor_method_comparison_json_ci_only",
                "current_evidence_summary_json_ci_only",
                "op_family_decision_validation_json_ci_only",
                "cross_family_decision_validation_json_ci_only",
                "portfolio_decision_card_validation_json_ci_only",
                "method_family_decision_card_validation_json_ci_only",
                "superfecta_html_report_validation_json_ci_only",
            ])
            and all(rows_by_name[name]["diagnostic_matches_source"] is True for name in [
                "forward_evidence_scorecard_json_ci_only",
                "compare_main_approaches_json_ci_only",
                "op_anchor_method_comparison_json_ci_only",
                "current_evidence_summary_json_ci_only",
                "op_family_decision_validation_json_ci_only",
                "cross_family_decision_validation_json_ci_only",
                "portfolio_decision_card_validation_json_ci_only",
                "method_family_decision_card_validation_json_ci_only",
                "superfecta_html_report_validation_json_ci_only",
            ]),
            "json_ci_only_surfaces_inventory",
            "audit verifies scorecard JSON, comparison sidecars, current-evidence JSON, direct decision-card validator payloads, and the shareable HTML report validator payload copy the exact OP_REFINED CI-only diagnostic rather than merely repeating similar text",
        )
    )
    checks.append(
        require(
            rows_by_name["current_evidence_summary_json_scorecard_audit_route"]["status"] == "pass"
            and rows_by_name["current_evidence_summary_json_scorecard_audit_route"]["kind"] == "json_scorecard_audit_route"
            and rows_by_name["current_evidence_summary_json_scorecard_audit_route"]["route_path"] == "scorecard_audit_route"
            and rows_by_name["current_evidence_summary_json_scorecard_audit_route"]["route_matches_scorecard_gate_minimums"] is True
            and rows_by_name["current_evidence_summary_json_scorecard_audit_route"]["referenced_markdown_path"] == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and rows_by_name["current_evidence_summary_json_scorecard_audit_route"]["referenced_json_path"] == "scorecard_ranking_contract_audit.json"
            and rows_by_name["current_evidence_summary_json_scorecard_audit_route"]["referenced_markdown_path_is_audit_output"] is True
            and rows_by_name["current_evidence_summary_json_scorecard_audit_route"]["referenced_json_path_is_audit_output"] is True
            and rows_by_name["current_evidence_summary_json_scorecard_audit_route"]["referenced_markdown_exists"] is True
            and rows_by_name["current_evidence_summary_json_scorecard_audit_route"]["referenced_json_exists_or_is_current_output"] is True
            and rows_by_name["current_evidence_summary_json_scorecard_audit_route"]["referenced_route_artifacts_verified_on_disk"] is True,
            "json_scorecard_audit_route_surface_inventory",
            "audit verifies current_evidence_summary.json scorecard_audit_route points back to the scorecard audit with source-matched 30/20/100 gate floors, no-BAQ-as-BEL prerequisite, validator command, artifact paths, on-disk route artifact verification, and non-evidence flags",
        )
    )
    scorecard_route_row = rows_by_name["current_evidence_summary_json_scorecard_audit_route"]
    checks.append(
        require(
            scorecard_route_row["route_matches_expected_contract"] is True
            and scorecard_route_row["route_field_contract_matches_expected"] is True
            and scorecard_route_row["route_field_contract_mismatches"] == []
            and scorecard_route_row["route_gate_floor_snapshot_matches_source"] is True
            and scorecard_route_row["route_validator_command_matches_contract"] is True
            and scorecard_route_row["route_valid_use_matches_contract"] is True
            and scorecard_route_row["route_non_evidence_flags_match_contract"] is True
            and scorecard_route_row["route_read_required_phrases_present"] is True
            and scorecard_route_row["route_read_missing_phrases"] == []
            and scorecard_route_row["referenced_route_artifacts_verified_on_disk"] is True,
            "json_scorecard_audit_route_structured_diagnostics",
            "audit row now publishes separate machine-readable diagnostics for bridge-route field contract, copied gate floors, validator command, synchronization-only valid-use, non-evidence flags, route-read phrases, and referenced artifact verification instead of only a broad route pass/fail",
        )
    )
    scorecard_route_diagnostics = {
        "source_row": "current_evidence_summary_json_scorecard_audit_route",
        "source_path": scorecard_route_row["path"],
        "route_path": scorecard_route_row["route_path"],
        "route_matches_expected_contract": scorecard_route_row["route_matches_expected_contract"],
        "route_field_contract_matches_expected": scorecard_route_row["route_field_contract_matches_expected"],
        "route_field_contract_mismatches": scorecard_route_row["route_field_contract_mismatches"],
        "route_gate_floor_snapshot_matches_source": scorecard_route_row["route_gate_floor_snapshot_matches_source"],
        "route_validator_command_matches_contract": scorecard_route_row["route_validator_command_matches_contract"],
        "route_valid_use_matches_contract": scorecard_route_row["route_valid_use_matches_contract"],
        "route_non_evidence_flags_match_contract": scorecard_route_row["route_non_evidence_flags_match_contract"],
        "route_read_required_phrases_present": scorecard_route_row["route_read_required_phrases_present"],
        "route_read_missing_phrases": scorecard_route_row["route_read_missing_phrases"],
        "referenced_route_artifacts_verified_on_disk": scorecard_route_row["referenced_route_artifacts_verified_on_disk"],
    }
    rebuild_contract_row = rows_by_name["current_evidence_summary_json_rebuild_validation_contract"]
    checks.append(
        require(
            rebuild_contract_row["status"] == "pass"
            and rebuild_contract_row["kind"] == "json_rebuild_validation_contract"
            and rebuild_contract_row["contract_path"] == "rebuild_validation_contract"
            and rebuild_contract_row["expected_upstream_refresh_order_commands"] == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and rebuild_contract_row["observed_upstream_refresh_order_commands"]
            == rebuild_contract_row["expected_upstream_refresh_order_commands"]
            and rebuild_contract_row["upstream_refresh_order_commands_match_expected"] is True
            and rebuild_contract_row["contract_matches_expected"] is True
            and rebuild_contract_row["contract_field_mismatches"] == []
            and rebuild_contract_row["requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"] is True
            and rebuild_contract_row["required_non_evidence_flags_match_contract"] is True
            and rebuild_contract_row["upstream_refresh_order_valid_use_matches_contract"] is True
            and rebuild_contract_row["direct_validation_command_matches_contract"] is True,
            "json_rebuild_validation_contract_surface_inventory",
            "audit verifies current_evidence_summary.json rebuild_validation_contract preserves the settlement-audit -> current-bridge -> bridge-validator order before quoting current totals after source-byte changes",
        )
    )
    rebuild_contract_diagnostics = {
        "source_row": "current_evidence_summary_json_rebuild_validation_contract",
        "source_path": rebuild_contract_row["path"],
        "contract_path": rebuild_contract_row["contract_path"],
        "expected_upstream_refresh_order_commands": rebuild_contract_row[
            "expected_upstream_refresh_order_commands"
        ],
        "observed_upstream_refresh_order_commands": rebuild_contract_row[
            "observed_upstream_refresh_order_commands"
        ],
        "upstream_refresh_order_commands_match_expected": rebuild_contract_row[
            "upstream_refresh_order_commands_match_expected"
        ],
        "contract_matches_expected": rebuild_contract_row["contract_matches_expected"],
        "contract_field_mismatches": rebuild_contract_row["contract_field_mismatches"],
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": rebuild_contract_row[
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
        ],
        "required_non_evidence_flags_match_contract": rebuild_contract_row[
            "required_non_evidence_flags_match_contract"
        ],
        "upstream_refresh_order_valid_use_matches_contract": rebuild_contract_row[
            "upstream_refresh_order_valid_use_matches_contract"
        ],
        "direct_validation_command_matches_contract": rebuild_contract_row[
            "direct_validation_command_matches_contract"
        ],
    }
    checks.append(
        require(
            rebuild_contract_diagnostics["upstream_refresh_order_commands_match_expected"] is True
            and rebuild_contract_diagnostics["contract_matches_expected"] is True
            and rebuild_contract_diagnostics["contract_field_mismatches"] == []
            and rebuild_contract_diagnostics[
                "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
            ]
            is True
            and rebuild_contract_diagnostics["required_non_evidence_flags_match_contract"] is True
            and rebuild_contract_diagnostics["upstream_refresh_order_valid_use_matches_contract"] is True
            and rebuild_contract_diagnostics["direct_validation_command_matches_contract"] is True,
            "json_rebuild_validation_contract_diagnostics_payload_published",
            "direct validation JSON now exports a compact rebuild_validation_contract_diagnostics payload so parent rollups can verify the bridge rebuild order without parsing audit rows",
        )
    )
    checks.append(
        require(
            scorecard_route_diagnostics["route_matches_expected_contract"] is True
            and scorecard_route_diagnostics["route_field_contract_matches_expected"] is True
            and scorecard_route_diagnostics["route_field_contract_mismatches"] == []
            and scorecard_route_diagnostics["route_gate_floor_snapshot_matches_source"] is True
            and scorecard_route_diagnostics["route_validator_command_matches_contract"] is True
            and scorecard_route_diagnostics["route_valid_use_matches_contract"] is True
            and scorecard_route_diagnostics["route_non_evidence_flags_match_contract"] is True
            and scorecard_route_diagnostics["route_read_required_phrases_present"] is True
            and scorecard_route_diagnostics["route_read_missing_phrases"] == []
            and scorecard_route_diagnostics["referenced_route_artifacts_verified_on_disk"] is True,
            "json_scorecard_audit_route_diagnostics_payload_published",
            "direct validation JSON now exports a compact scorecard_audit_route_diagnostics payload so parent rollups can verify bridge-route health without parsing the audit artifact row table",
        )
    )
    parsed_inventory = parse_surface_inventory(saved_md)
    checks.append(
        require(
            set(parsed_inventory) == set(rows_by_name)
            and all(
                parsed_inventory[name]["status"] == row["status"]
                and parsed_inventory[name]["kind"] == row["kind"]
                and parsed_inventory[name]["role"] == row["role"]
                and parsed_inventory[name]["path"] == row["path"]
                and parsed_inventory[name]["bytes"] == row["bytes"]
                and parsed_inventory[name]["sha256"] == row["sha256"]
                and row["source_fingerprint"] == fingerprint_path(row["path"])
                for name, row in rows_by_name.items()
            ),
            "surface_inventory_markdown_matches_json_and_disk",
            "markdown surface inventory path/byte/hash rows match scorecard_ranking_contract_audit.json and current disk fingerprints for every audited text/JSON surface",
        )
    )
    checks.append(
        require(
            "This audit only checks whether report-facing surfaces carry the frozen scorecard ranking semantics and OP_REFINED CI-only diagnostic" in saved_md
            and f"valid_evidence_scope={audit.SCORECARD_AUDIT_VALID_EVIDENCE_SCOPE}" in saved_md
            and "new forward evidence, settled ROI, promotion readiness, live profitability, or real-money evidence" in saved_md
            and saved_payload["evidence_boundary"] == audit.EVIDENCE_BOUNDARY
            and saved_payload["valid_evidence_scope"] == audit.SCORECARD_AUDIT_VALID_EVIDENCE_SCOPE
            and saved_payload["evidence_boundary"]["valid_evidence_scope"] == audit.SCORECARD_AUDIT_VALID_EVIDENCE_SCOPE
            and saved_payload["evidence_boundary"]["not_promotion_readiness_evidence"] is True
            and saved_payload["evidence_boundary"]["not_real_money_evidence"] is True,
            "evidence_boundary_present",
            "audit output publishes the exact valid_evidence_scope line and says it is synchronization/provenance metadata only, not settled ROI, promotion readiness, live profitability, or real-money evidence",
        )
    )
    checks.append(
        require(
            "Do not use it to promote `OP_REFINED_K7`" in saved_md
            and "treat CI-only coverage as a cleared paper-observation gate" in saved_md
            and "reopen odds-only XGBoost" in saved_md
            and "substitute `BAQ` for `BEL`" in saved_md
            and "discuss real-money sizing" in saved_md,
            "non_goals_present",
            "audit bottom line blocks the main report-safety failure modes explicitly",
        )
    )
    checks.append(
        require(
            tmp_parent == TMP_PARENT
            and tmp_parent.is_relative_to(BASE)
            and tmp_parent.exists(),
            "cli_scratch_root_project_local",
            f"scorecard ranking-contract negative CLI fixture writes use project-local temporary root {tmp_parent}, cleared before the fixture run",
        )
    )
    checks.append(
        require(
            scratch["tmp_parent_is_project_local"] is True
            and scratch["tmp_parent_cleared_before_fixture_run"] is True
            and Path(scratch["tmp_parent"]) == TMP_PARENT,
            "cli_scratch_metadata_published",
            "scorecard ranking-contract audit validation publishes top-level project-local scratch metadata so parent rollups can verify the cleared fixture root without parsing prose",
        )
    )

    with tempfile.TemporaryDirectory(prefix="scorecard_contract_audit_", dir=tmp_parent) as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        tmp_scorecard = tmpdir / "bad_forward_evidence_scorecard.json"
        shutil.copy2(audit.SCORECARD_JSON, tmp_scorecard)
        bad_payload = read_json(tmp_scorecard)
        bad_payload.pop("ranking_contract", None)
        tmp_scorecard.write_text(json.dumps(bad_payload, indent=2) + "\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(BASE / "scorecard_ranking_contract_audit.py"), "--scorecard-json", str(tmp_scorecard), "--md-output", str(tmpdir / "x.md"), "--json-output", str(tmpdir / "x.json")],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
        )
        checks.append(
            require(
                result.returncode != 0 and "missing ranking_contract" in f"{result.stdout}\n{result.stderr}",
                "missing_source_contract_fails_fast",
                "audit CLI fails fast if forward_evidence_scorecard.json loses ranking_contract instead of emitting a polished but ungrounded inventory",
            )
        )

        missing_ci_scorecard = tmpdir / "bad_ci_only_forward_evidence_scorecard.json"
        shutil.copy2(audit.SCORECARD_JSON, missing_ci_scorecard)
        bad_ci_payload = read_json(missing_ci_scorecard)
        bad_ci_payload.pop("ci_only_promotion_diagnostics", None)
        missing_ci_scorecard.write_text(json.dumps(bad_ci_payload, indent=2) + "\n", encoding="utf-8")
        ci_result = subprocess.run(
            [
                sys.executable,
                str(BASE / "scorecard_ranking_contract_audit.py"),
                "--scorecard-json",
                str(missing_ci_scorecard),
                "--md-output",
                str(tmpdir / "ci.md"),
                "--json-output",
                str(tmpdir / "ci.json"),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
        )
        checks.append(
            require(
                ci_result.returncode != 0 and "missing ci_only_promotion_diagnostics" in f"{ci_result.stdout}\n{ci_result.stderr}",
                "missing_source_ci_only_diagnostic_fails_fast",
                "audit CLI fails fast if forward_evidence_scorecard.json loses ci_only_promotion_diagnostics instead of emitting a polished but ungrounded CI-only inventory",
            )
        )

        bad_route_json = tmpdir / "bad_scorecard_audit_route_current_evidence.json"
        bad_route_payload = read_json(BASE / "current_evidence_summary.json")
        bad_route = dict(bad_route_payload["scorecard_audit_route"])
        bad_route["markdown_path"] = "NOT_THE_SCORECARD_AUDIT.md"
        bad_route["json_path"] = "not_the_scorecard_audit.json"
        bad_route_payload["scorecard_audit_route"] = bad_route
        bad_route_json.write_text(json.dumps(bad_route_payload, indent=2) + "\n", encoding="utf-8")
        bad_route_result = audit.check_json_scorecard_audit_route_surface(
            {
                "name": "bad_scorecard_audit_route",
                "path": bad_route_json,
                "role": "negative fixture current-evidence bridge route",
                "route_path": "scorecard_audit_route",
            },
            decision_gate_minimums,
        )
        bad_route_issues = "; ".join(bad_route_result.get("issues", []))
        checks.append(
            require(
                bad_route_result["status"] == "fail"
                and bad_route_result["route_matches_scorecard_gate_minimums"] is False
                and bad_route_result["referenced_markdown_path_is_audit_output"] is False
                and bad_route_result["referenced_json_path_is_audit_output"] is False
                and bad_route_result["referenced_route_artifacts_verified_on_disk"] is False
                and "markdown_path does not point to the scorecard audit markdown output" in bad_route_issues
                and "json_path does not point to the scorecard audit JSON output" in bad_route_issues,
                "bad_scorecard_audit_route_artifacts_fail_in_process",
                "audit row checker fails a temporary current_evidence_summary.json whose scorecard_audit_route points at non-audit markdown/JSON paths, proving route-artifact verification is not only a happy-path inventory field",
            )
        )

        bad_route_gates_json = tmpdir / "bad_scorecard_audit_route_gates_current_evidence.json"
        bad_route_gates_payload = read_json(BASE / "current_evidence_summary.json")
        bad_route_gates = dict(bad_route_gates_payload["scorecard_audit_route"])
        bad_route_gates_snapshot = dict(bad_route_gates["gate_floor_snapshot"])
        bad_route_gates_snapshot["anchor_displacement_min_roi_complete_settled_observations"] = 29
        bad_route_gates_snapshot["real_money_no_baq_as_bel_required"] = False
        bad_route_gates["gate_floor_snapshot"] = bad_route_gates_snapshot
        bad_route_gates_payload["scorecard_audit_route"] = bad_route_gates
        bad_route_gates_json.write_text(json.dumps(bad_route_gates_payload, indent=2) + "\n", encoding="utf-8")
        bad_route_gates_result = audit.check_json_scorecard_audit_route_surface(
            {
                "name": "bad_scorecard_audit_route_gates",
                "path": bad_route_gates_json,
                "role": "negative fixture current-evidence bridge route with stale gate-floor snapshot",
                "route_path": "scorecard_audit_route",
            },
            decision_gate_minimums,
        )
        bad_route_gates_issues = "; ".join(bad_route_gates_result.get("issues", []))
        checks.append(
            require(
                bad_route_gates_result["status"] == "fail"
                and bad_route_gates_result["route_matches_scorecard_gate_minimums"] is False
                and bad_route_gates_result["referenced_route_artifacts_verified_on_disk"] is True
                and "scorecard_audit_route.gate_floor_snapshot does not match scorecard-audit route contract"
                in bad_route_gates_issues,
                "bad_scorecard_audit_route_gate_floor_snapshot_fails_in_process",
                "audit row checker fails a temporary current_evidence_summary.json whose scorecard_audit_route keeps valid artifacts but drifts from the scorecard-sourced 30/20/100 gate-floor snapshot and no-BAQ prerequisite",
            )
        )

        bad_route_command_json = tmpdir / "bad_scorecard_audit_route_command_current_evidence.json"
        bad_route_command_payload = read_json(BASE / "current_evidence_summary.json")
        bad_route_command = dict(bad_route_command_payload["scorecard_audit_route"])
        bad_route_command["validator_command"] = "python3 validate_project_surfaces.py"
        bad_route_command["gate_floor_source"] = "manual copied prose"
        bad_route_command["valid_use"] = "general evidence read"
        bad_route_command_payload["scorecard_audit_route"] = bad_route_command
        bad_route_command_json.write_text(json.dumps(bad_route_command_payload, indent=2) + "\n", encoding="utf-8")
        bad_route_command_result = audit.check_json_scorecard_audit_route_surface(
            {
                "name": "bad_scorecard_audit_route_command",
                "path": bad_route_command_json,
                "role": "negative fixture current-evidence bridge route with stale command/source metadata",
                "route_path": "scorecard_audit_route",
            },
            decision_gate_minimums,
        )
        bad_route_command_issues = "; ".join(bad_route_command_result.get("issues", []))
        checks.append(
            require(
                bad_route_command_result["status"] == "fail"
                and bad_route_command_result["route_matches_scorecard_gate_minimums"] is False
                and bad_route_command_result["referenced_route_artifacts_verified_on_disk"] is True
                and "scorecard_audit_route.validator_command does not match scorecard-audit route contract"
                in bad_route_command_issues
                and "scorecard_audit_route.gate_floor_source does not match scorecard-audit route contract"
                in bad_route_command_issues
                and "scorecard_audit_route.valid_use does not match scorecard-audit route contract"
                in bad_route_command_issues,
                "bad_scorecard_audit_route_command_source_fails_in_process",
                "audit row checker fails a temporary current_evidence_summary.json whose scorecard_audit_route keeps valid artifacts but drifts from the dedicated validator command, scorecard gate-floor source, and synchronization-only valid-use metadata",
            )
        )

        bad_route_boundary_json = tmpdir / "bad_scorecard_audit_route_boundary_current_evidence.json"
        bad_route_boundary_payload = read_json(BASE / "current_evidence_summary.json")
        bad_route_boundary = dict(bad_route_boundary_payload["scorecard_audit_route"])
        bad_route_boundary["not_real_money_evidence"] = False
        bad_route_boundary["not_bankroll_guidance"] = False
        bad_route_boundary_payload["scorecard_audit_route"] = bad_route_boundary
        bad_route_boundary_json.write_text(json.dumps(bad_route_boundary_payload, indent=2) + "\n", encoding="utf-8")
        bad_route_boundary_result = audit.check_json_scorecard_audit_route_surface(
            {
                "name": "bad_scorecard_audit_route_boundary",
                "path": bad_route_boundary_json,
                "role": "negative fixture current-evidence bridge route with weakened non-evidence flags",
                "route_path": "scorecard_audit_route",
            },
            decision_gate_minimums,
        )
        bad_route_boundary_issues = "; ".join(bad_route_boundary_result.get("issues", []))
        checks.append(
            require(
                bad_route_boundary_result["status"] == "fail"
                and bad_route_boundary_result["route_matches_scorecard_gate_minimums"] is False
                and bad_route_boundary_result["referenced_route_artifacts_verified_on_disk"] is True
                and "scorecard_audit_route.not_real_money_evidence does not match scorecard-audit route contract"
                in bad_route_boundary_issues
                and "scorecard_audit_route.not_bankroll_guidance does not match scorecard-audit route contract"
                in bad_route_boundary_issues,
                "bad_scorecard_audit_route_non_evidence_flags_fail_in_process",
                "audit row checker fails a temporary current_evidence_summary.json whose scorecard_audit_route weakens non-evidence flags while still pointing at the right audit artifacts",
            )
        )

        bad_route_read_json = tmpdir / "bad_scorecard_audit_route_read_current_evidence.json"
        bad_route_read_payload = read_json(BASE / "current_evidence_summary.json")
        bad_route_read = dict(bad_route_read_payload["scorecard_audit_route"])
        bad_route_read["route_read"] = "Read the scorecard audit for copied gate floors and ranking context."
        bad_route_read_payload["scorecard_audit_route"] = bad_route_read
        bad_route_read_json.write_text(json.dumps(bad_route_read_payload, indent=2) + "\n", encoding="utf-8")
        bad_route_read_result = audit.check_json_scorecard_audit_route_surface(
            {
                "name": "bad_scorecard_audit_route_read",
                "path": bad_route_read_json,
                "role": "negative fixture current-evidence bridge route with weakened route_read text",
                "route_path": "scorecard_audit_route",
            },
            decision_gate_minimums,
        )
        bad_route_read_issues = "; ".join(bad_route_read_result.get("issues", []))
        checks.append(
            require(
                bad_route_read_result["status"] == "fail"
                and bad_route_read_result["route_matches_scorecard_gate_minimums"] is False
                and bad_route_read_result["referenced_route_artifacts_verified_on_disk"] is True
                and "scorecard_audit_route.route_read missing 'OP_REFINED CI-only support context'" in bad_route_read_issues
                and "scorecard_audit_route.route_read missing 'generated-at timezone provenance'" in bad_route_read_issues
                and "scorecard_audit_route.route_read missing 'no-BAQ-as-BEL prerequisite drift'" in bad_route_read_issues,
                "bad_scorecard_audit_route_read_phrase_fails_in_process",
                "audit row checker fails a temporary current_evidence_summary.json whose scorecard_audit_route keeps valid fields but weakens the human route_read synchronization text",
            )
        )

        bad_rebuild_contract_json = tmpdir / "bad_rebuild_contract_current_evidence.json"
        bad_rebuild_contract_payload = read_json(BASE / "current_evidence_summary.json")
        bad_rebuild_contract = dict(bad_rebuild_contract_payload["rebuild_validation_contract"])
        bad_rebuild_contract["prerequisite_rebuild_command"] = "python3 current_evidence_summary.py"
        bad_rebuild_contract["requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"] = False
        bad_rebuild_contract["not_settled_roi_or_real_money_evidence"] = False
        bad_rebuild_contract_payload["rebuild_validation_contract"] = bad_rebuild_contract
        bad_rebuild_contract_json.write_text(
            json.dumps(bad_rebuild_contract_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        bad_rebuild_contract_result = audit.check_json_rebuild_validation_contract_surface(
            {
                "name": "bad_rebuild_validation_contract",
                "path": bad_rebuild_contract_json,
                "role": "negative fixture current-evidence bridge rebuild contract",
                "contract_path": "rebuild_validation_contract",
            }
        )
        bad_rebuild_contract_issues = "; ".join(bad_rebuild_contract_result.get("issues", []))
        checks.append(
            require(
                bad_rebuild_contract_result["status"] == "fail"
                and bad_rebuild_contract_result["contract_matches_expected"] is False
                and bad_rebuild_contract_result[
                    "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
                ]
                is False
                and bad_rebuild_contract_result["required_non_evidence_flags_match_contract"] is False
                and "rebuild_validation_contract.prerequisite_rebuild_command does not match current-evidence rebuild contract"
                in bad_rebuild_contract_issues
                and "rebuild_validation_contract.requires_settlement_audit_refresh_before_bridge_when_source_bytes_change does not match current-evidence rebuild contract"
                in bad_rebuild_contract_issues
                and "rebuild_validation_contract.not_settled_roi_or_real_money_evidence does not match current-evidence rebuild contract"
                in bad_rebuild_contract_issues,
                "bad_rebuild_validation_contract_fails_in_process",
                "audit row checker fails a temporary current_evidence_summary.json whose rebuild_validation_contract skips the settlement-audit prerequisite or weakens non-evidence flags",
            )
        )

        missing_rebuild_cli_json = tmpdir / "missing_rebuild_contract_cli_current_evidence.json"
        missing_rebuild_cli_payload = read_json(BASE / "current_evidence_summary.json")
        missing_rebuild_cli_payload.pop("rebuild_validation_contract", None)
        missing_rebuild_cli_json.write_text(
            json.dumps(missing_rebuild_cli_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_rebuild_cli_out_dir = tmpdir / "missing_rebuild_cli_outputs"
        missing_rebuild_cli_out_dir.mkdir()
        missing_rebuild_cli_md = missing_rebuild_cli_out_dir / "scorecard_audit_should_not_write.md"
        missing_rebuild_cli_sidecar = missing_rebuild_cli_out_dir / "scorecard_audit_should_not_write.json"
        missing_rebuild_cli_result = subprocess.run(
            [
                sys.executable,
                str(BASE / "scorecard_ranking_contract_audit.py"),
                "--generated-at",
                saved_payload["generated_at"],
                "--current-evidence-json",
                str(missing_rebuild_cli_json),
                "--md-output",
                str(missing_rebuild_cli_md),
                "--json-output",
                str(missing_rebuild_cli_sidecar),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
        )
        missing_rebuild_cli_text = f"{missing_rebuild_cli_result.stdout}\n{missing_rebuild_cli_result.stderr}"
        checks.append(
            require(
                missing_rebuild_cli_result.returncode != 0
                and "critical current_evidence_summary.json bridge rows failed before writing scorecard audit artifacts"
                in missing_rebuild_cli_text
                and "missing rebuild_validation_contract" in missing_rebuild_cli_text
                and not missing_rebuild_cli_md.exists()
                and not missing_rebuild_cli_sidecar.exists(),
                "missing_current_evidence_rebuild_contract_fails_before_audit_artifacts",
                "the real scorecard_ranking_contract_audit.py CLI rejects a current-evidence sidecar with no rebuild_validation_contract before writing markdown/JSON audit artifacts",
            )
        )

        weakened_rebuild_cli_json = tmpdir / "weakened_rebuild_contract_cli_current_evidence.json"
        weakened_rebuild_cli_payload = read_json(BASE / "current_evidence_summary.json")
        weakened_rebuild_cli_payload["rebuild_validation_contract"][
            "upstream_refresh_order_is_provenance_metadata_only"
        ] = False
        weakened_rebuild_cli_json.write_text(
            json.dumps(weakened_rebuild_cli_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        weakened_rebuild_cli_out_dir = tmpdir / "weakened_rebuild_cli_outputs"
        weakened_rebuild_cli_out_dir.mkdir()
        weakened_rebuild_cli_md = weakened_rebuild_cli_out_dir / "scorecard_audit_should_not_write.md"
        weakened_rebuild_cli_sidecar = weakened_rebuild_cli_out_dir / "scorecard_audit_should_not_write.json"
        weakened_rebuild_cli_result = subprocess.run(
            [
                sys.executable,
                str(BASE / "scorecard_ranking_contract_audit.py"),
                "--generated-at",
                saved_payload["generated_at"],
                "--current-evidence-json",
                str(weakened_rebuild_cli_json),
                "--md-output",
                str(weakened_rebuild_cli_md),
                "--json-output",
                str(weakened_rebuild_cli_sidecar),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
        )
        weakened_rebuild_cli_text = f"{weakened_rebuild_cli_result.stdout}\n{weakened_rebuild_cli_result.stderr}"
        checks.append(
            require(
                weakened_rebuild_cli_result.returncode != 0
                and "critical current_evidence_summary.json bridge rows failed before writing scorecard audit artifacts"
                in weakened_rebuild_cli_text
                and "rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only"
                in weakened_rebuild_cli_text
                and not weakened_rebuild_cli_md.exists()
                and not weakened_rebuild_cli_sidecar.exists(),
                "weakened_current_evidence_rebuild_contract_fails_before_audit_artifacts",
                "the real scorecard_ranking_contract_audit.py CLI rejects a current-evidence sidecar with a weakened provenance-only rebuild flag before writing markdown/JSON audit artifacts",
            )
        )

    suite_status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    payload = {
        "suite_status": suite_status,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "summary": {
            "suite_read": (
                "scorecard ranking-contract / CI-only audit verifies every configured report-facing text and JSON surface carries the tier-first contract or source-matched OP_REFINED CI-only diagnostic; "
                "this is report synchronization only, not forward evidence or promotion readiness"
            ),
            "rebuild_command": rebuild_command,
        },
        "scratch": scratch,
        "audited_surface_count": saved_payload["row_count"],
        "valid_evidence_scope": audit.SCORECARD_AUDIT_VALID_EVIDENCE_SCOPE,
        "scorecard_audit_route_diagnostics": scorecard_route_diagnostics,
        "rebuild_validation_contract_diagnostics": rebuild_contract_diagnostics,
        "scorecard_ranking_contract": contract,
        "decision_gate_minimums": decision_gate_minimums,
        "evidence_boundary": audit.EVIDENCE_BOUNDARY,
        "evidence_boundary_metadata": audit.build_evidence_boundary_metadata(decision_gate_minimums),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Scorecard Ranking-Contract Audit Validation",
        "",
        f"Status: **{suite_status.upper()}**",
        f"Total checks: {len(checks)}",
        "",
        "## Summary",
        "",
        payload["summary"]["suite_read"],
        "",
        f"- Temporary fixture root: `{tmp_parent}` (cleared before CLI fixture run)",
        f"- valid_evidence_scope={audit.SCORECARD_AUDIT_VALID_EVIDENCE_SCOPE}",
        "",
        "## Checks",
        "",
    ]
    for check in checks:
        lines.append(f"- {check['status'].upper()} — `{check['check']}`: {check['detail']}")
    lines.extend([
        "",
        "## Rebuild",
        "",
        f"- `{rebuild_command}`",
        "",
    ])
    VALIDATION_MD.write_text("\n".join(lines), encoding="utf-8")
    VALIDATION_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {VALIDATION_MD}")
    print(f"Wrote {VALIDATION_JSON}")
    if suite_status != "pass":
        failed = [check for check in checks if check["status"] != "pass"]
        raise AssertionError(f"scorecard ranking-contract audit validation failed: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
