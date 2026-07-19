#!/usr/bin/env python3
"""
Fixture-driven validation for paper_trade_preflight_note.py.

Purpose:
- pin the preflight-note helper directly at the source layer
- keep active-target, no-target, API-unreachable, and explicit-error messaging reproducible
- verify the real CLI still writes both text and JSON note artifacts cleanly under isolated stubs
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from typing import Any

import paper_trade_preflight_note as preflight_source

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "paper_trade_preflight_note.py"
OUT_DIR = BASE / "out" / "status_validation" / "paper_trade_preflight_note"
TMP_PARENT = OUT_DIR / "_tmp"
FIXTURE_ROOT = TMP_PARENT / "preflight_note_fixture"
REPORT_MD = OUT_DIR / "paper_trade_preflight_note_validation.md"
REPORT_JSON = OUT_DIR / "paper_trade_preflight_note_validation.json"
LIVE_RUNS_ROOT = BASE / "out" / "daily_portfolio_runs"
TOP_LEVEL_DEFAULT_TEXT = BASE / "out" / "paper_trade_preflight_note.txt"
TOP_LEVEL_DEFAULT_JSON = BASE / "out" / "paper_trade_preflight_note.json"
REBUILD_COMMAND = "python3 validate_paper_trade_preflight_note.py"
SCORECARD_JSON = BASE / "forward_evidence_scorecard.json"
NO_BAQ_AS_BEL_PREREQUISITE = "no BAQ-as-BEL substitution"
EXPECTED_SOURCE_BOUNDARY_FIELDS = {
    "valid_evidence_scope": preflight_source.PREFLIGHT_VALID_EVIDENCE_SCOPE,
    "evidence_boundary": preflight_source.PREFLIGHT_EVIDENCE_BOUNDARY,
    "evidence_boundary_text": preflight_source.PREFLIGHT_EVIDENCE_BOUNDARY_TEXT,
}

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "paper-trade preflight-note validator",
    "valid_evidence_scope": preflight_source.PREFLIGHT_VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "isolated preflight-note fixture stubs",
        "saved run-root preflight_note.txt / preflight_note.json surfaces",
        "top-level default preflight helper artifact inventory",
        "superfecta_ops.py source-level track matching",
        "forward_evidence_scorecard.json decision_gate_minimums",
    ],
    "valid_use": "calendar/context classification and BAQ/BEL alias guardrail for paper-trade operator surfaces",
    "not_new_forward_evidence": True,
    "not_live_paper_trade_ledger": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_real_money_evidence": True,
    "not_promotion_readiness_evidence": True,
    "preflight_validator_passes_are_calendar_context_metadata_only": True,
    "non_goals": [
        "do not treat no-target preflight days as profitability evidence",
        "do not treat active-target preflight days as qualifying paper signals",
        "do not promote OP_REFINED_K7 or Phase 8 from preflight validator cleanliness",
        "do not substitute BAQ for BEL",
        "do not treat calendar/context classification as real-money evidence",
    ],
}


CASES: list[dict[str, Any]] = [
    {
        "name": "case_active_targets_text",
        "scenario": "text mode still says when primary paper-basket target tracks are racing and calls out shadow-only tracks separately",
        "format": "text",
        "payload": {
            "date": "2026-04-20",
            "checked_at": "2026-04-20T08:15:00-04:00",
            "api_ok": True,
            "has_targets": True,
            "relevant_tracks": ["OP", "CD"],
            "shadow_tracks": ["SA", "KEE"],
            "total_cards": 7,
            "error": None,
        },
        "expected_text": "Preflight context: primary paper-basket target tracks racing today: OP, CD. Shadow-only tracks also present: SA, KEE.\n",
        "expected_output": "out/paper_trade_preflight_note.txt",
    },
    {
        "name": "case_no_targets_text",
        "scenario": "text mode still explains honest no-target days instead of implying the rules just missed",
        "format": "text",
        "payload": {
            "date": "2026-04-21",
            "checked_at": "2026-04-21T08:10:00-04:00",
            "api_ok": True,
            "has_targets": False,
            "relevant_tracks": [],
            "shadow_tracks": ["AQU", "SA"],
            "excluded_tracks": ["BAQ"],
            "total_cards": 5,
            "error": None,
        },
        "expected_text": "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 5 NYRA card(s). Shadow-only tracks present: AQU, SA. Excluded track aliases present: BAQ (not treated as BEL).\n",
        "expected_output": "out/paper_trade_preflight_note.txt",
    },
    {
        "name": "case_no_targets_json",
        "scenario": "JSON mode still preserves the structured no-target classification instead of making a dead calendar look like a quiet rules miss",
        "format": "json",
        "payload": {
            "date": "2026-04-21",
            "checked_at": "2026-04-21T08:10:00-04:00",
            "api_ok": True,
            "has_targets": False,
            "relevant_tracks": [],
            "shadow_tracks": ["AQU", "SA"],
            "total_cards": 5,
            "error": None,
        },
        "expected_json": {
            "date": "2026-04-21",
            "checked_at": "2026-04-21T08:10:00-04:00",
            "api_ok": True,
            "calendar_state": "NO TARGETS",
            "calendar_reason": "no_targets",
            "has_targets": False,
            "relevant_tracks": [],
            "relevant_track_count": 0,
            "shadow_tracks": ["AQU", "SA"],
            "shadow_track_count": 2,
            "excluded_tracks": [],
            "excluded_track_count": 0,
            "total_cards": 5,
            "error": None,
            "note": "Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across 5 NYRA card(s). Shadow-only tracks present: AQU, SA."
        },
        "expected_output": "no_target_payload.json",
        "output_arg": "no_target_payload.json",
    },
    {
        "name": "case_api_unreachable_text",
        "scenario": "API-unreachable days still mark calendar state as unknown instead of pretending there were no targets",
        "format": "text",
        "payload": {
            "date": "2026-04-22",
            "checked_at": "2026-04-22T08:05:00-04:00",
            "api_ok": False,
            "has_targets": False,
            "relevant_tracks": [],
            "shadow_tracks": [],
            "total_cards": 0,
            "error": None,
        },
        "expected_text": "Preflight context: could not reach the NYRA preflight API, so calendar state is unknown.\n",
        "expected_output": "out/paper_trade_preflight_note.txt",
    },
    {
        "name": "case_explicit_error_text",
        "scenario": "explicit upstream preflight errors still surface the real error string in text output",
        "format": "text",
        "payload": {
            "date": "2026-04-23",
            "checked_at": "2026-04-23T08:20:00-04:00",
            "api_ok": True,
            "has_targets": False,
            "relevant_tracks": [],
            "shadow_tracks": [],
            "total_cards": 0,
            "error": "calendar decode failed",
        },
        "expected_text": "Preflight context: NYRA preflight check failed (calendar decode failed). Treat calendar state as unknown.\n",
        "expected_output": "out/paper_trade_preflight_note.txt",
    },
    {
        "name": "case_json_payload",
        "scenario": "JSON mode still preserves the structured preflight payload alongside the human note",
        "format": "json",
        "payload": {
            "date": "2026-04-24",
            "checked_at": "2026-04-24T08:25:00-04:00",
            "api_ok": True,
            "has_targets": True,
            "relevant_tracks": ["OP"],
            "shadow_tracks": ["CD", "DMR"],
            "total_cards": 4,
            "error": None,
        },
        "expected_json": {
            "date": "2026-04-24",
            "checked_at": "2026-04-24T08:25:00-04:00",
            "api_ok": True,
            "calendar_state": "ACTIVE TARGETS",
            "calendar_reason": "active_targets",
            "has_targets": True,
            "relevant_tracks": ["OP"],
            "relevant_track_count": 1,
            "shadow_tracks": ["CD", "DMR"],
            "shadow_track_count": 2,
            "excluded_tracks": [],
            "excluded_track_count": 0,
            "total_cards": 4,
            "error": None,
            "note": "Preflight context: primary paper-basket target tracks racing today: OP. Shadow-only tracks also present: CD, DMR.",
        },
        "expected_output": "preflight_payload.json",
        "output_arg": "preflight_payload.json",
    },
]


def prepare_tmp_parent() -> dict[str, Any]:
    """Use project-local scratch space so fixture writes avoid system temp quotas."""
    if TMP_PARENT.exists():
        shutil.rmtree(TMP_PARENT)
    TMP_PARENT.mkdir(parents=True, exist_ok=True)
    return {
        "tmp_parent": str(TMP_PARENT),
        "tmp_parent_is_project_local": TMP_PARENT.is_relative_to(BASE),
        "tmp_parent_cleared_before_fixture_run": True,
        "fixture_root": str(FIXTURE_ROOT.relative_to(BASE)),
    }


def write_case_files(case_root: Path, payload: dict[str, Any]) -> Path:
    shutil.copy2(SCRIPT, case_root / "paper_trade_preflight_note.py")
    stub = (
        "from __future__ import annotations\n"
        "\n"
        "def check_todays_cards_extended():\n"
        f"    return {payload!r}\n"
    )
    (case_root / "superfecta_ops.py").write_text(stub, encoding="utf-8")
    return case_root / "paper_trade_preflight_note.py"


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_root = FIXTURE_ROOT / case["name"]
    if case_root.exists():
        shutil.rmtree(case_root)
    case_root.mkdir(parents=True, exist_ok=True)
    case_script = write_case_files(case_root, case["payload"])

    cmd = [sys.executable, str(case_script), "--format", case["format"]]
    output_arg = case.get("output_arg")
    if output_arg:
        cmd.extend(["--output", output_arg])

    result = subprocess.run(cmd, cwd=case_root, capture_output=True, text=True)
    (case_root / "stdout.txt").write_text(result.stdout, encoding="utf-8")
    (case_root / "stderr.txt").write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise AssertionError(f"{case['name']}: unexpected non-zero exit: {result.stderr}")

    expected_output = case_root / case["expected_output"]
    if not expected_output.exists():
        raise AssertionError(f"{case['name']}: expected output file missing: {expected_output}")

    if case["format"] == "text":
        if result.stdout != case["expected_text"]:
            raise AssertionError(
                f"{case['name']}: stdout mismatch\nactual={result.stdout!r}\nexpected={case['expected_text']!r}"
            )
        output_text = expected_output.read_text(encoding="utf-8")
        if output_text != case["expected_text"]:
            raise AssertionError(
                f"{case['name']}: output file mismatch\nactual={output_text!r}\nexpected={case['expected_text']!r}"
            )
    else:
        expected_json = {
            **case["expected_json"],
            **EXPECTED_SOURCE_BOUNDARY_FIELDS,
        }
        payload = json.loads(result.stdout)
        output_payload = json.loads(expected_output.read_text(encoding="utf-8"))
        if payload != expected_json:
            raise AssertionError(
                f"{case['name']}: stdout JSON mismatch\nactual={json.dumps(payload, indent=2)}\nexpected={json.dumps(expected_json, indent=2)}"
            )
        if output_payload != expected_json:
            raise AssertionError(
                f"{case['name']}: output JSON mismatch\nactual={json.dumps(output_payload, indent=2)}\nexpected={json.dumps(expected_json, indent=2)}"
            )

    return {
        "name": case["name"],
        "scenario": case["scenario"],
        "result": "PASS",
        "stdout": str((case_root / 'stdout.txt').relative_to(BASE)),
        "output": str(expected_output.relative_to(BASE)),
    }


def live_run_roots() -> list[Path]:
    runs: list[Path] = []
    if not LIVE_RUNS_ROOT.exists():
        raise AssertionError(f"no live run folders found under {LIVE_RUNS_ROOT}")
    for run_root in sorted(p for p in LIVE_RUNS_ROOT.iterdir() if p.is_dir()):
        if (run_root / "preflight_note.txt").exists() and (run_root / "preflight_note.json").exists():
            runs.append(run_root)
    if not runs:
        raise AssertionError(f"no live preflight-note surfaces found under {LIVE_RUNS_ROOT}")
    return runs


def validate_live_surfaces() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    original_checker = preflight_source.check_todays_cards_extended
    try:
        for run_root in live_run_roots():
            json_path = run_root / "preflight_note.json"
            text_path = run_root / "preflight_note.txt"
            saved_payload = json.loads(json_path.read_text(encoding="utf-8"))
            preflight_source.check_todays_cards_extended = lambda payload=saved_payload: {
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
            rebuilt_payload = preflight_source.build_payload()
            expected_text = str(rebuilt_payload["note"]) + "\n"
            expected_json = json.dumps(rebuilt_payload, indent=2) + "\n"
            if text_path.read_text(encoding="utf-8") != expected_text:
                raise AssertionError(f"live preflight_note.txt drifted from the current source-layer rebuild: {text_path}")
            if json_path.read_text(encoding="utf-8") != expected_json:
                raise AssertionError(f"live preflight_note.json drifted from the current source-layer rebuild: {json_path}")
            results.append({
                "name": f"live_surface_{run_root.name}",
                "scenario": "saved live preflight-note surfaces match the current source-layer rebuild",
                "run_root": str(run_root.relative_to(BASE)),
                "note": rebuilt_payload["note"],
                "text_output": str(text_path.relative_to(BASE)),
                "json_output": str(json_path.relative_to(BASE)),
            })
    finally:
        preflight_source.check_todays_cards_extended = original_checker
    return results


def validate_top_level_default_artifact_boundary(live_surfaces: list[dict[str, Any]]) -> dict[str, Any]:
    latest_run_root = Path(live_surfaces[-1]["run_root"]) if live_surfaces else None
    latest_run_text = BASE / latest_run_root / "preflight_note.txt" if latest_run_root else None
    top_level_text = TOP_LEVEL_DEFAULT_TEXT.read_text(encoding="utf-8") if TOP_LEVEL_DEFAULT_TEXT.exists() else ""
    latest_text = latest_run_text.read_text(encoding="utf-8") if latest_run_text and latest_run_text.exists() else ""
    matches_latest_run_root = bool(top_level_text and latest_text and top_level_text == latest_text)
    top_line = top_level_text.splitlines()[0] if top_level_text.splitlines() else ""
    return {
        "name": "top_level_default_preflight_artifact_boundary",
        "scenario": "the stale-prone default out/paper_trade_preflight_note.txt helper artifact is inventoried as a standalone manual probe, not as the validated live run-root preflight surface",
        "result": "PASS",
        "artifact_role": "standalone manual helper output / scratch cache; daily operator surfaces use run-root preflight_note.txt/json instead",
        "text_output": str(TOP_LEVEL_DEFAULT_TEXT.relative_to(BASE)),
        "text_exists": TOP_LEVEL_DEFAULT_TEXT.exists(),
        "json_output": str(TOP_LEVEL_DEFAULT_JSON.relative_to(BASE)),
        "json_exists": TOP_LEVEL_DEFAULT_JSON.exists(),
        "latest_run_root": str(latest_run_root) if latest_run_root else "",
        "matches_latest_run_root": matches_latest_run_root,
        "first_line": top_line,
        "operator_guidance": "Before using the top-level default preflight helper artifact as a current calendar read, rerun paper_trade_preflight_note.py directly; for saved live/operator reads, use the run-root preflight_note.txt/json artifacts validated above.",
    }


def validate_source_track_matching() -> dict[str, Any]:
    import superfecta_ops as ops_source

    fake_cards = [
        {"cardName": "Belmont at the Big A", "cardDate": "2026-05-18T00:00:00", "cardId": "baq-card", "numberOfRunners": 80},
        {"cardName": "Belmont @ The Big A", "cardDate": "2026-05-18T00:00:00", "cardId": "baq-at-sign-card", "numberOfRunners": 81},
        {"cardName": "Belmont Park At The Big A", "cardDate": "2026-05-18T00:00:00", "cardId": "baq-belpark-biga-card", "numberOfRunners": 82},
        {"cardName": "Belmont Park @ The Big A", "cardDate": "2026-05-18T00:00:00", "cardId": "baq-belpark-at-sign-card", "numberOfRunners": 83},
        {"cardName": "Belmont Park At Aqueduct", "cardDate": "2026-05-18T00:00:00", "cardId": "baq-belpark-aqu-card", "numberOfRunners": 84},
        {"cardName": "BAQ", "cardDate": "2026-05-18T00:00:00", "cardId": "baq-short-card", "numberOfRunners": 70},
        {"cardName": "Belmont Park", "cardDate": "2026-05-18T00:00:00", "cardId": "bel-card", "numberOfRunners": 72},
        {"cardName": "Santa Anita Park", "cardDate": "2026-05-18T00:00:00", "cardId": "sa-card", "numberOfRunners": 61},
        {"cardName": "Churchill Downs", "cardDate": "2026-05-18T00:00:00", "cardId": "cd-card", "numberOfRunners": 93},
    ]
    stub = types.ModuleType("list_cards")
    stub.list_cards = lambda: fake_cards
    sentinel = object()
    original = sys.modules.get("list_cards", sentinel)
    sys.modules["list_cards"] = stub
    try:
        payload = ops_source.check_todays_cards_extended()
    finally:
        if original is sentinel:
            sys.modules.pop("list_cards", None)
        else:
            sys.modules["list_cards"] = original

    baq_shadow_cards = [
        card for card in payload.get("shadow_cards", [])
        if card.get("card_name") == "Belmont at the Big A"
    ]
    dangerous_bel_alias_names = {
        "Belmont @ The Big A",
        "Belmont Park @ The Big A",
        "Belmont at the Big A",
        "Belmont Park At The Big A",
        "Belmont Park At Aqueduct",
        "BAQ",
    }
    dangerous_bel_shadow_cards = [
        card for card in payload.get("shadow_cards", [])
        if card.get("track") == "BEL" and card.get("card_name") in dangerous_bel_alias_names
    ]
    bel_shadow_cards = [
        card for card in payload.get("shadow_cards", [])
        if card.get("track") == "BEL"
    ]
    if baq_shadow_cards:
        raise AssertionError("Belmont at the Big A must not be emitted as a BEL shadow card")
    if dangerous_bel_shadow_cards:
        raise AssertionError(f"dangerous BAQ/Big A labels must not be emitted as BEL shadow cards: {dangerous_bel_shadow_cards!r}")
    if [card.get("card_name") for card in bel_shadow_cards] != ["Belmont Park"]:
        raise AssertionError(f"expected only genuine Belmont Park to match BEL shadow, got {bel_shadow_cards!r}")
    if payload.get("excluded_tracks") != ["BAQ"]:
        raise AssertionError(f"expected BAQ in excluded_tracks, got {payload.get('excluded_tracks')!r}")
    excluded_card_names = [card.get("card_name") for card in payload.get("excluded_cards", [])]
    if set(excluded_card_names) != dangerous_bel_alias_names:
        raise AssertionError(f"expected every dangerous BAQ/Big A label to surface as excluded BAQ context, got {excluded_card_names!r}")
    if payload.get("relevant_tracks") != ["CD"]:
        raise AssertionError(f"expected only CD as active target in source fixture, got {payload.get('relevant_tracks')!r}")
    return {
        "name": "source_track_matching_baq_is_not_bel",
        "scenario": "superfecta_ops.check_todays_cards_extended keeps BAQ / Big A / Belmont-at-Aqueduct labels out of BEL while still allowing genuine Belmont Park",
        "result": "PASS",
        "active_tracks": payload.get("relevant_tracks", []),
        "shadow_tracks": payload.get("shadow_tracks", []),
        "excluded_tracks": payload.get("excluded_tracks", []),
        "excluded_card_names": excluded_card_names,
        "rejected_bel_alias_card_names": sorted(dangerous_bel_alias_names),
        "bel_shadow_card_names": [card.get("card_name") for card in bel_shadow_cards],
    }


def display_scorecard_path(scorecard_json: Path) -> str:
    try:
        return str(scorecard_json.relative_to(BASE))
    except ValueError:
        return str(scorecard_json)


def require_positive_non_bool_int(value: Any, *, field_name: str, source_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError(f"{source_name} {field_name} must be a positive non-boolean integer")
    return value


def require_string_list(value: Any, *, field_name: str, source_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise AssertionError(f"{source_name} {field_name} must be a string list")
    return value


def read_scorecard_gate_minimums(scorecard_json: Path = SCORECARD_JSON) -> dict[str, Any]:
    source_name = display_scorecard_path(scorecard_json)
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
        field_name="decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
        source_name=source_name,
    )
    phase8_min = require_positive_non_bool_int(
        phase8.get("min_roi_complete_settled_observations"),
        field_name="decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
        source_name=source_name,
    )
    real_money_min = require_positive_non_bool_int(
        real_money.get("min_total_settled_observations_with_usable_roi"),
        field_name="decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
        source_name=source_name,
    )
    real_money_requires = require_string_list(
        real_money.get("also_requires"),
        field_name="decision_gate_minimums.real_money_discussion.also_requires",
        source_name=source_name,
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
            "preflight-note calendar/context fixtures do not count toward anchor-displacement, "
            "Phase 8 promotion-review, or real-money discussion gates"
        ),
    }


def guardrail(condition: bool, check: str, detail: str) -> dict[str, str]:
    if not condition:
        raise AssertionError(f"{check}: {detail}")
    return {"check": check, "status": "pass", "detail": detail}


def configure_output_paths(fixture_root: Path, out_dir: Path) -> None:
    global OUT_DIR, TMP_PARENT, FIXTURE_ROOT, REPORT_MD, REPORT_JSON
    OUT_DIR = out_dir
    FIXTURE_ROOT = fixture_root
    TMP_PARENT = FIXTURE_ROOT.parent
    REPORT_MD = OUT_DIR / "paper_trade_preflight_note_validation.md"
    REPORT_JSON = OUT_DIR / "paper_trade_preflight_note_validation.json"


def assert_scorecard_failure_before_artifacts(
    *,
    scorecard_json: Path,
    mutation: Any,
    expected_error: str,
    check: str,
    detail: str,
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="preflight_note_scorecard_guardrail_") as tmp_name:
        tmpdir = Path(tmp_name)
        bad_scorecard = tmpdir / "forward_evidence_scorecard.json"
        bad_payload = json.loads(scorecard_json.read_text(encoding="utf-8"))
        mutation(bad_payload)
        bad_scorecard.write_text(json.dumps(bad_payload, indent=2) + "\n", encoding="utf-8")
        nested_fixture_root = tmpdir / "nested" / "fixture"
        nested_out_dir = tmpdir / "nested" / "out"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--scorecard-json",
                str(bad_scorecard),
                "--fixture-root",
                str(nested_fixture_root),
                "--out-dir",
                str(nested_out_dir),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
        )
        combined_output = result.stdout + result.stderr
        if result.returncode == 0:
            raise AssertionError(f"{check}: malformed scorecard unexpectedly passed")
        if expected_error not in combined_output:
            raise AssertionError(
                f"{check}: expected error {expected_error!r}, got stdout={result.stdout!r} stderr={result.stderr!r}"
            )
        if nested_fixture_root.exists() or nested_out_dir.exists():
            raise AssertionError(f"{check}: malformed scorecard created fixture/report artifacts")
    return guardrail(True, check, detail)


def scorecard_no_artifact_guardrails(scorecard_json: Path) -> list[dict[str, str]]:
    return [
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["anchor_displacement"].__setitem__(
                "min_roi_complete_settled_observations",
                True,
            ),
            expected_error=(
                "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check="scorecard_boolean_gate_floor_fails_before_preflight_artifacts",
            detail=(
                "a boolean anchor-displacement floor in forward_evidence_scorecard.json fails before "
                "nested preflight-note fixture/report artifacts are created"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["phase8_promotion_review"].__setitem__(
                "min_roi_complete_settled_observations",
                0,
            ),
            expected_error=(
                "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations "
                "must be a positive non-boolean integer"
            ),
            check="scorecard_nonpositive_phase8_gate_floor_fails_before_preflight_artifacts",
            detail=(
                "a non-positive Phase 8 promotion-review floor in forward_evidence_scorecard.json fails "
                "before nested preflight-note fixture/report artifacts are created"
            ),
        ),
        assert_scorecard_failure_before_artifacts(
            scorecard_json=scorecard_json,
            mutation=lambda payload: payload["decision_gate_minimums"]["real_money_discussion"].__setitem__(
                "min_total_settled_observations_with_usable_roi",
                0,
            ),
            expected_error=(
                "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi "
                "must be a positive non-boolean integer"
            ),
            check="scorecard_nonpositive_real_money_gate_floor_fails_before_preflight_artifacts",
            detail=(
                "a non-positive real-money discussion floor in forward_evidence_scorecard.json fails "
                "before nested preflight-note fixture/report artifacts are created"
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
            expected_error=(
                "decision_gate_minimums.real_money_discussion.also_requires "
                f"must include {NO_BAQ_AS_BEL_PREREQUISITE}"
            ),
            check="scorecard_missing_no_baq_fails_before_preflight_artifacts",
            detail=(
                "a scorecard missing the no-BAQ-as-BEL real-money prerequisite fails before "
                "nested preflight-note fixture/report artifacts are created"
            ),
        ),
    ]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard-json", type=Path, default=SCORECARD_JSON)
    parser.add_argument("--fixture-root", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args([] if argv is None else argv)
    scorecard_json = args.scorecard_json.expanduser().resolve()
    configure_output_paths(
        fixture_root=args.fixture_root.expanduser().resolve(),
        out_dir=args.out_dir.expanduser().resolve(),
    )
    scorecard_gates = read_scorecard_gate_minimums(scorecard_json)
    scorecard_guardrails = scorecard_no_artifact_guardrails(scorecard_json)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scratch = prepare_tmp_parent()
    for legacy in (
        FIXTURE_ROOT / "preflight_note_fixture_validation.md",
        FIXTURE_ROOT / "preflight_note_fixture_validation.json",
    ):
        legacy.unlink(missing_ok=True)

    fixture_results = [run_case(case) for case in CASES]
    live_surfaces = validate_live_surfaces()
    top_level_default_artifact = validate_top_level_default_artifact_boundary(live_surfaces)
    source_track_matching = validate_source_track_matching()
    results = fixture_results + live_surfaces + [top_level_default_artifact]
    child_checks = [
        *scorecard_guardrails,
        {
            "check": "fixture_calendar_state_split_stays_covered",
            "status": "pass",
            "detail": "fixture cases still keep active-target, no-target, API-unreachable, and explicit-error preflight states operationally distinct instead of flattening them into a generic no-card read",
        },
        {
            "check": "structured_calendar_classification_and_track_counts_stay_explicit",
            "status": "pass",
            "detail": "the structured payload still exposes first-class calendar_state/calendar_reason classification, compact active-target, shadow-track, and excluded-alias counts, plus source-level valid_evidence_scope/evidence_boundary/evidence_boundary_text fields so downstream wrappers do not have to infer calendar meaning or evidence scope from prose alone",
        },
        {
            "check": "direct_validation_report_exposes_preflight_valid_scope",
            "status": "pass",
            "detail": "the direct preflight-note validator report now exposes the raw valid_evidence_scope line and keeps green calendar/context checks classified as routing metadata only",
        },
        {
            "check": "saved_fixture_and_live_surfaces_match_current_rebuilds",
            "status": "pass",
            "detail": "fixture stdout/output artifacts plus saved live preflight text/json surfaces still have to match fresh source-layer rebuilds instead of drifting behind helper changes",
        },
        {
            "check": "shadow_only_and_no_target_language_stays_honest",
            "status": "pass",
            "detail": "active-target days still separate shadow-only tracks from the live basket, no-target days still say the active basket was absent instead of implying a clean rules miss, and the source-level card matcher keeps BAQ / Big A / Belmont-at-Aqueduct labels out of BEL while surfacing BAQ as an excluded alias",
        },
        {
            "check": "top_level_default_preflight_artifact_stays_inventoried_as_non_live_surface",
            "status": "pass",
            "detail": "the stale-prone default out/paper_trade_preflight_note.txt helper artifact is now inventoried separately as a standalone manual probe/scratch cache, so saved live validation keeps using run-root preflight_note.txt/json surfaces instead of silently treating the top-level file as current",
        },
        {
            "check": "preflight_note_explicitly_stays_calendar_context_not_new_evidence",
            "status": "pass",
            "detail": "the direct validator summary and JSON-mode source payload still say plainly that preflight note is a calendar/context classification surface rather than new forward evidence",
        },
        {
            "check": "preflight_note_preserves_scorecard_gate_boundary",
            "status": "pass",
            "detail": "the preflight-note validator now publishes the scorecard-sourced 30/20/100 gates plus the no-BAQ-as-BEL prerequisite while saying calendar/context fixtures do not count toward those gates",
        },
        {
            "check": "fixture_scratch_root_project_local",
            "status": "pass",
            "detail": f"preflight-note fixture stubs write under the cleared project-local temporary root {TMP_PARENT}",
        },
        {
            "check": "fixture_scratch_metadata_published",
            "status": "pass",
            "detail": "preflight-note validation publishes top-level project-local scratch metadata so operator and project rollups can verify the cleared fixture root without parsing markdown prose",
        },
    ]
    if (
        scorecard_gates.get("source") != "forward_evidence_scorecard.json"
        or scorecard_gates.get("source_path") != "decision_gate_minimums"
        or scorecard_gates.get("anchor_displacement_min_roi_complete_settled_observations") != 30
        or scorecard_gates.get("phase8_promotion_review_min_roi_complete_settled_observations") != 20
        or scorecard_gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") != 100
        or scorecard_gates.get("real_money_no_baq_as_bel_required") is not True
        or "no BAQ-as-BEL substitution" not in scorecard_gates.get("real_money_also_requires", [])
    ):
        raise AssertionError("preflight-note scorecard gate boundary no longer matches forward_evidence_scorecard.json")

    payload = {
        "suite_status": "pass",
        "artifact_status": "pass",
        "valid_evidence_scope": preflight_source.PREFLIGHT_VALID_EVIDENCE_SCOPE,
        "total_fixture_scenarios": len(fixture_results),
        "total_checks": len(results),
        "check_count": len(results),
        "child_check_count": len(child_checks),
        "child_checks": child_checks,
        "fixture_case_count": len(fixture_results),
        "live_surface_checks": len(live_surfaces),
        "top_level_default_artifact_checks": 1,
        "cases": results,
        "top_level_default_artifact": top_level_default_artifact,
        "source_track_matching": source_track_matching,
        "summary": {
            "current_read": "preflight-note helper still distinguishes active-target, no-target, API-unreachable, and explicit-error days cleanly, while now preserving first-class `calendar_state` / `calendar_reason` classification plus compact target/shadow/excluded track counts in the structured JSON payload that downstream wrappers and summaries rely on, with JSON-mode source output carrying `valid_evidence_scope`, `evidence_boundary`, and `evidence_boundary_text` so calendar context cannot be overread as scanner evidence, settled ROI, promotion readiness, live profitability, real-money support, or BAQ-as-BEL evidence, and with the direct validator report now exposing exact valid_evidence_scope=paper_trade_preflight_calendar_context_only as calendar/context metadata only. Fixture stdout/output artifacts stay under a cleared project-local validation scratch root plus saved live run-root text/json surfaces pinned to fresh source-layer rebuilds, the stale-prone top-level default out/paper_trade_preflight_note.txt helper artifact inventoried as a standalone manual probe rather than a validated live surface, a source-level BAQ/Big A guardrail so Belmont at the Big A cannot surface as BEL and dangerous Belmont Park at Big A/Aqueduct plus at-sign Big A labels stay excluded from BEL, rejects malformed and non-positive scorecard gates before fixture/report artifacts, and the scorecard-sourced 30/20/100 decision gates plus the no-BAQ-as-BEL prerequisite preserved as a boundary that calendar/context fixtures do not advance; preflight note: calendar/context classification surface, not new forward evidence by itself",
        },
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scorecard_decision_gate_minimums_read": scorecard_gates,
        "scratch": scratch,
        "fixture_root": str(FIXTURE_ROOT.relative_to(BASE)),
        "report_path": str(OUT_DIR.relative_to(BASE)),
        "rebuild": {
            "workdir": str(BASE),
            "command": REBUILD_COMMAND,
            "fixture_root": str(FIXTURE_ROOT.relative_to(BASE)),
            "report_path": str(REPORT_MD.relative_to(BASE)),
        },
    }

    lines = [
        "# Paper-Trade Preflight Note Validation",
        "",
        "This report validates `paper_trade_preflight_note.py` directly inside isolated fixture stubs under the cleared project-local scratch root `out/status_validation/paper_trade_preflight_note/_tmp/`, while publishing the direct validator readout under `out/status_validation/paper_trade_preflight_note/`.",
        "",
        "## Rebuild",
        "",
        f"- Working directory: `{BASE}`",
        f"- Command: `{REBUILD_COMMAND}`",
        f"- Fixture root: `{FIXTURE_ROOT.relative_to(BASE)}`",
        f"- Fixture scratch root: `{TMP_PARENT.relative_to(BASE)}`",
        f"- Fixture scratch root project-local: `{scratch['tmp_parent_is_project_local']}`",
        f"- Fixture scratch root cleared before fixture run: `{scratch['tmp_parent_cleared_before_fixture_run']}`",
        f"- Direct report path: `{REPORT_MD.relative_to(BASE)}`",
        "",
        "## Fixture cases",
        "",
        "| Case | Scenario | Output artifact |",
        "|---|---|---|",
    ]
    for row in fixture_results:
        lines.append(f"| `{row['name']}` | {row['scenario']} | `{row['output']}` |")

    lines.extend([
        "",
        "## Live current surfaces",
        "",
    ])
    for row in live_surfaces:
        lines.append(f"- `{row['run_root']}` -> `{row['text_output']}` and `{row['json_output']}`")

    lines.extend([
        "",
        "## Top-level default helper artifact boundary",
        "",
        f"- Artifact: `{top_level_default_artifact['text_output']}` ({'present' if top_level_default_artifact['text_exists'] else 'missing'}).",
        f"- Adjacent JSON: `{top_level_default_artifact['json_output']}` ({'present' if top_level_default_artifact['json_exists'] else 'missing'}).",
        f"- Role: {top_level_default_artifact['artifact_role']}.",
        f"- Latest validated run root: `{top_level_default_artifact['latest_run_root'] or 'none'}`.",
        f"- Matches latest run-root preflight text: `{top_level_default_artifact['matches_latest_run_root']}`.",
        f"- First line now on disk: {top_level_default_artifact['first_line'] or 'missing'}",
        f"- Operator guidance: {top_level_default_artifact['operator_guidance']}",
        "",
        "## Source-level track-matching guardrail",
        "",
        f"- `{source_track_matching['name']}`: {source_track_matching['scenario']}.",
        f"- Active: {', '.join(source_track_matching['active_tracks']) or 'none'}; shadow: {', '.join(source_track_matching['shadow_tracks']) or 'none'}; excluded: {', '.join(source_track_matching['excluded_tracks']) or 'none'}.",
        f"- Rejected BEL aliases: {', '.join(source_track_matching['rejected_bel_alias_card_names'])}.",
        "",
        "## Current Read",
        "",
        f"- Suite read: {payload['summary']['current_read']}",
        "",
        "## Evidence Boundary",
        "",
        f"- Artifact role: {EVIDENCE_BOUNDARY['artifact_role']}",
        f"- valid_evidence_scope={EVIDENCE_BOUNDARY['valid_evidence_scope']}",
        f"- Valid use: {EVIDENCE_BOUNDARY['valid_use']}",
        "- Boundary: preflight-note validator cleanliness is calendar/context metadata only, not new forward evidence, not a live paper-trade ledger, not a current-day scanner result, not settled ROI, not live profitability, not promotion readiness, and not real-money evidence.",
        "- Non-goals: do not treat no-target preflight days as profitability evidence, active-target calendar presence as a qualifying paper signal, or calendar/context fixtures as promotion / real-money support.",
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
        "## Validation result",
        "",
        "- Active-target days still say which live-basket tracks are racing and keep shadow-only tracks separate.",
        "- No-target days still say OP / CD were not on the calendar instead of implying a clean rules miss.",
        "- Belmont at the Big A, at-sign Big A labels, Belmont Park at the Big A, Belmont Park at Aqueduct, and BAQ are now surfaced as excluded BAQ context and are not treated as BEL; genuine Belmont Park remains the only BEL shadow match in the source-level fixture.",
        "- API-unreachable and explicit-error days still mark the calendar state as unknown instead of collapsing into the no-target branch.",
        "- JSON mode still preserves the structured fields the wrapper and downstream summaries depend on across both active-target and no-target branches.",
        "- The JSON payload now also exposes first-class `calendar_state` / `calendar_reason` classification plus compact target/shadow/excluded track counts, so downstream checks do not have to reconstruct the calendar classification from multiple booleans, lists, alias exclusions, and error-state inference.",
        "- JSON-mode source output and the direct validator report now carry exact `valid_evidence_scope=paper_trade_preflight_calendar_context_only` metadata that keeps preflight calendar context out of scanner-result, settled-ROI, promotion, live-profitability, real-money, and BAQ-as-BEL evidence lanes.",
        "- The validator now also fails if any saved live `preflight_note.txt` or `preflight_note.json` surface under `out/daily_portfolio_runs/` drifts from the current source-layer rebuild.",
        "- Fixture stubs now write under a cleared project-local validation scratch root instead of the older separate status-validation fixture tree.",
        "- The top-level default `out/paper_trade_preflight_note.txt` helper artifact is now inventoried as a standalone manual probe/scratch cache rather than silently treated as one of the validated live operator surfaces.",
        "- The validator JSON now publishes fourteen explicit structured guardrails, including direct validator valid_evidence_scope exposure, so parent rollups can verify the preflight calendar/context boundary without inferring it from source-output fields alone.",
        "",
        "## Bottom Line",
        "",
        "Green here means the preflight-note helper still keeps active-target, no-target, and unknown-calendar days structurally distinct in both text and JSON, so downstream wrappers do not have to infer whether a quiet-looking day came from an empty race calendar or an actual scan result. This is a calendar/context contract check, not new forward-profit evidence.",
        "",
        "## Sources",
        "",
    ])
    for row in fixture_results:
        lines.append(f"- `{row['stdout']}`")
        lines.append(f"- `{row['output']}`")
    for row in live_surfaces:
        lines.append(f"- `{row['text_output']}`")
        lines.append(f"- `{row['json_output']}`")
    if top_level_default_artifact["text_exists"]:
        lines.append(f"- `{top_level_default_artifact['text_output']}` (standalone manual helper output; not a validated run-root live surface)")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_JSON}")
    for row in results:
        output = row.get('output') or f"{row['text_output']} | {row['json_output']}"
        print(f"PASS {row['name']}: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
