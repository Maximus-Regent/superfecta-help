#!/usr/bin/env python3
"""
Fixture-driven validation for paper_trade_pipeline.py.

Purpose:
- pin the pipeline orchestrator directly at the source layer
- keep scanner-status and observation-result classification reproducible
- prove the real CLI still completes cleanly across skip-scan, scanner-failure, empty/unreadable/invalid-shape scanner-status, partial-cache, and no-bet states
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import paper_trade_pipeline as pipeline_source

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "paper_trade_pipeline.py"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "paper_trade_pipeline_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_pipeline"
REPORT_MD = OUT_DIR / "paper_trade_pipeline_validation.md"
REPORT_JSON = OUT_DIR / "paper_trade_pipeline_validation.json"
REBUILD_COMMAND = "python3 validate_paper_trade_pipeline.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
VALIDATOR_EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade pipeline validator report",
    "valid_evidence_scope": pipeline_source.PIPELINE_VALID_SCOPE,
    "valid_use": "source-layer scan/recommend/log workflow-status reproducibility audit",
    "pipeline_validator_passes_are_workflow_metadata_only": True,
    "not_new_forward_evidence": True,
    "not_current_day_scanner_result": True,
    "not_live_paper_trade_ledger": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_anchor_change_evidence": True,
    "not_phase8_promotion_evidence": True,
    "not_odds_only_xgboost_reopening_evidence": True,
    "baq_as_bel_substitution_allowed": False,
}


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def signal_hit(
    scan_ts: str,
    rule_id: str,
    race_id: str,
    favorite_program: str,
    *,
    track: str = "OP",
    card_name: str = "Oaklawn Park",
    race_number: str = "7",
) -> dict[str, Any]:
    return {
        "scan_ts": scan_ts,
        "rule_id": rule_id,
        "track": track,
        "card_name": card_name,
        "race_number": race_number,
        "race_id": race_id,
        "surface": "D",
        "condition": "FAST",
        "field_size": 12,
        "favorite_program": favorite_program,
        "favorite_name": "Fixture Favorite",
        "favorite_prob": 0.38,
        "second_prob": 0.23,
        "prob_gap": 0.15,
        "k": 7,
        "base_stake": 1.0,
        "estimated_cost": 24.0,
        "underneath_programs": ["2", "3", "5"],
        "ticket_structure": "1/WIN with 3 underneath",
    }


HIT_OP = signal_hit("2026-04-20T11:00:00", "OP_DURABLE_K7", "OP-2026-04-20-R7", "1")
HIT_CD = signal_hit(
    "2026-04-20T11:05:00",
    "CD_CORE_K8",
    "CD-2026-04-20-R8",
    "4",
    track="CD",
    card_name="Churchill Downs",
    race_number="8",
)

RECOMMENDATION_BET = {
    "signal_key": f"{HIT_OP['scan_ts']}|{HIT_OP['rule_id']}|{HIT_OP['race_id']}|{HIT_OP['favorite_program']}",
    "decision": "BET",
    "rule_id": HIT_OP["rule_id"],
    "track": HIT_OP["track"],
    "card_name": HIT_OP["card_name"],
    "race_number": HIT_OP["race_number"],
    "race_id": HIT_OP["race_id"],
}

RECOMMENDATION_NO_BET = {
    "signal_key": f"{HIT_OP['scan_ts']}|{HIT_OP['rule_id']}|{HIT_OP['race_id']}|{HIT_OP['favorite_program']}",
    "decision": "NO BET",
    "rule_id": HIT_OP["rule_id"],
    "track": HIT_OP["track"],
    "card_name": HIT_OP["card_name"],
    "race_number": HIT_OP["race_number"],
    "race_id": HIT_OP["race_id"],
}


CASES: list[dict[str, Any]] = [
    {
        "name": "case_skip_scan_empty_reuse",
        "scenario": "skip-scan empty inputs still classify as a clean empty run instead of a failure",
        "skip_scan": True,
        "initial_scan_hits": [],
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "skipped_scan",
            "scanner_result": "reused_input_empty",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "clean_empty_run",
            "observation_scope": "clean_observation",
            "observation_reason": "reused_input_empty",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "Recommendation summary:"],
    },
    {
        "name": "case_skip_scan_missing_reuse",
        "scenario": "skip-scan with a missing reused scan file writes an explicit missing-output fallback and does not treat the fallback [] as a clean reused empty scan",
        "skip_scan": True,
        "initial_scan_hits": None,
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "missing_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "missing_or_empty_scan_output",
            "scan_input_state_before_empty_fallback": "missing",
            "scan_input_empty_fallback_value": "[]",
            "scanner_status_state": "missing",
            "scanner_result": "missing_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "missing_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "No scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_missing_reuse_with_sidecar",
        "scenario": "skip-scan with a missing reused scan file and a readable scanner-status sidecar still keeps missing scan output as the controlling result",
        "skip_scan": True,
        "initial_scan_hits": None,
        "initial_scanner_status": {
            "result": "hits_found",
            "partial_cache": False,
            "raw_hit_count": 2,
            "emitted_hit_count": 2,
            "missing_race_detail_cache_skips": 0,
        },
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "missing_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "missing_or_empty_scan_output",
            "scan_input_state_before_empty_fallback": "missing",
            "scan_input_empty_fallback_value": "[]",
            "scanner_status_state": "readable",
            "scanner_status_reported_result": "hits_found",
            "scanner_result": "missing_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "missing_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "No scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_missing_reuse_with_empty_sidecar",
        "scenario": "skip-scan with a missing reused scan file and an empty scanner-status sidecar still keeps missing scan output as the controlling result",
        "skip_scan": True,
        "initial_scan_hits": None,
        "initial_scanner_status_raw": "",
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "missing_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "missing_or_empty_scan_output",
            "scan_input_state_before_empty_fallback": "missing",
            "scan_input_empty_fallback_value": "[]",
            "scanner_status_state": "empty",
            "scanner_result": "missing_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "missing_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "No scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_missing_reuse_with_unreadable_sidecar",
        "scenario": "skip-scan with a missing reused scan file and an unreadable scanner-status sidecar still keeps missing scan output as the controlling result",
        "skip_scan": True,
        "initial_scan_hits": None,
        "initial_scanner_status_raw": "{not valid json",
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "missing_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "missing_or_empty_scan_output",
            "scan_input_state_before_empty_fallback": "missing",
            "scan_input_empty_fallback_value": "[]",
            "scanner_status_state": "unreadable",
            "scanner_result": "missing_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "missing_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "No scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_zero_byte_reuse",
        "scenario": "skip-scan with a zero-byte reused scan file writes an explicit missing-output fallback and does not treat the fallback [] as a clean reused empty scan",
        "skip_scan": True,
        "initial_scan_hits": None,
        "initial_scan_raw": "",
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "missing_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "missing_or_empty_scan_output",
            "scan_input_state_before_empty_fallback": "empty",
            "scan_input_empty_fallback_value": "[]",
            "scanner_status_state": "missing",
            "scanner_result": "missing_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "missing_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "No scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_zero_byte_reuse_with_sidecar",
        "scenario": "skip-scan with a zero-byte reused scan file and a readable scanner-status sidecar still keeps missing scan output as the controlling result",
        "skip_scan": True,
        "initial_scan_hits": None,
        "initial_scan_raw": "",
        "initial_scanner_status": {
            "result": "hits_found",
            "partial_cache": False,
            "raw_hit_count": 2,
            "emitted_hit_count": 2,
            "missing_race_detail_cache_skips": 0,
        },
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "missing_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "missing_or_empty_scan_output",
            "scan_input_state_before_empty_fallback": "empty",
            "scan_input_empty_fallback_value": "[]",
            "scanner_status_state": "readable",
            "scanner_status_reported_result": "hits_found",
            "scanner_result": "missing_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "missing_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "No scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_zero_byte_reuse_with_empty_sidecar",
        "scenario": "skip-scan with a zero-byte reused scan file and an empty scanner-status sidecar still keeps missing scan output as the controlling result",
        "skip_scan": True,
        "initial_scan_hits": None,
        "initial_scan_raw": "",
        "initial_scanner_status_raw": "",
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "missing_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "missing_or_empty_scan_output",
            "scan_input_state_before_empty_fallback": "empty",
            "scan_input_empty_fallback_value": "[]",
            "scanner_status_state": "empty",
            "scanner_result": "missing_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "missing_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "No scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_zero_byte_reuse_with_unreadable_sidecar",
        "scenario": "skip-scan with a zero-byte reused scan file and an unreadable scanner-status sidecar still keeps missing scan output as the controlling result",
        "skip_scan": True,
        "initial_scan_hits": None,
        "initial_scan_raw": "",
        "initial_scanner_status_raw": "{not valid json",
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "missing_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "missing_or_empty_scan_output",
            "scan_input_state_before_empty_fallback": "empty",
            "scan_input_empty_fallback_value": "[]",
            "scanner_status_state": "unreadable",
            "scanner_result": "missing_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "missing_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "No scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_malformed_reuse",
        "scenario": "skip-scan with a malformed reused scan file writes an explicit invalid-output fallback and does not continue through the recommender with corrupt scanner JSON",
        "skip_scan": True,
        "initial_scan_hits": None,
        "initial_scan_raw": "{not valid json",
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "invalid_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "invalid_scan_output",
            "scan_input_state_before_empty_fallback": "unreadable",
            "scan_input_empty_fallback_value": "[]",
            "scanner_status_state": "missing",
            "scanner_result": "invalid_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "invalid_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "Invalid scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_malformed_reuse_with_sidecar",
        "scenario": "skip-scan with a malformed reused scan file and a readable scanner-status sidecar still keeps invalid scan output as the controlling result",
        "skip_scan": True,
        "initial_scan_hits": None,
        "initial_scan_raw": "{not valid json",
        "initial_scanner_status": {
            "result": "hits_found",
            "partial_cache": False,
            "raw_hit_count": 3,
            "emitted_hit_count": 3,
            "missing_race_detail_cache_skips": 0,
        },
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "invalid_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "invalid_scan_output",
            "scan_input_state_before_empty_fallback": "unreadable",
            "scan_input_empty_fallback_value": "[]",
            "scanner_status_state": "readable",
            "scanner_status_reported_result": "hits_found",
            "scanner_result": "invalid_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "invalid_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "Invalid scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_malformed_reuse_with_empty_sidecar",
        "scenario": "skip-scan with a malformed reused scan file and an empty scanner-status sidecar still keeps invalid scan output as the controlling result",
        "skip_scan": True,
        "initial_scan_hits": None,
        "initial_scan_raw": "{not valid json",
        "initial_scanner_status_raw": "",
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "invalid_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "invalid_scan_output",
            "scan_input_state_before_empty_fallback": "unreadable",
            "scan_input_empty_fallback_value": "[]",
            "scanner_status_state": "empty",
            "scanner_result": "invalid_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "invalid_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "Invalid scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_malformed_reuse_with_unreadable_sidecar",
        "scenario": "skip-scan with a malformed reused scan file and an unreadable scanner-status sidecar still keeps invalid scan output as the controlling result",
        "skip_scan": True,
        "initial_scan_hits": None,
        "initial_scan_raw": "{not valid json",
        "initial_scanner_status_raw": "{not valid json",
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "invalid_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "invalid_scan_output",
            "scan_input_state_before_empty_fallback": "unreadable",
            "scan_input_empty_fallback_value": "[]",
            "scanner_status_state": "unreadable",
            "scanner_result": "invalid_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "invalid_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "Invalid scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_invalid_shape_reuse",
        "scenario": "skip-scan with a readable but non-list reused scan file writes an explicit invalid-output fallback and does not treat the fallback [] as a clean empty scan",
        "skip_scan": True,
        "initial_scan_hits": None,
        "initial_scan_raw": '{"unexpected": "object"}',
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "invalid_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "invalid_scan_output",
            "scan_input_state_before_empty_fallback": "invalid_shape",
            "scan_input_empty_fallback_value": "[]",
            "scan_input_shape_error": "expected scanner-output JSON list, got dict",
            "scanner_status_state": "missing",
            "scanner_result": "invalid_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "invalid_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "Invalid scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_invalid_shape_reuse_with_sidecar",
        "scenario": "skip-scan with an invalid-shape reused scan file and a readable scanner-status sidecar still keeps invalid scan output as the controlling result",
        "skip_scan": True,
        "initial_scan_hits": None,
        "initial_scan_raw": '{"unexpected": "object"}',
        "initial_scanner_status": {
            "result": "hits_found",
            "partial_cache": False,
            "raw_hit_count": 3,
            "emitted_hit_count": 3,
            "missing_race_detail_cache_skips": 0,
        },
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "invalid_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "invalid_scan_output",
            "scan_input_state_before_empty_fallback": "invalid_shape",
            "scan_input_empty_fallback_value": "[]",
            "scan_input_shape_error": "expected scanner-output JSON list, got dict",
            "scanner_status_state": "readable",
            "scanner_status_reported_result": "hits_found",
            "scanner_result": "invalid_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "invalid_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "Invalid scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_invalid_shape_reuse_with_empty_sidecar",
        "scenario": "skip-scan with an invalid-shape reused scan file and an empty scanner-status sidecar still keeps invalid scan output as the controlling result",
        "skip_scan": True,
        "initial_scan_hits": None,
        "initial_scan_raw": '{"unexpected": "object"}',
        "initial_scanner_status_raw": "",
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "invalid_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "invalid_scan_output",
            "scan_input_state_before_empty_fallback": "invalid_shape",
            "scan_input_empty_fallback_value": "[]",
            "scan_input_shape_error": "expected scanner-output JSON list, got dict",
            "scanner_status_state": "empty",
            "scanner_result": "invalid_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "invalid_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "Invalid scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_invalid_shape_reuse_with_unreadable_sidecar",
        "scenario": "skip-scan with an invalid-shape reused scan file and an unreadable scanner-status sidecar still keeps invalid scan output as the controlling result",
        "skip_scan": True,
        "initial_scan_hits": None,
        "initial_scan_raw": '{"unexpected": "object"}',
        "initial_scanner_status_raw": "{not valid json",
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 0, "emitted_hit_count": 0, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "invalid_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "invalid_scan_output",
            "scan_input_state_before_empty_fallback": "invalid_shape",
            "scan_input_empty_fallback_value": "[]",
            "scan_input_shape_error": "expected scanner-output JSON list, got dict",
            "scanner_status_state": "unreadable",
            "scanner_result": "invalid_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "invalid_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "Invalid scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_skip_scan_bets_ready",
        "scenario": "skip-scan reuse with a BET recommendation still classifies as bets ready",
        "skip_scan": True,
        "initial_scan_hits": [HIT_OP],
        "scan_stub": {
            "mode": "success",
            "scan_hits": [HIT_OP],
            "scanner_status": {"result": "no_qualifiers", "partial_cache": False, "raw_hit_count": 1, "emitted_hit_count": 1, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [RECOMMENDATION_BET],
        "expected_status": {
            "scanner_stage_status": "skipped_scan",
            "scanner_result": "reused_input_with_hits",
            "scan_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 1,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "bets_ready",
            "observation_scope": "bet_ready",
            "observation_reason": "bets_ready",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "Artifacts"],
    },
    {
        "name": "case_skip_scan_custom_scanner_status_sidecar",
        "scenario": "skip-scan reuse can still read a renamed scanner-status sidecar instead of falling back to generic reused-input classification",
        "skip_scan": True,
        "scan_input_name": "incoming/renamed_live_scan.json",
        "scanner_status_name": "incoming/custom_scanner_sidecar.json",
        "initial_scan_hits": [HIT_OP],
        "initial_scanner_status": {
            "result": "partial_cache_missing_detail",
            "partial_cache": True,
            "raw_hit_count": 2,
            "emitted_hit_count": 1,
            "missing_race_detail_cache_skips": 1,
        },
        "scan_stub": {
            "mode": "success",
            "scan_hits": [HIT_OP],
            "scanner_status": {"result": "hits_found", "partial_cache": False, "raw_hit_count": 1, "emitted_hit_count": 1, "missing_race_detail_cache_skips": 0},
        },
        "recommendations": [RECOMMENDATION_NO_BET],
        "expected_status": {
            "scanner_stage_status": "skipped_scan",
            "scanner_result": "partial_cache_missing_detail",
            "scanner_partial_cache": True,
            "scanner_raw_hit_count": 2,
            "scanner_emitted_hit_count": 1,
            "scanner_missing_race_detail_cache_skips": 1,
            "scan_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 0,
            "no_bet_count": 1,
            "error_count": 0,
            "observation_result": "partial_cache_with_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_with_activity",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Skipping scan step", "Pipeline status:"],
    },
    {
        "name": "case_scanner_failed_graceful_empty",
        "scenario": "scanner failures still degrade to an empty scan file with an explicit fallback reason, keep the pipeline alive, and classify as scanner_failed_empty_run",
        "skip_scan": False,
        "initial_scan_hits": None,
        "scan_stub": {
            "mode": "fail",
            "exit_code": 17,
            "scan_hits": [],
            "scanner_status": None,
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "scanner_failed",
            "scanner_exit_code": 17,
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "scanner_failed",
            "scan_input_state_before_empty_fallback": "scanner_failed_before_scan_file_replacement",
            "scan_input_empty_fallback_value": "[]",
            "scanner_result": "scanner_failed",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_failure",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Scanner exited with code 17", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_scanner_failed_overwrites_stale_scan_hits",
        "scenario": "scanner failures overwrite any pre-existing scan hits with a safe empty fallback instead of letting stale activity feed the recommender",
        "skip_scan": False,
        "initial_scan_hits": [HIT_OP],
        "scan_stub": {
            "mode": "fail",
            "exit_code": 17,
            "scan_hits": [],
            "scanner_status": None,
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "scanner_failed",
            "scanner_exit_code": 17,
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "scanner_failed",
            "scan_input_state_before_empty_fallback": "scanner_failed_before_scan_file_replacement",
            "scan_input_empty_fallback_value": "[]",
            "scanner_result": "scanner_failed",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_failure",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Scanner exited with code 17", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_scanner_success_missing_scan_output",
        "scenario": "scanner success without a scan-output file still writes an empty fallback with a missing-output reason instead of reading like clean no qualifiers",
        "skip_scan": False,
        "initial_scan_hits": None,
        "scan_stub": {
            "mode": "success_without_scan_output",
            "scan_hits": [],
            "scanner_status": {
                "result": "no_qualifiers",
                "partial_cache": False,
                "raw_hit_count": 0,
                "emitted_hit_count": 0,
                "missing_race_detail_cache_skips": 0,
            },
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "missing_scan_output",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "missing_or_empty_scan_output",
            "scan_input_state_before_empty_fallback": "missing",
            "scan_input_empty_fallback_value": "[]",
            "scanner_status_state": "readable",
            "scanner_status_reported_result": "no_qualifiers",
            "scanner_result": "missing_scan_output",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "missing_scan_output",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["stub scan complete without save", "No scanner output", "Scanner hits:"],
        "expected_scan_hits_after": [],
    },
    {
        "name": "case_cache_only_miss",
        "scenario": "cache-only scans with missing day files still publish a cache_only_miss operational-limit status instead of reading like a quiet clean empty day",
        "skip_scan": False,
        "cache_only": True,
        "initial_scan_hits": None,
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {
                "result": "scanner_error",
                "error": "No cached data for requested day",
                "partial_cache": False,
                "raw_hit_count": 0,
                "emitted_hit_count": 0,
                "missing_race_detail_cache_skips": 0,
            },
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "completed",
            "scanner_result": "scanner_error",
            "scanner_error": "No cached data for requested day",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "completed_without_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "cache_only_miss",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["$", "Pipeline status:"],
    },
    {
        "name": "case_api_access_stale_cache_fallback",
        "scenario": "API-access failures that complete from stale cache still carry API-failure and stale-cache metadata instead of reading like a clean empty day",
        "skip_scan": False,
        "initial_scan_hits": None,
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {
                "result": "scanner_error",
                "error_type": "HTTPError",
                "error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
                "http_status": 403,
                "api_access_failure": True,
                "api_failure_class": "api_access_failure",
                "api_failure_valid_scope": "operator_refresh_context_only",
                "api_failure_boundary": "API-access-failure operator context only; not a no-target, clean-empty, or forward-performance read.",
                "api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
                "api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
                "stale_cache_fallback_applied": True,
                "stale_cache_fallback_count": 2,
                "stale_cache_fallback_kind": "cards",
                "stale_cache_fallback_error_type": "HTTPError",
                "stale_cache_fallback_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
                "partial_cache": False,
                "raw_hit_count": 0,
                "emitted_hit_count": 0,
                "missing_race_detail_cache_skips": 0,
            },
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "completed",
            "scanner_status_state": "readable",
            "scanner_result": "scanner_error",
            "scanner_error_type": "HTTPError",
            "scanner_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "scanner_http_status": 403,
            "scanner_api_failure_class": "api_access_failure",
            "scanner_api_access_failure": True,
            "scanner_api_failure_valid_scope": "operator_refresh_context_only",
            "scanner_api_failure_boundary": "API-access-failure operator context only; not a no-target, clean-empty, or forward-performance read.",
            "scanner_api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
            "scanner_api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
            "scanner_stale_cache_fallback_applied": True,
            "scanner_stale_cache_fallback_count": 2,
            "scanner_stale_cache_fallback_kind": "cards",
            "scanner_stale_cache_fallback_error_type": "HTTPError",
            "scanner_stale_cache_fallback_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_failed_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "api_access_failure",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["$", "Pipeline status:"],
    },
    {
        "name": "case_partial_cache_empty",
        "scenario": "partial-cache scans with no surviving hits still classify as partial_cache_empty_run instead of a clean empty day",
        "skip_scan": False,
        "initial_scan_hits": None,
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status": {
                "result": "partial_cache_no_qualifiers",
                "partial_cache": True,
                "raw_hit_count": 1,
                "emitted_hit_count": 0,
                "missing_race_detail_cache_skips": 1,
            },
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "completed",
            "scanner_result": "partial_cache_no_qualifiers",
            "scanner_partial_cache": True,
            "scanner_raw_hit_count": 1,
            "scanner_emitted_hit_count": 0,
            "scanner_missing_race_detail_cache_skips": 1,
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "partial_cache_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_empty",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["$", "Pipeline status:"],
    },
    {
        "name": "case_partial_cache_with_activity",
        "scenario": "partial-cache scans with surviving hits and no-bet recommendations still classify as partial_cache_with_activity",
        "skip_scan": False,
        "initial_scan_hits": None,
        "scan_stub": {
            "mode": "success",
            "scan_hits": [HIT_OP],
            "scanner_status": {
                "result": "partial_cache_missing_detail",
                "partial_cache": True,
                "raw_hit_count": 2,
                "emitted_hit_count": 1,
                "missing_race_detail_cache_skips": 1,
            },
        },
        "recommendations": [RECOMMENDATION_NO_BET],
        "expected_status": {
            "scanner_stage_status": "completed",
            "scanner_result": "partial_cache_missing_detail",
            "scanner_partial_cache": True,
            "scanner_raw_hit_count": 2,
            "scanner_emitted_hit_count": 1,
            "scanner_missing_race_detail_cache_skips": 1,
            "scan_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 0,
            "no_bet_count": 1,
            "error_count": 0,
            "observation_result": "partial_cache_with_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "partial_cache_with_activity",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["$", "Pipeline status:"],
    },
    {
        "name": "case_signals_logged_no_bet",
        "scenario": "normal scans with hits but no BET recommendations still classify as signals_logged_no_bet instead of bets ready",
        "skip_scan": False,
        "initial_scan_hits": None,
        "scan_stub": {
            "mode": "success",
            "scan_hits": [HIT_OP, HIT_CD],
            "scanner_status": {
                "result": "hits_found",
                "partial_cache": False,
                "raw_hit_count": 2,
                "emitted_hit_count": 2,
                "missing_race_detail_cache_skips": 0,
            },
        },
        "recommendations": [RECOMMENDATION_NO_BET],
        "expected_status": {
            "scanner_stage_status": "completed",
            "scanner_result": "hits_found",
            "scan_hit_count": 2,
            "recommendation_count": 1,
            "bet_count": 0,
            "no_bet_count": 1,
            "error_count": 0,
            "observation_result": "signals_logged_no_bet",
            "observation_scope": "clean_observation",
            "observation_reason": "signals_logged_no_bet",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Paper-trade pipeline", "Recommendation tickets:"],
    },
    {
        "name": "case_empty_scanner_status_sidecar",
        "scenario": "zero-byte scanner-status sidecars stay explicit operational-limit states instead of reading like clean quiet days",
        "skip_scan": False,
        "initial_scan_hits": None,
        "scan_stub": {
            "mode": "success",
            "scan_hits": [],
            "scanner_status_raw": "",
        },
        "recommendations": [],
        "expected_status": {
            "scanner_stage_status": "completed",
            "scanner_status_state": "empty",
            "scanner_result": "scanner_status_empty",
            "scanner_partial_cache": False,
            "scan_hit_count": 0,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "scanner_status_unavailable_empty_run",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_status_empty",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["$", "Pipeline status:"],
    },
    {
        "name": "case_unreadable_scanner_status_sidecar_with_activity",
        "scenario": "malformed scanner-status sidecars keep scan activity but mark coverage as operationally limited",
        "skip_scan": False,
        "initial_scan_hits": None,
        "scan_stub": {
            "mode": "success",
            "scan_hits": [HIT_OP],
            "scanner_status_raw": "{not valid json",
        },
        "recommendations": [RECOMMENDATION_NO_BET],
        "expected_status": {
            "scanner_stage_status": "completed",
            "scanner_status_state": "unreadable",
            "scanner_result": "scanner_status_unreadable",
            "scanner_partial_cache": False,
            "scan_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 0,
            "no_bet_count": 1,
            "error_count": 0,
            "observation_result": "scanner_status_unavailable_with_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_status_unreadable",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Paper-trade pipeline", "Pipeline status:"],
    },
    {
        "name": "case_invalid_shape_scanner_status_sidecar_with_activity",
        "scenario": "readable but non-object scanner-status sidecars keep scan activity but mark coverage as operationally limited",
        "skip_scan": False,
        "initial_scan_hits": None,
        "scan_stub": {
            "mode": "success",
            "scan_hits": [HIT_OP],
            "scanner_status_raw": "[]",
        },
        "recommendations": [RECOMMENDATION_NO_BET],
        "expected_status": {
            "scanner_stage_status": "completed",
            "scanner_status_state": "readable",
            "scanner_result": "scanner_status_invalid_shape",
            "scanner_status_error": "expected scanner-status JSON object, got list",
            "scanner_partial_cache": False,
            "scan_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 0,
            "no_bet_count": 1,
            "error_count": 0,
            "observation_result": "scanner_status_unavailable_with_activity",
            "observation_scope": "operational_limit",
            "observation_reason": "scanner_status_invalid_shape",
            "result": "ok",
            "stage": "done",
        },
        "stdout_needles": ["Paper-trade pipeline", "Pipeline status:"],
    },
    {
        "name": "case_recommender_failure_after_hits",
        "scenario": "recommender failures keep the scanner context and clear stale recommendation summaries/plan/prediction artifacts before saving pipeline_error status output",
        "skip_scan": False,
        "initial_scan_hits": None,
        "scan_stub": {
            "mode": "success",
            "scan_hits": [HIT_OP],
            "scanner_status": {
                "result": "hits_found",
                "partial_cache": False,
                "raw_hit_count": 1,
                "emitted_hit_count": 1,
                "missing_race_detail_cache_skips": 0,
            },
        },
        "recommender_stub": {
            "mode": "fail",
            "exit_code": 23,
        },
        "initial_recommendation_artifacts": [RECOMMENDATION_BET],
        "recommendations": [],
        "expect_returncode": 1,
        "expect_logger_marker": False,
        "expected_stale_recommendation_artifacts_cleared": True,
        "expected_status": {
            "scanner_stage_status": "completed",
            "scanner_result": "hits_found",
            "scan_hit_count": 1,
            "recommendation_count": 0,
            "bet_count": 0,
            "no_bet_count": 0,
            "error_count": 0,
            "last_completed_stage": "scanner",
            "recommendation_stale_artifacts_cleared_before_recommender": True,
            "recommendation_stale_artifact_count_cleared": 6,
            "recommendation_stale_prediction_artifacts_clear_enabled": True,
            "recommendation_stale_artifact_guard": "clears stale recommendation summaries, plan files, and non-reuse prediction files before recommender subprocess so failures cannot publish old actionable tickets or scored-race context",
            "observation_scope": "operational_failure",
            "observation_reason": "recommender_failure",
            "result": "pipeline_error",
            "stage": "recommender",
            "error_type": "CalledProcessError",
        },
        "stdout_needles": ["Paper-trade pipeline", "$"],
    },
    {
        "name": "case_logger_failure_after_bet",
        "scenario": "logger failures preserve recommendation counts, bets-ready context, and the last completed recommender stage",
        "skip_scan": False,
        "initial_scan_hits": None,
        "scan_stub": {
            "mode": "success",
            "scan_hits": [HIT_OP],
            "scanner_status": {
                "result": "hits_found",
                "partial_cache": False,
                "raw_hit_count": 1,
                "emitted_hit_count": 1,
                "missing_race_detail_cache_skips": 0,
            },
        },
        "recommendations": [RECOMMENDATION_BET],
        "logger_stub": {
            "mode": "fail",
            "exit_code": 29,
        },
        "expect_returncode": 1,
        "expect_logger_marker": False,
        "expected_status": {
            "scanner_stage_status": "completed",
            "scanner_result": "hits_found",
            "scan_hit_count": 1,
            "recommendation_count": 1,
            "bet_count": 1,
            "no_bet_count": 0,
            "error_count": 0,
            "observation_result": "bets_ready",
            "last_completed_stage": "recommender",
            "observation_scope": "operational_failure",
            "observation_reason": "logger_failure",
            "result": "pipeline_error",
            "stage": "logger",
            "error_type": "CalledProcessError",
        },
        "stdout_needles": ["Paper-trade pipeline", "$"],
    },
]


SCAN_STUB = """#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path

