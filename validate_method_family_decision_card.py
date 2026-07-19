#!/usr/bin/env python3
"""
Validation for the method-family decision card.

Purpose:
- keep the method-family artifact reproducible
- pin the saved CSV / markdown surfaces against a fresh rebuild
- pin the real CLI stdout report plus save notices
- pin the current selective-rule / Harville / XGBoost ordering
- make sure dead-end method families stay retired in report-safe ways
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.testing import assert_frame_equal

import method_family_decision_card as mfd

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "out" / "status_validation" / "method_family_decision_card"
OUT_MD = OUT_DIR / "method_family_decision_card_validation.md"
OUT_JSON = OUT_DIR / "method_family_decision_card_validation.json"
TMP_PARENT = OUT_DIR / "_tmp"
REBUILD_COMMAND = "python3 validate_method_family_decision_card.py"
METHOD_SCRIPT = BASE / "method_family_decision_card.py"
METHOD_CSV = BASE / "method_family_decision_card.csv"
METHOD_MD = BASE / "METHOD_FAMILY_DECISION.md"
COMPARE_CSV = BASE / "compare_main_approaches.csv"
COMPARE_JSON = BASE / "compare_main_approaches.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
BACKTEST_CSV = BASE / "backtest_summary.csv"
AB_JSON = BASE / "ab_downstream_comparison_results.json"
CROSS_FAMILY_CSV = BASE / "cross_family_decision_card.csv"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
SCORECARD_AUDIT_MD = BASE / "SCORECARD_RANKING_CONTRACT_AUDIT.md"
SCORECARD_AUDIT_JSON = BASE / "scorecard_ranking_contract_audit.json"


def prepare_tmp_parent() -> Path:
    if TMP_PARENT.exists():
        shutil.rmtree(TMP_PARENT)
    TMP_PARENT.mkdir(parents=True, exist_ok=True)
    return TMP_PARENT


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


def compare_like_saved(saved: pd.DataFrame, rebuilt: pd.DataFrame) -> None:
    missing_cols = [col for col in saved.columns if col not in rebuilt.columns]
    if missing_cols:
        raise AssertionError(f"rebuilt method-family frame is missing saved columns {missing_cols}")
    rebuilt = rebuilt[saved.columns]
    assert_frame_equal(
        normalize_frame(saved, "family_id"),
        normalize_frame(rebuilt, "family_id"),
        check_dtype=False,
        check_exact=False,
        atol=1e-9,
        rtol=0,
    )


def build_expected_cli_stdout(report_text: str, csv_name: str = "method_family_decision_card.csv", md_name: str = "METHOD_FAMILY_DECISION.md") -> str:
    return report_text + f"Saved: {csv_name}\nSaved: {md_name}\n"


def load_backtest_rows() -> list[dict[str, str]]:
    with BACKTEST_CSV.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def parse_source_provenance_table(markdown_text: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    in_table = False
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if line == "| Source | Path | Bytes | SHA-256 |":
            in_table = True
            continue
        if not in_table:
            continue
        if line == "|---|---|---:|---|":
            continue
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 4:
            continue
        source, path, byte_count, sha = cells
        rows[source.strip("`")] = {
            "path": path.strip("`"),
            "bytes": int(byte_count),
            "sha256": sha.strip("`"),
        }
    return rows


def source_provenance_matches_disk(markdown_text: str) -> bool:
    markdown_rows = parse_source_provenance_table(markdown_text)
    expected = mfd.source_file_fingerprints()
    if set(markdown_rows) != set(expected):
        return False
    for label, expected_fingerprint in expected.items():
        if markdown_rows[label] != expected_fingerprint:
            return False
    return True


def load_operator_boundary() -> dict[str, Any]:
    return mfd.load_current_operator_boundary(COMPARE_JSON)


def load_current_gate_progress() -> dict[str, Any]:
    return mfd.load_current_gate_progress(CURRENT_EVIDENCE_JSON)


def load_rebuild_validation_contract() -> dict[str, Any]:
    return mfd.load_rebuild_validation_contract(CURRENT_EVIDENCE_JSON)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_parent = prepare_tmp_parent()
    scratch = {
        "tmp_parent": str(tmp_parent),
        "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
        "tmp_parent_cleared_before_fixture_run": True,
    }

    saved_df = pd.read_csv(METHOD_CSV)
    rebuilt_df = pd.DataFrame(mfd.build_rows())
    compare_like_saved(saved_df, rebuilt_df)
    saved_md = METHOD_MD.read_text(encoding="utf-8")
    rebuilt_md = mfd.render_md(mfd.build_rows())
    scorecard_ranking_contract = mfd.load_scorecard_ranking_contract(SCORECARD_JSON)
    scorecard_decision_gates = mfd.load_scorecard_decision_gate_minimums(SCORECARD_JSON)
    scorecard_ci_only_diagnostic = mfd.load_scorecard_ci_only_diagnostic(SCORECARD_JSON)
    operator_boundary = load_operator_boundary()
    current_gate_progress = load_current_gate_progress()
    rebuild_validation_contract = load_rebuild_validation_contract()
    scorecard_audit_route = mfd.load_scorecard_audit_route(CURRENT_EVIDENCE_JSON)
    operator_read_gate = operator_boundary["operator_read_gate"]
    decision_gates = mfd.load_decision_change_gate_minimums(COMPARE_JSON)
    operator_gate_status = operator_read_gate.get("gate_status")
    operator_gate_read = str(operator_read_gate.get("read") or "")
    if operator_read_gate.get("requires_refresh_before_evidence_read"):
        operator_read_gate_branch_ok = (
            operator_gate_status == "refresh_required_before_evidence_read"
            and operator_read_gate.get("recommended_command") == "./run_daily_portfolio_observation.sh"
            and operator_read_gate.get("has_wrapper_refresh_action") is True
            and "Refresh/recheck with `./run_daily_portfolio_observation.sh`" in operator_gate_read
            and "not a no-target, clean-empty, bet-readiness, settled-ROI" in operator_gate_read
        )
    else:
        operator_read_gate_branch_ok = (
            operator_gate_status == "current_operator_routing_context_only"
            and operator_read_gate.get("recommended_command") == operator_boundary.get("best_action_command")
            and operator_read_gate.get("has_wrapper_refresh_action") is False
            and "current operator routing context" in operator_gate_read
            and "not settled ROI, promotion readiness, live-profitability, bankroll, or real-money evidence"
            in operator_gate_read
        )

    checks: list[dict[str, Any]] = []
    checks.append(
        require(
            saved_md == rebuilt_md,
            "markdown_matches_rebuild",
            "METHOD_FAMILY_DECISION.md still matches a fresh rebuild from method_family_decision_card.py",
        )
    )

    with tempfile.TemporaryDirectory(prefix="method_family_cli_", dir=tmp_parent) as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        pinned_dir = tmpdir / "pinned_out"
        pinned_csv = pinned_dir / "method_family_custom.csv"
        pinned_md = pinned_dir / "METHOD_FAMILY_CUSTOM.md"
        alt_compare_csv = tmpdir / "alt_compare_main.csv"
        alt_compare_json = tmpdir / "alt_compare_main.json"
        alt_current_evidence_json = tmpdir / "alt_current_evidence_summary.json"
        alt_cross_family_csv = tmpdir / "alt_cross_family_decision.csv"
        alt_scorecard_json = tmpdir / "alt_forward_evidence_scorecard.json"
        alt_backtest_csv = tmpdir / "alt_backtest_summary.csv"
        alt_ab_json = tmpdir / "alt_ab_downstream_comparison_results.json"
        custom_cross_family_csv = tmpdir / "custom_cross_family_decision.csv"
        custom_out_dir = tmpdir / "custom_hierarchy_out"
        custom_csv = custom_out_dir / "method_family_custom_hierarchy.csv"
        custom_md = custom_out_dir / "METHOD_FAMILY_CUSTOM_HIERARCHY.md"
        missing_compare_csv = tmpdir / "missing_train_only_compare.csv"
        missing_cross_family_csv = tmpdir / "missing_primary_shadow_cross_family.csv"
        missing_backtest_csv = tmpdir / "missing_harville_backtest.csv"
        missing_ab_json = tmpdir / "missing_ab_delta.json"
        missing_scorecard_json = tmpdir / "missing_ranking_contract_scorecard.json"
        missing_scorecard_gate_json = tmpdir / "missing_decision_gate_scorecard.json"
        missing_scorecard_audit_route_json = tmpdir / "missing_scorecard_audit_route_current_evidence.json"
        malformed_scorecard_gate_json = tmpdir / "malformed_decision_gate_scorecard.json"
        nonpositive_phase8_scorecard_gate_json = tmpdir / "nonpositive_phase8_gate_scorecard.json"
        nonpositive_real_money_scorecard_gate_json = tmpdir / "nonpositive_real_money_gate_scorecard.json"
        missing_no_baq_scorecard_gate_json = tmpdir / "missing_no_baq_gate_scorecard.json"
        missing_ci_only_scorecard_json = tmpdir / "missing_ci_only_scorecard.json"
        missing_compare_json = tmpdir / "missing_operator_boundary_compare_main.json"
        bad_generated_at_compare_json = tmpdir / "bad_generated_at_compare_main.json"
        missing_freshness_reference_compare_json = tmpdir / "missing_freshness_reference_compare_main.json"
        false_refresh_boundary_flag_compare_json = tmpdir / "false_refresh_boundary_flag_compare_main.json"
        false_refresh_accounting_flag_compare_json = tmpdir / "false_refresh_accounting_flag_compare_main.json"
        missing_decision_gates_compare_json = tmpdir / "missing_decision_gates_compare_main.json"
        missing_rebuild_validation_contract_json = tmpdir / "missing_rebuild_validation_contract_current_evidence.json"
        weakened_rebuild_validation_contract_json = tmpdir / "weakened_rebuild_validation_contract_current_evidence.json"
        missing_contract_output_dir = tmpdir / "missing_contract_nested_output" / "artifacts"
        missing_contract_should_not_write_csv = missing_contract_output_dir / "missing_contract_should_not_write.csv"
        missing_contract_should_not_write_md = missing_contract_output_dir / "missing_contract_should_not_write.md"
        missing_scorecard_gate_output_dir = tmpdir / "missing_scorecard_gate_nested_output" / "artifacts"
        missing_scorecard_gate_should_not_write_csv = missing_scorecard_gate_output_dir / "missing_scorecard_gate_should_not_write.csv"
        missing_scorecard_gate_should_not_write_md = missing_scorecard_gate_output_dir / "missing_scorecard_gate_should_not_write.md"
        missing_scorecard_audit_route_output_dir = tmpdir / "missing_scorecard_audit_route_nested_output" / "artifacts"
        missing_scorecard_audit_route_should_not_write_csv = (
            missing_scorecard_audit_route_output_dir / "missing_scorecard_audit_route_should_not_write.csv"
        )
        missing_scorecard_audit_route_should_not_write_md = (
            missing_scorecard_audit_route_output_dir / "missing_scorecard_audit_route_should_not_write.md"
        )
        malformed_scorecard_gate_output_dir = tmpdir / "malformed_scorecard_gate_nested_output" / "artifacts"
        malformed_scorecard_gate_should_not_write_csv = malformed_scorecard_gate_output_dir / "malformed_scorecard_gate_should_not_write.csv"
        malformed_scorecard_gate_should_not_write_md = malformed_scorecard_gate_output_dir / "malformed_scorecard_gate_should_not_write.md"
        nonpositive_phase8_scorecard_gate_output_dir = (
            tmpdir / "nonpositive_phase8_scorecard_gate_nested_output" / "artifacts"
        )
        nonpositive_phase8_scorecard_gate_should_not_write_csv = (
            nonpositive_phase8_scorecard_gate_output_dir / "nonpositive_phase8_scorecard_gate_should_not_write.csv"
        )
        nonpositive_phase8_scorecard_gate_should_not_write_md = (
            nonpositive_phase8_scorecard_gate_output_dir / "nonpositive_phase8_scorecard_gate_should_not_write.md"
        )
        nonpositive_real_money_scorecard_gate_output_dir = (
            tmpdir / "nonpositive_real_money_scorecard_gate_nested_output" / "artifacts"
        )
        nonpositive_real_money_scorecard_gate_should_not_write_csv = (
            nonpositive_real_money_scorecard_gate_output_dir / "nonpositive_real_money_scorecard_gate_should_not_write.csv"
        )
        nonpositive_real_money_scorecard_gate_should_not_write_md = (
            nonpositive_real_money_scorecard_gate_output_dir / "nonpositive_real_money_scorecard_gate_should_not_write.md"
        )
        missing_no_baq_output_dir = tmpdir / "missing_no_baq_nested_output" / "artifacts"
        missing_no_baq_should_not_write_csv = missing_no_baq_output_dir / "missing_no_baq_should_not_write.csv"
        missing_no_baq_should_not_write_md = missing_no_baq_output_dir / "missing_no_baq_should_not_write.md"
        missing_ci_only_output_dir = tmpdir / "missing_ci_only_nested_output" / "artifacts"
        missing_ci_only_should_not_write_csv = missing_ci_only_output_dir / "missing_ci_only_should_not_write.csv"
        missing_ci_only_should_not_write_md = missing_ci_only_output_dir / "missing_ci_only_should_not_write.md"
        missing_operator_output_dir = tmpdir / "missing_operator_nested_output" / "artifacts"
        missing_operator_should_not_write_csv = missing_operator_output_dir / "missing_operator_should_not_write.csv"
        missing_operator_should_not_write_md = missing_operator_output_dir / "missing_operator_should_not_write.md"
        bad_generated_at_output_dir = tmpdir / "bad_generated_at_nested_output" / "artifacts"
        bad_generated_at_should_not_write_csv = bad_generated_at_output_dir / "bad_generated_at_should_not_write.csv"
        bad_generated_at_should_not_write_md = bad_generated_at_output_dir / "bad_generated_at_should_not_write.md"
        missing_freshness_output_dir = tmpdir / "missing_freshness_nested_output" / "artifacts"
        missing_freshness_should_not_write_csv = missing_freshness_output_dir / "missing_freshness_should_not_write.csv"
        missing_freshness_should_not_write_md = missing_freshness_output_dir / "missing_freshness_should_not_write.md"
        false_refresh_boundary_output_dir = tmpdir / "false_refresh_boundary_nested_output" / "artifacts"
        false_refresh_boundary_should_not_write_csv = false_refresh_boundary_output_dir / "false_refresh_boundary_should_not_write.csv"
        false_refresh_boundary_should_not_write_md = false_refresh_boundary_output_dir / "false_refresh_boundary_should_not_write.md"
        false_refresh_accounting_output_dir = tmpdir / "false_refresh_accounting_nested_output" / "artifacts"
        false_refresh_accounting_should_not_write_csv = false_refresh_accounting_output_dir / "false_refresh_accounting_should_not_write.csv"
        false_refresh_accounting_should_not_write_md = false_refresh_accounting_output_dir / "false_refresh_accounting_should_not_write.md"
        missing_gate_output_dir = tmpdir / "missing_gate_nested_output" / "artifacts"
        missing_gate_should_not_write_csv = missing_gate_output_dir / "missing_gate_should_not_write.csv"
        missing_gate_should_not_write_md = missing_gate_output_dir / "missing_gate_should_not_write.md"
        missing_rebuild_validation_contract_output_dir = (
            tmpdir / "missing_rebuild_validation_contract_nested_output" / "artifacts"
        )
        missing_rebuild_validation_contract_should_not_write_csv = (
            missing_rebuild_validation_contract_output_dir / "missing_rebuild_validation_contract_should_not_write.csv"
        )
        missing_rebuild_validation_contract_should_not_write_md = (
            missing_rebuild_validation_contract_output_dir / "missing_rebuild_validation_contract_should_not_write.md"
        )
        weakened_rebuild_validation_contract_output_dir = (
            tmpdir / "weakened_rebuild_validation_contract_nested_output" / "artifacts"
        )
        weakened_rebuild_validation_contract_should_not_write_csv = (
            weakened_rebuild_validation_contract_output_dir / "weakened_rebuild_validation_contract_should_not_write.csv"
        )
        weakened_rebuild_validation_contract_should_not_write_md = (
            weakened_rebuild_validation_contract_output_dir / "weakened_rebuild_validation_contract_should_not_write.md"
        )
        for src in [
            METHOD_SCRIPT,
            COMPARE_CSV,
            COMPARE_JSON,
            CURRENT_EVIDENCE_JSON,
            BACKTEST_CSV,
            AB_JSON,
            CROSS_FAMILY_CSV,
            SCORECARD_JSON,
            SCORECARD_AUDIT_MD,
            SCORECARD_AUDIT_JSON,
        ]:
            shutil.copy2(src, tmpdir / src.name)
        shutil.copy2(COMPARE_CSV, alt_compare_csv)
        shutil.copy2(COMPARE_JSON, alt_compare_json)
        shutil.copy2(CURRENT_EVIDENCE_JSON, alt_current_evidence_json)
        shutil.copy2(CROSS_FAMILY_CSV, alt_cross_family_csv)
        shutil.copy2(SCORECARD_JSON, alt_scorecard_json)
        shutil.copy2(BACKTEST_CSV, alt_backtest_csv)
        shutil.copy2(AB_JSON, alt_ab_json)
        cli_result = subprocess.run(
            [sys.executable, METHOD_SCRIPT.name],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        cli_csv = pd.read_csv(tmpdir / METHOD_CSV.name)
        compare_like_saved(saved_df, cli_csv)
        cli_report_text = (tmpdir / METHOD_MD.name).read_text(encoding="utf-8")
        if cli_report_text != rebuilt_md:
            raise AssertionError("CLI-generated METHOD_FAMILY_DECISION.md drifted from a fresh rebuild")
        expected_cli_stdout = build_expected_cli_stdout(cli_report_text)
        if cli_result.stdout != expected_cli_stdout:
            raise AssertionError("method_family_decision_card.py CLI stdout no longer matches its generated report plus save notices")

        pinned_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--compare-csv",
                str(alt_compare_csv),
                "--compare-json",
                str(alt_compare_json),
                "--current-evidence-json",
                str(alt_current_evidence_json),
                "--cross-family-csv",
                str(alt_cross_family_csv),
                "--scorecard-json",
                str(alt_scorecard_json),
                "--backtest-csv",
                str(alt_backtest_csv),
                "--ab-json",
                str(alt_ab_json),
                "--csv-output",
                str(pinned_csv),
                "--md-output",
                str(pinned_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        pinned_csv_df = pd.read_csv(pinned_csv)
        compare_like_saved(saved_df, pinned_csv_df)
        pinned_report_text = pinned_md.read_text(encoding="utf-8")
        pinned_rebuilt_md = mfd.render_md(
            mfd.build_rows(
                compare_csv=alt_compare_csv,
                cross_family_csv=alt_cross_family_csv,
                backtest_csv=alt_backtest_csv,
                ab_json=alt_ab_json,
            ),
            compare_csv_name=alt_compare_csv.name,
            compare_json_name=alt_compare_json.name,
            current_evidence_json_name=alt_current_evidence_json.name,
            cross_family_csv_name=alt_cross_family_csv.name,
            scorecard_json_name=alt_scorecard_json.name,
            backtest_csv_name=alt_backtest_csv.name,
            ab_json_name=alt_ab_json.name,
            csv_output_name=pinned_csv.name,
            md_output_name=pinned_md.name,
            scorecard_json_path=alt_scorecard_json,
            compare_json_path=alt_compare_json,
            current_evidence_json_path=alt_current_evidence_json,
            source_paths={
                "compare_main_approaches": alt_compare_csv,
                "compare_main_approaches_json": alt_compare_json,
                "current_evidence_summary": alt_current_evidence_json,
                "cross_family_decision_card": alt_cross_family_csv,
                "forward_evidence_scorecard": alt_scorecard_json,
                "backtest_summary": alt_backtest_csv,
                "ab_downstream_comparison": alt_ab_json,
            },
        )
        if pinned_report_text != pinned_rebuilt_md:
            raise AssertionError("Pinned/custom-output METHOD_FAMILY_DECISION.md drifted from a fresh rebuild")
        expected_pinned_stdout = build_expected_cli_stdout(pinned_report_text, csv_name=pinned_csv.name, md_name=pinned_md.name)
        if pinned_result.stdout != expected_pinned_stdout:
            raise AssertionError("Pinned/custom-output method_family_decision_card.py CLI stdout no longer matches its generated report plus save notices")

        custom_cross_df = pd.read_csv(alt_cross_family_csv)
        custom_ids = {
            "LIVE_DEFAULT": "ALT_ANCHOR_K7",
            "PRIMARY_SHADOW": "ALT_PAPER_COMPANION_K8",
            "SECONDARY_SHADOW": "ALT_CLOSEST_SHADOW_K7",
        }
        custom_cross_df["rule_id"] = custom_cross_df.apply(
            lambda row: custom_ids.get(str(row.get("shadow_rank", "")), row.get("rule_id", "")),
            axis=1,
        )
        custom_cross_df.to_csv(custom_cross_family_csv, index=False)
        custom_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--cross-family-csv",
                str(custom_cross_family_csv),
                "--scorecard-json",
                str(alt_scorecard_json),
                "--csv-output",
                str(custom_csv),
                "--md-output",
                str(custom_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        custom_csv_df = pd.read_csv(custom_csv).set_index("family_id")
        if str(custom_csv_df.loc["selective_rule_path", "current_anchor"]) != "ALT_ANCHOR_K7":
            raise AssertionError("custom cross-family LIVE_DEFAULT anchor did not reach the method-family CSV")
        if str(custom_csv_df.loc["selective_rule_path", "primary_shadow"]) != "ALT_PAPER_COMPANION_K8":
            raise AssertionError("custom cross-family PRIMARY_SHADOW paper companion did not reach the method-family CSV")
        if str(custom_csv_df.loc["selective_rule_path", "secondary_shadow"]) != "ALT_CLOSEST_SHADOW_K7":
            raise AssertionError("custom cross-family SECONDARY_SHADOW closest shadow did not reach the method-family CSV")
        custom_report_text = custom_md.read_text(encoding="utf-8")
        for expected in [
            "with ALT_ANCHOR_K7 still the safest anchor, but the recent path was uneven rather than a smooth two-year glide",
            "Current paper-basket companion read: `ALT_ANCHOR_K7` stays the safest anchor, `ALT_PAPER_COMPANION_K8` is the primary OP/CD paper-basket companion, and `ALT_CLOSEST_SHADOW_K7` remains the stronger same-family OP shadow challenger rather than a promoted default.",
            "`CROSS_FAMILY_DECISION.md`: use when the question is how the paper-basket companion and same-family OP shadow challenger line up behind `ALT_ANCHOR_K7`.",
            "`OP_ANCHOR_METHOD_COMPARISON.md`: use when the question is specifically why `ALT_ANCHOR_K7` still outranks Harville while the current odds-only XGBoost path stays parked unless its evidence class changes materially.",
        ]:
            if expected not in custom_report_text:
                raise AssertionError(f"custom cross-family hierarchy did not render dynamic method-family markdown text: {expected}")
        stale_default_fragments = [
            "with OP_DURABLE_K7 still the safest anchor, but the recent path was uneven rather than a smooth two-year glide",
            "line up behind `OP_DURABLE_K7`.",
            "why `OP_DURABLE_K7` still outranks Harville",
        ]
        for stale in stale_default_fragments:
            if stale in custom_report_text:
                raise AssertionError(f"custom cross-family hierarchy render still contains stale default anchor fragment: {stale}")
        expected_custom_stdout = build_expected_cli_stdout(custom_report_text, csv_name=custom_csv.name, md_name=custom_md.name)
        if custom_result.stdout != expected_custom_stdout:
            raise AssertionError("Custom-hierarchy method_family_decision_card.py CLI stdout no longer matches its generated report plus save notices")

        missing_compare_df = pd.read_csv(alt_compare_csv)
        missing_compare_df = missing_compare_df[missing_compare_df["method_id"] != "train_only_selector"].copy()
        missing_compare_df.to_csv(missing_compare_csv, index=False)
        missing_compare_result = subprocess.run(
            [sys.executable, METHOD_SCRIPT.name, "--compare-csv", str(missing_compare_csv)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_compare_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted compare_main_approaches.csv without train_only_selector")
        missing_compare_text = f"{missing_compare_result.stdout}\n{missing_compare_result.stderr}"
        if "missing required compare-main method rows: train_only_selector" not in missing_compare_text:
            raise AssertionError("compare-main failure no longer explains that train_only_selector is required for the method-family card")

        missing_cross_df = pd.read_csv(alt_cross_family_csv)
        missing_cross_df = missing_cross_df[missing_cross_df["shadow_rank"] != "PRIMARY_SHADOW"].copy()
        missing_cross_df.to_csv(missing_cross_family_csv, index=False)
        missing_cross_result = subprocess.run(
            [sys.executable, METHOD_SCRIPT.name, "--cross-family-csv", str(missing_cross_family_csv)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_cross_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted cross_family_decision_card.csv without PRIMARY_SHADOW")
        missing_cross_text = f"{missing_cross_result.stdout}\n{missing_cross_result.stderr}"
        if "missing required cross-family shadow rows: PRIMARY_SHADOW" not in missing_cross_text:
            raise AssertionError("cross-family failure no longer explains that PRIMARY_SHADOW is required for the method-family card")

        missing_backtest_df = pd.read_csv(alt_backtest_csv)
        missing_backtest_df = missing_backtest_df[missing_backtest_df["Strategy"] != "Harville-Top120"].copy()
        missing_backtest_df.to_csv(missing_backtest_csv, index=False)
        missing_backtest_result = subprocess.run(
            [sys.executable, METHOD_SCRIPT.name, "--backtest-csv", str(missing_backtest_csv)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_backtest_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted backtest_summary.csv without Harville-Top120")
        missing_backtest_text = f"{missing_backtest_result.stdout}\n{missing_backtest_result.stderr}"
        if "missing required backtest strategy rows: Harville-Top120" not in missing_backtest_text:
            raise AssertionError("backtest failure no longer explains that Harville-Top120 is required for the method-family card")

        missing_ab_payload = json.loads(alt_ab_json.read_text(encoding="utf-8"))
        del missing_ab_payload["ev_engine_comparison"]["delta"]
        missing_ab_json.write_text(json.dumps(missing_ab_payload, indent=2) + "\n", encoding="utf-8")
        missing_ab_result = subprocess.run(
            [sys.executable, METHOD_SCRIPT.name, "--ab-json", str(missing_ab_json)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_ab_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted AB JSON missing the delta block")
        missing_ab_text = f"{missing_ab_result.stdout}\n{missing_ab_result.stderr}"
        if "missing required JSON path: ev_engine_comparison.delta.ev_pass_count_delta" not in missing_ab_text:
            raise AssertionError("AB-json failure no longer explains the missing ev_engine_comparison.delta path for the method-family card")

        missing_contract_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        missing_contract_payload.pop("ranking_contract", None)
        missing_scorecard_json.write_text(json.dumps(missing_contract_payload, indent=2) + "\n", encoding="utf-8")
        missing_scorecard_json_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--scorecard-json",
                str(missing_scorecard_json),
                "--csv-output",
                str(missing_contract_should_not_write_csv),
                "--md-output",
                str(missing_contract_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_scorecard_json_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted a scorecard JSON missing ranking_contract")
        missing_scorecard_json_text = f"{missing_scorecard_json_result.stdout}\n{missing_scorecard_json_result.stderr}"
        if "missing ranking_contract" not in missing_scorecard_json_text:
            raise AssertionError("scorecard JSON failure no longer explains that ranking_contract is required for the method-family card")
        if missing_contract_output_dir.exists() or missing_contract_should_not_write_csv.exists() or missing_contract_should_not_write_md.exists():
            raise AssertionError("missing scorecard ranking-contract failure created output directories or wrote partial method-family artifacts before failing")

        missing_scorecard_gate_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        missing_scorecard_gate_payload.pop("decision_gate_minimums", None)
        missing_scorecard_gate_json.write_text(json.dumps(missing_scorecard_gate_payload, indent=2) + "\n", encoding="utf-8")
        missing_scorecard_gate_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--scorecard-json",
                str(missing_scorecard_gate_json),
                "--csv-output",
                str(missing_scorecard_gate_should_not_write_csv),
                "--md-output",
                str(missing_scorecard_gate_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_scorecard_gate_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted a scorecard JSON missing decision_gate_minimums")
        missing_scorecard_gate_text = f"{missing_scorecard_gate_result.stdout}\n{missing_scorecard_gate_result.stderr}"
        if "missing decision_gate_minimums" not in missing_scorecard_gate_text:
            raise AssertionError("scorecard JSON failure no longer explains that decision_gate_minimums is required for the method-family card")
        if (
            missing_scorecard_gate_output_dir.exists()
            or missing_scorecard_gate_should_not_write_csv.exists()
            or missing_scorecard_gate_should_not_write_md.exists()
        ):
            raise AssertionError("missing scorecard decision-gate failure created output directories or wrote partial method-family artifacts before failing")

        missing_scorecard_audit_route_payload = json.loads(alt_current_evidence_json.read_text(encoding="utf-8"))
        missing_scorecard_audit_route_payload.pop("scorecard_audit_route", None)
        missing_scorecard_audit_route_json.write_text(
            json.dumps(missing_scorecard_audit_route_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_scorecard_audit_route_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--current-evidence-json",
                str(missing_scorecard_audit_route_json),
                "--csv-output",
                str(missing_scorecard_audit_route_should_not_write_csv),
                "--md-output",
                str(missing_scorecard_audit_route_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_scorecard_audit_route_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted current_evidence_summary.json without scorecard_audit_route")
        missing_scorecard_audit_route_text = (
            f"{missing_scorecard_audit_route_result.stdout}\n{missing_scorecard_audit_route_result.stderr}"
        )
        if "missing scorecard_audit_route" not in missing_scorecard_audit_route_text:
            raise AssertionError("current-evidence JSON failure no longer explains that scorecard_audit_route is required")
        if (
            missing_scorecard_audit_route_output_dir.exists()
            or missing_scorecard_audit_route_should_not_write_csv.exists()
            or missing_scorecard_audit_route_should_not_write_md.exists()
        ):
            raise AssertionError("missing scorecard audit route created output directories or wrote partial method-family artifacts before failing")

        missing_rebuild_payload = json.loads((tmpdir / CURRENT_EVIDENCE_JSON.name).read_text(encoding="utf-8"))
        missing_rebuild_payload.pop("rebuild_validation_contract", None)
        missing_rebuild_validation_contract_json.write_text(
            json.dumps(missing_rebuild_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_rebuild_validation_contract_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--current-evidence-json",
                str(missing_rebuild_validation_contract_json),
                "--csv-output",
                str(missing_rebuild_validation_contract_should_not_write_csv),
                "--md-output",
                str(missing_rebuild_validation_contract_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_rebuild_validation_contract_result.returncode == 0:
            raise AssertionError(
                "method_family_decision_card.py unexpectedly accepted current_evidence_summary.json without rebuild_validation_contract"
            )
        missing_rebuild_validation_contract_text = (
            f"{missing_rebuild_validation_contract_result.stdout}\n{missing_rebuild_validation_contract_result.stderr}"
        )
        if "missing rebuild_validation_contract" not in missing_rebuild_validation_contract_text:
            raise AssertionError("current-evidence JSON failure no longer explains that rebuild_validation_contract is required")
        if (
            missing_rebuild_validation_contract_output_dir.exists()
            or missing_rebuild_validation_contract_should_not_write_csv.exists()
            or missing_rebuild_validation_contract_should_not_write_md.exists()
        ):
            raise AssertionError(
                "missing rebuild-validation-contract failure created output directories or wrote partial method-family artifacts before failing"
            )

        weakened_rebuild_payload = json.loads((tmpdir / CURRENT_EVIDENCE_JSON.name).read_text(encoding="utf-8"))
        weakened_rebuild_payload["rebuild_validation_contract"][
            "upstream_refresh_order_is_provenance_metadata_only"
        ] = False
        weakened_rebuild_validation_contract_json.write_text(
            json.dumps(weakened_rebuild_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        weakened_rebuild_validation_contract_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--current-evidence-json",
                str(weakened_rebuild_validation_contract_json),
                "--csv-output",
                str(weakened_rebuild_validation_contract_should_not_write_csv),
                "--md-output",
                str(weakened_rebuild_validation_contract_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if weakened_rebuild_validation_contract_result.returncode == 0:
            raise AssertionError(
                "method_family_decision_card.py unexpectedly accepted current_evidence_summary.json with a weakened rebuild_validation_contract"
            )
        weakened_rebuild_validation_contract_text = (
            f"{weakened_rebuild_validation_contract_result.stdout}\n"
            f"{weakened_rebuild_validation_contract_result.stderr}"
        )
        if (
            "rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true"
            not in weakened_rebuild_validation_contract_text
        ):
            raise AssertionError("current-evidence JSON failure no longer explains that the rebuild route must stay provenance metadata only")
        if (
            weakened_rebuild_validation_contract_output_dir.exists()
            or weakened_rebuild_validation_contract_should_not_write_csv.exists()
            or weakened_rebuild_validation_contract_should_not_write_md.exists()
        ):
            raise AssertionError(
                "weakened rebuild-validation-contract failure created output directories or wrote partial method-family artifacts before failing"
            )

        malformed_scorecard_gate_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        malformed_scorecard_gate_payload["decision_gate_minimums"]["anchor_displacement"][
            "min_roi_complete_settled_observations"
        ] = True
        malformed_scorecard_gate_json.write_text(json.dumps(malformed_scorecard_gate_payload, indent=2) + "\n", encoding="utf-8")
        malformed_scorecard_gate_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--scorecard-json",
                str(malformed_scorecard_gate_json),
                "--csv-output",
                str(malformed_scorecard_gate_should_not_write_csv),
                "--md-output",
                str(malformed_scorecard_gate_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if malformed_scorecard_gate_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted a boolean anchor-displacement gate floor")
        malformed_scorecard_gate_text = f"{malformed_scorecard_gate_result.stdout}\n{malformed_scorecard_gate_result.stderr}"
        if "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations must be a positive non-boolean integer" not in malformed_scorecard_gate_text:
            raise AssertionError("scorecard JSON failure no longer explains that boolean gate floors are malformed")
        if (
            malformed_scorecard_gate_output_dir.exists()
            or malformed_scorecard_gate_should_not_write_csv.exists()
            or malformed_scorecard_gate_should_not_write_md.exists()
        ):
            raise AssertionError("malformed scorecard gate floor created output directories or wrote partial method-family artifacts before failing")

        nonpositive_phase8_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        nonpositive_phase8_payload["decision_gate_minimums"]["phase8_promotion_review"][
            "min_roi_complete_settled_observations"
        ] = 0
        nonpositive_phase8_scorecard_gate_json.write_text(
            json.dumps(nonpositive_phase8_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        nonpositive_phase8_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--scorecard-json",
                str(nonpositive_phase8_scorecard_gate_json),
                "--csv-output",
                str(nonpositive_phase8_scorecard_gate_should_not_write_csv),
                "--md-output",
                str(nonpositive_phase8_scorecard_gate_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if nonpositive_phase8_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted a non-positive Phase 8 promotion-review gate floor")
        nonpositive_phase8_text = f"{nonpositive_phase8_result.stdout}\n{nonpositive_phase8_result.stderr}"
        if "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer" not in nonpositive_phase8_text:
            raise AssertionError("scorecard JSON failure no longer explains that non-positive Phase 8 gate floors are malformed")
        if (
            nonpositive_phase8_scorecard_gate_output_dir.exists()
            or nonpositive_phase8_scorecard_gate_should_not_write_csv.exists()
            or nonpositive_phase8_scorecard_gate_should_not_write_md.exists()
        ):
            raise AssertionError("non-positive Phase 8 scorecard gate floor created output directories or wrote partial method-family artifacts before failing")

        nonpositive_real_money_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        nonpositive_real_money_payload["decision_gate_minimums"]["real_money_discussion"][
            "min_total_settled_observations_with_usable_roi"
        ] = 0
        nonpositive_real_money_scorecard_gate_json.write_text(
            json.dumps(nonpositive_real_money_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        nonpositive_real_money_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--scorecard-json",
                str(nonpositive_real_money_scorecard_gate_json),
                "--csv-output",
                str(nonpositive_real_money_scorecard_gate_should_not_write_csv),
                "--md-output",
                str(nonpositive_real_money_scorecard_gate_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if nonpositive_real_money_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted a non-positive real-money discussion gate floor")
        nonpositive_real_money_text = f"{nonpositive_real_money_result.stdout}\n{nonpositive_real_money_result.stderr}"
        if "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer" not in nonpositive_real_money_text:
            raise AssertionError("scorecard JSON failure no longer explains that non-positive real-money gate floors are malformed")
        if (
            nonpositive_real_money_scorecard_gate_output_dir.exists()
            or nonpositive_real_money_scorecard_gate_should_not_write_csv.exists()
            or nonpositive_real_money_scorecard_gate_should_not_write_md.exists()
        ):
            raise AssertionError("non-positive real-money scorecard gate floor created output directories or wrote partial method-family artifacts before failing")

        missing_no_baq_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"]["also_requires"] = [
            item
            for item in missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"]["also_requires"]
            if item != mfd.NO_BAQ_AS_BEL_PREREQUISITE
        ]
        missing_no_baq_scorecard_gate_json.write_text(json.dumps(missing_no_baq_payload, indent=2) + "\n", encoding="utf-8")
        missing_no_baq_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--scorecard-json",
                str(missing_no_baq_scorecard_gate_json),
                "--csv-output",
                str(missing_no_baq_should_not_write_csv),
                "--md-output",
                str(missing_no_baq_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_no_baq_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted a real-money gate without the no-BAQ-as-BEL prerequisite")
        missing_no_baq_text = f"{missing_no_baq_result.stdout}\n{missing_no_baq_result.stderr}"
        if "must include 'no BAQ-as-BEL substitution'" not in missing_no_baq_text:
            raise AssertionError("scorecard JSON failure no longer explains that no-BAQ-as-BEL is required for the real-money gate")
        if missing_no_baq_output_dir.exists() or missing_no_baq_should_not_write_csv.exists() or missing_no_baq_should_not_write_md.exists():
            raise AssertionError("missing no-BAQ-as-BEL prerequisite created output directories or wrote partial method-family artifacts before failing")

        missing_ci_only_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        missing_ci_only_payload.pop("ci_only_promotion_diagnostics", None)
        missing_ci_only_scorecard_json.write_text(json.dumps(missing_ci_only_payload, indent=2) + "\n", encoding="utf-8")
        missing_ci_only_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--scorecard-json",
                str(missing_ci_only_scorecard_json),
                "--csv-output",
                str(missing_ci_only_should_not_write_csv),
                "--md-output",
                str(missing_ci_only_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_ci_only_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted a scorecard JSON missing ci_only_promotion_diagnostics")
        missing_ci_only_text = f"{missing_ci_only_result.stdout}\n{missing_ci_only_result.stderr}"
        if "missing ci_only_promotion_diagnostics" not in missing_ci_only_text:
            raise AssertionError("scorecard JSON failure no longer explains that ci_only_promotion_diagnostics is required for the method-family card")
        if missing_ci_only_output_dir.exists() or missing_ci_only_should_not_write_csv.exists() or missing_ci_only_should_not_write_md.exists():
            raise AssertionError("missing CI-only diagnostic created output directories or wrote partial method-family artifacts before failing")

        missing_compare_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        missing_compare_payload.pop("current_operator_boundary", None)
        missing_compare_json.write_text(json.dumps(missing_compare_payload, indent=2) + "\n", encoding="utf-8")
        missing_compare_json_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--compare-json",
                str(missing_compare_json),
                "--csv-output",
                str(missing_operator_should_not_write_csv),
                "--md-output",
                str(missing_operator_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_compare_json_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted compare_main_approaches.json without current_operator_boundary")
        missing_compare_json_text = f"{missing_compare_json_result.stdout}\n{missing_compare_json_result.stderr}"
        if "missing current_operator_boundary" not in missing_compare_json_text:
            raise AssertionError("compare-main JSON failure no longer explains that current_operator_boundary is required for the method-family card")
        if missing_operator_output_dir.exists() or missing_operator_should_not_write_csv.exists() or missing_operator_should_not_write_md.exists():
            raise AssertionError("missing current-operator boundary failure created output directories or wrote partial method-family artifacts before failing")

        bad_generated_at_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        bad_generated_at_payload["current_operator_boundary"]["generated_at"] = "2026-06-26T18:12:48"
        bad_generated_at_compare_json.write_text(json.dumps(bad_generated_at_payload, indent=2) + "\n", encoding="utf-8")
        bad_generated_at_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--compare-json",
                str(bad_generated_at_compare_json),
                "--csv-output",
                str(bad_generated_at_should_not_write_csv),
                "--md-output",
                str(bad_generated_at_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if bad_generated_at_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted a timezone-naive current_operator_boundary.generated_at")
        bad_generated_at_text = f"{bad_generated_at_result.stdout}\n{bad_generated_at_result.stderr}"
        if "current_operator_boundary generated_at must be timezone-aware ISO provenance metadata" not in bad_generated_at_text:
            raise AssertionError("compare-main JSON failure no longer explains that current_operator_boundary.generated_at must be timezone-aware")
        if bad_generated_at_output_dir.exists() or bad_generated_at_should_not_write_csv.exists() or bad_generated_at_should_not_write_md.exists():
            raise AssertionError("bad current-operator generated_at failure created output directories or wrote partial method-family artifacts before failing")

        missing_freshness_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        missing_freshness_payload["current_operator_boundary"].pop("source_freshness_generated_reference_date", None)
        missing_freshness_reference_compare_json.write_text(json.dumps(missing_freshness_payload, indent=2) + "\n", encoding="utf-8")
        missing_freshness_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--compare-json",
                str(missing_freshness_reference_compare_json),
                "--csv-output",
                str(missing_freshness_should_not_write_csv),
                "--md-output",
                str(missing_freshness_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_freshness_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted compare_main_approaches.json without current_operator_boundary.source_freshness_generated_reference_date")
        missing_freshness_text = f"{missing_freshness_result.stdout}\n{missing_freshness_result.stderr}"
        if "current_operator_boundary is missing fields: source_freshness_generated_reference_date" not in missing_freshness_text:
            raise AssertionError("compare-main JSON failure no longer explains that current_operator_boundary.source_freshness_generated_reference_date is required")
        if missing_freshness_output_dir.exists() or missing_freshness_should_not_write_csv.exists() or missing_freshness_should_not_write_md.exists():
            raise AssertionError("missing current-operator freshness-reference failure created output directories or wrote partial method-family artifacts before failing")

        false_refresh_boundary_flag_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        false_refresh_boundary_flag_payload["current_operator_boundary"]["refresh_boundary_not_real_money_evidence"] = False
        false_refresh_boundary_flag_compare_json.write_text(json.dumps(false_refresh_boundary_flag_payload, indent=2) + "\n", encoding="utf-8")
        false_refresh_boundary_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--compare-json",
                str(false_refresh_boundary_flag_compare_json),
                "--csv-output",
                str(false_refresh_boundary_should_not_write_csv),
                "--md-output",
                str(false_refresh_boundary_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if false_refresh_boundary_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted current_operator_boundary.refresh_boundary_not_real_money_evidence=false")
        false_refresh_boundary_text = f"{false_refresh_boundary_result.stdout}\n{false_refresh_boundary_result.stderr}"
        if "current_operator_boundary must mark refresh_boundary_not_real_money_evidence=true" not in false_refresh_boundary_text:
            raise AssertionError("compare-main JSON failure no longer explains that refresh_boundary_not_real_money_evidence must remain true")
        if (
            false_refresh_boundary_output_dir.exists()
            or false_refresh_boundary_should_not_write_csv.exists()
            or false_refresh_boundary_should_not_write_md.exists()
        ):
            raise AssertionError("false refresh-boundary flag failure created output directories or wrote partial method-family artifacts before failing")

        false_refresh_accounting_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        false_refresh_accounting_payload["current_operator_boundary"][
            "refresh_counts_as_roi_complete_evidence_by_itself"
        ] = True
        false_refresh_accounting_flag_compare_json.write_text(
            json.dumps(false_refresh_accounting_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        false_refresh_accounting_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--compare-json",
                str(false_refresh_accounting_flag_compare_json),
                "--csv-output",
                str(false_refresh_accounting_should_not_write_csv),
                "--md-output",
                str(false_refresh_accounting_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if false_refresh_accounting_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted current_operator_boundary.refresh_counts_as_roi_complete_evidence_by_itself=true")
        false_refresh_accounting_text = f"{false_refresh_accounting_result.stdout}\n{false_refresh_accounting_result.stderr}"
        if "current_operator_boundary must preserve refresh_counts_as_roi_complete_evidence_by_itself=false" not in false_refresh_accounting_text:
            raise AssertionError("compare-main JSON failure no longer explains that wrapper refresh cannot count as ROI-complete evidence")
        if (
            false_refresh_accounting_output_dir.exists()
            or false_refresh_accounting_should_not_write_csv.exists()
            or false_refresh_accounting_should_not_write_md.exists()
        ):
            raise AssertionError("false refresh-accounting flag failure created output directories or wrote partial method-family artifacts before failing")

        missing_gate_payload = json.loads((tmpdir / COMPARE_JSON.name).read_text(encoding="utf-8"))
        missing_gate_payload.pop("decision_change_gate_minimums", None)
        missing_decision_gates_compare_json.write_text(json.dumps(missing_gate_payload, indent=2) + "\n", encoding="utf-8")
        missing_gate_result = subprocess.run(
            [
                sys.executable,
                METHOD_SCRIPT.name,
                "--compare-json",
                str(missing_decision_gates_compare_json),
                "--csv-output",
                str(missing_gate_should_not_write_csv),
                "--md-output",
                str(missing_gate_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_gate_result.returncode == 0:
            raise AssertionError("method_family_decision_card.py unexpectedly accepted compare_main_approaches.json without decision_change_gate_minimums")
        missing_gate_text = f"{missing_gate_result.stdout}\n{missing_gate_result.stderr}"
        if "missing decision_change_gate_minimums" not in missing_gate_text:
            raise AssertionError("compare-main JSON failure no longer explains that decision_change_gate_minimums is required for the method-family card")
        if missing_gate_output_dir.exists() or missing_gate_should_not_write_csv.exists() or missing_gate_should_not_write_md.exists():
            raise AssertionError("missing decision-gate failure created output directories or wrote partial method-family artifacts before failing")

    checks.append(
        require(
            True,
            "cli_csv_matches_saved",
            "method_family_decision_card.py CLI still writes a CSV that matches the saved method-family table",
        )
    )
    checks.append(
        require(
            True,
            "cli_markdown_matches_rebuild",
            "method_family_decision_card.py CLI still writes METHOD_FAMILY_DECISION.md exactly as a fresh rebuild renders it",
        )
    )
    checks.append(
        require(
            True,
            "cli_stdout_matches_generated_report",
            "method_family_decision_card.py CLI stdout still matches the generated report plus its Saved: lines",
        )
    )
    checks.append(
        require(
            tmp_parent.is_relative_to(BASE) and tmp_parent.exists(),
            "cli_scratch_root_project_local",
            "method_family_decision_card.py CLI fixture now writes temporary rebuild, custom-source, custom-hierarchy, and negative-test files under the project-local status-validation scratch root, and that scratch root is cleared before each fixture run",
        )
    )
    checks.append(
        require(
            scratch["tmp_parent_is_project_local"] is True
            and scratch["tmp_parent_cleared_before_fixture_run"] is True
            and Path(scratch["tmp_parent"]) == tmp_parent,
            "cli_scratch_metadata_published",
            "method-family decision-card validation publishes top-level project-local scratch metadata so parent rollups can verify the cleared fixture root without parsing prose",
        )
    )
    checks.append(
        require(
            True,
            "cli_custom_source_and_output_paths",
            "method_family_decision_card.py can now rerender from explicit compare-main / cross-family / backtest / AB input paths and write to custom output paths without depending on the default saved compare or method-family artifact names",
        )
    )
    checks.append(
        require(
            True,
            "custom_cross_family_hierarchy_renders_dynamically",
            "method_family_decision_card.py now proves a custom cross-family LIVE_DEFAULT / PRIMARY_SHADOW / SECONDARY_SHADOW hierarchy reaches the saved CSV, top comparison table, paper-basket companion read, follow-up routes, and real CLI stdout instead of leaving hardcoded OP_DURABLE_K7 wording behind",
        )
    )
    checks.append(
        require(
            True,
            "missing_compare_method_fails_fast",
            "the real method-family CLI now fails fast if compare_main_approaches.csv loses train_only_selector instead of quietly weakening the honest benchmark lane",
        )
    )
    checks.append(
        require(
            True,
            "missing_primary_shadow_fails_fast",
            "the real method-family CLI now fails fast if cross_family_decision_card.csv loses PRIMARY_SHADOW instead of quietly flattening the selective-family shadow hierarchy",
        )
    )
    checks.append(
        require(
            True,
            "missing_harville_backtest_line_fails_fast",
            "the real method-family CLI now fails fast if backtest_summary.csv loses Harville-Top120 instead of quietly softening the benchmark-only case against Harville",
        )
    )
    checks.append(
        require(
            True,
            "missing_ab_delta_path_fails_fast",
            "the real method-family CLI now fails fast if the downstream A/B JSON loses its required delta path instead of quietly weakening the XGBoost caution block",
        )
    )
    checks.append(
        require(
            True,
            "missing_scorecard_ranking_contract_fails_fast",
            "the real method-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if the scorecard JSON loses ranking_contract instead of silently dropping tier-first ranking semantics",
        )
    )
    checks.append(
        require(
            True,
            "malformed_scorecard_decision_gate_minimums_fails_fast",
            "the real method-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if the scorecard JSON loses decision_gate_minimums, contains a boolean anchor floor, gives Phase 8 or real-money review a non-positive floor, or drops the no-BAQ-as-BEL real-money prerequisite instead of silently weakening paper-observation or real-money-discussion gates",
        )
    )
    checks.append(
        require(
            True,
            "missing_scorecard_audit_route_fails_fast",
            "the real method-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if current_evidence_summary.json loses scorecard_audit_route instead of silently dropping copied gate/ranking/CI-only/timezone/no-BAQ synchronization routing",
        )
    )
    checks.append(
        require(
            True,
            "missing_rebuild_validation_contract_fails_fast",
            "the real method-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if current_evidence_summary.json loses rebuild_validation_contract or weakens its provenance-only flag instead of silently dropping or overstating the settlement-audit -> current-bridge -> bridge-validator route before quoting current totals",
        )
    )
    checks.append(
        require(
            True,
            "missing_scorecard_ci_only_diagnostic_fails_fast",
            "the real method-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if the scorecard JSON loses the OP_REFINED CI-only diagnostic instead of locally reconstructing promotion-boundary prose",
        )
    )
    checks.append(
        require(
            True,
            "missing_operator_boundary_fails_fast",
            "the real method-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if compare_main_approaches.json loses current_operator_boundary instead of silently dropping the current paper-workflow boundary",
        )
    )
    checks.append(
        require(
            True,
            "bad_current_operator_generated_at_fails_fast",
            "the real method-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if compare_main_approaches.json carries a timezone-naive current_operator_boundary.generated_at instead of republishing malformed current-paper provenance",
        )
    )
    checks.append(
        require(
            True,
            "missing_current_operator_freshness_reference_fails_fast",
            "the real method-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if compare_main_approaches.json loses current_operator_boundary.source_freshness_generated_reference_date instead of publishing a detached current-paper freshness read",
        )
    )
    checks.append(
        require(
            True,
            "false_current_operator_refresh_not_real_money_flag_fails_fast",
            "the real method-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if compare_main_approaches.json marks current_operator_boundary.refresh_boundary_not_real_money_evidence=false or refresh_counts_as_roi_complete_evidence_by_itself=true instead of republishing weakened current-paper provenance",
        )
    )
    checks.append(
        require(
            True,
            "missing_decision_gate_minimums_fails_fast",
            "the real method-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if compare_main_approaches.json loses decision_change_gate_minimums instead of silently dropping the scorecard-sourced posture gates",
        )
    )

    df = rebuilt_df.set_index("family_id")
    selective_anchor = str(df.loc["selective_rule_path", "current_anchor"])
    selective_primary_shadow = str(df.loc["selective_rule_path", "primary_shadow"])
    selective_secondary_shadow = str(df.loc["selective_rule_path", "secondary_shadow"])
    compare_df = pd.read_csv(COMPARE_CSV).set_index("method_id")
    cross_df = pd.read_csv(CROSS_FAMILY_CSV).set_index("rule_id")
    backtest_rows = load_backtest_rows()
    harville = next(row for row in backtest_rows if row["Strategy"] == "Harville-Top120")
    ml_rows = [row for row in backtest_rows if row["Strategy"].startswith("ML-")]
    best_ml = max(ml_rows, key=lambda row: float(row["ROI%"]))

    ab = json.loads(AB_JSON.read_text(encoding="utf-8"))
    baseline = ab["prediction_accuracy"]["baseline"]
    enriched = ab["prediction_accuracy"]["enriched"]
    ev_base = ab["ev_engine_comparison"]["baseline"]
    ev_enriched = ab["ev_engine_comparison"]["enriched"]
    payout_rmse_reduction_pct = (1.0 - enriched["payout_rmse"] / baseline["payout_rmse"]) * 100.0

    checks.append(
        require(
            scorecard_ranking_contract.get("rank_is_tier_first_decision_order") is True
            and scorecard_ranking_contract.get("forward_trust_is_secondary_within_tier") is True
            and scorecard_ranking_contract.get("raw_score_is_not_an_automatic_deployment_instruction") is True
            and "CD_CORE_K8 ranks ahead of OP_REFINED_K7" in str(scorecard_ranking_contract.get("known_rank_override") or "")
            and "Inherited scorecard ranking contract:" in saved_md
            and "Scorecard rank-contract override: CD_CORE_K8 ranks ahead of OP_REFINED_K7" in saved_md
            and "raw Score cannot turn the selective-family OP_REFINED shadow context into an automatic promotion cue" in saved_md
            and f"`valid_evidence_scope={mfd.VALID_EVIDENCE_SCOPE}`" in saved_md
            and "`forward_evidence_scorecard.json`" in saved_md,
            "scorecard_ranking_contract_inherited",
            "METHOD_FAMILY_DECISION.md now consumes forward_evidence_scorecard.json ranking_contract and exposes a raw valid_evidence_scope line so the selective-vs-Harville-vs-XGBoost page inherits tier-first score semantics and cannot treat OP_REFINED shadow context as an automatic promotion cue or fresh paper evidence",
        )
    )
    checks.append(
        require(
            scorecard_ci_only_diagnostic["candidate_rule_id"] == "OP_REFINED_K7"
            and scorecard_ci_only_diagnostic["ci_only_promotion_allowed"] is False
            and "Scorecard CI-only promotion check: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` says `ci_only_promotion_allowed=false`; the positive OP_REFINED CI lower bound is support context only, not a method-family promotion trigger." in saved_md
            and "## Scorecard CI-Only Promotion Check" in saved_md
            and "Source: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7`" in saved_md
            and "- Current decision: Keep OP_REFINED_K7 shadow/watch only." in saved_md
            and "- CI-only promotion allowed: `false`" in saved_md
            and "Why not: smaller holdout sample than OP_DURABLE_K7, losing 2024 holdout split, lower walk-forward recurrence than OP_DURABLE_K7, uncleared phase8_promotion_review paper-observation gate, uncleared anchor_displacement paper-observation gate." in saved_md
            and "Does not count: positive bootstrap CI lower bound by itself, hotter aggregate small-sample holdout ROI, historical replay rows, clean rebuilds, green validators." in saved_md
            and "positive CI support can justify continued observation, but it cannot by itself promote `OP_REFINED_K7`, displace `OP_DURABLE_K7`, or change the method-family ordering." in saved_md,
            "scorecard_ci_only_diagnostic_inherited",
            "METHOD_FAMILY_DECISION.md now source-matches the scorecard OP_REFINED CI-only diagnostic so positive CI support cannot read as method-family promotion readiness",
        )
    )
    checks.append(
        require(
            "## Source Provenance" in saved_md
            and "Exact input-byte fingerprints for this method-family card." in saved_md
            and "they do not prove settled paper ROI, promotion readiness, live profitability, or real-money performance." in saved_md
            and source_provenance_matches_disk(saved_md),
            "source_provenance_markdown_matches_disk",
            "METHOD_FAMILY_DECISION.md now fingerprints compare-main CSV/JSON, cross-family, scorecard, backtest, and downstream A/B inputs, with markdown byte counts and SHA-256 values matching current disk files",
        )
    )
    checks.append(
        require(
            "## Current Operator Boundary" in saved_md
            and f"This context is inherited from `{COMPARE_JSON.name}` / `{operator_boundary['source_path']}`" in saved_md
            and f"`{operator_boundary['right_now_freshness_state']}`; refresh before right-now use = `{operator_boundary['requires_refresh_before_right_now_use']}`" in saved_md
            and f"bridge reference = `{operator_boundary['source_freshness_generated_reference_date']}` (`{operator_boundary['source_freshness_generated_reference_timezone']}`)" in saved_md
            and f"comparison = `{operator_boundary['source_freshness_staleness_comparison_source']}` / `{operator_boundary['source_freshness_staleness_comparison_date']}`" in saved_md
            and mfd.md_cell(operator_boundary["source_freshness_read"]) in saved_md
            and f"`{operator_boundary['refresh_action_command']}` required before right-now use = `{operator_boundary['refresh_required_before_right_now_instruction_use']}`" in saved_md
            and f"can update surfaces = `{operator_boundary['refresh_can_update_operator_surfaces']}`" in saved_md
            and f"settles rows / creates ROI evidence / clean-empty performance = `{operator_boundary['refresh_can_settle_open_rows_by_itself']}` / `{operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}` / `{operator_boundary['clean_empty_refresh_counts_as_forward_performance']}`" in saved_md
            and "| Operator read gate |" in saved_md
            and f"`{COMPARE_JSON.name}` `current_operator_boundary.operator_read_gate`" in saved_md
            and mfd.md_cell(operator_read_gate["read"]) in saved_md
            and operator_read_gate_branch_ok
            and operator_read_gate["current_top_card_counts_as_no_target_evidence"] is False
            and operator_read_gate["current_top_card_counts_as_clean_empty_evidence"] is False
            and operator_read_gate["current_top_card_counts_as_bet_readiness_evidence"] is False
            and operator_read_gate["current_top_card_counts_as_settled_roi_evidence"] is False
            and operator_boundary["refresh_boundary_not_forward_performance_evidence"] is True
            and operator_boundary["refresh_boundary_not_promotion_readiness_evidence"] is True
            and operator_boundary["refresh_boundary_not_live_profitability_evidence"] is True
            and operator_boundary["refresh_boundary_not_real_money_evidence"] is True
            and "| Primary first-read gate |" not in saved_md
            and "| Bridge-published gate progress |" in saved_md
            and f"`{CURRENT_EVIDENCE_JSON.name}` `decision_gate_progress`" in saved_md
            and mfd.md_cell(current_gate_progress["read"]) in saved_md
            and current_gate_progress.get("gate_status") == "all_uncleared"
            and current_gate_progress.get("all_gates_ready") is False
            and current_gate_progress.get("not_forward_performance_evidence") is True
            and current_gate_progress.get("not_promotion_readiness_evidence") is True
            and current_gate_progress.get("not_live_profitability_evidence") is True
            and current_gate_progress.get("not_real_money_evidence") is True
            and f"| Current settled rule mix | OP_DURABLE_K7={operator_boundary['op_anchor_roi_complete_rows']}; CD_CORE_K8={operator_boundary['cd_companion_roi_complete_rows']};" in saved_md
            and mfd.md_cell(operator_boundary["primary_rule_mix_read"]) in saved_md
            and operator_boundary["current_settled_context_is_cd_only"] is True
            and (
                f"| Settlement queue state | `{operator_boundary['open_settlement_queue_state']}`; "
                f"{mfd.md_cell(operator_boundary['open_settlement_context'])}; detail: "
                f"{mfd.md_cell(operator_boundary['open_settlement_queue_read'])} |"
            ) in saved_md
            and "| Open settlement context |" not in saved_md
            and "Settlement queue state:" not in str(operator_boundary.get("open_settlement_queue_read") or "")
            and mfd.md_cell(operator_boundary["recommendation_context_read"]) in saved_md
            and "Latest recommendation-state context is operator routing only" in saved_md
            and f"`{operator_boundary['best_action_command']}`" in saved_md
            and "The current operator boundary is routing/provenance context only." in saved_md
            and "it is not settled ROI, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence." in saved_md,
            "current_operator_boundary_documented",
            "METHOD_FAMILY_DECISION.md now carries the compare-main current-operator boundary plus current_evidence_summary.json decision_gate_progress, including structured freshness provenance, stale-card refresh routing, wrapper-refresh non-evidence flags, the inherited operator_read_gate, bridge-published current gate split, CD-only current settled rule mix, source-published settlement-queue state/context/detail, recommendation-state context, and non-performance/no-real-money caveat",
        )
    )
    checks.append(
        require(
            operator_read_gate_branch_ok
            and operator_read_gate.get("not_forward_performance_evidence") is True
            and operator_read_gate.get("not_promotion_readiness_evidence") is True
            and operator_read_gate.get("not_live_profitability_evidence") is True
            and operator_read_gate.get("not_real_money_evidence") is True
            and operator_gate_status in {"refresh_required_before_evidence_read", "current_operator_routing_context_only"},
            "current_operator_read_gate_documented",
            "METHOD_FAMILY_DECISION.md now republishes compare_main_approaches.json current_operator_boundary.operator_read_gate as branch-aware routing metadata, not no-target, clean-empty, method-family proof, bet-readiness, settled ROI, promotion, live-profitability, bankroll, or real-money evidence",
        )
    )
    checks.append(
        require(
            mfd.has_timezone_aware_timestamp(operator_boundary.get("generated_at")),
            "current_operator_boundary_generated_at_is_timezone_aware",
            f"method-family card inherits compare-main current_operator_boundary.generated_at={operator_boundary.get('generated_at')!r} as parseable timezone-aware provenance metadata only",
        )
    )
    checks.append(
        require(
            rebuild_validation_contract["upstream_refresh_commands"] == mfd.REQUIRED_REBUILD_REFRESH_ORDER
            and rebuild_validation_contract["prerequisite_rebuild_command"] == "python3 paper_trade_settlement_audit.py"
            and rebuild_validation_contract["rebuild_command"] == "python3 current_evidence_summary.py"
            and rebuild_validation_contract["direct_validation_command"] == "python3 validate_current_evidence_summary.py"
            and rebuild_validation_contract["requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"] is True
            and rebuild_validation_contract["requires_source_consistency_before_quoting_current_totals"] is True
            and rebuild_validation_contract["requires_source_freshness_before_right_now_instruction_use"] is True
            and rebuild_validation_contract["upstream_refresh_order_is_provenance_metadata_only"] is True
            and rebuild_validation_contract["not_settled_roi_or_real_money_evidence"] is True
            and "**Current bridge rebuild order:**" in saved_md
            and f"`{CURRENT_EVIDENCE_JSON.name}` `rebuild_validation_contract`" in saved_md
            and "`python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*`" in saved_md,
            "current_evidence_rebuild_validation_contract_documented",
            "METHOD_FAMILY_DECISION.md now republishes current_evidence_summary.json.rebuild_validation_contract so source-byte changes route through settlement-audit -> current-bridge -> bridge-validator before anyone quotes current totals from the method-family card",
        )
    )
    checks.append(
        require(
            "## Decision Gate Source" in saved_md
            and f"These gate minimums are loaded directly from `{SCORECARD_JSON.name}` `decision_gate_minimums`; `{COMPARE_JSON.name}` also carries matching copied gate values in `decision_change_gate_minimums`." in saved_md
            and scorecard_decision_gates["phase8_promotion_review"]["minimum_roi_complete_settled_observations"] == 20
            and scorecard_decision_gates["anchor_displacement"]["minimum_roi_complete_same_candidate_observations"] == 30
            and scorecard_decision_gates["real_money_discussion"]["minimum_total_settled_roi_complete_observations"] == 100
            and scorecard_decision_gates["phase8_promotion_review"]["threshold_source"] == "forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations"
            and scorecard_decision_gates["anchor_displacement"]["threshold_source"] == "forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations"
            and scorecard_decision_gates["real_money_discussion"]["threshold_source"] == "forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi"
            and decision_gates["phase8_promotion_review"]["minimum_roi_complete_settled_observations"] == 20
            and decision_gates["anchor_displacement"]["minimum_roi_complete_same_candidate_observations"] == 30
            and decision_gates["real_money_discussion"]["minimum_total_settled_roi_complete_observations"] == 100
            and decision_gates["phase8_promotion_review"]["threshold_source"] == "forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations"
            and decision_gates["anchor_displacement"]["threshold_source"] == "forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations"
            and decision_gates["real_money_discussion"]["threshold_source"] == "forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi"
            and "| phase8_promotion_review | 20 ROI-complete settled shadow observations |" in saved_md
            and "| anchor_displacement | 30 ROI-complete same-candidate paper observations |" in saved_md
            and "| real_money_discussion | 100 total settled observations with usable ROI |" in saved_md
            and "The 20-row Phase 8 promotion-review gate is not an anchor-displacement gate, and the 100-row real-money discussion floor is not bankroll guidance." in saved_md,
            "decision_gate_minimums_documented",
            "METHOD_FAMILY_DECISION.md now loads scorecard decision_gate_minimums directly, cross-checks compare-main's copied gate values, and preserves the 20 Phase 8 review / 30 anchor-displacement / 100 real-money-discussion thresholds with exact threshold-source keys",
        )
    )
    checks.append(
        require(
            scorecard_audit_route.get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route.get("json_path") == "scorecard_ranking_contract_audit.json"
            and scorecard_audit_route.get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route.get("gate_floor_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and scorecard_audit_route.get("artifacts_present") is True
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get("real_money_no_baq_as_bel_required") is True
            and scorecard_audit_route.get("not_forward_performance_evidence") is True
            and scorecard_audit_route.get("not_settled_roi_evidence") is True
            and scorecard_audit_route.get("not_promotion_readiness_evidence") is True
            and scorecard_audit_route.get("not_live_profitability_evidence") is True
            and scorecard_audit_route.get("not_bankroll_guidance") is True
            and scorecard_audit_route.get("not_real_money_evidence") is True
            and "**Scorecard audit route:** `current_evidence_summary.json` `scorecard_audit_route` points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py`" in saved_md
            and "| Scorecard audit route | `current_evidence_summary.json` `scorecard_audit_route`:" in saved_md
            and "Route metadata checks copied gate/ranking/CI-only/timezone/no-BAQ synchronization only; it is not method-family evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in saved_md,
            "scorecard_audit_route_documented",
            "METHOD_FAMILY_DECISION.md now republishes current_evidence_summary.json.scorecard_audit_route so copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks route to the dedicated scorecard audit as metadata only, not method-family evidence or performance proof",
        )
    )
    checks.append(
        require(
            df.loc["selective_rule_path", "role"] == "PAPER NOW"
            and df.loc["harville_ranked", "role"] == "BENCHMARK ONLY"
            and df.loc["xgboost_residual", "role"] == "RESEARCH ONLY",
            "method_family_roles",
            "method-family card still orders selective rules first, Harville second, XGBoost third",
        )
    )
    checks.append(
        require(
            "current_anchor" in saved_df.columns and "primary_shadow" in saved_df.columns and "secondary_shadow" in saved_df.columns,
            "csv_shadow_columns_present",
            "method_family_decision_card.csv now carries the current anchor plus primary/secondary shadow rule identifiers for the selective family",
        )
    )
    checks.append(
        require(
            abs(float(df.loc["selective_rule_path", "primary_metric"]) - float(compare_df.loc["phase7_live_portfolio", "holdout_roi"])) < 1e-9
            and int(df.loc["selective_rule_path", "primary_sample"]) == int(compare_df.loc["phase7_live_portfolio", "holdout_races"])
            and abs(float(df.loc["selective_rule_path", "holdout_2024_metric"]) - float(compare_df.loc["phase7_live_portfolio", "holdout_2024_roi"])) < 1e-9
            and int(df.loc["selective_rule_path", "holdout_2024_sample"]) == int(compare_df.loc["phase7_live_portfolio", "holdout_2024_races"])
            and abs(float(df.loc["selective_rule_path", "holdout_2025_metric"]) - float(compare_df.loc["phase7_live_portfolio", "holdout_2025_roi"])) < 1e-9
            and int(df.loc["selective_rule_path", "holdout_2025_sample"]) == int(compare_df.loc["phase7_live_portfolio", "holdout_2025_races"])
            and abs(float(df.loc["selective_rule_path", "secondary_metric"]) - float(compare_df.loc["train_only_selector", "wf_roi"])) < 1e-9
            and int(df.loc["selective_rule_path", "secondary_sample"]) == int(compare_df.loc["train_only_selector", "wf_races"])
            and str(df.loc["selective_rule_path", "current_anchor"]) == str(cross_df[cross_df["shadow_rank"] == "LIVE_DEFAULT"].index[0])
            and str(df.loc["selective_rule_path", "primary_shadow"]) == str(cross_df[cross_df["shadow_rank"] == "PRIMARY_SHADOW"].index[0])
            and str(df.loc["selective_rule_path", "secondary_shadow"]) == str(cross_df[cross_df["shadow_rank"] == "SECONDARY_SHADOW"].index[0]),
            "selective_matches_compare_main",
            "selective-rule row still matches the Phase 7 portfolio holdout, holdout year split, the honest train-only selector walk-forward benchmark, and the current anchor/shadow shortlist",
        )
    )
    checks.append(
        require(
            abs(float(df.loc["harville_ranked", "primary_metric"]) - float(harville["ROI%"])) < 1e-9
            and int(df.loc["harville_ranked", "primary_sample"]) == int(float(harville["Races"]))
            and abs(float(df.loc["harville_ranked", "secondary_metric"]) - float(harville["HitRate%"])) < 1e-9,
            "harville_matches_backtest",
            "Harville row still matches the broad Harville-Top120 benchmark line in backtest_summary.csv",
        )
    )
    checks.append(
        require(
            str(df.loc["xgboost_residual", "primary_metric_label"]) == f"best ML betting ROI ({best_ml['Strategy']})"
            and abs(float(df.loc["xgboost_residual", "primary_metric"]) - float(best_ml["ROI%"])) < 1e-9
            and int(df.loc["xgboost_residual", "primary_sample"]) == int(float(best_ml["Races"])),
            "xgboost_best_ml_line",
            "XGBoost row still points at the least-bad ML betting line, which remains negative on a large sample",
        )
    )
    checks.append(
        require(
            abs(float(df.loc["xgboost_residual", "secondary_metric"]) - float(payout_rmse_reduction_pct)) < 1e-9
            and int(df.loc["xgboost_residual", "secondary_sample"]) == int(ab["test_set"]["n_races"]),
            "xgboost_ab_metric",
            "XGBoost row still uses the matched downstream payout-RMSE improvement as its secondary evidence",
        )
    )
    checks.append(
        require(
            float(df.loc["selective_rule_path", "primary_metric"]) > 0
            and float(df.loc["harville_ranked", "primary_metric"]) < 0
            and float(df.loc["xgboost_residual", "primary_metric"]) < 0,
            "only_selective_is_paper_positive",
            "selective rules remain the only method family here with positive current paper-facing evidence",
        )
    )
    selective_table_primary = (
        "| Selective rule path | PAPER NOW | +38.68% (2024-2025 holdout ROI; 2024 +0.37% on 109, 2025 +105.38% on 66) | 175 | +22.46% (train-only selector walk-forward ROI) |"
    )
    selective_table_why = f"with {selective_anchor} still the safest anchor, but the recent path was uneven rather than a smooth two-year glide."
    checks.append(
        require(
            "For the selective family, the primary evidence includes the 2024/2025 holdout split because the aggregate holdout number alone is too smooth. Its secondary evidence is the honest train-only selector walk-forward benchmark, not a replay of the frozen Phase 7 basket." in saved_md
            and "For XGBoost, the secondary column is model-fit context from the matched downstream A/B, not a betting-evidence line." in saved_md
            and "This card is split-aware, not family-CI-backed at the top level" in saved_md
            and "Inherited scorecard ranking contract:" in saved_md
            and "the frozen sources do not publish a selective-family bootstrap CI lower bound" in saved_md
            and "At the method-family layer, this card does not have a published family-level bootstrap CI field. The caution surface here is the selective family holdout split, the honest train-only walk-forward benchmark, and the rule-level anchor/shadow evidence beneath it rather than a top-level family CI claim." in saved_md
            and selective_table_primary in saved_md
            and selective_table_why in saved_md
            and "Holdout split: 2024 +0.37% on 109 races; 2025 +105.38% on 66 races. That is positive in both years, but most of the aggregate holdout edge came in 2025, so the family still needs paper-trade confirmation instead of victory-lap language." in saved_md
            and "Its frozen holdout split is still worth saying plainly: 2024 +0.37% on 109 races versus 2025 +105.38% on 66 races. That is better than Harville/XGBoost, but it is not a smooth straight-line edge." in saved_md
            and "It should also stay read as a split-aware operating hierarchy, not as a formal family-level CI proof surface." in saved_md
            and "This card is intentionally pinned to the frozen 2024-2025 holdout standard carried by the compare-main, cross-family, and forward-scorecard JSON artifacts, so a prettier number from some other window or method slice does not quietly rewrite the current paper method hierarchy." in saved_md,
            "selective_holdout_split_documented",
            "method-family card now makes the selective family split-aware in the top comparison table as well as the explanatory sections below, says the family layer is not backed by a published family-level CI, labels the XGBoost secondary column as non-betting evidence, and states the frozen 2024-2025 holdout lock explicitly",
        )
    )
    checks.append(
        require(
            f"Current paper-basket companion read: `{selective_anchor}` stays the safest anchor, `{selective_primary_shadow}` is the primary OP/CD paper-basket companion, and `{selective_secondary_shadow}` remains the stronger same-family OP shadow challenger rather than a promoted default." in saved_md,
            "selective_shadow_read_documented",
            "method-family card now states the current-paper selective-family anchor / paper-companion / shadow-challenger ordering directly instead of leaving it implicit",
        )
    )
    checks.append(
        require(
            float(df.loc["harville_ranked", "primary_sample"]) > float(df.loc["selective_rule_path", "primary_sample"])
            and float(df.loc["harville_ranked", "primary_metric"]) < 0,
            "harville_negative_on_huge_sample",
            "Harville still stays BENCHMARK ONLY because it loses badly even on a much larger sample",
        )
    )
    checks.append(
        require(
            float(df.loc["xgboost_residual", "primary_metric"]) < 0
            and float(df.loc["xgboost_residual", "secondary_metric"]) > 0
            and int(ev_enriched["ev_pass_count"]) <= int(ev_base["ev_pass_count"])
            and int(ab["ev_engine_comparison"]["delta"]["ev_pass_count_delta"]) == -7
            and "drifted down by 7" in saved_md
            and "-3.93% relative; -0.0315 percentage points of 22244 test winners" in saved_md
            and "from 178 baseline to 171 enriched" in saved_md
            and "Read the payout-RMSE gain as model-fit context only; it does not become deployment-worthy unless the downstream betting behavior improves too." in saved_md
            and "For XGBoost specifically, the payout-RMSE improvement is still just model-fit context from the matched downstream test, not a separate betting-proof column." in saved_md,
            "xgboost_prediction_gain_not_betting_gain",
            "XGBoost still improves prediction metrics a bit without improving the downstream EV pass count into a deployment case, now with the normalized drift spelled out in the markdown and the payout-RMSE line labeled as model-fit context rather than betting proof",
        )
    )
    checks.append(
        require(
            "## Narrow Follow-Up Reads" in saved_md,
            "narrow_follow_up_section",
            "method-family card now includes a dedicated narrow follow-up reads section",
        )
    )
    checks.append(
        require(
            f"`CROSS_FAMILY_DECISION.md`: use when the question is how the paper-basket companion and same-family OP shadow challenger line up behind `{selective_anchor}`." in saved_md,
            "cross_family_follow_up_entry",
            "method-family card points paper-companion / shadow-challenger order questions to the dedicated cross-family decision artifact",
        )
    )
    checks.append(
        require(
            f"`OP_ANCHOR_METHOD_COMPARISON.md`: use when the question is specifically why `{selective_anchor}` still outranks Harville while the current odds-only XGBoost path stays parked unless its evidence class changes materially." in saved_md,
            "op_follow_up_entry",
            "method-family card points narrow OP-vs-Harville-vs-parked-odds-only-XGBoost evidence-class questions to the dedicated OP anchor comparison artifact",
        )
    )
    checks.append(
        require(
            "`AB_DOWNSTREAM_COMPARISON.md`: use when the question is specifically whether the enriched horse-history XGBoost downstream correction is strong enough to change the paper-betting answer. It is not." in saved_md,
            "ab_follow_up_entry",
            "method-family card points narrow enriched-horse-history XGBoost downstream questions to the dedicated A/B artifact",
        )
    )
    checks.append(
        require(
            "`compare_recommender_scope_paths.md`: use when the question is specifically whether widened `--allow-all-combos` scope should change the current paper default. It should not." in saved_md,
            "scope_follow_up_entry",
            "method-family card points narrow widened-scope questions to the dedicated scope guardrail artifact",
        )
    )

    suite_read = (
        f"method-family card stays pinned to the frozen 2024-2025 holdout standard with valid_evidence_scope={mfd.VALID_EVIDENCE_SCOPE}; "
        f"Paper now=selective_rule_path ({float(df.loc['selective_rule_path', 'primary_metric']):+.2f}% holdout on {int(df.loc['selective_rule_path', 'primary_sample'])} races; "
        f"2024={float(df.loc['selective_rule_path', 'holdout_2024_metric']):+.2f}% on {int(df.loc['selective_rule_path', 'holdout_2024_sample'])}, "
        f"2025={float(df.loc['selective_rule_path', 'holdout_2025_metric']):+.2f}% on {int(df.loc['selective_rule_path', 'holdout_2025_sample'])}; "
        f"train-only selector benchmark={float(df.loc['selective_rule_path', 'secondary_metric']):+.2f}% on {int(df.loc['selective_rule_path', 'secondary_sample'])}; no published family CI low in frozen sources; "
        f"inside that family, anchor={df.loc['selective_rule_path', 'current_anchor']}, paper companion={df.loc['selective_rule_path', 'primary_shadow']}, closest shadow={df.loc['selective_rule_path', 'secondary_shadow']}); "
        f"scorecard ranking contract inherited=tier-first, raw Score non-promotional ({scorecard_ranking_contract['known_rank_override']}); "
        f"benchmark only=harville_ranked ({float(df.loc['harville_ranked', 'primary_metric']):+.2f}% broad ROI on {int(df.loc['harville_ranked', 'primary_sample'])} races); "
        f"research only=xgboost_residual ({float(df.loc['xgboost_residual', 'primary_metric']):+.2f}% best ML betting ROI despite {float(payout_rmse_reduction_pct):+.2f}% payout-RMSE improvement as model-fit context, not a betting-evidence line, and a -7 pass / -3.93% / -0.0315pp downstream drift); "
        f"current operator boundary inherited from compare-main JSON names stale-card refresh route={operator_boundary['refresh_action_command']}, wrapper-can-settle-rows={operator_boundary['refresh_can_settle_open_rows_by_itself']}, wrapper-counts-as-ROI-evidence={operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}, clean-empty-forward-performance={operator_boundary['clean_empty_refresh_counts_as_forward_performance']}, {operator_boundary['roi_complete_primary_rows']}/{operator_boundary['first_read_threshold']} primary ROI-complete rows, current settled rule mix OP_DURABLE_K7={operator_boundary['op_anchor_roi_complete_rows']} / CD_CORE_K8={operator_boundary['cd_companion_roi_complete_rows']} with CD-only context={operator_boundary['current_settled_context_is_cd_only']}, settlement-queue state={operator_boundary['open_settlement_queue_state']} / context={operator_boundary['open_settlement_context']}, recommendation-state context={operator_boundary['recommendation_context_read']}, and the operator route as routing/provenance only rather than settled ROI, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence; "
        f"operator read gate inherited from compare-main says {operator_read_gate['read']} with gate_status={operator_read_gate['gate_status']} and recommended_command={operator_read_gate['recommended_command']}; "
        f"bridge-published gate progress from current_evidence_summary.json.decision_gate_progress says {current_gate_progress['read']} with gate_status={current_gate_progress['gate_status']} and all_gates_ready={current_gate_progress['all_gates_ready']}; "
        f"current_evidence_summary.json.rebuild_validation_contract routes source-byte changes through {' -> '.join(rebuild_validation_contract['upstream_refresh_commands'])} before quoting CURRENT_EVIDENCE_SUMMARY.* as provenance/rebuild metadata only, not method-family evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence; "
        f"current_evidence_summary.json.scorecard_audit_route points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to {scorecard_audit_route['markdown_path']} / {scorecard_audit_route['json_path']} plus {scorecard_audit_route['validator_command']} as report-synchronization metadata only, not method-family evidence, forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence; "
        f"copied current-operator generated_at={operator_boundary['generated_at']} stays parseable timezone-aware provenance metadata only; "
        f"structured freshness provenance bridge reference={operator_boundary['source_freshness_generated_reference_date']} ({operator_boundary['source_freshness_generated_reference_timezone']}), comparison={operator_boundary['source_freshness_staleness_comparison_source']} / {operator_boundary['source_freshness_staleness_comparison_date']}, read={operator_boundary['source_freshness_read']} stays operator-readiness metadata only; "
        f"decision gates loaded directly from scorecard JSON decision_gate_minimums keep phase8_promotion_review={scorecard_decision_gates['phase8_promotion_review']['minimum_roi_complete_settled_observations']}, anchor_displacement={scorecard_decision_gates['anchor_displacement']['minimum_roi_complete_same_candidate_observations']}, and real_money_discussion={scorecard_decision_gates['real_money_discussion']['minimum_total_settled_roi_complete_observations']}, with compare-main copied gate values cross-checked; "
        f"scorecard CI-only diagnostic inherited from forward_evidence_scorecard.json:{mfd.OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY} keeps ci_only_promotion_allowed={str(scorecard_ci_only_diagnostic['ci_only_promotion_allowed']).lower()} so positive OP_REFINED CI support stays out of method-family promotion readiness; "
        "saved CSV, saved markdown, and real CLI stdout stay pinned to the same method-family decision render; "
        "project-local CLI scratch-root reporting stays pinned"
    )

    payload = {
        "suite_status": "pass",
        "artifact": {
            "saved_csv": METHOD_CSV.name,
            "saved_markdown": METHOD_MD.name,
            "valid_evidence_scope": mfd.VALID_EVIDENCE_SCOPE,
            "status": "pass",
            "rows": int(len(saved_df)),
        },
        "valid_evidence_scope": mfd.VALID_EVIDENCE_SCOPE,
        "scorecard_ranking_contract": scorecard_ranking_contract,
        "scorecard_ranking_contract_source": SCORECARD_JSON.name,
        "scorecard_decision_gate_minimums": scorecard_decision_gates,
        "scorecard_decision_gate_minimums_source": SCORECARD_JSON.name,
        "scorecard_ci_only_diagnostic": scorecard_ci_only_diagnostic,
        "scorecard_ci_only_diagnostic_source": f"{SCORECARD_JSON.name}:{mfd.OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}",
        "current_evidence_gate_progress_read": current_gate_progress,
        "current_evidence_rebuild_validation_contract_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            "source_path": "rebuild_validation_contract",
            "upstream_refresh_commands": rebuild_validation_contract["upstream_refresh_commands"],
            "prerequisite_rebuild_command": rebuild_validation_contract["prerequisite_rebuild_command"],
            "rebuild_command": rebuild_validation_contract["rebuild_command"],
            "direct_validation_command": rebuild_validation_contract["direct_validation_command"],
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": rebuild_validation_contract[
                "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
            ],
            "requires_source_consistency_before_quoting_current_totals": rebuild_validation_contract[
                "requires_source_consistency_before_quoting_current_totals"
            ],
            "requires_source_freshness_before_right_now_instruction_use": rebuild_validation_contract[
                "requires_source_freshness_before_right_now_instruction_use"
            ],
            "upstream_refresh_order_is_provenance_metadata_only": rebuild_validation_contract[
                "upstream_refresh_order_is_provenance_metadata_only"
            ],
            "not_settled_roi_or_real_money_evidence": rebuild_validation_contract[
                "not_settled_roi_or_real_money_evidence"
            ],
        },
        "current_evidence_scorecard_audit_route_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            "source_path": "scorecard_audit_route",
            "markdown_path": scorecard_audit_route["markdown_path"],
            "json_path": scorecard_audit_route["json_path"],
            "validator_command": scorecard_audit_route["validator_command"],
            "gate_floor_source": scorecard_audit_route["gate_floor_source"],
            "gate_floor_snapshot": scorecard_audit_route["gate_floor_snapshot"],
            "route_read": scorecard_audit_route["route_read"],
            "artifacts_present": scorecard_audit_route["artifacts_present"],
            "not_forward_performance_evidence": scorecard_audit_route["not_forward_performance_evidence"],
            "not_settled_roi_evidence": scorecard_audit_route["not_settled_roi_evidence"],
            "not_promotion_readiness_evidence": scorecard_audit_route["not_promotion_readiness_evidence"],
            "not_live_profitability_evidence": scorecard_audit_route["not_live_profitability_evidence"],
            "not_bankroll_guidance": scorecard_audit_route["not_bankroll_guidance"],
            "not_real_money_evidence": scorecard_audit_route["not_real_money_evidence"],
        },
        "current_operator_read_gate": operator_read_gate,
        "scratch": scratch,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "summary": {
            "paper_now": "selective_rule_path",
            "benchmark_only": "harville_ranked",
            "research_only": "xgboost_residual",
            "best_ml_strategy": best_ml["Strategy"],
            "best_ml_roi": float(best_ml["ROI%"]),
            "payout_rmse_reduction_pct": float(payout_rmse_reduction_pct),
            "current_operator_boundary": {
                "source_path": operator_boundary["source_path"],
                "generated_at": operator_boundary["generated_at"],
                "source_freshness_generated_reference_date": operator_boundary["source_freshness_generated_reference_date"],
                "source_freshness_generated_reference_timezone": operator_boundary["source_freshness_generated_reference_timezone"],
                "source_freshness_staleness_comparison_source": operator_boundary["source_freshness_staleness_comparison_source"],
                "source_freshness_staleness_comparison_date": operator_boundary["source_freshness_staleness_comparison_date"],
                "source_freshness_read": operator_boundary["source_freshness_read"],
                "right_now_freshness_state": operator_boundary["right_now_freshness_state"],
                "requires_refresh_before_right_now_use": operator_boundary["requires_refresh_before_right_now_use"],
                "refresh_action_command": operator_boundary["refresh_action_command"],
                "refresh_required_before_right_now_instruction_use": operator_boundary["refresh_required_before_right_now_instruction_use"],
                "refresh_can_update_operator_surfaces": operator_boundary["refresh_can_update_operator_surfaces"],
                "refresh_can_settle_open_rows_by_itself": operator_boundary["refresh_can_settle_open_rows_by_itself"],
                "refresh_counts_as_roi_complete_evidence_by_itself": operator_boundary["refresh_counts_as_roi_complete_evidence_by_itself"],
                "clean_empty_refresh_counts_as_forward_performance": operator_boundary["clean_empty_refresh_counts_as_forward_performance"],
                "refresh_boundary_not_forward_performance_evidence": operator_boundary["refresh_boundary_not_forward_performance_evidence"],
                "refresh_boundary_not_promotion_readiness_evidence": operator_boundary["refresh_boundary_not_promotion_readiness_evidence"],
                "refresh_boundary_not_live_profitability_evidence": operator_boundary["refresh_boundary_not_live_profitability_evidence"],
                "refresh_boundary_not_real_money_evidence": operator_boundary["refresh_boundary_not_real_money_evidence"],
                "open_settlement_summary": operator_boundary["open_settlement_summary"],
                "open_settlement_context": operator_boundary["open_settlement_context"],
                "open_settlement_queue_state": operator_boundary["open_settlement_queue_state"],
                "open_settlement_queue_read": operator_boundary["open_settlement_queue_read"],
                "roi_complete_primary_rows": operator_boundary["roi_complete_primary_rows"],
                "first_read_threshold": operator_boundary["first_read_threshold"],
                "first_read_remaining": operator_boundary["first_read_remaining"],
                "op_anchor_roi_complete_rows": operator_boundary["op_anchor_roi_complete_rows"],
                "cd_companion_roi_complete_rows": operator_boundary["cd_companion_roi_complete_rows"],
                "current_settled_context_is_cd_only": operator_boundary["current_settled_context_is_cd_only"],
                "primary_rule_mix_read": operator_boundary["primary_rule_mix_read"],
                "latest_context_has_no_bet_recommendations": operator_boundary["latest_context_has_no_bet_recommendations"],
                "latest_context_has_bet_ready_language": operator_boundary["latest_context_has_bet_ready_language"],
                "latest_context_has_no_qualifying_races": operator_boundary["latest_context_has_no_qualifying_races"],
                "latest_run_context": operator_boundary["latest_run_context"],
                "recommendation_context_read": operator_boundary["recommendation_context_read"],
                "best_action_command": operator_boundary["best_action_command"],
                "not_forward_performance_evidence": operator_boundary["not_forward_performance_evidence"],
                "not_bet_readiness_evidence_by_itself": operator_boundary["not_bet_readiness_evidence_by_itself"],
            },
            "current_evidence_gate_progress_read": current_gate_progress,
            "current_evidence_rebuild_validation_contract_read": {
                "source": CURRENT_EVIDENCE_JSON.name,
                "source_path": "rebuild_validation_contract",
                "upstream_refresh_commands": rebuild_validation_contract["upstream_refresh_commands"],
                "prerequisite_rebuild_command": rebuild_validation_contract["prerequisite_rebuild_command"],
                "rebuild_command": rebuild_validation_contract["rebuild_command"],
                "direct_validation_command": rebuild_validation_contract["direct_validation_command"],
                "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": rebuild_validation_contract[
                    "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
                ],
                "requires_source_consistency_before_quoting_current_totals": rebuild_validation_contract[
                    "requires_source_consistency_before_quoting_current_totals"
                ],
                "requires_source_freshness_before_right_now_instruction_use": rebuild_validation_contract[
                    "requires_source_freshness_before_right_now_instruction_use"
                ],
                "upstream_refresh_order_is_provenance_metadata_only": rebuild_validation_contract[
                    "upstream_refresh_order_is_provenance_metadata_only"
                ],
                "not_settled_roi_or_real_money_evidence": rebuild_validation_contract[
                    "not_settled_roi_or_real_money_evidence"
                ],
            },
            "scorecard_audit_route_read": {
                "source": CURRENT_EVIDENCE_JSON.name,
                "source_path": "scorecard_audit_route",
                "markdown_path": scorecard_audit_route["markdown_path"],
                "json_path": scorecard_audit_route["json_path"],
                "validator_command": scorecard_audit_route["validator_command"],
                "gate_floor_source": scorecard_audit_route["gate_floor_source"],
                "gate_floor_snapshot": scorecard_audit_route["gate_floor_snapshot"],
                "route_read": scorecard_audit_route["route_read"],
                "artifacts_present": scorecard_audit_route["artifacts_present"],
                "not_forward_performance_evidence": scorecard_audit_route["not_forward_performance_evidence"],
                "not_settled_roi_evidence": scorecard_audit_route["not_settled_roi_evidence"],
                "not_promotion_readiness_evidence": scorecard_audit_route["not_promotion_readiness_evidence"],
                "not_live_profitability_evidence": scorecard_audit_route["not_live_profitability_evidence"],
                "not_bankroll_guidance": scorecard_audit_route["not_bankroll_guidance"],
                "not_real_money_evidence": scorecard_audit_route["not_real_money_evidence"],
            },
            "scorecard_decision_gate_minimums": scorecard_decision_gates,
            "decision_change_gate_minimums": decision_gates,
            "narrow_follow_up_reads": [
                "CROSS_FAMILY_DECISION.md",
                "OP_ANCHOR_METHOD_COMPARISON.md",
                "AB_DOWNSTREAM_COMPARISON.md",
                "compare_recommender_scope_paths.md",
            ],
            "suite_read": suite_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }

    lines = [
        "# Method Family Decision Card Validation",
        "",
        "This report validates the method-family card directly, including the saved CSV and markdown artifacts plus the real CLI stdout report, save notices, inherited scorecard ranking contract, direct scorecard decision gates, source-provenance fingerprints, and fail-fast checks for missing compare-main, cross-family, backtest, downstream A/B, scorecard-ranking, or scorecard-gate source pieces.",
        "",
        "## Artifact Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Saved artifacts: `{METHOD_CSV.name}`, `{METHOD_MD.name}`",
        f"- Temporary fixture root: `{tmp_parent}` (cleared before CLI fixture run)",
        f"- Rows checked: {len(saved_df)}",
        "- Result: PASS",
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
            f"- Source scope line: `valid_evidence_scope={mfd.VALID_EVIDENCE_SCOPE}`",
            "- Source-drift guardrail: required compare-main methods, selective shadow rows, Harville benchmark rows, and downstream A/B delta fields now fail fast instead of degrading into a polished-looking but incomplete method hierarchy",
            "- Source provenance: the method-family markdown fingerprints compare-main, cross-family, scorecard, backtest, and downstream A/B inputs and the direct validator compares those byte counts and SHA-256 values to disk.",
            f"- Current operator boundary: refresh route={operator_boundary['refresh_action_command']}, wrapper-can-settle-rows={operator_boundary['refresh_can_settle_open_rows_by_itself']}, wrapper-counts-as-ROI-evidence={operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}, clean-empty-forward-performance={operator_boundary['clean_empty_refresh_counts_as_forward_performance']}; {operator_boundary['roi_complete_primary_rows']}/{operator_boundary['first_read_threshold']} primary ROI-complete rows; current settled rule mix OP_DURABLE_K7={operator_boundary['op_anchor_roi_complete_rows']} / CD_CORE_K8={operator_boundary['cd_companion_roi_complete_rows']}; settlement-queue state={operator_boundary['open_settlement_queue_state']} / context={operator_boundary['open_settlement_context']}; recommendation-state context={operator_boundary['recommendation_context_read']}; this is routing/provenance only, not settled ROI, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- Bridge-published gate progress: `{CURRENT_EVIDENCE_JSON.name}` `decision_gate_progress` says {current_gate_progress['read']} gate_status={current_gate_progress['gate_status']}; all_gates_ready={current_gate_progress['all_gates_ready']}; this is routing context only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- Current bridge rebuild order: `{CURRENT_EVIDENCE_JSON.name}` `rebuild_validation_contract` routes source-byte changes through {' -> '.join(rebuild_validation_contract['upstream_refresh_commands'])} before quoting `CURRENT_EVIDENCE_SUMMARY.*`; this is provenance/rebuild metadata only, not method-family evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- Scorecard audit route: `{CURRENT_EVIDENCE_JSON.name}` `scorecard_audit_route` points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to `{scorecard_audit_route['markdown_path']}` / `{scorecard_audit_route['json_path']}` plus `{scorecard_audit_route['validator_command']}`; route_read={scorecard_audit_route['route_read']}; this is report-synchronization metadata only, not method-family evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- Source freshness provenance: bridge reference={operator_boundary['source_freshness_generated_reference_date']} ({operator_boundary['source_freshness_generated_reference_timezone']}), comparison={operator_boundary['source_freshness_staleness_comparison_source']} / {operator_boundary['source_freshness_staleness_comparison_date']}; read={operator_boundary['source_freshness_read']}",
            f"- Decision gates: phase8_promotion_review={scorecard_decision_gates['phase8_promotion_review']['minimum_roi_complete_settled_observations']}, anchor_displacement={scorecard_decision_gates['anchor_displacement']['minimum_roi_complete_same_candidate_observations']}, real_money_discussion={scorecard_decision_gates['real_money_discussion']['minimum_total_settled_roi_complete_observations']}; these are loaded directly from scorecard `decision_gate_minimums`, cross-checked against compare-main copied gate values, and are posture gates only.",
            f"- Scorecard ranking contract: tier-first={scorecard_ranking_contract['rank_is_tier_first_decision_order']}; raw-score-promotional={not scorecard_ranking_contract['raw_score_is_not_an_automatic_deployment_instruction']}; {scorecard_ranking_contract['known_rank_override']}",
            f"- PAPER NOW: Selective rule path ({float(df.loc['selective_rule_path', 'primary_metric']):+.2f}% holdout on {int(df.loc['selective_rule_path', 'primary_sample'])} races; 2024={float(df.loc['selective_rule_path', 'holdout_2024_metric']):+.2f}% on {int(df.loc['selective_rule_path', 'holdout_2024_sample'])}, 2025={float(df.loc['selective_rule_path', 'holdout_2025_metric']):+.2f}% on {int(df.loc['selective_rule_path', 'holdout_2025_sample'])})",
            f"- BENCHMARK ONLY: Harville-ranked probabilities ({float(df.loc['harville_ranked', 'primary_metric']):+.2f}% broad ROI on {int(df.loc['harville_ranked', 'primary_sample'])} races)",
            f"- RESEARCH ONLY: XGBoost residual correction ({float(df.loc['xgboost_residual', 'primary_metric']):+.2f}% best ML betting ROI, {float(df.loc['xgboost_residual', 'secondary_metric']):+.2f}% payout RMSE reduction)",
            f"- Selective-family paper-companion read: anchor={df.loc['selective_rule_path', 'current_anchor']}, paper companion={df.loc['selective_rule_path', 'primary_shadow']}, closest shadow={df.loc['selective_rule_path', 'secondary_shadow']}",
            "- Narrow follow-up reads: `CROSS_FAMILY_DECISION.md`, `OP_ANCHOR_METHOD_COMPARISON.md`, `AB_DOWNSTREAM_COMPARISON.md`, `compare_recommender_scope_paths.md`",
            "",
            "## Bottom Line",
            "",
            "- Green here means the method-family card is still pinned to the frozen 2024-2025 holdout standard, the saved CSV/markdown surfaces still rebuild cleanly from source, and the paper-facing method ordering still says selective rules first, Harville second, XGBoost third.",
            "- It does not mean Harville or XGBoost found a new deployment case, and it does not authorize swapping in a prettier alternate evaluation window.",
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
