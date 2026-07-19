#!/usr/bin/env python3
"""
Forward Evidence Scorecard — ranks rules by holdout & walk-forward quality.

This script reads existing evaluation artifacts and produces a single ranked
view that answers: "Which rules should I actually trust going forward?"

Rules are ranked by forward evidence, then assigned a conservative deployment
bucket so small-sample Phase 8 variants do not outrank the safer OP anchor.

Usage:
    python forward_evidence_scorecard.py

Outputs:
    - Ranked table to stdout
    - forward_evidence_scorecard.txt
    - forward_evidence_scorecard.csv
    - forward_evidence_scorecard.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent

FROZEN_SUMMARY = BASE / "frozen_portfolio_eval_summary.csv"
WF_FOLDS = BASE / "walk_forward_validation_folds.csv"
PHASE7_REPORT = BASE / "PHASE7_REPORT.md"
PHASE8_REPORT = BASE / "PHASE8_REPORT.md"
TXT_OUTPUT = BASE / "forward_evidence_scorecard.txt"
CSV_OUTPUT = BASE / "forward_evidence_scorecard.csv"
JSON_OUTPUT = BASE / "forward_evidence_scorecard.json"

REPORT_TIME_ZONE = "Europe/Zagreb"
GENERATED_AT_TIMEZONE_CONTRACT = (
    "generated_at must include an explicit timezone label; the default CLI render uses "
    "Europe/Zagreb local time so copied scorecard excerpts are not timezone-ambiguous"
)
GENERATED_AT_TZ_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} (UTC|CET|CEST)$")


# Bootstrap CIs (lower bound) are hardcoded because they are not stored in the
# frozen CSV artifacts. Most are printed in the Phase 7 / Phase 8 reports; the
# CD_CORE_K8 lower bound is a legacy scorecard constant and is flagged below so
# it does not masquerade as an extracted report row.
BOOTSTRAP_CI_LOWER: dict[str, float] = {
    "BEL_BROAD1_K7": 44.4,
    "OP_DURABLE_K7": -3.4,
    "OP_REFINED_K7": 11.2,
    "AQU_K9": 3.1,
    "SA_K9": -6.3,
    "KEE_K9": -3.0,
    "CD_CORE_K8": -15.0,
    "CD_REFINED_K9": -26.4,
    "DMR_FALL_K7": -28.8,
}

BOOTSTRAP_CI_LOWER_SOURCES: dict[str, dict[str, Any]] = {
    "BEL_BROAD1_K7": {
        "source_type": "report_text_exact",
        "source_report": "PHASE7_REPORT.md",
        "source_text": "Block bootstrap 95% CI | [+44.4%, +239.4%]",
        "provenance_note": "exact Phase 7 broadened-rule report line",
    },
    "OP_DURABLE_K7": {
        "source_type": "report_text_exact",
        "source_report": "PHASE7_REPORT.md",
        "source_text": "Block bootstrap 95% CI | [-3.4%, +76.1%]",
        "provenance_note": "exact Phase 7 OP report line",
    },
    "OP_REFINED_K7": {
        "source_type": "report_text_exact",
        "source_report": "PHASE8_REPORT.md",
        "source_text": "Bootstrap CI | [+11.2%, +90.8%]",
        "provenance_note": "exact Phase 8 OP refined report line",
    },
    "AQU_K9": {
        "source_type": "report_text_exact",
        "source_report": "PHASE8_REPORT.md",
        "source_text": "Bootstrap CI | [+3.1%, +106.6%]",
        "provenance_note": "exact Phase 8 AQU report line",
    },
    "SA_K9": {
        "source_type": "report_text_exact",
        "source_report": "PHASE8_REPORT.md",
        "source_text": "Bootstrap CI | [-6.3%, +58.1%]",
        "provenance_note": "exact Phase 8 SA rule-table report line",
    },
    "KEE_K9": {
        "source_type": "report_text_exact",
        "source_report": "PHASE8_REPORT.md",
        "source_text": "Bootstrap CI | [-3.0%, +67.2%]",
        "provenance_note": "exact Phase 8 KEE report line",
    },
    "CD_CORE_K8": {
        "source_type": "legacy_hardcoded_unprinted",
        "source_report": "forward_evidence_scorecard.py",
        "source_text": "CD_CORE_K8 CI lower bound is not printed as a standalone bootstrap-CI line in PHASE7_REPORT.md or PHASE8_REPORT.md.",
        "provenance_note": "legacy hardcoded CI lower-bound input; keep as caution metadata, not extracted report proof",
    },
    "CD_REFINED_K9": {
        "source_type": "report_text_exact",
        "source_report": "PHASE8_REPORT.md",
        "source_text": "Bootstrap CI | [-26.4%, +191.5%]",
        "provenance_note": "exact Phase 8 CD refined report line",
    },
    "DMR_FALL_K7": {
        "source_type": "report_text_exact",
        "source_report": "PHASE8_REPORT.md",
        "source_text": "Bootstrap CI | [-28.8%, +64.9%]",
        "provenance_note": "exact Phase 8 DMR report line",
    },
}

FULL_SAMPLE_ROI: dict[str, float] = {
    "BEL_BROAD1_K7": 134.9,
    "OP_DURABLE_K7": 35.0,
    "OP_REFINED_K7": 50.0,
    "AQU_K9": 50.2,
    "SA_K9": 25.9,
    "KEE_K9": 30.8,
    "CD_CORE_K8": 13.1,
    "CD_REFINED_K9": 57.0,
    "DMR_FALL_K7": 14.4,
}

FULL_SAMPLE_RACES: dict[str, int] = {
    "BEL_BROAD1_K7": 85,
    "OP_DURABLE_K7": 505,
    "OP_REFINED_K7": 267,
    "AQU_K9": 64,
    "SA_K9": 64,
    "KEE_K9": 111,
    "CD_CORE_K8": 485,
    "CD_REFINED_K9": 151,
    "DMR_FALL_K7": 145,
}

PHASE_ORIGIN: dict[str, str] = {
    "BEL_BROAD1_K7": "P7",
    "OP_DURABLE_K7": "P7",
    "OP_REFINED_K7": "P8",
    "AQU_K9": "P8",
    "SA_K9": "P8",
    "KEE_K9": "P8",
    "CD_CORE_K8": "P7",
    "CD_REFINED_K9": "P8",
    "DMR_FALL_K7": "P8",
}

TIER_PRIORITY = {
    "ANCHOR": 5,
    "PAPER": 4,
    "WATCH": 3,
    "DORMANT": 2,
    "SKIP": 1,
    "NO_DATA": 0,
}

VALID_EVIDENCE_SCOPE = "frozen_holdout_walk_forward_scorecard_only"
SOURCE_SCOPE = "frozen 2024-2025 holdout summary + train-only walk-forward folds; bootstrap CI lows are hardcoded inputs with report-fingerprint and source-note provenance"
EVIDENCE_BOUNDARY = "not a live paper-trade ledger; does not consume current-day scanner, settlement-audit, or profitability results"
MACHINE_READABLE_EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "forward evidence scorecard",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "frozen_portfolio_eval_summary.csv",
        "walk_forward_validation_folds.csv",
        "PHASE7_REPORT.md",
        "PHASE8_REPORT.md",
    ],
    "valid_use": "frozen 2024-2025 holdout plus train-only walk-forward ranking and conservative deployment-tier posture metadata",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "source_fingerprints_are_reproducibility_metadata_only": True,
    "decision_gate_minimums_are_forward_observation_requirements_not_current_evidence": True,
    "stronger_forward_confidence_requires": [
        "qualifying live paper signals",
        "ROI-complete settled paper rows",
        "settlement-quality checks",
        "other real forward observations",
    ],
    "non_goals": [
        "do not use the scorecard rebuild as settled ROI",
        "do not promote OP_REFINED_K7 or Phase 8 from this artifact",
        "do not reopen current odds-only XGBoost from this artifact",
        "do not substitute BAQ for BEL",
        "do not discuss real-money scaling from this artifact",
    ],
}

RANKING_CONTRACT: dict[str, Any] = {
    "rank_sort_order": ["tier_priority", "forward_trust", "holdout_races", "holdout_roi"],
    "rank_is_tier_first_decision_order": True,
    "forward_trust_is_secondary_within_tier": True,
    "raw_score_is_not_an_automatic_deployment_instruction": True,
    "known_rank_override": "CD_CORE_K8 ranks ahead of OP_REFINED_K7 because PAPER tier outranks WATCH tier even though OP_REFINED_K7 has the higher raw forward_trust score.",
    "why": "The scorecard rank is a conservative decision/posture order; tier gates protect against small-sample and mixed-year spikes outrunning the safer OP anchor or primary OP/CD paper-basket companion.",
}

DECISION_CHANGE_GATES: tuple[dict[str, str], ...] = (
    {
        "gate_id": "anchor_displacement",
        "current_decision": "Keep OP_DURABLE_K7 as the safest current anchor.",
        "what_would_change_it": "A challenger needs 30+ ROI-complete settled paper observations plus a cleaner split-aware forward read than the OP anchor before any anchor-review discussion.",
        "does_not_count": "Historical replay rows, clean empty scans, open paper signals, source fingerprints, or green validators do not count as new anchor-changing evidence.",
    },
    {
        "gate_id": "primary_companion",
        "current_decision": "Keep CD_CORE_K8 as the primary OP/CD paper-basket companion, not an anchor replacement and not a Phase 8 shadow-lane promotion.",
        "what_would_change_it": "Changing companion status needs ROI-complete settled OP/CD paper evidence or a new frozen-standard evaluation input, not a wording-only or compatibility-key change.",
        "does_not_count": "The legacy primary_shadow key, a regenerated scorecard, or a validation pass by itself does not prove promotion readiness or live profitability.",
    },
    {
        "gate_id": "phase8_promotion_review",
        "current_decision": "Keep OP_REFINED_K7 and the rest of Phase 8 in shadow/watch mode.",
        "what_would_change_it": "Promotion review needs 20+ ROI-complete settled shadow observations for the candidate with complete ROI coverage and cleaner split-aware/walk-forward support than the current anchor/companion pair.",
        "does_not_count": "A hotter small-sample aggregate holdout ROI or a WATCH label does not make the rule promotion-ready.",
    },
    {
        "gate_id": "real_money_discussion",
        "current_decision": "Keep this as paper-trade observation, not a real-money claim.",
        "what_would_change_it": "Real-money discussion waits for 100+ total settled paper observations with usable ROI coverage, concentration checks, payout sanity checks, and no BAQ-as-BEL substitution.",
        "does_not_count": "Frozen holdout P&L, daily top-card readiness, clean validators, or empty/no-target wrapper runs are not real-money evidence.",
    },
)

DECISION_GATE_MINIMUMS: dict[str, dict[str, Any]] = {
    "anchor_displacement": {
        "min_roi_complete_settled_observations": 30,
        "observation_scope": "same candidate paper observations",
        "also_requires": [
            "cleaner split-aware forward read than OP_DURABLE_K7",
            "equal-or-better walk-forward support",
        ],
        "does_not_count": [
            "historical replay rows",
            "clean empty scans",
            "open paper signals",
            "source fingerprints",
            "green validators",
        ],
    },
    "phase8_promotion_review": {
        "min_roi_complete_settled_observations": 20,
        "observation_scope": "candidate shadow observations",
        "also_requires": [
            "complete ROI coverage",
            "cleaner split-aware/walk-forward support than the current anchor/companion pair",
        ],
        "does_not_count": [
            "small-sample aggregate holdout ROI",
            "WATCH label",
            "clean rebuild",
            "empty live run",
        ],
    },
    "real_money_discussion": {
        "min_total_settled_observations_with_usable_roi": 100,
        "also_requires": [
            "positive paper ROI",
            "concentration checks",
            "payout-distribution sanity checks",
            "no BAQ-as-BEL substitution",
        ],
        "does_not_count": [
            "frozen holdout P&L",
            "daily top-card readiness",
            "clean validators",
            "empty/no-target wrapper runs",
        ],
    },
}

CI_ONLY_PROMOTION_DIAGNOSTICS: dict[str, dict[str, Any]] = {
    "OP_REFINED_K7": {
        "candidate_rule_id": "OP_REFINED_K7",
        "current_anchor_rule_id": "OP_DURABLE_K7",
        "positive_ci_lower_bound_is_support_context": True,
        "ci_only_promotion_allowed": False,
        "current_decision": "Keep OP_REFINED_K7 shadow/watch only.",
        "why_not": [
            "smaller holdout sample than OP_DURABLE_K7",
            "losing 2024 holdout split",
            "lower walk-forward recurrence than OP_DURABLE_K7",
            "uncleared phase8_promotion_review paper-observation gate",
            "uncleared anchor_displacement paper-observation gate",
        ],
        "required_before_review": {
            "phase8_promotion_review": "20+ ROI-complete candidate shadow observations plus cleaner split-aware/walk-forward support",
            "anchor_displacement": "30+ ROI-complete same-candidate paper observations plus a cleaner split-aware forward read and equal-or-better walk-forward support",
        },
        "does_not_count": [
            "positive bootstrap CI lower bound by itself",
            "hotter aggregate small-sample holdout ROI",
            "historical replay rows",
            "clean rebuilds",
            "green validators",
        ],
    },
}

EXPECTED_RULE_IDS = tuple(FULL_SAMPLE_ROI.keys())
REQUIRED_RULE_SLICES = ("holdout_2024_2025", "year_2024", "year_2025")


def file_fingerprint(path: Path) -> dict[str, Any]:
    resolved = Path(path)
    data = resolved.read_bytes()
    return {
        "path": resolved.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def source_file_fingerprints(
    frozen_summary_path: Path = FROZEN_SUMMARY,
    wf_folds_path: Path = WF_FOLDS,
    phase7_report_path: Path = PHASE7_REPORT,
    phase8_report_path: Path = PHASE8_REPORT,
) -> dict[str, dict[str, Any]]:
    return {
        "frozen_summary": file_fingerprint(Path(frozen_summary_path)),
        "walk_forward_folds": file_fingerprint(Path(wf_folds_path)),
        "bootstrap_phase7_report": file_fingerprint(Path(phase7_report_path)),
        "bootstrap_phase8_report": file_fingerprint(Path(phase8_report_path)),
    }


def validate_bootstrap_ci_source_texts(
    phase7_report_path: Path = PHASE7_REPORT,
    phase8_report_path: Path = PHASE8_REPORT,
) -> None:
    report_paths = {
        "PHASE7_REPORT.md": Path(phase7_report_path),
        "PHASE8_REPORT.md": Path(phase8_report_path),
    }
    report_text_by_name = {
        report_name: report_path.read_text(encoding="utf-8")
        for report_name, report_path in report_paths.items()
    }
    for rule_id, source in BOOTSTRAP_CI_LOWER_SOURCES.items():
        if source["source_type"] != "report_text_exact":
            continue
        source_report = str(source["source_report"])
        report_path = report_paths.get(source_report)
        if report_path is None:
            raise ValueError(
                f"bootstrap CI source for {rule_id} references unsupported report {source_report!r}"
            )
        source_text = str(source["source_text"])
        if source_text not in report_text_by_name[source_report]:
            raise ValueError(
                f"{report_path.name} does not contain expected bootstrap CI source text "
                f"for {rule_id} ({source_report}): {source_text!r}"
            )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build the forward-evidence scorecard from frozen holdout and walk-forward artifacts")
    p.add_argument("--frozen-summary", default=str(FROZEN_SUMMARY), help="Frozen portfolio evaluation summary CSV path")
    p.add_argument("--wf-folds", default=str(WF_FOLDS), help="Walk-forward folds CSV path")
    p.add_argument("--phase7-report", default=str(PHASE7_REPORT), help="Phase 7 report path used to fingerprint hardcoded bootstrap CI lower-bound provenance")
    p.add_argument("--phase8-report", default=str(PHASE8_REPORT), help="Phase 8 report path used to fingerprint hardcoded bootstrap CI lower-bound provenance")
    p.add_argument("--txt-output", default=str(TXT_OUTPUT), help="Text report output path")
    p.add_argument("--csv-output", default=str(CSV_OUTPUT), help="CSV table output path")
    p.add_argument("--json-output", default=str(JSON_OUTPUT), help="JSON sidecar output path with metadata plus ranked rows")
    p.add_argument("--generated-at", help="Optional generated-at text to pin into the report for reproducible rerenders")
    p.add_argument("--stdout-only", action="store_true", help="Print the report but do not save files or save notices")
    return p.parse_args()


def read_frozen_rule_summary(summary_path: Path) -> pd.DataFrame:
    df = pd.read_csv(summary_path)
    required_columns = {"level", "name", "slice", "races", "profit", "roi", "hit_rate"}
    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise ValueError(f"{summary_path.name} is missing required columns: {', '.join(missing)}")

    filtered = df[
        (df["level"] == "rule")
        & (df["name"].isin(EXPECTED_RULE_IDS))
        & (df["slice"].isin(REQUIRED_RULE_SLICES))
    ].copy()

    deduped_rows: list[pd.Series] = []
    comparable_columns = [
        column
        for column in ["cost_per_race", "races", "hits", "wagered", "returned", "profit", "roi", "hit_rate"]
        if column in filtered.columns
    ]
    for rule_id in EXPECTED_RULE_IDS:
        for slice_name in REQUIRED_RULE_SLICES:
            group = filtered[(filtered["name"] == rule_id) & (filtered["slice"] == slice_name)].copy()
            if group.empty:
                raise ValueError(
                    f"{summary_path.name} is missing required rule slice {rule_id} / {slice_name}; "
                    "refusing to invent a zero row for the scorecard"
                )
            if len(group) > 1:
                conflicting_columns: list[str] = []
                for column in comparable_columns:
                    raw_values = group[column]
                    try:
                        numeric_values = pd.to_numeric(raw_values)
                    except (TypeError, ValueError):
                        unique_values = raw_values.fillna("").astype(str).drop_duplicates()
                    else:
                        unique_values = numeric_values.astype(float).round(10).drop_duplicates()
                    if len(unique_values) > 1:
                        conflicting_columns.append(column)
                if conflicting_columns:
                    raise ValueError(
                        f"{summary_path.name} has conflicting duplicate rows for {rule_id} / {slice_name} "
                        f"across columns: {', '.join(conflicting_columns)}"
                    )
            deduped_rows.append(group.iloc[0].copy())

    return pd.DataFrame(deduped_rows)


def load_holdout_by_rule(rule_summary: pd.DataFrame) -> pd.DataFrame:
    df = rule_summary.copy()
    holdout = df[(df["slice"] == "holdout_2024_2025") & (df["level"] == "rule")].copy()
    holdout = holdout.rename(columns={
        "name": "rule_id",
        "roi": "holdout_roi",
        "races": "holdout_races",
        "profit": "holdout_profit",
        "hit_rate": "holdout_hit_rate",
    })
    return holdout[["rule_id", "holdout_roi", "holdout_races", "holdout_profit", "holdout_hit_rate"]].copy()


def load_holdout_year_stats(rule_summary: pd.DataFrame) -> dict[str, dict[str, float | int]]:
    df = rule_summary.copy()
    years = df[(df["level"] == "rule") & (df["slice"].str.startswith("year_"))].copy()
    stats: dict[str, dict[str, float | int]] = {}
    for rule_id, grp in years.groupby("name"):
        grp = grp.sort_values(["slice", "races", "profit"], ascending=[True, False, False]).drop_duplicates(subset=["slice"], keep="first")
        observed = grp[grp["races"] > 0].copy()
        years_observed = int(len(observed))
        years_positive = int((observed["roi"] > 0).sum()) if years_observed else 0
        worst_year_roi = float(observed["roi"].min()) if years_observed else np.nan

        row: dict[str, float | int] = {
            "years_observed": years_observed,
            "years_positive": years_positive,
            "worst_year_roi": worst_year_roi,
        }
        for year in (2024, 2025):
            match = grp[grp["slice"] == f"year_{year}"]
            if match.empty:
                row[f"holdout_{year}_roi"] = 0.0
                row[f"holdout_{year}_races"] = 0
                row[f"holdout_{year}_profit"] = 0.0
            else:
                hit = match.iloc[0]
                row[f"holdout_{year}_roi"] = round(float(hit["roi"]), 2)
                row[f"holdout_{year}_races"] = int(hit["races"])
                row[f"holdout_{year}_profit"] = round(float(hit["profit"]), 2)
        stats[str(rule_id)] = row
    return stats


def compute_wf_selection_freq(wf_folds_path: Path) -> dict[str, tuple[int, int]]:
    df = pd.read_csv(wf_folds_path)
    if "selected_rule_ids" not in df.columns:
        raise ValueError(f"{wf_folds_path.name} is missing required column: selected_rule_ids")
    total_folds = len(df)
    if total_folds <= 0:
        raise ValueError(f"{wf_folds_path.name} has no walk-forward folds")
    freq: dict[str, int] = {}
    for rule_ids in df["selected_rule_ids"]:
        for rid in str(rule_ids).split(","):
            rid = rid.strip()
            if rid and not rid.endswith("_BRIDGE_BAQ"):
                if rid not in EXPECTED_RULE_IDS:
                    raise ValueError(f"{wf_folds_path.name} references unknown rule id: {rid}")
                freq[rid] = freq.get(rid, 0) + 1
    return {k: (v, total_folds) for k, v in freq.items()}


def forward_trust_score(
    holdout_roi: float,
    holdout_races: int,
    wf_frac: float,
    ci_lower: float,
    years_positive: int,
    years_observed: int,
) -> float:
    """Composite score for ordering within conservative tiers."""
    roi_clamped = np.clip(holdout_roi, -50, 75)
    roi_score = (roi_clamped + 50) / 125 * 100

    if holdout_races <= 0:
        size_score = 0.0
    else:
        size_score = min(np.log1p(holdout_races) / np.log1p(150) * 100, 100)

    wf_score = wf_frac * 100

    if ci_lower >= 10:
        ci_score = 100.0
    elif ci_lower >= 0:
        ci_score = 60.0 + ci_lower * 4
    elif ci_lower >= -20:
        ci_score = max(60.0 + ci_lower * 2.0, 0)
    else:
        ci_score = 0.0

    year_score = 0.0 if years_observed == 0 else (years_positive / years_observed) * 100

    return round(
        0.28 * roi_score
        + 0.32 * size_score
        + 0.20 * wf_score
        + 0.10 * ci_score
        + 0.10 * year_score,
        1,
    )


def recommendation_tier(
    rule_id: str,
    holdout_roi: float,
    holdout_races: int,
    wf_sel: int,
    ci_lower: float,
    years_positive: int,
    years_observed: int,
) -> str:
    if holdout_races == 0:
        return "DORMANT" if rule_id.startswith("BEL_") else "NO_DATA"
    if holdout_roi <= 0:
        return "SKIP"
    if holdout_races >= 100 and wf_sel >= 5 and ci_lower >= -5:
        return "ANCHOR"
    if (
        holdout_races >= 50
        and years_observed >= 2
        and years_positive == years_observed
        and wf_sel >= 1
        and ci_lower > -20
    ):
        return "PAPER"
    return "WATCH"


def note_for_rule(
    rule_id: str,
    tier: str,
    holdout_races: int,
    wf_sel: int,
    wf_total: int,
    ci_lower: float,
    years_positive: int,
    years_observed: int,
) -> str:
    notes: list[str] = []

    if tier == "ANCHOR":
        notes.append("best current OP anchor")
    elif tier == "PAPER":
        notes.append("positive holdout in both years")
    elif tier == "DORMANT":
        notes.append("no 2024-2025 forward races")
    elif tier == "SKIP":
        notes.append("negative holdout")

    if holdout_races and holdout_races < 50:
        notes.append(f"small holdout ({holdout_races})")
    if years_observed >= 2 and years_positive < years_observed:
        notes.append(f"mixed holdout years ({years_positive}/{years_observed})")
    if wf_sel <= 2 and wf_total:
        notes.append(f"low WF selection ({wf_sel}/{wf_total})")
    if ci_lower < 0:
        notes.append("CI crosses zero")
    if rule_id == "CD_CORE_K8" and tier == "PAPER":
        notes.append("CD family still variant-sensitive")

    seen: list[str] = []
    for note in notes:
        if note not in seen:
            seen.append(note)
    return "; ".join(seen[:3])


def deployment_context(rule_id: str, tier: str) -> tuple[str, str, str]:
    if rule_id == "OP_DURABLE_K7":
        return (
            "Safest current anchor",
            "Keep as safest current anchor",
            "Largest current OP holdout sample plus the strongest walk-forward selection frequency, even though the 2024/2025 path was uneven.",
        )
    if rule_id == "CD_CORE_K8":
        return (
            "Primary paper-basket companion",
            "Keep in the primary paper-basket mix, not as an anchor replacement",
            "Primary OP/CD paper-basket companion: positive in both holdout years, but still a smaller forward sample with low walk-forward selection.",
        )
    if rule_id == "OP_REFINED_K7":
        return (
            "Closest OP challenger",
            "Shadow/watch only",
            "Hotter aggregate holdout ROI, but on a much smaller forward sample with a losing 2024 and only 2/10 walk-forward selections.",
        )
    if rule_id == "DMR_FALL_K7":
        return (
            "One-year pocket only",
            "Observation only",
            "Only one observed holdout year so far, with no train-only walk-forward support yet.",
        )
    if rule_id == "KEE_K9":
        return (
            "Tiny cross-track watch",
            "Observation only",
            "Positive in both holdout years, but still only 20 forward races and CI crosses zero.",
        )
    if rule_id == "SA_K9":
        return (
            "Tiny cross-track watch",
            "Observation only",
            "Positive pocket so far, but only 11 forward races and no train-only walk-forward support yet.",
        )
    if rule_id == "BEL_BROAD1_K7":
        return (
            "Dormant Belmont leg",
            "Wait for Belmont forward races; do not substitute BAQ",
            "Strong historical rule, but it has zero 2024-2025 forward races, so it cannot currently carry current-paper weight.",
        )
    if tier == "SKIP":
        return (
            "Negative holdout skip",
            "Do not promote",
            "Negative holdout in the current forward window, so it stays out of both the primary paper basket and the shadow queue.",
        )
    if tier == "WATCH":
        return (
            "Observation-only watch",
            "Observation only",
            "Forward sample is still too small or too unstable to justify promotion.",
        )
    if tier == "PAPER":
        return (
            "Paper-trade candidate",
            "Paper trade now",
            "Forward evidence is good enough for paper trading, but not strong enough to replace the safer OP anchor.",
        )
    if tier == "ANCHOR":
        return (
            "Current anchor",
            "Keep as anchor",
            "Largest current forward evidence base inside the strongest live family.",
        )
    return (
        "Unclassified",
        "Review manually",
        "This rule needs manual review because its current deployment role is not pinned by the scorecard.",
    )


def build_scorecard(
    frozen_summary_path: Path = FROZEN_SUMMARY,
    wf_folds_path: Path = WF_FOLDS,
) -> pd.DataFrame:
    rule_summary = read_frozen_rule_summary(Path(frozen_summary_path))
    holdout = load_holdout_by_rule(rule_summary).drop_duplicates(subset="rule_id", keep="first")
    year_stats = load_holdout_year_stats(rule_summary)
    wf_freq = compute_wf_selection_freq(Path(wf_folds_path))

    rows = []
    for rule_id in sorted(FULL_SAMPLE_ROI.keys()):
        h = holdout[holdout["rule_id"] == rule_id]
        if len(h) > 0:
            h_roi = float(h.iloc[0]["holdout_roi"])
            h_races = int(h.iloc[0]["holdout_races"])
            h_profit = float(h.iloc[0]["holdout_profit"])
        else:
            h_roi, h_races, h_profit = 0.0, 0, 0.0

        wf_sel, wf_total = wf_freq.get(rule_id, (0, 10))
        wf_frac = wf_sel / wf_total if wf_total > 0 else 0.0
        ci_lower = BOOTSTRAP_CI_LOWER.get(rule_id, 0.0)
        ci_source = BOOTSTRAP_CI_LOWER_SOURCES[rule_id]
        stats = year_stats.get(rule_id, {})
        years_observed = int(stats.get("years_observed", 0))
        years_positive = int(stats.get("years_positive", 0))
        worst_year_roi = stats.get("worst_year_roi", np.nan)

        score = forward_trust_score(
            h_roi,
            h_races,
            wf_frac,
            ci_lower,
            years_positive,
            years_observed,
        )
        tier = recommendation_tier(
            rule_id,
            h_roi,
            h_races,
            wf_sel,
            ci_lower,
            years_positive,
            years_observed,
        )
        note = note_for_rule(
            rule_id,
            tier,
            h_races,
            wf_sel,
            wf_total,
            ci_lower,
            years_positive,
            years_observed,
        )
        current_role, action_now, deployment_reason = deployment_context(rule_id, tier)

        rows.append({
            "rule_id": rule_id,
            "phase": PHASE_ORIGIN.get(rule_id, "?"),
            "backtest_roi": FULL_SAMPLE_ROI.get(rule_id, 0.0),
            "backtest_races": FULL_SAMPLE_RACES.get(rule_id, 0),
            "holdout_roi": h_roi,
            "holdout_races": h_races,
            "holdout_profit": h_profit,
            "holdout_years": f"{years_positive}/{years_observed}",
            "holdout_2024_roi": float(stats.get("holdout_2024_roi", 0.0)),
            "holdout_2024_races": int(stats.get("holdout_2024_races", 0)),
            "holdout_2024_profit": float(stats.get("holdout_2024_profit", 0.0)),
            "holdout_2025_roi": float(stats.get("holdout_2025_roi", 0.0)),
            "holdout_2025_races": int(stats.get("holdout_2025_races", 0)),
            "holdout_2025_profit": float(stats.get("holdout_2025_profit", 0.0)),
            "worst_year_roi": worst_year_roi,
            "wf_selected": f"{wf_sel}/{wf_total}",
            "wf_selected_count": wf_sel,
            "wf_total_folds": wf_total,
            "ci_lower": ci_lower,
            "ci_lower_source_type": ci_source["source_type"],
            "ci_lower_source_report": ci_source["source_report"],
            "ci_lower_source_note": ci_source["provenance_note"],
            "forward_trust": score,
            "tier": tier,
            "current_role": current_role,
            "action_now": action_now,
            "deployment_reason": deployment_reason,
            "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
            "source_scope": SOURCE_SCOPE,
            "evidence_boundary": EVIDENCE_BOUNDARY,
            "note": note,
        })

    df = pd.DataFrame(rows)
    df["tier_priority"] = df["tier"].map(TIER_PRIORITY)
    df = df.sort_values(
        ["tier_priority", "forward_trust", "holdout_races", "holdout_roi"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    df.index = df.index + 1
    df.index.name = "rank"
    return df


def format_split_line(row: pd.Series) -> str:
    return (
        f"- {row['rule_id']}: "
        f"2024 {float(row['holdout_2024_roi']):+0.1f}% on {int(row['holdout_2024_races'])}"
        f" | 2025 {float(row['holdout_2025_roi']):+0.1f}% on {int(row['holdout_2025_races'])}"
    )


def format_year_cell(roi: float, races: int) -> str:
    return f"{roi:+0.1f}%/{races}"


def count_holdout_years(row: pd.Series) -> tuple[int, int]:
    observed = 0
    positive = 0
    for year in (2024, 2025):
        races = int(row[f"holdout_{year}_races"])
        roi = float(row[f"holdout_{year}_roi"])
        if races > 0:
            observed += 1
            if roi > 0:
                positive += 1
    return positive, observed


def watch_blocker(row: pd.Series) -> str:
    holdout_races = int(row["holdout_races"])
    wf_selected = int(row["wf_selected_count"])
    ci_lower = float(row["ci_lower"])
    positive_years, observed_years = count_holdout_years(row)

    if row["rule_id"] == "OP_REFINED_K7":
        return f"closest OP challenger, but mixed years and only {holdout_races} forward races"
    if observed_years < 2:
        return f"only {observed_years} observed holdout year so far; no train-only support yet"
    if positive_years == observed_years and holdout_races <= 20 and ci_lower < 0:
        return f"clean two-year sign, but still only {holdout_races} forward races and CI crosses zero"
    if wf_selected == 0:
        return "positive pocket, but no train-only support yet"
    return "not enough forward races yet"


def format_generated_at(generated_at: Any | None = None) -> str:
    if generated_at is None:
        return datetime.now(ZoneInfo(REPORT_TIME_ZONE)).strftime("%Y-%m-%d %H:%M %Z")
    if isinstance(generated_at, str):
        generated_text = generated_at.strip()
        if not GENERATED_AT_TZ_RE.match(generated_text):
            raise ValueError(
                "generated_at must use 'YYYY-MM-DD HH:MM TZ' with TZ in UTC, CET, or CEST"
            )
        return generated_text

    generated_ts = pd.Timestamp(generated_at)
    if generated_ts.tzinfo is None:
        generated_ts = generated_ts.tz_localize(REPORT_TIME_ZONE)
    else:
        generated_ts = generated_ts.tz_convert(REPORT_TIME_ZONE)
    return generated_ts.strftime("%Y-%m-%d %H:%M %Z")


def scorecard_export_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=["tier_priority"], errors="ignore")


def format_source_fingerprint(label: str, fingerprint: dict[str, Any]) -> str:
    return f"- {label}: {fingerprint['path']} ({fingerprint['bytes']} bytes, sha256={fingerprint['sha256']})"


def build_json_payload(
    df: pd.DataFrame,
    generated_at: Any | None = None,
    frozen_summary_path: Path = FROZEN_SUMMARY,
    wf_folds_path: Path = WF_FOLDS,
    phase7_report_path: Path = PHASE7_REPORT,
    phase8_report_path: Path = PHASE8_REPORT,
) -> dict[str, Any]:
    validate_bootstrap_ci_source_texts(
        phase7_report_path=Path(phase7_report_path),
        phase8_report_path=Path(phase8_report_path),
    )
    export_df = scorecard_export_frame(df).reset_index()
    return {
        "schema_version": 1,
        "artifact": "forward_evidence_scorecard",
        "generated_at": format_generated_at(generated_at),
        "generated_at_timezone": REPORT_TIME_ZONE,
        "generated_at_timezone_contract": GENERATED_AT_TIMEZONE_CONTRACT,
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "source_scope": SOURCE_SCOPE,
        "evidence_boundary": MACHINE_READABLE_EVIDENCE_BOUNDARY,
        "evidence_boundary_text": EVIDENCE_BOUNDARY,
        "ranking_standard": "rules ranked by tier-first conservative decision order, then forward_trust within tier; not an automatic deployment instruction",
        "ranking_contract": RANKING_CONTRACT,
        "decision_change_gates": list(DECISION_CHANGE_GATES),
        "decision_gate_minimums": DECISION_GATE_MINIMUMS,
        "ci_only_promotion_diagnostics": CI_ONLY_PROMOTION_DIAGNOSTICS,
        "bootstrap_ci_lower_sources": {
            rule_id: {
                **source,
                "ci_lower": BOOTSTRAP_CI_LOWER[rule_id],
            }
            for rule_id, source in BOOTSTRAP_CI_LOWER_SOURCES.items()
        },
        "source_files": source_file_fingerprints(
            frozen_summary_path=Path(frozen_summary_path),
            wf_folds_path=Path(wf_folds_path),
            phase7_report_path=Path(phase7_report_path),
            phase8_report_path=Path(phase8_report_path),
        ),
        "row_count": int(len(export_df)),
        "columns": list(export_df.columns),
        "rows": json.loads(export_df.to_json(orient="records")),
    }


def format_report(
    df: pd.DataFrame,
    generated_at: Any | None = None,
    frozen_summary_path: Path = FROZEN_SUMMARY,
    wf_folds_path: Path = WF_FOLDS,
    phase7_report_path: Path = PHASE7_REPORT,
    phase8_report_path: Path = PHASE8_REPORT,
) -> str:
    validate_bootstrap_ci_source_texts(
        phase7_report_path=Path(phase7_report_path),
        phase8_report_path=Path(phase8_report_path),
    )
    generated_text = format_generated_at(generated_at)
    fingerprints = source_file_fingerprints(
        frozen_summary_path=Path(frozen_summary_path),
        wf_folds_path=Path(wf_folds_path),
        phase7_report_path=Path(phase7_report_path),
        phase8_report_path=Path(phase8_report_path),
    )

    table_width = 170
    lines = [
        "=" * table_width,
        "FORWARD EVIDENCE SCORECARD",
        f"Generated: {generated_text}",
        f"Generated timezone contract: {GENERATED_AT_TIMEZONE_CONTRACT}.",
        f"Valid evidence scope: valid_evidence_scope={VALID_EVIDENCE_SCOPE}.",
        f"Source scope: {SOURCE_SCOPE}.",
        f"Evidence boundary: this is {EVIDENCE_BOUNDARY}.",
        "Source fingerprints (exact input bytes; same values are copied into the JSON sidecar):",
        format_source_fingerprint("frozen_summary", fingerprints["frozen_summary"]),
        format_source_fingerprint("walk_forward_folds", fingerprints["walk_forward_folds"]),
        format_source_fingerprint("bootstrap_phase7_report", fingerprints["bootstrap_phase7_report"]),
        format_source_fingerprint("bootstrap_phase8_report", fingerprints["bootstrap_phase8_report"]),
        "Rules ranked by tier-first conservative decision order, then by forward_trust within tier.",
        "Rank is not raw-score order: PAPER CD_CORE_K8 intentionally ranks ahead of WATCH OP_REFINED_K7 even though OP_REFINED_K7 has the higher raw Score.",
        "Main table stays split-aware on purpose so an aggregate holdout ROI does not outrun the year-specific sample support behind it.",
        "Bootstrap CI lower bounds are hardcoded scorecard inputs with text/CSV/JSON source notes; CD_CORE_K8 is flagged as a legacy hardcoded value that is not printed as a standalone CI line in the Phase 7/8 reports.",
        "=" * table_width,
        "",
    ]

    header = (
        f"{'Rank':<5} {'Rule':<22} {'Ph':<4} "
        f"{'HO ROI':>8} {'HO N':>6} {'2024 ROI/N':>14} {'2025 ROI/N':>14} {'Yrs+':>6} {'WF':>6} {'CI Lo':>7} {'Score':>7} {'Tier':<8} Note"
    )
    lines.append(header)
    lines.append("-" * len(header))

    for rank, row in df.iterrows():
        line = (
            f"{rank:<5} {row['rule_id']:<22} {row['phase']:<4} "
            f"{row['holdout_roi']:>+7.1f}% {row['holdout_races']:>5} "
            f"{format_year_cell(float(row['holdout_2024_roi']), int(row['holdout_2024_races'])):>14} "
            f"{format_year_cell(float(row['holdout_2025_roi']), int(row['holdout_2025_races'])):>14} "
            f"{row['holdout_years']:>6} {row['wf_selected']:>6} "
            f"{row['ci_lower']:>+6.1f}% {row['forward_trust']:>6.1f} "
            f"{row['tier']:<8} {row['note']}"
        )
        lines.append(line)

    lines.extend([
        "",
        "HOLDOUT YEAR SPLIT (2024 vs 2025)",
        "-" * table_width,
        "Use this when an aggregate holdout ROI looks prettier than the underlying two-year path.",
    ])
    for _, row in df.iterrows():
        lines.append(format_split_line(row))

    lines.extend([
        "",
        "BOOTSTRAP CI LOWER-BOUND PROVENANCE",
        "-" * table_width,
        "These values affect the compact score only. They are reproducibility/caution metadata, not fresh forward evidence.",
    ])
    for _, row in df.iterrows():
        rule_id = str(row["rule_id"])
        source = BOOTSTRAP_CI_LOWER_SOURCES[rule_id]
        lines.append(
            f"- {rule_id}: {float(row['ci_lower']):+0.1f}% | {source['source_type']} | "
            f"{source['source_report']} | {source['provenance_note']}"
        )

    op_refined = df[df["rule_id"] == "OP_REFINED_K7"].iloc[0]
    op_anchor = df[df["rule_id"] == "OP_DURABLE_K7"].iloc[0]
    lines.extend([
        "",
        "CI-ONLY PROMOTION CHECK",
        "-" * table_width,
        "Use this when a positive bootstrap CI lower bound starts to look like a decision trigger.",
        f"- OP_REFINED_K7: positive CI lower bound ({float(op_refined['ci_lower']):+0.1f}%) is support context only; ci_only_promotion_allowed=false.",
        f"  It remains WATCH because the holdout sample is {int(op_refined['holdout_races'])} vs OP_DURABLE_K7's {int(op_anchor['holdout_races'])}, 2024 was losing, walk-forward recurrence is {op_refined['wf_selected']} vs {op_anchor['wf_selected']}, and the separate 20-row promotion-review / 30-row anchor-displacement paper-observation gates are uncleared.",
    ])

    watch_rows = df[df["tier"] == "WATCH"].copy()
    if not watch_rows.empty:
        lines.extend([
            "",
            "WATCH-LIST TRIAGE (shadow only, not a promotion queue)",
            "-" * table_width,
            "Use this when a WATCH rule's aggregate holdout ROI starts to look stronger than the sample behind it.",
        ])
        watch_header = (
            f"{'Rule':<22} {'HO N':>6} {'2024 ROI/N':>14} {'2025 ROI/N':>14} {'WF':>6} Why still WATCH"
        )
        lines.append(watch_header)
        lines.append("-" * len(watch_header))
        for _, row in watch_rows.iterrows():
            lines.append(
                f"{row['rule_id']:<22} {int(row['holdout_races']):>6} "
                f"{format_year_cell(float(row['holdout_2024_roi']), int(row['holdout_2024_races'])):>14} "
                f"{format_year_cell(float(row['holdout_2025_roi']), int(row['holdout_2025_races'])):>14} "
                f"{row['wf_selected']:>6} {watch_blocker(row)}"
            )
        lines.extend([
            "",
            "Bottom line: OP_REFINED_K7 is the closest shadow challenger because it stays inside the strongest current family,",
            "but none of the WATCH rules has enough forward support to displace OP_DURABLE_K7 or join the primary paper basket yet.",
        ])

    lines.extend([
        "",
        "DECISION-CHANGE GATES (what would actually change the tiers)",
        "-" * table_width,
        "Use this section to avoid treating a pretty score, clean rebuild, or empty live run as posture-changing proof.",
        "Machine-readable threshold summary (also copied into the JSON sidecar): anchor_displacement=30 ROI-complete same-candidate settled observations; phase8_promotion_review=20 ROI-complete shadow observations; real_money_discussion=100 total settled observations with usable ROI.",
    ])
    for gate in DECISION_CHANGE_GATES:
        lines.extend([
            f"- {gate['gate_id']}: {gate['current_decision']}",
            f"  Would change only if: {gate['what_would_change_it']}",
            f"  Does not count: {gate['does_not_count']}",
        ])

    lines.extend([
        "",
        "-" * 132,
        "LEGEND:",
        "  HO ROI / HO N = 2024-2025 holdout ROI and race count",
        "  2024 ROI/N    = year-specific holdout ROI and race count for 2024",
        "  2025 ROI/N    = year-specific holdout ROI and race count for 2025",
        "  Yrs+          = profitable holdout years / observed holdout years (2024, 2025)",
        "  WF            = walk-forward folds selected / total folds",
        "  CI Lo         = bootstrap 95% CI lower bound from scorecard source notes",
        "  Score         = forward_trust score used inside a tier; rank is tier-first and not raw-score order",
        "  Tier          = ANCHOR (safest current paper anchor), PAPER (paper trade now),",
        "                  WATCH (shadow only / not enough evidence), DORMANT (no forward races), SKIP (negative holdout)",
        "",
        "KEY INSIGHT: OP_DURABLE_K7 is the safest anchor because it has the largest real holdout sample",
        "plus the strongest walk-forward selection frequency. Small-sample Phase 8 winners stay in WATCH until",
        "they earn more forward races.",
        "-" * table_width,
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    args = parse_args()
    df = build_scorecard(
        frozen_summary_path=Path(args.frozen_summary),
        wf_folds_path=Path(args.wf_folds),
    )
    generated_at = args.generated_at if args.generated_at else pd.Timestamp.now()
    report = format_report(
        df,
        generated_at=generated_at,
        frozen_summary_path=Path(args.frozen_summary),
        wf_folds_path=Path(args.wf_folds),
        phase7_report_path=Path(args.phase7_report),
        phase8_report_path=Path(args.phase8_report),
    )
    print(report)

    if not args.stdout_only:
        txt_output = Path(args.txt_output)
        csv_output = Path(args.csv_output)
        json_output = Path(args.json_output)
        txt_output.parent.mkdir(parents=True, exist_ok=True)
        csv_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.parent.mkdir(parents=True, exist_ok=True)

        export_df = scorecard_export_frame(df)
        txt_output.write_text(report + "\n", encoding="utf-8")
        export_df.to_csv(csv_output, index_label="rank")
        json_output.write_text(
            json.dumps(
                build_json_payload(
                    df,
                    generated_at=generated_at,
                    frozen_summary_path=Path(args.frozen_summary),
                    wf_folds_path=Path(args.wf_folds),
                    phase7_report_path=Path(args.phase7_report),
                    phase8_report_path=Path(args.phase8_report),
                ),
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )

        print(f"\nSaved to: {txt_output.resolve()}")
        print(f"Saved to: {csv_output.resolve()}")
        print(f"Saved to: {json_output.resolve()}")
