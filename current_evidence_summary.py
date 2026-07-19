#!/usr/bin/env python3
"""
Current Evidence Summary — report-ready bridge from frozen ranking to live paper status.

Purpose:
- Give Cole one concise, current, report-safe read that combines the frozen
  scorecard posture with the latest paper-trade gate progress.
- Keep this summary as navigation/communication only: it does not create new
  forward evidence, promote rules, or support real-money claims.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parent
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
RIGHT_NOW_JSON = BASE / "PAPER_TRADE_NOW.json"
SETTLEMENT_AUDIT_JSON = BASE / "out" / "paper_trade_settlement_audit.json"
SCORECARD_AUDIT_MD = BASE / "SCORECARD_RANKING_CONTRACT_AUDIT.md"
SCORECARD_AUDIT_JSON = BASE / "scorecard_ranking_contract_audit.json"
MD_OUTPUT = BASE / "CURRENT_EVIDENCE_SUMMARY.md"
JSON_OUTPUT = BASE / "current_evidence_summary.json"
VALID_EVIDENCE_SCOPE = "current_evidence_bridge_report_navigation_only"
DAILY_WRAPPER_COMMAND = "./run_daily_portfolio_observation.sh"
SCORECARD_AUDIT_VALIDATOR_COMMAND = "python3 validate_scorecard_ranking_contract_audit.py"
REFRESH_ACTION_BOUNDARY_TEXT_FIELDS = [
    "command",
    "valid_use",
    "read",
]
REFRESH_ACTION_BOUNDARY_BOOL_FIELDS = [
    "required_before_right_now_instruction_use",
    "source_action_counts_as_current_instruction_before_refresh",
    "wrapper_refresh_can_update_operator_surfaces",
    "wrapper_refresh_can_settle_open_rows_by_itself",
    "wrapper_refresh_counts_as_roi_complete_evidence_by_itself",
    "clean_empty_refresh_counts_as_forward_performance",
    "missing_or_invalid_artifact_counts_as_clean_quiet_day",
    "not_forward_performance_evidence",
    "not_promotion_readiness_evidence",
    "not_live_profitability_evidence",
    "not_real_money_evidence",
]
CURRENT_BRIDGE_UPSTREAM_REFRESH_ORDER = [
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

HIT_TOKENS = {"hit", "won", "win", "winner", "cash", "cashed", "1", "true", "yes", "y"}
MISS_TOKENS = {"miss", "lost", "lose", "loss", "0", "false", "no", "n", "x"}
SETTLED_TS_PLACEHOLDER_TOKENS = {"", "open", "pending", "unsettled", "todo", "tbd", "na", "n/a", "none", "null"}
EXPECTED_AUDIT_UPSTREAM_SOURCE_LABELS = [
    "forward_evidence_scorecard_json",
    "primary_signals_ledger",
    "primary_settlement_ledger",
    "primary_rules_json",
    "shadow_signals_ledger",
    "shadow_settlement_ledger",
    "shadow_rules_json",
]
REFERENCE_TIME_ZONE = "America/New_York"
DECISION_GATE_THRESHOLD_SPECS = {
    "anchor_displacement": {
        "top_card_key": "anchor_displacement_min_roi_complete_settled_observations",
        "scorecard_key": "min_roi_complete_settled_observations",
    },
    "phase8_promotion_review": {
        "top_card_key": "phase8_promotion_review_min_roi_complete_settled_observations",
        "scorecard_key": "min_roi_complete_settled_observations",
    },
    "real_money_discussion": {
        "top_card_key": "real_money_discussion_min_total_settled_observations_with_usable_roi",
        "scorecard_key": "min_total_settled_observations_with_usable_roi",
    },
}
NO_BAQ_AS_BEL_REQUIREMENT = "no BAQ-as-BEL substitution"
OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY = "ci_only_promotion_diagnostics.OP_REFINED_K7"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a concise current evidence summary for Cole")
    parser.add_argument("--scorecard-json", default=str(SCORECARD_JSON), help="forward_evidence_scorecard.json path")
    parser.add_argument("--right-now-json", default=str(RIGHT_NOW_JSON), help="PAPER_TRADE_NOW.json path")
    parser.add_argument("--settlement-audit-json", default=str(SETTLEMENT_AUDIT_JSON), help="settlement audit JSON path")
    parser.add_argument("--md-output", default=str(MD_OUTPUT), help="markdown output path")
    parser.add_argument("--json-output", default=str(JSON_OUTPUT), help="JSON output path")
    parser.add_argument("--generated-at", help="Optional ISO/text timestamp for reproducible rerenders")
    parser.add_argument("--stdout-only", action="store_true", help="Print markdown only; do not write files or save notices")
    return parser.parse_args()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def file_fingerprint(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": display_path(path),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def source_fingerprint_matches_disk(fp: dict[str, Any]) -> tuple[bool, str]:
    path_text = str(fp.get("path") or "").strip()
    if not path_text:
        return False, "missing path"
    path = Path(path_text)
    if not path.is_absolute():
        path = BASE / path
    if not path.exists():
        return False, f"missing source path {path_text}"
    actual = file_fingerprint(path)
    ok = (
        fp.get("path") == actual.get("path")
        and int(fp.get("bytes", -1) or -1) == int(actual.get("bytes", -2) or -2)
        and fp.get("sha256") == actual.get("sha256")
        and fp.get("exists", True) is not False
    )
    return ok, f"saved={fp}; actual={actual}"


def build_audit_upstream_source_context(audit: dict[str, Any]) -> dict[str, Any]:
    sources = audit.get("source_files") if isinstance(audit.get("source_files"), dict) else {}
    labels = list(sources)
    missing = [label for label in EXPECTED_AUDIT_UPSTREAM_SOURCE_LABELS if label not in sources]
    malformed: list[str] = []
    drifted: list[str] = []
    for label, fp in sources.items():
        if not isinstance(fp, dict):
            malformed.append(label)
            continue
        sha = str(fp.get("sha256") or "")
        if not fp.get("path") or int(fp.get("bytes", 0) or 0) <= 0 or len(sha) != 64 or fp.get("exists", True) is not True:
            malformed.append(label)
            continue
        matches, _detail = source_fingerprint_matches_disk(fp)
        if not matches:
            drifted.append(label)
    expected_count = len(EXPECTED_AUDIT_UPSTREAM_SOURCE_LABELS)
    matching_count = max(len(labels) - len(missing) - len(malformed) - len(drifted), 0)
    all_match = not missing and not malformed and not drifted and set(labels) == set(EXPECTED_AUDIT_UPSTREAM_SOURCE_LABELS)
    if all_match:
        read = (
            f"settlement audit upstream source fingerprints match disk for {matching_count}/{expected_count} inputs "
            "(scorecard, primary/shadow rules, primary/shadow signal ledgers, and primary/shadow settlement ledgers); "
            "this is provenance metadata only, not forward-performance evidence."
        )
    else:
        read = (
            f"settlement audit upstream source fingerprints need attention: {matching_count}/{expected_count} expected inputs match; "
            f"missing={missing or 'none'}, malformed={malformed or 'none'}, drifted={drifted or 'none'}. "
            "Rerun `python3 paper_trade_settlement_audit.py` before quoting current paper totals."
        )
    return {
        "expected_labels": EXPECTED_AUDIT_UPSTREAM_SOURCE_LABELS,
        "labels": labels,
        "expected_count": expected_count,
        "matching_count": matching_count,
        "missing_labels": missing,
        "malformed_labels": malformed,
        "drifted_labels": drifted,
        "all_match": all_match,
        "source_files": sources,
        "read": read,
        "not_forward_performance_evidence": True,
    }


def require_audit_upstream_sources_current(
    audit_upstream_sources: dict[str, Any],
    settlement_audit_json_path: Path,
) -> None:
    if audit_upstream_sources.get("all_match") is True:
        return
    missing = audit_upstream_sources.get("missing_labels") or []
    malformed = audit_upstream_sources.get("malformed_labels") or []
    drifted = audit_upstream_sources.get("drifted_labels") or []
    raise ValueError(
        f"{settlement_audit_json_path.name} upstream source fingerprints are stale or incomplete; "
        "rerun `python3 paper_trade_settlement_audit.py` before `python3 current_evidence_summary.py`. "
        f"missing={missing}; malformed={malformed}; drifted={drifted}"
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def require_positive_non_bool_int(value: Any, label: str, scorecard_json_path: Path) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{scorecard_json_path.name} {label} must be a positive non-boolean integer")
    return value


def require_nonempty_string_list(value: Any, label: str, scorecard_json_path: Path) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{scorecard_json_path.name} {label} must be a non-empty string list")
    return [item.strip() for item in value]


def load_scorecard_ci_only_diagnostic(scorecard: dict[str, Any], scorecard_json_path: Path) -> dict[str, Any]:
    diagnostics = scorecard.get("ci_only_promotion_diagnostics")
    if not isinstance(diagnostics, dict):
        raise ValueError(f"{scorecard_json_path.name} is missing ci_only_promotion_diagnostics")
    diagnostic = diagnostics.get("OP_REFINED_K7")
    if not isinstance(diagnostic, dict):
        raise ValueError(f"{scorecard_json_path.name} is missing {OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}")
    if diagnostic.get("candidate_rule_id") != "OP_REFINED_K7":
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic has the wrong candidate_rule_id")
    if diagnostic.get("current_anchor_rule_id") != "OP_DURABLE_K7":
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic has the wrong current_anchor_rule_id")
    if diagnostic.get("positive_ci_lower_bound_is_support_context") is not True:
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic must mark positive CI as support context")
    if diagnostic.get("ci_only_promotion_allowed") is not False:
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic must keep ci_only_promotion_allowed=false")
    require_nonempty_string_list(
        diagnostic.get("why_not"),
        f"{OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}.why_not",
        scorecard_json_path,
    )
    required_before_review = diagnostic.get("required_before_review")
    if not isinstance(required_before_review, dict):
        raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic is missing required_before_review")
    for gate_name in ("phase8_promotion_review", "anchor_displacement"):
        if not str(required_before_review.get(gate_name) or "").strip():
            raise ValueError(f"{scorecard_json_path.name} OP_REFINED CI-only diagnostic missing {gate_name} review requirement")
    require_nonempty_string_list(
        diagnostic.get("does_not_count"),
        f"{OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}.does_not_count",
        scorecard_json_path,
    )
    return diagnostic


def build_gate_minimum_source_alignment(
    scorecard: dict[str, Any],
    top_card_gate_minimums: dict[str, Any],
    scorecard_json_path: Path,
) -> dict[str, Any]:
    scorecard_gates = scorecard.get("decision_gate_minimums")
    if not isinstance(scorecard_gates, dict):
        raise ValueError(f"{scorecard_json_path.name} is missing decision_gate_minimums")

    top_card_values: dict[str, int | None] = {}
    scorecard_values: dict[str, int] = {}
    effective_values: dict[str, int] = {}
    threshold_sources: dict[str, str] = {}
    mismatched_fields: list[str] = []
    missing_top_card_fields: list[str] = []

    for gate_name, spec in DECISION_GATE_THRESHOLD_SPECS.items():
        gate_payload = scorecard_gates.get(gate_name)
        if not isinstance(gate_payload, dict):
            raise ValueError(f"{scorecard_json_path.name} decision_gate_minimums is missing {gate_name}")
        scorecard_key = spec["scorecard_key"]
        scorecard_value = require_positive_non_bool_int(
            gate_payload.get(scorecard_key),
            f"decision_gate_minimums.{gate_name}.{scorecard_key}",
            scorecard_json_path,
        )

        top_card_key = spec["top_card_key"]
        top_card_value = int_or_none(top_card_gate_minimums.get(top_card_key))
        top_card_values[top_card_key] = top_card_value
        scorecard_values[top_card_key] = scorecard_value
        effective_values[top_card_key] = scorecard_value
        threshold_sources[gate_name] = f"{scorecard_json_path.name}:decision_gate_minimums.{gate_name}.{scorecard_key}"
        if top_card_value is None:
            missing_top_card_fields.append(top_card_key)
        if top_card_value != scorecard_value:
            mismatched_fields.append(top_card_key)

    real_money_gate = scorecard_gates.get("real_money_discussion")
    also_requires = real_money_gate.get("also_requires") if isinstance(real_money_gate, dict) else None
    if not isinstance(also_requires, list) or not all(isinstance(item, str) for item in also_requires):
        raise ValueError(
            f"{scorecard_json_path.name} decision_gate_minimums.real_money_discussion.also_requires must be a string list"
        )
    real_money_requirements = [item.strip() for item in also_requires]
    if NO_BAQ_AS_BEL_REQUIREMENT not in real_money_requirements:
        raise ValueError(
            f"{scorecard_json_path.name} decision_gate_minimums.real_money_discussion.also_requires must include no BAQ-as-BEL substitution"
        )

    values_match = not mismatched_fields
    read = (
        f"PAPER_TRADE_NOW decision-gate fields match {scorecard_json_path.name} decision_gate_minimums for "
        "anchor_displacement, phase8_promotion_review, and real_money_discussion."
        if values_match
        else (
            f"PAPER_TRADE_NOW decision-gate fields do not match {scorecard_json_path.name}: "
            f"{', '.join(mismatched_fields)}. "
            f"Missing top-card fields: {', '.join(missing_top_card_fields) if missing_top_card_fields else 'none'}. "
            f"Use {scorecard_json_path.name} decision_gate_minimums as the bridge's canonical gate floors and refresh the top card before quoting current gate progress."
        )
    )
    return {
        "scorecard_source_path": scorecard_json_path.name,
        "top_card_values": top_card_values,
        "scorecard_values": scorecard_values,
        "effective_values": effective_values,
        "effective_values_source": f"{scorecard_json_path.name}:decision_gate_minimums",
        "threshold_sources": threshold_sources,
        "real_money_discussion_also_requires": real_money_requirements,
        "real_money_no_baq_as_bel_required": NO_BAQ_AS_BEL_REQUIREMENT in real_money_requirements,
        "source_values_match_scorecard": values_match,
        "mismatched_fields": mismatched_fields,
        "missing_top_card_fields": missing_top_card_fields,
        "read": read,
    }


def build_scorecard_audit_route(gate_source_alignment: dict[str, Any]) -> dict[str, Any]:
    effective_values = gate_source_alignment["effective_values"]
    gate_floor_snapshot = {
        "anchor_displacement_min_roi_complete_settled_observations": effective_values.get(
            "anchor_displacement_min_roi_complete_settled_observations"
        ),
        "phase8_promotion_review_min_roi_complete_settled_observations": effective_values.get(
            "phase8_promotion_review_min_roi_complete_settled_observations"
        ),
        "real_money_discussion_min_total_settled_observations_with_usable_roi": effective_values.get(
            "real_money_discussion_min_total_settled_observations_with_usable_roi"
        ),
        "real_money_no_baq_as_bel_required": gate_source_alignment["real_money_no_baq_as_bel_required"],
    }
    route_read = (
        "Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus "
        "`python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 gate floors, "
        "tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and "
        "no-BAQ-as-BEL prerequisite drift across report-facing surfaces."
    )
    return {
        "markdown_path": display_path(SCORECARD_AUDIT_MD),
        "json_path": display_path(SCORECARD_AUDIT_JSON),
        "validator_command": SCORECARD_AUDIT_VALIDATOR_COMMAND,
        "gate_floor_source": gate_source_alignment["effective_values_source"],
        "gate_floor_snapshot": gate_floor_snapshot,
        "route_read": route_read,
        "valid_use": "navigation route for scorecard gate/ranking/CI-only/timezone/no-BAQ synchronization checks",
        "artifacts_present": SCORECARD_AUDIT_MD.exists() and SCORECARD_AUDIT_JSON.exists(),
        "not_forward_performance_evidence": True,
        "not_settled_roi_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_live_profitability_evidence": True,
        "not_bankroll_guidance": True,
        "not_real_money_evidence": True,
    }


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def format_generated_at(generated_at: str | None = None) -> str:
    if generated_at:
        text = generated_at.strip()
        parse_text = text[:-1] + "+00:00" if text.endswith("Z") else text
        try:
            parsed = datetime.fromisoformat(parse_text)
        except ValueError as exc:
            raise ValueError("generated_at must be timezone-aware ISO provenance metadata") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware ISO provenance metadata")
        return text
    return datetime.now().astimezone().isoformat(timespec="seconds")


def iso_date_token(value: Any) -> str | None:
    text = str(value or "").strip()
    if len(text) < 10:
        return None
    candidate = text[:10]
    try:
        datetime.fromisoformat(candidate)
    except ValueError:
        return None
    return candidate


def generated_reference_date_token(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    parse_text = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(parse_text)
    except ValueError:
        return iso_date_token(text)
    if parsed.tzinfo is None:
        return parsed.date().isoformat()
    return parsed.astimezone(ZoneInfo(REFERENCE_TIME_ZONE)).date().isoformat()


def iso_date_delta_days(start_date: str | None, end_date: str | None) -> int | None:
    if not start_date or not end_date:
        return None
    try:
        start = datetime.fromisoformat(start_date).date()
        end = datetime.fromisoformat(end_date).date()
    except ValueError:
        return None
    return (end - start).days


def build_operator_status_context(right_now: dict[str, Any]) -> dict[str, Any]:
    best_action = right_now.get("best_action") if isinstance(right_now.get("best_action"), dict) else {}
    ops = right_now.get("ops") if isinstance(right_now.get("ops"), dict) else {}
    headline = str(best_action.get("headline") or "")
    command = str(best_action.get("command") or "")
    why = str(best_action.get("why") or "")
    timing = str(best_action.get("timing") or "")
    day_bucket = str(ops.get("day_bucket") or "")
    takeaway = str(ops.get("takeaway") or "")
    best_action_joined = " ".join([headline, command, why, timing]).lower()
    ops_joined = " ".join([day_bucket, takeaway]).lower()
    joined = " ".join([best_action_joined, ops_joined]).lower()
    missing_scan_output_issue = (
        "missing scan-output" in joined
        or "scan-output artifact is missing" in joined
        or "scan-output artifact was missing" in joined
    )
    wrapper_refresh_action = "run_daily_portfolio_observation.sh" in command or "refresh the daily wrapper" in best_action_joined
    ops_takeaway_mentions_refresh = "refresh the daily wrapper" in ops_joined or "re-check sidecars" in ops_joined
    if missing_scan_output_issue:
        read = (
            "readable scanner-status sidecar plus missing scan-output artifact remains "
            "an operational refresh condition, not a clean no-qualifier observation or forward-performance evidence."
        )
    elif wrapper_refresh_action:
        read = (
            "right-now action points to wrapper refresh; treat it as operator readiness, "
            "not forward-performance evidence."
        )
    elif day_bucket == "ISSUE" and ops_takeaway_mentions_refresh:
        read = (
            "latest ops takeaway asks for refresh/re-check, while the current best action may still be settlement-first; "
            "treat both as operator routing metadata, not forward-performance evidence."
        )
    elif day_bucket or takeaway:
        read = "ops bucket/takeaway are routing metadata, not forward-performance evidence."
    else:
        read = "operator issue context unavailable from PAPER_TRADE_NOW; do not infer performance from missing routing metadata."
    return {
        "best_action_headline": headline or None,
        "best_action_command": command or None,
        "best_action_why": why or None,
        "best_action_timing": timing or None,
        "ops_day_bucket": day_bucket or None,
        "ops_takeaway": takeaway or None,
        "missing_scan_output_artifact_issue": missing_scan_output_issue,
        "wrapper_refresh_action": wrapper_refresh_action,
        "ops_takeaway_mentions_refresh": ops_takeaway_mentions_refresh,
        "read": read,
        "valid_use": "operator routing and source-readiness context only",
        "not_forward_performance_evidence": True,
    }


def build_primary_recommendation_context(primary: dict[str, Any], right_now: dict[str, Any]) -> dict[str, Any]:
    latest_context = str(primary.get("recent_run_context") or "").strip()
    ops = right_now.get("ops") if isinstance(right_now.get("ops"), dict) else {}
    ops_takeaway = str(ops.get("takeaway") or "").strip()
    joined = " ".join([latest_context, ops_takeaway]).lower()
    no_bet_latest_context = "no bet recommendations" in joined or "nothing reached a bet-ready state" in joined
    scanner_failure_boundary_context = (
        "api-access-failure operator context only" in joined
        or "scanner-error operator context only" in joined
        or "not a no-target, clean-empty, or forward-performance read" in joined
    )
    stale_cache_fallback_context = "stale-cache fallback" in joined or "stale cache fallback" in joined
    bet_ready_latest_context = (
        not no_bet_latest_context
        and not scanner_failure_boundary_context
        and (
            "bet recommendation" in joined
            or "bet-ready" in joined
            or "tickets selected" in joined
        )
    )
    if latest_context:
        if no_bet_latest_context:
            read = (
                f"{latest_context} The latest recommendation context is a qualifying scanner observation with no BET recommendation, "
                "not a bet-ready ticket; settle only from actual result/payout evidence and do not interpret the open row as forward performance."
            )
        elif bet_ready_latest_context:
            read = (
                f"{latest_context} Bet-readiness still depends on the recommendation ledger and later ROI-complete settlement; "
                "do not treat the recommendation context itself as forward performance."
            )
        elif scanner_failure_boundary_context:
            read = (
                f"{latest_context} Use recommendation and settlement ledgers before interpreting bet readiness or forward performance."
            )
        else:
            read = (
                f"{latest_context} Treat this as operator context only; use recommendation and settlement ledgers before "
                "interpreting bet readiness or forward performance."
            )
    else:
        read = (
            "No latest primary recommendation context was published by PAPER_TRADE_NOW; use recommendation and settlement ledgers before "
            "interpreting bet readiness or forward performance."
        )
    return {
        "latest_run_context": latest_context or None,
        "ops_takeaway": ops_takeaway or None,
        "latest_context_has_no_bet_recommendations": no_bet_latest_context,
        "latest_context_has_scanner_failure_boundary": scanner_failure_boundary_context,
        "latest_context_has_stale_cache_fallback": stale_cache_fallback_context,
        "latest_context_has_bet_ready_language": bet_ready_latest_context,
        "read": read,
        "valid_use": "recommendation-state operator context only",
        "not_forward_performance_evidence": True,
        "not_bet_readiness_evidence_by_itself": True,
    }


def build_operator_read_gate(
    source_freshness: dict[str, Any],
    operator_status_context: dict[str, Any],
    primary_recommendation_context: dict[str, Any],
    best_action_for_use: dict[str, Any],
) -> dict[str, Any]:
    """Publish a structured gate for whether the saved top card can be read as current."""
    joined = " ".join(
        str(value or "")
        for value in [
            operator_status_context.get("best_action_headline"),
            operator_status_context.get("best_action_why"),
            operator_status_context.get("ops_day_bucket"),
            operator_status_context.get("ops_takeaway"),
            primary_recommendation_context.get("latest_run_context"),
            primary_recommendation_context.get("ops_takeaway"),
            primary_recommendation_context.get("read"),
        ]
    )
    joined_lower = joined.lower()
    has_api_access_failure = (
        "api-access-failure" in joined_lower
        or "api access failure" in joined_lower
        or "api-access scanner failure" in joined_lower
        or "http 403" in joined_lower
        or "403 client error" in joined_lower
    )
    has_scanner_failure_boundary = bool(primary_recommendation_context.get("latest_context_has_scanner_failure_boundary"))
    has_stale_cache_fallback = bool(primary_recommendation_context.get("latest_context_has_stale_cache_fallback"))
    has_missing_scan_output = bool(operator_status_context.get("missing_scan_output_artifact_issue"))
    has_wrapper_refresh_action = bool(operator_status_context.get("wrapper_refresh_action"))
    has_issue_bucket = "ISSUE" in str(operator_status_context.get("ops_day_bucket") or "").upper()
    requires_source_refresh = bool(source_freshness.get("requires_refresh_before_right_now_use"))
    requires_refresh_before_evidence_read = any(
        [
            requires_source_refresh,
            has_api_access_failure,
            has_scanner_failure_boundary,
            has_stale_cache_fallback,
            has_missing_scan_output,
            has_wrapper_refresh_action,
            has_issue_bucket,
        ]
    )
    reasons: list[str] = []
    if requires_source_refresh:
        reasons.append("source freshness requires wrapper refresh")
    if has_api_access_failure:
        reasons.append("scanner/API-access failure context is present")
    elif has_scanner_failure_boundary:
        reasons.append("scanner failure boundary is present")
    if has_stale_cache_fallback:
        reasons.append("stale-cache fallback context is present")
    if has_missing_scan_output:
        reasons.append("scan-output artifact issue is present")
    if has_wrapper_refresh_action:
        reasons.append("best action points to wrapper refresh")
    if has_issue_bucket:
        reasons.append("ops bucket is ISSUE")
    reason_text = "; ".join(dict.fromkeys(reasons)) if reasons else "no refresh-first operator issue surfaced"
    command = str(best_action_for_use.get("command") or DAILY_WRAPPER_COMMAND)
    if requires_refresh_before_evidence_read:
        read = (
            f"Refresh/recheck with `{command}` before using the saved top card as today's instruction "
            f"or evidence; reasons: {reason_text}. This is not a no-target, clean-empty, bet-readiness, settled ROI, "
            "promotion, live-profitability, bankroll, or real-money read."
        )
        gate_status = "refresh_required_before_evidence_read"
    else:
        read = (
            f"Saved top card can be read as current operator routing context with `{command}`, "
            "but it is still not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence."
        )
        gate_status = "current_operator_routing_context_only"
    return {
        "gate_status": gate_status,
        "requires_refresh_before_evidence_read": requires_refresh_before_evidence_read,
        "requires_source_freshness_refresh": requires_source_refresh,
        "has_api_access_failure_context": has_api_access_failure,
        "has_scanner_failure_boundary": has_scanner_failure_boundary,
        "has_stale_cache_fallback_context": has_stale_cache_fallback,
        "has_missing_scan_output_artifact_issue": has_missing_scan_output,
        "has_wrapper_refresh_action": has_wrapper_refresh_action,
        "has_issue_bucket": has_issue_bucket,
        "reason_text": reason_text,
        "recommended_command": command,
        "current_top_card_counts_as_no_target_evidence": False,
        "current_top_card_counts_as_clean_empty_evidence": False,
        "current_top_card_counts_as_bet_readiness_evidence": False,
        "current_top_card_counts_as_settled_roi_evidence": False,
        "not_forward_performance_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_live_profitability_evidence": True,
        "not_real_money_evidence": True,
        "valid_use": "operator instruction/evidence-read gating only",
        "read": read,
    }


def build_bridge_best_action(source_best_action: dict[str, Any], source_freshness: dict[str, Any]) -> dict[str, Any]:
    """Return the action this bridge should show as usable right now.

    The source PAPER_TRADE_NOW card can be stale relative to the bridge render
    date. In that case the bridge must not keep showing a lane-only settlement,
    monitor, or stand-down command as the current instruction. It can preserve
    that source action as inherited context, but the usable action should fail
    closed to the daily wrapper refresh.
    """
    action = dict(source_best_action) if isinstance(source_best_action, dict) else {}
    command = str(action.get("command") or "")
    requires_refresh = bool(source_freshness.get("requires_refresh_before_right_now_use"))

    if requires_refresh and "run_daily_portfolio_observation.sh" not in command:
        inherited_headline = str(action.get("headline") or "source best action").strip()
        inherited_command = str(action.get("command") or "").strip()
        inherited_bits = [inherited_headline]
        if inherited_command:
            inherited_bits.append(inherited_command)
        inherited_read = " / ".join(inherited_bits)
        return {
            "headline": "Refresh the daily wrapper before using stale right-now card",
            "lane_key": action.get("lane_key"),
            "lane": action.get("lane") or "All paper-trade lanes",
            "command": DAILY_WRAPPER_COMMAND,
            "why": (
                f"{source_freshness.get('read')} The inherited source action ({inherited_read}) is kept as stale context only "
                "until the wrapper refreshes the run artifacts."
            ),
            "timing": "now",
            "source_action_overridden": True,
            "override_reason": source_freshness.get("requires_refresh_reason"),
            "inherited_source_action": action,
        }

    action.setdefault("source_action_overridden", False)
    action.setdefault("override_reason", None)
    return action


def build_source_freshness(generated_text: str, right_now: dict[str, Any]) -> dict[str, Any]:
    run_freshness = right_now.get("run_freshness") if isinstance(right_now.get("run_freshness"), dict) else {}
    generated_date = iso_date_token(generated_text)
    generated_reference_date = generated_reference_date_token(generated_text)
    run_date = iso_date_token(run_freshness.get("run_date"))
    as_of_date = iso_date_token(run_freshness.get("as_of_date"))
    freshness_state = str(run_freshness.get("freshness_state") or "").strip()
    valid_freshness_states = {"current_run_date", "stale_past_run", "future_run_date", "unknown_run_date"}
    freshness_state_valid = freshness_state in valid_freshness_states
    comparison_date = generated_reference_date or generated_date
    is_stale_vs_generated_date = bool(comparison_date and as_of_date and as_of_date < comparison_date)
    right_now_internal_is_stale = bool(run_freshness.get("is_stale"))
    internal_age_days = max(iso_date_delta_days(run_date, as_of_date) or 0, 0)
    source_age_days = max(iso_date_delta_days(as_of_date, comparison_date) or 0, 0)
    refresh_age_days = max(
        internal_age_days if right_now_internal_is_stale else 0,
        source_age_days if is_stale_vs_generated_date else 0,
        0,
    )
    requires_refresh = is_stale_vs_generated_date or right_now_internal_is_stale or not freshness_state_valid
    if right_now_internal_is_stale and is_stale_vs_generated_date:
        read = (
            f"Right-now card is stale for its own as-of date: run date {run_date or 'unknown'} vs as-of date {as_of_date or 'unknown'}; "
            f"right-now source as-of date {as_of_date or 'unknown'} is also older than bridge reference date {comparison_date or 'unknown'} "
            f"({REFERENCE_TIME_ZONE}); "
            f"refresh `./run_daily_portfolio_observation.sh` before treating the best-action card as today's operator instruction. "
            f"Staleness age: {refresh_age_days} day(s)."
        )
        reason = "right_now_internal_and_source_stale"
    elif right_now_internal_is_stale:
        read = (
            f"Right-now card is stale for its own as-of date: run date {run_date or 'unknown'} vs as-of date {as_of_date or 'unknown'}; "
            f"refresh `./run_daily_portfolio_observation.sh` before treating the best-action card as today's operator instruction. "
            f"Staleness age: {refresh_age_days} day(s)."
        )
        reason = "right_now_internal_stale"
    elif is_stale_vs_generated_date:
        read = (
            f"Right-now source as-of date {as_of_date} is older than bridge reference date {comparison_date} "
            f"({REFERENCE_TIME_ZONE}); "
            f"refresh `./run_daily_portfolio_observation.sh` before treating the best-action card as today's operator instruction. "
            f"Staleness age: {refresh_age_days} day(s)."
        )
        reason = "source_as_of_older_than_bridge"
    elif not freshness_state_valid:
        read = (
            f"Right-now card did not publish a valid freshness_state (`{freshness_state or 'missing'}`), so refresh `./run_daily_portfolio_observation.sh` "
            "before treating the best-action card as today's operator instruction."
        )
        reason = "right_now_freshness_state_missing_or_invalid"
    else:
        read = (
            f"Right-now source as-of date {as_of_date or 'unknown'} is not older than bridge reference date {comparison_date or 'unknown'} "
            f"({REFERENCE_TIME_ZONE}); "
            "still treat the bridge as report/navigation context rather than performance evidence."
        )
        reason = "source_current_for_bridge"
    refresh_action_boundary = {
        "command": DAILY_WRAPPER_COMMAND,
        "required_before_right_now_instruction_use": requires_refresh,
        "source_action_counts_as_current_instruction_before_refresh": not requires_refresh,
        "wrapper_refresh_can_update_operator_surfaces": True,
        "wrapper_refresh_can_settle_open_rows_by_itself": False,
        "wrapper_refresh_counts_as_roi_complete_evidence_by_itself": False,
        "clean_empty_refresh_counts_as_forward_performance": False,
        "missing_or_invalid_artifact_counts_as_clean_quiet_day": False,
        "valid_use": "operator-card freshness and rerun routing boundary",
        "read": (
            f"run `{DAILY_WRAPPER_COMMAND}` before using stale right-now instructions; "
            "a wrapper refresh can update operator surfaces, but by itself it does not settle open rows, "
            "create ROI-complete evidence, promote OP_DURABLE_K7, or support real-money discussion."
        ),
        "not_forward_performance_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_live_profitability_evidence": True,
        "not_real_money_evidence": True,
    }
    return {
        "generated_date": generated_date,
        "generated_reference_date": generated_reference_date,
        "generated_reference_timezone": REFERENCE_TIME_ZONE,
        "generated_reference_date_differs_from_local_date": bool(
            generated_date and generated_reference_date and generated_date != generated_reference_date
        ),
        "right_now_run_date": run_date,
        "right_now_as_of_date": as_of_date,
        "right_now_freshness_state": freshness_state or None,
        "right_now_freshness_state_valid": freshness_state_valid,
        "right_now_internal_is_stale": right_now_internal_is_stale,
        "is_stale_vs_generated_date": is_stale_vs_generated_date,
        "right_now_internal_stale_age_days": internal_age_days,
        "source_stale_age_days_vs_bridge": source_age_days,
        "refresh_age_days": refresh_age_days,
        "staleness_comparison_date": comparison_date,
        "staleness_comparison_source": "generated_reference_date",
        "requires_refresh_before_right_now_use": requires_refresh,
        "requires_refresh_reason": reason,
        "refresh_action_boundary": refresh_action_boundary,
        "read": read,
        "not_forward_performance_evidence": True,
    }


def build_calendar_context(source_freshness: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_local_date": source_freshness.get("generated_date"),
        "generated_reference_date": source_freshness.get("generated_reference_date"),
        "generated_reference_timezone": source_freshness.get("generated_reference_timezone"),
        "right_now_run_date": source_freshness.get("right_now_run_date"),
        "right_now_as_of_date": source_freshness.get("right_now_as_of_date"),
        "staleness_comparison_date": source_freshness.get("staleness_comparison_date"),
        "staleness_comparison_source": source_freshness.get("staleness_comparison_source"),
        "generated_reference_date_differs_from_local_date": source_freshness.get(
            "generated_reference_date_differs_from_local_date"
        ),
        "requires_refresh_before_right_now_use": source_freshness.get("requires_refresh_before_right_now_use"),
        "read": (
            "Calendar dates are operator-readiness context only: freshness uses the "
            f"{source_freshness.get('generated_reference_timezone')} reference date "
            f"{source_freshness.get('staleness_comparison_date')} for racing-card comparison while preserving "
            f"the local generated date {source_freshness.get('generated_date')} as provenance."
        ),
        "not_forward_performance_evidence": True,
        "not_live_profitability_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_real_money_evidence": True,
    }


def pct(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "n/a"
    return f"{value * 100:+.2f}%" if value < 0 else f"{value * 100:.2f}%"


def money(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return "n/a"
    return f"${value:,.2f}"


def keyed_items_text(value: Any) -> str:
    if isinstance(value, dict):
        return "; ".join(f"{key} = {item}" for key, item in value.items())
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return str(value or "")


def clean_outcome(value: str | None) -> str:
    text = str(value or "").strip().lower()
    if text in HIT_TOKENS:
        return "hit"
    if text in MISS_TOKENS:
        return "miss"
    return "other"


def settled_ts_gap_reason(value: Any) -> str:
    """Mirror the settlement audit's timestamp standard for ROI-complete rows."""
    text = str(value or "").strip()
    normalized = text.lower()
    if not text:
        return "missing settled_ts"
    if normalized in SETTLED_TS_PLACEHOLDER_TOKENS or (text.startswith("<") and text.endswith(">")):
        return "placeholder settled_ts"
    if "T" not in text and " " not in text:
        return "malformed settled_ts"
    parse_text = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        datetime.fromisoformat(parse_text)
    except ValueError:
        return "malformed settled_ts"
    return ""


