#!/usr/bin/env python3
"""
Direct paper-trade settlement completeness audit.

Purpose:
- Compare signal ledgers to settlement ledgers before forward performance is interpreted.
- Surface missing settlement templates, stale/orphan settlement rows, duplicate keys,
  matched-key signal/settlement metadata mismatches, incomplete settled rows, and rows
  that cannot yet contribute to realized ROI.
- Keep the paper-trade evidence boundary explicit: this is a ledger-quality audit,
  not new forward edge evidence by itself.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from paper_trade_forward_check import classify_outcome, parse_float
from paper_trade_lane_monitor import is_incomplete_settled_row, is_open_row, roi_gap_reason

BASE = Path(__file__).resolve().parent
DEFAULT_OUTPUT_MD = BASE / "out" / "paper_trade_settlement_audit.md"
DEFAULT_OUTPUT_JSON = BASE / "out" / "paper_trade_settlement_audit.json"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
FALLBACK_GATE_MINIMUMS = {
    "anchor_displacement": 30,
    "phase8_promotion_review": 20,
    "real_money_discussion": 100,
}
NO_BAQ_AS_BEL_REQUIREMENT = "no BAQ-as-BEL substitution"
SETTLEMENT_AUDIT_ARTIFACT_ROLE = "paper-trade settlement ledger completeness / ROI-coverage audit"
SETTLEMENT_AUDIT_VALID_EVIDENCE_SCOPE = "paper_trade_settlement_quality_audit_only"
SETTLEMENT_AUDIT_EVIDENCE_BOUNDARY_TEXT = (
    "Settlement-audit output is ledger-completeness / ROI-coverage metadata only: "
    "signal/settlement alignment, open-row queues, ROI-complete coverage counts, "
    "and scorecard gate progress are not scanner evidence, not new forward-performance "
    "evidence by itself, not settled profit proof, not promotion readiness, not live "
    "profitability, not bankroll guidance, not real-money support, or BAQ-as-BEL evidence."
)
LANE_DEFAULTS = [
    {
        "name": "primary",
        "label": "Phase 7 current paper lane",
        "role": "primary paper lane: OP_DURABLE_K7 safest OP anchor plus CD_CORE_K8 paper companion",
        "rules_file": BASE / "phase7_current_paper_rules.json",
        "promotion_scope": "lane_total_first_read",
        "signals_ledger": BASE / "paper_trades" / "phase7_current_paper_paper_trade_signals.csv",
        "settlement_ledger": BASE / "paper_trades" / "phase7_current_paper_paper_trade_settlements.csv",
    },
    {
        "name": "shadow",
        "label": "Phase 8 shadow/watch lane",
        "role": "shadow/watch lane: OP_REFINED_K7 plus other Phase 8 rules remain observation-only unless settled forward evidence clears explicit gates",
        "rules_file": BASE / "phase8_shadow_rules.json",
        "promotion_scope": "per_rule_shadow_watch",
        "signals_ledger": BASE / "paper_trades" / "phase8_shadow_paper_trade_signals.csv",
        "settlement_ledger": BASE / "paper_trades" / "phase8_shadow_paper_trade_settlements.csv",
    },
]

KEY_METADATA_FIELDS = ("rule_id", "track", "race_number", "race_id")
SETTLED_TS_PLACEHOLDER_TOKENS = {"", "open", "pending", "unsettled", "todo", "tbd", "na", "n/a", "none", "null"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit paper-trade signal/settlement ledger completeness")
    p.add_argument("--min-settled", type=int, default=None, help="First useful settled ROI-complete observation milestone; defaults to the scorecard anchor-displacement gate")
    p.add_argument("--portfolio-review-settled", type=int, default=None, help="Broader portfolio-review settled observation milestone; defaults to the scorecard real-money discussion gate")
    p.add_argument("--shadow-rule-min-settled", type=int, default=None, help="Per-rule ROI-complete settlement gate before any shadow/watch rule can be promotion-reviewed; defaults to the scorecard Phase 8 promotion-review gate")
    p.add_argument("--format", choices=["md", "json", "text"], default="md", help="Output format for stdout")
    p.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD), help="Markdown output path")
    p.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON), help="JSON output path")
    p.add_argument(
        "--lane",
        action="append",
        default=[],
        metavar="NAME,LABEL,SIGNALS_CSV,SETTLEMENTS_CSV,ROLE",
        help="Optional lane override. May be repeated. ROLE is optional; commas in values are not supported.",
    )
    return p.parse_args()


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def file_fingerprint(path: Path) -> dict[str, Any]:
    """Return exact source-file provenance for an audit input."""
    path = Path(path)
    if not path.exists():
        return {
            "path": display_path(path),
            "exists": False,
            "bytes": 0,
            "sha256": "",
        }
    data = path.read_bytes()
    return {
        "path": display_path(path),
        "exists": True,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def build_source_files(lanes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    sources = {
        "forward_evidence_scorecard_json": file_fingerprint(SCORECARD_JSON),
    }
    for lane in lanes:
        lane_name = str(lane.get("name", "lane")).strip() or "lane"
        sources[f"{lane_name}_signals_ledger"] = file_fingerprint(Path(lane["signals_ledger"]))
        sources[f"{lane_name}_settlement_ledger"] = file_fingerprint(Path(lane["settlement_ledger"]))
        if lane.get("rules_file"):
            sources[f"{lane_name}_rules_json"] = file_fingerprint(Path(lane["rules_file"]))
    return sources


def load_scorecard_rule_metadata(path: Path = SCORECARD_JSON) -> dict[str, Any]:
    """Load scorecard tier/posture metadata for per-rule shadow gate reads."""
    fallback = {
        "source_path": display_path(path),
        "source_loaded": False,
        "fallback_used": True,
        "fallback_reason": "forward_evidence_scorecard.json missing or unreadable; scorecard rule tier metadata unavailable",
        "rules": {},
    }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload["rows"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return fallback

    rules: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return fallback
    for row in rows:
        if not isinstance(row, dict):
            continue
        rule_id = str(row.get("rule_id", "")).strip()
        if not rule_id:
            continue
        rules[rule_id] = {
            "tier": str(row.get("tier", "")).strip() or "UNRANKED",
            "current_role": str(row.get("current_role", "")).strip(),
            "action_now": str(row.get("action_now", "")).strip(),
            "note": str(row.get("note", "")).strip(),
            "holdout_roi": row.get("holdout_roi"),
            "holdout_races": row.get("holdout_races"),
            "wf_selected": str(row.get("wf_selected", "")).strip(),
        }
    return {
        "source_path": display_path(path),
        "source_loaded": True,
        "fallback_used": False,
        "fallback_reason": "",
        "rules": rules,
    }


def conservative_gate_payload(
    path: Path,
    *,
    source_loaded: bool,
    fallback_reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "source_path": display_path(path),
        "source_loaded": source_loaded,
        "fallback_used": True,
        "fallback_reason": fallback_reason,
        "anchor_displacement_min_roi_complete_settled_observations": FALLBACK_GATE_MINIMUMS["anchor_displacement"],
        "phase8_promotion_review_min_roi_complete_settled_observations": FALLBACK_GATE_MINIMUMS["phase8_promotion_review"],
        "real_money_discussion_min_total_settled_observations_with_usable_roi": FALLBACK_GATE_MINIMUMS["real_money_discussion"],
        "real_money_discussion_also_requires": [NO_BAQ_AS_BEL_REQUIREMENT],
        "real_money_no_baq_as_bel_required": True,
    }
    if extra:
        payload.update(extra)
    return payload


def require_positive_non_bool_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive non-boolean integer")
    return value


def load_scorecard_gate_minimums(path: Path = SCORECARD_JSON) -> dict[str, Any]:
    """Load posture-change sample gates from the forward scorecard sidecar.

    The settlement audit is an operational ledger-quality surface, but its sample
    milestones should not drift away from the frozen-evidence scorecard's
    machine-readable decision gates. If the sidecar is absent or malformed, keep
    the historical safe defaults and make the fallback explicit in the payload.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return conservative_gate_payload(
            path,
            source_loaded=False,
            fallback_reason="forward_evidence_scorecard.json missing, unreadable, or invalid JSON; using conservative historical gate defaults",
        )

    try:
        gates = payload["decision_gate_minimums"]
        if not isinstance(gates, dict):
            raise ValueError("decision_gate_minimums must be an object")
        anchor = require_positive_non_bool_int(
            gates["anchor_displacement"]["min_roi_complete_settled_observations"],
            "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
        )
        phase8 = require_positive_non_bool_int(
            gates["phase8_promotion_review"]["min_roi_complete_settled_observations"],
            "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
        )
        real_money_gate = gates["real_money_discussion"]
        real_money = require_positive_non_bool_int(
            real_money_gate["min_total_settled_observations_with_usable_roi"],
            "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
        )
        also_requires = real_money_gate["also_requires"]
        if not isinstance(also_requires, list) or not all(isinstance(item, str) for item in also_requires):
            raise ValueError("decision_gate_minimums.real_money_discussion.also_requires must be a string list")
        real_money_requirements = [item.strip() for item in also_requires]
        if NO_BAQ_AS_BEL_REQUIREMENT not in real_money_requirements:
            raise ValueError("decision_gate_minimums.real_money_discussion.also_requires must include no BAQ-as-BEL substitution")
    except (KeyError, TypeError, ValueError) as exc:
        return conservative_gate_payload(
            path,
            source_loaded=True,
            fallback_reason="forward_evidence_scorecard.json decision_gate_minimums malformed; using conservative historical gate defaults",
            extra={"malformed_gate_error": str(exc)},
        )

    conservative_floors = {
        "anchor_displacement_min_roi_complete_settled_observations": FALLBACK_GATE_MINIMUMS["anchor_displacement"],
        "phase8_promotion_review_min_roi_complete_settled_observations": FALLBACK_GATE_MINIMUMS["phase8_promotion_review"],
        "real_money_discussion_min_total_settled_observations_with_usable_roi": FALLBACK_GATE_MINIMUMS["real_money_discussion"],
    }
    loaded_values = {
        "anchor_displacement_min_roi_complete_settled_observations": anchor,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money,
        "real_money_discussion_also_requires": real_money_requirements,
        "real_money_no_baq_as_bel_required": NO_BAQ_AS_BEL_REQUIREMENT in real_money_requirements,
    }
    lowered = {
        key: {"loaded_value": loaded_values[key], "conservative_floor": conservative_floors[key]}
        for key in conservative_floors
        if loaded_values[key] < conservative_floors[key]
    }
    if lowered:
        return {
            **conservative_gate_payload(
                path,
                source_loaded=True,
                fallback_reason="forward_evidence_scorecard.json decision_gate_minimums fell below conservative historical floors; using conservative historical gate defaults",
                extra={"rejected_lowered_values": lowered},
            ),
            "real_money_discussion_also_requires": real_money_requirements,
            "real_money_no_baq_as_bel_required": NO_BAQ_AS_BEL_REQUIREMENT in real_money_requirements,
        }

    return {
        "source_path": display_path(path),
        "source_loaded": True,
        "fallback_used": False,
        "fallback_reason": "",
        "real_money_discussion_also_requires": real_money_requirements,
        "real_money_no_baq_as_bel_required": NO_BAQ_AS_BEL_REQUIREMENT in real_money_requirements,
        **loaded_values,
    }


