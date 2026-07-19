#!/usr/bin/env python3
"""
Validation for the portfolio decision card.

Purpose:
- keep the top-level portfolio decision artifact reproducible
- pin the saved CSV / markdown surfaces against a fresh rebuild
- pin the real CLI stdout report plus save notices
- pin the current PAPER NOW / SHADOW ONLY / BENCHMARK ONLY ordering
- make sure the report-facing portfolio card still matches frozen sources
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

import portfolio_decision_card as pdc

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "out" / "status_validation" / "portfolio_decision_card"
OUT_MD = OUT_DIR / "portfolio_decision_card_validation.md"
OUT_JSON = OUT_DIR / "portfolio_decision_card_validation.json"
TMP_PARENT = OUT_DIR / "_tmp"
REBUILD_COMMAND = "python3 validate_portfolio_decision_card.py"
PORTFOLIO_SCRIPT = BASE / "portfolio_decision_card.py"
PORTFOLIO_CSV = BASE / "portfolio_decision_card.csv"
PORTFOLIO_MD = BASE / "PORTFOLIO_DECISION_CARD.md"
COMPARE_CSV = BASE / "compare_main_approaches.csv"
COMPARE_JSON = BASE / "compare_main_approaches.json"
FROZEN_EVAL = BASE / "frozen_portfolio_eval_summary.csv"
WF_FOLDS = BASE / "walk_forward_validation_folds.csv"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
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
        raise AssertionError(f"rebuilt portfolio frame is missing saved columns {missing_cols}")
    rebuilt = rebuilt[saved.columns]
    assert_frame_equal(
        normalize_frame(saved, "method_id"),
        normalize_frame(rebuilt, "method_id"),
        check_dtype=False,
        check_exact=False,
        atol=1e-9,
        rtol=0,
    )


def build_expected_cli_stdout(report_text: str, csv_name: str = "portfolio_decision_card.csv", md_name: str = "PORTFOLIO_DECISION_CARD.md") -> str:
    return report_text + f"Saved: {csv_name}\nSaved: {md_name}\n"


def frozen_portfolio_row(portfolio_name: str, slice_name: str) -> pd.Series:
    df = pd.read_csv(FROZEN_EVAL)
    match = df[(df["level"] == "portfolio") & (df["name"] == portfolio_name) & (df["slice"] == slice_name)]
    if match.empty:
        raise AssertionError(f"Missing frozen portfolio row for {portfolio_name} / {slice_name}")
    return match.iloc[0]


def selector_year_roi(year: int) -> float:
    df = pd.read_csv(WF_FOLDS)
    match = df[df["test_year"] == year]
    if match.empty:
        raise AssertionError(f"Missing walk-forward fold for {year}")
    return float(match.iloc[0]["test_roi"])


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
    expected = pdc.source_file_fingerprints()
    if set(markdown_rows) != set(expected):
        return False
    for label, expected_fingerprint in expected.items():
        if markdown_rows[label] != expected_fingerprint:
            return False
    return True


def load_operator_boundary() -> dict[str, Any]:
    return pdc.load_current_operator_boundary(COMPARE_JSON)


def load_decision_gates() -> dict[str, Any]:
    return pdc.load_decision_change_gate_minimums(COMPARE_JSON)


def load_current_gate_progress() -> dict[str, Any]:
    return pdc.load_current_gate_progress(CURRENT_EVIDENCE_JSON)


def load_scorecard_audit_route() -> dict[str, Any]:
    return pdc.load_scorecard_audit_route(CURRENT_EVIDENCE_JSON)


def load_rebuild_validation_contract() -> dict[str, Any]:
    return pdc.load_rebuild_validation_contract(CURRENT_EVIDENCE_JSON)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_parent = prepare_tmp_parent()
    scratch = {
        "tmp_parent": str(tmp_parent),
        "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
        "tmp_parent_cleared_before_fixture_run": True,
    }

    saved_df = pd.read_csv(PORTFOLIO_CSV)
    rebuilt_df = pdc.build_dataframe()
    compare_like_saved(saved_df, rebuilt_df)
    saved_md = PORTFOLIO_MD.read_text(encoding="utf-8")
    rebuilt_md = pdc.build_markdown(rebuilt_df)
    if not rebuilt_md.endswith("\n"):
        rebuilt_md += "\n"
    operator_boundary = load_operator_boundary()
    current_gate_progress = load_current_gate_progress()
    scorecard_audit_route = load_scorecard_audit_route()
    rebuild_validation_contract = load_rebuild_validation_contract()
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

    df = rebuilt_df.set_index("method_id")
    compare_df = pd.read_csv(COMPARE_CSV).set_index("method_id")

    phase7_holdout = frozen_portfolio_row("phase7_live", "holdout_2024_2025")
    phase8_holdout = frozen_portfolio_row("phase8_frozen", "holdout_2024_2025")
    phase7_2024 = frozen_portfolio_row("phase7_live", "year_2024")
    phase7_2025 = frozen_portfolio_row("phase7_live", "year_2025")
    phase8_2024 = frozen_portfolio_row("phase8_frozen", "year_2024")
    phase8_2025 = frozen_portfolio_row("phase8_frozen", "year_2025")
    selector_2024 = selector_year_roi(2024)
    selector_2025 = selector_year_roi(2025)
    scorecard_ranking_contract = pdc.load_scorecard_ranking_contract(SCORECARD_JSON)
    scorecard_ci_only_diagnostic = pdc.load_scorecard_ci_only_diagnostic(SCORECARD_JSON)
    decision_gates = load_decision_gates()

    checks: list[dict[str, Any]] = []
    checks.append(
        require(
            saved_md == rebuilt_md,
            "markdown_matches_rebuild",
            "PORTFOLIO_DECISION_CARD.md still matches a fresh rebuild from portfolio_decision_card.py",
        )
    )

    with tempfile.TemporaryDirectory(prefix="portfolio_card_cli_", dir=tmp_parent) as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        pinned_dir = tmpdir / "pinned_out"
        pinned_csv = pinned_dir / "portfolio_custom.csv"
        pinned_md = pinned_dir / "PORTFOLIO_CUSTOM.md"
        alt_compare_csv = tmpdir / "alt_compare_main.csv"
        alt_compare_json = tmpdir / "alt_compare_main.json"
        alt_frozen_eval_csv = tmpdir / "alt_frozen_portfolio_eval_summary.csv"
        alt_wf_folds_csv = tmpdir / "alt_walk_forward_validation_folds.csv"
        alt_scorecard_json = tmpdir / "alt_forward_evidence_scorecard.json"
        missing_compare_csv = tmpdir / "missing_train_only_compare_main.csv"
        missing_frozen_eval_csv = tmpdir / "missing_phase8_2025_frozen_eval.csv"
        missing_wf_folds_csv = tmpdir / "missing_2025_wf_folds.csv"
        missing_scorecard_json = tmpdir / "missing_ranking_contract_scorecard.json"
        missing_ci_only_scorecard_json = tmpdir / "missing_ci_only_scorecard.json"
        missing_compare_json = tmpdir / "missing_operator_boundary_compare_main.json"
        bad_generated_at_compare_json = tmpdir / "bad_generated_at_compare_main.json"
        missing_freshness_reference_compare_json = tmpdir / "missing_freshness_reference_compare_main.json"
        false_refresh_boundary_flag_compare_json = tmpdir / "false_refresh_boundary_flag_compare_main.json"
        false_refresh_accounting_flag_compare_json = tmpdir / "false_refresh_accounting_flag_compare_main.json"
        missing_gate_compare_json = tmpdir / "missing_decision_gates_compare_main.json"
        nonpositive_phase8_gate_compare_json = tmpdir / "nonpositive_phase8_decision_gates_compare_main.json"
        nonpositive_real_money_gate_compare_json = tmpdir / "nonpositive_real_money_decision_gates_compare_main.json"
        missing_rebuild_validation_contract_json = tmpdir / "missing_rebuild_validation_contract_current_evidence.json"
        weakened_rebuild_validation_contract_json = tmpdir / "weakened_rebuild_validation_contract_current_evidence.json"
        missing_contract_output_dir = tmpdir / "missing_contract_nested_output" / "artifacts"
        missing_contract_should_not_write_csv = missing_contract_output_dir / "missing_contract_should_not_write.csv"
        missing_contract_should_not_write_md = missing_contract_output_dir / "missing_contract_should_not_write.md"
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
        false_refresh_accounting_should_not_write_csv = (
            false_refresh_accounting_output_dir / "false_refresh_accounting_should_not_write.csv"
        )
        false_refresh_accounting_should_not_write_md = (
            false_refresh_accounting_output_dir / "false_refresh_accounting_should_not_write.md"
        )
        missing_gate_output_dir = tmpdir / "missing_gate_nested_output" / "artifacts"
        missing_gate_should_not_write_csv = missing_gate_output_dir / "missing_gate_should_not_write.csv"
        missing_gate_should_not_write_md = missing_gate_output_dir / "missing_gate_should_not_write.md"
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
            PORTFOLIO_SCRIPT,
            COMPARE_CSV,
            COMPARE_JSON,
            FROZEN_EVAL,
            WF_FOLDS,
            SCORECARD_JSON,
            CURRENT_EVIDENCE_JSON,
            SCORECARD_AUDIT_MD,
            SCORECARD_AUDIT_JSON,
        ]:
            shutil.copy2(src, tmpdir / src.name)
        shutil.copy2(COMPARE_CSV, alt_compare_csv)
        shutil.copy2(COMPARE_JSON, alt_compare_json)
        shutil.copy2(FROZEN_EVAL, alt_frozen_eval_csv)
        shutil.copy2(WF_FOLDS, alt_wf_folds_csv)
        shutil.copy2(SCORECARD_JSON, alt_scorecard_json)
        cli_result = subprocess.run(
            [sys.executable, PORTFOLIO_SCRIPT.name],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        cli_csv = pd.read_csv(tmpdir / PORTFOLIO_CSV.name)
        compare_like_saved(saved_df, cli_csv)
        cli_report_text = (tmpdir / PORTFOLIO_MD.name).read_text(encoding="utf-8")
        if cli_report_text != rebuilt_md:
            raise AssertionError("CLI-generated PORTFOLIO_DECISION_CARD.md drifted from a fresh rebuild")
        expected_cli_stdout = build_expected_cli_stdout(cli_report_text)
        if cli_result.stdout != expected_cli_stdout:
            raise AssertionError("portfolio_decision_card.py CLI stdout no longer matches its generated report plus save notices")

        pinned_result = subprocess.run(
            [
                sys.executable,
                PORTFOLIO_SCRIPT.name,
                "--compare-csv",
                str(alt_compare_csv),
                "--compare-json",
                str(alt_compare_json),
                "--frozen-eval-csv",
                str(alt_frozen_eval_csv),
                "--wf-folds-csv",
                str(alt_wf_folds_csv),
                "--scorecard-json",
                str(alt_scorecard_json),
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
        pinned_rebuilt_md = pdc.build_markdown(
            pdc.build_dataframe(
                compare_path=alt_compare_csv,
                frozen_eval_path=alt_frozen_eval_csv,
                wf_folds_path=alt_wf_folds_csv,
            ),
            compare_csv_name=alt_compare_csv.name,
            compare_json_name=alt_compare_json.name,
            frozen_eval_csv_name=alt_frozen_eval_csv.name,
            wf_folds_csv_name=alt_wf_folds_csv.name,
            scorecard_json_name=alt_scorecard_json.name,
            csv_output_name=pinned_csv.name,
            md_output_name=pinned_md.name,
            scorecard_json_path=alt_scorecard_json,
            compare_json_path=alt_compare_json,
            current_evidence_json_path=tmpdir / CURRENT_EVIDENCE_JSON.name,
            source_paths={
                "compare_main_approaches": alt_compare_csv,
                "compare_main_approaches_json": alt_compare_json,
                "frozen_portfolio_eval": alt_frozen_eval_csv,
                "walk_forward_folds": alt_wf_folds_csv,
                "forward_evidence_scorecard": alt_scorecard_json,
                "current_evidence_summary": tmpdir / CURRENT_EVIDENCE_JSON.name,
            },
        )
        if not pinned_rebuilt_md.endswith("\n"):
            pinned_rebuilt_md += "\n"
        if pinned_report_text != pinned_rebuilt_md:
            raise AssertionError("Pinned/custom-output PORTFOLIO_DECISION_CARD.md drifted from a fresh rebuild")
        expected_pinned_stdout = build_expected_cli_stdout(pinned_report_text, csv_name=pinned_csv.name, md_name=pinned_md.name)
        if pinned_result.stdout != expected_pinned_stdout:
            raise AssertionError("Pinned/custom-output portfolio_decision_card.py CLI stdout no longer matches its generated report plus save notices")

        missing_compare_df = pd.read_csv(alt_compare_csv)
        missing_compare_df = missing_compare_df[missing_compare_df["method_id"] != "train_only_selector"].copy()
        missing_compare_df.to_csv(missing_compare_csv, index=False)
        missing_compare_result = subprocess.run(
            [sys.executable, PORTFOLIO_SCRIPT.name, "--compare-csv", str(missing_compare_csv)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_compare_result.returncode == 0:
            raise AssertionError("portfolio_decision_card.py unexpectedly accepted compare_main_approaches.csv without train_only_selector")
        missing_compare_text = f"{missing_compare_result.stdout}\n{missing_compare_result.stderr}"
        if "missing required compare-main method rows: train_only_selector" not in missing_compare_text:
            raise AssertionError("compare-main failure no longer explains that train_only_selector is required for the portfolio card")

        missing_frozen_df = pd.read_csv(alt_frozen_eval_csv)
        missing_frozen_df = missing_frozen_df[
            ~((missing_frozen_df["level"] == "portfolio") & (missing_frozen_df["name"] == "phase8_frozen") & (missing_frozen_df["slice"] == "year_2025"))
        ].copy()
        missing_frozen_df.to_csv(missing_frozen_eval_csv, index=False)
        missing_frozen_result = subprocess.run(
            [sys.executable, PORTFOLIO_SCRIPT.name, "--frozen-eval-csv", str(missing_frozen_eval_csv)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_frozen_result.returncode == 0:
            raise AssertionError("portfolio_decision_card.py unexpectedly accepted frozen portfolio eval data without phase8_frozen/year_2025")
        missing_frozen_text = f"{missing_frozen_result.stdout}\n{missing_frozen_result.stderr}"
        if "missing required frozen portfolio rows: phase8_frozen/year_2025" not in missing_frozen_text:
            raise AssertionError("frozen-eval failure no longer explains that phase8_frozen/year_2025 is required for the portfolio card")

        missing_wf_df = pd.read_csv(alt_wf_folds_csv)
        missing_wf_df = missing_wf_df[missing_wf_df["test_year"] != 2025].copy()
        missing_wf_df.to_csv(missing_wf_folds_csv, index=False)
        missing_wf_result = subprocess.run(
            [sys.executable, PORTFOLIO_SCRIPT.name, "--wf-folds-csv", str(missing_wf_folds_csv)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_wf_result.returncode == 0:
            raise AssertionError("portfolio_decision_card.py unexpectedly accepted walk_forward_validation_folds.csv without 2025")
        missing_wf_text = f"{missing_wf_result.stdout}\n{missing_wf_result.stderr}"
        if "missing required walk-forward year rows: 2025" not in missing_wf_text:
            raise AssertionError("walk-forward failure no longer explains that 2025 is required for the portfolio card")

        missing_contract_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        missing_contract_payload.pop("ranking_contract", None)
        missing_scorecard_json.write_text(json.dumps(missing_contract_payload, indent=2) + "\n", encoding="utf-8")
        missing_scorecard_json_result = subprocess.run(
            [
                sys.executable,
                PORTFOLIO_SCRIPT.name,
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
            raise AssertionError("portfolio_decision_card.py unexpectedly accepted a scorecard JSON missing ranking_contract")
        missing_scorecard_json_text = f"{missing_scorecard_json_result.stdout}\n{missing_scorecard_json_result.stderr}"
        if "missing ranking_contract" not in missing_scorecard_json_text:
            raise AssertionError("scorecard JSON failure no longer explains that ranking_contract is required for the portfolio card")
        if missing_contract_output_dir.exists() or missing_contract_should_not_write_csv.exists() or missing_contract_should_not_write_md.exists():
            raise AssertionError("missing scorecard ranking-contract failure created output directories or wrote partial portfolio artifacts before failing")

        missing_ci_only_payload = json.loads(alt_scorecard_json.read_text(encoding="utf-8"))
        missing_ci_only_payload.pop("ci_only_promotion_diagnostics", None)
        missing_ci_only_scorecard_json.write_text(json.dumps(missing_ci_only_payload, indent=2) + "\n", encoding="utf-8")
        missing_ci_only_result = subprocess.run(
            [
                sys.executable,
                PORTFOLIO_SCRIPT.name,
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
            raise AssertionError("portfolio_decision_card.py unexpectedly accepted a scorecard JSON missing ci_only_promotion_diagnostics")
        missing_ci_only_text = f"{missing_ci_only_result.stdout}\n{missing_ci_only_result.stderr}"
        if "missing ci_only_promotion_diagnostics" not in missing_ci_only_text:
            raise AssertionError("scorecard JSON failure no longer explains that ci_only_promotion_diagnostics is required for the portfolio card")
        if missing_ci_only_output_dir.exists() or missing_ci_only_should_not_write_csv.exists() or missing_ci_only_should_not_write_md.exists():
            raise AssertionError("missing CI-only diagnostic failure created output directories or wrote partial portfolio artifacts before failing")

        missing_compare_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        missing_compare_payload.pop("current_operator_boundary", None)
        missing_compare_json.write_text(json.dumps(missing_compare_payload, indent=2) + "\n", encoding="utf-8")
        missing_compare_json_result = subprocess.run(
            [
                sys.executable,
                PORTFOLIO_SCRIPT.name,
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
            raise AssertionError("portfolio_decision_card.py unexpectedly accepted compare_main_approaches.json without current_operator_boundary")
        missing_compare_json_text = f"{missing_compare_json_result.stdout}\n{missing_compare_json_result.stderr}"
        if "missing current_operator_boundary" not in missing_compare_json_text:
            raise AssertionError("compare-main JSON failure no longer explains that current_operator_boundary is required for the portfolio card")
        if missing_operator_output_dir.exists() or missing_operator_should_not_write_csv.exists() or missing_operator_should_not_write_md.exists():
            raise AssertionError("missing current-operator boundary failure created output directories or wrote partial portfolio artifacts before failing")

        bad_generated_at_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        bad_generated_at_payload["current_operator_boundary"]["generated_at"] = "2026-06-26T18:12:48"
        bad_generated_at_compare_json.write_text(json.dumps(bad_generated_at_payload, indent=2) + "\n", encoding="utf-8")
        bad_generated_at_result = subprocess.run(
            [
                sys.executable,
                PORTFOLIO_SCRIPT.name,
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
            raise AssertionError("portfolio_decision_card.py unexpectedly accepted a timezone-naive current_operator_boundary.generated_at")
        bad_generated_at_text = f"{bad_generated_at_result.stdout}\n{bad_generated_at_result.stderr}"
        if "current_operator_boundary generated_at must be timezone-aware ISO provenance metadata" not in bad_generated_at_text:
            raise AssertionError("compare-main JSON failure no longer explains that current_operator_boundary.generated_at must be timezone-aware")
        if bad_generated_at_output_dir.exists() or bad_generated_at_should_not_write_csv.exists() or bad_generated_at_should_not_write_md.exists():
            raise AssertionError("bad current-operator generated_at failure created output directories or wrote partial portfolio artifacts before failing")

        missing_freshness_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        missing_freshness_payload["current_operator_boundary"].pop("source_freshness_generated_reference_date", None)
        missing_freshness_reference_compare_json.write_text(json.dumps(missing_freshness_payload, indent=2) + "\n", encoding="utf-8")
        missing_freshness_result = subprocess.run(
            [
                sys.executable,
                PORTFOLIO_SCRIPT.name,
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
            raise AssertionError("portfolio_decision_card.py unexpectedly accepted compare_main_approaches.json without current_operator_boundary.source_freshness_generated_reference_date")
        missing_freshness_text = f"{missing_freshness_result.stdout}\n{missing_freshness_result.stderr}"
        if "current_operator_boundary is missing fields: source_freshness_generated_reference_date" not in missing_freshness_text:
            raise AssertionError("compare-main JSON failure no longer explains that current_operator_boundary.source_freshness_generated_reference_date is required")
        if missing_freshness_output_dir.exists() or missing_freshness_should_not_write_csv.exists() or missing_freshness_should_not_write_md.exists():
            raise AssertionError("missing current-operator freshness-reference failure created output directories or wrote partial portfolio artifacts before failing")

        false_refresh_boundary_flag_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        false_refresh_boundary_flag_payload["current_operator_boundary"]["refresh_boundary_not_real_money_evidence"] = False
        false_refresh_boundary_flag_compare_json.write_text(json.dumps(false_refresh_boundary_flag_payload, indent=2) + "\n", encoding="utf-8")
        false_refresh_boundary_result = subprocess.run(
            [
                sys.executable,
                PORTFOLIO_SCRIPT.name,
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
            raise AssertionError("portfolio_decision_card.py unexpectedly accepted current_operator_boundary.refresh_boundary_not_real_money_evidence=false")
        false_refresh_boundary_text = f"{false_refresh_boundary_result.stdout}\n{false_refresh_boundary_result.stderr}"
        if "current_operator_boundary must mark refresh_boundary_not_real_money_evidence=true" not in false_refresh_boundary_text:
            raise AssertionError("compare-main JSON failure no longer explains that refresh_boundary_not_real_money_evidence must remain true")
        if (
            false_refresh_boundary_output_dir.exists()
            or false_refresh_boundary_should_not_write_csv.exists()
            or false_refresh_boundary_should_not_write_md.exists()
        ):
            raise AssertionError("false refresh-boundary flag failure created output directories or wrote partial portfolio artifacts before failing")

        false_refresh_accounting_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        false_refresh_accounting_payload["current_operator_boundary"][
            "clean_empty_refresh_counts_as_forward_performance"
        ] = True
        false_refresh_accounting_flag_compare_json.write_text(
            json.dumps(false_refresh_accounting_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        false_refresh_accounting_result = subprocess.run(
            [
                sys.executable,
                PORTFOLIO_SCRIPT.name,
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
            raise AssertionError("portfolio_decision_card.py unexpectedly accepted current_operator_boundary.clean_empty_refresh_counts_as_forward_performance=true")
        false_refresh_accounting_text = f"{false_refresh_accounting_result.stdout}\n{false_refresh_accounting_result.stderr}"
        if "current_operator_boundary must preserve clean_empty_refresh_counts_as_forward_performance=false" not in false_refresh_accounting_text:
            raise AssertionError("compare-main JSON failure no longer explains that clean empty wrapper refreshes cannot count as forward performance")
        if (
            false_refresh_accounting_output_dir.exists()
            or false_refresh_accounting_should_not_write_csv.exists()
            or false_refresh_accounting_should_not_write_md.exists()
        ):
            raise AssertionError("false refresh-accounting flag failure created output directories or wrote partial portfolio artifacts before failing")

        missing_gate_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        missing_gate_payload.pop("decision_change_gate_minimums", None)
        missing_gate_compare_json.write_text(json.dumps(missing_gate_payload, indent=2) + "\n", encoding="utf-8")
        missing_gate_result = subprocess.run(
            [
                sys.executable,
                PORTFOLIO_SCRIPT.name,
                "--compare-json",
                str(missing_gate_compare_json),
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
            raise AssertionError("portfolio_decision_card.py unexpectedly accepted compare_main_approaches.json without decision_change_gate_minimums")
        missing_gate_text = f"{missing_gate_result.stdout}\n{missing_gate_result.stderr}"
        if "missing decision_change_gate_minimums" not in missing_gate_text:
            raise AssertionError("compare-main JSON failure no longer explains that decision_change_gate_minimums is required for the portfolio card")
        if missing_gate_output_dir.exists() or missing_gate_should_not_write_csv.exists() or missing_gate_should_not_write_md.exists():
            raise AssertionError("missing decision-gate failure created output directories or wrote partial portfolio artifacts before failing")

        nonpositive_phase8_gate_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        nonpositive_phase8_gate_payload["decision_change_gate_minimums"]["phase8_promotion_review"][
            "minimum_roi_complete_settled_observations"
        ] = 0
        nonpositive_phase8_gate_compare_json.write_text(
            json.dumps(nonpositive_phase8_gate_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        nonpositive_phase8_gate_result = subprocess.run(
            [
                sys.executable,
                PORTFOLIO_SCRIPT.name,
                "--compare-json",
                str(nonpositive_phase8_gate_compare_json),
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
            raise AssertionError("portfolio_decision_card.py unexpectedly accepted a non-positive phase8_promotion_review gate floor")
        nonpositive_phase8_gate_text = f"{nonpositive_phase8_gate_result.stdout}\n{nonpositive_phase8_gate_result.stderr}"
        if (
            "decision_change_gate_minimums.phase8_promotion_review.minimum_roi_complete_settled_observations must be a positive integer"
            not in nonpositive_phase8_gate_text
        ):
            raise AssertionError("non-positive Phase 8 gate failure no longer names the malformed decision_change_gate_minimums threshold")
        if (
            nonpositive_phase8_gate_output_dir.exists()
            or nonpositive_phase8_gate_should_not_write_csv.exists()
            or nonpositive_phase8_gate_should_not_write_md.exists()
        ):
            raise AssertionError("non-positive Phase 8 decision-gate failure created output directories or wrote partial portfolio artifacts before failing")

        nonpositive_real_money_gate_payload = json.loads(alt_compare_json.read_text(encoding="utf-8"))
        nonpositive_real_money_gate_payload["decision_change_gate_minimums"]["real_money_discussion"][
            "minimum_total_settled_roi_complete_observations"
        ] = 0
        nonpositive_real_money_gate_compare_json.write_text(
            json.dumps(nonpositive_real_money_gate_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        nonpositive_real_money_gate_result = subprocess.run(
            [
                sys.executable,
                PORTFOLIO_SCRIPT.name,
                "--compare-json",
                str(nonpositive_real_money_gate_compare_json),
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
            raise AssertionError("portfolio_decision_card.py unexpectedly accepted a non-positive real_money_discussion gate floor")
        nonpositive_real_money_gate_text = (
            f"{nonpositive_real_money_gate_result.stdout}\n{nonpositive_real_money_gate_result.stderr}"
        )
        if (
            "decision_change_gate_minimums.real_money_discussion.minimum_total_settled_roi_complete_observations must be a positive integer"
            not in nonpositive_real_money_gate_text
        ):
            raise AssertionError("non-positive real-money gate failure no longer names the malformed decision_change_gate_minimums threshold")
        if (
            nonpositive_real_money_gate_output_dir.exists()
            or nonpositive_real_money_gate_should_not_write_csv.exists()
            or nonpositive_real_money_gate_should_not_write_md.exists()
        ):
            raise AssertionError("non-positive real-money decision-gate failure created output directories or wrote partial portfolio artifacts before failing")

        missing_rebuild_payload = json.loads((tmpdir / CURRENT_EVIDENCE_JSON.name).read_text(encoding="utf-8"))
        missing_rebuild_payload.pop("rebuild_validation_contract", None)
        missing_rebuild_validation_contract_json.write_text(
            json.dumps(missing_rebuild_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_rebuild_validation_contract_result = subprocess.run(
            [
                sys.executable,
                PORTFOLIO_SCRIPT.name,
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
                "portfolio_decision_card.py unexpectedly accepted current_evidence_summary.json without rebuild_validation_contract"
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
                "missing rebuild-validation-contract failure created output directories or wrote partial portfolio artifacts before failing"
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
                PORTFOLIO_SCRIPT.name,
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
                "portfolio_decision_card.py unexpectedly accepted current_evidence_summary.json with a weakened rebuild_validation_contract"
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
                "weakened rebuild-validation-contract failure created output directories or wrote partial portfolio artifacts before failing"
            )

    checks.append(
        require(
            True,
            "cli_csv_matches_saved",
            "portfolio_decision_card.py CLI still writes a CSV that matches the saved portfolio decision table",
        )
    )
    checks.append(
        require(
            True,
            "cli_markdown_matches_rebuild",
            "portfolio_decision_card.py CLI still writes PORTFOLIO_DECISION_CARD.md exactly as a fresh rebuild renders it",
        )
    )
    checks.append(
        require(
            True,
            "cli_stdout_matches_generated_report",
            "portfolio_decision_card.py CLI stdout still matches the generated report plus its Saved: lines",
        )
    )
    checks.append(
        require(
            tmp_parent.is_relative_to(BASE) and tmp_parent.exists(),
            "cli_scratch_root_project_local",
            "portfolio_decision_card.py CLI fixture now writes temporary rebuild, custom-source, and negative-test files under the project-local status-validation scratch root, and that scratch root is cleared before each fixture run",
        )
    )
    checks.append(
        require(
            scratch["tmp_parent_is_project_local"] is True
            and scratch["tmp_parent_cleared_before_fixture_run"] is True
            and Path(scratch["tmp_parent"]) == tmp_parent,
            "cli_scratch_metadata_published",
            "portfolio decision-card validation publishes top-level project-local scratch metadata so parent rollups can verify the cleared fixture root without parsing prose",
        )
    )
    checks.append(
        require(
            True,
            "cli_custom_source_and_output_paths",
            "portfolio_decision_card.py can now rerender from explicit compare-main / frozen-eval / walk-forward source paths and write to custom output paths without depending on the default saved portfolio artifact names",
        )
    )
    checks.append(
        require(
            True,
            "missing_compare_method_fails_fast",
            "the real portfolio-card CLI now fails fast if compare_main_approaches.csv loses train_only_selector instead of quietly weakening the benchmark lane",
        )
    )
    checks.append(
        require(
            True,
            "missing_frozen_year_slice_fails_fast",
            "the real portfolio-card CLI now fails fast if the frozen phase8_frozen/year_2025 slice disappears instead of quietly softening the split-aware caution surface",
        )
    )
    checks.append(
        require(
            True,
            "missing_walk_forward_year_fails_fast",
            "the real portfolio-card CLI now fails fast if the walk-forward folds lose 2025 instead of quietly degrading the train-only benchmark split",
        )
    )
    checks.append(
        require(
            True,
            "missing_scorecard_ranking_contract_fails_fast",
            "the real portfolio-card CLI now fails fast without creating output directories or writing CSV/markdown artifacts if the scorecard JSON loses ranking_contract instead of silently dropping tier-first ranking semantics",
        )
    )
    checks.append(
        require(
            True,
            "missing_scorecard_ci_only_diagnostic_fails_fast",
            "the real portfolio-card CLI now fails fast without creating output directories or writing CSV/markdown artifacts if the scorecard JSON loses ci_only_promotion_diagnostics instead of silently dropping the OP_REFINED CI-only promotion boundary",
        )
    )
    checks.append(
        require(
            True,
            "missing_operator_boundary_fails_fast",
            "the real portfolio-card CLI now fails fast without creating output directories or writing CSV/markdown artifacts if compare_main_approaches.json loses current_operator_boundary instead of silently dropping the current paper-workflow boundary",
        )
    )
    checks.append(
        require(
            True,
            "bad_current_operator_generated_at_fails_fast",
            "the real portfolio-card CLI now fails fast without creating output directories or writing CSV/markdown artifacts if compare_main_approaches.json carries a timezone-naive current_operator_boundary.generated_at instead of republishing malformed current-paper provenance",
        )
    )
    checks.append(
        require(
            True,
            "missing_current_operator_freshness_reference_fails_fast",
            "the real portfolio-card CLI now fails fast without creating output directories or writing CSV/markdown artifacts if compare_main_approaches.json loses current_operator_boundary.source_freshness_generated_reference_date instead of publishing a detached current-paper freshness read",
        )
    )
    checks.append(
        require(
            True,
            "false_current_operator_refresh_not_real_money_flag_fails_fast",
            "the real portfolio-card CLI now fails fast without creating output directories or writing CSV/markdown artifacts if compare_main_approaches.json marks current_operator_boundary.refresh_boundary_not_real_money_evidence=false instead of republishing weakened current-paper provenance",
        )
    )
    checks.append(
        require(
            True,
            "false_current_operator_clean_empty_refresh_accounting_fails_fast",
            "the real portfolio-card CLI now fails fast without creating output directories or writing CSV/markdown artifacts if compare_main_approaches.json marks current_operator_boundary.clean_empty_refresh_counts_as_forward_performance=true instead of republishing weakened current-paper provenance",
        )
    )
    checks.append(
        require(
            True,
            "missing_decision_gate_minimums_fails_fast",
            "the real portfolio-card CLI now fails fast without creating output directories or writing CSV/markdown artifacts if compare_main_approaches.json loses decision_change_gate_minimums or carries non-positive Phase 8 / real-money copied floors instead of silently dropping or weakening the scorecard-sourced posture gates",
        )
    )
    checks.append(
        require(
            True,
            "missing_rebuild_validation_contract_fails_fast",
            "the real portfolio-card CLI now fails fast without creating output directories or writing CSV/markdown artifacts if current_evidence_summary.json loses rebuild_validation_contract or weakens its provenance-only flag instead of silently dropping or overstating the settlement-audit -> current-bridge -> bridge-validator route before quoting current totals",
        )
    )
    checks.append(
        require(
            scorecard_ranking_contract.get("rank_is_tier_first_decision_order") is True
            and scorecard_ranking_contract.get("forward_trust_is_secondary_within_tier") is True
            and scorecard_ranking_contract.get("raw_score_is_not_an_automatic_deployment_instruction") is True
            and "CD_CORE_K8 ranks ahead of OP_REFINED_K7" in str(scorecard_ranking_contract.get("known_rank_override") or "")
            and "Inherited scorecard ranking contract:" in saved_md
            and f"`valid_evidence_scope={pdc.VALID_EVIDENCE_SCOPE}`" in saved_md
            and "Scorecard rank-contract override: CD_CORE_K8 ranks ahead of OP_REFINED_K7" in saved_md
            and "raw Score cannot turn a shadow Phase 8 / OP_REFINED line into an automatic promotion cue" in saved_md
            and "`forward_evidence_scorecard.json`" in saved_md,
            "scorecard_ranking_contract_inherited",
            "PORTFOLIO_DECISION_CARD.md now consumes forward_evidence_scorecard.json ranking_contract and publishes the source valid_evidence_scope line so the Phase 7 / Phase 8 / selector portfolio read inherits tier-first score semantics and cannot treat a shadow OP_REFINED line as an automatic promotion cue",
        )
    )
    checks.append(
        require(
            scorecard_ci_only_diagnostic["candidate_rule_id"] == "OP_REFINED_K7"
            and scorecard_ci_only_diagnostic["current_anchor_rule_id"] == "OP_DURABLE_K7"
            and scorecard_ci_only_diagnostic["ci_only_promotion_allowed"] is False
            and "- **Scorecard CI-only promotion check:** `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` says `ci_only_promotion_allowed=false`; the positive OP_REFINED CI lower bound is support context only, not a portfolio-level Phase 8 default trigger." in saved_md
            and "## Scorecard CI-Only Promotion Check" in saved_md
            and "Source: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7`" in saved_md
            and "- Current decision: Keep OP_REFINED_K7 shadow/watch only." in saved_md
            and "- CI-only promotion allowed: `false`" in saved_md
            and "uncleared phase8_promotion_review paper-observation gate" in saved_md
            and "uncleared anchor_displacement paper-observation gate" in saved_md
            and "Does not count: positive bootstrap CI lower bound by itself" in saved_md,
            "scorecard_ci_only_diagnostic_inherited",
            "PORTFOLIO_DECISION_CARD.md now consumes the OP_REFINED scorecard CI-only diagnostic so a positive bootstrap lower bound stays support context only rather than a portfolio-level Phase 8 default trigger",
        )
    )
    checks.append(
        require(
            "## Source Provenance" in saved_md
            and "Exact input-byte fingerprints for this portfolio card." in saved_md
            and "they do not prove settled paper ROI, promotion readiness, live profitability, or real-money performance." in saved_md
            and source_provenance_matches_disk(saved_md),
            "source_provenance_markdown_matches_disk",
            "PORTFOLIO_DECISION_CARD.md now fingerprints compare-main CSV/JSON, frozen portfolio, walk-forward, scorecard, and current-evidence bridge inputs, with markdown byte counts and SHA-256 values matching current disk files",
        )
    )
    checks.append(
        require(
            "## Current Operator Boundary" in saved_md
            and f"This context is inherited from `{COMPARE_JSON.name}` / `{operator_boundary['source_path']}`" in saved_md
            and f"bridge reference = `{operator_boundary['source_freshness_generated_reference_date']}` (`{operator_boundary['source_freshness_generated_reference_timezone']}`)" in saved_md
            and f"comparison = `{operator_boundary['source_freshness_staleness_comparison_source']}` / `{operator_boundary['source_freshness_staleness_comparison_date']}`" in saved_md
            and pdc.md_cell(operator_boundary["source_freshness_read"]) in saved_md
            and "| Operator read gate |" in saved_md
            and f"`{COMPARE_JSON.name}` `current_operator_boundary.operator_read_gate`" in saved_md
            and pdc.md_cell(operator_read_gate["read"]) in saved_md
            and operator_read_gate_branch_ok
            and operator_read_gate["current_top_card_counts_as_no_target_evidence"] is False
            and operator_read_gate["current_top_card_counts_as_clean_empty_evidence"] is False
            and operator_read_gate["current_top_card_counts_as_bet_readiness_evidence"] is False
            and operator_read_gate["current_top_card_counts_as_settled_roi_evidence"] is False
            and "| Primary first-read gate |" not in saved_md
            and "| Bridge-published gate progress |" in saved_md
            and f"`{CURRENT_EVIDENCE_JSON.name}` `decision_gate_progress`" in saved_md
            and pdc.md_cell(current_gate_progress["read"]) in saved_md
            and current_gate_progress.get("gate_status") == "all_uncleared"
            and current_gate_progress.get("all_gates_ready") is False
            and current_gate_progress.get("not_forward_performance_evidence") is True
            and current_gate_progress.get("not_promotion_readiness_evidence") is True
            and current_gate_progress.get("not_live_profitability_evidence") is True
            and current_gate_progress.get("not_real_money_evidence") is True
            and (
                f"| Settlement queue state | `{operator_boundary['open_settlement_queue_state']}`; "
                f"{pdc.md_cell(operator_boundary['open_settlement_context'])}; detail: "
                f"{pdc.md_cell(operator_boundary['open_settlement_queue_read'])} |"
            ) in saved_md
            and "| Open settlement context |" not in saved_md
            and "Settlement queue state:" not in str(operator_boundary.get("open_settlement_queue_read") or "")
            and pdc.md_cell(operator_boundary["recommendation_context_read"]) in saved_md
            and "Latest recommendation-state context is operator routing only, not bet readiness or forward-performance evidence" in saved_md
            and f"`{operator_boundary['best_action_command']}`" in saved_md
            and "The current operator boundary is routing/provenance context only." in saved_md
            and "it is not settled ROI, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence." in saved_md,
            "current_operator_boundary_documented",
            "PORTFOLIO_DECISION_CARD.md now carries the compare-main current-operator boundary plus current_evidence_summary.json decision_gate_progress, including structured freshness provenance, the inherited operator_read_gate, bridge-published gate split, source-published settlement-queue state/context/detail, recommendation-state context, current operator route, and non-performance/no-real-money caveat",
        )
    )
    checks.append(
        require(
            f"`{CURRENT_EVIDENCE_JSON.name}` `scorecard_audit_route`" in saved_md
            and "| Scorecard audit route |" in saved_md
            and pdc.md_cell(scorecard_audit_route["route_read"]) in saved_md
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
            and "Report-synchronization route only; it is not portfolio-ranking evidence, forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in saved_md,
            "scorecard_audit_route_documented",
            "PORTFOLIO_DECISION_CARD.md now republishes current_evidence_summary.json.scorecard_audit_route so copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks point to the dedicated scorecard audit without becoming portfolio-ranking, settled ROI, promotion, live-profitability, bankroll, or real-money evidence",
        )
    )
    checks.append(
        require(
            rebuild_validation_contract["upstream_refresh_commands"] == pdc.REQUIRED_REBUILD_REFRESH_ORDER
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
            and "`python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py`" in saved_md
            and "not portfolio-ranking evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in saved_md,
            "current_evidence_rebuild_validation_contract_documented",
            "PORTFOLIO_DECISION_CARD.md now republishes current_evidence_summary.json.rebuild_validation_contract so source-byte changes route through settlement-audit -> current-bridge -> bridge-validator before anyone quotes current totals from the portfolio card",
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
            "PORTFOLIO_DECISION_CARD.md now republishes compare_main_approaches.json current_operator_boundary.operator_read_gate as branch-aware routing metadata, not no-target, clean-empty, bet-readiness, settled ROI, portfolio-ranking evidence, promotion, live-profitability, bankroll, or real-money evidence",
        )
    )
    checks.append(
        require(
            pdc.has_timezone_aware_timestamp(operator_boundary.get("generated_at")),
            "current_operator_boundary_generated_at_is_timezone_aware",
            f"portfolio card inherits compare-main current_operator_boundary.generated_at={operator_boundary.get('generated_at')!r} as parseable timezone-aware provenance metadata only",
        )
    )
    checks.append(
        require(
            operator_boundary["current_settled_context_is_cd_only"] is True
            and operator_boundary["op_anchor_roi_complete_rows"] == 0
            and operator_boundary["cd_companion_roi_complete_rows"] == operator_boundary["roi_complete_primary_rows"]
            and operator_boundary["refresh_can_update_operator_surfaces"] is True
            and operator_boundary["refresh_can_settle_open_rows_by_itself"] is False
            and operator_boundary["refresh_counts_as_roi_complete_evidence_by_itself"] is False
            and operator_boundary["clean_empty_refresh_counts_as_forward_performance"] is False
            and operator_boundary["refresh_boundary_not_forward_performance_evidence"] is True
            and operator_boundary["refresh_boundary_not_live_profitability_evidence"] is True
            and operator_boundary["refresh_boundary_not_promotion_readiness_evidence"] is True
            and operator_boundary["refresh_boundary_not_real_money_evidence"] is True
            and f"OP_DURABLE_K7={operator_boundary['op_anchor_roi_complete_rows']}; CD_CORE_K8={operator_boundary['cd_companion_roi_complete_rows']}" in saved_md
            and pdc.md_cell(operator_boundary["primary_rule_mix_read"]) in saved_md
            and pdc.md_cell(operator_boundary["refresh_action_boundary_read"]) in saved_md
            and f"clean-empty forward performance = `{operator_boundary['clean_empty_refresh_counts_as_forward_performance']}`" in saved_md
            and "Current settled sample is CD-only context, not OP-anchor forward evidence or a portfolio-ranking change" in saved_md
            and "Wrapper refresh can update operator surfaces, but it cannot settle rows, create ROI-complete evidence, promote OP_DURABLE_K7, count clean-empty refreshes as performance, or support live-profitability / real-money claims" in saved_md,
            "current_operator_rule_mix_and_refresh_boundary_documented",
            "PORTFOLIO_DECISION_CARD.md republishes compare-main's current rule-mix and stale-card refresh boundary, keeping 0 OP_DURABLE_K7 settled rows, the current CD_CORE_K8 settled count, and wrapper refreshes / clean-empty refreshes separate from OP-anchor proof, portfolio-ranking changes, promotion readiness, live profitability, bankroll guidance, and real-money evidence",
        )
    )
    checks.append(
        require(
            "## Decision Gate Source" in saved_md
            and f"These gate minimums are inherited from `{COMPARE_JSON.name}` `decision_change_gate_minimums`" in saved_md
            and decision_gates["phase8_promotion_review"]["minimum_roi_complete_settled_observations"] == 20
            and decision_gates["anchor_displacement"]["minimum_roi_complete_same_candidate_observations"] == 30
            and decision_gates["real_money_discussion"]["minimum_total_settled_roi_complete_observations"] == 100
            and decision_gates["phase8_promotion_review"]["threshold_source"] == "forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations"
            and decision_gates["anchor_displacement"]["threshold_source"] == "forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations"
            and decision_gates["real_money_discussion"]["threshold_source"] == "forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi"
            and "| phase8_promotion_review | 20 ROI-complete settled shadow observations |" in saved_md
            and "| anchor_displacement | 30 ROI-complete same-candidate paper observations |" in saved_md
            and "| real_money_discussion | 100 total settled observations with usable ROI |" in saved_md
            and "The 20-row Phase 8 promotion-review gate is not the 30-row anchor-displacement gate, and the 100-row real-money discussion floor is not bankroll guidance." in saved_md,
            "decision_gate_minimums_documented",
            "PORTFOLIO_DECISION_CARD.md now inherits the scorecard-sourced compare-main decision_change_gate_minimums bundle, preserving the 20 Phase 8 review / 30 anchor-displacement / 100 real-money-discussion thresholds and exact threshold_source keys",
        )
    )
    checks.append(
        require(
            df.loc["phase7_live_portfolio", "role"] == "PAPER NOW"
            and df.loc["phase8_frozen_portfolio", "role"] == "SHADOW ONLY"
            and df.loc["train_only_selector", "role"] == "BENCHMARK ONLY",
            "portfolio_roles",
            "portfolio card still orders the three main approaches as PAPER NOW / SHADOW ONLY / BENCHMARK ONLY",
        )
    )

    for method_id in ["phase7_live_portfolio", "phase8_frozen_portfolio", "train_only_selector"]:
        checks.append(
            require(
                abs(float(df.loc[method_id, "holdout_roi"]) - float(compare_df.loc[method_id, "holdout_roi"])) < 1e-9
                and int(df.loc[method_id, "holdout_races"]) == int(compare_df.loc[method_id, "holdout_races"])
                and abs(float(df.loc[method_id, "holdout_2024_roi"]) - float(compare_df.loc[method_id, "holdout_2024_roi"])) < 1e-9
                and int(df.loc[method_id, "holdout_2024_races"]) == int(compare_df.loc[method_id, "holdout_2024_races"])
                and abs(float(df.loc[method_id, "holdout_2025_roi"]) - float(compare_df.loc[method_id, "holdout_2025_roi"])) < 1e-9
                and int(df.loc[method_id, "holdout_2025_races"]) == int(compare_df.loc[method_id, "holdout_2025_races"])
                and abs(float(df.loc[method_id, "wf_roi"]) - float(compare_df.loc[method_id, "wf_roi"])) < 1e-9
                and int(df.loc[method_id, "wf_races"]) == int(compare_df.loc[method_id, "wf_races"])
                and str(df.loc[method_id, "secondary_basis"]) == str(compare_df.loc[method_id, "secondary_basis"])
                and str(df.loc[method_id, "role"]) == str(compare_df.loc[method_id, "deployment_posture"]),
                f"{method_id}_matches_compare_main",
                f"{method_id} portfolio-card row still matches compare_main_approaches.csv, including deployment posture, secondary-basis labeling, and holdout year split counts",
            )
        )

    checks.append(
        require(
            abs(float(df.loc["phase7_live_portfolio", "holdout_roi"]) - float(phase7_holdout["roi"])) < 1e-9
            and int(df.loc["phase7_live_portfolio", "holdout_races"]) == int(phase7_holdout["races"]),
            "phase7_matches_frozen_holdout",
            "Phase 7 portfolio row still matches the frozen 2024-2025 portfolio holdout",
        )
    )
    checks.append(
        require(
            abs(float(df.loc["phase8_frozen_portfolio", "holdout_roi"]) - float(phase8_holdout["roi"])) < 1e-9
            and int(df.loc["phase8_frozen_portfolio", "holdout_races"]) == int(phase8_holdout["races"]),
            "phase8_matches_frozen_holdout",
            "Phase 8 portfolio row still matches the frozen 2024-2025 portfolio holdout",
        )
    )
    checks.append(
        require(
            abs(float(df.loc["phase7_live_portfolio", "holdout_2024_roi"]) - float(phase7_2024["roi"])) < 1e-9
            and int(df.loc["phase7_live_portfolio", "holdout_2024_races"]) == int(compare_df.loc["phase7_live_portfolio", "holdout_2024_races"])
            and abs(float(df.loc["phase7_live_portfolio", "holdout_2025_roi"]) - float(phase7_2025["roi"])) < 1e-9
            and int(df.loc["phase7_live_portfolio", "holdout_2025_races"]) == int(compare_df.loc["phase7_live_portfolio", "holdout_2025_races"]),
            "phase7_year_slices",
            "Phase 7 card row still matches the frozen 2024 and 2025 portfolio slices plus their race counts",
        )
    )
    checks.append(
        require(
            abs(float(df.loc["phase8_frozen_portfolio", "holdout_2024_roi"]) - float(phase8_2024["roi"])) < 1e-9
            and int(df.loc["phase8_frozen_portfolio", "holdout_2024_races"]) == int(compare_df.loc["phase8_frozen_portfolio", "holdout_2024_races"])
            and abs(float(df.loc["phase8_frozen_portfolio", "holdout_2025_roi"]) - float(phase8_2025["roi"])) < 1e-9
            and int(df.loc["phase8_frozen_portfolio", "holdout_2025_races"]) == int(compare_df.loc["phase8_frozen_portfolio", "holdout_2025_races"]),
            "phase8_year_slices",
            "Phase 8 card row still matches the frozen 2024 and 2025 portfolio slices plus their race counts",
        )
    )
    checks.append(
        require(
            abs(float(df.loc["train_only_selector", "holdout_2024_roi"]) - selector_2024) < 1e-9
            and int(df.loc["train_only_selector", "holdout_2024_races"]) == int(compare_df.loc["train_only_selector", "holdout_2024_races"])
            and abs(float(df.loc["train_only_selector", "holdout_2025_roi"]) - selector_2025) < 1e-9
            and int(df.loc["train_only_selector", "holdout_2025_races"]) == int(compare_df.loc["train_only_selector", "holdout_2025_races"]),
            "selector_year_slices",
            "train-only selector row still matches the direct 2024 and 2025 walk-forward fold ROIs plus their race counts",
        )
    )
    checks.append(
        require(
            float(df.loc["phase7_live_portfolio", "holdout_roi"]) > float(df.loc["phase8_frozen_portfolio", "holdout_roi"]) > float(df.loc["train_only_selector", "holdout_roi"]),
            "current_holdout_order",
            "current 2024-2025 holdout ordering still runs Phase 7 first, Phase 8 second, train-only selector third",
        )
    )
    checks.append(
        require(
            float(df.loc["phase8_frozen_portfolio", "holdout_roi_vs_phase7"]) < 0
            and int(df.loc["phase8_frozen_portfolio", "holdout_races_vs_phase7"]) < 0,
            "phase8_stays_shadow",
            "Phase 8 still stays SHADOW ONLY because it trails Phase 7 on both holdout ROI and holdout sample size",
        )
    )
    checks.append(
        require(
            float(df.loc["train_only_selector", "wf_roi"]) > float(df.loc["train_only_selector", "holdout_roi"])
            and float(df.loc["train_only_selector", "holdout_roi_vs_phase7"]) < 0,
            "selector_stays_benchmark",
            "train-only selector still stays BENCHMARK ONLY because its honest WF read is useful, but its current holdout remains weaker than Phase 7",
        )
    )
    checks.append(
        require(
            "daily operating default" in str(df.loc["train_only_selector", "decision_reason"])
            and "best live default" not in saved_md
            and "best live default" not in saved_df.to_csv(index=False),
            "selector_not_best_daily_operating_default_wording",
            "portfolio card now describes the train-only selector as not the best daily operating default, avoiding live-default shorthand in markdown/CSV surfaces",
        )
    )
    checks.append(
        require(
            "| Approach | Role | Holdout ROI | Holdout Races | 2024 ROI / N | 2025 ROI / N | Secondary ROI | Secondary Races | Secondary Years+ | Secondary Basis | Why It Sits Here |" in saved_md
            and "This card is split-aware, not CI-backed at the portfolio level" in saved_md
            and "Inherited scorecard ranking contract:" in saved_md
            and "Unlike the rule-level cards, it does not carry a published portfolio bootstrap CI lower bound from the frozen sources" in saved_md
            and "2024 was basically flat (+0.37% on 109 races) and most of the aggregate holdout edge came from 2025 (+105.38% on 66)" in saved_md
            and "BEL contributes zero 2024-2025 holdout races here, so the Phase 7 holdout read is effectively OP/CD historical evidence." in saved_md
            and "active holdout is effectively the OP+CD portfolio" not in saved_md
            and "Its secondary read is only a frozen replay on the walk-forward test years, not an extra train-only validation layer." in saved_md
            and "its prettier secondary line is also only a frozen replay on the walk-forward test years." in saved_md
            and "Its honest benchmark value comes with a very lopsided recent split (-19.95% on 45 in 2024, +98.37% on 20 in 2025)" in saved_md
            and "Its better replay headline on the walk-forward test years is not enough to offset the weaker current holdout" in saved_md
            and "It also keeps the fixed portfolios from quietly borrowing replay-on-walk-forward-years numbers as if they were extra train-only proof." in saved_md
            and "this note should stay read as a split-aware operating ranking, not as a formal CI-backed proof surface" in saved_md,
            "year_split_counts_documented",
            "portfolio card now shows the 2024/2025 split with race counts, keeps dormant-BEL wording as historical OP/CD holdout evidence rather than active-status wording, and says plainly that the caution surface here is split behavior plus sample support plus whether the secondary line is replay-only or actual train-only context, not a published portfolio-level CI",
        )
    )

    suite_read = (
        f"Paper now=phase7_live_portfolio ({float(df.loc['phase7_live_portfolio', 'holdout_roi']):+.2f}% on {int(df.loc['phase7_live_portfolio', 'holdout_races'])} races; "
        f"2024={float(df.loc['phase7_live_portfolio', 'holdout_2024_roi']):+.2f}% on {int(df.loc['phase7_live_portfolio', 'holdout_2024_races'])}, "
        f"2025={float(df.loc['phase7_live_portfolio', 'holdout_2025_roi']):+.2f}% on {int(df.loc['phase7_live_portfolio', 'holdout_2025_races'])}; no published portfolio CI low in frozen sources); "
        f"shadow only=phase8_frozen_portfolio ({float(df.loc['phase8_frozen_portfolio', 'holdout_roi']):+.2f}% on {int(df.loc['phase8_frozen_portfolio', 'holdout_races'])} races); "
        f"benchmark only=train_only_selector ({float(df.loc['train_only_selector', 'holdout_roi']):+.2f}% holdout, {float(df.loc['train_only_selector', 'wf_roi']):+.2f}% walk-forward); "
        f"scorecard ranking contract inherited=tier-first, raw Score non-promotional ({scorecard_ranking_contract['known_rank_override']}); "
        f"scorecard CI-only diagnostic inherited from forward_evidence_scorecard.json:{pdc.OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY} keeps ci_only_promotion_allowed={str(scorecard_ci_only_diagnostic['ci_only_promotion_allowed']).lower()} so positive OP_REFINED CI support stays out of portfolio-level Phase 8 default readiness; "
        f"bridge-published gate progress from current_evidence_summary.json.decision_gate_progress says {current_gate_progress['read']} with gate_status={current_gate_progress['gate_status']} and all_gates_ready={current_gate_progress['all_gates_ready']}; "
        f"current_evidence_summary.json.rebuild_validation_contract routes source-byte changes through {' -> '.join(rebuild_validation_contract['upstream_refresh_commands'])} before quoting CURRENT_EVIDENCE_SUMMARY.* as provenance/rebuild metadata only, not portfolio-ranking evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence; "
        f"current_evidence_summary.json.scorecard_audit_route points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to {scorecard_audit_route['markdown_path']} / {scorecard_audit_route['json_path']} plus {scorecard_audit_route['validator_command']} as report-synchronization metadata only; "
        f"operator read gate inherited from compare-main says {operator_read_gate['read']} with gate_status={operator_read_gate['gate_status']} and recommended_command={operator_read_gate['recommended_command']}; "
        f"current operator boundary inherited from compare-main JSON names {operator_boundary['roi_complete_primary_rows']}/{operator_boundary['first_read_threshold']} primary ROI-complete rows, settlement-queue state={operator_boundary['open_settlement_queue_state']} / context={operator_boundary['open_settlement_context']}, recommendation-state context={operator_boundary['recommendation_context_read']}, and the current operator route as routing/provenance only rather than settled ROI, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence; "
        f"copied current-operator generated_at={operator_boundary['generated_at']} stays parseable timezone-aware provenance metadata only; "
        f"structured freshness provenance bridge reference={operator_boundary['source_freshness_generated_reference_date']} ({operator_boundary['source_freshness_generated_reference_timezone']}), comparison={operator_boundary['source_freshness_staleness_comparison_source']} / {operator_boundary['source_freshness_staleness_comparison_date']}, read={operator_boundary['source_freshness_read']} stays operator-readiness metadata only; "
        f"current operator rule-mix boundary keeps OP_DURABLE_K7={operator_boundary['op_anchor_roi_complete_rows']} and CD_CORE_K8={operator_boundary['cd_companion_roi_complete_rows']} as CD-only current settled context, while stale-card refresh boundary says {operator_boundary['refresh_action_boundary_read']}, wrapper-counts-as-ROI-evidence={operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}, clean-empty-forward-performance={operator_boundary['clean_empty_refresh_counts_as_forward_performance']}, and remains non-ROI/non-promotion/non-real-money context; "
        f"decision gates inherited from compare-main JSON decision_change_gate_minimums keep phase8_promotion_review={decision_gates['phase8_promotion_review']['minimum_roi_complete_settled_observations']}, anchor_displacement={decision_gates['anchor_displacement']['minimum_roi_complete_same_candidate_observations']}, and real_money_discussion={decision_gates['real_money_discussion']['minimum_total_settled_roi_complete_observations']} scorecard-sourced thresholds separate; "
        "saved CSV, saved markdown, and real CLI stdout stay pinned to the same portfolio decision render; "
        "project-local CLI scratch-root reporting stays pinned"
    )

    payload = {
        "suite_status": "pass",
        "valid_evidence_scope": pdc.VALID_EVIDENCE_SCOPE,
        "artifact": {
            "saved_csv": PORTFOLIO_CSV.name,
            "saved_markdown": PORTFOLIO_MD.name,
            "status": "pass",
            "rows": int(len(saved_df)),
        },
        "scorecard_ranking_contract": scorecard_ranking_contract,
        "scorecard_ranking_contract_source": SCORECARD_JSON.name,
        "scorecard_ci_only_diagnostic": scorecard_ci_only_diagnostic,
        "scorecard_ci_only_diagnostic_source": f"{SCORECARD_JSON.name}:{pdc.OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}",
        "scorecard_audit_route": scorecard_audit_route,
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
        "current_evidence_gate_progress_read": current_gate_progress,
        "current_operator_read_gate": operator_read_gate,
        "scratch": scratch,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "summary": {
            "paper_now": "phase7_live_portfolio",
            "shadow_only": "phase8_frozen_portfolio",
            "benchmark_only": "train_only_selector",
            "benchmark": "train_only_selector",
            "phase7_holdout_roi": float(df.loc["phase7_live_portfolio", "holdout_roi"]),
            "phase8_holdout_roi": float(df.loc["phase8_frozen_portfolio", "holdout_roi"]),
            "selector_holdout_roi": float(df.loc["train_only_selector", "holdout_roi"]),
            "current_operator_boundary": {
                "source_path": operator_boundary["source_path"],
                "generated_at": operator_boundary["generated_at"],
                "source_freshness_generated_reference_date": operator_boundary["source_freshness_generated_reference_date"],
                "source_freshness_generated_reference_timezone": operator_boundary["source_freshness_generated_reference_timezone"],
                "source_freshness_staleness_comparison_source": operator_boundary["source_freshness_staleness_comparison_source"],
                "source_freshness_staleness_comparison_date": operator_boundary["source_freshness_staleness_comparison_date"],
                "source_freshness_read": operator_boundary["source_freshness_read"],
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
                "refresh_action_command": operator_boundary["refresh_action_command"],
                "refresh_action_boundary_read": operator_boundary["refresh_action_boundary_read"],
                "refresh_can_update_operator_surfaces": operator_boundary["refresh_can_update_operator_surfaces"],
                "refresh_can_settle_open_rows_by_itself": operator_boundary["refresh_can_settle_open_rows_by_itself"],
                "refresh_counts_as_roi_complete_evidence_by_itself": operator_boundary["refresh_counts_as_roi_complete_evidence_by_itself"],
                "clean_empty_refresh_counts_as_forward_performance": operator_boundary[
                    "clean_empty_refresh_counts_as_forward_performance"
                ],
                "latest_context_has_no_bet_recommendations": operator_boundary["latest_context_has_no_bet_recommendations"],
                "latest_context_has_no_qualifying_races": operator_boundary["latest_context_has_no_qualifying_races"],
                "latest_context_has_bet_ready_language": operator_boundary["latest_context_has_bet_ready_language"],
                "recommendation_context_read": operator_boundary["recommendation_context_read"],
                "best_action_command": operator_boundary["best_action_command"],
                "not_forward_performance_evidence": operator_boundary["not_forward_performance_evidence"],
                "not_bet_readiness_evidence_by_itself": operator_boundary["not_bet_readiness_evidence_by_itself"],
            },
            "decision_change_gate_minimums": decision_gates,
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
            "scorecard_audit_route_read": {
                "source_path": CURRENT_EVIDENCE_JSON.name,
                "markdown_path": scorecard_audit_route["markdown_path"],
                "json_path": scorecard_audit_route["json_path"],
                "validator_command": scorecard_audit_route["validator_command"],
                "gate_floor_source": scorecard_audit_route["gate_floor_source"],
                "gate_floor_snapshot": scorecard_audit_route["gate_floor_snapshot"],
                "route_read": scorecard_audit_route["route_read"],
                "not_forward_performance_evidence": scorecard_audit_route["not_forward_performance_evidence"],
                "not_settled_roi_evidence": scorecard_audit_route["not_settled_roi_evidence"],
                "not_promotion_readiness_evidence": scorecard_audit_route["not_promotion_readiness_evidence"],
                "not_live_profitability_evidence": scorecard_audit_route["not_live_profitability_evidence"],
                "not_bankroll_guidance": scorecard_audit_route["not_bankroll_guidance"],
                "not_real_money_evidence": scorecard_audit_route["not_real_money_evidence"],
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
            "suite_read": suite_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }

    lines = [
        "# Portfolio Decision Card Validation",
        "",
        "This report validates the main portfolio decision card directly, including the saved CSV and markdown artifacts plus the real CLI stdout report, save notices, inherited scorecard ranking contract, source-provenance fingerprints, current-evidence gate-progress routing, and fail-fast checks for missing compare-main methods, frozen portfolio year slices, walk-forward years, or scorecard ranking-contract JSON.",
        "",
        "## Artifact Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Saved artifacts: `{PORTFOLIO_CSV.name}`, `{PORTFOLIO_MD.name}`",
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
            "- Source-drift guardrail: required compare-main methods, frozen portfolio split rows, and train-only walk-forward years now fail fast instead of degrading into a polished-looking but incomplete portfolio recommendation",
            "- Source provenance: the portfolio markdown fingerprints compare-main CSV/JSON, frozen portfolio, walk-forward, scorecard, and current-evidence bridge inputs and the direct validator compares those byte counts and SHA-256 values to disk.",
            f"- Current gate progress: {current_gate_progress['read']} gate_status={current_gate_progress['gate_status']}; all_gates_ready={current_gate_progress['all_gates_ready']}; this is routing context only, not settled ROI, promotion readiness, live profitability, or real-money evidence.",
            f"- Current bridge rebuild order: current_evidence_summary.json.rebuild_validation_contract routes source-byte changes through {' -> '.join(rebuild_validation_contract['upstream_refresh_commands'])} before quoting CURRENT_EVIDENCE_SUMMARY.*; this is provenance/rebuild metadata only, not portfolio-ranking evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- Scorecard audit route: current_evidence_summary.json.scorecard_audit_route points copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks to {scorecard_audit_route['markdown_path']} / {scorecard_audit_route['json_path']} plus {scorecard_audit_route['validator_command']}; this is report-synchronization metadata only, not settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- valid_evidence_scope={pdc.VALID_EVIDENCE_SCOPE}",
            f"- Current operator boundary: {operator_boundary['roi_complete_primary_rows']}/{operator_boundary['first_read_threshold']} primary ROI-complete rows, settlement-queue state={operator_boundary['open_settlement_queue_state']} / context={operator_boundary['open_settlement_context']}, recommendation-state context={operator_boundary['recommendation_context_read']}; this is routing/provenance only, not settled ROI, bet readiness, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
            f"- Source freshness provenance: bridge reference={operator_boundary['source_freshness_generated_reference_date']} ({operator_boundary['source_freshness_generated_reference_timezone']}), comparison={operator_boundary['source_freshness_staleness_comparison_source']} / {operator_boundary['source_freshness_staleness_comparison_date']}; read={operator_boundary['source_freshness_read']}",
            f"- Current rule mix / refresh boundary: OP_DURABLE_K7={operator_boundary['op_anchor_roi_complete_rows']}, CD_CORE_K8={operator_boundary['cd_companion_roi_complete_rows']}, CD-only current settled context={operator_boundary['current_settled_context_is_cd_only']}; refresh boundary={operator_boundary['refresh_action_boundary_read']}; wrapper-counts-as-ROI-evidence={operator_boundary['refresh_counts_as_roi_complete_evidence_by_itself']}; clean-empty-forward-performance={operator_boundary['clean_empty_refresh_counts_as_forward_performance']}.",
            f"- Decision gates: phase8_promotion_review={decision_gates['phase8_promotion_review']['minimum_roi_complete_settled_observations']}, anchor_displacement={decision_gates['anchor_displacement']['minimum_roi_complete_same_candidate_observations']}, real_money_discussion={decision_gates['real_money_discussion']['minimum_total_settled_roi_complete_observations']}; these are inherited from compare-main `decision_change_gate_minimums` with scorecard threshold_source keys and are posture gates only.",
            f"- Scorecard ranking contract: tier-first={scorecard_ranking_contract['rank_is_tier_first_decision_order']}; raw-score-promotional={not scorecard_ranking_contract['raw_score_is_not_an_automatic_deployment_instruction']}; {scorecard_ranking_contract['known_rank_override']}",
            f"- Scorecard CI-only diagnostic: `forward_evidence_scorecard.json:{pdc.OP_REFINED_CI_ONLY_DIAGNOSTIC_SOURCE_KEY}` keeps ci_only_promotion_allowed={str(scorecard_ci_only_diagnostic['ci_only_promotion_allowed']).lower()}, so positive OP_REFINED CI support stays out of portfolio-level Phase 8 default readiness.",
            f"- PAPER NOW: Phase 7 OP/CD rule-component basket ({float(df.loc['phase7_live_portfolio', 'holdout_roi']):+.2f}% on {int(df.loc['phase7_live_portfolio', 'holdout_races'])} races; 2024={float(df.loc['phase7_live_portfolio', 'holdout_2024_roi']):+.2f}% on {int(df.loc['phase7_live_portfolio', 'holdout_2024_races'])}, 2025={float(df.loc['phase7_live_portfolio', 'holdout_2025_roi']):+.2f}% on {int(df.loc['phase7_live_portfolio', 'holdout_2025_races'])}; target cards require daily preflight)",
            f"- SHADOW ONLY: Phase 8 frozen portfolio ({float(df.loc['phase8_frozen_portfolio', 'holdout_roi']):+.2f}% on {int(df.loc['phase8_frozen_portfolio', 'holdout_races'])} races; 2024={float(df.loc['phase8_frozen_portfolio', 'holdout_2024_roi']):+.2f}% on {int(df.loc['phase8_frozen_portfolio', 'holdout_2024_races'])}, 2025={float(df.loc['phase8_frozen_portfolio', 'holdout_2025_roi']):+.2f}% on {int(df.loc['phase8_frozen_portfolio', 'holdout_2025_races'])})",
            f"- BENCHMARK ONLY: Train-only selector ({float(df.loc['train_only_selector', 'holdout_roi']):+.2f}% holdout; 2024={float(df.loc['train_only_selector', 'holdout_2024_roi']):+.2f}% on {int(df.loc['train_only_selector', 'holdout_2024_races'])}, 2025={float(df.loc['train_only_selector', 'holdout_2025_roi']):+.2f}% on {int(df.loc['train_only_selector', 'holdout_2025_races'])}; {float(df.loc['train_only_selector', 'wf_roi']):+.2f}% WF)",
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