def arg_value(flag: str) -> str | None:
    args = sys.argv[1:]
    for i, part in enumerate(args):
        if part == flag and i + 1 < len(args):
            return args[i + 1]
    return None

base = Path(__file__).resolve().parent
cfg = json.loads((base / 'stub_config.json').read_text(encoding='utf-8'))
scan_cfg = cfg['scan_stub']
save_path = Path(arg_value('--save'))
status_path = Path(arg_value('--status-json'))
if scan_cfg.get('mode') == 'fail':
    sys.exit(int(scan_cfg.get('exit_code', 1)))
status_path.parent.mkdir(parents=True, exist_ok=True)
if 'scanner_status_raw' in scan_cfg:
    status_path.write_text(str(scan_cfg.get('scanner_status_raw', '')), encoding='utf-8')
else:
    status = scan_cfg.get('scanner_status')
    if status is not None:
        status_path.write_text(json.dumps(status, indent=2) + '\\n', encoding='utf-8')
if scan_cfg.get('mode') == 'success_without_scan_output':
    print('stub scan complete without save')
    raise SystemExit(0)
save_path.parent.mkdir(parents=True, exist_ok=True)
save_path.write_text(json.dumps(scan_cfg.get('scan_hits', []), indent=2) + '\\n', encoding='utf-8')
print('stub scan complete')
"""

RECOMMENDER_STUB = """#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--scan-input', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--model')
    p.add_argument('--top-combinations')
    p.add_argument('--threads')
    p.add_argument('--workers')
    p.add_argument('--bankroll')
    p.add_argument('--payout-unit')
    p.add_argument('--ticket-increment')
    p.add_argument('--payout-haircut')
    p.add_argument('--kelly-fraction')
    p.add_argument('--min-ev-roi')
    p.add_argument('--min-prob')
    p.add_argument('--max-tickets')
    p.add_argument('--max-race-risk')
    p.add_argument('--max-ticket-risk')
    p.add_argument('--reuse-predictions', action='store_true')
    p.add_argument('--allow-all-combos', action='store_true')
    return p.parse_args()

