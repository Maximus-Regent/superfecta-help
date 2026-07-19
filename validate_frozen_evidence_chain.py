#!/usr/bin/env python3
"""
Run the broader frozen-evidence validators as one compact sweep.

Purpose:
- give Cole one command for the report-facing evidence chain
- bundle the forward-evidence scorecard, comparison harness, direct walk-forward caution, direct frozen-replay caution/metadata check,
  direct Phase 7/Phase 8 legacy-report cautions, direct legacy broad-backtest caution, frozen stack, direct card-suite checks, the cross-surface scorecard ranking-contract audit,
  the narrow comparison artifacts that defend the OP anchor, the downstream enriched-horse-history XGBoost research-only read,
  the full-data XGBoost retrain diagnostic boundary, and the selective-scope guardrail
- summarize whether the full conservative story is still aligned after edits
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import validate_ab_downstream_comparison as ab_downstream
import validate_backtest_report_caution as backtest_report_caution
import validate_compare_main_approaches as compare_main
import validate_compare_recommender_scope_paths as recommender_scope
import validate_decision_cards_suite as decision_cards
import validate_forward_evidence_scorecard as forward_scorecard
import validate_frozen_decision_stack as frozen_stack
import validate_frozen_portfolio_eval_caution as frozen_replay_caution
import validate_full_data_retrain_artifacts as full_data_retrain_artifacts
import validate_phase7_report_caution as phase7_report_caution
import validate_phase8_report_caution as phase8_report_caution
import validate_walk_forward_validation_caution as walk_forward_caution
import validate_op_anchor_method_comparison as op_anchor
import validate_scorecard_ranking_contract_audit as ranking_contract_audit

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "out" / "status_validation" / "frozen_evidence_chain"
OUT_MD = OUT_DIR / "frozen_evidence_chain_validation.md"
OUT_JSON = OUT_DIR / "frozen_evidence_chain_validation.json"
REBUILD_COMMAND = "python3 validate_frozen_evidence_chain.py"
REUSE_EXISTING_FLAG = "--reuse-existing-child-json"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "research-side frozen-evidence validator rollup",
    "source_scope": [
        "forward-evidence scorecard validator output",
        "main comparison validator output",
        "walk-forward validation caution validator output",
        "frozen replay caution / metadata validator output",
        "Phase 7 legacy-report caution validator output",
        "Phase 8 legacy-report caution validator output",
        "legacy broad-backtest caution validator output",
        "frozen decision-stack validator output",
        "decision-card suite validator output",
        "scorecard ranking-contract audit output",
        "OP-anchor comparison validator output",
        "downstream XGBoost A/B validator output",
        "full-data XGBoost retrain artifact validator output",
        "selective-scope comparison validator output",
    ],
    "valid_use": "alignment and reproducibility audit for frozen report-facing evidence ordering",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
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
        "do not use a green frozen-evidence sweep as settled ROI",
        "do not use child JSON hashes as performance evidence",
        "do not treat the train-only walk-forward selector benchmark as settled paper-trade ROI",
        "do not treat legacy broad-backtest baselines as current deployment guidance",
        "do not promote OP_REFINED_K7 or Phase 8 from validation cleanliness",
        "do not treat the Phase 7 legacy report by itself as live-profitability, bankroll, or real-money evidence",
        "do not reopen current odds-only XGBoost from validation cleanliness",
        "do not treat full-data XGBoost retrain RMSE / MAE improvements as paper-trade evidence",
        "do not treat Harville benchmark-only output as a live approach",
        "do not substitute BAQ for BEL",
        "do not discuss real-money scaling from validator passes",
    ],
}

SUITE: list[dict[str, Any]] = [
    {
        "name": "forward_evidence_scorecard",
        "label": "Forward evidence scorecard",
        "runner": forward_scorecard.main,
        "json_path": BASE / "out" / "status_validation" / "forward_evidence_scorecard" / "forward_evidence_scorecard_validation.json",
        "metric_key": "check_count",
    },
    {
        "name": "compare_main_approaches",
        "label": "Compare main approaches",
        "runner": compare_main.main,
        "json_path": BASE / "out" / "status_validation" / "compare_main_approaches" / "compare_main_approaches_validation.json",
        "metric_key": "check_count",
    },
    {
        "name": "walk_forward_validation_caution",
        "label": "Walk-forward validation caution",
        "runner": walk_forward_caution.main,
        "json_path": BASE / "out" / "status_validation" / "walk_forward_validation_caution" / "walk_forward_validation_caution_validation.json",
        "metric_key": "check_count",
    },
    {
        "name": "frozen_portfolio_eval_caution",
        "label": "Frozen portfolio replay caution",
        "runner": frozen_replay_caution.main,
        "json_path": BASE / "out" / "status_validation" / "frozen_portfolio_eval_caution" / "frozen_portfolio_eval_caution_validation.json",
        "metric_key": "check_count",
    },
    {
        "name": "phase7_report_caution",
        "label": "Phase 7 legacy report caution",
        "runner": phase7_report_caution.main,
        "json_path": BASE / "out" / "status_validation" / "phase7_report_caution" / "phase7_report_caution_validation.json",
        "metric_key": "check_count",
    },
    {
        "name": "phase8_report_caution",
        "label": "Phase 8 legacy report caution",
        "runner": phase8_report_caution.main,
        "json_path": BASE / "out" / "status_validation" / "phase8_report_caution" / "phase8_report_caution_validation.json",
        "metric_key": "check_count",
    },
    {
        "name": "backtest_report_caution",
        "label": "Legacy broad-backtest caution",
        "runner": backtest_report_caution.main,
        "json_path": BASE / "out" / "status_validation" / "backtest_report_caution" / "backtest_report_caution_validation.json",
        "metric_key": "check_count",
    },
    {
        "name": "frozen_decision_stack",
        "label": "Frozen decision stack",
        "runner": frozen_stack.main,
        "json_path": BASE / "out" / "status_validation" / "frozen_decision_stack" / "frozen_decision_stack_validation.json",
        "metric_key": "total_checks",
    },
    {
        "name": "decision_cards_suite",
        "label": "Decision cards suite",
        "runner": decision_cards.main,
        "json_path": BASE / "out" / "status_validation" / "decision_cards_suite" / "decision_cards_suite_validation.json",
        "metric_key": "total_frozen_checks",
    },
    {
        "name": "scorecard_ranking_contract_audit",
        "label": "Scorecard ranking-contract audit",
        "runner": ranking_contract_audit.main,
        "json_path": BASE / "out" / "status_validation" / "scorecard_ranking_contract_audit" / "scorecard_ranking_contract_audit_validation.json",
        "metric_key": "check_count",
    },
    {
        "name": "op_anchor_method_comparison",
        "label": "OP anchor method comparison",
        "runner": op_anchor.main,
        "json_path": BASE / "out" / "status_validation" / "op_anchor_method_comparison" / "op_anchor_method_comparison_validation.json",
        "metric_key": "check_count",
    },
    {
        "name": "ab_downstream_comparison",
        "label": "Downstream XGBoost A/B comparison",
        "runner": ab_downstream.main,
        "json_path": BASE / "out" / "status_validation" / "ab_downstream_comparison" / "ab_downstream_comparison_validation.json",
        "metric_key": "check_count",
    },
    {
        "name": "full_data_retrain_artifacts",
        "label": "Full-data XGBoost retrain artifact",
        "runner": full_data_retrain_artifacts.main,
        "json_path": BASE / "out" / "status_validation" / "full_data_retrain_artifacts" / "full_data_retrain_artifacts_validation.json",
        "metric_key": "check_count",
    },
    {
        "name": "compare_recommender_scope_paths",
        "label": "Recommender scope comparison",
        "runner": recommender_scope.main,
        "json_path": BASE / "out" / "status_validation" / "compare_recommender_scope_paths" / "compare_recommender_scope_paths_validation.json",
        "metric_key": "check_count",
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
    ordered_reads = [
        ("scorecard", payload_map["forward_evidence_scorecard"].get("summary", {}).get("suite_read", "")),
        ("comparison layer", payload_map["compare_main_approaches"].get("summary", {}).get("suite_read", "")),
        ("walk-forward caution", payload_map["walk_forward_validation_caution"].get("summary", {}).get("suite_read", "")),
        ("frozen replay caution", payload_map["frozen_portfolio_eval_caution"].get("summary", {}).get("suite_read", "")),
        ("Phase 7 report caution", payload_map["phase7_report_caution"].get("summary", {}).get("suite_read", "")),
        ("Phase 8 report caution", payload_map["phase8_report_caution"].get("summary", {}).get("suite_read", "")),
        ("legacy broad backtest", payload_map["backtest_report_caution"].get("summary", {}).get("suite_read", "")),
        ("frozen stack", payload_map["frozen_decision_stack"].get("summary", {}).get("suite_read", "")),
        ("decision cards", payload_map["decision_cards_suite"].get("summary", {}).get("suite_read", "")),
        ("scorecard ranking-contract audit", payload_map["scorecard_ranking_contract_audit"].get("summary", {}).get("suite_read", "")),
        ("OP anchor comparison", payload_map["op_anchor_method_comparison"].get("summary", {}).get("suite_read", "")),
        ("downstream A/B", payload_map["ab_downstream_comparison"].get("summary", {}).get("suite_read", "")),
        ("full-data retrain", payload_map["full_data_retrain_artifacts"].get("summary", {}).get("suite_read", "")),
        ("scope guardrail", payload_map["compare_recommender_scope_paths"].get("summary", {}).get("current_read", "")),
    ]
    return "; ".join(
        [
            *(f"{label}: {text}" for label, text in ordered_reads),
            "frozen-evidence chain layer: research-side evidence-alignment check, not new forward evidence by itself; stronger forward confidence still requires settled paper trades and other real forward results",
            "frozen-evidence chain source audit: exact child-validation JSON byte counts and SHA-256 hashes are published for reproducibility only, not performance evidence",
            "frozen-evidence chain evidence boundary: machine-readable evidence_boundary metadata keeps research validator passes, child hashes, and frozen replay alignment separate from settled ROI, current-day scanner output, live profitability, promotion readiness, and real-money evidence",
        ]
    )



def main() -> int:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rebuild_command = REBUILD_COMMAND + (f" {REUSE_EXISTING_FLAG}" if args.reuse_existing_child_json else "")
    child_validator_mode = "reuse-existing-child-json" if args.reuse_existing_child_json else "rebuild-children"

    rows: list[dict[str, Any]] = []
    total_checks = 0
    payload_map: dict[str, dict[str, Any]] = {}

    for item in SUITE:
        payload = load_child_payload(item, args.reuse_existing_child_json)
        child_fingerprint = fingerprint_file(item["json_path"])
        payload_map[item["name"]] = payload
        artifact_status = require_child_status(payload, item["label"])
        check_count = require_explicit_int(payload, item["metric_key"], item["label"])
        child_check_count = require_explicit_int(payload, "check_count", item["label"])
        child_checks = require_child_checks(payload, item["label"])
        current_read = require_child_read(payload, item["label"])
        total_checks += check_count
        rows.append(
            {
                "name": item["name"],
                "label": item["label"],
                "check_count": check_count,
                "result": artifact_status,
                "current_read": current_read,
                "json_path": child_fingerprint["path"],
                "child_json_bytes": child_fingerprint["bytes"],
                "child_json_sha256": child_fingerprint["sha256"],
                "child_json_fingerprint": child_fingerprint,
                "child_check_count": child_check_count,
                "child_checks": child_checks,
                "child_scratch": payload.get("scratch") if isinstance(payload.get("scratch"), dict) else {},
                "child_scorecard_audit_route_diagnostics": (
                    payload.get("scorecard_audit_route_diagnostics")
                    if isinstance(payload.get("scorecard_audit_route_diagnostics"), dict)
                    else {}
                ),
                "child_rebuild_validation_contract_diagnostics": (
                    payload.get("rebuild_validation_contract_diagnostics")
                    if isinstance(payload.get("rebuild_validation_contract_diagnostics"), dict)
                    else {}
                ),
            }
        )

    overall_pass = all(row["result"] == "PASS" for row in rows)
    if not overall_pass:
        raise AssertionError("Frozen evidence chain has at least one failing validator")

    row_map = {row["name"]: row for row in rows}
    checks = [
        require(
            all(row_map[name]["result"] == "PASS" for name in row_map)
            and all(isinstance(row_map[name]["check_count"], int) and row_map[name]["check_count"] > 0 for name in row_map)
            and all(isinstance(row_map[name]["child_check_count"], int) and row_map[name]["child_check_count"] > 0 for name in row_map)
            and all(isinstance(row_map[name]["current_read"], str) and row_map[name]["current_read"].strip() for name in row_map),
            "child_research_validators_publish_explicit_status_metrics_counts_and_reads",
            "all fourteen frozen-evidence child validators now have to publish explicit PASS status, explicit advertised metric integers, nonzero check_count, and non-empty summary read metadata instead of letting the research umbrella infer them from fallback list lengths or partial payloads",
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
            "child_validator_json_fingerprints_are_published",
            "frozen-evidence chain now publishes exact byte counts and SHA-256 hashes for every child validation JSON it summarized, so parent rollups are reproducible without treating child hashes as performance evidence",
        ),
        require(
            "OP_DURABLE_K7 stays ANCHOR" in row_map["forward_evidence_scorecard"]["current_read"]
            and "CD_CORE_K8 stays PAPER" in row_map["forward_evidence_scorecard"]["current_read"]
            and "OP_REFINED_K7" in row_map["forward_evidence_scorecard"]["current_read"],
            "scorecard_keeps_deployment_tiers",
            "scorecard rollup still keeps OP_DURABLE_K7 as ANCHOR, CD_CORE_K8 as PAPER, and OP_REFINED_K7 in the smaller-sample challenger lane",
        ),
        require(
            payload_map["forward_evidence_scorecard"].get("suite_status") == "pass"
            and int(payload_map["forward_evidence_scorecard"].get("total_checks", 0)) == 33
            and payload_map["forward_evidence_scorecard"].get("valid_evidence_scope") == "frozen_holdout_walk_forward_scorecard_only"
            and payload_map["forward_evidence_scorecard"].get("evidence_boundary", {}).get("valid_evidence_scope") == "frozen_holdout_walk_forward_scorecard_only"
            and payload_map["forward_evidence_scorecard"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and payload_map["forward_evidence_scorecard"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and row_map["forward_evidence_scorecard"].get("child_scratch", {}).get("tmp_parent_is_project_local") is True
            and row_map["forward_evidence_scorecard"].get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and payload_map["compare_main_approaches"].get("suite_status") == "pass"
            and int(payload_map["compare_main_approaches"].get("total_checks", 0)) == 65
            and isinstance(payload_map["compare_main_approaches"].get("evidence_boundary"), dict)
            and payload_map["compare_main_approaches"]["evidence_boundary"].get("artifact_role") == "main approach comparison bundle"
            and payload_map["compare_main_approaches"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["compare_main_approaches"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["compare_main_approaches"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["compare_main_approaches"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["compare_main_approaches"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and payload_map["compare_main_approaches"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and row_map["compare_main_approaches"].get("child_scratch", {}).get("tmp_parent_is_project_local") is True
            and row_map["compare_main_approaches"].get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True,
            "core_research_source_validators_publish_explicit_suite_status_and_totals",
            "the forward-evidence scorecard and main-comparison source validators now publish explicit top-level suite_status plus total_checks metadata, including the scorecard text/CSV source-scope disclosure, direct valid_evidence_scope metadata, CSV bootstrap-CI source-note columns, CSV/JSON bootstrap-CI source parity, machine-readable JSON evidence boundary, machine-readable decision-gate minimums, generated-at timezone-label contract and no-timezone CLI fail-fast coverage, project-local CLI scratch-root metadata, plus the main-comparison inherited scorecard ranking contract, main-comparison machine-readable evidence boundary, project-local CLI scratch-root metadata, markdown/JSON source-provenance parity, main-comparison scorecard-sourced decision-gate minimums with missing-threshold / non-positive Phase 8 and real-money floor / missing no-BAQ prerequisite fail-fast coverage and changed-threshold rerender coverage, current-evidence generated_at timezone fail-fast coverage, current-evidence scorecard-audit route propagation, current-evidence rebuild-validation contract propagation, missing and weakened rebuild-validation-contract fail-fast coverage, missing source-freshness, missing refresh-action non-evidence-flag fail-fast coverage, weakened refresh-accounting fail-fast coverage, API/403 sidecar action/recheck route preservation, and fail-fast frozen-source / holdout-window guardrails, instead of relying only on nested artifact status and raw check arrays",
        ),
        require(
            payload_map["walk_forward_validation_caution"].get("suite_status") == "pass"
            and int(payload_map["walk_forward_validation_caution"].get("total_checks", 0)) == 15
            and payload_map["walk_forward_validation_caution"].get("valid_evidence_scope") == "train_only_walk_forward_selector_benchmark_only"
            and payload_map["walk_forward_validation_caution"].get("evidence_boundary", {}).get("valid_evidence_scope") == "train_only_walk_forward_selector_benchmark_only"
            and "historical train-only selector benchmark" in row_map["walk_forward_validation_caution"]["current_read"]
            and "valid_evidence_scope=train_only_walk_forward_selector_benchmark_only" in row_map["walk_forward_validation_caution"]["current_read"]
            and "+22.46% result is useful evaluation context" in row_map["walk_forward_validation_caution"]["current_read"]
            and "previously mined candidate universe" in row_map["walk_forward_validation_caution"]["current_read"]
            and "fixed Phase 7 / Phase 8 rows are replay context rather than extra train-only validation" in row_map["walk_forward_validation_caution"]["current_read"]
            and "BEL->BAQ is a failed coverage diagnostic" in row_map["walk_forward_validation_caution"]["current_read"]
            and "not settled paper-trade ROI, promotion readiness, live profitability, bankroll guidance, real-money evidence, or BAQ/BEL aliasing" in row_map["walk_forward_validation_caution"]["current_read"]
            and "current bridge rebuild order is read from current_evidence_summary.json.rebuild_validation_contract as provenance metadata only" in row_map["walk_forward_validation_caution"]["current_read"],
            "walk_forward_caution_keeps_train_only_boundary",
            "direct walk-forward validation caution now participates in the research umbrella and keeps the +22.46% train-only selector result in benchmark context, with candidate-universe, fixed-replay, BAQ diagnostic, unstable-year, no-paper-ROI, no-real-money, and current bridge rebuild-order guardrails visible before the result is over-read",
        ),
        require(
            row_map["walk_forward_validation_caution"].get("child_check_count") == 15
            and isinstance(row_map["walk_forward_validation_caution"].get("child_checks"), list)
            and {check.get("check") for check in row_map["walk_forward_validation_caution"]["child_checks"]} == {
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
            },
            "walk_forward_caution_publishes_structured_child_checks",
            "walk-forward validation caution now has to publish its fifteen explicit structured checks, including missing/weakened current-bridge rebuild-contract no-artifact fixtures, the train-only selector benchmark boundary and raw valid_evidence_scope, candidate-universe limitation, current anchor/companion/shadow posture, fixed replay vs train-only separation, failed BEL->BAQ diagnostic, unstable-year visibility, and generator-preserved caution wording, instead of only being discoverable as a separate leaf validator",
        ),
        require(
            payload_map["frozen_portfolio_eval_caution"].get("suite_status") == "pass"
            and int(payload_map["frozen_portfolio_eval_caution"].get("total_checks", 0)) == 23
            and payload_map["frozen_portfolio_eval_caution"].get("valid_evidence_scope") == "frozen_portfolio_replay_chronological_holdout_only"
            and payload_map["frozen_portfolio_eval_caution"].get("evidence_boundary", {}).get("valid_evidence_scope") == "frozen_portfolio_replay_chronological_holdout_only"
            and "historical frozen replay" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "valid_evidence_scope=frozen_portfolio_replay_chronological_holdout_only" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "not live paper-trade or real-money evidence" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "Phase 7 still beats Phase 8" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "OP_DURABLE_K7 remains the safest current paper anchor" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "CD_CORE_K8 as paper companion" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "OP_REFINED_K7 / Phase 8 remain shadow-watch" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "BAQ is not BEL" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "current top-card quotes must go through the combined operator_status_context/source_freshness/operator_read_gate route before use" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "report/metadata sidecar expose exact source-byte fingerprints" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "without turning hashes into performance evidence" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "rejects malformed or timezone-naive current-evidence generated_at provenance" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "missing operator_read_gate provenance" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "incomplete source_freshness reference provenance" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "missing refresh_action_boundary provenance" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "incomplete refresh_action_boundary command/read/Boolean evidence flags" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "machine-readable evidence_boundary_metadata" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "current bridge rebuild route" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "weakened wrapper-refresh accounting" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "missing rebuild_validation_contract provenance" in row_map["frozen_portfolio_eval_caution"]["current_read"]
            and "rejects weakened rebuild_validation_contract provenance before writing frozen-replay artifacts" in row_map["frozen_portfolio_eval_caution"]["current_read"],
            "frozen_replay_caution_keeps_metadata_boundary",
            "direct frozen-portfolio replay caution now participates in the research umbrella and preserves the historical-replay / no-live-or-real-money boundary, Phase 7-over-Phase 8 posture, OP/CD/Phase 8 roles, BAQ-not-BEL warning, combined current top-card operator-status/source-freshness/operator-read-gate routing, current bridge rebuild routing, generator boundary, current-evidence generated_at plus operator-read-gate/source-freshness reference and refresh-action fail-fast coverage, required refresh-action field coverage, weakened refresh-accounting fail-fast coverage, missing/weakened rebuild-validation-contract fail-fast coverage, metadata-sidecar machine-readable evidence-boundary metadata, and metadata-sidecar source fingerprints as reproducibility metadata only",
        ),
        require(
            payload_map["phase7_report_caution"].get("suite_status") == "pass"
            and int(payload_map["phase7_report_caution"].get("total_checks", 0)) == 12
            and payload_map["phase7_report_caution"].get("valid_evidence_scope") == "legacy_phase7_discovery_context_only"
            and payload_map["phase7_report_caution"].get("evidence_boundary", {}).get("valid_evidence_scope") == "legacy_phase7_discovery_context_only"
            and "valid_evidence_scope=legacy_phase7_discovery_context_only" in row_map["phase7_report_caution"]["current_read"]
            and "Phase 7 remains strongest historical candidate-family context" in row_map["phase7_report_caution"]["current_read"]
            and "OP_DURABLE_K7 stays anchor" in row_map["phase7_report_caution"]["current_read"]
            and "CD_CORE_K8 stays the paper companion" in row_map["phase7_report_caution"]["current_read"]
            and "OP_REFINED_K7 and Phase 8 stay shadow/watch" in row_map["phase7_report_caution"]["current_read"]
            and "dormant BEL is not BAQ" in row_map["phase7_report_caution"]["current_read"]
            and "cost/Kelly/historical profit lines are backtest or paper-accounting metadata only" in row_map["phase7_report_caution"]["current_read"]
            and "not live-profitability, promotion, bankroll, or real-money evidence" in row_map["phase7_report_caution"]["current_read"]
            and "current bridge rebuild order is read from current_evidence_summary.json.rebuild_validation_contract as provenance metadata only" in row_map["phase7_report_caution"]["current_read"],
            "phase7_report_caution_keeps_anchor_boundary",
            "direct Phase 7 legacy-report caution now participates in the research umbrella, publishes valid_evidence_scope, and keeps the strongest historical candidate-family report behind the current scorecard/paper-observation posture, with OP anchor / CD companion / Phase 8 shadow roles, BAQ-not-BEL, cost/Kelly no-bankroll boundaries, and the current bridge rebuild-order preflight visible before the original historical replay is over-read",
        ),
        require(
            row_map["phase7_report_caution"].get("child_check_count") == 12
            and isinstance(row_map["phase7_report_caution"].get("child_checks"), list)
            and {check.get("check") for check in row_map["phase7_report_caution"]["child_checks"]} == {
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
            },
            "phase7_report_caution_publishes_structured_child_checks",
            "Phase 7 report caution now has to publish its twelve explicit structured checks, including missing/weakened current-bridge rebuild-contract no-artifact fixtures, exact valid_evidence_scope metadata, the OP anchor / CD companion / Phase 8 shadow posture, dormant BEL / no-BAQ boundary, cost/Kelly paper-accounting boundary, paper-only automation guidance, risk-boundary guardrail, and generator-preserved caution wording, instead of only being discoverable as a separate leaf validator",
        ),
        require(
            payload_map["phase8_report_caution"].get("suite_status") == "pass"
            and int(payload_map["phase8_report_caution"].get("total_checks", 0)) == 16
            and "legacy full-sample discovery context, not the deployment guide" in row_map["phase8_report_caution"]["current_read"]
            and "OP_DURABLE_K7 remains the current paper anchor" in row_map["phase8_report_caution"]["current_read"]
            and "Phase 8 stays shadow/watch" in row_map["phase8_report_caution"]["current_read"]
            and "BAQ is not BEL" in row_map["phase8_report_caution"]["current_read"]
            and "historical paper-accounting metadata only" in row_map["phase8_report_caution"]["current_read"]
            and "not real-money placement, sizing, bankroll, stop-loss, or scale-up guidance" in row_map["phase8_report_caution"]["current_read"]
            and "current bridge rebuild order is read from current_evidence_summary.json.rebuild_validation_contract as provenance metadata only" in row_map["phase8_report_caution"]["current_read"],
            "phase8_report_caution_keeps_cost_boundary",
            "direct Phase 8 legacy-report caution now participates in the research umbrella and keeps Phase 8 as legacy discovery / shadow-watch context, with BAQ-not-BEL plus cost/sizing/no-real-money boundaries and the current bridge rebuild-order preflight visible before the original full-sample headline is over-read",
        ),
        require(
            row_map["phase8_report_caution"].get("child_check_count") == 16
            and isinstance(row_map["phase8_report_caution"].get("child_checks"), list)
            and {check.get("check") for check in row_map["phase8_report_caution"]["child_checks"]} == {
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
            },
            "phase8_report_caution_publishes_structured_child_checks",
            "Phase 8 report caution now has to publish its sixteen explicit structured checks, including missing/weakened current-bridge rebuild-contract no-artifact fixtures, the cost/sizing paper-accounting boundary, and legacy-demotion guardrails, instead of only being discoverable as a separate leaf validator",
        ),
        require(
            payload_map["backtest_report_caution"].get("suite_status") == "pass"
            and int(payload_map["backtest_report_caution"].get("total_checks", 0)) == 10
            and row_map["backtest_report_caution"].get("child_check_count") == 10
            and "legacy large-sample negative baseline" in row_map["backtest_report_caution"]["current_read"]
            and "generic odds-only ML families" in row_map["backtest_report_caution"]["current_read"]
            and "does not override the scorecard, main comparison, current-evidence bridge, OP_DURABLE_K7 anchor, CD_CORE_K8 paper companion, or the OP/CD paper-observation route" in row_map["backtest_report_caution"]["current_read"]
            and "valid_evidence_scope=legacy_broad_backtest_negative_baseline_context_only" in row_map["backtest_report_caution"]["current_read"]
            and "full-data XGBoost retrain artifacts stay model-fit reproducibility context only" in row_map["backtest_report_caution"]["current_read"]
            and "BAQ is not BEL" in row_map["backtest_report_caution"]["current_read"]
            and "not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in row_map["backtest_report_caution"]["current_read"]
            and isinstance(payload_map["backtest_report_caution"].get("evidence_boundary"), dict)
            and payload_map["backtest_report_caution"]["evidence_boundary"].get("artifact_role") == "legacy broad-backtest caution validator"
            and payload_map["backtest_report_caution"].get("valid_evidence_scope") == "legacy_broad_backtest_negative_baseline_context_only"
            and payload_map["backtest_report_caution"]["evidence_boundary"].get("valid_evidence_scope") == "legacy_broad_backtest_negative_baseline_context_only"
            and payload_map["backtest_report_caution"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["backtest_report_caution"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["backtest_report_caution"]["evidence_boundary"].get("no_baq_as_bel") is True
            and isinstance(row_map["backtest_report_caution"].get("child_checks"), list)
            and {check.get("check") for check in row_map["backtest_report_caution"]["child_checks"]} == {
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
            },
            "backtest_report_caution_publishes_structured_child_checks",
            "legacy broad-backtest caution now participates in the frozen-evidence chain and has to publish ten structured checks, including current-bridge rebuild-contract no-artifact fixtures, generator-preserved current-evidence boundary wording, the raw valid_evidence_scope line, the negative broad-baseline read, odds-only XGBoost parked status, full-data retrain routing, and no-BAQ-as-BEL boundary, instead of only being discoverable as a standalone leaf validator",
        ),
        require(
            row_map["frozen_portfolio_eval_caution"].get("child_check_count") == 23
            and isinstance(row_map["frozen_portfolio_eval_caution"].get("child_checks"), list)
            and {check.get("check") for check in row_map["frozen_portfolio_eval_caution"]["child_checks"]} == {
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
            },
            "frozen_replay_caution_publishes_structured_child_checks",
            "frozen-portfolio replay caution now has to publish its twenty-three explicit structured checks, including the raw valid_evidence_scope contract, boundary-date source precedence, malformed current-evidence generated_at fail-fast fixture, missing operator-read-gate fixture, missing source-freshness reference fail-fast fixture, missing refresh-action boundary, missing refresh-action no-real-money flag, weakened refresh-accounting fail-fast fixture, missing/weakened rebuild-validation-contract fail-fast fixtures, metadata sidecar machine-readable evidence-boundary contract, source-fingerprint contract, and generator-boundary protection, instead of only being discoverable as a separate leaf validator",
        ),
        require(
            row_map["forward_evidence_scorecard"].get("child_check_count") == 33
            and row_map["forward_evidence_scorecard"].get("child_scratch", {}).get("tmp_parent_is_project_local") is True
            and row_map["forward_evidence_scorecard"].get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and isinstance(row_map["forward_evidence_scorecard"].get("child_checks"), list)
            and {check.get("check") for check in row_map["forward_evidence_scorecard"]["child_checks"]} == {
                "anchor_row",
                "paper_vs_watch_guardrail",
                "tier_first_ranking_contract",
                "year_split_columns",
                "deployment_context_columns",
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
                "decision_change_gates",
                "decision_gate_minimums_json_present",
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
            },
            "scorecard_publishes_structured_child_checks",
            "forward-evidence scorecard now has to publish its thirty-three explicit structured checks, including text, CSV source-scope / non-live-evidence disclosure, direct valid_evidence_scope metadata, CSV bootstrap-CI source-note columns, CSV/JSON bootstrap-CI source parity, JSON machine-readable evidence boundary, generated-at timezone-label provenance, tier-first ranking contract, bootstrap-CI source notes plus report fingerprints, exact Phase 7 and separate Phase 8 bootstrap-CI report-text fail-fast coverage, the PHASE7 report paper-only risk boundary, the PHASE8 report shadow-only cost boundary, decision-change gates, machine-readable decision-gate minimums, deployment-context columns, dormant-BEL current-paper wording, pinned rerender CLI coverage, no-timezone generated-at CLI fail-fast coverage, project-local CLI scratch-root coverage, top-level scratch metadata, and the newer frozen-source fail-fast guards, instead of only a summary string plus raw check array",
        ),
        require(
            "Phase7=PAPER NOW" in row_map["compare_main_approaches"]["current_read"]
            and "Phase8=SHADOW ONLY" in row_map["compare_main_approaches"]["current_read"]
            and "one-screen read routes the primary paper-basket core, closest OP challenger, Harville benchmark-only lane, odds-only XGBoost research-only lane, settlement-audit non-evidence boundary, and BEL-not-BAQ caution before the detailed tables" in row_map["compare_main_approaches"]["current_read"]
            and "method-family action summary tells Cole to spend operational energy on settled selective paper observations first while Harville and current odds-only XGBoost stay comparison controls unless their evidence class changes" in row_map["compare_main_approaches"]["current_read"]
            and "method-family evidence-debt checklist now names the missing evidence class, invalid shortcuts, and next honest action for the selective OP/CD path, Harville, and current odds-only XGBoost" in row_map["compare_main_approaches"]["current_read"]
            and "scorecard ranking-contract inheritance keeps deployment posture tier-first so OP_REFINED_K7's hotter raw score cannot become an automatic promotion cue" in row_map["compare_main_approaches"]["current_read"]
            and "source provenance table fingerprints the exact comparison input bytes, matches the JSON sidecar source_files map, and proves row-identical source-byte drift changes provenance only, without treating those hashes as performance evidence" in row_map["compare_main_approaches"]["current_read"]
            and "current operator-boundary snapshot carries the combined operator_status_context/source_freshness/operator_read_gate route, the current recommendation-state, source-published settlement-queue state/context plus by-rule detail, API/403 sidecar action/recheck route when present, source-freshness reference date/timezone/comparison-source fields, wrapper-refresh non-evidence boundary, scorecard-audit route, and rebuild-validation contract from current_evidence_summary.json as routing metadata only" in row_map["compare_main_approaches"]["current_read"]
            and "machine-readable evidence_boundary metadata now keeps the main comparison bundle separate from live paper ledgers, scanner output, settled ROI, live profitability, promotion readiness, real-money evidence, OP_REFINED_K7 promotion, odds-only XGBoost reopening, Harville live treatment, and BAQ/BEL substitution" in row_map["compare_main_approaches"]["current_read"]
            and "Phase 8 shadow triage still treats OP_REFINED_K7 as the closest challenger while KEE_K9, SA_K9, and DMR_FALL_K7 remain observation-only pockets" in row_map["compare_main_approaches"]["current_read"]
            and "decision-change gates pin OP_REFINED_K7 promotion review, stricter OP_DURABLE_K7 anchor displacement, Harville live reconsideration, current odds-only XGBoost reopening, BEL/BAQ substitution, and real-money scaling behind explicit forward-observation/evidence-class thresholds" in row_map["compare_main_approaches"]["current_read"]
            and "machine-readable decision-gate minimums keep anchor_displacement=30 same-candidate rows, phase8_promotion_review=20 shadow rows, and real_money_discussion=100 total settled rows named separately" in row_map["compare_main_approaches"]["current_read"]
            and "those named anchor_displacement=30, phase8_promotion_review=20, and real_money_discussion=100 thresholds are source-matched against forward_evidence_scorecard.json and now loaded directly from its decision_gate_minimums with fail-fast missing-threshold, non-positive Phase 8 / real-money floor, and missing no-BAQ prerequisite coverage plus changed-threshold fixture coverage" in row_map["compare_main_approaches"]["current_read"]
            and "holdout OP switch choices 2024=OP_REFINED_K7, 2025=OP_REFINED_K7" in row_map["compare_main_approaches"]["current_read"]
            and "saved CSV, saved markdown, saved JSON sidecar, and real CLI stdout stay pinned to the same main-comparison render" in row_map["compare_main_approaches"]["current_read"]
            and "custom method-family source paths rerender hierarchy labels and provenance without changing ranked rows" in row_map["compare_main_approaches"]["current_read"]
            and "project-local CLI scratch-root metadata stays published for comparison rerenders" in row_map["compare_main_approaches"]["current_read"],
            "comparison_layer_keeps_phase_and_switch_guardrails",
            "comparison rollup still keeps Phase 7 above Phase 8 and preserves the train-only switch as a benchmark read instead of a live override, with saved CSV/markdown/JSON sidecar and CLI reproducibility surfaced directly",
        ),
        require(
            row_map["compare_main_approaches"].get("child_check_count") == 65
            and isinstance(row_map["compare_main_approaches"].get("child_checks"), list)
            and {check.get("check") for check in row_map["compare_main_approaches"]["child_checks"]} == {
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
                "bad_current_evidence_generated_at_fails_fast",
                "missing_current_evidence_rebuild_validation_contract_fails_fast",
                "weakened_current_evidence_rebuild_validation_contract_fails_fast",
                "missing_current_evidence_source_freshness_fails_fast",
                "missing_current_evidence_operator_read_gate_fails_fast",
                "missing_current_evidence_refresh_action_boundary_field_fails_fast",
                "false_current_evidence_refresh_accounting_fails_fast",
                "scorecard_ranking_contract_inherited",
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
                "source_byte_drift_updates_provenance_only",
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
                "custom_method_family_source_paths_rerender_dynamically",
                "missing_scorecard_row_fails_fast",
                "missing_scorecard_gate_minimum_fails_fast",
                "nonpositive_phase8_scorecard_gate_minimum_fails_fast",
                "nonpositive_real_money_scorecard_gate_minimum_fails_fast",
                "missing_scorecard_no_baq_prerequisite_fails_fast",
                "missing_op_switch_candidate_fails_fast",
            },
            "comparison_layer_publishes_structured_child_checks",
            "compare-main-approaches now has to publish its sixty-five explicit structured checks, including the matched JSON sidecar, machine-readable method-family evidence-debt checklist, current-evidence reference-date/timezone source-freshness fields, timezone-aware copied current-evidence generated_at provenance, current-evidence scorecard-audit route propagation, current-evidence rebuild-validation contract propagation, missing and weakened rebuild-validation-contract fail-fast coverage, missing source-freshness fail-fast coverage, missing operator_read_gate fail-fast coverage, missing refresh-action non-evidence-flag fail-fast coverage, weakened refresh-accounting fail-fast coverage, wrapper-refresh non-evidence boundary, machine-readable evidence boundary, machine-readable decision-gate minimums loaded directly from the scorecard JSON, inherited scorecard ranking-contract semantics, one-screen read, method-family action summary, method-family evidence-debt checklist, custom method-family source-path rerender coverage, project-local CLI scratch-root coverage plus top-level scratch metadata, source-provenance markdown/JSON parity plus row-identical source-byte drift coverage, scorecard-driven ladder/triage contract, decision-change gates, plus the frozen-window, source-row, scorecard-gate threshold, non-positive Phase 8 and real-money gate-floor, and no-BAQ prerequisite fail-fast, changed-gate rerender coverage, and bad current-evidence generated_at fail-fast coverage, instead of only a summary string plus raw check array",
        ),
        require(
            payload_map["compare_main_approaches"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and payload_map["compare_main_approaches"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and row_map["compare_main_approaches"].get("child_scratch", {}).get("tmp_parent_is_project_local") is True
            and row_map["compare_main_approaches"].get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and row_map["compare_main_approaches"].get("child_scratch", {}).get("tmp_parent")
            == payload_map["compare_main_approaches"].get("scratch", {}).get("tmp_parent")
            and any(
                check.get("check") == "cli_scratch_metadata_published"
                for check in row_map["compare_main_approaches"].get("child_checks", [])
            ),
            "compare_main_scratch_metadata_propagated",
            "frozen-evidence now requires the compare-main validator's top-level project-local scratch metadata to survive into the parent row inventory as child_scratch, so the one-screen comparison route can be audited without parsing rebuild fields or prose",
        ),
        require(
            "Anchor=OP_DURABLE_K7 KEEP AS ANCHOR" in row_map["frozen_decision_stack"]["current_read"]
            and "benchmark only selector=BENCHMARK ONLY" in row_map["frozen_decision_stack"]["current_read"]
            and "as benchmark context rather than a live override" in row_map["frozen_decision_stack"]["current_read"]
            and "shadow watch keeps BEL dormant and includes OP_REFINED_K7" in row_map["frozen_decision_stack"]["current_read"]
            and "inherited scorecard ranking contract keeps rank tier-first and raw Score non-promotional" in row_map["frozen_decision_stack"]["current_read"]
            and "scorecard audit route=SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json via python3 validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization metadata only" in row_map["frozen_decision_stack"]["current_read"]
            and "current_evidence_summary.json rebuild_validation_contract routes source-byte changes through python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py before quoting CURRENT_EVIDENCE_SUMMARY.* as provenance/rebuild metadata only" in row_map["frozen_decision_stack"]["current_read"]
            and "method-family stack keeps Harville BENCHMARK ONLY and XGBoost RESEARCH ONLY despite only a +4.24% payout-RMSE model-fit gain rather than betting proof" in row_map["frozen_decision_stack"]["current_read"]
            and "saved scorecard JSON/CSV and all four direct decision-card CSV artifacts stay pinned to fresh builder output inside the frozen stack" in row_map["frozen_decision_stack"]["current_read"],
            "frozen_stack_keeps_anchor_benchmark_and_watch_roles",
            "frozen stack rollup still keeps the anchor, benchmark-only selector role, explicit switch-is-benchmark-not-live-override guardrail, BEL dormancy, OP_REFINED_K7 watch status, inherited scorecard ranking-contract semantics, the scorecard-audit route, the current bridge rebuild-order route, the Harville/XGBoost method-scope caution, and direct saved-artifact reproducibility explicit",
        ),
        require(
            row_map["frozen_decision_stack"].get("child_check_count") == 13
            and isinstance(row_map["frozen_decision_stack"].get("child_checks"), list)
            and {check.get("check") for check in row_map["frozen_decision_stack"]["child_checks"]} == {
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
            },
            "frozen_stack_publishes_structured_child_checks",
            "frozen decision stack now has to publish its thirteen explicit structured rollup checks, including inherited scorecard ranking-contract semantics, the current-evidence scorecard-audit route, the current-evidence rebuild-order route, and missing/weakened rebuild-contract no-artifact fixtures, instead of only split artifact/invariant arrays plus a summary string",
        ),
        require(
            "benchmark only=harville_ranked (-24.05% broad ROI on 90004 races)" in row_map["decision_cards_suite"]["current_read"]
            and "research only=xgboost_residual (-24.16% best ML betting ROI despite +4.24% payout-RMSE improvement as model-fit context, not a betting-evidence line, and a -7 pass / -3.93% / -0.0315pp downstream drift)" in row_map["decision_cards_suite"]["current_read"]
            and "replay context rather than extra train-only validation" in row_map["decision_cards_suite"]["current_read"]
            and "valid_evidence_scope=split_aware_cross_family_paper_hierarchy_only" in row_map["decision_cards_suite"]["current_read"]
            and "broader Phase 8 pockets KEE_K9 / SA_K9 / DMR_FALL_K7 stay observation-only rather than entering the near-term promotion queue" in row_map["decision_cards_suite"]["current_read"]
            and "anchor still leads on OP holdout sample" in row_map["decision_cards_suite"]["current_read"]
            and "recurrence context rather than a second profit line" in row_map["decision_cards_suite"]["current_read"]
            and "saved CSV, saved markdown, and real CLI stdout stay pinned to the same OP-family decision render" in row_map["decision_cards_suite"]["current_read"]
            and "saved CSV, saved markdown, and real CLI stdout stay pinned to the same cross-family decision render" in row_map["decision_cards_suite"]["current_read"]
            and "saved CSV, saved markdown, and real CLI stdout stay pinned to the same portfolio decision render" in row_map["decision_cards_suite"]["current_read"]
            and "saved CSV, saved markdown, and real CLI stdout stay pinned to the same method-family decision render" in row_map["decision_cards_suite"]["current_read"]
            and "scorecard ranking contract inherited=tier-first, raw Score non-promotional" in row_map["decision_cards_suite"]["current_read"]
            and "current_evidence_summary.json.scorecard_audit_route points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py as report-synchronization metadata only" in row_map["decision_cards_suite"]["current_read"]
            and "decision gates inherited from compare-main JSON decision_change_gate_minimums" in row_map["decision_cards_suite"]["current_read"]
            and "decision-card layer=report-facing frozen evidence ordering, not new forward proof" in row_map["decision_cards_suite"]["current_read"]
            and "changes in real confidence still require settled paper trades in the operator lane" in row_map["decision_cards_suite"]["current_read"],
            "decision_cards_keep_cross_family_roles",
            "decision-card rollup still keeps Harville as benchmark-only and XGBoost as research-only despite the RMSE improvement story, while surfacing OP-family, cross-family, portfolio, and method-family saved-artifact plus CLI reproducibility, keeping the OP-family fixed-rule secondary read labeled as replay context rather than extra train-only validation, keeping the cross-family valid_evidence_scope and observation-only-pocket split explicit alongside the recurrence-context caution, keeping the XGBoost payout-RMSE gain labeled as model-fit context rather than a betting-evidence line, inheriting scorecard tier-first ranking semantics, OP-family/cross-family/portfolio/method-family scorecard-audit routes, and scorecard-sourced portfolio/method-family decision gates, and saying plainly that the card layer is frozen-evidence ordering rather than new forward proof",
        ),
        require(
            payload_map["decision_cards_suite"].get("suite_status") == "pass"
            and int(payload_map["decision_cards_suite"].get("total_checks", 0)) == 11
            and row_map["decision_cards_suite"].get("child_check_count") == 11
            and isinstance(row_map["decision_cards_suite"].get("child_checks"), list)
            and {check.get("check") for check in row_map["decision_cards_suite"]["child_checks"]} == {
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
            },
            "decision_cards_publishes_structured_child_checks",
            "decision-card suite now has to publish explicit top-level suite_status, explicit total_checks, and its eleven explicit structured rollup checks, including OP/cross-family plus portfolio/method scratch metadata, inherited scorecard ranking-contract semantics, and the direct-source suite-status/total-check metadata contract, instead of only a summary string plus raw check array",
        ),
        require(
            payload_map["scorecard_ranking_contract_audit"].get("suite_status") == "pass"
            and int(payload_map["scorecard_ranking_contract_audit"].get("total_checks", 0)) == 31
            and row_map["scorecard_ranking_contract_audit"].get("child_check_count") == 31
            and payload_map["scorecard_ranking_contract_audit"].get("audited_surface_count") == 41
            and payload_map["scorecard_ranking_contract_audit"].get("evidence_boundary", {}).get("not_promotion_readiness_evidence") is True
            and payload_map["scorecard_ranking_contract_audit"].get("evidence_boundary", {}).get("not_real_money_evidence") is True
            and payload_map["scorecard_ranking_contract_audit"].get("decision_gate_minimums", {}).get("anchor_displacement", {}).get("min_roi_complete_settled_observations") == 30
            and payload_map["scorecard_ranking_contract_audit"].get("decision_gate_minimums", {}).get("phase8_promotion_review", {}).get("min_roi_complete_settled_observations") == 20
            and payload_map["scorecard_ranking_contract_audit"].get("decision_gate_minimums", {}).get("real_money_discussion", {}).get("min_total_settled_observations_with_usable_roi") == 100
            and payload_map["scorecard_ranking_contract_audit"].get("evidence_boundary_metadata", {}).get("ci_only_coverage_does_not_clear_promotion_or_anchor_gates") is True
            and payload_map["scorecard_ranking_contract_audit"].get("evidence_boundary_metadata", {}).get("no_baq_as_bel_prerequisite_preserved") is True
            and payload_map["scorecard_ranking_contract_audit"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and payload_map["scorecard_ranking_contract_audit"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and "scorecard ranking-contract / CI-only audit" in row_map["scorecard_ranking_contract_audit"]["current_read"]
            and "report synchronization only" in row_map["scorecard_ranking_contract_audit"]["current_read"]
            and "not forward evidence or promotion readiness" in row_map["scorecard_ranking_contract_audit"]["current_read"]
            and isinstance(row_map["scorecard_ranking_contract_audit"].get("child_checks"), list)
            and {check.get("check") for check in row_map["scorecard_ranking_contract_audit"]["child_checks"]} == {
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
            },
            "scorecard_ranking_contract_audit_publishes_structured_child_checks",
            "scorecard ranking-contract / CI-only diagnostic audit now participates in the frozen-evidence chain and has to publish thirty-one structured checks across forty-one report-facing text/JSON surfaces, including saved-timestamp rebuild-command parity, generated-at timezone-label provenance, markdown/JSON/disk surface-fingerprint parity, source-matched OP_REFINED CI-only diagnostic coverage, source-matched current-evidence scorecard_audit_route coverage plus structured route diagnostics exported for parent rollups, source-matched rebuild_validation_contract coverage plus diagnostics, bad-route artifact-path, gate-floor snapshot, command/source metadata, non-evidence-flag, route-read phrase, bad-rebuild-contract fail-fast coverage, and real-CLI missing/weakened rebuild-contract no-artifact coverage, scorecard-sourced 30/20/100 gate floors with no-BAQ-as-BEL prerequisite, project-local negative-test scratch isolation, top-level scratch metadata, the direct decision-card validator JSON contracts, and the shareable HTML report CI-only boundary, while preserving the no-forward-evidence / no-promotion-readiness boundary",
        ),
        require(
            payload_map["scorecard_ranking_contract_audit"].get("scorecard_audit_route_diagnostics")
            == row_map["scorecard_ranking_contract_audit"].get("child_scorecard_audit_route_diagnostics")
            and row_map["scorecard_ranking_contract_audit"]["child_scorecard_audit_route_diagnostics"].get(
                "source_row"
            )
            == "current_evidence_summary_json_scorecard_audit_route"
            and row_map["scorecard_ranking_contract_audit"]["child_scorecard_audit_route_diagnostics"].get(
                "route_matches_expected_contract"
            )
            is True
            and row_map["scorecard_ranking_contract_audit"]["child_scorecard_audit_route_diagnostics"].get(
                "route_field_contract_matches_expected"
            )
            is True
            and row_map["scorecard_ranking_contract_audit"]["child_scorecard_audit_route_diagnostics"].get(
                "route_field_contract_mismatches"
            )
            == []
            and row_map["scorecard_ranking_contract_audit"]["child_scorecard_audit_route_diagnostics"].get(
                "route_gate_floor_snapshot_matches_source"
            )
            is True
            and row_map["scorecard_ranking_contract_audit"]["child_scorecard_audit_route_diagnostics"].get(
                "route_validator_command_matches_contract"
            )
            is True
            and row_map["scorecard_ranking_contract_audit"]["child_scorecard_audit_route_diagnostics"].get(
                "route_valid_use_matches_contract"
            )
            is True
            and row_map["scorecard_ranking_contract_audit"]["child_scorecard_audit_route_diagnostics"].get(
                "route_non_evidence_flags_match_contract"
            )
            is True
            and row_map["scorecard_ranking_contract_audit"]["child_scorecard_audit_route_diagnostics"].get(
                "route_read_required_phrases_present"
            )
            is True
            and row_map["scorecard_ranking_contract_audit"]["child_scorecard_audit_route_diagnostics"].get(
                "route_read_missing_phrases"
            )
            == []
            and row_map["scorecard_ranking_contract_audit"]["child_scorecard_audit_route_diagnostics"].get(
                "referenced_route_artifacts_verified_on_disk"
            )
            is True,
            "scorecard_audit_route_diagnostics_propagated",
            "frozen-evidence parent rows now carry the scorecard audit's compact route diagnostics so parent rollups can verify current_evidence_summary.json scorecard_audit_route health without parsing the direct audit row table",
        ),
        require(
            payload_map["scorecard_ranking_contract_audit"].get("rebuild_validation_contract_diagnostics")
            == row_map["scorecard_ranking_contract_audit"].get("child_rebuild_validation_contract_diagnostics")
            and row_map["scorecard_ranking_contract_audit"]["child_rebuild_validation_contract_diagnostics"].get(
                "source_row"
            )
            == "current_evidence_summary_json_rebuild_validation_contract"
            and row_map["scorecard_ranking_contract_audit"]["child_rebuild_validation_contract_diagnostics"].get(
                "expected_upstream_refresh_order_commands"
            )
            == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and row_map["scorecard_ranking_contract_audit"]["child_rebuild_validation_contract_diagnostics"].get(
                "observed_upstream_refresh_order_commands"
            )
            == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and row_map["scorecard_ranking_contract_audit"]["child_rebuild_validation_contract_diagnostics"].get(
                "upstream_refresh_order_commands_match_expected"
            )
            is True
            and row_map["scorecard_ranking_contract_audit"]["child_rebuild_validation_contract_diagnostics"].get(
                "contract_matches_expected"
            )
            is True
            and row_map["scorecard_ranking_contract_audit"]["child_rebuild_validation_contract_diagnostics"].get(
                "contract_field_mismatches"
            )
            == []
            and row_map["scorecard_ranking_contract_audit"]["child_rebuild_validation_contract_diagnostics"].get(
                "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
            )
            is True
            and row_map["scorecard_ranking_contract_audit"]["child_rebuild_validation_contract_diagnostics"].get(
                "required_non_evidence_flags_match_contract"
            )
            is True
            and row_map["scorecard_ranking_contract_audit"]["child_rebuild_validation_contract_diagnostics"].get(
                "upstream_refresh_order_valid_use_matches_contract"
            )
            is True
            and row_map["scorecard_ranking_contract_audit"]["child_rebuild_validation_contract_diagnostics"].get(
                "direct_validation_command_matches_contract"
            )
            is True,
            "scorecard_rebuild_validation_contract_diagnostics_propagated",
            "frozen-evidence parent rows now carry the scorecard audit's compact rebuild-validation diagnostics so parent rollups can verify current_evidence_summary.json rebuild_validation_contract health without parsing the direct audit row table",
        ),
        require(
            payload_map["scorecard_ranking_contract_audit"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and payload_map["scorecard_ranking_contract_audit"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and row_map["scorecard_ranking_contract_audit"].get("child_scratch", {}).get("tmp_parent_is_project_local") is True
            and row_map["scorecard_ranking_contract_audit"].get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and row_map["scorecard_ranking_contract_audit"].get("child_scratch", {}).get("tmp_parent")
            == payload_map["scorecard_ranking_contract_audit"].get("scratch", {}).get("tmp_parent"),
            "scorecard_ranking_contract_audit_scratch_metadata_propagated",
            "the frozen-evidence row inventory now has to carry the scorecard ranking-contract audit's cleared project-local scratch metadata through child_scratch instead of only checking the direct child JSON sidecar",
        ),
        require(
            payload_map["op_anchor_method_comparison"].get("suite_status") == "pass"
            and int(payload_map["op_anchor_method_comparison"].get("total_checks", 0)) == 45
            and isinstance(payload_map["op_anchor_method_comparison"].get("evidence_boundary"), dict)
            and payload_map["op_anchor_method_comparison"]["evidence_boundary"].get("artifact_role") == "OP-anchor method comparison artifact"
            and payload_map["op_anchor_method_comparison"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["op_anchor_method_comparison"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["op_anchor_method_comparison"]["evidence_boundary"].get("not_real_money_evidence") is True
            and payload_map["op_anchor_method_comparison"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["op_anchor_method_comparison"].get("evidence_boundary_text") == op_anchor.oamc.EVIDENCE_BOUNDARY_TEXT
            and payload_map["op_anchor_method_comparison"].get("anchor_review_policy", {}).get("source_path") == "forward_evidence_scorecard.json"
            and payload_map["op_anchor_method_comparison"].get("scorecard_decision_gate_minimums", {}).get("phase8_promotion_review", {}).get("min_roi_complete_settled_observations") == 20
            and payload_map["op_anchor_method_comparison"].get("scorecard_decision_gate_minimums", {}).get("anchor_displacement", {}).get("min_roi_complete_settled_observations") == 30
            and payload_map["op_anchor_method_comparison"].get("scorecard_decision_gate_minimums", {}).get("real_money_discussion", {}).get("min_total_settled_observations_with_usable_roi") == 100
            and payload_map["op_anchor_method_comparison"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and payload_map["op_anchor_method_comparison"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and row_map["op_anchor_method_comparison"].get("child_scratch", {}).get("tmp_parent_is_project_local") is True
            and row_map["op_anchor_method_comparison"].get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and payload_map["ab_downstream_comparison"].get("suite_status") == "pass"
            and int(payload_map["ab_downstream_comparison"].get("total_checks", 0)) == 35
            and payload_map["compare_recommender_scope_paths"].get("suite_status") == "pass"
            and int(payload_map["compare_recommender_scope_paths"].get("total_checks", 0)) == 26,
            "narrow_research_leaf_validators_publish_explicit_suite_status_and_totals",
            "the three narrow research-side comparison validators now publish explicit top-level suite_status plus total_checks metadata, including the newer OP-anchor and downstream A/B fail-fast source guards, inherited scorecard ranking contract with forward_trust secondary-within-tier semantics, OP-anchor and downstream A/B current-paper CD-only operator-boundary snapshots with operator_read_gate and scorecard_audit_route routing, OP-anchor, downstream A/B, and recommender-scope rebuild_validation_contract routing, OP-anchor and downstream A/B timezone-aware current-evidence generated_at provenance, OP-anchor and downstream A/B missing current-evidence operator_read_gate, OP-anchor and downstream A/B missing/weakened rebuild_validation_contract, missing source_freshness, missing source_freshness reference-field, missing refresh-action boundary, plus missing-or-false refresh-action non-evidence-flag and clean-empty refresh-accounting no-write coverage, downstream A/B / recommender-scope project-local CLI scratch-root checks plus top-level scratch metadata, OP-anchor and recommender-scope markdown/JSON source-provenance parity, the recommender-scope scorecard decision-gate read plus missing gate-block / missing-threshold / malformed boolean and non-positive Phase 8 and real-money gate-floor / missing no-BAQ prerequisite / missing-or-weakened rebuild-contract no-write fixtures, and OP-anchor, downstream A/B, plus recommender-scope machine-readable evidence boundaries, instead of relying only on nested artifact status or artifact_status with raw check arrays",
        ),
        require(
            payload_map["ab_downstream_comparison"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and payload_map["ab_downstream_comparison"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and row_map["ab_downstream_comparison"].get("child_scratch", {}).get("tmp_parent_is_project_local") is True
            and row_map["ab_downstream_comparison"].get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and row_map["ab_downstream_comparison"].get("child_scratch", {}).get("tmp_parent")
            == payload_map["ab_downstream_comparison"].get("scratch", {}).get("tmp_parent")
            and payload_map["compare_recommender_scope_paths"].get("scratch", {}).get("tmp_parent_is_project_local") is True
            and payload_map["compare_recommender_scope_paths"].get("scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and row_map["compare_recommender_scope_paths"].get("child_scratch", {}).get("tmp_parent_is_project_local") is True
            and row_map["compare_recommender_scope_paths"].get("child_scratch", {}).get("tmp_parent_cleared_before_fixture_run") is True
            and row_map["compare_recommender_scope_paths"].get("child_scratch", {}).get("tmp_parent")
            == payload_map["compare_recommender_scope_paths"].get("scratch", {}).get("tmp_parent"),
            "narrow_research_leaf_scratch_metadata_propagated",
            "the frozen-evidence row inventory now has to carry the downstream A/B and recommender-scope validators' cleared project-local scratch metadata through child_scratch instead of only checking each direct child JSON sidecar",
        ),
        require(
            "Harville stays benchmark-only" in row_map["op_anchor_method_comparison"]["current_read"]
            and "XGBoost stays research-only" in row_map["op_anchor_method_comparison"]["current_read"]
            and "paper companion=CD_CORE_K8, closest shadow=OP_REFINED_K7" in row_map["op_anchor_method_comparison"]["current_read"]
            and "paper-basket context table now keeps OP_DURABLE_K7, CD_CORE_K8, and OP_REFINED_K7 in separate anchor / companion / shadow lanes before the broader Harville/XGBoost comparison" in row_map["op_anchor_method_comparison"]["current_read"]
            and "paper-observation gates now pin OP_REFINED_K7 promotion, current odds-only XGBoost reopening, BEL/BAQ substitution, and real-money scaling behind forward evidence thresholds" in row_map["op_anchor_method_comparison"]["current_read"]
            and "anchor-review policy now reads forward_evidence_scorecard.json decision_gate_minimums directly and separates the 20-row Phase 8 promotion-review threshold from the stricter 30-row OP anchor-displacement discussion threshold plus the 100-row real-money discussion floor" in row_map["op_anchor_method_comparison"]["current_read"]
            and "scorecard ranking-contract inheritance now pins tier-first rank semantics, forward_trust secondary-within-tier semantics, and raw-score non-deployment semantics so raw OP_REFINED_K7 score does not become an automatic promotion cue" in row_map["op_anchor_method_comparison"]["current_read"]
            and "current paper snapshot now carries the combined operator_status_context/source_freshness/operator_read_gate route plus current_evidence_summary.json source freshness, refresh routing, operator_read_gate" in row_map["op_anchor_method_comparison"]["current_read"]
            and "scorecard_audit_route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization metadata only" in row_map["op_anchor_method_comparison"]["current_read"]
            and "rebuild_validation_contract order ['python3 paper_trade_settlement_audit.py', 'python3 current_evidence_summary.py', 'python3 validate_current_evidence_summary.py']" in row_map["op_anchor_method_comparison"]["current_read"]
            and "settlement-audit -> current-bridge -> bridge-validator provenance before current totals are quoted" in row_map["op_anchor_method_comparison"]["current_read"]
            and "primary ROI-complete rows, 0 OP_DURABLE_K7 settled rows" in row_map["op_anchor_method_comparison"]["current_read"]
            and "CD_CORE_K8 settled rows" in row_map["op_anchor_method_comparison"]["current_read"]
            and "settlement queue state=closed with" in row_map["op_anchor_method_comparison"]["current_read"]
            and "open rows as operator context rather than OP-anchor proof" in row_map["op_anchor_method_comparison"]["current_read"]
            and "copied current-evidence generated_at=" in row_map["op_anchor_method_comparison"]["current_read"]
            and "stays parseable timezone-aware provenance metadata only before the OP-anchor comparison republishes current-paper context" in row_map["op_anchor_method_comparison"]["current_read"]
            and "source-freshness bridge reference=" in row_map["op_anchor_method_comparison"]["current_read"]
            and "(America/New_York) and comparison=generated_reference_date:" in row_map["op_anchor_method_comparison"]["current_read"]
            and "are printed as operator-readiness provenance" in row_map["op_anchor_method_comparison"]["current_read"]
            and "refresh-accounting fields stay fail-closed with wrapper-can-settle-rows=False, wrapper-counts-as-ROI-evidence=False, clean-empty-forward-performance=False" in row_map["op_anchor_method_comparison"]["current_read"]
            and "missing operator_read_gate, missing/weakened rebuild_validation_contract, missing source_freshness, missing source_freshness reference fields, missing refresh-action boundary, missing-or-false refresh-action non-evidence flags, and weakened clean-empty refresh-accounting flags are fixture-tested as no-output-directory/no-artifact CLI paths before current-paper bridge republishing" in row_map["op_anchor_method_comparison"]["current_read"]
            and "stale Phase 7 live-portfolio labels are removed from the OP-anchor markdown/JSON surfaces" in row_map["op_anchor_method_comparison"]["current_read"]
            and "source fingerprints now pin the exact scorecard CSV/JSON / compare-main / method-family / cross-family / downstream A/B / current-evidence input bytes, with the markdown source-provenance table matching the JSON source_fingerprints map, as reproducibility metadata only" in row_map["op_anchor_method_comparison"]["current_read"]
            and "artifact-level machine-readable evidence_boundary plus evidence_boundary_text metadata now says the OP-anchor comparison and current-paper snapshot are posture/reproducibility or operator-routing metadata only" in row_map["op_anchor_method_comparison"]["current_read"]
            and "saved JSON, saved markdown, source provenance, boundary text, and real CLI stdout stay pinned to the same OP-anchor comparison render" in row_map["op_anchor_method_comparison"]["current_read"],
            "op_anchor_comparison_keeps_method_roles_and_companion_order",
            "OP-anchor comparison rollup still keeps the selective paper-companion / shadow-challenger ordering, Harville/XGBoost role split, current CD-only paper-status caveat, current-evidence freshness/timestamp provenance, inherited tier-first plus forward_trust-secondary scorecard-ranking semantics, forward-observation decision gates, and saved-artifact plus CLI reproducibility read explicit",
        ),
        require(
            row_map["op_anchor_method_comparison"].get("child_check_count") == 45
            and isinstance(row_map["op_anchor_method_comparison"].get("child_checks"), list)
            and {check.get("check") for check in row_map["op_anchor_method_comparison"]["child_checks"]} == {
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
            },
            "op_anchor_comparison_publishes_structured_child_checks",
            "OP-anchor comparison now has to publish its forty-five explicit structured checks, including explicit source-path rerender coverage, project-local CLI scratch-root coverage plus top-level scratch metadata, paper-companion ordering, the structured paper-basket / shadow context table, stale live-portfolio label removal, current-paper CD-only operator-boundary snapshot with source-derived settlement-queue state/context plus operator_read_gate, scorecard_audit_route, and rebuild_validation_contract routing, timezone-aware current-evidence generated_at provenance plus missing operator_read_gate, missing/weakened rebuild_validation_contract, missing source_freshness, missing source_freshness reference-field, missing refresh-action boundary, missing-or-false refresh-action non-evidence-flag fail-fast coverage, clean-empty refresh-accounting fail-fast coverage, scorecard ranking-contract inheritance with forward_trust secondary-within-tier fail-fast coverage, scorecard decision_gate_minimums fail-fast coverage, source-byte provenance drift coverage, markdown/JSON source-provenance parity, the machine-readable artifact evidence boundary plus readable boundary-text parity, the separate promotion-review versus anchor-displacement policy guardrail, and the newer fail-fast source guards, instead of only a summary string plus raw check array",
        ),
        require(
            "EV winner pass counts still drift down by 7" in row_map["ab_downstream_comparison"]["current_read"]
            and "-3.93% relative; -0.0315pp of test winners" in row_map["ab_downstream_comparison"]["current_read"]
            and "enriched horse-history XGBoost path remains research-only" in row_map["ab_downstream_comparison"]["current_read"]
            and "saved JSON, saved markdown, cross-family hierarchy source fingerprinting, and custom hierarchy rerendering stay pinned" in row_map["ab_downstream_comparison"]["current_read"]
            and "project-local CLI scratch-root reporting stays pinned" in row_map["ab_downstream_comparison"]["current_read"]
            and "model artifact fingerprints match current disk bytes" in row_map["ab_downstream_comparison"]["current_read"]
            and "current paper snapshot says " in row_map["ab_downstream_comparison"]["current_read"]
            and "wrapper refresh route=./run_daily_portfolio_observation.sh" in row_map["ab_downstream_comparison"]["current_read"]
            and "required_before_right_now_use=" in row_map["ab_downstream_comparison"]["current_read"]
            and "requires the combined operator_status_context/source_freshness/operator_read_gate route before quoting current PAPER_TRADE_NOW instructions from this A/B artifact" in row_map["ab_downstream_comparison"]["current_read"]
            and "operator_read_gate=" in row_map["ab_downstream_comparison"]["current_read"]
            and " via " in row_map["ab_downstream_comparison"]["current_read"]
            and "primary rows are " in row_map["ab_downstream_comparison"]["current_read"]
            and "OP_DURABLE_K7 has 0 ROI-complete row(s), CD_CORE_K8 has" in row_map["ab_downstream_comparison"]["current_read"]
            and "settlement queue state=closed with" in row_map["ab_downstream_comparison"]["current_read"]
            and "open row(s) as operator context rather than OP-anchor proof" in row_map["ab_downstream_comparison"]["current_read"]
            and "scorecard audit route from current_evidence_summary.json.scorecard_audit_route points to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks" in row_map["ab_downstream_comparison"]["current_read"]
            and "rebuild_validation_contract order from current_evidence_summary.json routes source-byte changes through python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py before quoting current totals as provenance metadata only" in row_map["ab_downstream_comparison"]["current_read"]
            and "copied current-evidence generated_at=" in row_map["ab_downstream_comparison"]["current_read"]
            and "stays parseable timezone-aware provenance metadata only before the downstream A/B comparison republishes current-paper context" in row_map["ab_downstream_comparison"]["current_read"]
            and "source-freshness bridge reference=" in row_map["ab_downstream_comparison"]["current_read"]
            and "(America/New_York) and comparison=generated_reference_date:" in row_map["ab_downstream_comparison"]["current_read"]
            and "are printed as operator-readiness provenance" in row_map["ab_downstream_comparison"]["current_read"]
            and "missing operator_read_gate, missing/weakened rebuild_validation_contract, missing source_freshness, missing source_freshness reference fields, missing refresh-action boundary, missing-or-false refresh-action non-evidence flags, and weakened refresh-accounting flags are fixture-tested as no-output-directory/no-artifact CLI paths before current-paper bridge republishing" in row_map["ab_downstream_comparison"]["current_read"]
            and "full CLI JSON/markdown/stdout plus custom CLI source/output-path checks are explicitly skipped because raw rebuild inputs are missing" in row_map["ab_downstream_comparison"]["current_read"],
            "downstream_ab_keeps_negative_betting_read",
            "downstream A/B rollup still treats the RMSE gain as insufficient because the betting pass-through weakens, now with normalized pass-through drift, current CD-only paper-status caveat, scorecard-audit and rebuild-order route publication, timezone-aware current-evidence generated_at provenance, saved-artifact reproducibility, dynamic hierarchy rerendering, project-local scratch-root reporting, and explicit raw-input limitations made visible",
        ),
        require(
            row_map["ab_downstream_comparison"].get("child_check_count") == 35
            and isinstance(row_map["ab_downstream_comparison"].get("child_checks"), list)
            and {check.get("check") for check in row_map["ab_downstream_comparison"]["child_checks"]} == {
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
            },
            "downstream_ab_publishes_structured_child_checks",
            "downstream A/B comparison now has to publish its thirty-five explicit structured checks, including the refresh-current-evidence-only CLI path, the current-paper CD-only operator-boundary snapshot plus combined operator route, operator_read_gate, scorecard_audit_route, and rebuild_validation_contract, timezone-aware current-evidence generated_at provenance plus malformed-timestamp, missing operator_read_gate, missing/weakened rebuild_validation_contract, missing source_freshness, missing source_freshness reference-field, missing refresh-action boundary, missing-or-false refresh-action non-evidence-flag fail-fast coverage, clean-empty refresh-accounting fail-fast coverage, machine-readable evidence-boundary routing, paper-basket companion paper-lane read, cross-family source fingerprinting, current-disk hierarchy/model fingerprint parity, custom hierarchy rerender coverage, project-local CLI scratch-root coverage plus top-level scratch metadata, and the custom CLI source/output-path check with an explicit skip state when raw rebuild inputs are absent, instead of only a summary string plus raw check array",
        ),
        require(
            payload_map["full_data_retrain_artifacts"].get("suite_status") == "pass"
            and int(payload_map["full_data_retrain_artifacts"].get("total_checks", 0)) == 12
            and row_map["full_data_retrain_artifacts"].get("child_check_count") == 12
            and isinstance(payload_map["full_data_retrain_artifacts"].get("evidence_boundary"), dict)
            and payload_map["full_data_retrain_artifacts"]["evidence_boundary"].get("artifact_role") == "full-data XGBoost retrain artifact validator"
            and payload_map["full_data_retrain_artifacts"]["evidence_boundary"].get("not_new_forward_evidence") is True
            and payload_map["full_data_retrain_artifacts"]["evidence_boundary"].get("not_live_paper_trade_ledger") is True
            and payload_map["full_data_retrain_artifacts"]["evidence_boundary"].get("not_current_day_scanner_result") is True
            and payload_map["full_data_retrain_artifacts"]["evidence_boundary"].get("not_settled_roi_evidence") is True
            and payload_map["full_data_retrain_artifacts"]["evidence_boundary"].get("not_live_profitability_evidence") is True
            and payload_map["full_data_retrain_artifacts"]["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and payload_map["full_data_retrain_artifacts"]["evidence_boundary"].get("not_real_money_evidence") is True
            and isinstance(payload_map["full_data_retrain_artifacts"].get("evidence_boundary_metadata"), dict)
            and payload_map["full_data_retrain_artifacts"]["evidence_boundary_metadata"].get("artifact_role") == "full-data XGBoost retrain diagnostic metadata"
            and payload_map["full_data_retrain_artifacts"]["evidence_boundary_metadata"].get("metrics_are_model_fit_diagnostics_only") is True
            and payload_map["full_data_retrain_artifacts"]["evidence_boundary_metadata"].get("not_current_odds_only_xgboost_reopening_evidence") is True
            and payload_map["full_data_retrain_artifacts"]["evidence_boundary_metadata"].get("not_bankroll_guidance") is True
            and payload_map["full_data_retrain_artifacts"]["evidence_boundary_metadata"].get("not_real_money_evidence") is True
            and "ROI-complete settled paper observations" in payload_map["full_data_retrain_artifacts"]["evidence_boundary_metadata"].get("xgboost_reopening_requires", [])
            and payload_map["full_data_retrain_artifacts"].get("current_evidence_rebuild_validation_contract_read", {}).get("upstream_refresh_order_commands") == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and payload_map["full_data_retrain_artifacts"].get("current_evidence_rebuild_validation_contract_read", {}).get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and payload_map["full_data_retrain_artifacts"].get("current_evidence_rebuild_validation_contract_read", {}).get("upstream_refresh_order_is_provenance_metadata_only") is True
            and "large payout-fit metrics while keeping those metrics in model-research context only" in row_map["full_data_retrain_artifacts"]["current_read"]
            and "current_evidence_summary.json.rebuild_validation_contract as provenance/rebuild metadata only" in row_map["full_data_retrain_artifacts"]["current_read"]
            and "XGBoost research-only unless its evidence class changes materially and downstream/paper evidence follows" in row_map["full_data_retrain_artifacts"]["current_read"]
            and "missing or weakened current-evidence rebuild contracts fail before validation artifacts are written" in row_map["full_data_retrain_artifacts"]["current_read"]
            and "evidence_boundary_metadata keeps full-data retrain diagnostics out of XGBoost reopening" in row_map["full_data_retrain_artifacts"]["current_read"]
            and isinstance(row_map["full_data_retrain_artifacts"].get("child_checks"), list)
            and {check.get("check") for check in row_map["full_data_retrain_artifacts"]["child_checks"]} == {
                "current_evidence_missing_rebuild_contract_fails_before_artifacts",
                "current_evidence_weakened_rebuild_contract_fails_before_artifacts",
                "status_research_artifact_boundary",
                "evidence_boundary_present",
                "fit_metrics_not_betting_evidence",
                "deployment_route_points_to_comparison_artifacts",
                "self_validation_route_present",
                "current_evidence_rebuild_contract_route_present",
                "headline_metrics_have_local_caveat",
                "training_command_pinned",
                "prediction_command_caveated",
                "machine_readable_diagnostic_boundary_metadata",
            },
            "full_data_retrain_artifact_guardrail_publishes_structured_child_checks",
            "full-data retrain validation now participates in the frozen-evidence chain and has to publish twelve structured checks plus machine-readable no-new-forward-evidence, current-evidence rebuild-contract, and diagnostic-boundary metadata, keeping full-data RMSE / MAE improvements, exact retrain commands, and diagnostic single-race prediction commands in model-fit reproducibility context rather than paper-trade evidence, XGBoost reopening evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
        ),
        require(
            "selective Phase 7 filter as the honest current paper default" in row_map["compare_recommender_scope_paths"]["current_read"]
            and "allow-all-combos preserved as an explicit research-only counterfactual" in row_map["compare_recommender_scope_paths"]["current_read"]
            and "raise stake and off-scope share" in row_map["compare_recommender_scope_paths"]["current_read"]
            and "evidence_boundary.not_current_paper_scope_change_evidence=true" in row_map["compare_recommender_scope_paths"]["current_read"]
            and "scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite" in row_map["compare_recommender_scope_paths"]["current_read"]
            and "current_evidence_summary.json scorecard_audit_route is republished so copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py as synchronization metadata only" in row_map["compare_recommender_scope_paths"]["current_read"]
            and "current_evidence_summary.json rebuild_validation_contract is republished so source-byte changes route through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py before quoting current totals from this counterfactual surface" in row_map["compare_recommender_scope_paths"]["current_read"]
            and "missing scorecard gate failure is fixture-tested as a no-output-directory/no-artifact CLI path" in row_map["compare_recommender_scope_paths"]["current_read"]
            and "malformed boolean/non-positive scorecard gate floors plus a missing no-BAQ-as-BEL prerequisite" in row_map["compare_recommender_scope_paths"]["current_read"]
            and "including non-positive Phase 8 and real-money scorecard floors" in row_map["compare_recommender_scope_paths"]["current_read"]
            and "missing or weakened current-evidence rebuild contracts are fixture-tested as no-output-directory/no-artifact CLI paths" in row_map["compare_recommender_scope_paths"]["current_read"]
            and "dynamic cross-family hierarchy rerendering" in row_map["compare_recommender_scope_paths"]["current_read"]
            and "project-local CLI scratch-root reporting" in row_map["compare_recommender_scope_paths"]["current_read"]
            and "markdown/JSON/disk source provenance stay pinned to the same scope-comparison render" in row_map["compare_recommender_scope_paths"]["current_read"],
            "scope_guardrail_keeps_paper_default_vs_counterfactual_split",
            "scope-comparison rollup still keeps widened combo scope in the research-only counterfactual lane instead of the current paper default, while making stake/off-scope inflation, scorecard gate floors, the scorecard-audit route, the current-evidence rebuild route, saved-output-directory/artifact, dynamic cross-family hierarchy, project-local scratch-root reporting, and CLI reproducibility explicit",
        ),
        require(
            row_map["compare_recommender_scope_paths"].get("child_check_count") == 26
            and isinstance(row_map["compare_recommender_scope_paths"].get("child_checks"), list)
            and {check.get("check") for check in row_map["compare_recommender_scope_paths"]["child_checks"]} == {
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
            },
            "scope_guardrail_publishes_structured_child_checks",
            "scope-comparison validator now has to publish its twenty-six explicit structured checks, including the paper-companion paper-lane read, scorecard-sourced 30/20/100 gate read plus no-BAQ-as-BEL prerequisite, scorecard-audit route publication, current-evidence rebuild-contract publication, machine-readable scope evidence boundary, missing scorecard gate-block, missing-threshold, malformed boolean and non-positive Phase 8 plus real-money gate-floor, missing no-BAQ-as-BEL, and missing/weakened rebuild-contract no-output-directory/no-write fixtures, project-local CLI scratch-root coverage plus top-level scratch metadata, and markdown/JSON/disk source-provenance parity, instead of only a summary string plus raw check array",
        ),
    ]

    suite_read = build_suite_read(payload_map)
    checks.append(
        require(
            "frozen-evidence chain layer: research-side evidence-alignment check, not new forward evidence by itself" in suite_read
            and "stronger forward confidence still requires settled paper trades and other real forward results" in suite_read,
            "frozen_chain_explicitly_stays_alignment_not_new_evidence",
            "frozen-evidence chain summary now says plainly that a green research-side sweep is alignment checking rather than new forward evidence",
        )
    )
    checks.append(
        require(
            EVIDENCE_BOUNDARY.get("artifact_role") == "research-side frozen-evidence validator rollup"
            and EVIDENCE_BOUNDARY.get("not_new_forward_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_live_paper_trade_ledger") is True
            and EVIDENCE_BOUNDARY.get("not_current_day_scanner_result") is True
            and EVIDENCE_BOUNDARY.get("not_settled_roi_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_live_profitability_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_real_money_evidence") is True
            and EVIDENCE_BOUNDARY.get("not_promotion_readiness_evidence") is True
            and EVIDENCE_BOUNDARY.get("hashes_are_reproducibility_metadata_only") is True
            and "ROI-complete settled paper rows" in EVIDENCE_BOUNDARY.get("stronger_forward_confidence_requires", [])
            and "do not treat legacy broad-backtest baselines as current deployment guidance" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "do not promote OP_REFINED_K7 or Phase 8 from validation cleanliness" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "do not reopen current odds-only XGBoost from validation cleanliness" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "do not treat full-data XGBoost retrain RMSE / MAE improvements as paper-trade evidence" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "do not substitute BAQ for BEL" in EVIDENCE_BOUNDARY.get("non_goals", [])
            and "machine-readable evidence_boundary metadata" in suite_read,
            "frozen_chain_json_publishes_machine_readable_evidence_boundary",
            "frozen-evidence parent JSON now publishes a machine-readable evidence_boundary block that keeps research validator passes, child hashes, frozen replay alignment, OP_REFINED_K7 / Phase 8 promotion, current odds-only XGBoost reopening, full-data retrain RMSE / MAE diagnostics, Harville benchmark-only reads, BAQ/BEL substitution, live profitability, promotion readiness, and real-money evidence in separate evidence lanes",
        )
    )

    payload = {
        "suite_status": "pass",
        "validators_run": len(rows),
        "total_checks": total_checks,
        "rows": rows,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "child_artifact_fingerprints": {
            row["name"]: {
                "path": row["json_path"],
                "bytes": row["child_json_bytes"],
                "sha256": row["child_json_sha256"],
            }
            for row in rows
        },
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
        "# Frozen Evidence Chain Validation",
        "",
        "This report runs the broader report-facing evidence validators together, from the forward-evidence scorecard and main comparison harness through the direct walk-forward benchmark caution, direct frozen-replay caution/metadata check, direct Phase 7 and Phase 8 legacy-report cautions, frozen decision stack, direct decision-card layer, and scorecard ranking-contract audit, plus the narrow comparison artifacts that defend the OP anchor, the downstream enriched-horse-history XGBoost research-only read, the full-data XGBoost retrain diagnostic boundary, and the selective-scope guardrail.",
        "",
        f"- Validators run: {len(rows)}",
        f"- Total checks: {total_checks}",
        "- Overall result: PASS",
        "",
        "## Validator Summary",
        "",
        "| Validator | Checks | Result | Source | Source bytes | Source sha256 |",
        "|---|---:|---|---|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['label']} | {row['check_count']} | {row['result']} | `{row['json_path']}` | {row['child_json_bytes']} | `{row['child_json_sha256']}` |"
        )

    lines.extend(
        [
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
            "- Not new forward evidence; not a live paper-trade ledger; not current-day scanner output; not settled-ROI evidence; not live-profitability evidence; not real-money evidence; not promotion-readiness evidence.",
            "- Child hashes are reproducibility metadata only.",
            f"- Stronger forward confidence still requires: {', '.join(EVIDENCE_BOUNDARY['stronger_forward_confidence_requires'])}.",
            f"- Non-goals: {', '.join(EVIDENCE_BOUNDARY['non_goals'])}.",
            "",
            "## Child Validator Reads",
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
            "The full report-facing evidence chain is currently aligned:",
            "",
            f"- scorecard layer: {next(row['current_read'] for row in rows if row['name'] == 'forward_evidence_scorecard')}",
            f"- comparison layer: {next(row['current_read'] for row in rows if row['name'] == 'compare_main_approaches')}",
            f"- walk-forward caution: {next(row['current_read'] for row in rows if row['name'] == 'walk_forward_validation_caution')}",
            f"- frozen replay caution: {next(row['current_read'] for row in rows if row['name'] == 'frozen_portfolio_eval_caution')}",
            f"- Phase 7 report caution: {next(row['current_read'] for row in rows if row['name'] == 'phase7_report_caution')}",
            f"- Phase 8 report caution: {next(row['current_read'] for row in rows if row['name'] == 'phase8_report_caution')}",
            f"- legacy broad-backtest caution: {next(row['current_read'] for row in rows if row['name'] == 'backtest_report_caution')}",
            f"- frozen stack: {next(row['current_read'] for row in rows if row['name'] == 'frozen_decision_stack')}",
            f"- decision-card layer: {next(row['current_read'] for row in rows if row['name'] == 'decision_cards_suite')}",
            f"- scorecard ranking-contract audit: {next(row['current_read'] for row in rows if row['name'] == 'scorecard_ranking_contract_audit')}",
            f"- OP-anchor framing: {next(row['current_read'] for row in rows if row['name'] == 'op_anchor_method_comparison')}",
            f"- downstream XGBoost guardrail: {next(row['current_read'] for row in rows if row['name'] == 'ab_downstream_comparison')}",
            f"- full-data XGBoost retrain guardrail: {next(row['current_read'] for row in rows if row['name'] == 'full_data_retrain_artifacts')}",
            f"- selective-scope guardrail: {next(row['current_read'] for row in rows if row['name'] == 'compare_recommender_scope_paths')}",
            "",
            "If this suite stays green after edits, Cole can be more confident the main evidence chain still matches the current report-safe deployment logic, including the direct walk-forward benchmark caution, the direct frozen-replay caution/metadata boundary, the direct Phase 7/Phase 8 legacy/cost-boundary cautions, the legacy broad-backtest negative-baseline caution, the scorecard ranking-contract audit, and the narrow comparison artifacts that defend why OP stays anchor, why the downstream enriched-horse-history XGBoost correction and full-data retrain stay research/model-fit only, and why widened combo scope stays a counterfactual rather than a daily operating default.",
            "That green read is an evidence-alignment check, not new forward evidence by itself; genuinely stronger forward confidence still has to come from settled paper trades and other real forward results.",
            "",
            "## Child Validation JSON Fingerprints",
            "",
            "These hashes identify the exact child validation JSON artifacts summarized by this parent sweep. They are reproducibility metadata only, not settled ROI, live profitability, promotion readiness, or real-money evidence.",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- `{row['json_path']}` — {row['child_json_bytes']} bytes, sha256={row['child_json_sha256']}")

    lines.extend(
        [
            "",
            "## Sources",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- `{row['json_path']}`")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
