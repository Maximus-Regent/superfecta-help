#!/usr/bin/env python3
"""
Expected-value ticket selector for superfecta model outputs.

Consumes combo-level prediction CSVs from:
  - NYRA/model_main.py
  - XGBoost/predict_single_race.py

The engine moves beyond raw payout prediction by:
  1. Converting model outputs into conservative EV estimates
  2. Enforcing a bet / no-bet rule with minimum edge thresholds
  3. Ranking tickets by expected profit under bankroll-aware sizing
  4. Applying simple race-level and ticket-level risk caps

Assumptions:
  - predicted_payout is normalized to a $1 payout, matching the training code.
  - Payouts scale linearly with stake size.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_PROB_COL = "jointProb"
DEFAULT_PAYOUT_COL = "predicted_payout"
DEFAULT_PAYOUT_UNIT = 1.0
DEFAULT_TICKET_INCREMENT = 0.10
DEFAULT_PAYOUT_HAIRCUT = 0.75
DEFAULT_BANKROLL = 500.0
DEFAULT_KELLY_FRACTION = 0.25
DEFAULT_MIN_EV_ROI = 0.15
DEFAULT_MIN_PROB = 0.0005
DEFAULT_MAX_TICKETS = 4
DEFAULT_MAX_RACE_RISK = 0.02
DEFAULT_MAX_TICKET_RISK = 0.0075
EV_TICKET_ENGINE_VALID_EVIDENCE_SCOPE = "ev_ticket_stake_sizing_metadata_only"
EV_TICKET_ENGINE_BOUNDARY_TEXT = (
    "EV ticket-engine output is source-layer paper stake-sizing metadata only; it is not a current-day "
    "scanner result, not a live paper-trade ledger, not settled ROI evidence, not promotion readiness, "
    "not live-profitability evidence, and not real-money support. BET plans remain hypothetical paper "
    "sizing candidates until the recommender, logger, settlement sync, actual result, return, cost, "
    "settled_ts, and later audit or forward-check review are complete."
)
EV_TICKET_ENGINE_EVIDENCE_BOUNDARY = {
    "artifact_role": "EV ticket-engine stake plan",
    "valid_use": "source-layer paper stake-sizing metadata before recommendation, ledger, and settlement review",
    "not_current_day_scanner_result": True,
    "not_live_paper_trade_ledger": True,
    "not_settled_roi_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "requires_recommender_context_before_paper_plan": True,
    "requires_logger_append_before_ledger_row": True,
    "requires_settlement_sync_before_open_settlement_row": True,
    "requires_actual_result_return_cost_and_settled_ts_before_roi_complete": True,
    "requires_later_audit_or_forward_check_review_before_sample_gate_use": True,
}


@dataclass
class EngineConfig:
    bankroll: float = DEFAULT_BANKROLL
    payout_unit: float = DEFAULT_PAYOUT_UNIT
    ticket_increment: float = DEFAULT_TICKET_INCREMENT
    payout_haircut: float = DEFAULT_PAYOUT_HAIRCUT
    kelly_fraction: float = DEFAULT_KELLY_FRACTION
    min_ev_roi: float = DEFAULT_MIN_EV_ROI
    min_prob: float = DEFAULT_MIN_PROB
    max_tickets: int = DEFAULT_MAX_TICKETS
    max_race_risk: float = DEFAULT_MAX_RACE_RISK
    max_ticket_risk: float = DEFAULT_MAX_TICKET_RISK
    prob_col: str = DEFAULT_PROB_COL
    payout_col: str = DEFAULT_PAYOUT_COL
    race_label: str = ""


@dataclass
class RacePlan:
    decision: str
    reason: str
    race_label: str
    tickets_considered: int
    tickets_selected: int
    bankroll: float
    race_risk_budget: float
    total_stake: float
    total_expected_return: float
    total_expected_profit: float
    portfolio_expected_roi_pct: float
    tickets: list[dict[str, Any]]
    valid_evidence_scope: str = EV_TICKET_ENGINE_VALID_EVIDENCE_SCOPE
    evidence_boundary_text: str = EV_TICKET_ENGINE_BOUNDARY_TEXT
    evidence_boundary: dict[str, Any] = field(default_factory=lambda: dict(EV_TICKET_ENGINE_EVIDENCE_BOUNDARY))


def _round_down(value: float, increment: float) -> float:
    if increment <= 0:
        return round(float(value), 10)
    return round(np.floor(value / increment) * increment, 10)


def _clip_series(series: pd.Series, lower: float | None = None, upper: float | None = None) -> pd.Series:
    out = series.astype(float)
    if lower is not None:
        out = out.clip(lower=lower)
    if upper is not None:
        out = out.clip(upper=upper)
    return out


def add_ev_metrics(
    df: pd.DataFrame,
    prob_col: str = DEFAULT_PROB_COL,
    payout_col: str = DEFAULT_PAYOUT_COL,
    payout_unit: float = DEFAULT_PAYOUT_UNIT,
    payout_haircut: float = DEFAULT_PAYOUT_HAIRCUT,
) -> pd.DataFrame:
    """Add EV-related columns to a prediction DataFrame."""
    if prob_col not in df.columns:
        raise KeyError(f"Missing probability column: {prob_col}")
    if payout_col not in df.columns:
        raise KeyError(f"Missing payout column: {payout_col}")
    if payout_unit <= 0:
        raise ValueError("payout_unit must be > 0")

    out = df.copy()
    prob = _clip_series(out[prob_col], 0.0, 1.0)
    raw_payout = _clip_series(out[payout_col], 0.0, None)
    adj_payout = raw_payout * float(payout_haircut)

    gross_multiple = adj_payout / float(payout_unit)
    net_multiple = gross_multiple - 1.0
    expected_return_multiple = prob * gross_multiple
    ev_profit_multiple = expected_return_multiple - 1.0

    # Avoid exploding Kelly fractions for effectively break-even tickets.
    kelly_eligible = gross_multiple >= 1.05
    safe_net_multiple = net_multiple.where(kelly_eligible, np.nan)
    full_kelly_frac = ((prob * safe_net_multiple) - (1.0 - prob)) / safe_net_multiple
    full_kelly_frac = (
        full_kelly_frac
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
        .clip(lower=0.0)
    )

    out["adj_predicted_payout"] = adj_payout
    out["expected_return_1"] = expected_return_multiple
    out["ev_profit_1"] = ev_profit_multiple
    out["ev_roi_pct"] = ev_profit_multiple * 100.0
    out["full_kelly_frac"] = full_kelly_frac
    out["value_rank"] = (
        out["ev_profit_1"].rank(method="first", ascending=False).astype(int)
    )
    return out


def build_race_plan(df: pd.DataFrame, config: EngineConfig) -> RacePlan:
    enriched = add_ev_metrics(
        df,
        prob_col=config.prob_col,
        payout_col=config.payout_col,
        payout_unit=config.payout_unit,
        payout_haircut=config.payout_haircut,
    )

    if enriched.empty:
        return RacePlan(
            decision="NO BET",
            reason="No rows were available in the prediction file.",
            race_label=config.race_label or "race",
            tickets_considered=0,
            tickets_selected=0,
            bankroll=config.bankroll,
            race_risk_budget=round(config.bankroll * config.max_race_risk, 2),
            total_stake=0.0,
            total_expected_return=0.0,
            total_expected_profit=0.0,
            portfolio_expected_roi_pct=0.0,
            tickets=[],
        )

    enriched = enriched.sort_values(
        ["ev_profit_1", config.prob_col], ascending=[False, False]
    ).reset_index(drop=True)

    eligible = enriched[
        (enriched[config.prob_col] >= config.min_prob)
        & (enriched["ev_profit_1"] >= config.min_ev_roi)
        & (enriched["full_kelly_frac"] > 0)
    ].copy()

    race_risk_budget = round(config.bankroll * config.max_race_risk, 2)
    ticket_risk_cap = config.bankroll * config.max_ticket_risk

    if eligible.empty:
        best = enriched.iloc[0]
        if float(best["ev_profit_1"]) <= 0:
            reason = "Best ticket is still negative EV after the conservative payout haircut."
        elif float(best[config.prob_col]) < config.min_prob:
            reason = "Best ticket is too low-probability for the current filters."
        else:
            reason = "No ticket cleared the minimum EV / Kelly thresholds."
        return RacePlan(
            decision="NO BET",
            reason=reason,
            race_label=config.race_label or "race",
            tickets_considered=len(enriched),
            tickets_selected=0,
            bankroll=config.bankroll,
            race_risk_budget=race_risk_budget,
            total_stake=0.0,
            total_expected_return=0.0,
            total_expected_profit=0.0,
            portfolio_expected_roi_pct=0.0,
            tickets=[],
        )

    eligible["raw_kelly_stake"] = config.bankroll * config.kelly_fraction * eligible["full_kelly_frac"]
    eligible["target_stake"] = eligible["raw_kelly_stake"].clip(upper=ticket_risk_cap)
    eligible["expected_profit_target"] = eligible["target_stake"] * eligible["ev_profit_1"]

    selected = eligible.sort_values(
        ["expected_profit_target", config.prob_col], ascending=[False, False]
    ).head(config.max_tickets).copy()

    target_total = float(selected["target_stake"].sum())
    if target_total <= 0:
        return RacePlan(
            decision="NO BET",
            reason="Kelly sizing produced no positive dollar stake above zero.",
            race_label=config.race_label or "race",
            tickets_considered=len(enriched),
            tickets_selected=0,
            bankroll=config.bankroll,
            race_risk_budget=race_risk_budget,
            total_stake=0.0,
            total_expected_return=0.0,
            total_expected_profit=0.0,
            portfolio_expected_roi_pct=0.0,
            tickets=[],
        )

    scale = min(1.0, race_risk_budget / target_total) if target_total > 0 else 0.0
    selected["recommended_stake"] = selected["target_stake"] * scale
    selected["recommended_stake"] = selected["recommended_stake"].map(
        lambda x: _round_down(float(x), config.ticket_increment)
    )
    selected = selected[selected["recommended_stake"] >= config.ticket_increment].copy()

    if selected.empty:
        return RacePlan(
            decision="NO BET",
            reason="Risk caps pushed every recommended stake below the minimum ticket increment.",
            race_label=config.race_label or "race",
            tickets_considered=len(enriched),
            tickets_selected=0,
            bankroll=config.bankroll,
            race_risk_budget=race_risk_budget,
            total_stake=0.0,
            total_expected_return=0.0,
            total_expected_profit=0.0,
            portfolio_expected_roi_pct=0.0,
            tickets=[],
        )

    selected["expected_return_dollars"] = selected["recommended_stake"] * selected["expected_return_1"]
    selected["expected_profit_dollars"] = selected["recommended_stake"] * selected["ev_profit_1"]
    selected["hit_rate_pct"] = selected[config.prob_col] * 100.0

    total_stake = round(float(selected["recommended_stake"].sum()), 2)
    total_expected_return = round(float(selected["expected_return_dollars"].sum()), 2)
    total_expected_profit = round(float(selected["expected_profit_dollars"].sum()), 2)
    portfolio_roi_pct = round((total_expected_profit / total_stake) * 100.0, 2) if total_stake > 0 else 0.0

    keep_cols = [
        "combo",
        config.prob_col,
        config.payout_col,
        "adj_predicted_payout",
        "expected_return_1",
        "ev_profit_1",
        "ev_roi_pct",
        "full_kelly_frac",
        "recommended_stake",
        "expected_return_dollars",
        "expected_profit_dollars",
        "value_rank",
        "rank",
    ]
    existing_cols = [c for c in keep_cols if c in selected.columns]
    ticket_rows = selected[existing_cols].copy()

    rename_map = {
        config.prob_col: "joint_prob",
        config.payout_col: "predicted_payout",
    }
    ticket_rows = ticket_rows.rename(columns=rename_map)

    for col in ticket_rows.columns:
        if pd.api.types.is_numeric_dtype(ticket_rows[col]):
            ticket_rows[col] = ticket_rows[col].map(
                lambda x: round(float(x), 6) if pd.notna(x) else x
            )
    ticket_rows["valid_evidence_scope"] = EV_TICKET_ENGINE_VALID_EVIDENCE_SCOPE
    ticket_rows["evidence_boundary_text"] = EV_TICKET_ENGINE_BOUNDARY_TEXT

    return RacePlan(
        decision="BET",
        reason="At least one ticket cleared the EV filters and fit inside bankroll caps.",
        race_label=config.race_label or "race",
        tickets_considered=len(enriched),
        tickets_selected=len(ticket_rows),
        bankroll=config.bankroll,
        race_risk_budget=race_risk_budget,
        total_stake=total_stake,
        total_expected_return=total_expected_return,
        total_expected_profit=total_expected_profit,
        portfolio_expected_roi_pct=portfolio_roi_pct,
        tickets=ticket_rows.to_dict(orient="records"),
    )


def format_plan(plan: RacePlan) -> str:
    lines = [
        f"EV ticket plan for {plan.race_label}",
        f"Decision: {plan.decision}",
        f"Reason: {plan.reason}",
        f"valid_evidence_scope={plan.valid_evidence_scope}",
        f"Evidence boundary: {plan.evidence_boundary_text}",
        f"Bankroll: ${plan.bankroll:,.2f} | Race risk budget: ${plan.race_risk_budget:,.2f}",
        f"Tickets considered: {plan.tickets_considered} | selected: {plan.tickets_selected}",
    ]
    if plan.decision == "BET":
        lines.append(
            f"Stake ${plan.total_stake:,.2f} -> expected return ${plan.total_expected_return:,.2f} "
            f"(expected profit ${plan.total_expected_profit:,.2f}, ROI {plan.portfolio_expected_roi_pct:.2f}%)"
        )
        lines.append("")
        for i, ticket in enumerate(plan.tickets, 1):
            lines.append(
                f"{i}. {ticket['combo']} | stake ${ticket['recommended_stake']:.2f} | "
                f"p={ticket['joint_prob']:.4%} | adj payout ${ticket['adj_predicted_payout']:.2f} | "
                f"EV ROI {ticket['ev_roi_pct']:.2f}%"
            )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build an EV-based superfecta ticket plan from prediction CSV output")
    p.add_argument("--input", "-i", required=True, help="Prediction CSV from model_main.py or predict_single_race.py")
    p.add_argument("--bankroll", type=float, default=DEFAULT_BANKROLL, help="Bankroll used for stake sizing")
    p.add_argument("--payout-unit", type=float, default=DEFAULT_PAYOUT_UNIT, help="Dollar unit represented by predicted_payout")
    p.add_argument("--ticket-increment", type=float, default=DEFAULT_TICKET_INCREMENT, help="Minimum ticket increment, usually 0.10 or 1.00")
    p.add_argument("--payout-haircut", type=float, default=DEFAULT_PAYOUT_HAIRCUT, help="Conservative haircut applied to predicted payouts")
    p.add_argument("--kelly-fraction", type=float, default=DEFAULT_KELLY_FRACTION, help="Fraction of full Kelly to use")
    p.add_argument("--min-ev-roi", type=float, default=DEFAULT_MIN_EV_ROI, help="Minimum expected ROI as a decimal, after haircut")
    p.add_argument("--min-prob", type=float, default=DEFAULT_MIN_PROB, help="Minimum joint probability for a ticket to be playable")
    p.add_argument("--max-tickets", type=int, default=DEFAULT_MAX_TICKETS, help="Maximum tickets to carry in one race")
    p.add_argument("--max-race-risk", type=float, default=DEFAULT_MAX_RACE_RISK, help="Max bankroll fraction at risk in one race")
    p.add_argument("--max-ticket-risk", type=float, default=DEFAULT_MAX_TICKET_RISK, help="Max bankroll fraction at risk on one ticket")
    p.add_argument("--prob-col", default=DEFAULT_PROB_COL, help="Probability column to use")
    p.add_argument("--payout-col", default=DEFAULT_PAYOUT_COL, help="Payout column to use")
    p.add_argument("--race-label", default="", help="Optional label shown in the output")
    p.add_argument("--save-json", help="Optional output JSON path")
    p.add_argument("--save-csv", help="Optional output CSV path for selected tickets only")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    config = EngineConfig(
        bankroll=args.bankroll,
        payout_unit=args.payout_unit,
        ticket_increment=args.ticket_increment,
        payout_haircut=args.payout_haircut,
        kelly_fraction=args.kelly_fraction,
        min_ev_roi=args.min_ev_roi,
        min_prob=args.min_prob,
        max_tickets=args.max_tickets,
        max_race_risk=args.max_race_risk,
        max_ticket_risk=args.max_ticket_risk,
        prob_col=args.prob_col,
        payout_col=args.payout_col,
        race_label=args.race_label or Path(args.input).stem,
    )

    df = pd.read_csv(args.input)
    plan = build_race_plan(df, config)

    if args.save_json:
        Path(args.save_json).write_text(json.dumps(asdict(plan), indent=2), encoding="utf-8")

    if args.save_csv and plan.tickets:
        pd.DataFrame(plan.tickets).to_csv(args.save_csv, index=False)

    print(format_plan(plan))


if __name__ == "__main__":
    main()
