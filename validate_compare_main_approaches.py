#!/usr/bin/env python3
"""
Validation for compare_main_approaches.py.

Purpose:
- keep the main comparison harness reproducible at the source layer
- check saved compare_main_approaches artifacts against a fresh in-memory rebuild
- pin the small set of frozen relationships the comparison is supposed to preserve
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.testing import assert_frame_equal

import compare_main_approaches as cma

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "out" / "status_validation" / "compare_main_approaches"
OUT_MD = OUT_DIR / "compare_main_approaches_validation.md"
OUT_JSON = OUT_DIR / "compare_main_approaches_validation.json"
TMP_PARENT = OUT_DIR / "_tmp"
REBUILD_COMMAND = "python3 validate_compare_main_approaches.py"
COMPARE_SCRIPT = BASE / "compare_main_approaches.py"
METHOD_FAMILY_SCRIPT = BASE / "method_family_decision_card.py"
CROSS_FAMILY_CSV = BASE / "cross_family_decision_card.csv"
COMPARE_CSV = BASE / "compare_main_approaches.csv"
COMPARE_MD = BASE / "compare_main_approaches.md"
COMPARE_JSON = BASE / "compare_main_approaches.json"
FROZEN_EVAL = BASE / "frozen_portfolio_eval_summary.csv"
PHASE5_CACHE = BASE / "phase5_race_cache.pkl"
PHASE7_RULES = BASE / "phase7_live_rules.json"
WF_FOLDS = BASE / "walk_forward_validation_folds.csv"
WF_RULES = BASE / "walk_forward_validation_rules.csv"
BACKTEST_SUMMARY = BASE / "backtest_summary.csv"
AB_RESULTS = BASE / "ab_downstream_comparison_results.json"
FORWARD_SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"


HOLDOUT_YEARS = [2024, 2025]


def normalize_frame(df: pd.DataFrame, key: str) -> pd.DataFrame:
    out = df.copy().sort_values(key).reset_index(drop=True)
    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]):
            out[col] = pd.to_numeric(out[col], errors="coerce").round(6)
        elif pd.api.types.is_bool_dtype(out[col]):
            out[col] = out[col].astype(bool)
        else:
            out[col] = out[col].fillna("")
    return out


def require(condition: bool, name: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    return {"check": name, "status": "pass", "detail": detail}


def has_timezone_aware_timestamp(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    parse_text = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(parse_text)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def frozen_row(level: str, name: str, slice_name: str) -> pd.Series:
    df = pd.read_csv(FROZEN_EVAL)
    match = df[(df["level"] == level) & (df["name"] == name) & (df["slice"] == slice_name)]
    if match.empty:
        raise AssertionError(f"Missing frozen row for {level} / {name} / {slice_name}")
    return match.iloc[0]


def compare_like_saved(saved: pd.DataFrame, rebuilt: pd.DataFrame) -> None:
    if "rank" in saved.columns and "rank" not in rebuilt.columns:
        rebuilt = rebuilt.copy()
        rebuilt.insert(0, "rank", range(1, len(rebuilt) + 1))
    missing_cols = [col for col in saved.columns if col not in rebuilt.columns]
    if missing_cols:
        raise AssertionError(f"rebuilt compare frame is missing saved columns {missing_cols}")
    rebuilt = rebuilt[saved.columns]
    assert_frame_equal(
        normalize_frame(saved, "method_id"),
        normalize_frame(rebuilt, "method_id"),
        check_dtype=False,
        check_exact=False,
        atol=1e-9,
        rtol=0,
    )


def build_suite_read(compare_df: pd.DataFrame, holdout_choice_map: dict[int, str], selective_family: dict[str, Any]) -> str:
    return (
        "main comparison harness stays locked to the frozen 2024-2025 holdout standard; "
        f"Phase7=PAPER NOW ({float(compare_df.loc['phase7_live_portfolio', 'holdout_roi']):+.2f}% on "
        f"{int(compare_df.loc['phase7_live_portfolio', 'holdout_races'])} races; "
        f"2024={float(compare_df.loc['phase7_live_portfolio', 'holdout_2024_roi']):+.2f}% on {int(compare_df.loc['phase7_live_portfolio', 'holdout_2024_races'])}, "
        f"2025={float(compare_df.loc['phase7_live_portfolio', 'holdout_2025_roi']):+.2f}% on {int(compare_df.loc['phase7_live_portfolio', 'holdout_2025_races'])}); "
        f"Phase8=SHADOW ONLY ({float(compare_df.loc['phase8_frozen_portfolio', 'holdout_roi']):+.2f}% on "
        f"{int(compare_df.loc['phase8_frozen_portfolio', 'holdout_races'])} races); "
        f"OP_DURABLE_K7 stays ANCHOR on the larger holdout sample "
        f"({int(compare_df.loc['op_durable_only', 'holdout_races'])} vs "
        f"{int(compare_df.loc['op_refined_only', 'holdout_races'])} races for OP_REFINED_K7; "
        f"2024={float(compare_df.loc['op_durable_only', 'holdout_2024_roi']):+.2f}% on {int(compare_df.loc['op_durable_only', 'holdout_2024_races'])}, "
        f"2025={float(compare_df.loc['op_durable_only', 'holdout_2025_roi']):+.2f}% on {int(compare_df.loc['op_durable_only', 'holdout_2025_races'])}); "
        f"selective family guardrail also stays split-aware (2024={float(compare_df.loc['phase7_live_portfolio', 'holdout_2024_roi']):+.2f}% on {int(compare_df.loc['phase7_live_portfolio', 'holdout_2024_races'])}, "
        f"2025={float(compare_df.loc['phase7_live_portfolio', 'holdout_2025_roi']):+.2f}% on {int(compare_df.loc['phase7_live_portfolio', 'holdout_2025_races'])}); "
        f"current paper-companion read anchor={selective_family['current_anchor']}, paper companion={selective_family['primary_shadow']}, closest shadow={selective_family['secondary_shadow']}; "
        "primary paper-basket core is effectively OP_DURABLE_K7 + CD_CORE_K8 while BEL_BROAD1_K7 stays dormant until Belmont reopens; "
        "one-screen read routes the primary paper-basket core, closest OP challenger, Harville benchmark-only lane, odds-only XGBoost research-only lane, settlement-audit non-evidence boundary, and BEL-not-BAQ caution before the detailed tables; "
        "method-family action summary tells Cole to spend operational energy on settled selective paper observations first while Harville and current odds-only XGBoost stay comparison controls unless their evidence class changes, with settlement-audit repairs treated as row-usability work rather than lane promotion; "
        "OP_REFINED_K7 positive-CI support is now pinned as support context only, not enough by itself to promote the rule, displace OP_DURABLE_K7, or change the OP/CD paper core; "
        "method-family evidence-debt checklist now names the missing evidence class, invalid shortcuts, and next honest action for the selective OP/CD path, Harville, and current odds-only XGBoost, with the same checklist plus scorecard-sourced gate minimums published in compare_main_approaches.json for automation; "
        "scorecard ranking-contract inheritance keeps deployment posture tier-first so OP_REFINED_K7's hotter raw score cannot become an automatic promotion cue; "
        "source provenance table fingerprints the exact comparison input bytes, matches the JSON sidecar source_files map, and proves row-identical source-byte drift changes provenance only, without treating those hashes as performance evidence; "
        "current operator-boundary snapshot carries the combined operator_status_context/source_freshness/operator_read_gate route, the current recommendation-state, source-published settlement-queue state/context plus by-rule detail, API/403 sidecar action/recheck route when present, source-freshness reference date/timezone/comparison-source fields, wrapper-refresh non-evidence boundary, scorecard-audit route, and rebuild-validation contract from current_evidence_summary.json as routing metadata only; "
        "machine-readable evidence_boundary metadata now keeps the main comparison bundle separate from live paper ledgers, scanner output, settled ROI, live profitability, promotion readiness, real-money evidence, OP_REFINED_K7 promotion, odds-only XGBoost reopening, Harville live treatment, and BAQ/BEL substitution; "
        "Phase 8 shadow triage still treats OP_REFINED_K7 as the closest challenger while KEE_K9, SA_K9, and DMR_FALL_K7 remain observation-only pockets; "
        "decision-change gates pin OP_REFINED_K7 promotion review, stricter OP_DURABLE_K7 anchor displacement, Harville live reconsideration, current odds-only XGBoost reopening, BEL/BAQ substitution, and real-money scaling behind explicit forward-observation/evidence-class thresholds; machine-readable decision-gate minimums keep anchor_displacement=30 same-candidate rows, phase8_promotion_review=20 shadow rows, and real_money_discussion=100 total settled rows named separately, with evidence scope now separating future settled ledger observations from historical replay, clean scans, open signals, ledger-quality/settlement-audit passes, calibration-only summaries, or another odds-only rerun; those named anchor_displacement=30, phase8_promotion_review=20, and real_money_discussion=100 thresholds are source-matched against forward_evidence_scorecard.json and now loaded directly from its decision_gate_minimums with fail-fast missing-threshold, non-positive Phase 8 / real-money floor, and missing no-BAQ prerequisite coverage plus changed-threshold fixture coverage so the scorecard and main-comparison gates cannot drift independently; "
        f"op_train_switch and train_only_selector stay BENCHMARK ONLY; "
        f"holdout OP switch choices "
        f"{', '.join(f'{year}={rule}' for year, rule in holdout_choice_map.items())}; "
        "saved CSV, saved markdown, saved JSON sidecar, and real CLI stdout stay pinned to the same main-comparison render; "
        "custom method-family source paths rerender hierarchy labels and provenance without changing ranked rows; "
        "project-local CLI scratch-root metadata stays published for comparison rerenders"
    )


def build_expected_cli_stdout(
    report_text: str,
    csv_name: str = "compare_main_approaches.csv",
    md_name: str = "compare_main_approaches.md",
    json_name: str = "compare_main_approaches.json",
) -> str:
    return report_text + f"Saved: {csv_name}\nSaved: {md_name}\nSaved: {json_name}\n"


def strip_source_provenance_section(report_text: str) -> str:
    return re.sub(
        r"\n## Source Provenance\n\n.*?\n## Cole's One-Screen Read",
        "\n## Source Provenance\n\n<SOURCE PROVENANCE STRIPPED>\n\n## Cole's One-Screen Read",
        report_text,
        flags=re.S,
    )


def parse_source_provenance_table(report_text: str) -> dict[str, dict[str, Any]]:
    try:
        section = report_text.split("## Source Provenance\n\n", 1)[1].split("## Cole's One-Screen Read", 1)[0]
    except IndexError as exc:
        raise AssertionError("compare_main_approaches.md source provenance section could not be isolated") from exc

    rows_started = False
    row_lines: list[str] = []
    for line in section.splitlines():
        if line == "| Source | Path | Bytes | SHA-256 |":
            rows_started = True
            continue
        if rows_started and line == "|---|---|---:|---|":
            continue
        if rows_started:
            if not line.startswith("| "):
                break
            row_lines.append(line)

    if not row_lines:
        raise AssertionError("compare_main_approaches.md source provenance table could not be parsed")

    parsed: dict[str, dict[str, Any]] = {}
    for line in row_lines:
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) != 4:
            raise AssertionError(f"unexpected source provenance row shape: {line}")
        label, path_cell, bytes_cell, sha_cell = parts
        parsed[label] = {
            "path": path_cell.strip("`"),
            "bytes": int(bytes_cell),
            "sha256": sha_cell.strip("`"),
        }
    return parsed


def prepare_tmp_parent() -> Path:
    """Use project-local scratch space so CLI fixture writes avoid system temp quotas."""
    if TMP_PARENT.exists():
        shutil.rmtree(TMP_PARENT)
    TMP_PARENT.mkdir(parents=True, exist_ok=True)
    return TMP_PARENT


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_parent = prepare_tmp_parent()
    scratch_meta = {
        "tmp_parent": str(tmp_parent),
        "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
        "tmp_parent_cleared_before_fixture_run": True,
    }

    saved_df = pd.read_csv(COMPARE_CSV)
    saved_json = json.loads(COMPARE_JSON.read_text(encoding="utf-8"))
    scorecard_json = json.loads(FORWARD_SCORECARD_JSON.read_text(encoding="utf-8"))
    rebuilt_df, wf_years, folds, holdout_switch_choices = cma.build_dataframe(HOLDOUT_YEARS)
    compare_like_saved(saved_df, rebuilt_df)

    checks: list[dict[str, Any]] = []
    report_text = COMPARE_MD.read_text(encoding="utf-8")
    runtime_match = re.search(r"^- Runtime: ([0-9]+(?:\.[0-9]+)?) seconds$", report_text, flags=re.MULTILINE)
    if runtime_match is None:
        raise AssertionError("compare_main_approaches.md is missing its runtime line")
    saved_runtime_sec = float(runtime_match.group(1))
    rebuilt_md = cma.build_report(
        rebuilt_df,
        HOLDOUT_YEARS,
        wf_years,
        saved_runtime_sec,
        cma.load_method_family_rows(),
    )
    checks.append(
        require(
            report_text.strip() == rebuilt_md.strip(),
            "markdown_matches_rebuild",
            "compare_main_approaches.md still matches a fresh rebuild from compare_main_approaches.py",
        )
    )
    expected_json = cma.build_json_payload(
        rebuilt_df,
        HOLDOUT_YEARS,
        wf_years,
        saved_runtime_sec,
        cma.load_method_family_rows(compare_rows=rebuilt_df.to_dict(orient="records")),
    )
    compare_like_saved(saved_df, pd.DataFrame(saved_json.get("ranked_rows", [])))
    evidence_boundary = saved_json.get("evidence_boundary", {})
    current_operator_boundary = saved_json.get("current_operator_boundary", {})
    expected_current_operator_boundary = cma.load_current_operator_boundary()
    current_gate_progress = current_operator_boundary.get("decision_gate_progress", {})
    current_evidence = json.loads(CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8"))
    source_current_gate_progress = current_evidence["decision_gate_progress"]
    source_operator_read_gate = current_evidence["operator_read_gate"]
    source_scorecard_audit_route = current_evidence["scorecard_audit_route"]
    source_rebuild_validation_contract = current_evidence["rebuild_validation_contract"]
    source_open_queue = current_evidence["current_paper_status"]["primary"]["open_settlement_queue_by_rule"]
    source_operator_gate_status = source_operator_read_gate.get("gate_status")
    source_operator_gate_read = str(source_operator_read_gate.get("read") or "")
    source_operator_requires_refresh = bool(
        source_operator_read_gate.get("requires_refresh_before_evidence_read")
    )
    if source_operator_requires_refresh:
        operator_read_gate_branch_ok = (
            source_operator_gate_status == "refresh_required_before_evidence_read"
            and source_operator_read_gate.get("recommended_command") == "./run_daily_portfolio_observation.sh"
            and source_operator_read_gate.get("has_wrapper_refresh_action") is True
            and "Refresh/recheck with `./run_daily_portfolio_observation.sh`" in source_operator_gate_read
            and "not a no-target, clean-empty, bet-readiness, settled-ROI" in source_operator_gate_read
        )
    else:
        operator_read_gate_branch_ok = (
            source_operator_gate_status == "current_operator_routing_context_only"
            and source_operator_read_gate.get("recommended_command")
            == current_operator_boundary.get("best_action_command")
            and source_operator_read_gate.get("has_wrapper_refresh_action") is False
            and "current operator routing context" in source_operator_gate_read
            and "not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence"
            in source_operator_gate_read
        )
    checks.append(
        require(
            saved_json == expected_json
            and saved_json.get("row_count") == int(len(saved_df))
            and saved_json.get("source_files") == cma.source_file_fingerprints()
            and evidence_boundary == cma.MACHINE_READABLE_EVIDENCE_BOUNDARY
            and saved_json.get("evidence_boundary_text") == cma.EVIDENCE_BOUNDARY
            and saved_json.get("decision_change_gate_minimums") == cma.load_decision_change_gate_minimums()
            and saved_json.get("scorecard_ranking_contract") == scorecard_json.get("ranking_contract")
            and saved_json.get("scorecard_ranking_contract_read") == "rank is tier-first conservative decision order; raw forward_trust/Score is evidence support inside posture, not an automatic promotion queue"
            and saved_json.get("decision_read", {}).get("active_anchor") == "OP_DURABLE_K7"
            and saved_json.get("decision_read", {}).get("paper_companion") == "CD_CORE_K8"
            and saved_json.get("decision_read", {}).get("closest_shadow") == "OP_REFINED_K7"
            and saved_json.get("method_family_roles", {}).get("selective_rule_path", {}).get("primary_companion") == "CD_CORE_K8"
            and current_operator_boundary.get("source_path") == CURRENT_EVIDENCE_JSON.name
            and current_operator_boundary == expected_current_operator_boundary
            and current_gate_progress == source_current_gate_progress
            and current_operator_boundary.get("operator_read_gate") == source_operator_read_gate
            and operator_read_gate_branch_ok
            and current_operator_boundary.get("operator_read_gate", {}).get("gate_status")
            == source_operator_gate_status
            and current_operator_boundary.get("operator_read_gate", {}).get("recommended_command")
            == source_operator_read_gate.get("recommended_command")
            and current_operator_boundary.get("operator_read_gate", {}).get("requires_refresh_before_evidence_read")
            is source_operator_read_gate.get("requires_refresh_before_evidence_read")
            and current_operator_boundary.get("operator_read_gate", {}).get("has_api_access_failure_context")
            is source_operator_read_gate.get("has_api_access_failure_context")
            and current_operator_boundary.get("operator_read_gate", {}).get("has_scanner_failure_boundary")
            is source_operator_read_gate.get("has_scanner_failure_boundary")
            and current_operator_boundary.get("operator_read_gate", {}).get("has_stale_cache_fallback_context")
            is source_operator_read_gate.get("has_stale_cache_fallback_context")
            and current_operator_boundary.get("operator_read_gate", {}).get(
                "current_top_card_counts_as_no_target_evidence"
            )
            is False
            and current_operator_boundary.get("operator_read_gate", {}).get(
                "current_top_card_counts_as_clean_empty_evidence"
            )
            is False
            and current_operator_boundary.get("operator_read_gate", {}).get(
                "current_top_card_counts_as_bet_readiness_evidence"
            )
            is False
            and current_operator_boundary.get("operator_read_gate", {}).get(
                "current_top_card_counts_as_settled_roi_evidence"
            )
            is False
            and current_operator_boundary.get("operator_read_gate", {}).get(
                "not_forward_performance_evidence"
            )
            is True
            and current_operator_boundary.get("operator_read_gate", {}).get(
                "not_promotion_readiness_evidence"
            )
            is True
            and current_operator_boundary.get("operator_read_gate", {}).get(
                "not_live_profitability_evidence"
            )
            is True
            and current_operator_boundary.get("operator_read_gate", {}).get("not_real_money_evidence")
            is True
            and str(current_operator_boundary.get("operator_read_gate", {}).get("read") or "")
            == source_operator_gate_read
            and "| Operator read gate | `current_evidence_summary.json` `operator_read_gate`:"
            in report_text
            and current_gate_progress.get("gate_status") == "all_uncleared"
            and current_gate_progress.get("all_gates_ready") is False
            and current_gate_progress.get("not_forward_performance_evidence") is True
            and current_gate_progress.get("not_promotion_readiness_evidence") is True
            and current_gate_progress.get("not_live_profitability_evidence") is True
            and current_gate_progress.get("not_real_money_evidence") is True
            and "Gate progress: primary first-read 6/30" in current_gate_progress.get("read", "")
            and "OP anchor same-candidate 0/30" in current_gate_progress.get("read", "")
            and "Phase 8 weakest shadow 0/20" in current_gate_progress.get("read", "")
            and "real-money discussion floor 6/100" in current_gate_progress.get("read", "")
            and current_operator_boundary.get("source_consistency_overall_match") is True
            and current_operator_boundary.get("right_now_freshness_state")
            == expected_current_operator_boundary.get("right_now_freshness_state")
            and current_operator_boundary.get("requires_refresh_before_right_now_use")
            == expected_current_operator_boundary.get("requires_refresh_before_right_now_use")
            and current_operator_boundary.get("refresh_action_command") == "./run_daily_portfolio_observation.sh"
            and current_operator_boundary.get("refresh_action_command")
            == expected_current_operator_boundary.get("refresh_action_command")
            and current_operator_boundary.get("refresh_required_before_right_now_instruction_use")
            == expected_current_operator_boundary.get("refresh_required_before_right_now_instruction_use")
            and current_operator_boundary.get("refresh_source_action_counts_as_current_instruction_before_refresh")
            == expected_current_operator_boundary.get("refresh_source_action_counts_as_current_instruction_before_refresh")
            and current_operator_boundary.get("refresh_can_update_operator_surfaces")
            == expected_current_operator_boundary.get("refresh_can_update_operator_surfaces")
            and current_operator_boundary.get("refresh_can_settle_open_rows_by_itself")
            == expected_current_operator_boundary.get("refresh_can_settle_open_rows_by_itself")
            and current_operator_boundary.get("refresh_counts_as_roi_complete_evidence_by_itself")
            == expected_current_operator_boundary.get("refresh_counts_as_roi_complete_evidence_by_itself")
            and current_operator_boundary.get("clean_empty_refresh_counts_as_forward_performance")
            == expected_current_operator_boundary.get("clean_empty_refresh_counts_as_forward_performance")
            and current_operator_boundary.get("missing_or_invalid_artifact_counts_as_clean_quiet_day")
            == expected_current_operator_boundary.get("missing_or_invalid_artifact_counts_as_clean_quiet_day")
            and current_operator_boundary.get("refresh_boundary_not_forward_performance_evidence") is True
            and current_operator_boundary.get("refresh_boundary_not_promotion_readiness_evidence") is True
            and current_operator_boundary.get("refresh_boundary_not_live_profitability_evidence") is True
            and current_operator_boundary.get("refresh_boundary_not_real_money_evidence") is True
            and current_operator_boundary.get("source_freshness_generated_reference_date")
            == expected_current_operator_boundary.get("source_freshness_generated_reference_date")
            and current_operator_boundary.get("source_freshness_generated_reference_timezone")
            == expected_current_operator_boundary.get("source_freshness_generated_reference_timezone")
            and current_operator_boundary.get("source_freshness_staleness_comparison_source")
            == expected_current_operator_boundary.get("source_freshness_staleness_comparison_source")
            and current_operator_boundary.get("source_freshness_staleness_comparison_date")
            == expected_current_operator_boundary.get("source_freshness_staleness_comparison_date")
            and current_operator_boundary.get("right_now_as_of_date")
            == expected_current_operator_boundary.get("right_now_as_of_date")
            and current_operator_boundary.get("right_now_run_date")
            == expected_current_operator_boundary.get("right_now_run_date")
            and current_operator_boundary.get("open_settlement_rows")
            == expected_current_operator_boundary.get("open_settlement_rows")
            and current_operator_boundary.get("roi_complete_primary_rows")
            == expected_current_operator_boundary.get("roi_complete_primary_rows")
            and current_operator_boundary.get("first_read_threshold")
            == expected_current_operator_boundary.get("first_read_threshold")
            and current_operator_boundary.get("op_anchor_roi_complete_rows")
            == expected_current_operator_boundary.get("op_anchor_roi_complete_rows")
            and current_operator_boundary.get("cd_companion_roi_complete_rows")
            == expected_current_operator_boundary.get("cd_companion_roi_complete_rows")
            and current_operator_boundary.get("primary_rule_mix_read")
            == expected_current_operator_boundary.get("primary_rule_mix_read")
            and current_operator_boundary.get("current_settled_context_is_cd_only") is True
            and current_operator_boundary.get("latest_context_has_no_bet_recommendations")
            == expected_current_operator_boundary.get("latest_context_has_no_bet_recommendations")
            and current_operator_boundary.get("latest_context_has_no_qualifying_races")
            == expected_current_operator_boundary.get("latest_context_has_no_qualifying_races")
            and current_operator_boundary.get("latest_context_has_bet_ready_language") is False
            and str(current_operator_boundary.get("recommendation_context_read") or "")
            == str(expected_current_operator_boundary.get("recommendation_context_read") or "")
            and str(current_operator_boundary.get("open_settlement_summary") or "")
            == str(expected_current_operator_boundary.get("open_settlement_summary") or "")
            and str(current_operator_boundary.get("open_settlement_context") or "")
            == str(expected_current_operator_boundary.get("open_settlement_context") or "")
            and str(current_operator_boundary.get("open_settlement_queue_state") or "")
            == str(expected_current_operator_boundary.get("open_settlement_queue_state") or "")
            and current_operator_boundary.get("open_settlement_queue_state")
            == source_open_queue.get("open_settlement_queue_state")
            and current_operator_boundary.get("open_settlement_context")
            == source_open_queue.get("open_settlement_context")
            and current_operator_boundary.get("open_settlement_queue_read") == source_open_queue.get("detail_read")
            and "Settlement queue state:" not in str(current_operator_boundary.get("open_settlement_queue_read") or "")
            and "Open settlement queue by rule:" in str(current_operator_boundary.get("open_settlement_queue_read") or "")
            and str(current_operator_boundary.get("source_freshness_read") or "")
            == str(expected_current_operator_boundary.get("source_freshness_read") or "")
            and current_operator_boundary.get("right_now_run_date")
            and current_operator_boundary.get("right_now_as_of_date")
            and "performance evidence" in str(current_operator_boundary.get("source_freshness_read") or "")
            and current_operator_boundary.get("not_forward_performance_evidence") is True
            and current_operator_boundary.get("not_bet_readiness_evidence_by_itself") is True
            and "BAQ is not BEL" in saved_json.get("decision_read", {}).get("baq_boundary", ""),
            "json_sidecar_surface",
            "compare_main_approaches.json now matches a fresh metadata+ranked-row rebuild, carries exact source fingerprints including the current-evidence bridge, preserves the OP_DURABLE_K7 / CD_CORE_K8 paper-companion / OP_REFINED_K7 / BAQ-not-BEL decision read, inherits the forward scorecard ranking_contract, publishes machine-readable decision-gate minimums, dynamically mirrors the bridge-published all-uncleared decision_gate_progress split plus current operator_read_gate/recommendation-state/settlement-queue/operator-freshness boundary as context only, and publishes the same machine-readable evidence_boundary metadata as the generator",
        )
    )
    evidence_debt_rows = saved_json.get("method_family_evidence_debt", [])
    evidence_debt_by_family = {
        str(row.get("family")): row
        for row in evidence_debt_rows
        if isinstance(row, dict)
    }
    expected_gate_minimums = cma.load_decision_change_gate_minimums()
    selective_gate_sources = evidence_debt_by_family.get("Selective OP/CD rule path", {}).get(
        "source_gate_minimums",
        {},
    )
    checks.append(
        require(
            evidence_debt_rows == expected_json.get("method_family_evidence_debt")
            and len(evidence_debt_rows) == 3
            and set(evidence_debt_by_family) == {
                "Selective OP/CD rule path",
                "Harville-ranked probabilities",
                "Current odds-only XGBoost correction path",
            }
            and "`OP_REFINED_K7` also needs 20+ complete shadow rows before promotion review"
            in evidence_debt_by_family["Selective OP/CD rule path"].get("still_missing", "")
            and "30+ same-candidate rows before anchor displacement"
            in evidence_debt_by_family["Selective OP/CD rule path"].get("still_missing", "")
            and "100+ total ROI-complete observations before any real-money discussion"
            in evidence_debt_by_family["Selective OP/CD rule path"].get("still_missing", "")
            and selective_gate_sources == {
                "phase8_promotion_review": {
                    "minimum": expected_gate_minimums["phase8_promotion_review"][
                        "minimum_roi_complete_settled_observations"
                    ],
                    "threshold_source": expected_gate_minimums["phase8_promotion_review"]["threshold_source"],
                },
                "anchor_displacement": {
                    "minimum": expected_gate_minimums["anchor_displacement"][
                        "minimum_roi_complete_same_candidate_observations"
                    ],
                    "threshold_source": expected_gate_minimums["anchor_displacement"]["threshold_source"],
                },
                "real_money_discussion": {
                    "minimum": expected_gate_minimums["real_money_discussion"][
                        "minimum_total_settled_roi_complete_observations"
                    ],
                    "threshold_source": expected_gate_minimums["real_money_discussion"]["threshold_source"],
                },
            }
            and "clean scans, open signals, or a settlement-audit pass"
            in evidence_debt_by_family["Selective OP/CD rule path"].get("invalid_shortcut", "")
            and "`OP_DURABLE_K7` + `CD_CORE_K8` observations"
            in evidence_debt_by_family["Selective OP/CD rule path"].get("next_honest_action", "")
            and "not just broad hit-rate/calibration context"
            in evidence_debt_by_family["Harville-ranked probabilities"].get("still_missing", "")
            and "41.99% hit rate" in evidence_debt_by_family["Harville-ranked probabilities"].get("invalid_shortcut", "")
            and "future betting-evidence surface turns positive"
            in evidence_debt_by_family["Harville-ranked probabilities"].get("next_honest_action", "")
            and "materially richer non-odds feature/data class"
            in evidence_debt_by_family["Current odds-only XGBoost correction path"].get("still_missing", "")
            and "betting ROI remains -24.16%"
            in evidence_debt_by_family["Current odds-only XGBoost correction path"].get("invalid_shortcut", "")
            and "feature class changes and the betting pass-through improves"
            in evidence_debt_by_family["Current odds-only XGBoost correction path"].get("next_honest_action", "")
            and "JSON sidecar publishes machine-readable evidence_boundary metadata plus the method-family evidence-debt checklist"
            in report_text,
            "method_family_evidence_debt_json_present",
            "compare_main_approaches.json now publishes the same method-family evidence-debt checklist as the markdown, including scorecard-sourced source_gate_minimums for the selective OP/CD path, so automation can distinguish missing evidence class, invalid shortcuts, and next honest action for the selective OP/CD path, Harville, and current odds-only XGBoost without parsing prose",
        )
    )
    checks.append(
        require(
            current_operator_boundary.get("source_path") == CURRENT_EVIDENCE_JSON.name
            and current_operator_boundary.get("source_freshness_generated_reference_date")
            == expected_current_operator_boundary.get("source_freshness_generated_reference_date")
            and current_operator_boundary.get("source_freshness_generated_reference_timezone") == "America/New_York"
            and current_operator_boundary.get("source_freshness_staleness_comparison_source") == "generated_reference_date"
            and current_operator_boundary.get("source_freshness_staleness_comparison_date")
            == current_operator_boundary.get("source_freshness_generated_reference_date")
            and current_operator_boundary.get("right_now_as_of_date")
            == expected_current_operator_boundary.get("right_now_as_of_date")
            and current_operator_boundary.get("right_now_run_date")
            == expected_current_operator_boundary.get("right_now_run_date")
            and str(current_operator_boundary.get("source_freshness_read") or "")
            == str(expected_current_operator_boundary.get("source_freshness_read") or "")
            and "performance evidence" in str(current_operator_boundary.get("source_freshness_read") or ""),
            "current_operator_boundary_publishes_reference_date_fields",
            "main-comparison JSON now publishes discrete current-evidence source-freshness reference fields, proving the operator-boundary snapshot uses current_evidence_summary.json generated_reference_date in America/New_York as current/stale comparison metadata rather than relying only on prose or local generated-date context",
        )
    )
    checks.append(
        require(
            has_timezone_aware_timestamp(current_operator_boundary.get("generated_at"))
            and current_operator_boundary.get("generated_at") == expected_current_operator_boundary.get("generated_at"),
            "current_operator_boundary_generated_at_is_timezone_aware",
            f"copied current-evidence generated_at={current_operator_boundary.get('generated_at')!r} is parseable timezone-aware provenance metadata only",
        )
    )
    recommendation_context_read = str(current_operator_boundary.get("recommendation_context_read") or "")
    latest_run_context = str(current_operator_boundary.get("latest_run_context") or "")
    recommendation_context_is_api_access = any(
        token in recommendation_context_read or token in latest_run_context
        for token in ("API-access", "HTTP 403", "403 Client Error")
    )
    checks.append(
        require(
            (
                not recommendation_context_is_api_access
                or (
                    "Sidecar action: refresh_daily_wrapper_before_evidence_read" in recommendation_context_read
                    and "Recheck command: ./run_daily_portfolio_observation.sh" in recommendation_context_read
                    and "Sidecar action: refresh_daily_wrapper_before_evidence_read" in latest_run_context
                    and "Recheck command: ./run_daily_portfolio_observation.sh" in latest_run_context
                    and "Sidecar action: refresh_daily_wrapper_before_evidence_read" in report_text
                    and "Recheck command: ./run_daily_portfolio_observation.sh" in report_text
                )
            ),
            "current_operator_boundary_preserves_api_failure_action_route",
            "when the current recommendation-state context is API-access / HTTP 403 related, the main comparison JSON and markdown preserve the sidecar action plus wrapper recheck command from current_evidence_summary.json rather than keeping only a generic scanner-failure boundary",
        )
    )
    checks.append(
        require(
            current_operator_boundary.get("refresh_action_command") == "./run_daily_portfolio_observation.sh"
            and current_operator_boundary.get("refresh_required_before_right_now_instruction_use")
            == expected_current_operator_boundary.get("refresh_required_before_right_now_instruction_use")
            and current_operator_boundary.get("refresh_source_action_counts_as_current_instruction_before_refresh")
            == expected_current_operator_boundary.get("refresh_source_action_counts_as_current_instruction_before_refresh")
            and current_operator_boundary.get("refresh_can_update_operator_surfaces") is True
            and current_operator_boundary.get("refresh_can_settle_open_rows_by_itself") is False
            and current_operator_boundary.get("refresh_counts_as_roi_complete_evidence_by_itself") is False
            and current_operator_boundary.get("clean_empty_refresh_counts_as_forward_performance") is False
            and current_operator_boundary.get("missing_or_invalid_artifact_counts_as_clean_quiet_day") is False
            and "does not settle open rows" in str(current_operator_boundary.get("refresh_action_boundary_read") or "")
            and "create ROI-complete evidence" in str(current_operator_boundary.get("refresh_action_boundary_read") or "")
            and "support real-money discussion" in str(current_operator_boundary.get("refresh_action_boundary_read") or "")
            and current_operator_boundary.get("refresh_boundary_not_forward_performance_evidence") is True
            and current_operator_boundary.get("refresh_boundary_not_promotion_readiness_evidence") is True
            and current_operator_boundary.get("refresh_boundary_not_live_profitability_evidence") is True
            and current_operator_boundary.get("refresh_boundary_not_real_money_evidence") is True,
            "current_operator_boundary_publishes_refresh_action_boundary",
            "main-comparison JSON now republishes the current-evidence wrapper refresh boundary, including the wrapper command, refresh-before-use requirement, source-matched source-action-currentness branch, operator-surface update allowance, and explicit no-settlement/no-ROI/no-clean-empty-performance/no-promotion/no-live-profitability/no-real-money interpretation",
        )
    )
    scorecard_audit_route = current_operator_boundary.get("scorecard_audit_route", {})
    scorecard_audit_snapshot = scorecard_audit_route.get("gate_floor_snapshot", {})
    checks.append(
        require(
            scorecard_audit_route == source_scorecard_audit_route
            and scorecard_audit_route.get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route.get("json_path") == "scorecard_ranking_contract_audit.json"
            and scorecard_audit_route.get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route.get("gate_floor_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and scorecard_audit_route.get("valid_use") == "navigation route for scorecard gate/ranking/CI-only/timezone/no-BAQ synchronization checks"
            and scorecard_audit_snapshot.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and scorecard_audit_snapshot.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and scorecard_audit_snapshot.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and scorecard_audit_snapshot.get("real_money_no_baq_as_bel_required") is True
            and scorecard_audit_route.get("artifacts_present") is True
            and scorecard_audit_route.get("not_forward_performance_evidence") is True
            and scorecard_audit_route.get("not_settled_roi_evidence") is True
            and scorecard_audit_route.get("not_promotion_readiness_evidence") is True
            and scorecard_audit_route.get("not_live_profitability_evidence") is True
            and scorecard_audit_route.get("not_bankroll_guidance") is True
            and scorecard_audit_route.get("not_real_money_evidence") is True
            and "30/20/100 gate floors" in str(scorecard_audit_route.get("route_read") or "")
            and "OP_REFINED CI-only support context" in str(scorecard_audit_route.get("route_read") or "")
            and "generated-at timezone provenance" in str(scorecard_audit_route.get("route_read") or "")
            and "no-BAQ-as-BEL prerequisite" in str(scorecard_audit_route.get("route_read") or "")
            and "| Scorecard audit route | `current_evidence_summary.json` `scorecard_audit_route`:" in report_text,
            "current_operator_boundary_publishes_scorecard_audit_route",
            "main-comparison JSON and markdown now republish current_evidence_summary.json scorecard_audit_route so copied gate/ranking/CI-only/timezone/no-BAQ synchronization questions route to the dedicated audit without becoming forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
        )
    )
    rebuild_validation_contract = current_operator_boundary.get("rebuild_validation_contract", {})
    rebuild_order_commands = [
        str(row.get("command") or "")
        for row in rebuild_validation_contract.get("upstream_refresh_order", [])
        if isinstance(row, dict)
    ]
    checks.append(
        require(
            rebuild_validation_contract == source_rebuild_validation_contract
            and rebuild_validation_contract.get("prerequisite_rebuild_command")
            == "python3 paper_trade_settlement_audit.py"
            and rebuild_validation_contract.get("rebuild_command") == "python3 current_evidence_summary.py"
            and rebuild_validation_contract.get("direct_validation_command")
            == "python3 validate_current_evidence_summary.py"
            and rebuild_order_commands
            == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and rebuild_validation_contract.get(
                "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
            )
            is True
            and rebuild_validation_contract.get("requires_source_consistency_before_quoting_current_totals")
            is True
            and rebuild_validation_contract.get("requires_source_freshness_before_right_now_instruction_use")
            is True
            and rebuild_validation_contract.get("green_checks_are_reproducibility_metadata_only") is True
            and rebuild_validation_contract.get("upstream_refresh_order_is_provenance_metadata_only") is True
            and rebuild_validation_contract.get("not_settled_roi_or_real_money_evidence") is True
            and "| Current bridge rebuild order | `current_evidence_summary.json` `rebuild_validation_contract`:"
            in report_text
            and "`python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`"
            in report_text
            and "before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes" in report_text
            and "Provenance/rebuild route only" in report_text,
            "current_operator_boundary_publishes_rebuild_validation_contract",
            "main-comparison JSON and markdown now republish current_evidence_summary.json rebuild_validation_contract so source-byte changes route through settlement audit -> current bridge -> bridge validator before current totals are quoted, while keeping the route as provenance/rebuild metadata rather than settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
        )
    )
    checks.append(
        require(
            evidence_boundary == cma.MACHINE_READABLE_EVIDENCE_BOUNDARY
            and evidence_boundary.get("artifact_role") == "main approach comparison bundle"
            and evidence_boundary.get("valid_evidence_scope") == "frozen_main_approach_comparison_only"
            and evidence_boundary.get("not_new_forward_evidence") is True
            and evidence_boundary.get("not_live_paper_trade_ledger") is True
            and evidence_boundary.get("not_current_day_scanner_result") is True
            and evidence_boundary.get("not_settled_roi_evidence") is True
            and evidence_boundary.get("not_live_profitability_evidence") is True
            and evidence_boundary.get("not_real_money_evidence") is True
            and evidence_boundary.get("not_promotion_readiness_evidence") is True
            and evidence_boundary.get("current_operator_boundary_snapshot_is_context_only") is True
            and evidence_boundary.get("current_operator_routing_requires_combined_route") is True
            and "operator_read_gate" in evidence_boundary.get("current_operator_routing_fields", [])
            and evidence_boundary.get("source_fingerprints_are_reproducibility_metadata_only") is True
            and evidence_boundary.get("row_identical_source_byte_drift_is_provenance_only") is True
            and evidence_boundary.get("decision_gates_are_forward_observation_requirements_not_current_evidence") is True
            and "ROI-complete settled paper rows" in evidence_boundary.get("stronger_forward_confidence_requires", [])
            and "combined operator_status_context/source_freshness/operator_read_gate route" in str(saved_json.get("evidence_boundary_text") or "")
            and "operator_read_gate" in " ".join(evidence_boundary.get("non_goals", []))
            and "do not promote OP_REFINED_K7 or Phase 8 from this artifact" in evidence_boundary.get("non_goals", [])
            and "do not reopen current odds-only XGBoost from this artifact" in evidence_boundary.get("non_goals", [])
            and "do not treat Harville benchmark-only output as a live approach" in evidence_boundary.get("non_goals", [])
            and "do not substitute BAQ for BEL" in evidence_boundary.get("non_goals", [])
            and "- `valid_evidence_scope=frozen_main_approach_comparison_only`" in report_text
            and "quote current `PAPER_TRADE_NOW` instructions without the combined `CURRENT_EVIDENCE_SUMMARY.md` / `operator_status_context` / `source_freshness` / `operator_read_gate` route" in report_text,
            "compare_main_approaches_json_publishes_machine_readable_evidence_boundary",
            "main comparison JSON now publishes a machine-readable evidence_boundary block and matching prose boundary with exact valid_evidence_scope=frozen_main_approach_comparison_only wording that keep frozen comparison rows, source fingerprints, the current operator-boundary snapshot including the combined operator_status_context/source_freshness/operator_read_gate route, row-identical byte-drift checks, and decision gates separate from new forward evidence, live paper ledgers, scanner output, settled ROI, live profitability, promotion readiness, real-money evidence, OP_REFINED_K7 / Phase 8 promotion, odds-only XGBoost reopening, Harville live treatment, and BAQ/BEL substitution",
        )
    )
    gate_minimums = saved_json.get("decision_change_gate_minimums", {})
    checks.append(
        require(
            gate_minimums == cma.load_decision_change_gate_minimums()
            and gate_minimums.get("phase8_promotion_review", {}).get("minimum_roi_complete_settled_observations") == 20
            and gate_minimums.get("anchor_displacement", {}).get("minimum_roi_complete_same_candidate_observations") == 30
            and gate_minimums.get("real_money_discussion", {}).get("minimum_total_settled_roi_complete_observations") == 100
            and "promotion-review discussion only" in gate_minimums.get("phase8_promotion_review", {}).get("gate_role", "")
            and "replacing OP_DURABLE_K7" in gate_minimums.get("anchor_displacement", {}).get("gate_role", "")
            and "no BAQ-as-BEL substitution" in gate_minimums.get("real_money_discussion", {}).get("also_requires", [])
            and gate_minimums.get("phase8_promotion_review", {}).get("threshold_source") == "forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations"
            and gate_minimums.get("anchor_displacement", {}).get("threshold_source") == "forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations"
            and gate_minimums.get("real_money_discussion", {}).get("threshold_source") == "forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi"
            and "Machine-readable threshold summary (also copied into the JSON sidecar): anchor_displacement=30 ROI-complete same-candidate observations; phase8_promotion_review=20 ROI-complete shadow observations; real_money_discussion=100 total settled observations with usable ROI." in report_text
            and "Threshold source: `forward_evidence_scorecard.json` `decision_gate_minimums`; the JSON sidecar records the exact source key for `phase8_promotion_review`, `anchor_displacement`, and `real_money_discussion`." in report_text,
            "decision_gate_minimums_json_present",
            "main comparison JSON now publishes machine-readable decision-gate minimums sourced directly from forward_evidence_scorecard.json, with exact threshold_source keys that separate 20 ROI-complete shadow observations for Phase 8 promotion review from 30 same-candidate observations for OP_DURABLE_K7 anchor displacement and 100 total settled ROI-complete observations before any real-money discussion",
        )
    )
    scorecard_gate_minimums = scorecard_json.get("decision_gate_minimums", {})
    compare_gate_thresholds = {
        "phase8_promotion_review": gate_minimums.get("phase8_promotion_review", {}).get("minimum_roi_complete_settled_observations"),
        "anchor_displacement": gate_minimums.get("anchor_displacement", {}).get("minimum_roi_complete_same_candidate_observations"),
        "real_money_discussion": gate_minimums.get("real_money_discussion", {}).get("minimum_total_settled_roi_complete_observations"),
    }
    scorecard_gate_thresholds = {
        "phase8_promotion_review": scorecard_gate_minimums.get("phase8_promotion_review", {}).get("min_roi_complete_settled_observations"),
        "anchor_displacement": scorecard_gate_minimums.get("anchor_displacement", {}).get("min_roi_complete_settled_observations"),
        "real_money_discussion": scorecard_gate_minimums.get("real_money_discussion", {}).get("min_total_settled_observations_with_usable_roi"),
    }
    checks.append(
        require(
            "frozen 2024-2025 holdout" in str(scorecard_json.get("source_scope", ""))
            and compare_gate_thresholds == scorecard_gate_thresholds == {
                "phase8_promotion_review": 20,
                "anchor_displacement": 30,
                "real_money_discussion": 100,
            }
            and "no BAQ-as-BEL substitution" in gate_minimums.get("real_money_discussion", {}).get("also_requires", [])
            and "no BAQ-as-BEL substitution" in scorecard_gate_minimums.get("real_money_discussion", {}).get("also_requires", [])
            and "not_live_paper_trade_ledger" in str(scorecard_json.get("evidence_boundary", ""))
            and "not a live paper-trade ledger" in str(scorecard_json.get("evidence_boundary_text", ""))
            and "does not consume current-day scanner" in str(scorecard_json.get("evidence_boundary_text", "")),
            "decision_gate_minimums_match_scorecard_json",
            "main-comparison decision_change_gate_minimums now source-match the scorecard JSON's 20 Phase 8 promotion-review / 30 anchor-displacement / 100 real-money-discussion gate thresholds, with both artifacts preserving the no-BAQ-as-BEL real-money prerequisite and non-live-evidence boundary",
        )
    )
    scorecard_ranking_contract = scorecard_json.get("ranking_contract", {})
    checks.append(
        require(
            saved_json.get("scorecard_ranking_contract") == scorecard_ranking_contract
            and saved_json.get("scorecard_ranking_contract_read") == "rank is tier-first conservative decision order; raw forward_trust/Score is evidence support inside posture, not an automatic promotion queue"
            and scorecard_ranking_contract.get("rank_is_tier_first_decision_order") is True
            and scorecard_ranking_contract.get("forward_trust_is_secondary_within_tier") is True
            and scorecard_ranking_contract.get("raw_score_is_not_an_automatic_deployment_instruction") is True
            and "CD_CORE_K8 ranks ahead of OP_REFINED_K7" in scorecard_ranking_contract.get("known_rank_override", "")
            and "Inherited scorecard ranking contract: rank is tier-first" in report_text
            and "Scorecard rank contract inherited: CD_CORE_K8 ranks ahead of OP_REFINED_K7" in report_text
            and "The inherited scorecard contract says: CD_CORE_K8 ranks ahead of OP_REFINED_K7" in report_text,
            "scorecard_ranking_contract_inherited",
            "main comparison now consumes forward_evidence_scorecard.json ranking_contract so deployment posture remains tier-first and OP_REFINED_K7's hotter raw score cannot become an automatic promotion cue above CD_CORE_K8 or OP_DURABLE_K7",
        )
    )

    with tempfile.TemporaryDirectory(prefix="compare_main_cli_", dir=tmp_parent) as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        pinned_dir = tmpdir / "pinned_out"
        pinned_csv = pinned_dir / "main_compare.csv"
        pinned_md = pinned_dir / "main_compare.md"
        pinned_json = pinned_dir / "main_compare.json"
        alt_cache = tmpdir / "alt_phase5_race_cache.pkl"
        alt_phase7_rules = tmpdir / "alt_phase7_live_rules.json"
        alt_wf_folds = tmpdir / "alt_walk_forward_validation_folds.csv"
        alt_wf_rules = tmpdir / "alt_walk_forward_validation_rules.csv"
        alt_scorecard = tmpdir / "alt_forward_evidence_scorecard.csv"
        alt_scorecard_json = tmpdir / "alt_forward_evidence_scorecard.json"
        custom_cross_family = tmpdir / "custom_cross_family_decision_card.csv"
        custom_scorecard = tmpdir / "custom_forward_evidence_scorecard.csv"
        custom_scorecard_json = tmpdir / "custom_forward_evidence_scorecard.json"
        alt_backtest = tmpdir / "alt_backtest_summary.csv"
        alt_ab_results = tmpdir / "alt_ab_downstream_comparison_results.json"
        custom_csv = tmpdir / "custom_main_compare.csv"
        custom_md = tmpdir / "custom_main_compare.md"
        custom_json = tmpdir / "custom_main_compare.json"
        missing_scorecard = tmpdir / "missing_scorecard.csv"
        missing_gate_minimum_json = tmpdir / "missing_gate_minimum_scorecard.json"
        missing_gate_output_dir = tmpdir / "missing_gate_should_not_exist"
        missing_gate_should_not_write_csv = missing_gate_output_dir / "missing_gate_main_compare.csv"
        missing_gate_should_not_write_md = missing_gate_output_dir / "missing_gate_main_compare.md"
        missing_gate_should_not_write_json = missing_gate_output_dir / "missing_gate_main_compare.json"
        missing_no_baq_gate_json = tmpdir / "missing_no_baq_gate_scorecard.json"
        missing_no_baq_gate_output_dir = tmpdir / "missing_no_baq_gate_should_not_exist"
        missing_no_baq_gate_should_not_write_csv = (
            missing_no_baq_gate_output_dir / "missing_no_baq_gate_main_compare.csv"
        )
        missing_no_baq_gate_should_not_write_md = (
            missing_no_baq_gate_output_dir / "missing_no_baq_gate_main_compare.md"
        )
        missing_no_baq_gate_should_not_write_json = (
            missing_no_baq_gate_output_dir / "missing_no_baq_gate_main_compare.json"
        )
        nonpositive_phase8_gate_json = tmpdir / "nonpositive_phase8_gate_scorecard.json"
        nonpositive_phase8_gate_output_dir = tmpdir / "nonpositive_phase8_gate_should_not_exist"
        nonpositive_phase8_gate_should_not_write_csv = (
            nonpositive_phase8_gate_output_dir / "nonpositive_phase8_gate_main_compare.csv"
        )
        nonpositive_phase8_gate_should_not_write_md = (
            nonpositive_phase8_gate_output_dir / "nonpositive_phase8_gate_main_compare.md"
        )
        nonpositive_phase8_gate_should_not_write_json = (
            nonpositive_phase8_gate_output_dir / "nonpositive_phase8_gate_main_compare.json"
        )
        nonpositive_real_money_gate_json = tmpdir / "nonpositive_real_money_gate_scorecard.json"
        nonpositive_real_money_gate_output_dir = tmpdir / "nonpositive_real_money_gate_should_not_exist"
        nonpositive_real_money_gate_should_not_write_csv = (
            nonpositive_real_money_gate_output_dir / "nonpositive_real_money_gate_main_compare.csv"
        )
        nonpositive_real_money_gate_should_not_write_md = (
            nonpositive_real_money_gate_output_dir / "nonpositive_real_money_gate_main_compare.md"
        )
        nonpositive_real_money_gate_should_not_write_json = (
            nonpositive_real_money_gate_output_dir / "nonpositive_real_money_gate_main_compare.json"
        )
        changed_gate_minimum_json = tmpdir / "changed_gate_minimum_scorecard.json"
        changed_gate_csv = tmpdir / "changed_gate_main_compare.csv"
        changed_gate_md = tmpdir / "changed_gate_main_compare.md"
        changed_gate_json = tmpdir / "changed_gate_main_compare.json"
        bad_current_evidence_json = tmpdir / "bad_generated_at_current_evidence_summary.json"
        bad_current_evidence_output_dir = tmpdir / "bad_current_evidence_nested_output" / "artifacts"
        bad_current_evidence_should_not_write_csv = (
            bad_current_evidence_output_dir / "bad_current_evidence_should_not_write.csv"
        )
        bad_current_evidence_should_not_write_md = (
            bad_current_evidence_output_dir / "bad_current_evidence_should_not_write.md"
        )
        bad_current_evidence_should_not_write_json = (
            bad_current_evidence_output_dir / "bad_current_evidence_should_not_write.json"
        )
        missing_rebuild_contract_json = tmpdir / "missing_rebuild_contract_current_evidence_summary.json"
        missing_rebuild_contract_output_dir = tmpdir / "missing_rebuild_contract_nested_output" / "artifacts"
        missing_rebuild_contract_should_not_write_csv = (
            missing_rebuild_contract_output_dir / "missing_rebuild_contract_should_not_write.csv"
        )
        missing_rebuild_contract_should_not_write_md = (
            missing_rebuild_contract_output_dir / "missing_rebuild_contract_should_not_write.md"
        )
        missing_rebuild_contract_should_not_write_json = (
            missing_rebuild_contract_output_dir / "missing_rebuild_contract_should_not_write.json"
        )
        weakened_rebuild_contract_json = tmpdir / "weakened_rebuild_contract_current_evidence_summary.json"
        weakened_rebuild_contract_output_dir = tmpdir / "weakened_rebuild_contract_nested_output" / "artifacts"
        weakened_rebuild_contract_should_not_write_csv = (
            weakened_rebuild_contract_output_dir / "weakened_rebuild_contract_should_not_write.csv"
        )
        weakened_rebuild_contract_should_not_write_md = (
            weakened_rebuild_contract_output_dir / "weakened_rebuild_contract_should_not_write.md"
        )
        weakened_rebuild_contract_should_not_write_json = (
            weakened_rebuild_contract_output_dir / "weakened_rebuild_contract_should_not_write.json"
        )
        missing_source_freshness_json = tmpdir / "missing_source_freshness_current_evidence_summary.json"
        missing_source_freshness_output_dir = tmpdir / "missing_source_freshness_nested_output" / "artifacts"
        missing_source_freshness_should_not_write_csv = (
            missing_source_freshness_output_dir / "missing_source_freshness_should_not_write.csv"
        )
        missing_source_freshness_should_not_write_md = (
            missing_source_freshness_output_dir / "missing_source_freshness_should_not_write.md"
        )
        missing_source_freshness_should_not_write_json = (
            missing_source_freshness_output_dir / "missing_source_freshness_should_not_write.json"
        )
        missing_operator_read_gate_json = tmpdir / "missing_operator_read_gate_current_evidence_summary.json"
        missing_operator_read_gate_output_dir = (
            tmpdir / "missing_operator_read_gate_nested_output" / "artifacts"
        )
        missing_operator_read_gate_should_not_write_csv = (
            missing_operator_read_gate_output_dir / "missing_operator_read_gate_should_not_write.csv"
        )
        missing_operator_read_gate_should_not_write_md = (
            missing_operator_read_gate_output_dir / "missing_operator_read_gate_should_not_write.md"
        )
        missing_operator_read_gate_should_not_write_json = (
            missing_operator_read_gate_output_dir / "missing_operator_read_gate_should_not_write.json"
        )
        missing_refresh_action_boundary_field_json = (
            tmpdir / "missing_refresh_action_boundary_field_current_evidence_summary.json"
        )
        missing_refresh_action_boundary_field_output_dir = (
            tmpdir / "missing_refresh_action_boundary_field_nested_output" / "artifacts"
        )
        missing_refresh_action_boundary_field_should_not_write_csv = (
            missing_refresh_action_boundary_field_output_dir
            / "missing_refresh_action_boundary_field_should_not_write.csv"
        )
        missing_refresh_action_boundary_field_should_not_write_md = (
            missing_refresh_action_boundary_field_output_dir
            / "missing_refresh_action_boundary_field_should_not_write.md"
        )
        missing_refresh_action_boundary_field_should_not_write_json = (
            missing_refresh_action_boundary_field_output_dir
            / "missing_refresh_action_boundary_field_should_not_write.json"
        )
        false_refresh_accounting_json = tmpdir / "false_refresh_accounting_current_evidence_summary.json"
        false_refresh_accounting_output_dir = tmpdir / "false_refresh_accounting_nested_output" / "artifacts"
        false_refresh_accounting_should_not_write_csv = (
            false_refresh_accounting_output_dir / "false_refresh_accounting_should_not_write.csv"
        )
        false_refresh_accounting_should_not_write_md = (
            false_refresh_accounting_output_dir / "false_refresh_accounting_should_not_write.md"
        )
        false_refresh_accounting_should_not_write_json = (
            false_refresh_accounting_output_dir / "false_refresh_accounting_should_not_write.json"
        )
        missing_wf_rules = tmpdir / "missing_op_switch_rules.csv"
        for src in [
            COMPARE_SCRIPT,
            METHOD_FAMILY_SCRIPT,
            CROSS_FAMILY_CSV,
            PHASE5_CACHE,
            PHASE7_RULES,
            WF_FOLDS,
            WF_RULES,
            BACKTEST_SUMMARY,
            AB_RESULTS,
            cma.SCORECARD_CSV,
            cma.SCORECARD_JSON,
            CURRENT_EVIDENCE_JSON,
        ]:
            shutil.copy2(src, tmpdir / src.name)
        shutil.copy2(PHASE5_CACHE, alt_cache)
        shutil.copy2(PHASE7_RULES, alt_phase7_rules)
        shutil.copy2(WF_FOLDS, alt_wf_folds)
        shutil.copy2(WF_RULES, alt_wf_rules)
        shutil.copy2(cma.SCORECARD_CSV, alt_scorecard)
        shutil.copy2(cma.SCORECARD_JSON, alt_scorecard_json)
        shutil.copy2(BACKTEST_SUMMARY, alt_backtest)
        shutil.copy2(AB_RESULTS, alt_ab_results)
        cli_result = subprocess.run(
            [sys.executable, COMPARE_SCRIPT.name],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        cli_csv = pd.read_csv(tmpdir / COMPARE_CSV.name)
        compare_like_saved(saved_df, cli_csv)
        cli_report_text = (tmpdir / COMPARE_MD.name).read_text(encoding="utf-8")
        cli_runtime_match = re.search(r"^- Runtime: ([0-9]+(?:\.[0-9]+)?) seconds$", cli_report_text, flags=re.MULTILINE)
        if cli_runtime_match is None:
            raise AssertionError("CLI-generated compare_main_approaches.md is missing its runtime line")
        cli_runtime_sec = float(cli_runtime_match.group(1))
        cli_rebuilt_md = cma.build_report(
            rebuilt_df,
            HOLDOUT_YEARS,
            wf_years,
            cli_runtime_sec,
            cma.load_method_family_rows(),
        )
        if cli_report_text.strip() != cli_rebuilt_md.strip():
            raise AssertionError("CLI-generated compare_main_approaches.md drifted from a fresh rebuild")
        expected_cli_stdout = build_expected_cli_stdout(cli_report_text)
        if cli_result.stdout != expected_cli_stdout:
            raise AssertionError("compare_main_approaches.py CLI stdout no longer matches its generated report plus save notices")

        pinned_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--runtime-sec",
                f"{saved_runtime_sec}",
                "--cache-path",
                str(alt_cache),
                "--phase7-rules",
                str(alt_phase7_rules),
                "--wf-folds",
                str(alt_wf_folds),
                "--wf-rules",
                str(alt_wf_rules),
                "--scorecard-csv",
                str(alt_scorecard),
                "--scorecard-json",
                str(alt_scorecard_json),
                "--csv-output",
                str(pinned_csv),
                "--md-output",
                str(pinned_md),
                "--json-output",
                str(pinned_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        pinned_csv_df = pd.read_csv(pinned_csv)
        compare_like_saved(saved_df, pinned_csv_df)
        pinned_report_text = pinned_md.read_text(encoding="utf-8")
        pinned_rebuilt_md = cma.build_report(
            rebuilt_df,
            HOLDOUT_YEARS,
            wf_years,
            saved_runtime_sec,
            cma.load_method_family_rows(),
            csv_output_name=pinned_csv.name,
            md_output_name=pinned_md.name,
            json_output_name=pinned_json.name,
            scorecard_csv=alt_scorecard,
            scorecard_json=alt_scorecard_json,
            source_paths={
                "phase5_race_cache": alt_cache,
                "phase7_live_rules": alt_phase7_rules,
                "walk_forward_folds": alt_wf_folds,
                "walk_forward_rules": alt_wf_rules,
                "forward_evidence_scorecard": alt_scorecard,
                "forward_evidence_scorecard_json": alt_scorecard_json,
            },
        )
        if pinned_report_text.strip() != pinned_rebuilt_md.strip():
            raise AssertionError("Pinned/custom-output compare_main_approaches.md drifted from a fresh rebuild")
        pinned_json_payload = json.loads(pinned_json.read_text(encoding="utf-8"))
        expected_pinned_json = cma.build_json_payload(
            rebuilt_df,
            HOLDOUT_YEARS,
            wf_years,
            saved_runtime_sec,
            cma.load_method_family_rows(compare_rows=rebuilt_df.to_dict(orient="records")),
            csv_output_name=pinned_csv.name,
            md_output_name=pinned_md.name,
            json_output_name=pinned_json.name,
            source_paths={
                "phase5_race_cache": alt_cache,
                "phase7_live_rules": alt_phase7_rules,
                "walk_forward_folds": alt_wf_folds,
                "walk_forward_rules": alt_wf_rules,
                "forward_evidence_scorecard": alt_scorecard,
                "forward_evidence_scorecard_json": alt_scorecard_json,
            },
            scorecard_json=alt_scorecard_json,
        )
        if pinned_json_payload != expected_pinned_json:
            raise AssertionError("Pinned/custom-output compare_main_approaches.json drifted from a fresh sidecar rebuild")
        expected_pinned_stdout = build_expected_cli_stdout(
            pinned_report_text,
            csv_name=pinned_csv.name,
            md_name=pinned_md.name,
            json_name=pinned_json.name,
        )
        if pinned_result.stdout != expected_pinned_stdout:
            raise AssertionError("Pinned/custom-output compare_main_approaches.py CLI stdout no longer matches its generated report plus save notices")

        custom_hierarchy = {
            "LIVE_DEFAULT": "ALT_ANCHOR_K7",
            "PRIMARY_SHADOW": "ALT_PAPER_COMPANION_K8",
            "SECONDARY_SHADOW": "ALT_CLOSEST_SHADOW_K7",
        }
        custom_cross_df = pd.read_csv(tmpdir / CROSS_FAMILY_CSV.name)
        for shadow_rank, rule_id in custom_hierarchy.items():
            custom_cross_df.loc[custom_cross_df["shadow_rank"] == shadow_rank, "rule_id"] = rule_id
        custom_cross_df.to_csv(custom_cross_family, index=False)

        custom_scorecard_df = pd.read_csv(alt_scorecard)
        custom_scorecard_rows = []
        for source_rule, custom_rule in [
            ("OP_DURABLE_K7", "ALT_ANCHOR_K7"),
            ("CD_CORE_K8", "ALT_PAPER_COMPANION_K8"),
            ("OP_REFINED_K7", "ALT_CLOSEST_SHADOW_K7"),
        ]:
            source_rows = custom_scorecard_df[custom_scorecard_df["rule_id"] == source_rule]
            if source_rows.empty:
                raise AssertionError(f"fixture scorecard is missing source row {source_rule}")
            row = source_rows.iloc[0].copy()
            row["rule_id"] = custom_rule
            custom_scorecard_rows.append(row)
        custom_scorecard_df = pd.concat([custom_scorecard_df, pd.DataFrame(custom_scorecard_rows)], ignore_index=True)
        custom_scorecard_df.to_csv(custom_scorecard, index=False)
        custom_scorecard_json_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        source_diagnostic = custom_scorecard_json_payload["ci_only_promotion_diagnostics"]["OP_REFINED_K7"]
        custom_diagnostic = dict(source_diagnostic)
        custom_diagnostic["candidate_rule_id"] = "ALT_CLOSEST_SHADOW_K7"
        custom_diagnostic["current_anchor_rule_id"] = "ALT_ANCHOR_K7"
        custom_scorecard_json_payload["ci_only_promotion_diagnostics"][
            "ALT_CLOSEST_SHADOW_K7"
        ] = custom_diagnostic
        custom_scorecard_json.write_text(
            json.dumps(custom_scorecard_json_payload, indent=2) + "\n",
            encoding="utf-8",
        )

        custom_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--runtime-sec",
                f"{saved_runtime_sec}",
                "--scorecard-csv",
                str(custom_scorecard),
                "--scorecard-json",
                str(custom_scorecard_json),
                "--cross-family-csv",
                str(custom_cross_family),
                "--backtest-csv",
                str(alt_backtest),
                "--ab-json",
                str(alt_ab_results),
                "--csv-output",
                str(custom_csv),
                "--md-output",
                str(custom_md),
                "--json-output",
                str(custom_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        custom_csv_df = pd.read_csv(custom_csv)
        compare_like_saved(saved_df, custom_csv_df)
        custom_report_text = custom_md.read_text(encoding="utf-8")
        custom_json_payload = json.loads(custom_json.read_text(encoding="utf-8"))
        expected_custom_stdout = build_expected_cli_stdout(
            custom_report_text,
            csv_name=custom_csv.name,
            md_name=custom_md.name,
            json_name=custom_json.name,
        )
        if custom_result.stdout != expected_custom_stdout:
            raise AssertionError("Custom source-path compare_main_approaches.py CLI stdout no longer matches its generated report plus save notices")
        checks.append(
            require(
                "`ALT_ANCHOR_K7` remains the safest anchor" in custom_report_text
                and "`ALT_PAPER_COMPANION_K8` is the primary OP/CD paper-basket companion" in custom_report_text
                and "`ALT_CLOSEST_SHADOW_K7` remains the narrower same-family OP shadow challenger" in custom_report_text
                and f"`{custom_cross_family.name}`" in custom_report_text
                and f"`{custom_scorecard.name}`" in custom_report_text
                and "Scorecard diagnostic source: `custom_forward_evidence_scorecard.json:ci_only_promotion_diagnostics.ALT_CLOSEST_SHADOW_K7` (`ci_only_promotion_allowed=false`)." in custom_report_text
                and f"`{alt_backtest.name}`" in custom_report_text
                and f"`{alt_ab_results.name}`" in custom_report_text
                and custom_json_payload["decision_read"]["active_anchor"] == "ALT_ANCHOR_K7"
                and custom_json_payload["decision_read"]["paper_companion"] == "ALT_PAPER_COMPANION_K8"
                and custom_json_payload["decision_read"]["closest_shadow"] == "ALT_CLOSEST_SHADOW_K7"
                and custom_json_payload["method_family_roles"]["selective_rule_path"]["current_anchor"] == "ALT_ANCHOR_K7"
                and custom_json_payload["method_family_roles"]["selective_rule_path"]["primary_companion"] == "ALT_PAPER_COMPANION_K8"
                and custom_json_payload["method_family_roles"]["selective_rule_path"]["secondary_shadow"] == "ALT_CLOSEST_SHADOW_K7"
                and custom_json_payload["source_files"]["forward_evidence_scorecard"]["path"] == custom_scorecard.name
                and custom_json_payload["source_files"]["forward_evidence_scorecard_json"]["path"] == custom_scorecard_json.name
                and custom_json_payload["op_challenger_diagnostic"]["scorecard_ci_only_diagnostic_source"] == "custom_forward_evidence_scorecard.json:ci_only_promotion_diagnostics.ALT_CLOSEST_SHADOW_K7"
                and custom_json_payload["op_challenger_diagnostic"]["scorecard_ci_only_promotion_diagnostic"] == custom_diagnostic
                and custom_json_payload["source_files"]["cross_family_decision_card"]["path"] == custom_cross_family.name
                and custom_json_payload["source_files"]["backtest_summary"]["path"] == alt_backtest.name
                and custom_json_payload["source_files"]["ab_downstream_comparison_results"]["path"] == alt_ab_results.name
                and custom_json_payload["ranked_rows"] == pinned_json_payload["ranked_rows"],
                "custom_method_family_source_paths_rerender_dynamically",
                "custom scorecard, scorecard-ranking JSON, cross-family, backtest, and downstream A/B source paths now rerender the main-comparison hierarchy labels, source provenance, JSON decision_read/method-family roles, and CLI stdout without changing ranked comparison rows",
            )
        )

        source_drift_before = cma.file_fingerprint(alt_scorecard)
        source_drift_before_row = cma.format_source_fingerprint_row("forward_evidence_scorecard", source_drift_before)
        with alt_scorecard.open("a", encoding="utf-8", newline="") as handle:
            handle.write("\n")
        source_drift_after = cma.file_fingerprint(alt_scorecard)
        source_drift_after_row = cma.format_source_fingerprint_row("forward_evidence_scorecard", source_drift_after)
        drift_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--runtime-sec",
                f"{saved_runtime_sec}",
                "--cache-path",
                str(alt_cache),
                "--phase7-rules",
                str(alt_phase7_rules),
                "--wf-folds",
                str(alt_wf_folds),
                "--wf-rules",
                str(alt_wf_rules),
                "--scorecard-csv",
                str(alt_scorecard),
                "--scorecard-json",
                str(alt_scorecard_json),
                "--csv-output",
                str(pinned_csv),
                "--md-output",
                str(pinned_md),
                "--json-output",
                str(pinned_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        drift_csv_df = pd.read_csv(pinned_csv)
        compare_like_saved(saved_df, drift_csv_df)
        drift_report_text = pinned_md.read_text(encoding="utf-8")
        drift_json_payload = json.loads(pinned_json.read_text(encoding="utf-8"))
        expected_drift_stdout = build_expected_cli_stdout(
            drift_report_text,
            csv_name=pinned_csv.name,
            md_name=pinned_md.name,
            json_name=pinned_json.name,
        )
        if drift_result.stdout != expected_drift_stdout:
            raise AssertionError("Row-identical source-byte drift stdout no longer matches its generated report plus save notices")
        checks.append(
            require(
                source_drift_before["sha256"] != source_drift_after["sha256"]
                and source_drift_before["bytes"] != source_drift_after["bytes"]
                and source_drift_before_row in pinned_report_text
                and source_drift_after_row in drift_report_text
                and source_drift_before_row not in drift_report_text
                and pinned_json_payload["source_files"]["forward_evidence_scorecard"] == source_drift_before
                and drift_json_payload["source_files"]["forward_evidence_scorecard"] == source_drift_after
                and pinned_json_payload["ranked_rows"] == drift_json_payload["ranked_rows"]
                and strip_source_provenance_section(pinned_report_text).strip() == strip_source_provenance_section(drift_report_text).strip(),
                "source_byte_drift_updates_provenance_only",
                "row-identical scorecard source-byte drift changes the compare-main source fingerprint row plus JSON sidecar provenance, while the comparison CSV, JSON ranked rows, and report body outside Source Provenance stay unchanged",
            )
        )

        rejected_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--holdout-years",
                "2023",
                "2024",
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if rejected_result.returncode == 0:
            raise AssertionError("compare_main_approaches.py unexpectedly accepted a non-frozen holdout window")
        rejection_text = (rejected_result.stderr or rejected_result.stdout).strip()
        if "intentionally locked to the frozen 2024-2025 holdout standard" not in rejection_text:
            raise AssertionError("compare_main_approaches.py rejection message no longer explains the frozen 2024-2025 holdout lock")

        missing_scorecard_df = pd.read_csv(alt_scorecard)
        missing_scorecard_df = missing_scorecard_df[missing_scorecard_df["rule_id"] != "OP_REFINED_K7"].copy()
        missing_scorecard_df.to_csv(missing_scorecard, index=False)
        missing_scorecard_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--scorecard-csv",
                str(missing_scorecard),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_scorecard_result.returncode == 0:
            raise AssertionError("compare_main_approaches.py unexpectedly accepted a scorecard missing OP_REFINED_K7")
        missing_scorecard_text = f"{missing_scorecard_result.stdout}\n{missing_scorecard_result.stderr}"
        if "missing required scorecard rows: OP_REFINED_K7" not in missing_scorecard_text:
            raise AssertionError("scorecard-row failure no longer explains that OP_REFINED_K7 is required for the comparison ladder")

        missing_gate_minimum_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        del missing_gate_minimum_payload["decision_gate_minimums"]["anchor_displacement"][
            "min_roi_complete_settled_observations"
        ]
        missing_gate_minimum_json.write_text(
            json.dumps(missing_gate_minimum_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_gate_minimum_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--scorecard-json",
                str(missing_gate_minimum_json),
                "--csv-output",
                str(missing_gate_should_not_write_csv),
                "--md-output",
                str(missing_gate_should_not_write_md),
                "--json-output",
                str(missing_gate_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_gate_minimum_result.returncode == 0:
            raise AssertionError("compare_main_approaches.py unexpectedly accepted a scorecard JSON missing a decision_gate_minimums threshold")
        missing_gate_minimum_text = f"{missing_gate_minimum_result.stdout}\n{missing_gate_minimum_result.stderr}"
        if "JSON path must be a positive integer: decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations" not in missing_gate_minimum_text:
            raise AssertionError("scorecard gate-minimum failure no longer names the missing anchor_displacement threshold")
        if (
            missing_gate_output_dir.exists()
            or missing_gate_should_not_write_csv.exists()
            or missing_gate_should_not_write_md.exists()
            or missing_gate_should_not_write_json.exists()
        ):
            raise AssertionError("missing scorecard gate failure created partial compare-main output paths before failing")
        checks.append(
            require(
                True,
                "missing_scorecard_gate_minimum_fails_fast",
                "compare_main_approaches.py now fails fast without creating output directories or writing artifacts when forward_evidence_scorecard.json is missing a required decision_gate_minimums threshold, so the main comparison cannot silently fall back to local gate-threshold literals",
            )
        )

        missing_no_baq_gate_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        missing_no_baq_gate_payload["decision_gate_minimums"]["real_money_discussion"]["also_requires"] = [
            item
            for item in missing_no_baq_gate_payload["decision_gate_minimums"]["real_money_discussion"][
                "also_requires"
            ]
            if item != "no BAQ-as-BEL substitution"
        ]
        missing_no_baq_gate_json.write_text(
            json.dumps(missing_no_baq_gate_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_no_baq_gate_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--scorecard-json",
                str(missing_no_baq_gate_json),
                "--csv-output",
                str(missing_no_baq_gate_should_not_write_csv),
                "--md-output",
                str(missing_no_baq_gate_should_not_write_md),
                "--json-output",
                str(missing_no_baq_gate_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_no_baq_gate_result.returncode == 0:
            raise AssertionError("compare_main_approaches.py unexpectedly accepted a scorecard JSON missing the no-BAQ-as-BEL prerequisite")
        missing_no_baq_gate_text = f"{missing_no_baq_gate_result.stdout}\n{missing_no_baq_gate_result.stderr}"
        if "JSON path must include no BAQ-as-BEL substitution: decision_gate_minimums.real_money_discussion.also_requires" not in missing_no_baq_gate_text:
            raise AssertionError("scorecard no-BAQ prerequisite failure no longer names the real_money_discussion requirement")
        if (
            missing_no_baq_gate_output_dir.exists()
            or missing_no_baq_gate_should_not_write_csv.exists()
            or missing_no_baq_gate_should_not_write_md.exists()
            or missing_no_baq_gate_should_not_write_json.exists()
        ):
            raise AssertionError("missing no-BAQ scorecard gate failure created partial compare-main output paths before failing")
        checks.append(
            require(
                True,
                "missing_scorecard_no_baq_prerequisite_fails_fast",
                "compare_main_approaches.py now fails fast without creating output directories or writing artifacts when forward_evidence_scorecard.json real_money_discussion.also_requires loses the no-BAQ-as-BEL prerequisite",
            )
        )

        nonpositive_phase8_gate_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        nonpositive_phase8_gate_payload["decision_gate_minimums"]["phase8_promotion_review"][
            "min_roi_complete_settled_observations"
        ] = 0
        nonpositive_phase8_gate_json.write_text(
            json.dumps(nonpositive_phase8_gate_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        nonpositive_phase8_gate_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--scorecard-json",
                str(nonpositive_phase8_gate_json),
                "--csv-output",
                str(nonpositive_phase8_gate_should_not_write_csv),
                "--md-output",
                str(nonpositive_phase8_gate_should_not_write_md),
                "--json-output",
                str(nonpositive_phase8_gate_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if nonpositive_phase8_gate_result.returncode == 0:
            raise AssertionError("compare_main_approaches.py unexpectedly accepted a non-positive Phase 8 scorecard gate floor")
        nonpositive_phase8_gate_text = f"{nonpositive_phase8_gate_result.stdout}\n{nonpositive_phase8_gate_result.stderr}"
        if "JSON path must be a positive integer: decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations" not in nonpositive_phase8_gate_text:
            raise AssertionError("non-positive Phase 8 scorecard gate failure no longer names the malformed threshold")
        if (
            nonpositive_phase8_gate_output_dir.exists()
            or nonpositive_phase8_gate_should_not_write_csv.exists()
            or nonpositive_phase8_gate_should_not_write_md.exists()
            or nonpositive_phase8_gate_should_not_write_json.exists()
        ):
            raise AssertionError("non-positive Phase 8 scorecard gate failure created partial compare-main output paths before failing")
        checks.append(
            require(
                True,
                "nonpositive_phase8_scorecard_gate_minimum_fails_fast",
                "compare_main_approaches.py now fails fast without creating output directories or writing artifacts when forward_evidence_scorecard.json gives phase8_promotion_review a non-positive observation floor",
            )
        )

        nonpositive_real_money_gate_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        nonpositive_real_money_gate_payload["decision_gate_minimums"]["real_money_discussion"][
            "min_total_settled_observations_with_usable_roi"
        ] = 0
        nonpositive_real_money_gate_json.write_text(
            json.dumps(nonpositive_real_money_gate_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        nonpositive_real_money_gate_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--scorecard-json",
                str(nonpositive_real_money_gate_json),
                "--csv-output",
                str(nonpositive_real_money_gate_should_not_write_csv),
                "--md-output",
                str(nonpositive_real_money_gate_should_not_write_md),
                "--json-output",
                str(nonpositive_real_money_gate_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if nonpositive_real_money_gate_result.returncode == 0:
            raise AssertionError("compare_main_approaches.py unexpectedly accepted a non-positive real-money scorecard gate floor")
        nonpositive_real_money_gate_text = f"{nonpositive_real_money_gate_result.stdout}\n{nonpositive_real_money_gate_result.stderr}"
        if "JSON path must be a positive integer: decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi" not in nonpositive_real_money_gate_text:
            raise AssertionError("non-positive real-money scorecard gate failure no longer names the malformed threshold")
        if (
            nonpositive_real_money_gate_output_dir.exists()
            or nonpositive_real_money_gate_should_not_write_csv.exists()
            or nonpositive_real_money_gate_should_not_write_md.exists()
            or nonpositive_real_money_gate_should_not_write_json.exists()
        ):
            raise AssertionError("non-positive real-money scorecard gate failure created partial compare-main output paths before failing")
        checks.append(
            require(
                True,
                "nonpositive_real_money_scorecard_gate_minimum_fails_fast",
                "compare_main_approaches.py now fails fast without creating output directories or writing artifacts when forward_evidence_scorecard.json gives real_money_discussion a non-positive observation floor",
            )
        )

        changed_gate_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        changed_gate_payload["decision_gate_minimums"]["phase8_promotion_review"][
            "min_roi_complete_settled_observations"
        ] = 21
        changed_gate_payload["decision_gate_minimums"]["anchor_displacement"][
            "min_roi_complete_settled_observations"
        ] = 31
        changed_gate_payload["decision_gate_minimums"]["real_money_discussion"][
            "min_total_settled_observations_with_usable_roi"
        ] = 101
        changed_gate_minimum_json.write_text(
            json.dumps(changed_gate_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        changed_gate_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--runtime-sec",
                f"{saved_runtime_sec}",
                "--cache-path",
                str(alt_cache),
                "--phase7-rules",
                str(alt_phase7_rules),
                "--wf-folds",
                str(alt_wf_folds),
                "--wf-rules",
                str(alt_wf_rules),
                "--scorecard-csv",
                str(alt_scorecard),
                "--scorecard-json",
                str(changed_gate_minimum_json),
                "--csv-output",
                str(changed_gate_csv),
                "--md-output",
                str(changed_gate_md),
                "--json-output",
                str(changed_gate_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        changed_gate_csv_df = pd.read_csv(changed_gate_csv)
        compare_like_saved(saved_df, changed_gate_csv_df)
        changed_gate_report_text = changed_gate_md.read_text(encoding="utf-8")
        changed_gate_json_payload = json.loads(changed_gate_json.read_text(encoding="utf-8"))
        changed_gate_stdout = build_expected_cli_stdout(
            changed_gate_report_text,
            csv_name=changed_gate_csv.name,
            md_name=changed_gate_md.name,
            json_name=changed_gate_json.name,
        )
        changed_gate_minimums = changed_gate_json_payload.get("decision_change_gate_minimums", {})
        changed_gate_evidence_debt = {
            str(row.get("family")): row
            for row in changed_gate_json_payload.get("method_family_evidence_debt", [])
            if isinstance(row, dict)
        }
        changed_selective_gates = changed_gate_evidence_debt.get("Selective OP/CD rule path", {}).get(
            "source_gate_minimums",
            {},
        )
        checks.append(
            require(
                changed_gate_result.stdout == changed_gate_stdout
                and changed_gate_json_payload["ranked_rows"] == pinned_json_payload["ranked_rows"]
                and changed_gate_minimums.get("phase8_promotion_review", {}).get(
                    "minimum_roi_complete_settled_observations"
                )
                == 21
                and changed_gate_minimums.get("anchor_displacement", {}).get(
                    "minimum_roi_complete_same_candidate_observations"
                )
                == 31
                and changed_gate_minimums.get("real_money_discussion", {}).get(
                    "minimum_total_settled_roi_complete_observations"
                )
                == 101
                and changed_selective_gates
                == {
                    "phase8_promotion_review": {
                        "minimum": 21,
                        "threshold_source": (
                            f"{changed_gate_minimum_json.name}:decision_gate_minimums."
                            "phase8_promotion_review.min_roi_complete_settled_observations"
                        ),
                    },
                    "anchor_displacement": {
                        "minimum": 31,
                        "threshold_source": (
                            f"{changed_gate_minimum_json.name}:decision_gate_minimums."
                            "anchor_displacement.min_roi_complete_settled_observations"
                        ),
                    },
                    "real_money_discussion": {
                        "minimum": 101,
                        "threshold_source": (
                            f"{changed_gate_minimum_json.name}:decision_gate_minimums."
                            "real_money_discussion.min_total_settled_observations_with_usable_roi"
                        ),
                    },
                }
                and "also needs 21+ complete shadow rows before promotion review"
                in changed_gate_evidence_debt["Selective OP/CD rule path"].get("still_missing", "")
                and "31+ same-candidate rows before anchor displacement"
                in changed_gate_evidence_debt["Selective OP/CD rule path"].get("still_missing", "")
                and "101+ total ROI-complete observations before any real-money discussion"
                in changed_gate_evidence_debt["Selective OP/CD rule path"].get("still_missing", "")
                and (
                    f"loaded from `{changed_gate_minimum_json.name}` `decision_gate_minimums`: "
                    "phase8_promotion_review=21, anchor_displacement=31, real_money_discussion=101"
                )
                in changed_gate_report_text
                and (
                    "Machine-readable threshold summary (also copied into the JSON sidecar): "
                    "anchor_displacement=31 ROI-complete same-candidate observations; "
                    "phase8_promotion_review=21 ROI-complete shadow observations; "
                    "real_money_discussion=101 total settled observations with usable ROI."
                )
                in changed_gate_report_text,
                "changed_scorecard_gate_minimums_rerender_from_source",
                "a copied scorecard JSON with altered 21/31/101 decision-gate floors now rerenders compare-main Markdown and JSON gate fields from that source while leaving ranked evidence rows unchanged, proving the comparison does not preserve stale local gate literals",
            )
        )

        bad_current_evidence_payload = json.loads((tmpdir / CURRENT_EVIDENCE_JSON.name).read_text(encoding="utf-8"))
        bad_current_evidence_payload["generated_at"] = "2026-06-26 18:12:48"
        bad_current_evidence_json.write_text(
            json.dumps(bad_current_evidence_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        bad_current_evidence_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--current-evidence-json",
                str(bad_current_evidence_json),
                "--csv-output",
                str(bad_current_evidence_should_not_write_csv),
                "--md-output",
                str(bad_current_evidence_should_not_write_md),
                "--json-output",
                str(bad_current_evidence_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if bad_current_evidence_result.returncode == 0:
            raise AssertionError("compare_main_approaches.py unexpectedly accepted current-evidence JSON with a timezone-naive generated_at")
        bad_current_evidence_text = f"{bad_current_evidence_result.stdout}\n{bad_current_evidence_result.stderr}"
        if "generated_at must be timezone-aware ISO provenance metadata" not in bad_current_evidence_text:
            raise AssertionError("current-evidence generated_at failure no longer explains that timestamp provenance must be timezone-aware")
        if (
            bad_current_evidence_output_dir.exists()
            or bad_current_evidence_should_not_write_csv.exists()
            or bad_current_evidence_should_not_write_md.exists()
            or bad_current_evidence_should_not_write_json.exists()
        ):
            raise AssertionError("bad current-evidence CLI path created output directories or wrote compare-main artifacts before failing provenance validation")
        checks.append(
            require(
                True,
                "bad_current_evidence_generated_at_fails_fast",
                "the real compare-main CLI now fails fast without creating output directories or writing artifacts if current_evidence_summary.json generated_at is timezone-naive before republishing the current-paper operator-boundary snapshot",
            )
        )

        missing_rebuild_contract_payload = json.loads((tmpdir / CURRENT_EVIDENCE_JSON.name).read_text(encoding="utf-8"))
        del missing_rebuild_contract_payload["rebuild_validation_contract"]
        missing_rebuild_contract_json.write_text(
            json.dumps(missing_rebuild_contract_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_rebuild_contract_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--current-evidence-json",
                str(missing_rebuild_contract_json),
                "--csv-output",
                str(missing_rebuild_contract_should_not_write_csv),
                "--md-output",
                str(missing_rebuild_contract_should_not_write_md),
                "--json-output",
                str(missing_rebuild_contract_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_rebuild_contract_result.returncode == 0:
            raise AssertionError(
                "compare_main_approaches.py unexpectedly accepted current-evidence JSON without rebuild_validation_contract"
            )
        missing_rebuild_contract_text = (
            f"{missing_rebuild_contract_result.stdout}\n{missing_rebuild_contract_result.stderr}"
        )
        if "missing rebuild_validation_contract" not in missing_rebuild_contract_text:
            raise AssertionError(
                "current-evidence rebuild_validation_contract failure no longer explains the missing contract"
            )
        if (
            missing_rebuild_contract_output_dir.exists()
            or missing_rebuild_contract_should_not_write_csv.exists()
            or missing_rebuild_contract_should_not_write_md.exists()
            or missing_rebuild_contract_should_not_write_json.exists()
        ):
            raise AssertionError(
                "missing rebuild-validation-contract CLI path created output directories or wrote compare-main artifacts before failing provenance validation"
            )
        checks.append(
            require(
                True,
                "missing_current_evidence_rebuild_validation_contract_fails_fast",
                "the real compare-main CLI now fails fast without creating output directories or writing artifacts if current_evidence_summary.json loses rebuild_validation_contract before republishing the current-paper operator-boundary snapshot",
            )
        )

        weakened_rebuild_contract_payload = json.loads(
            (tmpdir / CURRENT_EVIDENCE_JSON.name).read_text(encoding="utf-8")
        )
        weakened_rebuild_contract_payload["rebuild_validation_contract"][
            "upstream_refresh_order_is_provenance_metadata_only"
        ] = False
        weakened_rebuild_contract_json.write_text(
            json.dumps(weakened_rebuild_contract_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        weakened_rebuild_contract_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--current-evidence-json",
                str(weakened_rebuild_contract_json),
                "--csv-output",
                str(weakened_rebuild_contract_should_not_write_csv),
                "--md-output",
                str(weakened_rebuild_contract_should_not_write_md),
                "--json-output",
                str(weakened_rebuild_contract_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if weakened_rebuild_contract_result.returncode == 0:
            raise AssertionError(
                "compare_main_approaches.py unexpectedly accepted current-evidence JSON with a weakened rebuild_validation_contract"
            )
        weakened_rebuild_contract_text = (
            f"{weakened_rebuild_contract_result.stdout}\n{weakened_rebuild_contract_result.stderr}"
        )
        if "rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true" not in weakened_rebuild_contract_text:
            raise AssertionError(
                "current-evidence rebuild_validation_contract failure no longer explains the weakened provenance-only flag"
            )
        if (
            weakened_rebuild_contract_output_dir.exists()
            or weakened_rebuild_contract_should_not_write_csv.exists()
            or weakened_rebuild_contract_should_not_write_md.exists()
            or weakened_rebuild_contract_should_not_write_json.exists()
        ):
            raise AssertionError(
                "weakened rebuild-validation-contract CLI path created output directories or wrote compare-main artifacts before failing provenance validation"
            )
        checks.append(
            require(
                True,
                "weakened_current_evidence_rebuild_validation_contract_fails_fast",
                "the real compare-main CLI now fails fast without creating output directories or writing artifacts if current_evidence_summary.json keeps rebuild_validation_contract but weakens upstream_refresh_order_is_provenance_metadata_only before republishing the current-paper operator-boundary snapshot",
            )
        )

        missing_source_freshness_payload = json.loads((tmpdir / CURRENT_EVIDENCE_JSON.name).read_text(encoding="utf-8"))
        del missing_source_freshness_payload["source_freshness"]
        missing_source_freshness_json.write_text(
            json.dumps(missing_source_freshness_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_source_freshness_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--current-evidence-json",
                str(missing_source_freshness_json),
                "--csv-output",
                str(missing_source_freshness_should_not_write_csv),
                "--md-output",
                str(missing_source_freshness_should_not_write_md),
                "--json-output",
                str(missing_source_freshness_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_source_freshness_result.returncode == 0:
            raise AssertionError("compare_main_approaches.py unexpectedly accepted current-evidence JSON missing source_freshness")
        missing_source_freshness_text = f"{missing_source_freshness_result.stdout}\n{missing_source_freshness_result.stderr}"
        if "missing source_freshness" not in missing_source_freshness_text:
            raise AssertionError("current-evidence source_freshness failure no longer names the missing bridge block")
        if (
            missing_source_freshness_output_dir.exists()
            or missing_source_freshness_should_not_write_csv.exists()
            or missing_source_freshness_should_not_write_md.exists()
            or missing_source_freshness_should_not_write_json.exists()
        ):
            raise AssertionError("missing source_freshness CLI path created output directories or wrote compare-main artifacts before failing source validation")
        checks.append(
            require(
                True,
                "missing_current_evidence_source_freshness_fails_fast",
                "the real compare-main CLI now fails fast without creating nested output directories or writing artifacts if current_evidence_summary.json loses source_freshness before republishing the current-paper operator-boundary snapshot",
            )
        )

        missing_operator_read_gate_payload = json.loads(
            (tmpdir / CURRENT_EVIDENCE_JSON.name).read_text(encoding="utf-8")
        )
        del missing_operator_read_gate_payload["operator_read_gate"]
        missing_operator_read_gate_json.write_text(
            json.dumps(missing_operator_read_gate_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_operator_read_gate_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--current-evidence-json",
                str(missing_operator_read_gate_json),
                "--csv-output",
                str(missing_operator_read_gate_should_not_write_csv),
                "--md-output",
                str(missing_operator_read_gate_should_not_write_md),
                "--json-output",
                str(missing_operator_read_gate_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_operator_read_gate_result.returncode == 0:
            raise AssertionError("compare_main_approaches.py unexpectedly accepted current-evidence JSON missing operator_read_gate")
        missing_operator_read_gate_text = (
            f"{missing_operator_read_gate_result.stdout}\n{missing_operator_read_gate_result.stderr}"
        )
        if "is missing operator_read_gate" not in missing_operator_read_gate_text:
            raise AssertionError("current-evidence operator_read_gate failure no longer names the missing bridge block")
        if (
            missing_operator_read_gate_output_dir.exists()
            or missing_operator_read_gate_should_not_write_csv.exists()
            or missing_operator_read_gate_should_not_write_md.exists()
            or missing_operator_read_gate_should_not_write_json.exists()
        ):
            raise AssertionError("missing operator_read_gate CLI path created output directories or wrote compare-main artifacts before failing source validation")
        checks.append(
            require(
                True,
                "missing_current_evidence_operator_read_gate_fails_fast",
                "the real compare-main CLI now fails fast without creating nested output directories or writing artifacts if current_evidence_summary.json loses operator_read_gate before republishing the current-paper operator-boundary snapshot",
            )
        )

        missing_refresh_action_boundary_field_payload = json.loads(
            (tmpdir / CURRENT_EVIDENCE_JSON.name).read_text(encoding="utf-8")
        )
        del missing_refresh_action_boundary_field_payload["source_freshness"]["refresh_action_boundary"][
            "not_real_money_evidence"
        ]
        missing_refresh_action_boundary_field_json.write_text(
            json.dumps(missing_refresh_action_boundary_field_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_refresh_action_boundary_field_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--current-evidence-json",
                str(missing_refresh_action_boundary_field_json),
                "--csv-output",
                str(missing_refresh_action_boundary_field_should_not_write_csv),
                "--md-output",
                str(missing_refresh_action_boundary_field_should_not_write_md),
                "--json-output",
                str(missing_refresh_action_boundary_field_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_refresh_action_boundary_field_result.returncode == 0:
            raise AssertionError("compare_main_approaches.py unexpectedly accepted current-evidence JSON missing source_freshness.refresh_action_boundary.not_real_money_evidence")
        missing_refresh_action_boundary_field_text = (
            f"{missing_refresh_action_boundary_field_result.stdout}\n"
            f"{missing_refresh_action_boundary_field_result.stderr}"
        )
        if (
            "source_freshness.refresh_action_boundary missing fields: not_real_money_evidence"
            not in missing_refresh_action_boundary_field_text
        ):
            raise AssertionError("current-evidence refresh-action-boundary field failure no longer names the missing not_real_money_evidence flag")
        if (
            missing_refresh_action_boundary_field_output_dir.exists()
            or missing_refresh_action_boundary_field_should_not_write_csv.exists()
            or missing_refresh_action_boundary_field_should_not_write_md.exists()
            or missing_refresh_action_boundary_field_should_not_write_json.exists()
        ):
            raise AssertionError("missing refresh-action-boundary field CLI path created output directories or wrote compare-main artifacts before failing source validation")
        checks.append(
            require(
                True,
                "missing_current_evidence_refresh_action_boundary_field_fails_fast",
                "the real compare-main CLI now fails fast without creating nested output directories or writing artifacts if current_evidence_summary.json loses source_freshness.refresh_action_boundary.not_real_money_evidence before republishing the current-paper operator-boundary snapshot",
            )
        )

        false_refresh_accounting_payload = json.loads(
            (tmpdir / CURRENT_EVIDENCE_JSON.name).read_text(encoding="utf-8")
        )
        false_refresh_accounting_payload["source_freshness"]["refresh_action_boundary"][
            "clean_empty_refresh_counts_as_forward_performance"
        ] = True
        false_refresh_accounting_json.write_text(
            json.dumps(false_refresh_accounting_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        false_refresh_accounting_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--current-evidence-json",
                str(false_refresh_accounting_json),
                "--csv-output",
                str(false_refresh_accounting_should_not_write_csv),
                "--md-output",
                str(false_refresh_accounting_should_not_write_md),
                "--json-output",
                str(false_refresh_accounting_should_not_write_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if false_refresh_accounting_result.returncode == 0:
            raise AssertionError("compare_main_approaches.py unexpectedly accepted current-evidence JSON with source_freshness.refresh_action_boundary.clean_empty_refresh_counts_as_forward_performance=true")
        false_refresh_accounting_text = (
            f"{false_refresh_accounting_result.stdout}\n"
            f"{false_refresh_accounting_result.stderr}"
        )
        if (
            "source_freshness.refresh_action_boundary must mark "
            "clean_empty_refresh_counts_as_forward_performance=false"
            not in false_refresh_accounting_text
        ):
            raise AssertionError("current-evidence refresh-accounting failure no longer names the weakened clean-empty forward-performance flag")
        if (
            false_refresh_accounting_output_dir.exists()
            or false_refresh_accounting_should_not_write_csv.exists()
            or false_refresh_accounting_should_not_write_md.exists()
            or false_refresh_accounting_should_not_write_json.exists()
        ):
            raise AssertionError("weakened refresh-accounting CLI path created output directories or wrote compare-main artifacts before failing source validation")
        checks.append(
            require(
                True,
                "false_current_evidence_refresh_accounting_fails_fast",
                "the real compare-main CLI now fails fast without creating nested output directories or writing artifacts if current_evidence_summary.json marks source_freshness.refresh_action_boundary.clean_empty_refresh_counts_as_forward_performance=true before republishing weakened wrapper-refresh accounting",
            )
        )

        missing_wf_rules_df = pd.read_csv(alt_wf_rules)
        missing_wf_rules_df = missing_wf_rules_df[
            ~((missing_wf_rules_df["test_year"] == 2025) & (missing_wf_rules_df["rule_id"] == "OP_REFINED_K7"))
        ].copy()
        missing_wf_rules_df.to_csv(missing_wf_rules, index=False)
        missing_wf_rules_result = subprocess.run(
            [
                sys.executable,
                COMPARE_SCRIPT.name,
                "--wf-rules",
                str(missing_wf_rules),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_wf_rules_result.returncode == 0:
            raise AssertionError("compare_main_approaches.py unexpectedly accepted walk-forward rules missing the 2025 OP_REFINED_K7 switch candidate")
        missing_wf_rules_text = f"{missing_wf_rules_result.stdout}\n{missing_wf_rules_result.stderr}"
        if "missing required OP switch row for OP_REFINED_K7 in holdout year 2025" not in missing_wf_rules_text:
            raise AssertionError("walk-forward-rule failure no longer explains the missing OP_REFINED_K7 holdout-year switch candidate")

    compare_df = rebuilt_df.set_index("method_id")

    phase7_holdout = frozen_row("portfolio", "phase7_live", "holdout_2024_2025")
    phase8_holdout = frozen_row("portfolio", "phase8_frozen", "holdout_2024_2025")
    op_durable_holdout = frozen_row("rule", "OP_DURABLE_K7", "holdout_2024_2025")
    op_refined_holdout = frozen_row("rule", "OP_REFINED_K7", "holdout_2024_2025")

    checks.append(
        require(
            abs(float(compare_df.loc["phase7_live_portfolio", "holdout_roi"]) - float(phase7_holdout["roi"])) < 1e-9
            and int(compare_df.loc["phase7_live_portfolio", "holdout_races"]) == int(phase7_holdout["races"])
            and abs(float(compare_df.loc["phase7_live_portfolio", "holdout_profit"]) - float(phase7_holdout["profit"])) < 1e-9,
            "phase7_matches_frozen_holdout",
            "Phase 7 comparison row still matches frozen holdout ROI, races, and profit",
        )
    )
    checks.append(
        require(
            abs(float(compare_df.loc["phase8_frozen_portfolio", "holdout_roi"]) - float(phase8_holdout["roi"])) < 1e-9
            and int(compare_df.loc["phase8_frozen_portfolio", "holdout_races"]) == int(phase8_holdout["races"])
            and abs(float(compare_df.loc["phase8_frozen_portfolio", "holdout_profit"]) - float(phase8_holdout["profit"])) < 1e-9,
            "phase8_matches_frozen_holdout",
            "Phase 8 comparison row still matches frozen holdout ROI, races, and profit",
        )
    )
    checks.append(
        require(
            abs(float(compare_df.loc["op_durable_only", "holdout_roi"]) - float(op_durable_holdout["roi"])) < 1e-9
            and int(compare_df.loc["op_durable_only", "holdout_races"]) == int(op_durable_holdout["races"]),
            "op_durable_matches_rule_holdout",
            "OP durable comparison row still matches the frozen OP_DURABLE_K7 holdout row",
        )
    )
    checks.append(
        require(
            abs(float(compare_df.loc["op_refined_only", "holdout_roi"]) - float(op_refined_holdout["roi"])) < 1e-9
            and int(compare_df.loc["op_refined_only", "holdout_races"]) == int(op_refined_holdout["races"]),
            "op_refined_matches_rule_holdout",
            "OP refined comparison row still matches the frozen OP_REFINED_K7 holdout row",
        )
    )

    selector_wf = cma.dynamic_rows_from_folds(folds[folds["test_year"].isin(wf_years)])
    selector_holdout = cma.dynamic_rows_from_folds(folds[folds["test_year"].isin(HOLDOUT_YEARS)])
    checks.append(
        require(
            abs(float(compare_df.loc["train_only_selector", "wf_roi"]) - float(selector_wf["roi"])) < 1e-9
            and int(compare_df.loc["train_only_selector", "wf_races"]) == int(selector_wf["races"])
            and abs(float(compare_df.loc["train_only_selector", "holdout_roi"]) - float(selector_holdout["roi"])) < 1e-9
            and int(compare_df.loc["train_only_selector", "holdout_races"]) == int(selector_holdout["races"]),
            "selector_matches_walk_forward_folds",
            "train-only selector row still matches direct aggregation from walk_forward_validation_folds.csv",
        )
    )

    holdout_choice_map = {
        int(row.test_year): str(row.rule_id)
        for _, row in holdout_switch_choices.sort_values("test_year").iterrows()
    }
    checks.append(
        require(
            holdout_choice_map == {2024: "OP_REFINED_K7", 2025: "OP_REFINED_K7"},
            "op_holdout_switch_choices",
            "current OP train-score switch still chooses OP_REFINED_K7 in both holdout years",
        )
    )
    checks.append(
        require(
            abs(float(compare_df.loc["op_train_switch", "holdout_roi"]) - float(compare_df.loc["op_refined_only", "holdout_roi"])) < 1e-9
            and int(compare_df.loc["op_train_switch", "holdout_races"]) == int(compare_df.loc["op_refined_only", "holdout_races"]),
            "op_switch_equals_refined_on_holdout",
            "OP train-score switch still collapses to the refined OP line on the 2024-2025 holdout",
        )
    )
    checks.append(
        require(
            abs(float(compare_df.loc["phase7_live_portfolio", "holdout_2024_roi"]) - 0.37) < 1e-9
            and int(compare_df.loc["phase7_live_portfolio", "holdout_2024_races"]) == 109
            and abs(float(compare_df.loc["phase7_live_portfolio", "holdout_2025_roi"]) - 105.38) < 1e-9
            and int(compare_df.loc["phase7_live_portfolio", "holdout_2025_races"]) == 66,
            "phase7_holdout_year_split",
            "Phase 7 comparison row now pins the nearly-flat 2024 / strong 2025 holdout split on the full current portfolio sample",
        )
    )
    checks.append(
        require(
            abs(float(compare_df.loc["phase8_frozen_portfolio", "holdout_2024_roi"]) - 9.5) < 1e-9
            and int(compare_df.loc["phase8_frozen_portfolio", "holdout_2024_races"]) == 85
            and abs(float(compare_df.loc["phase8_frozen_portfolio", "holdout_2025_roi"]) - 50.26) < 1e-9
            and int(compare_df.loc["phase8_frozen_portfolio", "holdout_2025_races"]) == 33,
            "phase8_holdout_year_split",
            "Phase 8 comparison row now pins the positive-both-years but smaller-sample 2024 / 2025 holdout split",
        )
    )
    checks.append(
        require(
            abs(float(compare_df.loc["op_durable_only", "holdout_2024_roi"]) - (-47.41)) < 1e-9
            and int(compare_df.loc["op_durable_only", "holdout_2024_races"]) == 68
            and abs(float(compare_df.loc["op_durable_only", "holdout_2025_roi"]) - 124.61) < 1e-9
            and int(compare_df.loc["op_durable_only", "holdout_2025_races"]) == 47
            and abs(float(compare_df.loc["op_refined_only", "holdout_2024_roi"]) - (-25.47)) < 1e-9
            and int(compare_df.loc["op_refined_only", "holdout_2024_races"]) == 33
            and abs(float(compare_df.loc["op_refined_only", "holdout_2025_roi"]) - 210.02) < 1e-9
            and int(compare_df.loc["op_refined_only", "holdout_2025_races"]) == 16,
            "op_holdout_year_split",
            "OP durable and OP refined rows now carry the explicit 2024 / 2025 holdout split that clarifies sample-vs-ROI tradeoffs",
        )
    )
    checks.append(
        require(
            abs(float(compare_df.loc["train_only_selector", "holdout_2024_roi"]) - (-19.95)) < 1e-9
            and int(compare_df.loc["train_only_selector", "holdout_2024_races"]) == 45
            and abs(float(compare_df.loc["train_only_selector", "holdout_2025_roi"]) - 98.37) < 1e-9
            and int(compare_df.loc["train_only_selector", "holdout_2025_races"]) == 20,
            "selector_holdout_year_split",
            "train-only yearly selector row now pins its losing 2024 / rebound 2025 holdout split",
        )
    )
    checks.append(
        require(
            int(compare_df.loc["phase7_live_portfolio", "rank"]) == 1
            and int(compare_df.loc["phase8_frozen_portfolio", "rank"]) == 2,
            "comparison_top_order",
            "comparison ranking still starts with Phase 7 first and Phase 8 second under the conservative score",
        )
    )
    checks.append(
        require(
            str(compare_df.loc["phase7_live_portfolio", "secondary_basis"]) == "frozen replay on walk-forward test years"
            and str(compare_df.loc["phase8_frozen_portfolio", "secondary_basis"]) == "frozen replay on walk-forward test years"
            and str(compare_df.loc["op_durable_only", "secondary_basis"]) == "frozen replay on walk-forward test years"
            and str(compare_df.loc["op_refined_only", "secondary_basis"]) == "frozen replay on walk-forward test years"
            and str(compare_df.loc["op_train_switch", "secondary_basis"]) == "actual train-only walk-forward"
            and str(compare_df.loc["train_only_selector", "secondary_basis"]) == "actual train-only walk-forward",
            "secondary_basis_split",
            "comparison CSV now distinguishes frozen replay context for fixed methods from actual train-only walk-forward context for dynamic selectors",
        )
    )
    posture_map = {
        method_id: str(compare_df.loc[method_id, "deployment_posture"])
        for method_id in compare_df.index.tolist()
    }
    checks.append(
        require(
            posture_map == cma.DEPLOYMENT_POSTURE,
            "deployment_posture_map",
            "comparison harness still carries the current PAPER NOW / SHADOW ONLY / ANCHOR / WATCH / BENCHMARK ONLY posture labels",
        )
    )
    checks.append(
        require(
            float(compare_df.loc["op_durable_only", "holdout_races"]) > float(compare_df.loc["op_refined_only", "holdout_races"]),
            "op_anchor_has_larger_sample",
            "OP durable still carries the larger holdout sample than OP refined inside the comparison harness",
        )
    )
    checks.append(
        require(
            str(compare_df.loc["op_durable_only", "deployment_posture"]) == "ANCHOR"
            and str(compare_df.loc["op_refined_only", "deployment_posture"]) == "WATCH"
            and float(compare_df.loc["op_refined_only", "score"]) > float(compare_df.loc["op_durable_only", "score"]),
            "op_score_vs_posture_guardrail",
            "OP refined may outscore durable on compact evidence ordering, but the posture layer still keeps durable as ANCHOR and refined as WATCH",
        )
    )

    family_rows = cma.load_method_family_rows()
    family_by_id = {str(row["family_id"]): row for row in family_rows}
    selective_family = family_by_id["selective_rule_path"]
    harville_family = family_by_id["harville_ranked"]
    xgboost_family = family_by_id["xgboost_residual"]
    op_challenger_diagnostic = saved_json.get("op_challenger_diagnostic", {})
    source_ci_diagnostic = scorecard_json["ci_only_promotion_diagnostics"]["OP_REFINED_K7"]
    one_screen_rows = [
        f"| What is the primary paper-basket core? | Keep `{selective_family['current_anchor']}` as the anchor and `{selective_family['primary_shadow']}` as the primary paper-basket companion | Paper only; daily target-card availability still comes from the current preflight, and real-money confidence still needs 100+ settled ledger observations with usable ROI coverage plus concentration and payout checks |",
        f"| What is the closest challenger? | `{selective_family['secondary_shadow']}` is the closest same-family OP shadow, not a promoted default | Promotion review needs 20+ future settled shadow ledger observations; replacing the anchor needs 30+ ROI-complete same-candidate observations plus cleaner split-aware/walk-forward support |",
        f"| Does Harville change the current paper path? | No — Harville remains {harville_family['role']} | Current broad replay is {cma.fmt_pct(float(harville_family['primary_metric']))} ROI despite a {cma.fmt_plain_pct(float(harville_family['secondary_metric']))} hit rate; it needs positive betting evidence, not just calibration value |",
        f"| Does current odds-only XGBoost change the current paper path? | No — current odds-only XGBoost remains {xgboost_family['role']} / parked | Best ML betting ROI is {cma.fmt_pct(float(xgboost_family['primary_metric']))}; another odds-only replay is not enough to reopen it |",
        "| Do clean scans or settlement audits change posture? | No — clean scans, open signals, and ledger/settlement audits are operability checks, not performance proof | They can reveal missing templates or ROI-coverage gaps; only settled hit/miss rows with usable return/cost coverage can feed future decision changes |",
        "| Can BAQ stand in for BEL? | No — keep `BEL_BROAD1_K7` dormant until fresh Belmont races exist | BAQ needs independent evidence and must not inherit BEL's rule |",
    ]
    action_summary_rows = [
        f"| Selective rule path | Paper-observe `{selective_family['current_anchor']}` + `{selective_family['primary_shadow']}` and keep `{selective_family['secondary_shadow']}` shadow-only | Real-money confidence or anchor changes before settled ROI-complete paper observations | 100+ settled paper observations with usable ROI coverage for confidence; 20+ settled shadow observations before `{selective_family['secondary_shadow']}` promotion review; 30+ same-candidate ROI-complete observations plus cleaner split-aware/walk-forward support before anchor displacement |",
        "| Harville-ranked probabilities | Calibration and benchmark sanity checks | Paper-bet selection or deployment promotion from hit rate alone | Positive frozen-holdout or train-only walk-forward betting evidence; calibration-only summaries do not change posture |",
        "| Current odds-only XGBoost correction path | Research-only diagnostics for what odds-derived models can and cannot add | Reopening the betting path from another odds-only replay or payout-model metric | A materially richer non-odds feature/data class, downstream betting pass-through improvement, and then settled paper observations |",
    ]
    evidence_debt_rows = [
        f"| Selective OP/CD rule path | Future settled OP/CD paper rows with usable ROI coverage; `{selective_family['secondary_shadow']}` also needs 20+ complete shadow rows before promotion review; 30+ same-candidate rows before anchor displacement; 100+ total ROI-complete observations before any real-money discussion | Treating old holdout/replay rows, clean scans, open signals, or a settlement-audit pass as posture-changing proof | Keep collecting and settling `{selective_family['current_anchor']}` + `{selective_family['primary_shadow']}` observations; log `{selective_family['secondary_shadow']}` as shadow-only until the explicit gates are met |",
        f"| Harville-ranked probabilities | Positive betting evidence on frozen holdout or train-only walk-forward terms, not just broad hit-rate/calibration context | Promoting from a {cma.fmt_plain_pct(float(harville_family['secondary_metric']))} hit rate while the broad betting replay is {cma.fmt_pct(float(harville_family['primary_metric']))} ROI | Keep Harville as a benchmark/calibration sanity check unless a future betting-evidence surface turns positive |",
        f"| Current odds-only XGBoost correction path | A materially richer non-odds feature/data class, downstream betting pass-through improvement, and then settled paper observations | Reopening from another odds-only rerun, payout-RMSE gain, or model-fit-only downstream A/B result while betting ROI remains {cma.fmt_pct(float(xgboost_family['primary_metric']))} | Keep the current odds-only XGBoost path parked; reopen only if the feature class changes and the betting pass-through improves before paper observation |",
    ]
    evidence_class_triage_rows = [
        f"| Selective rule path | Frozen holdout + train-only walk-forward benchmark ({cma.fmt_pct(float(selective_family['primary_metric']))} on {int(selective_family['primary_sample'])} holdout races; {cma.fmt_pct(float(selective_family['secondary_metric']))} on {int(selective_family['secondary_sample'])} train-only walk-forward races) | PAPER NOW; keep `{selective_family['current_anchor']}` as anchor, `{selective_family['primary_shadow']}` as paper companion, and `{selective_family['secondary_shadow']}` shadow-only | `{selective_family['secondary_shadow']}` promotion review needs 20+ future settled shadow ledger observations with complete ROI coverage and cleaner split-aware/walk-forward support; anchor displacement needs 30+ same-candidate ROI-complete observations; real-money confidence still needs 100+ settled paper observations with usable ROI coverage plus concentration checks |",
        f"| Harville-ranked probabilities | Broad structural benchmark ({cma.fmt_pct(float(harville_family['primary_metric']))} ROI on {int(harville_family['primary_sample'])} races; {cma.fmt_plain_pct(float(harville_family['secondary_metric']))} hit rate) | BENCHMARK ONLY; useful for calibration context, not a paper betting path | Positive frozen holdout / train-only walk-forward betting evidence, not just a high hit rate |",
        f"| Current odds-only XGBoost correction path | Research/model-fit lane ({cma.fmt_pct(float(xgboost_family['primary_metric']))} best ML betting ROI on {int(xgboost_family['primary_sample'])} races; {cma.fmt_plain_pct(float(xgboost_family['secondary_metric']))} matched payout-RMSE reduction context) | RESEARCH ONLY / parked; the enriched horse-history downstream A/B remains separate research-only context too | Material evidence-class change: richer non-odds features plus downstream betting improvement and then settled paper observations; not another odds-only replay |",
        "| Paper-trade operational surfaces | Daily scan results, open signals, settlement audit, and ledger-quality checks | OPERABILITY / REPAIR ONLY; use them to keep the ledger complete before interpreting ROI | They only change posture after they become settled hit/miss rows with usable return/cost coverage; audit cleanliness alone is not forward-performance evidence |",
    ]
    decision_change_gate_rows = [
        f"| Replace `{selective_family['current_anchor']}` anchor with `{selective_family['secondary_shadow']}` | Keep `{selective_family['current_anchor']}` as anchor; `{selective_family['secondary_shadow']}` stays shadow-only | 30+ ROI-complete same-candidate settled paper observations plus cleaner split-aware/walk-forward/frozen support that clearly beats the anchor's larger sample; 20+ shadow rows only starts promotion review | Future settled same-candidate paper ledger rows with complete ROI coverage; historical replay or holdout rows do not count as new promotion evidence | The challenger line is hotter but smaller and uneven: 49 holdout races, a losing 2024 / very hot 2025 split, and only 2/10 walk-forward selections |",
        f"| Move Harville-ranked probabilities into the current paper path | {harville_family['role']} | Positive frozen-holdout or train-only walk-forward betting evidence, not only a high hit rate on a broad benchmark replay | New betting-evidence surface only; calibration or hit-rate summaries without profitable wagering evidence do not change deployment posture | The current broad replay is {cma.fmt_pct(float(harville_family['primary_metric']))} ROI despite a {cma.fmt_plain_pct(float(harville_family['secondary_metric']))} hit rate |",
        f"| Reopen current odds-only XGBoost as a betting path | {xgboost_family['role']} / parked | Richer non-odds features, downstream betting improvement, then settled paper observations; another odds-only replay is not enough | A materially different feature/data class plus downstream betting pass-through; another odds-only rerun is not a new evidence class | Current best ML betting ROI is {cma.fmt_pct(float(xgboost_family['primary_metric']))}, and the downstream A/B remains model-fit context rather than betting proof |",
        "| Substitute BAQ for dormant BEL | Do not substitute; keep `BEL_BROAD1_K7` dormant | Fresh Belmont qualifying races only; BAQ needs its own independent evidence and must not inherit BEL's rule | Fresh Belmont qualifying races only; BAQ needs independent evidence and cannot inherit BEL history | The BEL->BAQ bridge already failed, and the current scorecard has zero BEL holdout races |",
        "| Move from paper to real money | Paper only | 100+ settled paper observations with hit-rate/ROI inside the expected range plus concentration and payout checks | Settled paper-trade ledger observations with usable ROI coverage, not clean scans, open signals, ledger-quality/settlement-audit passes, or replay backtests | Clean runs and clean audits prove operability; they are not forward-profit proof until outcomes settle |",
    ]
    selective_guardrail_primary = (
        f"| {selective_family['label']} | {selective_family['role']} | "
        f"{cma.fmt_pct(float(selective_family['primary_metric']))} ({selective_family['primary_metric_label']}; "
        f"2024 {cma.fmt_pct(float(selective_family['holdout_2024_metric']))} on {int(selective_family['holdout_2024_sample'])}, "
        f"2025 {cma.fmt_pct(float(selective_family['holdout_2025_metric']))} on {int(selective_family['holdout_2025_sample'])}) | 175 | +22.46% (train-only selector walk-forward ROI) |"
    )
    selective_guardrail_why = "but the recent path was uneven rather than a smooth two-year glide."
    selective_shadow_read = (
        f"`{selective_family['current_anchor']}` remains the safest anchor, "
        f"`{selective_family['primary_shadow']}` is the primary OP/CD paper-basket companion, "
        f"and `{selective_family['secondary_shadow']}` remains the narrower same-family OP shadow challenger."
    )
    current_rule_ladder_rows = cma.build_current_rule_ladder(selective_family)
    shadow_watch_triage_rows = cma.build_shadow_watch_triage()
    scorecard_rows = cma.load_scorecard_rows()
    source_fingerprint_rows = [
        cma.format_source_fingerprint_row(label, fingerprint)
        for label, fingerprint in cma.source_file_fingerprints().items()
    ]
    operator_boundary_rows = [
        f"| Source freshness | `{current_operator_boundary['right_now_freshness_state']}`; refresh before right-now use = `{current_operator_boundary['requires_refresh_before_right_now_use']}` | Source freshness is operator-readiness metadata, not performance proof |",
        f"| Source freshness reference | bridge reference date `{current_operator_boundary['source_freshness_generated_reference_date']}` in `{current_operator_boundary['source_freshness_generated_reference_timezone']}`; compared via `{current_operator_boundary['source_freshness_staleness_comparison_source']}` = `{current_operator_boundary['source_freshness_staleness_comparison_date']}`; right-now as-of `{current_operator_boundary['right_now_as_of_date']}` / run `{current_operator_boundary['right_now_run_date']}` | Reference-date routing is reproducibility metadata for stale-card checks, not performance proof |",
        f"| Refresh action boundary | `{current_operator_boundary['refresh_action_command']}` required before right-now use = `{current_operator_boundary['refresh_required_before_right_now_instruction_use']}`; source action current before refresh = `{current_operator_boundary['refresh_source_action_counts_as_current_instruction_before_refresh']}`; can update operator surfaces = `{current_operator_boundary['refresh_can_update_operator_surfaces']}`; settles rows / creates ROI evidence / clean-empty performance = `{current_operator_boundary['refresh_can_settle_open_rows_by_itself']}` / `{current_operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}` / `{current_operator_boundary['clean_empty_refresh_counts_as_forward_performance']}` | Wrapper refresh is operator routing only; it is not settled ROI, promotion readiness, live profitability, or real-money evidence |",
        f"| Source consistency | overall match = `{current_operator_boundary['source_consistency_overall_match']}` | Fingerprints and bridge consistency are reproducibility checks only |",
        f"| Bridge-published gate progress | `{current_operator_boundary['source_path']}` `decision_gate_progress`: {cma.md_cell(current_operator_boundary['decision_gate_progress']['read'])} Source: `{current_operator_boundary['decision_gate_progress']['source_path']}` `{current_operator_boundary['decision_gate_progress']['source_json_path']}`; gate status = `{current_operator_boundary['decision_gate_progress']['gate_status']}` | Current gates are all uncleared routing context only; they do not create settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
        f"| Current bridge rebuild order | `{current_operator_boundary['source_path']}` `rebuild_validation_contract`: `python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*` after source-byte changes | Provenance/rebuild route only; green checks and rebuild order are not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence |",
        f"| Current settled rule mix | OP_DURABLE_K7={current_operator_boundary['op_anchor_roi_complete_rows']}; CD_CORE_K8={current_operator_boundary['cd_companion_roi_complete_rows']}; {cma.md_cell(current_operator_boundary['primary_rule_mix_read'])} | Rule-specific settled rows stay separate; CD-only paper rows are not OP-anchor forward evidence |",
        f"| Settlement queue state | `{current_operator_boundary['open_settlement_queue_state']}`; {cma.md_cell(current_operator_boundary['open_settlement_context'])}; detail: {cma.md_cell(current_operator_boundary['open_settlement_queue_read'])} | Open rows are settlement workflow only; fill outcomes from result/payout evidence before interpreting ROI |",
        f"| Recommendation context | {cma.md_cell(current_operator_boundary['recommendation_context_read'])} | Latest recommendation-state context is operator routing only, not bet readiness or forward-performance evidence |",
        f"| Operator route | `{current_operator_boundary['best_action_command']}` | Use the bridge route to settle or refresh; do not infer profit, promotion, or real-money readiness from the route itself |",
    ]
    checks.append(
        require(
            "## Evidence Boundary" in report_text
            and "Artifact role: main approach comparison bundle" in report_text
            and "not new forward evidence, a live paper-trade ledger, current-day scanner output, settled ROI, live profitability, promotion readiness, or real-money evidence" in report_text
            and "Decision-change gates are forward-observation requirements, not evidence that a gate has already been cleared." in report_text
            and "Current-evidence bridge data, when shown below, is operator-routing context only and does not convert open signals, recommendation-state context, source freshness, or settlement queue rows into settled ROI or bet readiness." in report_text
            and "## Current Operator Boundary Snapshot" in report_text
            and "This small snapshot is copied from `current_evidence_summary.json` so the comparison report can point to the current settlement boundary without becoming a live-paper performance surface." in report_text
            and "| Field | Current bridge read | Evidence boundary |" in report_text
            and all(row in report_text for row in operator_boundary_rows)
            and "| Primary first-read gate |" not in report_text
            and "`current_evidence_summary.json` `decision_gate_progress`" in report_text
            and "## Source Provenance" in report_text
            and f"These fingerprints identify the exact input files used by this comparison rerender. {cma.EVIDENCE_BOUNDARY}." in report_text
            and "| Source | Path | Bytes | SHA-256 |" in report_text
            and all(row in report_text for row in source_fingerprint_rows)
            and "see Source Provenance above for exact input-byte fingerprints" in report_text,
            "source_provenance_section_present",
            "compare_main_approaches.md now carries a human-readable evidence boundary, a current-evidence operator-boundary snapshot for bridge-published decision_gate_progress, rebuild_validation_contract, recommendation-state, source-published settlement-queue state/context/detail, and exact path/byte/SHA-256 fingerprints for its comparison inputs, including race cache, rules, walk-forward artifacts, scorecard, current-evidence bridge, cross-family card, backtest summary, and A/B JSON, while stating those hashes and the operator snapshot are reproducibility/routing metadata rather than promotion evidence",
        )
    )
    parsed_source_rows = parse_source_provenance_table(report_text)
    checks.append(
        require(
            parsed_source_rows == saved_json.get("source_files") == cma.source_file_fingerprints(),
            "source_provenance_markdown_matches_json",
            "compare_main_approaches.md Source Provenance table now matches compare_main_approaches.json source_files exactly for every path, byte count, and SHA-256 fingerprint",
        )
    )
    checks.append(
        require(
            "## Cole's One-Screen Read" in report_text
            and "Use this when the full report is too much and Cole needs the decision-safe answer first. This is a routing summary, not new forward evidence." in report_text
            and "| Question | Current read | Evidence boundary |" in report_text
            and all(row in report_text for row in one_screen_rows),
            "one_screen_read_present",
            "compare_main_approaches.md now opens the detailed comparison with a one-screen decision-safe routing table for the primary OP/CD paper-basket core, the OP_REFINED_K7 challenger, Harville, current odds-only XGBoost, the settlement-audit non-evidence boundary, and the BEL-not-BAQ caution without adding new forward evidence",
        )
    )
    checks.append(
        require(
            "## Method-Family Action Summary" in report_text
            and "Use this when the comparison question is Harville vs current odds-only XGBoost vs the selective OP/CD path. It is an action map, not a profitability upgrade." in report_text
            and "| Family | Use it for now | Do not use it for | Next valid evidence |" in report_text
            and all(row in report_text for row in action_summary_rows)
            and "Action map verdict: spend operational energy on settled selective paper observations first; Harville and current odds-only XGBoost stay comparison controls unless their evidence class changes. Settlement-audit repairs can make future rows usable, but audit cleanliness alone does not promote any lane." in report_text
            and op_challenger_diagnostic == cma.build_op_challenger_diagnostic(selective_family)
            and op_challenger_diagnostic.get("anchor_rule") == "OP_DURABLE_K7"
            and op_challenger_diagnostic.get("challenger_rule") == "OP_REFINED_K7"
            and op_challenger_diagnostic.get("anchor_holdout_races") == 115
            and op_challenger_diagnostic.get("challenger_holdout_races") == 49
            and abs(float(op_challenger_diagnostic.get("challenger_sample_ratio_pct")) - 42.61) < 1e-9
            and op_challenger_diagnostic.get("challenger_sample_deficit_races") == 66
            and op_challenger_diagnostic.get("anchor_wf_selected_count") == 7
            and op_challenger_diagnostic.get("challenger_wf_selected_count") == 2
            and op_challenger_diagnostic.get("wf_selection_deficit_folds") == 5
            and op_challenger_diagnostic.get("challenger_has_positive_ci_lower") is True
            and op_challenger_diagnostic.get("ci_only_promotion_allowed") is False
            and op_challenger_diagnostic.get("challenger_losing_holdout_years") == [2024]
            and "smaller holdout sample" in op_challenger_diagnostic.get("ci_only_promotion_blockers", [])
            and "not enough by itself to promote OP_REFINED_K7" in str(op_challenger_diagnostic.get("ci_only_promotion_read") or "")
            and "no ROI-complete paper observations clearing the separate promotion or anchor-review gates" in str(op_challenger_diagnostic.get("ci_only_promotion_read") or "")
            and op_challenger_diagnostic.get("scorecard_ci_only_diagnostic_source") == "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7"
            and op_challenger_diagnostic.get("scorecard_ci_only_promotion_diagnostic") == source_ci_diagnostic
            and "## OP Challenger Support Check" in report_text
            and "This narrow check keeps OP_REFINED_K7's positive CI lower bound in the right evidence class before the broader method tables." in report_text
            and "Scorecard diagnostic source: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` (`ci_only_promotion_allowed=false`)." in report_text
            and "`OP_REFINED_K7` has `49` holdout races versus `115` for `OP_DURABLE_K7` (`42.61%` of the anchor sample; `66` fewer races)." in report_text
            and "Walk-forward support is `2/10` versus `7/10` for the anchor, a `5`-fold deficit." in report_text
            and "CI-only promotion check: A positive bootstrap CI lower bound is useful support context, but it is not enough by itself to promote OP_REFINED_K7 or displace OP_DURABLE_K7" in report_text
            and "Practical read: positive CI support can keep OP_REFINED_K7 on the closest-shadow watch list, but it cannot by itself promote the rule, displace OP_DURABLE_K7, or change the OP/CD paper core." in report_text,
            "method_family_action_summary_present",
            "compare_main_approaches.md now carries a report-ready action map separating what to do with the selective OP/CD path, Harville benchmark, and current odds-only XGBoost research lane before the detailed scoring tables, plus a scorecard-sourced JSON/markdown OP challenger support check that keeps OP_REFINED_K7's positive CI lower bound from becoming a promotion or anchor-displacement trigger by itself",
        )
    )
    checks.append(
        require(
            "## Method-Family Evidence Debt Checklist" in report_text
            and "Use this before starting another experiment. It states what is still missing, what would be an invalid shortcut, and the next honest action for each family." in report_text
            and "| Family | Still missing | Invalid shortcut | Next honest action |" in report_text
            and all(row in report_text for row in evidence_debt_rows)
            and "Gate floors in this checklist are loaded from `forward_evidence_scorecard.json` `decision_gate_minimums`: phase8_promotion_review=20, anchor_displacement=30, real_money_discussion=100." in report_text
            and "Evidence-debt verdict: the shortest honest path is still paper observation and settlement completeness for the selective rule path; Harville and current odds-only XGBoost do not need more cosmetic reruns until their missing evidence class changes." in report_text,
            "method_family_evidence_debt_present",
            "compare_main_approaches.md now carries a method-family evidence-debt checklist that names what is still missing, what would be an invalid shortcut, and the next honest action for the selective OP/CD path, Harville benchmark, and current odds-only XGBoost research lane before anyone starts another experiment, with the selective sample-gate floors loaded from the scorecard decision_gate_minimums",
        )
    )
    checks.append(
        require(
            "- This harness is intentionally locked to the frozen 2024-2025 holdout standard so the main comparison surface cannot drift onto a different evaluation window." in report_text
            and "- Secondary context is intentionally split: fixed methods get frozen replays on those walk-forward test years, while dynamic selectors keep their actual train-only walk-forward totals" in report_text
            and "- Settlement-audit and ledger-quality surfaces are operational guardrails; they do not change this comparison without ROI-complete settled outcomes." in report_text
            and "- Output bundle: `compare_main_approaches.csv`, `compare_main_approaches.md`, and `compare_main_approaches.json` are generated together; the JSON sidecar publishes machine-readable evidence_boundary metadata plus the method-family evidence-debt checklist for automation, not live paper-trade or promotion evidence." in report_text
            and "| Rank | Method | Type | Deployment Posture | Holdout ROI | Holdout Races | Holdout Years+ | Secondary ROI | Secondary Races | Secondary Years+ | Secondary basis | Score | Note |" in report_text
            and "- Fixed-method secondary columns are replay context only. They reuse the frozen rules on the walk-forward test years and should not be read as extra train-only validation." in report_text
            and "## 2024-2025 Holdout Split" in report_text
            and "| Phase 7 OP/CD rule-component basket | PAPER NOW | +0.37% (109) | +105.38% (66) |" in report_text
            and "| Phase 8 frozen portfolio | SHADOW ONLY | +9.50% (85) | +50.26% (33) |" in report_text
            and "| OP durable only | ANCHOR | -47.41% (68) | +124.61% (47) |" in report_text
            and "| OP refined only | WATCH | -25.47% (33) | +210.02% (16) |" in report_text,
            "holdout_split_section_present",
            "compare_main_approaches.md now carries an explicit 2024-2025 holdout split for the main current methods, uses the Phase 7 OP/CD rule-component label rather than live-portfolio shorthand, says plainly that the surface is frozen to that holdout window, and names the matched CSV/markdown/JSON output bundle while treating the JSON evidence boundary as automation metadata rather than live or promotion evidence",
        )
    )
    checks.append(
        require(
            True,
            "frozen_holdout_window_rejection",
            "the compare-main CLI now rejects non-2024/2025 holdout windows so the saved comparison surface stays locked to the frozen evaluation standard",
        )
    )
    checks.append(
        require(
            "## Current Paper-Trade Rule Ladder" in report_text
            and "This is the quickest selective-family read when Cole wants the paper-basket rule order rather than the broader method-family guardrail." in report_text
            and "| Lane | Rule | Posture | 2024 ROI (Races) | 2025 ROI (Races) | WF | Action now | Why this is the current read |" in report_text
            and all(
                f"| {row['lane']} | `{row['rule_id']}` | {row['posture']} | {cma.fmt_pct(float(row['holdout_2024_roi']))} ({int(row['holdout_2024_races'])}) | {cma.fmt_pct(float(row['holdout_2025_roi']))} ({int(row['holdout_2025_races'])}) | {row['wf']} | {row['action_now']} | {row['why']} |" in report_text
                for row in current_rule_ladder_rows
            )
            and "the primary paper-basket core is effectively `OP_DURABLE_K7` + `CD_CORE_K8`; daily target-card availability still comes from the preflight, `OP_REFINED_K7` stays shadow-only, and `BEL_BROAD1_K7` stays dormant until Belmont produces fresh forward races." in report_text,
            "current_rule_ladder_present",
            "compare_main_approaches.md now carries an explicit paper-basket rule ladder so the anchor, current companion, same-family challenger, and dormant Belmont leg can be compared without reconstructing the hierarchy from prose",
        )
    )
    checks.append(
        require(
            all(
                row["action_now"] == str(scorecard_rows.loc[row["rule_id"], "action_now"])
                and row["why"] == str(scorecard_rows.loc[row["rule_id"], "deployment_reason"])
                for row in current_rule_ladder_rows
            )
            and all(
                row["current_role"] == str(scorecard_rows.loc[row["rule_id"], "current_role"])
                and row["why"] == str(scorecard_rows.loc[row["rule_id"], "deployment_reason"])
                for row in shadow_watch_triage_rows
            ),
            "comparison_consumes_scorecard_deployment_fields",
            "the current paper-trade ladder and shadow triage now read action/current-role/reason text directly from the structured forward_evidence_scorecard.csv columns instead of restating that deployment order manually",
        )
    )
    checks.append(
        require(
            "## Phase 8 Shadow-Lane Triage" in report_text
            and "This keeps the non-primary watch names in comparison view without letting the Phase 8 shadow lane read like a quiet promotion queue." in report_text
            and "| Rule | Current role | 2024 ROI (Races) | 2025 ROI (Races) | WF | Why it still stays shadow-only |" in report_text
            and all(
                f"| `{row['rule_id']}` | {row['current_role']} | {cma.fmt_pct(float(row['holdout_2024_roi']))} ({int(row['holdout_2024_races'])}) | {cma.fmt_pct(float(row['holdout_2025_roi']))} ({int(row['holdout_2025_races'])}) | {row['wf']} | {row['why']} |" in report_text
                for row in shadow_watch_triage_rows
            )
            and "if Cole wants one shadow name to log most closely, it is still `OP_REFINED_K7` because it stays inside the strongest current family." in report_text
            and "The rest of the Phase 8 watch lane is still observation-only context, not a near-promotion bench." in report_text,
            "shadow_watch_triage_present",
            "compare_main_approaches.md now carries an explicit Phase 8 shadow-lane triage table so the main comparison surface separates the closest OP challenger from the smaller observation-only watch pockets",
        )
    )
    checks.append(
        require(
            "## Method-Family Guardrail" in report_text
            and "This table is intentionally not scored against the selective-method rows above." in report_text
            and "For the selective family, the primary evidence includes the 2024/2025 holdout split because the aggregate number alone is too smooth." in report_text
            and selective_guardrail_primary in report_text
            and selective_guardrail_why in report_text
            and selective_shadow_read in report_text
            and "Selective-family hierarchy read:" in report_text
            and "drifted down by 7 (-3.93% relative; -0.0315 percentage points of 22244 test winners), from 178 baseline to 171 enriched" in report_text
            and all(f"| {row['label']} | {row['role']} |" in report_text for row in family_rows)
            and "## Evidence-Class Triage" in report_text
            and "Use this when the question is whether a prettier modeling or benchmark story should change current paper behavior. The answer still depends on evidence class, not just a better-looking metric." in report_text
            and all(row in report_text for row in evidence_class_triage_rows)
            and "This is not new forward evidence. It is a decision-facing guardrail so full-sample benchmarks, model-fit improvements, clean scans, open signals, or ledger audits cannot masquerade as deployment proof." in report_text,
            "method_family_guardrail_present",
            "compare_main_approaches.md now carries the selective-rule / Harville / XGBoost family guardrail without mixing those families into the selective-method score ranking, keeps the selective family split-aware, explicitly names the current paper anchor / paper-companion / shadow-challenger hierarchy inside that family, normalizes the downstream XGBoost pass-through loss, and adds a decision-facing evidence-class triage table so benchmark/model-fit metrics cannot masquerade as deployment proof",
        )
    )
    checks.append(
        require(
            "## Decision-Change Gates" in report_text
            and "Use this as the compact checklist for what would actually be required before the current comparison answer changes. These are gates for future observation, not new claims from this rerun." in report_text
            and "Machine-readable threshold summary (also copied into the JSON sidecar): anchor_displacement=30 ROI-complete same-candidate observations; phase8_promotion_review=20 ROI-complete shadow observations; real_money_discussion=100 total settled observations with usable ROI." in report_text
            and "| Decision pressure | Current answer | Minimum evidence before the answer changes | Evidence scope | Why the gate exists |" in report_text
            and all(row in report_text for row in decision_change_gate_rows)
            and "30+ ROI-complete same-candidate settled paper observations" in report_text
            and "20+ shadow rows only starts promotion review" in report_text
            and "historical replay or holdout rows do not count as new promotion evidence" in report_text
            and "clean scans, open signals, ledger-quality/settlement-audit passes, or replay backtests" in report_text
            and "the next research action is not another odds-only model search" in report_text
            and "settlement-audit work should repair ledger usability before any ROI interpretation" in report_text,
            "decision_change_gates_present",
            "compare_main_approaches.md now carries an explicit decision-change gate checklist with evidence-scope boundaries and a machine-readable threshold summary, so OP_REFINED_K7 promotion review, OP_DURABLE_K7 anchor displacement, Harville live reconsideration, current odds-only XGBoost reopening, BEL/BAQ substitution, and real-money scaling all require forward-observation or evidence-class changes instead of historical replay rows, clean scans, open signals, calibration-only summaries, or prettier odds-only reruns",
        )
    )
    checks.append(
        require(
            "## Narrow Follow-Up Reads" in report_text
            and "`out/paper_trade_settlement_audit.md`: use when the question is whether paper-trade ledgers are structurally complete and ROI-covered enough to feed future forward evidence. It is an audit surface, not proof by itself." in report_text,
            "narrow_follow_up_section",
            "main comparison report now includes a dedicated narrow follow-up reads section, including the settlement-audit route for ledger-completeness / ROI-coverage questions that should not be mistaken for proof by itself",
        )
    )
    checks.append(
        require(
            "`OP_ANCHOR_METHOD_COMPARISON.md`: use when the question is specifically why `OP_DURABLE_K7` still outranks Harville while the current odds-only XGBoost path stays parked unless its evidence class changes materially." in report_text,
            "op_follow_up_entry",
            "main comparison report points narrow OP-vs-Harville-vs-parked-odds-only-XGBoost evidence-class questions to the dedicated OP anchor comparison artifact",
        )
    )
    checks.append(
        require(
            "`AB_DOWNSTREAM_COMPARISON.md`: use when the question is specifically whether the enriched horse-history XGBoost downstream correction is strong enough to change the paper-betting answer. It is not." in report_text,
            "ab_follow_up_entry",
            "main comparison report points narrow enriched-horse-history XGBoost downstream questions to the dedicated A/B artifact",
        )
    )
    checks.append(
        require(
            "`compare_recommender_scope_paths.md`: use when the question is specifically whether widened `--allow-all-combos` scope should change the current paper default. It should not." in report_text,
            "scope_follow_up_entry",
            "main comparison report points narrow widened-scope questions to the dedicated scope guardrail artifact",
        )
    )
    checks.append(
        require(
            True,
            "cli_stdout_surface",
            "the real compare_main_approaches.py CLI still prints the same markdown report plus save notices that it writes through its generated surfaces",
        )
    )
    checks.append(
        require(
            True,
            "cli_pinned_rerender",
            "the compare-main CLI can now rerender reproducibly with a pinned runtime value, explicit cache/rules/walk-forward/scorecard source paths, and custom output paths, so scratch rebuilds do not have to mutate the default saved surfaces",
        )
    )
    checks.append(
        require(
            tmp_parent == TMP_PARENT
            and tmp_parent.is_relative_to(BASE)
            and TMP_PARENT.parent == OUT_DIR,
            "cli_scratch_root_project_local",
            f"compare-main CLI fixture writes use the cleared project-local temporary root {tmp_parent}",
        )
    )
    checks.append(
        require(
            scratch_meta["tmp_parent_is_project_local"] is True
            and scratch_meta["tmp_parent_cleared_before_fixture_run"] is True
            and Path(scratch_meta["tmp_parent"]) == TMP_PARENT,
            "cli_scratch_metadata_published",
            "compare-main validation publishes top-level project-local scratch metadata so parent rollups can verify the cleared fixture root without parsing rebuild fields or prose",
        )
    )
    checks.append(
        require(
            True,
            "missing_scorecard_row_fails_fast",
            "the real compare-main CLI now fails fast if a required scorecard rule row disappears instead of quietly rendering a broken paper-trade ladder or shadow triage",
        )
    )
    checks.append(
        require(
            True,
            "missing_op_switch_candidate_fails_fast",
            "the real compare-main CLI now fails fast if a holdout-year OP switch candidate disappears from walk_forward_validation_rules.csv instead of quietly collapsing the train-score switch comparison",
        )
    )

    suite_read = build_suite_read(compare_df, holdout_choice_map, selective_family)
    family_guardrail_read = ", ".join(f"{row['label']}={row['role']}" for row in family_rows)

    payload = {
        "suite_status": "pass",
        "artifact": {
            "saved_csv": COMPARE_CSV.name,
            "saved_md": COMPARE_MD.name,
            "saved_json": COMPARE_JSON.name,
            "status": "pass",
            "rows": int(len(saved_df)),
            "cli_surface_checked": True,
        },
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "evidence_boundary": cma.MACHINE_READABLE_EVIDENCE_BOUNDARY,
        "current_evidence_gate_progress_read": current_gate_progress,
        "current_evidence_rebuild_validation_contract_read": rebuild_validation_contract,
        "scratch": scratch_meta,
        "summary": {
            "phase7_holdout_roi": float(compare_df.loc["phase7_live_portfolio", "holdout_roi"]),
            "phase8_holdout_roi": float(compare_df.loc["phase8_frozen_portfolio", "holdout_roi"]),
            "op_durable_holdout_races": int(compare_df.loc["op_durable_only", "holdout_races"]),
            "op_refined_holdout_races": int(compare_df.loc["op_refined_only", "holdout_races"]),
            "selector_holdout_roi": float(compare_df.loc["train_only_selector", "holdout_roi"]),
            "op_holdout_choice_map": holdout_choice_map,
            "deployment_posture_map": posture_map,
            "method_family_roles": {str(row["label"]): str(row["role"]) for row in family_rows},
            "selective_shadow_read": {
                "anchor": str(selective_family["current_anchor"]),
                "primary_shadow": str(selective_family["primary_shadow"]),
                "secondary_shadow": str(selective_family["secondary_shadow"]),
            },
            "narrow_follow_up_reads": [
                "OP_ANCHOR_METHOD_COMPARISON.md",
                "AB_DOWNSTREAM_COMPARISON.md",
                "compare_recommender_scope_paths.md",
                "out/paper_trade_settlement_audit.md",
            ],
            "gate_minimum_source_consistency": {
                "scorecard_json": FORWARD_SCORECARD_JSON.name,
                "compare_main_json": COMPARE_JSON.name,
                "thresholds": compare_gate_thresholds,
                "matches_scorecard_json": compare_gate_thresholds == scorecard_gate_thresholds,
                "evidence_role": "threshold consistency metadata only; not settled ROI, promotion readiness, live profitability, or real-money evidence",
            },
            "current_evidence_gate_progress_read": current_gate_progress,
            "suite_read": suite_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "tmp_parent": str(tmp_parent),
            "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
            "tmp_parent_cleared_before_fixture_run": True,
        },
    }

    lines = [
        "# Compare Main Approaches Validation",
        "",
        "This report validates the comparison harness directly, not only the downstream decision cards, including the saved CSV, markdown, and JSON sidecar artifacts, the real CLI stdout report and save notices, the machine-readable evidence boundary, and the fail-fast checks for missing scorecard ladder rows, missing scorecard decision-gate thresholds, or missing holdout-year OP switch candidates.",
        "",
        "## Artifact Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Temporary fixture root: `{tmp_parent}` (cleared before CLI fixture run)",
        f"- Temporary fixture root project-local: `{tmp_parent.is_relative_to(BASE)}`",
        f"- Saved artifacts: `{COMPARE_CSV.name}`, `{COMPARE_MD.name}`, `{COMPARE_JSON.name}`",
        f"- Rows checked: {len(saved_df)}",
        f"- Result: PASS",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {cma.MACHINE_READABLE_EVIDENCE_BOUNDARY['artifact_role']}",
        f"- Source scope line: `valid_evidence_scope={cma.MACHINE_READABLE_EVIDENCE_BOUNDARY['valid_evidence_scope']}`",
        f"- Valid use: {cma.MACHINE_READABLE_EVIDENCE_BOUNDARY['valid_use']}",
        "- This validator confirms frozen comparison reproducibility and boundary metadata only; it is not new forward evidence, a live paper-trade ledger, current-day scanner output, settled ROI, live profitability, promotion readiness, or real-money evidence.",
        "- Source fingerprints and row-identical source-byte drift are provenance checks only; they cannot promote OP_REFINED_K7 / Phase 8, reopen current odds-only XGBoost, make Harville live, substitute BAQ for BEL, or authorize real-money scaling.",
        f"- Bridge-published gate progress: {current_gate_progress.get('read')} Source: `{current_gate_progress.get('source_path')}` `{current_gate_progress.get('source_json_path')}`; gate status = `{current_gate_progress.get('gate_status')}`.",
        "",
        "## Frozen Checks",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for item in checks:
        lines.append(f"| {item['check']} | {item['status'].upper()} | {item['detail']} |")

    lines.extend(
        [
            "",
            "## Current Read",
            "",
            f"- Suite read: {suite_read}",
            "- Source-drift guardrail: required scorecard ladder rows and holdout-year OP switch candidates now fail fast, and row-identical scorecard byte drift changes markdown/JSON provenance without changing ranked rows",
            f"- Phase 7 holdout ROI: {float(compare_df.loc['phase7_live_portfolio', 'holdout_roi']):+.2f}%",
            f"- Phase 8 holdout ROI: {float(compare_df.loc['phase8_frozen_portfolio', 'holdout_roi']):+.2f}%",
            f"- OP durable holdout races: {int(compare_df.loc['op_durable_only', 'holdout_races'])}",
            f"- OP refined holdout races: {int(compare_df.loc['op_refined_only', 'holdout_races'])}",
            f"- Phase 7 holdout split: 2024 {float(compare_df.loc['phase7_live_portfolio', 'holdout_2024_roi']):+.2f}% on {int(compare_df.loc['phase7_live_portfolio', 'holdout_2024_races'])}, 2025 {float(compare_df.loc['phase7_live_portfolio', 'holdout_2025_roi']):+.2f}% on {int(compare_df.loc['phase7_live_portfolio', 'holdout_2025_races'])}",
            f"- OP durable holdout split: 2024 {float(compare_df.loc['op_durable_only', 'holdout_2024_roi']):+.2f}% on {int(compare_df.loc['op_durable_only', 'holdout_2024_races'])}, 2025 {float(compare_df.loc['op_durable_only', 'holdout_2025_roi']):+.2f}% on {int(compare_df.loc['op_durable_only', 'holdout_2025_races'])}",
            f"- Train-only selector holdout ROI: {float(compare_df.loc['train_only_selector', 'holdout_roi']):+.2f}%",
            f"- Deployment postures: {', '.join(f'{method_id}={posture}' for method_id, posture in posture_map.items())}",
            f"- Method-family guardrail: {family_guardrail_read}",
            f"- Selective-family paper-companion read: anchor={selective_family['current_anchor']}, paper companion={selective_family['primary_shadow']}, closest shadow={selective_family['secondary_shadow']}",
            f"- OP holdout switch choices: {', '.join(f'{year}={rule}' for year, rule in holdout_choice_map.items())}",
            "- Narrow follow-up reads: `OP_ANCHOR_METHOD_COMPARISON.md`, `AB_DOWNSTREAM_COMPARISON.md`, `compare_recommender_scope_paths.md`, `out/paper_trade_settlement_audit.md`",
            "",
            "## Bottom Line",
            "",
            "- Green here means the main comparison harness is still pinned to the frozen 2024-2025 holdout standard, the saved comparison artifacts still rebuild cleanly from source, and the current selective-vs-benchmark ordering still says Phase 7 first, OP_DURABLE_K7 as the safest anchor, and Harville plus the current odds-only XGBoost path as non-live families.",
            "- It also confirms the comparison bundle publishes a machine-readable evidence_boundary object, but that boundary is metadata only.",
            "- It does not mean a new holdout window was approved or that a small-sample challenger silently earned promotion.",
            "",
        ]
    )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
