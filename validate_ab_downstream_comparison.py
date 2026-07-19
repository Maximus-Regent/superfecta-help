#!/usr/bin/env python3
"""
Validation for ab_downstream_comparison.py.

Purpose:
- keep the downstream XGBoost-vs-baseline comparison reproducible
- pin the saved JSON / markdown surfaces against a fresh markdown rebuild
- pin the real CLI stdout report plus save notices when raw rebuild inputs are available
- keep a report-safe saved-artifact validation path when raw rebuild inputs are not present
- pin the current honest read that prediction gains do not yet create a paper-betting case
"""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import ab_downstream_comparison as adc

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "ab_downstream_comparison.py"
OUT_JSON = BASE / "ab_downstream_comparison_results.json"
OUT_MD = BASE / "AB_DOWNSTREAM_COMPARISON.md"
REPORT_DIR = BASE / "out" / "status_validation" / "ab_downstream_comparison"
REPORT_MD = REPORT_DIR / "ab_downstream_comparison_validation.md"
REPORT_JSON = REPORT_DIR / "ab_downstream_comparison_validation.json"
TMP_PARENT = REPORT_DIR / "_tmp"
REBUILD_COMMAND = "python3 validate_ab_downstream_comparison.py"
VALID_EVIDENCE_SCOPE = adc.VALID_EVIDENCE_SCOPE


REQUIRED_INPUTS = [
    BASE / "14years_major_tracks.csv",
    BASE / "ab_baseline_model.json",
    BASE / "ab_enriched_model.json",
    BASE / "horse_features_major_tracks.csv",
    BASE / "cross_family_decision_card.csv",
    BASE / "current_evidence_summary.json",
]


