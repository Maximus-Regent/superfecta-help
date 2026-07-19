#!/usr/bin/env python3
"""
Validation for compare_recommender_scope_paths.py.

Purpose:
- keep the scope-comparison artifact reproducible
- pin the saved JSON / markdown surfaces against a fresh rebuild
- pin the real CLI stdout report plus save notices
- pin the selective-vs-widened ticket comparison onto the intended guardrail read
"""

from __future__ import annotations

import json
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import compare_recommender_scope_paths as crsp

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "compare_recommender_scope_paths.py"
OUT_MD = BASE / "compare_recommender_scope_paths.md"
OUT_JSON = BASE / "compare_recommender_scope_paths.json"
REPORT_DIR = BASE / "out" / "status_validation" / "compare_recommender_scope_paths"
REPORT_MD = REPORT_DIR / "compare_recommender_scope_paths_validation.md"
REPORT_JSON = REPORT_DIR / "compare_recommender_scope_paths_validation.json"
TMP_PARENT = REPORT_DIR / "_tmp"
REBUILD_COMMAND = "python3 validate_compare_recommender_scope_paths.py"
VALID_EVIDENCE_SCOPE = crsp.VALID_EVIDENCE_SCOPE


def require(condition: bool, label: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    return {"check": label, "status": "pass", "detail": detail}


def build_payload(
    cross_family_csv: Path = crsp.CROSS_FAMILY_CSV,
    scorecard_json: Path = crsp.FORWARD_SCORECARD_JSON,
    current_evidence_json: Path = crsp.CURRENT_EVIDENCE_JSON,
) -> dict[str, Any]:
    return crsp.build_payload(
        cross_family_csv=cross_family_csv,
        scorecard_json=scorecard_json,
        current_evidence_json=current_evidence_json,
    )


def build_expected_json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2) + "\n"


def build_expected_cli_stdout(markdown: str, *, md_name: str = OUT_MD.name, json_name: str = OUT_JSON.name) -> str:
    return markdown + f"Saved: {md_name}\nSaved: {json_name}\n"