def rule_row(scorecard: dict[str, Any], rule_id: str) -> dict[str, Any]:
    for row in scorecard.get("rows", []):
        if row.get("rule_id") == rule_id:
            return row
    return {}


def lane_by_name(audit: dict[str, Any], name: str) -> dict[str, Any]:
    for lane in audit.get("lanes", []):
        if lane.get("name") == name:
            return lane
    return {}


def summarize_settlement_csv(path: Path) -> dict[str, Any]:
    rows = load_csv_rows(path)
    hit_count = 0
    miss_count = 0
    settled_rows = 0
    total_cost = 0.0
    total_return = 0.0
    settled_ts_gap_counts: Counter[str] = Counter()
    non_positive_cost_rows = 0
    for row in rows:
        outcome = clean_outcome(row.get("outcome"))
        if outcome not in {"hit", "miss"}:
            continue
        try:
            actual_cost = float(str(row.get("actual_cost") or "").strip())
            actual_return = float(str(row.get("actual_return") or "").strip())
        except ValueError:
            continue
        if not (math.isfinite(actual_cost) and math.isfinite(actual_return)) or actual_cost < 0 or actual_return < 0:
            continue
        timestamp_gap = settled_ts_gap_reason(row.get("settled_ts"))
        if timestamp_gap:
            settled_ts_gap_counts[timestamp_gap] += 1
            continue
        if actual_cost <= 0:
            non_positive_cost_rows += 1
            continue
        settled_rows += 1
        total_cost += actual_cost
        total_return += actual_return
        if outcome == "hit":
            hit_count += 1
        else:
            miss_count += 1
    roi = (total_return / total_cost - 1.0) if total_cost > 0 else None
    hit_rate = (hit_count / settled_rows) if settled_rows else None
    return {
        "path": display_path(path),
        "row_count": len(rows),
        "roi_complete_rows_from_csv": settled_rows,
        "hit_count": hit_count,
        "miss_count": miss_count,
        "hit_rate": hit_rate,
        "actual_cost_sum": total_cost,
        "actual_return_sum": total_return,
        "flat_ticket_roi": roi,
        "settled_ts_gap_rows_from_csv": sum(settled_ts_gap_counts.values()),
        "settled_ts_gap_reason_counts": dict(sorted(settled_ts_gap_counts.items())),
        "non_positive_cost_rows_from_csv": non_positive_cost_rows,
    }


