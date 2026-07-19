#!/usr/bin/env python3
"""
Validation for the OP family decision card.

Purpose:
- keep the OP-family decision artifact reproducible
- pin the saved CSV / markdown surfaces against a fresh rebuild
- pin the real CLI stdout report plus save notices
- pin the conservative replacement bar for OP_DURABLE_K7
- catch drift where a prettier small-sample challenger might get promoted too easily
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.testing import assert_frame_equal

import compare_main_approaches as cma
import op_family_decision as ofd

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "out" / "status_validation" / "op_family_decision"
OUT_MD = OUT_DIR / "op_family_decision_validation.md"
OUT_JSON = OUT_DIR / "op_family_decision_validation.json"
TMP_PARENT = OUT_DIR / "_tmp"
REBUILD_COMMAND = "python3 validate_op_family_decision.py"
OP_SCRIPT = BASE / "op_family_decision.py"
OP_CSV = BASE / "op_family_decision.csv"
OP_MD = BASE / "OP_FAMILY_DECISION.md"
FROZEN_EVAL = BASE / "frozen_portfolio_eval_summary.csv"
SCORECARD_CSV = BASE / "forward_evidence_scorecard.csv"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
COMPARE_JSON = BASE / "compare_main_approaches.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
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
        raise AssertionError(f"rebuilt OP-family frame is missing saved columns {missing_cols}")
    rebuilt = rebuilt[saved.columns]
    assert_frame_equal(
        normalize_frame(saved, "label"),
        normalize_frame(rebuilt, "label"),
        check_dtype=False,
        check_exact=False,
        atol=1e-9,
        rtol=0,
    )


def build_expected_cli_stdout(report_text: str, csv_name: str = "op_family_decision.csv", md_name: str = "OP_FAMILY_DECISION.md") -> str:
    return report_text + f"Saved: {csv_name}\nSaved: {md_name}\n"


def frozen_row(level: str, name: str, slice_name: str) -> pd.Series:
    df = pd.read_csv(FROZEN_EVAL)
    match = df[(df["level"] == level) & (df["name"] == name) & (df["slice"] == slice_name)]
    if match.empty:
        raise AssertionError(f"Missing frozen row for {level} / {name} / {slice_name}")
    return match.iloc[0]


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
        label = source.strip("`")
        rows[label] = {
            "path": path.strip("`"),
            "bytes": int(byte_count),
            "sha256": sha.strip("`"),
        }
    return rows


def source_provenance_matches_disk(markdown_text: str) -> bool:
    markdown_rows = parse_source_provenance_table(markdown_text)
    expected = ofd.source_file_fingerprints()
    if set(markdown_rows) != set(expected):
        return False
    for label, expected_fingerprint in expected.items():
        if markdown_rows[label] != expected_fingerprint:
            return False
    return True


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_parent = prepare_tmp_parent()
    scratch_meta = {
        "tmp_parent": str(tmp_parent),
        "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
        "tmp_parent_cleared_before_fixture_run": True,
    }

    saved_df = pd.read_csv(OP_CSV)
    rebuilt_df = ofd.build_dataframe()
    compare_like_saved(saved_df, rebuilt_df)
    saved_md = OP_MD.read_text(encoding="utf-8")
    rebuilt_md = ofd.build_markdown(rebuilt_df)
    if not rebuilt_md.endswith("\n"):
        rebuilt_md += "\n"

    df = rebuilt_df.set_index("label")
    compare_df, _wf_years, _folds, holdout_switch_choices = cma.build_dataframe(cma.DEFAULT_HOLDOUT_YEARS)
    compare_df = compare_df.set_index("method_id")

    durable_holdout = frozen_row("rule", "OP_DURABLE_K7", "holdout_2024_2025")
    refined_holdout = frozen_row("rule", "OP_REFINED_K7", "holdout_2024_2025")
    scorecard_df = pd.read_csv(SCORECARD_CSV).set_index("rule_id")
    scorecard_ranking_contract = ofd.load_scorecard_ranking_contract(SCORECARD_JSON)
    scorecard_decision_gates = ofd.load_scorecard_decision_gate_minimums(SCORECARD_JSON)
    scorecard_ci_only_diagnostic = ofd.load_scorecard_ci_only_diagnostic(SCORECARD_JSON)
    operator_boundary = ofd.load_current_operator_boundary(COMPARE_JSON)
    current_gate_progress = ofd.load_current_gate_progress(CURRENT_EVIDENCE_JSON)
    scorecard_audit_route = ofd.load_scorecard_audit_route(CURRENT_EVIDENCE_JSON)
    rebuild_validation_contract = ofd.load_rebuild_validation_contract(CURRENT_EVIDENCE_JSON)
    operator_read_gate = operator_boundary["operator_read_gate"]
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

    holdout_choice_map = {
        int(row.test_year): str(row.rule_id)
        for _, row in holdout_switch_choices.sort_values("test_year").iterrows()
    }

    checks: list[dict[str, Any]] = []
    checks.append(
        require(
            saved_md == rebuilt_md,
            "markdown_matches_rebuild",
            "OP_FAMILY_DECISION.md still matches a fresh rebuild from op_family_decision.py",
        )
    )
    checks.append(
        require(
            "holdout_2024_races" in saved_df.columns and "holdout_2025_races" in saved_df.columns and "holdout_ci_lower" in saved_df.columns and "secondary_basis" in saved_df.columns,
            "csv_year_count_columns_present",
            "op_family_decision.csv still carries the year-specific holdout race-count columns plus the scorecard-backed CI-lower column and explicit secondary-basis labeling alongside the year ROIs",
        )
    )

    with tempfile.TemporaryDirectory(prefix="op_family_cli_", dir=tmp_parent) as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        pinned_dir = tmpdir / "pinned_out"
        pinned_csv = pinned_dir / "op_family_custom.csv"
        pinned_md = pinned_dir / "OP_FAMILY_CUSTOM.md"
        alt_cache = tmpdir / "alt_phase5_cache.pkl"
        alt_phase7 = tmpdir / "alt_phase7_rules.json"
        alt_wf_rules = tmpdir / "alt_walk_forward_rules.csv"
        alt_scorecard = tmpdir / "alt_forward_scorecard.csv"
        alt_scorecard_json = tmpdir / "alt_forward_scorecard.json"
        alt_compare_json = tmpdir / "alt_compare_main_approaches.json"
        alt_current_evidence_json = tmpdir / "alt_current_evidence_summary.json"
        for src in [
            OP_SCRIPT,
            Path(cma.__file__).resolve(),
            cma.CACHE_PATH,
            cma.PHASE7_RULES_PATH,
            cma.WF_RULES_PATH,
            SCORECARD_CSV,
            SCORECARD_JSON,
            COMPARE_JSON,
            CURRENT_EVIDENCE_JSON,
            SCORECARD_AUDIT_MD,
            SCORECARD_AUDIT_JSON,
        ]:
            shutil.copy2(src, tmpdir / src.name)
        shutil.copy2(cma.CACHE_PATH, alt_cache)
        shutil.copy2(cma.PHASE7_RULES_PATH, alt_phase7)
        shutil.copy2(cma.WF_RULES_PATH, alt_wf_rules)
        shutil.copy2(SCORECARD_CSV, alt_scorecard)
        shutil.copy2(SCORECARD_JSON, alt_scorecard_json)
        shutil.copy2(COMPARE_JSON, alt_compare_json)
        shutil.copy2(CURRENT_EVIDENCE_JSON, alt_current_evidence_json)
        cli_result = subprocess.run(
            [sys.executable, OP_SCRIPT.name],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        cli_csv = pd.read_csv(tmpdir / OP_CSV.name)
        compare_like_saved(saved_df, cli_csv)
        cli_report_text = (tmpdir / OP_MD.name).read_text(encoding="utf-8")
        if cli_report_text != rebuilt_md:
            raise AssertionError("CLI-generated OP_FAMILY_DECISION.md drifted from a fresh rebuild")
        expected_cli_stdout = build_expected_cli_stdout(cli_report_text)
        if cli_result.stdout != expected_cli_stdout:
            raise AssertionError("op_family_decision.py CLI stdout no longer matches its generated report plus save notices")

        pinned_result = subprocess.run(
            [
                sys.executable,
                OP_SCRIPT.name,
                "--cache-pkl",
                str(alt_cache),
                "--phase7-rules-json",
                str(alt_phase7),
                "--wf-rules-csv",
                str(alt_wf_rules),
                "--scorecard-csv",
                str(alt_scorecard),
                "--scorecard-json",
                str(alt_scorecard_json),
                "--compare-json",
                str(alt_compare_json),
                "--current-evidence-json",
                str(alt_current_evidence_json),
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
        pinned_rebuilt_md = ofd.build_markdown(
            ofd.build_dataframe(
                cache_path=alt_cache,
                phase7_rules_path=alt_phase7,
                wf_rules_path=alt_wf_rules,
                scorecard_path=alt_scorecard,
            ),
            cache_name=alt_cache.name,
            phase7_rules_name=alt_phase7.name,
            wf_rules_name=alt_wf_rules.name,
            scorecard_name=alt_scorecard.name,
            scorecard_json_name=alt_scorecard_json.name,
            compare_json_name=alt_compare_json.name,
            current_evidence_json_name=alt_current_evidence_json.name,
            csv_output_name=pinned_csv.name,
            md_output_name=pinned_md.name,
            scorecard_json_path=alt_scorecard_json,
            compare_json_path=alt_compare_json,
            current_evidence_json_path=alt_current_evidence_json,
            source_paths={
                "compare_main_approaches": tmpdir / Path(cma.__file__).resolve().name,
                "compare_main_approaches_json": alt_compare_json,
                "current_evidence_summary": alt_current_evidence_json,
                "phase5_race_cache": alt_cache,
                "phase7_rules": alt_phase7,
                "walk_forward_rules": alt_wf_rules,
                "forward_evidence_scorecard_csv": alt_scorecard,
                "forward_evidence_scorecard_json": alt_scorecard_json,
            },
        )
        if not pinned_rebuilt_md.endswith("\n"):
            pinned_rebuilt_md += "\n"
        if pinned_report_text != pinned_rebuilt_md:
            raise AssertionError("Pinned/custom-output OP_FAMILY_DECISION.md drifted from a fresh rebuild")
        expected_pinned_stdout = build_expected_cli_stdout(pinned_report_text, csv_name=pinned_csv.name, md_name=pinned_md.name)
        if pinned_result.stdout != expected_pinned_stdout:
            raise AssertionError("Pinned/custom-output op_family_decision.py CLI stdout no longer matches its generated report plus save notices")

        missing_cache = tmpdir / "missing_hit7_cache.pkl"
        missing_phase7 = tmpdir / "missing_op_durable_phase7_rules.json"
        missing_wf_rules = tmpdir / "missing_op_refined_wf_rules.csv"
        missing_scorecard = tmpdir / "missing_op_refined_scorecard.csv"
        missing_scorecard_json = tmpdir / "missing_ranking_contract_scorecard.json"
        missing_ci_only_diagnostic_scorecard_json = tmpdir / "missing_ci_only_diagnostic_scorecard.json"
        missing_decision_gate_scorecard_json = tmpdir / "missing_decision_gate_scorecard.json"
        malformed_decision_gate_scorecard_json = tmpdir / "malformed_decision_gate_scorecard.json"
        nonpositive_phase8_gate_scorecard_json = tmpdir / "nonpositive_phase8_gate_scorecard.json"
        nonpositive_real_money_gate_scorecard_json = tmpdir / "nonpositive_real_money_gate_scorecard.json"
        missing_no_baq_gate_scorecard_json = tmpdir / "missing_no_baq_gate_scorecard.json"
        bad_operator_generated_at_json = tmpdir / "bad_operator_generated_at_compare_main.json"
        missing_source_freshness_reference_json = tmpdir / "missing_source_freshness_reference_compare_main.json"
        false_refresh_boundary_flag_json = tmpdir / "false_refresh_boundary_flag_compare_main.json"
        false_refresh_accounting_flag_json = tmpdir / "false_refresh_accounting_flag_compare_main.json"
        missing_scorecard_audit_route_json = tmpdir / "missing_scorecard_audit_route_current_evidence.json"
        missing_rebuild_validation_contract_json = tmpdir / "missing_rebuild_validation_contract_current_evidence.json"
        weakened_rebuild_validation_contract_json = tmpdir / "weakened_rebuild_validation_contract_current_evidence.json"
        missing_gate_output_dir = tmpdir / "missing_gate_nested_output" / "artifacts"
        missing_gate_should_not_write_csv = missing_gate_output_dir / "missing_gate_should_not_write.csv"
        missing_gate_should_not_write_md = missing_gate_output_dir / "missing_gate_should_not_write.md"
        malformed_gate_output_dir = tmpdir / "malformed_gate_nested_output" / "artifacts"
        malformed_gate_should_not_write_csv = malformed_gate_output_dir / "malformed_gate_should_not_write.csv"
        malformed_gate_should_not_write_md = malformed_gate_output_dir / "malformed_gate_should_not_write.md"
        nonpositive_phase8_gate_output_dir = tmpdir / "nonpositive_phase8_gate_nested_output" / "artifacts"
        nonpositive_phase8_gate_should_not_write_csv = (
            nonpositive_phase8_gate_output_dir / "nonpositive_phase8_gate_should_not_write.csv"
        )
        nonpositive_phase8_gate_should_not_write_md = (
            nonpositive_phase8_gate_output_dir / "nonpositive_phase8_gate_should_not_write.md"
        )
        nonpositive_real_money_gate_output_dir = tmpdir / "nonpositive_real_money_gate_nested_output" / "artifacts"
        nonpositive_real_money_gate_should_not_write_csv = (
            nonpositive_real_money_gate_output_dir / "nonpositive_real_money_gate_should_not_write.csv"
        )
        nonpositive_real_money_gate_should_not_write_md = (
            nonpositive_real_money_gate_output_dir / "nonpositive_real_money_gate_should_not_write.md"
        )
        missing_no_baq_output_dir = tmpdir / "missing_no_baq_nested_output" / "artifacts"
        missing_no_baq_should_not_write_csv = missing_no_baq_output_dir / "missing_no_baq_should_not_write.csv"
        missing_no_baq_should_not_write_md = missing_no_baq_output_dir / "missing_no_baq_should_not_write.md"
        bad_generated_at_output_dir = tmpdir / "bad_generated_at_nested_output" / "artifacts"
        bad_generated_at_should_not_write_csv = bad_generated_at_output_dir / "bad_generated_at_should_not_write.csv"
        bad_generated_at_should_not_write_md = bad_generated_at_output_dir / "bad_generated_at_should_not_write.md"
        missing_source_freshness_reference_output_dir = tmpdir / "missing_source_freshness_reference_nested_output" / "artifacts"
        missing_source_freshness_reference_should_not_write_csv = (
            missing_source_freshness_reference_output_dir / "missing_source_freshness_reference_should_not_write.csv"
        )
        missing_source_freshness_reference_should_not_write_md = (
            missing_source_freshness_reference_output_dir / "missing_source_freshness_reference_should_not_write.md"
        )
        false_refresh_boundary_flag_output_dir = tmpdir / "false_refresh_boundary_flag_nested_output" / "artifacts"
        false_refresh_boundary_flag_should_not_write_csv = (
            false_refresh_boundary_flag_output_dir / "false_refresh_boundary_flag_should_not_write.csv"
        )
        false_refresh_boundary_flag_should_not_write_md = (
            false_refresh_boundary_flag_output_dir / "false_refresh_boundary_flag_should_not_write.md"
        )
        false_refresh_accounting_flag_output_dir = tmpdir / "false_refresh_accounting_flag_nested_output" / "artifacts"
        false_refresh_accounting_flag_should_not_write_csv = (
            false_refresh_accounting_flag_output_dir / "false_refresh_accounting_flag_should_not_write.csv"
        )
        false_refresh_accounting_flag_should_not_write_md = (
            false_refresh_accounting_flag_output_dir / "false_refresh_accounting_flag_should_not_write.md"
        )
        missing_ci_only_output_dir = tmpdir / "missing_ci_only_nested_output" / "artifacts"
        missing_ci_only_should_not_write_csv = missing_ci_only_output_dir / "missing_ci_only_should_not_write.csv"
        missing_ci_only_should_not_write_md = missing_ci_only_output_dir / "missing_ci_only_should_not_write.md"
        missing_scorecard_audit_route_output_dir = tmpdir / "missing_scorecard_audit_route_nested_output" / "artifacts"
        missing_scorecard_audit_route_should_not_write_csv = (
            missing_scorecard_audit_route_output_dir / "missing_scorecard_audit_route_should_not_write.csv"
        )
        missing_scorecard_audit_route_should_not_write_md = (
            missing_scorecard_audit_route_output_dir / "missing_scorecard_audit_route_should_not_write.md"
        )
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

        missing_cache_df = pd.read_pickle(alt_cache).drop(columns=["hit_7"])
        missing_cache_df.to_pickle(missing_cache)
        missing_cache_result = subprocess.run(
            [sys.executable, OP_SCRIPT.name, "--cache-pkl", str(missing_cache)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_cache_result.returncode == 0:
            raise AssertionError("op_family_decision.py unexpectedly accepted a cache missing hit_7")
        missing_cache_text = f"{missing_cache_result.stdout}\n{missing_cache_result.stderr}"
        if "is missing required cache columns: hit_7" not in missing_cache_text:
            raise AssertionError("cache failure no longer explains that hit_7 is required for the OP-family card")

        missing_phase7_payload = json.loads(alt_phase7.read_text(encoding="utf-8"))
        missing_phase7_payload["rules"] = [
            row for row in missing_phase7_payload["rules"] if row.get("rule_id") != "OP_DURABLE_K7"
        ]
        missing_phase7.write_text(json.dumps(missing_phase7_payload, indent=2) + "\n", encoding="utf-8")
        missing_phase7_result = subprocess.run(
            [sys.executable, OP_SCRIPT.name, "--phase7-rules-json", str(missing_phase7)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_phase7_result.returncode == 0:
            raise AssertionError("op_family_decision.py unexpectedly accepted Phase 7 rules without OP_DURABLE_K7")
        missing_phase7_text = f"{missing_phase7_result.stdout}\n{missing_phase7_result.stderr}"
        if "missing required Phase 7 OP rule rows: OP_DURABLE_K7" not in missing_phase7_text:
            raise AssertionError("Phase 7 failure no longer explains that OP_DURABLE_K7 is required for the OP-family card")

        missing_wf_df = pd.read_csv(alt_wf_rules)
        missing_wf_df = missing_wf_df[
            ~((missing_wf_df["test_year"] == 2025) & (missing_wf_df["rule_id"] == "OP_REFINED_K7"))
        ].copy()
        missing_wf_df.to_csv(missing_wf_rules, index=False)
        missing_wf_result = subprocess.run(
            [sys.executable, OP_SCRIPT.name, "--wf-rules-csv", str(missing_wf_rules)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_wf_result.returncode == 0:
            raise AssertionError("op_family_decision.py unexpectedly accepted walk-forward rules without OP_REFINED_K7/year_2025")
        missing_wf_text = f"{missing_wf_result.stdout}\n{missing_wf_result.stderr}"
        if "missing required walk-forward OP rule rows: OP_REFINED_K7/year_2025" not in missing_wf_text:
            raise AssertionError("walk-forward failure no longer explains that OP_REFINED_K7/year_2025 is required for the OP-family card")

        missing_scorecard_df = pd.read_csv(alt_scorecard)
        missing_scorecard_df = missing_scorecard_df[missing_scorecard_df["rule_id"] != "OP_REFINED_K7"].copy()
        missing_scorecard_df.to_csv(missing_scorecard, index=False)
        missing_scorecard_result = subprocess.run(
            [sys.executable, OP_SCRIPT.name, "--scorecard-csv", str(missing_scorecard)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_scorecard_result.returncode == 0:
            raise AssertionError("op_family_decision.py unexpectedly accepted a scorecard missing OP_REFINED_K7")
        missing_scorecard_text = f"{missing_scorecard_result.stdout}\n{missing_scorecard_result.stderr}"
        if "missing required scorecard rule rows: OP_REFINED_K7" not in missing_scorecard_text:
            raise AssertionError("scorecard failure no longer explains that OP_REFINED_K7 is required for the OP-family card")

        missing_contract_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        missing_contract_payload.pop("ranking_contract", None)
        missing_scorecard_json.write_text(json.dumps(missing_contract_payload, indent=2) + "\n", encoding="utf-8")
        missing_scorecard_json_result = subprocess.run(
            [sys.executable, OP_SCRIPT.name, "--scorecard-json", str(missing_scorecard_json)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_scorecard_json_result.returncode == 0:
            raise AssertionError("op_family_decision.py unexpectedly accepted a scorecard JSON missing ranking_contract")
        missing_scorecard_json_text = f"{missing_scorecard_json_result.stdout}\n{missing_scorecard_json_result.stderr}"
        if "missing ranking_contract" not in missing_scorecard_json_text:
            raise AssertionError("scorecard JSON failure no longer explains that ranking_contract is required for the OP-family card")

        missing_ci_only_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        missing_ci_only_payload.pop("ci_only_promotion_diagnostics", None)
        missing_ci_only_diagnostic_scorecard_json.write_text(
            json.dumps(missing_ci_only_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_ci_only_result = subprocess.run(
            [
                sys.executable,
                OP_SCRIPT.name,
                "--scorecard-json",
                str(missing_ci_only_diagnostic_scorecard_json),
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
            raise AssertionError("op_family_decision.py unexpectedly accepted a scorecard JSON missing ci_only_promotion_diagnostics")
        missing_ci_only_text = f"{missing_ci_only_result.stdout}\n{missing_ci_only_result.stderr}"
        if "missing ci_only_promotion_diagnostics" not in missing_ci_only_text:
            raise AssertionError("scorecard JSON failure no longer explains that ci_only_promotion_diagnostics is required for the OP-family card")
        if missing_ci_only_output_dir.exists() or missing_ci_only_should_not_write_csv.exists() or missing_ci_only_should_not_write_md.exists():
            raise AssertionError("missing CI-only diagnostic created output directories or wrote partial OP-family artifacts before failing")

        shutil.copy2(SCORECARD_JSON, missing_decision_gate_scorecard_json)
        missing_gate_payload = json.loads(missing_decision_gate_scorecard_json.read_text(encoding="utf-8"))
        missing_gate_payload.pop("decision_gate_minimums", None)
        missing_decision_gate_scorecard_json.write_text(json.dumps(missing_gate_payload, indent=2) + "\n", encoding="utf-8")
        missing_gate_result = subprocess.run(
            [
                sys.executable,
                OP_SCRIPT.name,
                "--scorecard-json",
                str(missing_decision_gate_scorecard_json),
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
            raise AssertionError("op_family_decision.py unexpectedly accepted a scorecard JSON missing decision_gate_minimums")
        missing_gate_text = f"{missing_gate_result.stdout}\n{missing_gate_result.stderr}"
        if "missing decision_gate_minimums" not in missing_gate_text:
            raise AssertionError("scorecard JSON failure no longer explains that decision_gate_minimums is required for the OP-family card")
        if missing_gate_output_dir.exists() or missing_gate_should_not_write_csv.exists() or missing_gate_should_not_write_md.exists():
            raise AssertionError("scorecard JSON decision-gate failure created output directories or wrote partial OP-family artifacts before failing")

        malformed_gate_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        malformed_gate_payload["decision_gate_minimums"]["anchor_displacement"][
            "min_roi_complete_settled_observations"
        ] = True
        malformed_decision_gate_scorecard_json.write_text(
            json.dumps(malformed_gate_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        malformed_gate_result = subprocess.run(
            [
                sys.executable,
                OP_SCRIPT.name,
                "--scorecard-json",
                str(malformed_decision_gate_scorecard_json),
                "--csv-output",
                str(malformed_gate_should_not_write_csv),
                "--md-output",
                str(malformed_gate_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if malformed_gate_result.returncode == 0:
            raise AssertionError("op_family_decision.py unexpectedly accepted a boolean anchor-displacement gate floor")
        malformed_gate_text = f"{malformed_gate_result.stdout}\n{malformed_gate_result.stderr}"
        if "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations must be a positive non-boolean integer" not in malformed_gate_text:
            raise AssertionError("scorecard JSON failure no longer explains that boolean gate floors are malformed")
        if malformed_gate_output_dir.exists() or malformed_gate_should_not_write_csv.exists() or malformed_gate_should_not_write_md.exists():
            raise AssertionError("malformed scorecard gate floor created output directories or wrote partial OP-family artifacts before failing")

        nonpositive_phase8_gate_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        nonpositive_phase8_gate_payload["decision_gate_minimums"]["phase8_promotion_review"][
            "min_roi_complete_settled_observations"
        ] = 0
        nonpositive_phase8_gate_scorecard_json.write_text(
            json.dumps(nonpositive_phase8_gate_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        nonpositive_phase8_gate_result = subprocess.run(
            [
                sys.executable,
                OP_SCRIPT.name,
                "--scorecard-json",
                str(nonpositive_phase8_gate_scorecard_json),
                "--csv-output",
                str(nonpositive_phase8_gate_should_not_write_csv),
                "--md-output",
                str(nonpositive_phase8_gate_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if nonpositive_phase8_gate_result.returncode == 0:
            raise AssertionError("op_family_decision.py unexpectedly accepted a non-positive Phase 8 promotion-review gate floor")
        nonpositive_phase8_gate_text = f"{nonpositive_phase8_gate_result.stdout}\n{nonpositive_phase8_gate_result.stderr}"
        if "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer" not in nonpositive_phase8_gate_text:
            raise AssertionError("scorecard JSON failure no longer explains that non-positive Phase 8 gate floors are malformed")
        if (
            nonpositive_phase8_gate_output_dir.exists()
            or nonpositive_phase8_gate_should_not_write_csv.exists()
            or nonpositive_phase8_gate_should_not_write_md.exists()
        ):
            raise AssertionError("non-positive Phase 8 scorecard gate floor created output directories or wrote partial OP-family artifacts before failing")

        nonpositive_real_money_gate_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        nonpositive_real_money_gate_payload["decision_gate_minimums"]["real_money_discussion"][
            "min_total_settled_observations_with_usable_roi"
        ] = 0
        nonpositive_real_money_gate_scorecard_json.write_text(
            json.dumps(nonpositive_real_money_gate_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        nonpositive_real_money_gate_result = subprocess.run(
            [
                sys.executable,
                OP_SCRIPT.name,
                "--scorecard-json",
                str(nonpositive_real_money_gate_scorecard_json),
                "--csv-output",
                str(nonpositive_real_money_gate_should_not_write_csv),
                "--md-output",
                str(nonpositive_real_money_gate_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if nonpositive_real_money_gate_result.returncode == 0:
            raise AssertionError("op_family_decision.py unexpectedly accepted a non-positive real-money discussion gate floor")
        nonpositive_real_money_gate_text = f"{nonpositive_real_money_gate_result.stdout}\n{nonpositive_real_money_gate_result.stderr}"
        if "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer" not in nonpositive_real_money_gate_text:
            raise AssertionError("scorecard JSON failure no longer explains that non-positive real-money gate floors are malformed")
        if (
            nonpositive_real_money_gate_output_dir.exists()
            or nonpositive_real_money_gate_should_not_write_csv.exists()
            or nonpositive_real_money_gate_should_not_write_md.exists()
        ):
            raise AssertionError("non-positive real-money scorecard gate floor created output directories or wrote partial OP-family artifacts before failing")

        missing_no_baq_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"]["also_requires"] = [
            item
            for item in missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"]["also_requires"]
            if item != ofd.NO_BAQ_AS_BEL_PREREQUISITE
        ]
        missing_no_baq_gate_scorecard_json.write_text(
            json.dumps(missing_no_baq_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_no_baq_result = subprocess.run(
            [
                sys.executable,
                OP_SCRIPT.name,
                "--scorecard-json",
                str(missing_no_baq_gate_scorecard_json),
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
            raise AssertionError("op_family_decision.py unexpectedly accepted a real-money gate without the no-BAQ-as-BEL prerequisite")
        missing_no_baq_text = f"{missing_no_baq_result.stdout}\n{missing_no_baq_result.stderr}"
        if "must include 'no BAQ-as-BEL substitution'" not in missing_no_baq_text:
            raise AssertionError("scorecard JSON failure no longer explains that no-BAQ-as-BEL is required for the real-money gate")
        if missing_no_baq_output_dir.exists() or missing_no_baq_should_not_write_csv.exists() or missing_no_baq_should_not_write_md.exists():
            raise AssertionError("missing no-BAQ-as-BEL prerequisite created output directories or wrote partial OP-family artifacts before failing")

        bad_generated_at_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        bad_generated_at_payload["current_operator_boundary"]["generated_at"] = "2026-06-26T18:12:48"
        bad_operator_generated_at_json.write_text(json.dumps(bad_generated_at_payload, indent=2) + "\n", encoding="utf-8")
        bad_generated_at_result = subprocess.run(
            [
                sys.executable,
                OP_SCRIPT.name,
                "--compare-json",
                str(bad_operator_generated_at_json),
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
            raise AssertionError("op_family_decision.py unexpectedly accepted timezone-naive current_operator_boundary.generated_at")
        bad_generated_at_text = f"{bad_generated_at_result.stdout}\n{bad_generated_at_result.stderr}"
        if "current_operator_boundary generated_at must be timezone-aware ISO provenance metadata" not in bad_generated_at_text:
            raise AssertionError("compare-main JSON failure no longer explains that current_operator_boundary.generated_at must be timezone-aware provenance")
        if bad_generated_at_output_dir.exists() or bad_generated_at_should_not_write_csv.exists() or bad_generated_at_should_not_write_md.exists():
            raise AssertionError("bad current-operator generated_at failure created output directories or wrote partial OP-family artifacts before failing")

        missing_source_reference_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        del missing_source_reference_payload["current_operator_boundary"]["source_freshness_generated_reference_timezone"]
        missing_source_freshness_reference_json.write_text(
            json.dumps(missing_source_reference_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_source_reference_result = subprocess.run(
            [
                sys.executable,
                OP_SCRIPT.name,
                "--compare-json",
                str(missing_source_freshness_reference_json),
                "--csv-output",
                str(missing_source_freshness_reference_should_not_write_csv),
                "--md-output",
                str(missing_source_freshness_reference_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_source_reference_result.returncode == 0:
            raise AssertionError("op_family_decision.py unexpectedly accepted current_operator_boundary without source-freshness reference metadata")
        missing_source_reference_text = f"{missing_source_reference_result.stdout}\n{missing_source_reference_result.stderr}"
        if "current_operator_boundary is missing fields: source_freshness_generated_reference_timezone" not in missing_source_reference_text:
            raise AssertionError("compare-main JSON failure no longer names the missing current-operator source-freshness reference field")
        if (
            missing_source_freshness_reference_output_dir.exists()
            or missing_source_freshness_reference_should_not_write_csv.exists()
            or missing_source_freshness_reference_should_not_write_md.exists()
        ):
            raise AssertionError("missing source-freshness reference field created output directories or wrote partial OP-family artifacts before failing")

        false_refresh_boundary_flag_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        false_refresh_boundary_flag_payload["current_operator_boundary"]["refresh_boundary_not_real_money_evidence"] = False
        false_refresh_boundary_flag_json.write_text(
            json.dumps(false_refresh_boundary_flag_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        false_refresh_boundary_flag_result = subprocess.run(
            [
                sys.executable,
                OP_SCRIPT.name,
                "--compare-json",
                str(false_refresh_boundary_flag_json),
                "--csv-output",
                str(false_refresh_boundary_flag_should_not_write_csv),
                "--md-output",
                str(false_refresh_boundary_flag_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if false_refresh_boundary_flag_result.returncode == 0:
            raise AssertionError("op_family_decision.py unexpectedly accepted current_operator_boundary.refresh_boundary_not_real_money_evidence=false")
        false_refresh_boundary_flag_text = (
            f"{false_refresh_boundary_flag_result.stdout}\n{false_refresh_boundary_flag_result.stderr}"
        )
        if "current_operator_boundary must mark refresh_boundary_not_real_money_evidence=true" not in false_refresh_boundary_flag_text:
            raise AssertionError("compare-main JSON failure no longer explains that refresh_boundary_not_real_money_evidence must remain true")
        if (
            false_refresh_boundary_flag_output_dir.exists()
            or false_refresh_boundary_flag_should_not_write_csv.exists()
            or false_refresh_boundary_flag_should_not_write_md.exists()
        ):
            raise AssertionError("false refresh-boundary non-evidence flag created output directories or wrote partial OP-family artifacts before failing")

        false_refresh_accounting_flag_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        false_refresh_accounting_flag_payload["current_operator_boundary"][
            "refresh_counts_as_roi_complete_evidence_by_itself"
        ] = True
        false_refresh_accounting_flag_json.write_text(
            json.dumps(false_refresh_accounting_flag_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        false_refresh_accounting_flag_result = subprocess.run(
            [
                sys.executable,
                OP_SCRIPT.name,
                "--compare-json",
                str(false_refresh_accounting_flag_json),
                "--csv-output",
                str(false_refresh_accounting_flag_should_not_write_csv),
                "--md-output",
                str(false_refresh_accounting_flag_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if false_refresh_accounting_flag_result.returncode == 0:
            raise AssertionError("op_family_decision.py unexpectedly accepted current_operator_boundary.refresh_counts_as_roi_complete_evidence_by_itself=true")
        false_refresh_accounting_flag_text = (
            f"{false_refresh_accounting_flag_result.stdout}\n{false_refresh_accounting_flag_result.stderr}"
        )
        if "current_operator_boundary must preserve refresh_counts_as_roi_complete_evidence_by_itself=false" not in false_refresh_accounting_flag_text:
            raise AssertionError("compare-main JSON failure no longer explains that wrapper refresh cannot count as ROI-complete evidence")
        if (
            false_refresh_accounting_flag_output_dir.exists()
            or false_refresh_accounting_flag_should_not_write_csv.exists()
            or false_refresh_accounting_flag_should_not_write_md.exists()
        ):
            raise AssertionError("false refresh-accounting flag created output directories or wrote partial OP-family artifacts before failing")

        missing_route_payload = json.loads(alt_current_evidence_json.read_text(encoding="utf-8"))
        missing_route_payload.pop("scorecard_audit_route", None)
        missing_scorecard_audit_route_json.write_text(
            json.dumps(missing_route_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_scorecard_audit_route_result = subprocess.run(
            [
                sys.executable,
                OP_SCRIPT.name,
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
            raise AssertionError("op_family_decision.py unexpectedly accepted current_evidence_summary.json without scorecard_audit_route")
        missing_scorecard_audit_route_text = (
            f"{missing_scorecard_audit_route_result.stdout}\n{missing_scorecard_audit_route_result.stderr}"
        )
        if "missing scorecard_audit_route" not in missing_scorecard_audit_route_text:
            raise AssertionError("current-evidence JSON failure no longer explains that scorecard_audit_route is required for the OP-family card")
        if (
            missing_scorecard_audit_route_output_dir.exists()
            or missing_scorecard_audit_route_should_not_write_csv.exists()
            or missing_scorecard_audit_route_should_not_write_md.exists()
        ):
            raise AssertionError("missing scorecard audit route created output directories or wrote partial OP-family artifacts before failing")

        missing_rebuild_payload = json.loads(alt_current_evidence_json.read_text(encoding="utf-8"))
        missing_rebuild_payload.pop("rebuild_validation_contract", None)
        missing_rebuild_validation_contract_json.write_text(
            json.dumps(missing_rebuild_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_rebuild_validation_contract_result = subprocess.run(
            [
                sys.executable,
                OP_SCRIPT.name,
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
            raise AssertionError("op_family_decision.py unexpectedly accepted current_evidence_summary.json without rebuild_validation_contract")
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
            raise AssertionError("missing rebuild validation contract created output directories or wrote partial OP-family artifacts before failing")

        weakened_rebuild_payload = json.loads(alt_current_evidence_json.read_text(encoding="utf-8"))
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
                OP_SCRIPT.name,
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
            raise AssertionError("op_family_decision.py unexpectedly accepted current_evidence_summary.json with a weakened rebuild_validation_contract")
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
            raise AssertionError("weakened rebuild validation contract created output directories or wrote partial OP-family artifacts before failing")

    checks.append(
        require(
            True,
            "cli_csv_matches_saved",
            "op_family_decision.py CLI still writes a CSV that matches the saved OP-family decision table",
        )
    )
    checks.append(
        require(
            tmp_parent == TMP_PARENT
            and tmp_parent.exists()
            and tmp_parent.is_relative_to(BASE),
            "cli_scratch_root_project_local",
            f"OP-family CLI, custom-source, and negative source-drift fixtures use project-local temporary root {tmp_parent}, cleared before the fixture run",
        )
    )
    checks.append(
        require(
            scratch_meta["tmp_parent_is_project_local"] is True
            and scratch_meta["tmp_parent_cleared_before_fixture_run"] is True
            and Path(scratch_meta["tmp_parent"]) == TMP_PARENT,
            "cli_scratch_metadata_published",
            "OP-family validation publishes top-level project-local scratch metadata so parent rollups can verify the cleared fixture root without parsing rebuild fields or prose",
        )
    )
    checks.append(
        require(
            True,
            "cli_markdown_matches_rebuild",
            "op_family_decision.py CLI still writes OP_FAMILY_DECISION.md exactly as a fresh rebuild renders it",
        )
    )
    checks.append(
        require(
            True,
            "cli_stdout_matches_generated_report",
            "op_family_decision.py CLI stdout still matches the generated report plus its Saved: lines",
        )
    )
    checks.append(
        require(
            True,
            "cli_custom_input_and_output_paths",
            "op_family_decision.py can now rerender from explicit cache, Phase 7 rules, walk-forward rules, and scorecard input paths and write to custom output paths without depending on the default saved artifact names",
        )
    )
    checks.append(
        require(
            True,
            "cli_cache_contract_required",
            "op_family_decision.py now fails fast if the race cache loses required OP replay columns such as hit_7 instead of drifting into a traceback or incomplete replay",
        )
    )
    checks.append(
        require(
            True,
            "cli_phase7_anchor_rule_required",
            "op_family_decision.py now fails fast if the Phase 7 anchor source loses OP_DURABLE_K7 instead of quietly weakening the OP-family anchor line",
        )
    )
    checks.append(
        require(
            True,
            "cli_walk_forward_rule_rows_required",
            "op_family_decision.py now fails fast if the yearly OP walk-forward candidate set loses a required OP_DURABLE_K7 or OP_REFINED_K7 row",
        )
    )
    checks.append(
        require(
            True,
            "cli_scorecard_rule_rows_required",
            "op_family_decision.py now fails fast if the scorecard loses required OP rows or the anchor CI-lower input",
        )
    )
    checks.append(
        require(
            True,
            "cli_scorecard_ranking_contract_required",
            "op_family_decision.py now fails fast if the scorecard JSON loses ranking_contract instead of silently dropping tier-first ranking semantics",
        )
    )
    checks.append(
        require(
            True,
            "cli_scorecard_ci_only_diagnostic_required",
            "the real OP-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if the scorecard JSON loses the OP_REFINED CI-only diagnostic instead of locally reconstructing promotion-boundary prose",
        )
    )
    checks.append(
        require(
            True,
            "cli_scorecard_decision_gate_minimums_required",
            "the real OP-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if the scorecard JSON loses decision_gate_minimums, contains a boolean anchor floor, gives Phase 8 or real-money review a non-positive floor, or drops the no-BAQ-as-BEL real-money prerequisite instead of silently weakening the paper-observation floors for anchor displacement, Phase 8 promotion review, or real-money discussion",
        )
    )
    checks.append(
        require(
            True,
            "bad_current_operator_generated_at_fails_fast",
            "the real OP-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if compare_main_approaches.json carries a timezone-naive current_operator_boundary.generated_at or loses the current-operator source-freshness reference fields instead of republishing malformed current-paper provenance",
        )
    )
    checks.append(
        require(
            True,
            "false_current_operator_refresh_not_real_money_flag_fails_fast",
            "the real OP-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if compare_main_approaches.json marks current_operator_boundary.refresh_boundary_not_real_money_evidence=false or refresh_counts_as_roi_complete_evidence_by_itself=true instead of republishing weakened current-paper provenance",
        )
    )
    checks.append(
        require(
            True,
            "missing_scorecard_audit_route_fails_fast",
            "the real OP-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if current_evidence_summary.json loses scorecard_audit_route instead of silently dropping the copied gate/ranking/CI-only/timezone/no-BAQ synchronization route",
        )
    )
    checks.append(
        require(
            True,
            "missing_rebuild_validation_contract_fails_fast",
            "the real OP-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if current_evidence_summary.json loses rebuild_validation_contract or weakens its provenance-only flag instead of silently dropping or overstating the settlement-audit -> current-bridge -> bridge-validator route before quoting current totals",
        )
    )
    checks.append(
        require(
            scorecard_ranking_contract.get("rank_is_tier_first_decision_order") is True
            and scorecard_ranking_contract.get("forward_trust_is_secondary_within_tier") is True
            and scorecard_ranking_contract.get("raw_score_is_not_an_automatic_deployment_instruction") is True
            and "CD_CORE_K8 ranks ahead of OP_REFINED_K7" in str(scorecard_ranking_contract.get("known_rank_override") or "")
            and "Inherited scorecard ranking contract: rank is tier-first" in saved_md
            and "Scorecard rank-contract override: CD_CORE_K8 ranks ahead of OP_REFINED_K7" in saved_md
            and "Do not read raw Score as a promotion queue" in saved_md
            and "`forward_evidence_scorecard.json`" in saved_md,
            "scorecard_ranking_contract_inherited",
            "OP_FAMILY_DECISION.md now consumes forward_evidence_scorecard.json ranking_contract so the OP-only anchor/challenger page explains that raw OP_REFINED_K7 score is not an automatic promotion cue",
        )
    )
    checks.append(
        require(
            scorecard_ci_only_diagnostic["candidate_rule_id"] == "OP_REFINED_K7"
            and scorecard_ci_only_diagnostic["current_anchor_rule_id"] == "OP_DURABLE_K7"
            and scorecard_ci_only_diagnostic["ci_only_promotion_allowed"] is False
            and "Scorecard CI-only promotion check: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` says `ci_only_promotion_allowed=false`; OP_REFINED's positive CI lower bound is support context only, not an anchor-replacement trigger." in saved_md
            and "## Scorecard CI-Only Promotion Check" in saved_md
            and "Source: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7`" in saved_md
            and "- Current decision: Keep OP_REFINED_K7 shadow/watch only." in saved_md
            and "- CI-only promotion allowed: `false`" in saved_md
            and "smaller holdout sample than OP_DURABLE_K7, losing 2024 holdout split, lower walk-forward recurrence than OP_DURABLE_K7" in saved_md
            and "phase8 promotion review = 20+ ROI-complete candidate shadow observations plus cleaner split-aware/walk-forward support" in saved_md
            and "anchor displacement = 30+ ROI-complete same-candidate paper observations plus a cleaner split-aware forward read and equal-or-better walk-forward support" in saved_md
            and "Does not count: positive bootstrap CI lower bound by itself, hotter aggregate small-sample holdout ROI, historical replay rows, clean rebuilds, green validators." in saved_md,
            "scorecard_ci_only_diagnostic_documented",
            "OP_FAMILY_DECISION.md now source-matches the scorecard OP_REFINED CI-only diagnostic so positive CI support cannot read as OP anchor-replacement readiness",
        )
    )
    checks.append(
        require(
            scorecard_decision_gates["anchor_displacement"]["minimum_roi_complete_same_candidate_observations"] == 30
            and scorecard_decision_gates["phase8_promotion_review"]["minimum_roi_complete_settled_observations"] == 20
            and scorecard_decision_gates["real_money_discussion"]["minimum_total_settled_roi_complete_observations"] == 100
            and "## Decision-Change Gates" in saved_md
            and "These gates are loaded directly from `forward_evidence_scorecard.json` `decision_gate_minimums`." in saved_md
            and "| Anchor displacement | 30 ROI-complete same-candidate observations |" in saved_md
            and "| Phase 8 promotion review | 20 ROI-complete shadow observations |" in saved_md
            and "| Real-money discussion | 100 total ROI-complete settled paper observations |" in saved_md
            and "`forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations`" in saved_md
            and "`forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations`" in saved_md
            and "`forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi`" in saved_md
            and "Clean empty scans, open paper signals, historical replay rows, source fingerprints, green validators, or a WATCH label do not satisfy these gates." in saved_md,
            "scorecard_decision_gate_minimums_documented",
            "OP_FAMILY_DECISION.md now loads the scorecard decision_gate_minimums directly and documents the separate 30-row OP anchor-displacement floor, 20-row Phase 8 promotion-review floor, and 100-row real-money discussion floor with exact threshold-source keys",
        )
    )
    checks.append(
        require(
            "## Current OP Paper Snapshot" in saved_md
            and f"This context is inherited from `{COMPARE_JSON.name}` / `{operator_boundary['source_path']}`" in saved_md
            and f"bridge reference = `{operator_boundary['source_freshness_generated_reference_date']}` (`{operator_boundary['source_freshness_generated_reference_timezone']}`)" in saved_md
            and f"comparison = `{operator_boundary['source_freshness_staleness_comparison_source']}` / `{operator_boundary['source_freshness_staleness_comparison_date']}`" in saved_md
            and str(operator_boundary["source_freshness_read"]) in saved_md
            and f"`{operator_boundary['refresh_action_command']}` required before right-now use = `{operator_boundary['refresh_required_before_right_now_instruction_use']}`" in saved_md
            and f"settles rows / creates ROI evidence / clean-empty performance = `{operator_boundary['refresh_can_settle_open_rows_by_itself']}` / `{operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}` / `{operator_boundary['clean_empty_refresh_counts_as_forward_performance']}`" in saved_md
            and "| Operator read gate |" in saved_md
            and f"`{COMPARE_JSON.name}` `current_operator_boundary.operator_read_gate`" in saved_md
            and cma.md_cell(operator_read_gate["read"]) in saved_md
            and operator_read_gate_branch_ok
            and operator_read_gate["current_top_card_counts_as_no_target_evidence"] is False
            and operator_read_gate["current_top_card_counts_as_clean_empty_evidence"] is False
            and operator_read_gate["current_top_card_counts_as_bet_readiness_evidence"] is False
            and operator_read_gate["current_top_card_counts_as_settled_roi_evidence"] is False
            and "| Primary first-read gate |" not in saved_md
            and f"`{CURRENT_EVIDENCE_JSON.name}` `decision_gate_progress`" in saved_md
            and current_gate_progress["read"] in saved_md
            and f"gate status = `{current_gate_progress['gate_status']}`" in saved_md
            and f"| Current settled rule mix | OP_DURABLE_K7={operator_boundary['op_anchor_roi_complete_rows']}; CD_CORE_K8={operator_boundary['cd_companion_roi_complete_rows']};" in saved_md
            and (
                f"| Settlement queue state | `{operator_boundary['open_settlement_queue_state']}`; "
                f"{cma.md_cell(operator_boundary['open_settlement_context'])}; detail: "
                f"{cma.md_cell(operator_boundary['open_settlement_queue_read'])} |"
            ) in saved_md
            and "| Open settlement context |" not in saved_md
            and "Settlement queue state:" not in str(operator_boundary.get("open_settlement_queue_read") or "")
            and bool(operator_boundary["current_settled_context_is_cd_only"]) is True
            and int(operator_boundary["op_anchor_roi_complete_rows"]) == 0
            and int(operator_boundary["cd_companion_roi_complete_rows"]) == int(operator_boundary["roi_complete_primary_rows"])
            and "CD-only paper rows are not OP-anchor forward evidence" in saved_md
            and "The current operator boundary is routing/provenance context only." in saved_md
            and "not settled ROI, OP-anchor proof, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in saved_md,
            "current_operator_boundary_documented",
            "OP_FAMILY_DECISION.md carries the compare-main current-operator boundary plus current_evidence_summary.json decision_gate_progress, including structured source-freshness reference-date and staleness-comparison fields, stale-card refresh routing, wrapper-refresh non-evidence flags, the inherited operator_read_gate, the bridge-published current gate split, OP_DURABLE_K7=0 versus the current CD_CORE_K8 count, the CD-only current settled context, source-published settlement-queue state/context/detail, recommendation-state context, and no OP-anchor-proof / no-real-money caveat",
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
            "OP_FAMILY_DECISION.md now republishes compare_main_approaches.json current_operator_boundary.operator_read_gate as branch-aware routing metadata, not no-target, clean-empty, bet-readiness, settled ROI, OP-anchor proof, promotion, live-profitability, bankroll, or real-money evidence",
        )
    )
    checks.append(
        require(
            current_gate_progress.get("gate_status") == "all_uncleared"
            and current_gate_progress.get("all_gates_ready") is False
            and "Gate progress: primary first-read 6/30" in current_gate_progress.get("read", "")
            and "OP anchor same-candidate 0/30" in current_gate_progress.get("read", "")
            and "Phase 8 weakest shadow 0/20" in current_gate_progress.get("read", "")
            and "real-money discussion floor 6/100" in current_gate_progress.get("read", "")
            and f"Bridge-published current gate progress: `{CURRENT_EVIDENCE_JSON.name}` `decision_gate_progress`" in saved_md,
            "current_evidence_gate_progress_documented",
            "OP_FAMILY_DECISION.md now reads current_evidence_summary.json.decision_gate_progress directly so primary 6/30, OP-anchor same-candidate 0/30, Phase 8 0/20, and real-money 6/100 gates stay visible as uncleared routing context",
        )
    )
    checks.append(
        require(
            rebuild_validation_contract["upstream_refresh_commands"] == ofd.REQUIRED_REBUILD_REFRESH_ORDER
            and rebuild_validation_contract["prerequisite_rebuild_command"] == "python3 paper_trade_settlement_audit.py"
            and rebuild_validation_contract["rebuild_command"] == "python3 current_evidence_summary.py"
            and rebuild_validation_contract["direct_validation_command"] == "python3 validate_current_evidence_summary.py"
            and rebuild_validation_contract["requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"] is True
            and rebuild_validation_contract["requires_source_consistency_before_quoting_current_totals"] is True
            and rebuild_validation_contract["upstream_refresh_order_is_provenance_metadata_only"] is True
            and rebuild_validation_contract["not_settled_roi_or_real_money_evidence"] is True
            and "Current bridge rebuild order:" in saved_md
            and f"`{CURRENT_EVIDENCE_JSON.name}` `rebuild_validation_contract`" in saved_md
            and "python3 paper_trade_settlement_audit.py -> python3 current_evidence_summary.py -> python3 validate_current_evidence_summary.py" in saved_md
            and "before quoting `CURRENT_EVIDENCE_SUMMARY.*`" in saved_md
            and "not OP-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in saved_md,
            "current_evidence_rebuild_validation_contract_documented",
            "OP_FAMILY_DECISION.md now republishes current_evidence_summary.json.rebuild_validation_contract so source-byte changes route through settlement-audit -> current-bridge -> bridge-validator before anyone quotes current totals from the OP-family card",
        )
    )
    checks.append(
        require(
            f"`{CURRENT_EVIDENCE_JSON.name}` `scorecard_audit_route`" in saved_md
            and "| Scorecard audit route |" in saved_md
            and cma.md_cell(scorecard_audit_route["route_read"]) in saved_md
            and scorecard_audit_route["validator_command"] == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route["markdown_path"] == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route["json_path"] == "scorecard_ranking_contract_audit.json"
            and scorecard_audit_route["gate_floor_source"] == "forward_evidence_scorecard.json:decision_gate_minimums"
            and scorecard_audit_route["gate_floor_snapshot"]["anchor_displacement_min_roi_complete_settled_observations"] == 30
            and scorecard_audit_route["gate_floor_snapshot"]["phase8_promotion_review_min_roi_complete_settled_observations"] == 20
            and scorecard_audit_route["gate_floor_snapshot"]["real_money_discussion_min_total_settled_observations_with_usable_roi"] == 100
            and scorecard_audit_route["gate_floor_snapshot"]["real_money_no_baq_as_bel_required"] is True
            and scorecard_audit_route["artifacts_present"] is True
            and scorecard_audit_route["not_forward_performance_evidence"] is True
            and scorecard_audit_route["not_settled_roi_evidence"] is True
            and scorecard_audit_route["not_promotion_readiness_evidence"] is True
            and scorecard_audit_route["not_live_profitability_evidence"] is True
            and scorecard_audit_route["not_bankroll_guidance"] is True
            and scorecard_audit_route["not_real_money_evidence"] is True
            and "Report-synchronization route only; it is not OP-family evidence, forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in saved_md,
            "current_evidence_scorecard_audit_route_documented",
            "OP_FAMILY_DECISION.md now republishes current_evidence_summary.json.scorecard_audit_route so copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks point to the dedicated audit without becoming OP-family evidence, settled ROI, OP-anchor proof, promotion, live-profitability, bankroll, or real-money evidence",
        )
    )
    checks.append(
        require(
            ofd.has_timezone_aware_timestamp(operator_boundary.get("generated_at")),
            "current_operator_boundary_generated_at_is_timezone_aware",
            f"OP-family card inherits compare-main current_operator_boundary.generated_at={operator_boundary.get('generated_at')!r} as parseable timezone-aware provenance metadata only",
        )
    )
    checks.append(
        require(
            "## Source Provenance" in saved_md
            and "Exact input-byte fingerprints for this OP-family card." in saved_md
            and "they do not prove settled paper ROI, promotion readiness, live profitability, or real-money performance." in saved_md
            and source_provenance_matches_disk(saved_md),
            "source_provenance_markdown_matches_disk",
            "OP_FAMILY_DECISION.md now fingerprints compare-main logic, race-cache, Phase 7 rules, walk-forward rules, and scorecard inputs, with markdown byte counts and SHA-256 values matching current disk files",
        )
    )
    checks.append(
        require(
            df.loc["OP_DURABLE_K7", "decision"] == "KEEP AS ANCHOR"
            and bool(df.loc["OP_DURABLE_K7", "can_replace_anchor"]) is True,
            "anchor_stays_anchor",
            "OP_DURABLE_K7 still remains the anchor in the OP family card",
        )
    )
    checks.append(
        require(
            abs(float(df.loc["OP_DURABLE_K7", "holdout_roi"]) - float(durable_holdout["roi"])) < 1e-9
            and int(df.loc["OP_DURABLE_K7", "holdout_races"]) == int(durable_holdout["races"])
            and abs(float(df.loc["OP_DURABLE_K7", "holdout_ci_lower"]) - float(scorecard_df.loc["OP_DURABLE_K7", "ci_lower"])) < 1e-9,
            "durable_matches_frozen_holdout",
            "OP_DURABLE_K7 card row still matches the frozen holdout ROI, races, and scorecard CI-lower caution",
        )
    )
    checks.append(
        require(
            abs(float(df.loc["OP_REFINED_K7", "holdout_roi"]) - float(refined_holdout["roi"])) < 1e-9
            and int(df.loc["OP_REFINED_K7", "holdout_races"]) == int(refined_holdout["races"]),
            "refined_matches_frozen_holdout",
            "OP_REFINED_K7 card row still matches the frozen holdout ROI and races",
        )
    )
    checks.append(
        require(
            holdout_choice_map == {2024: "OP_REFINED_K7", 2025: "OP_REFINED_K7"},
            "switch_holdout_choices",
            "train-only OP switch still chooses OP_REFINED_K7 in both holdout years",
        )
    )
    checks.append(
        require(
            abs(float(df.loc["Train-only OP switch", "holdout_roi"]) - float(df.loc["OP_REFINED_K7", "holdout_roi"])) < 1e-9
            and int(df.loc["Train-only OP switch", "holdout_races"]) == int(df.loc["OP_REFINED_K7", "holdout_races"]),
            "switch_collapses_to_refined_on_holdout",
            "train-only OP switch still collapses to the refined OP line on the 2024-2025 holdout",
        )
    )
    checks.append(
        require(
            df.loc["OP_REFINED_K7", "decision"] == "KEEP AS WATCH / RESEARCH"
            and bool(df.loc["OP_REFINED_K7", "can_replace_anchor"]) is False
            and bool(df.loc["OP_REFINED_K7", "check_holdout_beats_anchor"]) is True
            and bool(df.loc["OP_REFINED_K7", "check_holdout_sample_matches_anchor"]) is False
            and bool(df.loc["OP_REFINED_K7", "check_holdout_all_years_positive"]) is False
            and bool(df.loc["OP_REFINED_K7", "check_wf_coverage_matches_anchor"]) is False
            and bool(df.loc["OP_REFINED_K7", "check_wf_years_match_anchor"]) is True,
            "refined_replacement_bar",
            "OP_REFINED_K7 still fails the conservative replacement bar on sample size, losing holdout year, and WF coverage",
        )
    )
    checks.append(
        require(
            df.loc["Train-only OP switch", "decision"] == "KEEP AS WATCH / RESEARCH"
            and bool(df.loc["Train-only OP switch", "can_replace_anchor"]) is False
            and bool(df.loc["Train-only OP switch", "check_holdout_beats_anchor"]) is True
            and bool(df.loc["Train-only OP switch", "check_holdout_sample_matches_anchor"]) is False
            and bool(df.loc["Train-only OP switch", "check_holdout_all_years_positive"]) is False
            and bool(df.loc["Train-only OP switch", "check_wf_coverage_matches_anchor"]) is False
            and bool(df.loc["Train-only OP switch", "check_wf_years_match_anchor"]) is True,
            "switch_replacement_bar",
            "Train-only OP switch still fails the same conservative replacement bar and does not earn promotion",
        )
    )
    checks.append(
        require(
            abs(float(df.loc["OP_DURABLE_K7", "holdout_2024_roi"]) - (-47.41)) < 1e-9
            and int(df.loc["OP_DURABLE_K7", "holdout_2024_races"]) == 68
            and abs(float(df.loc["OP_DURABLE_K7", "holdout_2025_roi"]) - 124.61) < 1e-9
            and int(df.loc["OP_DURABLE_K7", "holdout_2025_races"]) == 47,
            "durable_holdout_year_split",
            "OP_DURABLE_K7 still carries the expected 2024 loss / 2025 rebound holdout split on the larger sample",
        )
    )
    checks.append(
        require(
            abs(float(df.loc["OP_REFINED_K7", "holdout_2024_roi"]) - (-25.47)) < 1e-9
            and int(df.loc["OP_REFINED_K7", "holdout_2024_races"]) == 33
            and abs(float(df.loc["OP_REFINED_K7", "holdout_2025_roi"]) - 210.02) < 1e-9
            and int(df.loc["OP_REFINED_K7", "holdout_2025_races"]) == 16,
            "refined_holdout_year_split",
            "OP_REFINED_K7 still shows the smaller-sample losing-2024 / hot-2025 split that keeps it from replacing the anchor",
        )
    )
    checks.append(
        require(
            "This note is intentionally locked to the frozen 2024-2025 holdout standard for its primary comparison, so a prettier number from some other window does not quietly rewrite the current OP answer." in saved_md
            and f"`valid_evidence_scope={ofd.VALID_EVIDENCE_SCOPE}`" in saved_md
            and "This top table is split-aware on purpose" in saved_md
            and "Fixed OP rows below use frozen replays on the walk-forward test years as secondary context; only the train-only OP switch row uses actual train-only walk-forward evidence." in saved_md
            and "For the fixed rows, that secondary context is replay context rather than extra train-only validation." in saved_md
            and "Inherited scorecard ranking contract: rank is tier-first" in saved_md
            and "The anchor itself also still needs caution: `OP_DURABLE_K7` remains the safest current default, but its bootstrap 95% CI lower bound is still `-3.40%`." in saved_md
            and "| Method | Type | Holdout ROI | Holdout Races | 2024 ROI / N | 2025 ROI / N | Holdout Years+ | Worst Holdout Year | Secondary ROI | Secondary Races | Secondary Years+ | Secondary Basis | Decision |" in saved_md
            and "| OP_DURABLE_K7 | fixed anchor | +22.90% | 115 | -47.41% / 68 | +124.61% / 47 |" in saved_md
            and "| Train-only OP switch | dynamic challenger | +51.43% | 49 | -25.47% / 33 | +210.02% / 16 |" in saved_md
            and "| OP_REFINED_K7 | fixed challenger | +51.43% | 49 | -25.47% / 33 | +210.02% / 16 |" in saved_md
            and "## 2024-2025 Holdout Split" in saved_md
            and "| OP_DURABLE_K7 | -47.41% (68) | +124.61% (47) |" in saved_md
            and "| OP_REFINED_K7 | -25.47% (33) | +210.02% (16) |" in saved_md
            and "| Train-only OP switch | -25.47% (33) | +210.02% (16) |" in saved_md
            and "For fixed rules here, that secondary context is a frozen replay on the walk-forward test years; for the train-only switch it is actual train-only walk-forward. Treat the fixed-rule secondary columns as replay context rather than extra train-only validation. The bar is therefore conservative, not perfectly apples-to-apples." in saved_md
            and "- **Keep `OP_DURABLE_K7` as the current paper anchor.** It has 115 holdout races and 416 secondary-context races (`frozen replay on walk-forward test years`, so replay context rather than extra train-only validation)" in saved_md
            and "live-paper anchor" not in saved_md
            and "- **Treat the train-only OP switch as research context.** It is the only row here with true train-only walk-forward secondary evidence" in saved_md
            and "- **Anchor caution:** that does not make it a statistically clean slam dunk; the bootstrap 95% CI lower bound for `OP_DURABLE_K7` is still `-3.40%`." in saved_md,
            "holdout_split_section_present",
            "OP_FAMILY_DECISION.md now carries the explicit frozen 2024-2025 holdout lock, the holdout split, secondary-basis honesty, explicit replay-context caution for fixed-rule secondary columns, current-paper anchor wording, and the anchor CI caution in both the framing and the implications section",
        )
    )
    checks.append(
        require(
            int(df.loc["OP_DURABLE_K7", "holdout_races"]) > int(df.loc["OP_REFINED_K7", "holdout_races"])
            and int(df.loc["OP_DURABLE_K7", "wf_races"]) > int(df.loc["OP_REFINED_K7", "wf_races"]),
            "anchor_has_larger_forward_sample",
            "OP_DURABLE_K7 still carries the larger holdout and walk-forward samples inside the OP family",
        )
    )
    checks.append(
        require(
            abs(float(df.loc["OP_DURABLE_K7", "holdout_roi"]) - float(compare_df.loc["op_durable_only", "holdout_roi"])) < 1e-9
            and abs(float(df.loc["OP_REFINED_K7", "holdout_roi"]) - float(compare_df.loc["op_refined_only", "holdout_roi"])) < 1e-9
            and str(df.loc["OP_DURABLE_K7", "secondary_basis"]) == str(compare_df.loc["op_durable_only", "secondary_basis"])
            and str(df.loc["OP_REFINED_K7", "secondary_basis"]) == str(compare_df.loc["op_refined_only", "secondary_basis"])
            and str(df.loc["Train-only OP switch", "secondary_basis"]) == str(compare_df.loc["op_train_switch", "secondary_basis"]),
            "matches_compare_main_rows",
            "OP family card still agrees with the corresponding OP rows from compare_main_approaches.csv, including secondary-basis labeling",
        )
    )

    suite_read = (
        f"OP-family card stays locked to the frozen 2024-2025 holdout standard with valid_evidence_scope={ofd.VALID_EVIDENCE_SCOPE}; "
        f"Anchor {str(df.loc['OP_DURABLE_K7', 'decision'])} with "
        f"{int(df.loc['OP_DURABLE_K7', 'holdout_races'])} holdout races and "
        f"{int(df.loc['OP_DURABLE_K7', 'wf_races'])} secondary-context races ({str(df.loc['OP_DURABLE_K7', 'secondary_basis'])}, replay context rather than extra train-only validation); CI low={float(df.loc['OP_DURABLE_K7', 'holdout_ci_lower']):+.2f}%; "
        f"top table now carries the split directly with 2024={float(df.loc['OP_DURABLE_K7', 'holdout_2024_roi']):+.2f}% on {int(df.loc['OP_DURABLE_K7', 'holdout_2024_races'])} vs "
        f"2025={float(df.loc['OP_DURABLE_K7', 'holdout_2025_roi']):+.2f}% on {int(df.loc['OP_DURABLE_K7', 'holdout_2025_races'])}; "
        "OP_REFINED_K7 and the train-only OP switch stay KEEP AS WATCH / RESEARCH; "
        f"scorecard ranking contract inherited=tier-first, raw Score non-promotional ({scorecard_ranking_contract['known_rank_override']}); "
        "scorecard CI-only diagnostic inherited from forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7 keeps ci_only_promotion_allowed=false so positive OP_REFINED CI support stays out of OP anchor-replacement readiness; "
        "scorecard decision gates inherited directly from forward_evidence_scorecard.json decision_gate_minimums (anchor_displacement=30 same-candidate settled observations; phase8_promotion_review=20 shadow observations; real_money_discussion=100 total settled ROI-complete observations); "
        "source provenance fingerprints compare-main logic/JSON, race-cache, Phase 7 rules, walk-forward rules, and scorecard inputs as reproducibility metadata only; "
        f"current operator boundary inherited from compare-main JSON names stale-card refresh route={operator_boundary['refresh_action_command']} with source-freshness bridge reference={operator_boundary['source_freshness_generated_reference_date']} ({operator_boundary['source_freshness_generated_reference_timezone']}) and staleness comparison={operator_boundary['source_freshness_staleness_comparison_source']}:{operator_boundary['source_freshness_staleness_comparison_date']}, wrapper-can-settle-rows={operator_boundary['refresh_can_settle_open_rows_by_itself']}, wrapper-counts-as-ROI-evidence={operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}, clean-empty-forward-performance={operator_boundary['clean_empty_refresh_counts_as_forward_performance']}, {operator_boundary['roi_complete_primary_rows']}/{operator_boundary['first_read_threshold']} primary ROI-complete rows, current settled rule mix OP_DURABLE_K7={operator_boundary['op_anchor_roi_complete_rows']} / CD_CORE_K8={operator_boundary['cd_companion_roi_complete_rows']} with CD-only context={operator_boundary['current_settled_context_is_cd_only']}, settlement-queue state={operator_boundary['open_settlement_queue_state']} / context={operator_boundary['open_settlement_context']}, recommendation-state context={operator_boundary['recommendation_context_read']}, and the operator route as routing/provenance only rather than settled ROI, OP-anchor proof, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence; "
        f"operator read gate inherited from compare-main says {operator_read_gate['read']} with gate_status={operator_read_gate['gate_status']} and recommended_command={operator_read_gate['recommended_command']}; "
        f"bridge-published gate progress from current_evidence_summary.json.decision_gate_progress says {current_gate_progress['read']} with gate_status={current_gate_progress['gate_status']} and all_gates_ready={current_gate_progress['all_gates_ready']}; "
        f"current_evidence_summary.json.rebuild_validation_contract routes source-byte changes through {' -> '.join(rebuild_validation_contract['upstream_refresh_commands'])} before quoting CURRENT_EVIDENCE_SUMMARY.* as provenance/rebuild metadata only, not OP-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence; "
        f"current_evidence_summary.json.scorecard_audit_route points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to {scorecard_audit_route['markdown_path']} / {scorecard_audit_route['json_path']} plus {scorecard_audit_route['validator_command']} as report-synchronization metadata only, not OP-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence; "
        f"copied current-operator generated_at={operator_boundary['generated_at']} stays parseable timezone-aware provenance metadata only; "
        f"holdout switch choices {', '.join(f'{year}={rule}' for year, rule in holdout_choice_map.items())}; "
        "saved CSV, saved markdown, and real CLI stdout stay pinned to the same OP-family decision render; "
        "required cache, Phase 7 anchor, walk-forward candidate rows, scorecard rows, scorecard ranking-contract JSON, and scorecard decision-gate JSON now fail fast when they drift"
        "; bad scorecard-gate and current-operator provenance fixtures now prove no output directory or partial OP-family artifact is created before failure"
    )

    payload = {
        "suite_status": "pass",
        "artifact": {
            "saved_csv": OP_CSV.name,
            "saved_markdown": OP_MD.name,
            "status": "pass",
            "rows": int(len(saved_df)),
        },
        "valid_evidence_scope": ofd.VALID_EVIDENCE_SCOPE,
        "scorecard_ranking_contract": scorecard_ranking_contract,
        "scorecard_ranking_contract_source": SCORECARD_JSON.name,
        "scorecard_decision_gate_minimums": scorecard_decision_gates,
        "scorecard_decision_gate_minimums_source": SCORECARD_JSON.name,
        "scorecard_ci_only_diagnostic": scorecard_ci_only_diagnostic,
        "scorecard_ci_only_diagnostic_source": f"{SCORECARD_JSON.name}:{ofd.OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}",
        "current_operator_read_gate": operator_read_gate,
        "current_operator_boundary": {
            "source": COMPARE_JSON.name,
            "generated_at": operator_boundary["generated_at"],
            "source_freshness_generated_reference_date": operator_boundary["source_freshness_generated_reference_date"],
            "source_freshness_generated_reference_timezone": operator_boundary["source_freshness_generated_reference_timezone"],
            "source_freshness_staleness_comparison_source": operator_boundary["source_freshness_staleness_comparison_source"],
            "source_freshness_staleness_comparison_date": operator_boundary["source_freshness_staleness_comparison_date"],
            "source_freshness_read": operator_boundary["source_freshness_read"],
            "refresh_action_command": operator_boundary["refresh_action_command"],
            "refresh_can_settle_open_rows_by_itself": operator_boundary["refresh_can_settle_open_rows_by_itself"],
            "refresh_counts_as_roi_complete_evidence_by_itself": operator_boundary["refresh_counts_as_roi_complete_evidence_by_itself"],
            "clean_empty_refresh_counts_as_forward_performance": operator_boundary["clean_empty_refresh_counts_as_forward_performance"],
            "roi_complete_primary_rows": operator_boundary["roi_complete_primary_rows"],
            "first_read_threshold": operator_boundary["first_read_threshold"],
            "op_anchor_roi_complete_rows": operator_boundary["op_anchor_roi_complete_rows"],
            "cd_companion_roi_complete_rows": operator_boundary["cd_companion_roi_complete_rows"],
            "current_settled_context_is_cd_only": operator_boundary["current_settled_context_is_cd_only"],
            "open_settlement_summary": operator_boundary["open_settlement_summary"],
            "open_settlement_context": operator_boundary["open_settlement_context"],
            "open_settlement_queue_state": operator_boundary["open_settlement_queue_state"],
            "open_settlement_queue_read": operator_boundary["open_settlement_queue_read"],
            "recommendation_context_read": operator_boundary["recommendation_context_read"],
        },
        "current_evidence_gate_progress_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            "source_path": "decision_gate_progress",
            "read": current_gate_progress["read"],
            "gate_status": current_gate_progress["gate_status"],
            "all_gates_ready": current_gate_progress["all_gates_ready"],
            "not_forward_performance_evidence": current_gate_progress["not_forward_performance_evidence"],
            "not_promotion_readiness_evidence": current_gate_progress["not_promotion_readiness_evidence"],
            "not_live_profitability_evidence": current_gate_progress["not_live_profitability_evidence"],
            "not_real_money_evidence": current_gate_progress["not_real_money_evidence"],
        },
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
            "read": scorecard_audit_route["route_read"],
            "artifacts_present": scorecard_audit_route["artifacts_present"],
            "not_forward_performance_evidence": scorecard_audit_route["not_forward_performance_evidence"],
            "not_settled_roi_evidence": scorecard_audit_route["not_settled_roi_evidence"],
            "not_promotion_readiness_evidence": scorecard_audit_route["not_promotion_readiness_evidence"],
            "not_live_profitability_evidence": scorecard_audit_route["not_live_profitability_evidence"],
            "not_bankroll_guidance": scorecard_audit_route["not_bankroll_guidance"],
            "not_real_money_evidence": scorecard_audit_route["not_real_money_evidence"],
        },
        "scratch": scratch_meta,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "summary": {
            "anchor_holdout_races": int(df.loc["OP_DURABLE_K7", "holdout_races"]),
            "anchor_wf_races": int(df.loc["OP_DURABLE_K7", "wf_races"]),
            "refined_holdout_races": int(df.loc["OP_REFINED_K7", "holdout_races"]),
            "switch_holdout_choice_map": holdout_choice_map,
            "anchor_decision": str(df.loc["OP_DURABLE_K7", "decision"]),
            "suite_read": suite_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }

    lines = [
        "# OP Family Decision Validation",
        "",
        "This report validates the OP-family card directly, including the saved CSV and markdown artifacts, the real CLI stdout report and save notices, the inherited scorecard ranking contract, the scorecard-sourced decision-change gates, and the fail-fast source contract around the cache, Phase 7 anchor rule, walk-forward OP candidate rows, scorecard rows, and scorecard JSON.",
        "",
        "## Artifact Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Saved artifacts: `{OP_CSV.name}`, `{OP_MD.name}`",
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
            f"- Source scope line: `valid_evidence_scope={ofd.VALID_EVIDENCE_SCOPE}`",
            f"- Anchor decision: {df.loc['OP_DURABLE_K7', 'decision']}",
            f"- OP_DURABLE_K7 holdout races: {int(df.loc['OP_DURABLE_K7', 'holdout_races'])}",
            f"- OP_DURABLE_K7 secondary-context races: {int(df.loc['OP_DURABLE_K7', 'wf_races'])} ({df.loc['OP_DURABLE_K7', 'secondary_basis']})",
            f"- OP_REFINED_K7 holdout races: {int(df.loc['OP_REFINED_K7', 'holdout_races'])}",
            f"- Scorecard ranking contract: tier-first={scorecard_ranking_contract['rank_is_tier_first_decision_order']}; raw-score-promotional={not scorecard_ranking_contract['raw_score_is_not_an_automatic_deployment_instruction']}; {scorecard_ranking_contract['known_rank_override']}",
            f"- Scorecard decision gates: anchor_displacement={scorecard_decision_gates['anchor_displacement']['minimum_roi_complete_same_candidate_observations']} same-candidate settled rows; phase8_promotion_review={scorecard_decision_gates['phase8_promotion_review']['minimum_roi_complete_settled_observations']} shadow rows; real_money_discussion={scorecard_decision_gates['real_money_discussion']['minimum_total_settled_roi_complete_observations']} total settled ROI-complete rows",
            f"- Current evidence gate progress: {current_gate_progress['read']} gate_status={current_gate_progress['gate_status']}; all_gates_ready={current_gate_progress['all_gates_ready']}; this is routing context only, not settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- Current bridge rebuild order: current_evidence_summary.json.rebuild_validation_contract routes source-byte changes through {' -> '.join(rebuild_validation_contract['upstream_refresh_commands'])} before quoting CURRENT_EVIDENCE_SUMMARY.*; this is provenance/rebuild metadata only, not OP-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- Scorecard audit route: current_evidence_summary.json.scorecard_audit_route points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to {scorecard_audit_route['markdown_path']} / {scorecard_audit_route['json_path']} plus {scorecard_audit_route['validator_command']}; this is report-synchronization metadata only, not OP-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- Current operator boundary: generated_at={operator_boundary['generated_at']}; source-freshness bridge reference={operator_boundary['source_freshness_generated_reference_date']} ({operator_boundary['source_freshness_generated_reference_timezone']}), staleness comparison={operator_boundary['source_freshness_staleness_comparison_source']}:{operator_boundary['source_freshness_staleness_comparison_date']}; refresh route={operator_boundary['refresh_action_command']}, wrapper-can-settle-rows={operator_boundary['refresh_can_settle_open_rows_by_itself']}, wrapper-counts-as-ROI-evidence={operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}, clean-empty-forward-performance={operator_boundary['clean_empty_refresh_counts_as_forward_performance']}; {operator_boundary['roi_complete_primary_rows']}/{operator_boundary['first_read_threshold']} primary ROI-complete rows; current settled rule mix OP_DURABLE_K7={operator_boundary['op_anchor_roi_complete_rows']} / CD_CORE_K8={operator_boundary['cd_companion_roi_complete_rows']}; settlement-queue state={operator_boundary['open_settlement_queue_state']} / context={operator_boundary['open_settlement_context']}; recommendation-state context={operator_boundary['recommendation_context_read']}; this is routing/provenance only, not settled ROI, OP-anchor proof, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- OP_DURABLE_K7 holdout split: 2024 {float(df.loc['OP_DURABLE_K7', 'holdout_2024_roi']):+.2f}% on {int(df.loc['OP_DURABLE_K7', 'holdout_2024_races'])}, 2025 {float(df.loc['OP_DURABLE_K7', 'holdout_2025_roi']):+.2f}% on {int(df.loc['OP_DURABLE_K7', 'holdout_2025_races'])}",
            f"- OP_REFINED_K7 holdout split: 2024 {float(df.loc['OP_REFINED_K7', 'holdout_2024_roi']):+.2f}% on {int(df.loc['OP_REFINED_K7', 'holdout_2024_races'])}, 2025 {float(df.loc['OP_REFINED_K7', 'holdout_2025_roi']):+.2f}% on {int(df.loc['OP_REFINED_K7', 'holdout_2025_races'])}",
            f"- Train-only OP switch holdout choices: {', '.join(f'{year}={rule}' for year, rule in holdout_choice_map.items())}",
            "",
            "## Bottom Line",
            "",
            "- Green here means the OP-family card is still pinned to the frozen 2024-2025 holdout standard, the saved CSV/markdown surfaces still rebuild cleanly from source, and `OP_DURABLE_K7` still survives the conservative replacement bar as the safest current anchor.",
            "- It does not mean `OP_REFINED_K7` or the train-only switch discovered enough new forward evidence to earn promotion.",
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