def resolve_gate_minimums(args: argparse.Namespace) -> dict[str, Any]:
    scorecard_gates = load_scorecard_gate_minimums()
    min_settled = (
        args.min_settled
        if args.min_settled is not None
        else scorecard_gates["anchor_displacement_min_roi_complete_settled_observations"]
    )
    portfolio_review_settled = (
        args.portfolio_review_settled
        if args.portfolio_review_settled is not None
        else scorecard_gates["real_money_discussion_min_total_settled_observations_with_usable_roi"]
    )
    shadow_rule_min_settled = (
        args.shadow_rule_min_settled
        if args.shadow_rule_min_settled is not None
        else scorecard_gates["phase8_promotion_review_min_roi_complete_settled_observations"]
    )

    overrides: dict[str, dict[str, int]] = {}
    if min_settled != scorecard_gates["anchor_displacement_min_roi_complete_settled_observations"]:
        overrides["min_settled"] = {
            "scorecard_value": scorecard_gates["anchor_displacement_min_roi_complete_settled_observations"],
            "active_value": min_settled,
        }
    if portfolio_review_settled != scorecard_gates["real_money_discussion_min_total_settled_observations_with_usable_roi"]:
        overrides["portfolio_review_settled"] = {
            "scorecard_value": scorecard_gates["real_money_discussion_min_total_settled_observations_with_usable_roi"],
            "active_value": portfolio_review_settled,
        }
    if shadow_rule_min_settled != scorecard_gates["phase8_promotion_review_min_roi_complete_settled_observations"]:
        overrides["shadow_rule_min_settled"] = {
            "scorecard_value": scorecard_gates["phase8_promotion_review_min_roi_complete_settled_observations"],
            "active_value": shadow_rule_min_settled,
        }

    return {
        **scorecard_gates,
        "active_min_settled": min_settled,
        "active_portfolio_review_settled": portfolio_review_settled,
        "active_shadow_rule_min_settled": shadow_rule_min_settled,
        "cli_overrides": overrides,
        "alignment_read": (
            "settlement-audit sample milestones are source-matched to forward_evidence_scorecard.json decision_gate_minimums"
            if not overrides and scorecard_gates["source_loaded"] and not scorecard_gates["fallback_used"]
            else "settlement-audit sample milestones are using explicit CLI/fallback values; do not treat fixture/custom thresholds as posture-changing gates"
        ),
    }


