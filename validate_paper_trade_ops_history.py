#!/usr/bin/env python3
"""
Fixture-driven validation for paper_trade_ops_history.py.

Purpose:
- keep the rolling ops-history bucket logic reproducible
- validate representative no-target, active-target, limited-coverage, hit-found, and issue days
- confirm the report preserves honest takeaways instead of softening operational failures
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

import paper_trade_ops_history as ptoh

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "paper_trade_ops_history.py"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "ops_history_fixture"
RUNS_ROOT = FIXTURE_ROOT / "out" / "daily_portfolio_runs"
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_ops_history"
OUT_MD = OUT_DIR / "paper_trade_ops_history_validation.md"
OUT_JSON = OUT_DIR / "paper_trade_ops_history_validation.json"
LIVE_MD = BASE / "OPS_HISTORY.md"
LIVE_CSV = BASE / "ops_history.csv"
REBUILD_COMMAND = "python3 validate_paper_trade_ops_history.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade ops-history validator",
    "valid_evidence_scope": ptoh.OPS_HISTORY_VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "isolated ops-history fixture daily-run folders",
        "live OPS_HISTORY.md and ops_history.csv source-layer rebuilds",
        "paper_trade_ops_history.py",
        "forward_evidence_scorecard.json decision_gate_minimums",
    ],
    "valid_use": "rolling operator recap validation for calendar state, activity buckets, and operational failure modes",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "ops_history_validator_passes_are_operational_recap_metadata_only": True,
    "non_goals": [
        "do not treat no-target days as rules performance evidence",
        "do not treat clean-empty or cache/partial-cache buckets as ROI-complete observations",
        "do not treat issue-day routing as promotion readiness",
        "do not promote OP_REFINED_K7 or Phase 8 from ops-history streaks",
        "do not substitute BAQ for BEL",
        "do not treat rolling ops recap cleanliness as real-money evidence",
    ],
}


NO_TARGET_PREFLIGHT = {
    "api_ok": True,
    "calendar_state": "NO TARGETS",
    "calendar_reason": "no_targets",
    "has_targets": False,
    "relevant_tracks": [],
    "shadow_tracks": ["KEE"],
    "total_cards": 18,
    "error": None,
    "note": "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 18 NYRA card(s). Shadow-only tracks present: KEE.",
}

ACTIVE_PREFLIGHT = {
    "api_ok": True,
    "calendar_state": "ACTIVE TARGETS",
    "calendar_reason": "active_targets",
    "has_targets": True,
    "relevant_tracks": ["OP", "CD"],
    "shadow_tracks": [],
    "total_cards": 18,
    "error": None,
    "note": "Preflight context: primary paper-basket target tracks racing today: OP, CD.",
}

UPSTREAM_ERROR_PREFLIGHT = {
    "api_ok": False,
    "calendar_state": "UNKNOWN",
    "calendar_reason": "upstream_error",
    "has_targets": False,
    "relevant_tracks": [],
    "shadow_tracks": [],
    "total_cards": 0,
    "error": "403 Client Error: Forbidden for url: https://brk0201-iapi-webservice.nyrabets.com/ListCards.ashx",
    "note": "Preflight context: NYRA preflight check failed (403 Client Error: Forbidden for url: https://brk0201-iapi-webservice.nyrabets.com/ListCards.ashx). Treat calendar state as unknown.",
}


EXPECTED = {
    "2026-06-05": {
        "calendar_state": "UNKNOWN",
        "day_bucket": "ISSUE",
        "primary_state": "SCANNER API ACCESS FAILURE",
        "takeaway": "Primary lane scanner API access failure before producing a usable lane result. Detail: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx. Treat this as API-access-failure operator context only, not a no-target, clean-empty, settled ROI, promotion, live-profitability, or real-money evidence. Stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx. Sidecar action: refresh_daily_wrapper_before_evidence_read. Recheck command: ./run_daily_portfolio_observation.sh. Refresh the daily wrapper and re-check sidecars before treating the day as evidence.",
    },
    "2026-06-04": {
        "calendar_state": "UNKNOWN",
        "day_bucket": "ISSUE",
        "primary_state": "SCANNER API ACCESS FAILURE",
        "takeaway": "Primary lane scanner API access failure before producing a usable lane result. Detail: 403 Client Error: Forbidden for url: https://brk0201-iapi-webservice.nyrabets.com/ListCards.ashx. Treat this as API-access-failure operator context only, not a no-target, clean-empty, settled ROI, promotion, live-profitability, or real-money evidence. Sidecar action: refresh_daily_wrapper_before_evidence_read. Recheck command: ./run_daily_portfolio_observation.sh. Refresh the daily wrapper and re-check sidecars before treating the day as evidence.",
    },
    "2026-06-03": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ISSUE",
        "primary_state": "INVALID SHAPE",
        "takeaway": "Primary lane pipeline status sidecar has invalid JSON shape. Refresh the daily wrapper before drawing conclusions.",
    },
    "2026-06-02": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ISSUE",
        "primary_state": "SCANNER INVALID SHAPE",
        "takeaway": "Primary lane scanner status sidecar has invalid JSON shape. Refresh the daily wrapper before drawing conclusions.",
    },
    "2026-06-01": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ISSUE",
        "primary_state": "SCANNER RECORDED INVALID SHAPE",
        "takeaway": "Primary lane scanner status sidecar was recorded invalid-shape by the pipeline. Refresh the daily wrapper before drawing conclusions.",
    },
    "2026-05-31": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ISSUE",
        "primary_state": "SCANNER EMPTY",
        "takeaway": "Primary lane scanner status sidecar was empty. Refresh the daily wrapper before drawing conclusions.",
    },
    "2026-05-30": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ISSUE",
        "primary_state": "PIPELINE EMPTY",
        "takeaway": "Primary lane pipeline status sidecar was empty. Refresh the daily wrapper before drawing conclusions.",
    },
    "2026-05-29": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ACTIVE, LIMITED COVERAGE WITH ACTIVITY",
        "primary_state": "PARTIAL CACHE WITH ACTIVITY",
        "takeaway": "OP/CD were active and the primary lane still found 1 hit(s) and turned them into 1 recommendation(s) on partial cache coverage, so keep the activity but do not treat it like a full live read. 4 missing race detail cache file(s). Re-run live before leaning on it as evidence.",
    },
    "2026-05-28": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ACTIVE, LIMITED COVERAGE WITH ACTIVITY",
        "primary_state": "PARTIAL CACHE WITH ACTIVITY",
        "takeaway": "OP/CD were active and the primary lane still found 1 hit(s) and turned them into 1 recommendation(s) on partial cache coverage, so keep the activity but do not treat it like a full live read. 3 missing race detail cache file(s). Re-run live before leaning on it as evidence.",
    },
    "2026-05-27": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ACTIVE, LIMITED COVERAGE WITH ACTIVITY",
        "primary_state": "PARTIAL CACHE WITH ACTIVITY",
        "takeaway": "OP/CD were active and the primary lane still found 1 hit(s) and turned them into 1 recommendation(s) on partial cache coverage, so keep the activity but do not treat it like a full live read. 1 missing race detail cache file(s). Re-run live before leaning on it as evidence.",
    },
    "2026-05-26": {
        "calendar_state": "NO TARGETS",
        "day_bucket": "NO TARGETS",
        "primary_state": "CACHE MISS (CACHE-ONLY)",
        "takeaway": "No active OP/CD cards. The cache-only run missed today's cache files, but the quiet day is still explained by the race calendar, not by a rules miss.",
    },
    "2026-05-25": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "BETS READY",
        "primary_state": "BETS READY (2 bets)",
        "takeaway": "Primary lane produced 2 bet(s). Review the lane artifacts before the races go off.",
    },
    "2026-05-24": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ISSUE",
        "primary_state": "UNREADABLE",
        "takeaway": "Primary lane status artifacts were missing or unreadable. Refresh the daily wrapper before drawing conclusions.",
    },
    "2026-05-23": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ACTIVE, HITS FOUND",
        "primary_state": "SIGNALS, NO BET",
        "takeaway": "OP/CD were active and the primary lane found 1 hit(s), but nothing reached a bet-ready state.",
    },
    "2026-05-22": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ACTIVE, LIMITED COVERAGE",
        "primary_state": "PARTIAL CACHE EMPTY",
        "takeaway": "OP/CD were active, but the latest primary-lane read finished empty on partial cache coverage. 2 missing race detail cache file(s). Re-run live before treating it as a true zero-hit day.",
    },
    "2026-05-21": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ACTIVE, ZERO HITS",
        "primary_state": "CLEAN EMPTY",
        "takeaway": "OP/CD were active, but the primary lane found zero qualifying hits.",
    },
    "2026-05-20": {
        "calendar_state": "NO TARGETS",
        "day_bucket": "NO TARGETS",
        "primary_state": "CACHE MISS (CACHE-ONLY)",
        "takeaway": "No active OP/CD cards. The cache-only run missed today's cache files, but the quiet day is still explained by the race calendar, not by a rules miss.",
    },
    "2026-05-19": {
        "calendar_state": "UNREADABLE",
        "day_bucket": "UNKNOWN CALENDAR",
        "primary_state": "CLEAN EMPTY",
        "takeaway": "Preflight calendar context was unreadable, so treat the daily result as operationally ambiguous.",
    },
    "2026-05-18": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ISSUE",
        "primary_state": "RECOMMENDER FAILURE",
        "takeaway": "Primary lane hit a recommender failure. After scanner completed, 1 hit(s) were already found before the failure. Error type: RuntimeError. Detail: fixture recommender crash. Refresh the daily wrapper and re-check sidecars before treating the day as evidence.",
    },
    "2026-05-17": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ISSUE",
        "primary_state": "LOGGER FAILURE",
        "takeaway": "Primary lane hit a logger failure. After recommender completed, 1 recommendation(s) were already built and 1 BET recommendation(s) were ready (context: bets_ready) before the failure. Error type: ValueError. Detail: fixture logger crash. Refresh the daily wrapper and re-check sidecars before treating the day as evidence.",
    },
    "2026-05-16": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ACTIVE, ZERO HITS",
        "primary_state": "CLEAN EMPTY",
        "takeaway": "OP/CD were active, but the primary lane found zero qualifying hits.",
    },
    "2026-05-15": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ISSUE",
        "primary_state": "SCANNER RECORDED EMPTY",
        "takeaway": "Primary lane scanner status sidecar was recorded empty by the pipeline. Refresh the daily wrapper before drawing conclusions.",
    },
    "2026-05-14": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ISSUE",
        "primary_state": "SCANNER RECORDED UNREADABLE",
        "takeaway": "Primary lane scanner status sidecar was recorded unreadable by the pipeline. Refresh the daily wrapper before drawing conclusions.",
    },
    "2026-05-13": {
        "calendar_state": "OP/CD ACTIVE",
        "day_bucket": "ISSUE",
        "primary_state": "MISSING SCAN OUTPUT",
        "takeaway": "Primary lane scan-output artifact was missing after scanner status reported no_qualifiers; pipeline used a safe empty [] fallback, so this is not a clean no-qualifier observation. Refresh the daily wrapper before treating the day as a clean no-qualifier observation.",
    },
}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, indent=2) + "\n")


def pipeline_status(observation_result: str, *, hits: int = 0, recs: int = 0, bets: int = 0,
                    cache_only: bool = False, result: str = "ok", scanner_result: str | None = None,
                    scanner_error: str | None = None, observation_reason: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "result": result,
        "stage": "done",
        "observation_result": observation_result,
        "scan_hit_count": hits,
        "recommendation_count": recs,
        "bet_count": bets,
        "cache_only": cache_only,
    }
    if scanner_result is not None:
        payload["scanner_result"] = scanner_result
    if scanner_error is not None:
        payload["scanner_error"] = scanner_error
    if observation_reason is not None:
        payload["observation_reason"] = observation_reason
    return payload


def scanner_status(result: str, *, cache_only: bool = False, partial_cache: bool = False,
                   error: str | None = None, missing_race_detail_cache_skips: int = 0) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "result": result,
        "cache_only": cache_only,
        "partial_cache": partial_cache,
        "missing_race_detail_cache_skips": missing_race_detail_cache_skips,
        "card_count": 4,
        "race_count": 18,
    }
    if error is not None:
        payload["error"] = error
    return payload


def make_case(run_date: str, *, preflight: dict[str, Any], primary_status: dict[str, Any] | None,
              shadow_status: dict[str, Any], primary_scanner: dict[str, Any] | None = None,
              shadow_scanner: dict[str, Any] | None = None, primary_scanner_relpath: str | None = None,
              shadow_scanner_relpath: str | None = None, primary_default_scanner: dict[str, Any] | None = None,
              shadow_default_scanner: dict[str, Any] | None = None, malformed_primary: bool = False,
              malformed_preflight: bool = False, remove_preflight_txt: bool = False,
              empty_primary_status: bool = False, empty_primary_scanner: bool = False) -> Path:
    run_root = RUNS_ROOT / run_date
    preflight_payload = {"date": run_date, "checked_at": f"{run_date} 11:00", **preflight}
    write_text(run_root / "preflight_note.txt", preflight_payload["note"] + "\n")
    if malformed_preflight:
        write_text(run_root / "preflight_note.json", "{bad json\n")
    else:
        write_json(run_root / "preflight_note.json", preflight_payload)
    if remove_preflight_txt:
        (run_root / "preflight_note.txt").unlink()
    write_text(run_root / "daily_summary.txt", f"Fixture daily summary for {run_date}.\n")

    (run_root / "phase7_current_paper").mkdir(parents=True, exist_ok=True)
    (run_root / "phase8_shadow").mkdir(parents=True, exist_ok=True)

    primary_scanner_path = run_root / "phase7_current_paper" / (primary_scanner_relpath or "live_scan.status.json")
    shadow_scanner_path = run_root / "phase8_shadow" / (shadow_scanner_relpath or "live_scan.status.json")

    primary_status_payload = dict(primary_status) if primary_status is not None else None
    if primary_status_payload is not None and (primary_scanner is not None or empty_primary_scanner):
        primary_status_payload.setdefault("scanner_status_path", str(primary_scanner_path))
    shadow_status_payload = dict(shadow_status)
    if shadow_scanner is not None:
        shadow_status_payload.setdefault("scanner_status_path", str(shadow_scanner_path))

    if empty_primary_status:
        write_text(run_root / "phase7_current_paper" / "pipeline_status.json", "")
    elif malformed_primary:
        write_text(run_root / "phase7_current_paper" / "pipeline_status.json", "{bad json\n")
    elif primary_status_payload is not None:
        write_json(run_root / "phase7_current_paper" / "pipeline_status.json", primary_status_payload)

    write_json(run_root / "phase8_shadow" / "pipeline_status.json", shadow_status_payload)

    if empty_primary_scanner:
        write_text(primary_scanner_path, "")
    elif primary_scanner is not None:
        write_json(primary_scanner_path, primary_scanner)
    if shadow_scanner is not None:
        write_json(shadow_scanner_path, shadow_scanner)
    if primary_default_scanner is not None:
        write_json(run_root / "phase7_current_paper" / "live_scan.status.json", primary_default_scanner)
    if shadow_default_scanner is not None:
        write_json(run_root / "phase8_shadow" / "live_scan.status.json", shadow_default_scanner)
    return run_root


def assert_contains(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"{label}: expected to find {needle!r}")


def display_scorecard_path(scorecard_json: Path) -> str:
    try:
        return str(scorecard_json.relative_to(BASE))
    except ValueError:
        return str(scorecard_json)


def require_positive_non_bool_int(value: Any, *, field_name: str, source_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, field_name: str, source_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise AssertionError(f"{source_name} {field_name} must be a string list")
    return value


def read_scorecard_gate_minimums(scorecard_json: Path = SCORECARD_JSON) -> dict[str, Any]:
    source_name = display_scorecard_path(scorecard_json)
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
        field_name="decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
        source_name=source_name,
    )
    phase8_min = require_positive_non_bool_int(
        phase8.get("min_roi_complete_settled_observations"),
        field_name="decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
        source_name=source_name,
    )
    real_money_min = require_positive_non_bool_int(
        real_money.get("min_total_settled_observations_with_usable_roi"),
        field_name="decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
        source_name=source_name,
    )
    real_money_requires = require_string_list(
        real_money.get("also_requires"),
        field_name="decision_gate_minimums.real_money_discussion.also_requires",
        source_name=source_name,
    )
    if NO_BAQ_AS_BEL_PREREQUISITE not in real_money_requires:
        raise AssertionError(
            f"{source_name} decision_gate_minimums.real_money_discussion.also_requires "
            f"must include {NO_BAQ_AS_BEL_PREREQUISITE}"
        )
    return {
        "source": source_name,
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_also_requires": real_money_requires,
        "real_money_no_baq_as_bel_required": True,
        "evidence_boundary": (
            "ops-history day buckets, streaks, clean-empty rows, no-target rows, and issue routing "
            "do not count toward anchor-displacement, Phase 8 promotion-review, or real-money "
            "discussion gates"
        ),
    }


def guardrail(condition: bool, check: str, detail: str) -> dict[str, str]:
    if not condition:
        raise AssertionError(f"{check}: {detail}")
    return {"check": check, "status": "pass", "detail": detail}


def configure_output_paths(fixture_root: Path, out_dir: Path) -> None:
    global FIXTURE_ROOT, RUNS_ROOT, OUT_DIR, OUT_MD, OUT_JSON
    FIXTURE_ROOT = fixture_root
    RUNS_ROOT = FIXTURE_ROOT / "out" / "daily_portfolio_runs"
    OUT_DIR = out_dir
    OUT_MD = OUT_DIR / "paper_trade_ops_history_validation.md"
    OUT_JSON = OUT_DIR / "paper_trade_ops_history_validation.json"


def assert_scorecard_failure_before_artifacts(
    *,
    scorecard_json: Path,
    mutation: Any,
    expected_error: str,
    check: str,
    detail: str,
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="ops_history_scorecard_guardrail_") as tmp_name:
        tmpdir = Path(tmp_name)
        bad_scorecard = tmpdir / "forward_evidence_scorecard.json"
        bad_payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
        mutation(bad_payload)
        bad_scorecard.write_text(json.dumps(bad_payload, indent=2) + "\n", encoding="utf-8")
        nested_fixture_root = tmpdir / "nested" / "fixture"
        nested_out_dir = tmpdir / "nested" / "out"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(bad_scorecard),
                "--fixture-root",
                str(nested_fixture_root),
                "--out-dir",
                str(nested_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        combined_output = result.stdout + result.stderr
        if result.returncode == 0:
            raise AssertionError(f"{check}: malformed scorecard unexpectedly passed")
        if expected_error not in combined_output:
            raise AssertionError(
                f"{check}: expected error {expected_error!r}, got stdout={result.stdout!r} stderr={result.stderr!r}"
            )
        if nested_fixture_root.exists() or nested_out_dir.exists():
            raise AssertionError(f"{check}: malformed scorecard created fixture/report artifacts")
    return guardrail(True, check, detail)


def scorecard_no_artifact_guardrails(scorecard_json: Path) -> list[dict[str, str]]:
    return [
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["anchor_displacement"].__setitem__(
                "min_roi_complete_settled_observations",
                True,
            ),
            expected_error=(
                "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check="scorecard_boolean_gate_floor_fails_before_ops_history_artifacts",
            detail=(
                "a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before "
                "nested ops-history fixture/report artifacts are created"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["phase8_promotion_review"].__setitem__(
                "min_roi_complete_settled_observations",
                0,
            ),
            expected_error=(
                "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check="scorecard_phase8_gate_floor_fails_before_ops_history_artifacts",
            detail=(
                "a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails before "
                "nested ops-history fixture/report artifacts are created"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                "min_total_settled_observations_with_usable_roi",
                0,
            ),
            expected_error=(
                "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi "
                "must be a positive non-boolean integer"
            ),
            check="scorecard_real_money_gate_floor_fails_before_ops_history_artifacts",
            detail=(
                "a non-positive real-money discussion floor in forward_evidence_scorecard.json fails before "
                "nested ops-history fixture/report artifacts are created"
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
            expected_error=(
                "decision_gate_minimums.real_money_discussion.also_requires "
                f"must include {NO_BAQ_AS_BEL_PREREQUISITE}"
            ),
            check="scorecard_missing_no_baq_fails_before_ops_history_artifacts",
            detail=(
                "a scorecard missing the no-BAQ-as-BEL real-money prerequisite fails before "
                "nested ops-history fixture/report artifacts are created"
            ),
        ),
    ]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--fixture-root", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args(argv)


def build_fixture_scratch_metadata() -> dict[str, Any]:
    validation_root = (BASE / "out" / "status_validation").resolve()
    fixture_root = FIXTURE_ROOT.resolve()
    return {
        "fixture_root": str(fixture_root),
        "fixture_root_relative": str(FIXTURE_ROOT.relative_to(BASE)),
        "fixture_root_is_project_local": fixture_root == validation_root or validation_root in fixture_root.parents,
        "fixture_root_cleared_before_fixture_run": True,
    }


def validate_live_surfaces() -> dict[str, Any]:
    live_rows = ptoh.collect_rows(ptoh.DEFAULT_RUNS_ROOT, limit=14)
    rebuilt_dir = FIXTURE_ROOT / "_live_rebuilt"
    rebuilt_dir.mkdir(parents=True, exist_ok=True)
    rebuilt_csv = rebuilt_dir / "ops_history.csv"
    rebuilt_md = rebuilt_dir / "OPS_HISTORY.md"
    ptoh.write_csv(rebuilt_csv, live_rows)
    ptoh.write_md(rebuilt_md, live_rows, limit=14)

    if not LIVE_CSV.exists():
        raise AssertionError(f"missing live ops-history CSV surface: {LIVE_CSV}")
    if not LIVE_MD.exists():
        raise AssertionError(f"missing live ops-history markdown surface: {LIVE_MD}")

    live_csv_text = LIVE_CSV.read_text(encoding="utf-8")
    live_md_text = LIVE_MD.read_text(encoding="utf-8")
    expected_csv_text = rebuilt_csv.read_text(encoding="utf-8")
    expected_md_text = rebuilt_md.read_text(encoding="utf-8")
    live_summary_counts = ptoh.summarize_rows(live_rows)

    if live_csv_text != expected_csv_text:
        raise AssertionError("live ops_history.csv drifted from the current source-layer rebuild")
    if live_md_text != expected_md_text:
        raise AssertionError("live OPS_HISTORY.md drifted from the current source-layer rebuild")
    assert_contains(
        live_md_text,
        "`OP_DURABLE_K7` remains the anchor and `CD_CORE_K8` remains the primary OP/CD paper-basket companion",
        "live ops hierarchy context",
    )
    assert_contains(
        live_md_text,
        "BAQ remains not treated as BEL; this ops rollup is not settled ROI, live profitability, promotion readiness, or real-money evidence.",
        "live ops hierarchy/evidence boundary",
    )
    assert_contains(
        live_md_text,
        f"valid_evidence_scope={ptoh.OPS_HISTORY_VALID_EVIDENCE_SCOPE}",
        "live ops source evidence scope",
    )
    assert_contains(
        live_md_text,
        ptoh.OPS_HISTORY_EVIDENCE_BOUNDARY_TEXT,
        "live ops source evidence boundary text",
    )

    latest_row = live_rows[0] if live_rows else None
    return {
        "case": "live_current_surface",
        "scenario": "default OPS_HISTORY markdown and CSV surfaces match the latest live rebuild",
        "run_count": len(live_rows),
        "latest_date": latest_row["date"] if latest_row else None,
        "latest_calendar_state": latest_row["calendar_state"] if latest_row else None,
        "day_bucket": latest_row["day_bucket"] if latest_row else None,
        "summary_counts": live_summary_counts,
        "ops_history_md": str(LIVE_MD.relative_to(BASE)),
        "ops_history_csv": str(LIVE_CSV.relative_to(BASE)),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args([] if argv is None else argv)
    scorecard_json = args.scorecard_json.expanduser().resolve()
    configure_output_paths(
        fixture_root=args.fixture_root.expanduser().resolve(),
        out_dir=args.out_dir.expanduser().resolve(),
    )
    scorecard_gates = read_scorecard_gate_minimums(scorecard_json)
    scorecard_guardrails = scorecard_no_artifact_guardrails(scorecard_json)

    if FIXTURE_ROOT.exists():
        shutil.rmtree(FIXTURE_ROOT)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scratch = build_fixture_scratch_metadata()

    clean_shadow = pipeline_status("clean_empty_run")

    make_case(
        "2026-06-05",
        preflight=UPSTREAM_ERROR_PREFLIGHT,
        primary_status={
            **pipeline_status(
                "scanner_failed_empty_run",
                scanner_result="scanner_error",
                scanner_error="403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
                observation_reason="api_access_failure",
            ),
            "scanner_http_status": 403,
            "scanner_api_access_failure": True,
            "scanner_api_failure_class": "api_access_failure",
            "scanner_api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
            "scanner_api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
            "scanner_stale_cache_fallback_applied": True,
            "scanner_stale_cache_fallback_count": 2,
            "scanner_stale_cache_fallback_kind": "cards",
            "scanner_stale_cache_fallback_error_type": "HTTPError",
            "scanner_stale_cache_fallback_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
        },
        shadow_status=clean_shadow,
        primary_scanner={
            **scanner_status(
                "scanner_error",
                error="403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
            ),
            "http_status": 403,
            "api_access_failure": True,
            "api_failure_class": "api_access_failure",
            "api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
            "api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
            "stale_cache_fallback_applied": True,
            "stale_cache_fallback_count": 2,
            "stale_cache_fallback_kind": "cards",
            "stale_cache_fallback_error_type": "HTTPError",
            "stale_cache_fallback_error": "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx",
        },
    )
    make_case(
        "2026-06-04",
        preflight=UPSTREAM_ERROR_PREFLIGHT,
        primary_status={
            **pipeline_status(
                "scanner_failed_empty_run",
                scanner_result="scanner_error",
                scanner_error="403 Client Error: Forbidden for url: https://brk0201-iapi-webservice.nyrabets.com/ListCards.ashx",
                observation_reason="api_access_failure",
            ),
            "scanner_http_status": 403,
            "scanner_api_access_failure": True,
            "scanner_api_failure_class": "api_access_failure",
            "scanner_api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
            "scanner_api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
        },
        shadow_status=clean_shadow,
        primary_scanner={
            **scanner_status(
                "scanner_error",
                error="403 Client Error: Forbidden for url: https://brk0201-iapi-webservice.nyrabets.com/ListCards.ashx",
            ),
            "http_status": 403,
            "api_access_failure": True,
            "api_failure_class": "api_access_failure",
            "api_failure_operator_action": "refresh_daily_wrapper_before_evidence_read",
            "api_failure_recheck_command": "./run_daily_portfolio_observation.sh",
        },
    )
    make_case(
        "2026-06-03",
        preflight=ACTIVE_PREFLIGHT,
        primary_status=None,
        shadow_status=clean_shadow,
    )
    write_text(RUNS_ROOT / "2026-06-03" / "phase7_current_paper" / "pipeline_status.json", "[]\n")
    make_case(
        "2026-06-02",
        preflight=ACTIVE_PREFLIGHT,
        primary_status=pipeline_status("clean_empty_run"),
        shadow_status=clean_shadow,
    )
    write_text(RUNS_ROOT / "2026-06-02" / "phase7_current_paper" / "live_scan.status.json", "[]\n")
    make_case(
        "2026-06-01",
        preflight=ACTIVE_PREFLIGHT,
        primary_status={
            **pipeline_status(
                "scanner_status_unavailable_invalid_shape_run",
                scanner_result="scanner_status_invalid_shape",
                scanner_error="expected scanner-status JSON object, got list",
                observation_reason="scanner_status_invalid_shape",
            ),
            "scanner_status_state": "invalid_shape",
            "scanner_status_error": "expected scanner-status JSON object, got list",
        },
        shadow_status=clean_shadow,
    )

    make_case(
        "2026-05-31",
        preflight=ACTIVE_PREFLIGHT,
        primary_status=pipeline_status("clean_empty_run"),
        shadow_status=clean_shadow,
        empty_primary_scanner=True,
    )
    make_case(
        "2026-05-30",
        preflight=ACTIVE_PREFLIGHT,
        primary_status=None,
        shadow_status=clean_shadow,
        empty_primary_status=True,
    )
    make_case(
        "2026-05-20",
        preflight=NO_TARGET_PREFLIGHT,
        primary_status=pipeline_status(
            "scanner_failed_empty_run",
            cache_only=True,
            scanner_result="scanner_error",
            scanner_error="No cached data found for today's cards.",
        ),
        shadow_status=clean_shadow,
        primary_scanner=scanner_status(
            "scanner_error",
            cache_only=True,
            error="No cached data found for today's cards.",
        ),
    )
    make_case(
        "2026-05-21",
        preflight=ACTIVE_PREFLIGHT,
        primary_status=pipeline_status("clean_empty_run"),
        shadow_status=clean_shadow,
    )
    make_case(
        "2026-05-22",
        preflight=ACTIVE_PREFLIGHT,
        primary_status=pipeline_status("partial_cache_empty_run", cache_only=True),
        shadow_status=clean_shadow,
        primary_scanner=scanner_status(
            "partial_cache_no_qualifiers",
            cache_only=True,
            partial_cache=True,
            missing_race_detail_cache_skips=2,
        ),
    )
    make_case(
        "2026-05-23",
        preflight=ACTIVE_PREFLIGHT,
        primary_status=pipeline_status("signals_logged_no_bet", hits=1, recs=1),
        shadow_status=clean_shadow,
    )
    make_case(
        "2026-05-29",
        preflight=ACTIVE_PREFLIGHT,
        primary_status={
            **pipeline_status(
                "partial_cache_with_activity",
                hits=1,
                recs=1,
                scanner_result="partial_cache_missing_detail",
                observation_reason="partial_cache_with_activity",
            ),
            "scanner_status_path": str(
                (RUNS_ROOT / "2026-05-29" / "phase7_current_paper" / "renamed_live_scan.status.json").relative_to(BASE)
            ),
        },
        shadow_status=clean_shadow,
        primary_scanner=scanner_status(
            "partial_cache_missing_detail",
            partial_cache=True,
            missing_race_detail_cache_skips=4,
        ),
        primary_scanner_relpath="renamed_live_scan.status.json",
    )
    make_case(
        "2026-05-28",
        preflight=ACTIVE_PREFLIGHT,
        primary_status={
            **pipeline_status(
                "partial_cache_with_activity",
                hits=1,
                recs=1,
                scanner_result="partial_cache_missing_detail",
                observation_reason="partial_cache_with_activity",
            ),
            "scanner_status_path": "phase7_current_paper/renamed_live_scan.status.json",
        },
        shadow_status=clean_shadow,
        primary_scanner=scanner_status(
            "partial_cache_missing_detail",
            partial_cache=True,
            missing_race_detail_cache_skips=3,
        ),
        primary_scanner_relpath="renamed_live_scan.status.json",
    )
    make_case(
        "2026-05-27",
        preflight=ACTIVE_PREFLIGHT,
        primary_status={
            **pipeline_status(
                "partial_cache_with_activity",
                hits=1,
                recs=1,
                scanner_result="partial_cache_missing_detail",
                observation_reason="partial_cache_with_activity",
            ),
            "scanner_status_path": "renamed_live_scan.status.json",
        },
        shadow_status=clean_shadow,
        primary_scanner=scanner_status(
            "partial_cache_missing_detail",
            partial_cache=True,
            missing_race_detail_cache_skips=1,
        ),
        primary_scanner_relpath="renamed_live_scan.status.json",
        primary_default_scanner=scanner_status(
            "partial_cache_missing_detail",
            partial_cache=True,
            missing_race_detail_cache_skips=9,
        ),
    )
    make_case(
        "2026-05-26",
        preflight={
            **NO_TARGET_PREFLIGHT,
            "note": "JSON-only preflight note: no active OP/CD cards today; KEE is shadow-only.",
        },
        primary_status=pipeline_status(
            "scanner_failed_empty_run",
            cache_only=True,
            scanner_result="scanner_error",
            scanner_error="No cached data found for today's cards.",
        ),
        shadow_status=clean_shadow,
        primary_scanner=scanner_status(
            "scanner_error",
            cache_only=True,
            error="No cached data found for today's cards.",
        ),
        remove_preflight_txt=True,
    )
    make_case(
        "2026-05-25",
        preflight=ACTIVE_PREFLIGHT,
        primary_status=pipeline_status("bets_ready", hits=2, recs=2, bets=2),
        shadow_status=clean_shadow,
    )
    make_case(
        "2026-05-24",
        preflight=ACTIVE_PREFLIGHT,
        primary_status=None,
        shadow_status=clean_shadow,
        malformed_primary=True,
    )
    make_case(
        "2026-05-19",
        preflight=ACTIVE_PREFLIGHT,
        primary_status=pipeline_status("clean_empty_run"),
        shadow_status=clean_shadow,
        malformed_preflight=True,
    )
    make_case(
        "2026-05-18",
        preflight=ACTIVE_PREFLIGHT,
        primary_status={
            **pipeline_status("signals_logged_no_bet", hits=1, recs=0, result="pipeline_error"),
            "stage": "recommender",
            "last_completed_stage": "scanner",
            "error_type": "RuntimeError",
            "error": "fixture recommender crash",
        },
        shadow_status=clean_shadow,
    )
    make_case(
        "2026-05-17",
        preflight=ACTIVE_PREFLIGHT,
        primary_status={
            **pipeline_status("bets_ready", hits=1, recs=1, bets=1, result="pipeline_error"),
            "stage": "logger",
            "last_completed_stage": "recommender",
            "error_type": "ValueError",
            "error": "fixture logger crash",
        },
        shadow_status=clean_shadow,
    )
    make_case(
        "2026-05-16",
        preflight={
            **ACTIVE_PREFLIGHT,
            "note": "JSON-only preflight note: primary paper-basket target tracks racing today: OP, CD.",
        },
        primary_status=pipeline_status("clean_empty_run"),
        shadow_status=clean_shadow,
        remove_preflight_txt=True,
    )
    make_case(
        "2026-05-15",
        preflight=ACTIVE_PREFLIGHT,
        primary_status={
            **pipeline_status(
                "scanner_status_unavailable_empty_run",
                scanner_result="scanner_status_empty",
                observation_reason="scanner_status_empty",
            ),
            "scanner_status_state": "empty",
        },
        shadow_status=clean_shadow,
    )
    make_case(
        "2026-05-14",
        preflight=ACTIVE_PREFLIGHT,
        primary_status={
            **pipeline_status(
                "scanner_status_unavailable_unreadable_run",
                scanner_result="scanner_status_unreadable",
                scanner_error="JSONDecodeError: fixture malformed scanner status",
                observation_reason="scanner_status_unreadable",
            ),
            "scanner_status_state": "unreadable",
            "scanner_status_error": "JSONDecodeError: fixture malformed scanner status",
        },
        shadow_status=clean_shadow,
    )
    make_case(
        "2026-05-13",
        preflight=ACTIVE_PREFLIGHT,
        primary_status={
            **pipeline_status(
                "scanner_failed_empty_run",
                scanner_result="missing_scan_output",
                observation_reason="missing_scan_output",
            ),
            "scanner_stage_status": "missing_scan_output",
            "scanner_status_reported_result": "no_qualifiers",
            "scan_input_empty_fallback_applied": True,
            "scan_input_empty_fallback_reason": "missing_or_empty_scan_output",
            "scan_input_state_before_empty_fallback": "missing",
            "scan_input_empty_fallback_value": "[]",
        },
        shadow_status=clean_shadow,
        primary_scanner=scanner_status("no_qualifiers"),
    )

    ops_md = FIXTURE_ROOT / "OPS_HISTORY.md"
    ops_csv = FIXTURE_ROOT / "ops_history.csv"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runs-root", str(RUNS_ROOT),
            "--md-output", str(ops_md),
            "--csv-output", str(ops_csv),
            "--limit", str(len(EXPECTED)),
        ],
        cwd=BASE,
        capture_output=True,
        text=True,
        check=True,
    )

    with ops_csv.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    if len(rows) != len(EXPECTED):
        raise AssertionError(f"expected {len(EXPECTED)} ops rows, got {len(rows)}")
    for row in rows:
        if row.get("valid_evidence_scope") != ptoh.OPS_HISTORY_VALID_EVIDENCE_SCOPE:
            raise AssertionError(f"{row.get('date')}: ops_history.csv lost valid_evidence_scope")
        if row.get("evidence_boundary_text") != ptoh.OPS_HISTORY_EVIDENCE_BOUNDARY_TEXT:
            raise AssertionError(f"{row.get('date')}: ops_history.csv lost evidence_boundary_text")

    rebuilt_rows = ptoh.collect_rows(RUNS_ROOT, limit=len(EXPECTED))
    fixture_summary_counts = ptoh.summarize_rows(rebuilt_rows)
    rebuilt_dir = FIXTURE_ROOT / "_rebuilt"
    rebuilt_dir.mkdir(parents=True, exist_ok=True)
    rebuilt_csv = rebuilt_dir / "ops_history.csv"
    rebuilt_md = rebuilt_dir / "OPS_HISTORY.md"
    ptoh.write_csv(rebuilt_csv, rebuilt_rows)
    ptoh.write_md(rebuilt_md, rebuilt_rows, limit=len(EXPECTED))

    with rebuilt_csv.open(encoding="utf-8", newline="") as fh:
        rebuilt_csv_rows = list(csv.DictReader(fh))
    if rows != rebuilt_csv_rows:
        raise AssertionError("ops_history.csv no longer matches a fresh rebuild from paper_trade_ops_history.py")
    if ops_md.read_text(encoding="utf-8") != rebuilt_md.read_text(encoding="utf-8"):
        raise AssertionError("OPS_HISTORY.md no longer matches a fresh rebuild from paper_trade_ops_history.py")
    expected_summary_counts = {
        "run_days": 24,
        "target_days": 19,
        "no_target_days": 2,
        "calendar_unknown_days": 3,
        "primary_issue_days": 13,
        "primary_activity_days": 7,
        "no_target_expected_empty_days": 2,
        "active_zero_hit_days": 2,
        "active_limited_coverage_days": 1,
        "active_limited_coverage_with_activity_days": 3,
        "active_hit_found_days": 1,
        "bets_ready_days": 1,
        "streaks": {
            "no_target": 0,
            "active_zero_hit": 0,
            "active_limited_coverage": 0,
            "active_limited_coverage_with_activity": 0,
            "active_hit_found": 0,
            "issue": 7,
        },
    }
    if fixture_summary_counts != expected_summary_counts:
        raise AssertionError(f"fixture summary counts drifted: expected {expected_summary_counts}, got {fixture_summary_counts}")

    by_date = {row["date"]: row for row in rows}
    for run_date, expected in EXPECTED.items():
        row = by_date.get(run_date)
        if row is None:
            raise AssertionError(f"missing row for {run_date}")
        if row["calendar_state"] != expected["calendar_state"]:
            raise AssertionError(f"{run_date}: expected calendar_state {expected['calendar_state']!r}, got {row['calendar_state']!r}")
        if row["day_bucket"] != expected["day_bucket"]:
            raise AssertionError(f"{run_date}: expected day_bucket {expected['day_bucket']!r}, got {row['day_bucket']!r}")
        if row["primary_state"] != expected["primary_state"]:
            raise AssertionError(f"{run_date}: expected primary_state {expected['primary_state']!r}, got {row['primary_state']!r}")
        if row["takeaway"] != expected["takeaway"]:
            raise AssertionError(f"{run_date}: expected takeaway {expected['takeaway']!r}, got {row['takeaway']!r}")

    if by_date["2026-05-26"]["preflight_note"] != "JSON-only preflight note: no active OP/CD cards today; KEE is shadow-only.":
        raise AssertionError("2026-05-26: expected json-only no-target preflight note to survive into ops-history rows")
    if by_date["2026-05-16"]["preflight_note"] != "JSON-only preflight note: primary paper-basket target tracks racing today: OP, CD.":
        raise AssertionError("2026-05-16: expected json-only active-target preflight note to survive into ops-history rows")
    if by_date["2026-05-18"]["primary_pipeline_last_completed_stage"] != "scanner":
        raise AssertionError("2026-05-18: expected recommender failure row to preserve last completed stage=scanner")
    if by_date["2026-05-17"]["primary_pipeline_last_completed_stage"] != "recommender":
        raise AssertionError("2026-05-17: expected logger failure row to preserve last completed stage=recommender")

    ops_text = ops_md.read_text(encoding="utf-8")
    assert_contains(ops_text, "Included run days: **24**", "ops summary run count")
    assert_contains(ops_text, "- No-target days: **2**", "ops summary no-target count")
    assert_contains(ops_text, "- Calendar-unknown days: **3**", "ops summary calendar-unknown count")
    assert_contains(ops_text, "- Primary-lane issue days: **13**", "ops summary issue count")
    assert_contains(ops_text, "- Active-target zero-hit days: **2**", "ops summary zero-hit count")
    assert_contains(ops_text, "- Active-target limited-coverage days: **1**", "ops summary limited-coverage count")
    assert_contains(ops_text, "- Active-target limited-coverage-with-activity days: **3**", "ops summary limited-coverage-with-activity count")
    assert_contains(ops_text, "- Active-target hit-found / no-bet days: **1**", "ops summary hit-found count")
    assert_contains(ops_text, "- Bet-ready days: **1**", "ops summary bet-ready count")
    assert_contains(ops_text, "- Consecutive active-target limited-coverage-with-activity days at the top of the log: **0**", "ops summary limited-coverage-with-activity streak")
    assert_contains(ops_text, "- Consecutive primary-issue days at the top of the log: **7**", "ops summary issue streak")
    assert_contains(ops_text, "## Live hierarchy context", "ops hierarchy context section")
    assert_contains(ops_text, "`OP_DURABLE_K7` remains the anchor and `CD_CORE_K8` remains the primary OP/CD paper-basket companion, not a Phase 8 shadow-lane promotion.", "ops hierarchy primary context")
    assert_contains(ops_text, "`OP_REFINED_K7` remains the lead same-family challenger; lane streaks or hit-found days alone do not promote OP_REFINED_K7 or any other Phase 8 pocket.", "ops hierarchy shadow context")
    assert_contains(ops_text, "BAQ remains not treated as BEL; this ops rollup is not settled ROI, live profitability, promotion readiness, or real-money evidence.", "ops hierarchy boundary")
    assert_contains(ops_text, "## Evidence boundary", "ops source evidence boundary section")
    assert_contains(ops_text, f"valid_evidence_scope={ptoh.OPS_HISTORY_VALID_EVIDENCE_SCOPE}", "ops source evidence scope")
    assert_contains(ops_text, ptoh.OPS_HISTORY_EVIDENCE_BOUNDARY_TEXT, "ops source evidence boundary text")
    assert_contains(ops_text, "| `2026-06-05` | UNKNOWN | SCANNER API ACCESS FAILURE", "ops table unknown-calendar API-access stale-cache scanner-failure row")
    assert_contains(ops_text, "Primary lane scanner API access failure before producing a usable lane result. Detail: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx. Treat this as API-access-failure operator context only, not a no-target, clean-empty, settled ROI, promotion, live-profitability, or real-money evidence. Stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: 403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx. Sidecar action: refresh_daily_wrapper_before_evidence_read. Recheck command: ./run_daily_portfolio_observation.sh. Refresh the daily wrapper and re-check sidecars before treating the day as evidence.", "ops table API-access stale-cache fallback detail")
    assert_contains(ops_text, "| `2026-06-04` | UNKNOWN | SCANNER API ACCESS FAILURE", "ops table unknown-calendar API-access scanner-failure row")
    assert_contains(ops_text, "Primary lane scanner API access failure before producing a usable lane result. Detail: 403 Client Error: Forbidden for url: https://brk0201-iapi-webservice.nyrabets.com/ListCards.ashx. Treat this as API-access-failure operator context only, not a no-target, clean-empty, settled ROI, promotion, live-profitability, or real-money evidence. Sidecar action: refresh_daily_wrapper_before_evidence_read. Recheck command: ./run_daily_portfolio_observation.sh. Refresh the daily wrapper and re-check sidecars before treating the day as evidence.", "ops table API-access scanner-failure action detail")
    assert_contains(ops_text, "| `2026-06-03` | OP/CD ACTIVE | INVALID SHAPE", "ops table invalid-shape pipeline sidecar row")
    assert_contains(ops_text, "Primary lane pipeline status sidecar has invalid JSON shape. Refresh the daily wrapper before drawing conclusions.", "ops table invalid-shape pipeline takeaway")
    assert_contains(ops_text, "| `2026-06-02` | OP/CD ACTIVE | SCANNER INVALID SHAPE", "ops table invalid-shape scanner sidecar row")
    assert_contains(ops_text, "Primary lane scanner status sidecar has invalid JSON shape. Refresh the daily wrapper before drawing conclusions.", "ops table invalid-shape scanner takeaway")
    assert_contains(ops_text, "| `2026-06-01` | OP/CD ACTIVE | SCANNER RECORDED INVALID SHAPE", "ops table pipeline-recorded invalid-shape scanner-status row")
    assert_contains(ops_text, "Primary lane scanner status sidecar was recorded invalid-shape by the pipeline. Refresh the daily wrapper before drawing conclusions.", "ops table pipeline-recorded invalid-shape scanner-status takeaway")
    assert_contains(ops_text, "| `2026-05-31` | OP/CD ACTIVE | SCANNER EMPTY", "ops table empty scanner sidecar row")
    assert_contains(ops_text, "Primary lane scanner status sidecar was empty. Refresh the daily wrapper before drawing conclusions.", "ops table empty scanner takeaway")
    assert_contains(ops_text, "| `2026-05-30` | OP/CD ACTIVE | PIPELINE EMPTY", "ops table empty pipeline sidecar row")
    assert_contains(ops_text, "Primary lane pipeline status sidecar was empty. Refresh the daily wrapper before drawing conclusions.", "ops table empty pipeline takeaway")
    assert_contains(ops_text, "`SCANNER API ACCESS FAILURE`, `PIPELINE EMPTY`, `SCANNER EMPTY`, `SCANNER INVALID SHAPE`, `SCANNER RECORDED EMPTY`, `SCANNER RECORDED UNREADABLE`, `SCANNER RECORDED INVALID SHAPE`, `INVALID SHAPE`, `UNREADABLE`, or `MISSING` means treat the day as operationally unresolved until the missing/empty/unreadable/invalid-shape sidecars are checked; API-access failures should preserve their sidecar action, wrapper recheck command, and stale-cache fallback count/kind/error when present as operational routing metadata only.", "ops guardrail separates missing empty unreadable invalid-shape sidecars and API-action routing")
    assert_contains(ops_text, "| `2026-05-29` | OP/CD ACTIVE | PARTIAL CACHE WITH ACTIVITY", "ops table project-relative partial-cache-with-activity row")
    assert_contains(ops_text, "4 missing race detail cache file(s). Re-run live before leaning on it as evidence.", "ops table project-relative partial-cache-with-activity takeaway detail")
    assert_contains(ops_text, "| `2026-05-28` | OP/CD ACTIVE | PARTIAL CACHE WITH ACTIVITY", "ops table run-root-relative partial-cache-with-activity row")
    assert_contains(ops_text, "3 missing race detail cache file(s). Re-run live before leaning on it as evidence.", "ops table run-root-relative partial-cache-with-activity takeaway detail")
    assert_contains(ops_text, "| `2026-05-27` | OP/CD ACTIVE | PARTIAL CACHE WITH ACTIVITY", "ops table lane-local partial-cache-with-activity row")
    assert_contains(ops_text, "1 missing race detail cache file(s). Re-run live before leaning on it as evidence.", "ops table lane-local partial-cache-with-activity takeaway detail")
    project_relative_primary_pipeline = json.loads((RUNS_ROOT / "2026-05-29" / "phase7_current_paper" / "pipeline_status.json").read_text(encoding="utf-8"))
    expected_project_relative = str((RUNS_ROOT / "2026-05-29" / "phase7_current_paper" / "renamed_live_scan.status.json").relative_to(BASE))
    if project_relative_primary_pipeline.get("scanner_status_path") != expected_project_relative:
        raise AssertionError("2026-05-29: expected fixture pipeline sidecar to preserve a project-relative renamed scanner-status path")
    run_root_relative_primary_pipeline = json.loads((RUNS_ROOT / "2026-05-28" / "phase7_current_paper" / "pipeline_status.json").read_text(encoding="utf-8"))
    if run_root_relative_primary_pipeline.get("scanner_status_path") != "phase7_current_paper/renamed_live_scan.status.json":
        raise AssertionError("2026-05-28: expected fixture pipeline sidecar to preserve a run-root-relative renamed scanner-status path")
    lane_local_primary_pipeline = json.loads((RUNS_ROOT / "2026-05-27" / "phase7_current_paper" / "pipeline_status.json").read_text(encoding="utf-8"))
    if lane_local_primary_pipeline.get("scanner_status_path") != "renamed_live_scan.status.json":
        raise AssertionError("2026-05-27: expected fixture pipeline sidecar to preserve a lane-local renamed scanner-status path")
    stale_default_primary_scanner = json.loads((RUNS_ROOT / "2026-05-27" / "phase7_current_paper" / "live_scan.status.json").read_text(encoding="utf-8"))
    if stale_default_primary_scanner.get("missing_race_detail_cache_skips") != 9:
        raise AssertionError("2026-05-27: expected stale default scanner sidecar to remain present with a distinct missing-detail count")
    assert_contains(ops_text, "| `2026-05-26` | NO TARGETS | CACHE MISS (CACHE-ONLY)", "ops table json-only no-target row")
    assert_contains(ops_text, "| `2026-05-25` | OP/CD ACTIVE | BETS READY (2 bets)", "ops table bet-ready row")
    assert_contains(ops_text, "| `2026-05-24` | OP/CD ACTIVE | UNREADABLE", "ops table unreadable primary row")
    assert_contains(ops_text, "| `2026-05-18` | OP/CD ACTIVE | RECOMMENDER FAILURE", "ops table recommender failure row")
    assert_contains(ops_text, "Primary lane hit a recommender failure. After scanner completed, 1 hit(s) were already found before the failure. Error type: RuntimeError. Detail: fixture recommender crash.", "ops table recommender failure takeaway")
    assert_contains(ops_text, "| `2026-05-17` | OP/CD ACTIVE | LOGGER FAILURE", "ops table logger failure row")
    assert_contains(ops_text, "Primary lane hit a logger failure. After recommender completed, 1 recommendation(s) were already built and 1 BET recommendation(s) were ready (context: bets_ready) before the failure. Error type: ValueError. Detail: fixture logger crash.", "ops table logger failure takeaway")
    assert_contains(ops_text, "| `2026-05-19` | UNREADABLE | CLEAN EMPTY", "ops table unreadable preflight row")
    assert_contains(ops_text, "| `2026-05-23` | OP/CD ACTIVE | SIGNALS, NO BET", "ops table hit-found row")
    assert_contains(ops_text, "| `2026-05-22` | OP/CD ACTIVE | PARTIAL CACHE EMPTY", "ops table partial-cache row")
    assert_contains(ops_text, "2 missing race detail cache file(s). Re-run live before treating it as a true zero-hit day.", "ops table partial-cache takeaway detail")
    assert_contains(ops_text, "| `2026-05-21` | OP/CD ACTIVE | CLEAN EMPTY", "ops table zero-hit row")
    assert_contains(ops_text, "| `2026-05-20` | NO TARGETS | CACHE MISS (CACHE-ONLY)", "ops table no-target cache-miss row")
    assert_contains(ops_text, "| `2026-05-16` | OP/CD ACTIVE | CLEAN EMPTY", "ops table json-only zero-hit row")
    assert_contains(ops_text, "| `2026-05-15` | OP/CD ACTIVE | SCANNER RECORDED EMPTY", "ops table pipeline-recorded empty scanner-status row")
    assert_contains(ops_text, "Primary lane scanner status sidecar was recorded empty by the pipeline. Refresh the daily wrapper before drawing conclusions.", "ops table pipeline-recorded empty scanner-status takeaway")
    assert_contains(ops_text, "| `2026-05-14` | OP/CD ACTIVE | SCANNER RECORDED UNREADABLE", "ops table pipeline-recorded unreadable scanner-status row")
    assert_contains(ops_text, "Primary lane scanner status sidecar was recorded unreadable by the pipeline. Refresh the daily wrapper before drawing conclusions.", "ops table pipeline-recorded unreadable scanner-status takeaway")
    assert_contains(ops_text, "| `2026-05-13` | OP/CD ACTIVE | MISSING SCAN OUTPUT", "ops table missing scan-output row")
    assert_contains(ops_text, "Primary lane scan-output artifact was missing after scanner status reported no_qualifiers; pipeline used a safe empty [] fallback, so this is not a clean no-qualifier observation. Refresh the daily wrapper before treating the day as a clean no-qualifier observation.", "ops table missing scan-output takeaway")
    assert_contains(ops_text, "`MISSING SCAN OUTPUT` means the scanner-status sidecar was readable but the expected scan-output artifact was absent", "ops guardrail separates missing scan-output from clean empty")
    assert_contains(ops_text, "- `2026-06-05`: Preflight context: NYRA preflight check failed (403 Client Error: Forbidden for url: https://brk0201-iapi-webservice.nyrabets.com/ListCards.ashx). Treat calendar state as unknown.", "ops latest preflight preserves newest API-access stale-cache detail")
    assert_contains(ops_text, "- `2026-06-04`: Preflight context: NYRA preflight check failed (403 Client Error: Forbidden for url: https://brk0201-iapi-webservice.nyrabets.com/ListCards.ashx). Treat calendar state as unknown.", "ops latest preflight preserves unknown-calendar scanner-failure detail")
    assert_contains(ops_text, "- `2026-06-03`: Preflight context: primary paper-basket target tracks racing today: OP, CD.", "ops latest preflight still reflects newest active-target run")

    live_surface = validate_live_surfaces()

    suite_read = (
        "ops history still keeps bet-ready, no-target, unknown-calendar, zero-hit, limited-coverage empty, limited-coverage with activity, hit-found / no-bet, "
        "and explicit API-access scanner failure, including API-access stale-cache fallback count/kind/error context, recommender/logger plus missing scan-output and missing/empty/unreadable/invalid-shape artifact issue days and pipeline-recorded scanner-status issue days operationally distinct, now preserving API sidecar action/recheck routing, preserving what had already succeeded before recommender/logger failures, carrying partial-cache missing-detail context directly in both limited-coverage takeaways, recovering lane-local, run-root, or project-relative pipeline-declared relocated scanner sidecars when the default lane filename is absent, preferring the declared sidecar when a stale default scanner filename is still present, and keeping saved JSON preflight calendar context explicit at the source layer when the text sibling is gone, with both the fixture surfaces and the real default CSV/markdown surfaces pinned at the source layer; "
        "fixture and live summary counts are now published as structured JSON so calendar-unknown totals can be checked without scraping markdown and are sourced from calendar_state rather than day_bucket; "
        "the markdown now publishes the OP_DURABLE_K7 anchor / CD_CORE_K8 primary OP/CD paper-basket companion / OP_REFINED_K7 shadow-watch hierarchy context plus the BAQ-not-BEL and no-settled-ROI/no-promotion/no-real-money boundary; "
        "source markdown now carries exact `valid_evidence_scope=rolling_operator_recap_only` plus boundary text, CSV outputs carry `valid_evidence_scope` plus `evidence_boundary_text`, and the direct validator report exposes exact `valid_evidence_scope=rolling_operator_recap_only` as validator-report metadata only, so rolling day buckets and streaks cannot be overread as scanner evidence, settled ROI, promotion readiness, live profitability, real-money support, or BAQ-as-BEL evidence; "
        "the direct validator rejects malformed scorecard gates before fixture/report artifacts, including non-positive Phase 8 and real-money floors, and publishes the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that day buckets, streaks, clean-empty rows, no-target rows, and issue routing do not advance; "
        "ops history: rolling operational recap surface, not new forward evidence by itself"
    )
    child_checks = [
        *scorecard_guardrails,
        {
            "check": "fixture_day_bucket_matrix_stays_covered",
            "status": "pass",
            "detail": "fixture days still cover no-target, zero-hit, limited-coverage empty, limited-coverage with activity, hit-found/no-bet, bet-ready, unreadable-calendar, unknown-calendar API-access scanner failure with and without stale-cache fallback detail, missing scan-output, missing/empty/unreadable/invalid-shape artifact, pipeline-recorded scanner-status, and recommender/logger failure branches",
        },
        {
            "check": "saved_fixture_and_live_surfaces_match_current_rebuilds",
            "status": "pass",
            "detail": "fixture ops_history CSV/markdown outputs plus the real default OPS_HISTORY surfaces still have to match fresh source-layer rebuilds instead of drifting behind helper changes",
        },
        {
            "check": "saved_json_preflight_context_and_relocated_sidecar_recovery_stay_explicit",
            "status": "pass",
            "detail": "saved JSON preflight calendar context after text-note loss stays explicit in row-level ops-history output, while lane-local, run-root, project-relative, or stale-default-masked pipeline-declared relocated scanner-sidecar recovery all stay explicit instead of degrading into generic issue rows",
        },
        {
            "check": "pipeline_failure_and_partial_cache_takeaways_stay_honest",
            "status": "pass",
            "detail": "recommender/logger failure rows still preserve what had already succeeded before the crash, while both limited-coverage branches keep missing-detail cache counts visible in the takeaway text",
        },
        {
            "check": "api_access_stale_cache_fallback_takeaway_stays_explicit",
            "status": "pass",
            "detail": "the rolling ops-history fixture now proves API-access scanner failures completed from stale cache keep fallback kind/count/error metadata in the day-level takeaway beside the sidecar action and wrapper recheck command",
        },
        {
            "check": "ops_history_explicitly_stays_operational_recap_not_new_evidence",
            "status": "pass",
            "detail": "the direct validator summary still says plainly that ops history is a rolling operational recap surface rather than new forward evidence, with the OP/CD/Phase 8 hierarchy and BAQ-not-BEL boundary visible in the markdown",
        },
        {
            "check": "source_outputs_publish_ops_history_evidence_boundary_fields",
            "status": "pass",
            "detail": "the source markdown now renders exact valid_evidence_scope=rolling_operator_recap_only plus boundary text, and every source CSV row carries valid_evidence_scope plus evidence_boundary_text so automation cannot treat ops buckets or streaks as scanner, ROI, promotion, live-profitability, real-money, or BAQ-as-BEL evidence",
        },
        {
            "check": "direct_validation_report_exposes_ops_history_valid_scope",
            "status": "pass",
            "detail": "the direct ops-history validator report now exposes the raw valid_evidence_scope line and keeps green day-bucket/streak checks classified as rolling operator-recap metadata only",
        },
        {
            "check": "ops_history_preserves_scorecard_gate_boundary",
            "status": "pass",
            "detail": "the ops-history validator now publishes the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite while saying day buckets, streaks, clean-empty rows, no-target rows, and issue routing do not count toward those gates",
        },
        {
            "check": "fixture_scratch_metadata_published",
            "status": "pass",
            "detail": "the ops-history validator JSON publishes project-local fixture scratch metadata so parent rollups can verify the isolated fixture root without parsing markdown prose",
        },
        {
            "check": "summary_counts_published_and_calendar_unknown_counts_source_calendar_state",
            "status": "pass",
            "detail": "fixture and live validator JSON publish structured ops-history summary counts, with calendar_unknown_days sourced from calendar_state rather than day_bucket so unknown-calendar issue days remain visible",
        },
    ]
    if (
        scorecard_gates.get("source") != "forward_evidence_scorecard.json"
        or scorecard_gates.get("source_path") != "decision_gate_minimums"
        or scorecard_gates.get("anchor_displacement_min_roi_complete_settled_observations") != 30
        or scorecard_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") != 20
        or scorecard_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") != 100
        or scorecard_gates.get("real_money_no_baq_as_bel_required") is not True
        or "no BAQ-as-BEL substitution" not in scorecard_gates.get("real_money_also_requires", [])
    ):
        raise AssertionError("ops-history scorecard gate boundary no longer matches forward_evidence_scorecard.json")
    if (
        scratch.get("fixture_root_relative") != "out/status_validation/ops_history_fixture"
        or scratch.get("fixture_root_is_project_local") is not True
        or scratch.get("fixture_root_cleared_before_fixture_run") is not True
    ):
        raise AssertionError("ops-history fixture scratch metadata no longer proves a project-local cleared fixture root")

    report = {
        "suite_status": "pass",
        "valid_evidence_scope": ptoh.OPS_HISTORY_VALID_EVIDENCE_SCOPE,
        "total_fixture_scenarios": len(EXPECTED),
        "total_checks": len(EXPECTED) + 1,
        "check_count": len(EXPECTED) + 1,
        "child_check_count": len(child_checks),
        "child_checks": child_checks,
        "fixture_case_count": len(EXPECTED),
        "live_surface_checks": 1,
        "ops_history_md": str(ops_md.relative_to(BASE)),
        "ops_history_csv": str(ops_csv.relative_to(BASE)),
        "live_ops_history_md": live_surface["ops_history_md"],
        "live_ops_history_csv": live_surface["ops_history_csv"],
        "cases": [
            {
                "date": run_date,
                "calendar_state": EXPECTED[run_date]["calendar_state"],
                "day_bucket": EXPECTED[run_date]["day_bucket"],
                "primary_state": EXPECTED[run_date]["primary_state"],
                "takeaway": EXPECTED[run_date]["takeaway"],
            }
            for run_date in sorted(EXPECTED.keys(), reverse=True)
        ],
        "live_surface": live_surface,
        "fixture_summary_counts": fixture_summary_counts,
        "summary": {
            "suite_read": suite_read,
        },
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "scratch": scratch,
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }
    write_text(OUT_MD, "\n".join([
        "# Paper Trade Ops History Validation",
        "",
        "This report validates `paper_trade_ops_history.py` against representative fixture days under `out/status_validation/ops_history_fixture/`, while publishing the direct validator readout under the standard `out/status_validation/paper_trade_ops_history/` path.",
        "",
        "## Cases",
        "",
        f"- `2026-06-05`: unknown-calendar day with an API-access scanner failure completed from stale cache now still counts toward calendar-unknown summary totals while staying in the issue bucket, and the takeaway preserves HTTP 403 detail, stale-cache fallback kind/count/error context, sidecar action, and wrapper recheck routing.",
        f"- `2026-06-04`: unknown-calendar day with an API-access scanner failure now still counts toward calendar-unknown summary totals while staying in the issue bucket, and the takeaway preserves the upstream 403 detail plus sidecar action/recheck routing.",
        f"- `2026-06-03`: active-target day with a readable but non-object `pipeline_status.json` now lands in `ISSUE` as `INVALID SHAPE` instead of flattening into missing/unreadable or a quiet row.",
        f"- `2026-06-02`: active-target day with a readable but non-object scanner-status sidecar now lands in `ISSUE` as `SCANNER INVALID SHAPE` instead of flattening into unreadable or clean-empty.",
        f"- `2026-06-01`: active-target day with `pipeline_status.json` recording `scanner_status_state=invalid_shape` but no physical scanner-status sidecar now lands in `ISSUE` as `SCANNER RECORDED INVALID SHAPE` instead of flattening into a quiet or miscellaneous row.",
        f"- `2026-05-31`: active-target day with a readable pipeline but zero-byte scanner sidecar now lands in `ISSUE` as `SCANNER EMPTY` instead of flattening into unreadable or clean-empty.",
        f"- `2026-05-30`: active-target day with a zero-byte `pipeline_status.json` now lands in `ISSUE` as `PIPELINE EMPTY` instead of flattening into missing/unreadable.",
        f"- `2026-05-29`: active-target partial-cache-with-activity day still lands in `ACTIVE, LIMITED COVERAGE WITH ACTIVITY` when `pipeline_status.json` declares the renamed scanner sidecar relative to the project root, and the takeaway keeps the scanner-only 4-missing-detail count.",
        f"- `2026-05-28`: active-target partial-cache-with-activity day still lands in `ACTIVE, LIMITED COVERAGE WITH ACTIVITY` when `pipeline_status.json` declares the renamed scanner sidecar relative to the run root, and the takeaway keeps the scanner-only 3-missing-detail count.",
        f"- `2026-05-27`: active-target partial-cache-with-activity day still lands in `ACTIVE, LIMITED COVERAGE WITH ACTIVITY` when `pipeline_status.json` declares the renamed scanner sidecar as a lane-local filename, proving the ops-history source layer can recover relocated sidecars instead of flattening the day into a weaker missing-artifact read.",
        f"- `2026-05-26`: no-target cache-only miss still stays `NO TARGETS` after `preflight_note.txt` is removed, proving the ops-history source layer keeps the saved JSON preflight snapshot explicit instead of flattening the day into a generic quiet row.",
        f"- `2026-05-25`: active-target bet-ready day still lands in `BETS READY` with a direct pre-race action takeaway.",
        f"- `2026-05-24`: unreadable primary status sidecar now lands in `ISSUE` instead of drifting into a softer miscellaneous bucket.",
        f"- `2026-05-23`: active-target hit-found / no-bet day still lands in `ACTIVE, HITS FOUND`.",
        f"- `2026-05-22`: active-target partial-cache empty day still lands in `ACTIVE, LIMITED COVERAGE` and now keeps the missing race-detail cache count in the takeaway when the scanner sidecar exposes it.",
        f"- `2026-05-21`: active-target clean-empty day still lands in `ACTIVE, ZERO HITS`.",
        f"- `2026-05-20`: no-target cache-only miss still stays `NO TARGETS` with an explicit cache-miss takeaway.",
        f"- `2026-05-19`: malformed `preflight_note.json` now lands in `UNKNOWN CALENDAR` with an unreadable-preflight takeaway instead of softening into a missing-note case.",
        f"- `2026-05-18`: recommender-stage pipeline errors now stay explicit as `RECOMMENDER FAILURE` and preserve that scanner had already completed with 1 hit before the crash.",
        f"- `2026-05-17`: logger-stage pipeline errors now stay explicit as `LOGGER FAILURE` and preserve that the recommender had already built 1 BET-ready recommendation before logging died.",
        f"- `2026-05-16`: active-target clean-empty day still lands in `ACTIVE, ZERO HITS` after `preflight_note.txt` is removed, proving the stored row note and bucket logic stay anchored to `preflight_note.json` even when that older run drops out of the top-five latest-notes markdown excerpt.",
        f"- `2026-05-15`: active-target day with `pipeline_status.json` recording `scanner_status_state=empty` but no physical scanner-status sidecar now lands in `ISSUE` as `SCANNER RECORDED EMPTY` instead of flattening into a quiet or miscellaneous row.",
        f"- `2026-05-14`: active-target day with `pipeline_status.json` recording `scanner_status_state=unreadable` but no physical scanner-status sidecar now lands in `ISSUE` as `SCANNER RECORDED UNREADABLE` instead of flattening into a quiet or miscellaneous row.",
        f"- `2026-05-13`: active-target day with a readable scanner-status sidecar but missing scan-output artifact now lands in `ISSUE` as `MISSING SCAN OUTPUT`, preserving the sidecar's `no_qualifiers` report while warning that the safe empty fallback is not a clean no-qualifier observation.",
        "",
        "## Current Read",
        "",
        f"- Suite read: {suite_read}",
        "",
        "## Source Output Boundary",
        "",
        f"- Source scope line: `valid_evidence_scope={ptoh.OPS_HISTORY_VALID_EVIDENCE_SCOPE}`",
        f"- Source boundary text: {ptoh.OPS_HISTORY_EVIDENCE_BOUNDARY_TEXT}",
        "- CSV contract: every `ops_history.csv` row carries `valid_evidence_scope` and `evidence_boundary_text`.",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
        f"- valid_evidence_scope={EVIDENCE_BOUNDARY['valid_evidence_scope']}",
        f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
        "- Boundary: ops-history validator cleanliness is operational-recap metadata only, not new forward evidence, not a live paper-trade ledger, not a current-day scanner result, not settled ROI, not live profitability, not promotion readiness, and not real-money evidence.",
        "- Non-goals: do not treat day buckets, streaks, no-target rows, clean-empty rows, limited-coverage rows, or issue routing as ROI-complete observations, profitability evidence, promotion support, or real-money support.",
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
        "## Live current surface",
        "",
        f"- Latest live row date: `{live_surface['latest_date']}`",
        f"- Latest live calendar state: `{live_surface['latest_calendar_state']}`",
        f"- Latest live day bucket: `{live_surface['day_bucket']}`",
        f"- Live summary counts: `{json.dumps(live_surface['summary_counts'], sort_keys=True)}`",
        f"- Live markdown surface: `{live_surface['ops_history_md']}`",
        f"- Live CSV surface: `{live_surface['ops_history_csv']}`",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        "",
        "## Validation result",
        "",
        f"- Fixture markdown: `{report['ops_history_md']}`",
        f"- Fixture CSV: `{report['ops_history_csv']}`",
        f"- Live markdown: `{report['live_ops_history_md']}`",
        f"- Live CSV: `{report['live_ops_history_csv']}`",
        f"- Fixture summary counts: `{json.dumps(fixture_summary_counts, sort_keys=True)}`",
        "- Fixture root: `out/status_validation/ops_history_fixture/`",
        "- Fixture scratch: project-local `out/status_validation/ops_history_fixture/` is cleared before the fixture run and published in the validator JSON.",
        "- PASS: the rolling ops-history layer now keeps the key day-bucket transitions pinned directly, including saved-JSON preflight-context runs after text-note loss, zero-byte and invalid-shape pipeline/scanner sidecars, missing scan-output artifacts, and pipeline-recorded empty/unreadable/invalid-shape scanner-status states, the guardrail text now names missing scan-output plus missing/empty/unreadable/invalid-shape sidecars, the direct validator report exposes the raw valid_evidence_scope, and both the fixture surfaces plus the real default CSV/markdown surfaces still match a fresh rebuild from the source layer.",
        "",
    ]))
    write_text(OUT_JSON, json.dumps(report, indent=2) + "\n")

    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    print("PASS paper_trade_ops_history")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