def build_payload(
    generated_at: str | None = None,
    scorecard_json_path: Path = SCORECARD_JSON,
    right_now_json_path: Path = RIGHT_NOW_JSON,
    settlement_audit_json_path: Path = SETTLEMENT_AUDIT_JSON,
) -> dict[str, Any]:
    scorecard = load_json(scorecard_json_path)
    right_now = load_json(right_now_json_path)
    audit = load_json(settlement_audit_json_path)

    primary = right_now.get("primary", {})
    shadow = right_now.get("shadow", {})
    live_hierarchy = right_now.get("live_hierarchy", {})
    primary_lane = lane_by_name(audit, "primary")
    shadow_lane = lane_by_name(audit, "shadow")
    primary_signal_path = BASE / str(primary.get("files", {}).get("signals_ledger", "paper_trades/phase7_current_paper_paper_trade_signals.csv"))
    settlement_path = BASE / str(primary.get("files", {}).get("settlement_ledger", "paper_trades/phase7_current_paper_paper_trade_settlements.csv"))
    shadow_signal_path = BASE / str(shadow.get("files", {}).get("signals_ledger", "paper_trades/phase8_shadow_paper_trade_signals.csv"))
    shadow_settlement_path = BASE / str(shadow.get("files", {}).get("settlement_ledger", "paper_trades/phase8_shadow_paper_trade_settlements.csv"))
    settlement_summary = summarize_settlement_csv(settlement_path)

    gate_minimums = right_now.get("decision_gate_minimums", {})
    if not isinstance(gate_minimums, dict):
        gate_minimums = {}
    gate_source_alignment = build_gate_minimum_source_alignment(scorecard, gate_minimums, scorecard_json_path)
    scorecard_audit_route = build_scorecard_audit_route(gate_source_alignment)
    ci_only_diagnostic = load_scorecard_ci_only_diagnostic(scorecard, scorecard_json_path)
    ci_only_diagnostic_source = f"{scorecard_json_path.name}:{OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}"
    ci_only_promotion_check = {
        "source": ci_only_diagnostic_source,
        "candidate_rule_id": ci_only_diagnostic["candidate_rule_id"],
        "current_anchor_rule_id": ci_only_diagnostic["current_anchor_rule_id"],
        "positive_ci_lower_bound_is_support_context": ci_only_diagnostic["positive_ci_lower_bound_is_support_context"],
        "ci_only_promotion_allowed": ci_only_diagnostic["ci_only_promotion_allowed"],
        "why_not": ci_only_diagnostic["why_not"],
        "required_before_review": ci_only_diagnostic["required_before_review"],
        "does_not_count": ci_only_diagnostic["does_not_count"],
        "scorecard_ci_only_promotion_diagnostic": ci_only_diagnostic,
        "read": (
            f"Scorecard CI-only promotion check: `{ci_only_diagnostic_source}` keeps "
            "`ci_only_promotion_allowed=false`; OP_REFINED's positive CI lower bound is support context only, "
            "not a current paper promotion trigger."
        ),
        "valid_use": "source-matched shadow/watch evidence-class boundary for current report wording",
        "not_forward_performance_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_live_profitability_evidence": True,
        "not_real_money_evidence": True,
    }
    first_read = primary.get("sample_progress", {}).get("first_read", {})
    portfolio_review = primary.get("sample_progress", {}).get("portfolio_review", {})
    primary_gate = primary_lane.get("promotion_gate", {})
    primary_rule_progress = primary_gate.get("rule_progress", []) if isinstance(primary_gate, dict) else []
    primary_rule_counts = {
        str(row.get("rule_id")): int(row.get("roi_complete_settled_rows", 0) or 0)
        for row in primary_rule_progress
    }
    op_primary_rows = primary_rule_counts.get("OP_DURABLE_K7", 0)
    cd_primary_rows = primary_rule_counts.get("CD_CORE_K8", 0)
    if op_primary_rows == 0 and cd_primary_rows > 0:
        primary_rule_context = "Current settled paper context is CD-only, so it should not be counted as OP-anchor forward evidence."
    elif op_primary_rows > 0 and cd_primary_rows == 0:
        primary_rule_context = "Current settled paper context is OP-only; keep CD companion reads separate until CD has ROI-complete rows."
    elif op_primary_rows > 0 and cd_primary_rows > 0:
        primary_rule_context = "Current settled paper context spans OP and CD; keep OP-anchor and CD-companion reads rule-specific."
    else:
        primary_rule_context = "Current primary paper has no ROI-complete rule-specific settled rows yet."
    primary_rule_mix_read = (
        f"Primary rule mix: OP_DURABLE_K7 has {op_primary_rows} ROI-complete settled row(s); "
        f"CD_CORE_K8 has {cd_primary_rows}. {primary_rule_context}"
    )
    shadow_gate = shadow_lane.get("promotion_gate", {})
    shadow_rule_progress = shadow_gate.get("rule_progress", []) if isinstance(shadow_gate, dict) else []
    shadow_rule_progress_read = "; ".join(
        (
            f"{row.get('rule_id')} ({row.get('scorecard_tier', 'UNKNOWN')}) "
            f"{row.get('promotion_progress', '0/20 (0.0%)')}"
        )
        for row in shadow_rule_progress
    )
    if not shadow_rule_progress_read:
        shadow_rule_progress_read = "No shadow rule progress rows available; rerun the settlement audit before quoting Phase 8 watch-list coverage."

    anchor_row = rule_row(scorecard, str(live_hierarchy.get("current_anchor") or "OP_DURABLE_K7"))
    companion_row = rule_row(scorecard, str(live_hierarchy.get("primary_companion") or "CD_CORE_K8"))
    shadow_lead_row = rule_row(scorecard, str(live_hierarchy.get("secondary_shadow") or "OP_REFINED_K7"))

    first_remaining = int(first_read.get("remaining", 0) or 0)
    primary_settled = int(primary.get("settled", primary_lane.get("settled_outcome_rows", 0)) or 0)
    primary_open = int(primary.get("open_settlements", primary_lane.get("open_settlement_rows", 0)) or 0)
    primary_open_details = (
        primary_lane.get("open_settlement_row_details", [])
        if isinstance(primary_lane.get("open_settlement_row_details"), list)
        else []
    )
    primary_open_summary = str(primary_lane.get("open_settlement_summary") or "").strip()
    if not primary_open_summary:
        primary_open_summary = "none"
    primary_incomplete = int(primary.get("incomplete_settlements", primary_lane.get("incomplete_settled_rows", 0)) or 0)
    primary_roi_complete = int(primary.get("roi_covered_settled", primary_lane.get("roi_complete_settled_rows", 0)) or 0)
    primary_open_rule_counts = Counter()
    for row in primary_open_details:
        if not isinstance(row, dict):
            continue
        rule_id = str(row.get("rule_id") or "").strip() or "UNKNOWN"
        primary_open_rule_counts[rule_id] += 1
    primary_open_rows_with_rule_id = sum(primary_open_rule_counts.values())
    primary_open_rows_without_published_rule_id = max(primary_open - primary_open_rows_with_rule_id, 0)
    primary_roi_gap = int(primary.get("roi_gap_settlements", primary_lane.get("roi_gap_settled_rows", 0)) or 0)
    anchor_effective_value = gate_source_alignment["effective_values"].get(
        "anchor_displacement_min_roi_complete_settled_observations"
    )
    anchor_review_threshold = int(
        anchor_effective_value
        if anchor_effective_value is not None
        else first_read.get("threshold")
        or 30
    )
    anchor_settlement_gap = {
        "anchor_rule_id": "OP_DURABLE_K7",
        "companion_rule_id": "CD_CORE_K8",
        "anchor_roi_complete_settled_rows": op_primary_rows,
        "companion_roi_complete_settled_rows": cd_primary_rows,
        "lane_roi_complete_settled_rows": primary_roi_complete,
        "open_settlement_rows": primary_open,
        "same_candidate_anchor_review_floor": anchor_review_threshold,
        "anchor_rows_needed_for_same_candidate_review": max(anchor_review_threshold - op_primary_rows, 0),
        "anchor_specific_review_ready": op_primary_rows >= anchor_review_threshold,
        "current_sample_is_cd_only": op_primary_rows == 0 and cd_primary_rows > 0,
        "companion_rows_count_as_anchor_evidence": False,
        "valid_use": "rule-specific settlement coverage context for keeping OP-anchor and CD-companion reads separate",
        "not_forward_performance_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_live_profitability_evidence": True,
        "not_real_money_evidence": True,
    }
    anchor_settlement_gap["read"] = (
        f"OP-anchor settlement gap: {anchor_settlement_gap['anchor_rule_id']} has {op_primary_rows} ROI-complete settled row(s); "
        f"{anchor_settlement_gap['companion_rule_id']} has {cd_primary_rows}. "
        f"Need {anchor_settlement_gap['anchor_rows_needed_for_same_candidate_review']} more "
        f"{anchor_settlement_gap['anchor_rule_id']} ROI-complete row(s) before the "
        f"{anchor_review_threshold}-row same-candidate anchor-review floor is even count-complete. "
        "CD companion rows do not reduce that OP-anchor gap."
    )
    open_rows_by_rule = dict(sorted(primary_open_rule_counts.items()))
    open_rows_by_rule.setdefault(anchor_settlement_gap["anchor_rule_id"], 0)
    open_rows_by_rule.setdefault(anchor_settlement_gap["companion_rule_id"], 0)
    other_open_rule_rows = sum(
        count
        for rule_id, count in open_rows_by_rule.items()
        if rule_id not in {anchor_settlement_gap["anchor_rule_id"], anchor_settlement_gap["companion_rule_id"]}
    )
    open_settlement_queue_by_rule = {
        "anchor_rule_id": anchor_settlement_gap["anchor_rule_id"],
        "companion_rule_id": anchor_settlement_gap["companion_rule_id"],
        "open_rows_by_rule": dict(sorted(open_rows_by_rule.items())),
        "total_open_rows": primary_open,
        "published_open_row_detail_count": len(primary_open_details),
        "open_rows_with_published_rule_id": primary_open_rows_with_rule_id,
        "open_rows_without_published_rule_id": primary_open_rows_without_published_rule_id,
        "anchor_open_rows": open_rows_by_rule.get(anchor_settlement_gap["anchor_rule_id"], 0),
        "companion_open_rows": open_rows_by_rule.get(anchor_settlement_gap["companion_rule_id"], 0),
        "other_open_rule_rows": other_open_rule_rows,
        "current_open_queue_is_cd_only": (
            open_rows_by_rule.get(anchor_settlement_gap["anchor_rule_id"], 0) == 0
            and open_rows_by_rule.get(anchor_settlement_gap["companion_rule_id"], 0) > 0
            and other_open_rule_rows == 0
        ),
        "open_rows_count_as_roi_complete": False,
        "open_rows_count_as_anchor_evidence": False,
        "valid_use": "settlement workflow triage for preserving rule identity before outcomes are ROI-complete",
        "not_forward_performance_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_live_profitability_evidence": True,
        "not_real_money_evidence": True,
    }
    open_settlement_queue_by_rule["open_settlement_queue_state"] = "closed" if primary_open == 0 else "open"
    open_settlement_queue_by_rule["open_settlement_context"] = (
        "no open primary settlement rows"
        if primary_open == 0
        else primary_open_summary
    )
    open_settlement_queue_by_rule["detail_read"] = (
        f"Open settlement queue by rule: {open_settlement_queue_by_rule['anchor_rule_id']} has "
        f"{open_settlement_queue_by_rule['anchor_open_rows']} open row(s); "
        f"{open_settlement_queue_by_rule['companion_rule_id']} has "
        f"{open_settlement_queue_by_rule['companion_open_rows']}; other primary rules have "
        f"{open_settlement_queue_by_rule['other_open_rule_rows']}; "
        f"{open_settlement_queue_by_rule['open_rows_without_published_rule_id']} open row(s) lack published rule IDs. "
        "Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence."
    )
    open_settlement_queue_by_rule["read"] = (
        "Settlement queue state: "
        f"{open_settlement_queue_by_rule['open_settlement_queue_state']}; "
        f"{open_settlement_queue_by_rule['open_settlement_context']}; detail: "
        f"{open_settlement_queue_by_rule['detail_read']}"
    )
    audit_primary_roi_complete = int(primary_lane.get("roi_complete_settled_rows", 0) or 0)
    csv_primary_roi_complete = int(settlement_summary["roi_complete_rows_from_csv"])
    audit_cost_sum = float(primary_lane.get("roi_complete_cost_sum", 0.0) or 0.0)
    audit_return_sum = float(primary_lane.get("roi_complete_return_sum", 0.0) or 0.0)
    audit_reason_counts = primary_lane.get("roi_gap_reason_counts", {})
    audit_settled_ts_gap_rows = sum(
        int(count or 0)
        for reason, count in (audit_reason_counts.items() if isinstance(audit_reason_counts, dict) else [])
        if "settled_ts" in str(reason)
    )
    audit_upstream_sources = build_audit_upstream_source_context(audit)
    require_audit_upstream_sources_current(audit_upstream_sources, settlement_audit_json_path)
    source_consistency = {
        "overall_match": (
            primary_roi_complete == audit_primary_roi_complete == csv_primary_roi_complete
            and primary_open == int(primary_lane.get("open_settlement_rows", 0) or 0)
            and primary_incomplete == int(primary_lane.get("incomplete_settled_rows", 0) or 0)
            and primary_roi_gap == int(primary_lane.get("roi_gap_settled_rows", 0) or 0)
            and math.isclose(audit_cost_sum, float(settlement_summary["actual_cost_sum"]), abs_tol=1e-9)
            and math.isclose(audit_return_sum, float(settlement_summary["actual_return_sum"]), abs_tol=1e-9)
            and int(settlement_summary["settled_ts_gap_rows_from_csv"]) == audit_settled_ts_gap_rows
        ),
        "primary_roi_complete_settled_rows": {
            "paper_trade_now": primary_roi_complete,
            "settlement_audit": audit_primary_roi_complete,
            "settlement_csv_recomputed": csv_primary_roi_complete,
        },
        "primary_open_settlement_rows": {
            "paper_trade_now": primary_open,
            "settlement_audit": int(primary_lane.get("open_settlement_rows", 0) or 0),
        },
        "primary_incomplete_settlement_rows": {
            "paper_trade_now": primary_incomplete,
            "settlement_audit": int(primary_lane.get("incomplete_settled_rows", 0) or 0),
        },
        "primary_roi_gap_settlement_rows": {
            "paper_trade_now": primary_roi_gap,
            "settlement_audit": int(primary_lane.get("roi_gap_settled_rows", 0) or 0),
        },
        "primary_cost_return_sums": {
            "settlement_audit_cost": audit_cost_sum,
            "settlement_csv_cost": settlement_summary["actual_cost_sum"],
            "settlement_audit_return": audit_return_sum,
            "settlement_csv_return": settlement_summary["actual_return_sum"],
        },
        "primary_settled_ts_gap_rows": {
            "settlement_audit": audit_settled_ts_gap_rows,
            "settlement_csv_recomputed": settlement_summary["settled_ts_gap_rows_from_csv"],
        },
        "primary_settled_ts_gap_reason_counts": {
            "settlement_audit": {
                str(reason): int(count or 0)
                for reason, count in (audit_reason_counts.items() if isinstance(audit_reason_counts, dict) else [])
                if "settled_ts" in str(reason)
            },
            "settlement_csv_recomputed": settlement_summary["settled_ts_gap_reason_counts"],
        },
        "settlement_audit_upstream_sources": audit_upstream_sources,
    }
    primary_assessment = str(primary.get("assessment") or "UNKNOWN")
    decision_read = (
        f"TOO EARLY: primary paper is {primary_roi_complete}/{first_read.get('threshold', 30)} ROI-complete "
        f"with {first_remaining} more needed before a first statistical read; current settled sample is report context only."
        if not first_read.get("ready")
        else "FIRST READ READY: review hit rate, ROI, concentration, payout sanity, and frozen hierarchy before any posture change."
    )
    phase8_review_threshold = int(
        gate_source_alignment["effective_values"].get("phase8_promotion_review_min_roi_complete_settled_observations")
        or shadow_gate.get("active_first_read_min_settled")
        or 20
    )
    real_money_threshold = int(
        gate_source_alignment["effective_values"].get("real_money_discussion_min_total_settled_observations_with_usable_roi")
        or portfolio_review.get("threshold")
        or 100
    )
    shadow_gate_rows: list[dict[str, Any]] = []
    for row in shadow_rule_progress:
        if not isinstance(row, dict):
            continue
        current_rows = int(row.get("roi_complete_settled_rows", 0) or 0)
        shadow_gate_rows.append(
            {
                "rule_id": str(row.get("rule_id") or ""),
                "scorecard_tier": row.get("scorecard_tier"),
                "current_rows": current_rows,
                "threshold": phase8_review_threshold,
                "remaining": max(phase8_review_threshold - current_rows, 0),
                "ready": current_rows >= phase8_review_threshold,
                "promotion_progress": row.get("promotion_progress"),
            }
        )
    weakest_shadow_rows = min((row["current_rows"] for row in shadow_gate_rows), default=0)
    weakest_shadow_rule_ids = [
        row["rule_id"] for row in shadow_gate_rows if row["current_rows"] == weakest_shadow_rows
    ]
    decision_gate_progress = {
        "source_path": scorecard_json_path.name,
        "source_json_path": "decision_gate_minimums",
        "valid_use": "machine-readable current gate progress for report routing and no-overclaim checks",
        "not_forward_performance_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_live_profitability_evidence": True,
        "not_real_money_evidence": True,
        "gate_status": "all_uncleared",
        "primary_first_read": {
            "gate_source": "anchor_displacement",
            "current_rows": primary_roi_complete,
            "threshold": int(first_read.get("threshold") or anchor_review_threshold),
            "remaining": max(int(first_read.get("threshold") or anchor_review_threshold) - primary_roi_complete, 0),
            "ready": bool(first_read.get("ready")),
            "rows_counted": "primary ROI-complete settled rows",
            "read": (
                f"Primary first-read gate: {primary_roi_complete}/{int(first_read.get('threshold') or anchor_review_threshold)} "
                f"ROI-complete primary rows; {max(int(first_read.get('threshold') or anchor_review_threshold) - primary_roi_complete, 0)} more needed."
            ),
        },
        "op_anchor_same_candidate_review": {
            "gate_source": "anchor_displacement",
            "candidate_rule_id": anchor_settlement_gap["anchor_rule_id"],
            "current_rows": op_primary_rows,
            "threshold": anchor_review_threshold,
            "remaining": max(anchor_review_threshold - op_primary_rows, 0),
            "ready": op_primary_rows >= anchor_review_threshold,
            "companion_rule_id": anchor_settlement_gap["companion_rule_id"],
            "companion_rows": cd_primary_rows,
            "companion_rows_count_as_anchor_evidence": False,
            "read": anchor_settlement_gap["read"],
        },
        "phase8_promotion_review": {
            "gate_source": "phase8_promotion_review",
            "threshold_per_candidate": phase8_review_threshold,
            "weakest_current_rows": weakest_shadow_rows,
            "weakest_rule_ids": weakest_shadow_rule_ids,
            "ready": bool(shadow_gate_rows) and all(row["ready"] for row in shadow_gate_rows),
            "per_rule": shadow_gate_rows,
            "read": (
                f"Phase 8 promotion-review gate: weakest current shadow coverage is {weakest_shadow_rows}/{phase8_review_threshold} "
                f"for {', '.join(weakest_shadow_rule_ids) if weakest_shadow_rule_ids else 'no published shadow rows'}; "
                "the floor is per candidate and is not a promotion entitlement."
            ),
        },
        "real_money_discussion": {
            "gate_source": "real_money_discussion",
            "current_primary_roi_complete_rows": primary_roi_complete,
            "threshold": real_money_threshold,
            "remaining_against_primary_review": max(real_money_threshold - primary_roi_complete, 0),
            "ready": primary_roi_complete >= real_money_threshold,
            "also_requires": gate_source_alignment["real_money_discussion_also_requires"],
            "no_baq_as_bel_required": gate_source_alignment["real_money_no_baq_as_bel_required"],
            "read": (
                f"Real-money discussion floor: primary bridge currently has {primary_roi_complete}/{real_money_threshold} "
                "ROI-complete rows, before concentration, payout-distribution, positive-ROI, and no-BAQ-as-BEL prerequisites."
            ),
        },
    }
    decision_gate_progress["all_gates_ready"] = all(
        [
            decision_gate_progress["primary_first_read"]["ready"],
            decision_gate_progress["op_anchor_same_candidate_review"]["ready"],
            decision_gate_progress["phase8_promotion_review"]["ready"],
            decision_gate_progress["real_money_discussion"]["ready"],
        ]
    )
    decision_gate_progress["read"] = (
        f"Gate progress: primary first-read {primary_roi_complete}/{decision_gate_progress['primary_first_read']['threshold']}; "
        f"OP anchor same-candidate {op_primary_rows}/{anchor_review_threshold}; "
        f"Phase 8 weakest shadow {weakest_shadow_rows}/{phase8_review_threshold}; "
        f"real-money discussion floor {primary_roi_complete}/{real_money_threshold}. "
        "All remain uncleared and are routing context only."
    )

    generated_text = format_generated_at(generated_at)
    source_freshness = build_source_freshness(generated_text, right_now)
    calendar_context = build_calendar_context(source_freshness)
    source_best_action = right_now.get("best_action") if isinstance(right_now.get("best_action"), dict) else {}
    best_action_for_use = build_bridge_best_action(source_best_action, source_freshness)
    right_now_for_operator_context = dict(right_now)
    right_now_for_operator_context["best_action"] = best_action_for_use
    operator_status_context = build_operator_status_context(right_now_for_operator_context)
    primary_recommendation_context = build_primary_recommendation_context(primary, right_now_for_operator_context)
    operator_read_gate = build_operator_read_gate(
        source_freshness,
        operator_status_context,
        primary_recommendation_context,
        best_action_for_use,
    )
    preflight_excluded_track_summary = str(right_now.get("preflight_excluded_track_summary") or "").strip()
    if not preflight_excluded_track_summary:
        preflight_excluded_track_summary = "BAQ (not treated as BEL)"
    source_files = {
        "forward_evidence_scorecard_json": file_fingerprint(scorecard_json_path),
        "paper_trade_now_json": file_fingerprint(right_now_json_path),
        "paper_trade_settlement_audit_json": file_fingerprint(settlement_audit_json_path),
        "primary_signals_ledger": file_fingerprint(primary_signal_path),
        "primary_settlement_ledger": file_fingerprint(settlement_path),
        "shadow_signals_ledger": file_fingerprint(shadow_signal_path),
        "shadow_settlement_ledger": file_fingerprint(shadow_settlement_path),
    }
    if primary_open:
        settlement_queue_read = (
            f"{primary_open} open primary settlement row(s) are settlement-queue work only: fill actual result, "
            "return, cost, and settled_ts from result/payout evidence before interpreting performance. "
            f"Open row(s): {primary_open_summary}. "
            f"Open rows do not change the {primary_roi_complete}/{first_read.get('threshold', 30)} ROI-complete first-read count."
        )
    elif primary_incomplete or primary_roi_gap:
        settlement_queue_read = (
            f"Primary settlement rows need repair before interpretation: {primary_incomplete} incomplete row(s) and "
            f"{primary_roi_gap} ROI-gap row(s). Repair result, return, cost, and settled_ts coverage before quoting forward performance."
        )
    else:
        settlement_queue_read = (
            "Primary settlement queue is currently closed for saved rows, but that queue cleanliness is "
            "operability metadata only and does not add forward-performance evidence beyond ROI-complete settled rows."
        )
    rebuild_validation_contract = {
        "rebuild_command": "python3 current_evidence_summary.py",
        "prerequisite_rebuild_command": "python3 paper_trade_settlement_audit.py",
        "upstream_refresh_order": CURRENT_BRIDGE_UPSTREAM_REFRESH_ORDER,
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": True,
        "upstream_refresh_order_valid_use": (
            "reproducible rebuild order for current bridge provenance after scorecard/rules/ledger byte changes"
        ),
        "direct_validation_command": "python3 validate_current_evidence_summary.py",
        "broader_rollup_commands_after_report_surface_edits": [
            "python3 validate_report_surfaces.py --reuse-existing-child-json",
            "python3 validate_project_surfaces.py --reuse-existing-child-json",
        ],
        "direct_output_paths": [
            "CURRENT_EVIDENCE_SUMMARY.md",
            "current_evidence_summary.json",
        ],
        "validation_output_paths": [
            "out/status_validation/current_evidence_summary/current_evidence_summary_validation.md",
            "out/status_validation/current_evidence_summary/current_evidence_summary_validation.json",
        ],
        "green_checks_are_reproducibility_metadata_only": True,
        "requires_source_consistency_before_quoting_current_totals": True,
        "requires_source_freshness_before_right_now_instruction_use": True,
        "upstream_refresh_order_is_provenance_metadata_only": True,
        "not_settled_roi_or_real_money_evidence": True,
    }

    current_read = (
        f"OP_DURABLE_K7 remains the safest anchor, CD_CORE_K8 remains the primary OP/CD paper-basket companion, "
        f"and OP_REFINED_K7 remains shadow/watch. Current primary paper is {primary_roi_complete}/{first_read.get('threshold', 30)} "
        f"ROI-complete with {primary_open} open rows, observed hit rate {pct(settlement_summary['hit_rate'])}, "
        f"flat-ticket ROI {pct(settlement_summary['flat_ticket_roi'])}, and decision gate {primary_assessment}. "
        f"Recommendation context: {primary_recommendation_context['read']} "
        f"{primary_rule_mix_read} {anchor_settlement_gap['read']} {open_settlement_queue_by_rule['read']} "
        f"{decision_gate_progress['read']} "
        f"{ci_only_promotion_check['read']} "
        f"Phase 8 remains shadow-only: {shadow_gate.get('gate_read', '0/20 per rule')}; BAQ is not BEL. "
        f"Scorecard audit route (`current_evidence_summary.json.scorecard_audit_route`): {scorecard_audit_route['route_read']} "
        f"Source freshness: {source_freshness['read']} {operator_status_context['read']} {operator_read_gate['read']}"
    )

    return {
        "schema_version": 1,
        "artifact": "current_evidence_summary",
        "generated_at": generated_text,
        "valid_use": "report-ready bridge from frozen evidence ranking to current paper-trade gate status",
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "evidence_boundary": {
            "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
            "not_new_forward_evidence": True,
            "not_live_profitability_evidence": True,
            "not_promotion_readiness_evidence": True,
            "not_real_money_evidence": True,
            "source_files_are_reproducibility_metadata_only": True,
            "source_freshness_is_operator_readiness_not_performance_proof": True,
            "decision_gate_status_is_routing_context_not_performance_proof": True,
            "operator_issue_context_is_not_performance_proof": True,
            "operator_read_gate_is_operator_routing_not_performance_proof": True,
            "scorecard_audit_route_is_synchronization_metadata_only": True,
        },
        "source_files": source_files,
        "rebuild_validation_contract": rebuild_validation_contract,
        "scorecard_audit_route": scorecard_audit_route,
        "source_freshness": source_freshness,
        "calendar_context": calendar_context,
        "operator_read_gate": operator_read_gate,
        "source_consistency": source_consistency,
        "scorecard_ci_only_promotion_check": ci_only_promotion_check,
        "frozen_posture": {
            "anchor": {
                "rule_id": anchor_row.get("rule_id", live_hierarchy.get("current_anchor")),
                "tier": anchor_row.get("tier"),
                "holdout_roi": anchor_row.get("holdout_roi"),
                "holdout_races": anchor_row.get("holdout_races"),
                "wf_selected": anchor_row.get("wf_selected"),
                "read": "keep as safest current OP anchor",
            },
            "primary_companion": {
                "rule_id": companion_row.get("rule_id", live_hierarchy.get("primary_companion")),
                "tier": companion_row.get("tier"),
                "holdout_roi": companion_row.get("holdout_roi"),
                "holdout_races": companion_row.get("holdout_races"),
                "wf_selected": companion_row.get("wf_selected"),
                "read": "primary OP/CD paper-basket companion, not an anchor replacement",
            },
            "shadow_lead": {
                "rule_id": shadow_lead_row.get("rule_id", live_hierarchy.get("secondary_shadow")),
                "tier": shadow_lead_row.get("tier"),
                "holdout_roi": shadow_lead_row.get("holdout_roi"),
                "holdout_races": shadow_lead_row.get("holdout_races"),
                "wf_selected": shadow_lead_row.get("wf_selected"),
                "read": "closest same-family shadow/watch challenger only",
                "scorecard_ci_only_promotion_check": ci_only_promotion_check,
            },
        },
        "current_paper_status": {
            "run_root": right_now.get("run_root"),
            "run_freshness": right_now.get("run_freshness"),
            "best_action": best_action_for_use,
            "source_best_action": source_best_action,
            "best_action_overridden_for_source_freshness": bool(best_action_for_use.get("source_action_overridden")),
            "operator_status_context": operator_status_context,
            "operator_read_gate": operator_read_gate,
            "preflight_excluded_track_summary": preflight_excluded_track_summary,
            "primary": {
                "state": primary.get("state"),
                "assessment": primary_assessment,
                "settled": primary_settled,
                "open_settlements": primary_open,
                "incomplete_settlements": primary_incomplete,
                "roi_complete_settled": primary_roi_complete,
                "roi_gap_settlements": primary_roi_gap,
                "first_read": first_read,
                "portfolio_review": portfolio_review,
                "hit_count": settlement_summary["hit_count"],
                "miss_count": settlement_summary["miss_count"],
                "hit_rate": settlement_summary["hit_rate"],
                "flat_ticket_roi": settlement_summary["flat_ticket_roi"],
                "actual_cost_sum": settlement_summary["actual_cost_sum"],
                "actual_return_sum": settlement_summary["actual_return_sum"],
                "ledger_path": settlement_summary["path"],
                "rule_progress": primary_rule_progress,
                "rule_mix_read": primary_rule_mix_read,
                "anchor_settlement_gap": anchor_settlement_gap,
                "open_settlement_queue_by_rule": open_settlement_queue_by_rule,
                "settlement_queue_read": settlement_queue_read,
                "open_settlement_row_details": primary_open_details,
                "open_settlement_summary": primary_open_summary,
                "recommendation_context": primary_recommendation_context,
            },
            "shadow": {
                "state": shadow.get("state"),
                "assessment": shadow.get("assessment"),
                "roi_complete_settled": int(shadow.get("roi_covered_settled", shadow_lane.get("roi_complete_settled_rows", 0)) or 0),
                "promotion_gate_read": shadow_gate.get("gate_read"),
                "rule_progress_read": shadow_rule_progress_read,
                "rule_progress": shadow_rule_progress,
                "ci_only_promotion_check": ci_only_promotion_check,
            },
        },
        "decision_gate_minimums": {
            "source_path": gate_minimums.get("source_path"),
            "source_loaded": gate_minimums.get("source_loaded"),
            "anchor_displacement_min_roi_complete_settled_observations": gate_source_alignment["effective_values"].get("anchor_displacement_min_roi_complete_settled_observations"),
            "phase8_promotion_review_min_roi_complete_settled_observations": gate_source_alignment["effective_values"].get("phase8_promotion_review_min_roi_complete_settled_observations"),
            "real_money_discussion_min_total_settled_observations_with_usable_roi": gate_source_alignment["effective_values"].get("real_money_discussion_min_total_settled_observations_with_usable_roi"),
            "alignment_read": gate_minimums.get("alignment_read"),
            "scorecard_source_path": gate_source_alignment["scorecard_source_path"],
            "top_card_values": gate_source_alignment["top_card_values"],
            "scorecard_values": gate_source_alignment["scorecard_values"],
            "effective_values": gate_source_alignment["effective_values"],
            "effective_values_source": gate_source_alignment["effective_values_source"],
            "threshold_sources": gate_source_alignment["threshold_sources"],
            "real_money_discussion_also_requires": gate_source_alignment["real_money_discussion_also_requires"],
            "real_money_no_baq_as_bel_required": gate_source_alignment["real_money_no_baq_as_bel_required"],
            "source_values_match_scorecard": gate_source_alignment["source_values_match_scorecard"],
            "mismatched_fields": gate_source_alignment["mismatched_fields"],
            "missing_top_card_fields": gate_source_alignment["missing_top_card_fields"],
            "source_alignment_read": gate_source_alignment["read"],
        },
        "decision_gate_progress": decision_gate_progress,
        "decision_read": decision_read,
        "do_not_do": [
            (
                f"do not treat {primary_roi_complete} settled misses as promotion-grade forward evidence"
                if primary_roi_complete == settlement_summary["miss_count"] and settlement_summary["hit_count"] == 0
                else f"do not treat the {primary_roi_complete} ROI-complete settled-row sample as promotion-grade forward evidence"
            ),
            "do not change rules from the tiny sample",
            "do not promote OP_REFINED_K7 or Phase 8",
            "do not reopen current odds-only XGBoost",
            "do not substitute BAQ for BEL",
            "do not discuss real-money scaling",
        ],
        "next_actions": [
            "keep the daily OP/CD + shadow wrapper running on target days",
            "settle any new qualifying paper signals only from actual result and payout evidence",
            "wait for at least 30 ROI-complete primary rows before a first statistical read",
            "wait for 20 ROI-complete shadow rows per candidate before Phase 8 promotion review",
            "wait for 100 total ROI-complete settled observations plus concentration/payout sanity before real-money discussion",
        ],
        "summary": {
            "current_read": current_read,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    primary = payload["current_paper_status"]["primary"]
    shadow = payload["current_paper_status"]["shadow"]
    anchor = payload["frozen_posture"]["anchor"]
    companion = payload["frozen_posture"]["primary_companion"]
    shadow_lead = payload["frozen_posture"]["shadow_lead"]
    gates = payload["decision_gate_minimums"]
    consistency = payload["source_consistency"]
    freshness = payload["source_freshness"]
    calendar_context = payload["calendar_context"]
    ci_only = payload["scorecard_ci_only_promotion_check"]
    gate_progress = payload["decision_gate_progress"]
    scorecard_audit_route = payload["scorecard_audit_route"]
    first_read = primary["first_read"]
    portfolio_review = primary["portfolio_review"]
    best_action = payload["current_paper_status"].get("best_action") or {}
    source_best_action = payload["current_paper_status"].get("source_best_action") or {}
    operator_status_context = payload["current_paper_status"].get("operator_status_context") or {}
    operator_read_gate = payload.get("operator_read_gate") or payload["current_paper_status"].get("operator_read_gate") or {}
    inherited_action_line = None
    if best_action.get("source_action_overridden"):
        inherited_action_line = (
            f"- Inherited source action held back: **{source_best_action.get('headline')}** "
            f"/ `{source_best_action.get('command')}`; stale source action is context only until refresh."
        )

    lines = [
        "# Current Evidence Summary",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        "## Evidence Boundary",
        "",
        "- This is a report-ready bridge from existing validated surfaces: frozen scorecard posture plus current paper-trade gate status.",
        f"- valid_evidence_scope={payload['valid_evidence_scope']}",
        "- It is **not** new forward-performance evidence, live-profitability evidence, promotion-readiness evidence, or real-money evidence.",
        "- Source fingerprints and green validators are reproducibility metadata only; decision-gate status is routing context, not performance proof.",
        "- Only ROI-complete settled paper rows with usable return/cost and actual `settled_ts` values can support future forward-performance claims.",
        "",
        "## One-Screen Read",
        "",
        f"- Anchor: `{anchor['rule_id']}` remains the safest current OP anchor (`{anchor['tier']}`, {float(anchor['holdout_roi']):+.2f}% holdout ROI on {int(anchor['holdout_races'])} races, {anchor['wf_selected']} WF).",
        f"- Primary paper-basket companion: `{companion['rule_id']}` remains the primary OP/CD paper-basket companion (`{companion['tier']}`), not an anchor replacement.",
        f"- Shadow lead: `{shadow_lead['rule_id']}` remains shadow/watch only (`{shadow_lead['tier']}`), not promoted. Scorecard CI-only source `{ci_only['source']}` says `ci_only_promotion_allowed=false`.",
        f"- Current primary paper: `{primary['roi_complete_settled']}/{first_read.get('threshold')}` ROI-complete settled rows, `{primary['open_settlements']}` open rows, `{primary['incomplete_settlements']}` incomplete rows, hit rate `{pct(primary['hit_rate'])}`, flat-ticket ROI `{pct(primary['flat_ticket_roi'])}` on {money(primary['actual_cost_sum'])} cost / {money(primary['actual_return_sum'])} return.",
        f"- Settlement queue: {primary['settlement_queue_read']}",
        f"- Latest primary recommendation context: {primary['recommendation_context']['read']}",
        f"- {primary['rule_mix_read']}",
        f"- {primary['anchor_settlement_gap']['read']}",
        f"- {primary['open_settlement_queue_by_rule']['read']}",
        f"- Broader review: `{portfolio_review.get('current')}/{portfolio_review.get('threshold')}` ROI-complete rows; `{portfolio_review.get('remaining')}` more needed before even the broad review count is met.",
        f"- Decision gate: **{payload['decision_read']}**",
        f"- Source freshness: {freshness['read']}",
        f"- Operator issue context: {operator_status_context.get('read')}",
        f"- Operator read gate: {operator_read_gate.get('read')}",
        f"- BAQ/BEL: `{payload['current_paper_status'].get('preflight_excluded_track_summary')}`; do not treat BAQ as BEL.",
        "",
        "## Source Consistency",
        "",
        f"- Overall source match: `{consistency['overall_match']}` across `PAPER_TRADE_NOW.json`, `out/paper_trade_settlement_audit.json`, and the primary settlement CSV recompute.",
        f"- Primary ROI-complete rows: `PAPER_TRADE_NOW={consistency['primary_roi_complete_settled_rows']['paper_trade_now']}`, `settlement_audit={consistency['primary_roi_complete_settled_rows']['settlement_audit']}`, `csv_recomputed={consistency['primary_roi_complete_settled_rows']['settlement_csv_recomputed']}`.",
        f"- Primary settlement queue: open `PAPER_TRADE_NOW={consistency['primary_open_settlement_rows']['paper_trade_now']}` / audit `{consistency['primary_open_settlement_rows']['settlement_audit']}`; incomplete `PAPER_TRADE_NOW={consistency['primary_incomplete_settlement_rows']['paper_trade_now']}` / audit `{consistency['primary_incomplete_settlement_rows']['settlement_audit']}`; ROI-gap `PAPER_TRADE_NOW={consistency['primary_roi_gap_settlement_rows']['paper_trade_now']}` / audit `{consistency['primary_roi_gap_settlement_rows']['settlement_audit']}`.",
        f"- Cost/return sums: audit {money(consistency['primary_cost_return_sums']['settlement_audit_cost'])} cost / {money(consistency['primary_cost_return_sums']['settlement_audit_return'])} return; CSV recompute {money(consistency['primary_cost_return_sums']['settlement_csv_cost'])} cost / {money(consistency['primary_cost_return_sums']['settlement_csv_return'])} return.",
        f"- CSV settled_ts coverage: recompute skipped `{consistency['primary_settled_ts_gap_rows']['settlement_csv_recomputed']}` timestamp-gap row(s); audit timestamp-gap rows `{consistency['primary_settled_ts_gap_rows']['settlement_audit']}`.",
        f"- Settlement-audit upstream fingerprints: {consistency['settlement_audit_upstream_sources']['read']}",
        "",
        "## Source Freshness",
        "",
        f"- Right-now source run date: `{freshness['right_now_run_date']}`; source as-of date: `{freshness['right_now_as_of_date']}`; bridge generated local date: `{freshness['generated_date']}`; bridge reference date: `{freshness['generated_reference_date']}` (`{freshness['generated_reference_timezone']}`).",
        f"- Right-now freshness state: `{freshness['right_now_freshness_state']}`; state valid: `{freshness['right_now_freshness_state_valid']}`.",
        f"- Stale versus bridge reference date: `{freshness['is_stale_vs_generated_date']}`; refresh before right-now use: `{freshness['requires_refresh_before_right_now_use']}`.",
        f"- Staleness age: source-vs-bridge `{freshness['source_stale_age_days_vs_bridge']}` day(s); right-now internal `{freshness['right_now_internal_stale_age_days']}` day(s); refresh age `{freshness['refresh_age_days']}` day(s).",
        f"- Refresh boundary: {freshness['refresh_action_boundary']['read']}",
        f"- Operator read: {freshness['read']}",
        "",
        "## Calendar Context",
        "",
        f"- Generated local date: `{calendar_context['generated_local_date']}`; generated reference date: `{calendar_context['generated_reference_date']}` (`{calendar_context['generated_reference_timezone']}`).",
        f"- Right-now run/as-of dates: run=`{calendar_context['right_now_run_date']}`, as-of=`{calendar_context['right_now_as_of_date']}`.",
        f"- Staleness comparison: `{calendar_context['staleness_comparison_source']}` -> `{calendar_context['staleness_comparison_date']}`; local/reference dates differ: `{calendar_context['generated_reference_date_differs_from_local_date']}`.",
        f"- Calendar boundary: {calendar_context['read']} It is not forward-performance, live-profitability, promotion-readiness, or real-money evidence.",
        "",
        "## Gate Minimums",
        "",
        f"- Gate source: `{gates['source_path']}`; loaded={gates['source_loaded']}. {gates['alignment_read']}",
        f"- Gate source alignment: `{gates['source_values_match_scorecard']}`. {gates['source_alignment_read']}",
        f"- Canonical gate values used by the bridge: anchor `{gates['effective_values']['anchor_displacement_min_roi_complete_settled_observations']}`; Phase 8 `{gates['effective_values']['phase8_promotion_review_min_roi_complete_settled_observations']}`; real-money `{gates['effective_values']['real_money_discussion_min_total_settled_observations_with_usable_roi']}` (source: `{gates['effective_values_source']}`).",
        f"- Threshold sources: anchor `{gates['threshold_sources']['anchor_displacement']}`; Phase 8 `{gates['threshold_sources']['phase8_promotion_review']}`; real-money `{gates['threshold_sources']['real_money_discussion']}`.",
        f"- Real-money prerequisites: `{'; '.join(gates['real_money_discussion_also_requires'])}`; no-BAQ-as-BEL required = `{gates['real_money_no_baq_as_bel_required']}`.",
        f"- Anchor displacement / first-read gate: `{gates['anchor_displacement_min_roi_complete_settled_observations']}` ROI-complete settled observations.",
        f"- Phase 8 promotion review: `{gates['phase8_promotion_review_min_roi_complete_settled_observations']}` ROI-complete settled shadow observations per candidate.",
        f"- Real-money discussion: `{gates['real_money_discussion_min_total_settled_observations_with_usable_roi']}` total settled observations with usable ROI plus concentration/payout sanity checks.",
        f"- Scorecard audit route (`current_evidence_summary.json.scorecard_audit_route`): {scorecard_audit_route['route_read']} This route is synchronization metadata only, not current paper evidence.",
        "",
        "## Gate Progress",
        "",
        f"- Progress source: `{gate_progress['source_path']}` `{gate_progress['source_json_path']}`; status `{gate_progress['gate_status']}`; all gates ready = `{gate_progress['all_gates_ready']}`.",
        f"- {gate_progress['primary_first_read']['read']}",
        f"- OP same-candidate anchor review: `{gate_progress['op_anchor_same_candidate_review']['current_rows']}/{gate_progress['op_anchor_same_candidate_review']['threshold']}` ROI-complete `{gate_progress['op_anchor_same_candidate_review']['candidate_rule_id']}` rows; `{gate_progress['op_anchor_same_candidate_review']['remaining']}` more needed. `{gate_progress['op_anchor_same_candidate_review']['companion_rule_id']}` companion rows count as anchor evidence = `{gate_progress['op_anchor_same_candidate_review']['companion_rows_count_as_anchor_evidence']}`.",
        f"- {gate_progress['phase8_promotion_review']['read']}",
        f"- {gate_progress['real_money_discussion']['read']}",
        f"- Gate-progress boundary: machine-readable routing metadata only; not forward-performance evidence, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "",
        "## Shadow Watch Status",
        "",
        f"- Shadow lane: `{shadow['state']}` / `{shadow['assessment']}` with `{shadow['roi_complete_settled']}` ROI-complete settled rows.",
        f"- OP_REFINED CI-only check: {ci_only['read']}",
        f"- OP_REFINED blockers from scorecard: {'; '.join(ci_only['why_not'])}.",
        f"- OP_REFINED required before review: {keyed_items_text(ci_only['required_before_review'])}.",
        f"- Does not count: {'; '.join(ci_only['does_not_count'])}.",
        f"- Promotion gate: {shadow['promotion_gate_read']}",
        f"- Per-rule shadow coverage: {shadow['rule_progress_read']}",
        "",
        "## Best Next Action",
        "",
        f"- Action: **{best_action.get('headline')}**",
        f"- Freshness caveat: {freshness['read']}",
        f"- Command: `{best_action.get('command')}`",
        *( [inherited_action_line] if inherited_action_line else [] ),
        f"- Why: {best_action.get('why')}",
        f"- Ops bucket: `{operator_status_context.get('ops_day_bucket')}`",
        f"- Ops takeaway: {operator_status_context.get('ops_takeaway')}",
        f"- Operator issue boundary: {operator_status_context.get('read')}",
        f"- Operator read gate status: `{operator_read_gate.get('gate_status')}`; refresh before evidence read = `{operator_read_gate.get('requires_refresh_before_evidence_read')}`; clean-empty/no-target evidence from current card = `{operator_read_gate.get('current_top_card_counts_as_clean_empty_evidence')}` / `{operator_read_gate.get('current_top_card_counts_as_no_target_evidence')}`.",
        f"- Refresh action boundary: {freshness['refresh_action_boundary']['read']}",
        "",
        "## Do Not Do",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["do_not_do"])
    lines.extend([
        "",
        "## Next Honest Actions",
        "",
    ])
    lines.extend(f"- {item}" for item in payload["next_actions"])
    contract = payload["rebuild_validation_contract"]
    lines.extend([
        "",
        "## Rebuild & Validate",
        "",
        "- Machine-readable contract: the JSON sidecar field `rebuild_validation_contract` is the source for this order; on canonical outputs quote it as `current_evidence_summary.json.rebuild_validation_contract`.",
        f"- Upstream prerequisite: `{contract['prerequisite_rebuild_command']}` before `{contract['rebuild_command']}` when scorecard, rules, signals, or settlement-ledger source bytes change.",
        "- Upstream refresh order: "
        + "; ".join(
            f"{step['order']}. `{step['command']}` ({step['reason']})"
            for step in contract["upstream_refresh_order"]
        ),
        f"- Rebuild command: `{contract['rebuild_command']}`",
        f"- Direct validation command: `{contract['direct_validation_command']}`",
        "- Broader rollup after report-surface wording changes: " + "; ".join(f"`{cmd}`" for cmd in contract["broader_rollup_commands_after_report_surface_edits"]),
        "- Direct outputs: " + ", ".join(f"`{path}`" for path in contract["direct_output_paths"]),
        "- Validation outputs: " + ", ".join(f"`{path}`" for path in contract["validation_output_paths"]),
        "- Green checks are reproducibility/operator-readiness metadata only; they are not settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence.",
        "",
        "## Source Fingerprints",
        "",
        "| Source | Path | Bytes | SHA-256 |",
        "|---|---|---:|---|",
    ])
    for label, fp in payload["source_files"].items():
        lines.append(f"| {label} | `{fp['path']}` | {fp['bytes']} | `{fp['sha256']}` |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    payload = build_payload(
        generated_at=args.generated_at,
        scorecard_json_path=Path(args.scorecard_json),
        right_now_json_path=Path(args.right_now_json),
        settlement_audit_json_path=Path(args.settlement_audit_json),
    )
    markdown = render_markdown(payload)
    print(markdown)
    if not args.stdout_only:
        md_output = Path(args.md_output)
        json_output = Path(args.json_output)
        md_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.parent.mkdir(parents=True, exist_ok=True)
        md_output.write_text(markdown + "\n", encoding="utf-8")
        json_output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"\nSaved to: {md_output.resolve()}")
        print(f"Saved to: {json_output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
