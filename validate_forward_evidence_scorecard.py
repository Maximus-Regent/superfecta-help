#!/usr/bin/env python3
"""
Validation for forward_evidence_scorecard.py.

Purpose:
- keep the forward-evidence ranking artifact reproducible at the source layer
- pin the saved CSV and text scorecard surfaces against a fresh rebuild
- lock the current conservative deployment read: OP_DURABLE_K7 anchor first,
  CD_CORE_K8 paper-now, small-sample Phase 8 winners still watch-only
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.testing import assert_frame_equal

import forward_evidence_scorecard as fes

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "out" / "status_validation" / "forward_evidence_scorecard"
OUT_MD = OUT_DIR / "forward_evidence_scorecard_validation.md"
OUT_JSON = OUT_DIR / "forward_evidence_scorecard_validation.json"
TMP_PARENT = OUT_DIR / "_tmp"
REBUILD_COMMAND = "python3 validate_forward_evidence_scorecard.py"
SCORECARD_SCRIPT = BASE / "forward_evidence_scorecard.py"
SCORECARD_CSV = BASE / "forward_evidence_scorecard.csv"
SCORECARD_TXT = BASE / "forward_evidence_scorecard.txt"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
FROZEN_SUMMARY = BASE / "frozen_portfolio_eval_summary.csv"
WF_FOLDS = BASE / "walk_forward_validation_folds.csv"
PHASE7_REPORT = BASE / "PHASE7_REPORT.md"
PHASE8_REPORT = BASE / "PHASE8_REPORT.md"
GENERATED_AT_TZ_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} (UTC|CET|CEST)$")


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
    rebuilt_like_saved = rebuilt.copy().reset_index()
    if "rank" not in rebuilt_like_saved.columns and "rank" in saved.columns:
        rebuilt_like_saved.insert(0, "rank", range(1, len(rebuilt_like_saved) + 1))
    missing_cols = [col for col in saved.columns if col not in rebuilt_like_saved.columns]
    if missing_cols:
        raise AssertionError(f"rebuilt scorecard is missing saved columns {missing_cols}")
    rebuilt_like_saved = rebuilt_like_saved[saved.columns]
    assert_frame_equal(
        normalize_frame(saved, "rule_id"),
        normalize_frame(rebuilt_like_saved, "rule_id"),
        check_dtype=False,
        check_exact=False,
        atol=1e-9,
        rtol=0,
    )


def parse_generated_timestamp(report_text: str) -> str:
    match = re.search(r"^Generated: (.+)$", report_text, flags=re.MULTILINE)
    if match is None:
        raise AssertionError("forward_evidence_scorecard.txt is missing its Generated line")
    generated_at = match.group(1).strip()
    if not GENERATED_AT_TZ_RE.match(generated_at):
        raise AssertionError(
            "forward_evidence_scorecard.txt Generated line must use 'YYYY-MM-DD HH:MM TZ' with TZ in UTC, CET, or CEST"
        )
    return generated_at


def normalize_json_payload(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    rows = out.get("rows", [])
    if isinstance(rows, list):
        out["rows"] = sorted(rows, key=lambda row: row.get("rule_id", ""))
    return out


def compare_json_payload(saved_payload: dict[str, Any], rebuilt_payload: dict[str, Any]) -> None:
    if normalize_json_payload(saved_payload) != normalize_json_payload(rebuilt_payload):
        raise AssertionError("forward_evidence_scorecard.json no longer matches a fresh metadata+rows rebuild")


def build_suite_read(df: pd.DataFrame) -> str:
    top = df.iloc[0]
    cd_core = df[df["rule_id"] == "CD_CORE_K8"].iloc[0]
    op_refined = df[df["rule_id"] == "OP_REFINED_K7"].iloc[0]
    kee = df[df["rule_id"] == "KEE_K9"].iloc[0]
    dmr = df[df["rule_id"] == "DMR_FALL_K7"].iloc[0]
    sa = df[df["rule_id"] == "SA_K9"].iloc[0]
    bel = df[df["rule_id"] == "BEL_BROAD1_K7"].iloc[0]
    return (
        f"{top['rule_id']} stays {top['tier']} at rank {int(top['rank'])} "
        f"({float(top['holdout_roi']):+.1f}% on {int(top['holdout_races'])} holdout races, {str(top['wf_selected'])} WF; "
        f"main table now carries 2024={float(top['holdout_2024_roi']):+.1f}% on {int(top['holdout_2024_races'])}, "
        f"2025={float(top['holdout_2025_roi']):+.1f}% on {int(top['holdout_2025_races'])}); "
        f"CD_CORE_K8 stays {cd_core['tier']} ahead of OP_REFINED_K7 as the primary OP/CD paper-basket companion because the deployment tiering stays more conservative than the raw score ordering "
        f"even though CD_CORE_K8 is mostly a steadier two-positive-year holdout and OP_REFINED_K7 is a smaller mixed-year spike; "
        "the scorecard now also publishes a CI-only promotion diagnostic saying OP_REFINED_K7's positive CI lower bound is support context only, not a promotion trigger; "
        f"watch triage now makes the shadow blockers explicit too: OP_REFINED_K7 stays the closest challenger, KEE_K9 stays a tiny two-year watch, "
        f"and SA_K9 / DMR_FALL_K7 remain observation-only pockets rather than near-promotion cases; "
        f"BEL_BROAD1_K7 stays {bel['tier']} until new forward races exist; "
        f"scorecard source-scope text now says it is built from frozen 2024-2025 holdout plus train-only walk-forward artifacts and exposes exact valid_evidence_scope={fes.VALID_EVIDENCE_SCOPE}, while also saying it is not a live paper-trade ledger or current-day profitability result, with the same scope and boundary carried into the CSV rows and the text/CSV/JSON sidecars; the CSV rows and JSON sidecar now publish bootstrap-CI lower-bound source notes, including the CD_CORE_K8 legacy hardcoded value that is not printed as a standalone Phase 7/8 report CI line, while the JSON sidecar also fingerprints the frozen input files and the Phase 7/Phase 8 report files; the scorecard also publishes decision-change gates, machine-readable decision-gate minimums, and a machine-readable JSON evidence boundary so clean rebuilds, empty scans, compatibility keys, historical replay rows, and small-sample shadow excitement cannot be mistaken for posture-changing evidence; PHASE7_REPORT.md now keeps its automation/risk section as paper observation only, not bet sizing or bankroll guidance, and PHASE8_REPORT.md now labels its $2/cost/expected lines as historical paper-accounting metadata for shadow/watch context only"
    )


def build_expected_cli_stdout(report_text: str, txt_path: Path, csv_path: Path, json_path: Path) -> str:
    return report_text + f"\n\nSaved to: {txt_path.resolve()}\nSaved to: {csv_path.resolve()}\nSaved to: {json_path.resolve()}\n"


def build_expected_stdout_only(report_text: str) -> str:
    return report_text + "\n"


def strip_source_fingerprint_lines(report_text: str) -> str:
    return "\n".join(
        line
        for line in report_text.splitlines()
        if not line.startswith("Source fingerprints ")
        and not line.startswith("- frozen_summary:")
        and not line.startswith("- walk_forward_folds:")
    )


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

    saved_df = pd.read_csv(SCORECARD_CSV)
    saved_payload = json.loads(SCORECARD_JSON.read_text(encoding="utf-8"))
    rebuilt_df = fes.build_scorecard()
    compare_like_saved(saved_df, rebuilt_df)

    saved_report = SCORECARD_TXT.read_text(encoding="utf-8")
    phase7_report_text = PHASE7_REPORT.read_text(encoding="utf-8")
    phase8_report_text = PHASE8_REPORT.read_text(encoding="utf-8")
    generated_at = parse_generated_timestamp(saved_report)
    rebuilt_report = fes.format_report(rebuilt_df, generated_at=generated_at)
    rebuilt_payload = fes.build_json_payload(rebuilt_df, generated_at=generated_at)
    if saved_report.strip() != rebuilt_report.strip():
        raise AssertionError("forward_evidence_scorecard.txt no longer matches a fresh rebuild")
    compare_json_payload(saved_payload, rebuilt_payload)

    with tempfile.TemporaryDirectory(prefix="forward_scorecard_cli_", dir=tmp_parent) as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        cli_script = tmpdir / SCORECARD_SCRIPT.name
        cli_frozen = tmpdir / FROZEN_SUMMARY.name
        cli_wf = tmpdir / WF_FOLDS.name
        cli_phase7_report = tmpdir / PHASE7_REPORT.name
        cli_phase8_report = tmpdir / PHASE8_REPORT.name
        cli_txt = tmpdir / SCORECARD_TXT.name
        cli_csv = tmpdir / SCORECARD_CSV.name
        cli_json = tmpdir / SCORECARD_JSON.name
        pinned_dir = tmpdir / "pinned_out"
        pinned_txt = pinned_dir / "scorecard.txt"
        pinned_csv = pinned_dir / "scorecard.csv"
        pinned_json = pinned_dir / "scorecard.json"
        alt_frozen = tmpdir / "alt_frozen_portfolio_eval_summary.csv"
        alt_wf = tmpdir / "alt_walk_forward_validation_folds.csv"
        fingerprint_only_frozen = tmpdir / "fingerprint_only_frozen_portfolio_eval_summary.csv"
        fingerprint_only_txt = tmpdir / "fingerprint_only_scorecard.txt"
        fingerprint_only_csv = tmpdir / "fingerprint_only_scorecard.csv"
        fingerprint_only_json = tmpdir / "fingerprint_only_scorecard.json"
        missing_year_summary = tmpdir / "missing_year_summary.csv"
        conflicting_duplicate_summary = tmpdir / "conflicting_duplicate_summary.csv"
        bad_phase7_report = tmpdir / "bad_phase7_report.md"
        bad_report_output_dir = tmpdir / "bad_report_should_not_exist"
        bad_report_txt = bad_report_output_dir / "bad_report_scorecard.txt"
        bad_report_csv = bad_report_output_dir / "bad_report_scorecard.csv"
        bad_report_json = bad_report_output_dir / "bad_report_scorecard.json"
        bad_phase8_report = tmpdir / "bad_phase8_report.md"
        bad_phase8_report_output_dir = tmpdir / "bad_phase8_report_should_not_exist"
        bad_phase8_report_txt = bad_phase8_report_output_dir / "bad_phase8_report_scorecard.txt"
        bad_phase8_report_csv = bad_phase8_report_output_dir / "bad_phase8_report_scorecard.csv"
        bad_phase8_report_json = bad_phase8_report_output_dir / "bad_phase8_report_scorecard.json"
        shutil.copy2(SCORECARD_SCRIPT, cli_script)
        shutil.copy2(FROZEN_SUMMARY, cli_frozen)
        shutil.copy2(FROZEN_SUMMARY, alt_frozen)
        shutil.copy2(WF_FOLDS, cli_wf)
        shutil.copy2(WF_FOLDS, alt_wf)
        shutil.copy2(PHASE7_REPORT, cli_phase7_report)
        shutil.copy2(PHASE8_REPORT, cli_phase8_report)
        cli_result = subprocess.run(
            [sys.executable, cli_script.name],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        cli_saved_report = cli_txt.read_text(encoding="utf-8")
        cli_generated_at = parse_generated_timestamp(cli_saved_report)
        cli_rebuilt_report = fes.format_report(rebuilt_df, generated_at=cli_generated_at)
        if cli_saved_report.strip() != cli_rebuilt_report.strip():
            raise AssertionError("CLI-generated forward_evidence_scorecard.txt drifted from a fresh rebuild")
        cli_saved_df = pd.read_csv(cli_csv)
        compare_like_saved(saved_df, cli_saved_df)
        cli_saved_payload = json.loads(cli_json.read_text(encoding="utf-8"))
        cli_rebuilt_payload = fes.build_json_payload(rebuilt_df, generated_at=cli_generated_at)
        compare_json_payload(cli_rebuilt_payload, cli_saved_payload)
        expected_cli_stdout = build_expected_cli_stdout(cli_rebuilt_report, cli_txt, cli_csv, cli_json)
        if cli_result.stdout != expected_cli_stdout:
            raise AssertionError("forward_evidence_scorecard.py CLI stdout no longer matches its generated report plus save notices")

        pinned_result = subprocess.run(
            [
                sys.executable,
                cli_script.name,
                "--generated-at",
                generated_at,
                "--frozen-summary",
                str(alt_frozen),
                "--wf-folds",
                str(alt_wf),
                "--txt-output",
                str(pinned_txt),
                "--csv-output",
                str(pinned_csv),
                "--json-output",
                str(pinned_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        pinned_expected_report = fes.format_report(
            rebuilt_df,
            generated_at=generated_at,
            frozen_summary_path=alt_frozen,
            wf_folds_path=alt_wf,
        )
        pinned_report = pinned_txt.read_text(encoding="utf-8")
        if pinned_report.strip() != pinned_expected_report.strip():
            raise AssertionError("Pinned generated-at CLI rerender no longer matches the expected custom-source forward_evidence_scorecard.txt surface")
        pinned_df = pd.read_csv(pinned_csv)
        compare_like_saved(saved_df, pinned_df)
        pinned_payload = json.loads(pinned_json.read_text(encoding="utf-8"))
        pinned_rebuilt_payload = fes.build_json_payload(
            rebuilt_df,
            generated_at=generated_at,
            frozen_summary_path=alt_frozen,
            wf_folds_path=alt_wf,
        )
        compare_json_payload(pinned_rebuilt_payload, pinned_payload)
        expected_pinned_stdout = build_expected_cli_stdout(pinned_expected_report, pinned_txt, pinned_csv, pinned_json)
        if pinned_result.stdout != expected_pinned_stdout:
            raise AssertionError("Pinned/custom-output CLI rerender no longer matches the expected report plus custom save notices")

        stdout_only_result = subprocess.run(
            [
                sys.executable,
                cli_script.name,
                "--generated-at",
                generated_at,
                "--stdout-only",
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        if stdout_only_result.stdout != build_expected_stdout_only(rebuilt_report):
            raise AssertionError("stdout-only mode no longer prints only the report text")
        if stdout_only_result.stderr:
            raise AssertionError("stdout-only mode unexpectedly wrote to stderr")

        bad_generated_at_result = subprocess.run(
            [
                sys.executable,
                cli_script.name,
                "--generated-at",
                "2026-07-08 04:08",
                "--stdout-only",
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if bad_generated_at_result.returncode == 0:
            raise AssertionError("forward_evidence_scorecard.py unexpectedly accepted a generated-at timestamp without a timezone label")
        bad_generated_at_output = f"{bad_generated_at_result.stdout}\n{bad_generated_at_result.stderr}"
        if "generated_at must use 'YYYY-MM-DD HH:MM TZ' with TZ in UTC, CET, or CEST" not in bad_generated_at_output:
            raise AssertionError("bad generated-at failure no longer names the explicit timezone-label requirement")

        fingerprint_only_frozen.write_text(cli_frozen.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        fingerprint_only_result = subprocess.run(
            [
                sys.executable,
                cli_script.name,
                "--generated-at",
                generated_at,
                "--frozen-summary",
                str(fingerprint_only_frozen),
                "--wf-folds",
                str(cli_wf),
                "--txt-output",
                str(fingerprint_only_txt),
                "--csv-output",
                str(fingerprint_only_csv),
                "--json-output",
                str(fingerprint_only_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        fingerprint_only_report = fingerprint_only_txt.read_text(encoding="utf-8")
        fingerprint_only_expected_report = fes.format_report(
            rebuilt_df,
            generated_at=generated_at,
            frozen_summary_path=fingerprint_only_frozen,
            wf_folds_path=cli_wf,
        )
        if fingerprint_only_report.strip() != fingerprint_only_expected_report.strip():
            raise AssertionError("Fingerprint-only frozen source copy no longer matches the expected custom-source scorecard text")
        if strip_source_fingerprint_lines(fingerprint_only_report) != strip_source_fingerprint_lines(rebuilt_report):
            raise AssertionError("Fingerprint-only source-byte drift changed more than the visible source fingerprint lines")
        if fingerprint_only_report.strip() == rebuilt_report.strip():
            raise AssertionError("Fingerprint-only source-byte drift did not change the text scorecard fingerprint lines")
        fingerprint_only_df = pd.read_csv(fingerprint_only_csv)
        compare_like_saved(saved_df, fingerprint_only_df)
        fingerprint_only_payload = json.loads(fingerprint_only_json.read_text(encoding="utf-8"))
        fingerprint_only_rebuilt_payload = fes.build_json_payload(
            rebuilt_df,
            generated_at=generated_at,
            frozen_summary_path=fingerprint_only_frozen,
            wf_folds_path=cli_wf,
        )
        compare_json_payload(fingerprint_only_rebuilt_payload, fingerprint_only_payload)
        expected_fingerprint_only_stdout = build_expected_cli_stdout(
            fingerprint_only_expected_report,
            fingerprint_only_txt,
            fingerprint_only_csv,
            fingerprint_only_json,
        )
        if fingerprint_only_result.stdout != expected_fingerprint_only_stdout:
            raise AssertionError("Fingerprint-only source rerender no longer matches expected report plus save notices")
        same_rows_different_source_fingerprint = (
            fingerprint_only_payload["rows"] == saved_payload["rows"]
            and fingerprint_only_payload["source_files"]["frozen_summary"]["sha256"]
            != saved_payload["source_files"]["frozen_summary"]["sha256"]
            and fingerprint_only_payload["source_files"]["frozen_summary"]["bytes"]
            == saved_payload["source_files"]["frozen_summary"]["bytes"] + 1
            and fingerprint_only_payload["source_files"]["frozen_summary"]["path"] == fingerprint_only_frozen.name
        )

        missing_df = pd.read_csv(cli_frozen)
        missing_df = missing_df[
            ~(
                (missing_df["level"] == "rule")
                & (missing_df["name"] == "OP_DURABLE_K7")
                & (missing_df["slice"] == "year_2025")
            )
        ].copy()
        missing_df.to_csv(missing_year_summary, index=False)
        missing_result = subprocess.run(
            [
                sys.executable,
                cli_script.name,
                "--frozen-summary",
                str(missing_year_summary),
                "--stdout-only",
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if missing_result.returncode == 0:
            raise AssertionError("forward_evidence_scorecard.py unexpectedly accepted a frozen summary missing OP_DURABLE_K7 / year_2025")
        missing_output = f"{missing_result.stdout}\n{missing_result.stderr}"
        if "missing required rule slice OP_DURABLE_K7 / year_2025" not in missing_output:
            raise AssertionError("missing-year failure no longer reports the missing OP_DURABLE_K7 / year_2025 source slice clearly")

        conflicting_df = pd.read_csv(cli_frozen)
        bel_duplicate_idx = conflicting_df[
            (conflicting_df["level"] == "rule")
            & (conflicting_df["name"] == "BEL_BROAD1_K7")
            & (conflicting_df["slice"] == "year_2024")
        ].index[-1]
        conflicting_df.loc[bel_duplicate_idx, "roi"] = 1.23
        conflicting_df.to_csv(conflicting_duplicate_summary, index=False)
        conflicting_result = subprocess.run(
            [
                sys.executable,
                cli_script.name,
                "--frozen-summary",
                str(conflicting_duplicate_summary),
                "--stdout-only",
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if conflicting_result.returncode == 0:
            raise AssertionError("forward_evidence_scorecard.py unexpectedly accepted conflicting duplicate BEL rows in the frozen summary")
        conflicting_output = f"{conflicting_result.stdout}\n{conflicting_result.stderr}"
        if "conflicting duplicate rows for BEL_BROAD1_K7 / year_2024" not in conflicting_output:
            raise AssertionError("conflicting-duplicate failure no longer reports the BEL year_2024 source conflict clearly")

        bad_phase7_report.write_text(
            "# Bad Phase 7 report fixture\n\nThis fixture intentionally omits the exact bootstrap-CI source lines.\n",
            encoding="utf-8",
        )
        bad_report_result = subprocess.run(
            [
                sys.executable,
                cli_script.name,
                "--phase7-report",
                str(bad_phase7_report),
                "--txt-output",
                str(bad_report_txt),
                "--csv-output",
                str(bad_report_csv),
                "--json-output",
                str(bad_report_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if bad_report_result.returncode == 0:
            raise AssertionError("forward_evidence_scorecard.py unexpectedly accepted a Phase 7 report missing exact bootstrap-CI source text")
        bad_report_output = f"{bad_report_result.stdout}\n{bad_report_result.stderr}"
        if "does not contain expected bootstrap CI source text for BEL_BROAD1_K7" not in bad_report_output:
            raise AssertionError("bad Phase 7 report failure no longer names the missing exact bootstrap-CI source text")
        if bad_report_output_dir.exists() or bad_report_txt.exists() or bad_report_csv.exists() or bad_report_json.exists():
            raise AssertionError("bad Phase 7 bootstrap-CI source fixture wrote output artifacts despite failing provenance validation")

        bad_phase8_report.write_text(
            "# Bad Phase 8 report fixture\n\nThis fixture intentionally omits the exact bootstrap-CI source lines.\n",
            encoding="utf-8",
        )
        bad_phase8_report_result = subprocess.run(
            [
                sys.executable,
                cli_script.name,
                "--phase8-report",
                str(bad_phase8_report),
                "--txt-output",
                str(bad_phase8_report_txt),
                "--csv-output",
                str(bad_phase8_report_csv),
                "--json-output",
                str(bad_phase8_report_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
        )
        if bad_phase8_report_result.returncode == 0:
            raise AssertionError("forward_evidence_scorecard.py unexpectedly accepted a Phase 8 report missing exact bootstrap-CI source text")
        bad_phase8_report_output = f"{bad_phase8_report_result.stdout}\n{bad_phase8_report_result.stderr}"
        if "does not contain expected bootstrap CI source text for OP_REFINED_K7" not in bad_phase8_report_output:
            raise AssertionError("bad Phase 8 report failure no longer names the first missing exact bootstrap-CI source text")
        if (
            bad_phase8_report_output_dir.exists()
            or bad_phase8_report_txt.exists()
            or bad_phase8_report_csv.exists()
            or bad_phase8_report_json.exists()
        ):
            raise AssertionError("bad Phase 8 bootstrap-CI source fixture wrote output artifacts despite failing provenance validation")

    df = saved_df.copy()
    checks: list[dict[str, Any]] = []

    top = df.sort_values("rank").iloc[0]
    checks.append(
        require(
            top["rule_id"] == "OP_DURABLE_K7"
            and top["tier"] == "ANCHOR"
            and int(top["holdout_races"]) == 115
            and str(top["wf_selected"]) == "7/10"
            and "best current OP anchor" in str(top["note"]),
            "anchor_row",
            "OP_DURABLE_K7 still leads the scorecard as ANCHOR with 115 holdout races, 7/10 walk-forward selection, and the anchor note intact",
        )
    )

    cd_core = df[df["rule_id"] == "CD_CORE_K8"].iloc[0]
    op_refined = df[df["rule_id"] == "OP_REFINED_K7"].iloc[0]
    checks.append(
        require(
            cd_core["tier"] == "PAPER"
            and op_refined["tier"] == "WATCH"
            and int(cd_core["rank"]) < int(op_refined["rank"])
            and float(op_refined["forward_trust"]) > float(cd_core["forward_trust"]),
            "paper_vs_watch_guardrail",
            "CD_CORE_K8 still stays PAPER and ranks above OP_REFINED_K7 even though OP_REFINED_K7 carries the higher compact score, because the tier guardrail remains conservative",
        )
    )

    checks.append(
        require(
            saved_payload.get("ranking_standard") == "rules ranked by tier-first conservative decision order, then forward_trust within tier; not an automatic deployment instruction"
            and saved_payload.get("ranking_contract") == fes.RANKING_CONTRACT
            and saved_payload["ranking_contract"].get("rank_is_tier_first_decision_order") is True
            and saved_payload["ranking_contract"].get("forward_trust_is_secondary_within_tier") is True
            and "CD_CORE_K8 ranks ahead of OP_REFINED_K7" in saved_payload["ranking_contract"].get("known_rank_override", "")
            and "Rules ranked by tier-first conservative decision order, then by forward_trust within tier." in saved_report
            and "Rank is not raw-score order: PAPER CD_CORE_K8 intentionally ranks ahead of WATCH OP_REFINED_K7" in saved_report
            and "Score         = forward_trust score used inside a tier; rank is tier-first and not raw-score order" in saved_report,
            "tier_first_ranking_contract",
            "the scorecard now makes the tier-first ranking contract explicit in both text and JSON, so readers do not confuse OP_REFINED_K7's higher raw score with a promotion above the PAPER-tier CD_CORE_K8 companion",
        )
    )

    checks.append(
        require(
            abs(float(top["holdout_2024_roi"]) - (-47.41)) < 1e-9
            and int(top["holdout_2024_races"]) == 68
            and abs(float(top["holdout_2025_roi"]) - 124.61) < 1e-9
            and int(top["holdout_2025_races"]) == 47
            and abs(float(cd_core["holdout_2024_roi"]) - 45.65) < 1e-9
            and int(cd_core["holdout_2024_races"]) == 41
            and abs(float(cd_core["holdout_2025_roi"]) - 78.21) < 1e-9
            and int(cd_core["holdout_2025_races"]) == 19
            and abs(float(op_refined["holdout_2024_roi"]) - (-25.47)) < 1e-9
            and int(op_refined["holdout_2024_races"]) == 33
            and abs(float(op_refined["holdout_2025_roi"]) - 210.02) < 1e-9
            and int(op_refined["holdout_2025_races"]) == 16,
            "year_split_columns",
            "the scorecard CSV now carries explicit 2024 and 2025 holdout ROI/race columns for the main current rules, clarifying steady-vs-spiky forward evidence",
        )
    )

    checks.append(
        require(
            str(top["current_role"]) == "Safest current anchor"
            and str(top["action_now"]) == "Keep as safest current anchor"
            and "Largest current OP holdout sample" in str(top["deployment_reason"])
            and str(cd_core["current_role"]) == "Primary paper-basket companion"
            and str(cd_core["action_now"]) == "Keep in the primary paper-basket mix, not as an anchor replacement"
            and "Primary OP/CD paper-basket companion" in str(cd_core["deployment_reason"])
            and "positive in both holdout years" in str(cd_core["deployment_reason"])
            and "non-anchor shadow" not in str(cd_core["deployment_reason"])
            and str(op_refined["current_role"]) == "Closest OP challenger"
            and str(op_refined["action_now"]) == "Shadow/watch only"
            and "losing 2024" in str(op_refined["deployment_reason"]),
            "deployment_context_columns",
            "the saved scorecard CSV now carries explicit current-role, action-now, and deployment-reason columns for the key current rules, with CD_CORE_K8 pinned as the primary OP/CD paper-basket companion rather than a generic non-anchor shadow, so downstream readers do not have to reconstruct the paper-trade order from prose alone",
        )
    )

    checks.append(
        require(
            "DECISION-CHANGE GATES (what would actually change the tiers)" in saved_report
            and "anchor_displacement" in saved_report
            and "30+ ROI-complete settled paper observations" in saved_report
            and "primary_companion" in saved_report
            and "CD_CORE_K8 as the primary OP/CD paper-basket companion" in saved_report
            and "phase8_promotion_review" in saved_report
            and "20+ ROI-complete settled shadow observations" in saved_report
            and "Machine-readable threshold summary" in saved_report
            and "anchor_displacement=30 ROI-complete same-candidate settled observations" in saved_report
            and "phase8_promotion_review=20 ROI-complete shadow observations" in saved_report
            and "real_money_discussion=100 total settled observations with usable ROI" in saved_report
            and "real_money_discussion" in saved_report
            and "100+ total settled paper observations" in saved_report
            and saved_payload.get("decision_change_gates") == list(fes.DECISION_CHANGE_GATES),
            "decision_change_gates",
            "the scorecard text and JSON now publish explicit decision-change gates so anchor changes, CD companion changes, Phase 8 promotion review, and real-money discussion require settled forward evidence rather than clean rebuilds or historical replay rows",
        )
    )

    checks.append(
        require(
            saved_payload.get("decision_gate_minimums") == fes.DECISION_GATE_MINIMUMS
            and saved_payload["decision_gate_minimums"]["anchor_displacement"]["min_roi_complete_settled_observations"] == 30
            and saved_payload["decision_gate_minimums"]["anchor_displacement"]["observation_scope"] == "same candidate paper observations"
            and "equal-or-better walk-forward support" in saved_payload["decision_gate_minimums"]["anchor_displacement"]["also_requires"]
            and saved_payload["decision_gate_minimums"]["phase8_promotion_review"]["min_roi_complete_settled_observations"] == 20
            and saved_payload["decision_gate_minimums"]["phase8_promotion_review"]["observation_scope"] == "candidate shadow observations"
            and "complete ROI coverage" in saved_payload["decision_gate_minimums"]["phase8_promotion_review"]["also_requires"]
            and saved_payload["decision_gate_minimums"]["real_money_discussion"]["min_total_settled_observations_with_usable_roi"] == 100
            and "no BAQ-as-BEL substitution" in saved_payload["decision_gate_minimums"]["real_money_discussion"]["also_requires"]
            and "empty/no-target wrapper runs" in saved_payload["decision_gate_minimums"]["real_money_discussion"]["does_not_count"],
            "decision_gate_minimums_json_present",
            "the scorecard JSON now publishes machine-readable numeric minimums that separate 20 ROI-complete Phase 8 shadow observations from the stricter 30 ROI-complete same-candidate anchor-displacement threshold and the 100-row real-money discussion threshold",
        )
    )

    bel = df[df["rule_id"] == "BEL_BROAD1_K7"].iloc[0]
    checks.append(
        require(
            bel["tier"] == "DORMANT"
            and int(bel["holdout_races"]) == 0
            and "no 2024-2025 forward races" in str(bel["note"]),
            "bel_dormant",
            "BEL_BROAD1_K7 still stays DORMANT with zero 2024-2025 holdout races and an explicit dormant note",
        )
    )
    checks.append(
        require(
            "current-paper weight" in str(bel["deployment_reason"])
            and "live-paper weight" not in saved_report
            and "live-paper weight" not in json.dumps(saved_payload)
            and "live-paper weight" not in saved_df.to_csv(index=False),
            "bel_dormant_current_paper_weight_wording",
            "BEL_BROAD1_K7 dormant wording now says it cannot carry current-paper weight, avoiding stale live-paper shorthand in scorecard CSV/text/JSON surfaces",
        )
    )

    negative_rules = df[df["holdout_roi"] <= 0].set_index("rule_id")
    checks.append(
        require(
            negative_rules.loc["CD_REFINED_K9", "tier"] == "SKIP"
            and negative_rules.loc["AQU_K9", "tier"] == "SKIP",
            "negative_holdout_skip",
            "negative-holdout rules still stay in SKIP status instead of being promoted by small-sample or walk-forward noise",
        )
    )

    saved_fingerprints = saved_payload.get("source_files", {})
    expected_ci_sources = {
        rule_id: {**source, "ci_lower": fes.BOOTSTRAP_CI_LOWER[rule_id]}
        for rule_id, source in fes.BOOTSTRAP_CI_LOWER_SOURCES.items()
    }
    report_text_by_name = {
        "PHASE7_REPORT.md": phase7_report_text,
        "PHASE8_REPORT.md": phase8_report_text,
    }
    report_ci_sources_match_text = all(
        source["source_text"] in report_text_by_name[source["source_report"]]
        for source in expected_ci_sources.values()
        if source["source_type"] == "report_text_exact"
    )
    checks.append(
        require(
            f"Valid evidence scope: valid_evidence_scope={fes.VALID_EVIDENCE_SCOPE}." in saved_report
            and "Source scope: frozen 2024-2025 holdout summary + train-only walk-forward folds; bootstrap CI lows are hardcoded inputs with report-fingerprint and source-note provenance." in saved_report
            and "Evidence boundary: this is not a live paper-trade ledger; does not consume current-day scanner, settlement-audit, or profitability results." in saved_report
            and "Source fingerprints (exact input bytes; same values are copied into the JSON sidecar):" in saved_report
            and fes.format_source_fingerprint("frozen_summary", saved_fingerprints.get("frozen_summary", {})) in saved_report
            and fes.format_source_fingerprint("walk_forward_folds", saved_fingerprints.get("walk_forward_folds", {})) in saved_report
            and fes.format_source_fingerprint("bootstrap_phase7_report", saved_fingerprints.get("bootstrap_phase7_report", {})) in saved_report
            and fes.format_source_fingerprint("bootstrap_phase8_report", saved_fingerprints.get("bootstrap_phase8_report", {})) in saved_report,
            "source_scope_text",
            "the text scorecard now discloses its exact valid_evidence_scope, frozen-source scope, non-live-evidence boundary, and exact input-byte fingerprints for the frozen CSVs plus the report files that provide broad provenance for hardcoded bootstrap-CI lower-bound inputs",
        )
    )

    checks.append(
        require(
            "valid_evidence_scope" in saved_df.columns
            and "source_scope" in saved_df.columns
            and "evidence_boundary" in saved_df.columns
            and set(saved_df["valid_evidence_scope"].dropna().astype(str)) == {fes.VALID_EVIDENCE_SCOPE}
            and set(saved_df["source_scope"].dropna().astype(str)) == {fes.SOURCE_SCOPE}
            and set(saved_df["evidence_boundary"].dropna().astype(str)) == {fes.EVIDENCE_BOUNDARY},
            "source_scope_csv_columns",
            "the saved scorecard CSV now carries the same valid evidence scope, frozen-source scope, and non-live-evidence boundary on every row so spreadsheet consumers cannot detach rankings from their source contract",
        )
    )

    checks.append(
        require(
            saved_payload.get("valid_evidence_scope") == fes.VALID_EVIDENCE_SCOPE
            and saved_payload.get("evidence_boundary", {}).get("valid_evidence_scope") == fes.VALID_EVIDENCE_SCOPE
            and "valid_evidence_scope" in saved_payload.get("columns", [])
            and all(
                row.get("valid_evidence_scope") == fes.VALID_EVIDENCE_SCOPE
                for row in saved_payload.get("rows", [])
            )
            and f"valid_evidence_scope={fes.VALID_EVIDENCE_SCOPE}" in saved_report,
            "scorecard_outputs_expose_valid_evidence_scope",
            "the saved scorecard text, CSV rows, JSON sidecar, ranked JSON rows, and machine-readable boundary now expose the exact valid_evidence_scope so frozen scorecard rebuilds stay classified as ranking/posture metadata only",
        )
    )

    checks.append(
        require(
            "ci_lower_source_type" in saved_df.columns
            and "ci_lower_source_report" in saved_df.columns
            and "ci_lower_source_note" in saved_df.columns
            and set(saved_df["ci_lower_source_type"].dropna().astype(str)) == {
                source["source_type"] for source in fes.BOOTSTRAP_CI_LOWER_SOURCES.values()
            }
            and str(cd_core["ci_lower_source_type"]) == "legacy_hardcoded_unprinted"
            and str(cd_core["ci_lower_source_report"]) == "forward_evidence_scorecard.py"
            and "legacy hardcoded CI lower-bound input" in str(cd_core["ci_lower_source_note"])
            and str(top["ci_lower_source_type"]) == "report_text_exact"
            and str(top["ci_lower_source_report"]) == "PHASE7_REPORT.md"
            and "exact Phase 7 OP report line" in str(top["ci_lower_source_note"]),
            "bootstrap_ci_source_csv_columns",
            "the saved scorecard CSV now carries per-row bootstrap-CI source type, source report, and source note fields, so spreadsheet readers see CD_CORE_K8's legacy-hardcoded exception instead of assuming every CI lower bound came directly from a Phase report line",
        )
    )

    csv_rows_by_rule = {str(row["rule_id"]): row for row in saved_df.to_dict("records")}
    json_rows_by_rule = {str(row["rule_id"]): row for row in saved_payload.get("rows", [])}
    checks.append(
        require(
            set(csv_rows_by_rule) == set(fes.EXPECTED_RULE_IDS)
            and set(json_rows_by_rule) == set(fes.EXPECTED_RULE_IDS)
            and all(
                abs(float(csv_rows_by_rule[rule_id]["ci_lower"]) - float(expected_ci_sources[rule_id]["ci_lower"])) < 1e-9
                and abs(float(json_rows_by_rule[rule_id]["ci_lower"]) - float(expected_ci_sources[rule_id]["ci_lower"])) < 1e-9
                and str(csv_rows_by_rule[rule_id]["ci_lower_source_type"]) == str(expected_ci_sources[rule_id]["source_type"])
                and str(json_rows_by_rule[rule_id]["ci_lower_source_type"]) == str(expected_ci_sources[rule_id]["source_type"])
                and str(csv_rows_by_rule[rule_id]["ci_lower_source_report"]) == str(expected_ci_sources[rule_id]["source_report"])
                and str(json_rows_by_rule[rule_id]["ci_lower_source_report"]) == str(expected_ci_sources[rule_id]["source_report"])
                and str(csv_rows_by_rule[rule_id]["ci_lower_source_note"]) == str(expected_ci_sources[rule_id]["provenance_note"])
                and str(json_rows_by_rule[rule_id]["ci_lower_source_note"]) == str(expected_ci_sources[rule_id]["provenance_note"])
                for rule_id in fes.EXPECTED_RULE_IDS
            ),
            "bootstrap_ci_csv_json_source_parity",
            "every saved scorecard CSV row and ranked JSON row now has to match the JSON bootstrap_ci_lower_sources map for CI lower bound, source type, source report, and source note, so the spreadsheet provenance surface cannot drift from the automation provenance surface",
        )
    )

    checks.append(
        require(
            saved_payload.get("schema_version") == 1
            and saved_payload.get("artifact") == "forward_evidence_scorecard"
            and saved_payload.get("generated_at") == generated_at
            and saved_payload.get("generated_at_timezone") == fes.REPORT_TIME_ZONE
            and saved_payload.get("generated_at_timezone_contract") == fes.GENERATED_AT_TIMEZONE_CONTRACT
            and saved_payload.get("valid_evidence_scope") == fes.VALID_EVIDENCE_SCOPE
            and saved_payload.get("source_scope") == fes.SOURCE_SCOPE
            and saved_payload.get("evidence_boundary") == fes.MACHINE_READABLE_EVIDENCE_BOUNDARY
            and saved_payload.get("evidence_boundary_text") == fes.EVIDENCE_BOUNDARY
            and saved_payload.get("ranking_contract") == fes.RANKING_CONTRACT
            and saved_payload.get("decision_change_gates") == list(fes.DECISION_CHANGE_GATES)
            and saved_payload.get("decision_gate_minimums") == fes.DECISION_GATE_MINIMUMS
            and saved_payload.get("ci_only_promotion_diagnostics") == fes.CI_ONLY_PROMOTION_DIAGNOSTICS
            and saved_payload["ci_only_promotion_diagnostics"]["OP_REFINED_K7"].get("ci_only_promotion_allowed") is False
            and saved_payload.get("bootstrap_ci_lower_sources") == expected_ci_sources
            and saved_payload.get("source_files") == fes.source_file_fingerprints()
            and saved_payload.get("source_files", {}).get("frozen_summary", {}).get("path") == fes.FROZEN_SUMMARY.name
            and saved_payload.get("source_files", {}).get("walk_forward_folds", {}).get("path") == fes.WF_FOLDS.name
            and saved_payload.get("source_files", {}).get("bootstrap_phase7_report", {}).get("path") == fes.PHASE7_REPORT.name
            and saved_payload.get("source_files", {}).get("bootstrap_phase8_report", {}).get("path") == fes.PHASE8_REPORT.name
            and len(saved_payload.get("source_files", {}).get("frozen_summary", {}).get("sha256", "")) == 64
            and len(saved_payload.get("source_files", {}).get("walk_forward_folds", {}).get("sha256", "")) == 64
            and len(saved_payload.get("source_files", {}).get("bootstrap_phase7_report", {}).get("sha256", "")) == 64
            and len(saved_payload.get("source_files", {}).get("bootstrap_phase8_report", {}).get("sha256", "")) == 64
            and saved_payload.get("row_count") == len(saved_df)
            and "rows" in saved_payload
            and isinstance(saved_payload["rows"], list)
            and saved_payload["rows"][0].get("rule_id") == "OP_DURABLE_K7"
            and saved_payload["rows"][0].get("tier") == "ANCHOR"
            and "valid_evidence_scope" in saved_payload.get("columns", [])
            and "source_scope" in saved_payload.get("columns", [])
            and "evidence_boundary" in saved_payload.get("columns", [])
            and "ci_lower_source_type" in saved_payload.get("columns", [])
            and "ci_lower_source_report" in saved_payload.get("columns", [])
            and "ci_lower_source_note" in saved_payload.get("columns", [])
            and same_rows_different_source_fingerprint,
            "json_sidecar_surface",
            "the saved scorecard JSON sidecar now carries generated-at, source-file fingerprint, valid evidence scope, frozen-source, machine-readable evidence-boundary, evidence-boundary text, tier-first ranking contract, decision-change-gate, CI-only promotion diagnostic, bootstrap-CI lower-bound source-note, column, and ranked-row metadata so automation can consume the same contract as the text and CSV surfaces and verify the frozen input files plus bootstrap-CI provenance, including row-identical source-byte drift",
        )
    )

    checks.append(
        require(
            GENERATED_AT_TZ_RE.match(generated_at) is not None
            and f"Generated: {generated_at}" in saved_report
            and f"Generated timezone contract: {fes.GENERATED_AT_TIMEZONE_CONTRACT}." in saved_report
            and saved_payload.get("generated_at") == generated_at
            and saved_payload.get("generated_at_timezone") == "Europe/Zagreb"
            and saved_payload.get("generated_at_timezone_contract") == fes.GENERATED_AT_TIMEZONE_CONTRACT,
            "generated_at_timezone_contract",
            "the source scorecard now publishes and validates an explicit generated-at timezone label in text and JSON, using Europe/Zagreb local time by default so copied scorecard excerpts are not timezone-ambiguous",
        )
    )

    boundary = saved_payload.get("evidence_boundary", {})
    checks.append(
        require(
            boundary == fes.MACHINE_READABLE_EVIDENCE_BOUNDARY
            and boundary.get("artifact_role") == "forward evidence scorecard"
            and boundary.get("valid_evidence_scope") == fes.VALID_EVIDENCE_SCOPE
            and boundary.get("not_new_forward_evidence") is True
            and boundary.get("not_live_paper_trade_ledger") is True
            and boundary.get("not_current_day_scanner_result") is True
            and boundary.get("not_settled_roi_evidence") is True
            and boundary.get("not_live_profitability_evidence") is True
            and boundary.get("not_real_money_evidence") is True
            and boundary.get("not_promotion_readiness_evidence") is True
            and boundary.get("source_fingerprints_are_reproducibility_metadata_only") is True
            and boundary.get("decision_gate_minimums_are_forward_observation_requirements_not_current_evidence") is True
            and "do not promote OP_REFINED_K7 or Phase 8 from this artifact" in boundary.get("non_goals", [])
            and "do not substitute BAQ for BEL" in boundary.get("non_goals", [])
            and saved_payload.get("evidence_boundary_text") == fes.EVIDENCE_BOUNDARY,
            "json_machine_readable_evidence_boundary",
            "the scorecard JSON now publishes a machine-readable evidence_boundary block with exact valid_evidence_scope plus the legacy evidence_boundary_text, keeping scorecard rows, source fingerprints, and decision-gate minimums separate from live paper ledgers, scanner output, settled ROI, live profitability, promotion readiness, real-money evidence, OP_REFINED_K7 / Phase 8 promotion, odds-only XGBoost reopening, and BAQ/BEL substitution",
        )
    )

    checks.append(
        require(
            all(key in saved_fingerprints for key in ["frozen_summary", "walk_forward_folds", "bootstrap_phase7_report", "bootstrap_phase8_report"])
            and saved_fingerprints["bootstrap_phase7_report"] == fes.file_fingerprint(fes.PHASE7_REPORT)
            and saved_fingerprints["bootstrap_phase8_report"] == fes.file_fingerprint(fes.PHASE8_REPORT)
            and saved_payload.get("bootstrap_ci_lower_sources") == expected_ci_sources
            and report_ci_sources_match_text
            and saved_payload["bootstrap_ci_lower_sources"]["CD_CORE_K8"]["source_type"] == "legacy_hardcoded_unprinted"
            and "not printed as a standalone bootstrap-CI line" in saved_payload["bootstrap_ci_lower_sources"]["CD_CORE_K8"]["source_text"]
            and "Bootstrap CI lower bounds are hardcoded scorecard inputs with text/CSV/JSON source notes" in saved_report
            and "BOOTSTRAP CI LOWER-BOUND PROVENANCE" in saved_report
            and "CD_CORE_K8: -15.0% | legacy_hardcoded_unprinted | forward_evidence_scorecard.py" in saved_report
            and "  CI Lo         = bootstrap 95% CI lower bound from scorecard source notes" in saved_report,
            "bootstrap_ci_report_fingerprints",
            "the scorecard JSON/text source audit now fingerprints PHASE7_REPORT.md and PHASE8_REPORT.md and publishes per-rule bootstrap-CI source notes, including exact report-text matches where available plus a visible CD_CORE_K8 legacy-hardcoded exception instead of implying every CI low is directly printed in the Phase reports",
        )
    )
    checks.append(
        require(
            "Automation Guidance — paper observation only" in phase7_report_text
            and "do not place, size, bankroll, stop-loss, or scale real-money bets from this report" in phase7_report_text
            and "this is not a bankroll recommendation" in phase7_report_text
            and "this is not live-profitability or real-money evidence" in phase7_report_text
            and "Do **not** size, bankroll, stop-loss, or scale real-money bets from `PHASE7_REPORT.md`." in phase7_report_text
            and "separate human-approved risk memo" in phase7_report_text
            and "Minimum bankroll for one year" not in phase7_report_text
            and "Recommended bankroll" not in phase7_report_text
            and "Place the $2" not in phase7_report_text,
            "phase7_report_paper_only_risk_boundary",
            "PHASE7_REPORT.md now keeps $2 costs as paper/historical accounting units and explicitly removes direct real-money placement, bankroll, stop-loss, and scale-up instructions from the report source used by the scorecard fingerprint",
        )
    )
    checks.append(
        require(
            "legacy discovery report, not the deployment guide" in phase8_report_text
            and "Phase 8 rules belong in shadow/watch observation" in phase8_report_text
            and "Do not treat the 7-track full-sample result below as live profitability proof or promotion readiness." in phase8_report_text
            and "Treat every `$2`, `Cost`, and `Expected` line below as historical/paper accounting metadata, not a deployment size." in phase8_report_text
            and "Do not place, size, bankroll, stop-loss, or scale real-money bets from this report" in phase8_report_text
            and "separate human-approved risk memo" in phase8_report_text
            and "30 / 20 / 100 ROI-complete paper-evidence gates" in phase8_report_text
            and "no-BAQ-as-BEL guardrail" in phase8_report_text
            and "do not use real money from this report alone" not in phase8_report_text,
            "phase8_report_shadow_only_cost_boundary",
            "PHASE8_REPORT.md now labels the $2/cost/expected lines as historical/paper accounting metadata and explicitly blocks real-money placement, sizing, bankroll, stop-loss, or scale-up interpretation from the legacy Phase 8 source report used by the scorecard fingerprint",
        )
    )

    checks.append(
        require(
            "Main table stays split-aware on purpose" in saved_report
            and "2024 ROI/N" in saved_report
            and "2025 ROI/N" in saved_report
            and "OP_DURABLE_K7          P7     +22.9%   115" in saved_report
            and "-47.4%/68" in saved_report
            and "+124.6%/47" in saved_report
            and "CD_CORE_K8             P7     +56.0%    60" in saved_report
            and "+45.6%/41" in saved_report
            and "+78.2%/19" in saved_report
            and "OP_REFINED_K7          P8     +51.4%    49" in saved_report
            and "-25.5%/33" in saved_report
            and "+210.0%/16" in saved_report
            and "HOLDOUT YEAR SPLIT (2024 vs 2025)" in saved_report
            and "- OP_DURABLE_K7: 2024 -47.4% on 68 | 2025 +124.6% on 47" in saved_report
            and "- CD_CORE_K8: 2024 +45.6% on 41 | 2025 +78.2% on 19" in saved_report
            and "- OP_REFINED_K7: 2024 -25.5% on 33 | 2025 +210.0% on 16" in saved_report,
            "holdout_split_text",
            "the text scorecard now keeps the 2024-vs-2025 split visible in both the main ranked table and the compact split section",
        )
    )

    checks.append(
        require(
            "WATCH-LIST TRIAGE (shadow only, not a promotion queue)" in saved_report
            and "CI-ONLY PROMOTION CHECK" in saved_report
            and "Use this when a positive bootstrap CI lower bound starts to look like a decision trigger." in saved_report
            and "OP_REFINED_K7: positive CI lower bound (+11.2%) is support context only; ci_only_promotion_allowed=false." in saved_report
            and "20-row promotion-review / 30-row anchor-displacement paper-observation gates are uncleared" in saved_report
            and "Use this when a WATCH rule's aggregate holdout ROI starts to look stronger than the sample behind it." in saved_report
            and "OP_REFINED_K7" in saved_report
            and "closest OP challenger, but mixed years and only 49 forward races" in saved_report
            and "DMR_FALL_K7" in saved_report
            and "only 1 observed holdout year so far; no train-only support yet" in saved_report
            and "KEE_K9" in saved_report
            and "clean two-year sign, but still only 20 forward races and CI crosses zero" in saved_report
            and "SA_K9" in saved_report
            and "clean two-year sign, but still only 11 forward races and CI crosses zero" in saved_report
            and "Bottom line: OP_REFINED_K7 is the closest shadow challenger because it stays inside the strongest current family," in saved_report
            and "but none of the WATCH rules has enough forward support to displace OP_DURABLE_K7 or join the primary paper basket yet." in saved_report,
            "watch_triage_text",
            "the text scorecard now gives each WATCH rule an explicit blocker and makes OP_REFINED_K7's positive CI lower bound support context only, so Phase 8 shadow names read as observation-only pockets instead of a vague promotion queue",
        )
    )

    checks.append(
        require(
            "  2024 ROI/N    = year-specific holdout ROI and race count for 2024" in saved_report
            and "  2025 ROI/N    = year-specific holdout ROI and race count for 2025" in saved_report
            and "KEY INSIGHT: OP_DURABLE_K7 is the safest anchor because it has the largest real holdout sample" in saved_report
            and "Small-sample Phase 8 winners stay in WATCH until" in saved_report,
            "key_insight_text",
            "the text scorecard still states the conservative anchor insight and now documents the main-table year-split columns explicitly in the legend, with WATCH still framed as shadow-only rather than promotion-ready",
        )
    )

    checks.append(
        require(
            True,
            "cli_stdout_surface",
            "the real forward_evidence_scorecard.py CLI still prints the same ranked table plus save notices that it writes through the generated text and CSV surfaces",
        )
    )

    checks.append(
        require(
            True,
            "cli_pinned_rerender",
            "the CLI can now rerender the scorecard reproducibly with a pinned Generated timestamp, explicit frozen-summary / walk-forward source paths, custom output paths, and side-effect-free stdout-only mode",
        )
    )
    checks.append(
        require(
            True,
            "cli_generated_at_requires_timezone_label",
            "the real CLI now rejects pinned generated-at values that omit an explicit UTC/CET/CEST timezone label before writing or printing a scorecard, preventing ambiguous source-scorecard timestamps",
        )
    )

    checks.append(
        require(
            True,
            "cli_scratch_root_project_local",
            "the forward-evidence scorecard CLI fixture now writes temporary rebuild and negative-test files under the project-local status-validation scratch root, and that scratch root is cleared before each fixture run",
        )
    )

    checks.append(
        require(
            scratch_meta["tmp_parent_is_project_local"] is True
            and scratch_meta["tmp_parent_cleared_before_fixture_run"] is True
            and scratch_meta["tmp_parent"] == str(TMP_PARENT),
            "cli_scratch_metadata_published",
            "the validation JSON now publishes top-level scratch metadata so parent rollups can verify the project-local scorecard fixture root directly",
        )
    )

    checks.append(
        require(
            True,
            "missing_source_slice_fails_fast",
            "the real CLI now fails fast if a required frozen holdout/year slice disappears instead of silently inventing a zero-filled scorecard row",
        )
    )

    checks.append(
        require(
            True,
            "conflicting_duplicate_slice_fails_fast",
            "the real CLI now rejects conflicting duplicate frozen-summary rows (for example BEL year duplicates that stop agreeing) instead of silently taking the first one",
        )
    )

    checks.append(
        require(
            True,
            "bootstrap_ci_source_text_missing_fails_fast",
            "the real CLI now rejects a custom Phase 7/8 report that lacks an exact report_text_exact bootstrap-CI source line before writing scorecard outputs, so report fingerprints cannot imply provenance that the supplied report does not contain",
        )
    )
    checks.append(
        require(
            True,
            "phase8_bootstrap_ci_source_text_missing_fails_fast",
            "the real CLI now separately rejects a custom Phase 8 report that lacks exact report_text_exact bootstrap-CI source lines before writing scorecard outputs, pinning OP_REFINED_K7 / Phase 8 watch-list CI provenance instead of relying only on the Phase 7 negative fixture",
        )
    )

    suite_read = build_suite_read(df)

    payload = {
        "suite_status": "pass",
        "artifact": {
            "saved_csv": SCORECARD_CSV.name,
            "saved_txt": SCORECARD_TXT.name,
            "saved_json": SCORECARD_JSON.name,
            "status": "pass",
            "rows": int(len(saved_df)),
            "generated_at": generated_at,
            "cli_surface_checked": True,
            "tmp_parent": scratch_meta["tmp_parent"],
            "tmp_parent_is_project_local": scratch_meta["tmp_parent_is_project_local"],
            "tmp_parent_cleared_before_fixture_run": scratch_meta["tmp_parent_cleared_before_fixture_run"],
        },
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "valid_evidence_scope": fes.VALID_EVIDENCE_SCOPE,
        "evidence_boundary": fes.MACHINE_READABLE_EVIDENCE_BOUNDARY,
        "scratch": scratch_meta,
        "summary": {
            "scorecard_anchor": str(top["rule_id"]),
            "anchor_tier": str(top["tier"]),
            "anchor_holdout_races": int(top["holdout_races"]),
            "anchor_holdout_split": {
                "2024": {
                    "roi": float(top["holdout_2024_roi"]),
                    "races": int(top["holdout_2024_races"]),
                },
                "2025": {
                    "roi": float(top["holdout_2025_roi"]),
                    "races": int(top["holdout_2025_races"]),
                },
            },
            "anchor_wf_selected": str(top["wf_selected"]),
            "paper_rule": str(cd_core["rule_id"]),
            "watch_rule": str(op_refined["rule_id"]),
            "dormant_rule": str(bel["rule_id"]),
            "suite_read": suite_read,
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "tmp_parent": scratch_meta["tmp_parent"],
            "tmp_parent_is_project_local": scratch_meta["tmp_parent_is_project_local"],
            "tmp_parent_cleared_before_fixture_run": scratch_meta["tmp_parent_cleared_before_fixture_run"],
        },
    }

    lines = [
        "# Forward Evidence Scorecard Validation",
        "",
        "This report validates the forward-evidence ranking artifact directly, including the saved CSV table, its bootstrap-CI source-note columns, and CSV/JSON source-note parity against the bootstrap source map, the text scorecard surface Cole is likely to read first, the JSON metadata sidecar for automation, the text/CSV/JSON source-scope / non-live-evidence disclosure, the machine-readable JSON evidence boundary, the decision-change gates and machine-readable decision-gate minimums, the real CLI stdout table plus save notices, the fail-fast source-drift checks for missing or conflicting frozen slices, the exact bootstrap-CI report-text fail-fast check for custom Phase 7/8 report inputs, the PHASE7_REPORT.md paper-only risk boundary, and the PHASE8_REPORT.md shadow-only cost boundary.",
        "",
        "## Artifact Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Temporary fixture root: `{tmp_parent}` (cleared before CLI fixture run)",
        f"- Saved artifacts: `{SCORECARD_CSV.name}`, `{SCORECARD_TXT.name}`, `{SCORECARD_JSON.name}`",
        f"- valid_evidence_scope={fes.VALID_EVIDENCE_SCOPE}",
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
            f"- Generated timestamp pinned from saved text artifact: {generated_at}",
            f"- Generated timestamp timezone contract: `{fes.GENERATED_AT_TIMEZONE_CONTRACT}`",
            f"- Source scope / evidence boundary: valid_evidence_scope={fes.VALID_EVIDENCE_SCOPE}; frozen holdout + train-only walk-forward only; no live paper-trade ledger, scanner, settlement-audit, or current-day profitability results are consumed; the same scope, boundary, and bootstrap-CI source notes are carried into the CSV rows and checked against the JSON source map, while the JSON sidecar now also publishes a machine-readable evidence_boundary plus evidence_boundary_text",
            "- Source-drift guardrail: missing required rule/year slices, conflicting duplicate frozen-summary rows, and custom report inputs missing exact bootstrap-CI source text now fail fast instead of degrading into invented zero rows, silent first-row wins, or misleading report-fingerprint provenance",
            f"- Anchor row: `{top['rule_id']}` ({top['tier']})",
            f"- Anchor holdout split: 2024 {float(top['holdout_2024_roi']):+.2f}% on {int(top['holdout_2024_races'])}, 2025 {float(top['holdout_2025_roi']):+.2f}% on {int(top['holdout_2025_races'])}",
            f"- Paper row: `{cd_core['rule_id']}` ({cd_core['tier']})",
            f"- Watch row: `{op_refined['rule_id']}` ({op_refined['tier']})",
            f"- Dormant row: `{bel['rule_id']}` ({bel['tier']})",
            "",
        ]
    )

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