args = parse_args()
base = Path(__file__).resolve().parent
cfg = json.loads((base / 'stub_config.json').read_text(encoding='utf-8'))
recommender_cfg = cfg.get('recommender_stub', {})
out_dir = Path(args.output_dir)
out_dir.mkdir(parents=True, exist_ok=True)
if recommender_cfg.get('mode') == 'fail':
    raise SystemExit(int(recommender_cfg.get('exit_code', 1)))
recs = cfg.get('recommendations', [])
(out_dir / 'recommendations_summary.json').write_text(json.dumps(recs, indent=2) + '\\n', encoding='utf-8')
with (out_dir / 'recommendations_summary.csv').open('w', encoding='utf-8', newline='') as fh:
    fieldnames = ['signal_key', 'decision', 'race_id']
    writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\\n")
    writer.writeheader()
    for row in recs:
        writer.writerow({key: row.get(key, '') for key in fieldnames})
print('stub recommender complete')
"""

LOGGER_STUB = """#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--ledger', required=True)
    p.add_argument('--state', required=True)
    p.add_argument('--recommendations-input', required=True)
    p.add_argument('--recommendation-ledger', required=True)
    p.add_argument('--recommendation-state', required=True)
    return p.parse_args()

args = parse_args()
base = Path(__file__).resolve().parent
cfg = json.loads((base / 'stub_config.json').read_text(encoding='utf-8'))
logger_cfg = cfg.get('logger_stub', {})
if logger_cfg.get('mode') == 'fail':
    raise SystemExit(int(logger_cfg.get('exit_code', 1)))
