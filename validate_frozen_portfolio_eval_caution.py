#!/usr/bin/env python3
"""
Validation for the Frozen Portfolio Evaluation report boundary.

Purpose:
- keep FROZEN_PORTFOLIO_EVAL.md tied to the frozen 2024-2025 holdout standard
- prevent the historical replay P&L from being read as live paper-trade, promotion-ready, or real-money evidence
- preserve the current OP_DURABLE_K7 / CD_CORE_K8 / Phase 8 shadow-watch / BAQ-is-not-BEL posture
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import evaluate_frozen_portfolios as frozen_eval

BASE = Path(__file__).resolve().parent
REPORT = BASE / "FROZEN_PORTFOLIO_EVAL.md"
GENERATOR = BASE / "evaluate_frozen_portfolios.py"
METADATA = BASE / "frozen_portfolio_eval_metadata.json"
CACHE_PATH = BASE / "phase5_race_cache.pkl"
PHASE7_RULES = BASE / "phase7_live_rules.json"
CURRENT_EVIDENCE = BASE / "current_evidence_summary.json"
OUT_DIR = BASE / "out" / "status_validation" / "frozen_portfolio_eval_caution"
OUT_MD = OUT_DIR / "frozen_portfolio_eval_caution_validation.md"
OUT_JSON = OUT_DIR / "frozen_portfolio_eval_caution_validation.json"
TMP_PARENT = OUT_DIR / "_tmp"
REBUILD_COMMAND = "python3 validate_frozen_portfolio_eval_caution.py"
VALID_EVIDENCE_SCOPE = frozen_eval.VALID_EVIDENCE_SCOPE
REQUIRED_SOURCE_FRESHNESS_FIELDS = [
    "generated_reference_date",
    "generated_reference_timezone",
    "staleness_comparison_source",
    "staleness_comparison_date",
    "read",
]
REQUIRED_REFRESH_ACTION_BOUNDARY_TEXT_FIELDS = [
    "command",
    "valid_use",
    "read",
]
REQUIRED_REFRESH_ACTION_BOUNDARY_BOOL_FIELDS = [
    "required_before_right_now_instruction_use",
    "source_action_counts_as_current_instruction_before_refresh",
    "not_forward_performance_evidence",
    "not_live_profitability_evidence",
    "not_promotion_readiness_evidence",
    "not_real_money_evidence",
    "wrapper_refresh_can_update_operator_surfaces",
    "wrapper_refresh_can_settle_open_rows_by_itself",
    "wrapper_refresh_counts_as_roi_complete_evidence_by_itself",
    "clean_empty_refresh_counts_as_forward_performance",
    "missing_or_invalid_artifact_counts_as_clean_quiet_day",
]
REQUIRED_OPERATOR_READ_GATE_TEXT_FIELDS = [
    "gate_status",
    "reason_text",
    "recommended_command",
    "valid_use",
    "read",
]
REQUIRED_OPERATOR_READ_GATE_BOOL_FIELDS = [
    "requires_refresh_before_evidence_read",
    "requires_source_freshness_refresh",
    "has_api_access_failure_context",
    "has_scanner_failure_boundary",
    "has_stale_cache_fallback_context",
    "has_missing_scan_output_artifact_issue",
    "has_wrapper_refresh_action",
    "has_issue_bucket",
    "current_top_card_counts_as_no_target_evidence",
    "current_top_card_counts_as_clean_empty_evidence",
    "current_top_card_counts_as_bet_readiness_evidence",
    "current_top_card_counts_as_settled_roi_evidence",
    "not_forward_performance_evidence",
    "not_promotion_readiness_evidence",
    "not_live_profitability_evidence",
    "not_real_money_evidence",
]
REQUIRED_REBUILD_REFRESH_ORDER = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "pass", "detail": detail}


def file_fingerprint(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"path": path.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def expected_source_files() -> dict[str, dict[str, object]]:
    return {
        "race_cache": file_fingerprint(CACHE_PATH),
        "phase7_rules": file_fingerprint(PHASE7_RULES),
        "generator": file_fingerprint(GENERATOR),
        "current_evidence_summary": file_fingerprint(CURRENT_EVIDENCE),
    }


def format_source_fingerprint(label: str, info: dict[str, object]) -> str:
    return f"- {label}: {info['path']} ({info['bytes']} bytes, sha256={info['sha256']})"


def prepare_tmp_parent() -> Path:
    """Use project-local scratch so CLI fixtures do not depend on system temp state."""
    if TMP_PARENT.exists():
        shutil.rmtree(TMP_PARENT)
    TMP_PARENT.mkdir(parents=True, exist_ok=True)
    return TMP_PARENT


def current_boundary_date(current_evidence: dict[str, Any]) -> str:
    return str(current_boundary_info(current_evidence)["date"])


def current_boundary_info(current_evidence: dict[str, Any]) -> dict[str, Any]:
    freshness = current_evidence.get("source_freshness")
    if isinstance(freshness, dict):
        if freshness.get("generated_reference_date"):
            return {
                "date": str(freshness["generated_reference_date"]),
                "source": "source_freshness.generated_reference_date",
                "timezone": freshness.get("generated_reference_timezone"),
            }
        if freshness.get("generated_date"):
            return {"date": str(freshness["generated_date"]), "source": "source_freshness.generated_date", "timezone": None}
    generated_at = str(current_evidence.get("generated_at") or "")
    if "T" in generated_at:
        return {"date": generated_at.split("T", 1)[0], "source": "generated_at_date", "timezone": None}
    return {"date": generated_at, "source": "unknown", "timezone": None}


def current_source_freshness_context(current_evidence: dict[str, Any]) -> dict[str, Any]:
    freshness = current_evidence.get("source_freshness")
    if not isinstance(freshness, dict):
        raise AssertionError("current_evidence_summary.json missing source_freshness")
    missing = [field for field in REQUIRED_SOURCE_FRESHNESS_FIELDS if freshness.get(field) in (None, "")]
    if missing:
        raise AssertionError(f"current_evidence_summary.json source_freshness missing {', '.join(missing)}")
    return {
        "generated_reference_date": str(freshness["generated_reference_date"]),
        "generated_reference_timezone": str(freshness["generated_reference_timezone"]),
        "staleness_comparison_source": str(freshness["staleness_comparison_source"]),
        "staleness_comparison_date": str(freshness["staleness_comparison_date"]),
        "read": str(freshness["read"]),
        "right_now_freshness_state": str(freshness.get("right_now_freshness_state") or "unknown"),
        "requires_refresh_before_right_now_use": bool(freshness.get("requires_refresh_before_right_now_use")),
    }


def current_refresh_action_boundary_context(current_evidence: dict[str, Any]) -> dict[str, Any]:
    freshness = current_evidence.get("source_freshness")
    if not isinstance(freshness, dict):
        raise AssertionError("current_evidence_summary.json missing source_freshness")
    refresh_action = freshness.get("refresh_action_boundary")
    if not isinstance(refresh_action, dict):
        raise AssertionError("current_evidence_summary.json source_freshness missing refresh_action_boundary")
    missing = [
        field
        for field in REQUIRED_REFRESH_ACTION_BOUNDARY_TEXT_FIELDS
        if refresh_action.get(field) in (None, "")
    ]
    missing.extend(
        field
        for field in REQUIRED_REFRESH_ACTION_BOUNDARY_BOOL_FIELDS
        if not isinstance(refresh_action.get(field), bool)
    )
    if missing:
        raise AssertionError(
            "current_evidence_summary.json source_freshness.refresh_action_boundary missing "
            + ", ".join(missing)
        )
    required_true_fields = [
        "not_forward_performance_evidence",
        "not_live_profitability_evidence",
        "not_promotion_readiness_evidence",
        "not_real_money_evidence",
    ]
    weakened_true_fields = [
        field for field in required_true_fields if refresh_action.get(field) is not True
    ]
    if weakened_true_fields:
        raise AssertionError(
            "current_evidence_summary.json source_freshness.refresh_action_boundary must mark "
            + ", ".join(weakened_true_fields)
            + "=true"
        )
    if refresh_action.get("wrapper_refresh_can_update_operator_surfaces") is not True:
        raise AssertionError(
            "current_evidence_summary.json source_freshness.refresh_action_boundary must mark "
            "wrapper_refresh_can_update_operator_surfaces=true"
        )
    required_false_fields = [
        "wrapper_refresh_can_settle_open_rows_by_itself",
        "wrapper_refresh_counts_as_roi_complete_evidence_by_itself",
        "clean_empty_refresh_counts_as_forward_performance",
        "missing_or_invalid_artifact_counts_as_clean_quiet_day",
    ]
    weakened_false_fields = [
        field for field in required_false_fields if refresh_action.get(field) is not False
    ]
    if weakened_false_fields:
        raise AssertionError(
            "current_evidence_summary.json source_freshness.refresh_action_boundary must mark "
            + ", ".join(weakened_false_fields)
            + "=false"
        )
    return {
        "command": str(refresh_action["command"]),
        "valid_use": str(refresh_action["valid_use"]),
        "read": str(refresh_action["read"]),
        "required_before_right_now_instruction_use": refresh_action["required_before_right_now_instruction_use"],
        "source_action_counts_as_current_instruction_before_refresh": refresh_action[
            "source_action_counts_as_current_instruction_before_refresh"
        ],
        "not_forward_performance_evidence": refresh_action["not_forward_performance_evidence"],
        "not_live_profitability_evidence": refresh_action["not_live_profitability_evidence"],
        "not_promotion_readiness_evidence": refresh_action["not_promotion_readiness_evidence"],
        "not_real_money_evidence": refresh_action["not_real_money_evidence"],
        "wrapper_refresh_can_update_operator_surfaces": refresh_action[
            "wrapper_refresh_can_update_operator_surfaces"
        ],
        "wrapper_refresh_can_settle_open_rows_by_itself": refresh_action[
            "wrapper_refresh_can_settle_open_rows_by_itself"
        ],
        "wrapper_refresh_counts_as_roi_complete_evidence_by_itself": refresh_action[
            "wrapper_refresh_counts_as_roi_complete_evidence_by_itself"
        ],
        "clean_empty_refresh_counts_as_forward_performance": refresh_action[
            "clean_empty_refresh_counts_as_forward_performance"
        ],
        "missing_or_invalid_artifact_counts_as_clean_quiet_day": refresh_action[
            "missing_or_invalid_artifact_counts_as_clean_quiet_day"
        ],
    }


def current_operator_read_gate_context(current_evidence: dict[str, Any]) -> dict[str, Any]:
    gate = current_evidence.get("operator_read_gate")
    if not isinstance(gate, dict):
        raise AssertionError("current_evidence_summary.json missing operator_read_gate")
    if gate != current_evidence.get("current_paper_status", {}).get("operator_read_gate"):
        raise AssertionError(
            "current_evidence_summary.json operator_read_gate must match "
            "current_paper_status.operator_read_gate"
        )
    missing = [
        field
        for field in REQUIRED_OPERATOR_READ_GATE_TEXT_FIELDS
        if gate.get(field) in (None, "")
    ]
    missing.extend(
        field
        for field in REQUIRED_OPERATOR_READ_GATE_BOOL_FIELDS
        if not isinstance(gate.get(field), bool)
    )
    if missing:
        raise AssertionError("current_evidence_summary.json operator_read_gate missing " + ", ".join(missing))
    gate_status = gate.get("gate_status")
    if gate_status not in {"refresh_required_before_evidence_read", "current_operator_routing_context_only"}:
        raise AssertionError(
            "current_evidence_summary.json operator_read_gate.gate_status must be a known "
            "instruction/evidence-read state"
        )
    if gate.get("valid_use") != "operator instruction/evidence-read gating only":
        raise AssertionError("current_evidence_summary.json operator_read_gate.valid_use drifted")
    required_true_fields = [
        "not_forward_performance_evidence",
        "not_promotion_readiness_evidence",
        "not_live_profitability_evidence",
        "not_real_money_evidence",
    ]
    weakened_true_fields = [
        field for field in required_true_fields if gate.get(field) is not True
    ]
    if weakened_true_fields:
        raise AssertionError(
            "current_evidence_summary.json operator_read_gate must mark "
            + ", ".join(weakened_true_fields)
            + "=true"
        )
    required_false_fields = [
        "current_top_card_counts_as_no_target_evidence",
        "current_top_card_counts_as_clean_empty_evidence",
        "current_top_card_counts_as_bet_readiness_evidence",
        "current_top_card_counts_as_settled_roi_evidence",
    ]
    weakened_false_fields = [
        field for field in required_false_fields if gate.get(field) is not False
    ]
    if weakened_false_fields:
        raise AssertionError(
            "current_evidence_summary.json operator_read_gate must mark "
            + ", ".join(weakened_false_fields)
            + "=false"
        )
    read = str(gate["read"]).strip()
    if gate_status == "refresh_required_before_evidence_read":
        if gate.get("recommended_command") != "./run_daily_portfolio_observation.sh":
            raise AssertionError("current_evidence_summary.json operator_read_gate must recommend the daily wrapper")
        required_refresh_fields = [
            "requires_refresh_before_evidence_read",
            "has_wrapper_refresh_action",
        ]
        false_refresh_fields = [
            field for field in required_refresh_fields if gate.get(field) is not True
        ]
        if false_refresh_fields:
            raise AssertionError(
                "current_evidence_summary.json operator_read_gate must mark "
                + ", ".join(false_refresh_fields)
                + "=true"
            )
        if not any(
            gate.get(field) is True
            for field in (
                "requires_source_freshness_refresh",
                "has_api_access_failure_context",
                "has_scanner_failure_boundary",
                "has_stale_cache_fallback_context",
                "has_missing_scan_output_artifact_issue",
                "has_issue_bucket",
            )
        ):
            raise AssertionError("current_evidence_summary.json operator_read_gate refresh branch must publish a refresh cause")
        for phrase in (
            "Refresh/recheck with `./run_daily_portfolio_observation.sh`",
            "not a no-target, clean-empty, bet-readiness, settled-ROI, promotion, live-profitability, bankroll, or real-money read",
        ):
            if phrase not in read:
                raise AssertionError(f"current_evidence_summary.json operator_read_gate.read missing {phrase!r}")
    else:
        unexpected_refresh_fields = [
            "requires_refresh_before_evidence_read",
            "requires_source_freshness_refresh",
            "has_api_access_failure_context",
            "has_scanner_failure_boundary",
            "has_stale_cache_fallback_context",
            "has_missing_scan_output_artifact_issue",
            "has_wrapper_refresh_action",
            "has_issue_bucket",
        ]
        true_refresh_fields = [
            field for field in unexpected_refresh_fields if gate.get(field) is not False
        ]
        if true_refresh_fields:
            raise AssertionError(
                "current_evidence_summary.json current operator-read branch must mark "
                + ", ".join(true_refresh_fields)
                + "=false"
            )
        for phrase in (
            "current operator routing context",
            "not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence",
        ):
            if phrase not in read:
                raise AssertionError(f"current_evidence_summary.json operator_read_gate.read missing {phrase!r}")
    return {
        "gate_status": str(gate["gate_status"]),
        "valid_use": str(gate["valid_use"]),
        "reason_text": str(gate["reason_text"]),
        "recommended_command": str(gate["recommended_command"]),
        "requires_refresh_before_evidence_read": gate["requires_refresh_before_evidence_read"],
        "requires_source_freshness_refresh": gate["requires_source_freshness_refresh"],
        "has_api_access_failure_context": gate["has_api_access_failure_context"],
        "has_scanner_failure_boundary": gate["has_scanner_failure_boundary"],
        "has_stale_cache_fallback_context": gate["has_stale_cache_fallback_context"],
        "has_missing_scan_output_artifact_issue": gate["has_missing_scan_output_artifact_issue"],
        "has_wrapper_refresh_action": gate["has_wrapper_refresh_action"],
        "has_issue_bucket": gate["has_issue_bucket"],
        "current_top_card_counts_as_no_target_evidence": gate[
            "current_top_card_counts_as_no_target_evidence"
        ],
        "current_top_card_counts_as_clean_empty_evidence": gate[
            "current_top_card_counts_as_clean_empty_evidence"
        ],
        "current_top_card_counts_as_bet_readiness_evidence": gate[
            "current_top_card_counts_as_bet_readiness_evidence"
        ],
        "current_top_card_counts_as_settled_roi_evidence": gate[
            "current_top_card_counts_as_settled_roi_evidence"
        ],
        "not_forward_performance_evidence": gate["not_forward_performance_evidence"],
        "not_promotion_readiness_evidence": gate["not_promotion_readiness_evidence"],
        "not_live_profitability_evidence": gate["not_live_profitability_evidence"],
        "not_real_money_evidence": gate["not_real_money_evidence"],
        "read": read,
    }


def current_rebuild_validation_contract_context(current_evidence: dict[str, Any]) -> dict[str, Any]:
    contract = current_evidence.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise AssertionError("current_evidence_summary.json missing rebuild_validation_contract")
    order = contract.get("upstream_refresh_order")
    if not isinstance(order, list):
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order must be a list")
    commands: list[str] = []
    for expected_order, row in enumerate(order, start=1):
        if not isinstance(row, dict):
            raise AssertionError("current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order row drifted")
        if row.get("order") != expected_order:
            raise AssertionError("current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order order drifted")
        command = str(row.get("command") or "")
        reason = str(row.get("reason") or "")
        if not command or not reason:
            raise AssertionError("current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order row is incomplete")
        commands.append(command)
    if commands != REQUIRED_REBUILD_REFRESH_ORDER:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract upstream order drifted")
    expected_values = {
        "prerequisite_rebuild_command": "python3 paper_trade_settlement_audit.py",
        "rebuild_command": "python3 current_evidence_summary.py",
        "direct_validation_command": "python3 validate_current_evidence_summary.py",
        "upstream_refresh_order_valid_use": (
            "reproducible rebuild order for current bridge provenance after scorecard/rules/ledger byte changes"
        ),
    }
    for key, expected in expected_values.items():
        if contract.get(key) != expected:
            raise AssertionError(f"current_evidence_summary.json rebuild_validation_contract.{key} drifted")
    required_true_flags = [
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
        "green_checks_are_reproducibility_metadata_only",
        "requires_source_consistency_before_quoting_current_totals",
        "requires_source_freshness_before_right_now_instruction_use",
        "upstream_refresh_order_is_provenance_metadata_only",
        "not_settled_roi_or_real_money_evidence",
    ]
    weakened_flags = [flag for flag in required_true_flags if contract.get(flag) is not True]
    if weakened_flags:
        raise AssertionError(
            "current_evidence_summary.json rebuild_validation_contract must mark "
            + ", ".join(weakened_flags)
            + "=true"
        )
    return {
        "source_path": "rebuild_validation_contract",
        "upstream_refresh_commands": commands,
        "prerequisite_rebuild_command": contract["prerequisite_rebuild_command"],
        "rebuild_command": contract["rebuild_command"],
        "direct_validation_command": contract["direct_validation_command"],
        "upstream_refresh_order_valid_use": contract["upstream_refresh_order_valid_use"],
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": contract[
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
        ],
        "requires_source_consistency_before_quoting_current_totals": contract[
            "requires_source_consistency_before_quoting_current_totals"
        ],
        "requires_source_freshness_before_right_now_instruction_use": contract[
            "requires_source_freshness_before_right_now_instruction_use"
        ],
        "green_checks_are_reproducibility_metadata_only": contract[
            "green_checks_are_reproducibility_metadata_only"
        ],
        "upstream_refresh_order_is_provenance_metadata_only": contract[
            "upstream_refresh_order_is_provenance_metadata_only"
        ],
        "not_settled_roi_or_real_money_evidence": contract["not_settled_roi_or_real_money_evidence"],
    }


def current_paper_context(current_evidence: dict[str, Any]) -> dict[str, Any]:
    status = current_evidence.get("current_paper_status")
    if not isinstance(status, dict):
        raise AssertionError("current_evidence_summary.json missing current_paper_status")
    primary = status.get("primary")
    if not isinstance(primary, dict):
        raise AssertionError("current_evidence_summary.json missing current_paper_status.primary")
    first_read = primary.get("first_read") if isinstance(primary.get("first_read"), dict) else {}
    recommendation_context = (
        primary.get("recommendation_context") if isinstance(primary.get("recommendation_context"), dict) else {}
    )
    open_settlements = int(primary.get("open_settlements", 0) or 0)
    open_summary = str(primary.get("open_settlement_summary") or "").strip()
    if open_settlements > 0 and open_summary.lower() in {"", "none"}:
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_summary "
            "must identify open rows when open_settlements > 0"
        )
    open_queue = primary.get("open_settlement_queue_by_rule")
    if not isinstance(open_queue, dict):
        raise AssertionError(
            "current_evidence_summary.json missing "
            "current_paper_status.primary.open_settlement_queue_by_rule"
        )
    open_settlement_queue_state = str(open_queue.get("open_settlement_queue_state") or "").strip()
    open_settlement_context = str(open_queue.get("open_settlement_context") or "").strip()
    open_settlement_queue_read = str(open_queue.get("detail_read") or "").strip()
    expected_open_settlement_queue_state = "closed" if open_settlements == 0 else "open"
    if open_settlement_queue_state not in {"closed", "open"}:
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_queue_state must be closed or open"
        )
    if open_settlement_queue_state != expected_open_settlement_queue_state:
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_queue_state must match current_paper_status.primary.open_settlements"
        )
    if not open_settlement_context:
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_context is required"
        )
    if open_settlements == 0 and open_settlement_context != "no open primary settlement rows":
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_context must read no open primary settlement rows when open_settlements is 0"
        )
    if open_settlements > 0 and "open" not in open_settlement_context.lower():
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "open_settlement_context must identify open rows when open_settlements is greater than 0"
        )
    if "Open settlement queue by rule:" not in open_settlement_queue_read:
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "detail_read must carry the by-rule open settlement detail"
        )
    if "Settlement queue state:" in open_settlement_queue_read:
        raise AssertionError(
            "current_evidence_summary.json current_paper_status.primary.open_settlement_queue_by_rule."
            "detail_read must not nest the settlement queue state wrapper"
        )
    return {
        "roi_complete_settled": int(primary.get("roi_complete_settled", 0) or 0),
        "hit_count": int(primary.get("hit_count", 0) or 0),
        "miss_count": int(primary.get("miss_count", 0) or 0),
        "open_settlements": open_settlements,
        "open_settlement_summary": open_summary,
        "open_settlement_queue_state": open_settlement_queue_state,
        "open_settlement_context": open_settlement_context,
        "open_settlement_queue_read": open_settlement_queue_read,
        "rule_mix_read": str(primary.get("rule_mix_read") or "").strip(),
        "first_read_current": int(first_read.get("current", 0) or 0),
        "first_read_threshold": int(first_read.get("threshold", 30) or 30),
        "latest_context_has_no_bet_recommendations": bool(
            recommendation_context.get("latest_context_has_no_bet_recommendations")
        ),
        "recommendation_context_read": str(recommendation_context.get("read") or "").strip(),
    }


def run_bad_current_evidence_generated_at_fixture(current_evidence: dict[str, Any], tmp_parent: Path) -> tuple[bool, str]:
    fixture_path = tmp_parent / "bad_generated_at_current_evidence_summary.json"
    bad_output_dir = tmp_parent / "bad_current_evidence_nested_output" / "artifacts"
    bad_outputs = [
        bad_output_dir / "bad_current_evidence_should_not_write_summary.csv",
        bad_output_dir / "bad_current_evidence_should_not_write_yearly.csv",
        bad_output_dir / "bad_current_evidence_should_not_write.md",
        bad_output_dir / "bad_current_evidence_should_not_write_metadata.json",
    ]
    bad_payload = dict(current_evidence)
    bad_payload["generated_at"] = "2026-06-26 18:12:48"
    try:
        fixture_path.write_text(json.dumps(bad_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                GENERATOR.name,
                "--current-evidence-json",
                str(fixture_path),
                "--summary-output",
                str(bad_outputs[0]),
                "--yearly-output",
                str(bad_outputs[1]),
                "--report-output",
                str(bad_outputs[2]),
                "--metadata-output",
                str(bad_outputs[3]),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if result.returncode == 0:
            return False, "evaluate_frozen_portfolios.py unexpectedly accepted a timezone-naive generated_at"
        combined_output = f"{result.stdout}\n{result.stderr}"
        if "generated_at must be timezone-aware ISO provenance metadata" not in combined_output:
            return False, "bad generated_at CLI failure no longer explains that timestamp provenance must be timezone-aware"
        if bad_output_dir.exists() or any(path.exists() for path in bad_outputs):
            return False, "bad generated_at CLI path created output directories or wrote frozen-replay artifacts before provenance validation failed"
        return True, (
            "the real frozen replay CLI rejects timezone-naive current_evidence_summary.json generated_at before "
            "creating output directories or writing summary/yearly/report/metadata artifacts"
        )
    finally:
        fixture_path.unlink(missing_ok=True)
        for path in bad_outputs:
            path.unlink(missing_ok=True)


def run_missing_operator_read_gate_fixture(
    current_evidence: dict[str, Any],
    tmp_parent: Path,
) -> tuple[bool, str]:
    fixture_path = tmp_parent / "missing_operator_read_gate_current_evidence_summary.json"
    bad_output_dir = tmp_parent / "missing_operator_read_gate_nested_output" / "artifacts"
    bad_outputs = [
        bad_output_dir / "missing_operator_read_gate_should_not_write_summary.csv",
        bad_output_dir / "missing_operator_read_gate_should_not_write_yearly.csv",
        bad_output_dir / "missing_operator_read_gate_should_not_write.md",
        bad_output_dir / "missing_operator_read_gate_should_not_write_metadata.json",
    ]
    bad_payload = json.loads(json.dumps(current_evidence))
    bad_payload.pop("operator_read_gate", None)
    try:
        fixture_path.write_text(json.dumps(bad_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                GENERATOR.name,
                "--current-evidence-json",
                str(fixture_path),
                "--summary-output",
                str(bad_outputs[0]),
                "--yearly-output",
                str(bad_outputs[1]),
                "--report-output",
                str(bad_outputs[2]),
                "--metadata-output",
                str(bad_outputs[3]),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if result.returncode == 0:
            return False, "evaluate_frozen_portfolios.py unexpectedly accepted missing operator_read_gate"
        combined_output = f"{result.stdout}\n{result.stderr}"
        if "is missing operator_read_gate" not in combined_output:
            return False, "missing operator_read_gate failure no longer names the required read gate"
        if bad_output_dir.exists() or any(path.exists() for path in bad_outputs):
            return False, "missing operator_read_gate CLI path created output directories or wrote frozen-replay artifacts before source validation failed"
        return True, (
            "the real frozen replay CLI rejects current_evidence_summary.json without operator_read_gate before "
            "creating output directories or writing summary/yearly/report/metadata artifacts"
        )
    finally:
        fixture_path.unlink(missing_ok=True)
        for path in bad_outputs:
            path.unlink(missing_ok=True)


def run_missing_source_freshness_reference_fixture(
    current_evidence: dict[str, Any],
    tmp_parent: Path,
) -> tuple[bool, str]:
    fixture_path = tmp_parent / "missing_source_freshness_reference_current_evidence_summary.json"
    bad_output_dir = tmp_parent / "missing_source_freshness_nested_output" / "artifacts"
    bad_outputs = [
        bad_output_dir / "missing_source_freshness_should_not_write_summary.csv",
        bad_output_dir / "missing_source_freshness_should_not_write_yearly.csv",
        bad_output_dir / "missing_source_freshness_should_not_write.md",
        bad_output_dir / "missing_source_freshness_should_not_write_metadata.json",
    ]
    bad_payload = json.loads(json.dumps(current_evidence))
    bad_payload["source_freshness"].pop("generated_reference_date", None)
    try:
        fixture_path.write_text(json.dumps(bad_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                GENERATOR.name,
                "--current-evidence-json",
                str(fixture_path),
                "--summary-output",
                str(bad_outputs[0]),
                "--yearly-output",
                str(bad_outputs[1]),
                "--report-output",
                str(bad_outputs[2]),
                "--metadata-output",
                str(bad_outputs[3]),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if result.returncode == 0:
            return False, "evaluate_frozen_portfolios.py unexpectedly accepted source_freshness without generated_reference_date"
        combined_output = f"{result.stdout}\n{result.stderr}"
        if "source_freshness is missing fields: generated_reference_date" not in combined_output:
            return False, "missing source_freshness generated_reference_date failure no longer names the missing freshness-reference field"
        if bad_output_dir.exists() or any(path.exists() for path in bad_outputs):
            return False, "missing source_freshness reference CLI path created output directories or wrote frozen-replay artifacts before source validation failed"
        return True, (
            "the real frozen replay CLI rejects current_evidence_summary.json without "
            "source_freshness.generated_reference_date before creating output directories or writing "
            "summary/yearly/report/metadata artifacts"
        )
    finally:
        fixture_path.unlink(missing_ok=True)
        for path in bad_outputs:
            path.unlink(missing_ok=True)


def run_missing_refresh_action_boundary_fixture(
    current_evidence: dict[str, Any],
    tmp_parent: Path,
) -> tuple[bool, str]:
    fixture_path = tmp_parent / "missing_refresh_action_boundary_current_evidence_summary.json"
    bad_output_dir = tmp_parent / "missing_refresh_action_boundary_nested_output" / "artifacts"
    bad_outputs = [
        bad_output_dir / "missing_refresh_action_boundary_should_not_write_summary.csv",
        bad_output_dir / "missing_refresh_action_boundary_should_not_write_yearly.csv",
        bad_output_dir / "missing_refresh_action_boundary_should_not_write.md",
        bad_output_dir / "missing_refresh_action_boundary_should_not_write_metadata.json",
    ]
    bad_payload = json.loads(json.dumps(current_evidence))
    bad_payload["source_freshness"].pop("refresh_action_boundary", None)
    try:
        fixture_path.write_text(json.dumps(bad_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                GENERATOR.name,
                "--current-evidence-json",
                str(fixture_path),
                "--summary-output",
                str(bad_outputs[0]),
                "--yearly-output",
                str(bad_outputs[1]),
                "--report-output",
                str(bad_outputs[2]),
                "--metadata-output",
                str(bad_outputs[3]),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if result.returncode == 0:
            return False, "evaluate_frozen_portfolios.py unexpectedly accepted source_freshness without refresh_action_boundary"
        combined_output = f"{result.stdout}\n{result.stderr}"
        if "source_freshness is missing refresh_action_boundary" not in combined_output:
            return False, "missing refresh_action_boundary failure no longer names the required wrapper-refresh boundary"
        if bad_output_dir.exists() or any(path.exists() for path in bad_outputs):
            return False, "missing refresh_action_boundary CLI path created output directories or wrote frozen-replay artifacts before source validation failed"
        return True, (
            "the real frozen replay CLI rejects current_evidence_summary.json without "
            "source_freshness.refresh_action_boundary before creating output directories or writing "
            "summary/yearly/report/metadata artifacts"
        )
    finally:
        fixture_path.unlink(missing_ok=True)
        for path in bad_outputs:
            path.unlink(missing_ok=True)


def run_missing_refresh_action_boundary_field_fixture(
    current_evidence: dict[str, Any],
    tmp_parent: Path,
) -> tuple[bool, str]:
    fixture_path = tmp_parent / "missing_refresh_action_boundary_field_current_evidence_summary.json"
    bad_output_dir = tmp_parent / "missing_refresh_action_boundary_field_nested_output" / "artifacts"
    bad_outputs = [
        bad_output_dir / "missing_refresh_action_boundary_field_should_not_write_summary.csv",
        bad_output_dir / "missing_refresh_action_boundary_field_should_not_write_yearly.csv",
        bad_output_dir / "missing_refresh_action_boundary_field_should_not_write.md",
        bad_output_dir / "missing_refresh_action_boundary_field_should_not_write_metadata.json",
    ]
    bad_payload = json.loads(json.dumps(current_evidence))
    bad_payload["source_freshness"]["refresh_action_boundary"].pop("not_real_money_evidence", None)
    try:
        fixture_path.write_text(json.dumps(bad_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                GENERATOR.name,
                "--current-evidence-json",
                str(fixture_path),
                "--summary-output",
                str(bad_outputs[0]),
                "--yearly-output",
                str(bad_outputs[1]),
                "--report-output",
                str(bad_outputs[2]),
                "--metadata-output",
                str(bad_outputs[3]),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if result.returncode == 0:
            return False, "evaluate_frozen_portfolios.py unexpectedly accepted refresh_action_boundary without not_real_money_evidence"
        combined_output = f"{result.stdout}\n{result.stderr}"
        if "source_freshness.refresh_action_boundary is missing fields: not_real_money_evidence" not in combined_output:
            return False, "missing refresh_action_boundary field failure no longer names the missing no-real-money flag"
        if bad_output_dir.exists() or any(path.exists() for path in bad_outputs):
            return False, "missing refresh_action_boundary field CLI path created output directories or wrote frozen-replay artifacts before source validation failed"
        return True, (
            "the real frozen replay CLI rejects current_evidence_summary.json without "
            "source_freshness.refresh_action_boundary.not_real_money_evidence before creating output directories or "
            "writing summary/yearly/report/metadata artifacts"
        )
    finally:
        fixture_path.unlink(missing_ok=True)
        for path in bad_outputs:
            path.unlink(missing_ok=True)


def run_false_refresh_accounting_fixture(
    current_evidence: dict[str, Any],
    tmp_parent: Path,
) -> tuple[bool, str]:
    fixture_path = tmp_parent / "false_refresh_accounting_current_evidence_summary.json"
    bad_output_dir = tmp_parent / "false_refresh_accounting_nested_output" / "artifacts"
    bad_outputs = [
        bad_output_dir / "false_refresh_accounting_should_not_write_summary.csv",
        bad_output_dir / "false_refresh_accounting_should_not_write_yearly.csv",
        bad_output_dir / "false_refresh_accounting_should_not_write.md",
        bad_output_dir / "false_refresh_accounting_should_not_write_metadata.json",
    ]
    bad_payload = json.loads(json.dumps(current_evidence))
    bad_payload["source_freshness"]["refresh_action_boundary"][
        "clean_empty_refresh_counts_as_forward_performance"
    ] = True
    try:
        fixture_path.write_text(json.dumps(bad_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                GENERATOR.name,
                "--current-evidence-json",
                str(fixture_path),
                "--summary-output",
                str(bad_outputs[0]),
                "--yearly-output",
                str(bad_outputs[1]),
                "--report-output",
                str(bad_outputs[2]),
                "--metadata-output",
                str(bad_outputs[3]),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if result.returncode == 0:
            return False, "evaluate_frozen_portfolios.py unexpectedly accepted refresh_action_boundary.clean_empty_refresh_counts_as_forward_performance=true"
        combined_output = f"{result.stdout}\n{result.stderr}"
        if (
            "source_freshness.refresh_action_boundary must mark "
            "clean_empty_refresh_counts_as_forward_performance=false"
            not in combined_output
        ):
            return False, "weakened refresh-accounting failure no longer names the clean-empty forward-performance flag"
        if bad_output_dir.exists() or any(path.exists() for path in bad_outputs):
            return False, "weakened refresh-accounting CLI path created output directories or wrote frozen-replay artifacts before source validation failed"
        return True, (
            "the real frozen replay CLI rejects current_evidence_summary.json with "
            "source_freshness.refresh_action_boundary.clean_empty_refresh_counts_as_forward_performance=true "
            "before creating output directories or writing summary/yearly/report/metadata artifacts"
        )
    finally:
        fixture_path.unlink(missing_ok=True)
        for path in bad_outputs:
            path.unlink(missing_ok=True)


def run_missing_rebuild_validation_contract_fixture(
    current_evidence: dict[str, Any],
    tmp_parent: Path,
) -> tuple[bool, str]:
    fixture_path = tmp_parent / "missing_rebuild_validation_contract_current_evidence_summary.json"
    bad_output_dir = tmp_parent / "missing_rebuild_validation_contract_nested_output" / "artifacts"
    bad_outputs = [
        bad_output_dir / "missing_rebuild_validation_contract_should_not_write_summary.csv",
        bad_output_dir / "missing_rebuild_validation_contract_should_not_write_yearly.csv",
        bad_output_dir / "missing_rebuild_validation_contract_should_not_write.md",
        bad_output_dir / "missing_rebuild_validation_contract_should_not_write_metadata.json",
    ]
    bad_payload = json.loads(json.dumps(current_evidence))
    bad_payload.pop("rebuild_validation_contract", None)
    try:
        fixture_path.write_text(json.dumps(bad_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                GENERATOR.name,
                "--current-evidence-json",
                str(fixture_path),
                "--summary-output",
                str(bad_outputs[0]),
                "--yearly-output",
                str(bad_outputs[1]),
                "--report-output",
                str(bad_outputs[2]),
                "--metadata-output",
                str(bad_outputs[3]),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if result.returncode == 0:
            return False, "evaluate_frozen_portfolios.py unexpectedly accepted missing rebuild_validation_contract"
        combined_output = f"{result.stdout}\n{result.stderr}"
        if "missing rebuild_validation_contract" not in combined_output:
            return False, "missing rebuild_validation_contract failure no longer names the required current bridge rebuild contract"
        if bad_output_dir.exists() or any(path.exists() for path in bad_outputs):
            return False, "missing rebuild_validation_contract CLI path created output directories or wrote frozen-replay artifacts before source validation failed"
        return True, (
            "the real frozen replay CLI rejects current_evidence_summary.json without "
            "rebuild_validation_contract before creating output directories or writing summary/yearly/report/metadata artifacts"
        )
    finally:
        fixture_path.unlink(missing_ok=True)
        for path in bad_outputs:
            path.unlink(missing_ok=True)


def run_weakened_rebuild_validation_contract_fixture(
    current_evidence: dict[str, Any],
    tmp_parent: Path,
) -> tuple[bool, str]:
    fixture_path = tmp_parent / "weakened_rebuild_validation_contract_current_evidence_summary.json"
    bad_output_dir = tmp_parent / "weakened_rebuild_validation_contract_nested_output" / "artifacts"
    bad_outputs = [
        bad_output_dir / "weakened_rebuild_validation_contract_should_not_write_summary.csv",
        bad_output_dir / "weakened_rebuild_validation_contract_should_not_write_yearly.csv",
        bad_output_dir / "weakened_rebuild_validation_contract_should_not_write.md",
        bad_output_dir / "weakened_rebuild_validation_contract_should_not_write_metadata.json",
    ]
    bad_payload = json.loads(json.dumps(current_evidence))
    bad_payload["rebuild_validation_contract"][
        "upstream_refresh_order_is_provenance_metadata_only"
    ] = False
    try:
        fixture_path.write_text(json.dumps(bad_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                GENERATOR.name,
                "--current-evidence-json",
                str(fixture_path),
                "--summary-output",
                str(bad_outputs[0]),
                "--yearly-output",
                str(bad_outputs[1]),
                "--report-output",
                str(bad_outputs[2]),
                "--metadata-output",
                str(bad_outputs[3]),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if result.returncode == 0:
            return False, (
                "evaluate_frozen_portfolios.py unexpectedly accepted a weakened "
                "rebuild_validation_contract provenance flag"
            )
        combined_output = f"{result.stdout}\n{result.stderr}"
        if (
            "rebuild_validation_contract must mark "
            "upstream_refresh_order_is_provenance_metadata_only=true"
            not in combined_output
        ):
            return False, (
                "weakened rebuild_validation_contract failure no longer names the "
                "provenance-only rebuild-order flag"
            )
        if bad_output_dir.exists() or any(path.exists() for path in bad_outputs):
            return False, (
                "weakened rebuild_validation_contract CLI path created output directories "
                "or wrote frozen-replay artifacts before source validation failed"
            )
        return True, (
            "the real frozen replay CLI rejects current_evidence_summary.json when "
            "rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only=false "
            "before creating output directories or writing summary/yearly/report/metadata artifacts"
        )
    finally:
        fixture_path.unlink(missing_ok=True)
        for path in bad_outputs:
            path.unlink(missing_ok=True)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_parent = prepare_tmp_parent()
    scratch_meta = {
        "tmp_parent": str(tmp_parent),
        "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
        "tmp_parent_cleared_before_fixture_run": True,
    }
    text = REPORT.read_text(encoding="utf-8")
    generator_text = GENERATOR.read_text(encoding="utf-8")
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    evidence_boundary_metadata = metadata.get("evidence_boundary_metadata")
    if not isinstance(evidence_boundary_metadata, dict):
        evidence_boundary_metadata = {}
    current_evidence = json.loads(CURRENT_EVIDENCE.read_text(encoding="utf-8"))
    current_context = current_paper_context(current_evidence)
    recommendation_read = str(current_context["recommendation_context_read"])
    boundary_info = current_boundary_info(current_evidence)
    boundary_date = str(boundary_info["date"])
    source_freshness = current_source_freshness_context(current_evidence)
    refresh_action = current_refresh_action_boundary_context(current_evidence)
    operator_read_gate = current_operator_read_gate_context(current_evidence)
    rebuild_validation_contract = current_rebuild_validation_contract_context(current_evidence)
    expected_sources = expected_source_files()
    first_18 = "\n".join(text.splitlines()[:18])
    expected_operator_read_gate_line = (
        "- Operator read gate: `operator_read_gate.requires_refresh_before_evidence_read="
        f"{str(operator_read_gate['requires_refresh_before_evidence_read']).lower()}`; "
        f"gate status = `{operator_read_gate['gate_status']}`; "
        f"recommended command = `{operator_read_gate['recommended_command']}`; "
        f"read: {operator_read_gate['read']} "
        "This is instruction/evidence-read routing only, not frozen-replay performance evidence."
    )
    expected_rebuild_validation_contract_line = (
        "- Current bridge rebuild order: `current_evidence_summary.json` `rebuild_validation_contract` "
        f"routes source-byte changes through {' -> '.join(rebuild_validation_contract['upstream_refresh_commands'])} "
        "before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, "
        "not frozen-replay performance, settled ROI, live profitability, promotion readiness, "
        "bankroll guidance, or real-money evidence."
    )
    expected_open_read = (
        f"{current_context['open_settlements']} open primary settlement row(s) awaiting result/payout evidence"
        if current_context["open_settlements"]
        else "no open primary settlement rows awaiting result/payout evidence"
    )
    expected_queue_state_read = (
        f"Settlement queue state: `{current_context['open_settlement_queue_state']}`; "
        f"{current_context['open_settlement_context']}; detail: "
        f"{current_context['open_settlement_queue_read']}"
    )
    expected_settlement_queue_boundary = "Open/closed queue state is workflow context"
    forbidden_open_identity = (
        "Current open row: `none`" if current_context["open_settlements"] == 0 else ""
    )
    bad_generated_at_ok, bad_generated_at_detail = run_bad_current_evidence_generated_at_fixture(current_evidence, tmp_parent)
    missing_operator_read_gate_ok, missing_operator_read_gate_detail = run_missing_operator_read_gate_fixture(
        current_evidence,
        tmp_parent,
    )
    missing_freshness_ok, missing_freshness_detail = run_missing_source_freshness_reference_fixture(
        current_evidence,
        tmp_parent,
    )
    missing_refresh_action_ok, missing_refresh_action_detail = run_missing_refresh_action_boundary_fixture(
        current_evidence,
        tmp_parent,
    )
    missing_refresh_action_field_ok, missing_refresh_action_field_detail = (
        run_missing_refresh_action_boundary_field_fixture(
            current_evidence,
            tmp_parent,
        )
    )
    false_refresh_accounting_ok, false_refresh_accounting_detail = run_false_refresh_accounting_fixture(
        current_evidence,
        tmp_parent,
    )
    missing_rebuild_validation_contract_ok, missing_rebuild_validation_contract_detail = (
        run_missing_rebuild_validation_contract_fixture(
            current_evidence,
            tmp_parent,
        )
    )
    weakened_rebuild_validation_contract_ok, weakened_rebuild_validation_contract_detail = (
        run_weakened_rebuild_validation_contract_fixture(
            current_evidence,
            tmp_parent,
        )
    )

    checks: list[dict[str, Any]] = []
    checks.append(require(
        current_boundary_info({
            "source_freshness": {
                "generated_reference_date": "2026-06-20",
                "generated_reference_timezone": "America/New_York",
                "generated_date": "2026-06-21",
            },
            "generated_at": "2026-06-22T01:00:00+02:00",
        }) == {
            "date": "2026-06-20",
            "source": "source_freshness.generated_reference_date",
            "timezone": "America/New_York",
        }
        and current_boundary_info({
            "source_freshness": {"generated_date": "2026-06-21"},
            "generated_at": "2026-06-22T01:00:00+02:00",
        }) == {
            "date": "2026-06-21",
            "source": "source_freshness.generated_date",
            "timezone": None,
        }
        and current_boundary_info({
            "generated_at": "2026-06-22T01:00:00+02:00",
        }) == {
            "date": "2026-06-22",
            "source": "generated_at_date",
            "timezone": None,
        },
        "current_boundary_date_source_precedence",
        "the frozen replay boundary date helper prefers the New York reference date, then the bridge generated date, then generated_at only as a fallback",
    ))
    checks.append(require(
        bad_generated_at_ok,
        "bad_current_evidence_generated_at_fails_fast",
        bad_generated_at_detail,
    ))
    checks.append(require(
        missing_operator_read_gate_ok,
        "missing_current_evidence_operator_read_gate_fails_fast",
        missing_operator_read_gate_detail,
    ))
    checks.append(require(
        missing_freshness_ok,
        "missing_current_evidence_source_freshness_reference_fails_fast",
        missing_freshness_detail,
    ))
    checks.append(require(
        missing_refresh_action_ok,
        "missing_current_evidence_refresh_action_boundary_fails_fast",
        missing_refresh_action_detail,
    ))
    checks.append(require(
        missing_refresh_action_field_ok,
        "missing_current_evidence_refresh_action_boundary_field_fails_fast",
        missing_refresh_action_field_detail,
    ))
    checks.append(require(
        false_refresh_accounting_ok,
        "false_current_evidence_refresh_accounting_fails_fast",
        false_refresh_accounting_detail,
    ))
    checks.append(require(
        missing_rebuild_validation_contract_ok,
        "missing_current_evidence_rebuild_validation_contract_fails_fast",
        missing_rebuild_validation_contract_detail,
    ))
    checks.append(require(
        weakened_rebuild_validation_contract_ok,
        "weakened_current_evidence_rebuild_validation_contract_fails_fast",
        weakened_rebuild_validation_contract_detail,
    ))
    checks.append(require(
        f"## Current evidence boundary ({boundary_date})" in first_18
        and "historical frozen replay" in first_18
        and "not a live paper-trade ledger" in first_18,
        "top_boundary_labels_historical_replay",
        "the report opens by labeling the frozen evaluation as a historical replay rather than a live paper ledger",
    ))
    checks.append(require(
        f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}" in first_18
        and f'VALID_EVIDENCE_SCOPE = "{VALID_EVIDENCE_SCOPE}"' in generator_text
        and metadata.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
        and evidence_boundary_metadata.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE,
        "frozen_replay_valid_evidence_scope_visible",
        "the report, generator, metadata sidecar, and machine-readable boundary now expose the raw frozen-replay valid_evidence_scope so the chronological holdout replay cannot be copied as live paper-trade, promotion, bankroll, or real-money evidence",
    ))
    checks.append(require(
        "not real-money evidence" in first_18
        and f"{current_context['roi_complete_settled']} ROI-complete primary-lane settlements" in first_18
        and current_context["rule_mix_read"] in first_18
        and expected_open_read in first_18
        and "settlement-queue state is operability metadata only" in first_18
        and f"does not change the {current_context['first_read_current']}/{current_context['first_read_threshold']} ROI-complete first-read count" in first_18
        and expected_queue_state_read in first_18
        and (not forbidden_open_identity or forbidden_open_identity not in first_18)
        and "detail: Settlement queue state" not in first_18
        and f"Latest primary recommendation context: {recommendation_read}" in first_18
        and expected_settlement_queue_boundary in first_18
        and "not a bet-ready ticket or forward-performance proof" in first_18
        and "cannot prove live profitability or justify a strategy change" in first_18
        and expected_operator_read_gate_line in first_18
        and "instruction/evidence-read routing only" in first_18
        and "`CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json`" in first_18
        and "the combined `operator_status_context` + `source_freshness` + `operator_read_gate` route" in first_18
        and "wrapper-refresh, missing-output, freshness routing, or read-gate routing is source-readiness context" in first_18
        and "not frozen-replay performance evidence" in first_18
        and expected_rebuild_validation_contract_line in first_18,
        "tiny_current_paper_sample_not_live_or_real_money_evidence_boundary",
        "the top boundary says frozen replay is not real-money or live-profitability evidence, derives the current tiny settled-paper/settlement-queue/recommendation-state/read-gate context from the current-evidence bridge without upgrading strategy posture, and routes any current top-card quote through the combined operator-status/source-freshness/operator-read-gate path plus the settlement-audit/current-bridge/bridge-validator rebuild order first",
    ))
    checks.append(require(
        "Phase 7 beat Phase 8 on frozen 2024-2025 holdout" in first_18
        and "+38.68%` on 175 races" in first_18
        and "+21.45%` on 118 races" in first_18
        and "Phase 8 remains shadow/watch" in first_18,
        "phase7_over_phase8_holdout_posture_visible",
        "the stricter holdout comparison remains visible and keeps Phase 8 in shadow/watch instead of deployment-upgrade status",
    ))
    checks.append(require(
        "`OP_DURABLE_K7` remains the safest current paper anchor" in first_18
        and "`CD_CORE_K8` is the paper companion" in first_18
        and "`OP_REFINED_K7` and the rest of Phase 8 need forward observation" in first_18,
        "current_rule_roles_visible",
        "the top boundary preserves OP_DURABLE_K7 as anchor, CD_CORE_K8 as paper companion, and OP_REFINED/Phase 8 as observation-only",
    ))
    checks.append(require(
        "`BAQ` is not `BEL`" in first_18
        and "unsupported aliasing" in first_18,
        "baq_not_bel_boundary_visible",
        "the report keeps the BAQ/BEL coverage break from being patched by aliasing",
    ))
    checks.append(require(
        "materially closer to a deployment-style replay than shuffled splits" in text
        and "still needs train-only walk-forward context and live paper settlement" in text,
        "why_this_matters_keeps_walkforward_and_settlement_gap",
        "the methodology section now says chronology is better than shuffled splits but still needs train-only walk-forward and live settlement context",
    ))
    checks.append(require(
        "historical replay P&L" in text
        and "does **not** by itself prove live profitability" in text
        and "Phase 7 current-paper rules" in text
        and "Phase 7 current-paper rule portfolio" in text
        and "current rule mapping explicitly avoids unsupported aliasing" in text
        and "Phase 7 live portfolio" not in text
        and "Phase 7 live rules" not in text
        and "current live-rule mapping" not in text
        and "actual betting P&L" not in text
        and "much more encouraging" not in text,
        "interpretation_replaces_overstrong_pnl_language",
        "interpretation now uses historical-replay P&L language, labels the Phase 7 replay as current-paper rules rather than a live portfolio, and removes old overstrong encouragement / actual-betting phrasing",
    ))
    checks.append(require(
        "ROI-complete live paper-trade settlements" in text
        and "live paper trading" in text
        and "before any real-money discussion" in text,
        "next_loop_requires_settled_paper_before_real_money",
        "the recommended loop now ends at live paper trading and requires ROI-complete settlements before any real-money discussion",
    ))
    checks.append(require(
        "Re-check this report boundary with `python3 validate_frozen_portfolio_eval_caution.py` after edits." in text,
        "self_recheck_command_documented",
        "the report names the narrow validator that protects this evidence boundary",
    ))
    checks.append(require(
        'CURRENT_EVIDENCE_SUMMARY = BASE / "current_evidence_summary.json"' in generator_text
        and "def load_current_evidence_summary(" in generator_text
        and "def current_operator_ledger_line" in generator_text
        and "## Current evidence boundary" in generator_text
        and "historical frozen replay" in generator_text
        and "not a live paper-trade ledger and not real-money evidence" in generator_text
        and "Valid evidence scope" in generator_text
        and "valid_evidence_scope={VALID_EVIDENCE_SCOPE}" in generator_text
        and "ROI-complete primary-lane settlements" in generator_text
        and "open primary settlement row(s) awaiting result/payout evidence" in generator_text
        and "settlement-queue state is operability metadata only" in generator_text
        and "open_settlement_queue_by_rule" in generator_text
        and "open_settlement_queue_state must match current_paper_status.primary.open_settlements" in generator_text
        and "detail_read must not nest the settlement queue state wrapper" in generator_text
        and "Settlement queue state: `" in generator_text
        and "recommendation_context_read" in generator_text
        and "Latest primary recommendation context" in generator_text
        and "not a bet-ready ticket" in generator_text
        and "or forward-performance proof" in generator_text
        and "the combined `operator_status_context` + `source_freshness` + `operator_read_gate` route" in generator_text
        and "not frozen-replay performance evidence" in generator_text
        and "def has_timezone_aware_timestamp" in generator_text
        and "def require_current_evidence_generated_at" in generator_text
        and "generated_at must be timezone-aware ISO provenance metadata" in generator_text
        and "def current_refresh_action_boundary_context" in generator_text
        and "def current_refresh_action_boundary_line" in generator_text
        and "REQUIRED_REFRESH_ACTION_BOUNDARY_TEXT_FIELDS" in generator_text
        and "REQUIRED_REFRESH_ACTION_BOUNDARY_BOOL_FIELDS" in generator_text
        and "def current_operator_read_gate_context" in generator_text
        and "def current_operator_read_gate_line" in generator_text
        and "REQUIRED_OPERATOR_READ_GATE_TEXT_FIELDS" in generator_text
        and "REQUIRED_OPERATOR_READ_GATE_BOOL_FIELDS" in generator_text
        and "operator_read_gate must match current_paper_status.operator_read_gate" in generator_text
        and "operator_read_gate.requires_refresh_before_evidence_read" in generator_text
        and "instruction/evidence-read routing only" in generator_text
        and "def current_rebuild_validation_contract_context" in generator_text
        and "def current_rebuild_validation_contract_line" in generator_text
        and "REQUIRED_REBUILD_REFRESH_ORDER" in generator_text
        and "rebuild_validation_contract upstream order drifted" in generator_text
        and "Current bridge rebuild order" in generator_text
        and "settled ROI, live profitability, promotion readiness" in generator_text
        and "source_freshness.refresh_action_boundary is missing fields" in generator_text
        and "valid use" in generator_text
        and "source action counts as current before" in generator_text
        and "can settle open rows by itself" in generator_text
        and "clean-empty refresh counts as" in generator_text
        and "missing/invalid artifacts count as" in generator_text
        and "historical replay P&L" in generator_text
        and "Phase 7 current-paper rules" in generator_text
        and "Phase 7 current-paper rule portfolio" in generator_text
        and "current rule mapping explicitly avoids unsupported aliasing" in generator_text
        and "Phase 7 live portfolio" not in generator_text
        and "Phase 7 live rules" not in generator_text
        and "current live-rule mapping" not in generator_text
        and "before any real-money discussion" in generator_text
        and "actual betting P&L" not in generator_text
        and "much more encouraging" not in generator_text,
        "generator_preserves_current_boundary",
        "the frozen-portfolio generator now emits the same historical-replay / no-live-proof caution, sources current paper counts/settlement-queue/recommendation-state/read-gate context from the bridge, carries the settlement-audit -> current-bridge -> bridge-validator rebuild contract, and keeps the current-paper Phase 7 label instead of regenerating old overstrong or live-portfolio report wording",
    ))
    checks.append(require(
        "## Source reproducibility" in text
        and "fingerprints are audit/reproducibility metadata only, not performance evidence" in text
        and (
            "Machine-readable evidence boundary: "
            "`frozen_portfolio_eval_metadata.json.evidence_boundary_metadata`"
        ) in text
        and "frozen chronological holdout replay metadata" in text
        and "requires the combined current-operator route before top-card quotation" in text
        and "not live-profitability, promotion, anchor-change, Phase 8 promotion, BAQ/BEL substitution, or real-money evidence" in text
        and f"Source freshness provenance: bridge reference `{source_freshness['generated_reference_date']}` (`{source_freshness['generated_reference_timezone']}`)" in text
        and f"comparison `{source_freshness['staleness_comparison_source']}` = `{source_freshness['staleness_comparison_date']}`" in text
        and f"right-now state `{source_freshness['right_now_freshness_state']}`" in text
        and f"refresh before right-now use = `{source_freshness['requires_refresh_before_right_now_use']}`" in text
        and str(source_freshness["read"]) in text
        and f"Refresh action boundary: `{refresh_action['command']}`" in text
        and f"valid use = {refresh_action['valid_use']}" in text
        and f"required before right-now use = `{refresh_action['required_before_right_now_instruction_use']}`" in text
        and (
            "source action counts as current before refresh = "
            f"`{refresh_action['source_action_counts_as_current_instruction_before_refresh']}`"
        ) in text
        and f"can update operator surfaces = `{refresh_action['wrapper_refresh_can_update_operator_surfaces']}`" in text
        and f"can settle open rows by itself = `{refresh_action['wrapper_refresh_can_settle_open_rows_by_itself']}`" in text
        and f"counts as ROI-complete evidence by itself = `{refresh_action['wrapper_refresh_counts_as_roi_complete_evidence_by_itself']}`" in text
        and f"clean-empty refresh counts as forward performance = `{refresh_action['clean_empty_refresh_counts_as_forward_performance']}`" in text
        and (
            "missing/invalid artifacts count as a clean quiet day = "
            f"`{refresh_action['missing_or_invalid_artifact_counts_as_clean_quiet_day']}`"
        ) in text
        and (
            "not forward/live-profitability/promotion/real-money evidence = "
            f"`{refresh_action['not_forward_performance_evidence']}` / "
            f"`{refresh_action['not_live_profitability_evidence']}` / "
            f"`{refresh_action['not_promotion_readiness_evidence']}` / "
            f"`{refresh_action['not_real_money_evidence']}`"
        ) in text
        and str(refresh_action["read"]) in text
        and expected_operator_read_gate_line in text
        and expected_rebuild_validation_contract_line in text
        and "source-routing metadata only, not frozen-replay or live-performance evidence" in text
        and "Phase 8 frozen rule definitions are embedded in `evaluate_frozen_portfolios.py`" in text
        and "same values are copied into `frozen_portfolio_eval_metadata.json`" in text
        and all(format_source_fingerprint(label, info) in text for label, info in expected_sources.items()),
        "source_fingerprints_visible_in_report",
        "the generated report now exposes exact source-byte fingerprints plus the full bridge source-freshness reference/readout, wrapper-refresh action boundary, operator-read-gate route, and current bridge rebuild order without treating them as performance evidence",
    ))
    checks.append(require(
        evidence_boundary_metadata.get("artifact_role") == "frozen chronological holdout replay metadata"
        and evidence_boundary_metadata.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
        and evidence_boundary_metadata.get("valid_use") == "historical frozen replay reproducibility and posture metadata"
        and evidence_boundary_metadata.get("source_scope")
        == "cached major-track race-level dataset + phase7_live_rules.json + embedded Phase 8 frozen rule definitions"
        and evidence_boundary_metadata.get("holdout_years") == [2024, 2025]
        and evidence_boundary_metadata.get("train_end_year") == 2023
        and "Phase 7 current-paper rules remain ahead of Phase 8 frozen rules"
        in evidence_boundary_metadata.get("phase7_over_phase8_holdout_read", "")
        and evidence_boundary_metadata.get("phase7_holdout_roi")
        == metadata.get("holdout_summary", {}).get("phase7_live", {}).get("roi")
        and evidence_boundary_metadata.get("phase7_holdout_races") == 175
        and evidence_boundary_metadata.get("phase8_holdout_roi")
        == metadata.get("holdout_summary", {}).get("phase8_frozen", {}).get("roi")
        and evidence_boundary_metadata.get("phase8_holdout_races") == 118
        and evidence_boundary_metadata.get("current_operator_routing_requires_combined_route") is True
        and evidence_boundary_metadata.get("current_operator_route_source") == "current_evidence_summary.json"
        and evidence_boundary_metadata.get("current_operator_route")
        == ["operator_status_context", "source_freshness", "operator_read_gate"]
        and evidence_boundary_metadata.get("current_bridge_rebuild_route_source")
        == "current_evidence_summary.json.rebuild_validation_contract"
        and evidence_boundary_metadata.get("current_bridge_rebuild_order") == REQUIRED_REBUILD_REFRESH_ORDER
        and evidence_boundary_metadata.get("current_bridge_rebuild_route_valid_use")
        == "provenance/rebuild metadata only before quoting CURRENT_EVIDENCE_SUMMARY after source-byte changes"
        and evidence_boundary_metadata.get("not_live_paper_trade_ledger") is True
        and evidence_boundary_metadata.get("not_current_day_scanner_result") is True
        and evidence_boundary_metadata.get("not_live_profitability_evidence") is True
        and evidence_boundary_metadata.get("not_real_money_evidence") is True
        and evidence_boundary_metadata.get("not_promotion_readiness_evidence") is True
        and evidence_boundary_metadata.get("not_anchor_change_evidence") is True
        and evidence_boundary_metadata.get("not_companion_change_evidence") is True
        and evidence_boundary_metadata.get("not_phase8_promotion_evidence") is True
        and evidence_boundary_metadata.get("not_baq_as_bel_evidence") is True
        and evidence_boundary_metadata.get("baq_as_bel_substitution_allowed") is False
        and "do not treat historical frozen replay P&L as live paper-trade ledger evidence"
        in evidence_boundary_metadata.get("non_goals", [])
        and "do not promote Phase 8 or OP_REFINED_K7 from this artifact"
        in evidence_boundary_metadata.get("non_goals", [])
        and "do not change the OP_DURABLE_K7 anchor from this artifact"
        in evidence_boundary_metadata.get("non_goals", [])
        and "do not substitute BAQ for BEL" in evidence_boundary_metadata.get("non_goals", [])
        and "EVIDENCE_BOUNDARY_METADATA_ROLE" in generator_text
        and "def frozen_replay_evidence_boundary_metadata" in generator_text
        and "current_operator_routing_requires_combined_route" in generator_text,
        "metadata_sidecar_publishes_machine_readable_evidence_boundary",
        "the frozen replay metadata sidecar now publishes a machine-readable evidence_boundary_metadata block that pins the frozen holdout scope, combined current-operator route, current bridge rebuild route, Phase 7-over-Phase 8 holdout read, no BAQ-as-BEL substitution, and no-live/no-promotion/no-anchor-change/no-real-money boundaries",
    ))
    checks.append(require(
        metadata.get("artifact") == "frozen_portfolio_eval"
        and metadata.get("schema_version") == 1
        and metadata.get("source_scope") == "cached major-track race-level dataset + phase7_live_rules.json + embedded Phase 8 frozen rule definitions"
        and metadata.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
        and metadata.get("evidence_boundary") == "historical frozen replay only; not a live paper-trade ledger, live-profitability proof, promotion-ready evidence, or real-money evidence"
        and metadata.get("evidence_boundary_metadata") == evidence_boundary_metadata
        and metadata.get("current_boundary_date") == boundary_date
        and metadata.get("current_boundary_date_source") == boundary_info["source"]
        and metadata.get("current_boundary_reference_timezone") == boundary_info["timezone"]
        and metadata.get("current_source_freshness") == source_freshness
        and metadata.get("current_refresh_action_boundary") == refresh_action
        and metadata.get("current_operator_read_gate") == operator_read_gate
        and metadata.get("current_evidence_rebuild_validation_contract") == rebuild_validation_contract
        and metadata.get("current_evidence_source", {}).get("path") == "current_evidence_summary.json"
        and metadata.get("current_evidence_source", {}).get("generated_at") == current_evidence.get("generated_at")
        and frozen_eval.has_timezone_aware_timestamp(metadata.get("current_evidence_source", {}).get("generated_at"))
        and metadata.get("current_paper_context") == current_context
        and metadata.get("holdout_years") == [2024, 2025]
        and metadata.get("train_end_year") == 2023
        and metadata.get("source_files") == expected_sources
        and metadata.get("outputs", {}).get("report_md") == "FROZEN_PORTFOLIO_EVAL.md"
        and metadata.get("outputs", {}).get("metadata_json") == "frozen_portfolio_eval_metadata.json"
        and metadata.get("row_counts", {}).get("summary_csv") == 60
        and metadata.get("row_counts", {}).get("yearly_csv") == 30
        and metadata.get("holdout_summary", {}).get("phase7_live", {}).get("races") == 175
        and metadata.get("holdout_summary", {}).get("phase8_frozen", {}).get("races") == 118
        and "not live-profitability proof" in metadata.get("non_goals", []),
        "metadata_sidecar_matches_sources_and_boundary",
        "the metadata sidecar carries the same source fingerprints, current-evidence bridge pointer, full source-freshness provenance, wrapper-refresh action boundary, operator-read-gate route, current bridge rebuild-validation contract, current settlement-queue/recommendation-state context, frozen-replay evidence boundary, output map, row counts, and Phase 7-over-Phase 8 holdout summary for automation",
    ))

    payload: dict[str, Any] = {
        "suite": "frozen_portfolio_eval_caution",
        "suite_status": "pass",
        "total_checks": len(checks),
        "check_count": len(checks),
        "report_path": rel(OUT_MD),
        "source_report": rel(REPORT),
        "source_generator": rel(GENERATOR),
        "source_metadata": rel(METADATA),
        "rebuild_command": REBUILD_COMMAND,
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "evidence_boundary": {
            "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
            "artifact_role": "frozen-portfolio replay caution validator",
            "valid_use": "chronological holdout replay/report-boundary validation only",
            "not_settled_roi_evidence": True,
            "not_live_profitability_evidence": True,
            "not_promotion_readiness_evidence": True,
            "not_bankroll_guidance": True,
            "not_real_money_evidence": True,
        },
        "summary": {
            "suite_read": (
                "FROZEN_PORTFOLIO_EVAL.md now carries the current evidence boundary at the source: "
                f"historical frozen replay, valid_evidence_scope={VALID_EVIDENCE_SCOPE}, not live paper-trade or real-money evidence; Phase 7 still beats Phase 8 on frozen 2024-2025 holdout; "
                "OP_DURABLE_K7 remains the safest current paper anchor with CD_CORE_K8 as paper companion; OP_REFINED_K7 / Phase 8 remain shadow-watch; "
                "BAQ is not BEL; the current settlement-queue/recommendation-state/operator-read-gate context is sourced from current_evidence_summary.json and remains operability metadata rather than added ROI-complete evidence; current top-card quotes must go through the combined operator_status_context/source_freshness/operator_read_gate route before use; a decision-grade settled paper sample is still required before promotion or bankroll discussion; the generator now preserves that boundary when the report is rebuilt; and the report/metadata sidecar expose exact source-byte fingerprints for reproducibility without turning hashes into performance evidence."
                " The metadata sidecar now also publishes machine-readable evidence_boundary_metadata for the frozen holdout scope, combined current-operator route, current bridge rebuild route, and no-live/no-promotion/no-anchor-change/no-real-money boundary. The generator now also rejects malformed or timezone-naive current-evidence generated_at provenance, missing operator_read_gate provenance, incomplete source_freshness reference provenance, missing refresh_action_boundary provenance, incomplete refresh_action_boundary command/read/Boolean evidence flags, weakened wrapper-refresh accounting, and missing rebuild_validation_contract provenance before republishing the bridge snapshot."
                " It now also rejects weakened rebuild_validation_contract provenance before writing frozen-replay artifacts."
            )
        },
        "current_evidence_rebuild_validation_contract_read": rebuild_validation_contract,
        "evidence_boundary_metadata": evidence_boundary_metadata,
        "scratch": scratch_meta,
        "checks": checks,
    }

    md_lines = [
        "# Frozen Portfolio Evaluation Caution Validation",
        "",
        f"Status: **{payload['suite_status'].upper()}**",
        f"Checks: **{len(checks)}/{len(checks)}**",
        f"Source report: `{rel(REPORT)}`",
        f"Source generator: `{rel(GENERATOR)}`",
        f"Source metadata: `{rel(METADATA)}`",
        f"Rebuild command: `{REBUILD_COMMAND}`",
        "",
        "## Current read",
        "",
        payload["summary"]["suite_read"],
        "",
        "## Evidence Boundary",
        "",
        f"- valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
        "- Boundary: this validator pass is chronological holdout replay/report-boundary validation only, not settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence.",
        "",
        "## Checks",
        "",
    ]
    for check in checks:
        md_lines.append(f"- `{check['check']}` — {check['detail']}")
    OUT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
