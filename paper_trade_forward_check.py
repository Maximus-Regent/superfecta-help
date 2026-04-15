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
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
DEFAULT_SIGNALS_LEDGER = BASE / "paper_trades" / "phase7_current_paper_paper_trade_signals.csv"
DEFAULT_RECOMMENDATION_LEDGER = BASE / "paper_trades" / "phase7_current_paper_paper_trade_recommendations.csv"
DEFAULT_RULES = BASE / "phase7_current_paper_rules.json"
DEFAULT_FROZEN_EVAL = BASE / "frozen_portfolio_eval_summary.csv"
DEFAULT_OUTPUT = BASE / "out" / "paper_trade_forward_check.md"

PORTFOLIO_BASELINE_MAP = {
    "op_anchor_rules.json": ("phase7_live", "OP anchor paper lane", ["OP_DURABLE_K7"]),
    "phase7_current_paper_rules.json": ("phase7_live", "Phase 7 current paper lane", ["OP_DURABLE_K7", "CD_CORE_K8"]),
    "phase7_live_rules.json": ("phase7_live", "Phase 7 live lane", ["BEL_BROAD1_K7", "OP_DURABLE_K7", "CD_CORE_K8"]),
    "phase8_shadow_rules.json": ("phase8_frozen", "Phase 8 shadow lane", ["OP_REFINED_K7", "AQU_K9", "SA_K9", "KEE_K9", "CD_REFINED_K9", "DMR_FALL_K7"]),
}