payload = {
    'input': args.input,
    'ledger': args.ledger,
    'state': args.state,
    'recommendations_input': args.recommendations_input,
    'recommendation_ledger': args.recommendation_ledger,
    'recommendation_state': args.recommendation_state,
}
out = base / 'out' / 'logger_invocation.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload, indent=2) + '\\n', encoding='utf-8')
print('stub logger complete')
"""


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def recommendation_artifact_paths(case_root: Path) -> list[Path]:
    output_dir = case_root / "out" / "paper_trade_recommendations_latest"
    return [
        output_dir / "recommendations_summary.json",
        output_dir / "recommendations_summary.csv",
        output_dir / "recommendations_summary.txt",
        output_dir / "plans" / "race_STALE_plan.json",
        output_dir / "plans" / "race_STALE_plan.csv",
        output_dir / "predictions" / "race_STALE_predictions.csv",
    ]


def write_initial_recommendation_artifacts(case_root: Path, recommendations: list[dict[str, Any]]) -> None:
    summary_json, summary_csv, summary_txt, plan_json, plan_csv, prediction_csv = recommendation_artifact_paths(case_root)
    write_json(summary_json, recommendations)
    write_text(summary_csv, "signal_key,decision,race_id\nstale|old|ticket,BET,STALE-R1\n")
    write_text(summary_txt, "STALE recommendation summary\n")
    write_text(plan_json, '{"stale": true}\n')
    write_text(plan_csv, "combo,recommended_stake\n1-2-3-4,9.90\n")
    write_text(prediction_csv, "combo,jointProb,predicted_payout\n1-2-3-4,0.05,120.00\n")


def setup_case(case: dict[str, Any]) -> tuple[Path, Path, Path, Path]:
    case_root = FIXTURE_ROOT / case["name"]
    if case_root.exists():
        shutil.rmtree(case_root)
    case_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCRIPT, case_root / "paper_trade_pipeline.py")
    write_text(case_root / "scan_live.sh", SCAN_STUB)
    write_text(case_root / "paper_trade_recommender.py", RECOMMENDER_STUB)
    write_text(case_root / "paper_trade_logger.py", LOGGER_STUB)
    (case_root / "scan_live.sh").chmod(0o755)
    (case_root / "paper_trade_recommender.py").chmod(0o755)
    (case_root / "paper_trade_logger.py").chmod(0o755)
    write_json(
        case_root / "stub_config.json",
        {
            "scan_stub": case["scan_stub"],
            "recommendations": case["recommendations"],
            "recommender_stub": case.get("recommender_stub", {"mode": "success"}),
            "logger_stub": case.get("logger_stub", {"mode": "success"}),
        },
    )
    scan_input = case_root / case.get("scan_input_name", "out/live_scan_latest.json")
    if "initial_scan_raw" in case:
        write_text(scan_input, str(case["initial_scan_raw"]))
    elif case.get("initial_scan_hits") is not None:
        write_json(scan_input, case["initial_scan_hits"])
    default_scanner_status_rel = scan_input.relative_to(case_root).with_suffix(".status.json")
    scanner_status_output = case_root / case.get("scanner_status_name", str(default_scanner_status_rel))
    if "initial_scanner_status_raw" in case:
        write_text(scanner_status_output, str(case["initial_scanner_status_raw"]))
    elif case.get("initial_scanner_status") is not None:
        write_json(scanner_status_output, case["initial_scanner_status"])
    if case.get("initial_recommendation_artifacts") is not None:
        write_initial_recommendation_artifacts(case_root, case["initial_recommendation_artifacts"])
    status_output = case_root / "out" / "paper_trade_pipeline_status.json"
    return case_root, scan_input, scanner_status_output, status_output


def assert_subset(actual: dict[str, Any], expected: dict[str, Any], case_name: str) -> None:
    for key, value in expected.items():
        if actual.get(key) != value:
            raise AssertionError(f"{case_name}: expected {key}={value!r}, got {actual.get(key)!r}")


def guardrail(condition: bool, check: str, detail: str) -> dict[str, str]:
    if not condition:
        raise AssertionError(f"{check}: {detail}")
    return {"check": check, "status": "pass", "detail": detail}


def require_positive_non_bool_int(value: Any, *, source_name: str, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, source_name: str, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise AssertionError(f"{source_name} {field_name} must be a string list")
    return value


def read_scorecard_gate_minimums(scorecard_json: Path = SCORECARD_JSON) -> dict[str, Any]:
    source_name = display_path(scorecard_json)
    payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
    gates = payload.get("decision_gate_minimums")
    if not isinstance(gates, dict):
        raise AssertionError(f"{source_name} is missing decision_gate_minimums")
    anchor = gates.get("anchor_displacement")
    phase8 = gates.get("phase8_promotion_review")
    real_money = gates.get("real_money_discussion")
    if not isinstance(anchor, dict) or not isinstance(phase8, dict) or not isinstance(real_money, dict):
        raise AssertionError(f"{source_name} decision_gate_minimums is incomplete")
    anchor_min = require_positive_non_bool_int(
        anchor.get("min_roi_complete_settled_observations"),
        source_name=source_name,
        field_name="decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
    )
    phase8_min = require_positive_non_bool_int(
        phase8.get("min_roi_complete_settled_observations"),
        source_name=source_name,
        field_name="decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
    )
    real_money_min = require_positive_non_bool_int(
        real_money.get("min_total_settled_observations_with_usable_roi"),
        source_name=source_name,
        field_name="decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
    )
    real_money_requires = require_string_list(
        real_money.get("also_requires"),
        source_name=source_name,
        field_name="decision_gate_minimums.real_money_discussion.also_requires",
    )
    if NO_BAQ_AS_BEL_PREREQUISITE not in real_money_requires:
        raise AssertionError(
            f"{source_name} decision_gate_minimums.real_money_discussion.also_requires "
            f"must include {NO_BAQ_AS_BEL_PREREQUISITE}"
        )
    return {
        "source": "forward_evidence_scorecard.json",
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_also_requires": real_money_requires,
        "real_money_no_baq_as_bel_required": True,
        "evidence_boundary": (
            "pipeline status fixtures, scan fallback states, and workflow sidecars do not count toward "
            "anchor-displacement, Phase 8 promotion-review, or real-money discussion gates"
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--fixture-root", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def configure_output_paths(fixture_root: Path, out_dir: Path) -> None:
    global FIXTURE_ROOT, OUT_DIR, REPORT_MD, REPORT_JSON
    FIXTURE_ROOT = fixture_root
    OUT_DIR = out_dir
    REPORT_MD = OUT_DIR / "paper_trade_pipeline_validation.md"
    REPORT_JSON = OUT_DIR / "paper_trade_pipeline_validation.json"


def assert_scorecard_failure_before_artifacts(
    *,
    scorecard_json: Path,
    mutation: Any,
    expected_stderr: str,
    check_name: str,
    detail: str,
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix=f"{check_name}_") as tmp:
        tmpdir = Path(tmp)
        bad_scorecard = tmpdir / "forward_evidence_scorecard.json"
        bad_payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
        mutation(bad_payload)
        bad_scorecard.write_text(json.dumps(bad_payload, indent=2) + "\n", encoding="utf-8")

        fixture_root = tmpdir / "fixture_root"
        out_dir = tmpdir / "nested" / "report_artifacts"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(bad_scorecard),
                "--fixture-root",
                str(fixture_root),
                "--out-dir",
                str(out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if result.returncode == 0:
            raise AssertionError(f"{check_name}: malformed scorecard unexpectedly passed")
        if expected_stderr not in result.stderr:
            raise AssertionError(
                f"{check_name}: failure stderr no longer explains the malformed scorecard gate\n"
                f"stderr={result.stderr}"
            )
        if fixture_root.exists() or out_dir.exists():
            raise AssertionError(f"{check_name}: malformed scorecard created fixture/report artifacts")
    return guardrail(True, check_name, detail)


def scorecard_no_artifact_guardrails(scorecard_json: Path) -> list[dict[str, str]]:
    return [
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["anchor_displacement"].__setitem__(
                "min_roi_complete_settled_observations",
                True,
            ),
            expected_stderr=(
                "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check_name="scorecard_boolean_gate_floor_fails_before_pipeline_artifacts",
            detail=(
                "a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before "
                "the pipeline validator creates fixture roots or report artifacts"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["phase8_promotion_review"].__setitem__(
                "min_roi_complete_settled_observations",
                0,
            ),
            expected_stderr=(
                "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check_name="scorecard_nonpositive_phase8_gate_floor_fails_before_pipeline_artifacts",
            detail=(
                "a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails before "
                "the pipeline validator creates fixture roots or report artifacts"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                "min_total_settled_observations_with_usable_roi",
                0,
            ),
            expected_stderr=(
                "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi "
                "must be a positive non-boolean integer"
            ),
            check_name="scorecard_nonpositive_real_money_gate_floor_fails_before_pipeline_artifacts",
            detail=(
                "a non-positive real-money discussion floor in forward_evidence_scorecard.json fails before "
                "the pipeline validator creates fixture roots or report artifacts"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                "also_requires",
                [
                    item
                    for item in payload["decision_gate_minimums"]["real_money_discussion"].get(
                        "also_requires",
                        [],
                    )
                    if item != NO_BAQ_AS_BEL_PREREQUISITE
                ],
            ),
            expected_stderr=(
                "decision_gate_minimums.real_money_discussion.also_requires must include "
                f"{NO_BAQ_AS_BEL_PREREQUISITE}"
            ),
            check_name="scorecard_missing_no_baq_fails_before_pipeline_artifacts",
            detail=(
                "a scorecard real-money gate that drops the no BAQ-as-BEL prerequisite fails before "
                "the pipeline validator creates fixture roots or report artifacts"
            ),
        ),
    ]


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_root, scan_input, scanner_status_output, status_output = setup_case(case)
    cmd = [
        sys.executable,
        str(case_root / "paper_trade_pipeline.py"),
        "--scan-input",
        str(scan_input),
        "--scanner-status-output",
        str(scanner_status_output),
        "--status-output",
        str(status_output),
    ]
    if case.get("skip_scan"):
        cmd.append("--skip-scan")
    if case.get("cache_only"):
        cmd.append("--cache-only")

    result = subprocess.run(cmd, cwd=case_root, capture_output=True, text=True)
    (case_root / "stdout.txt").write_text(result.stdout, encoding="utf-8")
    (case_root / "stderr.txt").write_text(result.stderr, encoding="utf-8")
    expected_returncode = int(case.get("expect_returncode", 0))
    if result.returncode != expected_returncode:
        raise AssertionError(
            f"{case['name']}: expected return code {expected_returncode}, got {result.returncode}\n"
            f"stderr={result.stderr}"
        )
    for needle in case.get("stdout_needles", []):
        if needle not in result.stdout:
            raise AssertionError(f"{case['name']}: expected stdout to contain {needle!r}")
    for needle in (
        f"valid_evidence_scope={pipeline_source.PIPELINE_VALID_SCOPE}",
        f"Evidence boundary: {pipeline_source.PIPELINE_EVIDENCE_BOUNDARY}",
    ):
        if needle not in result.stdout:
            raise AssertionError(f"{case['name']}: expected stdout to contain pipeline boundary line {needle!r}")

    status_payload = read_json(status_output)
    assert_subset(status_payload, case["expected_status"], case["name"])
    if status_payload.get("valid_evidence_scope") != pipeline_source.PIPELINE_VALID_SCOPE:
        raise AssertionError(f"{case['name']}: pipeline status is missing the scan/recommend/log evidence scope")
    if status_payload.get("evidence_boundary") != pipeline_source.PIPELINE_EVIDENCE_BOUNDARY:
        raise AssertionError(f"{case['name']}: pipeline status is missing the operational-only evidence boundary")
    if status_payload.get("evidence_boundary_metadata") != pipeline_source.PIPELINE_EVIDENCE_BOUNDARY_METADATA:
        raise AssertionError(f"{case['name']}: pipeline status is missing the structured operational-only evidence boundary metadata")

    logger_marker = case_root / "out" / "logger_invocation.json"
    expect_logger_marker = bool(case.get("expect_logger_marker", True))
    if expect_logger_marker and not logger_marker.exists():
        raise AssertionError(f"{case['name']}: logger marker missing")
    if not expect_logger_marker and logger_marker.exists():
        raise AssertionError(f"{case['name']}: logger marker unexpectedly exists")

    if "expected_scan_hits_after" in case:
        scan_hits_after = read_json(scan_input)
        if scan_hits_after != case["expected_scan_hits_after"]:
            raise AssertionError(
                f"{case['name']}: scan input mismatch after run\n"
                f"actual={json.dumps(scan_hits_after, indent=2)}\nexpected={json.dumps(case['expected_scan_hits_after'], indent=2)}"
            )

    if case.get("expected_stale_recommendation_artifacts_cleared"):
        remaining = [str(path.relative_to(case_root)) for path in recommendation_artifact_paths(case_root) if path.exists()]
        if remaining:
            raise AssertionError(f"{case['name']}: stale recommendation artifacts were not cleared: {remaining}")

    return {
        "name": case["name"],
        "scenario": case["scenario"],
        "result": "PASS",
        "status_output": str(status_output.relative_to(BASE)),
        "scanner_status_output": str(scanner_status_output.relative_to(BASE)),
        "stdout": str((case_root / "stdout.txt").relative_to(BASE)),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    scorecard_json = args.scorecard_json.expanduser().resolve()
    configure_output_paths(args.fixture_root.expanduser().resolve(), args.out_dir.expanduser().resolve())
    scorecard_gates = read_scorecard_gate_minimums(scorecard_json)
    scorecard_artifact_guardrails = scorecard_no_artifact_guardrails(scorecard_json)

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for legacy in (
        FIXTURE_ROOT / "paper_trade_pipeline_fixture_validation.md",
        FIXTURE_ROOT / "paper_trade_pipeline_fixture_validation.json",
    ):
        legacy.unlink(missing_ok=True)

    results = [run_case(case) for case in CASES]
    status_by_case = {row["name"]: read_json(BASE / row["status_output"]) for row in results}
    case_names = set(status_by_case)
    if BASE.resolve() not in FIXTURE_ROOT.resolve().parents:
        raise AssertionError("paper-trade pipeline fixture root is not project-local")
    scratch = {
        "fixture_root_relative": str(FIXTURE_ROOT.relative_to(BASE)),
        "fixture_root_is_project_local": True,
        "case_roots_cleared_by_setup_case": True,
        "report_root_relative": str(OUT_DIR.relative_to(BASE)),
        "evidence_boundary": "paper-trade pipeline fixture scratch metadata is reproducibility context only, not a scanner result, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
    }
    current_read = "paper-trade pipeline still classifies skip-scan empty reuse, skip-scan missing reuse, skip-scan missing reuse with empty, readable, and unreadable sidecars, skip-scan zero-byte reuse, skip-scan zero-byte reuse with empty, readable, and unreadable sidecars, skip-scan malformed reuse, skip-scan malformed reuse with empty, readable, and unreadable sidecars, skip-scan invalid-shape reuse, skip-scan invalid-shape reuse with empty, readable, and unreadable sidecars, bets-ready reuse, skip-scan custom scanner-status reuse, cache-only missing-cache runs, API-access stale-cache fallback runs, scanner-failed and missing-output empty runs with explicit scan-input fallback reason fields, scanner-failure stale-scan overwrite protection, recommender-failure stale recommendation artifact cleanup including non-reuse prediction CSV cleanup, empty scanner-status sidecars, unreadable scanner-status sidecars with activity, readable-but-invalid-shape scanner-status sidecars with activity, partial-cache empty runs, partial-cache activity, and signals-logged-no-bet runs distinctly in its machine-readable status output, now also publishing explicit observation-scope and observation-reason fields plus `valid_evidence_scope` / `evidence_boundary` metadata, structured `evidence_boundary_metadata`, and stdout-visible source-level valid_evidence_scope plus evidence-boundary lines so downstream helpers and copied logs do not have to infer cache-miss vs API-access stale-cache fallback vs missing scan output vs invalid scan output vs sidecar-unavailable vs invalid scanner-status shape vs partial-cache vs true clean-empty meaning from mixed sidecar strings or let stale scan hits survive a failed scanner run, stale recommendation tickets or scored-race context survive a failed recommender run, or treat a green workflow sidecar or copied log as live profitability, promotion, or real-money evidence, while preserving the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that pipeline status fixtures and workflow sidecars do not advance, rejecting malformed and non-positive scorecard gates before fixture/report artifacts, accepting an explicit scanner-status-output path so reused or scratch live-scan artifacts do not have to keep a hard-coded sidecar basename, preserving scanner/recommendation context plus last-completed-stage detail across direct recommender and logger pipeline_error fixtures, publishing project-local fixture scratch metadata as a structured guardrail, exposing exact valid_evidence_scope=scan_recommend_log_status_only as direct validator-report metadata only, and publishing its validator report at the standard paper-trade-pipeline validation path"
    child_checks = [
        *scorecard_artifact_guardrails,
        guardrail(
            {
                "case_skip_scan_empty_reuse",
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
                "case_skip_scan_bets_ready",
                "case_cache_only_miss",
                "case_api_access_stale_cache_fallback",
                "case_scanner_failed_graceful_empty",
                "case_scanner_failed_overwrites_stale_scan_hits",
                "case_scanner_success_missing_scan_output",
                "case_empty_scanner_status_sidecar",
                "case_unreadable_scanner_status_sidecar_with_activity",
                "case_invalid_shape_scanner_status_sidecar_with_activity",
                "case_partial_cache_empty",
                "case_partial_cache_with_activity",
                "case_signals_logged_no_bet",
            }.issubset(case_names)
            and status_by_case["case_scanner_failed_graceful_empty"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_scanner_failed_graceful_empty"].get("scan_input_empty_fallback_reason") == "scanner_failed"
            and status_by_case["case_scanner_failed_graceful_empty"].get("scan_input_state_before_empty_fallback") == "scanner_failed_before_scan_file_replacement"
            and status_by_case["case_scanner_failed_overwrites_stale_scan_hits"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_scanner_failed_overwrites_stale_scan_hits"].get("scan_input_empty_fallback_reason") == "scanner_failed"
            and status_by_case["case_scanner_failed_overwrites_stale_scan_hits"].get("scan_hit_count") == 0
            and status_by_case["case_scanner_failed_overwrites_stale_scan_hits"].get("scanner_result") == "scanner_failed"
            and status_by_case["case_scanner_failed_overwrites_stale_scan_hits"].get("observation_reason") == "scanner_failure"
            and status_by_case["case_scanner_success_missing_scan_output"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_scanner_success_missing_scan_output"].get("scan_input_empty_fallback_reason") == "missing_or_empty_scan_output"
            and status_by_case["case_scanner_success_missing_scan_output"].get("scan_input_state_before_empty_fallback") == "missing"
            and status_by_case["case_scanner_success_missing_scan_output"].get("scanner_result") == "missing_scan_output"
            and status_by_case["case_scanner_success_missing_scan_output"].get("scanner_status_reported_result") == "no_qualifiers"
            and status_by_case["case_scanner_success_missing_scan_output"].get("observation_reason") == "missing_scan_output"
            and status_by_case["case_skip_scan_missing_reuse"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_missing_reuse"].get("scanner_status_state") == "missing"
            and status_by_case["case_skip_scan_missing_reuse"].get("scanner_result") == "missing_scan_output"
            and status_by_case["case_skip_scan_missing_reuse"].get("observation_reason") == "missing_scan_output"
            and "scanner_status_reported_result" not in status_by_case["case_skip_scan_missing_reuse"]
            and status_by_case["case_skip_scan_missing_reuse_with_sidecar"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_missing_reuse_with_sidecar"].get("scan_input_state_before_empty_fallback") == "missing"
            and status_by_case["case_skip_scan_missing_reuse_with_sidecar"].get("scanner_status_state") == "readable"
            and status_by_case["case_skip_scan_missing_reuse_with_sidecar"].get("scanner_status_reported_result") == "hits_found"
            and status_by_case["case_skip_scan_missing_reuse_with_sidecar"].get("scanner_result") == "missing_scan_output"
            and status_by_case["case_skip_scan_missing_reuse_with_sidecar"].get("observation_reason") == "missing_scan_output"
            and status_by_case["case_skip_scan_missing_reuse_with_empty_sidecar"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_missing_reuse_with_empty_sidecar"].get("scan_input_state_before_empty_fallback") == "missing"
            and status_by_case["case_skip_scan_missing_reuse_with_empty_sidecar"].get("scanner_status_state") == "empty"
            and status_by_case["case_skip_scan_missing_reuse_with_empty_sidecar"].get("scanner_result") == "missing_scan_output"
            and status_by_case["case_skip_scan_missing_reuse_with_empty_sidecar"].get("observation_reason") == "missing_scan_output"
            and "scanner_status_reported_result" not in status_by_case["case_skip_scan_missing_reuse_with_empty_sidecar"]
            and status_by_case["case_skip_scan_missing_reuse_with_unreadable_sidecar"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_missing_reuse_with_unreadable_sidecar"].get("scan_input_state_before_empty_fallback") == "missing"
            and status_by_case["case_skip_scan_missing_reuse_with_unreadable_sidecar"].get("scanner_status_state") == "unreadable"
            and "scanner_status_error" in status_by_case["case_skip_scan_missing_reuse_with_unreadable_sidecar"]
            and status_by_case["case_skip_scan_missing_reuse_with_unreadable_sidecar"].get("scanner_result") == "missing_scan_output"
            and status_by_case["case_skip_scan_missing_reuse_with_unreadable_sidecar"].get("observation_reason") == "missing_scan_output"
            and "scanner_status_reported_result" not in status_by_case["case_skip_scan_missing_reuse_with_unreadable_sidecar"]
            and status_by_case["case_skip_scan_zero_byte_reuse"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_zero_byte_reuse"].get("scan_input_state_before_empty_fallback") == "empty"
            and status_by_case["case_skip_scan_zero_byte_reuse"].get("scanner_status_state") == "missing"
            and status_by_case["case_skip_scan_zero_byte_reuse"].get("scanner_result") == "missing_scan_output"
            and status_by_case["case_skip_scan_zero_byte_reuse"].get("observation_reason") == "missing_scan_output"
            and "scanner_status_reported_result" not in status_by_case["case_skip_scan_zero_byte_reuse"]
            and status_by_case["case_skip_scan_zero_byte_reuse_with_sidecar"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_zero_byte_reuse_with_sidecar"].get("scan_input_state_before_empty_fallback") == "empty"
            and status_by_case["case_skip_scan_zero_byte_reuse_with_sidecar"].get("scanner_status_state") == "readable"
            and status_by_case["case_skip_scan_zero_byte_reuse_with_sidecar"].get("scanner_status_reported_result") == "hits_found"
            and status_by_case["case_skip_scan_zero_byte_reuse_with_sidecar"].get("scanner_result") == "missing_scan_output"
            and status_by_case["case_skip_scan_zero_byte_reuse_with_sidecar"].get("observation_reason") == "missing_scan_output"
            and status_by_case["case_skip_scan_zero_byte_reuse_with_empty_sidecar"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_zero_byte_reuse_with_empty_sidecar"].get("scan_input_state_before_empty_fallback") == "empty"
            and status_by_case["case_skip_scan_zero_byte_reuse_with_empty_sidecar"].get("scanner_status_state") == "empty"
            and status_by_case["case_skip_scan_zero_byte_reuse_with_empty_sidecar"].get("scanner_result") == "missing_scan_output"
            and status_by_case["case_skip_scan_zero_byte_reuse_with_empty_sidecar"].get("observation_reason") == "missing_scan_output"
            and "scanner_status_reported_result" not in status_by_case["case_skip_scan_zero_byte_reuse_with_empty_sidecar"]
            and status_by_case["case_skip_scan_zero_byte_reuse_with_unreadable_sidecar"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_zero_byte_reuse_with_unreadable_sidecar"].get("scan_input_state_before_empty_fallback") == "empty"
            and status_by_case["case_skip_scan_zero_byte_reuse_with_unreadable_sidecar"].get("scanner_status_state") == "unreadable"
            and "scanner_status_error" in status_by_case["case_skip_scan_zero_byte_reuse_with_unreadable_sidecar"]
            and status_by_case["case_skip_scan_zero_byte_reuse_with_unreadable_sidecar"].get("scanner_result") == "missing_scan_output"
            and status_by_case["case_skip_scan_zero_byte_reuse_with_unreadable_sidecar"].get("observation_reason") == "missing_scan_output"
            and "scanner_status_reported_result" not in status_by_case["case_skip_scan_zero_byte_reuse_with_unreadable_sidecar"]
            and status_by_case["case_skip_scan_malformed_reuse"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_malformed_reuse"].get("scan_input_state_before_empty_fallback") == "unreadable"
            and status_by_case["case_skip_scan_malformed_reuse"].get("scan_input_empty_fallback_reason") == "invalid_scan_output"
            and status_by_case["case_skip_scan_malformed_reuse"].get("scanner_status_state") == "missing"
            and status_by_case["case_skip_scan_malformed_reuse"].get("scanner_result") == "invalid_scan_output"
            and status_by_case["case_skip_scan_malformed_reuse"].get("observation_reason") == "invalid_scan_output"
            and "scanner_status_reported_result" not in status_by_case["case_skip_scan_malformed_reuse"]
            and status_by_case["case_skip_scan_malformed_reuse_with_sidecar"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_malformed_reuse_with_sidecar"].get("scan_input_state_before_empty_fallback") == "unreadable"
            and status_by_case["case_skip_scan_malformed_reuse_with_sidecar"].get("scanner_status_state") == "readable"
            and status_by_case["case_skip_scan_malformed_reuse_with_sidecar"].get("scanner_status_reported_result") == "hits_found"
            and status_by_case["case_skip_scan_malformed_reuse_with_sidecar"].get("scanner_result") == "invalid_scan_output"
            and status_by_case["case_skip_scan_malformed_reuse_with_sidecar"].get("observation_reason") == "invalid_scan_output"
            and status_by_case["case_skip_scan_malformed_reuse_with_empty_sidecar"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_malformed_reuse_with_empty_sidecar"].get("scan_input_state_before_empty_fallback") == "unreadable"
            and status_by_case["case_skip_scan_malformed_reuse_with_empty_sidecar"].get("scanner_status_state") == "empty"
            and status_by_case["case_skip_scan_malformed_reuse_with_empty_sidecar"].get("scanner_result") == "invalid_scan_output"
            and status_by_case["case_skip_scan_malformed_reuse_with_empty_sidecar"].get("observation_reason") == "invalid_scan_output"
            and "scanner_status_reported_result" not in status_by_case["case_skip_scan_malformed_reuse_with_empty_sidecar"]
            and status_by_case["case_skip_scan_malformed_reuse_with_unreadable_sidecar"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_malformed_reuse_with_unreadable_sidecar"].get("scan_input_state_before_empty_fallback") == "unreadable"
            and status_by_case["case_skip_scan_malformed_reuse_with_unreadable_sidecar"].get("scanner_status_state") == "unreadable"
            and "scanner_status_error" in status_by_case["case_skip_scan_malformed_reuse_with_unreadable_sidecar"]
            and status_by_case["case_skip_scan_malformed_reuse_with_unreadable_sidecar"].get("scanner_result") == "invalid_scan_output"
            and status_by_case["case_skip_scan_malformed_reuse_with_unreadable_sidecar"].get("observation_reason") == "invalid_scan_output"
            and "scanner_status_reported_result" not in status_by_case["case_skip_scan_malformed_reuse_with_unreadable_sidecar"]
            and status_by_case["case_skip_scan_invalid_shape_reuse"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_invalid_shape_reuse"].get("scan_input_state_before_empty_fallback") == "invalid_shape"
            and status_by_case["case_skip_scan_invalid_shape_reuse"].get("scan_input_empty_fallback_reason") == "invalid_scan_output"
            and status_by_case["case_skip_scan_invalid_shape_reuse"].get("scan_input_shape_error") == "expected scanner-output JSON list, got dict"
            and status_by_case["case_skip_scan_invalid_shape_reuse"].get("scanner_status_state") == "missing"
            and status_by_case["case_skip_scan_invalid_shape_reuse"].get("scanner_result") == "invalid_scan_output"
            and status_by_case["case_skip_scan_invalid_shape_reuse"].get("observation_reason") == "invalid_scan_output"
            and "scanner_status_reported_result" not in status_by_case["case_skip_scan_invalid_shape_reuse"]
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_sidecar"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_sidecar"].get("scan_input_state_before_empty_fallback") == "invalid_shape"
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_sidecar"].get("scanner_status_state") == "readable"
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_sidecar"].get("scanner_status_reported_result") == "hits_found"
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_sidecar"].get("scanner_result") == "invalid_scan_output"
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_sidecar"].get("observation_reason") == "invalid_scan_output"
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_empty_sidecar"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_empty_sidecar"].get("scan_input_state_before_empty_fallback") == "invalid_shape"
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_empty_sidecar"].get("scan_input_shape_error") == "expected scanner-output JSON list, got dict"
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_empty_sidecar"].get("scanner_status_state") == "empty"
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_empty_sidecar"].get("scanner_result") == "invalid_scan_output"
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_empty_sidecar"].get("observation_reason") == "invalid_scan_output"
            and "scanner_status_reported_result" not in status_by_case["case_skip_scan_invalid_shape_reuse_with_empty_sidecar"]
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_unreadable_sidecar"].get("scan_input_empty_fallback_applied") is True
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_unreadable_sidecar"].get("scan_input_state_before_empty_fallback") == "invalid_shape"
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_unreadable_sidecar"].get("scan_input_shape_error") == "expected scanner-output JSON list, got dict"
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_unreadable_sidecar"].get("scanner_status_state") == "unreadable"
            and "scanner_status_error" in status_by_case["case_skip_scan_invalid_shape_reuse_with_unreadable_sidecar"]
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_unreadable_sidecar"].get("scanner_result") == "invalid_scan_output"
            and status_by_case["case_skip_scan_invalid_shape_reuse_with_unreadable_sidecar"].get("observation_reason") == "invalid_scan_output"
            and "scanner_status_reported_result" not in status_by_case["case_skip_scan_invalid_shape_reuse_with_unreadable_sidecar"]
            and status_by_case["case_skip_scan_empty_reuse"].get("scan_input_empty_fallback_applied") is False
            and status_by_case["case_api_access_stale_cache_fallback"].get("scanner_api_access_failure") is True
            and status_by_case["case_api_access_stale_cache_fallback"].get("scanner_http_status") == 403
            and status_by_case["case_api_access_stale_cache_fallback"].get("scanner_api_failure_class") == "api_access_failure"
            and status_by_case["case_api_access_stale_cache_fallback"].get("scanner_api_failure_operator_action") == "refresh_daily_wrapper_before_evidence_read"
            and status_by_case["case_api_access_stale_cache_fallback"].get("scanner_api_failure_recheck_command") == "./run_daily_portfolio_observation.sh"
            and status_by_case["case_api_access_stale_cache_fallback"].get("scanner_stale_cache_fallback_applied") is True
            and status_by_case["case_api_access_stale_cache_fallback"].get("scanner_stale_cache_fallback_count") == 2
            and status_by_case["case_api_access_stale_cache_fallback"].get("scanner_stale_cache_fallback_kind") == "cards"
            and status_by_case["case_api_access_stale_cache_fallback"].get("observation_result") == "scanner_failed_empty_run"
            and status_by_case["case_api_access_stale_cache_fallback"].get("observation_scope") == "operational_limit"
            and status_by_case["case_api_access_stale_cache_fallback"].get("observation_reason") == "api_access_failure"
            and status_by_case["case_api_access_stale_cache_fallback"].get("scanner_result") != "no_qualifiers",

            "pipeline_status_matrix_stays_operationally_distinct",
            "the validator still covers clean-empty reuse, skip-scan missing reuse, skip-scan missing reuse with empty, readable, and unreadable sidecars, skip-scan zero-byte reuse, skip-scan zero-byte reuse with empty, readable, and unreadable sidecars, skip-scan malformed reuse, skip-scan malformed reuse with empty, readable, and unreadable sidecars, skip-scan invalid-shape reuse, skip-scan invalid-shape reuse with empty, readable, and unreadable sidecars, bets-ready reuse, cache-only miss, API-access stale-cache fallback, scanner failure and missing scan output with explicit empty-scan fallback metadata, scanner-failure stale-scan overwrite protection, recommender-failure stale recommendation artifact cleanup including non-reuse prediction CSV cleanup, empty/unreadable/invalid-shape scanner-status sidecars, partial-cache empty, partial-cache-with-activity, and signals-logged-no-bet states instead of flattening them into one quiet-run branch or reusing stale scan activity after a failed scanner run or stale recommendation tickets/scored-race context after a failed recommender run",
        ),
        guardrail(
            all(
                status.get("valid_evidence_scope") == pipeline_source.PIPELINE_VALID_SCOPE
                and status.get("evidence_boundary") == pipeline_source.PIPELINE_EVIDENCE_BOUNDARY
                and status.get("evidence_boundary_metadata") == pipeline_source.PIPELINE_EVIDENCE_BOUNDARY_METADATA
                and status.get("evidence_boundary_metadata", {}).get("status_sidecar_is_workflow_metadata_only") is True
                and "do not substitute BAQ for BEL" in status.get("evidence_boundary_metadata", {}).get("non_goals", [])
                for status in status_by_case.values()
            ),
            "pipeline_status_publishes_workflow_only_evidence_boundary",
            "every saved pipeline-status fixture now carries `valid_evidence_scope`, the prose `evidence_boundary`, and structured `evidence_boundary_metadata`, and every fixture stdout prints the same scope/boundary lines, so automation and copied logs see the scan/recommend/log sidecar as workflow-state metadata rather than live profitability, promotion, real-money evidence, OP_REFINED_K7 / Phase 8 promotion, odds-only XGBoost reopening, or BAQ/BEL substitution evidence",
        ),
        guardrail(
            status_by_case["case_skip_scan_custom_scanner_status_sidecar"].get("scanner_status_path", "").endswith("custom_scanner_sidecar.json")
            and status_by_case["case_empty_scanner_status_sidecar"].get("scanner_status_state") == "empty"
            and status_by_case["case_unreadable_scanner_status_sidecar_with_activity"].get("scanner_status_state") == "unreadable"
            and status_by_case["case_invalid_shape_scanner_status_sidecar_with_activity"].get("scanner_status_state") == "readable"
            and status_by_case["case_invalid_shape_scanner_status_sidecar_with_activity"].get("scanner_result") == "scanner_status_invalid_shape"
            and status_by_case["case_invalid_shape_scanner_status_sidecar_with_activity"].get("observation_reason") == "scanner_status_invalid_shape",
            "scanner_status_sidecar_paths_and_states_stay_machine_readable",
            "custom scanner-status sidecar paths plus empty/unreadable/invalid-shape scanner-status states stay explicit in JSON instead of being inferred from default filenames or prose-only warnings",
        ),
        guardrail(
            status_by_case["case_recommender_failure_after_hits"].get("result") == "pipeline_error"
            and status_by_case["case_recommender_failure_after_hits"].get("last_completed_stage") == "scanner"
            and status_by_case["case_recommender_failure_after_hits"].get("scan_hit_count") == 1
            and status_by_case["case_recommender_failure_after_hits"].get("recommendation_count") == 0
            and status_by_case["case_recommender_failure_after_hits"].get("recommendation_stale_artifacts_cleared_before_recommender") is True
            and status_by_case["case_recommender_failure_after_hits"].get("recommendation_stale_artifact_count_cleared") == 6
            and status_by_case["case_recommender_failure_after_hits"].get("recommendation_stale_prediction_artifacts_clear_enabled") is True
            and "old actionable tickets or scored-race context" in status_by_case["case_recommender_failure_after_hits"].get("recommendation_stale_artifact_guard", "")
            and status_by_case["case_logger_failure_after_bet"].get("result") == "pipeline_error"
            and status_by_case["case_logger_failure_after_bet"].get("last_completed_stage") == "recommender"
            and status_by_case["case_logger_failure_after_bet"].get("observation_result") == "bets_ready",
            "pipeline_errors_preserve_pre_error_context",
            "recommender and logger failures still preserve upstream scanner/recommendation counts plus last-completed-stage context, and recommender failures clear stale recommendation summaries/plan artifacts plus non-reuse prediction CSVs before the failed subprocess can leave old actionable tickets or scored-race context behind",
        ),
        guardrail(
            "workflow sidecar or copied log as live profitability, promotion, or real-money evidence" in current_read
            and "standard paper-trade-pipeline validation path" in current_read,
            "pipeline_validator_stays_source_layer_not_new_evidence",
            "the direct pipeline validator summary still frames a green result as source-layer workflow/status reproducibility, not new forward edge evidence",
        ),
        guardrail(
            VALIDATOR_EVIDENCE_BOUNDARY.get("valid_evidence_scope") == pipeline_source.PIPELINE_VALID_SCOPE
            and VALIDATOR_EVIDENCE_BOUNDARY.get("pipeline_validator_passes_are_workflow_metadata_only") is True
            and VALIDATOR_EVIDENCE_BOUNDARY.get("not_settled_roi_evidence") is True
            and VALIDATOR_EVIDENCE_BOUNDARY.get("not_live_profitability_evidence") is True
            and VALIDATOR_EVIDENCE_BOUNDARY.get("not_real_money_evidence") is True
            and VALIDATOR_EVIDENCE_BOUNDARY.get("not_promotion_readiness_evidence") is True
            and VALIDATOR_EVIDENCE_BOUNDARY.get("baq_as_bel_substitution_allowed") is False
            and f"valid_evidence_scope={pipeline_source.PIPELINE_VALID_SCOPE}" in current_read,
            "direct_validation_report_exposes_pipeline_valid_scope",
            "the direct pipeline validation markdown and JSON now expose valid_evidence_scope=scan_recommend_log_status_only so the report artifact itself cannot be copied as scanner evidence, settled ROI, promotion readiness, live profitability, real-money support, XGBoost reopening, Phase 8 promotion, or BAQ-as-BEL evidence",
        ),
        guardrail(
            scorecard_gates.get("source") == "forward_evidence_scorecard.json"
            and scorecard_gates.get("source_path") == "decision_gate_minimums"
            and scorecard_gates.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and scorecard_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and scorecard_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and scorecard_gates.get("real_money_no_baq_as_bel_required") is True
            and "no BAQ-as-BEL substitution" in scorecard_gates.get("real_money_also_requires", []),
            "pipeline_preserves_scorecard_gate_boundary",
            "the direct pipeline validator now reads forward_evidence_scorecard.json decision_gate_minimums and publishes the 30-row anchor-review floor, 20-row Phase 8 review floor, 100-row real-money discussion floor, and no-BAQ-as-BEL prerequisite as workflow-status boundary metadata only",
        ),
        guardrail(
            scratch["fixture_root_relative"] == "out/status_validation/paper_trade_pipeline_fixture"
            and scratch["fixture_root_is_project_local"] is True
            and scratch["case_roots_cleared_by_setup_case"] is True,
            "fixture_scratch_metadata_published",
            "the direct pipeline validator now publishes project-local fixture scratch metadata so parent rollups can verify isolated pipeline-fixture hygiene without parsing markdown prose",
        ),
    ]

    payload = {
        "suite_status": "pass",
        "artifact_status": "pass",
        "total_fixture_scenarios": len(results),
        "total_checks": len(results),
        "check_count": len(results),
        "valid_evidence_scope": pipeline_source.PIPELINE_VALID_SCOPE,
        "evidence_boundary": VALIDATOR_EVIDENCE_BOUNDARY,
        "evidence_boundary_text": pipeline_source.PIPELINE_EVIDENCE_BOUNDARY,
        "cases": results,
        "child_check_count": len(child_checks),
        "child_checks": child_checks,
        "scratch": scratch,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "summary": {
            "current_read": current_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "fixture_root": str(FIXTURE_ROOT),
            "report_path": str(REPORT_MD),
        },
    }

    lines = [
        "# Paper-Trade Pipeline Validation",
        "",
        "This report validates `paper_trade_pipeline.py` directly inside isolated fixture stubs while publishing the saved validator artifact at the standard paper-trade-pipeline report path.",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {VALIDATOR_EVIDENCE_BOUNDARY['artifact_role']}",
        f"- valid_evidence_scope={pipeline_source.PIPELINE_VALID_SCOPE}",
        f"- Valid use: {VALIDATOR_EVIDENCE_BOUNDARY['valid_use']}",
        f"- Source status boundary: {pipeline_source.PIPELINE_EVIDENCE_BOUNDARY}",
        "- Boundary: this validator pass is workflow-status reproducibility metadata only, not scanner evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, real-money support, XGBoost reopening, Phase 8 promotion, or BAQ-as-BEL evidence.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Fixture root: `{FIXTURE_ROOT}`",
        f"- Report path: `{REPORT_MD}`",
        f"- Fixture scratch metadata: `{scratch['fixture_root_relative']}` is project-local and each fixture case root is cleared before setup.",
        "",
        "## Cases",
        "",
        "| Case | Scenario | Status artifact |",
        "|---|---|---|",
    ]
    for row in results:
        lines.append(f"| `{row['name']}` | {row['scenario']} | `{row['status_output']}` |")

    lines.extend([
        "",
        "## Rollup Guardrails",
        "",
        *[f"- PASS `{check['check']}` — {check['detail']}" for check in child_checks],
        "",
        "## Current Read",
        "",
        f"- Suite read: {payload['summary']['current_read']}",
        "",
        "## Decision-Gate Source",
        "",
        f"- Source: `{scorecard_gates['source']}` `{scorecard_gates['source_path']}`.",
        f"- Anchor displacement: `{scorecard_gates['anchor_displacement_min_roi_complete_settled_observations']}` ROI-complete same-candidate paper observations.",
        f"- Phase 8 promotion review: `{scorecard_gates['phase8_promotion_review_min_roi_complete_settled_observations']}` ROI-complete shadow observations.",
        f"- Real-money discussion: `{scorecard_gates['real_money_discussion_min_total_settled_observations_with_usable_roi']}` total settled observations with usable ROI.",
        f"- Real-money prerequisites: {'; '.join(scorecard_gates['real_money_also_requires'])}.",
        f"- Boundary: {scorecard_gates['evidence_boundary']}.",
        "",
        "## Validation result",
        "",
        "- Skip-scan empty reuse still lands in `clean_empty_run` instead of collapsing into a generic failure.",
        "- Skip-scan with a missing reused scan file now stays in `missing_scan_output` with explicit fallback metadata and no fallback-derived `scanner_status_reported_result`.",
        "- Skip-scan with a missing reused scan file plus a readable scanner-status sidecar now keeps `missing_scan_output` as the controlling result while preserving the sidecar's own result only as `scanner_status_reported_result`.",
        "- Skip-scan with a missing reused scan file plus an empty scanner-status sidecar now keeps `missing_scan_output` as the controlling result while preserving the empty-sidecar fact only as scanner-status metadata.",
        "- Skip-scan with a missing reused scan file plus an unreadable scanner-status sidecar now keeps `missing_scan_output` as the controlling result while preserving the sidecar parse failure only as scanner-status metadata.",
        "- Skip-scan with a zero-byte reused scan file now stays in `missing_scan_output` with explicit fallback metadata and no fallback-derived `scanner_status_reported_result`.",
        "- Skip-scan with a zero-byte reused scan file plus a readable scanner-status sidecar now keeps `missing_scan_output` as the controlling result while preserving the sidecar's own result only as `scanner_status_reported_result`.",
        "- Skip-scan with a zero-byte reused scan file plus an empty scanner-status sidecar now keeps `missing_scan_output` as the controlling result while preserving the empty-sidecar fact only as scanner-status metadata.",
        "- Skip-scan with a zero-byte reused scan file plus an unreadable scanner-status sidecar now keeps `missing_scan_output` as the controlling result while preserving the sidecar parse failure only as scanner-status metadata.",
        "- Skip-scan with a malformed reused scan file now stays in `invalid_scan_output` with explicit fallback metadata and no fallback-derived `scanner_status_reported_result`.",
        "- Skip-scan with a malformed reused scan file plus a readable scanner-status sidecar now keeps `invalid_scan_output` as the controlling result while preserving the sidecar's own result only as `scanner_status_reported_result`.",
        "- Skip-scan with a malformed reused scan file plus an empty scanner-status sidecar now keeps `invalid_scan_output` as the controlling result while preserving the empty-sidecar fact only as scanner-status metadata.",
        "- Skip-scan with a malformed reused scan file plus an unreadable scanner-status sidecar now keeps `invalid_scan_output` as the controlling result while preserving the sidecar parse failure only as scanner-status metadata.",
        "- Skip-scan with a readable but non-list reused scan file now stays in `invalid_scan_output` with explicit shape-error metadata and no fallback-derived `scanner_status_reported_result`.",
        "- Skip-scan with a readable but non-list reused scan file plus a readable scanner-status sidecar now keeps `invalid_scan_output` as the controlling result while preserving the sidecar's own result only as `scanner_status_reported_result`.",
        "- Skip-scan with a readable but non-list reused scan file plus an empty scanner-status sidecar now keeps `invalid_scan_output` as the controlling result while preserving the empty-sidecar fact only as scanner-status metadata.",
        "- Skip-scan with a readable but non-list reused scan file plus an unreadable scanner-status sidecar now keeps `invalid_scan_output` as the controlling result while preserving the sidecar parse failure only as scanner-status metadata.",
        "- Skip-scan reuse with a BET recommendation still lands in `bets_ready`.",
        "- Cache-only runs with missing day files still land in an explicit `cache_only_miss` operational-limit branch instead of looking like a clean quiet day.",
        "- API-access failures that complete from stale cache now keep `scanner_api_access_failure=true`, the HTTP/action/recheck fields, stale-cache fallback metadata, and `observation_reason=api_access_failure` instead of looking like a clean quiet day.",
        "- Scanner failures still degrade to an empty scan file, keep the pipeline alive, classify as `scanner_failed_empty_run`, and publish `scan_input_empty_fallback_*` fields so downstream helpers can tell the empty scan file was a protective fallback rather than a clean no-hit scanner output.",
        "- Scanner success without a scan-output file now publishes `scanner_result=missing_scan_output`, preserves the sidecar's reported result separately, and uses `observation_reason=missing_scan_output` instead of reading like clean no qualifiers.",
        "- Empty scanner-status sidecars now publish `scanner_status_state=empty`, `scanner_result=scanner_status_empty`, and an operational-limit reason instead of reading like clean quiet days.",
        "- Unreadable scanner-status sidecars now preserve scan/recommendation activity while publishing `scanner_status_state=unreadable`, `scanner_result=scanner_status_unreadable`, and an operational-limit reason.",
        "- Readable but non-object scanner-status sidecars now preserve scan/recommendation activity while publishing `scanner_status_state=readable`, `scanner_result=scanner_status_invalid_shape`, `scanner_status_error`, and an operational-limit reason.",
        "- Partial-cache empty runs still stay distinct from clean-empty runs instead of reading like full-coverage zero-hit days.",
        "- Partial-cache runs with surviving activity still keep the partial-cache branch instead of reading like a clean empty day.",
        "- The saved pipeline sidecar now also carries explicit `observation_scope` / `observation_reason`, `valid_evidence_scope`, prose `evidence_boundary`, and structured `evidence_boundary_metadata` fields, while CLI stdout prints `valid_evidence_scope` plus the same evidence boundary, so downstream operator helpers and copied logs can distinguish cache misses, empty/unreadable/invalid-shape scanner-status sidecars, partial-cache reads, true clean-empty runs, and pipeline failures without fragile string inference or over-reading workflow status as live edge evidence, OP_REFINED_K7 / Phase 8 promotion evidence, odds-only XGBoost reopening evidence, BAQ/BEL substitution evidence, or real-money evidence.",
        "- Hits plus NO BET recommendations still classify as `signals_logged_no_bet` instead of overpromoting the day to bets ready.",
        "- Recommender failures now keep the upstream scanner counts plus `last_completed_stage=scanner` in the saved `pipeline_error` status sidecar, while clearing stale recommendation summaries, plan artifacts, and non-reuse prediction CSVs before the failed recommender can leave old tickets/scored-race context behind.",
        "- Logger failures now keep the built recommendation counts plus the pre-error `bets_ready` / `signals_logged_no_bet` context with `last_completed_stage=recommender`.",
        "",
        "## Bottom Line",
        "",
        "- Green here means the source-layer paper-trade pipeline still keeps cache-only misses, API-access stale-cache fallbacks, skip-scan missing-input, zero-byte-input, malformed-input, and invalid-shape-input fallbacks, scanner-failure and missing-output empty-file fallbacks, recommender-failure stale recommendation/prediction cleanup, empty/unreadable/invalid-shape scanner-status sidecars, partial-cache empties, clean-empty runs, activity-bearing partial-cache runs, and downstream recommender/logger failures operationally distinct in the saved machine-readable status sidecar.",
        "- It does not mean the lane found a new edge; it means the scan -> recommend -> log status contract is still honest enough for Cole to interpret empty or broken live runs safely, with the JSON and stdout carrying the same workflow-only evidence boundary.",
        "",
        "## Sources",
        "",
    ])
    for row in results:
        lines.append(f"- `{row['stdout']}`")
        lines.append(f"- `{row['status_output']}`")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    for row in results:
        print(f"PASS {row['name']}: {row['status_output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