def build_evidence_boundary_metadata(gate_minimums: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_role": SETTLEMENT_AUDIT_ARTIFACT_ROLE,
        "valid_evidence_scope": SETTLEMENT_AUDIT_VALID_EVIDENCE_SCOPE,
        "valid_use": (
            "audit signal/settlement ledger alignment, open settlement queues, ROI-complete coverage, "
            "and sample-gate progress before interpreting paper-trade outcomes"
        ),
        "source_scope": [
            "primary and shadow signal ledgers",
            "primary and shadow settlement ledgers",
            "primary and shadow rule JSON files",
            "forward_evidence_scorecard.json decision_gate_minimums",
        ],
        "decision_gate_source": "forward_evidence_scorecard.json decision_gate_minimums",
        "decision_gate_source_path": gate_minimums["source_path"],
        "decision_gate_source_loaded": gate_minimums["source_loaded"],
        "decision_gate_fallback_used": gate_minimums["fallback_used"],
        "anchor_displacement_min_roi_complete_settled_observations": gate_minimums[
            "anchor_displacement_min_roi_complete_settled_observations"
        ],
        "phase8_promotion_review_min_roi_complete_settled_observations": gate_minimums[
            "phase8_promotion_review_min_roi_complete_settled_observations"
        ],
        "real_money_discussion_min_total_settled_observations_with_usable_roi": gate_minimums[
            "real_money_discussion_min_total_settled_observations_with_usable_roi"
        ],
        "real_money_no_baq_as_bel_required": gate_minimums["real_money_no_baq_as_bel_required"],
        "requires_actual_settled_ts_for_roi_complete": True,
        "open_rows_are_not_performance_evidence": True,
        "roi_complete_counts_are_sample_coverage_not_profitability": True,
        "green_audit_is_not_profit_proof": True,
        "not_new_forward_evidence_by_itself": True,
        "not_forward_performance_evidence_by_itself": True,
        "not_live_profitability_evidence": True,
        "not_promotion_readiness_evidence": True,
        "not_anchor_change_evidence": True,
        "not_companion_change_evidence": True,
        "not_phase8_promotion_evidence": True,
        "not_scope_change_evidence": True,
        "not_baq_as_bel_evidence": True,
        "not_real_money_evidence": True,
        "posture_change_requires": [
            "ROI-complete settled paper observations",
            "forward-check decision-gate review",
            "settlement-quality and payout-concentration checks",
            "no BAQ-as-BEL substitution",
            "human review before any real-money discussion",
        ],
        "current_anchor_rule_id": "OP_DURABLE_K7",
        "current_primary_companion_rule_id": "CD_CORE_K8",
        "current_same_family_shadow_rule_id": "OP_REFINED_K7",
    }


def parse_lane_overrides(raw_lanes: list[str]) -> list[dict[str, Any]]:
    if not raw_lanes:
        return LANE_DEFAULTS

    lanes: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for raw in raw_lanes:
        parts = [part.strip() for part in raw.split(",")]
        if len(parts) not in {4, 5}:
            raise SystemExit(
                "--lane must be NAME,LABEL,SIGNALS_CSV,SETTLEMENTS_CSV[,ROLE]; "
                f"got {raw!r}"
            )
        name, label, signals, settlements = parts[:4]
        if not name:
            raise SystemExit("--lane NAME must be nonblank so audit lane payloads and source fingerprints stay unambiguous")
        if name in seen_names:
            raise SystemExit(
                f"duplicate lane name in --lane overrides: {name}; "
                "use unique lane names so audit lane payloads and source fingerprints stay unambiguous"
            )
        seen_names.add(name)
        if not label or not signals or not settlements:
            raise SystemExit("--lane LABEL, SIGNALS_CSV, and SETTLEMENTS_CSV must be nonblank")
        role = parts[4] if len(parts) == 5 and parts[4] else f"custom lane: {label}"
        lanes.append(
            {
                "name": name,
                "label": label,
                "role": role,
                "signals_ledger": Path(signals),
                "settlement_ledger": Path(settlements),
            }
        )
    return lanes