def strip_code_cell(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        return value[1:-1]
    return value


def fingerprint_path(path_text: str) -> dict[str, Any]:
    path = Path(path_text)
    if not path.is_absolute():
        path = BASE / path
    data = path.read_bytes()
    return {
        "path": path_text,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def parse_source_provenance_table(markdown: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    in_table = False
    for line in markdown.splitlines():
        if line == "| Source | Path | Bytes | SHA-256 |":
            in_table = True
            continue
        if not in_table:
            continue
        if line.startswith("|---"):
            continue
        if not line.startswith("|"):
            break
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) != 4:
            raise AssertionError(f"unexpected source provenance row shape: {line}")
        source, path, byte_text, sha256 = parts
        source = strip_code_cell(source)
        rows[source] = {
            "source": source,
            "path": strip_code_cell(path),
            "bytes": int(byte_text),
            "sha256": strip_code_cell(sha256),
        }
    if not rows:
        raise AssertionError("source provenance table was not found or had no rows")
    return rows


def prepare_tmp_parent() -> Path:
    """Use project-local scratch space so CLI fixture writes avoid system temp quotas."""
    if TMP_PARENT.exists():
        shutil.rmtree(TMP_PARENT)
    TMP_PARENT.mkdir(parents=True, exist_ok=True)
    return TMP_PARENT


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_parent = prepare_tmp_parent()
    scratch_meta = {
        "tmp_parent": str(tmp_parent),
        "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
        "tmp_parent_cleared_before_fixture_run": True,
    }
    if not OUT_MD.exists() or not OUT_JSON.exists():
        raise AssertionError("scope comparison artifacts were not created")

    rebuilt_payload = build_payload()
    rebuilt_json_text = build_expected_json_text(rebuilt_payload)
    rebuilt_markdown = crsp.build_markdown(rebuilt_payload)
    saved_json_text = OUT_JSON.read_text(encoding="utf-8")
    saved_md = OUT_MD.read_text(encoding="utf-8")

    if saved_json_text != rebuilt_json_text:
        raise AssertionError("compare_recommender_scope_paths.json drifted from a fresh rebuild")
    if saved_md != rebuilt_markdown:
        raise AssertionError("compare_recommender_scope_paths.md drifted from a fresh rebuild")

    payload = json.loads(saved_json_text)
    current_read = payload.get("summary", {}).get("current_read", "")
    if (
        "selective recommender path" not in current_read
        or "allow-all override" not in current_read
        or "raise stake and off-scope share" not in current_read
    ):
        raise AssertionError("current_read lost the selective-vs-allow-all framing or the stake/off-scope normalization read")
    modeled_ev_read = payload.get("summary", {}).get("modeled_ev_read", "")
    if (
        "stub-race EV, not observed settlement P&L" not in modeled_ev_read
        or "tickets outside the selective scanner universe" not in modeled_ev_read
    ):
        raise AssertionError("modeled_ev_read lost the stub-EV / not-observed-P&L boundary")

    scenarios = payload.get("scenarios", [])
    by_name = {row["name"]: row for row in scenarios}
    mixed = by_name["mixed_universe_op_anchor"]
    off_only = by_name["off_universe_only_op_anchor"]

    markdown_needles = [
        "# Recommender Scope Path Comparison",
        "This is a controlled scope comparison, not a paper-promotion test.",
        "OP_DURABLE_K7",
        "CD_CORE_K8",
        "OP_REFINED_K7",
        "Mixed-universe OP anchor race",
        "Off-universe-only OP anchor race",
        "Modeled expected-profit deltas below are stub-race EV diagnostics, not observed settlement P&L or live profitability evidence.",
        "Machine-readable boundary: `evidence_boundary.not_current_paper_scope_change_evidence=true`; the explicit allow-all override remains `research_only_counterfactual` and does not widen the current paper default.",
        "Scorecard-sourced 30/20/100 gates still apply",
        "Scorecard audit route:",
        "Current-evidence rebuild route:",
        "copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks",
        "SCORECARD_RANKING_CONTRACT_AUDIT.md",
        "validate_scorecard_ranking_contract_audit.py",
        "current_evidence_summary.json.rebuild_validation_contract",
        "python3 paper_trade_settlement_audit.py",
        "python3 current_evidence_summary.py",
        "python3 validate_current_evidence_summary.py",
        "real-money discussion needs 100 total settled usable-ROI observations plus no BAQ-as-BEL substitution",
        "Audit route read: Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus `python3 validate_scorecard_ranking_contract_audit.py`",
        "Rebuild route read: source-byte changes that affect current totals require",
        "This route is not forward performance, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "| Scenario | Scored combos | Default path | Allow-all path | Stake change vs default | Widened off-scope share | Modeled EV lift source |",
        "The explicit `--allow-all-combos` path is useful as a counterfactual research switch, not as evidence that the current paper scope should widen now.",
        "Any widened expected-profit bump here must be read alongside stake inflation and off-scope ticket share",
        "The modeled expected-profit lift is not observed P&L; in these fixtures the lift comes mostly or entirely from tickets the default selective path would exclude.",
        "These byte hashes are reproducibility metadata for the scope guardrail only; they are not settled ROI, not promotion readiness, not live profitability, and not real-money evidence.",
    ]
    source_fingerprints = payload.get("source_provenance", {}).get("source_fingerprints", {})
    source_provenance_rows = parse_source_provenance_table(saved_md)

    with tempfile.TemporaryDirectory(prefix="scope_paths_", dir=tmp_parent) as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        for src in [
            SCRIPT,
            BASE / "ev_ticket_engine.py",
            BASE / "paper_trade_recommender.py",
            crsp.CROSS_FAMILY_CSV,
            crsp.FORWARD_SCORECARD_JSON,
            crsp.CURRENT_EVIDENCE_JSON,
        ]:
            shutil.copy2(src, tmpdir / src.name)
        cli_result = subprocess.run(
            [sys.executable, SCRIPT.name],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        cli_json_text = (tmpdir / OUT_JSON.name).read_text(encoding="utf-8")
        cli_md = (tmpdir / OUT_MD.name).read_text(encoding="utf-8")
        if cli_json_text != rebuilt_json_text:
            raise AssertionError("CLI-generated compare_recommender_scope_paths.json drifted from a fresh rebuild")
        if cli_md != rebuilt_markdown:
            raise AssertionError("CLI-generated compare_recommender_scope_paths.md drifted from a fresh rebuild")
        expected_cli_stdout = build_expected_cli_stdout(cli_md)
        if cli_result.stdout != expected_cli_stdout:
            raise AssertionError("compare_recommender_scope_paths.py CLI stdout no longer matches the generated markdown plus Saved: lines")

        custom_cross_family_csv = tmpdir / "custom_cross_family_decision.csv"
        custom_md = tmpdir / "custom_scope_paths.md"
        custom_json = tmpdir / "custom_scope_paths.json"
        custom_cross_text = (tmpdir / crsp.CROSS_FAMILY_CSV.name).read_text(encoding="utf-8")
        for old_value, new_value in {
            "OP_DURABLE_K7": "ALT_ANCHOR_K7",
            "CD_CORE_K8": "ALT_PAPER_COMPANION_K8",
            "OP_REFINED_K7": "ALT_CLOSEST_SHADOW_K7",
        }.items():
            custom_cross_text = custom_cross_text.replace(old_value, new_value)
        custom_cross_family_csv.write_text(custom_cross_text, encoding="utf-8")
        custom_payload = build_payload(cross_family_csv=custom_cross_family_csv)
        custom_payload["source_provenance"]["source_fingerprints"]["cross_family_decision_card"][
            "path"
        ] = custom_cross_family_csv.name
        custom_expected_json_text = build_expected_json_text(custom_payload)
        custom_expected_md = crsp.build_markdown(custom_payload)
        custom_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--cross-family-csv",
                str(custom_cross_family_csv),
                "--md-output",
                str(custom_md),
                "--json-output",
                str(custom_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        custom_json_text = custom_json.read_text(encoding="utf-8")
        custom_md_text = custom_md.read_text(encoding="utf-8")
        if custom_json_text != custom_expected_json_text:
            raise AssertionError("custom cross-family CLI JSON drifted from the source-driven rebuild")
        if custom_md_text != custom_expected_md:
            raise AssertionError("custom cross-family CLI markdown drifted from the source-driven rebuild")
        custom_loaded = json.loads(custom_json_text)
        if custom_loaded["guardrail"]["anchor"] != "ALT_ANCHOR_K7":
            raise AssertionError("custom cross-family anchor did not reach the recommender-scope JSON")
        if custom_loaded["guardrail"]["primary_companion"] != "ALT_PAPER_COMPANION_K8":
            raise AssertionError("custom cross-family paper companion did not reach the recommender-scope JSON")
        if custom_loaded["guardrail"]["secondary_shadow"] != "ALT_CLOSEST_SHADOW_K7":
            raise AssertionError("custom cross-family closest shadow did not reach the recommender-scope JSON")
        for expected in [
            "`ALT_ANCHOR_K7` as the safest current paper anchor",
            "`ALT_PAPER_COMPANION_K8` remains the primary OP/CD paper-basket companion",
            "`ALT_CLOSEST_SHADOW_K7` stays the smaller same-family OP shadow challenger",
            "not evidence that widened stub-race tickets should outrank `ALT_PAPER_COMPANION_K8`",
            "without claiming that widened stub-race EV should outrank `ALT_ANCHOR_K7`, `ALT_PAPER_COMPANION_K8`, or the broader frozen holdout and walk-forward evidence chain",
        ]:
            if expected not in custom_md_text:
                raise AssertionError(f"custom cross-family hierarchy did not render dynamic markdown text: {expected}")
        for stale in ["OP_DURABLE_K7", "CD_CORE_K8", "OP_REFINED_K7"]:
            if stale in custom_json_text or stale in custom_md_text:
                raise AssertionError(f"custom cross-family hierarchy render still contains stale default rule id: {stale}")
        expected_custom_stdout = build_expected_cli_stdout(custom_md_text, md_name=custom_md.name, json_name=custom_json.name)
        if custom_result.stdout != expected_custom_stdout:
            raise AssertionError("custom cross-family CLI stdout no longer matches the generated markdown plus Saved: lines")

        missing_gate_block_scorecard_json = tmpdir / "missing_gate_block_forward_evidence_scorecard.json"
        missing_gate_block_output_dir = tmpdir / "missing_gate_block_nested_output" / "artifacts"
        missing_gate_block_md = missing_gate_block_output_dir / "missing_gate_block_scope_paths_should_not_write.md"
        missing_gate_block_json = missing_gate_block_output_dir / "missing_gate_block_scope_paths_should_not_write.json"
        missing_gate_block_payload = json.loads((tmpdir / crsp.FORWARD_SCORECARD_JSON.name).read_text(encoding="utf-8"))
        missing_gate_block_payload.pop("decision_gate_minimums", None)
        missing_gate_block_scorecard_json.write_text(json.dumps(missing_gate_block_payload, indent=2) + "\n", encoding="utf-8")
        missing_gate_block_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--scorecard-json",
                str(missing_gate_block_scorecard_json),
                "--md-output",
                str(missing_gate_block_md),
                "--json-output",
                str(missing_gate_block_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_gate_block_result.returncode == 0:
            raise AssertionError("compare_recommender_scope_paths.py unexpectedly accepted a scorecard missing decision_gate_minimums")
        missing_gate_block_text = f"{missing_gate_block_result.stdout}\n{missing_gate_block_result.stderr}"
        if "missing decision_gate_minimums" not in missing_gate_block_text:
            raise AssertionError("missing scorecard gate-block failure no longer says decision_gate_minimums is required")
        if missing_gate_block_output_dir.exists() or missing_gate_block_md.exists() or missing_gate_block_json.exists():
            raise AssertionError("bad scorecard gate-block CLI path created output directories or wrote recommender-scope artifacts before failing source validation")

        bad_gate_scorecard_json = tmpdir / "bad_gate_forward_evidence_scorecard.json"
        bad_gate_output_dir = tmpdir / "bad_gate_nested_output" / "artifacts"
        bad_gate_md = bad_gate_output_dir / "bad_gate_scope_paths_should_not_write.md"
        bad_gate_json = bad_gate_output_dir / "bad_gate_scope_paths_should_not_write.json"
        bool_gate_scorecard_json = tmpdir / "bool_gate_forward_evidence_scorecard.json"
        bool_gate_output_dir = tmpdir / "bool_gate_nested_output" / "artifacts"
        bool_gate_md = bool_gate_output_dir / "bool_gate_scope_paths_should_not_write.md"
        bool_gate_json = bool_gate_output_dir / "bool_gate_scope_paths_should_not_write.json"
        non_positive_gate_scorecard_json = tmpdir / "non_positive_gate_forward_evidence_scorecard.json"
        non_positive_gate_output_dir = tmpdir / "non_positive_gate_nested_output" / "artifacts"
        non_positive_gate_md = non_positive_gate_output_dir / "non_positive_gate_scope_paths_should_not_write.md"
        non_positive_gate_json = non_positive_gate_output_dir / "non_positive_gate_scope_paths_should_not_write.json"
        non_positive_real_money_scorecard_json = tmpdir / "non_positive_real_money_forward_evidence_scorecard.json"
        non_positive_real_money_output_dir = tmpdir / "non_positive_real_money_nested_output" / "artifacts"
        non_positive_real_money_md = (
            non_positive_real_money_output_dir / "non_positive_real_money_scope_paths_should_not_write.md"
        )
        non_positive_real_money_json = (
            non_positive_real_money_output_dir / "non_positive_real_money_scope_paths_should_not_write.json"
        )
        missing_no_baq_scorecard_json = tmpdir / "missing_no_baq_forward_evidence_scorecard.json"
        missing_no_baq_output_dir = tmpdir / "missing_no_baq_nested_output" / "artifacts"
        missing_no_baq_md = missing_no_baq_output_dir / "missing_no_baq_scope_paths_should_not_write.md"
        missing_no_baq_json = missing_no_baq_output_dir / "missing_no_baq_scope_paths_should_not_write.json"
        bad_gate_payload = json.loads((tmpdir / crsp.FORWARD_SCORECARD_JSON.name).read_text(encoding="utf-8"))
        bad_gate_payload["decision_gate_minimums"].pop("anchor_displacement")
        bad_gate_scorecard_json.write_text(json.dumps(bad_gate_payload, indent=2) + "\n", encoding="utf-8")
        bad_gate_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--scorecard-json",
                str(bad_gate_scorecard_json),
                "--md-output",
                str(bad_gate_md),
                "--json-output",
                str(bad_gate_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if bad_gate_result.returncode == 0:
            raise AssertionError("compare_recommender_scope_paths.py unexpectedly accepted a scorecard missing the anchor_displacement gate")
        bad_gate_text = f"{bad_gate_result.stdout}\n{bad_gate_result.stderr}"
        if "missing decision_gate_minimums.anchor_displacement" not in bad_gate_text:
            raise AssertionError("missing scorecard gate failure no longer names the anchor_displacement decision gate")
        if bad_gate_output_dir.exists() or bad_gate_md.exists() or bad_gate_json.exists():
            raise AssertionError("bad scorecard gate CLI path created output directories or wrote recommender-scope artifacts before failing source validation")

        bool_gate_payload = json.loads((tmpdir / crsp.FORWARD_SCORECARD_JSON.name).read_text(encoding="utf-8"))
        bool_gate_payload["decision_gate_minimums"]["anchor_displacement"][
            "min_roi_complete_settled_observations"
        ] = True
        bool_gate_scorecard_json.write_text(json.dumps(bool_gate_payload, indent=2) + "\n", encoding="utf-8")
        bool_gate_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--scorecard-json",
                str(bool_gate_scorecard_json),
                "--md-output",
                str(bool_gate_md),
                "--json-output",
                str(bool_gate_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if bool_gate_result.returncode == 0:
            raise AssertionError("compare_recommender_scope_paths.py unexpectedly accepted a boolean anchor_displacement gate floor")
        bool_gate_text = f"{bool_gate_result.stdout}\n{bool_gate_result.stderr}"
        if (
            "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations "
            "must be a positive integer"
        ) not in bool_gate_text:
            raise AssertionError("boolean scorecard gate failure no longer names the malformed anchor_displacement threshold")
        if bool_gate_output_dir.exists() or bool_gate_md.exists() or bool_gate_json.exists():
            raise AssertionError("boolean scorecard gate CLI path created output directories or wrote recommender-scope artifacts before failing source validation")

        non_positive_gate_payload = json.loads((tmpdir / crsp.FORWARD_SCORECARD_JSON.name).read_text(encoding="utf-8"))
        non_positive_gate_payload["decision_gate_minimums"]["phase8_promotion_review"][
            "min_roi_complete_settled_observations"
        ] = 0
        non_positive_gate_scorecard_json.write_text(
            json.dumps(non_positive_gate_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        non_positive_gate_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--scorecard-json",
                str(non_positive_gate_scorecard_json),
                "--md-output",
                str(non_positive_gate_md),
                "--json-output",
                str(non_positive_gate_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if non_positive_gate_result.returncode == 0:
            raise AssertionError("compare_recommender_scope_paths.py unexpectedly accepted a non-positive phase8_promotion_review gate floor")
        non_positive_gate_text = f"{non_positive_gate_result.stdout}\n{non_positive_gate_result.stderr}"
        if (
            "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations "
            "must be a positive integer"
        ) not in non_positive_gate_text:
            raise AssertionError("non-positive scorecard gate failure no longer names the malformed phase8_promotion_review threshold")
        if non_positive_gate_output_dir.exists() or non_positive_gate_md.exists() or non_positive_gate_json.exists():
            raise AssertionError("non-positive scorecard gate CLI path created output directories or wrote recommender-scope artifacts before failing source validation")

        non_positive_real_money_payload = json.loads((tmpdir / crsp.FORWARD_SCORECARD_JSON.name).read_text(encoding="utf-8"))
        non_positive_real_money_payload["decision_gate_minimums"]["real_money_discussion"][
            "min_total_settled_observations_with_usable_roi"
        ] = 0
        non_positive_real_money_scorecard_json.write_text(
            json.dumps(non_positive_real_money_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        non_positive_real_money_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--scorecard-json",
                str(non_positive_real_money_scorecard_json),
                "--md-output",
                str(non_positive_real_money_md),
                "--json-output",
                str(non_positive_real_money_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if non_positive_real_money_result.returncode == 0:
            raise AssertionError("compare_recommender_scope_paths.py unexpectedly accepted a non-positive real_money_discussion gate floor")
        non_positive_real_money_text = f"{non_positive_real_money_result.stdout}\n{non_positive_real_money_result.stderr}"
        if (
            "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi "
            "must be a positive integer"
        ) not in non_positive_real_money_text:
            raise AssertionError("non-positive real-money scorecard gate failure no longer names the malformed threshold")
        if (
            non_positive_real_money_output_dir.exists()
            or non_positive_real_money_md.exists()
            or non_positive_real_money_json.exists()
        ):
            raise AssertionError("non-positive real-money gate CLI path created output directories or wrote recommender-scope artifacts before failing source validation")

        missing_no_baq_payload = json.loads((tmpdir / crsp.FORWARD_SCORECARD_JSON.name).read_text(encoding="utf-8"))
        missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"]["also_requires"] = [
            item
            for item in missing_no_baq_payload["decision_gate_minimums"]["real_money_discussion"]["also_requires"]
            if item != "no BAQ-as-BEL substitution"
        ]
        missing_no_baq_scorecard_json.write_text(
            json.dumps(missing_no_baq_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_no_baq_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--scorecard-json",
                str(missing_no_baq_scorecard_json),
                "--md-output",
                str(missing_no_baq_md),
                "--json-output",
                str(missing_no_baq_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_no_baq_result.returncode == 0:
            raise AssertionError("compare_recommender_scope_paths.py unexpectedly accepted a scorecard missing the no-BAQ-as-BEL prerequisite")
        missing_no_baq_text = f"{missing_no_baq_result.stdout}\n{missing_no_baq_result.stderr}"
        if "must include no BAQ-as-BEL substitution" not in missing_no_baq_text:
            raise AssertionError("missing no-BAQ-as-BEL scorecard failure no longer names the prerequisite")
        if missing_no_baq_output_dir.exists() or missing_no_baq_md.exists() or missing_no_baq_json.exists():
            raise AssertionError("missing no-BAQ-as-BEL scorecard CLI path created output directories or wrote recommender-scope artifacts before failing source validation")

        missing_rebuild_current_evidence_json = tmpdir / "missing_rebuild_current_evidence_summary.json"
        missing_rebuild_output_dir = tmpdir / "missing_rebuild_nested_output" / "artifacts"
        missing_rebuild_md = missing_rebuild_output_dir / "missing_rebuild_scope_paths_should_not_write.md"
        missing_rebuild_json = missing_rebuild_output_dir / "missing_rebuild_scope_paths_should_not_write.json"
        missing_rebuild_payload = json.loads((tmpdir / crsp.CURRENT_EVIDENCE_JSON.name).read_text(encoding="utf-8"))
        missing_rebuild_payload.pop("rebuild_validation_contract", None)
        missing_rebuild_current_evidence_json.write_text(
            json.dumps(missing_rebuild_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_rebuild_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(missing_rebuild_current_evidence_json),
                "--md-output",
                str(missing_rebuild_md),
                "--json-output",
                str(missing_rebuild_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_rebuild_result.returncode == 0:
            raise AssertionError("compare_recommender_scope_paths.py unexpectedly accepted current evidence missing rebuild_validation_contract")
        missing_rebuild_text = f"{missing_rebuild_result.stdout}\n{missing_rebuild_result.stderr}"
        if "missing rebuild_validation_contract" not in missing_rebuild_text:
            raise AssertionError("missing rebuild_validation_contract failure no longer names the required current-evidence route")
        if missing_rebuild_output_dir.exists() or missing_rebuild_md.exists() or missing_rebuild_json.exists():
            raise AssertionError("missing rebuild-contract CLI path created output directories or wrote recommender-scope artifacts before failing source validation")

        weakened_rebuild_current_evidence_json = tmpdir / "weakened_rebuild_current_evidence_summary.json"
        weakened_rebuild_output_dir = tmpdir / "weakened_rebuild_nested_output" / "artifacts"
        weakened_rebuild_md = weakened_rebuild_output_dir / "weakened_rebuild_scope_paths_should_not_write.md"
        weakened_rebuild_json = weakened_rebuild_output_dir / "weakened_rebuild_scope_paths_should_not_write.json"
        weakened_rebuild_payload = json.loads((tmpdir / crsp.CURRENT_EVIDENCE_JSON.name).read_text(encoding="utf-8"))
        weakened_rebuild_payload["rebuild_validation_contract"][
            "upstream_refresh_order_is_provenance_metadata_only"
        ] = False
        weakened_rebuild_current_evidence_json.write_text(
            json.dumps(weakened_rebuild_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        weakened_rebuild_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(weakened_rebuild_current_evidence_json),
                "--md-output",
                str(weakened_rebuild_md),
                "--json-output",
                str(weakened_rebuild_json),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if weakened_rebuild_result.returncode == 0:
            raise AssertionError("compare_recommender_scope_paths.py unexpectedly accepted current evidence with a weakened rebuild_validation_contract")
        weakened_rebuild_text = f"{weakened_rebuild_result.stdout}\n{weakened_rebuild_result.stderr}"
        if "rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true" not in weakened_rebuild_text:
            raise AssertionError("weakened rebuild_validation_contract failure no longer names the provenance-only flag")
        if weakened_rebuild_output_dir.exists() or weakened_rebuild_md.exists() or weakened_rebuild_json.exists():
            raise AssertionError("weakened rebuild-contract CLI path created output directories or wrote recommender-scope artifacts before failing source validation")

    checks: list[dict[str, Any]] = []
    checks.append(
        require(
            saved_json_text == rebuilt_json_text,
            "json_matches_rebuild",
            "compare_recommender_scope_paths.json still matches a fresh rebuild",
        )
    )
    checks.append(
        require(
            saved_md == rebuilt_markdown,
            "markdown_matches_rebuild",
            "compare_recommender_scope_paths.md still matches a fresh rebuild",
        )
    )
    checks.append(
        require(
            True,
            "cli_json_matches_rebuild",
            "compare_recommender_scope_paths.py CLI still writes JSON that matches a fresh rebuild",
        )
    )
    checks.append(
        require(
            True,
            "cli_markdown_matches_rebuild",
            "compare_recommender_scope_paths.py CLI still writes markdown that matches a fresh rebuild",
        )
    )
    checks.append(
        require(
            True,
            "cli_stdout_matches_generated_report",
            "compare_recommender_scope_paths.py CLI stdout still matches the generated markdown plus its Saved: lines",
        )
    )
    checks.append(
        require(
            True,
            "custom_cross_family_hierarchy_renders_dynamically",
            "compare_recommender_scope_paths.py can now rerender from an explicit cross-family CSV and custom output paths, proving anchor / paper-companion / same-family shadow labels reach JSON, markdown guardrails, scenario rule IDs, and real CLI stdout without stale default rule IDs",
        )
    )
    checks.append(
        require(
            True,
            "missing_scorecard_gate_block_fails_fast_without_artifacts",
            "the real compare_recommender_scope_paths.py CLI now rejects a scorecard missing the whole decision_gate_minimums block before creating output directories or writing markdown/JSON artifacts",
        )
    )
    checks.append(
        require(
            True,
            "missing_scorecard_gate_fails_fast_without_artifacts",
            "the real compare_recommender_scope_paths.py CLI now rejects a scorecard missing the anchor_displacement decision gate before creating output directories or writing markdown/JSON artifacts",
        )
    )
    checks.append(
        require(
            True,
            "malformed_scorecard_gate_floor_fails_fast_without_artifacts",
            "the real compare_recommender_scope_paths.py CLI now rejects a boolean anchor_displacement observation floor before creating output directories or writing markdown/JSON artifacts",
        )
    )
    checks.append(
        require(
            True,
            "non_positive_scorecard_gate_floor_fails_fast_without_artifacts",
            "the real compare_recommender_scope_paths.py CLI now rejects a non-positive phase8_promotion_review observation floor before creating output directories or writing markdown/JSON artifacts",
        )
    )
    checks.append(
        require(
            True,
            "non_positive_real_money_scorecard_gate_floor_fails_fast_without_artifacts",
            "the real compare_recommender_scope_paths.py CLI now rejects a non-positive real_money_discussion observation floor before creating output directories or writing markdown/JSON artifacts",
        )
    )
    checks.append(
        require(
            True,
            "missing_no_baq_prerequisite_fails_fast_without_artifacts",
            "the real compare_recommender_scope_paths.py CLI now rejects a real_money_discussion gate missing the no-BAQ-as-BEL prerequisite before creating output directories or writing markdown/JSON artifacts",
        )
    )
    checks.append(
        require(
            len(scenarios) == 2,
            "scenario_count",
            "scenario count still equals 2",
        )
    )
    checks.append(
        require(
            mixed["default_path"]["decision"] == "BET"
            and mixed["default_filtered_combo_count"] == 1
            and mixed["allow_all_out_of_scope_ticket_count"] == 2
            and mixed["allow_all_path"]["ticket_combos"] == ["9-2-3-5", "1-2-3-4", "1-2-3-5"]
            and mixed["allow_all_out_of_scope_share_pct"] == 66.7
            and mixed["allow_all_off_scope_stake"] == 5.6
            and mixed["allow_all_off_scope_expected_profit"] == 9.35
            and mixed["allow_all_off_scope_expected_profit_share_pct"] == 91.4
            and mixed["modeled_expected_profit_delta_vs_default"] == 9.35
            and mixed["stake_multiple_vs_default"] == 6.1
            and mixed["stake_delta_vs_default"] == 5.6,
            "mixed_default_vs_widened",
            "mixed-universe OP anchor race still shows selective BET from one in-scope combo, widened BET with two out-of-scope tickets, 66.7% ticket off-scope share, 6.1x stake inflation, and $9.35 / 91.4% of widened modeled expected profit coming from off-scope tickets",
        )
    )
    checks.append(
        require(
            off_only["default_path"]["decision"] == "NO BET"
            and off_only["allow_all_path"]["decision"] == "BET"
            and off_only["allow_all_out_of_scope_ticket_count"] == 1
            and off_only["allow_all_out_of_scope_share_pct"] == 100.0
            and off_only["allow_all_off_scope_stake"] == 3.7
            and off_only["allow_all_off_scope_expected_profit"] == 29.6
            and off_only["allow_all_off_scope_expected_profit_share_pct"] == 100.0
            and off_only["modeled_expected_profit_delta_vs_default"] == 29.6
            and off_only["stake_multiple_vs_default"] is None
            and off_only["stake_delta_vs_default"] == 3.7,
            "off_universe_only_default_vs_widened",
            "off-universe-only OP anchor race still shows selective NO BET versus widened BET with one out-of-scope ticket, 100.0% off-scope share, brand-new widened exposure from a zero-stake base, and all widened modeled expected profit coming from off-scope tickets",
        )
    )
    checks.append(
        require(
            payload["guardrail"]["anchor"] == "OP_DURABLE_K7"
            and payload["guardrail"].get("primary_companion") == "CD_CORE_K8"
            and payload["guardrail"]["primary_shadow"] == "CD_CORE_K8"
            and payload["guardrail"]["secondary_shadow"] == "OP_REFINED_K7",
            "paper_companion_order_in_json",
            "scope comparison JSON now carries the current anchor plus paper-basket companion and same-family shadow-challenger ordering for the live selective lane while preserving the legacy primary_shadow key",
        )
    )
    gate_summary = payload.get("scorecard_decision_gate_minimums", {})
    scorecard_audit_route = payload.get("scorecard_audit_route", {})
    rebuild_contract = payload.get("current_evidence_rebuild_validation_contract", {})
    evidence_boundary = payload.get("evidence_boundary", {})
    checks.append(
        require(
            gate_summary.get("source") == "forward_evidence_scorecard.json"
            and gate_summary.get("source_path") == "decision_gate_minimums"
            and gate_summary.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and gate_summary.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and gate_summary.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and gate_summary.get("real_money_no_baq_as_bel_required") is True
            and "counterfactual research only" in str(gate_summary.get("read") or "")
            and "no-BAQ-as-BEL prerequisite" in str(gate_summary.get("read") or ""),
            "scorecard_decision_gate_minimums_published",
            "scope comparison JSON now publishes the forward_evidence_scorecard.json decision_gate_minimums read so widened allow-all counterfactuals cannot bypass the 30/20/100 observation floors or the no-BAQ-as-BEL prerequisite",
        )
    )
    checks.append(
        require(
            isinstance(scorecard_audit_route, dict)
            and scorecard_audit_route.get("source") == "current_evidence_summary.json"
            and scorecard_audit_route.get("source_path") == "scorecard_audit_route"
            and scorecard_audit_route.get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route.get("json_path") == "scorecard_ranking_contract_audit.json"
            and scorecard_audit_route.get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route.get("gate_floor_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get(
                "anchor_displacement_min_roi_complete_settled_observations"
            )
            == 30
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get(
                "phase8_promotion_review_min_roi_complete_settled_observations"
            )
            == 20
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get(
                "real_money_discussion_min_total_settled_observations_with_usable_roi"
            )
            == 100
            and scorecard_audit_route.get("gate_floor_snapshot", {}).get("real_money_no_baq_as_bel_required")
            is True
            and scorecard_audit_route.get("artifacts_present") is True
            and scorecard_audit_route.get("not_forward_performance_evidence") is True
            and scorecard_audit_route.get("not_settled_roi_evidence") is True
            and scorecard_audit_route.get("not_promotion_readiness_evidence") is True
            and scorecard_audit_route.get("not_live_profitability_evidence") is True
            and scorecard_audit_route.get("not_bankroll_guidance") is True
            and scorecard_audit_route.get("not_real_money_evidence") is True
            and "copied 30/20/100 gate floors" in str(scorecard_audit_route.get("route_read") or "")
            and "tier-first ranking" in str(scorecard_audit_route.get("route_read") or "")
            and "OP_REFINED CI-only support context" in str(scorecard_audit_route.get("route_read") or "")
            and "no-BAQ-as-BEL prerequisite" in str(scorecard_audit_route.get("route_read") or "")
            and "Scorecard audit route:" in saved_md
            and "Audit route read:" in saved_md,
            "scorecard_audit_route_published",
            "scope comparison JSON/markdown now republishes current_evidence_summary.json.scorecard_audit_route so copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks route to the dedicated scorecard audit without becoming forward evidence",
        )
    )
    checks.append(
        require(
            isinstance(rebuild_contract, dict)
            and rebuild_contract.get("source") == "current_evidence_summary.json"
            and rebuild_contract.get("source_path") == "rebuild_validation_contract"
            and rebuild_contract.get("upstream_refresh_order_commands")
            == [
                "python3 paper_trade_settlement_audit.py",
                "python3 current_evidence_summary.py",
                "python3 validate_current_evidence_summary.py",
            ]
            and rebuild_contract.get("prerequisite_rebuild_command") == "python3 paper_trade_settlement_audit.py"
            and rebuild_contract.get("rebuild_command") == "python3 current_evidence_summary.py"
            and rebuild_contract.get("direct_validation_command") == "python3 validate_current_evidence_summary.py"
            and rebuild_contract.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and rebuild_contract.get("requires_source_consistency_before_quoting_current_totals") is True
            and rebuild_contract.get("upstream_refresh_order_is_provenance_metadata_only") is True
            and rebuild_contract.get("not_settled_roi_or_real_money_evidence") is True
            and "Current-evidence rebuild route:" in saved_md
            and "Rebuild route read:" in saved_md
            and "python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> `python3 validate_current_evidence_summary.py" in saved_md,
            "current_evidence_rebuild_validation_contract_published",
            "scope comparison JSON/markdown now republishes current_evidence_summary.json.rebuild_validation_contract so source-byte changes route through settlement-audit -> current-bridge -> bridge-validator before anyone quotes current totals from this counterfactual surface",
        )
    )
    checks.append(
        require(
            True,
            "missing_current_evidence_rebuild_contract_fails_fast_without_artifacts",
            "the real compare_recommender_scope_paths.py CLI now rejects a current_evidence_summary.json missing rebuild_validation_contract before creating output directories or writing markdown/JSON artifacts",
        )
    )
    checks.append(
        require(
            True,
            "weakened_current_evidence_rebuild_contract_fails_fast_without_artifacts",
            "the real compare_recommender_scope_paths.py CLI now rejects a current_evidence_summary.json whose rebuild_validation_contract weakens the provenance-only flag before creating output directories or writing markdown/JSON artifacts",
        )
    )
    checks.append(
        require(
            isinstance(evidence_boundary, dict)
            and payload.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and evidence_boundary.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}" in saved_md
            and evidence_boundary.get("artifact_role") == "selective-vs-allow-all recommender scope guardrail"
            and evidence_boundary.get("anchor_rule_id") == "OP_DURABLE_K7"
            and evidence_boundary.get("primary_companion_rule_id") == "CD_CORE_K8"
            and evidence_boundary.get("same_family_shadow_rule_id") == "OP_REFINED_K7"
            and evidence_boundary.get("allow_all_override_role") == "research_only_counterfactual"
            and evidence_boundary.get("default_scope_role") == "current_paper_default"
            and evidence_boundary.get("not_current_paper_scope_change_evidence") is True
            and evidence_boundary.get("not_observed_settlement_pnl") is True
            and evidence_boundary.get("not_settled_roi_evidence") is True
            and evidence_boundary.get("not_promotion_readiness_evidence") is True
            and evidence_boundary.get("not_anchor_change_evidence") is True
            and evidence_boundary.get("not_live_profitability_evidence") is True
            and evidence_boundary.get("not_real_money_evidence") is True
            and "scorecard-sourced 30/20/100 gate review" in evidence_boundary.get("scope_change_requires", [])
            and "no BAQ-as-BEL substitution" in evidence_boundary.get("scope_change_requires", [])
            and "do not use allow-all counterfactuals to widen the current paper default"
            in evidence_boundary.get("non_goals", [])
            and "do not promote the same-family shadow rule from this artifact" in evidence_boundary.get("non_goals", [])
            and "do not displace the current paper anchor from this artifact" in evidence_boundary.get("non_goals", []),
            "scope_evidence_boundary_published",
            "scope comparison JSON/markdown now publish the raw valid_evidence_scope plus a machine-readable boundary that keeps allow-all scope widening as a research-only counterfactual rather than current paper-default, anchor-change, promotion, or real-money evidence",
        )
    )
    checks.append(
        require(
            all(needle in saved_md for needle in markdown_needles)
            and "`CD_CORE_K8` remains the primary OP/CD paper-basket companion" in saved_md
            and "not evidence that widened stub-race tickets should outrank `CD_CORE_K8`" in saved_md
            and "Scorecard-sourced 30/20/100 gates still apply" in saved_md
            and "Current-evidence rebuild route:" in saved_md
            and "settlement-ledger byte changes" in saved_md
            and "not scope-change evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence" in saved_md
            and "Gate read: widened scope comparisons are counterfactual research only" in saved_md
            and "$+9.35 lift; $9.35 / 91.4% off-scope" in saved_md
            and "$+29.60 lift; $29.60 / 100.0% off-scope" in saved_md
            and "Modeled EV boundary: $+9.35 widened modeled expected-profit lift is stub EV, not observed P&L" in saved_md
            and "Modeled EV boundary: $+29.60 widened modeled expected-profit lift is stub EV, not observed P&L" in saved_md
            and "6.1x ($+5.60)" in saved_md
            and "new $3.70 exposure" in saved_md
            and "66.7%" in saved_md
            and "100.0%" in saved_md,
            "markdown_guardrail",
            "markdown guardrail still says this is not a paper-promotion test, now carries the explicit anchor / paper-companion / shadow-challenger context, scorecard-sourced gate floors, the scorecard-audit route, the current-evidence rebuild route, and directly exposes stake inflation, off-scope share, and the not-observed-P&L modeled EV lift source for the widened path",
        )
    )
    checks.append(
        require(
            tmp_parent == TMP_PARENT
            and tmp_parent.is_relative_to(BASE)
            and TMP_PARENT.parent == REPORT_DIR,
            "cli_scratch_root_project_local",
            f"recommender-scope CLI fixture and custom hierarchy scratch writes use project-local temporary root {tmp_parent}, cleared before the fixture run",
        )
    )
    checks.append(
        require(
            scratch_meta["tmp_parent_is_project_local"] is True
            and scratch_meta["tmp_parent_cleared_before_fixture_run"] is True
            and Path(scratch_meta["tmp_parent"]) == TMP_PARENT,
            "cli_scratch_metadata_published",
            "recommender-scope validation now publishes top-level project-local scratch metadata so parent rollups can verify the cleared fixture root without parsing prose or nested summary fields",
        )
    )
    checks.append(
        require(
            set(source_provenance_rows) == set(source_fingerprints)
            and all(
                source_provenance_rows[name]["path"] == fingerprint["path"]
                and source_provenance_rows[name]["bytes"] == fingerprint["bytes"]
                and source_provenance_rows[name]["sha256"] == fingerprint["sha256"]
                and fingerprint == fingerprint_path(fingerprint["path"])
                for name, fingerprint in source_fingerprints.items()
            )
            and "not settled ROI" in payload["source_provenance"]["read"]
            and "not real-money evidence" in payload["source_provenance"]["read"],
            "source_provenance_markdown_matches_json_and_disk",
            "markdown Source Provenance rows match compare_recommender_scope_paths.json source_fingerprints and current disk fingerprints for the generator, cross-family card, scorecard JSON, current-evidence JSON, EV engine, and recommender source files",
        )
    )

    validation_payload = {
        "suite_status": "pass",
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "artifact_status": "pass",
        "scratch": scratch_meta,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "summary": {
            "current_read": "the scope-comparison artifact still shows the selective Phase 7 filter as the honest current paper default, with allow-all-combos preserved as an explicit research-only counterfactual that can widen tickets, raise stake and off-scope share, flip NO BET into BET, and create modeled expected-profit lift from off-scope tickets on the same stub races; modeled expected-profit lift is pinned as stub EV rather than observed settlement P&L; machine-readable evidence_boundary.not_current_paper_scope_change_evidence=true keeps the widened path out of current paper-default, anchor-change, promotion, live-profitability, and real-money evidence; current paper hierarchy remains anchor=OP_DURABLE_K7, paper companion=CD_CORE_K8, closest shadow=OP_REFINED_K7; scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite are published so widened stub-ticket EV cannot bypass forward observation floors; current_evidence_summary.json scorecard_audit_route is republished so copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks route to SCORECARD_RANKING_CONTRACT_AUDIT.md / scorecard_ranking_contract_audit.json plus python3 validate_scorecard_ranking_contract_audit.py as synchronization metadata only; current_evidence_summary.json rebuild_validation_contract is republished so source-byte changes route through paper_trade_settlement_audit.py -> current_evidence_summary.py -> validate_current_evidence_summary.py before quoting current totals from this counterfactual surface, as provenance metadata only; missing scorecard gate failure is fixture-tested as a no-output-directory/no-artifact CLI path, including the whole decision_gate_minimums block and an individual anchor_displacement threshold, malformed boolean/non-positive scorecard gate floors plus a missing no-BAQ-as-BEL prerequisite are fixture-tested as the same no-output-directory/no-artifact CLI path, including non-positive Phase 8 and real-money scorecard floors, and missing or weakened current-evidence rebuild contracts are fixture-tested as no-output-directory/no-artifact CLI paths; saved JSON, saved markdown, dynamic cross-family hierarchy rerendering, real CLI stdout, project-local CLI scratch-root reporting, and markdown/JSON/disk source provenance stay pinned to the same scope-comparison render",
            "cli_fixture_scratch": {
                "tmp_parent": str(tmp_parent),
                "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
                "tmp_parent_cleared_before_fixture_run": True,
            },
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
        "# Recommender Scope Path Comparison Validation",
        "",
        "This validator rebuilds `compare_recommender_scope_paths.py` and pins the saved JSON/markdown artifacts plus the real CLI stdout report for the selective-vs-widened scope guardrail.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
        f"- Artifacts checked: `{OUT_MD.relative_to(BASE)}`, `{OUT_JSON.relative_to(BASE)}`",
        f"- Temporary fixture root: `{tmp_parent}` (cleared before CLI fixture run)",
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
            f"- {validation_payload['summary']['current_read']}",
            "",
            "## Sources",
            "",
            f"- `{OUT_MD.relative_to(BASE)}`",
            f"- `{OUT_JSON.relative_to(BASE)}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(validation_payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    print("PASS compare_recommender_scope_paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
