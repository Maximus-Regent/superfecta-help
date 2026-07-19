#!/usr/bin/env python3
"""
Validation for rule-targeted live scanning and max-races limited-coverage status.

Purpose:
- pin the scanner pre-detail filter so --max-races is spent on rule-relevant races, not unrelated cards
- prove max-races-limited active scans do not classify as clean empty observations
- keep downstream summaries routing limited coverage as operational evidence only
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any

import live_portfolio_scanner as scanner
import paper_trade_ops_history as ops_history
import paper_trade_pipeline as pipeline
import paper_trade_status_summary as status_summary

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "out" / "status_validation" / "live_scan_targeting_and_limit_status"
REPORT_MD = OUT_DIR / "live_scan_targeting_and_limit_status_validation.md"
REPORT_JSON = OUT_DIR / "live_scan_targeting_and_limit_status_validation.json"
REBUILD_COMMAND = "python3 validate_live_scan_targeting_and_limit_status.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
VALID_EVIDENCE_SCOPE = "live_scan_targeting_limited_coverage_guardrail_only"

EVIDENCE_BOUNDARY = {
    "artifact_role": "live-scan targeting and max-races limited-coverage validator",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "valid_use": "synthetic scanner/pipeline/status/ops guardrail validation for target filtering, capped-coverage routing, and operator-status metadata",
    "source_scope": "synthetic race-summary fixtures including an explicit BEL-vs-BAQ fixture plus direct scanner/pipeline/status-summary/ops-history helper outputs; not a current-day live scanner result",
    "not_new_forward_evidence": True,
    "not_current_day_scanner_evidence": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_real_money_evidence": True,
    "non_goals": [
        "do not use this validator as proof of a quiet/no-signal day",
        "do not use capped no-hit fixture behavior as settled ROI or live-profitability evidence",
        "do not use a green validator as Phase 8 / OP_REFINED_K7 promotion evidence",
        "do not treat BAQ as BEL",
        "do not use this validator as real-money readiness evidence",
    ],
    "stronger_forward_confidence_requires": [
        "fresh OP/CD wrapper runs on active target days with max-races high enough to cover full_target_coverage_min_races",
        "qualifying paper signals copied into settlement templates",
        "ROI-complete settled paper rows before any scorecard gate advances",
    ],
}


def require(condition: bool, check: str, detail: str) -> dict[str, str]:
    if not condition:
        raise AssertionError(f"{check}: {detail}")
    return {"check": check, "status": "pass", "detail": detail}


def read_rules() -> list[dict[str, Any]]:
    return json.loads((BASE / "phase7_current_paper_rules.json").read_text(encoding="utf-8"))["rules"]


def require_positive_non_bool_int(value: Any, *, source_name: str, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, source_name: str, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise AssertionError(f"{source_name} {field_name} must be a list of non-empty strings")
    return value


def read_scorecard_gate_minimums(scorecard_json_path: Path = SCORECARD_JSON) -> dict[str, Any]:
    source_path = Path(scorecard_json_path)
    source_name = source_path.name
    payload = json.loads(source_path.read_text(encoding="utf-8"))
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
        "source": source_name,
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_also_requires": real_money_requires,
        "real_money_no_baq_as_bel_required": True,
        "evidence_boundary": (
            "synthetic live-scan targeting and max-races limited-coverage checks do not count toward "
            "anchor-displacement, Phase 8 promotion-review, or real-money discussion gates"
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args([] if argv is None else argv)


def scorecard_gate_cli_contract_checks(scorecard_json_path: Path = SCORECARD_JSON) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    with TemporaryDirectory(prefix="live_scan_targeting_scorecard_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        base_payload = json.loads(Path(scorecard_json_path).read_text(encoding="utf-8"))
        scorecard_path = tmp_root / "forward_evidence_scorecard.json"
        bad_out_dir = tmp_root / "nested" / "live_scan_targeting_and_limit_status"

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
                "scorecard_boolean_gate_floor_fails_before_live_scan_artifacts",
                "a malformed boolean anchor-displacement scorecard gate fails before nested live-scan targeting validation outputs are created",
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
                "scorecard_nonpositive_phase8_gate_floor_fails_before_live_scan_artifacts",
                "a non-positive Phase 8 promotion-review scorecard gate fails before nested live-scan targeting validation outputs are created",
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
                "scorecard_nonpositive_real_money_gate_floor_fails_before_live_scan_artifacts",
                "a non-positive real-money discussion scorecard gate fails before nested live-scan targeting validation outputs are created",
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
                "scorecard_missing_no_baq_fails_before_live_scan_artifacts",
                "a scorecard gate missing the no-BAQ-as-BEL real-money prerequisite fails before nested live-scan targeting validation outputs are created",
            )
        )
    return checks


def synthetic_api_access_failure_status() -> dict[str, Any]:
    """Run scanner.main with a synthetic 403 from list_cards and return the sidecar."""
    class SyntheticResponse:
        status_code = 403

    class SyntheticHTTPError(RuntimeError):
        response = SyntheticResponse()

    def deny_cards() -> list[dict[str, Any]]:
        raise SyntheticHTTPError("403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx")

    with TemporaryDirectory(prefix="live_scan_api_access_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        rules_path = tmp_root / "rules.json"
        status_path = tmp_root / "live_scan.status.json"
        rules_path.write_text(json.dumps({"rules": []}) + "\n", encoding="utf-8")

        old_argv = sys.argv
        old_list_cards = scanner.list_cards
        old_cache_dir = scanner.CACHE_DIR
        try:
            scanner.list_cards = deny_cards
            scanner.CACHE_DIR = tmp_root / "cache"
            sys.argv = [
                str(BASE / "live_portfolio_scanner.py"),
                "--rules",
                str(rules_path),
                "--status-json",
                str(status_path),
                "--json",
                "--no-dedup",
            ]
            try:
                scanner.main()
            except SyntheticHTTPError:
                pass
        finally:
            scanner.list_cards = old_list_cards
            scanner.CACHE_DIR = old_cache_dir
            sys.argv = old_argv

        if not status_path.exists():
            raise AssertionError("synthetic 403 scanner fixture did not write a status sidecar")
        payload = json.loads(status_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise AssertionError("synthetic 403 scanner fixture wrote a non-object status sidecar")
        return payload


def synthetic_no_matching_cards_stdout() -> str:
    """Run scanner.main with an empty card list and return human stdout."""
    def no_cards() -> list[dict[str, Any]]:
        return []

    with TemporaryDirectory(prefix="live_scan_no_matching_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        rules_path = tmp_root / "rules.json"
        status_path = tmp_root / "live_scan.status.json"
        rules_path.write_text(json.dumps({"rules": []}) + "\n", encoding="utf-8")

        old_argv = sys.argv
        old_list_cards = scanner.list_cards
        old_cache_dir = scanner.CACHE_DIR
        buffer = io.StringIO()
        try:
            scanner.list_cards = no_cards
            scanner.CACHE_DIR = tmp_root / "cache"
            sys.argv = [
                str(BASE / "live_portfolio_scanner.py"),
                "--rules",
                str(rules_path),
                "--status-json",
                str(status_path),
                "--no-dedup",
            ]
            with contextlib.redirect_stdout(buffer):
                scanner.main()
        finally:
            scanner.list_cards = old_list_cards
            scanner.CACHE_DIR = old_cache_dir
            sys.argv = old_argv

        return buffer.getvalue()


def hydrate_api_access_failure_pipeline(scanner_status: dict[str, Any]) -> dict[str, Any]:
    """Prove paper_trade_pipeline copies scanner API-failure metadata structurally."""
    with TemporaryDirectory(prefix="pipeline_api_access_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        scan_input = tmp_root / "live_scan.json"
        scanner_status_path = tmp_root / "live_scan.status.json"
        scan_input.write_text("[]", encoding="utf-8")
        scanner_status_path.write_text(json.dumps(scanner_status) + "\n", encoding="utf-8")

        status_payload: dict[str, object] = {
            "scanner_stage_status": "scanner_failed",
            "cache_only": False,
        }
        pipeline._hydrate_scan_context(
            SimpleNamespace(skip_scan=False),
            scan_input,
            scanner_status_path,
            status_payload,
        )
        status_payload["observation_result"] = pipeline._observation_result(status_payload)
        status_payload["observation_scope"], status_payload["observation_reason"] = pipeline._observation_metadata(status_payload)
        return dict(status_payload)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    scorecard_gates = read_scorecard_gate_minimums(args.scorecard_json)
    scorecard_cli_checks = scorecard_gate_cli_contract_checks(args.scorecard_json)
    out_dir = Path(args.out_dir)
    report_md = out_dir / "live_scan_targeting_and_limit_status_validation.md"
    report_json = out_dir / "live_scan_targeting_and_limit_status_validation.json"

    rules = read_rules()
    out_dir.mkdir(parents=True, exist_ok=True)

    synthetic_races = [
        {"raceId": "FR-1", "raceNumber": 1, "raceMeetingName": "FR Toulouse"},
        {"raceId": "BAQ-7", "raceNumber": 7, "raceMeetingName": "Belmont At The Big A"},
        {"raceId": "OP-6", "raceNumber": 6, "raceMeetingName": "Oaklawn Park"},
        {"raceId": "OP-7", "raceNumber": 7, "raceMeetingName": "Oaklawn Park"},
        {"raceId": "CD-1", "raceNumber": 1, "raceMeetingName": "Churchill Downs"},
        {"raceId": "CD-2", "raceNumber": 2, "raceMeetingName": "Churchill Downs"},
    ]
    candidates, skipped = scanner.candidate_races_for_rules(synthetic_races, rules)
    candidate_ids = [race["raceId"] for race in candidates]

    bel_alias_rules = [
        {
            "rule_id": "BEL_BROAD1_K7_SYNTHETIC_PREFETCH_ONLY",
            "track": "BEL",
            "card_names": ["Belmont Park"],
            "card_min": 5,
        }
    ]
    bel_alias_races = [
        {"raceId": "BEL-7", "raceNumber": 7, "raceMeetingName": "Belmont Park"},
        {"raceId": "BAQ-BIGA-7", "raceNumber": 7, "raceMeetingName": "Belmont At The Big A"},
        {"raceId": "BAQ-AT-SIGN-BIGA-7", "raceNumber": 7, "raceMeetingName": "Belmont @ The Big A"},
        {"raceId": "BAQ-BELPARK-BIGA-7", "raceNumber": 7, "raceMeetingName": "Belmont Park At The Big A"},
        {"raceId": "BAQ-BELPARK-AT-SIGN-BIGA-7", "raceNumber": 7, "raceMeetingName": "Belmont Park @ The Big A"},
        {"raceId": "BAQ-BELPARK-AQU-7", "raceNumber": 7, "raceMeetingName": "Belmont Park At Aqueduct"},
        {"raceId": "AQU-7", "raceNumber": 7, "raceMeetingName": "Aqueduct"},
    ]
    bel_alias_candidates, bel_alias_skipped = scanner.candidate_races_for_rules(bel_alias_races, bel_alias_rules)
    bel_alias_candidate_ids = [race["raceId"] for race in bel_alias_candidates]
    bel_alias_rejected_ids = {
        "BAQ-BIGA-7",
        "BAQ-AT-SIGN-BIGA-7",
        "BAQ-BELPARK-BIGA-7",
        "BAQ-BELPARK-AT-SIGN-BIGA-7",
        "BAQ-BELPARK-AQU-7",
    }
    coverage_counts = scanner.target_coverage_counts(target_race_count=18, race_details_attempted=12)
    scanner_boundary_hits = scanner.analyze_race(
        "Oaklawn Park",
        {"raceId": "OP-SOURCE-BOUNDARY", "raceNumber": 7, "raceMeetingName": "Oaklawn Park"},
        {
            "raceId": "OP-SOURCE-BOUNDARY",
            "raceNumber": 7,
            "surface": "DIRT",
            "raceTaggedValues": [{"value": "track|main|FAST"}],
            "runners": [
                {"programNumber": str(idx), "runnerName": f"Runner {idx}", "currentWinPrice": price}
                for idx, price in enumerate([1.2, 10, 20, 20, 20, 20, 20, 20, 20, 20, 20], start=1)
            ],
        },
        rules,
        base_stake=1.0,
        emit_combos=True,
    )
    scanner_boundary_hit = scanner_boundary_hits[0] if scanner_boundary_hits else {}
    scanner_no_hit_human = scanner.format_human([], emit_combos=False)
    scanner_hit_human = scanner.format_human(scanner_boundary_hits, emit_combos=False)
    scanner_hit_discord = scanner.format_discord(scanner_boundary_hits)
    scanner_valid_scope_line = f"valid_evidence_scope={scanner.SCANNER_VALID_EVIDENCE_SCOPE}"
    scanner_no_matching_cards_stdout = synthetic_no_matching_cards_stdout()
    with TemporaryDirectory(prefix="live_scan_empty_csv_") as tmp_dir:
        scanner_empty_csv = Path(tmp_dir) / "empty_scan.csv"
        scanner._save_output([], str(scanner_empty_csv))
        scanner_empty_csv_header = scanner_empty_csv.read_text(encoding="utf-8").strip()
    api_access_scanner_status = synthetic_api_access_failure_status()
    api_access_pipeline_status = hydrate_api_access_failure_pipeline(api_access_scanner_status)
    api_access_summary_payload = status_summary.summarize(
        api_access_scanner_status,
        api_access_pipeline_status,
        scanner_state="readable",
        pipeline_state="readable",
        require_pipeline_status=True,
    )

    limited_empty_status: dict[str, object] = {
        "result": "ok",
        "stage": "done",
        "scanner_stage_status": "completed",
        "scanner_result": "no_qualifiers",
        "scanner_partial_cache": False,
        "scanner_max_race_limit_hit": True,
        "scanner_race_details_attempted": 12,
        "scanner_race_details_loaded": 12,
        "scanner_target_race_count": 18,
        "scanner_full_target_coverage_min_races": coverage_counts["full_target_coverage_min_races"],
        "scanner_unattempted_target_race_count": coverage_counts["unattempted_target_race_count"],
        "scanner_pre_detail_skipped_race_count": 426,
        "scan_hit_count": 0,
        "recommendation_count": 0,
        "bet_count": 0,
    }
    limited_empty_observation = pipeline._observation_result(limited_empty_status)
    limited_empty_status["observation_result"] = limited_empty_observation
    limited_empty_scope, limited_empty_reason = pipeline._observation_metadata(limited_empty_status)

    limited_activity_status = dict(limited_empty_status)
    limited_activity_status.update({"scan_hit_count": 1, "recommendation_count": 1})
    limited_activity_observation = pipeline._observation_result(limited_activity_status)
    limited_activity_status["observation_result"] = limited_activity_observation
    limited_activity_scope, limited_activity_reason = pipeline._observation_metadata(limited_activity_status)

    clean_status = dict(limited_empty_status)
    clean_status.update({"scanner_max_race_limit_hit": False, "scanner_target_race_count": 8})
    clean_observation = pipeline._observation_result(clean_status)

    summary_payload = status_summary.summarize(
        {
            "result": "no_qualifiers",
            "partial_cache": False,
            "raw_hit_count": 0,
            "emitted_hit_count": 0,
            "race_details_attempted": 12,
            "race_details_loaded": 12,
            "max_race_limit_hit": 1,
            "target_race_count": 18,
            "full_target_coverage_min_races": coverage_counts["full_target_coverage_min_races"],
            "unattempted_target_race_count": coverage_counts["unattempted_target_race_count"],
            "pre_detail_skipped_race_count": 426,
        },
        {
            **limited_empty_status,
            "observation_scope": limited_empty_scope,
            "observation_reason": limited_empty_reason,
        },
        scanner_state="readable",
        pipeline_state="readable",
        require_pipeline_status=True,
    )

    lane_label, lane_observation, lane_detail, *_lane_counts = ops_history.summarize_lane(
        {
            **limited_empty_status,
            "observation_scope": limited_empty_scope,
            "observation_reason": limited_empty_reason,
        },
        {
            "max_race_limit_hit": 1,
            "race_details_attempted": 12,
            "target_race_count": 18,
            "full_target_coverage_min_races": coverage_counts["full_target_coverage_min_races"],
            "unattempted_target_race_count": coverage_counts["unattempted_target_race_count"],
            "pre_detail_skipped_race_count": 426,
        },
    )
    day_bucket = ops_history.classify_day_bucket(
        "ACTIVE TARGETS",
        lane_observation,
        0,
        0,
        0,
        False,
        False,
    )

    checks = [
        *scorecard_cli_checks,
        require(
            candidate_ids == ["OP-7", "CD-1", "CD-2"] and skipped == 3,
            "scanner_prefilter_spends_detail_attempts_only_on_rule_candidate_races",
            "synthetic race-summary rows keep OP race 7+ and CD races while skipping unrelated FR/BAQ rows and OP race 6 before any race-detail fetch",
        ),
        require(
            "BAQ-7" not in candidate_ids and bel_alias_rejected_ids.isdisjoint(bel_alias_candidate_ids),
            "scanner_prefilter_does_not_alias_baq_as_bel",
            "Belmont-at-the-Big-A / BAQ-style synthetic rows are not treated as BEL even when a feed label contains the Belmont Park substring, and are not treated as active OP/CD rule-card candidates",
        ),
        require(
            bel_alias_candidate_ids == ["BEL-7"] and bel_alias_skipped == 6,
            "scanner_prefilter_accepts_true_belmont_without_baq_bridge",
            "an explicit synthetic BEL rule still accepts true Belmont Park while skipping Belmont-at-the-Big-A / BAQ, at-sign Big A labels, Belmont-Park-at-Big-A, Belmont-Park-at-Aqueduct, and Aqueduct rows, so the dormant BEL path stays distinct from BAQ substitution",
        ),
        require(
            limited_empty_observation == "limited_coverage_empty_run"
            and limited_empty_scope == "operational_limit"
            and limited_empty_reason == "max_race_limit_empty",
            "pipeline_max_race_limited_empty_is_not_clean_empty",
            "a no-hit scanner sidecar with max_race_limit_hit=true now becomes limited_coverage_empty_run / operational_limit instead of clean_empty_run",
        ),
        require(
            limited_activity_observation == "limited_coverage_with_activity"
            and limited_activity_scope == "operational_limit"
            and limited_activity_reason == "max_race_limit_with_activity",
            "pipeline_max_race_limited_activity_stays_limited",
            "activity found before a max-races cap remains visible but is still classified as operationally limited coverage",
        ),
        require(
            clean_observation == "clean_empty_run",
            "pipeline_clean_empty_still_available_without_limit_hit",
            "normal no-qualifier scans still classify cleanly when max_race_limit_hit is false",
        ),
        require(
            coverage_counts == {
                "full_target_coverage_min_races": 18,
                "unattempted_target_race_count": 6,
            }
            and len(scanner_boundary_hits) == 1
            and scanner_boundary_hit.get("valid_evidence_scope") == scanner.SCANNER_VALID_EVIDENCE_SCOPE
            and scanner_boundary_hit.get("evidence_boundary_text") == scanner.SCANNER_EVIDENCE_BOUNDARY_TEXT
            and isinstance(scanner_boundary_hit.get("evidence_boundary"), dict)
            and scanner_boundary_hit["evidence_boundary"].get("not_settled_roi_evidence") is True
            and scanner_boundary_hit["evidence_boundary"].get("not_real_money_evidence") is True
            and scanner_boundary_hit["evidence_boundary"].get("baq_as_bel_substitution_allowed") is False
            and scanner.SCANNER_EVIDENCE_BOUNDARY_TEXT in scanner_no_hit_human
            and scanner.SCANNER_EVIDENCE_BOUNDARY_TEXT in scanner_hit_human
            and scanner.SCANNER_EVIDENCE_BOUNDARY_TEXT in scanner_hit_discord,
            "scanner_publishes_target_coverage_gap_counts",
            "scanner-side coverage metadata now gives operators the full target-race cap floor and unattempted target-candidate count after a capped run, while successful scanner hit rows plus human/Discord output carry source-level scanner evidence boundaries",
        ),
        require(
            scanner_valid_scope_line in scanner_no_hit_human
            and scanner_valid_scope_line in scanner_hit_human
            and scanner_valid_scope_line in scanner_hit_discord
            and scanner_valid_scope_line in scanner_no_matching_cards_stdout
            and scanner.SCANNER_EVIDENCE_BOUNDARY_TEXT in scanner_no_matching_cards_stdout
            and scanner_empty_csv_header
            == "rule_id,track,card_name,race_number,valid_evidence_scope,evidence_boundary_text",
            "scanner_text_and_empty_csv_outputs_publish_valid_scope",
            "human no-hit, human alert, Discord alert, no-matching-cards, and empty saved-CSV scanner outputs now expose the source-level valid_evidence_scope instead of leaving copied no-hit or alert text to rely only on evidence-boundary prose",
        ),
        require(
            api_access_scanner_status.get("http_status") == 403
            and api_access_scanner_status.get("api_failure_class") == "api_access_failure"
            and api_access_scanner_status.get("api_access_failure") is True
            and api_access_scanner_status.get("api_client_error") is True
            and api_access_scanner_status.get("api_failure_valid_scope") == "operator_refresh_context_only"
            and api_access_scanner_status.get("api_failure_operator_action") == "refresh_daily_wrapper_before_evidence_read"
            and api_access_scanner_status.get("api_failure_recheck_command") == "./run_daily_portfolio_observation.sh"
            and "not a no-target, clean-empty" in str(api_access_scanner_status.get("api_failure_boundary") or "")
            and api_access_scanner_status.get("valid_evidence_scope") == scanner.SCANNER_VALID_EVIDENCE_SCOPE
            and api_access_scanner_status.get("evidence_boundary_text") == scanner.SCANNER_EVIDENCE_BOUNDARY_TEXT
            and isinstance(api_access_scanner_status.get("evidence_boundary"), dict)
            and api_access_scanner_status["evidence_boundary"].get("not_promotion_readiness_evidence") is True
            and (
                api_access_scanner_status.get("result") == "scanner_error"
                or api_access_scanner_status.get("stale_cache_fallback_applied") is True
            ),
            "scanner_api_access_failure_or_fallback_sidecar_is_structured",
            "a synthetic HTTP 403 scanner path writes http_status=403 plus api_access_failure=true / api_failure_class=api_access_failure, explicit operator-action / recheck-command fields, and source-level scanner evidence boundaries even when stale cache fallback lets the scanner complete, so downstream helpers do not infer API-access context from prose alone",
        ),
        require(
            api_access_pipeline_status.get("scanner_api_access_failure") is True
            and api_access_pipeline_status.get("scanner_http_status") == 403
            and api_access_pipeline_status.get("scanner_api_failure_class") == "api_access_failure"
            and api_access_pipeline_status.get("scanner_api_failure_operator_action") == "refresh_daily_wrapper_before_evidence_read"
            and api_access_pipeline_status.get("scanner_api_failure_recheck_command") == "./run_daily_portfolio_observation.sh"
            and api_access_pipeline_status.get("observation_result") == "scanner_failed_empty_run"
            and api_access_pipeline_status.get("observation_scope") == "operational_limit"
            and api_access_pipeline_status.get("observation_reason") == "api_access_failure"
            and api_access_summary_payload.get("headline") == "scanner API access failure"
            and api_access_summary_payload.get("scanner_api_access_failure") is True
            and api_access_summary_payload.get("scanner_api_failure_operator_action") == "refresh_daily_wrapper_before_evidence_read"
            and api_access_summary_payload.get("scanner_api_failure_recheck_command") == "./run_daily_portfolio_observation.sh"
            and "HTTP 403" in api_access_summary_payload.get("detail_parts", [])
            and "API-access-failure operator context only" in api_access_summary_payload.get("detail_parts", [])
            and "operator action refresh_daily_wrapper_before_evidence_read" in api_access_summary_payload.get("detail_parts", [])
            and "recheck command ./run_daily_portfolio_observation.sh" in api_access_summary_payload.get("detail_parts", []),
            "pipeline_and_status_summary_preserve_api_access_failure_context",
            "pipeline hydration copies the scanner API-access fields and status-summary renders them as scanner API access failure / operational_limit with operator-action and recheck-command diagnostics instead of flattening 403 or stale-cache fallback into clean empty, no-target, or generic sample-collection context",
        ),
        require(
            summary_payload["headline"] == "limited coverage"
            and summary_payload["observation_reason"] == "max_race_limit_empty"
            and "max-races cap hit after 12 attempt(s)" in summary_payload["detail_parts"]
            and "18 target candidate race(s)" in summary_payload["detail_parts"]
            and "6 target candidate race(s) unattempted" in summary_payload["detail_parts"]
            and "raise --max-races to at least 18 for full target coverage" in summary_payload["detail_parts"]
            and summary_payload["unattempted_target_race_count"] == 6
            and summary_payload["full_target_coverage_min_races"] == 18,
            "status_summary_surfaces_limit_hit_and_candidate_count",
            "the lane status summary calls the run limited coverage and carries the cap hit, target-candidate count, unattempted count, and full-coverage cap floor in machine-readable details",
        ),
        require(
            lane_label == "LIMITED COVERAGE EMPTY"
            and day_bucket == "ACTIVE, LIMITED COVERAGE"
            and "max-races cap" in lane_detail
            and "6 target candidate race(s) unattempted" in lane_detail
            and "raise --max-races to at least 18 for full target coverage" in lane_detail,
            "ops_history_buckets_limit_hit_as_active_limited_coverage",
            "ops-history helpers route max-races empty reads into ACTIVE, LIMITED COVERAGE rather than ACTIVE, ZERO HITS while preserving the cap floor needed for a full target read",
        ),
        require(
            scorecard_gates.get("source") == "forward_evidence_scorecard.json"
            and scorecard_gates.get("source_path") == "decision_gate_minimums"
            and scorecard_gates.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and scorecard_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and scorecard_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and scorecard_gates.get("real_money_no_baq_as_bel_required") is True
            and "no BAQ-as-BEL substitution" in scorecard_gates.get("real_money_also_requires", [])
            and "do not count toward anchor-displacement" in scorecard_gates.get("evidence_boundary", ""),
            "scorecard_gate_boundary_preserved_for_synthetic_live_scan_checks",
            "synthetic live-scan targeting and limited-coverage checks now publish the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite while saying these scanner fixtures do not count toward those gates",
        ),
        require(
            EVIDENCE_BOUNDARY.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE,
            "direct_validation_report_exposes_live_scan_targeting_valid_scope",
            "the direct live-scan targeting validator report now exposes the raw valid_evidence_scope line and keeps capped-targeting / BAQ-BEL fixtures classified as guardrail metadata only",
        ),
    ]

    current_read = (
        "live scanner pre-detail targeting now spends race-detail attempts on rule-card/race-min candidates before --max-races is applied, "
        "does not alias BAQ as BEL even in an explicit BEL-vs-BAQ fixture that includes dangerous Belmont-substring Big A labels, carries scanner API-access-failure sidecar metadata structurally, including operator-action diagnostics, through the pipeline/status summary, and the scanner/status/ops layers now carry source-level scanner valid_evidence_scope lines and evidence boundaries plus both the unattempted target-candidate count and the cap floor needed for full target coverage while classifying max-races-limited no-hit reads as operationally limited coverage rather than clean empty forward observations"
        f"; the validator also exposes exact valid_evidence_scope={VALID_EVIDENCE_SCOPE} as synthetic guardrail metadata only and preserves the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as a boundary that synthetic scanner fixtures do not advance"
        " and fixture-tests boolean anchor floors, non-positive Phase 8 / real-money floors, and missing no-BAQ prerequisites as no-artifact malformed scorecard failures"
    )
    payload = {
        "suite_status": "pass",
        "artifact_status": "pass",
        "total_fixture_scenarios": 1,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "child_check_count": len(checks),
        "child_checks": checks,
        "summary": {"current_read": current_read},
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "report_path": str(report_md),
        },
        "synthetic_candidate_ids": candidate_ids,
        "synthetic_skipped_race_count": skipped,
        "synthetic_bel_alias_candidate_ids": bel_alias_candidate_ids,
        "synthetic_bel_alias_skipped_race_count": bel_alias_skipped,
        "synthetic_target_coverage_counts": coverage_counts,
        "synthetic_scanner_boundary_hit": scanner_boundary_hit,
        "synthetic_scanner_valid_scope_line": scanner_valid_scope_line,
        "synthetic_no_matching_cards_stdout": scanner_no_matching_cards_stdout,
        "synthetic_empty_scanner_csv_header": scanner_empty_csv_header,
        "synthetic_api_access_scanner_status": api_access_scanner_status,
        "synthetic_api_access_pipeline_status": api_access_pipeline_status,
        "synthetic_api_access_status_summary": api_access_summary_payload,
    }

    lines = [
        "# Live Scan Targeting and Limited-Coverage Validation",
        "",
        "This report validates the scanner pre-detail targeting guardrail plus max-races limited-coverage status routing.",
        "",
        "## Current Read",
        "",
        f"- {current_read}",
        "",
        "## Checks",
        "",
    ]
    for check in checks:
        lines.append(f"- PASS `{check['check']}` — {check['detail']}")
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
            f"- valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
            f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
            f"- Source scope: {EVIDENCE_BOUNDARY['source_scope']}",
            "- Not new forward evidence; not current-day scanner evidence; not settled ROI; not live-profitability evidence; not promotion-readiness evidence; not real-money evidence.",
            "- Green status here proves synthetic guardrail behavior only; it does not prove a quiet/no-signal day.",
            f"- Stronger forward confidence still requires: {', '.join(EVIDENCE_BOUNDARY['stronger_forward_confidence_requires'])}.",
            f"- Non-goals: {', '.join(EVIDENCE_BOUNDARY['non_goals'])}.",
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
            "## Rebuild",
            "",
            f"- Working directory: `{BASE}`",
            f"- Command: `{REBUILD_COMMAND}`",
            f"- Report path: `{report_md}`",
        ]
    )

    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {report_md}")
    print(f"Wrote {report_json}")
    print(f"PASS live_scan_targeting_and_limit_status {len(checks)}/{len(checks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