def load_rule_ids(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rule_ids = [str(rule.get("rule_id", "")).strip() for rule in payload.get("rules", [])]
    return [rule_id for rule_id in rule_ids if rule_id]


def clean_key(row: dict[str, str]) -> str:
    return str(row.get("signal_key", "")).strip()


def clean_rule_id(row: dict[str, str]) -> str:
    return str(row.get("rule_id", "")).strip() or "UNKNOWN_RULE"


def key_program_from_signal_key(signal_key: str) -> str:
    parts = [part.strip() for part in str(signal_key or "").split("|")]
    return parts[-1] if len(parts) >= 4 and parts[-1] else ""


def open_row_details(rows: list[dict[str, str]], limit: int = 10) -> list[dict[str, str]]:
    """Return a compact operator snapshot of rows waiting on settlement evidence."""
    details: list[dict[str, str]] = []
    for row in rows[:limit]:
        signal_key = clean_key(row)
        details.append(
            {
                "signal_key": signal_key,
                "scan_ts": str(row.get("scan_ts", "")).strip(),
                "rule_id": str(row.get("rule_id", "")).strip(),
                "track": str(row.get("track", "")).strip(),
                "card_name": str(row.get("card_name", "")).strip(),
                "race_number": str(row.get("race_number", "")).strip(),
                "race_id": str(row.get("race_id", "")).strip(),
                "key_program": key_program_from_signal_key(signal_key),
                "expected_cost": str(row.get("expected_cost", "")).strip(),
                "settlement_status": str(row.get("settlement_status", "")).strip(),
            }
        )
    return details


def summarize_open_row_details(details: list[dict[str, str]], total_open_rows: int) -> str:
    if not details:
        return "none"
    parts = [
        (
            f"{row.get('signal_key', '<missing-key>')} "
            f"({row.get('track', '?')} R{row.get('race_number', '?')}, "
            f"rule={row.get('rule_id', '?')}, key={row.get('key_program') or '?'}, "
            f"expected_cost={row.get('expected_cost') or '?'})"
        )
        for row in details
    ]
    if total_open_rows > len(details):
        parts.append(f"+{total_open_rows - len(details)} more")
    return "; ".join(parts)


def key_counter(rows: list[dict[str, str]]) -> Counter[str]:
    return Counter(clean_key(row) for row in rows if clean_key(row))


def rule_counter(rows: list[dict[str, str]]) -> Counter[str]:
    return Counter(clean_rule_id(row) for row in rows)


def duplicate_keys(counter: Counter[str]) -> list[str]:
    return sorted(key for key, count in counter.items() if count > 1)


def keyed_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    keyed: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        key = clean_key(row)
        if key:
            keyed.setdefault(key, []).append(row)
    return keyed


def metadata_mismatches(signal_rows: list[dict[str, str]], settlement_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Return matched signal_key rows whose identity metadata no longer agrees.

    Duplicate keys are already separate structural repairs, so this comparison is only
    made for keys with exactly one signal row and exactly one settlement row.
    """
    signal_by_key = keyed_rows(signal_rows)
    settlement_by_key = keyed_rows(settlement_rows)
    mismatches: list[dict[str, Any]] = []
    for key in sorted(set(signal_by_key) & set(settlement_by_key)):
        if len(signal_by_key[key]) != 1 or len(settlement_by_key[key]) != 1:
            continue
        signal_row = signal_by_key[key][0]
        settlement_row = settlement_by_key[key][0]
        field_mismatches = []
        for field in KEY_METADATA_FIELDS:
            signal_value = str(signal_row.get(field, "")).strip()
            settlement_value = str(settlement_row.get(field, "")).strip()
            if signal_value != settlement_value:
                field_mismatches.append(
                    {
                        "field": field,
                        "signal_value": signal_value,
                        "settlement_value": settlement_value,
                    }
                )
        if field_mismatches:
            mismatches.append({"signal_key": key, "fields": field_mismatches})
    return mismatches


def summarize_metadata_mismatches(mismatches: list[dict[str, Any]], limit: int = 5) -> str:
    if not mismatches:
        return "none"
    parts = []
    for mismatch in mismatches[:limit]:
        field_bits = ", ".join(
            f"{field['field']}: signal={field['signal_value'] or '<blank>'} settlement={field['settlement_value'] or '<blank>'}"
            for field in mismatch.get("fields", [])
        )
        parts.append(f"{mismatch.get('signal_key', '<unknown>')}[{field_bits}]")
    if len(mismatches) > limit:
        parts.append(f"+{len(mismatches) - limit} more")
    return "; ".join(parts)


def settled_ts_gap_reason(row: dict[str, str]) -> str:
    """Explain why a settled row's timestamp is not audit-grade yet."""
    text = str(row.get("settled_ts") or "").strip()
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


def audit_roi_gap_reason(row: dict[str, str]) -> str:
    """Explain why a settled hit/miss row cannot count as audit-grade ROI evidence."""
    reasons = [token.strip() for token in roi_gap_reason(row).split(";") if token.strip()]
    timestamp_reason = settled_ts_gap_reason(row)
    if timestamp_reason and timestamp_reason not in reasons:
        reasons.append(timestamp_reason)
    return "; ".join(reasons)


def reason_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        reason = audit_roi_gap_reason(row)
        for part in [token.strip() for token in reason.split(";") if token.strip()]:
            counter[part] += 1
    return dict(sorted(counter.items()))


def summarize_reasons(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return "; ".join(f"{reason}: {count}" for reason, count in counts.items())


def pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "n/a"
    return f"{numerator}/{denominator} ({(numerator / denominator) * 100:.1f}%)"


def lane_assessment(
    *,
    missing_templates: int,
    orphan_settlements: int,
    duplicate_signal_keys: int,
    duplicate_settlement_keys: int,
    blank_signal_keys: int,
    blank_settlement_keys: int,
    metadata_mismatches: int,
    incomplete_settled: int,
    roi_gap_settled: int,
    roi_complete_settled: int,
    min_settled: int,
    portfolio_review_settled: int,
) -> str:
    structural_gaps = (
        missing_templates
        + orphan_settlements
        + duplicate_signal_keys
        + duplicate_settlement_keys
        + blank_signal_keys
        + blank_settlement_keys
        + metadata_mismatches
    )
    if structural_gaps:
        return "ledger_structure_repair_required"
    if incomplete_settled or roi_gap_settled:
        return "settlement_quality_repair_required"
    if roi_complete_settled <= 0:
        return "pre_evidence_waiting_for_roi_complete_settlements"
    if roi_complete_settled < min_settled:
        return "collecting_first_read_pre_evidence"
    if roi_complete_settled < portfolio_review_settled:
        return "first_read_possible_but_not_portfolio_review"
    return "portfolio_review_sample_audit_clear_not_profit_proof"


def lane_next_action(
    *,
    assessment: str,
    signal_rows: int,
    open_settlement_rows: int,
    incomplete_settled_rows: int,
    roi_gap_settled_rows: int,
    roi_complete_settled_rows: int,
    min_settled: int,
    portfolio_review_settled: int,
    first_read_sample_subject: str = "ROI-complete settled row(s)",
    first_read_context: str = "before even a first-read sample is available",
    portfolio_review_context: str = "before portfolio-review confidence",
) -> tuple[str, str]:
    if assessment == "ledger_structure_repair_required":
        return (
            "repair_ledger_structure",
            "Repair missing templates, orphan settlement rows, duplicate keys, blank signal keys, or matched-key metadata mismatches before reading settlement quality.",
        )
    if incomplete_settled_rows:
        return (
            "complete_settlement_outcomes",
            f"Complete {incomplete_settled_rows} settled row(s) that still lack hit/miss outcome data before interpreting realized ROI.",
        )
    if roi_gap_settled_rows:
        return (
            "repair_roi_coverage",
            f"Repair usable return/cost/timestamp coverage for {roi_gap_settled_rows} settled outcome row(s) before using ROI totals.",
        )
    if open_settlement_rows:
        return (
            "settle_open_rows",
            f"Enter results for {open_settlement_rows} open settlement row(s); open rows are observation work, not performance evidence yet.",
        )
    if signal_rows <= 0:
        return (
            "collect_signals",
            "No signal rows exist yet, so the next useful action is to keep the scan/logging path operational and wait for qualifying paper observations.",
        )
    if roi_complete_settled_rows < min_settled:
        remaining = max(min_settled - roi_complete_settled_rows, 0)
        return (
            "continue_collecting_roi_complete_settlements",
            f"Collect {remaining} more {first_read_sample_subject} {first_read_context}.",
        )
    if roi_complete_settled_rows < portfolio_review_settled:
        remaining = max(portfolio_review_settled - roi_complete_settled_rows, 0)
        return (
            "review_first_read_keep_collecting",
            f"A first read is possible, but collect {remaining} more ROI-complete settled row(s) {portfolio_review_context}.",
        )
    return (
        "portfolio_review_sample_ready_audit_only",
        "The audit sample milestone is clear; review through the forward-check decision gates and do not treat audit cleanliness as profit proof.",
    )


def build_promotion_gate(
    *,
    lane: dict[str, Any],
    signal_rows: list[dict[str, str]],
    roi_complete_rows: list[dict[str, str]],
    min_settled: int,
    portfolio_review_settled: int,
    shadow_rule_min_settled: int,
) -> dict[str, Any]:
    promotion_scope = str(lane.get("promotion_scope", "lane_total_first_read"))
    expected_rule_ids = load_rule_ids(Path(lane["rules_file"]) if lane.get("rules_file") else None)
    scorecard_metadata = load_scorecard_rule_metadata()
    scorecard_rules = scorecard_metadata["rules"] if isinstance(scorecard_metadata.get("rules"), dict) else {}
    signal_rule_counts = rule_counter(signal_rows)
    roi_complete_rule_counts = rule_counter(roi_complete_rows)
    observed_rule_ids = sorted(set(signal_rule_counts) | set(roi_complete_rule_counts))
    rule_ids = expected_rule_ids or observed_rule_ids

    if promotion_scope == "per_rule_shadow_watch":
        rule_rows = []
        for rule_id in rule_ids:
            metadata = scorecard_rules.get(rule_id, {}) if isinstance(scorecard_rules.get(rule_id, {}), dict) else {}
            roi_complete_count = int(roi_complete_rule_counts.get(rule_id, 0))
            rule_rows.append(
                {
                    "rule_id": rule_id,
                    "signal_rows": int(signal_rule_counts.get(rule_id, 0)),
                    "roi_complete_settled_rows": roi_complete_count,
                    "promotion_progress": pct(roi_complete_count, shadow_rule_min_settled),
                    "promotion_ready": roi_complete_count >= shadow_rule_min_settled,
                    "scorecard_tier": metadata.get("tier", "UNRANKED"),
                    "scorecard_action_now": metadata.get("action_now", ""),
                    "scorecard_note": metadata.get("note", ""),
                    "holdout_roi": metadata.get("holdout_roi"),
                    "holdout_races": metadata.get("holdout_races"),
                    "wf_selected": metadata.get("wf_selected", ""),
                }
            )
        weakest_count = min((row["roi_complete_settled_rows"] for row in rule_rows), default=0)
        ready = bool(rule_rows) and all(row["promotion_ready"] for row in rule_rows)
        skip_rule_ids = [row["rule_id"] for row in rule_rows if row.get("scorecard_tier") == "SKIP"]
        skip_caution = (
            " negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion;"
            if skip_rule_ids
            else ""
        )
        return {
            "scope": promotion_scope,
            "active_first_read_gate": "phase8_promotion_review",
            "active_first_read_scope": "per_rule_shadow_watch",
            "active_first_read_min_settled": shadow_rule_min_settled,
            "active_first_read_count": weakest_count,
            "active_first_read_progress": pct(weakest_count, shadow_rule_min_settled),
            "min_roi_complete_settled_per_rule": shadow_rule_min_settled,
            "expected_rule_ids": rule_ids,
            "rule_progress": rule_rows,
            "scorecard_rule_metadata": {
                "source_path": scorecard_metadata["source_path"],
                "source_loaded": scorecard_metadata["source_loaded"],
                "fallback_used": scorecard_metadata["fallback_used"],
                "fallback_reason": scorecard_metadata["fallback_reason"],
            },
            "scorecard_skip_rule_ids": skip_rule_ids,
            "promotion_ready": ready,
            "gate_read": (
                f"Shadow/watch phase8_promotion_review gate is per-rule: every expected shadow rule needs "
                f"{shadow_rule_min_settled} ROI-complete settled row(s) before review; the {shadow_rule_min_settled}-row count is a review floor, not a promotion entitlement; "
                f"lane totals alone do not promote OP_REFINED_K7 or any other Phase 8 pocket; "
                f"scorecard tiers remain binding ({scorecard_metadata['source_path']});"
                f"{skip_caution} "
                f"weakest current rule coverage is {weakest_count}/{shadow_rule_min_settled}."
            ),
        }

    return {
        "scope": promotion_scope,
        "active_first_read_gate": "anchor_displacement",
        "active_first_read_scope": "lane_total_first_read",
        "active_first_read_min_settled": min_settled,
        "active_first_read_count": len(roi_complete_rows),
        "active_first_read_progress": pct(len(roi_complete_rows), min_settled),
        "min_roi_complete_settled_lane_total": min_settled,
        "portfolio_review_settled_lane_total": portfolio_review_settled,
        "expected_rule_ids": rule_ids,
        "rule_progress": [
            {
                "rule_id": rule_id,
                "signal_rows": int(signal_rule_counts.get(rule_id, 0)),
                "roi_complete_settled_rows": int(roi_complete_rule_counts.get(rule_id, 0)),
            }
            for rule_id in rule_ids
        ],
        "promotion_ready": len(roi_complete_rows) >= min_settled,
        "gate_read": (
            f"Primary anchor_displacement first-read gate is lane-total: {min_settled} ROI-complete settled row(s) before a first read "
            f"and {portfolio_review_settled} before broader portfolio review; audit cleanliness still is not profit proof."
        ),
    }


def audit_lane(lane: dict[str, Any], min_settled: int, portfolio_review_settled: int, shadow_rule_min_settled: int) -> dict[str, Any]:
    signals_path = Path(lane["signals_ledger"])
    settlement_path = Path(lane["settlement_ledger"])
    signal_rows = load_csv_rows(signals_path)
    settlement_rows = load_csv_rows(settlement_path)

    signal_counts = key_counter(signal_rows)
    settlement_counts = key_counter(settlement_rows)
    signal_keys = set(signal_counts)
    settlement_keys = set(settlement_counts)

    missing_template_keys = sorted(signal_keys - settlement_keys)
    orphan_settlement_keys = sorted(settlement_keys - signal_keys)
    duplicate_signal_keys = duplicate_keys(signal_counts)
    duplicate_settlement_keys = duplicate_keys(settlement_counts)
    blank_signal_key_rows = sum(1 for row in signal_rows if not clean_key(row))
    blank_settlement_key_rows = sum(1 for row in settlement_rows if not clean_key(row))
    metadata_mismatch_rows = metadata_mismatches(signal_rows, settlement_rows)

    open_rows = [row for row in settlement_rows if is_open_row(row)]
    open_details = open_row_details(open_rows)
    incomplete_rows = [row for row in settlement_rows if is_incomplete_settled_row(row)]
    settled_outcome_rows = [row for row in settlement_rows if classify_outcome(row) in {"hit", "miss"}]
    roi_gap_rows = [row for row in settled_outcome_rows if audit_roi_gap_reason(row)]
    roi_complete_rows = [row for row in settled_outcome_rows if not audit_roi_gap_reason(row)]
    reasons = reason_counts(roi_gap_rows)

    actual_cost_values = [parse_float(row.get("actual_cost")) for row in roi_complete_rows]
    expected_cost_values = [parse_float(row.get("expected_cost")) for row in roi_complete_rows]
    actual_return_values = [parse_float(row.get("actual_return")) for row in roi_complete_rows]
    roi_complete_costs = [actual if actual is not None else expected for actual, expected in zip(actual_cost_values, expected_cost_values)]
    cost_sum = sum(value for value in roi_complete_costs if value is not None)
    return_sum = sum(value for value in actual_return_values if value is not None)

    promotion_gate = build_promotion_gate(
        lane=lane,
        signal_rows=signal_rows,
        roi_complete_rows=roi_complete_rows,
        min_settled=min_settled,
        portfolio_review_settled=portfolio_review_settled,
        shadow_rule_min_settled=shadow_rule_min_settled,
    )
    active_first_read_count = int(promotion_gate["active_first_read_count"])
    active_first_read_min_settled = int(promotion_gate["active_first_read_min_settled"])
    is_shadow_per_rule_gate = promotion_gate["scope"] == "per_rule_shadow_watch"

    assessment = lane_assessment(
        missing_templates=len(missing_template_keys),
        orphan_settlements=len(orphan_settlement_keys),
        duplicate_signal_keys=len(duplicate_signal_keys),
        duplicate_settlement_keys=len(duplicate_settlement_keys),
        blank_signal_keys=blank_signal_key_rows,
        blank_settlement_keys=blank_settlement_key_rows,
        metadata_mismatches=len(metadata_mismatch_rows),
        incomplete_settled=len(incomplete_rows),
        roi_gap_settled=len(roi_gap_rows),
        roi_complete_settled=active_first_read_count,
        min_settled=active_first_read_min_settled,
        portfolio_review_settled=portfolio_review_settled,
    )
    next_action, next_action_reason = lane_next_action(
        assessment=assessment,
        signal_rows=len(signal_rows),
        open_settlement_rows=len(open_rows),
        incomplete_settled_rows=len(incomplete_rows),
        roi_gap_settled_rows=len(roi_gap_rows),
        roi_complete_settled_rows=active_first_read_count,
        min_settled=active_first_read_min_settled,
        portfolio_review_settled=portfolio_review_settled,
        first_read_sample_subject=(
            "ROI-complete settled row(s) for the weakest shadow rule"
            if is_shadow_per_rule_gate
            else "ROI-complete settled row(s)"
        ),
        first_read_context=(
            "before a per-rule Phase 8 promotion-review sample is available"
            if is_shadow_per_rule_gate
            else "before even a first-read sample is available"
        ),
        portfolio_review_context=(
            "before portfolio-review confidence; per-rule Phase 8 promotion still needs every shadow rule to clear its own gate"
            if is_shadow_per_rule_gate
            else "before portfolio-review confidence"
        ),
    )

    return {
        "name": lane["name"],
        "label": lane["label"],
        "role": lane["role"],
        "signals_ledger": display_path(signals_path),
        "settlement_ledger": display_path(settlement_path),
        "signal_rows": len(signal_rows),
        "settlement_rows": len(settlement_rows),
        "blank_signal_key_rows": blank_signal_key_rows,
        "blank_settlement_key_rows": blank_settlement_key_rows,
        "duplicate_signal_keys": duplicate_signal_keys,
        "duplicate_settlement_keys": duplicate_settlement_keys,
        "missing_settlement_template_keys": missing_template_keys,
        "orphan_settlement_keys": orphan_settlement_keys,
        "metadata_mismatches": metadata_mismatch_rows,
        "metadata_mismatch_summary": summarize_metadata_mismatches(metadata_mismatch_rows),
        "open_settlement_rows": len(open_rows),
        "open_settlement_keys": [clean_key(row) for row in open_rows if clean_key(row)],
        "open_settlement_row_details": open_details,
        "open_settlement_summary": summarize_open_row_details(open_details, len(open_rows)),
        "incomplete_settled_rows": len(incomplete_rows),
        "settled_outcome_rows": len(settled_outcome_rows),
        "roi_complete_settled_rows": len(roi_complete_rows),
        "roi_gap_settled_rows": len(roi_gap_rows),
        "roi_gap_reason_counts": reasons,
        "roi_gap_reason_summary": summarize_reasons(reasons),
        "active_first_read_gate": promotion_gate["active_first_read_gate"],
        "active_first_read_scope": promotion_gate["active_first_read_scope"],
        "active_first_read_min_settled": active_first_read_min_settled,
        "active_first_read_count": active_first_read_count,
        "first_read_progress": promotion_gate["active_first_read_progress"],
        "portfolio_review_progress": pct(len(roi_complete_rows), portfolio_review_settled),
        "roi_complete_cost_sum": round(cost_sum, 2),
        "roi_complete_return_sum": round(return_sum, 2),
        "assessment": assessment,
        "next_action": next_action,
        "next_action_reason": next_action_reason,
        "promotion_gate": promotion_gate,
    }


def build_current_read(lanes: list[dict[str, Any]], gate_minimums: dict[str, Any]) -> str:
    lane_bits = [
        f"{lane['name']}={lane['assessment']} with {lane['roi_complete_settled_rows']} ROI-complete settled row(s), "
        f"{lane['missing_settlement_template_count']} missing template(s), {lane['orphan_settlement_count']} orphan settlement row(s), "
        f"{lane['metadata_mismatch_count']} matched-key metadata mismatch(es), and {lane['roi_gap_settled_rows']} ROI-coverage gap row(s)"
        for lane in lanes
    ]
    gate_bits = [lane["promotion_gate"]["gate_read"].rstrip(".") for lane in lanes if lane.get("promotion_gate")]
    return (
        "settlement audit: "
        + "; ".join(lane_bits)
        + ("; " + "; ".join(gate_bits) if gate_bits else "")
        + f"; {gate_minimums['alignment_read']}: "
        f"anchor_displacement={gate_minimums['anchor_displacement_min_roi_complete_settled_observations']}, "
        f"phase8_promotion_review={gate_minimums['phase8_promotion_review_min_roi_complete_settled_observations']}, "
        f"real_money_discussion={gate_minimums['real_money_discussion_min_total_settled_observations_with_usable_roi']}"
        + "; ledger-completeness / ROI-coverage audit only, not new forward evidence by itself; "
        "OP_DURABLE_K7 remains the safest OP anchor, CD_CORE_K8 remains the paper companion, "
        "OP_REFINED_K7 remains shadow/watch only, BAQ is not BEL, Harville remains benchmark-only, "
        "and current odds-only XGBoost remains research-only unless future settled evidence clears the explicit gates"
    )


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    gate_minimums = resolve_gate_minimums(args)
    lane_defs = parse_lane_overrides(args.lane)
    audited_lanes = [
        audit_lane(
            lane,
            gate_minimums["active_min_settled"],
            gate_minimums["active_portfolio_review_settled"],
            gate_minimums["active_shadow_rule_min_settled"],
        )
        for lane in lane_defs
    ]
    for lane in audited_lanes:
        lane["missing_settlement_template_count"] = len(lane["missing_settlement_template_keys"])
        lane["orphan_settlement_count"] = len(lane["orphan_settlement_keys"])
        lane["duplicate_signal_key_count"] = len(lane["duplicate_signal_keys"])
        lane["duplicate_settlement_key_count"] = len(lane["duplicate_settlement_keys"])
        lane["metadata_mismatch_count"] = len(lane["metadata_mismatches"])

    payload = {
        "artifact_status": "pass",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "valid_evidence_scope": SETTLEMENT_AUDIT_VALID_EVIDENCE_SCOPE,
        "evidence_boundary_text": SETTLEMENT_AUDIT_EVIDENCE_BOUNDARY_TEXT,
        "min_settled": gate_minimums["active_min_settled"],
        "portfolio_review_settled": gate_minimums["active_portfolio_review_settled"],
        "shadow_rule_min_settled": gate_minimums["active_shadow_rule_min_settled"],
        "decision_gate_minimums": gate_minimums,
        "evidence_boundary_metadata": build_evidence_boundary_metadata(gate_minimums),
        "source_files": build_source_files(lane_defs),
        "summary": {
            "current_read": build_current_read(audited_lanes, gate_minimums),
            "evidence_boundary": SETTLEMENT_AUDIT_EVIDENCE_BOUNDARY_TEXT,
            "decision_gate_alignment": gate_minimums["alignment_read"],
        },
        "lanes": audited_lanes,
    }
    return payload


def render_text(payload: dict[str, Any]) -> str:
    lines = [
        "Paper Trade Settlement Audit",
        f"Generated: {payload['generated_at']}",
        f"valid_evidence_scope={payload['valid_evidence_scope']}",
        f"Evidence boundary: {payload['evidence_boundary_text']}",
        (
            "Decision gates: "
            f"source={payload['decision_gate_minimums']['source_path']} "
            f"loaded={payload['decision_gate_minimums']['source_loaded']} "
            f"anchor_displacement={payload['decision_gate_minimums']['anchor_displacement_min_roi_complete_settled_observations']} "
            f"phase8_promotion_review={payload['decision_gate_minimums']['phase8_promotion_review_min_roi_complete_settled_observations']} "
            f"real_money_discussion={payload['decision_gate_minimums']['real_money_discussion_min_total_settled_observations_with_usable_roi']} "
            f"real_money_no_baq_as_bel_required={payload['decision_gate_minimums']['real_money_no_baq_as_bel_required']}"
        ),
        (
            "Source fingerprints: "
            + ", ".join(
                f"{label}={fp['bytes']} bytes/{fp['sha256'][:12] if fp['sha256'] else 'missing'}"
                for label, fp in payload.get("source_files", {}).items()
            )
        ),
        payload["summary"]["current_read"],
    ]
    for lane in payload["lanes"]:
        lines.append(
            f"- {lane['label']}: assessment={lane['assessment']}; signals={lane['signal_rows']}; "
            f"settlement_rows={lane['settlement_rows']}; ROI-complete settled={lane['roi_complete_settled_rows']}; "
            f"missing_templates={lane['missing_settlement_template_count']}; orphans={lane['orphan_settlement_count']}; "
            f"metadata_mismatches={lane['metadata_mismatch_count']}; "
            f"open_row_details={lane['open_settlement_summary']}; "
            f"ROI gaps={lane['roi_gap_settled_rows']} ({lane['roi_gap_reason_summary']}); "
            f"next_action={lane['next_action']}; gate={lane['promotion_gate']['gate_read']}"
        )
    return "\n".join(lines) + "\n"


def render_md(payload: dict[str, Any]) -> str:
    lines = [
        "# Paper Trade Settlement Audit",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        "## Evidence Boundary",
        "",
        f"- `valid_evidence_scope={payload['valid_evidence_scope']}`",
        f"- {payload['evidence_boundary_text']}",
        "- Deployment posture stays unchanged: `OP_DURABLE_K7` remains the safest OP anchor, `CD_CORE_K8` remains the paper companion, `OP_REFINED_K7` remains shadow/watch only, Harville remains benchmark-only, current odds-only `XGBoost` remains research-only/parked, and `BAQ` is not `BEL`.",
        "- Only settled paper trades with usable return/cost coverage and actual ISO `settled_ts` values can support future forward-performance claims.",
        f"- Machine-readable boundary: `evidence_boundary_metadata.artifact_role` is `{payload['evidence_boundary_metadata']['artifact_role']}`; `green_audit_is_not_profit_proof=true`, `roi_complete_counts_are_sample_coverage_not_profitability=true`, and `not_real_money_evidence=true` keep this audit out of promotion/live-profitability claims.",
        "",
        "## Decision-Gate Source",
        "",
        f"- Source: `{payload['decision_gate_minimums']['source_path']}`; loaded={payload['decision_gate_minimums']['source_loaded']}; fallback_used={payload['decision_gate_minimums']['fallback_used']}.",
        f"- Scorecard `decision_gate_minimums`: anchor_displacement={payload['decision_gate_minimums']['anchor_displacement_min_roi_complete_settled_observations']} ROI-complete same-candidate settled observations; phase8_promotion_review={payload['decision_gate_minimums']['phase8_promotion_review_min_roi_complete_settled_observations']} ROI-complete shadow observations; real_money_discussion={payload['decision_gate_minimums']['real_money_discussion_min_total_settled_observations_with_usable_roi']} total settled observations with usable ROI; real_money_requires={'; '.join(payload['decision_gate_minimums']['real_money_discussion_also_requires'])}.",
        f"- Active audit gates: min_settled={payload['min_settled']}; shadow_rule_min_settled={payload['shadow_rule_min_settled']}; portfolio_review_settled={payload['portfolio_review_settled']}. {payload['summary']['decision_gate_alignment']}.",
        "- These thresholds are posture-gate metadata for audit routing only; they are not live-profitability, promotion, anchor-change, or real-money evidence.",
        "",
        "## Current Read",
        "",
        f"- {payload['summary']['current_read']}",
        "",
        "## Lane Ledger Audit",
        "",
        "| Lane | Role | Signals | Settlement rows | Missing templates | Orphan settlements | Metadata mismatches | Open rows | Settled outcomes | ROI-complete settled | ROI gaps | First read | Portfolio review | Next action | Assessment |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|",
    ]
    for lane in payload["lanes"]:
        lines.append(
            f"| {lane['label']} | {lane['role']} | {lane['signal_rows']} | {lane['settlement_rows']} | "
            f"{lane['missing_settlement_template_count']} | {lane['orphan_settlement_count']} | {lane['metadata_mismatch_count']} | {lane['open_settlement_rows']} | "
            f"{lane['settled_outcome_rows']} | {lane['roi_complete_settled_rows']} | {lane['roi_gap_settled_rows']} | "
            f"{lane['first_read_progress']} | {lane['portfolio_review_progress']} | `{lane['next_action']}` | `{lane['assessment']}` |"
        )

    lines.extend(["", "## Promotion Gates", ""])
    for lane in payload["lanes"]:
        gate = lane["promotion_gate"]
        lines.append(f"- **{lane['label']}**: {gate['gate_read']}")
        if gate.get("rule_progress"):
            progress = "; ".join(
                f"{row['rule_id']} ({row['scorecard_tier']}) {row['promotion_progress']}"
                if "promotion_progress" in row and row.get("scorecard_tier")
                else f"{row['rule_id']} {row['promotion_progress']}"
                if "promotion_progress" in row
                else f"{row['rule_id']} {row['roi_complete_settled_rows']} ROI-complete"
                for row in gate["rule_progress"]
            )
            lines.append(f"  - Rule coverage: {progress}")

    lines.extend(["", "## Open Settlement Queue", ""])
    any_open = False
    for lane in payload["lanes"]:
        if lane["open_settlement_rows"]:
            any_open = True
            lines.append(
                f"- **{lane['label']}**: {lane['open_settlement_summary']}. "
                "Settle these rows only from actual result/payout evidence with a real `settled_ts`; they are not performance evidence while open."
            )
    if not any_open:
        lines.append("- No open settlement rows are visible in the audited ledgers right now.")

    lines.extend(["", "## Next Actions", ""])
    for lane in payload["lanes"]:
        lines.append(f"- **{lane['label']}**: `{lane['next_action']}` — {lane['next_action_reason']}")

    lines.extend(["", "## Repair Queue", ""])
    any_repair = False
    for lane in payload["lanes"]:
        lane_repairs: list[str] = []
        if lane["blank_signal_key_rows"]:
            lane_repairs.append(f"{lane['blank_signal_key_rows']} blank signal-key row(s) in signal ledger")
        if lane["blank_settlement_key_rows"]:
            lane_repairs.append(f"{lane['blank_settlement_key_rows']} blank settlement-key row(s) in settlement ledger")
        if lane["duplicate_signal_keys"]:
            lane_repairs.append(f"duplicate signal keys: {', '.join(lane['duplicate_signal_keys'])}")
        if lane["duplicate_settlement_keys"]:
            lane_repairs.append(f"duplicate settlement keys: {', '.join(lane['duplicate_settlement_keys'])}")
        if lane["missing_settlement_template_keys"]:
            lane_repairs.append(f"missing settlement templates: {', '.join(lane['missing_settlement_template_keys'][:5])}")
        if lane["orphan_settlement_keys"]:
            lane_repairs.append(f"orphan settlement rows: {', '.join(lane['orphan_settlement_keys'][:5])}")
        if lane["metadata_mismatches"]:
            lane_repairs.append(f"metadata mismatches: {lane['metadata_mismatch_summary']}")
        if lane["incomplete_settled_rows"]:
            lane_repairs.append(f"{lane['incomplete_settled_rows']} settled row(s) missing outcome")
        if lane["roi_gap_settled_rows"]:
            lane_repairs.append(f"{lane['roi_gap_settled_rows']} settled row(s) missing ROI coverage ({lane['roi_gap_reason_summary']})")
        if lane_repairs:
            any_repair = True
            lines.append(f"- **{lane['label']}**: " + "; ".join(lane_repairs))
    if not any_repair:
        lines.append("- No structural or settled-row ROI-coverage repairs are visible in the audited ledgers right now.")

    lines.extend([
        "",
        "## Source Ledgers",
        "",
    ])
    for lane in payload["lanes"]:
        lines.append(f"- {lane['label']} signals: `{lane['signals_ledger']}`")
        lines.append(f"- {lane['label']} settlements: `{lane['settlement_ledger']}`")

    lines.extend([
        "",
        "## Source Fingerprints",
        "",
        "| Source | Path | Exists | Bytes | SHA-256 |",
        "|---|---|---|---:|---|",
    ])
    for label, fp in payload.get("source_files", {}).items():
        lines.append(
            f"| {label} | `{fp['path']}` | `{fp['exists']}` | {fp['bytes']} | `{fp['sha256']}` |"
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    payload = build_payload(args)
    output_md = Path(args.output_md)
    output_json = Path(args.output_json)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    md = render_md(payload)
    output_md.write_text(md, encoding="utf-8")
    output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if args.format == "json":
        print(json.dumps(payload, indent=2))
    elif args.format == "text":
        print(render_text(payload), end="")
    else:
        print(md, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