def require(condition: bool, label: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    return {"check": label, "status": "pass", "detail": detail}


def check_item(label: str, status: str, detail: str) -> dict[str, Any]:
    return {"check": label, "status": status, "detail": detail}



def approx_equal(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol



def build_expected_cli_stdout(markdown: str, *, md_name: str = OUT_MD.name, json_name: str = OUT_JSON.name) -> str:
    return markdown + f"Saved: {md_name}\nSaved: {json_name}\n"


def build_hierarchy_source_line(source: dict[str, Any]) -> str:
    return (
        f"- Selective paper-lane hierarchy source: `{source['path']}` "
        f"(`sha256={source['sha256']}`, `{source['bytes']}` bytes)."
    )


def build_model_source_row(label: str, source: dict[str, Any]) -> str:
    return f"| `{label}` | `{source['path']}` | {source['bytes']} | `{source['sha256']}` |"


def replace_rule_ids(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: replace_rule_ids(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_rule_ids(item, replacements) for item in value]
    if isinstance(value, str):
        for old_value, new_value in replacements.items():
            value = value.replace(old_value, new_value)
        return value
    return value


def prepare_tmp_parent() -> Path:
    """Use project-local scratch space so fixture writes avoid system temp quotas."""
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
    if not OUT_JSON.exists() or not OUT_MD.exists():
        raise AssertionError("expected downstream comparison artifacts were not created")

    saved_json_text = OUT_JSON.read_text(encoding="utf-8")
    payload = json.loads(saved_json_text)
    saved_md = OUT_MD.read_text(encoding="utf-8")
    rebuilt_md = adc.build_markdown(payload)
    if saved_md != rebuilt_md:
        raise AssertionError("AB_DOWNSTREAM_COMPARISON.md drifted from a fresh build_markdown() rebuild")

    missing_required_inputs = [src for src in REQUIRED_INPUTS if not src.exists()]
    full_cli_rebuild_available = not missing_required_inputs
    cli_json_status = "skip"
    cli_markdown_status = "skip"
    cli_stdout_status = "skip"
    custom_cli_status = "skip"
    cli_json_detail = (
        "full ab_downstream_comparison.py CLI rebuild was not run because raw rebuild inputs are missing: "
        + ", ".join(src.name for src in missing_required_inputs)
    )
    cli_markdown_detail = cli_json_detail
    cli_stdout_detail = cli_json_detail
    custom_cli_detail = cli_json_detail
    refresh_only_cli_status = "skip"
    refresh_only_cli_detail = "refresh-only CLI fixture did not run"

    with tempfile.TemporaryDirectory(prefix="ab_downstream_comparison_", dir=tmp_parent) as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        (tmpdir / SCRIPT.name).write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        if full_cli_rebuild_available:
            for src in REQUIRED_INPUTS:
                (tmpdir / src.name).symlink_to(src)
            cli_result = subprocess.run(
                [sys.executable, SCRIPT.name],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                check=True,
                timeout=900,
            )
            cli_json_text = (tmpdir / OUT_JSON.name).read_text(encoding="utf-8")
            cli_md = (tmpdir / OUT_MD.name).read_text(encoding="utf-8")
            if cli_json_text != saved_json_text:
                raise AssertionError("CLI-generated ab_downstream_comparison_results.json drifted from the saved artifact")
            if cli_md != saved_md:
                raise AssertionError("CLI-generated AB_DOWNSTREAM_COMPARISON.md drifted from the saved artifact")
            expected_cli_stdout = build_expected_cli_stdout(cli_md)
            if cli_result.stdout != expected_cli_stdout:
                raise AssertionError("ab_downstream_comparison.py CLI stdout no longer matches the generated markdown plus Saved: lines")
            cli_json_status = "pass"
            cli_markdown_status = "pass"
            cli_stdout_status = "pass"
            cli_json_detail = "ab_downstream_comparison.py CLI still writes JSON that matches the saved downstream comparison artifact"
            cli_markdown_detail = "ab_downstream_comparison.py CLI still writes markdown that matches the saved downstream comparison artifact"
            cli_stdout_detail = "ab_downstream_comparison.py CLI stdout still matches the generated markdown plus its Saved: lines"

        custom_cross_family_csv = tmpdir / "custom_cross_family_decision.csv"
        cross_family_source = tmpdir / adc.CROSS_FAMILY_CSV.name
        if not cross_family_source.exists():
            cross_family_source.symlink_to(adc.CROSS_FAMILY_CSV)
        custom_cross_text = cross_family_source.read_text(encoding="utf-8")
        for old_value, new_value in {
            "OP_DURABLE_K7": "ALT_ANCHOR_K7",
            "CD_CORE_K8": "ALT_PAPER_COMPANION_K8",
            "OP_REFINED_K7": "ALT_CLOSEST_SHADOW_K7",
        }.items():
            custom_cross_text = custom_cross_text.replace(old_value, new_value)
        custom_cross_family_csv.write_text(custom_cross_text, encoding="utf-8")
        custom_shadow_read = adc.load_selective_shadow_read(custom_cross_family_csv)
        custom_payload = replace_rule_ids(
            copy.deepcopy(payload),
            {
                "OP_DURABLE_K7": "ALT_ANCHOR_K7",
                "CD_CORE_K8": "ALT_PAPER_COMPANION_K8",
                "OP_REFINED_K7": "ALT_CLOSEST_SHADOW_K7",
            },
        )
        custom_payload["selective_shadow_read"] = custom_shadow_read
        custom_md = adc.build_markdown(custom_payload)
        if custom_shadow_read["current_anchor"] != "ALT_ANCHOR_K7":
            raise AssertionError("custom cross-family anchor did not reach the downstream A/B hierarchy read")
        if custom_shadow_read["primary_companion"] != "ALT_PAPER_COMPANION_K8":
            raise AssertionError("custom cross-family paper companion did not reach the downstream A/B hierarchy read")
        if custom_shadow_read["secondary_shadow"] != "ALT_CLOSEST_SHADOW_K7":
            raise AssertionError("custom cross-family closest shadow did not reach the downstream A/B hierarchy read")
        if custom_shadow_read["cross_family_source"].get("path") != custom_cross_family_csv.name:
            raise AssertionError("custom cross-family source filename was not preserved in the downstream A/B hierarchy metadata")
        for expected in [
            "`ALT_ANCHOR_K7` remains the safest anchor",
            "`ALT_PAPER_COMPANION_K8` is the primary OP/CD paper-basket companion",
            "`ALT_CLOSEST_SHADOW_K7` stays a smaller same-family OP shadow challenger",
            f"Selective paper-lane hierarchy source: `{custom_cross_family_csv.name}`",
            "with `ALT_ANCHOR_K7` still the safest anchor, `ALT_PAPER_COMPANION_K8` as the primary OP/CD paper-basket companion, and `ALT_CLOSEST_SHADOW_K7` as the same-family OP shadow challenger.",
        ]:
            if expected not in custom_md:
                raise AssertionError(f"custom cross-family hierarchy did not render dynamic downstream A/B markdown text: {expected}")
        for stale in ["OP_DURABLE_K7", "CD_CORE_K8", "OP_REFINED_K7"]:
            if stale in custom_md:
                raise AssertionError(f"custom cross-family downstream A/B render still contains stale default rule id: {stale}")

        refresh_json_output = tmpdir / "refresh_ab_downstream_comparison_results.json"
        refresh_md_output = tmpdir / "refresh_AB_DOWNSTREAM_COMPARISON.md"
        refresh_json_output.write_text(saved_json_text, encoding="utf-8")
        for src in [adc.CURRENT_EVIDENCE_JSON, adc.CROSS_FAMILY_CSV, adc.BASELINE_MODEL, adc.ENRICHED_MODEL]:
            linked = tmpdir / src.name
            if not linked.exists():
                linked.symlink_to(src)
        refresh_cli_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--refresh-current-evidence-only",
                "--json-output",
                refresh_json_output.name,
                "--md-output",
                refresh_md_output.name,
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        refresh_payload = json.loads(refresh_json_output.read_text(encoding="utf-8"))
        refresh_md = refresh_md_output.read_text(encoding="utf-8")
        if refresh_payload.get("current_operator_boundary") != adc.load_current_operator_boundary(adc.CURRENT_EVIDENCE_JSON):
            raise AssertionError("refresh-only CLI did not republish the current current_evidence_summary.json boundary")
        if refresh_payload.get("selective_shadow_read") != adc.load_selective_shadow_read(adc.CROSS_FAMILY_CSV):
            raise AssertionError("refresh-only CLI did not republish the current cross-family hierarchy read")
        if refresh_payload.get("model_source_fingerprints") != adc.model_source_fingerprints():
            raise AssertionError("refresh-only CLI did not republish current model source fingerprints")
        if refresh_md != adc.build_markdown(refresh_payload):
            raise AssertionError("refresh-only CLI markdown no longer matches a fresh build_markdown() rebuild")
        if refresh_cli_result.stdout != build_expected_cli_stdout(
            refresh_md,
            md_name=refresh_md_output.name,
            json_name=refresh_json_output.name,
        ):
            raise AssertionError("refresh-only CLI stdout no longer matches the refreshed markdown plus Saved: lines")
        refresh_only_cli_status = "pass"
        refresh_only_cli_detail = (
            "ab_downstream_comparison.py --refresh-current-evidence-only can refresh the copied "
            "current-evidence bridge, hierarchy fingerprint, model fingerprints, markdown, JSON, "
            "and stdout from saved A/B metrics without raw race-level rebuild inputs"
        )

        if full_cli_rebuild_available:
            custom_md_output = tmpdir / "custom_ab_downstream_comparison.md"
            custom_json_output = tmpdir / "custom_ab_downstream_comparison.json"
            custom_cli_result = subprocess.run(
                [
                    sys.executable,
                    SCRIPT.name,
                    "--cross-family-csv",
                    custom_cross_family_csv.name,
                    "--md-output",
                    custom_md_output.name,
                    "--json-output",
                    custom_json_output.name,
                ],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                check=True,
                timeout=900,
            )
            custom_cli_payload = json.loads(custom_json_output.read_text(encoding="utf-8"))
            custom_cli_md = custom_md_output.read_text(encoding="utf-8")
            if custom_cli_payload["selective_shadow_read"] != custom_shadow_read:
                raise AssertionError("custom CLI cross-family hierarchy did not match load_selective_shadow_read()")
            if custom_cli_md != adc.build_markdown(custom_cli_payload):
                raise AssertionError("custom CLI markdown did not match a fresh build_markdown() rebuild")
            expected_custom_cli_stdout = build_expected_cli_stdout(
                custom_cli_md,
                md_name=custom_md_output.name,
                json_name=custom_json_output.name,
            )
            if custom_cli_result.stdout != expected_custom_cli_stdout:
                raise AssertionError("custom CLI stdout did not preserve the requested output filenames plus generated markdown")
            for expected in [
                "`ALT_ANCHOR_K7` remains the safest anchor",
                "`ALT_PAPER_COMPANION_K8` is the primary OP/CD paper-basket companion",
                "`ALT_CLOSEST_SHADOW_K7` stays a smaller same-family OP shadow challenger",
                f"Selective paper-lane hierarchy source: `{custom_cross_family_csv.name}`",
            ]:
                if expected not in custom_cli_md:
                    raise AssertionError(f"custom CLI cross-family hierarchy did not render dynamic downstream A/B markdown text: {expected}")
            for stale in ["OP_DURABLE_K7", "CD_CORE_K8", "OP_REFINED_K7"]:
                if stale in custom_cli_md:
                    raise AssertionError(f"custom CLI downstream A/B render still contains stale default rule id: {stale}")
            custom_cli_status = "pass"
            custom_cli_detail = "downstream A/B CLI accepts a custom cross-family CSV plus custom markdown/JSON output paths and keeps stdout, JSON, and markdown aligned to that custom hierarchy"

        bad_current_evidence_json = tmpdir / "bad_generated_at_current_evidence_summary.json"
        bad_current_evidence_output_dir = tmpdir / "bad_current_evidence_outputs"
        bad_current_evidence_md = bad_current_evidence_output_dir / "bad_current_evidence_should_not_write.md"
        bad_current_evidence_json_output = bad_current_evidence_output_dir / "bad_current_evidence_should_not_write.json"
        bad_current_evidence_payload = json.loads(adc.CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8"))
        bad_current_evidence_payload["generated_at"] = "2026-06-26 18:12:48"
        bad_current_evidence_json.write_text(
            json.dumps(bad_current_evidence_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        bad_current_evidence_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(bad_current_evidence_json),
                "--md-output",
                str(bad_current_evidence_md),
                "--json-output",
                str(bad_current_evidence_json_output),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if bad_current_evidence_result.returncode == 0:
            raise AssertionError("ab_downstream_comparison.py unexpectedly accepted current-evidence JSON with a timezone-naive generated_at")
        bad_current_evidence_text = f"{bad_current_evidence_result.stdout}\n{bad_current_evidence_result.stderr}"
        if "generated_at must be timezone-aware ISO provenance metadata" not in bad_current_evidence_text:
            raise AssertionError("current-evidence generated_at failure no longer explains that timestamp provenance must be timezone-aware")
        if bad_current_evidence_output_dir.exists() or bad_current_evidence_md.exists() or bad_current_evidence_json_output.exists():
            raise AssertionError("bad current-evidence CLI path created downstream comparison output paths before failing provenance validation")

        missing_operator_read_gate_json = tmpdir / "missing_operator_read_gate_current_evidence_summary.json"
        missing_operator_read_gate_output_dir = tmpdir / "missing_operator_read_gate_outputs" / "artifacts"
        missing_operator_read_gate_md = (
            missing_operator_read_gate_output_dir / "missing_operator_read_gate_should_not_write.md"
        )
        missing_operator_read_gate_json_output = (
            missing_operator_read_gate_output_dir / "missing_operator_read_gate_should_not_write.json"
        )
        missing_operator_read_gate_payload = json.loads(adc.CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8"))
        del missing_operator_read_gate_payload["operator_read_gate"]
        missing_operator_read_gate_json.write_text(
            json.dumps(missing_operator_read_gate_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_operator_read_gate_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(missing_operator_read_gate_json),
                "--md-output",
                str(missing_operator_read_gate_md),
                "--json-output",
                str(missing_operator_read_gate_json_output),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_operator_read_gate_result.returncode == 0:
            raise AssertionError("ab_downstream_comparison.py unexpectedly accepted current-evidence JSON missing operator_read_gate")
        missing_operator_read_gate_text = (
            f"{missing_operator_read_gate_result.stdout}\n{missing_operator_read_gate_result.stderr}"
        )
        if "is missing operator_read_gate" not in missing_operator_read_gate_text:
            raise AssertionError("current-evidence operator_read_gate failure no longer names the missing bridge block")
        if (
            missing_operator_read_gate_output_dir.exists()
            or missing_operator_read_gate_md.exists()
            or missing_operator_read_gate_json_output.exists()
        ):
            raise AssertionError("missing operator_read_gate CLI path created downstream comparison output paths before failing bridge validation")

        missing_rebuild_validation_contract_json = (
            tmpdir / "missing_rebuild_validation_contract_current_evidence_summary.json"
        )
        missing_rebuild_validation_contract_output_dir = (
            tmpdir / "missing_rebuild_validation_contract_outputs" / "artifacts"
        )
        missing_rebuild_validation_contract_md = (
            missing_rebuild_validation_contract_output_dir
            / "missing_rebuild_validation_contract_should_not_write.md"
        )
        missing_rebuild_validation_contract_json_output = (
            missing_rebuild_validation_contract_output_dir
            / "missing_rebuild_validation_contract_should_not_write.json"
        )
        missing_rebuild_validation_contract_payload = json.loads(
            adc.CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8")
        )
        missing_rebuild_validation_contract_payload.pop("rebuild_validation_contract", None)
        missing_rebuild_validation_contract_json.write_text(
            json.dumps(missing_rebuild_validation_contract_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_rebuild_validation_contract_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(missing_rebuild_validation_contract_json),
                "--md-output",
                str(missing_rebuild_validation_contract_md),
                "--json-output",
                str(missing_rebuild_validation_contract_json_output),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_rebuild_validation_contract_result.returncode == 0:
            raise AssertionError(
                "ab_downstream_comparison.py unexpectedly accepted current-evidence JSON missing rebuild_validation_contract"
            )
        missing_rebuild_validation_contract_text = (
            f"{missing_rebuild_validation_contract_result.stdout}\n"
            f"{missing_rebuild_validation_contract_result.stderr}"
        )
        if "is missing rebuild_validation_contract" not in missing_rebuild_validation_contract_text:
            raise AssertionError(
                "current-evidence rebuild_validation_contract failure no longer names the missing bridge route"
            )
        if (
            missing_rebuild_validation_contract_output_dir.exists()
            or missing_rebuild_validation_contract_md.exists()
            or missing_rebuild_validation_contract_json_output.exists()
        ):
            raise AssertionError(
                "missing rebuild_validation_contract CLI path created downstream comparison output paths before failing bridge validation"
            )

        weakened_rebuild_validation_contract_json = (
            tmpdir / "weakened_rebuild_validation_contract_current_evidence_summary.json"
        )
        weakened_rebuild_validation_contract_output_dir = (
            tmpdir / "weakened_rebuild_validation_contract_outputs" / "artifacts"
        )
        weakened_rebuild_validation_contract_md = (
            weakened_rebuild_validation_contract_output_dir
            / "weakened_rebuild_validation_contract_should_not_write.md"
        )
        weakened_rebuild_validation_contract_json_output = (
            weakened_rebuild_validation_contract_output_dir
            / "weakened_rebuild_validation_contract_should_not_write.json"
        )
        weakened_rebuild_validation_contract_payload = json.loads(
            adc.CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8")
        )
        weakened_rebuild_validation_contract_payload["rebuild_validation_contract"][
            "upstream_refresh_order_is_provenance_metadata_only"
        ] = False
        weakened_rebuild_validation_contract_json.write_text(
            json.dumps(weakened_rebuild_validation_contract_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        weakened_rebuild_validation_contract_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(weakened_rebuild_validation_contract_json),
                "--md-output",
                str(weakened_rebuild_validation_contract_md),
                "--json-output",
                str(weakened_rebuild_validation_contract_json_output),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if weakened_rebuild_validation_contract_result.returncode == 0:
            raise AssertionError(
                "ab_downstream_comparison.py unexpectedly accepted current-evidence JSON with weakened rebuild_validation_contract"
            )
        weakened_rebuild_validation_contract_text = (
            f"{weakened_rebuild_validation_contract_result.stdout}\n"
            f"{weakened_rebuild_validation_contract_result.stderr}"
        )
        if (
            "rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true"
            not in weakened_rebuild_validation_contract_text
        ):
            raise AssertionError(
                "weakened current-evidence rebuild_validation_contract failure no longer names the provenance-only flag"
            )
        if (
            weakened_rebuild_validation_contract_output_dir.exists()
            or weakened_rebuild_validation_contract_md.exists()
            or weakened_rebuild_validation_contract_json_output.exists()
        ):
            raise AssertionError(
                "weakened rebuild_validation_contract CLI path created downstream comparison output paths before failing bridge validation"
            )

        missing_source_freshness_json = tmpdir / "missing_source_freshness_current_evidence_summary.json"
        missing_source_freshness_output_dir = tmpdir / "missing_source_freshness_outputs" / "artifacts"
        missing_source_freshness_md = missing_source_freshness_output_dir / "missing_source_freshness_should_not_write.md"
        missing_source_freshness_json_output = missing_source_freshness_output_dir / "missing_source_freshness_should_not_write.json"
        missing_source_freshness_reference_json = tmpdir / "missing_source_freshness_reference_current_evidence_summary.json"
        missing_source_freshness_reference_output_dir = (
            tmpdir / "missing_source_freshness_reference_outputs" / "artifacts"
        )
        missing_source_freshness_reference_md = (
            missing_source_freshness_reference_output_dir
            / "missing_source_freshness_reference_should_not_write.md"
        )
        missing_source_freshness_reference_json_output = (
            missing_source_freshness_reference_output_dir
            / "missing_source_freshness_reference_should_not_write.json"
        )
        missing_refresh_action_boundary_json = tmpdir / "missing_refresh_action_boundary_current_evidence_summary.json"
        missing_refresh_action_boundary_output_dir = (
            tmpdir / "missing_refresh_action_boundary_outputs" / "artifacts"
        )
        missing_refresh_action_boundary_md = (
            missing_refresh_action_boundary_output_dir
            / "missing_refresh_action_boundary_should_not_write.md"
        )
        missing_refresh_action_boundary_json_output = (
            missing_refresh_action_boundary_output_dir
            / "missing_refresh_action_boundary_should_not_write.json"
        )
        missing_refresh_action_boundary_field_json = (
            tmpdir / "missing_refresh_action_boundary_field_current_evidence_summary.json"
        )
        missing_refresh_action_boundary_field_output_dir = (
            tmpdir / "missing_refresh_action_boundary_field_outputs" / "artifacts"
        )
        missing_refresh_action_boundary_field_md = (
            missing_refresh_action_boundary_field_output_dir
            / "missing_refresh_action_boundary_field_should_not_write.md"
        )
        missing_refresh_action_boundary_field_json_output = (
            missing_refresh_action_boundary_field_output_dir
            / "missing_refresh_action_boundary_field_should_not_write.json"
        )
        false_refresh_action_boundary_flag_json = (
            tmpdir / "false_refresh_action_boundary_flag_current_evidence_summary.json"
        )
        false_refresh_action_boundary_flag_output_dir = (
            tmpdir / "false_refresh_action_boundary_flag_outputs" / "artifacts"
        )
        false_refresh_action_boundary_flag_md = (
            false_refresh_action_boundary_flag_output_dir
            / "false_refresh_action_boundary_flag_should_not_write.md"
        )
        false_refresh_action_boundary_flag_json_output = (
            false_refresh_action_boundary_flag_output_dir
            / "false_refresh_action_boundary_flag_should_not_write.json"
        )
        false_refresh_accounting_flag_json = (
            tmpdir / "false_refresh_accounting_flag_current_evidence_summary.json"
        )
        false_refresh_accounting_flag_output_dir = (
            tmpdir / "false_refresh_accounting_flag_outputs" / "artifacts"
        )
        false_refresh_accounting_flag_md = (
            false_refresh_accounting_flag_output_dir / "false_refresh_accounting_flag_should_not_write.md"
        )
        false_refresh_accounting_flag_json_output = (
            false_refresh_accounting_flag_output_dir / "false_refresh_accounting_flag_should_not_write.json"
        )
        missing_source_freshness_payload = json.loads(adc.CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8"))
        missing_source_freshness_payload.pop("source_freshness", None)
        missing_source_freshness_json.write_text(
            json.dumps(missing_source_freshness_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_source_freshness_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(missing_source_freshness_json),
                "--md-output",
                str(missing_source_freshness_md),
                "--json-output",
                str(missing_source_freshness_json_output),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_source_freshness_result.returncode == 0:
            raise AssertionError("ab_downstream_comparison.py unexpectedly accepted current-evidence JSON missing source_freshness")
        missing_source_freshness_text = f"{missing_source_freshness_result.stdout}\n{missing_source_freshness_result.stderr}"
        if "missing source_freshness" not in missing_source_freshness_text:
            raise AssertionError("missing current-evidence source_freshness failure no longer names the required bridge block")
        if (
            missing_source_freshness_output_dir.exists()
            or missing_source_freshness_md.exists()
            or missing_source_freshness_json_output.exists()
        ):
            raise AssertionError("missing source_freshness CLI path created downstream comparison output paths before failing bridge validation")

        missing_source_freshness_reference_payload = json.loads(
            adc.CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8")
        )
        del missing_source_freshness_reference_payload["source_freshness"]["generated_reference_timezone"]
        missing_source_freshness_reference_json.write_text(
            json.dumps(missing_source_freshness_reference_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_source_freshness_reference_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(missing_source_freshness_reference_json),
                "--md-output",
                str(missing_source_freshness_reference_md),
                "--json-output",
                str(missing_source_freshness_reference_json_output),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_source_freshness_reference_result.returncode == 0:
            raise AssertionError("ab_downstream_comparison.py unexpectedly accepted current-evidence JSON missing source_freshness generated_reference_timezone")
        missing_source_freshness_reference_text = (
            f"{missing_source_freshness_reference_result.stdout}\n"
            f"{missing_source_freshness_reference_result.stderr}"
        )
        if "source_freshness missing fields: generated_reference_timezone" not in missing_source_freshness_reference_text:
            raise AssertionError("missing current-evidence source_freshness reference failure no longer names the required reference field")
        if (
            missing_source_freshness_reference_output_dir.exists()
            or missing_source_freshness_reference_md.exists()
            or missing_source_freshness_reference_json_output.exists()
        ):
            raise AssertionError("missing source_freshness reference CLI path created downstream comparison output paths before failing bridge validation")

        missing_refresh_action_boundary_payload = json.loads(
            adc.CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8")
        )
        del missing_refresh_action_boundary_payload["source_freshness"]["refresh_action_boundary"]
        missing_refresh_action_boundary_json.write_text(
            json.dumps(missing_refresh_action_boundary_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        missing_refresh_action_boundary_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(missing_refresh_action_boundary_json),
                "--md-output",
                str(missing_refresh_action_boundary_md),
                "--json-output",
                str(missing_refresh_action_boundary_json_output),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_refresh_action_boundary_result.returncode == 0:
            raise AssertionError("ab_downstream_comparison.py unexpectedly accepted current-evidence JSON missing source_freshness.refresh_action_boundary")
        missing_refresh_action_boundary_text = (
            f"{missing_refresh_action_boundary_result.stdout}\n"
            f"{missing_refresh_action_boundary_result.stderr}"
        )
        if "missing source_freshness.refresh_action_boundary" not in missing_refresh_action_boundary_text:
            raise AssertionError("missing current-evidence refresh-action boundary failure no longer names the required bridge sub-block")
        if (
            missing_refresh_action_boundary_output_dir.exists()
            or missing_refresh_action_boundary_md.exists()
            or missing_refresh_action_boundary_json_output.exists()
        ):
            raise AssertionError("missing refresh_action_boundary CLI path created downstream comparison output paths before failing bridge validation")

        missing_refresh_action_boundary_field_payload = json.loads(
            adc.CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8")
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
                SCRIPT.name,
                "--current-evidence-json",
                str(missing_refresh_action_boundary_field_json),
                "--md-output",
                str(missing_refresh_action_boundary_field_md),
                "--json-output",
                str(missing_refresh_action_boundary_field_json_output),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if missing_refresh_action_boundary_field_result.returncode == 0:
            raise AssertionError("ab_downstream_comparison.py unexpectedly accepted current-evidence JSON missing source_freshness.refresh_action_boundary.not_real_money_evidence")
        missing_refresh_action_boundary_field_text = (
            f"{missing_refresh_action_boundary_field_result.stdout}\n"
            f"{missing_refresh_action_boundary_field_result.stderr}"
        )
        if (
            "source_freshness.refresh_action_boundary missing fields: not_real_money_evidence"
            not in missing_refresh_action_boundary_field_text
        ):
            raise AssertionError("missing current-evidence refresh-action field failure no longer names the missing not-real-money flag")
        if (
            missing_refresh_action_boundary_field_output_dir.exists()
            or missing_refresh_action_boundary_field_md.exists()
            or missing_refresh_action_boundary_field_json_output.exists()
        ):
            raise AssertionError("missing refresh_action_boundary field CLI path created downstream comparison output paths before failing bridge validation")

        false_refresh_action_boundary_flag_payload = json.loads(
            adc.CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8")
        )
        false_refresh_action_boundary_flag_payload["source_freshness"]["refresh_action_boundary"][
            "not_real_money_evidence"
        ] = False
        false_refresh_action_boundary_flag_json.write_text(
            json.dumps(false_refresh_action_boundary_flag_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        false_refresh_action_boundary_flag_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(false_refresh_action_boundary_flag_json),
                "--md-output",
                str(false_refresh_action_boundary_flag_md),
                "--json-output",
                str(false_refresh_action_boundary_flag_json_output),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if false_refresh_action_boundary_flag_result.returncode == 0:
            raise AssertionError("ab_downstream_comparison.py unexpectedly accepted current-evidence JSON with source_freshness.refresh_action_boundary.not_real_money_evidence=false")
        false_refresh_action_boundary_flag_text = (
            f"{false_refresh_action_boundary_flag_result.stdout}\n"
            f"{false_refresh_action_boundary_flag_result.stderr}"
        )
        if (
            "source_freshness.refresh_action_boundary must mark not_real_money_evidence=true"
            not in false_refresh_action_boundary_flag_text
        ):
            raise AssertionError("false current-evidence refresh-action flag failure no longer names the weakened not-real-money flag")
        if (
            false_refresh_action_boundary_flag_output_dir.exists()
            or false_refresh_action_boundary_flag_md.exists()
            or false_refresh_action_boundary_flag_json_output.exists()
        ):
            raise AssertionError("false refresh_action_boundary flag CLI path created downstream comparison output paths before failing bridge validation")

        false_refresh_accounting_flag_payload = json.loads(
            adc.CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8")
        )
        false_refresh_accounting_flag_payload["source_freshness"]["refresh_action_boundary"][
            "clean_empty_refresh_counts_as_forward_performance"
        ] = True
        false_refresh_accounting_flag_json.write_text(
            json.dumps(false_refresh_accounting_flag_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        false_refresh_accounting_flag_result = subprocess.run(
            [
                sys.executable,
                SCRIPT.name,
                "--current-evidence-json",
                str(false_refresh_accounting_flag_json),
                "--md-output",
                str(false_refresh_accounting_flag_md),
                "--json-output",
                str(false_refresh_accounting_flag_json_output),
            ],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if false_refresh_accounting_flag_result.returncode == 0:
            raise AssertionError("ab_downstream_comparison.py unexpectedly accepted current-evidence JSON with source_freshness.refresh_action_boundary.clean_empty_refresh_counts_as_forward_performance=true")
        false_refresh_accounting_flag_text = (
            f"{false_refresh_accounting_flag_result.stdout}\n"
            f"{false_refresh_accounting_flag_result.stderr}"
        )
        if (
            "source_freshness.refresh_action_boundary must mark clean_empty_refresh_counts_as_forward_performance=false"
            not in false_refresh_accounting_flag_text
        ):
            raise AssertionError("false current-evidence refresh-accounting failure no longer names the weakened clean-empty refresh flag")
        if (
            false_refresh_accounting_flag_output_dir.exists()
            or false_refresh_accounting_flag_md.exists()
            or false_refresh_accounting_flag_json_output.exists()
        ):
            raise AssertionError("false refresh-accounting flag CLI path created downstream comparison output paths before failing bridge validation")

    test_set = payload["test_set"]
    shadow_read = payload["selective_shadow_read"]
    hierarchy_source = shadow_read.get("cross_family_source", {})
    current_hierarchy_source = adc.file_fingerprint(adc.CROSS_FAMILY_CSV)
    model_sources = payload.get("model_source_fingerprints", {})
    current_model_sources = adc.model_source_fingerprints()
    pred = payload["prediction_accuracy"]
    base = pred["baseline"]
    enriched = pred["enriched"]
    delta = pred["delta"]
    ev = payload["ev_engine_comparison"]
    ev_base = ev["baseline"]
    ev_enriched = ev["enriched"]
    disagreement = payload["disagreement_analysis"]
    ev_delta = ev["delta"]
    current_operator_boundary = payload.get("current_operator_boundary", {})
    expected_current_operator_boundary = adc.load_current_operator_boundary(adc.CURRENT_EVIDENCE_JSON)
    current_gate_progress = current_operator_boundary.get("decision_gate_progress", {})
    evidence_boundary = payload.get("evidence_boundary", {})
    source_current_evidence_payload = json.loads(adc.CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8"))
    source_operator_read_gate = source_current_evidence_payload["operator_read_gate"]
    source_operator_status_context = source_current_evidence_payload["current_paper_status"][
        "operator_status_context"
    ]
    source_open_queue = source_current_evidence_payload["current_paper_status"]["primary"][
        "open_settlement_queue_by_rule"
    ]
    source_scorecard_audit_route = source_current_evidence_payload["scorecard_audit_route"]
    source_rebuild_validation_contract = source_current_evidence_payload["rebuild_validation_contract"]
    rebuild_validation_contract = current_operator_boundary.get("rebuild_validation_contract", {})
    rebuild_order_commands = [
        row.get("command")
        for row in rebuild_validation_contract.get("upstream_refresh_order", [])
        if isinstance(row, dict)
    ]
    operator_read_gate = current_operator_boundary.get("operator_read_gate", {})
    operator_read_gate_read = str(operator_read_gate.get("read") or "")
    operator_gate_requires_refresh = bool(operator_read_gate.get("requires_refresh_before_evidence_read"))
    operator_gate_common_non_evidence_ok = (
        operator_read_gate.get("current_top_card_counts_as_no_target_evidence") is False
        and operator_read_gate.get("current_top_card_counts_as_clean_empty_evidence") is False
        and operator_read_gate.get("current_top_card_counts_as_bet_readiness_evidence") is False
        and operator_read_gate.get("current_top_card_counts_as_settled_roi_evidence") is False
        and operator_read_gate.get("not_forward_performance_evidence") is True
        and operator_read_gate.get("not_promotion_readiness_evidence") is True
        and operator_read_gate.get("not_live_profitability_evidence") is True
        and operator_read_gate.get("not_real_money_evidence") is True
    )
    operator_gate_branch_ok = (
        operator_read_gate.get("gate_status") == "refresh_required_before_evidence_read"
        and operator_gate_requires_refresh
        and operator_read_gate.get("recommended_command") == "./run_daily_portfolio_observation.sh"
        and operator_read_gate.get("has_wrapper_refresh_action") is True
        and any(
            operator_read_gate.get(flag) is True
            for flag in (
                "requires_source_freshness_refresh",
                "has_api_access_failure_context",
                "has_scanner_failure_boundary",
                "has_stale_cache_fallback_context",
                "has_missing_scan_output_artifact_issue",
                "has_issue_bucket",
            )
        )
        and "Refresh/recheck with `./run_daily_portfolio_observation.sh`" in operator_read_gate_read
    ) or (
        operator_read_gate.get("gate_status") == "current_operator_routing_context_only"
        and not operator_gate_requires_refresh
        and operator_read_gate.get("requires_source_freshness_refresh") is False
        and operator_read_gate.get("has_api_access_failure_context") is False
        and operator_read_gate.get("has_scanner_failure_boundary") is False
        and operator_read_gate.get("has_stale_cache_fallback_context") is False
        and operator_read_gate.get("has_missing_scan_output_artifact_issue") is False
        and operator_read_gate.get("has_wrapper_refresh_action") is False
        and operator_read_gate.get("has_issue_bucket") is False
        and "current operator routing context" in operator_read_gate_read
    )
    expected_combined_route_fragment = (
        "combined route: use operator_status_context plus "
        f"source_freshness.requires_refresh_before_right_now_use="
        f"{current_operator_boundary.get('requires_refresh_before_right_now_use')} plus "
        f"operator_read_gate.requires_refresh_before_evidence_read="
        f"{operator_read_gate.get('requires_refresh_before_evidence_read')}"
    )
    combined_route_boundary = adc.combined_operator_route_boundary_text(current_operator_boundary)
    operator_gate_boundary = adc.operator_read_gate_boundary_text(operator_read_gate)

    checks: list[dict[str, Any]] = []
    checks.append(
        require(
            saved_md == rebuilt_md,
            "markdown_matches_rebuild",
            "AB_DOWNSTREAM_COMPARISON.md still matches a fresh build_markdown() rebuild",
        )
    )
    checks.append(
        check_item(
            "cli_json_matches_saved",
            cli_json_status,
            cli_json_detail,
        )
    )
    checks.append(
        check_item(
            "cli_markdown_matches_saved",
            cli_markdown_status,
            cli_markdown_detail,
        )
    )
    checks.append(
        check_item(
            "cli_stdout_matches_generated_report",
            cli_stdout_status,
            cli_stdout_detail,
        )
    )
    checks.append(
        check_item(
            "refresh_current_evidence_only_cli_updates_snapshot",
            refresh_only_cli_status,
            refresh_only_cli_detail,
        )
    )
    checks.append(
        require(
            test_set["n_races"] == 22244 and test_set["split_date"] == "2020-12-19",
            "test_set_shape",
            "chronological downstream comparison still rebuilds on the 22,244-race test set starting 2020-12-19",
        )
    )
    checks.append(
        require(
            enriched["log_ratio_rmse"] < base["log_ratio_rmse"]
            and enriched["payout_rmse"] < base["payout_rmse"]
            and delta["log_ratio_rmse"] < 0
            and delta["payout_rmse"] < 0,
            "prediction_metrics_improve",
            "enriched horse-history XGBoost path still improves matched prediction error metrics versus the baseline path",
        )
    )
    checks.append(
        require(
            ev_base["ev_pass_count"] == 178
            and ev_enriched["ev_pass_count"] == 171
            and ev_enriched["ev_pass_count"] <= ev_base["ev_pass_count"]
            and ev_delta["ev_pass_count_delta"] == -7
            and approx_equal(ev_delta["ev_pass_count_relative_change_pct"], -3.93, 0.01)
            and approx_equal(ev_delta["ev_pass_pct_point_delta"], -0.0315, 0.0001),
            "ev_pass_counts_stay_small_and_not_better",
            "conservative EV winner pass counts still stay tiny and do not improve under the enriched path, now with the -7 pass / -3.93% / -0.0315pp drift pinned explicitly",
        )
    )
    checks.append(
        require(
            approx_equal(base["payout_rmse"], 6191.69, 0.01)
            and approx_equal(enriched["payout_rmse"], 5929.40, 0.01)
            and approx_equal(delta["payout_rmse"], -262.29, 0.01),
            "payout_rmse_read_is_stable",
            "payout RMSE headline still matches the current frozen A/B evidence read",
        )
    )
    checks.append(
        require(
            disagreement["only_baseline_pass"]["count"] == 70
            and disagreement["only_enriched_pass"]["count"] == 63
            and disagreement["both_pass"]["count"] == 108,
            "disagreement_buckets_stable",
            "the disagreement split between baseline-only, enriched-only, and shared passes remains pinned",
        )
    )
    checks.append(
        require(
            "This is a research comparison, not a paper-promotion case." in saved_md
            and "not deployable ROI claims" in saved_md
            and "Keep the enriched horse-history XGBoost path in `RESEARCH ONLY`" in saved_md
            and "Non-goal: do not quote current `PAPER_TRADE_NOW` instructions from this A/B artifact without the combined `CURRENT_EVIDENCE_SUMMARY` `operator_status_context` / `source_freshness` / `operator_read_gate` route." in saved_md
            and "Pass-through delta vs baseline: `-7` winner passes, `-3.93%` relative, `-0.0315` percentage points" in saved_md
            and "tiny, winner-only slice rather than a full paper-candidate ranking test" in saved_md
            and "Selective paper-lane hierarchy source: `cross_family_decision_card.csv`" in saved_md
            and "sha256=" in saved_md,
            "markdown_guardrail",
            "markdown summary still preserves the paper-safety guardrail, the winner-only ROI caveat, the normalized pass-through drift read, and the cross-family hierarchy source line",
        )
    )
    checks.append(
        require(
            isinstance(evidence_boundary, dict)
            and payload.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and evidence_boundary.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}" in saved_md
            and evidence_boundary.get("current_operator_routing_requires_combined_route") is True
            and evidence_boundary.get("current_operator_routing_is_source_readiness_not_performance") is True
            and "operator_status_context" in evidence_boundary.get("current_operator_routing_fields", [])
            and "source_freshness" in evidence_boundary.get("current_operator_routing_fields", [])
            and "operator_read_gate" in evidence_boundary.get("current_operator_routing_fields", [])
            and "decision_gate_progress" in evidence_boundary.get("current_operator_routing_fields", [])
            and "scorecard_audit_route" in evidence_boundary.get("current_operator_routing_fields", [])
            and "rebuild_validation_contract" in evidence_boundary.get("current_operator_routing_fields", [])
            and "do not quote current PAPER_TRADE_NOW instructions from this artifact; use the combined operator_status_context/source_freshness/operator_read_gate route from CURRENT_EVIDENCE_SUMMARY instead"
            in evidence_boundary.get("non_goals", [])
            and "do not treat the copied scorecard audit route as downstream A/B evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence"
            in evidence_boundary.get("non_goals", [])
            and "do not treat the copied rebuild-validation contract as downstream A/B evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence"
            in evidence_boundary.get("non_goals", [])
            and evidence_boundary.get("not_settled_roi_evidence") is True
            and evidence_boundary.get("not_promotion_readiness_evidence") is True
            and evidence_boundary.get("not_live_profitability_evidence") is True
            and evidence_boundary.get("not_real_money_evidence") is True
            and evidence_boundary.get("not_current_day_scanner_result") is True
            and evidence_boundary.get("not_new_forward_evidence") is True,
            "evidence_boundary_combined_operator_route_pinned",
            "saved downstream A/B JSON/markdown now publishes the raw valid_evidence_scope plus the combined operator_status_context/source_freshness/operator_read_gate route requirement as source-readiness metadata only",
        )
    )
    checks.append(
        require(
            current_operator_boundary == expected_current_operator_boundary
            and current_operator_boundary.get("source_path") == adc.CURRENT_EVIDENCE_JSON.name
            and current_operator_boundary.get("source_fingerprint") == adc.file_fingerprint(adc.CURRENT_EVIDENCE_JSON)
            and current_operator_boundary.get("combined_operator_route_read")
            == expected_current_operator_boundary.get("combined_operator_route_read")
            and expected_combined_route_fragment in str(current_operator_boundary.get("combined_operator_route_read") or "")
            and "downstream A/B artifact" in str(current_operator_boundary.get("combined_operator_route_read") or "")
            and current_operator_boundary.get("operator_status_context_read")
            == expected_current_operator_boundary.get("operator_status_context_read")
            == source_operator_status_context.get("read")
            and current_operator_boundary.get("operator_status_context_valid_use")
            == source_operator_status_context.get("valid_use")
            and current_operator_boundary.get("operator_status_context_best_action_command")
            == source_operator_status_context.get("best_action_command")
            and isinstance(current_operator_boundary.get("operator_status_context_best_action_command"), str)
            and bool(current_operator_boundary.get("operator_status_context_best_action_command"))
            and current_operator_boundary.get("operator_status_context_ops_day_bucket")
            == source_operator_status_context.get("ops_day_bucket")
            and isinstance(current_operator_boundary.get("operator_status_context_ops_day_bucket"), str)
            and bool(current_operator_boundary.get("operator_status_context_ops_day_bucket"))
            and current_operator_boundary.get("operator_status_context_not_forward_performance_evidence") is True
            and current_operator_boundary.get("operator_read_gate")
            == expected_current_operator_boundary.get("operator_read_gate")
            == source_operator_read_gate
            and operator_read_gate.get("valid_use") == "operator instruction/evidence-read gating only"
            and isinstance(operator_read_gate.get("recommended_command"), str)
            and bool(operator_read_gate.get("recommended_command"))
            and operator_gate_common_non_evidence_ok
            and operator_gate_branch_ok
            and current_operator_boundary.get("right_now_freshness_state")
            == expected_current_operator_boundary.get("right_now_freshness_state")
            and current_operator_boundary.get("requires_refresh_before_right_now_use")
            == expected_current_operator_boundary.get("requires_refresh_before_right_now_use")
            and current_operator_boundary.get("refresh_action_command") == "./run_daily_portfolio_observation.sh"
            and current_operator_boundary.get("refresh_can_update_operator_surfaces") is True
            and current_operator_boundary.get("refresh_can_settle_open_rows_by_itself") is False
            and current_operator_boundary.get("refresh_counts_as_roi_complete_evidence_by_itself") is False
            and current_operator_boundary.get("clean_empty_refresh_counts_as_forward_performance") is False
            and current_operator_boundary.get("refresh_boundary_not_forward_performance_evidence") is True
            and current_operator_boundary.get("refresh_boundary_not_promotion_readiness_evidence") is True
            and current_operator_boundary.get("refresh_boundary_not_live_profitability_evidence") is True
            and current_operator_boundary.get("refresh_boundary_not_real_money_evidence") is True
            and current_operator_boundary.get("roi_complete_primary_rows")
            == expected_current_operator_boundary.get("roi_complete_primary_rows")
            and current_operator_boundary.get("first_read_threshold")
            == expected_current_operator_boundary.get("first_read_threshold")
            and current_operator_boundary.get("first_read_remaining")
            == expected_current_operator_boundary.get("first_read_remaining")
            and current_operator_boundary.get("op_anchor_roi_complete_rows")
            == expected_current_operator_boundary.get("op_anchor_roi_complete_rows")
            and current_operator_boundary.get("cd_companion_roi_complete_rows")
            == expected_current_operator_boundary.get("cd_companion_roi_complete_rows")
            and current_operator_boundary.get("current_settled_context_is_cd_only")
            == expected_current_operator_boundary.get("current_settled_context_is_cd_only")
            and current_operator_boundary.get("companion_rows_count_as_anchor_evidence")
            == expected_current_operator_boundary.get("companion_rows_count_as_anchor_evidence")
            and current_operator_boundary.get("open_settlement_rows")
            == expected_current_operator_boundary.get("open_settlement_rows")
            and current_operator_boundary.get("open_settlement_queue_state")
            == ("closed" if current_operator_boundary.get("open_settlement_rows") == 0 else "open")
            and current_operator_boundary.get("open_settlement_queue_state")
            == expected_current_operator_boundary.get("open_settlement_queue_state")
            and current_operator_boundary.get("open_settlement_queue_state")
            == source_open_queue.get("open_settlement_queue_state")
            and current_operator_boundary.get("open_settlement_context")
            == expected_current_operator_boundary.get("open_settlement_context")
            and current_operator_boundary.get("open_settlement_context")
            == source_open_queue.get("open_settlement_context")
            and (
                current_operator_boundary.get("open_settlement_rows") != 0
                or current_operator_boundary.get("open_settlement_context") == "no open primary settlement rows"
            )
            and current_operator_boundary.get("anchor_open_rows")
            == expected_current_operator_boundary.get("anchor_open_rows")
            and current_operator_boundary.get("companion_open_rows")
            == expected_current_operator_boundary.get("companion_open_rows")
            and current_operator_boundary.get("current_open_queue_is_cd_only")
            == expected_current_operator_boundary.get("current_open_queue_is_cd_only")
            and current_operator_boundary.get("open_rows_count_as_roi_complete")
            == expected_current_operator_boundary.get("open_rows_count_as_roi_complete")
            and current_operator_boundary.get("open_rows_count_as_anchor_evidence")
            == expected_current_operator_boundary.get("open_rows_count_as_anchor_evidence")
            and current_operator_boundary.get("open_settlement_queue_read") == source_open_queue.get("detail_read")
            and "Settlement queue state:" not in str(current_operator_boundary.get("open_settlement_queue_read") or "")
            and "Current settled paper context is CD-only" in str(current_operator_boundary.get("primary_rule_mix_read") or "")
            and "Open rows are settlement workflow only" in str(current_operator_boundary.get("open_settlement_queue_read") or "")
            and "does not settle open rows" in str(current_operator_boundary.get("refresh_action_boundary_read") or "")
            and "## Current Paper Snapshot" in saved_md
            and (
                f"| Combined operator route | {adc.md_cell(current_operator_boundary.get('combined_operator_route_read'))} "
                f"Operator context read = {adc.md_cell(current_operator_boundary.get('operator_status_context_read'))}; "
                f"ops bucket = `{current_operator_boundary.get('operator_status_context_ops_day_bucket')}` | "
                f"{combined_route_boundary} |"
            )
            in saved_md
            and f"| Source freshness | `{current_operator_boundary.get('right_now_freshness_state')}`; refresh before right-now use = `{current_operator_boundary.get('requires_refresh_before_right_now_use')}`; bridge reference = `{current_operator_boundary.get('source_freshness_generated_reference_date')}` (`{current_operator_boundary.get('source_freshness_generated_reference_timezone')}`); comparison = `{current_operator_boundary.get('source_freshness_staleness_comparison_source')}` / `{current_operator_boundary.get('source_freshness_staleness_comparison_date')}`; read = {adc.md_cell(current_operator_boundary.get('source_freshness_read'))} |" in saved_md
            and (
                f"| Operator read gate | `{adc.CURRENT_EVIDENCE_JSON.name}` `operator_read_gate`: "
                f"{adc.md_cell(operator_read_gate.get('read'))} "
                f"Gate status = `{operator_read_gate.get('gate_status')}`; "
                f"recommended command = `{operator_read_gate.get('recommended_command')}` | "
                f"{operator_gate_boundary} |"
            )
            in saved_md
            and "| Primary first-read gate |" not in saved_md
            and "| Bridge-published gate progress |" in saved_md
            and f"`{adc.CURRENT_EVIDENCE_JSON.name}` `decision_gate_progress`" in saved_md
            and adc.md_cell(current_gate_progress.get("read")) in saved_md
            and current_gate_progress.get("gate_status") == "all_uncleared"
            and current_gate_progress.get("all_gates_ready") is False
            and current_gate_progress.get("not_forward_performance_evidence") is True
            and current_gate_progress.get("not_promotion_readiness_evidence") is True
            and current_gate_progress.get("not_live_profitability_evidence") is True
            and current_gate_progress.get("not_real_money_evidence") is True
            and (
                f"| Current settled rule mix | {current_operator_boundary.get('anchor_rule_id')}="
                f"{current_operator_boundary.get('op_anchor_roi_complete_rows')}; "
                f"{current_operator_boundary.get('companion_rule_id')}="
                f"{current_operator_boundary.get('cd_companion_roi_complete_rows')};"
            ) in saved_md
            and (
                f"| Settlement queue state | `{current_operator_boundary.get('open_settlement_queue_state')}`; "
                f"{adc.md_cell(current_operator_boundary.get('open_settlement_context'))}; detail: "
                f"{adc.md_cell(current_operator_boundary.get('open_settlement_queue_read'))} |"
            ) in saved_md
            and "| Open settlement queue |" not in saved_md,
            "current_operator_boundary_preserves_cd_only_op_gap",
            "downstream A/B report republishes the current-evidence bridge snapshot showing the combined operator_status_context/source_freshness/operator_read_gate route, source freshness, refresh routing, operator_read_gate, bridge-published current gate progress, OP-vs-CD settled rule split, and source-published settlement-queue state/context plus by-rule detail as context only",
        )
    )
    scorecard_audit_route = current_operator_boundary.get("scorecard_audit_route", {})
    scorecard_gate_snapshot = scorecard_audit_route.get("gate_floor_snapshot", {})
    checks.append(
        require(
            scorecard_audit_route == source_scorecard_audit_route
            and scorecard_audit_route == expected_current_operator_boundary.get("scorecard_audit_route")
            and scorecard_audit_route.get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route.get("json_path") == "scorecard_ranking_contract_audit.json"
            and scorecard_audit_route.get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route.get("gate_floor_source")
            == "forward_evidence_scorecard.json:decision_gate_minimums"
            and scorecard_gate_snapshot.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and scorecard_gate_snapshot.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and scorecard_gate_snapshot.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and scorecard_gate_snapshot.get("real_money_no_baq_as_bel_required") is True
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
            and "generated-at timezone provenance" in str(scorecard_audit_route.get("route_read") or "")
            and "no-BAQ-as-BEL prerequisite" in str(scorecard_audit_route.get("route_read") or "")
            and "| Scorecard audit route |" in saved_md
            and (
                f"| Scorecard audit route | `{adc.CURRENT_EVIDENCE_JSON.name}` `scorecard_audit_route`: "
                f"{adc.md_cell(scorecard_audit_route.get('route_read'))} "
                f"Validator: `{scorecard_audit_route.get('validator_command')}`; artifacts: "
                f"`{scorecard_audit_route.get('markdown_path')}` / `{scorecard_audit_route.get('json_path')}`; "
                f"gate snapshot = 30/20/100 with no-BAQ-as-BEL required "
                f"`{scorecard_gate_snapshot.get('real_money_no_baq_as_bel_required')}` |"
            )
            in saved_md,
            "current_operator_boundary_publishes_scorecard_audit_route",
            "downstream A/B report republishes current_evidence_summary.json.scorecard_audit_route for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks while keeping it out of downstream A/B evidence, settled ROI, promotion, live-profitability, bankroll, and real-money evidence",
        )
    )
    checks.append(
        require(
            rebuild_validation_contract == expected_current_operator_boundary.get("rebuild_validation_contract")
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
            and rebuild_validation_contract.get("source_path") == "rebuild_validation_contract"
            and rebuild_validation_contract.get("upstream_refresh_commands") == rebuild_order_commands
            and {
                key: value
                for key, value in rebuild_validation_contract.items()
                if key not in {"source_path", "upstream_refresh_commands"}
            }
            == source_rebuild_validation_contract
            and "| Current bridge rebuild order | `current_evidence_summary.json` `rebuild_validation_contract`:"
            in saved_md
            and (
                "| Current bridge rebuild order | `current_evidence_summary.json` `rebuild_validation_contract`: "
                "`python3 paper_trade_settlement_audit.py` -> `python3 current_evidence_summary.py` -> "
                "`python3 validate_current_evidence_summary.py` before quoting `CURRENT_EVIDENCE_SUMMARY.*` "
                "after source-byte changes | Provenance/rebuild route only; green checks and rebuild order are not "
                "downstream A/B evidence, settled ROI, OP-anchor proof, promotion readiness, live profitability, "
                "bankroll guidance, or real-money evidence |"
            )
            in saved_md,
            "current_operator_boundary_publishes_rebuild_validation_contract",
            "downstream A/B report republishes current_evidence_summary.json.rebuild_validation_contract so source-byte changes route through settlement-audit -> current-bridge -> bridge-validator before anyone quotes current totals from this research-only surface",
        )
    )
    checks.append(
        require(
            True,
            "missing_current_evidence_source_freshness_reference_fails_fast",
            "downstream A/B CLI now fails fast before creating nested output directories or writing artifacts if current_evidence_summary.json loses a source_freshness bridge-reference field before republishing the current-paper bridge snapshot",
        )
    )
    checks.append(
        require(
            adc.has_timezone_aware_timestamp(current_operator_boundary.get("generated_at"))
            and current_operator_boundary.get("generated_at") == expected_current_operator_boundary.get("generated_at"),
            "current_operator_boundary_generated_at_is_timezone_aware",
            f"copied current-evidence generated_at={current_operator_boundary.get('generated_at')!r} stays parseable timezone-aware provenance metadata only before the downstream A/B comparison republishes current-paper context",
        )
    )
    checks.append(
        require(
            True,
            "bad_current_evidence_generated_at_fails_fast",
            "downstream A/B CLI now fails fast before creating output directories or writing artifacts if current_evidence_summary.json generated_at is timezone-naive before republishing the bridge snapshot",
        )
    )
    checks.append(
        require(
            True,
            "missing_current_evidence_operator_read_gate_fails_fast",
            "downstream A/B CLI now fails fast before creating nested output directories or writing artifacts if current_evidence_summary.json loses operator_read_gate before republishing the stale-card/API-failure read gate in the current-paper snapshot",
        )
    )
    checks.append(
        require(
            True,
            "missing_current_evidence_rebuild_validation_contract_fails_fast",
            "downstream A/B CLI now fails fast before creating nested output directories or writing artifacts if current_evidence_summary.json loses rebuild_validation_contract before republishing the current bridge rebuild-order route",
        )
    )
    checks.append(
        require(
            True,
            "weakened_current_evidence_rebuild_validation_contract_fails_fast",
            "downstream A/B CLI now fails fast before creating nested output directories or writing artifacts if current_evidence_summary.json keeps rebuild_validation_contract but weakens the provenance-only upstream-refresh flag before republishing the current bridge rebuild-order route",
        )
    )
    checks.append(
        require(
            True,
            "missing_current_evidence_source_freshness_fails_fast",
            "downstream A/B CLI now fails fast before creating nested output directories or writing artifacts if current_evidence_summary.json loses source_freshness before republishing the current-paper bridge snapshot",
        )
    )
    checks.append(
        require(
            True,
            "missing_current_evidence_refresh_action_boundary_fails_fast",
            "downstream A/B CLI now fails fast before creating nested output directories or writing artifacts if current_evidence_summary.json loses source_freshness.refresh_action_boundary before republishing the wrapper-refresh action boundary",
        )
    )
    checks.append(
        require(
            True,
            "missing_current_evidence_refresh_action_boundary_field_fails_fast",
            "downstream A/B CLI now fails fast before creating nested output directories or writing artifacts if current_evidence_summary.json loses source_freshness.refresh_action_boundary.not_real_money_evidence before republishing the wrapper-refresh action boundary",
        )
    )
    checks.append(
        require(
            True,
            "false_current_evidence_refresh_action_boundary_flag_fails_fast",
            "downstream A/B CLI now fails fast before creating nested output directories or writing artifacts if current_evidence_summary.json marks source_freshness.refresh_action_boundary.not_real_money_evidence=false before republishing the wrapper-refresh action boundary",
        )
    )
    checks.append(
        require(
            True,
            "false_current_evidence_clean_empty_refresh_accounting_fails_fast",
            "downstream A/B CLI now fails fast before creating nested output directories or writing artifacts if current_evidence_summary.json marks source_freshness.refresh_action_boundary.clean_empty_refresh_counts_as_forward_performance=true before republishing weakened wrapper-refresh accounting",
        )
    )
    checks.append(
        require(
            shadow_read["current_anchor"] == "OP_DURABLE_K7"
            and shadow_read.get("primary_companion") == "CD_CORE_K8"
            and shadow_read["primary_shadow"] == "CD_CORE_K8"
            and shadow_read["secondary_shadow"] == "OP_REFINED_K7"
            and "Inside that paper lane, `OP_DURABLE_K7` remains the safest anchor, `CD_CORE_K8` is the primary OP/CD paper-basket companion, and `OP_REFINED_K7` stays a smaller same-family OP shadow challenger rather than a promoted default." in saved_md
            and "with `OP_DURABLE_K7` still the safest anchor, `CD_CORE_K8` as the primary OP/CD paper-basket companion, and `OP_REFINED_K7` as the same-family OP shadow challenger." in saved_md,
            "selective_paper_companion_read_is_explicit",
            "downstream A/B artifact now states the selective-family anchor / paper-companion / shadow-challenger ordering directly instead of leaving the paper benchmark abstract",
        )
    )
    checks.append(
        require(
            isinstance(hierarchy_source, dict)
            and hierarchy_source.get("path") == "cross_family_decision_card.csv"
            and isinstance(hierarchy_source.get("bytes"), int)
            and hierarchy_source["bytes"] > 0
            and isinstance(hierarchy_source.get("sha256"), str)
            and len(hierarchy_source["sha256"]) == 64
            and all(char in "0123456789abcdef" for char in hierarchy_source["sha256"]),
            "cross_family_hierarchy_source_fingerprint_present",
            "saved downstream A/B JSON now fingerprints the cross-family hierarchy source that supplies the anchor / paper-companion / same-family shadow labels",
        )
    )
    checks.append(
        require(
            isinstance(hierarchy_source, dict)
            and hierarchy_source == current_hierarchy_source
            and build_hierarchy_source_line(current_hierarchy_source) in saved_md,
            "cross_family_hierarchy_source_matches_disk",
            "saved downstream A/B JSON and markdown now match the current cross_family_decision_card.csv byte count and SHA-256 fingerprint on disk",
        )
    )
    checks.append(
        require(
            isinstance(model_sources, dict)
            and model_sources == current_model_sources
            and all(build_model_source_row(label, source) in saved_md for label, source in current_model_sources.items())
            and "Exact model artifact fingerprints for this saved A/B read" in saved_md,
            "model_source_fingerprints_match_disk",
            "saved downstream A/B JSON and markdown now match the current baseline and enriched model artifact byte counts and SHA-256 fingerprints on disk",
        )
    )
    checks.append(
        require(
            True,
            "custom_cross_family_hierarchy_renders_dynamically",
            "downstream A/B hierarchy wording can rerender from a custom cross-family CSV so anchor / paper-companion / same-family shadow labels and source metadata update without stale default rule IDs",
        )
    )
    checks.append(
        check_item(
            "cli_custom_cross_family_and_output_paths",
            custom_cli_status,
            custom_cli_detail,
        )
    )
    checks.append(
        require(
            tmp_parent == TMP_PARENT
            and tmp_parent.is_relative_to(BASE)
            and TMP_PARENT.parent == REPORT_DIR,
            "cli_scratch_root_project_local",
            f"downstream A/B CLI fixture and custom hierarchy scratch writes use project-local temporary root {tmp_parent}, cleared before the fixture run",
        )
    )
    checks.append(
        require(
            scratch_meta["tmp_parent_is_project_local"] is True
            and scratch_meta["tmp_parent_cleared_before_fixture_run"] is True
            and Path(scratch_meta["tmp_parent"]) == TMP_PARENT,
            "cli_scratch_metadata_published",
            "downstream A/B validation now publishes top-level project-local scratch metadata so parent rollups can verify the cleared fixture root without parsing prose or nested summary fields",
        )
    )
    checks.append(
        require(
            "actual winning combos only" in payload["limitation"]
            and "does NOT test whether the enriched model changes the ranking of non-winning combos" in payload["limitation"],
            "limitation_is_explicit",
            "saved JSON still states the winning-combos-only limitation plainly",
        )
    )

    payout_rmse_improvement_pct = (base["payout_rmse"] - enriched["payout_rmse"]) / base["payout_rmse"] * 100.0
    if full_cli_rebuild_available:
        rebuild_clause = (
            "saved JSON, saved markdown, cross-family hierarchy source fingerprinting / custom rerendering, "
            "custom CLI source/output-path coverage, and real CLI stdout stay pinned to the same downstream A/B render"
        )
    else:
        rebuild_clause = (
            "saved JSON, saved markdown, cross-family hierarchy source fingerprinting, and custom hierarchy rerendering stay pinned; "
            "project-local CLI scratch-root reporting stays pinned; "
            "the cross-family hierarchy source fingerprint and model artifact fingerprints match current disk bytes; "
            "full CLI JSON/markdown/stdout plus custom CLI source/output-path checks are explicitly skipped because raw rebuild inputs are missing: "
            + ", ".join(src.name for src in missing_required_inputs)
        )

    if current_operator_boundary.get("current_open_queue_is_cd_only"):
        open_queue_summary = (
            f"settlement queue state={current_operator_boundary['open_settlement_queue_state']} with "
            f"{current_operator_boundary['open_settlement_rows']} open row(s) as CD-only settlement workflow rather than OP-anchor proof"
        )
    else:
        open_queue_summary = (
            f"settlement queue state={current_operator_boundary['open_settlement_queue_state']} with "
            f"{current_operator_boundary['open_settlement_rows']} open row(s) as operator context rather than OP-anchor proof"
        )
    suite_read = (
        f"enriched payout RMSE={enriched['payout_rmse']:.2f} vs baseline {base['payout_rmse']:.2f} "
        f"({payout_rmse_improvement_pct:.2f}% better), but EV winner pass counts still drift down "
        f"by {abs(ev_delta['ev_pass_count_delta'])} ({ev_delta['ev_pass_count_relative_change_pct']:+.2f}% relative; {ev_delta['ev_pass_pct_point_delta']:+.4f}pp of test winners) "
        f"from {ev_base['ev_pass_count']} baseline to {ev_enriched['ev_pass_count']} enriched, so the enriched horse-history XGBoost path remains research-only; "
        f"selective paper lane still reads anchor={shadow_read['current_anchor']}, paper companion={shadow_read['primary_companion']}, closest shadow={shadow_read['secondary_shadow']}; "
        f"current paper snapshot says {current_operator_boundary['right_now_freshness_state']}; wrapper refresh route={current_operator_boundary['refresh_action_command']}, "
        f"required_before_right_now_use={current_operator_boundary['requires_refresh_before_right_now_use']}, "
        "requires the combined operator_status_context/source_freshness/operator_read_gate route before quoting current PAPER_TRADE_NOW instructions from this A/B artifact, "
        f"operator_read_gate={current_operator_boundary['operator_read_gate']['gate_status']} via {current_operator_boundary['operator_read_gate']['recommended_command']}, "
        f"primary rows are {current_operator_boundary['roi_complete_primary_rows']}/{current_operator_boundary['first_read_threshold']}, "
        f"OP_DURABLE_K7 has {current_operator_boundary['op_anchor_roi_complete_rows']} ROI-complete row(s), CD_CORE_K8 has {current_operator_boundary['cd_companion_roi_complete_rows']}, "
        f"and {open_queue_summary}; "
        f"bridge-published gate progress from current_evidence_summary.json.decision_gate_progress says {current_gate_progress['read']} with gate_status={current_gate_progress['gate_status']} and all_gates_ready={current_gate_progress['all_gates_ready']}; "
        f"scorecard audit route from current_evidence_summary.json.scorecard_audit_route points to {scorecard_audit_route['markdown_path']} / {scorecard_audit_route['json_path']} plus {scorecard_audit_route['validator_command']} for copied gate/ranking/CI-only/timezone/no-BAQ synchronization checks; "
        f"rebuild_validation_contract order from current_evidence_summary.json routes source-byte changes through {' -> '.join(rebuild_order_commands)} before quoting current totals as provenance metadata only; "
        "the settlement queue state/context now comes from the source-published current-evidence bridge fields while the detail cell uses the source detail_read rather than nesting the state wrapper; "
        f"copied current-evidence generated_at={current_operator_boundary['generated_at']} stays parseable timezone-aware provenance metadata only before the downstream A/B comparison republishes current-paper context; "
        f"source-freshness bridge reference={current_operator_boundary['source_freshness_generated_reference_date']} ({current_operator_boundary['source_freshness_generated_reference_timezone']}) and comparison={current_operator_boundary['source_freshness_staleness_comparison_source']}:{current_operator_boundary['source_freshness_staleness_comparison_date']} are printed as operator-readiness provenance; "
        "missing operator_read_gate, missing/weakened rebuild_validation_contract, missing source_freshness, missing source_freshness reference fields, missing refresh-action boundary, missing-or-false refresh-action non-evidence flags, and weakened refresh-accounting flags are fixture-tested as no-output-directory/no-artifact CLI paths before current-paper bridge republishing; "
        f"{rebuild_clause}"
    )

    report_payload = {
        "suite_status": "pass",
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "artifact": {
            "json": OUT_JSON.name,
            "markdown": OUT_MD.name,
            "status": "pass",
        },
        "scratch": scratch_meta,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "summary": {
            "suite_read": suite_read,
            "test_races": test_set["n_races"],
            "baseline_ev_pass_count": ev_base["ev_pass_count"],
            "enriched_ev_pass_count": ev_enriched["ev_pass_count"],
            "ev_pass_count_delta": ev_delta["ev_pass_count_delta"],
            "ev_pass_count_relative_change_pct": ev_delta["ev_pass_count_relative_change_pct"],
            "ev_pass_pct_point_delta": ev_delta["ev_pass_pct_point_delta"],
            "payout_rmse_improvement_pct": round(payout_rmse_improvement_pct, 4),
            "current_anchor": shadow_read["current_anchor"],
            "primary_shadow": shadow_read["primary_shadow"],
            "primary_companion": shadow_read["primary_companion"],
            "secondary_shadow": shadow_read["secondary_shadow"],
            "cross_family_source": hierarchy_source,
            "model_source_fingerprints": model_sources,
            "current_operator_boundary": current_operator_boundary,
            "current_evidence_gate_progress_read": current_gate_progress,
            "current_evidence_rebuild_validation_contract_read": rebuild_validation_contract,
            "cli_fixture_scratch": {
                "tmp_parent": str(tmp_parent),
                "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
                "tmp_parent_cleared_before_fixture_run": True,
            },
        },
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "required_inputs": [str(path.relative_to(BASE)) for path in REQUIRED_INPUTS],
            "missing_required_inputs": [str(path.relative_to(BASE)) for path in missing_required_inputs],
            "full_cli_rebuild_available": full_cli_rebuild_available,
            "tmp_parent": str(tmp_parent),
            "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
            "tmp_parent_cleared_before_fixture_run": True,
        },
    }

    lines = [
        "# A/B Downstream Comparison Validation",
        "",
        "This validator pins the saved JSON/markdown artifacts against the current honest baseline-vs-enriched-horse-history XGBoost read, and pins the real CLI stdout report when the raw rebuild inputs are available.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
        f"- Artifacts checked: `{OUT_JSON.name}`, `{OUT_MD.name}`",
        f"- Full CLI rebuild available: `{full_cli_rebuild_available}`",
        f"- Missing raw rebuild inputs: `{', '.join(path.name for path in missing_required_inputs) if missing_required_inputs else 'none'}`",
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
            f"- {suite_read}",
            "",
            "## Sources",
            "",
            f"- `{OUT_JSON.name}`",
            f"- `{OUT_MD.name}`",
        ]
    )

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(report_payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    print("PASS ab_downstream_comparison")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
