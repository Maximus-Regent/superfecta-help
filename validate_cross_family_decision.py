#!/usr/bin/env python3
"""
Validation for the cross-family decision card.

Purpose:
- keep the active shortlist artifact reproducible
- pin the saved CSV / markdown surfaces against a fresh rebuild
- pin the real CLI stdout report plus save notices
- pin the current anchor / paper / watch ordering across OP and CD, plus the explicit near-promotion vs observation-only shadow split
- catch drift where small-sample or weak-coverage challengers get promoted too easily
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

import cross_family_decision_card as cf

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "out" / "status_validation" / "cross_family_decision"
OUT_MD = OUT_DIR / "cross_family_decision_validation.md"
OUT_JSON = OUT_DIR / "cross_family_decision_validation.json"
TMP_PARENT = OUT_DIR / "_tmp"
REBUILD_COMMAND = "python3 validate_cross_family_decision.py"
CROSS_SCRIPT = BASE / "cross_family_decision_card.py"
CROSS_CSV = BASE / "cross_family_decision_card.csv"
CROSS_MD = BASE / "CROSS_FAMILY_DECISION.md"
SCORECARD_CSV = BASE / "forward_evidence_scorecard.csv"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
FROZEN_EVAL = BASE / "frozen_portfolio_eval_summary.csv"
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
        raise AssertionError(f"rebuilt cross-family frame is missing saved columns {missing_cols}")
    rebuilt = rebuilt[saved.columns]
    assert_frame_equal(
        normalize_frame(saved, "rule_id"),
        normalize_frame(rebuilt, "rule_id"),
        check_dtype=False,
        check_exact=False,
        atol=1e-9,
        rtol=0,
    )


def build_expected_cli_stdout(report_text: str, csv_name: str = "cross_family_decision_card.csv", md_name: str = "CROSS_FAMILY_DECISION.md") -> str:
    return report_text + f"Saved: {csv_name}\nSaved: {md_name}\n"


def frozen_rule_slice(rule_id: str, slice_name: str) -> pd.Series:
    df = pd.read_csv(FROZEN_EVAL)
    match = df[(df["level"] == "rule") & (df["name"] == rule_id) & (df["slice"] == slice_name)]
    if match.empty:
        raise AssertionError(f"Missing frozen rule slice for {rule_id} / {slice_name}")
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
    expected = cf.source_file_fingerprints()
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

    saved_df = pd.read_csv(CROSS_CSV)
    rebuilt_df = cf.build_dataframe()
    compare_like_saved(saved_df, rebuilt_df)
    saved_md = CROSS_MD.read_text(encoding="utf-8")
    rebuilt_md = cf.build_markdown(rebuilt_df)
    if not rebuilt_md.endswith("\n"):
        rebuilt_md += "\n"

    df = rebuilt_df.set_index("rule_id")
    score_df = pd.read_csv(SCORECARD_CSV).set_index("rule_id")
    scorecard_ranking_contract = cf.load_scorecard_ranking_contract(SCORECARD_JSON)
    scorecard_decision_gates = cf.load_scorecard_decision_gate_minimums(SCORECARD_JSON)
    scorecard_ci_only_diagnostic = cf.load_scorecard_ci_only_diagnostic(SCORECARD_JSON)
    operator_boundary = cf.load_current_operator_boundary(COMPARE_JSON)
    current_gate_progress = cf.load_current_gate_progress(CURRENT_EVIDENCE_JSON)
    scorecard_audit_route = cf.load_scorecard_audit_route(CURRENT_EVIDENCE_JSON)
    rebuild_validation_contract = cf.load_rebuild_validation_contract(CURRENT_EVIDENCE_JSON)
    rebuild_order_commands = rebuild_validation_contract["upstream_refresh_commands"]
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

    checks: list[dict[str, Any]] = []
    checks.append(
        require(
            saved_md == rebuilt_md,
            "markdown_matches_rebuild",
            "CROSS_FAMILY_DECISION.md still matches a fresh rebuild from cross_family_decision_card.py",
        )
    )
    checks.append(
        require(
            "holdout_2024_races" in saved_df.columns and "holdout_2025_races" in saved_df.columns,
            "csv_year_count_columns_present",
            "cross_family_decision_card.csv now carries the year-specific holdout race-count columns alongside the year ROIs",
        )
    )
    checks.append(
        require(
            "shadow_rank" in saved_df.columns and "promotion_blocker" in saved_df.columns,
            "csv_shadow_columns_present",
            "cross_family_decision_card.csv now carries explicit shadow ordering plus per-rule promotion blockers",
        )
    )

    with tempfile.TemporaryDirectory(prefix="cross_family_cli_", dir=tmp_parent) as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        pinned_dir = tmpdir / "pinned_out"
        pinned_csv = pinned_dir / "cross_family_custom.csv"
        pinned_md = pinned_dir / "CROSS_FAMILY_CUSTOM.md"
        alt_scorecard_csv = tmpdir / "alt_forward_scorecard.csv"
        alt_scorecard_json = tmpdir / "alt_forward_scorecard.json"
        alt_frozen_eval_csv = tmpdir / "alt_frozen_eval_summary.csv"
        alt_compare_json = tmpdir / "alt_compare_main_approaches.json"
        missing_shortlist_scorecard_csv = tmpdir / "missing_op_refined_scorecard.csv"
        missing_watch_scorecard_csv = tmpdir / "missing_kee_scorecard.csv"
        missing_frozen_eval_csv = tmpdir / "missing_cd_2025_frozen_eval.csv"
        bad_scorecard_json = tmpdir / "bad_forward_scorecard.json"
        missing_decision_gate_json = tmpdir / "missing_decision_gate_scorecard.json"
        malformed_decision_gate_json = tmpdir / "malformed_decision_gate_scorecard.json"
        nonpositive_phase8_gate_json = tmpdir / "nonpositive_phase8_gate_scorecard.json"
        nonpositive_real_money_gate_json = tmpdir / "nonpositive_real_money_gate_scorecard.json"
        missing_no_baq_gate_json = tmpdir / "missing_no_baq_gate_scorecard.json"
        missing_operator_boundary_json = tmpdir / "missing_operator_boundary_compare_main.json"
        missing_scorecard_audit_route_json = tmpdir / "missing_scorecard_audit_route_current_evidence.json"
        missing_rebuild_validation_contract_json = tmpdir / "missing_rebuild_validation_contract_current_evidence.json"
        weakened_rebuild_validation_contract_json = tmpdir / "weakened_rebuild_validation_contract_current_evidence.json"
        bad_operator_generated_at_json = tmpdir / "bad_operator_generated_at_compare_main.json"
        missing_source_freshness_reference_json = tmpdir / "missing_source_freshness_reference_compare_main.json"
        false_refresh_boundary_flag_json = tmpdir / "false_refresh_boundary_flag_compare_main.json"
        false_refresh_accounting_flag_json = tmpdir / "false_refresh_accounting_flag_compare_main.json"
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
        missing_rebuild_output_dir = tmpdir / "missing_rebuild_nested_output" / "artifacts"
        missing_rebuild_should_not_write_csv = missing_rebuild_output_dir / "missing_rebuild_should_not_write.csv"
        missing_rebuild_should_not_write_md = missing_rebuild_output_dir / "missing_rebuild_should_not_write.md"
        weakened_rebuild_output_dir = tmpdir / "weakened_rebuild_nested_output" / "artifacts"
        weakened_rebuild_should_not_write_csv = weakened_rebuild_output_dir / "weakened_rebuild_should_not_write.csv"
        weakened_rebuild_should_not_write_md = weakened_rebuild_output_dir / "weakened_rebuild_should_not_write.md"
        bad_operator_output_dir = tmpdir / "bad_operator_nested_output" / "artifacts"
        bad_operator_should_not_write_csv = bad_operator_output_dir / "bad_operator_should_not_write.csv"
        bad_operator_should_not_write_md = bad_operator_output_dir / "bad_operator_should_not_write.md"
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
        for src in [
            CROSS_SCRIPT,
            SCORECARD_CSV,
            SCORECARD_JSON,
            FROZEN_EVAL,
            COMPARE_JSON,
            CURRENT_EVIDENCE_JSON,
            SCORECARD_AUDIT_MD,
            SCORECARD_AUDIT_JSON,
        ]:
            shutil.copy2(src, tmpdir / src.name)
        shutil.copy2(SCORECARD_CSV, alt_scorecard_csv)
        shutil.copy2(SCORECARD_JSON, alt_scorecard_json)
        shutil.copy2(FROZEN_EVAL, alt_frozen_eval_csv)
        shutil.copy2(COMPARE_JSON, alt_compare_json)
        cli_result = subprocess.run(
            [sys.executable, CROSS_SCRIPT.name],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        cli_csv = pd.read_csv(tmpdir / CROSS_CSV.name)
        compare_like_saved(saved_df, cli_csv)
        cli_report_text = (tmpdir / CROSS_MD.name).read_text(encoding="utf-8")
        if cli_report_text != rebuilt_md:
            raise AssertionError("CLI-generated CROSS_FAMILY_DECISION.md drifted from a fresh rebuild")
        expected_cli_stdout = build_expected_cli_stdout(cli_report_text)
        if cli_result.stdout != expected_cli_stdout:
            raise AssertionError("cross_family_decision_card.py CLI stdout no longer matches its generated report plus save notices")

        pinned_result = subprocess.run(
            [
                sys.executable,
                CROSS_SCRIPT.name,
                "--scorecard-csv",
                str(alt_scorecard_csv),
                "--scorecard-json",
                str(alt_scorecard_json),
                "--frozen-eval-csv",
                str(alt_frozen_eval_csv),
                "--compare-main-json",
                str(alt_compare_json),
                "--current-evidence-json",
                str(tmpdir / CURRENT_EVIDENCE_JSON.name),
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
        pinned_rebuilt_md = cf.build_markdown(
            cf.build_dataframe(scorecard_path=alt_scorecard_csv, frozen_eval_path=alt_frozen_eval_csv),
            scorecard_csv_name=alt_scorecard_csv.name,
            scorecard_json_name=alt_scorecard_json.name,
            frozen_eval_csv_name=alt_frozen_eval_csv.name,
            compare_json_name=alt_compare_json.name,
            csv_output_name=pinned_csv.name,
            md_output_name=pinned_md.name,
            scorecard_path=alt_scorecard_csv,
            scorecard_json_path=alt_scorecard_json,
            compare_json_path=alt_compare_json,
            current_evidence_json_path=tmpdir / CURRENT_EVIDENCE_JSON.name,
            source_paths={
                "forward_evidence_scorecard_csv": alt_scorecard_csv,
                "forward_evidence_scorecard_json": alt_scorecard_json,
                "frozen_portfolio_eval": alt_frozen_eval_csv,
                "compare_main_approaches_json": alt_compare_json,
                "current_evidence_summary": tmpdir / CURRENT_EVIDENCE_JSON.name,
            },
        )
        if not pinned_rebuilt_md.endswith("\n"):
            pinned_rebuilt_md += "\n"
        if pinned_report_text != pinned_rebuilt_md:
            raise AssertionError("Pinned/custom-output CROSS_FAMILY_DECISION.md drifted from a fresh rebuild")
        expected_pinned_stdout = build_expected_cli_stdout(pinned_report_text, csv_name=pinned_csv.name, md_name=pinned_md.name)
        if pinned_result.stdout != expected_pinned_stdout:
            raise AssertionError("Pinned/custom-output cross_family_decision_card.py CLI stdout no longer matches its generated report plus save notices")

        missing_shortlist_df = pd.read_csv(alt_scorecard_csv)
        missing_shortlist_df = missing_shortlist_df[missing_shortlist_df["rule_id"] != "OP_REFINED_K7"].copy()
        missing_shortlist_df.to_csv(missing_shortlist_scorecard_csv, index=False)
        missing_shortlist_result = subprocess.run(
            [sys.executable, CROSS_SCRIPT.name, "--scorecard-csv", str(missing_shortlist_scorecard_csv)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_shortlist_result.returncode == 0:
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted a scorecard missing OP_REFINED_K7")
        missing_shortlist_text = f"{missing_shortlist_result.stdout}\n{missing_shortlist_result.stderr}"
        if "missing required scorecard rule rows: OP_REFINED_K7" not in missing_shortlist_text:
            raise AssertionError("shortlist scorecard failure no longer explains that OP_REFINED_K7 is required for the cross-family card")

        missing_watch_df = pd.read_csv(alt_scorecard_csv)
        missing_watch_df = missing_watch_df[missing_watch_df["rule_id"] != "KEE_K9"].copy()
        missing_watch_df.to_csv(missing_watch_scorecard_csv, index=False)
        missing_watch_result = subprocess.run(
            [sys.executable, CROSS_SCRIPT.name, "--scorecard-csv", str(missing_watch_scorecard_csv)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_watch_result.returncode == 0:
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted a scorecard missing KEE_K9")
        missing_watch_text = f"{missing_watch_result.stdout}\n{missing_watch_result.stderr}"
        if "missing required scorecard rule rows: KEE_K9" not in missing_watch_text:
            raise AssertionError("watch-context failure no longer explains that KEE_K9 is required for the cross-family card's observation-only section")

        missing_frozen_df = pd.read_csv(alt_frozen_eval_csv)
        missing_frozen_df = missing_frozen_df[
            ~((missing_frozen_df["level"] == "rule") & (missing_frozen_df["name"] == "CD_CORE_K8") & (missing_frozen_df["slice"] == "year_2025"))
        ].copy()
        missing_frozen_df.to_csv(missing_frozen_eval_csv, index=False)
        missing_frozen_result = subprocess.run(
            [sys.executable, CROSS_SCRIPT.name, "--frozen-eval-csv", str(missing_frozen_eval_csv)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_frozen_result.returncode == 0:
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted frozen eval data missing CD_CORE_K8/year_2025")
        missing_frozen_text = f"{missing_frozen_result.stdout}\n{missing_frozen_result.stderr}"
        if "missing required frozen rule rows: CD_CORE_K8/year_2025" not in missing_frozen_text:
            raise AssertionError("frozen-eval failure no longer explains that CD_CORE_K8/year_2025 is required for the cross-family card")

        bad_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        bad_payload.pop("ranking_contract", None)
        bad_scorecard_json.write_text(json.dumps(bad_payload, indent=2) + "\n", encoding="utf-8")
        bad_json_result = subprocess.run(
            [sys.executable, CROSS_SCRIPT.name, "--scorecard-json", str(bad_scorecard_json)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if bad_json_result.returncode == 0:
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted a scorecard JSON missing ranking_contract")
        bad_json_text = f"{bad_json_result.stdout}\n{bad_json_result.stderr}"
        if "missing ranking_contract" not in bad_json_text:
            raise AssertionError("scorecard JSON failure no longer explains that ranking_contract is required for the cross-family card")

        missing_gate_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        missing_gate_payload.pop("decision_gate_minimums", None)
        missing_decision_gate_json.write_text(json.dumps(missing_gate_payload, indent=2) + "\n", encoding="utf-8")
        missing_gate_result = subprocess.run(
            [
                sys.executable,
                CROSS_SCRIPT.name,
                "--scorecard-json",
                str(missing_decision_gate_json),
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
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted a scorecard JSON missing decision_gate_minimums")
        missing_gate_text = f"{missing_gate_result.stdout}\n{missing_gate_result.stderr}"
        if "missing decision_gate_minimums" not in missing_gate_text:
            raise AssertionError("scorecard JSON failure no longer explains that decision_gate_minimums is required for the cross-family card")
        if missing_gate_output_dir.exists() or missing_gate_should_not_write_csv.exists() or missing_gate_should_not_write_md.exists():
            raise AssertionError("scorecard JSON decision-gate failure created output directories or wrote partial cross-family artifacts before failing")

        malformed_gate_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        malformed_gate_payload["decision_gate_minimums"]["anchor_displacement"][
            "min_roi_complete_settled_observations"
        ] = True
        malformed_decision_gate_json.write_text(json.dumps(malformed_gate_payload, indent=2) + "\n", encoding="utf-8")
        malformed_gate_result = subprocess.run(
            [
                sys.executable,
                CROSS_SCRIPT.name,
                "--scorecard-json",
                str(malformed_decision_gate_json),
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
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted a boolean anchor-displacement gate floor")
        malformed_gate_text = f"{malformed_gate_result.stdout}\n{malformed_gate_result.stderr}"
        if "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations must be a positive non-boolean integer" not in malformed_gate_text:
            raise AssertionError("scorecard JSON failure no longer explains that boolean gate floors are malformed")
        if malformed_gate_output_dir.exists() or malformed_gate_should_not_write_csv.exists() or malformed_gate_should_not_write_md.exists():
            raise AssertionError("malformed scorecard gate floor created output directories or wrote partial cross-family artifacts before failing")

        nonpositive_phase8_gate_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        nonpositive_phase8_gate_payload["decision_gate_minimums"]["phase8_promotion_review"][
            "min_roi_complete_settled_observations"
        ] = 0
        nonpositive_phase8_gate_json.write_text(
            json.dumps(nonpositive_phase8_gate_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        nonpositive_phase8_result = subprocess.run(
            [
                sys.executable,
                CROSS_SCRIPT.name,
                "--scorecard-json",
                str(nonpositive_phase8_gate_json),
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
        if nonpositive_phase8_result.returncode == 0:
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted a non-positive Phase 8 promotion-review gate floor")
        nonpositive_phase8_text = f"{nonpositive_phase8_result.stdout}\n{nonpositive_phase8_result.stderr}"
        if "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer" not in nonpositive_phase8_text:
            raise AssertionError("scorecard JSON failure no longer explains that non-positive Phase 8 gate floors are malformed")
        if (
            nonpositive_phase8_gate_output_dir.exists()
            or nonpositive_phase8_gate_should_not_write_csv.exists()
            or nonpositive_phase8_gate_should_not_write_md.exists()
        ):
            raise AssertionError("non-positive Phase 8 scorecard gate floor created output directories or wrote partial cross-family artifacts before failing")

        nonpositive_real_money_gate_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        nonpositive_real_money_gate_payload["decision_gate_minimums"]["real_money_discussion"][
            "min_total_settled_observations_with_usable_roi"
        ] = 0
        nonpositive_real_money_gate_json.write_text(
            json.dumps(nonpositive_real_money_gate_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        nonpositive_real_money_result = subprocess.run(
            [
                sys.executable,
                CROSS_SCRIPT.name,
                "--scorecard-json",
                str(nonpositive_real_money_gate_json),
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
        if nonpositive_real_money_result.returncode == 0:
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted a non-positive real-money discussion gate floor")
        nonpositive_real_money_text = f"{nonpositive_real_money_result.stdout}\n{nonpositive_real_money_result.stderr}"
        if "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer" not in nonpositive_real_money_text:
            raise AssertionError("scorecard JSON failure no longer explains that non-positive real-money gate floors are malformed")
        if (
            nonpositive_real_money_gate_output_dir.exists()
            or nonpositive_real_money_gate_should_not_write_csv.exists()
            or nonpositive_real_money_gate_should_not_write_md.exists()
        ):
            raise AssertionError("non-positive real-money scorecard gate floor created output directories or wrote partial cross-family artifacts before failing")

        missing_no_baq_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"]["also_requires"] = [
            item
            for item in missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"]["also_requires"]
            if item != cf.NO_BAQ_AS_BEL_PREREQUISITE
        ]
        missing_no_baq_gate_json.write_text(json.dumps(missing_no_baq_payload, indent=2) + "\n", encoding="utf-8")
        missing_no_baq_result = subprocess.run(
            [
                sys.executable,
                CROSS_SCRIPT.name,
                "--scorecard-json",
                str(missing_no_baq_gate_json),
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
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted a real-money gate without the no-BAQ-as-BEL prerequisite")
        missing_no_baq_text = f"{missing_no_baq_result.stdout}\n{missing_no_baq_result.stderr}"
        if "must include 'no BAQ-as-BEL substitution'" not in missing_no_baq_text:
            raise AssertionError("scorecard JSON failure no longer explains that no-BAQ-as-BEL is required for the real-money gate")
        if missing_no_baq_output_dir.exists() or missing_no_baq_should_not_write_csv.exists() or missing_no_baq_should_not_write_md.exists():
            raise AssertionError("missing no-BAQ-as-BEL prerequisite created output directories or wrote partial cross-family artifacts before failing")

        missing_operator_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        missing_operator_payload.pop("current_operator_boundary", None)
        missing_operator_boundary_json.write_text(json.dumps(missing_operator_payload, indent=2) + "\n", encoding="utf-8")
        missing_operator_result = subprocess.run(
            [sys.executable, CROSS_SCRIPT.name, "--compare-main-json", str(missing_operator_boundary_json)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_operator_result.returncode == 0:
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted compare_main_approaches.json without current_operator_boundary")
        missing_operator_text = f"{missing_operator_result.stdout}\n{missing_operator_result.stderr}"
        if "missing current_operator_boundary" not in missing_operator_text:
            raise AssertionError("compare-main JSON failure no longer explains that current_operator_boundary is required for the cross-family card")

        missing_route_payload = json.loads((tmpdir / CURRENT_EVIDENCE_JSON.name).read_text(encoding="utf-8"))
        missing_route_payload.pop("scorecard_audit_route", None)
        missing_scorecard_audit_route_json.write_text(
            json.dumps(missing_route_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_route_result = subprocess.run(
            [
                sys.executable,
                CROSS_SCRIPT.name,
                "--current-evidence-json",
                str(missing_scorecard_audit_route_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_route_result.returncode == 0:
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted current_evidence_summary.json without scorecard_audit_route")
        missing_route_text = f"{missing_route_result.stdout}\n{missing_route_result.stderr}"
        if "missing scorecard_audit_route" not in missing_route_text:
            raise AssertionError("current-evidence JSON failure no longer explains that scorecard_audit_route is required for the cross-family card")

        missing_rebuild_payload = json.loads((tmpdir / CURRENT_EVIDENCE_JSON.name).read_text(encoding="utf-8"))
        missing_rebuild_payload.pop("rebuild_validation_contract", None)
        missing_rebuild_validation_contract_json.write_text(
            json.dumps(missing_rebuild_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_rebuild_result = subprocess.run(
            [
                sys.executable,
                CROSS_SCRIPT.name,
                "--current-evidence-json",
                str(missing_rebuild_validation_contract_json),
                "--csv-output",
                str(missing_rebuild_should_not_write_csv),
                "--md-output",
                str(missing_rebuild_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_rebuild_result.returncode == 0:
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted current_evidence_summary.json without rebuild_validation_contract")
        missing_rebuild_text = f"{missing_rebuild_result.stdout}\n{missing_rebuild_result.stderr}"
        if "missing rebuild_validation_contract" not in missing_rebuild_text:
            raise AssertionError("current-evidence JSON failure no longer explains that rebuild_validation_contract is required for the cross-family card")
        if (
            missing_rebuild_output_dir.exists()
            or missing_rebuild_should_not_write_csv.exists()
            or missing_rebuild_should_not_write_md.exists()
        ):
            raise AssertionError("missing rebuild_validation_contract created output directories or wrote partial cross-family artifacts before failing")

        weakened_rebuild_payload = json.loads((tmpdir / CURRENT_EVIDENCE_JSON.name).read_text(encoding="utf-8"))
        weakened_rebuild_payload["rebuild_validation_contract"][
            "upstream_refresh_order_is_provenance_metadata_only"
        ] = False
        weakened_rebuild_validation_contract_json.write_text(
            json.dumps(weakened_rebuild_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        weakened_rebuild_result = subprocess.run(
            [
                sys.executable,
                CROSS_SCRIPT.name,
                "--current-evidence-json",
                str(weakened_rebuild_validation_contract_json),
                "--csv-output",
                str(weakened_rebuild_should_not_write_csv),
                "--md-output",
                str(weakened_rebuild_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if weakened_rebuild_result.returncode == 0:
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted current_evidence_summary.json with a weakened rebuild_validation_contract")
        weakened_rebuild_text = f"{weakened_rebuild_result.stdout}\n{weakened_rebuild_result.stderr}"
        if "rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true" not in weakened_rebuild_text:
            raise AssertionError("current-evidence JSON failure no longer explains that the rebuild route must stay provenance metadata only")
        if (
            weakened_rebuild_output_dir.exists()
            or weakened_rebuild_should_not_write_csv.exists()
            or weakened_rebuild_should_not_write_md.exists()
        ):
            raise AssertionError("weakened rebuild_validation_contract created output directories or wrote partial cross-family artifacts before failing")

        bad_generated_at_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        bad_generated_at_payload["current_operator_boundary"]["generated_at"] = "2026-06-26T18:12:48"
        bad_operator_generated_at_json.write_text(json.dumps(bad_generated_at_payload, indent=2) + "\n", encoding="utf-8")
        bad_generated_at_result = subprocess.run(
            [
                sys.executable,
                CROSS_SCRIPT.name,
                "--compare-main-json",
                str(bad_operator_generated_at_json),
                "--csv-output",
                str(bad_operator_should_not_write_csv),
                "--md-output",
                str(bad_operator_should_not_write_md),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if bad_generated_at_result.returncode == 0:
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted timezone-naive current_operator_boundary.generated_at")
        bad_generated_at_text = f"{bad_generated_at_result.stdout}\n{bad_generated_at_result.stderr}"
        if "current_operator_boundary generated_at must be timezone-aware ISO provenance metadata" not in bad_generated_at_text:
            raise AssertionError("compare-main JSON failure no longer explains that current_operator_boundary.generated_at must be timezone-aware provenance")
        if bad_operator_output_dir.exists() or bad_operator_should_not_write_csv.exists() or bad_operator_should_not_write_md.exists():
            raise AssertionError("bad current-operator provenance created output directories or wrote partial cross-family artifacts before failing")

        missing_source_reference_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        del missing_source_reference_payload["current_operator_boundary"]["source_freshness_generated_reference_timezone"]
        missing_source_freshness_reference_json.write_text(
            json.dumps(missing_source_reference_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_source_reference_result = subprocess.run(
            [
                sys.executable,
                CROSS_SCRIPT.name,
                "--compare-main-json",
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
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted current_operator_boundary without source-freshness reference metadata")
        missing_source_reference_text = f"{missing_source_reference_result.stdout}\n{missing_source_reference_result.stderr}"
        if "current_operator_boundary is missing fields: source_freshness_generated_reference_timezone" not in missing_source_reference_text:
            raise AssertionError("compare-main JSON failure no longer names the missing current-operator source-freshness reference field")
        if (
            missing_source_freshness_reference_output_dir.exists()
            or missing_source_freshness_reference_should_not_write_csv.exists()
            or missing_source_freshness_reference_should_not_write_md.exists()
        ):
            raise AssertionError("missing source-freshness reference field created output directories or wrote partial cross-family artifacts before failing")

        false_refresh_boundary_flag_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        false_refresh_boundary_flag_payload["current_operator_boundary"]["refresh_boundary_not_real_money_evidence"] = False
        false_refresh_boundary_flag_json.write_text(
            json.dumps(false_refresh_boundary_flag_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        false_refresh_boundary_flag_result = subprocess.run(
            [
                sys.executable,
                CROSS_SCRIPT.name,
                "--compare-main-json",
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
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted current_operator_boundary.refresh_boundary_not_real_money_evidence=false")
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
            raise AssertionError("false refresh-boundary non-evidence flag created output directories or wrote partial cross-family artifacts before failing")

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
                CROSS_SCRIPT.name,
                "--compare-main-json",
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
            raise AssertionError("cross_family_decision_card.py unexpectedly accepted current_operator_boundary.refresh_counts_as_roi_complete_evidence_by_itself=true")
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
            raise AssertionError("false refresh-accounting flag created output directories or wrote partial cross-family artifacts before failing")

    checks.append(
        require(
            True,
            "cli_csv_matches_saved",
            "cross_family_decision_card.py CLI still writes a CSV that matches the saved cross-family decision table",
        )
    )
    checks.append(
        require(
            tmp_parent == TMP_PARENT
            and tmp_parent.exists()
            and tmp_parent.is_relative_to(BASE),
            "cli_scratch_root_project_local",
            f"cross-family CLI, custom-source, and negative source-drift fixtures use project-local temporary root {tmp_parent}, cleared before the fixture run",
        )
    )
    checks.append(
        require(
            scratch_meta["tmp_parent_is_project_local"] is True
            and scratch_meta["tmp_parent_cleared_before_fixture_run"] is True
            and Path(scratch_meta["tmp_parent"]) == TMP_PARENT,
            "cli_scratch_metadata_published",
            "cross-family validation publishes top-level project-local scratch metadata so parent rollups can verify the cleared fixture root without parsing rebuild fields or prose",
        )
    )
    checks.append(
        require(
            True,
            "cli_markdown_matches_rebuild",
            "cross_family_decision_card.py CLI still writes CROSS_FAMILY_DECISION.md exactly as a fresh rebuild renders it",
        )
    )
    checks.append(
        require(
            True,
            "cli_stdout_matches_generated_report",
            "cross_family_decision_card.py CLI stdout still matches the generated report plus its Saved: lines",
        )
    )
    checks.append(
        require(
            True,
            "cli_custom_input_and_output_paths",
            "cross_family_decision_card.py can now rerender from explicit scorecard and frozen-eval input paths and write to custom output paths without depending on the default saved artifact names",
        )
    )
    checks.append(
        require(
            True,
            "missing_shortlist_rule_fails_fast",
            "the real cross-family CLI now fails fast if the scorecard loses OP_REFINED_K7 instead of quietly weakening the active shortlist",
        )
    )
    checks.append(
        require(
            True,
            "missing_watch_context_rule_fails_fast",
            "the real cross-family CLI now fails fast if the scorecard loses KEE_K9 instead of quietly flattening the observation-only watch context",
        )
    )
    checks.append(
        require(
            True,
            "missing_frozen_year_slice_fails_fast",
            "the real cross-family CLI now fails fast if frozen eval loses CD_CORE_K8/year_2025 instead of quietly softening the paper-vs-anchor split story",
        )
    )
    checks.append(
        require(
            True,
            "missing_scorecard_ranking_contract_fails_fast",
            "the real cross-family CLI now fails fast if the scorecard JSON loses ranking_contract instead of quietly dropping the tier-first ranking semantics",
        )
    )
    checks.append(
        require(
            True,
            "missing_scorecard_decision_gate_minimums_fails_fast",
            "the real cross-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if the scorecard JSON loses decision_gate_minimums, contains a boolean anchor floor, gives Phase 8 or real-money review a non-positive floor, or drops the no-BAQ-as-BEL real-money prerequisite instead of silently weakening the paper-observation floors for anchor displacement, Phase 8 promotion review, or real-money discussion",
        )
    )
    checks.append(
        require(
            True,
            "missing_operator_boundary_fails_fast",
            "the real cross-family CLI now fails fast if compare_main_approaches.json loses current_operator_boundary instead of silently dropping the current paper-workflow boundary",
        )
    )
    checks.append(
        require(
            True,
            "missing_scorecard_audit_route_fails_fast",
            "the real cross-family CLI now fails fast if current_evidence_summary.json loses scorecard_audit_route instead of silently dropping the copied gate/ranking/CI-only/timezone/no-BAQ audit route from the current paper snapshot",
        )
    )
    checks.append(
        require(
            True,
            "missing_rebuild_validation_contract_fails_fast",
            "the real cross-family CLI now fails fast without creating output directories or writing artifacts if current_evidence_summary.json loses rebuild_validation_contract or weakens its provenance-only flag before republishing the current bridge rebuild-order route",
        )
    )
    checks.append(
        require(
            True,
            "bad_current_operator_generated_at_fails_fast",
            "the real cross-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if compare_main_approaches.json carries a timezone-naive current_operator_boundary.generated_at or loses the current-operator source-freshness reference fields instead of republishing malformed current-paper provenance",
        )
    )
    checks.append(
        require(
            True,
            "false_current_operator_refresh_not_real_money_flag_fails_fast",
            "the real cross-family CLI now fails fast without creating output directories or writing CSV/markdown artifacts if compare_main_approaches.json marks current_operator_boundary.refresh_boundary_not_real_money_evidence=false or refresh_counts_as_roi_complete_evidence_by_itself=true instead of republishing weakened current-paper provenance",
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
            and "`forward_evidence_scorecard.json`" in saved_md,
            "scorecard_ranking_contract_inherited",
            "CROSS_FAMILY_DECISION.md now consumes forward_evidence_scorecard.json ranking_contract so the shortlist explains that rank is tier-first and raw OP_REFINED_K7 score is not an automatic promotion cue",
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
            and "Clean empty scans, open paper signals, historical replay rows, source fingerprints, green validators, compatibility labels, or a WATCH label do not satisfy these gates." in saved_md,
            "scorecard_decision_gate_minimums_documented",
            "CROSS_FAMILY_DECISION.md now loads the scorecard decision_gate_minimums directly and documents the separate 30-row anchor-displacement floor, 20-row Phase 8 promotion-review floor, and 100-row real-money discussion floor with exact threshold-source keys",
        )
    )
    checks.append(
        require(
            "## Current Paper Snapshot" in saved_md
            and f"This context is inherited from `{COMPARE_JSON.name}` / `{operator_boundary['source_path']}`" in saved_md
            and f"bridge reference = `{operator_boundary['source_freshness_generated_reference_date']}` (`{operator_boundary['source_freshness_generated_reference_timezone']}`)" in saved_md
            and f"comparison = `{operator_boundary['source_freshness_staleness_comparison_source']}` / `{operator_boundary['source_freshness_staleness_comparison_date']}`" in saved_md
            and str(operator_boundary["source_freshness_read"]) in saved_md
            and f"`{operator_boundary['refresh_action_command']}` required before right-now use = `{operator_boundary['refresh_required_before_right_now_instruction_use']}`" in saved_md
            and f"settles rows / creates ROI evidence / clean-empty performance = `{operator_boundary['refresh_can_settle_open_rows_by_itself']}` / `{operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}` / `{operator_boundary['clean_empty_refresh_counts_as_forward_performance']}`" in saved_md
            and "| Operator read gate |" in saved_md
            and f"`{COMPARE_JSON.name}` `current_operator_boundary.operator_read_gate`" in saved_md
            and cf.md_cell(operator_read_gate["read"]) in saved_md
            and operator_read_gate_branch_ok
            and operator_read_gate["current_top_card_counts_as_no_target_evidence"] is False
            and operator_read_gate["current_top_card_counts_as_clean_empty_evidence"] is False
            and operator_read_gate["current_top_card_counts_as_bet_readiness_evidence"] is False
            and operator_read_gate["current_top_card_counts_as_settled_roi_evidence"] is False
            and "| Primary first-read gate |" not in saved_md
            and "| Bridge-published gate progress |" in saved_md
            and f"`{CURRENT_EVIDENCE_JSON.name}` `decision_gate_progress`" in saved_md
            and cf.md_cell(current_gate_progress["read"]) in saved_md
            and current_gate_progress.get("gate_status") == "all_uncleared"
            and current_gate_progress.get("all_gates_ready") is False
            and current_gate_progress.get("not_forward_performance_evidence") is True
            and current_gate_progress.get("not_promotion_readiness_evidence") is True
            and current_gate_progress.get("not_live_profitability_evidence") is True
            and current_gate_progress.get("not_real_money_evidence") is True
            and f"| Current settled rule mix | OP_DURABLE_K7={operator_boundary['op_anchor_roi_complete_rows']}; CD_CORE_K8={operator_boundary['cd_companion_roi_complete_rows']};" in saved_md
            and (
                f"| Settlement queue state | `{operator_boundary['open_settlement_queue_state']}`; "
                f"{cf.md_cell(operator_boundary['open_settlement_context'])}; detail: "
                f"{cf.md_cell(operator_boundary['open_settlement_queue_read'])} |"
            ) in saved_md
            and "| Open settlement context |" not in saved_md
            and "Settlement queue state:" not in str(operator_boundary.get("open_settlement_queue_read") or "")
            and bool(operator_boundary["current_settled_context_is_cd_only"]) is True
            and int(operator_boundary["op_anchor_roi_complete_rows"]) == 0
            and int(operator_boundary["cd_companion_roi_complete_rows"]) == int(operator_boundary["roi_complete_primary_rows"])
            and "CD-only paper rows are not OP-anchor or cross-family promotion evidence" in saved_md
            and "The current operator boundary is routing/provenance context only." in saved_md
            and "not settled ROI, OP-anchor proof, cross-family promotion readiness, live profitability, bankroll guidance, or real-money evidence" in saved_md,
            "current_operator_boundary_documented",
            "CROSS_FAMILY_DECISION.md carries the compare-main current-operator boundary plus current_evidence_summary.json decision_gate_progress, including structured source-freshness reference-date and staleness-comparison fields, stale-card refresh routing, wrapper-refresh non-evidence flags, the inherited operator_read_gate, the bridge-published current gate split, OP_DURABLE_K7=0 versus the current CD_CORE_K8 count, the CD-only current settled context, source-published settlement-queue state/context/detail, recommendation-state context, and no cross-family-promotion / no-real-money caveat",
        )
    )
    checks.append(
        require(
            "| Scorecard audit route |" in saved_md
            and "`current_evidence_summary.json` `scorecard_audit_route`" in saved_md
            and scorecard_audit_route.get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route.get("json_path") == "scorecard_ranking_contract_audit.json"
            and scorecard_audit_route.get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route.get("gate_floor_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get("real_money_no_baq_as_bel_required") is True
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
            and "Report-synchronization route only; it is not cross-family evidence, forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in saved_md,
            "current_evidence_scorecard_audit_route_documented",
            "CROSS_FAMILY_DECISION.md now republishes current_evidence_summary.json.scorecard_audit_route so copied gate/ranking/CI-only/timezone/no-BAQ synchronization questions route to the dedicated audit without becoming cross-family evidence, forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
        )
    )
    checks.append(
        require(
            "| Current bridge rebuild order |" in saved_md
            and "`current_evidence_summary.json` `rebuild_validation_contract`" in saved_md
            and rebuild_validation_contract.get("prerequisite_rebuild_command") == "python3 paper_trade_settlement_audit.py"
            and rebuild_validation_contract.get("rebuild_command") == "python3 current_evidence_summary.py"
            and rebuild_validation_contract.get("direct_validation_command") == "python3 validate_current_evidence_summary.py"
            and rebuild_order_commands
            == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and rebuild_validation_contract.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and rebuild_validation_contract.get("requires_source_consistency_before_quoting_current_totals") is True
            and rebuild_validation_contract.get("requires_source_freshness_before_right_now_instruction_use") is True
            and rebuild_validation_contract.get("green_checks_are_reproducibility_metadata_only") is True
            and rebuild_validation_contract.get("upstream_refresh_order_is_provenance_metadata_only") is True
            and rebuild_validation_contract.get("not_settled_roi_or_real_money_evidence") is True
            and rebuild_validation_contract.get("source_path") == "rebuild_validation_contract"
            and (
                "| Current bridge rebuild order | `current_evidence_summary.json` `rebuild_validation_contract`: "
                "`python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> "
                "`python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*` "
                "after source-byte changes | Provenance/rebuild route only; green checks and rebuild order are not "
                "cross-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, "
                "bankroll guidance, or real-money evidence |"
            )
            in saved_md,
            "current_evidence_rebuild_validation_contract_documented",
            "CROSS_FAMILY_DECISION.md now republishes current_evidence_summary.json.rebuild_validation_contract so source-byte changes route through settlement-audit -> current-bridge -> bridge-validator before anyone quotes current totals from the direct cross-family card",
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
            "CROSS_FAMILY_DECISION.md now republishes compare_main_approaches.json current_operator_boundary.operator_read_gate as branch-aware routing metadata, not no-target, clean-empty, bet-readiness, settled ROI, promotion, live-profitability, bankroll, or real-money evidence",
        )
    )
    checks.append(
        require(
            cf.has_timezone_aware_timestamp(operator_boundary.get("generated_at")),
            "current_operator_boundary_generated_at_is_timezone_aware",
            f"cross-family card inherits compare-main current_operator_boundary.generated_at={operator_boundary.get('generated_at')!r} as parseable timezone-aware provenance metadata only",
        )
    )
    checks.append(
        require(
            "## Source Provenance" in saved_md
            and "Exact input-byte fingerprints for this cross-family card." in saved_md
            and "they do not prove settled paper ROI, promotion readiness, live profitability, or real-money performance." in saved_md
            and source_provenance_matches_disk(saved_md),
            "source_provenance_markdown_matches_disk",
            "CROSS_FAMILY_DECISION.md now fingerprints scorecard CSV/JSON, frozen-eval, compare-main JSON, and current-evidence bridge inputs, with markdown byte counts and SHA-256 values matching current disk files",
        )
    )
    checks.append(
        require(
            df.loc["OP_DURABLE_K7", "role"] == "ANCHOR"
            and df.loc["CD_CORE_K8", "role"] == "PAPER"
            and df.loc["OP_REFINED_K7", "role"] == "WATCH",
            "cross_family_roles",
            "cross-family card still orders the shortlist as ANCHOR / PAPER / WATCH",
        )
    )
    checks.append(
        require(
            df.loc["OP_DURABLE_K7", "scorecard_tier"] == "ANCHOR"
            and df.loc["CD_CORE_K8", "scorecard_tier"] == "PAPER"
            and df.loc["OP_REFINED_K7", "scorecard_tier"] == "WATCH",
            "scorecard_tier_alignment",
            "cross-family card still agrees with the forward evidence scorecard tiers",
        )
    )
    checks.append(
        require(
            df.loc["OP_DURABLE_K7", "shadow_rank"] == "LIVE_DEFAULT"
            and df.loc["CD_CORE_K8", "shadow_rank"] == "PRIMARY_SHADOW"
            and df.loc["OP_REFINED_K7", "shadow_rank"] == "SECONDARY_SHADOW",
            "shadow_rank_ordering",
            "cross-family card keeps the legacy shadow_rank compatibility labels while mapping CD_CORE_K8 to the paper-basket companion and OP_REFINED_K7 to the same-family shadow challenger behind the anchor",
        )
    )

    for rule_id in ["OP_DURABLE_K7", "CD_CORE_K8", "OP_REFINED_K7"]:
        score_row = score_df.loc[rule_id]
        checks.append(
            require(
                abs(float(df.loc[rule_id, "holdout_roi"]) - float(score_row["holdout_roi"])) < 1e-9
                and int(df.loc[rule_id, "holdout_races"]) == int(score_row["holdout_races"])
                and int(df.loc[rule_id, "wf_selected_count"]) == int(score_row["wf_selected_count"])
                and abs(float(df.loc[rule_id, "ci_lower"]) - float(score_row["ci_lower"])) < 1e-9
                and abs(float(df.loc[rule_id, "forward_trust"]) - float(score_row["forward_trust"])) < 1e-9,
                f"{rule_id.lower()}_matches_scorecard",
                f"{rule_id} cross-family row still matches the scorecard holdout/sample/WF/CI metrics",
            )
        )

    for rule_id in ["OP_DURABLE_K7", "CD_CORE_K8", "OP_REFINED_K7"]:
        year_2024 = frozen_rule_slice(rule_id, "year_2024")
        year_2025 = frozen_rule_slice(rule_id, "year_2025")
        score_row = score_df.loc[rule_id]
        checks.append(
            require(
                abs(float(df.loc[rule_id, "holdout_2024_roi"]) - float(year_2024["roi"])) < 1e-9
                and int(df.loc[rule_id, "holdout_2024_races"]) == int(score_row["holdout_2024_races"])
                and abs(float(df.loc[rule_id, "holdout_2025_roi"]) - float(year_2025["roi"])) < 1e-9
                and int(df.loc[rule_id, "holdout_2025_races"]) == int(score_row["holdout_2025_races"]),
                f"{rule_id.lower()}_matches_year_slices",
                f"{rule_id} cross-family row still matches the frozen 2024 and 2025 rule slices plus the scorecard year-specific race counts",
            )
        )

    checks.append(
        require(
            int(df.loc["OP_DURABLE_K7", "holdout_races"]) > int(df.loc["CD_CORE_K8", "holdout_races"])
            and int(df.loc["OP_DURABLE_K7", "wf_selected_count"]) > int(df.loc["CD_CORE_K8", "wf_selected_count"]),
            "anchor_has_larger_sample_than_cd",
            "OP_DURABLE_K7 still beats CD_CORE_K8 on OP holdout sample and walk-forward selection coverage",
        )
    )
    checks.append(
        require(
            float(df.loc["CD_CORE_K8", "holdout_roi_vs_anchor"]) > 0
            and int(df.loc["CD_CORE_K8", "holdout_races_vs_anchor"]) < 0
            and int(df.loc["CD_CORE_K8", "wf_selected_vs_anchor"]) < 0
            and "walk-forward recurrence" in str(df.loc["CD_CORE_K8", "promotion_blocker"]),
            "cd_is_paper_not_anchor",
            "CD_CORE_K8 still stays PAPER because its prettier ROI comes on a smaller sample and much weaker WF selection than the anchor",
        )
    )
    checks.append(
        require(
            float(df.loc["OP_REFINED_K7", "holdout_roi_vs_anchor"]) > 0
            and int(df.loc["OP_REFINED_K7", "holdout_races_vs_anchor"]) < 0
            and float(df.loc["OP_REFINED_K7", "holdout_2024_roi"]) < 0
            and "non-losing second holdout year" in str(df.loc["OP_REFINED_K7", "promotion_blocker"]),
            "op_refined_stays_watch",
            "OP_REFINED_K7 still stays WATCH because the higher ROI is paired with a smaller sample and a losing 2024 holdout year",
        )
    )
    checks.append(
        require(
            "This table keeps the shortlist split-aware on purpose" in saved_md
            and f"`valid_evidence_scope={cf.VALID_EVIDENCE_SCOPE}`" in saved_md
            and "Here, `WF Selected` is train-only selection recurrence context, not a second profit line or extra train-only validation layer." in saved_md
            and "Treat those roles as evidence-ranked, not statistically clean slam dunks: `OP_DURABLE_K7` still has CI low `-3.40%`, `CD_CORE_K8` still has CI low `-15.00%`, and `OP_REFINED_K7` only gets a positive CI low `+11.20%` on a much smaller holdout sample." in saved_md
            and "Scorecard CI-only promotion check: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` says `ci_only_promotion_allowed=false`; the positive OP_REFINED CI lower bound is support context only, not a promotion trigger." in saved_md
            and "| OP_DURABLE_K7 | OP | ANCHOR | +22.90% | 115 | -47.41% / 68 | +124.61% / 47 |" in saved_md
            and "| CD_CORE_K8 | CD | PAPER | +55.96% | 60 | +45.65% / 41 | +78.21% / 19 |" in saved_md
            and "| OP_REFINED_K7 | OP | WATCH | +51.43% | 49 | -25.47% / 33 | +210.02% / 16 |" in saved_md
            and "largest OP holdout sample (115)" in saved_md
            and "largest active holdout sample" not in saved_md
            and "its own holdout path was uneven (`2024 -47.41% on 68`, `2025 +124.61% on 47`)" in saved_md
            and "Treat the walk-forward-selected counts as recurrence context for how often each rule survives train-only yearly selection, not as fresh standalone profit proof." in saved_md
            and "This note is intentionally pinned to the frozen 2024-2025 holdout standard carried by the scorecard and frozen-evaluation artifacts, so a prettier line from some other window does not quietly rewrite the paper-decision shortlist." in saved_md,
            "markdown_split_counts_present",
            "CROSS_FAMILY_DECISION.md now carries the source-level valid_evidence_scope line, the explicit frozen 2024-2025 holdout lock, split-aware year ROI plus race counts, makes the WF-selected column recurrence context rather than a second profit line, avoids stale active-sample wording, and keeps explicit CI caution for all three shortlist roles",
        )
    )
    checks.append(
        require(
            "## Paper Companion and Shadow Read" in saved_md
            and "**Primary paper companion: `CD_CORE_K8`**" in saved_md
            and "sample depth (`60` vs `115`), walk-forward selection (`1/10` vs `7/10`), and CI strength (still `-15.00%` at the lower bound)" in saved_md
            and "**Same-family OP shadow challenger: `OP_REFINED_K7`**" in saved_md
            and "its CI lower bound is positive at `+11.20%`, but it still needs more forward races" in saved_md,
            "markdown_shadow_read_present",
            "CROSS_FAMILY_DECISION.md now names CD_CORE_K8 as the primary paper companion and OP_REFINED_K7 as the same-family OP shadow challenger explicitly, with CI-strength caution attached",
        )
    )
    checks.append(
        require(
            "### Scorecard CI-Only Promotion Check" in saved_md
            and "Source: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7`" in saved_md
            and "- Current decision: Keep OP_REFINED_K7 shadow/watch only." in saved_md
            and "- CI-only promotion allowed: `false`" in saved_md
            and "smaller holdout sample than OP_DURABLE_K7, losing 2024 holdout split, lower walk-forward recurrence than OP_DURABLE_K7" in saved_md
            and "phase8 promotion review = 20+ ROI-complete candidate shadow observations plus cleaner split-aware/walk-forward support" in saved_md
            and "anchor displacement = 30+ ROI-complete same-candidate paper observations plus a cleaner split-aware forward read and equal-or-better walk-forward support" in saved_md
            and "Does not count: positive bootstrap CI lower bound by itself, hotter aggregate small-sample holdout ROI, historical replay rows, clean rebuilds, green validators." in saved_md
            and scorecard_ci_only_diagnostic["ci_only_promotion_allowed"] is False
            and scorecard_ci_only_diagnostic["candidate_rule_id"] == "OP_REFINED_K7",
            "markdown_scorecard_ci_only_diagnostic_present",
            "CROSS_FAMILY_DECISION.md now source-matches the scorecard OP_REFINED CI-only diagnostic so positive CI support cannot read as cross-family promotion readiness",
        )
    )
    checks.append(
        require(
            "## Not in the near-promotion shortlist" in saved_md
            and "The rest of the current Phase 8 watch list is still observation-only, not part of the near-term cross-family promotion queue:" in saved_md
            and "`KEE_K9`: keep logging it, but it still has only 20 holdout races, CI low -3.00%, and only 3/10 walk-forward support." in saved_md
            and "`SA_K9`: still only 11 holdout races and 0/10 walk-forward support, even though both observed holdout years are positive." in saved_md
            and "`DMR_FALL_K7`: still only 14 holdout races, just one observed holdout year, and 0/10 walk-forward support." in saved_md
            and "Those pockets are worth observing, but they are not peers of `CD_CORE_K8` or `OP_REFINED_K7` for current paper-hierarchy promotion decisions." in saved_md,
            "markdown_observation_only_pockets_present",
            "CROSS_FAMILY_DECISION.md now says plainly that KEE_K9, SA_K9, and DMR_FALL_K7 are observation-only pockets outside the near-term cross-family promotion shortlist",
        )
    )

    suite_read = (
        f"cross-family card stays pinned to the frozen 2024-2025 holdout standard with valid_evidence_scope={cf.VALID_EVIDENCE_SCOPE}; "
        "Anchor=OP_DURABLE_K7, paper companion=CD_CORE_K8, closest same-family shadow=OP_REFINED_K7; broader Phase 8 pockets KEE_K9 / SA_K9 / DMR_FALL_K7 stay observation-only rather than entering the near-term promotion queue; "
        f"anchor still leads on OP holdout sample ({int(df.loc['OP_DURABLE_K7', 'holdout_races'])} vs {int(df.loc['CD_CORE_K8', 'holdout_races'])} holdout races) "
        f"and walk-forward selection coverage ({int(df.loc['OP_DURABLE_K7', 'wf_selected_count'])} vs {int(df.loc['CD_CORE_K8', 'wf_selected_count'])}, recurrence context rather than a second profit line), with CI lows {float(df.loc['OP_DURABLE_K7', 'ci_lower']):+.2f}% vs {float(df.loc['CD_CORE_K8', 'ci_lower']):+.2f}% vs {float(df.loc['OP_REFINED_K7', 'ci_lower']):+.2f}%; "
        f"with the anchor split shown directly as 2024={float(df.loc['OP_DURABLE_K7', 'holdout_2024_roi']):+.2f}% on {int(df.loc['OP_DURABLE_K7', 'holdout_2024_races'])} "
        f"vs 2025={float(df.loc['OP_DURABLE_K7', 'holdout_2025_roi']):+.2f}% on {int(df.loc['OP_DURABLE_K7', 'holdout_2025_races'])}; "
        f"scorecard ranking contract inherited=tier-first, raw Score non-promotional ({scorecard_ranking_contract['known_rank_override']}); "
        "scorecard CI-only diagnostic inherited from forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7 keeps ci_only_promotion_allowed=false so positive OP_REFINED CI support stays out of cross-family promotion readiness; "
        "scorecard decision gates inherited directly from forward_evidence_scorecard.json decision_gate_minimums (anchor_displacement=30 same-candidate settled observations; phase8_promotion_review=20 shadow observations; real_money_discussion=100 total settled ROI-complete observations); "
        f"bridge-published gate progress from current_evidence_summary.json.decision_gate_progress says {current_gate_progress['read']} with gate_status={current_gate_progress['gate_status']} and all_gates_ready={current_gate_progress['all_gates_ready']}; "
        f"current_evidence_summary.json.scorecard_audit_route points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to {scorecard_audit_route['markdown_path']} / {scorecard_audit_route['json_path']} plus {scorecard_audit_route['validator_command']} as report-synchronization metadata only, not cross-family evidence, forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence; "
        f"current_evidence_summary.json.rebuild_validation_contract routes source-byte changes through {' -> '.join(rebuild_order_commands)} before quoting CURRENT_EVIDENCE_SUMMARY.* as provenance/rebuild metadata only, not cross-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence; "
        f"operator read gate inherited from compare-main says {operator_read_gate['read']} with gate_status={operator_read_gate['gate_status']} and recommended_command={operator_read_gate['recommended_command']}; "
        f"current operator boundary inherited from compare-main JSON names stale-card refresh route={operator_boundary['refresh_action_command']} with source-freshness bridge reference={operator_boundary['source_freshness_generated_reference_date']} ({operator_boundary['source_freshness_generated_reference_timezone']}) and staleness comparison={operator_boundary['source_freshness_staleness_comparison_source']}:{operator_boundary['source_freshness_staleness_comparison_date']}, plus current settled rule mix OP_DURABLE_K7={operator_boundary['op_anchor_roi_complete_rows']} / CD_CORE_K8={operator_boundary['cd_companion_roi_complete_rows']} with CD-only context={operator_boundary['current_settled_context_is_cd_only']} and settlement-queue state={operator_boundary['open_settlement_queue_state']} / context={operator_boundary['open_settlement_context']} from compare-main rather than settled ROI, OP-anchor proof, cross-family promotion readiness, live profitability, bankroll guidance, or real-money evidence; "
        f"copied current-operator generated_at={operator_boundary['generated_at']} stays parseable timezone-aware provenance metadata only; "
        "source provenance fingerprints the scorecard CSV/JSON, frozen-eval, compare-main, and current-evidence inputs as reproducibility metadata only; "
        "saved CSV, saved markdown, and real CLI stdout stay pinned to the same cross-family decision render; "
        "bad scorecard-gate, current-evidence rebuild-contract, and current-operator provenance fixtures now prove no output directory or partial cross-family artifact is created before failure"
    )

    payload = {
        "suite_status": "pass",
        "artifact": {
            "saved_csv": CROSS_CSV.name,
            "saved_markdown": CROSS_MD.name,
            "status": "pass",
            "rows": int(len(saved_df)),
        },
        "valid_evidence_scope": cf.VALID_EVIDENCE_SCOPE,
        "scorecard_ranking_contract": scorecard_ranking_contract,
        "scorecard_ranking_contract_source": SCORECARD_JSON.name,
        "scorecard_decision_gate_minimums": scorecard_decision_gates,
        "scorecard_decision_gate_minimums_source": SCORECARD_JSON.name,
        "scorecard_ci_only_diagnostic": scorecard_ci_only_diagnostic,
        "scorecard_ci_only_diagnostic_source": f"{SCORECARD_JSON.name}:{cf.OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}",
        "current_evidence_gate_progress_read": current_gate_progress,
        "current_evidence_scorecard_audit_route_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            **scorecard_audit_route,
        },
        "current_evidence_rebuild_validation_contract_read": {
            "source": CURRENT_EVIDENCE_JSON.name,
            **rebuild_validation_contract,
        },
        "current_operator_read_gate": operator_read_gate,
        "current_operator_boundary": {
            "source_path": operator_boundary["source_path"],
            "generated_at": operator_boundary["generated_at"],
            "source_freshness_generated_reference_date": operator_boundary["source_freshness_generated_reference_date"],
            "source_freshness_generated_reference_timezone": operator_boundary["source_freshness_generated_reference_timezone"],
            "source_freshness_staleness_comparison_source": operator_boundary["source_freshness_staleness_comparison_source"],
            "source_freshness_staleness_comparison_date": operator_boundary["source_freshness_staleness_comparison_date"],
            "source_freshness_read": operator_boundary["source_freshness_read"],
            "refresh_action_command": operator_boundary["refresh_action_command"],
            "refresh_required_before_right_now_instruction_use": operator_boundary["refresh_required_before_right_now_instruction_use"],
            "refresh_can_update_operator_surfaces": operator_boundary["refresh_can_update_operator_surfaces"],
            "refresh_can_settle_open_rows_by_itself": operator_boundary["refresh_can_settle_open_rows_by_itself"],
            "refresh_counts_as_roi_complete_evidence_by_itself": operator_boundary["refresh_counts_as_roi_complete_evidence_by_itself"],
            "clean_empty_refresh_counts_as_forward_performance": operator_boundary["clean_empty_refresh_counts_as_forward_performance"],
            "not_forward_performance_evidence": operator_boundary["not_forward_performance_evidence"],
            "not_bet_readiness_evidence_by_itself": operator_boundary["not_bet_readiness_evidence_by_itself"],
            "open_settlement_context": operator_boundary["open_settlement_context"],
            "open_settlement_queue_state": operator_boundary["open_settlement_queue_state"],
            "open_settlement_queue_read": operator_boundary["open_settlement_queue_read"],
            "current_settled_context_is_cd_only": operator_boundary["current_settled_context_is_cd_only"],
            "op_anchor_roi_complete_rows": operator_boundary["op_anchor_roi_complete_rows"],
            "cd_companion_roi_complete_rows": operator_boundary["cd_companion_roi_complete_rows"],
            "roi_complete_primary_rows": operator_boundary["roi_complete_primary_rows"],
            "first_read_threshold": operator_boundary["first_read_threshold"],
            "first_read_remaining": operator_boundary["first_read_remaining"],
        },
        "scratch": scratch_meta,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "summary": {
            "anchor_rule": "OP_DURABLE_K7",
            "paper_rule": "CD_CORE_K8",
            "watch_rule": "OP_REFINED_K7",
            "anchor_holdout_races": int(df.loc["OP_DURABLE_K7", "holdout_races"]),
            "anchor_wf_selected_count": int(df.loc["OP_DURABLE_K7", "wf_selected_count"]),
            "current_evidence_gate_progress_read": {
                "source_path": current_gate_progress["source_path"],
                "source_json_path": current_gate_progress["source_json_path"],
                "gate_status": current_gate_progress["gate_status"],
                "all_gates_ready": current_gate_progress["all_gates_ready"],
                "read": current_gate_progress["read"],
                "not_forward_performance_evidence": current_gate_progress["not_forward_performance_evidence"],
                "not_promotion_readiness_evidence": current_gate_progress["not_promotion_readiness_evidence"],
                "not_live_profitability_evidence": current_gate_progress["not_live_profitability_evidence"],
                "not_real_money_evidence": current_gate_progress["not_real_money_evidence"],
            },
            "current_evidence_scorecard_audit_route_read": {
                "source": CURRENT_EVIDENCE_JSON.name,
                "markdown_path": scorecard_audit_route["markdown_path"],
                "json_path": scorecard_audit_route["json_path"],
                "validator_command": scorecard_audit_route["validator_command"],
                "valid_use": scorecard_audit_route["valid_use"],
                "artifacts_present": scorecard_audit_route["artifacts_present"],
                "not_forward_performance_evidence": scorecard_audit_route["not_forward_performance_evidence"],
                "not_settled_roi_evidence": scorecard_audit_route["not_settled_roi_evidence"],
                "not_promotion_readiness_evidence": scorecard_audit_route["not_promotion_readiness_evidence"],
                "not_live_profitability_evidence": scorecard_audit_route["not_live_profitability_evidence"],
                "not_bankroll_guidance": scorecard_audit_route["not_bankroll_guidance"],
                "not_real_money_evidence": scorecard_audit_route["not_real_money_evidence"],
            },
            "current_evidence_rebuild_validation_contract_read": {
                "source": CURRENT_EVIDENCE_JSON.name,
                "source_path": rebuild_validation_contract["source_path"],
                "prerequisite_rebuild_command": rebuild_validation_contract["prerequisite_rebuild_command"],
                "rebuild_command": rebuild_validation_contract["rebuild_command"],
                "direct_validation_command": rebuild_validation_contract["direct_validation_command"],
                "upstream_refresh_commands": rebuild_validation_contract["upstream_refresh_commands"],
                "upstream_refresh_order_is_provenance_metadata_only": rebuild_validation_contract[
                    "upstream_refresh_order_is_provenance_metadata_only"
                ],
                "not_settled_roi_or_real_money_evidence": rebuild_validation_contract[
                    "not_settled_roi_or_real_money_evidence"
                ],
            },
            "suite_read": suite_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }

    lines = [
        "# Cross-Family Decision Validation",
        "",
        "This report validates the active cross-family shortlist directly, including the saved CSV and markdown artifacts plus the real CLI stdout report, save notices, scorecard-sourced decision-change gates, current-evidence gate-progress routing, and the fail-fast checks for missing shortlist/watch scorecard rows or frozen year slices.",
        "",
        "## Artifact Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Saved artifacts: `{CROSS_CSV.name}`, `{CROSS_MD.name}`",
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
            f"- Source scope line: `valid_evidence_scope={cf.VALID_EVIDENCE_SCOPE}`",
            "- Source-drift guardrail: required shortlist rows, watch-context rows, and frozen 2024/2025 rule slices now fail fast instead of degrading into a polished-looking but incomplete cross-family hierarchy",
            f"- Anchor: OP_DURABLE_K7 ({df.loc['OP_DURABLE_K7', 'role']})",
            f"- Paper: CD_CORE_K8 ({df.loc['CD_CORE_K8', 'role']})",
            f"- Watch: OP_REFINED_K7 ({df.loc['OP_REFINED_K7', 'role']})",
            f"- Scorecard ranking contract: tier-first={scorecard_ranking_contract['rank_is_tier_first_decision_order']}; raw-score-promotional={not scorecard_ranking_contract['raw_score_is_not_an_automatic_deployment_instruction']}; {scorecard_ranking_contract['known_rank_override']}",
            f"- Scorecard decision gates: anchor_displacement={scorecard_decision_gates['anchor_displacement']['minimum_roi_complete_same_candidate_observations']} same-candidate settled rows; phase8_promotion_review={scorecard_decision_gates['phase8_promotion_review']['minimum_roi_complete_settled_observations']} shadow rows; real_money_discussion={scorecard_decision_gates['real_money_discussion']['minimum_total_settled_roi_complete_observations']} total settled ROI-complete rows",
            f"- Current gate progress: {current_gate_progress['read']} gate_status={current_gate_progress['gate_status']}; all_gates_ready={current_gate_progress['all_gates_ready']}; this is routing context only, not settled ROI, OP-anchor proof, cross-family promotion readiness, live profitability, or real-money evidence.",
            f"- Scorecard audit route: current_evidence_summary.json.scorecard_audit_route -> {scorecard_audit_route['markdown_path']} / {scorecard_audit_route['json_path']} plus {scorecard_audit_route['validator_command']}; this is report-synchronization metadata only, not cross-family evidence, forward performance, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- Current bridge rebuild order: current_evidence_summary.json.rebuild_validation_contract -> {' -> '.join(rebuild_order_commands)} before quoting CURRENT_EVIDENCE_SUMMARY.* after source-byte changes; this is provenance/rebuild metadata only, not cross-family evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- Anchor holdout races: {int(df.loc['OP_DURABLE_K7', 'holdout_races'])}",
            f"- Anchor walk-forward selections: {int(df.loc['OP_DURABLE_K7', 'wf_selected_count'])}/{int(df.loc['OP_DURABLE_K7', 'wf_total_folds'])}",
            f"- Anchor holdout split: 2024 {float(df.loc['OP_DURABLE_K7', 'holdout_2024_roi']):+.2f}% on {int(df.loc['OP_DURABLE_K7', 'holdout_2024_races'])}, 2025 {float(df.loc['OP_DURABLE_K7', 'holdout_2025_roi']):+.2f}% on {int(df.loc['OP_DURABLE_K7', 'holdout_2025_races'])}",
            f"- CD_CORE_K8 holdout split: 2024 {float(df.loc['CD_CORE_K8', 'holdout_2024_roi']):+.2f}% on {int(df.loc['CD_CORE_K8', 'holdout_2024_races'])}, 2025 {float(df.loc['CD_CORE_K8', 'holdout_2025_roi']):+.2f}% on {int(df.loc['CD_CORE_K8', 'holdout_2025_races'])}",
            f"- OP_REFINED_K7 holdout split: 2024 {float(df.loc['OP_REFINED_K7', 'holdout_2024_roi']):+.2f}% on {int(df.loc['OP_REFINED_K7', 'holdout_2024_races'])}, 2025 {float(df.loc['OP_REFINED_K7', 'holdout_2025_roi']):+.2f}% on {int(df.loc['OP_REFINED_K7', 'holdout_2025_races'])}",
            "",
            "## Bottom Line",
            "",
            "- Green here means the active cross-family shortlist is still pinned to the frozen 2024-2025 holdout standard, the saved CSV/markdown surfaces still rebuild cleanly from source, and the current paper-hierarchy ordering still says OP_DURABLE_K7 first, CD_CORE_K8 second, OP_REFINED_K7 third.",
            "- It does not mean a smaller-sample challenger quietly earned promotion or that a different holdout window became the new standard.",
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
