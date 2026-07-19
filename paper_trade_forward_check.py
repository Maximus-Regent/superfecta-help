#!/usr/bin/env python3
"""
Forward paper-trade expectation check.

Purpose:
- Compare settled paper-trade observations against the frozen holdout baselines.
- Keep the daily paper / shadow ledgers tied to the same honest standard used elsewhere.
- Say clearly when there is not enough settled sample yet.

This script validates hit rate first and flat-ticket ROI when settlement data exists.
The settlement ledger is optional, but once populated it lets the same frozen standard
check both hit rate and actual forward return.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
DEFAULT_SIGNALS_LEDGER = BASE / "paper_trades" / "phase7_current_paper_paper_trade_signals.csv"
DEFAULT_RECOMMENDATION_LEDGER = BASE / "paper_trades" / "phase7_current_paper_paper_trade_recommendations.csv"
DEFAULT_RULES = BASE / "phase7_current_paper_rules.json"
DEFAULT_FROZEN_EVAL = BASE / "frozen_portfolio_eval_summary.csv"
DEFAULT_OUTPUT = BASE / "out" / "paper_trade_forward_check.md"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
FALLBACK_GATE_MINIMUMS = {
    "anchor_displacement": 30,
    "phase8_promotion_review": 20,
    "real_money_discussion": 100,
}
NO_BAQ_AS_BEL_REQUIREMENT = "no BAQ-as-BEL substitution"

PORTFOLIO_BASELINE_MAP = {
    "op_anchor_rules.json": ("phase7_live", "OP anchor paper lane", ["OP_DURABLE_K7"]),
    "phase7_current_paper_rules.json": ("phase7_live", "Phase 7 current paper lane", ["OP_DURABLE_K7", "CD_CORE_K8"]),
    "phase7_live_rules.json": ("phase7_live", "Phase 7 legacy rules lane", ["BEL_BROAD1_K7", "OP_DURABLE_K7", "CD_CORE_K8"]),
    "phase8_shadow_rules.json": ("phase8_frozen", "Phase 8 shadow lane", ["OP_REFINED_K7", "AQU_K9", "SA_K9", "KEE_K9", "CD_REFINED_K9", "DMR_FALL_K7"]),
}

HIT_TOKENS = {"hit", "won", "win", "winner", "cash", "cashed", "1", "true", "yes", "y"}
MISS_TOKENS = {"miss", "lost", "lose", "loss", "0", "false", "no", "n", "x"}
SETTLED_STATUS_TOKENS = {"settled", "closed", "complete", "completed", "done"}
OPEN_STATUS_TOKENS = {"open", "pending", "unsettled", "todo"}
SETTLED_TS_PLACEHOLDER_TOKENS = {"", "open", "pending", "unsettled", "todo", "tbd", "na", "n/a", "none", "null"}
FORWARD_CHECK_VALID_EVIDENCE_SCOPE = "frozen-baseline comparison for ROI-complete paper observations"
FORWARD_CHECK_EVIDENCE_BOUNDARY = {
    "artifact_role": "paper-trade forward check",
    "valid_use": FORWARD_CHECK_VALID_EVIDENCE_SCOPE,
    "not_new_forward_evidence_by_itself": True,
    "not_current_day_scanner_result": True,
    "not_anchor_change_evidence": True,
    "not_phase8_promotion_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "non_goals": [
        "do not treat forward-check cleanliness as new observations",
        "do not treat sub-threshold hot or cold reads as rule-change permission",
        "do not treat scorecard-gate visibility as promotion readiness",
        "do not treat any forward-check pass as live-profitability or real-money support",
    ],
}
FORWARD_CHECK_BOUNDARY_TEXT = (
    "forward check is a frozen-baseline comparison for ROI-complete paper observations only; "
    "not a current-day scanner result, not new forward evidence by itself, not anchor-change evidence, "
    "not Phase 8 promotion evidence, not live-profitability evidence, and not real-money support"
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compare settled paper-trade observations against frozen baselines")
    p.add_argument("--signals-ledger", default=str(DEFAULT_SIGNALS_LEDGER), help="Signal ledger CSV path")
    p.add_argument("--recommendation-ledger", default=str(DEFAULT_RECOMMENDATION_LEDGER), help="Recommendation ledger CSV path")
    p.add_argument("--settlement-ledger", help="Optional settlement ledger CSV path; defaults from --signals-ledger")
    p.add_argument("--rules", default=str(DEFAULT_RULES), help="Rules JSON path for the lane being checked")
    p.add_argument("--frozen-eval", default=str(DEFAULT_FROZEN_EVAL), help="Frozen evaluation summary CSV path")
    p.add_argument("--scorecard-json", default=str(SCORECARD_JSON), help="Forward evidence scorecard JSON sidecar for decision-gate minimums")
    p.add_argument("--min-settled", type=int, default=None, help="Minimum settled races before treating the check as decision-grade; defaults to the scorecard anchor-displacement gate")
    p.add_argument("--portfolio-review-settled", type=int, default=None, help="Broader settled-race milestone for portfolio review readiness; defaults to the scorecard real-money discussion gate")
    p.add_argument("--format", choices=["text", "md", "json"], default="md", help="Output format")
    p.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Optional output path")
    return p.parse_args()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def load_scorecard_gate_minimums(path: Path = SCORECARD_JSON) -> dict[str, Any]:
    """Load posture-change sample gates from the forward scorecard sidecar.

    The forward checker is the first ROI-read surface operators may inspect after
    settlements exist, so its sample milestones should stay source-matched to the
    frozen-evidence scorecard's machine-readable decision gates. If the sidecar
    is absent or malformed, use conservative historical defaults and expose the
    fallback explicitly in the payload.
    """
    fallback = {
        "source_path": display_path(path),
        "source_loaded": False,
        "fallback_used": True,
        "fallback_reason": "forward_evidence_scorecard.json missing or unreadable; using conservative historical gate defaults",
        "anchor_displacement_min_roi_complete_settled_observations": FALLBACK_GATE_MINIMUMS["anchor_displacement"],
        "phase8_promotion_review_min_roi_complete_settled_observations": FALLBACK_GATE_MINIMUMS["phase8_promotion_review"],
        "real_money_discussion_min_total_settled_observations_with_usable_roi": FALLBACK_GATE_MINIMUMS["real_money_discussion"],
        "real_money_discussion_also_requires": [NO_BAQ_AS_BEL_REQUIREMENT],
        "real_money_no_baq_as_bel_required": True,
    }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        gates = payload["decision_gate_minimums"]
        if not isinstance(gates, dict):
            raise ValueError("decision_gate_minimums must be an object")
        anchor_gate = require_positive_non_bool_int(
            gates["anchor_displacement"]["min_roi_complete_settled_observations"],
            "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
        )
        phase8_gate = require_positive_non_bool_int(
            gates["phase8_promotion_review"]["min_roi_complete_settled_observations"],
            "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
        )
        real_money_gate_payload = gates["real_money_discussion"]
        real_money_gate = require_positive_non_bool_int(
            real_money_gate_payload["min_total_settled_observations_with_usable_roi"],
            "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
        )
        also_requires = real_money_gate_payload["also_requires"]
        if not isinstance(also_requires, list) or not all(isinstance(item, str) for item in also_requires):
            raise ValueError("decision_gate_minimums.real_money_discussion.also_requires must be a string list")
        real_money_requirements = [item.strip() for item in also_requires]
        if NO_BAQ_AS_BEL_REQUIREMENT not in real_money_requirements:
            raise ValueError("decision_gate_minimums.real_money_discussion.also_requires must include no BAQ-as-BEL substitution")
    except (OSError, json.JSONDecodeError):
        return fallback
    except (KeyError, TypeError, ValueError) as exc:
        return {
            **fallback,
            "source_loaded": True,
            "fallback_reason": "forward_evidence_scorecard.json decision_gate_minimums malformed; using conservative historical gate defaults",
            "malformed_gate_error": str(exc),
        }

    conservative_floors = {
        "anchor_displacement_min_roi_complete_settled_observations": FALLBACK_GATE_MINIMUMS["anchor_displacement"],
        "phase8_promotion_review_min_roi_complete_settled_observations": FALLBACK_GATE_MINIMUMS["phase8_promotion_review"],
        "real_money_discussion_min_total_settled_observations_with_usable_roi": FALLBACK_GATE_MINIMUMS["real_money_discussion"],
    }
    loaded_values = {
        "anchor_displacement_min_roi_complete_settled_observations": anchor_gate,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_gate,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_gate,
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
            "source_path": display_path(path),
            "source_loaded": True,
            "fallback_used": True,
            "fallback_reason": "forward_evidence_scorecard.json decision_gate_minimums fell below conservative historical floors; using conservative historical gate defaults",
            "rejected_lowered_values": lowered,
            "real_money_discussion_also_requires": real_money_requirements,
            "real_money_no_baq_as_bel_required": NO_BAQ_AS_BEL_REQUIREMENT in real_money_requirements,
            **conservative_floors,
        }

    return {
        "source_path": display_path(path),
        "source_loaded": True,
        "fallback_used": False,
        "fallback_reason": "",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_gate,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_gate,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_gate,
        "real_money_discussion_also_requires": real_money_requirements,
        "real_money_no_baq_as_bel_required": NO_BAQ_AS_BEL_REQUIREMENT in real_money_requirements,
    }


def require_positive_non_bool_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive non-boolean integer")
    return value


def default_first_read_gate(portfolio_name: str, rules_path: Path) -> tuple[str, int]:
    """Choose the scorecard gate that matches the lane being checked.

    Primary Phase 7 / OP-CD paper lanes use the anchor-displacement first-read
    gate (30 ROI-complete settled observations). Phase 8 shadow lanes use the
    scorecard's promotion-review gate (20 ROI-complete shadow observations).
    """
    if portfolio_name == "phase8_frozen" or rules_path.name == "phase8_shadow_rules.json":
        return "phase8_promotion_review", FALLBACK_GATE_MINIMUMS["phase8_promotion_review"]
    return "anchor_displacement", FALLBACK_GATE_MINIMUMS["anchor_displacement"]


def resolve_gate_minimums(args: argparse.Namespace, portfolio_name: str, rules_path: Path) -> dict[str, Any]:
    scorecard_path = Path(getattr(args, "scorecard_json", SCORECARD_JSON))
    scorecard_gates = load_scorecard_gate_minimums(scorecard_path)
    requested_min_settled = getattr(args, "min_settled", None)
    requested_portfolio_review_settled = getattr(args, "portfolio_review_settled", None)

    default_gate_name, fallback_gate_value = default_first_read_gate(portfolio_name, rules_path)
    default_gate_key = (
        "phase8_promotion_review_min_roi_complete_settled_observations"
        if default_gate_name == "phase8_promotion_review"
        else "anchor_displacement_min_roi_complete_settled_observations"
    )
    default_min_settled = int(scorecard_gates.get(default_gate_key, fallback_gate_value))

    min_settled = requested_min_settled if requested_min_settled is not None else default_min_settled
    portfolio_review_settled = (
        requested_portfolio_review_settled
        if requested_portfolio_review_settled is not None
        else scorecard_gates["real_money_discussion_min_total_settled_observations_with_usable_roi"]
    )

    overrides: dict[str, dict[str, Any]] = {}
    if min_settled != default_min_settled:
        overrides["min_settled"] = {
            "scorecard_gate": default_gate_name,
            "scorecard_value": default_min_settled,
            "active_value": int(min_settled),
        }
    if portfolio_review_settled != scorecard_gates["real_money_discussion_min_total_settled_observations_with_usable_roi"]:
        overrides["portfolio_review_settled"] = {
            "scorecard_gate": "real_money_discussion",
            "scorecard_value": scorecard_gates["real_money_discussion_min_total_settled_observations_with_usable_roi"],
            "active_value": int(portfolio_review_settled),
        }

    return {
        **scorecard_gates,
        "active_first_read_gate": default_gate_name,
        "active_first_read_gate_key": default_gate_key,
        "active_min_settled": int(min_settled),
        "active_portfolio_review_settled": int(portfolio_review_settled),
        "cli_overrides": overrides,
        "alignment_read": (
            f"forward-check sample milestones are source-matched to forward_evidence_scorecard.json decision_gate_minimums using {default_gate_name} for this lane"
            if not overrides and scorecard_gates["source_loaded"] and not scorecard_gates.get("fallback_used")
            else "forward-check sample milestones are using explicit CLI/fallback values; do not treat fixture/custom thresholds as posture-changing gates"
        ),
    }


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def default_settlement_ledger_path(signals_path: Path) -> Path:
    name = signals_path.name
    if "signals" in name:
        return signals_path.with_name(name.replace("signals", "settlements"))
    return signals_path.with_name(f"{signals_path.stem}_settlements.csv")


def normalize_token(value: str | None) -> str:
    return str(value or "").strip().lower()


def parse_float(value: str | None) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def has_value(value: str | None) -> bool:
    return bool(str(value or "").strip())


def settled_ts_gap_reason(row: dict[str, str]) -> str:
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


def classify_outcome(row: dict[str, str]) -> str:
    outcome = normalize_token(row.get("outcome"))
    status = normalize_token(row.get("status"))

    if outcome in HIT_TOKENS:
        return "hit"
    if outcome in MISS_TOKENS:
        return "miss"
    if status in OPEN_STATUS_TOKENS or (not outcome and not status):
        return "open"
    if status in SETTLED_STATUS_TOKENS and not outcome:
        return "settled_unknown"
    return "open"


def settlement_roi_gap_reason(row: dict[str, str]) -> str:
    """Explain why a settled hit/miss row is not ROI-complete for forward gates."""
    if classify_outcome(row) not in {"hit", "miss"}:
        return ""

    actual_cost_text = row.get("actual_cost")
    actual_return_text = row.get("actual_return")
    actual_cost = parse_float(actual_cost_text)
    expected_cost = parse_float(row.get("expected_cost"))
    actual_return = parse_float(actual_return_text)
    actual_cost_is_malformed = has_value(actual_cost_text) and actual_cost is None
    actual_cost_is_blank = not has_value(actual_cost_text)

    reasons: list[str] = []
    if actual_return is None:
        reasons.append("missing actual_return")
    if actual_cost_is_malformed:
        reasons.append("malformed actual_cost")
    elif actual_cost is not None:
        if actual_cost <= 0:
            reasons.append("non-positive actual_cost")
    elif actual_cost_is_blank and expected_cost is None:
        reasons.append("missing actual_cost and expected_cost")
    elif actual_cost_is_blank and expected_cost is not None and expected_cost <= 0:
        reasons.append("non-positive expected_cost")

    timestamp_reason = settled_ts_gap_reason(row)
    if timestamp_reason:
        reasons.append(timestamp_reason)

    return "; ".join(reasons)


def merge_settlement_rows(signal_rows: list[dict[str, str]], settlement_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    settlement_by_key = {row.get("signal_key", ""): row for row in settlement_rows if row.get("signal_key")}
    merged: list[dict[str, str]] = []

    for signal in signal_rows:
        row = dict(signal)
        row["expected_cost"] = row.get("estimated_cost", "")
        settlement = settlement_by_key.get(row.get("signal_key", ""))
        if settlement:
            if settlement.get("settlement_status"):
                row["status"] = settlement.get("settlement_status", row.get("status", ""))
            if settlement.get("outcome"):
                row["outcome"] = settlement.get("outcome", row.get("outcome", ""))
            row["actual_cost"] = settlement.get("actual_cost", "")
            row["actual_return"] = settlement.get("actual_return", "")
            row["actual_profit"] = settlement.get("actual_profit", "")
            row["settled_ts"] = settlement.get("settled_ts", "")
            row["expected_cost"] = settlement.get("expected_cost", row.get("expected_cost", ""))
        merged.append(row)

    return merged


def pct(value: float) -> str:
    return f"{value:.2f}%"


def signed_pct(value: float) -> str:
    return f"{value:+.2f}%"


def read_rules(path: Path) -> tuple[str, str, list[str]]:
    name = path.name
    payload = load_json(path)
    rule_ids = [str(rule.get("rule_id", "")) for rule in payload.get("rules", []) if rule.get("rule_id")]
    portfolio_name, lane_label, default_rule_ids = PORTFOLIO_BASELINE_MAP.get(
        name,
        ("custom", name.replace("_", " ").replace(".json", ""), rule_ids),
    )
    return portfolio_name, lane_label, default_rule_ids or rule_ids


def load_frozen_baselines(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = load_csv_rows(path)
    rule_rows: dict[str, dict[str, Any]] = {}
    portfolio_rows: dict[str, dict[str, Any]] = {}

    for row in rows:
        if row.get("slice") != "holdout_2024_2025":
            continue
        parsed = {
            "portfolio": row.get("portfolio", ""),
            "name": row.get("name", ""),
            "races": int(float(row.get("races", 0) or 0)),
            "hits": int(float(row.get("hits", 0) or 0)),
            "wagered": float(row.get("wagered", 0) or 0),
            "returned": float(row.get("returned", 0) or 0),
            "profit": float(row.get("profit", 0) or 0),
            "roi": float(row.get("roi", 0) or 0),
            "hit_rate": float(row.get("hit_rate", 0) or 0),
        }
        if row.get("level") == "rule":
            rule_rows[parsed["name"]] = parsed
        elif row.get("level") == "portfolio":
            portfolio_rows[parsed["name"]] = parsed

    return rule_rows, portfolio_rows


def z_band(expected_rate: float, n: int) -> tuple[float, float, float] | None:
    if n <= 0:
        return None
    p = expected_rate / 100.0
    se = math.sqrt(max(p * (1.0 - p), 0.0) / n)
    se_pct = se * 100.0
    lo = max(0.0, expected_rate - 2.0 * se_pct)
    hi = min(100.0, expected_rate + 2.0 * se_pct)
    return lo, hi, se_pct


def assess_against_expected(
    observed_hit_rate: float,
    expected_hit_rate: float,
    settled_n: int,
    min_settled: int,
    roi_complete_n: int | None = None,
) -> tuple[str, str]:
    if settled_n <= 0:
        return "NO DATA", "No settled races yet, so this lane has no forward evidence one way or the other."

    band = z_band(expected_hit_rate, settled_n)
    if band is None:
        return "NO DATA", "No settled races yet, so this lane has no forward evidence one way or the other."
    lo, hi, se_pct = band

    gate_n = settled_n if roi_complete_n is None else max(int(roi_complete_n), 0)
    if gate_n < min_settled:
        return (
            "TOO EARLY",
            f"Only {gate_n} ROI-complete settled race(s) ({settled_n} outcome-settled). Expected noise band is {pct(lo)} to {pct(hi)} around the frozen hit-rate baseline.",
        )

    if observed_hit_rate < lo:
        return (
            "RUNNING COLD",
            f"Observed hit rate is below the approximate 2-sigma band ({pct(lo)} to {pct(hi)}).",
        )
    if observed_hit_rate > hi:
        return (
            "RUNNING HOT",
            f"Observed hit rate is above the approximate 2-sigma band ({pct(lo)} to {pct(hi)}).",
        )
    return (
        "WITHIN EXPECTED NOISE",
        f"Observed hit rate sits inside the approximate 2-sigma band ({pct(lo)} to {pct(hi)}), with ~{pct(se_pct)} standard error.",
    )


def summarize_signal_rows(rows: list[dict[str, str]]) -> dict[str, Any]:
    total = len(rows)
    settled = 0
    hits = 0
    misses = 0
    open_count = 0
    settled_unknown = 0
    settled_with_roi = 0
    roi_actual_cost_rows = 0
    roi_expected_cost_fallback_rows = 0
    roi_missing_return_rows = 0
    roi_missing_cost_rows = 0
    roi_malformed_actual_cost_rows = 0
    roi_non_positive_cost_rows = 0
    roi_missing_settled_ts_rows = 0
    roi_placeholder_settled_ts_rows = 0
    roi_malformed_settled_ts_rows = 0
    actual_cost_sum = 0.0
    actual_return_sum = 0.0
    actual_profit_sum = 0.0

    for row in rows:
        cls = classify_outcome(row)
        if cls == "hit":
            settled += 1
            hits += 1
        elif cls == "miss":
            settled += 1
            misses += 1
        elif cls == "settled_unknown":
            settled_unknown += 1
        else:
            open_count += 1

        if cls in {"hit", "miss"}:
            actual_cost_text = row.get("actual_cost")
            expected_cost_text = row.get("expected_cost")
            actual_return_text = row.get("actual_return")
            actual_cost = parse_float(actual_cost_text)
            expected_cost = parse_float(expected_cost_text)
            actual_return = parse_float(actual_return_text)
            actual_profit = parse_float(row.get("actual_profit"))

            actual_cost_source = "actual_cost" if actual_cost is not None else ""
            actual_cost_is_malformed = has_value(actual_cost_text) and actual_cost is None
            actual_cost_is_blank = not has_value(actual_cost_text)
            effective_cost = actual_cost
            if actual_cost is None and actual_cost_is_blank and expected_cost is not None:
                effective_cost = expected_cost
                actual_cost = expected_cost
                actual_cost_source = "expected_cost_fallback"

            if actual_return is None:
                roi_missing_return_rows += 1
            if actual_cost_is_malformed:
                roi_malformed_actual_cost_rows += 1
            elif effective_cost is None:
                roi_missing_cost_rows += 1
            elif effective_cost <= 0:
                roi_non_positive_cost_rows += 1

            timestamp_gap = settled_ts_gap_reason(row)
            if timestamp_gap == "missing settled_ts":
                roi_missing_settled_ts_rows += 1
            elif timestamp_gap == "placeholder settled_ts":
                roi_placeholder_settled_ts_rows += 1
            elif timestamp_gap == "malformed settled_ts":
                roi_malformed_settled_ts_rows += 1

            if actual_profit is None and actual_cost is not None and actual_return is not None:
                actual_profit = actual_return - actual_cost

            if effective_cost is not None and effective_cost > 0 and actual_return is not None and not timestamp_gap:
                settled_with_roi += 1
                if actual_cost_source == "actual_cost":
                    roi_actual_cost_rows += 1
                elif actual_cost_source == "expected_cost_fallback":
                    roi_expected_cost_fallback_rows += 1
                actual_cost_sum += effective_cost
                actual_return_sum += actual_return
                actual_profit_sum += actual_profit if actual_profit is not None else (actual_return - effective_cost)

    hit_rate = (hits / settled * 100.0) if settled else 0.0
    actual_roi = (actual_profit_sum / actual_cost_sum * 100.0) if actual_cost_sum else None
    return {
        "total": total,
        "settled": settled,
        "hits": hits,
        "misses": misses,
        "open": open_count,
        "settled_unknown": settled_unknown,
        "hit_rate": hit_rate,
        "settled_with_roi": settled_with_roi,
        "roi_actual_cost_rows": roi_actual_cost_rows,
        "roi_expected_cost_fallback_rows": roi_expected_cost_fallback_rows,
        "roi_missing_return_rows": roi_missing_return_rows,
        "roi_missing_cost_rows": roi_missing_cost_rows,
        "roi_malformed_actual_cost_rows": roi_malformed_actual_cost_rows,
        "roi_non_positive_cost_rows": roi_non_positive_cost_rows,
        "roi_missing_or_malformed_cost_rows": roi_missing_cost_rows + roi_malformed_actual_cost_rows,
        "roi_missing_settled_ts_rows": roi_missing_settled_ts_rows,
        "roi_placeholder_settled_ts_rows": roi_placeholder_settled_ts_rows,
        "roi_malformed_settled_ts_rows": roi_malformed_settled_ts_rows,
        "roi_settled_ts_gap_rows": roi_missing_settled_ts_rows + roi_placeholder_settled_ts_rows + roi_malformed_settled_ts_rows,
        "actual_cost_sum": actual_cost_sum,
        "actual_return_sum": actual_return_sum,
        "actual_profit_sum": actual_profit_sum,
        "actual_roi": actual_roi,
    }


def summarize_recommendation_rows(rows: list[dict[str, str]]) -> dict[str, int]:
    summary = {"total": len(rows), "bet": 0, "no_bet": 0, "error": 0, "open": 0}
    for row in rows:
        decision = normalize_token(row.get("decision"))
        if decision == "bet":
            summary["bet"] += 1
        elif decision == "no bet":
            summary["no_bet"] += 1
        elif decision == "error":
            summary["error"] += 1
        else:
            summary["open"] += 1
    return summary


def milestone_progress(current: int, threshold: int) -> dict[str, Any]:
    threshold = max(int(threshold), 0)
    current = max(int(current), 0)
    ready = threshold == 0 or current >= threshold
    remaining = max(threshold - current, 0)
    pct_complete = 100.0 if threshold == 0 else min(current / threshold * 100.0, 100.0)
    return {
        "threshold": threshold,
        "current": current,
        "ready": ready,
        "remaining": remaining,
        "pct_complete": pct_complete,
    }


def decision_gate_note(portfolio_observed: dict[str, Any], first_read: dict[str, Any], portfolio_review: dict[str, Any]) -> str:
    settled = int(portfolio_observed.get("settled", 0) or 0)
    settled_with_roi = int(portfolio_observed.get("settled_with_roi", 0) or 0)
    roi_missing = max(settled - settled_with_roi, 0)

    if settled <= 0:
        return (
            f"No strategy change: this is still pre-evidence with 0 settled races. "
            f"Collect {first_read['remaining']} more ROI-complete settled race(s) for the first statistical read "
            f"and {portfolio_review['remaining']} more for the broader portfolio review gate."
        )
    if not first_read["ready"]:
        return (
            f"No strategy change: {settled_with_roi} ROI-complete settled race(s) ({settled} outcome-settled) is below the first statistical-read gate "
            f"of {first_read['threshold']}; collect {first_read['remaining']} more before treating the hit-rate/ROI check as decision-grade."
        )
    if not portfolio_review["ready"]:
        return (
            f"First read only: {settled_with_roi}/{portfolio_review['threshold']} ROI-complete settled race(s) toward the broader portfolio review gate. "
            f"Do not change the anchor, promote shadow rules, or size real money from this surface until the {portfolio_review['threshold']}+ ROI-complete settled-review gate and settlement-quality checks are satisfied."
        )
    if roi_missing:
        return (
            f"Portfolio review count reached, but {roi_missing} outcome-settled race(s) still lack return/cost/timestamp coverage. "
            "Resolve ROI coverage and concentration/payout checks before changing the paper-trade hierarchy or considering real money."
        )
    return (
        "Portfolio review count reached with ROI-complete settled coverage. Still compare hit rate, flat-ticket ROI, concentration/payout risk, and the frozen OP/CD/shadow hierarchy before any rule-promotion or real-money decision."
    )


def decision_gate_caution(gate_minimums: dict[str, Any]) -> str:
    active_gate = str(gate_minimums.get("active_first_read_gate") or "").strip()
    if active_gate == "phase8_promotion_review":
        return (
            "Phase 8 shadow first-read status is a review floor, not a promotion entitlement; "
            "lane totals alone do not promote any Phase 8 pocket, scorecard tiers remain binding, "
            "and negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion."
        )
    return ""


def build_rule_summary(rule_id: str, rows: list[dict[str, str]], baseline: dict[str, Any] | None, min_settled: int) -> dict[str, Any]:
    observed = summarize_signal_rows(rows)
    expected_hit_rate = float(baseline["hit_rate"]) if baseline else None
    expected_roi = float(baseline["roi"]) if baseline else None
    expected_races = int(baseline["races"]) if baseline else None

    if baseline and observed["settled"] > 0:
        assessment, note = assess_against_expected(
            observed["hit_rate"],
            expected_hit_rate,
            observed["settled"],
            min_settled,
            observed["settled_with_roi"],
        )
        band = z_band(expected_hit_rate, observed["settled"])
        lo, hi, _ = band if band else (None, None, None)
    elif baseline:
        assessment, note = "NO DATA", "No settled races yet, so this lane has no forward evidence one way or the other."
        lo = hi = None
    else:
        assessment, note = "NO BASELINE", "Rule is missing from the frozen holdout summary."
        lo = hi = None

    observed_roi_missing = max(observed["settled"] - observed["settled_with_roi"], 0)
    if observed["settled"] and observed_roi_missing:
        note = (
            f"{note} ROI uses {observed['settled_with_roi']}/{observed['settled']} ROI-complete settled rows; "
            f"{observed_roi_missing} still missing return/cost/timestamp coverage."
        )

    return {
        "rule_id": rule_id,
        "observed_total": observed["total"],
        "observed_settled": observed["settled"],
        "observed_hits": observed["hits"],
        "observed_misses": observed["misses"],
        "observed_open": observed["open"],
        "observed_hit_rate": observed["hit_rate"],
        "observed_roi": observed["actual_roi"],
        "observed_settled_with_roi": observed["settled_with_roi"],
        "observed_roi_missing": observed_roi_missing,
        "expected_hit_rate": expected_hit_rate,
        "expected_roi": expected_roi,
        "expected_races": expected_races,
        "expected_band_lo": lo,
        "expected_band_hi": hi,
        "assessment": assessment,
        "note": note,
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    rules_path = Path(args.rules)
    signals_path = Path(args.signals_ledger)
    recommendation_path = Path(args.recommendation_ledger)
    settlement_path = Path(args.settlement_ledger) if args.settlement_ledger else default_settlement_ledger_path(signals_path)
    portfolio_name, lane_label, rule_ids = read_rules(rules_path)

    gate_minimums = resolve_gate_minimums(args, portfolio_name=portfolio_name, rules_path=rules_path)
    min_settled = gate_minimums["active_min_settled"]
    portfolio_review_settled = gate_minimums["active_portfolio_review_settled"]
    rule_baselines, portfolio_baselines = load_frozen_baselines(Path(args.frozen_eval))

    signal_rows = load_csv_rows(signals_path)
    recommendation_rows = load_csv_rows(recommendation_path)
    settlement_rows = load_csv_rows(settlement_path)
    merged_signal_rows = merge_settlement_rows(signal_rows, settlement_rows)
    rule_rows: dict[str, list[dict[str, str]]] = {rule_id: [] for rule_id in rule_ids}

    for row in merged_signal_rows:
        rid = row.get("rule_id", "")
        if rid in rule_rows:
            rule_rows[rid].append(row)

    portfolio_observed = summarize_signal_rows([row for row in merged_signal_rows if row.get("rule_id", "") in rule_rows])
    recommendation_summary = summarize_recommendation_rows(recommendation_rows)

    rule_summaries = [
        build_rule_summary(rule_id, rule_rows.get(rule_id, []), rule_baselines.get(rule_id), min_settled)
        for rule_id in rule_ids
    ]

    portfolio_baseline = portfolio_baselines.get(portfolio_name)
    if portfolio_baseline and portfolio_observed["settled"] > 0:
        portfolio_assessment, portfolio_note = assess_against_expected(
            portfolio_observed["hit_rate"],
            float(portfolio_baseline["hit_rate"]),
            portfolio_observed["settled"],
            min_settled,
            portfolio_observed["settled_with_roi"],
        )
        portfolio_band = z_band(float(portfolio_baseline["hit_rate"]), portfolio_observed["settled"])
        p_lo, p_hi, _ = portfolio_band if portfolio_band else (None, None, None)
    elif portfolio_baseline:
        portfolio_assessment, portfolio_note = "NO DATA", "No settled races yet, so this lane has no forward evidence one way or the other."
        p_lo = p_hi = None
    else:
        portfolio_assessment, portfolio_note = "NO BASELINE", "Lane is missing a frozen portfolio baseline."
        p_lo = p_hi = None

    sample_progress = {
        "first_read": milestone_progress(portfolio_observed["settled_with_roi"], min_settled),
        "portfolio_review": milestone_progress(portfolio_observed["settled_with_roi"], portfolio_review_settled),
    }
    decision_gate = decision_gate_note(
        portfolio_observed,
        sample_progress["first_read"],
        sample_progress["portfolio_review"],
    )

    return {
        "lane_label": lane_label,
        "portfolio_name": portfolio_name,
        "rules_path": str(rules_path),
        "signals_ledger": str(signals_path),
        "recommendation_ledger": str(recommendation_path),
        "settlement_ledger": str(settlement_path),
        "min_settled": min_settled,
        "portfolio_review_settled": portfolio_review_settled,
        "decision_gate_minimums": gate_minimums,
        "sample_progress": sample_progress,
        "decision_gate": decision_gate,
        "decision_gate_caution": decision_gate_caution(gate_minimums),
        "valid_evidence_scope": FORWARD_CHECK_VALID_EVIDENCE_SCOPE,
        "evidence_boundary": FORWARD_CHECK_EVIDENCE_BOUNDARY,
        "evidence_boundary_text": FORWARD_CHECK_BOUNDARY_TEXT,
        "portfolio_observed": portfolio_observed,
        "recommendation_summary": recommendation_summary,
        "portfolio_baseline": portfolio_baseline,
        "portfolio_assessment": portfolio_assessment,
        "portfolio_note": portfolio_note,
        "portfolio_band_lo": p_lo,
        "portfolio_band_hi": p_hi,
        "rule_summaries": rule_summaries,
        "roi_note": (
            "Observed ROI is shown when the settlement ledger has settled outcomes with usable return/cost values and actual ISO settled_ts values. "
            "The ROI coverage line shows how many settled races currently contribute to that number, "
            "and the ROI cost-source line separates explicit actual_cost rows from expected-cost fallback rows. "
            "If ROI is still n/a, fill in settlement rows with outcome plus actual_return, optionally actual_cost, and an actual settled_ts; "
            "malformed actual_cost or settled_ts values are treated as settlement-quality gaps rather than silently falling back."
        ),
    }


def render_md(payload: dict[str, Any]) -> str:
    po = payload["portfolio_observed"]
    pb = payload["portfolio_baseline"]
    rs = payload["recommendation_summary"]

    sample_progress = payload["sample_progress"]
    first_read = sample_progress["first_read"]
    portfolio_review = sample_progress["portfolio_review"]

    lines = [
        "# Paper-Trade Forward Check",
        "",
        f"Lane: **{payload['lane_label']}**",
        "",
        "## Decision-Gate Source",
        "",
        f"- Source: `{payload['decision_gate_minimums']['source_path']}`; loaded={payload['decision_gate_minimums']['source_loaded']}; fallback_used={payload['decision_gate_minimums']['fallback_used']}.",
        f"- Scorecard `decision_gate_minimums`: anchor_displacement={payload['decision_gate_minimums']['anchor_displacement_min_roi_complete_settled_observations']} ROI-complete same-candidate settled observations; phase8_promotion_review={payload['decision_gate_minimums']['phase8_promotion_review_min_roi_complete_settled_observations']} ROI-complete shadow observations; real_money_discussion={payload['decision_gate_minimums']['real_money_discussion_min_total_settled_observations_with_usable_roi']} total settled observations with usable ROI; real_money_requires={'; '.join(payload['decision_gate_minimums']['real_money_discussion_also_requires'])}.",
        f"- Active forward-check gates: first_read_gate={payload['decision_gate_minimums']['active_first_read_gate']}; min_settled={payload['min_settled']}; portfolio_review_settled={payload['portfolio_review_settled']}. {payload['decision_gate_minimums']['alignment_read']}.",
        "- These thresholds are posture-gate metadata for ROI-read routing only; they are not live-profitability, promotion, anchor-change, or real-money evidence.",
        *( [f"- Decision-gate caution: {payload['decision_gate_caution']}"] if payload.get("decision_gate_caution") else [] ),
        "",
        "## Evidence Boundary",
        "",
        f"- `valid_evidence_scope={payload['valid_evidence_scope']}`",
        f"- Valid use: {payload['valid_evidence_scope']}.",
        f"- Boundary: {payload['evidence_boundary_text']}.",
        "- Non-goals: do not treat clean forward-check rebuilds, scorecard-gate visibility, open rows, or sub-threshold hot/cold reads as rule-change permission, promotion support, live-profitability proof, or real-money support.",
        "",
        "## Portfolio Summary",
        "",
        f"- Assessment: **{payload['portfolio_assessment']}**",
        f"- Observed signals: `{po['total']}` total, `{po['settled']}` settled, `{po['open']}` still open",
        f"- Observed hit rate: `{pct(po['hit_rate'])}` ({po['hits']} hit / {po['settled']} settled)" if po["settled"] else "- Observed hit rate: `n/a` (no settled races yet)",
        (
            f"- Observed flat-ticket ROI: `{signed_pct(float(po['actual_roi']))}` on `{po['settled_with_roi']}` ROI-complete settled race(s) with return/cost/timestamp coverage"
            if po.get("actual_roi") is not None else
            "- Observed flat-ticket ROI: `n/a` (no settled return values yet)"
        ),
        (
            f"- ROI coverage: `{po['settled_with_roi']}/{po['settled']}` settled race(s) are ROI-complete (`{max(po['settled'] - po['settled_with_roi'], 0)}` still missing return/cost/timestamp coverage)"
            if po['settled'] else
            "- ROI coverage: `0/0` settled race(s) are ROI-complete (no settled outcomes yet)"
        ),
        f"- ROI cost source: `{po['roi_actual_cost_rows']}` actual-cost row(s), `{po['roi_expected_cost_fallback_rows']}` expected-cost fallback row(s), `{po['roi_missing_or_malformed_cost_rows']}` missing/malformed cost row(s), `{po['roi_non_positive_cost_rows']}` non-positive cost row(s)",
        f"- ROI return gaps: `{po['roi_missing_return_rows']}` settled outcome row(s) missing return values; malformed actual-cost rows: `{po['roi_malformed_actual_cost_rows']}`",
        f"- ROI timestamp gaps: `{po['roi_settled_ts_gap_rows']}` settled outcome row(s) missing usable settled_ts (`{po['roi_missing_settled_ts_rows']}` missing, `{po['roi_placeholder_settled_ts_rows']}` placeholder, `{po['roi_malformed_settled_ts_rows']}` malformed)",
        (
            f"- Sample progress: `{first_read['current']}/{first_read['threshold']}` ROI-complete settled toward the first statistical read ({first_read['remaining']} more needed)"
            if not first_read["ready"] else
            f"- Sample progress: `{first_read['current']}/{first_read['threshold']}` ROI-complete settled; first statistical read threshold reached"
        ),
        (
            f"- Broader review progress: `{portfolio_review['current']}/{portfolio_review['threshold']}` ROI-complete settled toward the portfolio review gate ({portfolio_review['remaining']} more needed)"
            if not portfolio_review["ready"] else
            f"- Broader review progress: `{portfolio_review['current']}/{portfolio_review['threshold']}` ROI-complete settled; portfolio review gate reached"
        ),
        f"- Recommendation flow so far: `{rs['total']}` row(s), `{rs['bet']}` BET, `{rs['no_bet']}` NO BET, `{rs['error']}` ERROR",
        f"- Decision gate: {payload['decision_gate']}",
    ]

    if po["settled_unknown"]:
        lines.append(
            f"- Settlement data gap: `{po['settled_unknown']}` row(s) are marked settled but still missing an outcome, so they are excluded from hit-rate and ROI checks"
        )

    if pb:
        lines.extend([
            f"- Frozen baseline hit rate: `{pct(float(pb['hit_rate']))}` on `{int(pb['races'])}` holdout races",
            f"- Frozen baseline ROI: `{signed_pct(float(pb['roi']))}`",
        ])
        if payload["portfolio_band_lo"] is not None:
            lines.append(
                f"- Approximate 2-sigma hit-rate band at current sample: `{pct(float(payload['portfolio_band_lo']))}` to `{pct(float(payload['portfolio_band_hi']))}`"
            )
    else:
        lines.append("- Frozen baseline: `missing`")

    lines.extend([
        f"- Read: {payload['portfolio_note']}",
        f"- Settlement ledger: `{payload['settlement_ledger']}`",
        "",
        "## Rule-Level Check",
        "",
        "| Rule | Settled | Open | Observed Hit Rate | Observed ROI | Frozen Hit Rate | Frozen ROI | Check | Note |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ])

    for row in payload["rule_summaries"]:
        observed_hr = pct(float(row["observed_hit_rate"])) if row["observed_settled"] else "n/a"
        observed_roi = signed_pct(float(row["observed_roi"])) if row["observed_roi"] is not None else "n/a"
        expected_hr = pct(float(row["expected_hit_rate"])) if row["expected_hit_rate"] is not None else "n/a"
        expected_roi = signed_pct(float(row["expected_roi"])) if row["expected_roi"] is not None else "n/a"
        lines.append(
            f"| {row['rule_id']} | {int(row['observed_settled'])} | {int(row['observed_open'])} | {observed_hr} | {observed_roi} | {expected_hr} | {expected_roi} | {row['assessment']} | {row['note']} |"
        )

    lines.extend([
        "",
        "## Notes",
        "",
        f"- {payload['roi_note']}",
        "- Rows marked `settled` with a blank outcome are treated as incomplete settlement data until the outcome is filled.",
        f"- Decision-grade first-read threshold in this checker: `{payload['min_settled']}` ROI-complete settled races from `{payload['decision_gate_minimums']['active_first_read_gate']}`.",
        "- Accepted settled outcomes are simple values like `HIT` and `MISS`.",
        "- Blank settlement rows or `settlement_status=open` are treated as still pending.",
        "- If `actual_cost` is blank, the checker falls back to the scanner's estimated ticket cost for flat-ticket ROI and reports how many ROI rows used that fallback.",
        "- If `actual_cost` is present but malformed, the row is treated as a settlement-quality gap rather than silently falling back to `expected_cost`.",
        "- Missing, placeholder, or malformed `settled_ts` values are settlement-quality gaps and do not count toward ROI-complete sample milestones.",
        "",
    ])

    return "\n".join(lines)


def render_text(payload: dict[str, Any]) -> str:
    po = payload["portfolio_observed"]
    pb = payload["portfolio_baseline"]
    sample_progress = payload["sample_progress"]
    first_read = sample_progress["first_read"]
    portfolio_review = sample_progress["portfolio_review"]

    pieces = [
        f"{payload['lane_label']}: {payload['portfolio_assessment']}",
        (
            "gate source "
            f"{payload['decision_gate_minimums']['source_path']} decision_gate_minimums "
            f"loaded={payload['decision_gate_minimums']['source_loaded']} "
            f"anchor_displacement={payload['decision_gate_minimums']['anchor_displacement_min_roi_complete_settled_observations']} "
            f"phase8_promotion_review={payload['decision_gate_minimums']['phase8_promotion_review_min_roi_complete_settled_observations']} "
            f"real_money_discussion={payload['decision_gate_minimums']['real_money_discussion_min_total_settled_observations_with_usable_roi']} "
            f"real_money_no_baq_as_bel_required={payload['decision_gate_minimums']['real_money_no_baq_as_bel_required']} "
            f"active_first_read_gate={payload['decision_gate_minimums']['active_first_read_gate']}"
        ),
        f"{po['settled']} settled / {po['open']} open",
        f"sample progress {first_read['current']}/{first_read['threshold']} ROI-complete",
        f"portfolio review progress {portfolio_review['current']}/{portfolio_review['threshold']} ROI-complete",
    ]
    if payload.get("decision_gate_caution"):
        pieces.append(f"decision-gate caution {payload['decision_gate_caution']}")
    pieces.append(f"valid_evidence_scope={payload['valid_evidence_scope']}")
    pieces.append(f"evidence boundary {payload['evidence_boundary_text']}")
    if po["settled_unknown"]:
        pieces.append(f"{po['settled_unknown']} settled row(s) missing outcome")
    if po["settled"]:
        pieces.append(f"observed hit rate {pct(po['hit_rate'])}")
    pieces.append(f"ROI coverage {po['settled_with_roi']}/{po['settled']} ROI-complete")
    pieces.append(
        f"ROI cost source actual={po['roi_actual_cost_rows']} "
        f"expected_fallback={po['roi_expected_cost_fallback_rows']} "
        f"missing_or_malformed_cost={po['roi_missing_or_malformed_cost_rows']} "
        f"non_positive_cost={po['roi_non_positive_cost_rows']} "
        f"missing_return={po['roi_missing_return_rows']} "
        f"timestamp_gaps={po['roi_settled_ts_gap_rows']} "
        f"missing_ts={po['roi_missing_settled_ts_rows']} "
        f"placeholder_ts={po['roi_placeholder_settled_ts_rows']} "
        f"malformed_ts={po['roi_malformed_settled_ts_rows']}"
    )
    if po.get("actual_roi") is not None:
        pieces.append(f"observed ROI {signed_pct(float(po['actual_roi']))} on {po['settled_with_roi']}/{po['settled']} ROI-complete settled races")
    elif po["settled"]:
        pieces.append("observed ROI n/a")
    if pb:
        pieces.append(f"baseline hit rate {pct(float(pb['hit_rate']))}")
    pieces.append(f"decision gate {payload['decision_gate']}")
    pieces.append(payload["portfolio_note"])
    return ", ".join(pieces) + "\n"


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    payload = build_payload(args)

    if args.format == "json":
        output = json.dumps(payload, indent=2) + "\n"
    elif args.format == "text":
        output = render_text(payload)
    else:
        output = render_md(payload) + "\n"

    if args.output:
        write_output(Path(args.output), output)
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
