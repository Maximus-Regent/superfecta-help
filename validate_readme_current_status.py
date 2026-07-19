#!/usr/bin/env python3
"""
Validation for the README current-status block.

Purpose:
- keep the repo landing page aligned with the frozen evaluation standard
- stop stale research-only headline numbers from reappearing in fast-read status text
- pin the README's anchor / paper / benchmark / method-family summary to current frozen artifacts
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

BASE = Path(__file__).resolve().parent
README = BASE / "README.md"
PORTFOLIO_CSV = BASE / "portfolio_decision_card.csv"
METHOD_CSV = BASE / "method_family_decision_card.csv"
SCORECARD_CSV = BASE / "forward_evidence_scorecard.csv"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
OUT_DIR = BASE / "out" / "status_validation" / "readme_current_status"
OUT_MD = OUT_DIR / "readme_current_status_validation.md"
OUT_JSON = OUT_DIR / "readme_current_status_validation.json"
REBUILD_COMMAND = "python3 validate_readme_current_status.py"
API_ACCESS_ACTION_TEXT = "Sidecar action: refresh_daily_wrapper_before_evidence_read"
API_ACCESS_RECHECK_TEXT = "Recheck command: ./run_daily_portfolio_observation.sh"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"


def load_csv_map(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {str(row[key]): row for row in rows}


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "pass", "detail": detail}


def require_paths_exist(paths: list[Path], name: str, detail: str) -> dict[str, Any]:
    missing = [str(path.relative_to(BASE)) if BASE in path.parents else str(path) for path in paths if not path.exists()]
    if missing:
        raise AssertionError(f"{name}: {detail}; missing: {', '.join(missing)}")
    return {"check": name, "status": "pass", "detail": detail}


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

    return {
        "payload": payload,
        "read": {
            "source": source_name,
            "source_path": "decision_gate_minimums",
            "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
            "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
            "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
            "real_money_no_baq_as_bel_required": True,
        },
    }


def format_source_freshness_clause(requires_refresh: bool) -> str:
    if requires_refresh:
        return (
            "`operator_status_context` plus `source_freshness.requires_refresh_before_right_now_use=true` "
            "means refresh `./run_daily_portfolio_observation.sh` before using the saved best-action card "
            "as today's operator instruction when routing/freshness says to"
        )
    return (
        "`operator_status_context` plus `source_freshness.requires_refresh_before_right_now_use=false` "
        "means the saved best-action card is fresh against the current bridge, while operator routing "
        "remains source-readiness context rather than performance evidence"
    )


def is_api_access_context(text: str) -> bool:
    return any(marker in text for marker in ("API-access", "API access", "HTTP 403", "403 Client Error"))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the README current-status block")
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--current-evidence-json", type=Path, default=CURRENT_EVIDENCE_JSON)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def scorecard_gate_cli_contract_checks(
    scorecard_json_path: Path = SCORECARD_JSON,
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="readme_scorecard_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(scorecard_json_path).read_text(encoding="utf-8"))
        scorecard_path = tmp_root / "forward_evidence_scorecard.json"

        nonpositive_phase8_out_dir = tmp_root / "nonpositive_phase8" / "readme_current_status_validation"
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
                str(nonpositive_phase8_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not nonpositive_phase8_out_dir.exists()
                and "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer"
                in proc.stderr,
                "scorecard_nonpositive_phase8_floor_fails_before_artifacts",
                "validate_readme_current_status.py rejects a non-positive Phase 8 promotion-review scorecard gate before creating nested output directories or partial landing-page validation artifacts",
            )
        )

        nonpositive_real_money_out_dir = tmp_root / "nonpositive_real_money" / "readme_current_status_validation"
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
                str(nonpositive_real_money_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        checks.append(
            require(
                proc.returncode != 0
                and not nonpositive_real_money_out_dir.exists()
                and "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer"
                in proc.stderr,
                "scorecard_nonpositive_real_money_floor_fails_before_artifacts",
                "validate_readme_current_status.py rejects a non-positive real-money discussion scorecard gate before creating nested output directories or partial landing-page validation artifacts",
            )
        )

    return checks


def current_bridge_rebuild_cli_contract_checks(
    current_evidence_json_path: Path = CURRENT_EVIDENCE_JSON,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="readme_current_evidence_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(current_evidence_json_path).read_text(encoding="utf-8"))
        current_evidence_path = tmp_root / "current_evidence_summary.json"

        missing_contract_out_dir = tmp_root / "missing" / "readme_current_status_validation"
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
                "validate_readme_current_status.py rejects a current-evidence sidecar with no rebuild_validation_contract before creating nested output directories or partial landing-page validation artifacts",
            )
        )

        weakened_contract_out_dir = tmp_root / "weakened" / "readme_current_status_validation"
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
                "validate_readme_current_status.py rejects a current-evidence rebuild contract that no longer marks the rebuild order as provenance metadata only before creating nested output directories or partial landing-page validation artifacts",
            )
        )

    return checks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir)
    out_md = out_dir / OUT_MD.name
    out_json = out_dir / OUT_JSON.name

    readme_text = README.read_text(encoding="utf-8")
    if "## Current honest status" not in readme_text or "## If you are starting cold" not in readme_text or "## What is in this repo" not in readme_text:
        raise AssertionError("README is missing the expected current-status / cold-start section markers")
    status_block = readme_text.split("## Current honest status", 1)[1].split("## If you are starting cold", 1)[0]
    cold_start_block = readme_text.split("## If you are starting cold", 1)[1].split("## What is in this repo", 1)[0]

    portfolio = load_csv_map(PORTFOLIO_CSV, "method_id")
    method_family = load_csv_map(METHOD_CSV, "family_id")
    scorecard = load_csv_map(SCORECARD_CSV, "rule_id")
    scorecard_gate_context_read = scorecard_gate_context(args.scorecard_json)
    scorecard_json = scorecard_gate_context_read["payload"]
    current_evidence = json.loads(Path(args.current_evidence_json).read_text(encoding="utf-8"))
    scorecard_audit_route = current_evidence.get("scorecard_audit_route")
    if not isinstance(scorecard_audit_route, dict):
        raise AssertionError("current_evidence_summary.json must publish scorecard_audit_route as an object")
    scorecard_audit_gate_floor_snapshot = scorecard_audit_route.get("gate_floor_snapshot")
    if not isinstance(scorecard_audit_gate_floor_snapshot, dict):
        raise AssertionError("current_evidence_summary.json scorecard_audit_route must publish gate_floor_snapshot")
    rebuild_validation_contract = current_evidence.get("rebuild_validation_contract")
    if not isinstance(rebuild_validation_contract, dict):
        raise AssertionError("current_evidence_summary.json must publish rebuild_validation_contract as an object")
    upstream_refresh_order = rebuild_validation_contract.get("upstream_refresh_order")
    if not isinstance(upstream_refresh_order, list):
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract must publish upstream_refresh_order")
    expected_rebuild_order_commands = [
        "python3 paper_trade_settlement_audit.py",
        "python3 current_evidence_summary.py",
        "python3 validate_current_evidence_summary.py",
    ]
    try:
        sorted_rebuild_order = sorted(
            upstream_refresh_order,
            key=lambda row: int(row.get("order", 0)) if isinstance(row, dict) else 0,
        )
    except Exception as exc:  # pragma: no cover - defensive validator context
        raise AssertionError("rebuild_validation_contract upstream_refresh_order has invalid order values") from exc
    rebuild_order_commands = [
        str(row.get("command") or "")
        for row in sorted_rebuild_order
        if isinstance(row, dict)
    ]
    if rebuild_order_commands != expected_rebuild_order_commands:
        raise AssertionError("current_evidence_summary.json rebuild_validation_contract upstream order drifted")
    if rebuild_validation_contract.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is not True:
        raise AssertionError("rebuild_validation_contract must require settlement audit refresh before bridge rebuild")
    if rebuild_validation_contract.get("upstream_refresh_order_is_provenance_metadata_only") is not True:
        raise AssertionError(
            "current_evidence_summary.json rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true"
        )
    if rebuild_validation_contract.get("not_settled_roi_or_real_money_evidence") is not True:
        raise AssertionError("rebuild_validation_contract must not be settled ROI or real-money evidence")

    anchor = scorecard["OP_DURABLE_K7"]
    phase7 = portfolio["phase7_live_portfolio"]
    selector = portfolio["train_only_selector"]
    phase8 = portfolio["phase8_frozen_portfolio"]
    selective = method_family["selective_rule_path"]
    harville = method_family["harville_ranked"]
    xgboost = method_family["xgboost_residual"]

    expected_intro = "This project is strongest when treated conservatively, using the frozen 2024-2025 holdout and train-only walk-forward standard:"
    expected_anchor_line = (
        f"- **Safest current anchor:** `{anchor['rule_id']}` "
        f"(**{float(anchor['holdout_roi']):+.1f}%** holdout on **{int(anchor['holdout_races'])}** races, `{anchor['tier']}`)"
    )
    expected_paper_line = (
        f"- **Primary paper baseline:** `{phase7['label']}` "
        f"(**{float(phase7['holdout_roi']):+.2f}% ROI on {int(phase7['holdout_races'])} holdout races; "
        f"2024 {float(phase7['holdout_2024_roi']):+.2f}% on {int(phase7['holdout_2024_races'])}, "
        f"2025 {float(phase7['holdout_2025_roi']):+.2f}% on {int(phase7['holdout_2025_races'])}; "
        "target cards confirmed by daily preflight**)"
    )
    expected_selector_line = (
        f"- **Current honest selector benchmark:** `{selector['label']}` "
        f"(**{float(selector['wf_roi']):+.2f}%** walk-forward, **{float(selector['holdout_roi']):+.2f}%** 2024-2025 holdout, `{selector['role']}`)"
    )
    expected_phase8_line = (
        f"- **Phase 8 status:** `{phase8['label']}` stays `{phase8['role']}` "
        f"(**{float(phase8['holdout_roi']):+.2f}% on {int(phase8['holdout_races'])}; "
        f"2024 {float(phase8['holdout_2024_roi']):+.2f}% on {int(phase8['holdout_2024_races'])}, "
        f"2025 {float(phase8['holdout_2025_roi']):+.2f}% on {int(phase8['holdout_2025_races'])}**), not the default"
    )
    current_paper_status = current_evidence["current_paper_status"]
    current_primary = current_paper_status["primary"]
    rule_progress = {row["rule_id"]: row for row in current_primary["rule_progress"]}
    recommendation_context = current_primary.get("recommendation_context", {})
    open_settlement_summary = str(current_primary.get("open_settlement_summary") or "").strip()
    open_settlements = int(current_primary.get("open_settlements", 0) or 0)
    recommendation_context_read = str(recommendation_context.get("read") or "").strip()
    recommendation_context_is_api_access = is_api_access_context(recommendation_context_read)
    open_queue = current_primary.get("open_settlement_queue_by_rule")
    if not isinstance(open_queue, dict):
        raise AssertionError("current_evidence_summary.json must publish current_paper_status.primary.open_settlement_queue_by_rule")
    open_settlement_queue_state = str(open_queue.get("open_settlement_queue_state") or "").strip()
    open_settlement_context = str(open_queue.get("open_settlement_context") or "").strip()
    open_settlement_detail_read = str(open_queue.get("detail_read") or "").strip()
    expected_open_settlement_queue_state = "closed" if open_settlements == 0 else "open"
    if open_settlement_queue_state not in {"closed", "open"}:
        raise AssertionError("open_settlement_queue_state must be closed or open")
    if open_settlement_queue_state != expected_open_settlement_queue_state:
        raise AssertionError("open_settlement_queue_state must match current_paper_status.primary.open_settlements")
    if open_settlements == 0 and open_settlement_context != "no open primary settlement rows":
        raise AssertionError("closed queue context must read no open primary settlement rows")
    if open_settlements > 0 and "open" not in open_settlement_context.lower():
        raise AssertionError("open queue context must identify open rows")
    if "Open settlement queue by rule:" not in open_settlement_detail_read:
        raise AssertionError("detail_read must carry by-rule open settlement detail")
    if "Settlement queue state:" in open_settlement_detail_read:
        raise AssertionError("detail_read must not nest the settlement queue state wrapper")
    source_published_queue_read = (
        f"source-published settlement queue state `{open_settlement_queue_state}` / "
        f"{open_settlement_context}; detail: {open_settlement_detail_read}"
    )
    if open_settlements and open_settlement_summary:
        recommendation_clause = (
            f"latest recommendation-state context says: {recommendation_context_read}; "
            "the open row is settlement workflow, not a bet-ready ticket or forward-performance proof"
            if recommendation_context_read
            else "recommendation-ledger and settlement-ledger context must be checked before interpreting any open row"
        )
        open_row_clause = (
            f"{source_published_queue_read}; bridge-published open settlement identity is `{open_settlement_summary}`; "
            f"{recommendation_clause}"
        )
    else:
        recommendation_clause = (
            f"latest recommendation-state context says: {recommendation_context_read}; "
            "source-published settlement queue state/detail are workflow metadata only"
            if recommendation_context_read
            else "recommendation-ledger context must be checked before interpreting bet readiness"
        )
        open_row_clause = (
            f"{source_published_queue_read}; no current open-row identity is published because the queue is closed; "
            f"{recommendation_clause}"
        )
    source_consistency_read = "matched" if current_evidence["source_consistency"].get("overall_match") else "mismatched"
    source_freshness = current_evidence["source_freshness"]
    requires_refresh = bool(source_freshness.get("requires_refresh_before_right_now_use"))
    source_freshness_clause = format_source_freshness_clause(requires_refresh)
    operator_read_gate = current_evidence.get("operator_read_gate")
    if not isinstance(operator_read_gate, dict):
        raise AssertionError("current_evidence_summary.json must publish operator_read_gate as an object")
    if operator_read_gate != current_paper_status.get("operator_read_gate"):
        raise AssertionError("current_evidence_summary.json operator_read_gate must match current_paper_status.operator_read_gate")
    operator_read_gate_read = str(operator_read_gate.get("read") or "").strip()
    if not operator_read_gate_read:
        raise AssertionError("current_evidence_summary.json operator_read_gate.read must be populated")
    if not isinstance(operator_read_gate.get("recommended_command"), str) or not operator_read_gate.get("recommended_command"):
        raise AssertionError("current_evidence_summary.json operator_read_gate must publish a recommended command")
    operator_read_gate_clause = (
        f"`operator_read_gate.requires_refresh_before_evidence_read={str(operator_read_gate.get('requires_refresh_before_evidence_read'))}` "
        f"plus `operator_read_gate.recommended_command={operator_read_gate.get('recommended_command')}` says {operator_read_gate_read} "
        f"Gate status `{operator_read_gate.get('gate_status')}` and valid use `{operator_read_gate.get('valid_use')}` are instruction/evidence-read routing only"
    )
    operator_read_requires_refresh = str(bool(operator_read_gate.get("requires_refresh_before_evidence_read"))).lower()
    if requires_refresh:
        combined_operator_read_route_clause = (
            "`operator_status_context`, `source_freshness.requires_refresh_before_right_now_use=true`, "
            f"and `operator_read_gate.requires_refresh_before_evidence_read={operator_read_requires_refresh}` together require "
            "`./run_daily_portfolio_observation.sh` before using the saved best-action card as today's operator instruction or evidence; "
            f"`operator_read_gate.recommended_command={operator_read_gate.get('recommended_command')}` says {operator_read_gate_read} "
            f"Gate status `{operator_read_gate.get('gate_status')}` and valid use `{operator_read_gate.get('valid_use')}` are instruction/evidence-read routing only"
        )
    else:
        combined_operator_read_route_clause = (
            "`operator_status_context`, `source_freshness.requires_refresh_before_right_now_use=false`, "
            f"and `operator_read_gate.requires_refresh_before_evidence_read={operator_read_requires_refresh}` together say the saved best-action card "
            "is fresh against the current bridge but still goes through operator-read-gate routing before instruction or evidence use; "
            f"`operator_read_gate.recommended_command={operator_read_gate.get('recommended_command')}` says {operator_read_gate_read} "
            f"Gate status `{operator_read_gate.get('gate_status')}` and valid use `{operator_read_gate.get('valid_use')}` are instruction/evidence-read routing only"
        )
    scorecard_gate_minimums = scorecard_json.get("decision_gate_minimums", {})
    scorecard_anchor_gate = (
        scorecard_gate_minimums.get("anchor_displacement")
        if isinstance(scorecard_gate_minimums.get("anchor_displacement"), dict)
        else {}
    )
    scorecard_phase8_gate = (
        scorecard_gate_minimums.get("phase8_promotion_review")
        if isinstance(scorecard_gate_minimums.get("phase8_promotion_review"), dict)
        else {}
    )
    scorecard_real_money_gate = (
        scorecard_gate_minimums.get("real_money_discussion")
        if isinstance(scorecard_gate_minimums.get("real_money_discussion"), dict)
        else {}
    )
    scorecard_gate_read = scorecard_gate_context_read["read"]
    scorecard_anchor_min = scorecard_gate_read["anchor_displacement_min_roi_complete_settled_observations"]
    scorecard_phase8_min = scorecard_gate_read["phase8_promotion_review_min_roi_complete_settled_observations"]
    scorecard_real_money_min = scorecard_gate_read[
        "real_money_discussion_min_total_settled_observations_with_usable_roi"
    ]
    current_gate_minimums = (
        current_evidence.get("decision_gate_minimums")
        if isinstance(current_evidence.get("decision_gate_minimums"), dict)
        else {}
    )
    current_gate_progress = (
        current_evidence.get("decision_gate_progress")
        if isinstance(current_evidence.get("decision_gate_progress"), dict)
        else {}
    )
    current_primary_gate_progress = (
        current_gate_progress.get("primary_first_read")
        if isinstance(current_gate_progress.get("primary_first_read"), dict)
        else {}
    )
    current_op_anchor_gate_progress = (
        current_gate_progress.get("op_anchor_same_candidate_review")
        if isinstance(current_gate_progress.get("op_anchor_same_candidate_review"), dict)
        else {}
    )
    current_phase8_gate_progress = (
        current_gate_progress.get("phase8_promotion_review")
        if isinstance(current_gate_progress.get("phase8_promotion_review"), dict)
        else {}
    )
    current_real_money_gate_progress = (
        current_gate_progress.get("real_money_discussion")
        if isinstance(current_gate_progress.get("real_money_discussion"), dict)
        else {}
    )
    current_gate_progress_read = str(current_gate_progress.get("read") or "").strip()
    current_gate_progress_display = current_gate_progress_read.rstrip(".")
    current_gate_progress_clause = (
        f"bridge-published gate progress from `current_evidence_summary.json.decision_gate_progress`: "
        f"{current_gate_progress_display}"
    )
    scorecard_gate_source_clause = (
        f"using scorecard-sourced gates (`{SCORECARD_JSON.name}` `decision_gate_minimums`: "
        f"`anchor_displacement={scorecard_anchor_min}`, "
        f"`phase8_promotion_review={scorecard_phase8_min}`, "
        f"`real_money_discussion={scorecard_real_money_min}`)"
    )
    scorecard_audit_route_clause = (
        "`current_evidence_summary.json.scorecard_audit_route` to "
        "`SCORECARD_RANKING_CONTRACT_AUDIT.md` with `scorecard_ranking_contract_audit.json` "
        "and `validate_scorecard_ranking_contract_audit.py`"
    )
    rebuild_order_clause = (
        "`current_evidence_summary.json.rebuild_validation_contract`: "
        "`python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> "
        "`python3 validate_current_evidence_summary.py` after scorecard/rules/signals/settlement-ledger "
        "byte changes before quoting current totals"
    )
    rebuild_order_boundary = (
        "provenance/rebuild metadata only, not settled ROI, promotion readiness, live profitability, "
        "bankroll guidance, or real-money evidence"
    )
    expected_shadow_split_line = "- **Current shadow-lane split:** `OP_REFINED_K7` is the closest same-family challenger; `KEE_K9`, `SA_K9`, and `DMR_FALL_K7` stay observation-only pockets, not near-promotion cases"
    expected_current_evidence_line = (
        "- **Current paper-trade evidence bridge:** `CURRENT_EVIDENCE_SUMMARY.md` says primary paper is "
        f"**{int(current_primary['first_read']['current'])}/{int(current_primary['first_read']['threshold'])}** ROI-complete and "
        f"**{int(current_primary['portfolio_review']['current'])}/{int(current_primary['portfolio_review']['threshold'])}** toward broad review; "
        f"{current_gate_progress_clause}; {scorecard_gate_source_clause}; "
        "current settled paper context is `CD_CORE_K8`-only "
        f"(**{int(rule_progress['CD_CORE_K8']['roi_complete_settled_rows'])}** rows) with `OP_DURABLE_K7` at "
        f"**{int(rule_progress['OP_DURABLE_K7']['roi_complete_settled_rows'])}** ROI-complete rows, source consistency is "
        f"`{source_consistency_read}` with a timestamp-aware CSV recompute that requires actual `settled_ts`, "
        f"bridge rebuild order comes from {rebuild_order_clause}; {rebuild_order_boundary}, {open_row_clause}, "
        f"{combined_operator_read_route_clause}, and this is context only — not OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence"
    )
    api_access_route_read = {
        "source": CURRENT_EVIDENCE_JSON.name,
        "source_path": "current_paper_status.primary.recommendation_context.read",
        "route_required": recommendation_context_is_api_access,
        "readme_has_sidecar_action": API_ACCESS_ACTION_TEXT in status_block,
        "readme_has_recheck_command": API_ACCESS_RECHECK_TEXT in status_block,
        "source_has_sidecar_action": API_ACCESS_ACTION_TEXT in recommendation_context_read,
        "source_has_recheck_command": API_ACCESS_RECHECK_TEXT in recommendation_context_read,
    }
    expected_selective_line = f"  - `{selective['label']}` = `{selective['role']}`"
    expected_harville_line = f"  - `{harville['label']}` = `{harville['role']}`"
    expected_xgboost_line = f"  - `{xgboost['label']}` = `{xgboost['role']}`"
    expected_cold_start_scorecard = "- **Fastest research-side read:** `forward_evidence_scorecard.txt`"
    expected_cold_start_scorecard_audit = "- **Fastest scorecard gate/ranking audit:** `current_evidence_summary.json.scorecard_audit_route` to `SCORECARD_RANKING_CONTRACT_AUDIT.md` with `scorecard_ranking_contract_audit.json` and `validate_scorecard_ranking_contract_audit.py` (copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite; report-synchronization / reproducibility metadata only, not promotion readiness, live profitability, bankroll guidance, or real-money evidence)"
    expected_cold_start_top_card = "- **Fastest operator-side read:** `PAPER_TRADE_NOW.md` (top-card read that keeps primary/shadow recent-run context plus lifted lane why-now lines visible alongside the current next action, with direct primary/shadow pipeline/scanner status-sidecar pointers for issue-day debugging and a matched `PAPER_TRADE_NOW.json` `operator_read_gate`; when the card is stale, those downstream lane details stay explicitly labeled as inherited snapshot context rather than current-day state)"
    bridge_queue_navigation = (
        "closed settlement-queue plus recommendation-state context"
        if open_settlements == 0
        else "current open-row identity plus recommendation-state context"
    )
    expected_cold_start_current_evidence = f"- **Fastest frozen-to-current evidence bridge:** `CURRENT_EVIDENCE_SUMMARY.md` with `current_evidence_summary.json` (source-checked bridge from frozen scorecard posture to current paper status; keeps the bridge-published current gates via `decision_gate_progress`, CD-only current rule mix, {bridge_queue_navigation}, source consistency across `PAPER_TRADE_NOW`, settlement audit, and the timestamp-aware primary settlement CSV recompute, plus `scorecard_audit_route` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks, plus `rebuild_validation_contract` for settlement-audit -> current-bridge -> bridge-validator order after source-byte changes, plus the combined `operator_status_context` + `source_freshness` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` route for stale or operational-issue right-now cards, and no-new-forward-evidence / no-promotion / no-live-profitability / no-real-money boundaries visible)"
    expected_cold_start_status_doc_route = "- **Fastest main status / repo-map route:** `COLE_STATUS_AND_PLAN.md` with `validate_cole_status_and_plan.py` (single-source status map; use the named `status_doc_base_api_access_route_documented` check for base API-access / HTTP 403 status-summary action-recheck route edits before lane enrichment; status/map alignment only, not new forward evidence)"
    expected_cold_start_decision_path = "- **Fastest direct decision-card path:** `OP_FAMILY_DECISION.md` → `CROSS_FAMILY_DECISION.md` (anchor / paper / watch shortlist plus current-paper snapshot caveat: stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and no OP-anchor / no cross-family-promotion evidence boundary) → `PORTFOLIO_DECISION_CARD.md` → `METHOD_FAMILY_DECISION.md`"
    expected_cold_start_main_comparison = "- **Fastest one-screen method/portfolio comparison:** `compare_main_approaches.md` with matched `compare_main_approaches.csv` / `compare_main_approaches.json` sidecars (OP/CD paper core, `OP_REFINED_K7` shadow-only challenger, Harville benchmark-only lane, current odds-only XGBoost research-only lane, evidence-class triage, source provenance/parity, and machine-readable evidence_boundary metadata; reproducibility/navigation metadata only, not new forward evidence, live profitability, promotion readiness, or real-money evidence)"
    expected_cold_start_full_data_retrain = "- **Fastest full-data XGBoost retrain caveat:** `FULL_DATA_RETRAIN_ARTIFACTS.md` with `validate_full_data_retrain_artifacts.py` (exact retrain/prediction commands plus RMSE / MAE model-fit diagnostics only; not paper-trade evidence, live profitability, promotion readiness, bankroll guidance, or real-money evidence)"
    expected_cold_start_frozen = "- **Fastest validated research sweep:** `out/status_validation/frozen_evidence_chain/frozen_evidence_chain_validation.md`"
    expected_cold_start_current_evidence_validation = "- **Fastest validated current-evidence bridge check:** `out/status_validation/current_evidence_summary/current_evidence_summary_validation.md`"
    expected_cold_start_top_card_validation = "- **Fastest validated operator top-card check:** `out/status_validation/paper_trade_now/paper_trade_now_validation.md`"
    expected_cold_start_decision_cards_validation = "- **Fastest validated decision-card sweep:** `out/status_validation/decision_cards_suite/decision_cards_suite_validation.md` (frozen-evidence ordering check, not new forward proof)"
    expected_cold_start_cross_family_validation = "- **Fastest validated cross-family current-paper check:** `out/status_validation/cross_family_decision/cross_family_decision_validation.md` (direct anchor / paper / watch and current-paper snapshot check; CD-only settled rows, source-published settlement-queue state/context, stale-card refresh routing, and green validation are not OP-anchor proof or cross-family promotion evidence)"
    expected_cold_start_project = "- **Fastest validated repo-wide read:** `out/status_validation/project_surfaces/project_surfaces_validation.md` (cross-layer alignment check, not new forward evidence by itself)"
    expected_cold_start_scorecard_validator = "- **If you changed only the scorecard:** run `python3 validate_forward_evidence_scorecard.py` before broader research sweeps"
    expected_cold_start_current_evidence_validator = f"- **If you changed only the current-evidence bridge:** run `python3 validate_current_evidence_summary.py` before broader report/project sweeps so source consistency, timestamp-gap exclusion, the combined operator-status/source-freshness/operator-read-gate route, CD-only current rule mix, {bridge_queue_navigation}, bridge-published current gates via `decision_gate_progress`, `scorecard_audit_route` synchronization routing, `rebuild_validation_contract` order routing, and no-overclaim boundaries stay pinned"
    expected_cold_start_cross_family_validator = "- **If you changed only the cross-family shortlist or current-paper snapshot caveat:** run `python3 validate_cross_family_decision.py` before broader decision-card, frozen-chain, or project sweeps so the anchor / paper / watch order, stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and no cross-family-promotion evidence boundary stay pinned"
    expected_cold_start_top_card_validator = "- **If you changed only the top operator card:** run `python3 validate_paper_trade_now.py` before broader operator sweeps so the live hierarchy, preserved primary/shadow recent-run context plus lane why-now lines, the stale-card inherited-snapshot honesty note, and direct pipeline/scanner sidecar pointers stay pinned"
    expected_validated_note = "- Fastest validated repo-wide read: `out/status_validation/project_surfaces/project_surfaces_validation.md` (cross-layer alignment check, not new forward evidence by itself)"
    expected_core_strategy_lines = [
        "- `compare_main_approaches.py`",
        "- `ab_downstream_comparison.py`",
        "- `op_anchor_method_comparison.py`",
        "- `compare_recommender_scope_paths.py`",
        "- `forward_evidence_scorecard.py`",
        "- `current_evidence_summary.py`",
        "- `portfolio_decision_card.py`",
        "- `method_family_decision_card.py`",
        "- `experiment_selector_variants.py`",
        "- `experiment_sample_size.py`",
        "- `walk_forward_validation.py`",
        "- `evaluate_frozen_portfolios.py`",
    ]
    expected_live_demo_lines = [
        "- `superfecta_ops.py`",
        "- `demo_live_predictions.py`",
        "- `live_portfolio_scanner.py`",
        "- `scan_live.sh`",
    ]
    expected_paper_trade_ops_lines = [
        "- `run_daily_portfolio_observation.sh`",
        "- `paper_trade_pipeline.py`",
        "- `paper_trade_status_summary.py`",
        "- `paper_trade_now.py`",
        "- `paper_trade_daily_summary.py`",
        "- `paper_trade_lane_summary.py`",
        "- `paper_trade_forward_check.py`",
        "- `paper_trade_lane_monitor.py`",
        "- `paper_trade_next_steps.py`",
        "- `paper_trade_ops_history.py`",
        "- `paper_trade_settlement_sync.py`",
        "- `paper_trade_settlement_helper.py`",
        "- `paper_trade_preflight_note.py`",
        "- `refresh_live_paper_trade_surfaces.py` (rerender saved per-run operator surfaces, saved `preflight_note` text/JSON, plus top-level `OPS_HISTORY` / `PAPER_TRADE_NOW` / `CURRENT_EVIDENCE_SUMMARY` after source-layer render changes, with current-evidence bridge rebuilds preserving `current_evidence_summary.json.rebuild_validation_contract` as the settlement-audit -> current-bridge -> bridge-validator route, rebuilt top-card recent-run context plus lifted lane why-now lines preserved when current lane artifacts provide them, stale rebuilt cards keeping the inherited-snapshot honesty note, `--latest-only` confined to the newest copied run's preflight, lane, and daily-summary surfaces, `--skip-top-level` confined to leaving `OPS_HISTORY` / `PAPER_TRADE_NOW` / `CURRENT_EVIDENCE_SUMMARY` untouched while still rerendering those per-run surfaces against the existing top-level outputs, and `--as-of-date` supporting reproducible top-card freshness rerenders while saying in stdout whether that pin was applied or skipped because top-level outputs were refreshed or skipped; presentation/rebuild metadata only, not new forward evidence)",
    ]
    expected_operator_doc_now = "- `PAPER_TRADE_NOW.md` (fastest operator-side read for the next live paper-trade action, with preserved primary/shadow recent-run context plus lifted lane why-now lines, direct primary/shadow pipeline/scanner status-sidecar pointers, a matched `PAPER_TRADE_NOW.json` `operator_read_gate`, and stale-card downstream lane details explicitly labeled as inherited snapshot context rather than current-day state)"
    expected_operator_doc_ops_history = "- `OPS_HISTORY.md` (rolling quiet-day vs issue-day context so recent daily behavior is not misread from one run folder alone)"
    expected_operator_doc_guide = "- `DAILY_ARTIFACT_GUIDE.md` (day-to-day routing across the main research and paper-operator surfaces, including where preserved primary/shadow recent-run context plus lifted lane why-now lines should surface first and where issue-day triage should jump into the direct pipeline/scanner sidecar pointers surfaced from `PAPER_TRADE_NOW.md`)"
    expected_operator_doc_usage = "- `PAPER_TRADE_USAGE.md` (hands-on OP-anchor-first operator runbook)"
    expected_operator_validator_now = "- `validate_paper_trade_now.py` (consistency check for the top-card operator surface and its saved outputs, including the live hierarchy, preserved primary/shadow recent-run context plus lane why-now lines, the stale-card inherited-snapshot honesty note, `operator_read_gate` no-evidence routing, and direct primary/shadow pipeline/scanner status-sidecar pointers)"
    expected_operator_validator_ops_history = "- `validate_paper_trade_ops_history.py` (direct validator for the rolling ops-history surface so quiet no-target days, clean active empty days, limited-coverage days, and explicit issue/failure days stay separated)"
    expected_operator_validator_preflight = "- `validate_paper_trade_preflight_note.py` (direct validator for the shared preflight-note surface so no-target days, active-target days, and unknown-calendar degradation do not blur together)"
    expected_operator_validator_guide = "- `validate_daily_artifact_guide.py` (consistency check for the day-to-day repo-map guide and latest-run pointers)"
    expected_operator_validator_usage = "- `validate_paper_trade_usage.py` (consistency check for the hands-on operator runbook)"
    expected_operator_validator_status_summary = "- `validate_paper_trade_status_summary.py` (direct validator for the one-line base lane summary, including unreadable scanner sidecars, wrapper-only required-pipeline sidecar issue branches, and saved recommender/logger failure lines that should keep stage, error type, and detail visible)"
    expected_operator_validator_daily_summary = "- `validate_paper_trade_daily_summary.py` (direct validator for the combined daily summary, including the routed top-card focus/timing/freshness/ops snapshot, preserved primary/shadow recent-run context lines, the explicit primary/shadow next-step states plus first-read and broader-review readiness lines, the visible shadow-review-without-live-promotion cue, and failure/placeholder integrity)"
    expected_operator_validator_refresh = "- `validate_refresh_live_paper_trade_surfaces.py` (direct validator for the saved-live refresh helper so regenerated per-run summaries, saved `preflight_note` text/JSON, plus top-level `OPS_HISTORY` / `PAPER_TRADE_NOW` / `CURRENT_EVIDENCE_SUMMARY` stay source-matched, current-evidence rebuilds preserve `current_evidence_summary.json.rebuild_validation_contract`, rebuilt daily summaries inherit the routed top-card focus/timing/freshness/ops snapshot, preserved primary/shadow recent-run context plus lifted lane why-now lines survive rebuilt top-card refreshes when current lane artifacts provide them, stale rebuilt cards keep the inherited-snapshot honesty note, `--latest-only` stays confined to the newest copied run's preflight, lane, and daily-summary surfaces, `--skip-top-level` stays confined to leaving top-level outputs untouched while still rebuilding the per-run preflight/lane/daily layer against those existing top-level outputs, the `--as-of-date` freshness pin is proved and reported honestly, the helper stays explicit that rerendering is not new forward evidence, and together with `validate_run_daily_portfolio_observation.py` it acts as one of the two leaf source-of-truth wrapper reports whose inherited wrapper-guardrail inventories broader operator/project sweeps should preserve rather than flatten)"
    expected_operator_validator_daily_wrapper = "- `validate_run_daily_portfolio_observation.py` (direct validator for the real daily wrapper so cache-miss, hit-found / no-BET, settle-first, partial-cache, helper-failure, placeholder, markdown-mirror, lane-summary-fallback, and daily-summary-fallback orchestration stays honest, preserved primary/shadow recent-run context plus lifted lane why-now lines survive wrapper fallbacks when saved lane artifacts provide them, wrapper-generated `CURRENT_EVIDENCE_SUMMARY` refresh/placeholder plus source-backed recommendation-context/open-row separation stays explicit before Cole-facing current-paper wording, and together with `validate_refresh_live_paper_trade_surfaces.py` it acts as the other leaf source-of-truth wrapper report whose inherited wrapper-guardrail inventories broader operator/project sweeps should preserve rather than flatten)"
    expected_operator_validator_suite = "- `validate_paper_trade_operator_suite.py` (one-command sweep across the operator-facing paper-trade surfaces, including the top card, daily summary, lane summaries, forward/settlement helpers, refresh-helper coverage, daily-wrapper coverage, wrapper-level failure-mode messaging, preserved primary/shadow recent-run context plus lifted lane why-now lines across the top operator reads, and the direct top-card pipeline/scanner sidecar-pointer contract; it should preserve the inherited wrapper-guardrail inventories from those two leaf wrapper reports rather than replacing them with one flattened green light)"
    expected_quickstart_doc = "- `VALIDATION_QUICKSTART.md` (validated runbook for choosing the right validator, including the broader operator-suite route, the direct source-layer paper-trade chain routes, the parent-rollup reuse shortcut guardrails, documented output paths, and the dated-report / legacy-alias policy)"
    expected_quickstart_validator = "- `validate_validation_quickstart.py` (consistency check for that runbook so the validation ladder, the broader operator-suite route, direct source-layer routes, reuse guardrails, documented output paths, and dated-report / legacy-alias guidance do not drift quietly)"
    expected_status_doc = "- `COLE_STATUS_AND_PLAN.md` (single-source status document and repo map, including the frozen posture, validation reading order, and the named `status_doc_base_api_access_route_documented` route for base API-access / HTTP 403 status-summary action-recheck wording before lane enrichment)"
    expected_status_doc_validator = "- `validate_cole_status_and_plan.py` (direct validator for the main status document and repo map, including `status_doc_base_api_access_route_documented` so API-access route wording stays status/map alignment metadata rather than settled ROI, promotion readiness, live profitability, or real-money evidence)"
    expected_current_evidence_doc = f"- `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` (source-checked and freshness-routed frozen-to-current bridge for short Cole updates, including source consistency across `PAPER_TRADE_NOW`, settlement audit, and the timestamp-aware primary settlement CSV recompute, the combined `operator_status_context` + `source_freshness` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` route, CD-only current rule mix, {bridge_queue_navigation}, bridge-published current gates via `decision_gate_progress`, bridge-owned `scorecard_audit_route` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks, bridge-owned `rebuild_validation_contract` for settlement-audit -> current-bridge -> bridge-validator order after source-byte changes, and explicit no-new-forward-evidence / no-promotion / no-live-profitability / no-real-money boundaries)"
    expected_current_evidence_validator = f"- `validate_current_evidence_summary.py` (rebuild/consistency check for the current-evidence bridge so report-ready updates do not drift from the top card, operator-status context, structured operator_read_gate routing, settlement audit, timestamp-aware primary settlement CSV recompute, {bridge_queue_navigation}, frozen scorecard posture, bridge-owned scorecard-audit routing, bridge-owned rebuild-order routing, or stale right-now source freshness)"
    expected_scorecard_audit_doc = "- `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` (report-facing scorecard contract audit reached from `current_evidence_summary.json.scorecard_audit_route` for copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and the no-BAQ-as-BEL prerequisite; synchronization/reproducibility metadata only)"
    expected_scorecard_audit_validator = "- `validate_scorecard_ranking_contract_audit.py` (direct validator for the scorecard ranking-contract / gate-floor audit so copied gate floors and no-BAQ prerequisite drift fail loudly without becoming live paper, promotion, bankroll, or real-money evidence)"
    expected_op_family_doc = "- `OP_FAMILY_DECISION.md` (short answer to whether anything beats `OP_DURABLE_K7` yet)"
    expected_op_family_validator = "- `validate_op_family_decision.py` (rebuild/consistency check for the OP-family card, including the saved surfaces, real CLI output, and anchor-replacement bar)"
    expected_cross_family_doc = "- `CROSS_FAMILY_DECISION.md` (compact anchor / paper / watch shortlist for `OP_DURABLE_K7`, `CD_CORE_K8`, and `OP_REFINED_K7`, plus the current-paper snapshot caveat and the explicit near-promotion vs observation-only split for the smaller Phase 8 pockets)"
    expected_cross_family_validator = "- `validate_cross_family_decision.py` (rebuild/consistency check for that cross-family shortlist, its current anchor / paper / watch ordering, the current-paper snapshot caveat, and the explicit near-promotion vs observation-only shadow split)"
    expected_portfolio_decision_doc = "- `PORTFOLIO_DECISION_CARD.md` (compact `PAPER NOW` / `SHADOW ONLY` / `BENCHMARK ONLY` portfolio-level card)"
    expected_portfolio_decision_validator = "- `validate_portfolio_decision_card.py` (rebuild/consistency check for that top-level portfolio card and its current paper / shadow / benchmark ordering)"
    expected_method_family_doc = "- `METHOD_FAMILY_DECISION.md` (compact card for the selective-rule path versus the Harville benchmark and the parked current odds-only XGBoost path)"
    expected_op_anchor_doc = "- `OP_ANCHOR_METHOD_COMPARISON.md` (cold-read OP-centered comparison showing why `OP_DURABLE_K7` still outranks Harville while the current odds-only XGBoost path stays parked unless its evidence class changes materially, making the unlike evidence classes explicit, and keeping the broader selective-family secondary line in replay-only context rather than extra train-only proof)"
    expected_method_family_validator = "- `validate_method_family_decision_card.py` (rebuild/consistency check for that method-family card and its current PAPER NOW / BENCHMARK ONLY / RESEARCH ONLY ordering)"
    expected_decision_cards_suite_validator = "- `validate_decision_cards_suite.py` (one-command sweep across the four direct decision-card validators)"
    expected_main_comparison_doc = "- `compare_main_approaches.md` / `.csv` / `.json` (one-screen OP/CD paper-core, `OP_REFINED_K7` shadow-only, Harville benchmark-only, and current odds-only XGBoost research-only comparison bundle; matched sidecars carry source provenance, parity, and machine-readable evidence_boundary metadata as reproducibility/navigation metadata only, not new forward evidence)"
    expected_main_comparison_validator = "- `validate_compare_main_approaches.py` (rebuild/consistency check for the main comparison bundle, including saved CSV/markdown/JSON parity, source fingerprints, evidence-class triage, machine-readable evidence boundary, and evidence-scope decision-change gates)"
    expected_full_data_retrain_doc = "- `FULL_DATA_RETRAIN_ARTIFACTS.md` (full-data XGBoost retrain artifact for exact command and model-fit reproducibility context only, not paper-trade evidence, live profitability, promotion readiness, bankroll guidance, or real-money evidence)"
    expected_full_data_retrain_validator = "- `validate_full_data_retrain_artifacts.py` (direct validator for the full-data retrain artifact and its model-fit-not-betting-evidence boundary)"
    expected_working_status_validator = "- `validate_working_status_report.py` (consistency check for that dated live/demo-vs-production note and its stable-vs-mutable artifact framing)"
    expected_report_alias_note = (
        "- For the shareable visual report, use the dated report pair. `Superfecta_Project_Report_2026-04-15.html` is the validation trust anchor, "
        "and `Superfecta_Project_Report_2026-04-15.pdf` is its derivative export. `Superfecta_Project_Report.html`, `Superfecta_Project_Report.pdf`, and `Superfecta_Project_Report.docx` are only legacy aliases. "
        "`Superfecta Prediction - Quick Start Guide.pdf` and `OpenClaw Prompt.docx` are also legacy alias surfaces that point back to the current runbooks/trust path. None is a preferred or separately validated report surface."
    )

    checks: list[dict[str, Any]] = []
    if (
        Path(args.scorecard_json).resolve() == SCORECARD_JSON.resolve()
        and Path(args.current_evidence_json).resolve() == CURRENT_EVIDENCE_JSON.resolve()
    ):
        checks.extend(scorecard_gate_cli_contract_checks(args.scorecard_json, args.current_evidence_json))
    if Path(args.current_evidence_json).resolve() == CURRENT_EVIDENCE_JSON.resolve():
        checks.extend(current_bridge_rebuild_cli_contract_checks(args.current_evidence_json))
    fresh_clause = format_source_freshness_clause(False)
    stale_clause = format_source_freshness_clause(True)
    checks.append(
        require(
            "requires_refresh_before_right_now_use=false" in fresh_clause
            and "fresh against the current bridge" in fresh_clause
            and "./run_daily_portfolio_observation.sh" not in fresh_clause,
            "source_freshness_false_branch_is_fresh_not_refresh",
            "README validator's source-freshness helper now distinguishes fresh right-now cards from refresh-required cards",
        )
    )
    checks.append(
        require(
            "requires_refresh_before_right_now_use=true" in stale_clause
            and "./run_daily_portfolio_observation.sh" in stale_clause
            and "before using the saved best-action card" in stale_clause,
            "source_freshness_true_branch_is_refresh_first",
            "README validator's source-freshness helper keeps stale right-now cards refresh-first",
        )
    )
    checks.append(
        require(
            anchor["tier"] == "ANCHOR" and anchor["rank"] == "1",
            "anchor_source_still_op_durable",
            "forward scorecard still ranks OP_DURABLE_K7 first and keeps it in the ANCHOR tier",
        )
    )
    checks.append(
        require(
            expected_intro in status_block,
            "status_intro",
            "README current-status block still states the frozen holdout plus train-only walk-forward standard",
        )
    )
    checks.append(
        require(
            expected_anchor_line in status_block,
            "anchor_line",
            "README still names OP_DURABLE_K7 as the safest current anchor with the frozen holdout sample",
        )
    )
    checks.append(
        require(
            expected_paper_line in status_block,
            "paper_line",
            "README still names the Phase 7 OP/CD rule-component basket as the primary paper baseline with the current frozen holdout ROI, explicit 2024/2025 split, and daily-preflight target-card boundary",
        )
    )
    checks.append(
        require(
            expected_selector_line in status_block,
            "selector_line",
            "README still presents the train-only yearly selector as the honest benchmark, not the daily operating default",
        )
    )
    checks.append(
        require(
            expected_phase8_line in status_block,
            "phase8_line",
            "README still keeps the Phase 8 frozen portfolio in SHADOW ONLY status while making its weaker 2024/2025 split visible",
        )
    )
    checks.append(
        require(
            expected_shadow_split_line in status_block,
            "shadow_split_line",
            "README current-status block now keeps the closest-challenger vs observation-only-pocket shadow split explicit instead of leaving Phase 8 as a generic shadow bucket",
        )
    )
    checks.append(
        require(
            expected_current_evidence_line in status_block,
            "current_evidence_bridge_line",
            "README current-status block now points to the source-checked current-evidence bridge while keeping the tiny CD-only settled sample separate from OP-anchor proof, promotion readiness, live profitability, and real-money evidence",
        )
    )
    checks.append(
        require(
            source_published_queue_read in status_block
            and "source-published settlement queue state" in status_block
            and "detail: Open settlement queue by rule:" in status_block
            and (
                open_settlements > 0
                or "current primary open settlement queue has **0** open row(s)" not in status_block
            )
            and (
                open_settlements > 0
                or "open_settlement_summary=none" not in status_block
            ),
            "source_published_settlement_queue_state",
            "README current-status block now consumes current_evidence_summary.json source-published settlement queue state/context/detail instead of deriving closed-queue display wording from raw open_settlements/open_settlement_summary fields",
        )
    )
    checks.append(
        require(
            (not recommendation_context_is_api_access)
            or (
                API_ACCESS_ACTION_TEXT in recommendation_context_read
                and API_ACCESS_RECHECK_TEXT in recommendation_context_read
                and API_ACCESS_ACTION_TEXT in expected_current_evidence_line
                and API_ACCESS_RECHECK_TEXT in expected_current_evidence_line
                and API_ACCESS_ACTION_TEXT in status_block
                and API_ACCESS_RECHECK_TEXT in status_block
                and "not a no-target, clean-empty, or forward-performance read" in status_block
            ),
            "current_evidence_api_access_route_line",
            "README current-status block now has a named check proving API-access recommendation context preserves the sidecar action and wrapper recheck route instead of stopping at a generic 403 warning",
        )
    )
    checks.append(
        require(
            scorecard_gate_read["anchor_displacement_min_roi_complete_settled_observations"] == current_primary["first_read"]["threshold"]
            and scorecard_gate_read["real_money_discussion_min_total_settled_observations_with_usable_roi"] == current_primary["portfolio_review"]["threshold"]
            and scorecard_gate_read["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and scorecard_gate_read["real_money_no_baq_as_bel_required"] is True
            and current_gate_minimums.get("source_path") == SCORECARD_JSON.name
            and current_gate_minimums.get("source_loaded") is True
            and current_gate_minimums.get("anchor_displacement_min_roi_complete_settled_observations") == scorecard_anchor_min
            and current_gate_minimums.get("phase8_promotion_review_min_roi_complete_settled_observations") == scorecard_phase8_min
            and current_gate_minimums.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == scorecard_real_money_min
            and current_gate_progress.get("source_path") == SCORECARD_JSON.name
            and current_gate_progress.get("source_json_path") == "decision_gate_minimums"
            and current_gate_progress.get("gate_status") == "all_uncleared"
            and current_gate_progress.get("all_gates_ready") is False
            and current_gate_progress.get("not_forward_performance_evidence") is True
            and current_gate_progress.get("not_promotion_readiness_evidence") is True
            and current_gate_progress.get("not_live_profitability_evidence") is True
            and current_gate_progress.get("not_real_money_evidence") is True
            and current_primary_gate_progress.get("current_rows") == current_primary["first_read"]["current"]
            and current_primary_gate_progress.get("threshold") == scorecard_anchor_min
            and current_primary_gate_progress.get("remaining") == scorecard_anchor_min - current_primary["first_read"]["current"]
            and current_primary_gate_progress.get("ready") is False
            and current_op_anchor_gate_progress.get("candidate_rule_id") == "OP_DURABLE_K7"
            and current_op_anchor_gate_progress.get("current_rows") == rule_progress["OP_DURABLE_K7"]["roi_complete_settled_rows"]
            and current_op_anchor_gate_progress.get("threshold") == scorecard_anchor_min
            and current_op_anchor_gate_progress.get("remaining") == scorecard_anchor_min
            and current_op_anchor_gate_progress.get("companion_rule_id") == "CD_CORE_K8"
            and current_op_anchor_gate_progress.get("companion_rows") == rule_progress["CD_CORE_K8"]["roi_complete_settled_rows"]
            and current_op_anchor_gate_progress.get("companion_rows_count_as_anchor_evidence") is False
            and current_phase8_gate_progress.get("threshold_per_candidate") == scorecard_phase8_min
            and current_phase8_gate_progress.get("weakest_current_rows") == 0
            and current_phase8_gate_progress.get("ready") is False
            and current_real_money_gate_progress.get("current_primary_roi_complete_rows") == current_primary["portfolio_review"]["current"]
            and current_real_money_gate_progress.get("threshold") == scorecard_real_money_min
            and current_real_money_gate_progress.get("remaining_against_primary_review") == scorecard_real_money_min - current_primary["portfolio_review"]["current"]
            and current_real_money_gate_progress.get("ready") is False
            and current_real_money_gate_progress.get("no_baq_as_bel_required") is True
            and current_gate_progress_clause in status_block
            and scorecard_gate_source_clause in status_block,
            "readme_current_gates_source_match_scorecard_json",
            "README current-status gate wording now source-matches forward_evidence_scorecard.json decision_gate_minimums and current_evidence_summary.json decision_gate_progress, preserves the no-BAQ-as-BEL real-money prerequisite, and treats primary 6/30, OP-anchor 0/30, Phase 8 0/20, and real-money 6/100 gates as uncleared routing context rather than proof",
        )
    )
    checks.append(
        require(
            "source_freshness.requires_refresh_before_right_now_use=" in status_block
            and combined_operator_read_route_clause in status_block
            and "combined `operator_status_context` + `source_freshness` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` route" in cold_start_block
            and "combined operator-status/source-freshness/operator-read-gate route" in cold_start_block
            and "combined `operator_status_context` + `source_freshness` / `requires_refresh_before_right_now_use` + `operator_read_gate` / `requires_refresh_before_evidence_read` route" in readme_text
            and "stale right-now source freshness" in readme_text,
            "current_evidence_combined_operator_read_route",
            "README now routes cold readers, bridge-only edits, and the report inventory through the combined operator_status_context / source_freshness / operator_read_gate route so a source-matched but stale/API-failure right-now card triggers a daily-wrapper refresh before operator instruction or evidence use",
        )
    )
    checks.append(
        require(
            operator_read_gate.get("gate_status") in {
                "refresh_required_before_evidence_read",
                "current_operator_routing_context_only",
            }
            and operator_read_gate.get("valid_use") == "operator instruction/evidence-read gating only"
            and isinstance(operator_read_gate.get("requires_refresh_before_evidence_read"), bool)
            and isinstance(operator_read_gate.get("has_api_access_failure_context"), bool)
            and isinstance(operator_read_gate.get("has_scanner_failure_boundary"), bool)
            and isinstance(operator_read_gate.get("has_stale_cache_fallback_context"), bool)
            and operator_read_gate.get("current_top_card_counts_as_no_target_evidence") is False
            and operator_read_gate.get("current_top_card_counts_as_clean_empty_evidence") is False
            and operator_read_gate.get("current_top_card_counts_as_bet_readiness_evidence") is False
            and operator_read_gate.get("current_top_card_counts_as_settled_roi_evidence") is False
            and operator_read_gate.get("not_live_profitability_evidence") is True
            and operator_read_gate.get("not_real_money_evidence") is True
            and combined_operator_read_route_clause in status_block
            and "operator_read_gate` / `requires_refresh_before_evidence_read` route" in cold_start_block
            and "operator-read-gate route" in cold_start_block
            and "structured operator_read_gate routing" in readme_text
            and "`operator_read_gate` / `requires_refresh_before_evidence_read` route" in readme_text
            and "matched `PAPER_TRADE_NOW.json` `operator_read_gate`" in readme_text,
            "current_evidence_operator_read_gate_route",
            "README now routes cold readers, top-card readers, current-evidence bridge edits, and report inventory reads through current_evidence_summary.json operator_read_gate so stale/API-failure/stale-cache-fallback right-now cards require wrapper refresh before instruction/evidence use and cannot be mistaken for no-target, clean-empty, bet-readiness, settled-ROI, live-profitability, bankroll, or real-money evidence",
        )
    )
    checks.append(
        require(
            "bridge-published current gates" in cold_start_block
            and "bridge-published current gates" in readme_text
            and "keeps the 4/30 and 4/100 gates" not in cold_start_block
            and "CD-only current rule mix, 4/30 and 4/100 gates" not in readme_text,
            "current_evidence_navigation_uses_bridge_published_gates",
            "README cold-start and inventory navigation now route current gate wording through bridge-published current gates instead of pinning today's settled-row literals",
        )
    )
    checks.append(
        require(
            expected_selective_line in status_block and expected_harville_line in status_block and expected_xgboost_line in status_block,
            "method_family_lines",
            "README method-family hierarchy still matches the current PAPER NOW / BENCHMARK ONLY / RESEARCH ONLY roles",
        )
    )
    checks.append(
        require(
            "+30.42%" not in readme_text,
            "stale_selector_headline_removed",
            "README no longer advertises the stale +30.42% selector headline as current status",
        )
    )
    checks.append(
        require(
            expected_cold_start_scorecard in cold_start_block,
            "cold_start_scorecard_read",
            "README now tells cold readers to start research-side navigation with the forward evidence scorecard",
        )
    )
    checks.append(
        require(
            expected_cold_start_scorecard_audit in cold_start_block,
            "cold_start_scorecard_audit_read",
            "README now points cold readers to the scorecard ranking-contract / gate-floor audit when the question is copied 30/20/100 floors, tier-first ranking, OP_REFINED CI-only context, timezone provenance, or no-BAQ prerequisite drift, while keeping that route as synchronization metadata only",
        )
    )
    checks.append(
        require(
            scorecard_audit_route.get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route.get("json_path") == "scorecard_ranking_contract_audit.json"
            and scorecard_audit_route.get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route.get("gate_floor_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and scorecard_audit_gate_floor_snapshot.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and scorecard_audit_gate_floor_snapshot.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and scorecard_audit_gate_floor_snapshot.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and scorecard_audit_gate_floor_snapshot.get("real_money_no_baq_as_bel_required") is True
            and scorecard_audit_route.get("artifacts_present") is True
            and scorecard_audit_route.get("not_forward_performance_evidence") is True
            and scorecard_audit_route.get("not_settled_roi_evidence") is True
            and scorecard_audit_route.get("not_promotion_readiness_evidence") is True
            and scorecard_audit_route.get("not_live_profitability_evidence") is True
            and scorecard_audit_route.get("not_bankroll_guidance") is True
            and scorecard_audit_route.get("not_real_money_evidence") is True
            and "copied 30/20/100 gate floors" in str(scorecard_audit_route.get("route_read") or "")
            and "tier-first ranking" in str(scorecard_audit_route.get("route_read") or "")
            and "no-BAQ-as-BEL prerequisite" in str(scorecard_audit_route.get("route_read") or "")
            and scorecard_audit_route_clause in cold_start_block
            and "`scorecard_audit_route` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks" in cold_start_block
            and "bridge-owned `scorecard_audit_route` for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks" in readme_text
            and "bridge-owned scorecard-audit routing" in readme_text,
            "current_evidence_scorecard_audit_route_read",
            "README now consumes current_evidence_summary.json.scorecard_audit_route before sending cold readers or report-inventory readers to the scorecard gate/ranking/CI-only/timezone/no-BAQ audit, while preserving that route as synchronization metadata only",
        )
    )
    checks.append(
        require(
            rebuild_order_clause in readme_text
            and "`rebuild_validation_contract` for settlement-audit -> current-bridge -> bridge-validator order after source-byte changes" in cold_start_block
            and "`rebuild_validation_contract` order routing" in cold_start_block
            and "bridge-owned `rebuild_validation_contract` for settlement-audit -> current-bridge -> bridge-validator order after source-byte changes" in readme_text
            and "bridge-owned rebuild-order routing" in readme_text
            and rebuild_validation_contract.get("rebuild_command") == "python3 current_evidence_summary.py"
            and rebuild_validation_contract.get("prerequisite_rebuild_command") == "python3 paper_trade_settlement_audit.py"
            and rebuild_order_commands == expected_rebuild_order_commands
            and rebuild_validation_contract.get("direct_validation_command") == "python3 validate_current_evidence_summary.py"
            and rebuild_validation_contract.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and rebuild_validation_contract.get("requires_source_consistency_before_quoting_current_totals") is True
            and rebuild_validation_contract.get("upstream_refresh_order_is_provenance_metadata_only") is True
            and rebuild_validation_contract.get("not_settled_roi_or_real_money_evidence") is True
            and rebuild_order_boundary in readme_text,
            "current_evidence_rebuild_validation_contract_read",
            "README now consumes current_evidence_summary.json.rebuild_validation_contract before telling cold readers or report-inventory readers how to rebuild/quote the current bridge after source-byte changes, while preserving that route as provenance metadata only",
        )
    )
    checks.append(
        require(
            expected_cold_start_top_card in cold_start_block,
            "cold_start_top_card_read",
            "README now tells cold readers to start operator-side navigation with PAPER_TRADE_NOW.md when they need the next live paper-trade action",
        )
    )
    checks.append(
        require(
            expected_cold_start_current_evidence in cold_start_block,
            "cold_start_current_evidence_read",
            "README now gives cold readers the source-checked frozen-to-current bridge before they turn the tiny settled paper sample into an OP-anchor or promotion claim",
        )
    )
    checks.append(
        require(
            expected_cold_start_status_doc_route in cold_start_block,
            "cold_start_status_doc_api_access_route",
            "README now gives cold readers the direct main status / repo-map route for status_doc_base_api_access_route_documented when base API-access / HTTP 403 status-summary action-recheck wording changes before lane enrichment",
        )
    )
    checks.append(
        require(
            expected_cold_start_decision_path in cold_start_block,
            "cold_start_decision_path_read",
            "README now gives cold readers the direct decision-card reading path from the OP anchor question through the cross-family, portfolio, and method-family cards",
        )
    )
    checks.append(
        require(
            expected_cold_start_main_comparison in cold_start_block,
            "cold_start_main_comparison_read",
            "README now gives cold readers the direct one-screen main comparison path across the OP/CD paper core, OP_REFINED_K7 shadow lane, Harville benchmark, and parked odds-only XGBoost lane while keeping the matched CSV/JSON sidecars and evidence boundary framed as reproducibility metadata only",
        )
    )
    checks.append(
        require(
            expected_cold_start_full_data_retrain in cold_start_block,
            "cold_start_full_data_retrain_caveat_read",
            "README now gives cold readers the direct full-data XGBoost retrain caveat route while keeping exact retrain/prediction commands and RMSE / MAE gains in model-fit context only",
        )
    )
    checks.append(
        require(
            expected_cold_start_frozen in cold_start_block,
            "cold_start_frozen_read",
            "README now points cold readers to the frozen evidence-chain report for the fastest validated research sweep",
        )
    )
    checks.append(
        require(
            expected_cold_start_current_evidence_validation in cold_start_block,
            "cold_start_current_evidence_validation_read",
            "README now points cold readers to the direct validation report for the frozen-to-current bridge so source-consistency and no-overclaim checks are discoverable from the landing page",
        )
    )
    checks.append(
        require(
            expected_cold_start_top_card_validation in cold_start_block,
            "cold_start_top_card_validation_read",
            "README now points cold readers to the direct paper-trade-now validation report for the fastest validated operator-side top-card check, with the top-card context-preservation contract made explicit nearby",
        )
    )
    checks.append(
        require(
            expected_cold_start_decision_cards_validation in cold_start_block,
            "cold_start_decision_cards_validation_read",
            "README now points cold readers to the direct decision-cards-suite report for the fastest validated card-level sweep and says that sweep is frozen-evidence ordering rather than new proof",
        )
    )
    checks.append(
        require(
            expected_cold_start_cross_family_validation in cold_start_block
            and expected_cold_start_cross_family_validator in cold_start_block
            and expected_cross_family_doc in readme_text
            and expected_cross_family_validator in readme_text,
            "cross_family_current_paper_route_present",
            "README now routes cross-family current-paper snapshot caveat edits through the direct cross-family validator and keeps CD-only/open-row context out of OP-anchor proof or cross-family promotion evidence",
        )
    )
    checks.append(
        require(
            expected_cold_start_project in cold_start_block,
            "cold_start_project_read",
            "README now points cold readers to the top-level project-surfaces report for the fastest validated repo-wide read and says that report is a cross-layer alignment check rather than new forward evidence",
        )
    )
    checks.append(
        require(
            expected_cold_start_scorecard_validator in cold_start_block,
            "cold_start_scorecard_validator",
            "README now says scorecard-only edits should use the direct scorecard validator before broader research sweeps",
        )
    )
    checks.append(
        require(
            expected_cold_start_current_evidence_validator in cold_start_block,
            "cold_start_current_evidence_validator",
            "README now says current-evidence bridge edits should use the direct source-consistency / no-overclaim validator before broader report or project sweeps",
        )
    )
    checks.append(
        require(
            expected_cold_start_top_card_validator in cold_start_block,
            "cold_start_top_card_validator",
            "README now says top-card-only operator edits should use the direct paper-trade-now validator before broader operator sweeps",
        )
    )
    checks.append(
        require(
            expected_validated_note in readme_text,
            "validated_read_note",
            "README notes now point readers to the top-level validated project-surfaces report for the fastest honest repo-wide read and keep it framed as a cross-layer alignment check rather than new forward evidence",
        )
    )
    checks.append(
        require(
            all(line in readme_text for line in expected_core_strategy_lines),
            "core_strategy_inventory_lines",
            "README still names the current core strategy and evaluation scripts in the repo inventory",
        )
    )
    checks.append(
        require(
            all(line in readme_text for line in expected_live_demo_lines),
            "live_demo_inventory_lines",
            "README still names the live and demo operations scripts in the repo inventory",
        )
    )
    checks.append(
        require(
            all(line in readme_text for line in expected_paper_trade_ops_lines),
            "paper_trade_ops_inventory_lines",
            "README still names the core paper-trade operation scripts in the repo inventory, including the source helpers that generate the first one-line status and top-card operator reads plus the saved-live refresh helper that rebuilds derived operator surfaces after render changes",
        )
    )
    checks.append(
        require(
            all(
                line in readme_text
                for line in [
                    expected_operator_doc_now,
                    expected_operator_doc_ops_history,
                    expected_operator_doc_guide,
                    expected_operator_doc_usage,
                    expected_operator_validator_now,
                    expected_operator_validator_ops_history,
                    expected_operator_validator_preflight,
                    expected_operator_validator_guide,
                    expected_operator_validator_usage,
                    expected_operator_validator_status_summary,
                    expected_operator_validator_daily_summary,
                    expected_operator_validator_refresh,
                    expected_operator_validator_daily_wrapper,
                    expected_operator_validator_suite,
                    expected_quickstart_doc,
                    expected_quickstart_validator,
                ]
            ),
            "operator_docs_inventory_lines",
            "README now names the operator-facing top card, rolling ops history, daily guide, runbook, quickstart, and their direct validators in the repo inventory, including the quiet-day-vs-issue-day ops-history route, the direct preflight-note route, the direct base-status-summary route, the combined-daily-summary route with preserved primary/shadow recent-run context, the saved-live refresh route plus the real daily-wrapper route as the two source-of-truth wrapper leaves, wrapper-generated CURRENT_EVIDENCE_SUMMARY refresh/placeholder plus source-backed recommendation-context/open-row separation before Cole-facing current-paper wording, the one-command operator-suite sweep that inherits rather than flattens those wrapper guardrails, the broader operator-suite route, the direct source-layer paper-trade chain routes, the parent-rollup reuse shortcut guardrails, documented output paths, and dated-report / legacy-alias guidance",
        )
    )
    checks.append(
        require(
            "two leaf source-of-truth wrapper reports whose inherited wrapper-guardrail inventories broader operator/project sweeps should preserve rather than flatten" in readme_text
            and "the other leaf source-of-truth wrapper report whose inherited wrapper-guardrail inventories broader operator/project sweeps should preserve rather than flatten" in readme_text
            and "wrapper-generated `CURRENT_EVIDENCE_SUMMARY` refresh/placeholder plus source-backed recommendation-context/open-row separation stays explicit before Cole-facing current-paper wording" in readme_text
            and "preserve the inherited wrapper-guardrail inventories from those two leaf wrapper reports rather than replacing them with one flattened green light" in readme_text,
            "readme_wrapper_leaf_source_of_truth_note_present",
            "README now says plainly that the refresh-helper and daily-wrapper validators are the source-of-truth wrapper leaves, that the daily-wrapper leaf carries wrapper-generated CURRENT_EVIDENCE_SUMMARY refresh/placeholder plus recommendation-context/open-row separation, and that the umbrella operator sweep should preserve rather than flatten their inherited guardrail inventories",
        )
    )
    checks.append(
        require(
            all(
                line in readme_text
                for line in [
                    expected_op_family_doc,
                    expected_op_family_validator,
                    expected_cross_family_doc,
                    expected_cross_family_validator,
                    expected_portfolio_decision_doc,
                    expected_portfolio_decision_validator,
                    expected_method_family_doc,
                    expected_method_family_validator,
                    expected_decision_cards_suite_validator,
                ]
            ),
            "decision_card_inventory_lines",
            "README now names the four report-facing decision cards plus their direct validators and the one-command decision-card suite in the repo inventory",
        )
    )
    checks.append(
        require(
            expected_op_anchor_doc in readme_text,
            "op_anchor_inventory_line",
            "the README still describes the OP-anchor comparison as both a Harville/XGBoost ranking guardrail and an explicit replay-only selective-family caution surface",
        )
    )
    checks.append(
        require(
            expected_main_comparison_doc in readme_text and expected_main_comparison_validator in readme_text,
            "main_comparison_inventory_lines",
            "README now names the generated main-comparison markdown/CSV/JSON bundle plus its direct validator in the report inventory, with Harville, current odds-only XGBoost, source-provenance, parity, machine-readable evidence-boundary, and decision-change-gate scope framed as reproducibility metadata rather than new evidence",
        )
    )
    checks.append(
        require(
            expected_full_data_retrain_doc in readme_text and expected_full_data_retrain_validator in readme_text,
            "full_data_retrain_inventory_lines",
            "README now names the full-data XGBoost retrain artifact plus its direct validator in the report inventory while keeping the exact commands and RMSE / MAE diagnostics out of the betting-evidence lane",
        )
    )
    checks.append(
        require(
            expected_current_evidence_doc in readme_text and expected_current_evidence_validator in readme_text,
            "current_evidence_inventory_lines",
            "README now names the source-checked and freshness-routed frozen-to-current bridge plus its direct validator in the report inventory so short Cole updates can be checked without skipping source consistency, source freshness, operator_read_gate routing, CD-only rule mix, bridge-published current gates, bridge rebuild-order routing, or no-overclaim boundaries",
        )
    )
    checks.append(
        require(
            expected_scorecard_audit_doc in readme_text
            and expected_scorecard_audit_validator in readme_text
            and "report-synchronization / reproducibility metadata only" in cold_start_block
            and "without becoming live paper, promotion, bankroll, or real-money evidence" in readme_text,
            "scorecard_audit_inventory_lines",
            "README now names the scorecard ranking-contract / gate-floor audit and validator in both the cold-start route and report inventory while keeping the audit out of live paper, promotion, bankroll, and real-money evidence",
        )
    )
    checks.append(
        require(
            expected_status_doc in readme_text and expected_status_doc_validator in readme_text,
            "status_doc_api_access_inventory_lines",
            "README now names the main status document plus its direct validator in the report inventory so status_doc_base_api_access_route_documented stays discoverable for base API-access / HTTP 403 status-summary route wording before lane enrichment",
        )
    )
    checks.append(
        require(
            expected_working_status_validator in readme_text,
            "working_status_validator_inventory_line",
            "README now names the direct validator for the dated working-status note, so cold readers can verify that live/demo-vs-production surface too",
        )
    )
    checks.append(
        require(
            expected_report_alias_note in readme_text,
            "report_alias_note",
            "README now says the dated HTML file is the trust anchor, the dated PDF is its derivative export, and the undated HTML/PDF/DOCX report aliases, old quick-start PDF, and historical OpenClaw prompt DOCX are only legacy aliases, not preferred validated report surfaces",
        )
    )
    checks.append(
        require(
            "- `Superfecta_Project_Report.html`" not in readme_text
            and "- `Superfecta_Project_Report.pdf`" not in readme_text,
            "legacy_report_aliases_not_listed_as_primary_artifacts",
            "README does not list the undated Superfecta_Project_Report.html or .pdf files in the main report inventory, so the legacy aliases are not promoted as primary report artifacts",
        )
    )
    checks.append(
        require_paths_exist(
            [
                BASE / "forward_evidence_scorecard.txt",
                BASE / "PAPER_TRADE_NOW.md",
                BASE / "CURRENT_EVIDENCE_SUMMARY.md",
                BASE / "current_evidence_summary.json",
                BASE / "SCORECARD_RANKING_CONTRACT_AUDIT.md",
                BASE / "scorecard_ranking_contract_audit.json",
                BASE / "COLE_STATUS_AND_PLAN.md",
                BASE / "validate_cole_status_and_plan.py",
                BASE / "out" / "status_validation" / "current_evidence_summary" / "current_evidence_summary_validation.md",
                BASE / "compare_main_approaches.md",
                BASE / "compare_main_approaches.csv",
                BASE / "compare_main_approaches.json",
                BASE / "FULL_DATA_RETRAIN_ARTIFACTS.md",
                BASE / "validate_full_data_retrain_artifacts.py",
                BASE / "out" / "status_validation" / "frozen_evidence_chain" / "frozen_evidence_chain_validation.md",
                BASE / "out" / "status_validation" / "paper_trade_now" / "paper_trade_now_validation.md",
                BASE / "out" / "status_validation" / "decision_cards_suite" / "decision_cards_suite_validation.md",
                BASE / "out" / "status_validation" / "cross_family_decision" / "cross_family_decision_validation.md",
                BASE / "out" / "status_validation" / "project_surfaces" / "project_surfaces_validation.md",
                BASE / "validate_forward_evidence_scorecard.py",
                BASE / "validate_scorecard_ranking_contract_audit.py",
                BASE / "validate_current_evidence_summary.py",
                BASE / "validate_paper_trade_now.py",
            ],
            "cold_start_paths_exist",
            "the cold-start research-side, one-screen main-comparison sidecar, and operator-side paths named directly in README all exist on disk, so the landing page is not routing readers to stale artifacts",
        )
    )
    checks.append(
        require_paths_exist(
            [
                BASE / "Superfecta_Project_Report_2026-04-15.html",
                BASE / "Superfecta_Project_Report_2026-04-15.pdf",
                BASE / "Superfecta_Project_Report.html",
                BASE / "Superfecta_Project_Report.pdf",
                BASE / "Superfecta_Project_Report.docx",
                BASE / "Superfecta Prediction - Quick Start Guide.pdf",
                BASE / "OpenClaw Prompt.docx",
                BASE / "VALIDATION_QUICKSTART.md",
                BASE / "validate_validation_quickstart.py",
            ],
            "report_anchor_and_runbook_paths_exist",
            "the shareable report trust-anchor files, the legacy alias surfaces, and the validated quickstart runbook named in README all exist on disk",
        )
    )
    checks.append(
        require_paths_exist(
            [
                BASE / "compare_main_approaches.py",
                BASE / "ab_downstream_comparison.py",
                BASE / "op_anchor_method_comparison.py",
                BASE / "compare_recommender_scope_paths.py",
                BASE / "forward_evidence_scorecard.py",
                BASE / "current_evidence_summary.py",
                BASE / "portfolio_decision_card.py",
                BASE / "method_family_decision_card.py",
                BASE / "experiment_selector_variants.py",
                BASE / "experiment_sample_size.py",
                BASE / "walk_forward_validation.py",
                BASE / "evaluate_frozen_portfolios.py",
            ],
            "core_strategy_inventory_paths_exist",
            "the core strategy and evaluation scripts listed in README all exist on disk, so the landing page is not naming stale research entry points",
        )
    )
    checks.append(
        require_paths_exist(
            [
                BASE / "superfecta_ops.py",
                BASE / "demo_live_predictions.py",
                BASE / "live_portfolio_scanner.py",
                BASE / "scan_live.sh",
            ],
            "live_demo_inventory_paths_exist",
            "the live and demo operations scripts listed in README all exist on disk, so the landing page keeps the ops surface honest too",
        )
    )
    checks.append(
        require_paths_exist(
            [
                BASE / "run_daily_portfolio_observation.sh",
                BASE / "paper_trade_pipeline.py",
                BASE / "paper_trade_status_summary.py",
                BASE / "paper_trade_now.py",
                BASE / "paper_trade_daily_summary.py",
                BASE / "paper_trade_lane_summary.py",
                BASE / "paper_trade_forward_check.py",
                BASE / "paper_trade_lane_monitor.py",
                BASE / "paper_trade_next_steps.py",
                BASE / "paper_trade_ops_history.py",
                BASE / "paper_trade_settlement_sync.py",
                BASE / "paper_trade_settlement_helper.py",
                BASE / "paper_trade_preflight_note.py",
                BASE / "refresh_live_paper_trade_surfaces.py",
            ],
            "paper_trade_ops_inventory_paths_exist",
            "the core paper-trade operation scripts listed in README all exist on disk, so the landing-page operator inventory stays honest across the full saved-surface generation chain rather than only a subset of the paper-trade helpers",
        )
    )
    checks.append(
        require_paths_exist(
            [
                BASE / "PAPER_TRADE_NOW.md",
                BASE / "OPS_HISTORY.md",
                BASE / "DAILY_ARTIFACT_GUIDE.md",
                BASE / "PAPER_TRADE_USAGE.md",
                BASE / "validate_paper_trade_now.py",
                BASE / "validate_paper_trade_ops_history.py",
                BASE / "validate_paper_trade_preflight_note.py",
                BASE / "validate_daily_artifact_guide.py",
                BASE / "validate_paper_trade_usage.py",
                BASE / "validate_paper_trade_status_summary.py",
                BASE / "validate_paper_trade_daily_summary.py",
                BASE / "validate_refresh_live_paper_trade_surfaces.py",
                BASE / "validate_run_daily_portfolio_observation.py",
                BASE / "validate_paper_trade_operator_suite.py",
            ],
            "operator_inventory_paths_exist",
            "the operator-facing docs and direct validators listed in the README inventory all exist on disk, so the landing page stays honest for paper-operator navigation too",
        )
    )
    checks.append(
        require_paths_exist(
            [
                BASE / "COLE_STATUS_AND_PLAN.md",
                BASE / "validate_cole_status_and_plan.py",
                BASE / "COLE_FULL_REPORT_2026-04-15.md",
                BASE / "OP_FAMILY_DECISION.md",
                BASE / "validate_op_family_decision.py",
                BASE / "CROSS_FAMILY_DECISION.md",
                BASE / "validate_cross_family_decision.py",
                BASE / "PORTFOLIO_DECISION_CARD.md",
                BASE / "validate_portfolio_decision_card.py",
                BASE / "METHOD_FAMILY_DECISION.md",
                BASE / "validate_method_family_decision_card.py",
                BASE / "validate_decision_cards_suite.py",
                BASE / "compare_main_approaches.md",
                BASE / "compare_main_approaches.csv",
                BASE / "compare_main_approaches.json",
                BASE / "validate_compare_main_approaches.py",
                BASE / "CURRENT_EVIDENCE_SUMMARY.md",
                BASE / "current_evidence_summary.json",
                BASE / "validate_current_evidence_summary.py",
                BASE / "WORKING_STATUS_REPORT_2026-04-15.md",
                BASE / "validate_working_status_report.py",
                BASE / "OVERNIGHT_PROGRESS.md",
                BASE / "AB_DOWNSTREAM_COMPARISON.md",
                BASE / "validate_ab_downstream_comparison.py",
                BASE / "FULL_DATA_RETRAIN_ARTIFACTS.md",
                BASE / "validate_full_data_retrain_artifacts.py",
                BASE / "OP_ANCHOR_METHOD_COMPARISON.md",
                BASE / "validate_op_anchor_method_comparison.py",
                BASE / "compare_recommender_scope_paths.md",
                BASE / "validate_compare_recommender_scope_paths.py",
            ],
            "highlighted_report_inventory_paths_exist",
            "the highlighted report, decision-card, main-comparison sidecar, and guardrail artifacts listed in the README report inventory all exist on disk, so the landing-page repo map stays honest",
        )
    )

    suite_read = (
        f"README current status matches frozen evidence: anchor={anchor['rule_id']} ({float(anchor['holdout_roi']):+.1f}% on {int(anchor['holdout_races'])}); "
        f"paper={phase7['label']} ({float(phase7['holdout_roi']):+.2f}% on {int(phase7['holdout_races'])}; 2024={float(phase7['holdout_2024_roi']):+.2f}% on {int(phase7['holdout_2024_races'])}, 2025={float(phase7['holdout_2025_roi']):+.2f}% on {int(phase7['holdout_2025_races'])}); "
        f"selector benchmark={selector['label']} ({float(selector['wf_roi']):+.2f}% WF, {float(selector['holdout_roi']):+.2f}% holdout); "
        f"cold-start reads=forward_evidence_scorecard.txt on the research side, current_evidence_summary.json scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus validate_scorecard_ranking_contract_audit.py for copied gate-floor/ranking/CI-only/timezone/no-BAQ prerequisite drift as synchronization metadata only, and PAPER_TRADE_NOW.md on the operator side, with the operator-side top card now explicitly framed as preserving primary/shadow recent-run context plus lifted lane why-now lines, exposing direct primary/shadow pipeline/scanner status-sidecar pointers plus a matched PAPER_TRADE_NOW.json operator_read_gate, and labeling stale downstream lane details as inherited snapshot context rather than current-day state, the frozen-to-current bridge `CURRENT_EVIDENCE_SUMMARY.md` / `current_evidence_summary.json` now visible for short Cole updates with source consistency, the combined operator-status/source-freshness/operator-read-gate route, CD-only current rule mix, {bridge_queue_navigation}, scorecard_audit_route synchronization routing to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization metadata only, rebuild_validation_contract order routing through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py as provenance/rebuild metadata only before quoting current totals after source-byte changes, bridge-published current gates source-matched to `forward_evidence_scorecard.json` `decision_gate_minimums` with anchor_displacement={scorecard_anchor_min}, phase8_promotion_review={scorecard_phase8_min}, and real_money_discussion={scorecard_real_money_min}, direct `decision_gate_progress` read={current_gate_progress_read}, operator_read_gate read={operator_read_gate_read}, and no-new-forward-evidence / no-promotion / no-live-profitability / no-real-money boundaries, the main status / repo-map route `COLE_STATUS_AND_PLAN.md` plus `validate_cole_status_and_plan.py` now visible for `status_doc_base_api_access_route_documented` base API-access / HTTP 403 status-summary route wording before lane enrichment as status/map alignment metadata only, the daily guide now also explicitly pointing issue-day triage at those top-card sidecar pointers, the direct decision-card path `OP_FAMILY_DECISION.md` -> `CROSS_FAMILY_DECISION.md` current-paper snapshot caveat -> `PORTFOLIO_DECISION_CARD.md` -> `METHOD_FAMILY_DECISION.md`, the direct cross-family current-paper validation path now pins stale-card refresh routing, CD-only settled rows, source-published settlement-queue state/context, and no OP-anchor / no cross-family-promotion evidence before broader decision-card or project sweeps, the direct one-screen main comparison route `compare_main_approaches.md` plus matched CSV/JSON sidecars now explicitly covers the OP/CD paper core, `OP_REFINED_K7` shadow-only challenger, Harville benchmark-only lane, current odds-only XGBoost research-only lane, evidence-class triage, source provenance/parity, and machine-readable evidence boundary as reproducibility/navigation metadata rather than new evidence, the direct full-data XGBoost retrain caveat route `FULL_DATA_RETRAIN_ARTIFACTS.md` plus `validate_full_data_retrain_artifacts.py` now keeps exact retrain/prediction commands and RMSE / MAE diagnostics in model-fit context only rather than paper-trade, live-profitability, promotion, bankroll, or real-money evidence, the dedicated OP-anchor comparison doc now explicitly carries unlike evidence-class labeling plus the parked odds-only XGBoost reopening bar, the validated decision-card suite report now explicitly framed as a frozen-evidence ordering check rather than new proof, the validated repo-wide read now explicitly framed as a cross-layer alignment check rather than new forward evidence, and named cold-start/report, research-inventory, live-ops, paper-trade, and operator-doc paths pinned to real files, including the generated main-comparison markdown/CSV/JSON bundle plus direct validator in the report inventory, the source-checked current-evidence bridge with the combined operator-read route plus direct validator, bridge-owned scorecard-audit routing, and bridge-owned rebuild-order routing in the report inventory, the main status document plus direct validator in the report inventory, the scorecard audit markdown/JSON plus direct validator in the report inventory as synchronization/reproducibility metadata only, the full-data retrain artifact plus direct validator in the report inventory, the human-facing `OPS_HISTORY.md` surface plus its source `paper_trade_ops_history.py` helper, the shared `paper_trade_preflight_note.py` helper, the source `paper_trade_status_summary.py` and `paper_trade_now.py` helpers, the combined daily-summary helper with its routed top-card focus/timing/freshness/ops snapshot plus the saved-live refresh helper with rebuilt daily summaries inheriting refreshed top-card snapshot lines, rebuilt top-card recent-run context plus lifted lane why-now lines preserved when current lane artifacts provide them, stale rebuilt cards keeping the inherited-snapshot honesty note, `--latest-only` confined to the newest copied run's preflight, lane, and daily-summary surfaces, `--skip-top-level` confined to leaving `OPS_HISTORY` / `PAPER_TRADE_NOW` untouched while still rerendering those per-run surfaces against the existing top-level outputs, plus the real daily-wrapper validator as the other source-of-truth wrapper leaf carrying wrapper-generated CURRENT_EVIDENCE_SUMMARY refresh/placeholder plus source-backed recommendation-context/open-row separation before Cole-facing current-paper wording, explicit `--as-of-date` freshness pinning that now says whether it was applied or skipped because top-level outputs were refreshed or skipped, and the note that the operator-suite sweep should preserve those inherited wrapper-guardrail inventories rather than flattening them, all inside the rerender-only/not-new-evidence boundary, the direct ops-history / preflight-note / base-status-summary / combined-daily-summary / refresh-helper / daily-wrapper validators, with the top-card and wrapper paths now carrying the stronger recent-run-context-plus-lifted-lane-why-now preservation contract, stale-card inherited-snapshot honesty note, routed top-card snapshot inheritance, operator_read_gate no-evidence routing, plus the direct sidecar-pointer contract, the direct decision-card validators plus the one-command decision-card suite, the one-command operator-suite sweep, and the report-alias note that demotes the undated HTML/PDF/DOCX report aliases, old quick-start PDF, and historical OpenClaw prompt DOCX to legacy surfaces; "
        f"source-published settlement queue state/detail read={open_settlement_queue_state} / {open_settlement_context} with by-rule detail preserved as workflow metadata only; "
        f"Phase 8={phase8['role']} ({float(phase8['holdout_roi']):+.2f}% on {int(phase8['holdout_races'])}; 2024={float(phase8['holdout_2024_roi']):+.2f}% on {int(phase8['holdout_2024_races'])}, 2025={float(phase8['holdout_2025_roi']):+.2f}% on {int(phase8['holdout_2025_races'])}); "
        "landing-page shadow split keeps OP_REFINED_K7 as the closest same-family challenger while KEE_K9 / SA_K9 / DMR_FALL_K7 stay observation-only pockets; "
        f"method roles={selective['role']} / {harville['role']} / {xgboost['role']}"
    )

    payload = {
        "suite_status": "pass",
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "summary": {
            "suite_read": suite_read,
        },
        "scorecard_decision_gate_minimums_read": scorecard_gate_read,
        "current_evidence_gate_progress_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            "source_path": "decision_gate_progress",
            "scorecard_source": current_gate_progress.get("source_path"),
            "scorecard_source_json_path": current_gate_progress.get("source_json_path"),
            "gate_status": current_gate_progress.get("gate_status"),
            "all_gates_ready": current_gate_progress.get("all_gates_ready"),
            "primary_first_read": current_primary_gate_progress,
            "op_anchor_same_candidate_review": current_op_anchor_gate_progress,
            "phase8_promotion_review": current_phase8_gate_progress,
            "real_money_discussion": current_real_money_gate_progress,
            "read": current_gate_progress_read,
            "not_forward_performance_evidence": True,
            "not_promotion_readiness_evidence": True,
            "not_live_profitability_evidence": True,
            "not_real_money_evidence": True,
        },
        "current_evidence_operator_read_gate_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            "source_path": "operator_read_gate",
            "gate_status": operator_read_gate.get("gate_status"),
            "valid_use": operator_read_gate.get("valid_use"),
            "requires_refresh_before_evidence_read": operator_read_gate.get("requires_refresh_before_evidence_read"),
            "has_api_access_failure_context": operator_read_gate.get("has_api_access_failure_context"),
            "has_scanner_failure_boundary": operator_read_gate.get("has_scanner_failure_boundary"),
            "has_stale_cache_fallback_context": operator_read_gate.get("has_stale_cache_fallback_context"),
            "recommended_command": operator_read_gate.get("recommended_command"),
            "current_top_card_counts_as_no_target_evidence": operator_read_gate.get("current_top_card_counts_as_no_target_evidence"),
            "current_top_card_counts_as_clean_empty_evidence": operator_read_gate.get("current_top_card_counts_as_clean_empty_evidence"),
            "current_top_card_counts_as_bet_readiness_evidence": operator_read_gate.get("current_top_card_counts_as_bet_readiness_evidence"),
            "current_top_card_counts_as_settled_roi_evidence": operator_read_gate.get("current_top_card_counts_as_settled_roi_evidence"),
            "not_forward_performance_evidence": operator_read_gate.get("not_forward_performance_evidence"),
            "not_promotion_readiness_evidence": operator_read_gate.get("not_promotion_readiness_evidence"),
            "not_live_profitability_evidence": operator_read_gate.get("not_live_profitability_evidence"),
            "not_real_money_evidence": operator_read_gate.get("not_real_money_evidence"),
            "read": operator_read_gate_read,
        },
        "current_evidence_api_access_route_read": api_access_route_read,
        "current_evidence_scorecard_audit_route_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            "source_path": "scorecard_audit_route",
            "markdown_path": scorecard_audit_route.get("markdown_path"),
            "json_path": scorecard_audit_route.get("json_path"),
            "validator_command": scorecard_audit_route.get("validator_command"),
            "gate_floor_source": scorecard_audit_route.get("gate_floor_source"),
            "gate_floor_snapshot": scorecard_audit_gate_floor_snapshot,
            "route_read": scorecard_audit_route.get("route_read"),
            "valid_use": scorecard_audit_route.get("valid_use"),
            "artifacts_present": scorecard_audit_route.get("artifacts_present"),
            "not_forward_performance_evidence": scorecard_audit_route.get("not_forward_performance_evidence"),
            "not_settled_roi_evidence": scorecard_audit_route.get("not_settled_roi_evidence"),
            "not_promotion_readiness_evidence": scorecard_audit_route.get("not_promotion_readiness_evidence"),
            "not_live_profitability_evidence": scorecard_audit_route.get("not_live_profitability_evidence"),
            "not_bankroll_guidance": scorecard_audit_route.get("not_bankroll_guidance"),
            "not_real_money_evidence": scorecard_audit_route.get("not_real_money_evidence"),
        },
        "current_evidence_rebuild_validation_contract_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            "source_path": "rebuild_validation_contract",
            "rebuild_command": rebuild_validation_contract.get("rebuild_command"),
            "prerequisite_rebuild_command": rebuild_validation_contract.get("prerequisite_rebuild_command"),
            "upstream_refresh_order": rebuild_order_commands,
            "direct_validation_command": rebuild_validation_contract.get("direct_validation_command"),
            "valid_use": rebuild_validation_contract.get("upstream_refresh_order_valid_use"),
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": rebuild_validation_contract.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"),
            "requires_source_consistency_before_quoting_current_totals": rebuild_validation_contract.get("requires_source_consistency_before_quoting_current_totals"),
            "upstream_refresh_order_is_provenance_metadata_only": rebuild_validation_contract.get("upstream_refresh_order_is_provenance_metadata_only"),
            "not_settled_roi_or_real_money_evidence": rebuild_validation_contract.get("not_settled_roi_or_real_money_evidence"),
        },
        "current_evidence_settlement_queue_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            "source_path": "current_paper_status.primary.open_settlement_queue_by_rule",
            "open_settlements": open_settlements,
            "open_settlement_queue_state": open_settlement_queue_state,
            "open_settlement_context": open_settlement_context,
            "detail_read": open_settlement_detail_read,
            "source_published_queue_read": source_published_queue_read,
            "not_forward_performance_evidence": True,
            "not_promotion_readiness_evidence": True,
            "not_live_profitability_evidence": True,
            "not_real_money_evidence": True,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }

    lines = [
        "# README Current Status Validation",
        "",
        "This report checks that the repo landing page still matches the frozen evidence standard instead of drifting toward stale research-only headlines.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Target file: `{README.name}`",
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
            f"- Anchor line: {expected_anchor_line}",
            f"- Paper line: {expected_paper_line}",
            f"- Selector line: {expected_selector_line}",
            f"- Phase 8 line: {expected_phase8_line}",
            f"- Shadow split line: {expected_shadow_split_line}",
            f"- Current evidence bridge line: {expected_current_evidence_line}",
            f"- Current evidence gate-progress read: {current_gate_progress_read}",
            f"- Current evidence operator-read-gate read: {operator_read_gate_read}",
            f"- Source-published settlement queue read: {source_published_queue_read}",
            f"- Current evidence API-access route read: route_required={api_access_route_read['route_required']}; action={api_access_route_read['readme_has_sidecar_action']}; recheck={api_access_route_read['readme_has_recheck_command']}",
            f"- Scorecard gate source: `{SCORECARD_JSON.name}` `decision_gate_minimums` (`anchor_displacement={scorecard_anchor_min}`, `phase8_promotion_review={scorecard_phase8_min}`, `real_money_discussion={scorecard_real_money_min}`)",
            f"- Cold-start scorecard read: {expected_cold_start_scorecard}",
            f"- Cold-start current-evidence bridge read: {expected_cold_start_current_evidence}",
            f"- Cold-start status-doc route: {expected_cold_start_status_doc_route}",
            f"- Cold-start cross-family validation read: {expected_cold_start_cross_family_validation}",
            f"- Cold-start main comparison read: {expected_cold_start_main_comparison}",
            f"- Cold-start frozen sweep: {expected_cold_start_frozen}",
            f"- Cold-start scorecard validator: {expected_cold_start_scorecard_validator}",
            f"- Cold-start current-evidence validator: {expected_cold_start_current_evidence_validator}",
            f"- Cold-start cross-family validator: {expected_cold_start_cross_family_validator}",
            f"- Core strategy inventory: {'; '.join(expected_core_strategy_lines[:5])}; ...",
            f"- Live/demo inventory: {'; '.join(expected_live_demo_lines)}",
            f"- Paper-trade ops inventory: {'; '.join(expected_paper_trade_ops_lines[:4])}; ...",
            f"- Operator docs inventory: {expected_operator_doc_now}; {expected_operator_doc_ops_history}; {expected_operator_doc_guide}; {expected_operator_doc_usage}; {expected_quickstart_doc}",
            f"- Operator validator inventory: {expected_operator_validator_now}; {expected_operator_validator_ops_history}; {expected_operator_validator_preflight}; {expected_operator_validator_status_summary}; {expected_operator_validator_daily_summary}; {expected_operator_validator_refresh}; {expected_operator_validator_daily_wrapper}; {expected_operator_validator_suite}; {expected_quickstart_validator}",
            f"- Main comparison inventory: {expected_main_comparison_doc}; {expected_main_comparison_validator}",
            f"- Status-doc inventory: {expected_status_doc}; {expected_status_doc_validator}",
            f"- Current evidence inventory: {expected_current_evidence_doc}; {expected_current_evidence_validator}",
            f"- Working-status validator inventory: {expected_working_status_validator}",
            f"- Report alias note: {expected_report_alias_note}",
            "",
            "## Source Artifacts",
            "",
            f"- `{SCORECARD_CSV.name}`",
            f"- `{SCORECARD_JSON.name}`",
            f"- `{PORTFOLIO_CSV.name}`",
            f"- `{METHOD_CSV.name}`",
        ]
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
