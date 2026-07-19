#!/usr/bin/env python3
"""
Validation for refresh_live_paper_trade_surfaces.py.

Purpose:
- keep the saved-live refresh helper reproducible instead of merely documented
- prove the helper can rebuild stale per-run operator surfaces plus temp-routed top-level surfaces
- pin the --latest-only selector so targeted refreshes do not silently broaden scope
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import paper_trade_daily_summary as ptds
import paper_trade_forward_check as ptfc
import paper_trade_lane_monitor as ptlm
import paper_trade_lane_summary as ptls
import paper_trade_next_steps as ptns
import paper_trade_now as ptnow
import paper_trade_ops_history as ptoh
import paper_trade_preflight_note as ptpn
import paper_trade_status_summary as ptss
import refresh_live_paper_trade_surfaces as source_refresh

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "refresh_live_paper_trade_surfaces.py"
LIVE_RUNS_ROOT = BASE / "out" / "daily_portfolio_runs"
FIXTURE_ROOT = BASE / "out" / "status_validation" / "refresh_live_paper_trade_surfaces_fixture"
OUT_DIR = BASE / "out" / "status_validation" / "refresh_live_paper_trade_surfaces"
OUT_MD = OUT_DIR / "refresh_live_paper_trade_surfaces_validation.md"
OUT_JSON = OUT_DIR / "refresh_live_paper_trade_surfaces_validation.json"
REBUILD_COMMAND = "python3 validate_refresh_live_paper_trade_surfaces.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER = [
    "python3 paper_trade_settlement_audit.py",
    "python3 current_evidence_summary.py",
    "python3 validate_current_evidence_summary.py",
]
VALID_EVIDENCE_SCOPE = "saved_live_refresh_helper_rebuild_metadata_only"

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "saved-live refresh-helper validator",
    "source_scope": [
        "copied live daily-run folders under isolated refresh-helper fixtures",
        "refresh_live_paper_trade_surfaces.py",
        "source-layer operator renderers used by the refresh helper",
        "forward_evidence_scorecard.json decision_gate_minimums",
        "current_evidence_summary.json rebuild_validation_contract",
    ],
    "valid_use": "saved artifact rebuild reproducibility and wrapper-surface maintenance validation",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "not_new_forward_evidence": True,
    "not_current_day_scanner_result": True,
    "not_live_paper_trade_ledger": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "refresh_helper_validator_passes_are_rebuild_metadata_only": True,
}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def live_run_roots() -> list[Path]:
    roots = sorted(path for path in LIVE_RUNS_ROOT.iterdir() if path.is_dir()) if LIVE_RUNS_ROOT.exists() else []
    if not roots:
        raise AssertionError(f"no live run folders found under {LIVE_RUNS_ROOT}")
    return roots


def copy_live_runs(case_root: Path) -> tuple[Path, list[Path]]:
    if case_root.exists():
        shutil.rmtree(case_root)
    runs_root = case_root / "out" / "daily_portfolio_runs"
    shutil.copytree(LIVE_RUNS_ROOT, runs_root)
    copied = sorted(path for path in runs_root.iterdir() if path.is_dir())
    if not copied:
        raise AssertionError(f"failed to copy live run folders into {runs_root}")
    return runs_root, copied


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except Exception:
        return str(path)


def build_fixture_scratch_metadata() -> dict[str, Any]:
    return {
        "fixture_root": str(FIXTURE_ROOT),
        "fixture_root_relative": rel(FIXTURE_ROOT),
        "fixture_root_is_project_local": FIXTURE_ROOT.is_relative_to(BASE / "out" / "status_validation"),
        "case_roots_cleared_by_copy_live_runs": True,
        "evidence_boundary": (
            "refresh-helper fixture scratch metadata is saved-surface rebuild reproducibility context only, "
            "not a current-day scanner result, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence"
        ),
    }


def require_positive_non_bool_int(value: Any, *, source_name: str, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, source_name: str, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AssertionError(f"{source_name} {field_name} must be a list of strings")
    return value


def read_scorecard_gate_minimums(scorecard_json: Path = SCORECARD_JSON) -> dict[str, Any]:
    source_name = rel(scorecard_json)
    payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
    gates = payload.get("decision_gate_minimums")
    if not isinstance(gates, dict):
        raise AssertionError(f"{source_name} is missing decision_gate_minimums")
    anchor = gates.get("anchor_displacement")
    phase8 = gates.get("phase8_promotion_review")
    real_money = gates.get("real_money_discussion")
    if not isinstance(anchor, dict) or not isinstance(phase8, dict) or not isinstance(real_money, dict):
        raise AssertionError(f"{source_name} decision_gate_minimums is incomplete")
    anchor_min = require_positive_non_bool_int(
        anchor.get("min_roi_complete_settled_observations"),
        source_name=source_name,
        field_name="decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
    )
    phase8_min = require_positive_non_bool_int(
        phase8.get("min_roi_complete_settled_observations"),
        source_name=source_name,
        field_name="decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
    )
    real_money_min = require_positive_non_bool_int(
        real_money.get("min_total_settled_observations_with_usable_roi"),
        source_name=source_name,
        field_name="decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
    )
    real_money_requires = require_string_list(
        real_money.get("also_requires"),
        source_name=source_name,
        field_name="decision_gate_minimums.real_money_discussion.also_requires",
    )
    if NO_BAQ_AS_BEL_PREREQUISITE not in real_money_requires:
        raise AssertionError(
            f"{source_name} decision_gate_minimums.real_money_discussion.also_requires "
            f"must include {NO_BAQ_AS_BEL_PREREQUISITE}"
        )
    return {
        "source": source_name,
        "source_path": "decision_gate_minimums",
        "anchor_displacement_min_roi_complete_settled_observations": anchor_min,
        "phase8_promotion_review_min_roi_complete_settled_observations": phase8_min,
        "real_money_discussion_min_total_settled_observations_with_usable_roi": real_money_min,
        "real_money_also_requires": real_money_requires,
        "real_money_no_baq_as_bel_required": True,
        "evidence_boundary": (
            "saved-live refreshes, stale-surface rebuilds, copied-run fixture cleanliness, "
            "and top-card rerenders do not count toward anchor-displacement, Phase 8 "
            "promotion-review, or real-money discussion gates"
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--current-evidence-json", type=Path, default=CURRENT_EVIDENCE_JSON)
    parser.add_argument("--fixture-root", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args(argv)


def configure_output_paths(fixture_root: Path, out_dir: Path) -> None:
    global FIXTURE_ROOT, OUT_DIR, OUT_MD, OUT_JSON
    FIXTURE_ROOT = fixture_root
    OUT_DIR = out_dir
    OUT_MD = OUT_DIR / "refresh_live_paper_trade_surfaces_validation.md"
    OUT_JSON = OUT_DIR / "refresh_live_paper_trade_surfaces_validation.json"


def guardrail(condition: bool, check: str, detail: str) -> dict[str, str]:
    if not condition:
        raise AssertionError(f"{check}: {detail}")
    return {"check": check, "status": "pass", "detail": detail}


def assert_scorecard_failure_before_artifacts(
    *,
    scorecard_json: Path,
    mutation: Any,
    expected_stderr: str,
    check_name: str,
    detail: str,
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix=f"{check_name}_") as tmp:
        tmpdir = Path(tmp)
        bad_scorecard = tmpdir / "forward_evidence_scorecard.json"
        bad_payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
        mutation(bad_payload)
        bad_scorecard.write_text(json.dumps(bad_payload, indent=2) + "\n", encoding="utf-8")

        fixture_root = tmpdir / "fixture_root"
        out_dir = tmpdir / "nested" / "report_artifacts"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(bad_scorecard),
                "--fixture-root",
                str(fixture_root),
                "--out-dir",
                str(out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
        if result.returncode == 0:
            raise AssertionError(f"{check_name}: malformed scorecard unexpectedly passed")
        if expected_stderr not in result.stderr:
            raise AssertionError(
                f"{check_name}: failure stderr no longer explains the malformed scorecard gate\n"
                f"stderr={result.stderr}"
            )
        if fixture_root.exists() or out_dir.exists():
            raise AssertionError(f"{check_name}: malformed scorecard created fixture/report artifacts")
    return guardrail(True, check_name, detail)


def scorecard_no_artifact_guardrails(scorecard_json: Path) -> list[dict[str, str]]:
    return [
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["anchor_displacement"].__setitem__(
                "min_roi_complete_settled_observations",
                True,
            ),
            expected_stderr=(
                "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check_name="scorecard_boolean_gate_floor_fails_before_refresh_helper_artifacts",
            detail=(
                "a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before "
                "the saved-live refresh validator creates fixture roots or report artifacts"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["phase8_promotion_review"].__setitem__(
                "min_roi_complete_settled_observations",
                0,
            ),
            expected_stderr=(
                "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check_name="scorecard_nonpositive_phase8_gate_floor_fails_before_refresh_helper_artifacts",
            detail=(
                "a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails before "
                "the saved-live refresh validator creates fixture roots or report artifacts"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                "min_total_settled_observations_with_usable_roi",
                0,
            ),
            expected_stderr=(
                "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi "
                "must be a positive non-boolean integer"
            ),
            check_name="scorecard_nonpositive_real_money_gate_floor_fails_before_refresh_helper_artifacts",
            detail=(
                "a non-positive real-money discussion floor in forward_evidence_scorecard.json fails before "
                "the saved-live refresh validator creates fixture roots or report artifacts"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                "also_requires",
                [
                    item
                    for item in payload["decision_gate_minimums"]["real_money_discussion"].get(
                        "also_requires",
                        [],
                    )
                    if item != NO_BAQ_AS_BEL_PREREQUISITE
                ],
            ),
            expected_stderr=(
                "decision_gate_minimums.real_money_discussion.also_requires must include "
                f"{NO_BAQ_AS_BEL_PREREQUISITE}"
            ),
            check_name="scorecard_missing_no_baq_fails_before_refresh_helper_artifacts",
            detail=(
                "a scorecard real-money gate that drops the no BAQ-as-BEL prerequisite fails before "
                "the saved-live refresh validator creates fixture roots or report artifacts"
            ),
        ),
    ]


def read_current_evidence_rebuild_contract(current_evidence_json: Path = CURRENT_EVIDENCE_JSON) -> dict[str, Any]:
    source_name = rel(current_evidence_json)
    payload = json.loads(current_evidence_json.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{source_name} must be a JSON object")
    contract = payload.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise AssertionError(f"{source_name} is missing rebuild_validation_contract")

    upstream_order = contract.get("upstream_refresh_order")
    if not isinstance(upstream_order, list) or len(upstream_order) != 3:
        raise AssertionError(f"{source_name} rebuild_validation_contract.upstream_refresh_order shape drifted")
    commands: list[str] = []
    orders: list[int] = []
    for step in upstream_order:
        if not isinstance(step, dict):
            raise AssertionError(f"{source_name} rebuild_validation_contract.upstream_refresh_order steps must be objects")
        commands.append(step.get("command"))
        orders.append(step.get("order"))
    if orders != [1, 2, 3] or commands != EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER:
        raise AssertionError(f"{source_name} rebuild_validation_contract upstream order drifted")
    if contract.get("prerequisite_rebuild_command") != EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER[0]:
        raise AssertionError(f"{source_name} rebuild_validation_contract prerequisite command drifted")
    if contract.get("rebuild_command") != EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER[1]:
        raise AssertionError(f"{source_name} rebuild_validation_contract rebuild command drifted")
    if contract.get("direct_validation_command") != EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER[2]:
        raise AssertionError(f"{source_name} rebuild_validation_contract validator command drifted")
    for flag in (
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
        "requires_source_consistency_before_quoting_current_totals",
        "upstream_refresh_order_is_provenance_metadata_only",
        "not_settled_roi_or_real_money_evidence",
    ):
        if contract.get(flag) is not True:
            raise AssertionError(f"{source_name} rebuild_validation_contract.{flag} must be true")

    return {
        "source": source_name,
        "source_path": "rebuild_validation_contract",
        "upstream_refresh_order_commands": commands,
        "prerequisite_rebuild_command": contract.get("prerequisite_rebuild_command"),
        "rebuild_command": contract.get("rebuild_command"),
        "direct_validation_command": contract.get("direct_validation_command"),
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change": contract.get(
            "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change"
        ),
        "requires_source_consistency_before_quoting_current_totals": contract.get(
            "requires_source_consistency_before_quoting_current_totals"
        ),
        "upstream_refresh_order_is_provenance_metadata_only": contract.get(
            "upstream_refresh_order_is_provenance_metadata_only"
        ),
        "not_settled_roi_or_real_money_evidence": contract.get("not_settled_roi_or_real_money_evidence"),
        "evidence_boundary": (
            "current-evidence rebuild-order validation is provenance metadata only; it is not settled ROI, "
            "promotion readiness, live profitability, bankroll guidance, or real-money evidence"
        ),
    }


def assert_current_evidence_failure_before_artifacts(
    *,
    scorecard_json: Path,
    current_evidence_json: Path,
    mutation: Any,
    expected_stderr: str,
    check_name: str,
    detail: str,
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix=f"{check_name}_") as tmp:
        tmpdir = Path(tmp)
        bad_current_evidence = tmpdir / "current_evidence_summary.json"
        bad_payload = json.loads(current_evidence_json.read_text(encoding="utf-8"))
        mutation(bad_payload)
        bad_current_evidence.write_text(json.dumps(bad_payload, indent=2) + "\n", encoding="utf-8")

        fixture_root = tmpdir / "fixture_root"
        out_dir = tmpdir / "nested" / "report_artifacts"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(scorecard_json),
                "--current-evidence-json",
                str(bad_current_evidence),
                "--fixture-root",
                str(fixture_root),
                "--out-dir",
                str(out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
        if result.returncode == 0:
            raise AssertionError(f"{check_name}: malformed current-evidence sidecar unexpectedly passed")
        if expected_stderr not in result.stderr:
            raise AssertionError(
                f"{check_name}: failure stderr no longer explains the malformed current-evidence rebuild contract\n"
                f"stderr={result.stderr}"
            )
        if fixture_root.exists() or out_dir.exists():
            raise AssertionError(f"{check_name}: malformed current-evidence sidecar created fixture/report artifacts")
    return guardrail(True, check_name, detail)


def current_evidence_no_artifact_guardrails(
    scorecard_json: Path,
    current_evidence_json: Path,
) -> list[dict[str, str]]:
    return [
        assert_current_evidence_failure_before_artifacts(
            scorecard_json=scorecard_json,
            current_evidence_json=current_evidence_json,
            mutation=lambda payload: payload.pop("rebuild_validation_contract", None),
            expected_stderr="is missing rebuild_validation_contract",
            check_name="current_evidence_missing_rebuild_contract_fails_before_refresh_helper_artifacts",
            detail=(
                "a current_evidence_summary.json sidecar missing rebuild_validation_contract fails before "
                "the saved-live refresh validator creates fixture roots or report artifacts"
            ),
        ),
        assert_current_evidence_failure_before_artifacts(
            scorecard_json=scorecard_json,
            current_evidence_json=current_evidence_json,
            mutation=lambda payload: payload["rebuild_validation_contract"].__setitem__(
                "upstream_refresh_order_is_provenance_metadata_only",
                False,
            ),
            expected_stderr="rebuild_validation_contract.upstream_refresh_order_is_provenance_metadata_only must be true",
            check_name="current_evidence_weakened_rebuild_contract_fails_before_refresh_helper_artifacts",
            detail=(
                "a current_evidence_summary.json sidecar whose rebuild order is no longer provenance metadata only "
                "fails before the saved-live refresh validator creates fixture roots or report artifacts"
            ),
        ),
    ]


def expected_preflight_jump_path(run_root: Path) -> str:
    return rel(ptds.resolve_preflight_surface(run_root)[0])


def extract_recent_run_context_line(next_steps_path: Path) -> str | None:
    for raw_line in next_steps_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("Latest run context:"):
            return line
    return None


def strip_inline_markdown(value: str) -> str:
    return value.replace("**", "").replace("`", "").strip()


def extract_optional_bullet_value(text: str, label: str) -> str | None:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        prefix = f"- {label}:"
        if line.startswith(prefix):
            value = strip_inline_markdown(line[len(prefix):].strip())
            return value or None
    return None


def assert_daily_summary_keeps_right_now_snapshot(
    daily_summary_text: str,
    right_now_md_text: str,
    case_name: str,
    label_prefix: str,
) -> None:
    if "Right-now snapshot:" not in daily_summary_text:
        raise AssertionError(f"{case_name}: {label_prefix} daily_summary.txt did not keep the routed right-now snapshot header")
    right_now_focus = extract_optional_bullet_value(right_now_md_text, "Focus")
    right_now_timing = extract_optional_bullet_value(right_now_md_text, "Timing")
    right_now_run_freshness = extract_optional_bullet_value(right_now_md_text, "Run freshness")
    right_now_stale_snapshot_note = extract_optional_bullet_value(right_now_md_text, "Stale snapshot note")
    right_now_ops_bucket = extract_optional_bullet_value(right_now_md_text, "Latest ops bucket")
    if right_now_focus and f"- Current operator focus: {right_now_focus}" not in daily_summary_text:
        raise AssertionError(f"{case_name}: {label_prefix} daily_summary.txt did not keep the routed right-now focus snapshot")
    if right_now_timing and f"- Current timing: {right_now_timing}" not in daily_summary_text:
        raise AssertionError(f"{case_name}: {label_prefix} daily_summary.txt did not keep the routed right-now timing snapshot")
    if right_now_run_freshness and f"- Current run freshness: {right_now_run_freshness}" not in daily_summary_text:
        raise AssertionError(f"{case_name}: {label_prefix} daily_summary.txt did not keep the routed right-now freshness snapshot")
    if right_now_stale_snapshot_note and f"- Current stale snapshot note: {right_now_stale_snapshot_note}" not in daily_summary_text:
        raise AssertionError(f"{case_name}: {label_prefix} daily_summary.txt did not keep the routed right-now stale-snapshot note")
    if right_now_ops_bucket and f"- Current ops bucket: {right_now_ops_bucket}" not in daily_summary_text:
        raise AssertionError(f"{case_name}: {label_prefix} daily_summary.txt did not keep the routed right-now ops-bucket snapshot")


def operator_read_gate_issue_flags_from_json(
    right_now_json: Path,
    case_name: str,
) -> tuple[dict[str, bool], str, str]:
    payload = json.loads(right_now_json.read_text(encoding="utf-8"))
    gate = payload.get("operator_read_gate")
    if not isinstance(gate, dict):
        raise AssertionError(f"{case_name}: {rel(right_now_json)} did not publish operator_read_gate")
    flags: dict[str, bool] = {}
    for flag in ptnow.OPERATOR_READ_GATE_ISSUE_FLAGS:
        value = gate.get(flag)
        if not isinstance(value, bool):
            raise AssertionError(f"{case_name}: {rel(right_now_json)} operator_read_gate.{flag} is not boolean")
        flags[flag] = value
    issue_gate = {flag: flags[flag] for flag in ptnow.OPERATOR_READ_GATE_ISSUE_FLAGS}
    return (
        flags,
        ptnow.operator_issue_flags_line(issue_gate),
        ptnow.operator_issue_flags_line(issue_gate, markdown=True),
    )


def assert_top_level_issue_flags_survive_refresh(
    *,
    paper_trade_now_txt: Path,
    paper_trade_now_md: Path,
    paper_trade_now_json: Path,
    current_evidence_json: Path,
    case_name: str,
) -> None:
    flags, text_issue_line, md_issue_line = operator_read_gate_issue_flags_from_json(
        paper_trade_now_json,
        case_name,
    )
    txt_text = paper_trade_now_txt.read_text(encoding="utf-8")
    md_text = paper_trade_now_md.read_text(encoding="utf-8")
    expected_txt = f"- Operator read-gate issue flags: {text_issue_line}"
    expected_md = f"- Operator read-gate issue flags: {md_issue_line}"
    if expected_txt not in txt_text:
        raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.txt dropped issue flags {expected_txt!r}")
    if expected_md not in md_text:
        raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.md dropped issue flags {expected_md!r}")

    current_payload = json.loads(current_evidence_json.read_text(encoding="utf-8"))
    current_gate = current_payload.get("operator_read_gate")
    if not isinstance(current_gate, dict):
        raise AssertionError(f"{case_name}: refreshed current-evidence JSON did not publish operator_read_gate")
    for flag, expected_value in flags.items():
        if current_gate.get(flag) is not expected_value:
            raise AssertionError(
                f"{case_name}: refreshed current-evidence JSON operator_read_gate.{flag} "
                f"did not match PAPER_TRADE_NOW.json"
            )


def assert_daily_summary_lifts_right_now_issue_flags(
    daily_summary_path: Path,
    right_now_json: Path,
    case_name: str,
    label_prefix: str,
) -> None:
    _, text_issue_line, _ = operator_read_gate_issue_flags_from_json(right_now_json, case_name)
    expected = f"- Current operator read-gate issue flags: {text_issue_line}"
    if expected not in daily_summary_path.read_text(encoding="utf-8"):
        raise AssertionError(
            f"{case_name}: {label_prefix} daily_summary.txt did not lift routed right-now issue flags {expected!r}"
        )


def write_existing_right_now_with_issue_flags(case_root: Path, flags: dict[str, bool]) -> tuple[Path, Path]:
    md_path = case_root / "PAPER_TRADE_NOW.md"
    json_path = case_root / "PAPER_TRADE_NOW.json"
    source_json = json.loads(ptds.right_now_json_path(ptds.DEFAULT_RIGHT_NOW).read_text(encoding="utf-8"))
    gate = source_json.get("operator_read_gate")
    if not isinstance(gate, dict):
        raise AssertionError("default PAPER_TRADE_NOW.json must publish operator_read_gate for refresh-helper fixture setup")
    for flag in ptnow.OPERATOR_READ_GATE_ISSUE_FLAGS:
        gate[flag] = bool(flags[flag])
    source_json["operator_read_gate"] = gate
    write_text(json_path, json.dumps(source_json, indent=2) + "\n")

    source_md = ptds.DEFAULT_RIGHT_NOW.read_text(encoding="utf-8")
    expected_line = f"- Operator read-gate issue flags: {ptnow.operator_issue_flags_line(gate, markdown=True)}"
    lines = []
    replaced = False
    for line in source_md.splitlines():
        if line.startswith("- Operator read-gate issue flags:"):
            lines.append(expected_line)
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        lines.append(expected_line)
    write_text(md_path, "\n".join(lines) + "\n")
    return md_path, json_path


def expected_settlement_action_line(settlement_audit_md: Path, lane_name: str, label: str) -> str:
    action, reason = ptds.extract_settlement_audit_action(settlement_audit_md, lane_name, label.lower())
    return f"- {label} settlement-audit action: {action}" + (f" — {reason}" if reason else "")


def assert_daily_summary_keeps_settlement_audit_actions(
    daily_summary_text: str,
    settlement_audit_md: Path,
    case_name: str,
    label_prefix: str,
) -> None:
    boundary = "- Settlement-audit actions are ledger-readiness guidance only; they are not new forward evidence by themselves."
    if boundary not in daily_summary_text:
        raise AssertionError(f"{case_name}: {label_prefix} daily_summary.txt dropped the settlement-audit next-action no-new-evidence boundary")
    for lane_name, label in (("primary", "Primary"), ("shadow", "Shadow")):
        expected = expected_settlement_action_line(settlement_audit_md, lane_name, label)
        if expected not in daily_summary_text:
            raise AssertionError(f"{case_name}: {label_prefix} daily_summary.txt dropped the {label.lower()} settlement-audit next-action line {expected!r}")


def assert_daily_summary_keeps_next_step_source_artifacts(
    daily_summary_text: str,
    run_root: Path,
    case_name: str,
    label_prefix: str,
) -> None:
    for lane_name, label in ((ptds.DEFAULT_PRIMARY_LANE, "Primary"), (ptds.DEFAULT_SHADOW_LANE, "Shadow")):
        source_path = ptds.resolve_next_steps_text_source(run_root / lane_name)
        expected = f"- {label} next-step source artifact: {rel(source_path)}"
        if expected not in daily_summary_text:
            raise AssertionError(
                f"{case_name}: {label_prefix} daily_summary.txt dropped the {label.lower()} next-step source artifact line {expected!r}"
            )


def relocate_scanner_for_anchor(
    run_root: Path,
    lane_name: str,
    anchor_style: str,
    declared: str,
    relocated_path: Path,
    proof_card_count: int,
    proof_race_count: int,
    keep_default_stale: bool = False,
    stale_default_card_count: int = 7,
    stale_default_race_count: int = 77,
) -> dict[str, Any]:
    lane_dir = run_root / lane_name
    original_scanner = lane_dir / "live_scan.status.json"
    pipeline_path = lane_dir / "pipeline_status.json"
    if not original_scanner.exists():
        raise AssertionError(f"relocated scanner fixture needs default scanner sidecar first: {original_scanner}")
    if not pipeline_path.exists():
        raise AssertionError(f"relocated scanner fixture needs pipeline sidecar first: {pipeline_path}")

    base_scanner_payload = json.loads(original_scanner.read_text(encoding="utf-8"))
    scanner_payload = dict(base_scanner_payload)
    scanner_payload.update({
        "result": "no_qualifiers",
        "card_count": proof_card_count,
        "race_count": proof_race_count,
        "race_details_attempted": min(proof_race_count, 12),
        "max_race_limit_hit": 1,
    })
    write_text(relocated_path, json.dumps(scanner_payload, indent=2) + "\n")
    if keep_default_stale:
        stale_payload = dict(base_scanner_payload)
        stale_payload.update({
            "result": "no_qualifiers",
            "card_count": stale_default_card_count,
            "race_count": stale_default_race_count,
            "race_details_attempted": min(stale_default_race_count, 12),
            "max_race_limit_hit": 1,
        })
        write_text(original_scanner, json.dumps(stale_payload, indent=2) + "\n")
    else:
        original_scanner.unlink()

    pipeline_payload = json.loads(pipeline_path.read_text(encoding="utf-8"))
    pipeline_payload.update({
        "scanner_status_path": declared,
        "scanner_result": "no_qualifiers",
        "observation_result": "clean_empty_run",
        "observation_reason": None,
        "scan_hit_count": 0,
        "recommendation_count": 0,
        "bet_count": 0,
    })
    write_text(pipeline_path, json.dumps(pipeline_payload, indent=2) + "\n")

    return {
        "anchor": anchor_style,
        "run": run_root.name,
        "run_root": str(run_root),
        "lane": lane_name,
        "declared": declared,
        "relocated": rel(relocated_path),
        "expected_context": f"across {proof_card_count} card(s) and {proof_race_count} race(s)",
        "stale_default": rel(original_scanner) if keep_default_stale else None,
        "stale_context": f"across {stale_default_card_count} card(s) and {stale_default_race_count} race(s)" if keep_default_stale else None,
    }


def assert_relocated_anchor_proofs(proofs: list[dict[str, Any]], case_name: str) -> None:
    for proof in proofs:
        run_root = Path(str(proof["run_root"]))
        lane_dir = run_root / str(proof["lane"])
        expected = str(proof["expected_context"])
        surfaces = {
            "next_steps.txt": lane_dir / "next_steps.txt",
            "summary.txt": lane_dir / "summary.txt",
            "daily_summary.txt": run_root / "daily_summary.txt",
        }
        for label, path in surfaces.items():
            text = path.read_text(encoding="utf-8")
            if expected not in text:
                raise AssertionError(
                    f"{case_name}: {proof['anchor']} relocated scanner sidecar was not reflected in {label}; "
                    f"expected rebuilt context {expected!r} from {proof['relocated']}"
                )
            stale_context = proof.get("stale_context")
            if stale_context and str(stale_context) in text:
                raise AssertionError(
                    f"{case_name}: {proof['anchor']} rebuilt {label} used stale default scanner context "
                    f"{stale_context!r} from {proof['stale_default']} instead of declared sidecar {proof['relocated']}"
                )


def force_pipeline_recorded_invalid_shape_scanner_missing(lane_dir: Path) -> None:
    default_scanner_path = lane_dir / "live_scan.status.json"
    if default_scanner_path.exists():
        default_scanner_path.unlink()

    pipeline_path = lane_dir / "pipeline_status.json"
    if not pipeline_path.exists():
        raise AssertionError(f"invalid-shape refresh fixture needs pipeline sidecar first: {pipeline_path}")
    pipeline_payload = json.loads(pipeline_path.read_text(encoding="utf-8"))
    pipeline_payload.pop("scanner_status_path", None)
    pipeline_payload.update({
        "run_ts": "2026-05-24T10:11:00",
        "scanner_result": "scanner_status_invalid_shape",
        "scanner_status_state": "invalid_shape",
        "scanner_status_error": "expected scanner-status JSON object, got list",
        "observation_result": "scanner_status_unavailable_with_activity",
        "observation_scope": "operational_limit",
        "observation_reason": "scanner_status_invalid_shape",
        "scan_hit_count": 1,
        "scanner_raw_hit_count": 1,
        "recommendation_count": 1,
        "bet_count": 0,
        "error_count": 0,
    })
    write_text(pipeline_path, json.dumps(pipeline_payload, indent=2) + "\n")


def force_missing_scan_output_state(lane_dir: Path) -> None:
    scanner_path = lane_dir / "live_scan.status.json"
    scanner_payload = {
        "run_ts": "2026-05-24T10:12:00",
        "result": "no_qualifiers",
        "emitted_hit_count": 0,
        "raw_hit_count": 0,
        "rules_path": "phase7_current_paper_rules.json",
    }
    write_text(scanner_path, json.dumps(scanner_payload, indent=2) + "\n")

    pipeline_path = lane_dir / "pipeline_status.json"
    if not pipeline_path.exists():
        raise AssertionError(f"missing scan-output refresh fixture needs pipeline sidecar first: {pipeline_path}")
    pipeline_payload = json.loads(pipeline_path.read_text(encoding="utf-8"))
    pipeline_payload.pop("scanner_status_path", None)
    pipeline_payload.update({
        "run_ts": "2026-05-24T10:12:00",
        "scanner_result": "missing_scan_output",
        "scanner_status_reported_result": "no_qualifiers",
        "scanner_stage_status": "missing_scan_output",
        "observation_result": "scanner_failed_empty_run",
        "observation_scope": "operational_limit",
        "observation_reason": "missing_scan_output",
        "scan_input_empty_fallback_applied": True,
        "scan_input_empty_fallback_reason": "missing_or_empty_scan_output",
        "scan_input_state_before_empty_fallback": "missing",
        "scan_input_empty_fallback_value": "[]",
        "scan_hit_count": 0,
        "scanner_raw_hit_count": 0,
        "recommendation_count": 0,
        "bet_count": 0,
        "error_count": 0,
    })
    write_text(pipeline_path, json.dumps(pipeline_payload, indent=2) + "\n")


def assert_missing_scan_output_survives_refresh(run_root: Path, lane_name: str, case_name: str) -> None:
    lane_dir = run_root / lane_name
    status_fragments = [
        "missing scanner output, 0 scanner hit(s), 0 recommendation(s)",
        "scanner-status reported no_qualifiers",
        "safe empty scan fallback missing_or_empty_scan_output",
        "scan input was missing before fallback",
    ]
    action_fragments = [
        "scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers",
        "the pipeline used a safe empty [] fallback",
        "not a clean no-qualifier observation",
    ]
    for label, path in {
        "next_steps.txt": lane_dir / "next_steps.txt",
        "next_steps.md": lane_dir / "next_steps.md",
    }.items():
        text = strip_inline_markdown(path.read_text(encoding="utf-8"))
        for fragment in action_fragments:
            if fragment not in text:
                raise AssertionError(f"{case_name}: refreshed {label} dropped missing scan-output action fragment {fragment!r}")
        if "completed cleanly and found no qualifying races" in text:
            raise AssertionError(f"{case_name}: refreshed {label} flattened missing scan-output into clean-empty guidance")

    for label, path in {
        "lane summary": lane_dir / "summary.txt",
        "daily summary": run_root / "daily_summary.txt",
    }.items():
        text = strip_inline_markdown(path.read_text(encoding="utf-8"))
        for fragment in status_fragments + action_fragments:
            if fragment not in text:
                raise AssertionError(f"{case_name}: refreshed {label} dropped missing scan-output fragment {fragment!r}")
        if f"{lane_name} run 2026-05-24T10:12:00: clean empty run" in text or "Phase 7 current paper run 2026-05-24T10:12:00: clean empty run" in text:
            raise AssertionError(f"{case_name}: refreshed {label} flattened missing scan-output into a clean-empty headline")


def assert_pipeline_recorded_invalid_shape_survives_refresh(run_root: Path, lane_name: str, case_name: str) -> None:
    lane_dir = run_root / lane_name
    expected_status_fragments = [
        "scanner sidecar recorded invalid shape",
        "scanner-status error: expected scanner-status JSON object, got list",
        "current scanner sidecar file missing",
        "pipeline recorded scanner-status state invalid_shape",
    ]
    for label, path in {
        "lane summary": lane_dir / "summary.txt",
        "daily summary": run_root / "daily_summary.txt",
    }.items():
        text = path.read_text(encoding="utf-8")
        for fragment in expected_status_fragments:
            if fragment not in text:
                raise AssertionError(f"{case_name}: refreshed {label} dropped copied invalid-shape status fragment {fragment!r}")
        if "Phase 8 shadow run 2026-05-24T10:11:00: clean empty run" in text:
            raise AssertionError(f"{case_name}: refreshed {label} flattened the copied invalid-shape state into a clean-empty headline")

    expected_action_fragments = [
        "The latest scanner status sidecar was recorded invalid-shape by the pipeline, and the current scanner sidecar file is missing from this surface.",
    ]
    for label, path in {
        "next_steps.txt": lane_dir / "next_steps.txt",
        "next_steps.md": lane_dir / "next_steps.md",
        "daily summary": run_root / "daily_summary.txt",
    }.items():
        text = strip_inline_markdown(path.read_text(encoding="utf-8"))
        for fragment in expected_action_fragments:
            if fragment not in text:
                raise AssertionError(f"{case_name}: refreshed {label} dropped copied invalid-shape action fragment {fragment!r}")


def run_helper(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=BASE,
        capture_output=True,
        text=True,
        check=True,
    )


def expected_lane_components(run_root: Path, lane: source_refresh.LaneConfig) -> dict[str, str]:
    lane_dir = run_root / lane.name
    scanner_path = source_refresh.resolve_lane_scanner_status_path(lane_dir)
    pipeline_path = lane_dir / "pipeline_status.json"
    preflight_note = run_root / "preflight_note.txt"

    scanner_state = ptss.json_state(scanner_path)
    pipeline_state = ptss.json_state(pipeline_path)
    scanner = ptss.read_json(scanner_path)
    pipeline = ptss.read_json(pipeline_path)
    base_summary_payload = ptss.summarize(
        scanner,
        pipeline,
        scanner_state=scanner_state,
        pipeline_state=pipeline_state,
        require_pipeline_status=True,
    )
    base_summary_text = base_summary_payload["summary_line"] + "\n"

    forward_args = SimpleNamespace(
        signals_ledger=str(lane.signals_ledger),
        recommendation_ledger=str(lane.recommendation_ledger),
        settlement_ledger=str(lane.settlement_ledger),
        rules=str(lane.rules),
        frozen_eval=str(ptfc.DEFAULT_FROZEN_EVAL),
        min_settled=None,
        portfolio_review_settled=None,
        format="json",
        output=None,
    )
    forward_payload = ptfc.build_payload(forward_args)
    forward_check_text = ptfc.render_text(forward_payload)
    forward_check_md = ptfc.render_md(forward_payload) + "\n"

    monitor_args = SimpleNamespace(
        signals_ledger=str(lane.signals_ledger),
        recommendation_ledger=str(lane.recommendation_ledger),
        settlement_ledger=str(lane.settlement_ledger),
        rules=str(lane.rules),
        frozen_eval=str(ptlm.DEFAULT_FROZEN_EVAL),
        min_settled=None,
        portfolio_review_settled=None,
        max_open=5,
        format="json",
        output=None,
    )
    monitor_payload = ptlm.build_monitor_payload(monitor_args)
    lane_monitor_text = ptlm.render_text(monitor_payload)
    lane_monitor_md = ptlm.render_md(monitor_payload) + "\n"

    next_args = SimpleNamespace(
        signals_ledger=str(lane.signals_ledger),
        recommendation_ledger=str(lane.recommendation_ledger),
        settlement_ledger=str(lane.settlement_ledger),
        rules=str(lane.rules),
        frozen_eval=str(ptns.DEFAULT_FROZEN_EVAL),
        min_settled=None,
        portfolio_review_settled=None,
        max_open=5,
        runner=str(ptns.DEFAULT_RUNNER),
        scanner_status=str(scanner_path),
        pipeline_status=str(pipeline_path),
        preflight_note=str(preflight_note),
        format="json",
        output=None,
    )
    next_payload = ptns.build_payload(next_args)
    next_steps_text = ptns.render_text(next_payload)
    next_steps_md = ptns.render_md(next_payload) + "\n"

    scratch = lane_dir / ".refresh_validator_expected"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        scratch_base = scratch / "base_summary.txt"
        write_text(scratch_base, base_summary_text)
        lane_summary_args = SimpleNamespace(
            base_summary=str(scratch_base),
            next_steps_text=str(lane_dir / "next_steps.txt"),
            next_steps_md=str(lane_dir / "next_steps.md"),
            lane_monitor_text=str(lane_dir / "lane_monitor.txt"),
            lane_monitor_md=str(lane_dir / "lane_monitor.md"),
            forward_check_text=str(lane_dir / "forward_check.txt"),
            forward_check_md=str(lane_dir / "forward_check.md"),
            settlement_ledger=str(lane.settlement_ledger),
            display_summary=str(lane_dir / "summary.txt"),
            output=str(lane_dir / "summary.txt"),
        )
        summary_text = ptls.render_text(lane_summary_args)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    return {
        "base_summary": base_summary_text,
        "forward_check_txt": forward_check_text,
        "forward_check_md": forward_check_md,
        "lane_monitor_txt": lane_monitor_text,
        "lane_monitor_md": lane_monitor_md,
        "next_steps_txt": next_steps_text,
        "next_steps_md": next_steps_md,
        "summary_txt": summary_text,
    }


def assert_run_root_matches_source_layer(
    run_root: Path,
    case_name: str,
    right_now_md: Path,
    ops_history_md: Path,
    settlement_audit_md: Path,
) -> None:
    preflight_json = run_root / "preflight_note.json"
    preflight_text = run_root / "preflight_note.txt"
    saved_preflight = json.loads(preflight_json.read_text(encoding="utf-8"))
    original_checker = ptpn.check_todays_cards_extended
    try:
        ptpn.check_todays_cards_extended = lambda payload=saved_preflight: {
            "date": payload.get("date"),
            "checked_at": payload.get("checked_at"),
            "api_ok": payload.get("api_ok"),
            "has_targets": payload.get("has_targets"),
            "relevant_tracks": payload.get("relevant_tracks"),
            "shadow_tracks": payload.get("shadow_tracks"),
            "excluded_tracks": payload.get("excluded_tracks"),
            "total_cards": payload.get("total_cards"),
            "error": payload.get("error"),
        }
        rebuilt_preflight = ptpn.build_payload()
    finally:
        ptpn.check_todays_cards_extended = original_checker
    if preflight_text.read_text(encoding="utf-8") != str(rebuilt_preflight["note"]) + "\n":
        raise AssertionError(f"{case_name}: refreshed preflight_note.txt drifted from the current source-layer rebuild")
    if preflight_json.read_text(encoding="utf-8") != json.dumps(rebuilt_preflight, indent=2) + "\n":
        raise AssertionError(f"{case_name}: refreshed preflight_note.json drifted from the current source-layer rebuild")

    for lane in source_refresh.LANES:
        lane_dir = run_root / lane.name
        expected = expected_lane_components(run_root, lane)
        checks = {
            lane_dir / "forward_check.txt": expected["forward_check_txt"],
            lane_dir / "forward_check.md": expected["forward_check_md"],
            lane_dir / "lane_monitor.txt": expected["lane_monitor_txt"],
            lane_dir / "lane_monitor.md": expected["lane_monitor_md"],
            lane_dir / "next_steps.txt": expected["next_steps_txt"],
            lane_dir / "next_steps.md": expected["next_steps_md"],
            lane_dir / "summary.txt": expected["summary_txt"],
        }
        for path, expected_text in checks.items():
            actual = path.read_text(encoding="utf-8")
            if actual != expected_text:
                raise AssertionError(f"{case_name}: refreshed {path} drifted from the current source-layer rebuild")

    daily_args = SimpleNamespace(
        run_root=str(run_root),
        primary_lane=ptds.DEFAULT_PRIMARY_LANE,
        shadow_lane=ptds.DEFAULT_SHADOW_LANE,
        primary_label=ptds.DEFAULT_PRIMARY_LABEL,
        shadow_label=ptds.DEFAULT_SHADOW_LABEL,
        right_now=str(right_now_md),
        ops_history=str(ops_history_md),
        settlement_audit=str(settlement_audit_md),
        output=str(run_root / "daily_summary.txt"),
    )
    expected_daily = ptds.render_text(ptds.build_payload(daily_args))
    actual_daily = (run_root / "daily_summary.txt").read_text(encoding="utf-8")
    if actual_daily != expected_daily:
        raise AssertionError(f"{case_name}: refreshed daily_summary.txt drifted from the current source-layer rebuild")


def assert_top_level_matches_source_layer(
    runs_root: Path,
    ops_history_md: Path,
    ops_history_csv: Path,
    paper_trade_now_txt: Path,
    paper_trade_now_md: Path,
    paper_trade_now_json: Path,
    settlement_audit_md: Path,
    case_name: str,
    ops_limit: int = source_refresh.DEFAULT_OPS_LIMIT,
    as_of_date: str | None = None,
) -> None:
    rows = ptoh.collect_rows(runs_root, ops_limit)
    expected_md = ops_history_md.with_name("expected_ops_history.md")
    expected_csv = ops_history_csv.with_name("expected_ops_history.csv")
    ptoh.write_md(expected_md, rows, ops_limit)
    ptoh.write_csv(expected_csv, rows)
    try:
        if ops_history_md.read_text(encoding="utf-8") != expected_md.read_text(encoding="utf-8"):
            raise AssertionError(f"{case_name}: refreshed OPS_HISTORY markdown drifted from the current source-layer rebuild")
        if ops_history_csv.read_text(encoding="utf-8") != expected_csv.read_text(encoding="utf-8"):
            raise AssertionError(f"{case_name}: refreshed ops_history.csv drifted from the current source-layer rebuild")
    finally:
        expected_md.unlink(missing_ok=True)
        expected_csv.unlink(missing_ok=True)

    now_args = SimpleNamespace(
        run_root=None,
        runs_root=str(runs_root),
        ops_limit=ops_limit,
        min_settled=None,
        portfolio_review_settled=None,
        max_open=5,
        runner=str(ptnow.DEFAULT_RUNNER),
        paper_trades_dir=str(ptnow.DEFAULT_PAPER_TRADES_DIR),
        primary_rules=str(ptnow.DEFAULT_PRIMARY_RULES),
        shadow_rules=str(ptnow.DEFAULT_SHADOW_RULES),
        frozen_eval=str(ptnow.DEFAULT_FROZEN_EVAL),
        ops_history_md=str(ops_history_md),
        settlement_audit=str(settlement_audit_md),
        as_of_date=as_of_date,
        format="json",
        output=None,
    )
    now_payload = ptnow.build_payload(now_args)
    expected_txt = ptnow.render_text(now_payload)
    expected_md = ptnow.render_md(now_payload) + "\n"
    expected_json = json.dumps(now_payload, indent=2) + "\n"
    actual_now_txt = paper_trade_now_txt.read_text(encoding="utf-8")
    actual_now_md = paper_trade_now_md.read_text(encoding="utf-8")
    actual_now_json = paper_trade_now_json.read_text(encoding="utf-8")
    if actual_now_txt != expected_txt:
        raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.txt drifted from the current source-layer rebuild")
    if actual_now_md != expected_md:
        raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.md drifted from the current source-layer rebuild")
    if actual_now_json != expected_json:
        raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.json drifted from the current source-layer rebuild")
    payload_json = json.loads(actual_now_json)
    if not payload_json.get("settlement_audit") or not payload_json.get("shadow_settlement_audit_promotion_gate") or not payload_json.get("shadow_settlement_audit_rule_progress"):
        raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.json dropped settlement-audit pointer or shadow per-rule promotion-gate fields")
    focus_lane = now_payload[now_payload["best_action"]["lane_key"]]
    expected_text_quick_reads = [
        f"1. {focus_lane['summary_txt']}",
        f"2. {focus_lane['next_steps_md']}",
        f"3. {focus_lane['lane_monitor_md']}",
        f"4. {now_payload['daily_summary']}",
        f"5. {rel(ops_history_md)}",
    ]
    expected_md_quick_reads = [
        f"1. `{focus_lane['summary_txt']}`",
        f"2. `{focus_lane['next_steps_md']}`",
        f"3. `{focus_lane['lane_monitor_md']}`",
        f"4. `{now_payload['daily_summary']}`",
        f"5. `{rel(ops_history_md)}`",
    ]
    for snippet in expected_text_quick_reads:
        if snippet not in actual_now_txt:
            raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.txt dropped quick-read item {snippet!r}")
    for snippet in expected_md_quick_reads:
        if snippet not in actual_now_md:
            raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.md dropped quick-read item {snippet!r}")
    expected_text_audit = f"- Settlement audit: {now_payload['settlement_audit']}"
    expected_md_audit = f"- Settlement audit: `{now_payload['settlement_audit']}`"
    if expected_text_audit not in actual_now_txt:
        raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.txt dropped routed settlement-audit pointer {expected_text_audit!r}")
    if expected_md_audit not in actual_now_md:
        raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.md dropped routed settlement-audit pointer {expected_md_audit!r}")
    if now_payload.get("shadow_settlement_audit_promotion_gate"):
        expected_gate = f"- Shadow settlement-audit promotion gate: {now_payload['shadow_settlement_audit_promotion_gate']}"
        if expected_gate not in actual_now_txt or expected_gate not in actual_now_md:
            raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW surfaces dropped shadow settlement-audit promotion gate {expected_gate!r}")
    if now_payload.get("shadow_settlement_audit_rule_progress"):
        expected_progress = f"- Shadow per-rule promotion coverage: {now_payload['shadow_settlement_audit_rule_progress']}"
        if expected_progress not in actual_now_txt or expected_progress not in actual_now_md:
            raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW surfaces dropped shadow settlement-audit rule-progress line {expected_progress!r}")
    if now_payload["primary"].get("recent_run_context"):
        expected_text = f"- Primary lane context: {now_payload['primary']['recent_run_context']}"
        if expected_text not in actual_now_txt:
            raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.txt dropped the primary lane-context line {expected_text!r}")
        if expected_text not in actual_now_md:
            raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.md dropped the primary lane-context line {expected_text!r}")
    if now_payload["primary"].get("why"):
        expected_text = f"- Primary lane why now: {now_payload['primary']['why']}"
        if expected_text not in actual_now_txt:
            raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.txt dropped the primary lane-why line {expected_text!r}")
        if expected_text not in actual_now_md:
            raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.md dropped the primary lane-why line {expected_text!r}")
    if now_payload["shadow"].get("recent_run_context"):
        expected_text = f"- Shadow lane context: {now_payload['shadow']['recent_run_context']}"
        if expected_text not in actual_now_txt:
            raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.txt dropped the shadow lane-context line {expected_text!r}")
        if expected_text not in actual_now_md:
            raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.md dropped the shadow lane-context line {expected_text!r}")
    if now_payload["shadow"].get("why"):
        expected_text = f"- Shadow lane why now: {now_payload['shadow']['why']}"
        if expected_text not in actual_now_txt:
            raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.txt dropped the shadow lane-why line {expected_text!r}")
        if expected_text not in actual_now_md:
            raise AssertionError(f"{case_name}: refreshed PAPER_TRADE_NOW.md dropped the shadow lane-why line {expected_text!r}")



def assert_settlement_audit_refreshed(md_path: Path, json_path: Path, case_name: str) -> None:
    if not md_path.exists() or not json_path.exists():
        raise AssertionError(f"{case_name}: refresh did not write settlement audit md/json outputs")
    md_text = md_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if "Paper Trade Settlement Audit" not in md_text:
        raise AssertionError(f"{case_name}: settlement audit markdown did not render the audit title")
    if "not new forward evidence by itself" not in md_text:
        raise AssertionError(f"{case_name}: settlement audit markdown dropped the no-new-evidence boundary")
    if payload.get("artifact_status") != "pass":
        raise AssertionError(f"{case_name}: settlement audit JSON did not publish pass artifact_status")
    boundary = str(payload.get("summary", {}).get("evidence_boundary", ""))
    metadata = payload.get("evidence_boundary_metadata", {})
    if "not scanner evidence" not in boundary or not isinstance(metadata, dict) or metadata.get("not_new_forward_evidence_by_itself") is not True:
        raise AssertionError(f"{case_name}: settlement audit JSON dropped the evidence-boundary text")


def assert_current_evidence_refreshed(md_path: Path, json_path: Path, case_name: str) -> None:
    if not md_path.exists() or not json_path.exists():
        raise AssertionError(f"{case_name}: refresh did not write current evidence md/json outputs")
    md_text = md_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if "Current Evidence Summary" not in md_text:
        raise AssertionError(f"{case_name}: current evidence markdown did not render the bridge title")
    if "not forward-performance evidence" not in md_text:
        raise AssertionError(f"{case_name}: current evidence markdown dropped the no-forward-performance boundary")
    if payload.get("artifact") != "current_evidence_summary":
        raise AssertionError(f"{case_name}: current evidence JSON did not publish the current_evidence_summary artifact id")
    evidence_boundary = payload.get("evidence_boundary")
    if not isinstance(evidence_boundary, dict) or evidence_boundary.get("not_new_forward_evidence") is not True:
        raise AssertionError(f"{case_name}: current evidence JSON dropped not_new_forward_evidence=true")
    if evidence_boundary.get("not_real_money_evidence") is not True:
        raise AssertionError(f"{case_name}: current evidence JSON dropped not_real_money_evidence=true")
    contract = payload.get("rebuild_validation_contract")
    if not isinstance(contract, dict):
        raise AssertionError(f"{case_name}: current evidence JSON did not publish rebuild_validation_contract")
    upstream_order = contract.get("upstream_refresh_order")
    if not isinstance(upstream_order, list) or len(upstream_order) != 3:
        raise AssertionError(f"{case_name}: current evidence rebuild_validation_contract upstream_refresh_order shape drifted")
    commands = [step.get("command") for step in upstream_order if isinstance(step, dict)]
    orders = [step.get("order") for step in upstream_order if isinstance(step, dict)]
    if orders != [1, 2, 3] or commands != EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER:
        raise AssertionError(f"{case_name}: current evidence rebuild_validation_contract upstream order drifted")
    if contract.get("prerequisite_rebuild_command") != EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER[0]:
        raise AssertionError(f"{case_name}: current evidence rebuild_validation_contract prerequisite command drifted")
    if contract.get("rebuild_command") != EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER[1]:
        raise AssertionError(f"{case_name}: current evidence rebuild_validation_contract rebuild command drifted")
    if contract.get("direct_validation_command") != EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER[2]:
        raise AssertionError(f"{case_name}: current evidence rebuild_validation_contract validator command drifted")
    for flag in (
        "requires_settlement_audit_refresh_before_bridge_when_source_bytes_change",
        "requires_source_consistency_before_quoting_current_totals",
        "upstream_refresh_order_is_provenance_metadata_only",
        "not_settled_roi_or_real_money_evidence",
    ):
        if contract.get(flag) is not True:
            raise AssertionError(f"{case_name}: current evidence rebuild_validation_contract.{flag} must be true")


def assert_helper_stdout_reports_current_evidence_route(stdout: list[str], case_name: str) -> str:
    expected_prefix = (
        "Current-evidence rebuild route: "
        f"{source_refresh.CURRENT_EVIDENCE_REBUILD_CONTRACT_SOURCE}: "
        f"{' -> '.join(source_refresh.CURRENT_EVIDENCE_REBUILD_COMMANDS)}"
    )
    for line in stdout:
        if (
            line.startswith(expected_prefix)
            and "provenance/rebuild metadata only" in line
            and "not settled ROI" in line
            and "real-money evidence" in line
        ):
            return line
    raise AssertionError(
        f"{case_name}: helper stdout did not report the current-evidence rebuild route "
        "and non-evidence boundary"
    )


def helper_source_documents_current_evidence_rebuild_contract() -> bool:
    script_text = SCRIPT.read_text(encoding="utf-8")
    return (
        source_refresh.CURRENT_EVIDENCE_REBUILD_CONTRACT_SOURCE
        == "current_evidence_summary.json.rebuild_validation_contract"
        and list(source_refresh.CURRENT_EVIDENCE_REBUILD_COMMANDS) == EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER
        and source_refresh.CURRENT_EVIDENCE_REBUILD_CONTRACT_SOURCE in script_text
        and all(command in script_text for command in EXPECTED_CURRENT_EVIDENCE_REBUILD_ORDER)
        and "settlement audit -> current bridge -> bridge validator" in script_text
        and "provenance/rebuild metadata only" in script_text
        and "not settled ROI" in script_text
        and "real-money evidence" in script_text
    )


def case_full_refresh() -> dict[str, Any]:
    case_root = FIXTURE_ROOT / "case_full_refresh"
    runs_root, run_roots = copy_live_runs(case_root)
    ops_history_md = case_root / "OPS_HISTORY.md"
    ops_history_csv = case_root / "ops_history.csv"
    paper_trade_now_txt = case_root / "PAPER_TRADE_NOW.txt"
    paper_trade_now_md = case_root / "PAPER_TRADE_NOW.md"
    paper_trade_now_json = case_root / "PAPER_TRADE_NOW.json"
    settlement_audit_md = case_root / "out" / "paper_trade_settlement_audit.md"
    settlement_audit_json = case_root / "out" / "paper_trade_settlement_audit.json"
    current_evidence_md = case_root / "CURRENT_EVIDENCE_SUMMARY.md"
    current_evidence_json = case_root / "current_evidence_summary.json"

    write_text(run_roots[0] / "phase7_current_paper" / "summary.txt", "STALE primary summary\n")
    write_text(run_roots[-1] / "phase8_shadow" / "next_steps.md", "# STALE shadow next steps\n")
    write_text(run_roots[-1] / "daily_summary.txt", "STALE daily summary\n")
    write_text(ops_history_md, "# STALE OPS HISTORY\n")
    write_text(ops_history_csv, "date,stale\n")
    write_text(paper_trade_now_txt, "STALE right now\n")
    write_text(paper_trade_now_md, "# STALE right now\n")
    write_text(paper_trade_now_json, "{\"stale\": true}\n")
    write_text(current_evidence_md, "# STALE current evidence\n")
    write_text(current_evidence_json, "{\"stale\": true}\n")

    if len(run_roots) < 2:
        raise AssertionError("case_full_refresh needs at least two copied run folders to prove all relocated scanner anchor styles")
    lane_local_run = run_roots[0]
    run_root_relative_run = run_roots[0]
    project_relative_run = run_roots[-1]
    stale_default_run = run_roots[-1]
    project_relocated_scanner = case_root / "project_relative_scanners" / "phase7_project_relative_live_scan.status.json"
    relocated_sidecar_proofs = [
        relocate_scanner_for_anchor(
            lane_local_run,
            "phase7_current_paper",
            "lane-local",
            "renamed_live_scan_lane_local.status.json",
            lane_local_run / "phase7_current_paper" / "renamed_live_scan_lane_local.status.json",
            proof_card_count=13,
            proof_race_count=113,
        ),
        relocate_scanner_for_anchor(
            run_root_relative_run,
            "phase8_shadow",
            "run-root-relative",
            "phase8_shadow/renamed_live_scan_run_root.status.json",
            run_root_relative_run / "phase8_shadow" / "renamed_live_scan_run_root.status.json",
            proof_card_count=17,
            proof_race_count=117,
        ),
        relocate_scanner_for_anchor(
            project_relative_run,
            "phase7_current_paper",
            "project-relative",
            rel(project_relocated_scanner),
            project_relocated_scanner,
            proof_card_count=19,
            proof_race_count=119,
        ),
        relocate_scanner_for_anchor(
            stale_default_run,
            "phase8_shadow",
            "stale-default declared-sidecar precedence",
            "renamed_live_scan_stale_default.status.json",
            stale_default_run / "phase8_shadow" / "renamed_live_scan_stale_default.status.json",
            proof_card_count=23,
            proof_race_count=123,
            keep_default_stale=True,
            stale_default_card_count=7,
            stale_default_race_count=77,
        ),
    ]

    latest_run_date = ptnow.parse_iso_date(run_roots[-1].name)
    if latest_run_date is None:
        raise AssertionError(f"case_full_refresh: latest copied run folder is not an ISO date: {run_roots[-1].name}")
    as_of_date = latest_run_date.isoformat()

    result = run_helper([
        "--runs-root", str(runs_root),
        "--ops-history-md-output", str(ops_history_md),
        "--ops-history-csv-output", str(ops_history_csv),
        "--paper-trade-now-text-output", str(paper_trade_now_txt),
        "--paper-trade-now-md-output", str(paper_trade_now_md),
        "--paper-trade-now-json-output", str(paper_trade_now_json),
        "--settlement-audit-md-output", str(settlement_audit_md),
        "--settlement-audit-json-output", str(settlement_audit_json),
        "--current-evidence-md-output", str(current_evidence_md),
        "--current-evidence-json-output", str(current_evidence_json),
        "--as-of-date", as_of_date,
    ])
    stdout = result.stdout.splitlines()
    if not stdout or "including top-level settlement audit / OPS_HISTORY / PAPER_TRADE_NOW / CURRENT_EVIDENCE_SUMMARY outputs" not in stdout[0]:
        raise AssertionError("case_full_refresh: helper summary line did not describe the top-level refresh scope")
    if len(stdout) < 2 or "does not create new paper-trade outcomes or new forward evidence" not in stdout[1]:
        raise AssertionError("case_full_refresh: helper did not print the non-evidence note after refreshing saved surfaces")
    if len(stdout) < 3 or f"pinned to as-of date {as_of_date}" not in stdout[2]:
        raise AssertionError("case_full_refresh: helper did not print the explicit as-of-date pin note after refreshing top-level PAPER_TRADE_NOW")
    current_evidence_route_line = assert_helper_stdout_reports_current_evidence_route(stdout, "case_full_refresh")

    assert_settlement_audit_refreshed(settlement_audit_md, settlement_audit_json, "case_full_refresh")
    assert_current_evidence_refreshed(current_evidence_md, current_evidence_json, "case_full_refresh")
    assert_top_level_issue_flags_survive_refresh(
        paper_trade_now_txt=paper_trade_now_txt,
        paper_trade_now_md=paper_trade_now_md,
        paper_trade_now_json=paper_trade_now_json,
        current_evidence_json=current_evidence_json,
        case_name="case_full_refresh",
    )

    refreshed_right_now_md_text = paper_trade_now_md.read_text(encoding="utf-8")
    for run_root in run_roots:
        assert_run_root_matches_source_layer(
            run_root,
            "case_full_refresh",
            right_now_md=paper_trade_now_md,
            ops_history_md=ops_history_md,
            settlement_audit_md=settlement_audit_md,
        )
        daily_summary_text = (run_root / "daily_summary.txt").read_text(encoding="utf-8")
        if f"- Right now: {rel(paper_trade_now_md)}" not in daily_summary_text:
            raise AssertionError("case_full_refresh: rebuilt daily_summary.txt did not point at the routed PAPER_TRADE_NOW.md surface")
        if f"- Rolling ops history: {rel(ops_history_md)}" not in daily_summary_text:
            raise AssertionError("case_full_refresh: rebuilt daily_summary.txt did not point at the routed OPS_HISTORY.md surface")
        if f"- Settlement audit: {rel(settlement_audit_md)}" not in daily_summary_text:
            raise AssertionError("case_full_refresh: rebuilt daily_summary.txt did not point at the routed settlement-audit surface")
        assert_daily_summary_keeps_settlement_audit_actions(
            daily_summary_text,
            settlement_audit_md,
            case_name="case_full_refresh",
            label_prefix="rebuilt",
        )
        assert_daily_summary_keeps_next_step_source_artifacts(
            daily_summary_text,
            run_root,
            case_name="case_full_refresh",
            label_prefix="rebuilt",
        )
        if f"- Preflight note: {expected_preflight_jump_path(run_root)}" not in daily_summary_text:
            raise AssertionError("case_full_refresh: rebuilt daily_summary.txt did not keep the routed preflight-note quick jump chosen by the source-layer preflight resolver")
        if f"Artifacts root: {rel(run_root)}" not in daily_summary_text:
            raise AssertionError("case_full_refresh: rebuilt daily_summary.txt did not keep the routed artifacts-root pointer")
        if f"- Primary summary: {rel(run_root / 'phase7_current_paper' / 'summary.txt')}" not in daily_summary_text:
            raise AssertionError("case_full_refresh: rebuilt daily_summary.txt did not keep the routed primary summary quick jump")
        if f"- Primary next steps: {rel(run_root / 'phase7_current_paper' / 'next_steps.md')}" not in daily_summary_text:
            raise AssertionError("case_full_refresh: rebuilt daily_summary.txt did not keep the routed primary next-steps quick jump")
        if f"- Primary lane monitor: {rel(run_root / 'phase7_current_paper' / 'lane_monitor.md')}" not in daily_summary_text:
            raise AssertionError("case_full_refresh: rebuilt daily_summary.txt did not keep the routed primary lane-monitor quick jump")
        if f"- Primary forward check: {rel(run_root / 'phase7_current_paper' / 'forward_check.md')}" not in daily_summary_text:
            raise AssertionError("case_full_refresh: rebuilt daily_summary.txt did not keep the routed primary forward-check quick jump")
        if f"- Shadow summary: {rel(run_root / 'phase8_shadow' / 'summary.txt')}" not in daily_summary_text:
            raise AssertionError("case_full_refresh: rebuilt daily_summary.txt did not keep the routed shadow summary quick jump")
        if f"- Shadow next steps: {rel(run_root / 'phase8_shadow' / 'next_steps.md')}" not in daily_summary_text:
            raise AssertionError("case_full_refresh: rebuilt daily_summary.txt did not keep the routed shadow next-steps quick jump")
        if f"- Shadow lane monitor: {rel(run_root / 'phase8_shadow' / 'lane_monitor.md')}" not in daily_summary_text:
            raise AssertionError("case_full_refresh: rebuilt daily_summary.txt did not keep the routed shadow lane-monitor quick jump")
        if f"- Shadow forward check: {rel(run_root / 'phase8_shadow' / 'forward_check.md')}" not in daily_summary_text:
            raise AssertionError("case_full_refresh: rebuilt daily_summary.txt did not keep the routed shadow forward-check quick jump")
        assert_daily_summary_keeps_right_now_snapshot(
            daily_summary_text,
            refreshed_right_now_md_text,
            case_name="case_full_refresh",
            label_prefix="rebuilt",
        )
        assert_daily_summary_lifts_right_now_issue_flags(
            run_root / "daily_summary.txt",
            paper_trade_now_json,
            case_name="case_full_refresh",
            label_prefix="rebuilt",
        )
        primary_context = extract_recent_run_context_line(run_root / "phase7_current_paper" / "next_steps.txt")
        if primary_context is not None and f"- Primary lane context: {primary_context}" not in daily_summary_text:
            raise AssertionError("case_full_refresh: rebuilt daily_summary.txt did not keep the refreshed primary lane-context line")
        shadow_context = extract_recent_run_context_line(run_root / "phase8_shadow" / "next_steps.txt")
        if shadow_context is not None and f"- Shadow lane context: {shadow_context}" not in daily_summary_text:
            raise AssertionError("case_full_refresh: rebuilt daily_summary.txt did not keep the refreshed shadow lane-context line")
    assert_relocated_anchor_proofs(relocated_sidecar_proofs, "case_full_refresh")
    assert_top_level_matches_source_layer(
        runs_root,
        ops_history_md=ops_history_md,
        ops_history_csv=ops_history_csv,
        paper_trade_now_txt=paper_trade_now_txt,
        paper_trade_now_md=paper_trade_now_md,
        paper_trade_now_json=paper_trade_now_json,
        settlement_audit_md=settlement_audit_md,
        case_name="case_full_refresh",
        as_of_date=as_of_date,
    )

    return {
        "case": "case_full_refresh",
        "scenario": "full helper refresh rebuilds stale per-run and temp-routed top-level operator surfaces while proving lane-local, run-root-relative, project-relative, and stale-default relocated scanner sidecars",
        "run_count": len(run_roots),
        "as_of_date": as_of_date,
        "stdout_first_line": stdout[0] if stdout else "",
        "stdout_second_line": stdout[1] if len(stdout) > 1 else "",
        "stdout_third_line": stdout[2] if len(stdout) > 2 else "",
        "stdout_current_evidence_rebuild_route_line": current_evidence_route_line,
        "relocated_sidecar_proofs": relocated_sidecar_proofs,
        "sample_outputs": [
            rel(run_roots[0] / "phase7_current_paper" / "summary.txt"),
            rel(run_roots[-1] / "daily_summary.txt"),
            rel(ops_history_md),
            rel(paper_trade_now_md),
            rel(paper_trade_now_json),
            rel(settlement_audit_md),
            rel(current_evidence_md),
        ],
    }


def case_blank_preflight_text_refresh() -> dict[str, Any]:
    case_root = FIXTURE_ROOT / "case_blank_preflight_text_refresh"
    runs_root, run_roots = copy_live_runs(case_root)
    ops_history_md = case_root / "OPS_HISTORY.md"
    ops_history_csv = case_root / "ops_history.csv"
    paper_trade_now_txt = case_root / "PAPER_TRADE_NOW.txt"
    paper_trade_now_md = case_root / "PAPER_TRADE_NOW.md"
    paper_trade_now_json = case_root / "PAPER_TRADE_NOW.json"
    settlement_audit_md = case_root / "out" / "paper_trade_settlement_audit.md"
    settlement_audit_json = case_root / "out" / "paper_trade_settlement_audit.json"
    current_evidence_md = case_root / "CURRENT_EVIDENCE_SUMMARY.md"
    current_evidence_json = case_root / "current_evidence_summary.json"
    latest = run_roots[-1]

    write_text(latest / "preflight_note.txt", "\n")
    write_text(latest / "daily_summary.txt", "STALE daily summary\n")
    write_text(ops_history_md, "# STALE OPS HISTORY\n")
    write_text(ops_history_csv, "date,stale\n")
    write_text(paper_trade_now_txt, "STALE right now\n")
    write_text(paper_trade_now_md, "# STALE right now\n")
    write_text(paper_trade_now_json, "{\"stale\": true}\n")
    write_text(current_evidence_md, "# STALE current evidence\n")
    write_text(current_evidence_json, "{\"stale\": true}\n")

    latest_run_date = ptnow.parse_iso_date(latest.name)
    if latest_run_date is None:
        raise AssertionError(f"case_blank_preflight_text_refresh: latest copied run folder is not an ISO date: {latest.name}")
    as_of_date = latest_run_date.isoformat()

    result = run_helper([
        "--runs-root", str(runs_root),
        "--ops-history-md-output", str(ops_history_md),
        "--ops-history-csv-output", str(ops_history_csv),
        "--paper-trade-now-text-output", str(paper_trade_now_txt),
        "--paper-trade-now-md-output", str(paper_trade_now_md),
        "--paper-trade-now-json-output", str(paper_trade_now_json),
        "--settlement-audit-md-output", str(settlement_audit_md),
        "--settlement-audit-json-output", str(settlement_audit_json),
        "--current-evidence-md-output", str(current_evidence_md),
        "--current-evidence-json-output", str(current_evidence_json),
        "--as-of-date", as_of_date,
    ])
    stdout = result.stdout.splitlines()
    if not stdout or "including top-level settlement audit / OPS_HISTORY / PAPER_TRADE_NOW / CURRENT_EVIDENCE_SUMMARY outputs" not in stdout[0]:
        raise AssertionError("case_blank_preflight_text_refresh: helper summary line did not describe the top-level refresh scope")
    if len(stdout) < 2 or "does not create new paper-trade outcomes or new forward evidence" not in stdout[1]:
        raise AssertionError("case_blank_preflight_text_refresh: helper did not print the non-evidence note after refreshing saved surfaces")
    if len(stdout) < 3 or f"pinned to as-of date {as_of_date}" not in stdout[2]:
        raise AssertionError("case_blank_preflight_text_refresh: helper did not print the explicit as-of-date pin note after refreshing top-level PAPER_TRADE_NOW")
    current_evidence_route_line = assert_helper_stdout_reports_current_evidence_route(
        stdout,
        "case_blank_preflight_text_refresh",
    )

    rebuilt_preflight_text = (latest / "preflight_note.txt").read_text(encoding="utf-8")
    if not rebuilt_preflight_text.strip():
        raise AssertionError("case_blank_preflight_text_refresh: refresh left preflight_note.txt blank instead of rebuilding it from the saved JSON snapshot")

    assert_settlement_audit_refreshed(settlement_audit_md, settlement_audit_json, "case_blank_preflight_text_refresh")
    assert_current_evidence_refreshed(current_evidence_md, current_evidence_json, "case_blank_preflight_text_refresh")
    assert_top_level_issue_flags_survive_refresh(
        paper_trade_now_txt=paper_trade_now_txt,
        paper_trade_now_md=paper_trade_now_md,
        paper_trade_now_json=paper_trade_now_json,
        current_evidence_json=current_evidence_json,
        case_name="case_blank_preflight_text_refresh",
    )
    assert_run_root_matches_source_layer(
        latest,
        "case_blank_preflight_text_refresh",
        right_now_md=paper_trade_now_md,
        ops_history_md=ops_history_md,
        settlement_audit_md=settlement_audit_md,
    )
    assert_top_level_matches_source_layer(
        runs_root,
        ops_history_md=ops_history_md,
        ops_history_csv=ops_history_csv,
        paper_trade_now_txt=paper_trade_now_txt,
        paper_trade_now_md=paper_trade_now_md,
        paper_trade_now_json=paper_trade_now_json,
        settlement_audit_md=settlement_audit_md,
        case_name="case_blank_preflight_text_refresh",
        as_of_date=as_of_date,
    )

    latest_daily_summary = (latest / "daily_summary.txt").read_text(encoding="utf-8")
    assert_daily_summary_lifts_right_now_issue_flags(
        latest / "daily_summary.txt",
        paper_trade_now_json,
        case_name="case_blank_preflight_text_refresh",
        label_prefix="rebuilt",
    )
    assert_daily_summary_keeps_settlement_audit_actions(
        latest_daily_summary,
        settlement_audit_md,
        case_name="case_blank_preflight_text_refresh",
        label_prefix="rebuilt",
    )
    assert_daily_summary_keeps_next_step_source_artifacts(
        latest_daily_summary,
        latest,
        case_name="case_blank_preflight_text_refresh",
        label_prefix="rebuilt",
    )
    expected_preflight_path = rel(latest / "preflight_note.txt")
    if f"- Preflight note: {expected_preflight_path}" not in latest_daily_summary:
        raise AssertionError("case_blank_preflight_text_refresh: rebuilt daily_summary.txt did not switch back to the rebuilt preflight_note.txt quick jump after refresh repaired the blank text note")
    if f"- Preflight note: {rel(latest / 'preflight_note.json')}" in latest_daily_summary:
        raise AssertionError("case_blank_preflight_text_refresh: rebuilt daily_summary.txt still pointed at preflight_note.json even after refresh rebuilt a non-blank preflight_note.txt")

    return {
        "case": "case_blank_preflight_text_refresh",
        "scenario": "full refresh repairs a blank copied preflight_note.txt from the saved JSON snapshot before rebuilding routed top-level surfaces",
        "run": latest.name,
        "stdout_first_line": stdout[0] if stdout else "",
        "stdout_second_line": stdout[1] if len(stdout) > 1 else "",
        "stdout_third_line": stdout[2] if len(stdout) > 2 else "",
        "stdout_current_evidence_rebuild_route_line": current_evidence_route_line,
        "sample_outputs": [
            rel(latest / "preflight_note.txt"),
            rel(latest / "daily_summary.txt"),
            rel(paper_trade_now_md),
            rel(paper_trade_now_json),
            rel(settlement_audit_md),
            rel(current_evidence_md),
        ],
    }


def case_missing_scan_output_refresh() -> dict[str, Any]:
    case_root = FIXTURE_ROOT / "case_missing_scan_output_refresh"
    runs_root, run_roots = copy_live_runs(case_root)
    latest = run_roots[-1]
    lane_name = "phase7_current_paper"
    lane_dir = latest / lane_name

    force_missing_scan_output_state(lane_dir)
    write_text(lane_dir / "summary.txt", "STALE primary summary SHOULD REFRESH\n")
    write_text(lane_dir / "next_steps.txt", "STALE primary next steps SHOULD REFRESH\n")
    write_text(lane_dir / "next_steps.md", "# STALE primary next steps SHOULD REFRESH\n")
    write_text(latest / "daily_summary.txt", "STALE daily summary SHOULD REFRESH\n")

    result = run_helper([
        "--runs-root", str(runs_root),
        "--latest-only",
        "--skip-top-level",
    ])
    stdout = result.stdout.splitlines()
    if not stdout or "per-run preflight, lane, and daily-summary surfaces only; top-level outputs skipped" not in stdout[0]:
        raise AssertionError("case_missing_scan_output_refresh: helper summary line did not describe the skip-top-level scope")
    if len(stdout) < 2 or "does not create new paper-trade outcomes or new forward evidence" not in stdout[1]:
        raise AssertionError("case_missing_scan_output_refresh: helper did not print the non-evidence note after refreshing saved surfaces")

    assert_run_root_matches_source_layer(
        latest,
        "case_missing_scan_output_refresh",
        right_now_md=ptds.DEFAULT_RIGHT_NOW,
        ops_history_md=ptds.DEFAULT_OPS_HISTORY,
        settlement_audit_md=ptds.DEFAULT_SETTLEMENT_AUDIT,
    )
    assert_missing_scan_output_survives_refresh(
        latest,
        lane_name,
        "case_missing_scan_output_refresh",
    )

    return {
        "case": "case_missing_scan_output_refresh",
        "scenario": "latest-only refresh preserves a readable scanner-status sidecar with a missing scan-output artifact as latest-run context across next-steps, lane summary, and daily summary surfaces even when settlement-first action priority still wins",
        "latest_run": latest.name,
        "lane": lane_name,
        "stdout_first_line": stdout[0] if stdout else "",
        "stdout_second_line": stdout[1] if len(stdout) > 1 else "",
        "sample_outputs": [
            rel(lane_dir / "summary.txt"),
            rel(lane_dir / "next_steps.txt"),
            rel(lane_dir / "next_steps.md"),
            rel(latest / "daily_summary.txt"),
        ],
    }


def case_pipeline_recorded_invalid_shape_refresh() -> dict[str, Any]:
    case_root = FIXTURE_ROOT / "case_pipeline_recorded_invalid_shape_refresh"
    runs_root, run_roots = copy_live_runs(case_root)
    latest = run_roots[-1]
    lane_name = "phase8_shadow"
    lane_dir = latest / lane_name

    force_pipeline_recorded_invalid_shape_scanner_missing(lane_dir)
    write_text(lane_dir / "summary.txt", "STALE shadow summary SHOULD REFRESH\n")
    write_text(lane_dir / "next_steps.txt", "STALE shadow next steps SHOULD REFRESH\n")
    write_text(lane_dir / "next_steps.md", "# STALE shadow next steps SHOULD REFRESH\n")
    write_text(latest / "daily_summary.txt", "STALE daily summary SHOULD REFRESH\n")

    result = run_helper([
        "--runs-root", str(runs_root),
        "--latest-only",
        "--skip-top-level",
    ])
    stdout = result.stdout.splitlines()
    if not stdout or "per-run preflight, lane, and daily-summary surfaces only; top-level outputs skipped" not in stdout[0]:
        raise AssertionError("case_pipeline_recorded_invalid_shape_refresh: helper summary line did not describe the skip-top-level scope")
    if len(stdout) < 2 or "does not create new paper-trade outcomes or new forward evidence" not in stdout[1]:
        raise AssertionError("case_pipeline_recorded_invalid_shape_refresh: helper did not print the non-evidence note after refreshing saved surfaces")

    assert_run_root_matches_source_layer(
        latest,
        "case_pipeline_recorded_invalid_shape_refresh",
        right_now_md=ptds.DEFAULT_RIGHT_NOW,
        ops_history_md=ptds.DEFAULT_OPS_HISTORY,
        settlement_audit_md=ptds.DEFAULT_SETTLEMENT_AUDIT,
    )
    assert_pipeline_recorded_invalid_shape_survives_refresh(
        latest,
        lane_name,
        "case_pipeline_recorded_invalid_shape_refresh",
    )

    return {
        "case": "case_pipeline_recorded_invalid_shape_refresh",
        "scenario": "latest-only refresh preserves a pipeline-recorded invalid-shape scanner-status caution when the copied shadow lane no longer has live_scan.status.json, even when settlement-first routing remains the top action",
        "latest_run": latest.name,
        "lane": lane_name,
        "stdout_first_line": stdout[0] if stdout else "",
        "stdout_second_line": stdout[1] if len(stdout) > 1 else "",
        "sample_outputs": [
            rel(lane_dir / "summary.txt"),
            rel(lane_dir / "next_steps.txt"),
            rel(lane_dir / "next_steps.md"),
            rel(latest / "daily_summary.txt"),
        ],
    }


def case_latest_only_refresh() -> dict[str, Any]:
    case_root = FIXTURE_ROOT / "case_latest_only_refresh"
    runs_root, run_roots = copy_live_runs(case_root)
    if len(run_roots) < 2:
        raise AssertionError("latest-only refresh case needs at least two run folders to verify scoping")
    older = run_roots[0]
    latest = run_roots[-1]

    write_text(older / "phase7_current_paper" / "summary.txt", "OLDER STALE SHOULD REMAIN\n")
    write_text(older / "daily_summary.txt", "OLDER DAILY SHOULD REMAIN\n")
    write_text(older / "preflight_note.txt", "OLDER PREFLIGHT SHOULD REMAIN\n")
    write_text(latest / "phase7_current_paper" / "summary.txt", "LATEST STALE SHOULD REFRESH\n")
    write_text(latest / "daily_summary.txt", "LATEST DAILY SHOULD REFRESH\n")
    write_text(latest / "preflight_note.txt", "\n")
    existing_right_now_md, existing_right_now_json = write_existing_right_now_with_issue_flags(
        case_root,
        {
            "has_api_access_failure_context": True,
            "has_scanner_failure_boundary": True,
            "has_stale_cache_fallback_context": True,
        },
    )

    result = run_helper([
        "--runs-root", str(runs_root),
        "--latest-only",
        "--skip-top-level",
        "--paper-trade-now-md-output", str(existing_right_now_md),
        "--paper-trade-now-json-output", str(existing_right_now_json),
        "--as-of-date", latest.name,
    ])
    stdout = result.stdout.splitlines()
    if not stdout or "per-run preflight, lane, and daily-summary surfaces only; top-level outputs skipped" not in stdout[0]:
        raise AssertionError("case_latest_only_refresh: helper summary line did not describe the skip-top-level scope")
    if len(stdout) < 2 or "does not create new paper-trade outcomes or new forward evidence" not in stdout[1]:
        raise AssertionError("case_latest_only_refresh: helper did not print the non-evidence note after refreshing saved surfaces")
    if len(stdout) < 3 or f"--as-of-date {latest.name} was ignored because top-level PAPER_TRADE_NOW refresh was skipped" not in stdout[2]:
        raise AssertionError("case_latest_only_refresh: helper did not say that --as-of-date was ignored when top-level refresh was skipped")

    assert_run_root_matches_source_layer(
        latest,
        "case_latest_only_refresh",
        right_now_md=existing_right_now_md,
        ops_history_md=ptds.DEFAULT_OPS_HISTORY,
        settlement_audit_md=ptds.DEFAULT_SETTLEMENT_AUDIT,
    )
    latest_daily_summary = (latest / "daily_summary.txt").read_text(encoding="utf-8")
    refreshed_right_now_md_text = existing_right_now_md.read_text(encoding="utf-8")
    if f"- Right now: {rel(existing_right_now_md)}" not in latest_daily_summary:
        raise AssertionError("case_latest_only_refresh: latest daily_summary.txt did not point at the preserved existing PAPER_TRADE_NOW.md surface after refresh")
    assert_daily_summary_lifts_right_now_issue_flags(
        latest / "daily_summary.txt",
        existing_right_now_json,
        case_name="case_latest_only_refresh",
        label_prefix="latest",
    )
    if f"- Rolling ops history: {rel(ptds.DEFAULT_OPS_HISTORY)}" not in latest_daily_summary:
        raise AssertionError("case_latest_only_refresh: latest daily_summary.txt did not point at the default OPS_HISTORY.md surface after refresh")
    if f"- Settlement audit: {rel(ptds.DEFAULT_SETTLEMENT_AUDIT)}" not in latest_daily_summary:
        raise AssertionError("case_latest_only_refresh: latest daily_summary.txt did not point at the default settlement-audit surface after refresh")
    assert_daily_summary_keeps_settlement_audit_actions(
        latest_daily_summary,
        ptds.DEFAULT_SETTLEMENT_AUDIT,
        case_name="case_latest_only_refresh",
        label_prefix="latest",
    )
    assert_daily_summary_keeps_next_step_source_artifacts(
        latest_daily_summary,
        latest,
        case_name="case_latest_only_refresh",
        label_prefix="latest",
    )
    if f"- Preflight note: {expected_preflight_jump_path(latest)}" not in latest_daily_summary:
        raise AssertionError("case_latest_only_refresh: latest daily_summary.txt did not keep the refreshed preflight-note quick jump chosen by the source-layer preflight resolver")
    if f"Artifacts root: {rel(latest)}" not in latest_daily_summary:
        raise AssertionError("case_latest_only_refresh: latest daily_summary.txt did not keep the refreshed artifacts-root pointer")
    if f"- Primary summary: {rel(latest / 'phase7_current_paper' / 'summary.txt')}" not in latest_daily_summary:
        raise AssertionError("case_latest_only_refresh: latest daily_summary.txt did not keep the refreshed primary summary quick jump")
    if f"- Primary next steps: {rel(latest / 'phase7_current_paper' / 'next_steps.md')}" not in latest_daily_summary:
        raise AssertionError("case_latest_only_refresh: latest daily_summary.txt did not keep the refreshed primary next-steps quick jump")
    if f"- Primary lane monitor: {rel(latest / 'phase7_current_paper' / 'lane_monitor.md')}" not in latest_daily_summary:
        raise AssertionError("case_latest_only_refresh: latest daily_summary.txt did not keep the refreshed primary lane-monitor quick jump")
    if f"- Primary forward check: {rel(latest / 'phase7_current_paper' / 'forward_check.md')}" not in latest_daily_summary:
        raise AssertionError("case_latest_only_refresh: latest daily_summary.txt did not keep the refreshed primary forward-check quick jump")
    if f"- Shadow summary: {rel(latest / 'phase8_shadow' / 'summary.txt')}" not in latest_daily_summary:
        raise AssertionError("case_latest_only_refresh: latest daily_summary.txt did not keep the refreshed shadow summary quick jump")
    if f"- Shadow next steps: {rel(latest / 'phase8_shadow' / 'next_steps.md')}" not in latest_daily_summary:
        raise AssertionError("case_latest_only_refresh: latest daily_summary.txt did not keep the refreshed shadow next-steps quick jump")
    if f"- Shadow lane monitor: {rel(latest / 'phase8_shadow' / 'lane_monitor.md')}" not in latest_daily_summary:
        raise AssertionError("case_latest_only_refresh: latest daily_summary.txt did not keep the refreshed shadow lane-monitor quick jump")
    if f"- Shadow forward check: {rel(latest / 'phase8_shadow' / 'forward_check.md')}" not in latest_daily_summary:
        raise AssertionError("case_latest_only_refresh: latest daily_summary.txt did not keep the refreshed shadow forward-check quick jump")
    assert_daily_summary_keeps_right_now_snapshot(
        latest_daily_summary,
        refreshed_right_now_md_text,
        case_name="case_latest_only_refresh",
        label_prefix="latest",
    )
    primary_context = extract_recent_run_context_line(latest / "phase7_current_paper" / "next_steps.txt")
    if primary_context is not None and f"- Primary lane context: {primary_context}" not in latest_daily_summary:
        raise AssertionError("case_latest_only_refresh: latest daily_summary.txt did not keep the refreshed primary lane-context line")
    shadow_context = extract_recent_run_context_line(latest / "phase8_shadow" / "next_steps.txt")
    if shadow_context is not None and f"- Shadow lane context: {shadow_context}" not in latest_daily_summary:
        raise AssertionError("case_latest_only_refresh: latest daily_summary.txt did not keep the refreshed shadow lane-context line")
    rebuilt_latest_preflight = (latest / "preflight_note.txt").read_text(encoding="utf-8")
    if not rebuilt_latest_preflight.strip():
        raise AssertionError("case_latest_only_refresh: latest preflight_note.txt stayed blank even though --latest-only should still rebuild the newest run's preflight surface")
    older_text = (older / "phase7_current_paper" / "summary.txt").read_text(encoding="utf-8")
    if older_text != "OLDER STALE SHOULD REMAIN\n":
        raise AssertionError("case_latest_only_refresh: older run changed even though --latest-only should have scoped the refresh to the newest run")
    older_daily_summary = (older / "daily_summary.txt").read_text(encoding="utf-8")
    if older_daily_summary != "OLDER DAILY SHOULD REMAIN\n":
        raise AssertionError("case_latest_only_refresh: older daily_summary.txt changed even though --latest-only should have left the older run untouched")
    older_preflight = (older / "preflight_note.txt").read_text(encoding="utf-8")
    if older_preflight != "OLDER PREFLIGHT SHOULD REMAIN\n":
        raise AssertionError("case_latest_only_refresh: older preflight_note.txt changed even though --latest-only should have left older run preflight surfaces untouched")

    return {
        "case": "case_latest_only_refresh",
        "scenario": "--latest-only refreshes only the newest copied run's preflight, lane, and daily-summary surfaces when top-level refresh is skipped",
        "latest_run": latest.name,
        "older_run": older.name,
        "stdout_first_line": stdout[0] if stdout else "",
        "stdout_second_line": stdout[1] if len(stdout) > 1 else "",
        "stdout_third_line": stdout[2] if len(stdout) > 2 else "",
        "existing_right_now_issue_flags": "has_api_access_failure_context=true; has_scanner_failure_boundary=true; has_stale_cache_fallback_context=true",
        "older_summary": rel(older / "phase7_current_paper" / "summary.txt"),
        "latest_summary": rel(latest / "phase7_current_paper" / "summary.txt"),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_output_paths(args.fixture_root.expanduser().resolve(), args.out_dir.expanduser().resolve())
    scorecard_json = args.scorecard_json.expanduser().resolve()
    current_evidence_json = args.current_evidence_json.expanduser().resolve()
    scorecard_gates = read_scorecard_gate_minimums(scorecard_json)
    current_evidence_rebuild_contract = read_current_evidence_rebuild_contract(current_evidence_json)
    scorecard_artifact_guardrails = scorecard_no_artifact_guardrails(scorecard_json)
    current_evidence_artifact_guardrails = current_evidence_no_artifact_guardrails(
        scorecard_json,
        current_evidence_json,
    )

    live_run_roots()
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scratch = build_fixture_scratch_metadata()

    results = [
        case_full_refresh(),
        case_blank_preflight_text_refresh(),
        case_missing_scan_output_refresh(),
        case_pipeline_recorded_invalid_shape_refresh(),
        case_latest_only_refresh(),
    ]

    checks = scorecard_artifact_guardrails + current_evidence_artifact_guardrails + [
        {
            "check": "full_refresh_rebuilds_saved_live_surfaces",
            "status": "pass",
            "detail": "full refresh still rebuilds stale per-run operator surfaces plus the temp-routed settlement-audit, OPS_HISTORY, and PAPER_TRADE_NOW top-level surfaces from the current source-layer generators, now also proving lane-local, run-root-relative, project-relative, and stale-default pipeline-declared relocated scanner sidecars with distinct card/race-count context instead of assuming live_scan.status.json is absent or current",
        },
        {
            "check": "preflight_note_surfaces_refresh_from_saved_snapshot",
            "status": "pass",
            "detail": "full refresh now also rebuilds saved preflight_note.txt / preflight_note.json from each run's saved calendar snapshot, including repairing a blank copied preflight_note.txt from the surviving JSON snapshot, so source-layer schema changes do not leave the live preflight surfaces stale",
        },
        {
            "check": "missing_scan_output_survives_saved_live_refresh",
            "status": "pass",
            "detail": "latest-only refresh now directly proves a copied lane with a readable scanner-status sidecar but missing scan-output artifact is rebuilt with explicit latest-run context in next-steps, lane summary, and combined daily summary surfaces instead of being flattened into clean-empty context, even when settlement-first action priority still wins",
        },
        {
            "check": "pipeline_recorded_invalid_shape_survives_saved_live_refresh",
            "status": "pass",
            "detail": "latest-only refresh now directly proves a copied lane with pipeline-recorded invalid_shape scanner-status state and no physical live_scan.status.json is rebuilt with explicit operational artifact-caution wording in the lane summary, next-steps surfaces, and combined daily summary instead of being flattened into clean-empty or generic missing-sidecar context, even when settlement-first routing remains the top action",
        },
        {
            "check": "daily_summary_keeps_routed_quick_jump_bundle",
            "status": "pass",
            "detail": "rebuilt daily summaries still keep the routed PAPER_TRADE_NOW / OPS_HISTORY / settlement-audit / preflight / artifacts-root pointers, the settlement-audit next-action/no-new-evidence lines lifted from the routed audit JSON, the routed right-now focus/timing/freshness/stale-snapshot/ops snapshot, the full primary and shadow quick-jump bundle, and explicit per-lane recent-run context lines when the saved next-step artifacts have them",
        },
        {
            "check": "daily_summary_next_step_source_artifacts_stay_explicit",
            "status": "pass",
            "detail": "rebuilt daily summaries now have their own structured refresh-helper guardrail proving Primary/Shadow next-step source artifact lines survive full refresh, blank-preflight repair, and latest-only refresh paths using the same missing-or-blank text mirror resolver as the source-layer daily summary",
        },
        {
            "check": "daily_summary_lifts_operator_read_gate_issue_flags_through_saved_live_refresh",
            "status": "pass",
            "detail": "rebuilt daily summaries now have their own structured refresh-helper guardrail proving the routed PAPER_TRADE_NOW.json operator_read_gate issue flags survive full refresh, blank-preflight repair, and skip-top-level latest-only refresh paths, including a preserved existing top-card fixture where API-access, scanner-boundary, and stale-cache fallback flags are all true",
        },
        {
            "check": "paper_trade_now_keeps_routed_navigation_bundle",
            "status": "pass",
            "detail": "refreshed PAPER_TRADE_NOW text and markdown still keep the full routed recommendation-lane navigation bundle plus the routed top-level reads, including the settlement-audit pointer and shadow per-rule promotion-gate coverage",
        },
        {
            "check": "paper_trade_now_keeps_lane_context_and_why_lines",
            "status": "pass",
            "detail": "refreshed PAPER_TRADE_NOW text and markdown still keep explicit primary/shadow lane-context lines plus the lifted per-lane `why now` lines when the saved lane artifacts have them",
        },
        {
            "check": "current_evidence_bridge_refreshes_with_rebuild_contract",
            "status": "pass",
            "detail": "full top-level refresh now rebuilds temp-routed CURRENT_EVIDENCE_SUMMARY markdown/JSON from the just-refreshed PAPER_TRADE_NOW.json and settlement-audit JSON, while preserving the settlement-audit -> current bridge -> current bridge validator rebuild contract and non-evidence flags",
        },
        {
            "check": "refresh_helper_source_documents_current_evidence_rebuild_contract",
            "status": "pass",
            "detail": "refresh_live_paper_trade_surfaces.py now names current_evidence_summary.json.rebuild_validation_contract, exposes the settlement-audit -> current-bridge -> bridge-validator command order as source constants, and prints the route during full top-level refreshes as provenance metadata only rather than settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence",
        },
        {
            "check": "as_of_date_pins_top_level_freshness_for_reproducible_refreshes",
            "status": "pass",
            "detail": "the full refresh case now proves that an explicit --as-of-date pins the rebuilt PAPER_TRADE_NOW freshness read to a chosen calendar date instead of the validator machine clock",
        },
        {
            "check": "latest_only_refresh_stays_confined_to_newest_preflight_lane_daily_surfaces",
            "status": "pass",
            "detail": "--latest-only still refreshes only the newest copied run's preflight, lane, and daily-summary surfaces instead of silently broadening to older runs or top-level outputs",
        },
        {
            "check": "helper_stdout_says_refresh_is_not_new_evidence",
            "status": "pass",
            "detail": "the helper now prints an explicit note that it re-renders saved operator surfaces from existing artifacts and does not create new paper-trade outcomes or new forward evidence",
        },
        {
            "check": "helper_stdout_reports_as_of_date_usage_honestly",
            "status": "pass",
            "detail": "the helper stdout now says whether --as-of-date pinned rebuilt PAPER_TRADE_NOW freshness or was ignored because top-level outputs were skipped",
        },
        {
            "check": "refresh_helper_preserves_scorecard_gate_boundary",
            "status": "pass",
            "detail": "the refresh-helper validator now validates malformed and non-positive scorecard gates before fixture/report artifacts and publishes the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite while saying saved-live rebuilds, stale-surface refreshes, copied-run fixtures, and top-card rerenders do not count toward those gates",
        },
        {
            "check": "direct_validation_report_exposes_refresh_helper_valid_scope",
            "status": "pass",
            "detail": f"the refresh-helper validation markdown and JSON now expose exact valid_evidence_scope={VALID_EVIDENCE_SCOPE} as saved-live rebuild metadata only, without treating rerenders, copied-run fixtures, top-card freshness, or green wrapper checks as scanner evidence, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money support",
        },
        {
            "check": "fixture_scratch_metadata_published",
            "status": "pass",
            "detail": "the refresh-helper validator now publishes project-local fixture scratch metadata so parent rollups can verify copied-run fixture hygiene without parsing markdown prose",
        },
    ]
    if (
        scratch.get("fixture_root_relative") != "out/status_validation/refresh_live_paper_trade_surfaces_fixture"
        or scratch.get("fixture_root_is_project_local") is not True
        or scratch.get("case_roots_cleared_by_copy_live_runs") is not True
    ):
        raise AssertionError("refresh-helper fixture scratch metadata is no longer project-local or case-cleared")
    if (
        scorecard_gates.get("source") != "forward_evidence_scorecard.json"
        or scorecard_gates.get("source_path") != "decision_gate_minimums"
        or scorecard_gates.get("anchor_displacement_min_roi_complete_settled_observations") != 30
        or scorecard_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") != 20
        or scorecard_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") != 100
        or scorecard_gates.get("real_money_no_baq_as_bel_required") is not True
        or "no BAQ-as-BEL substitution" not in scorecard_gates.get("real_money_also_requires", [])
    ):
        raise AssertionError("refresh-helper scorecard gate boundary no longer matches forward_evidence_scorecard.json")
    if not helper_source_documents_current_evidence_rebuild_contract():
        raise AssertionError("refresh helper source no longer documents the current-evidence rebuild contract")

    payload = {
        "suite_status": "pass",
        "total_fixture_scenarios": len(results),
        "scenario_count": len(results),
        "results": results,
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "child_check_count": len(checks),
        "child_checks": checks,
        "summary": {
            "suite_read": f"refresh helper still rebuilds stale saved per-run summaries plus temp-routed settlement-audit / OPS_HISTORY / PAPER_TRADE_NOW / CURRENT_EVIDENCE_SUMMARY surfaces from the current generators, now also rebuilding saved preflight-note text/JSON surfaces from each run's saved calendar snapshot and directly repairing a blank copied preflight_note.txt from the surviving JSON snapshot, directly proving missing scan-output artifacts survive saved-live refresh when the scanner-status sidecar is readable, directly proving pipeline-recorded invalid_shape scanner-status states survive saved-live refresh when the copied lane no longer has live_scan.status.json, while proving lane-local, run-root-relative, project-relative, and stale-default pipeline-declared relocated scanner sidecars with distinct card/race-count context when a copied lane either no longer keeps live_scan.status.json at the default path or still has an older default scanner filename beside the declared sidecar, keeps rebuilt daily summaries inheriting refreshed top-level routed top-card snapshot lines while preserving the routed settlement-audit/preflight/artifacts pointers, settlement-audit next-action/no-new-evidence lines lifted from the routed audit JSON, the routed right-now focus/timing/freshness/stale-snapshot/ops snapshot, the full per-lane quick-jump bundle, explicit primary/shadow next-step source artifact lines, routed operator_read_gate issue flags, and explicit primary/shadow recent-run context lines, keeps refreshed PAPER_TRADE_NOW quick reads pinned to the full routed recommendation-lane navigation bundle plus the routed top-level reads, including the settlement-audit pointer and shadow per-rule promotion-gate coverage, explicit primary/shadow lane-context plus lane-why lines, and top-card issue flags matched into the current-evidence bridge, rebuilds temp-routed current-evidence markdown/JSON from the refreshed right-now JSON and settlement audit JSON while preserving the settlement-audit -> current bridge -> current bridge validator rebuild contract and non-evidence flags, source-documents that route through current_evidence_summary.json.rebuild_validation_contract constants and stdout, validates malformed current-evidence rebuild contracts before fixture/report artifacts, keeps --latest-only confined to the newest copied run's preflight, lane, and daily-summary surfaces instead of broadening silently while preserving existing top-card operator_read_gate issue flags under --skip-top-level, now says explicitly in its own stdout both that a refresh rebuilds saved operator surfaces from existing artifacts rather than creating new forward evidence and whether --as-of-date was actually applied to top-level PAPER_TRADE_NOW freshness, publishes project-local fixture scratch metadata for copied-run fixture hygiene, validates malformed and non-positive scorecard gates before fixture/report artifacts and publishes the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite as refresh-helper boundary metadata only, publishes the bridge-owned current_evidence_summary.json rebuild_validation_contract read as refresh-helper boundary metadata only, exposes exact valid_evidence_scope={VALID_EVIDENCE_SCOPE} in the direct validator report and evidence boundary as saved-live rebuild metadata only, and now says plainly that this is one of the two leaf source-of-truth wrapper reports whose inherited wrapper-guardrail inventory broader operator/project sweeps should preserve rather than flatten",
        },
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "current_evidence_rebuild_validation_contract_read": current_evidence_rebuild_contract,
        "scratch": scratch,
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
        },
    }

    lines = [
        "# Refresh Live Paper-Trade Surfaces Validation",
        "",
        "This report validates the saved-live refresh helper directly instead of only relying on downstream stale-surface failures.",
        "",
        f"- Scenarios: {len(results)}",
        f"- Rollup checks: {len(checks)}",
        "- Overall result: PASS",
        "",
        "## Current Read",
        "",
        f"- Suite read: {payload['summary']['suite_read']}",
        "",
        "## Scenario Results",
        "",
        "| Case | Scenario | Key Read |",
        "|---|---|---|",
    ]
    for row in results:
        key_read = row.get("stdout_first_line") or row.get("latest_run") or "pass"
        second = row.get("stdout_second_line")
        if second:
            key_read = f"{key_read} / {second}"
        lines.append(f"| {row['case']} | {row['scenario']} | {key_read} |")

    lines.extend([
        "",
        "## Rollup Checks",
        "",
    ])
    for check in checks:
        lines.append(f"- PASS `{check['check']}` — {check['detail']}")

    lines.extend([
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
        f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
        f"- valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
        "- Boundary: refresh-helper validation is saved-surface rebuild metadata only, not new forward evidence, not a current-day scanner result, not a live paper-trade ledger, not settled ROI, not live profitability, not promotion readiness, and not real-money evidence.",
        "",
        "## Decision-Gate Source",
        "",
        f"- Source: `{scorecard_gates['source']}` `{scorecard_gates['source_path']}`.",
        f"- Anchor displacement: `{scorecard_gates['anchor_displacement_min_roi_complete_settled_observations']}` ROI-complete same-candidate paper observations.",
        f"- Phase 8 promotion review: `{scorecard_gates['phase8_promotion_review_min_roi_complete_settled_observations']}` ROI-complete shadow observations.",
        f"- Real-money discussion: `{scorecard_gates['real_money_discussion_min_total_settled_observations_with_usable_roi']}` total settled observations with usable ROI.",
        f"- Real-money prerequisites: {'; '.join(scorecard_gates['real_money_also_requires'])}.",
        f"- Boundary: {scorecard_gates['evidence_boundary']}.",
        "",
        "## Current-Evidence Rebuild Contract",
        "",
        f"- Source: `{current_evidence_rebuild_contract['source']}` `{current_evidence_rebuild_contract['source_path']}`.",
        f"- Commands: {' -> '.join(f'`{command}`' for command in current_evidence_rebuild_contract['upstream_refresh_order_commands'])}.",
        f"- Requires settlement audit before bridge on source-byte changes: `{current_evidence_rebuild_contract['requires_settlement_audit_refresh_before_bridge_when_source_bytes_change']}`.",
        f"- Requires source consistency before quoting current totals: `{current_evidence_rebuild_contract['requires_source_consistency_before_quoting_current_totals']}`.",
        f"- Boundary: {current_evidence_rebuild_contract['evidence_boundary']}.",
        "",
        "## Fixture Scratch Metadata",
        "",
        f"- Fixture scratch metadata: `{scratch['fixture_root_relative']}` is project-local and each copied-run case root is cleared before setup.",
        f"- Boundary: {scratch['evidence_boundary']}.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        "",
        "## Sources",
        "",
        f"- `{rel(SCRIPT)}`",
        f"- `{rel(source_refresh.DEFAULT_RUNS_ROOT)}`",
    ])

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