HIT_TOKENS = {"hit", "won", "win", "winner", "cash", "cashed", "1", "true", "yes", "y"}
MISS_TOKENS = {"miss", "lost", "lose", "loss", "0", "false", "no", "n", "x"}
SETTLED_STATUS_TOKENS = {"settled", "closed", "complete", "completed", "done"}
OPEN_STATUS_TOKENS = {"open", "pending", "unsettled", "todo"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compare settled paper-trade observations against frozen baselines")
    p.add_argument("--signals-ledger", default=str(DEFAULT_SIGNALS_LEDGER), help="Signal ledger CSV path")
    p.add_argument("--recommendation-ledger", default=str(DEFAULT_RECOMMENDATION_LEDGER), help="Recommendation ledger CSV path")
    p.add_argument("--settlement-ledger", help="Optional settlement ledger CSV path; defaults from --signals-ledger")
    p.add_argument("--rules", default=str(DEFAULT_RULES), help="Rules JSON path for the lane being checked")
    p.add_argument("--frozen-eval", default=str(DEFAULT_FROZEN_EVAL), help="Frozen evaluation summary CSV path")
    p.add_argument("--min-settled", type=int, default=30, help="Minimum settled races before treating the check as decision-grade")
    p.add_argument("--format", choices=["text", "md", "json"], default="md", help="Output format")
    p.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Optional output path")
    return p.parse_args()


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


def assess_against_expected(observed_hit_rate: float, expected_hit_rate: float, settled_n: int, min_settled: int) -> tuple[str, str]:
    if settled_n <= 0:
        return "NO DATA", "No settled races yet."

    band = z_band(expected_hit_rate, settled_n)
    if band is None:
        return "NO DATA", "No settled races yet."
    lo, hi, se_pct = band

    if settled_n < min_settled:
        return (
            "TOO EARLY",
            f"Only {settled_n} settled race(s). Expected noise band is {pct(lo)} to {pct(hi)} around the frozen hit-rate baseline.",
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
            actual_cost = parse_float(row.get("actual_cost"))
            expected_cost = parse_float(row.get("expected_cost"))
            actual_return = parse_float(row.get("actual_return"))
            actual_profit = parse_float(row.get("actual_profit"))

            if actual_cost is None:
                actual_cost = expected_cost
            if actual_profit is None and actual_cost is not None and actual_return is not None:
                actual_profit = actual_return - actual_cost

            if actual_cost is not None and actual_return is not None:
                settled_with_roi += 1
                actual_cost_sum += actual_cost
                actual_return_sum += actual_return
                actual_profit_sum += actual_profit if actual_profit is not None else (actual_return - actual_cost)

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


def build_rule_summary(rule_id: str, rows: list[dict[str, str]], baseline: dict[str, Any] | None, min_settled: int) -> dict[str, Any]:
    observed = summarize_signal_rows(rows)
    expected_hit_rate = float(baseline["hit_rate"]) if baseline else None
    expected_roi = float(baseline["roi"]) if baseline else None
    expected_races = int(baseline["races"]) if baseline else None

    if baseline and observed["settled"] > 0:
        assessment, note = assess_against_expected(observed["hit_rate"], expected_hit_rate, observed["settled"], min_settled)
        band = z_band(expected_hit_rate, observed["settled"])
        lo, hi, _ = band if band else (None, None, None)
    elif baseline:
        assessment, note = "NO DATA", "No settled races yet."
        lo = hi = None
    else:
        assessment, note = "NO BASELINE", "Rule is missing from the frozen holdout summary."
        lo = hi = None

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
        build_rule_summary(rule_id, rule_rows.get(rule_id, []), rule_baselines.get(rule_id), args.min_settled)
        for rule_id in rule_ids
    ]

    portfolio_baseline = portfolio_baselines.get(portfolio_name)
    if portfolio_baseline and portfolio_observed["settled"] > 0:
        portfolio_assessment, portfolio_note = assess_against_expected(
            portfolio_observed["hit_rate"],
            float(portfolio_baseline["hit_rate"]),
            portfolio_observed["settled"],
            args.min_settled,
        )
        portfolio_band = z_band(float(portfolio_baseline["hit_rate"]), portfolio_observed["settled"])
        p_lo, p_hi, _ = portfolio_band if portfolio_band else (None, None, None)
    elif portfolio_baseline:
        portfolio_assessment, portfolio_note = "NO DATA", "No settled races yet."
        p_lo = p_hi = None
    else:
        portfolio_assessment, portfolio_note = "NO BASELINE", "Lane is missing a frozen portfolio baseline."
        p_lo = p_hi = None

    return {
        "lane_label": lane_label,
        "portfolio_name": portfolio_name,
        "rules_path": str(rules_path),
        "signals_ledger": str(signals_path),
        "recommendation_ledger": str(recommendation_path),
        "settlement_ledger": str(settlement_path),
        "min_settled": args.min_settled,
        "portfolio_observed": portfolio_observed,
        "recommendation_summary": recommendation_summary,
        "portfolio_baseline": portfolio_baseline,
        "portfolio_assessment": portfolio_assessment,
        "portfolio_note": portfolio_note,
        "portfolio_band_lo": p_lo,
        "portfolio_band_hi": p_hi,
        "rule_summaries": rule_summaries,
        "roi_note": (
            "Observed ROI is shown when the settlement ledger has settled return/cost values. "
            "If ROI is still n/a, fill in settlement rows with outcome plus actual_return and optionally actual_cost."
        ),
    }


def render_md(payload: dict[str, Any]) -> str:
    po = payload["portfolio_observed"]
    pb = payload["portfolio_baseline"]
    rs = payload["recommendation_summary"]

    lines = [
        "# Paper-Trade Forward Check",
        "",
        f"Lane: **{payload['lane_label']}**",
        "",
        "## Portfolio Summary",
        "",
        f"- Assessment: **{payload['portfolio_assessment']}**",
        f"- Observed signals: `{po['total']}` total, `{po['settled']}` settled, `{po['open']}` still open",
        f"- Observed hit rate: `{pct(po['hit_rate'])}` ({po['hits']} hit / {po['settled']} settled)" if po["settled"] else "- Observed hit rate: `n/a` (no settled races yet)",
        (
            f"- Observed flat-ticket ROI: `{signed_pct(float(po['actual_roi']))}` on `{po['settled_with_roi']}` settled race(s) with return values"
            if po.get("actual_roi") is not None else
            "- Observed flat-ticket ROI: `n/a` (no settled return values yet)"
        ),
        f"- Recommendation flow so far: `{rs['total']}` row(s), `{rs['bet']}` BET, `{rs['no_bet']}` NO BET, `{rs['error']}` ERROR",
    ]

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
        f"- Decision-grade threshold in this checker: `{payload['min_settled']}` settled races.",
        "- Accepted settled outcomes are simple values like `HIT` and `MISS`.",
        "- Blank settlement rows or `settlement_status=open` are treated as still pending.",
        "- If `actual_cost` is blank, the checker falls back to the scanner's estimated ticket cost for flat-ticket ROI.",
        "",
    ])

    return "\n".join(lines)


def render_text(payload: dict[str, Any]) -> str:
    po = payload["portfolio_observed"]
    pb = payload["portfolio_baseline"]
    pieces = [
        f"{payload['lane_label']}: {payload['portfolio_assessment']}",
        f"{po['settled']} settled / {po['open']} open",
    ]
    if po["settled"]:
        pieces.append(f"observed hit rate {pct(po['hit_rate'])}")
    if po.get("actual_roi") is not None:
        pieces.append(f"observed ROI {signed_pct(float(po['actual_roi']))}")
    if pb:
        pieces.append(f"baseline hit rate {pct(float(pb['hit_rate']))}")
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
